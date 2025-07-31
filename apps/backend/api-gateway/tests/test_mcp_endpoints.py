"""
Integration tests for MCP API endpoints
Tests the full HTTP API layer for MCP tools
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
from app.main import create_application
from shared.models import MCPHealthCheck, MCPInvokeResponse, MCPTool, MCPToolsResponse
from fastapi.testclient import TestClient


class TestMCPEndpoints:
    """Test suite for MCP API endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        app = create_application()
        return TestClient(app)

    @pytest.fixture
    def mock_mcp_client(self):
        """Mock MCP client for authentication"""
        client = Mock()
        client.client_name = "test_client"
        client.scopes = ["tools:read", "tools:execute", "health:check"]
        return client

    @pytest.fixture
    def mock_deps(self, mock_mcp_client):
        """Mock MCP dependencies"""
        deps = Mock()
        deps.mcp_client = mock_mcp_client
        deps.request_context = {"request_id": "test-request-123"}
        return deps

    @pytest.fixture
    def auth_headers(self):
        """Valid API key headers for testing"""
        return {"X-API-Key": "dev_default"}

    def test_mcp_tools_endpoint_without_auth(self, client):
        """Test MCP tools endpoint requires authentication"""
        response = client.get("/api/v1/mcp/tools")
        assert response.status_code == 401

    @patch("app.api.mcp.tools.mcp_service")
    @patch("app.dependencies.get_mcp_client")
    @patch("app.dependencies.require_scope")
    def test_mcp_tools_endpoint_success(
        self, mock_require_scope, mock_get_mcp_client, mock_service, client, mock_deps, auth_headers
    ):
        """Test successful MCP tools listing"""
        # Mock authentication
        mock_get_mcp_client.return_value = mock_deps
        mock_require_scope.return_value = None

        # Mock service response
        mock_tools_response = MCPToolsResponse(
            success=True,
            tools=[
                MCPTool(
                    name="get_node_types",
                    description="Get node types",
                    category="workflow",
                    tags=["nodes"],
                ),
                MCPTool(
                    name="get_node_details",
                    description="Get node details",
                    category="workflow",
                    tags=["specs"],
                ),
                MCPTool(
                    name="search_nodes",
                    description="Search nodes",
                    category="workflow",
                    tags=["search"],
                ),
            ],
            total_count=3,
            available_count=3,
            categories=["workflow"],
            timestamp=datetime.now(timezone.utc),
            processing_time_ms=10.5,
            request_id="test-request-123",
        )
        mock_service.get_available_tools.return_value = mock_tools_response

        response = client.get("/api/v1/mcp/tools", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["tools"]) == 3
        assert data["total_count"] == 3
        assert "processing_time_ms" in data
        assert "request_id" in data

    @patch("app.api.mcp.tools.mcp_service")
    @patch("app.dependencies.get_mcp_client")
    @patch("app.dependencies.require_scope")
    def test_mcp_tools_endpoint_service_error(
        self, mock_require_scope, mock_get_mcp_client, mock_service, client, mock_deps, auth_headers
    ):
        """Test MCP tools endpoint with service error"""
        # Mock authentication
        mock_get_mcp_client.return_value = mock_deps
        mock_require_scope.return_value = None

        # Mock service error
        mock_service.get_available_tools.side_effect = Exception("Service error")

        response = client.get("/api/v1/mcp/tools", headers=auth_headers)

        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "Failed to retrieve tools" in data["error"]

    def test_mcp_invoke_endpoint_without_auth(self, client):
        """Test MCP invoke endpoint requires authentication"""
        payload = {"tool_name": "get_node_types", "parameters": {}}
        response = client.post("/api/v1/mcp/invoke", json=payload)
        assert response.status_code == 401

    @patch("app.api.mcp.tools.mcp_service")
    @patch("app.dependencies.get_mcp_client")
    @patch("app.dependencies.require_scope")
    def test_mcp_invoke_get_node_types_success(
        self, mock_require_scope, mock_get_mcp_client, mock_service, client, mock_deps, auth_headers
    ):
        """Test successful get_node_types invocation"""
        # Mock authentication
        mock_get_mcp_client.return_value = mock_deps
        mock_require_scope.return_value = None

        # Mock service response
        mock_result = MCPInvokeResponse(
            success=True,
            tool_name="get_node_types",
            result={
                "ACTION_NODE": ["HTTP_REQUEST", "RUN_CODE"],
                "AI_AGENT_NODE": ["OPENAI_NODE", "CLAUDE_NODE"],
            },
            execution_time_ms=15.5,
            timestamp=datetime.now(timezone.utc),
            request_id="test-request-123",
        )
        mock_service.invoke_tool = AsyncMock(return_value=mock_result)

        payload = {"tool_name": "get_node_types", "parameters": {}}

        response = client.post("/api/v1/mcp/invoke", json=payload, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["tool_name"] == "get_node_types"
        assert "ACTION_NODE" in data["result"]
        assert data["execution_time_ms"] == 15.5
        assert "request_id" in data

    @patch("app.api.mcp.tools.mcp_service")
    @patch("app.dependencies.get_mcp_client")
    @patch("app.dependencies.require_scope")
    def test_mcp_invoke_get_node_details_success(
        self, mock_require_scope, mock_get_mcp_client, mock_service, client, mock_deps, auth_headers
    ):
        """Test successful get_node_details invocation"""
        # Mock authentication
        mock_get_mcp_client.return_value = mock_deps
        mock_require_scope.return_value = None

        # Mock service response
        mock_result = MCPInvokeResponse(
            success=True,
            tool_name="get_node_details",
            result=[
                {
                    "node_type": "ACTION_NODE",
                    "subtype": "HTTP_REQUEST",
                    "description": "Make HTTP requests to external APIs",
                    "parameters": [{"name": "url", "type": "string", "required": True}],
                    "input_ports": [],
                    "output_ports": [],
                }
            ],
            execution_time_ms=25.3,
            timestamp=datetime.now(timezone.utc),
            request_id="test-request-123",
        )
        mock_service.invoke_tool = AsyncMock(return_value=mock_result)

        payload = {
            "tool_name": "get_node_details",
            "parameters": {
                "nodes": [{"node_type": "ACTION_NODE", "subtype": "HTTP_REQUEST"}],
                "include_examples": True,
            },
        }

        response = client.post("/api/v1/mcp/invoke", json=payload, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["tool_name"] == "get_node_details"
        assert len(data["result"]) == 1
        assert data["result"][0]["node_type"] == "ACTION_NODE"

    @patch("app.api.mcp.tools.mcp_service")
    @patch("app.dependencies.get_mcp_client")
    @patch("app.dependencies.require_scope")
    def test_mcp_invoke_search_nodes_success(
        self, mock_require_scope, mock_get_mcp_client, mock_service, client, mock_deps, auth_headers
    ):
        """Test successful search_nodes invocation"""
        # Mock authentication
        mock_get_mcp_client.return_value = mock_deps
        mock_require_scope.return_value = None

        # Mock service response
        mock_result = MCPInvokeResponse(
            success=True,
            tool_name="search_nodes",
            result=[
                {
                    "node_type": "ACTION_NODE",
                    "subtype": "HTTP_REQUEST",
                    "description": "Make HTTP requests",
                    "relevance_score": 15,
                }
            ],
            execution_time_ms=12.7,
            timestamp=datetime.now(timezone.utc),
            request_id="test-request-123",
        )
        mock_service.invoke_tool = AsyncMock(return_value=mock_result)

        payload = {
            "tool_name": "search_nodes",
            "parameters": {"query": "HTTP request", "max_results": 5},
        }

        response = client.post("/api/v1/mcp/invoke", json=payload, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["tool_name"] == "search_nodes"
        assert len(data["result"]) == 1
        assert data["result"][0]["relevance_score"] == 15

    @patch("app.api.mcp.tools.mcp_service")
    @patch("app.dependencies.get_mcp_client")
    @patch("app.dependencies.require_scope")
    def test_mcp_invoke_invalid_tool(
        self, mock_require_scope, mock_get_mcp_client, mock_service, client, mock_deps, auth_headers
    ):
        """Test invocation of invalid tool"""
        # Mock authentication
        mock_get_mcp_client.return_value = mock_deps
        mock_require_scope.return_value = None

        # Mock service response for invalid tool
        mock_result = MCPInvokeResponse(
            success=False,
            tool_name="invalid_tool",
            error="Tool 'invalid_tool' not found",
            error_type="TOOL_NOT_FOUND",
            execution_time_ms=1.2,
            timestamp=datetime.now(timezone.utc),
            request_id="test-request-123",
        )
        mock_service.invoke_tool = AsyncMock(return_value=mock_result)

        payload = {"tool_name": "invalid_tool", "parameters": {}}

        response = client.post("/api/v1/mcp/invoke", json=payload, headers=auth_headers)

        assert response.status_code == 200  # Service returns error in response, not HTTP error
        data = response.json()
        assert data["success"] is False
        assert data["error"] == "Tool 'invalid_tool' not found"
        assert data["error_type"] == "TOOL_NOT_FOUND"

    @patch("app.api.mcp.tools.mcp_service")
    @patch("app.dependencies.get_mcp_client")
    @patch("app.dependencies.require_scope")
    def test_mcp_invoke_timeout_validation(
        self, mock_require_scope, mock_get_mcp_client, mock_service, client, mock_deps, auth_headers
    ):
        """Test timeout parameter validation"""
        # Mock authentication
        mock_get_mcp_client.return_value = mock_deps
        mock_require_scope.return_value = None

        # Test invalid timeout (too low)
        payload = {"tool_name": "get_node_types", "parameters": {}, "timeout": 0}

        response = client.post("/api/v1/mcp/invoke", json=payload, headers=auth_headers)
        assert response.status_code == 400  # ValidationError

        # Test invalid timeout (too high)
        payload["timeout"] = 500

        response = client.post("/api/v1/mcp/invoke", json=payload, headers=auth_headers)
        assert response.status_code == 400  # ValidationError

    @patch("app.api.mcp.tools.mcp_service")
    @patch("app.dependencies.get_mcp_client")
    @patch("app.dependencies.require_scope")
    def test_mcp_invoke_service_exception(
        self, mock_require_scope, mock_get_mcp_client, mock_service, client, mock_deps, auth_headers
    ):
        """Test MCP invoke with service exception"""
        # Mock authentication
        mock_get_mcp_client.return_value = mock_deps
        mock_require_scope.return_value = None

        # Mock service exception
        mock_service.invoke_tool = AsyncMock(side_effect=Exception("Service error"))

        payload = {"tool_name": "get_node_types", "parameters": {}}

        response = client.post("/api/v1/mcp/invoke", json=payload, headers=auth_headers)

        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "Tool invocation failed" in data["error"]

    def test_mcp_tool_info_endpoint_without_auth(self, client):
        """Test MCP tool info endpoint requires authentication"""
        response = client.get("/api/v1/mcp/tools/get_node_types")
        assert response.status_code == 401

    @patch("app.api.mcp.tools.mcp_service")
    @patch("app.dependencies.get_mcp_client")
    @patch("app.dependencies.require_scope")
    def test_mcp_tool_info_success(
        self, mock_require_scope, mock_get_mcp_client, mock_service, client, mock_deps, auth_headers
    ):
        """Test successful tool info retrieval"""
        # Mock authentication
        mock_get_mcp_client.return_value = mock_deps
        mock_require_scope.return_value = None

        # Mock service response
        mock_service.get_tool_info.return_value = {
            "name": "get_node_types",
            "description": "Get all available workflow node types",
            "version": "1.0.0",
            "available": True,
            "category": "workflow",
            "usage_examples": [{}],
        }

        response = client.get("/api/v1/mcp/tools/get_node_types", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "get_node_types"
        assert data["available"] is True
        assert "processing_time_ms" in data
        assert "request_id" in data

    @patch("app.api.mcp.tools.mcp_service")
    @patch("app.dependencies.get_mcp_client")
    @patch("app.dependencies.require_scope")
    def test_mcp_tool_info_not_found(
        self, mock_require_scope, mock_get_mcp_client, mock_service, client, mock_deps, auth_headers
    ):
        """Test tool info for non-existent tool"""
        # Mock authentication
        mock_get_mcp_client.return_value = mock_deps
        mock_require_scope.return_value = None

        # Mock service response for non-existent tool
        mock_service.get_tool_info.return_value = {
            "name": "invalid_tool",
            "description": "Tool 'invalid_tool' not found",
            "available": False,
            "error": "Tool not found",
        }

        response = client.get("/api/v1/mcp/tools/invalid_tool", headers=auth_headers)

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "Tool 'invalid_tool' not found" in data["error"]

    def test_mcp_health_endpoint_without_auth(self, client):
        """Test MCP health endpoint requires authentication"""
        response = client.get("/api/v1/mcp/health")
        assert response.status_code == 401

    @patch("app.api.mcp.tools.mcp_service")
    @patch("app.dependencies.get_mcp_client")
    @patch("app.dependencies.require_scope")
    def test_mcp_health_success(
        self, mock_require_scope, mock_get_mcp_client, mock_service, client, mock_deps, auth_headers
    ):
        """Test successful MCP health check"""
        # Mock authentication
        mock_get_mcp_client.return_value = mock_deps
        mock_require_scope.return_value = None

        # Mock service response
        mock_health = MCPHealthCheck(
            healthy=True,
            version="3.0.0",
            available_tools=["get_node_types", "get_node_details", "search_nodes"],
            timestamp=1234567890,
            processing_time_ms=10.5,
            request_id="test-request-123",
        )
        mock_service.health_check.return_value = mock_health

        response = client.get("/api/v1/mcp/health", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["healthy"] is True
        assert data["version"] == "3.0.0"
        assert len(data["available_tools"]) == 3

    @patch("app.api.mcp.tools.mcp_service")
    @patch("app.dependencies.get_mcp_client")
    @patch("app.dependencies.require_scope")
    def test_mcp_health_unhealthy(
        self, mock_require_scope, mock_get_mcp_client, mock_service, client, mock_deps, auth_headers
    ):
        """Test MCP health check when unhealthy"""
        # Mock authentication
        mock_get_mcp_client.return_value = mock_deps
        mock_require_scope.return_value = None

        # Mock unhealthy service response
        mock_health = MCPHealthCheck(
            healthy=False,
            version="3.0.0",
            available_tools=[],
            timestamp=1234567890,
            processing_time_ms=10.5,
            request_id="test-request-123",
        )
        mock_service.health_check.return_value = mock_health

        response = client.get("/api/v1/mcp/health", headers=auth_headers)

        assert response.status_code == 503  # Service Unavailable
        data = response.json()
        assert data["healthy"] is False
        assert len(data["available_tools"]) == 0

    @patch("app.api.mcp.tools.mcp_service")
    @patch("app.dependencies.get_mcp_client")
    @patch("app.dependencies.require_scope")
    def test_mcp_health_exception(
        self, mock_require_scope, mock_get_mcp_client, mock_service, client, mock_deps, auth_headers
    ):
        """Test MCP health check with exception"""
        # Mock authentication
        mock_get_mcp_client.return_value = mock_deps
        mock_require_scope.return_value = None

        # Mock service exception
        mock_service.health_check.side_effect = Exception("Health check failed")

        response = client.get("/api/v1/mcp/health", headers=auth_headers)

        assert response.status_code == 500
        data = response.json()
        assert data["healthy"] is False
        assert "Health check failed" in data["error"]

    def test_request_headers_and_metadata(self, client, auth_headers):
        """Test that request headers are properly processed"""
        with patch("app.dependencies.get_mcp_client") as mock_get_client, patch(
            "app.dependencies.require_scope"
        ) as mock_require_scope, patch("app.api.mcp.tools.mcp_service") as mock_service:
            # Mock authentication
            mock_deps = Mock()
            mock_deps.mcp_client = Mock(client_name="test_client")
            mock_deps.request_context = {"request_id": "test-request-123"}
            mock_get_client.return_value = mock_deps
            mock_require_scope.return_value = None

            # Mock service
            mock_tools_response = MCPToolsResponse(
                success=True,
                tools=[],
                total_count=0,
                available_count=0,
                categories=[],
                timestamp=datetime.now(timezone.utc),
                processing_time_ms=5.0,
                request_id="test-request-123",
            )
            mock_service.get_available_tools.return_value = mock_tools_response

            response = client.get("/api/v1/mcp/tools", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert "processing_time_ms" in data
            assert "request_id" in data

    def test_malformed_json_request(self, client, auth_headers):
        """Test handling of malformed JSON in POST requests"""
        with patch("app.dependencies.get_mcp_client") as mock_get_client, patch(
            "app.dependencies.require_scope"
        ) as mock_require_scope:
            mock_deps = Mock()
            mock_deps.mcp_client = Mock(client_name="test_client")
            mock_deps.request_context = {"request_id": "test-request-123"}
            mock_get_client.return_value = mock_deps
            mock_require_scope.return_value = None

            # Send malformed JSON
            response = client.post(
                "/api/v1/mcp/invoke",
                headers=auth_headers,
                content="invalid json content",
            )

            assert response.status_code == 422  # Unprocessable Entity
