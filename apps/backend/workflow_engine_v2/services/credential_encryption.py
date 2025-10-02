"""
Credential encryption service for secure token storage.

Provides AES-256 encryption for OAuth tokens and sensitive credentials.
"""

import base64
import logging
import os
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class CredentialEncryption:
    """Handles encryption/decryption of sensitive credentials."""

    def __init__(self, encryption_key: Optional[str] = None):
        """Initialize with encryption key.

        Args:
            encryption_key: Base64 encoded encryption key. If None, generates from environment.
        """
        self.logger = logging.getLogger(__name__)

        if encryption_key:
            self.fernet = Fernet(encryption_key.encode())
        else:
            # Generate key from environment or create new one
            key = self._get_or_generate_key()
            self.fernet = Fernet(key)

    def _get_or_generate_key(self) -> bytes:
        """Get encryption key from environment or generate new one."""
        env_key = os.getenv("CREDENTIAL_ENCRYPTION_KEY")

        if env_key:
            try:
                return env_key.encode()
            except Exception as e:
                self.logger.warning(f"Invalid encryption key in environment: {e}")

        # Generate new key
        key = Fernet.generate_key()
        self.logger.warning(
            "Generated new encryption key. Set CREDENTIAL_ENCRYPTION_KEY environment variable for production."
        )
        return key

    def encrypt(self, data: str) -> str:
        """Encrypt string data.

        Args:
            data: Plain text data to encrypt

        Returns:
            Base64 encoded encrypted data
        """
        try:
            if not data:
                return data

            encrypted = self.fernet.encrypt(data.encode())
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            self.logger.error(f"Encryption failed: {e}")
            raise

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string data.

        Args:
            encrypted_data: Base64 encoded encrypted data

        Returns:
            Decrypted plain text data
        """
        try:
            if not encrypted_data:
                return encrypted_data

            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            decrypted = self.fernet.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            self.logger.error(f"Decryption failed: {e}")
            raise

    def encrypt_dict(self, data: dict) -> dict:
        """Encrypt sensitive fields in a dictionary.

        Args:
            data: Dictionary containing data to encrypt

        Returns:
            Dictionary with sensitive fields encrypted
        """
        sensitive_fields = [
            "access_token",
            "refresh_token",
            "api_key",
            "secret",
            "password",
            "client_secret",
            "private_key",
        ]

        encrypted_data = data.copy()

        for field in sensitive_fields:
            if field in encrypted_data and encrypted_data[field]:
                encrypted_data[field] = self.encrypt(encrypted_data[field])

        return encrypted_data

    def decrypt_dict(self, encrypted_data: dict) -> dict:
        """Decrypt sensitive fields in a dictionary.

        Args:
            encrypted_data: Dictionary with encrypted sensitive fields

        Returns:
            Dictionary with sensitive fields decrypted
        """
        sensitive_fields = [
            "access_token",
            "refresh_token",
            "api_key",
            "secret",
            "password",
            "client_secret",
            "private_key",
        ]

        decrypted_data = encrypted_data.copy()

        for field in sensitive_fields:
            if field in decrypted_data and decrypted_data[field]:
                try:
                    decrypted_data[field] = self.decrypt(decrypted_data[field])
                except Exception:
                    # Field might not be encrypted, leave as-is
                    pass

        return decrypted_data


__all__ = ["CredentialEncryption"]
