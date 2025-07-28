#!/usr/bin/env python3
"""
会话管理功能测试
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

class SessionManagementTest:
    """会话管理测试类"""
    
    def __init__(self):
        self.config = test_config
        self.access_token = None
        self.session_ids = []
    
    async def authenticate(self):
        """获取认证token"""
        if not self.config.has_auth_config():
            print("⚠️ 缺少认证配置，跳过认证")
            return True
        
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
                    self.access_token = auth_result.get("access_token")
                    return self.access_token is not None
                
                return False
                
        except Exception:
            return False
    
    async def test_create_session_basic(self):
        """测试基本会话创建"""
        print("📝 测试基本会话创建...")
        
        session_data = {"action": "create"}
        headers = self.config.get_auth_headers(self.access_token)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config.api_gateway_url}/api/v1/session",
                    json=session_data,
                    headers=headers,
                    timeout=self.config.session_timeout
                )
                
                if response.status_code in [200, 201]:
                    result = response.json()
                    session_id = result.get("session_id")
                    
                    if session_id:
                        print(f"✅ 会话创建成功: {session_id}")
                        self.session_ids.append(session_id)
                        
                        # 验证session_id格式
                        if len(session_id) > 10:  # 基本格式检查
                            print("✅ Session ID格式正确")
                        else:
                            print("⚠️ Session ID格式异常")
                        
                        return True
                    else:
                        print("❌ 响应中没有session_id")
                        return False
                else:
                    print(f"❌ 会话创建失败: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ 会话创建异常: {e}")
            return False
    
    async def test_create_session_edit_action(self):
        """测试编辑动作会话创建（需要workflow_id）"""
        print("✏️ 测试编辑动作会话创建...")
        
        # 测试没有workflow_id的edit动作（应该失败）
        session_data = {"action": "edit"}
        headers = self.config.get_auth_headers(self.access_token)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config.api_gateway_url}/api/v1/session",
                    json=session_data,
                    headers=headers,
                    timeout=self.config.session_timeout
                )
                
                if response.status_code == 400:
                    print("✅ 缺少workflow_id的edit动作正确被拒绝")
                    return True
                else:
                    print(f"⚠️ edit动作验证异常: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ edit动作测试异常: {e}")
            return False
    
    async def test_invalid_action(self):
        """测试无效动作"""
        print("🚫 测试无效动作...")
        
        session_data = {"action": "invalid_action"}
        headers = self.config.get_auth_headers(self.access_token)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config.api_gateway_url}/api/v1/session",
                    json=session_data,
                    headers=headers,
                    timeout=self.config.session_timeout
                )
                
                if response.status_code == 400:
                    print("✅ 无效动作正确被拒绝")
                    return True
                else:
                    print(f"⚠️ 无效动作验证异常: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ 无效动作测试异常: {e}")
            return False
    
    async def test_get_session(self):
        """测试获取会话"""
        print("📖 测试获取会话...")
        
        if not self.session_ids:
            print("⚠️ 没有可用的session_id，跳过获取测试")
            return True
        
        session_id = self.session_ids[0]
        headers = self.config.get_auth_headers(self.access_token)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.api_gateway_url}/api/v1/session/{session_id}",
                    headers=headers,
                    timeout=self.config.session_timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if result.get("id") == session_id:
                        print(f"✅ 会话获取成功: {session_id}")
                        return True
                    else:
                        print("❌ 返回的session_id不匹配")
                        return False
                else:
                    print(f"❌ 会话获取失败: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ 会话获取异常: {e}")
            return False
    
    async def test_get_nonexistent_session(self):
        """测试获取不存在的会话"""
        print("🔍 测试获取不存在的会话...")
        
        fake_session_id = "nonexistent-session-id"
        headers = self.config.get_auth_headers(self.access_token)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.api_gateway_url}/api/v1/session/{fake_session_id}",
                    headers=headers,
                    timeout=self.config.session_timeout
                )
                
                if response.status_code == 404:
                    print("✅ 不存在的会话正确返回404")
                    return True
                else:
                    print(f"⚠️ 不存在会话处理异常: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ 不存在会话测试异常: {e}")
            return False
    
    async def test_list_sessions(self):
        """测试列出用户会话"""
        print("📝 测试列出用户会话...")
        
        headers = self.config.get_auth_headers(self.access_token)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.api_gateway_url}/api/v1/sessions",
                    headers=headers,
                    timeout=self.config.session_timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    sessions = result.get("sessions", [])
                    
                    print(f"✅ 会话列表获取成功，找到 {len(sessions)} 个会话")
                    
                    # 验证我们创建的会话在列表中
                    if self.session_ids:
                        session_ids_in_list = [s.get("id") for s in sessions]
                        for session_id in self.session_ids:
                            if session_id in session_ids_in_list:
                                print(f"✅ 创建的会话 {session_id} 在列表中")
                            else:
                                print(f"⚠️ 创建的会话 {session_id} 不在列表中")
                    
                    return True
                else:
                    print(f"❌ 会话列表获取失败: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ 会话列表获取异常: {e}")
            return False
    
    async def run_all_tests(self):
        """运行所有会话管理测试"""
        print("🚀 开始会话管理功能测试")
        print("=" * 50)
        
        # 先进行认证
        if not await self.authenticate():
            print("❌ 认证失败，无法继续会话测试")
            return False
        
        tests = [
            ("基本会话创建", self.test_create_session_basic),
            ("编辑动作验证", self.test_create_session_edit_action),
            ("无效动作验证", self.test_invalid_action),
            ("获取会话", self.test_get_session),
            ("获取不存在会话", self.test_get_nonexistent_session),
            ("列出用户会话", self.test_list_sessions),
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
        print("📊 会话管理测试报告")
        print("=" * 50)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ 通过" if result else "❌ 失败"
            print(f"  {status} {test_name}")
        
        print(f"\n通过率: {passed}/{total} ({(passed/total)*100:.1f}%)")
        print(f"创建的会话数: {len(self.session_ids)}")
        
        if passed == total:
            print("🎉 所有会话管理测试通过！")
        else:
            print("⚠️ 部分会话管理测试失败")
        
        return passed == total

async def main():
    """主测试函数"""
    test = SessionManagementTest()
    success = await test.run_all_tests()
    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)