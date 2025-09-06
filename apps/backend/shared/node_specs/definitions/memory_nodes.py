"""
Memory node specifications.

This module defines specifications for MEMORY_NODE subtypes that provide
various memory and storage operations for LLM context enhancement.
All memory nodes are designed to be attached to LLM nodes to provide context.
"""

from ...models.node_enums import MemorySubtype, NodeType, OpenAIModel
from ..base import (
    ConnectionType,
    DataFormat,
    InputPortSpec,
    NodeSpec,
    OutputPortSpec,
    ParameterDef,
    ParameterType,
)

# CONVERSATION BUFFER Memory Node
CONVERSATION_BUFFER_SPEC = NodeSpec(
    node_type=NodeType.MEMORY,
    subtype=MemorySubtype.CONVERSATION_BUFFER,
    description="Store and manage conversation history with configurable window size for LLM context",
    display_name="Conversation Buffer Memory",
    category="memory",
    template_id="memory_conversation_buffer",
    parameters=[
        ParameterDef(
            name="window_size",
            type=ParameterType.INTEGER,
            required=False,
            default_value=10,
            description="Number of conversation turns to keep in buffer",
        ),
        ParameterDef(
            name="window_type",
            type=ParameterType.ENUM,
            required=False,
            default_value="turns",
            enum_values=["turns", "tokens", "time"],
            description="Type of window: turns, tokens, or time-based",
        ),
        ParameterDef(
            name="storage_backend",
            type=ParameterType.ENUM,
            required=False,
            default_value="redis",
            enum_values=["redis", "memory", "postgresql"],
            description="Storage backend for conversation buffer",
        ),
        ParameterDef(
            name="ttl_seconds",
            type=ParameterType.INTEGER,
            required=False,
            default_value=3600,
            description="Time-to-live for conversation buffer in seconds",
        ),
        ParameterDef(
            name="include_system_messages",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Whether to include system messages in buffer",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=True,
            description="Conversation message to store",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"role": "string", "content": "string", "timestamp": "string", "metadata": "object"}',
                examples=[
                    '{"role": "user", "content": "Hello, how are you?", "timestamp": "2025-01-01T10:00:00Z"}',
                    '{"role": "assistant", "content": "I\'m doing well, thank you!", "metadata": {"tokens": 12}}',
                ],
            ),
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="context",
            type=ConnectionType.MAIN,
            description="Recent conversation context for LLM",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"messages": "array", "total_tokens": "number", "window_info": "object"}',
            ),
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Buffer operation error",
        ),
    ],
    examples=[
        {
            "name": "Chat History Context",
            "description": "Maintain recent chat history for conversational AI",
            "parameters": {
                "window_size": "20",
                "window_type": "turns",
                "storage_backend": "redis",
            },
        }
    ],
)

# CONVERSATION SUMMARY Memory Node
CONVERSATION_SUMMARY_SPEC = NodeSpec(
    node_type=NodeType.MEMORY,
    subtype=MemorySubtype.CONVERSATION_SUMMARY,
    description="Complete conversation memory with buffer and progressive summarization for optimal LLM context",
    display_name="Conversation Summary Memory",
    category="memory",
    template_id="memory_conversation_summary",
    parameters=[
        ParameterDef(
            name="summary_trigger",
            type=ParameterType.ENUM,
            required=False,
            default_value="message_count",
            enum_values=["message_count", "token_count", "time_interval"],
            description="When to trigger summary generation",
        ),
        ParameterDef(
            name="trigger_threshold",
            type=ParameterType.INTEGER,
            required=False,
            default_value=10,
            description="Threshold for summary trigger (messages/tokens/minutes)",
        ),
        ParameterDef(
            name="summarization_model",
            type=ParameterType.STRING,
            required=False,
            default_value=OpenAIModel.GPT_5_NANO.value,
            description="Model to use for summarization",
        ),
        ParameterDef(
            name="summary_style",
            type=ParameterType.ENUM,
            required=False,
            default_value="progressive",
            enum_values=["progressive", "hierarchical", "key_points"],
            description="Style of summary generation",
        ),
        ParameterDef(
            name="preserve_entities",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Whether to preserve important entities in summaries",
        ),
        ParameterDef(
            name="buffer_window_size",
            type=ParameterType.INTEGER,
            required=False,
            default_value=10,
            description="Number of recent messages to keep in buffer",
        ),
        ParameterDef(
            name="summary_context_weight",
            type=ParameterType.FLOAT,
            required=False,
            default_value=0.3,
            description="Weight given to summary vs buffer context (0.0-1.0)",
        ),
        ParameterDef(
            name="max_total_tokens",
            type=ParameterType.INTEGER,
            required=False,
            default_value=4000,
            description="Maximum total tokens for combined context",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=True,
            description="Conversation data to summarize",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"messages": "array", "session_metadata": "object"}',
                examples=[
                    '{"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}',
                ],
            ),
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="context",
            type=ConnectionType.MAIN,
            description="Conversation summary for LLM context",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"summary": "string", "key_points": "array", "entities": "array", "metadata": "object"}',
            ),
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Summarization error",
        ),
    ],
    examples=[
        {
            "name": "Progressive Session Summary",
            "description": "Maintain progressive summaries for long conversations",
            "parameters": {
                "summary_trigger": "message_count",
                "trigger_threshold": "15",
                "summary_style": "progressive",
            },
        }
    ],
)

