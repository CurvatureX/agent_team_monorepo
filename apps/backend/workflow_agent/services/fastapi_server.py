"""
FastAPI Server for Workflow Agent
只实现 ProcessConversation 这一个接口
"""

import asyncio
import json
import logging
import os

# Import shared models
import sys
import time
from typing import TYPE_CHECKING, Any, AsyncGenerator, Optional

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

from workflow_agent.agents.state import WorkflowStage, WorkflowState

# Import workflow agent components
from workflow_agent.agents.workflow_agent import WorkflowAgent
from workflow_agent.core.config import settings
from workflow_agent.services.state_manager import get_workflow_agent_state_manager

# Add parent directory to path for shared models
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))  # Go to apps/backend
sys.path.insert(0, parent_dir)

# shared models导入（两种环境都相同）
from shared.models.conversation import (  # noqa: E402
    ConversationRequest,
    ConversationResponse,
    ErrorContent,
    ResponseType,
    StatusChangeContent,
)

# Initialize TELEMETRY_AVAILABLE variable
TELEMETRY_AVAILABLE = False

if TYPE_CHECKING:
    from shared.telemetry import MetricsMiddleware as TelemetryMetricsMiddleware
    from shared.telemetry import TrackingMiddleware as TelemetryTrackingMiddleware
    from shared.telemetry import setup_telemetry as telemetry_setup

    MetricsMiddleware = TelemetryMetricsMiddleware
    TrackingMiddleware = TelemetryTrackingMiddleware
    setup_telemetry = telemetry_setup
else:
    try:
        from shared.telemetry import (
            MetricsMiddleware,
            TrackingMiddleware,
            setup_telemetry,
        )
        TELEMETRY_AVAILABLE = True
    except ImportError:
        # Fallback for deployment - create dummy implementations
        print("Warning: Could not import telemetry components, using stubs")

        def setup_telemetry(*args: Any, **kwargs: Any) -> None:
            pass

        class TrackingMiddleware:
            def __init__(self, app: Any) -> None:
                self.app = app

            async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
                await self.app(scope, receive, send)

        class MetricsMiddleware:
            def __init__(self, app: Any, **kwargs: Any) -> None:
                self.app = app

            async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
                await self.app(scope, receive, send)

logger = logging.getLogger(__name__)


