"""
Integration tests for MCP API endpoints
Tests the full HTTP API layer for MCP tools
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
from app.main import create_application
from app.models import MCPContentItem, MCPHealthCheck, MCPInvokeResponse, MCPTool, MCPToolsResponse
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
        # Response follows MCP JSON-RPC 2.0 standard
        assert data["jsonrpc"] == "2.0"
        assert "id" in data
        assert "result" in data
        assert "tools" in data["result"]
        assert len(data["result"]["tools"]) == 6
        # Check first tool has MCP required fields
        first_tool = data["result"]["tools"][0]
        assert first_tool["name"] == "get_node_types"
        assert first_tool["description"] == "Get node types"
        assert "inputSchema" in first_tool or "parameters" in first_tool

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
        # Response follows JSON-RPC 2.0 error format
        assert data["jsonrpc"] == "2.0"
        assert "error" in data
        assert data["error"]["code"] == -32603
        assert "Failed to retrieve tools" in data["error"]["message"]

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

        # Mock service response - MCP compliant format
        mock_result = MCPInvokeResponse(
            content=[
                MCPContentItem(type="text", text="Tool 'get_node_types' executed successfully")
            ],
            isError=False,
            structuredContent={
                "ACTION_NODE": ["HTTP_REQUEST", "RUN_CODE"],
                "AI_AGENT_NODE": ["OPENAI_NODE", "CLAUDE_NODE"],
            },
        )
        # Set private attributes
        mock_result._tool_name = "get_node_types"
        mock_result._execution_time_ms = 15.5
        mock_result._request_id = "test-request-123"
        mock_service.invoke_tool = AsyncMock(return_value=mock_result)

        # Support both old and new request formats for backwards compatibility
        payload = {"name": "get_node_types", "arguments": {}}

        response = client.post("/api/v1/mcp/invoke", json=payload, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        # Response follows JSON-RPC 2.0 format
        assert data["jsonrpc"] == "2.0"
        assert "id" in data
        assert "result" in data
        # Check MCP tools/call response structure
        result = data["result"]
        assert "content" in result
        assert "isError" in result
        assert result["isError"] is False
        assert len(result["content"]) > 0
        assert result["content"][0]["type"] == "text"
        assert "structuredContent" in result
        assert "ACTION_NODE" in result["structuredContent"]

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
            content=[
                MCPContentItem(type="text", text="Tool 'get_node_details' executed successfully")
            ],
            isError=False,
            structuredContent={
                "nodes": [
                    {
                        "node_type": "ACTION_NODE",
                        "subtype": "HTTP_REQUEST",
                        "description": "Make HTTP requests to external APIs",
                        "parameters": [{"name": "url", "type": "string", "required": True}],
                        "input_ports": [],
                        "output_ports": [],
                    }
                ]
            },
        )
        # Set private attributes
        mock_result._tool_name = "get_node_details"
        mock_result._execution_time_ms = 25.3
        mock_service.invoke_tool = AsyncMock(return_value=mock_result)

        payload = {
            "name": "get_node_details",
            "arguments": {
                "nodes": [{"node_type": "ACTION_NODE", "subtype": "HTTP_REQUEST"}],
                "include_examples": True,
            },
        }

        response = client.post("/api/v1/mcp/invoke", json=payload, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        # Response follows JSON-RPC 2.0 format
        assert data["jsonrpc"] == "2.0"
        assert "id" in data
        assert "result" in data
        # Check MCP tools/call response structure
        result = data["result"]
        assert "content" in result
        assert "isError" in result
        assert result["isError"] is False
        assert len(result["content"]) > 0
        assert result["content"][0]["type"] == "text"
        assert "structuredContent" in result
        assert "nodes" in result["structuredContent"]
        assert len(result["structuredContent"]["nodes"]) == 1
        assert result["structuredContent"]["nodes"][0]["node_type"] == "ACTION_NODE"

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
            content=[MCPContentItem(type="text", text="Tool 'search_nodes' executed successfully")],
            isError=False,
            structuredContent={
                "nodes": [
                    {
                        "node_type": "ACTION_NODE",
                        "subtype": "HTTP_REQUEST",
                        "description": "Make HTTP requests",
                        "relevance_score": 15,
                    }
                ]
            },
        )
        # Set private attributes
        mock_result._tool_name = "search_nodes"
        mock_result._execution_time_ms = 12.7
        mock_service.invoke_tool = AsyncMock(return_value=mock_result)

        payload = {
            "tool_name": "search_nodes",
            "parameters": {"query": "HTTP request", "max_results": 5},
        }

        response = client.post("/api/v1/mcp/invoke", json=payload, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        # Response follows JSON-RPC 2.0 format
        assert data["jsonrpc"] == "2.0"
        assert "id" in data
        assert "result" in data
        # Check MCP tools/call response structure
        result = data["result"]
        assert "content" in result
        assert "isError" in result
        assert result["isError"] is False
        assert len(result["content"]) > 0
        assert result["content"][0]["type"] == "text"
        assert "structuredContent" in result
        assert "nodes" in result["structuredContent"]
        assert len(result["structuredContent"]["nodes"]) == 1
        assert result["structuredContent"]["nodes"][0]["relevance_score"] == 15

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
            content=[MCPContentItem(type="text", text="Tool 'invalid_tool' not found")],
            isError=True,
        )
        # Set private attributes
        mock_result._tool_name = "invalid_tool"
        mock_result._execution_time_ms = 1.2
        mock_service.invoke_tool = AsyncMock(return_value=mock_result)

        payload = {"tool_name": "invalid_tool", "parameters": {}}

        response = client.post("/api/v1/mcp/invoke", json=payload, headers=auth_headers)

        assert response.status_code == 200  # Service returns error in response, not HTTP error
        data = response.json()
        # Response follows JSON-RPC 2.0 format
        assert data["jsonrpc"] == "2.0"
        assert "id" in data
        assert "result" in data
        # Check MCP tools/call response structure for errors
        result = data["result"]
        assert "content" in result
        assert "isError" in result
        assert result["isError"] is True
        assert len(result["content"]) > 0
        assert "Tool 'invalid_tool' not found" in result["content"][0]["text"]

    @patch("app.api.mcp.tools.mcp_service")
    @patch("app.dependencies.get_mcp_client")
    @patch("app.dependencies.require_scope")
    def test_mcp_invoke_missing_name_validation(
        self, mock_require_scope, mock_get_mcp_client, mock_service, client, mock_deps, auth_headers
    ):
        """Test validation when required name field is missing"""
        # Mock authentication
        mock_get_mcp_client.return_value = mock_deps
        mock_require_scope.return_value = None

        # Test missing name field
        payload = {"arguments": {}}

        response = client.post("/api/v1/mcp/invoke", json=payload, headers=auth_headers)
        assert response.status_code == 422  # ValidationError for missing required field

        # Test that the first case (missing name) returns proper error
        data = response.json()
        assert "Field required" in str(data)

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
        # Response follows JSON-RPC 2.0 error format
        assert data["jsonrpc"] == "2.0"
        assert "error" in data
        assert "Tool invocation failed" in data["error"]["message"]

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
        assert len(data["available_tools"]) == 6

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
        assert len(data["available_tools"]) == 3

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
            # Response follows MCP JSON-RPC 2.0 standard
            assert data["jsonrpc"] == "2.0"
            assert "result" in data
            assert "tools" in data["result"]

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
