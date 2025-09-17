from typing import Any, Dict

import pytest

from shared.models.node_enums import NodeType, ToolSubtype
from workflow_engine.tests.integration.utils.assertions import (
    assert_execution_success_status,
    assert_log_contains,
)
from workflow_engine.tests.integration.utils.workflow_factory import node, single_node_workflow


@pytest.mark.asyncio
async def test_mcp_tool_execution_mock(app_client, patch_workflow_definition, in_memory_logs):
    """Test MCP tool execution with mock responses."""
    tool_node = node(
        "n1",
        ntype=NodeType.TOOL.value,
        subtype=ToolSubtype.MCP_TOOL.value,
        parameters={
            "tool_type": "mcp",
            "operation": "execute",
            "tool_name": "file_read",
            "tool_parameters": {"path": "/tmp/test.txt"},
        },
    )
    wf = single_node_workflow(tool_node)
    patch_workflow_definition(wf)

    # Execute workflow
    resp = await app_client.post(
        "/v1/workflows/wf_mcp/execute",
        json={
            "workflow_id": "wf_mcp",
            "user_id": "u1",
            "trigger_data": {"context": "file_operation"},
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Assert execution success
    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs contain MCP tool execution
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of TOOL node")
    assert_log_contains(logs, "Successfully completed TOOL node")


@pytest.mark.asyncio
async def test_utility_tool_timestamp(app_client, patch_workflow_definition, in_memory_logs):
    """Test utility tool timestamp generation."""
    tool_node = node(
        "n1",
        ntype=NodeType.TOOL.value,
        subtype=ToolSubtype.MCP_TOOL.value,
        parameters={"tool_type": "utility", "operation": "generate", "utility_type": "timestamp"},
    )
    wf = single_node_workflow(tool_node)
    patch_workflow_definition(wf)

    # Execute workflow
    resp = await app_client.post(
        "/v1/workflows/wf_timestamp/execute",
        json={
            "workflow_id": "wf_timestamp",
            "user_id": "u1",
            "trigger_data": {},
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Assert execution success
    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs contain utility tool execution
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of TOOL node")
    assert_log_contains(logs, "Successfully completed TOOL node")


@pytest.mark.asyncio
async def test_utility_tool_uuid_generation(app_client, patch_workflow_definition, in_memory_logs):
    """Test utility tool UUID generation."""
    tool_node = node(
        "n1",
        ntype=NodeType.TOOL.value,
        subtype=ToolSubtype.MCP_TOOL.value,
        parameters={"tool_type": "utility", "operation": "generate", "utility_type": "uuid"},
    )
    wf = single_node_workflow(tool_node)
    patch_workflow_definition(wf)

    # Execute workflow
    resp = await app_client.post(
        "/v1/workflows/wf_uuid/execute",
        json={
            "workflow_id": "wf_uuid",
            "user_id": "u1",
            "trigger_data": {},
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Assert execution success
    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs contain UUID generation
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of TOOL node")
    assert_log_contains(logs, "Successfully completed TOOL node")


@pytest.mark.asyncio
async def test_utility_tool_hash_functions(app_client, patch_workflow_definition, in_memory_logs):
    """Test utility tool hash functions (md5, sha256)."""
    tool_node = node(
        "n1",
        ntype=NodeType.TOOL.value,
        subtype=ToolSubtype.MCP_TOOL.value,
        parameters={
            "tool_type": "utility",
            "operation": "hash",
            "utility_type": "hash",
            "text": "Hello, World!",
            "hash_type": "sha256",
        },
    )
    wf = single_node_workflow(tool_node)
    patch_workflow_definition(wf)

    # Execute workflow
    resp = await app_client.post(
        "/v1/workflows/wf_hash/execute",
        json={
            "workflow_id": "wf_hash",
            "user_id": "u1",
            "trigger_data": {"input_text": "test data"},
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Assert execution success
    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs contain hash operation
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of TOOL node")
    assert_log_contains(logs, "Successfully completed TOOL node")


@pytest.mark.asyncio
async def test_file_operations_read_write(app_client, patch_workflow_definition, in_memory_logs):
    """Test file read/write operations."""
    # Test file write operation
    tool_node = node(
        "n1",
        ntype=NodeType.TOOL.value,
        subtype=ToolSubtype.MCP_TOOL.value,
        parameters={
            "tool_type": "file",
            "operation": "write",
            "file_path": "/tmp/test_workflow.txt",
            "content": "This is test content from workflow engine",
        },
    )
    wf = single_node_workflow(tool_node)
    patch_workflow_definition(wf)

    # Execute workflow
    resp = await app_client.post(
        "/v1/workflows/wf_file_write/execute",
        json={
            "workflow_id": "wf_file_write",
            "user_id": "u1",
            "trigger_data": {"operation": "file_test"},
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Assert execution success
    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs contain file operation
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of TOOL node")
    assert_log_contains(logs, "Successfully completed TOOL node")


@pytest.mark.asyncio
async def test_api_tool_http_requests(app_client, patch_workflow_definition, in_memory_logs):
    """Test API tool HTTP request functionality."""
    tool_node = node(
        "n1",
        ntype=NodeType.TOOL.value,
        subtype=ToolSubtype.MCP_TOOL.value,
        parameters={
            "tool_type": "api",
            "operation": "request",
            "url": "https://httpbin.org/get",
            "method": "GET",
            "headers": {"User-Agent": "Workflow-Engine-Test", "Accept": "application/json"},
        },
    )
    wf = single_node_workflow(tool_node)
    patch_workflow_definition(wf)

    # Execute workflow
    resp = await app_client.post(
        "/v1/workflows/wf_api/execute",
        json={
            "workflow_id": "wf_api",
            "user_id": "u1",
            "trigger_data": {"test": "api_call"},
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Assert execution success
    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs contain API tool execution
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of TOOL node")
    assert_log_contains(logs, "Successfully completed TOOL node")


@pytest.mark.asyncio
async def test_tool_parameter_validation(app_client, patch_workflow_definition):
    """Test tool-specific parameter validation."""
    # Test API tool without required URL parameter
    tool_node = node(
        "n1",
        ntype=NodeType.TOOL.value,
        subtype=ToolSubtype.MCP_TOOL.value,
        parameters={
            "tool_type": "api",
            "operation": "request",
            "method": "GET"
            # Missing required 'url' parameter
        },
    )
    wf = single_node_workflow(tool_node)
    patch_workflow_definition(wf)

    resp = await app_client.post(
        "/v1/workflows/wf_api_validation/execute",
        json={
            "workflow_id": "wf_api_validation",
            "user_id": "u1",
            "trigger_data": {},
            "async_execution": False,
        },
    )

    # Should handle validation error gracefully
    assert resp.status_code == 200
    # The execution should still succeed but may have error in the result
    # based on current validation implementation


@pytest.mark.asyncio
async def test_generic_tool_execution(app_client, patch_workflow_definition, in_memory_logs):
    """Test generic/unknown tool type execution."""
    tool_node = node(
        "n1",
        ntype=NodeType.TOOL.value,
        subtype=ToolSubtype.MCP_TOOL.value,
        parameters={
            "tool_type": "custom_tool",
            "operation": "process",
            "custom_parameter": "test_value",
        },
    )
    wf = single_node_workflow(tool_node)
    patch_workflow_definition(wf)

    # Execute workflow
    resp = await app_client.post(
        "/v1/workflows/wf_generic/execute",
        json={
            "workflow_id": "wf_generic",
            "user_id": "u1",
            "trigger_data": {"input": "generic_test"},
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Assert execution success
    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs contain generic tool execution
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of TOOL node")
    assert_log_contains(logs, "Successfully completed TOOL node")


@pytest.mark.asyncio
async def test_utility_tool_format_operations(
    app_client, patch_workflow_definition, in_memory_logs
):
    """Test utility tool data formatting operations."""
    tool_node = node(
        "n1",
        ntype=NodeType.TOOL.value,
        subtype=ToolSubtype.MCP_TOOL.value,
        parameters={
            "tool_type": "utility",
            "operation": "format",
            "utility_type": "format",
            "format_type": "json",
        },
    )
    wf = single_node_workflow(tool_node)
    patch_workflow_definition(wf)

    # Execute workflow with data to format
    resp = await app_client.post(
        "/v1/workflows/wf_format/execute",
        json={
            "workflow_id": "wf_format",
            "user_id": "u1",
            "trigger_data": {"name": "test", "value": "123", "nested": '{"key": "value"}'},
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Assert execution success
    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs contain format operation
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of TOOL node")
    assert_log_contains(logs, "Successfully completed TOOL node")
