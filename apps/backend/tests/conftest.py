"""
pytest 配置文件
配置测试环境和共享的 fixtures
"""

import pytest
import asyncio
import os
import sys
from unittest.mock import MagicMock, AsyncMock

# Add project paths to Python path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "api-gateway"))
sys.path.insert(0, os.path.join(project_root, "workflow_agent"))


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client for testing"""
    client = MagicMock()
    
    # Mock table operations
    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value.data = [
        {"id": "test_session_123", "user_id": "test_user", "status": "active"}
    ]
    mock_table.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "test_session_123", "user_id": "test_user", "status": "active"}
    ]
    
    client.table.return_value = mock_table
    return client


@pytest.fixture
def mock_grpc_client():
    """Mock gRPC client for testing"""
    client = AsyncMock()
    client.connected = True
    
    # Mock process_conversation_stream
    async def mock_conversation_stream(*args, **kwargs):
        # Simulate conversation flow
        yield {
            "type": "message",
            "session_id": "test_session",
            "message": "I understand you want to create a workflow.",
            "is_final": False
        }
        yield {
            "type": "workflow", 
            "session_id": "test_session",
            "workflow": '{"name": "Test Workflow", "nodes": []}',
            "is_final": True
        }
    
    client.process_conversation_stream = mock_conversation_stream
    return client


@pytest.fixture
def mock_authenticated_user():
    """Mock authenticated user for testing"""
    user = MagicMock()
    user.sub = "test_user_123"
    user.token = "mock_jwt_token"
    user.email = "test@example.com"
    return user


@pytest.fixture
def sample_session_data():
    """Sample session data for testing"""
    return {
        "id": "test_session_123",
        "user_id": "test_user_123", 
        "session_type": "workflow",
        "action": "create",
        "workflow_id": None,
        "metadata": {"source": "test"},
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }


@pytest.fixture  
def sample_chat_request():
    """Sample chat request for testing"""
    return {
        "session_id": "test_session_123",
        "message": "Create a data processing workflow",
        "context": {"origin": "create"}
    }


@pytest.fixture
def sample_workflow():
    """Sample workflow for testing"""
    return {
        "name": "Test Workflow",
        "description": "A test workflow for validation",
        "nodes": [
            {
                "id": "start",
                "type": "trigger",
                "name": "Start Trigger", 
                "config": {"trigger_type": "manual"}
            },
            {
                "id": "process",
                "type": "action", 
                "name": "Process Data",
                "config": {"action": "process"}
            },
            {
                "id": "end",
                "type": "end",
                "name": "End",
                "config": {}
            }
        ],
        "connections": [
            {"from": "start", "to": "process"},
            {"from": "process", "to": "end"}
        ],
        "created_at": 1640995200000
    }


@pytest.fixture
def mock_workflow_agent_servicer():
    """Mock WorkflowAgentServicer for testing"""
    servicer = MagicMock()
    servicer.session_states = {}
    
    # Mock clarification response
    def mock_clarification_response(state, message):
        return f"I understand you want to: {message}. Please provide more details."
    
    servicer._generate_clarification_response = mock_clarification_response
    
    # Mock workflow generation trigger
    def mock_should_move_to_generation(state):
        conversations = state.get("conversations", [])
        user_messages = [c for c in conversations if c.get("role") == "user"]
        return len(user_messages) >= 2
    
    servicer._should_move_to_workflow_generation = mock_should_move_to_generation
    
    return servicer


# Test environment markers
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


# Skip tests if dependencies are not available
def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle missing dependencies"""
    skip_no_grpc = pytest.mark.skip(reason="gRPC dependencies not available")
    skip_no_workflow_agent = pytest.mark.skip(reason="workflow_agent module not available")
    
    for item in items:
        # Skip gRPC tests if proto modules not available
        if "grpc" in item.nodeid.lower():
            try:
                import grpc
            except ImportError:
                item.add_marker(skip_no_grpc)
        
        # Skip workflow_agent tests if module not available
        if "workflow_agent" in item.nodeid.lower():
            try:
                from workflow_agent.services.grpc_server import WorkflowAgentServicer
            except ImportError:
                item.add_marker(skip_no_workflow_agent)