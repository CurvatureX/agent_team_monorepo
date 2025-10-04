"""Enhanced Supabase-backed execution repository for workflow_engine_v2.

Implements comprehensive ExecutionRepository interface with full CRUD operations,
filtering, searching, and advanced database features using supabase-py.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Use absolute imports
from shared.models import Execution, ExecutionStatus
from shared.models.supabase import create_supabase_client

from workflow_engine_v2.utils.run_data import build_run_data_snapshot

from .repository import ExecutionRepository


class SupabaseExecutionRepositoryV2(ExecutionRepository):
    """Enhanced Supabase-backed execution repository."""

    def __init__(
        self,
        url: Optional[str] = None,
        key: Optional[str] = None,
        table: str = "workflow_executions",
    ) -> None:
        self._table = table
        self.logger = logging.getLogger(__name__)

        try:
            self._client = create_supabase_client()
            if self._client:
                self.logger.info("Enhanced Supabase Execution Repository initialized successfully")
            else:
                self.logger.warning(
                    "Supabase client not available - repository will have limited functionality"
                )
        except Exception as e:
            self.logger.error(f"Failed to initialize Supabase client: {e}")
            self._client = None

    def save(self, execution: Execution) -> None:
        """Save an execution to the database."""
        if not self._client:
            self.logger.warning("Cannot save execution - Supabase client not available")
            return

        try:
            status_value = (
                execution.status.value
                if hasattr(execution.status, "value")
                else str(execution.status)
            )
            trigger_info = getattr(execution, "trigger_info", None)
            trigger_data = {}
            trigger_user = None
            trigger_type = "MANUAL"
            if trigger_info:
                trigger_data = getattr(trigger_info, "trigger_data", {}) or {}
                trigger_user = getattr(trigger_info, "user_id", None)
                trigger_type = str(getattr(trigger_info, "trigger_type", "manual")).upper()

            # Map trigger types to valid execution modes
            # Database constraint allows: MANUAL, TRIGGER, WEBHOOK, RETRY
            execution_mode_map = {
                "MANUAL": "MANUAL",
                "SLACK": "TRIGGER",
                "SCHEDULE": "TRIGGER",
                "WEBHOOK": "WEBHOOK",
                "EMAIL": "TRIGGER",
                "API": "TRIGGER",
                "RETRY": "RETRY",
            }
            execution_mode = execution_mode_map.get(trigger_type, "MANUAL")

            now_iso = datetime.utcnow().isoformat()

            # Build run_data snapshot from node executions for observability dashboards
            run_data_snapshot = build_run_data_snapshot(execution)
            execution.run_data = run_data_snapshot

            execution_payload: Dict[str, Any] = {
                "execution_id": execution.execution_id,
                "workflow_id": execution.workflow_id,
                "status": status_value,
                "mode": execution_mode,
                "triggered_by": trigger_user,
                "start_time": getattr(execution, "start_time", None),
                "end_time": getattr(execution, "end_time", None),
                "run_data": run_data_snapshot,
                "metadata": {"trigger_data": trigger_data},
                "error_message": getattr(execution, "error_message", None),
                "error_details": getattr(execution, "error_details", None),
                "created_at": getattr(execution, "created_at", None) or now_iso,
                "updated_at": now_iso,
            }

            result = (
                self._client.table(self._table)
                .upsert(execution_payload, on_conflict="execution_id")
                .execute()
            )

            if not result.data:
                self.logger.warning(
                    f"No data returned when saving execution {execution.execution_id}"
                )
            else:
                self.logger.debug(f"Successfully saved execution {execution.execution_id}")

            # Update execution_status table for quick status lookups
            try:
                now_iso = datetime.utcnow().isoformat()
                status_payload = {
                    "execution_id": execution.execution_id,
                    "workflow_id": execution.workflow_id,
                    "status": status_value,
                    "current_node_id": execution.current_node_id,
                    "progress_data": {"run_data": run_data_snapshot},
                    "error_message": getattr(execution, "error_message", None),
                    "created_at": now_iso,
                    "updated_at": now_iso,
                }

                status_result = (
                    self._client.table("execution_status")
                    .upsert(status_payload, on_conflict="execution_id")
                    .execute()
                )

                if not status_result.data:
                    self.logger.debug(
                        "Execution status upsert returned no data for %s",
                        execution.execution_id,
                    )
            except Exception as status_error:
                self.logger.error(
                    "Failed to update execution_status for %s: %s",
                    execution.execution_id,
                    status_error,
                )

        except Exception as e:
            self.logger.error(f"Failed to save execution {execution.execution_id}: {e}")

    def get(self, execution_id: str) -> Optional[Execution]:
        """Get an execution by ID."""
        if not self._client:
            return None

        try:
            result = (
                self._client.table(self._table)
                .select("*")
                .eq("execution_id", execution_id)
                .limit(1)
                .execute()
            )

            if result.data:
                execution_data = result.data[0]
                return self._deserialize_execution(execution_data)

            return None

        except Exception as e:
            self.logger.error(f"Failed to get execution {execution_id}: {e}")
            return None

    def list(self, limit: int = 50, offset: int = 0) -> List[Execution]:
        """List executions with pagination."""
        if not self._client:
            return []

        try:
            result = (
                self._client.table(self._table)
                .select("*")
                .range(offset, offset + limit - 1)
                .order("start_time", desc=True)
                .execute()
            )

            executions = []
            for row in result.data or []:
                try:
                    execution = self._deserialize_execution(row)
                    if execution:
                        executions.append(execution)
                except Exception as e:
                    self.logger.warning(f"Failed to deserialize execution: {e}")
                    continue

            return executions

        except Exception as e:
            self.logger.error(f"Failed to list executions: {e}")
            return []

    def list_by_workflow(
        self, workflow_id: str, limit: int = 50, offset: int = 0
    ) -> List[Execution]:
        """List executions for a specific workflow."""
        if not self._client:
            return []

        try:
            result = (
                self._client.table(self._table)
                .select("*")
                .eq("workflow_id", workflow_id)
                .range(offset, offset + limit - 1)
                .order("start_time", desc=True)
                .execute()
            )

            executions = []
            for row in result.data or []:
                try:
                    execution = self._deserialize_execution(row)
                    if execution:
                        executions.append(execution)
                except Exception:
                    continue

            return executions

        except Exception as e:
            self.logger.error(f"Failed to list executions for workflow {workflow_id}: {e}")
            return []

    def list_by_status(
        self, status: ExecutionStatus, limit: int = 50, offset: int = 0
    ) -> List[Execution]:
        """List executions by status."""
        if not self._client:
            return []

        try:
            result = (
                self._client.table(self._table)
                .select("*")
                .eq("status", status.value)
                .range(offset, offset + limit - 1)
                .order("start_time", desc=True)
                .execute()
            )

            executions = []
            for row in result.data or []:
                try:
                    execution = self._deserialize_execution(row)
                    if execution:
                        executions.append(execution)
                except Exception:
                    continue

            return executions

        except Exception as e:
            self.logger.error(f"Failed to list executions by status {status}: {e}")
            return []

    def list_by_user(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Execution]:
        """List executions for a specific user."""
        if not self._client:
            return []

        try:
            result = (
                self._client.table(self._table)
                .select("*")
                .eq("user_id", user_id)
                .range(offset, offset + limit - 1)
                .order("start_time", desc=True)
                .execute()
            )

            executions = []
            for row in result.data or []:
                try:
                    execution = self._deserialize_execution(row)
                    if execution:
                        executions.append(execution)
                except Exception:
                    continue

            return executions

        except Exception as e:
            self.logger.error(f"Failed to list executions for user {user_id}: {e}")
            return []

    def search(
        self,
        workflow_id: Optional[str] = None,
        status: Optional[ExecutionStatus] = None,
        user_id: Optional[str] = None,
        start_time_after: Optional[datetime] = None,
        start_time_before: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Execution]:
        """Search executions with multiple filters."""
        if not self._client:
            return []

        try:
            query = self._client.table(self._table).select("*")

            # Apply filters
            if workflow_id:
                query = query.eq("workflow_id", workflow_id)
            if status:
                query = query.eq("status", status.value)
            if user_id:
                query = query.eq("user_id", user_id)
            if start_time_after:
                query = query.gte("start_time", start_time_after.isoformat())
            if start_time_before:
                query = query.lte("start_time", start_time_before.isoformat())

            result = (
                query.range(offset, offset + limit - 1).order("start_time", desc=True).execute()
            )

            executions = []
            for row in result.data or []:
                try:
                    execution = self._deserialize_execution(row)
                    if execution:
                        executions.append(execution)
                except Exception:
                    continue

            return executions

        except Exception as e:
            self.logger.error(f"Failed to search executions: {e}")
            return []

    def delete(self, execution_id: str) -> bool:
        """Delete an execution."""
        if not self._client:
            return False

        try:
            result = (
                self._client.table(self._table).delete().eq("execution_id", execution_id).execute()
            )

            success = bool(result.data)
            if success:
                self.logger.info(f"Successfully deleted execution {execution_id}")
            else:
                self.logger.warning(f"No execution found to delete: {execution_id}")

            return success

        except Exception as e:
            self.logger.error(f"Failed to delete execution {execution_id}: {e}")
            return False

    def delete_old_executions(self, older_than_days: int = 30) -> int:
        """Delete executions older than specified days."""
        if not self._client:
            return 0

        try:
            cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)

            result = (
                self._client.table(self._table)
                .delete()
                .lt("start_time", cutoff_date.isoformat())
                .execute()
            )

            deleted_count = len(result.data) if result.data else 0
            self.logger.info(
                f"Deleted {deleted_count} old executions (older than {older_than_days} days)"
            )

            return deleted_count

        except Exception as e:
            self.logger.error(f"Failed to delete old executions: {e}")
            return 0

    def get_execution_statistics(self) -> Dict[str, Any]:
        """Get execution statistics."""
        if not self._client:
            return {"error": "Supabase client not available"}

        try:
            stats = {}

            # Total count
            result = self._client.table(self._table).select("*", count="exact").execute()

            stats["total_executions"] = getattr(result, "count", 0)

            # Status distribution (would need a custom RPC function in production)
            try:
                status_result = self._client.rpc("get_execution_status_distribution").execute()
                if status_result.data:
                    stats["status_distribution"] = status_result.data
            except Exception:
                # Fallback: get recent executions and calculate distribution
                recent = self.list(limit=1000)
                status_counts = {}
                for execution in recent:
                    status = execution.status.value if hasattr(execution, "status") else "unknown"
                    status_counts[status] = status_counts.get(status, 0) + 1
                stats["status_distribution"] = status_counts

            # Recent activity (last 24 hours)
            twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
            recent_executions = self.search(start_time_after=twenty_four_hours_ago, limit=1000)
            stats["executions_last_24h"] = len(recent_executions)

            return stats

        except Exception as e:
            self.logger.error(f"Failed to get execution statistics: {e}")
            return {"error": str(e)}

    def _deserialize_execution(self, data: Dict[str, Any]) -> Optional[Execution]:
        """Convert database row to Execution object."""
        try:
            # Convert string timestamps back to datetime objects
            if "start_time" in data and isinstance(data["start_time"], str):
                data["start_time"] = datetime.fromisoformat(
                    data["start_time"].replace("Z", "+00:00")
                )
            if "end_time" in data and isinstance(data["end_time"], str):
                data["end_time"] = datetime.fromisoformat(data["end_time"].replace("Z", "+00:00"))

            return Execution(**data)

        except Exception as e:
            self.logger.error(f"Failed to deserialize execution data: {e}")
            return None

    def health_check(self) -> Dict[str, Any]:
        """Check repository health."""
        if not self._client:
            return {
                "status": "unhealthy",
                "error": "Supabase client not available",
                "timestamp": datetime.utcnow().isoformat(),
            }

        try:
            # Try a simple query
            result = self._client.table(self._table).select("execution_id").limit(1).execute()

            return {
                "status": "healthy",
                "table": self._table,
                "timestamp": datetime.utcnow().isoformat(),
                "test_query_success": True,
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "test_query_success": False,
            }


# Alias for backward compatibility
SupabaseExecutionRepository = SupabaseExecutionRepositoryV2

__all__ = ["SupabaseExecutionRepositoryV2", "SupabaseExecutionRepository"]
