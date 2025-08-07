#!/usr/bin/env python3
"""
Test script to verify gap resolution works properly
"""

import asyncio
import json
import aiohttp
import uuid

async def test_workflow():
    """Test the workflow with gap resolution"""
    
    url = "http://localhost:8001/process-conversation"
    session_id = f"test-gap-resolution-{uuid.uuid4().hex[:8]}"
    
    # First request that should trigger gap analysis
    print("=" * 60)
    print("TEST: Gap Resolution Flow")
    print("=" * 60)
    
    # Step 1: Initial request
    request_data = {
        "session_id": session_id,
        "user_id": "test_user",
        "access_token": "test_token",
        "user_message": "I want to sync unread gmail to slack"
    }
    
    print(f"\n1. Initial request: {request_data['user_message']}")
    print("-" * 40)
    
    async with aiohttp.ClientSession() as session_client:
        # First request
        async with session_client.post(url, json=request_data) as response:
            if response.status != 200:
                print(f"Error: {response.status}")
                return
                
            stage_transitions = []
            messages = []
            
            async for line in response.content:
                if line:
                    line_str = line.decode('utf-8').strip()
                    if line_str.startswith("data: "):
                        try:
                            data = json.loads(line_str[6:])
                            
                            if data.get("response_type") in ["STATUS_CHANGE", "RESPONSE_TYPE_STATUS_CHANGE"]:
                                status = data.get("status_change", {})
                                prev = status.get("previous_stage", "?")
                                curr = status.get("current_stage", "?")
                                stage_transitions.append(f"{prev} → {curr}")
                                print(f"  Stage: {prev} → {curr}")
                            
                            elif data.get("response_type") in ["MESSAGE", "RESPONSE_TYPE_MESSAGE"]:
                                msg = data.get("message", "")
                                messages.append(msg)
                                print(f"  Message: {msg[:100]}...")
                                
                        except json.JSONDecodeError:
                            pass
            
            print(f"\nFirst request completed with {len(stage_transitions)} transitions")
            if messages:
                print(f"Last message (should be alternatives): {messages[-1][:200]}...")
        
        # Step 2: User chooses option B
        print(f"\n2. User response: 'B' (choosing manual trigger)")
        print("-" * 40)
        
        request_data["user_message"] = "B"
        
        async with session_client.post(url, json=request_data) as response:
            if response.status != 200:
                print(f"Error: {response.status}")
                return
                
            stage_transitions = []
            workflow_generated = False
            
            async for line in response.content:
                if line:
                    line_str = line.decode('utf-8').strip()
                    if line_str.startswith("data: "):
                        try:
                            data = json.loads(line_str[6:])
                            
                            if data.get("response_type") in ["STATUS_CHANGE", "RESPONSE_TYPE_STATUS_CHANGE"]:
                                status = data.get("status_change", {})
                                prev = status.get("previous_stage", "?")
                                curr = status.get("current_stage", "?")
                                stage_transitions.append(f"{prev} → {curr}")
                                print(f"  Stage: {prev} → {curr}")
                                
                                # Check for workflow generation
                                if curr == "workflow_generation":
                                    print("  ✅ Reached workflow_generation stage!")
                            
                            elif data.get("response_type") in ["WORKFLOW", "RESPONSE_TYPE_WORKFLOW"]:
                                workflow_generated = True
                                print("  ✅ Workflow generated successfully!")
                                
                        except json.JSONDecodeError:
                            pass
            
            print(f"\nSecond request completed with {len(stage_transitions)} transitions")
            
            # Check results
            print("\n" + "=" * 60)
            print("TEST RESULTS:")
            print("=" * 60)
            
            if workflow_generated:
                print("✅ SUCCESS: Workflow was generated after user choice")
            elif "workflow_generation" in str(stage_transitions):
                print("⚠️  PARTIAL: Reached workflow_generation but no workflow output")
            else:
                print("❌ FAILED: Did not reach workflow_generation stage")
                print(f"   Transitions: {stage_transitions}")

if __name__ == "__main__":
    asyncio.run(test_workflow())