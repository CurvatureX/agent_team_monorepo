"""Human-in-the-Loop service primitives for workflow_engine_v2."""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models.human_in_loop import HILChannelType, HILInteractionType
from workflow_engine_v2.services.hil_response_classifier import (
    ClassificationResult,
    HILResponseClassifierV2,
)
from workflow_engine_v2.services.oauth2_service import OAuth2ServiceV2

logger = logging.getLogger(__name__)


class HILWorkflowServiceV2:
    """Service for managing complete HIL workflow lifecycle with advanced features."""

    def __init__(self):
        self.oauth_service = OAuth2ServiceV2()
        # Backwards compatibility alias for legacy references
        self.oauth_integration_service = self.oauth_service
        self.hil_response_classifier = HILResponseClassifierV2()

        # Initialize Supabase client for interaction storage
        import os

        from supabase import Client, create_client

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

        if supabase_url and supabase_key:
            self._supabase: Optional[Client] = create_client(supabase_url, supabase_key)
            logger.info("HIL Service V2: Initialized with Supabase database storage")
        else:
            self._supabase = None
            logger.warning(
                "HIL Service V2: No Supabase credentials found, interactions will be cached in-memory"
            )

        # Local cache so the engine can operate even without Supabase connectivity
        self._in_memory_store: Dict[str, Dict[str, Any]] = {}
        self._memory_lock = Lock()

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
            "warning": "⏰ Reminder: your approval is still pending and will timeout soon.",
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

    async def create_interaction(
        self,
        interaction_data: Optional[Dict[str, Any]] = None,
        *,
        workflow_id: Optional[str] = None,
        node_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        user_id: Optional[str] = None,
        interaction_type: Optional[Union[HILInteractionType, str]] = None,
        channel_type: Optional[Union[HILChannelType, str]] = None,
        request_data: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[int] = None,
        priority: str = "normal",
    ) -> str:
        """Create and persist a new HIL interaction record."""

        merged: Dict[str, Any] = {}
        if interaction_data:
            merged.update(interaction_data)

        overrides = {
            "workflow_id": workflow_id,
            "node_id": node_id,
            "execution_id": execution_id,
            "user_id": user_id,
            "interaction_type": interaction_type,
            "channel_type": channel_type,
            "request_data": request_data,
            "timeout_seconds": timeout_seconds,
            "priority": priority,
        }
        for key, value in overrides.items():
            if value is not None and merged.get(key) is None:
                merged[key] = value

        if not merged.get("workflow_id"):
            raise ValueError("workflow_id is required for HIL interactions")
        if not merged.get("execution_id"):
            raise ValueError("execution_id is required for HIL interactions")
        if not merged.get("node_id"):
            raise ValueError("node_id is required for HIL interactions")
        if not merged.get("user_id"):
            raise ValueError("user_id is required for HIL interactions")

        # Normalise interaction and channel types
        interaction_value = merged.get("interaction_type") or merged.get("interaction")
        if interaction_value is None:
            interaction_value = HILInteractionType.APPROVAL.value
        interaction_str = (
            interaction_value.value if isinstance(interaction_value, HILInteractionType) else str(interaction_value)
        ).lower()

        channel_value = merged.get("channel_type") or merged.get("channel")
        if channel_value is None:
            channel_value = HILChannelType.SLACK.value
        channel_aliases = {"in_app": HILChannelType.APP.value}
        channel_candidate = (
            channel_value.value if isinstance(channel_value, HILChannelType) else str(channel_value)
        ).lower()
        channel_str = channel_aliases.get(channel_candidate, channel_candidate)

        final_timeout_seconds = merged.get("timeout_seconds")
        if final_timeout_seconds is None:
            final_timeout_seconds = 3600
        try:
            final_timeout_seconds = int(final_timeout_seconds)
        except (TypeError, ValueError):
            raise ValueError("timeout_seconds must be an integer value")
        final_timeout_seconds = max(60, min(86400, final_timeout_seconds))

        now = datetime.utcnow()
        timeout_at = now + timedelta(seconds=final_timeout_seconds)

        request_payload = merged.get("request_data") or {}
        if not request_payload:
            # Backwards compatibility for simplified payloads
            request_payload = {
                "title": merged.get("title") or merged.get("name"),
                "description": merged.get("description"),
                "message": merged.get("message"),
                "approval_options": merged.get("approval_options"),
                "input_fields": merged.get("input_fields"),
                "selection_options": merged.get("selection_options"),
                "timeout_action": merged.get("timeout_action", "fail"),
            }

        interaction_id = merged.get("id") or str(uuid4())

        record = {
            "id": interaction_id,
            "workflow_id": merged["workflow_id"],
            "execution_id": merged["execution_id"],
            "node_id": merged["node_id"],
            "user_id": merged["user_id"],
            "status": "pending",
            "priority": merged.get("priority", "normal"),
            "interaction_type": interaction_str,
            "channel_type": channel_str,
            "request_data": request_payload,
            "timeout_seconds": final_timeout_seconds,
            "timeout_at": timeout_at.isoformat(),
            "warning_sent": False,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        await asyncio.to_thread(self._persist_interaction, record)
        return interaction_id

    def create_interaction_sync(self, **kwargs: Any) -> str:
        """Synchronous wrapper so runners can call the async API from sync code."""

        coro = self.create_interaction(**kwargs)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result()

        new_loop = asyncio.new_event_loop()
        try:
            return new_loop.run_until_complete(coro)
        finally:
            new_loop.close()

    def get_cached_interaction(self, interaction_id: str) -> Optional[Dict[str, Any]]:
        """Return the cached interaction record if stored locally."""

        with self._memory_lock:
            record = self._in_memory_store.get(interaction_id)
            if record:
                return dict(record)
        return None

    def _persist_interaction(self, record: Dict[str, Any]) -> None:
        """Persist record in Supabase if configured and always mirror it in memory."""

        if self._supabase:
            try:
                result = self._supabase.table("hil_interactions").insert(record).execute()
                if not result.data:
                    logger.error(
                        "Failed to store HIL interaction %s in database; falling back to memory cache",
                        record["id"],
                    )
            except Exception as exc:  # pragma: no cover - logging path
                message = str(exc)
                if "priority" in message:
                    fallback_record = dict(record)
                    fallback_record.pop("priority", None)
                    try:
                        result = (
                            self._supabase.table("hil_interactions")
                            .insert(fallback_record)
                            .execute()
                        )
                        if not result.data:
                            logger.error(
                                "Retry without priority still failed for HIL interaction %s",
                                record["id"],
                            )
                        else:
                            record = fallback_record
                            logger.info(
                                "Stored HIL interaction %s without priority column",
                                record["id"],
                            )
                    except Exception as fallback_exc:
                        logger.error(
                            "Error storing HIL interaction %s without priority: %s",
                            record["id"],
                            fallback_exc,
                        )
                else:
                    logger.error("Error storing HIL interaction %s: %s", record["id"], exc)

        with self._memory_lock:
            self._in_memory_store[record["id"]] = dict(record)

    async def send_system_message(
        self,
        interaction: Dict[str, Any],
        message_type: str,
        template_context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send an internal system notification (warning/timeout) for an interaction."""

        template_context = template_context or {}
        channel_type = interaction.get("channel_type", "slack")
        request_data = interaction.get("request_data", {}) or {}
        channel_config = request_data.get("channel_config", {}) or {}

        # Reuse response templates if provided on the node definition
        response_templates = request_data.get("response_messages", {}) or {}
        template = response_templates.get(message_type)

        if not template:
            defaults = {
                "warning": (
                    "⏰ Interaction {interaction_id} will timeout at {timeout_at}. Respond soon to avoid automatic handling."
                ),
                "timeout": (
                    "⛔ Interaction {interaction_id} timed out. Action: {timeout_action_description}"
                ),
            }
            template = defaults.get(
                message_type, "ℹ️ Workflow update for interaction {interaction_id}."
            )

        context = {
            **template_context,
            "interaction_id": interaction.get("id"),
            "workflow_id": interaction.get("workflow_id"),
            "timeout_at": interaction.get("timeout_at"),
        }

        user_id = interaction.get("user_id")
        if user_id:
            context.setdefault("user_id", user_id)
            workflow_ctx = request_data.get("workflow_context") or {}
            context.setdefault("workflow", {"user_id": workflow_ctx.get("user_id", user_id)})

        node_parameters = {
            "channel_type": channel_type,
            "channel_config": channel_config,
        }

        return await self._send_response_message(message_type, template, context, node_parameters)


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
