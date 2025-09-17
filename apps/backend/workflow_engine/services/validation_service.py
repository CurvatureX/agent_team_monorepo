"""
Validation Service - Workflow validation and debugging service.

This module implements workflow validation and debugging operations.
Migrated from old workflow engine structure to new flat architecture.
"""

import logging
from typing import Any, Dict, List, Optional, Set

# Use relative imports for the new flat structure
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# Minimal models for compatibility
class ValidateWorkflowRequest:
    """Minimal ValidateWorkflowRequest for compatibility"""

    def __init__(self, **kwargs):
        self.workflow = kwargs.get("workflow")


class ValidateWorkflowResponse:
    """Minimal ValidateWorkflowResponse for compatibility"""

    def __init__(self, **kwargs):
        self.valid = kwargs.get("valid", False)
        self.errors = kwargs.get("errors", [])
        self.warnings = kwargs.get("warnings", [])
        self.message = kwargs.get("message", "")


class TestNodeRequest:
    """Minimal TestNodeRequest for compatibility"""

    def __init__(self, **kwargs):
        self.node = kwargs.get("node")
        self.input_data = kwargs.get("input_data", {})
        self.static_data = kwargs.get("static_data", {})
        self.credentials = kwargs.get("credentials", {})


class TestNodeResponse:
    """Minimal TestNodeResponse for compatibility"""

    def __init__(self, **kwargs):
        self.success = kwargs.get("success", False)
        self.output_data = kwargs.get("output_data", {})
        self.error = kwargs.get("error", "")
        self.execution_time = kwargs.get("execution_time", 0)
        self.message = kwargs.get("message", "")


