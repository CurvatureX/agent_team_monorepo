#!/usr/bin/env python3
"""
Interactive End-to-End Test for Chat API
Tests the complete flow: Authentication -> Session Creation -> Chat Streaming
"""

import os
import sys
import json
import time
import requests
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
from colorama import init, Fore, Style

# Initialize colorama for colored output
init(autoreset=True)

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'test_interactive_e2e_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration from .env
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL")
TEST_USER_PASSWORD = os.getenv("TEST_USER_PASSWORD")

# Validate environment variables
if not all([SUPABASE_URL, SUPABASE_ANON_KEY, TEST_USER_EMAIL, TEST_USER_PASSWORD]):
    logger.error("Missing required environment variables!")
    logger.error(f"SUPABASE_URL: {'✓' if SUPABASE_URL else '✗'}")
    logger.error(f"SUPABASE_ANON_KEY: {'✓' if SUPABASE_ANON_KEY else '✗'}")
    logger.error(f"TEST_USER_EMAIL: {'✓' if TEST_USER_EMAIL else '✗'}")
    logger.error(f"TEST_USER_PASSWORD: {'✓' if TEST_USER_PASSWORD else '✗'}")
    sys.exit(1)

class ChatAPITester:
    def __init__(self):
        self.access_token: Optional[str] = None
        self.session_id: Optional[str] = None
        self.session = requests.Session()
        self.conversation_history = []  # Track conversation for debugging
        
    def log_request(self, method: str, url: str, headers: Dict, data: Any = None):
        """Log detailed request information"""
        logger.info(f"\n{Fore.CYAN}{'='*80}")
        logger.info(f"{Fore.YELLOW}REQUEST: {method} {url}")
        logger.info(f"{Fore.GREEN}Headers:")
        for key, value in headers.items():
            if key.lower() == 'authorization' and value:
                # Mask the token for security
                masked_value = f"{value[:20]}...{value[-10:]}" if len(value) > 30 else value
                logger.info(f"  {key}: {masked_value}")
            else:
                logger.info(f"  {key}: {value}")
        if data:
            logger.info(f"{Fore.GREEN}Body:")
            if isinstance(data, dict):
                logger.info(json.dumps(data, indent=2, ensure_ascii=False))
            else:
                logger.info(str(data))
        logger.info(f"{Fore.CYAN}{'='*80}\n")
        
    def log_response(self, response: requests.Response):
        """Log detailed response information"""
        logger.info(f"\n{Fore.MAGENTA}{'='*80}")
        logger.info(f"{Fore.YELLOW}RESPONSE: {response.status_code} {response.reason}")
        logger.info(f"{Fore.GREEN}Headers:")
        for key, value in response.headers.items():
            logger.info(f"  {key}: {value}")
        
        # Handle streaming responses
        if 'text/event-stream' in response.headers.get('content-type', ''):
            logger.info(f"{Fore.GREEN}Body: [Streaming Response - See stream output below]")
        else:
            logger.info(f"{Fore.GREEN}Body:")
            try:
                logger.info(json.dumps(response.json(), indent=2, ensure_ascii=False))
            except:
                logger.info(response.text)
        logger.info(f"{Fore.MAGENTA}{'='*80}\n")
        
    def authenticate(self) -> bool:
        """Authenticate and get access token"""
        logger.info(f"\n{Fore.BLUE}=== STEP 1: Authentication ===")
        
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
            self.log_request("POST", auth_url, headers, data)
            response = self.session.post(auth_url, headers=headers, json=data)
            self.log_response(response)
            
            if response.status_code == 200:
                auth_data = response.json()
                self.access_token = auth_data.get("access_token")
                logger.info(f"{Fore.GREEN}✓ Authentication successful!")
                logger.info(f"Access token obtained: {self.access_token[:20]}...{self.access_token[-10:]}")
                return True
            else:
                logger.error(f"{Fore.RED}✗ Authentication failed!")
                return False
                
        except Exception as e:
            logger.error(f"{Fore.RED}✗ Authentication error: {str(e)}")
            return False
            
    def create_session(self) -> bool:
        """Create a new chat session"""
        logger.info(f"\n{Fore.BLUE}=== STEP 2: Create Session ===")
        
        if not self.access_token:
            logger.error("No access token available!")
            return False
            
        url = f"{API_BASE_URL}/api/v1/app/sessions"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        data = {
            "action": "create"
        }
        
        try:
            self.log_request("POST", url, headers, data)
            response = self.session.post(url, headers=headers, json=data)
            self.log_response(response)
            
            if response.status_code == 200:
                response_data = response.json()
                # The response has a structure: {"session": {...}, "message": "..."}
                session_data = response_data.get("session", {})
                self.session_id = session_data.get("id")
                logger.info(f"{Fore.GREEN}✓ Session created successfully!")
                logger.info(f"Session ID: {self.session_id}")
                logger.info(f"User ID: {session_data.get('user_id')}")
                logger.info(f"Action: {session_data.get('action_type')}")
                logger.info(f"Status: {session_data.get('status')}")
                logger.info(f"Created At: {session_data.get('created_at')}")
                return True
            else:
                logger.error(f"{Fore.RED}✗ Session creation failed!")
                return False
                
        except Exception as e:
            logger.error(f"{Fore.RED}✗ Session creation error: {str(e)}")
            return False
            
    def stream_chat(self, message: str):
        """Send a chat message and stream the response"""
        logger.info(f"\n{Fore.BLUE}=== Chat Stream Request ===")
        logger.info(f"Message: {message}")
        
        if not self.access_token or not self.session_id:
            logger.error("Missing access token or session ID!")
            return
            
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
            self.log_request("POST", url, headers, data)
            
            # Stream the response
            with self.session.post(url, headers=headers, json=data, stream=True) as response:
                # Log initial response info
                logger.info(f"\n{Fore.MAGENTA}{'='*80}")
                logger.info(f"{Fore.YELLOW}STREAMING RESPONSE: {response.status_code}")
                logger.info(f"{Fore.GREEN}Headers:")
                for key, value in response.headers.items():
                    logger.info(f"  {key}: {value}")
                logger.info(f"{Fore.MAGENTA}{'='*80}\n")
                
                if response.status_code != 200:
                    logger.error(f"{Fore.RED}✗ Stream request failed!")
                    logger.error(response.text)
                    return
                    
                # Process SSE stream
                logger.info(f"{Fore.CYAN}=== Stream Events ===")
                full_response = ""
                event_count = 0
                
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        logger.debug(f"Raw line: {line_str}")
                        
                        if line_str.startswith('data: '):
                            event_count += 1
                            data_str = line_str[6:]  # Remove 'data: '
                            
                            try:
                                if data_str == '[DONE]':
                                    logger.info(f"{Fore.GREEN}✓ Stream completed")
                                    break
                                elif data_str.strip() == '':
                                    logger.debug("Empty data, skipping")
                                    continue
                                    
                                data = json.loads(data_str)
                                logger.info(f"\n{Fore.YELLOW}Event #{event_count}:")
                                logger.info(json.dumps(data, indent=2, ensure_ascii=False))
                                
                                # Extract content
                                if data.get('type') == 'content':
                                    content = data.get('content', '')
                                    full_response += content
                                    print(f"{Fore.WHITE}{content}", end='', flush=True)
                                elif data.get('type') == 'workflow_completed':
                                    logger.info(f"\n{Fore.GREEN}✓ Workflow completed!")
                                    workflow_id = data.get('data', {}).get('workflow_id')
                                    if workflow_id:
                                        logger.info(f"Workflow ID: {workflow_id}")
                                elif data.get('type') == 'error':
                                    logger.error(f"\n{Fore.RED}✗ Error: {data.get('error')}")
                                    
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to parse JSON: {e}")
                                logger.error(f"Data string: {data_str}")
                                
                logger.info(f"\n{Fore.CYAN}=== End of Stream ===")
                logger.info(f"Total events: {event_count}")
                logger.info(f"Full response length: {len(full_response)} characters")
                print("\n")  # New line after streaming
                
                # Store in conversation history
                self.conversation_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "user": message,
                    "assistant": full_response,
                    "events": event_count
                })
                
        except Exception as e:
            logger.error(f"{Fore.RED}✗ Stream error: {str(e)}")
            
    def interactive_chat(self):
        """Run interactive chat session"""
        logger.info(f"\n{Fore.BLUE}=== STEP 3: Interactive Chat ===")
        print(f"\n{Fore.GREEN}Chat session started! Type 'exit' to quit.")
        print(f"{Fore.YELLOW}Session ID: {self.session_id}")
        print(f"{Fore.CYAN}Try starting with a workflow request like: '我想创建一个自动化客服工单路由系统'\n")
        
        while True:
            try:
                # Get user input
                message = input(f"{Fore.CYAN}You: {Style.RESET_ALL}")
                
                if message.lower() in ['exit', 'quit', 'bye']:
                    print(f"{Fore.YELLOW}Ending chat session...")
                    break
                    
                if not message.strip():
                    continue
                    
                # Send message and stream response
                print(f"{Fore.GREEN}Assistant: {Style.RESET_ALL}", end='', flush=True)
                self.stream_chat(message)
                
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Chat interrupted by user.")
                break
            except Exception as e:
                logger.error(f"{Fore.RED}Chat error: {str(e)}")
                
    def check_health(self) -> bool:
        """Check API health status"""
        logger.info(f"\n{Fore.BLUE}=== STEP 0: Health Check ===")
        
        health_url = f"{API_BASE_URL}/health"
        try:
            self.log_request("GET", health_url, {})
            response = self.session.get(health_url)
            self.log_response(response)
            
            if response.status_code == 200:
                health_data = response.json()
                logger.info(f"{Fore.GREEN}✓ API is healthy!")
                logger.info(f"Status: {health_data.get('status')}")
                logger.info(f"Version: {health_data.get('version')}")
                return True
            else:
                logger.error(f"{Fore.RED}✗ API health check failed!")
                return False
        except Exception as e:
            logger.error(f"{Fore.RED}✗ Health check error: {str(e)}")
            logger.error(f"Make sure the API is running at {API_BASE_URL}")
            return False
            
    def run(self):
        """Run the complete test flow"""
        logger.info(f"{Fore.BLUE}{'='*80}")
        logger.info(f"{Fore.BLUE}Starting Interactive End-to-End Test")
        logger.info(f"{Fore.BLUE}API Base URL: {API_BASE_URL}")
        logger.info(f"{Fore.BLUE}Test User: {TEST_USER_EMAIL}")
        logger.info(f"{Fore.BLUE}{'='*80}\n")
        
        # Step 0: Health check
        if not self.check_health():
            logger.error("API is not healthy! Exiting...")
            return
        
        # Step 1: Authenticate
        if not self.authenticate():
            logger.error("Authentication failed! Exiting...")
            return
            
        # Step 2: Create session
        if not self.create_session():
            logger.error("Session creation failed! Exiting...")
            return
            
        # Step 3: Interactive chat
        self.interactive_chat()
        
        # Summary
        logger.info(f"\n{Fore.BLUE}{'='*80}")
        logger.info(f"{Fore.BLUE}Test Summary")
        logger.info(f"{Fore.BLUE}{'='*80}")
        logger.info(f"{Fore.GREEN}Session ID: {self.session_id}")
        logger.info(f"{Fore.GREEN}Conversation Turns: {len(self.conversation_history)}")
        logger.info(f"{Fore.GREEN}Total Events Received: {sum(h['events'] for h in self.conversation_history)}")
        
        # Show API endpoints for reference
        logger.info(f"\n{Fore.YELLOW}API Endpoints Reference:")
        logger.info(f"  Health Check: GET {API_BASE_URL}/health")
        logger.info(f"  API Docs: GET {API_BASE_URL}/docs")
        logger.info(f"  Create Session: POST {API_BASE_URL}/api/v1/app/sessions")
        logger.info(f"  Chat Stream: POST {API_BASE_URL}/api/v1/app/chat/stream")
        logger.info(f"  List Sessions: GET {API_BASE_URL}/api/v1/app/sessions")
        logger.info(f"  Get Session: GET {API_BASE_URL}/api/v1/app/sessions/{{session_id}}")
        
        logger.info(f"\n{Fore.BLUE}Log file saved to: test_interactive_e2e_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        logger.info(f"{Fore.BLUE}{'='*80}")
        

def main():
    """Main entry point"""
    tester = ChatAPITester()
    
    try:
        tester.run()
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        sys.exit(1)
        

if __name__ == "__main__":
    main()