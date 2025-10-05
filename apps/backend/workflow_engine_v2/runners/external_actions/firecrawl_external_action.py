"""
Firecrawl external action for workflow_engine_v2 using official firecrawl-py SDK.

This implementation uses the official Firecrawl SDK (firecrawl-py) for web scraping operations,
strictly following the node specification in shared/node_specs/EXTERNAL_ACTION/FIRECRAWL.py.

Official SDK: pip install firecrawl-py
Docs: https://docs.firecrawl.dev/sdks/python
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from firecrawl import FirecrawlApp

from shared.models import ExecutionStatus, NodeExecutionResult
from workflow_engine_v2.core.context import NodeExecutionContext

from .base_external_action import BaseExternalAction


class FirecrawlExternalAction(BaseExternalAction):
    """
    Firecrawl external action handler using official firecrawl-py SDK.

    Follows node spec output format:
    - success: boolean
    - content: string (extracted content)
    - data: object (structured data for extract)
    - urls_processed: array (list of processed URLs)
    - error_message: string
    - stats: object (execution statistics)
    """

    def __init__(self):
        super().__init__("firecrawl")

    async def handle_operation(
        self, context: NodeExecutionContext, operation: str
    ) -> NodeExecutionResult:
        """Handle Firecrawl operation - delegates to execute for API key auth."""
        # For Firecrawl, we override execute() since it uses API key auth, not OAuth
        # This method satisfies the abstract base class requirement
        return await self.execute(context)

    async def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute Firecrawl-specific operations using official SDK."""
        try:
            # Get API key from configurations
            api_key = context.node.configurations.get("firecrawl_api_key", "")

            if not api_key:
                return self._create_spec_error_result(
                    "Firecrawl API key not found. Please add firecrawl_api_key to node configurations.",
                    "execute",
                    {
                        "reason": "missing_api_key",
                        "solution": "Set firecrawl_api_key in node configurations",
                    },
                )

            # Initialize official Firecrawl SDK
            app = FirecrawlApp(api_key=api_key)

            # Get action_type from input_params or configurations
            action_type = context.input_data.get("action_type") or context.node.configurations.get(
                "action_type", "scrape"
            )

            self.log_execution(context, f"Executing Firecrawl operation: {action_type}")

            # Execute action using official SDK
            result = await self._execute_action(app, context, action_type)

            return result

        except Exception as e:
            self.log_execution(context, f"Unexpected error: {str(e)}", "ERROR")
            return self._create_spec_error_result(
                f"Firecrawl action failed: {str(e)}",
                action_type if "action_type" in locals() else "unknown",
                {"exception_type": type(e).__name__, "exception": str(e)},
            )

    async def _execute_action(
        self, app: FirecrawlApp, context: NodeExecutionContext, action_type: str
    ) -> NodeExecutionResult:
        """Execute specific Firecrawl action using official SDK methods."""
        url = context.input_data.get("url")

        try:
            if action_type == "scrape":
                # Scrape single URL
                if not url:
                    raise ValueError("Missing required parameter: url")

                params = {"formats": [context.input_data.get("format", "markdown")]}
                if context.input_data.get("include_selectors"):
                    params["includeTags"] = context.input_data.get("include_selectors")
                if context.input_data.get("exclude_selectors"):
                    params["excludeTags"] = context.input_data.get("exclude_selectors")

                response = app.scrape(url, formats=params.get("formats"))
                return self._create_spec_success_result("scrape", response)

            elif action_type == "crawl":
                # Async crawl - returns job ID
                if not url:
                    raise ValueError("Missing required parameter: url")

                params = {}
                if context.input_data.get("limit"):
                    params["limit"] = context.input_data.get("limit")
                if context.input_data.get("max_depth"):
                    params["max_discovery_depth"] = context.input_data.get("max_depth")

                response = app.crawl(url, poll_interval=2, **params)
                return self._create_spec_success_result("crawl", response)

            elif action_type == "map":
                # Map URLs from website
                if not url:
                    raise ValueError("Missing required parameter: url")

                response = app.map(url)
                return self._create_spec_success_result("map", response)

            elif action_type == "search":
                # Search web
                query = context.input_data.get("query")
                if not query:
                    raise ValueError("Missing required parameter: query")

                params = {}
                if context.input_data.get("limit"):
                    params["limit"] = context.input_data.get("limit")

                response = app.search(query, **params)
                return self._create_spec_success_result("search", response)

            elif action_type == "extract":
                # Extract structured data
                if not url:
                    raise ValueError("Missing required parameter: url")

                schema = context.input_data.get("schema", {"type": "object", "properties": {}})

                # Extract expects an array of URLs
                response = app.extract(urls=[url], schema=schema)
                return self._create_spec_success_result("extract", response)

            else:
                raise ValueError(f"Unsupported action type: {action_type}")

        except Exception as e:
            self.log_execution(context, f"Firecrawl API error: {str(e)}", "ERROR")
            return self._create_spec_error_result(
                f"Firecrawl API error: {str(e)}",
                action_type,
                {"reason": "api_error", "api_error": str(e)},
            )

    def _create_spec_error_result(
        self, message: str, operation: str, error_details: Dict[str, Any] = None
    ) -> NodeExecutionResult:
        """
        Create error result following node spec output format.

        Spec output_params:
        - success: false
        - content: ""
        - data: {}
        - urls_processed: []
        - error_message: string
        - stats: {}
        """
        return NodeExecutionResult(
            status=ExecutionStatus.ERROR,
            error_message=message,
            error_details={
                "integration": self.integration_name,
                "operation": operation,
                **(error_details or {}),
            },
            output_data={
                "success": False,
                "content": "",
                "data": {},
                "urls_processed": [],
                "error_message": message,
                "stats": {},
            },
            metadata={
                "node_type": "external_action",
                "integration": self.integration_name,
                "operation": operation,
            },
        )

    def _create_spec_success_result(self, action_type: str, response: Any) -> NodeExecutionResult:
        """
        Create success result following node spec output format.

        Spec output_params:
        - success: true
        - content: string (extracted content)
        - data: object (structured data)
        - urls_processed: array
        - error_message: ""
        - stats: object
        """
        # Extract relevant data based on action type
        content = ""
        data = {}
        urls_processed = []
        stats = {}

        if action_type == "scrape":
            # Official SDK returns: {success, data: {markdown, html, metadata, ...}}
            if isinstance(response, dict) and response.get("success"):
                scrape_data = response.get("data", {})
                content = scrape_data.get("markdown", "") or scrape_data.get("html", "")
                data = scrape_data.get("metadata", {})
                if scrape_data.get("url"):
                    urls_processed = [scrape_data["url"]]

        elif action_type == "crawl":
            # Official SDK returns crawl results with data array
            if isinstance(response, dict):
                if response.get("success") and response.get("data"):
                    crawl_data = response.get("data", [])
                    if isinstance(crawl_data, list):
                        content_parts = []
                        for page in crawl_data:
                            page_content = page.get("markdown", "") or page.get("html", "")
                            if page_content:
                                content_parts.append(page_content)
                            if page.get("url"):
                                urls_processed.append(page["url"])
                        content = "\n\n---\n\n".join(content_parts)
                        stats["pages_processed"] = len(crawl_data)
                else:
                    # Async job started
                    data = {
                        "status": response.get("status", "pending"),
                        "message": "Crawl job processing. Results will be available when complete.",
                    }

        elif action_type == "extract":
            # Official SDK returns extracted data
            if isinstance(response, dict) and response.get("success"):
                extract_data = response.get("data", {})
                data = extract_data
                if response.get("url"):
                    urls_processed = [response["url"]]

        elif action_type == "search":
            # Official SDK returns search results
            if isinstance(response, dict) and response.get("success"):
                search_data = response.get("data", [])
                if isinstance(search_data, list):
                    data = {"results": search_data}
                    urls_processed = [r.get("url") for r in search_data if r.get("url")]
                    stats["results_count"] = len(search_data)

        elif action_type == "map":
            # Official SDK returns discovered URLs
            if isinstance(response, dict) and response.get("success"):
                links = response.get("links", [])
                urls_processed = links
                data = {"discovered_urls": links}
                stats["urls_found"] = len(links)

        # Add execution timestamp
        from datetime import datetime

        stats["timestamp"] = datetime.now().isoformat()
        stats["action_type"] = action_type

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data={
                "success": True,
                "content": content,
                "data": data,
                "urls_processed": urls_processed,
                "error_message": "",
                "stats": stats,
            },
            metadata={
                "node_type": "external_action",
                "integration": self.integration_name,
                "operation": action_type,
                "action_type": action_type,
            },
        )


__all__ = ["FirecrawlExternalAction"]
