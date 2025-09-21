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
                # Attempt to get database connection from workflow engine
                from ..core.database import get_db_session

                self.get_db_session = get_db_session
                self.logger.info("Database session factory available")
            except ImportError:
                self.logger.warning("Database not available - using in-memory storage")
                self.get_db_session = None

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

            # TODO: Insert into workflow_execution_pauses table
            pause_id = await self._create_pause_record(pause_data)
            pause_data["id"] = pause_id

            # TODO: Update workflow execution status to PAUSED
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

            # TODO: Update workflow execution status back to RUNNING
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

            # TODO: Query workflow_execution_pauses table
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
        """
        Check for and handle expired pause records.

        Returns:
            List of expired pause records that were processed
        """
        try:
            # TODO: Query for expired pauses
            expired_pauses = await self._query_expired_pauses()
            processed_pauses = []

            for pause_record in expired_pauses:
                try:
                    # Handle timeout based on resume conditions
                    await self._handle_pause_timeout(pause_record)
                    processed_pauses.append(pause_record)

                except Exception as e:
                    self.logger.error(
                        f"Failed to handle timeout for pause {pause_record['id']}: {str(e)}"
                    )

            if processed_pauses:
                self.logger.info(f"Processed {len(processed_pauses)} expired pauses")

            return processed_pauses

        except Exception as e:
            self.logger.error(f"Failed to check expired pauses: {str(e)}")
            return []

    async def cancel_paused_execution(
        self, execution_id: str, cancellation_reason: str = "manual_cancellation"
    ) -> bool:
        """
        Cancel a paused workflow execution.

        Args:
            execution_id: Workflow execution identifier
            cancellation_reason: Reason for cancellation

        Returns:
            True if cancellation was successful
        """
        try:
            # Get active pause record
            pause_record = await self._get_active_pause_record(execution_id)
            if not pause_record:
                self.logger.warning(f"No active pause record found for execution {execution_id}")
                return False

            # Update pause record to cancelled
            cancellation_info = {
                "cancelled_at": datetime.now(),
                "cancellation_reason": cancellation_reason,
                "status": "cancelled",
            }

            await self._update_pause_record(pause_record["id"], cancellation_info)

            # TODO: Update workflow execution status to CANCELLED
            await self._update_workflow_execution_status(execution_id, ExecutionStatus.CANCELLED)

            self.logger.info(
                f"Cancelled paused workflow execution {execution_id} "
                f"(reason: {cancellation_reason})"
            )

            return True

        except Exception as e:
            self.logger.error(f"Failed to cancel paused execution {execution_id}: {str(e)}")
            return False

    def get_pause_status(self, execution_id: str) -> Dict[str, Any]:
        """
        Get current pause status for workflow execution.

        Args:
            execution_id: Workflow execution identifier

        Returns:
            Dict with pause status information
        """
        # TODO: Query current pause status from database
        # For now, return mock status
        return {
            "execution_id": execution_id,
            "is_paused": False,  # TODO: Get actual status
            "pause_reason": None,
            "paused_at": None,
            "paused_node_id": None,
            "timeout_at": None,
            "resume_conditions": None,
        }

    # Private helper methods

    async def _create_pause_record(self, pause_data: Dict[str, Any]) -> str:
        """Create pause record in database."""
        # TODO: Insert into workflow_execution_pauses table
        # For now, return mock ID
        pause_id = f"pause_{pause_data['execution_id'][:8]}_{int(datetime.now().timestamp())}"
        self.logger.debug(f"Mock pause record created: {pause_id}")
        return pause_id

    async def _get_active_pause_record(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get active pause record for execution."""
        # TODO: Query workflow_execution_pauses table
        # For now, return None (no active pause)
        self.logger.debug(f"Mock query for active pause record: {execution_id}")
        return None

    async def _update_pause_record(self, pause_id: str, update_data: Dict[str, Any]):
        """Update pause record in database."""
        # TODO: Update workflow_execution_pauses table
        self.logger.debug(f"Mock pause record update: {pause_id}")

    async def _update_workflow_execution_status(self, execution_id: str, status: ExecutionStatus):
        """Update workflow execution status."""
        # TODO: Update workflow_executions table
        self.logger.debug(f"Mock workflow status update: {execution_id} -> {status.value}")

    async def _query_pause_records(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query pause records with filters."""
        # TODO: Query workflow_execution_pauses table
        self.logger.debug(f"Mock pause records query with filters: {filters}")
        return []

    async def _query_expired_pauses(self) -> List[Dict[str, Any]]:
        """Query expired pause records."""
        # TODO: Query workflow_execution_pauses table for expired pauses
        self.logger.debug("Mock expired pauses query")
        return []

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
        """Determine next step in workflow execution after resume."""
        # TODO: Implement logic to determine next execution step
        # This might involve checking the paused node, resume data, and workflow definition

        return {
            "node_id": pause_record["paused_node_id"],
            "action": "continue",
            "resume_data": resume_data,
            "execution_context": {
                "resumed_from_pause": True,
                "pause_duration_seconds": (
                    datetime.now() - pause_record["paused_at"]
                ).total_seconds(),
            },
        }

    async def _handle_pause_timeout(self, pause_record: Dict[str, Any]):
        """Handle timeout for a paused workflow execution."""
        execution_id = pause_record["execution_id"]

        # Check if timeout handling is configured in resume conditions
        resume_conditions = pause_record.get("resume_conditions", {})
        timeout_action = resume_conditions.get("timeout_action", "fail")

        if timeout_action == "resume":
            # Resume with default data
            default_data = resume_conditions.get("timeout_default_data", {})
            await self.resume_workflow_execution(
                execution_id, WorkflowResumeReason.TIMEOUT_REACHED, default_data
            )
        elif timeout_action == "cancel":
            # Cancel the execution
            await self.cancel_paused_execution(execution_id, "timeout_cancellation")
        else:
            # Default: fail the execution
            await self._update_workflow_execution_status(execution_id, ExecutionStatus.ERROR)
            await self._update_pause_record(
                pause_record["id"],
                {"timeout_at": datetime.now(), "timeout_action": "failed", "status": "timeout"},
            )

        self.logger.info(
            f"Handled timeout for paused execution {execution_id} " f"(action: {timeout_action})"
        )
