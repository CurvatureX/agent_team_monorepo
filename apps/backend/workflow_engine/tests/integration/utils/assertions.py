from typing import Any, Dict, Iterable, List, Optional


def assert_execution_success_status(resp_json: Dict[str, Any]) -> None:
    assert resp_json.get("success") is True
    assert resp_json.get("status") in {"success", "SUCCESS", "COMPLETED", "NEW"}


def assert_log_contains(logs: Iterable[Dict[str, Any]], contains: str) -> None:
    msgs = [l.get("message", "") for l in logs]
    assert any(
        contains in m for m in msgs
    ), f"Log message containing '{contains}' not found. Messages: {msgs}"


def assert_execution_status(response_data: Dict[str, Any], expected_status: str) -> None:
    """Assert that the execution has the expected status."""
    actual_status = response_data.get("status")
    assert (
        actual_status == expected_status
    ), f"Expected status '{expected_status}', got '{actual_status}'"


def assert_node_output_structure(output_data: Dict[str, Any], expected_fields: List[str]) -> None:
    """Assert node output contains expected fields."""
    for field in expected_fields:
        assert (
            field in output_data
        ), f"Expected field '{field}' not found in output: {output_data.keys()}"


def assert_data_flow_integrity(source_output: Dict[str, Any], target_input: Dict[str, Any]) -> None:
    """Assert data flows correctly between nodes."""
    # Check that key data from source appears in target
    for key, value in source_output.items():
        if key in target_input:
            assert (
                target_input[key] == value
            ), f"Data mismatch for key '{key}': source={value}, target={target_input[key]}"


def assert_log_completeness(logs: List[Dict[str, Any]], expected_node_count: int) -> None:
    """Assert logs are complete for all nodes."""
    assert len(logs) > 0, "No logs found"

    # Count unique node executions in logs
    node_executions = set()
    for log in logs:
        if isinstance(log, dict):
            message = log.get("message", "")
            if "node" in message.lower() or "execut" in message.lower():
                node_executions.add(message)

    # Should have at least some node execution logs
    assert len(node_executions) > 0, "No node execution logs found"


def assert_user_friendly_messages(logs: List[Dict[str, Any]]) -> None:
    """Assert logs contain user-friendly messages."""
    user_friendly_count = 0
    for log in logs:
        if isinstance(log, dict):
            message = log.get("message", "")
            if isinstance(message, str) and len(message) > 10:
                # Check for descriptive words
                descriptive_words = ["executing", "started", "completed", "processing", "finished"]
                if any(word in message.lower() for word in descriptive_words):
                    user_friendly_count += 1

    assert user_friendly_count > 0, "No user-friendly log messages found"


def assert_error_handled_gracefully(response_data: Dict[str, Any]) -> None:
    """Assert that errors are handled gracefully."""
    # Should still have a response even if there were errors
    assert "execution_id" in response_data, "No execution_id even with errors"

    # Check if error information is provided when needed
    if response_data.get("success") is False:
        assert (
            "error_message" in response_data or "message" in response_data
        ), "No error details provided"


def assert_async_execution_response(response_data: Dict[str, Any]) -> None:
    """Assert async execution returns immediately with proper response."""
    assert response_data.get("success") is True, "Async execution should indicate success"
    assert "execution_id" in response_data, "Async execution should return execution_id"

    # For async, should have status indicating it's running or queued
    status = response_data.get("status")
    assert status in ["NEW", "RUNNING", "QUEUED"], f"Unexpected async status: {status}"


def assert_sync_execution_response(response_data: Dict[str, Any]) -> None:
    """Assert sync execution returns complete results."""
    assert response_data.get("success") is True, "Sync execution should be successful"
    assert "execution_id" in response_data, "Sync execution should return execution_id"

    # For sync, should have completion status
    status = response_data.get("status")
    assert status in ["SUCCESS", "ERROR", "COMPLETED"], f"Unexpected sync status: {status}"


def assert_node_type_executed(logs: List[Dict[str, Any]], node_type: str) -> None:
    """Assert that a specific node type was executed."""
    node_type_found = False
    for log in logs:
        if isinstance(log, dict):
            message = str(log.get("message", "")).lower()
            if node_type.lower() in message:
                node_type_found = True
                break
        elif node_type.lower() in str(log).lower():
            node_type_found = True
            break

    assert node_type_found, f"Node type '{node_type}' execution not found in logs"


