"""
Test service layer components for workflow_engine_v2.
"""
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models import ExecutionStatus
from shared.models.node_enums import (
    ActionSubtype,
    AIAgentSubtype,
    ExternalActionSubtype,
    FlowSubtype,
    NodeType,
    TriggerSubtype,
)
from shared.models.workflow_new import Connection, Node, Workflow, WorkflowMetadata
from workflow_engine_v2.services.supabase_repository_v2 import SupabaseExecutionRepositoryV2
from workflow_engine_v2.services.unified_log_service import UnifiedLogServiceV2
from workflow_engine_v2.services.validation_service import ValidationServiceV2
from workflow_engine_v2.services.workflow_status_manager import WorkflowStatusManagerV2


class TestValidationServiceV2:
    """Test workflow validation service."""

    @pytest.fixture
    def validation_service(self):
        return ValidationServiceV2()

    @pytest.fixture
    def valid_workflow(self):
        """Create a valid workflow for testing."""
        metadata = WorkflowMetadata(
            id="test_workflow",
            name="Test Workflow",
            created_time=int(datetime.utcnow().timestamp() * 1000),
            created_by="test_user",
        )

        nodes = [
            Node(
                id="trigger_1",
                type=NodeType.TRIGGER.value,
                subtype=TriggerSubtype.WEBHOOK.value,
                configurations={"port": 8080},
            ),
            Node(
                id="action_1",
                type=NodeType.ACTION.value,
                subtype=ActionSubtype.HTTP_REQUEST.value,
                configurations={"url": "https://api.example.com", "method": "GET"},
            ),
        ]

        connections = [
            Connection(
                id="conn_1",
                from_node="trigger_1",
                to_node="action_1",
                output_key="result",
            )
        ]

        return Workflow(
            metadata=metadata, nodes=nodes, connections=connections, triggers=["trigger_1"]
        )

    def test_validate_valid_workflow(self, validation_service, valid_workflow):
        """Test validation of a valid workflow."""
        is_valid, errors, warnings = validation_service.validate_workflow(valid_workflow)

        assert is_valid is True
        assert len(errors) == 0
        # May have warnings, but that's acceptable

    def test_validate_workflow_missing_metadata(self, validation_service):
        """Test validation with missing metadata."""
        workflow = Workflow(metadata=None, nodes=[], connections=[], triggers=[])

        is_valid, errors, warnings = validation_service.validate_workflow(workflow)

        assert is_valid is False
        assert any("metadata is required" in error.lower() for error in errors)

    def test_validate_workflow_missing_name(self, validation_service):
        """Test validation with missing workflow name."""
        metadata = WorkflowMetadata(
            id="test_id",
            name="",  # Empty name
            created_time=int(datetime.utcnow().timestamp() * 1000),
            created_by="test_user",
        )

        workflow = Workflow(metadata=metadata, nodes=[], connections=[], triggers=[])

        is_valid, errors, warnings = validation_service.validate_workflow(workflow)

        assert is_valid is False
        assert any("name is required" in error.lower() for error in errors)

    def test_validate_duplicate_node_ids(self, validation_service, valid_workflow):
        """Test validation with duplicate node IDs."""
        # Add duplicate node ID
        duplicate_node = Node(
            id="trigger_1",  # Same ID as existing node
            type=NodeType.ACTION.value,
            subtype=ActionSubtype.HTTP_REQUEST.value,
            configurations={},
        )
        valid_workflow.nodes.append(duplicate_node)

        is_valid, errors, warnings = validation_service.validate_workflow(valid_workflow)

        assert is_valid is False
        assert any("duplicate node id" in error.lower() for error in errors)

    def test_validate_invalid_node_type(self, validation_service, valid_workflow):
        """Test validation with invalid node type."""
        invalid_node = Node(
            id="invalid_node", type="INVALID_TYPE", subtype="WEBHOOK", configurations={}
        )
        valid_workflow.nodes.append(invalid_node)

        is_valid, errors, warnings = validation_service.validate_workflow(valid_workflow)

        assert is_valid is False
        assert any("invalid node type" in error.lower() for error in errors)

    def test_validate_external_action_missing_action_type(self, validation_service, valid_workflow):
        """Test validation of external action without action_type."""
        external_node = Node(
            id="external_node",
            type=NodeType.EXTERNAL_ACTION.value,
            subtype=ExternalActionSubtype.SLACK.value,
            configurations={},  # Missing action_type
        )
        valid_workflow.nodes.append(external_node)

        is_valid, errors, warnings = validation_service.validate_workflow(valid_workflow)

        assert is_valid is False
        assert any("requires 'action_type' configuration" in error for error in errors)

    def test_validate_disconnected_nodes(self, validation_service, valid_workflow):
        """Test validation with disconnected nodes."""
        # Add a node that's not connected to anything
        disconnected_node = Node(
            id="disconnected_node",
            type=NodeType.ACTION.value,
            subtype=ActionSubtype.HTTP_REQUEST.value,
            configurations={},
        )
        valid_workflow.nodes.append(disconnected_node)

        is_valid, errors, warnings = validation_service.validate_workflow(valid_workflow)

        assert is_valid is True  # Should still be valid
        assert any("disconnected from the workflow" in warning for warning in warnings)

    def test_validate_connection_to_nonexistent_node(self, validation_service, valid_workflow):
        """Test validation with connection to non-existent node."""
        invalid_connection = Connection(
            id="invalid_conn",
            from_node="trigger_1",
            to_node="nonexistent_node",
            output_key="result",
        )
        valid_workflow.connections.append(invalid_connection)

        is_valid, errors, warnings = validation_service.validate_workflow(valid_workflow)

        assert is_valid is False
        assert any("non-existent to_node" in error for error in errors)

    def test_validate_ai_agent_configuration(self, validation_service, valid_workflow):
        """Test validation of AI agent node configuration."""
        ai_node = Node(
            id="ai_node",
            type=NodeType.AI_AGENT.value,
            subtype=AIAgentSubtype.OPENAI_CHATGPT.value,
            configurations={"model": "gpt-3.5-turbo"},
        )
        valid_workflow.nodes.append(ai_node)

        is_valid, errors, warnings = validation_service.validate_workflow(valid_workflow)

        assert is_valid is True
        # Should pass validation with proper model

    def test_validate_flow_if_missing_condition(self, validation_service, valid_workflow):
        """Test validation of IF flow node missing condition."""
        if_node = Node(
            id="if_node",
            type=NodeType.FLOW.value,
            subtype=FlowSubtype.IF.value,
            configurations={},  # Missing condition
        )
        valid_workflow.nodes.append(if_node)

        is_valid, errors, warnings = validation_service.validate_workflow(valid_workflow)

        assert is_valid is False
        assert any("requires 'condition' configuration" in error for error in errors)

    def test_validate_standalone_node(self, validation_service):
        """Test validation of a single node."""
        node = Node(
            id="test_node",
            type=NodeType.ACTION.value,
            subtype=ActionSubtype.HTTP_REQUEST.value,
            configurations={"url": "https://example.com", "method": "GET"},
        )

        is_valid, errors, warnings = validation_service.validate_node_standalone(node)

        assert is_valid is True
        assert len(errors) == 0


