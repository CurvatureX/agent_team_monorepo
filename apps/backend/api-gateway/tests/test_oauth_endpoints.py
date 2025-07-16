"""
Tests for OAuth2 API endpoints
"""

import pytest
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from ..routers.oauth import router as oauth_router
from ..core.grpc_client import WorkflowAgentClient

# Create test app
app = FastAPI()
app.include_router(oauth_router, prefix="/oauth2")

# Mock workflow client
mock_workflow_client = Mock(spec=WorkflowAgentClient)


@pytest.fixture
def client():
    """Create test client with mocked dependencies"""
    
    def get_mock_workflow_client():
        return mock_workflow_client
    
    app.dependency_overrides = {
        oauth_router.get_workflow_client: get_mock_workflow_client
    }
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clean up overrides
    app.dependency_overrides.clear()


class TestOAuth2AuthorizeEndpoint:
    """Test OAuth2 authorization URL generation endpoint"""
    
    def test_generate_auth_url_success(self, client):
        """Test successful authorization URL generation"""
        response = client.get(
            "/oauth2/authorize/google_calendar",
            params={"user_id": "test_user_123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "auth_url" in data
        assert "state" in data
        assert "google_calendar" in data["auth_url"]
        assert "test_user_123" in data["auth_url"]
    
    def test_generate_auth_url_with_scopes(self, client):
        """Test authorization URL generation with custom scopes"""
        response = client.get(
            "/oauth2/authorize/github",
            params={
                "user_id": "test_user_123",
                "scopes": "repo,user,admin:org"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "repo,user,admin:org" in data["auth_url"]
    
    def test_generate_auth_url_invalid_provider(self, client):
        """Test authorization URL generation with invalid provider"""
        response = client.get(
            "/oauth2/authorize/invalid_provider",
            params={"user_id": "test_user_123"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Unsupported provider" in data["detail"]
    
    def test_generate_auth_url_missing_user_id(self, client):
        """Test authorization URL generation without user_id"""
        response = client.get("/oauth2/authorize/google_calendar")
        
        assert response.status_code == 422  # Validation error


class TestOAuth2CallbackEndpoint:
    """Test OAuth2 callback processing endpoint"""
    
    def test_oauth_callback_success(self, client):
        """Test successful OAuth2 callback processing"""
        response = client.get(
            "/oauth2/callback/google_calendar",
            params={
                "code": "test_auth_code_123",
                "state": "state_test_user_123_google_calendar"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "Successfully authorized" in data["message"]
        assert "credential_id" in data
    
    def test_oauth_callback_with_error(self, client):
        """Test OAuth2 callback with error from provider"""
        response = client.get(
            "/oauth2/callback/slack",
            params={
                "error": "access_denied",
                "error_description": "User denied access",
                "state": "state_test_user_123_slack"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is False
        assert "OAuth2 authorization failed" in data["message"]
        assert "access_denied" in data["error"]
    
    def test_oauth_callback_invalid_provider(self, client):
        """Test OAuth2 callback with invalid provider"""
        response = client.get(
            "/oauth2/callback/invalid_provider",
            params={
                "code": "test_code",
                "state": "test_state"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Unsupported provider" in data["detail"]
    
    def test_oauth_callback_missing_params(self, client):
        """Test OAuth2 callback without required parameters"""
        response = client.get("/oauth2/callback/google_calendar")
        
        assert response.status_code == 422  # Validation error


class TestOAuth2ProvidersEndpoint:
    """Test OAuth2 providers listing endpoint"""
    
    def test_list_providers(self, client):
        """Test listing supported OAuth2 providers"""
        response = client.get("/oauth2/providers")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "providers" in data
        providers = data["providers"]
        
        # Check that all expected providers are present
        expected_providers = ["google_calendar", "github", "slack"]
        for provider in expected_providers:
            assert provider in providers
            assert "name" in providers[provider]
            assert "default_scopes" in providers[provider]
        
        # Check specific provider details
        assert providers["google_calendar"]["name"] == "Google Calendar"
        assert "https://www.googleapis.com/auth/calendar.events" in providers["google_calendar"]["default_scopes"]
        
        assert providers["github"]["name"] == "Github"
        assert "repo" in providers["github"]["default_scopes"]
        assert "user" in providers["github"]["default_scopes"]
        
        assert providers["slack"]["name"] == "Slack"
        assert "chat:write" in providers["slack"]["default_scopes"]


# Integration tests (to be run when gRPC services are available)
class TestOAuth2Integration:
    """Integration tests for OAuth2 endpoints with real services"""
    
    @pytest.mark.skip(reason="Requires gRPC services to be running")
    def test_full_oauth_flow_integration(self, client):
        """Test complete OAuth2 flow integration"""
        # This test will be enabled when OAuth2Handler and CredentialService are implemented
        pass
    
    @pytest.mark.skip(reason="Requires gRPC services to be running")
    def test_state_validation_integration(self, client):
        """Test OAuth2 state parameter validation with Redis"""
        # This test will be enabled when Redis state management is implemented
        pass 