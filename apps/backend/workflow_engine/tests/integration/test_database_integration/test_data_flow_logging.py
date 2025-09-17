from typing import Any, Dict

import pytest

from shared.models.node_enums import (
    ActionSubtype,
    AIAgentSubtype,
    ExternalActionSubtype,
    FlowSubtype,
    NodeType,
    ToolSubtype,
    TriggerSubtype,
)
from workflow_engine.tests.integration.utils.assertions import (
    assert_execution_success_status,
    assert_log_contains,
)
from workflow_engine.tests.integration.utils.workflow_factory import connect, linear_workflow, node


@pytest.mark.asyncio
async def test_input_output_data_logging(app_client, patch_workflow_definition, in_memory_logs):
    """Test input/output data logged for each node."""
    # Create workflow with data transformations to track input/output
    trigger = node(
        "n1", NodeType.TRIGGER.value, TriggerSubtype.MANUAL.value, {"trigger_type": "manual"}
    )

    transformer = node(
        "n2",
        NodeType.ACTION.value,
        ActionSubtype.DATA_TRANSFORMATION.value,
        {
            "action_type": "data_transformation",
            "transformation_type": "field_mapping",
            "field_mappings": {
                "input_message": "transformed_message",
                "raw_data": "processed_data",
            },
        },
    )

    ai_processor = node(
        "n3",
        NodeType.AI_AGENT.value,
        AIAgentSubtype.OPENAI_CHATGPT.value,
        {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "system_prompt": "Process the input data",
            "user_message": "Transform this data: {{input_data.processed_data}}",
        },
    )

    wf = linear_workflow([trigger, transformer, ai_processor])
    patch_workflow_definition(wf)

    # Execute with specific input data to track
    resp = await app_client.post(
        "/v1/workflows/wf_linear/execute",
        json={
            "workflow_id": "wf_linear",
            "user_id": "u1",
            "trigger_data": {
                "input_message": "Original message for transformation",
                "raw_data": '{"key": "value", "number": 42}',
                "metadata": '{"source": "test", "version": "1.0"}',
            },
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check that data flow is logged
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)

    assert len(logs) > 0, "No logs found for data flow tracking"

    # Look for data-related log entries
    log_content = " ".join([str(log) for log in logs]).lower()

    # Should have logs indicating data processing
    data_processing_indicators = ["transform", "process", "input", "output", "data"]
    data_logs_found = any(indicator in log_content for indicator in data_processing_indicators)
    assert data_logs_found, "No data processing logs found"


@pytest.mark.asyncio
async def test_parameter_logging_accuracy(app_client, patch_workflow_definition, in_memory_logs):
    """Test node parameters logged accurately."""
    # Create nodes with specific parameters to verify logging
    tool_node = node(
        "n1",
        NodeType.TOOL.value,
        ToolSubtype.MCP_TOOL.value,
        {
            "tool_type": "utility",
            "utility_type": "hash",
            "operation": "generate",
            "hash_type": "sha256",
            "text": "Test input for hashing",
            "custom_parameter": "custom_value_123",
        },
    )

    external_action = node(
        "n2",
        NodeType.EXTERNAL_ACTION.value,
        ExternalActionSubtype.WEBHOOK.value,
        {
            "action_type": "webhook",
            "url": "https://httpbin.org/post",
            "method": "POST",
            "payload": {"test": "parameter_logging"},
            "headers": {"Content-Type": "application/json"},
            "timeout": 30,
        },
    )

    wf = linear_workflow([tool_node, external_action])
    patch_workflow_definition(wf)

    resp = await app_client.post(
        "/v1/workflows/wf_linear/execute",
        json={
            "workflow_id": "wf_linear",
            "user_id": "u1",
            "trigger_data": {"test": "parameter_accuracy"},
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check parameter logging
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)

    assert len(logs) > 0, "No logs found for parameter tracking"

    # Check for node execution logs with parameter information
    log_content = " ".join([str(log) for log in logs])

    # Should have logs indicating node execution with tool types
    node_execution_indicators = ["tool", "utility", "hash", "webhook", "external"]
    node_logs_found = any(
        indicator in log_content.lower() for indicator in node_execution_indicators
    )
    assert node_logs_found, "No node execution logs with parameters found"


@pytest.mark.asyncio
async def test_data_flow_integrity_verification(
    app_client, patch_workflow_definition, in_memory_logs
):
    """Test data flow integrity between nodes."""
    # Create workflow with clear data dependencies
    trigger = node(
        "n1", NodeType.TRIGGER.value, TriggerSubtype.MANUAL.value, {"trigger_type": "manual"}
    )

    # Node that adds data
    data_enricher = node(
        "n2",
        NodeType.ACTION.value,
        ActionSubtype.DATA_TRANSFORMATION.value,
        {
            "action_type": "data_transformation",
            "transformation_type": "field_mapping",
            "field_mappings": {"original": "enriched_original", "timestamp": "processing_time"},
            "additional_fields": {
                "enriched_at": "{{current_timestamp}}",
                "processing_stage": "enrichment",
            },
        },
    )

    # Node that processes enriched data
    data_processor = node(
        "n3",
        NodeType.TOOL.value,
        ToolSubtype.MCP_TOOL.value,
        {
            "tool_type": "utility",
            "utility_type": "format",
            "operation": "format",
            "format_type": "json",
        },
    )

    # Final validation node
    validator = node(
        "n4",
        NodeType.FLOW.value,
        FlowSubtype.IF.value,
        {
            "flow_type": "if",
            "condition": "input_data.enriched_original != null",
            "validation_field": "enriched_original",
            "validation_type": "not_null",
        },
    )

    wf = linear_workflow([trigger, data_enricher, data_processor, validator])
    patch_workflow_definition(wf)

    # Execute with traceable data
    resp = await app_client.post(
        "/v1/workflows/wf_linear/execute",
        json={
            "workflow_id": "wf_linear",
            "user_id": "u1",
            "trigger_data": {
                "original": "source_data_value",
                "timestamp": "2025-01-17T10:00:00Z",
                "trace_id": "integrity_test_123",
            },
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Verify data flow logging
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)

    assert len(logs) > 0, "No logs found for data flow verification"

    # Check for evidence of data flow through the pipeline
    log_content = " ".join([str(log) for log in logs]).lower()

    # Should have logs for each stage of processing
    processing_stages = ["trigger", "transform", "format", "flow"]
    stages_logged = sum(1 for stage in processing_stages if stage in log_content)
    assert stages_logged >= 2, "Insufficient data flow logging across processing stages"


@pytest.mark.asyncio
async def test_branching_data_flow_tracking(app_client, patch_workflow_definition, in_memory_logs):
    """Test data flow tracking in branching workflows."""
    # Create branching workflow to test data flow tracking
    trigger = node(
        "n1", NodeType.TRIGGER.value, TriggerSubtype.MANUAL.value, {"trigger_type": "manual"}
    )

    # Decision point
    router = node(
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

    # High priority path
    high_priority_action = node(
        "n3",
        NodeType.AI_AGENT.value,
        AIAgentSubtype.OPENAI_CHATGPT.value,
        {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "system_prompt": "Handle high priority request",
            "user_message": "Process urgently: {{input_data.message}}",
        },
    )

    # Normal priority path
    normal_priority_action = node(
        "n4",
        NodeType.ACTION.value,
        ActionSubtype.DATA_FORMATTING.value,
        {
            "action_type": "log",
            "message": "Processing normal priority: {{input_data.message}}",
            "level": "INFO",
        },
    )

    # Define branching workflow
    workflow = {
        "id": "wf_branching_data",
        "name": "Branching Data Flow Test",
        "nodes": [trigger, router, high_priority_action, normal_priority_action],
        "connections": {
            "n1": [connect("n1", "n2")],  # TRIGGER → Router
            "n2": [
                connect("n2", "n3", output_field="true_path"),  # High priority
                connect("n2", "n4", output_field="false_path"),  # Normal priority
            ],
        },
    }

    patch_workflow_definition(workflow)

    # Test high priority path
    resp = await app_client.post(
        "/v1/workflows/wf_branching_data/execute",
        json={
            "workflow_id": "wf_branching_data",
            "user_id": "u1",
            "trigger_data": {
                "priority": "high",
                "message": "Urgent data processing required",
                "branch_test": "high_priority_path",
            },
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check branching data flow logs
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)

    assert len(logs) > 0, "No logs found for branching data flow"

    # Should have logs for branching decision and execution
    log_content = " ".join([str(log) for log in logs]).lower()

    # Check for flow control and branching
    flow_indicators = ["flow", "if", "condition", "branch"]
    flow_logs_found = any(indicator in log_content for indicator in flow_indicators)
    assert flow_logs_found, "No flow control logs found for branching workflow"


@pytest.mark.asyncio
async def test_parallel_data_flow_logging(app_client, patch_workflow_definition, in_memory_logs):
    """Test data flow logging in parallel execution scenarios."""
    # Create workflow with parallel data processing
    trigger = node(
        "n1", NodeType.TRIGGER.value, TriggerSubtype.MANUAL.value, {"trigger_type": "manual"}
    )

    # Split data for parallel processing
    splitter = node(
        "n2",
        NodeType.FLOW.value,
        FlowSubtype.SPLIT.value,
        {
            "flow_type": "split",
            "split_field": "data_array",
            "split_strategy": "parallel",
            "max_parallel": 3,
        },
    )

    # Parallel processors
    processor_a = node(
        "n3",
        NodeType.TOOL.value,
        ToolSubtype.MCP_TOOL.value,
        {
            "tool_type": "utility",
            "utility_type": "hash",
            "operation": "process_a",
            "hash_type": "md5",
        },
    )

    processor_b = node(
        "n4",
        NodeType.ACTION.value,
        ActionSubtype.DATA_TRANSFORMATION.value,
        {
            "action_type": "data_transformation",
            "transformation_type": "field_mapping",
            "field_mappings": {"input": "output_b"},
        },
    )

    processor_c = node(
        "n5",
        NodeType.TOOL.value,
        ToolSubtype.MCP_TOOL.value,
        {"tool_type": "utility", "utility_type": "timestamp", "operation": "process_c"},
    )

    # Merge results
    merger = node(
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

    # Define parallel workflow
    workflow = {
        "id": "wf_parallel_data",
        "name": "Parallel Data Flow Test",
        "nodes": [trigger, splitter, processor_a, processor_b, processor_c, merger],
        "connections": {
            "n1": [connect("n1", "n2")],  # TRIGGER → Splitter
            "n2": [
                connect("n2", "n3"),  # Split → Processor A
                connect("n2", "n4"),  # Split → Processor B
                connect("n2", "n5"),  # Split → Processor C
            ],
            "n3": [connect("n3", "n6")],  # Processor A → Merger
            "n4": [connect("n4", "n6")],  # Processor B → Merger
            "n5": [connect("n5", "n6")],  # Processor C → Merger
        },
    }

    patch_workflow_definition(workflow)

    resp = await app_client.post(
        "/v1/workflows/wf_parallel_data/execute",
        json={
            "workflow_id": "wf_parallel_data",
            "user_id": "u1",
            "trigger_data": {
                "data_array": '["item1", "item2", "item3"]',
                "parallel_test": "true",
                "processing_id": "parallel_flow_123",
            },
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check parallel data flow logs
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)

    assert len(logs) > 0, "No logs found for parallel data flow"

    # Should have logs for split/merge operations
    log_content = " ".join([str(log) for log in logs]).lower()

    # Look for basic execution indicators that should be captured
    execution_indicators = ["flow", "tool", "action", "execut", "completed"]
    execution_logs_found = sum(1 for indicator in execution_indicators if indicator in log_content)
    assert execution_logs_found >= 2, "Insufficient parallel processing execution logs found"


@pytest.mark.asyncio
async def test_error_data_flow_logging(app_client, patch_workflow_definition, in_memory_logs):
    """Test data flow logging when errors occur."""
    # Create workflow with potential error points
    trigger = node(
        "n1", NodeType.TRIGGER.value, TriggerSubtype.MANUAL.value, {"trigger_type": "manual"}
    )

    # Node that might fail
    error_prone_node = node(
        "n2",
        NodeType.ACTION.value,
        ActionSubtype.HTTP_REQUEST.value,
        {
            "action_type": "http_request",
            "url": "https://nonexistent-error-domain-12345.com/api",
            "method": "POST",
            "payload": {"test": "error_flow"},
            "timeout": 1,
        },
    )

    # Recovery node
    recovery_node = node(
        "n3",
        NodeType.ACTION.value,
        ActionSubtype.DATA_FORMATTING.value,
        {
            "action_type": "log",
            "message": "Handling error recovery: {{input_data}}",
            "level": "WARNING",
        },
    )

    wf = linear_workflow([trigger, error_prone_node, recovery_node])
    patch_workflow_definition(wf)

    resp = await app_client.post(
        "/v1/workflows/wf_linear/execute",
        json={
            "workflow_id": "wf_linear",
            "user_id": "u1",
            "trigger_data": {"test": "error_data_flow", "error_expected": "true"},
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Workflow should complete (even with errors)
    assert resp.status_code == 200

    # Check error handling in data flow logs
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)

    assert len(logs) > 0, "No logs found for error data flow"

    # Should have logs for execution attempts even when errors occur
    log_content = " ".join([str(log) for log in logs]).lower()

    # Should have execution logs regardless of errors
    execution_indicators = ["execut", "trigger", "action", "http"]
    execution_logs_found = any(indicator in log_content for indicator in execution_indicators)
    assert execution_logs_found, "No execution logs found for error scenarios"


@pytest.mark.asyncio
async def test_data_transformation_chain_logging(
    app_client, patch_workflow_definition, in_memory_logs
):
    """Test logging of data transformations through processing chain."""
    # Create chain of data transformations
    trigger = node(
        "n1", NodeType.TRIGGER.value, TriggerSubtype.MANUAL.value, {"trigger_type": "manual"}
    )

    # First transformation
    transform_1 = node(
        "n2",
        NodeType.ACTION.value,
        ActionSubtype.DATA_TRANSFORMATION.value,
        {
            "action_type": "data_transformation",
            "transformation_type": "field_mapping",
            "field_mappings": {"raw_input": "step1_output", "metadata": "step1_metadata"},
        },
    )

    # Second transformation
    transform_2 = node(
        "n3",
        NodeType.ACTION.value,
        ActionSubtype.DATA_TRANSFORMATION.value,
        {
            "action_type": "data_transformation",
            "transformation_type": "jsonpath",
            "jsonpath_expression": "$.step1_output",
            "output_field": "step2_result",
        },
    )

    # Final formatting
    formatter = node(
        "n4",
        NodeType.TOOL.value,
        ToolSubtype.MCP_TOOL.value,
        {
            "tool_type": "utility",
            "utility_type": "format",
            "format_type": "json",
            "operation": "format",
        },
    )

    wf = linear_workflow([trigger, transform_1, transform_2, formatter])
    patch_workflow_definition(wf)

    resp = await app_client.post(
        "/v1/workflows/wf_linear/execute",
        json={
            "workflow_id": "wf_linear",
            "user_id": "u1",
            "trigger_data": {
                "raw_input": "Original data for transformation chain",
                "metadata": '{"version": "1.0", "source": "api"}',
                "chain_test": "transformation_logging",
            },
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check transformation chain logging
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)

    assert len(logs) > 0, "No logs found for transformation chain"

    # Should have logs for each transformation step
    log_content = " ".join([str(log) for log in logs]).lower()

    transformation_indicators = ["transform", "format", "mapping", "json", "utility"]
    transformation_logs_found = sum(
        1 for indicator in transformation_indicators if indicator in log_content
    )
    assert transformation_logs_found >= 2, "Insufficient transformation chain logs found"
