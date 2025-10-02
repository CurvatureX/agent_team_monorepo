"""
Logs API Endpoints for Workflow Engine V2

Provides logs endpoints that integrate with the API Gateway's user-friendly logs system.
These endpoints serve the logs that are consumed by /api/v1/app/executions/{execution_id}/logs

Features:
- User-friendly log retrieval
- Real-time log streaming
- Filtering and pagination
- Direct Supabase integration
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException
from fastapi import Path as PathParam
from fastapi import Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))


class LogsResponse(BaseModel):
    """Response model for logs endpoint"""

    execution_id: str
    logs: List[Dict[str, Any]]
    total_count: int
    pagination: Dict[str, Any]


class StreamResponse(BaseModel):
    """Response model for streaming logs"""

    execution_id: str
    event_type: str
    data: Dict[str, Any]
    timestamp: str


# Create router
router = APIRouter(prefix="/api/v2", tags=["Execution Logs"])


class LogsService:
    """Service for retrieving execution logs"""

    def __init__(self):
        self._supabase = None
        self._init_supabase()

    def _init_supabase(self):
        """Initialize Supabase client"""
        try:
            import os

            from supabase import create_client

            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_ANON_KEY")

            if url and key:
                self._supabase = create_client(url, key)
        except Exception:
            pass

    async def get_logs(
        self,
        execution_id: str,
        limit: int = 100,
        offset: int = 0,
        level: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        access_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get execution logs from Supabase"""
        if not self._supabase:
            return {
                "execution_id": execution_id,
                "logs": [],
                "total_count": 0,
                "pagination": {"limit": limit, "offset": offset, "has_more": False},
            }

        try:
            # Build query
            query = (
                self._supabase.table("workflow_execution_logs")
                .select("*")
                .eq("execution_id", execution_id)
                .order("timestamp", desc=False)
            )

            # Add filters
            if level:
                query = query.eq("level", level.upper())
            if start_time:
                query = query.gte("timestamp", start_time)
            if end_time:
                query = query.lte("timestamp", end_time)

            # Apply pagination
            query = query.range(offset, offset + limit - 1)

            # Execute query
            response = query.execute()
            logs = response.data or []

            # Get total count
            count_query = (
                self._supabase.table("workflow_execution_logs")
                .select("id", count="exact")
                .eq("execution_id", execution_id)
            )

            if level:
                count_query = count_query.eq("level", level.upper())
            if start_time:
                count_query = count_query.gte("timestamp", start_time)
            if end_time:
                count_query = count_query.lte("timestamp", end_time)

            count_response = count_query.execute()
            total_count = count_response.count or 0

            # Format logs for API Gateway compatibility
            formatted_logs = []
            for log in logs:
                formatted_log = {
                    "id": log.get("id"),
                    "execution_id": execution_id,
                    "timestamp": log.get("timestamp"),
                    "level": log.get("level", "info").lower(),
                    "message": log.get("message", ""),
                    "user_friendly_message": log.get("user_friendly_message", ""),
                    "event_type": log.get("event_type", "log"),
                    "node_id": log.get("node_id"),
                    "node_name": log.get("node_name"),
                    "display_priority": log.get("display_priority", 5),
                    "is_milestone": log.get("is_milestone", False),
                    "data": log.get("data", {}),
                    "step_number": log.get("step_number"),
                    "total_steps": log.get("total_steps"),
                }
                formatted_logs.append(formatted_log)

            return {
                "execution_id": execution_id,
                "logs": formatted_logs,
                "total_count": total_count,
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "has_more": total_count > offset + len(formatted_logs),
                },
            }

        except Exception as e:
            print(f"Error retrieving logs: {e}")
            return {
                "execution_id": execution_id,
                "logs": [],
                "total_count": 0,
                "pagination": {"limit": limit, "offset": offset, "has_more": False},
            }

    async def stream_logs(self, execution_id: str, follow: bool = False):
        """Stream execution logs"""
        # First, get existing logs
        existing_logs = await self.get_logs(execution_id, limit=1000)

        # Yield existing logs
        for log in existing_logs.get("logs", []):
            yield {
                "event_type": "log",
                "data": log,
                "timestamp": log.get("timestamp"),
                "execution_id": execution_id,
            }

        # If not following, stop here
        if not follow:
            yield {
                "event_type": "complete",
                "data": {"message": "Historical logs complete"},
                "timestamp": time.time(),
                "execution_id": execution_id,
            }
            return

        # For real-time streaming, we would need to implement
        # a pub/sub system or polling mechanism
        # This is a simplified version
        yield {
            "event_type": "info",
            "data": {"message": "Real-time streaming not implemented yet"},
            "timestamp": time.time(),
            "execution_id": execution_id,
        }


# Initialize service
logs_service = LogsService()


