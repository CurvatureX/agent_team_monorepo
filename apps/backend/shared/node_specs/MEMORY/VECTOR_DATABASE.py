"""
VECTOR_DATABASE Memory Node Specification

Vector database memory for semantic search and embeddings storage.
This memory node is attached to AI_AGENT nodes and provides
context retrieval based on semantic similarity.

Note: MEMORY nodes are attached to AI_AGENT nodes via attached_nodes,
not connected through input/output ports.
"""

from typing import Any, Dict, List

from ...models.node_enums import MemorySubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec


class VectorDatabaseMemorySpec(BaseNodeSpec):
    """Vector database memory specification for AI_AGENT attached memory."""

    def __init__(self):
        super().__init__(
            type=NodeType.MEMORY,
            subtype=MemorySubtype.VECTOR_DATABASE,
            name="Vector_Database_Memory",
            description="Vector database memory for semantic search and embeddings-based context retrieval",
            # Configuration parameters (simplified)
            configurations={
                "database_provider": {
                    "type": "string",
                    "default": "supabase_pgvector",
                    "description": "向量数据库提供商",
                    "required": True,
                    "options": ["supabase_pgvector", "pinecone", "weaviate", "chromadb", "qdrant"],
                },
                "database_url": {
                    "type": "string",
                    "default": "",
                    "description": "数据库连接URL",
                    "required": True,
                    "sensitive": True,
                },
                "table_name": {
                    "type": "string",
                    "default": "embeddings",
                    "description": "向量数据表名",
                    "required": True,
                },
                "embedding_model": {
                    "type": "string",
                    "default": "text-embedding-ada-002",
                    "description": "嵌入模型",
                    "required": True,
                    "options": [
                        "text-embedding-ada-002",
                        "text-embedding-3-small",
                        "text-embedding-3-large",
                        "sentence-transformers/all-MiniLM-L6-v2",
                    ],
                },
                "vector_dimension": {
                    "type": "integer",
                    "default": 1536,
                    "description": "向量维度",
                    "required": True,
                },
                "similarity_threshold": {
                    "type": "float",
                    "default": 0.7,
                    "min": 0.0,
                    "max": 1.0,
                    "description": "相似度阈值",
                    "required": False,
                },
                "max_results": {
                    "type": "integer",
                    "default": 5,
                    "min": 1,
                    "max": 50,
                    "description": "最大返回结果数",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Runtime parameters (schema-style)
            input_params={
                "operation": {
                    "type": "string",
                    "default": "search",
                    "description": "向量库操作",
                    "required": False,
                    "options": ["search", "store", "update", "delete"],
                },
                "query": {
                    "type": "string",
                    "default": "",
                    "description": "查询文本（search时）",
                    "required": False,
                    "multiline": True,
                },
                "context": {
                    "type": "object",
                    "default": {},
                    "description": "上下文元数据（可参与过滤）",
                    "required": False,
                },
                "filters": {
                    "type": "object",
                    "default": {},
                    "description": "元数据过滤条件",
                    "required": False,
                },
                "items": {
                    "type": "array",
                    "default": [],
                    "description": "待写入/更新的项（含id/content/metadata）",
                    "required": False,
                },
                "ids": {
                    "type": "array",
                    "default": [],
                    "description": "待删除或更新的项ID",
                    "required": False,
                },
            },
            output_params={
                "results": {
                    "type": "array",
                    "default": [],
                    "description": "搜索结果（文本片段或文档）",
                    "required": False,
                },
                "scores": {
                    "type": "array",
                    "default": [],
                    "description": "相似度分数",
                    "required": False,
                },
                "total_results": {
                    "type": "integer",
                    "default": 0,
                    "description": "返回结果数量",
                    "required": False,
                },
                "search_time": {
                    "type": "number",
                    "default": 0,
                    "description": "搜索耗时（秒）",
                    "required": False,
                },
                "cached": {
                    "type": "boolean",
                    "default": False,
                    "description": "是否命中缓存（如实现）",
                    "required": False,
                },
            },
            # MEMORY nodes have no ports - they are attached to AI_AGENT nodes            # Memory nodes don't have attached_nodes (only AI_AGENT has this)
            attached_nodes=None,
            # Metadata
            tags=["memory", "vector", "embeddings", "semantic-search", "attached"],
            # Examples
            examples=[
                {
                    "name": "Documentation Search Memory",
                    "description": "Search through documentation and knowledge base using semantic similarity",
                    "configurations": {
                        "database_provider": "supabase_pgvector",
                        "database_url": "postgresql://postgres:password@localhost:5432/knowledge",
                        "table_name": "documentation_embeddings",
                        "embedding_model": "text-embedding-ada-002",
                        "vector_dimension": 1536,
                        "similarity_threshold": 0.75,
                        "max_results": 3,
                    },
                    "usage_example": {
                        "attached_to": "documentation_ai_agent",
                        "query_example": {
                            "query": "How do I configure authentication in the API?",
                            "context": {"user_type": "developer", "product": "api_gateway"},
                            "operation": "search",
                        },
                        "expected_result": {
                            "results": [
                                {
                                    "content": "API authentication can be configured using JWT tokens...",
                                    "source": "api-auth-guide.md",
                                    "title": "Authentication Configuration",
                                },
                                {
                                    "content": "OAuth 2.0 integration requires setting up client credentials...",
                                    "source": "oauth-setup.md",
                                    "title": "OAuth Setup Guide",
                                },
                            ],
                            "scores": [0.85, 0.78],
                            "total_results": 2,
                            "search_time": 0.12,
                            "cached": False,
                        },
                    },
                },
                {
                    "name": "Conversation History Memory",
                    "description": "Store and retrieve relevant conversation context for AI agents",
                    "configurations": {
                        "database_provider": "chromadb",
                        "table_name": "conversation_memory",
                        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                        "vector_dimension": 384,
                        "similarity_threshold": 0.6,
                        "max_results": 10,
                        "metadata_filters": {"user_id": "{{user_id}}", "session_active": True},
                    },
                    "usage_example": {
                        "attached_to": "customer_support_ai",
                        "query_example": {
                            "query": "User is asking about their previous order",
                            "context": {"user_id": "user_12345", "current_session": "session_789"},
                            "filters": {"user_id": "user_12345", "topic": "orders"},
                            "operation": "search",
                        },
                        "expected_result": {
                            "results": [
                                {
                                    "content": "User asked about order #ORD-001 delivery status",
                                    "timestamp": "2025-01-20T10:30:00Z",
                                    "resolution": "Provided tracking number",
                                },
                                {
                                    "content": "User reported issue with order #ORD-002 missing item",
                                    "timestamp": "2025-01-18T14:15:00Z",
                                    "resolution": "Replacement sent",
                                },
                            ],
                            "scores": [0.82, 0.74],
                            "total_results": 2,
                            "search_time": 0.08,
                        },
                    },
                },
                {
                    "name": "Code Repository Memory",
                    "description": "Search through codebase for relevant code examples and documentation",
                    "configurations": {
                        "database_provider": "weaviate",
                        "database_url": "https://weaviate-instance.example.com",
                        "table_name": "code_embeddings",
                        "embedding_model": "text-embedding-3-small",
                        "vector_dimension": 1536,
                        "similarity_threshold": 0.8,
                        "max_results": 5,
                        "search_type": "mmr",
                    },
                    "usage_example": {
                        "attached_to": "code_review_ai",
                        "query_example": {
                            "query": "function for user authentication validation",
                            "context": {"language": "python", "framework": "fastapi"},
                            "filters": {"file_type": "python", "framework": "fastapi"},
                            "operation": "search",
                        },
                        "expected_result": {
                            "results": [
                                {
                                    "content": "def validate_user_token(token: str) -> Optional[User]:",
                                    "file_path": "auth/validators.py",
                                    "function_name": "validate_user_token",
                                    "context": "JWT token validation function",
                                }
                            ],
                            "scores": [0.89],
                            "total_results": 1,
                            "search_time": 0.15,
                        },
                    },
                },
            ],
        )


# Export the specification instance
VECTOR_DATABASE_MEMORY_SPEC = VectorDatabaseMemorySpec()
