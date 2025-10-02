"""HIL Timeout Management Service for workflow_engine_v2.

Provides background monitoring and automatic timeout processing for HIL interactions,
including warning notifications and workflow resume management.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Use absolute imports
from shared.models import ExecutionStatus

from .hil_service import HILWorkflowServiceV2

logger = logging.getLogger(__name__)


class HILTimeoutManager:
    """Background service for monitoring and processing HIL interaction timeouts."""

    def __init__(
        self,
        check_interval_minutes: int = 1,
        warning_threshold_minutes: int = 15,
        enable_background_monitoring: bool = True,
    ):
        """
        Initialize HIL timeout manager.

        Args:
            check_interval_minutes: How often to check for timeouts (default: 1 minute)
            warning_threshold_minutes: Send warning N minutes before timeout (default: 15 minutes)
            enable_background_monitoring: Whether to start background monitoring loop
        """
        self.check_interval_minutes = check_interval_minutes
        self.warning_threshold_minutes = warning_threshold_minutes
        self.enable_background_monitoring = enable_background_monitoring

        # Initialize services
        self.hil_service = HILWorkflowServiceV2()

        # Initialize Supabase client
        self._init_database_connection()

        # Background monitoring state
        self._monitoring_task: Optional[asyncio.Task] = None
        self._is_running = False

        logger.info(f"HIL Timeout Manager initialized with {check_interval_minutes}min intervals")

    def _init_database_connection(self) -> None:
        """Initialize Supabase database connection."""
        try:
            from supabase import Client, create_client

            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

            if supabase_url and supabase_key:
                self._supabase: Client = create_client(supabase_url, supabase_key)
                logger.info("HIL Timeout Manager: Connected to Supabase database")
            else:
                self._supabase = None
                logger.warning(
                    "HIL Timeout Manager: No database connection - timeout processing disabled"
                )

        except Exception as e:
            self._supabase = None
            logger.error(f"HIL Timeout Manager: Failed to connect to database: {str(e)}")

    async def start_monitoring(self) -> None:
        """Start background timeout monitoring if enabled."""
        if not self.enable_background_monitoring or not self._supabase:
            return

        if self._is_running:
            logger.warning("HIL timeout monitoring already running")
            return

        self._is_running = True
        self._monitoring_task = asyncio.create_task(self._timeout_monitoring_loop())
        logger.info("HIL timeout background monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop background timeout monitoring."""
        self._is_running = False

        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        logger.info("HIL timeout background monitoring stopped")

    async def _timeout_monitoring_loop(self) -> None:
        """Main background monitoring loop."""
        while self._is_running:
            try:
                # Check for expired interactions
                await self.process_expired_interactions()

                # Send timeout warnings
                await self.send_timeout_warnings()

                # Wait for next check interval
                await asyncio.sleep(self.check_interval_minutes * 60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in HIL timeout monitoring loop: {str(e)}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def process_expired_interactions(self) -> List[str]:
        """
        Find and process expired HIL interactions.

        Returns:
            List of interaction IDs that were processed
        """
        if not self._supabase:
            return []

        try:
            # Get expired interactions from database
            expired_interactions = await self._get_expired_interactions()

            processed_ids = []
            for interaction in expired_interactions:
                try:
                    # Process timeout for this interaction
                    success = await self._process_interaction_timeout(interaction)
                    if success:
                        processed_ids.append(interaction["id"])
                        logger.info(f"Processed timeout for HIL interaction {interaction['id']}")

                except Exception as e:
                    logger.error(
                        f"Failed to process timeout for interaction {interaction.get('id')}: {str(e)}"
                    )

            if processed_ids:
                logger.info(f"Processed {len(processed_ids)} expired HIL interactions")

            return processed_ids

        except Exception as e:
            logger.error(f"Failed to process expired HIL interactions: {str(e)}")
            return []

    async def send_timeout_warnings(self) -> List[str]:
        """
        Send warning notifications for interactions approaching timeout.

        Returns:
            List of interaction IDs that received warnings
        """
        if not self._supabase:
            return []

        try:
            # Get interactions approaching timeout
            warning_interactions = await self._get_warning_interactions()

            warned_ids = []
            for interaction in warning_interactions:
                try:
                    # Send warning notification
                    success = await self._send_timeout_warning(interaction)
                    if success:
                        warned_ids.append(interaction["id"])
                        logger.info(f"Sent timeout warning for HIL interaction {interaction['id']}")

                except Exception as e:
                    logger.error(
                        f"Failed to send warning for interaction {interaction.get('id')}: {str(e)}"
                    )

            if warned_ids:
                logger.info(f"Sent timeout warnings for {len(warned_ids)} HIL interactions")

            return warned_ids

        except Exception as e:
            logger.error(f"Failed to send timeout warnings: {str(e)}")
            return []

    async def _get_expired_interactions(self) -> List[Dict[str, Any]]:
        """Get HIL interactions that have exceeded their timeout."""
        try:
            current_time = datetime.utcnow()

            result = (
                self._supabase.table("hil_interactions")
                .select("*")
                .eq("status", "pending")
                .lte("timeout_at", current_time.isoformat())
                .execute()
            )

            return result.data or []

        except Exception as e:
            logger.error(f"Failed to query expired interactions: {str(e)}")
            return []

    async def _get_warning_interactions(self) -> List[Dict[str, Any]]:
        """Get HIL interactions approaching timeout that haven't been warned."""
        try:
            current_time = datetime.utcnow()
            warning_time = current_time + timedelta(minutes=self.warning_threshold_minutes)

            result = (
                self._supabase.table("hil_interactions")
                .select("*")
                .eq("status", "pending")
                .eq("warning_sent", False)
                .lte("timeout_at", warning_time.isoformat())
                .gte("timeout_at", current_time.isoformat())
                .execute()
            )

            return result.data or []

        except Exception as e:
            logger.error(f"Failed to query warning interactions: {str(e)}")
            return []

    async def _process_interaction_timeout(self, interaction: Dict[str, Any]) -> bool:
        """Process timeout for a specific HIL interaction."""
        try:
            interaction_id = interaction["id"]
            timeout_action = interaction.get("request_data", {}).get("timeout_action", "fail")

            # Update interaction status to timeout
            self._supabase.table("hil_interactions").update(
                {
                    "status": "timeout",
                    "updated_at": datetime.utcnow().isoformat(),
                    "response_data": {
                        "timeout": True,
                        "timeout_action": timeout_action,
                        "timeout_at": datetime.utcnow().isoformat(),
                    },
                }
            ).eq("id", interaction_id).execute()

            # Send timeout notification
            await self._send_timeout_notification(interaction)

            # Resume workflow based on timeout action
            await self._resume_workflow_after_timeout(interaction, timeout_action)

            return True

        except Exception as e:
            logger.error(f"Failed to process interaction timeout: {str(e)}")
            return False

    async def _send_timeout_warning(self, interaction: Dict[str, Any]) -> bool:
        """Send timeout warning notification for an interaction."""
        try:
            interaction_id = interaction["id"]

            # Mark warning as sent
            self._supabase.table("hil_interactions").update(
                {"warning_sent": True, "updated_at": datetime.utcnow().isoformat()}
            ).eq("id", interaction_id).execute()

            # Send warning via HIL service
            channel_type = interaction.get("channel_type", "slack")
            timeout_at = datetime.fromisoformat(interaction["timeout_at"].replace("Z", "+00:00"))
            minutes_remaining = max(0, int((timeout_at - datetime.utcnow()).total_seconds() / 60))

            warning_data = {
                "interaction_id": interaction_id,
                "workflow_name": interaction.get("request_data", {})
                .get("workflow_context", {})
                .get("workflow_name", "Workflow"),
                "minutes_remaining": minutes_remaining,
                "timeout_at": timeout_at.isoformat(),
            }

            # Use HIL service to send warning message
            await self.hil_service._send_response_message(
                interaction_id=interaction_id,
                message_type="warning",
                channel_type=channel_type,
                template_variables=warning_data,
                workflow_context=interaction.get("request_data", {}),
            )

            return True

        except Exception as e:
            logger.error(f"Failed to send timeout warning: {str(e)}")
            return False

    async def _send_timeout_notification(self, interaction: Dict[str, Any]) -> bool:
        """Send timeout notification for an interaction."""
        try:
            interaction_id = interaction["id"]
            channel_type = interaction.get("channel_type", "slack")
            timeout_action = interaction.get("request_data", {}).get("timeout_action", "fail")

            timeout_data = {
                "interaction_id": interaction_id,
                "workflow_name": interaction.get("request_data", {})
                .get("workflow_context", {})
                .get("workflow_name", "Workflow"),
                "timeout_action_description": self._get_timeout_action_description(timeout_action),
            }

            # Use HIL service to send timeout message
            await self.hil_service._send_response_message(
                interaction_id=interaction_id,
                message_type="timeout",
                channel_type=channel_type,
                template_variables=timeout_data,
                workflow_context=interaction.get("request_data", {}),
            )

            return True

        except Exception as e:
            logger.error(f"Failed to send timeout notification: {str(e)}")
            return False

    async def _resume_workflow_after_timeout(
        self, interaction: Dict[str, Any], timeout_action: str
    ) -> bool:
        """Resume workflow execution after HIL timeout based on timeout action."""
        try:
            execution_id = interaction.get("execution_id")
            node_id = interaction.get("node_id")

            if not execution_id or not node_id:
                logger.error(f"Missing execution_id or node_id for timeout resume")
                return False

            # Update workflow pause record
            self._supabase.table("workflow_execution_pauses").update(
                {
                    "status": "resumed",
                    "resume_reason": "timeout_reached",
                    "resume_data": {
                        "timeout_action": timeout_action,
                        "timeout_at": datetime.utcnow().isoformat(),
                    },
                    "resumed_at": datetime.utcnow().isoformat(),
                }
            ).eq("execution_id", execution_id).eq("node_id", node_id).eq(
                "status", "active"
            ).execute()

            # Resume workflow execution through engine
            # TODO: Integrate with ExecutionEngine resume mechanism
            logger.info(
                f"Workflow {execution_id} resumed after HIL timeout with action: {timeout_action}"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to resume workflow after timeout: {str(e)}")
            return False

    def _get_timeout_action_description(self, timeout_action: str) -> str:
        """Get human-readable description of timeout action."""
        descriptions = {
            "fail": "Workflow execution will be stopped due to timeout",
            "continue": "Workflow execution will continue with default response",
            "default_response": "Workflow execution will continue with configured default response",
        }
        return descriptions.get(
            timeout_action, f"Workflow will proceed with action: {timeout_action}"
        )

    async def manual_timeout_check(self) -> Dict[str, int]:
        """Manually trigger timeout check (useful for testing or on-demand processing)."""
        logger.info("Manual HIL timeout check triggered")

        expired_count = len(await self.process_expired_interactions())
        warned_count = len(await self.send_timeout_warnings())

        result = {
            "expired_interactions_processed": expired_count,
            "timeout_warnings_sent": warned_count,
        }

        logger.info(f"Manual timeout check completed: {result}")
        return result


# Global timeout manager instance
_timeout_manager: Optional[HILTimeoutManager] = None


def get_hil_timeout_manager() -> HILTimeoutManager:
    """Get or create the global HIL timeout manager instance."""
    global _timeout_manager
    if _timeout_manager is None:
        _timeout_manager = HILTimeoutManager()
    return _timeout_manager


async def start_hil_timeout_monitoring() -> None:
    """Start the global HIL timeout monitoring service."""
    manager = get_hil_timeout_manager()
    await manager.start_monitoring()


async def stop_hil_timeout_monitoring() -> None:
    """Stop the global HIL timeout monitoring service."""
    global _timeout_manager
    if _timeout_manager:
        await _timeout_manager.stop_monitoring()
        _timeout_manager = None


__all__ = [
    "HILTimeoutManager",
    "get_hil_timeout_manager",
    "start_hil_timeout_monitoring",
    "stop_hil_timeout_monitoring",
]
