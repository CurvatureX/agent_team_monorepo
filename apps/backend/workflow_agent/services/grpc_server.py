import asyncio
import json
import time
from concurrent import futures
from typing import Optional, AsyncGenerator

import grpc
import structlog

from agents.workflow_agent import WorkflowAgent 
from core.config import settings  
from workflow_agent_pb2 import (
    ConversationRequest, ConversationResponse, AgentState, 
    ErrorContent, Conversation, AlternativeOption,
    ClarificationContext, WorkflowContext, RAGContext, RAGResult,
    STAGE_CLARIFICATION, STAGE_NEGOTIATION, STAGE_GAP_ANALYSIS,
    STAGE_ALTERNATIVE_GENERATION, STAGE_WORKFLOW_GENERATION, 
    STAGE_DEBUG, STAGE_COMPLETED, STAGE_ERROR
)
import workflow_agent_pb2_grpc
from workflow_agent_pb2_grpc import add_WorkflowAgentServicer_to_server
from agents.state import WorkflowState, WorkflowStage, WorkflowOrigin, ClarificationPurpose

logger = structlog.get_logger()


class StateConverter:
    """状态转换器 - 处理 protobuf 和内部状态之间的转换"""
    
    @staticmethod
    def proto_to_workflow_state(proto_state: AgentState) -> WorkflowState:
        """将 protobuf AgentState 转换为内部 WorkflowState"""
        # 解析 current_workflow_json 为对象
        current_workflow = {}
        if proto_state.current_workflow_json:
            try:
                import json
                current_workflow = json.loads(proto_state.current_workflow_json)
            except (json.JSONDecodeError, TypeError):
                current_workflow = {}
        
        # 构建 WorkflowState
        state: WorkflowState = {
            "session_id": proto_state.session_id,
            "user_id": proto_state.user_id,
            "created_at": proto_state.created_at,
            "updated_at": proto_state.updated_at,
            "stage": WorkflowStage(StateConverter._proto_enum_to_stage(proto_state.stage)),
            "intent_summary": proto_state.intent_summary,
            "current_workflow": current_workflow,
            "debug_result": proto_state.debug_result,
            "debug_loop_count": proto_state.debug_loop_count,
            "execution_history": list(proto_state.execution_history),
            "gaps": list(proto_state.gaps),
            "clarification_context": {
                "origin": WorkflowOrigin.CREATE,
                "purpose": ClarificationPurpose.INITIAL_INTENT,
                "collected_info": {},
                "pending_questions": []
            },
            "conversations": [],
            "alternatives": []
        }
        
        # 处理 previous_stage
        if proto_state.previous_stage:
            state["previous_stage"] = WorkflowStage(StateConverter._proto_enum_to_stage(proto_state.previous_stage))
        
        # 转换 conversations
        conversations = []
        for conv in proto_state.conversations:
            conversations.append({
                "role": conv.role,
                "text": conv.text,
                "timestamp": conv.timestamp,
                "metadata": dict(conv.metadata)
            })
        state["conversations"] = conversations
        
        # 转换 alternatives
        alternatives = []
        for alt in proto_state.alternatives:
            alternatives.append({
                "id": alt.id,
                "title": alt.title,
                "description": alt.description,
                "approach": alt.approach,
                "trade_offs": list(alt.trade_offs),
                "complexity": alt.complexity
            })
        state["alternatives"] = alternatives
        
        # 转换 clarification_context
        if proto_state.clarification_context:
            state["clarification_context"] = {
                "purpose": proto_state.clarification_context.purpose,
                "origin": proto_state.clarification_context.origin,
                "collected_info": dict(proto_state.clarification_context.collected_info),
                "pending_questions": list(proto_state.clarification_context.pending_questions)
            }
        
        # 转换 workflow_context
        if proto_state.workflow_context:
            state["workflow_context"] = {
                "origin": proto_state.workflow_context.origin,
                "source_workflow_id": proto_state.workflow_context.source_workflow_id,
                "modification_intent": proto_state.workflow_context.modification_intent
            }
        
        # 转换 rag_context
        if proto_state.rag_context:
            rag_results = []
            for result in proto_state.rag_context.results:
                rag_results.append({
                    "id": result.id,
                    "node_type": result.node_type,
                    "title": result.title,
                    "description": result.description,
                    "content": result.content,
                    "similarity": result.similarity,
                    "metadata": dict(result.metadata)
                })
            
            state["rag"] = {
                "query": proto_state.rag_context.query,
                "timestamp": proto_state.rag_context.timestamp,
                "metadata": dict(proto_state.rag_context.metadata),
                "results": rag_results
            }
        
        return state
    
    @staticmethod
    def workflow_state_to_proto(state: WorkflowState) -> AgentState:
        """将内部 WorkflowState 转换为 protobuf AgentState"""
        agent_state = AgentState()
        
        # 基本字段
        agent_state.session_id = str(state.get("session_id", ""))
        agent_state.user_id = str(state.get("user_id", ""))
        agent_state.created_at = int(state.get("created_at", time.time() * 1000))
        agent_state.updated_at = int(time.time() * 1000)
        agent_state.stage = StateConverter._stage_to_proto_enum(state.get("stage", "clarification"))
        agent_state.intent_summary = str(state.get("intent_summary", ""))
        agent_state.debug_result = str(state.get("debug_result", ""))
        agent_state.debug_loop_count = int(state.get("debug_loop_count", 0))
        
        # 处理 current_workflow
        current_workflow = state.get("current_workflow")
        if current_workflow:
            if isinstance(current_workflow, dict):
                agent_state.current_workflow_json = json.dumps(current_workflow)
            else:
                agent_state.current_workflow_json = str(current_workflow)
        
        # 处理 previous_stage
        previous_stage = state.get("previous_stage")
        if previous_stage:
            agent_state.previous_stage = StateConverter._stage_to_proto_enum(previous_stage)
        
        # 处理数组字段
        execution_history = state.get("execution_history", [])
        if isinstance(execution_history, list):
            agent_state.execution_history[:] = [str(item) for item in execution_history]
        
        gaps = state.get("gaps", [])
        if isinstance(gaps, list):
            agent_state.gaps[:] = [str(gap) for gap in gaps]
        
        # 转换 conversations
        conversations = state.get("conversations", [])
        for conv in conversations:
            if isinstance(conv, dict):
                conversation = Conversation()
                conversation.role = str(conv.get("role", "user"))
                conversation.text = str(conv.get("text", ""))
                conversation.timestamp = int(conv.get("timestamp", time.time() * 1000))
                
                metadata = conv.get("metadata", {})
                if isinstance(metadata, dict):
                    for key, value in metadata.items():
                        conversation.metadata[str(key)] = str(value)
                
                agent_state.conversations.append(conversation)
        
        # 转换 alternatives
        alternatives = state.get("alternatives", [])
        for alt_data in alternatives:
            if isinstance(alt_data, dict):
                alt = AlternativeOption()
                alt.id = str(alt_data.get("id", ""))
                alt.title = str(alt_data.get("title", ""))
                alt.description = str(alt_data.get("description", ""))
                alt.approach = str(alt_data.get("approach", ""))
                alt.complexity = str(alt_data.get("complexity", ""))
                
                trade_offs = alt_data.get("trade_offs", [])
                if isinstance(trade_offs, list):
                    alt.trade_offs[:] = [str(t) for t in trade_offs]
                
                agent_state.alternatives.append(alt)
        
        # 转换 clarification_context
        clarification_context = state.get("clarification_context", {})
        if clarification_context:
            context = ClarificationContext()
            context.purpose = str(clarification_context.get("purpose", ""))
            context.origin = str(clarification_context.get("origin", ""))
            
            pending_questions = clarification_context.get("pending_questions", [])
            if isinstance(pending_questions, list):
                context.pending_questions[:] = [str(q) for q in pending_questions]
            
            collected_info = clarification_context.get("collected_info", {})
            if isinstance(collected_info, dict):
                for key, value in collected_info.items():
                    context.collected_info[str(key)] = str(value)
            
            agent_state.clarification_context.CopyFrom(context)
        
        # 转换 workflow_context
        workflow_context = state.get("workflow_context", {})
        if workflow_context:
            context = WorkflowContext()
            context.origin = str(workflow_context.get("origin", ""))
            context.source_workflow_id = str(workflow_context.get("source_workflow_id", ""))
            context.modification_intent = str(workflow_context.get("modification_intent", ""))
            agent_state.workflow_context.CopyFrom(context)
        
        # 转换 rag_context
        rag_context = state.get("rag", {})
        if rag_context:
            context = RAGContext()
            context.query = str(rag_context.get("query", ""))
            context.timestamp = int(rag_context.get("timestamp", time.time() * 1000))
            
            metadata = rag_context.get("metadata", {})
            if isinstance(metadata, dict):
                for key, value in metadata.items():
                    context.metadata[str(key)] = str(value)
            
            results = rag_context.get("results", [])
            for result_data in results:
                if isinstance(result_data, dict):
                    result = RAGResult()
                    result.id = str(result_data.get("id", ""))
                    result.node_type = str(result_data.get("node_type", ""))
                    result.title = str(result_data.get("title", ""))
                    result.description = str(result_data.get("description", ""))
                    result.content = str(result_data.get("content", ""))
                    result.similarity = float(result_data.get("similarity", 0.0))
                    
                    result_metadata = result_data.get("metadata", {})
                    if isinstance(result_metadata, dict):
                        for key, value in result_metadata.items():
                            result.metadata[str(key)] = str(value)
                    
                    context.results.append(result)
            
            agent_state.rag_context.CopyFrom(context)
        
        return agent_state
    
    @staticmethod
    def _stage_to_proto_enum(stage: str) -> int:
        """将 stage 字符串转换为 protobuf 枚举"""
        mapping = {
            "clarification": STAGE_CLARIFICATION,
            "negotiation": STAGE_NEGOTIATION,
            "gap_analysis": STAGE_GAP_ANALYSIS,
            "alternative_generation": STAGE_ALTERNATIVE_GENERATION,
            "workflow_generation": STAGE_WORKFLOW_GENERATION,
            "debug": STAGE_DEBUG,
            "completed": STAGE_COMPLETED
        }
        return mapping.get(stage, STAGE_ERROR)
    
    @staticmethod
    def _proto_enum_to_stage(proto_enum: int) -> str:
        """将 protobuf 枚举转换为 stage 字符串"""
        mapping = {
            STAGE_CLARIFICATION: "clarification",
            STAGE_NEGOTIATION: "negotiation",
            STAGE_GAP_ANALYSIS: "gap_analysis",
            STAGE_ALTERNATIVE_GENERATION: "alternative_generation",
            STAGE_WORKFLOW_GENERATION: "workflow_generation",
            STAGE_DEBUG: "debug",
            STAGE_COMPLETED: "completed"
        }
        return mapping.get(proto_enum, "clarification")