# ENTITY MEMORY Node
ENTITY_MEMORY_SPEC = NodeSpec(
    node_type=NodeType.MEMORY,
    subtype=MemorySubtype.ENTITY_MEMORY,
    description="Extract, store and track entities mentioned in conversations for context enhancement",
    display_name="Entity Memory",
    category="memory",
    template_id="memory_entity",
    parameters=[
        ParameterDef(
            name="entity_types",
            type=ParameterType.JSON,
            required=False,
            default_value=["person", "organization", "location", "product", "concept"],
            description="Types of entities to extract and track",
        ),
        ParameterDef(
            name="extraction_model",
            type=ParameterType.STRING,
            required=False,
            default_value=OpenAIModel.GPT_5_NANO.value,
            description="Model to use for entity extraction",
        ),
        ParameterDef(
            name="storage_backend",
            type=ParameterType.ENUM,
            required=False,
            default_value="postgresql",
            enum_values=["postgresql", "elasticsearch", "neo4j"],
            description="Storage backend for entity data",
        ),
        ParameterDef(
            name="relationship_tracking",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Whether to track relationships between entities",
        ),
        ParameterDef(
            name="importance_scoring",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Whether to calculate entity importance scores",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=True,
            description="Text content for entity extraction",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"content": "string", "context": "object", "existing_entities": "array"}',
                examples=[
                    '{"content": "John works at OpenAI and lives in San Francisco", "context": {"session_id": "123"}}',
                ],
            ),
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="context",
            type=ConnectionType.MAIN,
            description="Entity context for LLM",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"entities": "array", "relationships": "array", "entity_summary": "string"}',
            ),
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Entity extraction error",
        ),
    ],
    examples=[
        {
            "name": "Customer Entity Tracking",
            "description": "Track customer entities and relationships in support conversations",
            "parameters": {
                "entity_types": ["person", "company", "product", "issue"],
                "relationship_tracking": "true",
            },
        }
    ],
)

# EPISODIC MEMORY Node
EPISODIC_MEMORY_SPEC = NodeSpec(
    node_type=NodeType.MEMORY,
    subtype=MemorySubtype.EPISODIC_MEMORY,
    description="Store and retrieve timestamped events and experiences for temporal context",
    display_name="Episodic Memory",
    category="memory",
    template_id="memory_episodic",
    parameters=[
        ParameterDef(
            name="storage_backend",
            type=ParameterType.ENUM,
            required=False,
            default_value="timescaledb",
            enum_values=["timescaledb", "postgresql", "elasticsearch"],
            description="Storage backend optimized for time-series data",
        ),
        ParameterDef(
            name="importance_threshold",
            type=ParameterType.FLOAT,
            required=False,
            default_value=0.5,
            description="Minimum importance score for event storage (0.0-1.0)",
        ),
        ParameterDef(
            name="retention_period",
            type=ParameterType.STRING,
            required=False,
            default_value="30 days",
            description="How long to retain episodic memories",
        ),
        ParameterDef(
            name="event_embedding",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Whether to generate embeddings for semantic event search",
        ),
        ParameterDef(
            name="temporal_context_window",
            type=ParameterType.STRING,
            required=False,
            default_value="7 days",
            description="Time window for retrieving relevant episodic context",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=True,
            description="Event data to store",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"actor": "string", "action": "string", "object": "object", "context": "object", "outcome": "object", "importance": "number"}',
                examples=[
                    '{"actor": "user", "action": "completed_task", "object": {"task": "deploy_service"}, "outcome": {"success": true}, "importance": 0.8}',
                ],
            ),
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="context",
            type=ConnectionType.MAIN,
            description="Relevant episodic memories for LLM context",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"episodes": "array", "temporal_patterns": "object", "context_summary": "string"}',
            ),
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Episodic memory error",
        ),
    ],
    examples=[
        {
            "name": "User Behavior Tracking",
            "description": "Track user actions and decisions over time",
            "parameters": {
                "importance_threshold": "0.6",
                "temporal_context_window": "14 days",
            },
        }
    ],
)

