#!/usr/bin/env python3
"""
Interactive test script for the complete workflow agent flow
Includes authentication, session management, and chat streaming
"""
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Optional, List, Dict
import aiohttp
from aiohttp import ClientTimeout

# Configuration
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8000")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

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
    UNDERLINE = '\033[4m'


class WorkflowTester:
    def __init__(self):
        self.access_token: Optional[str] = None
        self.session_id: Optional[str] = None
        self.conversation_history: List[Dict] = []
        self.current_stage = None
        self.debug_mode = "--debug" in sys.argv
        
    def log(self, message: str, color: str = ""):
        """Print colored log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{Colors.CYAN}[{timestamp}]{Colors.ENDC} {color}{message}{Colors.ENDC}")
        
    def log_debug(self, message: str):
        """Print debug message if debug mode is on"""
        if self.debug_mode:
            self.log(f"🐛 {message}", Colors.YELLOW)
    
    async def authenticate(self, email: str, password: str) -> bool:
        """Authenticate with Supabase"""
        self.log("🔐 Authenticating...", Colors.BLUE)
        
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            self.log("❌ Missing SUPABASE_URL or SUPABASE_ANON_KEY in environment", Colors.RED)
            self.log("Using mock authentication for testing", Colors.YELLOW)
            self.access_token = "mock-token-for-testing"
            return True
        
        auth_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    auth_url,
                    json={"email": email, "password": password},
                    headers={
                        "apikey": SUPABASE_ANON_KEY,
                        "Content-Type": "application/json"
                    }
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.access_token = data.get("access_token")
                        self.log("✅ Authentication successful", Colors.GREEN)
                        return True
                    else:
                        error_text = await resp.text()
                        self.log(f"❌ Authentication failed: {resp.status}", Colors.RED)
                        self.log_debug(f"Response: {error_text}")
                        return False
            except Exception as e:
                self.log(f"❌ Authentication error: {e}", Colors.RED)
                return False
    
    async def create_session(self) -> bool:
        """Create a new session"""
        self.log("📝 Creating new session...", Colors.BLUE)
        
        async with aiohttp.ClientSession() as session:
            try:
                headers = {
                    "Content-Type": "application/json"
                }
                if self.access_token:
                    headers["Authorization"] = f"Bearer {self.access_token}"
                
                async with session.post(
                    f"{API_GATEWAY_URL}/api/app/sessions",
                    json={
                        "action": "create",
                        "name": f"Test Session - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        "workflow_id": None
                    },
                    headers=headers
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.session_id = data["id"]
                        self.log(f"✅ Session created: {self.session_id}", Colors.GREEN)
                        return True
                    else:
                        error_text = await resp.text()
                        self.log(f"❌ Session creation failed: {resp.status}", Colors.RED)
                        self.log_debug(f"Response: {error_text}")
                        return False
            except Exception as e:
                self.log(f"❌ Session creation error: {e}", Colors.RED)
                return False
    
    async def send_message(self, message: str):
        """Send a message and stream the response"""
        self.log(f"\n💬 YOU: {message}", Colors.BOLD)
        self.conversation_history.append({"role": "user", "text": message, "timestamp": time.time()})
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        
        timeout = ClientTimeout(total=60, connect=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.post(
                    f"{API_GATEWAY_URL}/api/app/chat/stream",
                    json={
                        "session_id": self.session_id,
                        "user_message": message
                    },
                    headers=headers
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        self.log(f"❌ Error: {resp.status}", Colors.RED)
                        self.log_debug(f"Response: {error_text}")
                        return
                    
                    assistant_messages = []
                    async for line in resp.content:
                        line = line.decode('utf-8').strip()
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                                await self.handle_sse_event(data)
                                
                                # Collect assistant messages
                                if data.get("type") == "message":
                                    msg_text = data.get("data", {}).get("text", "")
                                    if msg_text:
                                        assistant_messages.append(msg_text)
                                        
                            except json.JSONDecodeError as e:
                                self.log_debug(f"Failed to parse SSE: {line}")
                    
                    # Add assistant response to history
                    if assistant_messages:
                        full_response = "\n".join(assistant_messages)
                        self.conversation_history.append({
                            "role": "assistant", 
                            "text": full_response,
                            "timestamp": time.time()
                        })
                        
            except asyncio.TimeoutError:
                self.log("⏱️ Request timed out", Colors.YELLOW)
            except Exception as e:
                self.log(f"❌ Error: {e}", Colors.RED)
                import traceback
                self.log_debug(traceback.format_exc())
    
    async def handle_sse_event(self, data: Dict):
        """Handle SSE event from the stream"""
        event_type = data.get("type")
        event_data = data.get("data", {})
        
        if event_type == "status_change":
            status = event_data
            new_stage = status.get("current_stage")
            if new_stage != self.current_stage:
                self.current_stage = new_stage
                self.log(f"\n🔄 Stage changed to: {new_stage}", Colors.YELLOW)
                
                # Log debug info if available
                if self.debug_mode and "stage_state" in status:
                    state_info = status["stage_state"]
                    self.log_debug(f"Intent: {state_info.get('intent_summary', 'N/A')}")
                    gaps = state_info.get('gaps', [])
                    if gaps:
                        self.log_debug(f"Gaps: {', '.join(gaps)}")
                        
        elif event_type == "message":
            text = event_data.get("text", "")
            if text:
                self.log(f"\n🤖 ASSISTANT: {text}", Colors.GREEN)
                
        elif event_type == "workflow":
            self.log("\n✨ WORKFLOW GENERATED!", Colors.BOLD + Colors.GREEN)
            workflow = event_data.get("workflow", {})
            if isinstance(workflow, str):
                try:
                    workflow = json.loads(workflow)
                except:
                    pass
            
            if isinstance(workflow, dict):
                self.log("📋 Workflow Details:", Colors.CYAN)
                print(json.dumps(workflow, indent=2))
            else:
                self.log(f"Workflow: {workflow}", Colors.CYAN)
                
        elif event_type == "error":
            error_msg = event_data.get("error", "Unknown error")
            self.log(f"\n❌ ERROR: {error_msg}", Colors.RED)
            
        elif event_type == "debug" and self.debug_mode:
            debug_msg = event_data.get("message", "")
            self.log_debug(f"Debug: {debug_msg}")
    
    def print_conversation_history(self):
        """Print the full conversation history"""
        print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"{Colors.HEADER}📜 CONVERSATION HISTORY{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
        
        for entry in self.conversation_history:
            timestamp = datetime.fromtimestamp(entry["timestamp"]).strftime("%H:%M:%S")
            role = entry["role"].upper()
            text = entry["text"]
            
            if role == "USER":
                print(f"\n{Colors.CYAN}[{timestamp}] {Colors.BOLD}YOU:{Colors.ENDC}")
                print(f"  {text}")
            else:
                print(f"\n{Colors.GREEN}[{timestamp}] {Colors.BOLD}ASSISTANT:{Colors.ENDC}")
                # Indent multi-line responses
                for line in text.split('\n'):
                    print(f"  {line}")
    
    async def interactive_mode(self):
        """Run in interactive mode"""
        print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"{Colors.HEADER}🚀 WORKFLOW AGENT INTERACTIVE TESTER{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"\nCommands:")
        print(f"  {Colors.CYAN}/help{Colors.ENDC}     - Show this help")
        print(f"  {Colors.CYAN}/history{Colors.ENDC}  - Show conversation history")
        print(f"  {Colors.CYAN}/clear{Colors.ENDC}    - Start a new session")
        print(f"  {Colors.CYAN}/exit{Colors.ENDC}     - Exit the tester")
        print(f"  {Colors.CYAN}/debug{Colors.ENDC}    - Toggle debug mode")
        print(f"\nDebug mode: {Colors.YELLOW if self.debug_mode else Colors.ENDC}{'ON' if self.debug_mode else 'OFF'}{Colors.ENDC}")
        
        # Authenticate
        if not self.access_token:
            email = input(f"\n{Colors.CYAN}Email (or press Enter for guest): {Colors.ENDC}").strip()
            if email:
                password = input(f"{Colors.CYAN}Password: {Colors.ENDC}").strip()
                if not await self.authenticate(email, password):
                    self.log("Using guest mode", Colors.YELLOW)
        
        # Create initial session
        if not await self.create_session():
            self.log("Failed to create session. Exiting.", Colors.RED)
            return
        
        print(f"\n{Colors.GREEN}Ready! Type your message or a command.{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")
        
        # Interactive loop
        while True:
            try:
                user_input = input(f"{Colors.CYAN}> {Colors.ENDC}").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.startswith("/"):
                    command = user_input.lower()
                    
                    if command == "/exit":
                        self.log("👋 Goodbye!", Colors.GREEN)
                        break
                    elif command == "/history":
                        self.print_conversation_history()
                    elif command == "/clear":
                        if await self.create_session():
                            self.conversation_history = []
                            self.current_stage = None
                            self.log("🆕 Started new session", Colors.GREEN)
                    elif command == "/debug":
                        self.debug_mode = not self.debug_mode
                        self.log(f"Debug mode: {'ON' if self.debug_mode else 'OFF'}", Colors.YELLOW)
                    elif command == "/help":
                        print(f"\nCommands:")
                        print(f"  {Colors.CYAN}/help{Colors.ENDC}     - Show this help")
                        print(f"  {Colors.CYAN}/history{Colors.ENDC}  - Show conversation history")
                        print(f"  {Colors.CYAN}/clear{Colors.ENDC}    - Start a new session")
                        print(f"  {Colors.CYAN}/exit{Colors.ENDC}     - Exit the tester")
                        print(f"  {Colors.CYAN}/debug{Colors.ENDC}    - Toggle debug mode")
                    else:
                        self.log(f"Unknown command: {command}", Colors.YELLOW)
                else:
                    # Send message
                    await self.send_message(user_input)
                    
            except KeyboardInterrupt:
                print(f"\n{Colors.YELLOW}Use /exit to quit{Colors.ENDC}")
            except Exception as e:
                self.log(f"Error: {e}", Colors.RED)
                if self.debug_mode:
                    import traceback
                    traceback.print_exc()


async def run_automated_test():
    """Run an automated test scenario"""
    print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}🤖 AUTOMATED TEST SCENARIO{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
    
    tester = WorkflowTester()
    tester.debug_mode = True
    
    # Skip auth for automated test
    tester.access_token = "mock-token"
    
    if not await tester.create_session():
        return
    
    # Test scenario
    test_messages = [
        "I want to automate something",
        "I need to monitor my website and get alerts when it's down",
        "The website is https://example.com and I want to check every 5 minutes",
        "Send alerts to admin@example.com"
    ]
    
    for msg in test_messages:
        await tester.send_message(msg)
        await asyncio.sleep(3)  # Wait between messages
    
    # Print history
    tester.print_conversation_history()


async def main():
    """Main entry point"""
    if "--test" in sys.argv:
        await run_automated_test()
    else:
        tester = WorkflowTester()
        await tester.interactive_mode()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Interrupted{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.RED}Fatal error: {e}{Colors.ENDC}")
        if "--debug" in sys.argv:
            import traceback
            traceback.print_exc()