class TestUnifiedLogServiceV2:
    """Test unified log service."""

    @pytest.fixture
    def log_service(self):
        return UnifiedLogServiceV2()

    @pytest.fixture
    def mock_supabase(self):
        """Mock Supabase client."""
        client = MagicMock()
        table_mock = MagicMock()
        client.table.return_value = table_mock
        table_mock.insert.return_value.execute.return_value.data = [{"id": "log_entry_1"}]
        table_mock.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = (
            []
        )
        return client

    @pytest.mark.asyncio
    async def test_log_execution_event(self, log_service):
        """Test logging an execution event."""
        result = await log_service.log_execution_event(
            execution_id="exec_123",
            event_type="workflow_start",
            event_data={"trigger": "webhook"},
            node_id="node_1",
            workflow_id="workflow_456",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_log_workflow_start(self, log_service):
        """Test logging workflow start."""
        result = await log_service.log_workflow_start(
            execution_id="exec_123",
            workflow_id="workflow_456",
            user_id="user_789",
            trigger_data={"source": "api"},
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_log_workflow_complete(self, log_service):
        """Test logging workflow completion."""
        result = await log_service.log_workflow_complete(
            execution_id="exec_123",
            workflow_id="workflow_456",
            status=ExecutionStatus.SUCCESS,
            execution_time_ms=5000.0,
            node_count=3,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_log_node_execution(self, log_service):
        """Test logging node execution."""
        result = await log_service.log_node_execution(
            execution_id="exec_123",
            node_id="node_1",
            node_type="ACTION",
            status=ExecutionStatus.SUCCESS,
            execution_time_ms=1500.0,
            input_data={"param": "value"},
            output_data={"result": "success"},
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_get_execution_logs(self, log_service):
        """Test retrieving execution logs."""
        with patch.object(log_service, "supabase", new=MagicMock()) as mock_supabase:
            mock_table = MagicMock()
            mock_supabase.table.return_value = mock_table
            mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
                {
                    "execution_id": "exec_123",
                    "event_type": "workflow_start",
                    "timestamp": datetime.utcnow().isoformat(),
                    "event_data": {"trigger": "webhook"},
                }
            ]

            logs = await log_service.get_execution_logs("exec_123")
            assert len(logs) >= 1
            assert logs[0]["execution_id"] == "exec_123"

    @pytest.mark.asyncio
    async def test_get_execution_summary(self, log_service):
        """Test getting execution summary."""
        with patch.object(log_service, "get_execution_logs") as mock_get_logs:
            mock_get_logs.return_value = [
                {
                    "event_type": "workflow_start",
                    "timestamp": "2024-01-01T10:00:00Z",
                    "event_data": {},
                },
                {
                    "event_type": "node_execution",
                    "timestamp": "2024-01-01T10:00:30Z",
                    "level": "INFO",
                },
                {
                    "event_type": "workflow_complete",
                    "timestamp": "2024-01-01T10:01:00Z",
                    "event_data": {"status": "success", "execution_time_ms": 60000},
                },
            ]

            summary = await log_service.get_execution_summary("exec_123")

            assert summary["execution_id"] == "exec_123"
            assert summary["total_logs"] == 3
            assert summary["node_executions"] == 1
            assert summary["status"] == "success"
            assert summary["execution_time_ms"] == 60000

    def test_truncate_data(self, log_service):
        """Test data truncation for large logs."""
        # Test string truncation
        large_string = "x" * 2000
        truncated = log_service._truncate_data(large_string, max_size=100)
        assert len(str(truncated)) <= 100

        # Test dict truncation
        large_dict = {f"key_{i}": f"value_{i}" * 100 for i in range(50)}
        truncated = log_service._truncate_data(large_dict, max_size=500)
        # Should be truncated to fit within size limit

        # Test list truncation
        large_list = list(range(100))
        truncated = log_service._truncate_data(large_list, max_size=50)
        assert len(truncated) == 10  # Should take first 10 items


class TestWorkflowStatusManagerV2:
    """Test workflow status manager."""

    @pytest.fixture
    def status_manager(self):
        return WorkflowStatusManagerV2()

    @pytest.mark.asyncio
    async def test_update_execution_status(self, status_manager):
        """Test updating execution status."""
        result = await status_manager.update_execution_status(
            execution_id="exec_123",
            status=ExecutionStatus.RUNNING,
            workflow_id="workflow_456",
            node_id="node_1",
            progress_data={"step": 1, "total_steps": 3},
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_get_execution_status(self, status_manager):
        """Test getting execution status."""
        # First update status
        await status_manager.update_execution_status(
            execution_id="exec_get_test", status=ExecutionStatus.SUCCESS, workflow_id="workflow_456"
        )

        # Then retrieve it
        status_info = await status_manager.get_execution_status("exec_get_test")

        assert status_info is not None
        assert status_info["execution_id"] == "exec_get_test"
        assert status_info["status"] == ExecutionStatus.SUCCESS.value
        assert status_info["workflow_id"] == "workflow_456"

    @pytest.mark.asyncio
    async def test_list_executions_by_status(self, status_manager):
        """Test listing executions by status."""
        # Create some test executions
        for i in range(3):
            await status_manager.update_execution_status(
                execution_id=f"exec_list_{i}",
                status=ExecutionStatus.RUNNING,
                workflow_id="workflow_list",
            )

        executions = await status_manager.list_executions_by_status(
            status=ExecutionStatus.RUNNING, workflow_id="workflow_list"
        )

        assert len(executions) >= 3
        for execution in executions:
            assert execution["status"] == ExecutionStatus.RUNNING.value

    @pytest.mark.asyncio
    async def test_get_workflow_execution_summary(self, status_manager):
        """Test getting workflow execution summary."""
        workflow_id = "summary_workflow"

        # Create test executions
        statuses = [ExecutionStatus.SUCCESS, ExecutionStatus.ERROR, ExecutionStatus.RUNNING]
        for i, status in enumerate(statuses):
            await status_manager.update_execution_status(
                execution_id=f"summary_exec_{i}", status=status, workflow_id=workflow_id
            )

        summary = await status_manager.get_workflow_execution_summary(workflow_id)

        assert summary["workflow_id"] == workflow_id
        assert summary["total_executions"] >= 3
        assert ExecutionStatus.SUCCESS.value in summary["status_counts"]

    @pytest.mark.asyncio
    async def test_mark_execution_timeout(self, status_manager):
        """Test marking execution as timed out."""
        result = await status_manager.mark_execution_timeout(
            execution_id="timeout_exec", timeout_reason="Maximum execution time exceeded"
        )

        assert result is True

        # Verify status was updated
        status_info = await status_manager.get_execution_status("timeout_exec")
        assert status_info["status"] == ExecutionStatus.TIMEOUT.value

    @pytest.mark.asyncio
    async def test_mark_execution_cancelled(self, status_manager):
        """Test marking execution as cancelled."""
        result = await status_manager.mark_execution_cancelled(
            execution_id="cancelled_exec", cancelled_by="user_123"
        )

        assert result is True

        # Verify status was updated
        status_info = await status_manager.get_execution_status("cancelled_exec")
        assert status_info["status"] == ExecutionStatus.CANCELLED.value
        assert status_info["progress_data"]["cancelled_by"] == "user_123"

    @pytest.mark.asyncio
    async def test_get_active_executions(self, status_manager):
        """Test getting active executions."""
        # Create some active executions
        active_statuses = [
            ExecutionStatus.RUNNING,
            ExecutionStatus.WAITING,
            ExecutionStatus.WAITING_FOR_HUMAN,
        ]

        for i, status in enumerate(active_statuses):
            await status_manager.update_execution_status(
                execution_id=f"active_exec_{i}", status=status, workflow_id="active_workflow"
            )

        active_executions = await status_manager.get_active_executions()

        # Should include all the active executions we created
        active_exec_ids = [exec_info["execution_id"] for exec_info in active_executions]
        for i in range(len(active_statuses)):
            assert f"active_exec_{i}" in active_exec_ids

    @pytest.mark.asyncio
    async def test_get_status_statistics(self, status_manager):
        """Test getting status statistics."""
        # Create test executions with different statuses
        test_executions = [
            ("stat_exec_1", ExecutionStatus.SUCCESS),
            ("stat_exec_2", ExecutionStatus.ERROR),
            ("stat_exec_3", ExecutionStatus.SUCCESS),
            ("stat_exec_4", ExecutionStatus.RUNNING),
        ]

        for exec_id, status in test_executions:
            await status_manager.update_execution_status(exec_id, status)

        stats = await status_manager.get_status_statistics()

        assert "total_executions" in stats
        assert "status_counts" in stats
        assert stats["total_executions"] >= 4
        assert ExecutionStatus.SUCCESS.value in stats["status_counts"]
