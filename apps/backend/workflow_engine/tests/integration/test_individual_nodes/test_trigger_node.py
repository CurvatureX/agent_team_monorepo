from typing import Any, Dict

import pytest

from shared.models.node_enums import NodeType, TriggerSubtype
from workflow_engine.tests.integration.utils.assertions import (
    assert_execution_success_status,
    assert_log_contains,
)
from workflow_engine.tests.integration.utils.lifecycle_utils import create_lifecycle_manager
from workflow_engine.tests.integration.utils.workflow_factory import node, single_node_workflow


@pytest.mark.asyncio
async def test_manual_trigger_basic(app_client):
    """Test: TRIGGER node with manual trigger using real API lifecycle"""
    manager = create_lifecycle_manager(app_client)

    try:
        # Create workflow definition
        trigger = node(
            "n1",
            ntype=NodeType.TRIGGER.value,
            subtype=TriggerSubtype.MANUAL.value,
            parameters={"trigger_type": "manual", "user_id": "tester"},
        )
        workflow_definition = single_node_workflow(trigger)

        # Execute complete workflow lifecycle
        workflow_id = await manager.create_workflow(workflow_definition)
        execution_result = await manager.execute_and_wait(
            workflow_id, {"message": "hello"}, timeout_seconds=30
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
async def test_trigger_parameter_validation(app_client):
    """Test: TRIGGER node parameter validation using real API lifecycle"""
    manager = create_lifecycle_manager(app_client)

    try:
        # Create webhook trigger workflow
        trigger = node(
            "n1",
            ntype=NodeType.TRIGGER.value,
            subtype=TriggerSubtype.WEBHOOK.value,
            parameters={"trigger_type": "webhook"},
        )
        workflow_definition = single_node_workflow(trigger)

        # Execute complete workflow lifecycle
        workflow_id = await manager.create_workflow(workflow_definition)
        execution_result = await manager.execute_and_wait(
            workflow_id, {"payload": '{"action": "push"}'}, timeout_seconds=30
        )

        # Verify execution completed
        assert execution_result.get("execution_id")

        # Clean up
        await manager.delete_workflow(workflow_id)

    except Exception as e:
        # Ensure cleanup on failure
        await manager.cleanup_all()
        raise