# KNOWLEDGE BASE Memory Node
KNOWLEDGE_BASE_SPEC = NodeSpec(
    node_type=NodeType.MEMORY,
    subtype=MemorySubtype.KNOWLEDGE_BASE,
    description="Store and query structured knowledge facts and rules for factual context",
    display_name="Knowledge Base Memory",
    category="memory",
    template_id="memory_knowledge_base",
    parameters=[
        ParameterDef(
            name="storage_backend",
            type=ParameterType.ENUM,
            required=False,
            default_value="neo4j",
            enum_values=["neo4j", "postgresql", "arangodb"],
            description="Storage backend for knowledge representation",
        ),
        ParameterDef(
            name="fact_extraction_model",
            type=ParameterType.STRING,
            required=False,
            default_value=OpenAIModel.GPT_5.value,
            description="Model for extracting structured facts",
        ),
        ParameterDef(
            name="confidence_threshold",
            type=ParameterType.FLOAT,
            required=False,
            default_value=0.8,
            description="Minimum confidence score for fact storage (0.0-1.0)",
        ),
        ParameterDef(
            name="fact_validation",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Whether to validate facts against existing knowledge",
        ),
        ParameterDef(
            name="rule_inference",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=False,
            description="Whether to enable rule-based inference",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=True,
            description="Content for fact extraction or knowledge query",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"content": "string", "query": "string", "fact_type": "string", "domain": "string"}',
                examples=[
                    '{"content": "The capital of France is Paris", "fact_type": "location", "domain": "geography"}',
                    '{"query": "What do we know about machine learning?", "domain": "technology"}',
                ],
            ),
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="context",
            type=ConnectionType.MAIN,
            description="Relevant knowledge facts for LLM context",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"facts": "array", "rules": "array", "inferences": "array", "knowledge_summary": "string"}',
            ),
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Knowledge base error",
        ),
    ],
    examples=[
        {
            "name": "Domain Knowledge Base",
            "description": "Maintain structured knowledge about a specific domain",
            "parameters": {
                "confidence_threshold": "0.9",
                "fact_validation": "true",
                "rule_inference": "true",
            },
        }
    ],
)

# GRAPH MEMORY Node
GRAPH_MEMORY_SPEC = NodeSpec(
    node_type=NodeType.MEMORY,
    subtype=MemorySubtype.GRAPH_MEMORY,
    description="Store and query graph-structured relationships for complex contextual understanding",
    display_name="Graph Memory",
    category="memory",
    template_id="memory_graph",
    parameters=[
        ParameterDef(
            name="graph_database",
            type=ParameterType.ENUM,
            required=False,
            default_value="neo4j",
            enum_values=["neo4j", "arangodb", "tigergraph"],
            description="Graph database backend",
        ),
        ParameterDef(
            name="relationship_types",
            type=ParameterType.JSON,
            required=False,
            default_value=["related_to", "part_of", "causes", "depends_on", "similar_to"],
            description="Types of relationships to track",
        ),
        ParameterDef(
            name="traversal_depth",
            type=ParameterType.INTEGER,
            required=False,
            default_value=2,
            description="Maximum depth for graph traversals",
        ),
        ParameterDef(
            name="node_types",
            type=ParameterType.JSON,
            required=False,
            default_value=["concept", "entity", "event", "topic"],
            description="Types of nodes to create in the graph",
        ),
        ParameterDef(
            name="weight_relationships",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Whether to assign weights to relationships",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=True,
            description="Graph elements to add or query parameters",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"nodes": "array", "relationships": "array", "query": "object", "start_node": "string"}',
                examples=[
                    '{"nodes": [{"id": "ML", "type": "concept", "properties": {"name": "Machine Learning"}}]}',
                    '{"query": {"start_node": "AI", "relationship_types": ["related_to"], "depth": 2}}',
                ],
            ),
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="context",
            type=ConnectionType.MAIN,
            description="Graph-based context for LLM",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"paths": "array", "connected_nodes": "array", "relationship_summary": "string"}',
            ),
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Graph operation error",
        ),
    ],
    examples=[
        {
            "name": "Concept Relationship Graph",
            "description": "Build and query relationships between concepts and topics",
            "parameters": {
                "relationship_types": ["related_to", "part_of", "prerequisite"],
                "traversal_depth": "3",
            },
        }
    ],
)

