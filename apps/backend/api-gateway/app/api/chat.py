"""
新的 Chat API - 支持三种返回类型：ai message, workflow, error
基于新的 workflow_agent.proto 文件
"""

import json
from fastapi import APIRouter, HTTPException, Request
from app.models import MessageType, ChatRequest
from app.database import sessions_rls_repo, chats_rls_repo
from app.utils.sse import create_sse_response
from app.config import settings
from app.utils import log_info, log_error, log_debug

router = APIRouter()


class StageResponseProcessor:
    """为每个 stage 处理响应的处理器类"""
    
    @staticmethod
    def process_clarification_response(agent_state: dict) -> dict:
        """处理澄清阶段响应"""
        conversations = agent_state.get("conversations", [])
        if conversations:
            latest_message = conversations[-1].get("text", "")
            return {
                "type": "ai_message",
                "content": {
                    "text": latest_message,
                    "role": "assistant",
                    "stage": "clarification"
                }
            }
        return {
            "type": "ai_message", 
            "content": {
                "text": "请描述您想要创建的工作流",
                "role": "assistant",
                "stage": "clarification"
            }
        }
    
    @staticmethod
    def process_negotiation_response(agent_state: dict) -> dict:
        """处理协商阶段响应"""
        conversations = agent_state.get("conversations", [])
        clarification_context = agent_state.get("clarification_context", {})
        pending_questions = clarification_context.get("pending_questions", [])
        
        if conversations:
            latest_message = conversations[-1].get("text", "")
            response = {
                "type": "ai_message",
                "content": {
                    "text": latest_message,
                    "role": "assistant",
                    "stage": "negotiation"
                }
            }
            if pending_questions:
                response["content"]["questions"] = pending_questions
            return response
        
        return {
            "type": "ai_message",
            "content": {
                "text": "请提供更多信息以便我更好地理解您的需求",
                "role": "assistant",
                "stage": "negotiation"
            }
        }
    
    @staticmethod
    def process_gap_analysis_response(agent_state: dict) -> dict:
        """处理差距分析阶段响应"""
        gaps = agent_state.get("gaps", [])
        return {
            "type": "ai_message",
            "content": {
                "text": f"需求分析完成，识别了 {len(gaps)} 个技术能力缺口" if gaps else "需求分析完成，可以直接实现",
                "role": "assistant",
                "stage": "gap_analysis",
                "gaps": gaps
            }
        }
    
    @staticmethod
    def process_alternative_generation_response(agent_state: dict) -> dict:
        """处理替代方案生成阶段响应 - 返回 alternatives 数据"""
        alternatives = agent_state.get("alternatives", [])
        conversations = agent_state.get("conversations", [])
        
        latest_message = ""
        if conversations:
            latest_message = conversations[-1].get("text", "")
        
        # 这里返回 alternatives 类型而不是 ai_message
        return {
            "type": "alternatives",
            "content": {
                "text": latest_message or "基于技术能力分析，为您提供以下替代方案：",
                "role": "assistant",
                "stage": "alternative_generation",
                "alternatives": alternatives
            }
        }
    
    @staticmethod
    def process_workflow_generation_response(agent_state: dict) -> dict:
        """处理工作流生成阶段响应 - 返回 workflow 数据"""
        current_workflow_json = agent_state.get("current_workflow_json", "")
        
        try:
            workflow_data = json.loads(current_workflow_json) if current_workflow_json else {}
        except json.JSONDecodeError:
            workflow_data = {}
        
        # 这里返回 workflow 类型
        return {
            "type": "workflow",
            "content": {
                "text": "工作流生成完成",
                "role": "assistant",
                "stage": "workflow_generation"
            },
            "workflow": workflow_data
        }
    
    @staticmethod
    def process_debug_response(agent_state: dict) -> dict:
        """处理调试阶段响应"""
        debug_result = agent_state.get("debug_result", "")
        
        try:
            debug_data = json.loads(debug_result) if debug_result else {}
        except json.JSONDecodeError:
            debug_data = {"success": False, "errors": ["Invalid debug result"]}
        
        return {
            "type": "ai_message",
            "content": {
                "text": "工作流验证完成" if debug_data.get("success") else "工作流验证发现问题",
                "role": "assistant",
                "stage": "debug",
                "debug_info": debug_data
            }
        }
    
    @staticmethod
    def process_completed_response(agent_state: dict) -> dict:
        """处理完成阶段响应 - 返回最终 workflow"""
        current_workflow_json = agent_state.get("current_workflow_json", "")
        
        try:
            workflow_data = json.loads(current_workflow_json) if current_workflow_json else {}
        except json.JSONDecodeError:
            workflow_data = {}
        
        return {
            "type": "workflow",
            "content": {
                "text": "工作流创建完成！",
                "role": "assistant",
                "stage": "completed"
            },
            "workflow": workflow_data
        }
    
    @classmethod
    def process_stage_response(cls, stage: str, agent_state: dict) -> dict:
        """根据 stage 处理响应"""
        processors = {
            "clarification": cls.process_clarification_response,
            "negotiation": cls.process_negotiation_response,
            "gap_analysis": cls.process_gap_analysis_response,
            "alternative_generation": cls.process_alternative_generation_response,
            "workflow_generation": cls.process_workflow_generation_response,
            "debug": cls.process_debug_response,
            "completed": cls.process_completed_response
        }
        
        processor = processors.get(stage, cls.process_clarification_response)
        return processor(agent_state)


