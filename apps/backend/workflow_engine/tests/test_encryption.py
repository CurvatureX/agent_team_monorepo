"""
Unit tests for encryption service.

Tests all encryption functionality including normal operations,
edge cases, and error conditions.
"""

import os
import pytest
from unittest.mock import patch

from workflow_engine.core.encryption import (
    CredentialEncryption,
    EncryptionError,
    InvalidKeyError,
    DecryptionError,
    get_encryption,
    encrypt_credential_data,
    decrypt_credential_data,
)


class TestCredentialEncryption:
    """Test cases for CredentialEncryption class."""
    
    def test_init_with_valid_key(self):
        """Test initialization with valid encryption key."""
        key = "this_is_a_test_key_that_is_long_enough_for_security"
        encryption = CredentialEncryption(key)
        assert encryption is not None
    
    def test_init_with_environment_variable(self):
        """Test initialization using environment variable."""
        test_key = "env_test_key_that_is_long_enough_for_security"
        with patch.dict(os.environ, {"CREDENTIAL_ENCRYPTION_KEY": test_key}):
            encryption = CredentialEncryption()
            assert encryption is not None
    
    def test_init_missing_key(self):
        """Test initialization fails when no key is provided."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(InvalidKeyError, match="Encryption key not found"):
                CredentialEncryption()
    
    def test_init_short_key(self):
        """Test initialization fails with key too short."""
        short_key = "short"
        with pytest.raises(InvalidKeyError, match="must be at least 32 characters"):
            CredentialEncryption(short_key)
    
    def test_encrypt_decrypt_roundtrip(self):
        """Test that encryption and decryption work together."""
        key = "test_key_for_roundtrip_that_is_long_enough"
        encryption = CredentialEncryption(key)
        
        original_data = "sensitive_password_123"
        encrypted = encryption.encrypt(original_data)
        decrypted = encryption.decrypt(encrypted)
        
        assert decrypted == original_data
        assert encrypted != original_data
        assert len(encrypted) > len(original_data)
    
    def test_encrypt_different_values_produce_different_output(self):
        """Test that different values produce different encrypted output."""
        key = "test_key_for_different_values_that_is_long"
        encryption = CredentialEncryption(key)
        
        value1 = "password1"
        value2 = "password2"
        
        encrypted1 = encryption.encrypt(value1)
        encrypted2 = encryption.encrypt(value2)
        
        assert encrypted1 != encrypted2
    
    def test_encrypt_same_value_produces_different_output(self):
        """Test that same value produces different encrypted output each time (due to IV)."""
        key = "test_key_for_same_value_different_output"
        encryption = CredentialEncryption(key)
        
        value = "same_password"
        encrypted1 = encryption.encrypt(value)
        encrypted2 = encryption.encrypt(value)
        
        # Fernet includes random IV, so same plaintext produces different ciphertext
        assert encrypted1 != encrypted2
        
        # But both should decrypt to the same value
        assert encryption.decrypt(encrypted1) == value
        assert encryption.decrypt(encrypted2) == value
    
    def test_encrypt_non_string_raises_error(self):
        """Test that encrypting non-string raises error."""
        key = "test_key_for_non_string_error_that_is_long"
        encryption = CredentialEncryption(key)
        
        with pytest.raises(EncryptionError, match="Data must be a string"):
            encryption.encrypt(123)
        
        with pytest.raises(EncryptionError, match="Data must be a string"):
            encryption.encrypt(None)
    
    def test_decrypt_non_string_raises_error(self):
        """Test that decrypting non-string raises error."""
        key = "test_key_for_decrypt_non_string_error_long"
        encryption = CredentialEncryption(key)
        
        with pytest.raises(DecryptionError, match="Encrypted data must be a string"):
            encryption.decrypt(123)
        
        with pytest.raises(DecryptionError, match="Encrypted data must be a string"):
            encryption.decrypt(None)
    
    def test_decrypt_invalid_data_raises_error(self):
        """Test that decrypting invalid data raises error."""
        key = "test_key_for_invalid_data_error_that_is_long"
        encryption = CredentialEncryption(key)
        
        with pytest.raises(DecryptionError, match="Invalid encrypted data"):
            encryption.decrypt("invalid_encrypted_data")
    
    def test_decrypt_with_wrong_key_raises_error(self):
        """Test that decrypting with wrong key raises error."""
        key1 = "test_key_1_for_wrong_key_error_that_is_long"
        key2 = "test_key_2_for_wrong_key_error_that_is_long"
        
        encryption1 = CredentialEncryption(key1)
        encryption2 = CredentialEncryption(key2)
        
        data = "secret_password"
        encrypted = encryption1.encrypt(data)
        
        with pytest.raises(DecryptionError, match="Invalid encrypted data"):
            encryption2.decrypt(encrypted)
    
    def test_encrypt_dict(self):
        """Test encrypting specific keys in a dictionary."""
        key = "test_key_for_dict_encryption_that_is_long"
        encryption = CredentialEncryption(key)
        
        data = {
            "username": "user123",
            "password": "secret123",
            "api_key": "key_abc_123",
            "public_info": "not_secret"
        }
        sensitive_keys = ["password", "api_key"]
        
        encrypted_data = encryption.encrypt_dict(data, sensitive_keys)
        
        # Non-sensitive data should be unchanged
        assert encrypted_data["username"] == "user123"
        assert encrypted_data["public_info"] == "not_secret"
        
        # Sensitive data should be encrypted
        assert encrypted_data["password"] != "secret123"
        assert encrypted_data["api_key"] != "key_abc_123"
        
        # Should be able to decrypt back
        decrypted_data = encryption.decrypt_dict(encrypted_data, sensitive_keys)
        assert decrypted_data == data
    
    def test_encrypt_dict_with_none_values(self):
        """Test encrypting dictionary with None values."""
        key = "test_key_for_dict_none_values_that_is_long"
        encryption = CredentialEncryption(key)
        
        data = {
            "password": None,
            "api_key": "real_key"
        }
        sensitive_keys = ["password", "api_key"]
        
        encrypted_data = encryption.encrypt_dict(data, sensitive_keys)
        
        # None values should remain None
        assert encrypted_data["password"] is None
        assert encrypted_data["api_key"] != "real_key"
    
    def test_encrypt_dict_with_non_string_values(self):
        """Test encrypting dictionary with non-string values."""
        key = "test_key_for_dict_non_string_that_is_long"
        encryption = CredentialEncryption(key)
        
        data = {
            "port": 443,
            "enabled": True,
            "api_key": "string_key"
        }
        sensitive_keys = ["port", "enabled"]
        
        encrypted_data = encryption.encrypt_dict(data, sensitive_keys)
        
        # Should encrypt string representations
        assert encrypted_data["port"] != 443
        assert encrypted_data["enabled"] != True
        
        # When decrypted, should get string representations back
        decrypted_data = encryption.decrypt_dict(encrypted_data, sensitive_keys)
        assert decrypted_data["port"] == "443"
        assert decrypted_data["enabled"] == "True"
    
    def test_consistent_key_derivation(self):
        """Test that same key source produces same encryption key."""
        key_source = "consistent_test_key_that_is_long_enough"
        
        encryption1 = CredentialEncryption(key_source)
        encryption2 = CredentialEncryption(key_source)
        
        data = "test_data_for_consistency"
        encrypted1 = encryption1.encrypt(data)
        
        # Should be able to decrypt with second instance
        decrypted = encryption2.decrypt(encrypted1)
        assert decrypted == data
    
    def test_generate_key(self):
        """Test key generation utility."""
        key = CredentialEncryption.generate_key()
        
        assert isinstance(key, str)
        assert len(key) >= 32
        
        # Generated key should be usable
        encryption = CredentialEncryption(key)
        test_data = "test_with_generated_key"
        encrypted = encryption.encrypt(test_data)
        decrypted = encryption.decrypt(encrypted)
        assert decrypted == test_data
    
    def test_multiple_key_generation_produces_different_keys(self):
        """Test that multiple key generations produce different keys."""
        key1 = CredentialEncryption.generate_key()
        key2 = CredentialEncryption.generate_key()
        
        assert key1 != key2


class TestGlobalEncryptionFunctions:
    """Test cases for global encryption functions."""
    
    def test_get_encryption_singleton(self):
        """Test that get_encryption returns singleton instance."""
        with patch.dict(os.environ, {"CREDENTIAL_ENCRYPTION_KEY": "test_key_for_singleton_that_is_long"}):
            # Clear global instance
            import workflow_engine.core.encryption as enc_module
            enc_module._encryption = None
            
            instance1 = get_encryption()
            instance2 = get_encryption()
            
            assert instance1 is instance2
    
    def test_get_encryption_missing_key(self):
        """Test that get_encryption raises error when key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            # Clear global instance
            import workflow_engine.core.encryption as enc_module
            enc_module._encryption = None
            
            with pytest.raises(InvalidKeyError):
                get_encryption()
    
    def test_convenience_functions(self):
        """Test convenience encrypt/decrypt functions."""
        test_key = "test_key_for_convenience_functions_long"
        with patch.dict(os.environ, {"CREDENTIAL_ENCRYPTION_KEY": test_key}):
            # Clear global instance
            import workflow_engine.core.encryption as enc_module
            enc_module._encryption = None
            
            original_data = "convenience_test_data"
            encrypted = encrypt_credential_data(original_data)
            decrypted = decrypt_credential_data(encrypted)
            
            assert decrypted == original_data
            assert encrypted != original_data


