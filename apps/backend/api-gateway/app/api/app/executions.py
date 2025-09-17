"""
Execution management API endpoints with authentication
支持认证的执行管理API端点
"""

from typing import Any, Dict, Optional

from app.core.config import get_settings
from app.dependencies import AuthenticatedDeps, SSEDeps
from app.exceptions import NotFoundError, ValidationError
from app.models import ResponseModel
from pydantic import BaseModel, Field

try:
    from shared.models import Execution
except ImportError:
    import sys
    from pathlib import Path

    backend_dir = Path(__file__).parent.parent.parent.parent.parent
    sys.path.insert(0, str(backend_dir))
    from shared.models import Execution


class ExecutionCancelResponse(BaseModel):
    success: bool = Field(description="Whether cancellation was successful")
    message: str = Field(description="Result message")
    execution_id: str = Field(description="Execution ID")


import asyncio
import json

from app.models import SSEEventType
from app.services.workflow_engine_http_client import get_workflow_engine_client
from app.utils.logger import get_logger
from app.utils.sse import create_sse_event, create_sse_response, format_sse_event
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

logger = get_logger(__name__)
router = APIRouter()


@router.get("/executions/{execution_id}", response_model=Execution)
async def get_execution_status(execution_id: str, deps: AuthenticatedDeps = Depends()):
    """
    Get execution status with user access control
    获取执行状态（支持用户访问控制）
    """
    try:
        logger.info(f"📊 Getting execution status {execution_id} for user {deps.current_user.sub}")

        # Get HTTP client
        settings = get_settings()

        http_client = await get_workflow_engine_client()

        # Get execution status via HTTP
        result = await http_client.get_execution_status(execution_id)
        if not result or result.get("error"):
            raise NotFoundError("Execution")

        logger.info(f"✅ Execution status retrieved: {execution_id}")

        # The result from workflow-engine should already match the Execution model
        # since both use the same shared models
        return Execution(**result)

    except (NotFoundError, HTTPException):
        raise
    except Exception as e:
        logger.error(f"❌ Error getting execution status {execution_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/executions/{execution_id}/cancel", response_model=ExecutionCancelResponse)
async def cancel_execution(execution_id: str, deps: AuthenticatedDeps = Depends()):
    """
    Cancel a running execution with user access control
    取消正在运行的执行（支持用户访问控制）
    """
    try:
        logger.info(f"🛑 Cancelling execution {execution_id} for user {deps.current_user.sub}")

        # Get HTTP client
        settings = get_settings()

        http_client = await get_workflow_engine_client()

        # Cancel execution via HTTP
        result = await http_client.cancel_execution(execution_id)
        if not result or result.get("error"):
            raise NotFoundError("Execution")

        # Check if cancellation was successful
        if not result.get("success", False):
            error_message = result.get("message", "Failed to cancel execution")
            raise HTTPException(status_code=400, detail=error_message)

        logger.info(f"✅ Execution cancelled: {execution_id}")

        return ExecutionCancelResponse(**result)

    except (NotFoundError, HTTPException):
        raise
    except Exception as e:
        logger.error(f"❌ Error cancelling execution {execution_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/workflows/{workflow_id}/executions")
