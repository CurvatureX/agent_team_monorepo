# Memory Node Persistence Implementation Guide

## 🎯 **Implementation Objective**

Replace in-memory storage in `workflow_engine_v2/runners/memory.py` with persistent database storage using Supabase tables, ensuring data survives service restarts and enables cross-session memory sharing.

## 📊 **Current State Analysis**

### Current In-Memory Implementation (`workflow_engine_v2/runners/memory.py`)
```python
class ConversationBufferMemory:
    def __init__(self):
        self.messages = []  # ❌ Lost on restart
        self.max_messages = 100

class VectorDatabaseMemory:
    def __init__(self):
        self.vectors = {}  # ❌ Lost on restart
        self.embeddings = {}

class EntityMemory:
    def __init__(self):
        self.entities = {}  # ❌ Lost on restart
        self.relationships = []

class WorkingMemory:
    def __init__(self):
        self.working_data = {}  # ❌ Lost on restart
        self.timestamp = None
```

### Database Schema Available (Enhanced)
- ✅ `conversation_buffers` - Message storage with ordering
- ✅ `conversation_summaries` - Conversation summaries
- ✅ `episodic_memory` - Episode-based memory storage
- ✅ `knowledge_facts` - Structured knowledge storage
- ✅ `knowledge_rules` - Rule-based knowledge
- ✅ `graph_nodes` - Graph-based memory nodes
- ✅ `graph_relationships` - Graph relationships
- ✅ `document_store` - Document storage with full-text search
- ✅ `embeddings` - Vector storage (existing)
- ✅ `entities` + `entity_relationships` - Entity storage (existing)
- ✅ `memory_data` - Generic key-value storage (existing)

## 🔧 **Implementation Plan**

### Phase 1: Create Persistent Memory Base Classes

#### 1.1 Abstract Base Class
```python
# workflow_engine_v2/runners/memory/base_persistent_memory.py
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from supabase import create_client, Client
from ..core.config import settings

class PersistentMemoryBase(ABC):
    """Base class for all persistent memory implementations."""

    def __init__(self, user_id: str, memory_node_id: str):
        self.user_id = user_id
        self.memory_node_id = memory_node_id
        self.supabase: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SECRET_KEY
        )

    @abstractmethod
    async def store(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Store data in the database."""
        pass

    @abstractmethod
    async def retrieve(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve data from the database."""
        pass

    @abstractmethod
    async def update(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing data in the database."""
        pass

    @abstractmethod
    async def delete(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Delete data from the database."""
        pass

    async def _execute_query(self, table: str, operation: str, data: Dict = None, filters: Dict = None):
        """Helper method for database operations with error handling."""
        try:
            query = self.supabase.table(table)

            if operation == "insert":
                result = query.insert(data).execute()
            elif operation == "select":
                if filters:
                    for key, value in filters.items():
                        query = query.eq(key, value)
                result = query.select().execute()
            elif operation == "update":
                if filters:
                    for key, value in filters.items():
                        query = query.eq(key, value)
                result = query.update(data).execute()
            elif operation == "delete":
                if filters:
                    for key, value in filters.items():
                        query = query.eq(key, value)
                result = query.delete().execute()

            return {"success": True, "data": result.data}

        except Exception as e:
            return {"success": False, "error": str(e)}
```

