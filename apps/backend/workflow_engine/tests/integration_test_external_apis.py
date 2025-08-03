#!/usr/bin/env python3
"""
External API Integration Test
外部API集成的端到端测试脚本
"""

import asyncio
import json
import os
import sys
from typing import Dict, Any

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from workflow_engine.services.api_adapters.base import APIAdapter
from workflow_engine.services.api_adapters.google_calendar import GoogleCalendarAdapter
from workflow_engine.services.api_adapters.github import GitHubAdapter
from workflow_engine.services.api_adapters.slack import SlackAdapter
from workflow_engine.services.api_adapters.http_tool import HTTPToolAdapter
from workflow_engine.services.credential_encryption import CredentialEncryption, EncryptionError
from workflow_engine.services.oauth2_service import OAuth2Service
from workflow_engine.nodes.external_action_node import ExternalActionNode, ExternalActionConfig


class ExternalAPIIntegrationTest:
    """外部API集成测试类"""
    
    def __init__(self):
        self.test_results = []
        self.encryption_key = "test_key_12345678901234567890123456789012"  # 32字节测试密钥
        
    def log_result(self, test_name: str, success: bool, message: str = "", details: Any = None):
        """记录测试结果"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        
        if details and not success:
            print(f"   Details: {details}")
    
    async def test_credential_encryption(self):
        """测试凭证加密服务"""
        test_name = "Credential Encryption Service"
        
        try:
            encryption = CredentialEncryption(self.encryption_key)
            
            # 测试加密解密
            test_credential = "test_access_token_12345"
            encrypted = encryption.encrypt_credential(test_credential)
            decrypted = encryption.decrypt_credential(encrypted)
            
            assert decrypted == test_credential, "Encryption/decryption mismatch"
            assert encrypted != test_credential, "Credential not encrypted"
            
            # 测试批量加密
            test_dict = {
                "access_token": "token123",
                "refresh_token": "refresh456"
            }
            encrypted_dict = encryption.encrypt_credential_dict(test_dict)
            decrypted_dict = encryption.decrypt_credential_dict(encrypted_dict)
            
            assert decrypted_dict == test_dict, "Dict encryption failed"
            
            self.log_result(test_name, True, "Encryption/decryption working correctly")
            
        except Exception as e:
            self.log_result(test_name, False, f"Encryption test failed: {str(e)}")
    
    async def test_api_adapters(self):
        """测试API适配器"""
        # 测试凭证 (Mock)
        mock_credentials = {
            "access_token": "mock_token_for_testing"
        }
        
        adapters = [
            ("Google Calendar", GoogleCalendarAdapter()),
            ("GitHub", GitHubAdapter()),
            ("Slack", SlackAdapter()),
            ("HTTP Tool", HTTPToolAdapter())
        ]
        
        for name, adapter in adapters:
            test_name = f"API Adapter - {name}"
            
            try:
                # 测试凭证验证
                is_valid = adapter.validate_credentials(mock_credentials)
                assert is_valid, f"{name} credentials validation failed"
                
                # 测试OAuth2配置获取
                oauth2_config = adapter.get_oauth2_config()
                assert oauth2_config is not None, f"{name} OAuth2 config is None"
                
                # 测试操作列表
                assert hasattr(adapter, 'OPERATIONS'), f"{name} missing OPERATIONS"
                assert len(adapter.OPERATIONS) > 0, f"{name} has no operations defined"
                
                self.log_result(test_name, True, f"Basic validation passed, {len(adapter.OPERATIONS)} operations available")
                
            except Exception as e:
                self.log_result(test_name, False, f"Adapter test failed: {str(e)}")
    
    async def test_oauth2_service(self):
        """测试OAuth2服务"""
        test_name = "OAuth2 Service"
        
        try:
            # 注意：这里创建的OAuth2Service没有数据库连接，只测试基本功能
            oauth2_service = OAuth2Service(
                encryption_key=self.encryption_key,
                # 传入None作为数据库连接，测试基本功能
                supabase_client=None
            )
            
            # 测试Provider配置
            providers = ["google_calendar", "github", "slack"]
            for provider in providers:
                config = oauth2_service._get_provider_config(provider)
                assert config is not None, f"No config for {provider}"
                assert "client_id_env" in config, f"Missing client_id_env for {provider}"
                assert "auth_url" in config, f"Missing auth_url for {provider}"
            
            self.log_result(test_name, True, f"Provider configurations validated for {len(providers)} providers")
            
        except Exception as e:
            self.log_result(test_name, False, f"OAuth2 service test failed: {str(e)}")
    
    async def test_external_action_node(self):
        """测试External Action Node"""
        test_name = "External Action Node"
        
        try:
            # 创建节点配置
            config = ExternalActionConfig(
                api_service="google_calendar",
                operation="list_events",
                parameters={
                    "calendar_id": "primary",
                    "time_min": "2025-08-01T00:00:00Z",
                    "time_max": "2025-08-31T23:59:59Z"
                }
            )
            
            # 创建节点实例
            node = ExternalActionNode(
                id="test_external_action",
                name="Test External Action",
                parameters=config.__dict__,
                oauth2_service=None  # Mock service
            )
            
            # 验证节点配置
            assert node.node_type == "EXTERNAL_ACTION", "Wrong node type"
            assert hasattr(node, '_create_config'), "Missing config creation method"
            
            # 测试配置创建
            created_config = node._create_config(config.__dict__)
            assert isinstance(created_config, ExternalActionConfig), "Config creation failed"
            assert created_config.api_service == "google_calendar", "Config mismatch"
            
            self.log_result(test_name, True, "Node creation and configuration successful")
            
        except Exception as e:
            self.log_result(test_name, False, f"External Action Node test failed: {str(e)}")
    
    async def test_http_tool_adapter(self):
        """测试HTTP工具适配器"""
        test_name = "HTTP Tool Adapter"
        
        try:
            adapter = HTTPToolAdapter()
            
            # 测试基本配置
            assert adapter.OPERATIONS, "No operations defined"
            assert "http_request" in adapter.OPERATIONS, "Missing http_request operation"
            
            # 测试凭证验证 (HTTP工具可以无凭证运行)
            assert adapter.validate_credentials({}), "Empty credentials should be valid"
            assert adapter.validate_credentials({"api_key": "test"}), "API key credentials should be valid"
            
            self.log_result(test_name, True, "HTTP Tool Adapter validation successful")
            
        except Exception as e:
            self.log_result(test_name, False, f"HTTP Tool Adapter test failed: {str(e)}")
    
    def print_summary(self):
        """打印测试总结"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print("\n" + "="*60)
        print("EXTERNAL API INTEGRATION TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        if failed_tests > 0:
            print("\nFailed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['message']}")
        
        print("\nIntegration Status:")
        if failed_tests == 0:
            print("🎉 All tests passed! External API integration is working correctly.")
        elif failed_tests <= 2:
            print("⚠️  Most tests passed with minor issues.")
        else:
            print("🚨 Multiple test failures detected. Review implementation.")
    
    async def run_all_tests(self):
        """运行所有集成测试"""
        print("Starting External API Integration Tests...\n")
        
        test_methods = [
            self.test_credential_encryption,
            self.test_api_adapters,
            self.test_oauth2_service,
            self.test_external_action_node,
            self.test_http_tool_adapter
        ]
        
        for test_method in test_methods:
            try:
                await test_method()
            except Exception as e:
                test_name = test_method.__name__.replace('test_', '').replace('_', ' ').title()
                self.log_result(test_name, False, f"Test execution failed: {str(e)}")
        
        self.print_summary()


async def main():
    """主函数"""
    test_suite = ExternalAPIIntegrationTest()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())