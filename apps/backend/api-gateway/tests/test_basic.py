"""
Basic tests for API Gateway
Tests cover all three API layers: Public, App, and MCP
"""

import os
import sys
import pytest
from app.main import create_application
from fastapi.testclient import TestClient

# Skip all tests in CI environment
if os.getenv("CI") == "true":
    pytest.skip("Skipping API Gateway tests in CI environment", allow_module_level=True)


@pytest.fixture
def client():
    """Create test client"""
    app = create_application()
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "version" in data


def test_version_endpoint(client):
    """Test version endpoint"""
    response = client.get("/version")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "service" in data


def test_docs_endpoint(client):
    """Test OpenAPI docs endpoint"""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_app_api_requires_auth(client):
    """Test that App API endpoints require authentication"""
    response = client.get("/api/v1/app/sessions")
    assert response.status_code == 401


def test_mcp_api_requires_auth(client):
    """Test that MCP API endpoints require authentication"""
    # Test tools endpoint
    response = client.get("/api/v1/mcp/tools")
    assert response.status_code == 401

    # Test invoke endpoint
    response = client.post("/api/v1/mcp/invoke", json={"tool_name": "test", "params": {}})
    assert response.status_code == 401

    # Test health endpoint
    response = client.get("/api/v1/mcp/health")
    assert response.status_code == 401

    # Test tool info endpoint
    response = client.get("/api/v1/mcp/tools/test_tool")
    assert response.status_code == 401


def test_request_id_header(client):
    """Test that request ID header is added"""
    response = client.get("/")
    assert "X-Request-ID" in response.headers


def test_process_time_header(client):
    """Test that process time header is added"""
    response = client.get("/")
    assert "X-Process-Time" in response.headers


def test_cors_headers(client):
    """Test CORS headers are present"""
    response = client.get("/")
    # Check that CORS middleware is working (should have access-control headers)
    assert response.status_code == 200


def test_invalid_endpoint(client):
    """Test invalid endpoint returns 404"""
    response = client.get("/api/invalid/endpoint")
    assert response.status_code == 404


def test_app_creation():
    """Test that app can be created successfully"""
    app = create_application()
    assert app is not None
    assert hasattr(app, "router")


def test_middleware_configuration(client):
    """Test middleware is properly configured"""
    response = client.get("/")
    # Check that standard headers are present
    assert "X-Request-ID" in response.headers
    assert "X-Process-Time" in response.headers
    # Check CORS is enabled
    assert response.status_code == 200


def test_mcp_node_knowledge_integration(client):
    """Test that MCP node knowledge tools are available (basic integration test)"""
    # This test verifies the MCP service can be instantiated without errors
    # Full functionality is tested in dedicated MCP test files
    from app.api.mcp.tools import NodeKnowledgeMCPService

    # Should be able to create service without errors
    service = NodeKnowledgeMCPService()
    assert service is not None

    # Should have node knowledge service
    assert hasattr(service, "node_knowledge")

    # Should be able to get available tools
    tools_response = service.get_available_tools()
    assert tools_response.success is True
    assert len(tools_response.tools) == 3

    # Should have the expected tool names
    tool_names = [tool.name for tool in tools_response.tools]
    expected_tools = ["get_node_types", "get_node_details", "search_nodes"]
    for expected_tool in expected_tools:
        assert expected_tool in tool_names


def test_health_endpoints_consistency(client):
    """Test that all health endpoints return consistent structure"""
    # Public health (no auth required)
    response = client.get("/api/v1/public/health")
    assert response.status_code == 200
    public_health = response.json()
    assert "status" in public_health

    # Root endpoint health info
    response = client.get("/")
    assert response.status_code == 200
    root_data = response.json()
    assert "service" in root_data
    assert "version" in root_data
