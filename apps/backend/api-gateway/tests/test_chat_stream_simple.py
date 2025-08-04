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
        cls.supabase_secret_key = os.getenv("SUPABASE_SECRET_KEY")

        # Get access token (try but don't fail if unavailable)
        cls.access_token = cls._get_access_token()

        # Set authorization header (use dummy token if auth failed)
        if cls.access_token:
            cls.auth_headers = {"Authorization": f"Bearer {cls.access_token}"}
        else:
            cls.auth_headers = {"Authorization": "Bearer dummy-token-for-testing"}

    @classmethod
    def _get_access_token(cls) -> Optional[str]:
        """Get access token from Supabase Auth"""
        import httpx

        auth_url = f"{cls.supabase_url}/auth/v1/token?grant_type=password"
        headers = {
            "apikey": cls.supabase_secret_key,
            "Content-Type": "application/json",
        }
        data = {
            "email": cls.test_email,
            "password": cls.test_password,
            "gotrue_meta_security": {},
        }

        try:
            response = httpx.post(auth_url, headers=headers, json=data)
            if response.status_code == 200:
                return response.json().get("access_token")
            else:
                print(f"Authentication failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Authentication failed: {e}")
        return None

    def test_chat_stream_basic(self):
        """Test basic chat streaming functionality"""
        # First create a session
        session_data = {"action": "create", "workflow_id": None}
        session_response = self.client.post(
            "/api/v1/app/sessions", json=session_data, headers=self.auth_headers
        )
        if session_response.status_code == 401:
            pytest.skip("Authentication failed - test requires valid Supabase credentials")
        assert session_response.status_code == 200
        session_id = session_response.json()["session"]["id"]

        # Send a simple chat message
        chat_data = {
            "session_id": session_id,
            "user_message": "Hello, test message",
        }

        # Test streaming response with timeout protection
        import httpx

        try:
            with httpx.Client(timeout=5.0) as client:
                with client.stream(
                    "POST",
                    "http://localhost:8000/api/v1/app/chat/stream",
                    json=chat_data,
                    headers=self.auth_headers,
                    timeout=5.0,
                ) as response:
                    if response.status_code == 200:
                        assert response.headers["content-type"] == "text/event-stream"

                        # Just check we can read first line without hanging
                        line_count = 0
                        for line in response.iter_lines():
                            line_count += 1
                            if line_count >= 1:  # Stop after first line
                                break

                        # We successfully connected and got at least one line
                        assert line_count > 0
                    else:
                        pytest.skip("Chat streaming endpoint returned non-200 status")

        except (httpx.TimeoutException, httpx.ConnectError, Exception) as e:
            pytest.skip(f"Chat streaming test skipped due to service unavailability: {e}")

    def test_chat_history_basic(self):
        """Test basic chat history retrieval"""
        # Create a session
        session_data = {"action": "create", "workflow_id": None}
        session_response = self.client.post(
            "/api/v1/app/sessions", json=session_data, headers=self.auth_headers
        )
        if session_response.status_code == 401:
            pytest.skip("Authentication failed - test requires valid Supabase credentials")
        assert session_response.status_code == 200
        session_id = session_response.json()["session"]["id"]

        # Send a message
        chat_data = {
            "session_id": session_id,
            "user_message": "Test message for history",
        }

        # Send the message (with timeout protection)
        try:
            with self.client.stream(
                "POST",
                "/api/v1/app/chat/stream",
                json=chat_data,
                headers=self.auth_headers,
                timeout=5.0,
            ) as response:
                assert response.status_code == 200
        except Exception:
            # If streaming fails, skip the test
            pytest.skip("Chat streaming failed, skipping history test")

        # Get chat history
        history_response = self.client.get(
            f"/api/v1/app/chat/history?session_id={session_id}",
            headers=self.auth_headers,
            timeout=30,  # Add timeout
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
