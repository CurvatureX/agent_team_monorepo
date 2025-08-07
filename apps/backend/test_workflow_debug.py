#!/usr/bin/env python3
"""
Debug test for workflow agent - identify the 'debug' error
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

def test_workflow():
    """Test workflow agent with detailed error tracking"""
    
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
    print(f"✓ Got access token")
    
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
    print("\n3. Sending chat message: 'Create a simple hello world workflow'")
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
            "user_message": "Create a simple hello world workflow that prints hello"
        },
        stream=True
    ) as response:
        
        if response.status_code != 200:
            print(f"Chat request failed: {response.status_code}")
            print(response.text)
            return
        
        # Track workflow stages
        stages_seen = []
        errors_seen = []
        
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
                    
                    # Track important events
                    event_type = event.get('type')
                    event_data = event.get('data', {})
                    
                    if event_type == 'status_change':
                        prev = event_data.get('previous_stage', 'unknown')
                        curr = event_data.get('current_stage', 'unknown')
                        stages_seen.append(f"{prev} → {curr}")
                        print(f"[Stage] {prev} → {curr}")
                    
                    elif event_type == 'error':
                        error = event_data.get('error', event_data.get('message', 'Unknown'))
                        errors_seen.append(error)
                        print(f"[Error] {error}")
                    
                    elif event_type == 'message':
                        # Print message content
                        text = event_data.get('text', '')
                        if text:
                            print(f"[Assistant] {text[:100]}...")
                        
                except json.JSONDecodeError as e:
                    print(f"JSON parse error: {e}")
                    print(f"Raw: {data_str[:200]}")
        
        print("\n" + "=" * 80)
        print(f"Events received: {event_count}")
        print(f"Stages seen: {' → '.join(stages_seen) if stages_seen else 'None'}")
        print(f"Errors: {errors_seen if errors_seen else 'None'}")
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    test_workflow()