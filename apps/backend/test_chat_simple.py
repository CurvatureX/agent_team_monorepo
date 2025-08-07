#!/usr/bin/env python3
"""
Simple Chat Test - Test workflow agent integration
"""

import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_BASE_URL = "http://localhost:8000"
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL")
TEST_USER_PASSWORD = os.getenv("TEST_USER_PASSWORD")

def test_chat():
    """Test chat with workflow agent"""
    
    # 1. Authenticate
    print("1. Authenticating...")
    auth_response = requests.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
    )
    
    if auth_response.status_code != 200:
        print(f"Authentication failed: {auth_response.status_code}")
        print(auth_response.text)
        return
    
    access_token = auth_response.json().get("access_token")
    print(f"✓ Got access token: {access_token[:20]}...")
    
    # 2. Create session
    print("\n2. Creating session...")
    session_response = requests.post(
        f"{API_BASE_URL}/api/v1/app/sessions",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json={"action": "create"}
    )
    
    if session_response.status_code != 200:
        print(f"Session creation failed: {session_response.status_code}")
        print(session_response.text)
        return
    
    session_id = session_response.json()["session"]["id"]
    print(f"✓ Created session: {session_id}")
    
    # 3. Send chat message
    print("\n3. Sending chat message: 'I want to sync unread gmail to slack'")
    print("-" * 80)
    
    with requests.post(
        f"{API_BASE_URL}/api/v1/app/chat/stream",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        },
        json={
            "session_id": session_id,
            "user_message": "I want to sync unread gmail to slack"
        },
        stream=True
    ) as response:
        
        if response.status_code != 200:
            print(f"Chat request failed: {response.status_code}")
            print(response.text)
            return
        
        # Process SSE stream
        event_count = 0
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
                    
                    print(f"\n[Event #{event_count}]")
                    print(json.dumps(event, indent=2, ensure_ascii=False))
                    
                    # Check for errors
                    if event.get('type') == 'error':
                        error = event.get('data', {}).get('error', 'Unknown error')
                        print(f"\n❌ Error: {error}")
                        break
                        
                except json.JSONDecodeError as e:
                    print(f"JSON parse error: {e}")
                    print(f"Raw data: {data_str[:100]}")
        
        print(f"\n✓ Received {event_count} events")
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    test_chat()