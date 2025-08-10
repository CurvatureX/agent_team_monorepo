#!/usr/bin/env python
"""
Interactive chat client for testing /chat/stream endpoint
Allows continuous conversation with the workflow agent
"""

import os
import sys
import json
import time
import httpx
from typing import Optional, Dict
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from backend .env
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
load_dotenv(env_path)


class InteractiveChatClient:
    """Interactive client for chat stream endpoint"""

    def __init__(self):
        """Setup client environment"""
        self.base_url = "http://localhost:8000"
        self.test_email = os.getenv("TEST_USER_EMAIL")
        self.test_password = os.getenv("TEST_USER_PASSWORD")
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
        self.access_token = None
        self.session_id = None

    def log(self, message: str, data: Optional[Dict] = None):
        """Print formatted log message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print(f"\n[{timestamp}] {message}")
        if data:
            print(f"Data: {json.dumps(data, indent=2, ensure_ascii=False)}")

    def print_separator(self, char="-", length=80):
        """Print a separator line"""
        print(char * length)

    def get_access_token(self) -> Optional[str]:
        """Get access token from Supabase Auth"""
        self.log("🔐 Getting access token from Supabase...")
        
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
        
        try:
            response = httpx.post(auth_url, headers=headers, json=data)
            
            if response.status_code == 200:
                auth_data = response.json()
                self.log("✅ Authentication successful")
                return auth_data.get("access_token")
            else:
                self.log(f"❌ Authentication failed: {response.text}")
                return None
        except Exception as e:
            self.log(f"❌ Exception during authentication: {str(e)}")
            return None

    def create_session(self) -> Optional[str]:
        """Create a new session"""
        self.log("📝 Creating new session...")
        
        if not self.access_token:
            self.access_token = self.get_access_token()
            if not self.access_token:
                raise Exception("Failed to get access token")
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        session_data = {"action": "create", "workflow_id": None}
        
        try:
            response = httpx.post(
                f"{self.base_url}/api/v1/app/sessions",
                json=session_data,
                headers=headers
            )
            
            if response.status_code == 200:
                response_data = response.json()
                session_id = response_data["session"]["id"]
                self.log(f"✅ Session created successfully: {session_id}")
                return session_id
            else:
                self.log(f"❌ Failed to create session: {response.text}")
                return None
        except Exception as e:
            self.log(f"❌ Exception during session creation: {str(e)}")
            return None

    def send_chat_message(self, message: str):
        """Send a chat message and stream the response"""
        if not self.session_id:
            self.log("❌ No active session")
            return
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        chat_data = {
            "session_id": self.session_id,
            "user_message": message,
        }
        
        self.log("📤 Sending message...", {"message": message})
        self.print_separator("=")
        
        try:
            # Use streaming client with longer timeout for AI responses
            with httpx.Client(timeout=120.0) as client:
                start_time = time.time()
                with client.stream(
                    "POST",
                    f"{self.base_url}/api/v1/app/chat/stream",
                    json=chat_data,
                    headers=headers
                ) as response:
                    if response.status_code != 200:
                        self.log(f"❌ Stream error: {response.read()}")
                        return
                    
                    # Read SSE events
                    event_count = 0
                    all_events = []
                    
                    for line in response.iter_lines():
                        if line.startswith("data: "):
                            event_count += 1
                            try:
                                # Parse SSE event
                                event_data = json.loads(line[6:])
                                all_events.append(event_data)
                                
                                # Print the full event with formatting
                                event_type = event_data.get("type", "unknown")
                                is_final = event_data.get("is_final", False)
                                
                                print(f"\n📨 Event #{event_count} [type: {event_type}]")
                                print("-" * 60)
                                
                                # Pretty print the event data
                                print(json.dumps(event_data, indent=2, ensure_ascii=False))
                                
                                # Special handling for different event types
                                if event_type == "message":
                                    content = event_data.get("content", "")
                                    print(f"\n💬 Assistant: {content}")
                                elif event_type == "status_change":
                                    status = event_data.get("status_change", {})
                                    print(f"\n🔄 Status Change: {status.get('previous_stage')} → {status.get('current_stage')}")
                                    if status.get('stage_state'):
                                        print("📊 Stage State:")
                                        print(json.dumps(status.get('stage_state'), indent=2, ensure_ascii=False))
                                elif event_type == "workflow":
                                    print(f"\n🔧 Workflow Generated!")
                                    workflow_data = event_data.get("workflow")
                                    if workflow_data:
                                        print(json.dumps(json.loads(workflow_data), indent=2, ensure_ascii=False))
                                elif event_type == "error":
                                    error = event_data.get("error", {})
                                    print(f"\n❌ Error: {error.get('message')}")
                                    print(f"   Code: {error.get('error_code')}")
                                    print(f"   Details: {error.get('details')}")
                                
                                # Check if this is the final event
                                if is_final:
                                    print(f"\n🏁 Conversation completed (final event received)")
                                    break
                                    
                            except json.JSONDecodeError as e:
                                self.log(f"⚠️ Failed to parse SSE event: {line}")
                                self.log(f"   Error: {e}")
                    
                    elapsed_time = time.time() - start_time
                    
                    # Summary
                    self.print_separator("=")
                    print(f"\n📊 Summary:")
                    print(f"   Total events: {event_count}")
                    print(f"   Duration: {elapsed_time:.2f}s")
                    print(f"   Events received: {[e.get('type', 'unknown') for e in all_events]}")
                    
        except httpx.ReadTimeout:
            self.log("⏱️ Stream timeout - the AI might be taking longer than expected")
        except Exception as e:
            self.log(f"❌ Exception during chat stream: {str(e)}")
            import traceback
            self.log(f"Traceback: {traceback.format_exc()}")

    def run_interactive_session(self):
        """Run an interactive chat session"""
        print("\n" + "=" * 80)
        print("🤖 Interactive Workflow Agent Chat Client")
        print("=" * 80)
        print(f"📍 Server: {self.base_url}")
        print(f"👤 User: {self.test_email}")
        print("=" * 80)
        
        # Setup session
        try:
            # Get access token
            self.access_token = self.get_access_token()
            if not self.access_token:
                print("\n❌ Failed to authenticate. Please check your credentials.")
                return
            
            # Create session
            self.session_id = self.create_session()
            if not self.session_id:
                print("\n❌ Failed to create session.")
                return
            
            print("\n✅ Ready to chat! Type 'exit' or 'quit' to end the session.")
            print("💡 Try asking about creating workflows, automations, or integrations.")
            self.print_separator()
            
            # Interactive loop
            while True:
                try:
                    # Get user input
                    user_message = input("\n👤 You: ").strip()
                    
                    # Check for exit commands
                    if user_message.lower() in ['exit', 'quit', 'bye']:
                        print("\n👋 Goodbye!")
                        break
                    
                    # Skip empty messages
                    if not user_message:
                        continue
                    
                    # Send message and stream response
                    self.send_chat_message(user_message)
                    
                except KeyboardInterrupt:
                    print("\n\n⚠️ Interrupted by user")
                    continue
                except Exception as e:
                    print(f"\n❌ Error: {str(e)}")
                    continue
            
        except Exception as e:
            print(f"\n❌ Fatal error: {str(e)}")
            import traceback
            print(traceback.format_exc())


def main():
    """Main entry point"""
    client = InteractiveChatClient()
    
    # Check if required environment variables are set
    if not all([client.test_email, client.test_password, client.supabase_url, client.supabase_anon_key]):
        print("❌ Missing required environment variables. Please check your .env file.")
        print("   Required: TEST_USER_EMAIL, TEST_USER_PASSWORD, SUPABASE_URL, SUPABASE_ANON_KEY")
        return
    
    try:
        client.run_interactive_session()
    except KeyboardInterrupt:
        print("\n\n👋 Session terminated by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")


if __name__ == "__main__":
    main()