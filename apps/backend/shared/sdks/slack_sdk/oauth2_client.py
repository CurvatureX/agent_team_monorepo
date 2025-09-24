"""
Slack OAuth2 Client for workflow integration.

This provides Slack OAuth2 authentication compatible with the BaseSDK pattern.
"""

import os
from typing import Any, Dict, Optional

from ..base import APIResponse, BaseSDK, OAuth2Config
from .client import SlackWebClient
from .exceptions import SlackAPIError, SlackAuthError, SlackRateLimitError


class SlackOAuth2SDK(BaseSDK):
    """Slack SDK client using OAuth2 bot tokens (bot mode only)."""

    @property
    def base_url(self) -> str:
        return "https://slack.com/api"

    @property
    def supported_operations(self) -> Dict[str, str]:
        # MCP-aligned operations (bot mode only)
        return {
            "slack_send_message": "Send message to channel or user (bot)",
            "slack_reply_to_thread": "Reply in a thread (bot)",
            "slack_add_reaction": "Add reaction to a message (bot)",
            "slack_list_channels": "List workspace channels",
            "slack_get_channel_history": "Get recent messages from a channel",
            "slack_invite_users_to_channel": "Invite users to a channel",
            "slack_list_users": "List workspace users",
            "slack_get_user_info": "Get user information",
            "slack_search_messages": "Search messages",
        }

    def get_oauth2_config(self) -> OAuth2Config:
        """Get Slack OAuth2 configuration."""
        return OAuth2Config(
            client_id=os.getenv("SLACK_CLIENT_ID", ""),
            client_secret=os.getenv("SLACK_CLIENT_SECRET", ""),
            auth_url="https://slack.com/oauth/v2/authorize",
            token_url="https://slack.com/api/oauth.v2.access",
            revoke_url="https://slack.com/api/auth.revoke",
            scopes=[
                "channels:read",
                "channels:write",
                "chat:write",
                "chat:write.public",
                "files:write",
                "groups:read",
                "users:read",
                "team:read",
            ],
            redirect_uri=os.getenv(
                "SLACK_REDIRECT_URI", "http://localhost:8002/api/v1/oauth2/slack/callback"
            ),
        )

    def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """Validate Slack credentials."""
        return "access_token" in credentials and bool(credentials["access_token"])

    async def call_operation(
        self, operation: str, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> APIResponse:
        """Execute Slack API operation."""
        if not self.validate_credentials(credentials):
            return APIResponse(
                success=False,
                error="Invalid credentials: missing access_token",
                provider="slack",
                operation=operation,
            )

        if operation not in self.supported_operations:
            return APIResponse(
                success=False,
                error=f"Unsupported operation: {operation}",
                provider="slack",
                operation=operation,
            )

        try:
            # Route to specific operation handler
            handler_map = {
                "send_message": self._send_message,
                "post_message": self._post_message,
                "update_message": self._update_message,
                "delete_message": self._delete_message,
                "list_channels": self._list_channels,
                "get_channel_info": self._get_channel_info,
                "create_channel": self._create_channel,
                "invite_to_channel": self._invite_to_channel,
                "get_user_info": self._get_user_info,
                "list_users": self._list_users,
                "upload_file": self._upload_file,
                "get_conversations": self._get_conversations,
                "get_conversation_history": self._get_conversation_history,
                "set_presence": self._set_presence,
                "get_team_info": self._get_team_info,
                "add_reaction": self._add_reaction,
                "search_messages": self._search_messages,
            }
            # Direct mapping for bot-mode MCP operations
            mapping = {
                "slack_send_message": "send_message",
                "slack_reply_to_thread": "send_message",
                "slack_add_reaction": "add_reaction",
                "slack_list_channels": "list_channels",
                "slack_get_channel_history": "get_conversation_history",
                "slack_invite_users_to_channel": "invite_to_channel",
                "slack_list_users": "list_users",
                "slack_get_user_info": "get_user_info",
                "slack_search_messages": "search_messages",
            }

            if operation not in mapping:
                return APIResponse(
                    success=False,
                    error=f"Unsupported operation: {operation}",
                    provider="slack",
                    operation=operation,
                )

            handler = handler_map[mapping[operation]]
            result = await handler(parameters, credentials)

            return APIResponse(success=True, data=result, provider="slack", operation=operation)

        except SlackAuthError as e:
            return APIResponse(
                success=False, error=str(e), provider="slack", operation=operation, status_code=401
            )
        except SlackRateLimitError as e:
            return APIResponse(
                success=False, error=str(e), provider="slack", operation=operation, status_code=429
            )
        except Exception as e:
            self.logger.error(f"Slack {operation} failed: {str(e)}")
            return APIResponse(success=False, error=str(e), provider="slack", operation=operation)

    async def _send_message(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Send message to channel or user."""
        channel = parameters.get("channel")
        text = parameters.get("text") or parameters.get("message", "")
        blocks = parameters.get("blocks")
        thread_ts = parameters.get("thread_ts")

        if not channel:
            raise SlackAPIError("Missing required parameter: channel")

        if not text and not blocks:
            raise SlackAPIError("Missing required parameter: text or blocks")

        url = f"{self.base_url}/chat.postMessage"
        headers = self._prepare_headers(credentials)

        payload = {"channel": channel, "text": text}

        if blocks:
            payload["blocks"] = blocks
        if thread_ts:
            payload["thread_ts"] = thread_ts

        response = await self.make_http_request("POST", url, headers=headers, json_data=payload)

        if not (200 <= response.status_code < 300):
            self._handle_error(response)

        response_data = response.json()

        if not response_data.get("ok"):
            raise SlackAPIError(f"Slack API error: {response_data.get('error', 'Unknown error')}")

        return {
            "message_ts": response_data.get("ts"),
            "channel": response_data.get("channel"),
            "text": text,
            "success": True,
        }

    async def _post_message(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Post message to channel (alias for send_message)."""
        return await self._send_message(parameters, credentials)

    async def _list_channels(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """List workspace channels."""
        types = parameters.get("types", "public_channel,private_channel")
        limit = min(int(parameters.get("limit", 100)), 1000)

        url = f"{self.base_url}/conversations.list"
        headers = self._prepare_headers(credentials)

        params = {"types": types, "limit": limit}

        response = await self.make_http_request("GET", url, headers=headers, params=params)

        if not (200 <= response.status_code < 300):
            self._handle_error(response)

        response_data = response.json()

        if not response_data.get("ok"):
            raise SlackAPIError(f"Slack API error: {response_data.get('error', 'Unknown error')}")

        channels = []
        for channel in response_data.get("channels", []):
            channels.append(
                {
                    "id": channel.get("id"),
                    "name": channel.get("name"),
                    "is_channel": channel.get("is_channel"),
                    "is_private": channel.get("is_private"),
                    "is_im": channel.get("is_im"),
                    "is_mpim": channel.get("is_mpim"),
                    "created": channel.get("created"),
                    "creator": channel.get("creator"),
                    "num_members": channel.get("num_members"),
                }
            )

        return {"channels": channels, "total_count": len(channels)}

    async def _get_user_info(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Get user information."""
        user = parameters.get("user")

        if not user:
            raise SlackAPIError("Missing required parameter: user")

        url = f"{self.base_url}/users.info"
        headers = self._prepare_headers(credentials)

        params = {"user": user}

        response = await self.make_http_request("GET", url, headers=headers, params=params)

        if not (200 <= response.status_code < 300):
            self._handle_error(response)

        response_data = response.json()

        if not response_data.get("ok"):
            raise SlackAPIError(f"Slack API error: {response_data.get('error', 'Unknown error')}")

        user_data = response_data.get("user", {})

        return {
            "id": user_data.get("id"),
            "name": user_data.get("name"),
            "real_name": user_data.get("real_name"),
            "display_name": user_data.get("profile", {}).get("display_name"),
            "email": user_data.get("profile", {}).get("email"),
            "image": user_data.get("profile", {}).get("image_72"),
            "is_bot": user_data.get("is_bot", False),
            "deleted": user_data.get("deleted", False),
        }

    async def _get_conversation_history(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        channel = parameters.get("channel") or parameters.get("channel_id")
        limit = min(int(parameters.get("limit", 100)), 1000)
        if not channel:
            raise SlackAPIError("Missing required parameter: channel")
        url = f"{self.base_url}/conversations.history"
        headers = self._prepare_headers(credentials)
        params = {"channel": channel, "limit": limit}
        response = await self.make_http_request("GET", url, headers=headers, params=params)
        if not (200 <= response.status_code < 300):
            self._handle_error(response)
        data = response.json()
        if not data.get("ok"):
            raise SlackAPIError(f"Slack API error: {data.get('error', 'Unknown error')}")
        return {"messages": data.get("messages", []), "has_more": data.get("has_more", False)}

    async def _get_channel_info(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        channel = parameters.get("channel") or parameters.get("channel_id")
        if not channel:
            raise SlackAPIError("Missing required parameter: channel")
        url = f"{self.base_url}/conversations.info"
        headers = self._prepare_headers(credentials)
        params = {"channel": channel}
        response = await self.make_http_request("GET", url, headers=headers, params=params)
        if not (200 <= response.status_code < 300):
            self._handle_error(response)
        data = response.json()
        if not data.get("ok"):
            raise SlackAPIError(f"Slack API error: {data.get('error', 'Unknown error')}")
        return data.get("channel", {})

    async def _invite_to_channel(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        channel = parameters.get("channel") or parameters.get("channel_id")
        users = parameters.get("users") or parameters.get("user_ids")
        if not channel or not users:
            raise SlackAPIError("Missing required parameters: channel and users")
        if isinstance(users, list):
            users = ",".join(users)
        url = f"{self.base_url}/conversations.invite"
        headers = self._prepare_headers(credentials)
        payload = {"channel": channel, "users": users}
        response = await self.make_http_request("POST", url, headers=headers, json_data=payload)
        if not (200 <= response.status_code < 300):
            self._handle_error(response)
        data = response.json()
        if not data.get("ok"):
            raise SlackAPIError(f"Slack API error: {data.get('error', 'Unknown error')}")
        return data

    async def _list_users(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        limit = min(int(parameters.get("limit", 200)), 1000)
        url = f"{self.base_url}/users.list"
        headers = self._prepare_headers(credentials)
        params = {"limit": limit}
        response = await self.make_http_request("GET", url, headers=headers, params=params)
        if not (200 <= response.status_code < 300):
            self._handle_error(response)
        data = response.json()
        if not data.get("ok"):
            raise SlackAPIError(f"Slack API error: {data.get('error', 'Unknown error')}")
        return {"members": data.get("members", [])}

    async def _get_conversations(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        types = parameters.get("types", "public_channel,private_channel")
        limit = min(int(parameters.get("limit", 200)), 1000)
        url = f"{self.base_url}/conversations.list"
        headers = self._prepare_headers(credentials)
        params = {"types": types, "limit": limit}
        response = await self.make_http_request("GET", url, headers=headers, params=params)
        if not (200 <= response.status_code < 300):
            self._handle_error(response)
        data = response.json()
        if not data.get("ok"):
            raise SlackAPIError(f"Slack API error: {data.get('error', 'Unknown error')}")
        return {"conversations": data.get("channels", [])}

    async def _add_reaction(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        channel = parameters.get("channel") or parameters.get("channel_id")
        name = parameters.get("name") or parameters.get("emoji")
        timestamp = (
            parameters.get("timestamp") or parameters.get("ts") or parameters.get("message_ts")
        )
        if not channel or not name or not timestamp:
            raise SlackAPIError("Missing required parameters: channel, name, timestamp")
        url = f"{self.base_url}/reactions.add"
        headers = self._prepare_headers(credentials)
        payload = {"channel": channel, "name": name, "timestamp": timestamp}
        response = await self.make_http_request("POST", url, headers=headers, json_data=payload)
        if not (200 <= response.status_code < 300):
            self._handle_error(response)
        data = response.json()
        if not data.get("ok"):
            raise SlackAPIError(f"Slack API error: {data.get('error', 'Unknown error')}")
        return {"ok": True}

    async def _search_messages(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        query = parameters.get("query")
        count = min(int(parameters.get("count", 20)), 100)
        if not query:
            raise SlackAPIError("Missing required parameter: query")
        url = f"{self.base_url}/search.messages"
        headers = self._prepare_headers(credentials)
        params = {"query": query, "count": count}
        response = await self.make_http_request("GET", url, headers=headers, params=params)
        if not (200 <= response.status_code < 300):
            self._handle_error(response)
        data = response.json()
        if not data.get("ok"):
            raise SlackAPIError(f"Slack API error: {data.get('error', 'Unknown error')}")
        return data.get("messages", {})

    async def _get_team_info(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Get team/workspace info."""
        url = f"{self.base_url}/team.info"
        headers = self._prepare_headers(credentials)

        response = await self.make_http_request("GET", url, headers=headers)

        if not (200 <= response.status_code < 300):
            self._handle_error(response)

        response_data = response.json()

        if not response_data.get("ok"):
            raise SlackAPIError(f"Slack API error: {response_data.get('error', 'Unknown error')}")

        team_data = response_data.get("team", {})

        return {
            "id": team_data.get("id"),
            "name": team_data.get("name"),
            "domain": team_data.get("domain"),
            "icon": team_data.get("icon", {}),
            "email_domain": team_data.get("email_domain"),
        }

    async def _test_connection_impl(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Slack specific connection test."""
        try:
            team_info = await self._get_team_info({}, credentials)
            return {
                "credentials_valid": True,
                "slack_access": True,
                "team_name": team_info.get("name"),
                "team_domain": team_info.get("domain"),
            }
        except Exception as e:
            return {"credentials_valid": False, "error": str(e)}

    def _prepare_headers(self, credentials: Dict[str, str]) -> Dict[str, str]:
        """Prepare Slack API headers."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AgentTeam-Workflow-Engine/1.0",
        }

        if "access_token" in credentials:
            headers["Authorization"] = f"Bearer {credentials['access_token']}"

        return headers

    def _handle_error(self, response) -> None:
        """Handle HTTP error responses."""
        if response.status_code == 401:
            raise SlackAuthError("Authentication failed")
        elif response.status_code == 403:
            raise SlackAuthError("Forbidden - insufficient permissions")
        elif response.status_code == 404:
            raise SlackAPIError("Channel or resource not found")
        elif response.status_code == 429:
            raise SlackRateLimitError("Rate limit exceeded")
        elif 400 <= response.status_code < 500:
            raise SlackAPIError(f"Client error: {response.status_code}")
        elif 500 <= response.status_code < 600:
            raise SlackAPIError(f"Server error: {response.status_code}")
        else:
            raise SlackAPIError(f"Unexpected error: {response.status_code}")

    # Placeholder methods for other operations - can be implemented as needed
    async def _update_message(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Update existing message."""
        raise NotImplementedError("Update message not yet implemented")

    async def _delete_message(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Delete message."""
        raise NotImplementedError("Delete message not yet implemented")

    async def _get_channel_info(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Get channel information."""
        raise NotImplementedError("Get channel info not yet implemented")

    async def _create_channel(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Create new channel."""
        raise NotImplementedError("Create channel not yet implemented")

    async def _invite_to_channel(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Invite user to channel."""
        raise NotImplementedError("Invite to channel not yet implemented")

    async def _list_users(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """List workspace users."""
        raise NotImplementedError("List users not yet implemented")

    async def _upload_file(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Upload file to Slack."""
        raise NotImplementedError("Upload file not yet implemented")

    async def _get_conversations(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Get conversation list."""
        raise NotImplementedError("Get conversations not yet implemented")

    async def _get_conversation_history(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Get conversation messages."""
        raise NotImplementedError("Get conversation history not yet implemented")

    async def _set_presence(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Set user presence."""
        raise NotImplementedError("Set presence not yet implemented")
