"""
Slack external action for workflow_engine_v2.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import httpx

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models import ExecutionStatus, NodeExecutionResult
from workflow_engine_v2.core.context import NodeExecutionContext

from .base_external_action import BaseExternalAction


class SlackExternalAction(BaseExternalAction):
    """Slack external action handler for workflow_engine_v2."""

    def __init__(self):
        super().__init__("slack")

    async def handle_operation(
        self, context: NodeExecutionContext, operation: str
    ) -> NodeExecutionResult:
        """Handle Slack-specific operations."""
        try:
            # Get Slack OAuth authentication token from oauth_tokens table
            slack_oauth_token = await self.get_oauth_token(context)

            if not slack_oauth_token:
                authentication_error_message = "❌ No Slack authentication token found. Please connect your Slack account in integrations settings."
                self.log_execution(context, authentication_error_message, "ERROR")
                return self.create_error_result(authentication_error_message, operation)

            # Route to appropriate Slack operation handler
            if operation.lower() in ["send_message", "send-message"]:
                return await self._send_message(context, slack_oauth_token)
            elif operation.lower() in ["get_channels", "list_channels"]:
                return await self._list_channels(context, slack_oauth_token)
            elif operation.lower() in ["get_users", "list_users"]:
                return await self._list_users(context, slack_oauth_token)
            else:
                # Default fallback: send message
                return await self._send_message(context, slack_oauth_token)

        except Exception as e:
            self.log_execution(context, f"Slack action failed: {str(e)}", "ERROR")
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=f"Slack action failed: {str(e)}",
                error_details={"integration_type": "slack", "operation": operation},
            )

    async def _send_message(
        self, context: NodeExecutionContext, slack_oauth_token: str
    ) -> NodeExecutionResult:
        """Send a Slack message."""
        # Extract message content from input data or node configurations
        slack_message_content = (
            context.input_data.get("text")
            or context.input_data.get("response")
            or context.input_data.get("message")
            or context.node.configurations.get("message")
            or "Hello from workflow!"
        )

        # Determine target channel from configurations (workflow-defined) or input data (trigger-based)
        target_channel_from_input = context.input_data.get("channel") or context.input_data.get(
            "channel_name"
        )
        channel_config = context.node.configurations.get("channel")

        # Extract actual value from configuration (handle both dict and string)
        if isinstance(channel_config, dict):
            target_channel_from_config = channel_config.get("default") or channel_config.get(
                "value"
            )
        elif isinstance(channel_config, str):
            target_channel_from_config = channel_config
        else:
            target_channel_from_config = None

        # Log channel resolution sources for debugging
        self.log_execution(
            context,
            f"🔍 Channel resolution - input: '{target_channel_from_input}', config: '{target_channel_from_config}'",
        )

        slack_target_channel = target_channel_from_config or target_channel_from_input or "#general"

        # Format channel name properly (ensure # prefix or channel ID format)
        if isinstance(slack_target_channel, str):
            if not slack_target_channel.startswith("#") and not slack_target_channel.startswith(
                "C"
            ):
                slack_target_channel = f"#{slack_target_channel}"
        else:
            slack_target_channel = "#general"

        self.log_execution(
            context,
            f"Sending Slack message to {slack_target_channel}: {slack_message_content[:100]}...",
        )

        # Prepare Slack API request headers and payload
        slack_api_headers = {
            "Authorization": f"Bearer {slack_oauth_token}",
            "Content-Type": "application/json",
        }

        slack_message_payload = {
            "channel": slack_target_channel,
            "text": slack_message_content,
            "username": context.node.configurations.get("username", "Workflow Bot"),
            "icon_emoji": context.node.configurations.get("icon_emoji", ":robot_face:"),
        }

        async with httpx.AsyncClient() as slack_http_client:
            slack_api_response = await slack_http_client.post(
                "https://slack.com/api/chat.postMessage",
                headers=slack_api_headers,
                json=slack_message_payload,
                timeout=10.0,
            )

        slack_response_data = slack_api_response.json()

        # Log the full Slack API response for debugging
        self.log_execution(context, f"🔍 Slack API response: {slack_response_data}")

        if slack_response_data.get("ok", False):
            self.log_execution(
                context, f"✅ Slack message sent successfully to {slack_target_channel}"
            )
            return self.create_success_result(
                "send_message",
                {
                    "success": True,
                    "message_timestamp": slack_response_data.get("ts"),
                    "channel_id": slack_response_data.get("channel"),
                    "message_details": slack_response_data.get("message", {}),
                    "channel_name": slack_target_channel,
                    "message_content": slack_message_content,
                    "slack_api_response": slack_response_data,
                },
            )
        else:
            slack_api_error = slack_response_data.get("error", "unknown_error")
            self.log_execution(context, f"❌ Slack API error: {slack_api_error}", "ERROR")
            self.log_execution(context, f"❌ Full Slack response: {slack_response_data}", "ERROR")
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=f"Slack API error: {slack_api_error}",
                error_details={
                    "slack_response": slack_response_data,
                    "channel": slack_target_channel,
                },
            )

    async def _list_channels(
        self, context: NodeExecutionContext, token: str
    ) -> NodeExecutionResult:
        """List Slack channels."""
        self.log_execution(context, "Listing Slack channels")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://slack.com/api/conversations.list",
                headers=headers,
                params={"types": "public_channel,private_channel"},
                timeout=10.0,
            )

        result = response.json()

        if result.get("ok", False):
            channels = result.get("channels", [])
            self.log_execution(context, f"✅ Retrieved {len(channels)} Slack channels")

            channels_data = []
            for channel in channels:
                channels_data.append(
                    {
                        "id": channel.get("id"),
                        "name": channel.get("name"),
                        "is_private": channel.get("is_private", False),
                        "is_member": channel.get("is_member", False),
                        "topic": channel.get("topic", {}).get("value", ""),
                        "purpose": channel.get("purpose", {}).get("value", ""),
                    }
                )

            return self.create_success_result(
                "list_channels",
                {
                    "channels_count": len(channels_data),
                    "channels": channels_data,
                },
            )
        else:
            error = result.get("error", "unknown_error")
            self.log_execution(context, f"❌ Slack API error: {error}", "ERROR")
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=f"Slack API error: {error}",
                error_details={"slack_response": result},
            )

    async def _list_users(self, context: NodeExecutionContext, token: str) -> NodeExecutionResult:
        """List Slack users."""
        self.log_execution(context, "Listing Slack users")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://slack.com/api/users.list",
                headers=headers,
                timeout=10.0,
            )

        result = response.json()

        if result.get("ok", False):
            users = result.get("members", [])
            self.log_execution(context, f"✅ Retrieved {len(users)} Slack users")

            users_data = []
            for user in users:
                if not user.get("deleted", False) and not user.get("is_bot", False):
                    users_data.append(
                        {
                            "id": user.get("id"),
                            "name": user.get("name"),
                            "real_name": user.get("real_name"),
                            "display_name": user.get("profile", {}).get("display_name", ""),
                            "email": user.get("profile", {}).get("email", ""),
                            "is_admin": user.get("is_admin", False),
                        }
                    )

            return self.create_success_result(
                "list_users",
                {
                    "users_count": len(users_data),
                    "users": users_data,
                },
            )
        else:
            error = result.get("error", "unknown_error")
            self.log_execution(context, f"❌ Slack API error: {error}", "ERROR")
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=f"Slack API error: {error}",
                error_details={"slack_response": result},
            )


__all__ = ["SlackExternalAction"]
