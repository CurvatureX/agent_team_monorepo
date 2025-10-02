"""
FIRECRAWL_MCP_TOOL Tool Node Specification

MCP tool for Firecrawl web scraping capabilities.
This tool is attached to AI_AGENT nodes and provides web scraping,
crawling, and content extraction through the MCP protocol.

Note: TOOL nodes are attached to AI_AGENT nodes via attached_nodes,
not connected through input/output ports.
"""

from typing import Any, Dict, List

from ...models.node_enums import NodeType, ToolSubtype
from ..base import COMMON_CONFIGS, BaseNodeSpec


class FirecrawlMCPToolSpec(BaseNodeSpec):
    """Firecrawl MCP Tool specification for AI_AGENT attached functionality."""

    def __init__(self):
        super().__init__(
            type=NodeType.TOOL,
            subtype=ToolSubtype.FIRECRAWL_MCP_TOOL,
            name="Firecrawl_MCP_Tool",
            description="Firecrawl MCP tool for web scraping and content extraction through MCP protocol",
            # Configuration parameters
            configurations={
                "mcp_server_url": {
                    "type": "string",
                    "default": "http://localhost:8000/api/v1/mcp",
                    "description": "MCP服务器URL",
                    "required": True,
                },
                "firecrawl_api_key": {
                    "type": "string",
                    "default": "",
                    "description": "Firecrawl API密钥",
                    "required": True,
                    "sensitive": True,
                },
                "available_tools": {
                    "type": "array",
                    "default": ["firecrawl_scrape", "firecrawl_map", "firecrawl_crawl"],
                    "description": "可用的Firecrawl工具列表",
                    "required": False,
                    "options": [
                        "firecrawl_scrape",
                        "firecrawl_map",
                        "firecrawl_crawl",
                        "firecrawl_batch_scrape",
                        "firecrawl_search",
                    ],
                },
                "default_formats": {
                    "type": "array",
                    "default": ["markdown", "html"],
                    "description": "默认输出格式",
                    "required": False,
                    "options": ["markdown", "html", "rawHtml", "screenshot", "links", "extract"],
                },
                "timeout_seconds": {
                    "type": "integer",
                    "default": 30,
                    "min": 5,
                    "max": 300,
                    "description": "请求超时时间（秒）",
                    "required": False,
                },
                "max_crawl_pages": {
                    "type": "integer",
                    "default": 100,
                    "min": 1,
                    "max": 10000,
                    "description": "最大爬取页面数",
                    "required": False,
                },
                "wait_for_selector": {
                    "type": "string",
                    "default": "",
                    "description": "等待特定选择器加载",
                    "required": False,
                },
                "extract_main_content": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否只提取主要内容",
                    "required": False,
                },
                "remove_base64_images": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否移除Base64图片",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Schema-style runtime parameters for tool execution
            input_params={
                "tool_name": {
                    "type": "string",
                    "default": "",
                    "description": "MCP tool function name to invoke",
                    "required": True,
                },
                "function_args": {
                    "type": "object",
                    "default": {},
                    "description": "Arguments for the selected tool function",
                    "required": False,
                },
                "context": {
                    "type": "object",
                    "default": {},
                    "description": "Optional context to pass along with the tool call",
                    "required": False,
                },
                "call_id": {
                    "type": "string",
                    "default": "",
                    "description": "Optional correlation ID for tracing",
                    "required": False,
                },
            },
            output_params={
                "result": {
                    "type": "object",
                    "default": {},
                    "description": "Result payload returned by the MCP tool",
                    "required": False,
                },
                "success": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether the MCP tool invocation succeeded",
                    "required": False,
                },
                "error_message": {
                    "type": "string",
                    "default": "",
                    "description": "Error details if invocation failed",
                    "required": False,
                },
                "execution_time": {
                    "type": "number",
                    "default": 0.0,
                    "description": "Execution time in seconds",
                    "required": False,
                },
                "cached": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether the result was served from cache",
                    "required": False,
                },
                "scraped_url": {
                    "type": "string",
                    "default": "",
                    "description": "Requested URL for scrape/crawl/map operation",
                    "required": False,
                },
                "content_type": {
                    "type": "string",
                    "default": "",
                    "description": "High-level content type for the operation result",
                    "required": False,
                },
                "pages_processed": {
                    "type": "integer",
                    "default": 0,
                    "description": "Number of pages processed (if applicable)",
                    "required": False,
                },
            },
            # TOOL nodes have no ports - they are attached to AI_AGENT nodes            # Tools don't have attached_nodes (only AI_AGENT has this)
            attached_nodes=None,
            # Metadata
            tags=["tool", "mcp", "firecrawl", "scraping", "web", "content", "attached"],
            # Examples
            examples=[
                {
                    "name": "Scrape Single Webpage",
                    "description": "Extract content from a single webpage with multiple formats",
                    "configurations": {
                        "mcp_server_url": "http://localhost:8000/api/v1/mcp",
                        "firecrawl_api_key": "fc_api_key_123",
                        "available_tools": ["firecrawl_scrape"],
                        "default_formats": ["markdown", "html"],
                        "timeout_seconds": 30,
                        "extract_main_content": True,
                    },
                    "usage_example": {
                        "attached_to": "content_extraction_ai",
                        "function_call": {
                            "tool_name": "firecrawl_scrape",
                            "function_args": {
                                "api_key": "fc_api_key_123",
                                "url": "https://example.com/blog/ai-trends-2025",
                                "formats": ["markdown", "html", "links"],
                                "onlyMainContent": True,
                                "includeTags": ["p", "h1", "h2", "h3", "article"],
                                "excludeTags": ["nav", "footer", "sidebar"],
                                "waitFor": 2000,
                                "timeout": 30000,
                                "removeBase64Images": True,
                            },
                            "context": {
                                "purpose": "content_analysis",
                                "target_content": "blog_article",
                            },
                        },
                        "expected_result": {
                            "result": {
                                "success": True,
                                "data": {
                                    "markdown": "# AI Trends 2025\n\nThe landscape of artificial intelligence continues to evolve...",
                                    "html": "<html><body><h1>AI Trends 2025</h1><p>The landscape...</p></body></html>",
                                    "links": [
                                        "https://example.com/related-article-1",
                                        "https://example.com/related-article-2",
                                    ],
                                },
                                "metadata": {
                                    "title": "AI Trends 2025 - Future Predictions",
                                    "description": "Exploring the latest trends in AI for 2025",
                                    "ogTitle": "AI Trends 2025",
                                    "ogDescription": "Future predictions and trends",
                                    "ogImage": "https://example.com/og-image.jpg",
                                    "ogUrl": "https://example.com/blog/ai-trends-2025",
                                },
                            },
                            "success": True,
                            "execution_time": 4.5,
                            "scraped_url": "https://example.com/blog/ai-trends-2025",
                            "content_type": "article",
                            "pages_processed": 1,
                        },
                    },
                },
                {
                    "name": "Map Website URLs",
                    "description": "Discover and map URLs from a website's sitemap and links",
                    "configurations": {
                        "mcp_server_url": "http://localhost:8000/api/v1/mcp",
                        "firecrawl_api_key": "fc_api_key_456",
                        "available_tools": ["firecrawl_map"],
                        "max_crawl_pages": 50,
                    },
                    "usage_example": {
                        "attached_to": "site_analysis_ai",
                        "function_call": {
                            "tool_name": "firecrawl_map",
                            "function_args": {
                                "api_key": "fc_api_key_456",
                                "url": "https://docs.example.com",
                                "search": "API documentation",
                                "ignoreSitemap": False,
                                "sitemapOnly": False,
                                "includeSubdomains": False,
                                "limit": 50,
                            },
                            "context": {"analysis_type": "documentation_mapping"},
                        },
                        "expected_result": {
                            "result": {
                                "success": True,
                                "links": [
                                    "https://docs.example.com/api/authentication",
                                    "https://docs.example.com/api/endpoints",
                                    "https://docs.example.com/api/webhooks",
                                    "https://docs.example.com/guides/getting-started",
                                    "https://docs.example.com/guides/advanced-usage",
                                ],
                                "total_links": 25,
                                "sitemap_found": True,
                                "robots_txt_found": True,
                            },
                            "success": True,
                            "execution_time": 2.1,
                            "scraped_url": "https://docs.example.com",
                            "content_type": "sitemap",
                        },
                    },
                },
                {
                    "name": "Crawl Multiple Pages",
                    "description": "Asynchronously crawl multiple pages with filtering and limits",
                    "configurations": {
                        "mcp_server_url": "http://localhost:8000/api/v1/mcp",
                        "firecrawl_api_key": "fc_api_key_789",
                        "available_tools": ["firecrawl_crawl"],
                        "max_crawl_pages": 20,
                        "timeout_seconds": 120,
                    },
                    "usage_example": {
                        "attached_to": "comprehensive_scraper_ai",
                        "function_call": {
                            "tool_name": "firecrawl_crawl",
                            "function_args": {
                                "api_key": "fc_api_key_789",
                                "url": "https://blog.example.com",
                                "includePaths": ["/posts/*", "/articles/*"],
                                "excludePaths": ["/admin/*", "/private/*"],
                                "maxDepth": 3,
                                "limit": 20,
                                "allowBackwardLinks": False,
                                "allowExternalLinks": False,
                                "formats": ["markdown"],
                                "onlyMainContent": True,
                                "deduplicateSimilarURLs": True,
                                "webhook": {
                                    "url": "https://webhook.example.com/firecrawl",
                                    "headers": {"Authorization": "Bearer webhook_token"},
                                },
                            },
                            "context": {
                                "crawl_purpose": "content_indexing",
                                "content_type": "blog_posts",
                            },
                        },
                        "expected_result": {
                            "result": {
                                "success": True,
                                "jobId": "crawl_job_abc123",
                                "status": "queued",
                                "total": 20,
                                "creditsUsed": 20,
                                "expiresAt": "2025-01-20T18:30:00Z",
                                "next": "https://api.firecrawl.dev/v0/crawl/job/crawl_job_abc123",
                            },
                            "success": True,
                            "execution_time": 1.8,
                            "scraped_url": "https://blog.example.com",
                            "content_type": "crawl_job",
                            "pages_processed": 0,
                        },
                    },
                },
            ],
        )


# Export the specification instance
FIRECRAWL_MCP_TOOL_SPEC = FirecrawlMCPToolSpec()
