"""
Firecrawl MCP API - Tools backed by FirecrawlSDK
"""

import time
from typing import Any, Dict

from app.models import MCPContentItem, MCPInvokeResponse, MCPTool, MCPToolsResponse
from app.utils.logger import get_logger

from shared.sdks import FirecrawlSDK

logger = get_logger(__name__)


class FirecrawlMCPService:
    def __init__(self) -> None:
        self.sdk = FirecrawlSDK()

    def get_available_tools(self) -> MCPToolsResponse:
        tools = [
            MCPTool(
                name="firecrawl_scrape",
                description="Scrape a single webpage with advanced extraction options",
                inputSchema={
                    "type": "object",
                    "required": ["api_key", "url"],
                    "properties": {
                        "api_key": {"type": "string", "description": "Firecrawl API key"},
                        "url": {"type": "string"},
                        "formats": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": [
                                    "markdown",
                                    "html",
                                    "rawHtml",
                                    "screenshot",
                                    "links",
                                    "screenshot@fullPage",
                                    "extract",
                                ],
                            },
                            "default": ["markdown"],
                        },
                        "onlyMainContent": {"type": "boolean"},
                        "includeTags": {"type": "array", "items": {"type": "string"}},
                        "excludeTags": {"type": "array", "items": {"type": "string"}},
                        "waitFor": {"type": "number"},
                        "timeout": {"type": "number"},
                        "actions": {"type": "array", "items": {"type": "object"}},
                        "extract": {"type": "object"},
                        "mobile": {"type": "boolean"},
                        "skipTlsVerification": {"type": "boolean"},
                        "removeBase64Images": {"type": "boolean"},
                        "location": {"type": "object"},
                    },
                },
                category="firecrawl",
                tags=["scrape", "web"],
            ),
            MCPTool(
                name="firecrawl_map",
                description="Discover URLs from a starting point (sitemap and HTML links)",
                inputSchema={
                    "type": "object",
                    "required": ["api_key", "url"],
                    "properties": {
                        "api_key": {"type": "string"},
                        "url": {"type": "string"},
                        "search": {"type": "string"},
                        "ignoreSitemap": {"type": "boolean"},
                        "sitemapOnly": {"type": "boolean"},
                        "includeSubdomains": {"type": "boolean"},
                        "limit": {"type": "number"},
                    },
                },
                category="firecrawl",
                tags=["map", "discover"],
            ),
            MCPTool(
                name="firecrawl_crawl",
                description="Start an asynchronous crawl of multiple pages",
                inputSchema={
                    "type": "object",
                    "required": ["api_key", "url"],
                    "properties": {
                        "api_key": {"type": "string"},
                        "url": {"type": "string"},
                        "excludePaths": {"type": "array", "items": {"type": "string"}},
                        "includePaths": {"type": "array", "items": {"type": "string"}},
                        "maxDepth": {"type": "number"},
                        "ignoreSitemap": {"type": "boolean"},
                        "limit": {"type": "number"},
                        "allowBackwardLinks": {"type": "boolean"},
                        "allowExternalLinks": {"type": "boolean"},
                        "webhook": {"oneOf": [{"type": "string"}, {"type": "object"}]},
                        "deduplicateSimilarURLs": {"type": "boolean"},
                        "ignoreQueryParameters": {"type": "boolean"},
                        "scrapeOptions": {"type": "object"},
                    },
                },
                category="firecrawl",
                tags=["crawl"],
            ),
            MCPTool(
                name="firecrawl_check_crawl_status",
                description="Check the status of a crawl job",
                inputSchema={
                    "type": "object",
                    "required": ["api_key", "id"],
                    "properties": {
                        "api_key": {"type": "string"},
                        "id": {"type": "string"},
                    },
                },
                category="firecrawl",
                tags=["crawl", "status"],
            ),
            MCPTool(
                name="firecrawl_batch_scrape",
                description="Batch scrape multiple URLs",
                inputSchema={
                    "type": "object",
                    "required": ["api_key", "urls"],
                    "properties": {
                        "api_key": {"type": "string"},
                        "urls": {"type": "array", "items": {"type": "string"}},
                        "options": {"type": "object"},
                    },
                },
                category="firecrawl",
                tags=["scrape", "batch"],
            ),
            MCPTool(
                name="firecrawl_check_batch_status",
                description="Check status of a batch scraping job",
                inputSchema={
                    "type": "object",
                    "required": ["api_key", "id"],
                    "properties": {
                        "api_key": {"type": "string"},
                        "id": {"type": "string"},
                    },
                },
                category="firecrawl",
                tags=["scrape", "status"],
            ),
            MCPTool(
                name="firecrawl_search",
                description="Search and optionally scrape results",
                inputSchema={
                    "type": "object",
                    "required": ["api_key", "query"],
                    "properties": {
                        "api_key": {"type": "string"},
                        "query": {"type": "string"},
                        "limit": {"type": "number"},
                        "lang": {"type": "string"},
                        "country": {"type": "string"},
                        "tbs": {"type": "string"},
                        "filter": {"type": "string"},
                        "location": {"type": "object"},
                        "scrapeOptions": {"type": "object"},
                    },
                },
                category="firecrawl",
                tags=["search", "web"],
            ),
            MCPTool(
                name="firecrawl_extract",
                description="Extract structured information from web pages using an LLM",
                inputSchema={
                    "type": "object",
                    "required": ["api_key", "urls"],
                    "properties": {
                        "api_key": {"type": "string"},
                        "urls": {"type": "array", "items": {"type": "string"}},
                        "prompt": {"type": "string"},
                        "systemPrompt": {"type": "string"},
                        "schema": {"type": "object"},
                        "allowExternalLinks": {"type": "boolean"},
                        "enableWebSearch": {"type": "boolean"},
                        "includeSubdomains": {"type": "boolean"},
                    },
                },
                category="firecrawl",
                tags=["extract", "ai"],
            ),
            MCPTool(
                name="firecrawl_generate_llmstxt",
                description="Generate LLMs.txt for a URL",
                inputSchema={
                    "type": "object",
                    "required": ["api_key", "url"],
                    "properties": {
                        "api_key": {"type": "string"},
                        "url": {"type": "string"},
                        "maxUrls": {"type": "number"},
                        "showFullText": {"type": "boolean"},
                    },
                },
                category="firecrawl",
                tags=["llmstxt", "ai"],
            ),
        ]

        return MCPToolsResponse(
            tools=tools,
            total_count=len(tools),
            available_count=len(tools),
            categories=["firecrawl"],
        )

    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        info = {
            t.name: {
                "name": t.name,
                "description": t.description,
                "category": "firecrawl",
                "available": True,
            }
            for t in self.get_available_tools().tools
        }
        return info.get(
            tool_name,
            {
                "name": tool_name,
                "available": False,
                "description": "Tool not found",
                "category": "firecrawl",
            },
        )

    def health_check(self):
        import time

        from app.models import MCPHealthCheck

        return MCPHealthCheck(
            healthy=True,
            version="1.0.0",
            available_tools=[t.name for t in self.get_available_tools().tools],
            timestamp=int(time.time()),
        )

    async def invoke_tool(self, tool_name: str, params: Dict[str, Any]) -> MCPInvokeResponse:
        start_time = time.time()
        try:
            credentials = {"api_key": params.get("api_key")}
            op_params = {k: v for k, v in params.items() if k != "api_key"}

            api_resp = await self.sdk.call_operation(tool_name, op_params, credentials)
            if not api_resp.success:
                resp = MCPInvokeResponse(
                    content=[
                        MCPContentItem(
                            type="text", text=str(api_resp.error or "Firecrawl operation failed")
                        )
                    ],
                    isError=True,
                )
            else:
                resp = MCPInvokeResponse(
                    content=[
                        MCPContentItem(type="text", text=f"{tool_name} executed successfully")
                    ],
                    isError=False,
                    structuredContent=api_resp.data,
                )
            resp._tool_name = tool_name
            resp._execution_time_ms = round((time.time() - start_time) * 1000, 2)
            return resp
        except Exception as e:
            resp = MCPInvokeResponse(
                content=[
                    MCPContentItem(type="text", text=f"Firecrawl tool execution failed: {str(e)}")
                ],
                isError=True,
            )
            resp._tool_name = tool_name
            resp._execution_time_ms = round((time.time() - start_time) * 1000, 2)
            return resp


firecrawl_mcp_service = FirecrawlMCPService()
