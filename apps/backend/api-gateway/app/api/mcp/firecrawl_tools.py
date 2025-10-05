"""
Firecrawl MCP API - Tools backed by FirecrawlSDK
"""

import time
from typing import Any, Dict

from app.models import MCPContentItem, MCPInvokeResponse, MCPTool, MCPToolsResponse
from app.utils.logger import get_logger

try:
    from firecrawl import FirecrawlApp
except ImportError:
    FirecrawlApp = None

logger = get_logger(__name__)


class FirecrawlMCPService:
    def __init__(self) -> None:
        # Use official Firecrawl SDK
        if FirecrawlApp is None:
            logger.warning("⚠️ FirecrawlApp not available - install firecrawl-py package")
            self.sdk = None
        else:
            self.sdk = None  # Will be initialized per-request with API key

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

        # Check if SDK is available
        if FirecrawlApp is None:
            resp = MCPInvokeResponse(
                content=[
                    MCPContentItem(
                        type="text",
                        text="Firecrawl SDK not available. Install with: pip install firecrawl-py",
                    )
                ],
                isError=True,
            )
            resp._tool_name = tool_name
            resp._execution_time_ms = round((time.time() - start_time) * 1000, 2)
            return resp

        try:
            # Extract API key and initialize Firecrawl client
            api_key = params.get("api_key")
            if not api_key:
                raise ValueError("api_key is required for Firecrawl operations")

            # Initialize Firecrawl app with API key
            app = FirecrawlApp(api_key=api_key)

            # Extract operation parameters (exclude api_key)
            op_params = {k: v for k, v in params.items() if k != "api_key"}

            # Execute the appropriate Firecrawl operation
            result = None
            if tool_name == "firecrawl_scrape":
                result = app.scrape_url(
                    url=op_params.get("url"), params=op_params.get("params", {})
                )
            elif tool_name == "firecrawl_crawl":
                result = app.crawl_url(
                    url=op_params.get("url"),
                    params=op_params.get("params", {}),
                    poll_interval=op_params.get("poll_interval", 2),
                )
            elif tool_name == "firecrawl_crawl_async":
                result = app.async_crawl_url(
                    url=op_params.get("url"), params=op_params.get("params", {})
                )
            elif tool_name == "firecrawl_check_crawl_status":
                result = app.check_crawl_status(id=op_params.get("id"))
            elif tool_name == "firecrawl_search":
                result = app.search(
                    query=op_params.get("query"),
                    params={k: v for k, v in op_params.items() if k != "query"},
                )
            elif tool_name == "firecrawl_extract":
                result = app.extract(
                    urls=op_params.get("urls"),
                    params={k: v for k, v in op_params.items() if k != "urls"},
                )
            elif tool_name == "firecrawl_llmstxt":
                result = app.crawl_url(
                    url=op_params.get("url"),
                    params={"formats": ["markdown"], **(op_params.get("params", {}))},
                )
            else:
                raise ValueError(f"Unknown Firecrawl tool: {tool_name}")

            # Build success response
            resp = MCPInvokeResponse(
                content=[MCPContentItem(type="text", text=f"{tool_name} executed successfully")],
                isError=False,
                structuredContent=result,
            )
            resp._tool_name = tool_name
            resp._execution_time_ms = round((time.time() - start_time) * 1000, 2)
            return resp

        except Exception as e:
            logger.error(f"❌ Firecrawl tool execution failed: {str(e)}")
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
