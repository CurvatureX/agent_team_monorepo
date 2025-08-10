#!/usr/bin/env python
"""
Test script for the enhanced gap analysis with negotiation tracking
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.nodes import WorkflowAgentNodes
from agents.state import WorkflowState, WorkflowStage, Conversation, is_clarification_ready
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_gap_analysis():
    """Test the enhanced gap analysis node with negotiation tracking"""
    
    # Create an instance of the nodes
    nodes = WorkflowAgentNodes()
    
    # Create initial state with a workflow request that has gaps
    state: WorkflowState = {
        "session_id": "test_session_123",
        "user_id": "test_user",
        "created_at": int(time.time() * 1000),
        "updated_at": int(time.time() * 1000),
        "stage": WorkflowStage.CLARIFICATION,
        "intent_summary": "I want to build a workflow that monitors GitHub issues and automatically responds to them with AI-generated responses, then posts updates to Slack",
        "conversations": [
            Conversation(
                role="user",
                text="I want to build a workflow that monitors GitHub issues and automatically responds to them with AI-generated responses, then posts updates to Slack",
                timestamp=int(time.time() * 1000)
            )
        ],
        "clarification_context": {
            "purpose": "initial_intent",
            "collected_info": {},
            "pending_questions": [],
            "origin": "create"
        },
        "gap_status": "no_gap",
        "identified_gaps": [],
        "gap_negotiation_count": 0,  # Test the new field
        "selected_alternative": None,  # Test the new field
    }
    
    print("Testing Gap Analysis Node with enhanced negotiation tracking...")
    print("=" * 50)
    
    # Check if clarification is ready (should be True initially)
    ready = is_clarification_ready(state)
    print(f"\nInitial clarification_ready (derived): {ready}")
    
    # Run gap analysis
    print("\n1. Running initial gap analysis...")
    result = await nodes.gap_analysis_node(state)
    
    print(f"\nGap Status: {result.get('gap_status')}")
    print(f"Negotiation Count: {result.get('gap_negotiation_count', 0)}")
    print(f"Selected Alternative: {result.get('selected_alternative')}")
    
    identified_gaps = result.get("identified_gaps", [])
    if identified_gaps:
        print(f"\nIdentified {len(identified_gaps)} gap(s):")
        for i, gap in enumerate(identified_gaps, 1):
            print(f"\n  Gap {i}:")
            print(f"    Required: {gap.get('required_capability')}")
            print(f"    Missing: {gap.get('missing_component')}")
            alternatives = gap.get('alternatives', [])
            if alternatives:
                print(f"    Alternatives ({len(alternatives)}):")
                for j, alt in enumerate(alternatives, 1):
                    print(f"      {j}. {alt}")
    
    # Check if negotiation message was added
    conversations = result.get("conversations", [])
    if conversations:
        latest_msg = conversations[-1]
        if latest_msg.get("role") == "assistant":
            print(f"\nNegotiation Message:\n{latest_msg.get('text')}")
    
    # Simulate user choosing an alternative
    if result.get("gap_status") == "has_gap":
        print("\n2. Simulating user choosing alternative A...")
        state = result
        state["conversations"].append(Conversation(
            role="user",
            text="Let's go with option A",
            timestamp=int(time.time() * 1000)
        ))
        state["previous_stage"] = WorkflowStage.GAP_ANALYSIS
        
        # Run clarification to process the choice
        print("\n3. Processing user choice through clarification...")
        clarification_result = await nodes.clarification_node(state)
        
        # Run gap analysis again to see resolution
        print("\n4. Running gap analysis again after user choice...")
        state = clarification_result
        state["previous_stage"] = WorkflowStage.CLARIFICATION
        final_result = await nodes.gap_analysis_node(state)
        
        print(f"\nFinal Gap Status: {final_result.get('gap_status')}")
        print(f"Final Negotiation Count: {final_result.get('gap_negotiation_count', 0)}")
    
    print("\n" + "=" * 50)
    print("Test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_gap_analysis())