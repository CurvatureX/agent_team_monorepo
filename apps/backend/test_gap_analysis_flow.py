#!/usr/bin/env python3
"""
Test script to verify gap analysis flow with alternatives generation
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
    "name": f"Gap Analysis Flow Test",
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
    output_lines = []
    stages_seen = []
    
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
                    print(f"  📍 Node: {node_name}, Stage: {stage}")
                        
                elif event_type == "message":
                    text = data.get("data", {}).get("text", "")
                    if text:
                        print(f"  💬 Assistant: {text[:150]}...")
                        
            except json.JSONDecodeError:
                pass
    
    return stages_seen

print("\n🔍 Testing gap analysis flow with alternatives...")

# Test 1: Request that should trigger gap analysis
stages1 = send_message("Create a workflow to sync Gmail emails to Slack, but only for emails with specific keywords in the body", 1)
print(f"\n  Stages visited: {stages1}")

time.sleep(3)

# Test 2: Respond to gap analysis alternatives
stages2 = send_message("Let's use the code execution node for custom filtering", 2)
print(f"\n  Stages visited: {stages2}")

# Check final result
print("\n" + "="*60)
print("📊 TEST SUMMARY")
print("="*60)

expected_flow = ["clarification", "gap_analysis", "clarification", "gap_analysis", "workflow_generation"]
actual_flow = stages1 + stages2

print(f"Expected flow includes gap resolution: {expected_flow}")
print(f"Actual flow: {actual_flow}")

if "gap_analysis" in stages1 and "workflow_generation" in stages2:
    print("✅ SUCCESS: Gap analysis flow with alternatives working correctly!")
else:
    print("❌ FAILED: Gap analysis flow not working as expected")

print("\nTest completed!")