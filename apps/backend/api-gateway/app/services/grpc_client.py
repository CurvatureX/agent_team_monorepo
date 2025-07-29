"""
gRPC Client for Workflow Service - Updated ProcessConversation Interface
根据最新的 workflow_agent.proto 实现简化的统一接口
"""

import asyncio
import time
from typing import Any, AsyncGenerator, Dict, Optional

from app.core.config import get_settings
settings = get_settings()

import grpc
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
    根据最新 proto 定义，workflow_agent_state 由 workflow_agent 服务管理
    api-gateway 只负责传参和返回，不做状态管理
    """

    def __init__(self):
        self.host = settings.WORKFLOW_AGENT_HOST
        self.port = settings.WORKFLOW_AGENT_PORT
        self.channel = None
        self.stub = None
        self.connected = False

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
        Process conversation using the unified ProcessConversation interface
        根据最新 proto 定义实现简化的流式处理

        Args:
            session_id: Session identifier
            user_message: User's message
            user_id: User identifier (not used in new proto)
            workflow_context: WorkflowContext (origin, source_workflow_id)
            access_token: User's JWT token

        Yields:
            Streaming responses from the workflow agent
        """
        if not self.connected:
            await self.connect()

        try:
            if GRPC_AVAILABLE:
                # Prepare gRPC request - 根据新的 proto 定义
                request = workflow_agent_pb2.ConversationRequest(
                    session_id=session_id,
                    user_id=user_id,
                    access_token=access_token or "",
                    user_message=user_message
                )

                # Add workflow context if provided
                if workflow_context and isinstance(workflow_context, dict):
                    try:
                        context = workflow_agent_pb2.WorkflowContext()
                        context.origin = str(workflow_context.get("origin", "create"))
                        context.source_workflow_id = str(
                            workflow_context.get("source_workflow_id", "")
                        )
                        request.workflow_context.CopyFrom(context)
                    except Exception as e:
                        logger.error(f"Error setting workflow_context in request: {e}")

                logger.info(f"About to call ProcessConversation with request: {request}")

                # Stream conversation processing
                try:
                    async for response in self.stub.ProcessConversation(request):
                        # Convert protobuf response to dict
                        response_dict = self._proto_response_to_dict(response)
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

    def _proto_response_to_dict(self, response) -> Dict[str, Any]:
        """Convert protobuf ConversationResponse to dictionary - 根据新 proto 定义"""
        result = {
            "session_id": response.session_id,
            "is_final": response.is_final,
        }

        # Handle different response types based on oneof response field
        if response.HasField("message"):
            result["type"] = "message"
            result["message"] = response.message
        elif response.HasField("workflow"):
            result["type"] = "workflow"
            result["workflow"] = response.workflow
        elif response.HasField("error"):
            result["type"] = "error"
            result["error"] = {
                "error_code": response.error.error_code,
                "message": response.error.message,
                "details": response.error.details,
                "is_recoverable": response.error.is_recoverable,
            }
        else:
            result["type"] = "unknown"

        # Handle response_type enum
        if response.response_type == workflow_agent_pb2.RESPONSE_TYPE_MESSAGE:
            result["response_type"] = "message"
        elif response.response_type == workflow_agent_pb2.RESPONSE_TYPE_WORKFLOW:
            result["response_type"] = "workflow"
        elif response.response_type == workflow_agent_pb2.RESPONSE_TYPE_ERROR:
            result["response_type"] = "error"
        else:
            result["response_type"] = "unknown"

        return result


# Global gRPC client instance (MVP simplified)
workflow_client = WorkflowGRPCClient()


async def get_workflow_client() -> WorkflowGRPCClient:
    """Get workflow gRPC client instance"""
    return workflow_client