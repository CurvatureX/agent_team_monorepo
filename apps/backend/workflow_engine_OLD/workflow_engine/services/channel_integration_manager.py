"""
Channel Integration Manager for HIL Node System.

Handles sending HIL requests through various communication channels
(Slack, email, webhooks, in-app notifications) and processing responses.
"""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from shared.models.human_in_loop import (
    HILApprovalRequest,
    HILChannelType,
    HILInputData,
    HILInputRequest,
    HILInteractionType,
    HILSelectionRequest,
)


class ChannelIntegration(ABC):
    """Abstract base class for channel integrations."""

    @abstractmethod
    async def send_request(
        self, interaction_data: Dict[str, Any], hil_input: HILInputData
    ) -> Dict[str, Any]:
        """Send HIL request through this channel."""
        pass

    @abstractmethod
    def format_message(self, hil_input: HILInputData) -> str:
        """Format HIL request as channel-appropriate message."""
        pass


class SlackIntegration(ChannelIntegration):
    """Slack channel integration for HIL requests."""

    def __init__(self, slack_token: Optional[str] = None):
        self.logger = logging.getLogger(f"{__name__}.SlackIntegration")
        self.slack_token = slack_token
        # TODO: Initialize Slack client when token available
        self.slack_client = None

        if not slack_token:
            self.logger.warning("Slack integration initialized without token")

    async def send_request(
        self, interaction_data: Dict[str, Any], hil_input: HILInputData
    ) -> Dict[str, Any]:
        """Send HIL request via Slack."""
        channel = hil_input.channel_config.slack_channel
        message = self.format_message(hil_input)

        # TODO: Use actual Slack API
        # For now, mock the Slack API call
        self.logger.info(f"Mock Slack message sent to {channel}")

        return {
            "channel": channel,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "message_id": f"slack_msg_{interaction_data['id'][:8]}",
            "status": "sent",
        }

    def format_message(self, hil_input: HILInputData) -> str:
        """Format HIL request as Slack message with interactive elements."""
        if hil_input.interaction_type == HILInteractionType.APPROVAL:
            return self._format_approval_message(hil_input.approval_request)
        elif hil_input.interaction_type == HILInteractionType.INPUT:
            return self._format_input_message(hil_input.input_request)
        elif hil_input.interaction_type == HILInteractionType.SELECTION:
            return self._format_selection_message(hil_input.selection_request)
        else:
            return f"HIL Request: {hil_input.interaction_type}"

    def _format_approval_message(self, approval_request: HILApprovalRequest) -> str:
        """Format approval request as Slack message."""
        message_parts = [f"🔔 **{approval_request.title}**", f"{approval_request.description}", ""]

        if approval_request.approval_data:
            message_parts.append("**Details:**")
            for key, value in approval_request.approval_data.items():
                message_parts.append(f"• {key}: {value}")
            message_parts.append("")

        message_parts.append("**Please respond with:**")
        for option in approval_request.approval_options:
            message_parts.append(f"• `{option}`")

        if approval_request.approval_reason_required:
            message_parts.append("\n*Please include a reason for your decision.*")

        return "\n".join(message_parts)

    def _format_input_message(self, input_request: HILInputRequest) -> str:
        """Format input request as Slack message."""
        message_parts = [
            f"📝 **{input_request.title}**",
            f"{input_request.description}",
            "",
            "**Required Information:**",
        ]

        for field in input_request.fields:
            field_desc = f"• **{field.label}**"
            if field.field_type != "text":
                field_desc += f" ({field.field_type})"
            if not field.required:
                field_desc += " (optional)"
            message_parts.append(field_desc)

            if field.options:
                message_parts.append(f"  Options: {', '.join(field.options)}")

        return "\n".join(message_parts)

    def _format_selection_message(self, selection_request: HILSelectionRequest) -> str:
        """Format selection request as Slack message."""
        message_parts = [
            f"🔽 **{selection_request.title}**",
            f"{selection_request.description}",
            "",
            "**Available Options:**",
        ]

        for i, option in enumerate(selection_request.options, 1):
            option_text = f"{i}. **{option.label}**"
            if option.description:
                option_text += f"\n   {option.description}"
            message_parts.append(option_text)

        selection_info = []
        if selection_request.multiple_selection:
            selection_info.append(
                f"Select {selection_request.min_selections}-{selection_request.max_selections or 'all'} options"
            )
        else:
            selection_info.append("Select one option")

        if selection_info:
            message_parts.extend(["", f"*{'; '.join(selection_info)}*"])

        return "\n".join(message_parts)


