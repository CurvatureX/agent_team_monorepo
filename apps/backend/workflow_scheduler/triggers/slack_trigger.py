"""
Slack Trigger Implementation

This module implements the Slack trigger for workflow_scheduler,
supporting various Slack events like messages, mentions, reactions, etc.
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional

import httpx

from shared.models.execution_new import ExecutionStatus
from shared.models.node_enums import IntegrationProvider, SlackEventType, TriggerSubtype
from shared.models.trigger import TriggerStatus
from shared.models.workflow_new import WorkflowExecutionResponse
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
        # Handle both 'events' and 'event_types' keys for backward compatibility
        self.event_types = trigger_config.get("event_types") or trigger_config.get(
            "events", [SlackEventType.MESSAGE.value, SlackEventType.APP_MENTION.value]
        )
        self.mention_required = trigger_config.get("mention_required", False)
        # Don't require command prefix by default - only if explicitly configured
        self.command_prefix = trigger_config.get("command_prefix", None)
        self.user_filter = trigger_config.get("user_filter")
        # Handle both 'ignore_bots' and 'filter_bot_messages' keys
        self.ignore_bots = trigger_config.get("ignore_bots") or trigger_config.get(
            "filter_bot_messages", True
        )
        self.require_thread = trigger_config.get("require_thread", False)

        # Note: Channel filtering now uses channel IDs resolved during deployment
        # No need for channel name cache since we don't make API calls during triggers

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
                f"❌ Failed to stop SlackTrigger for workflow {self.workflow_id}: {e}",
                exc_info=True,
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
                logger.info(
                    f"❌ WORKFLOW {self.workflow_id}: Event type '{event_type}' not in expected types {self.event_types} - SKIPPING"
                )
                return False

            logger.info(f"✅ Event type '{event_type}' matches expected types")

            # Channel filter - extract from the nested event
            channel_id = actual_event.get("channel", "")
            if not await self._matches_channel_filter_async(channel_id):
                logger.info(
                    f"❌ WORKFLOW {self.workflow_id}: Channel {channel_id} doesn't match filter '{self.channel_filter}' - SKIPPING"
                )
                return False

            # User filter - extract from the nested event
            user_id = actual_event.get("user", "")
            if not self._matches_user_filter(user_id):
                logger.info(
                    f"❌ WORKFLOW {self.workflow_id}: User {user_id} doesn't match filter '{self.user_filter}' - SKIPPING"
                )
                return False

            # Bot filter - extract from the nested event
            bot_id = actual_event.get("bot_id")
            if self.ignore_bots and bot_id:
                logger.info(
                    f"❌ WORKFLOW {self.workflow_id}: Ignoring bot message from bot_id: {bot_id} - SKIPPING"
                )
                return False

            # Mention filter - pass the nested event
            if self.mention_required and not self._has_bot_mention(actual_event):
                logger.info(f"❌ WORKFLOW {self.workflow_id}: Required mention not found - SKIPPING")
                return False

            # Thread filter - extract from the nested event
            if self.require_thread and not actual_event.get("thread_ts"):
                logger.info(f"❌ WORKFLOW {self.workflow_id}: Required thread not found - SKIPPING")
                return False

            # Command prefix filter (for message events)
            if event_type == SlackEventType.MESSAGE.value and self.command_prefix:
                message_text = actual_event.get("text", "")
                if not message_text.strip().startswith(self.command_prefix):
                    logger.info(
                        f"❌ WORKFLOW {self.workflow_id}: Message doesn't start with command prefix '{self.command_prefix}' - SKIPPING"
                    )
                    return False

            logger.info(
                f"✅ WORKFLOW {self.workflow_id}: ALL FILTERS PASSED - WORKFLOW WILL BE TRIGGERED"
            )
            return True

        except Exception as e:
            logger.error(
                f"❌ WORKFLOW {self.workflow_id}: Error processing Slack event: {e}",
                exc_info=True,
            )
            return False

    async def trigger_from_slack_event(self, event_data: dict) -> WorkflowExecutionResponse:
        """
        Trigger the workflow from a Slack event

        Args:
            event_data: The Slack event data

        Returns:
            WorkflowExecutionResponse with execution details
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
            return WorkflowExecutionResponse(
                execution_id=f"exec_{self.workflow_id}",
                workflow_id=self.workflow_id,
                status=ExecutionStatus.ERROR,
                message=f"Failed to trigger from Slack event: {str(e)}",
            )

    async def _get_channel_name(self, channel_id: str) -> Optional[str]:
        """
        Get channel name from channel ID using Slack API with user's OAuth token

        Args:
            channel_id: The Slack channel ID

        Returns:
            str: Channel name without # prefix, or None if not found
        """
        if not channel_id:
            return None

        # Check cache first
        if channel_id in self._channel_name_cache:
            return self._channel_name_cache[channel_id]

        try:
            # Get user's Slack OAuth token from database
            slack_token = await self._get_user_slack_token()
            if not slack_token:
                logger.warning(
                    f"No Slack OAuth token available for workflow {self.workflow_id} owner - channel name lookup failed"
                )
                return None

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://slack.com/api/conversations.info",
                    headers={"Authorization": f"Bearer {slack_token}"},
                    params={"channel": channel_id},
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("ok"):
                        channel_name = data.get("channel", {}).get("name")
                        if channel_name:
                            # Cache the result
                            self._channel_name_cache[channel_id] = channel_name
                            logger.debug(f"Resolved channel {channel_id} to name: {channel_name}")
                            return channel_name
                    else:
                        error_msg = data.get("error", "unknown")
                        if error_msg == "missing_scope":
                            logger.warning(
                                f"Slack OAuth token missing 'channels:read' scope for channel lookup - "
                                f"channel {channel_id} filtering will use channel ID only"
                            )
                        else:
                            logger.warning(f"Slack API error for channel {channel_id}: {error_msg}")
                else:
                    logger.warning(f"HTTP error getting channel info: {response.status_code}")

        except Exception as e:
            logger.warning(f"Failed to get channel name for {channel_id}: {e}")

        return None

    async def _get_user_slack_token(self) -> Optional[str]:
        """
        Get the workflow owner's Slack OAuth token from the database

        Returns:
            str: Slack access token, or None if not found
        """
        try:
            # First get the workflow owner's user_id
            from workflow_scheduler.core.supabase_client import get_supabase_client

            supabase = get_supabase_client()
            if not supabase:
                logger.error("Supabase client not available")
                return None

            # Get workflow owner
            workflow_result = (
                supabase.table("workflows").select("user_id").eq("id", self.workflow_id).execute()
            )

            if not workflow_result.data:
                logger.warning(f"Workflow {self.workflow_id} not found in database")
                return None

            user_id = workflow_result.data[0].get("user_id")
            if not user_id:
                logger.warning(f"No user_id found for workflow {self.workflow_id}")
                return None

            # Get user's Slack OAuth token
            oauth_result = (
                supabase.table("oauth_tokens")
                .select("access_token")
                .eq("user_id", user_id)
                .eq("integration_id", IntegrationProvider.SLACK.value)
                .eq("is_active", True)
                .execute()
            )

            if not oauth_result.data:
                logger.warning(f"No active Slack OAuth token found for user {user_id}")
                return None

            access_token = oauth_result.data[0].get("access_token")
            if access_token:
                logger.debug(
                    f"Retrieved Slack token for user {user_id} (workflow {self.workflow_id})"
                )
                return access_token
            else:
                logger.warning(f"Empty access_token for user {user_id}")
                return None

        except Exception as e:
            logger.error(
                f"Error getting user Slack token for workflow {self.workflow_id}: {e}",
                exc_info=True,
            )
            return None

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
            else:
                # Try to resolve channel name and compare
                # Note: This needs to be async, so we'll handle it in the calling method
                return False  # Will be handled asynchronously
        except re.error as e:
            logger.warning(f"Invalid channel filter regex '{self.channel_filter}': {e}")
            return False

    async def _matches_channel_filter_async(self, channel_id: str) -> bool:
        """
        Match channel filter using channel ID comparison (no API calls needed)

        Channel filters should be resolved to channel IDs during deployment time,
        so we only need to do simple string comparison here.

        Args:
            channel_id: The Slack channel ID

        Returns:
            bool: True if channel matches filter
        """
        if not self.channel_filter:
            return True

        try:
            # The channel_filter should now always be a channel ID (resolved during deployment)
            # Support both single channel ID and comma-separated list of channel IDs
            if "," in self.channel_filter:
                # Multiple channel IDs
                allowed_channels = [ch.strip() for ch in self.channel_filter.split(",")]
                matches = channel_id in allowed_channels
            else:
                # Single channel ID
                matches = channel_id == self.channel_filter

            if matches:
                logger.debug(f"Channel {channel_id} matches filter '{self.channel_filter}'")
            else:
                logger.debug(f"Channel {channel_id} doesn't match filter '{self.channel_filter}'")

            return matches

        except Exception as e:
            logger.warning(f"Error matching channel filter '{self.channel_filter}': {e}")
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
            if event_data.get("type") == SlackEventType.APP_MENTION.value:
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
