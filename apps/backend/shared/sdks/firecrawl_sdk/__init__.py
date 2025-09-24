"""
Firecrawl SDK for web scraping/search operations.

This SDK mirrors the tool naming and parameters used in common Firecrawl MCP
servers. It targets the Firecrawl HTTP API using an API key.
"""

from .client import FirecrawlAPIError, FirecrawlSDK

__all__ = [
    "FirecrawlSDK",
    "FirecrawlAPIError",
]
