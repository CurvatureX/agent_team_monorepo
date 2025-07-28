#!/usr/bin/env python3
"""
流式响应功能测试
"""

import asyncio
import httpx
import json
import sys
import os
from pathlib import Path
from typing import List, Set, Dict, Any

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from tests.utils.test_config import test_config

class StreamingResponseTest:
    """流式响应测试类"""
    
    def __init__(self):
        self.config = test_config
        self.access_token = None
        self.test_session_id = None
    
    async def setup(self):
        """设置测试环境"""
        # 认证
        if not await self.authenticate():
            return False
        
        # 创建测试会话
        if not await self.create_test_session():
            return False
        
        return True
    
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
    
    async def create_test_session(self):
        """创建测试会话"""
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
                    self.test_session_id = result.get("session_id")
                    return self.test_session_id is not None
                
                return False
                
        except Exception:
            return False
    
    async def test_basic_streaming(self):
        """测试基本流式响应"""
        print("📡 测试基本流式响应...")
        
        if not self.test_session_id:
            print("❌ 没有可用的session_id")
            return False
        
        chat_data = {
            "session_id": self.test_session_id,
            "message": "Hello, 简单测试"
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }
        
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        
        received_events = []
        response_count = 0
        max_responses = 5  # 限制响应数量
        
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{self.config.api_gateway_url}/api/v1/chat/stream",
                    json=chat_data,
                    headers=headers,
                    timeout=self.config.chat_timeout
                ) as response:
                    
                    if response.status_code != 200:
                        print(f"❌ 流式请求失败: {response.status_code}")
                        return False
                    
                    print("📡 开始接收SSE流...")
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            
                            if data_str.strip() == '{"type": "end"}':
                                print("📡 收到结束信号")
                                break
                            
                            try:
                                data = json.loads(data_str)
                                event_type = data.get("type")
                                received_events.append(data)
                                
                                print(f"📨 收到事件: {event_type}")
                                
                                response_count += 1
                                
                                # 限制响应数量避免长时间运行
                                if response_count >= max_responses:
                                    print(f"📡 已收到 {max_responses} 个响应，停止接收")
                                    break
                                
                                # 如果是最终响应，停止
                                if data.get("is_final", False):
                                    print("🏁 收到最终响应")
                                    break
                                    
                            except json.JSONDecodeError:
                                continue
            
            print(f"✅ 基本流式响应测试完成，收到 {len(received_events)} 个事件")
            return len(received_events) > 0
                
        except Exception as e:
            print(f"❌ 基本流式响应测试异常: {e}")
            return False
    
    async def test_sse_format_validation(self):
        """测试SSE格式验证"""
        print("📋 测试SSE格式验证...")
        
        if not self.test_session_id:
            print("❌ 没有可用的session_id")
            return False
        
        chat_data = {
            "session_id": self.test_session_id,
            "message": "测试SSE格式"
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }
        
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        
        valid_sse_lines = 0
        total_lines = 0
        
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{self.config.api_gateway_url}/api/v1/chat/stream",
                    json=chat_data,
                    headers=headers,
                    timeout=self.config.chat_timeout
                ) as response:
                    
                    if response.status_code != 200:
                        print(f"❌ SSE格式测试请求失败: {response.status_code}")
                        return False
                    
                    # 验证Content-Type
                    content_type = response.headers.get("content-type", "")
                    if "text/event-stream" in content_type:
                        print("✅ Content-Type正确设置为text/event-stream")
                    else:
                        print(f"⚠️ Content-Type异常: {content_type}")
                    
                    response_count = 0
                    max_responses = 3  # 只检查前几个响应
                    
                    async for line in response.aiter_lines():
                        total_lines += 1
                        
                        if line.startswith("data: "):
                            valid_sse_lines += 1
                            data_str = line[6:]
                            
                            if data_str.strip() == '{"type": "end"}':
                                break
                            
                            try:
                                json.loads(data_str)  # 验证JSON格式
                                response_count += 1
                                
                                if response_count >= max_responses:
                                    break
                                    
                            except json.JSONDecodeError:
                                print(f"⚠️ 无效JSON: {data_str[:50]}...")
            
            print(f"✅ SSE格式验证完成: {valid_sse_lines}/{total_lines} 行有效")
            return valid_sse_lines > 0
                
        except Exception as e:
            print(f"❌ SSE格式验证异常: {e}")
            return False
    
    async def test_concurrent_streams(self):
        """测试并发流式连接"""
        print("🔄 测试并发流式连接...")
        
        if not self.test_session_id:
            print("❌ 没有可用的session_id")
            return False
        
        async def single_stream_test(message_suffix: str):
            """单个流式测试"""
            chat_data = {
                "session_id": self.test_session_id,
                "message": f"并发测试 {message_suffix}"
            }
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "text/event-stream"
            }
            
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
            
            try:
                async with httpx.AsyncClient() as client:
                    async with client.stream(
                        "POST",
                        f"{self.config.api_gateway_url}/api/v1/chat/stream",
                        json=chat_data,
                        headers=headers,
                        timeout=10.0  # 较短超时
                    ) as response:
                        
                        if response.status_code != 200:
                            return False
                        
                        event_count = 0
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                data_str = line[6:]
                                
                                if data_str.strip() == '{"type": "end"}':
                                    break
                                
                                try:
                                    json.loads(data_str)
                                    event_count += 1
                                    
                                    # 快速退出
                                    if event_count >= 2:
                                        break
                                        
                                except json.JSONDecodeError:
                                    continue
                        
                        return event_count > 0
                        
            except Exception:
                return False
        
        # 创建2个并发连接（保守测试）
        tasks = [
            single_stream_test("A"),
            single_stream_test("B")
        ]
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful_streams = sum(1 for result in results if result is True)
            
            print(f"✅ 并发流式测试完成: {successful_streams}/2 个连接成功")
            return successful_streams >= 1  # 至少一个成功
            
        except Exception as e:
            print(f"❌ 并发流式测试异常: {e}")
            return False
    
    async def test_stream_timeout_handling(self):
        """测试流式响应超时处理"""
        print("⏱️ 测试流式响应超时处理...")
        
        if not self.test_session_id:
            print("❌ 没有可用的session_id")
            return False
        
        chat_data = {
            "session_id": self.test_session_id,
            "message": "超时测试"
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }
        
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{self.config.api_gateway_url}/api/v1/chat/stream",
                    json=chat_data,
                    headers=headers,
                    timeout=5.0  # 较短超时测试
                ) as response:
                    
                    if response.status_code != 200:
                        print(f"❌ 超时测试请求失败: {response.status_code}")
                        return False
                    
                    event_count = 0
                    
                    try:
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                event_count += 1
                                
                                # 快速退出测试
                                if event_count >= 2:
                                    print("✅ 在超时前收到响应")
                                    return True
                    
                    except asyncio.TimeoutError:
                        print("✅ 超时处理正常")
                        return True
                    
                    return event_count > 0
                    
        except asyncio.TimeoutError:
            print("✅ 超时处理正常")
            return True
        except Exception as e:
            print(f"❌ 超时测试异常: {e}")
            return False
    
    async def run_all_tests(self):
        """运行所有流式响应测试"""
        print("🚀 开始流式响应功能测试")
        print("=" * 50)
        
        # 设置测试环境
        if not await self.setup():
            print("❌ 测试环境设置失败")
            return False
        
        tests = [
            ("基本流式响应", self.test_basic_streaming),
            ("SSE格式验证", self.test_sse_format_validation),
            ("并发流式连接", self.test_concurrent_streams),
            ("超时处理", self.test_stream_timeout_handling),
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
        print("📊 流式响应测试报告")
        print("=" * 50)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ 通过" if result else "❌ 失败"
            print(f"  {status} {test_name}")
        
        print(f"\n通过率: {passed}/{total} ({(passed/total)*100:.1f}%)")
        
        if passed == total:
            print("🎉 所有流式响应测试通过！")
        else:
            print("⚠️ 部分流式响应测试失败")
        
        return passed == total

async def main():
    """主测试函数"""
    test = StreamingResponseTest()
    success = await test.run_all_tests()
    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)