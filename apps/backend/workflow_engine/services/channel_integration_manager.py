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
        import os

        self.logger = logging.getLogger(f"{__name__}.SlackIntegration")
        # Note: Slack token should be retrieved per-user from OAuth tokens table
        # No longer use environment variable for token
        self.slack_token = slack_token  # Only use explicitly passed token

        if not self.slack_token:
            self.logger.info(
                "Slack integration initialized without token - will need to retrieve OAuth token per-user"
            )

    async def send_request(
        self, interaction_data: Dict[str, Any], hil_input: HILInputData
    ) -> Dict[str, Any]:
        """Send HIL request via Slack."""
        import httpx

        channel = hil_input.channel_config.slack_channel
        message = self.format_message(hil_input)

        if self.slack_token:
            try:
                # Real Slack API call
                headers = {
                    "Authorization": f"Bearer {self.slack_token}",
                    "Content-Type": "application/json",
                }

                payload = {
                    "channel": channel,
                    "text": message,
                    "username": "Workflow HIL Bot",
                    "icon_emoji": ":question:",
                }

                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://slack.com/api/chat.postMessage",
                        headers=headers,
                        json=payload,
                        timeout=10.0,
                    )

                result = response.json()

                if result.get("ok", False):
                    self.logger.info(f"✅ HIL message sent to Slack channel {channel}")
                    return {
                        "channel": channel,
                        "message": message,
                        "timestamp": datetime.now().isoformat(),
                        "message_id": result.get("ts"),
                        "status": "sent",
                        "slack_response": result,
                    }
                else:
                    error = result.get("error", "unknown_error")
                    self.logger.error(f"❌ Slack API error: {error}")
                    return {
                        "channel": channel,
                        "message": message,
                        "timestamp": datetime.now().isoformat(),
                        "status": "failed",
                        "error": error,
                    }

            except Exception as e:
                self.logger.error(f"Failed to send Slack message: {str(e)}")
                return {
                    "channel": channel,
                    "message": message,
                    "timestamp": datetime.now().isoformat(),
                    "status": "failed",
                    "error": str(e),
                }
        else:
            # Return error when no token instead of mock response
            error_msg = "❌ No Slack authentication token found. Please connect your Slack account in integrations settings."
            self.logger.error(error_msg)
            return {
                "status": "failed",
                "error": error_msg,
                "reason": "missing_slack_token",
                "solution": "Connect Slack account in integrations settings",
                "channel": channel,
                "timestamp": datetime.now().isoformat(),
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
        import os

        self.logger = logging.getLogger(f"{__name__}.EmailIntegration")

        # Use provided config or environment variables
        if smtp_config:
            self.smtp_config = smtp_config
        else:
            self.smtp_config = {
                "smtp_server": os.getenv("SMTP_SERVER"),
                "smtp_port": int(os.getenv("SMTP_PORT", "587")) if os.getenv("SMTP_PORT") else 587,
                "smtp_user": os.getenv("SMTP_USER"),
                "smtp_password": os.getenv("SMTP_PASSWORD"),
                "from_email": os.getenv("SMTP_FROM_EMAIL") or os.getenv("SMTP_USER"),
            }

        if not self.smtp_config.get("smtp_server"):
            self.logger.warning("Email integration initialized without SMTP config")

    async def send_request(
        self, interaction_data: Dict[str, Any], hil_input: HILInputData
    ) -> Dict[str, Any]:
        """Send HIL request via email."""
        import asyncio
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        recipients = hil_input.channel_config.email_recipients or []
        subject = (
            hil_input.channel_config.email_subject or f"HIL Request: {hil_input.interaction_type}"
        )
        message = self.format_message(hil_input)

        if (
            self.smtp_config.get("smtp_server")
            and self.smtp_config.get("smtp_user")
            and self.smtp_config.get("smtp_password")
            and recipients
        ):
            try:
                # Real email sending
                self.logger.info(f"Sending HIL email to {len(recipients)} recipients")

                # Send email asynchronously
                result = await asyncio.get_event_loop().run_in_executor(
                    None, self._send_email_sync, recipients, subject, message
                )

                self.logger.info(f"✅ HIL email sent successfully to {len(recipients)} recipients")
                return {
                    "recipients": recipients,
                    "subject": subject,
                    "message": message,
                    "timestamp": datetime.now().isoformat(),
                    "message_id": f"email_msg_{interaction_data['id'][:8]}",
                    "status": "sent",
                    "email_sent": True,
                }

            except Exception as e:
                self.logger.error(f"Failed to send HIL email: {str(e)}")
                return {
                    "recipients": recipients,
                    "subject": subject,
                    "message": message,
                    "timestamp": datetime.now().isoformat(),
                    "status": "failed",
                    "error": str(e),
                }
        else:
            # Return error when no SMTP config instead of mock response
            error_msg = "❌ No email SMTP configuration found. Please configure SMTP settings in environment variables."
            self.logger.error(error_msg)
            return {
                "status": "failed",
                "error": error_msg,
                "reason": "missing_smtp_configuration",
                "solution": "Configure SMTP_SERVER, SMTP_PORT, SMTP_USER, and SMTP_PASSWORD environment variables",
                "recipients": recipients,
                "subject": subject,
                "timestamp": datetime.now().isoformat(),
            }

    def _send_email_sync(self, recipients: List[str], subject: str, message: str):
        """Synchronous email sending function."""
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        msg = MIMEMultipart()
        msg["From"] = self.smtp_config.get("from_email", self.smtp_config.get("smtp_user"))
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject

        # Attach message as both plain text and HTML
        msg.attach(MIMEText(message, "plain"))
        html_message = message.replace("\n", "<br>\n")
        msg.attach(MIMEText(html_message, "html"))

        # Send email
        server = smtplib.SMTP(self.smtp_config["smtp_server"], self.smtp_config["smtp_port"])
        server.starttls()
        server.login(self.smtp_config["smtp_user"], self.smtp_config["smtp_password"])
        text = msg.as_string()
        server.sendmail(msg["From"], recipients, text)
        server.quit()

    def format_message(self, hil_input: HILInputData) -> str:
        """Format HIL request as HTML email with professional templates."""
        if hil_input.interaction_type == HILInteractionType.APPROVAL:
            return self._format_approval_email_html(hil_input.approval_request)
        elif hil_input.interaction_type == HILInteractionType.INPUT:
            return self._format_input_email_html(hil_input.input_request)
        elif hil_input.interaction_type == HILInteractionType.SELECTION:
            return self._format_selection_email_html(hil_input.selection_request)
        else:
            return self._format_generic_email_html(hil_input.interaction_type)

    def _format_approval_email(self, approval_request: HILApprovalRequest) -> str:
        """Format approval request as email."""
        return f"""
Subject: {approval_request.title}

{approval_request.description}

Please reply to this email with one of the following options:
{chr(10).join(f"• {option}" for option in approval_request.approval_options)}

{'Please include a reason for your decision.' if approval_request.approval_reason_required else ''}
"""

    def _format_approval_email_html(self, approval_request: HILApprovalRequest) -> str:
        """Format approval request as professional HTML email."""
        options_html = "".join(
            f'<div style="margin: 8px 0; padding: 8px; background: #f0f0f0; border-radius: 4px;">• {option}</div>'
            for option in approval_request.approval_options
        )

        return f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #4CAF50; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9f9f9; padding: 20px; border-radius: 0 0 8px 8px; }}
        .options {{ margin: 15px 0; }}
        .footer {{ margin-top: 20px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>🚨 Approval Required</h2>
            <h3>{approval_request.title}</h3>
        </div>
        <div class="content">
            <p>{approval_request.description}</p>
            <p><strong>Please reply to this email with one of the following options:</strong></p>
            <div class="options">{options_html}</div>
            {f'<p><em>⚠️ Please include a reason for your decision.</em></p>' if approval_request.approval_reason_required else ''}
            <div class="footer">
                <p>This is an automated workflow notification. Reply to this email to provide your response.</p>
            </div>
        </div>
    </div>
</body>
</html>
"""

    def _format_input_email_html(self, input_request: HILInputRequest) -> str:
        """Format input request as professional HTML email."""
        fields_html = "".join(
            f"""<div style="margin: 10px 0;">
                <label style="font-weight: bold; display: block; margin-bottom: 4px;">
                    {field.label} {'*' if field.required else ''}
                </label>
                <p style="margin: 4px 0; color: #666; font-size: 14px;">{field.field_type}</p>
            </div>"""
            for field in input_request.fields
        )

        return f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #2196F3; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9f9f9; padding: 20px; border-radius: 0 0 8px 8px; }}
        .fields {{ margin: 15px 0; }}
        .footer {{ margin-top: 20px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>📝 Input Required</h2>
            <h3>{input_request.title}</h3>
        </div>
        <div class="content">
            <p>{input_request.description}</p>
            <p><strong>Please provide the following information in your reply:</strong></p>
            <div class="fields">{fields_html}</div>
            <div class="footer">
                <p>Reply to this email with the requested information in a clear format.</p>
            </div>
        </div>
    </div>
</body>
</html>
"""

    def _format_selection_email_html(self, selection_request: HILSelectionRequest) -> str:
        """Format selection request as professional HTML email."""
        options_html = "".join(
            f"""<div style="margin: 8px 0; padding: 10px; background: #e3f2fd; border-left: 4px solid #2196F3; border-radius: 4px;">
                <strong>{option.label}</strong>
                <br><small style="color: #666;">{option.value}</small>
            </div>"""
            for option in selection_request.options
        )

        return f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #FF9800; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9f9f9; padding: 20px; border-radius: 0 0 8px 8px; }}
        .options {{ margin: 15px 0; }}
        .footer {{ margin-top: 20px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>🔘 Selection Required</h2>
            <h3>{selection_request.title}</h3>
        </div>
        <div class="content">
            <p>{selection_request.description}</p>
            <p><strong>Please {'select one or more' if selection_request.multiple_selection else 'select one'} of the following options:</strong></p>
            <div class="options">{options_html}</div>
            <div class="footer">
                <p>Reply to this email with your selection{'s' if selection_request.multiple_selection else ''}.</p>
            </div>
        </div>
    </div>
</body>
</html>
"""

    def _format_generic_email_html(self, interaction_type: str) -> str:
        """Format generic HIL request as HTML email."""
        return f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #9C27B0; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9f9f9; padding: 20px; border-radius: 0 0 8px 8px; }}
        .footer {{ margin-top: 20px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>⚡ Workflow Action Required</h2>
            <h3>{interaction_type.replace('_', ' ').title()} Request</h3>
        </div>
        <div class="content">
            <p>A workflow requires your attention for a <strong>{interaction_type.replace('_', ' ').lower()}</strong> interaction.</p>
            <p>Please check your workflow dashboard for more details or reply to this email with your response.</p>
            <div class="footer">
                <p>This is an automated workflow notification.</p>
            </div>
        </div>
    </div>
</body>
</html>
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
        self.http_client = http_client

    async def send_request(
        self, interaction_data: Dict[str, Any], hil_input: HILInputData
    ) -> Dict[str, Any]:
        """Send HIL request via webhook."""
        import httpx

        webhook_url = hil_input.channel_config.webhook_url
        headers = hil_input.channel_config.webhook_headers or {}
        payload = self.format_message(hil_input)

        # Set default headers
        if "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"

        if not webhook_url:
            error_msg = "❌ No webhook URL provided for HIL request. Please configure webhook URL."
            self.logger.error(error_msg)
            return {
                "status": "failed",
                "error": error_msg,
                "reason": "missing_webhook_url",
                "solution": "Configure webhook URL in HIL node parameters or workflow settings",
                "payload": payload,
                "headers": headers,
                "timestamp": datetime.now().isoformat(),
            }

        try:
            # Real webhook HTTP request
            self.logger.info(f"Sending HIL webhook to {webhook_url}")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url, headers=headers, json=payload, timeout=30.0
                )

            self.logger.info(f"✅ Webhook sent successfully: {response.status_code}")

            # Try to parse response
            try:
                response_data = response.json()
            except:
                response_data = response.text

            return {
                "webhook_url": webhook_url,
                "payload": payload,
                "headers": headers,
                "timestamp": datetime.now().isoformat(),
                "status": "sent",
                "status_code": response.status_code,
                "response_data": response_data,
                "webhook_sent": True,
            }

        except Exception as e:
            self.logger.error(f"Failed to send HIL webhook: {str(e)}")
            return {
                "webhook_url": webhook_url,
                "payload": payload,
                "headers": headers,
                "timestamp": datetime.now().isoformat(),
                "status": "failed",
                "error": str(e),
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
        import os

        self.logger = logging.getLogger(f"{__name__}.InAppIntegration")
        self.notification_service = notification_service

        # Supabase connection for real-time notifications
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_secret_key = os.getenv("SUPABASE_SECRET_KEY")

        if not self.supabase_url or not self.supabase_secret_key:
            self.logger.warning("InApp integration initialized without Supabase config")

    async def send_request(
        self, interaction_data: Dict[str, Any], hil_input: HILInputData
    ) -> Dict[str, Any]:
        """Send HIL request via in-app notification."""
        user_ids = hil_input.channel_config.app_notification_users or []
        notification_data = self.format_message(hil_input)

        if self.supabase_url and self.supabase_secret_key and user_ids:
            try:
                # Real Supabase notification
                from supabase import create_client

                self.logger.info(f"Sending in-app notification to {len(user_ids)} users")

                supabase = create_client(self.supabase_url, self.supabase_secret_key)

                # Insert notification records into database
                notifications_created = []
                for user_id in user_ids:
                    notification_record = {
                        "user_id": user_id,
                        "type": "hil_request",
                        "title": self._get_title_from_request(hil_input),
                        "message": self._get_description_from_request(hil_input),
                        "data": notification_data,
                        "interaction_id": interaction_data.get("id"),
                        "priority": hil_input.priority.value,
                        "read": False,
                        "created_at": datetime.now().isoformat(),
                    }

                    result = supabase.table("notifications").insert(notification_record).execute()
                    if result.data:
                        notifications_created.append(result.data[0])

                # Send real-time notification via Supabase channels
                for user_id in user_ids:
                    channel_name = f"user_{user_id}_notifications"
                    await self._send_realtime_notification(
                        supabase, channel_name, notification_data
                    )

                self.logger.info(f"✅ In-app notifications sent to {len(user_ids)} users")

                return {
                    "user_ids": user_ids,
                    "notification_data": notification_data,
                    "timestamp": datetime.now().isoformat(),
                    "status": "sent",
                    "notifications_created": len(notifications_created),
                    "realtime_sent": True,
                }

            except Exception as e:
                self.logger.error(f"Failed to send in-app notification: {str(e)}")
                return {
                    "user_ids": user_ids,
                    "notification_data": notification_data,
                    "timestamp": datetime.now().isoformat(),
                    "status": "failed",
                    "error": str(e),
                }
        else:
            # Return error when no Supabase config instead of mock response
            error_msg = "❌ No Supabase configuration found for in-app notifications. Please configure SUPABASE_URL and SUPABASE_SECRET_KEY."
            self.logger.error(error_msg)
            return {
                "status": "failed",
                "error": error_msg,
                "reason": "missing_supabase_configuration",
                "solution": "Configure SUPABASE_URL and SUPABASE_SECRET_KEY environment variables",
                "user_ids": user_ids,
                "notification_data": notification_data,
                "timestamp": datetime.now().isoformat(),
            }

    async def _send_realtime_notification(
        self, supabase, channel_name: str, notification_data: Dict[str, Any]
    ):
        """Send real-time notification via Supabase realtime."""
        try:
            # Note: For real-time notifications, we would typically use Supabase's
            # real-time channels or push notifications. This is a placeholder
            # for the actual implementation which would depend on the frontend setup.

            # In a real implementation, you might:
            # 1. Use Supabase realtime channels
            # 2. Send push notifications via Firebase/APNs
            # 3. Use WebSocket connections
            # 4. Trigger browser notifications

            self.logger.debug(f"Real-time notification triggered for channel: {channel_name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send real-time notification: {str(e)}")
            return False

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

        # Channel-specific availability checks
        if channel_type == HILChannelType.SLACK:
            # Slack availability depends on OAuth token in database, not environment variable
            # This check is now generic - actual token validation happens at runtime
            return True  # Assume available, will validate OAuth token when needed
        elif channel_type == HILChannelType.EMAIL:
            return bool(
                os.getenv("SMTP_SERVER") and os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD")
            )
        elif channel_type == HILChannelType.WEBHOOK:
            return True  # Webhooks don't require configuration
        elif channel_type == HILChannelType.IN_APP:
            return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SECRET_KEY"))
        else:
            return False

    def get_available_channels(self) -> List[HILChannelType]:
        """Get list of available channel types."""
        return [
            channel_type
            for channel_type in self.integrations.keys()
            if self.is_channel_available(channel_type)
        ]
