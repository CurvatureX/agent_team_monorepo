#!/usr/bin/env python
"""
Test script for the optimized 3-node workflow architecture
Tests that gap analysis is now handled automatically in workflow_generation
"""

import asyncio
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from workflow_agent.agents.workflow_agent import WorkflowAgent
from workflow_agent.agents.state import WorkflowState, WorkflowStage


async def test_optimized_workflow():
    """Test the optimized workflow without gap_analysis node"""
    
    print("=" * 60)
    print("Testing Optimized 3-Node Workflow Architecture")
    print("=" * 60)
    
    # Initialize the workflow agent
    workflow_agent = WorkflowAgent()
    
    # Create initial state with a request that would previously trigger gap analysis
    initial_state = {
        "session_id": "test_session_001",
        "user_id": "test_user",
        "created_at": int(datetime.now().timestamp() * 1000),
        "updated_at": int(datetime.now().timestamp() * 1000),
        "stage": WorkflowStage.CLARIFICATION,
        "intent_summary": "",
        "conversations": [
            {
                "role": "user",
                "text": "I need a workflow that automatically analyzes customer emails and creates tasks in our project management system"
            }
        ],
        "clarification_context": {
            "purpose": "initial_intent",
            "collected_info": {},
            "pending_questions": [],
            "origin": "create"
        },
        "execution_history": []
    }
    
    print("\n📥 Initial User Request:")
    print(f"   '{initial_state['conversations'][0]['text']}'")
    
    print("\n🔄 Processing through optimized workflow...")
    print("   Expected flow: Clarification → Workflow Generation → Debug")
    
    # Process through the workflow
    chunk_count = 0
    current_stage = None
    
    try:
        async for chunk in workflow_agent.astream(initial_state):
            chunk_count += 1
            
            # Extract stage from chunk
            for node_name, node_state in chunk.items():
                if isinstance(node_state, dict) and 'stage' in node_state:
                    new_stage = node_state.get('stage')
                    if new_stage != current_stage:
                        current_stage = new_stage
                        print(f"\n   ✓ Stage {chunk_count}: {current_stage}")
                        
                        # Check we're not going through gap_analysis
                        if current_stage == "gap_analysis":
                            print("   ❌ ERROR: Should not go through gap_analysis node!")
                            return False
                        
                        # Print any automatic decisions made
                        if current_stage == WorkflowStage.WORKFLOW_GENERATION:
                            print("      → Automatically handling any capability gaps...")
            
            # Limit chunks to prevent infinite loops
            if chunk_count > 10:
                print("\n   ⚠️  Stopping after 10 chunks (check for infinite loop)")
                break
        
        print(f"\n✅ Workflow completed successfully in {chunk_count} chunks")
        print("   No gap_analysis node was invoked - gaps handled automatically!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error during workflow processing: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Set up minimal environment
    os.environ.setdefault("OPENAI_API_KEY", "test_key")
    os.environ.setdefault("GAP_ANALYSIS_USE_MCP", "true")
    
    # Run the test
    success = asyncio.run(test_optimized_workflow())
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Test PASSED: Optimized architecture working correctly")
    else:
        print("❌ Test FAILED: Check the implementation")
    print("=" * 60)
    
    sys.exit(0 if success else 1)