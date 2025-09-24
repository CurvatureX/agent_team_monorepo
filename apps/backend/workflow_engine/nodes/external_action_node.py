"""
External Action Node Executor.

Handles external integrations like Slack, webhooks, email, etc.
This file has been refactored to use modular external action handlers.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
from shared.models.node_enums import ExternalActionSubtype, NodeType

from .base import BaseNodeExecutor, ExecutionStatus, NodeExecutionContext, NodeExecutionResult
from .external_actions import (
    GitHubExternalAction,
    GoogleCalendarExternalAction,
    NotionExternalAction,
    SlackExternalAction,
)
from .factory import NodeExecutorFactory

logger = logging.getLogger(__name__)


@NodeExecutorFactory.register(NodeType.EXTERNAL_ACTION.value)
class ExternalActionNodeExecutor(BaseNodeExecutor):
    """Executor for external action nodes (Slack, webhooks, email, etc.)."""

    def __init__(self, node_type: str = NodeType.EXTERNAL_ACTION.value, subtype: str = None):
        super().__init__(node_type, subtype)
        # Initialize external action handlers
        self.external_actions = {
            "slack": SlackExternalAction(),
            "github": GitHubExternalAction(),
            "google": GoogleCalendarExternalAction(),
            "notion": NotionExternalAction(),
        }

    async def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute external action node using modular handlers."""
        # Basic debug logging
        print(f"🔥 EXTERNAL ACTION EXECUTE CALLED: node_id={context.node_id}")

        try:
            integration_type = self.subtype or context.get_parameter(
                "integration_type", ExternalActionSubtype.SLACK.value
            )
            operation = context.get_parameter("operation", "send_message")

            print(f"🔥 INTEGRATION TYPE: {integration_type}, OPERATION: {operation}")

            self.log_execution(
                context, f"Executing external action: {integration_type}/{operation}"
            )

        except Exception as e:
            print(f"🔥 ERROR IN EXTERNAL ACTION SETUP: {e}")
            raise

        try:
            # Map integration type to handler
            handler_key = self._get_handler_key(integration_type)

            if handler_key in self.external_actions:
                # Use modular external action handler
                handler = self.external_actions[handler_key]
                return await handler.handle_operation(context, operation)
            elif integration_type.upper() in [ExternalActionSubtype.WEBHOOK.value, "HTTP"]:
                # Keep webhook handling in main file (not OAuth-based)
                return await self._handle_webhook_action(context, operation)
            elif integration_type.upper() == ExternalActionSubtype.EMAIL.value:
                # Keep email handling in main file (SMTP-based)
                return await self._handle_email_action(context, operation)
            else:
                # Return error for unsupported integrations instead of mock
                return NodeExecutionResult(
                    status=ExecutionStatus.ERROR,
                    error_message=f"Unsupported integration type: {integration_type}",
                    error_details={
                        "integration_type": integration_type,
                        "operation": operation,
                        "supported_integrations": [
                            "slack",
                            "github",
                            "google_calendar",
                            "notion",
                            "webhook",
                            "email",
                        ],
                        "solution": f"Use one of the supported integration types or check if '{integration_type}' is properly configured",
                    },
                    metadata={
                        "node_type": "external_action",
                        "integration": integration_type,
                        "operation": operation,
                    },
                )

        except Exception as e:
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=f"External action failed: {str(e)}",
                error_details={"integration_type": integration_type, "operation": operation},
            )

    def _get_handler_key(self, integration_type: str) -> str:
        """Map integration type to handler key."""
        integration_upper = integration_type.upper()

        if integration_upper in [ExternalActionSubtype.SLACK.value, "SLACK_MESSAGE"]:
            return "slack"
        elif integration_upper in ["GITHUB", "GITHUB_ACTION"]:
            return "github"
        elif integration_upper in ["GOOGLE_CALENDAR", "GOOGLE", "CALENDAR"]:
            return "google"
        elif integration_upper in ["NOTION", "NOTION_ACTION"]:
            return "notion"
        else:
            return integration_type.lower()

    async def _handle_webhook_action(
        self, context: NodeExecutionContext, operation: str
    ) -> NodeExecutionResult:
        """Handle webhook/HTTP actions."""
        try:
            # Get webhook URL
            webhook_url = context.get_parameter("webhook_url") or context.get_parameter("url")
            if not webhook_url:
                return NodeExecutionResult(
                    status=ExecutionStatus.ERROR,
                    error_message="Webhook URL is required for webhook action",
                )

            # Get HTTP method
            method = context.get_parameter("method", "POST").upper()

            # Get payload data
            payload = (
                context.get_parameter("payload")
                or context.input_data
                or {"message": "Hello from workflow!"}
            )

            # Get headers
            headers = context.get_parameter("headers", {})
            if not isinstance(headers, dict):
                headers = {}

            # Set default content type if not specified
            if "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"

            self.log_execution(context, f"Sending {method} request to {webhook_url}")

            async with httpx.AsyncClient() as client:
                if method == "GET":
                    response = await client.get(webhook_url, headers=headers, timeout=30.0)
                elif method == "POST":
                    response = await client.post(
                        webhook_url, headers=headers, json=payload, timeout=30.0
                    )
                elif method == "PUT":
                    response = await client.put(
                        webhook_url, headers=headers, json=payload, timeout=30.0
                    )
                elif method == "DELETE":
                    response = await client.delete(webhook_url, headers=headers, timeout=30.0)
                else:
                    return NodeExecutionResult(
                        status=ExecutionStatus.ERROR,
                        error_message=f"Unsupported HTTP method: {method}",
                    )

            self.log_execution(context, f"✅ Webhook response: {response.status_code}")

            # Try to parse JSON response, fallback to text
            try:
                response_data = response.json()
            except:
                response_data = response.text

            return NodeExecutionResult(
                status=ExecutionStatus.SUCCESS,
                output_data={
                    "integration_type": "webhook",
                    "operation": operation,
                    "method": method,
                    "url": webhook_url,
                    "status_code": response.status_code,
                    "response_data": response_data,
                    "headers": dict(response.headers),
                    "timestamp": datetime.now().isoformat(),
                },
            )

        except Exception as e:
            self.log_execution(context, f"Webhook action failed: {str(e)}", "ERROR")
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR, error_message=f"Webhook request failed: {str(e)}"
            )

    async def _handle_email_action(
        self, context: NodeExecutionContext, operation: str
    ) -> NodeExecutionResult:
        """Handle email actions."""
        import os
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        try:
            # Get email configuration from environment or parameters
            smtp_server = os.getenv("SMTP_SERVER") or context.get_parameter("smtp_server")
            smtp_port = (
                int(os.getenv("SMTP_PORT", "587"))
                if os.getenv("SMTP_PORT")
                else context.get_parameter("smtp_port", 587)
            )
            smtp_user = os.getenv("SMTP_USER") or context.get_parameter("smtp_user")
            smtp_password = os.getenv("SMTP_PASSWORD") or context.get_parameter("smtp_password")

            # Get email details
            to_email = (
                context.get_parameter("to_email")
                or context.get_parameter("recipient")
                or context.get_parameter("to")  # Also support "to" parameter
            )
            from_email = smtp_user or context.get_parameter("from_email", "noreply@workflow.com")
            subject = context.get_parameter("subject", "Workflow Notification")

            # Get message content
            body = (
                context.input_data.get("response")
                or context.input_data.get("message")  # From AI agent
                or context.get_parameter("body")  # From trigger
                or "Hello from workflow!"  # From node config  # Default fallback
            )

            if not to_email:
                return NodeExecutionResult(
                    status=ExecutionStatus.ERROR,
                    error_message="Recipient email address is required",
                )

            if smtp_server and smtp_user and smtp_password:
                # Real email sending
                self.log_execution(context, f"Sending email to {to_email}: {subject}")

                # Create message
                msg = MIMEMultipart()
                msg["From"] = from_email
                msg["To"] = to_email
                msg["Subject"] = subject

                # Attach body
                msg.attach(MIMEText(body, "plain"))

                # Send email
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    self._send_email_sync,
                    smtp_server,
                    smtp_port,
                    smtp_user,
                    smtp_password,
                    msg,
                )

                self.log_execution(context, f"✅ Email sent successfully to {to_email}")

                return NodeExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    output_data={
                        "integration_type": "email",
                        "operation": operation,
                        "to_email": to_email,
                        "from_email": from_email,
                        "subject": subject,
                        "body": body,
                        "timestamp": datetime.now().isoformat(),
                        "real_email_sent": True,
                    },
                )
            else:
                # No SMTP configuration available - report error instead of mock mode
                error_msg = "❌ No email SMTP configuration found. Please configure SMTP settings in environment variables."
                self.log_execution(context, error_msg, "ERROR")

                return NodeExecutionResult(
                    status=ExecutionStatus.ERROR,
                    error_message=error_msg,
                    error_details={
                        "integration": "email",
                        "operation": operation,
                        "to_email": to_email,
                        "reason": "missing_smtp_configuration",
                        "solution": "Configure SMTP_SERVER, SMTP_PORT, SMTP_USER, and SMTP_PASSWORD environment variables",
                    },
                    metadata={
                        "node_type": "external_action",
                        "integration": "email",
                        "operation": operation,
                    },
                )

        except Exception as e:
            self.log_execution(context, f"Email action failed: {str(e)}", "ERROR")
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR, error_message=f"Email sending failed: {str(e)}"
            )

    def _send_email_sync(
        self, smtp_server: str, smtp_port: int, smtp_user: str, smtp_password: str, msg
    ):
        """Synchronous email sending function."""
        import smtplib

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        text = msg.as_string()
        server.sendmail(msg["From"], msg["To"], text)
        server.quit()

    def validate_parameters(self, context: NodeExecutionContext) -> tuple[bool, str]:
        """Validate external action node parameters."""
        integration_type = self.subtype or context.get_parameter(
            "integration_type", ExternalActionSubtype.SLACK.value
        )

        # Basic validation for different integration types
        if integration_type.upper() in [ExternalActionSubtype.SLACK.value, "SLACK_MESSAGE"]:
            # For Slack, we have a fallback to "#general" so validation is permissive
            # This matches the execution behavior which provides a default channel
            pass
        elif integration_type.upper() == ExternalActionSubtype.WEBHOOK.value:
            # For webhooks, we need a URL
            webhook_url = context.get_parameter("webhook_url") or context.get_parameter("url")
            if not webhook_url:
                return False, "Webhook integration requires 'webhook_url' or 'url' parameter"
        elif integration_type.upper() == ExternalActionSubtype.EMAIL.value:
            # For email, we need a recipient
            to_email = (
                context.get_parameter("to_email")
                or context.get_parameter("recipient")
                or context.get_parameter("to")
            )
            if not to_email:
                return (
                    False,
                    "Email integration requires 'to_email', 'recipient', or 'to' parameter",
                )

        # For now, be permissive and allow most configurations
        return True, ""
