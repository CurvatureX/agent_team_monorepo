#!/usr/bin/env python
"""
Debug-focused interactive chat client for /chat/stream endpoint
Prints all SSE events in detail for debugging
"""

import os
import sys
import json
import time
import httpx
from datetime import datetime
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
load_dotenv(env_path)


def colored_print(text: str, color: str = "default"):
    """Print colored text for better visibility"""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "default": "\033[0m"
    }
    print(f"{colors.get(color, '')}{text}{colors['default']}")


class ChatDebugClient:
    """Debug client for chat stream endpoint"""

    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.test_email = os.getenv("TEST_USER_EMAIL")
        self.test_password = os.getenv("TEST_USER_PASSWORD")
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
        self.access_token = None
        self.session_id = None

    def get_access_token(self) -> Optional[str]:
        """Get access token from Supabase Auth"""
        print("\n🔐 Authenticating...")
        
        auth_url = f"{self.supabase_url}/auth/v1/token?grant_type=password"
        headers = {
            "apikey": self.supabase_anon_key,
            "Content-Type": "application/json",
        }
        data = {
            "email": self.test_email,
            "password": self.test_password,
            "gotrue_meta_security": {},
        }
        
        response = httpx.post(auth_url, headers=headers, json=data, timeout=10.0)
        if response.status_code == 200:
            auth_data = response.json()
            colored_print("✅ Authentication successful", "green")
            return auth_data.get("access_token")
        else:
            colored_print(f"❌ Authentication failed: {response.text}", "red")
            return None

    def create_session(self) -> Optional[str]:
        """Create a new session"""
        print("\n📝 Creating session...")
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        session_data = {"action": "create", "workflow_id": None}
        
        response = httpx.post(
            f"{self.base_url}/api/v1/app/sessions",
            json=session_data,
            headers=headers,
            timeout=30.0  # Increased timeout for session creation
        )
        
        if response.status_code == 200:
            response_data = response.json()
            session_id = response_data["session"]["id"]
            colored_print(f"✅ Session created: {session_id}", "green")
            return session_id
        else:
            colored_print(f"❌ Failed to create session: {response.text}", "red")
            return None

    def stream_chat(self, message: str):
        """Send message and stream response with detailed output"""
        headers = {"Authorization": f"Bearer {self.access_token}"}
        chat_data = {
            "session_id": self.session_id,
            "user_message": message,
        }
        
        colored_print(f"\n👤 USER: {message}", "cyan")
        print("=" * 80)
        
        with httpx.Client(timeout=120.0) as client:
            start_time = time.time()
            event_count = 0
            
            with client.stream(
                "POST",
                f"{self.base_url}/api/v1/app/chat/stream",
                json=chat_data,
                headers=headers
            ) as response:
                if response.status_code != 200:
                    colored_print(f"❌ Error: {response.read()}", "red")
                    return
                
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        event_count += 1
                        try:
                            event_data = json.loads(line[6:])
                            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                            
                            # Print event header
                            event_type = event_data.get("type", "unknown")
                            colored_print(f"\n[{timestamp}] Event #{event_count} - Type: {event_type}", "yellow")
                            
                            # Print raw event data
                            print("RAW EVENT DATA:")
                            print(json.dumps(event_data, indent=2, ensure_ascii=False))
                            
                            # Parse specific event types
                            if event_type == "status_change":
                                data = event_data.get("data", {})
                                colored_print(f"\n🔄 STATE TRANSITION: {data.get('previous_stage')} → {data.get('current_stage')}", "magenta")
                                colored_print(f"📍 Node: {data.get('node_name')}", "magenta")
                                
                                # Print full stage_state
                                if data.get('stage_state'):
                                    colored_print("\n📊 FULL STATE:", "blue")
                                    print(json.dumps(data.get('stage_state'), indent=2, ensure_ascii=False))
                            
                            elif event_type == "message":
                                data = event_data.get("data", {})
                                colored_print(f"\n💬 ASSISTANT: {data.get('text')}", "green")
                            
                            elif event_type == "workflow":
                                colored_print("\n🔧 WORKFLOW GENERATED:", "blue")
                                data = event_data.get("data", {})
                                print(json.dumps(data, indent=2, ensure_ascii=False))
                            
                            elif event_type == "error":
                                error = event_data.get("error", {})
                                colored_print(f"\n❌ ERROR: {error.get('message')}", "red")
                                print(f"Code: {error.get('error_code')}")
                                print(f"Details: {error.get('details')}")
                            
                            # Check for final event
                            if event_data.get("is_final"):
                                colored_print(f"\n🏁 STREAM COMPLETED (is_final=true)", "green")
                                break
                                
                        except json.JSONDecodeError as e:
                            colored_print(f"⚠️ JSON Parse Error: {e}", "red")
                            print(f"Raw line: {line}")
                
                elapsed = time.time() - start_time
                print("\n" + "=" * 80)
                colored_print(f"📊 Total events: {event_count} | Duration: {elapsed:.2f}s", "cyan")

    def run(self):
        """Run interactive debug session"""
        colored_print("\n🤖 WORKFLOW AGENT DEBUG CLIENT", "cyan")
        print("=" * 80)
        
        # Setup
        self.access_token = self.get_access_token()
        if not self.access_token:
            return
        
        self.session_id = self.create_session()
        if not self.session_id:
            return
        
        colored_print("\n✅ Ready! Type your messages below (or 'exit' to quit)", "green")
        print("=" * 80)
        
        # Interactive loop
        while True:
            try:
                message = input("\n👤 > ").strip()
                
                if message.lower() in ['exit', 'quit']:
                    colored_print("\n👋 Goodbye!", "cyan")
                    break
                
                if message:
                    self.stream_chat(message)
                    
            except KeyboardInterrupt:
                colored_print("\n⚠️ Interrupted", "yellow")
                continue
            except Exception as e:
                colored_print(f"\n❌ Error: {e}", "red")


if __name__ == "__main__":
    # Check environment
    required_vars = ["TEST_USER_EMAIL", "TEST_USER_PASSWORD", "SUPABASE_URL", "SUPABASE_ANON_KEY"]
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        colored_print(f"❌ Missing environment variables: {', '.join(missing)}", "red")
        sys.exit(1)
    
    # Run client
    client = ChatDebugClient()
    client.run()