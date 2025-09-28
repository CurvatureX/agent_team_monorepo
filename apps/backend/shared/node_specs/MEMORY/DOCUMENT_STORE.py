"""
DOCUMENT_STORE Memory Node Specification

Document store memory for storing and searching documents with full-text
search capabilities for LLM context enhancement.

Note: MEMORY nodes are attached to AI_AGENT nodes via attached_nodes,
not connected through input/output ports.
"""

from typing import Any, Dict, List

from ...models.node_enums import MemorySubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec, create_port


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
                "storage_backend": {
                    "type": "string",
                    "default": "elasticsearch",
                    "description": "Document storage backend for full-text search",
                    "required": False,
                    "options": ["elasticsearch", "mongodb", "postgresql", "supabase"],
                },
                "collection_name": {
                    "type": "string",
                    "default": "documents",
                    "description": "Document collection or index name",
                    "required": True,
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
                    "default": ["txt", "md", "pdf", "docx", "html"],
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
            # Default runtime parameters
            default_input_params={
                "operation": "search",
                "document_id": "",
                "content": "",
                "metadata": {},
                "query": "",
                "filters": {},
                "file_path": "",
                "file_type": "",
            },
            default_output_params={
                "documents": [],
                "total_count": 0,
                "relevance_scores": [],
                "search_metadata": {},
                "document_summaries": [],
                "filtered_results": [],
                "execution_time_ms": 0,
            },
            # Port definitions - Memory nodes don't use traditional ports
            input_ports=[],
            output_ports=[],
            # Metadata
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
