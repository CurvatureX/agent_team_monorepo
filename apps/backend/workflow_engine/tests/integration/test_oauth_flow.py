"""
End-to-end integration tests for OAuth2 authorization flow.

This module tests the complete OAuth2 flow including:
- Authorization URL generation
- State management and validation
- Token exchange and storage
- Token refresh mechanisms
- Cross-service integration
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
import uuid

from workflow_engine.services.oauth2_handler import OAuth2Handler
from workflow_engine.services.credential_service import CredentialService
from workflow_engine.models.credential import OAuth2Credential
from workflow_engine.core.config import get_settings


@pytest.fixture
def mock_settings():
    """Mock settings for OAuth2 configuration."""
    settings = MagicMock()
    settings.get_oauth2_config.return_value = {
        "google_calendar": {
            "client_id": "test_google_client_id",
            "client_secret": "test_google_client_secret",
            "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "scopes": ["https://www.googleapis.com/auth/calendar.events"]
        },
        "github": {
            "client_id": "test_github_client_id",
            "client_secret": "test_github_client_secret",
            "auth_url": "https://github.com/login/oauth/authorize",
            "token_url": "https://github.com/login/oauth/access_token",
            "scopes": ["repo", "read:user"]
        },
        "slack": {
            "client_id": "test_slack_client_id",
            "client_secret": "test_slack_client_secret",
            "auth_url": "https://slack.com/oauth/v2/authorize",
            "token_url": "https://slack.com/api/oauth.v2.access",
            "scopes": ["chat:write", "channels:read"]
        }
    }
    return settings


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for state management."""
    redis_client = AsyncMock()
    redis_client.set = AsyncMock()
    redis_client.get = AsyncMock()
    redis_client.delete = AsyncMock()
    return redis_client


@pytest.fixture
def mock_credential_service():
    """Mock credential service."""
    service = AsyncMock(spec=CredentialService)
    service.store_credential = AsyncMock()
    service.get_credential = AsyncMock()
    service.update_credential = AsyncMock()
    return service


