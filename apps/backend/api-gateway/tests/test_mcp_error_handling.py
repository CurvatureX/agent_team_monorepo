"""
Comprehensive tests for MCP error handling and logging
"""

import time
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ..core.mcp_exceptions import (
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
    get_user_friendly_message,
)
from ..models.mcp_models import MCPErrorResponse
from ..routers.mcp import router
from ..services.mcp_service import MCPService


class TestMCPErrorClassification:
    """Test error classification functionality"""

    def test_classify_database_error(self):
        """Test classification of database errors"""
        db_error = Exception("Database connection failed")
        classified = classify_error(db_error)

        assert isinstance(classified, MCPDatabaseError)
        assert classified.error_type == MCPErrorType.DATABASE_ERROR
        assert classified.retryable is True
        assert classified.retry_after == 5

    def test_classify_network_error(self):
        """Test classification of network errors"""
        network_error = Exception("Network connection refused")
        classified = classify_error(network_error)

        assert isinstance(classified, MCPNetworkError)
        assert classified.error_type == MCPErrorType.NETWORK_ERROR
        assert classified.retryable is True

    def test_classify_timeout_error(self):
        """Test classification of timeout errors"""
        timeout_error = Exception("Request timed out")
        classified = classify_error(timeout_error)

        assert isinstance(classified, MCPTimeoutError)
        assert classified.error_type == MCPErrorType.TIMEOUT_ERROR
        assert classified.retryable is True

    def test_classify_rate_limit_error(self):
        """Test classification of rate limit errors"""
        rate_error = Exception("Rate limit exceeded")
        classified = classify_error(rate_error)

        assert isinstance(classified, MCPRateLimitError)
        assert classified.error_type == MCPErrorType.RATE_LIMIT_ERROR
        assert classified.retryable is True

    def test_classify_auth_error(self):
        """Test classification of authentication errors"""
        auth_error = Exception("Unauthorized access")
        classified = classify_error(auth_error)

        assert isinstance(classified, MCPAuthenticationError)
        assert classified.error_type == MCPErrorType.AUTHENTICATION_ERROR
        assert classified.retryable is False

    def test_classify_generic_error(self):
        """Test classification of generic errors"""
        generic_error = Exception("Something went wrong")
        classified = classify_error(generic_error)

        assert isinstance(classified, MCPServiceError)
        assert classified.error_type == MCPErrorType.SERVICE_ERROR


class TestMCPErrorMessages:
    """Test user-friendly error messages"""

    def test_validation_error_message(self):
        """Test validation error message"""
        message = get_user_friendly_message(MCPErrorType.VALIDATION_ERROR)
        assert "Invalid request parameters" in message
        assert "check your input" in message

    def test_tool_not_found_message(self):
        """Test tool not found error message"""
        message = get_user_friendly_message(MCPErrorType.TOOL_NOT_FOUND)
        assert "tool is not available" in message
        assert "check the tool name" in message

    def test_rate_limit_message_with_retry_after(self):
        """Test rate limit message with retry after"""
        message = get_user_friendly_message(MCPErrorType.RATE_LIMIT_ERROR, {"retry_after": 60})
        assert "Rate limit exceeded" in message
        assert "60 seconds" in message

    def test_database_error_message(self):
        """Test database error message"""
        message = get_user_friendly_message(MCPErrorType.DATABASE_ERROR)
        assert "Database temporarily unavailable" in message
        assert "try again" in message


class TestMCPErrorHTTPStatusCodes:
    """Test HTTP status code mapping"""

    def test_validation_error_status(self):
        """Test validation error returns 400"""
        assert get_http_status_code(MCPErrorType.VALIDATION_ERROR) == 400

    def test_tool_not_found_status(self):
        """Test tool not found returns 400"""
        assert get_http_status_code(MCPErrorType.TOOL_NOT_FOUND) == 400

    def test_database_error_status(self):
        """Test database error returns 503"""
        assert get_http_status_code(MCPErrorType.DATABASE_ERROR) == 503

    def test_timeout_error_status(self):
        """Test timeout error returns 504"""
        assert get_http_status_code(MCPErrorType.TIMEOUT_ERROR) == 504

    def test_rate_limit_error_status(self):
        """Test rate limit error returns 429"""
        assert get_http_status_code(MCPErrorType.RATE_LIMIT_ERROR) == 429

    def test_auth_error_status(self):
        """Test auth error returns 401"""
        assert get_http_status_code(MCPErrorType.AUTHENTICATION_ERROR) == 401

    def test_internal_error_status(self):
        """Test internal error returns 500"""
        assert get_http_status_code(MCPErrorType.INTERNAL_ERROR) == 500


