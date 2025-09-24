"""
Gmail MCP API - Tools backed by EmailSDK (SMTP/OAuth capable)
"""

import time
from typing import Any, Dict

from app.models import MCPContentItem, MCPInvokeResponse, MCPTool, MCPToolsResponse
from app.utils.logger import get_logger

from shared.sdks import EmailSDK

logger = get_logger(__name__)


class GmailMCPService:
    def __init__(self) -> None:
        self.sdk = EmailSDK()

    def get_available_tools(self) -> MCPToolsResponse:
        tools = [
            MCPTool(
                name="gmail_send_email",
                description="Send an email via Gmail SMTP or OAuth credentials",
                inputSchema={
                    "type": "object",
                    "required": ["to", "subject", "body"],
                    "properties": {
                        # Credentials can be SMTP or OAuth; pass via credentials object
                        "credentials": {
                            "type": "object",
                            "description": "SMTP or OAuth credentials (e.g., username/password or access_token)",
                        },
                        # Message fields
                        "to": {"type": "string"},
                        "cc": {"type": "string"},
                        "bcc": {"type": "string"},
                        "subject": {"type": "string"},
                        "body": {"type": "string"},
                        "html_body": {"type": "string"},
                        "from_email": {"type": "string"},
                        # Optional SMTP specifics if not using OAuth
                        "smtp_server": {"type": "string", "default": "smtp.gmail.com"},
                        "smtp_port": {"type": "integer", "default": 587},
                        "username": {"type": "string"},
                        "password": {"type": "string"},
                    },
                },
                category="gmail",
                tags=["email", "send"],
            ),
        ]
        return MCPToolsResponse(
            tools=tools, total_count=len(tools), available_count=len(tools), categories=["gmail"]
        )

    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        info = {
            "gmail_send_email": {
                "name": "gmail_send_email",
                "description": "Send an email via Gmail SMTP or OAuth credentials",
                "category": "gmail",
                "available": True,
            }
        }
        return info.get(
            tool_name,
            {
                "name": tool_name,
                "available": False,
                "description": "Tool not found",
                "category": "gmail",
            },
        )

    def health_check(self):
        import time

        from app.models import MCPHealthCheck

        return MCPHealthCheck(
            healthy=True,
            version="1.0.0",
            available_tools=["gmail_send_email"],
            timestamp=int(time.time()),
        )

    async def invoke_tool(self, tool_name: str, params: Dict[str, Any]) -> MCPInvokeResponse:
        start = time.time()
        try:
            if tool_name != "gmail_send_email":
                return MCPInvokeResponse(
                    content=[
                        MCPContentItem(type="text", text=f"Error: Tool '{tool_name}' not found")
                    ],
                    isError=True,
                )

            # Derive credentials
            credentials = params.get("credentials") or {}
            # Allow direct SMTP fields at root for convenience
            for key in ("smtp_server", "smtp_port", "username", "password", "access_token"):
                if key in params and key not in credentials:
                    credentials[key] = params[key]

            message_params = {
                k: v
                for k, v in params.items()
                if k
                not in (
                    "credentials",
                    "smtp_server",
                    "smtp_port",
                    "username",
                    "password",
                    "access_token",
                )
            }

            # Call using MCP-style op name
            api_resp = await self.sdk.call_operation(tool_name, message_params, credentials)
            if not api_resp.success:
                resp = MCPInvokeResponse(
                    content=[
                        MCPContentItem(
                            type="text", text=str(api_resp.error or "Gmail operation failed")
                        )
                    ],
                    isError=True,
                )
            else:
                resp = MCPInvokeResponse(
                    content=[
                        MCPContentItem(type="text", text=f"gmail_send_email executed successfully")
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
                    MCPContentItem(type="text", text=f"Gmail tool execution failed: {str(e)}")
                ],
                isError=True,
            )
            resp._tool_name = tool_name
            resp._execution_time_ms = round((time.time() - start) * 1000, 2)
            return resp


gmail_mcp_service = GmailMCPService()
