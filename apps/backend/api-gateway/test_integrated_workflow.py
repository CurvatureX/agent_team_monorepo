#!/usr/bin/env python3
"""
Test script for integrated workflow generation in chat stream
"""

import asyncio
import aiohttp
import json
from typing import AsyncGenerator


async def test_chat_stream_workflow_integration():
    """Test workflow generation integrated into chat stream"""
    
    print("🧪 Testing integrated workflow generation in chat stream...")
    
    # Test data
    session_id = "test-session-123"
    base_url = "http://localhost:8000"
    
    # Test 1: Regular chat message (should not trigger workflow)
    print("\n1. Testing regular chat message...")
    await test_chat_message(base_url, session_id, "Hello, how are you?")
    
    # Test 2: Workflow generation message (should trigger workflow)
    print("\n2. Testing workflow generation message...")
    await test_chat_message(base_url, session_id, "Create a workflow for email monitoring")
    
    print("\n✅ All tests completed!")


async def test_chat_message(base_url: str, session_id: str, user_message: str):
    """Test a single chat message"""
    
    print(f"   Message: '{user_message}'")
    
    url = f"{base_url}/api/v1/chat/stream"
    params = {
        "session_id": session_id,
        "user_message": user_message
    }
    
    # Mock authorization header
    headers = {
        "Authorization": "Bearer mock-token-for-testing"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 401:
                    print("   ⚠️  Authentication required - this is expected in production")
                    print(f"   Response: {response.status}")
                    return
                
                print(f"   Response status: {response.status}")
                
                if response.status == 200:
                    print("   📡 SSE Stream events:")
                    
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if line.startswith('data: '):
                            try:
                                data = json.loads(line[6:])  # Remove 'data: ' prefix
                                event_type = data.get('type', 'unknown')
                                
                                if event_type == 'message':
                                    delta = data.get('delta', '')
                                    workflow_id = data.get('workflow_id')
                                    if workflow_id:
                                        print(f"      📝 Message: '{delta}' (workflow_id: {workflow_id})")
                                    else:
                                        print(f"      💬 Message: '{delta}'")
                                
                                elif event_type.startswith('workflow_'):
                                    workflow_id = data.get('workflow_id', 'N/A')
                                    message = data.get('data', {}).get('message', 'N/A')
                                    print(f"      🔧 {event_type}: {message} (ID: {workflow_id})")
                                
                                else:
                                    print(f"      🔍 {event_type}: {data}")
                                    
                            except json.JSONDecodeError as e:
                                print(f"      ❌ JSON decode error: {e}")
                
                else:
                    text = await response.text()
                    print(f"   ❌ Error response: {text}")
                    
    except aiohttp.ClientError as e:
        print(f"   ❌ Connection error: {e}")
        print(f"   💡 Make sure the API Gateway is running on {base_url}")


if __name__ == "__main__":
    print("🚀 Testing Integrated Workflow Generation API")
    print("=" * 50)
    
    try:
        asyncio.run(test_chat_stream_workflow_integration())
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}") 