#!/usr/bin/env python3
"""
Test with complete information to force progression through all nodes
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
    "name": f"Force Complete Flow Test",
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
    print(f"Message {seq}:")
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
        --max-time 60'''
    
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=0)
    
    # Collect all output
    stages_seen = []
    nodes_seen = []
    last_message = ""
    
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
                    print(f"  📍 {node_name} → {stage}")
                        
                elif event_type == "message":
                    text = data.get("data", {}).get("text", "")
                    if text:
                        last_message = text
                        # Only print first 100 chars to avoid clutter
                        preview = text[:100] + "..." if len(text) > 100 else text
                        print(f"  💬 {preview}")
                        
            except json.JSONDecodeError:
                pass
    
    return stages_seen, nodes_seen, last_message

print("\n🔍 Testing with comprehensive request to force complete flow...")

# Provide ALL required information according to the clarification prompt requirements
comprehensive_request = """I need to create an email reminder workflow with these details:

OBJECTIVE: Automated daily email reminder system for personal task management

TRIGGER: Time-based trigger at 9:00 AM every day

WORKFLOW STEPS:
1. At 9:00 AM daily, the workflow automatically starts
2. It retrieves my task list from a Google Sheets document
3. It formats the tasks into a nice HTML email template
4. It sends the email to my personal email address (john@example.com)
5. It logs the successful send to a tracking spreadsheet

CORE FEATURES:
- Daily automated execution without manual intervention
- Integration with Google Sheets for dynamic task list
- Professional HTML email formatting
- Delivery confirmation tracking

SYSTEM INTEGRATIONS:
- Google Sheets API for reading task data
- Gmail API for sending emails
- Logging system for tracking sent reminders"""

stages1, nodes1, msg1 = send_message(comprehensive_request, 1)

# Wait a bit for processing
time.sleep(3)

# If still in clarification, provide more info
all_stages = stages1
all_nodes = nodes1

if stages1 and stages1[-1] == "clarification":
    print("\n📝 Providing additional clarification...")
    additional_info = """Additional details:

- The Google Sheets has columns: Task Name, Priority, Due Date
- Only include tasks with due dates within the next 7 days
- High priority tasks should be highlighted in red in the email
- The email subject should be "Daily Task Reminder - [Today's Date]"
- If there are no tasks, still send an email saying "No tasks for today"
- Use my Gmail account with OAuth2 authentication
- The workflow should handle errors gracefully and retry up to 3 times"""
    
    stages2, nodes2, msg2 = send_message(additional_info, 2)
    all_stages.extend(stages2)
    all_nodes.extend(nodes2)

# Check final result
print("\n" + "="*60)
print("📊 FINAL RESULTS")
print("="*60)

unique_stages = list(dict.fromkeys(all_stages))  # Remove duplicates while preserving order
unique_nodes = list(dict.fromkeys(all_nodes))

print(f"\nStages visited (in order): {unique_stages}")
print(f"Nodes visited (unique): {unique_nodes}")

# Expected flow through the 4 nodes
expected_nodes = ["clarification", "gap_analysis", "workflow_generation", "debug"]
missing_nodes = [node for node in expected_nodes if node not in unique_nodes]

if not missing_nodes:
    print("\n✅ SUCCESS: All 4 nodes were visited!")
else:
    print(f"\n❌ FAILED: Missing nodes: {missing_nodes}")

# Check if we reached completion
if "completed" in unique_stages:
    print("✅ Workflow reached COMPLETED stage!")
elif "debug" in unique_nodes:
    print("✅ Workflow reached debug stage!")
else:
    print("❌ Workflow did not complete")

print("\nTest completed!")