#!/usr/bin/env python3
"""
详细版聊天测试脚本 - 显示所有状态变化和API返回
"""

import json
import os
from datetime import datetime

import requests
from colorama import Back, Fore, Style, init
from dotenv import load_dotenv

# Initialize colorama
init(autoreset=True)

# Load environment variables
load_dotenv()

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL")
TEST_USER_PASSWORD = os.getenv("TEST_USER_PASSWORD")


class DetailedWorkflowTester:
    def __init__(self):
        self.session = requests.Session()
        self.access_token = None
        self.session_id = None
        self.event_count = 0

    def print_api_response(self, method: str, url: str, status_code: int, response_data: dict):
        """打印API响应"""
        print(f"\n{Fore.MAGENTA}📡 API响应 [{method} {url.split('/')[-1]}]:")
        print(f"{Fore.CYAN}状态码: {status_code}")
        print(f"{Fore.CYAN}返回数据:")
        print(json.dumps(response_data, indent=2, ensure_ascii=False))
        print(f"{Fore.MAGENTA}{'='*80}{Style.RESET_ALL}")

    def print_status_change_detail(self, data: dict):
        """打印状态变化的详细信息"""
        print(f"\n{Fore.YELLOW}🔄 状态变化详情:")
        print(f"  前一阶段: {data.get('previous_stage', 'N/A')}")
        print(f"  当前阶段: {data.get('current_stage', 'N/A')}")
        print(f"  节点名称: {data.get('node_name', 'N/A')}")

        # 打印阶段状态详情
        stage_state = data.get("stage_state", {})
        if stage_state:
            print(f"\n  {Fore.CYAN}阶段状态:")
            print(f"    会话ID: {stage_state.get('session_id', 'N/A')}")
            print(f"    阶段: {stage_state.get('stage', 'N/A')}")
            print(f"    意图摘要: {stage_state.get('intent_summary', 'N/A')}")
            print(f"    对话轮数: {stage_state.get('conversations_count', 0)}")
            print(f"    是否有工作流: {stage_state.get('has_workflow', False)}")

            # 如果有gaps信息
            gaps = stage_state.get("gaps", [])
            if gaps:
                print(f"    待澄清项: {', '.join(gaps)}")

            # 如果有debug信息
            debug_result = stage_state.get("debug_result", "")
            if debug_result:
                print(f"    调试信息: {debug_result}")

        print(f"{Fore.YELLOW}{'='*80}{Style.RESET_ALL}")

    def print_sse_event(self, event_num: int, event: dict):
        """打印SSE事件"""
        print(f"\n{Fore.GREEN}📨 SSE事件 #{event_num}:")
        print(f"  类型: {event.get('type')}")
        print(f"  时间戳: {event.get('timestamp', 'N/A')}")
        print(f"  是否最终: {event.get('is_final', False)}")

    def authenticate(self):
        """认证并获取访问令牌"""
        print(f"\n{Fore.BLUE}{'='*80}")
        print(f"{Fore.BLUE}🔐 步骤1: 用户认证")
        print(f"{Fore.BLUE}{'='*80}{Style.RESET_ALL}")

        auth_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
        data = {"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}

        print(f"\n请求: POST {auth_url}")
        print(f"数据: {json.dumps(data, indent=2)}")

        response = self.session.post(
            auth_url,
            headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
            json=data,
        )

        response_data = response.json()
        self.print_api_response("POST", auth_url, response.status_code, response_data)

        if response.status_code == 200:
            self.access_token = response_data.get("access_token")
            print(f"\n{Fore.GREEN}✅ 认证成功!")
            print(f"Access Token: {self.access_token[:50]}...{Style.RESET_ALL}")
            return True
        else:
            print(f"\n{Fore.RED}❌ 认证失败!{Style.RESET_ALL}")
            return False

    def create_session(self):
        """创建新的聊天会话"""
        print(f"\n{Fore.BLUE}{'='*80}")
        print(f"{Fore.BLUE}📝 步骤2: 创建会话")
        print(f"{Fore.BLUE}{'='*80}{Style.RESET_ALL}")

        url = f"{API_BASE_URL}/api/v1/app/sessions"
        data = {"action": "create"}

        print(f"\n请求: POST {url}")
        print(f"数据: {json.dumps(data, indent=2)}")

        response = self.session.post(
            url,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
            json=data,
        )

        response_data = response.json()
        self.print_api_response("POST", url, response.status_code, response_data)

        if response.status_code == 200:
            session_info = response_data.get("session", {})
            self.session_id = session_info.get("id")
            print(f"\n{Fore.GREEN}✅ 会话创建成功!")
            print(f"Session ID: {self.session_id}{Style.RESET_ALL}")
            return True
        else:
            print(f"\n{Fore.RED}❌ 会话创建失败!{Style.RESET_ALL}")
            return False

    def chat(self, message):
        """发送消息并处理流式响应"""
        print(f"\n{Fore.BLUE}{'='*80}")
        print(f"{Fore.BLUE}💬 发送聊天消息")
        print(f"{Fore.BLUE}{'='*80}{Style.RESET_ALL}")

        print(f"\n{Fore.CYAN}👤 用户: {message}{Style.RESET_ALL}")

        url = f"{API_BASE_URL}/api/v1/app/chat/stream"
        data = {"session_id": self.session_id, "user_message": message}

        print(f"\n请求: POST {url}")
        print(f"数据: {json.dumps(data, indent=2, ensure_ascii=False)}")

        with self.session.post(
            url,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            },
            json=data,
            stream=True,
        ) as response:
            print(f"\n{Fore.MAGENTA}📡 流式响应开始:")
            print(f"状态码: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            print(f"{Fore.MAGENTA}{'='*80}{Style.RESET_ALL}")

            if response.status_code != 200:
                print(f"{Fore.RED}❌ 请求失败!{Style.RESET_ALL}")
                return

            assistant_msg = ""
            self.event_count = 0

            for line in response.iter_lines():
                if line and line.startswith(b"data: "):
                    try:
                        data_str = line[6:].decode("utf-8")

                        if data_str == "[DONE]":
                            print(f"\n{Fore.GREEN}✅ 流式响应结束{Style.RESET_ALL}")
                            break

                        if not data_str.strip():
                            continue

                        event = json.loads(data_str)
                        self.event_count += 1

                        # 打印每个SSE事件
                        self.print_sse_event(self.event_count, event)

                        event_type = event.get("type")
                        event_data = event.get("data", {})

                        # 处理不同类型的事件
                        if event_type == "status_change":
                            # 详细打印状态变化
                            self.print_status_change_detail(event_data)

                        elif event_type == "message":
                            # 助手消息
                            content = event_data.get("text", "")
                            if content:
                                assistant_msg += content
                                print(f"\n{Fore.GREEN}🤖 助手消息片段:")
                                print(f"{content}{Style.RESET_ALL}")

                        elif event_type == "workflow":
                            # 工作流生成
                            print(f"\n{Fore.YELLOW}📋 工作流生成事件:")
                            workflow_data = event_data.get("workflow", {})
                            print(json.dumps(workflow_data, indent=2, ensure_ascii=False))
                            print(f"{Fore.GREEN}✅ 工作流生成完成!{Style.RESET_ALL}")

                        elif event_type == "error":
                            # 错误
                            print(f"\n{Fore.RED}❌ 错误事件:")
                            print(json.dumps(event_data, indent=2, ensure_ascii=False))
                            print(f"{Style.RESET_ALL}")

                        elif event_type == "debug":
                            # 调试信息
                            print(f"\n{Fore.MAGENTA}🐛 调试事件:")
                            print(json.dumps(event_data, indent=2, ensure_ascii=False))
                            print(f"{Style.RESET_ALL}")

                    except json.JSONDecodeError as e:
                        print(f"{Fore.RED}JSON解析错误: {e}")
                        print(f"原始数据: {data_str}{Style.RESET_ALL}")

            print(f"\n{Fore.CYAN}📊 统计:")
            print(f"  总事件数: {self.event_count}")
            print(f"  助手回复长度: {len(assistant_msg)} 字符{Style.RESET_ALL}")

            if assistant_msg:
                print(f"\n{Fore.GREEN}🤖 助手完整回复:")
                print(f"{assistant_msg}{Style.RESET_ALL}")

    def run(self):
        """运行测试"""
        print(f"{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}工作流聊天测试 (详细版)")
        print(f"{Fore.CYAN}显示所有状态变化和API返回")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")

        # 检查环境变量
        if not all([SUPABASE_URL, SUPABASE_ANON_KEY, TEST_USER_EMAIL, TEST_USER_PASSWORD]):
            print(f"{Fore.RED}❌ 缺少必要的环境变量!{Style.RESET_ALL}")
            return

        # 执行测试流程
        if not self.authenticate():
            return

        if not self.create_session():
            return

        print(f"\n{Fore.YELLOW}💬 开始交互式聊天 (输入 'exit' 退出)")
        print(f"示例: 我想创建一个自动化客服工单路由系统{Style.RESET_ALL}\n")

        while True:
            try:
                user_input = input(f"\n{Fore.BLUE}> {Style.RESET_ALL}")
                if user_input.lower() in ["exit", "quit"]:
                    break
                if user_input.strip():
                    self.chat(user_input)
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}聊天中断{Style.RESET_ALL}")
                break

        print(f"\n{Fore.GREEN}👋 测试结束!{Style.RESET_ALL}")


if __name__ == "__main__":
    tester = DetailedWorkflowTester()
    tester.run()
