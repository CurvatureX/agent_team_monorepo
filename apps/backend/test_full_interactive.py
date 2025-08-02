#!/usr/bin/env python3
"""
Full interactive test for API Gateway /chat/stream endpoint
Supports authentication, session management, and interactive chat
"""
import json
import os
import sys
import time
import subprocess
from datetime import datetime
import threading
import queue

# Configuration
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8000")
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://mkrczzgjeduruwxpanbj.supabase.co")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1rcmN6emdqZWR1cnV3eHBhbmJqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzE5NzkyNTksImV4cCI6MjA0NzU1NTI1OX0.vqGIRBiM-jCkbmMXxY-BGcCommm2TQtYKLkLCXGQVBM")

# ANSI color codes
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


class InteractiveTester:
    def __init__(self):
        self.access_token = None
        self.session_id = None
        self.email = None
        self.password = None
        
    def print_color(self, text, color=""):
        """Print colored text"""
        print(f"{color}{text}{Colors.ENDC}")
        
    def print_header(self, text):
        """Print section header"""
        print(f"\n{Colors.BOLD}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.ENDC}")
        print(f"{Colors.BOLD}{'='*60}{Colors.ENDC}")
        
    def get_credentials(self):
        """Get user credentials"""
        self.print_header("🔐 AUTHENTICATION")
        
        # Check for test credentials in environment
        test_email = os.getenv("TEST_USER_EMAIL")
        test_password = os.getenv("TEST_USER_PASSWORD")
        
        if test_email and test_password:
            use_test = input(f"\n{Colors.CYAN}Use test credentials? (Y/n): {Colors.ENDC}").strip().lower()
            if use_test != 'n':
                self.email = test_email
                self.password = test_password
                self.print_color(f"Using test email: {self.email}", Colors.GREEN)
                return
        
        # Get credentials from user
        self.email = input(f"\n{Colors.CYAN}Email: {Colors.ENDC}").strip()
        if not self.email:
            self.print_color("Using guest mode (no authentication)", Colors.YELLOW)
            return
            
        # Use getpass for password
        import getpass
        self.password = getpass.getpass(f"{Colors.CYAN}Password: {Colors.ENDC}")
        
    def authenticate(self):
        """Authenticate with Supabase"""
        if not self.email or not self.password:
            self.print_color("Skipping authentication (guest mode)", Colors.YELLOW)
            return True
            
        self.print_color("\nAuthenticating...", Colors.BLUE)
        
        # Prepare curl command for authentication
        auth_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
        
        curl_cmd = [
            'curl', '-s', '-X', 'POST', auth_url,
            '-H', f'apikey: {SUPABASE_ANON_KEY}',
            '-H', 'Content-Type: application/json',
            '-d', json.dumps({
                "email": self.email,
                "password": self.password
            })
        ]
        
        try:
            result = subprocess.run(curl_cmd, capture_output=True, text=True)
            if result.returncode == 0:
                response = json.loads(result.stdout)
                if 'access_token' in response:
                    self.access_token = response['access_token']
                    self.print_color("✅ Authentication successful!", Colors.GREEN)
                    return True
                else:
                    error_msg = response.get('error', response.get('msg', 'Unknown error'))
                    self.print_color(f"❌ Authentication failed: {error_msg}", Colors.RED)
                    return False
            else:
                self.print_color(f"❌ Authentication request failed", Colors.RED)
                return False
        except Exception as e:
            self.print_color(f"❌ Authentication error: {e}", Colors.RED)
            return False
    
    def create_session(self):
        """Create a new chat session"""
        self.print_color("\nCreating session...", Colors.BLUE)
        
        headers = ['-H', 'Content-Type: application/json']
        if self.access_token:
            headers.extend(['-H', f'Authorization: Bearer {self.access_token}'])
        
        curl_cmd = [
            'curl', '-s', '-X', 'POST',
            f'{API_GATEWAY_URL}/api/app/sessions'
        ] + headers + [
            '-d', json.dumps({
                "action": "create",
                "name": f"Interactive Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "workflow_id": None
            })
        ]
        
        try:
            result = subprocess.run(curl_cmd, capture_output=True, text=True)
            if result.returncode == 0:
                response = json.loads(result.stdout)
                if 'id' in response:
                    self.session_id = response['id']
                    self.print_color(f"✅ Session created: {self.session_id}", Colors.GREEN)
                    return True
                else:
                    self.print_color(f"❌ Failed to create session: {result.stdout}", Colors.RED)
                    return False
            else:
                self.print_color(f"❌ Session creation failed", Colors.RED)
                return False
        except Exception as e:
            self.print_color(f"❌ Session creation error: {e}", Colors.RED)
            return False
    
    def send_message_streaming(self, message):
        """Send a message and handle streaming response"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}YOU: {message}{Colors.ENDC}")
        
        headers = [
            '-H', 'Content-Type: application/json',
            '-H', 'Accept: text/event-stream'
        ]
        if self.access_token:
            headers.extend(['-H', f'Authorization: Bearer {self.access_token}'])
        
        curl_cmd = [
            'curl', '-s', '-X', 'POST',
            f'{API_GATEWAY_URL}/api/app/chat/stream',
            '-N'  # No buffering for streaming
        ] + headers + [
            '-d', json.dumps({
                "session_id": self.session_id,
                "user_message": message
            })
        ]
        
        # Start curl process
        process = subprocess.Popen(
            curl_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        current_stage = None
        assistant_response = []
        
        try:
            # Read streaming response
            for line in process.stdout:
                line = line.strip()
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        event_type = data.get("type")
                        event_data = data.get("data", {})
                        
                        if event_type == "status_change":
                            new_stage = event_data.get("current_stage")
                            if new_stage and new_stage != current_stage:
                                current_stage = new_stage
                                self.print_color(f"\n🔄 Stage: {new_stage}", Colors.YELLOW)
                                
                        elif event_type == "message":
                            text = event_data.get("text", "")
                            if text:
                                if not assistant_response:
                                    print(f"\n{Colors.BOLD}{Colors.GREEN}ASSISTANT:{Colors.ENDC}")
                                print(f"{Colors.GREEN}{text}{Colors.ENDC}")
                                assistant_response.append(text)
                                
                        elif event_type == "workflow":
                            self.print_color("\n✨ WORKFLOW GENERATED!", Colors.BOLD + Colors.CYAN)
                            workflow = event_data.get("workflow", {})
                            if isinstance(workflow, dict):
                                print(json.dumps(workflow, indent=2))
                                
                        elif event_type == "error":
                            error_msg = event_data.get("error", "Unknown error")
                            self.print_color(f"\n❌ Error: {error_msg}", Colors.RED)
                            
                    except json.JSONDecodeError:
                        pass
                        
            # Wait for process to complete
            process.wait()
            
        except KeyboardInterrupt:
            process.terminate()
            raise
        except Exception as e:
            self.print_color(f"\n❌ Streaming error: {e}", Colors.RED)
            process.terminate()
    
    def run_interactive(self):
        """Run interactive chat session"""
        self.print_header("💬 INTERACTIVE CHAT")
        print(f"\nSession: {self.session_id}")
        print(f"\nCommands:")
        print(f"  {Colors.CYAN}/new{Colors.ENDC}     - Create new session")
        print(f"  {Colors.CYAN}/exit{Colors.ENDC}    - Exit the program")
        print(f"  {Colors.CYAN}/history{Colors.ENDC} - Show conversation (coming soon)")
        print(f"\n{Colors.GREEN}Type your message and press Enter:{Colors.ENDC}")
        print(f"{Colors.BOLD}{'='*60}{Colors.ENDC}")
        
        while True:
            try:
                # Get user input
                user_input = input(f"\n{Colors.CYAN}> {Colors.ENDC}").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.lower() == '/exit':
                    self.print_color("\n👋 Goodbye!", Colors.GREEN)
                    break
                    
                elif user_input.lower() == '/new':
                    if self.create_session():
                        self.print_color("🆕 New session started!", Colors.GREEN)
                    continue
                    
                elif user_input.lower() == '/history':
                    self.print_color("📜 History feature coming soon...", Colors.YELLOW)
                    continue
                
                # Send message
                self.send_message_streaming(user_input)
                
            except KeyboardInterrupt:
                self.print_color("\n\nUse /exit to quit", Colors.YELLOW)
            except Exception as e:
                self.print_color(f"\n❌ Error: {e}", Colors.RED)
    
    def run(self):
        """Main entry point"""
        print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"{Colors.HEADER}🚀 API GATEWAY FULL CHAIN INTERACTIVE TESTER{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
        
        # Check services
        self.print_color("\nChecking services...", Colors.BLUE)
        
        # Check API Gateway
        try:
            result = subprocess.run(
                ['curl', '-s', f'{API_GATEWAY_URL}/health'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and 'healthy' in result.stdout:
                self.print_color("✅ API Gateway is healthy", Colors.GREEN)
            else:
                raise Exception("API Gateway not healthy")
        except:
            self.print_color("❌ API Gateway is not running", Colors.RED)
            self.print_color("Please run: docker compose up", Colors.YELLOW)
            return
        
        # Get credentials
        self.get_credentials()
        
        # Authenticate
        if not self.authenticate():
            self.print_color("\nContinuing without authentication...", Colors.YELLOW)
        
        # Create session
        if not self.create_session():
            self.print_color("Failed to create session. Exiting.", Colors.RED)
            return
        
        # Run interactive mode
        self.run_interactive()


def main():
    """Main function"""
    tester = InteractiveTester()
    tester.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Interrupted{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.RED}Fatal error: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()