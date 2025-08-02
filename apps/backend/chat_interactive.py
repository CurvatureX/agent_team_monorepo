#!/usr/bin/env python3
"""
Robust interactive chat client for API Gateway
Handles streaming responses properly without premature disconnection
"""
import asyncio
import json
import os
import sys
from datetime import datetime
import aiohttp

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


class InteractiveChatClient:
    def __init__(self):
        self.access_token = None
        self.session_id = None
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def print_header(self, text):
        print(f"\n{BOLD}{'='*60}{ENDC}")
        print(f"{BOLD}{CYAN}{text}{ENDC}")
        print(f"{BOLD}{'='*60}{ENDC}")
        
    async def authenticate(self):
        """Authenticate with Supabase"""
        email = os.getenv("TEST_USER_EMAIL")
        password = os.getenv("TEST_USER_PASSWORD")
        
        if not email or not password:
            print(f"{YELLOW}No test credentials found. Using guest mode.{ENDC}")
            return True
            
        print(f"{BLUE}Authenticating...{ENDC}")
        
        auth_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
        
        try:
            async with self.session.post(
                auth_url,
                json={"email": email, "password": password},
                headers={
                    "apikey": SUPABASE_ANON_KEY,
                    "Content-Type": "application/json"
                }
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.access_token = data.get('access_token')
                    print(f"{GREEN}✅ Authentication successful!{ENDC}")
                    return True
                else:
                    error = await resp.json()
                    print(f"{RED}Authentication failed: {error.get('msg', 'Unknown error')}{ENDC}")
                    print(f"{YELLOW}Continuing without authentication...{ENDC}")
                    return True
        except Exception as e:
            print(f"{RED}Authentication error: {e}{ENDC}")
            return False
    
    async def create_session(self):
        """Create a new chat session"""
        print(f"{BLUE}Creating session...{ENDC}")
        
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        
        try:
            async with self.session.post(
                f"{API_GATEWAY_URL}/api/v1/app/sessions",
                json={
                    "action": "create",
                    "name": f"Interactive Chat - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    "workflow_id": None
                },
                headers=headers
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Handle both response formats
                    if 'session' in data and 'id' in data['session']:
                        self.session_id = data['session']['id']
                    elif 'id' in data:
                        self.session_id = data['id']
                    else:
                        print(f"{RED}Unexpected session response format{ENDC}")
                        return False
                    
                    print(f"{GREEN}✅ Session created: {self.session_id}{ENDC}")
                    return True
                else:
                    error = await resp.text()
                    print(f"{RED}Failed to create session: {error}{ENDC}")
                    return False
        except Exception as e:
            print(f"{RED}Session creation error: {e}{ENDC}")
            return False
    
    async def send_message(self, message):
        """Send a message and handle streaming response"""
        print(f"\n{BOLD}{BLUE}YOU: {message}{ENDC}")
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        
        try:
            # Use streaming response
            async with self.session.post(
                f"{API_GATEWAY_URL}/api/v1/app/chat/stream",
                json={
                    "session_id": self.session_id,
                    "user_message": message
                },
                headers=headers
            ) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    print(f"{RED}Error: {error}{ENDC}")
                    return
                
                current_stage = None
                assistant_messages = []
                
                # Read streaming response
                async for line in resp.content:
                    line = line.decode('utf-8').strip()
                    
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
                                    if not assistant_messages:
                                        print(f"\n{BOLD}{GREEN}ASSISTANT:{ENDC}")
                                    print(f"{GREEN}{text}{ENDC}")
                                    assistant_messages.append(text)
                                    
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
                
                # Ensure we've read all data
                await asyncio.sleep(0.1)
                
        except asyncio.TimeoutError:
            print(f"{YELLOW}Request timeout{ENDC}")
        except Exception as e:
            print(f"{RED}Error: {e}{ENDC}")
    
    async def run_interactive(self):
        """Run interactive chat session"""
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
                    if await self.create_session():
                        print(f"{GREEN}New session started!{ENDC}")
                        
                elif user_input.lower() == '/demo':
                    await self.run_demo()
                    
                else:
                    # Send message
                    await self.send_message(user_input)
                    
            except KeyboardInterrupt:
                print(f"\n{YELLOW}Use /exit to quit{ENDC}")
            except EOFError:
                print(f"\n{YELLOW}EOF detected. Exiting...{ENDC}")
                break
    
    async def run_demo(self):
        """Run demo scenario"""
        print(f"\n{BOLD}{CYAN}Running demo scenario...{ENDC}")
        
        messages = [
            "Create a workflow to sync Gmail emails to Slack",
            "New emails with specific labels, send subject and sender to #notifications channel",
            "Use the 'important' and 'urgent' labels"
        ]
        
        for msg in messages:
            await self.send_message(msg)
            await asyncio.sleep(3)
            print()
        
        print(f"{GREEN}Demo completed!{ENDC}")
    
    async def run(self):
        """Main entry point"""
        print(f"{BOLD}{CYAN}{'='*60}{ENDC}")
        print(f"{BOLD}{CYAN}🚀 API GATEWAY INTERACTIVE CHAT CLIENT{ENDC}")
        print(f"{BOLD}{CYAN}{'='*60}{ENDC}")
        
        # Check if API Gateway is running
        print(f"\n{BLUE}Checking services...{ENDC}")
        
        try:
            async with self.session.get(f"{API_GATEWAY_URL}/health") as resp:
                if resp.status == 200 and 'healthy' in await resp.text():
                    print(f"{GREEN}✅ API Gateway is healthy{ENDC}")
                else:
                    raise Exception("Not healthy")
        except:
            print(f"{RED}❌ API Gateway is not running{ENDC}")
            print(f"{YELLOW}Please run: docker compose up{ENDC}")
            return
        
        # Authenticate
        if not await self.authenticate():
            return
        
        # Create session
        if not await self.create_session():
            return
        
        # Run interactive mode
        await self.run_interactive()


async def main():
    """Main function"""
    async with InteractiveChatClient() as client:
        await client.run()


if __name__ == "__main__":
    # Handle command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        # Run demo mode only
        async def demo_only():
            async with InteractiveChatClient() as client:
                print(f"{BOLD}{CYAN}Running demo mode...{ENDC}")
                # Check services
                try:
                    async with client.session.get(f"{API_GATEWAY_URL}/health") as resp:
                        if resp.status != 200:
                            print(f"{RED}API Gateway is not running{ENDC}")
                            return
                except:
                    print(f"{RED}Cannot connect to API Gateway{ENDC}")
                    return
                
                # Authenticate and create session
                if await client.authenticate() and await client.create_session():
                    await client.run_demo()
        
        asyncio.run(demo_only())
    else:
        # Run interactive mode
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print(f"\n{YELLOW}Interrupted{ENDC}")
        except Exception as e:
            print(f"\n{RED}Fatal error: {e}{ENDC}")