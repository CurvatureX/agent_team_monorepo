#!/usr/bin/env python3
"""
Simple test for workflow generation and creation
"""

import asyncio
import json
import httpx

async def test_direct_workflow_creation():
    """Test creating a workflow directly with correct structure"""
    
    # Correct workflow structure with all required fields
    workflow = {
        "name": "Timer HTTP Request Workflow",
        "description": "Send HTTP GET request to google.com every 5 minutes",
        "nodes": [
            {
                "id": "trigger-1",
                "name": "cron-trigger",
                "type": "TRIGGER_NODE",  # Correct uppercase format
                "subtype": "TRIGGER_CRON",  # Correct subtype from MCP
                "type_version": 1,
                "position": {"x": 100, "y": 100},  # Required field
                "parameters": {
                    "cron_expression": "*/5 * * * *"  # Correct parameter name from MCP
                },
                "credentials": {},
                "disabled": False,
                "on_error": "continue",
                "retry_policy": {
                    "max_tries": 3,
                    "wait_between_tries": 5
                }
            },
            {
                "id": "action-1",
                "name": "http-request",
                "type": "ACTION_NODE",  # Correct uppercase format
                "subtype": "HTTP_REQUEST",  # Correct subtype from MCP
                "type_version": 1,
                "position": {"x": 300, "y": 100},  # Required field
                "parameters": {
                    "url": "https://google.com",
                    "method": "GET",
                    "timeout": 30  # Integer, not string
                },
                "credentials": {},
                "disabled": False,
                "on_error": "continue",
                "retry_policy": {
                    "max_tries": 3,
                    "wait_between_tries": 5
                }
            }
        ],
        "connections": {  # Must be a dictionary, not array
            "cron-trigger": {
                "main": [
                    {
                        "node": "http-request",
                        "type": "main",
                        "index": 0
                    }
                ]
            }
        },
        "settings": {
            "timezone": {"name": "UTC"},
            "save_execution_progress": True,
            "save_manual_executions": True,
            "timeout": 3600,
            "error_policy": "continue",  # Must be "continue" or "stop"
            "caller_policy": "workflow"  # Must be "workflow" or "user"
        },
        "static_data": {},
        "tags": ["timer", "http", "test"]
    }
    
    print("=" * 60)
    print("Testing Direct Workflow Creation in Workflow Engine")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        # Test directly with workflow engine
        print("\n1. Testing with workflow engine...")
        response = await client.post(
            "http://localhost:8002/v1/workflows",
            json={
                **workflow,
                "user_id": "test_user"
            }
        )
        
        print(f"Response status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            workflow_id = result.get('workflow', {}).get('id')
            print(f"✅ Success! Workflow created with ID: {workflow_id}")
            return workflow_id
        else:
            print(f"❌ Failed: {response.text}")
            return None

async def test_workflow_agent_conversation():
    """Test workflow generation through workflow agent conversation"""
    
    print("\n" + "=" * 60)
    print("Testing Workflow Agent Conversation")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Send request to workflow agent
        print("\n2. Testing through workflow agent...")
        
        # First, we need to get session from API gateway
        # For simplicity, let's test directly with workflow agent
        response = await client.post(
            "http://localhost:8001/api/v1/conversation",
            json={
                "message": "Create a workflow that sends an HTTP GET request to https://google.com every 5 minutes using a cron trigger",
                "session_id": "test-simple-workflow",
                "user_id": "test_user"
            }
        )
        
        print(f"Response status: {response.status_code}")
        if response.status_code == 200:
            # Process streaming response
            workflow_found = False
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        if data.get("type") == "workflow":
                            workflow_found = True
                            workflow = data.get("data", {})
                            print("\n✅ Workflow generated!")
                            print(f"Name: {workflow.get('name')}")
                            print(f"Nodes: {len(workflow.get('nodes', []))}")
                            
                            # Show node details
                            for node in workflow.get('nodes', []):
                                print(f"  - {node.get('name')}: type={node.get('type')}, subtype={node.get('subtype')}")
                                
                        elif data.get("type") == "debug_result":
                            debug = data.get("data", {})
                            if debug.get("success"):
                                print("✅ Debug validation passed!")
                            else:
                                print(f"❌ Debug errors: {debug.get('errors')}")
                    except json.JSONDecodeError:
                        pass
            
            if not workflow_found:
                print("❌ No workflow generated in response")
        else:
            print(f"❌ Failed: {response.text}")

async def main():
    """Run tests"""
    print("Starting workflow tests...")
    
    # Test 1: Direct creation with correct structure
    workflow_id = await test_direct_workflow_creation()
    
    if workflow_id:
        print(f"\n✅ Direct workflow creation successful!")
        print(f"Workflow ID: {workflow_id}")
    else:
        print("\n❌ Direct workflow creation failed")
        print("Check the workflow structure and parameters")
    
    # Test 2: Through workflow agent (optional)
    # Uncomment to test workflow agent
    # await test_workflow_agent_conversation()

if __name__ == "__main__":
    asyncio.run(main())