class WorkflowAgentServicer(workflow_agent_pb2_grpc.WorkflowAgentServicer):
    """新的 WorkflowAgent gRPC 服务实现"""

    def __init__(self):
        logger.info("Initializing WorkflowAgentServicer")
        self.workflow_agent = WorkflowAgent()
        logger.info("WorkflowAgent initialized")

    async def ProcessConversation(
        self, 
        request: ConversationRequest, 
        context: grpc.aio.ServicerContext
    ) -> AsyncGenerator[ConversationResponse, None]:
        """
        处理对话的统一接口 - 支持所有 6 个阶段的工作流
        """
        try:
            logger.info(f"Processing conversation for session: {request.session_id}")

            # 转换 protobuf 状态为内部格式
            current_state = StateConverter.proto_to_workflow_state(request.current_state)
            
            # 更新基本信息
            current_state["session_id"] = request.session_id
            current_state["user_id"] = request.user_id
            current_state["updated_at"] = int(time.time() * 1000)

            # 添加用户消息到对话历史
            if request.user_message:
                current_state["conversations"].append({
                    "role": "user",
                    "text": request.user_message,
                    "timestamp": int(time.time() * 1000),
                    "metadata": {}
                })

            # 处理工作流上下文
            if request.workflow_context:
                current_state["workflow_context"] = {
                    "origin": request.workflow_context.origin,
                    "source_workflow_id": request.workflow_context.source_workflow_id,
                    "modification_intent": request.workflow_context.modification_intent
                }

            logger.info(f"Current stage: {current_state.get('stage', 'unknown')}")

            # 通过 LangGraph 处理状态
            final_state = None
            step_count = 0
            
            async for chunk in self.workflow_agent.graph.astream(current_state):
                step_count += 1
                logger.info(f"Processing step {step_count}: {list(chunk.keys())}")
                
                for node_name, node_output in chunk.items():
                    if node_name != "router":  # 跳过路由器节点
                        logger.info(f"Node {node_name} completed, stage: {node_output.get('stage')}")
                        
                        # 发送中间状态响应
                        response = ConversationResponse(
                            session_id=request.session_id,
                            updated_state=StateConverter.workflow_state_to_proto(node_output),
                            timestamp=int(time.time() * 1000),
                            is_final=False
                        )
                        yield response
                        
                        final_state = node_output

            # 发送最终响应
            if final_state:
                final_response = ConversationResponse(
                    session_id=request.session_id,
                    updated_state=StateConverter.workflow_state_to_proto(final_state),
                    timestamp=int(time.time() * 1000),
                    is_final=True
                )
                yield final_response
            else:
                # 如果没有最终状态，返回当前状态
                final_response = ConversationResponse(
                    session_id=request.session_id,
                    updated_state=StateConverter.workflow_state_to_proto(current_state),
                    timestamp=int(time.time() * 1000),
                    is_final=True
                )
                yield final_response

        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            logger.error(f"Failed to process conversation: {str(e)}", 
                        session_id=request.session_id,
                        traceback=error_traceback)
            
            # 发送错误响应
            error_response = ConversationResponse(
                session_id=request.session_id,
                error=ErrorContent(
                    error_code="INTERNAL_ERROR",
                    message=f"Failed to process conversation: {str(e)}",
                    details=str(e),
                    is_recoverable=True
                ),
                timestamp=int(time.time() * 1000),
                is_final=True
            )
            yield error_response


class WorkflowAgentServer:
    """新的 gRPC 服务器"""

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
            add_WorkflowAgentServicer_to_server(self.servicer, self.server)

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