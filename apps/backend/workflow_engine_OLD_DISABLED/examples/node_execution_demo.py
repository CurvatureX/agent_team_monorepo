#!/usr/bin/env python3
"""
Node Execution Demo

This script demonstrates the functionality of all 8 node executor types
in the workflow engine.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add the parent directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent))

from shared.models.node_enums import (
    ActionSubtype,
    AIAgentSubtype,
    ExternalActionSubtype,
    FlowSubtype,
    HumanLoopSubtype,
    MemorySubtype,
    NodeType,
    ToolSubtype,
    TriggerSubtype,
)
from workflow_engine.execution_engine import WorkflowExecutionEngine
from workflow_engine.nodes.base import NodeExecutionContext
from workflow_engine.nodes.factory import get_node_executor_factory, register_default_executors


def create_mock_node(
    node_id: str, node_type: str, subtype: str, parameters: dict = None, credentials: dict = None
):
    """Create a mock node object for testing."""

    class MockNode:
        def __init__(self, id, type, subtype, parameters, credentials):
            self.id = id
            self.name = f"{type} - {subtype}"
            self.type = type
            self.subtype = subtype
            self.parameters = parameters or {}
            self.credentials = credentials or {}
            self.disabled = False
            self.on_error = "STOP_WORKFLOW_ON_ERROR"

    return MockNode(node_id, node_type, subtype, parameters, credentials)


def demo_trigger_node():
    """Demo trigger node executor."""
    print("\n" + "=" * 50)
    print("TRIGGER NODE EXECUTOR DEMO")
    print("=" * 50)

    factory = get_node_executor_factory()
    executor = factory.get_executor(NodeType.TRIGGER.value)

    # Test different trigger types
    trigger_types = [
        (TriggerSubtype.MANUAL.value, {}, {"input": "Manual trigger test"}),
        (
            TriggerSubtype.WEBHOOK.value,
            {"webhook_url": "https://api.example.com/webhook", "method": "POST"},
            {"webhook_payload": {"data": "test"}},
        ),
        (TriggerSubtype.CRON.value, {"cron_expression": "0 9 * * *"}, {}),
        (
            TriggerSubtype.SLACK.value,
            {"platform": "slack", "channel": "#general"},
            {"message": {"text": "Hello from workflow!"}},
        ),
        (
            TriggerSubtype.EMAIL.value,
            {"email_address": "test@example.com", "subject_filter": "workflow"},
            {"email": {"subject": "Test Email"}},
        ),
        (
            TriggerSubtype.MANUAL.value,
            {"form_fields": ["name", "email"]},
            {"form_submission": {"name": "John", "email": "john@example.com"}},
        ),
        (
            TriggerSubtype.MANUAL.value,
            {"calendar_id": "primary", "event_type": "meeting"},
            {"calendar_event": {"title": "Team Meeting"}},
        ),
    ]

    for subtype, parameters, input_data in trigger_types:
        print(f"\n--- Testing {subtype} Trigger ---")

        node = create_mock_node("trigger-1", NodeType.TRIGGER.value, subtype, parameters)
        context = NodeExecutionContext(
            node=node,
            workflow_id="demo-workflow",
            execution_id="demo-exec-1",
            input_data=input_data,
            static_data={},
            credentials={},
            metadata={},
        )

        result = executor.execute(context)
        print(f"Status: {result.status.value}")
        print(f"Output: {json.dumps(result.output_data, indent=2)}")
        if result.logs:
            print(f"Logs: {result.logs}")


def demo_ai_agent_node():
    """Demo AI agent node executor."""
    print("\n" + "=" * 50)
    print("AI AGENT NODE EXECUTOR DEMO")
    print("=" * 50)

    factory = get_node_executor_factory()
    executor = factory.get_executor(NodeType.AI_AGENT.value)

    # Test different AI agent types
    agent_types = [
        (
            AIAgentSubtype.OPENAI_CHATGPT.value,
            {
                "model_provider": "openai",
                "model_name": "gpt-5-nano",
                "system_prompt": "You are a routing agent that analyzes user requests and routes them to appropriate flows.",
                "routing_rules": [
                    {
                        "name": "calendar",
                        "keywords": ["meeting", "schedule"],
                        "route": "calendar_flow",
                    },
                    {"name": "email", "keywords": ["email", "send"], "route": "email_flow"},
                ],
            },
            {"text": "Schedule a meeting with John tomorrow", "intent": "calendar"},
        ),
        (
            AIAgentSubtype.OPENAI_CHATGPT.value,
            {
                "model_provider": "openai",
                "model_name": "gpt-5-nano",
                "system_prompt": "You are a task analyzer that performs sentiment analysis on text.",
                "analysis_type": "sentiment",
            },
            {"text": "This is a great project and I'm excited to work on it!"},
        ),
        (
            AIAgentSubtype.OPENAI_CHATGPT.value,
            {
                "model_provider": "openai",
                "model_name": "gpt-5-nano",
                "system_prompt": "You are a data integration specialist that merges data from multiple sources.",
                "data_sources": ["database", "api", "file"],
                "integration_rules": [{"rule": "merge_by_id"}],
            },
            {"data": [{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}]},
        ),
        (
            AIAgentSubtype.OPENAI_CHATGPT.value,
            {
                "model_provider": "openai",
                "model_name": "gpt-5-nano",
                "system_prompt": "You are a report generator that creates comprehensive reports from data metrics.",
                "report_template": "weekly_summary",
                "output_format": "markdown",
            },
            {"metrics": {"users": 150, "revenue": 5000}},
        ),
    ]

    for subtype, parameters, input_data in agent_types:
        print(f"\n--- Testing {subtype} AI Agent ---")

        node = create_mock_node("ai-agent-1", NodeType.AI_AGENT.value, subtype, parameters)
        context = NodeExecutionContext(
            node=node,
            workflow_id="demo-workflow",
            execution_id="demo-exec-1",
            input_data=input_data,
            static_data={},
            credentials={},
            metadata={},
        )

        result = executor.execute(context)
        print(f"Status: {result.status.value}")
        print(f"Output: {json.dumps(result.output_data, indent=2)}")


def demo_external_action_node():
    """Demo external action node executor."""
    print("\n" + "=" * 50)
    print("EXTERNAL ACTION NODE EXECUTOR DEMO")
    print("=" * 50)

    factory = get_node_executor_factory()
    executor = factory.get_executor(NodeType.EXTERNAL_ACTION.value)

    # Test different external actions
    action_types = [
        (
            "GITHUB",
            {"action": "create_issue", "repository": "user/repo"},
            {"title": "Bug Report", "body": "Found a bug in the system"},
        ),
        (
            "GOOGLE_CALENDAR",
            {"action": "create_event", "calendar_id": "primary"},
            {"title": "Team Meeting", "start_time": "2024-01-15T10:00:00Z", "duration": 60},
        ),
        (
            "TRELLO",
            {"action": "create_card", "board_id": "board123"},
            {"title": "New Task", "description": "Task description", "list_id": "todo"},
        ),
        (
            ExternalActionSubtype.EMAIL.value,
            {"action": "send_email", "recipient": "user@example.com"},
            {"subject": "Test Email", "body": "Hello from workflow!"},
        ),
        (
            "SLACK",
            {"action": "send_message", "channel": "#general"},
            {"message": "Hello from workflow!"},
        ),
        (
            "API_CALL",
            {
                "url": "https://api.example.com/data",
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
            },
            {"request_data": {"key": "value"}},
        ),
    ]

    for subtype, parameters, input_data in action_types:
        print(f"\n--- Testing {subtype} External Action ---")

        node = create_mock_node(
            "external-action-1", NodeType.EXTERNAL_ACTION.value, subtype, parameters
        )
        context = NodeExecutionContext(
            node=node,
            workflow_id="demo-workflow",
            execution_id="demo-exec-1",
            input_data=input_data,
            static_data={},
            credentials={},
            metadata={},
        )

        result = executor.execute(context)
        print(f"Status: {result.status.value}")
        print(f"Output: {json.dumps(result.output_data, indent=2)}")


def demo_action_node():
    """Demo action node executor."""
    print("\n" + "=" * 50)
    print("ACTION NODE EXECUTOR DEMO")
    print("=" * 50)

    factory = get_node_executor_factory()
    executor = factory.get_executor(NodeType.ACTION.value)

    # Test different action types
    action_types = [
        (
            ActionSubtype.RUN_CODE.value,
            {
                "language": "python",
                "code": "print('Hello from Python!')\nresult = 42",
                "timeout": 30,
            },
            {"variables": {"x": 10, "y": 20}},
        ),
        (
            ActionSubtype.HTTP_REQUEST.value,
            {
                "url": "https://api.example.com/data",
                "method": "GET",
                "headers": {"Authorization": "Bearer token"},
            },
            {"request_data": {"query": "test"}},
        ),
        (
            ActionSubtype.DATA_TRANSFORMATION.value,
            {"transformation_type": "json_to_csv"},
            {"data": [{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}]},
        ),
        (
            "FILE_OPERATION",
            {"operation": "write", "file_path": "/tmp/test.txt"},
            {"content": "Hello, World!"},
        ),
    ]

    for subtype, parameters, input_data in action_types:
        print(f"\n--- Testing {subtype} Action ---")

        node = create_mock_node("action-1", NodeType.ACTION.value, subtype, parameters)
        context = NodeExecutionContext(
            node=node,
            workflow_id="demo-workflow",
            execution_id="demo-exec-1",
            input_data=input_data,
            static_data={},
            credentials={},
            metadata={},
        )

        result = executor.execute(context)
        print(f"Status: {result.status.value}")
        print(f"Output: {json.dumps(result.output_data, indent=2)}")


def demo_flow_node():
    """Demo flow node executor."""
    print("\n" + "=" * 50)
    print("FLOW NODE EXECUTOR DEMO")
    print("=" * 50)

    factory = get_node_executor_factory()
    executor = factory.get_executor(NodeType.FLOW.value)

    # Test different flow types
    flow_types = [
        ("IF", {"condition": "value > 10"}, {"value": 15}),
        (
            "FILTER",
            {"filter_condition": {"status": "active"}},
            [{"id": 1, "status": "active"}, {"id": 2, "status": "inactive"}],
        ),
        (
            "LOOP",
            {"loop_type": "for_each", "max_iterations": 5},
            {"items": ["item1", "item2", "item3"]},
        ),
        ("MERGE", {"merge_strategy": "combine"}, {"data1": {"a": 1}, "data2": {"b": 2}}),
        (
            "SWITCH",
            {
                "switch_cases": [
                    {"value": "option1", "route": "path1"},
                    {"value": "option2", "route": "path2"},
                    {"is_default": True, "route": "default"},
                ]
            },
            {"switch_value": "option1"},
        ),
        ("WAIT", {"wait_type": "time", "duration": 5}, {}),
    ]

    for subtype, parameters, input_data in flow_types:
        print(f"\n--- Testing {subtype} Flow Control ---")

        node = create_mock_node("flow-1", NodeType.FLOW.value, subtype, parameters)
        context = NodeExecutionContext(
            node=node,
            workflow_id="demo-workflow",
            execution_id="demo-exec-1",
            input_data=input_data,
            static_data={},
            credentials={},
            metadata={},
        )

        result = executor.execute(context)
        print(f"Status: {result.status.value}")
        print(f"Output: {json.dumps(result.output_data, indent=2)}")


def demo_human_loop_node():
    """Demo human-in-the-loop node executor."""
    print("\n" + "=" * 50)
    print("HUMAN-IN-THE-LOOP NODE EXECUTOR DEMO")
    print("=" * 50)

    factory = get_node_executor_factory()
    executor = factory.get_executor(NodeType.HUMAN_IN_THE_LOOP.value)

    # Test different human interaction types
    interaction_types = [
        (
            "GMAIL",
            {
                "recipient_email": "approver@example.com",
                "subject": "Approval Required",
                "timeout_hours": 24,
            },
            {"approval_data": {"amount": 1000, "purpose": "Equipment purchase"}},
        ),
        (
            "SLACK",
            {
                "channel": "#approvals",
                "message": "Please approve this request",
                "timeout_minutes": 60,
            },
            {"request_data": {"type": "budget_approval"}},
        ),
        (
            "DISCORD",
            {"channel_id": "123456789", "message": "Review needed", "timeout_minutes": 30},
            {"review_data": {"document": "proposal.pdf"}},
        ),
        (
            "TELEGRAM",
            {"chat_id": "987654321", "message": "Urgent approval needed", "timeout_minutes": 15},
            {"urgent_data": {"priority": "high"}},
        ),
        (
            "APP",
            {"interaction_type": "approval", "timeout_minutes": 30},
            {"approval_request": {"title": "Budget Approval", "amount": 5000}},
        ),
    ]

    for subtype, parameters, input_data in interaction_types:
        print(f"\n--- Testing {subtype} Human Interaction ---")

        node = create_mock_node(
            "human-loop-1", NodeType.HUMAN_IN_THE_LOOP.value, subtype, parameters
        )
        context = NodeExecutionContext(
            node=node,
            workflow_id="demo-workflow",
            execution_id="demo-exec-1",
            input_data=input_data,
            static_data={},
            credentials={},
            metadata={},
        )

        result = executor.execute(context)
        print(f"Status: {result.status.value}")
        print(f"Output: {json.dumps(result.output_data, indent=2)}")


def demo_tool_node():
    """Demo tool node executor."""
    print("\n" + "=" * 50)
    print("TOOL NODE EXECUTOR DEMO")
    print("=" * 50)

    factory = get_node_executor_factory()
    executor = factory.get_executor(NodeType.TOOL.value)

    # Test different tool types
    tool_types = [
        (
            "MCP",
            {
                "tool_name": "file_system",
                "tool_action": "read_file",
                "tool_parameters": {"file_path": "/path/to/file.txt"},
            },
            {},
        ),
        (
            "CALENDAR",
            {"calendar_provider": "google", "action": "create_event"},
            {"title": "Meeting", "start_time": "2024-01-15T10:00:00Z", "duration": 60},
        ),
        (
            ExternalActionSubtype.EMAIL.value,
            {"email_provider": "gmail", "action": "send_email"},
            {"recipient": "user@example.com", "subject": "Test", "body": "Hello!"},
        ),
        (
            "HTTP",
            {
                "url": "https://api.example.com/data",
                "method": "GET",
                "headers": {"Authorization": "Bearer token"},
            },
            {"query": "test"},
        ),
    ]

    for subtype, parameters, input_data in tool_types:
        print(f"\n--- Testing {subtype} Tool ---")

        node = create_mock_node("tool-1", NodeType.TOOL.value, subtype, parameters)
        context = NodeExecutionContext(
            node=node,
            workflow_id="demo-workflow",
            execution_id="demo-exec-1",
            input_data=input_data,
            static_data={},
            credentials={},
            metadata={},
        )

        result = executor.execute(context)
        print(f"Status: {result.status.value}")
        print(f"Output: {json.dumps(result.output_data, indent=2)}")


def demo_memory_node():
    """Demo memory node executor."""
    print("\n" + "=" * 50)
    print("MEMORY NODE EXECUTOR DEMO")
    print("=" * 50)

    factory = get_node_executor_factory()
    executor = factory.get_executor(NodeType.MEMORY.value)

    # Test different memory types
    memory_types = [
        (
            "SIMPLE_STORAGE",
            {"operation": "store", "key": "user_data", "ttl": 3600},
            {"value": {"name": "John", "age": 30}},
        ),
        (
            "BUFFER",
            {"operation": "push", "buffer_name": "message_queue", "buffer_size": 100},
            {"item": {"message": "Hello", "timestamp": "2024-01-15T10:00:00Z"}},
        ),
        (
            "KNOWLEDGE_GRAPH",
            {"operation": "add_node"},
            {
                "node_id": "person_1",
                "node_type": "person",
                "properties": {"name": "John", "age": 30},
            },
        ),
        (
            "VECTOR_STORE",
            {"operation": "store", "collection_name": "documents"},
            {
                "vector_id": "doc_1",
                "vector": [0.1, 0.2, 0.3],
                "metadata": {"text": "Sample document"},
            },
        ),
        (
            "DOCUMENT_STORAGE",
            {"operation": "store", "document_id": "doc_123"},
            {
                "content": "This is a sample document",
                "document_type": "text",
                "metadata": {"author": "John"},
            },
        ),
        (
            "EMBEDDINGS",
            {"operation": "generate", "model_name": "text-embedding-ada-002"},
            {"text": "This is a sample text to embed"},
        ),
    ]

    for subtype, parameters, input_data in memory_types:
        print(f"\n--- Testing {subtype} Memory Operation ---")

        node = create_mock_node("memory-1", NodeType.MEMORY.value, subtype, parameters)
        context = NodeExecutionContext(
            node=node,
            workflow_id="demo-workflow",
            execution_id="demo-exec-1",
            input_data=input_data,
            static_data={},
            credentials={},
            metadata={},
        )

        result = executor.execute(context)
        print(f"Status: {result.status.value}")
        print(f"Output: {json.dumps(result.output_data, indent=2)}")


def demo_workflow_execution():
    """Demo complete workflow execution."""
    print("\n" + "=" * 50)
    print("COMPLETE WORKFLOW EXECUTION DEMO")
    print("=" * 50)

    # Create a sample workflow definition
    workflow_definition = {
        "id": "demo-workflow",
        "name": "Demo Workflow",
        "nodes": [
            {
                "id": "trigger-1",
                "name": "Manual Trigger",
                "type": NodeType.TRIGGER.value,
                "subtype": TriggerSubtype.MANUAL.value,
                "parameters": {},
                "credentials": {},
            },
            {
                "id": "ai-agent-1",
                "name": "Router Agent",
                "type": NodeType.AI_AGENT.value,
                "subtype": AIAgentSubtype.OPENAI_CHATGPT.value,
                "parameters": {
                    "model_provider": "openai",
                    "model_name": "gpt-5-nano",
                    "routing_rules": [
                        {
                            "name": "calendar",
                            "keywords": ["meeting", "schedule"],
                            "route": "calendar_flow",
                        }
                    ],
                },
                "credentials": {},
            },
            {
                "id": "action-1",
                "name": "Data Transformation",
                "type": NodeType.ACTION.value,
                "subtype": ActionSubtype.DATA_TRANSFORMATION.value,
                "parameters": {"transformation_type": "filter"},
                "credentials": {},
            },
        ],
        "connections": [
            {"source": "trigger-1", "target": "ai-agent-1"},
            {"source": "ai-agent-1", "target": "action-1"},
        ],
        "static_data": {},
    }

    # Execute the workflow
    engine = WorkflowExecutionEngine()

    initial_data = {
        "text": "Schedule a meeting with the team tomorrow at 2 PM",
        "user_id": "user123",
    }

    result = engine.execute_workflow(
        workflow_id="demo-workflow",
        execution_id="demo-exec-001",
        workflow_definition=workflow_definition,
        initial_data=initial_data,
        credentials={},
    )

    print(f"Workflow Status: {result['status']}")
    print(f"Execution Order: {result['execution_order']}")
    print(f"Node Results:")
    for node_id, node_result in result["node_results"].items():
        print(f"  {node_id}: {node_result['status']}")

    if result["errors"]:
        print(f"Errors: {result['errors']}")


def main():
    """Main demo function."""
    print("WORKFLOW ENGINE NODE EXECUTORS DEMO")
    print("=" * 60)
    print(f"Demo started at: {datetime.now()}")

    # Register all executors
    register_default_executors()

    # Run all demos
    demo_trigger_node()
    demo_ai_agent_node()
    demo_external_action_node()
    demo_action_node()
    demo_flow_node()
    demo_human_loop_node()
    demo_tool_node()
    demo_memory_node()
    demo_workflow_execution()

    print("\n" + "=" * 60)
    print("DEMO COMPLETED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    main()
