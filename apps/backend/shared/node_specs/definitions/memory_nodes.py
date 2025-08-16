"""
Memory node specifications.

This module defines specifications for MEMORY_NODE subtypes that provide
various memory and storage operations including vector databases, key-value storage,
and document management.
"""

from ...models.node_enums import MemorySubtype, NodeType
from ..base import (
    ConnectionType,
    DataFormat,
    InputPortSpec,
    NodeSpec,
    OutputPortSpec,
    ParameterDef,
    ParameterType,
)

# VECTOR_DB Memory Node
VECTOR_STORE_MEMORY_SPEC = NodeSpec(
    node_type=NodeType.MEMORY,
    subtype=MemorySubtype.VECTOR_DATABASE,
    description="Store and search vectors in a vector database for semantic similarity",
    display_name="Vector Database",
    category="memory",
    template_id="memory_vector",
    parameters=[
        ParameterDef(
            name="operation",
            type=ParameterType.ENUM,
            required=True,
            enum_values=["store", "search", "delete", "update"],
            description="Vector database operation to perform",
        ),
        ParameterDef(
            name="collection_name",
            type=ParameterType.STRING,
            required=True,
            description="Name of the vector collection/table",
        ),
        ParameterDef(
            name="provider",
            type=ParameterType.ENUM,
            required=False,
            default_value="supabase",
            enum_values=["supabase", "pinecone", "weaviate", "chroma", "qdrant"],
            description="Vector database provider",
        ),
        ParameterDef(
            name="embedding_model",
            type=ParameterType.STRING,
            required=False,
            default_value="text-embedding-ada-002",
            description="Embedding model to use for vectorization",
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
            default_value=10,
            description="Maximum number of search results to return",
        ),
        ParameterDef(
            name="text",
            type=ParameterType.STRING,
            required=False,
            description="Text to store or search",
        ),
        ParameterDef(
            name="metadata",
            type=ParameterType.JSON,
            required=False,
            default_value={},
            description="Metadata",
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
                    '{"text": "Store this document", "metadata": {"source": "doc1.pdf", "type": "document"}}',
                    '{"query": "Find similar documents", "filters": {"type": "document"}}',
                ],
            ),
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Vector operation result",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"results": "array", "operation": "string", "count": "number", "scores": "array"}',
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
            "name": "Document Similarity Search",
            "description": "Search for similar documents using vector embeddings",
            "parameters": {
                "operation": "search",
                "collection_name": "documents",
                "similarity_threshold": "0.8",
            },
        }
    ],
)


# KEY_VALUE Memory Node
SIMPLE_MEMORY_SPEC = NodeSpec(
    node_type=NodeType.MEMORY,
    subtype=MemorySubtype.SIMPLE_MEMORY,
    description="Store simple key-value memory",
    parameters=[
        ParameterDef(
            name="operation",
            type=ParameterType.ENUM,
            required=True,
            enum_values=["get", "set", "delete", "exists"],
            description="Key-value operation to perform",
        ),
        ParameterDef(
            name="key",
            type=ParameterType.STRING,
            required=True,
            description="Storage key",
        ),
        ParameterDef(
            name="value",
            type=ParameterType.STRING,
            required=False,
            description="Storage value (for set operation)",
        ),
        ParameterDef(
            name="provider",
            type=ParameterType.ENUM,
            required=False,
            default_value="redis",
            enum_values=["redis", "memcached", "dynamodb", "memory"],
            description="Provider",
        ),
        ParameterDef(
            name="ttl_seconds",
            type=ParameterType.INTEGER,
            required=False,
            description="Time-to-live in seconds (for set operation)",
        ),
        ParameterDef(
            name="namespace",
            type=ParameterType.STRING,
            required=False,
            description="Namespace or prefix for the key",
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
                schema='{"value": "object", "key": "string", "metadata": "object"}',
                examples=[
                    '{"value": {"user_id": "123", "preferences": {}}, "key": "user:123:prefs"}',
                    '{"key": "session:abc123"}',
                ],
            ),
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Key-value operation result",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"value": "object", "key": "string", "exists": "boolean", "operation": "string", "ttl": "number"}',
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
            "name": "User Session Storage",
            "description": "Store user session data with expiration",
            "parameters": {
                "operation": "set",
                "key": "session:{{session_id}}",
                "ttl_seconds": "3600",
            },
        }
    ],
)


