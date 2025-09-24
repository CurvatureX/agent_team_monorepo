"""
Memory Node Executor.

Handles various memory operations including storage, retrieval, and context generation
using the comprehensive memory implementations system.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from shared.models.node_enums import MemorySubtype, NodeType

from .base import BaseNodeExecutor, ExecutionStatus, NodeExecutionContext, NodeExecutionResult
from .factory import NodeExecutorFactory


@NodeExecutorFactory.register(NodeType.MEMORY.value)
class MemoryNodeExecutor(BaseNodeExecutor):
    """Executor for memory nodes with comprehensive memory system support."""

    def __init__(self, node_type: str = NodeType.MEMORY.value, subtype: str = None):
        super().__init__(node_type, subtype)

    async def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute memory node operations."""
        memory_type = self.subtype or context.get_parameter(
            "memory_type", MemorySubtype.KEY_VALUE_STORE.value
        )
        operation = context.get_parameter("operation", "store")

        self.log_execution(context, f"Executing memory node: {memory_type}/{operation}")

        try:
            # Handle different memory operations
            if operation == "store":
                return await self._handle_store_operation(context, memory_type)
            elif operation == "retrieve":
                return await self._handle_retrieve_operation(context, memory_type)
            elif operation == "context":
                return await self._handle_context_operation(context, memory_type)
            elif operation == "delete":
                return await self._handle_delete_operation(context, memory_type)
            elif operation == "update":
                return await self._handle_update_operation(context, memory_type)
            elif operation in ["add_message", "search", "cleanup", "generate", "set_context"]:
                # These operations map to existing handlers or generic behavior
                return await self._handle_generic_operation(context, memory_type, operation)
            else:
                return await self._handle_generic_operation(context, memory_type, operation)

        except Exception as e:
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=f"Memory operation failed: {str(e)}",
                error_details={"memory_type": memory_type, "operation": operation},
            )

    async def _handle_store_operation(
        self, context: NodeExecutionContext, memory_type: str
    ) -> NodeExecutionResult:
        """Handle memory store operations."""
        data_to_store = context.get_parameter("data", context.input_data)
        key = context.get_parameter("key", f"item_{datetime.now().timestamp()}")
        metadata = context.get_parameter("metadata", {})
        ttl_param = context.get_parameter("ttl", None)
        ttl = (
            int(ttl_param) if ttl_param and str(ttl_param).isdigit() else None
        )  # Time to live in seconds

        self.log_execution(context, f"Storing data in {memory_type} with key: {key}")

        try:
            if memory_type == MemorySubtype.CONVERSATION_BUFFER.value:
                return await self._store_conversation_buffer(context, data_to_store, key, metadata)
            elif memory_type == MemorySubtype.VECTOR_DATABASE.value:
                return await self._store_vector_database(context, data_to_store, key, metadata)
            elif memory_type == MemorySubtype.KEY_VALUE_STORE.value:
                return await self._store_key_value(context, data_to_store, key, metadata, ttl)
            elif memory_type == MemorySubtype.WORKING_MEMORY.value:
                return await self._store_working_memory(context, data_to_store, key, metadata)
            elif memory_type == MemorySubtype.ENTITY_MEMORY.value:
                return await self._store_entity_memory(context, data_to_store, key, metadata)
            elif memory_type == MemorySubtype.CONVERSATION_SUMMARY.value:
                return await self._store_conversation_summary(context, data_to_store, key, metadata)
            else:
                return await self._store_generic_memory(
                    context, data_to_store, key, metadata, memory_type
                )

        except Exception as e:
            self.log_execution(context, f"Store operation failed: {str(e)}", "ERROR")
            raise

    async def _handle_retrieve_operation(
        self, context: NodeExecutionContext, memory_type: str
    ) -> NodeExecutionResult:
        """Handle memory retrieve operations."""
        key = context.get_parameter("key", "")
        query = context.get_parameter("query", "")
        limit = context.get_parameter("limit", 10)
        filters = context.get_parameter("filters", {})

        self.log_execution(context, f"Retrieving data from {memory_type}")

        try:
            if memory_type == MemorySubtype.CONVERSATION_BUFFER.value:
                return await self._retrieve_conversation_buffer(context, key, limit, filters)
            elif memory_type == MemorySubtype.VECTOR_DATABASE.value:
                return await self._retrieve_vector_database(context, query, limit, filters)
            elif memory_type == MemorySubtype.KEY_VALUE_STORE.value:
                return await self._retrieve_key_value(context, key, filters)
            elif memory_type == MemorySubtype.WORKING_MEMORY.value:
                return await self._retrieve_working_memory(context, key, limit, filters)
            elif memory_type == MemorySubtype.ENTITY_MEMORY.value:
                return await self._retrieve_entity_memory(context, key, query, limit, filters)
            elif memory_type == MemorySubtype.CONVERSATION_SUMMARY.value:
                return await self._retrieve_conversation_summary(context, key, limit, filters)
            else:
                return await self._retrieve_generic_memory(
                    context, key, query, limit, filters, memory_type
                )

        except Exception as e:
            self.log_execution(context, f"Retrieve operation failed: {str(e)}", "ERROR")
            raise

    async def _handle_context_operation(
        self, context: NodeExecutionContext, memory_type: str
    ) -> NodeExecutionResult:
        """Handle context generation operations."""
        context_type = context.get_parameter("context_type", "summary")
        max_tokens = context.get_parameter("max_tokens", 1000)
        include_metadata = context.get_parameter("include_metadata", True)

        self.log_execution(context, f"Generating context from {memory_type}")

        # Generate context based on memory type
        generated_context = await self._generate_context(
            memory_type, context_type, max_tokens, include_metadata, context
        )

        output_data = {
            "memory_type": memory_type,
            "operation": "context",
            "context_type": context_type,
            "generated_context": generated_context,
            "max_tokens": max_tokens,
            "include_metadata": include_metadata,
            "timestamp": datetime.now().isoformat(),
        }

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={"node_type": "memory", "memory_type": memory_type, "operation": "context"},
        )

    async def _handle_delete_operation(
        self, context: NodeExecutionContext, memory_type: str
    ) -> NodeExecutionResult:
        """Handle memory delete operations."""
        key = context.get_parameter("key", "")
        filters = context.get_parameter("filters", {})

        self.log_execution(context, f"Deleting data from {memory_type}")

        # Simulate deletion (in real implementation, delete from actual storage)
        deleted_count = 1 if key else len(filters)

        output_data = {
            "memory_type": memory_type,
            "operation": "delete",
            "key": key,
            "filters": filters,
            "deleted_count": deleted_count,
            "timestamp": datetime.now().isoformat(),
        }

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={"node_type": "memory", "memory_type": memory_type, "operation": "delete"},
        )

    async def _handle_update_operation(
        self, context: NodeExecutionContext, memory_type: str
    ) -> NodeExecutionResult:
        """Handle memory update operations."""
        key = context.get_parameter("key", "")
        updates = context.get_parameter("updates", {})
        upsert = context.get_parameter("upsert", False)

        self.log_execution(context, f"Updating data in {memory_type}")

        # Simulate update (in real implementation, update actual storage)
        updated_count = 1 if key else 0

        output_data = {
            "memory_type": memory_type,
            "operation": "update",
            "key": key,
            "updates": updates,
            "upsert": upsert,
            "updated_count": updated_count,
            "timestamp": datetime.now().isoformat(),
        }

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={"node_type": "memory", "memory_type": memory_type, "operation": "update"},
        )

    async def _handle_generic_operation(
        self, context: NodeExecutionContext, memory_type: str, operation: str
    ) -> NodeExecutionResult:
        """Handle generic memory operations."""
        import asyncio

        self.log_execution(context, f"Executing generic memory operation: {operation}")

        # Simulate processing time
        await asyncio.sleep(0.1)

        output_data = {
            "memory_type": memory_type,
            "operation": operation,
            "result": f"Generic {operation} operation completed",
            "input_data": context.input_data,
            "parameters": dict(context.parameters) if context.parameters else {},
            "timestamp": datetime.now().isoformat(),
        }

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={"node_type": "memory", "memory_type": memory_type, "operation": operation},
        )

    # Specific memory type implementations - Store operations

    async def _store_conversation_buffer(
        self, context: NodeExecutionContext, data: Any, key: str, metadata: Dict
    ) -> NodeExecutionResult:
        """Store data in conversation buffer memory."""
        # In real implementation, this would use actual ConversationBufferMemory
        max_messages = context.get_parameter("max_messages", 50)

        output_data = {
            "memory_type": MemorySubtype.CONVERSATION_BUFFER.value,
            "operation": "store",
            "key": key,
            "data_stored": data,
            "metadata": metadata,
            "max_messages": max_messages,
            "buffer_size": 1,  # Simulated current size
            "timestamp": datetime.now().isoformat(),
        }

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={
                "node_type": "memory",
                "memory_type": MemorySubtype.CONVERSATION_BUFFER.value,
                "operation": "store",
            },
        )

    async def _store_vector_database(
        self, context: NodeExecutionContext, data: Any, key: str, metadata: Dict
    ) -> NodeExecutionResult:
        """Store data in vector database memory."""
        # In real implementation, this would use actual VectorDatabaseMemory with embeddings
        import hashlib

        # Simulate vector embedding (in real implementation, use actual embedding model)
        text_content = str(data)
        vector_id = hashlib.md5(text_content.encode()).hexdigest()

        output_data = {
            "memory_type": MemorySubtype.VECTOR_DATABASE.value,
            "operation": "store",
            "key": key,
            "vector_id": vector_id,
            "data_stored": data,
            "metadata": metadata,
            "embedding_dimensions": 768,  # Simulated
            "similarity_threshold": context.get_parameter("similarity_threshold", 0.8),
            "timestamp": datetime.now().isoformat(),
        }

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={
                "node_type": "memory",
                "memory_type": MemorySubtype.VECTOR_DATABASE.value,
                "operation": "store",
            },
        )

    async def _store_key_value(
        self, context: NodeExecutionContext, data: Any, key: str, metadata: Dict, ttl: Optional[int]
    ) -> NodeExecutionResult:
        """Store data in key-value store memory."""
        # In real implementation, this would use actual KeyValueStoreMemory (Redis, etc.)
        expires_at = None
        if ttl:
            from datetime import timedelta

            expires_at = (datetime.now() + timedelta(seconds=ttl)).isoformat()

        output_data = {
            "memory_type": MemorySubtype.KEY_VALUE_STORE.value,
            "operation": "store",
            "key": key,
            "data_stored": data,
            "metadata": metadata,
            "ttl": ttl,
            "expires_at": expires_at,
            "timestamp": datetime.now().isoformat(),
        }

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={
                "node_type": "memory",
                "memory_type": MemorySubtype.KEY_VALUE_STORE.value,
                "operation": "store",
            },
        )

    async def _store_working_memory(
        self, context: NodeExecutionContext, data: Any, key: str, metadata: Dict
    ) -> NodeExecutionResult:
        """Store data in working memory."""
        # In real implementation, this would use actual WorkingMemory
        priority = context.get_parameter("priority", "medium")

        output_data = {
            "memory_type": MemorySubtype.WORKING_MEMORY.value,
            "operation": "store",
            "key": key,
            "data_stored": data,
            "metadata": metadata,
            "priority": priority,
            "memory_usage": "low",  # Simulated
            "timestamp": datetime.now().isoformat(),
        }

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={
                "node_type": "memory",
                "memory_type": MemorySubtype.WORKING_MEMORY.value,
                "operation": "store",
            },
        )

    async def _store_entity_memory(
        self, context: NodeExecutionContext, data: Any, key: str, metadata: Dict
    ) -> NodeExecutionResult:
        """Store data in entity memory."""
        # In real implementation, this would use actual EntityMemory
        entity_type = context.get_parameter("entity_type", "unknown")
        entity_id = context.get_parameter("entity_id", key)

        output_data = {
            "memory_type": MemorySubtype.ENTITY_MEMORY.value,
            "operation": "store",
            "key": key,
            "entity_id": entity_id,
            "entity_type": entity_type,
            "data_stored": data,
            "metadata": metadata,
            "timestamp": datetime.now().isoformat(),
        }

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={
                "node_type": "memory",
                "memory_type": MemorySubtype.ENTITY_MEMORY.value,
                "operation": "store",
            },
        )

    async def _store_conversation_summary(
        self, context: NodeExecutionContext, data: Any, key: str, metadata: Dict
    ) -> NodeExecutionResult:
        """Store data in conversation summary memory."""
        # In real implementation, this would use actual ConversationSummaryMemory
        summary_length = context.get_parameter("summary_length", "medium")

        output_data = {
            "memory_type": MemorySubtype.CONVERSATION_SUMMARY.value,
            "operation": "store",
            "key": key,
            "data_stored": data,
            "metadata": metadata,
            "summary_length": summary_length,
            "compression_ratio": 0.3,  # Simulated
            "timestamp": datetime.now().isoformat(),
        }

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={
                "node_type": "memory",
                "memory_type": MemorySubtype.CONVERSATION_SUMMARY.value,
                "operation": "store",
            },
        )

    async def _store_generic_memory(
        self, context: NodeExecutionContext, data: Any, key: str, metadata: Dict, memory_type: str
    ) -> NodeExecutionResult:
        """Store data in generic memory type."""
        output_data = {
            "memory_type": memory_type,
            "operation": "store",
            "key": key,
            "data_stored": data,
            "metadata": metadata,
            "timestamp": datetime.now().isoformat(),
        }

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={"node_type": "memory", "memory_type": memory_type, "operation": "store"},
        )

    # Retrieve operations for each memory type

    async def _retrieve_conversation_buffer(
        self, context: NodeExecutionContext, key: str, limit: int, filters: Dict
    ) -> NodeExecutionResult:
        """Retrieve data from conversation buffer memory."""
        # Simulate retrieved conversation data
        retrieved_data = [
            {"role": "user", "content": "Hello", "timestamp": datetime.now().isoformat()},
            {"role": "assistant", "content": "Hi there!", "timestamp": datetime.now().isoformat()},
        ]

        output_data = {
            "memory_type": MemorySubtype.CONVERSATION_BUFFER.value,
            "operation": "retrieve",
            "key": key,
            "limit": limit,
            "filters": filters,
            "retrieved_data": retrieved_data,
            "total_messages": len(retrieved_data),
            "timestamp": datetime.now().isoformat(),
        }

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={
                "node_type": "memory",
                "memory_type": MemorySubtype.CONVERSATION_BUFFER.value,
                "operation": "retrieve",
            },
        )

    async def _retrieve_vector_database(
        self, context: NodeExecutionContext, query: str, limit: int, filters: Dict
    ) -> NodeExecutionResult:
        """Retrieve data from vector database memory."""
        # Simulate vector search results
        retrieved_data = [
            {"content": f"Similar content to: {query}", "similarity_score": 0.95, "metadata": {}},
            {"content": f"Related content for: {query}", "similarity_score": 0.87, "metadata": {}},
        ]

        output_data = {
            "memory_type": MemorySubtype.VECTOR_DATABASE.value,
            "operation": "retrieve",
            "query": query,
            "limit": limit,
            "filters": filters,
            "retrieved_data": retrieved_data,
            "total_results": len(retrieved_data),
            "similarity_threshold": context.get_parameter("similarity_threshold", 0.8),
            "timestamp": datetime.now().isoformat(),
        }

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={
                "node_type": "memory",
                "memory_type": MemorySubtype.VECTOR_DATABASE.value,
                "operation": "retrieve",
            },
        )

    async def _retrieve_key_value(
        self, context: NodeExecutionContext, key: str, filters: Dict
    ) -> NodeExecutionResult:
        """Retrieve data from key-value store memory."""
        # Simulate key-value retrieval
        retrieved_data = {
            "value": f"Stored value for key: {key}",
            "metadata": {},
            "stored_at": datetime.now().isoformat(),
        }

        output_data = {
            "memory_type": MemorySubtype.KEY_VALUE_STORE.value,
            "operation": "retrieve",
            "key": key,
            "filters": filters,
            "retrieved_data": retrieved_data,
            "found": True,
            "timestamp": datetime.now().isoformat(),
        }

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={
                "node_type": "memory",
                "memory_type": MemorySubtype.KEY_VALUE_STORE.value,
                "operation": "retrieve",
            },
        )

    async def _retrieve_working_memory(
        self, context: NodeExecutionContext, key: str, limit: int, filters: Dict
    ) -> NodeExecutionResult:
        """Retrieve data from working memory."""
        # Simulate working memory retrieval
        retrieved_data = [
            {"key": f"item_{i}", "data": f"Working memory item {i}", "priority": "medium"}
            for i in range(min(limit, 3))
        ]

        output_data = {
            "memory_type": MemorySubtype.WORKING_MEMORY.value,
            "operation": "retrieve",
            "key": key,
            "limit": limit,
            "filters": filters,
            "retrieved_data": retrieved_data,
            "total_items": len(retrieved_data),
            "timestamp": datetime.now().isoformat(),
        }

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={
                "node_type": "memory",
                "memory_type": MemorySubtype.WORKING_MEMORY.value,
                "operation": "retrieve",
            },
        )

    async def _retrieve_entity_memory(
        self, context: NodeExecutionContext, key: str, query: str, limit: int, filters: Dict
    ) -> NodeExecutionResult:
        """Retrieve data from entity memory."""
        # Simulate entity memory retrieval
        retrieved_data = [
            {
                "entity_id": "user_123",
                "entity_type": "user",
                "attributes": {"name": "John", "age": 30},
            },
            {
                "entity_id": "product_456",
                "entity_type": "product",
                "attributes": {"name": "Widget", "price": 19.99},
            },
        ]

        output_data = {
            "memory_type": MemorySubtype.ENTITY_MEMORY.value,
            "operation": "retrieve",
            "key": key,
            "query": query,
            "limit": limit,
            "filters": filters,
            "retrieved_data": retrieved_data,
            "total_entities": len(retrieved_data),
            "timestamp": datetime.now().isoformat(),
        }

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={
                "node_type": "memory",
                "memory_type": MemorySubtype.ENTITY_MEMORY.value,
                "operation": "retrieve",
            },
        )

    async def _retrieve_conversation_summary(
        self, context: NodeExecutionContext, key: str, limit: int, filters: Dict
    ) -> NodeExecutionResult:
        """Retrieve data from conversation summary memory."""
        # Simulate conversation summary retrieval
        retrieved_data = {
            "summary": "This conversation covered topics about AI, workflow automation, and memory systems.",
            "key_points": ["AI capabilities", "Workflow design", "Memory management"],
            "participants": ["user", "assistant"],
            "duration": "15 minutes",
        }

        output_data = {
            "memory_type": MemorySubtype.CONVERSATION_SUMMARY.value,
            "operation": "retrieve",
            "key": key,
            "limit": limit,
            "filters": filters,
            "retrieved_data": retrieved_data,
            "summary_available": True,
            "timestamp": datetime.now().isoformat(),
        }

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={
                "node_type": "memory",
                "memory_type": MemorySubtype.CONVERSATION_SUMMARY.value,
                "operation": "retrieve",
            },
        )

    async def _retrieve_generic_memory(
        self,
        context: NodeExecutionContext,
        key: str,
        query: str,
        limit: int,
        filters: Dict,
        memory_type: str,
    ) -> NodeExecutionResult:
        """Retrieve data from generic memory type."""
        # Simulate generic memory retrieval
        retrieved_data = [
            {"id": i, "data": f"Generic {memory_type} item {i}"} for i in range(min(limit, 3))
        ]

        output_data = {
            "memory_type": memory_type,
            "operation": "retrieve",
            "key": key,
            "query": query,
            "limit": limit,
            "filters": filters,
            "retrieved_data": retrieved_data,
            "total_items": len(retrieved_data),
            "timestamp": datetime.now().isoformat(),
        }

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={"node_type": "memory", "memory_type": memory_type, "operation": "retrieve"},
        )

    async def _generate_context(
        self,
        memory_type: str,
        context_type: str,
        max_tokens: int,
        include_metadata: bool,
        context: NodeExecutionContext,
    ) -> Dict[str, Any]:
        """Generate context from memory."""
        # Simulate context generation based on memory type
        if context_type == "summary":
            generated_context = {
                "summary": f"Context summary from {memory_type} memory system",
                "key_insights": ["Insight 1", "Insight 2", "Insight 3"],
                "token_count": min(max_tokens, 500),
            }
        elif context_type == "recent":
            generated_context = {
                "recent_items": [
                    {"timestamp": datetime.now().isoformat(), "content": "Recent item 1"},
                    {"timestamp": datetime.now().isoformat(), "content": "Recent item 2"},
                ],
                "token_count": min(max_tokens, 300),
            }
        elif context_type == "relevant":
            query = context.get_parameter("query", "")
            generated_context = {
                "relevant_items": [
                    {"relevance_score": 0.95, "content": f"Highly relevant to: {query}"},
                    {"relevance_score": 0.87, "content": f"Related to: {query}"},
                ],
                "query": query,
                "token_count": min(max_tokens, 400),
            }
        else:
            generated_context = {
                "context": f"Generated {context_type} context from {memory_type}",
                "token_count": min(max_tokens, 200),
            }

        if include_metadata:
            generated_context["metadata"] = {
                "generation_time": datetime.now().isoformat(),
                "memory_type": memory_type,
                "context_type": context_type,
                "max_tokens": max_tokens,
            }

        return generated_context

    def validate_parameters(self, context: NodeExecutionContext) -> tuple[bool, str]:
        """Validate memory node parameters."""
        memory_type = self.subtype or context.get_parameter(
            "memory_type", MemorySubtype.KEY_VALUE_STORE.value
        )
        operation = context.get_parameter("operation", "store")

        # Use enums directly for validation
        valid_memory_subtypes = [e.value for e in MemorySubtype]

        valid_operations = [
            "store",
            "retrieve",
            "context",
            "delete",
            "update",
            "add_message",
            "cleanup",
            "search",
            "generate",
            "set_context",
            "update_entity",
            "get_context",
        ]

        if memory_type not in valid_memory_subtypes:
            error_msg = f"Invalid memory type: {memory_type}. Valid types: {', '.join(valid_memory_subtypes)}"
            self.log_execution(context, error_msg, "ERROR")
            return False, error_msg

        if operation not in valid_operations:
            error_msg = (
                f"Invalid operation: {operation}. Valid operations: {', '.join(valid_operations)}"
            )
            self.log_execution(context, error_msg, "ERROR")
            return False, error_msg

        # Validate operation-specific parameters
        if operation == "store":
            data = context.get_parameter("data")
            if data is None and not context.input_data:
                return False, "Store operation requires 'data' parameter or input_data"

        elif operation == "retrieve":
            key = context.get_parameter("key", "")
            query = context.get_parameter("query", "")
            if not key and not query and memory_type == MemorySubtype.VECTOR_DATABASE.value:
                return False, "Vector database retrieve operation requires 'query' parameter"
            elif not key and memory_type == MemorySubtype.KEY_VALUE_STORE.value:
                return False, "Key-value store retrieve operation requires 'key' parameter"

        elif operation == "context":
            context_type = context.get_parameter("context_type", "summary")
            valid_context_types = ["summary", "recent", "relevant"]
            if context_type not in valid_context_types:
                return (
                    False,
                    f"Invalid context_type: {context_type}. Valid types: {', '.join(valid_context_types)}",
                )

        return True, ""
