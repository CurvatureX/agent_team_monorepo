"""
Logging middleware for comprehensive request/response logging
"""

import time
import uuid
from typing import Callable

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()


class MCPLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging MCP requests and responses"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and response with comprehensive logging

        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain

        Returns:
            Response: HTTP response
        """
        # Generate request ID for tracing
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Start timing
        start_time = time.time()

        # Log incoming request
        await self._log_request(request, request_id)

        try:
            # Process request
            response = await call_next(request)

            # Calculate processing time
            processing_time = time.time() - start_time

            # Log successful response
            await self._log_response(request, response, request_id, processing_time)

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            # Calculate processing time for error case
            processing_time = time.time() - start_time

            # Log error
            logger.error(
                "Request processing failed",
                request_id=request_id,
                method=request.method,
                url=str(request.url),
                processing_time_ms=round(processing_time * 1000, 2),
                error=str(e),
                error_type=type(e).__name__,
            )

            # Create error response
            error_response = JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": "Internal server error",
                    "error_type": "INTERNAL_ERROR",
                    "request_id": request_id,
                },
                headers={"X-Request-ID": request_id},
            )

            return error_response

    async def _log_request(self, request: Request, request_id: str) -> None:
        """
        Log incoming request details

        Args:
            request: FastAPI request object
            request_id: Unique request identifier
        """
        # Get request body for POST requests (if applicable)
        request_body = None
        request_size = 0
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                # Read body without consuming it
                body = await request.body()
                if body:
                    request_size = len(body)
                    # Try to decode as JSON for logging (truncate if too long)
                    body_str = body.decode("utf-8")
                    if len(body_str) > 1000:
                        body_str = body_str[:1000] + "... (truncated)"
                    request_body = body_str
            except Exception:
                request_body = "<unable to read body>"

        # Extract relevant headers
        headers = {
            "user-agent": request.headers.get("user-agent"),
            "content-type": request.headers.get("content-type"),
            "content-length": request.headers.get("content-length"),
            "authorization": "***" if request.headers.get("authorization") else None,
            "x-forwarded-for": request.headers.get("x-forwarded-for"),
            "x-real-ip": request.headers.get("x-real-ip"),
        }
        # Remove None values
        headers = {k: v for k, v in headers.items() if v is not None}

        # Determine if this is an MCP request
        is_mcp_request = "/mcp/" in request.url.path

        logger.info(
            "Incoming request",
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            path=request.url.path,
            query_params=dict(request.query_params),
            headers=headers,
            client_ip=request.client.host if request.client else None,
            request_body=request_body,
            request_size=request_size,
            is_mcp_request=is_mcp_request,
            endpoint_category="mcp" if is_mcp_request else "other",
        )

    async def _log_response(
        self, request: Request, response: Response, request_id: str, processing_time: float
    ) -> None:
        """
        Log response details

        Args:
            request: FastAPI request object
            response: FastAPI response object
            request_id: Unique request identifier
            processing_time: Request processing time in seconds
        """
        # Extract response body for logging (if it's JSON and not too large)
        response_body = None
        response_size = 0
        if hasattr(response, "body") and response.body:
            try:
                response_size = len(response.body)
                body_str = response.body.decode("utf-8")
                if len(body_str) > 1000:
                    body_str = body_str[:1000] + "... (truncated)"
                response_body = body_str
            except Exception:
                response_body = "<unable to read response body>"

        # Determine log level based on status code
        log_level = "info"
        if response.status_code >= 400:
            log_level = "warning" if response.status_code < 500 else "error"

        # Determine if this is an MCP request
        is_mcp_request = "/mcp/" in request.url.path

        # Extract response headers
        response_headers = {
            "content-type": response.headers.get("content-type"),
            "content-length": response.headers.get("content-length"),
            "x-request-id": response.headers.get("x-request-id"),
            "retry-after": response.headers.get("retry-after"),
        }
        response_headers = {k: v for k, v in response_headers.items() if v is not None}

        # Performance categorization
        performance_category = "fast"
        if processing_time > 5.0:
            performance_category = "very_slow"
        elif processing_time > 2.0:
            performance_category = "slow"
        elif processing_time > 1.0:
            performance_category = "moderate"

        log_data = {
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "status_code": response.status_code,
            "processing_time_ms": round(processing_time * 1000, 2),
            "response_size": response_size,
            "response_body": response_body,
            "response_headers": response_headers,
            "is_mcp_request": is_mcp_request,
            "endpoint_category": "mcp" if is_mcp_request else "other",
            "performance_category": performance_category,
            "success": response.status_code < 400,
        }

        if log_level == "info":
            logger.info("Request completed successfully", **log_data)
        elif log_level == "warning":
            logger.warning("Request completed with client error", **log_data)
        else:
            logger.error("Request completed with server error", **log_data)


class MCPContextMiddleware(BaseHTTPMiddleware):
    """Middleware for adding MCP-specific context to logs"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add MCP context to structured logging

        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain

        Returns:
            Response: HTTP response
        """
        # Add MCP-specific context to all logs in this request
        with structlog.contextvars.bound_contextvars(
            service="mcp-api-gateway",
            request_path=request.url.path,
            request_method=request.method,
            request_id=getattr(request.state, "request_id", None),
        ):
            response = await call_next(request)
            return response


def setup_logging_middleware(app):
    """
    Setup logging middleware for the FastAPI app

    Args:
        app: FastAPI application instance
    """
    # Add context middleware first (outermost)
    app.add_middleware(MCPContextMiddleware)

    # Add logging middleware
    app.add_middleware(MCPLoggingMiddleware)

    logger.info("MCP logging middleware configured")