# DOCUMENT Memory Node
DOCUMENT_MEMORY_SPEC = NodeSpec(
    node_type=NodeType.MEMORY,
    subtype=MemorySubtype.DOCUMENT_STORE,
    description="Store, retrieve, and manage documents with full-text search capabilities",
    parameters=[
        ParameterDef(
            name="operation",
            type=ParameterType.ENUM,
            required=True,
            enum_values=["store", "retrieve", "update", "delete", "search"],
            description="Document operation to perform",
        ),
        ParameterDef(
            name="document_id",
            type=ParameterType.STRING,
            required=True,
            description="Unique identifier for the document",
        ),
        ParameterDef(
            name="provider",
            type=ParameterType.ENUM,
            required=False,
            default_value="elasticsearch",
            enum_values=["elasticsearch", "mongodb", "postgresql", "supabase"],
            description="Document storage provider",
        ),
        ParameterDef(
            name="collection",
            type=ParameterType.STRING,
            required=False,
            default_value="documents",
            description="Document collection or table name",
        ),
        ParameterDef(
            name="index_content",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Whether to index document content for search",
        ),
        ParameterDef(
            name="search_fields",
            type=ParameterType.JSON,
            required=False,
            description="Fields to search in (for search operation)",
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
                schema='{"content": "string", "metadata": "object", "query": "string", "filters": "object"}',
                examples=[
                    '{"content": "Document text content", "metadata": {"title": "Report", "author": "John"}}',
                    '{"query": "quarterly report", "filters": {"author": "John", "year": 2025}}',
                ],
            ),
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Document operation result",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"documents": "array", "document": "object", "count": "number", "operation": "string"}',
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
            "name": "Knowledge Base Search",
            "description": "Search documents in a knowledge base",
            "parameters": {
                "operation": "search",
                "collection": "knowledge_base",
                "search_fields": ["title", "content", "tags"],
            },
        },
        {
            "name": "Document Archive",
            "description": "Store documents with metadata for archival",
            "parameters": {
                "operation": "store",
                "document_id": "{{workflow.execution_id}}-{{timestamp}}",
                "index_content": "true",
            },
        },
    ],
)


# VECTOR DATABASE Memory Node
VECTOR_DATABASE_MEMORY_SPEC = NodeSpec(
    node_type=NodeType.MEMORY,
    subtype=MemorySubtype.VECTOR_DATABASE,
    description="Embed content into vector space for AI tasks",
    parameters=[
        ParameterDef(
            name="operation",
            type=ParameterType.ENUM,
            required=True,
            enum_values=["embed", "compare", "find_similar"],
            description="Embedding operation to perform",
        ),
        ParameterDef(
            name="embedding_model",
            type=ParameterType.STRING,
            required=False,
            default_value="text-embedding-ada-002",
            description="Embedding model to use",
        ),
        ParameterDef(
            name="similarity_metric",
            type=ParameterType.ENUM,
            required=False,
            default_value="cosine",
            enum_values=["cosine", "euclidean", "dot_product"],
            description="Similarity metric for comparisons",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=True,
            description="Content to embed or compare",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"text": "string", "embeddings": "array", "compare_with": "array"}',
                examples=[
                    '{"text": "Content to embed"}',
                    '{"embeddings": [0.1, 0.2, 0.3], "compare_with": [0.2, 0.3, 0.4]}',
                ],
            ),
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Embedding operation result",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"embeddings": "array", "similarity": "number", "similar_items": "array"}',
            ),
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Embedding operation error",
        ),
    ],
)

# Store Memory - Simple workflow memory storage
STORE_MEMORY_SPEC = NodeSpec(
    node_type=NodeType.MEMORY,
    subtype="STORE",  # Using string since we need separate subtype
    description="Store data in workflow memory",
    display_name="Store Memory",
    category="memory",
    template_id="memory_store",
    parameters=[
        ParameterDef(
            name="key",
            type=ParameterType.STRING,
            required=True,
            description="Memory key to store data under",
        ),
        ParameterDef(
            name="value",
            type=ParameterType.STRING,
            required=False,
            description="Value to store (if not provided, input data will be stored)",
        ),
        ParameterDef(
            name="ttl_minutes",
            type=ParameterType.INTEGER,
            required=False,
            default_value=60,
            description="Time to live in minutes",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=False,
            description="Data to store in memory",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"data": "object", "metadata": "object"}',
            ),
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Storage confirmation",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"stored": "boolean", "key": "string", "timestamp": "string"}',
            ),
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Storage error",
        ),
    ],
)

# Retrieve Memory - Simple workflow memory retrieval
RETRIEVE_MEMORY_SPEC = NodeSpec(
    node_type=NodeType.MEMORY,
    subtype="RETRIEVE",  # Using string since we need separate subtype
    description="Retrieve data from workflow memory",
    display_name="Retrieve Memory",
    category="memory",
    template_id="memory_retrieve",
    parameters=[
        ParameterDef(
            name="key",
            type=ParameterType.STRING,
            required=True,
            description="Memory key to retrieve data from",
        ),
        ParameterDef(
            name="default_value",
            type=ParameterType.STRING,
            required=False,
            description="Default value if key doesn't exist",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=False,
            description="Optional context for retrieval",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"context": "object", "filters": "object"}',
            ),
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Retrieved data",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"data": "object", "key": "string", "found": "boolean", "timestamp": "string"}',
            ),
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Retrieval error",
        ),
    ],
)
