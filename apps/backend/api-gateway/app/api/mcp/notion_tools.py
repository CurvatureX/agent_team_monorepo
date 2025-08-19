"""
Notion MCP API routes - Model Context Protocol endpoints for Notion integration
支持API Key认证的Notion MCP工具调用端点 - 使用参数传递访问令牌
"""

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.dependencies import MCPDeps, get_tool_name, require_scope
from app.exceptions import ServiceUnavailableError, ValidationError
from app.models import (
    MCPContentItem,
    MCPErrorResponse,
    MCPHealthCheck,
    MCPInvokeRequest,
    MCPInvokeResponse,
    MCPTool,
    MCPToolsResponse,
)
from app.utils.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from shared.sdks.notion_sdk import (
    NotionAPIError,
    NotionAuthError,
    NotionClient,
    NotionObjectNotFoundError,
    NotionRateLimitError,
    NotionValidationError,
)

logger = get_logger(__name__)
router = APIRouter()


class NotionMCPService:
    """MCP service for Notion operations with parameter-based authentication."""

    def __init__(self):
        # No global client - create per-request with user's token
        pass

    def get_available_tools(self) -> MCPToolsResponse:
        """Get available Notion tools."""
        tools = [
            MCPTool(
                name="search_notion",
                description="Search across Notion pages and databases using text query",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "access_token": {
                            "type": "string",
                            "description": "Notion integration access token",
                        },
                        "query": {
                            "type": "string",
                            "description": "Search query text",
                        },
                        "page_size": {
                            "type": "integer",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 100,
                            "description": "Number of results to return (1-100)",
                        },
                        "filter_type": {
                            "type": "string",
                            "enum": ["page", "database"],
                            "description": "Filter results by object type (optional)",
                        },
                    },
                    "required": ["access_token", "query"],
                },
                category="notion",
                tags=["search", "pages", "databases"],
            ),
            MCPTool(
                name="get_notion_page",
                description="Retrieve detailed information about a specific Notion page",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "access_token": {
                            "type": "string",
                            "description": "Notion integration access token",
                        },
                        "page_id": {
                            "type": "string",
                            "description": "Notion page ID",
                        },
                        "include_children": {
                            "type": "boolean",
                            "default": False,
                            "description": "Include page content blocks",
                        },
                    },
                    "required": ["access_token", "page_id"],
                },
                category="notion",
                tags=["page", "content"],
            ),
            MCPTool(
                name="create_notion_page",
                description="Create a new page in Notion",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "access_token": {
                            "type": "string",
                            "description": "Notion integration access token",
                        },
                        "parent_id": {
                            "type": "string",
                            "description": "Parent page or database ID",
                        },
                        "title": {
                            "type": "string",
                            "description": "Page title",
                        },
                        "content": {
                            "type": "string",
                            "description": "Page content as plain text",
                        },
                        "parent_type": {
                            "type": "string",
                            "enum": ["page", "database"],
                            "default": "page",
                            "description": "Type of parent object",
                        },
                    },
                    "required": ["access_token", "parent_id", "title"],
                },
                category="notion",
                tags=["create", "page"],
            ),
            MCPTool(
                name="query_notion_database",
                description="Query a Notion database with filters and sorting",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "access_token": {
                            "type": "string",
                            "description": "Notion integration access token",
                        },
                        "database_id": {
                            "type": "string",
                            "description": "Notion database ID",
                        },
                        "page_size": {
                            "type": "integer",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 100,
                            "description": "Number of results to return",
                        },
                        "filter_property": {
                            "type": "string",
                            "description": "Property name to filter by (optional)",
                        },
                        "filter_value": {
                            "type": "string",
                            "description": "Value to filter for (optional)",
                        },
                    },
                    "required": ["access_token", "database_id"],
                },
                category="notion",
                tags=["database", "query", "filter"],
            ),
            MCPTool(
                name="get_notion_database",
                description="Get information about a Notion database structure",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "access_token": {
                            "type": "string",
                            "description": "Notion integration access token",
                        },
                        "database_id": {
                            "type": "string",
                            "description": "Notion database ID",
                        },
                    },
                    "required": ["access_token", "database_id"],
                },
                category="notion",
                tags=["database", "schema"],
            ),
            MCPTool(
                name="update_notion_page",
                description="Update properties and content of an existing Notion page with granular block control",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "access_token": {
                            "type": "string",
                            "description": "Notion integration access token",
                        },
                        "page_id": {
                            "type": "string",
                            "description": "Notion page ID to update",
                        },
                        "properties": {
                            "type": "object",
                            "description": "Page properties to update (e.g., title, tags, status)",
                        },
                        "block_operations": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "operation": {
                                        "type": "string",
                                        "enum": ["update", "append", "insert", "delete"],
                                        "description": "Type of operation to perform",
                                    },
                                    "block_id": {
                                        "type": "string",
                                        "description": "Block ID (required for update/delete, optional for insert position)",
                                    },
                                    "block_data": {
                                        "type": "object",
                                        "description": "Block content (required for update/append/insert)",
                                    },
                                    "position": {
                                        "type": "string",
                                        "enum": ["before", "after"],
                                        "description": "Position for insert operation relative to block_id",
                                    },
                                },
                                "required": ["operation"],
                            },
                            "description": "Array of block operations to perform",
                        },
                        "append_blocks": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "Blocks to append at the end of the page (simplified version)",
                        },
                    },
                    "required": ["access_token", "page_id"],
                },
                category="notion",
                tags=["update", "page", "modify", "blocks"],
            ),
        ]

        # All tools are always available - validity checked per-request with token
        available_count = len(tools)

        return MCPToolsResponse(
            tools=tools,
            total_count=len(tools),
            available_count=available_count,
            categories=["notion"],
        )

    async def invoke_tool(self, tool_name: str, params: Dict[str, Any]) -> MCPInvokeResponse:
        """Invoke specified Notion tool with user-provided access token."""
        start_time = time.time()

        # Extract access token from parameters
        access_token = params.get("access_token")
        if not access_token:
            response = MCPInvokeResponse(
                content=[
                    MCPContentItem(
                        type="text",
                        text="Error: access_token parameter is required for Notion tools.",
                    )
                ],
                isError=True,
            )
            response._tool_name = tool_name
            response._execution_time_ms = round((time.time() - start_time) * 1000, 2)
            return response

        # Create client with user's token
        try:
            client = NotionClient(auth_token=access_token)
        except Exception as e:
            response = MCPInvokeResponse(
                content=[
                    MCPContentItem(
                        type="text", text=f"Error: Failed to create Notion client: {str(e)}"
                    )
                ],
                isError=True,
            )
            response._tool_name = tool_name
            response._execution_time_ms = round((time.time() - start_time) * 1000, 2)
            return response

        try:
            if tool_name == "search_notion":
                result = await self._search_notion(client, params)
            elif tool_name == "get_notion_page":
                result = await self._get_notion_page(client, params)
            elif tool_name == "create_notion_page":
                result = await self._create_notion_page(client, params)
            elif tool_name == "query_notion_database":
                result = await self._query_notion_database(client, params)
            elif tool_name == "get_notion_database":
                result = await self._get_notion_database(client, params)
            elif tool_name == "update_notion_page":
                result = await self._update_notion_page(client, params)
            else:
                response = MCPInvokeResponse(
                    content=[
                        MCPContentItem(type="text", text=f"Error: Tool '{tool_name}' not found")
                    ],
                    isError=True,
                )
                response._tool_name = tool_name
                response._execution_time_ms = round((time.time() - start_time) * 1000, 2)
                return response

            # Convert result to MCP-compliant content format
            content = [
                MCPContentItem(type="text", text=f"Tool '{tool_name}' executed successfully")
            ]

            response = MCPInvokeResponse(content=content, isError=False, structuredContent=result)
            response._tool_name = tool_name
            response._execution_time_ms = round((time.time() - start_time) * 1000, 2)
            return response

        except NotionAuthError as e:
            error_msg = f"Notion authentication failed: {str(e)}"
            logger.error(error_msg)
            response = MCPInvokeResponse(
                content=[MCPContentItem(type="text", text=error_msg)],
                isError=True,
            )
        except NotionRateLimitError as e:
            error_msg = f"Notion rate limit exceeded: {str(e)}"
            logger.error(error_msg)
            response = MCPInvokeResponse(
                content=[MCPContentItem(type="text", text=error_msg)],
                isError=True,
            )
        except NotionObjectNotFoundError as e:
            error_msg = f"Notion object not found: {str(e)}"
            logger.error(error_msg)
            response = MCPInvokeResponse(
                content=[MCPContentItem(type="text", text=error_msg)],
                isError=True,
            )
        except Exception as e:
            error_msg = f"Tool execution failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            response = MCPInvokeResponse(
                content=[MCPContentItem(type="text", text=error_msg)],
                isError=True,
            )
        finally:
            # Always close the client
            if "client" in locals():
                await client.close()

        response._tool_name = tool_name
        response._execution_time_ms = round((time.time() - start_time) * 1000, 2)
        return response

    async def _search_notion(self, client: NotionClient, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search Notion pages and databases."""
        query = params.get("query")
        page_size = params.get("page_size", 10)
        filter_type = params.get("filter_type")

        filter_conditions = None
        if filter_type:
            filter_conditions = {"value": filter_type, "property": "object"}

        results = await client.search(
            query=query,
            filter_conditions=filter_conditions,
            page_size=page_size,
        )

        # Convert Notion objects to serializable format
        serialized_results = []
        for result in results["results"]:
            if hasattr(result, "to_dict"):
                serialized_results.append(result.to_dict())
            else:
                # Fallback for basic info
                serialized_results.append(
                    {
                        "id": getattr(result, "id", "unknown"),
                        "object": getattr(result, "object", "unknown"),
                        "title": self._extract_title(result),
                        "url": getattr(result, "url", None),
                    }
                )

        return {
            "query": query,
            "results": serialized_results,
            "total_count": results["total_count"],
            "has_more": results["has_more"],
        }

    async def _get_notion_page(
        self, client: NotionClient, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get detailed page information."""
        page_id = params.get("page_id")
        include_children = params.get("include_children", False)

        page = await client.get_page(page_id)

        result = (
            page.to_dict()
            if hasattr(page, "to_dict")
            else {
                "id": page.id,
                "object": page.object,
                "title": self._extract_title(page),
                "url": page.url,
                "properties": page.properties,
            }
        )

        if include_children:
            children = await client.get_block_children(page_id)
            result["children"] = [
                child.to_dict()
                if hasattr(child, "to_dict")
                else {
                    "id": getattr(child, "id", "unknown"),
                    "type": getattr(child, "type", "unknown"),
                }
                for child in children["blocks"]
            ]

        return result

    async def _create_notion_page(
        self, client: NotionClient, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new Notion page."""
        parent_id = params.get("parent_id")
        title = params.get("title")
        content = params.get("content", "")
        parent_type = params.get("parent_type", "page")

        # Prepare parent reference
        if parent_type == "database":
            parent = {"database_id": parent_id}
            # For database pages, title is a property
            properties = {
                "Name": {  # Assuming "Name" is the title property
                    "title": [{"text": {"content": title}}]
                }
            }
        else:
            parent = {"page_id": parent_id}
            properties = {"title": [{"text": {"content": title}}]}

        # Prepare children blocks if content is provided
        children = []
        if content:
            children.append(
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"text": {"content": content}}]},
                }
            )

        page = await client.create_page(
            parent=parent,
            properties=properties,
            children=children if children else None,
        )

        return (
            page.to_dict()
            if hasattr(page, "to_dict")
            else {
                "id": page.id,
                "object": page.object,
                "title": title,
                "url": page.url,
            }
        )

    async def _query_notion_database(
        self, client: NotionClient, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Query a Notion database."""
        database_id = params.get("database_id")
        page_size = params.get("page_size", 10)
        filter_property = params.get("filter_property")
        filter_value = params.get("filter_value")

        filter_conditions = None
        if filter_property and filter_value:
            filter_conditions = {
                "property": filter_property,
                "rich_text": {"contains": filter_value},
            }

        results = await client.query_database(
            database_id=database_id,
            filter_conditions=filter_conditions,
            page_size=page_size,
        )

        serialized_pages = []
        for page in results["pages"]:
            if hasattr(page, "to_dict"):
                serialized_pages.append(page.to_dict())
            else:
                serialized_pages.append(
                    {
                        "id": page.id,
                        "object": page.object,
                        "title": self._extract_title(page),
                        "properties": page.properties,
                    }
                )

        return {
            "database_id": database_id,
            "pages": serialized_pages,
            "total_count": results["total_count"],
            "has_more": results["has_more"],
        }

    async def _get_notion_database(
        self, client: NotionClient, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get database structure information."""
        database_id = params.get("database_id")

        database = await client.get_database(database_id)

        return (
            database.to_dict()
            if hasattr(database, "to_dict")
            else {
                "id": database.id,
                "object": database.object,
                "title": self._extract_title(database),
                "properties": database.properties,
                "url": database.url,
            }
        )

    async def _update_notion_page(
        self, client: NotionClient, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing Notion page with granular block control."""
        page_id = params.get("page_id")
        properties = params.get("properties", {})
        block_operations = params.get("block_operations", [])
        append_blocks = params.get("append_blocks", [])

        results = {
            "page_id": page_id,
            "operations_performed": [],
            "properties_updated": False,
            "blocks_modified": 0,
            "errors": [],
        }

        # Update page properties if provided
        if properties:
            try:
                await client.update_page(page_id=page_id, properties=properties)
                results["properties_updated"] = True
                results["operations_performed"].append("properties_updated")
            except Exception as e:
                results["errors"].append(f"Property update failed: {str(e)}")

        # Process block operations
        for i, operation in enumerate(block_operations):
            try:
                op_type = operation.get("operation")
                block_id = operation.get("block_id")
                block_data = operation.get("block_data")
                position = operation.get("position")

                if op_type == "update":
                    if not block_id:
                        results["errors"].append(f"Operation {i}: block_id required for update")
                        continue
                    if not block_data:
                        results["errors"].append(f"Operation {i}: block_data required for update")
                        continue

                    await client.update_block(block_id=block_id, **block_data)
                    results["blocks_modified"] += 1
                    results["operations_performed"].append(f"updated_block_{block_id[:8]}")

                elif op_type == "delete":
                    if not block_id:
                        results["errors"].append(f"Operation {i}: block_id required for delete")
                        continue

                    await client.delete_block(block_id)
                    results["blocks_modified"] += 1
                    results["operations_performed"].append(f"deleted_block_{block_id[:8]}")

                elif op_type == "append":
                    if not block_data:
                        results["errors"].append(f"Operation {i}: block_data required for append")
                        continue

                    # Append to page or specific parent block
                    parent_id = block_id if block_id else page_id
                    await client.append_block_children(block_id=parent_id, children=[block_data])
                    results["blocks_modified"] += 1
                    results["operations_performed"].append(f"appended_to_{parent_id[:8]}")

                elif op_type == "insert":
                    if not block_id:
                        results["errors"].append(
                            f"Operation {i}: block_id required for insert position"
                        )
                        continue
                    if not block_data:
                        results["errors"].append(f"Operation {i}: block_data required for insert")
                        continue
                    if not position:
                        results["errors"].append(
                            f"Operation {i}: position (before/after) required for insert"
                        )
                        continue

                    # Get the parent of the reference block to insert into
                    reference_block = await client.get_block(block_id)
                    parent_id = getattr(reference_block, "parent", {}).get("page_id") or page_id

                    # Get current children to find insertion position
                    current_children = await client.get_block_children(parent_id)
                    blocks = current_children.get("blocks", [])

                    # Find the index of the reference block
                    ref_index = -1
                    for idx, block in enumerate(blocks):
                        if getattr(block, "id", "") == block_id:
                            ref_index = idx
                            break

                    if ref_index >= 0:
                        insert_index = ref_index if position == "before" else ref_index + 1

                        # Delete all blocks after insertion point
                        blocks_to_reinsert = blocks[insert_index:]
                        for block in blocks_to_reinsert:
                            if hasattr(block, "id"):
                                await client.delete_block(block.id)

                        # Insert new block
                        await client.append_block_children(
                            block_id=parent_id, children=[block_data]
                        )

                        # Re-insert the moved blocks
                        if blocks_to_reinsert:
                            reinsert_data = []
                            for block in blocks_to_reinsert:
                                if hasattr(block, "to_dict"):
                                    block_dict = block.to_dict()
                                    # Remove ID to create new blocks
                                    if "id" in block_dict:
                                        del block_dict["id"]
                                    reinsert_data.append(block_dict)

                            if reinsert_data:
                                await client.append_block_children(
                                    block_id=parent_id, children=reinsert_data
                                )

                        results["blocks_modified"] += 1
                        results["operations_performed"].append(
                            f"inserted_{position}_{block_id[:8]}"
                        )
                    else:
                        results["errors"].append(
                            f"Operation {i}: reference block {block_id} not found"
                        )

                else:
                    results["errors"].append(f"Operation {i}: unknown operation type '{op_type}'")

            except Exception as e:
                results["errors"].append(f"Operation {i} ({op_type}): {str(e)}")

        # Handle simple append blocks (for backward compatibility)
        if append_blocks:
            try:
                await client.append_block_children(block_id=page_id, children=append_blocks)
                results["blocks_modified"] += len(append_blocks)
                results["operations_performed"].append(f"appended_{len(append_blocks)}_blocks")
            except Exception as e:
                results["errors"].append(f"Append blocks failed: {str(e)}")

        # Get final page state
        try:
            final_page = await client.get_page(page_id)
            if hasattr(final_page, "to_dict"):
                results["page"] = final_page.to_dict()
            else:
                results["page"] = {
                    "id": final_page.id,
                    "object": final_page.object,
                    "title": self._extract_title(final_page),
                    "url": getattr(final_page, "url", None),
                    "properties": getattr(final_page, "properties", {}),
                }
        except Exception as e:
            results["errors"].append(f"Failed to retrieve final page state: {str(e)}")

        return results

    def _extract_title(self, notion_object) -> str:
        """Extract title from Notion object."""
        try:
            if hasattr(notion_object, "properties"):
                # For pages/databases with properties
                if "title" in notion_object.properties:
                    title_prop = notion_object.properties["title"]
                    if isinstance(title_prop, list) and len(title_prop) > 0:
                        return title_prop[0].get("text", {}).get("content", "Untitled")

                # Look for Name property (common in databases)
                if "Name" in notion_object.properties:
                    name_prop = notion_object.properties["Name"]
                    if isinstance(name_prop, dict) and "title" in name_prop:
                        title_list = name_prop["title"]
                        if isinstance(title_list, list) and len(title_list) > 0:
                            return title_list[0].get("text", {}).get("content", "Untitled")

            # Fallback to direct title attribute
            if hasattr(notion_object, "title"):
                if isinstance(notion_object.title, list) and len(notion_object.title) > 0:
                    return notion_object.title[0].get("text", {}).get("content", "Untitled")

            return "Untitled"
        except Exception:
            return "Untitled"

    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific tool."""
        tools_map = {
            "search_notion": {
                "name": "search_notion",
                "description": "Search across Notion pages and databases",
                "version": "1.0.0",
                "available": True,  # Always available since token is per-request
                "category": "notion",
                "usage_examples": [
                    {"access_token": "your-token", "query": "meeting notes"},
                    {"access_token": "your-token", "query": "project", "filter_type": "page"},
                ],
            },
            "get_notion_page": {
                "name": "get_notion_page",
                "description": "Get detailed page information",
                "version": "1.0.0",
                "available": True,
                "category": "notion",
                "usage_examples": [
                    {"access_token": "your-token", "page_id": "page-id-here"},
                    {
                        "access_token": "your-token",
                        "page_id": "page-id-here",
                        "include_children": True,
                    },
                ],
            },
            "create_notion_page": {
                "name": "create_notion_page",
                "description": "Create a new page in Notion",
                "version": "1.0.0",
                "available": True,
                "category": "notion",
                "usage_examples": [
                    {
                        "access_token": "your-token",
                        "parent_id": "parent-page-id",
                        "title": "New Page Title",
                        "content": "Page content here",
                    }
                ],
            },
            "query_notion_database": {
                "name": "query_notion_database",
                "description": "Query a Notion database",
                "version": "1.0.0",
                "available": True,
                "category": "notion",
                "usage_examples": [
                    {"access_token": "your-token", "database_id": "database-id-here"},
                    {
                        "access_token": "your-token",
                        "database_id": "database-id-here",
                        "filter_property": "Status",
                        "filter_value": "Done",
                    },
                ],
            },
            "get_notion_database": {
                "name": "get_notion_database",
                "description": "Get database structure information",
                "version": "1.0.0",
                "available": True,
                "category": "notion",
                "usage_examples": [
                    {"access_token": "your-token", "database_id": "database-id-here"}
                ],
            },
            "update_notion_page": {
                "name": "update_notion_page",
                "description": "Update properties and content of an existing Notion page with granular block control",
                "version": "2.0.0",
                "available": True,
                "category": "notion",
                "usage_examples": [
                    {
                        "access_token": "your-token",
                        "page_id": "page-id-here",
                        "properties": {"Name": {"title": [{"text": {"content": "Updated Title"}}]}},
                    },
                    {
                        "access_token": "your-token",
                        "page_id": "page-id-here",
                        "block_operations": [
                            {
                                "operation": "update",
                                "block_id": "block-id-to-update",
                                "block_data": {
                                    "paragraph": {
                                        "rich_text": [{"text": {"content": "Updated content"}}]
                                    }
                                },
                            },
                            {
                                "operation": "append",
                                "block_data": {
                                    "object": "block",
                                    "type": "paragraph",
                                    "paragraph": {
                                        "rich_text": [{"text": {"content": "New paragraph"}}]
                                    },
                                },
                            },
                            {
                                "operation": "insert",
                                "block_id": "reference-block-id",
                                "position": "after",
                                "block_data": {
                                    "object": "block",
                                    "type": "heading_2",
                                    "heading_2": {
                                        "rich_text": [{"text": {"content": "New Section"}}]
                                    },
                                },
                            },
                        ],
                    },
                    {
                        "access_token": "your-token",
                        "page_id": "page-id-here",
                        "append_blocks": [
                            {
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [{"text": {"content": "Simple append"}}]
                                },
                            }
                        ],
                    },
                ],
            },
        }

        return tools_map.get(
            tool_name,
            {
                "name": tool_name,
                "description": f"Tool '{tool_name}' not found",
                "available": False,
                "error": "Tool not found",
            },
        )

    def health_check(self) -> MCPHealthCheck:
        """MCP service health check."""
        available_tools = [
            "search_notion",
            "get_notion_page",
            "create_notion_page",
            "query_notion_database",
            "get_notion_database",
            "update_notion_page",
        ]

        # All tools are available since tokens are provided per-request
        healthy = True

        return MCPHealthCheck(
            healthy=healthy,
            version="1.0.0",
            available_tools=available_tools,
            timestamp=int(time.time()),
            error=None,
        )


# Initialize Notion MCP service
notion_mcp_service = NotionMCPService()
