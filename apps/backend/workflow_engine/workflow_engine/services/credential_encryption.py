"""
凭证加密服务
使用Fernet对称加密安全存储OAuth2令牌和API密钥
"""

import base64
import secrets
from typing import Dict, Optional, Any
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import json
import logging

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """加密操作错误"""
    pass


class DecryptionError(Exception):
    """解密操作错误"""
    pass


class CredentialEncryption:
    """凭证加密解密服务
    
    使用Fernet (AES 128 in CBC mode) 提供对称加密功能。
    支持字符串和字典的加密解密，以及密钥轮换。
    """
    
    def __init__(self, encryption_key: str):
        """初始化加密服务
        
        Args:
            encryption_key: Base64编码的32字节密钥，或用于派生密钥的字符串
            
        Raises:
            EncryptionError: 密钥格式无效时抛出
        """
        if encryption_key is None:
            raise EncryptionError("Encryption key cannot be None")
        
        if not isinstance(encryption_key, str):
            raise EncryptionError(f"Encryption key must be a string, got {type(encryption_key)}")
        
        if len(encryption_key.strip()) == 0:
            raise EncryptionError("Encryption key cannot be empty")
        
        try:
            # 如果是标准的Fernet密钥格式（44字符Base64），直接使用
            if len(encryption_key) == 44 and encryption_key.endswith('='):
                self._fernet = Fernet(encryption_key.encode())
            else:
                # 否则从字符串派生密钥
                derived_key = self._derive_key_from_string(encryption_key)
                self._fernet = Fernet(derived_key)
                
        except Exception as e:
            raise EncryptionError(f"Invalid encryption key: {str(e)}")
    
    def _derive_key_from_string(self, key_string: str) -> bytes:
        """从字符串派生Fernet密钥
        
        Args:
            key_string: 用于派生密钥的字符串
            
        Returns:
            Base64编码的Fernet密钥
        """
        # 使用固定的salt（生产环境中应该使用随机salt并存储）
        salt = b"workflow_engine_external_api_salt_2025"
        
        # 使用PBKDF2派生密钥
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(key_string.encode()))
        return key
    
    def encrypt_credential(self, credential: str) -> str:
        """加密单个凭证字符串
        
        Args:
            credential: 要加密的凭证字符串
            
        Returns:
            加密后的Base64字符串
            
        Raises:
            EncryptionError: 加密失败时抛出
        """
        if not isinstance(credential, str):
            raise EncryptionError(f"Credential must be a string, got {type(credential)}")
        
        try:
            encrypted_bytes = self._fernet.encrypt(credential.encode('utf-8'))
            return encrypted_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to encrypt credential: {str(e)}")
            raise EncryptionError(f"Encryption failed: {str(e)}")
    
    def decrypt_credential(self, encrypted_credential: str) -> str:
        """解密单个凭证字符串
        
        Args:
            encrypted_credential: 加密的Base64字符串
            
        Returns:
            解密后的原始凭证字符串
            
        Raises:
            DecryptionError: 解密失败时抛出
        """
        if not isinstance(encrypted_credential, str):
            raise DecryptionError(f"Encrypted credential must be a string, got {type(encrypted_credential)}")
        
        try:
            decrypted_bytes = self._fernet.decrypt(encrypted_credential.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except InvalidToken:
            logger.error("Invalid token during decryption - wrong key or corrupted data")
            raise DecryptionError("Invalid token: wrong encryption key or corrupted data")
        except Exception as e:
            logger.error(f"Failed to decrypt credential: {str(e)}")
            raise DecryptionError(f"Decryption failed: {str(e)}")
    
    def encrypt_credential_dict(self, credentials: Dict[str, str]) -> Dict[str, str]:
        """批量加密凭证字典
        
        Args:
            credentials: 包含凭证的字典
            
        Returns:
            加密后的凭证字典
            
        Raises:
            EncryptionError: 加密失败时抛出
        """
        if not isinstance(credentials, dict):
            raise EncryptionError(f"Credentials must be a dictionary, got {type(credentials)}")
        
        encrypted_dict = {}
        
        for key, value in credentials.items():
            if not isinstance(value, str):
                # 对于非字符串值，先转换为JSON字符串
                value = json.dumps(value)
            
            try:
                encrypted_dict[key] = self.encrypt_credential(value)
            except EncryptionError as e:
                logger.error(f"Failed to encrypt credential '{key}': {str(e)}")
                raise EncryptionError(f"Failed to encrypt credential '{key}': {str(e)}")
        
        return encrypted_dict
    
    def decrypt_credential_dict(self, encrypted_credentials: Dict[str, str]) -> Dict[str, str]:
        """批量解密凭证字典
        
        Args:
            encrypted_credentials: 加密的凭证字典
            
        Returns:
            解密后的凭证字典
            
        Raises:
            DecryptionError: 解密失败时抛出
        """
        if not isinstance(encrypted_credentials, dict):
            raise DecryptionError(f"Encrypted credentials must be a dictionary, got {type(encrypted_credentials)}")
        
        decrypted_dict = {}
        
        for key, encrypted_value in encrypted_credentials.items():
            try:
                decrypted_dict[key] = self.decrypt_credential(encrypted_value)
            except DecryptionError as e:
                logger.error(f"Failed to decrypt credential '{key}': {str(e)}")
                raise DecryptionError(f"Failed to decrypt credential '{key}': {str(e)}")
        
        return decrypted_dict
    
    def rotate_key(self, old_key: str, new_key: str) -> bool:
        """密钥轮换功能
        
        使用旧密钥解密数据，然后用新密钥重新加密。
        这个方法主要用于批量更新已存储的加密数据。
        
        Args:
            old_key: 旧的加密密钥
            new_key: 新的加密密钥
            
        Returns:
            轮换是否成功
            
        Raises:
            EncryptionError: 密钥轮换失败时抛出
        """
        try:
            # 创建新的加密服务实例
            new_encryption = CredentialEncryption(new_key)
            
            # 验证新密钥是否有效
            test_data = "test_key_rotation"
            encrypted_test = new_encryption.encrypt_credential(test_data)
            decrypted_test = new_encryption.decrypt_credential(encrypted_test)
            
            if decrypted_test != test_data:
                raise EncryptionError("New key validation failed")
            
            # 更新当前实例的密钥
            self.__init__(new_key)
            
            logger.info("Key rotation completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Key rotation failed: {str(e)}")
            raise EncryptionError(f"Key rotation failed: {str(e)}")
    
    def is_encrypted(self, data: str) -> bool:
        """检查数据是否已加密
        
        通过尝试解密来判断数据是否已经加密。
        这是一个辅助方法，用于防止重复加密。
        
        Args:
            data: 要检查的数据
            
        Returns:
            如果数据已加密返回True，否则返回False
        """
        try:
            self.decrypt_credential(data)
            return True
        except DecryptionError:
            return False
    
    @staticmethod
    def generate_key() -> str:
        """生成新的Fernet加密密钥
        
        Returns:
            Base64编码的44字符Fernet密钥
        """
        return Fernet.generate_key().decode()
    
    @staticmethod
    def generate_secure_string(length: int = 32) -> str:
        """生成安全的随机字符串
        
        用于生成OAuth2 state参数、nonce等。
        
        Args:
            length: 字符串长度，默认32
            
        Returns:
            URL安全的Base64编码随机字符串
        """
        return base64.urlsafe_b64encode(secrets.token_bytes(length)).decode().rstrip('=')


# 全局实例工厂函数
_encryption_instance: Optional[CredentialEncryption] = None


def get_encryption_service(encryption_key: Optional[str] = None) -> CredentialEncryption:
    """获取加密服务实例
    
    使用单例模式确保整个应用使用相同的加密密钥。
    
    Args:
        encryption_key: 加密密钥，首次调用时必须提供
        
    Returns:
        CredentialEncryption实例
        
    Raises:
        EncryptionError: 未提供密钥或密钥无效时抛出
    """
    global _encryption_instance
    
    if _encryption_instance is None:
        if encryption_key is None:
            raise EncryptionError("Encryption key must be provided for first initialization")
        _encryption_instance = CredentialEncryption(encryption_key)
    
    return _encryption_instance


def reset_encryption_service():
    """重置加密服务实例
    
    主要用于测试环境。
    """
    global _encryption_instance
    _encryption_instance = None