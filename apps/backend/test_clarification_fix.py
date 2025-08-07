#!/usr/bin/env python3
"""
Test clarification fix - should recognize clear requests immediately
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
    """Test workflow with clear Gmail to Slack request"""
    
    # 1. Authenticate
    print("1. Authenticating...")
    auth_response = requests.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
    )
    
    if auth_response.status_code != 200:
        print(f"Authentication failed: {auth_response.status_code}")
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
        return
    
    session_id = session_response.json()["session"]["id"]
    print(f"✓ Created session: {session_id}")
    
    # 3. Send clear request
    test_message = "I want to sync unread gmail to slack"
    print(f"\n3. Testing with: '{test_message}'")
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
            "user_message": test_message
        },
        stream=True
    ) as response:
        
        if response.status_code != 200:
            print(f"Chat request failed: {response.status_code}")
            return
        
        # Track what happens
        clarification_complete = False
        clarification_question = None
        workflow_received = False
        stages = []
        errors = []
        
        for line in response.iter_lines():
            if line and line.startswith(b'data: '):
                try:
                    data_str = line[6:].decode('utf-8')
                    
                    if data_str == '[DONE]':
                        break
                    
                    if not data_str.strip():
                        continue
                    
                    event = json.loads(data_str)
                    event_type = event.get('type')
                    event_data = event.get('data', {})
                    
                    if event_type == 'message':
                        # Check assistant response
                        text = event_data.get('text', '')
                        if text:
                            try:
                                # Try to parse as JSON to check clarification response
                                if text.startswith('```json'):
                                    json_text = text[7:]
                                    if json_text.endswith('```'):
                                        json_text = json_text[:-3]
                                    clarification_data = json.loads(json_text)
                                    clarification_complete = clarification_data.get('is_complete', False)
                                    clarification_question = clarification_data.get('clarification_question', '')
                                    print(f"[Clarification] is_complete: {clarification_complete}")
                                    if clarification_question:
                                        print(f"[Clarification] question: {clarification_question[:50]}...")
                            except:
                                pass
                    
                    elif event_type == 'status_change':
                        stage_state = event_data.get('stage_state', {})
                        stage = stage_state.get('stage', 'unknown')
                        stages.append(stage)
                        print(f"[Stage] {stage}")
                    
                    elif event_type == 'workflow':
                        workflow_received = True
                        print(f"[WORKFLOW] Received!")
                    
                    elif event_type == 'error':
                        error = event_data.get('message', 'Unknown')
                        errors.append(error)
                        print(f"[ERROR] {error}")
                        
                except json.JSONDecodeError:
                    pass
        
        print("\n" + "=" * 80)
        print("RESULTS:")
        print(f"• Request: '{test_message}'")
        print(f"• Clarification marked complete: {clarification_complete}")
        print(f"• Clarification question asked: {'Yes' if clarification_question else 'No'}")
        print(f"• Stages: {' → '.join(stages)}")
        print(f"• Workflow received: {workflow_received}")
        print(f"• Errors: {errors if errors else 'None'}")
        
        # Check success criteria
        if clarification_complete and not clarification_question:
            print("\n✅ SUCCESS: Request was understood immediately!")
        else:
            print(f"\n❌ FAILED: Unnecessary clarification question asked")
            if clarification_question:
                print(f"   Question: {clarification_question}")

if __name__ == "__main__":
    test_workflow()