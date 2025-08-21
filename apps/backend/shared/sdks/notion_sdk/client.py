"""
Notion SDK client implementation.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlencode

import httpx

from .exceptions import (
    NotionError,
    NotionAuthError,
    NotionPermissionError,
    NotionNotFoundError,
    NotionValidationError,
    NotionRateLimitError,
    NotionConflictError,
    NotionServerError,
    NotionConnectionError,
)
from .models import (
    Database,
    Page,
    Block,
    User,
    SearchResult,
    QueryResult,
    RichText,
)

logger = logging.getLogger(__name__)


class NotionSDK:
    """
    Notion SDK for comprehensive Notion API integration.
    
    This SDK provides:
    - Database operations (list, query, create)
    - Page operations (create, get, update, archive)
    - Block operations (get, append, update, delete)
    - Search functionality
    - User management
    - OAuth2 token management
    """
    
    BASE_URL = "https://api.notion.com/v1"
    API_VERSION = "2022-06-28"
    
    def __init__(self, access_token: Optional[str] = None, api_version: Optional[str] = None):
        """
        Initialize Notion SDK.
        
        Args:
            access_token: Notion access token (OAuth2 or Internal Integration)
            api_version: Notion API version to use (defaults to 2022-06-28)
        """
        self.access_token = access_token
        self.api_version = api_version or self.API_VERSION
        self._client = httpx.AsyncClient(timeout=30.0)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def set_access_token(self, access_token: str):
        """Update the access token."""
        self.access_token = access_token
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        if not self.access_token:
            raise NotionAuthError("Access token not set")
        
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Notion-Version": self.api_version,
        }
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Notion API.
        
        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint (without base URL)
            json_data: JSON body for POST/PATCH requests
            params: Query parameters
        
        Returns:
            API response as dictionary
        
        Raises:
            Various NotionError subclasses based on response
        """
        url = f"{self.BASE_URL}/{endpoint}"
        headers = self._get_headers()
        
        try:
            response = await self._client.request(
                method=method,
                url=url,
                headers=headers,
                json=json_data,
                params=params,
            )
        except httpx.ConnectError as e:
            raise NotionConnectionError(f"Failed to connect to Notion API: {str(e)}")
        except httpx.TimeoutException as e:
            raise NotionConnectionError(f"Request timed out: {str(e)}")
        except Exception as e:
            raise NotionError(f"Unexpected error: {str(e)}")
        
        # Handle response
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 204:
            return {"success": True}
        else:
            self._handle_error_response(response)
    
    def _handle_error_response(self, response: httpx.Response):
        """Handle error responses from Notion API."""
        try:
            error_data = response.json()
            error_code = error_data.get("code", "unknown")
            error_message = error_data.get("message", "Unknown error")
        except json.JSONDecodeError:
            error_code = "unknown"
            error_message = response.text or "Unknown error"
        
        if response.status_code == 400:
            raise NotionValidationError(error_message, error_code=error_code)
        elif response.status_code == 401:
            raise NotionAuthError(error_message, error_code=error_code)
        elif response.status_code == 403:
            raise NotionPermissionError(error_message, error_code=error_code)
        elif response.status_code == 404:
            raise NotionNotFoundError(error_message, error_code=error_code)
        elif response.status_code == 409:
            raise NotionConflictError(error_message, error_code=error_code)
        elif response.status_code == 429:
            retry_after = response.headers.get("retry-after")
            raise NotionRateLimitError(
                error_message,
                retry_after=int(retry_after) if retry_after else None,
                error_code=error_code
            )
        elif 500 <= response.status_code < 600:
            raise NotionServerError(error_message, error_code=error_code)
        else:
            raise NotionError(error_message, error_code=error_code)
    
    # Database Operations
    
    async def list_databases(
        self,
        page_size: int = 100,
        start_cursor: Optional[str] = None
    ) -> SearchResult:
        """
        List all databases accessible to the integration.
        
        Args:
            page_size: Number of results per page (max 100)
            start_cursor: Pagination cursor
        
        Returns:
            SearchResult containing databases
        """
        payload = {
            "filter": {"value": "database", "property": "object"},
            "page_size": min(page_size, 100)
        }
        
        if start_cursor:
            payload["start_cursor"] = start_cursor
        
        response = await self._make_request("POST", "search", json_data=payload)
        return SearchResult.from_dict(response)
    
    async def query_database(
        self,
        database_id: str,
        filter: Optional[Dict[str, Any]] = None,
        sorts: Optional[List[Dict[str, Any]]] = None,
        page_size: int = 100,
        start_cursor: Optional[str] = None
    ) -> QueryResult:
        """
        Query a database with optional filtering and sorting.
        
        Args:
            database_id: Database ID to query
            filter: Filter conditions
            sorts: Sort conditions
            page_size: Number of results per page (max 100)
            start_cursor: Pagination cursor
        
        Returns:
            QueryResult containing pages
        """
        payload = {
            "page_size": min(page_size, 100)
        }
        
        if filter:
            payload["filter"] = filter
        if sorts:
            payload["sorts"] = sorts
        if start_cursor:
            payload["start_cursor"] = start_cursor
        
        response = await self._make_request(
            "POST",
            f"databases/{database_id}/query",
            json_data=payload
        )
        return QueryResult.from_dict(response)
    
    async def create_database(
        self,
        parent: Dict[str, str],
        title: Union[str, List[RichText]],
        properties: Dict[str, Any],
        description: Optional[Union[str, List[RichText]]] = None,
        icon: Optional[Dict[str, Any]] = None,
        cover: Optional[Dict[str, Any]] = None
    ) -> Database:
        """
        Create a new database.
        
        Args:
            parent: Parent page or workspace
            title: Database title
            properties: Database properties schema
            description: Optional description
            icon: Optional icon
            cover: Optional cover image
        
        Returns:
            Created Database object
        """
        # Convert title to rich text if string
        if isinstance(title, str):
            title_rich_text = [RichText.from_string(title).to_dict()]
        else:
            title_rich_text = [rt.to_dict() for rt in title]
        
        payload = {
            "parent": parent,
            "title": title_rich_text,
            "properties": properties
        }
        
        if description:
            if isinstance(description, str):
                payload["description"] = [RichText.from_string(description).to_dict()]
            else:
                payload["description"] = [rt.to_dict() for rt in description]
        
        if icon:
            payload["icon"] = icon
        if cover:
            payload["cover"] = cover
        
        response = await self._make_request("POST", "databases", json_data=payload)
        return Database.from_dict(response)
    
    async def get_database(self, database_id: str) -> Database:
        """
        Retrieve a database by ID.
        
        Args:
            database_id: Database ID
        
        Returns:
            Database object
        """
        response = await self._make_request("GET", f"databases/{database_id}")
        return Database.from_dict(response)
    
    # Page Operations
    
    async def create_page(
        self,
        parent: Optional[Dict[str, str]] = None,
        database_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        children: Optional[List[Block]] = None,
        icon: Optional[Dict[str, Any]] = None,
        cover: Optional[Dict[str, Any]] = None
    ) -> Page:
        """
        Create a new page.
        
        Args:
            parent: Parent page or database (alternative to database_id)
            database_id: Database ID (shorthand for parent)
            properties: Page properties
            children: Initial content blocks
            icon: Optional icon
            cover: Optional cover image
        
        Returns:
            Created Page object
        """
        if database_id:
            parent = {"database_id": database_id}
        elif not parent:
            raise NotionValidationError("Either parent or database_id must be provided")
        
        payload = {
            "parent": parent,
            "properties": properties or {}
        }
        
        if children:
            payload["children"] = [block.to_dict() for block in children]
        if icon:
            payload["icon"] = icon
        if cover:
            payload["cover"] = cover
        
        response = await self._make_request("POST", "pages", json_data=payload)
        return Page.from_dict(response)
    
    async def get_page(self, page_id: str) -> Page:
        """
        Retrieve a page by ID.
        
        Args:
            page_id: Page ID
        
        Returns:
            Page object
        """
        response = await self._make_request("GET", f"pages/{page_id}")
        return Page.from_dict(response)
    
    async def update_page(
        self,
        page_id: str,
        properties: Optional[Dict[str, Any]] = None,
        icon: Optional[Dict[str, Any]] = None,
        cover: Optional[Dict[str, Any]] = None,
        archived: Optional[bool] = None
    ) -> Page:
        """
        Update a page's properties.
        
        Args:
            page_id: Page ID to update
            properties: Properties to update
            icon: Optional icon update
            cover: Optional cover update
            archived: Archive status
        
        Returns:
            Updated Page object
        """
        payload = {}
        
        if properties:
            payload["properties"] = properties
        if icon is not None:
            payload["icon"] = icon
        if cover is not None:
            payload["cover"] = cover
        if archived is not None:
            payload["archived"] = archived
        
        if not payload:
            raise NotionValidationError("No fields to update specified")
        
        response = await self._make_request("PATCH", f"pages/{page_id}", json_data=payload)
        return Page.from_dict(response)
    
    async def archive_page(self, page_id: str) -> Page:
        """
        Archive (soft delete) a page.
        
        Args:
            page_id: Page ID to archive
        
        Returns:
            Archived Page object
        """
        return await self.update_page(page_id, archived=True)
    
    # Block Operations
    
    async def get_blocks(
        self,
        block_id: str,
        page_size: int = 100,
        start_cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get child blocks of a block or page.
        
        Args:
            block_id: Block or page ID
            page_size: Number of results per page (max 100)
            start_cursor: Pagination cursor
        
        Returns:
            Dictionary with blocks, has_more, and next_cursor
        """
        params = {
            "page_size": min(page_size, 100)
        }
        
        if start_cursor:
            params["start_cursor"] = start_cursor
        
        response = await self._make_request(
            "GET",
            f"blocks/{block_id}/children",
            params=params
        )
        
        blocks = [Block.from_dict(item) for item in response.get("results", [])]
        
        return {
            "blocks": blocks,
            "has_more": response.get("has_more", False),
            "next_cursor": response.get("next_cursor")
        }
    
    async def append_blocks(
        self,
        block_id: str,
        children: List[Block],
        after: Optional[str] = None
    ) -> List[Block]:
        """
        Append blocks to a parent block or page.
        
        Args:
            block_id: Parent block or page ID
            children: Blocks to append
            after: Optional block ID to insert after
        
        Returns:
            List of created blocks
        """
        payload = {
            "children": [block.to_dict() for block in children]
        }
        
        if after:
            payload["after"] = after
        
        response = await self._make_request(
            "PATCH",
            f"blocks/{block_id}/children",
            json_data=payload
        )
        
        return [Block.from_dict(item) for item in response.get("results", [])]
    
    async def update_block(
        self,
        block_id: str,
        block: Block
    ) -> Block:
        """
        Update a block's content.
        
        Args:
            block_id: Block ID to update
            block: Updated block content
        
        Returns:
            Updated Block object
        """
        payload = {
            block.type: block.content
        }
        
        if block.archived is not None:
            payload["archived"] = block.archived
        
        response = await self._make_request(
            "PATCH",
            f"blocks/{block_id}",
            json_data=payload
        )
        
        return Block.from_dict(response)
    
    async def delete_block(self, block_id: str) -> bool:
        """
        Delete a block.
        
        Args:
            block_id: Block ID to delete
        
        Returns:
            True if successful
        """
        response = await self._make_request("DELETE", f"blocks/{block_id}")
        return response.get("success", True)
    
    # Search Operations
    
    async def search(
        self,
        query: Optional[str] = None,
        filter: Optional[Dict[str, Any]] = None,
        sort: Optional[Dict[str, Any]] = None,
        page_size: int = 100,
        start_cursor: Optional[str] = None
    ) -> SearchResult:
        """
        Search for pages and databases.
        
        Args:
            query: Search query text
            filter: Filter conditions
            sort: Sort configuration
            page_size: Number of results per page (max 100)
            start_cursor: Pagination cursor
        
        Returns:
            SearchResult with pages and databases
        """
        payload = {
            "page_size": min(page_size, 100)
        }
        
        if query:
            payload["query"] = query
        if filter:
            payload["filter"] = filter
        if sort:
            payload["sort"] = sort
        if start_cursor:
            payload["start_cursor"] = start_cursor
        
        response = await self._make_request("POST", "search", json_data=payload)
        return SearchResult.from_dict(response)
    
    # User Operations
    
    async def list_users(
        self,
        page_size: int = 100,
        start_cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List all users in the workspace.
        
        Args:
            page_size: Number of results per page (max 100)
            start_cursor: Pagination cursor
        
        Returns:
            Dictionary with users, has_more, and next_cursor
        """
        params = {
            "page_size": min(page_size, 100)
        }
        
        if start_cursor:
            params["start_cursor"] = start_cursor
        
        response = await self._make_request("GET", "users", params=params)
        
        users = [User.from_dict(item) for item in response.get("results", [])]
        
        return {
            "users": users,
            "has_more": response.get("has_more", False),
            "next_cursor": response.get("next_cursor")
        }
    
    async def get_user(self, user_id: str) -> User:
        """
        Get a specific user by ID.
        
        Args:
            user_id: User ID
        
        Returns:
            User object
        """
        response = await self._make_request("GET", f"users/{user_id}")
        return User.from_dict(response)
    
    async def get_me(self) -> User:
        """
        Get the current authenticated user.
        
        Returns:
            User object for authenticated user
        """
        response = await self._make_request("GET", "users/me")
        return User.from_dict(response)
    
    # Utility Methods
    
    async def test_connection(self) -> bool:
        """
        Test the connection and authentication.
        
        Returns:
            True if connection is successful
        """
        try:
            await self.get_me()
            return True
        except NotionError:
            return False
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()