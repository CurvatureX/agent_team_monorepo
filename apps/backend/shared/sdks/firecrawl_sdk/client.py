"""
Firecrawl API client (minimal) implemented as an SDK.

Provides operations aligned with Firecrawl MCP tools:
- firecrawl_scrape
- firecrawl_map
- firecrawl_crawl
- firecrawl_check_crawl_status
- firecrawl_batch_scrape
- firecrawl_check_batch_status
- firecrawl_search
- firecrawl_extract
- firecrawl_generate_llmstxt

NOTE: Endpoint paths are inferred from public Firecrawl docs and may need
adjustment to your deployment.
"""

import os
from typing import Any, Dict, Optional

from ..base import APIResponse, BaseSDK, OAuth2Config


class FirecrawlAPIError(Exception):
    pass


class FirecrawlSDK(BaseSDK):
    @property
    def base_url(self) -> str:
        return os.getenv("FIRECRAWL_API_URL", "https://api.firecrawl.dev/v1")

    @property
    def supported_operations(self) -> Dict[str, str]:
        return {
            "firecrawl_scrape": "Scrape a single URL",
            "firecrawl_map": "Discover URLs from a starting URL",
            "firecrawl_crawl": "Start an async crawl job",
            "firecrawl_check_crawl_status": "Check crawl job status",
            "firecrawl_batch_scrape": "Batch scrape multiple URLs",
            "firecrawl_check_batch_status": "Check batch scrape status",
            "firecrawl_search": "Search the web and optionally scrape results",
            "firecrawl_extract": "Extract structured info using an LLM",
            "firecrawl_generate_llmstxt": "Generate LLMs.txt for a domain",
        }

    def get_oauth2_config(self) -> OAuth2Config:
        # Uses API key header, not OAuth2
        return OAuth2Config(client_id="", client_secret="", auth_url="", token_url="")

    def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        return bool(credentials.get("api_key"))

    def _headers(self, credentials: Dict[str, str]) -> Dict[str, str]:
        api_key = credentials.get("api_key", "")
        return self.prepare_headers({}, {"Authorization": f"Bearer {api_key}"})

    async def call_operation(
        self, operation: str, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> APIResponse:
        if not self.validate_credentials(credentials):
            return APIResponse(
                success=False,
                error="Invalid credentials: missing api_key",
                provider="firecrawl",
                operation=operation,
            )

        if operation not in self.supported_operations:
            return APIResponse(
                success=False,
                error=f"Unsupported operation: {operation}",
                provider="firecrawl",
                operation=operation,
            )

        try:
            handler = getattr(self, f"_{operation}")
        except AttributeError:
            return APIResponse(
                success=False,
                error=f"Operation not implemented: {operation}",
                provider="firecrawl",
                operation=operation,
            )

        try:
            data = await handler(parameters, credentials)
            return APIResponse(success=True, data=data, provider="firecrawl", operation=operation)
        except Exception as e:
            self.logger.error(f"Firecrawl {operation} failed: {e}")
            return APIResponse(
                success=False, error=str(e), provider="firecrawl", operation=operation
            )

    # Operations
    async def _firecrawl_scrape(self, params: Dict[str, Any], credentials: Dict[str, str]):
        url = params.get("url")
        if not url:
            raise FirecrawlAPIError("Missing required parameter: url")
        endpoint = f"{self.base_url}/scrape"
        headers = self._headers(credentials)
        response = await self.make_http_request("POST", endpoint, headers=headers, json_data=params)
        if not (200 <= response.status_code < 300):
            self.handle_http_error(response, "firecrawl_scrape")
        return response.json()

    async def _firecrawl_map(self, params: Dict[str, Any], credentials: Dict[str, str]):
        if not params.get("url"):
            raise FirecrawlAPIError("Missing required parameter: url")
        endpoint = f"{self.base_url}/map"
        headers = self._headers(credentials)
        response = await self.make_http_request("POST", endpoint, headers=headers, json_data=params)
        if not (200 <= response.status_code < 300):
            self.handle_http_error(response, "firecrawl_map")
        return response.json()

    async def _firecrawl_crawl(self, params: Dict[str, Any], credentials: Dict[str, str]):
        if not params.get("url"):
            raise FirecrawlAPIError("Missing required parameter: url")
        endpoint = f"{self.base_url}/crawl"
        headers = self._headers(credentials)
        response = await self.make_http_request("POST", endpoint, headers=headers, json_data=params)
        if not (200 <= response.status_code < 300):
            self.handle_http_error(response, "firecrawl_crawl")
        return response.json()

    async def _firecrawl_check_crawl_status(
        self, params: Dict[str, Any], credentials: Dict[str, str]
    ):
        job_id = params.get("id")
        if not job_id:
            raise FirecrawlAPIError("Missing required parameter: id")
        endpoint = f"{self.base_url}/crawl/{job_id}"
        headers = self._headers(credentials)
        response = await self.make_http_request("GET", endpoint, headers=headers)
        if not (200 <= response.status_code < 300):
            self.handle_http_error(response, "firecrawl_check_crawl_status")
        return response.json()

    async def _firecrawl_batch_scrape(self, params: Dict[str, Any], credentials: Dict[str, str]):
        if not params.get("urls"):
            raise FirecrawlAPIError("Missing required parameter: urls")
        endpoint = f"{self.base_url}/scrape/batch"
        headers = self._headers(credentials)
        response = await self.make_http_request("POST", endpoint, headers=headers, json_data=params)
        if not (200 <= response.status_code < 300):
            self.handle_http_error(response, "firecrawl_batch_scrape")
        return response.json()

    async def _firecrawl_check_batch_status(
        self, params: Dict[str, Any], credentials: Dict[str, str]
    ):
        job_id = params.get("id")
        if not job_id:
            raise FirecrawlAPIError("Missing required parameter: id")
        endpoint = f"{self.base_url}/scrape/batch/{job_id}"
        headers = self._headers(credentials)
        response = await self.make_http_request("GET", endpoint, headers=headers)
        if not (200 <= response.status_code < 300):
            self.handle_http_error(response, "firecrawl_check_batch_status")
        return response.json()

    async def _firecrawl_search(self, params: Dict[str, Any], credentials: Dict[str, str]):
        if not params.get("query"):
            raise FirecrawlAPIError("Missing required parameter: query")
        endpoint = f"{self.base_url}/search"
        headers = self._headers(credentials)
        response = await self.make_http_request("POST", endpoint, headers=headers, json_data=params)
        if not (200 <= response.status_code < 300):
            self.handle_http_error(response, "firecrawl_search")
        return response.json()

    async def _firecrawl_extract(self, params: Dict[str, Any], credentials: Dict[str, str]):
        if not params.get("urls"):
            raise FirecrawlAPIError("Missing required parameter: urls")
        endpoint = f"{self.base_url}/extract"
        headers = self._headers(credentials)
        response = await self.make_http_request("POST", endpoint, headers=headers, json_data=params)
        if not (200 <= response.status_code < 300):
            self.handle_http_error(response, "firecrawl_extract")
        return response.json()

    async def _firecrawl_generate_llmstxt(
        self, params: Dict[str, Any], credentials: Dict[str, str]
    ):
        if not params.get("url"):
            raise FirecrawlAPIError("Missing required parameter: url")
        endpoint = f"{self.base_url}/llmstxt/generate"
        headers = self._headers(credentials)
        response = await self.make_http_request("POST", endpoint, headers=headers, json_data=params)
        if not (200 <= response.status_code < 300):
            self.handle_http_error(response, "firecrawl_generate_llmstxt")
        return response.json()
