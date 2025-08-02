#!/usr/bin/env python3
"""
Full integration test for 4-node workflow
"""
import json
import os
import subprocess
import time

# Load .env file if exists
if os.path.exists('.env'):
    with open('.env', 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

# Configuration
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8000")
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://mkrczzgjeduruwxpanbj.supabase.co")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# Authenticate
email = os.getenv("TEST_USER_EMAIL")
password = os.getenv("TEST_USER_PASSWORD")

auth_data = json.dumps({"email": email, "password": password})
cmd = f'''curl -s -X POST "{SUPABASE_URL}/auth/v1/token?grant_type=password" \
    -H "apikey: {SUPABASE_ANON_KEY}" \
    -H "Content-Type: application/json" \
    -d '{auth_data}' '''

result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
auth_response = json.loads(result.stdout)
access_token = auth_response.get('access_token')

print("✅ Authenticated")

# Create session
session_data = json.dumps({
    "action": "create",
    "name": f"Full Integration Test",
    "workflow_id": None
})

headers = f"-H 'Content-Type: application/json' -H 'Authorization: Bearer {access_token}'"
cmd = f'''curl -s -X POST "{API_GATEWAY_URL}/api/v1/app/sessions" {headers} -d '{session_data}' '''
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
session_response = json.loads(result.stdout)
session_id = session_response.get('session', {}).get('id') or session_response.get('id')

print(f"✅ Session ID: {session_id}")

# Function to send message and check state
def send_and_check_state(message, seq):
    print(f"\n{'='*60}")
    print(f"Message {seq}: {message}")
    print(f"{'='*60}")
    
    message_data = json.dumps({
        "session_id": session_id,
        "user_message": message
    })
    
    headers = f"-H 'Content-Type: application/json' -H 'Accept: text/event-stream' -H 'Authorization: Bearer {access_token}'"
    
    cmd = f'''curl -s -X POST "{API_GATEWAY_URL}/api/v1/app/chat/stream" \
        {headers} \
        -d '{message_data}' \
        --no-buffer \
        --max-time 30'''
    
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=0)
    
    # Collect all output
    stage_states = []
    
    while True:
        line = process.stdout.readline()
        if not line:
            if process.poll() is not None:
                break
            time.sleep(0.1)
            continue
            
        if line.startswith("data: "):
            try:
                data = json.loads(line[6:])
                event_type = data.get("type")
                
                if event_type == "status_change":
                    stage = data.get("data", {}).get("current_stage")
                    node_name = data.get("data", {}).get("node_name")
                    stage_state = data.get("data", {}).get("stage_state", {})
                    
                    print(f"\n📍 Node: {node_name}, Stage: {stage}")
                    
                    # Check for new fields
                    if "identified_gaps" in stage_state:
                        print(f"   ✅ identified_gaps field present: {stage_state['identified_gaps']}")
                    if "gap_status" in stage_state:
                        print(f"   ✅ gap_status field present: {stage_state['gap_status']}")
                    
                    # Check that old fields are NOT present
                    if "gaps" in stage_state:
                        print(f"   ❌ ERROR: Legacy 'gaps' field still present!")
                    if "alternatives" in stage_state:
                        print(f"   ❌ ERROR: Legacy 'alternatives' field still present!")
                        
                    stage_states.append(stage_state)
                        
                elif event_type == "message":
                    text = data.get("data", {}).get("text", "")
                    if text:
                        print(f"\n💬 Assistant: {text[:100]}...")
                        
            except json.JSONDecodeError:
                pass
    
    return stage_states

print("\n🔍 Testing full integration with new field structure...")

# Test 1: Simple request
states1 = send_and_check_state("Create a simple daily email reminder workflow", 1)

print("\n" + "="*60)
print("📊 INTEGRATION TEST SUMMARY")
print("="*60)

if states1:
    print(f"\nReceived {len(states1)} state updates")
    
    # Check last state
    last_state = states1[-1]
    print(f"\nLast state analysis:")
    print(f"  Stage: {last_state.get('stage')}")
    print(f"  Has identified_gaps: {'identified_gaps' in last_state}")
    print(f"  Has gap_status: {'gap_status' in last_state}")
    print(f"  Has legacy gaps: {'gaps' in last_state}")
    print(f"  Has legacy alternatives: {'alternatives' in last_state}")
    
    # Success criteria
    has_new_fields = 'identified_gaps' in last_state or 'gap_status' in last_state
    has_legacy_fields = 'gaps' in last_state or 'alternatives' in last_state
    
    if has_new_fields and not has_legacy_fields:
        print("\n✅ SUCCESS: New field structure correctly implemented!")
    else:
        print("\n❌ FAILED: Field structure issues detected")
else:
    print("\n❌ No state updates received")

print("\nTest completed!")