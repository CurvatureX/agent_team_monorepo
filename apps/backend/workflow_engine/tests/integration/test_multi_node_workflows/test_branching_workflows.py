from typing import Any, Dict

import pytest

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
from workflow_engine.tests.integration.utils.assertions import (
    assert_execution_success_status,
    assert_log_contains,
)
from workflow_engine.tests.integration.utils.lifecycle_utils import create_lifecycle_manager
from workflow_engine.tests.integration.utils.workflow_factory import connect, node


@pytest.mark.asyncio
async def test_conditional_branching_if_else(app_client):
    """Test: TRIGGER → FLOW(IF) → [AI_AGENT | ACTION(HTTP)] using real API lifecycle
    Verify: Correct branch taken based on condition"""
    manager = create_lifecycle_manager(app_client)

    try:
        # Create nodes
        trigger = node(
            "n1", NodeType.TRIGGER.value, TriggerSubtype.MANUAL.value, {"trigger_type": "manual"}
        )
        flow_if = node(
            "n2",
            NodeType.FLOW.value,
            FlowSubtype.IF.value,
            {
                "flow_type": "if",
                "condition": "input_data.priority == 'high'",
                "condition_field": "priority",
                "condition_operator": "==",
                "condition_value": "high",
            },
        )
        ai_agent = node(
            "n3",
            NodeType.AI_AGENT.value,
            AIAgentSubtype.OPENAI_CHATGPT.value,
            {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "system_prompt": "You are a high-priority task processor.",
                "user_message": "Process this high-priority request: {{input_data.message}}",
            },
        )
        http_action = node(
            "n4",
            NodeType.ACTION.value,
            ActionSubtype.HTTP_REQUEST.value,
            {
                "action_type": ActionSubtype.HTTP_REQUEST.value,
                "url": "https://httpbin.org/post",
                "method": "POST",
                "payload": '{"message": "{{input_data.message}}", "priority": "low"}',
            },
        )

        # Define workflow with branching connections
        workflow_definition = {
            "id": "wf_branching_if",
            "name": "Conditional Branching Workflow",
            "nodes": [trigger, flow_if, ai_agent, http_action],
            "connections": {
                "n1": [connect("n1", "n2")],  # TRIGGER → FLOW
                "n2": [
                    connect("n2", "n3", output_field="true_path"),  # FLOW → AI_AGENT (true)
                    connect("n2", "n4", output_field="false_path"),  # FLOW → ACTION (false)
                ],
            },
        }

        # Execute complete workflow lifecycle
        workflow_id = await manager.create_workflow(workflow_definition)
        execution_result = await manager.execute_and_wait(
            workflow_id,
            {"priority": "high", "message": "Urgent task"},
            timeout_seconds=60,  # Longer timeout for complex branching workflow
        )

        # Verify execution succeeded
        assert_execution_success_status(execution_result)

        # Clean up
        await manager.delete_workflow(workflow_id)

    except Exception as e:
        # Ensure cleanup on failure
        await manager.cleanup_all()
        raise


