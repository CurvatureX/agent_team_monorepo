"""
Credential Encryption Service
用于加密和解密敏感凭据数据的服务
"""

import base64
import json
import logging
import os
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class CredentialEncryption:
    """处理凭据加密和解密的服务类"""

    def __init__(self, encryption_key: Optional[str] = None):
        """
        初始化加密服务

        Args:
            encryption_key: 加密密钥，如果为空则从环境变量获取
        """
        self.encryption_key = encryption_key or os.getenv("CREDENTIAL_ENCRYPTION_KEY")
        if not self.encryption_key:
            # 如果没有提供密钥，生成一个默认密钥（开发环境使用）
            logger.warning(
                "No encryption key provided, using default key (not secure for production)"
            )
            self.encryption_key = "default_key_for_development_only"

        # 生成Fernet密钥
        self._fernet_key = self._derive_key(self.encryption_key.encode())
        self._cipher = Fernet(self._fernet_key)

    def _derive_key(self, password: bytes) -> bytes:
        """从密码派生加密密钥"""
        # 使用固定盐值（在生产环境中应该使用随机盐值并存储）
        salt = b"workflow_engine_salt"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key

    def encrypt_credentials(self, credentials: Dict[str, Any]) -> str:
        """
        加密凭据字典

        Args:
            credentials: 要加密的凭据字典

        Returns:
            加密后的base64字符串
        """
        try:
            # 将字典转换为JSON字符串
            json_str = json.dumps(credentials)

            # 加密数据
            encrypted_data = self._cipher.encrypt(json_str.encode())

            # 返回base64编码的字符串
            return base64.b64encode(encrypted_data).decode()

        except Exception as e:
            logger.error(f"Failed to encrypt credentials: {e}")
            raise

    def decrypt_credentials(self, encrypted_data: str) -> Dict[str, Any]:
        """
        解密凭据字符串

        Args:
            encrypted_data: 加密的base64字符串

        Returns:
            解密后的凭据字典
        """
        try:
            # 解码base64
            encrypted_bytes = base64.b64decode(encrypted_data.encode())

            # 解密数据
            decrypted_data = self._cipher.decrypt(encrypted_bytes)

            # 转换为字典
            return json.loads(decrypted_data.decode())

        except Exception as e:
            logger.error(f"Failed to decrypt credentials: {e}")
            raise

    def encrypt_single_value(self, value: str) -> str:
        """
        加密单个字符串值

        Args:
            value: 要加密的字符串

        Returns:
            加密后的base64字符串
        """
        try:
            encrypted_data = self._cipher.encrypt(value.encode())
            return base64.b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"Failed to encrypt single value: {e}")
            raise

    def decrypt_single_value(self, encrypted_value: str) -> str:
        """
        解密单个字符串值

        Args:
            encrypted_value: 加密的base64字符串

        Returns:
            解密后的字符串
        """
        try:
            encrypted_bytes = base64.b64decode(encrypted_value.encode())
            decrypted_data = self._cipher.decrypt(encrypted_bytes)
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt single value: {e}")
            raise


# 全局实例（单例模式）
_encryption_instance: Optional[CredentialEncryption] = None


def get_credential_encryption() -> CredentialEncryption:
    """获取凭据加密服务实例（单例模式）"""
    global _encryption_instance
    if _encryption_instance is None:
        _encryption_instance = CredentialEncryption()
    return _encryption_instance
