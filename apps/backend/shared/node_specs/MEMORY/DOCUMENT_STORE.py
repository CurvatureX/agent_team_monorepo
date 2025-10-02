"""
DOCUMENT_STORE Memory Node Specification

Document store memory for storing and searching documents with full-text
search capabilities for LLM context enhancement.

Note: MEMORY nodes are attached to AI_AGENT nodes via attached_nodes,
not connected through input/output ports.
"""

from typing import Any, Dict, List

from ...models.node_enums import MemorySubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec


class DocumentStoreMemorySpec(BaseNodeSpec):
    """Document store memory specification for AI_AGENT attached memory."""

    def __init__(self):
        super().__init__(
            type=NodeType.MEMORY,
            subtype=MemorySubtype.DOCUMENT_STORE,
            name="Document_Store_Memory",
            description="Store and search documents with full-text capabilities for LLM context retrieval",
            # Configuration parameters
            configurations={
                "collection_name": {
                    "type": "string",
                    "default": "documents",
                    "description": "Document collection or index name",
                    "required": True,
                },
                "auto_capture_from_ai": {
                    "type": "boolean",
                    "default": True,
                    "description": "当作为AI_AGENT的附加内存时，自动将AI输出写入文档存储（使用title/content输入或自动生成标题）",
                    "required": False,
                },
                "title_auto": {
                    "type": "boolean",
                    "default": True,
                    "description": "若未提供title，则从content自动生成标题（取第一行/句并截断）",
                    "required": False,
                },
                "title_max_length": {
                    "type": "integer",
                    "default": 80,
                    "description": "自动标题的最大长度",
                    "required": False,
                },
                "full_text_search": {
                    "type": "boolean",
                    "default": True,
                    "description": "Enable full-text search capabilities",
                    "required": False,
                },
                "search_fields": {
                    "type": "array",
                    "default": ["content", "title", "description"],
                    "description": "Fields to search in for text queries",
                    "required": False,
                },
                "max_results": {
                    "type": "integer",
                    "default": 10,
                    "description": "Maximum number of documents to return",
                    "required": False,
                },
                "indexing_strategy": {
                    "type": "string",
                    "default": "automatic",
                    "description": "How to index documents for search",
                    "required": False,
                    "options": ["automatic", "manual", "hybrid"],
                },
                "content_extraction": {
                    "type": "boolean",
                    "default": True,
                    "description": "Extract text content from various file formats",
                    "required": False,
                },
                "supported_formats": {
                    "type": "array",
                    "default": ["txt", "md"],
                    "description": "Document formats to support",
                    "required": False,
                },
                "relevance_scoring": {
                    "type": "string",
                    "default": "tf_idf",
                    "description": "Method for calculating document relevance",
                    "required": False,
                    "options": ["tf_idf", "bm25", "hybrid"],
                },
                "metadata_indexing": {
                    "type": "boolean",
                    "default": True,
                    "description": "Index document metadata for filtering",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Schema-style runtime parameters
            input_params={
                "operation": {
                    "type": "string",
                    "default": "search",
                    "description": "文档操作类型",
                    "required": False,
                    "options": ["store", "search", "update", "delete"],
                },
                "document_id": {
                    "type": "string",
                    "default": "",
                    "description": "文档ID（可选，未提供时由系统生成）",
                    "required": False,
                },
                "title": {
                    "type": "string",
                    "default": "",
                    "description": "文档标题（可选，如启用自动标题则可不填）",
                    "required": False,
                },
                "content": {
                    "type": "string",
                    "default": "",
                    "description": "文档正文内容（由AI节点输出自动填充）",
                    "required": False,
                    "multiline": True,
                },
                "tags": {
                    "type": "array",
                    "default": [],
                    "description": "文档标签",
                    "required": False,
                },
                "metadata": {
                    "type": "object",
                    "default": {},
                    "description": "文档元数据（如作者、来源、业务字段等）",
                    "required": False,
                },
                "query": {
                    "type": "string",
                    "default": "",
                    "description": "搜索查询字符串",
                    "required": False,
                },
                "filters": {
                    "type": "object",
                    "default": {},
                    "description": "搜索过滤条件",
                    "required": False,
                },
                "file_path": {
                    "type": "string",
                    "default": "",
                    "description": "原始文件路径（可选）",
                    "required": False,
                },
                "file_type": {
                    "type": "string",
                    "default": "",
                    "description": "原始文件类型（可选）",
                    "required": False,
                },
                "source_node": {
                    "type": "string",
                    "default": "",
                    "description": "来源AI节点ID或名称（可选）",
                    "required": False,
                },
                "created_at": {
                    "type": "string",
                    "default": "",
                    "description": "文档创建时间（ISO 8601，可选）",
                    "required": False,
                },
            },
            output_params={
                "documents": {
                    "type": "array",
                    "default": [],
                    "description": "文档结果集（搜索或存储后的返回）",
                    "required": False,
                },
                "total_count": {
                    "type": "integer",
                    "default": 0,
                    "description": "匹配或影响的文档数量",
                    "required": False,
                },
                "relevance_scores": {
                    "type": "array",
                    "default": [],
                    "description": "相关性分数（仅搜索）",
                    "required": False,
                },
                "search_metadata": {
                    "type": "object",
                    "default": {},
                    "description": "搜索或索引的元数据（耗时、算法、过滤等）",
                    "required": False,
                },
                "document_summaries": {
                    "type": "array",
                    "default": [],
                    "description": "文档摘要或分段概述（可选）",
                    "required": False,
                },
                "filtered_results": {
                    "type": "array",
                    "default": [],
                    "description": "根据过滤条件返回的结果（可选）",
                    "required": False,
                },
                "execution_time_ms": {
                    "type": "integer",
                    "default": 0,
                    "description": "操作耗时（毫秒）",
                    "required": False,
                },
            },
            # Port definitions - Memory nodes don't use traditional ports            # Metadata
            tags=["memory", "documents", "search", "full-text", "indexing", "knowledge-base"],
            # Examples
            examples=[
                {
                    "name": "Knowledge Document Search",
                    "description": "Search knowledge base documents for relevant context with full-text search",
                    "configurations": {
                        "storage_backend": "elasticsearch",
                        "collection_name": "knowledge_base",
                        "full_text_search": True,
                        "search_fields": ["content", "title", "summary"],
                        "max_results": 5,
                        "relevance_scoring": "bm25",
                        "metadata_indexing": True,
                    },
                    "input_example": {
                        "operation": "search",
                        "query": "machine learning best practices",
                        "filters": {
                            "category": "ai_ml",
                            "last_updated": {"gte": "2024-01-01"},
                            "author": "data_science_team",
                        },
                        "metadata": {
                            "search_context": "technical_consultation",
                            "user_expertise": "intermediate",
                        },
                    },
                    "expected_outputs": {
                        "documents": [
                            {
                                "document_id": "ml_practices_2024",
                                "title": "Machine Learning Best Practices Guide",
                                "content": "This comprehensive guide covers essential best practices for machine learning projects including data preprocessing, model selection, validation strategies, and deployment considerations...",
                                "metadata": {
                                    "category": "ai_ml",
                                    "author": "data_science_team",
                                    "last_updated": "2024-06-15",
                                    "tags": ["machine-learning", "best-practices", "deployment"],
                                },
                                "relevance_score": 0.95,
                            },
                            {
                                "document_id": "ml_model_validation",
                                "title": "Model Validation Techniques in ML",
                                "content": "Understanding different validation techniques is crucial for building robust machine learning models. This document covers cross-validation, holdout validation, and advanced techniques...",
                                "metadata": {
                                    "category": "ai_ml",
                                    "author": "data_science_team",
                                    "last_updated": "2024-03-20",
                                    "tags": ["validation", "model-evaluation", "statistics"],
                                },
                                "relevance_score": 0.87,
                            },
                        ],
                        "total_count": 2,
                        "relevance_scores": [0.95, 0.87],
                        "search_metadata": {
                            "query": "machine learning best practices",
                            "search_algorithm": "bm25",
                            "total_documents_searched": 1847,
                            "search_time_ms": 45,
                            "filters_applied": ["category", "last_updated", "author"],
                        },
                        "document_summaries": [
                            "Comprehensive guide covering ML project best practices including data preprocessing and deployment",
                            "Technical guide focusing on validation techniques for building robust ML models",
                        ],
                    },
                },
                {
                    "name": "Auto Capture AI Output",
                    "description": "AI_AGENT附加此内存节点后，自动将AI输出的title/content写入文档存储",
                    "configurations": {
                        "storage_backend": "supabase",
                        "collection_name": "ai_outputs",
                        "auto_capture_from_ai": True,
                        "title_auto": True,
                        "title_max_length": 80,
                    },
                    "input_example": {
                        "operation": "store",
                        "title": "Weekly Status Summary",
                        "content": "This week we completed the authentication revamp, fixed three critical bugs, and improved test coverage to 85%...",
                        "tags": ["status", "weekly"],
                        "metadata": {"author": "ai_agent", "project": "platform"},
                        "source_node": "OpenAI_ChatGPT",
                        "created_at": "2025-01-28T12:00:00Z",
                    },
                    "expected_outputs": {
                        "documents": [
                            {
                                "document_id": "auto_gen_12345",
                                "title": "Weekly Status Summary",
                                "stored": True,
                                "collection": "ai_outputs",
                            }
                        ],
                        "total_count": 1,
                        "search_metadata": {"indexing_time_ms": 25},
                    },
                },
                {
                    "name": "Policy Document Storage",
                    "description": "Store and organize company policy documents with automatic indexing",
                    "configurations": {
                        "storage_backend": "postgresql",
                        "collection_name": "company_policies",
                        "indexing_strategy": "automatic",
                        "content_extraction": True,
                        "supported_formats": ["pdf", "docx", "html", "md"],
                        "metadata_indexing": True,
                        "max_results": 15,
                    },
                    "input_example": {
                        "operation": "store",
                        "document_id": "hr_policy_2025",
                        "content": "Human Resources Policy Manual 2025\n\nThis manual outlines all HR policies including hiring procedures, employee benefits, performance evaluation processes, and workplace conduct guidelines...",
                        "metadata": {
                            "title": "HR Policy Manual 2025",
                            "category": "human_resources",
                            "department": "HR",
                            "effective_date": "2025-01-01",
                            "version": "v2.1",
                            "approval_status": "approved",
                            "tags": ["hr", "policies", "employee-handbook"],
                        },
                        "file_path": "/documents/policies/hr_policy_2025.pdf",
                        "file_type": "pdf",
                    },
                    "expected_outputs": {
                        "documents": [
                            {
                                "document_id": "hr_policy_2025",
                                "storage_status": "success",
                                "indexed_content_length": 15420,
                                "extracted_sections": [
                                    "hiring_procedures",
                                    "employee_benefits",
                                    "performance_evaluation",
                                    "workplace_conduct",
                                ],
                                "metadata_fields_indexed": 7,
                            }
                        ],
                        "search_metadata": {
                            "indexing_time_ms": 234,
                            "content_extraction_success": True,
                            "searchable_fields_created": ["content", "title", "category"],
                            "full_text_index_updated": True,
                        },
                    },
                },
                {
                    "name": "Technical Documentation Retrieval",
                    "description": "Retrieve relevant technical documentation for development context",
                    "configurations": {
                        "storage_backend": "elasticsearch",
                        "collection_name": "tech_docs",
                        "full_text_search": True,
                        "search_fields": ["content", "title", "code_snippets", "api_reference"],
                        "relevance_scoring": "hybrid",
                        "max_results": 8,
                        "content_extraction": True,
                    },
                    "input_example": {
                        "operation": "search",
                        "query": "REST API authentication JWT implementation",
                        "filters": {
                            "document_type": "api_documentation",
                            "programming_language": ["javascript", "typescript"],
                            "last_updated": {"gte": "2024-01-01"},
                        },
                        "metadata": {
                            "search_intent": "implementation_guidance",
                            "developer_level": "intermediate",
                        },
                    },
                    "expected_outputs": {
                        "documents": [
                            {
                                "document_id": "jwt_auth_guide",
                                "title": "JWT Authentication Implementation Guide",
                                "content": "# JWT Authentication for REST APIs\n\nThis guide demonstrates how to implement JWT authentication in Node.js applications...",
                                "code_snippets": [
                                    "const jwt = require('jsonwebtoken');",
                                    "const token = jwt.sign(payload, secret, { expiresIn: '1h' });",
                                ],
                                "metadata": {
                                    "document_type": "api_documentation",
                                    "programming_language": ["javascript", "typescript"],
                                    "difficulty": "intermediate",
                                    "last_updated": "2024-08-15",
                                },
                                "relevance_score": 0.92,
                            }
                        ],
                        "total_count": 1,
                        "document_summaries": [
                            "Comprehensive guide for implementing JWT authentication in Node.js REST APIs with code examples"
                        ],
                        "search_metadata": {
                            "hybrid_scoring_components": {
                                "text_relevance": 0.88,
                                "code_relevance": 0.96,
                                "metadata_boost": 0.05,
                            },
                            "programming_context_matched": True,
                        },
                    },
                },
            ],
        )


# Export the specification instance
DOCUMENT_STORE_MEMORY_SPEC = DocumentStoreMemorySpec()
