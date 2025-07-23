#!/usr/bin/env python3
"""
Test script for new API endpoints according to API_DOC.md
"""

import asyncio
from fastapi.testclient import TestClient
from app.main import app

def test_new_endpoints():
    """Test the updated API endpoints"""
    client = TestClient(app)
    
    print("🧪 Testing new API endpoints...")
    
    # Test 1: Health check (should work)
    print("\n1. Testing health endpoint...")
    response = client.get("/health")
    assert response.status_code == 200
    print("✅ Health check passed")
    
    # Test 2: Root endpoint (should show new endpoint info)
    print("\n2. Testing root endpoint...")
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    endpoints = data.get("endpoints", {})
    assert endpoints.get("chat") == "/api/v1/chat/stream"
    assert endpoints.get("workflow") == "/api/v1/workflow_generation"
    print("✅ Root endpoint shows updated paths")
    
    # Test 3: Check OpenAPI schema includes new endpoints
    print("\n3. Testing OpenAPI schema...")
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    paths = schema.get("paths", {})
    
    # Verify new endpoints are in schema
    assert "/api/v1/chat/stream" in paths
    assert "/api/v1/workflow_generation" in paths
    assert "/api/v1/session" in paths
    print("✅ OpenAPI schema includes new endpoints")
    
    # Test 4: Session endpoint requires auth (but should accept new parameters)
    print("\n4. Testing session endpoint (should require auth)...")
    response = client.post("/api/v1/session", json={"action": "create"})
    assert response.status_code == 401  # Should require authentication
    print("✅ Session endpoint requires authentication")
    
    # Test 5: Chat stream endpoint requires auth
    print("\n5. Testing chat stream endpoint (should require auth)...")
    response = client.get("/api/v1/chat/stream?session_id=test&user_message=hello")
    assert response.status_code == 401  # Should require authentication
    print("✅ Chat stream endpoint requires authentication")
    
    # Test 6: Workflow generation endpoint requires auth
    print("\n6. Testing workflow generation endpoint (should require auth)...")
    response = client.get("/api/v1/workflow_generation?session_id=test")
    assert response.status_code == 401  # Should require authentication
    print("✅ Workflow generation endpoint requires authentication")
    
    print("\n🎉 All endpoint tests passed!")
    print("📝 Note: Actual functionality requires valid JWT tokens from Supabase")

if __name__ == "__main__":
    test_new_endpoints()