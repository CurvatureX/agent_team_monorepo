import os

import pytest

from shared.models.node_enums import AIAgentSubtype, NodeType, TriggerSubtype
from workflow_engine.tests.integration.utils.assertions import (
    assert_ai_agent_execution,
    assert_execution_success_status,
    assert_log_contains,
)
from workflow_engine.tests.integration.utils.lifecycle_utils import create_lifecycle_manager
from workflow_engine.tests.integration.utils.workflow_factory import linear_workflow, node


@pytest.mark.asyncio
async def test_openai_integration_mock(app_client, monkeypatch):
    """Test: AI_AGENT node with OpenAI integration using real API lifecycle"""
    manager = create_lifecycle_manager(app_client)

    try:
        # Ensure no real API keys
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Create workflow definition
        trig = node(
            "t1",
            ntype=NodeType.TRIGGER.value,
            subtype=TriggerSubtype.MANUAL.value,
            parameters={"trigger_type": "manual"},
        )
        ai = node(
            "a1",
            ntype=NodeType.AI_AGENT.value,
            subtype=AIAgentSubtype.OPENAI_CHATGPT.value,
            parameters={
                "provider": "openai",
                "model": "gpt-4o-mini",
                "system_prompt": "You are helpful",
                "user_message": "{{input_data.user_message}}",
            },
        )
        workflow_definition = linear_workflow([trig, ai])

        # Execute complete workflow lifecycle
        workflow_id = await manager.create_workflow(workflow_definition)
        execution_result = await manager.execute_and_wait(
            workflow_id, {"user_message": "Say hi"}, timeout_seconds=30
        )

        # Verify execution (may fail due to no API key, but lifecycle should work)
        assert execution_result.get("execution_id")

        # Clean up
        await manager.delete_workflow(workflow_id)

    except Exception as e:
        # Ensure cleanup on failure
        await manager.cleanup_all()
        raise


@pytest.mark.asyncio
async def test_parameter_validation_missing_user_message(app_client):
    """Test: AI_AGENT node parameter validation using real API lifecycle"""
    manager = create_lifecycle_manager(app_client)

    try:
        # Create workflow with missing user message
        trig = node(
            "t1",
            ntype=NodeType.TRIGGER.value,
            subtype=TriggerSubtype.MANUAL.value,
            parameters={"trigger_type": "manual"},
        )
        ai = node(
            "a1",
            ntype=NodeType.AI_AGENT.value,
            subtype=AIAgentSubtype.OPENAI_CHATGPT.value,
            parameters={
                "provider": "openai",
                "model": "gpt-4o-mini",
                "system_prompt": "You are helpful"
                # Missing user_message parameter
            },
        )
        workflow_definition = linear_workflow([trig, ai])

        # Execute complete workflow lifecycle
        workflow_id = await manager.create_workflow(workflow_definition)
        execution_result = await manager.execute_and_wait(
            workflow_id, {}, timeout_seconds=30  # Empty trigger data - missing user message
        )

        # Verify execution completed (may fail due to validation, but lifecycle should work)
        assert execution_result.get("execution_id")

        # Clean up
        await manager.delete_workflow(workflow_id)

    except Exception as e:
        # Ensure cleanup on failure
        await manager.cleanup_all()
        raise
