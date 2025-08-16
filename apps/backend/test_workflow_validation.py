#!/usr/bin/env python3
"""
Workflow 创建和执行验证测试脚本
用于验证 prompt 修改和 hardcode 逻辑改动后的系统稳定性

使用方法:
    python test_workflow_validation.py           # 运行所有测试
    python test_workflow_validation.py --quick   # 快速测试（仅第一个案例）
    python test_workflow_validation.py --verbose # 详细日志模式
"""

import os
import sys
import json
import time
import argparse
import requests
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL")
TEST_USER_PASSWORD = os.getenv("TEST_USER_PASSWORD")

# ANSI 颜色码
class Color:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    GRAY = "\033[90m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


class TestStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    ERROR = "ERROR"


@dataclass
class TestCase:
    """测试用例"""
    id: str
    name: str
    description: str
    user_request: str
    expected_nodes: List[str]  # 期望的节点类型
    validation_rules: Dict[str, Any]  # 参数验证规则
    execution_data: Optional[Dict] = None  # 执行时的测试数据
    tags: List[str] = None


@dataclass
class TestResult:
    """测试结果"""
    case_id: str
    status: TestStatus
    workflow_id: Optional[str] = None
    creation_time: Optional[float] = None
    execution_time: Optional[float] = None
    errors: List[str] = None
    warnings: List[str] = None
    details: Dict = None


