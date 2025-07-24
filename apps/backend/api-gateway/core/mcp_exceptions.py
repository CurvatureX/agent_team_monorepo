"""
MCP service exception handling utilities
"""

import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional


class MCPErrorType(Enum):
    """MCP error types for classification"""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    PARAMETER_ERROR = "PARAMETER_ERROR"
    SERVICE_ERROR = "SERVICE_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class MCPError(Exception):
    """Base MCP exception class with enhanced error tracking"""

    def __init__(
        self,
        error_type: MCPErrorType,
        message: str,
        user_message: str,
        details: Optional[Dict[str, Any]] = None,
        error_id: Optional[str] = None,
        retryable: bool = False,
        retry_after: Optional[int] = None,
    ):
        self.error_type = error_type
        self.message = message
        self.user_message = user_message
        self.details = details or {}
        self.error_id = error_id or str(uuid.uuid4())
        self.timestamp = time.time()
        self.retryable = retryable
        self.retry_after = retry_after
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging and response"""
        return {
            "error_id": self.error_id,
            "error_type": self.error_type.value,
            "message": self.message,
            "user_message": self.user_message,
            "details": self.details,
            "timestamp": self.timestamp,
            "retryable": self.retryable,
            "retry_after": self.retry_after,
        }


class MCPValidationError(MCPError):
    """Validation error for MCP requests"""

    def __init__(
        self, message: str, user_message: str = None, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_type=MCPErrorType.VALIDATION_ERROR,
            message=message,
            user_message=user_message or message,
            details=details,
        )


class MCPToolNotFoundError(MCPError):
    """Tool not found error"""

    def __init__(self, tool_name: str):
        super().__init__(
            error_type=MCPErrorType.TOOL_NOT_FOUND,
            message=f"Tool '{tool_name}' not found",
            user_message="unknown tool",
            details={"tool_name": tool_name},
        )


class MCPParameterError(MCPError):
    """Parameter validation error"""

    def __init__(
        self, message: str, user_message: str = None, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_type=MCPErrorType.PARAMETER_ERROR,
            message=message,
            user_message=user_message or message,
            details=details,
        )


class MCPServiceError(MCPError):
    """Service execution error"""

    def __init__(
        self, message: str, user_message: str = None, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_type=MCPErrorType.SERVICE_ERROR,
            message=message,
            user_message=user_message or "Service error occurred",
            details=details,
        )


class MCPDatabaseError(MCPError):
    """Database operation error"""

    def __init__(
        self, message: str, user_message: str = None, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_type=MCPErrorType.DATABASE_ERROR,
            message=message,
            user_message=user_message or "Database error occurred",
            details=details,
            retryable=True,
            retry_after=5,
        )


class MCPNetworkError(MCPError):
    """Network operation error"""

    def __init__(
        self, message: str, user_message: str = None, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_type=MCPErrorType.NETWORK_ERROR,
            message=message,
            user_message=user_message or "Network error occurred",
            details=details,
            retryable=True,
            retry_after=3,
        )


class MCPTimeoutError(MCPError):
    """Request timeout error"""

    def __init__(
        self, message: str, user_message: str = None, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_type=MCPErrorType.TIMEOUT_ERROR,
            message=message,
            user_message=user_message or "Request timed out",
            details=details,
            retryable=True,
            retry_after=10,
        )


class MCPRateLimitError(MCPError):
    """Rate limit exceeded error"""

    def __init__(
        self,
        message: str,
        user_message: str = None,
        details: Optional[Dict[str, Any]] = None,
        retry_after: int = 60,
    ):
        super().__init__(
            error_type=MCPErrorType.RATE_LIMIT_ERROR,
            message=message,
            user_message=user_message or "Rate limit exceeded",
            details=details,
            retryable=True,
            retry_after=retry_after,
        )


class MCPAuthenticationError(MCPError):
    """Authentication error"""

    def __init__(
        self, message: str, user_message: str = None, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_type=MCPErrorType.AUTHENTICATION_ERROR,
            message=message,
            user_message=user_message or "Authentication failed",
            details=details,
            retryable=False,
        )


def get_http_status_code(error_type: MCPErrorType) -> int:
    """Map MCP error types to HTTP status codes"""
    status_mapping = {
        MCPErrorType.VALIDATION_ERROR: 400,
        MCPErrorType.TOOL_NOT_FOUND: 400,
        MCPErrorType.PARAMETER_ERROR: 400,
        MCPErrorType.SERVICE_ERROR: 500,
        MCPErrorType.DATABASE_ERROR: 503,
        MCPErrorType.NETWORK_ERROR: 503,
        MCPErrorType.TIMEOUT_ERROR: 504,
        MCPErrorType.RATE_LIMIT_ERROR: 429,
        MCPErrorType.AUTHENTICATION_ERROR: 401,
        MCPErrorType.INTERNAL_ERROR: 500,
    }
    return status_mapping.get(error_type, 500)


def classify_error(error: Exception) -> MCPError:
    """
    Classify generic exceptions into MCP error types

    Args:
        error: The exception to classify

    Returns:
        MCPError: Classified MCP error
    """
    error_message = str(error)
    error_lower = error_message.lower()

    # Network errors (check before database to avoid "connection" overlap)
    if any(
        keyword in error_lower
        for keyword in ["network", "connection refused", "host unreachable", "dns"]
    ):
        return MCPNetworkError(
            message=f"Network error: {error_message}",
            details={"original_error": error_message, "error_type": type(error).__name__},
        )

    # Database errors (check after network to avoid overlap)
    if any(
        keyword in error_lower
        for keyword in ["database", "connection", "supabase", "postgres", "sql"]
    ):
        return MCPDatabaseError(
            message=f"Database error: {error_message}",
            details={"original_error": error_message, "error_type": type(error).__name__},
        )

    # Timeout errors
    if any(keyword in error_lower for keyword in ["timeout", "timed out"]):
        return MCPTimeoutError(
            message=f"Timeout error: {error_message}",
            details={"original_error": error_message, "error_type": type(error).__name__},
        )

    # Rate limit errors
    if any(keyword in error_lower for keyword in ["rate limit", "quota", "too many requests"]):
        return MCPRateLimitError(
            message=f"Rate limit error: {error_message}",
            details={"original_error": error_message, "error_type": type(error).__name__},
        )

    # Authentication errors
    if any(keyword in error_lower for keyword in ["auth", "unauthorized", "forbidden", "api key"]):
        return MCPAuthenticationError(
            message=f"Authentication error: {error_message}",
            details={"original_error": error_message, "error_type": type(error).__name__},
        )

    # Default to service error
    return MCPServiceError(
        message=f"Service error: {error_message}",
        details={"original_error": error_message, "error_type": type(error).__name__},
    )


def get_user_friendly_message(error_type: MCPErrorType, details: Dict[str, Any] = None) -> str:
    """
    Get user-friendly error messages with recovery suggestions

    Args:
        error_type: The type of error
        details: Additional error details

    Returns:
        str: User-friendly error message
    """
    messages = {
        MCPErrorType.VALIDATION_ERROR: "Invalid request parameters. Please check your input and try again.",
        MCPErrorType.TOOL_NOT_FOUND: "The requested tool is not available. Please check the tool name.",
        MCPErrorType.PARAMETER_ERROR: "Invalid parameters provided. Please check the required parameters and try again.",
        MCPErrorType.SERVICE_ERROR: "Service temporarily unavailable. Please try again later.",
        MCPErrorType.DATABASE_ERROR: "Database temporarily unavailable. Please try again in a few moments.",
        MCPErrorType.NETWORK_ERROR: "Network connection issue. Please check your connection and try again.",
        MCPErrorType.TIMEOUT_ERROR: "Request timed out. Please try again with a smaller request.",
        MCPErrorType.RATE_LIMIT_ERROR: "Rate limit exceeded. Please wait and try again later.",
        MCPErrorType.AUTHENTICATION_ERROR: "Authentication failed. Please check your credentials.",
        MCPErrorType.INTERNAL_ERROR: "An unexpected error occurred. Please try again later.",
    }

    base_message = messages.get(error_type, "An error occurred. Please try again.")

    # Add specific recovery suggestions based on error details
    if error_type == MCPErrorType.RATE_LIMIT_ERROR and details and "retry_after" in details:
        base_message += f" Please wait {details['retry_after']} seconds before retrying."

    return base_message


def get_recovery_suggestions(error_type: MCPErrorType, details: Dict[str, Any] = None) -> List[str]:
    """
    Get specific recovery suggestions for different error types

    Args:
        error_type: The type of error
        details: Additional error details

    Returns:
        List[str]: List of recovery suggestions
    """
    suggestions = {
        MCPErrorType.VALIDATION_ERROR: [
            "Check the request format and ensure all required fields are provided",
            "Verify parameter types match the expected schema",
            "Review the API documentation for correct parameter formats",
        ],
        MCPErrorType.TOOL_NOT_FOUND: [
            "Use the /mcp/tools endpoint to get a list of available tools",
            "Check for typos in the tool name",
            "Ensure you're using the correct API version",
        ],
        MCPErrorType.PARAMETER_ERROR: [
            "Review the tool's parameter schema using /mcp/tools/{tool_name}",
            "Ensure all required parameters are provided",
            "Check parameter data types and formats",
        ],
        MCPErrorType.SERVICE_ERROR: [
            "Wait a few moments and retry the request",
            "Check the service status page for known issues",
            "Contact support if the issue persists",
        ],
        MCPErrorType.DATABASE_ERROR: [
            "Retry the request after a short delay",
            "Reduce the size of your request if possible",
            "Check if the issue persists and contact support",
        ],
        MCPErrorType.NETWORK_ERROR: [
            "Check your internet connection",
            "Verify firewall settings allow outbound connections",
            "Try the request again after a short delay",
        ],
        MCPErrorType.TIMEOUT_ERROR: [
            "Reduce the size or complexity of your request",
            "Break large requests into smaller chunks",
            "Retry with a longer timeout if possible",
        ],
        MCPErrorType.RATE_LIMIT_ERROR: [
            "Wait for the specified retry-after period",
            "Implement exponential backoff in your client",
            "Consider reducing request frequency",
        ],
        MCPErrorType.AUTHENTICATION_ERROR: [
            "Check your API credentials",
            "Ensure your API key is valid and not expired",
            "Verify you have permission to access this resource",
        ],
        MCPErrorType.INTERNAL_ERROR: [
            "Retry the request after a short delay",
            "Contact support with the error ID if the issue persists",
            "Check the service status page for known issues",
        ],
    }

    base_suggestions = suggestions.get(error_type, ["Contact support for assistance"])

    # Add context-specific suggestions
    if error_type == MCPErrorType.PARAMETER_ERROR and details:
        if "node_names" in details:
            base_suggestions.append("Ensure node_names is a non-empty array of strings")
        if "validation_error" in details:
            base_suggestions.append(f"Fix validation error: {details['validation_error']}")

    return base_suggestions


def get_support_info(error_type: MCPErrorType) -> Dict[str, str]:
    """
    Get support contact information based on error type

    Args:
        error_type: The type of error

    Returns:
        Dict[str, str]: Support contact information
    """
    if error_type in [MCPErrorType.INTERNAL_ERROR, MCPErrorType.SERVICE_ERROR]:
        return {
            "contact": "support@example.com",
            "documentation": "https://docs.example.com/mcp-api",
            "status_page": "https://status.example.com",
        }
    elif error_type == MCPErrorType.AUTHENTICATION_ERROR:
        return {
            "contact": "auth-support@example.com",
            "documentation": "https://docs.example.com/authentication",
        }
    else:
        return {
            "documentation": "https://docs.example.com/mcp-api",
            "troubleshooting": "https://docs.example.com/troubleshooting",
        }
