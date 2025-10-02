"""
Integration tests for AI Agent + Memory Node interaction in workflow_engine_v2.
"""

import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models import TriggerInfo
from shared.models.node_enums import AIAgentSubtype, MemorySubtype, NodeType
from shared.models.workflow import Node
from workflow_engine_v2.runners.ai import AIAgentRunner
from workflow_engine_v2.runners.memory import MemoryRunner


@pytest.fixture
def sample_execution_context():
    """Create sample execution context with user_id."""
    ctx = Mock()
    ctx.workflow = Mock()
    ctx.workflow.workflow_id = "workflow_123"
    ctx.workflow.user_id = "test_user_456"
    ctx.execution = Mock()
    ctx.execution.execution_id = "execution_789"
    ctx.execution.user_id = "test_user_456"
    return ctx


@pytest.fixture
def sample_trigger():
    """Create sample trigger info."""
    return TriggerInfo(
        trigger_type="manual",
        trigger_data={"message": "Hello AI!"},
        user_id="test_user_456",
        timestamp=1640995200,
    )


@pytest.fixture
def memory_node():
    """Create a memory node for testing."""
    return Node(
        id="memory_node_1",
        name="Conversation Memory",
        description="Stores conversation history",
        type=NodeType.MEMORY.value,
        subtype=MemorySubtype.CONVERSATION_BUFFER.value,
        configurations={
            "use_advanced": True,
            "use_persistent_storage": True,
            "max_messages": 50,
            "operation": "store",
        },
    )


@pytest.fixture
def ai_agent_node():
    """Create an AI agent node with attached memory."""
    return Node(
        id="ai_agent_1",
        name="Chat AI Agent",
        description="Handles conversation with memory",
        type=NodeType.AI_AGENT.value,
        subtype=AIAgentSubtype.ANTHROPIC_CLAUDE.value,
        configurations={
            "model": "claude-3-5-haiku-20241022",
            "prompt": "You are a helpful assistant with memory.",
            "provider": "anthropic",
        },
        attached_nodes=["memory_node_1"],
    )


