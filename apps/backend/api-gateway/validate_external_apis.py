#!/usr/bin/env python3
"""
Validate External APIs Integration
验证外部API集成是否正确
"""

import sys
import os

# 添加app目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_imports():
    """测试导入是否正常"""
    print("🔍 Testing imports...")
    
    try:
        # 测试外部API模型
        from models.external_api import (
            ExternalAPIProvider,
            OAuth2AuthorizeRequest,
            OAuth2AuthUrlResponse,
            CredentialInfo,
            TestAPICallRequest,
            TestAPICallResponse,
            StatusResponse
        )
        print("✅ External API models imported successfully")
        
        # 测试枚举值
        assert ExternalAPIProvider.GOOGLE_CALENDAR.value == "google_calendar"
        assert ExternalAPIProvider.GITHUB.value == "github"
        assert ExternalAPIProvider.SLACK.value == "slack"
        print("✅ External API provider enum values correct")
        
        # 测试模型创建
        auth_request = OAuth2AuthorizeRequest(
            provider=ExternalAPIProvider.GOOGLE_CALENDAR,
            scopes=["calendar.read"]
        )
        assert auth_request.provider == ExternalAPIProvider.GOOGLE_CALENDAR
        print("✅ External API models work correctly")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_router_structure():
    """测试路由器结构"""
    print("\n🔍 Testing router structure...")
    
    try:
        # 验证路由文件存在
        external_apis_file = os.path.join('app', 'api', 'app', 'external_apis.py')
        if not os.path.exists(external_apis_file):
            print(f"❌ External APIs router file not found: {external_apis_file}")
            return False
        
        # 检查主要函数是否定义
        with open(external_apis_file, 'r') as f:
            content = f.read()
            
        required_functions = [
            "start_oauth2_authorization",
            "oauth2_callback",
            "list_user_credentials",
            "revoke_credential",
            "test_api_call",
            "get_external_api_status",
            "get_external_api_metrics"
        ]
        
        for func in required_functions:
            if f"async def {func}" in content:
                print(f"✅ Function {func} defined")
            else:
                print(f"❌ Function {func} missing")
                return False
        
        # 检查路由是否正确定义
        required_routes = [
            '@router.post("/auth/authorize"',
            '@router.get("/auth/callback"',
            '@router.get("/credentials"',
            '@router.delete("/credentials/{provider}"',
            '@router.post("/test-call"',
            '@router.get("/status"',
            '@router.get("/metrics"'
        ]
        
        for route in required_routes:
            if route in content:
                print(f"✅ Route {route} defined")
            else:
                print(f"❌ Route {route} missing")
                return False
        
        print("✅ Router structure is correct")
        return True
        
    except Exception as e:
        print(f"❌ Error testing router structure: {e}")
        return False

def test_integration():
    """测试集成是否正确"""
    print("\n🔍 Testing API integration...")
    
    try:
        # 检查是否已添加到主路由器
        router_file = os.path.join('app', 'api', 'app', 'router.py')
        with open(router_file, 'r') as f:
            content = f.read()
        
        if "external_apis" in content and 'prefix="/external-apis"' in content:
            print("✅ External APIs router integrated correctly")
            return True
        else:
            print("❌ External APIs router not integrated")
            return False
            
    except Exception as e:
        print(f"❌ Error testing integration: {e}")
        return False

def main():
    """主验证函数"""
    print("🚀 Validating External APIs Integration\n")
    
    results = []
    results.append(test_imports())
    results.append(test_router_structure())
    results.append(test_integration())
    
    print(f"\n📊 Validation Results:")
    print(f"✅ Passed: {sum(results)}")
    print(f"❌ Failed: {len(results) - sum(results)}")
    
    if all(results):
        print("\n🎉 All validations passed! External APIs integration is ready.")
        return 0
    else:
        print("\n💥 Some validations failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())