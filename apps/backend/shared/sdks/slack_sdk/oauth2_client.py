"""
Slack OAuth2 Client for workflow integration.

This provides Slack OAuth2 authentication compatible with the BaseSDK pattern.
"""

import os
from typing import Any, Dict, Optional

from ..base import APIResponse, BaseSDK, OAuth2Config
from .exceptions import SlackAPIError, SlackAuthError, SlackRateLimitError
from .client import SlackWebClient


class SlackOAuth2SDK(BaseSDK):
    """Slack SDK client with OAuth2 authentication."""
    
    @property
    def base_url(self) -> str:
        return "https://slack.com/api"
    
    @property
    def supported_operations(self) -> Dict[str, str]:
        return {
            "send_message": "Send message to channel or user",
            "post_message": "Post message to channel", 
            "update_message": "Update existing message",
            "delete_message": "Delete message",
            "list_channels": "List workspace channels",
            "get_channel_info": "Get channel information",
            "create_channel": "Create new channel",
            "invite_to_channel": "Invite user to channel",
            "get_user_info": "Get user information",
            "list_users": "List workspace users",
            "upload_file": "Upload file to Slack",
            "get_conversations": "Get conversation list",
            "get_conversation_history": "Get conversation messages",
            "set_presence": "Set user presence",
            "get_team_info": "Get team/workspace info"
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
                "team:read"
            ],
            redirect_uri=os.getenv("SLACK_REDIRECT_URI", "http://localhost:8002/api/v1/oauth2/slack/callback")
        )
    
    def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """Validate Slack credentials."""
        return "access_token" in credentials and bool(credentials["access_token"])
    
    async def call_operation(
        self, 
        operation: str, 
        parameters: Dict[str, Any], 
        credentials: Dict[str, str]
    ) -> APIResponse:
        """Execute Slack API operation."""
        if not self.validate_credentials(credentials):
            return APIResponse(
                success=False,
                error="Invalid credentials: missing access_token",
                provider="slack",
                operation=operation
            )
        
        if operation not in self.supported_operations:
            return APIResponse(
                success=False,
                error=f"Unsupported operation: {operation}",
                provider="slack",
                operation=operation
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
                "get_team_info": self._get_team_info
            }
            
            handler = handler_map[operation]
            result = await handler(parameters, credentials)
            
            return APIResponse(
                success=True,
                data=result,
                provider="slack",
                operation=operation
            )
            
        except (SlackAuthError) as e:
            return APIResponse(
                success=False,
                error=str(e),
                provider="slack",
                operation=operation,
                status_code=401
            )
        except SlackRateLimitError as e:
            return APIResponse(
                success=False,
                error=str(e),
                provider="slack",
                operation=operation,
                status_code=429
            )
        except Exception as e:
            self.logger.error(f"Slack {operation} failed: {str(e)}")
            return APIResponse(
                success=False,
                error=str(e),
                provider="slack",
                operation=operation
            )
    
    async def _send_message(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
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
        
        payload = {
            "channel": channel,
            "text": text
        }
        
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
            "success": True
        }
    
    async def _post_message(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """Post message to channel (alias for send_message)."""
        return await self._send_message(parameters, credentials)
    
    async def _list_channels(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """List workspace channels."""
        types = parameters.get("types", "public_channel,private_channel")
        limit = min(int(parameters.get("limit", 100)), 1000)
        
        url = f"{self.base_url}/conversations.list"
        headers = self._prepare_headers(credentials)
        
        params = {
            "types": types,
            "limit": limit
        }
        
        response = await self.make_http_request("GET", url, headers=headers, params=params)
        
        if not (200 <= response.status_code < 300):
            self._handle_error(response)
        
        response_data = response.json()
        
        if not response_data.get("ok"):
            raise SlackAPIError(f"Slack API error: {response_data.get('error', 'Unknown error')}")
        
        channels = []
        for channel in response_data.get("channels", []):
            channels.append({
                "id": channel.get("id"),
                "name": channel.get("name"),
                "is_channel": channel.get("is_channel"),
                "is_private": channel.get("is_private"),
                "is_im": channel.get("is_im"),
                "is_mpim": channel.get("is_mpim"),
                "created": channel.get("created"),
                "creator": channel.get("creator"),
                "num_members": channel.get("num_members")
            })
        
        return {
            "channels": channels,
            "total_count": len(channels)
        }
    
    async def _get_user_info(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
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
            "deleted": user_data.get("deleted", False)
        }
    
    async def _get_team_info(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
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
            "email_domain": team_data.get("email_domain")
        }
    
    async def _test_connection_impl(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Slack specific connection test."""
        try:
            team_info = await self._get_team_info({}, credentials)
            return {
                "credentials_valid": True,
                "slack_access": True,
                "team_name": team_info.get("name"),
                "team_domain": team_info.get("domain")
            }
        except Exception as e:
            return {
                "credentials_valid": False,
                "error": str(e)
            }
    
    def _prepare_headers(self, credentials: Dict[str, str]) -> Dict[str, str]:
        """Prepare Slack API headers."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AgentTeam-Workflow-Engine/1.0"
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
    
    async def _update_message(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """Update existing message."""
        channel = parameters.get("channel")
        ts = parameters.get("ts") or parameters.get("message_ts")
        text = parameters.get("text")
        blocks = parameters.get("blocks")
        
        if not channel:
            raise SlackAPIError("Missing required parameter: channel")
        if not ts:
            raise SlackAPIError("Missing required parameter: ts or message_ts")
        if not text and not blocks:
            raise SlackAPIError("Missing required parameter: text or blocks")
        
        url = f"{self.base_url}/chat.update"
        headers = self._prepare_headers(credentials)
        
        payload = {
            "channel": channel,
            "ts": ts,
            "text": text
        }
        
        if blocks:
            payload["blocks"] = blocks
        
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
            "success": True
        }
    
    async def _delete_message(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """Delete message."""
        channel = parameters.get("channel")
        ts = parameters.get("ts") or parameters.get("message_ts")
        
        if not channel:
            raise SlackAPIError("Missing required parameter: channel")
        if not ts:
            raise SlackAPIError("Missing required parameter: ts or message_ts")
        
        url = f"{self.base_url}/chat.delete"
        headers = self._prepare_headers(credentials)
        
        payload = {
            "channel": channel,
            "ts": ts
        }
        
        response = await self.make_http_request("POST", url, headers=headers, json_data=payload)
        
        if not (200 <= response.status_code < 300):
            self._handle_error(response)
        
        response_data = response.json()
        
        if not response_data.get("ok"):
            raise SlackAPIError(f"Slack API error: {response_data.get('error', 'Unknown error')}")
        
        return {
            "deleted": True,
            "channel": channel,
            "ts": ts,
            "success": True
        }
    
    async def _get_channel_info(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """Get channel information."""
        channel = parameters.get("channel") or parameters.get("channel_id")
        
        if not channel:
            raise SlackAPIError("Missing required parameter: channel")
        
        url = f"{self.base_url}/conversations.info"
        headers = self._prepare_headers(credentials)
        
        params = {"channel": channel}
        
        response = await self.make_http_request("GET", url, headers=headers, params=params)
        
        if not (200 <= response.status_code < 300):
            self._handle_error(response)
        
        response_data = response.json()
        
        if not response_data.get("ok"):
            raise SlackAPIError(f"Slack API error: {response_data.get('error', 'Unknown error')}")
        
        channel_data = response_data.get("channel", {})
        
        return {
            "id": channel_data.get("id"),
            "name": channel_data.get("name"),
            "is_channel": channel_data.get("is_channel"),
            "is_private": channel_data.get("is_private"),
            "is_archived": channel_data.get("is_archived"),
            "topic": channel_data.get("topic", {}).get("value"),
            "purpose": channel_data.get("purpose", {}).get("value"),
            "created": channel_data.get("created"),
            "creator": channel_data.get("creator"),
            "num_members": channel_data.get("num_members")
        }
    
    async def _create_channel(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """Create new channel."""
        name = parameters.get("name")
        is_private = parameters.get("is_private", False)
        
        if not name:
            raise SlackAPIError("Missing required parameter: name")
        
        url = f"{self.base_url}/conversations.create"
        headers = self._prepare_headers(credentials)
        
        payload = {
            "name": name,
            "is_private": is_private
        }
        
        response = await self.make_http_request("POST", url, headers=headers, json_data=payload)
        
        if not (200 <= response.status_code < 300):
            self._handle_error(response)
        
        response_data = response.json()
        
        if not response_data.get("ok"):
            raise SlackAPIError(f"Slack API error: {response_data.get('error', 'Unknown error')}")
        
        channel_data = response_data.get("channel", {})
        
        return {
            "id": channel_data.get("id"),
            "name": channel_data.get("name"),
            "created": channel_data.get("created"),
            "is_private": is_private,
            "success": True
        }
    
    async def _invite_to_channel(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """Invite user to channel."""
        channel = parameters.get("channel") or parameters.get("channel_id")
        users = parameters.get("users")
        
        if not channel:
            raise SlackAPIError("Missing required parameter: channel")
        if not users:
            raise SlackAPIError("Missing required parameter: users")
        
        # Convert single user to list
        if isinstance(users, str):
            users = [users]
        
        url = f"{self.base_url}/conversations.invite"
        headers = self._prepare_headers(credentials)
        
        payload = {
            "channel": channel,
            "users": ",".join(users)
        }
        
        response = await self.make_http_request("POST", url, headers=headers, json_data=payload)
        
        if not (200 <= response.status_code < 300):
            self._handle_error(response)
        
        response_data = response.json()
        
        if not response_data.get("ok"):
            raise SlackAPIError(f"Slack API error: {response_data.get('error', 'Unknown error')}")
        
        return {
            "channel": response_data.get("channel", {}).get("id"),
            "invited_users": users,
            "success": True
        }
    
    async def _list_users(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """List workspace users."""
        limit = min(int(parameters.get("limit", 100)), 1000)
        cursor = parameters.get("cursor")
        
        url = f"{self.base_url}/users.list"
        headers = self._prepare_headers(credentials)
        
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        
        response = await self.make_http_request("GET", url, headers=headers, params=params)
        
        if not (200 <= response.status_code < 300):
            self._handle_error(response)
        
        response_data = response.json()
        
        if not response_data.get("ok"):
            raise SlackAPIError(f"Slack API error: {response_data.get('error', 'Unknown error')}")
        
        users = []
        for user in response_data.get("members", []):
            if not user.get("deleted", False):
                users.append({
                    "id": user.get("id"),
                    "name": user.get("name"),
                    "real_name": user.get("real_name"),
                    "display_name": user.get("profile", {}).get("display_name"),
                    "email": user.get("profile", {}).get("email"),
                    "is_bot": user.get("is_bot", False),
                    "is_admin": user.get("is_admin", False),
                    "is_owner": user.get("is_owner", False)
                })
        
        return {
            "users": users,
            "total_count": len(users),
            "next_cursor": response_data.get("response_metadata", {}).get("next_cursor")
        }
    
    async def _upload_file(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """Upload file to Slack."""
        channels = parameters.get("channels")
        content = parameters.get("content")
        filename = parameters.get("filename", "file.txt")
        filetype = parameters.get("filetype", "text")
        title = parameters.get("title")
        initial_comment = parameters.get("initial_comment")
        
        if not content:
            raise SlackAPIError("Missing required parameter: content")
        
        url = f"{self.base_url}/files.upload"
        headers = {
            "Authorization": f"Bearer {credentials['access_token']}"
        }
        
        form_data = {
            "content": content,
            "filename": filename,
            "filetype": filetype
        }
        
        if channels:
            if isinstance(channels, list):
                channels = ",".join(channels)
            form_data["channels"] = channels
        
        if title:
            form_data["title"] = title
        
        if initial_comment:
            form_data["initial_comment"] = initial_comment
        
        response = await self.make_http_request("POST", url, headers=headers, data=form_data)
        
        if not (200 <= response.status_code < 300):
            self._handle_error(response)
        
        response_data = response.json()
        
        if not response_data.get("ok"):
            raise SlackAPIError(f"Slack API error: {response_data.get('error', 'Unknown error')}")
        
        file_data = response_data.get("file", {})
        
        return {
            "id": file_data.get("id"),
            "name": file_data.get("name"),
            "title": file_data.get("title"),
            "mimetype": file_data.get("mimetype"),
            "size": file_data.get("size"),
            "url_private": file_data.get("url_private"),
            "permalink": file_data.get("permalink"),
            "success": True
        }
    
    async def _get_conversations(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """Get conversation list (alias for list_channels with more options)."""
        return await self._list_channels(parameters, credentials)
    
    async def _get_conversation_history(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """Get conversation messages."""
        channel = parameters.get("channel") or parameters.get("channel_id")
        limit = min(int(parameters.get("limit", 100)), 1000)
        oldest = parameters.get("oldest")
        latest = parameters.get("latest")
        inclusive = parameters.get("inclusive", True)
        cursor = parameters.get("cursor")
        
        if not channel:
            raise SlackAPIError("Missing required parameter: channel")
        
        url = f"{self.base_url}/conversations.history"
        headers = self._prepare_headers(credentials)
        
        params = {
            "channel": channel,
            "limit": limit,
            "inclusive": inclusive
        }
        
        if oldest:
            params["oldest"] = oldest
        if latest:
            params["latest"] = latest
        if cursor:
            params["cursor"] = cursor
        
        response = await self.make_http_request("GET", url, headers=headers, params=params)
        
        if not (200 <= response.status_code < 300):
            self._handle_error(response)
        
        response_data = response.json()
        
        if not response_data.get("ok"):
            raise SlackAPIError(f"Slack API error: {response_data.get('error', 'Unknown error')}")
        
        messages = []
        for msg in response_data.get("messages", []):
            messages.append({
                "ts": msg.get("ts"),
                "user": msg.get("user"),
                "text": msg.get("text"),
                "type": msg.get("type"),
                "subtype": msg.get("subtype"),
                "thread_ts": msg.get("thread_ts"),
                "reply_count": msg.get("reply_count", 0),
                "reactions": msg.get("reactions", [])
            })
        
        return {
            "messages": messages,
            "has_more": response_data.get("has_more", False),
            "next_cursor": response_data.get("response_metadata", {}).get("next_cursor")
        }
    
    async def _set_presence(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """Set user presence."""
        presence = parameters.get("presence", "auto")  # auto, away
        
        if presence not in ["auto", "away"]:
            raise SlackAPIError("Invalid presence value. Must be 'auto' or 'away'")
        
        url = f"{self.base_url}/users.setPresence"
        headers = self._prepare_headers(credentials)
        
        payload = {"presence": presence}
        
        response = await self.make_http_request("POST", url, headers=headers, json_data=payload)
        
        if not (200 <= response.status_code < 300):
            self._handle_error(response)
        
        response_data = response.json()
        
        if not response_data.get("ok"):
            raise SlackAPIError(f"Slack API error: {response_data.get('error', 'Unknown error')}")
        
        return {
            "presence": presence,
            "success": True
        }