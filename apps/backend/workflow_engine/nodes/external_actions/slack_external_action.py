"""
Slack external action for workflow_engine using Slack SDK.

This implementation uses the shared Slack SDK for all operations,
strictly following the node specification in shared/node_specs/EXTERNAL_ACTION/SLACK.py.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from nodes.base import ExecutionStatus, NodeExecutionContext, NodeExecutionResult

from shared.sdks.slack_sdk.client import SlackWebClient
from shared.sdks.slack_sdk.exceptions import (
    SlackAPIError,
    SlackAuthError,
    SlackChannelNotFoundError,
    SlackRateLimitError,
    SlackUserNotFoundError,
)

from .base_external_action import BaseExternalAction


class SlackExternalAction(BaseExternalAction):
    """
    Slack external action handler using Slack SDK.

    Follows node spec output format:
    - success: boolean
    - message_ts: string (Slack message timestamp)
    - channel_id: string
    - response_data: object (parsed Slack API response)
    - error_message: string
    - api_response: object (raw Slack API response)
    """

    def __init__(self):
        super().__init__("slack")

    async def handle_operation(
        self, context: NodeExecutionContext, operation: str
    ) -> NodeExecutionResult:
        """Handle Slack-specific operations using SDK."""
        try:
            # Get Slack OAuth token from oauth_tokens table
            slack_token = await self.get_oauth_token(context)

            if not slack_token:
                return self._create_spec_error_result(
                    "No Slack authentication token found. Please connect your Slack account in integrations settings.",
                    operation,
                    {
                        "reason": "missing_oauth_token",
                        "solution": "Connect Slack account in integrations settings",
                    },
                )

            # Initialize Slack SDK client
            with SlackWebClient(token=slack_token) as slack:
                # Route to appropriate operation handler
                return await self._route_operation(context, operation, slack)

        except SlackAuthError as e:
            self.log_execution(context, f"Slack authentication error: {str(e)}", "ERROR")
            return self._create_spec_error_result(
                f"Slack authentication failed: {str(e)}",
                operation,
                {
                    "reason": "authentication_error",
                    "solution": "Check Slack OAuth token permissions",
                },
            )
        except SlackRateLimitError as e:
            self.log_execution(context, f"Slack rate limit exceeded: {str(e)}", "ERROR")
            return self._create_spec_error_result(
                f"Slack rate limit exceeded: {str(e)}",
                operation,
                {"reason": "rate_limit_exceeded", "solution": "Wait before retrying"},
            )
        except (SlackChannelNotFoundError, SlackUserNotFoundError) as e:
            self.log_execution(context, f"Slack resource not found: {str(e)}", "ERROR")
            return self._create_spec_error_result(
                f"Slack resource not found: {str(e)}",
                operation,
                {"reason": "resource_not_found", "solution": "Verify channel/user ID"},
            )
        except SlackAPIError as e:
            self.log_execution(context, f"Slack API error: {str(e)}", "ERROR")
            return self._create_spec_error_result(
                f"Slack API error: {str(e)}",
                operation,
                {"reason": "api_error"},
            )
        except Exception as e:
            self.log_execution(context, f"Unexpected error: {str(e)}", "ERROR")
            return self._create_spec_error_result(
                f"Slack action failed: {str(e)}",
                operation,
                {"exception_type": type(e).__name__, "exception": str(e)},
            )

    def _create_spec_error_result(
        self, message: str, operation: str, error_details: Dict[str, Any] = None
    ) -> NodeExecutionResult:
        """
        Create error result following node spec output format.

        Spec output_params:
        - success: false
        - message_ts: ""
        - channel_id: ""
        - response_data: {}
        - error_message: string
        - api_response: {}
        """
        return NodeExecutionResult(
            status=ExecutionStatus.ERROR,
            error_message=message,
            error_details={
                "integration": self.integration_name,
                "operation": operation,
                **(error_details or {}),
            },
            output_data={
                "success": False,
                "message_ts": "",
                "channel_id": "",
                "response_data": {},
                "error_message": message,
                "api_response": {},
            },
            metadata={
                "node_type": "external_action",
                "integration": self.integration_name,
                "operation": operation,
            },
        )

    def _create_spec_success_result(
        self,
        operation: str,
        response_data: Any,
        message_ts: str = "",
        channel_id: str = "",
    ) -> NodeExecutionResult:
        """
        Create success result following node spec output format.

        Spec output_params:
        - success: true
        - message_ts: string
        - channel_id: string
        - response_data: object (parsed Slack API response)
        - error_message: ""
        - api_response: object (raw response)
        """
        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data={
                "success": True,
                "message_ts": message_ts,
                "channel_id": channel_id,
                "response_data": response_data,
                "error_message": "",
                "api_response": response_data,  # For backward compatibility
            },
            metadata={
                "node_type": "external_action",
                "integration": self.integration_name,
                "operation": operation,
            },
        )

    async def _route_operation(
        self,
        context: NodeExecutionContext,
        operation: str,
        slack: SlackWebClient,
    ) -> NodeExecutionResult:
        """Route operation to appropriate SDK handler."""
        op_lower = operation.lower().replace("-", "_")

        # Messaging operations
        if op_lower == "send_message":
            return await self._send_message(context, slack)
        elif op_lower == "update_message":
            return await self._update_message(context, slack)
        elif op_lower == "delete_message":
            return await self._delete_message(context, slack)
        elif op_lower == "send_file":
            return await self._send_file(context, slack)

        # Channel operations
        elif op_lower == "create_channel":
            return await self._create_channel(context, slack)
        elif op_lower == "invite_users":
            return await self._invite_users(context, slack)
        elif op_lower == "set_channel_topic":
            return await self._set_channel_topic(context, slack)
        elif op_lower == "archive_channel":
            return await self._archive_channel(context, slack)

        # Info operations
        elif op_lower == "get_channel_info":
            return await self._get_channel_info(context, slack)
        elif op_lower == "get_user_info":
            return await self._get_user_info(context, slack)

        else:
            return self._create_spec_error_result(
                f"Unsupported Slack operation: {operation}",
                operation,
                {
                    "reason": "unsupported_operation",
                    "solution": "Use one of the supported operations from node spec",
                    "supported_operations": [
                        "send_message",
                        "update_message",
                        "delete_message",
                        "send_file",
                        "create_channel",
                        "invite_users",
                        "set_channel_topic",
                        "archive_channel",
                        "get_channel_info",
                        "get_user_info",
                    ],
                },
            )

    def _get_channel(self, context: NodeExecutionContext) -> str:
        """
        Extract channel from input_params or configurations (per node spec).

        Priority: input_params.channel_override > configurations.channel
        """
        # From input_params (highest priority - as per node spec)
        channel = context.input_data.get("channel_override") or context.input_data.get("channel")

        # Fallback to configurations
        if not channel:
            channel = context.node.configurations.get("channel", "#general")

        # Format channel name properly
        if channel and not channel.startswith("#") and not channel.startswith("C"):
            channel = f"#{channel}"

        return channel

    # ============================================================================
    # Messaging Operations
    # ============================================================================

    async def _send_message(
        self, context: NodeExecutionContext, slack: SlackWebClient
    ) -> NodeExecutionResult:
        """Send a Slack message (follows node spec input_params)."""
        channel = self._get_channel(context)

        # Extract from input_params (as per node spec)
        message = context.input_data.get("message", "")
        blocks = context.input_data.get("blocks", [])
        attachments = context.input_data.get("attachments", [])
        thread_ts = context.node.configurations.get("thread_ts") or context.input_data.get(
            "thread_ts"
        )
        unfurl_links = context.node.configurations.get("unfurl_links", True)
        unfurl_media = context.node.configurations.get("unfurl_media", True)

        # Validate that we have either message text or blocks
        if not message and not blocks:
            return self._create_spec_error_result(
                "Message text or blocks required",
                "send_message",
                {"missing_parameters": ["message", "blocks"]},
            )

        self.log_execution(context, f"Sending Slack message to {channel}")

        try:
            # Prepare message kwargs
            kwargs = {
                "channel": channel,
                "text": message,
                "unfurl_links": unfurl_links,
                "unfurl_media": unfurl_media,
            }

            if blocks:
                kwargs["blocks"] = blocks
            if attachments:
                kwargs["attachments"] = attachments
            if thread_ts:
                kwargs["thread_ts"] = thread_ts

            # Use SDK to send message
            response = slack.send_message(**kwargs)

            self.log_execution(context, f"✅ Message sent to {channel}")

            return self._create_spec_success_result(
                "send_message",
                response,
                message_ts=response.get("ts", ""),
                channel_id=response.get("channel", ""),
            )

        except Exception as e:
            raise SlackAPIError(f"Failed to send message: {str(e)}")

    async def _update_message(
        self, context: NodeExecutionContext, slack: SlackWebClient
    ) -> NodeExecutionResult:
        """Update an existing Slack message."""
        channel = self._get_channel(context)
        message_ts = context.input_data.get("message_ts")
        message = context.input_data.get("message", "")
        blocks = context.input_data.get("blocks", [])

        if not message_ts:
            return self._create_spec_error_result(
                "message_ts required to update message",
                "update_message",
                {"missing_parameters": ["message_ts"]},
            )

        if not message and not blocks:
            return self._create_spec_error_result(
                "Message text or blocks required",
                "update_message",
                {"missing_parameters": ["message", "blocks"]},
            )

        self.log_execution(context, f"Updating Slack message {message_ts} in {channel}")

        try:
            # Make direct API call for update (SDK may not have this method)
            response = slack._make_request(
                "POST",
                "chat.update",
                data={
                    "channel": channel,
                    "ts": message_ts,
                    "text": message,
                    "blocks": blocks if blocks else None,
                },
            )

            self.log_execution(context, f"✅ Message {message_ts} updated")

            return self._create_spec_success_result(
                "update_message",
                response,
                message_ts=response.get("ts", ""),
                channel_id=response.get("channel", ""),
            )

        except Exception as e:
            raise SlackAPIError(f"Failed to update message: {str(e)}")

    async def _delete_message(
        self, context: NodeExecutionContext, slack: SlackWebClient
    ) -> NodeExecutionResult:
        """Delete a Slack message."""
        channel = self._get_channel(context)
        message_ts = context.input_data.get("message_ts")

        if not message_ts:
            return self._create_spec_error_result(
                "message_ts required to delete message",
                "delete_message",
                {"missing_parameters": ["message_ts"]},
            )

        self.log_execution(context, f"Deleting Slack message {message_ts} from {channel}")

        try:
            response = slack._make_request(
                "POST",
                "chat.delete",
                data={
                    "channel": channel,
                    "ts": message_ts,
                },
            )

            self.log_execution(context, f"✅ Message {message_ts} deleted")

            return self._create_spec_success_result(
                "delete_message",
                response,
                channel_id=response.get("channel", ""),
            )

        except Exception as e:
            raise SlackAPIError(f"Failed to delete message: {str(e)}")

    async def _send_file(
        self, context: NodeExecutionContext, slack: SlackWebClient
    ) -> NodeExecutionResult:
        """Upload a file to Slack."""
        channel = self._get_channel(context)
        file_content = context.input_data.get("file_content")
        filename = context.input_data.get("filename", "file.txt")
        initial_comment = context.input_data.get("initial_comment", "")

        if not file_content:
            return self._create_spec_error_result(
                "file_content required",
                "send_file",
                {"missing_parameters": ["file_content"]},
            )

        self.log_execution(context, f"Uploading file {filename} to {channel}")

        try:
            # Note: Slack SDK's send_file might need adjustment based on actual implementation
            response = slack._make_request(
                "POST",
                "files.upload",
                data={
                    "channels": channel,
                    "filename": filename,
                    "initial_comment": initial_comment,
                },
                files={"file": file_content},
            )

            self.log_execution(context, f"✅ File {filename} uploaded to {channel}")

            return self._create_spec_success_result(
                "send_file",
                response,
                channel_id=(
                    response.get("file", {}).get("channels", [channel])[0]
                    if isinstance(response.get("file", {}).get("channels"), list)
                    else channel
                ),
            )

        except Exception as e:
            raise SlackAPIError(f"Failed to upload file: {str(e)}")

    # ============================================================================
    # Channel Operations
    # ============================================================================

    async def _create_channel(
        self, context: NodeExecutionContext, slack: SlackWebClient
    ) -> NodeExecutionResult:
        """Create a new Slack channel."""
        channel_name = context.input_data.get("channel_name") or context.input_data.get("name")
        is_private = context.input_data.get("is_private", False)

        if not channel_name:
            return self._create_spec_error_result(
                "channel_name required",
                "create_channel",
                {"missing_parameters": ["channel_name"]},
            )

        # Clean channel name (lowercase, no spaces)
        channel_name = channel_name.lower().replace(" ", "-").replace("#", "")

        self.log_execution(context, f"Creating Slack channel: {channel_name}")

        try:
            endpoint = "conversations.create"
            response = slack._make_request(
                "POST",
                endpoint,
                data={
                    "name": channel_name,
                    "is_private": is_private,
                },
            )

            channel_id = response.get("channel", {}).get("id", "")
            self.log_execution(context, f"✅ Channel {channel_name} created: {channel_id}")

            return self._create_spec_success_result(
                "create_channel",
                response,
                channel_id=channel_id,
            )

        except Exception as e:
            raise SlackAPIError(f"Failed to create channel: {str(e)}")

    async def _invite_users(
        self, context: NodeExecutionContext, slack: SlackWebClient
    ) -> NodeExecutionResult:
        """Invite users to a Slack channel."""
        channel = self._get_channel(context)
        user_ids = context.input_data.get("user_ids", [])

        if not user_ids:
            return self._create_spec_error_result(
                "user_ids required",
                "invite_users",
                {"missing_parameters": ["user_ids"]},
            )

        if not isinstance(user_ids, list):
            user_ids = [user_ids]

        self.log_execution(context, f"Inviting {len(user_ids)} users to {channel}")

        try:
            response = slack._make_request(
                "POST",
                "conversations.invite",
                data={
                    "channel": channel,
                    "users": ",".join(user_ids),
                },
            )

            self.log_execution(context, f"✅ Invited {len(user_ids)} users to {channel}")

            return self._create_spec_success_result(
                "invite_users",
                response,
                channel_id=response.get("channel", {}).get("id", channel),
            )

        except Exception as e:
            raise SlackAPIError(f"Failed to invite users: {str(e)}")

    async def _set_channel_topic(
        self, context: NodeExecutionContext, slack: SlackWebClient
    ) -> NodeExecutionResult:
        """Set Slack channel topic."""
        channel = self._get_channel(context)
        topic = context.input_data.get("topic", "")

        if not topic:
            return self._create_spec_error_result(
                "topic required",
                "set_channel_topic",
                {"missing_parameters": ["topic"]},
            )

        self.log_execution(context, f"Setting topic for {channel}")

        try:
            response = slack._make_request(
                "POST",
                "conversations.setTopic",
                data={
                    "channel": channel,
                    "topic": topic,
                },
            )

            self.log_execution(context, f"✅ Topic set for {channel}")

            return self._create_spec_success_result(
                "set_channel_topic",
                response,
                channel_id=channel,
            )

        except Exception as e:
            raise SlackAPIError(f"Failed to set channel topic: {str(e)}")

    async def _archive_channel(
        self, context: NodeExecutionContext, slack: SlackWebClient
    ) -> NodeExecutionResult:
        """Archive a Slack channel."""
        channel = self._get_channel(context)

        self.log_execution(context, f"Archiving channel {channel}")

        try:
            response = slack._make_request(
                "POST",
                "conversations.archive",
                data={
                    "channel": channel,
                },
            )

            self.log_execution(context, f"✅ Channel {channel} archived")

            return self._create_spec_success_result(
                "archive_channel",
                response,
                channel_id=channel,
            )

        except Exception as e:
            raise SlackAPIError(f"Failed to archive channel: {str(e)}")

    # ============================================================================
    # Info Operations
    # ============================================================================

    async def _get_channel_info(
        self, context: NodeExecutionContext, slack: SlackWebClient
    ) -> NodeExecutionResult:
        """Get Slack channel information."""
        channel = self._get_channel(context)

        self.log_execution(context, f"Getting info for channel {channel}")

        try:
            response = slack.get_channel_info(channel)

            self.log_execution(context, f"✅ Retrieved info for {channel}")

            return self._create_spec_success_result(
                "get_channel_info",
                response,
                channel_id=response.get("channel", {}).get("id", channel),
            )

        except Exception as e:
            raise SlackAPIError(f"Failed to get channel info: {str(e)}")

    async def _get_user_info(
        self, context: NodeExecutionContext, slack: SlackWebClient
    ) -> NodeExecutionResult:
        """Get Slack user information."""
        user_id = context.input_data.get("user_id")

        if not user_id:
            return self._create_spec_error_result(
                "user_id required",
                "get_user_info",
                {"missing_parameters": ["user_id"]},
            )

        self.log_execution(context, f"Getting info for user {user_id}")

        try:
            response = slack.get_user_info(user_id)

            self.log_execution(context, f"✅ Retrieved info for user {user_id}")

            return self._create_spec_success_result(
                "get_user_info",
                response,
            )

        except Exception as e:
            raise SlackAPIError(f"Failed to get user info: {str(e)}")


__all__ = ["SlackExternalAction"]