# WORKING MEMORY Node
WORKING_MEMORY_SPEC = NodeSpec(
    node_type=NodeType.MEMORY,
    subtype=MemorySubtype.WORKING_MEMORY,
    description="Temporary memory for active reasoning and multi-step problem solving",
    display_name="Working Memory",
    category="memory",
    template_id="memory_working",
    parameters=[
        ParameterDef(
            name="storage_backend",
            type=ParameterType.ENUM,
            required=False,
            default_value="redis",
            enum_values=["redis", "memory"],
            description="Fast storage backend for working memory",
        ),
        ParameterDef(
            name="ttl_seconds",
            type=ParameterType.INTEGER,
            required=False,
            default_value=3600,
            description="Time-to-live for working memory items",
        ),
        ParameterDef(
            name="capacity_limit",
            type=ParameterType.INTEGER,
            required=False,
            default_value=100,
            description="Maximum number of items in working memory",
        ),
        ParameterDef(
            name="eviction_policy",
            type=ParameterType.ENUM,
            required=False,
            default_value="lru",
            enum_values=["lru", "fifo", "importance"],
            description="Eviction policy when capacity limit is reached",
        ),
        ParameterDef(
            name="namespace",
            type=ParameterType.STRING,
            required=False,
            default_value="default",
            description="Namespace for isolating working memory contexts",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=True,
            description="Working memory operations and data",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"operation": "string", "key": "string", "value": "object", "importance": "number"}',
                examples=[
                    '{"operation": "store", "key": "current_analysis", "value": {"findings": ["..."]}, "importance": 0.8}',
                    '{"operation": "retrieve", "key": "previous_step"}',
                ],
            ),
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="context",
            type=ConnectionType.MAIN,
            description="Working memory context for LLM reasoning",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"current_state": "object", "recent_items": "array", "reasoning_chain": "array"}',
            ),
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Working memory error",
        ),
    ],
    examples=[
        {
            "name": "Multi-Step Reasoning",
            "description": "Maintain intermediate results during complex problem solving",
            "parameters": {
                "ttl_seconds": "1800",
                "capacity_limit": "50",
                "eviction_policy": "importance",
            },
        }
    ],
)

# KEY-VALUE STORE Memory Node
KEY_VALUE_STORE_SPEC = NodeSpec(
    node_type=NodeType.MEMORY,
    subtype=MemorySubtype.KEY_VALUE_STORE,
    description="Store and retrieve key-value data for fast LLM context access",
    display_name="Key-Value Store Memory",
    category="memory",
    template_id="memory_key_value",
    parameters=[
        ParameterDef(
            name="storage_backend",
            type=ParameterType.ENUM,
            required=False,
            default_value="redis",
            enum_values=["redis", "memcached", "dynamodb", "postgresql"],
            description="Key-value storage backend",
        ),
        ParameterDef(
            name="ttl_seconds",
            type=ParameterType.INTEGER,
            required=False,
            description="Time-to-live for stored values in seconds",
        ),
        ParameterDef(
            name="namespace",
            type=ParameterType.STRING,
            required=False,
            default_value="default",
            description="Namespace for key isolation",
        ),
        ParameterDef(
            name="serialize_json",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Whether to automatically serialize/deserialize JSON",
        ),
        ParameterDef(
            name="compression",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=False,
            description="Whether to compress stored values",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=True,
            description="Key-value operation data",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"key": "string", "value": "object", "operation": "string", "metadata": "object"}',
                examples=[
                    '{"key": "user_preferences", "value": {"theme": "dark", "language": "en"}, "operation": "set"}',
                    '{"key": "user_preferences", "operation": "get"}',
                ],
            ),
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="context",
            type=ConnectionType.MAIN,
            description="Key-value data for LLM context",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"key": "string", "value": "object", "found": "boolean", "metadata": "object"}',
            ),
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Key-value operation error",
        ),
    ],
    examples=[
        {
            "name": "User Context Storage",
            "description": "Store and retrieve user preferences and context",
            "parameters": {
                "storage_backend": "redis",
                "namespace": "user_context",
                "ttl_seconds": "86400",
            },
        }
    ],
)

