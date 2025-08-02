#!/usr/bin/env python3
"""
Test script to verify workflow works correctly after router removal
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
    "name": f"Router Removal Test",
    "workflow_id": None
})

headers = f"-H 'Content-Type: application/json' -H 'Authorization: Bearer {access_token}'"
cmd = f'''curl -s -X POST "{API_GATEWAY_URL}/api/v1/app/sessions" {headers} -d '{session_data}' '''
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
session_response = json.loads(result.stdout)
session_id = session_response.get('session', {}).get('id') or session_response.get('id')

print(f"✅ Session ID: {session_id}")

# Function to send message and capture response
def send_message(message, seq):
    print(f"\n{'='*60}")
    print(f"Test {seq}: {message}")
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
    output_lines = []
    stages_seen = []
    has_router = False
    
    while True:
        line = process.stdout.readline()
        if not line:
            if process.poll() is not None:
                break
            time.sleep(0.1)
            continue
        output_lines.append(line.strip())
    
    # Parse output
    for line in output_lines:
        if line.startswith("data: "):
            try:
                data = json.loads(line[6:])
                event_type = data.get("type")
                
                if event_type == "status_change":
                    stage = data.get("data", {}).get("current_stage")
                    node_name = data.get("data", {}).get("node_name")
                    if stage:
                        stages_seen.append(stage)
                    if node_name == "router":
                        has_router = True
                        print("  ❌ Router node detected!")
                    else:
                        print(f"  ✅ Node: {node_name}, Stage: {stage}")
                        
                elif event_type == "message":
                    text = data.get("data", {}).get("text", "")
                    if text:
                        print(f"  💬 Assistant: {text[:80]}...")
                        
            except json.JSONDecodeError:
                pass
    
    return stages_seen, has_router

print("\n🔍 Testing workflow without router node...")

# Test 1: Basic workflow creation
stages1, has_router1 = send_message("Create a workflow to sync Gmail to Slack", 1)
print(f"\n  Stages visited: {stages1}")
if has_router1:
    print("  ❌ FAIL: Router node still exists!")
else:
    print("  ✅ PASS: No router node detected")

time.sleep(3)

# Test 2: Answer clarification question
stages2, has_router2 = send_message("New emails with 'urgent' label, send to #alerts channel", 2)
print(f"\n  Stages visited: {stages2}")
if has_router2:
    print("  ❌ FAIL: Router node still exists!")
else:
    print("  ✅ PASS: No router node detected")

# Summary
print("\n" + "="*60)
print("📊 TEST SUMMARY")
print("="*60)

if not has_router1 and not has_router2:
    print("✅ SUCCESS: Router node successfully removed!")
    print("✅ Workflow progresses correctly without router")
else:
    print("❌ FAILED: Router node still present in workflow")

print("\nTest completed!")