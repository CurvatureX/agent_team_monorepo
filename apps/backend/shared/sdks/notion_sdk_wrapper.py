"""
Notion SDK wrapper for workflow engine integration.

This module provides a unified interface for Notion operations compatible with
the external action node system.
"""

import logging
from typing import Any, Dict, List, Optional

from .base import APIResponse, AuthenticationError, BaseSDK, OAuth2Config, SDKError
from .notion_sdk import NotionAPIError, NotionAuthError, NotionClient, NotionRateLimitError


class NotionSDK(BaseSDK):
    """Notion SDK wrapper for external action nodes."""

    def __init__(self):
        """Initialize Notion SDK wrapper."""
        super().__init__()
        self.logger = logging.getLogger(__name__)

    @property
    def base_url(self) -> str:
        """Get the base URL for the Notion API."""
        return "https://api.notion.com/v1/"

    @property
    def supported_operations(self) -> Dict[str, str]:
        """Get supported operations and their descriptions."""
        return {
            "search": "Search across pages and databases",
            "page_get": "Retrieve a page by ID",
            "page_create": "Create a new page",
            "page_update": "Update an existing page",
            "database_get": "Retrieve a database schema",
            "database_query": "Query database records",
        }

    def get_oauth2_config(self) -> OAuth2Config:
        """Get OAuth2 configuration for Notion."""
        return OAuth2Config(
            client_id="",  # To be configured by deployment
            client_secret="",  # To be configured by deployment
            auth_url="https://api.notion.com/v1/oauth/authorize",
            token_url="https://api.notion.com/v1/oauth/token",
            scopes=["read", "update", "insert"],
            redirect_uri="",  # To be configured by deployment
        )

    def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """Validate that the provided credentials are valid."""
        access_token = credentials.get("access_token")
        if not access_token:
            return False

        # Basic validation - token should start with 'secret_' for integration tokens
        # or be a valid OAuth token
        return len(access_token) > 10

    async def call_operation(
        self, operation: str, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> APIResponse:
        """
        Execute a Notion operation.

        Args:
            operation: Operation to perform
            parameters: Operation parameters
            credentials: Authentication credentials

        Returns:
            APIResponse with result or error
        """
        if operation not in self.supported_operations:
            return APIResponse(
                success=False, error=f"Unsupported operation: {operation}", status_code=400
            )

        access_token = credentials.get("access_token")
        if not access_token:
            return APIResponse(
                success=False, error="Missing access_token in credentials", status_code=401
            )

        try:
            async with NotionClient(auth_token=access_token) as client:
                if operation == "search":
                    return await self._handle_search(client, parameters)
                elif operation == "page_get":
                    return await self._handle_page_get(client, parameters)
                elif operation == "page_create":
                    return await self._handle_page_create(client, parameters)
                elif operation == "page_update":
                    return await self._handle_page_update(client, parameters)
                elif operation == "database_get":
                    return await self._handle_database_get(client, parameters)
                elif operation == "database_query":
                    return await self._handle_database_query(client, parameters)
                else:
                    return APIResponse(
                        success=False,
                        error=f"Operation {operation} not implemented",
                        status_code=501,
                    )

        except NotionAuthError as e:
            self.logger.error(f"Notion auth error: {e}")
            return APIResponse(
                success=False, error=f"Authentication failed: {str(e)}", status_code=401
            )
        except NotionRateLimitError as e:
            self.logger.warning(f"Notion rate limit: {e}")
            return APIResponse(
                success=False, error=f"Rate limit exceeded: {str(e)}", status_code=429
            )
        except NotionAPIError as e:
            self.logger.error(f"Notion API error: {e}")
            return APIResponse(
                success=False,
                error=f"API error: {str(e)}",
                status_code=getattr(e, "status_code", 500),
            )
        except Exception as e:
            self.logger.error(f"Unexpected error in Notion SDK: {e}")
            return APIResponse(success=False, error=f"Unexpected error: {str(e)}", status_code=500)

    async def _handle_search(self, client: NotionClient, parameters: Dict[str, Any]) -> APIResponse:
        """Handle Notion search operation."""
        query = parameters.get("query", "")
        search_filter = parameters.get("search_filter", {})
        limit = parameters.get("limit", 10)

        # Build filter conditions
        filter_conditions = None
        if search_filter:
            object_type = search_filter.get("object_type")
            if object_type in ["page", "database"]:
                filter_conditions = {"property": "object", "value": object_type}

        result = await client.search(
            query=query if query else None, filter_conditions=filter_conditions, page_size=limit
        )

        return APIResponse(
            success=True,
            data={
                "results": [self._serialize_object(obj) for obj in result["results"]],
                "total_count": result["total_count"],
                "has_more": result["has_more"],
                "next_cursor": result["next_cursor"],
            },
            status_code=200,
        )

    async def _handle_page_get(
        self, client: NotionClient, parameters: Dict[str, Any]
    ) -> APIResponse:
        """Handle get page operation."""
        page_id = parameters.get("page_id")
        include_content = parameters.get("include_content", False)

        if not page_id:
            return APIResponse(
                success=False, error="page_id is required for page_get operation", status_code=400
            )

        page = await client.get_page(page_id)
        page_data = self._serialize_object(page)

        # Optionally include page content
        if include_content:
            children = await client.get_block_children(page_id)
            page_data["content"] = {
                "blocks": [self._serialize_object(block) for block in children["blocks"]],
                "has_more": children["has_more"],
            }

        return APIResponse(success=True, data=page_data, status_code=200)

    async def _handle_page_create(
        self, client: NotionClient, parameters: Dict[str, Any]
    ) -> APIResponse:
        """Handle create page operation."""
        parent_id = parameters.get("parent_id")
        parent_type = parameters.get("parent_type", "page")
        properties = parameters.get("properties", {})
        content = parameters.get("content", {})

        if not parent_id:
            return APIResponse(
                success=False,
                error="parent_id is required for page_create operation",
                status_code=400,
            )

        # Build parent reference
        if parent_type == "database":
            parent = {"database_id": parent_id}
        else:
            parent = {"page_id": parent_id}

        # Create page
        children = content.get("blocks", []) if content else None
        page = await client.create_page(parent=parent, properties=properties, children=children)

        return APIResponse(
            success=True,
            data={"page": self._serialize_object(page), "url": getattr(page, "url", None)},
            status_code=201,
        )

    async def _handle_page_update(
        self, client: NotionClient, parameters: Dict[str, Any]
    ) -> APIResponse:
        """Handle update page operation."""
        page_id = parameters.get("page_id")
        properties = parameters.get("properties")
        content = parameters.get("content")
        block_operations = parameters.get("block_operations", [])

        if not page_id:
            return APIResponse(
                success=False,
                error="page_id is required for page_update operation",
                status_code=400,
            )

        operations_performed = []

        # Update page properties
        if properties:
            await client.update_page(page_id, properties=properties)
            operations_performed.append("updated_properties")

        # Handle content operations
        if content:
            blocks = content.get("blocks", [])
            mode = content.get("mode", "append")

            if blocks:
                if mode == "replace":
                    # For replace mode, would need to delete existing blocks first
                    # This is a simplified implementation
                    await client.append_block_children(page_id, blocks)
                    operations_performed.append("replaced_content")
                else:  # append mode
                    await client.append_block_children(page_id, blocks)
                    operations_performed.append("appended_content")

        # Handle advanced block operations
        for operation in block_operations:
            op_type = operation.get("operation")
            block_id = operation.get("block_id")
            block_data = operation.get("block_data")

            if op_type == "update" and block_id and block_data:
                await client.update_block(block_id, block_data)
                operations_performed.append(f"updated_block_{block_id}")
            elif op_type == "delete" and block_id:
                await client.delete_block(block_id)
                operations_performed.append(f"deleted_block_{block_id}")
            elif op_type == "append" and block_data:
                await client.append_block_children(page_id, [block_data])
                operations_performed.append("appended_block")

        # Get updated page
        updated_page = await client.get_page(page_id)

        return APIResponse(
            success=True,
            data={
                "page": self._serialize_object(updated_page),
                "operations_performed": operations_performed,
                "url": getattr(updated_page, "url", None),
            },
            status_code=200,
        )

    async def _handle_database_get(
        self, client: NotionClient, parameters: Dict[str, Any]
    ) -> APIResponse:
        """Handle get database operation."""
        database_id = parameters.get("database_id")

        if not database_id:
            return APIResponse(
                success=False,
                error="database_id is required for database_get operation",
                status_code=400,
            )

        database = await client.get_database(database_id)

        return APIResponse(success=True, data=self._serialize_object(database), status_code=200)

    async def _handle_database_query(
        self, client: NotionClient, parameters: Dict[str, Any]
    ) -> APIResponse:
        """Handle database query operation."""
        database_id = parameters.get("database_id")
        database_query = parameters.get("database_query", {})
        limit = parameters.get("limit", 10)

        if not database_id:
            return APIResponse(
                success=False,
                error="database_id is required for database_query operation",
                status_code=400,
            )

        # Extract query parameters
        filter_conditions = database_query.get("filter")
        sorts = database_query.get("sorts")
        simple_filter = database_query.get("simple_filter")

        # Handle simple filter conversion
        if simple_filter and not filter_conditions:
            property_name = simple_filter.get("property")
            property_value = simple_filter.get("value")
            if property_name and property_value:
                filter_conditions = {
                    "property": property_name,
                    "rich_text": {"contains": property_value},
                }

        result = await client.query_database(
            database_id=database_id,
            filter_conditions=filter_conditions,
            sorts=sorts,
            page_size=limit,
        )

        return APIResponse(
            success=True,
            data={
                "pages": [self._serialize_object(page) for page in result["pages"]],
                "total_count": result["total_count"],
                "has_more": result["has_more"],
                "next_cursor": result["next_cursor"],
            },
            status_code=200,
        )

    def _serialize_object(self, obj: Any) -> Dict[str, Any]:
        """Serialize Notion objects to dictionaries."""
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        elif hasattr(obj, "__dict__"):
            return obj.__dict__
        else:
            return {"object": str(obj)}
