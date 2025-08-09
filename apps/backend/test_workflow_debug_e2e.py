#!/usr/bin/env python3
"""
End-to-End Workflow Debug Test
Tests the complete flow from session creation to workflow generation and debug execution
"""

import os
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
from colorama import init, Fore, Style

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


class WorkflowDebugE2ETester:
    def __init__(self):
        self.session = requests.Session()
        self.access_token = None
        self.session_id = None
        self.workflow_json = None
        self.test_results = []
        
    def print_separator(self, char='─', color=Fore.WHITE):
        print(f"{color}{char*80}{Style.RESET_ALL}")
        
    def print_test_header(self, title):
        self.print_separator('═', Fore.CYAN)
        print(f"{Fore.CYAN}📋 {title}{Style.RESET_ALL}")
        self.print_separator('═', Fore.CYAN)
        
    def print_step(self, step_num, description):
        print(f"\n{Fore.YELLOW}Step {step_num}:{Style.RESET_ALL} {description}")
        
    def authenticate(self):
        """Authenticate and get access token"""
        self.print_step(1, "Authenticating with Supabase")
        
        response = self.session.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        
        if response.status_code == 200:
            self.access_token = response.json().get("access_token")
            print(f"{Fore.GREEN}  ✓ Authentication successful{Style.RESET_ALL}")
            self.test_results.append(("Authentication", True, None))
            return True
        else:
            error = f"Status {response.status_code}: {response.text[:100]}"
            print(f"{Fore.RED}  ✗ Authentication failed: {error}{Style.RESET_ALL}")
            self.test_results.append(("Authentication", False, error))
            return False
            
    def create_session(self):
        """Create chat session"""
        self.print_step(2, "Creating workflow session")
        
        response = self.session.post(
            f"{API_BASE_URL}/api/v1/app/sessions",
            headers={"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"},
            json={"action": "create"}
        )
        
        if response.status_code == 200:
            self.session_id = response.json()["session"]["id"]
            print(f"{Fore.GREEN}  ✓ Session created: {self.session_id}{Style.RESET_ALL}")
            self.test_results.append(("Session Creation", True, None))
            return True
        else:
            error = f"Status {response.status_code}: {response.text[:100]}"
            print(f"{Fore.RED}  ✗ Session creation failed: {error}{Style.RESET_ALL}")
            self.test_results.append(("Session Creation", False, error))
            return False
            
    def send_workflow_request(self, message):
        """Send workflow generation request and process stream"""
        self.print_step(3, "Sending workflow generation request")
        print(f"  📝 Request: {Fore.CYAN}{message}{Style.RESET_ALL}")
        
        workflow_generated = False
        debug_executed = False
        status_changes = []
        assistant_messages = []
        errors = []
        
        with self.session.post(
            f"{API_BASE_URL}/api/v1/app/chat/stream",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream"
            },
            json={"session_id": self.session_id, "user_message": message},
            stream=True,
            timeout=60  # 60 second timeout
        ) as response:
            
            if response.status_code != 200:
                error = f"Request failed with status {response.status_code}"
                print(f"{Fore.RED}  ✗ {error}{Style.RESET_ALL}")
                self.test_results.append(("Workflow Request", False, error))
                return False
                
            # Track request ID
            trace_id = response.headers.get('X-Trace-ID') or response.headers.get('x-tracking-id')
            if trace_id:
                print(f"  {Fore.MAGENTA}Trace ID: {trace_id}{Style.RESET_ALL}")
            
            print(f"  {Fore.YELLOW}Processing SSE stream...{Style.RESET_ALL}")
            event_count = 0
            
            for line in response.iter_lines():
                if line and line.startswith(b'data: '):
                    try:
                        data_str = line[6:].decode('utf-8')
                        
                        if data_str == '[DONE]':
                            break
                            
                        if not data_str.strip():
                            continue
                            
                        # Parse SSE event
                        event = json.loads(data_str)
                        event_count += 1
                        
                        # Handle specific event types
                        event_type = event.get('type')
                        event_data = event.get('data', {})
                        
                        if event_type == 'status_change':
                            prev = event_data.get('previous_stage', 'unknown')
                            curr = event_data.get('current_stage', 'unknown')
                            status_changes.append((prev, curr))
                            print(f"    → Status: {Fore.CYAN}{prev}{Style.RESET_ALL} → {Fore.GREEN}{curr}{Style.RESET_ALL}")
                            
                            # Check for debug stage (lowercase from enum)
                            if curr == 'debug':
                                debug_executed = True
                                print(f"    {Fore.YELLOW}⚙️  Debug node executing...{Style.RESET_ALL}")
                                
                        elif event_type == 'message':
                            content = event_data.get('text', '')
                            if content:
                                assistant_messages.append(content)
                                
                        elif event_type == 'workflow':
                            workflow_generated = True
                            self.workflow_json = event_data.get('workflow')
                            print(f"    {Fore.GREEN}✓ Workflow generated successfully!{Style.RESET_ALL}")
                            if self.workflow_json:
                                print(f"      Name: {self.workflow_json.get('name', 'Unknown')}")
                                print(f"      Nodes: {len(self.workflow_json.get('nodes', []))}")
                                print(f"      Connections: {len(self.workflow_json.get('connections', []))}")
                                
                        elif event_type == 'debug_result':
                            debug_result = event_data
                            success = debug_result.get('success', False)
                            if success:
                                print(f"    {Fore.GREEN}✓ Debug validation passed!{Style.RESET_ALL}")
                            else:
                                print(f"    {Fore.YELLOW}⚠️  Debug found issues:{Style.RESET_ALL}")
                                for error in debug_result.get('errors', []):
                                    print(f"      - {error}")
                                    
                        elif event_type == 'error':
                            error_msg = event_data.get('error', 'Unknown error')
                            errors.append(error_msg)
                            print(f"    {Fore.RED}✗ Error: {error_msg}{Style.RESET_ALL}")
                            
                    except json.JSONDecodeError as e:
                        print(f"    {Fore.RED}JSON parse error: {e}{Style.RESET_ALL}")
                    except Exception as e:
                        print(f"    {Fore.RED}Unexpected error: {e}{Style.RESET_ALL}")
                        
            print(f"  {Fore.CYAN}Total events processed: {event_count}{Style.RESET_ALL}")
            
            # Print complete assistant response
            if assistant_messages:
                self.print_separator()
                print(f"{Fore.GREEN}Assistant Response:{Style.RESET_ALL}")
                full_message = ''.join(assistant_messages)
                # Truncate long messages
                if len(full_message) > 500:
                    print(full_message[:500] + "...")
                else:
                    print(full_message)
                self.print_separator()
        
        # Record test results
        if workflow_generated:
            self.test_results.append(("Workflow Generation", True, None))
        else:
            self.test_results.append(("Workflow Generation", False, "No workflow generated"))
            
        if debug_executed:
            self.test_results.append(("Debug Execution", True, None))
        else:
            self.test_results.append(("Debug Execution", False, "Debug node not executed"))
            
        return workflow_generated and debug_executed
    
    def verify_workflow_structure(self):
        """Verify the generated workflow has valid structure"""
        self.print_step(4, "Verifying workflow structure")
        
        if not self.workflow_json:
            print(f"{Fore.RED}  ✗ No workflow to verify{Style.RESET_ALL}")
            self.test_results.append(("Workflow Structure", False, "No workflow generated"))
            return False
            
        checks = []
        
        # Check for required fields
        has_name = bool(self.workflow_json.get('name'))
        has_nodes = bool(self.workflow_json.get('nodes'))
        has_connections = bool(self.workflow_json.get('connections'))
        
        checks.append(("Has name", has_name))
        checks.append(("Has nodes", has_nodes))
        checks.append(("Has connections", has_connections))
        
        # Check nodes structure
        if has_nodes:
            nodes = self.workflow_json['nodes']
            for node in nodes:
                has_id = bool(node.get('id'))
                has_type = bool(node.get('type'))
                checks.append((f"Node {node.get('id', 'unknown')} valid", has_id and has_type))
        
        # Print results
        all_passed = all(check[1] for check in checks)
        for check_name, passed in checks:
            if passed:
                print(f"  {Fore.GREEN}✓ {check_name}{Style.RESET_ALL}")
            else:
                print(f"  {Fore.RED}✗ {check_name}{Style.RESET_ALL}")
                
        self.test_results.append(("Workflow Structure", all_passed, None if all_passed else "Structure validation failed"))
        return all_passed
    
    def test_simple_http_workflow(self):
        """Test case: Create a simple HTTP request workflow"""
        self.print_test_header("Test Case: Hourly HTTP Request to Google")
        
        # The test message
        test_message = "Create a workflow that sends an HTTP GET request to https://google.com every hour"
        
        # Execute the test
        success = self.send_workflow_request(test_message)
        
        if success:
            # Verify the generated workflow
            self.verify_workflow_structure()
            
            # Check specific workflow details
            if self.workflow_json:
                nodes = self.workflow_json.get('nodes', [])
                
                # Check for trigger node
                has_trigger = any(node.get('type') in ['trigger', 'TRIGGER_NODE'] for node in nodes)
                # Check for HTTP action node
                has_http = any(
                    node.get('type') in ['action', 'ACTION_NODE', 'external_action', 'EXTERNAL_ACTION_NODE'] 
                    for node in nodes
                )
                
                print(f"\n  Workflow Analysis:")
                print(f"    {Fore.GREEN if has_trigger else Fore.RED}{'✓' if has_trigger else '✗'} Has trigger node{Style.RESET_ALL}")
                print(f"    {Fore.GREEN if has_http else Fore.RED}{'✓' if has_http else '✗'} Has HTTP action node{Style.RESET_ALL}")
                
                self.test_results.append(("Has Trigger", has_trigger, None))
                self.test_results.append(("Has HTTP Action", has_http, None))
        
        return success
    
    def print_test_summary(self):
        """Print summary of all test results"""
        self.print_separator('═', Fore.CYAN)
        print(f"{Fore.CYAN}📊 Test Summary{Style.RESET_ALL}")
        self.print_separator('═', Fore.CYAN)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for _, passed, _ in self.test_results if passed)
        
        for test_name, passed, error in self.test_results:
            status = f"{Fore.GREEN}✓ PASS{Style.RESET_ALL}" if passed else f"{Fore.RED}✗ FAIL{Style.RESET_ALL}"
            print(f"  {status} - {test_name}")
            if error:
                print(f"         {Fore.YELLOW}Error: {error}{Style.RESET_ALL}")
        
        self.print_separator()
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        color = Fore.GREEN if success_rate >= 80 else Fore.YELLOW if success_rate >= 50 else Fore.RED
        print(f"  {color}Results: {passed_tests}/{total_tests} passed ({success_rate:.1f}%){Style.RESET_ALL}")
        
        return passed_tests == total_tests
    
    def run(self):
        """Run the complete end-to-end test"""
        print(f"\n{Fore.CYAN}{'='*80}")
        print("🚀 Workflow Debug End-to-End Test")
        print(f"{'='*80}{Style.RESET_ALL}")
        
        print(f"\n{Fore.YELLOW}Test Configuration:{Style.RESET_ALL}")
        print(f"  API URL: {API_BASE_URL}")
        print(f"  Supabase URL: {SUPABASE_URL}")
        print(f"  Test User: {TEST_USER_EMAIL}")
        
        # Check environment variables
        if not all([SUPABASE_URL, SUPABASE_ANON_KEY, TEST_USER_EMAIL, TEST_USER_PASSWORD]):
            print(f"\n{Fore.RED}❌ Missing required environment variables!{Style.RESET_ALL}")
            print(f"Please ensure the following are set in your .env file:")
            print(f"  - SUPABASE_URL")
            print(f"  - SUPABASE_ANON_KEY")
            print(f"  - TEST_USER_EMAIL")
            print(f"  - TEST_USER_PASSWORD")
            return False
        
        # Check if services are running
        print(f"\n{Fore.YELLOW}Checking service availability...{Style.RESET_ALL}")
        try:
            health_response = requests.get(f"{API_BASE_URL}/health", timeout=5)
            if health_response.status_code == 200:
                print(f"{Fore.GREEN}  ✓ API Gateway is running{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}  ⚠️  API Gateway returned status {health_response.status_code}{Style.RESET_ALL}")
        except requests.exceptions.RequestException as e:
            print(f"{Fore.RED}  ✗ Cannot connect to API Gateway at {API_BASE_URL}{Style.RESET_ALL}")
            print(f"  Error: {e}")
            print(f"\n{Fore.YELLOW}Please ensure all services are running:{Style.RESET_ALL}")
            print(f"  cd /Users/bytedance/personal/agent_team_monorepo/apps/backend")
            print(f"  docker-compose up")
            return False
        
        try:
            # Run the test flow
            if not self.authenticate():
                print(f"\n{Fore.RED}❌ Test aborted: Authentication failed{Style.RESET_ALL}")
                return False
                
            if not self.create_session():
                print(f"\n{Fore.RED}❌ Test aborted: Session creation failed{Style.RESET_ALL}")
                return False
            
            # Run test case
            time.sleep(1)  # Small delay for stability
            test_passed = self.test_simple_http_workflow()
            
            # Print summary
            time.sleep(1)
            all_passed = self.print_test_summary()
            
            if all_passed:
                print(f"\n{Fore.GREEN}✅ All tests passed successfully!{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.YELLOW}⚠️  Some tests failed. Check the summary above.{Style.RESET_ALL}")
                
            return all_passed
            
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Test interrupted by user{Style.RESET_ALL}")
            return False
        except Exception as e:
            print(f"\n{Fore.RED}❌ Unexpected error: {e}{Style.RESET_ALL}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    tester = WorkflowDebugE2ETester()
    success = tester.run()
    exit(0 if success else 1)