#!/usr/bin/env python3

"""
Test script to verify that consultant_node generates AI questions in negotiation_history
This specifically addresses the issue where capability_gaps is empty
"""

import asyncio

import structlog

from agents.workflow_agent import WorkflowAgent

logger = structlog.get_logger()


async def test_consultant_question_generation():
    """Test that consultant phase generates questions when capability_gaps is empty"""
    print("🧪 Testing consultant question generation...")

    # Initialize workflow agent
    try:
        agent = WorkflowAgent()
    except Exception as e:
        print(f"⚠️  Failed to initialize WorkflowAgent (likely missing API key): {e}")
        print("📝 This test requires OpenAI API key to be set in environment variables")
        print("💡 Try setting OPENAI_API_KEY environment variable and run again")
        return False

    # Test with a simple input that should trigger requirement-based questions
    test_input = "我想自动化我的邮件工作流程"

    # Create initial state
    initial_state = {
        "user_input": test_input,
        "current_step": "consultant_phase",
        "stage": "consultant",
        "should_continue": True,
        "metadata": {"session_id": "test_consultant_session", "user_id": "test_user"},
        "requirement_negotiation": {
            "negotiation_history": [],
            "capability_analysis": {
                "capability_gaps": []  # Empty gaps to trigger requirement-based questions
            },
        },
    }

    print(f"📝 Initial input: {test_input}")
    print(
        f"🔍 Initial capability_gaps: {initial_state['requirement_negotiation']['capability_analysis']['capability_gaps']}"
    )

    # Run consultant phase
    try:
        result = await agent._consultant_phase_node(initial_state)

        print(f"✅ Consultant phase completed")
        print(f"📊 Result keys: {list(result.keys())}")

        # Check if AI questions were generated
        negotiation_history = result.get("negotiation_history", [])
        print(f"💬 Negotiation history length: {len(negotiation_history)}")

        for i, message in enumerate(negotiation_history):
            print(
                f"   Message {i+1}: role={message.get('role')}, type={message.get('type', 'N/A')}"
            )
            if message.get("role") == "assistant":
                print(f"   Content: {message.get('content', '')[:100]}...")

        # Check if AI message was generated
        ai_message = result.get("ai_message", "")
        print(f"🤖 AI message: {ai_message[:100]}...")

        # Verify consultant phase behavior
        waiting_for_user = result.get("waiting_for_user", False)
        print(f"⏳ Waiting for user: {waiting_for_user}")

        current_step = result.get("current_step", "")
        print(f"📍 Current step: {current_step}")

        # Success criteria
        has_ai_questions = any(
            msg.get("role") == "assistant" and msg.get("type") == "clarification_questions"
            for msg in negotiation_history
        )

        print(f"\n📋 Test Results:")
        print(f"   ✓ Has AI questions in history: {has_ai_questions}")
        print(f"   ✓ Waiting for user response: {waiting_for_user}")
        print(f"   ✓ AI message generated: {bool(ai_message)}")

        if has_ai_questions and waiting_for_user and ai_message:
            print("🎉 SUCCESS: Consultant phase is generating AI questions correctly!")
            return True
        else:
            print("❌ FAILURE: Consultant phase is not generating questions as expected")
            return False

    except Exception as e:
        print(f"❌ ERROR during consultant phase: {e}")
        logger.error("Consultant phase test failed", error=str(e))
        return False


async def main():
    """Main test function"""
    print("🚀 Starting consultant question generation test\n")

    success = await test_consultant_question_generation()

    if success:
        print("\n✅ All tests passed! Consultant phase is working correctly.")
    else:
        print("\n❌ Tests failed! Check the consultant phase implementation.")

    return success


if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)
