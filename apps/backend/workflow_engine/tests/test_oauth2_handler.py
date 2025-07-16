"""
Unit tests for OAuth2Handler service.

Tests OAuth2 authorization flow including URL generation, state management,
token exchange, and token refresh for multiple providers.
"""

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from urllib.parse import urlparse, parse_qs

import httpx

from workflow_engine.services.oauth2_handler import (
    OAuth2Handler,
    OAuth2Error,
    OAuth2StateError,
    OAuth2TokenError,
    OAuth2ConfigurationError,
    get_oauth2_handler
)
from workflow_engine.models.credential import OAuth2Credential


class TestOAuth2Handler:
    """Test cases for OAuth2Handler."""
    
    @pytest.fixture
    def handler(self):
        """Create OAuth2Handler instance for testing."""
        return OAuth2Handler()
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings with OAuth2 configuration."""
        settings = Mock()
        settings.api_timeout_connect = 5
        settings.api_timeout_read = 30
        settings.oauth2_state_expiry = 1800
        
        # Mock OAuth2 configurations
        def get_oauth2_config(provider):
            configs = {
                "google_calendar": {
                    "client_id": "google_test_client_id",
                    "client_secret": "google_test_client_secret",
                    "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
                    "token_url": "https://oauth2.googleapis.com/token",
                    "scopes": ["https://www.googleapis.com/auth/calendar.events"],
                },
                "github": {
                    "client_id": "github_test_client_id", 
                    "client_secret": "github_test_client_secret",
                    "auth_url": "https://github.com/login/oauth/authorize",
                    "token_url": "https://github.com/login/oauth/access_token",
                    "scopes": ["repo", "read:user"],
                },
                "slack": {
                    "client_id": "slack_test_client_id",
                    "client_secret": "slack_test_client_secret", 
                    "auth_url": "https://slack.com/oauth/v2/authorize",
                    "token_url": "https://slack.com/api/oauth.v2.access",
                    "scopes": ["chat:write", "channels:read"],
                }
            }
            return configs[provider]
        
        settings.get_oauth2_config = get_oauth2_config
        settings.validate_oauth2_providers = Mock(return_value=[])
        return settings
    
    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client for state management."""
        redis_client = AsyncMock()
        redis_client.store_oauth_state = AsyncMock(return_value="test_state_12345")
        redis_client.get_oauth_state = AsyncMock(return_value={
            "user_id": "test_user",
            "provider": "google_calendar",
            "created_at": str(int(datetime.utcnow().timestamp())),
            "redirect_uri": "https://example.com/callback",
            "scopes": ["https://www.googleapis.com/auth/calendar.events"]
        })
        redis_client.delete_oauth_state = AsyncMock(return_value=True)
        return redis_client
    
    @pytest.mark.asyncio
    async def test_generate_auth_url_google_calendar(self, handler, mock_settings, mock_redis_client):
        """Test generating Google Calendar authorization URL."""
        with patch('workflow_engine.services.oauth2_handler.get_settings', return_value=mock_settings), \
             patch('workflow_engine.services.oauth2_handler.get_redis_client', return_value=mock_redis_client):
            
            auth_url = await handler.generate_auth_url(
                provider="google_calendar",
                user_id="test_user",
                redirect_uri="https://example.com/callback"
            )
            
            # Verify URL structure
            parsed_url = urlparse(auth_url)
            assert parsed_url.scheme == "https"
            assert parsed_url.netloc == "accounts.google.com"
            assert parsed_url.path == "/o/oauth2/v2/auth"
            
            # Verify query parameters
            params = parse_qs(parsed_url.query)
            assert params["client_id"][0] == "google_test_client_id"
            assert params["redirect_uri"][0] == "https://example.com/callback"
            assert params["response_type"][0] == "code"
            assert params["state"][0] == "test_state_12345"
            assert "calendar.events" in params["scope"][0]
            assert params["access_type"][0] == "offline"
            assert params["prompt"][0] == "consent"
            
            # Verify Redis state storage was called
            mock_redis_client.store_oauth_state.assert_called_once_with(
                user_id="test_user",
                provider="google_calendar",
                redirect_uri="https://example.com/callback",
                scopes=["https://www.googleapis.com/auth/calendar.events"]
            )
    
    @pytest.mark.asyncio
    async def test_generate_auth_url_github(self, handler, mock_settings, mock_redis_client):
        """Test generating GitHub authorization URL."""
        with patch('workflow_engine.services.oauth2_handler.get_settings', return_value=mock_settings), \
             patch('workflow_engine.services.oauth2_handler.get_redis_client', return_value=mock_redis_client):
            
            auth_url = await handler.generate_auth_url(
                provider="github",
                user_id="test_user",
                redirect_uri="https://example.com/callback",
                scopes=["repo"]
            )
            
            # Verify URL structure
            parsed_url = urlparse(auth_url)
            assert parsed_url.netloc == "github.com"
            assert parsed_url.path == "/login/oauth/authorize"
            
            # Verify query parameters
            params = parse_qs(parsed_url.query)
            assert params["client_id"][0] == "github_test_client_id"
            assert params["scope"][0] == "repo"
    
    @pytest.mark.asyncio
    async def test_generate_auth_url_slack(self, handler, mock_settings, mock_redis_client):
        """Test generating Slack authorization URL."""
        with patch('workflow_engine.services.oauth2_handler.get_settings', return_value=mock_settings), \
             patch('workflow_engine.services.oauth2_handler.get_redis_client', return_value=mock_redis_client):
            
            auth_url = await handler.generate_auth_url(
                provider="slack",
                user_id="test_user", 
                redirect_uri="https://example.com/callback"
            )
            
            # Verify URL structure
            parsed_url = urlparse(auth_url)
            assert parsed_url.netloc == "slack.com"
            assert parsed_url.path == "/oauth/v2/authorize"
            
            # Verify Slack-specific parameters
            params = parse_qs(parsed_url.query)
            assert "user_scope" in params
    
    @pytest.mark.asyncio
    async def test_generate_auth_url_invalid_provider(self, handler, mock_settings):
        """Test authorization URL generation with invalid provider."""
        with patch('workflow_engine.services.oauth2_handler.get_settings', return_value=mock_settings):
            mock_settings.get_oauth2_config.side_effect = ValueError("Unknown provider")
            
            with pytest.raises(OAuth2ConfigurationError):
                await handler.generate_auth_url(
                    provider="invalid_provider",
                    user_id="test_user",
                    redirect_uri="https://example.com/callback"
                )
    
    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_success(self, handler, mock_settings, mock_redis_client):
        """Test successful token exchange."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "calendar.events"
        }
        
        with patch('workflow_engine.services.oauth2_handler.get_settings', return_value=mock_settings), \
             patch('workflow_engine.services.oauth2_handler.get_redis_client', return_value=mock_redis_client), \
             patch.object(handler, '_make_token_request', return_value=mock_response), \
             patch.object(handler, '_parse_token_response', return_value=mock_response.json.return_value):
            
            credential = await handler.exchange_code_for_tokens(
                provider="google_calendar",
                code="test_auth_code",
                state="test_state_12345",
                redirect_uri="https://example.com/callback"
            )
            
            # Verify credential
            assert isinstance(credential, OAuth2Credential)
            assert credential.access_token == "test_access_token"
            assert credential.refresh_token == "test_refresh_token"
            assert credential.token_type == "Bearer"
            assert credential.expires_in == 3600
            assert credential.provider == "google_calendar"
            
            # Verify state was retrieved and deleted
            mock_redis_client.get_oauth_state.assert_called_once_with("test_state_12345")
            mock_redis_client.delete_oauth_state.assert_called_once_with("test_state_12345")
    
    @pytest.mark.asyncio
    async def test_exchange_code_invalid_state(self, handler, mock_settings, mock_redis_client):
        """Test token exchange with invalid state."""
        mock_redis_client.get_oauth_state.return_value = None
        
        with patch('workflow_engine.services.oauth2_handler.get_settings', return_value=mock_settings), \
             patch('workflow_engine.services.oauth2_handler.get_redis_client', return_value=mock_redis_client):
            
            with pytest.raises(OAuth2StateError, match="Invalid or expired OAuth2 state"):
                await handler.exchange_code_for_tokens(
                    provider="google_calendar",
                    code="test_auth_code", 
                    state="invalid_state",
                    redirect_uri="https://example.com/callback"
                )
    
    @pytest.mark.asyncio
    async def test_exchange_code_provider_mismatch(self, handler, mock_settings, mock_redis_client):
        """Test token exchange with provider mismatch."""
        mock_redis_client.get_oauth_state.return_value = {
            "user_id": "test_user",
            "provider": "github",  # Different provider
            "created_at": str(int(datetime.utcnow().timestamp()))
        }
        
        with patch('workflow_engine.services.oauth2_handler.get_settings', return_value=mock_settings), \
             patch('workflow_engine.services.oauth2_handler.get_redis_client', return_value=mock_redis_client):
            
            with pytest.raises(OAuth2StateError, match="State provider mismatch"):
                await handler.exchange_code_for_tokens(
                    provider="google_calendar",
                    code="test_auth_code",
                    state="test_state_12345", 
                    redirect_uri="https://example.com/callback"
                )
    
    @pytest.mark.asyncio
    async def test_refresh_access_token_success(self, handler, mock_settings):
        """Test successful token refresh."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "token_type": "Bearer",
            "expires_in": 3600
        }
        
        with patch('workflow_engine.services.oauth2_handler.get_settings', return_value=mock_settings), \
             patch.object(handler, '_make_token_request', return_value=mock_response), \
             patch.object(handler, '_parse_token_response', return_value=mock_response.json.return_value):
            
            credential = await handler.refresh_access_token(
                refresh_token="test_refresh_token",
                provider="google_calendar"
            )
            
            # Verify new credential
            assert credential.access_token == "new_access_token"
            assert credential.refresh_token == "test_refresh_token"  # Preserved
            assert credential.token_type == "Bearer"
            assert credential.expires_in == 3600
    
    @pytest.mark.asyncio
    async def test_refresh_access_token_http_error(self, handler, mock_settings):
        """Test token refresh with HTTP error."""
        with patch('workflow_engine.services.oauth2_handler.get_settings', return_value=mock_settings), \
             patch.object(handler, '_make_token_request') as mock_request:
            
            mock_request.side_effect = httpx.HTTPStatusError(
                "Token refresh failed",
                request=Mock(),
                response=Mock(status_code=400)
            )
            
            with pytest.raises(OAuth2TokenError, match="Token refresh request failed"):
                await handler.refresh_access_token(
                    refresh_token="invalid_refresh_token",
                    provider="google_calendar"
                )
    
    @pytest.mark.asyncio
    async def test_is_token_expired_not_expired(self, handler):
        """Test token expiration check for valid token."""
        credential = OAuth2Credential(
            access_token="test_token",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            provider="google_calendar"
        )
        
        is_expired = await handler.is_token_expired(credential)
        assert not is_expired
    
    @pytest.mark.asyncio
    async def test_is_token_expired_expired(self, handler):
        """Test token expiration check for expired token."""
        credential = OAuth2Credential(
            access_token="test_token",
            expires_at=datetime.utcnow() - timedelta(minutes=1),
            provider="google_calendar"
        )
        
        is_expired = await handler.is_token_expired(credential)
        assert is_expired
    
    @pytest.mark.asyncio
    async def test_is_token_expired_no_expiry(self, handler):
        """Test token expiration check for token without expiry."""
        credential = OAuth2Credential(
            access_token="test_token",
            expires_at=None,
            provider="google_calendar"
        )
        
        is_expired = await handler.is_token_expired(credential)
        assert not is_expired
    
    @pytest.mark.asyncio
    async def test_parse_token_response_github(self, handler):
        """Test GitHub token response parsing (form-encoded)."""
        mock_response = Mock()
        mock_response.headers = {"content-type": "application/x-www-form-urlencoded"}
        mock_response.text = "access_token=test_token&token_type=bearer&scope=repo"
        
        result = await handler._parse_token_response(mock_response, "github")
        
        assert result["access_token"] == "test_token"
        assert result["token_type"] == "bearer" 
        assert result["scope"] == "repo"
    
    @pytest.mark.asyncio
    async def test_parse_token_response_json(self, handler):
        """Test JSON token response parsing."""
        mock_response = Mock()
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "access_token": "test_token",
            "token_type": "Bearer"
        }
        
        result = await handler._parse_token_response(mock_response, "google_calendar")
        
        assert result["access_token"] == "test_token"
        assert result["token_type"] == "Bearer"
    
    def test_calculate_expires_at(self, handler):
        """Test expires_at calculation."""
        # Test with expires_in
        expires_at = handler._calculate_expires_at(3600)
        expected = datetime.utcnow() + timedelta(seconds=3600)
        assert abs((expires_at - expected).total_seconds()) < 1
        
        # Test with None
        expires_at = handler._calculate_expires_at(None)
        assert expires_at is None
    
    @pytest.mark.asyncio
    async def test_make_token_request_success(self, handler):
        """Test successful token request."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        
        with patch.object(handler.http_client, 'post', return_value=mock_response) as mock_post:
            result = await handler._make_token_request(
                "https://oauth2.googleapis.com/token",
                {"grant_type": "authorization_code", "code": "test_code"},
                "google_calendar"
            )
            
            assert result == mock_response
            mock_post.assert_called_once()
            
            # Verify headers
            call_args = mock_post.call_args
            headers = call_args[1]["headers"]
            assert headers["Content-Type"] == "application/x-www-form-urlencoded"
            assert headers["Accept"] == "application/json"
            assert "google_calendar" in headers["User-Agent"]


class TestOAuth2HandlerGlobal:
    """Test global OAuth2Handler instance management."""
    
    @pytest.mark.asyncio
    async def test_get_oauth2_handler_singleton(self):
        """Test global OAuth2Handler singleton pattern."""
        # Clear global instance first
        import workflow_engine.services.oauth2_handler as oauth2_module
        oauth2_module._oauth2_handler = None
        
        handler1 = await get_oauth2_handler()
        handler2 = await get_oauth2_handler()
        
        assert handler1 is handler2
        assert isinstance(handler1, OAuth2Handler)
    
    @pytest.mark.asyncio
    async def test_close_oauth2_handler(self):
        """Test closing global OAuth2Handler instance."""
        from workflow_engine.services.oauth2_handler import close_oauth2_handler
        
        # Get instance first
        handler = await get_oauth2_handler()
        
        # Mock close method
        with patch.object(handler, 'close') as mock_close:
            await close_oauth2_handler()
            mock_close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__]) 