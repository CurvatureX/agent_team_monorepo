"""
gRPC Client for Workflow Service - New ProcessConversation Interface
"""

import asyncio
import time
from typing import AsyncGenerator, Dict, Any, Optional
from app.config import settings
from app.utils import log_info, log_warning, log_error, log_debug
from app.services.state_manager import get_state_manager

# Import gRPC modules - using the protobuf files from shared/proto
try:
    import grpc
    import sys
    import os
    # Add shared proto directory to path
    shared_proto_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "shared", "proto")
    if shared_proto_path not in sys.path:
        sys.path.append(shared_proto_path)
    
    import workflow_agent_pb2
    import workflow_agent_pb2_grpc
    GRPC_AVAILABLE = True
    log_debug("gRPC modules loaded successfully")
except ImportError as e:
    log_warning(f"gRPC not available: {e}. Using mock client.")
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
                self.channel = grpc.aio.insecure_channel(f"{self.host}:{self.port}")
                self.stub = workflow_agent_pb2_grpc.WorkflowAgentStub(self.channel)
                
                # Test connection
                await asyncio.wait_for(
                    grpc.aio.channel_ready_future(self.channel), 
                    timeout=5.0
                )
                
                self.connected = True
                log_info(f"Connected to workflow service at {self.host}:{self.port}")
            else:
                # Mock connection for environments without gRPC
                await asyncio.sleep(0.1)
                self.connected = True
                log_info(f"Mock connected to workflow service at {self.host}:{self.port}")
                
        except Exception as e:
            log_error(f"Failed to connect to workflow service: {e}")
            self.connected = False
            raise
    
    async def close(self):
        """Close gRPC connection"""
        if self.channel:
            await self.channel.close()
        self.connected = False
        log_info("Closed workflow service connection")
    
    async def process_conversation_stream(
        self, 
        session_id: str, 
        user_message: str, 
        user_id: str = "anonymous",
        workflow_context: Optional[Dict[str, Any]] = None,
        access_token: Optional[str] = None
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
                current_state_data = self.state_manager.get_state_by_session(session_id, access_token)
                
                # Prepare gRPC request
                request = workflow_agent_pb2.ConversationRequest(
                    session_id=session_id,
                    user_id=user_id,
                    user_message=user_message
                )
                
                # Add workflow context if provided
                if workflow_context:
                    request.workflow_context.origin = workflow_context.get("origin", "create")
                    request.workflow_context.source_workflow_id = workflow_context.get("source_workflow_id", "")
                    request.workflow_context.modification_intent = workflow_context.get("modification_intent", "")
                
                # Add current state if exists
                if current_state_data:
                    # Convert database state to protobuf AgentState
                    agent_state = self._db_state_to_proto(current_state_data)
                    request.current_state.CopyFrom(agent_state)
                
                # Stream conversation processing
                async for response in self.stub.ProcessConversation(request):
                    # Convert protobuf response to dict
                    response_dict = self._proto_response_to_dict(response)
                    
                    # Save updated state to database if provided
                    if response.updated_state:
                        updated_state = self._proto_state_to_dict(response.updated_state)
                        self.state_manager.save_full_state(session_id, updated_state, access_token)
                    
                    yield response_dict
                    
            else:
                # Mock implementation for environments without gRPC
                async for response in self._mock_process_conversation(session_id, user_message, user_id):
                    yield response
                    
        except Exception as e:
            log_error(f"Error in process_conversation_stream: {e}")
            # Yield error response
            yield {
                "type": "error",
                "session_id": session_id,
                "error": {
                    "error_code": "INTERNAL_ERROR",
                    "message": f"Failed to process conversation: {str(e)}",
                    "details": str(e),
                    "is_recoverable": True
                },
                "timestamp": int(time.time() * 1000),
                "is_final": True
            }
    
    async def _mock_process_conversation(
        self, 
        session_id: str, 
        user_message: str, 
        user_id: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Mock implementation for testing without gRPC"""
        stages = [
            {
                "type": "status",
                "status": {
                    "new_stage": "clarification",
                    "previous_stage": "",
                    "stage_description": "Entering clarification stage",
                    "pending_actions": []
                },
                "is_final": False
            },
            {
                "type": "message",
                "message": {
                    "text": "I understand you want to create a workflow. Let me clarify your requirements.",
                    "role": "assistant",
                    "message_type": "text",
                    "metadata": {}
                },
                "is_final": False
            },
            {
                "type": "status", 
                "status": {
                    "new_stage": "gap_analysis",
                    "previous_stage": "clarification",
                    "stage_description": "Entering gap_analysis stage",
                    "pending_actions": []
                },
                "is_final": False
            },
            {
                "type": "message",
                "message": {
                    "text": "Analyzing your requirements to identify any capability gaps...",
                    "role": "assistant",
                    "message_type": "text",
                    "metadata": {}
                },
                "is_final": False
            },
            {
                "type": "status",
                "status": {
                    "new_stage": "workflow_generation", 
                    "previous_stage": "gap_analysis",
                    "stage_description": "Entering workflow_generation stage",
                    "pending_actions": []
                },
                "is_final": False
            },
            {
                "type": "message",
                "message": {
                    "text": "Generating your workflow...",
                    "role": "assistant", 
                    "message_type": "text",
                    "metadata": {"workflow_id": f"wf_{session_id[:8]}"}
                },
                "is_final": False
            },
            {
                "type": "message",
                "message": {
                    "text": "Workflow generation completed successfully!",
                    "role": "assistant",
                    "message_type": "text", 
                    "metadata": {"workflow_id": f"wf_{session_id[:8]}"}
                },
                "is_final": True
            }
        ]
        
        for stage in stages:
            stage.update({
                "session_id": session_id,
                "timestamp": int(time.time() * 1000)
            })
            yield stage
            await asyncio.sleep(0.8)
    
    def _db_state_to_proto(self, db_state: Dict[str, Any]) -> 'workflow_agent_pb2.AgentState':
        """Convert database state to protobuf AgentState"""
        if not GRPC_AVAILABLE:
            return None
            
        # This would use the StateConverter from workflow_agent service
        # For now, create a basic AgentState
        agent_state = workflow_agent_pb2.AgentState(
            session_id=db_state.get("session_id", ""),
            user_id=db_state.get("user_id", ""),
            created_at=db_state.get("created_at", int(time.time() * 1000)),
            updated_at=db_state.get("updated_at", int(time.time() * 1000)),
            stage=self._stage_to_proto_enum(db_state.get("stage", "clarification")),
            intent_summary=db_state.get("intent_summary", ""),
            gaps=db_state.get("gaps", []),
            current_workflow_json=db_state.get("current_workflow_json", ""),
            debug_result=db_state.get("debug_result", ""),
            debug_loop_count=db_state.get("debug_loop_count", 0),
            execution_history=db_state.get("execution_history", [])
        )
        
        # Add conversations if available
        conversations = db_state.get("conversations", [])
        if isinstance(conversations, str):
            import json
            conversations = json.loads(conversations)
        
        for conv in conversations:
            conversation = workflow_agent_pb2.Conversation(
                role=conv.get("role", "user"),
                text=conv.get("text", ""),
                timestamp=conv.get("timestamp", int(time.time() * 1000)),
                metadata=conv.get("metadata", {})
            )
            agent_state.conversations.append(conversation)
        
        return agent_state
    
    def _proto_response_to_dict(self, response: 'workflow_agent_pb2.ConversationResponse') -> Dict[str, Any]:
        """Convert protobuf ConversationResponse to dictionary"""
        result = {
            "session_id": response.session_id,
            "timestamp": response.timestamp,
            "is_final": response.is_final
        }
        
        # Handle different response types
        if response.type == workflow_agent_pb2.RESPONSE_MESSAGE:
            result["type"] = "message"
            result["message"] = {
                "text": response.message.text,
                "role": response.message.role,
                "message_type": response.message.message_type,
                "metadata": dict(response.message.metadata)
            }
            
            # Add questions if present
            if response.message.questions:
                result["message"]["questions"] = []
                for q in response.message.questions:
                    result["message"]["questions"].append({
                        "id": q.id,
                        "question": q.question,
                        "category": q.category,
                        "is_required": q.is_required,
                        "options": list(q.options)
                    })
            
            # Add alternatives if present  
            if response.message.alternatives:
                result["message"]["alternatives"] = []
                for alt in response.message.alternatives:
                    result["message"]["alternatives"].append({
                        "id": alt.id,
                        "title": alt.title,
                        "description": alt.description,
                        "approach": alt.approach,
                        "trade_offs": list(alt.trade_offs),
                        "complexity": alt.complexity
                    })
                    
        elif response.type == workflow_agent_pb2.RESPONSE_STATUS:
            result["type"] = "status"
            result["status"] = {
                "new_stage": self._proto_enum_to_stage(response.status.new_stage),
                "previous_stage": self._proto_enum_to_stage(response.status.previous_stage),
                "stage_description": response.status.stage_description,
                "pending_actions": list(response.status.pending_actions)
            }
            
        elif response.type == workflow_agent_pb2.RESPONSE_ERROR:
            result["type"] = "error"
            result["error"] = {
                "error_code": response.error.error_code,
                "message": response.error.message,
                "details": response.error.details,
                "is_recoverable": response.error.is_recoverable
            }
        
        return result
    
    def _proto_state_to_dict(self, agent_state: 'workflow_agent_pb2.AgentState') -> Dict[str, Any]:
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
            "debug_loop_count": agent_state.debug_loop_count
        }
        
        # Add conversations
        conversations = []
        for conv in agent_state.conversations:
            conversations.append({
                "role": conv.role,
                "text": conv.text,
                "timestamp": conv.timestamp,
                "metadata": dict(conv.metadata)
            })
        state_dict["conversations"] = conversations
        
        # Add alternatives
        alternatives = []
        for alt in agent_state.alternatives:
            alternatives.append({
                "id": alt.id,
                "title": alt.title,
                "description": alt.description,
                "approach": alt.approach,
                "trade_offs": list(alt.trade_offs),
                "complexity": alt.complexity
            })
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
            "completed": workflow_agent_pb2.STAGE_COMPLETED
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
            workflow_agent_pb2.STAGE_COMPLETED: "completed"
        }
        return mapping.get(proto_enum, "clarification")


# Global gRPC client instance (MVP simplified)
workflow_client = WorkflowGRPCClient()


async def get_workflow_client() -> WorkflowGRPCClient:
    """Get workflow gRPC client instance"""
    return workflow_client