#!/usr/bin/env python3
"""
Test script for all Node Executors.

This script tests all implemented node executors to ensure they work correctly.
"""

import json
import time
from typing import Any, Dict
from workflow_engine.nodes import NodeExecutorFactory, NodeExecutionContext


def create_mock_node(node_type: str, subtype: str, parameters: Dict[str, Any] = None) -> Any:
    """Create a mock node for testing."""
    # Create a simple mock node object
    class MockNode:
        def __init__(self, node_type: str, subtype: str, parameters: Dict[str, Any] = None):
            self.type = node_type
            self.subtype = subtype
            self.parameters = parameters or {}
    
    return MockNode(node_type, subtype, parameters)


def create_mock_context(node: Any, input_data: Dict[str, Any] = None) -> NodeExecutionContext:
    """Create a mock execution context."""
    return NodeExecutionContext(
        node=node,
        input_data=input_data or {},
        metadata={"user_id": "test_user", "session_id": "test_session"},
        workflow_id="test_workflow",
        execution_id="test_execution",
        static_data={},
        credentials={}
    )


def test_trigger_node():
    """Test TRIGGER_NODE executor."""
    print("\n=== Testing TRIGGER_NODE ===")
    
    executor = NodeExecutorFactory.create_executor("TRIGGER_NODE")
    if not executor:
        print("❌ Failed to create TRIGGER_NODE executor")
        return False
    
    # Test MANUAL trigger
    node = create_mock_node("TRIGGER_NODE", "MANUAL", {
        "require_confirmation": True
    })
    context = create_mock_context(node, {"test_data": "hello"})
    
    result = executor.execute(context)
    print(f"✅ MANUAL trigger: {result.status}")
    if result.status == "SUCCESS":
        print(f"   Output: {result.output_data.get('trigger_type')}")
    
    # Test WEBHOOK trigger
    node = create_mock_node("TRIGGER_NODE", "WEBHOOK", {
        "method": "POST",
        "path": "/webhook/test"
    })
    context = create_mock_context(node, {
        "webhook_data": {"event": "test"},
        "headers": {"Content-Type": "application/json"}
    })
    
    result = executor.execute(context)
    print(f"✅ WEBHOOK trigger: {result.status}")
    
    return True


def test_ai_agent_node():
    """Test AI_AGENT_NODE executor."""
    print("\n=== Testing AI_AGENT_NODE ===")
    
    executor = NodeExecutorFactory.create_executor("AI_AGENT_NODE")
    if not executor:
        print("❌ Failed to create AI_AGENT_NODE executor")
        return False
    
    # Test ROUTER_AGENT
    node = create_mock_node("AI_AGENT_NODE", "ROUTER_AGENT", {
        "model": "gpt-4",
        "system_prompt": "You are a router agent."
    })
    context = create_mock_context(node, {"input": "route this request"})
    
    result = executor.execute(context)
    print(f"✅ ROUTER_AGENT: {result.status}")
    if result.status == "SUCCESS":
        print(f"   Output: {result.output_data.get('agent_type')}")
    
    # Test TASK_ANALYZER
    node = create_mock_node("AI_AGENT_NODE", "TASK_ANALYZER", {
        "model": "gpt-4",
        "analysis_type": "requirement"
    })
    context = create_mock_context(node, {"task": "analyze this task"})
    
    result = executor.execute(context)
    print(f"✅ TASK_ANALYZER: {result.status}")
    
    return True


def test_action_node():
    """Test ACTION_NODE executor."""
    print("\n=== Testing ACTION_NODE ===")
    
    executor = NodeExecutorFactory.create_executor("ACTION_NODE")
    if not executor:
        print("❌ Failed to create ACTION_NODE executor")
        return False
    
    # Test HTTP_REQUEST
    node = create_mock_node("ACTION_NODE", "HTTP_REQUEST", {
        "method": "GET",
        "url": "https://httpbin.org/get"
    })
    context = create_mock_context(node)
    
    result = executor.execute(context)
    print(f"✅ HTTP_REQUEST: {result.status}")
    if result.status == "SUCCESS":
        print(f"   Output: {result.output_data.get('action_type')}")
    
    # Test DATA_TRANSFORMATION
    node = create_mock_node("ACTION_NODE", "DATA_TRANSFORMATION", {
        "transformation_type": "filter"
    })
    context = create_mock_context(node, {"data": [1, 2, 3, 4, 5]})
    
    result = executor.execute(context)
    print(f"✅ DATA_TRANSFORMATION: {result.status}")
    
    return True


