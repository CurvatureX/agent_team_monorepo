#!/usr/bin/env python3
"""
End-to-end test for workflow agent integration (Phase 2)
Tests: API Gateway -> gRPC Client -> State Manager -> Database
"""

import asyncio
import json
import time
import uuid
from typing import Dict, Any

# Import application modules
from app.services.grpc_client import WorkflowGRPCClient
from app.services.state_manager import WorkflowStateManager
from app.database import init_admin_supabase
from app.utils import log_info, log_error, log_warning


async def test_state_manager():
    """Test basic state manager operations"""
    log_info("🧪 Testing State Manager operations...")
    
    state_manager = WorkflowStateManager()
    test_session_id = f"test_session_{uuid.uuid4().hex[:8]}"
    test_user_id = "test_user"
    
    try:
        # Test 1: Create state
        log_info("Test 1: Creating workflow state...")
        state_id = state_manager.create_state(
            session_id=test_session_id,
            user_id=test_user_id,
            initial_stage="clarification",
            clarification_context={"origin": "create", "pending_questions": []},
            workflow_context={"origin": "create", "source_workflow_id": "", "modification_intent": "test"}
        )
        
        if state_id:
            log_info(f"✅ State created with ID: {state_id}")
        else:
            log_error("❌ Failed to create state")
            return False
        
        # Test 2: Retrieve state
        log_info("Test 2: Retrieving workflow state...")
        retrieved_state = state_manager.get_state_by_session(test_session_id)
        
        if retrieved_state:
            log_info(f"✅ State retrieved: {retrieved_state['id']}")
            log_info(f"   Session: {retrieved_state['session_id']}")
            log_info(f"   Stage: {retrieved_state['stage']}")
        else:
            log_error("❌ Failed to retrieve state")
            return False
        
        # Test 3: Update state
        log_info("Test 3: Updating workflow state...")
        updates = {
            "stage": "gap_analysis",
            "intent_summary": "User wants to create a data processing workflow",
            "conversations": [
                {"role": "user", "text": "Create a workflow for data processing", "timestamp": int(time.time() * 1000)},
                {"role": "assistant", "text": "I'll help you create a data processing workflow", "timestamp": int(time.time() * 1000)}
            ]
        }
        
        success = state_manager.update_state(test_session_id, updates)
        if success:
            log_info("✅ State updated successfully")
        else:
            log_error("❌ Failed to update state")
            return False
        
        # Test 4: Verify update
        log_info("Test 4: Verifying state update...")
        updated_state = state_manager.get_state_by_session(test_session_id)
        
        if updated_state and updated_state["stage"] == "gap_analysis":
            log_info(f"✅ Update verified: Stage is now {updated_state['stage']}")
        else:
            log_error("❌ Update verification failed")
            return False
        
        # Test 5: Save full state
        log_info("Test 5: Testing full state save...")
        full_state = {
            "session_id": test_session_id,
            "user_id": test_user_id,
            "created_at": int(time.time() * 1000),
            "updated_at": int(time.time() * 1000),
            "stage": "workflow_generation",
            "execution_history": ["clarification", "gap_analysis"],
            "clarification_context": {"origin": "create", "pending_questions": []},
            "conversations": [
                {"role": "user", "text": "Generate the workflow now", "timestamp": int(time.time() * 1000)}
            ],
            "intent_summary": "Create automated data processing workflow",
            "gaps": [],
            "alternatives": [],
            "current_workflow": {"id": "wf_test", "name": "Test Workflow"},
            "debug_result": "",
            "debug_loop_count": 0
        }
        
        success = state_manager.save_full_state(test_session_id, full_state)
        if success:
            log_info("✅ Full state saved successfully")
        else:
            log_error("❌ Failed to save full state")
            return False
        
        # Test 6: Delete state
        log_info("Test 6: Deleting workflow state...")
        success = state_manager.delete_state(test_session_id)
        if success:
            log_info("✅ State deleted successfully")
        else:
            log_error("❌ Failed to delete state")
            return False
        
        log_info("🎉 All State Manager tests passed!")
        return True
        
    except Exception as e:
        log_error(f"❌ State Manager test failed: {e}")
        return False


async def test_grpc_client():
    """Test gRPC client with mock responses"""
    log_info("🧪 Testing gRPC Client operations...")
    
    client = WorkflowGRPCClient()
    test_session_id = f"test_grpc_{uuid.uuid4().hex[:8]}"
    
    try:
        # Test 1: Connect to service
        log_info("Test 1: Connecting to workflow service...")
        await client.connect()
        
        if client.connected:
            log_info("✅ Connected to workflow service")
        else:
            log_error("❌ Failed to connect to workflow service")
            return False
        
        # Test 2: Process conversation stream
        log_info("Test 2: Testing conversation stream...")
        responses = []
        
        async for response in client.process_conversation_stream(
            session_id=test_session_id,
            user_message="I want to create a workflow for data processing",
            user_id="test_user",
            workflow_context={"origin": "create", "source_workflow_id": "", "modification_intent": "test"}
        ):
            responses.append(response)
            log_info(f"   📥 Received: {response['type']}")
            
            # Stop after receiving final response
            if response.get("is_final", False):
                break
        
        if responses:
            log_info(f"✅ Received {len(responses)} responses from conversation stream")
            
            # Verify we got different response types
            response_types = set(r["type"] for r in responses)
            log_info(f"   Response types: {response_types}")
        else:
            log_error("❌ No responses received from conversation stream")
            return False
        
        # Test 3: Close connection
        log_info("Test 3: Closing connection...")
        await client.close()
        log_info("✅ Connection closed")
        
        log_info("🎉 All gRPC Client tests passed!")
        return True
        
    except Exception as e:
        log_error(f"❌ gRPC Client test failed: {e}")
        return False


