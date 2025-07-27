"""
Chat API endpoints with integrated workflow agent
"""

import json
from fastapi import APIRouter, HTTPException, Request, Query
from app.models import MessageType, ChatRequest
from app.database import sessions_rls_repo, chats_rls_repo
from app.utils.sse import create_sse_response, create_mock_chat_stream
from app.config import settings
from app.utils import log_info, log_error


router = APIRouter()


@router.post("/chat/stream")
async def chat_stream(chat_request: ChatRequest, http_request: Request):
    """
    流式对话接口 - 负责和 workflow_agent 交互

    集成workflow生成功能：
    - 自动检测workflow生成请求
    - 返回stage变更和workflow生成消息
    - Event types: message, status, error

    按照技术设计方案实现：
    - POST接口符合HTTP语义
    - SSE返回包含type字段的结构化响应
    - 完全集成workflow生成，无需独立端点
    """
    try:
        # Get user and access token
        user = getattr(http_request.state, "user", None)
        user_id = user.get("sub") if user else "anonymous"
        access_token = getattr(http_request.state, "access_token", None)

        # Session validation with RLS
        session = sessions_rls_repo.get_by_id(chat_request.session_id, access_token=access_token)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Store user message with RLS
        user_message_data = {
            "session_id": chat_request.session_id,
            "user_id": user_id,
            "message_type": MessageType.USER.value,
            "content": chat_request.message,
        }

        stored_user_message = chats_rls_repo.create(user_message_data)
        if not stored_user_message:
            raise HTTPException(status_code=500, detail="Failed to store user message")

        # Import gRPC client and state manager
        from app.services.grpc_client import workflow_client
        from app.services.state_manager import get_state_manager

        # Create SSE stream with workflow_agent integration
        async def workflow_conversation_stream():
            state_manager = get_state_manager()

            # Get session metadata for workflow context
            action_type = session.get("action_type", "create")
            source_workflow_id = session.get("source_workflow_id", "")

            workflow_context = {
                "origin": action_type,
                "source_workflow_id": source_workflow_id,
                "modification_intent": f"User requested {action_type} workflow",
            }

            # Create workflow state if needed
            existing_state = state_manager.get_state_by_session(
                chat_request.session_id, access_token
            )
            if not existing_state:
                state_id = state_manager.create_state(
                    session_id=chat_request.session_id,
                    user_id=user_id,
                    clarification_context={"origin": action_type, "pending_questions": []},
                    workflow_context=workflow_context,
                    access_token=access_token,
                )
                log_info(f"Created workflow state for session {chat_request.session_id}")

            # Process conversation through workflow_agent
            full_response = ""
            async for response in workflow_client.process_conversation_stream(
                session_id=chat_request.session_id,
                user_message=chat_request.message,
                user_id=user_id,
                workflow_context=workflow_context,
                access_token=access_token,
            ):
                # Transform response to match tech spec format
                sse_data = {
                    "type": response["type"],
                    "session_id": response["session_id"],
                    "timestamp": response["timestamp"],
                    "is_final": response.get("is_final", False),
                }

                # Add type-specific content
                if response["type"] == "message":
                    sse_data["content"] = response["message"]
                    full_response += response["message"].get("text", "")
                elif response["type"] == "status":
                    sse_data["content"] = response["status"]
                elif response["type"] == "error":
                    sse_data["content"] = response["error"]

                yield sse_data

                # Stop if final response
                if response.get("is_final", False):
                    break

            # Store final AI response
            if full_response.strip():
                ai_message_data = {
                    "session_id": chat_request.session_id,
                    "user_id": user_id,
                    "message_type": MessageType.ASSISTANT.value,
                    "content": full_response,
                }

                ai_message = chats_rls_repo.create(ai_message_data)
                if settings.DEBUG and ai_message:
                    log_info(f"📝 Stored AI response: {ai_message['id']}")

        return create_sse_response(workflow_conversation_stream())

    except HTTPException:
        raise
    except Exception as e:
        log_error(f"Error in chat stream: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/chat/{session_id}/messages")
async def get_chat_history(session_id: str, http_request: Request):
    """
    Get chat history for a session with RLS
    """
    try:
        # Get access token (user already validated by jwt_auth_middleware)
        access_token = getattr(http_request.state, "access_token", None)

        # Verify session exists with RLS (RLS ensures user can only access their own sessions)
        session = sessions_rls_repo.get_by_id(session_id, access_token=access_token)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Get all messages for this session with RLS (RLS ensures user can only access their own messages)
        messages = chats_rls_repo.get_by_session_id(session_id, access_token=access_token)

        # Sort by sequence_number (chronological order)
        messages.sort(key=lambda x: x["sequence_number"])

        return {"session_id": session_id, "messages": messages, "total_count": len(messages)}

    except HTTPException:
        raise
    except Exception as e:
        if settings.DEBUG:
            log_error(f"Error getting chat history: {e}")

        raise HTTPException(status_code=500, detail="Internal server error")