#### 1.2 Conversation Buffer Memory Implementation
```python
# workflow_engine_v2/runners/memory/conversation_buffer.py
from typing import Dict, List, Any, Optional
from .base_persistent_memory import PersistentMemoryBase

class ConversationBufferMemory(PersistentMemoryBase):
    """Persistent conversation buffer using conversation_buffers table."""

    async def store(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Store a message in the conversation buffer."""

        # Get next message order
        next_order = await self._get_next_message_order()

        message_data = {
            "user_id": self.user_id,
            "memory_node_id": self.memory_node_id,
            "message_order": next_order,
            "role": data.get("role", "user"),
            "content": data.get("content", ""),
            "metadata": data.get("metadata", {})
        }

        result = await self._execute_query(
            table="conversation_buffers",
            operation="insert",
            data=message_data
        )

        if result["success"]:
            # Maintain max message limit
            await self._cleanup_old_messages()
            return {
                "success": True,
                "message_order": next_order,
                "stored_at": "conversation_buffers"
            }
        else:
            return {
                "success": False,
                "error": result["error"]
            }

    async def retrieve(self, query: Dict[str, Any] = None) -> Dict[str, Any]:
        """Retrieve conversation messages in chronological order."""

        filters = {
            "user_id": self.user_id,
            "memory_node_id": self.memory_node_id
        }

        result = await self._execute_query(
            table="conversation_buffers",
            operation="select",
            filters=filters
        )

        if result["success"]:
            # Sort by message_order
            messages = sorted(result["data"], key=lambda x: x["message_order"])
            return {
                "success": True,
                "messages": messages,
                "total_count": len(messages)
            }
        else:
            return {
                "success": False,
                "error": result["error"],
                "messages": []
            }

    async def update(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a specific message by message_order."""

        filters = {
            "user_id": self.user_id,
            "memory_node_id": self.memory_node_id,
            "message_order": data["message_order"]
        }

        update_data = {}
        if "content" in data:
            update_data["content"] = data["content"]
        if "metadata" in data:
            update_data["metadata"] = data["metadata"]

        return await self._execute_query(
            table="conversation_buffers",
            operation="update",
            data=update_data,
            filters=filters
        )

    async def delete(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Delete specific messages or clear all."""

        filters = {
            "user_id": self.user_id,
            "memory_node_id": self.memory_node_id
        }

        # Add specific message_order if provided
        if "message_order" in query:
            filters["message_order"] = query["message_order"]

        return await self._execute_query(
            table="conversation_buffers",
            operation="delete",
            filters=filters
        )

    async def _get_next_message_order(self) -> int:
        """Get the next message order number."""
        result = await self._execute_query(
            table="conversation_buffers",
            operation="select",
            filters={
                "user_id": self.user_id,
                "memory_node_id": self.memory_node_id
            }
        )

        if result["success"] and result["data"]:
            max_order = max(msg["message_order"] for msg in result["data"])
            return max_order + 1
        return 0

    async def _cleanup_old_messages(self, max_messages: int = 100):
        """Remove oldest messages if exceeding limit."""
        result = await self.retrieve()

        if result["success"] and len(result["messages"]) > max_messages:
            # Keep most recent messages
            messages_to_delete = result["messages"][:-max_messages]

            for msg in messages_to_delete:
                await self.delete({"message_order": msg["message_order"]})
```

### Phase 2: Vector Database Memory Implementation

