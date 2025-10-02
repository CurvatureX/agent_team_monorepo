"""
Unified Log Service for workflow_engine_v2.

Provides centralized logging for workflow executions with structured data.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models import ExecutionStatus
from shared.models.supabase import create_supabase_client


class UnifiedLogServiceV2:
    """Unified logging service for workflow executions."""

    def __init__(self):
        """Initialize the unified log service."""
        self.logger = logging.getLogger(__name__)
        self.supabase = None
        self.in_memory_logs = []  # Fallback storage

        # Initialize Supabase connection
        try:
            self.supabase = create_supabase_client()
            if self.supabase:
                self.logger.info("Unified Log Service: Using Supabase for persistence")
            else:
                self.logger.warning(
                    "Unified Log Service: Supabase not available, using in-memory storage"
                )
        except Exception as e:
            self.logger.warning(f"Unified Log Service: Failed to initialize Supabase: {e}")

    async def log_execution_event(
        self,
        execution_id: str,
        event_type: str,
        event_data: Dict[str, Any],
        node_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        user_id: Optional[str] = None,
        level: str = "INFO",
    ) -> bool:
        """
        Log an execution event.

        Args:
            execution_id: Unique execution identifier
            event_type: Type of event (start, complete, error, node_execution, etc.)
            event_data: Structured event data
            node_id: Optional node identifier
            workflow_id: Optional workflow identifier
            user_id: Optional user identifier
            level: Log level (DEBUG, INFO, WARNING, ERROR)

        Returns:
            bool: Success status
        """
        try:
            log_entry = {
                "execution_id": execution_id,
                "event_type": event_type,
                "event_data": event_data,
                "node_id": node_id,
                "workflow_id": workflow_id,
                "user_id": user_id,
                "level": level,
                "created_at": datetime.utcnow().isoformat(),
                "source": "workflow_engine_v2",
            }

            # Store in database if available
            if self.supabase:
                try:
                    result = self.supabase.table("execution_logs").insert(log_entry).execute()
                    if result.data:
                        return True
                except Exception as e:
                    self.logger.error(f"Failed to store log in Supabase: {e}")

            # Fallback to in-memory storage
            self.in_memory_logs.append(log_entry)

            # Keep only recent logs in memory to prevent memory issues
            if len(self.in_memory_logs) > 1000:
                self.in_memory_logs = self.in_memory_logs[-500:]

            return True

        except Exception as e:
            self.logger.error(f"Error logging execution event: {e}")
            return False

    async def log_workflow_start(
        self,
        execution_id: str,
        workflow_id: str,
        user_id: str,
        trigger_data: Dict[str, Any],
    ) -> bool:
        """Log workflow execution start."""
        return await self.log_execution_event(
            execution_id=execution_id,
            event_type="workflow_start",
            event_data={
                "trigger_data": trigger_data,
                "status": "started",
            },
            workflow_id=workflow_id,
            user_id=user_id,
        )

    async def log_workflow_complete(
        self,
        execution_id: str,
        workflow_id: str,
        status: ExecutionStatus,
        execution_time_ms: float,
        node_count: int,
        error_message: Optional[str] = None,
    ) -> bool:
        """Log workflow execution completion."""
        return await self.log_execution_event(
            execution_id=execution_id,
            event_type="workflow_complete",
            event_data={
                "status": status.value,
                "execution_time_ms": execution_time_ms,
                "node_count": node_count,
                "error_message": error_message,
            },
            workflow_id=workflow_id,
        )

    async def log_node_execution(
        self,
        execution_id: str,
        node_id: str,
        node_type: str,
        status: ExecutionStatus,
        execution_time_ms: float,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Log individual node execution."""
        event_data = {
            "node_type": node_type,
            "status": status.value,
            "execution_time_ms": execution_time_ms,
        }

        # Add optional data (with size limits to prevent large logs)
        if input_data:
            event_data["input_data"] = self._truncate_data(input_data, max_size=1000)
        if output_data:
            event_data["output_data"] = self._truncate_data(output_data, max_size=1000)
        if error_message:
            event_data["error_message"] = error_message[:500]  # Limit error message length
        if error_details:
            event_data["error_details"] = self._truncate_data(error_details, max_size=500)

        level = "ERROR" if status == ExecutionStatus.ERROR else "INFO"

        return await self.log_execution_event(
            execution_id=execution_id,
            event_type="node_execution",
            event_data=event_data,
            node_id=node_id,
            level=level,
        )

    async def log_user_interaction(
        self,
        execution_id: str,
        interaction_type: str,
        interaction_data: Dict[str, Any],
        node_id: Optional[str] = None,
    ) -> bool:
        """Log human-in-the-loop or user interactions."""
        return await self.log_execution_event(
            execution_id=execution_id,
            event_type="user_interaction",
            event_data={
                "interaction_type": interaction_type,
                "interaction_data": self._truncate_data(interaction_data, max_size=1000),
            },
            node_id=node_id,
        )

    async def log_external_api_call(
        self,
        execution_id: str,
        node_id: str,
        api_provider: str,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: float,
        error_message: Optional[str] = None,
    ) -> bool:
        """Log external API calls."""
        level = "ERROR" if status_code >= 400 else "INFO"

        return await self.log_execution_event(
            execution_id=execution_id,
            event_type="external_api_call",
            event_data={
                "api_provider": api_provider,
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "response_time_ms": response_time_ms,
                "error_message": error_message,
            },
            node_id=node_id,
            level=level,
        )

    async def get_execution_logs(
        self,
        execution_id: str,
        event_type: Optional[str] = None,
        level: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve logs for a specific execution.

        Args:
            execution_id: Execution identifier
            event_type: Optional filter by event type
            level: Optional filter by log level
            limit: Maximum number of logs to return

        Returns:
            List of log entries
        """
        try:
            logs = []

            # Try Supabase first
            if self.supabase:
                try:
                    query = (
                        self.supabase.table("execution_logs")
                        .select("*")
                        .eq("execution_id", execution_id)
                    )

                    if event_type:
                        query = query.eq("event_type", event_type)
                    if level:
                        query = query.eq("level", level)

                    result = query.order("created_at", desc=True).limit(limit).execute()

                    if result.data:
                        logs = result.data

                except Exception as e:
                    self.logger.error(f"Failed to retrieve logs from Supabase: {e}")

            # Fallback to in-memory logs
            if not logs:
                logs = [
                    log
                    for log in self.in_memory_logs
                    if log["execution_id"] == execution_id
                    and (not event_type or log["event_type"] == event_type)
                    and (not level or log["level"] == level)
                ]
                logs = logs[-limit:]  # Get most recent

            return logs

        except Exception as e:
            self.logger.error(f"Error retrieving execution logs: {e}")
            return []

    async def get_workflow_logs(
        self,
        workflow_id: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve logs for all executions of a specific workflow.

        Args:
            workflow_id: Workflow identifier
            start_time: Optional start time filter (ISO format)
            end_time: Optional end time filter (ISO format)
            limit: Maximum number of logs to return

        Returns:
            List of log entries
        """
        try:
            logs = []

            # Try Supabase first
            if self.supabase:
                try:
                    query = (
                        self.supabase.table("execution_logs")
                        .select("*")
                        .eq("workflow_id", workflow_id)
                    )

                    if start_time:
                        query = query.gte("created_at", start_time)
                    if end_time:
                        query = query.lte("created_at", end_time)

                    result = query.order("created_at", desc=True).limit(limit).execute()

                    if result.data:
                        logs = result.data

                except Exception as e:
                    self.logger.error(f"Failed to retrieve workflow logs from Supabase: {e}")

            # Fallback to in-memory logs
            if not logs:
                logs = [log for log in self.in_memory_logs if log.get("workflow_id") == workflow_id]

                # Apply time filters if specified
                if start_time or end_time:
                    filtered_logs = []
                    for log in logs:
                        log_time = log["created_at"]
                        if start_time and log_time < start_time:
                            continue
                        if end_time and log_time > end_time:
                            continue
                        filtered_logs.append(log)
                    logs = filtered_logs

                logs = logs[-limit:]  # Get most recent

            return logs

        except Exception as e:
            self.logger.error(f"Error retrieving workflow logs: {e}")
            return []

    async def get_execution_summary(self, execution_id: str) -> Dict[str, Any]:
        """Get a summary of an execution."""
        try:
            logs = await self.get_execution_logs(execution_id)

            if not logs:
                return {"execution_id": execution_id, "status": "not_found"}

            # Analyze logs to create summary
            start_log = next((log for log in logs if log["event_type"] == "workflow_start"), None)
            complete_log = next(
                (log for log in logs if log["event_type"] == "workflow_complete"), None
            )
            node_logs = [log for log in logs if log["event_type"] == "node_execution"]
            error_logs = [log for log in logs if log["level"] == "ERROR"]

            summary = {
                "execution_id": execution_id,
                "total_logs": len(logs),
                "node_executions": len(node_logs),
                "errors": len(error_logs),
                "start_time": start_log["created_at"] if start_log else None,
                "end_time": complete_log["created_at"] if complete_log else None,
                "status": complete_log["event_data"]["status"] if complete_log else "running",
            }

            if complete_log:
                summary["execution_time_ms"] = complete_log["event_data"].get("execution_time_ms")

            if error_logs:
                summary["latest_error"] = error_logs[0]["event_data"].get("error_message")

            return summary

        except Exception as e:
            self.logger.error(f"Error getting execution summary: {e}")
            return {"execution_id": execution_id, "status": "error", "error": str(e)}

    def _truncate_data(self, data: Any, max_size: int = 1000) -> Any:
        """Truncate data to prevent overly large log entries."""
        try:
            serialized = json.dumps(data, default=str)
            if len(serialized) <= max_size:
                return data

            # If too large, return a truncated representation
            if isinstance(data, dict):
                truncated = {}
                for key, value in data.items():
                    key_str = str(key)[:50]  # Limit key length
                    if isinstance(value, (str, int, float, bool)):
                        truncated[key_str] = value
                    else:
                        truncated[key_str] = f"<truncated {type(value).__name__}>"

                    # Check if we're getting close to limit
                    if len(json.dumps(truncated, default=str)) > max_size - 100:
                        break

                return truncated
            elif isinstance(data, list):
                return data[:10]  # Take first 10 items
            else:
                return str(data)[:max_size]

        except Exception:
            return f"<serialization error: {type(data).__name__}>"


__all__ = ["UnifiedLogServiceV2"]
