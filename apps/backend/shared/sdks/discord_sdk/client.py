"""
Discord API client implemented as an SDK for use by MCP services.

Implements a subset of operations commonly provided by reference Discord MCP servers:
- get_server_info
- list_members
- create_text_channel
- send_message
- read_messages
- add_reaction
- add_multiple_reactions
- remove_reaction
- get_user_info
"""

from typing import Any, Dict, List, Optional
from urllib.parse import quote

from ..base import APIResponse, BaseSDK, OAuth2Config


class DiscordAPIError(Exception):
    pass


class DiscordSDK(BaseSDK):
    @property
    def base_url(self) -> str:
        return "https://discord.com/api/v10"

    @property
    def supported_operations(self) -> Dict[str, str]:
        base = {
            "get_server_info": "Get Discord guild (server) information",
            "list_members": "List members in a Discord server",
            "create_text_channel": "Create a text channel in a server",
            "send_message": "Send a message to a channel",
            "read_messages": "Read recent messages from a channel",
            "add_reaction": "Add a reaction to a message",
            "add_multiple_reactions": "Add multiple reactions to a message",
            "remove_reaction": "Remove the bot's reaction from a message",
            "get_user_info": "Get information for a Discord user",
        }
        # Also accept MCP tool names with 'discord_' prefix
        return {**base, **{f"discord_{k}": v for k, v in base.items()}}

    def get_oauth2_config(self) -> OAuth2Config:
        # Discord SDK here uses bot token auth; returning a placeholder OAuth2Config
        return OAuth2Config(
            client_id="",
            client_secret="",
            auth_url="",
            token_url="",
        )

    def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        return bool(credentials.get("bot_token"))

    async def call_operation(
        self, operation: str, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> APIResponse:
        if not self.validate_credentials(credentials):
            return APIResponse(
                success=False,
                error="Invalid credentials: missing bot_token",
                provider="discord",
                operation=operation,
            )

        if operation not in self.supported_operations:
            return APIResponse(
                success=False,
                error=f"Unsupported operation: {operation}",
                provider="discord",
                operation=operation,
            )

        handler_map = {
            "get_server_info": self._get_server_info,
            "list_members": self._list_members,
            "create_text_channel": self._create_text_channel,
            "send_message": self._send_message,
            "read_messages": self._read_messages,
            "add_reaction": self._add_reaction,
            "add_multiple_reactions": self._add_multiple_reactions,
            "remove_reaction": self._remove_reaction,
            "get_user_info": self._get_user_info,
        }

        # Normalize prefixed operation names
        op = operation
        if op.startswith("discord_"):
            op = op[len("discord_") :]
        try:
            result = await handler_map[op](parameters, credentials)
            return APIResponse(success=True, data=result, provider="discord", operation=operation)
        except Exception as e:
            self.logger.error(f"Discord {operation} failed: {e}")
            return APIResponse(success=False, error=str(e), provider="discord", operation=operation)

    def _auth_headers(self, credentials: Dict[str, str]) -> Dict[str, str]:
        bot_token = credentials.get("bot_token", "")
        return self.prepare_headers(
            credentials={}, extra_headers={"Authorization": f"Bot {bot_token}"}
        )

    async def _get_server_info(
        self, params: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        server_id = params.get("server_id")
        if not server_id:
            raise DiscordAPIError("Missing required parameter: server_id")
        url = f"{self.base_url}/guilds/{server_id}"
        headers = self._auth_headers(credentials)
        response = await self.make_http_request(
            "GET", url, headers=headers, params={"with_counts": "true"}
        )
        if not (200 <= response.status_code < 300):
            self.handle_http_error(response, "get_server_info")
        guild = response.json()
        return {
            "id": guild.get("id"),
            "name": guild.get("name"),
            "owner_id": guild.get("owner_id"),
            "member_count": guild.get("approximate_member_count"),
            "presence_count": guild.get("approximate_presence_count"),
            "icon": guild.get("icon"),
            "description": guild.get("description"),
            "premium_tier": guild.get("premium_tier"),
        }

    async def _list_members(
        self, params: Dict[str, Any], credentials: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        server_id = params.get("server_id")
        limit = int(params.get("limit", 100))
        limit = max(1, min(limit, 1000))
        if not server_id:
            raise DiscordAPIError("Missing required parameter: server_id")
        url = f"{self.base_url}/guilds/{server_id}/members"
        headers = self._auth_headers(credentials)
        response = await self.make_http_request(
            "GET", url, headers=headers, params={"limit": str(limit)}
        )
        if not (200 <= response.status_code < 300):
            self.handle_http_error(response, "list_members")
        data = response.json()
        results: List[Dict[str, Any]] = []
        if isinstance(data, list):
            for member in data:
                user = member.get("user", {})
                results.append(
                    {
                        "id": user.get("id"),
                        "username": user.get("username"),
                        "discriminator": user.get("discriminator"),
                        "global_name": user.get("global_name"),
                        "nick": member.get("nick"),
                        "joined_at": member.get("joined_at"),
                        "roles": member.get("roles", []),
                    }
                )
        return results

    async def _create_text_channel(
        self, params: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        server_id = params.get("server_id")
        name = params.get("name")
        category_id = params.get("category_id")
        topic = params.get("topic")
        if not server_id or not name:
            raise DiscordAPIError("Missing required parameters: server_id, name")
        url = f"{self.base_url}/guilds/{server_id}/channels"
        headers = self._auth_headers(credentials)
        payload: Dict[str, Any] = {"name": name, "type": 0}
        if topic:
            payload["topic"] = topic
        if category_id:
            payload["parent_id"] = category_id
        response = await self.make_http_request("POST", url, headers=headers, json_data=payload)
        if not (200 <= response.status_code < 300):
            self.handle_http_error(response, "create_text_channel")
        ch = response.json()
        return {
            "id": ch.get("id"),
            "name": ch.get("name"),
            "topic": ch.get("topic"),
            "parent_id": ch.get("parent_id"),
        }

    async def _send_message(
        self, params: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        channel_id = params.get("channel_id")
        content = params.get("content")
        if not channel_id or not content:
            raise DiscordAPIError("Missing required parameters: channel_id, content")
        url = f"{self.base_url}/channels/{channel_id}/messages"
        headers = self._auth_headers(credentials)
        response = await self.make_http_request(
            "POST", url, headers=headers, json_data={"content": content}
        )
        if not (200 <= response.status_code < 300):
            self.handle_http_error(response, "send_message")
        msg = response.json()
        return {
            "message_id": msg.get("id"),
            "channel_id": msg.get("channel_id"),
            "content_preview": (content[:100] + ("..." if len(content) > 100 else "")),
        }

    async def _read_messages(
        self, params: Dict[str, Any], credentials: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        channel_id = params.get("channel_id")
        limit = int(params.get("limit", 50))
        limit = max(1, min(limit, 100))
        if not channel_id:
            raise DiscordAPIError("Missing required parameter: channel_id")
        url = f"{self.base_url}/channels/{channel_id}/messages"
        headers = self._auth_headers(credentials)
        response = await self.make_http_request(
            "GET", url, headers=headers, params={"limit": str(limit)}
        )
        if not (200 <= response.status_code < 300):
            self.handle_http_error(response, "read_messages")
        data = response.json()
        out: List[Dict[str, Any]] = []
        if isinstance(data, list):
            for m in data:
                author = m.get("author", {})
                reactions = []
                for r in m.get("reactions", []) or []:
                    emoji = r.get("emoji", {})
                    reactions.append(
                        {
                            "name": emoji.get("name"),
                            "id": emoji.get("id"),
                            "count": r.get("count", 0),
                        }
                    )
                out.append(
                    {
                        "id": m.get("id"),
                        "content": m.get("content", ""),
                        "timestamp": m.get("timestamp"),
                        "author": {
                            "id": author.get("id"),
                            "username": author.get("username"),
                            "discriminator": author.get("discriminator"),
                            "global_name": author.get("global_name"),
                            "is_bot": author.get("bot", False),
                        },
                        "reactions": reactions,
                    }
                )
        return out

    async def _add_reaction(
        self, params: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        channel_id = params.get("channel_id")
        message_id = params.get("message_id")
        emoji = params.get("emoji")
        if not channel_id or not message_id or not emoji:
            raise DiscordAPIError("Missing required parameters: channel_id, message_id, emoji")
        enc_emoji = quote(emoji)
        url = (
            f"{self.base_url}/channels/{channel_id}/messages/{message_id}/reactions/{enc_emoji}/@me"
        )
        headers = self._auth_headers(credentials)
        response = await self.make_http_request("PUT", url, headers=headers)
        if response.status_code not in (200, 204):
            self.handle_http_error(response, "add_reaction")
        return {"status": "ok"}

    async def _remove_reaction(
        self, params: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        channel_id = params.get("channel_id")
        message_id = params.get("message_id")
        emoji = params.get("emoji")
        if not channel_id or not message_id or not emoji:
            raise DiscordAPIError("Missing required parameters: channel_id, message_id, emoji")
        enc_emoji = quote(emoji)
        url = (
            f"{self.base_url}/channels/{channel_id}/messages/{message_id}/reactions/{enc_emoji}/@me"
        )
        headers = self._auth_headers(credentials)
        response = await self.make_http_request("DELETE", url, headers=headers)
        if response.status_code not in (200, 204):
            self.handle_http_error(response, "remove_reaction")
        return {"status": "ok"}

    async def _add_multiple_reactions(
        self, params: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        channel_id = params.get("channel_id")
        message_id = params.get("message_id")
        emojis = params.get("emojis", [])
        if not channel_id or not message_id or not emojis:
            raise DiscordAPIError("Missing required parameters: channel_id, message_id, emojis")
        added, errors = [], []
        for e in emojis:
            try:
                await self._add_reaction(
                    {"channel_id": channel_id, "message_id": message_id, "emoji": e}, credentials
                )
                added.append(e)
            except Exception as ex:
                errors.append(f"{e}: {ex}")
        return {"added": added, "errors": errors}

    async def _get_user_info(
        self, params: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        user_id = params.get("user_id")
        if not user_id:
            raise DiscordAPIError("Missing required parameter: user_id")
        url = f"{self.base_url}/users/{user_id}"
        headers = self._auth_headers(credentials)
        response = await self.make_http_request("GET", url, headers=headers)
        if not (200 <= response.status_code < 300):
            self.handle_http_error(response, "get_user_info")
        u = response.json()
        return {
            "id": u.get("id"),
            "username": u.get("username"),
            "discriminator": u.get("discriminator"),
            "global_name": u.get("global_name"),
            "is_bot": u.get("bot", False),
            "avatar": u.get("avatar"),
        }
