"""
Streamlined Notion MCP API - Consolidated and simplified tools
减少工具数量，提高易用性的精简版Notion MCP集成
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
    """Streamlined MCP service for Notion operations with fewer, more powerful tools."""

    def __init__(self):
        # No global client - create per-request with user's token
        pass

    def get_available_tools(self) -> MCPToolsResponse:
        """Get available streamlined Notion tools."""
        tools = [
            MCPTool(
                name="notion_search",
                description="Universal search across all Notion content (pages, databases, blocks)",
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
                        "filter": {
                            "type": "object",
                            "properties": {
                                "object_type": {
                                    "type": "string",
                                    "enum": ["page", "database"],
                                    "description": "Filter by object type (optional)",
                                },
                                "property": {
                                    "type": "string",
                                    "description": "Property name for database filtering (optional)",
                                },
                                "value": {
                                    "type": "string",
                                    "description": "Property value for database filtering (optional)",
                                },
                            },
                            "description": "Advanced filtering options",
                        },
                        "limit": {
                            "type": "integer",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 100,
                            "description": "Maximum results to return",
                        },
                        "include_content": {
                            "type": "boolean",
                            "default": False,
                            "description": "Include page/block content in results",
                        },
                    },
                    "required": ["access_token", "query"],
                },
                category="notion",
                tags=["search", "universal", "pages", "databases"],
            ),
            MCPTool(
                name="notion_page",
                description="Complete page management (get, create, update with full block control)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "access_token": {
                            "type": "string",
                            "description": "Notion integration access token",
                        },
                        "action": {
                            "type": "string",
                            "enum": ["get", "create", "update"],
                            "description": "Action to perform on the page",
                        },
                        "page_id": {
                            "type": "string",
                            "description": "Page ID (required for get/update actions)",
                        },
                        "parent_id": {
                            "type": "string",
                            "description": "Parent page/database ID (required for create action)",
                        },
                        "parent_type": {
                            "type": "string",
                            "enum": ["page", "database"],
                            "default": "page",
                            "description": "Type of parent for create action",
                        },
                        "properties": {
                            "type": "object",
                            "description": "Page properties (title, status, tags, etc.)",
                        },
                        "content": {
                            "type": "object",
                            "properties": {
                                "blocks": {
                                    "type": "array",
                                    "items": {"type": "object"},
                                    "description": "Content blocks for the page",
                                },
                                "mode": {
                                    "type": "string",
                                    "enum": ["append", "replace"],
                                    "default": "append",
                                    "description": "How to handle content (append to existing or replace all)",
                                },
                            },
                            "description": "Page content configuration",
                        },
                        "block_operations": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "operation": {
                                        "type": "string",
                                        "enum": ["update", "insert", "delete", "append"],
                                        "description": "Block operation type",
                                    },
                                    "block_id": {
                                        "type": "string",
                                        "description": "Target block ID",
                                    },
                                    "position": {
                                        "type": "string",
                                        "enum": ["before", "after"],
                                        "description": "Insert position relative to block_id",
                                    },
                                    "block_data": {
                                        "type": "object",
                                        "description": "Block content data",
                                    },
                                },
                                "required": ["operation"],
                            },
                            "description": "Advanced block operations for precise editing",
                        },
                        "include_content": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include page content in response (for get/update)",
                        },
                    },
                    "required": ["access_token", "action"],
                },
                category="notion",
                tags=["page", "crud", "blocks", "content"],
            ),
            MCPTool(
                name="notion_database",
                description="Complete database operations (get schema, query with advanced filtering)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "access_token": {
                            "type": "string",
                            "description": "Notion integration access token",
                        },
                        "action": {
                            "type": "string",
                            "enum": ["get", "query"],
                            "description": "Action to perform (get schema or query data)",
                        },
                        "database_id": {
                            "type": "string",
                            "description": "Database ID",
                        },
                        "query": {
                            "type": "object",
                            "properties": {
                                "filter": {
                                    "type": "object",
                                    "description": "Notion API filter object (advanced filtering)",
                                },
                                "sorts": {
                                    "type": "array",
                                    "items": {"type": "object"},
                                    "description": "Sort configuration array",
                                },
                                "limit": {
                                    "type": "integer",
                                    "default": 10,
                                    "minimum": 1,
                                    "maximum": 100,
                                    "description": "Maximum results to return",
                                },
                                "simple_filter": {
                                    "type": "object",
                                    "properties": {
                                        "property": {"type": "string"},
                                        "value": {"type": "string"},
                                        "condition": {
                                            "type": "string",
                                            "enum": [
                                                "equals",
                                                "contains",
                                                "starts_with",
                                                "ends_with",
                                            ],
                                            "default": "contains",
                                        },
                                    },
                                    "description": "Simple property-based filtering",
                                },
                            },
                            "description": "Query configuration for database action",
                        },
                        "include_content": {
                            "type": "boolean",
                            "default": False,
                            "description": "Include page content for query results",
                        },
                    },
                    "required": ["access_token", "action", "database_id"],
                },
                category="notion",
                tags=["database", "query", "schema", "filter"],
            ),
        ]

        return MCPToolsResponse(
            tools=tools,
            total_count=len(tools),
            available_count=len(tools),
            categories=["notion"],
        )

    async def invoke_tool(self, tool_name: str, params: Dict[str, Any]) -> MCPInvokeResponse:
        """Invoke specified streamlined Notion tool."""
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
            if tool_name == "notion_search":
                result = await self._universal_search(client, params)
            elif tool_name == "notion_page":
                result = await self._page_operations(client, params)
            elif tool_name == "notion_database":
                result = await self._database_operations(client, params)
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

    async def _universal_search(
        self, client: NotionClient, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Universal search across all Notion content types."""
        query = params.get("query")
        filter_config = params.get("filter", {})
        limit = params.get("limit", 10)
        include_content = params.get("include_content", False)

        # Build filter conditions
        filter_conditions = None
        if filter_config.get("object_type"):
            filter_conditions = {"value": filter_config["object_type"], "property": "object"}

        # Perform search
        search_results = await client.search(
            query=query,
            filter_conditions=filter_conditions,
            page_size=limit,
        )

        # Process results
        results = []
        for item in search_results["results"]:
            result_item = {
                "id": getattr(item, "id", "unknown"),
                "object": getattr(item, "object", "unknown"),
                "title": self._extract_title(item),
                "url": getattr(item, "url", None),
            }

            # Add content if requested
            if include_content and result_item["object"] == "page":
                try:
                    children = await client.get_block_children(result_item["id"])
                    result_item["content"] = [
                        child.to_dict()
                        if hasattr(child, "to_dict")
                        else {"id": getattr(child, "id", "unknown")}
                        for child in children.get("blocks", [])
                    ]
                except:
                    result_item["content"] = []

            # Add database-specific filtering if needed
            if (
                filter_config.get("property")
                and filter_config.get("value")
                and result_item["object"] == "database"
            ):
                try:
                    # Query the database with the filter
                    db_filter = {
                        "property": filter_config["property"],
                        "rich_text": {"contains": filter_config["value"]},
                    }
                    db_results = await client.query_database(
                        database_id=result_item["id"], filter_conditions=db_filter, page_size=limit
                    )
                    result_item["filtered_pages"] = len(db_results.get("pages", []))
                except:
                    result_item["filtered_pages"] = 0

            results.append(result_item)

        return {
            "query": query,
            "results": results,
            "total_count": search_results.get("total_count", len(results)),
            "has_more": search_results.get("has_more", False),
            "filter": filter_config,
        }

    async def _page_operations(
        self, client: NotionClient, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle all page operations (get, create, update)."""
        action = params.get("action")
        page_id = params.get("page_id")
        include_content = params.get("include_content", True)

        if action == "get":
            if not page_id:
                raise ValueError("page_id is required for get action")

            page = await client.get_page(page_id)
            result = {
                "action": "get",
                "page": page.to_dict()
                if hasattr(page, "to_dict")
                else {
                    "id": page.id,
                    "object": page.object,
                    "title": self._extract_title(page),
                    "url": page.url,
                    "properties": page.properties,
                },
            }

            if include_content:
                children = await client.get_block_children(page_id)
                result["content"] = [
                    child.to_dict()
                    if hasattr(child, "to_dict")
                    else {
                        "id": getattr(child, "id", "unknown"),
                        "type": getattr(child, "type", "unknown"),
                    }
                    for child in children.get("blocks", [])
                ]

            return result

        elif action == "create":
            parent_id = params.get("parent_id")
            if not parent_id:
                raise ValueError("parent_id is required for create action")

            parent_type = params.get("parent_type", "page")
            properties = params.get("properties", {})
            content = params.get("content", {})

            # Prepare parent reference
            if parent_type == "database":
                parent = {"database_id": parent_id}
                # Ensure title property exists for database pages
                if "title" not in properties and "Name" not in properties:
                    properties["Name"] = {"title": [{"text": {"content": "New Page"}}]}
            else:
                parent = {"page_id": parent_id}
                if "title" not in properties:
                    properties["title"] = [{"text": {"content": "New Page"}}]

            # Prepare content blocks
            children = content.get("blocks", [])

            page = await client.create_page(
                parent=parent,
                properties=properties,
                children=children if children else None,
            )

            result = {
                "action": "create",
                "page": page.to_dict()
                if hasattr(page, "to_dict")
                else {
                    "id": page.id,
                    "object": page.object,
                    "title": self._extract_title(page),
                    "url": page.url,
                },
            }

            return result

        elif action == "update":
            if not page_id:
                raise ValueError("page_id is required for update action")

            properties = params.get("properties", {})
            content = params.get("content", {})
            block_operations = params.get("block_operations", [])

            results = {
                "action": "update",
                "page_id": page_id,
                "operations_performed": [],
                "properties_updated": False,
                "blocks_modified": 0,
                "errors": [],
            }

            # Update properties
            if properties:
                try:
                    await client.update_page(page_id=page_id, properties=properties)
                    results["properties_updated"] = True
                    results["operations_performed"].append("properties_updated")
                except Exception as e:
                    results["errors"].append(f"Property update failed: {str(e)}")

            # Handle content blocks
            if content.get("blocks"):
                blocks = content["blocks"]
                mode = content.get("mode", "append")

                try:
                    if mode == "replace":
                        # Delete existing blocks first
                        current_children = await client.get_block_children(page_id)
                        for block in current_children.get("blocks", []):
                            if hasattr(block, "id"):
                                await client.delete_block(block.id)

                    # Add new blocks
                    await client.append_block_children(block_id=page_id, children=blocks)
                    results["blocks_modified"] += len(blocks)
                    results["operations_performed"].append(f"{mode}_{len(blocks)}_blocks")
                except Exception as e:
                    results["errors"].append(f"Content update failed: {str(e)}")

            # Handle advanced block operations
            for i, operation in enumerate(block_operations):
                try:
                    op_type = operation.get("operation")
                    block_id = operation.get("block_id")
                    block_data = operation.get("block_data")
                    position = operation.get("position")

                    if op_type == "update" and block_id and block_data:
                        await client.update_block(block_id=block_id, **block_data)
                        results["blocks_modified"] += 1
                        results["operations_performed"].append(f"updated_block_{block_id[:8]}")

                    elif op_type == "delete" and block_id:
                        await client.delete_block(block_id)
                        results["blocks_modified"] += 1
                        results["operations_performed"].append(f"deleted_block_{block_id[:8]}")

                    elif op_type == "append" and block_data:
                        parent_id_for_append = block_id if block_id else page_id
                        await client.append_block_children(
                            block_id=parent_id_for_append, children=[block_data]
                        )
                        results["blocks_modified"] += 1
                        results["operations_performed"].append(
                            f"appended_to_{parent_id_for_append[:8]}"
                        )

                    elif op_type == "insert" and block_id and block_data and position:
                        # Simplified insert - just append after getting parent context
                        reference_block = await client.get_block(block_id)
                        parent_id_for_insert = (
                            getattr(reference_block, "parent", {}).get("page_id") or page_id
                        )
                        await client.append_block_children(
                            block_id=parent_id_for_insert, children=[block_data]
                        )
                        results["blocks_modified"] += 1
                        results["operations_performed"].append(
                            f"inserted_{position}_{block_id[:8]}"
                        )

                    else:
                        results["errors"].append(f"Operation {i}: Invalid or incomplete operation")

                except Exception as e:
                    results["errors"].append(f"Operation {i} failed: {str(e)}")

            # Get final page state if requested
            if include_content:
                try:
                    final_page = await client.get_page(page_id)
                    results["page"] = (
                        final_page.to_dict()
                        if hasattr(final_page, "to_dict")
                        else {
                            "id": final_page.id,
                            "title": self._extract_title(final_page),
                            "url": getattr(final_page, "url", None),
                        }
                    )
                except Exception as e:
                    results["errors"].append(f"Failed to retrieve final page state: {str(e)}")

            return results

        else:
            raise ValueError(f"Unknown action: {action}")

    async def _database_operations(
        self, client: NotionClient, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle database operations (get schema, query)."""
        action = params.get("action")
        database_id = params.get("database_id")

        if action == "get":
            database = await client.get_database(database_id)
            return {
                "action": "get",
                "database": database.to_dict()
                if hasattr(database, "to_dict")
                else {
                    "id": database.id,
                    "object": database.object,
                    "title": self._extract_title(database),
                    "properties": database.properties,
                    "url": database.url,
                },
            }

        elif action == "query":
            query_config = params.get("query", {})
            include_content = params.get("include_content", False)

            # Handle simple filter
            filter_conditions = None
            if query_config.get("simple_filter"):
                sf = query_config["simple_filter"]
                property_name = sf.get("property")
                value = sf.get("value")
                condition = sf.get("condition", "contains")

                if property_name and value:
                    if condition == "equals":
                        filter_conditions = {
                            "property": property_name,
                            "rich_text": {"equals": value},
                        }
                    elif condition == "contains":
                        filter_conditions = {
                            "property": property_name,
                            "rich_text": {"contains": value},
                        }
                    elif condition == "starts_with":
                        filter_conditions = {
                            "property": property_name,
                            "rich_text": {"starts_with": value},
                        }
                    elif condition == "ends_with":
                        filter_conditions = {
                            "property": property_name,
                            "rich_text": {"ends_with": value},
                        }

            # Use advanced filter if provided (overrides simple filter)
            if query_config.get("filter"):
                filter_conditions = query_config["filter"]

            # Query database
            results = await client.query_database(
                database_id=database_id,
                filter_conditions=filter_conditions,
                sorts=query_config.get("sorts"),
                page_size=query_config.get("limit", 10),
            )

            # Process pages
            pages = []
            for page in results.get("pages", []):
                page_data = {
                    "id": page.id,
                    "title": self._extract_title(page),
                    "properties": page.properties,
                    "url": getattr(page, "url", None),
                }

                # Add content if requested
                if include_content:
                    try:
                        children = await client.get_block_children(page.id)
                        page_data["content"] = [
                            child.to_dict()
                            if hasattr(child, "to_dict")
                            else {"id": getattr(child, "id", "unknown")}
                            for child in children.get("blocks", [])
                        ]
                    except:
                        page_data["content"] = []

                pages.append(page_data)

            return {
                "action": "query",
                "database_id": database_id,
                "pages": pages,
                "total_count": results.get("total_count", len(pages)),
                "has_more": results.get("has_more", False),
                "filter": filter_conditions,
                "query_config": query_config,
            }

        else:
            raise ValueError(f"Unknown action: {action}")

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
        """Get detailed information about a specific streamlined tool."""
        tools_map = {
            "notion_search": {
                "name": "notion_search",
                "description": "Universal search across all Notion content types",
                "version": "3.0.0",
                "available": True,
                "category": "notion",
                "consolidates": ["search_notion", "query_notion_database (basic search)"],
                "usage_examples": [
                    {"access_token": "your-token", "query": "meeting notes", "limit": 5},
                    {
                        "access_token": "your-token",
                        "query": "project",
                        "filter": {"object_type": "page"},
                        "include_content": True,
                    },
                ],
            },
            "notion_page": {
                "name": "notion_page",
                "description": "Complete page management with full CRUD and block operations",
                "version": "3.0.0",
                "available": True,
                "category": "notion",
                "consolidates": ["get_notion_page", "create_notion_page", "update_notion_page"],
                "usage_examples": [
                    {
                        "access_token": "your-token",
                        "action": "get",
                        "page_id": "page-id-here",
                        "include_content": True,
                    },
                    {
                        "access_token": "your-token",
                        "action": "create",
                        "parent_id": "parent-page-id",
                        "properties": {"title": [{"text": {"content": "New Page"}}]},
                        "content": {
                            "blocks": [
                                {
                                    "object": "block",
                                    "type": "paragraph",
                                    "paragraph": {
                                        "rich_text": [{"text": {"content": "Hello world"}}]
                                    },
                                }
                            ]
                        },
                    },
                    {
                        "access_token": "your-token",
                        "action": "update",
                        "page_id": "page-id-here",
                        "properties": {"Name": {"title": [{"text": {"content": "Updated Title"}}]}},
                        "block_operations": [
                            {
                                "operation": "update",
                                "block_id": "block-to-update",
                                "block_data": {
                                    "paragraph": {
                                        "rich_text": [{"text": {"content": "Updated content"}}]
                                    }
                                },
                            }
                        ],
                    },
                ],
            },
            "notion_database": {
                "name": "notion_database",
                "description": "Complete database operations with advanced querying",
                "version": "3.0.0",
                "available": True,
                "category": "notion",
                "consolidates": ["get_notion_database", "query_notion_database"],
                "usage_examples": [
                    {
                        "access_token": "your-token",
                        "action": "get",
                        "database_id": "database-id-here",
                    },
                    {
                        "access_token": "your-token",
                        "action": "query",
                        "database_id": "database-id-here",
                        "query": {
                            "simple_filter": {
                                "property": "Status",
                                "value": "Done",
                                "condition": "equals",
                            },
                            "limit": 20,
                        },
                        "include_content": False,
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
            "notion_search",
            "notion_page",
            "notion_database",
        ]

        # All tools are available since tokens are provided per-request
        healthy = True

        return MCPHealthCheck(
            healthy=healthy,
            version="3.0.0",
            available_tools=available_tools,
            timestamp=int(time.time()),
            error=None,
        )


# Initialize streamlined Notion MCP service
notion_mcp_service = NotionMCPService()
