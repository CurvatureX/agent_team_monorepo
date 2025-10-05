"""
Notion API client implementation.

Provides a comprehensive client for interacting with the Notion API,
including pages, databases, blocks, and search operations.
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

import httpx

from .exceptions import (
    NotionAPIError,
    NotionAuthError,
    NotionConflictError,
    NotionObjectNotFoundError,
    NotionPermissionError,
    NotionRateLimitError,
    NotionServiceUnavailableError,
    NotionValidationError,
)
from .models import (
    BlockType,
    NotionBlock,
    NotionDatabase,
    NotionPage,
    NotionSearchResult,
    NotionUser,
)


class NotionClient:
    """
    Notion API client for interacting with pages, databases, and blocks.

    This client handles authentication, rate limiting, and provides methods for
    common Notion operations like reading/writing pages, querying databases,
    and managing blocks.
    """

    BASE_URL = "https://api.notion.com/v1/"
    API_VERSION = "2022-06-28"

    def __init__(
        self,
        auth_token: str,
        timeout: int = 30,
        rate_limit_retry: bool = True,
        max_retries: int = 3,
    ):
        """
        Initialize Notion API client.

        Args:
            auth_token: Notion API token (starts with secret_)
            timeout: Request timeout in seconds
            rate_limit_retry: Whether to automatically retry on rate limit
            max_retries: Maximum number of retries for failed requests
        """
        self.auth_token = auth_token
        self.timeout = timeout
        self.rate_limit_retry = rate_limit_retry
        self.max_retries = max_retries

        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=self.timeout,
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Notion-Version": self.API_VERSION,
                "Content-Type": "application/json",
            },
        )

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict:
        """
        Make a request to the Notion API with retry logic.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint (without base URL)
            data: Request data for POST/PATCH
            params: Query parameters for GET

        Returns:
            Response data as dictionary

        Raises:
            NotionAPIError: For various API errors
            NotionAuthError: For authentication errors
            NotionRateLimitError: For rate limit errors
        """
        url = urljoin(self.BASE_URL, endpoint)

        for attempt in range(self.max_retries + 1):
            try:
                if method.upper() in ["POST", "PATCH"]:
                    response = await self.client.request(method, url, json=data)
                else:
                    response = await self.client.request(method, url, params=params)

                # Handle rate limiting at HTTP level
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    if self.rate_limit_retry and attempt < self.max_retries:
                        await asyncio.sleep(retry_after)
                        continue
                    raise NotionRateLimitError(
                        f"Rate limit exceeded. Retry after {retry_after} seconds",
                        retry_after=retry_after,
                        status_code=429,
                    )

                # Handle other HTTP errors
                if not response.is_success:
                    self._handle_http_error(response)

                response_data = response.json()
                return response_data

            except httpx.RequestError as e:
                if attempt == self.max_retries:
                    raise NotionAPIError(f"Request failed: {str(e)}")
                await asyncio.sleep(2**attempt)  # Exponential backoff

        raise NotionAPIError("Max retries exceeded")

    def _handle_http_error(self, response: httpx.Response) -> None:
        """Handle HTTP error responses."""
        try:
            error_data = response.json()
            message = error_data.get("message", f"HTTP {response.status_code}")
            code = error_data.get("code", "unknown_error")
        except:
            message = f"HTTP {response.status_code}"
            code = "unknown_error"

        if response.status_code == 400:
            raise NotionValidationError(message, error_code=code, status_code=response.status_code)
        elif response.status_code == 401:
            raise NotionAuthError(message, error_code=code)
        elif response.status_code == 403:
            raise NotionPermissionError(message, error_code=code)
        elif response.status_code == 404:
            raise NotionObjectNotFoundError(message, error_code=code)
        elif response.status_code == 409:
            raise NotionConflictError(message, error_code=code)
        elif response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            raise NotionRateLimitError(message, retry_after=retry_after, error_code=code)
        elif response.status_code == 503:
            raise NotionServiceUnavailableError(message, error_code=code)
        else:
            raise NotionAPIError(message, error_code=code, status_code=response.status_code)

    # Page operations
    async def get_page(self, page_id: str) -> NotionPage:
        """
        Retrieve a page by ID.

        Args:
            page_id: The page ID to retrieve

        Returns:
            NotionPage object

        Raises:
            NotionObjectNotFoundError: If page doesn't exist
            NotionPermissionError: If insufficient permissions
        """
        response = await self._make_request("GET", f"pages/{page_id}")
        return NotionPage.from_dict(response)

    async def create_page(
        self,
        parent: Dict[str, Any],
        properties: Dict[str, Any],
        children: Optional[List[Dict[str, Any]]] = None,
        icon: Optional[Dict[str, Any]] = None,
        cover: Optional[Dict[str, Any]] = None,
    ) -> NotionPage:
        """
        Create a new page.

        Args:
            parent: Parent page or database reference
            properties: Page properties
            children: Initial child blocks
            icon: Page icon
            cover: Page cover

        Returns:
            Created NotionPage object
        """
        data = {
            "parent": parent,
            "properties": properties,
        }

        if children:
            data["children"] = children
        if icon:
            data["icon"] = icon
        if cover:
            data["cover"] = cover

        response = await self._make_request("POST", "pages", data)
        return NotionPage.from_dict(response)

    async def update_page(
        self,
        page_id: str,
        properties: Optional[Dict[str, Any]] = None,
        archived: Optional[bool] = None,
        icon: Optional[Dict[str, Any]] = None,
        cover: Optional[Dict[str, Any]] = None,
    ) -> NotionPage:
        """
        Update a page.

        Args:
            page_id: Page ID to update
            properties: Properties to update
            archived: Whether to archive the page
            icon: New icon
            cover: New cover

        Returns:
            Updated NotionPage object
        """
        data = {}

        if properties is not None:
            data["properties"] = properties
        if archived is not None:
            data["archived"] = archived
        if icon is not None:
            data["icon"] = icon
        if cover is not None:
            data["cover"] = cover

        response = await self._make_request("PATCH", f"pages/{page_id}", data)
        return NotionPage.from_dict(response)

    # Database operations
    async def get_database(self, database_id: str) -> NotionDatabase:
        """
        Retrieve a database by ID.

        Args:
            database_id: The database ID to retrieve

        Returns:
            NotionDatabase object
        """
        response = await self._make_request("GET", f"databases/{database_id}")
        return NotionDatabase.from_dict(response)

    async def query_database(
        self,
        database_id: str,
        filter_conditions: Optional[Dict[str, Any]] = None,
        sorts: Optional[List[Dict[str, Any]]] = None,
        start_cursor: Optional[str] = None,
        page_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Query a database.

        Args:
            database_id: Database ID to query
            filter_conditions: Filter conditions
            sorts: Sort criteria
            start_cursor: Pagination cursor
            page_size: Number of results per page

        Returns:
            Query results with pages and pagination info
        """
        data = {"page_size": min(page_size, 100)}

        if filter_conditions:
            data["filter"] = filter_conditions
        if sorts:
            data["sorts"] = sorts
        if start_cursor:
            data["start_cursor"] = start_cursor

        response = await self._make_request("POST", f"databases/{database_id}/query", data)

        # Convert pages to NotionPage objects
        pages = [NotionPage.from_dict(page_data) for page_data in response.get("results", [])]

        return {
            "pages": pages,
            "next_cursor": response.get("next_cursor"),
            "has_more": response.get("has_more", False),
            "total_count": len(pages),
        }

    async def create_database(
        self,
        parent: Dict[str, Any],
        title: List[Dict[str, Any]],
        properties: Dict[str, Any],
        icon: Optional[Dict[str, Any]] = None,
        cover: Optional[Dict[str, Any]] = None,
        description: Optional[List[Dict[str, Any]]] = None,
    ) -> NotionDatabase:
        """
        Create a new database.

        Args:
            parent: Parent page reference
            title: Database title
            properties: Database properties schema
            icon: Database icon
            cover: Database cover
            description: Database description

        Returns:
            Created NotionDatabase object
        """
        data = {
            "parent": parent,
            "title": title,
            "properties": properties,
        }

        if icon:
            data["icon"] = icon
        if cover:
            data["cover"] = cover
        if description:
            data["description"] = description

        response = await self._make_request("POST", "databases", data)
        return NotionDatabase.from_dict(response)

    async def update_database(
        self,
        database_id: str,
        title: Optional[List[Dict[str, Any]]] = None,
        properties: Optional[Dict[str, Any]] = None,
        description: Optional[List[Dict[str, Any]]] = None,
        icon: Optional[Dict[str, Any]] = None,
        cover: Optional[Dict[str, Any]] = None,
    ) -> NotionDatabase:
        """
        Update a database.

        Args:
            database_id: Database ID to update
            title: New title
            properties: Properties schema updates
            description: New description
            icon: New icon
            cover: New cover

        Returns:
            Updated NotionDatabase object
        """
        data = {}

        if title is not None:
            data["title"] = title
        if properties is not None:
            data["properties"] = properties
        if description is not None:
            data["description"] = description
        if icon is not None:
            data["icon"] = icon
        if cover is not None:
            data["cover"] = cover

        response = await self._make_request("PATCH", f"databases/{database_id}", data)
        return NotionDatabase.from_dict(response)

    # Block operations
    async def get_block(self, block_id: str) -> NotionBlock:
        """
        Retrieve a block by ID.

        Args:
            block_id: Block ID to retrieve

        Returns:
            NotionBlock object
        """
        response = await self._make_request("GET", f"blocks/{block_id}")
        return NotionBlock.from_dict(response)

    async def get_block_children(
        self,
        block_id: str,
        start_cursor: Optional[str] = None,
        page_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Get children of a block.

        Args:
            block_id: Parent block ID
            start_cursor: Pagination cursor
            page_size: Number of results per page

        Returns:
            Children blocks and pagination info
        """
        params = {"page_size": min(page_size, 100)}

        if start_cursor:
            params["start_cursor"] = start_cursor

        response = await self._make_request("GET", f"blocks/{block_id}/children", params=params)

        blocks = [NotionBlock.from_dict(block_data) for block_data in response.get("results", [])]

        return {
            "blocks": blocks,
            "next_cursor": response.get("next_cursor"),
            "has_more": response.get("has_more", False),
            "total_count": len(blocks),
        }

    async def append_block_children(
        self,
        block_id: str,
        children: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Append children to a block.

        Args:
            block_id: Parent block ID
            children: Child blocks to append

        Returns:
            Response with appended blocks
        """
        data = {"children": children}
        response = await self._make_request("PATCH", f"blocks/{block_id}/children", data)

        blocks = [NotionBlock.from_dict(block_data) for block_data in response.get("results", [])]

        return {
            "blocks": blocks,
            "next_cursor": response.get("next_cursor"),
            "has_more": response.get("has_more", False),
        }

    async def update_block(
        self,
        block_id: str,
        block_data: Dict[str, Any],
        archived: Optional[bool] = None,
    ) -> NotionBlock:
        """
        Update a block.

        Args:
            block_id: Block ID to update
            block_data: Block content to update
            archived: Whether to archive the block

        Returns:
            Updated NotionBlock object
        """
        data = {}
        data.update(block_data)

        if archived is not None:
            data["archived"] = archived

        response = await self._make_request("PATCH", f"blocks/{block_id}", data)
        return NotionBlock.from_dict(response)

    async def delete_block(self, block_id: str) -> NotionBlock:
        """
        Delete (archive) a block.

        Args:
            block_id: Block ID to delete

        Returns:
            Deleted NotionBlock object
        """
        response = await self._make_request("DELETE", f"blocks/{block_id}")
        return NotionBlock.from_dict(response)

    # Search operations
    async def search(
        self,
        query: Optional[str] = None,
        filter_conditions: Optional[Dict[str, Any]] = None,
        sort: Optional[Dict[str, Any]] = None,
        start_cursor: Optional[str] = None,
        page_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Search across pages and databases.

        Args:
            query: Search query string
            filter_conditions: Filter conditions
            sort: Sort criteria
            start_cursor: Pagination cursor
            page_size: Number of results per page

        Returns:
            Search results with pagination info
        """
        data = {"page_size": min(page_size, 100)}

        if query:
            data["query"] = query
        if filter_conditions:
            data["filter"] = filter_conditions
        if sort:
            data["sort"] = sort
        if start_cursor:
            data["start_cursor"] = start_cursor

        response = await self._make_request("POST", "search", data)

        results = []
        for result_data in response.get("results", []):
            if result_data.get("object") == "page":
                results.append(NotionPage.from_dict(result_data))
            elif result_data.get("object") == "database":
                results.append(NotionDatabase.from_dict(result_data))

        return {
            "results": results,
            "next_cursor": response.get("next_cursor"),
            "has_more": response.get("has_more", False),
            "total_count": len(results),
        }

    async def list_databases(
        self,
        query: Optional[str] = None,
        start_cursor: Optional[str] = None,
        page_size: int = 100,
        sort: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """List databases accessible to the integration token.

        Args:
            query: Optional search keyword to narrow down databases
            start_cursor: Pagination cursor from previous call
            page_size: Number of databases per page (max 100)
            sort: Optional sort directive following Notion API format

        Returns:
            Dict containing databases list and pagination metadata
        """

        payload: Dict[str, Any] = {"page_size": min(page_size, 100)}

        if query:
            payload["query"] = query

        payload["filter"] = {"property": "object", "value": "database"}

        if sort:
            payload["sort"] = sort

        if start_cursor:
            payload["start_cursor"] = start_cursor

        response = await self._make_request("POST", "search", payload)

        databases = [
            NotionDatabase.from_dict(result)
            for result in response.get("results", [])
            if result.get("object") == "database"
        ]

        return {
            "databases": databases,
            "next_cursor": response.get("next_cursor"),
            "has_more": response.get("has_more", False),
            "total_count": len(databases),
        }

    # User operations
    async def get_user(self, user_id: str) -> NotionUser:
        """
        Get user information.

        Args:
            user_id: User ID to retrieve

        Returns:
            NotionUser object
        """
        response = await self._make_request("GET", f"users/{user_id}")
        return NotionUser.from_dict(response)

    async def list_users(
        self,
        start_cursor: Optional[str] = None,
        page_size: int = 100,
    ) -> Dict[str, Any]:
        """
        List all users in the workspace.

        Args:
            start_cursor: Pagination cursor
            page_size: Number of results per page

        Returns:
            Users list with pagination info
        """
        params = {"page_size": min(page_size, 100)}

        if start_cursor:
            params["start_cursor"] = start_cursor

        response = await self._make_request("GET", "users", params=params)

        users = [NotionUser.from_dict(user_data) for user_data in response.get("results", [])]

        return {
            "users": users,
            "next_cursor": response.get("next_cursor"),
            "has_more": response.get("has_more", False),
            "total_count": len(users),
        }

    async def get_me(self) -> NotionUser:
        """
        Get the current bot user information.

        Returns:
            NotionUser object for the bot
        """
        response = await self._make_request("GET", "users/me")
        return NotionUser.from_dict(response)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
