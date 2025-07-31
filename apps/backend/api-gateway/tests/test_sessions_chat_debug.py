"""
Integration test for /sessions and /chat/stream endpoints with detailed logging
Used for debugging and functional verification
"""

import os
import sys
import json
import time
import httpx
import pytest
from typing import Optional, Dict
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from backend .env
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
load_dotenv(env_path)

# Skip tests in CI environment
if os.getenv("CI") == "true":
    pytest.skip("Skipping integration tests in CI environment", allow_module_level=True)


class TestSessionsChatDebug:
    """Integration tests for sessions and chat endpoints with detailed logging"""

    def __init__(self):
        """Setup test environment"""
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

        self.log("📤 Sending auth request", {"url": auth_url, "email": self.test_email})
        
        try:
            response = httpx.post(auth_url, headers=headers, json=data)
            self.log(f"📥 Auth response status: {response.status_code}")
            
            if response.status_code == 200:
                auth_data = response.json()
                self.log("✅ Authentication successful", {
                    "access_token": auth_data.get("access_token", "")[:20] + "...",
                    "token_type": auth_data.get("token_type"),
                    "expires_in": auth_data.get("expires_in")
                })
                return auth_data.get("access_token")
            else:
                self.log(f"❌ Authentication failed: {response.text}")
                return None
        except Exception as e:
            self.log(f"❌ Exception during authentication: {str(e)}")
            return None

    def test_health_check(self):
        """Test health check endpoint"""
        self.log("🏥 Testing health check endpoint...")
        
        try:
            response = httpx.get(f"{self.base_url}/api/v1/public/health")
            self.log(f"📥 Health check response status: {response.status_code}")
            self.log("📥 Health check response", response.json())
            
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"
            self.log("✅ Health check passed")
        except Exception as e:
            self.log(f"❌ Health check failed: {str(e)}")
            raise

    def test_create_session(self):
        """Test session creation"""
        self.log("📝 Testing session creation...")
        
        if not self.access_token:
            self.access_token = self.get_access_token()
            if not self.access_token:
                raise Exception("Failed to get access token")
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        session_data = {"action": "create", "workflow_id": None}
        
        self.log("📤 Creating session", session_data)
        
        try:
            response = httpx.post(
                f"{self.base_url}/api/v1/app/sessions",
                json=session_data,
                headers=headers
            )
            self.log(f"📥 Create session response status: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                self.log("📥 Session created", response_data)
                self.session_id = response_data["session"]["id"]
                self.log(f"✅ Session created successfully: {self.session_id}")
            else:
                self.log(f"❌ Failed to create session: {response.text}")
                raise Exception(f"Failed to create session: {response.status_code}")
        except Exception as e:
            self.log(f"❌ Exception during session creation: {str(e)}")
            raise

    def test_get_session(self):
        """Test getting session by ID"""
        self.log(f"🔍 Testing get session by ID: {self.session_id}")
        
        if not self.session_id:
            self.log("⚠️ No session ID available, skipping test")
            return
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        try:
            response = httpx.get(
                f"{self.base_url}/api/v1/app/sessions/{self.session_id}",
                headers=headers
            )
            self.log(f"📥 Get session response status: {response.status_code}")
            
            if response.status_code == 200:
                self.log("📥 Session retrieved", response.json())
                self.log("✅ Get session successful")
            else:
                self.log(f"❌ Failed to get session: {response.text}")
        except Exception as e:
            self.log(f"❌ Exception during get session: {str(e)}")

    def test_list_sessions(self):
        """Test listing user sessions"""
        self.log("📋 Testing list sessions...")
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        try:
            response = httpx.get(
                f"{self.base_url}/api/v1/app/sessions",
                headers=headers
            )
            self.log(f"📥 List sessions response status: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                self.log(f"📥 Sessions list ({response_data['total_count']} total)", {
                    "page": response_data["page"],
                    "page_size": response_data["page_size"],
                    "sessions_count": len(response_data["sessions"])
                })
                # Show first 3 sessions
                for i, session in enumerate(response_data["sessions"][:3]):
                    self.log(f"  Session {i+1}", {
                        "id": session["id"],
                        "action_type": session.get("action_type"),
                        "created_at": session.get("created_at")
                    })
                self.log("✅ List sessions successful")
            else:
                self.log(f"❌ Failed to list sessions: {response.text}")
        except Exception as e:
            self.log(f"❌ Exception during list sessions: {str(e)}")

    def test_chat_stream(self):
        """Test chat stream endpoint"""
        self.log(f"💬 Testing chat stream for session: {self.session_id}")
        
        if not self.session_id:
            self.log("⚠️ No session ID available, skipping test")
            return
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        chat_data = {
            "session_id": self.session_id,
            "user_message": "Hello! Can you help me create a simple workflow?",
        }
        
        self.log("📤 Sending chat message", chat_data)
        
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
                    self.log(f"📥 Stream response status: {response.status_code}")
                    self.log(f"📥 Stream headers: {dict(response.headers)}")
                    
                    if response.status_code != 200:
                        self.log(f"❌ Stream error: {response.read()}")
                        return
                    
                    # Read SSE events until is_final=true
                    event_count = 0
                    message_count = 0
                    status_change_count = 0
                    workflow_count = 0
                    is_final_received = False
                    all_messages = []
                    
                    for line in response.iter_lines():
                        if line.startswith("data: "):
                            event_count += 1
                            try:
                                # Parse SSE event
                                event_data = json.loads(line[6:])
                                event_type = event_data.get("type")
                                is_final = event_data.get("is_final", False)
                                
                                # Log the full event
                                self.log(f"📨 SSE Event #{event_count} (type: {event_type}, event_data: {event_data})")
                                
                                # Check if this is the final event
                                if is_final:
                                    is_final_received = True
                                    self.log(f"🏁 Received final event (type: {event_type})")
                                    break
                                    
                            except json.JSONDecodeError as e:
                                self.log(f"⚠️ Failed to parse SSE event: {line}")
                                self.log(f"   Error: {e}")
                    
                    elapsed_time = time.time() - start_time
                    
                    # Summary
                    self.log("\n📊 Stream Summary:")
                    self.log(f"   Total events: {event_count}")
                    self.log(f"   Final received: {is_final_received}")
                    self.log(f"   Duration: {elapsed_time:.2f}s")
                    
                    if all_messages:
                        self.log("\n💬 All Messages Combined:")
                        full_conversation = "\n".join(all_messages)
                        self.log(full_conversation)
                    
                    if is_final_received:
                        self.log("\n✅ Chat stream completed successfully with is_final=true")
                    else:
                        self.log("\n⚠️ Chat stream ended without receiving is_final=true")
                    
        except httpx.ReadTimeout:
            self.log("⏱️ Stream timeout - increase timeout if waiting for AI response")
        except Exception as e:
            self.log(f"❌ Exception during chat stream: {str(e)}")
            import traceback
            self.log(f"Traceback: {traceback.format_exc()}")

    def test_chat_history(self):
        """Test getting chat history"""
        self.log(f"📜 Testing chat history for session: {self.session_id}")
        
        if not self.session_id:
            self.log("⚠️ No session ID available, skipping test")
            return
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        try:
            response = httpx.get(
                f"{self.base_url}/api/v1/app/chat/{self.session_id}/history",
                headers=headers
            )
            self.log(f"📥 Chat history response status: {response.status_code}")
            
            if response.status_code == 200:
                history_data = response.json()
                self.log(f"📥 Chat history ({len(history_data['messages'])} messages)", {
                    "session_id": history_data["session_id"],
                    "total_count": history_data["total_count"],
                    "page": history_data["page"]
                })
                # Show messages
                for i, msg in enumerate(history_data["messages"]):
                    self.log(f"  Message {i+1}", {
                        "type": msg["message_type"],
                        "content": msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"],
                        "created_at": msg["created_at"]
                    })
                self.log("✅ Chat history retrieved successfully")
            else:
                self.log(f"❌ Failed to get chat history: {response.text}")
        except Exception as e:
            self.log(f"❌ Exception during get chat history: {str(e)}")

    def run_all_tests(self):
        """Run all tests in sequence"""
        self.log("🚀 Starting integration tests for sessions and chat endpoints")
        self.log(f"📍 Base URL: {self.base_url}")
        self.log(f"👤 Test user: {self.test_email}")
        
        try:
            # Run tests in order
            # self.test_health_check()
            self.test_create_session()
            self.test_get_session()
            # self.test_list_sessions()
            self.test_chat_stream()
            # self.test_chat_history()
            
            self.log("\n✅ All tests completed successfully!")
        except Exception as e:
            self.log(f"\n❌ Test suite failed: {str(e)}")
            raise


if __name__ == "__main__":
    # Run the test suite
    test_suite = TestSessionsChatDebug()
    test_suite.run_all_tests()