# DOCUMENT STORE Memory Node
DOCUMENT_STORE_SPEC = NodeSpec(
    node_type=NodeType.MEMORY,
    subtype=MemorySubtype.DOCUMENT_STORE,
    description="Store and search documents with full-text capabilities for LLM context",
    display_name="Document Store Memory",
    category="memory",
    template_id="memory_document_store",
    parameters=[
        ParameterDef(
            name="storage_backend",
            type=ParameterType.ENUM,
            required=False,
            default_value="elasticsearch",
            enum_values=["elasticsearch", "mongodb", "postgresql", "supabase"],
            description="Document storage backend",
        ),
        ParameterDef(
            name="collection_name",
            type=ParameterType.STRING,
            required=True,
            description="Document collection or index name",
        ),
        ParameterDef(
            name="full_text_search",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Enable full-text search capabilities",
        ),
        ParameterDef(
            name="search_fields",
            type=ParameterType.JSON,
            required=False,
            default_value=["content", "title", "description"],
            description="Fields to search in for text queries",
        ),
        ParameterDef(
            name="max_results",
            type=ParameterType.INTEGER,
            required=False,
            default_value=10,
            description="Maximum number of documents to return",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=True,
            description="Document operation data",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"operation": "string", "document_id": "string", "content": "string", "metadata": "object", "query": "string", "filters": "object"}',
                examples=[
                    '{"operation": "store", "document_id": "doc123", "content": "Document content here", "metadata": {"title": "Important Document", "category": "policy"}}',
                    '{"operation": "search", "query": "policy document", "filters": {"category": "policy"}}',
                ],
            ),
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="context",
            type=ConnectionType.MAIN,
            description="Document search results for LLM context",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"documents": "array", "total_count": "number", "relevance_scores": "array"}',
            ),
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Document operation error",
        ),
    ],
    examples=[
        {
            "name": "Knowledge Document Search",
            "description": "Search knowledge base documents for relevant context",
            "parameters": {
                "storage_backend": "elasticsearch",
                "collection_name": "knowledge_base",
                "full_text_search": "true",
                "max_results": "5",
            },
        }
    ],
)

# VECTOR DATABASE Memory Node
VECTOR_DATABASE_SPEC = NodeSpec(
    node_type=NodeType.MEMORY,
    subtype=MemorySubtype.VECTOR_DATABASE,
    description="Store and search vectors in a vector database for semantic similarity and RAG",
    display_name="Vector Database Memory",
    category="memory",
    template_id="memory_vector_database",
    parameters=[
        ParameterDef(
            name="provider",
            type=ParameterType.ENUM,
            required=False,
            default_value="supabase",
            enum_values=["supabase", "pinecone", "weaviate", "chroma", "qdrant", "elasticsearch"],
            description="Vector database provider",
        ),
        ParameterDef(
            name="collection_name",
            type=ParameterType.STRING,
            required=True,
            description="Name of the vector collection/index",
        ),
        ParameterDef(
            name="embedding_model",
            type=ParameterType.STRING,
            required=False,
            default_value="text-embedding-3-small",
            description="Embedding model for vectorization",
        ),
        ParameterDef(
            name="similarity_threshold",
            type=ParameterType.FLOAT,
            required=False,
            default_value=0.7,
            description="Minimum similarity score for search results (0.0-1.0)",
        ),
        ParameterDef(
            name="max_results",
            type=ParameterType.INTEGER,
            required=False,
            default_value=5,
            description="Maximum number of search results for context",
        ),
        ParameterDef(
            name="auto_embed",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Automatically embed text content",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=True,
            description="Vector operation data",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"text": "string", "vector": "array", "metadata": "object", "query": "string", "filters": "object"}',
                examples=[
                    '{"text": "This is important information for the knowledge base", "metadata": {"source": "manual", "importance": 0.9}}',
                    '{"query": "Find information about machine learning", "filters": {"source": "documentation"}}',
                ],
            ),
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="context",
            type=ConnectionType.MAIN,
            description="Relevant vector search results for LLM context",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"results": "array", "similarities": "array", "context_text": "string", "metadata_summary": "object"}',
            ),
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Vector operation error",
        ),
    ],
    examples=[
        {
            "name": "RAG Knowledge Retrieval",
            "description": "Retrieve relevant context from knowledge base for LLM",
            "parameters": {
                "collection_name": "knowledge_base",
                "max_results": "3",
                "similarity_threshold": "0.8",
            },
        }
    ],
)
