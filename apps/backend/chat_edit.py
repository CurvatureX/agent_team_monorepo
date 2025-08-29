#!/usr/bin/env python3
"""
Edit Workflow Chat Test - Test editing existing workflows through chat interface
"""

import json
import os
from datetime import datetime
from typing import Optional

import requests
from colorama import Fore, Style, init
from dotenv import load_dotenv

# Initialize colorama
init(autoreset=True)

# Load environment variables
load_dotenv()

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
WORKFLOW_ENGINE_URL = os.getenv("WORKFLOW_ENGINE_URL", "http://localhost:8002")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL")
TEST_USER_PASSWORD = os.getenv("TEST_USER_PASSWORD")


class EditWorkflowChatTester:
    def __init__(self):
        self.session = requests.Session()
        self.access_token = None
        self.session_id = None
        self.workflow_id = None

    def print_separator(self):
        print(f"{Fore.WHITE}{'─'*80}{Style.RESET_ALL}")

    def authenticate(self):
        """Authenticate and get access token"""
        print(f"\n{Fore.CYAN}🔐 Authenticating...{Style.RESET_ALL}")

        response = self.session.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
        )

        if response.status_code == 200:
            self.access_token = response.json().get("access_token")
            print(f"{Fore.GREEN}✓ Authentication successful{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}✗ Authentication failed: {response.status_code}{Style.RESET_ALL}")
            return False

    def create_session(self, action="create", workflow_id=None):
        """Create chat session with specific action"""
        print(f"\n{Fore.CYAN}📝 Creating session (action={action})...{Style.RESET_ALL}")

        session_data = {"action": action}
        if workflow_id:
            session_data["workflow_id"] = workflow_id

        response = self.session.post(
            f"{API_BASE_URL}/api/v1/app/sessions",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
            json=session_data,
        )

        if response.status_code == 200:
            self.session_id = response.json()["session"]["id"]
            print(f"{Fore.GREEN}✓ Session created: {self.session_id}{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}✗ Session creation failed: {response.status_code}{Style.RESET_ALL}")
            return False


    def chat(self, message, action=None, workflow_id=None):
        """Send message and process stream with optional edit parameters"""
        self.print_separator()
        print(f"{Fore.CYAN}USER:{Style.RESET_ALL} {message}")
        if action:
            print(f"{Fore.YELLOW}[Mode: {action.upper()}{' - Workflow: ' + workflow_id if workflow_id else ''}]{Style.RESET_ALL}")
        self.print_separator()

        # Build request data
        request_data = {
            "session_id": self.session_id,
            "user_message": message
        }
        
        # Add action and workflow_id if provided
        if action:
            request_data["action"] = action
        if workflow_id:
            request_data["workflow_id"] = workflow_id

        with self.session.post(
            f"{API_BASE_URL}/api/v1/app/chat/stream",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            },
            json=request_data,
            stream=True,
            timeout=120,
        ) as response:
            if response.status_code != 200:
                print(f"{Fore.RED}Request failed: {response.status_code}{Style.RESET_ALL}")
                try:
                    error_text = response.text
                    print(f"{Fore.RED}Error details: {error_text}{Style.RESET_ALL}")
                except:
                    pass
                return None

            # Print tracking ID from response headers
            trace_id = response.headers.get("X-Trace-ID") or response.headers.get("x-trace-id")
            if trace_id:
                print(f"{Fore.MAGENTA}Trace ID: {trace_id}{Style.RESET_ALL}")

            event_count = 0
            assistant_messages = []
            returned_workflow_id = None
            workflow_data = None

            for line in response.iter_lines():
                if line and line.startswith(b"data: "):
                    try:
                        data_str = line[6:].decode("utf-8")

                        if data_str == "[DONE]":
                            break

                        if not data_str.strip():
                            continue

                        # Parse SSE event
                        event = json.loads(data_str)
                        event_count += 1

                        # Handle specific event types
                        event_type = event.get("type")
                        event_data = event.get("data", {})

                        if event_type == "status_change":
                            # Highlight status transitions
                            prev = event_data.get("previous_stage", "unknown")
                            curr = event_data.get("current_stage", "unknown")
                            print(f"\n{Fore.MAGENTA}>>> Status: {prev} → {curr}{Style.RESET_ALL}")

                        elif event_type == "message":
                            # Collect assistant messages
                            content = event_data.get("text", "")
                            if content:
                                assistant_messages.append(content)

                        elif event_type == "workflow":
                            print(f"\n{Fore.GREEN}>>> Workflow {'Updated' if action == 'edit' else 'Generated'}!{Style.RESET_ALL}")
                            
                            # Extract workflow data
                            workflow_info = event_data.get("workflow", {})
                            if workflow_info:
                                workflow_data = workflow_info
                                returned_workflow_id = workflow_info.get("workflow_id")
                                
                                # Show workflow details
                                print(f"  ID: {returned_workflow_id}")
                                print(f"  Name: {workflow_info.get('name', 'Unknown')}")
                                print(f"  Nodes: {len(workflow_info.get('nodes', []))}")
                                
                                # In edit mode, a new workflow is always created based on the original
                                if action == "edit" and workflow_id:
                                    if returned_workflow_id != workflow_id:
                                        print(f"  {Fore.GREEN}✓ New workflow created based on original{Style.RESET_ALL}")
                                        print(f"  Original ID: {workflow_id}")
                                        print(f"  New ID: {returned_workflow_id}")
                                
                                # Show what changed for edit mode
                                if action == "edit" and workflow_data.get("nodes"):
                                    print(f"\n  {Fore.CYAN}Modified nodes:{Style.RESET_ALL}")
                                    for node in workflow_data["nodes"]:
                                        if node.get("type") == "TRIGGER":
                                            cron = node.get("parameters", {}).get("cron", "")
                                            print(f"    - Trigger: {cron}")
                                        elif node.get("type") == "ACTION" and node.get("subtype") == "EMAIL":
                                            params = node.get("parameters", {})
                                            print(f"    - Email to: {params.get('to', 'N/A')}")
                                            print(f"    - Subject: {params.get('subject', 'N/A')}")

                        elif event_type == "error":
                            print(f"\n{Fore.RED}>>> Error: {event_data.get('error', 'Unknown')}{Style.RESET_ALL}")

                    except json.JSONDecodeError as e:
                        print(f"{Fore.RED}JSON parse error: {e}{Style.RESET_ALL}")

            # Print complete assistant response
            if assistant_messages:
                self.print_separator()
                print(f"{Fore.GREEN}ASSISTANT:{Style.RESET_ALL}")
                full_message = "".join(assistant_messages)
                print(full_message)
                self.print_separator()

            print(f"\n{Fore.CYAN}Total events: {event_count}{Style.RESET_ALL}")
            
            return returned_workflow_id

    def run_interactive_mode(self):
        """Run interactive chat mode with edit support"""
        print(f"\n{Fore.YELLOW}{'='*80}")
        print("INTERACTIVE EDIT MODE")
        print(f"{'='*80}{Style.RESET_ALL}")

        print(f"\n{Fore.YELLOW}Commands:{Style.RESET_ALL}")
        print("  create              - Start creating a new workflow")
        print("  edit <workflow_id>  - Edit an existing workflow")
        print("  exit/quit           - Exit the program")
        print(f"\n{Fore.YELLOW}Example: edit wf-123-456{Style.RESET_ALL}")
        
        # Create initial session
        if not self.create_session():
            return

        current_mode = "create"
        current_workflow_id = None

        while True:
            try:
                user_input = input(f"\n{Fore.CYAN}> {Style.RESET_ALL}")
                
                if user_input.lower() in ["exit", "quit"]:
                    break
                
                # Check for mode commands
                if user_input.lower() == "create":
                    # Switch to create mode
                    current_mode = "create"
                    current_workflow_id = None
                    self.create_session(action="create")
                    print(f"{Fore.GREEN}Switched to CREATE mode{Style.RESET_ALL}")
                    continue
                    
                elif user_input.lower().startswith("edit "):
                    # Switch to edit mode with workflow ID
                    parts = user_input.split(maxsplit=1)
                    if len(parts) == 2:
                        current_workflow_id = parts[1]
                        current_mode = "edit"
                        self.create_session(action="edit", workflow_id=current_workflow_id)
                        print(f"{Fore.GREEN}Switched to EDIT mode for workflow: {current_workflow_id}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.RED}Usage: edit <workflow_id>{Style.RESET_ALL}")
                    continue
                    

                # Regular chat message
                if user_input.strip():
                    if current_mode == "edit" and current_workflow_id:
                        self.chat(user_input, action="edit", workflow_id=current_workflow_id)
                    else:
                        self.chat(user_input)

            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Interrupted{Style.RESET_ALL}")
                break

        print(f"\n{Fore.GREEN}Edit workflow test completed!{Style.RESET_ALL}")

    def run(self):
        """Main run method"""
        print(f"\n{Fore.CYAN}{'='*80}")
        print("Workflow Edit Chat Test")
        print(f"{'='*80}{Style.RESET_ALL}")

        if not all([SUPABASE_URL, SUPABASE_ANON_KEY, TEST_USER_EMAIL, TEST_USER_PASSWORD]):
            print(f"{Fore.RED}Missing required environment variables!{Style.RESET_ALL}")
            return

        if not self.authenticate():
            return

        # Go directly to interactive mode
        self.run_interactive_mode()


if __name__ == "__main__":
    tester = EditWorkflowChatTester()
    tester.run()