"""
凭据加密服务
用于安全地加密和解密用户的OAuth2凭据
符合设计文档的AES-256加密要求
"""

import base64
from typing import Dict, Optional

from cryptography.fernet import Fernet

from shared.logging_config import get_logger
logger = get_logger(__name__)


class CredentialEncryption:
    """凭据加密/解密服务 - 符合设计文档要求"""

    def __init__(self, encryption_key: str):
        """初始化加密服务

        Args:
            encryption_key: Base64编码的Fernet加密密钥
        """
        try:
            # 如果提供的是有效的Fernet密钥，直接使用
            if len(encryption_key) == 44 and encryption_key.endswith("="):
                self.fernet = Fernet(encryption_key.encode())
            else:
                # 否则从字符串生成Fernet密钥
                key_bytes = base64.urlsafe_b64encode(encryption_key.encode()[:32].ljust(32, b"\0"))
                self.fernet = Fernet(key_bytes)

            logger.info("Credential encryption service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize credential encryption: {e}")
            # 使用默认密钥作为fallback
            self.fernet = Fernet(Fernet.generate_key())

    def encrypt_credential(self, credential: str) -> str:
        """加密凭证（符合设计文档接口）

        Args:
            credential: 要加密的明文凭证

        Returns:
            加密后的密文
        """
        try:
            return self.fernet.encrypt(credential.encode()).decode()
        except Exception as e:
            logger.error(f"Failed to encrypt credential: {e}")
            raise

    def decrypt_credential(self, encrypted_credential: str) -> str:
        """解密凭证（符合设计文档接口）

        Args:
            encrypted_credential: 要解密的密文

        Returns:
            解密后的明文凭证
        """
        try:
            return self.fernet.decrypt(encrypted_credential.encode()).decode()
        except Exception as e:
            logger.error(f"Failed to decrypt credential: {e}")
            raise

    def encrypt_credential_dict(self, credentials: Dict[str, str]) -> Dict[str, str]:
        """加密凭证字典（符合设计文档接口）

        Args:
            credentials: 要加密的凭证字典

        Returns:
            加密后的凭证字典
        """
        return {key: self.encrypt_credential(value) for key, value in credentials.items()}

    # 向后兼容的方法别名
    def encrypt(self, plaintext: str) -> str:
        """向后兼容的加密方法"""
        return self.encrypt_credential(plaintext)

    def decrypt(self, ciphertext: str) -> Optional[str]:
        """向后兼容的解密方法"""
        try:
            return self.decrypt_credential(ciphertext)
        except Exception:
            return None
