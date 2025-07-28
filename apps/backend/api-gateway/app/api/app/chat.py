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

        # Create SSE stream generator with actual gRPC integration
        async def generate_chat_stream():
            """生成聊天流式响应 - 与 workflow_agent 实际交互"""
            final_ai_response = ""
            final_workflow_data = None
            
            try:
                # Import gRPC client and response processor
                from app.services.grpc_client import workflow_client
                from app.services.response_processor import UnifiedResponseProcessor
                
                # Send initial status
                yield format_sse_event({
                    "type": "status",
                    "data": {"status": "processing", "message": "Connecting to workflow agent..."},
                    "session_id": chat_request.session_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

                # Process conversation stream with workflow agent
                async for response in workflow_client.process_conversation_stream(
                    session_id=chat_request.session_id,
                    user_message=chat_request.message,
                    user_id=deps.current_user.sub,
                    workflow_context=chat_request.context,
                    access_token=deps.current_user.token
                ):
                    logger.info(f"🔄 Received response: {response}")
                    # Handle error responses
                    if response["type"] == "error":
                        yield format_sse_event({
                            "type": "error",
                            "data": response.get("error", {"message": "Unknown error"}),
                            "session_id": chat_request.session_id,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })
                        return
                    
                    # Handle message responses from gRPC client
                    if response["type"] == "message":
                        # Extract agent state from the response
                        agent_state = response.get("agent_state", {})
                        current_stage = agent_state.get("stage", "clarification")
                        
                        # Extract message content
                        message_data = response.get("message", {})
                        if message_data:
                            # Add the latest message to conversations for processing
                            conversations = agent_state.get("conversations", [])
                            if message_data.get("text"):
                                conversations.append({
                                    "role": message_data.get("role", "assistant"),
                                    "text": message_data.get("text", ""),
                                })
                                agent_state["conversations"] = conversations
                        
                        # Use UnifiedResponseProcessor to format the response
                        processed_response = UnifiedResponseProcessor.process_stage_response(
                            current_stage, 
                            agent_state
                        )
                        
                        # Build SSE response
                        sse_data = {
                            "type": processed_response["type"],
                            "session_id": chat_request.session_id,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "is_final": response.get("is_final", False),
                            "data": processed_response["content"]
                        }
                        
                        # Add workflow data if present
                        if "workflow" in processed_response:
                            sse_data["workflow"] = processed_response["workflow"]
                            final_workflow_data = processed_response["workflow"]
                        elif response.get("workflow"):
                            # Check if workflow data is directly in response
                            try:
                                import json
                                workflow_data = json.loads(response["workflow"]) if isinstance(response["workflow"], str) else response["workflow"]
                                sse_data["workflow"] = workflow_data
                                final_workflow_data = workflow_data
                            except (json.JSONDecodeError, TypeError) as e:
                                logger.warning(f"Failed to parse workflow data: {e}")
                        
                        # Add alternatives if present
                        alternatives = response.get("alternatives", []) or agent_state.get("alternatives", [])
                        if alternatives:
                            sse_data["alternatives"] = alternatives
                        
                        # Collect AI response text for storage
                        if processed_response["type"] in ["ai_message", "alternatives", "workflow"]:
                            text_content = processed_response["content"].get("text", "")
                            if text_content:
                                final_ai_response += text_content
                        
                        yield format_sse_event(sse_data)
                        
                        # If this is the final response, break
                        if response.get("is_final", False):
                            break
                    
                    # Handle status updates
                    elif response["type"] == "status":
                        status_data = response.get("status", {})
                        yield format_sse_event({
                            "type": "status",
                            "data": {
                                "status": "processing",
                                "message": status_data.get("message", f"Stage: {status_data.get('current_stage', 'processing')}"),
                                "stage": status_data.get("current_stage", "clarification"),
                                "previous_stage": status_data.get("previous_stage"),
                                "intent_summary": status_data.get("intent_summary", "")
                            },
                            "session_id": chat_request.session_id,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })
                
                # Store AI response in database
                if final_ai_response.strip():
                    ai_message_data = {
                        "session_id": chat_request.session_id,
                        "user_id": deps.current_user.sub,
                        "message_type": MessageType.ASSISTANT.value,
                        "content": final_ai_response.strip(),
                        "metadata": {
                            "workflow_data": final_workflow_data,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    }
                    
                    try:
                        ai_result = user_client.table("chats").insert(ai_message_data).execute()
                        if ai_result.data:
                            logger.info(f"📝 Stored AI response: {ai_result.data[0]['id']}")
                    except Exception as e:
                        logger.warning(f"Failed to store AI response: {e}")

            except Exception as e:
                logger.error(f"❌ Error in chat stream: {e}")
                yield format_sse_event({
                    "type": "error",
                    "data": {"error": str(e), "error_type": "STREAM_ERROR"},
                    "session_id": chat_request.session_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

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
