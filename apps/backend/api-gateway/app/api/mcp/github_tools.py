"""
GitHub MCP API - minimal MCP tools backed by GitHub OAuth2 SDK
"""

import time
from typing import Any, Dict

from app.models import MCPContentItem, MCPInvokeResponse, MCPTool, MCPToolsResponse
from app.utils.logger import get_logger

from shared.sdks import GitHubSDK

logger = get_logger(__name__)


class GitHubMCPService:
    def __init__(self) -> None:
        self.sdk = GitHubSDK() if callable(GitHubSDK) else None

    def get_available_tools(self) -> MCPToolsResponse:
        tools = [
            MCPTool(
                name="github_get_repo",
                description="Get repository details",
                inputSchema={
                    "type": "object",
                    "required": ["access_token", "repository"],
                    "properties": {
                        "access_token": {"type": "string"},
                        "repository": {"type": "string", "description": "owner/repo"},
                    },
                },
                category="github",
                tags=["repo", "info"],
            ),
            MCPTool(
                name="github_list_repos",
                description="List authenticated user's repositories",
                inputSchema={
                    "type": "object",
                    "required": ["access_token"],
                    "properties": {
                        "access_token": {"type": "string"},
                    },
                },
                category="github",
                tags=["repo", "list"],
            ),
        ]
        return MCPToolsResponse(
            tools=tools, total_count=len(tools), available_count=len(tools), categories=["github"]
        )

    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        info = {
            "github_get_repo": {
                "name": "github_get_repo",
                "description": "Get repository details",
                "category": "github",
                "available": True,
            },
            "github_list_repos": {
                "name": "github_list_repos",
                "description": "List authenticated user's repositories",
                "category": "github",
                "available": True,
            },
        }
        return info.get(
            tool_name,
            {
                "name": tool_name,
                "available": False,
                "description": "Tool not found",
                "category": "github",
            },
        )

    def health_check(self):
        import time

        from app.models import MCPHealthCheck

        return MCPHealthCheck(
            healthy=True,
            version="1.0.0",
            available_tools=["github_get_repo", "github_list_repos"],
            timestamp=int(time.time()),
        )

    async def invoke_tool(self, tool_name: str, params: Dict[str, Any]) -> MCPInvokeResponse:
        start = time.time()
        try:
            if self.sdk is None:
                return MCPInvokeResponse(
                    content=[MCPContentItem(type="text", text="GitHub SDK not available")],
                    isError=True,
                )

            credentials = {"access_token": params.get("access_token")}
            op_params = {k: v for k, v in params.items() if k != "access_token"}

            api_resp = await self.sdk.call_operation(tool_name, op_params, credentials)

            if not api_resp.success:
                resp = MCPInvokeResponse(
                    content=[
                        MCPContentItem(
                            type="text", text=str(api_resp.error or "GitHub operation failed")
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
                    MCPContentItem(type="text", text=f"GitHub tool execution failed: {str(e)}")
                ],
                isError=True,
            )
            resp._tool_name = tool_name
            resp._execution_time_ms = round((time.time() - start) * 1000, 2)
            return resp


github_mcp_service = GitHubMCPService()
