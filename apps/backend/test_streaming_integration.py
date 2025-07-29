#!/usr/bin/env python3
"""
Test script to verify the streaming chat integration with workflow_agent
"""

import asyncio
import sys
import os

# Add the backend root to Python path
sys.path.insert(0, os.path.dirname(__file__))

from api_gateway.app.services.grpc_client import workflow_client
from api_gateway.app.services.response_processor import UnifiedResponseProcessor


async def test_grpc_connection():
    """Test gRPC connection to workflow agent"""
    print("🧪 Testing gRPC connection to workflow agent...")
    
    try:
        await workflow_client.connect()
        print("✅ Successfully connected to workflow agent")
        return True
    except Exception as e:
        print(f"❌ Failed to connect to workflow agent: {e}")
        return False
    finally:
        await workflow_client.close()


async def test_response_processor():
    """Test UnifiedResponseProcessor functionality"""
    print("🧪 Testing UnifiedResponseProcessor...")
    
    # Test clarification stage
    test_agent_state = {
        "conversations": [
            {"role": "assistant", "text": "What kind of workflow would you like to create?"}
        ],
        "stage": "clarification",
        "clarification_context": {
            "pending_questions": ["What is the main purpose?"],
            "purpose": "workflow_creation"
        }
    }
    
    try:
        processed = UnifiedResponseProcessor.process_stage_response("clarification", test_agent_state)
        print(f"✅ Clarification response processed: {processed['type']}")
        
        # Test workflow generation stage
        workflow_state = {
            "conversations": [
                {"role": "assistant", "text": "I've generated your workflow!"}
            ],
            "stage": "workflow_generation",
            "current_workflow": {"name": "Test Workflow", "nodes": []}
        }
        
        workflow_processed = UnifiedResponseProcessor.process_stage_response("workflow_generation", workflow_state)
        print(f"✅ Workflow response processed: {workflow_processed['type']}")
        
        return True
    except Exception as e:
        print(f"❌ Response processor test failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("🚀 Starting streaming integration tests...\n")
    
    # Test response processor (doesn't require gRPC)
    processor_ok = await test_response_processor()
    print()
    
    # Test gRPC connection (might fail if workflow_agent not running)
    grpc_ok = await test_grpc_connection()
    print()
    
    if processor_ok and grpc_ok:
        print("🎉 All tests passed! The streaming integration should work correctly.")
    elif processor_ok:
        print("⚠️ Response processor works, but gRPC connection failed.")
        print("   Make sure workflow_agent service is running on localhost:50051")
    else:
        print("❌ Tests failed. Check the implementation.")


if __name__ == "__main__":
    asyncio.run(main())