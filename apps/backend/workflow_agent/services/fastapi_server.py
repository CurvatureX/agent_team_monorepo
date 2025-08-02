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

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from agents.state import WorkflowStage, WorkflowState

# Import workflow agent components
from agents.workflow_agent import WorkflowAgent
from core.config import settings
from core.logging_config import get_logger
from services.state_manager import get_workflow_agent_state_manager

# Add parent directory to path for shared models
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))  # Go to apps/backend
sys.path.insert(0, parent_dir)

# shared models导入（两种环境都相同）
from shared.models.conversation import (
    ConversationRequest,
    ConversationResponse,
    ErrorContent,
    ResponseType,
    StatusChangeContent,
)

logger = get_logger(__name__)


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
        generator_created = False
        try:
            logger.info(f"Request: {request}")
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

            # 通过 LangGraph 处理状态 - 使用真正的 workflow_agent
            try:
                # 转换状态格式为 LangGraph WorkflowState
                workflow_state = self._convert_to_workflow_state(current_state)
                previous_stage = workflow_state.get("stage")
                
                # 使用 LangGraph 流式处理
                logger.info(f"Starting LangGraph streaming for session {session_id}, initial stage: {workflow_state.get('stage')}")
                stream_iterator = self.workflow_agent.graph.astream(workflow_state)
                
                # Shield the entire stream iteration from cancellation
                try:
                    async for step_state in stream_iterator:
                        for node_name, updated_state in step_state.items():
                            logger.info(
                                f"LangGraph node execution completed",
                                session_id=session_id,
                                node_name=node_name,
                                current_stage=updated_state.get("stage")
                            )
                            
                            # 发送状态变化信息
                            status_change_response = self._create_status_change_response(
                                session_id, node_name, previous_stage, updated_state
                            )
                            if status_change_response:
                                yield f"data: {status_change_response.model_dump_json()}\n\n"

                            # 只在特定阶段发送消息响应
                            current_stage = updated_state.get("stage", WorkflowStage.CLARIFICATION)
                            # Skip if stage is LangGraph END constant
                            # if current_stage == "__end__" or str(current_stage) == "__end__":
                            #     logger.info("Skipping message response for END stage")
                            #     continue
                            if current_stage == WorkflowStage.CLARIFICATION:
                                # Check if we have pending questions to send
                                clarification_context = updated_state.get("clarification_context", {})
                                pending_questions = clarification_context.get("pending_questions", [])
                                if pending_questions:
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
                            
                            # Check termination after each node execution
                            if self._should_terminate_workflow(updated_state):
                                # Safe handling of stage for logging
                                if hasattr(current_stage, 'value'):
                                    stage_log = current_stage.value
                                elif current_stage == "__end__" or str(current_stage) == "__end__":
                                    stage_log = "END"
                                else:
                                    stage_log = str(current_stage)
                                    
                                logger.info(
                                    f"Workflow termination triggered",
                                    session_id=session_id,
                                    node_name=node_name,
                                    stage=stage_log
                                )
                                break
                
                except asyncio.CancelledError:
                    logger.warning(f"LangGraph stream was cancelled for session {session_id}")
                    raise
                    
                logger.info(
                    f"LangGraph streaming completed - async for loop exited",
                    session_id=session_id,
                    final_stage=current_state.get("stage"),
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

            except (GeneratorExit, asyncio.CancelledError) as cancel_error:
                # 客户端断开连接时的正常处理
                logger.info(
                    f"Client disconnected or request cancelled during workflow processing",
                    session_id=session_id,
                    current_stage=current_state.get("stage"),
                    error_type=type(cancel_error).__name__
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
                raise  # 重新抛出 GeneratorExit/CancelledError
                
            except Exception as processing_error:
                # Handle AttributeError specifically for END constant
                error_msg = str(processing_error)
                if isinstance(processing_error, AttributeError) and "END" in error_msg:
                    logger.warning(
                        f"Handled END constant AttributeError",
                        session_id=session_id,
                        error=error_msg
                    )
                    # This is expected when workflow reaches END - not a real error
                else:
                    logger.error(
                        f"Error in workflow processing",
                        session_id=session_id,
                        error=error_msg,
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
                    f"Workflow processing cleanup - generator finally block",
                    session_id=session_id,
                    final_stage=current_state.get("stage"),
                    generator_created=generator_created
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
            "identified_gaps": db_state.get("identified_gaps", db_state.get("gaps", [])),  # Use new name or legacy
            "gap_status": db_state.get("gap_status", "no_gap"),
            "gap_resolution": "",  # Not in database yet
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
            # Using legacy field names for backward compatibility
            "gaps": current_state.get("identified_gaps", []),  # Map to legacy name
            "alternatives": [],  # Always empty, not used anymore
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
        current_stage = state.get("stage", WorkflowStage.CLARIFICATION)

        # 获取最后一条 assistant 消息
        for conv in reversed(conversations):
            if conv.get("role") == "assistant":
                # Only set is_final=True when we're in the final stages or when workflow is complete
                is_final = current_stage in [
                    WorkflowStage.WORKFLOW_GENERATION, 
                    WorkflowStage.DEBUG,
                    "__end__"
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
        
        # Terminal stages
        terminal_stages = [
            WorkflowStage.COMPLETED,
            WorkflowStage.DEBUG,  # DEBUG is the final stage before END
        ]
        
        # Special check for clarification waiting for input
        if current_stage == WorkflowStage.CLARIFICATION:
            clarification_context = state.get("clarification_context", {})
            pending_questions = clarification_context.get("pending_questions", [])
            
            if pending_questions:
                logger.info(
                    f"Workflow waiting for user input in clarification",
                    session_id=state.get("session_id", "unknown"),
                    pending_questions_count=len(pending_questions)
                )
                return True

        if current_stage in terminal_stages:
            # Handle both WorkflowStage enum and LangGraph END constant
            if hasattr(current_stage, 'value'):
                stage_str = current_stage.value
            elif current_stage == "__end__" or str(current_stage) == "__end__":
                stage_str = "END"
            else:
                stage_str = str(current_stage)
                
            logger.info(
                f"Workflow reached terminal stage: {current_stage}",
                session_id=state.get("session_id", "unknown"),
                stage=stage_str
            )
            return True
            
        return False


# 创建 FastAPI 应用
app = FastAPI(
    title="Workflow Agent API",
    description="工作流代理服务 - ProcessConversation 接口",
    version="1.0.0",
)

# 创建服务器实例
servicer = WorkflowAgentServicer()


@app.post("/process-conversation")
async def process_conversation(request: ConversationRequest, request_obj: Request):
    """
    ProcessConversation 接口 - 对应原来的 gRPC 方法
    返回流式响应
    """
    import time
    start_time = time.time()
    session_id = request.session_id
    
    async def wrapped_generator():
        """Wrapper to track client disconnection"""
        try:
            logger.info(f"Starting streaming response for session {session_id}")
            async for chunk in servicer.process_conversation(request):
                # Check if client is still connected
                if await request_obj.is_disconnected():
                    logger.warning(f"Client disconnected for session {session_id} after {time.time() - start_time:.2f}s")
                    break
                yield chunk
        except asyncio.CancelledError:
            elapsed = time.time() - start_time
            logger.warning(f"Streaming cancelled for session {session_id} after {elapsed:.2f}s")
            raise
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Error in streaming for session {session_id} after {elapsed:.2f}s: {e}")
            raise
        finally:
            elapsed = time.time() - start_time
            logger.info(f"Streaming ended for session {session_id} after {elapsed:.2f}s")
    
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
