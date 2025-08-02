#!/usr/bin/env python3
"""
Simple interactive test script for workflow agent chat flow
Uses only standard library modules
"""
import json
import urllib.request
import urllib.parse
import urllib.error
import ssl
import time
from datetime import datetime
import sys

# Configuration
API_GATEWAY_URL = "http://localhost:8000"
WORKFLOW_AGENT_URL = "http://localhost:8001"

# ANSI color codes
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def log(message, color=""):
    """Print colored log message"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Colors.BLUE}[{timestamp}]{Colors.ENDC} {color}{message}{Colors.ENDC}")


def send_to_workflow_agent(session_id, user_message, conversation_history=[]):
    """Send message directly to workflow agent and get streaming response"""
    
    request_data = {
        "session_id": session_id,
        "user_id": "test-user",
        "user_message": user_message,
        "access_token": ""
    }
    
    log(f"💬 Sending: {user_message}", Colors.BOLD)
    
    # Create request
    req = urllib.request.Request(
        f"{WORKFLOW_AGENT_URL}/process-conversation",
        data=json.dumps(request_data).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream'
        }
    )
    
    current_stage = None
    messages = []
    
    try:
        # Send request and read streaming response
        with urllib.request.urlopen(req) as response:
            buffer = ""
            while True:
                chunk = response.read(1024).decode('utf-8')
                if not chunk:
                    break
                
                buffer += chunk
                lines = buffer.split('\n')
                buffer = lines[-1]  # Keep incomplete line in buffer
                
                for line in lines[:-1]:
                    line = line.strip()
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            response_type = data.get("response_type")
                            
                            if response_type == "RESPONSE_TYPE_STATUS_CHANGE":
                                status = data.get("status_change", {})
                                new_stage = status.get("current_stage")
                                if new_stage and new_stage != current_stage:
                                    current_stage = new_stage
                                    log(f"🔄 Stage: {current_stage}", Colors.YELLOW)
                                    
                            elif response_type == "RESPONSE_TYPE_MESSAGE":
                                message = data.get("message", "")
                                if message:
                                    log(f"\n🤖 Assistant: {message}", Colors.GREEN)
                                    messages.append(message)
                                    
                            elif response_type == "RESPONSE_TYPE_WORKFLOW":
                                log("\n✨ Workflow Generated!", Colors.BOLD + Colors.GREEN)
                                workflow_str = data.get("workflow", "{}")
                                try:
                                    workflow = json.loads(workflow_str)
                                    print(json.dumps(workflow, indent=2))
                                except:
                                    print(workflow_str)
                                    
                            elif response_type == "RESPONSE_TYPE_ERROR":
                                error = data.get("error", {})
                                log(f"❌ Error: {error.get('message', 'Unknown error')}", Colors.RED)
                                
                        except json.JSONDecodeError:
                            pass
                            
    except urllib.error.HTTPError as e:
        log(f"❌ HTTP Error {e.code}: {e.reason}", Colors.RED)
        if e.code == 500:
            try:
                error_body = e.read().decode('utf-8')
                error_data = json.loads(error_body)
                log(f"Error details: {error_data.get('detail', 'No details')}", Colors.RED)
            except:
                pass
    except Exception as e:
        log(f"❌ Error: {e}", Colors.RED)
    
    return messages


def interactive_test():
    """Run interactive test"""
    print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}🚀 WORKFLOW AGENT CHAT TESTER{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"\nDirect connection to Workflow Agent at {WORKFLOW_AGENT_URL}")
    print(f"\nCommands:")
    print(f"  {Colors.YELLOW}/new{Colors.ENDC}    - Start new session")
    print(f"  {Colors.YELLOW}/exit{Colors.ENDC}   - Exit")
    print(f"  {Colors.YELLOW}/test{Colors.ENDC}   - Run test scenario")
    
    session_id = f"test-session-{int(time.time())}"
    log(f"Session ID: {session_id}", Colors.BLUE)
    
    conversation_history = []
    
    print(f"\n{Colors.GREEN}Ready! Type your message or command.{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")
    
    while True:
        try:
            user_input = input(f"{Colors.YELLOW}You> {Colors.ENDC}").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() == "/exit":
                log("👋 Goodbye!", Colors.GREEN)
                break
                
            elif user_input.lower() == "/new":
                session_id = f"test-session-{int(time.time())}"
                conversation_history = []
                log(f"🆕 New session: {session_id}", Colors.GREEN)
                
            elif user_input.lower() == "/test":
                # Run test scenario
                log("🧪 Running test scenario...", Colors.BLUE)
                test_messages = [
                    "I want to automate something",
                    "I need to send daily email reports at 9 AM",
                    "The reports should include sales data from our database"
                ]
                
                for msg in test_messages:
                    print()
                    messages = send_to_workflow_agent(session_id, msg, conversation_history)
                    conversation_history.append({"role": "user", "text": msg})
                    if messages:
                        conversation_history.append({"role": "assistant", "text": "\n".join(messages)})
                    time.sleep(2)
                    
            else:
                # Send regular message
                print()
                messages = send_to_workflow_agent(session_id, user_input, conversation_history)
                conversation_history.append({"role": "user", "text": user_input})
                if messages:
                    conversation_history.append({"role": "assistant", "text": "\n".join(messages)})
                
            print()
            
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Use /exit to quit{Colors.ENDC}")
        except Exception as e:
            log(f"Error: {e}", Colors.RED)


def automated_test():
    """Run automated test with specific scenarios"""
    print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}🤖 AUTOMATED TEST SCENARIOS{Colors.ENDC}") 
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
    
    scenarios = [
        {
            "name": "Basic Clarification Flow",
            "messages": [
                "I want to automate something",
                "I need to monitor my website and get alerts",
                "Check https://example.com every 5 minutes and email me if it's down"
            ]
        },
        {
            "name": "Alternative Generation Flow", 
            "messages": [
                "I need OAuth2 integration with custom token rotation",
                "I'll go with option 1",
                "It's for our internal CRM API to sync customer data"
            ]
        }
    ]
    
    for scenario in scenarios:
        print(f"\n{Colors.BLUE}📋 Scenario: {scenario['name']}{Colors.ENDC}")
        print("="*50)
        
        session_id = f"test-{scenario['name'].lower().replace(' ', '-')}-{int(time.time())}"
        conversation_history = []
        
        for msg in scenario['messages']:
            print()
            messages = send_to_workflow_agent(session_id, msg, conversation_history)
            conversation_history.append({"role": "user", "text": msg})
            if messages:
                conversation_history.append({"role": "assistant", "text": "\n".join(messages)})
            time.sleep(2)
        
        print(f"\n{Colors.GREEN}✅ Scenario completed{Colors.ENDC}")
        time.sleep(3)


if __name__ == "__main__":
    try:
        # Check if services are running
        try:
            req = urllib.request.Request(f"{WORKFLOW_AGENT_URL}/health")
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    log("✅ Workflow Agent is healthy", Colors.GREEN)
        except:
            log("❌ Workflow Agent is not running at " + WORKFLOW_AGENT_URL, Colors.RED)
            log("Please run: docker compose up", Colors.YELLOW)
            sys.exit(1)
        
        if "--test" in sys.argv:
            automated_test()
        else:
            interactive_test()
            
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Interrupted{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.ENDC}")