class WorkflowAgentServicer:
    """
    Workflow Agent FastAPI 服务实现
    内部管理 workflow_agent_state，对外提供简洁的对话接口
    """

    def __init__(self):
        logger.info("Initializing WorkflowAgentServicer")
        self.workflow_agent = WorkflowAgent()
        self.state_manager = get_workflow_agent_state_manager()
        logger.info("WorkflowAgentServicer initialized with database state management")

    async def process_conversation(
        self, request: ConversationRequest, request_obj: Optional[Request] = None
    ) -> AsyncGenerator[str, None]:
        """
        处理对话的统一接口 - 支持所有工作流生成阶段
        内部管理 workflow_agent_state，对外提供流式响应
        """
        generator_created = False
        try:
            # 获取 trace_id（如果有的话）
            trace_id = getattr(request_obj.state, "trace_id", None) if request_obj else None

            logger.info(
                "Processing conversation request",
                extra={
                    "request_session_id": request.session_id,
                    "request_user_id": request.user_id,
                    "trace_id": trace_id,
                },
            )
            session_id = request.session_id
            generator_created = True
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
                logger.info("Created new workflow_agent_state", extra={"session_id": session_id})
            else:
                logger.info(
                    "Retrieved existing workflow_agent_state", extra={"session_id": session_id}
                )

            # 添加用户消息到对话历史
            # Handle case where current_state is None due to database access issues
            if current_state is None:
                current_state = {
                    "session_id": session_id,
                    "user_id": request.user_id or "anonymous",
                    "stage": "clarification",
                    "intent_summary": "",
                    "conversations": [],
                    "current_workflow": {},
                }
                logger.warning("Using fallback state due to database access failure", 
                             extra={"session_id": session_id})
            
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

            # 通过 LangGraph 处理状态 - 使用真正的 workflow_agent
            try:
                # 转换状态格式为 LangGraph WorkflowState
                workflow_state = self._convert_to_workflow_state(current_state)
                previous_stage = workflow_state.get("stage")

                # 使用 LangGraph 流式处理
                logger.info(
                    "Starting LangGraph streaming",
                    extra={"session_id": session_id, "initial_stage": workflow_state.get("stage")},
                )
                stream_iterator = self.workflow_agent.graph.astream(workflow_state)

                # Shield the entire stream iteration from cancellation
                try:
                    async for step_state in stream_iterator:
                        for node_name, updated_state in step_state.items():
                            logger.info(
                                "LangGraph node execution completed",
                                extra={
                                    "session_id": session_id,
                                    "node_name": node_name,
                                    "current_stage": updated_state.get("stage"),
                                },
                            )

                            # 发送状态变化信息
                            status_change_response = self._create_status_change_response(
                                session_id, node_name, previous_stage, updated_state
                            )
                            if status_change_response:
                                yield f"data: {status_change_response.model_dump_json()}\n\n"

                            # 只在特定阶段发送消息响应
                            current_stage = updated_state.get("stage", WorkflowStage.CLARIFICATION)
                            if current_stage == WorkflowStage.CLARIFICATION:
                                # Always check for messages to send after clarification node runs
                                # This includes both pending questions AND completion messages
                                message_response = await self._create_message_response(
                                    session_id, updated_state
                                )
                                if message_response:
                                    logger.info(f"Sending clarification message to user")
                                    yield f"data: {message_response.model_dump_json()}\n\n"

                            # 在WORKFLOW_GENERATION节点完成后发送消息和工作流响应
                            if (
                                node_name == "workflow_generation"
                                and current_stage == WorkflowStage.WORKFLOW_GENERATION
                            ):
                                # 先发送workflow (重要：必须在状态还包含current_workflow时发送)
                                workflow_response = await self._create_workflow_response(
                                    session_id, updated_state
                                )
                                if workflow_response:
                                    logger.info("Sending workflow response after workflow_gen completed")
                                    yield f"data: {workflow_response.model_dump_json()}\n\n"
                                
                                # 然后发送完成消息
                                message_response = await self._create_message_response(
                                    session_id, updated_state
                                )
                                if message_response:
                                    logger.info("Sending completion message after workflow_gen completed")
                                    yield f"data: {message_response.model_dump_json()}\n\n"
                            # Debug logic removed - no longer needed in 2-node architecture

                            # 更新状态跟踪
                            previous_stage = current_stage
                            current_state = self._convert_from_workflow_state(updated_state)

                except asyncio.CancelledError:
                    logger.warning(
                        "LangGraph stream was cancelled", extra={"session_id": session_id}
                    )
                    raise

                logger.info(
                    "LangGraph streaming completed - async for loop exited",
                    extra={"session_id": session_id, "final_stage": current_state.get("stage")},
                )

                # 保存更新后的状态到数据库
                success = self.state_manager.save_full_state(
                    session_id=session_id,
                    workflow_state=current_state,
                    access_token=request.access_token,
                )
                if success:
                    logger.info(
                        "Saved updated workflow_agent_state", extra={"session_id": session_id}
                    )
                else:
                    logger.error(
                        "Failed to save workflow_agent_state", extra={"session_id": session_id}
                    )

            except (GeneratorExit, asyncio.CancelledError) as cancel_error:
                # 客户端断开连接时的正常处理
                logger.info(
                    "Client disconnected or request cancelled during workflow processing",
                    extra={
                        "session_id": session_id,
                        "current_stage": current_state.get("stage"),
                        "error_type": type(cancel_error).__name__,
                    },
                )
                # 保存当前状态
                try:
                    self.state_manager.save_full_state(
                        session_id=session_id,
                        workflow_state=current_state,
                        access_token=request.access_token,
                    )
                except Exception as save_error:
                    logger.error(
                        "Failed to save state on disconnect", extra={"error": str(save_error)}
                    )
                raise  # 重新抛出 GeneratorExit/CancelledError

            except Exception as processing_error:
                # Handle AttributeError specifically for END constant
                error_msg = str(processing_error)
                if isinstance(processing_error, AttributeError) and "END" in error_msg:
                    logger.warning(
                        "Handled END constant AttributeError",
                        extra={"session_id": session_id, "error": error_msg},
                    )
                    # This is expected when workflow reaches END - not a real error
                else:
                    logger.error(
                        "Error in workflow processing",
                        extra={
                            "session_id": session_id,
                            "error": error_msg,
                            "error_type": type(processing_error).__name__,
                        },
                    )

                # 尝试保存错误状态
                try:
                    current_state["error"] = str(processing_error)
                    current_state["error_stage"] = current_state.get("stage", "unknown")
                    self.state_manager.save_full_state(
                        session_id=session_id,
                        workflow_state=current_state,
                        access_token=request.access_token,
                    )
                except Exception as save_error:
                    logger.error("Failed to save error state", extra={"error": str(save_error)})

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
                    "Workflow processing cleanup - generator finally block",
                    extra={
                        "session_id": session_id,
                        "final_stage": current_state.get("stage"),
                        "generator_created": generator_created,
                    },
                )

        except Exception as e:
            import traceback

            error_traceback = traceback.format_exc()
            logger.error(
                "Failed to process conversation",
                extra={
                    "error": str(e),
                    "session_id": request.session_id,
                    "traceback": error_traceback,
                },
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
            "clarification_context": db_state.get(
                "clarification_context", {"origin": "create", "pending_questions": []}
            ),
            "conversations": db_state.get("conversations", []),
            # gap fields removed in optimized architecture
            "current_workflow": {},
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
        conversations = state.get("conversations", [])
        current_stage = state.get("stage", WorkflowStage.CLARIFICATION)

        # 获取最后一条 assistant 消息
        for conv in reversed(conversations):
            if conv.get("role") == "assistant":
                # Only set is_final=True when we're in the final stages or when workflow is complete
                is_final = current_stage in [
                    WorkflowStage.WORKFLOW_GENERATION,
                    "__end__",
                ]

                return ConversationResponse(
                    session_id=session_id,
                    response_type=ResponseType.MESSAGE,
                    message=conv.get("text", ""),
                    is_final=is_final,
                )

        return None

    async def _create_workflow_response(
        self, session_id: str, state: WorkflowState
    ) -> Optional[ConversationResponse]:
        current_workflow = state.get("current_workflow", {})
        workflow_id = state.get("workflow_id")

        logger.info(
            "Checking workflow for response",
            extra={
                "session_id": session_id,
                "has_workflow": bool(current_workflow),
                "workflow_type": type(current_workflow).__name__,
                "workflow_id": workflow_id,
                "node_count": len(current_workflow.get("nodes", [])) if isinstance(current_workflow, dict) else 0
            }
        )

        if (
            current_workflow
            and isinstance(current_workflow, dict)
            and current_workflow.get("nodes")
        ):
            # Add workflow_id to the workflow data if available
            workflow_data = current_workflow.copy()
            if workflow_id:
                workflow_data["workflow_id"] = workflow_id
                logger.info(
                    "Creating workflow response with workflow_id",
                    extra={
                        "session_id": session_id,
                        "node_count": len(current_workflow.get("nodes", [])),
                        "workflow_id": workflow_id,
                        "workflow_name": current_workflow.get("name", "Unknown")
                    },
                )
            else:
                logger.warning(
                    "Creating workflow response without workflow_id",
                    extra={
                        "session_id": session_id,
                        "node_count": len(current_workflow.get("nodes", [])),
                        "workflow_name": current_workflow.get("name", "Unknown")
                    },
                )
            
            workflow_json = json.dumps(workflow_data)
            return ConversationResponse(
                session_id=session_id,
                response_type=ResponseType.WORKFLOW,
                workflow=workflow_json,
                is_final=False,
            )
        else:
            logger.warning(
                "No workflow to send",
                extra={
                    "session_id": session_id,
                    "current_workflow": str(current_workflow)[:200] if current_workflow else None
                }
            )

        return None


# 创建 FastAPI 应用
app = FastAPI(
    title="Workflow Agent API",
    description="工作流代理服务 - ProcessConversation 接口",
    version="1.0.0",
)

# 初始化遥测系统
# 检查是否禁用OpenTelemetry
otel_disabled = os.getenv("OTEL_SDK_DISABLED", "false").lower() == "true"
environment = os.getenv("ENVIRONMENT", "development")

if not otel_disabled:
    # AWS生产环境使用localhost:4317 (AWS OTEL Collector sidecar)
    # 开发环境使用otel-collector:4317 (Docker Compose service)
    if environment in ["production", "staging"]:
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    else:
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")

    setup_telemetry(
        app, service_name="workflow-agent", service_version="1.0.0", otlp_endpoint=otlp_endpoint
    )

    # 添加遥测中间件
    app.add_middleware(TrackingMiddleware)
    app.add_middleware(MetricsMiddleware, service_name="workflow-agent")

    msg = f"OpenTelemetry configured for workflow-agent in {environment}"
    msg += f" with endpoint: {otlp_endpoint}"
    print(msg)
else:
    print("OpenTelemetry disabled for workflow-agent via OTEL_SDK_DISABLED environment variable")

# 创建服务器实例
servicer = WorkflowAgentServicer()


@app.post("/process-conversation")
async def process_conversation(request: ConversationRequest, request_obj: Request):
    """
    ProcessConversation 接口
    返回流式响应
    """
    import time

    start_time = time.time()
    session_id = request.session_id

    # 获取 trace_id
    trace_id = request_obj.headers.get("x-trace-id") or request_obj.headers.get("X-Trace-ID")
    if trace_id:
        logger.info(f"Processing conversation with trace_id: {trace_id}")
        # 将 trace_id 存储到 request state，供后续使用
        request_obj.state.trace_id = trace_id

    async def wrapped_generator():
        """Wrapper to track client disconnection"""
        try:
            logger.info("Starting streaming response", extra={"session_id": session_id})
            async for chunk in servicer.process_conversation(request, request_obj):
                # Check if client is still connected
                if await request_obj.is_disconnected():
                    logger.warning(
                        "Client disconnected",
                        extra={
                            "session_id": session_id,
                            "elapsed_seconds": round(time.time() - start_time, 2),
                        },
                    )
                    break
                yield chunk
        except asyncio.CancelledError:
            elapsed = time.time() - start_time
            logger.warning(
                "Streaming cancelled",
                extra={"session_id": session_id, "elapsed_seconds": round(elapsed, 2)},
            )
            raise
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                "Error in streaming",
                extra={
                    "session_id": session_id,
                    "elapsed_seconds": round(elapsed, 2),
                    "error": str(e),
                },
            )
            raise
        finally:
            elapsed = time.time() - start_time
            logger.info(
                "Streaming ended",
                extra={"session_id": session_id, "elapsed_seconds": round(elapsed, 2)},
            )

    return StreamingResponse(
        wrapped_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable proxy buffering
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
