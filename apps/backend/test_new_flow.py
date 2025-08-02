#!/usr/bin/env python3
"""
Test script for the new workflow agent flow
Tests the removal of Negotiation node and the new clarification-based flow
"""
import asyncio
import json
import httpx
import os
from datetime import datetime

# Configuration
API_GATEWAY_URL = "http://localhost:8000"
TEST_EMAIL = os.getenv("TEST_USER_EMAIL", "test@example.com")
TEST_PASSWORD = os.getenv("TEST_USER_PASSWORD", "testpassword123")
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://your-project.supabase.co")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "your-anon-key")


class WorkflowTestClient:
    def __init__(self):
        self.access_token = None
        self.session_id = None
        self.timeout = httpx.Timeout(30.0)
        
    async def authenticate(self):
        """Authenticate with Supabase to get JWT token"""
        print("\n🔐 Authenticating...")
        
        # Use Supabase auth endpoint
        auth_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                auth_url,
                json={
                    "email": TEST_EMAIL,
                    "password": TEST_PASSWORD,
                },
                headers={
                    "apikey": SUPABASE_ANON_KEY,
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                print("✅ Authentication successful")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
    
    async def create_session(self, action="create"):
        """Create a new session"""
        print(f"\n📝 Creating session with action: {action}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_GATEWAY_URL}/api/app/sessions",
                json={
                    "action": action,
                    "name": f"Test Flow - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    "workflow_id": None
                },
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 200:
                session = response.json()
                self.session_id = session["id"]
                print(f"✅ Session created: {self.session_id}")
                return True
            else:
                print(f"❌ Session creation failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
    
    async def send_message_and_stream(self, message):
        """Send a message and stream the response"""
        print(f"\n💬 Sending: {message}")
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{API_GATEWAY_URL}/api/app/chat/stream",
                json={
                    "session_id": self.session_id,
                    "user_message": message
                },
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Accept": "text/event-stream",
                    "Content-Type": "application/json"
                }
            ) as response:
                print(f"Response status: {response.status_code}")
                
                current_stage = None
                messages = []
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            event_type = data.get("type")
                            
                            if event_type == "status_change":
                                status_data = data.get("data", {})
                                new_stage = status_data.get("current_stage")
                                if new_stage != current_stage:
                                    current_stage = new_stage
                                    print(f"\n🔄 Stage: {current_stage}")
                                    
                            elif event_type == "message":
                                msg_data = data.get("data", {})
                                msg_text = msg_data.get("text", "")
                                if msg_text:
                                    print(f"\n🤖 Assistant: {msg_text}")
                                    messages.append(msg_text)
                                    
                            elif event_type == "workflow":
                                workflow_data = data.get("data", {})
                                print(f"\n✅ Workflow generated!")
                                print(f"Workflow: {json.dumps(workflow_data.get('workflow', {}), indent=2)}")
                                
                            elif event_type == "error":
                                error_data = data.get("data", {})
                                print(f"\n❌ Error: {error_data}")
                                
                        except json.JSONDecodeError:
                            print(f"Failed to parse: {line}")
                
                return messages


async def test_scenario_1():
    """Test Scenario 1: Basic clarification flow"""
    print("\n" + "="*60)
    print("📋 Scenario 1: Basic Clarification Flow")
    print("="*60)
    
    client = WorkflowTestClient()
    
    # Authenticate
    if not await client.authenticate():
        return
    
    # Create session
    if not await client.create_session():
        return
    
    # First message - vague request
    messages = await client.send_message_and_stream(
        "I want to automate something"
    )
    
    # Should get clarification questions
    print("\n⏸️  Waiting 2 seconds before next message...")
    await asyncio.sleep(2)
    
    # Answer clarification
    messages = await client.send_message_and_stream(
        "I want to monitor my website and get alerts when it's down"
    )
    
    print("\n✅ Scenario 1 completed")


async def test_scenario_2():
    """Test Scenario 2: Gap analysis with alternatives"""
    print("\n" + "="*60)
    print("📋 Scenario 2: Gap Analysis with Alternatives")
    print("="*60)
    
    client = WorkflowTestClient()
    
    # Authenticate
    if not await client.authenticate():
        return
    
    # Create session
    if not await client.create_session():
        return
    
    # First message - request with gaps
    messages = await client.send_message_and_stream(
        "I want to integrate with a custom API that requires OAuth2 authentication"
    )
    
    # Should identify gaps and provide alternatives
    print("\n⏸️  Waiting 2 seconds before selecting alternative...")
    await asyncio.sleep(2)
    
    # Select an alternative
    messages = await client.send_message_and_stream(
        "I'll go with option 1"
    )
    
    print("\n✅ Scenario 2 completed")


async def test_scenario_3():
    """Test Scenario 3: Multiple clarification rounds"""
    print("\n" + "="*60)
    print("📋 Scenario 3: Multiple Clarification Rounds")
    print("="*60)
    
    client = WorkflowTestClient()
    
    # Authenticate
    if not await client.authenticate():
        return
    
    # Create session
    if not await client.create_session():
        return
    
    # First message - very vague
    messages = await client.send_message_and_stream(
        "automate"
    )
    
    print("\n⏸️  Waiting 2 seconds...")
    await asyncio.sleep(2)
    
    # Still vague
    messages = await client.send_message_and_stream(
        "emails"
    )
    
    print("\n⏸️  Waiting 2 seconds...")
    await asyncio.sleep(2)
    
    # More specific
    messages = await client.send_message_and_stream(
        "I want to automatically send welcome emails to new users when they sign up"
    )
    
    print("\n✅ Scenario 3 completed")


async def main():
    """Run all test scenarios"""
    print("\n🚀 Starting Workflow Agent Flow Tests")
    print("Make sure docker-compose is running!")
    
    # Run scenarios
    await test_scenario_1()
    await asyncio.sleep(3)
    
    await test_scenario_2()
    await asyncio.sleep(3)
    
    await test_scenario_3()
    
    print("\n✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())