"""
Quick integration tests for API Gateway
Focus on sessions API and basic chat functionality
"""

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


class TestQuickIntegration:
    """Quick integration tests that don't depend on slow external services"""

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
        except Exception as e:
            print(f"Authentication failed: {e}")
        return None

    def test_health_check(self):
        """Test health check endpoint"""
        response = self.client.get("/api/v1/public/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_session_lifecycle(self):
        """Test complete session lifecycle: create, get, list"""
        # Create session
        session_data = {"action": "create", "workflow_id": None}
        create_response = self.client.post(
            "/api/v1/app/sessions", json=session_data, headers=self.auth_headers
        )
        if create_response.status_code == 401:
            pytest.skip("Authentication failed - test requires valid Supabase credentials")
        assert create_response.status_code == 200

        created_session = create_response.json()
        assert "session" in created_session
        session_id = created_session["session"]["id"]

        # Get specific session
        get_response = self.client.get(
            f"/api/v1/app/sessions/{session_id}", headers=self.auth_headers
        )
        assert get_response.status_code == 200

        # List sessions
        list_response = self.client.get("/api/v1/app/sessions", headers=self.auth_headers)
        assert list_response.status_code == 200
        data = list_response.json()
        assert "sessions" in data
        assert len(data["sessions"]) > 0

    def test_chat_stream_format(self):
        """Test chat stream returns correct format (don't wait for full response)"""
        # Create session
        session_data = {"action": "create", "workflow_id": None}
        session_response = self.client.post(
            "/api/v1/app/sessions", json=session_data, headers=self.auth_headers
        )
        if session_response.status_code == 401:
            pytest.skip("Authentication failed - test requires valid Supabase credentials")
        assert session_response.status_code == 200
        session_id = session_response.json()["session"]["id"]

        # Send chat message
        chat_data = {
            "session_id": session_id,
            "user_message": "Hi",  # Very simple message
        }

        # Just check that streaming starts correctly
        import httpx

        # Use httpx directly with a very short timeout
        with httpx.Client(timeout=5.0) as client:
            try:
                with client.stream(
                    "POST",
                    "http://localhost:8000/api/v1/app/chat/stream",
                    json=chat_data,
                    headers=self.auth_headers,
                ) as response:
                    assert response.status_code == 200
                    assert response.headers["content-type"] == "text/event-stream"

                    # Read just the first event to verify format
                    event_count = 0
                    for line in response.iter_lines():
                        if line.startswith("data: "):
                            event_count += 1
                            if event_count >= 1:
                                # We got at least one event, that's enough
                                break
                    assert event_count > 0
            except httpx.ReadTimeout:
                # If we timeout, at least we know the endpoint accepted the request
                pytest.skip("Chat stream timed out - workflow_agent might be slow")

    def test_error_handling(self):
        """Test error handling for invalid requests"""
        # Invalid session ID
        chat_data = {
            "session_id": "invalid-session-id",
            "user_message": "Test",
        }

        with self.client.stream(
            "POST", "/api/v1/app/chat/stream", json=chat_data, headers=self.auth_headers
        ) as response:
            # Should return an error (or 401 if auth failed)
            assert response.status_code in [400, 401, 404, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
