"""
Discord MCP API - Tools backed by DiscordSDK
"""

import time
from typing import Any, Dict

from app.models import MCPContentItem, MCPInvokeResponse, MCPTool, MCPToolsResponse
from app.utils.logger import get_logger

from shared.sdks import DiscordSDK

logger = get_logger(__name__)


class DiscordMCPService:
    def __init__(self) -> None:
        self.sdk = DiscordSDK()

    def get_available_tools(self) -> MCPToolsResponse:
        tools = [
            MCPTool(
                name="discord_get_server_info",
                description="Get information about a Discord server (guild)",
                inputSchema={
                    "type": "object",
                    "required": ["bot_token", "server_id"],
                    "properties": {
                        "bot_token": {"type": "string", "description": "Discord bot token"},
                        "server_id": {"type": "string", "description": "Discord server (guild) ID"},
                    },
                },
                category="discord",
                tags=["server", "guild", "info"],
            ),
            MCPTool(
                name="discord_list_members",
                description="List members in a Discord server",
                inputSchema={
                    "type": "object",
                    "required": ["bot_token", "server_id"],
                    "properties": {
                        "bot_token": {"type": "string"},
                        "server_id": {"type": "string"},
                        "limit": {"type": "integer", "default": 100},
                    },
                },
                category="discord",
                tags=["server", "members"],
            ),
            MCPTool(
                name="discord_create_text_channel",
                description="Create a text channel in a server",
                inputSchema={
                    "type": "object",
                    "required": ["bot_token", "server_id", "name"],
                    "properties": {
                        "bot_token": {"type": "string"},
                        "server_id": {"type": "string"},
                        "name": {"type": "string"},
                        "category_id": {"type": "string"},
                        "topic": {"type": "string"},
                    },
                },
                category="discord",
                tags=["channel", "create"],
            ),
            MCPTool(
                name="discord_send_message",
                description="Send a message to a channel",
                inputSchema={
                    "type": "object",
                    "required": ["bot_token", "channel_id", "content"],
                    "properties": {
                        "bot_token": {"type": "string"},
                        "channel_id": {"type": "string"},
                        "content": {"type": "string"},
                    },
                },
                category="discord",
                tags=["message", "send"],
            ),
            MCPTool(
                name="discord_read_messages",
                description="Read recent messages from a channel",
                inputSchema={
                    "type": "object",
                    "required": ["bot_token", "channel_id"],
                    "properties": {
                        "bot_token": {"type": "string"},
                        "channel_id": {"type": "string"},
                        "limit": {"type": "integer", "default": 50},
                    },
                },
                category="discord",
                tags=["message", "read"],
            ),
            MCPTool(
                name="discord_add_reaction",
                description="Add a reaction to a message",
                inputSchema={
                    "type": "object",
                    "required": ["bot_token", "channel_id", "message_id", "emoji"],
                    "properties": {
                        "bot_token": {"type": "string"},
                        "channel_id": {"type": "string"},
                        "message_id": {"type": "string"},
                        "emoji": {"type": "string"},
                    },
                },
                category="discord",
                tags=["reaction", "message"],
            ),
            MCPTool(
                name="discord_add_multiple_reactions",
                description="Add multiple reactions to a message",
                inputSchema={
                    "type": "object",
                    "required": ["bot_token", "channel_id", "message_id", "emojis"],
                    "properties": {
                        "bot_token": {"type": "string"},
                        "channel_id": {"type": "string"},
                        "message_id": {"type": "string"},
                        "emojis": {"type": "array", "items": {"type": "string"}},
                    },
                },
                category="discord",
                tags=["reaction", "bulk"],
            ),
            MCPTool(
                name="discord_remove_reaction",
                description="Remove the bot's reaction from a message",
                inputSchema={
                    "type": "object",
                    "required": ["bot_token", "channel_id", "message_id", "emoji"],
                    "properties": {
                        "bot_token": {"type": "string"},
                        "channel_id": {"type": "string"},
                        "message_id": {"type": "string"},
                        "emoji": {"type": "string"},
                    },
                },
                category="discord",
                tags=["reaction", "remove"],
            ),
            MCPTool(
                name="discord_get_user_info",
                description="Get Discord user info",
                inputSchema={
                    "type": "object",
                    "required": ["bot_token", "user_id"],
                    "properties": {
                        "bot_token": {"type": "string"},
                        "user_id": {"type": "string"},
                    },
                },
                category="discord",
                tags=["user", "info"],
            ),
        ]

        return MCPToolsResponse(
            tools=tools, total_count=len(tools), available_count=len(tools), categories=["discord"]
        )

    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        info = {
            t.name: {
                "name": t.name,
                "description": t.description,
                "category": "discord",
                "available": True,
            }
            for t in self.get_available_tools().tools
        }
        return info.get(
            tool_name,
            {
                "name": tool_name,
                "available": False,
                "description": "Tool not found",
                "category": "discord",
            },
        )

    def health_check(self):
        import time

        from app.models import MCPHealthCheck

        return MCPHealthCheck(
            healthy=True,
            version="1.0.0",
            available_tools=[t.name for t in self.get_available_tools().tools],
            timestamp=int(time.time()),
        )

    async def invoke_tool(self, tool_name: str, params: Dict[str, Any]) -> MCPInvokeResponse:
        start_time = time.time()
        try:
            # Extract credentials and remove from params for operation call
            credentials = {"bot_token": params.get("bot_token")}
            op_params = {k: v for k, v in params.items() if k != "bot_token"}

            api_resp = await self.sdk.call_operation(tool_name, op_params, credentials)
            if not api_resp.success:
                resp = MCPInvokeResponse(
                    content=[
                        MCPContentItem(
                            type="text", text=str(api_resp.error or "Discord operation failed")
                        )
                    ],
                    isError=True,
                )
            else:
                resp = MCPInvokeResponse(
                    content=[
                        MCPContentItem(type="text", text=f"{tool_name} executed successfully")
                    ],
                    isError=False,
                    structuredContent=api_resp.data,
                )
            resp._tool_name = tool_name
            resp._execution_time_ms = round((time.time() - start_time) * 1000, 2)
            return resp
        except Exception as e:
            resp = MCPInvokeResponse(
                content=[
                    MCPContentItem(type="text", text=f"Discord tool execution failed: {str(e)}")
                ],
                isError=True,
            )
            resp._tool_name = tool_name
            resp._execution_time_ms = round((time.time() - start_time) * 1000, 2)
            return resp


# Singleton service
discord_mcp_service = DiscordMCPService()
