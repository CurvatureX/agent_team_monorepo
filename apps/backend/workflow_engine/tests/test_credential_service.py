"""
Unit tests for credential management service.

Tests all credential management functionality including CRUD operations,
encryption, user isolation, and database locking.
"""

import asyncio
import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

# Mock environment variables before any imports
with patch.dict(os.environ, {'DATABASE_URL': 'sqlite:///:memory:'}):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    from workflow_engine.core.encryption import CredentialEncryption
    from workflow_engine.models.database import Base
    from workflow_engine.models.credential import OAuthToken, CredentialConfig, OAuth2Credential
    from workflow_engine.services.credential_service import (
        CredentialService,
        CredentialServiceError,
        CredentialNotFoundError,
        CredentialStorageError,
    )


# Test database setup
TEST_DATABASE_URL = "sqlite:///:memory:"

# Override database import to prevent PostgreSQL connection
with patch.dict('os.environ', {'DATABASE_URL': TEST_DATABASE_URL}):
    test_engine = create_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture
def db_session():
    """Create test database session."""
    Base.metadata.create_all(bind=test_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def test_encryption():
    """Create test encryption service."""
    return CredentialEncryption("test_key_for_credential_service_tests")


@pytest.fixture
def credential_service(db_session, test_encryption):
    """Create credential service with test dependencies."""
    with patch('workflow_engine.services.credential_service.get_encryption', return_value=test_encryption):
        with patch('workflow_engine.services.credential_service.get_settings') as mock_settings:
            # Mock settings
            mock_settings.return_value.api_timeout_connect = 5
            mock_settings.return_value.api_timeout_read = 30
            mock_settings.return_value.get_oauth2_config.return_value = {
                "token_url": "https://oauth2.example.com/token",
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
            }
            
            service = CredentialService(db_session)
            yield service


@pytest.fixture
def sample_credential():
    """Sample credential configuration for testing."""
    return CredentialConfig(
        provider="google_calendar",
        access_token="test_access_token_123",
        refresh_token="test_refresh_token_456",
        token_type="Bearer",
        expires_at=datetime.utcnow() + timedelta(hours=1),
        credential_data={
            "scope": "https://www.googleapis.com/auth/calendar.events",
            "client_id": "test_client_id"
        }
    )


class TestCredentialService:
    """Test cases for CredentialService class."""
    
    @pytest.mark.asyncio
    async def test_store_credential_new(self, credential_service, sample_credential):
        """Test storing new credential."""
        user_id = str(uuid4())
        
        credential_id = await credential_service.store_credential(
            user_id=user_id,
            provider="google_calendar",
            credential=sample_credential
        )
        
        assert credential_id is not None
        assert len(credential_id) > 0
        
        # Verify stored in database
        stored = await credential_service.get_credential(user_id, "google_calendar")
        assert stored is not None
        assert stored.access_token == sample_credential.access_token
        assert stored.refresh_token == sample_credential.refresh_token
        assert stored.token_type == sample_credential.token_type
    
    @pytest.mark.asyncio
    async def test_store_credential_update_existing(self, credential_service, sample_credential):
        """Test updating existing credential."""
        user_id = str(uuid4())
        
        # Store initial credential
        initial_id = await credential_service.store_credential(
            user_id=user_id,
            provider="google_calendar",
            credential=sample_credential
        )
        
        # Update with new credential
        updated_credential = CredentialConfig(
            provider="google_calendar",
            access_token="updated_access_token",
            refresh_token="updated_refresh_token",
            token_type="Bearer"
        )
        
        updated_id = await credential_service.store_credential(
            user_id=user_id,
            provider="google_calendar",
            credential=updated_credential
        )
        
        # Should update same record
        assert updated_id == initial_id
        
        # Verify updated values
        stored = await credential_service.get_credential(user_id, "google_calendar")
        assert stored.access_token == "updated_access_token"
        assert stored.refresh_token == "updated_refresh_token"
    
    @pytest.mark.asyncio
    async def test_get_credential_not_found(self, credential_service):
        """Test getting non-existent credential."""
        user_id = str(uuid4())
        
        result = await credential_service.get_credential(user_id, "nonexistent_provider")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_credential_user_isolation(self, credential_service, sample_credential):
        """Test that users can only access their own credentials."""
        user1_id = str(uuid4())
        user2_id = str(uuid4())
        
        # Store credential for user1
        await credential_service.store_credential(
            user_id=user1_id,
            provider="google_calendar",
            credential=sample_credential
        )
        
        # User1 can access their credential
        user1_cred = await credential_service.get_credential(user1_id, "google_calendar")
        assert user1_cred is not None
        
        # User2 cannot access user1's credential
        user2_cred = await credential_service.get_credential(user2_id, "google_calendar")
        assert user2_cred is None
    
    @pytest.mark.asyncio
    async def test_credential_encryption(self, credential_service, sample_credential, db_session):
        """Test that credentials are encrypted in database."""
        user_id = str(uuid4())
        
        await credential_service.store_credential(
            user_id=user_id,
            provider="google_calendar",
            credential=sample_credential
        )
        
        # Check raw database storage
        db_record = db_session.query(OAuthToken).filter_by(
            user_id=user_id,
            provider="google_calendar"
        ).first()
        
        assert db_record is not None
        # Access token should be encrypted (different from original)
        assert db_record.access_token != sample_credential.access_token
        # Refresh token should be encrypted
        assert db_record.refresh_token != sample_credential.refresh_token
    
    @pytest.mark.asyncio
    async def test_credential_with_integration_id(self, credential_service, sample_credential):
        """Test credential storage with integration ID."""
        user_id = str(uuid4())
        integration_id = "test_integration_123"
        
        credential_id = await credential_service.store_credential(
            user_id=user_id,
            provider="google_calendar",
            credential=sample_credential,
            integration_id=integration_id
        )
        
        assert credential_id is not None
        
        # Should find credential with integration ID
        stored = await credential_service.get_credential(
            user_id, "google_calendar", integration_id
        )
        assert stored is not None
        
        # Should not find without integration ID
        stored_without_id = await credential_service.get_credential(
            user_id, "google_calendar"
        )
        assert stored_without_id is None
    
    @pytest.mark.asyncio
    async def test_delete_credential(self, credential_service, sample_credential):
        """Test credential deletion."""
        user_id = str(uuid4())
        
        # Store credential
        await credential_service.store_credential(
            user_id=user_id,
            provider="google_calendar",
            credential=sample_credential
        )
        
        # Verify credential exists
        stored = await credential_service.get_credential(user_id, "google_calendar")
        assert stored is not None
        
        # Delete credential
        deleted = await credential_service.delete_credential(user_id, "google_calendar")
        assert deleted is True
        
        # Verify credential is gone
        stored_after = await credential_service.get_credential(user_id, "google_calendar")
        assert stored_after is None
        
        # Deleting again should return False
        deleted_again = await credential_service.delete_credential(user_id, "google_calendar")
        assert deleted_again is False
    
    @pytest.mark.asyncio
    async def test_list_credentials(self, credential_service):
        """Test listing user credentials."""
        user_id = str(uuid4())
        
        # Store multiple credentials
        cred1 = CredentialConfig(
            provider="google_calendar",
            access_token="token1",
            refresh_token="refresh1"
        )
        cred2 = CredentialConfig(
            provider="slack",
            access_token="token2",
            refresh_token="refresh2"
        )
        
        await credential_service.store_credential(user_id, "google_calendar", cred1)
        await credential_service.store_credential(user_id, "slack", cred2)
        
        # List credentials
        credentials = await credential_service.list_credentials(user_id)
        
        assert len(credentials) == 2
        providers = [cred["provider"] for cred in credentials]
        assert "google_calendar" in providers
        assert "slack" in providers
        
        # Verify sensitive data is not included
        for cred in credentials:
            assert "access_token" not in cred
            assert "refresh_token" not in cred
    
    @pytest.mark.asyncio
    async def test_refresh_oauth_token_success(self, credential_service, sample_credential):
        """Test successful OAuth2 token refresh."""
        user_id = str(uuid4())
        
        # Store credential with refresh token
        await credential_service.store_credential(
            user_id=user_id,
            provider="google_calendar",
            credential=sample_credential
        )
        
        # Mock HTTP response for token refresh
        mock_response = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "token_type": "Bearer",
            "expires_in": 3600
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock()
            mock_client.return_value.__aenter__.return_value.post.return_value.status_code = 200
            mock_client.return_value.__aenter__.return_value.post.return_value.json.return_value = mock_response
            
            # Refresh token
            success = await credential_service.refresh_oauth_token(user_id, "google_calendar")
            assert success is True
            
            # Verify token was updated
            updated_cred = await credential_service.get_credential(user_id, "google_calendar")
            assert updated_cred.access_token == "new_access_token"
            assert updated_cred.refresh_token == "new_refresh_token"
    
    @pytest.mark.asyncio
    async def test_refresh_oauth_token_no_refresh_token(self, credential_service):
        """Test token refresh when no refresh token exists."""
        user_id = str(uuid4())
        
        # Store credential without refresh token
        cred_no_refresh = CredentialConfig(
            provider="google_calendar",
            access_token="test_token",
            refresh_token=None
        )
        
        await credential_service.store_credential(
            user_id=user_id,
            provider="google_calendar",
            credential=cred_no_refresh
        )
        
        # Should raise error
        with pytest.raises(CredentialServiceError, match="No refresh token available"):
            await credential_service.refresh_oauth_token(user_id, "google_calendar")
    
    @pytest.mark.asyncio
    async def test_refresh_oauth_token_not_found(self, credential_service):
        """Test token refresh for non-existent credential."""
        user_id = str(uuid4())
        
        with pytest.raises(CredentialNotFoundError):
            await credential_service.refresh_oauth_token(user_id, "nonexistent_provider")
    
    @pytest.mark.asyncio
    async def test_refresh_oauth_token_http_error(self, credential_service, sample_credential):
        """Test token refresh HTTP error handling."""
        user_id = str(uuid4())
        
        await credential_service.store_credential(
            user_id=user_id,
            provider="google_calendar",
            credential=sample_credential
        )
        
        # Mock HTTP error response
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock()
            mock_client.return_value.__aenter__.return_value.post.return_value.status_code = 400
            mock_client.return_value.__aenter__.return_value.post.return_value.text = "Invalid refresh token"
            
            with pytest.raises(CredentialServiceError, match="Token refresh failed"):
                await credential_service.refresh_oauth_token(user_id, "google_calendar")
    
    @pytest.mark.asyncio 
    async def test_sensitive_data_encryption_in_credential_data(self, credential_service, test_encryption):
        """Test that sensitive fields in credential_data are encrypted."""
        user_id = str(uuid4())
        
        # Credential with sensitive data
        cred_with_secrets = CredentialConfig(
            provider="test_provider",
            access_token="test_token",
            credential_data={
                "client_secret": "super_secret_value",
                "api_key": "secret_api_key",
                "public_info": "not_secret_value"
            }
        )
        
        await credential_service.store_credential(
            user_id=user_id,
            provider="test_provider",
            credential=cred_with_secrets
        )
        
        # Retrieve and verify decryption
        retrieved = await credential_service.get_credential(user_id, "test_provider")
        assert retrieved.metadata["client_secret"] == "super_secret_value"
        assert retrieved.metadata["api_key"] == "secret_api_key"
        assert retrieved.metadata["public_info"] == "not_secret_value"
    
    def test_context_manager(self, test_encryption):
        """Test credential service context manager."""
        with patch('workflow_engine.services.credential_service.get_encryption', return_value=test_encryption):
            with patch('workflow_engine.services.credential_service.SessionLocal') as mock_session:
                mock_session.return_value = MagicMock()
                
                # Test context manager creates and closes session
                with CredentialService() as service:
                    assert service.session is not None
                
                # Session should be closed after context
                mock_session.return_value.close.assert_called_once()


class TestCredentialModels:
    """Test cases for credential model classes."""
    
    def test_oauth_token_model(self):
        """Test OAuthToken model basic functionality."""
        token = OAuthToken(
            user_id=uuid4(),
            provider="test_provider",
            access_token="encrypted_token",
            refresh_token="encrypted_refresh",
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        
        assert not token.is_expired()
        assert token.is_valid()
        
        # Test expired token
        token.expires_at = datetime.utcnow() - timedelta(hours=1)
        assert token.is_expired()
        assert not token.is_valid()
    
    def test_oauth_token_to_dict(self):
        """Test OAuthToken to_dict method."""
        token = OAuthToken(
            user_id=uuid4(),
            provider="test_provider",
            access_token="secret_token",
            credential_data={"client_secret": "secret", "public_info": "public"}
        )
        
        # Without sensitive data
        data = token.to_dict(include_sensitive=False)
        assert "access_token" not in data
        assert "refresh_token" not in data
        assert data["credential_data"]["public_info"] == "public"
        assert "client_secret" not in data["credential_data"]
        
        # With sensitive data
        sensitive_data = token.to_dict(include_sensitive=True)
        assert sensitive_data["access_token"] == "secret_token"
        assert sensitive_data["credential_data"]["client_secret"] == "secret"
    
    def test_credential_config_from_oauth2_response(self):
        """Test CredentialConfig creation from OAuth2 response."""
        oauth_response = {
            "access_token": "access_123",
            "refresh_token": "refresh_456",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "read write",
            "extra_field": "extra_value"
        }
        
        config = CredentialConfig.from_oauth2_response("test_provider", oauth_response)
        
        assert config.provider == "test_provider"
        assert config.access_token == "access_123"
        assert config.refresh_token == "refresh_456"
        assert config.token_type == "Bearer"
        assert config.expires_at is not None
        assert config.credential_data["scope"] == "read write"
        assert config.credential_data["extra_field"] == "extra_value"
    
    def test_oauth2_credential(self):
        """Test OAuth2Credential functionality."""
        credential = OAuth2Credential(
            access_token="test_token",
            refresh_token="test_refresh",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            scope="read write"
        )
        
        # Test auth header
        auth_header = credential.get_auth_header()
        assert auth_header["Authorization"] == "Bearer test_token"
        
        # Test not expired
        assert not credential.is_expired()
        
        # Test conversion to dict
        data = credential.to_dict()
        assert data["access_token"] == "test_token"
        assert data["scope"] == "read write"


@pytest.fixture(autouse=True)
def cleanup_service_globals():
    """Cleanup global service instance after each test."""
    yield
    # Reset global instance
    import workflow_engine.services.credential_service as cred_module
    cred_module._credential_service = None 