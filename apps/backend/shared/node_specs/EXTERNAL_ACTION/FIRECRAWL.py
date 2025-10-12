"""
FIRECRAWL External Action Node Specification

Firecrawl action node for web scraping and data extraction operations including
URL crawling, content extraction, structured data parsing, and website monitoring.
"""

from typing import Any, Dict, List

from ...models.node_enums import ExternalActionSubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec


class FirecrawlActionSpec(BaseNodeSpec):
    """Firecrawl action specification for web scraping and data extraction."""

    def __init__(self):
        super().__init__(
            type=NodeType.EXTERNAL_ACTION,
            subtype=ExternalActionSubtype.FIRECRAWL,
            name="Firecrawl_Action",
            description="Perform web scraping and data extraction using Firecrawl API for content crawling and structured data parsing",
            # Configuration parameters (simplified)
            configurations={
                "firecrawl_api_key": {
                    "type": "string",
                    "default": "",
                    "description": "Firecrawl API密钥",
                    "required": True,
                    "sensitive": True,
                },
                "action_type": {
                    "type": "string",
                    "default": "scrape",
                    "description": "Firecrawl操作类型",
                    "required": True,
                    "options": ["scrape", "crawl", "extract", "screenshot"],
                },
                **COMMON_CONFIGS,
            },
            # Parameter schemas (simplified)
            input_params={
                "action_type": {
                    "type": "string",
                    "default": "",
                    "description": "Dynamic action type (overrides configuration action_type)",
                    "required": False,
                    "options": ["scrape", "crawl", "extract", "screenshot"],
                },
                "url": {
                    "type": "string",
                    "default": "",
                    "description": "目标URL（scrape/extract/screenshot）",
                    "required": False,
                },
                "urls": {
                    "type": "array",
                    "default": [],
                    "description": "批量URL（crawl）",
                    "required": False,
                },
                "include_selectors": {
                    "type": "array",
                    "default": [],
                    "description": "包含的CSS选择器（可选）",
                    "required": False,
                },
                "exclude_selectors": {
                    "type": "array",
                    "default": ["script", "style"],
                    "description": "排除的CSS选择器（可选）",
                    "required": False,
                },
                "format": {
                    "type": "string",
                    "default": "markdown",
                    "description": "输出格式",
                    "required": False,
                    "options": ["markdown", "html", "text", "json"],
                },
                "max_depth": {
                    "type": "integer",
                    "default": 2,
                    "description": "爬取深度（crawl）",
                    "required": False,
                },
                "limit": {
                    "type": "integer",
                    "default": 50,
                    "description": "最大页面数（crawl）",
                    "required": False,
                },
                "schema": {
                    "type": "object",
                    "default": {},
                    "description": "结构化提取Schema（extract）",
                    "required": False,
                },
                "headers": {
                    "type": "object",
                    "default": {},
                    "description": "自定义HTTP头（可选）",
                    "required": False,
                },
                "screenshot": {
                    "type": "object",
                    "default": {"fullPage": True, "quality": 80, "format": "png"},
                    "description": "截图参数（screenshot）",
                    "required": False,
                },
            },
            output_params={
                "success": {
                    "type": "boolean",
                    "default": False,
                    "description": "操作是否成功",
                    "required": False,
                },
                "content": {
                    "type": "string",
                    "default": "",
                    "description": "提取到的内容（markdown/html/text）",
                    "required": False,
                },
                "data": {
                    "type": "object",
                    "default": {},
                    "description": "结构化数据（extract）",
                    "required": False,
                },
                "urls_processed": {
                    "type": "array",
                    "default": [],
                    "description": "处理的URL列表",
                    "required": False,
                },
                "error_message": {
                    "type": "string",
                    "default": "",
                    "description": "错误信息（失败时）",
                    "required": False,
                },
                "stats": {
                    "type": "object",
                    "default": {},
                    "description": "执行统计（耗时、页面数等）",
                    "required": False,
                },
            },  # Examples
            examples=[
                {
                    "name": "Single Page Content Extraction",
                    "description": "Extract structured content from a single webpage with custom formatting",
                    "configurations": {
                        "api_key": "fc-your_api_key_here",
                        "action_type": "firecrawl_scrape",
                        "url": "{{target_url}}",
                        "scrape_config": {
                            "formats": ["markdown", "html"],
                            "includeTags": ["article", "main", "content"],
                            "excludeTags": ["script", "style", "nav", "footer", "ads"],
                            "onlyMainContent": True,
                            "waitFor": 2000,
                            "timeout": 30000,
                            "headers": {
                                "User-Agent": "Mozilla/5.0 (compatible; DataExtractor/1.0)"
                            },
                        },
                        "output_format": "markdown",
                        "filter_config": {
                            "minLength": 100,
                            "contentFilter": "{{content_keywords}}",
                            "duplicateFilter": True,
                        },
                    },
                    "input_example": {
                        "data": {
                            "target_url": "https://example-news.com/article/tech-trends-2025",
                            "content_keywords": "technology, artificial intelligence, trends",
                        }
                    },
                    "expected_outputs": {
                        "result": {
                            "success": True,
                            "firecrawl_response": {
                                "success": True,
                                "data": {
                                    "markdown": "# Tech Trends 2025\n\nArtificial intelligence continues to reshape industries...",
                                    "html": "<article><h1>Tech Trends 2025</h1><p>Artificial intelligence continues...</p></article>",
                                    "metadata": {
                                        "title": "Tech Trends 2025: What to Expect",
                                        "description": "Analysis of upcoming technology trends",
                                        "language": "en",
                                        "publishedTime": "2025-01-20T10:00:00Z",
                                    },
                                },
                            },
                            "content": "# Tech Trends 2025\n\nArtificial intelligence continues to reshape industries...",
                            "extracted_data": {
                                "title": "Tech Trends 2025: What to Expect",
                                "author": "Tech Analyst",
                                "word_count": 1250,
                                "reading_time": "5 minutes",
                                "keywords": ["AI", "technology", "trends", "2025"],
                            },
                            "metadata": {
                                "url": "https://example-news.com/article/tech-trends-2025",
                                "status_code": 200,
                                "content_length": 5280,
                                "content_type": "text/html",
                                "last_modified": "2025-01-20T10:00:00Z",
                            },
                            "urls_processed": ["https://example-news.com/article/tech-trends-2025"],
                            "execution_stats": {
                                "action_type": "firecrawl_scrape",
                                "processing_time_ms": 3200,
                                "pages_processed": 1,
                                "content_extracted": True,
                            },
                        }
                    },
                },
                {
                    "name": "Website Crawling with Structured Data Extraction",
                    "description": "Crawl e-commerce website to extract product information with custom schema",
                    "configurations": {
                        "api_key": "fc-your_api_key_here",
                        "action_type": "firecrawl_crawl",
                        "url": "{{base_url}}",
                        "crawl_config": {
                            "maxDepth": 3,
                            "limit": 50,
                            "allowBacklinks": False,
                            "allowExternalLinks": False,
                            "includes": ["*/products/*", "*/categories/*"],
                            "excludes": ["*/cart", "*/checkout", "*/account"],
                            "maxConcurrency": 3,
                            "delay": 2000,
                        },
                        "extraction_config": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "product_name": {"type": "string"},
                                    "price": {"type": "string"},
                                    "description": {"type": "string"},
                                    "availability": {"type": "string"},
                                    "rating": {"type": "number"},
                                    "reviews_count": {"type": "integer"},
                                    "image_urls": {"type": "array", "items": {"type": "string"}},
                                    "category": {"type": "string"},
                                },
                            },
                            "systemPrompt": "Extract product information from e-commerce pages",
                            "extractorType": "llm",
                            "mode": "llm-extraction",
                        },
                        "rate_limit_config": {"requestsPerMinute": 30, "respectRobotsTxt": True},
                    },
                    "input_example": {
                        "data": {
                            "base_url": "https://example-store.com",
                            "category_filter": "electronics",
                            "max_products": 50,
                        }
                    },
                    "expected_outputs": {
                        "result": {
                            "success": True,
                            "firecrawl_response": {
                                "success": True,
                                "data": [
                                    {
                                        "url": "https://example-store.com/products/laptop-pro",
                                        "content": "# MacBook Pro 16-inch\n\nPowerful laptop for professionals...",
                                        "metadata": {
                                            "title": "MacBook Pro 16-inch - Premium Laptop",
                                            "statusCode": 200,
                                        },
                                        "extractedData": {
                                            "product_name": "MacBook Pro 16-inch",
                                            "price": "$2,499.00",
                                            "description": "Powerful laptop for professionals with M3 chip",
                                            "availability": "In Stock",
                                            "rating": 4.8,
                                            "reviews_count": 234,
                                            "category": "Laptops",
                                        },
                                    }
                                ],
                            },
                            "extracted_data": {
                                "products": [
                                    {
                                        "product_name": "MacBook Pro 16-inch",
                                        "price": "$2,499.00",
                                        "description": "Powerful laptop for professionals with M3 chip",
                                        "availability": "In Stock",
                                        "rating": 4.8,
                                        "reviews_count": 234,
                                        "category": "Laptops",
                                    }
                                ],
                                "total_products": 1,
                                "categories_found": ["Laptops", "Tablets", "Accessories"],
                            },
                            "urls_processed": [
                                "https://example-store.com/products/laptop-pro",
                                "https://example-store.com/categories/electronics",
                            ],
                            "execution_stats": {
                                "action_type": "firecrawl_crawl",
                                "processing_time_ms": 45000,
                                "pages_processed": 2,
                                "products_extracted": 1,
                                "max_depth_reached": 2,
                            },
                        }
                    },
                },
            ],
        )


# Export the specification instance
FIRECRAWL_EXTERNAL_ACTION_SPEC = FirecrawlActionSpec()
