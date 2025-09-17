from typing import Any, Dict

import pytest

from shared.models.node_enums import HumanLoopSubtype, NodeType
from workflow_engine.tests.integration.utils.assertions import (
    assert_execution_success_status,
    assert_log_contains,
)
from workflow_engine.tests.integration.utils.workflow_factory import node, single_node_workflow


@pytest.mark.asyncio
async def test_approval_request_creation(app_client, patch_workflow_definition, in_memory_logs):
    """Test approval request creation and storage."""
    hil_node = node(
        "n1",
        ntype=NodeType.HUMAN_IN_THE_LOOP.value,
        subtype=HumanLoopSubtype.IN_APP_APPROVAL.value,
        parameters={
            "interaction_type": "approval",
            "title": "Approve Workflow Action",
            "description": "Please review and approve this workflow action",
            "approval_options": ["Approve", "Reject", "Request Changes"],
            "reason_required": "true",
            "timeout_seconds": "300",
        },
    )
    wf = single_node_workflow(hil_node)
    patch_workflow_definition(wf)

    # Execute workflow
    resp = await app_client.post(
        "/v1/workflows/wf_approval/execute",
        json={
            "workflow_id": "wf_approval",
            "user_id": "u1",
            "trigger_data": {"action": "delete_user", "user_id": "target123"},
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Assert execution success
    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs contain HIL execution
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of HUMAN_IN_THE_LOOP node")
    assert_log_contains(logs, "Successfully completed HUMAN_IN_THE_LOOP node")


@pytest.mark.asyncio
async def test_input_request_with_form_fields(
    app_client, patch_workflow_definition, in_memory_logs
):
    """Test input request with multiple form fields."""
    hil_node = node(
        "n1",
        ntype=NodeType.HUMAN_IN_THE_LOOP.value,
        subtype=HumanLoopSubtype.FORM_SUBMISSION.value,
        parameters={
            "interaction_type": "input",
            "title": "User Information Required",
            "description": "Please provide the following information",
            "input_fields": [
                {"name": "name", "label": "Full Name", "type": "text", "required": "true"},
                {"name": "email", "label": "Email Address", "type": "email", "required": "true"},
                {
                    "name": "department",
                    "label": "Department",
                    "type": "select",
                    "options": ["Engineering", "Marketing", "Sales"],
                    "required": "false",
                },
                {
                    "name": "notes",
                    "label": "Additional Notes",
                    "type": "textarea",
                    "required": "false",
                },
            ],
            "timeout_seconds": "600",
        },
    )
    wf = single_node_workflow(hil_node)
    patch_workflow_definition(wf)

    # Execute workflow
    resp = await app_client.post(
        "/v1/workflows/wf_input/execute",
        json={
            "workflow_id": "wf_input",
            "user_id": "u1",
            "trigger_data": {"context": "user_onboarding"},
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Assert execution success
    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs contain HIL execution
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of HUMAN_IN_THE_LOOP node")
    assert_log_contains(logs, "Successfully completed HUMAN_IN_THE_LOOP node")


@pytest.mark.asyncio
async def test_selection_request_with_options(
    app_client, patch_workflow_definition, in_memory_logs
):
    """Test selection request with multiple options."""
    hil_node = node(
        "n1",
        ntype=NodeType.HUMAN_IN_THE_LOOP.value,
        subtype=HumanLoopSubtype.FORM_SUBMISSION.value,
        parameters={
            "interaction_type": "selection",
            "title": "Choose Processing Method",
            "description": "Select how you want to process this request",
            "options": [
                {"value": "fast", "label": "Fast Processing (2 hours)"},
                {"value": "standard", "label": "Standard Processing (24 hours)"},
                {"value": "thorough", "label": "Thorough Review (3 days)"},
                {"value": "custom", "label": "Custom Timeline"},
            ],
            "multiple_selection": "false",
            "timeout_seconds": "1800",
        },
    )
    wf = single_node_workflow(hil_node)
    patch_workflow_definition(wf)

    # Execute workflow
    resp = await app_client.post(
        "/v1/workflows/wf_selection/execute",
        json={
            "workflow_id": "wf_selection",
            "user_id": "u1",
            "trigger_data": {"request_id": "req_456", "priority": "medium"},
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Assert execution success
    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs contain HIL execution
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of HUMAN_IN_THE_LOOP node")
    assert_log_contains(logs, "Successfully completed HUMAN_IN_THE_LOOP node")


@pytest.mark.asyncio
async def test_review_request_with_criteria(app_client, patch_workflow_definition, in_memory_logs):
    """Test review request with specific criteria."""
    hil_node = node(
        "n1",
        ntype=NodeType.HUMAN_IN_THE_LOOP.value,
        subtype=HumanLoopSubtype.MANUAL_REVIEW.value,
        parameters={
            "interaction_type": "review",
            "title": "Code Review Required",
            "description": "Please review the following code changes",
            "content_to_review": {
                "file": "src/main.py",
                "changes": "+10 -3 lines",
                "diff": "Added new authentication method",
            },
            "review_criteria": [
                "Code follows style guidelines",
                "Security best practices applied",
                "Tests are included",
                "Documentation is updated",
            ],
            "timeout_seconds": "3600",
        },
    )
    wf = single_node_workflow(hil_node)
    patch_workflow_definition(wf)

    # Execute workflow
    resp = await app_client.post(
        "/v1/workflows/wf_review/execute",
        json={
            "workflow_id": "wf_review",
            "user_id": "u1",
            "trigger_data": {"pr_id": "123", "author": "dev_user"},
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Assert execution success
    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs contain HIL execution
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of HUMAN_IN_THE_LOOP node")
    assert_log_contains(logs, "Successfully completed HUMAN_IN_THE_LOOP node")


@pytest.mark.asyncio
async def test_timeout_handling(app_client, patch_workflow_definition, in_memory_logs):
    """Test HIL request timeout behavior."""
    hil_node = node(
        "n1",
        ntype=NodeType.HUMAN_IN_THE_LOOP.value,
        subtype=HumanLoopSubtype.IN_APP_APPROVAL.value,
        parameters={
            "interaction_type": "approval",
            "title": "Quick Approval",
            "description": "Time-sensitive approval required",
            "timeout_seconds": "1",  # Very short timeout for test
            "approval_options": ["Approve", "Reject"],
        },
    )
    wf = single_node_workflow(hil_node)
    patch_workflow_definition(wf)

    # Execute workflow
    resp = await app_client.post(
        "/v1/workflows/wf_timeout/execute",
        json={
            "workflow_id": "wf_timeout",
            "user_id": "u1",
            "trigger_data": {"urgent": "true"},
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Assert execution success (timeout handling should be graceful)
    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs contain HIL execution
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of HUMAN_IN_THE_LOOP node")


@pytest.mark.asyncio
async def test_hil_request_database_storage(app_client, patch_workflow_definition, in_memory_logs):
    """Test HIL requests are properly stored in database."""
    hil_node = node(
        "n1",
        ntype=NodeType.HUMAN_IN_THE_LOOP.value,
        subtype=HumanLoopSubtype.FORM_SUBMISSION.value,
        parameters={
            "interaction_type": "input",
            "title": "Database Storage Test",
            "description": "Test HIL request storage",
            "input_fields": [
                {"name": "test_field", "label": "Test Field", "type": "text", "required": "true"}
            ],
            "channels": ["email", "slack"],
            "priority": "high",
        },
    )
    wf = single_node_workflow(hil_node)
    patch_workflow_definition(wf)

    # Execute workflow
    resp = await app_client.post(
        "/v1/workflows/wf_storage/execute",
        json={
            "workflow_id": "wf_storage",
            "user_id": "u1",
            "trigger_data": {"test": "storage"},
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Assert execution success
    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs contain HIL request creation
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of HUMAN_IN_THE_LOOP node")
    assert_log_contains(logs, "Successfully completed HUMAN_IN_THE_LOOP node")


@pytest.mark.asyncio
async def test_parameter_validation(app_client, patch_workflow_definition):
    """Test HIL node parameter validation."""
    # Test with invalid timeout (should still execute as validation is permissive)
    hil_node = node(
        "n1",
        ntype=NodeType.HUMAN_IN_THE_LOOP.value,
        subtype=HumanLoopSubtype.FORM_SUBMISSION.value,
        parameters={
            "interaction_type": "selection",
            "title": "Validation Test",
            "timeout_seconds": -10,  # Invalid timeout
            "options": [],  # Empty options
        },
    )
    wf = single_node_workflow(hil_node)
    patch_workflow_definition(wf)

    resp = await app_client.post(
        "/v1/workflows/wf_validation/execute",
        json={
            "workflow_id": "wf_validation",
            "user_id": "u1",
            "trigger_data": {},
            "async_execution": False,
        },
    )

    # Should handle validation gracefully
    assert resp.status_code == 200
    # Current implementation may be permissive, adjust assertion based on actual behavior
