#!/usr/bin/env python3
"""
Test the enhanced parameter validation directly using node executors.
"""

import asyncio

from nodes.ai_agent_node import AIAgentNodeExecutor
from nodes.base import NodeExecutionContext


async def test_ai_node_parameter_validation():
    """Test AI node parameter validation with missing parameters"""
    print("🧪 Testing AI Node Parameter Validation")
    print("=" * 50)

    # Create AI Agent Node Executor
    ai_executor = AIAgentNodeExecutor()

    # Test Case 1: Missing both required parameters
    print("\n📝 Test Case 1: Missing both system_prompt and user_message")
    context1 = NodeExecutionContext(
        workflow_id="test-workflow-id",
        execution_id="test-execution-id",
        node_id="ai_node_1",
        parameters={
            "name": "Test AI Node",
            "model_version": "gpt-4"
            # Missing: system_prompt, user_message
        },
    )

    result1 = await ai_executor.execute_with_logging(context1)
    print(f"Status: {result1.status.value}")
    print(f"Error: {result1.error_message}")
    print()

    # Test Case 2: Missing one required parameter
    print("📝 Test Case 2: Missing user_message only")
    context2 = NodeExecutionContext(
        workflow_id="test-workflow-id",
        execution_id="test-execution-id-2",
        node_id="ai_node_2",
        parameters={
            "name": "Test AI Node 2",
            "model_version": "gpt-4",
            "system_prompt": "You are a helpful assistant"
            # Missing: user_message
        },
    )

    result2 = await ai_executor.execute_with_logging(context2)
    print(f"Status: {result2.status.value}")
    print(f"Error: {result2.error_message}")
    print()

    # Test Case 3: All required parameters present (should succeed)
    print("📝 Test Case 3: All required parameters present")
    context3 = NodeExecutionContext(
        workflow_id="test-workflow-id",
        execution_id="test-execution-id-3",
        node_id="ai_node_3",
        parameters={
            "name": "Test AI Node 3",
            "model_version": "gpt-4",
            "system_prompt": "You are a helpful assistant",
            "user_message": "Hello, how are you?",
        },
    )

    result3 = await ai_executor.execute_with_logging(context3)
    print(f"Status: {result3.status.value}")
    if result3.status.value == "success":
        print(f"Response: {result3.output_data.get('response', 'No response')}")
    else:
        print(f"Error: {result3.error_message}")
    print()


if __name__ == "__main__":
    asyncio.run(test_ai_node_parameter_validation())
