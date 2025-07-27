"""
Chat API endpoints with integrated workflow agent
支持SSE流式响应的聊天端点
"""

import json
import time
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request, Query, Depends
from fastapi.responses import StreamingResponse

from app.models.chat import (
    MessageType,
    ChatRequest,
    ChatMessage,
    ChatSSEEvent,
    ChatResponse,
    ChatHistory,
    WorkflowGenerationEvent,
)
from app.dependencies import AuthenticatedDeps, get_session_id
from app.exceptions import ValidationError, NotFoundError
from app.database import sessions_rls_repo, chats_rls_repo
from app.utils.sse import create_sse_response, create_mock_chat_stream
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/stream")
async def chat_stream(chat_request: ChatRequest, deps: AuthenticatedDeps = Depends()):
    """
    流式对话接口 - 负责和 workflow_agent 交互

    集成workflow生成功能：
    - 自动检测workflow生成请求
    - 返回stage变更和workflow生成消息
    - Event types: message, status, error, workflow_stage

    按照技术设计方案实现：
    - POST接口符合HTTP语义
    - SSE返回包含type字段的结构化响应
    - 完全集成workflow生成，无需独立端点
    """
    try:
        logger.info(f"💬 Starting chat stream for session {chat_request.session_id}")

        # Session validation with RLS
        session = sessions_rls_repo.get_by_id(
            chat_request.session_id, access_token=deps.current_user.token
        )
        if not session:
            raise NotFoundError("Session")

        # Store user message with RLS
        user_message_data = {
            "session_id": chat_request.session_id,
            "user_id": deps.current_user.sub,
            "message_type": MessageType.USER.value,
            "content": chat_request.message,
            "metadata": chat_request.context,
        }

        # Store user message (if chat repository is available)
        try:
            stored_user_message = chats_rls_repo.create(user_message_data)
        except Exception as e:
            logger.warning(f"Failed to store user message: {e}")
            stored_user_message = None

        # Create SSE stream generator
        async def generate_chat_stream():
            """生成聊天流式响应"""
            start_time = time.time()

            try:
                # Send initial status
                yield create_sse_response(
                    {
                        "type": "status",
                        "data": {"status": "processing", "message": "Processing your request..."},
                        "session_id": chat_request.session_id,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )

                # Use mock chat stream for now (replace with actual gRPC call)
                async for event in create_mock_chat_stream(
                    chat_request.message, chat_request.session_id
                ):
                    yield event

                # Send completion status
                processing_time = time.time() - start_time
                yield create_sse_response(
                    {
                        "type": "completion",
                        "data": {
                            "status": "completed",
                            "processing_time_ms": round(processing_time * 1000, 2),
                            "session_id": chat_request.session_id,
                        },
                        "session_id": chat_request.session_id,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )

            except Exception as e:
                logger.error(f"❌ Error in chat stream: {e}")
                yield create_sse_response(
                    {
                        "type": "error",
                        "data": {"error": str(e), "error_type": "STREAM_ERROR"},
                        "session_id": chat_request.session_id,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )

        logger.info(f"✅ Chat stream initiated for session {chat_request.session_id}")

        return StreamingResponse(
            generate_chat_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable Nginx buffering
            },
        )

    except (ValidationError, NotFoundError, HTTPException):
        raise
    except Exception as e:
        logger.error(f"❌ Error in chat stream: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{session_id}/history", response_model=ChatHistory)
async def get_chat_history(
    session_id: str = Depends(get_session_id),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    deps: AuthenticatedDeps = Depends(),
):
    """
    获取聊天历史记录
    """
    try:
        logger.info(f"📜 Getting chat history for session {session_id}")

        # Validate session access with RLS
        session = sessions_rls_repo.get_by_id(session_id, access_token=deps.current_user.token)
        if not session:
            raise NotFoundError("Session")

        # Get chat history (if available)
        try:
            messages_data = chats_rls_repo.get_by_session_id(
                session_id,
                access_token=deps.current_user.token,
                limit=page_size,
                offset=(page - 1) * page_size,
            )

            # Convert to ChatMessage objects
            messages = [ChatMessage(**msg_data) for msg_data in messages_data]

        except Exception as e:
            logger.warning(f"Failed to get chat history: {e}")
            messages = []

        logger.info(f"✅ Retrieved {len(messages)} messages for session {session_id}")

        return ChatHistory(
            session_id=session_id,
            messages=messages,
            total_count=len(messages),
            page=page,
            page_size=page_size,
        )

    except (NotFoundError, HTTPException):
        raise
    except Exception as e:
        logger.error(f"❌ Error getting chat history for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

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
