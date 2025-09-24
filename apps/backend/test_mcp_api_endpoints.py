#!/usr/bin/env python3
"""
Test MCP API endpoints directly through the API Gateway
Tests the /api/v1/mcp/ endpoints with both Notion and Google Calendar tools
"""

import json
import time

import requests


def test_mcp_endpoints():
    """Test MCP API endpoints."""
    print("🌐 Testing MCP API Endpoints")
    print("=" * 50)

    base_url = "http://localhost:8000/api/v1/mcp"
    headers = {
        "X-API-Key": "test-api-key",  # Mock API key for testing
        "Content-Type": "application/json",
    }

    # Test 1: Health check
    print("🔧 Test 1: MCP Health Check")
    try:
        response = requests.get(f"{base_url}/health", headers=headers, timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Healthy: {data.get('healthy', False)}")
            print(f"   Available tools: {len(data.get('available_tools', []))}")
        else:
            print(f"   Error: {response.text}")
    except requests.exceptions.ConnectionError:
        print("   ❌ API Gateway not running on localhost:8000")
        print("   💡 Start with: docker-compose up api-gateway")
        return False
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")

    # Test 2: List all tools
    print("\n🔧 Test 2: List All Tools")
    try:
        response = requests.get(f"{base_url}/tools", headers=headers, timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Total tools: {data.get('total_count', 0)}")
            print(f"   Categories: {data.get('categories', [])}")

            # List tool names
            tools = data.get("tools", [])
            print("   Tools found:")
            for tool in tools[:10]:  # Show first 10
                print(f"     - {tool['name']} ({tool['category']})")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   ❌ List tools failed: {e}")

    # Test 3: Notion tool invocation (with mock token)
    print("\n🔧 Test 3: Notion Tool Invocation")
    try:
        payload = {
            "tool_name": "notion_search",
            "parameters": {
                "access_token": "test_token_12345",
                "query": "test search",
                "ai_format": "structured",
                "limit": 5,
            },
        }

        response = requests.post(f"{base_url}/invoke", headers=headers, json=payload, timeout=10)

        print(f"   Status: {response.status_code}")
        if response.status_code in [200, 400]:  # 400 expected for mock token
            data = response.json()
            print(f"   Is Error: {data.get('isError', False)}")
            if data.get("content"):
                print(f"   Response: {data['content'][0]['text'][:100]}...")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Notion invocation failed: {e}")

    # Test 4: Google Calendar tool invocation (with mock token)
    print("\n🔧 Test 4: Google Calendar Tool Invocation")
    try:
        payload = {
            "tool_name": "google_calendar_events",
            "parameters": {
                "access_token": "test_token_12345",
                "action": "list",
                "filters": {"time_min": "today", "max_results": 5},
            },
        }

        response = requests.post(f"{base_url}/invoke", headers=headers, json=payload, timeout=10)

        print(f"   Status: {response.status_code}")
        if response.status_code in [200, 400]:  # 400 expected for mock token
            data = response.json()
            print(f"   Is Error: {data.get('isError', False)}")
            if data.get("content"):
                print(f"   Response: {data['content'][0]['text'][:100]}...")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Google Calendar invocation failed: {e}")

    # Test 5: New Google Calendar date query tool
    print("\n🔧 Test 5: Google Calendar Date Query Tool")
    try:
        payload = {
            "tool_name": "google_calendar_date_query",
            "parameters": {
                "access_token": "test_token_12345",
                "date_query": "events next week",
                "include_analytics": True,
                "ai_format": "narrative",
            },
        }

        response = requests.post(f"{base_url}/invoke", headers=headers, json=payload, timeout=10)

        print(f"   Status: {response.status_code}")
        if response.status_code in [200, 400]:  # 400 expected for mock token
            data = response.json()
            print(f"   Is Error: {data.get('isError', False)}")
            if data.get("content"):
                print(f"   Response: {data['content'][0]['text'][:100]}...")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Date query invocation failed: {e}")

    # Test 6: Document retrieval with Notion
    print("\n🔧 Test 6: Notion Document Retrieval")
    try:
        payload = {
            "tool_name": "notion_page",
            "parameters": {
                "access_token": "test_token_12345",
                "action": "retrieve",
                "search_query": "meeting notes",
                "content_format": "structured",
                "ai_format": "narrative",
            },
        }

        response = requests.post(f"{base_url}/invoke", headers=headers, json=payload, timeout=10)

        print(f"   Status: {response.status_code}")
        if response.status_code in [200, 400]:  # 400 expected for mock token
            data = response.json()
            print(f"   Is Error: {data.get('isError', False)}")
            if data.get("content"):
                print(f"   Response: {data['content'][0]['text'][:100]}...")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Document retrieval failed: {e}")

    print("\n🎯 MCP API Endpoints Test Summary")
    print("All endpoint connectivity tests completed!")
    return True


def test_authentication_scenarios():
    """Test different authentication scenarios."""
    print("\n🔐 Testing Authentication Scenarios")
    print("=" * 40)

    base_url = "http://localhost:8000/api/v1/mcp"

    # Test 1: No API key
    print("🔧 Test 1: No API Key")
    try:
        response = requests.get(f"{base_url}/tools", timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ Correctly rejected request without API key")
        else:
            print(f"   ❌ Unexpected status code: {response.status_code}")
    except Exception as e:
        print(f"   API Gateway not running: {e}")

    # Test 2: Invalid API key
    print("\n🔧 Test 2: Invalid API Key")
    try:
        headers = {"X-API-Key": "invalid-key-123"}
        response = requests.get(f"{base_url}/tools", headers=headers, timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ Correctly rejected invalid API key")
        else:
            print(f"   Response: {response.text[:100]}...")
    except Exception as e:
        print(f"   Test failed: {e}")

    # Test 3: Valid API key format
    print("\n🔧 Test 3: Valid API Key Format")
    try:
        headers = {"X-API-Key": "test-api-key"}
        response = requests.get(f"{base_url}/tools", headers=headers, timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ API key accepted")
        else:
            print(f"   Response: {response.text[:100]}...")
    except Exception as e:
        print(f"   Test failed: {e}")


if __name__ == "__main__":
    print("🚀 Starting MCP API Endpoint Tests")
    print("=" * 60)

    # Test basic functionality
    success = test_mcp_endpoints()

    # Test authentication
    test_authentication_scenarios()

    print("\n" + "=" * 60)
    print("✅ MCP API endpoint testing completed!")
    print("\n💡 For real OAuth testing:")
    print("1. Get real Notion API token from oauth_tokens table")
    print("2. Get real Google Calendar token from oauth_tokens table")
    print("3. Replace test_token_12345 with real tokens in requests")
