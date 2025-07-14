"""
Workflow Execution Engine.

Orchestrates the execution of workflows by managing node executors and handling
the execution flow based on workflow definitions with full ConnectionsMap support.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime
from collections import defaultdict, deque

from .nodes.factory import get_node_executor_factory, register_default_executors
from .nodes.base import NodeExecutionContext, NodeExecutionResult, ExecutionStatus
from .proto import workflow_pb2


class WorkflowExecutionEngine:
    """Main workflow execution engine with full ConnectionsMap support."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.factory = get_node_executor_factory()
        
        # Register all default executors
        register_default_executors()
        
        # Track execution state
        self.execution_states: Dict[str, Dict[str, Any]] = {}
        
    def execute_workflow(
        self, 
        workflow_id: str, 
        execution_id: str, 
        workflow_definition: Dict[str, Any],
        initial_data: Optional[Dict[str, Any]] = None,
        credentials: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a complete workflow with ConnectionsMap support."""
        
        self.logger.info(f"Starting workflow execution: {workflow_id} (execution: {execution_id})")
        
        # Initialize execution state
        execution_state = {
            "workflow_id": workflow_id,
            "execution_id": execution_id,
            "status": "running",
            "start_time": datetime.now().isoformat(),
            "nodes": workflow_definition.get("nodes", []),
            "connections": workflow_definition.get("connections", {}),
            "node_results": {},
            "execution_order": [],
            "errors": []
        }
        
        self.execution_states[execution_id] = execution_state
        
        try:
            # Validate workflow
            validation_errors = self._validate_workflow(workflow_definition)
            if validation_errors:
                execution_state["status"] = "error"
                execution_state["errors"] = validation_errors
                return execution_state
            
            # Calculate execution order
            execution_order = self._calculate_execution_order(workflow_definition)
            execution_state["execution_order"] = execution_order
            
            # Execute nodes in order
            for node_id in execution_order:
                node_result = self._execute_node(
                    node_id, 
                    workflow_definition, 
                    execution_state,
                    initial_data or {},
                    credentials or {}
                )
                
                execution_state["node_results"][node_id] = node_result
                
                # Stop execution if node failed and error handling requires it
                if node_result["status"] == "error":
                    node_def = self._get_node_by_id(workflow_definition, node_id)
                    if node_def:
                        error_handling = node_def.get("on_error", "STOP_WORKFLOW_ON_ERROR")
                        
                        if error_handling == "STOP_WORKFLOW_ON_ERROR":
                            execution_state["status"] = "error"
                            execution_state["errors"].append(f"Node {node_id} failed: {node_result.get('error_message', 'Unknown error')}")
                            break
            
            # Set final status
            if execution_state["status"] == "running":
                execution_state["status"] = "completed"
            
            execution_state["end_time"] = datetime.now().isoformat()
            
            self.logger.info(f"Workflow execution completed: {execution_id} (status: {execution_state['status']})")
            
            return execution_state
            
        except Exception as e:
            self.logger.error(f"Error executing workflow {workflow_id}: {str(e)}")
            execution_state["status"] = "error"
            execution_state["errors"].append(f"Execution error: {str(e)}")
            execution_state["end_time"] = datetime.now().isoformat()
            return execution_state
    
    def _validate_workflow(self, workflow_definition: Dict[str, Any]) -> List[str]:
        """Validate workflow definition with ConnectionsMap support."""
        errors = []
        
        nodes = workflow_definition.get("nodes", [])
        connections = workflow_definition.get("connections", {})
        
        if not nodes:
            errors.append("Workflow must have at least one node")
            return errors
        
        # Validate nodes
        node_ids = set()
        node_names = set()
        for node in nodes:
            node_id = node.get("id")
            node_name = node.get("name")
            
            if not node_id:
                errors.append("Node missing ID")
                continue
                
            if not node_name:
                errors.append(f"Node {node_id} missing name")
                continue
            
            if node_id in node_ids:
                errors.append(f"Duplicate node ID: {node_id}")
            node_ids.add(node_id)
            
            if node_name in node_names:
                errors.append(f"Duplicate node name: {node_name}")
            node_names.add(node_name)
            
            # Validate node type
            node_type = node.get("type")
            if not node_type:
                errors.append(f"Node {node_id} missing type")
                continue
            
            # Get executor and validate
            node_subtype = node.get("subtype", "")
            try:
                executor = self.factory.get_executor(node_type, node_subtype)
                if not executor:
                    errors.append(f"No executor found for node type: {node_type}")
                    continue
                
                # Validate node configuration - skip for now as it requires more complex setup
                # node_obj = self._dict_to_node_object(node)
                # node_errors = executor.validate(node_obj)
                # for error in node_errors:
                #     errors.append(f"Node {node_id}: {error}")
            except Exception as e:
                errors.append(f"Node {node_id}: Error validating node - {str(e)}")
        
        # Validate ConnectionsMap
        if connections:
            errors.extend(self._validate_connections_map(connections, node_names))
        
        # Check for circular dependencies
        if not errors:  # Only check if basic validation passes
            if self._has_circular_dependencies(nodes, connections):
                errors.append("Workflow contains circular dependencies")
        
        return errors
    
    def _validate_connections_map(self, connections: Dict[str, Any], node_names: Set[str]) -> List[str]:
        """Validate ConnectionsMap structure."""
        errors = []
        
        # Get connections dict from ConnectionsMap
        connections_dict = connections.get("connections", {})
        
        for source_node_name, node_connections in connections_dict.items():
            if source_node_name not in node_names:
                errors.append(f"Connection source node '{source_node_name}' does not exist")
                continue
            
            # Validate connection types
            connection_types = node_connections.get("connection_types", {})
            for connection_type, connection_array in connection_types.items():
                connections_list = connection_array.get("connections", [])
                
                for connection in connections_list:
                    target_node_name = connection.get("node")
                    if target_node_name not in node_names:
                        errors.append(f"Connection target node '{target_node_name}' does not exist")
                    
                    # Validate connection type
                    conn_type = connection.get("type")
                    if conn_type is not None:
                        valid_types = [
                            "MAIN", "AI_AGENT", "AI_CHAIN", "AI_DOCUMENT", "AI_EMBEDDING",
                            "AI_LANGUAGE_MODEL", "AI_MEMORY", "AI_OUTPUT_PARSER", "AI_RETRIEVER",
                            "AI_RERANKER", "AI_TEXT_SPLITTER", "AI_TOOL", "AI_VECTOR_STORE"
                        ]
                        if conn_type not in valid_types:
                            errors.append(f"Invalid connection type: {conn_type}")
                    
                    # Validate index
                    index = connection.get("index")
                    if index is not None and index < 0:
                        errors.append(f"Connection index must be non-negative: {index}")
        
        return errors
    
    def _calculate_execution_order(self, workflow_definition: Dict[str, Any]) -> List[str]:
        """Calculate execution order using topological sort with ConnectionsMap support."""
        
        nodes = workflow_definition.get("nodes", [])
        connections = workflow_definition.get("connections", {})
        
        # Build dependency graph using node names
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        
        # Create mapping from node names to IDs
        name_to_id = {}
        for node in nodes:
            node_id = node["id"]
            node_name = node["name"]
            name_to_id[node_name] = node_id
            in_degree[node_id] = 0
        
        # Build graph from ConnectionsMap
        connections_dict = connections.get("connections", {})
        for source_node_name, node_connections in connections_dict.items():
            source_node_id = name_to_id.get(source_node_name)
            if not source_node_id:
                continue
                
            connection_types = node_connections.get("connection_types", {})
            for connection_type, connection_array in connection_types.items():
                connections_list = connection_array.get("connections", [])
                
                for connection in connections_list:
                    target_node_name = connection.get("node")
                    target_node_id = name_to_id.get(target_node_name)
                    
                    if target_node_id:
                        graph[source_node_id].append(target_node_id)
                        in_degree[target_node_id] += 1
        
        # Topological sort using Kahn's algorithm
        queue = deque([node_id for node_id in in_degree if in_degree[node_id] == 0])
        execution_order = []
        
        while queue:
            current = queue.popleft()
            execution_order.append(current)
            
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return execution_order
    
    def _has_circular_dependencies(self, nodes: List[Dict], connections: Dict[str, Any]) -> bool:
        """Check if workflow has circular dependencies with ConnectionsMap support."""
        
        # Build adjacency list using node names
        graph = defaultdict(list)
        name_to_id = {}
        
        for node in nodes:
            node_id = node["id"]
            node_name = node["name"]
            name_to_id[node_name] = node_id
            graph[node_id] = []
        
        # Build graph from ConnectionsMap
        connections_dict = connections.get("connections", {})
        for source_node_name, node_connections in connections_dict.items():
            source_node_id = name_to_id.get(source_node_name)
            if not source_node_id:
                continue
                
            connection_types = node_connections.get("connection_types", {})
            for connection_type, connection_array in connection_types.items():
                connections_list = connection_array.get("connections", [])
                
                for connection in connections_list:
                    target_node_name = connection.get("node")
                    target_node_id = name_to_id.get(target_node_name)
                    
                    if target_node_id:
                        graph[source_node_id].append(target_node_id)
        
        # DFS to detect cycles
        visited = set()
        rec_stack = set()
        
        def has_cycle(node_id):
            if node_id in rec_stack:
                return True
            if node_id in visited:
                return False
            
            visited.add(node_id)
            rec_stack.add(node_id)
            
            for neighbor in graph[node_id]:
                if has_cycle(neighbor):
                    return True
            
            rec_stack.remove(node_id)
            return False
        
        # Check each node
        for node_id in graph:
            if node_id not in visited:
                if has_cycle(node_id):
                    return True
        
        return False
    
    def _execute_node(
        self,
        node_id: str,
        workflow_definition: Dict[str, Any],
        execution_state: Dict[str, Any],
        initial_data: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single node with ConnectionsMap support."""
        
        self.logger.info(f"Executing node: {node_id}")
        
        # Get node definition
        node_def = self._get_node_by_id(workflow_definition, node_id)
        if not node_def:
            return {
                "status": "error",
                "error_message": f"Node {node_id} not found in workflow definition"
            }
        
        # Get executor
        node_type = node_def["type"]
        node_subtype = node_def.get("subtype", "")
        executor = self.factory.get_executor(node_type, node_subtype)
        if not executor:
            return {
                "status": "error",
                "error_message": f"No executor found for node type: {node_type}"
            }
        
        # Prepare input data with connection type support
        input_data = self._prepare_node_input_data(node_id, workflow_definition, execution_state, initial_data)
        
        # Create execution context
        context = NodeExecutionContext(
            node=self._dict_to_node_object(node_def),
            workflow_id=execution_state["workflow_id"],
            execution_id=execution_state["execution_id"],
            input_data=input_data,
            static_data=workflow_definition.get("static_data", {}),
            credentials=credentials,
            metadata={"node_id": node_id}
        )
        
        try:
            # Execute node
            result = executor.execute(context)
            
            # Convert result to dict
            return {
                "status": result.status.value,
                "output_data": result.output_data,
                "error_message": result.error_message,
                "error_details": result.error_details,
                "execution_time": result.execution_time,
                "logs": result.logs,
                "metadata": result.metadata
            }
            
        except Exception as e:
            self.logger.error(f"Error executing node {node_id}: {str(e)}")
            return {
                "status": "error",
                "error_message": f"Execution error: {str(e)}",
                "output_data": {}
            }
    
    def _prepare_node_input_data(
        self, 
        node_id: str, 
        workflow_definition: Dict[str, Any], 
        execution_state: Dict[str, Any],
        initial_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare input data for a node based on ConnectionsMap."""
        
        connections = workflow_definition.get("connections", {})
        node_results = execution_state.get("node_results", {})
        
        # Get node name for this node_id
        node_name = None
        for node in workflow_definition.get("nodes", []):
            if node.get("id") == node_id:
                node_name = node.get("name")
                break
        
        if not node_name:
            return initial_data
        
        # Find incoming connections by looking for this node as a target
        incoming_connections = []
        connections_dict = connections.get("connections", {})
        
        for source_node_name, node_connections in connections_dict.items():
            connection_types = node_connections.get("connection_types", {})
            for connection_type, connection_array in connection_types.items():
                connections_list = connection_array.get("connections", [])
                
                for connection in connections_list:
                    if connection.get("node") == node_name:
                        # Find source node ID
                        source_node_id = None
                        for node in workflow_definition.get("nodes", []):
                            if node.get("name") == source_node_name:
                                source_node_id = node.get("id")
                                break
                        
                        if source_node_id:
                            incoming_connections.append({
                                "source_node_id": source_node_id,
                                "source_node_name": source_node_name,
                                "connection_type": connection_type,
                                "connection_info": connection
                            })
        
        # If no incoming connections, use initial data
        if not incoming_connections:
            return initial_data
        
        # Combine data from all incoming connections based on connection type
        combined_data = {}
        
        # Group connections by type
        connections_by_type = defaultdict(list)
        for conn in incoming_connections:
            connections_by_type[conn["connection_type"]].append(conn)
        
        # Process each connection type
        for connection_type, conns in connections_by_type.items():
            type_data = {}
            
            for conn in conns:
                source_node_id = conn["source_node_id"]
                if source_node_id in node_results:
                    source_result = node_results[source_node_id]
                    if source_result["status"] == "success":
                        output_data = source_result.get("output_data", {})
                        
                        # For MAIN connections, merge directly
                        if connection_type == "main":
                            combined_data.update(output_data)
                        else:
                            # For specialized connections, group by type
                            if connection_type not in combined_data:
                                combined_data[connection_type] = {}
                            combined_data[connection_type].update(output_data)
        
        # If no data was collected, return initial data
        if not combined_data:
            return initial_data
        
        return combined_data
    
    def _get_node_by_id(self, workflow_definition: Dict[str, Any], node_id: str) -> Optional[Dict[str, Any]]:
        """Get node definition by ID."""
        nodes = workflow_definition.get("nodes", [])
        for node in nodes:
            if node.get("id") == node_id:
                return node
        return None
    
    def _dict_to_node_object(self, node_dict: Dict[str, Any]) -> Any:
        """Convert node dictionary to node object for executor."""
        # Create a simple object that has the required attributes
        class NodeObject:
            def __init__(self, data):
                self.id = data.get("id")
                self.name = data.get("name", "")
                self.type = data.get("type")
                self.subtype = data.get("subtype", "")
                self.parameters = data.get("parameters", {})
                self.credentials = data.get("credentials", {})
                self.disabled = data.get("disabled", False)
                self.on_error = data.get("on_error", "STOP_WORKFLOW_ON_ERROR")
        
        return NodeObject(node_dict)
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get execution status."""
        return self.execution_states.get(execution_id)
    
    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel an execution."""
        if execution_id in self.execution_states:
            execution_state = self.execution_states[execution_id]
            if execution_state["status"] == "running":
                execution_state["status"] = "cancelled"
                execution_state["end_time"] = datetime.now().isoformat()
                return True
        return False
    
    def list_executions(self) -> List[Dict[str, Any]]:
        """List all executions."""
        return list(self.execution_states.values())
    
    def cleanup_execution(self, execution_id: str) -> bool:
        """Clean up execution state."""
        if execution_id in self.execution_states:
            del self.execution_states[execution_id]
            return True
        return False 