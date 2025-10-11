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


@router.get("/executions/recent_logs")
async def get_recent_execution_logs(
    workflow_id: str,
    limit: int = 100,
    include_all_executions: bool = False,
    deps: AuthenticatedDeps = Depends(),
):
    """
    Get the latest execution with its detailed logs for a workflow.
    返回工作流最新执行及其详细日志

    This API returns the most recent execution along with comprehensive logs,
    replacing the old behavior of just returning execution IDs.

    Query params:
      - workflow_id: required workflow ID
      - limit: maximum number of logs to return for the latest execution (default 100, max 1000)
      - include_all_executions: if true, return logs from multiple recent executions (default: false)

    Returns:
      - latest_execution: Details of the most recent execution
      - logs: Detailed execution logs with user-friendly messages
      - summary: Log statistics and counts
      - executions: (optional) List of other recent executions if include_all_executions=true
    """
    try:
        # Clamp limit between 1 and 1000
        limit = max(1, min(limit, 1000))

        logger.info(
            f"📋 Getting recent execution logs for workflow {workflow_id} (user: {deps.current_user.sub}, limit: {limit})"
        )

        http_client = await get_workflow_engine_client()

        # Fetch execution history from workflow engine (get at least 1 to find latest)
        execution_history_limit = 10 if include_all_executions else 1
        execution_data = await http_client.get_execution_history(
            workflow_id, execution_history_limit
        )

        # Extract executions from response
        if isinstance(execution_data, dict):
            executions = execution_data.get("executions", [])
        elif isinstance(execution_data, list):
            executions = execution_data
        else:
            executions = []

        # If no executions found, return empty response
        if not executions:
            logger.info(f"⚠️ No executions found for workflow {workflow_id}")
            return {
                "workflow_id": workflow_id,
                "latest_execution": None,
                "logs": [],
                "summary": {
                    "total_logs": 0,
                    "error_count": 0,
                    "warning_count": 0,
                    "milestone_count": 0,
                },
                "message": "No executions found for this workflow",
            }

        # Get the latest execution (first in the list, as it's ordered by most recent)
        latest_execution_data = executions[0]
        latest_execution_id = latest_execution_data.get(
            "execution_id"
        ) or latest_execution_data.get("id")

        logger.info(f"📊 Latest execution found: {latest_execution_id}")

        # Helper to format duration
        def format_duration_from_execution(execution: Dict[str, Any]) -> Optional[str]:
            try:
                duration_ms = execution.get("duration_ms")
                if duration_ms is not None:
                    try:
                        return f"{float(duration_ms) / 1000:.1f}s"
                    except Exception:
                        pass

                start_time = execution.get("start_time") or execution.get("created_at")
                end_time = execution.get("end_time") or execution.get("updated_at")

                if not start_time or not end_time:
                    return None  # Still running

                from datetime import datetime

                def _parse(t: Any) -> Optional[datetime]:
                    if t is None:
                        return None
                    if isinstance(t, (int, float)):
                        return datetime.fromtimestamp(
                            float(t) / 1000 if float(t) > 10000000000 else float(t)
                        )
                    if isinstance(t, str):
                        try:
                            return datetime.fromisoformat(t.replace("Z", "+00:00"))
                        except Exception:
                            return None
                    return None

                s = _parse(start_time)
                e = _parse(end_time)
                if s and e:
                    return f"{(e - s).total_seconds():.1f}s"
            except Exception:
                pass
            return None

        # Format latest execution details
        latest_execution = {
            "execution_id": latest_execution_id,
            "status": latest_execution_data.get("status"),
            "start_time": latest_execution_data.get("start_time")
            or latest_execution_data.get("created_at"),
            "end_time": latest_execution_data.get("end_time")
            or latest_execution_data.get("updated_at"),
            "duration": format_duration_from_execution(latest_execution_data),
            "error_message": latest_execution_data.get("error_message")
            or latest_execution_data.get("error"),
        }

        # Fetch detailed logs for the latest execution
        try:
            logs_response = await http_client.get_execution_logs(
                latest_execution_id, deps.access_token, {"limit": limit, "offset": 0}
            )

            detailed_logs = []
            if logs_response and logs_response.get("logs"):
                for log_entry in logs_response.get("logs", []):
                    detailed_log = {
                        "id": log_entry.get("id"),
                        "timestamp": log_entry.get("timestamp") or log_entry.get("created_at"),
                        "level": log_entry.get("level", "info"),
                        "message": log_entry.get("user_friendly_message")
                        or log_entry.get("message", ""),
                        "event_type": log_entry.get("event_type", "log"),
                        "node_id": log_entry.get("node_id"),
                        "node_name": log_entry.get("node_name"),
                        "is_milestone": log_entry.get("is_milestone", False),
                        "display_priority": log_entry.get("display_priority", 5),
                        "step_number": log_entry.get("step_number")
                        or log_entry.get("data", {}).get("step_number"),
                        "total_steps": log_entry.get("total_steps")
                        or log_entry.get("data", {}).get("total_steps"),
                    }
                    detailed_logs.append(detailed_log)

            # Calculate summary statistics
            summary = {
                "total_logs": len(detailed_logs),
                "error_count": sum(
                    1 for log in detailed_logs if log.get("level", "").lower() == "error"
                ),
                "warning_count": sum(
                    1 for log in detailed_logs if log.get("level", "").lower() == "warning"
                ),
                "milestone_count": sum(1 for log in detailed_logs if log.get("is_milestone")),
            }

            logger.info(
                f"✅ Retrieved {len(detailed_logs)} logs for latest execution {latest_execution_id} "
                f"(errors: {summary['error_count']}, warnings: {summary['warning_count']}, milestones: {summary['milestone_count']})"
            )

        except Exception as log_error:
            logger.warning(
                f"⚠️ Failed to fetch logs for execution {latest_execution_id}: {log_error}"
            )
            detailed_logs = []
            summary = {
                "total_logs": 0,
                "error_count": 0,
                "warning_count": 0,
                "milestone_count": 0,
            }

        # Build response
        response = {
            "workflow_id": workflow_id,
            "latest_execution": latest_execution,
            "logs": detailed_logs,
            "summary": summary,
        }

        # Optionally include other recent executions
        if include_all_executions and len(executions) > 1:
            other_executions = []
            for execution in executions[1:]:  # Skip the first one (latest)
                other_execution = {
                    "execution_id": execution.get("execution_id") or execution.get("id"),
                    "status": execution.get("status"),
                    "start_time": execution.get("start_time") or execution.get("created_at"),
                    "end_time": execution.get("end_time") or execution.get("updated_at"),
                    "duration": format_duration_from_execution(execution),
                    "error_message": execution.get("error_message") or execution.get("error"),
                }
                other_executions.append(other_execution)

            response["other_executions"] = other_executions
            response["total_executions"] = len(executions)

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting recent execution logs: {e}")
        import traceback

        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/executions/{execution_id}", response_model=Execution)
