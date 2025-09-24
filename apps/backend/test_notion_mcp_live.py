#!/usr/bin/env python3
"""
Live test of Notion MCP tools with real API calls
Tests the actual MCP endpoints and OAuth token handling
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict

# Add the backend path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def test_notion_mcp_tools():
    """Test Notion MCP tools with both mock and real scenarios."""

    print("🧪 Testing Notion MCP Tools")
    print("=" * 50)

    # Import the service
    try:
        from api_gateway.app.api.mcp.notion_tools import notion_mcp_service
    except ImportError:
        try:
            # Try alternative import path
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "api-gateway"))
            from app.api.mcp.notion_tools import notion_mcp_service
        except ImportError as e:
            print(f"❌ Failed to import Notion MCP service: {e}")
            return False

    # Test 1: Get available tools
    print("🔧 Test 1: Get Available Tools")
    try:
        tools_response = notion_mcp_service.get_available_tools()
        print(f"✅ Found {tools_response.total_count} tools:")
        for tool in tools_response.tools:
            print(f"  - {tool.name}: {tool.description[:60]}...")
        print()
    except Exception as e:
        print(f"❌ Failed to get tools: {e}")
        return False

    # Test 2: Tool schema validation
    print("🔧 Test 2: Tool Schema Validation")
    try:
        for tool in tools_response.tools:
            schema = tool.inputSchema
            assert "type" in schema
            assert "properties" in schema
            assert "access_token" in schema["properties"]
            assert "required" in schema
            print(f"✅ {tool.name} schema is valid")
        print()
    except Exception as e:
        print(f"❌ Schema validation failed: {e}")
        return False

    # Test 3: Error handling (missing token)
    print("🔧 Test 3: Error Handling (Missing Token)")
    try:
        response = await notion_mcp_service.invoke_tool(
            "notion_search",
            {
                "query": "test"
                # Missing access_token
            },
        )

        if response.isError:
            print("✅ Correctly handled missing access token error")
            print(f"   Error: {response.content[0].text}")
        else:
            print("❌ Should have failed with missing token")
        print()
    except Exception as e:
        print(f"❌ Unexpected error in error handling test: {e}")

    # Test 4: Tool info
    print("🔧 Test 4: Tool Information")
    try:
        for tool_name in ["notion_search", "notion_page", "notion_database"]:
            info = notion_mcp_service.get_tool_info(tool_name)
            print(f"✅ {tool_name}:")
            print(f"   Available: {info['available']}")
            print(f"   Category: {info['category']}")
            print(f"   Features: {len(info.get('features', []))} features")
        print()
    except Exception as e:
        print(f"❌ Tool info test failed: {e}")

    # Test 5: Health check
    print("🔧 Test 5: Health Check")
    try:
        health = notion_mcp_service.health_check()
        print(f"✅ Service healthy: {health.healthy}")
        print(f"   Version: {health.version}")
        print(f"   Available tools: {len(health.available_tools)}")
        print()
    except Exception as e:
        print(f"❌ Health check failed: {e}")

    # Test 6: Document retrieval action (new feature)
    print("🔧 Test 6: Document Retrieval Action Schema")
    try:
        page_tool = next(tool for tool in tools_response.tools if tool.name == "notion_page")
        actions = page_tool.inputSchema["properties"]["action"]["enum"]

        if "retrieve" in actions:
            print("✅ Document retrieval action is available")

            # Check for retrieval-specific parameters
            properties = page_tool.inputSchema["properties"]
            retrieval_params = ["page_ids", "search_query", "content_format", "ai_format"]
            found_params = [param for param in retrieval_params if param in properties]
            print(f"   Retrieval parameters: {len(found_params)}/{len(retrieval_params)}")
            print(f"   Found: {found_params}")
        else:
            print("❌ Document retrieval action not found")
        print()
    except Exception as e:
        print(f"❌ Document retrieval test failed: {e}")

    # Test 7: AI Format Options
    print("🔧 Test 7: AI Format Options")
    try:
        for tool in tools_response.tools:
            schema = tool.inputSchema["properties"]
            if "ai_format" in schema:
                ai_formats = schema["ai_format"]["enum"]
                print(f"✅ {tool.name} supports AI formats: {ai_formats}")
            else:
                print(f"ℹ️  {tool.name} doesn't have AI format options")
        print()
    except Exception as e:
        print(f"❌ AI format test failed: {e}")

    # Test 8: OAuth Token Simulation (with mock token)
    print("🔧 Test 8: OAuth Token Simulation")
    try:
        # Test with a mock token to see the request structure
        mock_params = {
            "access_token": "test_token_mock_12345",
            "query": "test search",
            "ai_format": "structured",
            "relevance_scoring": True,
            "limit": 5,
        }

        response = await notion_mcp_service.invoke_tool("notion_search", mock_params)

        # Even with a mock token, we should get a structured error
        if response.isError:
            print("✅ Mock token correctly triggers authentication error")
            print(f"   Response type: {'Error' if response.isError else 'Success'}")
        else:
            print("ℹ️  Mock token was processed (service might be in test mode)")

        # Check response structure
        print(f"   Has execution time: {hasattr(response, '_execution_time_ms')}")
        print(f"   Has tool name: {hasattr(response, '_tool_name')}")
        print()
    except Exception as e:
        print(f"❌ OAuth simulation failed: {e}")

    print("🎯 Notion MCP Test Summary")
    print("All basic functionality tests completed!")
    print("\n💡 To test with real data:")
    print("1. Set NOTION_API_KEY environment variable")
    print("2. Ensure Notion workspace access")
    print("3. Run with real OAuth tokens from oauth_tokens table")

    return True


async def test_with_real_oauth_token():
    """Test with real OAuth token if available."""
    print("\n🔑 Testing with Real OAuth Token")
    print("=" * 40)

    # Check for real OAuth token sources
    notion_token = os.getenv("NOTION_API_KEY")

    if not notion_token or notion_token.startswith("test_"):
        print("ℹ️  No real Notion OAuth token found")
        print("   Set NOTION_API_KEY environment variable for live testing")
        return

    try:
        from api_gateway.app.api.mcp.notion_tools import notion_mcp_service
    except ImportError:
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "api-gateway"))
            from app.api.mcp.notion_tools import notion_mcp_service
        except ImportError as e:
            print(f"❌ Failed to import: {e}")
            return

    # Test real search
    print("🔍 Testing real Notion search...")
    try:
        real_params = {
            "access_token": notion_token,
            "query": "meeting",
            "ai_format": "narrative",
            "relevance_scoring": True,
            "limit": 3,
        }

        response = await notion_mcp_service.invoke_tool("notion_search", real_params)

        if response.isError:
            print(f"❌ Real token search failed: {response.content[0].text}")
        else:
            print("✅ Real search succeeded!")
            content = response.structuredContent
            print(f"   Format type: {content.get('format_type', 'structured')}")
            print(f"   Results found: {content.get('total_count', 0)}")

            if content.get("ai_narrative"):
                print(f"   Narrative preview: {content['ai_narrative'][:100]}...")

    except Exception as e:
        print(f"❌ Real search test failed: {e}")


if __name__ == "__main__":
    print("🚀 Starting Notion MCP Live Tests")
    print("=" * 60)

    # Run basic tests
    success = asyncio.run(test_notion_mcp_tools())

    # Run OAuth tests if tokens available
    asyncio.run(test_with_real_oauth_token())

    print("\n" + "=" * 60)
    print("✅ Notion MCP testing completed!")
