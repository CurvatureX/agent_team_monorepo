"""
gRPC Client for Workflow Service - New ProcessConversation Interface
"""

import asyncio
import time
from typing import Any, AsyncGenerator, Dict, Optional

from app.core.config import get_settings

settings = get_settings()
# Import gRPC modules
import grpc
from app.services.state_manager import get_state_manager
import logging

logger = logging.getLogger("app.services.grpc_client")

try:
    from proto import workflow_agent_pb2, workflow_agent_pb2_grpc

    GRPC_AVAILABLE = True
    logger.info("gRPC modules loaded successfully")
except ImportError as e:
    # Fallback: proto modules not available
    logger.error(f"gRPC proto modules not available. Using mock client: {str(e)}")
    workflow_agent_pb2 = None
    workflow_agent_pb2_grpc = None
    GRPC_AVAILABLE = False


class WorkflowGRPCClient:
    """
    gRPC client for the unified ProcessConversation interface
    Integrates with StateManager for state persistence
    """

    def __init__(self):
        self.host = settings.WORKFLOW_SERVICE_HOST
        self.port = settings.WORKFLOW_SERVICE_PORT
        self.channel = None
        self.stub = None
        self.connected = False
        self.state_manager = get_state_manager()

    async def connect(self):
        """Connect to workflow service"""
        try:
            if GRPC_AVAILABLE:
                # Create gRPC channel and stub
                self.channel = grpc.aio.insecure_channel(f"{self.host}:{self.port}")  # type: ignore
                self.stub = workflow_agent_pb2_grpc.WorkflowAgentStub(self.channel)

                # Test connection with the newer API
                try:
                    # Try the newer method first
                    await asyncio.wait_for(self.channel.channel_ready(), timeout=5.0)
                except AttributeError:
                    # Fallback to the older method for compatibility
                    try:
                        import grpc.experimental as grpc_experimental

                        await asyncio.wait_for(
                            grpc_experimental.aio.channel_ready(self.channel), timeout=5.0
                        )
                    except (AttributeError, ImportError):
                        # If all else fails, just connect without verification
                        await asyncio.sleep(0.1)

                self.connected = True
                logger.info(f"Connected to workflow service {self.host}:{self.port}")
            else:
                # Mock connection for environments without gRPC
                await asyncio.sleep(0.1)
                self.connected = True
                logger.info(f"Mock connected to workflow service {self.host}:{self.port}")

        except Exception as e:
            logger.error(f"Failed to connect to workflow service: {e}")
            self.connected = False
            raise

    async def close(self):
        """Close gRPC connection"""
        if self.channel:
            await self.channel.close()
        self.connected = False
        logger.info("Closed workflow service connection")

    async def process_conversation_stream(
        self,
        session_id: str,
        user_message: str,
        user_id: str = "anonymous",
        workflow_context: Optional[Dict[str, Any]] = None,
        access_token: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process conversation using the new ProcessConversation interface

        Args:
            session_id: Session identifier
            user_message: User's message
            user_id: User identifier
            workflow_context: Optional workflow context (origin, source_workflow_id, etc.)
            access_token: User's JWT token for state persistence

        Yields:
            Streaming responses from the workflow agent
        """
        if not self.connected:
            await self.connect()

        try:
            if GRPC_AVAILABLE:
                # Get current state from database
                current_state_data = self.state_manager.get_state_by_session(
                    session_id, access_token
                )

                # Prepare gRPC request
                request = workflow_agent_pb2.ConversationRequest(
                    session_id=session_id, user_id=user_id, user_message=user_message
                )

                # Add workflow context if provided
                if workflow_context and isinstance(workflow_context, dict):
                    try:
                        context = workflow_agent_pb2.WorkflowContext()
                        context.origin = str(workflow_context.get("origin", "create"))
                        context.source_workflow_id = str(
                            workflow_context.get("source_workflow_id", "")
                        )
                        context.modification_intent = str(
                            workflow_context.get("modification_intent", "")
                        )
                        request.workflow_context.CopyFrom(context)
                    except Exception as e:
                        logger.error(f"Error setting workflow_context in request: {e}")

                # Add current state if exists
                if current_state_data:
                    try:
                        # Convert database state to protobuf AgentState
                        agent_state = self._db_state_to_proto(current_state_data)
                        request.current_state.CopyFrom(agent_state)
                    except Exception as e:
                        logger.error(f"Error converting state to proto: {e}")
                        logger.error(f"State data details: {current_state_data}")
                        import traceback

                        logger.error(f"Traceback details: {traceback.format_exc()}")
                        raise

                logger.info(f"About to call ProcessConversation with request: {request}")

                # Stream conversation processing
                try:
                    async for response in self.stub.ProcessConversation(request):
                        # Convert protobuf response to dict
                        response_dict = self._proto_response_to_dict(response)

                        # Save updated state to database if provided
                        if response.updated_state:
                            updated_state = self._proto_state_to_dict(response.updated_state)
                            self.state_manager.save_full_state(
                                session_id, updated_state, access_token
                            )

                        yield response_dict
                except Exception as grpc_error:
                    logger.error(f"gRPC call error: {grpc_error}")
                    import traceback

                    logger.error(f"gRPC traceback details: {traceback.format_exc()}")
                    raise

            else:
                logger.error("gRPC is not available")

        except Exception as e:
            logger.error(f"Error in process_conversation_stream: {e}")
            # Yield error response
            yield {
                "type": "error",
                "session_id": session_id,
                "error": {
                    "error_code": "INTERNAL_ERROR",
                    "message": f"Failed to process conversation: {str(e)}",
                    "details": str(e),
                    "is_recoverable": True,
                },
                "timestamp": int(time.time() * 1000),
                "is_final": True,
            }

    def _db_state_to_proto(self, db_state: Dict[str, Any]):
        """Convert database state to protobuf AgentState"""
        if not GRPC_AVAILABLE:
            return None

        # This would use the StateConverter from workflow_agent service
        # For now, create a basic AgentState with safe type conversions

        def safe_timestamp(value, default=None):
            """Safely convert timestamp to integer"""
            if default is None:
                default = int(time.time() * 1000)
            if isinstance(value, (int, float)):
                return int(value)
            elif isinstance(value, str):
                try:
                    # Try parsing ISO format or timestamp
                    import datetime

                    if "T" in value or "-" in value:
                        dt = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
                        return int(dt.timestamp() * 1000)
                    else:
                        return int(float(value))
                except (ValueError, TypeError):
                    return default
            else:
                return default

        try:
            # 创建基本AgentState对象，不包含复杂嵌套字段
            agent_state = workflow_agent_pb2.AgentState()

            # 设置基本字段
            agent_state.session_id = str(db_state.get("session_id", ""))
            agent_state.user_id = str(db_state.get("user_id", ""))
            agent_state.created_at = safe_timestamp(db_state.get("created_at"))
            agent_state.updated_at = safe_timestamp(db_state.get("updated_at"))
            agent_state.stage = self._stage_to_proto_enum(db_state.get("stage", "clarification"))
            agent_state.intent_summary = str(db_state.get("intent_summary", ""))
            agent_state.current_workflow_json = str(db_state.get("current_workflow_json", ""))
            agent_state.debug_result = str(db_state.get("debug_result", ""))
            agent_state.debug_loop_count = int(db_state.get("debug_loop_count", 0) or 0)

            # 处理简单的repeated字段
            gaps = db_state.get("gaps") or []
            if isinstance(gaps, list):
                agent_state.gaps[:] = [str(gap) for gap in gaps]

            execution_history = db_state.get("execution_history") or []
            if isinstance(execution_history, list):
                agent_state.execution_history[:] = [str(item) for item in execution_history]

            # 处理复杂嵌套对象 - 使用安全的方式
            clarification_context = db_state.get("clarification_context")
            if clarification_context and isinstance(clarification_context, dict):
                try:
                    # 创建ClarificationContext对象
                    context = workflow_agent_pb2.ClarificationContext()
                    context.purpose = str(clarification_context.get("purpose", ""))
                    context.origin = str(clarification_context.get("origin", ""))

                    # 处理pending_questions
                    pending_questions = clarification_context.get("pending_questions", [])
                    if isinstance(pending_questions, list):
                        context.pending_questions[:] = [str(q) for q in pending_questions]

                    # 处理collected_info (map类型)
                    collected_info = clarification_context.get("collected_info", {})
                    if isinstance(collected_info, dict):
                        for key, value in collected_info.items():
                            context.collected_info[str(key)] = str(value)

                    agent_state.clarification_context.CopyFrom(context)
                except Exception as e:
                    logger.error(f"Error setting clarification_context: {e}")

            # 处理workflow_context
            workflow_context = db_state.get("workflow_context")
            if workflow_context and isinstance(workflow_context, dict):
                try:
                    context = workflow_agent_pb2.WorkflowContext()
                    context.origin = str(workflow_context.get("origin", ""))
                    context.source_workflow_id = str(workflow_context.get("source_workflow_id", ""))
                    context.modification_intent = str(
                        workflow_context.get("modification_intent", "")
                    )
                    agent_state.workflow_context.CopyFrom(context)
                except Exception as e:
                    logger.error(f"Error setting workflow_context: {e}")

        except Exception as e:
            logger.error(f"Error creating AgentState: {e}")
            raise

        # Add conversations if available
        conversations = db_state.get("conversations", [])
        if isinstance(conversations, str):
            try:
                import json

                conversations = json.loads(conversations)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse conversations JSON: {conversations}")
                conversations = []

        if isinstance(conversations, list):
            for conv in conversations:
                try:
                    if isinstance(conv, dict):
                        conversation = workflow_agent_pb2.Conversation()
                        conversation.role = str(conv.get("role", "user"))
                        conversation.text = str(conv.get("text", ""))
                        conversation.timestamp = safe_timestamp(conv.get("timestamp"))

                        # Handle metadata separately to ensure string values
                        metadata = conv.get("metadata", {})
                        if isinstance(metadata, dict):
                            for key, value in metadata.items():
                                conversation.metadata[str(key)] = str(value)

                        agent_state.conversations.append(conversation)
                except Exception as e:
                    logger.error(f"Error converting conversation to proto: {e}")
                    continue

        return agent_state

    def _proto_response_to_dict(self, response) -> Dict[str, Any]:
        """Convert protobuf ConversationResponse to dictionary"""
        result = {
            "session_id": response.session_id,
            "timestamp": response.timestamp,
            "is_final": response.is_final,
        }

        # Handle different response types
        if response.type == workflow_agent_pb2.RESPONSE_MESSAGE:
            result["type"] = "message"
            result["message"] = {
                "text": response.message.text,
                "role": response.message.role,
                "message_type": response.message.message_type,
                "metadata": dict(response.message.metadata),
            }

            # Add questions if present
            if response.message.questions:
                result["message"]["questions"] = []
                for q in response.message.questions:
                    result["message"]["questions"].append(
                        {
                            "id": q.id,
                            "question": q.question,
                            "category": q.category,
                            "is_required": q.is_required,
                            "options": list(q.options),
                        }
                    )

            # Add alternatives if present
            if response.message.alternatives:
                result["message"]["alternatives"] = []
                for alt in response.message.alternatives:
                    result["message"]["alternatives"].append(
                        {
                            "id": alt.id,
                            "title": alt.title,
                            "description": alt.description,
                            "approach": alt.approach,
                            "trade_offs": list(alt.trade_offs),
                            "complexity": alt.complexity,
                        }
                    )

        elif response.type == workflow_agent_pb2.RESPONSE_STATUS:
            result["type"] = "status"
            result["status"] = {
                "new_stage": self._proto_enum_to_stage(response.status.new_stage),
                "previous_stage": self._proto_enum_to_stage(response.status.previous_stage),
                "stage_description": response.status.stage_description,
                "pending_actions": list(response.status.pending_actions),
            }

        elif response.type == workflow_agent_pb2.RESPONSE_ERROR:
            result["type"] = "error"
            result["error"] = {
                "error_code": response.error.error_code,
                "message": response.error.message,
                "details": response.error.details,
                "is_recoverable": response.error.is_recoverable,
            }

        return result

    def _proto_state_to_dict(self, agent_state) -> Dict[str, Any]:
        """Convert protobuf AgentState to dictionary for state manager"""
        state_dict = {
            "session_id": agent_state.session_id,
            "user_id": agent_state.user_id,
            "created_at": agent_state.created_at,
            "updated_at": agent_state.updated_at,
            "stage": self._proto_enum_to_stage(agent_state.stage),
            "execution_history": list(agent_state.execution_history),
            "intent_summary": agent_state.intent_summary,
            "gaps": list(agent_state.gaps),
            "current_workflow": agent_state.current_workflow_json,
            "debug_result": agent_state.debug_result,
            "debug_loop_count": agent_state.debug_loop_count,
        }

        # Add conversations
        conversations = []
        for conv in agent_state.conversations:
            conversations.append(
                {
                    "role": conv.role,
                    "text": conv.text,
                    "timestamp": conv.timestamp,
                    "metadata": dict(conv.metadata),
                }
            )
        state_dict["conversations"] = conversations

        # Add alternatives
        alternatives = []
        for alt in agent_state.alternatives:
            alternatives.append(
                {
                    "id": alt.id,
                    "title": alt.title,
                    "description": alt.description,
                    "approach": alt.approach,
                    "trade_offs": list(alt.trade_offs),
                    "complexity": alt.complexity,
                }
            )
        state_dict["alternatives"] = alternatives

        return state_dict

    def _stage_to_proto_enum(self, stage: str) -> int:
        """Convert stage string to protobuf enum"""
        if not GRPC_AVAILABLE:
            return 0

        mapping = {
            "clarification": workflow_agent_pb2.STAGE_CLARIFICATION,
            "negotiation": workflow_agent_pb2.STAGE_NEGOTIATION,
            "gap_analysis": workflow_agent_pb2.STAGE_GAP_ANALYSIS,
            "alternative_generation": workflow_agent_pb2.STAGE_ALTERNATIVE_GENERATION,
            "workflow_generation": workflow_agent_pb2.STAGE_WORKFLOW_GENERATION,
            "debug": workflow_agent_pb2.STAGE_DEBUG,
            "completed": workflow_agent_pb2.STAGE_COMPLETED,
        }
        return mapping.get(stage, workflow_agent_pb2.STAGE_ERROR)

    def _proto_enum_to_stage(self, proto_enum: int) -> str:
        """Convert protobuf enum to stage string"""
        if not GRPC_AVAILABLE:
            return "clarification"

        mapping = {
            workflow_agent_pb2.STAGE_CLARIFICATION: "clarification",
            workflow_agent_pb2.STAGE_NEGOTIATION: "negotiation",
            workflow_agent_pb2.STAGE_GAP_ANALYSIS: "gap_analysis",
            workflow_agent_pb2.STAGE_ALTERNATIVE_GENERATION: "alternative_generation",
            workflow_agent_pb2.STAGE_WORKFLOW_GENERATION: "workflow_generation",
            workflow_agent_pb2.STAGE_DEBUG: "debug",
            workflow_agent_pb2.STAGE_COMPLETED: "completed",
        }
        return mapping.get(proto_enum, "clarification")


# Global gRPC client instance (MVP simplified)
workflow_client = WorkflowGRPCClient()


async def get_workflow_client() -> WorkflowGRPCClient:
    """Get workflow gRPC client instance"""
    return workflow_client