@pytest.mark.asyncio
async def test_switch_case_multiple_branches(app_client, patch_workflow_definition, in_memory_logs):
    """Test: TRIGGER → FLOW(SWITCH) → [Multiple branches]
    Verify: Correct case executed based on switch value"""

    # Create nodes
    trigger = node(
        "n1", NodeType.TRIGGER.value, TriggerSubtype.MANUAL.value, {"trigger_type": "manual"}
    )
    flow_switch = node(
        "n2",
        NodeType.FLOW.value,
        FlowSubtype.SWITCH.value,
        {
            "flow_type": "switch",
            "switch_field": "request_type",
            "cases": {
                "email": {"action": "send_email"},
                "slack": {"action": "send_slack"},
                "webhook": {"action": "send_webhook"},
            },
            "default_case": {"action": "log_only"},
        },
    )
    email_action = node(
        "n3",
        NodeType.EXTERNAL_ACTION.value,
        ExternalActionSubtype.EMAIL.value,
        {
            "action_type": ExternalActionSubtype.EMAIL.value,
            "to": "admin@example.com",
            "subject": "Notification",
            "body": "{{input_data.message}}",
        },
    )
    slack_action = node(
        "n4",
        NodeType.EXTERNAL_ACTION.value,
        ExternalActionSubtype.SLACK.value,
        {
            "action_type": ExternalActionSubtype.SLACK.value,
            "channel": "#notifications",
            "message": "{{input_data.message}}",
        },
    )
    webhook_action = node(
        "n5",
        NodeType.EXTERNAL_ACTION.value,
        ExternalActionSubtype.WEBHOOK.value,
        {
            "action_type": ExternalActionSubtype.WEBHOOK.value,
            "url": "https://httpbin.org/post",
            "payload": '{"message": "{{input_data.message}}"}',
        },
    )
    log_action = node(
        "n6",
        NodeType.ACTION.value,
        ActionSubtype.DATA_FORMATTING.value,
        {
            "action_type": ActionSubtype.DATA_FORMATTING.value,
            "message": "Unhandled request type: {{input_data.request_type}}",
        },
    )

    workflow = {
        "id": "wf_switch_case",
        "name": "Switch Case Workflow",
        "nodes": [trigger, flow_switch, email_action, slack_action, webhook_action, log_action],
        "connections": {
            "n1": [connect("n1", "n2")],  # TRIGGER → SWITCH
            "n2": [
                connect("n2", "n3", output_field="email"),
                connect("n2", "n4", output_field="slack"),
                connect("n2", "n5", output_field="webhook"),
                connect("n2", "n6", output_field="default"),
            ],
        },
    }

    patch_workflow_definition(workflow)

    # Test email case
    resp = await app_client.post(
        "/v1/workflows/wf_switch_case/execute",
        json={
            "workflow_id": "wf_switch_case",
            "user_id": "u1",
            "trigger_data": {"request_type": "email", "message": "Test email notification"},
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs show switch execution
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of FLOW node")
    assert_log_contains(logs, "Successfully completed FLOW node")


@pytest.mark.asyncio
async def test_parallel_execution_merge(app_client, patch_workflow_definition, in_memory_logs):
    """Test: TRIGGER → FLOW(SPLIT) → [Parallel paths] → FLOW(MERGE)
    Verify: Parallel execution and data merging"""

    # Create nodes
    trigger = node(
        "n1", NodeType.TRIGGER.value, TriggerSubtype.MANUAL.value, {"trigger_type": "manual"}
    )
    split_flow = node(
        "n2",
        NodeType.FLOW.value,
        FlowSubtype.SPLIT.value,
        {
            "flow_type": "split",
            "split_field": "tasks",
            "split_strategy": "parallel",
            "max_parallel": 3,
        },
    )

    # Parallel processing nodes
    process_a = node(
        "n3",
        NodeType.ACTION.value,
        ActionSubtype.DATA_TRANSFORMATION.value,
        {
            "action_type": ActionSubtype.DATA_TRANSFORMATION.value,
            "transformation_type": "field_mapping",
            "field_mappings": {"input": "output_a"},
        },
    )
    process_b = node(
        "n4",
        NodeType.AI_AGENT.value,
        AIAgentSubtype.OPENAI_CHATGPT.value,
        {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "system_prompt": "Analyze the input data",
            "user_message": "Analyze: {{input_data}}",
        },
    )
    process_c = node(
        "n5",
        NodeType.TOOL.value,
        ToolSubtype.HTTP_CLIENT.value,
        {"tool_type": "utility", "utility_type": "timestamp", "operation": "generate"},
    )

    # Merge node
    merge_flow = node(
        "n6",
        NodeType.FLOW.value,
        FlowSubtype.MERGE.value,
        {
            "flow_type": "merge",
            "merge_strategy": "combine",
            "wait_for_all": True,
            "output_field": "merged_results",
        },
    )

    workflow = {
        "id": "wf_parallel_merge",
        "name": "Parallel Execution with Merge",
        "nodes": [trigger, split_flow, process_a, process_b, process_c, merge_flow],
        "connections": {
            "n1": [connect("n1", "n2")],  # TRIGGER → SPLIT
            "n2": [
                connect("n2", "n3"),  # SPLIT → Process A
                connect("n2", "n4"),  # SPLIT → Process B
                connect("n2", "n5"),  # SPLIT → Process C
            ],
            "n3": [connect("n3", "n6")],  # Process A → MERGE
            "n4": [connect("n4", "n6")],  # Process B → MERGE
            "n5": [connect("n5", "n6")],  # Process C → MERGE
        },
    }

    patch_workflow_definition(workflow)

    resp = await app_client.post(
        "/v1/workflows/wf_parallel_merge/execute",
        json={
            "workflow_id": "wf_parallel_merge",
            "user_id": "u1",
            "trigger_data": {
                "tasks": '["task1", "task2", "task3"]',
                "data": '{"input": "parallel processing test"}',
            },
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs show parallel execution
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of FLOW node")
    assert_log_contains(logs, "Successfully completed FLOW node")


@pytest.mark.asyncio
async def test_conditional_chain_workflow(app_client, patch_workflow_definition, in_memory_logs):
    """Test multiple conditional branches in sequence"""

    # Create nodes for conditional chain
    trigger = node(
        "n1", NodeType.TRIGGER.value, TriggerSubtype.MANUAL.value, {"trigger_type": "manual"}
    )

    # First condition: Check user role
    role_check = node(
        "n2",
        NodeType.FLOW.value,
        FlowSubtype.IF.value,
        {
            "flow_type": "if",
            "condition": "input_data.user_role == 'admin'",
            "condition_field": "user_role",
            "condition_operator": "==",
            "condition_value": "admin",
        },
    )

    # Second condition: Check permission level (only for admins)
    permission_check = node(
        "n3",
        NodeType.FLOW.value,
        FlowSubtype.IF.value,
        {
            "flow_type": "if",
            "condition": "input_data.permission_level >= 5",
            "condition_field": "permission_level",
            "condition_operator": ">=",
            "condition_value": 5,
        },
    )

    # Action for high-permission admins
    admin_action = node(
        "n4",
        NodeType.ACTION.value,
        ActionSubtype.HTTP_REQUEST.value,
        {
            "action_type": ActionSubtype.HTTP_REQUEST.value,
            "url": "https://httpbin.org/post",
            "method": "POST",
            "payload": {"action": "admin_operation", "user": "{{input_data.user_id}}"},
        },
    )

    # Action for low-permission admins
    limited_action = node(
        "n5",
        NodeType.ACTION.value,
        ActionSubtype.DATA_FORMATTING.value,
        {
            "action_type": ActionSubtype.DATA_FORMATTING.value,
            "message": "Limited admin access for user {{input_data.user_id}}",
        },
    )

    # Action for non-admins
    user_action = node(
        "n6",
        NodeType.ACTION.value,
        ActionSubtype.DATA_FORMATTING.value,
        {
            "action_type": ActionSubtype.DATA_FORMATTING.value,
            "message": "Regular user access for user {{input_data.user_id}}",
        },
    )

    workflow = {
        "id": "wf_conditional_chain",
        "name": "Conditional Chain Workflow",
        "nodes": [trigger, role_check, permission_check, admin_action, limited_action, user_action],
        "connections": {
            "n1": [connect("n1", "n2")],  # TRIGGER → Role Check
            "n2": [
                connect("n2", "n3", output_field="true_path"),  # Admin → Permission Check
                connect("n2", "n6", output_field="false_path"),  # Non-admin → User Action
            ],
            "n3": [
                connect("n3", "n4", output_field="true_path"),  # High permission → Admin Action
                connect("n3", "n5", output_field="false_path"),  # Low permission → Limited Action
            ],
        },
    }

    patch_workflow_definition(workflow)

    # Test high-permission admin path
    resp = await app_client.post(
        "/v1/workflows/wf_conditional_chain/execute",
        json={
            "workflow_id": "wf_conditional_chain",
            "user_id": "u1",
            "trigger_data": {"user_role": "admin", "permission_level": "8", "user_id": "admin123"},
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs show conditional execution
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of FLOW node")
    assert_log_contains(logs, "Successfully completed FLOW node")


@pytest.mark.asyncio
async def test_fan_out_fan_in_pattern(app_client, patch_workflow_definition, in_memory_logs):
    """Test fan-out to multiple processors then fan-in to aggregator"""

    # Create nodes
    trigger = node(
        "n1", NodeType.TRIGGER.value, TriggerSubtype.MANUAL.value, {"trigger_type": "manual"}
    )

    # Data preprocessor
    preprocessor = node(
        "n2",
        NodeType.ACTION.value,
        ActionSubtype.DATA_TRANSFORMATION.value,
        {
            "action_type": ActionSubtype.DATA_TRANSFORMATION.value,
            "transformation_type": "field_mapping",
            "field_mappings": {"raw_data": "processed_data"},
        },
    )

    # Multiple parallel processors
    text_processor = node(
        "n3",
        NodeType.AI_AGENT.value,
        AIAgentSubtype.OPENAI_CHATGPT.value,
        {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "system_prompt": "Extract key information from text",
            "user_message": "Process text: {{input_data.text}}",
        },
    )

    data_analyzer = node(
        "n4",
        NodeType.TOOL.value,
        ToolSubtype.HTTP_CLIENT.value,
        {
            "tool_type": "utility",
            "utility_type": "hash",
            "operation": "analyze",
            "hash_type": "sha256",
        },
    )

    metadata_extractor = node(
        "n5",
        NodeType.ACTION.value,
        ActionSubtype.DATA_TRANSFORMATION.value,
        {
            "action_type": ActionSubtype.DATA_TRANSFORMATION.value,
            "transformation_type": "custom",
            "transformation_rule": "$.metadata",
        },
    )

    # Aggregator
    aggregator = node(
        "n6",
        NodeType.FLOW.value,
        FlowSubtype.MERGE.value,
        {
            "flow_type": "merge",
            "merge_strategy": "combine",
            "wait_for_all": True,
            "output_field": "aggregated_results",
        },
    )

    # Final processor
    finalizer = node(
        "n7",
        NodeType.ACTION.value,
        ActionSubtype.DATA_FORMATTING.value,
        {
            "action_type": ActionSubtype.DATA_FORMATTING.value,
            "message": "Processing complete: {{input_data}}",
        },
    )

    workflow = {
        "id": "wf_fan_out_in",
        "name": "Fan-out Fan-in Pattern",
        "nodes": [
            trigger,
            preprocessor,
            text_processor,
            data_analyzer,
            metadata_extractor,
            aggregator,
            finalizer,
        ],
        "connections": {
            "n1": [connect("n1", "n2")],  # TRIGGER → Preprocessor
            "n2": [
                connect("n2", "n3"),  # Preprocessor → Text Processor
                connect("n2", "n4"),  # Preprocessor → Data Analyzer
                connect("n2", "n5"),  # Preprocessor → Metadata Extractor
            ],
            "n3": [connect("n3", "n6")],  # Text Processor → Aggregator
            "n4": [connect("n4", "n6")],  # Data Analyzer → Aggregator
            "n5": [connect("n5", "n6")],  # Metadata Extractor → Aggregator
            "n6": [connect("n6", "n7")],  # Aggregator → Finalizer
        },
    }

    patch_workflow_definition(workflow)

    resp = await app_client.post(
        "/v1/workflows/wf_fan_out_in/execute",
        json={
            "workflow_id": "wf_fan_out_in",
            "user_id": "u1",
            "trigger_data": {
                "text": "Sample text for processing",
                "metadata": '{"source": "api", "timestamp": "2025-01-17"}',
                "raw_data": "input for transformation",
            },
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs show fan-out/fan-in pattern
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of FLOW node")
    # Should see multiple parallel executions
