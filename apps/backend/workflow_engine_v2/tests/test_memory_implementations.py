"""
Test memory implementations for workflow_engine_v2.
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

from workflow_engine_v2.runners.memory_implementations.conversation_buffer import (
    ConversationBufferMemory,
)
from workflow_engine_v2.runners.memory_implementations.entity_memory import EntityMemory
from workflow_engine_v2.runners.memory_implementations.key_value_store import KeyValueStoreMemory
from workflow_engine_v2.runners.memory_implementations.orchestrator import MemoryOrchestrator
from workflow_engine_v2.runners.memory_implementations.vector_database import VectorDatabaseMemory


class TestKeyValueStoreMemory:
    """Test key-value store memory implementation."""

    @pytest.fixture
    def kv_memory(self):
        return KeyValueStoreMemory(namespace="test_namespace")

    @pytest.mark.asyncio
    async def test_store_and_retrieve(self, kv_memory):
        """Test storing and retrieving data."""
        data = {"key": "test_key", "value": "test_value", "metadata": {"source": "test"}}

        # Store data
        result = await kv_memory.store(data)
        assert result["status"] == "success"
        assert result["key"] == "test_key"

        # Retrieve data
        retrieved = await kv_memory.retrieve({"key": "test_key"})
        assert retrieved["status"] == "success"
        assert retrieved["data"]["value"] == "test_value"
        assert retrieved["data"]["metadata"]["source"] == "test"

    @pytest.mark.asyncio
    async def test_update_existing_key(self, kv_memory):
        """Test updating an existing key."""
        # Store initial data
        await kv_memory.store({"key": "update_key", "value": "initial_value"})

        # Update data
        result = await kv_memory.store({"key": "update_key", "value": "updated_value"})
        assert result["status"] == "success"

        # Verify update
        retrieved = await kv_memory.retrieve({"key": "update_key"})
        assert retrieved["data"]["value"] == "updated_value"

    @pytest.mark.asyncio
    async def test_delete_key(self, kv_memory):
        """Test deleting a key."""
        # Store data first
        await kv_memory.store({"key": "delete_key", "value": "to_be_deleted"})

        # Delete data
        result = await kv_memory.delete({"key": "delete_key"})
        assert result["status"] == "success"

        # Verify deletion
        retrieved = await kv_memory.retrieve({"key": "delete_key"})
        assert retrieved["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_list_keys(self, kv_memory):
        """Test listing all keys."""
        # Store multiple keys
        await kv_memory.store({"key": "key1", "value": "value1"})
        await kv_memory.store({"key": "key2", "value": "value2"})
        await kv_memory.store({"key": "key3", "value": "value3"})

        # List keys
        result = await kv_memory.list({})
        assert result["status"] == "success"
        assert len(result["keys"]) >= 3
        assert "key1" in result["keys"]
        assert "key2" in result["keys"]
        assert "key3" in result["keys"]


class TestConversationBufferMemory:
    """Test conversation buffer memory implementation."""

    @pytest.fixture
    def buffer_memory(self):
        return ConversationBufferMemory(buffer_size=3)

    @pytest.mark.asyncio
    async def test_store_conversation(self, buffer_memory):
        """Test storing conversation messages."""
        data = {
            "conversation_id": "conv_123",
            "message": {"role": "user", "content": "Hello"},
            "metadata": {"timestamp": datetime.utcnow().isoformat()},
        }

        result = await buffer_memory.store(data)
        assert result["status"] == "success"
        assert result["message_count"] == 1

    @pytest.mark.asyncio
    async def test_retrieve_conversation(self, buffer_memory):
        """Test retrieving conversation history."""
        # Store multiple messages
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ]

        for msg in messages:
            await buffer_memory.store(
                {
                    "conversation_id": "conv_123",
                    "message": msg,
                    "metadata": {"timestamp": datetime.utcnow().isoformat()},
                }
            )

        # Retrieve conversation
        result = await buffer_memory.retrieve({"conversation_id": "conv_123"})
        assert result["status"] == "success"
        assert len(result["messages"]) == 3
        assert result["messages"][0]["content"] == "Hello"

    @pytest.mark.asyncio
    async def test_buffer_overflow(self, buffer_memory):
        """Test buffer size limit enforcement."""
        # Store more messages than buffer size (3)
        for i in range(5):
            await buffer_memory.store(
                {
                    "conversation_id": "conv_overflow",
                    "message": {"role": "user", "content": f"Message {i}"},
                    "metadata": {"timestamp": datetime.utcnow().isoformat()},
                }
            )

        # Should only keep the last 3 messages
        result = await buffer_memory.retrieve({"conversation_id": "conv_overflow"})
        assert len(result["messages"]) == 3
        assert result["messages"][-1]["content"] == "Message 4"


class TestConversationBufferAutoSummary:
    """Test conversation buffer auto-summary feature."""

    @pytest.fixture
    def auto_summary_memory(self):
        # Configure with auto-summary enabled and small thresholds for testing
        return ConversationBufferMemory(
            config={
                "max_messages": 10,
                "auto_summarize": True,
                "summarize_count": 3,
            }
        )

    @pytest.mark.asyncio
    async def test_auto_summary_triggered(self, auto_summary_memory):
        """Test auto-summary is triggered when buffer is nearly full."""
        await auto_summary_memory.initialize()

        # Store messages up to nearly full (within 5 of max_messages)
        for i in range(6):
            result = await auto_summary_memory.store(
                {
                    "message": f"Message {i}",
                    "role": "user",
                }
            )
            assert result["success"] is True

        # Summary should be created when we're within 5 messages of the limit
        result = await auto_summary_memory.retrieve({})
        assert result["success"] is True
        assert result["summary"] != ""  # Summary should be generated

    @pytest.mark.asyncio
    async def test_summary_in_context(self, auto_summary_memory):
        """Test that summary appears in context retrieval."""
        await auto_summary_memory.initialize()

        # Store enough messages to trigger summary
        for i in range(6):
            await auto_summary_memory.store(
                {
                    "message": f"Message {i}",
                    "role": "user",
                }
            )

        # Get context
        result = await auto_summary_memory.get_context({})
        assert result["success"] is True
        assert result["has_summary"] is True
        assert "[Summary of earlier conversation]" in result["context"]
        assert len(result.get("messages", [])) > 0


class TestEntityMemory:
    """Test entity memory implementation."""

    @pytest.fixture
    def entity_memory(self):
        return EntityMemory()

    @pytest.mark.asyncio
    async def test_store_entity(self, entity_memory):
        """Test storing entity information."""
        data = {
            "entity_type": "person",
            "entity_id": "john_doe",
            "attributes": {"name": "John Doe", "age": 30, "occupation": "Developer"},
            "metadata": {"source": "conversation"},
        }

        result = await entity_memory.store(data)
        assert result["status"] == "success"
        assert result["entity_id"] == "john_doe"

    @pytest.mark.asyncio
    async def test_retrieve_entity(self, entity_memory):
        """Test retrieving entity information."""
        # Store entity first
        await entity_memory.store(
            {
                "entity_type": "person",
                "entity_id": "jane_smith",
                "attributes": {"name": "Jane Smith", "role": "Manager"},
                "metadata": {"source": "profile"},
            }
        )

        # Retrieve entity
        result = await entity_memory.retrieve({"entity_type": "person", "entity_id": "jane_smith"})
        assert result["status"] == "success"
        assert result["entity"]["attributes"]["name"] == "Jane Smith"
        assert result["entity"]["attributes"]["role"] == "Manager"

    @pytest.mark.asyncio
    async def test_list_entities_by_type(self, entity_memory):
        """Test listing entities by type."""
        # Store multiple entities
        entities = [
            {"entity_type": "person", "entity_id": "person1", "attributes": {"name": "Person 1"}},
            {"entity_type": "person", "entity_id": "person2", "attributes": {"name": "Person 2"}},
            {"entity_type": "organization", "entity_id": "org1", "attributes": {"name": "Org 1"}},
        ]

        for entity in entities:
            await entity_memory.store(entity)

        # List persons only
        result = await entity_memory.list({"entity_type": "person"})
        assert result["status"] == "success"
        assert len(result["entities"]) == 2
        assert all(e["entity_type"] == "person" for e in result["entities"])


class TestVectorDatabaseMemory:
    """Test vector database memory implementation."""

    @pytest.fixture
    def vector_memory(self):
        return VectorDatabaseMemory()

    @pytest.mark.asyncio
    async def test_store_with_embedding(self, vector_memory):
        """Test storing data with vector embedding."""
        with patch.object(vector_memory, "_generate_embedding") as mock_embedding:
            mock_embedding.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]

            data = {
                "content": "This is a test document about machine learning",
                "metadata": {"category": "AI", "source": "research"},
            }

            result = await vector_memory.store(data)
            assert result["status"] == "success"
            assert "document_id" in result
            mock_embedding.assert_called_once()

    @pytest.mark.asyncio
    async def test_similarity_search(self, vector_memory):
        """Test similarity search functionality."""
        with patch.object(vector_memory, "_generate_embedding") as mock_embedding, patch.object(
            vector_memory, "_similarity_search"
        ) as mock_search:
            mock_embedding.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]
            mock_search.return_value = [
                {
                    "content": "Similar document 1",
                    "similarity": 0.9,
                    "metadata": {"category": "AI"},
                },
                {
                    "content": "Similar document 2",
                    "similarity": 0.8,
                    "metadata": {"category": "ML"},
                },
            ]

            result = await vector_memory.retrieve(
                {"query": "machine learning concepts", "top_k": 2}
            )

            assert result["status"] == "success"
            assert len(result["similar_documents"]) == 2
            assert result["similar_documents"][0]["similarity"] == 0.9


class TestWorkingMemory:
    """Test working memory implementation."""

    @pytest.fixture
    def working_memory(self):
        return WorkingMemory(capacity=5)

    @pytest.mark.asyncio
    async def test_store_active_context(self, working_memory):
        """Test storing active context."""
        data = {
            "context_id": "ctx_123",
            "variables": {"current_task": "data_processing", "step": 1},
            "metadata": {"priority": "high"},
        }

        result = await working_memory.store(data)
        assert result["status"] == "success"
        assert result["context_id"] == "ctx_123"

    @pytest.mark.asyncio
    async def test_retrieve_active_context(self, working_memory):
        """Test retrieving active context."""
        # Store context first
        await working_memory.store(
            {
                "context_id": "active_ctx",
                "variables": {"task": "analysis", "progress": 50},
                "metadata": {"timestamp": datetime.utcnow().isoformat()},
            }
        )

        result = await working_memory.retrieve({"context_id": "active_ctx"})
        assert result["status"] == "success"
        assert result["context"]["variables"]["task"] == "analysis"
        assert result["context"]["variables"]["progress"] == 50

    @pytest.mark.asyncio
    async def test_capacity_management(self, working_memory):
        """Test working memory capacity management."""
        # Fill beyond capacity
        for i in range(7):  # Capacity is 5
            await working_memory.store(
                {
                    "context_id": f"ctx_{i}",
                    "variables": {"data": f"value_{i}"},
                    "metadata": {"timestamp": datetime.utcnow().isoformat()},
                }
            )

        # Should only keep the most recent contexts
        result = await working_memory.list({})
        assert len(result["contexts"]) <= 5


class TestMemoryOrchestrator:
    """Test memory orchestrator functionality."""

    @pytest.fixture
    def orchestrator(self):
        return MemoryOrchestrator()

    @pytest.mark.asyncio
    async def test_register_memory_type(self, orchestrator):
        """Test registering a memory implementation."""
        kv_memory = KeyValueStoreMemory()
        orchestrator.register_memory("key_value", kv_memory)

        assert "key_value" in orchestrator.memory_implementations
        assert orchestrator.memory_implementations["key_value"] == kv_memory

    @pytest.mark.asyncio
    async def test_store_across_multiple_memories(self, orchestrator):
        """Test storing data across multiple memory types."""
        # Register memory implementations
        orchestrator.register_memory("key_value", KeyValueStoreMemory())
        orchestrator.register_memory("conversation", ConversationBufferMemory())

        data = {
            "key": "test_key",
            "value": "test_value",
            "memory_types": ["key_value", "conversation"],
        }

        result = await orchestrator.store(data)
        assert result["status"] == "success"
        assert len(result["stored_in"]) == 2
        assert "key_value" in result["stored_in"]
        assert "conversation" in result["stored_in"]

    @pytest.mark.asyncio
    async def test_smart_retrieval(self, orchestrator):
        """Test smart retrieval from appropriate memory type."""
        with patch.object(orchestrator, "_determine_best_memory_type") as mock_determine:
            mock_determine.return_value = "key_value"

            # Register and mock memory
            mock_memory = AsyncMock()
            mock_memory.retrieve.return_value = {"status": "success", "data": "retrieved_data"}
            orchestrator.register_memory("key_value", mock_memory)

            query = {"key": "test_key", "context": "lookup"}
            result = await orchestrator.retrieve(query)

            assert result["status"] == "success"
            assert result["data"] == "retrieved_data"
            assert result["memory_type"] == "key_value"
            mock_memory.retrieve.assert_called_once_with(query)

    @pytest.mark.asyncio
    async def test_memory_type_selection(self, orchestrator):
        """Test memory type selection logic."""
        # Test different query types
        assert orchestrator._determine_best_memory_type({"key": "value"}) == "key_value"
        assert (
            orchestrator._determine_best_memory_type({"conversation_id": "123"}) == "conversation"
        )
        assert orchestrator._determine_best_memory_type({"entity_type": "person"}) == "entity"
        assert orchestrator._determine_best_memory_type({"query": "search text"}) == "vector"
        assert orchestrator._determine_best_memory_type({"context_id": "ctx"}) == "working"
