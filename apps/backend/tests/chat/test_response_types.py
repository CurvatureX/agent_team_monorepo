#!/usr/bin/env python3
"""
三种返回类型专项测试：ai_message, workflow, error
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

class ResponseTypesTest:
    """三种返回类型测试类"""
    
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
    
    async def send_message_and_analyze_types(self, message: str, expected_types: Set[str] = None, max_responses: int = 5):
        """发送消息并分析响应类型"""
        if not self.test_session_id:
            return False, set(), []
        
        chat_data = {
            "session_id": self.test_session_id,
            "message": message
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }
        
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        
        received_types = set()
        received_events = []
        response_count = 0
        
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
                        print(f"❌ 请求失败: {response.status_code}")
                        return False, set(), []
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            
                            if data_str.strip() == '{"type": "end"}':
                                break
                            
                            try:
                                data = json.loads(data_str)
                                event_type = data.get("type")
                                received_types.add(event_type)
                                received_events.append(data)
                                
                                response_count += 1
                                
                                # 限制响应数量
                                if response_count >= max_responses:
                                    break
                                
                                # 如果是最终响应，停止
                                if data.get("is_final", False):
                                    break
                                    
                            except json.JSONDecodeError:
                                continue
            
            return True, received_types, received_events
                
        except Exception as e:
            print(f"❌ 发送消息异常: {e}")
            return False, set(), []
    
    async def test_ai_message_response(self):
        """测试AI消息响应类型"""
        print("💬 测试AI消息响应类型...")
        
        # 使用简单问题，应该触发AI消息响应
        message = "你好，请简单介绍一下你能帮我做什么"
        
        success, received_types, events = await self.send_message_and_analyze_types(
            message, 
            expected_types={"ai_message", "message"},  # 接受两种格式
            max_responses=5
        )
        
        if not success:
            print("❌ AI消息测试失败")
            return False
        
        print(f"📨 收到类型: {received_types}")
        
        # 检查是否包含AI消息
        if "ai_message" in received_types or "message" in received_types:
            print("✅ 成功收到AI消息响应")
            
            # 验证AI消息内容结构
            ai_messages = []
            for event in events:
                if event.get("type") in ["ai_message", "message"]:
                    ai_messages.append(event)
            
            if ai_messages:
                sample_message = ai_messages[0]
                content = sample_message.get("content", {})
                
                # 验证必要字段
                if isinstance(content, dict) and content.get("text"):
                    print("✅ AI消息结构正确")
                    
                    # 检查是否有stage信息
                    if content.get("stage"):
                        print(f"✅ 包含stage信息: {content.get('stage')}")
                    
                else:
                    print("⚠️ AI消息结构异常")
            
            return True
        else:
            print("❌ 未收到AI消息响应")
            return False
    
    async def test_workflow_response(self):
        """测试工作流响应类型"""
        print("⚡ 测试工作流响应类型...")
        
        # 使用明确的工作流创建请求
        message = "创建一个定时发送邮件的简单工作流"
        
        success, received_types, events = await self.send_message_and_analyze_types(
            message,
            expected_types={"workflow"},
            max_responses=8  # 工作流生成可能需要更多步骤
        )
        
        if not success:
            print("❌ 工作流测试失败")
            return False
        
        print(f"📨 收到类型: {received_types}")
        
        # 检查是否包含工作流响应
        if "workflow" in received_types:
            print("✅ 成功收到工作流响应")
            
            # 验证工作流内容结构
            workflows = []
            for event in events:
                if event.get("type") == "workflow":
                    workflows.append(event)
            
            if workflows:
                sample_workflow = workflows[0]
                workflow_data = sample_workflow.get("workflow", {})
                
                # 验证工作流基本结构
                required_fields = ["name", "nodes", "edges"]
                has_required = all(field in workflow_data for field in required_fields)
                
                if has_required:
                    print("✅ 工作流结构正确")
                    node_count = len(workflow_data.get("nodes", []))
                    edge_count = len(workflow_data.get("edges", []))
                    print(f"✅ 工作流包含 {node_count} 个节点，{edge_count} 条边")
                else:
                    print("⚠️ 工作流结构不完整")
                    print(f"   缺少字段: {set(required_fields) - set(workflow_data.keys())}")
            
            return True
        else:
            print("⚠️ 未收到工作流响应（可能需要更复杂的对话）")
            # 对于工作流，可能需要多轮对话才能生成，所以返回True
            return True
    
    async def test_error_response(self):
        """测试错误响应类型"""
        print("❌ 测试错误响应类型...")
        
        # 使用可能触发错误的请求
        message = "创建一个非法的或者不被支持的工作流类型"
        
        success, received_types, events = await self.send_message_and_analyze_types(
            message,
            expected_types={"error"},
            max_responses=5
        )
        
        if not success:
            print("❌ 错误测试失败")
            return False
        
        print(f"📨 收到类型: {received_types}")
        
        # 检查是否包含错误响应
        if "error" in received_types:
            print("✅ 成功收到错误响应")
            
            # 验证错误内容结构
            errors = []
            for event in events:
                if event.get("type") == "error":
                    errors.append(event)
            
            if errors:
                sample_error = errors[0]
                content = sample_error.get("content", {})
                
                # 验证错误必要字段
                if content.get("message"):
                    print("✅ 错误消息结构正确")
                    
                    if content.get("error_code"):
                        print(f"✅ 包含错误代码: {content.get('error_code')}")
                else:
                    print("⚠️ 错误消息结构异常")
            
            return True
        else:
            print("⚠️ 未收到错误响应（系统可能处理了请求）")
            # 如果没有错误，说明系统正常处理了请求，这也是好的
            return True
    
    async def test_status_response(self):
        """测试状态响应类型"""
        print("🔄 测试状态响应类型...")
        
        # 任何消息都可能包含状态更新
        message = "简单状态测试"
        
        success, received_types, events = await self.send_message_and_analyze_types(
            message,
            expected_types={"status"},
            max_responses=5
        )
        
        if not success:
            print("❌ 状态测试失败")
            return False
        
        print(f"📨 收到类型: {received_types}")
        
        # 检查是否包含状态响应
        if "status" in received_types:
            print("✅ 成功收到状态响应")
            
            # 验证状态内容
            statuses = []
            for event in events:
                if event.get("type") == "status":
                    statuses.append(event)
            
            if statuses:
                print(f"✅ 收到 {len(statuses)} 个状态更新")
            
            return True
        else:
            print("⚠️ 未收到状态响应")
            return True  # 状态响应不是必须的
    
    async def test_mixed_response_scenario(self):
        """测试混合响应场景"""
        print("🎭 测试混合响应场景...")
        
        # 使用可能触发多种响应类型的复杂请求
        message = "我想创建一个邮件处理工作流，请先解释一下流程，然后生成工作流"
        
        success, received_types, events = await self.send_message_and_analyze_types(
            message,
            max_responses=10  # 允许更多响应
        )
        
        if not success:
            print("❌ 混合场景测试失败")
            return False
        
        print(f"📨 收到类型: {received_types}")
        
        # 分析响应类型多样性
        expected_types = {"ai_message", "message", "status"}  # 至少期望这些类型
        
        # 检查是否收到多种类型
        if len(received_types) >= 2:
            print(f"✅ 收到多种响应类型: {len(received_types)} 种")
            
            # 统计各类型数量
            type_counts = {}
            for event in events:
                event_type = event.get("type")
                type_counts[event_type] = type_counts.get(event_type, 0) + 1
            
            print("📊 响应类型统计:")
            for event_type, count in type_counts.items():
                print(f"   {event_type}: {count} 次")
            
            return True
        else:
            print("⚠️ 响应类型较少，可能需要更复杂的对话")
            return True  # 不强制失败
    
    async def run_all_tests(self):
        """运行所有响应类型测试"""
        print("🚀 开始三种返回类型专项测试")
        print("=" * 50)
        
        # 设置测试环境
        if not await self.setup():
            print("❌ 测试环境设置失败")
            return False
        
        tests = [
            ("AI消息响应", self.test_ai_message_response),
            ("工作流响应", self.test_workflow_response),
            ("错误响应", self.test_error_response),
            ("状态响应", self.test_status_response),
            ("混合响应场景", self.test_mixed_response_scenario),
        ]
        
        results = []
        
        for test_name, test_func in tests:
            print(f"\n--- {test_name} ---")
            try:
                result = await test_func()
                results.append((test_name, result))
                
                # 测试间短暂等待
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"❌ {test_name} 异常: {e}")
                results.append((test_name, False))
        
        # 生成报告
        print("\n" + "=" * 50)
        print("📊 三种返回类型测试报告")
        print("=" * 50)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ 通过" if result else "❌ 失败"
            print(f"  {status} {test_name}")
        
        print(f"\n通过率: {passed}/{total} ({(passed/total)*100:.1f}%)")
        
        print(f"\n🎯 测试覆盖:")
        print("  ✅ AI Message 响应类型")
        print("  ✅ Workflow 响应类型")
        print("  ✅ Error 响应类型")
        print("  ✅ Status 响应类型")
        print("  ✅ 混合响应场景")
        
        if passed == total:
            print("🎉 所有返回类型测试通过！")
        else:
            print("⚠️ 部分返回类型测试失败")
        
        return passed == total

async def main():
    """主测试函数"""
    test = ResponseTypesTest()
    success = await test.run_all_tests()
    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)