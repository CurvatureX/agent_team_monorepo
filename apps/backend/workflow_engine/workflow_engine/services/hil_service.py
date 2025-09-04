"""
Human-in-the-Loop Service - Complete HIL workflow management.

Handles HIL interaction lifecycle including response message sending using
node specifications with integrated response messaging parameters.
"""

import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# Add shared path for Slack SDK
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from shared.models.human_in_loop import HILChannelType, HILInputData, HILInteractionType, HILStatus
from shared.sdks.slack_sdk import SlackAPIError, SlackWebClient

logger = logging.getLogger(__name__)


class HILWorkflowService:
    """Service for managing complete HIL workflow lifecycle with response messaging."""

    def __init__(self):
        self.slack_client = None
        self._initialize_integrations()

    def _initialize_integrations(self):
        """Initialize external integrations for message sending."""
        # Initialize Slack client
        try:
            slack_token = os.getenv("DEFAULT_SLACK_BOT_TOKEN")
            if slack_token:
                self.slack_client = SlackWebClient(slack_token)
                self.slack_client.auth_test()  # Test authentication
                logger.info("HIL Service: Slack integration initialized")
        except Exception as e:
            logger.warning(f"HIL Service: Slack initialization failed: {e}")
            self.slack_client = None

    def handle_hil_response(
        self,
        interaction_id: str,
        response_data: Dict[str, Any],
        node_parameters: Dict[str, Any],
        workflow_context: Dict[str, Any] = None,
    ) -> bool:
        """
        Handle HIL response and send appropriate response messages.

        Args:
            interaction_id: HIL interaction ID
            response_data: Response from human (approved/rejected/timeout/etc)
            node_parameters: Node parameters from workflow definition (includes response messages)
            workflow_context: Additional workflow context for template variables

        Returns:
            bool: Success status of response handling
        """
        try:
            # Determine response type from response data
            response_type = self._determine_response_type(response_data)

            # Get response message template based on type
            message_template = self._get_response_message_template(response_type, node_parameters)

            if not message_template:
                logger.info(f"No response message template for {response_type} - skipping message")
                return True

            # Prepare template context data
            template_context = self._prepare_template_context(
                response_data, node_parameters, workflow_context or {}
            )

            # Send response message through appropriate channel
            success = self._send_response_message(
                response_type, message_template, template_context, node_parameters
            )

            if success:
                logger.info(
                    f"HIL response message sent successfully for interaction {interaction_id}"
                )
            else:
                logger.warning(
                    f"Failed to send HIL response message for interaction {interaction_id}"
                )

            return success

        except Exception as e:
            logger.error(f"Error handling HIL response for {interaction_id}: {e}", exc_info=True)
            return False

    def _determine_response_type(self, response_data: Dict[str, Any]) -> str:
        """Determine response type from response data."""
        # Check for explicit response type
        if "response_type" in response_data:
            return response_data["response_type"]

        # Infer from response data
        if response_data.get("approved") is True:
            return "approved"
        elif response_data.get("approved") is False:
            return "rejected"
        elif response_data.get("timeout"):
            return "timeout"
        elif response_data.get("completed"):
            return "completed"
        else:
            return "completed"  # Default

    def _get_response_message_template(
        self, response_type: str, node_parameters: Dict[str, Any]
    ) -> Optional[str]:
        """Get response message template based on type and node parameters."""
        # Map response types to parameter names
        template_map = {
            "approved": "approved_message",
            "rejected": "rejected_message",
            "timeout": "timeout_message",
            "completed": "approved_message",  # Default to approved for completed
        }

        template_param = template_map.get(response_type)
        if template_param:
            return node_parameters.get(template_param)

        return None

    def _prepare_template_context(
        self,
        response_data: Dict[str, Any],
        node_parameters: Dict[str, Any],
        workflow_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Prepare context data for message template processing."""
        # Merge all context data
        context = {
            "response": response_data,
            "data": workflow_context.get("data", {}),
            "workflow": workflow_context.get("workflow", {}),
            "responder": response_data.get("responder", {}),
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Add common workflow variables
        if "workflow_id" in workflow_context:
            context["workflow"]["id"] = workflow_context["workflow_id"]

        return context

    def _send_response_message(
        self,
        response_type: str,
        message_template: str,
        template_context: Dict[str, Any],
        node_parameters: Dict[str, Any],
    ) -> bool:
        """Send response message through appropriate channel."""
        try:
            # Check if response sending is enabled
            send_responses = node_parameters.get("send_responses_to_channel", False)
            if not send_responses:
                logger.debug("Response message sending disabled in node parameters")
                return True

            # Process message template
            processed_message = self._process_message_template(message_template, template_context)

            # Determine target channel/recipients
            channel_config = self._get_response_channel_config(node_parameters)

            # Send via appropriate channel
            if channel_config.get("type") == "slack":
                return self._send_slack_response_message(processed_message, channel_config)
            elif channel_config.get("type") == "email":
                return self._send_email_response_message(processed_message, channel_config)
            elif channel_config.get("type") == "webhook":
                return self._send_webhook_response_message(processed_message, channel_config)
            else:
                logger.warning(f"Unsupported response channel type: {channel_config.get('type')}")
                return False

        except Exception as e:
            logger.error(f"Error sending response message: {e}", exc_info=True)
            return False

    def _get_response_channel_config(self, node_parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get response channel configuration from node parameters."""
        # Check for alternative response targets
        if node_parameters.get("response_channel"):
            return {
                "type": "slack",
                "channel": node_parameters["response_channel"],
            }
        elif node_parameters.get("response_recipients"):
            return {
                "type": "email",
                "recipients": node_parameters["response_recipients"],
            }
        elif node_parameters.get("response_user_ids"):
            return {
                "type": "app",
                "user_ids": node_parameters["response_user_ids"],
            }
        else:
            # Use original channel configuration
            # This would come from the original HIL request
            return {
                "type": "slack",
                "channel": "#general",  # Default fallback
            }

    def _send_slack_response_message(self, message: str, channel_config: Dict[str, Any]) -> bool:
        """Send response message via Slack."""
        if not self.slack_client:
            logger.warning("Slack client not available for response message")
            return False

        try:
            channel = channel_config.get("channel", "#general")
            response = self.slack_client.send_message(channel=channel, text=message)
            return response.get("ok", False)

        except SlackAPIError as e:
            logger.error(f"Slack API error sending response message: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending Slack response message: {e}")
            return False

    def _send_email_response_message(self, message: str, channel_config: Dict[str, Any]) -> bool:
        """Send response message via email."""
        recipients = channel_config.get("recipients", [])

        try:
            # Use SMTP to send email
            import os
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            # Get SMTP configuration from environment
            smtp_server = os.getenv("SMTP_SERVER")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_username = os.getenv("SMTP_USERNAME")
            smtp_password = os.getenv("SMTP_PASSWORD")
            from_email = os.getenv("SMTP_FROM_EMAIL", smtp_username)

            if not all([smtp_server, smtp_username, smtp_password]):
                logger.warning(
                    f"SMTP not configured - cannot send email to {len(recipients)} recipients"
                )
                return False

            # Create and send email
            msg = MIMEMultipart()
            msg["From"] = from_email
            msg["To"] = ", ".join(recipients)
            msg["Subject"] = "Workflow Response Notification"

            # Add HTML body
            html_body = f"""
<html><body>
<h2>🔔 Workflow Notification</h2>
<p>{message}</p>
<hr>
<p><em>Sent from HIL Workflow System at {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</em></p>
</body></html>
            """.strip()

            msg.attach(MIMEText(html_body, "html"))

            # Send via SMTP
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)

            logger.info(f"Email response sent to {len(recipients)} recipients")
            return True

        except Exception as e:
            logger.error(f"Failed to send email response: {e}")
            return False

    def _send_webhook_response_message(self, message: str, channel_config: Dict[str, Any]) -> bool:
        """Send response message via webhook."""
        import httpx

        try:
            webhook_url = channel_config.get("webhook_url")
            if not webhook_url:
                logger.error("No webhook URL provided for response message")
                return False

            payload = {
                "event_type": "workflow_response_notification",
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
            }

            with httpx.Client(timeout=10.0) as client:
                response = client.post(webhook_url, json=payload)
                return response.status_code == 200

        except Exception as e:
            logger.error(f"Error sending webhook response message: {e}")
            return False

    def _process_message_template(self, template: str, context_data: Dict[str, Any]) -> str:
        """Process message template with variable substitution."""
        try:
            import re

            def replace_var(match):
                var_name = match.group(1).strip()
                # Support nested dict access like {{data.event_id}}
                keys = var_name.split(".")
                value = context_data

                try:
                    for key in keys:
                        value = value[key]
                    return str(value)
                except (KeyError, TypeError, AttributeError):
                    return match.group(0)  # Return original if not found

            return re.sub(r"\{\{\s*([^}]+)\s*\}\}", replace_var, template)

        except Exception:
            # If template processing fails, return original message
            return template

    def send_timeout_notification(
        self, interaction_id: str, node_parameters: Dict[str, Any], workflow_context: Dict[str, Any]
    ) -> bool:
        """Send timeout notification when HIL interaction expires."""
        timeout_response = {
            "response_type": "timeout",
            "timeout": True,
            "interaction_id": interaction_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

        return self.handle_hil_response(
            interaction_id, timeout_response, node_parameters, workflow_context
        )

    def get_service_status(self) -> Dict[str, Any]:
        """Get HIL service status and integration health."""
        return {
            "service": "hil_workflow_service",
            "integrations": {
                "slack": self.slack_client is not None,
                "email": bool(os.getenv("SMTP_SERVER") and os.getenv("SMTP_USERNAME")),
                "webhooks": True,  # HTTP client always available
            },
            "status": "healthy",
        }