#### 2.1 Vector Database Memory with Embeddings
```python
# workflow_engine_v2/runners/memory/vector_database.py
from typing import Dict, List, Any, Optional
import openai
from .base_persistent_memory import PersistentMemoryBase
from ..core.config import settings

class VectorDatabaseMemory(PersistentMemoryBase):
    """Persistent vector database using embeddings table."""

    def __init__(self, user_id: str, memory_node_id: str):
        super().__init__(user_id, memory_node_id)
        openai.api_key = settings.OPENAI_API_KEY

    async def store(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Store text with generated embeddings."""

        text = data.get("text", "")
        if not text:
            return {"success": False, "error": "Text content required for vector storage"}

        # Generate embedding using OpenAI
        try:
            embedding_response = await openai.Embedding.acreate(
                model="text-embedding-ada-002",
                input=text
            )
            embedding = embedding_response["data"][0]["embedding"]
        except Exception as e:
            return {"success": False, "error": f"Failed to generate embedding: {str(e)}"}

        # Store in embeddings table
        embedding_data = {
            "user_id": self.user_id,
            "content": text,
            "embedding": embedding,
            "metadata": {
                "memory_node_id": self.memory_node_id,
                "document_type": data.get("document_type", "text"),
                **data.get("metadata", {})
            }
        }

        result = await self._execute_query(
            table="embeddings",
            operation="insert",
            data=embedding_data
        )

        return result

    async def retrieve(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Perform semantic search using vector similarity."""

        query_text = query.get("text", "")
        if not query_text:
            return {"success": False, "error": "Query text required for vector search"}

        # Generate query embedding
        try:
            embedding_response = await openai.Embedding.acreate(
                model="text-embedding-ada-002",
                input=query_text
            )
            query_embedding = embedding_response["data"][0]["embedding"]
        except Exception as e:
            return {"success": False, "error": f"Failed to generate query embedding: {str(e)}"}

        # Perform vector similarity search using raw SQL
        similarity_threshold = query.get("similarity_threshold", 0.3)
        limit = query.get("limit", 10)

        try:
            # Using pgvector similarity search
            sql = """
            SELECT content, metadata,
                   1 - (embedding <=> %s) as similarity_score
            FROM embeddings
            WHERE user_id = %s
              AND metadata ->> 'memory_node_id' = %s
              AND 1 - (embedding <=> %s) > %s
            ORDER BY embedding <=> %s
            LIMIT %s
            """

            result = self.supabase.rpc("execute_sql", {
                "query": sql,
                "params": [
                    query_embedding, self.user_id, self.memory_node_id,
                    query_embedding, similarity_threshold, query_embedding, limit
                ]
            }).execute()

            return {
                "success": True,
                "results": result.data,
                "query_text": query_text,
                "similarity_threshold": similarity_threshold
            }

        except Exception as e:
            return {"success": False, "error": f"Vector search failed: {str(e)}"}

    async def update(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing vector entries."""
        # Implementation for updating embeddings if needed
        return {"success": False, "error": "Vector updates not implemented - create new entry instead"}

    async def delete(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Delete vector entries by metadata filters."""

        # Build SQL for complex metadata filtering
        filters = {
            "user_id": self.user_id,
            "metadata->>memory_node_id": self.memory_node_id
        }

        # Add additional metadata filters from query
        for key, value in query.get("metadata_filters", {}).items():
            filters[f"metadata->>{key}"] = value

        return await self._execute_query(
            table="embeddings",
            operation="delete",
            filters=filters
        )
```

### Phase 3: Entity Memory Implementation

