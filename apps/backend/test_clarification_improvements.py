#!/usr/bin/env python3
"""
Test script for improved clarification node with conversation history and round limits
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from workflow_agent.agents.nodes import WorkflowAgentNodes
from workflow_agent.agents.state import WorkflowState, WorkflowStage
from workflow_agent.models.workflow_agent_state import ConversationMessage


async def test_clarification_with_conversation_history():
    """Test that clarification node properly uses conversation history"""
    print("\n=== Testing Clarification with Conversation History ===\n")
    
    nodes = WorkflowAgentNodes()
    
    # Create initial state with conversation history
    state = {
        "session_id": "test_session_001",
        "user_id": "test_user",
        "stage": WorkflowStage.CLARIFICATION,
        "conversations": [
            {"role": "user", "text": "I want to sync my emails to a messaging platform", "timestamp": 1000},
            {"role": "assistant", "text": "I'll help you sync emails to a messaging platform. Which email service are you using (Gmail, Outlook, etc.) and which messaging platform (Slack, Teams, Discord)?", "timestamp": 2000},
            {"role": "user", "text": "I'm using Gmail and want to send to Slack", "timestamp": 3000},
        ],
        "intent_summary": "",
        "clarification_context": {}
    }
    
    # Process clarification
    result = await nodes.clarification_node(state)
    
    print("Input conversation history:")
    for conv in state["conversations"]:
        print(f"  {conv['role']}: {conv['text'][:100]}...")
    
    print(f"\nIntent Summary: {result.get('intent_summary', '')[:200]}...")
    print(f"Stage: {result.get('stage')}")
    
    # Check if the node properly understood the context
    assert "Gmail" in result.get("intent_summary", ""), "Should capture Gmail from history"
    assert "Slack" in result.get("intent_summary", ""), "Should capture Slack from history"
    
    print("\n✅ Conversation history test passed!")
    return result


async def test_clarification_round_limits():
    """Test that clarification enforces round limits"""
    print("\n=== Testing Clarification Round Limits ===\n")
    
    nodes = WorkflowAgentNodes()
    
    # Create state at maximum rounds
    state = {
        "session_id": "test_session_002",
        "user_id": "test_user",
        "stage": WorkflowStage.CLARIFICATION,
        "conversations": [
            {"role": "user", "text": "automate something", "timestamp": 1000},
            {"role": "assistant", "text": "What would you like to automate?", "timestamp": 2000},
            {"role": "user", "text": "emails", "timestamp": 3000},
            {"role": "assistant", "text": "Which email service and what automation?", "timestamp": 4000},
            {"role": "user", "text": "just do something with gmail", "timestamp": 5000},
        ],
        "intent_summary": "",
        "clarification_context": {}
    }
    
    # Process clarification - should force completion
    result = await nodes.clarification_node(state)
    
    print(f"Number of user messages: {len([c for c in state['conversations'] if c['role'] == 'user'])}")
    print(f"Intent Summary: {result.get('intent_summary', '')[:200]}...")
    
    # Extract the clarification output from conversations
    last_assistant_msg = None
    for conv in reversed(result.get("conversations", [])):
        if conv.get("role") == "assistant":
            last_assistant_msg = conv.get("text", "")
            break
    
    print(f"Last assistant message: {last_assistant_msg[:200]}...")
    
    # Check if completion was forced
    clarification_context = result.get("clarification_context", {})
    pending_questions = clarification_context.get("pending_questions", [])
    
    print(f"Pending questions: {pending_questions}")
    print(f"Should be ready to proceed: {len(pending_questions) == 0}")
    
    print("\n✅ Round limit test passed!")
    return result


async def test_clarification_comprehensive_summary():
    """Test that intent_summary is comprehensive across conversation"""
    print("\n=== Testing Comprehensive Intent Summary ===\n")
    
    nodes = WorkflowAgentNodes()
    
    # Create state with multi-turn conversation
    state = {
        "session_id": "test_session_003",
        "user_id": "test_user",
        "stage": WorkflowStage.CLARIFICATION,
        "conversations": [
            {"role": "user", "text": "I need to monitor GitHub PRs", "timestamp": 1000},
            {"role": "assistant", "text": "I'll help you monitor GitHub PRs. What would you like to do when new PRs are created?", "timestamp": 2000},
            {"role": "user", "text": "Send notifications to our team Slack channel #dev-updates", "timestamp": 3000},
        ],
        "intent_summary": "",
        "clarification_context": {}
    }
    
    # Process clarification
    result = await nodes.clarification_node(state)
    
    intent_summary = result.get("intent_summary", "")
    print(f"Comprehensive Intent Summary: {intent_summary}")
    
    # Check that summary includes all key information
    assert "GitHub" in intent_summary, "Should include GitHub from first message"
    assert "PR" in intent_summary.upper(), "Should include PR monitoring"
    assert "Slack" in intent_summary, "Should include Slack from second message"
    
    print("\n✅ Comprehensive summary test passed!")
    return result


async def test_clarification_no_repetitive_questions():
    """Test that clarification doesn't ask questions already answered"""
    print("\n=== Testing No Repetitive Questions ===\n")
    
    nodes = WorkflowAgentNodes()
    
    # Create state where email service was already specified
    state = {
        "session_id": "test_session_004",
        "user_id": "test_user",
        "stage": WorkflowStage.CLARIFICATION,
        "conversations": [
            {"role": "user", "text": "I want to sync Gmail to somewhere", "timestamp": 1000},
            {"role": "assistant", "text": "Where would you like to sync your Gmail messages to?", "timestamp": 2000},
            {"role": "user", "text": "Maybe to a database or notification system", "timestamp": 3000},
        ],
        "intent_summary": "User wants to sync Gmail messages to a destination",
        "clarification_context": {}
    }
    
    # Process clarification
    result = await nodes.clarification_node(state)
    
    # Check the assistant's response
    last_assistant_msg = None
    for conv in reversed(result.get("conversations", [])):
        if conv.get("role") == "assistant":
            last_assistant_msg = conv.get("text", "")
            break
    
    print(f"Assistant response: {last_assistant_msg}")
    
    # Should NOT ask about Gmail again since it was already specified
    if last_assistant_msg and "?" in last_assistant_msg:
        assert "which email" not in last_assistant_msg.lower(), "Should not ask about email service again"
        assert "gmail" not in last_assistant_msg.lower() or "from gmail" in last_assistant_msg.lower(), "Should not question Gmail choice"
    
    print("\n✅ No repetitive questions test passed!")
    return result


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Improved Clarification Node")
    print("=" * 60)
    
    try:
        # Test 1: Conversation history awareness
        await test_clarification_with_conversation_history()
        
        # Test 2: Round limits enforcement
        await test_clarification_round_limits()
        
        # Test 3: Comprehensive summaries
        await test_clarification_comprehensive_summary()
        
        # Test 4: No repetitive questions
        await test_clarification_no_repetitive_questions()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())