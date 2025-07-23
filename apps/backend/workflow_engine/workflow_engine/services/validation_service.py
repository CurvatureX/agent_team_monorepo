"""
Validation Service - 工作流验证和调试服务.

This module implements workflow validation and debugging operations with ConnectionsMap support.
"""

import logging
from typing import Dict, Any, List, Set

import grpc

logger = logging.getLogger(__name__)
settings = get_settings()


class ValidationService:
    """Service for workflow validation and debugging operations with ConnectionsMap support."""

    def __init__(self):
        self.logger = logger
        self.node_factory = NodeExecutorFactory()

    def validate_workflow(
        self, 
        request: workflow_service_pb2.ValidateWorkflowRequest, 
        context: grpc.ServicerContext
    ) -> workflow_service_pb2.ValidateWorkflowResponse:
        """Validate a workflow with ConnectionsMap support."""
        try:
            self.logger.info(f"Validating workflow: {request.workflow.name}")
            
            errors = []
            warnings = []
            
            # Basic workflow validation
            if not request.workflow.name:
                errors.append("Workflow name is required")
            
            if not request.workflow.nodes:
                errors.append("Workflow must have at least one node")
            
            # Node validation
            node_ids = set()
            node_names = set()
            for node in request.workflow.nodes:
                if not node.id:
                    errors.append("Node ID is required")
                    continue
                    
                if not node.name:
                    errors.append(f"Node {node.id} name is required")
                    continue
                    
                if node.id in node_ids:
                    errors.append(f"Duplicate node ID: {node.id}")
                else:
                    node_ids.add(node.id)
                
                if node.name in node_names:
                    errors.append(f"Duplicate node name: {node.name}")
                else:
                    node_names.add(node.name)
                
                # Validate node type and subtype
                if not node.type:
                    errors.append(f"Node {node.id}: Node type is required")
                    continue
                
                try:
                    executor = self.node_factory.get_executor(node.type, node.subtype)
                    # Validate node parameters
                    validation_result = executor.validate_parameters(dict(node.parameters))
                    if not validation_result.get("valid", True):
                        errors.extend([f"Node {node.id}: {error}" for error in validation_result.get("errors", [])])
                        warnings.extend([f"Node {node.id}: {warning}" for warning in validation_result.get("warnings", [])])
                except Exception as e:
                    errors.append(f"Node {node.id}: Invalid node type/subtype - {str(e)}")
            
            # ConnectionsMap validation
            if request.workflow.connections:
                connection_errors = self._validate_connections_map(request.workflow.connections, node_names)
                errors.extend(connection_errors)
            
            # Check for circular dependencies
            if not errors:  # Only check if basic validation passes
                circular_deps = self._check_circular_dependencies(request.workflow)
                if circular_deps:
                    errors.extend(circular_deps)
            
            is_valid = len(errors) == 0
            
            return workflow_service_pb2.ValidateWorkflowResponse(
                valid=is_valid,
                errors=errors,
                warnings=warnings,
                message="Workflow validation completed"
            )
            
        except Exception as e:
            self.logger.error(f"Error validating workflow: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to validate workflow: {str(e)}")
            return workflow_service_pb2.ValidateWorkflowResponse(
                valid=False,
                errors=[f"Validation error: {str(e)}"],
                warnings=[],
                message="Validation failed"
            )

    def _validate_connections_map(self, connections_map: workflow_pb2.ConnectionsMap, node_names: Set[str]) -> List[str]:
        """Validate ConnectionsMap structure."""
        errors = []
        
        # Valid connection types
        valid_connection_types = [
            "main", "ai_agent", "ai_chain", "ai_document", "ai_embedding",
            "ai_language_model", "ai_memory", "ai_output_parser", "ai_retriever",
            "ai_reranker", "ai_text_splitter", "ai_tool", "ai_vector_store"
        ]
        
        for source_node_name, node_connections in connections_map.connections.items():
            if source_node_name not in node_names:
                errors.append(f"Connection source node '{source_node_name}' does not exist")
                continue
            
            # Validate connection types
            for connection_type, connection_array in node_connections.connection_types.items():
                if connection_type not in valid_connection_types:
                    errors.append(f"Invalid connection type: {connection_type}")
                    continue
                
                for connection in connection_array.connections:
                    target_node_name = connection.node
                    if target_node_name not in node_names:
                        errors.append(f"Connection target node '{target_node_name}' does not exist")
                    
                    # Validate connection index
                    if connection.index < 0:
                        errors.append(f"Connection index must be non-negative: {connection.index}")
                    
                    # Validate connection type enum
                    if connection.type:
                        # Check if the connection type is valid
                        valid_enum_types = [
                            workflow_pb2.ConnectionType.MAIN,
                            workflow_pb2.ConnectionType.AI_AGENT,
                            workflow_pb2.ConnectionType.AI_CHAIN,
                            workflow_pb2.ConnectionType.AI_DOCUMENT,
                            workflow_pb2.ConnectionType.AI_EMBEDDING,
                            workflow_pb2.ConnectionType.AI_LANGUAGE_MODEL,
                            workflow_pb2.ConnectionType.AI_MEMORY,
                            workflow_pb2.ConnectionType.AI_OUTPUT_PARSER,
                            workflow_pb2.ConnectionType.AI_RETRIEVER,
                            workflow_pb2.ConnectionType.AI_RERANKER,
                            workflow_pb2.ConnectionType.AI_TEXT_SPLITTER,
                            workflow_pb2.ConnectionType.AI_TOOL,
                            workflow_pb2.ConnectionType.AI_VECTOR_STORE
                        ]
                        if connection.type not in valid_enum_types:
                            errors.append(f"Invalid connection type enum: {connection.type}")
        
        return errors

    def test_node(
        self, 
        request: workflow_service_pb2.TestNodeRequest, 
        context: grpc.ServicerContext
    ) -> workflow_service_pb2.TestNodeResponse:
        """Test a single node."""
        try:
            self.logger.info(f"Testing node: {request.node.id}")
            
            # Get node executor
            try:
                executor = self.node_factory.get_executor(request.node.type, request.node.subtype)
            except Exception as e:
                return workflow_service_pb2.TestNodeResponse(
                    success=False,
                    error=f"Invalid node type/subtype: {str(e)}",
                    message="Node test failed"
                )
            
            # Create execution context
            context_data = NodeExecutionContext(
                node=request.node,
                workflow_id="test",
                execution_id="test",
                input_data=dict(request.input_data),
                parameters=dict(request.node.parameters),
                static_data=dict(request.static_data) if request.static_data else {},
                credentials=dict(request.credentials) if request.credentials else {},
                metadata={}
            )
            
            # Execute node
            result = executor.execute(context_data)
            
            # Convert result to response
            success = result.status == ExecutionStatus.SUCCESS
            
            return workflow_service_pb2.TestNodeResponse(
                success=success,
                output_data=result.output_data,
                error=result.error_message if result.error_message else "",
                execution_time=result.execution_time,
                message=f"Node test {'completed' if success else 'failed'}"
            )
            
        except Exception as e:
            self.logger.error(f"Error testing node: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to test node: {str(e)}")
            return workflow_service_pb2.TestNodeResponse(
                success=False,
                error=f"Test error: {str(e)}",
                message="Node test failed"
            )

    def _check_circular_dependencies(self, workflow: workflow_pb2.Workflow) -> List[str]:
        """Check for circular dependencies in workflow with ConnectionsMap support."""
        errors = []
        
        if not workflow.connections:
            return errors
        
        # Build adjacency list using node names
        graph = {}
        name_to_id = {}
        
        for node in workflow.nodes:
            name_to_id[node.name] = node.id
            graph[node.id] = []
        
        # Build graph from ConnectionsMap
        for source_node_name, node_connections in workflow.connections.connections.items():
            source_node_id = name_to_id.get(source_node_name)
            if not source_node_id:
                continue
                
            for connection_type, connection_array in node_connections.connection_types.items():
                for connection in connection_array.connections:
                    target_node_name = connection.node
                    target_node_id = name_to_id.get(target_node_name)
                    
                    if target_node_id:
                        graph[source_node_id].append(target_node_id)
        
        # DFS to detect cycles
        visited = set()
        rec_stack = set()
        
        def has_cycle(node_id: str) -> bool:
            if node_id in rec_stack:
                return True
            if node_id in visited:
                return False
            
            visited.add(node_id)
            rec_stack.add(node_id)
            
            for neighbor in graph.get(node_id, []):
                if has_cycle(neighbor):
                    return True
            
            rec_stack.remove(node_id)
            return False
        
        for node_id in graph:
            if node_id not in visited:
                if has_cycle(node_id):
                    errors.append(f"Circular dependency detected involving node: {node_id}")
                    break
        
        return errors 