class WorkflowTestRunner:
    """Workflow 测试运行器"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.session = requests.Session()
        self.access_token = None
        self.session_id = None
        self.results: List[TestResult] = []
        
    def log(self, message: str, level: str = "INFO"):
        """简洁的日志输出"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if level == "SUCCESS":
            prefix = f"{Color.GREEN}✓{Color.RESET}"
            color = Color.GREEN
        elif level == "ERROR":
            prefix = f"{Color.RED}✗{Color.RESET}"
            color = Color.RED
        elif level == "WARNING":
            prefix = f"{Color.YELLOW}⚠{Color.RESET}"
            color = Color.YELLOW
        elif level == "INFO":
            prefix = f"{Color.BLUE}ℹ{Color.RESET}"
            color = Color.BLUE
        else:
            prefix = " "
            color = Color.GRAY
            
        if level != "DEBUG" or self.verbose:
            print(f"{Color.GRAY}[{timestamp}]{Color.RESET} {prefix} {color}{message}{Color.RESET}")
    
    def authenticate(self) -> bool:
        """认证"""
        self.log("Authenticating...", "INFO")
        
        try:
            response = self.session.post(
                f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
                headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
                json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
            )
            
            if response.status_code == 200:
                self.access_token = response.json().get("access_token")
                self.log("Authentication successful", "SUCCESS")
                return True
            else:
                self.log(f"Authentication failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"Authentication error: {str(e)}", "ERROR")
            return False
    
    def create_session(self) -> bool:
        """创建会话"""
        self.log("Creating session...", "INFO")
        
        try:
            response = self.session.post(
                f"{API_BASE_URL}/api/v1/app/sessions",
                headers={"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"},
                json={"action": "create"}
            )
            
            if response.status_code == 200:
                self.session_id = response.json()["session"]["id"]
                self.log(f"Session created: {self.session_id[:8]}...", "SUCCESS")
                return True
            else:
                self.log(f"Session creation failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"Session creation error: {str(e)}", "ERROR")
            return False
    
    def generate_workflow(self, test_case: TestCase) -> Tuple[Optional[Dict], Optional[str], List[str]]:
        """生成 workflow 并创建在系统中
        
        Returns:
            (workflow_data, created_workflow_id, errors)
        """
        self.log(f"Generating workflow: {test_case.name}", "INFO")
        
        errors = []
        workflow_data = None
        created_workflow_id = None
        start_time = time.time()
        
        try:
            with self.session.post(
                f"{API_BASE_URL}/api/v1/app/chat/stream",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream"
                },
                json={"session_id": self.session_id, "user_message": test_case.user_request},
                stream=True,
                timeout=120
            ) as response:
                
                if response.status_code != 200:
                    errors.append(f"Request failed: {response.status_code}")
                    return None, None, errors
                
                for line in response.iter_lines():
                    if line and line.startswith(b'data: '):
                        try:
                            data_str = line[6:].decode('utf-8')
                            if data_str == '[DONE]':
                                break
                            if not data_str.strip():
                                continue
                                
                            event = json.loads(data_str)
                            
                            # 处理错误事件
                            if event.get('type') == 'error':
                                error_msg = event.get('data', {}).get('error', 'Unknown error')
                                errors.append(f"Generation error: {error_msg}")
                                
                            # 获取 workflow 数据
                            elif event.get('type') == 'workflow':
                                event_data = event.get('data', {})
                                workflow_data = event_data.get('workflow', {})
                                
                                # 尝试多个位置获取 workflow ID - 优先查找 workflow_id 字段
                                created_workflow_id = (
                                    workflow_data.get('workflow_id') or  # workflow 数据中的 workflow_id (实际UUID)
                                    event_data.get('workflow_id') or     # 事件级别的 workflow_id
                                    (workflow_data.get('id') if workflow_data.get('id') != 'workflow' else None) or  # workflow 数据中的 id (排除 'workflow' 字符串)
                                    (event_data.get('id') if event_data.get('id') != 'workflow' else None)  # 事件级别的 id (排除 'workflow' 字符串)
                                )
                                
                                if self.verbose:
                                    self.log(f"Event data keys: {list(event_data.keys())}", "DEBUG")
                                    self.log(f"Workflow data.id: {workflow_data.get('id')}", "DEBUG")
                                    self.log(f"Workflow data.workflow_id: {workflow_data.get('workflow_id')}", "DEBUG")
                                    self.log(f"Final workflow ID: {created_workflow_id}", "DEBUG")
                                
                        except json.JSONDecodeError:
                            pass
                
                generation_time = time.time() - start_time
                
                if workflow_data:
                    self.log(f"Workflow generated in {generation_time:.2f}s (ID: {created_workflow_id})", "SUCCESS")
                else:
                    self.log("Workflow generation failed", "ERROR")
                    
        except requests.exceptions.Timeout:
            errors.append("Request timeout")
        except Exception as e:
            errors.append(f"Generation exception: {str(e)}")
            
        return workflow_data, created_workflow_id, errors
    
    def validate_workflow(self, workflow: Dict, test_case: TestCase) -> Tuple[bool, List[str], List[str]]:
        """验证 workflow 结构和参数"""
        errors = []
        warnings = []
        
        # 验证节点类型
        nodes = workflow.get('nodes', [])
        node_types = [node.get('type') for node in nodes]
        
        for expected_type in test_case.expected_nodes:
            if expected_type not in node_types:
                errors.append(f"Missing expected node type: {expected_type}")
        
        # 验证参数
        for node in nodes:
            node_type = node.get('type', '')
            node_name = node.get('name', 'unnamed')
            parameters = node.get('parameters', {})
            
            # 检查常见问题
            for param_name, param_value in parameters.items():
                # 检查占位符
                if isinstance(param_value, str):
                    if '<' in param_value and '>' in param_value:
                        errors.append(f"Placeholder found in {node_name}.{param_name}: {param_value}")
                    elif '{{' in param_value:
                        warnings.append(f"Template variable in {node_name}.{param_name}: {param_value}")
                
                # 检查无效值
                if isinstance(param_value, int) and param_value == 0:
                    if 'id' in param_name.lower() or 'number' in param_name.lower():
                        errors.append(f"Invalid zero value in {node_name}.{param_name}")
            
            # 应用自定义验证规则
            if node_type in test_case.validation_rules:
                rules = test_case.validation_rules[node_type]
                for param_name, validator in rules.items():
                    if param_name in parameters:
                        if not validator(parameters[param_name]):
                            errors.append(f"Validation failed for {node_name}.{param_name}: {parameters[param_name]}")
        
        # 检查节点类型格式
        for node in nodes:
            if node.get('type', '').endswith('_NODE'):
                errors.append(f"Invalid node type format: {node.get('type')}")
        
        is_valid = len(errors) == 0
        
        if is_valid:
            self.log("Workflow validation passed", "SUCCESS")
        else:
            self.log(f"Workflow validation failed with {len(errors)} errors", "ERROR")
            
        return is_valid, errors, warnings
    
    def execute_workflow(self, workflow_id: str, test_data: Dict) -> Tuple[bool, Optional[str], List[str]]:
        """执行 workflow - 尝试多个可能的 API 路径"""
        self.log(f"Executing workflow: {workflow_id}", "INFO")
        
        errors = []
        execution_id = None
        
        # 可能的 API 路径（按优先级排序）
        api_paths = [
            f"{API_BASE_URL}/api/v1/app/workflows/{workflow_id}/execute",  # 通过 API Gateway
            f"http://localhost:8002/v1/workflows/{workflow_id}/execute",    # 直接调用 workflow engine
        ]
        
        for api_path in api_paths:
            try:
                if self.verbose:
                    self.log(f"Trying API path: {api_path}", "DEBUG")
                    
                # 构造正确的请求数据格式
                # 对于直接调用 workflow engine，需要包含 workflow_id 和 user_id
                if "8002" in api_path:
                    request_data = {
                        "workflow_id": workflow_id,
                        "user_id": TEST_USER_EMAIL or "test_user",  # 使用测试用户邮箱作为 user_id
                        "input_data": test_data
                    }
                else:
                    # 对于 API Gateway，保持原始格式
                    request_data = test_data
                    
                response = self.session.post(
                    api_path,
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json"
                    },
                    json=request_data,
                    timeout=30
                )
                
                if response.status_code in [200, 201, 202]:
                    result = response.json()
                    execution_id = result.get('execution_id') or result.get('id')
                    self.log(f"Workflow execution started: {execution_id}", "SUCCESS")
                    return True, execution_id, errors
                    
                elif response.status_code == 404:
                    # Try next API path if workflow not found
                    if self.verbose:
                        self.log(f"Workflow not found at {api_path}, trying next path...", "DEBUG")
                    continue
                    
                else:
                    error_msg = f"Status {response.status_code}"
                    if response.text:
                        try:
                            error_detail = response.json().get('detail', response.text[:100])
                            error_msg += f": {error_detail}"
                        except:
                            error_msg += f": {response.text[:100]}"
                    errors.append(error_msg)
                    
            except requests.exceptions.Timeout:
                errors.append(f"Timeout at {api_path}")
                continue
            except requests.exceptions.ConnectionError:
                errors.append(f"Connection failed at {api_path}")
                continue
            except Exception as e:
                errors.append(f"Exception at {api_path}: {str(e)}")
                continue
        
        # 所有路径都失败了
        self.log(f"Workflow execution failed on all paths", "ERROR")
        return False, None, errors
    
    def run_test_case(self, test_case: TestCase) -> TestResult:
        """运行单个测试用例 - 完整的创建+执行集成测试"""
        print(f"\n{Color.BOLD}{'='*60}{Color.RESET}")
        print(f"{Color.BOLD}Test Case: {test_case.name}{Color.RESET}")
        print(f"{Color.GRAY}{test_case.description}{Color.RESET}")
        print(f"{Color.BOLD}{'='*60}{Color.RESET}")
        
        result = TestResult(
            case_id=test_case.id,
            status=TestStatus.SKIP,
            errors=[],
            warnings=[],
            details={}
        )
        
        # Step 1: 生成并创建 workflow
        workflow_data, created_workflow_id, gen_errors = self.generate_workflow(test_case)
        result.errors.extend(gen_errors)
        
        if not workflow_data:
            result.status = TestStatus.FAIL
            self.log("Workflow creation failed - no workflow data returned", "ERROR")
            return result
        
        # 使用实际返回的 workflow ID，如果没有则使用数据中的 ID
        actual_workflow_id = created_workflow_id or workflow_data.get('id', 'unknown')
        result.workflow_id = actual_workflow_id
        
        if actual_workflow_id == 'unknown' or actual_workflow_id == 'workflow':
            self.log(f"Warning: Workflow ID might be invalid: {actual_workflow_id}", "WARNING")
            result.warnings.append(f"Potentially invalid workflow ID: {actual_workflow_id}")
        
        # Step 2: 验证 workflow 结构
        is_valid, val_errors, val_warnings = self.validate_workflow(workflow_data, test_case)
        result.errors.extend(val_errors)
        result.warnings.extend(val_warnings)
        
        if not is_valid:
            result.status = TestStatus.FAIL
            self.log(f"Workflow validation failed with {len(val_errors)} errors", "ERROR")
            return result
        
        # Step 3: 执行 workflow（集成测试的关键部分）
        if test_case.execution_data:
            self.log(f"Starting workflow execution test for ID: {actual_workflow_id}", "INFO")
            
            # 先等待一下，确保 workflow 已经完全创建
            time.sleep(2)
            
            exec_success, exec_id, exec_errors = self.execute_workflow(
                actual_workflow_id,
                test_case.execution_data
            )
            result.errors.extend(exec_errors)
            
            if exec_success:
                result.status = TestStatus.PASS
                result.details['execution_id'] = exec_id
                self.log(f"Integration test PASSED - Workflow created and executed successfully", "SUCCESS")
            else:
                result.status = TestStatus.FAIL
                self.log(f"Integration test FAILED - Workflow execution failed", "ERROR")
                # 如果执行失败，可能是 workflow ID 或 API 路径问题
                if "404" in str(exec_errors):
                    result.errors.append(f"Workflow not found - ID might be incorrect: {actual_workflow_id}")
        else:
            # 仅创建测试，不执行
            result.status = TestStatus.PASS
            self.log("Workflow creation test passed (execution skipped)", "SUCCESS")
            result.details['created_workflow_id'] = actual_workflow_id
        
        return result
    
    def run_all_tests(self, test_cases: List[TestCase]) -> None:
        """运行所有测试"""
        print(f"\n{Color.BOLD}{Color.BLUE}Starting Workflow Validation Tests{Color.RESET}")
        print(f"{Color.GRAY}Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Color.RESET}")
        print(f"{Color.GRAY}Total test cases: {len(test_cases)}{Color.RESET}\n")
        
        # 初始化
        if not self.authenticate():
            self.log("Authentication failed, aborting tests", "ERROR")
            return
            
        if not self.create_session():
            self.log("Session creation failed, aborting tests", "ERROR")
            return
        
        # 运行测试
        for i, test_case in enumerate(test_cases, 1):
            self.log(f"Running test {i}/{len(test_cases)}: {test_case.id}", "INFO")
            result = self.run_test_case(test_case)
            self.results.append(result)
            
            # 短暂延迟，避免请求过快
            if i < len(test_cases):
                time.sleep(2)
        
        # 生成报告
        self.generate_report()
    
    def generate_report(self) -> None:
        """生成测试报告"""
        print(f"\n{Color.BOLD}{'='*60}{Color.RESET}")
        print(f"{Color.BOLD}Test Report{Color.RESET}")
        print(f"{Color.BOLD}{'='*60}{Color.RESET}\n")
        
        # 统计
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == TestStatus.PASS)
        failed = sum(1 for r in self.results if r.status == TestStatus.FAIL)
        skipped = sum(1 for r in self.results if r.status == TestStatus.SKIP)
        
        # 结果列表
        print(f"{Color.BOLD}Results:{Color.RESET}")
        for result in self.results:
            if result.status == TestStatus.PASS:
                symbol = f"{Color.GREEN}✓{Color.RESET}"
                status_color = Color.GREEN
            elif result.status == TestStatus.FAIL:
                symbol = f"{Color.RED}✗{Color.RESET}"
                status_color = Color.RED
            else:
                symbol = f"{Color.YELLOW}○{Color.RESET}"
                status_color = Color.YELLOW
                
            print(f"  {symbol} {result.case_id}: {status_color}{result.status.value}{Color.RESET}")
            
            if result.errors and self.verbose:
                for error in result.errors:
                    print(f"      {Color.RED}Error: {error}{Color.RESET}")
            
            if result.warnings and self.verbose:
                for warning in result.warnings:
                    print(f"      {Color.YELLOW}Warning: {warning}{Color.RESET}")
        
        # 总结
        print(f"\n{Color.BOLD}Summary:{Color.RESET}")
        print(f"  Total:   {total}")
        print(f"  {Color.GREEN}Passed:  {passed}{Color.RESET}")
        print(f"  {Color.RED}Failed:  {failed}{Color.RESET}")
        print(f"  {Color.YELLOW}Skipped: {skipped}{Color.RESET}")
        
        # 成功率
        if total > 0:
            success_rate = (passed / total) * 100
            if success_rate == 100:
                color = Color.GREEN
            elif success_rate >= 80:
                color = Color.YELLOW
            else:
                color = Color.RED
                
            print(f"\n{Color.BOLD}Success Rate: {color}{success_rate:.1f}%{Color.RESET}")
        
        # 结论
        print(f"\n{Color.BOLD}Conclusion:{Color.RESET}")
        if failed == 0:
            print(f"{Color.GREEN}✅ All tests passed! The system is working correctly.{Color.RESET}")
        elif failed <= 2:
            print(f"{Color.YELLOW}⚠️  Minor issues detected. Review the failed tests.{Color.RESET}")
        else:
            print(f"{Color.RED}❌ Multiple failures detected. System needs attention.{Color.RESET}")


