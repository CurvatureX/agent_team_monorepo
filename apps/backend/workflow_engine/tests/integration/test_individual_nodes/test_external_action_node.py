from typing import Any, Dict

import pytest

from shared.models.node_enums import ExternalActionSubtype, NodeType
from workflow_engine.tests.integration.utils.assertions import (
    assert_execution_success_status,
    assert_log_contains,
)
from workflow_engine.tests.integration.utils.workflow_factory import node, single_node_workflow


@pytest.mark.asyncio
async def test_slack_integration_mock(app_client, patch_workflow_definition, in_memory_logs):
    """Test Slack integration with mock token (no real API key)."""
    slack_node = node(
        "n1",
        ntype=NodeType.EXTERNAL_ACTION.value,
        subtype=ExternalActionSubtype.SLACK.value,
        parameters={
            "action_type": "slack",
            "channel": "#test-channel",
            "message": "Test message from workflow",
            "username": "Workflow Bot",
        },
    )
    wf = single_node_workflow(slack_node)
    patch_workflow_definition(wf)

    # Execute workflow
    resp = await app_client.post(
        "/v1/workflows/wf_slack/execute",
        json={
            "workflow_id": "wf_slack",
            "user_id": "u1",
            "trigger_data": {"source": "test"},
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Assert execution success
    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs contain Slack execution
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of EXTERNAL_ACTION node")


@pytest.mark.asyncio
async def test_webhook_posting(app_client, patch_workflow_definition, in_memory_logs):
    """Test webhook posting functionality."""
    webhook_node = node(
        "n1",
        ntype=NodeType.EXTERNAL_ACTION.value,
        subtype=ExternalActionSubtype.WEBHOOK.value,
        parameters={
            "action_type": "webhook",
            "url": "https://httpbin.org/post",
            "method": "POST",
            "payload": {"message": "Test webhook payload"},
            "headers": {"Content-Type": "application/json"},
        },
    )
    wf = single_node_workflow(webhook_node)
    patch_workflow_definition(wf)

    # Execute workflow
    resp = await app_client.post(
        "/v1/workflows/wf_webhook/execute",
        json={
            "workflow_id": "wf_webhook",
            "user_id": "u1",
            "trigger_data": {"test": "true"},
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Assert execution success
    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs contain webhook execution
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of EXTERNAL_ACTION node")


@pytest.mark.asyncio
async def test_email_sending_mock(app_client, patch_workflow_definition, in_memory_logs):
    """Test email sending with mock SMTP."""
    email_node = node(
        "n1",
        ntype=NodeType.EXTERNAL_ACTION.value,
        subtype=ExternalActionSubtype.EMAIL.value,
        parameters={
            "action_type": "email",
            "to_email": "test@example.com",
            "subject": "Test Email",
            "body": "This is a test email from the workflow engine.",
        },
    )
    wf = single_node_workflow(email_node)
    patch_workflow_definition(wf)

    # Execute workflow
    resp = await app_client.post(
        "/v1/workflows/wf_email/execute",
        json={
            "workflow_id": "wf_email",
            "user_id": "u1",
            "trigger_data": {"context": "test_run"},
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Assert execution success
    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs contain email execution
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of EXTERNAL_ACTION node")


@pytest.mark.asyncio
async def test_channel_parameter_validation(app_client, patch_workflow_definition):
    """Test Slack channel parameter requirements."""
    # Missing channel parameter should still execute (validation is permissive in current implementation)
    slack_node = node(
        "n1",
        ntype=NodeType.EXTERNAL_ACTION.value,
        subtype=ExternalActionSubtype.SLACK.value,
        parameters={"action_type": "slack", "message": "Test message without channel"},
    )
    wf = single_node_workflow(slack_node)
    patch_workflow_definition(wf)

    resp = await app_client.post(
        "/v1/workflows/wf_slack_validation/execute",
        json={
            "workflow_id": "wf_slack_validation",
            "user_id": "u1",
            "trigger_data": {},
            "async_execution": False,
        },
    )

    # Should still succeed (current implementation is permissive)
    assert resp.status_code == 200
    assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_integration_error_handling(app_client, patch_workflow_definition, in_memory_logs):
    """Test error handling for failed external integrations."""
    # Use invalid URL to trigger error
    webhook_node = node(
        "n1",
        ntype=NodeType.EXTERNAL_ACTION.value,
        subtype=ExternalActionSubtype.WEBHOOK.value,
        parameters={
            "action_type": "webhook",
            "url": "invalid-url-format",
            "method": "POST",
            "payload": {"test": True},
        },
    )
    wf = single_node_workflow(webhook_node)
    patch_workflow_definition(wf)

    # Execute workflow
    resp = await app_client.post(
        "/v1/workflows/wf_error/execute",
        json={
            "workflow_id": "wf_error",
            "user_id": "u1",
            "trigger_data": {},
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Should handle error gracefully
    assert resp.status_code == 200

    # Check logs for error handling
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    # External action node should log execution attempt
    assert_log_contains(logs, "Starting execution of EXTERNAL_ACTION node")
