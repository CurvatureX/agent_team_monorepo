"""
Enhanced Request/Response Validation Service
增强的请求/响应验证服务

Provides comprehensive input sanitization, output validation,
and security checks for all API endpoints.
"""

import html
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import bleach
from app.exceptions import ValidationError
from shared.logging_config import get_logger
from fastapi import HTTPException, Request
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

logger = get_logger(__name__)


class ValidationResult:
    """Validation result container"""

    def __init__(self, is_valid: bool, data: Any = None, errors: List[str] = None):
        self.is_valid = is_valid
        self.data = data
        self.errors = errors or []
        self.sanitized = False


class SecurityValidator:
    """Security-focused validation and sanitization"""

    # Common malicious patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"vbscript:",
        r"onload\s*=",
        r"onerror\s*=",
        r"onclick\s*=",
        r"onmouseover\s*=",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
    ]

    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"('|(\\'))+.*(=|like|union|insert|delete|update|drop|create|alter)",
        r"(union|select|insert|delete|update|drop|create|alter)\s+",
        r"--\s*",
        r"/\*[\s\S]*?\*/",
        r"\bor\s+\d+=\d+",
        r"\band\s+\d+=\d+",
    ]

    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$()]",
        r"(rm|cat|ls|ps|kill|wget|curl|nc|netcat)\s+",
        r"\.\./.*",
        r"/etc/passwd",
        r"/proc/",
    ]

    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\.[/\\]",
        r"[/\\]\.\.[/\\]",
        r"%2e%2e[/\\]",
        r"\.%2e[/\\]",
        r"%2e\.[/\\]",
    ]

    @classmethod
    def detect_xss(cls, text: str) -> List[str]:
        """Detect potential XSS attacks"""
        threats = []
        text_lower = text.lower()

        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                threats.append(f"XSS pattern detected: {pattern}")

        return threats

    @classmethod
    def detect_sql_injection(cls, text: str) -> List[str]:
        """Detect potential SQL injection attacks"""
        threats = []
        text_lower = text.lower()

        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                threats.append(f"SQL injection pattern detected: {pattern}")

        return threats

    @classmethod
    def detect_command_injection(cls, text: str) -> List[str]:
        """Detect potential command injection attacks"""
        threats = []

        for pattern in cls.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                threats.append(f"Command injection pattern detected: {pattern}")

        return threats

    @classmethod
    def detect_path_traversal(cls, text: str) -> List[str]:
        """Detect potential path traversal attacks"""
        threats = []

        for pattern in cls.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                threats.append(f"Path traversal pattern detected: {pattern}")

        return threats

    @classmethod
    def sanitize_html(cls, text: str) -> str:
        """Sanitize HTML content"""
        if not isinstance(text, str):
            return text

        # Allowed HTML tags and attributes (very restrictive)
        allowed_tags = ["p", "br", "strong", "em", "u", "i", "b"]
        allowed_attributes = {}

        # Clean HTML
        cleaned = bleach.clean(text, tags=allowed_tags, attributes=allowed_attributes)

        # HTML escape any remaining content
        return html.escape(cleaned)

    @classmethod
    def sanitize_string(cls, text: str, max_length: int = 1000) -> str:
        """Sanitize general string input"""
        if not isinstance(text, str):
            return str(text)

        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length]

        # Remove null bytes and control characters
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

        # Strip whitespace
        text = text.strip()

        return text


