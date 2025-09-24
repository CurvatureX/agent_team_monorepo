"""
Slack MCP API - minimal MCP tools backed by SlackSDK
"""

import time
from typing import Any, Dict

from app.models import MCPContentItem, MCPInvokeResponse, MCPTool, MCPToolsResponse
from app.utils.logger import get_logger

from shared.sdks import SlackSDK

logger = get_logger(__name__)


class SlackMCPService:
    def __init__(self) -> None:
        self.sdk = SlackSDK()

    def get_available_tools(self) -> MCPToolsResponse:
        tools = [
            MCPTool(
                name="slack_send_message",
                description="Send a message to a Slack channel or user (bot token)",
                inputSchema={
                    "type": "object",
                    "required": ["access_token", "channel", "text"],
                    "properties": {
                        "access_token": {
                            "type": "string",
                            "description": "Slack OAuth access token",
                        },
                        "channel": {"type": "string", "description": "Channel ID or user ID"},
                        "text": {"type": "string"},
                        "thread_ts": {"type": "string"},
                    },
                },
                category="slack",
                tags=["message", "send"],
            ),
            MCPTool(
                name="slack_list_channels",
                description="List Slack channels accessible to the user",
                inputSchema={
                    "type": "object",
                    "required": ["access_token"],
                    "properties": {
                        "access_token": {"type": "string"},
                        "types": {"type": "string", "default": "public_channel,private_channel"},
                        "limit": {"type": "integer", "default": 100},
                    },
                },
                category="slack",
                tags=["channel", "list"],
            ),
            MCPTool(
                name="slack_get_user_info",
                description="Get Slack user information",
                inputSchema={
                    "type": "object",
                    "required": ["access_token", "user"],
                    "properties": {
                        "access_token": {"type": "string"},
                        "user": {"type": "string", "description": "User ID"},
                    },
                },
                category="slack",
                tags=["user", "info"],
            ),
        ]
        return MCPToolsResponse(
            tools=tools, total_count=len(tools), available_count=len(tools), categories=["slack"]
        )

    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        info = {
            "slack_send_message": {
                "name": "slack_send_message",
                "description": "Send a message to a channel or user (bot token)",
                "category": "slack",
                "available": True,
            },
            "slack_list_channels": {
                "name": "slack_list_channels",
                "description": "List workspace channels",
                "category": "slack",
                "available": True,
            },
            "slack_get_user_info": {
                "name": "slack_get_user_info",
                "description": "Get Slack user information",
                "category": "slack",
                "available": True,
            },
        }
        return info.get(
            tool_name,
            {
                "name": tool_name,
                "available": False,
                "description": "Tool not found",
                "category": "slack",
            },
        )

    def health_check(self):
        from app.models import MCPHealthCheck

        return MCPHealthCheck(
            healthy=True,
            version="1.0.0",
            available_tools=["slack_send_message", "slack_list_channels", "slack_get_user_info"],
            timestamp=int(time.time()),
        )

    async def invoke_tool(self, tool_name: str, params: Dict[str, Any]) -> MCPInvokeResponse:
        start = time.time()
        try:
            credentials = {"access_token": params.get("access_token")}
            op_params = {k: v for k, v in params.items() if k != "access_token"}

            api_resp = await self.sdk.call_operation(tool_name, op_params, credentials)
            if not api_resp.success:
                resp = MCPInvokeResponse(
                    content=[
                        MCPContentItem(
                            type="text", text=str(api_resp.error or "Slack operation failed")
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
            resp._execution_time_ms = round((time.time() - start) * 1000, 2)
            return resp
        except Exception as e:
            resp = MCPInvokeResponse(
                content=[
                    MCPContentItem(type="text", text=f"Slack tool execution failed: {str(e)}")
                ],
                isError=True,
            )
            resp._tool_name = tool_name
            resp._execution_time_ms = round((time.time() - start) * 1000, 2)
            return resp


slack_mcp_service = SlackMCPService()