class TestMCPErrorObject:
    """Test MCP error object functionality"""

    def test_error_object_creation(self):
        """Test MCP error object creation"""
        error = MCPError(
            error_type=MCPErrorType.VALIDATION_ERROR,
            message="Test error",
            user_message="User friendly message",
            details={"key": "value"},
            retryable=True,
            retry_after=30,
        )

        assert error.error_type == MCPErrorType.VALIDATION_ERROR
        assert error.message == "Test error"
        assert error.user_message == "User friendly message"
        assert error.details == {"key": "value"}
        assert error.retryable is True
        assert error.retry_after == 30
        assert error.error_id is not None
        assert error.timestamp is not None

    def test_error_to_dict(self):
        """Test error to dictionary conversion"""
        error = MCPError(
            error_type=MCPErrorType.SERVICE_ERROR,
            message="Service error",
            user_message="Service unavailable",
        )

        error_dict = error.to_dict()

        assert error_dict["error_type"] == "SERVICE_ERROR"
        assert error_dict["message"] == "Service error"
        assert error_dict["user_message"] == "Service unavailable"
        assert "error_id" in error_dict
        assert "timestamp" in error_dict


class TestMCPServiceErrorHandling:
    """Test MCP service error handling"""

    @pytest.fixture
    def mock_node_client(self):
        """Mock node knowledge client"""
        with patch(
            "apps.backend.api_gateway.services.mcp_service.NodeKnowledgeClient"
        ) as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance
            return mock_instance

    @pytest.fixture
    def service(self, mock_node_client):
        """Create MCPService with mocked dependencies"""
        return MCPService()

    @pytest.mark.asyncio
    async def test_invoke_tool_database_error(self, service, mock_node_client):
        """Test tool invocation with database error"""
        mock_node_client.retrieve_node_knowledge = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        with pytest.raises(MCPDatabaseError) as exc_info:
            await service.invoke_tool("node_knowledge_retriever", {"node_names": ["test_node"]})

        assert exc_info.value.error_type == MCPErrorType.DATABASE_ERROR
        assert exc_info.value.retryable is True

    @pytest.mark.asyncio
    async def test_invoke_tool_network_error(self, service, mock_node_client):
        """Test tool invocation with network error"""
        mock_node_client.retrieve_node_knowledge = AsyncMock(
            side_effect=Exception("Network connection refused")
        )

        with pytest.raises(MCPNetworkError) as exc_info:
            await service.invoke_tool("node_knowledge_retriever", {"node_names": ["test_node"]})

        assert exc_info.value.error_type == MCPErrorType.NETWORK_ERROR
        assert exc_info.value.retryable is True

    @pytest.mark.asyncio
    async def test_invoke_tool_timeout_error(self, service, mock_node_client):
        """Test tool invocation with timeout error"""
        mock_node_client.retrieve_node_knowledge = AsyncMock(
            side_effect=Exception("Request timed out")
        )

        with pytest.raises(MCPTimeoutError) as exc_info:
            await service.invoke_tool("node_knowledge_retriever", {"node_names": ["test_node"]})

        assert exc_info.value.error_type == MCPErrorType.TIMEOUT_ERROR
        assert exc_info.value.retryable is True

    @pytest.mark.asyncio
    async def test_invoke_tool_invalid_node_names_type(self, service):
        """Test tool invocation with invalid node_names type"""
        with pytest.raises(MCPParameterError) as exc_info:
            await service.invoke_tool("node_knowledge_retriever", {"node_names": "not_a_list"})

        assert "must be a list" in exc_info.value.message
        assert exc_info.value.error_type == MCPErrorType.PARAMETER_ERROR

    @pytest.mark.asyncio
    async def test_invoke_tool_empty_node_names(self, service):
        """Test tool invocation with empty node names"""
        with pytest.raises(MCPParameterError) as exc_info:
            await service.invoke_tool("node_knowledge_retriever", {"node_names": ["", "  ", None]})

        assert "non-empty strings" in exc_info.value.message
        assert exc_info.value.error_type == MCPErrorType.PARAMETER_ERROR

    def test_get_available_tools_empty_registry(self, mock_node_client):
        """Test get available tools with empty registry"""
        with patch.object(MCPService, "__init__", lambda x: None):
            service = MCPService()
            service.tool_registry = {}

            with pytest.raises(MCPServiceError) as exc_info:
                service.get_available_tools()

            assert "empty or not initialized" in exc_info.value.message

    def test_get_available_tools_corrupted_registry(self, mock_node_client):
        """Test get available tools with corrupted registry"""
        with patch.object(MCPService, "__init__", lambda x: None):
            service = MCPService()
            service.tool_registry = {"invalid_tool": {"name": "test"}}  # Missing required fields

            with pytest.raises(MCPServiceError) as exc_info:
                service.get_available_tools()

            assert "No valid tools available" in exc_info.value.message


