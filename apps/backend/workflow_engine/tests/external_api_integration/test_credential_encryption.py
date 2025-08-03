"""
凭证加密服务测试
测试加密解密功能、密钥管理和错误处理
"""

import pytest
from unittest.mock import patch, Mock
from cryptography.fernet import Fernet

# 导入实际实现的加密服务
from workflow_engine.services.credential_encryption import (
    CredentialEncryption,
    EncryptionError,
    DecryptionError
)

@pytest.mark.unit
class TestCredentialEncryption:
    """凭证加密服务单元测试"""
    
    def test_encrypt_credential_success(self, mock_encryption_key):
        """测试：成功加密凭证"""
        encryption_service = CredentialEncryption(mock_encryption_key)
        credential = "test_access_token_12345"
        encrypted = encryption_service.encrypt_credential(credential)
        
        # 验证
        assert encrypted != credential  # 加密后应该不同
        assert len(encrypted) > len(credential)  # 加密后长度增加
        assert isinstance(encrypted, str)  # 返回字符串
    
    def test_decrypt_credential_success(self, mock_encryption_key):
        """测试：成功解密凭证"""
        encryption_service = CredentialEncryption(mock_encryption_key)
        original_credential = "test_access_token_12345"
        
        # 加密然后解密
        encrypted = encryption_service.encrypt_credential(original_credential)
        decrypted = encryption_service.decrypt_credential(encrypted)
        
        # 验证往返一致性
        assert decrypted == original_credential
    
    def test_encrypt_credential_dict_success(self, mock_encryption_key):
        """测试：批量加密凭证字典"""
        encryption_service = CredentialEncryption(mock_encryption_key)
        credentials = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "client_secret": "test_client_secret"
        }
        
        encrypted_dict = encryption_service.encrypt_credential_dict(credentials)
        
        # 验证
        assert len(encrypted_dict) == len(credentials)
        for key in credentials.keys():
            assert key in encrypted_dict
            assert encrypted_dict[key] != credentials[key]  # 值已加密
    
    def test_decrypt_credential_dict_success(self, mock_encryption_key):
        """测试：批量解密凭证字典"""
        encryption_service = CredentialEncryption(mock_encryption_key)
        original_credentials = {
            "access_token": "test_access_token", 
            "refresh_token": "test_refresh_token"
        }
        
        # 加密然后解密
        encrypted_dict = encryption_service.encrypt_credential_dict(original_credentials)
        decrypted_dict = encryption_service.decrypt_credential_dict(encrypted_dict)
        
        # 验证往返一致性
        assert decrypted_dict == original_credentials
    
    def test_invalid_encryption_key_raises_error(self):
        """测试：无效加密密钥抛出异常"""
        # 测试None密钥
        with pytest.raises(EncryptionError):
            CredentialEncryption(None)
        
        # 测试空字符串
        with pytest.raises(EncryptionError):
            CredentialEncryption("")
    
    def test_decrypt_with_wrong_key_raises_error(self, mock_encryption_key):
        """测试：使用错误密钥解密抛出异常"""
        encryption_service = CredentialEncryption(mock_encryption_key)
        credential = "test_credential"
        encrypted = encryption_service.encrypt_credential(credential)
        
        # 使用不同的密钥尝试解密
        different_key = Fernet.generate_key().decode()
        wrong_service = CredentialEncryption(different_key)
        
        with pytest.raises(DecryptionError):
            wrong_service.decrypt_credential(encrypted)
    
    def test_decrypt_invalid_data_raises_error(self, mock_encryption_key):
        """测试：解密无效数据抛出异常"""
        encryption_service = CredentialEncryption(mock_encryption_key)
        invalid_encrypted_data = "not_encrypted_data"
        
        with pytest.raises(DecryptionError):
            encryption_service.decrypt_credential(invalid_encrypted_data)
    
    def test_empty_credential_handling(self, mock_encryption_key):
        """测试：空凭证处理"""
        encryption_service = CredentialEncryption(mock_encryption_key)
        
        # 测试空字符串
        encrypted_empty = encryption_service.encrypt_credential("")
        decrypted_empty = encryption_service.decrypt_credential(encrypted_empty)
        assert decrypted_empty == ""
        
        # 测试空字典
        empty_dict = {}
        encrypted_dict = encryption_service.encrypt_credential_dict(empty_dict)
        decrypted_dict = encryption_service.decrypt_credential_dict(encrypted_dict)
        assert decrypted_dict == empty_dict
    
    def test_key_rotation_functionality(self, mock_encryption_key):
        """测试：密钥轮换功能"""
        old_service = CredentialEncryption(mock_encryption_key)
        credential = "test_credential_for_rotation"
        
        # 生成新密钥
        new_key = Fernet.generate_key().decode()
        
        # 执行密钥轮换
        success = old_service.rotate_key(mock_encryption_key, new_key)
        assert success is True
        
        # 验证轮换后可以加密解密
        test_data = "test_after_rotation"
        encrypted = old_service.encrypt_credential(test_data)
        decrypted = old_service.decrypt_credential(encrypted)
        assert decrypted == test_data

@pytest.mark.unit
class TestEncryptionPerformance:
    """加密性能测试"""
    
    def test_encryption_performance_benchmark(self, mock_encryption_key):
        """测试：加密性能基准测试"""
        import time
        
        encryption_service = CredentialEncryption(mock_encryption_key)
        test_credentials = [f"test_token_{i}" for i in range(1000)]
        
        start_time = time.time()
        for credential in test_credentials:
            encrypted = encryption_service.encrypt_credential(credential)
            decrypted = encryption_service.decrypt_credential(encrypted)
            assert decrypted == credential
        end_time = time.time()
        
        # 验证性能：1000次加密解密应在1秒内完成
        execution_time = end_time - start_time
        assert execution_time < 1.0, f"Encryption too slow: {execution_time}s"
    
    def test_large_credential_handling(self, mock_encryption_key):
        """测试：大型凭证数据处理"""
        import json
        encryption_service = CredentialEncryption(mock_encryption_key)
        
        # 测试大型JSON凭证（模拟复杂的OAuth2响应）
        large_credential = json.dumps({
            "access_token": "a" * 1000,  # 1KB access token
            "refresh_token": "r" * 1000,  # 1KB refresh token
            "metadata": {"data": "x" * 5000}  # 5KB metadata
        })
        
        encrypted = encryption_service.encrypt_credential(large_credential)
        decrypted = encryption_service.decrypt_credential(encrypted)
        
        assert decrypted == large_credential
        assert len(encrypted) > len(large_credential)  # 加密后会增长