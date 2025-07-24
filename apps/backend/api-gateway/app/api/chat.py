"""
Chat API endpoints for MVP
"""

from fastapi import APIRouter, HTTPException, Request, Query
from app.models import MessageType
from app.database import sessions_rls_repo, chats_rls_repo
from app.utils.sse import create_sse_response, create_mock_chat_stream
from app.config import settings
from app.utils import log_info, log_error


router = APIRouter()


@router.get("/chat/stream")
async def chat_stream(
    http_request: Request, 
    session_id: str = Query(..., description="Session ID"), 
    user_message: str = Query(..., description="User message")
):
    """
    Send chat message via GET and return AI streaming response
    
    Uses industry standard incremental streaming (OpenAI/Claude style):
    - Each event contains only delta (new content)
    - Frontend appends deltas to build full message
    
    RLS-enabled implementation:
    - Session validation with RLS
    - Store user message with RLS
    - Return mock AI streaming response
    - Store AI response with RLS
    """
    try:
        # Get user and access token (already validated by jwt_auth_middleware)
        user = getattr(http_request.state, 'user', None)
        user_id = user.get("sub") if user else None
        access_token = getattr(http_request.state, 'access_token', None)
        
        # Session validation with RLS (RLS ensures user can only access their own sessions)
        session = sessions_rls_repo.get_by_id(session_id, access_token=access_token)
        if not session:
            raise HTTPException(
                status_code=404,
                detail="Session not found"
            )
        
        # Store user message with RLS
        user_message_data = {
            "session_id": session_id,
            "user_id": user_id,
            "message_type": MessageType.USER.value,
            "content": user_message
        }
        
        stored_user_message = chats_rls_repo.create(user_message_data)
        if not stored_user_message:
            raise HTTPException(
                status_code=500,
                detail="Failed to store user message"
            )
        
        # Create SSE stream for AI response with RLS
        async def ai_response_stream():
            full_response = ""
            
            async for chunk in create_mock_chat_stream(session_id, user_message):
                # Accumulate deltas to get full response for storage
                full_response += chunk.get("delta", "")
                yield chunk
            
            # Store final AI response in database with RLS
            ai_message_data = {
                "session_id": session_id,
                "user_id": user_id,
                "message_type": MessageType.ASSISTANT.value,
                "content": full_response
            }
            
            ai_message = chats_rls_repo.create(ai_message_data)
            if settings.DEBUG and ai_message:
                log_info(f"📝 Stored AI response with RLS: {ai_message['id']}")
        
        return create_sse_response(ai_response_stream())
    
    except HTTPException:
        raise
    except Exception as e:
        if settings.DEBUG:
            log_error(f"Error in chat endpoint: {e}")
        
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.get("/chat/{session_id}/messages")
async def get_chat_history(session_id: str, http_request: Request):
    """
    Get chat history for a session with RLS
    """
    try:
        # Get access token (user already validated by jwt_auth_middleware)
        access_token = getattr(http_request.state, 'access_token', None)
        
        # Verify session exists with RLS (RLS ensures user can only access their own sessions)
        session = sessions_rls_repo.get_by_id(session_id, access_token=access_token)
        if not session:
            raise HTTPException(
                status_code=404,
                detail="Session not found"
            )
        
        # Get all messages for this session with RLS (RLS ensures user can only access their own messages)
        messages = chats_rls_repo.get_by_session_id(session_id, access_token=access_token)
        
        # Sort by sequence_number (chronological order)
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
        
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )