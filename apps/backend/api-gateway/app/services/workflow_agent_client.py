"""
Workflow Agent HTTP Client
调用 FastAPI ProcessConversation 接口，替换 gRPC 客户端
"""

import httpx
import json
import logging
from typing import AsyncGenerator, Dict, Any, Optional

from app.core.config import get_settings
from app.models import ConversationRequest, ConversationResponse

logger = logging.getLogger(__name__)
settings = get_settings()


class WorkflowAgentClient:
    """
    工作流代理 HTTP 客户端
    只调用 ProcessConversation 接口
    """
    
    def __init__(self):
        # 使用配置中的 HTTP URL
        self.base_url = settings.workflow_agent_http_url
        self.timeout = httpx.Timeout(connect=5.0, read=300.0, write=10.0, pool=2.0)
        logger.info(f"Workflow Agent HTTP Client initialized: {self.base_url}")
    
    async def process_conversation_stream(
        self,
        session_id: str,
        user_message: str,
        user_id: str = "anonymous",
        workflow_context: Optional[Dict[str, Any]] = None,
        access_token: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        调用 ProcessConversation 接口
        保持与原 gRPC 客户端相同的接口签名
        """
        try:
            # 构建请求
            request = ConversationRequest(
                session_id=session_id,
                user_id=user_id,
                access_token=access_token or "",
                user_message=user_message,
                workflow_context=workflow_context
            )
            
            logger.info(f"Calling ProcessConversation for session {session_id}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/process-conversation",
                    json=request.model_dump(),
                    headers={"Content-Type": "application/json"}
                ) as response:
                    
                    if response.status_code != 200:
                        logger.error(f"HTTP error: {response.status_code}")
                        yield {
                            "type": "error",
                            "session_id": session_id,
                            "error": {
                                "error_code": f"HTTP_{response.status_code}",
                                "message": f"HTTP error: {response.status_code}",
                                "details": await response.aread(),
                                "is_recoverable": False
                            },
                            "is_final": True,
                            "response_type": "error"
                        }
                        return
                    
                    # 处理 Server-Sent Events 流
                    async for line in response.aiter_lines():
                        line = line.strip()
                        if line.startswith("data: "):
                            try:
                                data = line[6:]  # 移除 "data: " 前缀
                                response_data = json.loads(data)
                                
                                # 转换为与 gRPC 客户端兼容的格式
                                converted_response = self._convert_to_grpc_format(response_data)
                                yield converted_response
                                
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to parse SSE data: {e}")
                                continue
                            except Exception as e:
                                logger.error(f"Error processing SSE line: {e}")
                                continue
                                
        except Exception as e:
            logger.error(f"Error in process_conversation_stream: {e}")
            yield {
                "type": "error",
                "session_id": session_id,
                "error": {
                    "error_code": "CONNECTION_ERROR",
                    "message": f"Failed to connect to workflow agent: {str(e)}",
                    "details": str(e),
                    "is_recoverable": True
                },
                "is_final": True,
                "response_type": "error"
            }
    
    def _convert_to_grpc_format(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        将 FastAPI 响应转换为与原 gRPC 客户端兼容的格式
        保持 API Gateway 中现有代码的兼容性
        """
        try:
            # 基础响应格式
            converted = {
                "session_id": response_data.get("session_id"),
                "is_final": response_data.get("is_final", False),
            }
            
            # 根据响应类型设置相应字段
            response_type = response_data.get("response_type")
            
            if response_type == "RESPONSE_TYPE_MESSAGE" and response_data.get("message"):
                converted.update({
                    "type": "message",
                    "response_type": "message",
                    "message": response_data["message"]
                })
            elif response_type == "RESPONSE_TYPE_WORKFLOW" and response_data.get("workflow"):
                converted.update({
                    "type": "workflow",
                    "response_type": "workflow", 
                    "workflow": response_data["workflow"]
                })
            elif response_type == "RESPONSE_TYPE_ERROR" and response_data.get("error"):
                converted.update({
                    "type": "error",
                    "response_type": "error",
                    "error": response_data["error"]
                })
            else:
                # 未知类型，默认为消息
                converted.update({
                    "type": "message",
                    "response_type": "message",
                    "message": str(response_data)
                })
            
            return converted
            
        except Exception as e:
            logger.error(f"Error converting response format: {e}")
            return {
                "type": "error",
                "session_id": response_data.get("session_id", "unknown"),
                "error": {
                    "error_code": "CONVERSION_ERROR",
                    "message": "Failed to convert response format",
                    "details": str(e),
                    "is_recoverable": True
                },
                "is_final": True,
                "response_type": "error"
            }


# 全局客户端实例
_client_instance: Optional[WorkflowAgentClient] = None


async def get_workflow_client() -> WorkflowAgentClient:
    """获取工作流代理客户端实例"""
    global _client_instance
    if _client_instance is None:
        _client_instance = WorkflowAgentClient()
    return _client_instance