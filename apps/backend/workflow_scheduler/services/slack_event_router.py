"""
Slack Event Router

This module provides a global event routing system for Slack events,
managing multiple Slack triggers and routing events to matching workflows.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from shared.models.workflow_new import WorkflowExecutionResponse

logger = logging.getLogger(__name__)


class SlackEventRouter:
    """
    Global Slack event router for managing and routing Slack events
    to registered triggers across all workflows.
    """

    _instance: Optional["SlackEventRouter"] = None
    _lock = asyncio.Lock()

    def __init__(self):
        # Workspace-specific triggers: {workspace_id: [triggers]}
        self.workspace_triggers: Dict[str, List] = {}
        # Global triggers (listen to all workspaces): [triggers]
        self.global_triggers: List = []

        logger.info("🔧 SlackEventRouter initialized")

    @classmethod
    async def get_instance(cls) -> "SlackEventRouter":
        """
        Get or create the singleton SlackEventRouter instance

        Returns:
            SlackEventRouter: The singleton instance
        """
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    async def register_trigger(self, trigger, workspace_id: str = None):
        """
        Register a Slack trigger with the router

        Args:
            trigger: SlackTrigger instance
            workspace_id: Workspace ID to register for, or None for global
        """
        try:
            if workspace_id:
                if workspace_id not in self.workspace_triggers:
                    self.workspace_triggers[workspace_id] = []
                self.workspace_triggers[workspace_id].append(trigger)
                logger.info(
                    f"📝 Registered SlackTrigger for workflow {trigger.workflow_id} in workspace {workspace_id}"
                )
            else:
                self.global_triggers.append(trigger)
                logger.info(f"📝 Registered global SlackTrigger for workflow {trigger.workflow_id}")

        except Exception as e:
            logger.error(f"❌ Failed to register SlackTrigger: {e}", exc_info=True)
            raise

    async def unregister_trigger(self, trigger, workspace_id: str = None):
        """
        Unregister a Slack trigger from the router

        Args:
            trigger: SlackTrigger instance
            workspace_id: Workspace ID to unregister from, or None for global
        """
        try:
            if workspace_id:
                if workspace_id in self.workspace_triggers:
                    if trigger in self.workspace_triggers[workspace_id]:
                        self.workspace_triggers[workspace_id].remove(trigger)
                        logger.info(
                            f"🗑️ Unregistered SlackTrigger for workflow {trigger.workflow_id} from workspace {workspace_id}"
                        )

                    # Clean up empty workspace entries
                    if not self.workspace_triggers[workspace_id]:
                        del self.workspace_triggers[workspace_id]
            else:
                if trigger in self.global_triggers:
                    self.global_triggers.remove(trigger)
                    logger.info(
                        f"🗑️ Unregistered global SlackTrigger for workflow {trigger.workflow_id}"
                    )

        except Exception as e:
            logger.error(f"❌ Failed to unregister SlackTrigger: {e}", exc_info=True)

    async def route_event(self, event_data: dict) -> List[WorkflowExecutionResponse]:
        """
        Route a Slack event to all matching triggers

        Args:
            event_data: The Slack event data

        Returns:
            List[WorkflowExecutionResponse]: Results from all triggered workflows
        """
        workspace_id = event_data.get("team_id", "")
        event_type = event_data.get("type", "")

        logger.info(f"🎯 Routing Slack event: {event_type} from workspace {workspace_id}")

        results = []
        processed_count = 0

        try:
            # Process workspace-specific triggers
            if workspace_id in self.workspace_triggers:
                workspace_results = await self._process_triggers(
                    self.workspace_triggers[workspace_id],
                    event_data,
                    f"workspace {workspace_id}",
                )
                results.extend(workspace_results)
                processed_count += len(workspace_results)

            # Process global triggers
            if self.global_triggers:
                global_results = await self._process_triggers(
                    self.global_triggers, event_data, "global"
                )
                results.extend(global_results)
                processed_count += len(global_results)

            logger.info(f"✅ Slack event routing completed: {processed_count} workflows triggered")

        except Exception as e:
            logger.error(f"❌ Error routing Slack event: {e}", exc_info=True)
            # Create error result with required fields
            error_result = WorkflowExecutionResponse(
                execution_id="",
                workflow_id="",
                status="router_error",
                message=f"Slack event routing failed: {str(e)}",
            )
            results.append(error_result)

        return results

    async def _process_triggers(
        self, triggers: List, event_data: dict, trigger_scope: str
    ) -> List[WorkflowExecutionResponse]:
        """
        Process a list of triggers for the given event

        Args:
            triggers: List of SlackTrigger instances
            event_data: The Slack event data
            trigger_scope: Description of trigger scope (for logging)

        Returns:
            List[WorkflowExecutionResponse]: Results from triggered workflows
        """
        results = []

        for trigger in triggers:
            try:
                # Check if the trigger matches the event
                if await trigger.process_slack_event(event_data):
                    logger.info(f"🔥 Triggering workflow {trigger.workflow_id} from {trigger_scope}")

                    # Trigger the workflow
                    result = await trigger.trigger_from_slack_event(event_data)
                    results.append(result)

                    logger.info(f"✅ Workflow {trigger.workflow_id} triggered: {result.status}")
                else:
                    logger.debug(
                        f"⚫ Event doesn't match trigger for workflow {trigger.workflow_id}"
                    )

            except Exception as e:
                logger.error(
                    f"❌ Error processing trigger for workflow {trigger.workflow_id}: {e}",
                    exc_info=True,
                )

                # Create error result for this specific trigger with required fields
                error_result = WorkflowExecutionResponse(
                    execution_id=f"exec_{trigger.workflow_id}",
                    workflow_id=str(trigger.workflow_id),
                    status="trigger_error",
                    message=f"Trigger processing failed: {str(e)}",
                )
                results.append(error_result)

        return results

    async def get_router_stats(self) -> Dict[str, Any]:
        """
        Get statistics about registered triggers

        Returns:
            Dict with router statistics
        """
        stats = {
            "total_workspaces": len(self.workspace_triggers),
            "global_triggers": len(self.global_triggers),
            "workspace_triggers": {},
            "total_triggers": len(self.global_triggers),
        }

        for workspace_id, triggers in self.workspace_triggers.items():
            stats["workspace_triggers"][workspace_id] = len(triggers)
            stats["total_triggers"] += len(triggers)

        return stats

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check for the router

        Returns:
            Dict with health status
        """
        try:
            stats = await self.get_router_stats()

            return {
                "service": "slack_event_router",
                "status": "healthy",
                "statistics": stats,
            }

        except Exception as e:
            logger.error(f"SlackEventRouter health check failed: {e}")
            return {
                "service": "slack_event_router",
                "status": "unhealthy",
                "error": str(e),
            }
