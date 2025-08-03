#!/usr/bin/env python3
"""
Simple External API Integration Validation
简单的外部API集成验证脚本 (无数据库依赖)
"""

import sys
import os
import asyncio

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_imports():
    """测试关键模块导入"""
    print("Testing module imports...")
    
    try:
        from workflow_engine.services.credential_encryption import CredentialEncryption
        print("✅ CredentialEncryption import successful")
    except Exception as e:
        print(f"❌ CredentialEncryption import failed: {e}")
        return False
    
    try:
        from workflow_engine.services.api_adapters.base import APIAdapter
        print("✅ APIAdapter base import successful")
    except Exception as e:
        print(f"❌ APIAdapter base import failed: {e}")
        return False
    
    try:
        from workflow_engine.services.api_adapters.google_calendar import GoogleCalendarAdapter
        from workflow_engine.services.api_adapters.github import GitHubAdapter
        from workflow_engine.services.api_adapters.slack import SlackAdapter
        from workflow_engine.services.api_adapters.http_tool import HTTPToolAdapter
        print("✅ All API adapters import successful")
    except Exception as e:
        print(f"❌ API adapters import failed: {e}")
        return False
    
    try:
        from workflow_engine.nodes.external_action_node import ExternalActionNode
        print("✅ ExternalActionNode import successful")
    except Exception as e:
        print(f"❌ ExternalActionNode import failed: {e}")
        return False
    
    return True

def test_credential_encryption():
    """测试凭证加密功能"""
    print("\nTesting credential encryption...")
    
    try:
        from workflow_engine.services.credential_encryption import CredentialEncryption
        
        encryption_key = "test_key_12345678901234567890123456789012"  # 32字节
        encryption = CredentialEncryption(encryption_key)
        
        # 测试基本加密解密
        test_credential = "test_access_token_12345"
        encrypted = encryption.encrypt_credential(test_credential)
        decrypted = encryption.decrypt_credential(encrypted)
        
        if decrypted == test_credential and encrypted != test_credential:
            print("✅ Basic encryption/decryption working")
        else:
            print("❌ Basic encryption/decryption failed")
            return False
        
        # 测试字典加密
        test_dict = {"access_token": "token123", "refresh_token": "refresh456"}
        encrypted_dict = encryption.encrypt_credential_dict(test_dict)
        decrypted_dict = encryption.decrypt_credential_dict(encrypted_dict)
        
        if decrypted_dict == test_dict:
            print("✅ Dictionary encryption/decryption working")
        else:
            print("❌ Dictionary encryption/decryption failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Credential encryption test failed: {e}")
        return False

def test_api_adapters():
    """测试API适配器基本功能"""
    print("\nTesting API adapters...")
    
    try:
        from workflow_engine.services.api_adapters.google_calendar import GoogleCalendarAdapter
        from workflow_engine.services.api_adapters.github import GitHubAdapter
        from workflow_engine.services.api_adapters.slack import SlackAdapter
        from workflow_engine.services.api_adapters.http_tool import HTTPToolAdapter
        
        adapters = [
            ("Google Calendar", GoogleCalendarAdapter()),
            ("GitHub", GitHubAdapter()),
            ("Slack", SlackAdapter()),
            ("HTTP Tool", HTTPToolAdapter())
        ]
        
        mock_credentials = {"access_token": "mock_token"}
        
        for name, adapter in adapters:
            # 检查必要属性
            if not hasattr(adapter, 'OPERATIONS'):
                print(f"❌ {name}: Missing OPERATIONS attribute")
                return False
            
            if len(adapter.OPERATIONS) == 0:
                print(f"❌ {name}: No operations defined")
                return False
            
            # 测试凭证验证
            if not adapter.validate_credentials(mock_credentials):
                print(f"❌ {name}: Credential validation failed")
                return False
            
            # 测试OAuth2配置
            try:
                oauth2_config = adapter.get_oauth2_config()
                if oauth2_config is None:
                    print(f"❌ {name}: OAuth2 config is None")
                    return False
            except Exception as e:
                print(f"❌ {name}: OAuth2 config failed: {e}")
                return False
            
            print(f"✅ {name}: {len(adapter.OPERATIONS)} operations available")
        
        return True
        
    except Exception as e:
        print(f"❌ API adapters test failed: {e}")
        return False

def test_external_action_node():
    """测试External Action Node"""
    print("\nTesting External Action Node...")
    
    try:
        from workflow_engine.nodes.external_action_node import ExternalActionNode, ExternalActionConfig
        
        # 创建配置
        config = ExternalActionConfig(
            api_service="google_calendar",
            operation="list_events",
            parameters={"calendar_id": "primary"}
        )
        
        # 创建节点 (不传入OAuth2服务)
        node = ExternalActionNode(
            id="test_node",
            name="Test Node",
            parameters=config.__dict__
        )
        
        if node.node_type != "EXTERNAL_ACTION":
            print("❌ Wrong node type")
            return False
        
        # 测试配置创建
        created_config = node._create_config(config.__dict__)
        if not isinstance(created_config, ExternalActionConfig):
            print("❌ Config creation failed")
            return False
        
        print("✅ External Action Node creation successful")
        return True
        
    except Exception as e:
        print(f"❌ External Action Node test failed: {e}")
        return False

def test_file_structure():
    """检查文件结构完整性"""
    print("\nChecking file structure...")
    
    base_path = os.path.join(os.path.dirname(__file__), '..')
    
    required_files = [
        'workflow_engine/services/credential_encryption.py',
        'workflow_engine/services/api_adapters/base.py',
        'workflow_engine/services/api_adapters/google_calendar.py',
        'workflow_engine/services/api_adapters/github.py',
        'workflow_engine/services/api_adapters/slack.py',
        'workflow_engine/services/api_adapters/http_tool.py',
        'workflow_engine/nodes/external_action_node.py',
        'workflow_engine/nodes/tool_node.py'
    ]
    
    missing_files = []
    for file_path in required_files:
        full_path = os.path.join(base_path, file_path)
        if not os.path.exists(full_path):
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ Missing files:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        return False
    else:
        print(f"✅ All {len(required_files)} required files present")
        return True

def main():
    """主函数"""
    print("="*60)
    print("EXTERNAL API INTEGRATION VALIDATION")
    print("="*60)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Module Imports", test_imports),
        ("Credential Encryption", test_credential_encryption),
        ("API Adapters", test_api_adapters),
        ("External Action Node", test_external_action_node)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        success = test_func()
        results.append((test_name, success))
    
    # 总结
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    
    total_tests = len(results)
    passed_tests = sum(1 for _, success in results if success)
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests} ✅")
    print(f"Failed: {total_tests - passed_tests} ❌")
    print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
    
    if passed_tests == total_tests:
        print("\n🎉 All validation tests passed!")
        print("External API integration implementation is ready for use.")
    else:
        print("\n⚠️ Some validation tests failed:")
        for test_name, success in results:
            if not success:
                print(f"  - {test_name}")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)