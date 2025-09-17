"""
HIL Timeout Manager.

Manages timeouts for Human-in-the-Loop interactions, including timeout detection,
notifications, and automatic workflow resumption based on timeout policies.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from shared.models.human_in_loop import HILStatus, HILTimeoutData

from .workflow_status_manager import WorkflowResumeReason, WorkflowStatusManager


class HILTimeoutManager:
    """Manager for HIL interaction timeouts."""

    def __init__(
        self,
        workflow_status_manager: WorkflowStatusManager,
        database_client=None,
        check_interval_minutes: int = 5,
    ):
        """Initialize HIL timeout manager.

        Args:
            workflow_status_manager: Workflow status manager for resume operations
            database_client: Database client for persistence (TODO: inject actual client)
            check_interval_minutes: How often to check for timeouts
        """
        self.logger = logging.getLogger(__name__)
        self.workflow_status_manager = workflow_status_manager
        # Initialize DB client if not provided
        if database_client is None:
            try:
                from database import Database

                self.db_client = Database().client
            except Exception as e:
                self.db_client = None
                self.logger.warning(f"HILTimeoutManager: No DB client available ({e})")
        else:
            self.db_client = database_client
        self.check_interval_minutes = check_interval_minutes

        # Timeout handlers
        self.timeout_handlers: Dict[str, Callable] = {}

        # Background task for timeout checking
        self._timeout_checker_task: Optional[asyncio.Task] = None
        self._is_running = False

        self.logger.info(
            f"Initialized HIL Timeout Manager "
            f"(check interval: {check_interval_minutes} minutes)"
        )

    def start_timeout_monitoring(self):
        """Start background timeout monitoring."""
        if self._is_running:
            self.logger.warning("Timeout monitoring is already running")
            return

        self._is_running = True
        self._timeout_checker_task = asyncio.create_task(self._timeout_checker_loop())
        self.logger.info("Started HIL timeout monitoring")

    def stop_timeout_monitoring(self):
        """Stop background timeout monitoring."""
        if not self._is_running:
            return

        self._is_running = False
        if self._timeout_checker_task:
            self._timeout_checker_task.cancel()
            self._timeout_checker_task = None

        self.logger.info("Stopped HIL timeout monitoring")

    async def register_interaction_timeout(
        self, interaction_id: str, timeout_at: datetime, timeout_policy: Dict[str, Any]
    ) -> bool:
        """
        Register a HIL interaction for timeout monitoring.

        Args:
            interaction_id: HIL interaction identifier
            timeout_at: When the interaction should timeout
            timeout_policy: Policy for handling timeout (continue/fail/default_response)

        Returns:
            True if registration was successful
        """
        try:
            timeout_record = {
                "interaction_id": interaction_id,
                "timeout_at": timeout_at,
                "timeout_policy": timeout_policy,
                "status": "active",
                "registered_at": datetime.now(),
            }

            # Store timeout record in database or memory
            await self._store_timeout_record(timeout_record)

            self.logger.debug(
                f"Registered timeout for interaction {interaction_id} " f"at {timeout_at}"
            )

            return True

        except Exception as e:
            self.logger.error(
                f"Failed to register timeout for interaction {interaction_id}: {str(e)}"
            )
            return False

    async def cancel_interaction_timeout(self, interaction_id: str) -> bool:
        """
        Cancel timeout monitoring for a HIL interaction.

        Args:
            interaction_id: HIL interaction identifier

        Returns:
            True if cancellation was successful
        """
        try:
            # Update timeout record status to 'cancelled'
            await self._update_timeout_record_status(interaction_id, "cancelled")

            self.logger.debug(f"Cancelled timeout for interaction {interaction_id}")
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to cancel timeout for interaction {interaction_id}: {str(e)}"
            )
            return False

    async def check_interaction_timeouts(self) -> List[Dict[str, Any]]:
        """
        Check for and process expired HIL interactions.

        Returns:
            List of processed timeout records
        """
        try:
            # Get expired interactions
            expired_interactions = await self._get_expired_interactions()
            processed_timeouts = []

            for interaction in expired_interactions:
                try:
                    timeout_result = await self._process_interaction_timeout(interaction)
                    if timeout_result:
                        processed_timeouts.append(timeout_result)

                except Exception as e:
                    self.logger.error(
                        f"Failed to process timeout for interaction {interaction['id']}: {str(e)}"
                    )

            if processed_timeouts:
                self.logger.info(f"Processed {len(processed_timeouts)} interaction timeouts")

            return processed_timeouts

        except Exception as e:
            self.logger.error(f"Failed to check interaction timeouts: {str(e)}")
            return []

    async def get_pending_timeouts(
        self, within_hours: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get list of pending timeouts.

        Args:
            within_hours: Optional filter for timeouts within X hours

        Returns:
            List of pending timeout records
        """
        try:
            filters = {"status": "active"}

            if within_hours:
                filters["timeout_before"] = datetime.now() + timedelta(hours=within_hours)

            # Query timeout records from database
            pending_timeouts = await self._query_timeout_records(filters)

            self.logger.debug(
                f"Found {len(pending_timeouts)} pending timeouts "
                f"({'within ' + str(within_hours) + 'h' if within_hours else 'total'})"
            )

            return pending_timeouts

        except Exception as e:
            self.logger.error(f"Failed to get pending timeouts: {str(e)}")
            return []

    def register_timeout_handler(
        self, interaction_type: str, handler: Callable[[Dict[str, Any]], None]
    ):
        """
        Register custom timeout handler for specific interaction types.

        Args:
            interaction_type: HIL interaction type (approval, input, selection, etc.)
            handler: Callable to handle timeout for this interaction type
        """
        self.timeout_handlers[interaction_type] = handler
        self.logger.debug(f"Registered timeout handler for {interaction_type}")

    async def send_timeout_warning(self, interaction_id: str, minutes_until_timeout: int) -> bool:
        """
        Send timeout warning for HIL interaction.

        Args:
            interaction_id: HIL interaction identifier
            minutes_until_timeout: Minutes remaining before timeout

        Returns:
            True if warning was sent successfully
        """
        try:
            # Get interaction details from database
            interaction = await self._get_interaction(interaction_id)
            if not interaction:
                self.logger.warning(f"Interaction {interaction_id} not found for warning")
                return False

            # Send warning through original channel (placeholder integration point)
            warning_result = await self._send_timeout_warning_message(
                interaction, minutes_until_timeout
            )

            self.logger.info(
                f"Sent timeout warning for interaction {interaction_id} "
                f"({minutes_until_timeout} minutes remaining)"
            )

            return warning_result

        except Exception as e:
            self.logger.error(
                f"Failed to send timeout warning for interaction {interaction_id}: {str(e)}"
            )
            return False

    # Private methods

    async def _timeout_checker_loop(self):
        """Background loop for checking timeouts."""
        self.logger.info(f"Started timeout checker loop (interval: {self.check_interval_minutes}m)")

        while self._is_running:
            try:
                await self.check_interaction_timeouts()

                # Check for warning notifications (5 minutes before timeout)
                await self._check_timeout_warnings()

                # Wait for next check
                await asyncio.sleep(self.check_interval_minutes * 60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in timeout checker loop: {str(e)}")
                await asyncio.sleep(60)  # Wait 1 minute on error

        self.logger.info("Timeout checker loop stopped")

    async def _get_expired_interactions(self) -> List[Dict[str, Any]]:
        """Get HIL interactions that have exceeded their timeout."""
        try:
            current_time = datetime.now().isoformat()
            if not self.db_client:
                # Without DB client, nothing to query
                self.logger.debug("DB client not available for expired interactions query")
                return []
            resp = (
                self.db_client.table("human_interactions")
                .select("*")
                .eq("status", HILStatus.PENDING.value)
                .lte("timeout_at", current_time)
                .execute()
            )
            return resp.data or []
        except Exception as e:
            self.logger.error(f"Failed to query expired interactions: {e}")
            return []

    async def _process_interaction_timeout(
        self, interaction: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Process timeout for a specific HIL interaction."""
        interaction_id = interaction["id"]
        execution_id = interaction.get("execution_id")

        # Get timeout policy from interaction data
        request_data = interaction.get("request_data", {})
        continue_on_timeout = request_data.get("continue_on_timeout", True)
        timeout_default_response = request_data.get("timeout_default_response")

        # Update interaction status to timeout
        await self._update_interaction_status(interaction_id, HILStatus.TIMEOUT)

        # Create timeout data
        timeout_data = HILTimeoutData(
            interaction_id=interaction_id,
            interaction_type=interaction["interaction_type"],
            timeout=True,
            timeout_hours=request_data.get("timeout_hours", 24),
            requested_at=interaction["created_at"],
            timeout_at=interaction["timeout_at"],
            channel_type=interaction["channel_type"],
            original_request=request_data,
            correlation_id=interaction.get("correlation_id"),
        )

        # Handle workflow resume/failure based on policy
        if continue_on_timeout and execution_id:
            # Resume workflow with default response or timeout data
            resume_data = timeout_default_response or timeout_data.dict()

            await self.workflow_status_manager.resume_workflow_execution(
                execution_id, WorkflowResumeReason.TIMEOUT_REACHED, resume_data
            )

            self.logger.info(
                f"Resumed workflow {execution_id} after HIL timeout "
                f"(interaction: {interaction_id})"
            )
        else:
            # Fail the workflow execution
            self.logger.info(f"HIL interaction {interaction_id} timed out - workflow not resumed")

        # Call custom timeout handler if registered
        interaction_type = interaction.get("interaction_type")
        if interaction_type in self.timeout_handlers:
            try:
                await self.timeout_handlers[interaction_type](interaction)
            except Exception as e:
                self.logger.error(f"Custom timeout handler failed: {str(e)}")

        return {
            "interaction_id": interaction_id,
            "execution_id": execution_id,
            "processed_at": datetime.now(),
            "timeout_data": timeout_data.dict(),
            "workflow_resumed": continue_on_timeout and execution_id is not None,
        }

    async def _check_timeout_warnings(self):
        """Check for interactions that need timeout warnings."""
        try:
            # Get interactions that will timeout in the next 15 minutes
            warning_threshold = datetime.now() + timedelta(minutes=15)

            # TODO: Query interactions approaching timeout
            approaching_timeout = await self._get_interactions_approaching_timeout(
                warning_threshold
            )

            for interaction in approaching_timeout:
                minutes_remaining = (
                    interaction["timeout_at"] - datetime.now()
                ).total_seconds() / 60

                if 0 < minutes_remaining <= 15:
                    await self.send_timeout_warning(interaction["id"], int(minutes_remaining))

        except Exception as e:
            self.logger.error(f"Failed to check timeout warnings: {str(e)}")

    async def _get_interactions_approaching_timeout(
        self, threshold: datetime
    ) -> List[Dict[str, Any]]:
        """Get interactions approaching timeout."""
        try:
            if not self.db_client:
                return []
            resp = (
                self.db_client.table("human_interactions")
                .select("*")
                .eq("status", HILStatus.PENDING.value)
                .gt("timeout_at", datetime.now().isoformat())
                .lte("timeout_at", threshold.isoformat())
                .execute()
            )
            return resp.data or []
        except Exception as e:
            self.logger.error(f"Failed to query interactions approaching timeout: {e}")
            return []

    async def _send_timeout_warning_message(
        self, interaction: Dict[str, Any], minutes_remaining: int
    ) -> bool:
        """Send timeout warning message through original channel."""
        try:
            # Integration placeholder: log-only for now
            channel_type = interaction.get("channel_type")
            self.logger.info(
                f"Timeout warning for interaction {interaction.get('id')} via {channel_type}: {minutes_remaining} minutes left"
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to send timeout warning message: {e}")
            return False

    async def _store_timeout_record(self, timeout_record: Dict[str, Any]):
        """Store timeout record for monitoring."""
        try:
            if not self.db_client:
                # Nothing persisted without DB; rely on human_interactions row
                self.logger.debug(
                    f"No DB client - skipping timeout record store for {timeout_record['interaction_id']}"
                )
                return
            # Update the human_interactions row with timeout tracking if exists
            payload = {
                "updated_at": datetime.now().isoformat(),
            }
            # This is a best-effort no-op if record missing
            self.db_client.table("human_interactions").update(payload).eq(
                "id", timeout_record["interaction_id"]
            ).execute()
        except Exception as e:
            self.logger.error(f"Failed to store timeout record: {e}")

    async def _update_timeout_record_status(self, interaction_id: str, status: str):
        """Update timeout record status."""
        try:
            if not self.db_client:
                return
            if status == "cancelled":
                self.db_client.table("human_interactions").update(
                    {"status": HILStatus.CANCELLED.value, "updated_at": datetime.now().isoformat()}
                ).eq("id", interaction_id).execute()
        except Exception as e:
            self.logger.error(f"Failed to update timeout record status: {e}")

    async def _query_timeout_records(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query timeout records with filters."""
        try:
            if not self.db_client:
                return []
            query = self.db_client.table("human_interactions").select("*")
            if filters.get("status"):
                query = query.eq(
                    "status",
                    HILStatus.PENDING.value if filters["status"] == "active" else filters["status"],
                )
            if filters.get("timeout_before"):
                query = query.lte("timeout_at", filters["timeout_before"].isoformat())
            resp = query.order("timeout_at", desc=False).limit(1000).execute()
            return resp.data or []
        except Exception as e:
            self.logger.error(f"Failed to query timeout records: {e}")
            return []

    async def _get_interaction(self, interaction_id: str) -> Optional[Dict[str, Any]]:
        """Get interaction record from database."""
        try:
            if not self.db_client:
                return None
            resp = (
                self.db_client.table("human_interactions")
                .select("*")
                .eq("id", interaction_id)
                .single()
                .execute()
            )
            return resp.data
        except Exception as e:
            self.logger.error(f"Failed to get interaction {interaction_id}: {e}")
            return None

    async def _update_interaction_status(self, interaction_id: str, status: HILStatus):
        """Update interaction status in database."""
        try:
            if not self.db_client:
                return
            payload = {"status": status.value, "updated_at": datetime.now().isoformat()}
            if status == HILStatus.TIMEOUT:
                payload["responded_at"] = datetime.now().isoformat()
            self.db_client.table("human_interactions").update(payload).eq(
                "id", interaction_id
            ).execute()
        except Exception as e:
            self.logger.error(f"Failed to update interaction status: {e}")

    def __del__(self):
        """Cleanup when object is destroyed."""
        if self._is_running:
            self.stop_timeout_monitoring()