class TestMCPRouterErrorHandling:
    """Test MCP router error handling"""

    @pytest.fixture
    def app(self):
        """Create test FastAPI app"""
        app = FastAPI()
        app.include_router(router, prefix="/mcp")
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return TestClient(app)

    def test_list_tools_error_response_format(self, client):
        """Test that error responses have correct format"""
        with patch("apps.backend.api_gateway.routers.mcp.mcp_service") as mock_service:
            mock_service.get_available_tools.side_effect = MCPServiceError(
                message="Service error", user_message="Service unavailable"
            )

            response = client.get("/mcp/tools")

            assert response.status_code == 500
            data = response.json()

            assert data["success"] is False
            assert data["error"] == "Service unavailable"
            assert data["error_type"] == "SERVICE_ERROR"
            assert "error_id" in data["details"]

    def test_invoke_tool_validation_error_response(self, client):
        """Test invoke tool validation error response"""
        response = client.post(
            "/mcp/invoke",
            json={
                "tool_name": "node_knowledge_retriever",
                "params": {},  # Missing required node_names
            },
        )

        assert response.status_code == 400
        data = response.json()

        assert data["success"] is False
        assert data["error_type"] == "VALIDATION_ERROR"
        assert "error_id" in data["details"]

    def test_invoke_tool_not_found_error_response(self, client):
        """Test invoke tool not found error response"""
        response = client.post(
            "/mcp/invoke", json={"tool_name": "nonexistent_tool", "params": {"test": "value"}}
        )

        assert response.status_code == 400
        data = response.json()

        assert data["success"] is False
        assert data["error"] == "unknown tool"
        assert data["error_type"] == "TOOL_NOT_FOUND"

    def test_rate_limit_error_headers(self, client):
        """Test that rate limit errors include retry-after header"""
        with patch("apps.backend.api_gateway.routers.mcp.mcp_service") as mock_service:
            mock_service.invoke_tool.side_effect = MCPRateLimitError(
                message="Rate limit exceeded", retry_after=60
            )

            response = client.post(
                "/mcp/invoke",
                json={"tool_name": "node_knowledge_retriever", "params": {"node_names": ["test"]}},
            )

            assert response.status_code == 429
            assert response.headers.get("Retry-After") == "60"

    def test_health_check_error_response(self, client):
        """Test health check error response"""
        with patch("apps.backend.api_gateway.routers.mcp.mcp_service") as mock_service:
            mock_service.health_check.side_effect = Exception("Health check failed")

            response = client.get("/mcp/health")

            assert response.status_code == 500
            data = response.json()

            assert data["healthy"] is False
            assert "error_id" in data
            assert "processing_time_ms" in data


class TestMCPLoggingIntegration:
    """Test logging integration with error handling"""

    @pytest.mark.asyncio
    async def test_error_logging_includes_context(self):
        """Test that errors are logged with proper context"""
        with patch("apps.backend.api_gateway.services.mcp_service.logger") as mock_logger:
            with patch(
                "apps.backend.api_gateway.services.mcp_service.NodeKnowledgeClient"
            ) as mock_client_class:
                mock_client = Mock()
                mock_client.retrieve_node_knowledge = AsyncMock(
                    side_effect=Exception("Database error")
                )
                mock_client_class.return_value = mock_client

                service = MCPService()

                with pytest.raises(MCPDatabaseError):
                    await service.invoke_tool(
                        "node_knowledge_retriever", {"node_names": ["test_node"]}
                    )

                # Verify error was logged with context
                mock_logger.error.assert_called()
                call_args = mock_logger.error.call_args

                assert "Node knowledge retrieval failed" in call_args[0]
                assert "node_names" in call_args[1]
                assert "error" in call_args[1]
                assert "processing_time_ms" in call_args[1]

    def test_performance_logging(self):
        """Test that performance metrics are logged"""
        with patch("apps.backend.api_gateway.services.mcp_service.logger") as mock_logger:
            service = MCPService()

            # Call get_available_tools which should log performance
            service.get_available_tools()

            # Verify performance was logged
            mock_logger.info.assert_called()
            call_args = mock_logger.info.call_args

            assert "processing_time_ms" in call_args[1]
            assert "tool_count" in call_args[1]


if __name__ == "__main__":
    pytest.main([__file__])