class TestOAuth2FlowE2E:
    """End-to-end tests for OAuth2 authorization flow."""
    
    @pytest.mark.asyncio
    async def test_complete_google_calendar_oauth_flow(self, mock_settings, mock_redis_client, mock_credential_service):
        """Test complete OAuth2 flow for Google Calendar."""
        
        with patch('workflow_engine.core.config.get_settings', return_value=mock_settings):
            with patch('workflow_engine.services.oauth2_handler.get_redis_client', return_value=mock_redis_client):
                
                handler = OAuth2Handler()
                handler.credential_service = mock_credential_service
                
                user_id = "test_user_123"
                provider = "google_calendar"
                
                # Step 1: Generate authorization URL
                auth_url = await handler.generate_auth_url(
                    provider=provider,
                    user_id=user_id,
                    scopes=["https://www.googleapis.com/auth/calendar.events"]
                )
                
                # Verify authorization URL structure
                assert "https://accounts.google.com/o/oauth2/v2/auth" in auth_url
                assert "client_id=test_google_client_id" in auth_url
                assert "scope=https%3A//www.googleapis.com/auth/calendar.events" in auth_url
                assert "response_type=code" in auth_url
                assert "state=" in auth_url
                
                # Extract state from URL for later verification
                state_param = None
                for param in auth_url.split("&"):
                    if param.startswith("state="):
                        state_param = param.split("=")[1]
                        break
                
                assert state_param is not None
                
                # Verify state was stored in Redis
                mock_redis_client.set.assert_called()
                redis_call_args = mock_redis_client.set.call_args
                assert state_param in redis_call_args[0][0]  # Redis key contains state
                
                # Step 2: Mock the callback with authorization code
                mock_redis_client.get.return_value = f"{user_id}:{provider}".encode()
                
                # Mock token exchange response
                mock_token_response = {
                    "access_token": "test_access_token_123",
                    "refresh_token": "test_refresh_token_123",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                    "scope": "https://www.googleapis.com/auth/calendar.events"
                }
                
                with patch('httpx.AsyncClient.post') as mock_post:
                    mock_response = MagicMock()
                    mock_response.json.return_value = mock_token_response
                    mock_response.raise_for_status.return_value = None
                    mock_post.return_value = mock_response
                    
                    # Exchange authorization code for tokens
                    credentials = await handler.exchange_code_for_tokens(
                        provider=provider,
                        code="test_authorization_code",
                        state=state_param
                    )
                    
                    # Verify credentials structure
                    assert credentials.provider == provider
                    assert credentials.access_token == "test_access_token_123"
                    assert credentials.refresh_token == "test_refresh_token_123"
                    assert credentials.expires_at > datetime.now().timestamp()
                    
                    # Verify token exchange request
                    mock_post.assert_called_once()
                    post_call_args = mock_post.call_args
                    assert post_call_args[0][0] == "https://oauth2.googleapis.com/token"
                    
                    # Verify credential was stored
                    mock_credential_service.store_credential.assert_called_once()
                    store_call_args = mock_credential_service.store_credential.call_args
                    assert store_call_args[0][0] == user_id
                    assert store_call_args[0][1] == provider
    
    @pytest.mark.asyncio
    async def test_github_oauth_flow_with_different_scopes(self, mock_settings, mock_redis_client, mock_credential_service):
        """Test OAuth2 flow for GitHub with custom scopes."""
        
        with patch('workflow_engine.core.config.get_settings', return_value=mock_settings):
            with patch('workflow_engine.services.oauth2_handler.get_redis_client', return_value=mock_redis_client):
                
                handler = OAuth2Handler()
                handler.credential_service = mock_credential_service
                
                user_id = "github_user_456"
                provider = "github"
                custom_scopes = ["repo", "read:user", "write:repo_hook"]
                
                # Generate authorization URL with custom scopes
                auth_url = await handler.generate_auth_url(
                    provider=provider,
                    user_id=user_id,
                    scopes=custom_scopes
                )
                
                # Verify GitHub-specific URL structure
                assert "https://github.com/login/oauth/authorize" in auth_url
                assert "client_id=test_github_client_id" in auth_url
                assert "repo" in auth_url
                assert "read%3Auser" in auth_url
                assert "write%3Arepo_hook" in auth_url
                
                # Mock successful token exchange
                mock_redis_client.get.return_value = f"{user_id}:{provider}".encode()
                
                mock_github_response = {
                    "access_token": "github_access_token_789",
                    "token_type": "token",
                    "scope": "repo,read:user,write:repo_hook"
                }
                
                with patch('httpx.AsyncClient.post') as mock_post:
                    mock_response = MagicMock()
                    mock_response.json.return_value = mock_github_response
                    mock_response.raise_for_status.return_value = None
                    mock_post.return_value = mock_response
                    
                    credentials = await handler.exchange_code_for_tokens(
                        provider=provider,
                        code="github_auth_code",
                        state="test_state"
                    )
                    
                    assert credentials.provider == provider
                    assert credentials.access_token == "github_access_token_789"
                    assert "repo,read:user,write:repo_hook" in credentials.credential_data["scope"]
    
    @pytest.mark.asyncio
    async def test_slack_oauth_flow_with_bot_token(self, mock_settings, mock_redis_client, mock_credential_service):
        """Test OAuth2 flow for Slack with bot token handling."""
        
        with patch('workflow_engine.core.config.get_settings', return_value=mock_settings):
            with patch('workflow_engine.services.oauth2_handler.get_redis_client', return_value=mock_redis_client):
                
                handler = OAuth2Handler()
                handler.credential_service = mock_credential_service
                
                user_id = "slack_user_789"
                provider = "slack"
                
                # Generate Slack authorization URL
                auth_url = await handler.generate_auth_url(
                    provider=provider,
                    user_id=user_id,
                    scopes=["chat:write", "channels:read"]
                )
                
                # Verify Slack-specific URL structure
                assert "https://slack.com/oauth/v2/authorize" in auth_url
                assert "client_id=test_slack_client_id" in auth_url
                assert "chat%3Awrite" in auth_url
                assert "channels%3Aread" in auth_url
                
                # Mock Slack OAuth2 response (includes both user and bot tokens)
                mock_redis_client.get.return_value = f"{user_id}:{provider}".encode()
                
                mock_slack_response = {
                    "ok": True,
                    "access_token": "xoxp-user-token",
                    "token_type": "bearer",
                    "scope": "chat:write,channels:read",
                    "bot_user_id": "U1234567890",
                    "authed_user": {
                        "id": "U0987654321",
                        "scope": "chat:write,channels:read",
                        "access_token": "xoxp-user-access-token"
                    },
                    "bot": {
                        "bot_user_id": "U1234567890",
                        "bot_access_token": "xoxb-bot-access-token"
                    }
                }
                
                with patch('httpx.AsyncClient.post') as mock_post:
                    mock_response = MagicMock()
                    mock_response.json.return_value = mock_slack_response
                    mock_response.raise_for_status.return_value = None
                    mock_post.return_value = mock_response
                    
                    credentials = await handler.exchange_code_for_tokens(
                        provider=provider,
                        code="slack_auth_code",
                        state="test_state"
                    )
                    
                    assert credentials.provider == provider
                    # Should use bot token for API operations
                    assert credentials.access_token == "xoxb-bot-access-token"
                    assert credentials.credential_data["bot_user_id"] == "U1234567890"
    
    @pytest.mark.asyncio
    async def test_oauth_state_validation_and_security(self, mock_settings, mock_redis_client, mock_credential_service):
        """Test OAuth2 state validation and security measures."""
        
        with patch('workflow_engine.core.config.get_settings', return_value=mock_settings):
            with patch('workflow_engine.services.oauth2_handler.get_redis_client', return_value=mock_redis_client):
                
                handler = OAuth2Handler()
                handler.credential_service = mock_credential_service
                
                user_id = "security_test_user"
                provider = "google_calendar"
                
                # Generate authorization URL
                auth_url = await handler.generate_auth_url(
                    provider=provider,
                    user_id=user_id,
                    scopes=["https://www.googleapis.com/auth/calendar.events"]
                )
                
                # Extract state parameter
                state_param = None
                for param in auth_url.split("&"):
                    if param.startswith("state="):
                        state_param = param.split("=")[1]
                        break
                
                # Test 1: Valid state
                mock_redis_client.get.return_value = f"{user_id}:{provider}".encode()
                
                with patch('httpx.AsyncClient.post') as mock_post:
                    mock_response = MagicMock()
                    mock_response.json.return_value = {
                        "access_token": "valid_token",
                        "refresh_token": "valid_refresh",
                        "expires_in": 3600
                    }
                    mock_response.raise_for_status.return_value = None
                    mock_post.return_value = mock_response
                    
                    # Should succeed with valid state
                    credentials = await handler.exchange_code_for_tokens(
                        provider=provider,
                        code="test_code",
                        state=state_param
                    )
                    assert credentials is not None
                
                # Test 2: Invalid state (CSRF attack simulation)
                mock_redis_client.get.return_value = None  # State not found in Redis
                
                with pytest.raises(Exception) as exc_info:
                    await handler.exchange_code_for_tokens(
                        provider=provider,
                        code="test_code",
                        state="invalid_state_parameter"
                    )
                assert "invalid" in str(exc_info.value).lower() or "state" in str(exc_info.value).lower()
                
                # Test 3: Expired state
                wrong_user_data = f"different_user:{provider}".encode()
                mock_redis_client.get.return_value = wrong_user_data
                
                with pytest.raises(Exception) as exc_info:
                    await handler.exchange_code_for_tokens(
                        provider=provider,
                        code="test_code",
                        state=state_param
                    )
                # Should fail due to user mismatch
    
    @pytest.mark.asyncio
    async def test_token_refresh_mechanism(self, mock_settings, mock_redis_client, mock_credential_service):
        """Test OAuth2 token refresh mechanism."""
        
        with patch('workflow_engine.core.config.get_settings', return_value=mock_settings):
            with patch('workflow_engine.services.oauth2_handler.get_redis_client', return_value=mock_redis_client):
                
                handler = OAuth2Handler()
                handler.credential_service = mock_credential_service
                
                provider = "google_calendar"
                
                # Create expired credentials
                expired_credentials = OAuth2Credential()
                expired_credentials.provider = provider
                expired_credentials.access_token = "expired_access_token"
                expired_credentials.refresh_token = "valid_refresh_token"
                expired_credentials.expires_at = int((datetime.now() - timedelta(hours=1)).timestamp())
                
                # Mock refresh token response
                mock_refresh_response = {
                    "access_token": "new_access_token_123",
                    "expires_in": 3600,
                    "token_type": "Bearer"
                }
                
                with patch('httpx.AsyncClient.post') as mock_post:
                    mock_response = MagicMock()
                    mock_response.json.return_value = mock_refresh_response
                    mock_response.raise_for_status.return_value = None
                    mock_post.return_value = mock_response
                    
                    # Refresh the token
                    refreshed_credentials = await handler.refresh_access_token(
                        refresh_token="valid_refresh_token",
                        provider=provider
                    )
                    
                    # Verify refreshed credentials
                    assert refreshed_credentials.access_token == "new_access_token_123"
                    assert refreshed_credentials.expires_at > datetime.now().timestamp()
                    
                    # Verify refresh request was made correctly
                    mock_post.assert_called_once()
                    post_call_args = mock_post.call_args
                    request_data = post_call_args[1]["data"]
                    assert request_data["grant_type"] == "refresh_token"
                    assert request_data["refresh_token"] == "valid_refresh_token"
    
    @pytest.mark.asyncio
    async def test_concurrent_oauth_flows(self, mock_settings, mock_redis_client, mock_credential_service):
        """Test concurrent OAuth2 flows for multiple users/providers."""
        
        with patch('workflow_engine.core.config.get_settings', return_value=mock_settings):
            with patch('workflow_engine.services.oauth2_handler.get_redis_client', return_value=mock_redis_client):
                
                handler = OAuth2Handler()
                handler.credential_service = mock_credential_service
                
                # Create multiple concurrent authorization URL generations
                auth_tasks = []
                
                users_and_providers = [
                    ("user1", "google_calendar"),
                    ("user2", "github"),
                    ("user3", "slack"),
                    ("user4", "google_calendar"),
                    ("user5", "github")
                ]
                
                start_time = datetime.now()
                
                for user_id, provider in users_and_providers:
                    task = handler.generate_auth_url(
                        provider=provider,
                        user_id=user_id,
                        scopes=mock_settings.get_oauth2_config()[provider]["scopes"]
                    )
                    auth_tasks.append(task)
                
                auth_urls = await asyncio.gather(*auth_tasks)
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                # Verify all URLs were generated
                assert len(auth_urls) == 5
                
                # Verify each URL is correct for its provider
                for i, (user_id, provider) in enumerate(users_and_providers):
                    auth_url = auth_urls[i]
                    config = mock_settings.get_oauth2_config()[provider]
                    assert config["auth_url"] in auth_url
                    assert config["client_id"] in auth_url
                
                # Concurrent generation should be fast
                assert execution_time < 5.0
                
                # Verify Redis calls were made for each state
                assert mock_redis_client.set.call_count == 5
    
    @pytest.mark.asyncio
    async def test_oauth_error_handling(self, mock_settings, mock_redis_client, mock_credential_service):
        """Test OAuth2 error handling scenarios."""
        
        with patch('workflow_engine.core.config.get_settings', return_value=mock_settings):
            with patch('workflow_engine.services.oauth2_handler.get_redis_client', return_value=mock_redis_client):
                
                handler = OAuth2Handler()
                handler.credential_service = mock_credential_service
                
                provider = "google_calendar"
                user_id = "error_test_user"
                
                # Test 1: Network error during token exchange
                mock_redis_client.get.return_value = f"{user_id}:{provider}".encode()
                
                with patch('httpx.AsyncClient.post') as mock_post:
                    import httpx
                    mock_post.side_effect = httpx.ConnectError("Network error")
                    
                    with pytest.raises(Exception) as exc_info:
                        await handler.exchange_code_for_tokens(
                            provider=provider,
                            code="test_code",
                            state="test_state"
                        )
                    assert "network" in str(exc_info.value).lower() or "connect" in str(exc_info.value).lower()
                
                # Test 2: OAuth error response
                with patch('httpx.AsyncClient.post') as mock_post:
                    mock_response = MagicMock()
                    mock_response.json.return_value = {
                        "error": "invalid_grant",
                        "error_description": "The authorization code is invalid or expired"
                    }
                    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                        "400 Bad Request", request=MagicMock(), response=mock_response
                    )
                    mock_post.return_value = mock_response
                    
                    with pytest.raises(Exception) as exc_info:
                        await handler.exchange_code_for_tokens(
                            provider=provider,
                            code="invalid_code",
                            state="test_state"
                        )
                    assert "invalid_grant" in str(exc_info.value) or "400" in str(exc_info.value)
                
                # Test 3: Redis connection error
                mock_redis_client.get.side_effect = Exception("Redis connection failed")
                
                with pytest.raises(Exception) as exc_info:
                    await handler.exchange_code_for_tokens(
                        provider=provider,
                        code="test_code",
                        state="test_state"
                    )
                # Should fail due to Redis error


