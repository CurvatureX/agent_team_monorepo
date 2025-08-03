#!/usr/bin/env python3
"""
优化的聊天流程测试脚本
重点展示工作流节点转换和对话内容
"""

import os
import sys
import json
import time
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime
from dotenv import load_dotenv
from colorama import init, Fore, Style, Back

# Initialize colorama for colored output
init(autoreset=True)

# Load environment variables
load_dotenv()

# Configuration from .env
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL")
TEST_USER_PASSWORD = os.getenv("TEST_USER_PASSWORD")


class WorkflowChatTester:
    def __init__(self):
        self.access_token: Optional[str] = None
        self.session_id: Optional[str] = None
        self.session = requests.Session()
        self.current_stage: Optional[str] = None
        self.stage_transitions: List[Dict] = []
        self.messages: List[Dict] = []
        
    def print_header(self, text: str, color=Fore.BLUE):
        """打印美观的标题"""
        print(f"\n{color}{'='*80}")
        print(f"{color}{text:^80}")
        print(f"{color}{'='*80}{Style.RESET_ALL}\n")
        
    def print_stage_transition(self, from_stage: str, to_stage: str, node_name: str):
        """打印工作流节点转换"""
        print(f"\n{Fore.YELLOW}🔄 工作流节点转换:")
        print(f"   {Fore.CYAN}{from_stage} {Fore.WHITE}→ {Fore.GREEN}{to_stage}")
        print(f"   {Fore.MAGENTA}节点: {node_name}{Style.RESET_ALL}")
        
    def print_message(self, role: str, content: str, timestamp: Optional[str] = None):
        """打印对话消息"""
        time_str = datetime.now().strftime("%H:%M:%S") if not timestamp else timestamp.split('T')[1][:8]
        
        if role == "user":
            print(f"\n{Fore.BLUE}👤 用户 [{time_str}]:{Style.RESET_ALL}")
            print(f"   {content}")
        else:
            print(f"\n{Fore.GREEN}🤖 助手 [{time_str}]:{Style.RESET_ALL}")
            # 格式化助手的消息，使其更易读
            lines = content.split('\n')
            for line in lines:
                if line.strip():
                    print(f"   {line}")
                    
    def print_workflow_summary(self, workflow_data: Dict):
        """打印工作流摘要"""
        print(f"\n{Fore.YELLOW}📋 生成的工作流摘要:{Style.RESET_ALL}")
        
        # 提取关键信息
        if isinstance(workflow_data, dict):
            if 'workflow_summary' in workflow_data:
                summary = workflow_data['workflow_summary']
                # 只显示概述部分
                if '## 工作流概述' in summary:
                    overview = summary.split('## 触发器')[0]
                    print(f"{Fore.CYAN}{overview.strip()}{Style.RESET_ALL}")
            elif 'nodes' in workflow_data:
                print(f"   {Fore.CYAN}节点数量: {len(workflow_data.get('nodes', []))}")
                print(f"   连接数量: {len(workflow_data.get('edges', []))}{Style.RESET_ALL}")
                
    def print_error(self, error_msg: str):
        """打印错误信息"""
        print(f"\n{Fore.RED}❌ 错误: {error_msg}{Style.RESET_ALL}")
        
    def print_info(self, info_msg: str, prefix="ℹ️"):
        """打印信息"""
        print(f"\n{Fore.CYAN}{prefix} {info_msg}{Style.RESET_ALL}")
        
    def authenticate(self) -> bool:
        """认证并获取访问令牌"""
        self.print_header("步骤 1: 用户认证", Fore.BLUE)
        
        auth_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
        headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Content-Type": "application/json"
        }
        data = {
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        }
        
        try:
            response = self.session.post(auth_url, headers=headers, json=data)
            
            if response.status_code == 200:
                auth_data = response.json()
                self.access_token = auth_data.get("access_token")
                self.print_info(f"认证成功! 用户: {TEST_USER_EMAIL}", "✅")
                return True
            else:
                self.print_error(f"认证失败: {response.status_code}")
                return False
                
        except Exception as e:
            self.print_error(f"认证错误: {str(e)}")
            return False
            
    def create_session(self) -> bool:
        """创建新的聊天会话"""
        self.print_header("步骤 2: 创建会话", Fore.BLUE)
        
        url = f"{API_BASE_URL}/api/v1/app/sessions"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        data = {"action": "create"}
        
        try:
            response = self.session.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                response_data = response.json()
                session_data = response_data.get("session", {})
                self.session_id = session_data.get("id")
                self.print_info(f"会话创建成功! ID: {self.session_id}", "✅")
                return True
            else:
                self.print_error(f"会话创建失败: {response.status_code}")
                return False
                
        except Exception as e:
            self.print_error(f"会话创建错误: {str(e)}")
            return False
            
    def stream_chat(self, message: str):
        """发送聊天消息并处理流式响应"""
        # 先显示用户消息
        self.print_message("user", message)
        self.messages.append({"role": "user", "content": message})
        
        url = f"{API_BASE_URL}/api/v1/app/chat/stream"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }
        data = {
            "session_id": self.session_id,
            "user_message": message
        }
        
        try:
            with self.session.post(url, headers=headers, json=data, stream=True) as response:
                if response.status_code != 200:
                    self.print_error(f"请求失败: {response.status_code}")
                    return
                    
                assistant_response = ""
                workflow_generated = False
                
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        
                        if line_str.startswith('data: '):
                            data_str = line_str[6:]
                            
                            try:
                                if data_str == '[DONE]':
                                    break
                                elif data_str.strip() == '':
                                    continue
                                    
                                event = json.loads(data_str)
                                event_type = event.get('type')
                                event_data = event.get('data', {})
                                
                                # 处理不同类型的事件
                                if event_type == 'status_change':
                                    # 工作流节点转换
                                    prev_stage = event_data.get('previous_stage', 'unknown')
                                    curr_stage = event_data.get('current_stage', 'unknown')
                                    node_name = event_data.get('node_name', 'unknown')
                                    
                                    if prev_stage != curr_stage:
                                        self.print_stage_transition(prev_stage, curr_stage, node_name)
                                        self.stage_transitions.append({
                                            'from': prev_stage,
                                            'to': curr_stage,
                                            'node': node_name
                                        })
                                    self.current_stage = curr_stage
                                    
                                elif event_type == 'message':
                                    # 助手消息
                                    content = event_data.get('text', '')
                                    if content:
                                        assistant_response += content
                                        
                                elif event_type == 'workflow':
                                    # 工作流生成完成
                                    workflow_data = event_data.get('workflow', {})
                                    self.print_workflow_summary(workflow_data)
                                    workflow_generated = True
                                    
                                elif event_type == 'error':
                                    # 错误消息
                                    error_msg = event_data.get('error', 'Unknown error')
                                    self.print_error(error_msg)
                                    
                            except json.JSONDecodeError:
                                pass
                
                # 显示助手的完整回复
                if assistant_response:
                    self.print_message("assistant", assistant_response)
                    self.messages.append({"role": "assistant", "content": assistant_response})
                    
                if workflow_generated:
                    self.print_info("工作流生成完成! 🎉", "✅")
                    
        except Exception as e:
            self.print_error(f"流处理错误: {str(e)}")
            
    def interactive_chat(self):
        """交互式聊天会话"""
        self.print_header("步骤 3: 交互式聊天", Fore.GREEN)
        
        print(f"{Fore.YELLOW}提示: 输入 'exit' 退出聊天")
        print(f"{Fore.CYAN}示例: 我想创建一个自动化客服工单路由系统{Style.RESET_ALL}\n")
        
        while True:
            try:
                # 获取用户输入
                user_input = input(f"\n{Fore.BLUE}请输入: {Style.RESET_ALL}")
                
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    break
                    
                if not user_input.strip():
                    continue
                    
                # 发送消息并处理响应
                self.stream_chat(user_input)
                
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}聊天中断{Style.RESET_ALL}")
                break
                
    def show_summary(self):
        """显示会话摘要"""
        self.print_header("会话摘要", Fore.MAGENTA)
        
        print(f"{Fore.CYAN}会话 ID: {self.session_id}")
        print(f"对话轮数: {len([m for m in self.messages if m['role'] == 'user'])}")
        print(f"当前阶段: {self.current_stage or 'N/A'}")
        
        if self.stage_transitions:
            print(f"\n{Fore.YELLOW}工作流节点转换历史:")
            for i, transition in enumerate(self.stage_transitions, 1):
                print(f"  {i}. {transition['from']} → {transition['to']} (节点: {transition['node']})")
                
    def run(self):
        """运行完整的测试流程"""
        self.print_header("工作流聊天测试", Fore.CYAN)
        
        # 检查环境变量
        if not all([SUPABASE_URL, SUPABASE_ANON_KEY, TEST_USER_EMAIL, TEST_USER_PASSWORD]):
            self.print_error("缺少必要的环境变量!")
            return
            
        # 执行测试流程
        if not self.authenticate():
            return
            
        if not self.create_session():
            return
            
        self.interactive_chat()
        
        # 显示摘要
        self.show_summary()
        

def main():
    """主入口"""
    tester = WorkflowChatTester()
    
    try:
        tester.run()
    except Exception as e:
        print(f"\n{Fore.RED}测试失败: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)
        

if __name__ == "__main__":
    main()