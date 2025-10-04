"""
Notion External Action Implementation using shared Notion SDK.

This module handles all Notion operations through the centralized Notion SDK.
"""

from dataclasses import asdict
from typing import Any, Dict

from shared.models.execution_new import ExecutionStatus, NodeExecutionResult
from shared.sdks.notion_sdk.client import NotionClient
from shared.sdks.notion_sdk.exceptions import NotionAPIError
from workflow_engine_v2.core.context import NodeExecutionContext

from .base_external_action import BaseExternalAction


class NotionExternalAction(BaseExternalAction):
    """Notion external action using shared SDK."""

    def __init__(self):
        super().__init__(integration_name="notion")

    def _create_success_result(
        self,
        notion_response: Dict[str, Any],
        resource_id: str = "",
        resource_url: str = "",
        execution_metadata: Dict[str, Any] = None,
    ) -> NodeExecutionResult:
        """Create a success result matching the Notion spec output_params."""
        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            outputs={
                "success": True,
                "notion_response": notion_response,
                "resource_id": resource_id,
                "resource_url": resource_url,
                "error_message": "",
                "rate_limit_info": {},
                "execution_metadata": execution_metadata or {},
            },
        )

    async def handle_operation(
        self, context: NodeExecutionContext, operation: str
    ) -> NodeExecutionResult:
        """Handle Notion operations using the shared SDK."""
        try:
            # Get Notion OAuth token
            notion_token = await self.get_oauth_token(context)

            if not notion_token:
                error_msg = "❌ No Notion authentication token found. Please connect your Notion account in integrations settings."
                self.log_execution(context, error_msg, "ERROR")
                return self.create_error_result(error_msg, operation)

            # Initialize Notion SDK client
            async with NotionClient(auth_token=notion_token) as client:
                # Map operation to SDK method
                action_type = operation.lower().replace("-", "_")

                if action_type in ["search", "search_pages", "search_content"]:
                    return await self._search(context, client)
                elif action_type in ["get_page", "retrieve_page"]:
                    return await self._get_page(context, client)
                elif action_type in ["create_page"]:
                    return await self._create_page(context, client)
                elif action_type in ["update_page"]:
                    return await self._update_page(context, client)
                elif action_type in ["get_database", "retrieve_database"]:
                    return await self._get_database(context, client)
                elif action_type in ["query_database"]:
                    return await self._query_database(context, client)
                elif action_type in ["create_database"]:
                    return await self._create_database(context, client)
                elif action_type in ["update_database"]:
                    return await self._update_database(context, client)
                elif action_type in ["get_block", "retrieve_block"]:
                    return await self._get_block(context, client)
                elif action_type in ["get_block_children", "retrieve_block_children"]:
                    return await self._get_block_children(context, client)
                elif action_type in ["append_blocks", "append_block_children"]:
                    return await self._append_blocks(context, client)
                elif action_type in ["update_block"]:
                    return await self._update_block(context, client)
                elif action_type in ["delete_block"]:
                    return await self._delete_block(context, client)
                elif action_type in ["list_users"]:
                    return await self._list_users(context, client)
                elif action_type in ["get_user", "retrieve_user"]:
                    return await self._get_user(context, client)
                else:
                    supported = "search, get_page, create_page, update_page, get_database, query_database, create_database, update_database, get_block, get_block_children, append_blocks, update_block, delete_block, list_users, get_user"
                    error_msg = f"Unsupported Notion operation: {operation}. Supported: {supported}"
                    self.log_execution(context, error_msg, "ERROR")
                    return self.create_error_result(error_msg, operation)

        except NotionAPIError as e:
            error_msg = f"❌ Notion API error: {str(e)}"
            self.log_execution(context, error_msg, "ERROR")
            return self.create_error_result(error_msg, operation)
        except Exception as e:
            error_msg = f"❌ Notion action failed: {str(e)}"
            self.log_execution(context, error_msg, "ERROR")
            return self.create_error_result(error_msg, operation)

    async def _search(
        self, context: NodeExecutionContext, client: NotionClient
    ) -> NodeExecutionResult:
        """Search Notion workspace."""
        query = context.input_data.get("query", "")
        filter_type = context.input_data.get("filter", {}).get("value", "page")
        page_size = context.input_data.get("page_size", 10)

        self.log_execution(context, f"Searching Notion: query='{query}', filter={filter_type}")

        result = await client.search(query=query, filter_type=filter_type, page_size=page_size)

        self.log_execution(context, f"✅ Found {len(result.results)} items")

        return self._create_success_result(
            notion_response={
                "object": "list",
                "results": [asdict(item) for item in result.results],
                "has_more": result.has_more,
                "next_cursor": result.next_cursor,
            },
            resource_id="",
            resource_url="",
            execution_metadata={
                "action_type": "search",
                "query": query,
                "result_count": len(result.results),
            },
        )

    async def _get_page(
        self, context: NodeExecutionContext, client: NotionClient
    ) -> NodeExecutionResult:
        """Get a Notion page."""
        page_id = context.input_data.get("page_id", "").replace("-", "")

        if not page_id:
            return self.create_error_result("page_id is required", "get_page")

        page = await client.get_page(page_id)

        return self._create_success_result(
            notion_response=asdict(page),
            resource_id=page.id,
            resource_url=page.url,
            execution_metadata={"action_type": "get_page", "page_id": page_id},
        )

    async def _create_page(
        self, context: NodeExecutionContext, client: NotionClient
    ) -> NodeExecutionResult:
        """Create a Notion page."""
        parent = context.input_data.get("parent", {})
        properties = context.input_data.get("properties", {})
        children = context.input_data.get("children", [])

        if not parent:
            return self.create_error_result("parent is required", "create_page")

        page = await client.create_page(parent=parent, properties=properties, children=children)

        self.log_execution(context, f"✅ Created page: {page.id}")

        return self._create_success_result(
            notion_response=asdict(page),
            resource_id=page.id,
            resource_url=page.url,
            execution_metadata={"action_type": "create_page", "parent": parent},
        )

    async def _update_page(
        self, context: NodeExecutionContext, client: NotionClient
    ) -> NodeExecutionResult:
        """Update a Notion page."""
        page_id = context.input_data.get("page_id", "").replace("-", "")
        properties = context.input_data.get("properties", {})

        if not page_id:
            return self.create_error_result("page_id is required", "update_page")

        page = await client.update_page(page_id, properties)

        self.log_execution(context, f"✅ Updated page: {page_id}")

        return self._create_success_result(
            notion_response=asdict(page),
            resource_id=page.id,
            resource_url=page.url,
            execution_metadata={"action_type": "update_page", "page_id": page_id},
        )

    async def _get_database(
        self, context: NodeExecutionContext, client: NotionClient
    ) -> NodeExecutionResult:
        """Get a Notion database."""
        database_id = context.input_data.get("database_id", "").replace("-", "")

        if not database_id:
            return self.create_error_result("database_id is required", "get_database")

        database = await client.get_database(database_id)

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            outputs={
                "success": True,
                "database": asdict(database),
                "resource_id": database.id,
            },
        )

    async def _query_database(
        self, context: NodeExecutionContext, client: NotionClient
    ) -> NodeExecutionResult:
        """Query a Notion database."""
        database_id = context.input_data.get("database_id", "").replace("-", "")
        filter_conditions = context.input_data.get("filter")
        sorts = context.input_data.get("sorts", [])
        page_size = context.input_data.get("page_size", 100)

        if not database_id:
            return self.create_error_result("database_id is required", "query_database")

        result = await client.query_database(
            database_id, filter_conditions=filter_conditions, sorts=sorts, page_size=page_size
        )

        self.log_execution(context, f"✅ Queried database: {len(result['results'])} results")

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            outputs={
                "success": True,
                "results": result["results"],
                "has_more": result.get("has_more", False),
                "next_cursor": result.get("next_cursor"),
            },
        )

    async def _create_database(
        self, context: NodeExecutionContext, client: NotionClient
    ) -> NodeExecutionResult:
        """Create a Notion database."""
        parent = context.input_data.get("parent", {})
        title = context.input_data.get("title", [])
        properties = context.input_data.get("properties", {})

        if not parent:
            return self.create_error_result("parent is required", "create_database")

        database = await client.create_database(parent=parent, title=title, properties=properties)

        self.log_execution(context, f"✅ Created database: {database.id}")

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            outputs={
                "success": True,
                "database": asdict(database),
                "resource_id": database.id,
            },
        )

    async def _update_database(
        self, context: NodeExecutionContext, client: NotionClient
    ) -> NodeExecutionResult:
        """Update a Notion database."""
        database_id = context.input_data.get("database_id", "").replace("-", "")
        title = context.input_data.get("title")
        properties = context.input_data.get("properties")

        if not database_id:
            return self.create_error_result("database_id is required", "update_database")

        database = await client.update_database(database_id, title=title, properties=properties)

        self.log_execution(context, f"✅ Updated database: {database_id}")

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            outputs={
                "success": True,
                "database": asdict(database),
                "resource_id": database.id,
            },
        )

    async def _get_block(
        self, context: NodeExecutionContext, client: NotionClient
    ) -> NodeExecutionResult:
        """Get a Notion block."""
        block_id = context.input_data.get("block_id", "").replace("-", "")

        if not block_id:
            return self.create_error_result("block_id is required", "get_block")

        block = await client.get_block(block_id)

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            outputs={
                "success": True,
                "block": asdict(block),
                "resource_id": block.id,
            },
        )

    async def _get_block_children(
        self, context: NodeExecutionContext, client: NotionClient
    ) -> NodeExecutionResult:
        """Get children of a Notion block."""
        # Handle both direct input and conversion-function-wrapped input
        block_id = (
            context.input_data.get("block_id")
            or context.input_data.get("data", {}).get("block_id")
            or context.input_data.get("result", {}).get("data", {}).get("block_id")
            or ""
        )
        if block_id:
            block_id = block_id.replace("-", "")

        page_size = (
            context.input_data.get("page_size")
            or context.input_data.get("data", {}).get("page_size")
            or context.input_data.get("result", {}).get("data", {}).get("page_size")
            or 100
        )

        if not block_id:
            return self.create_error_result("block_id is required", "get_block_children")

        result = await client.get_block_children(block_id, page_size=page_size)

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            outputs={
                "success": True,
                "blocks": [asdict(block) for block in result["blocks"]],
                "has_more": result.get("has_more", False),
                "next_cursor": result.get("next_cursor"),
            },
        )

    async def _append_blocks(
        self, context: NodeExecutionContext, client: NotionClient
    ) -> NodeExecutionResult:
        """Append blocks to a Notion page or block."""
        # Get page_id or block_id and children from input
        # Handle both direct input and conversion-function-wrapped input (result.data)
        page_id = (
            context.input_data.get("page_id")
            or context.input_data.get("data", {}).get("page_id")
            or context.input_data.get("result", {})
            .get("data", {})
            .get("page_id")  # From conversion function
            or context.node.configurations.get("page_config", {}).get("parent", {}).get("page_id")
        )

        children = (
            context.input_data.get("children")
            or context.input_data.get("data", {}).get("children")
            or context.input_data.get("result", {})
            .get("data", {})
            .get("children")  # From conversion function
            or context.node.configurations.get("page_config", {}).get("children", [])
        )

        if not page_id:
            return self.create_error_result(
                "page_id is required for append_blocks", "append_blocks"
            )

        if not children:
            return self.create_error_result(
                "children blocks array is required for append_blocks", "append_blocks"
            )

        # Remove hyphens from page_id
        page_id = page_id.replace("-", "")

        self.log_execution(context, f"Appending {len(children)} block(s) to page {page_id[:8]}...")

        result = await client.append_block_children(block_id=page_id, children=children)

        self.log_execution(context, f"✅ Appended {len(children)} block(s) to page")

        return self._create_success_result(
            notion_response={
                "object": "list",
                "results": [asdict(block) for block in result["blocks"]],
                "next_cursor": result.get("next_cursor"),
                "has_more": result.get("has_more", False),
            },
            resource_id=page_id,
            resource_url=f"https://www.notion.so/{page_id}",
            execution_metadata={
                "action_type": "append_blocks",
                "page_id": page_id,
                "blocks_appended": len(children),
            },
        )

    async def _update_block(
        self, context: NodeExecutionContext, client: NotionClient
    ) -> NodeExecutionResult:
        """Update a Notion block."""
        block_id = context.input_data.get("block_id", "").replace("-", "")
        block_data = context.input_data.get("block_data", {})

        if not block_id:
            return self.create_error_result("block_id is required", "update_block")

        block = await client.update_block(block_id, block_data)

        self.log_execution(context, f"✅ Updated block: {block_id}")

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            outputs={
                "success": True,
                "block": asdict(block),
                "resource_id": block.id,
            },
        )

    async def _delete_block(
        self, context: NodeExecutionContext, client: NotionClient
    ) -> NodeExecutionResult:
        """Delete (archive) a Notion block."""
        block_id = context.input_data.get("block_id", "").replace("-", "")

        if not block_id:
            return self.create_error_result("block_id is required", "delete_block")

        block = await client.delete_block(block_id)

        self.log_execution(context, f"✅ Deleted block: {block_id}")

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            outputs={
                "success": True,
                "block": asdict(block),
                "resource_id": block.id,
            },
        )

    async def _list_users(
        self, context: NodeExecutionContext, client: NotionClient
    ) -> NodeExecutionResult:
        """List Notion workspace users."""
        page_size = context.input_data.get("page_size", 100)

        result = await client.list_users(page_size=page_size)

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            outputs={
                "success": True,
                "users": [asdict(user) for user in result["users"]],
                "has_more": result.get("has_more", False),
                "next_cursor": result.get("next_cursor"),
            },
        )

    async def _get_user(
        self, context: NodeExecutionContext, client: NotionClient
    ) -> NodeExecutionResult:
        """Get a Notion user."""
        user_id = context.input_data.get("user_id", "")

        if not user_id:
            return self.create_error_result("user_id is required", "get_user")

        user = await client.get_user(user_id)

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            outputs={
                "success": True,
                "user": asdict(user),
                "resource_id": user.id,
            },
        )