#### 3.1 Entity Memory with Relationships
```python
# workflow_engine_v2/runners/memory/entity_memory.py
from typing import Dict, List, Any, Optional
from .base_persistent_memory import PersistentMemoryBase

class EntityMemory(PersistentMemoryBase):
    """Persistent entity memory using entities and entity_relationships tables."""

    async def store(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Store entity and its relationships."""

        entity_data = {
            "user_id": self.user_id,
            "name": data.get("name", ""),
            "entity_type": data.get("entity_type", "unknown"),
            "properties": {
                "memory_node_id": self.memory_node_id,
                **data.get("properties", {})
            }
        }

        # Store entity
        entity_result = await self._execute_query(
            table="entities",
            operation="insert",
            data=entity_data
        )

        if not entity_result["success"]:
            return entity_result

        entity_id = entity_result["data"][0]["id"]

        # Store relationships if provided
        relationships = data.get("relationships", [])
        relationship_results = []

        for rel in relationships:
            rel_data = {
                "user_id": self.user_id,
                "source_entity_id": entity_id,
                "target_entity_id": rel.get("target_entity_id"),
                "relationship_type": rel.get("type", "related_to"),
                "properties": {
                    "memory_node_id": self.memory_node_id,
                    **rel.get("properties", {})
                }
            }

            rel_result = await self._execute_query(
                table="entity_relationships",
                operation="insert",
                data=rel_data
            )
            relationship_results.append(rel_result)

        return {
            "success": True,
            "entity_id": entity_id,
            "relationships_created": len([r for r in relationship_results if r["success"]])
        }

    async def retrieve(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve entities and their relationships."""

        filters = {
            "user_id": self.user_id,
            "properties->>memory_node_id": self.memory_node_id
        }

        # Add entity name filter if provided
        if "name" in query:
            filters["name"] = query["name"]

        if "entity_type" in query:
            filters["entity_type"] = query["entity_type"]

        # Get entities
        entities_result = await self._execute_query(
            table="entities",
            operation="select",
            filters=filters
        )

        if not entities_result["success"]:
            return entities_result

        entities = entities_result["data"]

        # Get relationships for each entity
        for entity in entities:
            rel_result = await self._execute_query(
                table="entity_relationships",
                operation="select",
                filters={
                    "user_id": self.user_id,
                    "source_entity_id": entity["id"]
                }
            )

            entity["relationships"] = rel_result["data"] if rel_result["success"] else []

        return {
            "success": True,
            "entities": entities,
            "total_count": len(entities)
        }

    async def update(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update entity properties."""

        entity_id = data.get("entity_id")
        if not entity_id:
            return {"success": False, "error": "entity_id required for update"}

        update_data = {}
        if "name" in data:
            update_data["name"] = data["name"]
        if "entity_type" in data:
            update_data["entity_type"] = data["entity_type"]
        if "properties" in data:
            update_data["properties"] = data["properties"]

        return await self._execute_query(
            table="entities",
            operation="update",
            data=update_data,
            filters={
                "user_id": self.user_id,
                "id": entity_id
            }
        )

    async def delete(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Delete entities and their relationships."""

        entity_id = query.get("entity_id")

        if entity_id:
            # Delete specific entity and its relationships
            # Relationships will be deleted by CASCADE
            return await self._execute_query(
                table="entities",
                operation="delete",
                filters={
                    "user_id": self.user_id,
                    "id": entity_id
                }
            )
        else:
            # Delete all entities for this memory node
            return await self._execute_query(
                table="entities",
                operation="delete",
                filters={
                    "user_id": self.user_id,
                    "properties->>memory_node_id": self.memory_node_id
                }
            )
```

### Phase 4: Working Memory Implementation

#### 4.1 Working Memory with TTL Support
```python
# workflow_engine_v2/runners/memory/working_memory.py
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from .base_persistent_memory import PersistentMemoryBase

class WorkingMemory(PersistentMemoryBase):
    """Persistent working memory using memory_data table with TTL support."""

    async def store(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Store temporary working data with optional expiration."""

        key = data.get("key", "")
        if not key:
            return {"success": False, "error": "Key required for working memory storage"}

        # Calculate expiration if TTL provided
        expires_at = None
        if "ttl_seconds" in data:
            expires_at = datetime.utcnow() + timedelta(seconds=data["ttl_seconds"])

        memory_data = {
            "user_id": self.user_id,
            "memory_node_id": self.memory_node_id,
            "key": key,
            "value": data.get("value"),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "metadata": data.get("metadata", {})
        }

        # Use upsert to handle key conflicts
        try:
            result = self.supabase.table("memory_data").upsert(
                memory_data,
                on_conflict="user_id,memory_node_id,key"
            ).execute()

            return {
                "success": True,
                "key": key,
                "expires_at": expires_at.isoformat() if expires_at else None
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def retrieve(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve working memory data, automatically cleaning expired entries."""

        # Clean expired entries first
        await self._cleanup_expired()

        filters = {
            "user_id": self.user_id,
            "memory_node_id": self.memory_node_id
        }

        # Add key filter if specified
        if "key" in query:
            filters["key"] = query["key"]

        result = await self._execute_query(
            table="memory_data",
            operation="select",
            filters=filters
        )

        if result["success"]:
            # If specific key requested, return single value
            if "key" in query and result["data"]:
                return {
                    "success": True,
                    "key": query["key"],
                    "value": result["data"][0]["value"],
                    "metadata": result["data"][0]["metadata"]
                }
            else:
                # Return all key-value pairs
                data_dict = {
                    item["key"]: {
                        "value": item["value"],
                        "metadata": item["metadata"],
                        "expires_at": item["expires_at"]
                    }
                    for item in result["data"]
                }
                return {
                    "success": True,
                    "data": data_dict,
                    "total_keys": len(data_dict)
                }

        return result

    async def update(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update working memory entry."""

        key = data.get("key")
        if not key:
            return {"success": False, "error": "Key required for update"}

        # Use store method with same key (upsert behavior)
        return await self.store(data)

    async def delete(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Delete working memory entries."""

        filters = {
            "user_id": self.user_id,
            "memory_node_id": self.memory_node_id
        }

        if "key" in query:
            filters["key"] = query["key"]

        return await self._execute_query(
            table="memory_data",
            operation="delete",
            filters=filters
        )

    async def _cleanup_expired(self):
        """Remove expired entries from working memory."""
        try:
            current_time = datetime.utcnow().isoformat()
            self.supabase.table("memory_data").delete().lt("expires_at", current_time).execute()
        except Exception:
            # Silent cleanup failure - not critical
            pass
```

