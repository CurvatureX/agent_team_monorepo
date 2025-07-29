import asyncio
import json
import time
from concurrent import futures
from typing import Optional, AsyncGenerator

import grpc
import structlog

# 导入 agents 和核心组件
from agents.workflow_agent import WorkflowAgent 
from core.config import settings  
from services.state_manager import get_workflow_agent_state_manager
from agents.state import WorkflowState, WorkflowStage

# 导入新的 proto 定义
from proto.workflow_agent_pb2 import (
    ConversationRequest, ConversationResponse, WorkflowContext,
    ErrorContent, ResponseType,
    RESPONSE_TYPE_MESSAGE, RESPONSE_TYPE_WORKFLOW, RESPONSE_TYPE_ERROR
)
import proto.workflow_agent_pb2_grpc as workflow_agent_pb2_grpc

logger = structlog.get_logger()


class WorkflowAgentServicer(workflow_agent_pb2_grpc.WorkflowAgentServicer):
    """
    新的 WorkflowAgent gRPC 服务实现
    根据最新 proto 定义实现统一的 ProcessConversation 接口
    内部管理 workflow_agent_state，对外提供简洁的对话接口
    """

    def __init__(self):
        logger.info("Initializing WorkflowAgentServicer")
        self.workflow_agent = WorkflowAgent()
        self.state_manager = get_workflow_agent_state_manager()
        logger.info("WorkflowAgentServicer initialized with database state management")

    async def ProcessConversation(
        self, 
        request: ConversationRequest, 
        context: grpc.aio.ServicerContext
    ) -> AsyncGenerator[ConversationResponse, None]:
        """
        处理对话的统一接口 - 支持所有工作流生成阶段
        内部管理 workflow_agent_state，对外提供流式响应
        """
        try:
            logger.info(f"Request: {request}")
            session_id = request.session_id
            current_state = self.state_manager.get_state_by_session(session_id, request.access_token)
            
            if not current_state:
                # 创建新的 workflow_agent_state 记录
                workflow_context = None
                if request.workflow_context:
                    workflow_context = {
                        "origin": request.workflow_context.origin,
                        "source_workflow_id": request.workflow_context.source_workflow_id
                    }
                state_id = self.state_manager.create_state(
                    session_id=session_id,
                    user_id=request.user_id or "anonymous",
                    initial_stage="clarification",
                    workflow_context=workflow_context,
                    access_token=request.access_token
                )
                
                if not state_id:
                    raise Exception("Failed to create workflow_agent_state")
                
                # 重新获取创建的状态
                current_state = self.state_manager.get_state_by_session(session_id, request.access_token)
                logger.info(f"Created new workflow_agent_state for session {session_id}")
            else:
                logger.info(f"Retrieved existing workflow_agent_state for session {session_id}")
            
            # 添加用户消息到对话历史
            conversations = current_state.get("conversations", [])
            if request.user_message:
                conversations.append({
                    "role": "user",
                    "text": request.user_message,
                    "timestamp": int(time.time() * 1000)
                })
                current_state["conversations"] = conversations

            # 更新时间戳
            current_state["updated_at"] = int(time.time() * 1000)

            logger.info(f"Current stage: {current_state.get('stage', 'unknown')}")

            # 通过 LangGraph 处理状态 - 使用真正的 workflow_agent
            try:
                # 转换状态格式为 LangGraph WorkflowState
                workflow_state = self._convert_to_workflow_state(current_state)
                
                # 使用 LangGraph 流式处理
                async for step_state in self.workflow_agent.graph.astream(workflow_state):
                    for node_name, updated_state in step_state.items():
                        logger.info(f"LangGraph step completed: {node_name}")
                        
                        # 为每个节点生成相应的 gRPC 响应
                        async for response in self._generate_node_response(node_name, updated_state, session_id):
                            yield response
                            
                        # 更新当前状态
                        current_state = self._convert_from_workflow_state(updated_state)
                        
                        # 如果到达完成状态，退出循环
                        if updated_state.get("stage") == WorkflowStage.COMPLETED:
                            break

                # 保存更新后的状态到数据库 - 符合 req2.md 要求
                success = self.state_manager.save_full_state(
                    session_id=session_id,
                    workflow_state=current_state,
                    access_token=request.access_token
                )
                if success:
                    logger.info(f"Saved updated workflow_agent_state for session {session_id}")
                else:
                    logger.error(f"Failed to save workflow_agent_state for session {session_id}")

            except Exception as processing_error:
                logger.error(f"Error in workflow processing: {processing_error}")
                yield ConversationResponse(
                    session_id=session_id,
                    response_type=RESPONSE_TYPE_ERROR,
                    error=ErrorContent(
                        error_code="PROCESSING_ERROR",
                        message=f"Error processing workflow: {str(processing_error)}",
                        details=str(processing_error),
                        is_recoverable=True
                    ),
                    is_final=True
                )

        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            logger.error(f"Failed to process conversation: {str(e)}", 
                        session_id=request.session_id,
                        traceback=error_traceback)
            
            # 发送错误响应
            yield ConversationResponse(
                session_id=request.session_id,
                response_type=RESPONSE_TYPE_ERROR,
                error=ErrorContent(
                    error_code="INTERNAL_ERROR",
                    message=f"Failed to process conversation: {str(e)}",
                    details=str(e),
                    is_recoverable=True
                ),
                is_final=True
            )

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
            "clarification_context": db_state.get("clarification_context", {
                "origin": "create",
                "pending_questions": []
            }),
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
        
    async def _generate_node_response(self, node_name: str, state: WorkflowState, session_id: str) -> AsyncGenerator[ConversationResponse, None]:
        """为每个节点生成相应的 gRPC 响应"""
        stage = state.get("stage", WorkflowStage.CLARIFICATION)
        
        if stage == WorkflowStage.CLARIFICATION:
            yield await self._handle_clarification_response(state, session_id)
            
        elif stage == WorkflowStage.NEGOTIATION:
            yield await self._handle_negotiation_response(state, session_id)
            
        elif stage == WorkflowStage.GAP_ANALYSIS:
            yield await self._handle_gap_analysis_response(state, session_id)
            
        elif stage == WorkflowStage.ALTERNATIVE_GENERATION:
            yield await self._handle_alternative_generation_response(state, session_id)
            
        elif stage == WorkflowStage.WORKFLOW_GENERATION:
            yield await self._handle_workflow_generation_response(state, session_id)
            
        elif stage == WorkflowStage.DEBUG:
            yield await self._handle_debug_response(state, session_id)
            
        elif stage == WorkflowStage.COMPLETED:
            yield await self._handle_completion_response(state, session_id)
    
    async def _handle_clarification_response(self, state: WorkflowState, session_id: str) -> ConversationResponse:
        """处理澄清阶段响应"""
        conversations = state.get("conversations", [])
        if conversations:
            # 获取最新的助手消息
            for conv in reversed(conversations):
                if conv.get("role") == "assistant":
                    return ConversationResponse(
                        session_id=session_id,
                        response_type=RESPONSE_TYPE_MESSAGE,
                        message=conv.get("text", "正在处理您的请求..."),
                        is_final=False
                    )
        
        return ConversationResponse(
            session_id=session_id,
            response_type=RESPONSE_TYPE_MESSAGE,
            message="正在澄清您的需求...",
            is_final=False
        )
    
    async def _handle_negotiation_response(self, state: WorkflowState, session_id: str) -> ConversationResponse:
        """处理协商阶段响应"""
        clarification_context = state.get("clarification_context", {})
        pending_questions = clarification_context.get("pending_questions", [])
        
        if pending_questions:
            questions_text = "\n".join(pending_questions)
            return ConversationResponse(
                session_id=session_id,
                response_type=RESPONSE_TYPE_MESSAGE,
                message=questions_text,
                is_final=False
            )
        
        return ConversationResponse(
            session_id=session_id,
            response_type=RESPONSE_TYPE_MESSAGE,
            message="正在处理您的回复...",
            is_final=False
        )
    
    async def _handle_gap_analysis_response(self, state: WorkflowState, session_id: str) -> ConversationResponse:
        """处理能力差距分析阶段响应"""
        gaps = state.get("gaps", [])
        
        if gaps:
            gap_message = f"分析发现以下能力差距: {', '.join(gaps)}。正在生成替代方案..."
        else:
            gap_message = "能力分析完成，没有发现重大差距。准备生成工作流..."
            
        return ConversationResponse(
            session_id=session_id,
            response_type=RESPONSE_TYPE_MESSAGE,
            message=gap_message,
            is_final=False
        )
    
    async def _handle_alternative_generation_response(self, state: WorkflowState, session_id: str) -> ConversationResponse:
        """处理替代方案生成阶段响应"""
        alternatives = state.get("alternatives", [])
        
        if alternatives:
            alt_messages = []
            for i, alt in enumerate(alternatives, 1):
                if isinstance(alt, dict):
                    title = alt.get("title", f"方案 {i}")
                    description = alt.get("description", "")
                    alt_messages.append(f"{i}. {title}: {description}")
                else:
                    alt_messages.append(f"{i}. {alt}")
            
            message = "已生成以下替代方案：\n" + "\n".join(alt_messages) + "\n\n请选择您希望采用的方案编号。"
        else:
            message = "正在生成替代方案..."
            
        return ConversationResponse(
            session_id=session_id,
            response_type=RESPONSE_TYPE_MESSAGE,
            message=message,
            is_final=False
        )
    
    async def _handle_workflow_generation_response(self, state: WorkflowState, session_id: str) -> ConversationResponse:
        """处理工作流生成阶段响应"""
        current_workflow = state.get("current_workflow", {})
        
        if current_workflow and isinstance(current_workflow, dict) and current_workflow.get("nodes"):
            # 工作流已生成
            workflow_json = json.dumps(current_workflow) if isinstance(current_workflow, dict) else str(current_workflow)
            
            return ConversationResponse(
                session_id=session_id,
                response_type=RESPONSE_TYPE_WORKFLOW,
                workflow=workflow_json,
                is_final=False  # 还需要debug验证
            )
        else:
            return ConversationResponse(
                session_id=session_id,
                response_type=RESPONSE_TYPE_MESSAGE,
                message="正在生成工作流...",
                is_final=False
            )
    
    async def _handle_debug_response(self, state: WorkflowState, session_id: str) -> ConversationResponse:
        """处理调试阶段响应"""
        debug_result = state.get("debug_result", "")
        
        if debug_result:
            try:
                debug_data = json.loads(debug_result) if isinstance(debug_result, str) else debug_result
                
                if debug_data.get("success"):
                    return ConversationResponse(
                        session_id=session_id,
                        response_type=RESPONSE_TYPE_MESSAGE,
                        message="工作流验证成功！",
                        is_final=False
                    )
                else:
                    errors = debug_data.get("errors", [])
                    error_msg = "工作流验证发现问题：\n" + "\n".join(errors) + "\n正在修复..."
                    return ConversationResponse(
                        session_id=session_id,
                        response_type=RESPONSE_TYPE_MESSAGE,
                        message=error_msg,
                        is_final=False
                    )
            except (json.JSONDecodeError, TypeError):
                pass
        
        return ConversationResponse(
            session_id=session_id,
            response_type=RESPONSE_TYPE_MESSAGE,
            message="正在验证工作流...",
            is_final=False
        )
    
    async def _handle_completion_response(self, state: WorkflowState, session_id: str) -> ConversationResponse:
        """处理完成阶段响应"""
        current_workflow = state.get("current_workflow", {})
        
        if current_workflow and isinstance(current_workflow, dict):
            workflow_json = json.dumps(current_workflow)
            node_count = len(current_workflow.get("nodes", []))
            
            # 先发送成功消息
            return ConversationResponse(
                session_id=session_id,
                response_type=RESPONSE_TYPE_WORKFLOW,
                workflow=workflow_json,
                message=f"工作流生成完成！包含 {node_count} 个节点。",
                is_final=True
            )
        else:
            return ConversationResponse(
                session_id=session_id,
                response_type=RESPONSE_TYPE_ERROR,
                error=ErrorContent(
                    error_code="WORKFLOW_GENERATION_FAILED",
                    message="工作流生成失败",
                    details="无法生成有效的工作流",
                    is_recoverable=True
                ),
                is_final=True
            )


