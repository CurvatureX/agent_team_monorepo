#!/usr/bin/env python
"""
Manual test script for enhanced Gap Analysis Node
Run with: python test_gap_optimization.py
"""

import asyncio
import json
import logging
from agents.nodes import WorkflowAgentNodes
from agents.state import WorkflowStage, WorkflowState

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_gap_analysis_flow():
    """Test the enhanced gap analysis flow with different scenarios"""
    
    print("\n" + "="*60)
    print("Testing Enhanced Gap Analysis Node")
    print("="*60)
    
    # Initialize nodes
    nodes = WorkflowAgentNodes()
    
    # Test Case 1: Simple workflow with no gaps
    print("\n[Test 1] Simple workflow - no gaps expected")
    print("-" * 40)
    state1 = {
        "session_id": "test1",
        "stage": WorkflowStage.GAP_ANALYSIS,
        "intent_summary": "Send me a daily summary email",
        "conversations": [
            {"role": "user", "text": "Send me a daily summary email"}
        ],
        "clarification_context": {},
        "gap_negotiation_count": 0,
        "identified_gaps": [],
        "gap_status": "no_gap"
    }
    
    try:
        result1 = await nodes.gap_analysis_node(state1)
        print(f"Result: gap_status={result1.get('gap_status')}")
        print(f"Gaps found: {len(result1.get('identified_gaps', []))}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test Case 2: Complex workflow with gaps
    print("\n[Test 2] Complex workflow - gaps expected")
    print("-" * 40)
    state2 = {
        "session_id": "test2",
        "stage": WorkflowStage.GAP_ANALYSIS,
        "intent_summary": "Monitor my Gmail in real-time and instantly notify me on Slack for urgent emails, also translate them to Chinese using AI",
        "conversations": [
            {"role": "user", "text": "Monitor Gmail realtime, notify Slack for urgent, translate to Chinese"}
        ],
        "clarification_context": {},
        "gap_negotiation_count": 0,
        "identified_gaps": [],
        "gap_status": "no_gap"
    }
    
    try:
        result2 = await nodes.gap_analysis_node(state2)
        print(f"Result: gap_status={result2.get('gap_status')}")
        gaps = result2.get('identified_gaps', [])
        print(f"Gaps found: {len(gaps)}")
        
        if gaps:
            print("\nIdentified Gaps:")
            for i, gap in enumerate(gaps):
                print(f"  {i+1}. {gap.get('required_capability', 'Unknown')}")
                if gap.get('alternatives'):
                    print(f"     Alternatives: {gap['alternatives'][:2]}...")
        
        # Check if smart negotiation message was created
        conversations = result2.get('conversations', [])
        if conversations:
            last_message = conversations[-1]
            if 'text' in last_message and '⭐' in last_message['text']:
                print("\n✅ Smart recommendation with star rating detected!")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test Case 3: Auto-resolution after max rounds
    print("\n[Test 3] Testing auto-resolution after max rounds")
    print("-" * 40)
    state3 = {
        "session_id": "test3",
        "stage": WorkflowStage.GAP_ANALYSIS,
        "intent_summary": "Complex workflow with gaps",
        "conversations": [],
        "clarification_context": {"purpose": "gap_negotiation"},
        "gap_negotiation_count": 1,  # Already negotiated once
        "identified_gaps": [],
        "gap_status": "has_gap"
    }
    
    try:
        result3 = await nodes.gap_analysis_node(state3)
        print(f"Negotiation count: {result3.get('gap_negotiation_count')}")
        print(f"Gap status: {result3.get('gap_status')}")
        
        if result3.get('gap_status') == 'gap_resolved':
            print("✅ Auto-resolution triggered after max rounds!")
            if result3.get('selected_alternative'):
                print(f"   Selected: {result3['selected_alternative']}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test routing logic
    print("\n[Test 4] Testing routing logic")
    print("-" * 40)
    
    # Test different routing scenarios
    test_states = [
        {"stage": WorkflowStage.GAP_ANALYSIS, "gap_status": "no_gap", "gap_negotiation_count": 0},
        {"stage": WorkflowStage.GAP_ANALYSIS, "gap_status": "has_gap", "gap_negotiation_count": 0},
        {"stage": WorkflowStage.GAP_ANALYSIS, "gap_status": "has_gap", "gap_negotiation_count": 1},
        {"stage": WorkflowStage.GAP_ANALYSIS, "gap_status": "gap_resolved", "gap_negotiation_count": 1},
    ]
    
    for i, test_state in enumerate(test_states):
        next_stage = nodes.should_continue(test_state)
        print(f"  Scenario {i+1}: gap_status={test_state['gap_status']}, "
              f"count={test_state['gap_negotiation_count']} → {next_stage}")
    
    print("\n" + "="*60)
    print("Test Complete!")
    print("="*60)


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_gap_analysis_flow())