"""
Memory Node Executor.

Handles memory operations like vector database, key-value storage, document storage, etc.
"""

import hashlib
import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from shared.models import NodeType
from shared.models.node_enums import MemorySubtype
from shared.node_specs import node_spec_registry
from shared.node_specs.base import NodeSpec

from .base import BaseNodeExecutor, ExecutionStatus, NodeExecutionContext, NodeExecutionResult

try:
    from supabase import Client, create_client
except ImportError:
    Client = None


class MemoryNodeExecutor(BaseNodeExecutor):
    """Executor for MEMORY_NODE type."""

    def __init__(self, subtype: Optional[str] = None):
        super().__init__(subtype=subtype)
        # Mock memory storage (for backwards compatibility)
        self._vector_db = {}
        self._key_value_store = {}
        self._document_store = {}

        # Supabase client for persistent memory storage
        self._supabase_client: Optional[Client] = None

    def _get_node_spec(self) -> Optional[NodeSpec]:
        """Get the node specification for memory nodes."""
        if node_spec_registry and self._subtype:
            # Return the specific spec for current subtype
            return node_spec_registry.get_spec(NodeType.MEMORY.value, self._subtype)
        return None

    def get_supported_subtypes(self) -> List[str]:
        """Get supported memory subtypes."""
        return [subtype.value for subtype in MemorySubtype]

    def validate(self, node: Any) -> List[str]:
        """Validate memory node configuration using spec-based validation."""
        # First use the base class validation which includes spec validation
        errors = super().validate(node)

        # If spec validation passed, we're done
        if not errors and self.spec:
            return errors

        # Fallback if spec not available
        if not node.subtype:
            errors.append("Memory subtype is required")
            return errors

        if node.subtype not in self.get_supported_subtypes():
            errors.append(f"Unsupported memory subtype: {node.subtype}")

        return errors

    def _validate_legacy(self, node: Any) -> List[str]:
        """Legacy validation for backward compatibility."""
        errors = []

        if not hasattr(node, "subtype"):
            return errors

        subtype = node.subtype

        if subtype == MemorySubtype.VECTOR_DATABASE.value:
            errors.extend(
                self._validate_required_parameters(node, ["operation", "collection_name"])
            )
            if hasattr(node, "parameters"):
                operation = node.parameters.get("operation", "")
                if operation and operation not in ["store", "search", "delete", "update"]:
                    errors.append(f"Invalid vector DB operation: {operation}")

        elif subtype == MemorySubtype.KEY_VALUE_STORE.value:
            errors.extend(self._validate_required_parameters(node, ["operation", "key"]))
            if hasattr(node, "parameters"):
                operation = node.parameters.get("operation", "")
                if operation and operation not in ["get", "set", "delete", "exists"]:
                    errors.append(f"Invalid key-value operation: {operation}")

        elif subtype == MemorySubtype.DOCUMENT_STORE.value:
            errors.extend(self._validate_required_parameters(node, ["operation", "document_id"]))
            if hasattr(node, "parameters"):
                operation = node.parameters.get("operation", "")
                if operation and operation not in [
                    "store",
                    "retrieve",
                    "update",
                    "delete",
                    "search",
                ]:
                    errors.append(f"Invalid document operation: {operation}")

        return errors

    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute memory node."""
        start_time = time.time()
        logs = []

        try:
            subtype = context.node.subtype

            # Log detailed context information
            self.logger.info(f"🧠🔥 MEMORY NODE EXECUTE: Starting with subtype: {subtype}")
            self.logger.info(
                f"🧠🔥 MEMORY NODE EXECUTE: Workflow ID: {getattr(context, 'workflow_id', 'NONE')}"
            )
            self.logger.info(
                f"🧠🔥 MEMORY NODE EXECUTE: Execution ID: {getattr(context, 'execution_id', 'NONE')}"
            )
            self.logger.info(
                f"🧠🔥 MEMORY NODE EXECUTE: Node ID: {getattr(context.node, 'id', 'NONE') if hasattr(context, 'node') else 'NO_NODE'}"
            )
            self.logger.info(
                f"🧠🔥 MEMORY NODE EXECUTE: Input data keys: {list(context.input_data.keys()) if hasattr(context, 'input_data') and context.input_data else 'NO_INPUT'}"
            )

            if subtype == MemorySubtype.CONVERSATION_BUFFER.value:
                return self._execute_conversation_buffer(context, logs, start_time)
            elif subtype == MemorySubtype.CONVERSATION_SUMMARY.value:
                return self._execute_conversation_summary(context, logs, start_time)
            elif subtype == MemorySubtype.VECTOR_DATABASE.value:
                return self._execute_vector_db(context, logs, start_time)
            elif subtype == MemorySubtype.DOCUMENT_STORE.value:
                return self._execute_document(context, logs, start_time)
            elif subtype == MemorySubtype.KEY_VALUE_STORE.value:
                return self._execute_key_value(context, logs, start_time)
            elif subtype == MemorySubtype.ENTITY_MEMORY.value:
                return self._execute_entity_memory(context, logs, start_time)
            elif subtype == MemorySubtype.EPISODIC_MEMORY.value:
                return self._execute_episodic_memory(context, logs, start_time)
            elif subtype == MemorySubtype.KNOWLEDGE_BASE.value:
                return self._execute_knowledge_base(context, logs, start_time)
            elif subtype == MemorySubtype.GRAPH_MEMORY.value:
                return self._execute_graph_memory(context, logs, start_time)
            elif subtype == MemorySubtype.WORKING_MEMORY.value:
                return self._execute_working_memory(context, logs, start_time)
            else:
                return self._create_error_result(
                    f"Unsupported memory subtype: {subtype}",
                    execution_time=time.time() - start_time,
                    logs=logs,
                )

        except Exception as e:
            return self._create_error_result(
                f"Error executing memory: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs,
            )

    def _execute_vector_db(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute vector database operations with real OpenAI embeddings."""
        logs.append(f"Starting vector database operation")

        # Use spec-based parameter retrieval
        try:
            operation = self.get_parameter_with_spec(context, "operation")
        except (KeyError, AttributeError):
            operation = "search"

        try:
            collection_name = self.get_parameter_with_spec(context, "collection_name")
        except (KeyError, AttributeError):
            collection_name = "default"

        logs.append(f"Vector DB operation: {operation} on collection '{collection_name}'")
        self.logger.info(
            f"🧠 MEMORY NODE: Vector DB operation '{operation}' on collection '{collection_name}'"
        )

        try:
            if operation == "store":
                # Enhanced store operation with text embedding
                text_content = context.input_data.get("text", "")
                metadata = context.input_data.get("metadata", {})

                if not text_content:
                    # Try alternative content keys
                    text_content = context.input_data.get("content", "") or context.input_data.get(
                        "query", ""
                    )

                if not text_content:
                    logs.append("Error: No text content provided for vector storage")
                    raise ValueError("No text content provided for vector storage")

                logs.append(f"Storing vector: {len(text_content)} characters")
                self.logger.info(
                    f"🧠 MEMORY NODE: Embedding text content: '{text_content[:100]}...' ({len(text_content)} chars)"
                )
                result = self._store_vector_with_embedding(
                    collection_name, text_content, metadata, logs
                )

            elif operation == "search":
                # Enhanced search operation with query embedding and similarity
                query_text = (
                    context.input_data.get("query", "")
                    or context.input_data.get("text", "")
                    or context.input_data.get("content", "")
                )
                top_k = context.input_data.get("top_k", 5)
                similarity_threshold = context.input_data.get("similarity_threshold", 0.7)

                if not query_text:
                    raise ValueError("No query text provided for vector search")

                self.logger.info(
                    f"🧠 MEMORY NODE: Searching for: '{query_text[:100]}...' (top_k={top_k}, threshold={similarity_threshold})"
                )
                result = self._search_vectors_with_embedding(
                    collection_name, query_text, top_k, similarity_threshold, logs
                )

            elif operation == "delete":
                vector_id = context.input_data.get("vector_id", "")
                if not vector_id:
                    raise ValueError("No vector_id provided for deletion")
                result = self._delete_vector(collection_name, vector_id, logs)

            elif operation == "list":
                # New operation: list all vectors in collection
                result = self._list_vectors(collection_name, logs)

            else:
                result = {"error": f"Unknown vector operation: {operation}"}

            # Enhanced output data with memory context for LLM
            output_data = {
                "memory_type": MemorySubtype.VECTOR_DATABASE.value,
                "operation": operation,
                "collection_name": collection_name,
                "result": result,
                "success": "error" not in result,
                "executed_at": datetime.now().isoformat(),
            }

            # If search operation, format results for LLM consumption
            if operation == "search" and "results" in result:
                memory_context = self._format_vector_search_context(result["results"], logs)
                output_data["memory_context"] = memory_context
                output_data["formatted_context"] = memory_context

                self.logger.info(
                    f"🧠 MEMORY NODE:   📝 Formatted context length: {len(memory_context)} characters"
                )

            return self._create_success_result(
                output_data=output_data, execution_time=time.time() - start_time, logs=logs
            )

        except Exception as e:
            return self._create_error_result(
                f"Error in vector DB operation: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs,
            )

    def _execute_key_value(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute key-value operations."""
        # Use spec-based parameter retrieval
        operation = self.get_parameter_with_spec(context, "operation")
        key = self.get_parameter_with_spec(context, "key")

        try:
            if operation == "get":
                result = self._get_key_value(key)
            elif operation == "set":
                value = self.get_parameter_with_spec(context, "value")
                ttl = self.get_parameter_with_spec(context, "ttl")
                result = self._set_key_value(key, value, ttl)
            elif operation == "delete":
                result = self._delete_key_value(key)
            elif operation == "exists":
                result = self._exists_key_value(key)
            else:
                result = {"error": f"Unknown operation: {operation}"}

            output_data = {
                "memory_type": MemorySubtype.KEY_VALUE_STORE.value,
                "operation": operation,
                "key": key,
                "result": result,
                "success": "error" not in result,
                "executed_at": datetime.now().isoformat(),
            }

            return self._create_success_result(
                output_data=output_data, execution_time=time.time() - start_time, logs=logs
            )

        except Exception as e:
            return self._create_error_result(
                f"Error in key-value operation: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs,
            )

    def _execute_document(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute document operations with full-text search and indexing."""
        logs.append("Starting document store operation")

        # Use spec-based parameter retrieval with fallbacks
        try:
            operation = self.get_parameter_with_spec(context, "operation")
        except (KeyError, AttributeError):
            operation = context.input_data.get("operation", "search")

        document_id = context.input_data.get("document_id", "")

        try:
            if operation == "store":
                # Enhanced store operation with indexing
                content = context.input_data.get("content", "") or context.input_data.get(
                    "text", ""
                )
                title = context.input_data.get("title", "")
                metadata = context.input_data.get("metadata", {})

                if not content and not title:
                    raise ValueError("No content or title provided for document storage")

                if not document_id:
                    document_id = f"doc_{len(self._document_store) + 1}"
                logs.append(f"Storing document '{document_id}' ({len(content)} chars)")
                self.logger.info(
                    f"🧠 MEMORY NODE: Storing document '{document_id}' with content length: {len(content)} chars"
                )
                result = self._store_document_with_indexing(
                    document_id, title, content, metadata, logs
                )

            elif operation == "retrieve":
                if not document_id:
                    raise ValueError("No document_id provided for retrieval")
                result = self._retrieve_document_enhanced(document_id, logs)

            elif operation == "update":
                content = context.input_data.get("content", "") or context.input_data.get(
                    "text", ""
                )
                title = context.input_data.get("title", "")
                metadata = context.input_data.get("metadata", {})

                if not document_id:
                    raise ValueError("No document_id provided for update")
                result = self._update_document_with_indexing(
                    document_id, title, content, metadata, logs
                )

            elif operation == "delete":
                if not document_id:
                    raise ValueError("No document_id provided for deletion")
                result = self._delete_document_with_indexing(document_id, logs)

            elif operation == "search":
                # Enhanced search with full-text capabilities
                query = context.input_data.get("query", "") or context.input_data.get("text", "")
                max_results = context.input_data.get("max_results", 10)
                search_type = context.input_data.get(
                    "search_type", "full_text"
                )  # full_text, title, content

                if not query:
                    raise ValueError("No query provided for document search")

                self.logger.info(
                    f"🧠 MEMORY NODE: Searching documents for: '{query[:100]}...' (type: {search_type}, max: {max_results})"
                )
                result = self._search_documents_enhanced(query, max_results, search_type, logs)

            elif operation == "list":
                # New operation: list all documents
                result = self._list_all_documents(logs)

            else:
                result = {"error": f"Unknown document operation: {operation}"}

            # Enhanced output data with memory context for LLM
            output_data = {
                "memory_type": MemorySubtype.DOCUMENT_STORE.value,
                "operation": operation,
                "document_id": document_id,
                "result": result,
                "success": "error" not in result,
                "executed_at": datetime.now().isoformat(),
            }

            # If search operation, format results for LLM consumption
            if operation == "search" and "documents" in result:
                memory_context = self._format_document_search_context(result["documents"], logs)
                output_data["memory_context"] = memory_context
                output_data["formatted_context"] = memory_context

                self.logger.info(
                    f"🧠 MEMORY NODE:   📊 {len(result['documents'])} relevant documents found"
                )

            return self._create_success_result(
                output_data=output_data, execution_time=time.time() - start_time, logs=logs
            )

        except Exception as e:
            return self._create_error_result(
                f"Error in document operation: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs,
            )

    def _store_vector(
        self, collection_name: str, vector_data: Dict[str, Any], metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Store vector in collection."""
        if collection_name not in self._vector_db:
            self._vector_db[collection_name] = []

        vector_id = f"vec_{len(self._vector_db[collection_name]) + 1}"
        vector_entry = {
            "id": vector_id,
            "vector": vector_data.get("vector", []),
            "metadata": metadata,
            "created_at": datetime.now().isoformat(),
        }

        self._vector_db[collection_name].append(vector_entry)

        return {
            "vector_id": vector_id,
            "stored": True,
            "collection_size": len(self._vector_db[collection_name]),
        }

    def _search_vectors(
        self, collection_name: str, query_vector: List[float], top_k: int
    ) -> Dict[str, Any]:
        """Search vectors in collection."""
        if collection_name not in self._vector_db:
            return {"results": [], "count": 0}

        # Mock similarity search
        results = []
        for vector_entry in self._vector_db[collection_name][:top_k]:
            similarity = self._calculate_similarity(query_vector, vector_entry["vector"])
            results.append(
                {
                    "id": vector_entry["id"],
                    "similarity": similarity,
                    "metadata": vector_entry["metadata"],
                }
            )

        return {"results": results, "count": len(results), "query_vector": query_vector}

    def _delete_vector(self, collection_name: str, vector_id: str) -> Dict[str, Any]:
        """Delete vector from collection."""
        if collection_name not in self._vector_db:
            return {"error": "Collection not found"}

        for i, vector_entry in enumerate(self._vector_db[collection_name]):
            if vector_entry["id"] == vector_id:
                del self._vector_db[collection_name][i]
                return {"deleted": True, "vector_id": vector_id}

        return {"error": "Vector not found"}

    def _update_vector(
        self,
        collection_name: str,
        vector_id: str,
        vector_data: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update vector in collection."""
        if collection_name not in self._vector_db:
            return {"error": "Collection not found"}

        for vector_entry in self._vector_db[collection_name]:
            if vector_entry["id"] == vector_id:
                vector_entry["vector"] = vector_data.get("vector", vector_entry["vector"])
                vector_entry["metadata"] = metadata
                vector_entry["updated_at"] = datetime.now().isoformat()
                return {"updated": True, "vector_id": vector_id}

        return {"error": "Vector not found"}

    # Enhanced vector methods with real OpenAI embeddings
    def _get_openai_embedding(self, text: str, logs: List[str]) -> List[float]:
        """Get OpenAI embedding for text."""
        try:
            import os

            import openai
            from openai import OpenAI

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                # Return mock embedding for testing
                return [0.1] * 1536  # OpenAI text-embedding-ada-002 dimension

            client = OpenAI(api_key=api_key)

            response = client.embeddings.create(model="text-embedding-ada-002", input=text)

            embedding = response.data[0].embedding
            return embedding

        except Exception as e:
            return [0.1] * 1536  # Fallback mock embedding

    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        try:
            import math

            if len(vec1) != len(vec2):
                return 0.0

            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            magnitude1 = math.sqrt(sum(a * a for a in vec1))
            magnitude2 = math.sqrt(sum(a * a for a in vec2))

            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0

            return dot_product / (magnitude1 * magnitude2)
        except:
            return 0.0

    def _store_vector_with_embedding(
        self, collection_name: str, text_content: str, metadata: Dict[str, Any], logs: List[str]
    ) -> Dict[str, Any]:
        """Store text content with OpenAI embedding."""
        if collection_name not in self._vector_db:
            self._vector_db[collection_name] = []

        # Generate embedding for text content
        embedding = self._get_openai_embedding(text_content, logs)

        vector_id = f"vec_{len(self._vector_db[collection_name]) + 1}"
        vector_entry = {
            "id": vector_id,
            "vector": embedding,
            "text_content": text_content,
            "metadata": metadata,
            "created_at": datetime.now().isoformat(),
        }

        self._vector_db[collection_name].append(vector_entry)

        return {
            "vector_id": vector_id,
            "stored": True,
            "collection_size": len(self._vector_db[collection_name]),
            "text_content": text_content[:100] + "..." if len(text_content) > 100 else text_content,
            "embedding_dimension": len(embedding),
        }

    def _search_vectors_with_embedding(
        self,
        collection_name: str,
        query_text: str,
        top_k: int,
        similarity_threshold: float,
        logs: List[str],
    ) -> Dict[str, Any]:
        """Search vectors using OpenAI embedding and real cosine similarity."""
        if collection_name not in self._vector_db:
            return {"results": [], "count": 0, "query": query_text}

        # Generate embedding for query
        query_embedding = self._get_openai_embedding(query_text, logs)

        # Calculate similarities with all vectors
        similarities = []
        for vector_entry in self._vector_db[collection_name]:
            similarity = self._calculate_cosine_similarity(query_embedding, vector_entry["vector"])

            if similarity >= similarity_threshold:
                similarities.append(
                    {
                        "id": vector_entry["id"],
                        "similarity": similarity,
                        "text_content": vector_entry.get("text_content", ""),
                        "metadata": vector_entry["metadata"],
                        "created_at": vector_entry.get("created_at", ""),
                    }
                )

        # Sort by similarity descending
        similarities.sort(key=lambda x: x["similarity"], reverse=True)

        # Return top_k results
        results = similarities[:top_k]

        self.logger.info(
            f"🧠 MEMORY NODE: 📊 Found {len(similarities)} results above threshold {similarity_threshold}"
        )

        if results:
            avg_similarity = sum(r["similarity"] for r in results) / len(results)

        return {
            "results": results,
            "count": len(results),
            "query": query_text,
            "similarity_threshold": similarity_threshold,
            "total_candidates": len(self._vector_db[collection_name]),
        }

    def _delete_vector(
        self, collection_name: str, vector_id: str, logs: List[str]
    ) -> Dict[str, Any]:
        """Delete vector from collection with logging."""
        if collection_name not in self._vector_db:
            return {"error": "Collection not found"}

        for i, vector_entry in enumerate(self._vector_db[collection_name]):
            if vector_entry["id"] == vector_id:
                del self._vector_db[collection_name][i]
                return {"deleted": True, "vector_id": vector_id}

        return {"error": "Vector not found"}

    def _list_vectors(self, collection_name: str, logs: List[str]) -> Dict[str, Any]:
        """List all vectors in collection."""
        if collection_name not in self._vector_db:
            return {"vectors": [], "count": 0}

        vectors = []
        for vector_entry in self._vector_db[collection_name]:
            vectors.append(
                {
                    "id": vector_entry["id"],
                    "text_content": vector_entry.get("text_content", "")[:100] + "..."
                    if len(vector_entry.get("text_content", "")) > 100
                    else vector_entry.get("text_content", ""),
                    "metadata": vector_entry["metadata"],
                    "created_at": vector_entry.get("created_at", ""),
                }
            )
        self.logger.info(
            f"🧠 MEMORY NODE: 📋 Listed {len(vectors)} vectors from collection '{collection_name}'"
        )
        return {"vectors": vectors, "count": len(vectors)}

    def _format_vector_search_context(
        self, search_results: List[Dict[str, Any]], logs: List[str]
    ) -> str:
        """Format vector search results for LLM consumption."""
        if not search_results:
            return "No relevant information found in vector database."

        context_parts = []
        for i, result in enumerate(search_results, 1):
            text_content = result.get("text_content", "")
            similarity = result.get("similarity", 0.0)
            metadata = result.get("metadata", {})

            context_part = f"[Result {i}] (similarity: {similarity:.3f})\n{text_content}"

            # Add metadata if available
            if metadata:
                metadata_str = ", ".join(f"{k}: {v}" for k, v in metadata.items() if k != "id")
                if metadata_str:
                    context_part += f"\n[Metadata: {metadata_str}]"

            context_parts.append(context_part)

        formatted_context = "\n\n".join(context_parts)

        return formatted_context

    def _get_key_value(self, key: str) -> Dict[str, Any]:
        """Get value by key."""
        if key in self._key_value_store:
            return {"value": self._key_value_store[key]["value"], "found": True}
        return {"error": "Key not found"}

    def _set_key_value(self, key: str, value: Any, ttl: Optional[int] = None) -> Dict[str, Any]:
        """Set key-value pair."""
        self._key_value_store[key] = {
            "value": value,
            "created_at": datetime.now().isoformat(),
            "ttl": ttl,
        }
        return {"set": True, "key": key}

    def _delete_key_value(self, key: str) -> Dict[str, Any]:
        """Delete key-value pair."""
        if key in self._key_value_store:
            del self._key_value_store[key]
            return {"deleted": True, "key": key}
        return {"error": "Key not found"}

    def _exists_key_value(self, key: str) -> Dict[str, Any]:
        """Check if key exists."""
        return {"exists": key in self._key_value_store}

    def _store_document(self, document_id: str, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store document."""
        self._document_store[document_id] = {
            "data": document_data,
            "created_at": datetime.now().isoformat(),
        }
        return {"stored": True, "document_id": document_id}

    def _retrieve_document(self, document_id: str) -> Dict[str, Any]:
        """Retrieve document."""
        if document_id in self._document_store:
            return {
                "data": self._document_store[document_id]["data"],
                "found": True,
                "document_id": document_id,
            }
        return {"error": "Document not found"}

    def _update_document(self, document_id: str, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update document."""
        if document_id in self._document_store:
            self._document_store[document_id]["data"] = document_data
            self._document_store[document_id]["updated_at"] = datetime.now().isoformat()
            return {"updated": True, "document_id": document_id}
        return {"error": "Document not found"}

    def _delete_document(self, document_id: str) -> Dict[str, Any]:
        """Delete document."""
        if document_id in self._document_store:
            del self._document_store[document_id]
            return {"deleted": True, "document_id": document_id}
        return {"error": "Document not found"}

    def _search_documents(self, query: str) -> Dict[str, Any]:
        """Search documents."""
        results = []
        for doc_id, doc_data in self._document_store.items():
            if query.lower() in str(doc_data["data"]).lower():
                results.append({"document_id": doc_id, "data": doc_data["data"]})

        return {"results": results, "count": len(results), "query": query}

    # Enhanced document methods with full-text search and indexing
    def _create_word_index(self, text: str) -> Dict[str, List[int]]:
        """Create word index for full-text search."""
        import re

        # Simple word tokenization and indexing
        words = re.findall(r"\b\w+\b", text.lower())
        word_index = {}

        for position, word in enumerate(words):
            if len(word) > 2:  # Skip very short words
                if word not in word_index:
                    word_index[word] = []
                word_index[word].append(position)

        return word_index

    def _calculate_text_similarity(self, query: str, text: str) -> float:
        """Calculate text similarity based on word overlap."""
        import re

        query_words = set(re.findall(r"\b\w+\b", query.lower()))
        text_words = set(re.findall(r"\b\w+\b", text.lower()))

        if not query_words or not text_words:
            return 0.0

        intersection = query_words.intersection(text_words)
        union = query_words.union(text_words)

        return len(intersection) / len(union) if union else 0.0

    def _store_document_with_indexing(
        self, document_id: str, title: str, content: str, metadata: Dict[str, Any], logs: List[str]
    ) -> Dict[str, Any]:
        """Store document with full-text indexing."""
        # Create full text for indexing
        full_text = f"{title} {content}".strip()
        word_index = self._create_word_index(full_text)

        document_entry = {
            "title": title,
            "content": content,
            "metadata": metadata,
            "word_index": word_index,
            "word_count": len(full_text.split()),
            "char_count": len(full_text),
            "created_at": datetime.now().isoformat(),
        }

        self._document_store[document_id] = document_entry

        return {
            "stored": True,
            "document_id": document_id,
            "title": title,
            "content_length": len(content),
            "indexed_words": len(word_index),
            "word_count": len(full_text.split()),
        }

    def _retrieve_document_enhanced(self, document_id: str, logs: List[str]) -> Dict[str, Any]:
        """Retrieve document with enhanced metadata."""
        if document_id not in self._document_store:
            return {"error": "Document not found"}

        doc = self._document_store[document_id]

        return {
            "document_id": document_id,
            "title": doc.get("title", ""),
            "content": doc.get("content", ""),
            "metadata": doc.get("metadata", {}),
            "word_count": doc.get("word_count", 0),
            "char_count": doc.get("char_count", 0),
            "created_at": doc.get("created_at", ""),
            "updated_at": doc.get("updated_at", ""),
            "found": True,
        }

    def _update_document_with_indexing(
        self, document_id: str, title: str, content: str, metadata: Dict[str, Any], logs: List[str]
    ) -> Dict[str, Any]:
        """Update document with re-indexing."""
        if document_id not in self._document_store:
            return {"error": "Document not found"}

        # Re-create index with new content
        full_text = f"{title} {content}".strip()
        word_index = self._create_word_index(full_text)

        # Update document
        doc = self._document_store[document_id]
        doc.update(
            {
                "title": title,
                "content": content,
                "metadata": metadata,
                "word_index": word_index,
                "word_count": len(full_text.split()),
                "char_count": len(full_text),
                "updated_at": datetime.now().isoformat(),
            }
        )

        self.logger.info(
            f"🧠 MEMORY NODE: ✅ Updated document '{document_id}' with {len(word_index)} unique words indexed"
        )

        return {
            "updated": True,
            "document_id": document_id,
            "title": title,
            "content_length": len(content),
            "indexed_words": len(word_index),
        }

    def _delete_document_with_indexing(self, document_id: str, logs: List[str]) -> Dict[str, Any]:
        """Delete document and its index."""
        if document_id not in self._document_store:
            return {"error": "Document not found"}

        del self._document_store[document_id]

        return {"deleted": True, "document_id": document_id}

    def _search_documents_enhanced(
        self, query: str, max_results: int, search_type: str, logs: List[str]
    ) -> Dict[str, Any]:
        """Enhanced document search with full-text capabilities."""
        import re

        query_words = set(re.findall(r"\b\w+\b", query.lower()))
        results = []

        self.logger.info(
            f"🧠 MEMORY NODE: Searching {len(self._document_store)} documents with query words: {list(query_words)}"
        )

        for doc_id, doc in self._document_store.items():
            score = 0.0
            matched_terms = []

            if search_type == "title" and doc.get("title"):
                score = self._calculate_text_similarity(query, doc["title"])
                search_target = doc["title"]

            elif search_type == "content" and doc.get("content"):
                score = self._calculate_text_similarity(query, doc["content"])
                search_target = doc["content"]

            else:  # full_text search (default)
                title = doc.get("title", "")
                content = doc.get("content", "")
                full_text = f"{title} {content}"

                score = self._calculate_text_similarity(query, full_text)
                search_target = full_text

                # Also check word index for exact matches
                word_index = doc.get("word_index", {})
                for query_word in query_words:
                    if query_word in word_index:
                        matched_terms.append(query_word)
                        score += 0.1  # Bonus for exact word matches

            if score > 0.0:
                # Find context snippets
                snippet = self._extract_context_snippet(search_target, query, 150)

                results.append(
                    {
                        "document_id": doc_id,
                        "title": doc.get("title", ""),
                        "content": doc.get("content", ""),
                        "snippet": snippet,
                        "score": score,
                        "matched_terms": matched_terms,
                        "metadata": doc.get("metadata", {}),
                        "created_at": doc.get("created_at", ""),
                        "word_count": doc.get("word_count", 0),
                    }
                )

        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)

        # Limit results
        results = results[:max_results]

        if results:
            avg_score = sum(r["score"] for r in results) / len(results)

        return {
            "documents": results,
            "count": len(results),
            "query": query,
            "search_type": search_type,
            "total_documents": len(self._document_store),
        }

    def _extract_context_snippet(self, text: str, query: str, max_length: int = 150) -> str:
        """Extract relevant context snippet around query terms."""
        import re

        query_words = re.findall(r"\b\w+\b", query.lower())

        # Find first occurrence of any query word
        text_lower = text.lower()
        first_match_pos = len(text)

        for word in query_words:
            pos = text_lower.find(word)
            if pos != -1 and pos < first_match_pos:
                first_match_pos = pos

        if first_match_pos == len(text):
            # No matches found, return beginning
            return text[:max_length] + "..." if len(text) > max_length else text

        # Extract context around the match
        start = max(0, first_match_pos - max_length // 2)
        end = min(len(text), start + max_length)

        snippet = text[start:end]

        # Add ellipsis if truncated
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."

        return snippet

    def _list_all_documents(self, logs: List[str]) -> Dict[str, Any]:
        """List all documents with metadata."""
        documents = []

        for doc_id, doc in self._document_store.items():
            documents.append(
                {
                    "document_id": doc_id,
                    "title": doc.get("title", ""),
                    "content_preview": doc.get("content", "")[:100] + "..."
                    if len(doc.get("content", "")) > 100
                    else doc.get("content", ""),
                    "metadata": doc.get("metadata", {}),
                    "word_count": doc.get("word_count", 0),
                    "created_at": doc.get("created_at", ""),
                    "updated_at": doc.get("updated_at", ""),
                }
            )

        # Sort by creation date (newest first)
        documents.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return {"documents": documents, "count": len(documents)}

    def _format_document_search_context(
        self, search_results: List[Dict[str, Any]], logs: List[str]
    ) -> str:
        """Format document search results for LLM consumption."""
        if not search_results:
            return "No relevant documents found in document store."

        context_parts = []
        for i, result in enumerate(search_results, 1):
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            score = result.get("score", 0.0)
            metadata = result.get("metadata", {})

            context_part = f"[Document {i}] {title} (relevance: {score:.3f})\n{snippet}"

            # Add metadata if available
            if metadata:
                metadata_str = ", ".join(f"{k}: {v}" for k, v in metadata.items())
                if metadata_str:
                    context_part += f"\n[Metadata: {metadata_str}]"

            context_parts.append(context_part)

        formatted_context = "\n\n".join(context_parts)

        return formatted_context

    def _calculate_similarity(self, vector1: List[float], vector2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not vector1 or not vector2 or len(vector1) != len(vector2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vector1, vector2))
        magnitude1 = sum(a * a for a in vector1) ** 0.5
        magnitude2 = sum(b * b for b in vector2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def _execute_buffer(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute buffer memory operations."""
        # Use spec-based parameter retrieval
        operation = self.get_parameter_with_spec(context, "operation")
        buffer_name = self.get_parameter_with_spec(context, "buffer_name")

        # Initialize buffer if not exists
        if buffer_name not in self._key_value_store:
            self._key_value_store[buffer_name] = []

        buffer = self._key_value_store[buffer_name]
        max_size = self.get_parameter_with_spec(context, "max_size")

        if operation == "append":
            item = context.input_data.get("item", {})
            buffer.append({"item": item, "timestamp": datetime.now().isoformat()})
            # Maintain max size
            if len(buffer) > max_size:
                buffer.pop(0)
            result = {"operation": "append", "buffer_size": len(buffer)}

        elif operation == "get":
            result = {"operation": "get", "items": buffer, "count": len(buffer)}

        elif operation == "get_last_n":
            n = self.get_parameter_with_spec(context, "item_count")
            items = buffer[-n:] if buffer else []
            result = {"operation": "get_last_n", "items": items, "count": len(items)}

        elif operation == "clear":
            buffer.clear()
            result = {"operation": "clear", "buffer_size": 0}

        else:
            return self._create_error_result(
                f"Invalid buffer operation: {operation}",
                execution_time=time.time() - start_time,
                logs=logs,
            )

        return self._create_success_result(
            output_data=result, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_knowledge(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute knowledge memory operations."""
        # Use spec-based parameter retrieval
        operation = self.get_parameter_with_spec(context, "operation")
        knowledge_id = self.get_parameter_with_spec(context, "knowledge_id")

        # Initialize knowledge store if not exists
        if "knowledge" not in self._document_store:
            self._document_store["knowledge"] = {}

        knowledge_store = self._document_store["knowledge"]

        if operation == "store":
            content = context.input_data.get("content", "")
            metadata = context.input_data.get("metadata", {})
            knowledge_store[knowledge_id] = {
                "content": content,
                "metadata": metadata,
                "category": self.get_parameter_with_spec(context, "category"),
                "tags": self.get_parameter_with_spec(context, "tags"),
                "created_at": datetime.now().isoformat(),
            }
            result = {"operation": "store", "knowledge_id": knowledge_id}

        elif operation == "retrieve":
            knowledge = knowledge_store.get(knowledge_id)
            result = {"operation": "retrieve", "knowledge": knowledge}

        elif operation == "search":
            query = context.input_data.get("query", "")
            results = []
            for k_id, k_data in knowledge_store.items():
                if query.lower() in k_data["content"].lower():
                    results.append({"knowledge_id": k_id, "knowledge": k_data})
            result = {"operation": "search", "results": results, "count": len(results)}

        elif operation == "delete":
            if knowledge_id in knowledge_store:
                del knowledge_store[knowledge_id]
            result = {"operation": "delete", "knowledge_id": knowledge_id}

        else:
            return self._create_error_result(
                f"Invalid knowledge operation: {operation}",
                execution_time=time.time() - start_time,
                logs=logs,
            )

        return self._create_success_result(
            output_data=result, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_embedding(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute embedding memory operations."""
        # Use spec-based parameter retrieval
        operation = self.get_parameter_with_spec(context, "operation")
        embedding_model = self.get_parameter_with_spec(context, "embedding_model")

        if operation == "embed":
            text = context.input_data.get("text", "")
            # Mock embedding generation
            mock_embedding = [hash(text + str(i)) % 1000 / 1000.0 for i in range(768)]
            result = {
                "operation": "embed",
                "text": text,
                "embeddings": mock_embedding,
                "model": embedding_model,
            }

        elif operation == "compare":
            embeddings1 = context.input_data.get("embeddings", [])
            embeddings2 = context.input_data.get("compare_with", [])
            similarity = self._calculate_similarity(embeddings1, embeddings2)
            result = {
                "operation": "compare",
                "similarity": similarity,
                "metric": self.get_parameter_with_spec(context, "similarity_metric"),
            }

        elif operation == "find_similar":
            query_embeddings = context.input_data.get("embeddings", [])
            # Mock similarity search
            similar_items = [
                {"item_id": f"item_{i}", "similarity": 0.9 - i * 0.1} for i in range(5)
            ]
            result = {
                "operation": "find_similar",
                "similar_items": similar_items,
                "count": len(similar_items),
            }

        else:
            return self._create_error_result(
                f"Invalid embedding operation: {operation}",
                execution_time=time.time() - start_time,
                logs=logs,
            )

        return self._create_success_result(
            output_data=result, execution_time=time.time() - start_time, logs=logs
        )

    def _get_supabase_client(self) -> Optional[Client]:
        """Get Supabase client for persistent storage."""
        if not self._supabase_client and Client:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SECRET_KEY")

            if supabase_url and supabase_key:
                try:
                    self._supabase_client = create_client(supabase_url, supabase_key)
                except Exception:
                    self._supabase_client = None

        return self._supabase_client

    def _save_to_database(
        self,
        workflow_id: str,
        execution_id: str,
        memory_key: str,
        memory_value: dict,
        node_id: str,
        logs: List[str],
    ) -> None:
        """Save memory data to workflow_memory table using Supabase."""
        try:
            supabase = self._get_supabase_client()
            if not supabase:
                self.logger.info(
                    "🧠 DATABASE: ⚠️ Supabase client not available, using in-memory storage only"
                )
                return

            # Check if record already exists
            existing = (
                supabase.table("workflow_memory")
                .select("id")
                .eq("workflow_id", workflow_id)
                .eq("execution_id", execution_id)
                .eq("memory_key", memory_key)
                .execute()
            )

            memory_record = {
                "workflow_id": workflow_id,
                "execution_id": execution_id,
                "memory_key": memory_key,
                "memory_value": memory_value,
                "memory_type": "conversation_buffer",
                "node_id": node_id,
            }

            if existing.data:
                # Update existing record
                result = (
                    supabase.table("workflow_memory")
                    .update(
                        {
                            "memory_value": memory_value,
                            "node_id": node_id,
                            "updated_at": datetime.now().isoformat(),
                        }
                    )
                    .eq("workflow_id", workflow_id)
                    .eq("execution_id", execution_id)
                    .eq("memory_key", memory_key)
                    .execute()
                )

            else:
                # Insert new record
                result = supabase.table("workflow_memory").insert(memory_record).execute()

        except Exception as e:
            self.logger.warning(f"🧠 DATABASE: ⚠️ Failed to save memory to database: {str(e)}")
            self.logger.error(f"Database save warning: {str(e)}")

    def _load_from_database(
        self, workflow_id: str, execution_id: str, memory_key: str, logs: List[str]
    ) -> Optional[dict]:
        """Load memory data from workflow_memory table using Supabase."""
        try:
            supabase = self._get_supabase_client()
            if not supabase:
                self.logger.warn(
                    "🧠 DATABASE: ⚠️ Supabase client not available, using in-memory storage only"
                )
                return None

            result = (
                supabase.table("workflow_memory")
                .select("memory_value")
                .eq("workflow_id", workflow_id)
                .eq("execution_id", execution_id)
                .eq("memory_key", memory_key)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )

            if result.data:
                memory_data = result.data[0]["memory_value"]
                self.logger.warn(
                    f"🧠 DATABASE: Found {len(memory_data.get('messages', []))} stored messages"
                )
                return memory_data
            else:
                return None

        except Exception as e:
            return None

    def _load_conversation_history_from_workflow(
        self, workflow_id: str, logs: List[str]
    ) -> List[dict]:
        """Load conversation history across all executions for this workflow using Supabase."""
        try:
            supabase = self._get_supabase_client()
            if not supabase:
                self.logger.warn(
                    "🧠 DATABASE: ⚠️ Supabase client not available, using in-memory storage only"
                )
                return []

            result = (
                supabase.table("workflow_memory")
                .select("memory_value, created_at")
                .eq("workflow_id", workflow_id)
                .eq("memory_type", "conversation_buffer")
                .order("created_at", desc=True)
                .limit(100)
                .execute()
            )

            all_messages = []
            for record in result.data:
                memory_data = record["memory_value"]
                messages = memory_data.get("messages", [])
                # Filter out empty messages when loading from database
                valid_messages = [
                    msg
                    for msg in messages
                    if isinstance(msg, dict)
                    and msg.get("content", "")
                    and len(msg.get("content", "").strip()) > 0
                ]
                all_messages.extend(valid_messages)

            # Sort by timestamp and limit to recent messages
            all_messages.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            recent_messages = all_messages[:20]  # Last 20 messages across all executions
            self.logger.info(
                f"🧠 DATABASE: Loaded {len(recent_messages)} messages from conversation history"
            )
            return recent_messages

        except Exception as e:
            return []

    def _execute_conversation_buffer(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute conversation buffer memory operations."""
        logs.append("Starting conversation buffer memory operation")
        self.logger.info("🧠🔥 MEMORY NODE: Starting CONVERSATION_BUFFER execution")
        self.logger.info(
            f"🧠🔥 MEMORY NODE: Execution ID: {getattr(context, 'execution_id', 'unknown')}"
        )
        self.logger.info(
            f"🧠🔥 MEMORY NODE: Node ID: {getattr(context.node, 'id', 'unknown') if hasattr(context, 'node') else 'unknown'}"
        )

        # Get parameters from the node specification
        try:
            window_size = self.get_parameter_with_spec(context, "window_size")
        except (KeyError, AttributeError):
            window_size = 10

        try:
            window_type = self.get_parameter_with_spec(context, "window_type")
        except (KeyError, AttributeError):
            window_type = "turns"

        try:
            storage_backend = self.get_parameter_with_spec(context, "storage_backend")
        except (KeyError, AttributeError):
            storage_backend = "redis"

        try:
            include_system_messages = self.get_parameter_with_spec(
                context, "include_system_messages"
            )
        except (KeyError, AttributeError):
            include_system_messages = True

        logs.append(
            f"Memory configuration: window_size={window_size}, window_type={window_type}, backend={storage_backend}"
        )
        self.logger.info(
            f"🧠 MEMORY NODE: Configuration - window_size: {window_size}, window_type: {window_type}, backend: {storage_backend}"
        )

        # Get workflow and node information for database operations
        workflow_id = context.workflow_id or "unknown"
        execution_id = context.execution_id or "default"
        node_id = (
            getattr(context.node, "id", "memory_node")
            if hasattr(context, "node")
            else "memory_node"
        )

        # Initialize conversation buffer - try to load from database first
        buffer_key = f"conversation_buffer_{execution_id}"

        # Try to load existing conversation history from database
        existing_buffer = self._load_from_database(workflow_id, execution_id, buffer_key, logs)
        if existing_buffer:
            buffer = existing_buffer
            logs.append(
                f"Loaded existing conversation history ({len(existing_buffer.get('messages', []))} messages)"
            )
            self.logger.info(
                f"🧠 MEMORY NODE: Loaded existing buffer from database with key: {buffer_key}"
            )
        else:
            # Also try to load conversation history from other executions of this workflow
            workflow_history = self._load_conversation_history_from_workflow(workflow_id, logs)
            buffer = {
                "messages": workflow_history,  # Start with historical messages
                "created_at": datetime.now().isoformat(),
            }
            if workflow_history:
                logs.append(
                    f"Initialized conversation buffer with {len(workflow_history)} historical messages"
                )
                self.logger.info(
                    f"🧠 MEMORY NODE: Initialized with {len(workflow_history)} historical messages"
                )
            else:
                logs.append("Initialized empty conversation buffer")

        # Log input data analysis
        if hasattr(context, "input_data") and context.input_data:
            if isinstance(context.input_data, dict):
                for key, value in context.input_data.items():
                    if isinstance(value, str) and len(value) > 100:
                        self.logger.info(
                            f"🧠 MEMORY NODE: Input '{key}': {value[:100]}... ({len(value)} chars)"
                        )
                    else:
                        self.logger.info(f"🧠 MEMORY NODE: Input '{key}': {value}")
        else:
            self.logger.info("🧠 MEMORY NODE: No input data provided")

        try:
            # Handle incoming message data with robust extraction
            message_content = ""
            message_role = "user"
            message_metadata = {}
            message_timestamp = datetime.now().isoformat()

            if context.input_data:
                # Try multiple extraction strategies to get the actual message content

                # Strategy 1: Direct content field
                message_content = context.input_data.get("content", "")

                # Strategy 2: Look in text field (common for text-based nodes)
                if not message_content:
                    message_content = context.input_data.get("text", "")

                # Strategy 3: Look in response field (common for AI agent outputs)
                if not message_content:
                    message_content = context.input_data.get("response", "")

                # Strategy 4: Look in message field
                if not message_content:
                    message_content = context.input_data.get("message", "")

                # Strategy 5: If input_data has nested content structures, try to extract from them
                if not message_content and isinstance(context.input_data, dict):
                    for key, value in context.input_data.items():
                        if isinstance(value, dict):
                            nested_content = (
                                value.get("content", "")
                                or value.get("text", "")
                                or value.get("response", "")
                            )
                            if nested_content:
                                message_content = nested_content
                                break
                        elif (
                            isinstance(value, str)
                            and len(value.strip()) > 0
                            and key
                            not in ["timestamp", "format_type", "source_node", "role", "metadata"]
                        ):
                            # Use any non-empty string value that isn't obviously metadata
                            message_content = value
                            break

                # Extract other message fields with intelligent role detection
                message_role = self._detect_message_role(context.input_data)
                message_timestamp = context.input_data.get("timestamp", datetime.now().isoformat())
                message_metadata = context.input_data.get("metadata", {})

                # Log extraction details for debugging
                self.logger.info(
                    f"🧠 MEMORY NODE: Content extraction - Found content: '{message_content[:100]}{'...' if len(message_content) > 100 else ''}' ({len(message_content)} chars)"
                )
                if not message_content:
                    self.logger.warning(
                        f"🧠 MEMORY NODE: ⚠️ No content found in input_data keys: {list(context.input_data.keys())}"
                    )
                    # Log the full input data for debugging (truncated)
                    input_data_str = str(context.input_data)[:500]
                    self.logger.warning(f"🧠 MEMORY NODE: Input data sample: {input_data_str}...")

            if context.input_data:
                # Only store messages with meaningful content
                if message_content and len(message_content.strip()) > 0:
                    # Store new message
                    message = {
                        "role": message_role,
                        "content": message_content,
                        "timestamp": message_timestamp,
                        "metadata": message_metadata,
                    }

                    # Add message to buffer
                    buffer["messages"].append(message)
                    logs.append(f"Added new {message['role']} message to conversation buffer")
                    self.logger.info(
                        f"🧠 MEMORY NODE: Added message to buffer - role: {message['role']}, content: '{message['content'][:100]}{'...' if len(message['content']) > 100 else ''}'"
                    )

                    # Apply windowing policy after adding message
                    if window_type == "turns" and len(buffer["messages"]) > window_size:
                        old_count = len(buffer["messages"])
                        # Remove oldest messages beyond window size
                        buffer["messages"] = buffer["messages"][-window_size:]

                        logs.append(
                            f"Applied windowing: trimmed conversation from {old_count} to {len(buffer['messages'])} messages"
                        )
                        self.logger.info(
                            f"🧠 MEMORY NODE: Trimmed buffer from {old_count} to {len(buffer['messages'])} messages (window_size: {window_size})"
                        )
                else:
                    self.logger.warning(
                        f"🧠 MEMORY NODE: ⚠️ Skipping empty message - no meaningful content found"
                    )
                    logs.append("Skipped storing empty message - no meaningful content")

            # Filter messages if needed
            messages_to_return = buffer["messages"]
            if not include_system_messages:
                original_count = len(messages_to_return)
                messages_to_return = [
                    msg for msg in messages_to_return if msg.get("role") != "system"
                ]
                filtered_count = len(messages_to_return)
                if original_count != filtered_count:
                    logs.append(f"Filtered out {original_count - filtered_count} system messages")
                    self.logger.info(
                        f"🧠 MEMORY NODE: Filtered out {original_count - filtered_count} system messages"
                    )

            # Calculate total tokens (mock calculation)
            total_tokens = sum(len(msg.get("content", "").split()) for msg in messages_to_return)

            # Log detailed message analysis
            for i, msg in enumerate(messages_to_return):
                content_preview = (
                    msg.get("content", "")[:50] + "..."
                    if len(msg.get("content", "")) > 50
                    else msg.get("content", "")
                )
                self.logger.info(
                    f"🧠 MEMORY NODE:   Message {i+1}: {msg.get('role', 'unknown')} - '{content_preview}'"
                )

            # Prepare context output
            context_data = {
                "messages": messages_to_return,
                "total_tokens": total_tokens,
                "memory_type": MemorySubtype.CONVERSATION_BUFFER.value,  # Include memory type for AI agent
                "window_info": {
                    "window_size": window_size,
                    "window_type": window_type,
                    "current_size": len(messages_to_return),
                    "storage_backend": storage_backend,
                },
            }

            # Create formatted memory context for LLM consumption
            memory_context_for_llm = self._format_conversation_context(messages_to_return, logs)
            context_data["formatted_context"] = memory_context_for_llm
            context_data[
                "memory_context"
            ] = memory_context_for_llm  # Also provide as memory_context for AI agent

            self.logger.info(
                f"🧠 MEMORY NODE:   📝 Formatted context length: {len(memory_context_for_llm)} characters"
            )

            # Save updated buffer to database for persistence across executions
            # Only save if we actually processed new data AND have meaningful content
            if context.input_data and message_content and len(message_content.strip()) > 0:
                self._save_to_database(workflow_id, execution_id, buffer_key, buffer, node_id, logs)
                # Also update in-memory store for backwards compatibility
                self._key_value_store[buffer_key] = buffer
                logs.append("Saved conversation buffer to database for persistence")

            logs.append(
                f"Conversation buffer complete: {len(messages_to_return)} messages, ~{total_tokens} tokens"
            )
            self.logger.info(
                f"🧠🔥 MEMORY NODE: ✅ CONVERSATION_BUFFER SUCCESS - Generated {len(messages_to_return)} messages, ~{total_tokens} tokens"
            )
            self.logger.info(f"🧠🔥 MEMORY NODE: ✅ Output data keys: {list(context_data.keys())}")

            return self._create_success_result(
                output_data=context_data, execution_time=time.time() - start_time, logs=logs
            )

        except Exception as e:
            logs.append(f"Conversation buffer operation failed: {str(e)}")
            return self._create_error_result(
                f"Error in conversation buffer operation: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs,
            )

    def _format_conversation_context(self, messages: List[Dict], logs: List[str]) -> str:
        """Format conversation messages into a readable context string for LLM integration."""
        if not messages:
            return ""

        formatted_lines = []
        formatted_lines.append("=== Recent Conversation History ===")

        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")

            # Format timestamp for readability
            timestamp_str = ""
            if timestamp:
                try:
                    from datetime import datetime

                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    timestamp_str = f" [{dt.strftime('%H:%M')}]"
                except:
                    timestamp_str = f" [{timestamp}]"

            # Format the message
            role_display = role.upper() if role in ["user", "assistant", "system"] else role
            formatted_lines.append(f"{role_display}{timestamp_str}: {content}")

        formatted_lines.append("=== End of Conversation History ===")
        formatted_context = "\n".join(formatted_lines)

        self.logger.info(
            f"🧠 MEMORY NODE: Formatted {len(messages)} messages into {len(formatted_context)} character context"
        )
        return formatted_context

    def _detect_message_role(self, input_data: Dict[str, Any]) -> str:
        """Intelligently detect the message role based on input data context."""

        # Strategy 1: Check if explicitly provided
        if "role" in input_data and input_data["role"] in ["user", "assistant", "system"]:
            return input_data["role"]

        # Strategy 2: Check source node type to determine role
        source_node = input_data.get("source_node", "")
        if source_node:
            # AI agent responses should be marked as assistant
            if any(
                ai_indicator in source_node.lower()
                for ai_indicator in [
                    "ai_agent",
                    "openai",
                    "anthropic",
                    "claude",
                    "gpt",
                    "llm",
                    "assistant",
                ]
            ):
                return "assistant"

            # Trigger nodes usually represent user input
            if "trigger" in source_node.lower():
                return "user"

        # Strategy 3: Check metadata for AI provider information
        metadata = input_data.get("metadata", {})
        if isinstance(metadata, dict):
            # Check for AI provider indicators
            if any(
                key in metadata for key in ["provider", "model", "model_version", "system_prompt"]
            ):
                provider = metadata.get("provider", "").lower()
                model = metadata.get("model", "").lower()
                if any(
                    ai_provider in f"{provider} {model}"
                    for ai_provider in ["openai", "anthropic", "gpt", "claude", "llama", "gemini"]
                ):
                    return "assistant"

        # No content analysis - use only reliable metadata-based detection

        # Default fallback - prefer user for ambiguous cases
        return "user"

    # Supporting methods for advanced memory types
    def _generate_conversation_summary(
        self, text: str, max_length: int, strategy: str, logs: List[str]
    ) -> str:
        """Generate conversation summary using specified strategy."""
        if strategy == "extractive":
            # Simple extractive summarization - take key sentences
            sentences = text.split(".")
            important_sentences = []

            # Simple scoring based on length and keywords
            keywords = ["important", "key", "main", "summary", "result", "decision", "action"]

            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 20:  # Skip very short sentences
                    score = len(sentence) / 100  # Base score
                    for keyword in keywords:
                        if keyword.lower() in sentence.lower():
                            score += 0.5
                    important_sentences.append((sentence, score))

            # Sort by score and take top sentences
            important_sentences.sort(key=lambda x: x[1], reverse=True)

            summary_parts = []
            current_length = 0
            for sentence, score in important_sentences:
                if current_length + len(sentence) <= max_length:
                    summary_parts.append(sentence)
                    current_length += len(sentence)
                else:
                    break

            summary = ". ".join(summary_parts)
            return summary

        elif strategy == "abstractive":
            # Simple abstractive - just truncate with smart boundaries
            if len(text) <= max_length:
                return text

            # Try to cut at sentence boundaries
            truncated = text[:max_length]
            last_period = truncated.rfind(".")
            if last_period > max_length * 0.7:  # If we can find a good sentence boundary
                summary = truncated[: last_period + 1]
            else:
                summary = truncated + "..."

            return summary

        else:
            # Default - just truncate
            summary = text[:max_length] + "..." if len(text) > max_length else text
            return summary

    def _format_conversation_summary_context(
        self, summary_data: Dict[str, Any], logs: List[str]
    ) -> str:
        """Format conversation summary for LLM consumption."""
        summary = summary_data.get("summary", "")
        message_count = summary_data.get("message_count", 0)

        if not summary:
            return "No conversation summary available yet."

        context = f"Conversation Summary ({message_count} messages):\n{summary}"
        return context

    def _extract_entities_simple(self, text: str, logs: List[str]) -> List[Dict[str, Any]]:
        """Simple entity extraction using patterns."""
        import re

        entities = []

        # Simple patterns for different entity types
        patterns = {
            "PERSON": r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b",  # First Last
            "ORGANIZATION": r"\b[A-Z][A-Za-z\s&]+(?:Inc|Corp|LLC|Ltd|Company|Organization)\b",
            "LOCATION": r"\b(?:in|at|from|to)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b",
            "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "PHONE": r"\b\d{3}-?\d{3}-?\d{4}\b",
            "DATE": r"\b\d{1,2}/\d{1,2}/\d{4}\b|\b\d{4}-\d{2}-\d{2}\b",
        }

        for entity_type, pattern in patterns.items():
            matches = re.findall(pattern, text)
            for match in matches:
                entity_text = match if isinstance(match, str) else match[0] if match else ""
                if entity_text and len(entity_text) > 1:
                    entity_id = (
                        f"{entity_type.lower()}_{hashlib.md5(entity_text.encode()).hexdigest()[:8]}"
                    )
                    entities.append(
                        {
                            "id": entity_id,
                            "name": entity_text,
                            "type": entity_type,
                            "mentions": 1,
                            "created_at": datetime.now().isoformat(),
                        }
                    )

        return entities

    def _format_entity_memory_context(self, entity_data: Dict[str, Any], logs: List[str]) -> str:
        """Format entity memory for LLM consumption."""
        entities = entity_data.get("entities", {})
        relationships = entity_data.get("relationships", [])

        if not entities and not relationships:
            return "No entities or relationships tracked yet."

        context_parts = []

        if entities:
            context_parts.append("Known Entities:")
            entity_list = list(entities.values())
            # Sort by mention count (most mentioned first)
            entity_list.sort(key=lambda x: x.get("mentions", 0), reverse=True)

            for entity in entity_list[:10]:  # Limit to top 10
                mentions = entity.get("mentions", 1)
                context_parts.append(
                    f"- {entity['name']} ({entity['type']}, mentioned {mentions}x)"
                )

        if relationships:
            context_parts.append("\nKnown Relationships:")
            for rel in relationships[-5:]:  # Show last 5 relationships
                context_parts.append(
                    f"- {rel['entity1']} --{rel['relation_type']}--> {rel['entity2']}"
                )

        formatted_context = "\n".join(context_parts)
        return formatted_context

    def _format_knowledge_base_context(
        self, kb_data: Dict[str, Any], result: Dict[str, Any], logs: List[str]
    ) -> str:
        """Format knowledge base for LLM consumption."""
        facts = kb_data.get("facts", {})
        categories = kb_data.get("categories", {})

        if not facts:
            return "No facts stored in knowledge base yet."

        context_parts = []

        # Show recent or matching facts
        if "matching_facts" in result:
            # Show query results
            matching_facts = result["matching_facts"]
            if matching_facts:
                context_parts.append("Relevant Facts:")
                for fact in matching_facts[:5]:  # Show top 5 matches
                    confidence = fact.get("confidence", 0.8)
                    context_parts.append(f"- {fact['text']} (confidence: {confidence:.2f})")
        else:
            # Show most accessed or recent facts
            fact_list = list(facts.values())
            fact_list.sort(key=lambda x: x.get("access_count", 0), reverse=True)

            if fact_list:
                context_parts.append("Key Facts:")
                for fact in fact_list[:5]:  # Show top 5 facts
                    confidence = fact.get("confidence", 0.8)
                    context_parts.append(f"- {fact['text']} (confidence: {confidence:.2f})")

        # Show categories
        if categories:
            context_parts.append(f"\nKnowledge Categories: {', '.join(categories.keys())}")

        formatted_context = "\n".join(context_parts)
        self.logger.info(
            f"🧠 MEMORY NODE: Formatted knowledge base context ({len(formatted_context)} chars)"
        )
        return formatted_context

    def _execute_conversation_summary(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute conversation summary memory operations."""

        # Get parameters with fallbacks
        try:
            max_length = self.get_parameter_with_spec(context, "max_length")
        except (KeyError, AttributeError):
            max_length = 500

        try:
            summary_strategy = self.get_parameter_with_spec(context, "summary_strategy")
        except (KeyError, AttributeError):
            summary_strategy = "extractive"  # extractive, abstractive

        try:
            storage_backend = self.get_parameter_with_spec(context, "storage_backend")
        except (KeyError, AttributeError):
            storage_backend = "memory"

            self.logger.info(
                f"🧠 MEMORY NODE: Summary config - max_length: {max_length}, strategy: {summary_strategy}, backend: {storage_backend}"
            )

        # Initialize conversation summary storage
        summary_key = f"conversation_summary_{context.execution_id or 'default'}"
        if summary_key not in self._key_value_store:
            self._key_value_store[summary_key] = {
                "summary": "",
                "message_count": 0,
                "last_updated": datetime.now().isoformat(),
                "total_chars": 0,
            }

        summary_data = self._key_value_store[summary_key]

        try:
            # Handle new conversation data
            if context.input_data:
                new_messages = context.input_data.get("messages", [])
                new_text = context.input_data.get("text", "") or context.input_data.get(
                    "content", ""
                )

                if new_messages:
                    self.logger.info(
                        f"🧠 MEMORY NODE: Processing {len(new_messages)} new messages for summary"
                    )
                    text_to_summarize = "\n".join(
                        [
                            f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                            for msg in new_messages
                        ]
                    )
                elif new_text:
                    self.logger.info(
                        f"🧠 MEMORY NODE: Processing new text content ({len(new_text)} chars) for summary"
                    )
                    text_to_summarize = new_text
                else:
                    text_to_summarize = ""

                if text_to_summarize:
                    # Combine with existing summary
                    combined_text = f"{summary_data['summary']}\n\n{text_to_summarize}".strip()

                    if len(combined_text) > max_length * 2:  # Need to compress
                        self.logger.info(
                            f"🧠 MEMORY NODE: Content exceeds threshold, generating new summary..."
                        )
                        new_summary = self._generate_conversation_summary(
                            combined_text, max_length, summary_strategy, logs
                        )
                        summary_data["summary"] = new_summary
                        summary_data["message_count"] += len(new_messages) if new_messages else 1
                        summary_data["last_updated"] = datetime.now().isoformat()
                        summary_data["total_chars"] = len(new_summary)
                    else:
                        # Just append to existing summary
                        summary_data["summary"] = combined_text
                        summary_data["message_count"] += len(new_messages) if new_messages else 1
                        summary_data["last_updated"] = datetime.now().isoformat()
                        summary_data["total_chars"] = len(combined_text)

            # Format context for LLM
            memory_context = self._format_conversation_summary_context(summary_data, logs)

            context_data = {
                "summary": summary_data["summary"],
                "message_count": summary_data["message_count"],
                "total_chars": summary_data["total_chars"],
                "last_updated": summary_data["last_updated"],
                "memory_type": MemorySubtype.CONVERSATION_SUMMARY.value,
                "memory_context": memory_context,
                "formatted_context": memory_context,
            }

            self.logger.info(
                f"🧠 MEMORY NODE:   📝 Summary length: {summary_data['total_chars']} characters"
            )

            return self._create_success_result(
                output_data=context_data, execution_time=time.time() - start_time, logs=logs
            )

        except Exception as e:
            return self._create_error_result(
                f"Error in conversation summary operation: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs,
            )

    def _execute_entity_memory(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute entity memory operations."""

        # Get parameters with fallbacks
        try:
            operation = self.get_parameter_with_spec(context, "operation")
        except (KeyError, AttributeError):
            operation = context.input_data.get("operation", "extract")

        try:
            storage_backend = self.get_parameter_with_spec(context, "storage_backend")
        except (KeyError, AttributeError):
            storage_backend = "memory"

        self.logger.info(
            f"🧠 MEMORY NODE: Entity operation '{operation}' with backend: {storage_backend}"
        )

        # Initialize entity storage
        entities_key = f"entities_{context.execution_id or 'default'}"
        if entities_key not in self._key_value_store:
            self._key_value_store[entities_key] = {
                "entities": {},
                "relationships": [],
                "last_updated": datetime.now().isoformat(),
            }

        entity_data = self._key_value_store[entities_key]

        try:
            if operation == "extract":
                # Extract entities from text input
                text_input = context.input_data.get("text", "") or context.input_data.get(
                    "content", ""
                )
                if not text_input:
                    raise ValueError("No text provided for entity extraction")

                self.logger.info(
                    f"🧠 MEMORY NODE: Extracting entities from text ({len(text_input)} chars)"
                )
                extracted_entities = self._extract_entities_simple(text_input, logs)

                # Store extracted entities
                for entity in extracted_entities:
                    entity_id = entity["id"]
                    if entity_id not in entity_data["entities"]:
                        entity_data["entities"][entity_id] = entity
                        self.logger.info(
                            f"🧠 MEMORY NODE: Added new entity: {entity['name']} ({entity['type']})"
                        )
                    else:
                        # Update existing entity
                        existing = entity_data["entities"][entity_id]
                        existing["mentions"] = existing.get("mentions", 0) + entity.get(
                            "mentions", 1
                        )
                        existing["last_seen"] = datetime.now().isoformat()
                        self.logger.info(
                            f"🧠 MEMORY NODE: Updated entity: {entity['name']} (mentions: {existing['mentions']})"
                        )

                entity_data["last_updated"] = datetime.now().isoformat()
                result = {
                    "extracted_entities": extracted_entities,
                    "total_entities": len(entity_data["entities"]),
                }

            elif operation == "query":
                # Query entities by type or name
                query_type = context.input_data.get("entity_type", "")
                query_name = context.input_data.get("entity_name", "")

                matching_entities = []
                for entity_id, entity in entity_data["entities"].items():
                    if (not query_type or entity["type"].lower() == query_type.lower()) and (
                        not query_name or query_name.lower() in entity["name"].lower()
                    ):
                        matching_entities.append(entity)

                self.logger.info(
                    f"🧠 MEMORY NODE: Found {len(matching_entities)} entities matching query"
                )
                result = {
                    "matching_entities": matching_entities,
                    "query_type": query_type,
                    "query_name": query_name,
                }

            elif operation == "relate":
                # Add relationship between entities
                entity1 = context.input_data.get("entity1", "")
                entity2 = context.input_data.get("entity2", "")
                relation_type = context.input_data.get("relation_type", "related_to")

                if not entity1 or not entity2:
                    raise ValueError("Both entity1 and entity2 required for relationship")

                relationship = {
                    "entity1": entity1,
                    "entity2": entity2,
                    "relation_type": relation_type,
                    "created_at": datetime.now().isoformat(),
                }

                entity_data["relationships"].append(relationship)
                self.logger.info(
                    f"🧠 MEMORY NODE: Added relationship: {entity1} --{relation_type}--> {entity2}"
                )
                result = {
                    "relationship_added": True,
                    "total_relationships": len(entity_data["relationships"]),
                }

            elif operation == "list":
                # List all entities
                all_entities = list(entity_data["entities"].values())
                result = {"entities": all_entities, "count": len(all_entities)}

            else:
                raise ValueError(f"Unknown entity operation: {operation}")

            # Format context for LLM
            memory_context = self._format_entity_memory_context(entity_data, logs)

            output_data = {
                "memory_type": MemorySubtype.ENTITY_MEMORY.value,
                "operation": operation,
                "result": result,
                "entity_count": len(entity_data["entities"]),
                "relationship_count": len(entity_data["relationships"]),
                "memory_context": memory_context,
                "formatted_context": memory_context,
                "success": True,
                "executed_at": datetime.now().isoformat(),
            }

            return self._create_success_result(
                output_data=output_data, execution_time=time.time() - start_time, logs=logs
            )

        except Exception as e:
            return self._create_error_result(
                f"Error in entity memory operation: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs,
            )

    def _execute_episodic_memory(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute episodic memory operations (placeholder)."""
        _ = context  # Mark as used to avoid linting warnings
        return self._create_error_result(
            "Episodic memory not yet implemented",
            execution_time=time.time() - start_time,
            logs=logs,
        )

    def _execute_knowledge_base(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute knowledge base memory operations."""

        # Get parameters with fallbacks
        try:
            operation = self.get_parameter_with_spec(context, "operation")
        except (KeyError, AttributeError):
            operation = context.input_data.get("operation", "add_fact")

        try:
            storage_backend = self.get_parameter_with_spec(context, "storage_backend")
        except (KeyError, AttributeError):
            storage_backend = "memory"

            self.logger.info(
                f"🧠 MEMORY NODE: Knowledge operation '{operation}' with backend: {storage_backend}"
            )

        # Initialize knowledge base storage
        kb_key = f"knowledge_base_{context.execution_id or 'default'}"
        if kb_key not in self._key_value_store:
            self._key_value_store[kb_key] = {
                "facts": {},
                "rules": [],
                "categories": {},
                "last_updated": datetime.now().isoformat(),
            }

        kb_data = self._key_value_store[kb_key]

        try:
            if operation == "add_fact":
                # Add a new fact to the knowledge base
                fact_text = context.input_data.get("fact", "") or context.input_data.get("text", "")
                category = context.input_data.get("category", "general")
                confidence = context.input_data.get("confidence", 0.8)
                source = context.input_data.get("source", "user_input")

                if not fact_text:
                    raise ValueError("No fact text provided")

                fact_id = f"fact_{len(kb_data['facts']) + 1}"
                fact_entry = {
                    "id": fact_id,
                    "text": fact_text,
                    "category": category,
                    "confidence": confidence,
                    "source": source,
                    "created_at": datetime.now().isoformat(),
                    "access_count": 0,
                }

                kb_data["facts"][fact_id] = fact_entry

                # Update category count
                if category not in kb_data["categories"]:
                    kb_data["categories"][category] = 0
                kb_data["categories"][category] += 1

                self.logger.info(
                    f"🧠 MEMORY NODE: Added fact '{fact_text[:50]}...' to category '{category}'"
                )
                result = {
                    "fact_added": True,
                    "fact_id": fact_id,
                    "total_facts": len(kb_data["facts"]),
                }

            elif operation == "query":
                # Query facts by category or text search
                query_text = context.input_data.get("query", "") or context.input_data.get(
                    "text", ""
                )
                category_filter = context.input_data.get("category", "")
                min_confidence = context.input_data.get("min_confidence", 0.0)

                matching_facts = []
                for fact_id, fact in kb_data["facts"].items():
                    # Filter by category
                    if category_filter and fact["category"] != category_filter:
                        continue

                    # Filter by confidence
                    if fact["confidence"] < min_confidence:
                        continue

                    # Text search
                    if query_text:
                        if query_text.lower() in fact["text"].lower():
                            matching_facts.append(fact)
                            fact["access_count"] += 1  # Track access
                    else:
                        matching_facts.append(fact)
                        fact["access_count"] += 1

                # Sort by confidence and access count
                matching_facts.sort(
                    key=lambda x: (x["confidence"], x["access_count"]), reverse=True
                )

                result = {
                    "matching_facts": matching_facts,
                    "query": query_text,
                    "category_filter": category_filter,
                    "count": len(matching_facts),
                }

            elif operation == "add_rule":
                # Add inference rule
                rule_text = context.input_data.get("rule", "") or context.input_data.get("text", "")
                rule_type = context.input_data.get("rule_type", "simple")
                conditions = context.input_data.get("conditions", [])
                conclusions = context.input_data.get("conclusions", [])

                if not rule_text:
                    raise ValueError("No rule text provided")

                rule_entry = {
                    "id": f"rule_{len(kb_data['rules']) + 1}",
                    "text": rule_text,
                    "type": rule_type,
                    "conditions": conditions,
                    "conclusions": conclusions,
                    "created_at": datetime.now().isoformat(),
                    "applied_count": 0,
                }

                kb_data["rules"].append(rule_entry)
                result = {"rule_added": True, "total_rules": len(kb_data["rules"])}

            elif operation == "get_categories":
                # Get all categories with counts
                result = {
                    "categories": kb_data["categories"],
                    "total_categories": len(kb_data["categories"]),
                }

            elif operation == "infer":
                # Simple inference based on rules (basic implementation)
                query_facts = context.input_data.get("query_facts", [])
                applicable_rules = []

                for rule in kb_data["rules"]:
                    # Simple rule matching (can be enhanced)
                    if rule["type"] == "simple" and rule["conditions"]:
                        rule_applicable = True
                        for condition in rule["conditions"]:
                            if condition not in query_facts:
                                rule_applicable = False
                                break

                        if rule_applicable:
                            applicable_rules.append(rule)
                            rule["applied_count"] += 1

                result = {"applicable_rules": applicable_rules, "inferences": len(applicable_rules)}

            else:
                raise ValueError(f"Unknown knowledge base operation: {operation}")

            kb_data["last_updated"] = datetime.now().isoformat()

            # Format context for LLM
            memory_context = self._format_knowledge_base_context(kb_data, result, logs)

            output_data = {
                "memory_type": MemorySubtype.KNOWLEDGE_BASE.value,
                "operation": operation,
                "result": result,
                "total_facts": len(kb_data["facts"]),
                "total_rules": len(kb_data["rules"]),
                "total_categories": len(kb_data["categories"]),
                "memory_context": memory_context,
                "formatted_context": memory_context,
                "success": True,
                "executed_at": datetime.now().isoformat(),
            }

            return self._create_success_result(
                output_data=output_data, execution_time=time.time() - start_time, logs=logs
            )

        except Exception as e:
            return self._create_error_result(
                f"Error in knowledge base operation: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs,
            )

    def _execute_graph_memory(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute graph memory operations (placeholder)."""
        _ = context  # Mark as used to avoid linting warnings
        return self._create_error_result(
            "Graph memory not yet implemented", execution_time=time.time() - start_time, logs=logs
        )

    def _execute_working_memory(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute working memory operations (placeholder)."""
        _ = context  # Mark as used to avoid linting warnings
        return self._create_error_result(
            "Working memory not yet implemented", execution_time=time.time() - start_time, logs=logs
        )
