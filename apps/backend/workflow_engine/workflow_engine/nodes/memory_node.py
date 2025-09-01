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
from shared.models.node_enums import MemorySubtype, OpenAIModel
from shared.node_specs import node_spec_registry
from shared.node_specs.base import NodeSpec

from .base import BaseNodeExecutor, NodeExecutionContext, NodeExecutionResult

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
        self._supabase_client: Optional["Client"] = None

        # Gemini client for AI summarization
        self._gemini_model = None
        self._setup_gemini_client()

    def _setup_gemini_client(self) -> None:
        """Setup Gemini client for AI summarization."""
        try:
            google_api_key = os.getenv("GOOGLE_API_KEY")
            if google_api_key:
                import google.generativeai as genai

                genai.configure(api_key=google_api_key)
                self._gemini_model = genai.GenerativeModel("gemini-2.0-flash-exp")
                self.logger.info("Gemini client initialized for AI summarization")
            else:
                self.logger.warning("No GOOGLE_API_KEY found - AI summarization unavailable")
        except ImportError:
            self.logger.warning("google-generativeai not installed - AI summarization unavailable")
        except Exception as e:
            self.logger.error(f"Failed to setup Gemini client: {e}")

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
            self.logger.info(
                f"[Memory Node]: 🧠🔥 MEMORY NODE EXECUTE: Starting with subtype: {subtype}"
            )
            self.logger.info(
                f"[Memory Node]: 🧠🔥 MEMORY NODE EXECUTE: Workflow ID: {getattr(context, 'workflow_id', 'NONE')}"
            )
            self.logger.info(
                f"[Memory Node]: 🧠🔥 MEMORY NODE EXECUTE: Execution ID: {getattr(context, 'execution_id', 'NONE')}"
            )
            self.logger.info(
                f"[Memory Node]: 🧠🔥 MEMORY NODE EXECUTE: Node ID: {getattr(context.node, 'id', 'NONE') if hasattr(context, 'node') else 'NO_NODE'}"
            )
            self.logger.info(
                f"[Memory Node]: 🧠🔥 MEMORY NODE EXECUTE: Input data keys: {list(context.input_data.keys()) if hasattr(context, 'input_data') and context.input_data else 'NO_INPUT'}"
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
            f"[Memory Node]: 🧠 MEMORY NODE: Vector DB operation '{operation}' on collection '{collection_name}'"
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
                    f"[Memory Node]: 🧠 MEMORY NODE: Embedding text content: '{text_content[:100]}...' ({len(text_content)} chars)"
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
                    f"[Memory Node]: 🧠 MEMORY NODE: Searching for: '{query_text[:100]}...' (top_k={top_k}, threshold={similarity_threshold})"
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
                    f"[Memory Node]: 🧠 MEMORY NODE:   📝 Formatted context length: {len(memory_context)} characters"
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
                    f"[Memory Node]: 🧠 MEMORY NODE: Storing document '{document_id}' with content length: {len(content)} chars"
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
                    f"[Memory Node]: 🧠 MEMORY NODE: Searching documents for: '{query[:100]}...' (type: {search_type}, max: {max_results})"
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
                    f"[Memory Node]: 🧠 MEMORY NODE:   📊 {len(result['documents'])} relevant documents found"
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

            from openai import OpenAI

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                # Return mock embedding for testing
                return [0.1] * 1536  # OpenAI text-embedding-ada-002 dimension

            client = OpenAI(api_key=api_key)

            response = client.embeddings.create(model="text-embedding-ada-002", input=text)

            embedding = response.data[0].embedding
            return embedding

        except Exception:
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
        except (ZeroDivisionError, ValueError, TypeError):
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
            f"[Memory Node]: 🧠 MEMORY NODE: 📊 Found {len(similarities)} results above threshold {similarity_threshold}"
        )

        avg_similarity = 0.0
        if results:
            avg_similarity = sum(r["similarity"] for r in results) / len(results)

        return {
            "results": results,
            "count": len(results),
            "query": query_text,
            "similarity_threshold": similarity_threshold,
            "total_candidates": len(self._vector_db[collection_name]),
            "avg_similarity": avg_similarity,
        }

    def _delete_vector(
        self, collection_name: str, vector_id: str, logs: List[str]
    ) -> Dict[str, Any]:
        """Delete vector from collection with logging."""
        logs.append(f"Deleting vector '{vector_id}' from collection '{collection_name}'")

        if collection_name not in self._vector_db:
            return {"error": "Collection not found"}

        for i, vector_entry in enumerate(self._vector_db[collection_name]):
            if vector_entry["id"] == vector_id:
                del self._vector_db[collection_name][i]
                logs.append(f"Successfully deleted vector '{vector_id}'")
                return {"deleted": True, "vector_id": vector_id}

        return {"error": "Vector not found"}

    def _list_vectors(self, collection_name: str, logs: List[str]) -> Dict[str, Any]:
        """List all vectors in collection."""
        logs.append(f"Listing vectors in collection '{collection_name}'")

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
            f"[Memory Node]: 🧠 MEMORY NODE: 📋 Listed {len(vectors)} vectors from collection '{collection_name}'"
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
            f"[Memory Node]: 🧠 MEMORY NODE: ✅ Updated document '{document_id}' with {len(word_index)} unique words indexed"
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
            f"[Memory Node]: 🧠 MEMORY NODE: Searching {len(self._document_store)} documents with query words: {list(query_words)}"
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

        avg_score = 0.0
        if results:
            avg_score = sum(r["score"] for r in results) / len(results)

        return {
            "documents": results,
            "count": len(results),
            "query": query,
            "search_type": search_type,
            "total_documents": len(self._document_store),
            "avg_score": avg_score,
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
            # Mock similarity search (embeddings not used in mock implementation)
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

    def _get_supabase_client(self) -> Optional["Client"]:
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
                (
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
                supabase.table("workflow_memory").insert(memory_record).execute()

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

        except Exception:
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

        except Exception:
            return []

    def _execute_conversation_buffer(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute conversation buffer memory operations."""
        logs.append("Starting conversation buffer memory operation")
        self.logger.info("[Memory Node]: 🧠🔥 MEMORY NODE: Starting CONVERSATION_BUFFER execution")
        self.logger.info(
            f"[Memory Node]: 🧠🔥 MEMORY NODE: Execution ID: {getattr(context, 'execution_id', 'unknown')}"
        )
        self.logger.info(
            f"[Memory Node]: 🧠🔥 MEMORY NODE: Node ID: {getattr(context.node, 'id', 'unknown') if hasattr(context, 'node') else 'unknown'}"
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
            f"[Memory Node]: 🧠 MEMORY NODE: Configuration - window_size: {window_size}, window_type: {window_type}, backend: {storage_backend}"
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
                f"[Memory Node]: 🧠 MEMORY NODE: Loaded existing buffer from database with key: {buffer_key}"
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
                    f"[Memory Node]: 🧠 MEMORY NODE: Initialized with {len(workflow_history)} historical messages"
                )
            else:
                logs.append("Initialized empty conversation buffer")

        # Check if this is a special action to load conversation history for AI agent
        if (
            hasattr(context, "input_data")
            and context.input_data
            and context.input_data.get("action") == "load_conversation_history"
        ):
            self.logger.info(
                "[Memory Node]: 🧠 MEMORY NODE: Loading conversation history for AI agent"
            )

            # Return existing conversation history as formatted context
            messages = buffer.get("messages", [])
            conversation_history = self._format_conversation_history_for_ai(messages, logs)

            output_data = {
                "conversation_history": conversation_history,
                "message_count": len(messages),
                "memory_type": MemorySubtype.CONVERSATION_BUFFER.value,
                "executed_at": datetime.now().isoformat(),
            }

            return self._create_success_result(
                output_data=output_data, execution_time=time.time() - start_time, logs=logs
            )

        # Log input data analysis
        if hasattr(context, "input_data") and context.input_data:
            if isinstance(context.input_data, dict):
                for key, value in context.input_data.items():
                    if isinstance(value, str) and len(value) > 100:
                        self.logger.info(
                            f"[Memory Node]: 🧠 MEMORY NODE: Input '{key}': {value[:100]}... ({len(value)} chars)"
                        )
                    else:
                        self.logger.info(f"[Memory Node]: 🧠 MEMORY NODE: Input '{key}': {value}")
        else:
            self.logger.info("[Memory Node]: 🧠 MEMORY NODE: No input data provided")

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
                # Need to extract from nested structure like content extraction
                role_data = context.input_data
                # Check if data is nested under a key (like 'memory')
                if isinstance(context.input_data, dict):
                    for key, value in context.input_data.items():
                        if isinstance(value, dict) and any(
                            field in value for field in ["source_node", "metadata", "provider"]
                        ):
                            role_data = value
                            break

                message_role = self._detect_message_role(role_data)

                # Log role detection for debugging
                self.logger.info(
                    f"[Memory Node]: 🧠 MEMORY NODE: Role detection - source_node: '{role_data.get('source_node', 'none')}', detected role: '{message_role}'"
                )
                message_timestamp = role_data.get("timestamp", datetime.now().isoformat())
                message_metadata = role_data.get("metadata", {})

                # Log extraction details for debugging
                self.logger.info(
                    f"[Memory Node]: 🧠 MEMORY NODE: Content extraction - Found content: '{message_content[:100]}{'...' if len(message_content) > 100 else ''}' ({len(message_content)} chars)"
                )
                if not message_content:
                    self.logger.warning(
                        f"[Memory Node]: 🧠 MEMORY NODE: ⚠️ No content found in input_data keys: {list(context.input_data.keys())}"
                    )
                    # Log the full input data for debugging (truncated)
                    input_data_str = str(context.input_data)[:500]
                    self.logger.warning(
                        f"[Memory Node]: 🧠 MEMORY NODE: Input data sample: {input_data_str}..."
                    )

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
                        f"[Memory Node]: 🧠 MEMORY NODE: Added message to buffer - role: {message['role']}, content: '{message['content'][:100]}{'...' if len(message['content']) > 100 else ''}'"
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
                            f"[Memory Node]: 🧠 MEMORY NODE: Trimmed buffer from {old_count} to {len(buffer['messages'])} messages (window_size: {window_size})"
                        )
                else:
                    self.logger.warning(
                        f"[Memory Node]: 🧠 MEMORY NODE: ⚠️ Skipping empty message - no meaningful content found"
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
                        f"[Memory Node]: 🧠 MEMORY NODE: Filtered out {original_count - filtered_count} system messages"
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
                    f"[Memory Node]: 🧠 MEMORY NODE:   Message {i+1}: {msg.get('role', 'unknown')} - '{content_preview}'"
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
                f"[Memory Node]: 🧠 MEMORY NODE:   📝 Formatted context length: {len(memory_context_for_llm)} characters"
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
                f"[Memory Node]: 🧠🔥 MEMORY NODE: ✅ CONVERSATION_BUFFER SUCCESS - Generated {len(messages_to_return)} messages, ~{total_tokens} tokens"
            )
            self.logger.info(
                f"[Memory Node]: 🧠🔥 MEMORY NODE: ✅ Output data keys: {list(context_data.keys())}"
            )

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
            f"[Memory Node]: 🧠 MEMORY NODE: Formatted {len(messages)} messages into {len(formatted_context)} character context"
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

    def _format_conversation_history_for_ai(
        self, messages: List[Dict[str, Any]], logs: List[str]
    ) -> str:
        """Format conversation history for AI agent consumption."""
        if not messages:
            return ""

        self.logger.info(
            f"[Memory Node]: 🧠 MEMORY NODE: Formatting {len(messages)} messages for AI consumption"
        )

        formatted_conversations = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Skip empty messages
            if not content or len(content.strip()) == 0:
                continue

            # Format with clear role indicators
            if role == "user":
                formatted_conversations.append(f"User: {content}")
            elif role == "assistant":
                formatted_conversations.append(f"Assistant: {content}")
            else:
                formatted_conversations.append(f"{role.title()}: {content}")

        conversation_text = "\n\n".join(formatted_conversations)
        self.logger.info(
            f"[Memory Node]: 🧠 MEMORY NODE: Formatted conversation history ({len(conversation_text)} chars)"
        )

        return conversation_text

    # Supporting methods for advanced memory types
    def _generate_conversation_summary_with_metadata(
        self, text: str, max_length: int, strategy: str, logs: List[str]
    ) -> Dict[str, Any]:
        """Generate conversation summary with metadata using AI or fallback strategies."""
        # Enforce reasonable summary length limits (max 1500 characters for summaries)
        MAX_SUMMARY_LENGTH = 1500
        effective_max_length = min(max_length, MAX_SUMMARY_LENGTH)

        # Log warning if the provided max_length was too large
        if max_length > MAX_SUMMARY_LENGTH:
            logs.append(
                f"[Memory Node]: Warning - Requested max_length ({max_length}) exceeded limit, using {MAX_SUMMARY_LENGTH}"
            )

        # Try AI summarization first if available
        if self._gemini_model and len(text) > 100:  # Only use AI for substantial content
            try:
                ai_result = self._call_gemini_for_summary(
                    text, effective_max_length, strategy, logs
                )
                if ai_result and ai_result.get("summary"):
                    logs.append(
                        f"[Memory Node]: AI summary generated ({len(ai_result['summary'])} chars)"
                    )
                    return ai_result
            except Exception as e:
                logs.append(f"[Memory Node]: AI summarization failed, using fallback: {str(e)}")

        # Fallback to rule-based strategies
        summary = self._get_fallback_summary(text, effective_max_length, strategy, logs)
        return {"summary": summary, "key_points": [], "topics": []}

    def _call_gemini_for_summary(
        self, text: str, max_length: int, strategy: str, logs: List[str]
    ) -> Dict[str, Any]:
        """Generate AI summary with metadata using Gemini."""
        try:
            # Create AI summarization prompt
            prompt = self._create_ai_summarization_prompt(text, max_length, strategy)

            # Call Gemini synchronously (simpler approach)
            response = self._gemini_model.generate_content(prompt)
            response_text = response.text

            # Parse and validate response
            summary_data = self._parse_ai_summary_response(response_text)
            summary = summary_data.get("summary", "").strip()

            if not summary:
                logs.append("[Memory Node]: AI returned empty summary")
                return {"summary": "", "key_points": [], "topics": []}

            # Truncate if still too long
            if len(summary) > max_length:
                summary = self._truncate_summary_intelligently(summary, max_length)

            return {
                "summary": summary,
                "key_points": summary_data.get("key_points", []),
                "topics": summary_data.get("main_topics", []),
            }

        except Exception as e:
            self.logger.error(f"AI summarization failed: {e}")
            return {"summary": "", "key_points": [], "topics": []}

    def _get_fallback_summary(
        self, text: str, max_length: int, strategy: str, logs: List[str]
    ) -> str:
        """Get fallback summary using rule-based strategies."""
        if strategy == "extractive":
            return self._extractive_summarization(text, max_length, logs)
        elif strategy == "progressive":
            return self._progressive_summarization(text, max_length, logs)
        elif strategy == "abstractive":
            # Abstractive without AI falls back to extractive
            logs.append("[Memory Node]: Abstractive strategy using extractive fallback")
            return self._extractive_summarization(text, max_length, logs)
        else:
            # Default - extractive summarization
            return self._extractive_summarization(text, max_length, logs)

    def _create_ai_summarization_prompt(self, text: str, max_length: int, strategy: str) -> str:
        """Create prompt for AI summarization."""
        max_words = max_length // 5  # Rough words to chars ratio

        strategy_instructions = {
            "progressive": "Focus on key developments, decisions, and progression of ideas. Capture the main themes and outcomes.",
            "extractive": "Extract and combine the most important sentences and key points from the conversation.",
            "abstractive": "Create a comprehensive summary that captures the essence and main points in your own words.",
        }

        instruction = strategy_instructions.get(strategy, strategy_instructions["progressive"])

        prompt = f"""
Summarize this conversation in approximately {max_words} words or less ({max_length} characters maximum).

{instruction}

Focus on:
- Key decisions made or discussed
- Important actions planned or taken
- Main problems or questions raised
- Solutions or answers provided
- User requests and system responses
- Important outcomes or conclusions

Conversation to summarize:
{text}

Provide your response as JSON in this format:
{{
    "summary": "Your concise summary here",
    "key_points": ["Point 1", "Point 2", "Point 3"],
    "main_topics": ["Topic 1", "Topic 2"]
}}

Summary:
"""
        return prompt

    def _parse_ai_summary_response(self, response: str) -> Dict[str, Any]:
        """Parse Gemini AI response."""
        try:
            # Look for JSON in response
            if "{" in response and "}" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
                parsed = json.loads(json_str)
                return parsed
            else:
                # If no JSON, treat entire response as summary
                return {"summary": response.strip(), "key_points": [], "main_topics": []}
        except Exception as e:
            self.logger.warning(f"Failed to parse AI summary response: {e}")
            return {
                "summary": response.strip() if response else "",
                "key_points": [],
                "main_topics": [],
            }

    def _extractive_summarization(self, text: str, max_length: int, logs: List[str]) -> str:
        """Extractive summarization using keyword scoring."""
        sentences = text.split(".")
        important_sentences = []

        # Comprehensive keywords for extractive summarization
        keywords = [
            "important",
            "key",
            "main",
            "summary",
            "result",
            "decision",
            "action",
            "concluded",
            "agreed",
            "decided",
            "user",
            "request",
            "question",
            "problem",
            "solution",
            "answer",
            "plan",
            "strategy",
            "goal",
        ]

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20:  # Skip very short sentences
                score = len(sentence) / 100  # Base score
                sentence_lower = sentence.lower()

                # Keyword scoring
                for keyword in keywords:
                    if keyword in sentence_lower:
                        score += 0.5

                # Boost for question/answer patterns
                if "?" in sentence or sentence.startswith(("User:", "Assistant:", "AI:")):
                    score += 0.3

                important_sentences.append((sentence, score))

        # Sort by score and select top sentences
        important_sentences.sort(key=lambda x: x[1], reverse=True)

        summary_parts = []
        current_length = 0
        for sentence, score in important_sentences:
            if current_length + len(sentence) + 2 <= max_length:  # +2 for ". "
                summary_parts.append(sentence)
                current_length += len(sentence) + 2
            else:
                break

        summary = ". ".join(summary_parts)
        if len(summary) > max_length:
            summary = self._truncate_summary_intelligently(summary, max_length)

        logs.append(f"[Memory Node]: Extractive summary selected {len(summary_parts)} sentences")
        return summary

    def _progressive_summarization(self, text: str, max_length: int, logs: List[str]) -> str:
        """Progressive summarization focusing on key developments."""
        lines = text.split("\n")
        key_content = []

        # Progressive summary keywords
        progressive_keywords = [
            "decision",
            "decided",
            "agreed",
            "concluded",
            "resolved",
            "determined",
            "action",
            "next step",
            "todo",
            "will",
            "plan",
            "strategy",
            "approach",
            "important",
            "key",
            "main",
            "critical",
            "essential",
            "significant",
            "problem",
            "issue",
            "solution",
            "answer",
            "result",
            "outcome",
            "user",
            "request",
            "question",
            "need",
            "requirement",
            "goal",
            "completed",
            "done",
            "finished",
            "implemented",
            "created",
            "built",
        ]

        # Score each line based on content relevance
        scored_lines = []
        for line in lines:
            line = line.strip()
            if len(line) < 20:  # Skip very short lines
                continue

            score = 0
            line_lower = line.lower()

            # Keyword scoring
            for keyword in progressive_keywords:
                if keyword in line_lower:
                    score += 1

            # Boost for questions/responses
            if "?" in line or line.startswith(("User:", "Assistant:", "AI:")):
                score += 1

            # Boost for longer, substantive lines
            if len(line) > 50:
                score += 0.5

            if score > 0:
                scored_lines.append((line, score))

        # Sort by score and select top content
        scored_lines.sort(key=lambda x: x[1], reverse=True)

        current_length = 0
        for line, score in scored_lines:
            if current_length + len(line) + 1 <= max_length:
                key_content.append(line)
                current_length += len(line) + 1
            else:
                break

        if key_content:
            summary = "\n".join(key_content)
            logs.append(
                f"[Memory Node]: Progressive summary extracted {len(key_content)} key lines"
            )
        else:
            # Fallback to intelligent truncation
            summary = self._truncate_summary_intelligently(text, max_length)
            logs.append(
                "[Memory Node]: Progressive summary fallback - using intelligent truncation"
            )

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

    def _load_conversation_from_supabase(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """Load conversation data from Supabase tables."""
        try:
            supabase = self._get_supabase_client()
            if not supabase:
                self.logger.warning(
                    "[Memory Node]: 🧠 ConvSummary: No Supabase client, using empty data"
                )
                return self._get_empty_conversation_data()

            # Load conversation summary
            summary_response = (
                supabase.table("conversation_summaries")
                .select("*")
                .eq("session_id", session_id)
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )

            # Load conversation buffer (recent messages)
            buffer_response = (
                supabase.table("conversation_buffers")
                .select("*")
                .eq("session_id", session_id)
                .eq("user_id", user_id)
                .order("timestamp", desc=True)
                .limit(20)
                .execute()
            )

            # Get total message count for the session
            count_response = (
                supabase.table("conversation_buffers")
                .select("id", count="exact")
                .eq("session_id", session_id)
                .eq("user_id", user_id)
                .execute()
            )
            total_message_count = count_response.count or 0

            # Process summary
            summary = ""
            message_count = total_message_count  # Use actual total count from database
            total_chars = 0
            last_updated = datetime.now().isoformat()
            key_points = []
            topics = []

            if summary_response.data:
                latest_summary = summary_response.data[0]
                summary = latest_summary.get("summary", "")
                # Use database count, but update if summary has a higher count
                message_count = max(total_message_count, latest_summary.get("message_count", 0))
                total_chars = len(summary)
                last_updated = latest_summary.get("updated_at", last_updated)
                key_points = latest_summary.get("key_points", [])
                topics = latest_summary.get("topics", [])
                self.logger.info(
                    f"[Memory Node]: 🧠 ConvSummary: Loaded summary ({len(summary)} chars) with {len(key_points)} key points, {len(topics)} topics"
                )

            self.logger.info(
                f"[Memory Node]: 🧠 ConvSummary: Total messages in session: {message_count}"
            )

            # Process buffer (reverse order for chronological)
            buffer = []
            if buffer_response.data:
                for msg in reversed(buffer_response.data):  # Reverse to get chronological order
                    buffer.append(
                        {
                            "role": msg["role"],
                            "content": msg["content"],
                            "timestamp": msg["timestamp"],
                        }
                    )
                self.logger.info(
                    f"[Memory Node]: 🧠 ConvSummary: Loaded {len(buffer)} buffer messages"
                )

            return {
                "summary": summary,
                "buffer": buffer,
                "message_count": message_count,
                "last_updated": last_updated,
                "total_chars": total_chars,
                "key_points": key_points,
                "topics": topics,
            }

        except Exception as e:
            self.logger.error(f"[Memory Node]: 🧠 ConvSummary: Error loading from Supabase: {e}")
            return self._get_empty_conversation_data()

    def _get_empty_conversation_data(self) -> Dict[str, Any]:
        """Return empty conversation data structure."""
        return {
            "summary": "",
            "buffer": [],
            "message_count": 0,
            "last_updated": datetime.now().isoformat(),
            "total_chars": 0,
            "key_points": [],
            "topics": [],
        }

    def _format_summary_only_context(self, conv_data: Dict[str, Any], logs: List[str]) -> str:
        """Format conversation summary context WITHOUT recent messages (for system prompt only)."""
        summary = conv_data.get("summary", "")
        message_count = conv_data.get("message_count", 0)

        if not summary:
            return "No conversation summary available yet."

        # Only return the summary context, not recent messages
        context = f"## Conversation Summary ({message_count} total messages)\n\n{summary}"

        self.logger.info(
            f"[Memory Node]: 🧠 ConvSummary: 📝 Summary-only context formatted ({len(context)} chars)"
        )

        return context

    def _save_new_messages_to_supabase(
        self, session_id: str, user_id: str, new_messages: List[Dict[str, Any]]
    ) -> None:
        """Save only new messages to Supabase conversation_buffers table, avoiding duplicates."""
        try:
            supabase = self._get_supabase_client()
            if not supabase:
                self.logger.warning("[Memory Node]: 🧠 ConvSummary: No Supabase client, cannot save")
                return

            if not new_messages:
                return

            # Get existing messages for duplicate detection
            existing_messages_response = (
                supabase.table("conversation_buffers")
                .select("content, role, message_index")
                .eq("session_id", session_id)
                .eq("user_id", user_id)
                .order("message_index", desc=True)
                .limit(50)  # Check last 50 messages for duplicates
                .execute()
            )

            existing_messages = (
                existing_messages_response.data if existing_messages_response.data else []
            )
            existing_content_set = set()

            # Create a set of existing message content + role combinations for fast lookup
            for msg in existing_messages:
                existing_content_set.add((msg["content"].strip(), msg["role"]))

            # Get current max message_index for this session to append new messages
            next_index = 0
            if existing_messages:
                next_index = max(msg["message_index"] for msg in existing_messages) + 1

            # Filter out messages that already exist (same content + role)
            buffer_records = []
            messages_skipped = 0

            for msg in new_messages:
                content = msg["content"].strip()
                role = msg["role"]

                # Check if this exact message (content + role) already exists
                if (content, role) in existing_content_set:
                    messages_skipped += 1
                    self.logger.info(
                        f"[Memory Node]: 🧠 ConvSummary: Skipping duplicate message: {role} - {content[:50]}..."
                    )
                    continue

                buffer_records.append(
                    {
                        "session_id": session_id,
                        "user_id": user_id,
                        "message_index": next_index
                        + len(buffer_records),  # Use buffer_records length for sequential indexing
                        "role": role,
                        "content": content,
                        "timestamp": msg.get("timestamp", datetime.now().isoformat()),
                        "tokens_count": len(content.split()),  # Rough token estimate
                    }
                )

            if buffer_records:
                supabase.table("conversation_buffers").insert(buffer_records).execute()
                self.logger.info(
                    f"[Memory Node]: 🧠 ConvSummary: Saved {len(buffer_records)} new messages to Supabase"
                )

            if messages_skipped > 0:
                self.logger.info(
                    f"[Memory Node]: 🧠 ConvSummary: Skipped {messages_skipped} duplicate messages"
                )

        except Exception as e:
            self.logger.error(
                f"[Memory Node]: 🧠 ConvSummary: Error saving new messages to Supabase: {e}"
            )

    def _save_conversation_to_supabase(
        self,
        session_id: str,
        user_id: str,
        conv_data: Dict[str, Any],
        summarization_model: str = OpenAIModel.GPT_5_NANO.value,
    ) -> None:
        """Save conversation summary to Supabase tables (messages are saved separately)."""
        try:
            supabase = self._get_supabase_client()
            if not supabase:
                self.logger.warning("[Memory Node]: 🧠 ConvSummary: No Supabase client, cannot save")
                return

            # Save conversation summary if it exists
            summary = conv_data.get("summary", "")
            if summary:
                # Define maximum summary length (1500 characters for reasonable summaries)
                MAX_SUMMARY_LENGTH = 1500

                # If summary exceeds limit, truncate intelligently
                if len(summary) > MAX_SUMMARY_LENGTH:
                    self.logger.warning(
                        f"[Memory Node]: 🧠 ConvSummary: Summary too long ({len(summary)} chars), truncating to {MAX_SUMMARY_LENGTH}"
                    )
                    summary = self._truncate_summary_intelligently(summary, MAX_SUMMARY_LENGTH)

                summary_record = {
                    "session_id": session_id,
                    "user_id": user_id,
                    "summary": summary,
                    "summary_type": "progressive",
                    "message_count": conv_data.get("message_count", 0),
                    "token_count": len(summary.split()),  # Rough token estimate
                    "model_used": summarization_model,
                    "confidence_score": 0.8,  # Default confidence
                }

                # Use upsert to handle updates
                supabase.table("conversation_summaries").upsert(
                    summary_record, on_conflict="session_id,created_at"
                ).execute()
                self.logger.info(
                    f"[Memory Node]: 🧠 ConvSummary: Saved summary ({len(summary)} chars) to Supabase"
                )

        except Exception as e:
            self.logger.error(f"[Memory Node]: 🧠 ConvSummary: Error saving to Supabase: {e}")

    def _truncate_summary_intelligently(self, summary: str, max_length: int) -> str:
        """Intelligently truncate summary while preserving meaning."""
        if len(summary) <= max_length:
            return summary

        # Try to cut at sentence boundaries
        truncated = summary[:max_length]

        # Look for the last sentence boundary (period, exclamation, question mark)
        sentence_endings = [".", "!", "?"]
        last_sentence_end = -1

        for ending in sentence_endings:
            pos = truncated.rfind(ending)
            if pos > max_length * 0.7:  # Only if we can keep at least 70% of desired length
                last_sentence_end = max(last_sentence_end, pos)

        if last_sentence_end > 0:
            return truncated[: last_sentence_end + 1].strip()

        # If no good sentence boundary, look for last complete word
        last_space = truncated.rfind(" ")
        if last_space > max_length * 0.8:  # Only if we can keep at least 80% of desired length
            return truncated[:last_space].strip() + "..."

        # Fallback: hard truncate with ellipsis
        return truncated.rstrip() + "..."

    def _format_conversation_summary_context_with_buffer(
        self, conv_data: Dict[str, Any], buffer_window_size: int, logs: List[str]
    ) -> str:
        """Format conversation summary AND recent messages buffer for LLM consumption."""
        parts = []

        # Include summary if available
        summary = conv_data.get("summary", "")
        if summary:
            message_count = conv_data.get("message_count", 0)
            parts.append(f"## Conversation Summary ({message_count} total messages)")
            parts.append(summary)
            parts.append("")  # Empty line separator

        # Always include recent messages from buffer
        buffer = conv_data.get("buffer", [])
        if buffer:
            parts.append(f"## Recent Messages (Last {len(buffer)} messages)")
            for msg in buffer[-buffer_window_size:]:  # Ensure we don't exceed window size
                role = msg.get("role", "unknown").title()
                content = msg.get("content", "")
                if content:
                    parts.append(f"{role}: {content}")

            if not summary:
                parts.insert(
                    -len(buffer) - 1,
                    "No conversation summary available yet, showing recent messages:",
                )

        # If we have neither summary nor buffer, return empty state message
        if not parts:
            return "No conversation history available yet."

        formatted_context = "\n".join(parts)

        # Log detailed context being formatted for LLM
        self.logger.info(
            f"[Memory Node]: 🧠 ConvSummary: 🔄 Formatted context -> {len(formatted_context)} chars total"
        )

        # Show breakdown of what's included
        if summary:
            self.logger.info(
                f"[Memory Node]: 🧠 ConvSummary: 💡 Including summary: {len(summary)} chars"
            )

        if buffer:
            recent_messages = buffer[-buffer_window_size:]
            self.logger.info(
                f"[Memory Node]: 🧠 ConvSummary: 💬 Including {len(recent_messages)} recent messages"
            )

        # Show a preview of what's going to the LLM
        context_preview = (
            formatted_context[:200] + "..." if len(formatted_context) > 200 else formatted_context
        )
        self.logger.info(f"[Memory Node]: 🧠 ConvSummary: 🎯 LLM context preview: {context_preview}")

        return formatted_context

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
            f"[Memory Node]: 🧠 MEMORY NODE: Formatted knowledge base context ({len(formatted_context)} chars)"
        )
        return formatted_context

    def _execute_conversation_summary(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute conversation summary memory operations with proper buffer + summary support."""

        # Get parameters from node specification
        try:
            trigger_threshold = self.get_parameter_with_spec(context, "trigger_threshold")
        except (KeyError, AttributeError):
            trigger_threshold = 8

        try:
            buffer_window_size = self.get_parameter_with_spec(context, "buffer_window_size")
        except (KeyError, AttributeError):
            buffer_window_size = 6

        try:
            max_total_tokens = self.get_parameter_with_spec(context, "max_total_tokens")
        except (KeyError, AttributeError):
            max_total_tokens = 3000

        try:
            summary_style = self.get_parameter_with_spec(context, "summary_style")
        except (KeyError, AttributeError):
            summary_style = "progressive"

        try:
            summarization_model = self.get_parameter_with_spec(context, "summarization_model")
        except (KeyError, AttributeError):
            summarization_model = OpenAIModel.GPT_5_NANO.value

        # Use workflow_id and user_id as session_id for persistent storage
        session_id = (
            f"workflow_{context.workflow_id}"
            if context.workflow_id
            else f"execution_{context.execution_id}"
        )
        user_id = context.metadata.get("user_id", "system")

        self.logger.info(
            f"[Memory Node]: 🧠 ConvSummary: Using session_id: {session_id}, user_id: {user_id}"
        )
        self.logger.info(
            f"[Memory Node]: 🧠 ConvSummary: Config - threshold:{trigger_threshold}, buffer:{buffer_window_size}, model:{summarization_model}"
        )

        # Load conversation data from Supabase instead of in-memory storage
        conv_data = self._load_conversation_from_supabase(session_id, user_id)

        # Log what input data we received to debug different call patterns
        input_keys = list(context.input_data.keys()) if context.input_data else []
        self.logger.info(f"[Memory Node]: 🧠 ConvSummary: Input keys: {input_keys}")

        try:
            # Handle new conversation data (storing to conversation)
            conversation_data_provided = False
            if context.input_data:
                # Pattern 1: Direct user_message + ai_response (from AI Agent execution)
                if "user_message" in context.input_data and "ai_response" in context.input_data:
                    conversation_data_provided = True
                    user_msg = context.input_data["user_message"]
                    ai_response = context.input_data["ai_response"]

                    # Create new message objects
                    new_messages = [
                        {
                            "role": "user",
                            "content": user_msg,
                            "timestamp": datetime.now().isoformat(),
                        },
                        {
                            "role": "assistant",
                            "content": ai_response,
                            "timestamp": datetime.now().isoformat(),
                        },
                    ]

                    # Save new messages to Supabase immediately
                    self._save_new_messages_to_supabase(session_id, user_id, new_messages)

                    # Add to buffer and update counts
                    conv_data["buffer"].extend(new_messages)
                    conv_data["message_count"] += 2

                    # Log detailed content being stored
                    user_preview = user_msg[:80] + "..." if len(user_msg) > 80 else user_msg
                    ai_preview = ai_response[:80] + "..." if len(ai_response) > 80 else ai_response

                    self.logger.info(
                        f"[Memory Node]: 🧠 ConvSummary: Added exchange -> buffer:{len(conv_data['buffer'])}, total:{conv_data['message_count']}"
                    )
                    self.logger.info(f"[Memory Node]: 🧠 ConvSummary: 📥 User: {user_preview}")
                    self.logger.info(f"[Memory Node]: 🧠 ConvSummary: 🤖 AI: {ai_preview}")

                # Pattern 2: Messages array format
                elif context.input_data.get("messages"):
                    conversation_data_provided = True
                    # Handle messages array format
                    new_messages = context.input_data["messages"]
                    for msg in new_messages:
                        conv_data["buffer"].append(
                            {
                                "role": msg.get("role", "user"),
                                "content": msg.get("content", ""),
                                "timestamp": msg.get("timestamp", datetime.now().isoformat()),
                            }
                        )
                    conv_data["message_count"] += len(new_messages)

                    self.logger.info(
                        f"[Memory Node]: 🧠 ConvSummary: Added {len(new_messages)} msgs -> buffer:{len(conv_data['buffer'])}, total:{conv_data['message_count']}"
                    )

                # Pattern 3: Trigger/content data (extract user message from content)
                elif "content" in context.input_data and "trigger_type" in context.input_data.get(
                    "metadata", {}
                ):
                    conversation_data_provided = True
                    content = context.input_data["content"]
                    trigger_type = context.input_data["metadata"].get("trigger_type", "unknown")

                    # Clean user message based on trigger type
                    user_msg = content
                    if trigger_type == "slack" and "<@" in content:
                        # Remove Slack mention formatting to get clean user message
                        import re

                        user_msg = re.sub(r"<@[^>]+>", "", content).strip()

                    # Store as a user message (no AI response yet)
                    new_messages = [
                        {
                            "role": "user",
                            "content": user_msg,
                            "timestamp": datetime.now().isoformat(),
                        }
                    ]

                    # Save new messages to Supabase immediately
                    self._save_new_messages_to_supabase(session_id, user_id, new_messages)

                    # Add to buffer and update counts
                    conv_data["buffer"].extend(new_messages)
                    conv_data["message_count"] += 1

                    self.logger.info(
                        f"[Memory Node]: 🧠 ConvSummary: Added {trigger_type} trigger msg -> buffer:{len(conv_data['buffer'])}, total:{conv_data['message_count']}"
                    )
                    self.logger.info(
                        f"[Memory Node]: 🧠 ConvSummary: 📥 User (from {trigger_type}): {user_msg}"
                    )

                # Pattern 4: Action-based call (e.g., memory loading) - no conversation data
                elif context.input_data.get("action") or context.input_data.get("memory"):
                    self.logger.info(
                        f"[Memory Node]: 🧠 ConvSummary: Action/memory call - retrieving existing memory"
                    )
                    # No new conversation data to store, just return existing memory

                # Pattern 4: Any other input patterns - log for debugging but don't fail
                else:
                    self.logger.info(
                        f"[Memory Node]: 🧠 ConvSummary: No recognized conversation pattern in input - returning current memory state"
                    )

                # Only do buffer maintenance and summarization if we added new conversation data
                if conversation_data_provided:
                    # Maintain buffer window size
                    if len(conv_data["buffer"]) > buffer_window_size:
                        # Remove older messages beyond buffer size
                        removed_count = len(conv_data["buffer"]) - buffer_window_size
                        conv_data["buffer"] = conv_data["buffer"][-buffer_window_size:]
                        self.logger.info(
                            f"[Memory Node]: 🧠 ConvSummary: Trimmed {removed_count} old msgs -> buffer:{len(conv_data['buffer'])}"
                        )

                    # Check if we should generate a summary
                    if conv_data["message_count"] >= trigger_threshold:
                        self.logger.info(
                            f"[Memory Node]: 🧠 ConvSummary: ⚡ SUMMARIZING at {datetime.now().strftime('%H:%M:%S')} - {conv_data['message_count']} msgs >= {trigger_threshold}"
                        )

                        # Generate summary from all conversation history
                        all_messages = conv_data["buffer"]
                        if all_messages:
                            # Generate AI-powered summary using Gemini
                            conversation_text = "\n".join(
                                [f"{msg['role']}: {msg['content']}" for msg in all_messages]
                            )

                            # Generate new summary using AI-powered method
                            summary_result = self._generate_conversation_summary_with_metadata(
                                conversation_text, max_total_tokens // 2, summary_style, logs
                            )
                            logs.append(
                                f"[Memory Node]: 🧠 ConvSummary: Generated summary with AI metadata"
                            )

                            conv_data["summary"] = summary_result["summary"]
                            conv_data["key_points"] = summary_result.get("key_points", [])
                            conv_data["topics"] = summary_result.get("topics", [])
                            conv_data["total_chars"] = len(summary_result["summary"])

                            # Log summary preview for debugging
                            summary_preview = (
                                summary_result["summary"][:100] + "..."
                                if len(summary_result["summary"]) > 100
                                else summary_result["summary"]
                            )
                            self.logger.info(
                                f"[Memory Node]: 🧠 ConvSummary: ✅ Summary generated ({len(summary_result['summary'])} chars): {summary_preview}"
                            )

                    conv_data["last_updated"] = datetime.now().isoformat()

                    # Save to Supabase after adding new conversation data
                    self._save_conversation_to_supabase(
                        session_id, user_id, conv_data, summarization_model
                    )

            # Prepare structured data for AI agent consumption
            # 1. Summary context for system prompt enhancement (NO recent messages)
            summary_context = self._format_summary_only_context(conv_data, logs)

            # 2. Recent messages for chat history injection
            recent_messages = (
                conv_data["buffer"][-buffer_window_size:] if conv_data["buffer"] else []
            )

            # Format messages for AI API consumption (role/content structure)
            formatted_messages = []
            for msg in recent_messages:
                if msg.get("role") and msg.get("content"):
                    formatted_messages.append({"role": msg["role"], "content": msg["content"]})

            context_data = {
                "summary": conv_data["summary"],
                "key_points": conv_data.get("key_points", []),
                "entities": [],  # Note: Entity extraction not implemented in current AI summarization
                "topics": conv_data.get("topics", []),
                "buffer": recent_messages,  # Raw buffer data
                "messages": formatted_messages,  # Structured messages for chat history
                "message_count": conv_data["message_count"],
                "total_chars": conv_data["total_chars"],
                "last_updated": conv_data["last_updated"],
                "memory_type": MemorySubtype.CONVERSATION_SUMMARY.value,
                "memory_context": summary_context,  # ONLY summary, not recent messages
                "formatted_context": summary_context,  # ONLY summary, not recent messages
            }

            # Log what type of operation this was
            operation_type = "STORAGE" if conversation_data_provided else "RETRIEVAL"
            self.logger.info(
                f"[Memory Node]: 🧠 ConvSummary: 📤 {operation_type} - Summary for system prompt:{len(conv_data['summary'])} chars, Messages for chat history:{len(formatted_messages)} msgs"
            )

            # Show what content is being returned
            if conv_data["summary"]:
                summary_preview = (
                    conv_data["summary"][:120] + "..."
                    if len(conv_data["summary"]) > 120
                    else conv_data["summary"]
                )
                self.logger.info(
                    f"[Memory Node]: 🧠 ConvSummary: 📋 Summary content: {summary_preview}"
                )

            if formatted_messages:
                self.logger.info(f"[Memory Node]: 🧠 ConvSummary: 💬 Chat history messages for AI:")
                for i, msg in enumerate(formatted_messages[-3:]):  # Show last 3 messages
                    content_preview = (
                        msg["content"][:60] + "..." if len(msg["content"]) > 60 else msg["content"]
                    )
                    self.logger.info(
                        f"[Memory Node]: 🧠 ConvSummary:   {i+1}. {msg['role']}: {content_preview}"
                    )
            else:
                self.logger.info(f"[Memory Node]: 🧠 ConvSummary: 💬 No messages for chat history")

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
            f"[Memory Node]: 🧠 MEMORY NODE: Entity operation '{operation}' with backend: {storage_backend}"
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
                    f"[Memory Node]: 🧠 MEMORY NODE: Extracting entities from text ({len(text_input)} chars)"
                )
                extracted_entities = self._extract_entities_simple(text_input, logs)

                # Store extracted entities
                for entity in extracted_entities:
                    entity_id = entity["id"]
                    if entity_id not in entity_data["entities"]:
                        entity_data["entities"][entity_id] = entity
                        self.logger.info(
                            f"[Memory Node]: 🧠 MEMORY NODE: Added new entity: {entity['name']} ({entity['type']})"
                        )
                    else:
                        # Update existing entity
                        existing = entity_data["entities"][entity_id]
                        existing["mentions"] = existing.get("mentions", 0) + entity.get(
                            "mentions", 1
                        )
                        existing["last_seen"] = datetime.now().isoformat()
                        self.logger.info(
                            f"[Memory Node]: 🧠 MEMORY NODE: Updated entity: {entity['name']} (mentions: {existing['mentions']})"
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
                    f"[Memory Node]: 🧠 MEMORY NODE: Found {len(matching_entities)} entities matching query"
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
                    f"[Memory Node]: 🧠 MEMORY NODE: Added relationship: {entity1} --{relation_type}--> {entity2}"
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
                f"[Memory Node]: 🧠 MEMORY NODE: Knowledge operation '{operation}' with backend: {storage_backend}"
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
                    f"[Memory Node]: 🧠 MEMORY NODE: Added fact '{fact_text[:50]}...' to category '{category}'"
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
