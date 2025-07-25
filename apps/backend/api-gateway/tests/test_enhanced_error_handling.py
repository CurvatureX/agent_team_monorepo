"""
Enhanced tests for comprehensive MCP error handling and logging
"""

import json
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.mcp_exceptions import (
    MCPAuthenticationError,
    MCPDatabaseError,
    MCPError,
    MCPErrorType,
    MCPNetworkError,
    MCPParameterError,
    MCPRateLimitError,
    MCPServiceError,
    MCPTimeoutError,
    MCPToolNotFoundError,
    MCPValidationError,
    classify_error,
    get_http_status_code,
    get_recovery_suggestions,
    get_support_info,
    get_user_friendly_message,
)
from models.mcp_models import MCPErrorResponse


class TestEnhancedErrorHandling:
    """Test enhanced error handling features"""

    def test_recovery_suggestions_validation_error(self):
        """Test recovery suggestions for validation errors"""
        suggestions = get_recovery_suggestions(MCPErrorType.VALIDATION_ERROR)

        assert len(suggestions) >= 3
        assert any("required fields" in s for s in suggestions)
        assert any("parameter types" in s for s in suggestions)
        assert any("documentation" in s for s in suggestions)

    def test_recovery_suggestions_tool_not_found(self):
        """Test recovery suggestions for tool not found errors"""
        suggestions = get_recovery_suggestions(MCPErrorType.TOOL_NOT_FOUND)

        assert len(suggestions) >= 3
        assert any("/mcp/tools" in s for s in suggestions)
        assert any("typos" in s for s in suggestions)
        assert any("API version" in s for s in suggestions)

    def test_recovery_suggestions_parameter_error_with_context(self):
        """Test recovery suggestions with context-specific details"""
        details = {"node_names": ["invalid"], "validation_error": "must be non-empty"}
        suggestions = get_recovery_suggestions(MCPErrorType.PARAMETER_ERROR, details)

        assert len(suggestions) >= 4  # Base suggestions + context-specific
        assert any("node_names" in s for s in suggestions)
        assert any("non-empty" in s for s in suggestions)

    def test_recovery_suggestions_rate_limit(self):
        """Test recovery suggestions for rate limit errors"""
        suggestions = get_recovery_suggestions(MCPErrorType.RATE_LIMIT_ERROR)

        assert any("retry-after" in s for s in suggestions)
        assert any("exponential backoff" in s for s in suggestions)
        assert any("request frequency" in s for s in suggestions)

    def test_support_info_internal_error(self):
        """Test support info for internal errors"""
        support_info = get_support_info(MCPErrorType.INTERNAL_ERROR)

        assert "contact" in support_info
        assert "documentation" in support_info
        assert "status_page" in support_info
        assert "@example.com" in support_info["contact"]

    def test_support_info_authentication_error(self):
        """Test support info for authentication errors"""
        support_info = get_support_info(MCPErrorType.AUTHENTICATION_ERROR)

        assert "contact" in support_info
        assert "documentation" in support_info
        assert "auth-support@example.com" in support_info["contact"]

    def test_support_info_generic_error(self):
        """Test support info for generic errors"""
        support_info = get_support_info(MCPErrorType.VALIDATION_ERROR)

        assert "documentation" in support_info
        assert "troubleshooting" in support_info

    def test_enhanced_error_response_model(self):
        """Test enhanced error response model with all fields"""
        error_response = MCPErrorResponse(
            error="Test error message",
            error_type="VALIDATION_ERROR",
            details={"key": "value"},
            error_id="test-error-id",
            request_id="test-request-id",
            retryable=True,
            retry_after=30,
            timestamp=time.time(),
            recovery_suggestions=["suggestion1", "suggestion2"],
            support_info={"contact": "support@example.com"},
        )

        assert error_response.success is False
        assert error_response.error == "Test error message"
        assert error_response.error_type == "VALIDATION_ERROR"
        assert error_response.retryable is True
        assert error_response.retry_after == 30
        assert len(error_response.recovery_suggestions) == 2
        assert error_response.support_info["contact"] == "support@example.com"

    def test_error_response_serialization(self):
        """Test error response serialization includes all fields"""
        error_response = MCPErrorResponse(
            error="Test error",
            error_type="SERVICE_ERROR",
            recovery_suggestions=["Try again later"],
            support_info={"documentation": "https://docs.example.com"},
        )

        response_dict = error_response.model_dump()

        assert "success" in response_dict
        assert "error" in response_dict
        assert "error_type" in response_dict
        assert "recovery_suggestions" in response_dict
        assert "support_info" in response_dict
        assert response_dict["recovery_suggestions"] == ["Try again later"]


class TestErrorClassificationEnhancements:
    """Test enhanced error classification"""

    def test_classify_supabase_error(self):
        """Test classification of Supabase-specific errors"""
        supabase_error = Exception("Supabase connection timeout")
        classified = classify_error(supabase_error)

        assert isinstance(classified, MCPDatabaseError)
        assert classified.error_type == MCPErrorType.DATABASE_ERROR
        assert classified.retryable is True

    def test_classify_postgres_error(self):
        """Test classification of PostgreSQL errors"""
        postgres_error = Exception("PostgreSQL: connection refused")
        classified = classify_error(postgres_error)

        # Connection refused should be classified as network error, not database error
        assert isinstance(classified, MCPNetworkError)
        assert classified.error_type == MCPErrorType.NETWORK_ERROR

    def test_classify_dns_error(self):
        """Test classification of DNS errors"""
        dns_error = Exception("DNS resolution failed")
        classified = classify_error(dns_error)

        assert isinstance(classified, MCPNetworkError)
        assert classified.error_type == MCPErrorType.NETWORK_ERROR

    def test_classify_quota_error(self):
        """Test classification of quota/rate limit errors"""
        quota_error = Exception("API quota exceeded")
        classified = classify_error(quota_error)

        assert isinstance(classified, MCPRateLimitError)
        assert classified.error_type == MCPErrorType.RATE_LIMIT_ERROR

    def test_classify_api_key_error(self):
        """Test classification of API key errors"""
        api_key_error = Exception("Invalid API key provided")
        classified = classify_error(api_key_error)

        assert isinstance(classified, MCPAuthenticationError)
        assert classified.error_type == MCPErrorType.AUTHENTICATION_ERROR


