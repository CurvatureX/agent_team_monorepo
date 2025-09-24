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
                description="Universal search across all Notion content with AI-optimized results formatting for OpenAI, Claude, and Gemini",
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
                        "ai_format": {
                            "type": "string",
                            "enum": ["structured", "narrative", "summary"],
                            "default": "structured",
                            "description": "Format results for AI consumption: structured (JSON), narrative (conversational), or summary (condensed)",
                        },
                        "relevance_scoring": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include relevance scores and ranking for better AI decision-making",
                        },
                    },
                    "required": ["access_token", "query"],
                },
                category="notion",
                tags=["search", "universal", "pages", "databases"],
            ),
            MCPTool(
                name="notion_page",
                description="Complete page management (get, create, update, retrieve documents with full content) - AI-optimized for OpenAI, Claude, and Gemini",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "access_token": {
                            "type": "string",
                            "description": "Notion integration access token",
                        },
                        "action": {
                            "type": "string",
                            "enum": ["get", "create", "update", "retrieve", "list_metadata"],
                            "description": "Action to perform: get (single page), create (new page), update (modify existing), retrieve (multiple documents with full content), list_metadata (document metadata overview)",
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
                        "page_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of page IDs to retrieve (for retrieve action)",
                        },
                        "search_query": {
                            "type": "string",
                            "description": "Search query to find documents (alternative to page_ids for retrieve action)",
                        },
                        "max_documents": {
                            "type": "integer",
                            "default": 5,
                            "minimum": 1,
                            "maximum": 20,
                            "description": "Maximum number of documents to retrieve when using search_query",
                        },
                        "include_children": {
                            "type": "boolean",
                            "default": False,
                            "description": "Include nested child pages and databases (retrieve action)",
                        },
                        "content_format": {
                            "type": "string",
                            "enum": ["full", "text_only", "structured"],
                            "default": "full",
                            "description": "Format for content extraction: full (all details), text_only (plain text), structured (organized hierarchy)",
                        },
                        "ai_format": {
                            "type": "string",
                            "enum": ["structured", "narrative", "summary"],
                            "default": "structured",
                            "description": "AI-optimized output format for better LLM consumption",
                        },
                        "workspace_search": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "Search query to find documents (for list_metadata action)",
                                },
                                "filter_type": {
                                    "type": "string",
                                    "enum": ["page", "database", "all"],
                                    "default": "all",
                                    "description": "Filter by object type",
                                },
                                "sort_by": {
                                    "type": "string",
                                    "enum": ["created_time", "last_edited_time", "title"],
                                    "default": "last_edited_time",
                                    "description": "Sort documents by specified field",
                                },
                                "sort_order": {
                                    "type": "string",
                                    "enum": ["asc", "desc"],
                                    "default": "desc",
                                    "description": "Sort order (newest first by default)",
                                },
                                "limit": {
                                    "type": "integer",
                                    "default": 20,
                                    "minimum": 1,
                                    "maximum": 100,
                                    "description": "Maximum number of documents to return",
                                },
                            },
                            "description": "Workspace search configuration for list_metadata action",
                        },
                        "metadata_options": {
                            "type": "object",
                            "properties": {
                                "include_properties": {
                                    "type": "boolean",
                                    "default": True,
                                    "description": "Include custom properties (tags, status, dates, etc.)",
                                },
                                "include_content_preview": {
                                    "type": "boolean",
                                    "default": False,
                                    "description": "Include brief content preview (first 100 characters)",
                                },
                                "include_parent_info": {
                                    "type": "boolean",
                                    "default": True,
                                    "description": "Include parent page/database information",
                                },
                                "include_child_count": {
                                    "type": "boolean",
                                    "default": False,
                                    "description": "Include count of child pages/blocks",
                                },
                                "property_filters": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Specific properties to include (if empty, includes all)",
                                },
                            },
                            "description": "Metadata extraction options for list_metadata action",
                        },
                    },
                    "required": ["access_token", "action"],
                },
                category="notion",
                tags=[
                    "page",
                    "crud",
                    "blocks",
                    "content",
                    "retrieve",
                    "documents",
                    "metadata",
                    "list",
                ],
            ),
            MCPTool(
                name="notion_database",
                description="Complete database operations (get schema, query with advanced filtering) - AI-optimized for OpenAI, Claude, and Gemini",
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
        """Universal search across all Notion content types with AI-optimized formatting."""
        query = params.get("query")
        filter_config = params.get("filter", {})
        limit = params.get("limit", 10)
        include_content = params.get("include_content", False)
        ai_format = params.get("ai_format", "structured")
        relevance_scoring = params.get("relevance_scoring", True)

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

            # Add relevance scoring for AI optimization
            if relevance_scoring:
                # Simple relevance scoring based on query match in title/content
                score = 0
                if query.lower() in result_item["title"].lower():
                    score += 10
                if result_item.get("content"):
                    content_str = str(result_item["content"]).lower()
                    score += content_str.count(query.lower()) * 2
                result_item["relevance_score"] = score

            results.append(result_item)

        # Sort by relevance if scoring is enabled
        if relevance_scoring:
            results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

        base_result = {
            "query": query,
            "results": results,
            "total_count": search_results.get("total_count", len(results)),
            "has_more": search_results.get("has_more", False),
            "filter": filter_config,
        }

        # Apply AI-specific formatting
        if ai_format == "narrative":
            return self._format_for_narrative(base_result, query)
        elif ai_format == "summary":
            return self._format_for_summary(base_result, query)
        else:
            # Default structured format
            return base_result

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

        elif action == "retrieve":
            # Handle document retrieval action
            return await self._retrieve_documents(client, params)

        elif action == "list_metadata":
            # Handle metadata listing action
            return await self._list_document_metadata(client, params)

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
        """Extract title from Notion object or dictionary."""
        try:
            # Handle dictionary format (for mock data and direct API responses)
            if isinstance(notion_object, dict):
                # Check properties in dictionary
                if "properties" in notion_object and notion_object["properties"]:
                    props = notion_object["properties"]
                    for prop_name, prop_value in props.items():
                        if isinstance(prop_value, dict) and prop_value.get("type") == "title":
                            if "title" in prop_value and prop_value["title"]:
                                title_list = prop_value["title"]
                                if isinstance(title_list, list) and len(title_list) > 0:
                                    first_item = title_list[0]
                                    if isinstance(first_item, dict):
                                        return first_item.get(
                                            "plain_text",
                                            first_item.get("text", {}).get("content", "Untitled"),
                                        )
                return "Untitled"

            # Check direct title attribute first (for databases and some pages)
            if hasattr(notion_object, "title") and notion_object.title:
                if isinstance(notion_object.title, list) and len(notion_object.title) > 0:
                    first_title = notion_object.title[0]
                    if isinstance(first_title, dict) and "text" in first_title:
                        return first_title["text"].get("content", "Untitled")
                    elif isinstance(first_title, dict) and "plain_text" in first_title:
                        return first_title["plain_text"]

            # For pages with properties
            if hasattr(notion_object, "properties") and notion_object.properties:
                # Look for title property
                for prop_name, prop_value in notion_object.properties.items():
                    if isinstance(prop_value, dict) and prop_value.get("type") == "title":
                        if "title" in prop_value and prop_value["title"]:
                            title_list = prop_value["title"]
                            if isinstance(title_list, list) and len(title_list) > 0:
                                first_item = title_list[0]
                                if isinstance(first_item, dict):
                                    return first_item.get(
                                        "plain_text",
                                        first_item.get("text", {}).get("content", "Untitled"),
                                    )

            return "Untitled"
        except Exception:
            return "Untitled"

    async def _retrieve_documents(
        self, client: NotionClient, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Retrieve complete Notion documents with full content."""
        page_ids = params.get("page_ids", [])
        search_query = params.get("search_query")
        max_documents = params.get("max_documents", 5)
        include_properties = params.get("include_properties", True)
        include_blocks = params.get("include_blocks", True)
        include_children = params.get("include_children", False)
        content_format = params.get("content_format", "full")
        ai_format = params.get("ai_format", "structured")

        documents = []

        # If search_query provided, find documents first
        if search_query and not page_ids:
            search_results = await client.search(query=search_query, page_size=max_documents)
            # Filter to only pages
            from shared.sdks.notion_sdk import NotionPage

            results = search_results.get("results", []) if isinstance(search_results, dict) else []
            pages = [item for item in results if isinstance(item, NotionPage)]
            page_ids = [page.id for page in pages[:max_documents]]

        # Retrieve each document
        for page_id in page_ids:
            try:
                document = {
                    "page_id": page_id,
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                }

                # Get page properties
                if include_properties:
                    page = await client.get_page(page_id)
                    document["properties"] = {
                        "title": self._extract_title(page),
                        "url": page.url,
                        "created_time": page.created_time.isoformat()
                        if page.created_time
                        else None,
                        "last_edited_time": page.last_edited_time.isoformat()
                        if page.last_edited_time
                        else None,
                        "created_by": getattr(page.created_by, "id", None)
                        if page.created_by
                        else None,
                        "last_edited_by": getattr(page.last_edited_by, "id", None)
                        if page.last_edited_by
                        else None,
                        "cover": page.cover.file.url
                        if page.cover and hasattr(page.cover, "file")
                        else None,
                        "icon": page.icon.file.url
                        if page.icon and hasattr(page.icon, "file")
                        else None,
                        "archived": page.archived,
                        "parent": {
                            "type": page.parent.type,
                            "id": getattr(page.parent, page.parent.type + "_id", None),
                        }
                        if page.parent
                        else None,
                        "custom_properties": page.properties if hasattr(page, "properties") else {},
                    }

                # Get page content blocks
                if include_blocks:
                    blocks = await client.get_block_children(page_id)
                    document["content"] = await self._format_blocks_content(
                        client, blocks.results, content_format, include_children
                    )

                documents.append(document)

            except Exception as e:
                logger.error(f"Error retrieving document {page_id}: {e}")
                documents.append(
                    {
                        "page_id": page_id,
                        "error": str(e),
                        "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    }
                )

        result = {
            "action": "retrieve_documents",
            "total_documents": len(documents),
            "successful_retrievals": len([d for d in documents if "error" not in d]),
            "failed_retrievals": len([d for d in documents if "error" in d]),
            "documents": documents,
            "search_query": search_query,
            "content_format": content_format,
            "settings": {
                "include_properties": include_properties,
                "include_blocks": include_blocks,
                "include_children": include_children,
            },
        }

        # Apply AI formatting
        if ai_format == "narrative":
            return self._format_documents_for_narrative(result)
        elif ai_format == "summary":
            return self._format_documents_for_summary(result)
        else:
            return result

    async def _format_blocks_content(
        self, client: NotionClient, blocks: List, content_format: str, include_children: bool
    ) -> List[Dict[str, Any]]:
        """Format block content based on specified format."""
        formatted_blocks = []

        for block in blocks:
            if content_format == "text_only":
                # Extract only text content
                text_content = self._extract_text_from_block(block)
                if text_content:
                    formatted_blocks.append({"type": "text", "content": text_content})
            elif content_format == "structured":
                # Organized hierarchy
                formatted_block = {
                    "id": block.id,
                    "type": block.type,
                    "content": self._extract_text_from_block(block),
                    "created_time": block.created_time.isoformat()
                    if hasattr(block, "created_time") and block.created_time
                    else None,
                    "last_edited_time": block.last_edited_time.isoformat()
                    if hasattr(block, "last_edited_time") and block.last_edited_time
                    else None,
                }
                formatted_blocks.append(formatted_block)
            else:  # full format
                # All block details
                formatted_block = {
                    "id": block.id,
                    "object": block.object,
                    "type": block.type,
                    "created_time": block.created_time.isoformat()
                    if hasattr(block, "created_time") and block.created_time
                    else None,
                    "last_edited_time": block.last_edited_time.isoformat()
                    if hasattr(block, "last_edited_time") and block.last_edited_time
                    else None,
                    "created_by": getattr(block.created_by, "id", None)
                    if hasattr(block, "created_by") and block.created_by
                    else None,
                    "last_edited_by": getattr(block.last_edited_by, "id", None)
                    if hasattr(block, "last_edited_by") and block.last_edited_by
                    else None,
                    "has_children": block.has_children if hasattr(block, "has_children") else False,
                    "archived": block.archived if hasattr(block, "archived") else False,
                    "content": self._extract_block_content(block),
                }
                formatted_blocks.append(formatted_block)

            # Include children if requested
            if include_children and hasattr(block, "has_children") and block.has_children:
                try:
                    children = await client.get_block_children(block.id)
                    formatted_block["children"] = await self._format_blocks_content(
                        client, children.results, content_format, include_children
                    )
                except Exception as e:
                    logger.warning(f"Could not retrieve children for block {block.id}: {e}")

        return formatted_blocks

    def _extract_text_from_block(self, block) -> str:
        """Extract plain text from a block."""
        try:
            block_type = block.type
            if hasattr(block, block_type):
                block_data = getattr(block, block_type)
                if hasattr(block_data, "rich_text"):
                    return "".join([text.plain_text for text in block_data.rich_text])
                elif hasattr(block_data, "title"):
                    return "".join([text.plain_text for text in block_data.title])
        except Exception:
            pass
        return ""

    def _extract_block_content(self, block) -> Dict[str, Any]:
        """Extract full block content."""
        try:
            block_type = block.type
            if hasattr(block, block_type):
                block_data = getattr(block, block_type)
                return block_data.__dict__ if hasattr(block_data, "__dict__") else str(block_data)
        except Exception:
            pass
        return {}

    def _format_documents_for_narrative(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format document retrieval results as narrative text."""
        documents = result["documents"]
        total_docs = result["total_documents"]
        successful = result["successful_retrievals"]

        if total_docs == 0:
            narrative = "No documents were found or specified for retrieval."
        else:
            narrative = f"I retrieved {successful} of {total_docs} requested Notion documents:\n\n"

            for i, doc in enumerate(documents, 1):
                if "error" in doc:
                    narrative += (
                        f"{i}. Document {doc['page_id']}: ❌ Failed to retrieve - {doc['error']}\n"
                    )
                else:
                    title = doc.get("properties", {}).get("title", "Untitled")
                    narrative += f"{i}. **{title}**\n"

                    if doc.get("properties"):
                        props = doc["properties"]
                        if props.get("url"):
                            narrative += f"   📄 URL: {props['url']}\n"
                        if props.get("created_time"):
                            narrative += f"   📅 Created: {props['created_time'][:10]}\n"
                        if props.get("last_edited_time"):
                            narrative += f"   ✏️ Last edited: {props['last_edited_time'][:10]}\n"

                    if doc.get("content"):
                        content_preview = ""
                        for block in doc["content"][:3]:  # First 3 blocks
                            if isinstance(block, dict) and block.get("content"):
                                text = block["content"][:100]
                                if text:
                                    content_preview += f"   {text}...\n"

                        if content_preview:
                            narrative += f"   📝 Content preview:\n{content_preview}"

                    narrative += "\n"

        return {**result, "ai_narrative": narrative, "format_type": "narrative"}

    def _format_documents_for_summary(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format document retrieval results as summary."""
        documents = result["documents"]

        summary = {
            "total_requested": result["total_documents"],
            "successful_retrievals": result["successful_retrievals"],
            "failed_retrievals": result["failed_retrievals"],
            "retrieval_successful": result["successful_retrievals"] > 0,
            "search_query": result.get("search_query"),
            "content_format": result["content_format"],
            "documents_summary": [],
        }

        for doc in documents:
            if "error" not in doc:
                doc_summary = {
                    "page_id": doc["page_id"],
                    "title": doc.get("properties", {}).get("title", "Untitled"),
                    "url": doc.get("properties", {}).get("url"),
                    "has_content": bool(doc.get("content")),
                    "block_count": len(doc.get("content", [])),
                    "created_time": doc.get("properties", {}).get("created_time"),
                    "word_count": self._estimate_word_count(doc.get("content", [])),
                }
                summary["documents_summary"].append(doc_summary)

        return {**result, "ai_summary": summary, "format_type": "summary"}

    def _estimate_word_count(self, blocks: List) -> int:
        """Estimate word count from blocks."""
        total_words = 0
        for block in blocks:
            if isinstance(block, dict) and block.get("content"):
                if isinstance(block["content"], str):
                    total_words += len(block["content"].split())
        return total_words

    async def _list_document_metadata(
        self, client: NotionClient, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """List document metadata without full content."""
        workspace_search = params.get("workspace_search", {})
        metadata_options = params.get("metadata_options", {})
        ai_format = params.get("ai_format", "structured")

        # Extract search parameters
        search_query = workspace_search.get("query", "")
        filter_type = workspace_search.get("filter_type", "all")
        sort_by = workspace_search.get("sort_by", "last_edited_time")
        sort_order = workspace_search.get("sort_order", "desc")
        limit = workspace_search.get("limit", 20)

        # Extract metadata options
        include_properties = metadata_options.get("include_properties", True)
        include_content_preview = metadata_options.get("include_content_preview", False)
        include_parent_info = metadata_options.get("include_parent_info", True)
        include_child_count = metadata_options.get("include_child_count", False)
        property_filters = metadata_options.get("property_filters", [])

        documents_metadata = []

        try:
            # Search for documents
            search_params = {
                "query": search_query if search_query else "",
                "page_size": limit,
            }

            # Add filter if specified - Note: Notion search API has limited filtering
            # We'll filter results after getting them since the API doesn't support object type filters

            search_results = await client.search(**search_params)
            results = search_results.get("results", []) if isinstance(search_results, dict) else []

            # Filter by object type if specified
            if filter_type == "page":
                from shared.sdks.notion_sdk import NotionPage

                results = [item for item in results if isinstance(item, NotionPage)]
            elif filter_type == "database":
                from shared.sdks.notion_sdk import NotionDatabase

                results = [item for item in results if isinstance(item, NotionDatabase)]
            # filter_type == "all" means no filtering needed

            # Process each document
            for item in results:
                try:
                    metadata = await self._extract_document_metadata(
                        client,
                        item,
                        include_properties,
                        include_content_preview,
                        include_parent_info,
                        include_child_count,
                        property_filters,
                    )
                    documents_metadata.append(metadata)

                    # If it's a database and we want to include its pages, query them
                    from shared.sdks.notion_sdk import NotionDatabase

                    if isinstance(item, NotionDatabase) and filter_type in ["all", "page"]:
                        try:
                            # Try to get pages from this database
                            db_pages = await self._get_database_pages(client, item.id, limit)
                            for page_metadata in db_pages:
                                documents_metadata.append(page_metadata)
                        except Exception as e:
                            logger.warning(f"Failed to get pages from database {item.id}: {e}")

                except Exception as e:
                    logger.warning(
                        f"Failed to extract metadata for {getattr(item, 'id', 'unknown')}: {e}"
                    )
                    # Add error entry
                    documents_metadata.append(
                        {"id": getattr(item, "id", "unknown"), "error": str(e), "object": "unknown"}
                    )

            # Sort documents
            sorted_documents = self._sort_documents_metadata(
                documents_metadata, sort_by, sort_order
            )

            result = {
                "action": "list_metadata",
                "search_query": search_query,
                "filter_type": filter_type,
                "total_documents": len(sorted_documents),
                "documents": sorted_documents,
                "sort_by": sort_by,
                "sort_order": sort_order,
                "metadata_options": metadata_options,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
            }

            # Apply AI formatting
            if ai_format == "narrative":
                return self._format_metadata_for_narrative(result)
            elif ai_format == "summary":
                return self._format_metadata_for_summary(result)
            else:
                return result

        except Exception as e:
            logger.error(f"Error listing document metadata: {e}")
            return {
                "action": "list_metadata",
                "error": str(e),
                "search_query": search_query,
                "total_documents": 0,
                "documents": [],
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
            }

    async def _extract_document_metadata(
        self,
        client: NotionClient,
        document: Any,
        include_properties: bool,
        include_content_preview: bool,
        include_parent_info: bool,
        include_child_count: bool,
        property_filters: List[str],
    ) -> Dict[str, Any]:
        """Extract metadata from a single document."""
        doc_id = getattr(document, "id", None)

        # Determine object type based on class
        from shared.sdks.notion_sdk import NotionDatabase, NotionPage

        if isinstance(document, NotionPage):
            doc_object = "page"
        elif isinstance(document, NotionDatabase):
            doc_object = "database"
        else:
            doc_object = "unknown"

        # Base metadata
        metadata = {
            "id": doc_id,
            "object": doc_object,
            "title": self._extract_title(document),
            "url": getattr(document, "url", None),
            "created_time": getattr(document, "created_time", None),
            "last_edited_time": getattr(document, "last_edited_time", None),
            "archived": getattr(document, "archived", False),
        }

        # Convert datetime objects to ISO strings
        if metadata["created_time"]:
            metadata["created_time"] = (
                metadata["created_time"].isoformat()
                if hasattr(metadata["created_time"], "isoformat")
                else str(metadata["created_time"])
            )
        if metadata["last_edited_time"]:
            metadata["last_edited_time"] = (
                metadata["last_edited_time"].isoformat()
                if hasattr(metadata["last_edited_time"], "isoformat")
                else str(metadata["last_edited_time"])
            )

        # Add cover and icon if available
        if hasattr(document, "cover") and document.cover:
            metadata["cover"] = (
                getattr(document.cover, "file", {}).get("url")
                if hasattr(document.cover, "file")
                else None
            )
        if hasattr(document, "icon") and document.icon:
            metadata["icon"] = (
                getattr(document.icon, "file", {}).get("url")
                if hasattr(document.icon, "file")
                else None
            )

        # Include custom properties
        if include_properties and hasattr(document, "properties"):
            custom_properties = {}
            properties = document.properties if isinstance(document.properties, dict) else {}

            for prop_name, prop_value in properties.items():
                # Apply property filters if specified
                if property_filters and prop_name not in property_filters:
                    continue

                try:
                    custom_properties[prop_name] = self._extract_property_value(prop_value)
                except Exception as e:
                    custom_properties[prop_name] = f"Error extracting: {str(e)}"

            metadata["custom_properties"] = custom_properties

        # Include parent information
        if include_parent_info and hasattr(document, "parent"):
            parent = document.parent
            metadata["parent"] = {
                "type": getattr(parent, "type", None),
                "id": getattr(parent, getattr(parent, "type", "unknown") + "_id", None)
                if hasattr(parent, "type")
                else None,
            }

        # Include content preview
        if include_content_preview and doc_object == "page":
            try:
                blocks = await client.get_block_children(doc_id)
                preview_text = ""
                for block in blocks.results[:3]:  # First 3 blocks
                    text = self._extract_text_from_block(block)
                    if text:
                        preview_text += text + " "
                        if len(preview_text) > 100:
                            break

                metadata["content_preview"] = preview_text[:100].strip() + (
                    "..." if len(preview_text) > 100 else ""
                )
            except Exception as e:
                metadata["content_preview"] = f"Error: {str(e)}"

        # Include child count
        if include_child_count:
            try:
                if doc_object == "page":
                    blocks = await client.get_block_children(doc_id)
                    metadata["child_blocks_count"] = len(blocks.results)
                elif doc_object == "database":
                    # For databases, count pages
                    db_results = await client.query_database(doc_id, page_size=1)
                    metadata["child_pages_count"] = db_results.get("total_count", 0)
            except Exception as e:
                metadata["child_count_error"] = str(e)

        return metadata

    async def _get_database_pages(
        self, client: NotionClient, database_id: str, limit: int
    ) -> List[Dict[str, Any]]:
        """Get pages from a database, working around SDK parsing issues."""
        try:
            # Make direct HTTP call to avoid SDK parsing issues
            import httpx

            headers = {
                "Authorization": f"Bearer {client.auth_token}",
                "Notion-Version": client.API_VERSION,
                "Content-Type": "application/json",
            }

            url = f"{client.BASE_URL}databases/{database_id}/query"
            payload = {"page_size": min(limit, 100)}

            async with httpx.AsyncClient() as http_client:
                response = await http_client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

            pages_metadata = []
            for page_data in data.get("results", []):
                try:
                    # Extract basic metadata without using the SDK parsing
                    page_metadata = {
                        "id": page_data.get("id"),
                        "object": "page",
                        "title": self._extract_title_from_raw_data(page_data),
                        "url": page_data.get("url"),
                        "created_time": page_data.get("created_time"),
                        "last_edited_time": page_data.get("last_edited_time"),
                        "archived": page_data.get("archived", False),
                        "source": "database_page",
                    }

                    # Add basic properties if available
                    if page_data.get("properties"):
                        page_metadata["custom_properties"] = self._extract_raw_properties(
                            page_data["properties"]
                        )

                    pages_metadata.append(page_metadata)

                except Exception as e:
                    logger.warning(f"Failed to parse page data: {e}")
                    continue

            return pages_metadata

        except Exception as e:
            logger.error(f"Failed to get database pages: {e}")
            return []

    def _extract_title_from_raw_data(self, page_data: Dict[str, Any]) -> str:
        """Extract title from raw API response data."""
        try:
            properties = page_data.get("properties", {})

            # Look for title property
            for prop_name, prop_value in properties.items():
                if isinstance(prop_value, dict) and prop_value.get("type") == "title":
                    title_items = prop_value.get("title", [])
                    if title_items and len(title_items) > 0:
                        first_item = title_items[0]
                        if isinstance(first_item, dict):
                            return first_item.get("plain_text", "Untitled")

            return "Untitled"
        except Exception:
            return "Untitled"

    def _extract_raw_properties(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Extract properties from raw API data."""
        extracted = {}

        for prop_name, prop_value in properties.items():
            try:
                if not isinstance(prop_value, dict):
                    continue

                prop_type = prop_value.get("type")

                if prop_type == "title":
                    title_items = prop_value.get("title", [])
                    if title_items:
                        extracted[prop_name] = (
                            title_items[0].get("plain_text", "") if title_items else ""
                        )
                elif prop_type == "rich_text":
                    text_items = prop_value.get("rich_text", [])
                    extracted[prop_name] = " ".join(
                        [item.get("plain_text", "") for item in text_items]
                    )
                elif prop_type == "select":
                    select_value = prop_value.get("select")
                    extracted[prop_name] = select_value.get("name") if select_value else None
                elif prop_type == "multi_select":
                    multi_select = prop_value.get("multi_select", [])
                    extracted[prop_name] = [
                        item.get("name") for item in multi_select if isinstance(item, dict)
                    ]
                elif prop_type == "number":
                    extracted[prop_name] = prop_value.get("number")
                elif prop_type == "checkbox":
                    extracted[prop_name] = prop_value.get("checkbox", False)
                elif prop_type == "date":
                    date_value = prop_value.get("date")
                    if date_value:
                        extracted[prop_name] = date_value.get("start")
                elif prop_type in ["created_time", "last_edited_time"]:
                    extracted[prop_name] = prop_value.get(prop_type)
                else:
                    # For other types, store the type info
                    extracted[prop_name] = f"[{prop_type}]"

            except Exception as e:
                extracted[prop_name] = f"Error: {str(e)}"

        return extracted

    def _extract_property_value(self, prop_value: Any) -> Any:
        """Extract readable value from Notion property."""
        if isinstance(prop_value, dict):
            prop_type = prop_value.get("type")

            if prop_type == "title":
                title_items = prop_value.get("title", [])
                return " ".join([item.get("text", {}).get("content", "") for item in title_items])

            elif prop_type == "rich_text":
                rich_text_items = prop_value.get("rich_text", [])
                return " ".join(
                    [item.get("text", {}).get("content", "") for item in rich_text_items]
                )

            elif prop_type == "select":
                select_value = prop_value.get("select")
                return select_value.get("name") if select_value else None

            elif prop_type == "multi_select":
                multi_select_values = prop_value.get("multi_select", [])
                return [item.get("name") for item in multi_select_values]

            elif prop_type == "date":
                date_value = prop_value.get("date")
                if date_value:
                    return {
                        "start": date_value.get("start"),
                        "end": date_value.get("end"),
                        "time_zone": date_value.get("time_zone"),
                    }

            elif prop_type == "number":
                return prop_value.get("number")

            elif prop_type == "checkbox":
                return prop_value.get("checkbox")

            elif prop_type == "url":
                return prop_value.get("url")

            elif prop_type == "email":
                return prop_value.get("email")

            elif prop_type == "phone_number":
                return prop_value.get("phone_number")

            elif prop_type == "status":
                status_value = prop_value.get("status")
                return status_value.get("name") if status_value else None

            elif prop_type == "people":
                people_items = prop_value.get("people", [])
                return [person.get("name", person.get("id")) for person in people_items]

            else:
                return str(prop_value)

        return str(prop_value)

    def _sort_documents_metadata(
        self, documents: List[Dict], sort_by: str, sort_order: str
    ) -> List[Dict]:
        """Sort documents by specified criteria."""
        reverse = sort_order == "desc"

        try:
            if sort_by == "title":
                return sorted(documents, key=lambda d: d.get("title", "").lower(), reverse=reverse)
            elif sort_by == "created_time":
                return sorted(documents, key=lambda d: d.get("created_time", ""), reverse=reverse)
            elif sort_by == "last_edited_time":
                return sorted(
                    documents, key=lambda d: d.get("last_edited_time", ""), reverse=reverse
                )
            else:
                return documents
        except Exception as e:
            logger.warning(f"Failed to sort documents: {e}")
            return documents

    def _format_metadata_for_narrative(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format metadata listing results as narrative text."""
        documents = result["documents"]
        total_docs = result["total_documents"]
        search_query = result.get("search_query", "")

        if total_docs == 0:
            narrative = f"I found no Notion documents"
            if search_query:
                narrative += f" matching '{search_query}'"
            narrative += ". Try adjusting your search query or check if the content exists in your workspace."
        else:
            narrative = f"I found {total_docs} Notion document{'s' if total_docs != 1 else ''}"
            if search_query:
                narrative += f" matching '{search_query}'"
            narrative += ":\n\n"

            for i, doc in enumerate(documents[:15], 1):  # Show first 15
                if doc.get("error"):
                    narrative += f"{i}. ❌ Error: {doc['error']}\n"
                    continue

                title = doc.get("title", "Untitled")
                doc_type = doc.get("object", "unknown")
                narrative += f"{i}. **{title}** ({doc_type})\n"

                # Add timestamps
                if doc.get("last_edited_time"):
                    date_str = doc["last_edited_time"][:10]  # Extract date part
                    narrative += f"   📅 Last edited: {date_str}\n"

                # Add URL
                if doc.get("url"):
                    narrative += f"   🔗 {doc['url']}\n"

                # Add content preview if available
                if doc.get("content_preview"):
                    narrative += f"   📝 Preview: {doc['content_preview']}\n"

                # Add custom properties preview
                custom_props = doc.get("custom_properties", {})
                if custom_props:
                    prop_summary = []
                    for prop_name, prop_value in list(custom_props.items())[
                        :3
                    ]:  # First 3 properties
                        if prop_value and str(prop_value).strip():
                            prop_summary.append(f"{prop_name}: {str(prop_value)[:30]}")
                    if prop_summary:
                        narrative += f"   🏷️ Properties: {', '.join(prop_summary)}\n"

                narrative += "\n"

            if total_docs > 15:
                narrative += f"... and {total_docs - 15} more documents\n"

        return {**result, "ai_narrative": narrative, "format_type": "narrative"}

    def _format_metadata_for_summary(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format metadata listing results as summary."""
        documents = result["documents"]

        # Count by type
        pages = len([d for d in documents if d.get("object") == "page"])
        databases = len([d for d in documents if d.get("object") == "database"])
        errors = len([d for d in documents if d.get("error")])

        # Analyze properties
        all_properties = set()
        for doc in documents:
            custom_props = doc.get("custom_properties", {})
            all_properties.update(custom_props.keys())

        # Find recent activity
        recent_docs = []
        for doc in documents[:5]:  # Top 5 most recent
            if not doc.get("error"):
                recent_docs.append(
                    {
                        "title": doc.get("title", "Untitled"),
                        "type": doc.get("object", "unknown"),
                        "last_edited": doc.get("last_edited_time", "")[:10]
                        if doc.get("last_edited_time")
                        else None,
                        "has_preview": bool(doc.get("content_preview")),
                        "property_count": len(doc.get("custom_properties", {})),
                    }
                )

        summary = {
            "query_successful": result["total_documents"] > 0,
            "total_found": result["total_documents"],
            "search_query": result.get("search_query"),
            "breakdown": {"pages": pages, "databases": databases, "errors": errors},
            "properties_found": list(all_properties)[:10],  # First 10 property types
            "recent_documents": recent_docs,
            "sort_criteria": {
                "sort_by": result.get("sort_by"),
                "sort_order": result.get("sort_order"),
            },
        }

        return {**result, "ai_summary": summary, "format_type": "summary"}

    def _format_for_narrative(self, result: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Format search results as narrative text for conversational AI."""
        results = result["results"]
        total_count = result["total_count"]

        if not results:
            narrative = f"I found no Notion content matching '{query}'. You might want to try different search terms or check if the content exists in your workspace."
        else:
            narrative = f"I found {total_count} Notion items matching '{query}':\n\n"

            for i, item in enumerate(results, 1):
                narrative += f"{i}. **{item['title']}** ({item['object']})\n"
                if item.get("url"):
                    narrative += f"   Link: {item['url']}\n"
                if item.get("relevance_score"):
                    narrative += f"   Relevance: {item['relevance_score']}/10\n"

                # Add content preview if available
                if item.get("content") and len(item["content"]) > 0:
                    content_preview = str(item["content"][:150]).strip()
                    if content_preview:
                        narrative += f"   Preview: {content_preview}...\n"
                narrative += "\n"

        return {**result, "ai_narrative": narrative, "format_type": "narrative"}

    def _format_for_summary(self, result: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Format search results as condensed summary for efficient AI processing."""
        results = result["results"]
        total_count = result["total_count"]

        # Create condensed summaries
        summaries = []
        for item in results[:5]:  # Limit to top 5 for summary
            summary = {
                "title": item["title"],
                "type": item["object"],
                "relevance": item.get("relevance_score", 0),
                "url": item.get("url"),
            }

            # Add key content indicators
            if item.get("content"):
                summary["has_content"] = True
                summary["content_length"] = len(str(item["content"]))
            else:
                summary["has_content"] = False

            summaries.append(summary)

        return {
            **result,
            "ai_summary": {
                "query": query,
                "total_found": total_count,
                "top_results": summaries,
                "search_successful": total_count > 0,
            },
            "format_type": "summary",
        }

    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific streamlined tool."""
        tools_map = {
            "notion_search": {
                "name": "notion_search",
                "description": "Universal search across all Notion content types with AI-optimized formatting",
                "version": "3.1.0",
                "available": True,
                "category": "notion",
                "optimized_for": ["OpenAI GPT", "Claude", "Gemini"],
                "features": ["Relevance scoring", "AI-specific formatting", "Content preview"],
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
