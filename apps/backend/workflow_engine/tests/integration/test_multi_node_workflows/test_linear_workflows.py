import pytest

from shared.models.node_enums import AIAgentSubtype, ExternalActionSubtype, NodeType, TriggerSubtype
from workflow_engine.tests.integration.utils.assertions import assert_execution_success_status
from workflow_engine.tests.integration.utils.lifecycle_utils import create_lifecycle_manager
from workflow_engine.tests.integration.utils.workflow_factory import linear_workflow, node


@pytest.mark.asyncio
async def test_trigger_to_ai_to_slack(app_client):
    """Test: Linear workflow TRIGGER → AI_AGENT → EXTERNAL_ACTION using real API lifecycle"""
    manager = create_lifecycle_manager(app_client)

    try:
        # Create workflow definition using proper enums
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
                "system_prompt": "Summarize this message",
                "user_message": "{{input_data.user_message}}",
            },
        )
        slack = node(
            "s1",
            ntype=NodeType.EXTERNAL_ACTION.value,
            subtype=ExternalActionSubtype.SLACK.value,
            parameters={
                "action_type": "slack",
                "channel": "#random",
                "message": "{{input_data.ai_response}}",
            },
        )
        workflow_definition = linear_workflow([trig, ai, slack])

        # Execute complete workflow lifecycle
        workflow_id = await manager.create_workflow(workflow_definition)
        execution_result = await manager.execute_and_wait(
            workflow_id,
            {"user_message": "Hello, please process this message"},
            timeout_seconds=45,  # Longer timeout for multi-node workflow
        )

        # Verify execution succeeded
        assert_execution_success_status(execution_result)

        # Clean up
        await manager.delete_workflow(workflow_id)

    except Exception as e:
        # Ensure cleanup on failure
        await manager.cleanup_all()
        raise
