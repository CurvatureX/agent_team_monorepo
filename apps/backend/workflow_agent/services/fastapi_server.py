"""
FastAPI Server for Workflow Agent
只实现 ProcessConversation 这一个接口，替换 gRPC 服务器
"""

import asyncio
import json
import os

# Import shared models
import sys
import time
from typing import AsyncGenerator, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from agents.state import WorkflowStage, WorkflowState

# Import workflow agent components
from agents.workflow_agent import WorkflowAgent
from core.config import settings
import logging
from services.state_manager import get_workflow_agent_state_manager

# Add parent directory to path for shared models
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))  # Go to apps/backend
sys.path.insert(0, parent_dir)

# 遥测组件
try:
    from shared.telemetry import setup_telemetry, TrackingMiddleware, MetricsMiddleware
except ImportError:
    # Fallback for deployment - create dummy implementations
    print("Warning: Could not import telemetry components, using stubs")
    def setup_telemetry(*args, **kwargs):
        pass
    class TrackingMiddleware:
        def __init__(self, app):
            self.app = app
        async def __call__(self, scope, receive, send):
            await self.app(scope, receive, send)
    class MetricsMiddleware:
        def __init__(self, app, **kwargs):
            self.app = app
        async def __call__(self, scope, receive, send):
            await self.app(scope, receive, send)

# shared models导入（两种环境都相同）
from shared.models.conversation import (
    ConversationRequest,
    ConversationResponse,
    ErrorContent,
    ResponseType,
    StatusChangeContent,
)

logger = logging.getLogger(__name__)


