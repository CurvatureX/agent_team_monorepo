#!/usr/bin/env python3
"""
Improved Chat Test - Handles long input without terminal limitations
"""

import os
import json
import requests
import tempfile
import subprocess
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


class ImprovedChatTester:
    def __init__(self):
        self.session = requests.Session()
        self.access_token = None
        self.session_id = None
        self.conversation_history = []  # Store conversation for markdown export
        self.sse_events = []  # Store all SSE events for debugging
        self.start_time = None
        
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
            
    def get_multiline_input(self):
        """Open text editor for long input"""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as tf:
            tf.write("# Type your message below (lines starting with # will be ignored)\n")
            tf.write("# Save and close the editor when done\n\n")
            temp_filename = tf.name
        
        # Determine which editor to use
        editor = os.environ.get('EDITOR', 'nano')  # Default to nano if EDITOR not set
        if os.name == 'nt':  # Windows
            editor = 'notepad'
        elif not os.system('which vim >/dev/null 2>&1'):  # Check if vim exists
            editor = 'vim'
        elif not os.system('which nano >/dev/null 2>&1'):  # Check if nano exists
            editor = 'nano'
        
        # Open the editor
        try:
            subprocess.call([editor, temp_filename])
        except:
            # Fallback to basic input if editor fails
            print(f"{Fore.YELLOW}Editor failed to open. Using basic input instead.{Style.RESET_ALL}")
            return input("Enter your message: ")
        
        # Read the content
        with open(temp_filename, 'r') as f:
            lines = f.readlines()
        
        # Remove the temp file
        os.unlink(temp_filename)
        
        # Filter out comment lines and join
        message_lines = [line.rstrip() for line in lines if not line.strip().startswith('#')]
        return ' '.join(message_lines).strip()
    
    def chat(self, message):
        """Send message and process stream"""
        self.print_separator()
        print(f"{Fore.CYAN}USER:{Style.RESET_ALL} {message}")
        self.print_separator()
        
        # Store user message in history
        message_timestamp = datetime.now().isoformat()
        self.conversation_history.append({
            "role": "user",
            "content": message,
            "timestamp": message_timestamp
        })
        
        # Clear SSE events for this message
        current_sse_events = []
        
        with self.session.post(
            f"{API_BASE_URL}/api/v1/app/chat/stream",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream"
            },
            json={"session_id": self.session_id, "user_message": message},
            stream=True,
            timeout=300  # 5 minute timeout for workflow generation
        ) as response:
            
            if response.status_code != 200:
                print(f"{Fore.RED}Request failed: {response.status_code}{Style.RESET_ALL}")
                error_msg = f"Request failed with status code: {response.status_code}"
                self.conversation_history.append({
                    "role": "error",
                    "content": error_msg,
                    "timestamp": datetime.now().isoformat(),
                    "sse_events": current_sse_events  # Include any SSE events before error
                })
                return
                
            # Print tracking ID from response headers
            trace_id = response.headers.get('X-Trace-ID')
            if trace_id:
                print(f"{Fore.MAGENTA}Trace ID: {trace_id}{Style.RESET_ALL}")
            
            # Also check for x-tracking-id (lowercase)
            tracking_id = response.headers.get('x-tracking-id')
            if tracking_id:
                print(f"{Fore.MAGENTA}Tracking ID: {tracking_id}{Style.RESET_ALL}")
                
            event_count = 0
            assistant_messages = []
            workflow_data = None
            
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
                        
                        # Store SSE event
                        current_sse_events.append({
                            "event_number": event_count,
                            "timestamp": datetime.now().isoformat(),
                            "data": event
                        })
                        
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
                            workflow_data = event_data.get('workflow')
                            
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
                
                # Store assistant response in history with SSE events
                self.conversation_history.append({
                    "role": "assistant",
                    "content": full_message,
                    "timestamp": datetime.now().isoformat(),
                    "workflow": workflow_data,  # Include workflow if generated
                    "sse_events": current_sse_events  # Include all SSE events
                })
            elif current_sse_events:
                # If no assistant message but we have SSE events, still save them
                self.conversation_history.append({
                    "role": "assistant",
                    "content": "(No message content, see SSE events)",
                    "timestamp": datetime.now().isoformat(),
                    "workflow": workflow_data,
                    "sse_events": current_sse_events
                })
            
            print(f"\n{Fore.CYAN}Total events: {event_count}{Style.RESET_ALL}")
    
    def save_conversation_to_markdown(self):
        """Save the entire conversation to a markdown file"""
        if not self.conversation_history:
            return
        
        # Create chat_history directory if it doesn't exist
        history_dir = os.path.join(os.path.dirname(__file__), 'chat_history')
        os.makedirs(history_dir, exist_ok=True)
        
        # Generate filename with timestamp and session ID
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"chat_{timestamp}_{self.session_id[:8] if self.session_id else 'nosession'}.md"
        filepath = os.path.join(history_dir, filename)
        
        # Create markdown content
        md_content = []
        md_content.append(f"# Chat Session - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        md_content.append(f"\n**Session ID:** `{self.session_id}`")
        
        if self.start_time:
            duration = datetime.now() - self.start_time
            md_content.append(f"**Duration:** {duration}")
        
        # Calculate SSE event statistics
        total_sse_events = 0
        event_types = {}
        for entry in self.conversation_history:
            if entry.get('sse_events'):
                for event in entry['sse_events']:
                    total_sse_events += 1
                    event_type = event['data'].get('type', 'unknown')
                    event_types[event_type] = event_types.get(event_type, 0) + 1
        
        if total_sse_events > 0:
            md_content.append(f"\n**Total SSE Events:** {total_sse_events}")
            md_content.append("**Event Types:**")
            for event_type, count in sorted(event_types.items()):
                md_content.append(f"  - `{event_type}`: {count}")
        
        md_content.append("\n---\n")
        md_content.append("## Conversation\n")
        
        for entry in self.conversation_history:
            timestamp = entry.get('timestamp', '')
            role = entry['role']
            content = entry['content']
            
            if role == 'user':
                md_content.append(f"### 👤 User ({timestamp})\n")
                md_content.append(f"{content}\n")
            elif role == 'assistant':
                md_content.append(f"### 🤖 Assistant ({timestamp})\n")
                md_content.append(f"{content}\n")
                
                # Include SSE events if present
                if entry.get('sse_events'):
                    md_content.append("\n<details>")
                    md_content.append("<summary>📊 SSE Events (click to expand)</summary>\n")
                    md_content.append("\n#### Event Stream Details\n")
                    
                    for sse_event in entry['sse_events']:
                        event_num = sse_event['event_number']
                        event_time = sse_event['timestamp']
                        event_data = sse_event['data']
                        event_type = event_data.get('type', 'unknown')
                        
                        md_content.append(f"\n**Event #{event_num}** - Type: `{event_type}` - Time: {event_time}\n")
                        md_content.append("```json")
                        md_content.append(json.dumps(event_data, indent=2, ensure_ascii=False))
                        md_content.append("```")
                    
                    md_content.append("</details>\n")
                
                # Include workflow if present
                if entry.get('workflow'):
                    md_content.append("\n<details>")
                    md_content.append("<summary>📋 Generated Workflow (click to expand)</summary>\n")
                    md_content.append("```json")
                    md_content.append(json.dumps(entry['workflow'], indent=2, ensure_ascii=False))
                    md_content.append("```")
                    md_content.append("</details>\n")
            elif role == 'error':
                md_content.append(f"### ❌ Error ({timestamp})\n")
                md_content.append(f"{content}\n")
            
            md_content.append("\n---\n")
        
        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md_content))
        
        print(f"\n{Fore.GREEN}✅ Conversation saved to: {filepath}{Style.RESET_ALL}")
        return filepath
            
    def run(self):
        """Run the test"""
        print(f"\n{Fore.CYAN}{'='*80}")
        print("Workflow Chat Test - Improved Input Handling")
        print(f"{'='*80}{Style.RESET_ALL}")
        
        if not all([SUPABASE_URL, SUPABASE_ANON_KEY, TEST_USER_EMAIL, TEST_USER_PASSWORD]):
            print(f"{Fore.RED}Missing required environment variables!{Style.RESET_ALL}")
            return
            
        if not self.authenticate():
            return
            
        if not self.create_session():
            return
        
        # Set start time for duration tracking
        self.start_time = datetime.now()
            
        print(f"\n{Fore.YELLOW}Ready to chat. Type 'exit' to quit.{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Type 'edit' to open a text editor for longer input.{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Type 'save' to save the conversation history without exiting.{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Example: I want to have a workflow that monitors GitHub PRs and sends notifications to Slack{Style.RESET_ALL}\n")
        
        import sys
        
        while True:
            try:
                # First, try readline for normal input
                print(f"\n{Fore.CYAN}> {Style.RESET_ALL}", end="", flush=True)
                user_input = sys.stdin.readline().rstrip('\n')
                
                if user_input.lower() in ['exit', 'quit']:
                    break
                
                # Allow user to save conversation without exiting
                if user_input.lower() == 'save':
                    self.save_conversation_to_markdown()
                    continue
                
                # Allow user to open editor for long input
                if user_input.lower() == 'edit':
                    print(f"{Fore.YELLOW}Opening editor for input...{Style.RESET_ALL}")
                    user_input = self.get_multiline_input()
                    
                if user_input.strip():
                    self.chat(user_input)
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Interrupted{Style.RESET_ALL}")
                break
            except EOFError:
                # Handle Ctrl+D
                print(f"\n{Fore.YELLOW}EOF detected{Style.RESET_ALL}")
                break
        
        # Save conversation before exiting
        if self.conversation_history:
            print(f"\n{Fore.CYAN}Saving conversation history...{Style.RESET_ALL}")
            self.save_conversation_to_markdown()
                
        print(f"\n{Fore.GREEN}Test completed!{Style.RESET_ALL}")


if __name__ == "__main__":
    tester = ImprovedChatTester()
    tester.run()