async def get_execution_status(execution_id: str, deps: AuthenticatedDeps = Depends()):
    """
    Get execution status with user access control
    获取执行状态（支持用户访问控制）
    """
    try:
        # Use DEBUG level for frequent polling operations
        logger.debug(f"📊 Getting execution status {execution_id} for user {deps.current_user.sub}")

        # Get HTTP client
        settings = get_settings()

        http_client = await get_workflow_engine_client()

        # Get execution status via HTTP
        result = await http_client.get_execution_status(execution_id)
        if not result or result.get("error"):
            raise NotFoundError("Execution")

        logger.debug(f"✅ Execution status retrieved: {execution_id}")

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


@router.get("/executions/recent")
async def get_recent_executions(
    workflow_id: Optional[str] = None, limit: int = 10, deps: AuthenticatedDeps = Depends()
):
    """
    Get recent execution logs/summaries
    获取最近的执行日志/摘要

    Args:
        workflow_id: Optional workflow ID to filter executions
        limit: Maximum number of executions to return (default: 10, max: 50)
    """
    try:
        # Clamp limit to reasonable bounds
        limit = max(1, min(limit, 50))

        logger.info(
            f"📋 Getting recent executions (workflow_id: {workflow_id or 'all'}, limit: {limit}, user: {deps.current_user.sub})"
        )

        # Get HTTP client
        http_client = await get_workflow_engine_client()

        # Get execution history via HTTP
        if workflow_id:
            execution_data = await http_client.get_execution_history(workflow_id, limit)
        else:
            # TODO: Implement get all recent executions across workflows in workflow engine
            # For now, return empty if no workflow_id
            execution_data = {"executions": [], "total": 0}

        # Extract executions list
        if isinstance(execution_data, dict):
            executions = execution_data.get("executions", [])
        elif isinstance(execution_data, list):
            executions = execution_data
        else:
            executions = []

        # Transform executions to simplified format for logs display
        recent_logs = []
        for execution in executions:
            log_entry = {
                "execution_id": execution.get("execution_id") or execution.get("id"),
                "workflow_id": execution.get("workflow_id"),
                "status": execution.get("status"),
                "start_time": execution.get("start_time") or execution.get("created_at"),
                "end_time": execution.get("end_time") or execution.get("updated_at"),
                "duration_ms": execution.get("duration_ms"),
                "error_message": execution.get("error_message") or execution.get("error"),
            }

            # Calculate duration if not provided
            if not log_entry["duration_ms"] and log_entry["start_time"] and log_entry["end_time"]:
                try:
                    from datetime import datetime

                    start = (
                        datetime.fromisoformat(log_entry["start_time"].replace("Z", "+00:00"))
                        if isinstance(log_entry["start_time"], str)
                        else datetime.fromtimestamp(log_entry["start_time"])
                    )
                    end = (
                        datetime.fromisoformat(log_entry["end_time"].replace("Z", "+00:00"))
                        if isinstance(log_entry["end_time"], str)
                        else datetime.fromtimestamp(log_entry["end_time"])
                    )
                    log_entry["duration_ms"] = int((end - start).total_seconds() * 1000)
                except Exception:
                    pass

            recent_logs.append(log_entry)

        result = {
            "workflow_id": workflow_id,
            "executions": recent_logs,
            "total": len(recent_logs),
            "limit": limit,
        }

        logger.info(f"✅ Retrieved {len(recent_logs)} recent executions")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting recent executions: {e}")
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

        # Workflow engine v2 returns {"executions": [...], "total_count": N, "has_more": bool}
        if isinstance(execution_data, dict):
            executions = execution_data.get("executions", [])
            logger.info(f"✅ Retrieved {len(executions)} executions for workflow {workflow_id}")
            # Ensure workflow_id is included in response
            execution_data.setdefault("workflow_id", workflow_id)
            return execution_data
        elif isinstance(execution_data, list):
            logger.info(f"✅ Retrieved {len(execution_data)} executions for workflow {workflow_id}")
            return {
                "workflow_id": workflow_id,
                "executions": execution_data,
                "total_count": len(execution_data),
                "has_more": False,
            }
        else:
            logger.info(f"✅ Retrieved 0 executions for workflow {workflow_id}")
            return {
                "workflow_id": workflow_id,
                "executions": [],
                "total_count": 0,
                "has_more": False,
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting execution history for workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/executions/{execution_id}/logs/stream")
async def stream_execution_logs(
    execution_id: str, follow: bool = True, sse_deps: SSEDeps = Depends()
) -> StreamingResponse:
    """
    Stream execution logs in real-time via Server-Sent Events (SSE)
    通过SSE实时流式传输执行日志

    - If execution is RUNNING: streams logs in real-time via database polling every 1 second
    - If execution is FINISHED: returns all logs from database
    - Auto-detects execution status

    Args:
        execution_id: The execution ID to stream logs for
        follow: Whether to follow live logs (default: True for real-time updates)
    """

    async def log_stream():
        """Generate SSE events for execution logs"""
        try:
            import time

            # Use SSEDeps for authentication (supports both header and URL param for SSE)
            token = sse_deps.access_token
            user = sse_deps.current_user

            logger.info(f"🔄 Starting log stream for execution {execution_id} (user: {user.sub})")

            # Get HTTP client
            http_client = await get_workflow_engine_client()

            # Check execution status to determine streaming mode
            try:
                execution_status_data = await http_client.get_execution_status(execution_id)
                execution_status = execution_status_data.get("status", "UNKNOWN")
                logger.info(f"🐛 DEBUG: Status data from workflow engine: {execution_status_data}")
            except Exception as e:
                execution_status = "UNKNOWN"
                logger.error(f"🐛 DEBUG: Exception getting status: {e}")

            is_running = execution_status in ["NEW", "RUNNING", "WAITING_FOR_HUMAN", "PAUSED"]

            logger.info(
                f"📊 Execution {execution_id} status: {execution_status} (is_running: {is_running})"
            )

            # Track sent log IDs to avoid duplicates
            sent_log_ids = set()

            # Helper to format log entry
            def format_log_entry(log_entry: Dict[str, Any]) -> Dict[str, Any]:
                return {
                    "id": log_entry.get("id"),
                    "timestamp": log_entry.get("timestamp") or log_entry.get("created_at"),
                    "node_name": log_entry.get("node_name"),
                    "event_type": log_entry.get("event_type"),
                    "message": log_entry.get("user_friendly_message") or log_entry.get("message"),
                    "level": log_entry.get("level"),
                    "data": log_entry.get("data", {}),
                }

            # Get initial logs from database
            try:
                initial_logs_response = await http_client.get_execution_logs(
                    execution_id, token, {"limit": 1000, "offset": 0}
                )
                existing_logs = initial_logs_response.get("logs", [])
                logger.info(
                    f"🐛 DEBUG: Logs response: total_count={initial_logs_response.get('total_count')}, logs_length={len(existing_logs)}"
                )

                # Send initial logs
                for log_entry in existing_logs:
                    log_id = log_entry.get("id")
                    if log_id:
                        sent_log_ids.add(log_id)

                    log_event = create_sse_event(
                        event_type=SSEEventType.LOG,
                        data=format_log_entry(log_entry),
                        session_id=execution_id,
                        is_final=False,
                    )
                    yield format_sse_event(log_event.model_dump())
                    await asyncio.sleep(0.01)  # Small delay

                logger.info(
                    f"✅ Sent {len(existing_logs)} initial logs for execution {execution_id}"
                )

            except Exception as e:
                logger.warning(f"⚠️ Error retrieving initial logs for {execution_id}: {e}")
                # Continue anyway, will try to poll

            # Real-time streaming mode: poll database while execution is running
            if is_running and follow:
                logger.info(f"📡 Real-time streaming mode for {execution_id}")

                poll_interval = 0.5  # 500ms for responsive real-time updates
                last_poll_time = time.time()
                last_new_log_time = time.time()  # Track when we last received new logs
                inactivity_timeout = 300  # 5 minutes of no new logs before disconnect
                start_time = time.time()

                while True:
                    # Check if no new logs for 5 minutes - disconnect
                    if time.time() - last_new_log_time > inactivity_timeout:
                        logger.info(
                            f"⏱️ No new logs for {inactivity_timeout}s, disconnecting stream for {execution_id}"
                        )
                        # Send timeout completion event
                        timeout_event = create_sse_event(
                            event_type=SSEEventType.COMPLETE,
                            data={
                                "execution_id": execution_id,
                                "message": f"No new logs for {inactivity_timeout//60} minutes",
                                "total_logs": len(sent_log_ids),
                                "reason": "inactivity_timeout",
                            },
                            session_id=execution_id,
                            is_final=True,
                        )
                        yield format_sse_event(timeout_event.model_dump())
                        break

                    current_time = time.time()

                    # Poll database every 3 seconds for new logs
                    if current_time - last_poll_time >= poll_interval:
                        try:
                            # Get latest logs
                            new_logs_response = await http_client.get_execution_logs(
                                execution_id, token, {"limit": 100, "offset": 0}
                            )
                            new_logs = new_logs_response.get("logs", [])

                            # Send new logs that haven't been sent yet
                            new_count = 0
                            for log_entry in new_logs:
                                log_id = log_entry.get("id")
                                if log_id and log_id not in sent_log_ids:
                                    sent_log_ids.add(log_id)
                                    new_count += 1

                                    log_event = create_sse_event(
                                        event_type=SSEEventType.LOG,
                                        data={
                                            **format_log_entry(log_entry),
                                            "is_realtime": True,
                                        },
                                        session_id=execution_id,
                                        is_final=False,
                                    )
                                    yield format_sse_event(log_event.model_dump())

                            if new_count > 0:
                                logger.debug(f"📨 Sent {new_count} new logs for {execution_id}")
                                # Update last new log time since we received new logs
                                last_new_log_time = time.time()

                            # Check if execution finished
                            status_check = await http_client.get_execution_status(execution_id)
                            current_status = status_check.get("status", "UNKNOWN")

                            if current_status not in [
                                "NEW",
                                "RUNNING",
                                "WAITING_FOR_HUMAN",
                                "PAUSED",
                            ]:
                                logger.info(
                                    f"✅ Execution {execution_id} finished with status: {current_status}"
                                )

                                # CRITICAL: Wait for flush_sync() to complete by polling one more time
                                # The workflow engine flushes logs at the end of execution,
                                # but we need to give it time to complete
                                await asyncio.sleep(0.5)  # Brief delay for flush

                                # Final poll to get any remaining logs that were just flushed
                                try:
                                    final_logs_response = await http_client.get_execution_logs(
                                        execution_id, token, {"limit": 100, "offset": 0}
                                    )
                                    final_logs = final_logs_response.get("logs", [])

                                    # Send any new logs that appeared after the status change
                                    for log_entry in final_logs:
                                        log_id = log_entry.get("id")
                                        if log_id and log_id not in sent_log_ids:
                                            sent_log_ids.add(log_id)

                                            log_event = create_sse_event(
                                                event_type=SSEEventType.LOG,
                                                data={
                                                    **format_log_entry(log_entry),
                                                    "is_realtime": True,
                                                },
                                                session_id=execution_id,
                                                is_final=False,
                                            )
                                            yield format_sse_event(log_event.model_dump())

                                    logger.info(
                                        f"📨 Final poll found {len(final_logs) - (len(sent_log_ids) - len(final_logs))} additional logs"
                                    )
                                except Exception as final_poll_error:
                                    logger.warning(f"⚠️ Final poll failed: {final_poll_error}")

                                # Send completion event with updated log count
                                completion_event = create_sse_event(
                                    event_type=SSEEventType.COMPLETE,
                                    data={
                                        "execution_id": execution_id,
                                        "status": current_status,
                                        "message": "Execution completed",
                                        "total_logs": len(sent_log_ids),
                                    },
                                    session_id=execution_id,
                                    is_final=True,
                                )
                                yield format_sse_event(completion_event.model_dump())
                                break

                            last_poll_time = current_time

                        except asyncio.CancelledError:
                            logger.info(f"🛑 Log stream cancelled for {execution_id}")
                            return
                        except Exception as poll_error:
                            logger.error(f"❌ Polling error for {execution_id}: {poll_error}")
                            # Continue polling despite errors

                    # Small sleep to prevent tight loop
                    await asyncio.sleep(0.1)

            else:
                # Historical mode: execution is finished, send completion event
                logger.info(f"📚 Historical mode for {execution_id}")
                completion_event = create_sse_event(
                    event_type=SSEEventType.COMPLETE,
                    data={
                        "execution_id": execution_id,
                        "status": execution_status,
                        "message": "Historical logs retrieved",
                        "total_logs": len(sent_log_ids),
                    },
                    session_id=execution_id,
                    is_final=True,
                )
                yield format_sse_event(completion_event.model_dump())

        except Exception as e:
            logger.error(f"❌ Fatal error in log stream for {execution_id}: {e}")
            import traceback

            logger.error(f"❌ Traceback: {traceback.format_exc()}")

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
