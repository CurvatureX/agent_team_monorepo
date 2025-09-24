"""
Workflow Validator - 共享的工作流验证逻辑.

This module provides shared validation logic for both ValidationService and EnhancedWorkflowExecutionEngine.
"""

import logging
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Set

# Import from nodes factory in new flat structure
try:
    from nodes.factory import NodeExecutorFactory

    get_node_executor_factory = lambda: NodeExecutorFactory
except ImportError:
    # Fallback for cases where nodes factory is not available
    get_node_executor_factory = lambda: None
from .node_id_generator import NodeIdGenerator

logger = logging.getLogger(__name__)


class WorkflowValidator:
    """Shared workflow validation logic."""

    def __init__(self):
        self.node_factory = get_node_executor_factory()

    def validate_workflow_structure(
        self, workflow_definition: Dict[str, Any], validate_node_parameters: bool = True
    ) -> Dict[str, Any]:
        """
        Validate workflow structure.

        Args:
            workflow_definition: Workflow definition dictionary
            validate_node_parameters: Whether to validate node parameters (can be expensive)

        Returns:
            Dict with validation results: {"valid": bool, "errors": List[str], "warnings": List[str]}
        """
        errors = []
        warnings = []

        nodes = workflow_definition.get("nodes", [])
        connections = workflow_definition.get("connections", {})

        # DEBUG: Log the exact nodes being validated
        print(f"🐛 DEBUG: validate_workflow_structure called with {len(nodes)} nodes")
        for i, node in enumerate(nodes):
            print(
                f"🐛 DEBUG: Node {i}: id='{node.get('id')}', type='{node.get('type')}', subtype='{node.get('subtype')}'"
            )
        print(f"🐛 DEBUG: validate_node_parameters = {validate_node_parameters}")

        # Basic workflow validation
        if not nodes:
            errors.append("Workflow must have at least one node")
            return {"valid": False, "errors": errors, "warnings": warnings}

        # Node validation
        node_validation = self._validate_nodes(nodes, validate_node_parameters)
        errors.extend(node_validation["errors"])
        warnings.extend(node_validation["warnings"])

        # ConnectionsMap validation
        if connections:
            connection_errors = self._validate_connections_map(
                connections, node_validation["node_ids"]
            )
            errors.extend(connection_errors)

        # Check for circular dependencies
        if not errors:  # Only check if basic validation passes
            if self._has_circular_dependencies(nodes, connections):
                errors.append("Workflow contains circular dependencies")

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    def _validate_nodes(
        self, nodes: List[Dict[str, Any]], validate_parameters: bool = True
    ) -> Dict[str, Any]:
        """Validate nodes in workflow."""
        errors = []
        warnings = []
        node_ids = set()
        node_names = set()

        for node in nodes:
            node_id = node.get("id")
            node_name = node.get("name")

            # Basic node validation
            if not node_id:
                errors.append("Node missing ID")
                continue

            if not node_name:
                errors.append(f"Node {node_id} missing name")
                continue

            # Validate node ID format
            if not NodeIdGenerator.is_valid_node_id(node_id):
                errors.append(
                    f"Invalid node ID format: {node_id}. IDs must start with a letter or underscore, and contain only letters, numbers, underscores, and hyphens."
                )

            if node_id in node_ids:
                errors.append(f"Duplicate node ID: {node_id}")
            node_ids.add(node_id)

            if node_name in node_names:
                errors.append(f"Duplicate node name: {node_name}")
            node_names.add(node_name)

            # Node type validation
            node_type = node.get("type")
            if not node_type:
                errors.append(f"Node {node_id} missing type")
                continue

            # Get executor and validate
            node_subtype = node.get("subtype", "")
            print(
                f"🐛 DEBUG: Processing node {node_id} with type='{node_type}', subtype='{node_subtype}'"
            )
            try:
                executor = self.node_factory.create_executor(node_type, node_subtype)
                if not executor:
                    errors.append(
                        f"No executor found for node type: {node_type}, subtype: {node_subtype}"
                    )
                    continue

                print(
                    f"🐛 DEBUG: Created executor for {node_id}, executor subtype: {executor._subtype}"
                )

                # Validate node parameters if requested
                if validate_parameters:
                    node_obj = self._dict_to_node_object(node)
                    print(
                        f"🐛 DEBUG: Created node object for {node_id} with type='{node_obj.type}', subtype='{node_obj.subtype}'"
                    )
                    node_errors = executor.validate(node_obj)
                    for error in node_errors:
                        errors.append(f"Node {node_id}: {error}")

            except Exception as e:
                errors.append(f"Node {node_id}: Error validating node - {str(e)}")

        return {
            "errors": errors,
            "warnings": warnings,
            "node_ids": node_ids,
            "node_names": node_names,
        }

    def _validate_connections_map(
        self, connections: Dict[str, Any], node_ids: Set[str]
    ) -> List[str]:
        """Validate ConnectionsMap structure using node IDs."""
        errors = []

        # Get connections dict from ConnectionsMap
        connections_dict = connections.get("connections", {})

        # Valid connection types
        valid_connection_types = [
            "main",
            "ai_agent",
            "ai_chain",
            "ai_document",
            "ai_embedding",
            "ai_language_model",
            "ai_memory",
            "ai_output_parser",
            "ai_retriever",
            "ai_reranker",
            "ai_text_splitter",
            "ai_tool",
            "ai_vector_store",
        ]

        for source_node_id, node_connections in connections_dict.items():
            if source_node_id not in node_ids:
                errors.append(f"Connection source node ID '{source_node_id}' does not exist")
                continue

            # Validate connection types
            connection_types = node_connections.get("connection_types", {})
            for connection_type, connection_array in connection_types.items():
                if connection_type not in valid_connection_types:
                    errors.append(f"Invalid connection type: {connection_type}")
                    continue

                connections_list = connection_array.get("connections", [])
                for connection in connections_list:
                    target_node_id = connection.get("node")
                    if target_node_id not in node_ids:
                        errors.append(
                            f"Connection target node ID '{target_node_id}' does not exist"
                        )

                    # Validate connection type enum
                    conn_type = connection.get("type")
                    if conn_type is not None:
                        valid_types = [
                            "MAIN",
                            "AI_AGENT",
                            "AI_CHAIN",
                            "AI_DOCUMENT",
                            "AI_EMBEDDING",
                            "AI_LANGUAGE_MODEL",
                            "AI_MEMORY",
                            "AI_OUTPUT_PARSER",
                            "AI_RETRIEVER",
                            "AI_RERANKER",
                            "AI_TEXT_SPLITTER",
                            "AI_TOOL",
                            "AI_VECTOR_STORE",
                        ]
                        if conn_type not in valid_types:
                            errors.append(f"Invalid connection type: {conn_type}")

                    # Validate index
                    index = connection.get("index")
                    if index is not None and index < 0:
                        errors.append(f"Connection index must be non-negative: {index}")

        return errors

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

            for neighbor in graph.get(node_id, []):
                if has_cycle(neighbor):
                    return True

            rec_stack.remove(node_id)
            return False

        for node_id in graph:
            if node_id not in visited:
                if has_cycle(node_id):
                    return True

        return False

    def _dict_to_node_object(self, node_dict: Dict[str, Any]) -> Any:
        """Convert dictionary to node object for validation."""

        class NodeObject:
            def __init__(self, data):
                self.id = data.get("id", "")
                self.name = data.get("name", "")
                self.type = data.get("type", "")
                self.subtype = data.get("subtype", "")
                self.parameters = data.get("parameters", {})
                self.credentials = data.get("credentials", {})
                self.disabled = data.get("disabled", False)
                self.on_error = data.get("on_error", "STOP_WORKFLOW_ON_ERROR")

        return NodeObject(node_dict)

    def validate_single_node(
        self, node_definition: Dict[str, Any], input_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Validate a single node configuration.

        Args:
            node_definition: Node definition dictionary
            input_data: Optional input data for testing

        Returns:
            Dict with validation results
        """
        errors = []
        warnings = []

        # Basic node validation
        if not node_definition.get("id"):
            errors.append("Node ID is required")

        if not node_definition.get("name"):
            errors.append("Node name is required")

        node_type = node_definition.get("type")
        if not node_type:
            errors.append("Node type is required")
        else:
            # Validate node type and get executor
            node_subtype = node_definition.get("subtype", "")
            try:
                executor = self.node_factory.create_executor(node_type, node_subtype)
                if not executor:
                    errors.append(f"No executor found for node type: {node_type}")
                else:
                    # Validate node configuration
                    node_obj = self._dict_to_node_object(node_definition)
                    node_errors = executor.validate(node_obj)
                    errors.extend(node_errors)

            except Exception as e:
                errors.append(f"Error validating node: {str(e)}")

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}
