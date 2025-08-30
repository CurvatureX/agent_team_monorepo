"""
Generic API Call SDK client implementation.
"""

import base64
import os
from typing import Any, Dict, Optional
from urllib.parse import urlencode, urlparse

from ..base import APIResponse, BaseSDK, OAuth2Config
from .exceptions import (
    ApiCallAuthError,
    ApiCallError,
    ApiCallNotFoundError,
    ApiCallRateLimitError,
    ApiCallTimeoutError,
    ApiCallValidationError,
)
from .models import ApiRequest, ApiResponse


class ApiCallSDK(BaseSDK):
    """Generic API Call SDK client."""

    @property
    def base_url(self) -> str:
        # Generic API call doesn't have a fixed base URL
        return ""

    @property
    def supported_operations(self) -> Dict[str, str]:
        return {
            "get": "Make GET request",
            "post": "Make POST request",
            "put": "Make PUT request",
            "delete": "Make DELETE request",
            "patch": "Make PATCH request",
            "head": "Make HEAD request",
            "options": "Make OPTIONS request",
            "request": "Make generic HTTP request",
        }

    def get_oauth2_config(self) -> OAuth2Config:
        """Get OAuth2 configuration for generic API calls."""
        # Generic API call can be configured with any OAuth2 provider
        return OAuth2Config(
            client_id=os.getenv("API_CALL_CLIENT_ID", ""),
            client_secret=os.getenv("API_CALL_CLIENT_SECRET", ""),
            auth_url=os.getenv("API_CALL_AUTH_URL", ""),
            token_url=os.getenv("API_CALL_TOKEN_URL", ""),
            revoke_url=os.getenv("API_CALL_REVOKE_URL", ""),
            scopes=os.getenv("API_CALL_SCOPES", "").split(",")
            if os.getenv("API_CALL_SCOPES")
            else [],
            redirect_uri=os.getenv(
                "API_CALL_REDIRECT_URI", "http://localhost:8002/api/v1/oauth2/api_call/callback"
            ),
        )

    def get_custom_oauth2_config(self, provider: str) -> OAuth2Config:
        """Get OAuth2 configuration for specific provider."""
        # Support for common OAuth2 providers
        provider_configs = {
            "google": OAuth2Config(
                client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
                client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
                auth_url="https://accounts.google.com/o/oauth2/auth",
                token_url="https://oauth2.googleapis.com/token",
                revoke_url="https://oauth2.googleapis.com/revoke",
                scopes=["openid", "email", "profile"],
                redirect_uri=os.getenv(
                    "GOOGLE_REDIRECT_URI", "http://localhost:8000/api/v1/public/webhooks/google/auth"
                ),
            ),
            "microsoft": OAuth2Config(
                client_id=os.getenv("MICROSOFT_CLIENT_ID", ""),
                client_secret=os.getenv("MICROSOFT_CLIENT_SECRET", ""),
                auth_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
                token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
                revoke_url="",
                scopes=["openid", "email", "profile"],
                redirect_uri=os.getenv(
                    "MICROSOFT_REDIRECT_URI",
                    "http://localhost:8002/api/v1/oauth2/microsoft/callback",
                ),
            ),
            "facebook": OAuth2Config(
                client_id=os.getenv("FACEBOOK_CLIENT_ID", ""),
                client_secret=os.getenv("FACEBOOK_CLIENT_SECRET", ""),
                auth_url="https://www.facebook.com/v18.0/dialog/oauth",
                token_url="https://graph.facebook.com/v18.0/oauth/access_token",
                revoke_url="",
                scopes=["email", "public_profile"],
                redirect_uri=os.getenv(
                    "FACEBOOK_REDIRECT_URI", "http://localhost:8002/api/v1/oauth2/facebook/callback"
                ),
            ),
        }

        return provider_configs.get(provider, self.get_oauth2_config())

    def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """Validate credentials - can be empty for public APIs."""
        # Generic API calls may not require credentials
        return True

    async def call_operation(
        self, operation: str, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> APIResponse:
        """Execute generic API operation."""

        if operation not in self.supported_operations:
            return APIResponse(
                success=False,
                error=f"Unsupported operation: {operation}",
                provider="api_call",
                operation=operation,
            )

        try:
            # Create API request from parameters
            if operation == "request":
                # Generic request operation
                if "method" not in parameters or "url" not in parameters:
                    return APIResponse(
                        success=False,
                        error="Missing required parameters: method and url",
                        provider="api_call",
                        operation=operation,
                    )

                api_request = ApiRequest.from_dict(parameters)
            else:
                # Specific HTTP method operations
                if "url" not in parameters:
                    return APIResponse(
                        success=False,
                        error="Missing required parameter: url",
                        provider="api_call",
                        operation=operation,
                    )

                api_request = ApiRequest(
                    method=operation.upper(),
                    url=parameters["url"],
                    headers=parameters.get("headers", {}),
                    query_params=parameters.get("query_params", {}),
                    body=parameters.get("body"),
                    timeout=parameters.get("timeout", 30),
                    auth_type=parameters.get("auth_type"),
                    auth_credentials=parameters.get("auth_credentials", {}),
                )

            # Add authentication headers if provided
            headers = self._prepare_headers(api_request, credentials)

            # Build final URL with query parameters
            final_url = self._build_url(api_request.url, api_request.query_params)

            # Make HTTP request
            response = await self.make_http_request(
                method=api_request.method,
                url=final_url,
                headers=headers,
                json_data=api_request.body if isinstance(api_request.body, dict) else None,
                data=api_request.body if isinstance(api_request.body, (str, bytes)) else None,
                timeout=api_request.timeout or 30,
            )

            # Convert response
            api_response = ApiResponse.from_httpx_response(response, final_url)

            return APIResponse(
                success=api_response.is_success,
                data=api_response.to_dict(),
                provider="api_call",
                operation=operation,
                status_code=api_response.status_code,
            )

        except ApiCallTimeoutError as e:
            return APIResponse(
                success=False,
                error=str(e),
                provider="api_call",
                operation=operation,
                status_code=408,
            )
        except (ApiCallAuthError, ApiCallNotFoundError, ApiCallRateLimitError) as e:
            status_code = 401
            if isinstance(e, ApiCallNotFoundError):
                status_code = 404
            elif isinstance(e, ApiCallRateLimitError):
                status_code = 429

            return APIResponse(
                success=False,
                error=str(e),
                provider="api_call",
                operation=operation,
                status_code=status_code,
            )
        except Exception as e:
            self.logger.error(f"API call {operation} failed: {str(e)}")
            return APIResponse(
                success=False, error=str(e), provider="api_call", operation=operation
            )

    async def _test_connection_impl(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Generic API connection test (not applicable)."""
        return {
            "credentials_valid": True,
            "note": "Generic API call SDK - connection test not applicable",
        }

    def _prepare_headers(self, request: ApiRequest, credentials: Dict[str, str]) -> Dict[str, str]:
        """Prepare request headers with authentication."""
        headers = request.headers.copy() if request.headers else {}

        # Set default content type for POST/PUT/PATCH requests with body
        if request.method in ["POST", "PUT", "PATCH"] and request.body:
            if "content-type" not in {k.lower() for k in headers.keys()}:
                if isinstance(request.body, dict):
                    headers["Content-Type"] = "application/json"
                elif isinstance(request.body, str):
                    headers["Content-Type"] = "application/json"
                elif isinstance(request.body, bytes):
                    headers["Content-Type"] = "application/octet-stream"

        # Add authentication based on auth_type
        auth_type = request.auth_type or "bearer"  # Default to bearer token
        auth_creds = request.auth_credentials or credentials

        if auth_type == "bearer" and "access_token" in auth_creds:
            headers["Authorization"] = f"Bearer {auth_creds['access_token']}"
        elif auth_type == "bearer" and "token" in auth_creds:
            headers["Authorization"] = f"Bearer {auth_creds['token']}"
        elif auth_type == "api_key":
            api_key = auth_creds.get("api_key") or auth_creds.get("key")
            key_header = auth_creds.get("key_header", "X-API-Key")
            if api_key:
                headers[key_header] = api_key
        elif auth_type == "basic":
            username = auth_creds.get("username", "")
            password = auth_creds.get("password", "")
            if username and password:
                basic_auth = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers["Authorization"] = f"Basic {basic_auth}"
        elif auth_type == "oauth2" and "access_token" in auth_creds:
            headers["Authorization"] = f"Bearer {auth_creds['access_token']}"

        # Add custom headers from credentials
        if "headers" in auth_creds:
            headers.update(auth_creds["headers"])

        return headers

    def _build_url(self, base_url: str, query_params: Optional[Dict[str, str]]) -> str:
        """Build final URL with query parameters."""
        if not query_params:
            return base_url

        # Parse existing query parameters
        parsed = urlparse(base_url)

        if parsed.query:
            # URL already has query parameters
            separator = "&"
        else:
            separator = "?"

        query_string = urlencode(query_params)
        return f"{base_url}{separator}{query_string}"

    def _handle_error(self, response) -> None:
        """Handle HTTP error responses."""
        if response.status_code == 401:
            raise ApiCallAuthError("Authentication failed")
        elif response.status_code == 403:
            raise ApiCallAuthError("Access forbidden")
        elif response.status_code == 404:
            raise ApiCallNotFoundError("Resource not found")
        elif response.status_code == 429:
            raise ApiCallRateLimitError("Rate limit exceeded")
        elif response.status_code == 408:
            raise ApiCallTimeoutError("Request timeout")
        elif 400 <= response.status_code < 500:
            raise ApiCallValidationError(f"Client error: {response.status_code}")
        elif 500 <= response.status_code < 600:
            raise ApiCallError(f"Server error: {response.status_code}")
        else:
            raise ApiCallError(f"Unexpected error: {response.status_code}")
