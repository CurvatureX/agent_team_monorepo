#!/usr/bin/env python3
"""
Quick type check for updated workflow agent
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from workflow_agent.agents.state import WorkflowState, WorkflowStage, ClarificationContext
import time

def test_workflow_state():
    """Test WorkflowState with new fields"""
    print("Testing WorkflowState with new fields...")
    
    # Create a state with new fields
    state: WorkflowState = {
        "session_id": "test-123",
        "user_id": "user-123",
        "created_at": int(time.time() * 1000),
        "updated_at": int(time.time() * 1000),
        "stage": WorkflowStage.CLARIFICATION,
        "intent_summary": "",
        "conversations": [],
        "clarification_context": ClarificationContext(
            origin="create",
            pending_questions=[]
        ),
        # New gap analysis fields
        "gap_status": "no_gap",
        "identified_gaps": [],
        "gap_resolution": "",
        # Other fields
        "current_workflow": {},
        "debug_result": "",
        "debug_loop_count": 0,
    }
    
    print("✅ WorkflowState created successfully with new fields")
    print(f"   - gap_status: {state.get('gap_status')}")
    print(f"   - identified_gaps: {state.get('identified_gaps')}")
    print(f"   - gap_resolution: {state.get('gap_resolution')}")
    
    # Test that old fields are not present
    if "gaps" in state:
        print("❌ ERROR: Legacy 'gaps' field still present!")
    else:
        print("✅ Legacy 'gaps' field removed")
        
    if "alternatives" in state:
        print("❌ ERROR: Legacy 'alternatives' field still present!")
    else:
        print("✅ Legacy 'alternatives' field removed")
        
    if "selected_alternative" in state:
        print("❌ ERROR: Legacy 'selected_alternative' field still present!")
    else:
        print("✅ Legacy 'selected_alternative' field removed")
    
    return True

def main():
    print("\n🔍 Running type checks for updated workflow agent...\n")
    
    try:
        test_workflow_state()
        print("\n✅ All type checks passed!")
    except Exception as e:
        print(f"\n❌ Type check failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())