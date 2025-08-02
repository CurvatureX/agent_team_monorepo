#!/usr/bin/env python3
"""
Test script to verify the complete 4-node workflow
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
    "name": f"Complete Flow Test",
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
    stages_seen = []
    nodes_seen = []
    
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
                    if stage and stage not in stages_seen:
                        stages_seen.append(stage)
                    if node_name and node_name not in nodes_seen:
                        nodes_seen.append(node_name)
                    print(f"  📍 Node: {node_name}, Stage: {stage}")
                        
                elif event_type == "message":
                    text = data.get("data", {}).get("text", "")
                    if text:
                        print(f"  💬 Assistant: {text[:150]}...")
                        
            except json.JSONDecodeError:
                pass
    
    return stages_seen, nodes_seen

print("\n🔍 Testing complete 4-node flow...")

# Test 1: Request with complete information that should trigger gap analysis
stages1, nodes1 = send_message(
    "I need to create a workflow that monitors my Gmail inbox for emails from specific senders "
    "(john@example.com and mary@example.com), checks if the email subject contains 'urgent' or 'important', "
    "and if it does, automatically forwards the email to my team Slack channel #urgent-emails. "
    "The workflow should run every 5 minutes.", 1
)

time.sleep(3)

# Test 2: Continue the conversation if needed
if "clarification" in stages1[-1:]:
    # If still in clarification, provide more details
    stages2, nodes2 = send_message(
        "Yes, please use Gmail for email monitoring and Slack for notifications. "
        "The workflow should check every 5 minutes and only forward emails that match both conditions: "
        "from the specified senders AND containing urgent/important in subject.", 2
    )
    all_stages = stages1 + stages2
    all_nodes = nodes1 + nodes2
else:
    all_stages = stages1
    all_nodes = nodes1

# Check final result
print("\n" + "="*60)
print("📊 TEST SUMMARY")
print("="*60)

print(f"All stages visited: {all_stages}")
print(f"All nodes visited: {list(set(all_nodes))}")

# Expected flow through the 4 nodes
expected_nodes = ["clarification", "gap_analysis", "workflow_generation", "debug"]
visited_nodes = list(set(all_nodes))

missing_nodes = [node for node in expected_nodes if node not in visited_nodes]
if not missing_nodes:
    print("✅ SUCCESS: All 4 nodes were visited!")
else:
    print(f"❌ FAILED: Missing nodes: {missing_nodes}")

# Check if workflow was generated
if "workflow_generation" in visited_nodes:
    print("✅ Workflow generation completed")
else:
    print("❌ Workflow generation not reached")

print("\nTest completed!")