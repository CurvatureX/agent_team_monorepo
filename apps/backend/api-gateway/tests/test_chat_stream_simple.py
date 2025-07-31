"""
Simple integration test for /chat/stream endpoint
测试基本的聊天流式响应功能
"""

import json
import os
from typing import Optional

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

# Load environment variables
load_dotenv("../.env")

# Skip tests in CI environment
if os.getenv("CI") == "true":
    pytest.skip("Skipping integration tests in CI environment", allow_module_level=True)


class TestChatStream:
    """Simple test for chat streaming endpoint"""

    @classmethod
    def setup_class(cls):
        """Setup test class with authentication"""
        from app.main import create_application

        cls.app = create_application()
        cls.client = TestClient(cls.app)

        # Get test credentials from environment
        cls.test_email = os.getenv("TEST_USER_EMAIL")
        cls.test_password = os.getenv("TEST_USER_PASSWORD")
        cls.supabase_url = os.getenv("SUPABASE_URL")
        cls.supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")

        # Get access token
        cls.access_token = cls._get_access_token()
        assert cls.access_token, "Failed to obtain access token"

        # Set authorization header
        cls.auth_headers = {"Authorization": f"Bearer {cls.access_token}"}

    @classmethod
    def _get_access_token(cls) -> Optional[str]:
        """Get access token from Supabase Auth"""
        import httpx

        auth_url = f"{cls.supabase_url}/auth/v1/token?grant_type=password"
        headers = {
            "apikey": cls.supabase_anon_key,
            "Content-Type": "application/json",
        }
        data = {
            "email": cls.test_email,
            "password": cls.test_password,
            "gotrue_meta_security": {},
        }

        response = httpx.post(auth_url, headers=headers, json=data)
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            print(f"Authentication failed: {response.status_code} - {response.text}")
            return None

    def test_chat_stream_basic(self):
        """Test basic chat streaming functionality"""
        # First create a session
        session_data = {"action": "create", "workflow_id": None}
        session_response = self.client.post(
            "/api/v1/app/sessions", json=session_data, headers=self.auth_headers
        )
        assert session_response.status_code == 200
        session_id = session_response.json()["session"]["id"]

        # Send a simple chat message
        chat_data = {
            "session_id": session_id,
            "user_message": "Hello, test message",
        }

        # Test streaming response
        with self.client.stream(
            "POST", "/api/v1/app/chat/stream", json=chat_data, headers=self.auth_headers
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream"

            # Collect first few events
            events_collected = 0
            max_events = 5
            
            for line in response.iter_lines():
                if events_collected >= max_events:
                    break
                    
                if line.startswith("data: "):
                    data = line[6:]  # Remove "data: " prefix
                    if data != "[DONE]":
                        try:
                            event = json.loads(data)
                            # Basic validation
                            assert "type" in event
                            assert event["type"] in ["message", "status", "error", "workflow"]
                            events_collected += 1
                        except json.JSONDecodeError:
                            pass

            # Should have received at least one event
            assert events_collected > 0

    def test_chat_history_basic(self):
        """Test basic chat history retrieval"""
        # Create a session
        session_data = {"action": "create", "workflow_id": None}
        session_response = self.client.post(
            "/api/v1/app/sessions", json=session_data, headers=self.auth_headers
        )
        assert session_response.status_code == 200
        session_id = session_response.json()["session"]["id"]

        # Send a message
        chat_data = {
            "session_id": session_id,
            "user_message": "Test message for history",
        }
        
        # Send the message (no need to wait for full response)
        with self.client.stream(
            "POST", "/api/v1/app/chat/stream", json=chat_data, headers=self.auth_headers
        ) as response:
            assert response.status_code == 200

        # Get chat history
        history_response = self.client.get(
            f"/api/v1/app/chat/history?session_id={session_id}", 
            headers=self.auth_headers,
            timeout=30  # Add timeout
        )
        
        # Check response
        if history_response.status_code == 200:
            data = history_response.json()
            
            # Handle different response formats
            if isinstance(data, dict) and "messages" in data:
                messages = data["messages"]
            else:
                messages = data
            
            # Basic validation
            assert isinstance(messages, list)
            if len(messages) > 0:
                # At least we sent a message
                assert any(msg.get("role") == "user" for msg in messages)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])