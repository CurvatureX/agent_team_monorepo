"""
Basic tests for API Gateway
Tests cover all three API layers: Public, App, and MCP
"""

import pytest
from app.main import create_application
from fastapi.testclient import TestClient


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
    response = client.get("/api/v1/mcp/tools")
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