def get_test_cases() -> List[TestCase]:
    """定义测试用例"""
    return [
        TestCase(
            id="TC001",
            name="GitHub to Webhook",
            description="Create GitHub issue trigger with webhook action",
            user_request="When someone creates a GitHub issue, send a HTTP request to https://example.com/webhook",
            expected_nodes=["TRIGGER", "ACTION"],
            validation_rules={
                "TRIGGER": {
                    "repository": lambda v: isinstance(v, str) and "/" in v and "<" not in v,
                    "github_app_installation_id": lambda v: isinstance(v, int) and v > 0,
                },
                "ACTION": {
                    "url": lambda v: isinstance(v, str) and v.startswith("http"),
                    "method": lambda v: v in ["GET", "POST", "PUT", "DELETE", "PATCH"],
                }
            },
            execution_data={
                "trigger_type": "manual",
                "data": {"test": True}
            },
            tags=["github", "webhook", "integration"]
        ),
        
        TestCase(
            id="TC002",
            name="Scheduled Task",
            description="Create scheduled task with cron trigger",
            user_request="Every day at 9am, check GitHub repository microsoft/vscode for new issues",
            expected_nodes=["TRIGGER"],
            validation_rules={
                "TRIGGER": {
                    "cron_expression": lambda v: isinstance(v, str) and "*" in v,
                }
            },
            execution_data=None,  # 不执行，仅测试创建
            tags=["schedule", "cron"]
        ),
        
        TestCase(
            id="TC003",
            name="Slack Integration",
            description="Send Slack message when webhook received",
            user_request="When data is posted to webhook endpoint, send a message to Slack channel #general",
            expected_nodes=["TRIGGER", "EXTERNAL_ACTION"],
            validation_rules={
                "EXTERNAL_ACTION": {
                    "channel": lambda v: isinstance(v, str) and len(v) > 0,
                }
            },
            execution_data={
                "trigger_type": "webhook",
                "data": {"message": "Test message"}
            },
            tags=["slack", "webhook", "messaging"]
        ),
        
        TestCase(
            id="TC004",
            name="AI Processing",
            description="Use AI to process and transform data",
            user_request="When a customer support email arrives, use AI to classify it and create a ticket",
            expected_nodes=["TRIGGER", "AI_AGENT"],
            validation_rules={
                "AI_AGENT": {
                    "system_prompt": lambda v: isinstance(v, str) and len(v) > 10,
                }
            },
            execution_data=None,
            tags=["ai", "email", "classification"]
        ),
        
        TestCase(
            id="TC005",
            name="Complex Workflow",
            description="Multi-step workflow with conditions",
            user_request="Monitor GitHub repo for pull requests, if PR is from external contributor, request review from team lead, then notify in Slack",
            expected_nodes=["TRIGGER"],
            validation_rules={
                "TRIGGER": {
                    "repository": lambda v: isinstance(v, str) and "/" in v,
                }
            },
            execution_data=None,
            tags=["github", "review", "complex"]
        ),
    ]


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Workflow Validation Test Suite')
    parser.add_argument('--quick', action='store_true', help='Run only the first test case')
    parser.add_argument('--medium', action='store_true', help='Run first 3 test cases')
    parser.add_argument('--verbose', action='store_true', help='Show detailed logs')
    parser.add_argument('--case', type=str, help='Run specific test case by ID')
    
    args = parser.parse_args()
    
    # 检查环境变量
    if not all([SUPABASE_URL, SUPABASE_ANON_KEY, TEST_USER_EMAIL, TEST_USER_PASSWORD]):
        print(f"{Color.RED}Error: Missing required environment variables{Color.RESET}")
        print("Please ensure the following are set in .env:")
        print("  - SUPABASE_URL")
        print("  - SUPABASE_ANON_KEY")
        print("  - TEST_USER_EMAIL")
        print("  - TEST_USER_PASSWORD")
        sys.exit(1)
    
    # 获取测试用例
    test_cases = get_test_cases()
    
    # 根据参数过滤测试用例
    if args.quick:
        test_cases = test_cases[:1]
    elif args.medium:
        test_cases = test_cases[:3]
    elif args.case:
        test_cases = [tc for tc in test_cases if tc.id == args.case]
        if not test_cases:
            print(f"{Color.RED}Error: Test case {args.case} not found{Color.RESET}")
            sys.exit(1)
    
    # 运行测试
    runner = WorkflowTestRunner(verbose=args.verbose)
    runner.run_all_tests(test_cases)


if __name__ == "__main__":
    main()