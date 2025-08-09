#!/usr/bin/env python3
"""
Test script for the enhanced debug node with workflow_engine integration
Tests the complete flow: generation -> debug -> execution -> error feedback -> regeneration
"""

import asyncio
import json
import logging
from typing import Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_workflow_debug_flow():
    """Test the complete workflow debug flow"""
    
    try:
        # Import the workflow agent components
        from agents.workflow_agent import WorkflowAgent
        from agents.state import WorkflowState, WorkflowStage
        
        # Initialize the agent
        logger.info("Initializing Workflow Agent...")
        agent = WorkflowAgent()
        
        # Create a test state with a sample user request
        test_state = WorkflowState(
            session_id="test-session-001",
            user_id="test_user",
            stage=WorkflowStage.CLARIFICATION,
            conversations=[{
                "role": "user",
                "text": "Create a workflow that sends a daily email summary of GitHub issues",
                "timestamp": 1234567890
            }],
            intent_summary="",
            clarification_ready=True,  # Skip clarification for testing
            gap_status="no_gap",  # Skip gap analysis for testing
        )
        
        logger.info("Test Case 1: Simple workflow generation and debug")
        logger.info("-" * 50)
        
        # Step 1: Generate workflow
        logger.info("Step 1: Generating workflow...")
        state = await agent.nodes.workflow_generation_node(test_state)
        
        workflow = state.get("current_workflow")
        if workflow:
            logger.info(f"✓ Workflow generated: {workflow.get('name', 'Unknown')}")
            logger.info(f"  Nodes: {len(workflow.get('nodes', []))}")
            logger.info(f"  Connections: {len(workflow.get('connections', []))}")
        else:
            logger.error("✗ Failed to generate workflow")
            return
        
        # Step 2: Debug and execute workflow
        logger.info("\nStep 2: Debugging and executing workflow...")
        state = await agent.nodes.debug_node(state)
        
        debug_result = state.get("debug_result", {})
        if debug_result.get("success"):
            logger.info("✓ Workflow executed successfully!")
            logger.info(f"  Test data used: {json.dumps(debug_result.get('test_data_used', {}), indent=2)}")
        else:
            logger.warning("✗ Workflow execution failed")
            logger.warning(f"  Errors: {debug_result.get('errors', [])}")
            logger.warning(f"  Warnings: {debug_result.get('warnings', [])}")
            
            # Step 3: If failed, try regeneration
            if debug_result.get("errors"):
                logger.info("\nStep 3: Regenerating workflow based on errors...")
                state = await agent.nodes.workflow_generation_node(state)
                
                new_workflow = state.get("current_workflow")
                if new_workflow:
                    logger.info(f"✓ Workflow regenerated with fixes")
                    
                    # Step 4: Debug the regenerated workflow
                    logger.info("\nStep 4: Debugging regenerated workflow...")
                    state = await agent.nodes.debug_node(state)
                    
                    new_debug_result = state.get("debug_result", {})
                    if new_debug_result.get("success"):
                        logger.info("✓ Regenerated workflow executed successfully!")
                    else:
                        logger.warning("✗ Regenerated workflow still has issues")
                        logger.warning(f"  Remaining errors: {new_debug_result.get('errors', [])}")
        
        # Summary
        logger.info("\n" + "=" * 50)
        logger.info("Test Summary:")
        logger.info(f"  Debug iterations: {state.get('debug_loop_count', 0)}")
        logger.info(f"  Final status: {'SUCCESS' if debug_result.get('success') else 'FAILED'}")
        
        return state
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("Make sure you're running from the workflow_agent directory")
        logger.error("Try: cd /Users/bytedance/personal/agent_team_monorepo/apps/backend/workflow_agent")
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        return None

async def test_error_scenarios():
    """Test specific error scenarios"""
    
    logger.info("\n" + "=" * 50)
    logger.info("Testing Error Scenarios")
    logger.info("=" * 50)
    
    # Test Case 1: Invalid workflow structure
    from services.workflow_engine_client import WorkflowEngineClient
    from agents.test_data_generator import TestDataGenerator
    
    client = WorkflowEngineClient()
    generator = TestDataGenerator()
    
    # Create an invalid workflow (missing required fields)
    invalid_workflow = {
        "name": "Invalid Test Workflow",
        "nodes": [
            {"type": "trigger"}  # Missing id and other required fields
        ]
    }
    
    logger.info("\nTest Case: Invalid workflow structure")
    result = await client.validate_and_execute_workflow(invalid_workflow)
    
    if not result.get("success"):
        logger.info(f"✓ Correctly detected invalid workflow")
        logger.info(f"  Error: {result.get('error')}")
    else:
        logger.error("✗ Failed to detect invalid workflow")
    
    # Test Case 2: Test data generation
    valid_workflow = {
        "name": "Email Workflow",
        "description": "Send daily email summaries",
        "nodes": [
            {
                "id": "trigger1",
                "type": "trigger",
                "name": "Daily Trigger",
                "parameters": {"schedule": "0 9 * * *"}
            },
            {
                "id": "email1",
                "type": "action",
                "name": "Send Email",
                "parameters": {"to": "{{email}}", "subject": "{{subject}}"}
            }
        ],
        "connections": [{"from": "trigger1", "to": "email1"}]
    }
    
    logger.info("\nTest Case: Test data generation")
    test_data = await generator.generate_test_data(valid_workflow)
    logger.info(f"✓ Generated test data: {json.dumps(test_data, indent=2)}")

async def main():
    """Main test runner"""
    
    logger.info("Starting Workflow Debug Flow Tests")
    logger.info("=" * 50)
    
    # Run main flow test
    state = await test_workflow_debug_flow()
    
    # Run error scenario tests
    await test_error_scenarios()
    
    logger.info("\n" + "=" * 50)
    logger.info("All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())