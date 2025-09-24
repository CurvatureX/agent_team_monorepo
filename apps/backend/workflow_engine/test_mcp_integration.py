#!/usr/bin/env python3
"""
Test script for MCP integration with AI nodes.

This script demonstrates how to test the connection between AI nodes and TOOL nodes
for MCP function calling capabilities.
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict

# Add the current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from nodes.ai_agent_node import AIAgentNodeExecutor
from nodes.base import NodeExecutionContext
from nodes.tool_node import ToolNodeExecutor

from shared.models.node_enums import AIAgentSubtype


def create_test_context(
    node_id: str, parameters: Dict[str, Any], input_data: Dict[str, Any] = None
) -> NodeExecutionContext:
    """Create a test execution context."""
    return NodeExecutionContext(
        workflow_id="test-workflow-001",
        execution_id="test-execution-001",
        node_id=node_id,
        parameters=parameters,
        input_data=input_data or {},
        metadata={
            "workflow_connections": {
                "ai_agent_1": {
                    "connection_types": {
                        "mcp_tools": {"connections": [{"node": "mcp_tool_1", "port": "mcp_tools"}]}
                    }
                }
            },
            "workflow_nodes": [
                {
                    "id": "ai_agent_1",
                    "type": "AI_AGENT",
                    "name": "Test AI Agent",
                    "subtype": "OPENAI_CHATGPT",
                },
                {
                    "id": "mcp_tool_1",
                    "type": "TOOL",
                    "name": "Test MCP Tool",
                    "subtype": "MCP_TOOL",
                },
            ],
            "node_id": node_id,
        },
    )


async def test_tool_node_discovery():
    """Test TOOL node MCP function discovery."""
    print("🔧 Testing TOOL node MCP function discovery...")

    tool_executor = ToolNodeExecutor(subtype="MCP_TOOL")
    context = create_test_context(
        "mcp_tool_1", {"tool_type": "mcp", "operation": "discover"}, {"operation": "discover"}
    )

    try:
        # Test function discovery
        functions = await tool_executor.handle_function_discovery(context)

        print(f"✅ Discovery completed. Found {len(functions)} functions:")
        for i, func in enumerate(functions):
            if isinstance(func, dict) and "function" in func:
                func_name = func["function"].get("name", "unknown")
                func_desc = func["function"].get("description", "")
                print(f"  {i+1}. {func_name}: {func_desc}")

        return functions

    except Exception as e:
        print(f"❌ TOOL node discovery failed: {e}")
        return []


async def test_tool_node_execution():
    """Test TOOL node MCP function execution."""
    print("\n🔧 Testing TOOL node MCP function execution...")

    tool_executor = ToolNodeExecutor(subtype="MCP_TOOL")
    context = create_test_context(
        "mcp_tool_1",
        {"tool_type": "mcp", "operation": "execute"},
        {"operation": "execute", "function_name": "get_node_types", "function_args": {}},
    )

    try:
        # Test function execution
        result = await tool_executor.handle_function_execution(context, "get_node_types", {})

        print(f"✅ Function execution completed:")
        print(f"  Result keys: {list(result.keys()) if isinstance(result, dict) else type(result)}")
        if isinstance(result, dict) and "node_types" in result:
            print(f"  Found {len(result.get('node_types', []))} node types")

        return result

    except Exception as e:
        print(f"❌ TOOL node execution failed: {e}")
        return {}


async def test_ai_node_with_mcp():
    """Test AI node with MCP function calling."""
    print("\n🤖 Testing AI node with MCP integration...")

    # Skip actual AI call if API key not available
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️ OPENAI_API_KEY not set, skipping AI integration test")
        return

    ai_executor = AIAgentNodeExecutor(subtype=AIAgentSubtype.OPENAI_CHATGPT.value)
    context = create_test_context(
        "ai_agent_1",
        {
            "system_prompt": "You are a helpful assistant with access to workflow node information tools.",
            "enable_function_calling": True,
            "max_function_calls": 2,
        },
        {
            "message": "What types of nodes are available in this workflow system? Please use the available tools to find out."
        },
    )

    try:
        # Test AI execution with MCP tools
        result = await ai_executor.execute(context)

        print(f"✅ AI execution completed:")
        print(f"  Status: {result.status}")
        if result.output_data:
            response = result.output_data.get("response", "")
            print(f"  Response length: {len(response)} characters")
            print(f"  Response preview: {response[:200]}...")

        return result

    except Exception as e:
        print(f"❌ AI node execution failed: {e}")
        return None


async def test_workflow_integration():
    """Test complete workflow integration."""
    print("\n🔗 Testing complete workflow integration...")

    # This would test a full workflow execution with AI→TOOL connections
    # For now, we'll test the individual components

    print("1. Testing TOOL node discovery...")
    functions = await test_tool_node_discovery()

    print("\n2. Testing TOOL node execution...")
    result = await test_tool_node_execution()

    print("\n3. Testing AI node integration...")
    ai_result = await test_ai_node_with_mcp()

    print(f"\n📊 Integration Test Summary:")
    print(f"  Functions discovered: {len(functions)}")
    print(f"  Tool execution: {'✅' if result else '❌'}")
    print(f"  AI integration: {'✅' if ai_result else '⚠️'}")


async def main():
    """Run all MCP integration tests."""
    print("🚀 Starting MCP Integration Tests")
    print("=" * 50)

    try:
        await test_workflow_integration()

        print("\n" + "=" * 50)
        print("✅ MCP Integration Tests Completed!")

    except Exception as e:
        print(f"\n❌ Integration tests failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
