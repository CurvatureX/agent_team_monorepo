#!/usr/bin/env python3
"""
Simple test for workflow agent with clear output
"""
import json
import requests
import time
from datetime import datetime

# Colors
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RED = '\033[91m'
BOLD = '\033[1m'
ENDC = '\033[0m'


def test_workflow_conversation():
    """Test a simple conversation flow"""
    
    session_id = f"test-{int(time.time())}"
    print(f"\n{BOLD}🧪 Testing Workflow Agent{ENDC}")
    print(f"Session ID: {session_id}")
    print("="*60)
    
    # Test messages
    messages = [
        "I want to automate something",
        "I need to send daily email reports at 9 AM with sales data"
    ]
    
    for i, message in enumerate(messages, 1):
        print(f"\n{BOLD}Message {i}:{ENDC} {message}")
        print("-"*40)
        
        # Prepare request
        request_data = {
            "session_id": session_id,
            "user_id": "test-user",
            "user_message": message,
            "access_token": ""
        }
        
        try:
            # Send request with streaming
            response = requests.post(
                "http://localhost:8001/process-conversation",
                json=request_data,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream"
                },
                stream=True,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"{RED}❌ Error: {response.status_code}{ENDC}")
                print(response.text)
                continue
            
            # Process streaming response
            current_stage = None
            assistant_messages = []
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            response_type = data.get("response_type")
                            
                            if response_type == "RESPONSE_TYPE_STATUS_CHANGE":
                                stage = data.get("status_change", {}).get("current_stage")
                                if stage != current_stage:
                                    current_stage = stage
                                    print(f"{YELLOW}Stage:{ENDC} {stage}")
                                    
                            elif response_type == "RESPONSE_TYPE_MESSAGE":
                                msg = data.get("message", "")
                                if msg:
                                    assistant_messages.append(msg)
                                    
                            elif response_type == "RESPONSE_TYPE_WORKFLOW":
                                print(f"\n{GREEN}✨ Workflow Generated!{ENDC}")
                                
                            elif response_type == "RESPONSE_TYPE_ERROR":
                                error = data.get("error", {})
                                print(f"{RED}Error: {error.get('message')}{ENDC}")
                                
                        except json.JSONDecodeError:
                            pass
            
            # Print assistant response
            if assistant_messages:
                print(f"\n{GREEN}Assistant:{ENDC}")
                for msg in assistant_messages:
                    print(f"  {msg}")
            
            # Wait before next message
            if i < len(messages):
                print(f"\n{BLUE}Waiting 2 seconds...{ENDC}")
                time.sleep(2)
                
        except requests.exceptions.Timeout:
            print(f"{RED}⏱️ Request timed out{ENDC}")
        except Exception as e:
            print(f"{RED}❌ Error: {e}{ENDC}")
    
    print(f"\n{GREEN}✅ Test completed!{ENDC}")


def check_health():
    """Check if workflow agent is healthy"""
    try:
        response = requests.get("http://localhost:8001/health", timeout=5)
        if response.status_code == 200:
            print(f"{GREEN}✅ Workflow Agent is healthy{ENDC}")
            return True
    except:
        pass
    
    print(f"{RED}❌ Workflow Agent is not running{ENDC}")
    print("Please run: docker compose up")
    return False


if __name__ == "__main__":
    print(f"{BOLD}Workflow Agent Test{ENDC}")
    
    if check_health():
        test_workflow_conversation()