class WorkflowAgentServicer:
    """
    Workflow Agent FastAPI 服务实现
    基于 gRPC 实现的相同逻辑，转换为 FastAPI 流式接口
    内部管理 workflow_agent_state，对外提供简洁的对话接口
    """

    def __init__(self):
        logger.info("Initializing WorkflowAgentServicer")
        self.workflow_agent = WorkflowAgent()
        self.state_manager = get_workflow_agent_state_manager()
        logger.info("WorkflowAgentServicer initialized with database state management")

    async def process_conversation(self, request: ConversationRequest) -> AsyncGenerator[str, None]:
        """
        处理对话的统一接口 - 支持所有工作流生成阶段
        内部管理 workflow_agent_state，对外提供流式响应
        完全复刻 gRPC 服务的逻辑
        """
        try:
            logger.info(f"Request: {request}")
            session_id = request.session_id
            current_state = self.state_manager.get_state_by_session(
                session_id, request.access_token
            )

            if not current_state:
                # 创建新的 workflow_agent_state 记录
                workflow_context = None
                if request.workflow_context:
                    workflow_context = {
                        "origin": request.workflow_context.origin,
                        "source_workflow_id": request.workflow_context.source_workflow_id,
                    }
                state_id = self.state_manager.create_state(
                    session_id=session_id,
                    user_id=request.user_id or "anonymous",
                    initial_stage=WorkflowStage.CLARIFICATION,
                    workflow_context=workflow_context,
                    access_token=request.access_token,
                )

                if not state_id:
                    raise Exception("Failed to create workflow_agent_state")

                # 重新获取创建的状态
                current_state = self.state_manager.get_state_by_session(
                    session_id, request.access_token
                )
                logger.info(f"Created new workflow_agent_state for session {session_id}")
            else:
                logger.info(f"Retrieved existing workflow_agent_state for session {session_id}")

            # 添加用户消息到对话历史
            conversations = current_state.get("conversations", [])
            if request.user_message:
                conversations.append(
                    {
                        "role": "user",
                        "text": request.user_message,
                        "timestamp": int(time.time() * 1000),
                    }
                )
                current_state["conversations"] = conversations

            logger.info(f"Current stage: {current_state.get('stage', 'unknown')}")

            # 通过 LangGraph 处理状态 - 使用真正的 workflow_agent
            try:
                # 转换状态格式为 LangGraph WorkflowState
                workflow_state = self._convert_to_workflow_state(current_state)
                previous_stage = workflow_state.get("stage")
                
                # 使用标志变量控制外层循环
                should_continue = True
                
                # 使用 LangGraph 流式处理
                logger.info(f"Starting LangGraph streaming for session {session_id}")
                async for step_state in self.workflow_agent.graph.astream(workflow_state):
                    # 检查是否应该继续
                    if not should_continue:
                        logger.info(f"Breaking out of LangGraph stream for session {session_id}")
                        break
                    
                    for node_name, updated_state in step_state.items():
                        logger.info(
                            f"LangGraph node execution completed",
                            session_id=session_id,
                            node_name=node_name,
                            current_stage=updated_state.get("stage")
                        )
                        
                        # 发送状态变化信息
                        if node_name != "router":
                            status_change_response = self._create_status_change_response(
                                session_id, node_name, previous_stage, updated_state
                            )
                            yield f"data: {status_change_response.model_dump_json()}\n\n"

                        # 只在特定阶段发送消息响应
                        current_stage = updated_state.get("stage", WorkflowStage.CLARIFICATION)
                        if current_stage in [WorkflowStage.NEGOTIATION]:
                            message_response = await self._create_message_response(
                                session_id, updated_state
                            )
                            if message_response:
                                yield f"data: {message_response.model_dump_json()}\n\n"

                        # 如果是工作流生成完成，发送工作流响应
                        if current_stage == WorkflowStage.WORKFLOW_GENERATION:
                            workflow_response = await self._create_workflow_response(
                                session_id, updated_state
                            )
                            if workflow_response:
                                yield f"data: {workflow_response.model_dump_json()}\n\n"

                        # 更新状态跟踪
                        previous_stage = current_stage
                        current_state = self._convert_from_workflow_state(updated_state)
                        
                        # 检查是否应该终止 workflow
                        if self._should_terminate_workflow(updated_state):
                            logger.info(
                                f"Workflow termination triggered",
                                session_id=session_id,
                                node_name=node_name,
                                stage=current_stage
                            )
                            should_continue = False
                            break
                
                logger.info(
                    f"LangGraph streaming completed",
                    session_id=session_id,
                    final_stage=current_state.get("stage"),
                    was_terminated=not should_continue
                )

                # 保存更新后的状态到数据库
                success = self.state_manager.save_full_state(
                    session_id=session_id,
                    workflow_state=current_state,
                    access_token=request.access_token,
                )
                if success:
                    logger.info(f"Saved updated workflow_agent_state for session {session_id}")
                else:
                    logger.error(f"Failed to save workflow_agent_state for session {session_id}")

            except GeneratorExit:
                # 客户端断开连接时的正常处理
                logger.info(
                    f"Client disconnected during workflow processing",
                    session_id=session_id,
                    current_stage=current_state.get("stage")
                )
                # 保存当前状态
                try:
                    self.state_manager.save_full_state(
                        session_id=session_id,
                        workflow_state=current_state,
                        access_token=request.access_token
                    )
                except Exception as save_error:
                    logger.error(f"Failed to save state on disconnect: {save_error}")
                raise  # 重新抛出 GeneratorExit
                
            except Exception as processing_error:
                logger.error(
                    f"Error in workflow processing",
                    session_id=session_id,
                    error=str(processing_error),
                    error_type=type(processing_error).__name__
                )
                
                # 尝试保存错误状态
                try:
                    current_state["error"] = str(processing_error)
                    current_state["error_stage"] = current_state.get("stage", "unknown")
                    self.state_manager.save_full_state(
                        session_id=session_id,
                        workflow_state=current_state,
                        access_token=request.access_token
                    )
                except Exception as save_error:
                    logger.error(f"Failed to save error state: {save_error}")
                
                error_response = ConversationResponse(
                    session_id=session_id,
                    response_type=ResponseType.ERROR,
                    error=ErrorContent(
                        error_code="PROCESSING_ERROR",
                        message=f"Error processing workflow: {str(processing_error)}",
                        details=str(processing_error),
                        is_recoverable=True,
                    ),
                    is_final=True,
                )
                yield f"data: {error_response.model_dump_json()}\n\n"
            
            finally:
                # 清理逻辑
                logger.info(
                    f"Workflow processing cleanup",
                    session_id=session_id,
                    final_stage=current_state.get("stage")
                )

        except Exception as e:
            import traceback

            error_traceback = traceback.format_exc()
            logger.error(
                f"Failed to process conversation: {str(e)}",
                session_id=request.session_id,
                traceback=error_traceback,
            )

            # 发送错误响应
            error_response = ConversationResponse(
                session_id=request.session_id,
                response_type=ResponseType.ERROR,
                error=ErrorContent(
                    error_code="INTERNAL_ERROR",
                    message=f"Failed to process conversation: {str(e)}",
                    details=str(e),
                    is_recoverable=True,
                ),
                is_final=True,
            )
            yield f"data: {error_response.model_dump_json()}\n\n"

    def _convert_to_workflow_state(self, db_state: dict) -> WorkflowState:
        """将数据库状态转换为 LangGraph WorkflowState"""
        workflow_state: WorkflowState = {
            "session_id": db_state.get("session_id", ""),
            "user_id": db_state.get("user_id", "anonymous"),
            "created_at": db_state.get("created_at", int(time.time() * 1000)),
            "updated_at": db_state.get("updated_at", int(time.time() * 1000)),
            "stage": WorkflowStage(db_state.get("stage", "clarification")),
            "intent_summary": db_state.get("intent_summary", ""),
            "execution_history": db_state.get("execution_history", []),
            "clarification_context": db_state.get(
                "clarification_context", {"origin": "create", "pending_questions": []}
            ),
            "conversations": db_state.get("conversations", []),
            "gaps": db_state.get("gaps", []),
            "alternatives": db_state.get("alternatives", []),
            "current_workflow": {},
            "debug_result": db_state.get("debug_result", ""),
            "debug_loop_count": db_state.get("debug_loop_count", 0),
        }

        # 处理 current_workflow
        current_workflow = db_state.get("current_workflow")
        if isinstance(current_workflow, str) and current_workflow:
            try:
                workflow_state["current_workflow"] = json.loads(current_workflow)
            except json.JSONDecodeError:
                workflow_state["current_workflow"] = {}
        elif isinstance(current_workflow, dict):
            workflow_state["current_workflow"] = current_workflow
        else:
            workflow_state["current_workflow"] = {}

        return workflow_state

    def _convert_from_workflow_state(self, workflow_state: WorkflowState) -> dict:
        """将 LangGraph WorkflowState 转换为数据库状态"""
        db_state = dict(workflow_state)

        # 确保stage 是字符串
        if isinstance(db_state.get("stage"), WorkflowStage):
            db_state["stage"] = db_state["stage"].value

        return db_state

    def _create_status_change_response(
        self,
        session_id: str,
        node_name: str,
        previous_stage: Optional[WorkflowStage],
        current_state: WorkflowState,
    ) -> ConversationResponse:
        """创建状态变化响应"""
        current_stage = current_state.get("stage", WorkflowStage.CLARIFICATION)
        
        # 准备 stage_state 内容（不包含敏感信息）
        stage_state = {
            "session_id": current_state.get("session_id", session_id),
            "stage": (
                current_stage.value
                if isinstance(current_stage, WorkflowStage)
                else str(current_stage)
            ),
            "intent_summary": current_state.get("intent_summary", ""),
            "gaps": current_state.get("gaps", []),
            "alternatives": current_state.get("alternatives", []),
            "debug_result": current_state.get("debug_result", ""),
            "debug_loop_count": current_state.get("debug_loop_count", 0),
            "conversations_count": len(current_state.get("conversations", [])),
            "has_workflow": bool(current_state.get("current_workflow", {})),
        }

        return ConversationResponse(
            session_id=session_id,
            response_type=ResponseType.STATUS_CHANGE,
            is_final=False,
            status_change=StatusChangeContent(
                previous_stage=(
                    previous_stage.value
                    if previous_stage and isinstance(previous_stage, WorkflowStage)
                    else (str(previous_stage) if previous_stage else None)
                ),
                current_stage=(
                    current_stage.value
                    if isinstance(current_stage, WorkflowStage)
                    else str(current_stage)
                ),
                stage_state=stage_state,
                node_name=node_name,
            ),
        )

    async def _create_message_response(
        self, session_id: str, state: WorkflowState
    ) -> Optional[ConversationResponse]:
        """创建消息响应（仅限 clarification 和 alternative 阶段）"""
        conversations = state.get("conversations", [])

        # 获取最后一条 assistant 消息
        for conv in reversed(conversations):
            if conv.get("role") == "assistant":
                return ConversationResponse(
                    session_id=session_id,
                    response_type=ResponseType.MESSAGE,
                    message=conv.get("text", ""),
                    is_final=True,
                )

        return None

    async def _create_workflow_response(
        self, session_id: str, state: WorkflowState
    ) -> Optional[ConversationResponse]:
        """创建工作流响应"""
        current_workflow = state.get("current_workflow", {})

        if (
            current_workflow
            and isinstance(current_workflow, dict)
            and current_workflow.get("nodes")
        ):
            workflow_json = json.dumps(current_workflow)
            return ConversationResponse(
                session_id=session_id,
                response_type=ResponseType.WORKFLOW,
                workflow=workflow_json,
                is_final=False,
            )

        return None
    
    def _should_terminate_workflow(self, state: WorkflowState) -> bool:
        """
        判断是否应该终止 workflow 执行
        
        Args:
            state: 当前的 workflow 状态
            
        Returns:
            bool: True 表示应该终止，False 表示继续
        """
        current_stage = state.get("stage")
        
        # 定义应该终止的状态
        terminal_stages = [
            WorkflowStage.COMPLETED,
            WorkflowStage.NEGOTIATION  # 根据业务需求，negotiation 阶段也可能需要终止
        ]
        
        if current_stage in terminal_stages:
            logger.info(
                f"Workflow reached terminal stage: {current_stage}",
                session_id=state.get("session_id", "unknown"),
                stage=current_stage.value if hasattr(current_stage, 'value') else str(current_stage)
            )
            return True
            
        # 可以添加其他终止条件，比如错误次数过多
        debug_loop_count = state.get("debug_loop_count", 0)
        if debug_loop_count > 5:  # 防止无限循环
            logger.warning(
                f"Debug loop count exceeded limit: {debug_loop_count}",
                session_id=state.get("session_id", "unknown")
            )
            return True
            
        return False


# 创建 FastAPI 应用
app = FastAPI(
    title="Workflow Agent API",
    description="工作流代理服务 - ProcessConversation 接口",
    version="1.0.0",
)

# 初始化遥测系统
setup_telemetry(app, service_name="workflow-agent", service_version="1.0.0")

# 添加遥测中间件
app.add_middleware(TrackingMiddleware)  # type: ignore
app.add_middleware(MetricsMiddleware, service_name="workflow-agent")  # type: ignore

# 创建服务器实例
servicer = WorkflowAgentServicer()


@app.post("/process-conversation")
async def process_conversation(request: ConversationRequest):
    """
    ProcessConversation 接口 - 对应原来的 gRPC 方法
    返回流式响应
    """
    return StreamingResponse(
        servicer.process_conversation(request),
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
    import os

    import uvicorn

    port = getattr(settings, "FASTAPI_PORT", None) or int(os.getenv("FASTAPI_PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
