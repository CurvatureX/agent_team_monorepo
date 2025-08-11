"""
Validation Middleware for Enhanced Request/Response Security
增强请求/响应安全验证中间件
"""

import json
from typing import Any, Dict

from app.exceptions import ValidationError
from app.services.validation import validation_service
from shared.logging_config import get_logger
from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = get_logger(__name__)


class ValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request/response validation and security checks
    """

    def __init__(self, app, enable_security_checks: bool = True, max_request_size_mb: float = 10.0):
        super().__init__(app)
        self.enable_security_checks = enable_security_checks
        self.max_request_size_mb = max_request_size_mb
        self.excluded_paths = [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/public/health",
            "/api/v1/public/status",
        ]

    async def dispatch(self, request: Request, call_next):
        """Process request and response validation"""

        # Skip validation for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        # Skip validation for static files
        if any(ext in request.url.path for ext in [".js", ".css", ".png", ".jpg", ".ico", ".svg"]):
            return await call_next(request)

        try:
            # Validate request
            validation_result = await self._validate_request(request)
            if not validation_result.is_valid:
                return self._create_validation_error_response(validation_result.errors)

            # Process the request
            response = await call_next(request)

            # Validate response (for JSON responses)
            if hasattr(response, "body") and response.headers.get("content-type", "").startswith(
                "application/json"
            ):
                validated_response = await self._validate_response(response)
                if validated_response:
                    return validated_response

            return response

        except ValidationError as e:
            logger.warning(f"🚨 Validation middleware blocked request: {e}")
            return self._create_validation_error_response([str(e)])
        except Exception as e:
            logger.error(f"❌ Validation middleware error: {e}")
            # Don't block request for internal middleware errors
            return await call_next(request)

    async def _validate_request(self, request: Request):
        """Validate incoming request"""

        # Get request data for validation
        request_data = None

        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                # Read request body for validation
                body = await request.body()
                if body:
                    content_type = request.headers.get("content-type", "")

                    if "application/json" in content_type:
                        request_data = json.loads(body.decode())
                    elif "application/x-www-form-urlencoded" in content_type:
                        # For form data, validate as key-value pairs
                        form_data = await request.form()
                        request_data = dict(form_data)
                    # Note: Multipart form data (file uploads) handled separately

                # Restore body for downstream processing
                async def receive():
                    return {"type": "http.request", "body": body}

                request._receive = receive

            except json.JSONDecodeError:
                return validation_service.input_validator.validate_request_data(
                    None, security_check=False
                )._replace(is_valid=False, errors=["Invalid JSON in request body"])
            except Exception as e:
                logger.error(f"❌ Error reading request body: {e}")
                return validation_service.input_validator.validate_request_data(None)

        # Validate query parameters
        if request.query_params:
            query_data = dict(request.query_params)
            query_validation = validation_service.input_validator.validate_request_data(
                query_data, security_check=self.enable_security_checks
            )
            if not query_validation.is_valid:
                return query_validation

        # Validate headers for potential threats
        suspicious_headers = []
        for name, value in request.headers.items():
            if self.enable_security_checks:
                threats = validation_service.input_validator._check_security_threats(value)
                if threats:
                    suspicious_headers.extend([f"Header {name}: {threat}" for threat in threats])

        if suspicious_headers:
            return validation_service.input_validator.validate_request_data(None)._replace(
                is_valid=False, errors=suspicious_headers
            )

        # Validate main request data
        return await validation_service.validate_request(
            request,
            request_data,
            security_check=self.enable_security_checks,
            max_size_mb=self.max_request_size_mb,
        )

    async def _validate_response(self, response: Response):
        """Validate outgoing response"""
        try:
            # Only validate JSON responses
            if not response.headers.get("content-type", "").startswith("application/json"):
                return None

            # Get response body
            body = b""
            async for chunk in response.body_iterator:
                body += chunk

            if not body:
                return None

            # Parse JSON response
            try:
                response_data = json.loads(body.decode())
            except json.JSONDecodeError:
                logger.warning("🚨 Response contains invalid JSON")
                return None

            # Validate response data
            validation_result = await validation_service.validate_response(response_data)

            if not validation_result.is_valid:
                logger.error(f"🚨 Response validation failed: {validation_result.errors}")
                # In production, you might want to sanitize rather than block
                # For now, we'll log the error but allow the response

            # Return original response (validation is mainly for logging/monitoring)
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        except Exception as e:
            logger.error(f"❌ Error validating response: {e}")
            return None

    def _create_validation_error_response(self, errors: list) -> JSONResponse:
        """Create standardized validation error response"""
        return JSONResponse(
            status_code=400,
            content={
                "error": "validation_failed",
                "message": "Request validation failed",
                "details": {
                    "validation_errors": errors,
                    "security_check_enabled": self.enable_security_checks,
                    "help": "Please ensure your request data is properly formatted and does not contain malicious content",
                },
                "timestamp": logger.info("🚨 Validation error response sent"),
            },
        )


# Utility function to add validation middleware to FastAPI app
def add_validation_middleware(
    app, enable_security_checks: bool = True, max_request_size_mb: float = 10.0
):
    """Add validation middleware to FastAPI application"""
    app.add_middleware(
        ValidationMiddleware,
        enable_security_checks=enable_security_checks,
        max_request_size_mb=max_request_size_mb,
    )
    logger.info(
        f"✅ Validation middleware added (security_checks: {enable_security_checks}, max_size: {max_request_size_mb}MB)"
    )


# Export
__all__ = ["ValidationMiddleware", "add_validation_middleware"]
