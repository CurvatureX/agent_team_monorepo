"""
Workflow Status Manager for HIL Node System.

Manages workflow execution states, particularly pause and resume functionality
for Human-in-the-Loop interactions.
"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from ..nodes.base import ExecutionStatus


class WorkflowPauseReason(str, Enum):
    """Reasons why a workflow execution might be paused."""

    HUMAN_INTERACTION = "human_interaction"
    TIMEOUT = "timeout"
    ERROR = "error"
    MANUAL = "manual"
    SYSTEM_MAINTENANCE = "system_maintenance"


class WorkflowResumeReason(str, Enum):
    """Reasons why a workflow execution might be resumed."""

    HUMAN_RESPONSE = "human_response"
    TIMEOUT_REACHED = "timeout_reached"
    MANUAL_RESUME = "manual_resume"
    ERROR_RESOLVED = "error_resolved"
    SYSTEM_READY = "system_ready"


class WorkflowStatusManager:
    """Manager for workflow execution status and pause/resume operations."""

    def __init__(self, database_client=None):
        """Initialize workflow status manager.

        Args:
            database_client: Database client for persistence
        """
        self.logger = logging.getLogger(__name__)
        self.db_client = database_client

        # In-memory storage when database not available
        self._pause_records = {}
        self._workflow_statuses = {}

        # Try to initialize database connection if not provided
        if not self.db_client:
            try:
                # Use Workflow Engine Database wrapper to get Supabase client
                from database import Database

                self.db_client = Database().client
                if self.db_client:
                    self.logger.info("Database client initialized for WorkflowStatusManager")
                else:
                    self.logger.warning("Database client unavailable - using in-memory storage")
            except Exception as e:
                self.logger.warning(
                    f"Database not available for WorkflowStatusManager (fallback to memory): {e}"
                )
                self.db_client = None

        self.logger.info("Initialized WorkflowStatusManager")

    async def pause_workflow_execution(
        self,
        execution_id: str,
        node_id: str,
        pause_reason: WorkflowPauseReason,
        resume_conditions: Dict[str, Any],
        timeout_hours: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Pause workflow execution at specific node.

        Args:
            execution_id: Workflow execution identifier
            node_id: Node where execution is paused
            pause_reason: Reason for pausing
            resume_conditions: Conditions required to resume
            timeout_hours: Optional timeout for auto-resume

        Returns:
            Dict with pause record information
        """
        try:
            pause_data = {
                "execution_id": execution_id,
                "paused_at": datetime.now(),
                "paused_node_id": node_id,
                "pause_reason": pause_reason.value,
                "resume_conditions": resume_conditions,
                "status": "active",
                "timeout_at": (
                    datetime.now() + timedelta(hours=timeout_hours) if timeout_hours else None
                ),
            }

            # Persist pause record
            pause_id = await self._create_pause_record(pause_data)
            pause_data["id"] = pause_id

            # Update workflow execution status to PAUSED
            await self._update_workflow_execution_status(execution_id, ExecutionStatus.PAUSED)

            self.logger.info(
                f"Paused workflow execution {execution_id} at node {node_id} "
                f"(reason: {pause_reason.value})"
            )

            return pause_data

        except Exception as e:
            self.logger.error(f"Failed to pause workflow execution {execution_id}: {str(e)}")
            raise

    async def resume_workflow_execution(
        self,
        execution_id: str,
        resume_reason: WorkflowResumeReason,
        resume_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Resume paused workflow execution.

        Args:
            execution_id: Workflow execution identifier
            resume_reason: Reason for resuming
            resume_data: Optional data to pass to resumed execution

        Returns:
            Dict with resume information and next execution details
        """
        try:
            # Get active pause record
            pause_record = await self._get_active_pause_record(execution_id)
            if not pause_record:
                raise ValueError(f"No active pause record found for execution {execution_id}")

            # Validate resume conditions if specified
            if pause_record.get("resume_conditions"):
                self._validate_resume_conditions(
                    pause_record["resume_conditions"], resume_data or {}
                )

            # Update pause record
            resume_info = {
                "resumed_at": datetime.now(),
                "resume_trigger": resume_reason.value,
                "resume_data": resume_data,
                "status": "resumed",
            }

            await self._update_pause_record(pause_record["id"], resume_info)

            # Update workflow execution status back to RUNNING
            await self._update_workflow_execution_status(execution_id, ExecutionStatus.RUNNING)

            # Get next execution step information
            next_step = await self._determine_next_execution_step(pause_record, resume_data)

            self.logger.info(
                f"Resumed workflow execution {execution_id} " f"(reason: {resume_reason.value})"
            )

            return {
                "execution_id": execution_id,
                "resumed_at": resume_info["resumed_at"],
                "resume_reason": resume_reason.value,
                "paused_node_id": pause_record["paused_node_id"],
                "next_step": next_step,
            }

        except Exception as e:
            self.logger.error(f"Failed to resume workflow execution {execution_id}: {str(e)}")
            raise

    async def get_paused_executions(
        self,
        workflow_id: Optional[str] = None,
        pause_reason: Optional[WorkflowPauseReason] = None,
        include_expired: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get list of paused workflow executions.

        Args:
            workflow_id: Optional filter by workflow ID
            pause_reason: Optional filter by pause reason
            include_expired: Whether to include expired pauses

        Returns:
            List of paused execution records
        """
        try:
            filters = {"status": "active"}

            if workflow_id:
                filters["workflow_id"] = workflow_id

            if pause_reason:
                filters["pause_reason"] = pause_reason.value

            if not include_expired:
                filters["not_expired"] = True

            # Query workflow_execution_pauses table
            paused_executions = await self._query_pause_records(filters)

            self.logger.debug(
                f"Found {len(paused_executions)} paused executions "
                f"(workflow_id: {workflow_id}, reason: {pause_reason})"
            )

            return paused_executions

        except Exception as e:
            self.logger.error(f"Failed to get paused executions: {str(e)}")
            return []

    async def check_expired_pauses(self) -> List[Dict[str, Any]]:
        """Check for and handle expired pause records."""
        try:
            expired_pauses = await self._query_expired_pauses()
            processed_pauses: List[Dict[str, Any]] = []

            for pause_record in expired_pauses:
                try:
                    await self._handle_pause_timeout(pause_record)
                    processed_pauses.append(pause_record)
                except Exception as e:
                    self.logger.error(
                        f"Failed to handle timeout for pause {pause_record.get('id')}: {e}"
                    )

            if processed_pauses:
                self.logger.info(f"Processed {len(processed_pauses)} expired pauses")
            return processed_pauses
        except Exception as e:
            self.logger.error(f"Failed to check expired pauses: {e}")
            return []

    async def cancel_paused_execution(
        self, execution_id: str, cancellation_reason: str = "manual_cancellation"
    ) -> bool:
        """Cancel a paused workflow execution."""
        try:
            pause_record = await self._get_active_pause_record(execution_id)
            if not pause_record:
                self.logger.warning(f"No active pause record found for execution {execution_id}")
                return False

            cancellation_info = {
                "cancelled_at": datetime.now(),
                "cancellation_reason": cancellation_reason,
                "status": "cancelled",
            }
            await self._update_pause_record(pause_record["id"], cancellation_info)
            await self._update_workflow_execution_status(execution_id, ExecutionStatus.CANCELLED)
            self.logger.info(
                f"Cancelled paused workflow execution {execution_id} (reason: {cancellation_reason})"
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to cancel paused execution {execution_id}: {e}")
            return False

    def get_pause_status(self, execution_id: str) -> Dict[str, Any]:
        """Get current pause status for workflow execution."""
        try:
            if not self.db_client:
                # Fallback to in-memory
                record = next(
                    (
                        r
                        for r in self._pause_records.values()
                        if r.get("execution_id") == execution_id and r.get("status") == "active"
                    ),
                    None,
                )
            else:
                resp = (
                    self.db_client.table("workflow_execution_pauses")
                    .select("*")
                    .eq("execution_id", execution_id)
                    .eq("status", "active")
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                )
                record = resp.data[0] if resp.data else None

            return {
                "execution_id": execution_id,
                "is_paused": record is not None,
                "pause_reason": record.get("pause_reason") if record else None,
                "paused_at": record.get("paused_at") if record else None,
                "paused_node_id": record.get("paused_node_id") if record else None,
                "timeout_at": record.get("timeout_at") if record else None,
                "resume_conditions": record.get("resume_conditions") if record else None,
            }
        except Exception as e:
            self.logger.error(f"Failed to get pause status for {execution_id}: {e}")
            return {
                "execution_id": execution_id,
                "is_paused": False,
                "pause_reason": None,
                "paused_at": None,
                "paused_node_id": None,
                "timeout_at": None,
                "resume_conditions": None,
            }

    # Private helper methods

    async def _create_pause_record(self, pause_data: Dict[str, Any]) -> str:
        """Create pause record in database or memory. Returns pause ID."""
        if not self.db_client:
            # In-memory fallback
            pause_id = f"pause_{pause_data['execution_id'][:8]}_{int(datetime.now().timestamp())}"
            pause_data_with_id = dict(pause_data)
            pause_data_with_id["id"] = pause_id
            self._pause_records[pause_id] = pause_data_with_id
            self.logger.debug(f"[MEM] pause created: {pause_id}")
            return pause_id

        # Persist to Supabase
        payload = {
            "execution_id": pause_data["execution_id"],
            "paused_at": pause_data["paused_at"].isoformat()
            if isinstance(pause_data["paused_at"], datetime)
            else pause_data["paused_at"],
            "paused_node_id": pause_data["paused_node_id"],
            "pause_reason": pause_data["pause_reason"],
            "resume_conditions": pause_data.get("resume_conditions", {}),
            "status": pause_data.get("status", "active"),
            "timeout_at": (
                pause_data["timeout_at"].isoformat()
                if isinstance(pause_data.get("timeout_at"), datetime)
                else pause_data.get("timeout_at")
            ),
        }
        resp = self.db_client.table("workflow_execution_pauses").insert(payload).execute()
        if not resp.data:
            raise RuntimeError("Failed to create pause record")
        return resp.data[0]["id"]

    async def _get_active_pause_record(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get active pause record for execution."""
        if not self.db_client:
            return next(
                (
                    r
                    for r in self._pause_records.values()
                    if r.get("execution_id") == execution_id and r.get("status") == "active"
                ),
                None,
            )
        resp = (
            self.db_client.table("workflow_execution_pauses")
            .select("*")
            .eq("execution_id", execution_id)
            .eq("status", "active")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None

    async def _update_pause_record(self, pause_id: str, update_data: Dict[str, Any]):
        """Update pause record in database or memory."""
        if not self.db_client:
            if pause_id in self._pause_records:
                self._pause_records[pause_id].update(update_data)
            self.logger.debug(f"[MEM] pause updated: {pause_id}")
            return
        # Convert datetimes
        payload = {
            k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in update_data.items()
        }
        self.db_client.table("workflow_execution_pauses").update(payload).eq(
            "id", pause_id
        ).execute()

    async def _update_workflow_execution_status(self, execution_id: str, status: ExecutionStatus):
        """Update workflow execution status in database if available."""
        if not self.db_client:
            # Memory fallback
            self._workflow_statuses[execution_id] = status.value
            self.logger.debug(f"[MEM] workflow status: {execution_id} -> {status.value}")
            return
        payload = {"status": status.value, "updated_at": datetime.now().isoformat()}
        self.db_client.table("workflow_executions").update(payload).eq(
            "execution_id", execution_id
        ).execute()

    async def _query_pause_records(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query pause records with filters."""
        if not self.db_client:
            # Simple in-memory filter
            results = [
                r
                for r in self._pause_records.values()
                if r.get("status") == filters.get("status", "active")
            ]
            if filters.get("workflow_id"):
                # Requires mapping; not stored in memory fallback
                results = results
            if filters.get("pause_reason"):
                results = [r for r in results if r.get("pause_reason") == filters["pause_reason"]]
            if filters.get("not_expired"):
                now = datetime.now()
                results = [
                    r
                    for r in results
                    if (r.get("timeout_at") is None)
                    or (r.get("timeout_at") and r["timeout_at"] > now)
                ]
            return results

        query = self.db_client.table("workflow_execution_pauses").select("*")
        if "status" in filters:
            query = query.eq("status", filters["status"])
        if "workflow_id" in filters:
            query = query.eq("workflow_id", filters["workflow_id"])
        if "pause_reason" in filters:
            query = query.eq("pause_reason", filters["pause_reason"])
        if filters.get("not_expired"):
            now_iso = datetime.now().isoformat()
            # not expired means timeout_at is null or in the future
            query = query.or_(f"timeout_at.is.null,timeout_at.gt.{now_iso}")
        resp = query.order("created_at", desc=True).limit(1000).execute()
        return resp.data or []

    async def _query_expired_pauses(self) -> List[Dict[str, Any]]:
        """Query expired pause records."""
        if not self.db_client:
            now = datetime.now()
            return [
                r
                for r in self._pause_records.values()
                if r.get("status") == "active" and r.get("timeout_at") and r["timeout_at"] <= now
            ]
        now_iso = datetime.now().isoformat()
        resp = (
            self.db_client.table("workflow_execution_pauses")
            .select("*")
            .eq("status", "active")
            .lte("timeout_at", now_iso)
            .execute()
        )
        return resp.data or []

    def _validate_resume_conditions(
        self, required_conditions: Dict[str, Any], provided_data: Dict[str, Any]
    ):
        """Validate that resume conditions are met."""
        for key, required_value in required_conditions.items():
            if key not in provided_data:
                raise ValueError(f"Missing required resume condition: {key}")
            if required_value is not None and provided_data[key] != required_value:
                raise ValueError(f"Resume condition not met: {key}")
        self.logger.debug("Resume conditions validated successfully")

    async def _determine_next_execution_step(
        self, pause_record: Dict[str, Any], resume_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Determine next step in workflow execution after resume.
        Simple implementation continues from paused node with provided resume data.
        """
        paused_at = pause_record.get("paused_at")
        if isinstance(paused_at, str):
            try:
                from datetime import datetime as _dt

                paused_at_dt = _dt.fromisoformat(paused_at.replace("Z", "+00:00"))
            except Exception:
                paused_at_dt = datetime.now()
        else:
            paused_at_dt = paused_at or datetime.now()

        return {
            "node_id": pause_record["paused_node_id"],
            "action": "continue",
            "resume_data": resume_data,
            "execution_context": {
                "resumed_from_pause": True,
                "pause_duration_seconds": (datetime.now() - paused_at_dt).total_seconds(),
            },
        }

    async def _handle_pause_timeout(self, pause_record: Dict[str, Any]):
        """Handle timeout for a paused workflow execution."""
        execution_id = pause_record["execution_id"]
        resume_conditions = pause_record.get("resume_conditions", {})
        timeout_action = resume_conditions.get("timeout_action", "fail")

        if timeout_action == "resume":
            default_data = resume_conditions.get("timeout_default_data", {})
            await self.resume_workflow_execution(
                execution_id, WorkflowResumeReason.TIMEOUT_REACHED, default_data
            )
        elif timeout_action == "cancel":
            await self.cancel_paused_execution(execution_id, "timeout_cancellation")
        else:
            await self._update_workflow_execution_status(execution_id, ExecutionStatus.ERROR)
            await self._update_pause_record(
                pause_record["id"],
                {
                    "timeout_at": datetime.now().isoformat(),
                    "timeout_action": "failed",
                    "status": "timeout",
                },
            )
        self.logger.info(
            f"Handled timeout for paused execution {execution_id} (action: {timeout_action})"
        )
