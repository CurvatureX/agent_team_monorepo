"""
Notion external action for external actions.
"""

import asyncio
import socket
from datetime import datetime
from typing import Any, Dict

import httpx
from nodes.base import ExecutionStatus, NodeExecutionContext, NodeExecutionResult

from .base_external_action import BaseExternalAction


class NotionExternalAction(BaseExternalAction):
    """Notion external action handler."""

    def __init__(self):
        super().__init__("notion")

    async def _make_resilient_request(
        self,
        method: str,
        url: str,
        headers: dict,
        json_data: dict = None,
        context: NodeExecutionContext = None,
        max_retries: int = 3,
        base_delay: float = 1.0,
    ) -> httpx.Response:
        """Make HTTP request with retry logic for DNS and connection failures."""
        last_exception = None

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    if method.upper() == "POST":
                        response = await client.post(
                            url, headers=headers, json=json_data, timeout=30.0
                        )
                    else:
                        response = await client.get(url, headers=headers, timeout=30.0)
                    return response

            except (socket.gaierror, httpx.ConnectError, httpx.TimeoutException) as e:
                last_exception = e
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)  # Exponential backoff
                    if context:
                        self.log_execution(
                            context,
                            f"⚠️ Request failed (attempt {attempt + 1}/{max_retries}): {str(e)}. Retrying in {delay}s...",
                            "WARNING",
                        )
                    await asyncio.sleep(delay)
                else:
                    if context:
                        self.log_execution(
                            context,
                            f"❌ All {max_retries} retry attempts failed. Last error: {str(e)}",
                            "ERROR",
                        )
                    raise e
            except Exception as e:
                # For non-network errors, don't retry
                if context:
                    self.log_execution(context, f"❌ Non-retryable error: {str(e)}", "ERROR")
                raise e

        # This should never be reached, but just in case
        raise last_exception if last_exception else Exception("Unknown error in resilient request")

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
                "Notion-Version": "2022-06-28",  # Required by Notion API
            }

            # Handle different Notion operations
            if operation.lower() in ["create_page", "create-page"]:
                return await self._create_page(context, headers)
            elif operation.lower() in ["update_page", "update-page"]:
                return await self._update_page(context, headers)
            elif operation.lower() in ["query_database", "query-database"]:
                return await self._query_database(context, headers)
            elif operation.lower() in ["get_page", "get-page"]:
                return await self._get_page(context, headers)
            elif operation.lower() in ["list_databases", "list-databases"]:
                return await self._list_databases(context, headers)
            else:
                # Default: list databases
                return await self._list_databases(context, headers)

        except Exception as e:
            self.log_execution(context, f"Notion action failed: {str(e)}", "ERROR")
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=f"Notion action failed: {str(e)}",
                error_details={"integration_type": "notion", "operation": operation},
            )

    async def _create_page(
        self, context: NodeExecutionContext, headers: dict
    ) -> NodeExecutionResult:
        """Create a Notion page."""
        # Get parent (database ID or page ID)
        parent_id = context.get_parameter("parent_id") or context.get_parameter("database_id")
        parent_type = context.get_parameter("parent_type", "database_id")  # or "page_id"

        if not parent_id:
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message="Notion create page requires 'parent_id' or 'database_id' parameter",
                error_details={"operation": "create_page", "missing": ["parent_id"]},
            )

        # Get page content
        title = (
            context.get_parameter("title")
            or context.input_data.get("title")
            or "Workflow Generated Page"
        )
        content = (
            context.get_parameter("content")
            or context.get_parameter("body")
            or context.input_data.get("message")
            or context.input_data.get("content")
            or "This page was created by a workflow automation."
        )

        # Build payload
        payload = {
            "parent": {parent_type: parent_id},
            "properties": {},
            "children": [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"type": "text", "text": {"content": content}}]},
                }
            ],
        }

        # Add title property for database pages
        if parent_type == "database_id":
            title_property = context.get_parameter(
                "title_property", "title"
            )  # Default property name
            payload["properties"][title_property] = {
                "title": [{"type": "text", "text": {"content": title}}]
            }

        # Add additional properties if provided
        properties = context.get_parameter("properties", {})
        if isinstance(properties, dict):
            payload["properties"].update(properties)

        self.log_execution(context, f"Creating Notion page: {title}")

        response = await self._make_resilient_request(
            "POST", "https://api.notion.com/v1/pages", headers, payload, context
        )

        if response.status_code == 200:
            result = response.json()
            self.log_execution(context, f"✅ Notion page created successfully: {result.get('id')}")

            return self.create_success_result(
                "create_page",
                {
                    "page_id": result.get("id"),
                    "page_url": result.get("url"),
                    "title": title,
                    "parent_id": parent_id,
                    "parent_type": parent_type,
                    "created_time": result.get("created_time"),
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

    async def _query_database(
        self, context: NodeExecutionContext, headers: dict
    ) -> NodeExecutionResult:
        """Query a Notion database."""
        # Get database ID
        database_id = context.get_parameter("database_id")

        if not database_id:
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message="Notion query database requires 'database_id' parameter",
                error_details={"operation": "query_database", "missing": ["database_id"]},
            )

        # Build query payload
        payload = {}

        # Add filter if provided
        filter_conditions = context.get_parameter("filter")
        if filter_conditions:
            payload["filter"] = filter_conditions

        # Add sorts if provided
        sorts = context.get_parameter("sorts")
        if sorts:
            payload["sorts"] = sorts

        # Add page size limit
        page_size = context.get_parameter("page_size", 10)
        payload["page_size"] = min(page_size, 100)  # Notion API max is 100

        self.log_execution(context, f"Querying Notion database: {database_id}")

        response = await self._make_resilient_request(
            "POST",
            f"https://api.notion.com/v1/databases/{database_id}/query",
            headers,
            payload,
            context,
        )

        if response.status_code == 200:
            result = response.json()
            pages = result.get("results", [])
            self.log_execution(context, f"✅ Retrieved {len(pages)} pages from Notion database")

            # Process pages data
            pages_data = []
            for page in pages:
                page_data = {
                    "id": page.get("id"),
                    "url": page.get("url"),
                    "created_time": page.get("created_time"),
                    "last_edited_time": page.get("last_edited_time"),
                    "properties": {},
                }

                # Extract property values
                properties = page.get("properties", {})
                for prop_name, prop_data in properties.items():
                    prop_type = prop_data.get("type")
                    if prop_type == "title":
                        titles = prop_data.get("title", [])
                        page_data["properties"][prop_name] = " ".join(
                            [t.get("plain_text", "") for t in titles]
                        )
                    elif prop_type == "rich_text":
                        texts = prop_data.get("rich_text", [])
                        page_data["properties"][prop_name] = " ".join(
                            [t.get("plain_text", "") for t in texts]
                        )
                    elif prop_type == "select":
                        select_data = prop_data.get("select")
                        page_data["properties"][prop_name] = (
                            select_data.get("name") if select_data else None
                        )
                    elif prop_type == "number":
                        page_data["properties"][prop_name] = prop_data.get("number")
                    elif prop_type == "checkbox":
                        page_data["properties"][prop_name] = prop_data.get("checkbox")
                    elif prop_type == "date":
                        date_data = prop_data.get("date")
                        page_data["properties"][prop_name] = (
                            date_data.get("start") if date_data else None
                        )
                    else:
                        # For other types, store raw data
                        page_data["properties"][prop_name] = prop_data

                pages_data.append(page_data)

            return self.create_success_result(
                "query_database",
                {
                    "database_id": database_id,
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

    async def _get_page(self, context: NodeExecutionContext, headers: dict) -> NodeExecutionResult:
        """Get a Notion page."""
        # Get page ID
        page_id = context.get_parameter("page_id")

        if not page_id:
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message="Notion get page requires 'page_id' parameter",
                error_details={"operation": "get_page", "missing": ["page_id"]},
            )

        self.log_execution(context, f"Getting Notion page: {page_id}")

        response = await self._make_resilient_request(
            "GET", f"https://api.notion.com/v1/pages/{page_id}", headers, None, context
        )

        if response.status_code == 200:
            result = response.json()
            self.log_execution(context, f"✅ Retrieved Notion page successfully")

            # Extract basic page information
            page_data = {
                "id": result.get("id"),
                "url": result.get("url"),
                "created_time": result.get("created_time"),
                "last_edited_time": result.get("last_edited_time"),
                "archived": result.get("archived"),
                "properties": {},
            }

            # Extract property values
            properties = result.get("properties", {})
            for prop_name, prop_data in properties.items():
                prop_type = prop_data.get("type")
                if prop_type == "title":
                    titles = prop_data.get("title", [])
                    page_data["properties"][prop_name] = " ".join(
                        [t.get("plain_text", "") for t in titles]
                    )
                elif prop_type == "rich_text":
                    texts = prop_data.get("rich_text", [])
                    page_data["properties"][prop_name] = " ".join(
                        [t.get("plain_text", "") for t in texts]
                    )
                # Add other property types as needed

            return self.create_success_result(
                "get_page",
                {
                    "page": page_data,
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
        """List Notion databases (using search endpoint)."""
        # Build search payload to find databases
        payload = {
            "filter": {"value": "database", "property": "object"},
            "page_size": context.get_parameter("page_size", 10),
        }

        self.log_execution(context, "Listing Notion databases")

        response = await self._make_resilient_request(
            "POST", "https://api.notion.com/v1/search", headers, payload, context
        )

        if response.status_code == 200:
            result = response.json()
            databases = result.get("results", [])
            self.log_execution(context, f"✅ Retrieved {len(databases)} Notion databases")

            # Process databases data
            databases_data = []
            for db in databases:
                db_data = {
                    "id": db.get("id"),
                    "url": db.get("url"),
                    "title": "",
                    "created_time": db.get("created_time"),
                    "last_edited_time": db.get("last_edited_time"),
                    "archived": db.get("archived"),
                }

                # Extract title from properties
                title_prop = db.get("title", [])
                if title_prop:
                    db_data["title"] = " ".join([t.get("plain_text", "") for t in title_prop])

                databases_data.append(db_data)

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

    async def _update_page(
        self, context: NodeExecutionContext, headers: dict
    ) -> NodeExecutionResult:
        """Update a Notion page."""
        return NodeExecutionResult(
            status=ExecutionStatus.ERROR,
            error_message="Notion update page operation not implemented",
            error_details={
                "operation": "update_page",
                "reason": "feature_not_implemented",
                "solution": "Implement Notion page update functionality or use create_page operation",
                "alternatives": ["create_page", "query_database"],
            },
            metadata={
                "node_type": "external_action",
                "integration": "notion",
                "operation": "update_page",
            },
        )