### Phase 5: Memory Factory Integration

#### 5.1 Updated Memory Factory
```python
# workflow_engine_v2/runners/memory.py (Updated)
from typing import Dict, Any, Type
from .memory.conversation_buffer import ConversationBufferMemory
from .memory.vector_database import VectorDatabaseMemory
from .memory.entity_memory import EntityMemory
from .memory.working_memory import WorkingMemory
from .memory.base_persistent_memory import PersistentMemoryBase

class MemoryNodeExecutor:
    """Updated memory node executor with persistent storage."""

    # Memory type mapping to persistent classes
    MEMORY_IMPLEMENTATIONS = {
        "CONVERSATION_BUFFER": ConversationBufferMemory,
        "VECTOR_DATABASE": VectorDatabaseMemory,
        "ENTITY_MEMORY": EntityMemory,
        "WORKING_MEMORY": WorkingMemory,

        # Additional implementations to be added
        "CONVERSATION_SUMMARY": None,  # TODO: Implement
        "DOCUMENT_STORE": None,        # TODO: Implement
        "EPISODIC_MEMORY": None,       # TODO: Implement
        "KNOWLEDGE_BASE": None,        # TODO: Implement
        "GRAPH_MEMORY": None,          # TODO: Implement
    }

    @staticmethod
    def create_memory_instance(
        memory_type: str,
        user_id: str,
        memory_node_id: str
    ) -> PersistentMemoryBase:
        """Factory method to create persistent memory instances."""

        implementation_class = MemoryNodeExecutor.MEMORY_IMPLEMENTATIONS.get(memory_type)

        if implementation_class is None:
            raise ValueError(f"Memory type '{memory_type}' not implemented or not supported")

        return implementation_class(user_id=user_id, memory_node_id=memory_node_id)

    async def execute(self, context) -> Any:
        """Execute memory operation using persistent storage."""

        memory_type = context.node.configurations.get("memory_type")
        operation = context.node.configurations.get("operation", "store")

        user_id = context.execution.get("user_id")
        memory_node_id = context.node.id

        try:
            # Create persistent memory instance
            memory = self.create_memory_instance(memory_type, user_id, memory_node_id)

            # Execute operation
            if operation == "store":
                result = await memory.store(context.input_data.get("main", {}))
            elif operation == "retrieve":
                result = await memory.retrieve(context.input_data.get("main", {}))
            elif operation == "update":
                result = await memory.update(context.input_data.get("main", {}))
            elif operation == "delete":
                result = await memory.delete(context.input_data.get("main", {}))
            else:
                return NodeExecutionResult(
                    status=ExecutionStatus.ERROR,
                    error_message=f"Unsupported memory operation: {operation}",
                    error_details={
                        "reason": "unsupported_operation",
                        "supported_operations": ["store", "retrieve", "update", "delete"]
                    }
                )

            if result.get("success"):
                return NodeExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    output_data={"main": result},
                    metadata={
                        "memory_type": memory_type,
                        "operation": operation,
                        "storage": "persistent_database"
                    }
                )
            else:
                return NodeExecutionResult(
                    status=ExecutionStatus.ERROR,
                    error_message=result.get("error", "Memory operation failed"),
                    error_details={
                        "reason": "database_operation_failed",
                        "memory_type": memory_type,
                        "operation": operation
                    }
                )

        except Exception as e:
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=f"Memory execution failed: {str(e)}",
                error_details={
                    "reason": "execution_error",
                    "memory_type": memory_type,
                    "operation": operation
                }
            )
```

