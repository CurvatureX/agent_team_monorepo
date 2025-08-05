"""
Notification service for workflow_scheduler
Sends email notifications when triggers are activated
"""

import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

# Add shared path for email_client
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "shared"))

from email_client import EmailMessage, MigaduEmailClient

from ..core.config import settings
from ..models.triggers import ExecutionResult

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications when workflows are triggered"""

    def __init__(self):
        self.target_email = "z1771485029@gmail.com"
        self.email_client: Optional[MigaduEmailClient] = None
        self._initialize_email_client()

    def _initialize_email_client(self):
        """Initialize Migadu email client with configuration"""
        try:
            # Check if we have the required Migadu credentials
            username = settings.smtp_username
            password = settings.smtp_password

            if not username or not password:
                logger.warning(
                    "Migadu credentials not configured - notifications will be logged only"
                )
                logger.info(
                    "To enable email notifications, set SMTP_USERNAME and SMTP_PASSWORD environment variables"
                )
                logger.info(
                    "For Migadu: username should be your full email address (e.g., sender@yourdomain.com)"
                )
                return

            # Create Migadu client
            self.email_client = MigaduEmailClient(
                username=username,
                password=password,
                sender_email=settings.smtp_sender_email or username,
                sender_name=settings.smtp_sender_name or "Workflow Scheduler",
                use_starttls=settings.smtp_use_tls,  # Use TLS setting to determine STARTTLS vs SSL
            )

            # Test connection
            if self.email_client.test_connection():
                connection_method = (
                    "STARTTLS (port 587)" if settings.smtp_use_tls else "SSL (port 465)"
                )
                logger.info(
                    f"📧 Migadu email notification service initialized successfully ({connection_method})"
                )
                logger.info(
                    f"   📤 Sender: {settings.smtp_sender_name or 'Workflow Scheduler'} <{settings.smtp_sender_email or username}>"
                )
                logger.info(f"   📬 Target: {self.target_email}")
            else:
                logger.warning("Migadu connection test failed - notifications will be logged only")
                self.email_client = None

        except Exception as e:
            logger.error(f"Failed to initialize Migadu email client: {e}")
            logger.info(
                "Make sure SMTP_USERNAME is your full Migadu email address and SMTP_PASSWORD is correct"
            )
            self.email_client = None

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
            # Generate notification content
            subject, body = self._generate_notification_content(
                workflow_id, trigger_type, trigger_data
            )

            # Log the trigger event
            logger.info(f"🔔 Trigger notification: {workflow_id} triggered by {trigger_type}")

            # Send email if client is available
            if self.email_client:
                success = await self._send_email_notification(subject, body)
                if success:
                    logger.info(
                        f"📧 Email notification sent successfully for workflow {workflow_id}"
                    )
                    status = "notified_email"
                    message = f"Email notification sent for {trigger_type} trigger"
                else:
                    logger.warning(f"📧 Email notification failed for workflow {workflow_id}")
                    status = "notified_log_only"
                    message = f"Email failed, logged {trigger_type} trigger"
            else:
                logger.info(f"📝 Logged trigger notification for workflow {workflow_id}")
                status = "notified_log_only"
                message = f"Logged {trigger_type} trigger (email not configured)"

            return ExecutionResult(status=status, message=message, trigger_data=trigger_data)

        except Exception as e:
            error_msg = f"Failed to send trigger notification: {str(e)}"
            logger.error(error_msg, exc_info=True)

            return ExecutionResult(
                status="notification_failed", message=error_msg, trigger_data=trigger_data
            )

    def _generate_notification_content(
        self, workflow_id: str, trigger_type: str, trigger_data: Dict[str, Any]
    ) -> tuple[str, str]:
        """Generate email subject and body for the notification"""

        # Clean trigger type for display
        display_trigger_type = trigger_type.replace("TRIGGER_", "").title()

        # Generate subject
        subject = f"🚀 Workflow Triggered: {workflow_id} ({display_trigger_type})"

        # Generate body based on trigger type
        body_lines = [
            f"Hello! 👋",
            f"",
            f"A workflow has been triggered in the workflow scheduler system:",
            f"",
            f"📋 Workflow ID: {workflow_id}",
            f"⚡ Trigger Type: {display_trigger_type}",
            f"🕐 Triggered At: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
            f"",
        ]

        # Add trigger-specific details
        if trigger_type == "TRIGGER_CRON":
            cron_expr = trigger_data.get("cron_expression", "Unknown")
            timezone = trigger_data.get("timezone", "UTC")
            body_lines.extend(
                [
                    f"📅 Cron Expression: {cron_expr}",
                    f"🌍 Timezone: {timezone}",
                ]
            )

        elif trigger_type == "TRIGGER_MANUAL":
            user_id = trigger_data.get("user_id", "Unknown")
            confirmation = trigger_data.get("confirmation", False)
            body_lines.extend(
                [
                    f"👤 Triggered By: {user_id}",
                    f"✅ Confirmation: {'Yes' if confirmation else 'No'}",
                ]
            )

        elif trigger_type == "TRIGGER_WEBHOOK":
            method = trigger_data.get("method", "Unknown")
            path = trigger_data.get("path", "Unknown")
            remote_addr = trigger_data.get("remote_addr", "Unknown")
            body_lines.extend(
                [
                    f"🌐 HTTP Method: {method}",
                    f"🔗 Webhook Path: {path}",
                    f"📍 Remote Address: {remote_addr}",
                ]
            )

        elif trigger_type == "TRIGGER_EMAIL":
            sender = trigger_data.get("sender", "Unknown")
            subject_line = trigger_data.get("subject", "Unknown")
            body_lines.extend(
                [
                    f"📧 Email From: {sender}",
                    f"📝 Email Subject: {subject_line}",
                ]
            )

        elif trigger_type == "TRIGGER_GITHUB":
            event_type = trigger_data.get("event_type", "Unknown")
            repository = trigger_data.get("repository", {}).get("full_name", "Unknown")
            sender = trigger_data.get("sender", {}).get("login", "Unknown")
            body_lines.extend(
                [
                    f"🐙 GitHub Event: {event_type}",
                    f"📚 Repository: {repository}",
                    f"👤 GitHub User: {sender}",
                ]
            )

        body_lines.extend(
            [
                f"",
                f"📊 Trigger Data Summary:",
            ]
        )

        # Add limited trigger data (first 5 keys to avoid overwhelming)
        data_keys = list(trigger_data.keys())[:5]
        for key in data_keys:
            value = str(trigger_data[key])
            if len(value) > 100:
                value = value[:97] + "..."
            body_lines.append(f"   • {key}: {value}")

        if len(trigger_data.keys()) > 5:
            body_lines.append(f"   • ... and {len(trigger_data.keys()) - 5} more fields")

        body_lines.extend(
            [
                f"",
                f"💡 Note: This is a test notification. The actual workflow was not executed.",
                f"",
                f"🔧 System: Workflow Scheduler",
                f"📍 Service: workflow_scheduler",
                f"",
                f"Best regards,",
                f"Workflow Scheduler Team 🤖",
            ]
        )

        body = "\n".join(body_lines)

        return subject, body

    async def _send_email_notification(self, subject: str, body: str) -> bool:
        """Send email notification"""
        try:
            message = EmailMessage(
                subject=subject,
                body=body,
                receiver_email=self.target_email,
                sender_email=None,  # Will use default from config
            )

            # Run sync email sending in a thread-safe way
            import asyncio

            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(None, self.email_client.send_email, message)

            return success

        except Exception as e:
            logger.error(f"Error sending email notification: {e}", exc_info=True)
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Check health of notification service"""
        return {
            "service": "notification_service",
            "email_client_available": self.email_client is not None,
            "target_email": self.target_email,
            "status": "healthy" if self.email_client else "degraded",
        }
