"""
Workflow API endpoints for MVP
"""

from fastapi import APIRouter, HTTPException, Query, Request
from app.database import sessions_rls_repo
from app.utils.sse import create_sse_response, create_mock_workflow_stream
from app.config import settings
from app.utils import log_error


router = APIRouter()


@router.get("/workflow_generation")
async def listen_workflow_generation_progress(http_request: Request, session_id: str = Query(..., description="Session ID")):
    """
    Listen to workflow generation progress via SSE with RLS
    
    RLS-enabled implementation:
    - Session validation with RLS
    - Mock workflow generation stream
    - TODO: Replace with actual gRPC call to workflow service
    """
    try:
        # Get access token for RLS
        access_token = getattr(http_request.state, 'access_token', None)
        
        # Session validation with RLS
        session = sessions_rls_repo.get_by_id(session_id, access_token=access_token)
        if not session:
            raise HTTPException(
                status_code=404,
                detail="Session not found or access denied"
            )
        
        # Create SSE stream for workflow progress
        async def workflow_progress_stream():
            async for event in create_mock_workflow_stream(session_id):
                yield event
        
        return create_sse_response(workflow_progress_stream())
    
    except HTTPException:
        raise
    except Exception as e:
        if settings.DEBUG:
            log_error(f"Error in workflow endpoint: {e}")
        
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.get("/workflow/{workflow_id}")
async def get_workflow(workflow_id: str):
    """
    Get workflow by ID (MVP placeholder)
    TODO: Implement actual workflow retrieval via gRPC
    """
    try:
        # MVP: Return mock workflow data
        # TODO: Replace with actual gRPC call to workflow service
        return {
            "workflow_id": workflow_id,
            "status": "completed",
            "data": {
                "message": "This is a mock workflow response",
                "steps": [
                    {"id": 1, "name": "Step 1", "status": "completed"},
                    {"id": 2, "name": "Step 2", "status": "completed"},
                    {"id": 3, "name": "Step 3", "status": "completed"}
                ]
            },
            "created_at": "2025-07-15T10:00:00Z",
            "updated_at": "2025-07-15T10:05:00Z"
        }
    
    except Exception as e:
        if settings.DEBUG:
            log_error(f"Error getting workflow: {e}")
        
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )