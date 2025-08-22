"""
Slack Trigger Implementation

This module implements the Slack trigger for workflow_scheduler,
supporting various Slack events like messages, mentions, reactions, etc.
"""

import logging
import re
from typing import Any, Dict, List, Optional

from shared.models.node_enums import TriggerSubtype
from shared.models.trigger import ExecutionResult, TriggerStatus
from workflow_scheduler.triggers.base import BaseTrigger

logger = logging.getLogger(__name__)


class SlackTrigger(BaseTrigger):
    """
    Slack event trigger implementation

    Supports various Slack events:
    - message.channels, message.groups, message.im
    - app_mention
    - reaction_added, pin_added
    - file_shared
    """

    @property
    def trigger_type(self) -> str:
        return TriggerSubtype.SLACK.value

    def __init__(self, workflow_id: str, trigger_config: dict):
        super().__init__(workflow_id, trigger_config)

        # Slack-specific configuration
        self.workspace_id = trigger_config.get("workspace_id")
        self.channel_filter = trigger_config.get("channel_filter")
        self.event_types = trigger_config.get("event_types", ["message", "app_mention"])
        self.mention_required = trigger_config.get("mention_required", False)
        self.command_prefix = trigger_config.get("command_prefix", "!")
        self.user_filter = trigger_config.get("user_filter")
        self.ignore_bots = trigger_config.get("ignore_bots", True)
        self.require_thread = trigger_config.get("require_thread", False)

        logger.info(f"Initialized SlackTrigger for workflow {workflow_id}")
        logger.info(f"  Workspace: {self.workspace_id}")
        logger.info(f"  Events: {self.event_types}")
        logger.info(f"  Channel filter: {self.channel_filter}")

    async def start(self) -> bool:
        """
        Start the Slack trigger

        For Slack triggers, we don't actively start listening here.
        Instead, we register with the global SlackEventRouter.
        """
        try:
            if not self.enabled:
                logger.info(f"SlackTrigger for workflow {self.workflow_id} is disabled")
                return True

            # Import here to avoid circular imports
            from workflow_scheduler.services.slack_event_router import SlackEventRouter

            # Get the global Slack event router instance
            slack_router = await SlackEventRouter.get_instance()

            # Register this trigger with the router
            await slack_router.register_trigger(workspace_id=self.workspace_id, trigger=self)

            self.status = TriggerStatus.ACTIVE
            logger.info(f"✅ SlackTrigger started for workflow {self.workflow_id}")
            return True

        except Exception as e:
            logger.error(
                f"❌ Failed to start SlackTrigger for workflow {self.workflow_id}: {e}",
                exc_info=True,
            )
            self.status = TriggerStatus.ERROR
            return False

    async def stop(self) -> bool:
        """
        Stop the Slack trigger
        """
        try:
            # Import here to avoid circular imports
            from workflow_scheduler.services.slack_event_router import SlackEventRouter

            # Get the global Slack event router instance
            slack_router = await SlackEventRouter.get_instance()

            # Unregister this trigger from the router
            await slack_router.unregister_trigger(workspace_id=self.workspace_id, trigger=self)

            self.status = TriggerStatus.STOPPED
            logger.info(f"🛑 SlackTrigger stopped for workflow {self.workflow_id}")
            return True

        except Exception as e:
            logger.error(
                f"❌ Failed to stop SlackTrigger for workflow {self.workflow_id}: {e}", exc_info=True
            )
            return False

    async def process_slack_event(self, event_data: dict) -> bool:
        """
        Process a Slack event and determine if it matches this trigger's filters

        Args:
            event_data: The Slack event data

        Returns:
            bool: True if the event matches and should trigger the workflow
        """
        try:
            logger.info(f"🔍 Processing Slack event for workflow {self.workflow_id}")

            # For Slack events, the actual event is nested under 'event' key
            actual_event = event_data.get("event", {})
            event_type = actual_event.get("type", "")

            logger.info(f"🏷️  Event type extracted: '{event_type}' (from nested event)")
            logger.info(f"🎯 Expected event types: {self.event_types}")

            # Event type filter
            if event_type not in self.event_types:
                logger.info(f"❌ Event type '{event_type}' not in expected types {self.event_types}")
                return False

            logger.info(f"✅ Event type '{event_type}' matches expected types")

            # Channel filter - extract from the nested event
            channel_id = actual_event.get("channel", "")
            if not self._matches_channel_filter(channel_id):
                logger.debug(f"Channel {channel_id} doesn't match filter {self.channel_filter}")
                return False

            # User filter - extract from the nested event
            user_id = actual_event.get("user", "")
            if not self._matches_user_filter(user_id):
                logger.debug(f"User {user_id} doesn't match filter {self.user_filter}")
                return False

            # Bot filter - extract from the nested event
            bot_id = actual_event.get("bot_id")
            if self.ignore_bots and bot_id:
                logger.info(f"🤖 Ignoring bot message from bot_id: {bot_id}")
                return False

            # Mention filter - pass the nested event
            if self.mention_required and not self._has_bot_mention(actual_event):
                logger.debug("Required mention not found")
                return False

            # Thread filter - extract from the nested event
            if self.require_thread and not actual_event.get("thread_ts"):
                logger.debug("Required thread not found")
                return False

            # Command prefix filter (for message events)
            if event_type == "message" and self.command_prefix:
                message_text = actual_event.get("text", "")
                if not message_text.strip().startswith(self.command_prefix):
                    logger.debug(f"Message doesn't start with command prefix {self.command_prefix}")
                    return False

            logger.info(f"✅ Slack event matches filters for workflow {self.workflow_id}")
            return True

        except Exception as e:
            logger.error(
                f"Error processing Slack event for workflow {self.workflow_id}: {e}", exc_info=True
            )
            return False

    async def trigger_from_slack_event(self, event_data: dict) -> ExecutionResult:
        """
        Trigger the workflow from a Slack event

        Args:
            event_data: The Slack event data

        Returns:
            ExecutionResult with execution details
        """
        try:
            # Extract the nested event data
            actual_event = event_data.get("event", {})

            # Extract relevant data from the event
            trigger_data = {
                "trigger_type": self.trigger_type,
                "event_type": actual_event.get("type", ""),
                "message": actual_event.get("text", ""),
                "user_id": actual_event.get("user", ""),
                "channel_id": actual_event.get("channel", ""),
                "team_id": event_data.get("team_id", ""),  # team_id is at top level
                "timestamp": actual_event.get("ts", ""),
                "thread_ts": actual_event.get("thread_ts"),
                "workspace_id": self.workspace_id,
                "event_data": event_data,
            }

            # Call the base trigger workflow method
            return await self._trigger_workflow(trigger_data)

        except Exception as e:
            logger.error(f"Error triggering workflow from Slack event: {e}", exc_info=True)
            return ExecutionResult(
                status="error",
                message=f"Failed to trigger from Slack event: {str(e)}",
                trigger_data={"error": str(e)},
            )

    def _matches_channel_filter(self, channel_id: str) -> bool:
        """
        Check if channel matches the filter

        Args:
            channel_id: The Slack channel ID

        Returns:
            bool: True if channel matches filter
        """
        if not self.channel_filter:
            return True

        try:
            if self.channel_filter.startswith("C"):  # Channel ID format
                return channel_id == self.channel_filter
            else:  # Treat as regex pattern
                return bool(re.match(self.channel_filter, channel_id))
        except re.error as e:
            logger.warning(f"Invalid channel filter regex '{self.channel_filter}': {e}")
            return False

    def _matches_user_filter(self, user_id: str) -> bool:
        """
        Check if user matches the filter

        Args:
            user_id: The Slack user ID

        Returns:
            bool: True if user matches filter
        """
        if not self.user_filter:
            return True

        try:
            if self.user_filter.startswith("U"):  # User ID format
                return user_id == self.user_filter
            else:  # Treat as regex pattern
                return bool(re.match(self.user_filter, user_id))
        except re.error as e:
            logger.warning(f"Invalid user filter regex '{self.user_filter}': {e}")
            return False

    def _has_bot_mention(self, event_data: dict) -> bool:
        """
        Check if the event contains a bot mention

        Args:
            event_data: The Slack event data

        Returns:
            bool: True if bot is mentioned
        """
        try:
            # Check for app_mention event type
            if event_data.get("type") == "app_mention":
                return True

            # Check for direct mention in message text
            message_text = event_data.get("text", "")
            if "<@U" in message_text:  # Basic mention pattern
                return True

            # Check for mention in blocks (rich text format)
            blocks = event_data.get("blocks", [])
            for block in blocks:
                if self._block_contains_mention(block):
                    return True

            return False

        except Exception as e:
            logger.warning(f"Error checking bot mention: {e}")
            return False

    def _block_contains_mention(self, block: dict) -> bool:
        """
        Check if a Slack block contains a bot mention

        Args:
            block: Slack block data

        Returns:
            bool: True if block contains mention
        """
        try:
            if block.get("type") == "rich_text":
                elements = block.get("elements", [])
                for element in elements:
                    if element.get("type") == "rich_text_section":
                        text_elements = element.get("elements", [])
                        for text_elem in text_elements:
                            if text_elem.get("type") == "user" and text_elem.get("user_id"):
                                return True
            return False
        except Exception:
            return False

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check for the Slack trigger

        Returns:
            Dict with health status
        """
        health_status = await super().health_check()

        health_status.update(
            {
                "slack_specific": {
                    "workspace_id": self.workspace_id,
                    "channel_filter": self.channel_filter,
                    "event_types": self.event_types,
                    "mention_required": self.mention_required,
                    "ignore_bots": self.ignore_bots,
                }
            }
        )

        return health_status
