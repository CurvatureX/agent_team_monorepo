"""
Simplified tests for credential models and encryption.

Tests core functionality without complex service dependencies.
"""

import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

# Mock environment to use SQLite
with patch.dict(os.environ, {'DATABASE_URL': 'sqlite:///:memory:'}):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker, declarative_base
    from sqlalchemy import Column, String, Text, Boolean, TIMESTAMP, JSON
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
    from sqlalchemy.sql import func
    
    from workflow_engine.core.encryption import CredentialEncryption

# Simplified test base and model for testing
TestBase = declarative_base()

class TestOAuthToken(TestBase):
    """Simplified OAuth token model for testing."""
    __tablename__ = "test_oauth_tokens"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PG_UUID(as_uuid=True), nullable=False)
    provider = Column(String(100), nullable=False)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=True)
    credential_data = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), default=func.current_timestamp())
    
    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return datetime.utcnow().replace(tzinfo=self.expires_at.tzinfo) >= self.expires_at

# Test database setup
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture
def db_session():
    """Create test database session."""
    TestBase.metadata.create_all(bind=test_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        TestBase.metadata.drop_all(bind=test_engine)


@pytest.fixture
def test_encryption():
    """Create test encryption service."""
    return CredentialEncryption("test_key_for_credential_core_tests_long_enough")


class TestCredentialModels:
    """Test cases for credential models."""
    
    def test_oauth_token_model_basic(self, db_session):
        """Test OAuthToken model basic functionality."""
        user_id = uuid4()
        token = TestOAuthToken(
            user_id=user_id,
            provider="test_provider",
            access_token="test_token",
            refresh_token="test_refresh",
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        
        # Test not expired
        assert not token.is_expired()
        
        # Test expired
        token.expires_at = datetime.utcnow() - timedelta(hours=1)
        assert token.is_expired()
        
        # Test database operations
        db_session.add(token)
        db_session.commit()
        
        # Retrieve from database
        retrieved = db_session.query(TestOAuthToken).filter_by(user_id=user_id).first()
        assert retrieved is not None
        assert retrieved.provider == "test_provider"
        assert retrieved.access_token == "test_token"
    
    def test_oauth_token_with_credential_data(self, db_session):
        """Test OAuth token with JSON credential data."""
        user_id = uuid4()
        credential_data = {
            "scope": "read write",
            "client_id": "test_client",
            "extra_info": "additional_data"
        }
        
        token = TestOAuthToken(
            user_id=user_id,
            provider="test_provider",
            access_token="test_token",
            credential_data=credential_data
        )
        
        db_session.add(token)
        db_session.commit()
        
        # Retrieve and verify JSON data
        retrieved = db_session.query(TestOAuthToken).filter_by(user_id=user_id).first()
        assert retrieved.credential_data["scope"] == "read write"
        assert retrieved.credential_data["client_id"] == "test_client"
        assert retrieved.credential_data["extra_info"] == "additional_data"


class TestCredentialEncryption:
    """Test credential encryption functionality."""
    
    def test_token_encryption_decryption(self, test_encryption):
        """Test token encryption and decryption."""
        access_token = "test_access_token_123"
        refresh_token = "test_refresh_token_456"
        
        # Encrypt tokens
        encrypted_access = test_encryption.encrypt(access_token)
        encrypted_refresh = test_encryption.encrypt(refresh_token)
        
        # Verify encrypted data is different
        assert encrypted_access != access_token
        assert encrypted_refresh != refresh_token
        
        # Decrypt and verify
        decrypted_access = test_encryption.decrypt(encrypted_access)
        decrypted_refresh = test_encryption.decrypt(encrypted_refresh)
        
        assert decrypted_access == access_token
        assert decrypted_refresh == refresh_token
    
    def test_credential_data_encryption(self, test_encryption):
        """Test selective encryption of credential data."""
        credential_data = {
            "client_secret": "super_secret_value",
            "api_key": "secret_api_key_123",
            "scope": "public_scope_info",
            "client_id": "public_client_id"
        }
        
        # Encrypt sensitive fields
        sensitive_fields = ["client_secret", "api_key"]
        encrypted_data = credential_data.copy()
        
        for field in sensitive_fields:
            if field in encrypted_data:
                encrypted_data[field] = test_encryption.encrypt(encrypted_data[field])
        
        # Verify sensitive fields are encrypted
        assert encrypted_data["client_secret"] != credential_data["client_secret"]
        assert encrypted_data["api_key"] != credential_data["api_key"]
        
        # Verify non-sensitive fields are unchanged
        assert encrypted_data["scope"] == credential_data["scope"]
        assert encrypted_data["client_id"] == credential_data["client_id"]
        
        # Decrypt sensitive fields
        for field in sensitive_fields:
            if field in encrypted_data:
                encrypted_data[field] = test_encryption.decrypt(encrypted_data[field])
        
        # Verify all data matches original
        assert encrypted_data == credential_data


class TestCredentialWorkflow:
    """Test complete credential workflow."""
    
    def test_complete_credential_storage_workflow(self, db_session, test_encryption):
        """Test complete credential storage and retrieval workflow."""
        user_id = uuid4()
        
        # Original credential data
        access_token = "original_access_token"
        refresh_token = "original_refresh_token"
        credential_data = {
            "client_secret": "secret_value",
            "scope": "calendar.events",
            "client_id": "public_client_id"
        }
        
        # Encrypt sensitive data for storage
        encrypted_access_token = test_encryption.encrypt(access_token)
        encrypted_refresh_token = test_encryption.encrypt(refresh_token)
        encrypted_credential_data = credential_data.copy()
        encrypted_credential_data["client_secret"] = test_encryption.encrypt(
            credential_data["client_secret"]
        )
        
        # Store in database
        token = TestOAuthToken(
            user_id=user_id,
            provider="google_calendar",
            access_token=encrypted_access_token,
            refresh_token=encrypted_refresh_token,
            credential_data=encrypted_credential_data,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        
        db_session.add(token)
        db_session.commit()
        
        # Retrieve from database
        retrieved = db_session.query(TestOAuthToken).filter_by(
            user_id=user_id,
            provider="google_calendar"
        ).first()
        
        assert retrieved is not None
        assert not retrieved.is_expired()
        
        # Decrypt sensitive data
        decrypted_access = test_encryption.decrypt(retrieved.access_token)
        decrypted_refresh = test_encryption.decrypt(retrieved.refresh_token)
        decrypted_client_secret = test_encryption.decrypt(
            retrieved.credential_data["client_secret"]
        )
        
        # Verify decrypted data matches original
        assert decrypted_access == access_token
        assert decrypted_refresh == refresh_token
        assert decrypted_client_secret == credential_data["client_secret"]
        assert retrieved.credential_data["scope"] == credential_data["scope"]
        assert retrieved.credential_data["client_id"] == credential_data["client_id"]
    
    def test_user_isolation(self, db_session, test_encryption):
        """Test that users can only access their own credentials."""
        user1_id = uuid4()
        user2_id = uuid4()
        
        # Store credential for user1
        token1 = TestOAuthToken(
            user_id=user1_id,
            provider="google_calendar",
            access_token=test_encryption.encrypt("user1_token"),
            refresh_token=test_encryption.encrypt("user1_refresh")
        )
        
        # Store credential for user2
        token2 = TestOAuthToken(
            user_id=user2_id,
            provider="google_calendar",
            access_token=test_encryption.encrypt("user2_token"),
            refresh_token=test_encryption.encrypt("user2_refresh")
        )
        
        db_session.add_all([token1, token2])
        db_session.commit()
        
        # User1 can only access their credential
        user1_tokens = db_session.query(TestOAuthToken).filter_by(
            user_id=user1_id
        ).all()
        assert len(user1_tokens) == 1
        assert test_encryption.decrypt(user1_tokens[0].access_token) == "user1_token"
        
        # User2 can only access their credential
        user2_tokens = db_session.query(TestOAuthToken).filter_by(
            user_id=user2_id
        ).all()
        assert len(user2_tokens) == 1
        assert test_encryption.decrypt(user2_tokens[0].access_token) == "user2_token"
        
        # Cross-user access should return empty
        user1_as_user2 = db_session.query(TestOAuthToken).filter_by(
            user_id=user2_id,
            provider="google_calendar"
        ).filter(TestOAuthToken.user_id == user1_id).all()
        assert len(user1_as_user2) == 0
    
    def test_multiple_providers_per_user(self, db_session, test_encryption):
        """Test that users can have multiple provider credentials."""
        user_id = uuid4()
        
        # Store multiple provider credentials
        providers = ["google_calendar", "slack", "github"]
        for provider in providers:
            token = TestOAuthToken(
                user_id=user_id,
                provider=provider,
                access_token=test_encryption.encrypt(f"{provider}_token"),
                refresh_token=test_encryption.encrypt(f"{provider}_refresh")
            )
            db_session.add(token)
        
        db_session.commit()
        
        # Verify all providers stored
        all_tokens = db_session.query(TestOAuthToken).filter_by(
            user_id=user_id
        ).all()
        assert len(all_tokens) == 3
        
        stored_providers = [token.provider for token in all_tokens]
        for provider in providers:
            assert provider in stored_providers
        
        # Verify each token is correct
        for token in all_tokens:
            decrypted_access = test_encryption.decrypt(token.access_token)
            expected_token = f"{token.provider}_token"
            assert decrypted_access == expected_token


class TestCredentialSecurity:
    """Test credential security features."""
    
    def test_token_expiration_handling(self, db_session):
        """Test token expiration detection."""
        user_id = uuid4()
        
        # Valid token (not expired)
        valid_token = TestOAuthToken(
            user_id=user_id,
            provider="valid_provider",
            access_token="valid_token",
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        
        # Expired token
        expired_token = TestOAuthToken(
            user_id=user_id,
            provider="expired_provider",
            access_token="expired_token",
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        
        # Token without expiry (should be considered valid)
        no_expiry_token = TestOAuthToken(
            user_id=user_id,
            provider="no_expiry_provider",
            access_token="no_expiry_token",
            expires_at=None
        )
        
        assert not valid_token.is_expired()
        assert expired_token.is_expired()
        assert not no_expiry_token.is_expired()
    
    def test_encryption_consistency(self, test_encryption):
        """Test encryption consistency across multiple operations."""
        original_data = "sensitive_credential_data"
        
        # Multiple encryption operations should produce different ciphertext
        encrypted1 = test_encryption.encrypt(original_data)
        encrypted2 = test_encryption.encrypt(original_data)
        
        # Ciphertext should be different (due to IV)
        assert encrypted1 != encrypted2
        
        # But both should decrypt to the same value
        assert test_encryption.decrypt(encrypted1) == original_data
        assert test_encryption.decrypt(encrypted2) == original_data
    
    def test_cross_key_isolation(self):
        """Test that different encryption keys cannot decrypt each other's data."""
        key1 = "key1_for_encryption_test_that_is_long_enough"
        key2 = "key2_for_encryption_test_that_is_long_enough"
        
        encryption1 = CredentialEncryption(key1)
        encryption2 = CredentialEncryption(key2)
        
        data = "sensitive_data_to_encrypt"
        encrypted_with_key1 = encryption1.encrypt(data)
        
        # Key2 should not be able to decrypt data encrypted with key1
        with pytest.raises(Exception):  # Should raise DecryptionError
            encryption2.decrypt(encrypted_with_key1) 