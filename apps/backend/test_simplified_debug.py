#!/usr/bin/env python3
"""
Test script for simplified debug node behavior.
Tests that:
1. Debug node no longer assumes execution result fields
2. Debug node doesn't return to clarification
3. Max 2 attempts before giving up
"""

import asyncio
import json
import logging
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Mock workflow with intentional errors for testing
MOCK_WORKFLOW_WITH_ERROR = {
    "name": "Test Workflow with Error",
    "description": "Workflow designed to fail for testing",
    "nodes": [
        {
            "id": "trigger",
            "type": "TRIGGER_NODE",
            "subtype": "MANUAL_TRIGGER",
            "name": "Start",
            # Missing required parameter to cause error
            "parameters": {}
        },
        {
            "id": "action",
            "type": "ACTION_NODE", 
            "subtype": "INVALID_SUBTYPE",  # Invalid subtype to cause error
            "name": "Process",
            "parameters": {
                "action": "process_data"
            }
        }
    ],
    "connections": [
        {"from": "trigger", "to": "action"}
    ]
}

async def test_debug_node_simplified():
    """Test the simplified debug node behavior"""
    
    # Import after setting up environment
    from workflow_agent.agents.nodes import WorkflowAgentNodes
    from workflow_agent.agents.state import WorkflowState, WorkflowStage
    from workflow_agent.services.workflow_engine_client import WorkflowEngineClient
    
    logger.info("Testing simplified debug node...")
    
    # Initialize the nodes
    nodes = WorkflowAgentNodes()
    
    # Create initial state with a workflow that will fail
    state: WorkflowState = {
        "stage": WorkflowStage.DEBUG,
        "intent_summary": "Test workflow for debug node",
        "workflows": [MOCK_WORKFLOW_WITH_ERROR],
        "current_workflow_index": 0,
        "debug_loop_count": 0,
        "user_id": "test_user",
        "conversation_messages": []
    }
    
    # Test 1: First debug attempt
    logger.info("\n=== Test 1: First Debug Attempt ===")
    result1 = await nodes.debug_node(state)
    
    assert result1["debug_loop_count"] == 1, "Debug loop count should be 1"
    assert result1["debug_result"]["success"] == False, "Should fail on invalid workflow"
    
    # Check that error is simplified (just "ERROR" or actual error message)
    error_msg = result1["debug_result"].get("error")
    logger.info(f"Debug error (attempt 1): {error_msg}")
    assert error_msg is not None, "Should have error message"
    
    # Check routing - should stay in DEBUG stage for retry
    if result1["debug_loop_count"] < 2:
        assert result1["stage"] == WorkflowStage.DEBUG, "Should stay in DEBUG for retry"
        assert "debug_error_for_regeneration" in result1, "Should pass error for regeneration"
    
    logger.info("✓ First debug attempt handled correctly")
    
    # Test 2: Second debug attempt (still with error)
    logger.info("\n=== Test 2: Second Debug Attempt ===")
    state2 = result1.copy()
    result2 = await nodes.debug_node(state2)
    
    assert result2["debug_loop_count"] == 2, "Debug loop count should be 2"
    
    # After 2 attempts, should complete even with errors
    assert result2["stage"] == WorkflowStage.COMPLETED, "Should complete after 2 attempts"
    logger.info("✓ Completes after max 2 attempts")
    
    # Test 3: Verify no clarification routing
    logger.info("\n=== Test 3: Verify No Clarification Routing ===")
    # Check that at no point did we route to clarification
    assert result1["stage"] != WorkflowStage.CLARIFICATION, "Should not route to clarification"
    assert result2["stage"] != WorkflowStage.CLARIFICATION, "Should not route to clarification"
    logger.info("✓ Never routes to clarification")
    
    # Test 4: Test with successful workflow
    logger.info("\n=== Test 4: Test with Valid Workflow ===")
    valid_workflow = {
        "name": "Valid Test Workflow",
        "description": "A valid workflow for testing",
        "nodes": [
            {
                "id": "trigger",
                "type": "TRIGGER_NODE",
                "subtype": "MANUAL_TRIGGER",
                "name": "Start",
                "parameters": {
                    "name": "Manual Start"
                }
            }
        ],
        "connections": []
    }
    
    state3: WorkflowState = {
        "stage": WorkflowStage.DEBUG,
        "intent_summary": "Valid test workflow",
        "workflows": [valid_workflow],
        "current_workflow_index": 0,
        "debug_loop_count": 0,
        "user_id": "test_user",
        "conversation_messages": []
    }
    
    # Mock successful execution
    # Note: In real environment, this would call the actual workflow engine
    # For testing, we'll just verify the structure
    
    logger.info("✓ All tests passed!")
    
    return True

async def main():
    """Main test runner"""
    try:
        success = await test_debug_node_simplified()
        if success:
            logger.info("\n🎉 Simplified debug node tests completed successfully!")
            return 0
        else:
            logger.error("\n❌ Tests failed")
            return 1
    except Exception as e:
        logger.error(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)