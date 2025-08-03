#!/usr/bin/env python3
"""
最小化验证脚本
验证关键修复是否有效，避免数据库依赖问题
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_adapter_registry_fix():
    """测试API适配器注册表修复"""
    print("🔍 测试API适配器注册表修复...")
    try:
        # 测试能否成功导入注册表
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
            
        # 测试适配器创建
        github_adapter = APIAdapterRegistry.create_adapter('github')
        print(f"✅ GitHub适配器创建成功: {type(github_adapter).__name__}")
        
        return True
            
    except Exception as e:
        print(f"❌ 适配器注册表测试失败: {e}")
        return False

def test_imports_only():
    """只测试关键模块能否导入"""
    print("🔍 测试关键模块导入...")
    
    tests = [
        ("External Action Node", "workflow_engine.nodes.external_action_node"),
        ("OAuth2Service", "workflow_engine.services.oauth2_service"),
        ("CredentialEncryption", "workflow_engine.services.credential_encryption")
    ]
    
    passed = 0
    for name, module_path in tests:
        try:
            __import__(module_path)
            print(f"✅ {name} 模块导入成功")
            passed += 1
        except Exception as e:
            print(f"❌ {name} 模块导入失败: {e}")
    
    return passed == len(tests)

def test_credential_encryption_basic():
    """测试凭证加密基础功能"""
    print("🔍 测试凭证加密基础功能...")
    try:
        from workflow_engine.services.credential_encryption import CredentialEncryption
        
        # 生成测试密钥
        test_key = CredentialEncryption.generate_key()
        print(f"✅ 生成测试密钥: {test_key[:20]}...")
        
        # 创建加密服务
        encryption = CredentialEncryption(test_key)
        print("✅ 加密服务创建成功")
        
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

def main():
    """主测试函数"""
    print("🚀 开始最小化验证测试...\n")
    
    tests = [
        ("API适配器注册表修复", test_adapter_registry_fix),
        ("关键模块导入", test_imports_only),
        ("凭证加密基础功能", test_credential_encryption_basic)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
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
        print("🎉 关键修复验证成功！")
        return True
    else:
        print("⚠️ 存在未通过的测试。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)