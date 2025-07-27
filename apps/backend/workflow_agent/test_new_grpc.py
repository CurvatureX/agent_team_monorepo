#!/usr/bin/env python3
"""
Test script for the new unified ProcessConversation gRPC interface
"""

import os
import asyncio

# Try to load .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✓ Loaded environment variables from .env file")
    print(os.getenv("SUPABASE_URL"))
    print(os.getenv("SUPABASE_SECRET_KEY"))
except ImportError:
    print("⚠ python-dotenv not installed, using environment variables or defaults")

from proto import workflow_agent_pb2
from services.grpc_server import WorkflowAgentServicer

async def test_process_conversation():
    """Test the ProcessConversation interface"""
    
    print("=== Testing New ProcessConversation gRPC Interface ===")
    
    # Create servicer
    servicer = WorkflowAgentServicer()
    print("✓ Servicer created successfully")
    
    # Create test request
    request = workflow_agent_pb2.ConversationRequest(
        session_id="test_session_123",
        user_id="test_user",
        user_message="I want to create a workflow that sends Gmail emails to Slack",
        workflow_context=workflow_agent_pb2.WorkflowContext(
            origin="create",
            source_workflow_id="",
            modification_intent=""
        ),
        config=workflow_agent_pb2.ConversationConfig(
            enable_streaming=True,
            max_turns=10,
            timeout_seconds=30,
            language="en",
            enable_rag=True
        )
    )
    print("✓ Test request created")
    
    # Mock gRPC context
    class MockContext:
        def set_code(self, code):
            pass
        def set_details(self, details):
            pass
    
    context = MockContext()
    
    try:
        print("\n=== Processing Conversation (Streaming) ===")
        response_count = 0
        
        async for response in servicer.ProcessConversation(request, context):
            response_count += 1
            print(f"\n[Response {response_count}]")
            print(f"  Type: {response.type}")
            print(f"  Session ID: {response.session_id}")
            print(f"  Is Final: {response.is_final}")
            print(f"  Timestamp: {response.timestamp}")
            
            if response.type == workflow_agent_pb2.RESPONSE_MESSAGE:
                print(f"  Message Text: {response.message.text}")
                print(f"  Message Type: {response.message.message_type}")
                print(f"  Role: {response.message.role}")
                
                if response.message.questions:
                    print("  Questions:")
                    for q in response.message.questions:
                        print(f"    - {q.question} (Category: {q.category})")
                
                if response.message.alternatives:
                    print("  Alternatives:")
                    for alt in response.message.alternatives:
                        print(f"    - {alt.title}: {alt.description}")
                        
            elif response.type == workflow_agent_pb2.RESPONSE_STATUS:
                print(f"  Status: {response.status.stage_description}")
                print(f"  New Stage: {response.status.new_stage}")
                print(f"  Previous Stage: {response.status.previous_stage}")
                
            elif response.type == workflow_agent_pb2.RESPONSE_ERROR:
                print(f"  Error Code: {response.error.error_code}")
                print(f"  Error Message: {response.error.message}")
                print(f"  Recoverable: {response.error.is_recoverable}")
            
            # Print current state info
            if response.updated_state:
                state = response.updated_state
                print(f"  Current Stage: {state.stage}")
                print(f"  Conversation History: {len(state.conversations)} messages")
                print(f"  Intent Summary: {state.intent_summary}")
                
            # Break if this is a final response that requires user input
            if response.is_final and response.type == workflow_agent_pb2.RESPONSE_MESSAGE:
                if response.message.message_type in ["question", "options"]:
                    print("\n  >>> Waiting for user input (breaking test loop)")
                    break
                    
        print(f"\n✓ Test completed - received {response_count} streaming responses")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_process_conversation())