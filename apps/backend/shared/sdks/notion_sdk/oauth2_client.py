"""
Notion OAuth2 Client for workflow integration.

This provides Notion OAuth2 authentication compatible with the BaseSDK pattern.
"""

import asyncio
import os
from typing import Any, Dict, Optional

from ..base import APIResponse, BaseSDK, OAuth2Config
from .client import NotionClient
from .exceptions import (
    NotionAPIError,
    NotionAuthError,
    NotionObjectNotFoundError,
    NotionRateLimitError,
    NotionValidationError,
)


class NotionOAuth2SDK(BaseSDK):
    """Notion SDK client with OAuth2 authentication."""

    @property
    def base_url(self) -> str:
        return "https://api.notion.com/v1"

    @property
    def supported_operations(self) -> Dict[str, str]:
        return {
            "get_page": "Retrieve a page by ID",
            "create_page": "Create a new page",
            "update_page": "Update an existing page",
            "get_database": "Retrieve a database by ID",
            "query_database": "Query a database with filters and sorts",
            "create_database": "Create a new database",
            "update_database": "Update an existing database",
            "get_block": "Retrieve a block by ID",
            "get_block_children": "Get children blocks of a parent block",
            "append_block_children": "Append child blocks to a parent",
            "update_block": "Update a block",
            "delete_block": "Delete (archive) a block",
            "search": "Search across pages and databases",
            "get_user": "Get user information",
            "list_users": "List all users in workspace",
            "get_me": "Get current bot user information",
        }

    def get_oauth2_config(self) -> OAuth2Config:
        """Get Notion OAuth2 configuration."""
        return OAuth2Config(
            client_id=os.getenv("NOTION_CLIENT_ID", ""),
            client_secret=os.getenv("NOTION_CLIENT_SECRET", ""),
            auth_url="https://api.notion.com/v1/oauth/authorize",
            token_url="https://api.notion.com/v1/oauth/token",
            scopes=[],  # Notion doesn't use traditional OAuth scopes
            redirect_uri=os.getenv(
                "NOTION_REDIRECT_URI", "http://localhost:8002/api/v1/oauth2/notion/callback"
            ),
        )

    def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """Validate Notion credentials."""
        return "access_token" in credentials and bool(credentials["access_token"])

    async def call_operation(
        self, operation: str, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> APIResponse:
        """Execute Notion API operation."""
        if not self.validate_credentials(credentials):
            return APIResponse(
                success=False,
                error="Invalid credentials: missing access_token",
                provider="notion",
                operation=operation,
            )

        if operation not in self.supported_operations:
            return APIResponse(
                success=False,
                error=f"Unsupported operation: {operation}",
                provider="notion",
                operation=operation,
            )

        try:
            # Route to specific operation handler
            handler_map = {
                "get_page": self._get_page,
                "create_page": self._create_page,
                "update_page": self._update_page,
                "get_database": self._get_database,
                "query_database": self._query_database,
                "create_database": self._create_database,
                "update_database": self._update_database,
                "get_block": self._get_block,
                "get_block_children": self._get_block_children,
                "append_block_children": self._append_block_children,
                "update_block": self._update_block,
                "delete_block": self._delete_block,
                "search": self._search,
                "get_user": self._get_user,
                "list_users": self._list_users,
                "get_me": self._get_me,
            }

            handler = handler_map[operation]
            result = await handler(parameters, credentials)

            return APIResponse(success=True, data=result, provider="notion", operation=operation)

        except NotionAuthError as e:
            return APIResponse(
                success=False, error=str(e), provider="notion", operation=operation, status_code=401
            )
        except NotionRateLimitError as e:
            return APIResponse(
                success=False, error=str(e), provider="notion", operation=operation, status_code=429
            )
        except NotionObjectNotFoundError as e:
            return APIResponse(
                success=False, error=str(e), provider="notion", operation=operation, status_code=404
            )
        except NotionValidationError as e:
            return APIResponse(
                success=False, error=str(e), provider="notion", operation=operation, status_code=400
            )
        except Exception as e:
            self.logger.error(f"Notion {operation} failed: {str(e)}")
            return APIResponse(success=False, error=str(e), provider="notion", operation=operation)

    def _get_client(self, credentials: Dict[str, str]) -> NotionClient:
        """Create a Notion client with the provided credentials."""
        return NotionClient(auth_token=credentials["access_token"])

    # Page operations
    async def _get_page(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Retrieve a page by ID."""
        page_id = parameters.get("page_id")
        if not page_id:
            raise NotionValidationError("Missing required parameter: page_id")

        async with self._get_client(credentials) as client:
            page = await client.get_page(page_id)
            return {
                "id": page.id,
                "url": page.url,
                "title": self._extract_page_title(page),
                "created_time": page.created_time.isoformat(),
                "last_edited_time": page.last_edited_time.isoformat(),
                "archived": page.archived,
                "properties": self._serialize_properties(page.properties),
                "parent": page.parent,
            }

    async def _create_page(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Create a new page."""
        parent = parameters.get("parent")
        properties = parameters.get("properties")

        if not parent:
            raise NotionValidationError("Missing required parameter: parent")
        if not properties:
            raise NotionValidationError("Missing required parameter: properties")

        children = parameters.get("children")
        icon = parameters.get("icon")
        cover = parameters.get("cover")

        async with self._get_client(credentials) as client:
            page = await client.create_page(
                parent=parent, properties=properties, children=children, icon=icon, cover=cover
            )
            return {
                "id": page.id,
                "url": page.url,
                "title": self._extract_page_title(page),
                "created_time": page.created_time.isoformat(),
                "properties": self._serialize_properties(page.properties),
            }

    async def _update_page(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Update an existing page."""
        page_id = parameters.get("page_id")
        if not page_id:
            raise NotionValidationError("Missing required parameter: page_id")

        properties = parameters.get("properties")
        archived = parameters.get("archived")
        icon = parameters.get("icon")
        cover = parameters.get("cover")

        async with self._get_client(credentials) as client:
            page = await client.update_page(
                page_id=page_id, properties=properties, archived=archived, icon=icon, cover=cover
            )
            return {
                "id": page.id,
                "url": page.url,
                "title": self._extract_page_title(page),
                "last_edited_time": page.last_edited_time.isoformat(),
                "archived": page.archived,
                "properties": self._serialize_properties(page.properties),
            }

    # Database operations
    async def _get_database(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Retrieve a database by ID."""
        database_id = parameters.get("database_id")
        if not database_id:
            raise NotionValidationError("Missing required parameter: database_id")

        async with self._get_client(credentials) as client:
            database = await client.get_database(database_id)
            return {
                "id": database.id,
                "url": database.url,
                "title": self._extract_title_text(database.title),
                "description": self._extract_title_text(database.description),
                "created_time": database.created_time.isoformat(),
                "last_edited_time": database.last_edited_time.isoformat(),
                "archived": database.archived,
                "properties": database.properties,
                "parent": database.parent,
            }

    async def _query_database(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Query a database with filters and sorts."""
        database_id = parameters.get("database_id")
        if not database_id:
            raise NotionValidationError("Missing required parameter: database_id")

        filter_conditions = parameters.get("filter")
        sorts = parameters.get("sorts")
        start_cursor = parameters.get("start_cursor")
        page_size = parameters.get("page_size", 100)

        async with self._get_client(credentials) as client:
            result = await client.query_database(
                database_id=database_id,
                filter_conditions=filter_conditions,
                sorts=sorts,
                start_cursor=start_cursor,
                page_size=page_size,
            )

            pages_data = []
            for page in result["pages"]:
                pages_data.append(
                    {
                        "id": page.id,
                        "url": page.url,
                        "title": self._extract_page_title(page),
                        "created_time": page.created_time.isoformat(),
                        "last_edited_time": page.last_edited_time.isoformat(),
                        "archived": page.archived,
                        "properties": self._serialize_properties(page.properties),
                    }
                )

            return {
                "pages": pages_data,
                "next_cursor": result["next_cursor"],
                "has_more": result["has_more"],
                "total_count": result["total_count"],
            }

    async def _create_database(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Create a new database."""
        parent = parameters.get("parent")
        title = parameters.get("title")
        properties = parameters.get("properties")

        if not parent:
            raise NotionValidationError("Missing required parameter: parent")
        if not title:
            raise NotionValidationError("Missing required parameter: title")
        if not properties:
            raise NotionValidationError("Missing required parameter: properties")

        icon = parameters.get("icon")
        cover = parameters.get("cover")
        description = parameters.get("description")

        async with self._get_client(credentials) as client:
            database = await client.create_database(
                parent=parent,
                title=title,
                properties=properties,
                icon=icon,
                cover=cover,
                description=description,
            )
            return {
                "id": database.id,
                "url": database.url,
                "title": self._extract_title_text(database.title),
                "created_time": database.created_time.isoformat(),
                "properties": database.properties,
            }

    async def _update_database(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Update an existing database."""
        database_id = parameters.get("database_id")
        if not database_id:
            raise NotionValidationError("Missing required parameter: database_id")

        title = parameters.get("title")
        properties = parameters.get("properties")
        description = parameters.get("description")
        icon = parameters.get("icon")
        cover = parameters.get("cover")

        async with self._get_client(credentials) as client:
            database = await client.update_database(
                database_id=database_id,
                title=title,
                properties=properties,
                description=description,
                icon=icon,
                cover=cover,
            )
            return {
                "id": database.id,
                "url": database.url,
                "title": self._extract_title_text(database.title),
                "last_edited_time": database.last_edited_time.isoformat(),
                "properties": database.properties,
            }

    # Block operations
    async def _get_block(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Retrieve a block by ID."""
        block_id = parameters.get("block_id")
        if not block_id:
            raise NotionValidationError("Missing required parameter: block_id")

        async with self._get_client(credentials) as client:
            block = await client.get_block(block_id)
            return {
                "id": block.id,
                "type": block.type.value,
                "has_children": block.has_children,
                "archived": block.archived,
                "created_time": block.created_time.isoformat(),
                "last_edited_time": block.last_edited_time.isoformat(),
                "content": block.content,
            }

    async def _get_block_children(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Get children blocks of a parent block."""
        block_id = parameters.get("block_id")
        if not block_id:
            raise NotionValidationError("Missing required parameter: block_id")

        start_cursor = parameters.get("start_cursor")
        page_size = parameters.get("page_size", 100)

        async with self._get_client(credentials) as client:
            result = await client.get_block_children(
                block_id=block_id, start_cursor=start_cursor, page_size=page_size
            )

            blocks_data = []
            for block in result["blocks"]:
                blocks_data.append(
                    {
                        "id": block.id,
                        "type": block.type.value,
                        "has_children": block.has_children,
                        "archived": block.archived,
                        "content": block.content,
                    }
                )

            return {
                "blocks": blocks_data,
                "next_cursor": result["next_cursor"],
                "has_more": result["has_more"],
                "total_count": result["total_count"],
            }

    async def _append_block_children(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Append child blocks to a parent."""
        block_id = parameters.get("block_id")
        children = parameters.get("children")

        if not block_id:
            raise NotionValidationError("Missing required parameter: block_id")
        if not children:
            raise NotionValidationError("Missing required parameter: children")

        async with self._get_client(credentials) as client:
            result = await client.append_block_children(block_id=block_id, children=children)

            blocks_data = []
            for block in result["blocks"]:
                blocks_data.append(
                    {
                        "id": block.id,
                        "type": block.type.value,
                        "has_children": block.has_children,
                        "content": block.content,
                    }
                )

            return {
                "blocks": blocks_data,
                "next_cursor": result.get("next_cursor"),
                "has_more": result.get("has_more", False),
            }

    async def _update_block(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Update a block."""
        block_id = parameters.get("block_id")
        if not block_id:
            raise NotionValidationError("Missing required parameter: block_id")

        block_data = parameters.get("block_data", {})
        archived = parameters.get("archived")

        async with self._get_client(credentials) as client:
            block = await client.update_block(
                block_id=block_id, block_data=block_data, archived=archived
            )
            return {
                "id": block.id,
                "type": block.type.value,
                "has_children": block.has_children,
                "archived": block.archived,
                "last_edited_time": block.last_edited_time.isoformat(),
                "content": block.content,
            }

    async def _delete_block(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Delete (archive) a block."""
        block_id = parameters.get("block_id")
        if not block_id:
            raise NotionValidationError("Missing required parameter: block_id")

        async with self._get_client(credentials) as client:
            block = await client.delete_block(block_id)
            return {
                "id": block.id,
                "type": block.type.value,
                "archived": block.archived,
                "last_edited_time": block.last_edited_time.isoformat(),
            }

    # Search operations
    async def _search(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Search across pages and databases."""
        query = parameters.get("query")
        filter_conditions = parameters.get("filter")
        sort = parameters.get("sort")
        start_cursor = parameters.get("start_cursor")
        page_size = parameters.get("page_size", 100)

        async with self._get_client(credentials) as client:
            result = await client.search(
                query=query,
                filter_conditions=filter_conditions,
                sort=sort,
                start_cursor=start_cursor,
                page_size=page_size,
            )

            results_data = []
            for item in result["results"]:
                if hasattr(item, "properties"):  # Page
                    results_data.append(
                        {
                            "object": "page",
                            "id": item.id,
                            "url": item.url,
                            "title": self._extract_page_title(item),
                            "created_time": item.created_time.isoformat(),
                            "last_edited_time": item.last_edited_time.isoformat(),
                            "archived": item.archived,
                        }
                    )
                else:  # Database
                    results_data.append(
                        {
                            "object": "database",
                            "id": item.id,
                            "url": item.url,
                            "title": self._extract_title_text(item.title),
                            "created_time": item.created_time.isoformat(),
                            "last_edited_time": item.last_edited_time.isoformat(),
                            "archived": item.archived,
                        }
                    )

            return {
                "results": results_data,
                "next_cursor": result["next_cursor"],
                "has_more": result["has_more"],
                "total_count": result["total_count"],
            }

    # User operations
    async def _get_user(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Get user information."""
        user_id = parameters.get("user_id")
        if not user_id:
            raise NotionValidationError("Missing required parameter: user_id")

        async with self._get_client(credentials) as client:
            user = await client.get_user(user_id)
            return {
                "id": user.id,
                "type": user.type,
                "name": user.name,
                "avatar_url": user.avatar_url,
                "person_email": user.person_email,
                "bot_name": user.bot_name,
            }

    async def _list_users(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """List all users in workspace."""
        start_cursor = parameters.get("start_cursor")
        page_size = parameters.get("page_size", 100)

        async with self._get_client(credentials) as client:
            result = await client.list_users(start_cursor=start_cursor, page_size=page_size)

            users_data = []
            for user in result["users"]:
                users_data.append(
                    {
                        "id": user.id,
                        "type": user.type,
                        "name": user.name,
                        "avatar_url": user.avatar_url,
                        "person_email": user.person_email,
                        "bot_name": user.bot_name,
                    }
                )

            return {
                "users": users_data,
                "next_cursor": result["next_cursor"],
                "has_more": result["has_more"],
                "total_count": result["total_count"],
            }

    async def _get_me(
        self, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Get current bot user information."""
        async with self._get_client(credentials) as client:
            user = await client.get_me()
            return {
                "id": user.id,
                "type": user.type,
                "name": user.name,
                "avatar_url": user.avatar_url,
                "bot_name": user.bot_name,
            }

    async def _test_connection_impl(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Notion specific connection test."""
        try:
            user_info = await self._get_me({}, credentials)
            return {
                "credentials_valid": True,
                "notion_access": True,
                "bot_name": user_info.get("name"),
                "bot_id": user_info.get("id"),
            }
        except Exception as e:
            return {"credentials_valid": False, "error": str(e)}

    # Helper methods
    def _extract_page_title(self, page) -> str:
        """Extract title from page properties."""
        for prop_name, prop in page.properties.items():
            if prop.type.value == "title" and prop.value:
                return prop.value
        return "Untitled"

    def _extract_title_text(self, title_array) -> str:
        """Extract text from title array."""
        if not title_array:
            return ""
        return "".join([text.get("plain_text", "") for text in title_array])

    def _serialize_properties(self, properties) -> Dict[str, Any]:
        """Serialize page properties for JSON response."""
        result = {}
        for prop_name, prop in properties.items():
            if hasattr(prop.value, "__dict__"):
                # Handle complex objects like NotionUser
                result[prop_name] = {
                    "type": prop.type.value,
                    "value": prop.value.__dict__ if hasattr(prop.value, "__dict__") else prop.value,
                }
            else:
                result[prop_name] = {"type": prop.type.value, "value": prop.value}
        return result
