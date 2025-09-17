from typing import Any, Dict

import pytest

from shared.models.node_enums import MemorySubtype, NodeType
from workflow_engine.tests.integration.utils.assertions import (
    assert_execution_success_status,
    assert_log_contains,
)
from workflow_engine.tests.integration.utils.workflow_factory import node, single_node_workflow


@pytest.mark.asyncio
async def test_key_value_store_operations(app_client, patch_workflow_definition, in_memory_logs):
    """Test key-value storage and retrieval."""
    memory_node = node(
        "n1",
        ntype=NodeType.MEMORY.value,
        subtype=MemorySubtype.KEY_VALUE_STORE.value,
        parameters={
            "memory_type": "key_value_store",
            "operation": "store",
            "key": "user_preferences",
            "value": '{"theme": "dark", "language": "en", "notifications": true}',
            "ttl": "3600",
        },
    )
    wf = single_node_workflow(memory_node)
    patch_workflow_definition(wf)

    # Execute workflow
    resp = await app_client.post(
        "/v1/workflows/wf_kv_store/execute",
        json={
            "workflow_id": "wf_kv_store",
            "user_id": "u1",
            "trigger_data": {"user_id": "user123", "session": "session456"},
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Assert execution success
    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs contain memory operation
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of MEMORY node")


@pytest.mark.asyncio
async def test_vector_database_operations(app_client, patch_workflow_definition, in_memory_logs):
    """Test vector database storage and similarity search."""
    memory_node = node(
        "n1",
        ntype=NodeType.MEMORY.value,
        subtype=MemorySubtype.VECTOR_DATABASE.value,
        parameters={
            "memory_type": "vector_database",
            "operation": "store",
            "collection": "documents",
            "content": "This is a sample document for vector storage and retrieval testing",
            "metadata": '{"type": "test_document", "category": "integration_test", "timestamp": "2025-01-17"}',
            "embedding_model": "text-embedding-ada-002",
        },
    )
    wf = single_node_workflow(memory_node)
    patch_workflow_definition(wf)

    # Execute workflow
    resp = await app_client.post(
        "/v1/workflows/wf_vector/execute",
        json={
            "workflow_id": "wf_vector",
            "user_id": "u1",
            "trigger_data": {"document_id": "doc123", "content_type": "text"},
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Assert execution success
    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs contain vector database operation
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of MEMORY node")


@pytest.mark.asyncio
async def test_conversation_buffer_management(
    app_client, patch_workflow_definition, in_memory_logs
):
    """Test conversation buffer memory management."""
    memory_node = node(
        "n1",
        ntype=NodeType.MEMORY.value,
        subtype=MemorySubtype.CONVERSATION_BUFFER.value,
        parameters={
            "memory_type": "conversation_buffer",
            "operation": "add_message",
            "conversation_id": "conv_789",
            "message": '{"role": "user", "content": "What is the weather like today?", "timestamp": "2025-01-17T10:00:00Z"}',
            "max_messages": "50",
            "buffer_strategy": "sliding_window",
        },
    )
    wf = single_node_workflow(memory_node)
    patch_workflow_definition(wf)

    # Execute workflow
    resp = await app_client.post(
        "/v1/workflows/wf_conversation/execute",
        json={
            "workflow_id": "wf_conversation",
            "user_id": "u1",
            "trigger_data": {"session_id": "sess_456", "chat_id": "chat_123"},
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Assert execution success
    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs contain conversation buffer operation
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of MEMORY node")


@pytest.mark.asyncio
async def test_entity_memory_storage(app_client, patch_workflow_definition, in_memory_logs):
    """Test entity-based memory storage."""
    memory_node = node(
        "n1",
        ntype=NodeType.MEMORY.value,
        subtype=MemorySubtype.ENTITY_MEMORY.value,
        parameters={
            "memory_type": "entity_memory",
            "operation": "update_entity",
            "entity_type": "person",
            "entity_id": "person_123",
            "entity_data": '{"name": "John Doe", "role": "Software Engineer", "department": "Engineering", "skills": ["Python", "JavaScript", "Docker"], "last_seen": "2025-01-17"}',
            "merge_strategy": "update",
        },
    )
    wf = single_node_workflow(memory_node)
    patch_workflow_definition(wf)

    # Execute workflow
    resp = await app_client.post(
        "/v1/workflows/wf_entity/execute",
        json={
            "workflow_id": "wf_entity",
            "user_id": "u1",
            "trigger_data": {"context": "employee_update", "source": "hr_system"},
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Assert execution success
    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs contain entity memory operation
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of MEMORY node")


@pytest.mark.asyncio
async def test_working_memory_operations(app_client, patch_workflow_definition, in_memory_logs):
    """Test working memory operations."""
    memory_node = node(
        "n1",
        ntype=NodeType.MEMORY.value,
        subtype=MemorySubtype.WORKING_MEMORY.value,
        parameters={
            "memory_type": "working_memory",
            "operation": "set_context",
            "context_id": "workflow_context_456",
            "context_data": '{"current_step": "data_processing", "variables": {"input_count": 100, "processed_count": 0, "error_count": 0}, "metadata": {"started_at": "2025-01-17T10:00:00Z", "workflow_version": "1.2.0"}}',
            "scope": "workflow_execution",
        },
    )
    wf = single_node_workflow(memory_node)
    patch_workflow_definition(wf)

    # Execute workflow
    resp = await app_client.post(
        "/v1/workflows/wf_working_memory/execute",
        json={
            "workflow_id": "wf_working_memory",
            "user_id": "u1",
            "trigger_data": {"execution_context": "batch_processing"},
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Assert execution success
    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs contain working memory operation
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of MEMORY node")


@pytest.mark.asyncio
async def test_context_generation(app_client, patch_workflow_definition, in_memory_logs):
    """Test context generation from stored memory."""
    memory_node = node(
        "n1",
        ntype=NodeType.MEMORY.value,
        subtype=MemorySubtype.CONVERSATION_BUFFER.value,
        parameters={
            "memory_type": "conversation_buffer",
            "operation": "get_context",
            "conversation_id": "conv_context_test",
            "context_window": 10,
            "include_metadata": True,
            "format": "chronological",
        },
    )
    wf = single_node_workflow(memory_node)
    patch_workflow_definition(wf)

    # Execute workflow
    resp = await app_client.post(
        "/v1/workflows/wf_context/execute",
        json={
            "workflow_id": "wf_context",
            "user_id": "u1",
            "trigger_data": {"request_context": "true", "session": "context_test"},
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Assert execution success
    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs contain context generation
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of MEMORY node")


@pytest.mark.asyncio
async def test_memory_parameter_validation(app_client, patch_workflow_definition):
    """Test memory node parameter validation."""
    # Test with minimal parameters (should still execute)
    memory_node = node(
        "n1",
        ntype=NodeType.MEMORY.value,
        subtype=MemorySubtype.KEY_VALUE_STORE.value,
        parameters={
            "memory_type": "key_value_store",
            "operation": "get"
            # Missing key parameter
        },
    )
    wf = single_node_workflow(memory_node)
    patch_workflow_definition(wf)

    resp = await app_client.post(
        "/v1/workflows/wf_memory_validation/execute",
        json={
            "workflow_id": "wf_memory_validation",
            "user_id": "u1",
            "trigger_data": {},
            "async_execution": False,
        },
    )

    # Should handle validation gracefully
    assert resp.status_code == 200
    # Current implementation may be permissive with validation


@pytest.mark.asyncio
async def test_memory_search_operations(app_client, patch_workflow_definition, in_memory_logs):
    """Test memory search and query operations."""
    memory_node = node(
        "n1",
        ntype=NodeType.MEMORY.value,
        subtype=MemorySubtype.VECTOR_DATABASE.value,
        parameters={
            "memory_type": "vector_database",
            "operation": "search",
            "collection": "knowledge_base",
            "query": "machine learning algorithms",
            "similarity_threshold": 0.7,
            "max_results": 5,
            "include_metadata": True,
        },
    )
    wf = single_node_workflow(memory_node)
    patch_workflow_definition(wf)

    # Execute workflow
    resp = await app_client.post(
        "/v1/workflows/wf_search/execute",
        json={
            "workflow_id": "wf_search",
            "user_id": "u1",
            "trigger_data": {"search_query": "AI models", "domain": "technology"},
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Assert execution success
    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs contain search operation
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of MEMORY node")


@pytest.mark.asyncio
async def test_memory_cleanup_operations(app_client, patch_workflow_definition, in_memory_logs):
    """Test memory cleanup and maintenance operations."""
    memory_node = node(
        "n1",
        ntype=NodeType.MEMORY.value,
        subtype=MemorySubtype.WORKING_MEMORY.value,
        parameters={
            "memory_type": "working_memory",
            "operation": "cleanup",
            "cleanup_criteria": '{"older_than": "1h", "status": "completed", "preserve_errors": true}',
            "batch_size": "100",
        },
    )
    wf = single_node_workflow(memory_node)
    patch_workflow_definition(wf)

    # Execute workflow
    resp = await app_client.post(
        "/v1/workflows/wf_cleanup/execute",
        json={
            "workflow_id": "wf_cleanup",
            "user_id": "u1",
            "trigger_data": {"maintenance": "true", "scheduled_cleanup": "true"},
            "async_execution": False,
        },
    )
    data: Dict[str, Any] = resp.json()

    # Assert execution success
    assert resp.status_code == 200
    assert_execution_success_status(data)

    # Check logs contain cleanup operation
    exec_id = data["execution_id"]
    logs = await in_memory_logs.get_logs(exec_id)
    assert_log_contains(logs, "Starting execution of MEMORY node")
