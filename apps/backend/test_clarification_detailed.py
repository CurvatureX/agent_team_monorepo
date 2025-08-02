#!/usr/bin/env python3
"""
Detailed test to trace clarification stage issue
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

# Create session
session_data = json.dumps({
    "action": "create",
    "name": f"Detailed Clarification Test",
    "workflow_id": None
})

headers = f"-H 'Content-Type: application/json' -H 'Authorization: Bearer {access_token}'"
cmd = f'''curl -s -X POST "{API_GATEWAY_URL}/api/v1/app/sessions" {headers} -d '{session_data}' '''
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
session_response = json.loads(result.stdout)
session_id = session_response.get('session', {}).get('id') or session_response.get('id')

print(f"Session ID: {session_id}")

# Function to check workflow agent state
def check_workflow_state():
    cmd = f'''curl -s "{API_GATEWAY_URL}/api/v1/app/sessions/{session_id}" \
        -H 'Authorization: Bearer {access_token}' '''
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    try:
        session_data = json.loads(result.stdout)
        workflow_state = session_data.get('session', {}).get('workflow_agent_state', {})
        if workflow_state:
            print(f"\n📊 Workflow State:")
            print(f"  Stage: {workflow_state.get('stage')}")
            clarification_context = workflow_state.get('clarification_context', {})
            pending_questions = clarification_context.get('pending_questions', [])
            print(f"  Pending questions: {len(pending_questions)}")
            if pending_questions:
                for q in pending_questions:
                    print(f"    - {q}")
            conversations = workflow_state.get('conversations', [])
            print(f"  Conversation count: {len(conversations)}")
            if conversations:
                print(f"  Last 3 conversations:")
                for conv in conversations[-3:]:
                    print(f"    [{conv['role']}]: {conv['text'][:60]}...")
    except Exception as e:
        print(f"  Failed to get state: {e}")

# Function to send message
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
                    print(f"  🔄 Stage: {stage}")
                    
                elif event_type == "message":
                    text = data.get("data", {}).get("text", "")
                    if text:
                        print(f"  💬 Assistant: {text[:100]}...")
                        
            except json.JSONDecodeError:
                pass

print("\n🔍 Initial state:")
check_workflow_state()

# Test conversation flow
print("\n\n📝 Starting conversation flow...")

# Message 1
send_message("Create a workflow to sync Gmail emails to Slack", 1)
print("\n🔍 State after message 1:")
check_workflow_state()

time.sleep(3)

# Message 2 - Answer the question
send_message("New emails with specific labels, send subject and sender to #notifications channel", 2)
print("\n🔍 State after message 2:")
check_workflow_state()

time.sleep(3)

# Message 3 - Answer the follow-up question
send_message("Use the 'important' and 'urgent' labels", 3)
print("\n🔍 State after message 3:")
check_workflow_state()

print("\n\n✅ Test completed! Check the logs above to see the state progression.")