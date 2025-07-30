"""
Pytest configuration and shared fixtures for API Gateway tests.
"""

import os
import sys
from unittest.mock import Mock, patch

import pytest

# Add shared path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
shared_path = os.path.join(current_dir, "../../../../shared")
if shared_path not in sys.path:
    sys.path.insert(0, shared_path)


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment before running tests"""
    # Set test environment variables
    os.environ["DEBUG"] = "true"
    os.environ["LOG_LEVEL"] = "ERROR"  # Reduce log noise during tests
    os.environ["TESTING"] = "true"
    os.environ["MCP_API_KEY_REQUIRED"] = "true"  # Enable MCP auth testing

    # Ensure shared path is available
    if shared_path not in sys.path:
        sys.path.insert(0, shared_path)


@pytest.fixture
def mock_node_registry():
    """Create a comprehensive mock node registry for testing"""
    registry = Mock()

    # Mock node types
    registry.get_node_types.return_value = {
        "ACTION_NODE": ["HTTP_REQUEST", "RUN_CODE", "DATABASE_OPERATION"],
        "AI_AGENT_NODE": ["OPENAI_NODE", "CLAUDE_NODE", "GEMINI_NODE"],
        "FLOW_NODE": ["IF", "LOOP", "MERGE"],
        "TRIGGER_NODE": ["TRIGGER_MANUAL", "TRIGGER_CRON", "TRIGGER_WEBHOOK"],
        "TOOL_NODE": ["HTTP", "EMAIL", "CALENDAR"],
        "MEMORY_NODE": ["MEMORY_SIMPLE", "MEMORY_VECTOR_STORE"],
        "HUMAN_LOOP_NODE": ["HUMAN_APP", "HUMAN_SLACK"],
    }

    # Mock node spec
    def create_mock_spec(node_type, subtype):
        spec = Mock()
        spec.node_type = node_type
        spec.subtype = subtype
        spec.version = "1.0.0"
        spec.description = f"{node_type} {subtype} description"

        # Mock parameters
        spec.parameters = [
            Mock(
                name="test_param",
                type=Mock(value="string"),
                required=True,
                default_value=None,
                description="Test parameter",
                enum_values=None,
                validation_pattern=None,
            )
        ]

        # Mock ports
        spec.input_ports = [
            Mock(
                name="main",
                type="MAIN",
                required=True,
                description="Main input",
                max_connections=1,
                data_format=Mock(
                    mime_type="application/json",
                    schema='{"type": "object"}',
                    examples=['{"test": "data"}'],
                ),
                validation_schema='{"type": "object"}',
            )
        ]

        spec.output_ports = [
            Mock(
                name="main",
                type="MAIN",
                description="Main output",
                max_connections=-1,
                data_format=Mock(
                    mime_type="application/json",
                    schema='{"type": "object"}',
                    examples=['{"result": "data"}'],
                ),
                validation_schema='{"type": "object"}',
            )
        ]

        # Mock examples
        spec.examples = [{"name": "test_example", "description": "Test example usage"}]

        return spec

    registry.get_spec.side_effect = lambda node_type, subtype: create_mock_spec(node_type, subtype)

    # Mock list_all_specs
    all_specs = []
    for node_type, subtypes in registry.get_node_types.return_value.items():
        for subtype in subtypes:
            all_specs.append(create_mock_spec(node_type, subtype))

    registry.list_all_specs.return_value = all_specs

    return registry


@pytest.fixture
def mock_auth_headers():
    """Mock authentication headers for testing"""
    return {"X-API-Key": "dev_default"}


@pytest.fixture
def mock_mcp_client():
    """Mock MCP client for authentication testing"""
    client = Mock()
    client.client_name = "test_client"
    client.scopes = ["tools:read", "tools:execute", "health:check"]
    client.api_key = "dev_default"
    return client


@pytest.fixture
def mock_mcp_deps(mock_mcp_client):
    """Mock MCP dependencies"""
    deps = Mock()
    deps.mcp_client = mock_mcp_client
    deps.request_context = {"request_id": "test-request-123", "start_time": 1234567890.123}
    return deps


@pytest.fixture(autouse=True)
def suppress_registry_warnings():
    """Suppress node registry import warnings during tests"""
    import builtins

    original_print = builtins.print

    def selective_print(*args, **kwargs):
        message = " ".join(str(arg) for arg in args)
        if not any(
            warning in message
            for warning in [
                "Warning: Could not import",
                "Warning: Node registry not available",
                "Error getting node types:",
                "Error searching nodes:",
                "⚠️",
                "Warning: definitions package not found",
            ]
        ):
            # Call original print for non-warning messages
            original_print(*args, **kwargs)

    with patch("builtins.print", side_effect=selective_print):
        yield


@pytest.fixture
def sample_node_requests():
    """Sample node requests for testing"""
    return [
        {"node_type": "ACTION_NODE", "subtype": "HTTP_REQUEST"},
        {"node_type": "AI_AGENT_NODE", "subtype": "OPENAI_NODE"},
        {"node_type": "FLOW_NODE", "subtype": "IF"},
    ]


@pytest.fixture
def sample_search_queries():
    """Sample search queries for testing"""
    return ["HTTP request", "send email", "database operation", "AI agent", "conditional logic"]
