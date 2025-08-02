#!/usr/bin/env python3
"""
Simple interactive chat test for API Gateway
Minimal dependencies, maximum compatibility
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime

# Load .env file if exists
if os.path.exists('.env'):
    with open('.env', 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

# Configuration
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8000")
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://mkrczzgjeduruwxpanbj.supabase.co")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "sb_publishable_GDldaQkfc6tfJ2aEOx_H3w_rq2Tc5G3")

# Colors
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RED = '\033[91m'
BOLD = '\033[1m'
ENDC = '\033[0m'


class ChatTester:
    def __init__(self):
        self.access_token = None
        self.session_id = None
        
    def print_header(self, text):
        print(f"\n{BOLD}{'='*60}{ENDC}")
        print(f"{BOLD}{CYAN}{text}{ENDC}")
        print(f"{BOLD}{'='*60}{ENDC}")
        
    def authenticate(self):
        """Try to authenticate with test credentials"""
        # Load from .env file if exists
        if os.path.exists('.env'):
            with open('.env', 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        if key in ['TEST_USER_EMAIL', 'TEST_USER_PASSWORD', 'SUPABASE_URL', 'SUPABASE_ANON_KEY']:
                            os.environ[key] = value
        
        email = os.getenv("TEST_USER_EMAIL")
        password = os.getenv("TEST_USER_PASSWORD")
        
        if not email or not password:
            print(f"{YELLOW}No test credentials found. Using guest mode.{ENDC}")
            return True
            
        print(f"{BLUE}Authenticating...{ENDC}")
        
        auth_data = json.dumps({
            "email": email,
            "password": password
        })
        
        cmd = f'''curl -s -X POST "{SUPABASE_URL}/auth/v1/token?grant_type=password" \
            -H "apikey: {SUPABASE_ANON_KEY}" \
            -H "Content-Type: application/json" \
            -d '{auth_data}' '''
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        try:
            response = json.loads(result.stdout)
            if 'access_token' in response:
                self.access_token = response['access_token']
                print(f"{GREEN}✅ Authentication successful!{ENDC}")
                return True
            else:
                print(f"{RED}Authentication failed: {response.get('msg', 'Unknown error')}{ENDC}")
                print(f"{YELLOW}Continuing without authentication...{ENDC}")
                return True
        except:
            print(f"{YELLOW}Authentication response parsing failed. Continuing...{ENDC}")
            return True
    
    def create_session(self):
        """Create a new chat session"""
        print(f"{BLUE}Creating session...{ENDC}")
        
        session_data = json.dumps({
            "action": "create",
            "name": f"Chat Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "workflow_id": None
        })
        
        headers = "-H 'Content-Type: application/json'"
        if self.access_token:
            headers += f" -H 'Authorization: Bearer {self.access_token}'"
        
        cmd = f'''curl -s -X POST "{API_GATEWAY_URL}/api/v1/app/sessions" \
            {headers} \
            -d '{session_data}' '''
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        try:
            response = json.loads(result.stdout)
            # Check for session object in response
            if 'session' in response and 'id' in response['session']:
                self.session_id = response['session']['id']
                print(f"{GREEN}✅ Session created: {self.session_id}{ENDC}")
                return True
            elif 'id' in response:
                self.session_id = response['id']
                print(f"{GREEN}✅ Session created: {self.session_id}{ENDC}")
                return True
            else:
                print(f"{RED}Failed to create session: {result.stdout}{ENDC}")
                return False
        except:
            print(f"{RED}Session creation failed{ENDC}")
            return False
    
    def send_message(self, message):
        """Send a message and stream the response"""
        print(f"\n{BOLD}{BLUE}YOU: {message}{ENDC}")
        
        # Prepare the curl command for streaming
        message_data = json.dumps({
            "session_id": self.session_id,
            "user_message": message
        })
        
        headers = "-H 'Content-Type: application/json' -H 'Accept: text/event-stream'"
        if self.access_token:
            headers += f" -H 'Authorization: Bearer {self.access_token}'"
        
        # Add timeout and keep-alive options to curl
        cmd = f'''curl -s -X POST "{API_GATEWAY_URL}/api/v1/app/chat/stream" \
            {headers} \
            -d '{message_data}' \
            -N \
            --max-time 60 \
            --keepalive-time 10'''
        
        # Execute curl and stream output
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        
        current_stage = None
        assistant_responded = False
        
        try:
            # Read streaming response line by line
            while True:
                line = process.stdout.readline()
                if not line:
                    # Check if process has terminated
                    if process.poll() is not None:
                        break
                    continue
                
                line = line.strip()
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        event_type = data.get("type")
                        
                        if event_type == "status_change":
                            stage = data.get("data", {}).get("current_stage")
                            if stage and stage != current_stage:
                                current_stage = stage
                                print(f"{YELLOW}🔄 Stage: {stage}{ENDC}")
                                
                        elif event_type == "message":
                            text = data.get("data", {}).get("text", "")
                            if text:
                                if not assistant_responded:
                                    print(f"\n{BOLD}{GREEN}ASSISTANT:{ENDC}")
                                    assistant_responded = True
                                print(f"{GREEN}{text}{ENDC}")
                                
                        elif event_type == "workflow":
                            print(f"\n{BOLD}{CYAN}✨ WORKFLOW GENERATED!{ENDC}")
                            workflow = data.get("data", {}).get("workflow", {})
                            print(json.dumps(workflow, indent=2))
                            
                        elif event_type == "error":
                            error = data.get("data", {}).get("error", "Unknown error")
                            print(f"{RED}❌ Error: {error}{ENDC}")
                            
                        # Check if this is the final message
                        if data.get("is_final", False):
                            break
                            
                    except json.JSONDecodeError:
                        pass
            
            # Wait for process to complete properly
            remaining_output = process.stdout.read()
            if remaining_output:
                for line in remaining_output.strip().split('\n'):
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if data.get("type") == "message":
                                text = data.get("data", {}).get("text", "")
                                if text and not assistant_responded:
                                    print(f"\n{BOLD}{GREEN}ASSISTANT:{ENDC}")
                                    print(f"{GREEN}{text}{ENDC}")
                        except:
                            pass
            
            # Ensure process completes
            process.wait(timeout=5)
            
        except subprocess.TimeoutExpired:
            print(f"{YELLOW}Response timeout{ENDC}")
            process.terminate()
        except KeyboardInterrupt:
            process.terminate()
            print(f"\n{YELLOW}Message interrupted{ENDC}")
        except Exception as e:
            print(f"{RED}Stream error: {e}{ENDC}")
            process.terminate()
    
    def run_interactive(self):
        """Run interactive chat"""
        self.print_header("💬 INTERACTIVE CHAT")
        
        print(f"\nCommands:")
        print(f"  {CYAN}/exit{ENDC}  - Exit the program")
        print(f"  {CYAN}/new{ENDC}   - Create new session")
        print(f"  {CYAN}/demo{ENDC}  - Run demo scenario")
        print(f"\nSession: {self.session_id}")
        print(f"{GREEN}Ready! Type your message:{ENDC}\n")
        
        while True:
            try:
                # Get user input
                user_input = input(f"{CYAN}> {ENDC}").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.lower() == '/exit':
                    print(f"{GREEN}👋 Goodbye!{ENDC}")
                    break
                    
                elif user_input.lower() == '/new':
                    if self.create_session():
                        print(f"{GREEN}New session started!{ENDC}")
                        
                elif user_input.lower() == '/demo':
                    self.run_demo()
                    
                else:
                    # Send message
                    self.send_message(user_input)
                    
            except KeyboardInterrupt:
                print(f"\n{YELLOW}Use /exit to quit{ENDC}")
            except EOFError:
                print(f"\n{YELLOW}EOF detected. Exiting...{ENDC}")
                break
            except Exception as e:
                print(f"{RED}Error: {e}{ENDC}")
    
    def run_demo(self):
        """Run a demo scenario"""
        print(f"\n{BOLD}{CYAN}Running demo scenario...{ENDC}")
        
        messages = [
            "Create a workflow to sync Gmail emails to Slack",
            "New emails with specific labels, send subject and sender to #notifications channel", 
            "Use the 'important' and 'urgent' labels"
        ]
        
        for i, msg in enumerate(messages):
            print(f"\n{CYAN}--- Message {i+1} of {len(messages)} ---{ENDC}")
            self.send_message(msg)
            
            # Wait between messages
            if i < len(messages) - 1:
                print(f"\n{CYAN}Waiting 5 seconds before next message...{ENDC}")
                time.sleep(5)
            print()
        
        print(f"{GREEN}Demo completed!{ENDC}")
    
    def run(self):
        """Main entry point"""
        print(f"{BOLD}{CYAN}{'='*60}{ENDC}")
        print(f"{BOLD}{CYAN}🚀 API GATEWAY CHAT TESTER{ENDC}")
        print(f"{BOLD}{CYAN}{'='*60}{ENDC}")
        
        # Check if API Gateway is running
        print(f"\n{BLUE}Checking services...{ENDC}")
        
        try:
            result = subprocess.run(
                f'curl -s {API_GATEWAY_URL}/health',
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            if 'healthy' in result.stdout:
                print(f"{GREEN}✅ API Gateway is healthy{ENDC}")
            else:
                raise Exception("Not healthy")
        except:
            print(f"{RED}❌ API Gateway is not running{ENDC}")
            print(f"{YELLOW}Please run: docker compose up{ENDC}")
            return
        
        # Authenticate
        if not self.authenticate():
            return
        
        # Create session
        if not self.create_session():
            return
        
        # Run interactive mode
        self.run_interactive()


if __name__ == "__main__":
    # Handle command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--demo":
            # Run demo mode
            tester = ChatTester()
            if tester.authenticate() and tester.create_session():
                tester.run_demo()
        elif sys.argv[1] == "--help":
            print("Usage:")
            print("  python chat_test.py          # Interactive mode")
            print("  python chat_test.py --demo   # Run demo scenario")
        else:
            print(f"Unknown option: {sys.argv[1]}")
    else:
        # Run interactive mode
        try:
            tester = ChatTester()
            tester.run()
        except KeyboardInterrupt:
            print(f"\n{YELLOW}Interrupted{ENDC}")
        except Exception as e:
            print(f"\n{RED}Fatal error: {e}{ENDC}")
            import traceback
            traceback.print_exc()