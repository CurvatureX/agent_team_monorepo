#!/usr/bin/env python3
"""
Unit test for the new workflow agent flow
Tests the graph structure and node transitions
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from workflow_agent.agents.workflow_agent import WorkflowAgent
from workflow_agent.agents.state import WorkflowState, WorkflowStage, WorkflowOrigin, ClarificationContext
import time


async def test_clarification_to_gap_analysis():
    """Test: Clarification (complete) -> Gap Analysis"""
    print("\n" + "="*60)
    print("Test: Clarification (complete) -> Gap Analysis")
    print("="*60)
    
    agent = WorkflowAgent()
    
    # Initial state with clear requirements
    state: WorkflowState = {
        "session_id": "test-123",
        "user_id": "user-123",
        "created_at": int(time.time() * 1000),
        "updated_at": int(time.time() * 1000),
        "stage": WorkflowStage.CLARIFICATION,
        "intent_summary": "",
        "clarification_context": ClarificationContext(
            origin=WorkflowOrigin.CREATE,
            pending_questions=[]
        ),
        "conversations": [
            {"role": "user", "text": "I want to send daily reports via email at 9 AM"}
        ],
        "gaps": [],
        "alternatives": [],
        "current_workflow": {},
        "debug_result": "",
        "debug_loop_count": 0,
    }
    
    # Process through the graph
    print("\nInitial stage:", state["stage"])
    
    async for step in agent.graph.astream(state):
        for node_name, node_state in step.items():
            print(f"\nNode executed: {node_name}")
            print(f"New stage: {node_state.get('stage')}")
            
            # Check if we reached gap analysis
            if node_state.get("stage") == WorkflowStage.GAP_ANALYSIS:
                print("✅ Successfully transitioned to Gap Analysis!")
                return True
            
            # Update state for next iteration
            state = node_state
    
    return False


async def test_clarification_loop():
    """Test: Clarification (needs more info) -> Stay in Clarification"""
    print("\n" + "="*60)
    print("Test: Clarification Loop (needs more info)")
    print("="*60)
    
    agent = WorkflowAgent()
    
    # Initial state with vague requirements
    state: WorkflowState = {
        "session_id": "test-456",
        "user_id": "user-123",
        "created_at": int(time.time() * 1000),
        "updated_at": int(time.time() * 1000),
        "stage": WorkflowStage.CLARIFICATION,
        "intent_summary": "",
        "clarification_context": ClarificationContext(
            origin=WorkflowOrigin.CREATE,
            pending_questions=[]
        ),
        "conversations": [
            {"role": "user", "text": "I want to automate something"}
        ],
        "gaps": [],
        "alternatives": [],
        "current_workflow": {},
        "debug_result": "",
        "debug_loop_count": 0,
    }
    
    print("\nInitial stage:", state["stage"])
    
    # Process once - should stay in clarification with questions
    iteration_count = 0
    async for step in agent.graph.astream(state):
        iteration_count += 1
        for node_name, node_state in step.items():
            print(f"\nNode executed: {node_name}")
            print(f"Stage: {node_state.get('stage')}")
            
            # Check clarification context
            clarif_context = node_state.get("clarification_context", {})
            pending_q = clarif_context.get("pending_questions", [])
            if pending_q:
                print(f"Pending questions: {len(pending_q)}")
            
            # Should terminate after clarification asks questions
            if node_name == "clarification" and pending_q:
                print("✅ Clarification correctly waiting for user input!")
                return True
            
            state = node_state
        
        # Prevent infinite loop
        if iteration_count > 5:
            print("❌ Too many iterations")
            return False
    
    return True


async def test_alternative_to_clarification():
    """Test: Alternative Generation -> Clarification (for user choice)"""
    print("\n" + "="*60)
    print("Test: Alternative Generation -> Clarification")
    print("="*60)
    
    agent = WorkflowAgent()
    
    # State after gap analysis found issues
    state: WorkflowState = {
        "session_id": "test-789",
        "user_id": "user-123",
        "created_at": int(time.time() * 1000),
        "updated_at": int(time.time() * 1000),
        "stage": WorkflowStage.ALTERNATIVE_GENERATION,
        "intent_summary": "User wants OAuth2 integration",
        "clarification_context": ClarificationContext(
            origin=WorkflowOrigin.CREATE,
            pending_questions=[]
        ),
        "conversations": [
            {"role": "user", "text": "I need OAuth2 authentication"},
            {"role": "assistant", "text": "I understand you need OAuth2"}
        ],
        "gaps": ["oauth2_not_supported"],
        "alternatives": [],
        "current_workflow": {},
        "debug_result": "",
        "debug_loop_count": 0,
    }
    
    print("\nInitial stage:", state["stage"])
    
    async for step in agent.graph.astream(state):
        for node_name, node_state in step.items():
            print(f"\nNode executed: {node_name}")
            print(f"New stage: {node_state.get('stage')}")
            
            # Check if alternatives were generated
            if node_name == "alternative_generation":
                alts = node_state.get("alternatives", [])
                print(f"Alternatives generated: {len(alts)}")
            
            # Should go back to clarification
            if node_state.get("stage") == WorkflowStage.CLARIFICATION and node_name == "alternative_generation":
                print("✅ Alternative correctly routed to Clarification!")
                return True
            
            state = node_state
    
    return False


async def main():
    """Run all unit tests"""
    print("\n🚀 Running Workflow Agent Unit Tests")
    
    tests = [
        test_clarification_to_gap_analysis,
        test_clarification_loop,
        test_alternative_to_clarification,
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append((test.__name__, result))
        except Exception as e:
            print(f"\n❌ Error in {test.__name__}: {e}")
            results.append((test.__name__, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {total - passed} tests failed")


if __name__ == "__main__":
    asyncio.run(main())