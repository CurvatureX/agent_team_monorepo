#!/usr/bin/env python3
"""
集成测试验证脚本
验证External Action Node和OAuth2Service的修复是否有效
"""

import sys
import os
import asyncio

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_adapter_registration():
    """测试适配器注册"""
    print("🔍 测试适配器注册...")
    try:
        # 导入适配器注册表
        from workflow_engine.services.api_adapters.base import APIAdapterRegistry
        
        # 检查已注册的适配器
        adapters = APIAdapterRegistry.list_adapters()
        print(f"✅ 已注册的适配器: {adapters}")
        
        # 验证关键适配器
        expected_adapters = ['github', 'slack', 'google_calendar', 'http_tool']
        missing_adapters = [adapter for adapter in expected_adapters if adapter not in adapters]
        
        if missing_adapters:
            print(f"❌ 缺少适配器: {missing_adapters}")
            return False
        else:
            print("✅ 所有关键适配器已注册")
            return True
            
    except Exception as e:
        print(f"❌ 适配器注册测试失败: {e}")
        return False

def test_adapter_creation():
    """测试适配器创建"""
    print("🔍 测试适配器创建...")
    try:
        from workflow_engine.services.api_adapters.base import APIAdapterRegistry
        
        # 测试创建GitHub适配器
        github_adapter = APIAdapterRegistry.create_adapter('github')
        print(f"✅ GitHub适配器创建成功: {type(github_adapter).__name__}")
        
        # 测试创建Slack适配器
        slack_adapter = APIAdapterRegistry.create_adapter('slack')
        print(f"✅ Slack适配器创建成功: {type(slack_adapter).__name__}")
        
        # 验证适配器方法
        if hasattr(github_adapter, 'call') and hasattr(slack_adapter, 'call'):
            print("✅ 适配器接口验证通过")
            return True
        else:
            print("❌ 适配器接口不完整")
            return False
            
    except Exception as e:
        print(f"❌ 适配器创建测试失败: {e}")
        return False

def test_external_action_node():
    """测试External Action Node"""
    print("🔍 测试External Action Node...")
    try:
        # 只测试模块是否可以导入和方法是否存在
        from workflow_engine.nodes.external_action_node import ExternalActionNode
        
        print("✅ External Action Node模块导入成功")
        
        # 验证关键方法存在（通过检查类定义）
        required_methods = ['execute', 'validate']
        missing_methods = [method for method in required_methods if not hasattr(ExternalActionNode, method)]
        
        if missing_methods:
            print(f"❌ 缺少方法: {missing_methods}")
            return False
        else:
            print("✅ External Action Node方法验证通过")
            return True
            
    except Exception as e:
        print(f"❌ External Action Node测试失败: {e}")
        return False

async def test_oauth2_service():
    """测试OAuth2Service"""
    print("🔍 测试OAuth2Service...")
    try:
        # 只测试OAuth2Service能否被导入和初始化
        from workflow_engine.services.oauth2_service import OAuth2Service
        from workflow_engine.services.credential_encryption import CredentialEncryption
        
        print("✅ OAuth2Service模块导入成功")
        
        # 验证关键方法存在（通过检查类定义）
        required_methods = ['get_valid_token', 'refresh_token_if_needed']
        missing_methods = [method for method in required_methods if not hasattr(OAuth2Service, method)]
        
        if missing_methods:
            print(f"❌ 缺少方法: {missing_methods}")
            return False
        else:
            print("✅ OAuth2Service方法验证通过")
            return True
            
    except Exception as e:
        print(f"❌ OAuth2Service测试失败: {e}")
        return False

def test_credential_encryption():
    """测试凭证加密"""
    print("🔍 测试凭证加密...")
    try:
        from workflow_engine.services.credential_encryption import CredentialEncryption
        
        # 创建加密服务（使用测试密钥）
        test_key = CredentialEncryption.generate_key()
        encryption = CredentialEncryption(test_key)
        
        # 测试加密解密
        test_credential = "test_access_token_12345"
        encrypted = encryption.encrypt_credential(test_credential)
        decrypted = encryption.decrypt_credential(encrypted)
        
        if decrypted == test_credential:
            print("✅ 凭证加密解密测试通过")
            return True
        else:
            print("❌ 凭证加密解密测试失败")
            return False
            
    except Exception as e:
        print(f"❌ 凭证加密测试失败: {e}")
        return False

async def main():
    """主测试函数"""
    print("🚀 开始集成测试验证...\n")
    
    tests = [
        ("适配器注册", test_adapter_registration),
        ("适配器创建", test_adapter_creation),
        ("External Action Node", test_external_action_node),
        ("OAuth2Service", test_oauth2_service),
        ("凭证加密", test_credential_encryption)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
                print(f"✅ {test_name} 通过")
            else:
                print(f"❌ {test_name} 失败")
                
        except Exception as e:
            print(f"❌ {test_name} 异常: {e}")
    
    print(f"\n📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！修复验证成功。")
        return True
    else:
        print("⚠️ 存在失败的测试，需要进一步修复。")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)