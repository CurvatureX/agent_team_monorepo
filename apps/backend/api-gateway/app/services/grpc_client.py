"""
新的 gRPC 客户端 - 基于新的 workflow_agent.proto 文件
支持流式处理和状态管理
"""

import asyncio
import json
import time
from typing import AsyncGenerator, Dict, Any, Optional

import grpc
from app.config import settings
from app.services.state_manager import get_state_manager
from app.utils import log_info, log_warning, log_error, log_debug

# Import proto modules
try:
    from proto import workflow_agent_pb2
    from proto import workflow_agent_pb2_grpc
    GRPC_AVAILABLE = True
    log_info("✅ gRPC modules loaded successfully")
except ImportError as e:
    log_error(f"❌ gRPC proto modules not available: {e}. Using mock client.")
    workflow_agent_pb2 = None
    workflow_agent_pb2_grpc = None
    GRPC_AVAILABLE = False


class WorkflowGRPCClient:
    """
    新的 gRPC 客户端，基于新的 ProcessConversation 接口
    集成状态管理和流式响应处理
    """
    
    def __init__(self):
        self.host = settings.WORKFLOW_SERVICE_HOST
        self.port = settings.WORKFLOW_SERVICE_PORT
        self.channel = None
        self.stub = None
        self.connected = False
        self.state_manager = get_state_manager()
    
    async def connect(self):
        """连接到 workflow service"""
        try:
            if GRPC_AVAILABLE:
                self.channel = grpc.aio.insecure_channel(f"{self.host}:{self.port}")
                self.stub = workflow_agent_pb2_grpc.WorkflowAgentStub(self.channel)
                
                # 测试连接
                try:
                    await asyncio.wait_for(
                        self.channel.channel_ready(), 
                        timeout=5.0
                    )
                except AttributeError:
                    # 兼容性回退
                    await asyncio.sleep(0.1)
                
                self.connected = True
                log_info(f"Connected to workflow service at {self.host}:{self.port}")
            else:
                # Mock 连接
                await asyncio.sleep(0.1)
                self.connected = True
                log_info(f"Mock connected to workflow service at {self.host}:{self.port}")
                
        except Exception as e:
            log_error(f"Failed to connect to workflow service: {e}")
            self.connected = False
            raise
    
    async def close(self):
        """关闭 gRPC 连接"""
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
        处理对话流式请求
        
        Args:
            session_id: 会话 ID
            user_message: 用户消息
            user_id: 用户 ID
            workflow_context: 工作流上下文
            access_token: JWT token
            
        Yields:
            流式响应数据
        """
        if not self.connected:
            await self.connect()
        
        try:
            if GRPC_AVAILABLE:
                # 获取当前状态
                current_state_data = self.state_manager.get_state_by_session(session_id, access_token)
                
                # 构建 gRPC 请求
                request = workflow_agent_pb2.ConversationRequest(
                    session_id=session_id,
                    user_id=user_id,
                    user_message=user_message
                )
                
                # 添加工作流上下文
                if workflow_context and isinstance(workflow_context, dict):
                    try:
                        context = workflow_agent_pb2.WorkflowContext()
                        context.origin = str(workflow_context.get("origin", "create"))
                        context.source_workflow_id = str(workflow_context.get("source_workflow_id", ""))
                        context.modification_intent = str(workflow_context.get("modification_intent", ""))
                        request.workflow_context.CopyFrom(context)
                    except Exception as e:
                        log_error(f"Error setting workflow_context: {e}")
                
                # 添加当前状态
                if current_state_data:
                    try:
                        agent_state = self._db_state_to_proto(current_state_data)
                        request.current_state.CopyFrom(agent_state)
                        log_debug("State successfully added to request")
                    except Exception as e:
                        log_error(f"Error converting state to proto: {e}")
                        # 继续处理而不是失败
                
                log_debug("Calling ProcessConversation")
                
                # 流式处理
                async for response in self.stub.ProcessConversation(request):
                    # 转换响应
                    response_dict = self._proto_response_to_dict(response)
                    
                    # 保存最终状态到数据库
                    if response.is_final and response.updated_state:
                        try:
                            updated_state = self._proto_state_to_dict(response.updated_state)
                            self.state_manager.save_full_state(session_id, updated_state, access_token)
                            log_debug("Final state saved to database")
                        except Exception as e:
                            log_error(f"Error saving final state: {e}")
                    
                    yield response_dict
                    
            else:
                # Mock 实现
                async for response in self._mock_process_conversation(session_id, user_message, user_id):
                    yield response
                    
        except Exception as e:
            log_error(f"Error in process_conversation_stream: {e}")
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
    
    def _db_state_to_proto(self, db_state: Dict[str, Any]):
        """将数据库状态转换为 protobuf AgentState"""
        if not GRPC_AVAILABLE:
            return None
        
        def safe_timestamp(value, default=None):
            """安全的时间戳转换"""
            if default is None:
                default = int(time.time() * 1000)
            if isinstance(value, (int, float)):
                return int(value)
            elif isinstance(value, str):
                try:
                    import datetime
                    if 'T' in value or '-' in value:
                        dt = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
                        return int(dt.timestamp() * 1000)
                    else:
                        return int(float(value))
                except (ValueError, TypeError):
                    return default
            else:
                return default
        
        try:
            agent_state = workflow_agent_pb2.AgentState()
            
            # 基本字段
            agent_state.session_id = str(db_state.get("session_id", ""))
            agent_state.user_id = str(db_state.get("user_id", ""))
            agent_state.created_at = safe_timestamp(db_state.get("created_at"))
            agent_state.updated_at = safe_timestamp(db_state.get("updated_at"))
            agent_state.stage = self._stage_to_proto_enum(db_state.get("stage", "clarification"))
            agent_state.intent_summary = str(db_state.get("intent_summary", ""))
            agent_state.current_workflow_json = str(db_state.get("current_workflow_json", ""))
            agent_state.debug_result = str(db_state.get("debug_result", ""))
            agent_state.debug_loop_count = int(db_state.get("debug_loop_count", 0) or 0)
            
            # 处理 previous_stage
            previous_stage = db_state.get("previous_stage")
            if previous_stage:
                agent_state.previous_stage = self._stage_to_proto_enum(previous_stage)
            
            # 处理数组字段
            gaps = db_state.get("gaps") or []
            if isinstance(gaps, list):
                agent_state.gaps[:] = [str(gap) for gap in gaps]
                
            execution_history = db_state.get("execution_history") or []
            if isinstance(execution_history, list):
                agent_state.execution_history[:] = [str(item) for item in execution_history]
            
            # 处理 clarification_context
            clarification_context = db_state.get("clarification_context")
            if clarification_context and isinstance(clarification_context, dict):
                try:
                    context = workflow_agent_pb2.ClarificationContext()
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
                except Exception as e:
                    log_error(f"Error setting clarification_context: {e}")
            
            # 处理 workflow_context
            workflow_context = db_state.get("workflow_context")
            if workflow_context and isinstance(workflow_context, dict):
                try:
                    context = workflow_agent_pb2.WorkflowContext()
                    context.origin = str(workflow_context.get("origin", ""))
                    context.source_workflow_id = str(workflow_context.get("source_workflow_id", ""))
                    context.modification_intent = str(workflow_context.get("modification_intent", ""))
                    agent_state.workflow_context.CopyFrom(context)
                except Exception as e:
                    log_error(f"Error setting workflow_context: {e}")
            
            # 处理 rag_context
            rag_context = db_state.get("rag_context")
            if rag_context and isinstance(rag_context, dict):
                try:
                    context = workflow_agent_pb2.RAGContext()
                    context.query = str(rag_context.get("query", ""))
                    context.timestamp = safe_timestamp(rag_context.get("timestamp"))
                    
                    metadata = rag_context.get("metadata", {})
                    if isinstance(metadata, dict):
                        for key, value in metadata.items():
                            context.metadata[str(key)] = str(value)
                    
                    results = rag_context.get("results", [])
                    if isinstance(results, list):
                        for result_data in results:
                            if isinstance(result_data, dict):
                                result = workflow_agent_pb2.RAGResult()
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
                except Exception as e:
                    log_error(f"Error setting rag_context: {e}")
            
            # 处理 conversations
            conversations = db_state.get("conversations", [])
            if isinstance(conversations, str):
                try:
                    conversations = json.loads(conversations)
                except json.JSONDecodeError:
                    log_error(f"Failed to parse conversations JSON")
                    conversations = []
            
            if isinstance(conversations, list):
                for conv in conversations:
                    try:
                        if isinstance(conv, dict):
                            conversation = workflow_agent_pb2.Conversation()
                            conversation.role = str(conv.get("role", "user"))
                            conversation.text = str(conv.get("text", ""))
                            conversation.timestamp = safe_timestamp(conv.get("timestamp"))
                            
                            metadata = conv.get("metadata", {})
                            if isinstance(metadata, dict):
                                for key, value in metadata.items():
                                    conversation.metadata[str(key)] = str(value)
                            
                            agent_state.conversations.append(conversation)
                    except Exception as e:
                        log_error(f"Error converting conversation: {e}")
                        continue
            
            # 处理 alternatives
            alternatives = db_state.get("alternatives", [])
            if isinstance(alternatives, str):
                try:
                    alternatives = json.loads(alternatives)
                except json.JSONDecodeError:
                    alternatives = []
            
            if isinstance(alternatives, list):
                for alt_data in alternatives:
                    try:
                        if isinstance(alt_data, dict):
                            alt = workflow_agent_pb2.AlternativeOption()
                            alt.id = str(alt_data.get("id", ""))
                            alt.title = str(alt_data.get("title", ""))
                            alt.description = str(alt_data.get("description", ""))
                            alt.approach = str(alt_data.get("approach", ""))
                            alt.complexity = str(alt_data.get("complexity", ""))
                            
                            trade_offs = alt_data.get("trade_offs", [])
                            if isinstance(trade_offs, list):
                                alt.trade_offs[:] = [str(t) for t in trade_offs]
                            
                            agent_state.alternatives.append(alt)
                    except Exception as e:
                        log_error(f"Error converting alternative: {e}")
                        continue
            
            return agent_state
            
        except Exception as e:
            log_error(f"Error creating AgentState: {e}")
            raise
    
    def _proto_response_to_dict(self, response) -> Dict[str, Any]:
        """将 protobuf ConversationResponse 转换为字典"""
        result = {
            "session_id": response.session_id,
            "timestamp": response.timestamp,
            "is_final": response.is_final
        }
        
        # 处理错误
        if response.error and response.error.error_code:
            result["type"] = "error"
            result["error"] = {
                "error_code": response.error.error_code,
                "message": response.error.message,
                "details": response.error.details,
                "is_recoverable": response.error.is_recoverable
            }
        else:
            # 处理正常响应
            if response.updated_state:
                result["type"] = "message"
                result["agent_state"] = self._proto_state_to_dict(response.updated_state)
                
                # 基于 stage 确定响应类型和内容
                stage = result["agent_state"].get("stage", "clarification")
                result.update(self._process_stage_response(stage, result["agent_state"]))
            else:
                result["type"] = "status"
                result["message"] = "Processing..."
        
        return result
    
    def _process_stage_response(self, stage: str, agent_state: Dict[str, Any]) -> Dict[str, Any]:
        """根据 stage 处理响应内容"""
        if stage == "clarification":
            return self._process_clarification_response(agent_state)
        elif stage == "negotiation":
            return self._process_negotiation_response(agent_state)
        elif stage == "gap_analysis":
            return self._process_gap_analysis_response(agent_state)
        elif stage == "alternative_generation":
            return self._process_alternative_generation_response(agent_state)
        elif stage == "workflow_generation":
            return self._process_workflow_generation_response(agent_state)
        elif stage == "debug":
            return self._process_debug_response(agent_state)
        elif stage == "completed":
            return self._process_completed_response(agent_state)
        else:
            return {"message": {"text": "Processing...", "role": "assistant"}}
    
    def _process_clarification_response(self, agent_state: Dict[str, Any]) -> Dict[str, Any]:
        """处理澄清阶段响应"""
        conversations = agent_state.get("conversations", [])
        if conversations:
            latest_message = conversations[-1].get("text", "")
            return {
                "message": {
                    "text": latest_message,
                    "role": "assistant",
                    "type": "clarification"
                }
            }
        return {"message": {"text": "请描述您想要创建的工作流", "role": "assistant", "type": "clarification"}}
    
    def _process_negotiation_response(self, agent_state: Dict[str, Any]) -> Dict[str, Any]:
        """处理协商阶段响应"""
        conversations = agent_state.get("conversations", [])
        clarification_context = agent_state.get("clarification_context", {})
        pending_questions = clarification_context.get("pending_questions", [])
        
        if conversations:
            latest_message = conversations[-1].get("text", "")
            response = {
                "message": {
                    "text": latest_message,
                    "role": "assistant",
                    "type": "negotiation"
                }
            }
            if pending_questions:
                response["message"]["questions"] = pending_questions
            return response
        
        return {"message": {"text": "请提供更多信息", "role": "assistant", "type": "negotiation"}}
    
    def _process_gap_analysis_response(self, agent_state: Dict[str, Any]) -> Dict[str, Any]:
        """处理差距分析阶段响应"""
        gaps = agent_state.get("gaps", [])
        return {
            "message": {
                "text": f"分析完成，发现了 {len(gaps)} 个能力差距",
                "role": "assistant",
                "type": "gap_analysis",
                "gaps": gaps
            }
        }
    
    def _process_alternative_generation_response(self, agent_state: Dict[str, Any]) -> Dict[str, Any]:
        """处理替代方案生成阶段响应"""
        alternatives = agent_state.get("alternatives", [])
        conversations = agent_state.get("conversations", [])
        
        latest_message = ""
        if conversations:
            latest_message = conversations[-1].get("text", "")
        
        return {
            "message": {
                "text": latest_message,
                "role": "assistant", 
                "type": "alternatives",
                "alternatives": alternatives
            }
        }
    
    def _process_workflow_generation_response(self, agent_state: Dict[str, Any]) -> Dict[str, Any]:
        """处理工作流生成阶段响应"""
        current_workflow_json = agent_state.get("current_workflow_json", "")
        
        try:
            workflow_data = json.loads(current_workflow_json) if current_workflow_json else {}
        except json.JSONDecodeError:
            workflow_data = {}
        
        return {
            "message": {
                "text": "工作流生成完成",
                "role": "assistant",
                "type": "workflow"
            },
            "workflow": workflow_data
        }
    
    def _process_debug_response(self, agent_state: Dict[str, Any]) -> Dict[str, Any]:
        """处理调试阶段响应"""
        debug_result = agent_state.get("debug_result", "")
        
        try:
            debug_data = json.loads(debug_result) if debug_result else {}
        except json.JSONDecodeError:
            debug_data = {"success": False, "errors": ["Invalid debug result"]}
        
        return {
            "message": {
                "text": "调试完成" if debug_data.get("success") else "调试发现问题",
                "role": "assistant",
                "type": "debug",
                "debug_info": debug_data
            }
        }
    
    def _process_completed_response(self, agent_state: Dict[str, Any]) -> Dict[str, Any]:
        """处理完成阶段响应"""
        current_workflow_json = agent_state.get("current_workflow_json", "")
        
        try:
            workflow_data = json.loads(current_workflow_json) if current_workflow_json else {}
        except json.JSONDecodeError:
            workflow_data = {}
        
        return {
            "message": {
                "text": "工作流创建完成！",
                "role": "assistant",
                "type": "completed"
            },
            "workflow": workflow_data
        }
    
    def _proto_state_to_dict(self, agent_state) -> Dict[str, Any]:
        """将 protobuf AgentState 转换为字典"""
        state_dict = {
            "session_id": agent_state.session_id,
            "user_id": agent_state.user_id,
            "created_at": agent_state.created_at,
            "updated_at": agent_state.updated_at,
            "stage": self._proto_enum_to_stage(agent_state.stage),
            "execution_history": list(agent_state.execution_history),
            "intent_summary": agent_state.intent_summary,
            "gaps": list(agent_state.gaps),
            "current_workflow_json": agent_state.current_workflow_json,
            "debug_result": agent_state.debug_result,
            "debug_loop_count": agent_state.debug_loop_count
        }
        
        # 处理 previous_stage
        if agent_state.previous_stage:
            state_dict["previous_stage"] = self._proto_enum_to_stage(agent_state.previous_stage)
        
        # 处理 conversations
        conversations = []
        for conv in agent_state.conversations:
            conversations.append({
                "role": conv.role,
                "text": conv.text,
                "timestamp": conv.timestamp,
                "metadata": dict(conv.metadata)
            })
        state_dict["conversations"] = conversations
        
        # 处理 alternatives
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
        
        # 处理 clarification_context
        if agent_state.clarification_context:
            state_dict["clarification_context"] = {
                "purpose": agent_state.clarification_context.purpose,
                "origin": agent_state.clarification_context.origin,
                "collected_info": dict(agent_state.clarification_context.collected_info),
                "pending_questions": list(agent_state.clarification_context.pending_questions)
            }
        
        # 处理 workflow_context
        if agent_state.workflow_context:
            state_dict["workflow_context"] = {
                "origin": agent_state.workflow_context.origin,
                "source_workflow_id": agent_state.workflow_context.source_workflow_id,
                "modification_intent": agent_state.workflow_context.modification_intent
            }
        
        # 处理 rag_context
        if agent_state.rag_context:
            rag_results = []
            for result in agent_state.rag_context.results:
                rag_results.append({
                    "id": result.id,
                    "node_type": result.node_type,
                    "title": result.title,
                    "description": result.description,
                    "content": result.content,
                    "similarity": result.similarity,
                    "metadata": dict(result.metadata)
                })
            
            state_dict["rag_context"] = {
                "query": agent_state.rag_context.query,
                "timestamp": agent_state.rag_context.timestamp,
                "metadata": dict(agent_state.rag_context.metadata),
                "results": rag_results
            }
        
        return state_dict
    
    def _stage_to_proto_enum(self, stage: str) -> int:
        """将 stage 字符串转换为 protobuf 枚举"""
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
        """将 protobuf 枚举转换为 stage 字符串"""
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
    
    async def _mock_process_conversation(self, session_id: str, user_message: str, user_id: str):
        """Mock 实现，用于没有 gRPC 的环境"""
        yield {
            "type": "message",
            "session_id": session_id,
            "message": {
                "text": f"Mock response to: {user_message}",
                "role": "assistant",
                "type": "clarification"
            },
            "timestamp": int(time.time() * 1000),
            "is_final": True
        }


# 全局客户端实例
workflow_client = WorkflowGRPCClient()


async def get_workflow_client() -> WorkflowGRPCClient:
    """获取 workflow gRPC 客户端实例"""
    return workflow_client