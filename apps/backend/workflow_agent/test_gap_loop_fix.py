#!/usr/bin/env python3
"""
Test script to verify the gap analysis loop fix
"""

import asyncio
import json
import aiohttp

async def test_workflow():
    """Test the workflow with a request that should trigger gap analysis"""
    
    url = "http://localhost:8001/process-conversation"
    
    # Request that should trigger gap analysis
    request_data = {
        "session_id": "test-gap-loop-fix-001",
        "user_id": "test_user",
        "access_token": "test_token",  # Required field
        "user_message": "I want to sync unread gmail to slack"
    }
    
    print(f"Testing workflow with: {request_data['user_message']}")
    print("-" * 50)
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=request_data) as response:
            if response.status != 200:
                print(f"Error: {response.status}")
                return
                
            stage_transitions = []
            message_count = 0
            max_time = 30  # Maximum 30 seconds
            start_time = asyncio.get_event_loop().time()
            
            async for line in response.content:
                # Check timeout
                if asyncio.get_event_loop().time() - start_time > max_time:
                    print("\n⏱️ Timeout reached (30 seconds)")
                    break
                    
                if line:
                    line_str = line.decode('utf-8').strip()
                    if line_str.startswith("data: "):
                        try:
                            data = json.loads(line_str[6:])
                            
                            # Track status changes
                            if data.get("response_type") in ["STATUS_CHANGE", "RESPONSE_TYPE_STATUS_CHANGE"]:
                                status = data.get("status_change", {})
                                prev = status.get("previous_stage", "?")
                                curr = status.get("current_stage", "?")
                                node = status.get("node_name", "?")
                                stage_transitions.append(f"{prev} → {curr} (node: {node})")
                                print(f"Stage: {prev} → {curr} (node: {node})")
                                
                                # Check for the loop pattern
                                if len(stage_transitions) > 6:
                                    # Check if we're stuck in a loop
                                    last_4 = stage_transitions[-4:]
                                    if (last_4[0] == last_4[2] and 
                                        last_4[1] == last_4[3]):
                                        print("\n❌ LOOP DETECTED!")
                                        print(f"Repeating pattern: {last_4[0]} ↔ {last_4[1]}")
                                        break
                            
                            # Track messages
                            elif data.get("response_type") in ["MESSAGE", "RESPONSE_TYPE_MESSAGE"]:
                                message_count += 1
                                msg = data.get("message", "")[:100]
                                print(f"Message #{message_count}: {msg}...")
                                
                                # Check if it's the negotiation message
                                if "alternatives" in msg.lower() or "choose" in msg.lower():
                                    print("\n✅ Gap negotiation message sent to user!")
                                    print("Workflow should stop here and wait for user input.")
                                    
                                    # Wait a bit more to see if it continues
                                    await asyncio.sleep(2)
                                    
                            # Track workflow
                            elif data.get("response_type") in ["WORKFLOW", "RESPONSE_TYPE_WORKFLOW"]:
                                print("\n⚠️ Workflow generated - this shouldn't happen before user responds to gaps!")
                                
                        except json.JSONDecodeError:
                            pass
            
            print("\n" + "=" * 50)
            print("Test completed")
            print(f"Total transitions: {len(stage_transitions)}")
            print(f"Total messages: {message_count}")
            
            # Check final result
            if len(stage_transitions) <= 6:
                print("\n✅ No infinite loop detected")
            else:
                print("\n⚠️ Many transitions detected - possible issue")

if __name__ == "__main__":
    asyncio.run(test_workflow())