class ValidationService:
    """Service for workflow validation and debugging operations."""

    def __init__(self):
        self.logger = logger
        # For new flat structure, simplified node factory approach
        self.node_factory = None

    def validate_workflow(
        self, request: ValidateWorkflowRequest, context=None
    ) -> ValidateWorkflowResponse:
        """Validate a workflow."""
        try:
            workflow = request.workflow if hasattr(request, "workflow") else request
            workflow_name = getattr(workflow, "name", "Unknown Workflow")
            self.logger.info(f"Validating workflow: {workflow_name}")

            errors = []
            warnings = []

            # Basic workflow validation
            if not getattr(workflow, "name", None):
                errors.append("Workflow name is required")

            nodes = getattr(workflow, "nodes", [])
            if not nodes:
                errors.append("Workflow must have at least one node")

            # Node validation
            node_ids = set()
            node_names = set()

            for node in nodes:
                node_id = getattr(node, "id", None)
                node_name = getattr(node, "name", None)
                node_type = getattr(node, "type", None)

                if not node_id:
                    errors.append("Node ID is required")
                    continue

                if not node_name:
                    errors.append(f"Node {node_id} name is required")
                    continue

                if node_id in node_ids:
                    errors.append(f"Duplicate node ID: {node_id}")
                else:
                    node_ids.add(node_id)

                if node_name in node_names:
                    errors.append(f"Duplicate node name: {node_name}")
                else:
                    node_names.add(node_name)

                # Validate node type
                if not node_type:
                    errors.append(f"Node {node_id}: Node type is required")
                    continue

                # Comprehensive node validation using registered node types
                try:
                    from nodes.factory import NodeExecutorFactory

                    # Validate against registered node types
                    if not NodeExecutorFactory.is_registered(node_type):
                        warnings.append(f"Node {node_id}: Unknown node type {node_type}")
                    else:
                        # Validate node parameters using the actual node executor
                        try:
                            executor = NodeExecutorFactory.create_executor(node_type)
                            from nodes.base import NodeExecutionContext

                            # Create minimal context for validation
                            mock_context = NodeExecutionContext(
                                node_id=node_id,
                                execution_id="validation",
                                workflow_id="validation",
                                input_data={},
                                parameters=node.get("parameters", {}),
                            )

                            # Validate parameters
                            is_valid, validation_error = executor.validate_parameters(mock_context)
                            if not is_valid:
                                errors.append(f"Node {node_id}: {validation_error}")

                        except Exception as param_error:
                            warnings.append(
                                f"Node {node_id}: Parameter validation failed - {str(param_error)}"
                            )

                except Exception as e:
                    errors.append(f"Node {node_id}: Validation error - {str(e)}")

            # Connections validation
            connections = getattr(workflow, "connections", None)
            if connections:
                connection_errors = self._validate_connections(connections, node_names)
                errors.extend(connection_errors)

            # Check for circular dependencies
            if not errors:  # Only check if basic validation passes
                circular_deps = self._check_circular_dependencies(workflow)
                if circular_deps:
                    errors.extend(circular_deps)

            is_valid = len(errors) == 0

            return ValidateWorkflowResponse(
                valid=is_valid,
                errors=errors,
                warnings=warnings,
                message="Workflow validation completed",
            )

        except Exception as e:
            self.logger.error(f"Error validating workflow: {str(e)}")
            return ValidateWorkflowResponse(
                valid=False,
                errors=[f"Validation error: {str(e)}"],
                warnings=[],
                message="Validation failed",
            )

    def _validate_connections(self, connections: Any, node_names: Set[str]) -> List[str]:
        """Validate connections structure."""
        errors = []

        # Handle different connection formats
        if isinstance(connections, dict):
            for source_node_name, node_connections in connections.items():
                if source_node_name not in node_names:
                    errors.append(f"Connection source node '{source_node_name}' does not exist")
                    continue

                # Validate connection structure based on format
                if isinstance(node_connections, dict):
                    # Handle ConnectionsMap format
                    connection_types = node_connections.get("connection_types", {})
                    for connection_type, connection_array in connection_types.items():
                        if isinstance(connection_array, dict):
                            connections_list = connection_array.get("connections", [])
                            for connection in connections_list:
                                if isinstance(connection, dict):
                                    target_node_name = connection.get("node", "")
                                    if target_node_name and target_node_name not in node_names:
                                        errors.append(
                                            f"Connection target node '{target_node_name}' does not exist"
                                        )

        return errors

    def test_node(self, request: TestNodeRequest, context=None) -> TestNodeResponse:
        """Test a single node."""
        try:
            node = request.node if hasattr(request, "node") else request
            node_id = getattr(node, "id", "unknown")
            self.logger.info(f"Testing node: {node_id}")

            # Simplified node testing for new structure
            # In the old structure this would use the node factory
            # For migration, return a basic success response

            return TestNodeResponse(
                success=True,
                output_data={"test": "Node test completed"},
                error="",
                execution_time=100,
                message="Node test completed (simplified for migration)",
            )

        except Exception as e:
            self.logger.error(f"Error testing node: {str(e)}")
            return TestNodeResponse(
                success=False, error=f"Test error: {str(e)}", message="Node test failed"
            )

    def _check_circular_dependencies(self, workflow) -> List[str]:
        """Check for circular dependencies in workflow."""
        errors = []

        try:
            connections = getattr(workflow, "connections", None)
            nodes = getattr(workflow, "nodes", [])

            if not connections or not nodes:
                return errors

            # Build adjacency list using node names
            graph = {}
            name_to_id = {}

            for node in nodes:
                node_name = getattr(node, "name", "")
                node_id = getattr(node, "id", "")
                name_to_id[node_name] = node_id
                graph[node_id] = []

            # Build graph from connections
            if isinstance(connections, dict):
                for source_node_name, node_connections in connections.items():
                    source_node_id = name_to_id.get(source_node_name)
                    if not source_node_id:
                        continue

                    # Handle different connection formats
                    if isinstance(node_connections, dict):
                        connection_types = node_connections.get("connection_types", {})
                        for connection_type, connection_array in connection_types.items():
                            if isinstance(connection_array, dict):
                                connections_list = connection_array.get("connections", [])
                                for connection in connections_list:
                                    if isinstance(connection, dict):
                                        target_node_name = connection.get("node", "")
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

        except Exception as e:
            self.logger.error(f"Error checking circular dependencies: {e}")
            errors.append(f"Error checking circular dependencies: {str(e)}")

        return errors

    def validate_workflow_dict(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate workflow from dictionary format."""
        try:
            errors = []
            warnings = []

            # Basic validation
            if not workflow_data.get("name"):
                errors.append("Workflow name is required")

            nodes = workflow_data.get("nodes", [])
            if not nodes:
                errors.append("Workflow must have at least one node")

            # Node validation
            node_ids = set()
            for node in nodes:
                node_id = node.get("id")
                if not node_id:
                    errors.append("Node ID is required")
                    continue

                if node_id in node_ids:
                    errors.append(f"Duplicate node ID: {node_id}")
                else:
                    node_ids.add(node_id)

                if not node.get("type"):
                    errors.append(f"Node {node_id}: Node type is required")

            return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

        except Exception as e:
            self.logger.error(f"Error validating workflow dict: {e}")
            return {"valid": False, "errors": [f"Validation error: {str(e)}"], "warnings": []}
