"""
HTTP Client for Workflow Agent Service
Replaces the gRPC client with HTTP/FastAPI calls
"""

import asyncio
import json
import time
from typing import Any, AsyncGenerator, Dict, Optional

import httpx
from app.core.config import get_settings
from shared.logging_config import get_logger

settings = get_settings()
logger = get_logger(__name__)


class WorkflowAgentHTTPClient:
    """
    HTTP client for the Workflow Agent FastAPI service
    Replaces the gRPC ProcessConversation interface with HTTP calls
    """

    def __init__(self):
        self.base_url = settings.WORKFLOW_AGENT_URL or f"http://{settings.WORKFLOW_AGENT_HOST}:8001"
        # Increased timeout for streaming operations and RAG embedding generation
        self.timeout = httpx.Timeout(
            timeout=300.0,  # 5 minutes total timeout
            connect=10.0,   # 10 seconds connection timeout
            read=60.0,      # 60 seconds read timeout per chunk
            write=30.0      # 30 seconds write timeout
        )
        self.connected = False
        # Add connection pooling for better connection reuse
        self.limits = httpx.Limits(
            max_keepalive_connections=5,
            max_connections=10,
            keepalive_expiry=30.0
        )

    async def connect(self):
        """Test connection to workflow agent service"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/health")
                response.raise_for_status()
                self.connected = True
                logger.info(f"✅ Connected to Workflow Agent at {self.base_url}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Workflow Agent: {e}")
            self.connected = False
            raise

    async def close(self):
        """Close HTTP connection (no-op for HTTP)"""
        self.connected = False
        logger.info("Closed Workflow Agent HTTP connection")


    async def process_conversation_stream(
        self,
        session_id: str,
        user_message: str,
        user_id: str = "anonymous",
        workflow_context: Optional[Dict[str, Any]] = None,
        access_token: Optional[str] = None,
        tracking_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process conversation using HTTP POST to /process-conversation
        Returns streaming responses via Server-Sent Events
        """
        if not self.connected:
            await self.connect()

        try:
            # Prepare HTTP request - 符合最新的 ConversationRequest 模型
            request_data = {
                "session_id": session_id,
                "user_id": user_id,
                "user_message": user_message,
                "access_token": access_token or "",
            }
            
            # 正确处理 workflow_context - 需要匹配 WorkflowContext 模型
            if workflow_context:
                request_data["workflow_context"] = {
                    "origin": workflow_context.get("origin", "create"),
                    "source_workflow_id": workflow_context.get("source_workflow_id", "")
                }

            logger.info(f"📨 Sending HTTP request to {self.base_url}/process-conversation")

            # Stream conversation processing via HTTP SSE with connection pooling
            async with httpx.AsyncClient(
                timeout=self.timeout,
                limits=self.limits,
                http2=True  # Enable HTTP/2 for better streaming
            ) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/process-conversation",
                    json=request_data,
                    headers={
                        "Accept": "text/event-stream",
                        "Content-Type": "application/json",
                        "Connection": "keep-alive",
                        "Cache-Control": "no-cache",
                        "X-Tracking-ID": tracking_id or "",  # 传递 tracking_id
                    },
                ) as response:
                    response.raise_for_status()

                    # Process stream lines with better cancellation handling
                    try:
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                try:
                                    data = json.loads(line[6:])  # Remove "data: " prefix
                                    yield data
                                except json.JSONDecodeError as e:
                                    logger.error(f"❌ Error parsing SSE data: {e}")
                                    continue
                    except asyncio.CancelledError:
                        logger.info("Client disconnected during streaming")
                        # Re-raise to maintain proper cancellation semantics
                        raise

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ HTTP error in process_conversation_stream: {e.response.status_code}")
            # Yield error response - 符合 ConversationResponse 格式
            yield {
                "session_id": session_id,
                "response_type": "RESPONSE_TYPE_ERROR",
                "is_final": True,
                "error": {
                    "error_code": f"HTTP_{e.response.status_code}",
                    "message": f"HTTP request failed: {e.response.status_code}",
                    "details": str(e),
                    "is_recoverable": True,
                }
            }
        except Exception as e:
            logger.error(f"❌ Error in process_conversation_stream: {e}")
            # Yield error response - 符合 ConversationResponse 格式
            yield {
                "session_id": session_id,
                "response_type": "RESPONSE_TYPE_ERROR",
                "is_final": True,
                "error": {
                    "error_code": "INTERNAL_ERROR",
                    "message": f"Failed to process conversation: {str(e)}",
                    "details": str(e),
                    "is_recoverable": True,
                }
            }


# Global HTTP client instance
workflow_agent_client = WorkflowAgentHTTPClient()


async def get_workflow_agent_client() -> WorkflowAgentHTTPClient:
    """Get workflow agent HTTP client instance"""
    return workflow_agent_client