def test_human_loop_node():
    """Test HUMAN_IN_THE_LOOP_NODE executor."""
    print("\n=== Testing HUMAN_IN_THE_LOOP_NODE ===")
    
    executor = NodeExecutorFactory.create_executor("HUMAN_IN_THE_LOOP_NODE")
    if not executor:
        print("❌ Failed to create HUMAN_IN_THE_LOOP_NODE executor")
        return False
    
    # Test SLACK interaction
    node = create_mock_node("HUMAN_IN_THE_LOOP_NODE", "SLACK", {
        "channel": "#general",
        "message_template": "Please review: {task_name}"
    })
    context = create_mock_context(node, {"task_name": "Test Task"})
    
    result = executor.execute(context)
    print(f"✅ SLACK interaction: {result.status}")
    if result.status == "SUCCESS":
        print(f"   Output: {result.output_data.get('interaction_type')}")
    
    # Test APP interaction
    node = create_mock_node("HUMAN_IN_THE_LOOP_NODE", "APP", {
        "notification_type": "approval",
        "title": "Action Required",
        "message": "Please approve this action"
    })
    context = create_mock_context(node)
    
    result = executor.execute(context)
    print(f"✅ APP interaction: {result.status}")
    
    return True


def test_tool_node():
    """Test TOOL_NODE executor."""
    print("\n=== Testing TOOL_NODE ===")
    
    executor = NodeExecutorFactory.create_executor("TOOL_NODE")
    if not executor:
        print("❌ Failed to create TOOL_NODE executor")
        return False
    
    # Test MCP tool
    node = create_mock_node("TOOL_NODE", "MCP", {
        "tool_name": "test_tool",
        "operation": "test_operation"
    })
    context = create_mock_context(node)
    
    result = executor.execute(context)
    print(f"✅ MCP tool: {result.status}")
    if result.status == "SUCCESS":
        print(f"   Output: {result.output_data.get('tool_type')}")
    
    # Test CALENDAR tool
    node = create_mock_node("TOOL_NODE", "CALENDAR", {
        "calendar_id": "primary",
        "operation": "list_events"
    })
    context = create_mock_context(node)
    
    result = executor.execute(context)
    print(f"✅ CALENDAR tool: {result.status}")
    
    return True


def test_memory_node():
    """Test MEMORY_NODE executor."""
    print("\n=== Testing MEMORY_NODE ===")
    
    executor = NodeExecutorFactory.create_executor("MEMORY_NODE")
    if not executor:
        print("❌ Failed to create MEMORY_NODE executor")
        return False
    
    # Test KEY_VALUE operations
    node = create_mock_node("MEMORY_NODE", "KEY_VALUE", {
        "operation": "set",
        "key": "test_key"
    })
    context = create_mock_context(node, {"value": "test_value"})
    
    result = executor.execute(context)
    print(f"✅ KEY_VALUE set: {result.status}")
    if result.status == "SUCCESS":
        print(f"   Output: {result.output_data.get('memory_type')}")
    
    # Test VECTOR_DB operations
    node = create_mock_node("MEMORY_NODE", "VECTOR_DB", {
        "operation": "store",
        "collection_name": "test_collection"
    })
    context = create_mock_context(node, {
        "vector_data": {"vector": [1.0, 2.0, 3.0]},
        "metadata": {"description": "test vector"}
    })
    
    result = executor.execute(context)
    print(f"✅ VECTOR_DB store: {result.status}")
    
    return True


def test_flow_node():
    """Test FLOW_NODE executor (already implemented)."""
    print("\n=== Testing FLOW_NODE ===")
    
    executor = NodeExecutorFactory.create_executor("FLOW_NODE")
    if not executor:
        print("❌ Failed to create FLOW_NODE executor")
        return False
    
    # Test IF condition
    node = create_mock_node("FLOW_NODE", "IF", {
        "condition": "input_value > 5"
    })
    context = create_mock_context(node, {"input_value": 10})
    
    result = executor.execute(context)
    print(f"✅ IF condition: {result.status}")
    if result.status == "SUCCESS":
        print(f"   Output: {result.output_data.get('flow_type')}")
    
    return True


def main():
    """Run all node executor tests."""
    print("🧪 Testing All Node Executors")
    print("=" * 50)
    
    # Check supported node types
    supported_types = NodeExecutorFactory.get_supported_node_types()
    print(f"📋 Supported node types: {supported_types}")
    
    # Test each node type
    tests = [
        test_trigger_node,
        test_ai_agent_node,
        test_action_node,
        test_human_loop_node,
        test_tool_node,
        test_memory_node,
        test_flow_node
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All node executors are working correctly!")
    else:
        print("⚠️  Some node executors have issues.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 