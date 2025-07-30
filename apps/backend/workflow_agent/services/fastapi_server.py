"""
FastAPI Server for Workflow Agent
只实现 ProcessConversation 这一个接口，替换 gRPC 服务器
"""

import json
import os

# 统一导入路径管理
import sys
import time
from pathlib import Path
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

# 设置shared models导入路径
if os.path.exists("/app/shared"):  # Docker 环境
    if "/app" not in sys.path:
        sys.path.insert(0, "/app")
    # Docker环境下使用相对导入
    from agents.state import WorkflowOrigin, WorkflowStage, WorkflowState
    from agents.workflow_agent import WorkflowAgent
    from core.config import settings
else:  # 本地开发环境
    backend_dir = Path(__file__).parent.parent.parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    # 本地环境下使用完整路径导入
    from workflow_agent.agents.state import WorkflowOrigin, WorkflowStage, WorkflowState
    from workflow_agent.agents.workflow_agent import WorkflowAgent
    from workflow_agent.core.config import settings

# shared models导入（两种环境都相同）
from shared.models.conversation import (
    ConversationRequest,
    ConversationResponse,
    ErrorContent,
    ResponseType,
)

logger = structlog.get_logger()


class FastAPIWorkflowServer:
    """FastAPI 工作流服务器 - 只实现 ProcessConversation"""

    def __init__(self):
        self.workflow_agent = WorkflowAgent()
        logger.info("FastAPI Workflow Server initialized")

    async def process_conversation_stream(
        self, request: ConversationRequest
    ) -> AsyncGenerator[str, None]:
        """
        ProcessConversation 的流式实现
        返回 Server-Sent Events 格式的流
        """
        try:
            logger.info(f"Processing conversation for session {request.session_id}")

            # 转换请求为内部状态格式
            state: WorkflowState = {
                "session_id": request.session_id,
                "user_id": request.user_id,
                "created_at": int(time.time() * 1000),
                "updated_at": int(time.time() * 1000),
                "stage": WorkflowStage.CLARIFICATION,
                "intent_summary": "",
                "clarification_context": {"origin": WorkflowOrigin.CREATE, "pending_questions": []},
                "conversations": [
                    {
                        "role": "user",
                        "text": request.user_message,
                        "timestamp": int(time.time() * 1000),
                    }
                ],
                "gaps": [],
                "alternatives": [],
                "current_workflow": {},
                "debug_result": "",
                "debug_loop_count": 0,
            }

            # 如果有工作流上下文，设置相应字段
            if request.workflow_context:
                # 这里根据实际的 WorkflowAgent 实现来设置状态
                pass

            # 调用现有的 LangGraph 工作流代理
            try:
                # 使用现有的工作流代理处理
                async for chunk in self.workflow_agent.astream(state):
                    # 转换 LangGraph 输出为 ConversationResponse 格式
                    for node_name, node_output in chunk.items():
                        # 处理不同类型的输出
                        if isinstance(node_output, dict) and hasattr(node_output, "get"):
                            response = self._convert_to_conversation_response(
                                request.session_id, node_name, node_output
                            )
                            if response:
                                yield f"data: {response.model_dump_json()}\n\n"
                        elif isinstance(node_output, str):
                            # 处理字符串输出（通常是错误信息）
                            response = ConversationResponse(
                                session_id=request.session_id,
                                response_type=ResponseType.MESSAGE,
                                is_final=False,
                                message=f"节点 {node_name}: {node_output}",
                            )
                            yield f"data: {response.model_dump_json()}\n\n"
                        else:
                            # 处理其他类型的输出
                            logger.warning(
                                f"Unknown node output type for {node_name}: {type(node_output)}"
                            )
                            response = ConversationResponse(
                                session_id=request.session_id,
                                response_type=ResponseType.MESSAGE,
                                is_final=False,
                                message=f"处理节点 {node_name}...",
                            )
                            yield f"data: {response.model_dump_json()}\n\n"

                # 发送最终响应
                final_response = ConversationResponse(
                    session_id=request.session_id,
                    response_type=ResponseType.MESSAGE,
                    is_final=True,
                    message="工作流处理完成",
                )
                yield f"data: {final_response.model_dump_json()}\n\n"

            except Exception as e:
                logger.error(f"Error in workflow processing: {e}")
                error_response = ConversationResponse(
                    session_id=request.session_id,
                    response_type=ResponseType.ERROR,
                    is_final=True,
                    error=ErrorContent(
                        error_code="WORKFLOW_ERROR",
                        message=str(e),
                        details=f"Error in workflow processing: {e}",
                        is_recoverable=True,
                    ),
                )
                yield f"data: {error_response.model_dump_json()}\n\n"

        except Exception as e:
            logger.error(f"Error in process_conversation_stream: {e}")
            error_response = ConversationResponse(
                session_id=request.session_id,
                response_type=ResponseType.ERROR,
                is_final=True,
                error=ErrorContent(
                    error_code="INTERNAL_ERROR",
                    message="Internal server error",
                    details=str(e),
                    is_recoverable=False,
                ),
            )
            yield f"data: {error_response.model_dump_json()}\n\n"

    def _convert_to_conversation_response(
        self, session_id: str, node_name: str, node_output: dict
    ) -> ConversationResponse:
        """
        将 LangGraph 节点输出转换为 ConversationResponse
        """
        try:
            # 根据节点类型和输出内容决定响应类型
            if node_name == "designer" and "current_workflow_json" in node_output:
                # 工作流生成完成
                return ConversationResponse(
                    session_id=session_id,
                    response_type=ResponseType.WORKFLOW,
                    is_final=False,
                    workflow=node_output["current_workflow_json"],
                )
            elif "message" in node_output or "response" in node_output:
                # 普通消息响应
                message_text = node_output.get("message", node_output.get("response", ""))
                return ConversationResponse(
                    session_id=session_id,
                    response_type=ResponseType.MESSAGE,
                    is_final=False,
                    message=str(message_text),
                )

            # 默认返回空消息
            return ConversationResponse(
                session_id=session_id,
                response_type=ResponseType.MESSAGE,
                is_final=False,
                message="处理中...",
            )

        except Exception as e:
            logger.error(f"Error converting node output: {e}")
            return ConversationResponse(
                session_id=session_id,
                response_type=ResponseType.ERROR,
                is_final=False,
                error=ErrorContent(
                    error_code="CONVERSION_ERROR",
                    message="Error converting response",
                    details=str(e),
                    is_recoverable=True,
                ),
            )


# 创建 FastAPI 应用
app = FastAPI(
    title="Workflow Agent API", description="工作流代理服务 - ProcessConversation 接口", version="1.0.0"
)

# 创建服务器实例
server = FastAPIWorkflowServer()


@app.post("/process-conversation")
async def process_conversation(request: ConversationRequest):
    """
    ProcessConversation 接口 - 对应原来的 gRPC 方法
    返回流式响应
    """
    return StreamingResponse(
        server.process_conversation_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "workflow_agent_fastapi"}


if __name__ == "__main__":
    import uvicorn

    port = getattr(settings, "FASTAPI_PORT", None) or int(os.getenv("FASTAPI_PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