class EmailIntegration(ChannelIntegration):
    """Email integration for HIL requests."""

    def __init__(self, smtp_config: Optional[Dict[str, Any]] = None):
        self.logger = logging.getLogger(f"{__name__}.EmailIntegration")
        self.smtp_config = smtp_config or {}
        # TODO: Initialize email client when config available

        if not smtp_config:
            self.logger.warning("Email integration initialized without SMTP config")

    async def send_request(
        self, interaction_data: Dict[str, Any], hil_input: HILInputData
    ) -> Dict[str, Any]:
        """Send HIL request via email."""
        recipients = hil_input.channel_config.email_recipients or []
        subject = (
            hil_input.channel_config.email_subject or f"HIL Request: {hil_input.interaction_type}"
        )
        message = self.format_message(hil_input)

        # TODO: Use actual email service (SMTP, SendGrid, etc.)
        # For now, mock the email sending
        self.logger.info(f"Mock email sent to {len(recipients)} recipients")

        return {
            "recipients": recipients,
            "subject": subject,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "message_id": f"email_msg_{interaction_data['id'][:8]}",
            "status": "sent",
        }

    def format_message(self, hil_input: HILInputData) -> str:
        """Format HIL request as HTML email."""
        # TODO: Create proper HTML email templates
        # For now, return plain text
        if hil_input.interaction_type == HILInteractionType.APPROVAL:
            return self._format_approval_email(hil_input.approval_request)
        elif hil_input.interaction_type == HILInteractionType.INPUT:
            return self._format_input_email(hil_input.input_request)
        elif hil_input.interaction_type == HILInteractionType.SELECTION:
            return self._format_selection_email(hil_input.selection_request)
        else:
            return f"HIL Request: {hil_input.interaction_type}"

    def _format_approval_email(self, approval_request: HILApprovalRequest) -> str:
        """Format approval request as email."""
        return f"""
Subject: {approval_request.title}

{approval_request.description}

Please reply to this email with one of the following options:
{chr(10).join(f"• {option}" for option in approval_request.approval_options)}

{'Please include a reason for your decision.' if approval_request.approval_reason_required else ''}
"""

    def _format_input_email(self, input_request: HILInputRequest) -> str:
        """Format input request as email."""
        fields_text = "\n".join(
            f"• {field.label} ({'required' if field.required else 'optional'})"
            for field in input_request.fields
        )

        return f"""
Subject: {input_request.title}

{input_request.description}

Please provide the following information:
{fields_text}

Reply to this email with the requested information.
"""

    def _format_selection_email(self, selection_request: HILSelectionRequest) -> str:
        """Format selection request as email."""
        options_text = "\n".join(
            f"{i}. {option.label}" + (f" - {option.description}" if option.description else "")
            for i, option in enumerate(selection_request.options, 1)
        )

        return f"""
Subject: {selection_request.title}

{selection_request.description}

Available options:
{options_text}

Please reply with your selection(s).
"""


class WebhookIntegration(ChannelIntegration):
    """Webhook integration for HIL requests."""

    def __init__(self, http_client=None):
        self.logger = logging.getLogger(f"{__name__}.WebhookIntegration")
        self.http_client = http_client  # TODO: Use actual HTTP client

    async def send_request(
        self, interaction_data: Dict[str, Any], hil_input: HILInputData
    ) -> Dict[str, Any]:
        """Send HIL request via webhook."""
        webhook_url = hil_input.channel_config.webhook_url
        headers = hil_input.channel_config.webhook_headers or {}
        payload = self.format_message(hil_input)

        # TODO: Use actual HTTP client to send webhook
        # For now, mock the webhook call
        self.logger.info(f"Mock webhook sent to {webhook_url}")

        return {
            "webhook_url": webhook_url,
            "payload": payload,
            "headers": headers,
            "timestamp": datetime.now().isoformat(),
            "status": "sent",
        }

    def format_message(self, hil_input: HILInputData) -> Dict[str, Any]:
        """Format HIL request as webhook payload."""
        return {
            "interaction_type": hil_input.interaction_type.value,
            "channel_type": hil_input.channel_config.channel_type.value,
            "request_data": hil_input.dict(),
            "timestamp": datetime.now().isoformat(),
            "priority": hil_input.priority.value,
            "correlation_id": hil_input.correlation_id,
        }


