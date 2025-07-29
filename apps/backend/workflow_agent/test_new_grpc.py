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
            source_workflow_id=""
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
            
            if response.response_type == workflow_agent_pb2.RESPONSE_TYPE_MESSAGE:
                print(f"  Message: {response.message}")
            elif response.response_type == workflow_agent_pb2.RESPONSE_TYPE_WORKFLOW:
                print(f"  Workflow: {response.workflow}")
            elif response.response_type == workflow_agent_pb2.RESPONSE_TYPE_ERROR:
                print(f"  Error Code: {response.error.error_code}")
                print(f"  Error Message: {response.error.message}")
                print(f"  Recoverable: {response.error.is_recoverable}")
                    
        print(f"\n✓ Test completed - received {response_count} streaming responses")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_process_conversation())