"""
Chat API endpoints with integrated workflow agent
支持SSE流式响应的聊天端点
"""

import json
import time
from datetime import datetime, timezone

from app.core.database import create_user_supabase_client
from app.dependencies import AuthenticatedDeps, get_session_id
from app.exceptions import NotFoundError, ValidationError
from app.models.chat import (
    ChatHistory,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatSSEEvent,
    MessageType,
    WorkflowGenerationEvent,
)
from app.utils.logger import get_logger
from app.utils.sse import create_mock_chat_stream, create_sse_response
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

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
        user_client = create_user_supabase_client(deps.current_user.token)
        if not user_client:
            raise HTTPException(status_code=500, detail="Failed to create database client")

        session_result = (
            user_client.table("sessions").select("*").eq("id", chat_request.session_id).execute()
        )
        session = session_result.data[0] if session_result.data else None
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

        # Store user message with RLS
        try:
            chat_result = user_client.table("chats").insert(user_message_data).execute()
            stored_user_message = chat_result.data[0] if chat_result.data else None
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
        user_client = create_user_supabase_client(deps.current_user.token)
        if not user_client:
            raise HTTPException(status_code=500, detail="Failed to create database client")

        session_result = user_client.table("sessions").select("*").eq("id", session_id).execute()
        session = session_result.data[0] if session_result.data else None
        if not session:
            raise NotFoundError("Session")

        # Get chat history with RLS
        try:
            messages_result = (
                user_client.table("chats")
                .select("*")
                .eq("session_id", session_id)
                .order("created_at")
                .limit(page_size)
                .offset((page - 1) * page_size)
                .execute()
            )
            messages_data = messages_result.data if messages_result.data else []

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