class InputValidator:
    """Input validation service"""

    def __init__(self):
        self.security_validator = SecurityValidator()

    def validate_request_data(self, data: Any, security_check: bool = True) -> ValidationResult:
        """Validate and sanitize request data"""
        try:
            if data is None:
                return ValidationResult(is_valid=True, data=None)

            errors = []
            sanitized_data = data

            # Recursive validation for complex objects
            if isinstance(data, dict):
                sanitized_data, dict_errors = self._validate_dict(data, security_check)
                errors.extend(dict_errors)
            elif isinstance(data, list):
                sanitized_data, list_errors = self._validate_list(data, security_check)
                errors.extend(list_errors)
            elif isinstance(data, str):
                sanitized_data, str_errors = self._validate_string(data, security_check)
                errors.extend(str_errors)

            is_valid = len(errors) == 0
            result = ValidationResult(is_valid=is_valid, data=sanitized_data, errors=errors)
            result.sanitized = True

            if not is_valid:
                logger.warning(f"🚨 Validation failed with {len(errors)} errors: {errors}")

            return result

        except Exception as e:
            logger.error(f"❌ Error during validation: {e}")
            return ValidationResult(is_valid=False, errors=[f"Validation error: {str(e)}"])

    def _validate_dict(self, data: Dict[str, Any], security_check: bool) -> tuple:
        """Validate dictionary data"""
        errors = []
        sanitized = {}

        for key, value in data.items():
            # Validate key
            if not isinstance(key, str):
                errors.append(f"Invalid key type: {type(key)}")
                continue

            # Security check on key
            if security_check:
                key_threats = self._check_security_threats(key)
                if key_threats:
                    errors.extend(
                        [f"Security threat in key '{key}': {threat}" for threat in key_threats]
                    )
                    continue

            # Sanitize key
            clean_key = self.security_validator.sanitize_string(key, max_length=200)

            # Validate value recursively
            if isinstance(value, (dict, list, str)):
                if isinstance(value, dict):
                    clean_value, sub_errors = self._validate_dict(value, security_check)
                elif isinstance(value, list):
                    clean_value, sub_errors = self._validate_list(value, security_check)
                else:
                    clean_value, sub_errors = self._validate_string(value, security_check)

                errors.extend(sub_errors)
                sanitized[clean_key] = clean_value
            else:
                # For primitive types, store as-is
                sanitized[clean_key] = value

        return sanitized, errors

    def _validate_list(self, data: List[Any], security_check: bool) -> tuple:
        """Validate list data"""
        errors = []
        sanitized = []

        if len(data) > 1000:  # Prevent huge arrays
            errors.append("Array too large (max 1000 items)")
            data = data[:1000]

        for i, item in enumerate(data):
            if isinstance(item, dict):
                clean_item, sub_errors = self._validate_dict(item, security_check)
                errors.extend([f"Item {i}: {error}" for error in sub_errors])
                sanitized.append(clean_item)
            elif isinstance(item, list):
                clean_item, sub_errors = self._validate_list(item, security_check)
                errors.extend([f"Item {i}: {error}" for error in sub_errors])
                sanitized.append(clean_item)
            elif isinstance(item, str):
                clean_item, sub_errors = self._validate_string(item, security_check)
                errors.extend([f"Item {i}: {error}" for error in sub_errors])
                sanitized.append(clean_item)
            else:
                sanitized.append(item)

        return sanitized, errors

    def _validate_string(self, data: str, security_check: bool) -> tuple:
        """Validate string data"""
        errors = []

        if security_check:
            threats = self._check_security_threats(data)
            if threats:
                errors.extend(threats)

        # Sanitize string
        sanitized = self.security_validator.sanitize_string(data)

        return sanitized, errors

    def _check_security_threats(self, text: str) -> List[str]:
        """Check for security threats in text"""
        threats = []

        threats.extend(self.security_validator.detect_xss(text))
        threats.extend(self.security_validator.detect_sql_injection(text))
        threats.extend(self.security_validator.detect_command_injection(text))
        threats.extend(self.security_validator.detect_path_traversal(text))

        return threats


