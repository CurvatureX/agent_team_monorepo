"""
FIRECRAWL External Action Node Specification

Firecrawl action node for web scraping and data extraction operations including
URL crawling, content extraction, structured data parsing, and website monitoring.
"""

from typing import Any, Dict, List

from ...models.node_enums import ExternalActionSubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec, create_port


class FirecrawlActionSpec(BaseNodeSpec):
    """Firecrawl action specification for web scraping and data extraction."""

    def __init__(self):
        super().__init__(
            type=NodeType.EXTERNAL_ACTION,
            subtype=ExternalActionSubtype.FIRECRAWL,
            name="Firecrawl_Action",
            description="Perform web scraping and data extraction using Firecrawl API for content crawling and structured data parsing",
            # Configuration parameters
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
                    "options": [
                        "scrape",  # Single page scraping
                        "crawl",  # Multi-page crawling
                        "search",  # Web search with scraping
                        "extract",  # Structured data extraction
                        "monitor",  # Website change monitoring
                        "screenshot",  # Take webpage screenshot
                        "pdf_extract",  # Extract text from PDF
                        "batch_scrape",  # Batch process multiple URLs
                        "sitemap_crawl",  # Crawl based on sitemap
                        "link_discovery",  # Discover and extract links
                    ],
                },
                "url": {"type": "string", "default": "", "description": "目标URL", "required": False},
                "urls": {
                    "type": "array",
                    "default": [],
                    "description": "批量URL列表",
                    "required": False,
                },
                "scrape_config": {
                    "type": "object",
                    "default": {
                        "formats": ["markdown", "html"],
                        "includeTags": [],
                        "excludeTags": ["script", "style"],
                        "onlyMainContent": True,
                        "waitFor": 0,
                        "timeout": 30000,
                        "headers": {},
                    },
                    "description": "抓取配置",
                    "required": False,
                },
                "crawl_config": {
                    "type": "object",
                    "default": {
                        "maxDepth": 2,
                        "limit": 100,
                        "allowBacklinks": False,
                        "allowExternalLinks": False,
                        "includes": [],
                        "excludes": [],
                        "maxConcurrency": 5,
                        "delay": 1000,
                    },
                    "description": "爬虫配置",
                    "required": False,
                },
                "extraction_config": {
                    "type": "object",
                    "default": {
                        "schema": {},
                        "systemPrompt": "",
                        "userPrompt": "",
                        "extractorType": "llm",
                        "mode": "llm-extraction",
                    },
                    "description": "数据提取配置",
                    "required": False,
                },
                "search_config": {
                    "type": "object",
                    "default": {
                        "query": "",
                        "searchEngine": "google",
                        "country": "us",
                        "language": "en",
                        "location": "",
                        "numResults": 10,
                        "freshness": "anytime",
                    },
                    "description": "搜索配置",
                    "required": False,
                },
                "monitor_config": {
                    "type": "object",
                    "default": {
                        "webhookUrl": "",
                        "monitorType": "change",
                        "checkInterval": 3600,
                        "threshold": 0.1,
                        "includeSnapshot": False,
                    },
                    "description": "监控配置",
                    "required": False,
                },
                "screenshot_config": {
                    "type": "object",
                    "default": {
                        "fullPage": True,
                        "mobile": False,
                        "darkMode": False,
                        "quality": 80,
                        "format": "png",
                        "waitTime": 3000,
                    },
                    "description": "截图配置",
                    "required": False,
                },
                "output_format": {
                    "type": "string",
                    "default": "markdown",
                    "description": "输出格式",
                    "required": False,
                    "options": ["markdown", "html", "text", "json", "structured"],
                },
                "filter_config": {
                    "type": "object",
                    "default": {
                        "minLength": 0,
                        "maxLength": -1,
                        "contentFilter": "",
                        "languageFilter": "",
                        "duplicateFilter": True,
                    },
                    "description": "内容过滤配置",
                    "required": False,
                },
                "rate_limit_config": {
                    "type": "object",
                    "default": {
                        "requestsPerMinute": 60,
                        "burstLimit": 10,
                        "respectRobotsTxt": True,
                        "userAgent": "FirecrawlBot/1.0",
                    },
                    "description": "速率限制配置",
                    "required": False,
                },
                "retry_config": {
                    "type": "object",
                    "default": {
                        "maxRetries": 3,
                        "retryDelay": 2000,
                        "exponentialBackoff": True,
                        "retryOn": ["timeout", "5xx", "network_error"],
                    },
                    "description": "重试配置",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Default runtime parameters
            default_input_params={"data": {}, "context": {}, "variables": {}},
            default_output_params={
                "success": False,
                "firecrawl_response": {},
                "content": "",
                "extracted_data": {},
                "metadata": {},
                "urls_processed": [],
                "error_message": "",
                "execution_stats": {},
            },
            # Port definitions
            input_ports=[
                create_port(
                    port_id="main",
                    name="main",
                    data_type="dict",
                    description="Input data for Firecrawl action",
                    required=True,
                    max_connections=1,
                )
            ],
            output_ports=[
                create_port(
                    port_id="success",
                    name="success",
                    data_type="dict",
                    description="Output when Firecrawl action succeeds",
                    required=True,
                    max_connections=-1,
                ),
                create_port(
                    port_id="error",
                    name="error",
                    data_type="dict",
                    description="Output when Firecrawl action fails",
                    required=False,
                    max_connections=-1,
                ),
            ],
            # Metadata
            tags=[
                "external-action",
                "firecrawl",
                "web-scraping",
                "data-extraction",
                "crawling",
                "monitoring",
            ],
            # Examples
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
                        "success": {
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
                        "success": {
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
                {
                    "name": "Web Search with Content Extraction",
                    "description": "Perform web search and extract content from top results",
                    "configurations": {
                        "api_key": "fc-your_api_key_here",
                        "action_type": "firecrawl_search",
                        "search_config": {
                            "query": "{{search_query}}",
                            "searchEngine": "google",
                            "country": "{{country_code}}",
                            "language": "{{language_code}}",
                            "numResults": 10,
                            "freshness": "{{time_filter}}",
                        },
                        "scrape_config": {
                            "formats": ["markdown"],
                            "onlyMainContent": True,
                            "waitFor": 1000,
                            "timeout": 20000,
                        },
                        "extraction_config": {
                            "systemPrompt": "Extract key information including main points, statistics, and conclusions",
                            "extractorType": "llm",
                        },
                        "filter_config": {"minLength": 200, "duplicateFilter": True},
                    },
                    "input_example": {
                        "data": {
                            "search_query": "climate change impact 2025 report",
                            "country_code": "us",
                            "language_code": "en",
                            "time_filter": "month",
                            "max_results": 5,
                        }
                    },
                    "expected_outputs": {
                        "success": {
                            "success": True,
                            "firecrawl_response": {
                                "success": True,
                                "data": [
                                    {
                                        "url": "https://climate-research.org/report-2025",
                                        "title": "Climate Impact Report 2025",
                                        "content": "# Climate Impact Report 2025\n\nKey findings show accelerating trends...",
                                        "metadata": {
                                            "description": "Comprehensive analysis of climate change impacts",
                                            "publishedTime": "2025-01-15T00:00:00Z",
                                        },
                                        "extractedData": {
                                            "key_findings": [
                                                "Global temperature increase of 1.2°C since pre-industrial times",
                                                "Sea level rise of 23cm in past century",
                                            ],
                                            "statistics": {
                                                "temperature_change": "1.2°C",
                                                "sea_level_rise": "23cm",
                                            },
                                        },
                                    }
                                ],
                            },
                            "extracted_data": {
                                "search_results": [
                                    {
                                        "title": "Climate Impact Report 2025",
                                        "url": "https://climate-research.org/report-2025",
                                        "key_findings": [
                                            "Global temperature increase of 1.2°C since pre-industrial times",
                                            "Sea level rise of 23cm in past century",
                                        ],
                                    }
                                ],
                                "total_results": 1,
                                "search_query": "climate change impact 2025 report",
                            },
                            "urls_processed": ["https://climate-research.org/report-2025"],
                            "execution_stats": {
                                "action_type": "firecrawl_search",
                                "processing_time_ms": 12000,
                                "search_results_found": 10,
                                "pages_scraped": 1,
                                "content_extracted": True,
                            },
                        }
                    },
                },
                {
                    "name": "Batch URL Processing",
                    "description": "Process multiple URLs in batch with parallel extraction",
                    "configurations": {
                        "api_key": "fc-your_api_key_here",
                        "action_type": "firecrawl_batch_scrape",
                        "urls": "{{url_list}}",
                        "scrape_config": {
                            "formats": ["markdown"],
                            "onlyMainContent": True,
                            "timeout": 25000,
                        },
                        "extraction_config": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "summary": {"type": "string"},
                                    "publish_date": {"type": "string"},
                                    "author": {"type": "string"},
                                    "tags": {"type": "array", "items": {"type": "string"}},
                                },
                            }
                        },
                        "rate_limit_config": {"requestsPerMinute": 20, "burstLimit": 5},
                        "retry_config": {"maxRetries": 2, "retryDelay": 3000},
                    },
                    "input_example": {
                        "data": {
                            "url_list": [
                                "https://blog1.example.com/article-1",
                                "https://blog2.example.com/article-2",
                                "https://news.example.com/breaking-news",
                                "https://research.example.com/study-results",
                            ],
                            "batch_id": "batch_001",
                            "processing_priority": "high",
                        }
                    },
                    "expected_outputs": {
                        "success": {
                            "success": True,
                            "firecrawl_response": {
                                "success": True,
                                "results": [
                                    {
                                        "url": "https://blog1.example.com/article-1",
                                        "status": "success",
                                        "extractedData": {
                                            "title": "Innovation in AI Development",
                                            "summary": "Latest trends in artificial intelligence...",
                                            "publish_date": "2025-01-18",
                                            "author": "Jane Smith",
                                            "tags": ["AI", "technology", "innovation"],
                                        },
                                    }
                                ],
                            },
                            "extracted_data": {
                                "batch_results": [
                                    {
                                        "url": "https://blog1.example.com/article-1",
                                        "status": "success",
                                        "title": "Innovation in AI Development",
                                        "summary": "Latest trends in artificial intelligence...",
                                        "author": "Jane Smith",
                                        "tags": ["AI", "technology", "innovation"],
                                    }
                                ],
                                "success_count": 1,
                                "failure_count": 0,
                                "batch_id": "batch_001",
                            },
                            "urls_processed": [
                                "https://blog1.example.com/article-1",
                                "https://blog2.example.com/article-2",
                                "https://news.example.com/breaking-news",
                                "https://research.example.com/study-results",
                            ],
                            "execution_stats": {
                                "action_type": "firecrawl_batch_scrape",
                                "processing_time_ms": 8500,
                                "total_urls": 4,
                                "successful_extractions": 4,
                                "failed_extractions": 0,
                                "parallel_processing": True,
                            },
                        }
                    },
                },
            ],
        )


# Export the specification instance
FIRECRAWL_EXTERNAL_ACTION_SPEC = FirecrawlActionSpec()