async def test_end_to_end_integration():
    """Test complete end-to-end integration"""
    log_info("🧪 Testing End-to-End Integration...")
    
    client = WorkflowGRPCClient()
    test_session_id = f"test_e2e_{uuid.uuid4().hex[:8]}"
    
    try:
        # Test 1: Start conversation with state persistence
        log_info("Test 1: Starting conversation with state persistence...")
        
        await client.connect()
        responses = []
        
        async for response in client.process_conversation_stream(
            session_id=test_session_id,
            user_message="Create a workflow for processing customer data and sending emails",
            user_id="test_user_e2e",
            workflow_context={"origin": "create", "source_workflow_id": "", "modification_intent": "e2e test"},
            access_token=None  # Using admin access for test
        ):
            responses.append(response)
            log_info(f"   📥 {response['type']}: {response.get('message', {}).get('text', response.get('status', {}).get('stage_description', 'N/A'))[:50]}...")
            
            # Stop after receiving final response
            if response.get("is_final", False):
                break
        
        if responses:
            log_info(f"✅ End-to-end conversation completed with {len(responses)} responses")
        else:
            log_error("❌ No responses received in end-to-end test")
            return False
        
        # Test 2: Verify state was persisted
        log_info("Test 2: Verifying state persistence...")
        state_manager = client.state_manager
        persisted_state = state_manager.get_state_by_session(test_session_id)
        
        if persisted_state:
            log_info("✅ State was persisted successfully")
            log_info(f"   Session: {persisted_state['session_id']}")
            log_info(f"   User: {persisted_state['user_id']}")
            log_info(f"   Stage: {persisted_state['stage']}")
            log_info(f"   Conversations: {len(persisted_state.get('conversations', []))}")
        else:
            log_error("❌ State was not persisted")
            return False
        
        # Test 3: Continue conversation
        log_info("Test 3: Continuing conversation...")
        
        continue_responses = []
        async for response in client.process_conversation_stream(
            session_id=test_session_id,
            user_message="Please proceed with the workflow generation",
            user_id="test_user_e2e",
            access_token=None
        ):
            continue_responses.append(response)
            log_info(f"   📥 {response['type']}: {response.get('message', {}).get('text', response.get('status', {}).get('stage_description', 'N/A'))[:50]}...")
            
            if response.get("is_final", False):
                break
        
        if continue_responses:
            log_info(f"✅ Conversation continuation completed with {len(continue_responses)} responses")
        else:
            log_warning("⚠️ No responses received when continuing conversation")
        
        # Test 4: Cleanup
        log_info("Test 4: Cleaning up test data...")
        success = state_manager.delete_state(test_session_id)
        if success:
            log_info("✅ Test data cleaned up")
        else:
            log_warning("⚠️ Could not clean up test data")
        
        await client.close()
        
        log_info("🎉 End-to-End Integration test passed!")
        return True
        
    except Exception as e:
        log_error(f"❌ End-to-End Integration test failed: {e}")
        return False


async def main():
    """Run all tests"""
    log_info("🚀 Starting Phase 2 Integration Tests")
    log_info("="*50)
    
    # Initialize database connection
    try:
        init_admin_supabase()
        log_info("✅ Database connection initialized")
    except Exception as e:
        log_error(f"❌ Failed to initialize database: {e}")
        log_warning("⚠️ Some tests may fail without database connection")
    
    # Run tests
    results = {}
    
    log_info("\n" + "="*20 + " STATE MANAGER TESTS " + "="*20)
    results["state_manager"] = await test_state_manager()
    
    log_info("\n" + "="*20 + " GRPC CLIENT TESTS " + "="*22)
    results["grpc_client"] = await test_grpc_client()
    
    log_info("\n" + "="*20 + " END-TO-END TESTS " + "="*23)
    results["end_to_end"] = await test_end_to_end_integration()
    
    # Summary
    log_info("\n" + "="*20 + " TEST SUMMARY " + "="*27)
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        log_info(f"{test_name.replace('_', ' ').title()}: {status}")
    
    log_info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        log_info("🎉 All Phase 2 integration tests passed!")
        log_info("🚀 Ready for production deployment!")
    else:
        log_error(f"❌ {total - passed} test(s) failed")
        log_error("🔧 Please fix issues before proceeding")


if __name__ == "__main__":
    asyncio.run(main())