#!/usr/bin/env python3
"""
Clean Chat Test - Focus on SSE messages, status changes, and assistant responses
"""

import os
import json
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


class CleanChatTester:
    def __init__(self):
        self.session = requests.Session()
        self.access_token = None
        self.session_id = None
        
    def print_separator(self):
        print(f"{Fore.WHITE}{'─'*80}{Style.RESET_ALL}")
        
    def authenticate(self):
        """Authenticate and get access token"""
        print(f"\n{Fore.CYAN}🔐 Authenticating...{Style.RESET_ALL}")
        
        response = self.session.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        
        if response.status_code == 200:
            self.access_token = response.json().get("access_token")
            print(f"{Fore.GREEN}✓ Authentication successful{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}✗ Authentication failed: {response.status_code}{Style.RESET_ALL}")
            return False
            
    def create_session(self):
        """Create chat session"""
        print(f"\n{Fore.CYAN}📝 Creating session...{Style.RESET_ALL}")
        
        response = self.session.post(
            f"{API_BASE_URL}/api/v1/app/sessions",
            headers={"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"},
            json={"action": "create"}
        )
        
        if response.status_code == 200:
            self.session_id = response.json()["session"]["id"]
            print(f"{Fore.GREEN}✓ Session created: {self.session_id}{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}✗ Session creation failed: {response.status_code}{Style.RESET_ALL}")
            return False
            
    def chat(self, message):
        """Send message and process stream"""
        self.print_separator()
        print(f"{Fore.CYAN}USER:{Style.RESET_ALL} {message}")
        self.print_separator()
        
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
                print(f"{Fore.RED}Request failed: {response.status_code}{Style.RESET_ALL}")
                return
                
            # Print tracking ID from response headers
            tracking_id = response.headers.get('X-Tracking-ID')
            if not tracking_id:
                # Also check for lowercase header
                tracking_id = response.headers.get('x-tracking-id')
            if tracking_id:
                print(f"{Fore.MAGENTA}Tracking ID: {tracking_id}{Style.RESET_ALL}")
                
            event_count = 0
            assistant_messages = []
            
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
                        
                        # Print raw SSE message
                        print(f"\n{Fore.YELLOW}[SSE Event #{event_count}]{Style.RESET_ALL}")
                        print(json.dumps(event, indent=2, ensure_ascii=False))
                        
                        # Handle specific event types
                        event_type = event.get('type')
                        event_data = event.get('data', {})
                        
                        if event_type == 'status_change':
                            # Highlight status transitions
                            prev = event_data.get('previous_stage', 'unknown')
                            curr = event_data.get('current_stage', 'unknown')
                            print(f"\n{Fore.MAGENTA}>>> Status Change: {prev} → {curr}{Style.RESET_ALL}")
                            
                        elif event_type == 'message':
                            # Collect assistant messages
                            content = event_data.get('text', '')
                            if content:
                                assistant_messages.append(content)
                                
                        elif event_type == 'workflow':
                            print(f"\n{Fore.GREEN}>>> Workflow Generated!{Style.RESET_ALL}")
                            
                        elif event_type == 'error':
                            print(f"\n{Fore.RED}>>> Error: {event_data.get('error', 'Unknown')}{Style.RESET_ALL}")
                            
                    except json.JSONDecodeError as e:
                        print(f"{Fore.RED}JSON parse error: {e}{Style.RESET_ALL}")
                        
            # Print complete assistant response
            if assistant_messages:
                self.print_separator()
                print(f"{Fore.GREEN}ASSISTANT:{Style.RESET_ALL}")
                full_message = ''.join(assistant_messages)
                print(full_message)
                self.print_separator()
                
            print(f"\n{Fore.CYAN}Total events: {event_count}{Style.RESET_ALL}")
            
    def run(self):
        """Run the test"""
        print(f"\n{Fore.CYAN}{'='*80}")
        print("Workflow Chat Test - Clean Output")
        print(f"{'='*80}{Style.RESET_ALL}")
        
        if not all([SUPABASE_URL, SUPABASE_ANON_KEY, TEST_USER_EMAIL, TEST_USER_PASSWORD]):
            print(f"{Fore.RED}Missing required environment variables!{Style.RESET_ALL}")
            return
            
        if not self.authenticate():
            return
            
        if not self.create_session():
            return
            
        print(f"\n{Fore.YELLOW}Ready to chat. Type 'exit' to quit.{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Example: Send a HTTP request to https://google.com every 5 minutes{Style.RESET_ALL}\n")
        
        while True:
            try:
                user_input = input(f"\n{Fore.CYAN}> {Style.RESET_ALL}")
                if user_input.lower() in ['exit', 'quit']:
                    break
                if user_input.strip():
                    self.chat(user_input)
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Interrupted{Style.RESET_ALL}")
                break
                
        print(f"\n{Fore.GREEN}Test completed!{Style.RESET_ALL}")


if __name__ == "__main__":
    tester = CleanChatTester()
    tester.run()