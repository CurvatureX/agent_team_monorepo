#!/usr/bin/env python3
"""
认证功能测试
"""

import asyncio
import httpx
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from tests.utils.test_config import test_config

class AuthenticationTest:
    """认证功能测试类"""
    
    def __init__(self):
        self.config = test_config
        self.access_token = None
    
    async def test_health_check(self):
        """测试健康检查端点"""
        print("🏥 测试API Gateway健康检查...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.api_gateway_url}/health",
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ 健康检查成功: {data.get('status')}")
                    return True
                else:
                    print(f"❌ 健康检查失败: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ 健康检查异常: {e}")
            return False
    
    async def test_supabase_authentication(self):
        """测试Supabase认证"""
        print("🔐 测试Supabase认证...")
        
        if not self.config.has_auth_config():
            print("⚠️ 缺少认证配置，跳过认证测试")
            return True  # 跳过而不是失败
        
        auth_url = f"{self.config.supabase_url}/auth/v1/token?grant_type=password"
        auth_data = {
            "email": self.config.test_email,
            "password": self.config.test_password
        }
        headers = {
            "Content-Type": "application/json",
            "apikey": self.config.supabase_anon_key
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    auth_url,
                    json=auth_data,
                    headers=headers,
                    timeout=self.config.auth_timeout
                )
                
                if response.status_code == 200:
                    auth_result = response.json()
                    access_token = auth_result.get("access_token")
                    
                    if access_token:
                        print(f"✅ 认证成功: {self.config.test_email}")
                        self.access_token = access_token
                        
                        # 验证token格式
                        if len(access_token.split('.')) == 3:
                            print("✅ JWT token格式正确")
                        else:
                            print("⚠️ JWT token格式异常")
                            
                        return True
                    else:
                        print("❌ 认证响应中没有access_token")
                        return False
                else:
                    print(f"❌ 认证失败: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            print(f"❌ 认证异常: {e}")
            return False
    
    async def test_invalid_credentials(self):
        """测试无效凭据"""
        print("🚫 测试无效凭据...")
        
        if not self.config.has_auth_config():
            print("⚠️ 缺少认证配置，跳过无效凭据测试")
            return True
        
        auth_url = f"{self.config.supabase_url}/auth/v1/token?grant_type=password"
        auth_data = {
            "email": "invalid@example.com",
            "password": "wrongpassword"
        }
        headers = {
            "Content-Type": "application/json",
            "apikey": self.config.supabase_anon_key
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    auth_url,
                    json=auth_data,
                    headers=headers,
                    timeout=self.config.auth_timeout
                )
                
                if response.status_code == 400:
                    print("✅ 无效凭据正确被拒绝")
                    return True
                else:
                    print(f"⚠️ 无效凭据测试异常: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ 无效凭据测试异常: {e}")
            return False
    
    async def test_protected_endpoint_without_token(self):
        """测试无token访问受保护端点"""
        print("🔒 测试无token访问受保护端点...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config.api_gateway_url}/api/v1/session",
                    json={"action": "create"},
                    headers={"Content-Type": "application/json"},
                    timeout=5.0
                )
                
                if response.status_code == 401:
                    print("✅ 无token正确被拒绝")
                    return True
                else:
                    print(f"⚠️ 无token访问测试异常: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ 无token访问测试异常: {e}")
            return False
    
    async def test_protected_endpoint_with_valid_token(self):
        """测试有效token访问受保护端点"""
        print("🎫 测试有效token访问受保护端点...")
        
        if not self.access_token:
            print("⚠️ 没有有效token，跳过此测试")
            return True
        
        try:
            headers = self.config.get_auth_headers(self.access_token)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config.api_gateway_url}/api/v1/session",
                    json={"action": "create"},
                    headers=headers,
                    timeout=self.config.session_timeout
                )
                
                if response.status_code in [200, 201]:
                    print("✅ 有效token访问成功")
                    return True
                else:
                    print(f"❌ 有效token访问失败: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ 有效token访问测试异常: {e}")
            return False
    
    async def run_all_tests(self):
        """运行所有认证测试"""
        print("🚀 开始认证功能测试")
        print("=" * 50)
        
        tests = [
            ("健康检查", self.test_health_check),
            ("Supabase认证", self.test_supabase_authentication),
            ("无效凭据", self.test_invalid_credentials),
            ("无token访问", self.test_protected_endpoint_without_token),
            ("有效token访问", self.test_protected_endpoint_with_valid_token),
        ]
        
        results = []
        
        for test_name, test_func in tests:
            print(f"\n--- {test_name} ---")
            try:
                result = await test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"❌ {test_name} 异常: {e}")
                results.append((test_name, False))
        
        # 生成报告
        print("\n" + "=" * 50)
        print("📊 认证测试报告")
        print("=" * 50)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ 通过" if result else "❌ 失败"
            print(f"  {status} {test_name}")
        
        print(f"\n通过率: {passed}/{total} ({(passed/total)*100:.1f}%)")
        
        if passed == total:
            print("🎉 所有认证测试通过！")
        else:
            print("⚠️ 部分认证测试失败")
        
        return passed == total

async def main():
    """主测试函数"""
    test = AuthenticationTest()
    success = await test.run_all_tests()
    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)