#!/usr/bin/env python3
"""
Unit test to debug clarification node behavior
"""
import asyncio
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from workflow_agent.agents.nodes import WorkflowAgentNodes
from workflow_agent.agents.state import WorkflowState, WorkflowStage, ClarificationContext
import time

# Mock the LLM response
class MockLLM:
    async def ainvoke(self, messages):
        # Return a response that marks clarification as complete
        class MockResponse:
            content = json.dumps({
                "clarification_question": "",
                "is_complete": True,
                "workflow_summary": "## 工作流概述\nDaily email reminder workflow\n\n## 触发器\n### 1. Time Trigger\n**触发条件：** Every day at 9 AM\n**工作流程：**\n1. **Send Email**\n   - Send reminder email\n\n## 核心功能\n- **Email Sending：** Send daily reminders\n\n## 集成系统\n- **Email System：** For sending emails"
            })
        return MockResponse()

async def test_clarification_complete():
    """Test clarification node when it should mark as complete"""
    print("\n" + "="*60)
    print("Test: Clarification marks as complete")
    print("="*60)
    
    nodes = WorkflowAgentNodes()
    # Replace LLM with mock
    nodes.llm = MockLLM()
    
    # Initial state
    state: WorkflowState = {
        "session_id": "test-123",
        "user_id": "user-123",
        "created_at": int(time.time() * 1000),
        "updated_at": int(time.time() * 1000),
        "stage": WorkflowStage.CLARIFICATION,
        "intent_summary": "",
        "clarification_context": ClarificationContext(
            origin="create",
            pending_questions=[]
        ),
        "conversations": [
            {"role": "user", "text": "Create a daily email reminder at 9 AM"}
        ],
    }
    
    print(f"\nInitial stage: {state['stage']}")
    print(f"Initial intent_summary: '{state['intent_summary']}'")
    
    # Run clarification node
    result = await nodes.clarification_node(state)
    
    print(f"\nAfter clarification:")
    print(f"  Stage: {result.get('stage')}")
    print(f"  Intent summary: '{result.get('intent_summary')}'")
    print(f"  Pending questions: {result.get('clarification_context', {}).get('pending_questions', [])}")
    
    # Check should_continue
    next_node = nodes.should_continue(result)
    print(f"\nshould_continue returns: {next_node}")
    
    if result.get("stage") == WorkflowStage.GAP_ANALYSIS:
        print("\n✅ SUCCESS: Clarification correctly moved to gap_analysis stage!")
        return True
    else:
        print("\n❌ FAILED: Clarification did not progress to gap_analysis")
        return False

# Mock for prompt engine
class MockPromptEngine:
    async def render_prompt(self, template_name, **kwargs):
        if "clarification" in template_name:
            if "system" in template_name:
                return "You are a clarification assistant."
            else:
                return "Please analyze the user request."
        return "Mock prompt"

async def main():
    # Monkey patch the prompt engine
    import workflow_agent.agents.nodes
    workflow_agent.agents.nodes.get_prompt_engine = lambda: MockPromptEngine()
    
    result = await test_clarification_complete()
    
    if result:
        print("\n🎉 Test passed!")
    else:
        print("\n😞 Test failed!")

if __name__ == "__main__":
    asyncio.run(main())