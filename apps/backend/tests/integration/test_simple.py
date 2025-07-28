#!/usr/bin/env python3
"""
简化版集成测试 - 快速验证新工作流系统
"""

import asyncio
import httpx
import json
import os
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

class SimpleIntegrationTest:
    def __init__(self):
        self.api_gateway_url = "http://localhost:8000"
        self.test_user_token = None
        
    async def authenticate(self):
        """认证获取token"""
        print("🔐 进行用户认证...")
        
        supabase_url = os.getenv("SUPABASE_URL")
        test_email = os.getenv("TEST_USER_EMAIL")
        test_password = os.getenv("TEST_USER_PASSWORD")
        supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
        
        if not all([supabase_url, test_email, test_password, supabase_anon_key]):
            print("❌ 缺少认证配置")
            return False
        
        auth_url = f"{supabase_url}/auth/v1/token?grant_type=password"
        auth_data = {"email": test_email, "password": test_password}
        headers = {"Content-Type": "application/json", "apikey": supabase_anon_key}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(auth_url, json=auth_data, headers=headers, timeout=10.0)
                
                if response.status_code == 200:
                    auth_result = response.json()
                    access_token = auth_result.get("access_token")
                    if access_token:
                        print(f"✅ 认证成功")
                        self.test_user_token = access_token
                        return True
                    
                print(f"❌ 认证失败: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 认证异常: {e}")
            return False
    
    async def create_session(self):
        """创建会话"""
        print("📝 创建会话...")
        
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
        """测试简单聊天 - 限制响应数量避免超时"""
        print("💬 测试聊天...")
        
        chat_data = {
            "session_id": session_id,
            "message": "创建一个简单的邮件处理工作流"
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }
        
        if self.test_user_token:
            headers["Authorization"] = f"Bearer {self.test_user_token}"
        
        received_types = set()
        response_count = 0
        max_responses = 5  # 限制响应数量
        
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
                    
                    print("📡 接收响应...")
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            
                            if data_str.strip() == '{"type": "end"}':
                                print("📡 收到结束信号")
                                break
                            
                            try:
                                data = json.loads(data_str)
                                event_type = data.get("type")
                                received_types.add(event_type)
                                
                                print(f"📨 收到: {event_type}")
                                
                                if event_type == "ai_message":
                                    content = data.get("content", {})
                                    stage = content.get("stage", "unknown")
                                    text = content.get("text", "")[:100]
                                    print(f"   💬 AI消息 ({stage}): {text}...")
                                
                                elif event_type == "workflow":
                                    workflow = data.get("workflow", {})
                                    name = workflow.get("name", "Unnamed")
                                    print(f"   ⚡ 工作流: {name}")
                                
                                elif event_type == "error":
                                    error = data.get("content", {})
                                    print(f"   ❌ 错误: {error.get('message', 'Unknown')}")
                                
                                response_count += 1
                                
                                # 限制响应数量避免超时
                                if response_count >= max_responses:
                                    print(f"📡 已收到 {max_responses} 个响应，停止接收")
                                    break
                                
                                # 如果是最终响应，停止
                                if data.get("is_final", False):
                                    print("🏁 收到最终响应")
                                    break
                                    
                            except json.JSONDecodeError:
                                continue
            
            print(f"\n📊 测试结果:")
            print(f"收到响应数: {response_count}")
            print(f"响应类型: {received_types}")
            
            # 检查基本功能
            if "ai_message" in received_types or "message" in received_types:
                print("✅ 基本聊天功能正常")
                return True
            else:
                print("❌ 未收到有效响应")
                return False
                
        except Exception as e:
            print(f"❌ 聊天测试异常: {e}")
            return False

async def main():
    print("🚀 开始简化集成测试")
    print("=" * 50)
    
    test = SimpleIntegrationTest()
    
    # 认证
    auth_success = await test.authenticate()
    if not auth_success:
        print("❌ 认证失败，退出测试")
        return False
    
    # 创建会话
    session_id = await test.create_session()
    if not session_id:
        print("❌ 会话创建失败，退出测试")
        return False
    
    # 测试聊天
    chat_success = await test.test_simple_chat(session_id)
    
    print("\n" + "=" * 50)
    if chat_success:
        print("🎉 简化集成测试通过！")
        print("✅ 新工作流系统基本功能正常")
    else:
        print("❌ 简化集成测试失败")
    
    return chat_success

if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)