class TestLoggingEnhancements:
    """Test enhanced logging functionality"""

    @pytest.mark.asyncio
    async def test_request_logging_includes_mcp_context(self):
        """Test that MCP requests are properly categorized in logs"""
        from core.logging_middleware import MCPLoggingMiddleware

        # Mock request
        mock_request = Mock()
        mock_request.method = "POST"
        mock_request.url = Mock()
        mock_request.url.path = "/mcp/invoke"
        mock_request.url.__str__ = Mock(return_value="http://test.com/mcp/invoke")
        mock_request.query_params = {}
        mock_request.headers = Mock()
        mock_request.headers.get = Mock(side_effect=lambda k, default=None: {"content-type": "application/json"}.get(k, default))
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"
        mock_request.body = AsyncMock(return_value=b'{"tool_name": "test"}')
        mock_request.state = Mock()

        middleware = MCPLoggingMiddleware(Mock())

        with patch("core.logging_middleware.logger") as mock_logger:
            await middleware._log_request(mock_request, "test-request-id")

            # Verify MCP context was logged
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args[1]

            assert call_args["is_mcp_request"] is True
            assert call_args["endpoint_category"] == "mcp"
            assert call_args["path"] == "/mcp/invoke"

    @pytest.mark.asyncio
    async def test_response_logging_includes_performance_category(self):
        """Test that response logging includes performance categorization"""
        from core.logging_middleware import MCPLoggingMiddleware

        # Mock request and response
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url = Mock()
        mock_request.url.path = "/mcp/tools"
        mock_request.url.__str__ = Mock(return_value="http://test.com/mcp/tools")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.body = b'{"tools": []}'

        middleware = MCPLoggingMiddleware(Mock())

        with patch("core.logging_middleware.logger") as mock_logger:
            # Test slow response (> 2 seconds)
            await middleware._log_response(mock_request, mock_response, "test-id", 3.5)

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args[1]

            assert call_args["performance_category"] == "slow"
            assert call_args["processing_time_ms"] == 3500.0
            assert call_args["success"] is True

    def test_error_logging_context_preservation(self):
        """Test that error context is preserved in logging"""
        error = MCPParameterError(
            message="Invalid node_names parameter",
            user_message="node_names is required",
            details={"provided_params": {"node_names": []}, "tool_name": "test_tool"},
        )

        error_dict = error.to_dict()

        assert error_dict["error_type"] == "PARAMETER_ERROR"
        assert error_dict["details"]["provided_params"]["node_names"] == []
        assert error_dict["details"]["tool_name"] == "test_tool"
        assert "error_id" in error_dict
        assert "timestamp" in error_dict


class TestIntegrationScenarios:
    """Test integration scenarios for error handling"""

    def test_complete_error_flow_validation(self):
        """Test complete error flow from validation to response"""
        # Create a validation error
        error = MCPValidationError(
            message="Missing required parameter",
            user_message="node_names is required",
            details={"missing_param": "node_names"},
        )

        # Get HTTP status code
        status_code = get_http_status_code(error.error_type)
        assert status_code == 400

        # Get user-friendly message
        user_message = get_user_friendly_message(error.error_type)
        assert "Invalid request parameters" in user_message

        # Get recovery suggestions
        suggestions = get_recovery_suggestions(error.error_type, error.details)
        assert len(suggestions) >= 3

        # Get support info
        support_info = get_support_info(error.error_type)
        assert "documentation" in support_info

        # Create error response
        error_response = MCPErrorResponse(
            error=error.user_message,
            error_type=error.error_type.value,
            details=error.details,
            error_id=error.error_id,
            recovery_suggestions=suggestions,
            support_info=support_info,
        )

        assert error_response.success is False
        assert error_response.error_type == "VALIDATION_ERROR"
        assert len(error_response.recovery_suggestions) >= 3

    def test_complete_error_flow_database(self):
        """Test complete error flow for database errors"""
        # Simulate database error
        db_exception = Exception("Database connection failed")
        classified_error = classify_error(db_exception)

        assert isinstance(classified_error, MCPDatabaseError)
        assert classified_error.retryable is True
        assert classified_error.retry_after == 5

        # Test HTTP status mapping
        status_code = get_http_status_code(classified_error.error_type)
        assert status_code == 503

        # Test recovery suggestions
        suggestions = get_recovery_suggestions(classified_error.error_type)
        assert any("retry" in s.lower() for s in suggestions)
        assert any("delay" in s.lower() for s in suggestions)

    def test_rate_limit_error_with_retry_after(self):
        """Test rate limit error with retry-after handling"""
        error = MCPRateLimitError(
            message="Rate limit exceeded", user_message="Too many requests", retry_after=120
        )

        # Test that retry_after is properly set
        assert error.retry_after == 120
        assert error.retryable is True

        # Test HTTP status code
        status_code = get_http_status_code(error.error_type)
        assert status_code == 429

        # Test user message includes retry time
        user_message = get_user_friendly_message(
            error.error_type, {"retry_after": error.retry_after}
        )
        assert "120 seconds" in user_message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