class WorkflowAgentServer:
    """WorkflowAgent gRPC 服务器"""
    
    def __init__(self):
        logger.info("Initializing WorkflowAgentServer")
        self.server: Optional[grpc.aio.Server] = None
        self.servicer = WorkflowAgentServicer()
        logger.info("WorkflowAgentServer initialization complete")

    async def start(self):
        """启动 gRPC 服务器"""
        try:
            logger.info("Creating gRPC server instance")
            self.server = grpc.aio.server(
                futures.ThreadPoolExecutor(max_workers=settings.MAX_WORKERS)
            )

            # 添加服务到服务器
            logger.info("Adding servicer to server")
            workflow_agent_pb2_grpc.add_WorkflowAgentServicer_to_server(self.servicer, self.server)

            # 配置服务器地址
            listen_addr = f"{settings.GRPC_HOST}:{settings.GRPC_PORT}"
            logger.info(f"Configuring server address: {listen_addr}")
            self.server.add_insecure_port(listen_addr)

            # 启动服务器
            logger.info("Starting gRPC server...")
            await self.server.start()
            logger.info(f"gRPC server started at {listen_addr}")

        except Exception as e:
            logger.error(f"Failed to start gRPC server: {str(e)}")
            raise

    async def stop(self):
        """停止 gRPC 服务器"""
        if self.server:
            logger.info("Stopping gRPC server")
            await self.server.stop(grace=5)
            logger.info("gRPC server stopped")

    async def wait_for_termination(self):
        """等待服务器终止"""
        if self.server:
            await self.server.wait_for_termination()