"""
Workflow Status Manager for workflow_engine_v2.

Manages workflow execution status, state transitions, and notifications.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models import ExecutionStatus
from shared.models.supabase import create_supabase_client

from .events import get_event_bus


class WorkflowStatusManagerV2:
    """Manages workflow execution status and state transitions."""

    def __init__(self):
        """Initialize the workflow status manager."""
        self.logger = logging.getLogger(__name__)
        self.supabase = None
        self.event_bus = get_event_bus()

        # In-memory status cache
        self.status_cache = {}  # execution_id -> status_info

        # Initialize Supabase connection
        try:
            self.supabase = create_supabase_client()
            if self.supabase:
                self.logger.info("Workflow Status Manager: Using Supabase for persistence")
            else:
                self.logger.warning(
                    "Workflow Status Manager: Supabase not available, using cache only"
                )
        except Exception as e:
            self.logger.warning(f"Workflow Status Manager: Failed to initialize Supabase: {e}")

    def _normalize_status_payload(self, status_info: Dict[str, Any]) -> Dict[str, Any]:
        """Convert database-friendly fields into API schema friendly values."""
        normalized = dict(status_info) if status_info else {}

        for key in ["created_at", "updated_at"]:
            value = normalized.get(key)
            if isinstance(value, str):
                try:
                    normalized[key] = int(datetime.fromisoformat(value).timestamp() * 1000)
                except ValueError:
                    # Leave original value when conversion fails
                    pass

        return normalized

    async def update_execution_status(
        self,
        execution_id: str,
        status: ExecutionStatus,
        workflow_id: Optional[str] = None,
        node_id: Optional[str] = None,
        progress_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """
        Update the status of a workflow execution.

        Args:
            execution_id: Execution identifier
            status: New execution status
            workflow_id: Optional workflow identifier
            node_id: Optional current node identifier
            progress_data: Optional progress information
            error_message: Optional error message

        Returns:
            bool: Success status
        """
        try:
            timestamp = datetime.utcnow()

            # Prepare status update
            status_info = {
                "execution_id": execution_id,
                "status": status.value,
                "workflow_id": workflow_id,
                "current_node_id": node_id,
                "progress_data": progress_data or {},
                "error_message": error_message,
                "updated_at": timestamp.isoformat(),
            }

            # Update cache
            self.status_cache[execution_id] = status_info

            # Persist to database if available
            if self.supabase:
                try:
                    # Update or insert execution status
                    result = self.supabase.table("execution_status").upsert(status_info).execute()

                    if not result.data:
                        self.logger.warning(
                            f"Failed to persist status update for execution {execution_id}"
                        )

                except Exception as e:
                    self.logger.error(f"Error persisting status update: {e}")

            # Publish status update event
            self._publish_status_event(execution_id, status, status_info)

            self.logger.debug(f"Updated execution {execution_id} status to {status.value}")
            return True

        except Exception as e:
            self.logger.error(f"Error updating execution status: {e}")
            return False

    async def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of an execution."""
        try:
            # Check cache first
            if execution_id in self.status_cache:
                return self._normalize_status_payload(self.status_cache[execution_id])

            # Query database
            if self.supabase:
                try:
                    result = (
                        self.supabase.table("execution_status")
                        .select("*")
                        .eq("execution_id", execution_id)
                        .order("updated_at", desc=True)
                        .limit(1)
                        .execute()
                    )

                    if result.data:
                        status_info = result.data[0]
                        # Cache the result
                        self.status_cache[execution_id] = status_info
                        return self._normalize_status_payload(status_info)

                except Exception as e:
                    self.logger.error(f"Error querying execution status: {e}")

            return None

        except Exception as e:
            self.logger.error(f"Error getting execution status: {e}")
            return None

    async def list_executions_by_status(
        self,
        status: ExecutionStatus,
        workflow_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List executions by status."""
        try:
            executions = []

            if self.supabase:
                try:
                    query = (
                        self.supabase.table("execution_status")
                        .select("*")
                        .eq("status", status.value)
                    )

                    if workflow_id:
                        query = query.eq("workflow_id", workflow_id)

                    result = (
                        query.order("updated_at", desc=True)
                        .range(offset, offset + limit - 1)
                        .execute()
                    )

                    if result.data:
                        executions = result.data

                except Exception as e:
                    self.logger.error(f"Error listing executions by status: {e}")

            # Fallback to cache search
            if not executions:
                cache_matches = [
                    info
                    for info in self.status_cache.values()
                    if info["status"] == status.value
                    and (not workflow_id or info.get("workflow_id") == workflow_id)
                ]
                executions = cache_matches[offset : offset + limit]

            return executions

        except Exception as e:
            self.logger.error(f"Error listing executions by status: {e}")
            return []

    async def get_workflow_execution_summary(self, workflow_id: str) -> Dict[str, Any]:
        """Get execution summary for a workflow."""
        try:
            summary = {
                "workflow_id": workflow_id,
                "total_executions": 0,
                "status_counts": {},
                "recent_executions": [],
                "avg_execution_time": None,
            }

            if self.supabase:
                try:
                    # Get all executions for this workflow
                    result = (
                        self.supabase.table("execution_status")
                        .select("*")
                        .eq("workflow_id", workflow_id)
                        .order("updated_at", desc=True)
                        .limit(100)
                        .execute()
                    )

                    if result.data:
                        executions = result.data
                        summary["total_executions"] = len(executions)

                        # Count by status
                        for execution in executions:
                            status = execution["status"]
                            summary["status_counts"][status] = (
                                summary["status_counts"].get(status, 0) + 1
                            )

                        # Recent executions (last 10)
                        summary["recent_executions"] = executions[:10]

                        # Calculate average execution time for completed executions
                        completed_times = []
                        for execution in executions:
                            if (
                                execution.get("progress_data")
                                and "execution_time_ms" in execution["progress_data"]
                            ):
                                completed_times.append(
                                    execution["progress_data"]["execution_time_ms"]
                                )

                        if completed_times:
                            summary["avg_execution_time"] = sum(completed_times) / len(
                                completed_times
                            )

                except Exception as e:
                    self.logger.error(f"Error getting workflow summary: {e}")

            return summary

        except Exception as e:
            self.logger.error(f"Error getting workflow execution summary: {e}")
            return {"workflow_id": workflow_id, "error": str(e)}

    async def cleanup_old_statuses(self, older_than_days: int = 30) -> int:
        """Clean up old execution status records."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
            cleaned_count = 0

            if self.supabase:
                try:
                    # Delete old records
                    result = (
                        self.supabase.table("execution_status")
                        .delete()
                        .lt("updated_at", cutoff_date.isoformat())
                        .execute()
                    )

                    cleaned_count = len(result.data) if result.data else 0

                except Exception as e:
                    self.logger.error(f"Error cleaning up old statuses: {e}")

            # Clean up cache
            cache_keys_to_remove = []
            for execution_id, status_info in self.status_cache.items():
                try:
                    updated_at = datetime.fromisoformat(
                        status_info["updated_at"].replace("Z", "+00:00")
                    )
                    if updated_at < cutoff_date:
                        cache_keys_to_remove.append(execution_id)
                except (ValueError, KeyError):
                    # Invalid timestamp, remove from cache
                    cache_keys_to_remove.append(execution_id)

            for key in cache_keys_to_remove:
                del self.status_cache[key]

            self.logger.info(f"Cleaned up {cleaned_count} old status records")
            return cleaned_count

        except Exception as e:
            self.logger.error(f"Error cleaning up old statuses: {e}")
            return 0

    async def get_active_executions(self) -> List[Dict[str, Any]]:
        """Get all currently active (running/waiting) executions."""
        active_statuses = [
            ExecutionStatus.RUNNING,
            ExecutionStatus.WAITING,
            ExecutionStatus.WAITING_FOR_HUMAN,
        ]

        active_executions = []
        for status in active_statuses:
            executions = await self.list_executions_by_status(status, limit=100)
            active_executions.extend(executions)

        return active_executions

    async def mark_execution_timeout(self, execution_id: str, timeout_reason: str) -> bool:
        """Mark an execution as timed out."""
        return await self.update_execution_status(
            execution_id=execution_id,
            status=ExecutionStatus.TIMEOUT,
            error_message=f"Execution timed out: {timeout_reason}",
        )

    async def mark_execution_cancelled(self, execution_id: str, cancelled_by: str) -> bool:
        """Mark an execution as cancelled."""
        return await self.update_execution_status(
            execution_id=execution_id,
            status=ExecutionStatus.CANCELLED,
            progress_data={
                "cancelled_by": cancelled_by,
                "cancelled_at": datetime.utcnow().isoformat(),
            },
        )

    def _publish_status_event(
        self, execution_id: str, status: ExecutionStatus, status_info: Dict[str, Any]
    ):
        """Publish status change event to event bus."""
        try:
            from shared.models import ExecutionUpdateEvent

            event = ExecutionUpdateEvent(
                execution_id=execution_id,
                workflow_id=status_info.get("workflow_id"),
                status=status,
                node_id=status_info.get("current_node_id"),
                timestamp=datetime.utcnow(),
                data=status_info,
            )

            self.event_bus.publish(event)

        except Exception as e:
            self.logger.warning(f"Failed to publish status event: {e}")

    async def get_status_statistics(self) -> Dict[str, Any]:
        """Get overall status statistics."""
        try:
            stats = {
                "total_executions": len(self.status_cache),
                "status_counts": {},
                "cache_size": len(self.status_cache),
            }

            # Count statuses in cache
            for status_info in self.status_cache.values():
                status = status_info["status"]
                stats["status_counts"][status] = stats["status_counts"].get(status, 0) + 1

            # Get database stats if available
            if self.supabase:
                try:
                    # Get total count
                    result = (
                        self.supabase.table("execution_status")
                        .select("status", count="exact")
                        .execute()
                    )

                    if hasattr(result, "count") and result.count is not None:
                        stats["total_executions_db"] = result.count

                    # Get status distribution
                    result = self.supabase.rpc("get_status_distribution").execute()
                    if result.data:
                        stats["status_distribution_db"] = result.data

                except Exception as e:
                    self.logger.error(f"Error getting database statistics: {e}")

            return stats

        except Exception as e:
            self.logger.error(f"Error getting status statistics: {e}")
            return {"error": str(e)}


__all__ = ["WorkflowStatusManagerV2"]
