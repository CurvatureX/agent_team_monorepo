"""
Simplified Workflow Execution Engine.

Clean, focused implementation for reliable node-based workflow execution.
"""

import asyncio
import logging
import time
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
            self.logger.info(
                f"🔄 EXECUTION ENGINE: Starting node execution in order: {execution_order}"
            )
            node_results = {}
            for node_id in execution_order:
                self.logger.info(f"🚀 EXECUTION ENGINE: Starting execution of node '{node_id}'")

                # Find node definition for debugging
                node_def = self._get_node_by_id(workflow_definition, node_id)
                if node_def:
                    self.logger.info(
                        f"📋 EXECUTION ENGINE: Node '{node_id}' - Type: {node_def.get('type')}, Subtype: {node_def.get('subtype', 'N/A')}"
                    )

                start_time = time.time()
                node_result = await self._execute_node_simple(
                    node_id,
                    workflow_definition,
                    node_results,
                    initial_data or {},
                    credentials or {},
                    execution_id,
                )
                execution_time = time.time() - start_time

                node_results[node_id] = node_result

                # Enhanced logging for node result
                status = node_result.get("status", "UNKNOWN")
                self.logger.info(
                    f"✅ EXECUTION ENGINE: Node '{node_id}' completed in {execution_time:.3f}s - Status: {status}"
                )

                # Log node output data if available
                if node_result.get("output_data"):
                    output_keys = list(node_result["output_data"].keys())
                    self.logger.info(
                        f"📤 EXECUTION ENGINE: Node '{node_id}' output keys: {output_keys}"
                    )

                    # Special logging for memory node outputs
                    if node_def and node_def.get("type") == "MEMORY_NODE":
                        memory_context = node_result["output_data"].get("memory_context")
                        formatted_context = node_result["output_data"].get("formatted_context")
                        self.logger.info(
                            f"🧠 EXECUTION ENGINE: Memory node '{node_id}' context length: {len(memory_context) if memory_context else 0} chars"
                        )
                        self.logger.info(
                            f"🧠 EXECUTION ENGINE: Memory node '{node_id}' formatted context length: {len(formatted_context) if formatted_context else 0} chars"
                        )

                # Log any logs from the node execution
                if node_result.get("logs"):
                    for log_msg in node_result["logs"]:
                        self.logger.info(f"📝 EXECUTION ENGINE: Node '{node_id}' log: {log_msg}")

                # Stop on error
                if node_result.get("status") == "ERROR":
                    error_msg = node_result.get("error_message", "Node execution failed")
                    self.logger.error(f"❌ EXECUTION ENGINE: Node '{node_id}' failed: {error_msg}")
                    return {
                        "status": "ERROR",
                        "errors": [error_msg],
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
        """Simple execution order calculation with NEW connection format support."""
        try:
            nodes = workflow_definition.get("nodes", [])
            connections = workflow_definition.get("connections", {})  # NEW format is dict

            self.logger.info(f"🧮 ORDER CALCULATION: Processing {len(nodes)} nodes with connections")

            # Simple topological sort
            node_ids = [node["id"] for node in nodes]
            dependencies = {node_id: set() for node_id in node_ids}

            self.logger.info(f"🧮 ORDER CALCULATION: Node IDs: {node_ids}")

            # Build dependency graph - handle NEW connection format
            for source_node_id, node_connections in connections.items():
                if not isinstance(node_connections, dict):
                    continue

                connection_types = node_connections.get("connection_types", {})
                self.logger.info(
                    f"🧮 ORDER CALCULATION: Processing '{source_node_id}' with connection types: {list(connection_types.keys())}"
                )

                for conn_type, conn_array in connection_types.items():
                    if not isinstance(conn_array, dict) or "connections" not in conn_array:
                        continue

                    connections_list = conn_array.get("connections", [])
                    for conn in connections_list:
                        if not isinstance(conn, dict) or "node" not in conn:
                            continue

                        target_node_id = conn["node"]

                        if source_node_id in node_ids and target_node_id in node_ids:
                            if conn_type == "memory":
                                # For memory connections: AI agent (source) depends on memory node (target)
                                # This ensures memory nodes execute before AI agents that use them
                                dependencies[source_node_id].add(target_node_id)
                                self.logger.info(
                                    f"🧠 ORDER CALCULATION: Memory dependency: '{source_node_id}' depends on '{target_node_id}'"
                                )
                            else:
                                # For regular flow connections: target depends on source (normal flow)
                                dependencies[target_node_id].add(source_node_id)
                                self.logger.info(
                                    f"📈 ORDER CALCULATION: Flow dependency: '{target_node_id}' depends on '{source_node_id}'"
                                )

            # Log final dependencies for debugging
            for node_id, deps in dependencies.items():
                if deps:
                    self.logger.info(f"🔗 ORDER CALCULATION: '{node_id}' depends on: {list(deps)}")

            # Topological sort
            result = []
            remaining = set(node_ids)

            while remaining:
                # Find nodes with no dependencies
                ready = [node_id for node_id in remaining if not dependencies[node_id]]

                if not ready:
                    # Fallback: return nodes in definition order if cycles detected
                    self.logger.warning(
                        "⚠️ ORDER CALCULATION: Cycle detected, falling back to definition order"
                    )
                    return [node["id"] for node in nodes]

                # Process ready nodes (sort for deterministic order)
                ready.sort()
                self.logger.info(f"🎯 ORDER CALCULATION: Ready nodes for execution: {ready}")

                for node_id in ready:
                    result.append(node_id)
                    remaining.remove(node_id)

                    # Remove this node from other dependencies
                    for deps in dependencies.values():
                        deps.discard(node_id)

            final_order = result
            self.logger.info(f"🏁 ORDER CALCULATION: Final execution order: {final_order}")
            return final_order

        except Exception as e:
            self.logger.error(f"❌ ORDER CALCULATION: Error calculating execution order: {e}")
            # Fallback: return nodes in definition order
            fallback_order = [node["id"] for node in workflow_definition.get("nodes", [])]
            self.logger.warning(f"🔄 ORDER CALCULATION: Using fallback order: {fallback_order}")
            return fallback_order

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
            self.logger.info(f"🔧 NODE EXECUTOR: Starting execution for node '{node_id}'")

            # Get node definition
            node_def = self._get_node_by_id(workflow_definition, node_id)
            if not node_def:
                self.logger.error(f"❌ NODE EXECUTOR: Node definition not found for '{node_id}'")
                return {
                    "status": "ERROR",
                    "error_message": f"Node {node_id} not found in workflow definition",
                }

            # Get executor
            node_type = node_def["type"]
            node_subtype = node_def.get("subtype", "")
            self.logger.info(
                f"🏭 NODE EXECUTOR: Creating executor for '{node_id}' - Type: {node_type}, Subtype: {node_subtype}"
            )

            executor = self.factory.create_executor(node_type, node_subtype)

            if not executor:
                self.logger.error(
                    f"❌ NODE EXECUTOR: No executor found for node type: {node_type}, subtype: {node_subtype}"
                )
                return {
                    "status": "ERROR",
                    "error_message": f"No executor found for node type: {node_type}",
                }

            # Prepare input data
            self.logger.info(f"📊 NODE EXECUTOR: Preparing input data for '{node_id}'")
            input_data = self._prepare_node_input_data_simple(
                node_id, workflow_definition, previous_results, initial_data
            )

            # Log input data details
            input_keys = list(input_data.keys()) if input_data else []
            self.logger.info(f"📥 NODE EXECUTOR: Input data keys for '{node_id}': {input_keys}")

            # Special logging for memory integration
            if any(key.startswith("memory") for key in input_keys):
                self.logger.info(f"🧠 NODE EXECUTOR: Memory data detected in input for '{node_id}'")
                for key in input_keys:
                    if key.startswith("memory"):
                        value = input_data.get(key)
                        value_len = len(str(value)) if value else 0
                        self.logger.info(f"🧠 NODE EXECUTOR: {key} length: {value_len} chars")

            # Create execution context
            self.logger.info(f"🏗️ NODE EXECUTOR: Creating execution context for '{node_id}'")
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
            self.logger.info(
                f"⚡ NODE EXECUTOR: Executing node '{node_id}' with executor: {type(executor).__name__}"
            )
            if asyncio.iscoroutinefunction(executor.execute):
                result = await executor.execute(context)
            else:
                result = executor.execute(context)

            # Log execution result
            self.logger.info(
                f"🎯 NODE EXECUTOR: Node '{node_id}' execution completed - Result status: {result.status}"
            )

            # Log output data if available
            if result.output_data:
                output_keys = list(result.output_data.keys())
                self.logger.info(f"📤 NODE EXECUTOR: Node '{node_id}' output keys: {output_keys}")

                # Special logging for memory node results
                if node_type == "MEMORY_NODE":
                    memory_context = result.output_data.get("memory_context")
                    formatted_context = result.output_data.get("formatted_context")
                    memory_type = result.output_data.get("memory_type")
                    self.logger.info(
                        f"🧠 NODE EXECUTOR: Memory node '{node_id}' - Type: {memory_type}"
                    )
                    self.logger.info(
                        f"🧠 NODE EXECUTOR: Memory node '{node_id}' - Context length: {len(memory_context) if memory_context else 0}"
                    )
                    self.logger.info(
                        f"🧠 NODE EXECUTOR: Memory node '{node_id}' - Formatted length: {len(formatted_context) if formatted_context else 0}"
                    )

                    # Log a sample of the memory context
                    if formatted_context and len(formatted_context) > 0:
                        sample = (
                            formatted_context[:200] + "..."
                            if len(formatted_context) > 200
                            else formatted_context
                        )
                        self.logger.info(f"🧠 NODE EXECUTOR: Memory context sample: {sample}")

            # Log any execution logs from the result
            if hasattr(result, "logs") and result.logs:
                for log_msg in result.logs:
                    self.logger.info(f"📝 NODE EXECUTOR: Node '{node_id}' internal log: {log_msg}")

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
        self.logger.info(
            f"📊 INPUT PREPARATION: Starting for node '{node_id}' with initial keys: {list(input_data.keys())}"
        )

        connections = workflow_definition.get("connections", {})
        self.logger.info(
            f"🔗 INPUT PREPARATION: Found connections dict with {len(connections)} source nodes"
        )

        # Handle NEW connection format with connection_types
        for source_node_id, node_connections in connections.items():
            if not isinstance(node_connections, dict):
                continue

            connection_types = node_connections.get("connection_types", {})
            self.logger.info(
                f"🔗 INPUT PREPARATION: Source '{source_node_id}' has connection types: {list(connection_types.keys())}"
            )

            for conn_type, conn_array in connection_types.items():
                if not isinstance(conn_array, dict) or "connections" not in conn_array:
                    continue

                connections_list = conn_array.get("connections", [])
                for conn in connections_list:
                    if not isinstance(conn, dict) or "node" not in conn:
                        continue

                    target_node_id = conn["node"]

                    # If this connection targets our current node
                    if target_node_id == node_id:
                        self.logger.info(
                            f"🎯 INPUT PREPARATION: Found {conn_type} connection from '{source_node_id}' to '{node_id}'"
                        )

                        if source_node_id in previous_results:
                            source_result = previous_results[source_node_id]
                            if isinstance(source_result, dict) and "output_data" in source_result:
                                source_output = source_result["output_data"]

                                # Handle different connection types
                                if conn_type == "memory":
                                    # For memory connections, merge the memory data
                                    self.logger.info(
                                        f"🧠 INPUT PREPARATION: Adding memory data from '{source_node_id}' with keys: {list(source_output.keys())}"
                                    )
                                    input_data.update(source_output)
                                else:
                                    # For regular flow connections, merge all data
                                    self.logger.info(
                                        f"📥 INPUT PREPARATION: Adding flow data from '{source_node_id}' with keys: {list(source_output.keys())}"
                                    )
                                    input_data.update(source_output)
                            else:
                                self.logger.warning(
                                    f"⚠️ INPUT PREPARATION: Source '{source_node_id}' result has no output_data"
                                )
                        else:
                            self.logger.warning(
                                f"⚠️ INPUT PREPARATION: Source '{source_node_id}' not found in previous results"
                            )

        self.logger.info(
            f"📦 INPUT PREPARATION: Final input data for '{node_id}' has keys: {list(input_data.keys())}"
        )
        return input_data

    def _dict_to_node_object(self, node_def: Dict[str, Any]):
        """Convert node definition dict to node object."""
        from types import SimpleNamespace

        return SimpleNamespace(**node_def)
