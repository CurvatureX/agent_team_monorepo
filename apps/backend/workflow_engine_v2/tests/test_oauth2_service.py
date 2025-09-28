"""
Test OAuth2 service functionality for workflow_engine_v2.
"""
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from workflow_engine_v2.services.credential_encryption import CredentialEncryption
from workflow_engine_v2.services.oauth2_service import OAuth2ServiceV2, TokenResponse


@pytest.fixture
def oauth2_service():
    """Create OAuth2 service for testing."""
    return OAuth2ServiceV2()


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    client = MagicMock()
    client.table = MagicMock()
    return client


@pytest.mark.asyncio
async def test_google_token_exchange(oauth2_service):
    """Test Google OAuth token exchange."""
    with patch("aiohttp.ClientSession.post") as mock_post:
        # Mock successful token response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "access_token": "google_access_token",
            "refresh_token": "google_refresh_token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        mock_post.return_value.__aenter__.return_value = mock_response

        result = await oauth2_service.exchange_code_for_token(
            code="auth_code",
            client_id="google_client_id",
            redirect_uri="http://localhost:3000/callback",
            provider="google",
        )

        assert isinstance(result, TokenResponse)
        assert result.access_token == "google_access_token"
        assert result.refresh_token == "google_refresh_token"
        assert result.expires_in == 3600


@pytest.mark.asyncio
async def test_github_token_exchange(oauth2_service):
    """Test GitHub OAuth token exchange."""
    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = "access_token=github_token&token_type=Bearer"
        mock_post.return_value.__aenter__.return_value = mock_response

        result = await oauth2_service.exchange_code_for_token(
            code="auth_code",
            client_id="github_client_id",
            redirect_uri="http://localhost:3000/callback",
            provider="github",
        )

        assert result.access_token == "github_token"
        assert result.token_type == "Bearer"


@pytest.mark.asyncio
async def test_store_user_credentials(oauth2_service):
    """Test storing user credentials."""
    with patch.object(oauth2_service, "_client") as mock_client:
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.upsert.return_value.execute.return_value.data = [{"id": "stored"}]

        token_response = TokenResponse(
            access_token="test_token",
            refresh_token="test_refresh",
            expires_in=3600,
            token_type="Bearer",
        )

        result = await oauth2_service.store_user_credentials(
            user_id="user123", provider="google", token_response=token_response
        )

        assert result is True
        mock_table.upsert.assert_called_once()


@pytest.mark.asyncio
async def test_get_valid_token_fresh(oauth2_service):
    """Test getting a valid token that hasn't expired."""
    with patch.object(oauth2_service, "_client") as mock_client:
        from datetime import datetime, timedelta

        future_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {
                "encrypted_token": oauth2_service.encryption.encrypt("valid_token"),
                "expires_at": future_time,
            }
        ]

        token = await oauth2_service.get_valid_token("user123", "google")
        assert token == "valid_token"


@pytest.mark.asyncio
async def test_get_valid_token_refresh_needed(oauth2_service):
    """Test getting a valid token when refresh is needed."""
    with patch.object(oauth2_service, "_client") as mock_client:
        from datetime import datetime, timedelta

        past_time = (datetime.utcnow() - timedelta(hours=1)).isoformat()

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {
                "encrypted_token": oauth2_service.encryption.encrypt("expired_token"),
                "encrypted_refresh_token": oauth2_service.encryption.encrypt("refresh_token"),
                "expires_at": past_time,
            }
        ]

        with patch.object(oauth2_service, "refresh_token") as mock_refresh:
            mock_refresh.return_value = TokenResponse(
                access_token="refreshed_token",
                refresh_token="new_refresh_token",
                expires_in=3600,
                token_type="Bearer",
            )

            with patch.object(oauth2_service, "store_user_credentials") as mock_store:
                mock_store.return_value = True

                token = await oauth2_service.get_valid_token("user123", "google")
                assert token == "refreshed_token"
                mock_refresh.assert_called_once_with("refresh_token", "google")


@pytest.mark.asyncio
async def test_refresh_google_token(oauth2_service):
    """Test refreshing Google OAuth token."""
    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        mock_post.return_value.__aenter__.return_value = mock_response

        result = await oauth2_service.refresh_token("refresh_token", "google")

        assert result.access_token == "new_access_token"
        assert result.expires_in == 3600


def test_credential_encryption():
    """Test credential encryption and decryption."""
    encryption = CredentialEncryption()

    # Test string encryption
    original = "sensitive_data"
    encrypted = encryption.encrypt(original)
    decrypted = encryption.decrypt(encrypted)

    assert decrypted == original
    assert encrypted != original

    # Test dict encryption
    original_dict = {"token": "secret_token", "refresh": "refresh_token"}
    encrypted_dict = encryption.encrypt_dict(original_dict)
    decrypted_dict = encryption.decrypt_dict(encrypted_dict)

    assert decrypted_dict == original_dict
    assert encrypted_dict != original_dict


@pytest.mark.asyncio
async def test_unsupported_provider(oauth2_service):
    """Test handling of unsupported OAuth provider."""
    with pytest.raises(ValueError, match="Unsupported provider"):
        await oauth2_service.exchange_code_for_token(
            code="auth_code",
            client_id="client_id",
            redirect_uri="http://localhost:3000/callback",
            provider="unsupported_provider",
        )


@pytest.mark.asyncio
async def test_token_exchange_failure(oauth2_service):
    """Test handling of token exchange failure."""
    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.text.return_value = "Bad Request"
        mock_post.return_value.__aenter__.return_value = mock_response

        with pytest.raises(Exception, match="Token exchange failed"):
            await oauth2_service.exchange_code_for_token(
                code="invalid_code",
                client_id="client_id",
                redirect_uri="http://localhost:3000/callback",
                provider="google",
            )
