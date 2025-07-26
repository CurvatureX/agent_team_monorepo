"""
gRPC server for Workflow Agent service - New unified ProcessConversation interface
"""

import asyncio
import time
from concurrent import futures
from typing import Optional, AsyncGenerator

import grpc
import structlog

from agents.workflow_agent import WorkflowAgent
from core.config import settings
from proto import workflow_agent_pb2, workflow_agent_pb2_grpc
from agents.state import WorkflowStage, WorkflowOrigin
from agents.state_converter import StateConverter

logger = structlog.get_logger()


class WorkflowAgentServicer(workflow_agent_pb2_grpc.WorkflowAgentServicer):
    """Implementation of the unified WorkflowAgent gRPC service"""

    def __init__(self):
        # Initialize the LangGraph agent
        self.workflow_agent = WorkflowAgent()
        logger.info("WorkflowAgent initialized with new ProcessConversation interface")



    async def ProcessConversation(
        self, 
        request: workflow_agent_pb2.ConversationRequest, 
        context: grpc.aio.ServicerContext
    ) -> AsyncGenerator[workflow_agent_pb2.ConversationResponse, None]:
        """
        Unified interface for processing all 6-stage workflow conversations
        """
        try:
            logger.info(
                "Processing conversation", 
                session_id=request.session_id,
                stage=request.current_state.stage if request.current_state else "NEW",
                user_message_length=len(request.user_message)
            )

            # Convert protobuf state to internal format
            if request.current_state:
                current_state = StateConverter.proto_to_workflow_state(request.current_state)
            else:
                # Initialize new state using WorkflowState structure
                current_state = {
                    "session_id": request.session_id,
                    "user_id": request.user_id,
                    "created_at": int(time.time() * 1000),
                    "updated_at": int(time.time() * 1000),
                    "stage": WorkflowStage.CLARIFICATION,
                    "execution_history": [],
                    "clarification_context": {
                        "origin": WorkflowOrigin(request.workflow_context.origin) if request.workflow_context else WorkflowOrigin.CREATE,
                        "collected_info": {},
                        "pending_questions": []
                    },
                    "conversations": [],
                    "intent_summary": "",
                    "gaps": [],
                    "alternatives": [],
                    "current_workflow": {},
                    "debug_result": "",
                    "debug_loop_count": 0,
                    "workflow_context": {
                        "origin": request.workflow_context.origin if request.workflow_context else "create",
                        "source_workflow_id": request.workflow_context.source_workflow_id if request.workflow_context else "",
                        "modification_intent": request.workflow_context.modification_intent if request.workflow_context else ""
                    }
                }

            # Add user message to conversation history
            if request.user_message:
                current_state["conversations"].append({
                    "role": "user",
                    "text": request.user_message,
                    "timestamp": int(time.time() * 1000),
                    "metadata": {}
                })

            # Process through LangGraph - use astream for streaming
            previous_stage = current_state["stage"]
            
            async for chunk in self.workflow_agent.graph.astream(current_state):
                for node_name, node_output in chunk.items():
                    logger.info(f"Processing node: {node_name}", stage=node_output.get("stage"))
                    
                    # Detect stage changes
                    current_stage = node_output.get("stage", previous_stage)
                    if current_stage != previous_stage:
                        # Stage transition detected
                        stage_response = workflow_agent_pb2.ConversationResponse(
                            session_id=request.session_id,
                            type=workflow_agent_pb2.RESPONSE_STATUS,
                            status=workflow_agent_pb2.StatusContent(
                                new_stage=StateConverter._internal_stage_to_proto(current_stage),
                                previous_stage=StateConverter._internal_stage_to_proto(previous_stage),
                                stage_description=f"Entering {current_stage} stage",
                                pending_actions=[]
                            ),
                            updated_state=StateConverter.workflow_state_to_proto(node_output),
                            timestamp=int(time.time() * 1000),
                            is_final=False
                        )
                        yield stage_response
                        previous_stage = current_stage

                    # Handle different node types
                    if node_name == "clarification":
                        # Clarification node completed
                        if current_stage == WorkflowStage.NEGOTIATION:
                            # Moving to negotiation - will generate questions
                            continue
                        elif current_stage == WorkflowStage.GAP_ANALYSIS:
                            # Intent is clear, moving forward
                            message_response = workflow_agent_pb2.ConversationResponse(
                                session_id=request.session_id,
                                type=workflow_agent_pb2.RESPONSE_MESSAGE,
                                message=workflow_agent_pb2.MessageContent(
                                    text="Great! I understand your requirements. Let me analyze what we can implement.",
                                    role="assistant",
                                    message_type="text",
                                    metadata={}
                                ),
                                updated_state=StateConverter.workflow_state_to_proto(node_output),
                                timestamp=int(time.time() * 1000),
                                is_final=False
                            )
                            yield message_response

                    elif node_name == "negotiation":
                        # Negotiation node - return questions to user
                        pending_questions = node_output.get("clarification_context", {}).get("pending_questions", [])
                        
                        if pending_questions:
                            # Generate clarification questions
                            questions = []
                            for i, q in enumerate(pending_questions[:3]):  # Limit to 3 questions
                                question = workflow_agent_pb2.ClarificationQuestion(
                                    id=f"q_{i+1}",
                                    question=q,
                                    category="general",
                                    is_required=True,
                                    options=[]
                                )
                                questions.append(question)

                            question_response = workflow_agent_pb2.ConversationResponse(
                                session_id=request.session_id,
                                type=workflow_agent_pb2.RESPONSE_MESSAGE,
                                message=workflow_agent_pb2.MessageContent(
                                    text="I need some clarification to better understand your requirements:",
                                    role="assistant",
                                    message_type="question",
                                    metadata={},
                                    questions=questions
                                ),
                                updated_state=StateConverter.workflow_state_to_proto(node_output),
                                timestamp=int(time.time() * 1000),
                                is_final=True  # Wait for user input
                            )
                            yield question_response
                            return  # Exit and wait for user input

                    elif node_name == "gap_analysis":
                        # Gap analysis completed
                        gaps = node_output.get("gaps", [])
                        if gaps:
                            gap_message_response = workflow_agent_pb2.ConversationResponse(
                                session_id=request.session_id,
                                type=workflow_agent_pb2.RESPONSE_MESSAGE,
                                message=workflow_agent_pb2.MessageContent(
                                    text=f"I've identified some areas that need alternatives: {', '.join(gaps)}",
                                    role="assistant",
                                    message_type="text",
                                    metadata={}
                                ),
                                updated_state=StateConverter.workflow_state_to_proto(node_output),
                                timestamp=int(time.time() * 1000),
                                is_final=False
                            )
                            yield gap_message_response

                    elif node_name == "alternative_generation":
                        # Alternative generation completed
                        alternatives = node_output.get("alternatives", [])
                        if alternatives:
                            alt_options = []
                            for alt in alternatives:
                                option = workflow_agent_pb2.AlternativeOption(
                                    id=alt.get("id", ""),
                                    title=alt.get("title", ""),
                                    description=alt.get("description", ""),
                                    approach=alt.get("approach", ""),
                                    trade_offs=alt.get("trade_offs", []),
                                    complexity=alt.get("complexity", "medium")
                                )
                                alt_options.append(option)

                            alternatives_response = workflow_agent_pb2.ConversationResponse(
                                session_id=request.session_id,
                                type=workflow_agent_pb2.RESPONSE_MESSAGE,
                                message=workflow_agent_pb2.MessageContent(
                                    text="Here are some alternative approaches for your workflow:",
                                    role="assistant",
                                    message_type="options",
                                    metadata={},
                                    alternatives=alt_options
                                ),
                                updated_state=StateConverter.workflow_state_to_proto(node_output),
                                timestamp=int(time.time() * 1000),
                                is_final=True  # Wait for user selection
                            )
                            yield alternatives_response
                            return

                    elif node_name == "workflow_generation":
                        # Workflow generation in progress
                        generation_response = workflow_agent_pb2.ConversationResponse(
                            session_id=request.session_id,
                            type=workflow_agent_pb2.RESPONSE_MESSAGE,
                            message=workflow_agent_pb2.MessageContent(
                                text="Generating your workflow...",
                                role="assistant",
                                message_type="text",
                                metadata={"workflow_id": node_output.get("workflow_id", "")}
                            ),
                            updated_state=StateConverter.workflow_state_to_proto(node_output),
                            timestamp=int(time.time() * 1000),
                            is_final=False
                        )
                        yield generation_response

                    elif node_name == "debug":
                        # Debug/validation stage
                        debug_response = workflow_agent_pb2.ConversationResponse(
                            session_id=request.session_id,
                            type=workflow_agent_pb2.RESPONSE_MESSAGE,
                            message=workflow_agent_pb2.MessageContent(
                                text="Validating and optimizing your workflow...",
                                role="assistant",
                                message_type="text",
                                metadata={}
                            ),
                            updated_state=StateConverter.workflow_state_to_proto(node_output),
                            timestamp=int(time.time() * 1000),
                            is_final=False
                        )
                        yield debug_response

            # Final completion response
            final_response = workflow_agent_pb2.ConversationResponse(
                session_id=request.session_id,
                type=workflow_agent_pb2.RESPONSE_MESSAGE,
                message=workflow_agent_pb2.MessageContent(
                    text="Workflow processing completed!",
                    role="assistant",
                    message_type="text",
                    metadata={"workflow_id": current_state.get("workflow_id", "")}
                ),
                updated_state=StateConverter.workflow_state_to_proto(current_state),
                timestamp=int(time.time() * 1000),
                is_final=True
            )
            yield final_response

        except Exception as e:
            logger.error("Failed to process conversation", error=str(e), session_id=request.session_id)
            
            error_response = workflow_agent_pb2.ConversationResponse(
                session_id=request.session_id,
                type=workflow_agent_pb2.RESPONSE_ERROR,
                error=workflow_agent_pb2.ErrorContent(
                    error_code="INTERNAL_ERROR",
                    message=f"Failed to process conversation: {str(e)}",
                    details=str(e),
                    is_recoverable=True
                ),
                timestamp=int(time.time() * 1000),
                is_final=True
            )
            yield error_response


class WorkflowAgentServer:
    """gRPC server for Workflow Agent with unified ProcessConversation interface"""

    def __init__(self):
        self.server: Optional[grpc.aio.Server] = None
        self.servicer = WorkflowAgentServicer()

    async def start(self):
        """Start the gRPC server"""
        try:
            self.server = grpc.aio.server(
                futures.ThreadPoolExecutor(max_workers=settings.MAX_WORKERS)
            )

            # Add the servicer to the server
            workflow_agent_pb2_grpc.add_WorkflowAgentServicer_to_server(self.servicer, self.server)

            # Configure server address
            listen_addr = f"{settings.GRPC_HOST}:{settings.GRPC_PORT}"
            self.server.add_insecure_port(listen_addr)

            # Start the server
            await self.server.start()
            logger.info("gRPC server started with ProcessConversation interface", address=listen_addr)

        except Exception as e:
            logger.error("Failed to start gRPC server", error=str(e))
            raise

    async def stop(self):
        """Stop the gRPC server"""
        if self.server:
            logger.info("Stopping gRPC server")
            await self.server.stop(grace=5)
            logger.info("gRPC server stopped")

    async def wait_for_termination(self):
        """Wait for the server to terminate"""
        if self.server:
            await self.server.wait_for_termination()