async def get_workflow_execution_history(
    workflow_id: str, limit: int = 50, deps: AuthenticatedDeps = Depends()
):
    """
    Get execution history for a workflow
    获取工作流的执行历史
    """
    try:
        logger.info(
            f"📜 Getting execution history for workflow {workflow_id} (user: {deps.current_user.sub})"
        )

        # Get HTTP client
        settings = get_settings()

        http_client = await get_workflow_engine_client()

        # Get execution history via HTTP
        execution_data = await http_client.get_execution_history(workflow_id, limit)

        # The workflow engine returns: {"workflow_id": "...", "executions": [...], "total": N}
        # Return this directly instead of double-wrapping
        if isinstance(execution_data, dict) and "executions" in execution_data:
            logger.info(
                f"✅ Retrieved {len(execution_data.get('executions', []))} executions for workflow {workflow_id}"
            )
            return execution_data
        else:
            # Fallback for unexpected response format
            logger.info(
                f"✅ Retrieved {len(execution_data) if isinstance(execution_data, list) else 0} executions for workflow {workflow_id}"
            )
            return {
                "workflow_id": workflow_id,
                "executions": execution_data if isinstance(execution_data, list) else [],
                "total": len(execution_data) if isinstance(execution_data, list) else 0,
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting execution history for workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/executions/{execution_id}/logs/stream")
async def stream_execution_logs(
    execution_id: str, follow: bool = False, sse_deps: SSEDeps = Depends()
) -> StreamingResponse:
    """
    Stream execution logs in real-time via Server-Sent Events (SSE)
    通过SSE实时流式传输执行日志

    Args:
        execution_id: The execution ID to stream logs for
        follow: Whether to follow live logs (default: False - returns existing logs and closes)
    """

    async def log_stream():
        """Generate SSE events for execution logs"""
        try:
            # Use SSEDeps for authentication (supports both header and URL param for SSE)
            token = sse_deps.access_token
            user = sse_deps.current_user

            logger.info(f"🔄 Starting log stream for execution {execution_id} (user: {user.sub})")

            # Get HTTP client
            http_client = await get_workflow_engine_client()

            # First, get existing logs from database
            try:
                existing_logs = await http_client.get_execution_logs(execution_id, token)

                if existing_logs:
                    # Send existing logs first
                    for log_entry in existing_logs:
                        log_event = create_sse_event(
                            event_type=SSEEventType.LOG,
                            data={
                                "execution_id": execution_id,
                                "timestamp": log_entry.get("timestamp", ""),
                                "level": log_entry.get("level", "info"),
                                "message": log_entry.get("user_friendly_message")
                                or log_entry.get("message", ""),
                                "node_id": log_entry.get("node_id"),
                                "event_type": log_entry.get("event_type", "log"),
                                "display_priority": log_entry.get("display_priority", 5),
                                "is_milestone": log_entry.get("is_milestone", False),
                                "step_number": log_entry.get("data", {}).get("step_number"),
                                "total_steps": log_entry.get("data", {}).get("total_steps"),
                            },
                            session_id=execution_id,
                            is_final=False,
                        )
                        yield format_sse_event(log_event.model_dump())

                        # Small delay to prevent overwhelming the client
                        await asyncio.sleep(0.01)

                # Send initial completion event if not following
                if not follow:
                    completion_event = create_sse_event(
                        event_type=SSEEventType.COMPLETE,
                        data={
                            "execution_id": execution_id,
                            "message": "Historical logs retrieved",
                            "total_logs": len(existing_logs) if existing_logs else 0,
                        },
                        session_id=execution_id,
                        is_final=True,
                    )
                    yield format_sse_event(completion_event.model_dump())
                    return

            except Exception as e:
                logger.error(f"❌ Error retrieving existing logs for {execution_id}: {e}")

                # Send error event
                error_event = create_sse_event(
                    event_type=SSEEventType.ERROR,
                    data={
                        "execution_id": execution_id,
                        "error": f"Failed to retrieve logs: {str(e)}",
                        "error_type": "log_retrieval_error",
                    },
                    session_id=execution_id,
                    is_final=True,
                )
                yield format_sse_event(error_event.model_dump())
                return

            # If following, set up real-time streaming
            if follow:
                logger.info(f"📡 Setting up real-time log streaming for execution {execution_id}")

                # Connect to workflow engine's log stream
                try:
                    async for log_chunk in http_client.stream_execution_logs(execution_id, token):
                        if log_chunk:
                            # Process each log entry from the stream
                            log_data = (
                                log_chunk if isinstance(log_chunk, dict) else json.loads(log_chunk)
                            )

                            # Create SSE event for real-time log
                            realtime_event = create_sse_event(
                                event_type=SSEEventType.LOG,
                                data={
                                    "execution_id": execution_id,
                                    "timestamp": log_data.get("timestamp", ""),
                                    "level": log_data.get("level", "info"),
                                    "message": log_data.get("user_friendly_message")
                                    or log_data.get("message", ""),
                                    "node_id": log_data.get("node_id"),
                                    "event_type": log_data.get("event_type", "log"),
                                    "display_priority": log_data.get("display_priority", 5),
                                    "is_milestone": log_data.get("is_milestone", False),
                                    "step_number": log_data.get("data", {}).get("step_number"),
                                    "total_steps": log_data.get("data", {}).get("total_steps"),
                                    "is_realtime": True,
                                },
                                session_id=execution_id,
                                is_final=False,
                            )
                            yield format_sse_event(realtime_event.model_dump())

                except asyncio.CancelledError:
                    logger.info(f"🛑 Log stream cancelled for execution {execution_id}")
                    return
                except Exception as e:
                    logger.error(f"❌ Error in real-time log streaming for {execution_id}: {e}")

                    # Send error event
                    stream_error_event = create_sse_event(
                        event_type=SSEEventType.ERROR,
                        data={
                            "execution_id": execution_id,
                            "error": f"Real-time streaming error: {str(e)}",
                            "error_type": "stream_error",
                        },
                        session_id=execution_id,
                        is_final=True,
                    )
                    yield format_sse_event(stream_error_event.model_dump())

        except Exception as e:
            logger.error(f"❌ Fatal error in log stream for {execution_id}: {e}")

            # Send fatal error event
            fatal_error_event = create_sse_event(
                event_type=SSEEventType.ERROR,
                data={
                    "execution_id": execution_id,
                    "error": f"Fatal streaming error: {str(e)}",
                    "error_type": "fatal_error",
                },
                session_id=execution_id,
                is_final=True,
            )
            yield format_sse_event(fatal_error_event.model_dump())

    return create_sse_response(log_stream())


@router.get("/executions/{execution_id}/logs")
async def get_execution_logs(
    execution_id: str,
    limit: int = 100,
    offset: int = 0,
    level: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    deps: AuthenticatedDeps = Depends(),
):
    """
    Get execution logs (static API endpoint)
    获取执行日志（静态API端点）

    Args:
        execution_id: The execution ID to get logs for
        limit: Maximum number of logs to return (default: 100)
        offset: Number of logs to skip (default: 0)
        level: Filter by log level (optional)
        start_time: Filter logs after this time (optional)
        end_time: Filter logs before this time (optional)
    """
    try:
        logger.info(f"📋 Getting execution logs for {execution_id} (user: {deps.current_user.sub})")

        # Get HTTP client
        http_client = await get_workflow_engine_client()

        # Get execution logs via HTTP
        params = {"limit": limit, "offset": offset}
        if level:
            params["level"] = level
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time

        logs_response = await http_client.get_execution_logs(
            execution_id, deps.access_token, params
        )

        if not logs_response:
            logger.warning(f"⚠️ No logs found for execution {execution_id}")
            return {
                "execution_id": execution_id,
                "logs": [],
                "total_count": 0,
                "pagination": {"limit": limit, "offset": offset, "has_more": False},
            }

        # Transform logs for frontend compatibility
        transformed_logs = []
        for log_entry in logs_response.get("logs", []):
            transformed_log = {
                "id": log_entry.get("id"),
                "execution_id": execution_id,
                "timestamp": log_entry.get("timestamp") or log_entry.get("created_at"),
                "level": log_entry.get("level", "info"),
                "message": log_entry.get("user_friendly_message") or log_entry.get("message", ""),
                "event_type": log_entry.get("event_type", "log"),
                "node_id": log_entry.get("node_id"),
                "node_name": log_entry.get("node_name"),
                "display_priority": log_entry.get("display_priority", 5),
                "is_milestone": log_entry.get("is_milestone", False),
                "data": log_entry.get("data", {}),
                # Include step information from data
                "step_number": log_entry.get("step_number")
                or log_entry.get("data", {}).get("step_number"),
                "total_steps": log_entry.get("total_steps")
                or log_entry.get("data", {}).get("total_steps"),
            }
            transformed_logs.append(transformed_log)

        result = {
            "execution_id": execution_id,
            "logs": transformed_logs,
            "total_count": logs_response.get("total_count", len(transformed_logs)),
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": logs_response.get("pagination", {}).get("has_more", False),
            },
        }

        logger.info(f"✅ Retrieved {len(transformed_logs)} logs for execution {execution_id}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting execution logs for {execution_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
