#!/usr/bin/env python3
"""
Direct test of workflow agent API to see actual response
"""
import json
import requests
import os

# Load .env file if exists
if os.path.exists('.env'):
    with open('.env', 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

# Configuration
WORKFLOW_AGENT_URL = "http://localhost:8001"

# Create test request
test_request = {
    "session_id": "direct-test-123",
    "user_id": "test-user",
    "access_token": "dummy-token",
    "user_message": "Create a simple workflow",
    "workflow_context": None
}

print("🔍 Making direct request to workflow agent...")
print(f"URL: {WORKFLOW_AGENT_URL}/process-conversation")

try:
    # Make streaming request
    response = requests.post(
        f"{WORKFLOW_AGENT_URL}/process-conversation",
        json=test_request,
        stream=True,
        headers={"Accept": "text/event-stream"}
    )
    
    print(f"\nResponse status: {response.status_code}")
    
    if response.status_code == 200:
        print("\n📥 Streaming response:")
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith("data: "):
                    try:
                        data = json.loads(line_str[6:])
                        print("\n" + "="*60)
                        print(f"Event type: {data.get('response_type')}")
                        
                        # Check status_change for stage_state
                        if data.get('response_type') == 'RESPONSE_TYPE_STATUS_CHANGE':
                            status_change = data.get('status_change', {})
                            stage_state = status_change.get('stage_state', {})
                            
                            print(f"Stage: {status_change.get('current_stage')}")
                            print(f"Stage state fields:")
                            for key in sorted(stage_state.keys()):
                                print(f"  - {key}: {type(stage_state[key]).__name__}")
                            
                            # Check for legacy fields
                            if 'gaps' in stage_state:
                                print("  ❌ WARNING: Found legacy 'gaps' field!")
                            if 'alternatives' in stage_state:
                                print("  ❌ WARNING: Found legacy 'alternatives' field!")
                            if 'identified_gaps' in stage_state:
                                print("  ✅ Found new 'identified_gaps' field")
                            if 'gap_status' in stage_state:
                                print("  ✅ Found new 'gap_status' field")
                                
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e}")
                        print(f"Raw line: {line_str}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\nTest completed!")