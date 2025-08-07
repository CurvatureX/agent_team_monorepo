#!/usr/bin/env python3
"""
Test clarification node output in detail
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

def test_clarification():
    """Test clarification output in detail"""
    
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
    print("\n3. Sending test message: 'I want to sync unread gmail to slack'")
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
        
        # Track clarification output
        clarification_output = None
        assistant_messages = []
        
        # Process SSE stream
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
                    event_type = event.get('type')
                    event_data = event.get('data', {})
                    
                    if event_type == 'message':
                        text = event_data.get('text', '')
                        if text:
                            assistant_messages.append(text)
                            # Try to parse as JSON for clarification output
                            try:
                                # Clean up markdown code blocks
                                clean_text = text.strip()
                                if clean_text.startswith("```json"):
                                    clean_text = clean_text[7:]
                                    if clean_text.endswith("```"):
                                        clean_text = clean_text[:-3]
                                elif clean_text.startswith("```"):
                                    clean_text = clean_text[3:]
                                    if clean_text.endswith("```"):
                                        clean_text = clean_text[:-3]
                                
                                clarification_output = json.loads(clean_text.strip())
                            except json.JSONDecodeError:
                                pass
                        
                except json.JSONDecodeError as e:
                    print(f"JSON parse error: {e}")
                    print(f"Raw: {data_str[:200]}")
        
        print("\n" + "=" * 80)
        print("CLARIFICATION OUTPUT:")
        print("=" * 80)
        
        if clarification_output:
            print(json.dumps(clarification_output, indent=2))
            print("\nAnalysis:")
            print(f"- is_complete: {clarification_output.get('is_complete', 'N/A')}")
            print(f"- intent_summary: {clarification_output.get('intent_summary', 'N/A')[:100]}...")
            print(f"- clarification_question: {clarification_output.get('clarification_question', 'N/A')}")
        else:
            print("Full assistant response:")
            for msg in assistant_messages:
                print(msg)
        
        print("\n" + "=" * 80)
        
        # Check if it's marked as complete
        if clarification_output and clarification_output.get('is_complete'):
            print("✅ SUCCESS: Clarification marked as complete!")
        else:
            print("❌ ISSUE: Clarification not marked as complete, workflow will stop here")
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    test_clarification()