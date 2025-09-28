"""
Notion external action for workflow_engine_v2.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import httpx

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models import ExecutionStatus, NodeExecutionResult
from workflow_engine_v2.core.context import NodeExecutionContext

from .base_external_action import BaseExternalAction


class NotionExternalAction(BaseExternalAction):
    """Notion external action handler for workflow_engine_v2."""

    def __init__(self):
        super().__init__("notion")

    async def handle_operation(
        self, context: NodeExecutionContext, operation: str
    ) -> NodeExecutionResult:
        """Handle Notion-specific operations."""
        try:
            # Get Notion OAuth token from oauth_tokens table
            notion_token = await self.get_oauth_token(context)

            if not notion_token:
                error_msg = "❌ No Notion authentication token found. Please connect your Notion account in integrations settings."
                self.log_execution(context, error_msg, "ERROR")
                return self.create_error_result(error_msg, operation)

            # Prepare headers with OAuth token
            headers = {
                "Authorization": f"Bearer {notion_token}",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28",
            }

            # Handle different Notion operations
            if operation.lower() in ["search", "search_pages"]:
                return await self._search_pages(context, headers)
            elif operation.lower() in ["create_page", "create-page"]:
                return await self._create_page(context, headers)
            elif operation.lower() in ["update_page", "update-page", "page_update"]:
                return await self._update_page(context, headers)
            elif operation.lower() in ["get_page", "get-page"]:
                return await self._get_page(context, headers)
            elif operation.lower() in ["list_databases", "get_databases"]:
                return await self._list_databases(context, headers)
            else:
                # Default: search pages
                return await self._search_pages(context, headers)

        except Exception as e:
            self.log_execution(context, f"Notion action failed: {str(e)}", "ERROR")
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=f"Notion action failed: {str(e)}",
                error_details={"integration_type": "notion", "operation": operation},
            )

    async def _search_pages(
        self, context: NodeExecutionContext, headers: dict
    ) -> NodeExecutionResult:
        """Search Notion pages."""
        # Get search query
        query = (
            context.input_data.get("query")
            or context.input_data.get("search_query")
            or context.node.configurations.get("query")
            or ""
        )

        # Get optional filter parameters
        filter_value = context.node.configurations.get("filter", "page")  # page or database
        page_size = context.node.configurations.get("page_size", 10)

        payload = {
            "query": query,
            "filter": {"value": filter_value, "property": "object"},
            "page_size": page_size,
        }

        self.log_execution(context, f"Searching Notion pages with query: '{query}'")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.notion.com/v1/search",
                headers=headers,
                json=payload,
                timeout=30.0,
            )

        if response.status_code == 200:
            result = response.json()
            pages = result.get("results", [])
            self.log_execution(context, f"✅ Found {len(pages)} Notion pages")

            pages_data = []
            for page in pages:
                page_info = {
                    "id": page.get("id"),
                    "title": self._extract_title(page),
                    "url": page.get("url"),
                    "created_time": page.get("created_time"),
                    "last_edited_time": page.get("last_edited_time"),
                    "object": page.get("object"),
                }

                # Add parent info if available
                parent = page.get("parent")
                if parent:
                    page_info["parent_type"] = parent.get("type")
                    page_info["parent_id"] = parent.get(parent.get("type") + "_id")

                pages_data.append(page_info)

            return self.create_success_result(
                "search_pages",
                {
                    "query": query,
                    "pages_count": len(pages_data),
                    "pages": pages_data,
                    "has_more": result.get("has_more", False),
                },
            )
        else:
            error = f"Notion API error: {response.status_code} - {response.text}"
            self.log_execution(context, f"❌ {error}", "ERROR")
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=error,
                error_details={"status_code": response.status_code, "response": response.text},
            )

    async def _create_page(
        self, context: NodeExecutionContext, headers: dict
    ) -> NodeExecutionResult:
        """Create a Notion page."""
        # Get parent database/page ID
        parent_id = (
            context.input_data.get("parent_id")
            or context.node.configurations.get("parent_id")
            or context.node.configurations.get("database_id")
        )

        if not parent_id:
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message="Notion create page requires 'parent_id' or 'database_id' parameter",
                error_details={"operation": "create_page", "missing": ["parent_id"]},
            )

        # Get page title
        title = (
            context.input_data.get("title")
            or context.node.configurations.get("title")
            or "Workflow Generated Page"
        )

        # Get page content
        content = (
            context.input_data.get("content")
            or context.input_data.get("message")
            or context.node.configurations.get("content")
            or "This page was created by a workflow automation."
        )

        # Create page payload
        payload = {
            "parent": {"database_id": parent_id}
            if len(parent_id) == 32
            else {"page_id": parent_id},
            "properties": {"title": {"title": [{"text": {"content": title}}]}},
            "children": [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"text": {"content": content}}]},
                }
            ],
        }

        self.log_execution(context, f"Creating Notion page: {title}")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.notion.com/v1/pages",
                headers=headers,
                json=payload,
                timeout=30.0,
            )

        if response.status_code == 200:
            result = response.json()
            self.log_execution(context, f"✅ Notion page created successfully")

            return self.create_success_result(
                "create_page",
                {
                    "page_id": result.get("id"),
                    "page_url": result.get("url"),
                    "title": self._extract_title(result),
                    "created_time": result.get("created_time"),
                    "parent_id": parent_id,
                },
            )
        else:
            error = f"Notion API error: {response.status_code} - {response.text}"
            self.log_execution(context, f"❌ {error}", "ERROR")
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=error,
                error_details={"status_code": response.status_code, "response": response.text},
            )

    async def _update_page(
        self, context: NodeExecutionContext, headers: dict
    ) -> NodeExecutionResult:
        """Update a Notion page."""
        # Get page ID to update
        page_id = context.input_data.get("page_id") or context.node.configurations.get("page_id")

        if not page_id:
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message="Notion update page requires 'page_id' parameter",
                error_details={"operation": "update_page", "missing": ["page_id"]},
            )

        # Get update properties
        properties = {}

        # Update title if provided
        title = context.input_data.get("title") or context.node.configurations.get("title")
        if title:
            properties["title"] = {"title": [{"text": {"content": title}}]}

        # Add other properties from configurations
        custom_properties = context.node.configurations.get("properties", {})
        properties.update(custom_properties)

        if not properties:
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message="No update properties provided",
                error_details={"operation": "update_page", "page_id": page_id},
            )

        payload = {"properties": properties}

        self.log_execution(context, f"Updating Notion page: {page_id}")

        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"https://api.notion.com/v1/pages/{page_id}",
                headers=headers,
                json=payload,
                timeout=30.0,
            )

        if response.status_code == 200:
            result = response.json()
            self.log_execution(context, f"✅ Notion page updated successfully")

            return self.create_success_result(
                "update_page",
                {
                    "page_id": result.get("id"),
                    "page_url": result.get("url"),
                    "title": self._extract_title(result),
                    "last_edited_time": result.get("last_edited_time"),
                },
            )
        else:
            error = f"Notion API error: {response.status_code} - {response.text}"
            self.log_execution(context, f"❌ {error}", "ERROR")
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=error,
                error_details={"status_code": response.status_code, "response": response.text},
            )

    async def _get_page(self, context: NodeExecutionContext, headers: dict) -> NodeExecutionResult:
        """Get a Notion page."""
        # Get page ID
        page_id = context.input_data.get("page_id") or context.node.configurations.get("page_id")

        if not page_id:
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message="Notion get page requires 'page_id' parameter",
                error_details={"operation": "get_page", "missing": ["page_id"]},
            )

        self.log_execution(context, f"Getting Notion page: {page_id}")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.notion.com/v1/pages/{page_id}",
                headers=headers,
                timeout=30.0,
            )

        if response.status_code == 200:
            result = response.json()
            self.log_execution(context, f"✅ Notion page retrieved successfully")

            return self.create_success_result(
                "get_page",
                {
                    "page_id": result.get("id"),
                    "page_url": result.get("url"),
                    "title": self._extract_title(result),
                    "created_time": result.get("created_time"),
                    "last_edited_time": result.get("last_edited_time"),
                    "properties": result.get("properties", {}),
                },
            )
        else:
            error = f"Notion API error: {response.status_code} - {response.text}"
            self.log_execution(context, f"❌ {error}", "ERROR")
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=error,
                error_details={"status_code": response.status_code, "response": response.text},
            )

    async def _list_databases(
        self, context: NodeExecutionContext, headers: dict
    ) -> NodeExecutionResult:
        """List accessible Notion databases."""
        payload = {
            "filter": {"value": "database", "property": "object"},
            "page_size": 100,
        }

        self.log_execution(context, "Listing Notion databases")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.notion.com/v1/search",
                headers=headers,
                json=payload,
                timeout=30.0,
            )

        if response.status_code == 200:
            result = response.json()
            databases = result.get("results", [])
            self.log_execution(context, f"✅ Found {len(databases)} Notion databases")

            databases_data = []
            for db in databases:
                databases_data.append(
                    {
                        "id": db.get("id"),
                        "title": self._extract_title(db),
                        "url": db.get("url"),
                        "created_time": db.get("created_time"),
                        "last_edited_time": db.get("last_edited_time"),
                        "properties": list(db.get("properties", {}).keys()),
                    }
                )

            return self.create_success_result(
                "list_databases",
                {
                    "databases_count": len(databases_data),
                    "databases": databases_data,
                    "has_more": result.get("has_more", False),
                },
            )
        else:
            error = f"Notion API error: {response.status_code} - {response.text}"
            self.log_execution(context, f"❌ {error}", "ERROR")
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=error,
                error_details={"status_code": response.status_code, "response": response.text},
            )

    def _extract_title(self, page_or_db: dict) -> str:
        """Extract title from Notion page or database."""
        properties = page_or_db.get("properties", {})

        # Look for title property
        for prop_name, prop_value in properties.items():
            if prop_value.get("type") == "title":
                title_list = prop_value.get("title", [])
                if title_list:
                    return title_list[0].get("text", {}).get("content", "Untitled")

        # Fallback to object title if available
        if "title" in page_or_db:
            title_list = page_or_db.get("title", [])
            if title_list:
                return title_list[0].get("text", {}).get("content", "Untitled")

        return "Untitled"


__all__ = ["NotionExternalAction"]
