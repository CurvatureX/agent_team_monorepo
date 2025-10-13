"""
Ultra-Simple Notion MCP API - Designed for maximum AI usability
超级简化版Notion MCP集成 - 为AI优化设计

Only 3 tools, minimal parameters, maximum clarity:
1. notion_database - List all items in a database (smart defaults)
2. notion_page - Get page content (read-only)
3. notion_search - Search for databases/pages by keywords
"""

import time
from typing import Any, Dict

from app.models import MCPContentItem, MCPHealthCheck, MCPInvokeResponse, MCPTool, MCPToolsResponse
from app.utils.logger import get_logger

from shared.sdks.notion_sdk import (
    NotionAuthError,
    NotionClient,
    NotionObjectNotFoundError,
    NotionRateLimitError,
)

logger = get_logger(__name__)


class SimpleNotionMCPService:
    """Ultra-simple MCP service - 3 tools, easy to use."""

    def get_available_tools(self) -> MCPToolsResponse:
        """Get 3 simple Notion tools optimized for AI."""
        tools = [
            MCPTool(
                name="notion_database",
                description="List all items in a Notion database WITH FULL CONTENT. Returns all pages/items with their complete text content by default. Perfect for 'how many tasks', 'list TODO items with details', 'show database content'. The database_id is auto-injected if configured.",
                category="notion",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "access_token": {
                            "type": "string",
                            "description": "Notion OAuth token (auto-injected)",
                        },
                        "database_id": {
                            "type": "string",
                            "description": "Database ID (auto-injected if default_database_id configured)",
                        },
                        "filter": {
                            "type": "object",
                            "description": "Optional: Notion API filter to narrow results",
                        },
                        "limit": {
                            "type": "integer",
                            "default": 100,
                            "description": "Optional: Max items to return (default 100)",
                        },
                        "include_content": {
                            "type": "boolean",
                            "default": True,
                            "description": "Optional: Include full page content blocks (default: True)",
                        },
                    },
                    "required": ["access_token", "database_id"],
                },
                tags=["database", "list", "query", "content"],
            ),
            MCPTool(
                name="notion_page",
                description="Get full content of a Notion page including all text blocks. Perfect for 'show page content', 'read this page', 'what's in this document'.",
                category="notion",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "access_token": {
                            "type": "string",
                            "description": "Notion OAuth token (auto-injected)",
                        },
                        "page_id": {
                            "type": "string",
                            "description": "Page ID to retrieve",
                        },
                    },
                    "required": ["access_token", "page_id"],
                },
                tags=["page", "read", "content"],
            ),
            MCPTool(
                name="notion_search",
                description="Search for Notion databases or pages by keywords. Use this to find databases/pages when you don't have the ID. Perfect for 'find TODO database', 'search for project pages'.",
                category="notion",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "access_token": {
                            "type": "string",
                            "description": "Notion OAuth token (auto-injected)",
                        },
                        "query": {
                            "type": "string",
                            "description": "Search keywords",
                        },
                        "filter": {
                            "type": "object",
                            "properties": {
                                "object_type": {
                                    "type": "string",
                                    "enum": ["page", "database"],
                                    "description": "Optional: Filter by type",
                                },
                            },
                        },
                        "limit": {
                            "type": "integer",
                            "default": 10,
                            "description": "Optional: Max results (default 10)",
                        },
                    },
                    "required": ["access_token", "query"],
                },
                tags=["search", "find"],
            ),
        ]

        return MCPToolsResponse(
            tools=tools,
            total_count=len(tools),
            available_count=len(tools),
            categories=["notion"],
        )

    async def invoke_tool(self, tool_name: str, params: Dict[str, Any]) -> MCPInvokeResponse:
        """Invoke specified Notion tool."""
        start_time = time.time()

        # Extract access token
        access_token = params.get("access_token")
        if not access_token:
            response = MCPInvokeResponse(
                content=[
                    MCPContentItem(
                        type="text",
                        text="Error: access_token is required",
                    )
                ],
                isError=True,
            )
            response._tool_name = tool_name
            response._execution_time_ms = round((time.time() - start_time) * 1000, 2)
            return response

        # Create Notion client
        try:
            client = NotionClient(auth_token=access_token)
        except Exception as e:
            response = MCPInvokeResponse(
                content=[MCPContentItem(type="text", text=f"Error: {str(e)}")],
                isError=True,
            )
            response._tool_name = tool_name
            response._execution_time_ms = round((time.time() - start_time) * 1000, 2)
            return response

        try:
            # Route to correct handler
            if tool_name == "notion_database":
                result = await self._query_database(client, params)
            elif tool_name == "notion_page":
                result = await self._get_page(client, params)
            elif tool_name == "notion_search":
                result = await self._search(client, params)
            else:
                response = MCPInvokeResponse(
                    content=[MCPContentItem(type="text", text=f"Unknown tool: {tool_name}")],
                    isError=True,
                )
                response._tool_name = tool_name
                response._execution_time_ms = round((time.time() - start_time) * 1000, 2)
                return response

            # Success response
            response = MCPInvokeResponse(
                content=[MCPContentItem(type="text", text=f"✅ {tool_name} executed successfully")],
                isError=False,
                structuredContent=result,
            )
            response._tool_name = tool_name
            response._execution_time_ms = round((time.time() - start_time) * 1000, 2)
            return response

        except NotionAuthError as e:
            error_msg = f"Authentication failed: {str(e)}"
            logger.error(error_msg)
        except NotionRateLimitError as e:
            error_msg = f"Rate limit exceeded: {str(e)}"
            logger.error(error_msg)
        except NotionObjectNotFoundError as e:
            error_msg = f"Not found: {str(e)}"
            logger.error(error_msg)
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            logger.error(error_msg, exc_info=True)

        # Error response
        response = MCPInvokeResponse(
            content=[MCPContentItem(type="text", text=error_msg)],
            isError=True,
        )
        response._tool_name = tool_name
        response._execution_time_ms = round((time.time() - start_time) * 1000, 2)

        # Always close client
        if "client" in locals():
            await client.close()

        return response

    async def _query_database(self, client: NotionClient, params: Dict[str, Any]) -> Dict[str, Any]:
        """Query database - returns all items with full content."""
        database_id = params.get("database_id")
        filter_conditions = params.get("filter")
        limit = params.get("limit", 100)
        include_content = params.get("include_content", True)  # Default to True

        # Query database
        results = await client.query_database(
            database_id=database_id,
            filter_conditions=filter_conditions,
            page_size=limit,
        )

        # Extract pages with full content
        pages = []
        for page in results.get("pages", []):
            page_data = {
                "id": page.id,
                "title": self._extract_title(page),
                "properties": page.properties,
                "url": getattr(page, "url", None),
            }

            # Fetch full content blocks for each page
            if include_content:
                try:
                    children = await client.get_block_children(page.id)
                    page_data["content"] = [
                        {
                            "id": child.id,
                            "type": str(
                                child.type.value if hasattr(child.type, "value") else child.type
                            ),
                            "content": child.content if hasattr(child, "content") else None,
                        }
                        for child in children.get("blocks", [])
                    ]
                except Exception as e:
                    logger.warning(f"Failed to fetch content for page {page.id}: {str(e)}")
                    page_data["content"] = []

            pages.append(page_data)

        return {
            "action": "query",
            "database_id": database_id,
            "pages": pages,
            "total_count": len(pages),
            "has_more": results.get("has_more", False),
        }

    async def _get_page(self, client: NotionClient, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get page content - read-only."""
        page_id = params.get("page_id")

        # Get page metadata
        page = await client.get_page(page_id)

        # Get page content blocks
        children = await client.get_block_children(page_id)
        content = [
            {
                "id": child.id,
                "type": str(child.type.value if hasattr(child.type, "value") else child.type),
                "content": child.content if hasattr(child, "content") else None,
            }
            for child in children.get("blocks", [])
        ]

        return {
            "action": "get",
            "page_id": page_id,
            "title": self._extract_title(page),
            "url": page.url,
            "content": content,
        }

    async def _search(self, client: NotionClient, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for databases/pages by keywords."""
        query = params.get("query")
        filter_config = params.get("filter", {})
        limit = params.get("limit", 10)

        # Build filter
        filter_conditions = None
        if filter_config.get("object_type"):
            filter_conditions = {
                "value": filter_config["object_type"],
                "property": "object",
            }

        # Search
        search_results = await client.search(
            query=query,
            filter_conditions=filter_conditions,
            page_size=limit,
        )

        # Extract results
        results = []
        for item in search_results["results"]:
            results.append(
                {
                    "id": getattr(item, "id", "unknown"),
                    "object": getattr(item, "object", "unknown"),
                    "title": self._extract_title(item),
                    "url": getattr(item, "url", None),
                }
            )

        return {
            "query": query,
            "results": results,
            "total_count": len(results),
        }

    def _extract_title(self, notion_object) -> str:
        """Extract title from Notion object."""
        try:
            # Try direct title attribute
            if hasattr(notion_object, "title") and notion_object.title:
                if isinstance(notion_object.title, list) and len(notion_object.title) > 0:
                    first_title = notion_object.title[0]
                    if isinstance(first_title, dict):
                        return first_title.get(
                            "plain_text", first_title.get("text", {}).get("content", "Untitled")
                        )

            # Try properties
            if hasattr(notion_object, "properties") and notion_object.properties:
                for prop_name, prop_value in notion_object.properties.items():
                    if isinstance(prop_value, dict) and prop_value.get("type") == "title":
                        title_list = prop_value.get("title", [])
                        if title_list and len(title_list) > 0:
                            first_item = title_list[0]
                            if isinstance(first_item, dict):
                                return first_item.get(
                                    "plain_text",
                                    first_item.get("text", {}).get("content", "Untitled"),
                                )

            return "Untitled"
        except Exception:
            return "Untitled"

    def health_check(self) -> MCPHealthCheck:
        """Health check."""
        return MCPHealthCheck(
            healthy=True,
            version="4.0.0-simple",
            available_tools=["notion_database", "notion_page", "notion_search"],
            timestamp=int(time.time()),
            error=None,
        )


# Initialize simple service
simple_notion_mcp_service = SimpleNotionMCPService()