class TestOAuth2CrossServiceIntegration:
    """Test OAuth2 integration across different services."""
    
    @pytest.mark.asyncio
    async def test_multi_provider_user_workflow(self, mock_settings, mock_redis_client, mock_credential_service):
        """Test user authorizing multiple providers."""
        
        with patch('workflow_engine.core.config.get_settings', return_value=mock_settings):
            with patch('workflow_engine.services.oauth2_handler.get_redis_client', return_value=mock_redis_client):
                
                handler = OAuth2Handler()
                handler.credential_service = mock_credential_service
                
                user_id = "multi_provider_user"
                providers = ["google_calendar", "github", "slack"]
                
                # Store credentials for each provider
                stored_credentials = {}
                
                for provider in providers:
                    # Generate auth URL
                    auth_url = await handler.generate_auth_url(
                        provider=provider,
                        user_id=user_id,
                        scopes=mock_settings.get_oauth2_config()[provider]["scopes"]
                    )
                    
                    assert mock_settings.get_oauth2_config()[provider]["auth_url"] in auth_url
                    
                    # Mock token exchange
                    mock_redis_client.get.return_value = f"{user_id}:{provider}".encode()
                    
                    mock_token_response = {
                        "access_token": f"{provider}_access_token",
                        "refresh_token": f"{provider}_refresh_token",
                        "expires_in": 3600
                    }
                    
                    with patch('httpx.AsyncClient.post') as mock_post:
                        mock_response = MagicMock()
                        mock_response.json.return_value = mock_token_response
                        mock_response.raise_for_status.return_value = None
                        mock_post.return_value = mock_response
                        
                        credentials = await handler.exchange_code_for_tokens(
                            provider=provider,
                            code=f"{provider}_auth_code",
                            state="test_state"
                        )
                        
                        stored_credentials[provider] = credentials
                        assert credentials.provider == provider
                        assert credentials.access_token == f"{provider}_access_token"
                
                # Verify all providers were stored for the same user
                assert len(stored_credentials) == 3
                assert mock_credential_service.store_credential.call_count == 3
                
                # Verify each call was for the same user but different providers
                for call in mock_credential_service.store_credential.call_args_list:
                    assert call[0][0] == user_id  # Same user ID
                    assert call[0][1] in providers  # Valid provider
    
    @pytest.mark.asyncio
    async def test_oauth_state_isolation_between_users(self, mock_settings, mock_redis_client, mock_credential_service):
        """Test OAuth2 state isolation between different users."""
        
        with patch('workflow_engine.core.config.get_settings', return_value=mock_settings):
            with patch('workflow_engine.services.oauth2_handler.get_redis_client', return_value=mock_redis_client):
                
                handler = OAuth2Handler()
                handler.credential_service = mock_credential_service
                
                provider = "google_calendar"
                user1_id = "user_1"
                user2_id = "user_2"
                
                # Generate auth URLs for both users
                auth_url_1 = await handler.generate_auth_url(provider, user1_id, ["calendar"])
                auth_url_2 = await handler.generate_auth_url(provider, user2_id, ["calendar"])
                
                # Extract states
                state1 = None
                state2 = None
                
                for param in auth_url_1.split("&"):
                    if param.startswith("state="):
                        state1 = param.split("=")[1]
                        break
                
                for param in auth_url_2.split("&"):
                    if param.startswith("state="):
                        state2 = param.split("=")[1]
                        break
                
                # States should be different
                assert state1 != state2
                
                # Mock Redis responses for state validation
                def mock_redis_get(key):
                    if state1 in key:
                        return f"{user1_id}:{provider}".encode()
                    elif state2 in key:
                        return f"{user2_id}:{provider}".encode()
                    return None
                
                mock_redis_client.get.side_effect = mock_redis_get
                
                # Test that each user can only use their own state
                mock_token_response = {
                    "access_token": "test_token",
                    "refresh_token": "test_refresh",
                    "expires_in": 3600
                }
                
                with patch('httpx.AsyncClient.post') as mock_post:
                    mock_response = MagicMock()
                    mock_response.json.return_value = mock_token_response
                    mock_response.raise_for_status.return_value = None
                    mock_post.return_value = mock_response
                    
                    # User 1 with their state should succeed
                    credentials1 = await handler.exchange_code_for_tokens(
                        provider=provider,
                        code="user1_code",
                        state=state1
                    )
                    assert credentials1 is not None
                    
                    # User 2 with their state should succeed
                    credentials2 = await handler.exchange_code_for_tokens(
                        provider=provider,
                        code="user2_code",
                        state=state2
                    )
                    assert credentials2 is not None
                    
                    # User 1 with User 2's state should fail
                    with pytest.raises(Exception):
                        await handler.exchange_code_for_tokens(
                            provider=provider,
                            code="user1_code",
                            state=state2  # Wrong state
                        ) 