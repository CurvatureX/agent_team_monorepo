"""
Slack external action for external actions.
"""

from datetime import datetime
from typing import Any, Dict

import httpx

from nodes.base import ExecutionStatus, NodeExecutionContext, NodeExecutionResult

from .base_external_action import BaseExternalAction


class SlackExternalAction(BaseExternalAction):
    """Slack external action handler."""

    def __init__(self):
        super().__init__("slack")

    async def handle_operation(
        self, context: NodeExecutionContext, operation: str
    ) -> NodeExecutionResult:
        """Handle Slack-specific operations."""
        try:
            # Get Slack OAuth token from oauth_tokens table
            slack_token = await self.get_oauth_token(context)

            if not slack_token:
                error_msg = "❌ No Slack authentication token found. Please connect your Slack account in integrations settings."
                self.log_execution(context, error_msg, "ERROR")
                return self.create_error_result(error_msg, operation)

            # Handle different Slack operations
            if operation.lower() in ["send_message", "send-message"]:
                return await self._send_message(context, slack_token)
            elif operation.lower() in ["get_channels", "list_channels"]:
                return await self._list_channels(context, slack_token)
            elif operation.lower() in ["get_users", "list_users"]:
                return await self._list_users(context, slack_token)
            else:
                # Default: send message
                return await self._send_message(context, slack_token)

        except Exception as e:
            self.log_execution(context, f"Slack action failed: {str(e)}", "ERROR")
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=f"Slack action failed: {str(e)}",
                error_details={"integration_type": "slack", "operation": operation},
            )

    async def _send_message(self, context: NodeExecutionContext, token: str) -> NodeExecutionResult:
        """Send a Slack message."""
        # Get message content from AI agent output or input data
        message = (
            context.input_data.get("response")
            or context.input_data.get("message")  # From AI agent
            or context.get_parameter("message")  # From trigger
            or "Hello from workflow!"  # Default fallback
        )

        # Get channel from input data first (dynamic), then parameters (static)
        # This allows trigger data to override node configuration
        channel_from_input_data = context.input_data.get("channel") or context.input_data.get(
            "channel_name"
        )
        channel_from_parameters = context.get_parameter("channel")

        # Log the channel sources for debugging
        self.log_execution(
            context,
            f"🔍 Channel sources - input_data: '{channel_from_input_data}', parameters: '{channel_from_parameters}'",
        )

        channel = (
            channel_from_input_data or channel_from_parameters or "#general"  # Default fallback
        )

        # Format channel name properly
        if not channel.startswith("#") and not channel.startswith("C"):
            channel = f"#{channel}"

        self.log_execution(context, f"Sending Slack message to {channel}: {message[:100]}...")

        # Real Slack API call
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        payload = {
            "channel": channel,
            "text": message,
            "username": context.get_parameter("username", "Workflow Bot"),
            "icon_emoji": context.get_parameter("icon_emoji", ":robot_face:"),
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers=headers,
                json=payload,
                timeout=10.0,
            )

        result = response.json()

        # Log the full Slack API response for debugging
        self.log_execution(context, f"🔍 Slack API response: {result}")

        if result.get("ok", False):
            self.log_execution(context, f"✅ Slack message sent successfully to {channel}")
            return self.create_success_result(
                "send_message",
                {
                    "success": True,
                    "ts": result.get("ts"),
                    "channel": result.get("channel"),
                    "message": result.get("message", {}),
                    "channel_name": channel,
                    "message_sent": message,
                    "slack_response": result,  # Include response for debugging
                },
            )
        else:
            error = result.get("error", "unknown_error")
            self.log_execution(context, f"❌ Slack API error: {error}", "ERROR")
            self.log_execution(context, f"❌ Full Slack response: {result}", "ERROR")
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=f"Slack API error: {error}",
                error_details={"slack_response": result, "channel": channel},
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