@router.get(
    "/workflows/executions/{execution_id}/logs",
    response_model=LogsResponse,
    summary="Get execution logs",
    description="Retrieve logs for a workflow execution with filtering and pagination",
)
async def get_execution_logs(
    execution_id: str = PathParam(..., description="Execution ID"),
    limit: int = Query(100, description="Maximum number of logs to return", ge=1, le=1000),
    offset: int = Query(0, description="Number of logs to skip", ge=0),
    level: Optional[str] = Query(None, description="Filter by log level"),
    start_time: Optional[str] = Query(None, description="Start time filter (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time filter (ISO format)"),
    authorization: Optional[str] = Header(None, description="Bearer token for access control"),
):
    """Get execution logs with filtering and pagination"""

    try:
        # Extract access token
        access_token = None
        if authorization and authorization.startswith("Bearer "):
            access_token = authorization[7:]

        # Get logs from service
        result = await logs_service.get_logs(
            execution_id=execution_id,
            limit=limit,
            offset=offset,
            level=level,
            start_time=start_time,
            end_time=end_time,
            access_token=access_token,
        )

        return LogsResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve logs: {str(e)}")


@router.get(
    "/executions/{execution_id}/logs/stream",
    summary="Stream execution logs",
    description="Stream execution logs in real-time using Server-Sent Events",
)
async def stream_execution_logs(
    execution_id: str = PathParam(..., description="Execution ID"),
    follow: bool = Query(False, description="Follow live logs"),
    authorization: Optional[str] = Header(None),
):
    """Stream execution logs using Server-Sent Events"""

    async def event_stream():
        """Generate Server-Sent Events for log streaming"""
        try:
            # Extract access token
            access_token = None
            if authorization and authorization.startswith("Bearer "):
                access_token = authorization[7:]

            async for log_event in logs_service.stream_logs(execution_id, follow):
                # Format as SSE
                event_data = json.dumps(log_event, default=str)
                yield f"data: {event_data}\n\n"

                # Small delay to prevent overwhelming
                await asyncio.sleep(0.01)

        except Exception as e:
            error_event = {
                "event_type": "error",
                "data": {"error": str(e)},
                "timestamp": time.time(),
                "execution_id": execution_id,
            }
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
        },
    )


@router.get(
    "/executions/{execution_id}/logs/summary",
    summary="Get execution logs summary",
    description="Get a summary of execution logs including counts and milestones",
)
async def get_execution_logs_summary(
    execution_id: str = PathParam(..., description="Execution ID"),
    authorization: Optional[str] = Header(None),
):
    """Get execution logs summary"""

    try:
        # Get all logs to analyze
        all_logs = await logs_service.get_logs(execution_id, limit=10000)

        logs = all_logs.get("logs", [])

        # Analyze logs
        summary = {
            "execution_id": execution_id,
            "total_logs": len(logs),
            "log_levels": {},
            "event_types": {},
            "milestones": [],
            "nodes": {},
            "timeline": {"first_log": None, "last_log": None, "duration_estimate": None},
        }

        # Count by levels and event types
        for log in logs:
            level = log.get("level", "info")
            event_type = log.get("event_type", "log")

            summary["log_levels"][level] = summary["log_levels"].get(level, 0) + 1
            summary["event_types"][event_type] = summary["event_types"].get(event_type, 0) + 1

            # Collect milestones
            if log.get("is_milestone"):
                summary["milestones"].append(
                    {
                        "timestamp": log.get("timestamp"),
                        "message": log.get("user_friendly_message") or log.get("message"),
                        "event_type": event_type,
                    }
                )

            # Track nodes
            node_id = log.get("node_id")
            if node_id:
                if node_id not in summary["nodes"]:
                    summary["nodes"][node_id] = {
                        "node_name": log.get("node_name"),
                        "logs_count": 0,
                        "step_number": log.get("step_number"),
                        "status": "running",
                    }
                summary["nodes"][node_id]["logs_count"] += 1

                # Update status based on event type
                if event_type == "step_completed":
                    summary["nodes"][node_id]["status"] = "completed"
                elif event_type in ["step_failed", "step_error"]:
                    summary["nodes"][node_id]["status"] = "failed"

            # Timeline
            if summary["timeline"]["first_log"] is None:
                summary["timeline"]["first_log"] = log.get("timestamp")
            summary["timeline"]["last_log"] = log.get("timestamp")

        return summary

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")


# Health check endpoint
@router.get("/logs/health", summary="Health check for logs service")
async def logs_health_check():
    """Health check for the logs service"""
    return {
        "status": "healthy",
        "service": "workflow_engine_v2_logs",
        "version": "2.0.0",
        "supabase_connected": logs_service._supabase is not None,
        "timestamp": time.time(),
    }


__all__ = ["router", "LogsService"]
