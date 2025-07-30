#!/usr/bin/env python3
"""
Integration Test for API Gateway
Tests /session and /chat/stream endpoints with real authentication

Requirements:
- Add these environment variables to .env file:
  TEST_USER_EMAIL=your-test-email@example.com
  TEST_USER_PASSWORD=your-test-password

This test performs:
1. Real Supabase authentication using test credentials
2. Session creation via /api/app/sessions
3. Chat streaming via /api/app/chat/stream
4. Validates full end-to-end workflow
"""

import asyncio
import json
import os
import time
from typing import Optional

import httpx
import pytest
from dotenv import load_dotenv


# Load environment variables
load_dotenv()


class SupabaseAuth:
    """Helper class for Supabase authentication"""
    
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
        self.test_email = os.getenv("TEST_USER_EMAIL")
        self.test_password = os.getenv("TEST_USER_PASSWORD")
        
        if not all([self.supabase_url, self.supabase_anon_key, self.test_email, self.test_password]):
            raise ValueError(
                "Missing required environment variables. Please add to .env:\n"
                "TEST_USER_EMAIL=your-test-email@example.com\n"
                "TEST_USER_PASSWORD=your-test-password"
            )
    
    async def get_access_token(self) -> str:
        """Authenticate with Supabase and get access token"""
        auth_url = f"{self.supabase_url}/auth/v1/token?grant_type=password"
        
        auth_data = {
            "email": self.test_email,
            "password": self.test_password
        }
        
        headers = {
            "apikey": self.supabase_anon_key,
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(auth_url, json=auth_data, headers=headers)
            
            if response.status_code != 200:
                error_detail = response.text
                raise Exception(f"Authentication failed: {response.status_code} - {error_detail}")
            
            auth_result = response.json()
            access_token = auth_result.get("access_token")
            
            if not access_token:
                raise Exception("No access token in authentication response")
            
            print(f"✅ Successfully authenticated user: {self.test_email}")
            return access_token


class APIGatewayIntegrationTest:
    """Integration test for API Gateway endpoints"""
    
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.auth = SupabaseAuth()
        self.access_token: Optional[str] = None
        self.session_id: Optional[str] = None
    
    async def setup(self):
        """Setup test by getting authentication token"""
        print("🔧 Setting up integration test...")
        self.access_token = await self.auth.get_access_token()
        print(f"📝 Access token obtained: {self.access_token[:20]}...")
    
    async def test_session_creation(self) -> str:
        """Test session creation endpoint"""
        print("\n1️⃣ Testing session creation...")
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        session_data = {
            "title": "Integration Test Session",
            "description": "Automated integration test session",
            "action": "create"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/app/sessions",
                json=session_data,
                headers=headers
            )
            
            if response.status_code not in [200, 201]:
                error_detail = response.text
                raise Exception(f"Session creation failed: {response.status_code} - {error_detail}")
            
            session_result = response.json()
            session_id = session_result.get("session", {}).get("id")
            
            if not session_id:
                raise Exception("No session ID in response")
            
            self.session_id = session_id
            print(f"✅ Session created successfully: {session_id}")
            print(f"📄 Session data: {json.dumps(session_result, indent=2)}")
            
            return session_id
    
    async def test_chat_stream(self, session_id: str):
        """Test chat streaming endpoint"""
        print(f"\n2️⃣ Testing chat stream for session {session_id}...")
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }
        
        chat_data = {
            "session_id": session_id,
            "user_message": "帮我创建一个简单的邮件处理工作流"
        }
        
        print(f"📨 Sending chat request: {json.dumps(chat_data, ensure_ascii=False)}")
        
        response_count = 0
        response_types = set()
        messages_received = []
        status_changes = []
        workflow_received = None
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/v1/app/chat/stream",
                json=chat_data,
                headers=headers
            ) as response:
                
                if response.status_code != 200:
                    error_detail = await response.aread()
                    raise Exception(f"Chat stream failed: {response.status_code} - {error_detail.decode()}")
                
                print("📡 Receiving streaming responses...\n")
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            # 修复：去掉 "data: " 前缀再解析 JSON
                            data = json.loads(line[6:])  # 去掉 "data: " 前缀
                            response_count += 1
                            print(f"📥 Response #{response_count} - Type: {data}")
                            
                            # 收集响应类型用于分析
                            response_type = data.get("type", "unknown")
                            response_types.add(response_type)
                            
                            # 收集消息内容
                            if response_type == "message":
                                message_content = data.get("data", {}).get("text", "")
                                if message_content:
                                    messages_received.append(message_content)
                            
                            # 收集状态变化
                            elif response_type == "status_change":
                                status_info = data.get("data", {})
                                status_changes.append({
                                    "previous": status_info.get("previous_stage"),
                                    "current": status_info.get("current_stage"),
                                    "node": status_info.get("node_name")
                                })
                            
                            # 检查工作流响应
                            elif response_type == "workflow":
                                workflow_received = True
                            
                            # Stop after final response or reasonable limit
                            if data.get("is_final", False) or response_count >= 20:
                                break
                                
                        except json.JSONDecodeError as e:
                            print(f"❌ Failed to parse SSE data: {e}")
                            print(f"   Raw line: {line}")
                            # 添加更详细的调试信息
                            print(f"   Line length: {len(line)}")
                            print(f"   Line starts with 'data: ': {line.startswith('data: ')}")
                            if line.startswith("data: "):
                                print(f"   Content after 'data: ': {line[6:]}")
                            continue
        
        # Analyze results
        print(f"📊 Chat Stream Test Results:")
        print(f"   - Total responses: {response_count}")
        print(f"   - Response types: {response_types}")
        print(f"   - Messages received: {len(messages_received)}")
        print(f"   - Status changes: {len(status_changes)}")
        print(f"   - Workflow received: {'Yes' if workflow_received else 'No'}")
        
        # Validate results
        if response_count == 0:
            raise Exception("No responses received from chat stream")
        
        if "message" not in response_types and "error" not in response_types:
            raise Exception("Expected at least message or error responses")
        
        print("✅ Chat stream test completed successfully!")
        
        return {
            "response_count": response_count,
            "response_types": list(response_types),
            "messages": messages_received,
            "status_changes": status_changes,
            "workflow": workflow_received
        }
    
    async def test_session_cleanup(self, session_id: str):
        """Optionally cleanup test session"""
        print(f"\n3️⃣ Cleaning up test session {session_id}...")
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}/api/v1/app/sessions/{session_id}",
                headers=headers
            )
            
            if response.status_code == 204:
                print("✅ Session cleaned up successfully")
            else:
                print(f"⚠️ Session cleanup returned: {response.status_code}")
    
    async def run_full_test(self):
        """Run complete integration test"""
        print("🚀 Starting API Gateway Integration Test\n")
        
        try:
            # Setup authentication
            await self.setup()
            
            # Test session creation
            session_id = await self.test_session_creation()
            
            # Test chat streaming
            chat_results = await self.test_chat_stream(session_id)
            
            # Optional cleanup
            await self.test_session_cleanup(session_id)
            
            print("\n🎉 All integration tests passed!")
            print("\nTest Summary:")
            print(f"✅ Authentication: Success")
            print(f"✅ Session Creation: Success (ID: {session_id})")
            print(f"✅ Chat Streaming: Success ({chat_results['response_count']} responses)")
            print(f"✅ Response Types: {', '.join(chat_results['response_types'])}")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Integration test failed: {e}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    """Main test runner"""
    # Check environment setup
    required_vars = ["SUPABASE_URL", "SUPABASE_ANON_KEY", "TEST_USER_EMAIL", "TEST_USER_PASSWORD"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease add these to your .env file:")
        print("TEST_USER_EMAIL=your-test-email@example.com")
        print("TEST_USER_PASSWORD=your-test-password")
        return False
    
    # Run integration test
    test = APIGatewayIntegrationTest()
    return await test.run_full_test()


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)


# Pytest integration for automated testing
@pytest.mark.asyncio
async def test_integration():
    """Pytest wrapper for integration test"""
    test = APIGatewayIntegrationTest()
    success = await test.run_full_test()
    assert success, "Integration test failed"


@pytest.mark.asyncio  
async def test_auth_only():
    """Test authentication only"""
    auth = SupabaseAuth()
    token = await auth.get_access_token()
    assert token, "Failed to get access token"
    assert len(token) > 20, "Access token seems too short"


@pytest.mark.asyncio
async def test_session_only():
    """Test session creation only"""
    test = APIGatewayIntegrationTest()
    await test.setup()
    session_id = await test.test_session_creation()
    assert session_id, "Failed to create session"
    await test.test_session_cleanup(session_id)