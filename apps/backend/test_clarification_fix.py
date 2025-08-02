#!/usr/bin/env python3
"""
Test script to verify clarification stage fix
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

print(f"✅ Authenticated")

# Create session
session_data = json.dumps({
    "action": "create",
    "name": f"Clarification Fix Test",
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
    stages = []
    messages = []
    
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
                    stages.append(stage)
                    print(f"  Stage: {stage}")
                    
                elif event_type == "message":
                    text = data.get("data", {}).get("text", "")
                    if text:
                        messages.append(text)
                        print(f"  Assistant: {text}")
                        
                is_final = data.get("is_final", False)
                if is_final:
                    print(f"  [Response marked as final]")
                    
            except json.JSONDecodeError:
                pass
    
    return stages, messages

# Test messages
print("\nTesting clarification stage progression...")

# Message 1: Initial request
stages1, messages1 = send_message("Create a workflow to sync Gmail emails to Slack", 1)
print(f"  Stages visited: {stages1}")
print(f"  Got {len(messages1)} messages")

time.sleep(5)

# Message 2: Answer the clarification question
stages2, messages2 = send_message("New emails with specific labels, send subject and sender to #notifications channel", 2)
print(f"  Stages visited: {stages2}")
print(f"  Got {len(messages2)} messages")

# Check if we progressed beyond clarification
if stages2 and stages2[-1] != "clarification":
    print(f"\n✅ SUCCESS: Progressed to {stages2[-1]} stage!")
else:
    print(f"\n❌ FAILED: Still stuck in clarification stage")

# Check session state
print(f"\nChecking session state...")
cmd = f'''curl -s "{API_GATEWAY_URL}/api/v1/app/sessions/{session_id}" \
    -H 'Authorization: Bearer {access_token}' '''
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
try:
    session_data = json.loads(result.stdout)
    workflow_state = session_data.get('session', {}).get('workflow_agent_state', {})
    if workflow_state:
        print(f"  Current stage: {workflow_state.get('stage')}")
        clarification_context = workflow_state.get('clarification_context', {})
        pending_questions = clarification_context.get('pending_questions', [])
        print(f"  Pending questions: {len(pending_questions)}")
        conversations = workflow_state.get('conversations', [])
        print(f"  Total conversations: {len(conversations)}")
except Exception as e:
    print(f"  Failed to parse session data: {e}")

print("\nTest completed!")