"""
Memory Node Executor.

Handles memory operations like vector database, key-value storage, document storage, etc.
"""

import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
import hashlib

from .base import BaseNodeExecutor, NodeExecutionContext, NodeExecutionResult, ExecutionStatus


class MemoryNodeExecutor(BaseNodeExecutor):
    """Executor for MEMORY_NODE type."""
    
    def __init__(self):
        super().__init__()
        # Mock memory storage
        self._vector_db = {}
        self._key_value_store = {}
        self._document_store = {}
    
    def get_supported_subtypes(self) -> List[str]:
        """Get supported memory subtypes."""
        return [
            "VECTOR_DB",
            "KEY_VALUE", 
            "DOCUMENT"
        ]
    
    def validate(self, node: Any) -> List[str]:
        """Validate memory node configuration."""
        errors = []
        
        if not node.subtype:
            errors.append("Memory subtype is required")
            return errors
        
        subtype = node.subtype
        
        if subtype == "VECTOR_DB":
            errors.extend(self._validate_required_parameters(node, ["operation", "collection_name"]))
            operation = node.parameters.get("operation", "")
            if operation not in ["store", "search", "delete", "update"]:
                errors.append(f"Invalid vector DB operation: {operation}")
        
        elif subtype == "KEY_VALUE":
            errors.extend(self._validate_required_parameters(node, ["operation", "key"]))
            operation = node.parameters.get("operation", "")
            if operation not in ["get", "set", "delete", "exists"]:
                errors.append(f"Invalid key-value operation: {operation}")
        
        elif subtype == "DOCUMENT":
            errors.extend(self._validate_required_parameters(node, ["operation", "document_id"]))
            operation = node.parameters.get("operation", "")
            if operation not in ["store", "retrieve", "update", "delete", "search"]:
                errors.append(f"Invalid document operation: {operation}")
        
        return errors
    
    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute memory node."""
        start_time = time.time()
        logs = []
        
        try:
            subtype = context.node.subtype
            logs.append(f"Executing memory node with subtype: {subtype}")
            
            if subtype == "VECTOR_DB":
                return self._execute_vector_db(context, logs, start_time)
            elif subtype == "KEY_VALUE":
                return self._execute_key_value(context, logs, start_time)
            elif subtype == "DOCUMENT":
                return self._execute_document(context, logs, start_time)
            else:
                return self._create_error_result(
                    f"Unsupported memory subtype: {subtype}",
                    execution_time=time.time() - start_time,
                    logs=logs
                )
        
        except Exception as e:
            return self._create_error_result(
                f"Error executing memory: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs
            )
    
    def _execute_vector_db(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute vector database operations."""
        operation = context.get_parameter("operation", "store")
        collection_name = context.get_parameter("collection_name", "default")
        
        logs.append(f"Vector DB: {operation} on collection {collection_name}")
        
        try:
            if operation == "store":
                vector_data = context.get_parameter("vector_data", {})
                metadata = context.get_parameter("metadata", {})
                result = self._store_vector(collection_name, vector_data, metadata)
            elif operation == "search":
                query_vector = context.get_parameter("query_vector", [])
                top_k = context.get_parameter("top_k", 5)
                result = self._search_vectors(collection_name, query_vector, top_k)
            elif operation == "delete":
                vector_id = context.get_parameter("vector_id", "")
                result = self._delete_vector(collection_name, vector_id)
            elif operation == "update":
                vector_id = context.get_parameter("vector_id", "")
                vector_data = context.get_parameter("vector_data", {})
                metadata = context.get_parameter("metadata", {})
                result = self._update_vector(collection_name, vector_id, vector_data, metadata)
            else:
                result = {"error": f"Unknown operation: {operation}"}
            
            output_data = {
                "memory_type": "vector_db",
                "operation": operation,
                "collection_name": collection_name,
                "result": result,
                "success": "error" not in result,
                "executed_at": datetime.now().isoformat()
            }
            
            return self._create_success_result(
                output_data=output_data,
                execution_time=time.time() - start_time,
                logs=logs
            )
            
        except Exception as e:
            return self._create_error_result(
                f"Error in vector DB operation: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs
            )
    
    def _execute_key_value(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute key-value operations."""
        operation = context.get_parameter("operation", "get")
        key = context.get_parameter("key", "")
        
        logs.append(f"Key-Value: {operation} for key {key}")
        
        try:
            if operation == "get":
                result = self._get_key_value(key)
            elif operation == "set":
                value = context.get_parameter("value", "")
                ttl = context.get_parameter("ttl", None)
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
                "executed_at": datetime.now().isoformat()
            }
            
            return self._create_success_result(
                output_data=output_data,
                execution_time=time.time() - start_time,
                logs=logs
            )
            
        except Exception as e:
            return self._create_error_result(
                f"Error in key-value operation: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs
            )
    
    def _execute_document(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute document operations."""
        operation = context.get_parameter("operation", "store")
        document_id = context.get_parameter("document_id", "")
        
        logs.append(f"Document: {operation} for document {document_id}")
        
        try:
            if operation == "store":
                document_data = context.get_parameter("document_data", {})
                result = self._store_document(document_id, document_data)
            elif operation == "retrieve":
                result = self._retrieve_document(document_id)
            elif operation == "update":
                document_data = context.get_parameter("document_data", {})
                result = self._update_document(document_id, document_data)
            elif operation == "delete":
                result = self._delete_document(document_id)
            elif operation == "search":
                query = context.get_parameter("query", "")
                result = self._search_documents(query)
            else:
                result = {"error": f"Unknown operation: {operation}"}
            
            output_data = {
                "memory_type": "document",
                "operation": operation,
                "document_id": document_id,
                "result": result,
                "success": "error" not in result,
                "executed_at": datetime.now().isoformat()
            }
            
            return self._create_success_result(
                output_data=output_data,
                execution_time=time.time() - start_time,
                logs=logs
            )
            
        except Exception as e:
            return self._create_error_result(
                f"Error in document operation: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs
            )
    
    def _store_vector(self, collection_name: str, vector_data: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Store vector in collection."""
        if collection_name not in self._vector_db:
            self._vector_db[collection_name] = []
        
        vector_id = f"vec_{len(self._vector_db[collection_name]) + 1}"
        vector_entry = {
            "id": vector_id,
            "vector": vector_data.get("vector", []),
            "metadata": metadata,
            "created_at": datetime.now().isoformat()
        }
        
        self._vector_db[collection_name].append(vector_entry)
        
        return {
            "vector_id": vector_id,
            "stored": True,
            "collection_size": len(self._vector_db[collection_name])
        }
    
    def _search_vectors(self, collection_name: str, query_vector: List[float], top_k: int) -> Dict[str, Any]:
        """Search vectors in collection."""
        if collection_name not in self._vector_db:
            return {"results": [], "count": 0}
        
        # Mock similarity search
        results = []
        for vector_entry in self._vector_db[collection_name][:top_k]:
            similarity = self._calculate_similarity(query_vector, vector_entry["vector"])
            results.append({
                "id": vector_entry["id"],
                "similarity": similarity,
                "metadata": vector_entry["metadata"]
            })
        
        return {
            "results": results,
            "count": len(results),
            "query_vector": query_vector
        }
    
    def _delete_vector(self, collection_name: str, vector_id: str) -> Dict[str, Any]:
        """Delete vector from collection."""
        if collection_name not in self._vector_db:
            return {"error": "Collection not found"}
        
        for i, vector_entry in enumerate(self._vector_db[collection_name]):
            if vector_entry["id"] == vector_id:
                del self._vector_db[collection_name][i]
                return {"deleted": True, "vector_id": vector_id}
        
        return {"error": "Vector not found"}
    
    def _update_vector(self, collection_name: str, vector_id: str, vector_data: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
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
            "ttl": ttl
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
            "created_at": datetime.now().isoformat()
        }
        return {"stored": True, "document_id": document_id}
    
    def _retrieve_document(self, document_id: str) -> Dict[str, Any]:
        """Retrieve document."""
        if document_id in self._document_store:
            return {
                "data": self._document_store[document_id]["data"],
                "found": True,
                "document_id": document_id
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
                results.append({
                    "document_id": doc_id,
                    "data": doc_data["data"]
                })
        
        return {
            "results": results,
            "count": len(results),
            "query": query
        }
    
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
