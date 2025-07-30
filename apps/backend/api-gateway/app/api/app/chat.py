"""
Chat API endpoints with integrated workflow agent
支持SSE流式响应的聊天端点
"""

import json
from datetime import datetime, timezone

from app.core.database import create_user_supabase_client
from app.dependencies import AuthenticatedDeps, get_session_id
from app.exceptions import NotFoundError, ValidationError
from app.models import ChatHistory, ChatMessage, ChatRequest, MessageType
from app.utils.logger import get_logger
from app.utils.sse import create_mock_chat_stream, format_sse_event
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
    - Event types: message, status, error, workflow

    按照技术设计方案实现：
    - POST接口符合HTTP语义
    - SSE返回包含type字段的结构化响应
    - 完全集成workflow生成，无需独立端点
    """
    try:
        logger.info(f"💬 Starting chat stream for session {chat_request.session_id}")

        # Session validation with service role key
        admin_client = deps.db_manager.supabase_admin
        if not admin_client:
            raise HTTPException(status_code=500, detail="Failed to create database client")

        session_result = (
            admin_client.table("sessions")
            .select("*")
            .eq("id", chat_request.session_id)
            .eq("user_id", deps.current_user.sub)
            .execute()
        )
        session = session_result.data[0] if session_result.data else None
        if not session:
            raise NotFoundError("Session")

        # Get the next sequence number for this session
        try:
            sequence_result = (
                admin_client.table("chats")
                .select("sequence_number")
                .eq("session_id", chat_request.session_id)
                .eq("user_id", deps.current_user.sub)
                .order("sequence_number", desc=True)
                .limit(1)
                .execute()
            )
            next_sequence = 1
            if sequence_result.data:
                last_sequence = sequence_result.data[0].get("sequence_number", 0)
                next_sequence = (last_sequence or 0) + 1
        except Exception:
            next_sequence = 1

        # Store user message with RLS
        user_message_data = {
            "session_id": chat_request.session_id,
            "user_id": deps.current_user.sub,
            "content": chat_request.user_message,
            "message_type": MessageType.USER.value,
            "sequence_number": next_sequence,
        }

        # Store user message with service role key
        try:
            chat_result = admin_client.table("chats").insert(user_message_data).execute()
            stored_user_message = chat_result.data[0] if chat_result.data else None
        except Exception as e:
            logger.warning(f"Failed to store user message: {e}")
            stored_user_message = None

        # Create SSE stream generator with actual gRPC integration
        async def generate_chat_stream():
            """根据新 proto 定义生成聊天流式响应"""
            sequence_counter = next_sequence  # 从用户消息序号开始继续递增

            try:
                # Import HTTP client (替换 gRPC)
                from app.core.config import get_settings
                from app.services.workflow_agent_http_client import get_workflow_agent_client

                # HTTP client is now the only option

                workflow_client = await get_workflow_agent_client()

                # Send initial status
                yield format_sse_event(
                    {
                        "type": "message",
                        "data": {
                            "status": "processing",
                            "message": "Connecting to workflow agent...",
                        },
                        "session_id": chat_request.session_id,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )

                # 构建 workflow_context - 根据 session 的 action 字段
                workflow_context = None
                if session.get("action") and session["action"] != "create":
                    workflow_context = {
                        "origin": session["action"],  # edit 或 copy
                        "source_workflow_id": session.get("workflow_id", ""),
                    }

                # Process conversation stream with workflow agent
                async for response in workflow_client.process_conversation_stream(
                    session_id=chat_request.session_id,
                    user_message=chat_request.user_message,
                    user_id=deps.current_user.sub,
                    workflow_context=workflow_context,
                    access_token=deps.access_token,
                ):
                    logger.info(f"🔄 Received response: {response}")

                    # Handle error responses
                    if response.get("response_type") == "RESPONSE_TYPE_ERROR":
                        yield format_sse_event(
                            {
                                "type": "error",
                                "data": response.get("error", {"message": "Unknown error"}),
                                "session_id": chat_request.session_id,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }
                        )
                        return

                    # Handle status change responses - 新增支持
                    elif response.get("response_type") == "RESPONSE_TYPE_STATUS_CHANGE":
                        status_change = response.get("status_change", {})
                        yield format_sse_event(
                            {
                                "type": "status_change",
                                "data": {
                                    "previous_stage": status_change.get("previous_stage"),
                                    "current_stage": status_change.get("current_stage"),
                                    "stage_state": status_change.get("stage_state", {}),
                                    "node_name": status_change.get("node_name"),
                                },
                                "session_id": chat_request.session_id,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "is_final": response.get("is_final", False),
                            }
                        )
                        # 状态变化不需要存储到数据库，继续处理下一个响应

                    # Handle message responses - 根据新 proto
                    elif response.get("response_type") == "RESPONSE_TYPE_MESSAGE":
                        message_content = response.get("message", "")

                        # Store AI message in database immediately - 符合要求
                        if message_content.strip():
                            sequence_counter += 1
                            ai_message_data = {
                                "session_id": chat_request.session_id,
                                "user_id": deps.current_user.sub,
                                "message_type": MessageType.ASSISTANT.value,
                                "content": message_content.strip(),
                                "sequence_number": sequence_counter,
                            }

                            try:
                                ai_result = (
                                    admin_client.table("chats").insert(ai_message_data).execute()
                                )
                                if ai_result.data:
                                    logger.info(
                                        f"📝 Stored AI message: {ai_result.data[0]['id']} (seq: {sequence_counter})"
                                    )
                            except Exception as e:
                                logger.warning(f"Failed to store AI message: {e}")

                        # Build SSE response
                        sse_data = {
                            "type": "message",
                            "session_id": chat_request.session_id,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "is_final": response.get("is_final", False),
                            "data": {"text": message_content, "role": "assistant"},
                        }

                        yield format_sse_event(sse_data)

                        # If this is the final response, break
                        if response.get("is_final", False):
                            break

                    # Handle workflow responses - 根据新 proto
                    elif response.get("response_type") == "RESPONSE_TYPE_WORKFLOW":
                        workflow_content = response.get("workflow", "")

                        # Parse workflow JSON if it's a string
                        try:
                            if isinstance(workflow_content, str):
                                workflow_data = json.loads(workflow_content)
                            else:
                                workflow_data = workflow_content
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.warning(f"Failed to parse workflow data: {e}")
                            workflow_data = {"raw": workflow_content}

                        # Store workflow message in database immediately
                        workflow_message = "Workflow generated successfully!"
                        sequence_counter += 1
                        ai_message_data = {
                            "session_id": chat_request.session_id,
                            "user_id": deps.current_user.sub,
                            "message_type": MessageType.ASSISTANT.value,
                            "content": workflow_message,
                            "sequence_number": sequence_counter,
                        }

                        try:
                            ai_result = (
                                admin_client.table("chats").insert(ai_message_data).execute()
                            )
                            if ai_result.data:
                                logger.info(
                                    f"📝 Stored workflow message: {ai_result.data[0]['id']} (seq: {sequence_counter})"
                                )
                        except Exception as e:
                            logger.warning(f"Failed to store workflow message: {e}")

                        # Build SSE response
                        sse_data = {
                            "type": "workflow",
                            "session_id": chat_request.session_id,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "is_final": response.get("is_final", True),
                            "data": {"text": workflow_message, "workflow": workflow_data},
                        }

                        yield format_sse_event(sse_data)

                        if response.get("is_final", True):
                            break

                    # Handle unknown response types
                    else:
                        response_type = response.get("response_type", "UNKNOWN")
                        logger.warning(f"⚠️ Unknown response type: {response_type}")
                        yield format_sse_event(
                            {
                                "type": "debug",
                                "data": {
                                    "message": f"Received unknown response type: {response_type}",
                                    "raw_response": response,
                                },
                                "session_id": chat_request.session_id,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }
                        )

            except Exception as e:
                logger.error(f"❌ Error in chat stream: {e}")
                yield format_sse_event(
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

        # Validate session access with service role key
        admin_client = deps.db_manager.supabase_admin
        if not admin_client:
            raise HTTPException(status_code=500, detail="Failed to create database client")

        session_result = (
            admin_client.table("sessions")
            .select("*")
            .eq("id", session_id)
            .eq("user_id", deps.current_user.sub)
            .execute()
        )
        session = session_result.data[0] if session_result.data else None
        if not session:
            raise NotFoundError("Session")

        # Get chat history with service role key
        try:
            messages_result = (
                admin_client.table("chats")
                .select("*")
                .eq("session_id", session_id)
                .eq("user_id", deps.current_user.sub)
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
