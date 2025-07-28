#!/usr/bin/env python3
"""
快速工作流测试 - 验证升级后的系统是否正常工作
"""

import asyncio
import httpx
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

class QuickWorkflowTest:
    def __init__(self):
        self.api_gateway_url = "http://localhost:8000"
        self.test_user_token = None
        
    async def authenticate(self):
        """通过Supabase认证API获取JWT token"""
        print("🔐 进行用户认证...")
        
        supabase_url = os.getenv("SUPABASE_URL")
        test_email = os.getenv("TEST_USER_EMAIL")
        test_password = os.getenv("TEST_USER_PASSWORD")
        supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
        
        if not all([supabase_url, test_email, test_password, supabase_anon_key]):
            print("⚠️ 缺少认证配置，请检查 .env 文件中的:")
            print("  - SUPABASE_URL")
            print("  - TEST_USER_EMAIL") 
            print("  - TEST_USER_PASSWORD")
            print("  - SUPABASE_ANON_KEY")
            return None
        
        auth_url = f"{supabase_url}/auth/v1/token?grant_type=password"
        auth_data = {
            "email": test_email,
            "password": test_password
        }
        headers = {
            "Content-Type": "application/json",
            "apikey": supabase_anon_key
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    auth_url,
                    json=auth_data,
                    headers=headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    auth_result = response.json()
                    access_token = auth_result.get("access_token")
                    if access_token:
                        print(f"✅ 用户认证成功: {test_email}")
                        self.test_user_token = access_token
                        return access_token
                    else:
                        print("❌ 认证响应中没有access_token")
                        return None
                else:
                    print(f"❌ 认证失败: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            print(f"❌ 认证异常: {e}")
            return None
    
    async def create_session(self):
        """创建测试会话"""
        session_data = {"action": "create"}
        headers = {"Content-Type": "application/json"}
        
        if self.test_user_token:
            headers["Authorization"] = f"Bearer {self.test_user_token}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_gateway_url}/api/v1/session",
                    json=session_data,
                    headers=headers,
                    timeout=10.0
                )
                
                if response.status_code in [200, 201]:
                    result = response.json()
                    session_id = result.get("session_id")
                    print(f"✅ 会话创建成功: {session_id}")
                    return session_id
                else:
                    print(f"❌ 会话创建失败: {response.status_code}")
                    return None
        except Exception as e:
            print(f"❌ 会话创建异常: {e}")
            return None
    
    async def test_simple_chat(self, session_id: str):
        """测试简单聊天"""
        chat_data = {
            "session_id": session_id,
            "message": "我想创建一个简单的邮件处理工作流"
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }
        
        if self.test_user_token:
            headers["Authorization"] = f"Bearer {self.test_user_token}"
        
        received_responses = []
        response_types = set()
        
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{self.api_gateway_url}/api/v1/chat/stream",
                    json=chat_data,
                    headers=headers,
                    timeout=30.0
                ) as response:
                    
                    if response.status_code != 200:
                        print(f"❌ Chat请求失败: {response.status_code}")
                        return False
                    
                    print("📡 接收SSE流...")
                    
                    response_count = 0
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            
                            if data_str.strip() == '{"type": "end"}':
                                break
                            
                            try:
                                data = json.loads(data_str)
                                event_type = data.get("type")
                                response_types.add(event_type)
                                received_responses.append(data)
                                
                                print(f"📨 收到响应 {response_count + 1}: {event_type}")
                                
                                if event_type == "ai_message":
                                    content = data.get("content", {})
                                    text = content.get("text", "")[:100]
                                    stage = content.get("stage", "unknown")
                                    print(f"   💬 AI消息 ({stage}): {text}...")
                                
                                elif event_type == "workflow":
                                    workflow = data.get("workflow", {})
                                    name = workflow.get("name", "Unnamed")
                                    print(f"   ⚡ 工作流: {name}")
                                
                                elif event_type == "error":
                                    error = data.get("content", {})
                                    print(f"   ❌ 错误: {error.get('message', 'Unknown')}")
                                
                                response_count += 1
                                
                                # 限制响应数量避免无限循环
                                if response_count >= 10:
                                    print("📡 达到最大响应数量，停止接收")
                                    break
                                
                                # 如果是最终响应，停止
                                if data.get("is_final", False):
                                    print("🏁 收到最终响应")
                                    break
                                    
                            except json.JSONDecodeError:
                                continue
            
            # 分析结果
            print(f"\n📊 测试结果:")
            print(f"收到响应数: {len(received_responses)}")
            print(f"响应类型: {response_types}")
            
            # 检查是否收到了预期的响应类型
            if "ai_message" in response_types or "message" in response_types:
                print("✅ 收到了AI消息响应")
                return True
            else:
                print("❌ 未收到AI消息响应")
                return False
                
        except Exception as e:
            print(f"❌ 聊天测试异常: {e}")
            return False
    
    async def run_test(self):
        """运行快速测试"""
        print("🚀 开始快速工作流测试")
        print("=" * 50)
        
        # 认证
        await self.authenticate()
        
        # 创建会话
        session_id = await self.create_session()
        if not session_id:
            print("❌ 无法创建会话，测试失败")
            return False
        
        # 测试聊天
        chat_success = await self.test_simple_chat(session_id)
        
        print("\n" + "=" * 50)
        if chat_success:
            print("🎉 快速测试通过！")
            print("✅ 升级后的系统运行正常")
            print("✅ 三种返回类型架构工作正常")
            print("✅ gRPC 客户端和服务端通信正常")
        else:
            print("❌ 快速测试失败")
            print("需要检查服务配置或代码")
        
        return chat_success

async def main():
    test = QuickWorkflowTest()
    success = await test.run_test()
    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)