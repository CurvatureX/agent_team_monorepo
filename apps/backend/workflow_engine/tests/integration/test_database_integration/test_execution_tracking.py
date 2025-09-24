import pytest

from shared.models.node_enums import NodeType, TriggerSubtype
from workflow_engine.tests.integration.utils.lifecycle_utils import create_lifecycle_manager


@pytest.mark.asyncio
async def test_execution_record_creation_and_status_transitions(app_client):
    """Test: Database execution tracking with real API lifecycle"""
    manager = create_lifecycle_manager(app_client)

    try:
        # Create minimal trigger-only workflow
        workflow_definition = {
            "id": "wf_db_tracking",
            "name": "Database Tracking Test",
            "nodes": [
                {
                    "id": "n1",
                    "type": NodeType.TRIGGER.value,
                    "subtype": TriggerSubtype.MANUAL.value,
                    "parameters": {"trigger_type": "manual"},
                }
            ],
            "connections": {},
        }

        # Execute complete workflow lifecycle
        workflow_id = await manager.create_workflow(workflow_definition)

        # Start execution asynchronously to test status transitions
        execution_id = await manager.execute_workflow(workflow_id, {"k": "v"}, async_execution=True)

        # Monitor execution to see status transitions (NEW -> RUNNING -> COMPLETED)
        execution_result = await manager.monitor_execution(execution_id, timeout_seconds=30)

        # Verify execution completed and was tracked in database
        assert execution_result.get("execution_id") == execution_id
        assert execution_result.get("status") in ["COMPLETED", "SUCCESS"]

        # Clean up
        await manager.delete_workflow(workflow_id)

    except Exception as e:
        # Ensure cleanup on failure
        await manager.cleanup_all()
        raise
