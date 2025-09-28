"""
Test persistent memory implementations for workflow_engine_v2.
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

from workflow_engine_v2.runners.memory_implementations import (
    PersistentConversationBufferMemory,
    PersistentVectorDatabaseMemory,
    PersistentWorkingMemory,
)


@pytest.fixture
def sample_config():
    """Create sample configuration for memory instances."""
    return {
        "user_id": "test_user_123",
        "memory_node_id": "memory_node_456",
        "max_messages": 10,
        "max_tokens": 1000,
        "default_ttl": 3600,
    }


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client for testing."""
    mock_client = Mock()
    mock_table = Mock()
    mock_client.table.return_value = mock_table

    # Mock successful operations
    mock_result = Mock()
    mock_result.data = [{"id": "test_id", "content": "test content"}]
    mock_result.count = 1

    mock_table.insert.return_value.execute.return_value = mock_result
    mock_table.select.return_value.execute.return_value = mock_result
    mock_table.update.return_value.execute.return_value = mock_result
    mock_table.delete.return_value.execute.return_value = mock_result
    mock_table.upsert.return_value.execute.return_value = mock_result

    # Support method chaining
    mock_table.eq.return_value = mock_table
    mock_table.filter.return_value = mock_table

    return mock_client


class TestPersistentConversationBufferMemory:
    """Test persistent conversation buffer memory."""

    def test_initialization_requires_user_id(self):
        """Test that initialization requires user_id."""
        config = {"memory_node_id": "test_node"}

        with pytest.raises(ValueError, match="user_id is required"):
            PersistentConversationBufferMemory(config)

    @patch.dict(
        os.environ, {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SECRET_KEY": "test_key"}
    )
    @patch("workflow_engine_v2.runners.memory_implementations.persistent_base.create_client")
    def test_initialization_success(self, mock_create_client, sample_config, mock_supabase_client):
        """Test successful initialization."""
        mock_create_client.return_value = mock_supabase_client

        memory = PersistentConversationBufferMemory(sample_config)

        assert memory.user_id == "test_user_123"
        assert memory.memory_node_id == "memory_node_456"
        assert memory.max_messages == 10

    @patch.dict(
        os.environ, {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SECRET_KEY": "test_key"}
    )
    @patch("workflow_engine_v2.runners.memory_implementations.persistent_base.create_client")
    @pytest.mark.asyncio
    async def test_store_message(self, mock_create_client, sample_config, mock_supabase_client):
        """Test storing a message."""
        mock_create_client.return_value = mock_supabase_client

        memory = PersistentConversationBufferMemory(sample_config)
        await memory.initialize()

        # Mock the _get_next_message_order method
        with patch.object(memory, "_get_next_message_order", return_value=1):
            result = await memory.store(
                {"message": "Hello, world!", "role": "user", "metadata": {"source": "test"}}
            )

        assert result["success"] is True
        assert result["message_order"] == 1
        assert "storage" in result
        assert result["storage"] == "persistent_database"

    @patch.dict(
        os.environ, {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SECRET_KEY": "test_key"}
    )
    @patch("workflow_engine_v2.runners.memory_implementations.persistent_base.create_client")
    @pytest.mark.asyncio
    async def test_retrieve_messages(self, mock_create_client, sample_config, mock_supabase_client):
        """Test retrieving messages."""
        mock_create_client.return_value = mock_supabase_client

        # Mock database response
        mock_result = Mock()
        mock_result.data = [
            {
                "message_order": 1,
                "role": "user",
                "content": "Hello",
                "metadata": {"token_count": 1},
                "created_at": "2025-01-01T10:00:00Z",
            }
        ]
        mock_supabase_client.table.return_value.select.return_value.execute.return_value = (
            mock_result
        )

        memory = PersistentConversationBufferMemory(sample_config)
        await memory.initialize()

        # Mock _get_total_message_count
        with patch.object(memory, "_get_total_message_count", return_value=1):
            result = await memory.retrieve({"limit": 5})

        assert result["success"] is True
        assert len(result["messages"]) == 1
        assert result["messages"][0]["role"] == "user"
        assert result["messages"][0]["message"] == "Hello"
        assert result["storage"] == "persistent_database"


class TestPersistentVectorDatabaseMemory:
    """Test persistent vector database memory."""

    @patch.dict(
        os.environ,
        {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SECRET_KEY": "test_key",
            "OPENAI_API_KEY": "test_openai_key",
        },
    )
    @patch("workflow_engine_v2.runners.memory_implementations.persistent_base.create_client")
    def test_initialization_success(self, mock_create_client, sample_config, mock_supabase_client):
        """Test successful initialization."""
        mock_create_client.return_value = mock_supabase_client

        memory = PersistentVectorDatabaseMemory(sample_config)

        assert memory.user_id == "test_user_123"
        assert memory.memory_node_id == "memory_node_456"
        assert memory.embedding_model == "text-embedding-ada-002"
        assert memory.similarity_threshold == 0.3

    @patch.dict(
        os.environ,
        {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SECRET_KEY": "test_key",
            "OPENAI_API_KEY": "test_openai_key",
        },
    )
    @patch("workflow_engine_v2.runners.memory_implementations.persistent_base.create_client")
    @pytest.mark.asyncio
    async def test_store_with_embedding(
        self, mock_create_client, sample_config, mock_supabase_client
    ):
        """Test storing text with pre-computed embedding."""
        mock_create_client.return_value = mock_supabase_client

        memory = PersistentVectorDatabaseMemory(sample_config)
        await memory.initialize()

        # Test with pre-computed embedding
        test_embedding = [0.1, 0.2, 0.3]
        result = await memory.store(
            {
                "content": "This is test content",
                "embedding": test_embedding,
                "document_type": "text",
            }
        )

        assert result["success"] is True
        assert result["embedding_dimensions"] == 3
        assert result["document_type"] == "text"
        assert result["storage"] == "persistent_database"


class TestPersistentWorkingMemory:
    """Test persistent working memory."""

    @patch.dict(
        os.environ, {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SECRET_KEY": "test_key"}
    )
    @patch("workflow_engine_v2.runners.memory_implementations.persistent_base.create_client")
    def test_initialization_success(self, mock_create_client, sample_config, mock_supabase_client):
        """Test successful initialization."""
        mock_create_client.return_value = mock_supabase_client

        memory = PersistentWorkingMemory(sample_config)

        assert memory.user_id == "test_user_123"
        assert memory.memory_node_id == "memory_node_456"
        assert memory.default_ttl == 3600

    @patch.dict(
        os.environ, {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SECRET_KEY": "test_key"}
    )
    @patch("workflow_engine_v2.runners.memory_implementations.persistent_base.create_client")
    @pytest.mark.asyncio
    async def test_store_key_value(self, mock_create_client, sample_config, mock_supabase_client):
        """Test storing key-value data."""
        mock_create_client.return_value = mock_supabase_client

        memory = PersistentWorkingMemory(sample_config)
        await memory.initialize()

        result = await memory.store(
            {"key": "test_key", "value": {"data": "test_value"}, "ttl_seconds": 1800}
        )

        assert result["success"] is True
        assert result["key"] == "test_key"
        assert result["ttl_seconds"] == 1800
        assert result["storage"] == "persistent_database"

    @patch.dict(
        os.environ, {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SECRET_KEY": "test_key"}
    )
    @patch("workflow_engine_v2.runners.memory_implementations.persistent_base.create_client")
    @pytest.mark.asyncio
    async def test_retrieve_key_value(
        self, mock_create_client, sample_config, mock_supabase_client
    ):
        """Test retrieving key-value data."""
        mock_create_client.return_value = mock_supabase_client

        # Mock database response
        mock_result = Mock()
        mock_result.data = [
            {
                "key": "test_key",
                "value": {"data": "test_value"},
                "expires_at": None,
                "metadata": {},
                "created_at": "2025-01-01T10:00:00Z",
            }
        ]
        mock_supabase_client.table.return_value.select.return_value.execute.return_value = (
            mock_result
        )

        memory = PersistentWorkingMemory(sample_config)
        await memory.initialize()

        result = await memory.retrieve({"key": "test_key"})

        assert result["success"] is True
        assert result["key"] == "test_key"
        assert result["value"] == {"data": "test_value"}
        assert result["storage"] == "persistent_database"


class TestPersistentMemoryIntegration:
    """Test integration between memory types."""

    @patch.dict(
        os.environ, {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SECRET_KEY": "test_key"}
    )
    @patch("workflow_engine_v2.runners.memory_implementations.persistent_base.create_client")
    @pytest.mark.asyncio
    async def test_health_checks(self, mock_create_client, sample_config, mock_supabase_client):
        """Test health checks for all persistent memory types."""
        mock_create_client.return_value = mock_supabase_client

        # Test conversation buffer health check
        conv_memory = PersistentConversationBufferMemory(sample_config)
        conv_health = await conv_memory.health_check()
        assert conv_health["status"] == "healthy"
        assert conv_health["storage_type"] == "persistent_supabase"

        # Test vector database health check
        vec_memory = PersistentVectorDatabaseMemory(sample_config)
        vec_health = await vec_memory.health_check()
        assert vec_health["status"] == "healthy"
        assert vec_health["storage_type"] == "persistent_supabase"

        # Test working memory health check
        work_memory = PersistentWorkingMemory(sample_config)
        work_health = await work_memory.health_check()
        assert work_health["status"] == "healthy"
        assert work_health["storage_type"] == "persistent_supabase"

    def test_missing_environment_variables(self):
        """Test behavior when required environment variables are missing."""
        sample_config = {"user_id": "test_user", "memory_node_id": "test_node"}

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(
                ValueError,
                match="SUPABASE_URL and SUPABASE_SECRET_KEY environment variables are required",
            ):
                PersistentConversationBufferMemory(sample_config)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
