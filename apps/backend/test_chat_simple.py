#!/usr/bin/env python3
"""
简洁版聊天测试脚本 - 只显示关键信息
"""

import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL")
TEST_USER_PASSWORD = os.getenv("TEST_USER_PASSWORD")


class SimpleWorkflowTester:
    def __init__(self):
        self.session = requests.Session()
        self.access_token = None
        self.session_id = None
        
    def authenticate(self):
        """认证"""
        print("\n🔐 认证中...")
        response = self.session.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        if response.status_code == 200:
            self.access_token = response.json().get("access_token")
            print("✅ 认证成功")
            return True
        print(f"❌ 认证失败: {response.status_code}")
        return False
        
    def create_session(self):
        """创建会话"""
        print("\n📝 创建会话...")
        response = self.session.post(
            f"{API_BASE_URL}/api/v1/app/sessions",
            headers={"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"},
            json={"action": "create"}
        )
        if response.status_code == 200:
            self.session_id = response.json()["session"]["id"]
            print(f"✅ 会话创建成功: {self.session_id}")
            return True
        print(f"❌ 会话创建失败: {response.status_code}")
        return False
        
    def chat(self, message):
        """发送消息并处理响应"""
        print(f"\n👤 用户: {message}")
        
        with self.session.post(
            f"{API_BASE_URL}/api/v1/app/chat/stream",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream"
            },
            json={"session_id": self.session_id, "user_message": message},
            stream=True
        ) as response:
            
            if response.status_code != 200:
                print(f"❌ 请求失败: {response.status_code}")
                return
                
            assistant_msg = ""
            current_stage = None
            
            for line in response.iter_lines():
                if line and line.startswith(b'data: '):
                    try:
                        data_str = line[6:].decode('utf-8')
                        if data_str == '[DONE]':
                            break
                        if not data_str.strip():
                            continue
                            
                        event = json.loads(data_str)
                        event_type = event.get('type')
                        event_data = event.get('data', {})
                        
                        # 节点转换
                        if event_type == 'status_change':
                            new_stage = event_data.get('current_stage')
                            if new_stage != current_stage:
                                print(f"\n🔄 工作流阶段: {current_stage or 'start'} → {new_stage}")
                                current_stage = new_stage
                                
                        # 助手消息
                        elif event_type == 'message':
                            content = event_data.get('text', '')
                            assistant_msg += content
                            
                        # 工作流生成
                        elif event_type == 'workflow':
                            print("\n✅ 工作流生成完成!")
                            
                        # 错误
                        elif event_type == 'error':
                            print(f"\n❌ 错误: {event_data.get('error', 'Unknown')}")
                            
                    except json.JSONDecodeError:
                        pass
                        
            if assistant_msg:
                print(f"\n🤖 助手: {assistant_msg[:200]}..." if len(assistant_msg) > 200 else f"\n🤖 助手: {assistant_msg}")
                
    def run(self):
        """运行测试"""
        print("="*50)
        print("工作流聊天测试 (简洁版)")
        print("="*50)
        
        if not self.authenticate():
            return
            
        if not self.create_session():
            return
            
        print("\n💬 开始聊天 (输入 'exit' 退出)\n")
        
        while True:
            try:
                user_input = input("\n> ")
                if user_input.lower() in ['exit', 'quit']:
                    break
                if user_input.strip():
                    self.chat(user_input)
            except KeyboardInterrupt:
                break
                
        print("\n👋 再见!")


if __name__ == "__main__":
    tester = SimpleWorkflowTester()
    tester.run()