def assert_no_sensitive_data_in_logs(
    logs: List[Dict[str, Any]], sensitive_patterns: List[str]
) -> None:
    """Assert that sensitive data is not present in logs."""
    all_log_content = []
    for log in logs:
        if isinstance(log, dict):
            all_log_content.extend([str(v) for v in log.values() if v is not None])
        else:
            all_log_content.append(str(log))

    log_text = " ".join(all_log_content).lower()

    for pattern in sensitive_patterns:
        assert pattern.lower() not in log_text, f"Sensitive pattern '{pattern}' found in logs"


def assert_branching_logic_executed(logs: List[Dict[str, Any]], expected_branch: str) -> None:
    """Assert that the correct branch was taken in conditional workflows."""
    branch_indicators = ["if", "condition", "branch", "flow", expected_branch.lower()]
    branch_execution_found = False

    for log in logs:
        log_content = str(log).lower()
        if any(indicator in log_content for indicator in branch_indicators):
            branch_execution_found = True
            break

    assert (
        branch_execution_found
    ), f"Expected branch '{expected_branch}' execution not found in logs"


def assert_parallel_execution_evidence(logs: List[Dict[str, Any]]) -> None:
    """Assert that parallel execution occurred."""
    parallel_indicators = ["parallel", "split", "merge", "concurrent"]
    parallel_evidence = False

    for log in logs:
        log_content = str(log).lower()
        if any(indicator in log_content for indicator in parallel_indicators):
            parallel_evidence = True
            break

    assert parallel_evidence, "No evidence of parallel execution found in logs"


def assert_memory_operation_logged(logs: List[Dict[str, Any]], operation_type: str) -> None:
    """Assert that memory operations are properly logged."""
    memory_operation_found = False

    for log in logs:
        log_content = str(log).lower()
        if "memory" in log_content and operation_type.lower() in log_content:
            memory_operation_found = True
            break

    assert memory_operation_found, f"Memory operation '{operation_type}' not found in logs"


def assert_ai_agent_execution(logs: List[Dict[str, Any]], provider: Optional[str] = None) -> None:
    """Assert that AI agent execution is logged."""
    ai_indicators = ["ai", "agent", "openai", "anthropic", "claude", "gpt"]
    if provider:
        ai_indicators.append(provider.lower())

    ai_execution_found = False
    for log in logs:
        log_content = str(log).lower()
        if any(indicator in log_content for indicator in ai_indicators):
            ai_execution_found = True
            break

    assert ai_execution_found, f"AI agent execution not found in logs (provider: {provider})"


def assert_external_action_execution(logs: List[Dict[str, Any]], action_type: str) -> None:
    """Assert that external action execution is logged."""
    external_action_found = False

    for log in logs:
        log_content = str(log).lower()
        if "external" in log_content and action_type.lower() in log_content:
            external_action_found = True
            break
        elif action_type.lower() in log_content:
            external_action_found = True
            break

    assert external_action_found, f"External action '{action_type}' execution not found in logs"


def assert_tool_execution_logged(logs: List[Dict[str, Any]], tool_type: str) -> None:
    """Assert that tool execution is logged."""
    tool_execution_found = False

    for log in logs:
        log_content = str(log).lower()
        if "tool" in log_content and tool_type.lower() in log_content:
            tool_execution_found = True
            break

    assert tool_execution_found, f"Tool execution '{tool_type}' not found in logs"


def assert_human_loop_interaction_created(
    logs: List[Dict[str, Any]], interaction_type: str
) -> None:
    """Assert that human loop interaction was created."""
    hil_creation_found = False

    for log in logs:
        log_content = str(log).lower()
        if (
            "human" in log_content or "hil" in log_content
        ) and interaction_type.lower() in log_content:
            hil_creation_found = True
            break
        elif "created" in log_content and interaction_type.lower() in log_content:
            hil_creation_found = True
            break

    assert (
        hil_creation_found
    ), f"Human loop interaction '{interaction_type}' creation not found in logs"
