#!/usr/bin/env python3
"""
Test script for unified WorkflowState fields
Verifies all nodes work correctly with the unified state structure
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from agents.nodes import WorkflowAgentNodes
from agents.state import (
    WorkflowState,
    WorkflowStage,
    WorkflowOrigin,
    GapStatus,
    Conversation,
    ClarificationContext,
    WorkflowContext,
)
from services.state_manager import WorkflowAgentStateManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_initial_state() -> WorkflowState:
    """Create a properly initialized workflow state"""
    return WorkflowState(
        session_id="test-unified-001",
        user_id="test-user",
        stage=WorkflowStage.CLARIFICATION,
        conversations=[],
        user_message="I need a workflow to send daily reports to Slack",
        intent_summary="",
        workflow_context=WorkflowContext(
            origin=WorkflowOrigin.CREATE,
            requirements={}
        ),
        clarification_context=ClarificationContext(
            purpose="initial_intent",
            questions_asked=[],
            questions_pending=[],
            info_collected={},
            round_count=0
        ),
        identified_gaps=[],
        alternative_solutions=[],
        gap_status=GapStatus.NO_GAP,
        debug_loop_count=0,
        previous_errors=[],
        clarification_questions=[]
    )


async def test_clarification_node():
    """Test clarification node with unified state"""
    print("\n" + "="*60)
    print("Testing Clarification Node")
    print("="*60)
    
    nodes = WorkflowAgentNodes()
    state = create_initial_state()
    
    print(f"Initial state stage: {state['stage']}")
    print(f"User message: {state['user_message']}")
    
    try:
        result = await nodes.clarification_node(state)
        
        print("\n✅ Clarification node executed successfully")
        print(f"Intent summary: {result.get('intent_summary', 'Not set')}")
        print(f"Questions: {len(result.get('clarification_questions', []))}")
        print(f"Next stage: {result.get('stage')}")
        
        # Verify clarification context was updated
        context = result.get('clarification_context')
        if context:
            print(f"Clarification context updated:")
            print(f"  - Purpose: {context.get('purpose')}")
            print(f"  - Round count: {context.get('round_count')}")
            print(f"  - Pending questions: {len(context.get('questions_pending', []))}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error in clarification node: {e}")
        logger.error("Clarification node failed", exc_info=True)
        return state


async def test_gap_analysis_node(state: WorkflowState):
    """Test gap analysis node with unified state"""
    print("\n" + "="*60)
    print("Testing Gap Analysis Node")
    print("="*60)
    
    nodes = WorkflowAgentNodes()
    
    # Set up state for gap analysis
    state['stage'] = WorkflowStage.GAP_ANALYSIS
    state['intent_summary'] = "Daily Slack reporting workflow"
    
    print(f"Intent summary: {state['intent_summary']}")
    
    try:
        result = await nodes.gap_analysis_node(state)
        
        print("\n✅ Gap analysis node executed successfully")
        print(f"Gap status: {result.get('gap_status')}")
        print(f"Identified gaps: {len(result.get('identified_gaps', []))}")
        print(f"Alternative solutions: {len(result.get('alternative_solutions', []))}")
        print(f"Next stage: {result.get('stage')}")
        
        # Display gap details
        for gap in result.get('identified_gaps', []):
            if isinstance(gap, dict):
                print(f"\nGap found:")
                print(f"  - Capability: {gap.get('capability')}")
                print(f"  - Description: {gap.get('description')}")
                print(f"  - Severity: {gap.get('severity')}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error in gap analysis node: {e}")
        logger.error("Gap analysis node failed", exc_info=True)
        return state


async def test_workflow_generation_node(state: WorkflowState):
    """Test workflow generation node with unified state"""
    print("\n" + "="*60)
    print("Testing Workflow Generation Node")
    print("="*60)
    
    nodes = WorkflowAgentNodes()
    
    # Set up state for workflow generation
    state['stage'] = WorkflowStage.WORKFLOW_GENERATION
    
    print(f"Gap status: {state.get('gap_status')}")
    print("Generating workflow...")
    
    try:
        result = await nodes.workflow_generation_node(state)
        
        if 'current_workflow' in result:
            print("\n✅ Workflow generation executed successfully")
            workflow = result['current_workflow']
            print(f"Workflow ID: {workflow.get('id')}")
            print(f"Nodes: {len(workflow.get('nodes', []))}")
            print(f"Next stage: {result.get('stage')}")
        else:
            print("❌ No workflow generated")
        
        return result
        
    except Exception as e:
        print(f"❌ Error in workflow generation node: {e}")
        logger.error("Workflow generation node failed", exc_info=True)
        return state


async def test_debug_node(state: WorkflowState):
    """Test debug node with unified state"""
    print("\n" + "="*60)
    print("Testing Debug Node")
    print("="*60)
    
    nodes = WorkflowAgentNodes()
    
    # Set up state for debug
    state['stage'] = WorkflowStage.DEBUG
    
    print(f"Debug loop count: {state.get('debug_loop_count', 0)}")
    
    try:
        result = await nodes.debug_node(state)
        
        print("\n✅ Debug node executed successfully")
        
        debug_result = result.get('debug_result')
        if debug_result and isinstance(debug_result, dict):
            print(f"Debug result:")
            print(f"  - Success: {debug_result.get('success')}")
            print(f"  - Errors: {len(debug_result.get('errors', []))}")
            print(f"  - Warnings: {len(debug_result.get('warnings', []))}")
            print(f"  - Suggestions: {len(debug_result.get('suggestions', []))}")
        
        print(f"Next stage: {result.get('stage')}")
        print(f"Debug loop count: {result.get('debug_loop_count')}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error in debug node: {e}")
        logger.error("Debug node failed", exc_info=True)
        return state


def test_state_manager():
    """Test state manager with unified fields"""
    print("\n" + "="*60)
    print("Testing State Manager")
    print("="*60)
    
    manager = WorkflowAgentStateManager()
    
    # Create test state
    test_state = create_initial_state()
    
    print("Testing state persistence...")
    
    # Test saving state
    success = manager.save_full_state(
        session_id=test_state["session_id"],
        workflow_state=test_state
    )
    
    if success:
        print("✅ State saved successfully")
    else:
        print("⚠️  State save returned false (may be using mock)")
    
    # Test retrieving state
    retrieved = manager.get_state_by_session(test_state["session_id"])
    
    if retrieved:
        print("✅ State retrieved successfully")
        print(f"  - Session ID: {retrieved.get('session_id')}")
        print(f"  - Stage: {retrieved.get('stage')}")
        print(f"  - Gap status: {retrieved.get('gap_status')}")
        
        # Verify new fields are present
        new_fields = [
            'user_message',
            'clarification_questions',
            'alternative_solutions',
            'previous_errors',
            'previous_stage'
        ]
        
        print("\nChecking new fields:")
        for field in new_fields:
            if field in retrieved:
                print(f"  ✅ {field}: present")
            else:
                print(f"  ❌ {field}: missing")
    else:
        print("⚠️  No state retrieved (may be using mock)")


async def test_full_flow():
    """Test complete flow through all nodes"""
    print("\n" + "="*60)
    print("Testing Complete Flow")
    print("="*60)
    
    # Start with clarification
    state = create_initial_state()
    
    # Run through clarification
    print("\n1️⃣  Clarification Stage")
    state = await test_clarification_node()
    
    # Force progression to gap analysis
    state['stage'] = WorkflowStage.GAP_ANALYSIS
    state['intent_summary'] = "Daily Slack reporting workflow"
    
    print("\n2️⃣  Gap Analysis Stage")
    state = await test_gap_analysis_node(state)
    
    # Continue to workflow generation
    print("\n3️⃣  Workflow Generation Stage")
    state = await test_workflow_generation_node(state)
    
    # Final debug stage
    print("\n4️⃣  Debug Stage")
    state = await test_debug_node(state)
    
    print("\n" + "="*60)
    print("Complete Flow Test Finished")
    print(f"Final stage: {state.get('stage')}")
    print("="*60)


async def main():
    """Run all tests"""
    print("\n🚀 Testing Unified WorkflowState Implementation")
    print("=" * 60)
    
    # Test state manager
    test_state_manager()
    
    # Test individual nodes
    await test_full_flow()
    
    print("\n✅ All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())