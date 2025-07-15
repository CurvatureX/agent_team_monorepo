"""
Memory Node Executor.

Handles various memory and storage operations including simple storage, buffers, 
knowledge graphs, vector stores, document storage, and embeddings.
"""

import json
import random
import time
from typing import Any, Dict, List, Optional
from datetime import datetime

from .base import BaseNodeExecutor, NodeExecutionContext, NodeExecutionResult, ExecutionStatus


class MemoryNodeExecutor(BaseNodeExecutor):
    """Executor for MEMORY_NODE type."""
    
    def get_supported_subtypes(self) -> List[str]:
        """Get supported memory subtypes."""
        return [
            "SIMPLE_STORAGE",
            "BUFFER",
            "KNOWLEDGE_GRAPH",
            "VECTOR_STORE",
            "DOCUMENT_STORAGE",
            "EMBEDDINGS"
        ]
    
    def validate(self, node: Any) -> List[str]:
        """Validate memory node configuration."""
        errors = []
        
        if not node.subtype:
            errors.append("Memory subtype is required")
            return errors
        
        subtype = node.subtype
        
        if subtype == "SIMPLE_STORAGE":
            errors.extend(self._validate_required_parameters(node, ["operation", "key"]))
        
        elif subtype == "BUFFER":
            errors.extend(self._validate_required_parameters(node, ["operation", "buffer_name"]))
        
        elif subtype == "KNOWLEDGE_GRAPH":
            errors.extend(self._validate_required_parameters(node, ["operation"]))
        
        elif subtype == "VECTOR_STORE":
            errors.extend(self._validate_required_parameters(node, ["operation", "collection_name"]))
        
        elif subtype == "DOCUMENT_STORAGE":
            errors.extend(self._validate_required_parameters(node, ["operation", "document_id"]))
        
        elif subtype == "EMBEDDINGS":
            errors.extend(self._validate_required_parameters(node, ["operation", "model_name"]))
        
        return errors
    
    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute memory node."""
        start_time = time.time()
        logs = []
        
        try:
            subtype = context.node.subtype
            logs.append(f"Executing memory node with subtype: {subtype}")
            
            if subtype == "SIMPLE_STORAGE":
                return self._execute_simple_storage(context, logs, start_time)
            elif subtype == "BUFFER":
                return self._execute_buffer(context, logs, start_time)
            elif subtype == "KNOWLEDGE_GRAPH":
                return self._execute_knowledge_graph(context, logs, start_time)
            elif subtype == "VECTOR_STORE":
                return self._execute_vector_store(context, logs, start_time)
            elif subtype == "DOCUMENT_STORAGE":
                return self._execute_document_storage(context, logs, start_time)
            elif subtype == "EMBEDDINGS":
                return self._execute_embeddings(context, logs, start_time)
            else:
                return self._create_error_result(
                    f"Unsupported memory subtype: {subtype}",
                    execution_time=time.time() - start_time,
                    logs=logs
                )
        
        except Exception as e:
            return self._create_error_result(
                f"Error executing memory operation: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs
            )
    
    def _execute_simple_storage(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute simple storage operation."""
        operation = context.get_parameter("operation")
        key = context.get_parameter("key")
        
        logs.append(f"Simple storage operation: {operation} for key: {key}")
        
        if operation == "store":
            value = context.input_data.get("value", "")
            ttl = context.get_parameter("ttl", None)  # Time to live in seconds
            
            result = {
                "operation": "store",
                "key": key,
                "value": value,
                "ttl": ttl,
                "stored_at": datetime.now().isoformat(),
                "success": True
            }
            
        elif operation == "retrieve":
            # Simulate retrieval
            result = {
                "operation": "retrieve",
                "key": key,
                "value": "Simulated stored value",
                "retrieved_at": datetime.now().isoformat(),
                "success": True
            }
            
        elif operation == "delete":
            result = {
                "operation": "delete",
                "key": key,
                "deleted_at": datetime.now().isoformat(),
                "success": True
            }
            
        elif operation == "exists":
            result = {
                "operation": "exists",
                "key": key,
                "exists": True,
                "checked_at": datetime.now().isoformat(),
                "success": True
            }
            
        else:
            result = {"operation": operation, "success": False, "error": "Unknown storage operation"}
        
        output_data = {
            "memory_type": "simple_storage",
            "operation": operation,
            "key": key,
            "result": result,
            "executed_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_buffer(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute buffer operation."""
        operation = context.get_parameter("operation")
        buffer_name = context.get_parameter("buffer_name")
        buffer_size = context.get_parameter("buffer_size", 100)
        
        logs.append(f"Buffer operation: {operation} on buffer: {buffer_name}")
        
        if operation == "push":
            item = context.input_data.get("item", "")
            result = {
                "operation": "push",
                "buffer_name": buffer_name,
                "item": item,
                "buffer_size": buffer_size,
                "current_size": 5,  # Simulated
                "pushed_at": datetime.now().isoformat(),
                "success": True
            }
            
        elif operation == "pop":
            result = {
                "operation": "pop",
                "buffer_name": buffer_name,
                "item": "Simulated popped item",
                "current_size": 4,  # Simulated
                "popped_at": datetime.now().isoformat(),
                "success": True
            }
            
        elif operation == "peek":
            result = {
                "operation": "peek",
                "buffer_name": buffer_name,
                "item": "Simulated top item",
                "current_size": 5,  # Simulated
                "peeked_at": datetime.now().isoformat(),
                "success": True
            }
            
        elif operation == "clear":
            result = {
                "operation": "clear",
                "buffer_name": buffer_name,
                "items_removed": 5,  # Simulated
                "cleared_at": datetime.now().isoformat(),
                "success": True
            }
            
        else:
            result = {"operation": operation, "success": False, "error": "Unknown buffer operation"}
        
        output_data = {
            "memory_type": "buffer",
            "operation": operation,
            "buffer_name": buffer_name,
            "result": result,
            "executed_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_knowledge_graph(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute knowledge graph operation."""
        operation = context.get_parameter("operation")
        
        logs.append(f"Knowledge graph operation: {operation}")
        
        if operation == "add_node":
            node_id = context.input_data.get("node_id", "")
            node_type = context.input_data.get("node_type", "")
            properties = context.input_data.get("properties", {})
            
            result = {
                "operation": "add_node",
                "node_id": node_id,
                "node_type": node_type,
                "properties": properties,
                "added_at": datetime.now().isoformat(),
                "success": True
            }
            
        elif operation == "add_edge":
            from_node = context.input_data.get("from_node", "")
            to_node = context.input_data.get("to_node", "")
            edge_type = context.input_data.get("edge_type", "")
            
            result = {
                "operation": "add_edge",
                "from_node": from_node,
                "to_node": to_node,
                "edge_type": edge_type,
                "added_at": datetime.now().isoformat(),
                "success": True
            }
            
        elif operation == "query":
            query = context.input_data.get("query", "")
            result = {
                "operation": "query",
                "query": query,
                "results": [
                    {"node_id": "node1", "type": "person", "properties": {"name": "John"}},
                    {"node_id": "node2", "type": "company", "properties": {"name": "Acme Corp"}}
                ],
                "count": 2,
                "queried_at": datetime.now().isoformat(),
                "success": True
            }
            
        elif operation == "find_path":
            start_node = context.input_data.get("start_node", "")
            end_node = context.input_data.get("end_node", "")
            
            result = {
                "operation": "find_path",
                "start_node": start_node,
                "end_node": end_node,
                "path": ["node1", "node2", "node3"],
                "path_length": 3,
                "found_at": datetime.now().isoformat(),
                "success": True
            }
            
        else:
            result = {"operation": operation, "success": False, "error": "Unknown knowledge graph operation"}
        
        output_data = {
            "memory_type": "knowledge_graph",
            "operation": operation,
            "result": result,
            "executed_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_vector_store(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute vector store operation."""
        operation = context.get_parameter("operation")
        collection_name = context.get_parameter("collection_name")
        
        logs.append(f"Vector store operation: {operation} on collection: {collection_name}")
        
        if operation == "store":
            vector_id = context.input_data.get("vector_id", "")
            vector = context.input_data.get("vector", [])
            metadata = context.input_data.get("metadata", {})
            
            result = {
                "operation": "store",
                "collection_name": collection_name,
                "vector_id": vector_id,
                "vector_dimension": len(vector),
                "metadata": metadata,
                "stored_at": datetime.now().isoformat(),
                "success": True
            }
            
        elif operation == "search":
            query_vector = context.input_data.get("query_vector", [])
            top_k = context.input_data.get("top_k", 10)
            
            result = {
                "operation": "search",
                "collection_name": collection_name,
                "query_vector_dimension": len(query_vector),
                "top_k": top_k,
                "results": [
                    {"vector_id": "vec1", "score": 0.95, "metadata": {"text": "Similar item 1"}},
                    {"vector_id": "vec2", "score": 0.87, "metadata": {"text": "Similar item 2"}},
                    {"vector_id": "vec3", "score": 0.82, "metadata": {"text": "Similar item 3"}}
                ],
                "searched_at": datetime.now().isoformat(),
                "success": True
            }
            
        elif operation == "delete":
            vector_id = context.input_data.get("vector_id", "")
            
            result = {
                "operation": "delete",
                "collection_name": collection_name,
                "vector_id": vector_id,
                "deleted_at": datetime.now().isoformat(),
                "success": True
            }
            
        else:
            result = {"operation": operation, "success": False, "error": "Unknown vector store operation"}
        
        output_data = {
            "memory_type": "vector_store",
            "operation": operation,
            "collection_name": collection_name,
            "result": result,
            "executed_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_document_storage(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute document storage operation."""
        operation = context.get_parameter("operation")
        document_id = context.get_parameter("document_id")
        
        logs.append(f"Document storage operation: {operation} for document: {document_id}")
        
        if operation == "store":
            content = context.input_data.get("content", "")
            document_type = context.input_data.get("document_type", "text")
            metadata = context.input_data.get("metadata", {})
            
            result = {
                "operation": "store",
                "document_id": document_id,
                "document_type": document_type,
                "content_length": len(content),
                "metadata": metadata,
                "stored_at": datetime.now().isoformat(),
                "success": True
            }
            
        elif operation == "retrieve":
            result = {
                "operation": "retrieve",
                "document_id": document_id,
                "content": "Simulated document content",
                "document_type": "text",
                "metadata": {"author": "system", "created": "2024-01-15"},
                "retrieved_at": datetime.now().isoformat(),
                "success": True
            }
            
        elif operation == "search":
            query = context.input_data.get("query", "")
            
            result = {
                "operation": "search",
                "query": query,
                "results": [
                    {
                        "document_id": "doc1",
                        "title": "Document 1",
                        "snippet": "This document contains relevant information...",
                        "score": 0.95
                    },
                    {
                        "document_id": "doc2",
                        "title": "Document 2",
                        "snippet": "Another relevant document...",
                        "score": 0.87
                    }
                ],
                "count": 2,
                "searched_at": datetime.now().isoformat(),
                "success": True
            }
            
        elif operation == "delete":
            result = {
                "operation": "delete",
                "document_id": document_id,
                "deleted_at": datetime.now().isoformat(),
                "success": True
            }
            
        else:
            result = {"operation": operation, "success": False, "error": "Unknown document storage operation"}
        
        output_data = {
            "memory_type": "document_storage",
            "operation": operation,
            "document_id": document_id,
            "result": result,
            "executed_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_embeddings(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute embeddings operation."""
        operation = context.get_parameter("operation")
        model_name = context.get_parameter("model_name")
        
        logs.append(f"Embeddings operation: {operation} using model: {model_name}")
        
        if operation == "generate":
            text = context.input_data.get("text", "")
            
            # Simulate embedding generation
            import random
            embedding = [random.random() for _ in range(384)]  # Simulated 384-dimensional embedding
            
            result = {
                "operation": "generate",
                "model_name": model_name,
                "text": text,
                "embedding": embedding,
                "embedding_dimension": len(embedding),
                "generated_at": datetime.now().isoformat(),
                "success": True
            }
            
        elif operation == "similarity":
            text1 = context.input_data.get("text1", "")
            text2 = context.input_data.get("text2", "")
            
            # Simulate similarity calculation
            similarity_score = random.uniform(0.5, 0.99)
            
            result = {
                "operation": "similarity",
                "model_name": model_name,
                "text1": text1,
                "text2": text2,
                "similarity_score": similarity_score,
                "calculated_at": datetime.now().isoformat(),
                "success": True
            }
            
        elif operation == "batch_generate":
            texts = context.input_data.get("texts", [])
            
            # Simulate batch embedding generation
            embeddings = []
            for text in texts:
                embedding = [random.random() for _ in range(384)]
                embeddings.append({"text": text, "embedding": embedding})
            
            result = {
                "operation": "batch_generate",
                "model_name": model_name,
                "batch_size": len(texts),
                "embeddings": embeddings,
                "embedding_dimension": 384,
                "generated_at": datetime.now().isoformat(),
                "success": True
            }
            
        else:
            result = {"operation": operation, "success": False, "error": "Unknown embeddings operation"}
        
        output_data = {
            "memory_type": "embeddings",
            "operation": operation,
            "model_name": model_name,
            "result": result,
            "executed_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        ) 