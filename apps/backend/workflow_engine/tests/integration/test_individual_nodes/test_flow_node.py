from typing import Any, Dict

import pytest

from shared.models.node_enums import FlowSubtype, NodeType
from workflow_engine.tests.integration.utils.assertions import (
    assert_execution_success_status,
    assert_log_contains,
)
from workflow_engine.tests.integration.utils.lifecycle_utils import create_lifecycle_manager
from workflow_engine.tests.integration.utils.workflow_factory import node, single_node_workflow


@pytest.mark.asyncio
async def test_conditional_flow_true_path(app_client):
    """Test: FLOW node IF condition using real API lifecycle"""
    manager = create_lifecycle_manager(app_client)

    try:
        # Create workflow definition
        flow_node = node(
            "n1",
            ntype=NodeType.FLOW.value,
            subtype=FlowSubtype.IF.value,
            parameters={
                "flow_type": "if",
                "condition": "input_data.value > 10",
                "condition_field": "value",
                "condition_operator": ">",
                "condition_value": "10",
            },
        )
        workflow_definition = single_node_workflow(flow_node)

        # Execute complete workflow lifecycle
        workflow_id = await manager.create_workflow(workflow_definition)
        execution_result = await manager.execute_and_wait(
            workflow_id, {"value": "15"}, timeout_seconds=30  # > 10, should be true
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
async def test_conditional_flow_false_path(app_client, patch_workflow_definition, in_memory_logs):
    """Test IF condition evaluating to false."""
    flow_node = node(
        "n1",
        ntype=NodeType.FLOW.value,
        subtype=FlowSubtype.IF.value,
        parameters={
            "flow_type": "if",
            "condition": "input_data.value > 10",
            "condition_field": "value",
            "condition_operator": ">",
            "condition_value": 10,
        },
    )
    wf = single_node_workflow(flow_node)
    patch_workflow_definition(wf)

    # Execute with condition that should be false
    resp = await app_client.post(
        "/v1/workflows/wf_if_false/execute",
        json={
            "workflow_id": "wf_if_false",
            "user_id": "u1",
            "trigger_data": {"value": "5"},  # < 10, should be false
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Assert execution success
    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs contain flow execution
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of FLOW node")


@pytest.mark.asyncio
async def test_switch_case_flow(app_client, patch_workflow_definition, in_memory_logs):
    """Test SWITCH/CASE flow control."""
    flow_node = node(
        "n1",
        ntype=NodeType.FLOW.value,
        subtype=FlowSubtype.SWITCH.value,
        parameters={
            "flow_type": "switch",
            "switch_field": "category",
            "cases": {
                "urgent": {"priority": "high"},
                "normal": {"priority": "medium"},
                "low": {"priority": "low"},
            },
            "default_case": {"priority": "unknown"},
        },
    )
    wf = single_node_workflow(flow_node)
    patch_workflow_definition(wf)

    # Execute with switch value
    resp = await app_client.post(
        "/v1/workflows/wf_switch/execute",
        json={
            "workflow_id": "wf_switch",
            "user_id": "u1",
            "trigger_data": {"category": "urgent", "message": "test"},
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Assert execution success
    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs contain switch execution
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of FLOW node")


@pytest.mark.asyncio
async def test_for_each_loop_array(app_client, patch_workflow_definition, in_memory_logs):
    """Test FOR_EACH loop over array data."""
    flow_node = node(
        "n1",
        ntype=NodeType.FLOW.value,
        subtype=FlowSubtype.FOR_EACH.value,
        parameters={
            "flow_type": "for_each",
            "array_field": "items",
            "item_variable": "current_item",
            "max_iterations": 10,
        },
    )
    wf = single_node_workflow(flow_node)
    patch_workflow_definition(wf)

    # Execute with array data
    resp = await app_client.post(
        "/v1/workflows/wf_foreach/execute",
        json={
            "workflow_id": "wf_foreach",
            "user_id": "u1",
            "trigger_data": {"items": '["item1", "item2", "item3"]', "process": "batch"},
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Assert execution success
    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs contain for_each execution
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of FLOW node")


@pytest.mark.asyncio
async def test_merge_multiple_inputs(app_client, patch_workflow_definition, in_memory_logs):
    """Test data merging from multiple sources."""
    flow_node = node(
        "n1",
        ntype=NodeType.FLOW.value,
        subtype=FlowSubtype.MERGE.value,
        parameters={
            "flow_type": "merge",
            "merge_strategy": "combine",
            "output_field": "merged_data",
            "wait_for_all": True,
        },
    )
    wf = single_node_workflow(flow_node)
    patch_workflow_definition(wf)

    # Execute with multiple data sources to merge
    resp = await app_client.post(
        "/v1/workflows/wf_merge/execute",
        json={
            "workflow_id": "wf_merge",
            "user_id": "u1",
            "trigger_data": {
                "source1": '{"data": "value1"}',
                "source2": '{"data": "value2"}',
                "source3": '{"data": "value3"}',
            },
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Assert execution success
    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs contain merge execution
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of FLOW node")


@pytest.mark.asyncio
async def test_split_parallel_execution(app_client, patch_workflow_definition, in_memory_logs):
    """Test data splitting for parallel execution."""
    flow_node = node(
        "n1",
        ntype=NodeType.FLOW.value,
        subtype=FlowSubtype.SPLIT.value,
        parameters={
            "flow_type": "split",
            "split_field": "batch_data",
            "split_strategy": "parallel",
            "max_parallel": 3,
        },
    )
    wf = single_node_workflow(flow_node)
    patch_workflow_definition(wf)

    # Execute with data to split
    resp = await app_client.post(
        "/v1/workflows/wf_split/execute",
        json={
            "workflow_id": "wf_split",
            "user_id": "u1",
            "trigger_data": {
                "batch_data": '[{"id": 1, "value": "a"}, {"id": 2, "value": "b"}, {"id": 3, "value": "c"}]'
            },
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Assert execution success
    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs contain split execution
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of FLOW node")


@pytest.mark.asyncio
async def test_filter_array_data(app_client, patch_workflow_definition, in_memory_logs):
    """Test array filtering with conditions."""
    flow_node = node(
        "n1",
        ntype=NodeType.FLOW.value,
        subtype=FlowSubtype.FILTER.value,
        parameters={
            "flow_type": "filter",
            "array_field": "records",
            "filter_condition": "item.status == 'active'",
            "filter_field": "status",
            "filter_value": "active",
        },
    )
    wf = single_node_workflow(flow_node)
    patch_workflow_definition(wf)

    # Execute with array to filter
    resp = await app_client.post(
        "/v1/workflows/wf_filter/execute",
        json={
            "workflow_id": "wf_filter",
            "user_id": "u1",
            "trigger_data": {
                "records": '[{"id": 1, "status": "active", "name": "record1"}, {"id": 2, "status": "inactive", "name": "record2"}, {"id": 3, "status": "active", "name": "record3"}]'
            },
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Assert execution success
    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs contain filter execution
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of FLOW node")


@pytest.mark.asyncio
async def test_complex_nested_conditions(app_client, patch_workflow_definition, in_memory_logs):
    """Test complex nested conditional expressions."""
    flow_node = node(
        "n1",
        ntype=NodeType.FLOW.value,
        subtype=FlowSubtype.IF.value,
        parameters={
            "flow_type": "if",
            "condition": "(input_data.priority == 'high' and input_data.urgency > 7) or input_data.emergency == true",
            "nested_conditions": {
                "primary": {"field": "priority", "operator": "==", "value": "high"},
                "secondary": {"field": "urgency", "operator": ">", "value": 7},
                "emergency": {"field": "emergency", "operator": "==", "value": True},
            },
        },
    )
    wf = single_node_workflow(flow_node)
    patch_workflow_definition(wf)

    # Execute with complex condition data
    resp = await app_client.post(
        "/v1/workflows/wf_complex/execute",
        json={
            "workflow_id": "wf_complex",
            "user_id": "u1",
            "trigger_data": {
                "priority": "high",
                "urgency": "8",
                "emergency": "false",
                "context": "complex_test",
            },
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Assert execution success
    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs contain complex flow execution
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of FLOW node")
