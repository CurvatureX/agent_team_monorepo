"""
Pytest configuration and shared fixtures for workflow_engine_v2 tests.
"""
import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models.node_enums import ActionSubtype, NodeType, TriggerSubtype


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client for testing."""
    client = MagicMock()

    # Mock table operations
    table_mock = MagicMock()
    client.table.return_value = table_mock

    # Mock common operations
    table_mock.select.return_value = table_mock
    table_mock.insert.return_value = table_mock
    table_mock.upsert.return_value = table_mock
    table_mock.update.return_value = table_mock
    table_mock.delete.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.gte.return_value = table_mock
    table_mock.lte.return_value = table_mock
    table_mock.lt.return_value = table_mock
    table_mock.gt.return_value = table_mock
    table_mock.order.return_value = table_mock
    table_mock.limit.return_value = table_mock
    table_mock.range.return_value = table_mock
    table_mock.execute.return_value.data = []

    return client


@pytest.fixture
def mock_oauth_service():
    """Mock OAuth service for testing."""
    service = MagicMock()

    # Mock async methods
    service.get_valid_token = AsyncMock(return_value="mock_token")
    service.store_user_credentials = AsyncMock(return_value=True)
    service.exchange_code_for_token = AsyncMock()
    service.refresh_token = AsyncMock()

    return service


@pytest.fixture
def mock_event_bus():
    """Mock event bus for testing."""
    bus = MagicMock()
    bus.publish = MagicMock()
    bus.subscribe = MagicMock()
    return bus


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "test_secret_key")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "test_anon_key")
    monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test_anthropic_key")
    monkeypatch.setenv("ENCRYPTION_KEY", "test_encryption_key_32_chars_long")


@pytest.fixture
def sample_execution_context():
    """Create a sample execution context for testing."""
    from shared.models.workflow_new import Node

    context = MagicMock()
    context.execution_id = "test_exec_123"
    context.workflow_id = "test_workflow_456"
    context.node = Node(
        id="test_node",
        type="ACTION",
        subtype="HTTP_REQUEST",
        configurations={"url": "https://api.example.com", "method": "GET"},
    )
    context.input_data = {"main": {"test": "data"}}
    context.user_id = "test_user_789"

    return context


@pytest.fixture
def sample_node_execution_result():
    """Create a sample node execution result."""
    from shared.models import ExecutionStatus, NodeExecutionResult

    return NodeExecutionResult(
        status=ExecutionStatus.SUCCESS,
        output_data={"main": {"result": "success"}},
        execution_time_ms=1000.0,
        metadata={"node_type": "ACTION"},
    )


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "asyncio: mark test to run with asyncio")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "slow: mark test as slow running")


# Async test configuration
@pytest.fixture(scope="function")
def async_session():
    """Create async session for database tests."""
    # This would be used for actual database integration tests
    # For now, we'll use mocks
    pass


# Test data factories
@pytest.fixture
def workflow_factory():
    """Factory for creating test workflows."""
    from datetime import datetime

    from shared.models.workflow_new import Connection, Node, Workflow, WorkflowMetadata

    def _create_workflow(workflow_id="test_workflow", node_count=2):
        metadata = WorkflowMetadata(
            id=workflow_id,
            name=f"Test Workflow {workflow_id}",
            created_time=int(datetime.utcnow().timestamp() * 1000),
            created_by="test_user",
        )

        nodes = []
        connections = []

        # Create trigger node
        trigger_node = Node(
            id=f"{workflow_id}_trigger",
            type=NodeType.TRIGGER.value,
            subtype=TriggerSubtype.WEBHOOK.value,
            configurations={"port": 8080},
        )
        nodes.append(trigger_node)

        # Create additional nodes and connections
        prev_node_id = trigger_node.id
        for i in range(1, node_count):
            node = Node(
                id=f"{workflow_id}_node_{i}",
                type=NodeType.ACTION.value,
                subtype=ActionSubtype.HTTP_REQUEST.value,
                configurations={"url": f"https://api{i}.example.com", "method": "GET"},
            )
            nodes.append(node)

            connection = Connection(
                id=f"{workflow_id}_conn_{i}",
                from_node=prev_node_id,
                to_node=node.id,
                output_key="result",
            )
            connections.append(connection)
            prev_node_id = node.id

        return Workflow(
            metadata=metadata, nodes=nodes, connections=connections, triggers=[trigger_node.id]
        )

    return _create_workflow


@pytest.fixture
def execution_factory():
    """Factory for creating test executions."""
    from datetime import datetime

    from shared.models import Execution, ExecutionStatus

    def _create_execution(
        execution_id="test_exec", workflow_id="test_workflow", status=ExecutionStatus.SUCCESS
    ):
        return Execution(
            execution_id=execution_id,
            workflow_id=workflow_id,
            status=status,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            execution_sequence=["node1", "node2"],
            node_executions={},
            final_output={"result": "test"},
            error_message=None,
        )

    return _create_execution


# Error simulation fixtures
@pytest.fixture
def simulate_supabase_error():
    """Simulate Supabase connection errors."""

    def _error():
        raise Exception("Simulated Supabase connection error")

    return _error


@pytest.fixture
def simulate_api_error():
    """Simulate external API errors."""

    def _error(status_code=500, message="Internal Server Error"):
        error = MagicMock()
        error.status = status_code
        error.text.return_value = message
        return error

    return _error


# Performance testing fixtures
@pytest.fixture
def performance_timer():
    """Timer for performance testing."""
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.time()

        def stop(self):
            self.end_time = time.time()

        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None

    return Timer()


# Cleanup fixtures
@pytest.fixture(scope="function", autouse=True)
def cleanup_test_data():
    """Clean up test data after each test."""
    yield
    # This would clean up any test data created during the test
    # For now, since we're using mocks, no cleanup is needed
    pass
