#!/usr/bin/env python3
"""
Simple test to verify the basic flow after alternative node removal
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
    "name": f"Simple Flow Test",
    "workflow_id": None
})

headers = f"-H 'Content-Type: application/json' -H 'Authorization: Bearer {access_token}'"
cmd = f'''curl -s -X POST "{API_GATEWAY_URL}/api/v1/app/sessions" {headers} -d '{session_data}' '''
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
session_response = json.loads(result.stdout)
session_id = session_response.get('session', {}).get('id') or session_response.get('id')

print(f"✅ Session ID: {session_id}")

# Function to send message and capture response
def send_message(message):
    print(f"\n📤 Sending: {message}")
    
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
    stages = []
    nodes = []
    messages = []
    
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
                    node = data.get("data", {}).get("node_name")
                    if stage and stage not in stages:
                        stages.append(stage)
                    if node and node not in nodes:
                        nodes.append(node)
                        
                elif event_type == "message":
                    text = data.get("data", {}).get("text", "")
                    if text:
                        messages.append(text)
                        
            except json.JSONDecodeError:
                pass
    
    return stages, nodes, messages

print("\n🔍 Testing basic flow...")

# Test 1: Simple request
stages1, nodes1, messages1 = send_message("Create a simple reminder workflow")
print(f"  Stages: {stages1}")
print(f"  Nodes: {nodes1}")
if messages1:
    print(f"  Message: {messages1[0][:100]}...")

time.sleep(3)

# Test 2: Answer clarification
stages2, nodes2, messages2 = send_message("Send me a daily reminder at 9am to check emails")
print(f"\n  Stages: {stages2}")
print(f"  Nodes: {nodes2}")
if messages2:
    print(f"  Message: {messages2[0][:100]}...")

# Verify no alternative_generation node
all_nodes = nodes1 + nodes2
if "alternative_generation" in all_nodes:
    print("\n❌ FAILED: alternative_generation node still exists!")
else:
    print("\n✅ SUCCESS: alternative_generation node successfully removed!")

print(f"\nAll nodes visited: {list(set(all_nodes))}")
print("\nTest completed!")