class ResponseValidator:
    """Response validation service"""

    def validate_response_data(
        self, data: Any, model: Optional[BaseModel] = None
    ) -> ValidationResult:
        """Validate response data before sending to client"""
        try:
            errors = []

            # Validate against Pydantic model if provided
            if model and data:
                try:
                    if isinstance(data, dict):
                        validated_data = model(**data)
                        data = validated_data.model_dump()
                    elif hasattr(data, "model_dump"):
                        # Already a Pydantic model
                        data = data.model_dump()
                except PydanticValidationError as e:
                    errors.extend(
                        [f"Response validation error: {error['msg']}" for error in e.errors()]
                    )

            # Check for sensitive data leakage
            sensitive_fields = ["password", "secret", "key", "token", "private"]
            if isinstance(data, dict):
                leaked_fields = self._check_sensitive_fields(data, sensitive_fields)
                if leaked_fields:
                    errors.extend(
                        [
                            f"Sensitive field detected in response: {field}"
                            for field in leaked_fields
                        ]
                    )

            # Ensure JSON serializability
            try:
                json.dumps(data, default=str)
            except TypeError as e:
                errors.append(f"Response not JSON serializable: {str(e)}")

            is_valid = len(errors) == 0
            if not is_valid:
                logger.error(f"🚨 Response validation failed: {errors}")

            return ValidationResult(is_valid=is_valid, data=data, errors=errors)

        except Exception as e:
            logger.error(f"❌ Error during response validation: {e}")
            return ValidationResult(is_valid=False, errors=[f"Response validation error: {str(e)}"])

    def _check_sensitive_fields(
        self, data: Dict[str, Any], sensitive_fields: List[str]
    ) -> List[str]:
        """Check for sensitive fields in response data"""
        leaked_fields = []

        def check_recursive(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key

                    # Check if key contains sensitive information
                    if any(sensitive in key.lower() for sensitive in sensitive_fields):
                        # Allow certain exceptions (like public tokens, key names, etc.)
                        if not any(
                            exception in key.lower()
                            for exception in ["public", "name", "type", "id"]
                        ):
                            leaked_fields.append(current_path)

                    # Recurse into nested objects
                    if isinstance(value, (dict, list)):
                        check_recursive(value, current_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_recursive(item, f"{path}[{i}]")

        check_recursive(data)
        return leaked_fields


class EnhancedValidationService:
    """Main validation service combining input and response validation"""

    def __init__(self):
        self.input_validator = InputValidator()
        self.response_validator = ResponseValidator()
        self.stats = {
            "requests_validated": 0,
            "responses_validated": 0,
            "threats_detected": 0,
            "validation_errors": 0,
        }

    async def validate_request(
        self,
        request: Request,
        data: Any = None,
        security_check: bool = True,
        max_size_mb: float = 10.0,
    ) -> ValidationResult:
        """Comprehensive request validation"""
        try:
            self.stats["requests_validated"] += 1

            # Check request size
            content_length = request.headers.get("content-length")
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                if size_mb > max_size_mb:
                    raise ValidationError(
                        f"Request too large: {size_mb:.2f}MB (max: {max_size_mb}MB)"
                    )

            # Validate content type for POST/PUT requests
            if request.method in ["POST", "PUT", "PATCH"]:
                content_type = request.headers.get("content-type", "")
                if not any(
                    allowed in content_type
                    for allowed in [
                        "application/json",
                        "multipart/form-data",
                        "application/x-www-form-urlencoded",
                    ]
                ):
                    raise ValidationError(f"Unsupported content type: {content_type}")

            # Validate request data if provided
            validation_result = ValidationResult(is_valid=True, data=data)
            if data is not None:
                validation_result = self.input_validator.validate_request_data(data, security_check)

                if not validation_result.is_valid:
                    self.stats["validation_errors"] += 1
                    if any("threat" in error.lower() for error in validation_result.errors):
                        self.stats["threats_detected"] += 1

            # Log validation results
            if not validation_result.is_valid:
                logger.warning(
                    f"🚨 Request validation failed for {request.method} {request.url.path}: {validation_result.errors}"
                )
            else:
                logger.debug(f"✅ Request validation passed for {request.method} {request.url.path}")

            return validation_result

        except Exception as e:
            self.stats["validation_errors"] += 1
            logger.error(f"❌ Request validation error: {e}")
            return ValidationResult(is_valid=False, errors=[str(e)])

    async def validate_response(
        self, data: Any, model: Optional[BaseModel] = None, remove_sensitive: bool = True
    ) -> ValidationResult:
        """Comprehensive response validation"""
        try:
            self.stats["responses_validated"] += 1

            validation_result = self.response_validator.validate_response_data(data, model)

            if not validation_result.is_valid:
                self.stats["validation_errors"] += 1
                logger.warning(f"🚨 Response validation failed: {validation_result.errors}")
            else:
                logger.debug("✅ Response validation passed")

            return validation_result

        except Exception as e:
            self.stats["validation_errors"] += 1
            logger.error(f"❌ Response validation error: {e}")
            return ValidationResult(is_valid=False, errors=[str(e)])

    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics"""
        return {
            **self.stats,
            "threat_detection_rate": (
                self.stats["threats_detected"] / max(1, self.stats["requests_validated"])
            )
            * 100,
            "error_rate": (
                self.stats["validation_errors"]
                / max(1, self.stats["requests_validated"] + self.stats["responses_validated"])
            )
            * 100,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def reset_stats(self) -> None:
        """Reset validation statistics"""
        self.stats = {
            "requests_validated": 0,
            "responses_validated": 0,
            "threats_detected": 0,
            "validation_errors": 0,
        }


# Global validation service instance
validation_service = EnhancedValidationService()


# FastAPI dependency
async def get_validation_service() -> EnhancedValidationService:
    """FastAPI dependency for getting validation service"""
    return validation_service


# Validation decorators and utilities
def validate_request_size(max_size_mb: float = 10.0):
    """Decorator to validate request size"""

    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            content_length = request.headers.get("content-length")
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                if size_mb > max_size_mb:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Request too large: {size_mb:.2f}MB (max: {max_size_mb}MB)",
                    )
            return await func(request, *args, **kwargs)

        return wrapper

    return decorator


# Export commonly used items
__all__ = [
    "EnhancedValidationService",
    "ValidationResult",
    "SecurityValidator",
    "InputValidator",
    "ResponseValidator",
    "validation_service",
    "get_validation_service",
    "validate_request_size",
]