@router.post("/chat/stream")
async def chat_stream(
    chat_request: ChatRequest,
    http_request: Request
):
    """
    新的流式对话接口 - 支持三种返回类型
    
    返回类型：
    1. ai_message - 纯文本消息 (clarification, negotiation, gap_analysis, debug)
    2. workflow - 工作流数据 (workflow_generation, completed) 
    3. error - 错误消息
    
    只在 is_final=true 时保存状态到数据库
    """
    try:
        # 获取用户和访问令牌
        user = getattr(http_request.state, 'user', None)
        user_id = user.get("sub") if user else "anonymous"
        access_token = getattr(http_request.state, 'access_token', None)
        
        # 验证会话
        session = sessions_rls_repo.get_by_id(chat_request.session_id, access_token=access_token)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # 存储用户消息
        user_message_data = {
            "session_id": chat_request.session_id,
            "user_id": user_id,
            "message_type": MessageType.USER.value,
            "content": chat_request.message
        }
        
        stored_user_message = chats_rls_repo.create(user_message_data)
        if not stored_user_message:
            raise HTTPException(status_code=500, detail="Failed to store user message")
        
        # 导入 gRPC 客户端
        from app.services.grpc_client import workflow_client
        from app.services.state_manager import get_state_manager
        
        # 创建流式响应
        async def enhanced_workflow_stream():
            state_manager = get_state_manager()
            
            # 准备工作流上下文
            action_type = session.get("action_type", "create")
            source_workflow_id = session.get("source_workflow_id", "")
            
            workflow_context = {
                "origin": action_type,
                "source_workflow_id": source_workflow_id,
                "modification_intent": f"User requested {action_type} workflow"
            }
            
            # 创建或获取工作流状态
            existing_state = state_manager.get_state_by_session(chat_request.session_id, access_token)
            if not existing_state:
                state_id = state_manager.create_state(
                    session_id=chat_request.session_id,
                    user_id=user_id,
                    clarification_context={"origin": action_type, "pending_questions": []},
                    workflow_context=workflow_context,
                    access_token=access_token
                )
                log_debug(f"Created workflow state for session {chat_request.session_id}")
            
            # 处理对话流
            final_ai_response = ""
            final_workflow_data = None
            
            async for response in workflow_client.process_conversation_stream(
                session_id=chat_request.session_id,
                user_message=chat_request.message,
                user_id=user_id,
                workflow_context=workflow_context,
                access_token=access_token
            ):
                log_debug(f"Received response type: {response.get('type')}")
                
                # 处理错误响应
                if response["type"] == "error":
                    yield {
                        "type": "error",
                        "session_id": response["session_id"],
                        "timestamp": response["timestamp"],
                        "is_final": response.get("is_final", True),
                        "content": response["error"]
                    }
                    return
                
                # 处理正常响应
                if response["type"] == "message" and "agent_state" in response:
                    agent_state = response["agent_state"]
                    stage = agent_state.get("stage", "clarification")
                    
                    # 使用 StageResponseProcessor 处理响应
                    processed_response = StageResponseProcessor.process_stage_response(stage, agent_state)
                    
                    # 构建 SSE 响应
                    sse_data = {
                        "type": processed_response["type"],
                        "session_id": response["session_id"],
                        "timestamp": response["timestamp"],
                        "is_final": response.get("is_final", False),
                        "content": processed_response["content"]
                    }
                    
                    # 添加 workflow 数据（如果有）
                    if "workflow" in processed_response:
                        sse_data["workflow"] = processed_response["workflow"]
                        final_workflow_data = processed_response["workflow"]
                    
                    # 收集 AI 响应文本
                    if processed_response["type"] in ["ai_message", "alternatives"]:
                        final_ai_response += processed_response["content"].get("text", "")
                    
                    yield sse_data
                    
                    # 如果是最终响应，退出循环
                    if response.get("is_final", False):
                        break
                else:
                    # 处理状态更新等其他响应
                    yield {
                        "type": "status",
                        "session_id": response["session_id"],
                        "timestamp": response["timestamp"],
                        "is_final": response.get("is_final", False),
                        "content": {"message": "Processing..."}
                    }
            
            # 存储最终 AI 响应到数据库
            if final_ai_response.strip():
                ai_message_data = {
                    "session_id": chat_request.session_id,
                    "user_id": user_id,
                    "message_type": MessageType.ASSISTANT.value,
                    "content": final_ai_response
                }
                
                ai_message = chats_rls_repo.create(ai_message_data)
                if settings.DEBUG and ai_message:
                    log_info(f"📝 Stored AI response: {ai_message['id']}")
        
        return create_sse_response(enhanced_workflow_stream())
    
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"Error in chat stream: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/chat/{session_id}/messages")
async def get_chat_history(session_id: str, http_request: Request):
    """
    获取聊天历史记录
    """
    try:
        # 获取访问令牌
        access_token = getattr(http_request.state, 'access_token', None)
        
        # 验证会话存在
        session = sessions_rls_repo.get_by_id(session_id, access_token=access_token)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # 获取所有消息
        messages = chats_rls_repo.get_by_session_id(session_id, access_token=access_token)
        
        # 按序列号排序
        messages.sort(key=lambda x: x["sequence_number"])
        
        return {
            "session_id": session_id,
            "messages": messages,
            "total_count": len(messages)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        if settings.DEBUG:
            log_error(f"Error getting chat history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")