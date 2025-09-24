"""
Integration tests for API Gateway
测试真实的 /sessions 和 /chat/stream 接口
使用真实的 Supabase 账号进行认证
"""

import asyncio
import json
import os
from typing import Optional

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Load environment variables
load_dotenv("../.env")

# Skip tests in CI environment or when external services are unavailable
if os.getenv("CI") == "true" or os.getenv("SKIP_INTEGRATION_TESTS") == "true":
    pytest.skip(
        "Skipping integration tests in CI environment or when explicitly disabled",
        allow_module_level=True,
    )

# Test for Redis and database availability
try:
    import redis

    redis_client = redis.Redis(host="localhost", port=6379, db=0, socket_timeout=1)
    redis_client.ping()
    redis_available = True
except:
    redis_available = False

# For pre-commit and automated testing, skip integration tests by default
if not redis_available:
    pytest.skip("Skipping integration tests - Redis not available", allow_module_level=True)


class TestIntegration:
    """Integration tests for API Gateway with real authentication"""

    @classmethod
    def setup_class(cls):
        """Setup test class with authentication"""
        # Import app after environment variables are loaded
        from app.main import create_application

        cls.app = create_application()
        cls.client = TestClient(cls.app)

        # Get test credentials from environment
        cls.test_email = os.getenv("TEST_USER_EMAIL")
        cls.test_password = os.getenv("TEST_USER_PASSWORD")
        cls.supabase_url = os.getenv("SUPABASE_URL")
        cls.supabase_secret_key = os.getenv("SUPABASE_SECRET_KEY")

        # Verify environment variables
        assert cls.test_email, "TEST_USER_EMAIL not found in environment"
        assert cls.test_password, "TEST_USER_PASSWORD not found in environment"
        assert cls.supabase_url, "SUPABASE_URL not found in environment"
        assert cls.supabase_secret_key, "SUPABASE_SECRET_KEY not found in environment"

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

    def test_health_check(self):
        """Test basic health check endpoint"""
        response = self.client.get("/api/v1/public/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data

    def test_create_session(self):
        """Test creating a new session"""
        # Create a new session
        session_data = {
            "action": "create",
            "workflow_id": None,
        }
        response = self.client.post(
            "/api/v1/app/sessions", json=session_data, headers=self.auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        # Response format: {"message": "...", "session": {...}}
        assert "session" in data
        session = data["session"]
        assert "id" in session
        assert session["action"] == "create"

        # Store session_id for other tests
        self.__class__.session_id = session["id"]

    def test_get_sessions(self):
        """Test listing user sessions"""
        response = self.client.get("/api/v1/app/sessions", headers=self.auth_headers)
        assert response.status_code == 200

        data = response.json()
        # Response format: {"sessions": [...], "total": ...}
        assert "sessions" in data
        sessions = data["sessions"]
        assert isinstance(sessions, list)

        # Should have at least one session (from previous test)
        assert len(sessions) > 0

    def test_get_session_by_id(self):
        """Test getting a specific session"""
        # Use session_id from test_create_session
        if not hasattr(self.__class__, "session_id"):
            pytest.skip("No session_id available from previous test")

        response = self.client.get(
            f"/api/v1/app/sessions/{self.session_id}", headers=self.auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        # Response format could be {"session": {...}} or direct session object
        if "session" in data:
            session = data["session"]
        else:
            session = data
        assert session["id"] == self.session_id

    def test_chat_stream(self):
        """Test chat streaming endpoint"""
        # Create a session first
        session_data = {"action": "create", "workflow_id": None}
        session_response = self.client.post(
            "/api/v1/app/sessions", json=session_data, headers=self.auth_headers
        )
        assert session_response.status_code == 200
        session_data = session_response.json()
        session_id = (
            session_data["session"]["id"] if "session" in session_data else session_data["id"]
        )

        # Send a chat message
        chat_data = {
            "session_id": session_id,
            "user_message": "Hello, I want to create a simple workflow that sends me an email every morning at 8 AM",
        }

        # Use streaming response
        with self.client.stream(
            "POST", "/api/v1/app/chat/stream", json=chat_data, headers=self.auth_headers
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream"

            # Collect all SSE events
            events = []
            for line in response.iter_lines():
                if line.startswith("data: "):
                    data = line[6:]  # Remove "data: " prefix
                    if data != "[DONE]":
                        try:
                            event = json.loads(data)
                            events.append(event)
                        except json.JSONDecodeError:
                            pass

            # Verify we received events
            assert len(events) > 0

            # Check event structure
            for event in events:
                assert "type" in event
                assert event["type"] in ["message", "status", "error", "workflow"]

            # Should have at least one message event
            message_events = [e for e in events if e["type"] == "message"]
            assert len(message_events) > 0

    def test_chat_history(self):
        """Test getting chat history"""
        # Create a session and send a message first
        session_data = {"action": "create", "workflow_id": None}
        session_response = self.client.post(
            "/api/v1/app/sessions", json=session_data, headers=self.auth_headers
        )
        assert session_response.status_code == 200
        session_data = session_response.json()
        session_id = (
            session_data["session"]["id"] if "session" in session_data else session_data["id"]
        )

        # Send a chat message
        chat_data = {
            "session_id": session_id,
            "user_message": "Create a workflow for daily standup reminders",
        }
        with self.client.stream(
            "POST", "/api/v1/app/chat/stream", json=chat_data, headers=self.auth_headers
        ) as response:
            assert response.status_code == 200

        # Get chat history
        history_response = self.client.get(
            f"/api/v1/app/chat/history?session_id={session_id}", headers=self.auth_headers
        )
        assert history_response.status_code == 200

        data = history_response.json()
        # Response format could be {"messages": [...]} or direct list
        if isinstance(data, dict) and "messages" in data:
            messages = data["messages"]
        else:
            messages = data

        assert isinstance(messages, list)

        # Should have at least 2 messages (user message and assistant response)
        assert len(messages) >= 2

        # Verify message structure
        for message in messages:
            assert "role" in message
            assert "content" in message
            assert message["role"] in ["user", "assistant"]

    def test_unauthorized_access(self):
        """Test that endpoints require authentication"""
        # Test without auth header
        response = self.client.get("/api/v1/app/sessions")
        assert response.status_code == 401

        response = self.client.post("/api/v1/app/sessions", json={"action": "create"})
        assert response.status_code == 401

        # Test with invalid token
        invalid_headers = {"Authorization": "Bearer invalid_token"}
        response = self.client.get("/api/v1/app/sessions", headers=invalid_headers)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_concurrent_chat_streams(self):
        """Test handling multiple concurrent chat streams"""
        # Create multiple sessions
        session_ids = []
        for _ in range(3):
            session_data = {"action": "create", "workflow_id": None}
            response = self.client.post(
                "/api/v1/app/sessions", json=session_data, headers=self.auth_headers
            )
            assert response.status_code == 200
            resp_data = response.json()
            session_id = resp_data["session"]["id"] if "session" in resp_data else resp_data["id"]
            session_ids.append(session_id)

        # Send concurrent chat requests
        async def send_chat_request(session_id: str, message: str):
            async with AsyncClient(base_url="http://test") as ac:
                chat_data = {"session_id": session_id, "message": message}
                response = await ac.post(
                    "/api/v1/app/chat/stream", json=chat_data, headers=self.auth_headers
                )
                return response

        # Create tasks for concurrent requests
        tasks = [
            send_chat_request(session_ids[0], "Create a workflow for daily emails"),
            send_chat_request(session_ids[1], "Build a slack notification workflow"),
            send_chat_request(session_ids[2], "Setup a data backup workflow"),
        ]

        # Execute concurrently
        responses = await asyncio.gather(*tasks)

        # All should succeed
        for response in responses:
            assert response.status_code == 200

    def test_session_update(self):
        """Test updating a session"""
        # Create a session first
        session_data = {"action": "create", "workflow_id": None}
        create_response = self.client.post(
            "/api/v1/app/sessions", json=session_data, headers=self.auth_headers
        )
        assert create_response.status_code == 200
        create_data = create_response.json()
        session_id = create_data["session"]["id"] if "session" in create_data else create_data["id"]

        # Update the session
        update_data = {"status": "completed"}
        update_response = self.client.put(
            f"/api/v1/app/sessions/{session_id}",
            json=update_data,
            headers=self.auth_headers,
        )
        assert update_response.status_code == 200

        # Verify update
        data = update_response.json()
        # Response format could be {"session": {...}} or direct session object
        if "session" in data:
            session = data["session"]
        else:
            session = data
        assert session["status"] == "completed"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
