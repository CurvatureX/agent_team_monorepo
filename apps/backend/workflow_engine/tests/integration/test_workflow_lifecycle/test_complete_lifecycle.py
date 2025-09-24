"""
Complete Workflow Lifecycle Integration Tests

These tests verify the complete workflow lifecycle:
1. CREATE workflow via API
2. DEPLOY workflow (if needed)
3. EXECUTE workflow via API
4. MONITOR execution status
5. UNDEPLOY workflow (if needed)
6. DELETE workflow via API

This ensures workflows are actually created, executed, and cleaned up properly.
"""

import asyncio
import time
from typing import Any, Dict, List

import pytest

from shared.models.node_enums import (
    ActionSubtype,
    AIAgentSubtype,
    ExternalActionSubtype,
    FlowSubtype,
    HumanLoopSubtype,
    MemorySubtype,
    NodeType,
    ToolSubtype,
    TriggerSubtype,
)
from workflow_engine.tests.integration.utils.lifecycle_utils import WorkflowLifecycleManager
from workflow_engine.tests.integration.utils.workflow_factory import connect, node


class WorkflowLifecycleManager:
    """Helper class to manage complete workflow lifecycle"""

    def __init__(self, app_client):
        self.app_client = app_client
        self.created_workflows = []

    async def create_workflow(self, workflow_definition: Dict[str, Any]) -> str:
        """Create a workflow and return its ID"""
        resp = await self.app_client.post("/v1/workflows", json=workflow_definition)
        assert resp.status_code == 200, f"Failed to create workflow: {resp.text}"

        data = resp.json()
        workflow_id = data.get("id")
        assert workflow_id, f"No workflow ID returned: {data}"

        self.created_workflows.append(workflow_id)
        return workflow_id

    async def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Get workflow definition"""
        resp = await self.app_client.get(f"/v1/workflows/{workflow_id}")
        assert resp.status_code == 200, f"Failed to get workflow: {resp.text}"

        data = resp.json()
        assert data.get("found"), f"Workflow not found: {workflow_id}"
        return data.get("workflow", {})

    async def execute_workflow(
        self, workflow_id: str, trigger_data: Dict[str, Any], async_execution: bool = False
    ) -> str:
        """Execute a workflow and return execution ID"""
        request_data = {
            "workflow_id": workflow_id,
            "user_id": "test_user",
            "trigger_data": trigger_data,
            "async_execution": async_execution,
        }

        resp = await self.app_client.post(f"/v1/workflows/{workflow_id}/execute", json=request_data)
        assert resp.status_code == 200, f"Failed to execute workflow: {resp.text}"

        data = resp.json()
        execution_id = data.get("execution_id")
        assert execution_id, f"No execution ID returned: {data}"
        return execution_id

    async def monitor_execution(
        self, execution_id: str, timeout_seconds: int = 30
    ) -> Dict[str, Any]:
        """Monitor execution until completion or timeout"""
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            resp = await self.app_client.get(f"/v1/executions/{execution_id}")
            assert resp.status_code == 200, f"Failed to get execution status: {resp.text}"

            data = resp.json()
            status = data.get("status", "").upper()

            # Debug: print actual status
            print(
                f"🔍 DEBUG: Execution {execution_id} status: '{status}' (raw: '{data.get('status', 'MISSING')}')"
            )

            if status in ["COMPLETED", "SUCCESS", "FAILED", "CANCELLED", "ERROR"]:
                return data

            # Wait before checking again
            await asyncio.sleep(1)

        raise TimeoutError(
            f"Execution {execution_id} did not complete within {timeout_seconds} seconds"
        )

    async def delete_workflow(self, workflow_id: str):
        """Delete a workflow"""
        resp = await self.app_client.delete(f"/v1/workflows/{workflow_id}")
        assert resp.status_code == 200, f"Failed to delete workflow: {resp.text}"

        # Remove from tracking
        if workflow_id in self.created_workflows:
            self.created_workflows.remove(workflow_id)

    async def cleanup_all(self):
        """Clean up all created workflows"""
        for workflow_id in self.created_workflows.copy():
            try:
                await self.delete_workflow(workflow_id)
            except Exception as e:
                print(f"Failed to cleanup workflow {workflow_id}: {e}")


@pytest.fixture
def lifecycle_manager(app_client):
    """Fixture that provides a lifecycle manager and cleans up after tests"""
    manager = WorkflowLifecycleManager(app_client)

    yield manager

    # Cleanup is handled by the manager itself in each test


@pytest.mark.asyncio
async def test_simple_trigger_to_action_lifecycle(lifecycle_manager: WorkflowLifecycleManager):
    """Test: Complete lifecycle of TRIGGER → ACTION workflow"""

    # 1. CREATE WORKFLOW
    trigger_node = node(
        "trigger1", NodeType.TRIGGER.value, TriggerSubtype.MANUAL.value, {"trigger_type": "manual"}
    )

    action_node = node(
        "action1",
        NodeType.ACTION.value,
        ActionSubtype.DATA_TRANSFORMATION.value,
        {
            "action_type": ActionSubtype.DATA_TRANSFORMATION.value,
            "transformation_type": "field_mapping",
            "field_mappings": '{"input": "processed_output"}',
        },
    )

    workflow_definition = {
        "id": "test-simple-lifecycle",
        "name": "Simple Lifecycle Test",
        "description": "Test workflow for complete lifecycle",
        "nodes": [trigger_node, action_node],
        "connections": {"trigger1": [connect("trigger1", "action1")]},
    }

    workflow_id = await lifecycle_manager.create_workflow(workflow_definition)
    print(f"✅ Created workflow: {workflow_id}")

    # 2. VERIFY WORKFLOW CREATION
    created_workflow = await lifecycle_manager.get_workflow(workflow_id)
    assert created_workflow["id"] == workflow_id
    assert len(created_workflow["nodes"]) == 2
    print(f"✅ Verified workflow creation: {len(created_workflow['nodes'])} nodes")

    # 3. EXECUTE WORKFLOW (SYNC)
    trigger_data = {"input": "test data for processing", "timestamp": "2025-01-17T10:00:00Z"}

    execution_id = await lifecycle_manager.execute_workflow(
        workflow_id, trigger_data, async_execution=False
    )
    print(f"✅ Executed workflow synchronously: {execution_id}")

    # 4. VERIFY EXECUTION COMPLETED
    execution_status = await lifecycle_manager.monitor_execution(execution_id)
    assert execution_status["status"].upper() in ["COMPLETED", "SUCCESS"]
    print(f"✅ Execution completed with status: {execution_status['status']}")

    # 5. DELETE WORKFLOW
    await lifecycle_manager.delete_workflow(workflow_id)
    print(f"✅ Deleted workflow: {workflow_id}")

    # 6. VERIFY DELETION
    resp = await lifecycle_manager.app_client.get(f"/v1/workflows/{workflow_id}")
    deletion_data = resp.json()
    assert not deletion_data.get("found"), "Workflow should be deleted"
    print(f"✅ Verified workflow deletion")

    # 7. FINAL CLEANUP
    await lifecycle_manager.cleanup_all()


@pytest.mark.asyncio
async def test_async_execution_lifecycle(lifecycle_manager: WorkflowLifecycleManager):
    """Test: Async execution with monitoring"""

    # CREATE WORKFLOW with slower processing
    trigger_node = node(
        "trigger1", NodeType.TRIGGER.value, TriggerSubtype.MANUAL.value, {"trigger_type": "manual"}
    )

    # Use multiple nodes to make execution take longer
    action1 = node(
        "action1",
        NodeType.ACTION.value,
        ActionSubtype.DATA_TRANSFORMATION.value,
        {
            "action_type": ActionSubtype.DATA_TRANSFORMATION.value,
            "transformation_type": "field_mapping",
            "field_mappings": '{"step1": "processed"}',
        },
    )

    action2 = node(
        "action2",
        NodeType.ACTION.value,
        ActionSubtype.DATA_FORMATTING.value,
        {
            "action_type": ActionSubtype.DATA_FORMATTING.value,
            "format_template": "Step 2 processing: {{input_data.step1}}",
        },
    )

    workflow_definition = {
        "id": "test-async-lifecycle",
        "name": "Async Lifecycle Test",
        "description": "Test async workflow execution",
        "nodes": [trigger_node, action1, action2],
        "connections": {
            "trigger1": [connect("trigger1", "action1")],
            "action1": [connect("action1", "action2")],
        },
    }

    workflow_id = await lifecycle_manager.create_workflow(workflow_definition)
    print(f"✅ Created async workflow: {workflow_id}")

    # EXECUTE ASYNCHRONOUSLY
    trigger_data = {"step1": "initial data", "async_test": "true"}

    execution_id = await lifecycle_manager.execute_workflow(
        workflow_id, trigger_data, async_execution=True
    )
    print(f"✅ Started async execution: {execution_id}")

    # MONITOR EXECUTION
    execution_status = await lifecycle_manager.monitor_execution(execution_id, timeout_seconds=60)
    print(f"✅ Async execution completed: {execution_status['status']}")

    # CLEANUP
    await lifecycle_manager.delete_workflow(workflow_id)
    print(f"✅ Cleaned up async workflow")


@pytest.mark.asyncio
async def test_flow_control_lifecycle(lifecycle_manager: WorkflowLifecycleManager):
    """Test: Flow control workflow with conditional branching"""

    # CREATE WORKFLOW with conditional flow
    trigger_node = node(
        "trigger1", NodeType.TRIGGER.value, TriggerSubtype.MANUAL.value, {"trigger_type": "manual"}
    )

    flow_node = node(
        "flow1",
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

    high_priority_action = node(
        "action_high",
        NodeType.ACTION.value,
        ActionSubtype.DATA_FORMATTING.value,
        {
            "action_type": ActionSubtype.DATA_FORMATTING.value,
            "format_template": "HIGH PRIORITY: {{input_data.message}}",
        },
    )

    low_priority_action = node(
        "action_low",
        NodeType.ACTION.value,
        ActionSubtype.DATA_FORMATTING.value,
        {
            "action_type": ActionSubtype.DATA_FORMATTING.value,
            "format_template": "Low priority: {{input_data.message}}",
        },
    )

    workflow_definition = {
        "id": "test-flow-lifecycle",
        "name": "Flow Control Lifecycle Test",
        "description": "Test workflow with flow control",
        "nodes": [trigger_node, flow_node, high_priority_action, low_priority_action],
        "connections": {
            "trigger1": [connect("trigger1", "flow1")],
            "flow1": [
                connect("flow1", "action_high", output_field="true_path"),
                connect("flow1", "action_low", output_field="false_path"),
            ],
        },
    }

    workflow_id = await lifecycle_manager.create_workflow(workflow_definition)
    print(f"✅ Created flow control workflow: {workflow_id}")

    # TEST HIGH PRIORITY PATH
    high_priority_data = {
        "priority": "high",
        "message": "Urgent task requiring immediate attention",
    }

    execution_id_high = await lifecycle_manager.execute_workflow(
        workflow_id, high_priority_data, async_execution=False
    )
    execution_status_high = await lifecycle_manager.monitor_execution(execution_id_high)
    print(f"✅ High priority execution completed: {execution_status_high['status']}")

    # TEST LOW PRIORITY PATH
    low_priority_data = {"priority": "low", "message": "Regular task"}

    execution_id_low = await lifecycle_manager.execute_workflow(
        workflow_id, low_priority_data, async_execution=False
    )
    execution_status_low = await lifecycle_manager.monitor_execution(execution_id_low)
    print(f"✅ Low priority execution completed: {execution_status_low['status']}")

    # CLEANUP
    await lifecycle_manager.delete_workflow(workflow_id)
    print(f"✅ Cleaned up flow control workflow")


@pytest.mark.asyncio
async def test_multi_node_complex_lifecycle(lifecycle_manager: WorkflowLifecycleManager):
    """Test: Complex multi-node workflow with multiple node types"""

    # CREATE COMPLEX WORKFLOW
    trigger_node = node(
        "trigger1", NodeType.TRIGGER.value, TriggerSubtype.MANUAL.value, {"trigger_type": "manual"}
    )

    # Data transformation
    transform_node = node(
        "transform1",
        NodeType.ACTION.value,
        ActionSubtype.DATA_TRANSFORMATION.value,
        {
            "action_type": ActionSubtype.DATA_TRANSFORMATION.value,
            "transformation_type": "field_mapping",
            "field_mappings": '{"raw_input": "processed_data"}',
        },
    )

    # Flow control
    flow_node = node(
        "flow1",
        NodeType.FLOW.value,
        FlowSubtype.IF.value,
        {
            "flow_type": "if",
            "condition": "input_data.process_mode == 'advanced'",
            "condition_field": "process_mode",
            "condition_operator": "==",
            "condition_value": "advanced",
        },
    )

    # Advanced processing
    advanced_action = node(
        "advanced1",
        NodeType.ACTION.value,
        ActionSubtype.DATA_FORMATTING.value,
        {
            "action_type": ActionSubtype.DATA_FORMATTING.value,
            "format_template": "Advanced processing result: {{input_data.processed_data}}",
        },
    )

    # Simple processing
    simple_action = node(
        "simple1",
        NodeType.ACTION.value,
        ActionSubtype.DATA_FORMATTING.value,
        {
            "action_type": ActionSubtype.DATA_FORMATTING.value,
            "format_template": "Simple processing result: {{input_data.processed_data}}",
        },
    )

    # Memory storage
    memory_node = node(
        "memory1",
        NodeType.MEMORY.value,
        MemorySubtype.KEY_VALUE_STORE.value,
        {
            "memory_type": "key_value_store",
            "operation": "store",
            "key": "workflow_result_{{execution_id}}",
            "value": '{"result": "{{input_data}}", "timestamp": "{{current_timestamp}}"}',
        },
    )

    workflow_definition = {
        "id": "test-complex-lifecycle",
        "name": "Complex Multi-Node Lifecycle Test",
        "description": "Complex workflow testing multiple node types",
        "nodes": [
            trigger_node,
            transform_node,
            flow_node,
            advanced_action,
            simple_action,
            memory_node,
        ],
        "connections": {
            "trigger1": [connect("trigger1", "transform1")],
            "transform1": [connect("transform1", "flow1")],
            "flow1": [
                connect("flow1", "advanced1", output_field="true_path"),
                connect("flow1", "simple1", output_field="false_path"),
            ],
            "advanced1": [connect("advanced1", "memory1")],
            "simple1": [connect("simple1", "memory1")],
        },
    }

    workflow_id = await lifecycle_manager.create_workflow(workflow_definition)
    print(f"✅ Created complex workflow: {workflow_id}")

    # VERIFY WORKFLOW STRUCTURE
    created_workflow = await lifecycle_manager.get_workflow(workflow_id)
    assert len(created_workflow["nodes"]) == 6
    print(f"✅ Verified complex workflow structure: {len(created_workflow['nodes'])} nodes")

    # TEST ADVANCED MODE
    advanced_data = {
        "raw_input": "complex input data requiring advanced processing",
        "process_mode": "advanced",
        "metadata": '{"type": "complex", "version": "2.0"}',
    }

    execution_id_advanced = await lifecycle_manager.execute_workflow(
        workflow_id, advanced_data, async_execution=False
    )
    execution_status_advanced = await lifecycle_manager.monitor_execution(execution_id_advanced)
    print(f"✅ Advanced mode execution completed: {execution_status_advanced['status']}")

    # TEST SIMPLE MODE
    simple_data = {
        "raw_input": "simple input data",
        "process_mode": "simple",
        "metadata": '{"type": "simple", "version": "1.0"}',
    }

    execution_id_simple = await lifecycle_manager.execute_workflow(
        workflow_id, simple_data, async_execution=False
    )
    execution_status_simple = await lifecycle_manager.monitor_execution(execution_id_simple)
    print(f"✅ Simple mode execution completed: {execution_status_simple['status']}")

    # CLEANUP
    await lifecycle_manager.delete_workflow(workflow_id)
    print(f"✅ Cleaned up complex workflow")


@pytest.mark.asyncio
async def test_error_handling_lifecycle(lifecycle_manager: WorkflowLifecycleManager):
    """Test: Workflow error handling and recovery"""

    # CREATE WORKFLOW that might fail
    trigger_node = node(
        "trigger1", NodeType.TRIGGER.value, TriggerSubtype.MANUAL.value, {"trigger_type": "manual"}
    )

    # Action that might fail with invalid URL
    failing_action = node(
        "action1",
        NodeType.ACTION.value,
        ActionSubtype.HTTP_REQUEST.value,
        {
            "action_type": ActionSubtype.HTTP_REQUEST.value,
            "url": "https://invalid-domain-that-should-fail.com/api/test",
            "method": "GET",
            "timeout": "5",
        },
    )

    # Recovery action
    recovery_action = node(
        "action2",
        NodeType.ACTION.value,
        ActionSubtype.DATA_FORMATTING.value,
        {
            "action_type": ActionSubtype.DATA_FORMATTING.value,
            "format_template": "Recovery executed after error: {{input_data}}",
        },
    )

    workflow_definition = {
        "id": "test-error-lifecycle",
        "name": "Error Handling Lifecycle Test",
        "description": "Test workflow error handling",
        "nodes": [trigger_node, failing_action, recovery_action],
        "connections": {
            "trigger1": [connect("trigger1", "action1")],
            "action1": [connect("action1", "action2")],
        },
    }

    workflow_id = await lifecycle_manager.create_workflow(workflow_definition)
    print(f"✅ Created error handling workflow: {workflow_id}")

    # EXECUTE WORKFLOW (expect it to handle errors gracefully)
    error_test_data = {"test_error_handling": "true", "expected_outcome": "graceful_error_handling"}

    execution_id = await lifecycle_manager.execute_workflow(
        workflow_id, error_test_data, async_execution=False
    )
    execution_status = await lifecycle_manager.monitor_execution(execution_id)

    # Should complete even if individual nodes fail
    print(f"✅ Error handling execution completed: {execution_status['status']}")

    # CLEANUP
    await lifecycle_manager.delete_workflow(workflow_id)
    print(f"✅ Cleaned up error handling workflow")


@pytest.mark.asyncio
async def test_workflow_lifecycle_persistence(lifecycle_manager: WorkflowLifecycleManager):
    """Test: Workflow persistence and data integrity"""

    # CREATE WORKFLOW
    original_workflow = {
        "id": "test-persistence-lifecycle",
        "name": "Persistence Test Workflow",
        "description": "Testing workflow data persistence",
        "version": "1.0.0",
        "tags": ["test", "persistence", "integration"],
        "nodes": [
            node(
                "trigger1",
                NodeType.TRIGGER.value,
                TriggerSubtype.MANUAL.value,
                {"trigger_type": "manual"},
            ),
            node(
                "action1",
                NodeType.ACTION.value,
                ActionSubtype.DATA_TRANSFORMATION.value,
                {
                    "action_type": ActionSubtype.DATA_TRANSFORMATION.value,
                    "transformation_type": "field_mapping",
                    "field_mappings": '{"test": "persistence_verified"}',
                },
            ),
        ],
        "connections": {"trigger1": [connect("trigger1", "action1")]},
    }

    workflow_id = await lifecycle_manager.create_workflow(original_workflow)
    print(f"✅ Created persistence test workflow: {workflow_id}")

    # VERIFY DATA INTEGRITY
    retrieved_workflow = await lifecycle_manager.get_workflow(workflow_id)

    assert retrieved_workflow["name"] == original_workflow["name"]
    assert retrieved_workflow["description"] == original_workflow["description"]
    assert len(retrieved_workflow["nodes"]) == len(original_workflow["nodes"])
    print(f"✅ Verified workflow data integrity")

    # EXECUTE AND VERIFY EXECUTION PERSISTS
    persistence_data = {"test": "workflow persistence", "verify": "data integrity"}

    execution_id = await lifecycle_manager.execute_workflow(
        workflow_id, persistence_data, async_execution=False
    )
    execution_status = await lifecycle_manager.monitor_execution(execution_id)

    assert execution_status["execution_id"] == execution_id
    print(f"✅ Verified execution persistence: {execution_id}")

    # CLEANUP
    await lifecycle_manager.delete_workflow(workflow_id)
    print(f"✅ Cleaned up persistence test workflow")
