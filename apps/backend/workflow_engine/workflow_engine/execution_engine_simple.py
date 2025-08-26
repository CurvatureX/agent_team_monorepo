"""
Simplified Workflow Execution Engine.

Clean, focused implementation for reliable node-based workflow execution.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from .nodes.base import NodeExecutionContext, NodeExecutionResult
from .nodes.factory import get_node_executor_factory, register_default_executors


class WorkflowExecutionEngine:
    """Simplified workflow execution engine for reliable node-based workflow execution."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.factory = get_node_executor_factory()

        # Register all default executors
        register_default_executors()

    async def execute_workflow(
        self,
        workflow_id: str,
        execution_id: str,
        workflow_definition: Dict[str, Any],
        initial_data: Optional[Dict[str, Any]] = None,
        credentials: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a complete workflow."""

        self.logger.info(f"Executing workflow: {workflow_id} (execution: {execution_id})")

        try:
            # 1. Validate workflow structure
            if not self._validate_workflow_basic(workflow_definition):
                return {
                    "status": "ERROR",
                    "errors": ["Invalid workflow structure"],
                    "execution_id": execution_id,
                }

            # 2. Calculate execution order
            execution_order = self._calculate_execution_order_simple(workflow_definition)
            if not execution_order:
                return {
                    "status": "ERROR",
                    "errors": ["Cannot determine execution order"],
                    "execution_id": execution_id,
                }

            # 3. Execute nodes in sequence
            node_results = {}
            for node_id in execution_order:
                self.logger.info(f"Executing node: {node_id}")

                node_result = await self._execute_node_simple(
                    node_id,
                    workflow_definition,
                    node_results,
                    initial_data or {},
                    credentials or {},
                    execution_id,
                )

                node_results[node_id] = node_result

                # Stop on error
                if node_result.get("status") == "ERROR":
                    return {
                        "status": "ERROR",
                        "errors": [node_result.get("error_message", "Node execution failed")],
                        "execution_id": execution_id,
                        "node_results": node_results,
                        "failed_node": node_id,
                    }

            # 4. Return success
            return {
                "status": "completed",
                "execution_id": execution_id,
                "node_results": node_results,
                "execution_order": execution_order,
            }

        except Exception as e:
            self.logger.error(f"Error executing workflow {workflow_id}: {str(e)}")
            return {
                "status": "ERROR",
                "errors": [f"Execution error: {str(e)}"],
                "execution_id": execution_id,
                "node_results": {},
            }

    def _validate_workflow_basic(self, workflow_definition: Dict[str, Any]) -> bool:
        """Basic workflow validation."""
        try:
            nodes = workflow_definition.get("nodes", [])
            if not nodes:
                return False

            # Check each node has required fields
            for node in nodes:
                if not all(key in node for key in ["id", "type"]):
                    return False

            return True
        except Exception:
            return False

    def _calculate_execution_order_simple(self, workflow_definition: Dict[str, Any]) -> List[str]:
        """Simple execution order calculation."""
        try:
            nodes = workflow_definition.get("nodes", [])
            connections = workflow_definition.get("connections", [])

            # Simple topological sort
            node_ids = [node["id"] for node in nodes]
            dependencies = {node_id: set() for node_id in node_ids}

            # Build dependency graph
            for conn in connections:
                target = conn.get("target")
                source = conn.get("source")
                conn_type = conn.get("type", "flow")  # Default to flow connection

                if target and source and target in dependencies and source in node_ids:
                    if conn_type == "memory":
                        # For memory connections: AI agent (source) depends on memory node (target)
                        # This ensures memory nodes execute before AI agents that use them
                        dependencies[source].add(target)
                        self.logger.debug(f"Memory dependency: {source} depends on {target}")
                    else:
                        # For regular flow connections: target depends on source (normal flow)
                        dependencies[target].add(source)
                        self.logger.debug(f"Flow dependency: {target} depends on {source}")

            # Topological sort
            result = []
            remaining = set(node_ids)

            while remaining:
                # Find nodes with no dependencies
                ready = [node_id for node_id in remaining if not dependencies[node_id]]

                if not ready:
                    # Fallback: return nodes in definition order if cycles detected
                    return [node["id"] for node in nodes]

                # Process ready nodes
                for node_id in ready:
                    result.append(node_id)
                    remaining.remove(node_id)

                    # Remove this node from other dependencies
                    for deps in dependencies.values():
                        deps.discard(node_id)

            return result

        except Exception as e:
            self.logger.error(f"Error calculating execution order: {e}")
            # Fallback: return nodes in definition order
            return [node["id"] for node in workflow_definition.get("nodes", [])]

    async def _execute_node_simple(
        self,
        node_id: str,
        workflow_definition: Dict[str, Any],
        previous_results: Dict[str, Any],
        initial_data: Dict[str, Any],
        credentials: Dict[str, Any],
        execution_id: str,
    ) -> Dict[str, Any]:
        """Execute a single node with simplified logic."""

        try:
            # Get node definition
            node_def = self._get_node_by_id(workflow_definition, node_id)
            if not node_def:
                return {
                    "status": "ERROR",
                    "error_message": f"Node {node_id} not found in workflow definition",
                }

            # Get executor
            node_type = node_def["type"]
            node_subtype = node_def.get("subtype", "")
            executor = self.factory.create_executor(node_type, node_subtype)

            if not executor:
                return {
                    "status": "ERROR",
                    "error_message": f"No executor found for node type: {node_type}",
                }

            # Prepare input data
            input_data = self._prepare_node_input_data_simple(
                node_id, workflow_definition, previous_results, initial_data
            )

            # Create execution context
            context = NodeExecutionContext(
                node=self._dict_to_node_object(node_def),
                workflow_id=workflow_definition.get("id", "unknown"),
                execution_id=execution_id,
                input_data=input_data,
                static_data=workflow_definition.get("static_data", {}),
                credentials=credentials,
                metadata={"node_id": node_id},
            )

            # Execute node - handle both sync and async executors
            if asyncio.iscoroutinefunction(executor.execute):
                result = await executor.execute(context)
            else:
                result = executor.execute(context)

            # Convert result to dict
            return {
                "status": "SUCCESS" if result.status == "success" else "ERROR",
                "output_data": result.output_data,
                "error_message": result.error_message if hasattr(result, "error_message") else None,
                "logs": result.logs if hasattr(result, "logs") else [],
            }

        except Exception as e:
            self.logger.error(f"Error executing node {node_id}: {e}")
            return {
                "status": "ERROR",
                "error_message": f"Node execution failed: {str(e)}",
                "output_data": {},
            }

    def _get_node_by_id(
        self, workflow_definition: Dict[str, Any], node_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get node definition by ID."""
        nodes = workflow_definition.get("nodes", [])
        for node in nodes:
            if node.get("id") == node_id:
                return node
        return None

    def _prepare_node_input_data_simple(
        self,
        node_id: str,
        workflow_definition: Dict[str, Any],
        previous_results: Dict[str, Any],
        initial_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Prepare input data for node execution."""

        input_data = initial_data.copy()
        connections = workflow_definition.get("connections", [])

        # Find connections targeting this node
        for conn in connections:
            if conn.get("target") == node_id:
                source_id = conn.get("source")
                if source_id in previous_results:
                    source_result = previous_results[source_id]
                    if isinstance(source_result, dict) and "output_data" in source_result:
                        input_data.update(source_result["output_data"])

        return input_data

    def _dict_to_node_object(self, node_def: Dict[str, Any]):
        """Convert node definition dict to node object."""
        from types import SimpleNamespace

        return SimpleNamespace(**node_def)