class TestEncryptionIntegration:
    """Integration tests for encryption service."""
    
    def test_real_world_credential_scenario(self):
        """Test realistic credential encryption scenario."""
        key = "production_like_key_that_is_very_long_and_secure"
        encryption = CredentialEncryption(key)
        
        # Simulate OAuth2 credential data
        credential_data = {
            "access_token": "ya29.a0ARrdaM9...",
            "refresh_token": "1//0GWthWrNHj...",
            "token_type": "Bearer",
            "expires_in": 3599,
            "scope": "https://www.googleapis.com/auth/calendar"
        }
        
        sensitive_keys = ["access_token", "refresh_token"]
        
        # Encrypt sensitive data
        encrypted_credential = encryption.encrypt_dict(credential_data, sensitive_keys)
        
        # Verify sensitive data is encrypted
        assert encrypted_credential["access_token"] != credential_data["access_token"]
        assert encrypted_credential["refresh_token"] != credential_data["refresh_token"]
        
        # Verify non-sensitive data is preserved
        assert encrypted_credential["token_type"] == "Bearer"
        assert encrypted_credential["expires_in"] == 3599
        assert encrypted_credential["scope"] == "https://www.googleapis.com/auth/calendar"
        
        # Decrypt and verify
        decrypted_credential = encryption.decrypt_dict(encrypted_credential, sensitive_keys)
        assert decrypted_credential == credential_data
    
    def test_unicode_and_special_characters(self):
        """Test encryption with Unicode and special characters."""
        key = "unicode_test_key_that_is_long_enough_for_security"
        encryption = CredentialEncryption(key)
        
        test_cases = [
            "password with spaces",
            "pässwörd_with_ünicödé",
            "password!@#$%^&*()_+-={}[]|\\:;\"'<>?,.\/",
            "密码包含中文字符",
            "🔐🔑 password with emojis 🚀🌟",
            ""  # empty string
        ]
        
        for test_data in test_cases:
            encrypted = encryption.encrypt(test_data)
            decrypted = encryption.decrypt(encrypted)
            assert decrypted == test_data, f"Failed for: {test_data}"


@pytest.fixture(autouse=True)
def cleanup_global_encryption():
    """Cleanup global encryption instance after each test."""
    yield
    # Reset global instance
    import workflow_engine.core.encryption as enc_module
    enc_module._encryption = None 