class InAppIntegration(ChannelIntegration):
    """In-app notification integration for HIL requests."""

    def __init__(self, notification_service=None):
        self.logger = logging.getLogger(f"{__name__}.InAppIntegration")
        self.notification_service = notification_service  # TODO: Use actual notification service

    async def send_request(
        self, interaction_data: Dict[str, Any], hil_input: HILInputData
    ) -> Dict[str, Any]:
        """Send HIL request via in-app notification."""
        user_ids = hil_input.channel_config.app_notification_users or []
        notification_data = self.format_message(hil_input)

        # TODO: Use actual notification service
        # For now, mock the notification
        self.logger.info(f"Mock in-app notification sent to {len(user_ids)} users")

        return {
            "user_ids": user_ids,
            "notification_data": notification_data,
            "timestamp": datetime.now().isoformat(),
            "status": "sent",
        }

    def format_message(self, hil_input: HILInputData) -> Dict[str, Any]:
        """Format HIL request as in-app notification."""
        return {
            "type": "hil_request",
            "interaction_type": hil_input.interaction_type.value,
            "title": self._get_title_from_request(hil_input),
            "description": self._get_description_from_request(hil_input),
            "priority": hil_input.priority.value,
            "timeout_hours": hil_input.timeout_hours,
            "correlation_id": hil_input.correlation_id,
            "request_data": hil_input.dict(),
        }

    def _get_title_from_request(self, hil_input: HILInputData) -> str:
        """Extract title from HIL request."""
        if hil_input.approval_request:
            return hil_input.approval_request.title
        elif hil_input.input_request:
            return hil_input.input_request.title
        elif hil_input.selection_request:
            return hil_input.selection_request.title
        else:
            return f"HIL {hil_input.interaction_type.value.title()} Request"

    def _get_description_from_request(self, hil_input: HILInputData) -> str:
        """Extract description from HIL request."""
        if hil_input.approval_request:
            return hil_input.approval_request.description
        elif hil_input.input_request:
            return hil_input.input_request.description
        elif hil_input.selection_request:
            return hil_input.selection_request.description
        else:
            return f"Please respond to this {hil_input.interaction_type.value} request."


class ChannelIntegrationManager:
    """Manager for all channel integrations."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize channel integration manager.

        Args:
            config: Configuration dict with channel-specific settings
        """
        self.logger = logging.getLogger(__name__)
        self.config = config or {}

        # Initialize channel integrations
        self.integrations = {
            HILChannelType.SLACK: SlackIntegration(
                slack_token=self.config.get("slack", {}).get("token")
            ),
            HILChannelType.EMAIL: EmailIntegration(smtp_config=self.config.get("email", {})),
            HILChannelType.WEBHOOK: WebhookIntegration(
                http_client=self.config.get("webhook", {}).get("http_client")
            ),
            HILChannelType.APP: InAppIntegration(
                notification_service=self.config.get("app", {}).get("notification_service")
            ),
        }

        self.logger.info(
            f"Initialized ChannelIntegrationManager with {len(self.integrations)} integrations"
        )

    async def send_hil_request(
        self, interaction_data: Dict[str, Any], hil_input: HILInputData
    ) -> Dict[str, Any]:
        """Send HIL request through appropriate channel.

        Args:
            interaction_data: HIL interaction record from database
            hil_input: HIL input data with channel configuration

        Returns:
            Dict with sending result and metadata
        """
        channel_type = hil_input.channel_config.channel_type

        if channel_type not in self.integrations:
            raise ValueError(f"Unsupported channel type: {channel_type}")

        integration = self.integrations[channel_type]

        try:
            result = await integration.send_request(interaction_data, hil_input)

            self.logger.info(
                f"Sent HIL request via {channel_type.value} "
                f"for interaction {interaction_data['id']}"
            )

            return {
                "success": True,
                "channel_type": channel_type.value,
                "result": result,
                "sent_at": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Failed to send HIL request via {channel_type.value}: {str(e)}")

            return {
                "success": False,
                "channel_type": channel_type.value,
                "error": str(e),
                "failed_at": datetime.now().isoformat(),
            }

    def get_integration(self, channel_type: HILChannelType) -> Optional[ChannelIntegration]:
        """Get integration for specific channel type."""
        return self.integrations.get(channel_type)

    def is_channel_available(self, channel_type: HILChannelType) -> bool:
        """Check if channel integration is available and configured."""
        integration = self.integrations.get(channel_type)
        if not integration:
            return False

        # TODO: Add channel-specific availability checks
        # For now, assume all integrations are available
        return True

    def get_available_channels(self) -> List[HILChannelType]:
        """Get list of available channel types."""
        return [
            channel_type
            for channel_type in self.integrations.keys()
            if self.is_channel_available(channel_type)
        ]
