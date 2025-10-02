"""
Human-in-the-Loop Service for workflow_engine_v2.

Handles HIL interaction lifecycle including response message sending and
advanced classification features.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models.human_in_loop import HILChannelType, HILInputData, HILInteractionType, HILStatus
from workflow_engine_v2.services.hil_response_classifier import (
    ClassificationResult,
    HILResponseClassifierV2,
)
from workflow_engine_v2.services.oauth2_service import OAuth2ServiceV2

logger = logging.getLogger(__name__)


class HILWorkflowServiceV2:
    """Service for managing complete HIL workflow lifecycle with advanced features."""

    def __init__(self):
        self.oauth_integration_service = OAuth2ServiceV2()
        self.hil_response_classifier = HILResponseClassifierV2()

        # Initialize Supabase client for interaction storage
        import os

        from supabase import Client, create_client

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

        if supabase_url and supabase_key:
            self._supabase: Client = create_client(supabase_url, supabase_key)
            logger.info("HIL Service V2: Initialized with Supabase database storage")
        else:
            self._supabase = None
            logger.warning(
                "HIL Service V2: No Supabase credentials found, interactions will not be persisted"
            )

        logger.info(
            "HIL Service V2: Initialized with OAuth integration and response classification capabilities"
        )

    async def handle_hil_response(
        self,
        hil_interaction_id: str,
        human_response_data: Dict[str, Any],
        workflow_node_parameters: Dict[str, Any],
        workflow_execution_context: Dict[str, Any] = None,
    ) -> bool:
        """
        Handle HIL response and send appropriate response messages.

        Args:
            hil_interaction_id: HIL interaction identifier
            human_response_data: Response from human (approved/rejected/timeout/etc)
            workflow_node_parameters: Node parameters from workflow definition (includes response messages)
            workflow_execution_context: Additional workflow context for template variables

        Returns:
            bool: Success status of response handling
        """
        try:
            # Determine human response type from response data
            human_response_type = self._determine_response_type(human_response_data)

            # Get appropriate response message template based on response type
            response_message_template = self._get_response_message_template(
                human_response_type, workflow_node_parameters
            )

            if not response_message_template:
                logger.info(
                    f"No response message template for {human_response_type} - skipping message"
                )
                return True

            # Prepare template context data for message rendering
            message_template_context = self._prepare_template_context(
                human_response_data, workflow_node_parameters, workflow_execution_context or {}
            )

            # Send response message through appropriate communication channel
            message_send_success = await self._send_response_message(
                human_response_type,
                response_message_template,
                message_template_context,
                workflow_node_parameters,
            )

            if message_send_success:
                logger.info(
                    f"HIL response message sent successfully for interaction {hil_interaction_id}"
                )
            else:
                logger.warning(
                    f"Failed to send HIL response message for interaction {hil_interaction_id}"
                )

            return message_send_success

        except Exception as hil_handling_error:
            logger.error(
                f"Error handling HIL response for {hil_interaction_id}: {hil_handling_error}",
                exc_info=True,
            )
            return False

    async def classify_webhook_response(
        self, hil_interaction_data: Dict[str, Any], incoming_webhook_payload: Dict[str, Any]
    ) -> ClassificationResult:
        """
        Classify webhook response relevance to HIL interaction.

        Args:
            hil_interaction_data: HIL interaction data containing context and metadata
            incoming_webhook_payload: Webhook response payload to classify

        Returns:
            ClassificationResult with relevance assessment and confidence score
        """
        return await self.hil_response_classifier.classify_response_relevance(
            hil_interaction_data, incoming_webhook_payload
        )

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
        elif response_data.get("timeout") is True:
            return "timeout"
        elif "escalated" in response_data:
            return "escalated"
        else:
            return "completed"

    def _get_response_message_template(
        self, response_type: str, node_parameters: Dict[str, Any]
    ) -> Optional[str]:
        """Get response message template for the given response type."""
        # Look for response-specific templates in node parameters
        response_templates = node_parameters.get("response_messages", {})

        if response_type in response_templates:
            return response_templates[response_type]

        # Fallback to generic messages
        fallback_templates = {
            "approved": "✅ Your request has been approved and will proceed.",
            "rejected": "❌ Your request has been rejected.",
            "timeout": "⏰ Your request has timed out and will be processed automatically.",
            "escalated": "🔺 Your request has been escalated for further review.",
            "completed": "✅ Your request has been completed.",
        }

        return fallback_templates.get(response_type)

    def _prepare_template_context(
        self,
        response_data: Dict[str, Any],
        node_parameters: Dict[str, Any],
        workflow_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Prepare template context for message rendering."""
        context = {
            "response": response_data,
            "parameters": node_parameters,
            "workflow": workflow_context,
            "timestamp": datetime.now().isoformat(),
            "interaction_id": response_data.get("interaction_id", ""),
        }

        # Add specific response fields to top level for easy access
        for key in ["approved", "rejected", "timeout", "escalated", "reason", "feedback"]:
            if key in response_data:
                context[key] = response_data[key]

        return context

    async def _send_response_message(
        self,
        response_type: str,
        message_template: str,
        context: Dict[str, Any],
        node_parameters: Dict[str, Any],
    ) -> bool:
        """Send response message through appropriate channel."""
        try:
            # Get channel configuration
            channel_type = node_parameters.get("channel_type", "slack")
            channel_config = node_parameters.get("channel_config", {})

            # Render message template with context
            rendered_message = self._render_template(message_template, context)

            if channel_type.lower() == "slack":
                return await self._send_slack_message(rendered_message, channel_config, context)
            elif channel_type.lower() == "email":
                return await self._send_email_message(rendered_message, channel_config, context)
            else:
                logger.warning(f"Unsupported channel type for HIL response: {channel_type}")
                return False

        except Exception as e:
            logger.error(f"Error sending HIL response message: {e}")
            return False

    async def _send_slack_message(
        self, message: str, channel_config: Dict[str, Any], context: Dict[str, Any]
    ) -> bool:
        """Send message via Slack."""
        try:
            # Get user ID from context for OAuth token lookup
            user_id = context.get("workflow", {}).get("user_id") or context.get("user_id")

            if not user_id:
                logger.error("No user_id found for Slack OAuth token lookup")
                return False

            # Get Slack OAuth token
            slack_token = await self.oauth_service.get_valid_token(user_id, "slack")
            if not slack_token:
                logger.error(f"No valid Slack token for user {user_id}")
                return False

            # Get channel from config
            channel = channel_config.get("channel", "#general")

            # Send message using Slack API
            import httpx

            headers = {
                "Authorization": f"Bearer {slack_token}",
                "Content-Type": "application/json",
            }

            payload = {
                "channel": channel,
                "text": message,
                "username": "Workflow Bot",
                "icon_emoji": ":robot_face:",
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
                logger.info("HIL response message sent via Slack successfully")
                return True
            else:
                logger.error(f"Slack API error: {result.get('error', 'unknown')}")
                return False

        except Exception as e:
            logger.error(f"Error sending Slack HIL response: {e}")
            return False

    async def _send_email_message(
        self, message: str, channel_config: Dict[str, Any], context: Dict[str, Any]
    ) -> bool:
        """Send message via email."""
        try:
            # Email sending logic would go here
            # For now, just log the message
            logger.info(f"HIL response email (not implemented): {message}")
            return True

        except Exception as e:
            logger.error(f"Error sending email HIL response: {e}")
            return False

    def _render_template(self, template: str, context: Dict[str, Any]) -> str:
        """Render message template with context variables."""
        try:
            # Simple template rendering - replace {{variable}} with context values
            rendered = template
            for key, value in context.items():
                placeholder = f"{{{{{key}}}}}"
                if placeholder in rendered:
                    rendered = rendered.replace(placeholder, str(value))

            return rendered

        except Exception as e:
            logger.warning(f"Template rendering error: {e}")
            return template  # Return original template if rendering fails

    async def create_hil_interaction(
        self,
        workflow_id: str,
        node_id: str,
        execution_id: str,
        interaction_type: HILInteractionType,
        channel_type: HILChannelType,
        request_data: HILInputData,
        user_id: str,
        priority: str = "normal",
        timeout_seconds: Optional[int] = None,
    ) -> str:
        """
        Create a new HIL interaction.

        Returns:
            str: Interaction ID
        """
        # Store HIL interaction in database
        import uuid
        from datetime import datetime

        interaction_id = str(uuid.uuid4())

        if self._supabase:
            try:
                interaction_data = {
                    "id": interaction_id,
                    "workflow_id": workflow_id,
                    "execution_id": execution_id,
                    "node_id": node_id,
                    "user_id": user_id,
                    "status": "pending",
                    "interaction_type": interaction_type.value
                    if hasattr(interaction_type, "value")
                    else str(interaction_type),
                    "channel_type": channel_type.value
                    if hasattr(channel_type, "value")
                    else str(channel_type),
                    "input_data": input_data.dict() if hasattr(input_data, "dict") else input_data,
                    "timeout_seconds": timeout_seconds,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                }

                result = self._supabase.table("hil_interactions").insert(interaction_data).execute()

                if not result.data:
                    logger.error(f"Failed to store HIL interaction {interaction_id} in database")
                else:
                    logger.info(
                        f"Created HIL interaction {interaction_id} for workflow {workflow_id} in database"
                    )

            except Exception as e:
                logger.error(f"Error storing HIL interaction {interaction_id}: {str(e)}")
        else:
            logger.warning(
                f"Created HIL interaction {interaction_id} for workflow {workflow_id} (not persisted)"
            )

        return interaction_id

    async def get_pending_interactions(
        self, user_id: Optional[str] = None, workflow_id: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get list of pending HIL interactions."""
        # This would typically query a database
        # For now, return empty list
        return []

    async def resolve_interaction(
        self, interaction_id: str, response_data: Dict[str, Any], resolved_by: str
    ) -> bool:
        """Resolve an HIL interaction with response data."""
        try:
            # This would typically update the database record
            logger.info(f"Resolved HIL interaction {interaction_id} by {resolved_by}")
            return True
        except Exception as e:
            logger.error(f"Error resolving HIL interaction {interaction_id}: {e}")
            return False

    async def timeout_expired_interactions(
        self, timeout_threshold_seconds: int = 3600
    ) -> List[str]:
        """Find and handle expired HIL interactions."""
        try:
            # This would typically query database for expired interactions
            # For now, return empty list
            expired_interactions = []

            for interaction_id in expired_interactions:
                await self.handle_hil_response(
                    interaction_id, {"timeout": True, "response_type": "timeout"}, {}, {}
                )

            return expired_interactions
        except Exception as e:
            logger.error(f"Error processing expired HIL interactions: {e}")
            return []


__all__ = ["HILWorkflowServiceV2"]
