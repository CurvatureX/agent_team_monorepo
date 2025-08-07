"""
Notification service for workflow_scheduler
Sends Slack notifications when triggers are activated
"""

import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

# Add shared path for Slack SDK
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from shared.sdks.slack_sdk import SlackAPIError, SlackBlockBuilder, SlackWebClient
from workflow_scheduler.core.config import settings
from workflow_scheduler.models.triggers import ExecutionResult

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications when workflows are triggered"""

    def __init__(self, slack_bot_token: Optional[str] = None):
        self.target_channel = "#webhook-test"  # Target Slack channel
        self.slack_client: Optional[SlackWebClient] = None
        self._initialize_slack_client(slack_bot_token)

    def _initialize_slack_client(self, bot_token: Optional[str] = None):
        """Initialize Slack client with bot token"""
        try:
            # Use provided token or fall back to config default
            if bot_token is None:
                from workflow_scheduler.core.config import settings

                bot_token = settings.slack_bot_token

            if not bot_token:
                logger.warning("No Slack bot token available - notifications will be logged only")
                return

            # Create Slack client
            self.slack_client = SlackWebClient(bot_token)

            # Test authentication
            try:
                auth_info = self.slack_client.auth_test()
                logger.info(f"🤖 Slack notification service initialized successfully")
                logger.info(
                    f"   👤 Bot: @{auth_info.get('user', 'unknown')} ({auth_info.get('user_id', 'unknown')})"
                )
                logger.info(
                    f"   🏢 Team: {auth_info.get('team', 'unknown')} ({auth_info.get('team_id', 'unknown')})"
                )
                logger.info(f"   📢 Target Channel: {self.target_channel}")

            except SlackAPIError as e:
                logger.warning(
                    f"Slack authentication test failed: {e} - notifications will be logged only"
                )
                self.slack_client = None

        except Exception as e:
            logger.error(f"Failed to initialize Slack client: {e}")
            logger.info(
                "Make sure SLACK_BOT_TOKEN is a valid bot token with appropriate permissions"
            )
            self.slack_client = None

    async def send_trigger_notification(
        self, workflow_id: str, trigger_type: str, trigger_data: Dict[str, Any]
    ) -> ExecutionResult:
        """
        Send notification when a workflow is triggered

        Args:
            workflow_id: The workflow that was triggered
            trigger_type: Type of trigger (CRON, MANUAL, WEBHOOK, etc)
            trigger_data: Data associated with the trigger

        Returns:
            ExecutionResult with notification status
        """
        try:
            # Log the trigger event
            logger.info(f"🔔 Trigger notification: {workflow_id} triggered by {trigger_type}")

            # Send Slack notification if client is available
            if self.slack_client:
                success = await self._send_slack_notification(
                    workflow_id, trigger_type, trigger_data
                )
                if success:
                    logger.info(
                        f"💬 Slack notification sent successfully to {self.target_channel} for workflow {workflow_id}"
                    )
                    status = "notified_slack"
                    message = f"Slack notification sent for {trigger_type} trigger"
                else:
                    logger.warning(f"💬 Slack notification failed for workflow {workflow_id}")
                    status = "notified_log_only"
                    message = f"Slack failed, logged {trigger_type} trigger"
            else:
                logger.info(f"📝 Logged trigger notification for workflow {workflow_id}")
                status = "notified_log_only"
                message = f"Logged {trigger_type} trigger (Slack not configured)"

            return ExecutionResult(status=status, message=message, trigger_data=trigger_data)

        except Exception as e:
            error_msg = f"Failed to send trigger notification: {str(e)}"
            logger.error(error_msg, exc_info=True)

            return ExecutionResult(
                status="notification_failed", message=error_msg, trigger_data=trigger_data
            )

    async def _send_slack_notification(
        self, workflow_id: str, trigger_type: str, trigger_data: Dict[str, Any]
    ) -> bool:
        """Send Slack notification using blocks for rich formatting"""
        try:
            # Clean trigger type for display
            display_trigger_type = trigger_type.replace("TRIGGER_", "").title()

            # Create rich Slack message using blocks
            blocks = self._generate_slack_blocks(workflow_id, display_trigger_type, trigger_data)

            # Fallback text for notifications
            fallback_text = f"🚀 Workflow {workflow_id} triggered by {display_trigger_type}"

            # Send message to Slack
            response = self.slack_client.send_message(
                channel=self.target_channel, text=fallback_text, blocks=blocks
            )

            if response.get("ok"):
                logger.debug(f"Slack message sent with timestamp: {response.get('ts')}")
                return True
            else:
                logger.error(f"Slack API returned error: {response.get('error')}")
                return False

        except SlackAPIError as e:
            logger.error(f"Slack API error sending notification: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}", exc_info=True)
            return False

    def _generate_slack_blocks(
        self, workflow_id: str, display_trigger_type: str, trigger_data: Dict[str, Any]
    ) -> list:
        """Generate Slack blocks for rich message formatting"""

        # Header block with emoji and title
        blocks = [
            SlackBlockBuilder.header(f"🚀 Workflow Triggered"),
            SlackBlockBuilder.section(
                f"*Workflow ID:* `{workflow_id}`\n*Trigger Type:* {display_trigger_type}\n*Time:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
            ),
        ]

        # Add trigger-specific details
        trigger_details = []

        if "CRON" in workflow_id.upper():
            cron_expr = trigger_data.get("cron_expression", "Unknown")
            timezone = trigger_data.get("timezone", "UTC")
            trigger_details.extend([f"*Cron Expression:* `{cron_expr}`", f"*Timezone:* {timezone}"])

        elif "MANUAL" in workflow_id.upper():
            user_id = trigger_data.get("user_id", "Unknown")
            confirmation = trigger_data.get("confirmation", False)
            trigger_details.extend(
                [
                    f"*Triggered By:* {user_id}",
                    f"*Confirmation:* {'✅ Yes' if confirmation else '❌ No'}",
                ]
            )

        elif "WEBHOOK" in workflow_id.upper():
            method = trigger_data.get("method", "Unknown")
            path = trigger_data.get("path", "Unknown")
            remote_addr = trigger_data.get("remote_addr", "Unknown")
            trigger_details.extend(
                [f"*HTTP Method:* {method}", f"*Path:* `{path}`", f"*Remote IP:* {remote_addr}"]
            )

        elif "GITHUB" in workflow_id.upper():
            event_type = trigger_data.get("event_type", "Unknown")
            payload = trigger_data.get("payload", {})
            repository = payload.get("repository", {}).get("full_name", "Unknown")
            sender = payload.get("sender", {}).get("login", "Unknown")
            trigger_details.extend(
                [
                    f"*GitHub Event:* {event_type}",
                    f"*Repository:* {repository}",
                    f"*User:* @{sender}",
                ]
            )

        # Add trigger details section if we have any
        if trigger_details:
            blocks.append(SlackBlockBuilder.section("\n".join(trigger_details)))

        # Add divider
        blocks.append(SlackBlockBuilder.divider())

        # Add note about test mode
        blocks.append(
            SlackBlockBuilder.section(
                "💡 *Note:* This is a test notification. The actual workflow was not executed."
            )
        )

        # Add footer context
        blocks.append(
            SlackBlockBuilder.context(
                [
                    SlackBlockBuilder.text_element(
                        "🔧 Workflow Scheduler | 📍 workflow_scheduler service"
                    )
                ]
            )
        )

        return blocks

    async def health_check(self) -> Dict[str, Any]:
        """Check health of notification service"""
        return {
            "service": "notification_service",
            "slack_client_available": self.slack_client is not None,
            "target_channel": self.target_channel,
            "status": "healthy" if self.slack_client else "degraded",
        }