## 📋 **Implementation Checklist**

### Phase 1: Base Infrastructure ✅ (Completed)
- [x] Enhanced database schema with proper columns and constraints
- [x] RLS policies for multi-tenant security
- [x] Performance indexes for memory operations
- [x] Helper functions for common operations

### Phase 2: Core Memory Classes (Week 1)
- [ ] Create `PersistentMemoryBase` abstract class
- [ ] Implement `ConversationBufferMemory` → `conversation_buffers`
- [ ] Implement `VectorDatabaseMemory` → `embeddings`
- [ ] Implement `EntityMemory` → `entities` + `entity_relationships`
- [ ] Implement `WorkingMemory` → `memory_data`

### Phase 3: Advanced Memory Types (Week 2)
- [ ] Implement `ConversationSummaryMemory` → `conversation_summaries`
- [ ] Implement `DocumentStoreMemory` → `document_store`
- [ ] Implement `EpisodicMemory` → `episodic_memory`
- [ ] Implement `KnowledgeBaseMemory` → `knowledge_facts` + `knowledge_rules`
- [ ] Implement `GraphMemory` → `graph_nodes` + `graph_relationships`

### Phase 4: Integration & Testing (Week 3)
- [ ] Update `MemoryNodeExecutor` to use persistent classes
- [ ] Create comprehensive test suite for all memory types
- [ ] Performance testing vs in-memory implementation
- [ ] Migration testing with existing workflows

### Phase 5: Production Deployment (Week 4)
- [ ] Feature flag for gradual rollout
- [ ] Monitoring and alerting for memory operations
- [ ] Documentation and usage examples
- [ ] Performance optimization based on real usage

## 🚀 **Expected Benefits**

### Immediate Benefits
- **Data Persistence**: Memory survives service restarts
- **Cross-Session Sharing**: Memory shared between workflow executions
- **Multi-Tenant Security**: RLS policies ensure data isolation
- **Backup & Recovery**: Database-backed storage with automatic backups

### Performance Considerations
- **Read Operations**: 10-50ms (vs <1ms in-memory)
- **Write Operations**: 20-100ms with proper indexing
- **Vector Search**: 50-200ms with pgvector optimization
- **Entity Queries**: 10-30ms with relationship joins

### Scalability Improvements
- **Horizontal Scaling**: Database can handle multiple service instances
- **Memory Limits**: No longer constrained by service memory
- **Concurrent Access**: Proper database locking and transactions
- **Storage Capacity**: Unlimited storage vs in-memory constraints

## 🔧 **Migration Strategy**

### Backward Compatibility
1. **Feature Flag**: `USE_PERSISTENT_MEMORY=true/false`
2. **Gradual Migration**: Enable per memory type
3. **Fallback Support**: Keep in-memory as backup during transition
4. **Data Export**: Export existing in-memory data before migration

### Testing Strategy
1. **Unit Tests**: Each memory class with mocked Supabase
2. **Integration Tests**: Real database operations
3. **Performance Tests**: Compare persistent vs in-memory
4. **Load Tests**: Concurrent memory operations

This implementation plan provides a complete roadmap for migrating from in-memory to persistent database storage while maintaining performance and ensuring data integrity.
