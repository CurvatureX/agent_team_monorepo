"""
Credential encryption service for secure storage of sensitive data.

This module provides Fernet-based symmetric encryption for credential data,
following the pattern used by n8n and similar workflow automation tools.
"""

import base64
import hashlib
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class EncryptionError(Exception):
    """Base exception for encryption-related errors."""
    pass


class InvalidKeyError(EncryptionError):
    """Raised when encryption key is invalid or missing."""
    pass


class DecryptionError(EncryptionError):
    """Raised when decryption fails."""
    pass


class CredentialEncryption:
    """
    Provides secure encryption/decryption for credential data.
    
    Uses Fernet symmetric encryption with a key derived from an environment variable.
    Ensures consistent key generation and secure data handling.
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize the encryption service.
        
        Args:
            encryption_key: Optional override for encryption key.
                           If not provided, uses CREDENTIAL_ENCRYPTION_KEY environment variable.
                           
        Raises:
            InvalidKeyError: If encryption key is invalid or missing.
        """
        key_source = encryption_key or os.getenv("CREDENTIAL_ENCRYPTION_KEY")
        
        if not key_source:
            raise InvalidKeyError(
                "Encryption key not found. Set CREDENTIAL_ENCRYPTION_KEY environment variable."
            )
        
        if len(key_source) < 32:
            raise InvalidKeyError(
                f"Encryption key must be at least 32 characters long. Got {len(key_source)} characters."
            )
        
        self._fernet = self._create_fernet(key_source)
    
    def _create_fernet(self, key_source: str) -> Fernet:
        """
        Create a Fernet instance with a key derived from the source string.
        
        Args:
            key_source: Source string for key derivation
            
        Returns:
            Initialized Fernet instance
        """
        # Use PBKDF2 to derive a consistent 32-byte key from the source
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'curvaturex_workflow_engine',  # Fixed salt for consistency
            iterations=100000,  # OWASP recommended minimum
        )
        key = base64.urlsafe_b64encode(kdf.derive(key_source.encode('utf-8')))
        return Fernet(key)
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt a string value.
        
        Args:
            data: Plain text string to encrypt
            
        Returns:
            Base64-encoded encrypted string
            
        Raises:
            EncryptionError: If encryption fails
        """
        if not isinstance(data, str):
            raise EncryptionError(f"Data must be a string, got {type(data)}")
        
        try:
            encrypted_bytes = self._fernet.encrypt(data.encode('utf-8'))
            return encrypted_bytes.decode('utf-8')
        except Exception as e:
            raise EncryptionError(f"Encryption failed: {str(e)}") from e
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt an encrypted string value.
        
        Args:
            encrypted_data: Base64-encoded encrypted string
            
        Returns:
            Decrypted plain text string
            
        Raises:
            DecryptionError: If decryption fails
        """
        if not isinstance(encrypted_data, str):
            raise DecryptionError(f"Encrypted data must be a string, got {type(encrypted_data)}")
        
        try:
            decrypted_bytes = self._fernet.decrypt(encrypted_data.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except InvalidToken as e:
            raise DecryptionError("Invalid encrypted data or wrong encryption key") from e
        except Exception as e:
            raise DecryptionError(f"Decryption failed: {str(e)}") from e
    
    def encrypt_dict(self, data_dict: dict, sensitive_keys: list[str]) -> dict:
        """
        Encrypt specific keys in a dictionary.
        
        Args:
            data_dict: Dictionary containing data to encrypt
            sensitive_keys: List of keys whose values should be encrypted
            
        Returns:
            Dictionary with specified keys encrypted
        """
        result = data_dict.copy()
        
        for key in sensitive_keys:
            if key in result and result[key] is not None:
                if isinstance(result[key], str):
                    result[key] = self.encrypt(result[key])
                else:
                    # Convert non-string values to string before encryption
                    result[key] = self.encrypt(str(result[key]))
        
        return result
    
    def decrypt_dict(self, data_dict: dict, sensitive_keys: list[str]) -> dict:
        """
        Decrypt specific keys in a dictionary.
        
        Args:
            data_dict: Dictionary containing encrypted data
            sensitive_keys: List of keys whose values should be decrypted
            
        Returns:
            Dictionary with specified keys decrypted
        """
        result = data_dict.copy()
        
        for key in sensitive_keys:
            if key in result and result[key] is not None:
                result[key] = self.decrypt(result[key])
        
        return result
    
    @staticmethod
    def generate_key() -> str:
        """
        Generate a secure random encryption key.
        
        Returns:
            Base64-encoded random key suitable for use as CREDENTIAL_ENCRYPTION_KEY
        """
        key = Fernet.generate_key()
        return base64.urlsafe_b64decode(key).hex()


# Global encryption instance
_encryption: Optional[CredentialEncryption] = None


def get_encryption() -> CredentialEncryption:
    """
    Get the global encryption instance.
    
    Returns:
        Initialized CredentialEncryption instance
        
    Raises:
        InvalidKeyError: If encryption key is not configured
    """
    global _encryption
    if _encryption is None:
        _encryption = CredentialEncryption()
    return _encryption


def encrypt_credential_data(data: str) -> str:
    """
    Convenience function to encrypt credential data.
    
    Args:
        data: Plain text credential data
        
    Returns:
        Encrypted credential data
    """
    return get_encryption().encrypt(data)


def decrypt_credential_data(encrypted_data: str) -> str:
    """
    Convenience function to decrypt credential data.
    
    Args:
        encrypted_data: Encrypted credential data
        
    Returns:
        Decrypted plain text credential data
    """
    return get_encryption().decrypt(encrypted_data) 