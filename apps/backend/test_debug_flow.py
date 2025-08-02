#!/usr/bin/env python3
"""
Debug test to see what's happening in the workflow
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
    "name": f"Debug Flow Test",
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
    all_events = []
    
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
                all_events.append(data)
                event_type = data.get("type")
                
                if event_type == "status_change":
                    stage = data.get("data", {}).get("current_stage")
                    node_name = data.get("data", {}).get("node_name")
                    print(f"  📍 Node: {node_name}, Stage: {stage}")
                        
                elif event_type == "message":
                    text = data.get("data", {}).get("text", "")
                    if text:
                        print(f"  💬 Assistant: {text}")
                        
                elif event_type == "debug":
                    debug_data = data.get("data", {})
                    print(f"  🐛 Debug: {json.dumps(debug_data, indent=2)}")
                        
            except json.JSONDecodeError as e:
                print(f"  ⚠️ JSON error: {e}")
                print(f"  Raw line: {line}")
    
    return all_events

print("\n🔍 Testing with simple request...")

# Test 1: Very simple request that should complete clarification
events = send_message("Create a workflow that sends me an email reminder every day at 9 AM", 1)

# Analyze events
print("\n" + "="*60)
print("📊 EVENT ANALYSIS")
print("="*60)

stages_seen = []
nodes_seen = []
for event in events:
    if event.get("type") == "status_change":
        stage = event.get("data", {}).get("current_stage")
        node = event.get("data", {}).get("node_name")
        if stage and stage not in stages_seen:
            stages_seen.append(stage)
        if node and node not in nodes_seen:
            nodes_seen.append(node)

print(f"Stages: {stages_seen}")
print(f"Nodes: {nodes_seen}")

# Check last stage
if events:
    last_status = None
    for event in reversed(events):
        if event.get("type") == "status_change":
            last_status = event.get("data", {})
            break
    
    if last_status:
        print(f"\nLast status:")
        print(f"  Stage: {last_status.get('current_stage')}")
        print(f"  Node: {last_status.get('node_name')}")

print("\nTest completed!")