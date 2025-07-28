"""
新的 Chat API - 支持三种返回类型：ai message, workflow, error
基于新的 workflow_agent.proto 文件
"""

import json
import structlog
from fastapi import APIRouter, HTTPException, Request
from app.models import MessageType, ChatRequest
from app.database import sessions_rls_repo, chats_rls_repo
from app.utils.sse import create_sse_response
from app.config import settings

logger = structlog.get_logger("chat_api")

router = APIRouter()


# 移除重复的 StageResponseProcessor，使用统一的 UnifiedResponseProcessor


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
                logger.debug("Created workflow state for session", session_id=chat_request.session_id)
            
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
                logger.debug("Received response type", response_type=response.get('type'))
                
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
                
                # 处理正常响应（grpc_client已经处理过类型转换）
                if response["type"] in ["ai_message", "workflow", "alternatives"] and "agent_state" in response:
                    # grpc_client 已经调用过 UnifiedResponseProcessor，直接使用处理结果
                    # 构建 SSE 响应
                    sse_data = {
                        "type": response["type"],
                        "session_id": response["session_id"],
                        "timestamp": response["timestamp"],
                        "is_final": response.get("is_final", False),
                        "content": response["content"]
                    }
                    
                    # 添加 workflow 数据（如果有）
                    if "workflow" in response:
                        sse_data["workflow"] = response["workflow"]
                        final_workflow_data = response["workflow"]
                    
                    # 收集 AI 响应文本
                    if response["type"] in ["ai_message", "alternatives"]:
                        final_ai_response += response["content"].get("text", "")
                    
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
                    logger.info("📝 Stored AI response", message_id=ai_message['id'])
        
        return create_sse_response(enhanced_workflow_stream())
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in chat stream", error=str(e))
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
            logger.exception("Error getting chat history", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")