class TestAIMemoryIntegration:
    """Test AI Agent and Memory Node integration."""

    @patch.dict(
        os.environ, {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SECRET_KEY": "test_key"}
    )
    @patch("workflow_engine_v2.runners.memory_implementations.persistent_base.create_client")
    def test_memory_runner_context_extraction(
        self, mock_create_client, memory_node, sample_execution_context, sample_trigger
    ):
        """Test that MemoryRunner properly extracts user_id from context."""
        # Mock Supabase client
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        # Create memory runner
        memory_runner = MemoryRunner()

        # Prepare inputs with context
        inputs = {"main": {"message": "Hello!", "role": "user"}, "_ctx": sample_execution_context}

        # Run memory operation
        result = memory_runner.run(memory_node, inputs, sample_trigger)

        # Verify execution context was set
        assert hasattr(memory_runner, "_execution_context")
        assert memory_runner._execution_context["user_id"] == "test_user_456"
        assert memory_runner._execution_context["workflow_id"] == "workflow_123"

    @patch.dict(
        os.environ, {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SECRET_KEY": "test_key"}
    )
    @patch("workflow_engine_v2.runners.memory_implementations.persistent_base.create_client")
    def test_ai_agent_with_attached_memory(
        self,
        mock_create_client,
        ai_agent_node,
        memory_node,
        sample_execution_context,
        sample_trigger,
    ):
        """Test AI Agent runner with attached memory nodes."""
        # Mock Supabase client
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        # Add memory node to workflow context
        sample_execution_context.workflow.nodes = [ai_agent_node, memory_node]

        # Mock AI provider
        with patch("workflow_engine_v2.services.ai_providers.get_ai_provider") as mock_get_provider:
            mock_provider = Mock()
            mock_provider.generate.return_value = {
                "response": "Hello! How can I help you today?",
                "usage": {"input_tokens": 10, "output_tokens": 15},
            }
            mock_get_provider.return_value = mock_provider

            # Create AI agent runner
            ai_runner = AIAgentRunner()

            # Prepare inputs
            inputs = {"main": {"user_input": "Hello AI!"}, "_ctx": sample_execution_context}

            # Run AI agent with attached memory
            result = ai_runner.run(ai_agent_node, inputs, sample_trigger)

            # Verify result structure
            assert "main" in result
            assert "attached" in result["main"]
            assert "memory_node_1" in result["main"]["attached"]

            # Verify AI provider was called
            mock_provider.generate.assert_called_once()

    @patch.dict(
        os.environ, {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SECRET_KEY": "test_key"}
    )
    @patch("workflow_engine_v2.runners.memory_implementations.persistent_base.create_client")
    def test_memory_fallback_without_user_id(self, mock_create_client, memory_node):
        """Test memory fallback to in-memory when user_id is missing."""
        # Mock Supabase client
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        # Create context without user_id
        ctx = Mock()
        ctx.workflow = None
        ctx.execution = None

        trigger = TriggerInfo(
            trigger_type="manual",
            trigger_data={"message": "Hello!"},
            user_id=None,  # No user_id
            timestamp=1640995200,
        )

        inputs = {"main": {"message": "Hello!", "role": "user"}, "_ctx": ctx}

        memory_runner = MemoryRunner()
        result = memory_runner.run(memory_node, inputs, trigger)

        # Should still work (fallback to in-memory)
        assert "main" in result
        # Should have fallen back to in-memory implementation

    def test_memory_types_compatibility(self):
        """Test that all memory subtypes have proper implementations."""
        memory_runner = MemoryRunner()

        # Test memory class mappings
        test_config = {"user_id": "test_user", "memory_node_id": "test_node"}

        # Create a mock node for each memory subtype
        for subtype in [
            MemorySubtype.CONVERSATION_BUFFER,
            MemorySubtype.VECTOR_DATABASE,
            MemorySubtype.WORKING_MEMORY,
            MemorySubtype.KEY_VALUE_STORE,
            MemorySubtype.CONVERSATION_SUMMARY,
        ]:
            node = Node(
                id=f"memory_{subtype.value}",
                name=f"Test {subtype.value}",
                type=NodeType.MEMORY.value,
                subtype=subtype.value,
                configurations=test_config,
            )

            # Set up execution context
            memory_runner._execution_context = {
                "user_id": "test_user",
                "workflow_id": "test_workflow",
                "execution_id": "test_execution",
            }

            # This should not raise an error (memory class should exist)
            memory_instance = memory_runner._get_memory_instance(node, subtype)
            # Note: May be None if environment variables are missing, but shouldn't raise

    @patch.dict(
        os.environ, {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SECRET_KEY": "test_key"}
    )
    @patch("workflow_engine_v2.runners.memory_implementations.persistent_base.create_client")
    def test_memory_operations(self, mock_create_client, memory_node):
        """Test various memory operations work correctly."""
        # Mock Supabase client
        mock_client = Mock()
        mock_table = Mock()
        mock_client.table.return_value = mock_table

        # Mock successful database operations
        mock_result = Mock()
        mock_result.data = [{"id": "test_id", "content": "test content"}]
        mock_result.count = 1

        mock_table.insert.return_value.execute.return_value = mock_result
        mock_table.select.return_value.execute.return_value = mock_result
        mock_table.upsert.return_value.execute.return_value = mock_result

        # Support method chaining
        mock_table.eq.return_value = mock_table
        mock_table.filter.return_value = mock_table

        mock_create_client.return_value = mock_client

        memory_runner = MemoryRunner()

        # Set up execution context
        ctx = Mock()
        ctx.workflow = Mock()
        ctx.workflow.user_id = "test_user_456"
        ctx.execution = Mock()
        ctx.execution.user_id = "test_user_456"

        # Test store operation
        store_node = Node(
            id="memory_store",
            name="Store Memory",
            type=NodeType.MEMORY.value,
            subtype=MemorySubtype.CONVERSATION_BUFFER.value,
            configurations={
                "operation": "store",
                "use_advanced": True,
                "use_persistent_storage": True,
            },
        )

        inputs = {"main": {"message": "Hello!", "role": "user"}, "_ctx": ctx}

        trigger = TriggerInfo(
            trigger_type="manual", trigger_data={}, user_id="test_user_456", timestamp=1640995200
        )

        result = memory_runner.run(store_node, inputs, trigger)
        assert "main" in result

        # Test retrieve operation
        retrieve_node = Node(
            id="memory_retrieve",
            name="Retrieve Memory",
            type=NodeType.MEMORY.value,
            subtype=MemorySubtype.CONVERSATION_BUFFER.value,
            configurations={
                "operation": "retrieve",
                "use_advanced": True,
                "use_persistent_storage": True,
            },
        )

        result = memory_runner.run(retrieve_node, inputs, trigger)
        assert "main" in result


class TestMemoryPersistenceIntegration:
    """Test persistence-specific integration scenarios."""

    @patch.dict(
        os.environ, {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SECRET_KEY": "test_key"}
    )
    @patch("workflow_engine_v2.runners.memory_implementations.persistent_base.create_client")
    def test_persistent_memory_configuration(self, mock_create_client):
        """Test persistent memory configuration and initialization."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        # Test configuration options
        config_tests = [
            {"use_persistent_storage": True, "use_advanced": True, "max_messages": 100},
            {"use_persistent_storage": False, "use_advanced": True, "max_messages": 50},
            {"use_advanced": False},  # Should use legacy mode
        ]

        memory_runner = MemoryRunner()

        for config in config_tests:
            node = Node(
                id="test_memory",
                name="Test Memory",
                type=NodeType.MEMORY.value,
                subtype=MemorySubtype.CONVERSATION_BUFFER.value,
                configurations=config,
            )

            ctx = Mock()
            ctx.workflow = Mock()
            ctx.workflow.user_id = "test_user"

            inputs = {"main": {}, "_ctx": ctx}
            trigger = TriggerInfo(
                trigger_type="manual", trigger_data={}, user_id="test_user", timestamp=1640995200
            )

            # Should not raise an error
            result = memory_runner.run(node, inputs, trigger)
            assert "main" in result or "error" in result

    def test_error_handling_scenarios(self):
        """Test various error scenarios in memory integration."""
        memory_runner = MemoryRunner()

        # Test with invalid memory subtype
        invalid_node = Node(
            id="invalid_memory",
            name="Invalid Memory",
            type=NodeType.MEMORY.value,
            subtype="INVALID_TYPE",
            configurations={"use_advanced": True},
        )

        inputs = {"main": {}}
        trigger = TriggerInfo(
            trigger_type="manual", trigger_data={}, user_id="test_user", timestamp=1640995200
        )

        # Should handle gracefully
        result = memory_runner.run(invalid_node, inputs, trigger)
        assert isinstance(result, dict)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
