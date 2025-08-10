"""
Memory Node Executor.

Handles memory operations like vector database, key-value storage, document storage, etc.
"""

import hashlib
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import BaseNodeExecutor, ExecutionStatus, NodeExecutionContext, NodeExecutionResult

try:
    from shared.node_specs import node_spec_registry
    from shared.node_specs.base import NodeSpec
except ImportError:
    node_spec_registry = None
    NodeSpec = None


class MemoryNodeExecutor(BaseNodeExecutor):
    """Executor for MEMORY_NODE type."""

    def __init__(self):
        super().__init__()
        # Mock memory storage
        self._vector_db = {}
        self._key_value_store = {}
        self._document_store = {}

    def _get_node_spec(self) -> Optional[NodeSpec]:
        """Get the node specification for memory nodes."""
        if node_spec_registry and self._subtype:
            # Return the specific spec for current subtype
            return node_spec_registry.get_spec("MEMORY_NODE", self._subtype)
        return None

    def get_supported_subtypes(self) -> List[str]:
        """Get supported memory subtypes."""
        return [
            "MEMORY_SIMPLE",
            "MEMORY_BUFFER",
            "MEMORY_KNOWLEDGE",
            "MEMORY_VECTOR_STORE",
            "MEMORY_DOCUMENT",
            "MEMORY_EMBEDDING",
        ]

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
        
        if not hasattr(node, 'subtype'):
            return errors
            
        subtype = node.subtype

        if subtype == "MEMORY_VECTOR_STORE":
            errors.extend(
                self._validate_required_parameters(node, ["operation", "collection_name"])
            )
            if hasattr(node, 'parameters'):
                operation = node.parameters.get("operation", "")
                if operation and operation not in ["store", "search", "delete", "update"]:
                    errors.append(f"Invalid vector DB operation: {operation}")

        elif subtype == "MEMORY_SIMPLE":
            errors.extend(self._validate_required_parameters(node, ["operation", "key"]))
            if hasattr(node, 'parameters'):
                operation = node.parameters.get("operation", "")
                if operation and operation not in ["get", "set", "delete", "exists"]:
                    errors.append(f"Invalid key-value operation: {operation}")

        elif subtype == "MEMORY_DOCUMENT":
            errors.extend(self._validate_required_parameters(node, ["operation", "document_id"]))
            if hasattr(node, 'parameters'):
                operation = node.parameters.get("operation", "")
                if operation and operation not in ["store", "retrieve", "update", "delete", "search"]:
                    errors.append(f"Invalid document operation: {operation}")

        return errors

    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute memory node."""
        start_time = time.time()
        logs = []

        try:
            subtype = context.node.subtype
            logs.append(f"Executing memory node with subtype: {subtype}")

            if subtype == "MEMORY_VECTOR_STORE":
                return self._execute_vector_db(context, logs, start_time)
            elif subtype == "MEMORY_SIMPLE":
                return self._execute_key_value(context, logs, start_time)
            elif subtype == "MEMORY_DOCUMENT":
                return self._execute_document(context, logs, start_time)
            elif subtype == "MEMORY_BUFFER":
                return self._execute_buffer(context, logs, start_time)
            elif subtype == "MEMORY_KNOWLEDGE":
                return self._execute_knowledge(context, logs, start_time)
            elif subtype == "MEMORY_EMBEDDING":
                return self._execute_embedding(context, logs, start_time)
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
        """Execute vector database operations."""
        # Use spec-based parameter retrieval
        operation = self.get_parameter_with_spec(context, "operation")
        collection_name = self.get_parameter_with_spec(context, "collection_name")

        logs.append(f"Vector DB: {operation} on collection {collection_name}")

        try:
            if operation == "store":
                vector_data = self.get_parameter_with_spec(context, "vector_data")
                metadata = self.get_parameter_with_spec(context, "metadata")
                result = self._store_vector(collection_name, vector_data, metadata)
            elif operation == "search":
                query_vector = self.get_parameter_with_spec(context, "query_vector")
                top_k = self.get_parameter_with_spec(context, "top_k")
                result = self._search_vectors(collection_name, query_vector, top_k)
            elif operation == "delete":
                vector_id = self.get_parameter_with_spec(context, "vector_id")
                result = self._delete_vector(collection_name, vector_id)
            elif operation == "update":
                vector_id = self.get_parameter_with_spec(context, "vector_id")
                vector_data = self.get_parameter_with_spec(context, "vector_data")
                metadata = self.get_parameter_with_spec(context, "metadata")
                result = self._update_vector(collection_name, vector_id, vector_data, metadata)
            else:
                result = {"error": f"Unknown operation: {operation}"}

            output_data = {
                "memory_type": "vector_db",
                "operation": operation,
                "collection_name": collection_name,
                "result": result,
                "success": "error" not in result,
                "executed_at": datetime.now().isoformat(),
            }

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

        logs.append(f"Key-Value: {operation} for key {key}")

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
                "memory_type": "key_value",
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
        """Execute document operations."""
        # Use spec-based parameter retrieval
        operation = self.get_parameter_with_spec(context, "operation")
        document_id = self.get_parameter_with_spec(context, "document_id")

        logs.append(f"Document: {operation} for document {document_id}")

        try:
            if operation == "store":
                document_data = self.get_parameter_with_spec(context, "document_data")
                result = self._store_document(document_id, document_data)
            elif operation == "retrieve":
                result = self._retrieve_document(document_id)
            elif operation == "update":
                document_data = self.get_parameter_with_spec(context, "document_data")
                result = self._update_document(document_id, document_data)
            elif operation == "delete":
                result = self._delete_document(document_id)
            elif operation == "search":
                query = self.get_parameter_with_spec(context, "query")
                result = self._search_documents(query)
            else:
                result = {"error": f"Unknown operation: {operation}"}

            output_data = {
                "memory_type": "document",
                "operation": operation,
                "document_id": document_id,
                "result": result,
                "success": "error" not in result,
                "executed_at": datetime.now().isoformat(),
            }

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

        logs.append(f"Buffer Memory: {operation} on buffer {buffer_name}")

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

        logs.append(f"Knowledge Memory: {operation} for {knowledge_id}")

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

        logs.append(f"Embedding Memory: {operation} using {embedding_model}")

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
