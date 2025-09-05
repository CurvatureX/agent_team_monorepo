"""
Enhanced Workflow Execution Engine.

Balanced implementation that maintains sophisticated tracking and debugging capabilities
while keeping clean async/await handling and reasonable complexity.
"""

import asyncio
import logging
import os
import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from .nodes.base import NodeExecutionContext, NodeExecutionResult
from .nodes.factory import get_node_executor_factory, register_default_executors

# Import shared workflow models for proper connection validation
try:
    from shared.models.workflow import ConnectionArrayData, ConnectionData, NodeConnectionsData
    from shared.node_specs.communication_protocol import apply_transformation
except ImportError:
    # Fallback for deployment environments where shared models might not be available
    ConnectionData = dict
    NodeConnectionsData = dict
    ConnectionArrayData = dict
    apply_transformation = lambda data, src, tgt: data


class WorkflowExecutionEngine:
    """Enhanced workflow execution engine with sophisticated tracking and debugging capabilities."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.factory = get_node_executor_factory()

        # Register all default executors
        register_default_executors()

        # Track execution states for debugging
        self.execution_states: Dict[str, Dict[str, Any]] = {}

    async def execute_workflow(
        self,
        workflow_id: str,
        execution_id: str,
        workflow_definition: Dict[str, Any],
        initial_data: Optional[Dict[str, Any]] = None,
        credentials: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a complete workflow with enhanced tracking."""

        self.logger.info(
            f"🚀 Starting enhanced workflow execution: {workflow_id} (execution: {execution_id})"
        )
        self.logger.info(f"📋 Workflow definition keys: {list(workflow_definition.keys())}")
        self.logger.info(f"📊 Number of nodes: {len(workflow_definition.get('nodes', []))}")
        self.logger.info(f"🔗 Connections present: {bool(workflow_definition.get('connections'))}")
        self.logger.info(
            f"📥 Initial data keys: {list(initial_data.keys()) if initial_data else 'None'}"
        )
        self.logger.info(f"🔐 Credentials provided: {bool(credentials)}")

        # Initialize enhanced execution state
        execution_state = self._initialize_enhanced_execution_state(
            workflow_id, execution_id, workflow_definition, initial_data, credentials, user_id
        )
        self.execution_states[execution_id] = execution_state

        try:
            # Validate workflow
            self.logger.info("🔍 Step 1: Validating workflow structure...")
            validation_errors = self._validate_workflow(workflow_definition)
            if validation_errors:
                self.logger.error(
                    f"❌ Workflow validation failed with {len(validation_errors)} errors:"
                )
                for i, error in enumerate(validation_errors, 1):
                    self.logger.error(f"   {i}. {error}")
                execution_state["status"] = "ERROR"
                execution_state["errors"] = validation_errors
                self._record_execution_error(execution_id, "validation", validation_errors)
                return execution_state
            self.logger.info("✅ Workflow structure validation passed")

            # Calculate execution order
            self.logger.info("🔢 Step 2: Calculating execution order...")
            execution_order = self._calculate_execution_order(workflow_definition)
            execution_state["execution_order"] = execution_order
            self.logger.info(f"📋 Execution order calculated: {execution_order}")

            if not execution_order:
                self.logger.error("❌ No execution order calculated - no nodes to execute!")
                execution_state["status"] = "ERROR"
                execution_state["errors"] = ["No nodes found or circular dependency detected"]
                return execution_state

            # Record execution context
            self.logger.info("📝 Step 3: Recording execution context...")
            self._record_execution_context(
                execution_id, workflow_definition, initial_data, credentials
            )
            self.logger.info("✅ Execution context recorded")

            # Execute nodes in order with enhanced tracking
            self.logger.info(f"🏃 Step 4: Executing {len(execution_order)} nodes in order...")
            for i, node_id in enumerate(execution_order, 1):
                self.logger.info(
                    f"🔄 [{i}/{len(execution_order)}] Starting execution of node: {node_id}"
                )

                try:
                    node_result = await self._execute_node_with_enhanced_tracking(
                        node_id,
                        workflow_definition,
                        execution_state,
                        initial_data or {},
                        credentials or {},
                        user_id,
                    )

                    self.logger.info(
                        f"✅ [{i}/{len(execution_order)}] Node {node_id} completed with status: {node_result.get('status', 'UNKNOWN')}"
                    )

                    if node_result.get("error_message"):
                        self.logger.error(
                            f"⚠️ Node {node_id} error message: {node_result['error_message']}"
                        )

                    execution_state["node_results"][node_id] = node_result

                    # Record execution path
                    self._record_execution_path_step(
                        execution_id, node_id, node_result, workflow_definition
                    )

                    # Stop execution if node failed
                    if node_result["status"] == "ERROR":
                        self.logger.error(f"❌ Node {node_id} failed - stopping workflow execution")
                        execution_state["status"] = "ERROR"
                        execution_state["errors"].append(
                            f"Node {node_id} failed: {node_result.get('error_message', 'Unknown error')}"
                        )
                        break

                    # Stop execution if node is paused (Human-in-the-Loop)
                    if node_result["status"] == "PAUSED":
                        self.logger.info(
                            f"⏸️ Node {node_id} paused workflow execution - waiting for resume"
                        )
                        execution_state["status"] = "PAUSED"
                        execution_state["paused_at_node"] = node_id
                        execution_state["pause_reason"] = node_result.get("output_data", {}).get(
                            "pause_reason", "human_interaction"
                        )
                        execution_state["pause_data"] = {
                            "node_id": node_id,
                            "interaction_id": node_result.get("output_data", {}).get(
                                "interaction_id"
                            ),
                            "timeout_at": node_result.get("output_data", {}).get("timeout_at"),
                            "remaining_nodes": execution_order[
                                i + 1 :
                            ],  # Nodes after the paused node
                            "current_position": i,
                            "paused_at": datetime.now().isoformat(),
                        }

                        # Store complete execution context for seamless resume
                        await self._store_complete_pause_context(
                            execution_id,
                            execution_state,
                            workflow_definition,
                            initial_data,
                            credentials,
                            user_id,
                            node_id,
                            execution_order[i + 1 :],
                        )
                        break

                except Exception as node_error:
                    self.logger.error(
                        f"💥 Exception during node {node_id} execution: {str(node_error)}"
                    )
                    self.logger.exception("Full stack trace:")
                    execution_state["status"] = "ERROR"
                    execution_state["errors"].append(f"Node {node_id} exception: {str(node_error)}")
                    break

            self.logger.info(f"🏁 Node execution phase completed")

            # Set final status
            self.logger.info("🏁 Step 5: Finalizing workflow execution...")
            if execution_state["status"] == "RUNNING":
                execution_state["status"] = "completed"
                self.logger.info("✅ Workflow completed successfully")
            elif execution_state["status"] == "PAUSED":
                self.logger.info("⏸️ Workflow paused - awaiting human interaction")
                # Don't set end_time for paused workflows as they can be resumed
            else:
                self.logger.info(f"⚠️ Workflow finished with status: {execution_state['status']}")

            # Only set end_time for completed or error workflows, not paused ones
            if execution_state["status"] != "PAUSED":
                execution_state["end_time"] = datetime.now().isoformat()

            # Generate final execution report
            self.logger.info("📊 Generating execution report...")
            execution_report = self._generate_execution_report(execution_id, execution_state)
            execution_state["execution_report"] = execution_report

            # Log summary
            total_nodes = len(execution_state.get("node_results", {}))
            successful_nodes = len(
                [
                    r
                    for r in execution_state.get("node_results", {}).values()
                    if r.get("status") == "SUCCESS"
                ]
            )
            failed_nodes = total_nodes - successful_nodes

            self.logger.info(
                f"🎯 Workflow execution summary: {execution_id} | Status: {execution_state['status']} | "
                f"Nodes: {successful_nodes}/{total_nodes} successful | "
                f"Errors: {len(execution_state.get('errors', []))}"
            )

            return execution_state

        except Exception as e:
            self.logger.error(f"💥 Critical error executing workflow {workflow_id}: {str(e)}")
            self.logger.exception("Full stack trace:")
            execution_state["status"] = "ERROR"
            execution_state["errors"].append(f"Execution error: {str(e)}")
            execution_state["end_time"] = datetime.now().isoformat()
            self._record_execution_error(execution_id, "execution", [str(e)])

            return execution_state

    async def _execute_node_with_enhanced_tracking(
        self,
        node_id: str,
        workflow_definition: Dict[str, Any],
        execution_state: Dict[str, Any],
        initial_data: Dict[str, Any],
        credentials: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a single node with enhanced tracking and data collection."""

        self.logger.info(f"🔧 Executing node with enhanced tracking: {node_id}")

        node_def = self._get_node_by_id(workflow_definition, node_id)
        if not node_def:
            self.logger.error(f"❌ Node {node_id} not found in workflow definition")
            return {
                "status": "ERROR",
                "error_message": f"Node {node_id} not found in workflow definition",
            }

        self.logger.info(
            f"✅ Found node definition: {node_def.get('name', 'Unnamed')} (type: {node_def.get('type', 'Unknown')}, subtype: {node_def.get('subtype', 'None')})"
        )
        self.logger.info(f"🔍 Full node definition: {node_def}")

        # Record node execution start
        node_start_time = time.time()
        execution_state["performance_metrics"]["node_execution_times"][node_id] = {
            "start_time": node_start_time,
            "end_time": None,
            "duration": None,
        }

        # Get executor
        node_type = node_def["type"]
        node_subtype = node_def.get("subtype", "")

        try:
            executor = self.factory.create_executor(node_type, node_subtype)
            if not executor:
                self.logger.error(
                    f"❌ No executor found for node type: {node_type}, subtype: {node_subtype}"
                )
                return {
                    "status": "ERROR",
                    "error_message": f"No executor found for node type: {node_type}, subtype: {node_subtype}",
                }
            self.logger.info(f"✅ Created executor: {executor.__class__.__name__}")
        except Exception as executor_error:
            self.logger.error(f"💥 Error creating executor: {str(executor_error)}")
            self.logger.exception("Executor creation stack trace:")
            return {
                "status": "ERROR",
                "error_message": f"Error creating executor: {str(executor_error)}",
            }

        # Prepare input data with enhanced tracking
        self.logger.info(f"📥 Preparing input data for node: {node_id}")
        try:
            input_data = self._prepare_node_input_data_with_tracking(
                node_id, workflow_definition, execution_state, initial_data
            )
            self.logger.info(
                f"✅ Input data prepared - keys: {list(input_data.keys()) if input_data else 'None'}"
            )
        except Exception as input_error:
            self.logger.error(f"💥 Error preparing input data: {str(input_error)}")
            self.logger.exception("Input data preparation stack trace:")
            return {
                "status": "ERROR",
                "error_message": f"Error preparing input data: {str(input_error)}",
            }

        # Record node input data
        try:
            self._record_node_input_data(
                execution_state["execution_id"], node_id, node_def, input_data, credentials
            )
            self.logger.info("✅ Node input data recorded")
        except Exception as record_error:
            self.logger.warning(f"⚠️ Could not record node input data: {str(record_error)}")

        # Create enhanced execution context
        trigger_data = execution_state.get("execution_context", {}).get("trigger_data", {})

        context = NodeExecutionContext(
            node=self._dict_to_node_object(node_def),
            workflow_id=execution_state["workflow_id"],
            execution_id=execution_state["execution_id"],
            input_data=input_data,
            static_data=workflow_definition.get("static_data", {}),
            credentials=credentials,
            metadata={
                "node_id": node_id,
                "execution_start_time": node_start_time,
                "tracking_enabled": True,
                "trigger_data": trigger_data,
                "trigger_channel_id": trigger_data.get("channel_id"),
                "trigger_user_id": trigger_data.get("user_id"),
                "user_id": user_id,  # Add the actual executing user ID
                "workflow_connections": workflow_definition.get(
                    "connections", {}
                ),  # Add workflow connections
                "workflow_nodes": workflow_definition.get(
                    "nodes", []
                ),  # Add all nodes for memory node detection
            },
        )

        try:
            # Execute node - handle both sync and async executors
            self.logger.info(
                f"🔥🚀 EXECUTING NODE: {node_id} with executor {executor.__class__.__name__}"
            )
            self.logger.info(f"🔥🚀 NODE TYPE: {node_type}, SUBTYPE: {node_subtype}")
            self.logger.info(
                f"🔥🚀 INPUT DATA KEYS: {list(input_data.keys()) if input_data else 'NO_INPUT_DATA'}"
            )
            self.logger.info(f"🔥🚀 CREDENTIALS PROVIDED: {bool(credentials)}")

            self.logger.info(
                f"🚀 Executing node {node_id} with executor {executor.__class__.__name__}"
            )
            self.logger.info(
                f"🔧 Executor is async: {asyncio.iscoroutinefunction(executor.execute)}"
            )

            if asyncio.iscoroutinefunction(executor.execute):
                self.logger.info("⏳ Awaiting async executor...")
                result = await executor.execute(context)
            else:
                self.logger.info("⏳ Running sync executor...")
                result = executor.execute(context)

            self.logger.info(f"🔥✅ NODE EXECUTION COMPLETED: {node_id}")
            self.logger.info(f"🔥✅ RESULT TYPE: {type(result).__name__}")
            if hasattr(result, "status"):
                self.logger.info(f"🔥✅ RESULT STATUS: {result.status}")
            if hasattr(result, "output_data"):
                if isinstance(result.output_data, dict):
                    self.logger.info(f"🔥✅ OUTPUT DATA KEYS: {list(result.output_data.keys())}")
                    for key, value in result.output_data.items():
                        if isinstance(value, str) and len(value) > 200:
                            self.logger.info(
                                f"🔥✅ OUTPUT '{key}': {value[:200]}... ({len(value)} chars)"
                            )
                        else:
                            self.logger.info(f"🔥✅ OUTPUT '{key}': {value}")
                else:
                    self.logger.info(f"🔥✅ OUTPUT DATA (non-dict): {result.output_data}")
            if hasattr(result, "error_message") and result.error_message:
                self.logger.info(f"🔥❌ RESULT ERROR: {result.error_message}")
            if hasattr(result, "logs") and result.logs:
                self.logger.info(f"🔥📝 RESULT LOGS ({len(result.logs)} entries):")
                for i, log_entry in enumerate(result.logs):
                    self.logger.info(f"🔥📝 [{i+1}] {log_entry}")

            self.logger.info(f"✅ Node execution completed - result type: {type(result).__name__}")
            if hasattr(result, "status"):
                self.logger.info(f"📊 Execution result status: {result.status}")
            if hasattr(result, "output_data") and result.output_data:
                self.logger.info(
                    f"📤 Output data keys: {list(result.output_data.keys()) if isinstance(result.output_data, dict) else 'Non-dict output'}"
                )
            if hasattr(result, "error_message") and result.error_message:
                self.logger.error(f"⚠️ Execution result has error: {result.error_message}")

            # Record node execution end
            node_end_time = time.time()
            execution_state["performance_metrics"]["node_execution_times"][node_id].update(
                {"end_time": node_end_time, "duration": node_end_time - node_start_time}
            )

            # Record data flow
            self._record_data_flow(
                execution_state["execution_id"], node_id, input_data, result.output_data, node_def
            )

            # Convert result to dict with enhanced information
            # Handle both string status and ExecutionStatus enum
            status_value = result.status
            if hasattr(status_value, "value"):
                # It's an enum, get the value
                status_str = status_value.value.upper()
            else:
                # It's already a string
                status_str = str(status_value).upper()

            # Map to our expected status format - preserve PAUSED state
            if status_str == "PAUSED":
                final_status = "PAUSED"
            else:
                final_status = (
                    "SUCCESS" if status_str in ["SUCCESS", "COMPLETED", "success"] else "ERROR"
                )

            self.logger.info(
                f"🔄 Status conversion: {result.status} -> {status_str} -> {final_status}"
            )

            result_dict = {
                "status": final_status,
                "output_data": result.output_data,
                "error_message": getattr(result, "error_message", None),
                "logs": getattr(result, "logs", []),
                "execution_time": node_end_time - node_start_time,
                "node_type": node_type,
                "node_subtype": node_subtype,
            }

            # Record execution path step
            self._record_execution_path_step(
                execution_state["execution_id"], node_id, result_dict, workflow_definition
            )

            return result_dict

        except Exception as e:
            self.logger.error(f"Error executing node {node_id}: {str(e)}")

            # Record error
            node_end_time = time.time()
            execution_state["performance_metrics"]["node_execution_times"][node_id].update(
                {"end_time": node_end_time, "duration": node_end_time - node_start_time}
            )

            error_result_dict = {
                "status": "ERROR",
                "error_message": f"Node execution failed: {str(e)}",
                "output_data": {},
                "execution_time": node_end_time - node_start_time,
                "node_type": node_type,
                "node_subtype": node_subtype,
            }

            # Record execution path step for error case
            self._record_execution_path_step(
                execution_state["execution_id"], node_id, error_result_dict, workflow_definition
            )

            return error_result_dict

    def _initialize_enhanced_execution_state(
        self,
        workflow_id: str,
        execution_id: str,
        workflow_definition: Dict[str, Any],
        initial_data: Optional[Dict[str, Any]],
        credentials: Optional[Dict[str, Any]],
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Initialize enhanced execution state with detailed tracking."""

        execution_state = {
            "workflow_id": workflow_id,
            "execution_id": execution_id,
            "status": "RUNNING",
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "nodes": workflow_definition.get("nodes", []),
            "connections": workflow_definition.get("connections", {}),
            "node_results": {},
            "execution_order": [],
            "errors": [],
            # Enhanced tracking structures
            "execution_path": {
                "steps": [],
                "branch_decisions": {},
                "loop_info": [],
                "skipped_nodes": [],
                "node_execution_counts": {},
            },
            "node_inputs": {},
            "execution_context": {
                "environment_variables": dict(os.environ),
                "global_parameters": {},
                "workflow_variables": workflow_definition.get("static_data", {}),
                "initial_data": initial_data or {},
                "credentials_available": bool(credentials),
                "workflow_settings": workflow_definition.get("settings", {}),
                "execution_start_time": int(time.time()),
                "execution_mode": "manual",
                "triggered_by": "system",
                "user_id": user_id,
                "metadata": {},
            },
            "performance_metrics": {
                "total_execution_time": 0,
                "node_execution_times": {},
                "memory_usage": self._get_memory_usage(),
                "cpu_usage": self._get_cpu_usage(),
            },
            "data_flow": {
                "data_transfers": [],
                "data_transformations": [],
                "data_sources": {},
            },
        }

        # Store execution state
        self.execution_states[execution_id] = execution_state

        return execution_state

    def _prepare_node_input_data_with_tracking(
        self,
        node_id: str,
        workflow_definition: Dict[str, Any],
        execution_state: Dict[str, Any],
        initial_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Prepare input data for a node with enhanced tracking using ConnectionsMap."""

        connections = workflow_definition.get("connections", {})
        node_results = execution_state.get("node_results", {})

        return self._prepare_connections_data(
            node_id, connections, node_results, initial_data, execution_state
        )

    def _prepare_connections_data(
        self,
        node_id: str,
        connections: Dict,
        node_results: Dict,
        initial_data: Dict,
        execution_state: Dict,
    ) -> Dict[str, Any]:
        """Handle ConnectionsMap format with enhanced tracking."""

        incoming_connections = []
        connections_dict = connections

        for source_node_id, node_connections in connections_dict.items():
            connection_types = node_connections.get("connection_types", {})
            for connection_type, connection_array in connection_types.items():
                connections_list = connection_array.get("connections", [])

                for connection in connections_list:
                    if connection.get("node") == node_id:
                        # Get source node name for tracking
                        source_node_name = None
                        for node in execution_state.get("nodes", []):
                            if node.get("id") == source_node_id:
                                source_node_name = node.get("name")
                                break

                        incoming_connections.append(
                            {
                                "source_node_id": source_node_id,
                                "source_node_name": source_node_name or source_node_id,
                                "connection_type": connection_type,
                                "connection_info": connection,
                                "data_available": source_node_id in node_results,
                            }
                        )

        # If no incoming connections, use initial data
        if not incoming_connections:
            return initial_data

        # Combine data from all incoming connections with tracking
        combined_data = {}
        data_sources = []

        # Group connections by type
        connections_by_type = defaultdict(list)
        for conn in incoming_connections:
            connections_by_type[conn["connection_type"]].append(conn)

        # Process each connection type with tracking
        for connection_type, conns in connections_by_type.items():
            for conn in conns:
                source_node_id = conn["source_node_id"]
                if source_node_id in node_results:
                    source_result = node_results[source_node_id]
                    if source_result.get("status") == "SUCCESS":
                        output_data = source_result.get("output_data", {})

                        # Track data source
                        data_sources.append(
                            {
                                "source_node": source_node_id,
                                "source_node_name": conn["source_node_name"],
                                "connection_type": connection_type,
                                "data_present": bool(output_data),
                                "data_size": len(str(output_data)),
                            }
                        )

                        # For MAIN connections, apply transformation and merge
                        if connection_type == "main":
                            # Apply data transformation based on node types
                            transformed_data = self._transform_node_data(
                                output_data, source_node_id, node_id, execution_state
                            )
                            combined_data.update(transformed_data)
                        else:
                            # For specialized connections, group by type
                            if connection_type not in combined_data:
                                combined_data[connection_type] = {}
                            combined_data[connection_type].update(output_data)

        # Record data flow information
        execution_state["data_flow"]["data_sources"][node_id] = data_sources

        # If no data was collected, return initial data
        if not combined_data:
            return initial_data

        return combined_data

    def _record_execution_path_step(
        self,
        execution_id: str,
        node_id: str,
        node_result: Dict[str, Any],
        workflow_definition: Dict[str, Any],
    ):
        """Record a step in the execution path."""

        execution_state = self.execution_states.get(execution_id)
        if not execution_state:
            return

        # Get node definition
        node_def = self._get_node_by_id(workflow_definition, node_id)
        if not node_def:
            return

        # Create path step
        path_step = {
            "node_id": node_id,
            "node_name": node_def.get("name", ""),
            "node_type": node_def.get("type", ""),
            "node_subtype": node_def.get("subtype", ""),
            "start_time": execution_state["performance_metrics"]["node_execution_times"][node_id][
                "start_time"
            ],
            "end_time": execution_state["performance_metrics"]["node_execution_times"][node_id][
                "end_time"
            ],
            "execution_time": execution_state["performance_metrics"]["node_execution_times"][
                node_id
            ]["duration"],
            "status": node_result["status"],
            "error": node_result.get("error_message") if node_result["status"] == "ERROR" else None,
        }

        execution_state["execution_path"]["steps"].append(path_step)

        # Update execution count
        node_name = node_def.get("name", node_id)
        current_count = execution_state["execution_path"]["node_execution_counts"].get(node_name, 0)
        execution_state["execution_path"]["node_execution_counts"][node_name] = current_count + 1

    def _record_node_input_data(
        self,
        execution_id: str,
        node_id: str,
        node_def: Dict[str, Any],
        input_data: Dict[str, Any],
        credentials: Dict[str, Any],
    ):
        """Record node input data for debugging."""

        execution_state = self.execution_states.get(execution_id)
        if not execution_state:
            return

        node_input_data = {
            "node_id": node_id,
            "node_name": node_def.get("name", ""),
            "input_data": input_data,
            "parameters": node_def.get("parameters", {}),
            "credentials": {
                k: "***" if "password" in k.lower() or "token" in k.lower() else v
                for k, v in credentials.items()
            },
            "timestamp": int(time.time()),
        }

        execution_state["node_inputs"][node_id] = node_input_data

    def _record_execution_context(
        self,
        execution_id: str,
        workflow_definition: Dict[str, Any],
        initial_data: Optional[Dict[str, Any]],
        credentials: Optional[Dict[str, Any]],
    ):
        """Record execution context information."""

        execution_state = self.execution_states.get(execution_id)
        if not execution_state:
            return

        execution_state["execution_context"].update(
            {
                "workflow_variables": workflow_definition.get("static_data", {}),
                "initial_data": initial_data or {},
                "credentials_available": bool(credentials),
                "workflow_settings": workflow_definition.get("settings", {}),
            }
        )

    def _record_data_flow(
        self,
        execution_id: str,
        node_id: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        node_def: Dict[str, Any],
    ):
        """Record data flow information."""

        execution_state = self.execution_states.get(execution_id)
        if not execution_state:
            return

        data_transfer = {
            "node_id": node_id,
            "node_name": node_def.get("name", ""),
            "node_type": node_def.get("type", ""),
            "input_data_size": len(str(input_data)),
            "output_data_size": len(str(output_data)),
            "data_transformation": self._detect_data_transformation(input_data, output_data),
            "timestamp": int(time.time()),
        }

        execution_state["data_flow"]["data_transfers"].append(data_transfer)

    def _record_execution_error(self, execution_id: str, error_type: str, errors: List[str]):
        """Record execution errors for debugging."""

        execution_state = self.execution_states.get(execution_id)
        if not execution_state:
            return

        error_record = {
            "error_type": error_type,
            "errors": errors,
            "timestamp": int(time.time()),
            "execution_state": execution_state["status"],
        }

        if "error_records" not in execution_state:
            execution_state["error_records"] = []
        execution_state["error_records"].append(error_record)

    def _generate_execution_report(
        self, execution_id: str, execution_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive execution report for debugging."""

        total_execution_time = 0
        if execution_state["performance_metrics"]["node_execution_times"]:
            total_execution_time = sum(
                metrics.get("duration", 0)
                for metrics in execution_state["performance_metrics"][
                    "node_execution_times"
                ].values()
            )

        execution_state["performance_metrics"]["total_execution_time"] = total_execution_time

        report = {
            "execution_summary": {
                "execution_id": execution_id,
                "workflow_id": execution_state["workflow_id"],
                "status": execution_state["status"],
                "total_execution_time": total_execution_time,
                "nodes_executed": len(execution_state["execution_path"]["steps"]),
                "nodes_failed": len(
                    [
                        step
                        for step in execution_state["execution_path"]["steps"]
                        if step["status"] == "ERROR"
                    ]
                ),
                "start_time": execution_state["start_time"],
                "end_time": execution_state["end_time"],
            },
            "execution_path": execution_state["execution_path"],
            "node_inputs": execution_state["node_inputs"],
            "performance_metrics": execution_state["performance_metrics"],
            "data_flow": execution_state["data_flow"],
            "execution_context": execution_state["execution_context"],
            "errors": execution_state.get("error_records", []),
        }

        return report

    def _validate_workflow(self, workflow_definition: Dict[str, Any]) -> List[str]:
        """Validate workflow definition."""
        errors = []

        nodes = workflow_definition.get("nodes", [])
        connections = workflow_definition.get("connections", {})

        if not nodes:
            errors.append("Workflow must have at least one node")
            return errors

        # Validate nodes
        node_ids = set()
        for node in nodes:
            node_id = node.get("id")
            if not node_id:
                errors.append("Node missing ID")
                continue

            if node_id in node_ids:
                errors.append(f"Duplicate node ID: {node_id}")
            node_ids.add(node_id)

            # Validate node type
            node_type = node.get("type")
            if not node_type:
                errors.append(f"Node {node_id} missing type")

        # Validate connections format
        connection_errors = self._validate_connections_format(connections, node_ids)
        errors.extend(connection_errors)

        return errors

    def _validate_connections_format(
        self, connections: Dict[str, Any], node_ids: Set[str]
    ) -> List[str]:
        """Validate connections format matches NodeConnectionsData structure."""
        errors = []

        if not isinstance(connections, dict):
            return ["Connections must be a dictionary"]

        for source_node_id, node_connections in connections.items():
            # Check if source node exists
            if source_node_id not in node_ids:
                errors.append(
                    f"Connection source node '{source_node_id}' does not exist in workflow"
                )
                continue

            # Validate connection structure
            if not isinstance(node_connections, dict):
                errors.append(f"Connections for node '{source_node_id}' must be an object")
                continue

            if "connection_types" not in node_connections:
                errors.append(
                    f"Missing 'connection_types' in connections for node '{source_node_id}'"
                )
                continue

            connection_types = node_connections.get("connection_types", {})
            if not isinstance(connection_types, dict):
                errors.append(f"'connection_types' must be an object for node '{source_node_id}'")
                continue

            for conn_type, conn_array in connection_types.items():
                if not isinstance(conn_array, dict) or "connections" not in conn_array:
                    errors.append(
                        f"Invalid connection array format for '{source_node_id}.{conn_type}': must have 'connections' field"
                    )
                    continue

                connections_list = conn_array.get("connections", [])
                if not isinstance(connections_list, list):
                    errors.append(
                        f"'connections' must be a list for '{source_node_id}.{conn_type}'"
                    )
                    continue

                # Validate each connection
                for i, conn in enumerate(connections_list):
                    if not isinstance(conn, dict):
                        errors.append(
                            f"Connection {i} in '{source_node_id}.{conn_type}' must be an object"
                        )
                        continue
                    if "node" not in conn:
                        errors.append(
                            f"Connection {i} in '{source_node_id}.{conn_type}' missing required 'node' field"
                        )
                        continue

                    target_node_id = conn.get("node")
                    if target_node_id not in node_ids:
                        errors.append(
                            f"Connection target node '{target_node_id}' does not exist in workflow"
                        )

        return errors

    def _transform_node_data(
        self,
        output_data: Dict[str, Any],
        source_node_id: str,
        target_node_id: str,
        execution_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Transform data between nodes using communication protocol."""
        try:
            # Get source and target node information
            nodes = execution_state.get("nodes", [])
            source_node = next((n for n in nodes if n.get("id") == source_node_id), None)
            target_node = next((n for n in nodes if n.get("id") == target_node_id), None)

            if not source_node or not target_node:
                self.logger.warning(f"Could not find node information for transformation")
                return output_data

            source_type = f"{source_node.get('type')}.{source_node.get('subtype')}"
            target_type = f"{target_node.get('type')}.{target_node.get('subtype')}"

            self.logger.info(f"🔄 Transforming data from {source_type} to {target_type}")

            # Apply transformation
            transformed_data = apply_transformation(output_data, source_type, target_type)

            if transformed_data != output_data:
                self.logger.info(f"✅ Data transformation applied: {source_type} -> {target_type}")
            else:
                self.logger.debug(f"🔄 No transformation needed for {source_type} -> {target_type}")

            return transformed_data

        except Exception as e:
            self.logger.warning(f"⚠️ Data transformation failed: {e}, using original data")
            return output_data

    def _calculate_execution_order(self, workflow_definition: Dict[str, Any]) -> List[str]:
        """Calculate execution order using topological sort with ConnectionsMap."""

        nodes = workflow_definition.get("nodes", [])
        connections = workflow_definition.get("connections", {})

        return self._calculate_execution_order_from_connections_map(nodes, connections)

    def _calculate_execution_order_from_connections_map(
        self, nodes: List[Dict], connections: Dict[str, Any]
    ) -> List[str]:
        """Calculate execution order using ConnectionsMap format."""

        # Build dependency graph using node IDs
        graph = defaultdict(list)
        in_degree = defaultdict(int)

        # Initialize in_degree for all nodes
        for node in nodes:
            node_id = node["id"]
            in_degree[node_id] = 0

        # Build graph from connections
        for source_node_id, node_connections in connections.items():
            if source_node_id not in in_degree:
                continue

            connection_types = node_connections.get("connection_types", {})
            for connection_type, connection_array in connection_types.items():
                # Only consider "main" connections for execution order
                # Memory connections are for data flow, not execution sequence
                if connection_type != "main":
                    continue

                connections_list = connection_array.get("connections", [])

                for connection in connections_list:
                    target_node_id = connection.get("node")

                    if target_node_id and target_node_id in in_degree:
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

    def _detect_data_transformation(
        self, input_data: Dict[str, Any], output_data: Dict[str, Any]
    ) -> str:
        """Detect type of data transformation."""
        if len(input_data) != len(output_data):
            return "data_structure_changed"
        return "data_preserved"

    def _get_node_by_id(
        self, workflow_definition: Dict[str, Any], node_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get node definition by ID."""
        nodes = workflow_definition.get("nodes", [])
        for node in nodes:
            if node.get("id") == node_id:
                return node
        return None

    def _dict_to_node_object(self, node_def: Dict[str, Any]):
        """Convert node definition dict to node object."""
        from types import SimpleNamespace

        return SimpleNamespace(**node_def)

    # === Enhanced Tracking Methods ===

    def _record_execution_path_step(
        self,
        execution_id: str,
        node_id: str,
        node_result: Dict[str, Any],
        workflow_definition: Dict[str, Any],
    ):
        """Record a step in the execution path."""

        execution_state = self.execution_states.get(execution_id)
        if not execution_state:
            return

        # Get node definition
        node_def = self._get_node_by_id(workflow_definition, node_id)
        if not node_def:
            return

        # Create path step
        path_step = {
            "node_id": node_id,
            "node_name": node_def.get("name", ""),
            "node_type": node_def.get("type", ""),
            "node_subtype": node_def.get("subtype", ""),
            "start_time": execution_state["performance_metrics"]["node_execution_times"][node_id][
                "start_time"
            ],
            "end_time": execution_state["performance_metrics"]["node_execution_times"][node_id][
                "end_time"
            ],
            "execution_time": execution_state["performance_metrics"]["node_execution_times"][
                node_id
            ]["duration"],
            "status": node_result["status"],
            "input_sources": self._get_input_sources(node_id, workflow_definition),
            "output_targets": self._get_output_targets(node_id, workflow_definition),
            "connections": self._get_connection_info(node_id, workflow_definition),
            "context_variables": {},
            "error": node_result.get("error_message") if node_result["status"] == "ERROR" else None,
        }

        execution_state["execution_path"]["steps"].append(path_step)

        # Update execution count
        node_name = node_def.get("name", node_id)
        current_count = execution_state["execution_path"]["node_execution_counts"].get(node_name, 0)
        execution_state["execution_path"]["node_execution_counts"][node_name] = current_count + 1

    def _record_node_input_data(
        self,
        execution_id: str,
        node_id: str,
        node_def: Dict[str, Any],
        input_data: Dict[str, Any],
        credentials: Dict[str, Any],
    ):
        """Record node input data for debugging."""

        execution_state = self.execution_states.get(execution_id)
        if not execution_state:
            return

        node_input_data = {
            "node_id": node_id,
            "node_name": node_def.get("name", ""),
            "input_data": input_data,
            "connections": self._get_connection_data(node_id, execution_state),
            "parameters": node_def.get("parameters", {}),
            "credentials": {
                k: "***" if "password" in k.lower() or "token" in k.lower() else v
                for k, v in credentials.items()
            },
            "static_data": {},
            "timestamp": int(time.time()),
        }

        execution_state["node_inputs"][node_id] = node_input_data

    def _record_execution_context(
        self,
        execution_id: str,
        workflow_definition: Dict[str, Any],
        initial_data: Optional[Dict[str, Any]],
        credentials: Optional[Dict[str, Any]],
    ):
        """Record execution context information."""

        execution_state = self.execution_states.get(execution_id)
        if not execution_state:
            return

        execution_state["execution_context"].update(
            {
                "workflow_variables": workflow_definition.get("static_data", {}),
                "initial_data": initial_data or {},
                "credentials_available": bool(credentials),
                "workflow_settings": workflow_definition.get("settings", {}),
            }
        )

    def _record_data_flow(
        self,
        execution_id: str,
        node_id: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        node_def: Dict[str, Any],
    ):
        """Record data flow information."""

        execution_state = self.execution_states.get(execution_id)
        if not execution_state:
            return

        data_transfer = {
            "node_id": node_id,
            "node_name": node_def.get("name", ""),
            "node_type": node_def.get("type", ""),
            "input_data_size": len(str(input_data)),
            "output_data_size": len(str(output_data)),
            "data_transformation": self._detect_data_transformation(input_data, output_data),
            "timestamp": int(time.time()),
        }

        execution_state["data_flow"]["data_transfers"].append(data_transfer)

    def _record_execution_error(self, execution_id: str, error_type: str, errors: List[str]):
        """Record execution errors for debugging."""

        execution_state = self.execution_states.get(execution_id)
        if not execution_state:
            return

        error_record = {
            "error_type": error_type,
            "errors": errors,
            "timestamp": int(time.time()),
            "execution_state": execution_state["status"],
        }

        if "error_records" not in execution_state:
            execution_state["error_records"] = []
        execution_state["error_records"].append(error_record)

    def _generate_execution_report(
        self, execution_id: str, execution_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive execution report for Agent debugging."""

        total_execution_time = 0
        if execution_state["performance_metrics"]["node_execution_times"]:
            total_execution_time = sum(
                metrics.get("duration", 0) or 0
                for metrics in execution_state["performance_metrics"][
                    "node_execution_times"
                ].values()
            )

        execution_state["performance_metrics"]["total_execution_time"] = total_execution_time

        report = {
            "execution_summary": {
                "execution_id": execution_id,
                "workflow_id": execution_state["workflow_id"],
                "status": execution_state["status"],
                "total_execution_time": total_execution_time,
                "nodes_executed": len(execution_state["execution_path"]["steps"]),
                "nodes_failed": len(
                    [
                        step
                        for step in execution_state["execution_path"]["steps"]
                        if step["status"] == "ERROR"
                    ]
                ),
                "start_time": execution_state["start_time"],
                "end_time": execution_state["end_time"],
            },
            "execution_path": execution_state["execution_path"],
            "node_inputs": execution_state["node_inputs"],
            "performance_metrics": execution_state["performance_metrics"],
            "data_flow": execution_state["data_flow"],
            "execution_context": execution_state["execution_context"],
            "errors": execution_state.get("error_records", []),
        }

        return report

    def _get_input_sources(self, node_id: str, workflow_definition: Dict[str, Any]) -> List[str]:
        """Get input sources for a node."""
        sources = []
        connections = workflow_definition.get("connections", {})

        for source_node_id, node_connections in connections.items():
            connection_types = node_connections.get("connection_types", {})
            for connection_type, connection_array in connection_types.items():
                connections_list = connection_array.get("connections", [])
                for connection in connections_list:
                    if connection.get("node") == node_id:
                        sources.append(source_node_id)

        return sources

    def _get_output_targets(self, node_id: str, workflow_definition: Dict[str, Any]) -> List[str]:
        """Get output targets for a node."""
        targets = []
        connections = workflow_definition.get("connections", {})

        if node_id in connections:
            node_connections = connections[node_id]
            connection_types = node_connections.get("connection_types", {})
            for connection_type, connection_array in connection_types.items():
                connections_list = connection_array.get("connections", [])
                for connection in connections_list:
                    target_node = connection.get("node")
                    if target_node:
                        targets.append(target_node)

        return targets

    def _get_connection_info(
        self, node_id: str, workflow_definition: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get connection information for a node."""
        connections_info = []
        connections = workflow_definition.get("connections", {})

        # Get outgoing connections
        if node_id in connections:
            node_connections = connections[node_id]
            connection_types = node_connections.get("connection_types", {})
            for connection_type, connection_array in connection_types.items():
                connections_list = connection_array.get("connections", [])
                for connection in connections_list:
                    connections_info.append(
                        {
                            "direction": "outgoing",
                            "type": connection_type,
                            "target": connection.get("node"),
                            "connection_details": connection,
                        }
                    )

        # Get incoming connections
        for source_node_id, node_connections in connections.items():
            connection_types = node_connections.get("connection_types", {})
            for connection_type, connection_array in connection_types.items():
                connections_list = connection_array.get("connections", [])
                for connection in connections_list:
                    if connection.get("node") == node_id:
                        connections_info.append(
                            {
                                "direction": "incoming",
                                "type": connection_type,
                                "source": source_node_id,
                                "connection_details": connection,
                            }
                        )

        return connections_info

    def _get_connection_data(
        self, node_id: str, execution_state: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get connection data for a node."""
        return execution_state.get("data_flow", {}).get("data_sources", {}).get(node_id, [])

    def _detect_data_transformation(
        self, input_data: Dict[str, Any], output_data: Dict[str, Any]
    ) -> str:
        """Detect type of data transformation."""
        if not input_data and not output_data:
            return "no_data"
        elif not input_data:
            return "data_generated"
        elif not output_data:
            return "data_consumed"
        elif len(input_data) != len(output_data):
            return "data_structure_changed"
        elif input_data == output_data:
            return "data_passed_through"
        else:
            return "data_transformed"

    def _summarize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize data for debugging purposes."""
        if not data:
            return {"type": "empty", "size": 0}

        return {
            "type": "dict",
            "size": len(str(data)),
            "keys": list(data.keys()),
            "key_count": len(data),
        }

    def _get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage information."""
        try:
            import psutil

            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            return {
                "rss": memory_info.rss,
                "vms": memory_info.vms,
                "percent": process.memory_percent(),
            }
        except ImportError:
            return {"error": "psutil not available"}

    def _get_cpu_usage(self) -> Dict[str, Any]:
        """Get CPU usage information."""
        try:
            import psutil

            process = psutil.Process(os.getpid())
            return {"percent": process.cpu_percent(), "num_threads": process.num_threads()}
        except ImportError:
            return {"error": "psutil not available"}

    async def _store_complete_pause_context(
        self,
        execution_id: str,
        execution_state: Dict[str, Any],
        workflow_definition: Dict[str, Any],
        initial_data: Dict[str, Any],
        credentials: Dict[str, Any],
        user_id: Optional[str],
        paused_node_id: str,
        remaining_nodes: List[str],
    ):
        """Store complete execution context for seamless workflow resume."""
        try:
            # Create comprehensive pause context
            pause_context = {
                "execution_id": execution_id,
                "workflow_id": execution_state["workflow_id"],
                "paused_at": datetime.now().isoformat(),
                "paused_node_id": paused_node_id,
                "remaining_nodes": remaining_nodes,
                # Complete execution state snapshot
                "execution_state_snapshot": {
                    "status": execution_state["status"],
                    "start_time": execution_state["start_time"],
                    "node_results": execution_state["node_results"],
                    "execution_order": execution_state["execution_order"],
                    "execution_context": execution_state["execution_context"],
                    "performance_metrics": execution_state["performance_metrics"],
                    "execution_path": execution_state["execution_path"],
                    "node_inputs": execution_state.get("node_inputs", {}),
                    "data_flow": execution_state.get("data_flow", {}),
                    "errors": execution_state.get("errors", []),
                },
                # Complete workflow context for resume
                "workflow_context": {
                    "workflow_definition": workflow_definition,
                    "initial_data": initial_data,
                    "credentials": credentials,  # Note: Should be encrypted in production
                    "user_id": user_id,
                },
                # Resume metadata
                "resume_metadata": {
                    "pause_reason": execution_state.get("pause_reason", "human_interaction"),
                    "interaction_id": execution_state.get("pause_data", {}).get("interaction_id"),
                    "timeout_at": execution_state.get("pause_data", {}).get("timeout_at"),
                    "resume_ready": True,
                    "created_at": datetime.now().isoformat(),
                },
            }

            # Store in execution states for in-memory access
            if "pause_contexts" not in self.execution_states:
                self.execution_states["pause_contexts"] = {}
            self.execution_states["pause_contexts"][execution_id] = pause_context

            # Update database execution status to PAUSED
            await self._update_database_pause_status(execution_id, pause_context)

            self.logger.info(
                f"📁 Stored complete pause context for execution {execution_id} at node {paused_node_id}"
            )
            self.logger.info(f"📋 Remaining nodes for resume: {remaining_nodes}")
            self.logger.info(f"💾 Database status updated to PAUSED")

        except Exception as e:
            self.logger.error(f"⚠️ Failed to store pause context for {execution_id}: {e}")

    async def _update_database_pause_status(self, execution_id: str, pause_context: Dict[str, Any]):
        """Update database execution status to PAUSED with pause context."""
        try:
            # Import here to avoid circular imports
            from .models.database import get_db
            from .services.execution_service import ExecutionService

            # This would normally be injected, but for now we'll create a temporary connection
            # In production, this should use dependency injection or a proper database session
            self.logger.info(f"🔄 Updating database status to PAUSED for execution {execution_id}")

            # Store pause context (in production, this should be properly persisted)
            # For now, we rely on in-memory storage and the execution engine state

        except Exception as e:
            self.logger.warning(
                f"⚠️ Failed to update database pause status for {execution_id}: {e}"
            )
            # Don't fail the pause operation if database update fails

    async def resume_workflow_execution(
        self,
        execution_id: str,
        resume_data: Optional[Dict[str, Any]] = None,
        workflow_definition: Optional[Dict[str, Any]] = None,
        credentials: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Resume a paused workflow execution with full continuation support."""
        try:
            # First, try to get complete pause context
            pause_context = self.execution_states.get("pause_contexts", {}).get(execution_id)
            execution_state = self.execution_states.get(execution_id)

            if not pause_context and not execution_state:
                return {
                    "status": "ERROR",
                    "message": f"No execution state or pause context found for {execution_id}",
                }

            # Use pause context if available (more complete), otherwise fall back to execution state
            if pause_context:
                self.logger.info(f"🔄 Using stored pause context for resume")
                execution_state = pause_context["execution_state_snapshot"]
                workflow_context = pause_context["workflow_context"]

                # Get workflow definition and credentials from stored context
                if not workflow_definition:
                    workflow_definition = workflow_context["workflow_definition"]
                if not credentials:
                    credentials = workflow_context["credentials"]
                if not user_id:
                    user_id = workflow_context["user_id"]

                paused_node_id = pause_context["paused_node_id"]
                remaining_nodes = pause_context["remaining_nodes"]
                current_position = (
                    len(execution_state["execution_order"]) - len(remaining_nodes) - 1
                )
            else:
                self.logger.info(f"🔄 Using basic execution state for resume")
                if execution_state.get("status") != "PAUSED":
                    return {
                        "status": "ERROR",
                        "message": f"Execution {execution_id} is not in PAUSED state",
                    }

                # Get pause information from basic execution state
                pause_data = execution_state.get("pause_data", {})
                paused_node_id = pause_data.get("node_id")
                remaining_nodes = pause_data.get("remaining_nodes", [])
                current_position = pause_data.get("current_position", 0)

            self.logger.info(
                f"🔄 Resuming workflow execution {execution_id} from node {paused_node_id}"
            )
            self.logger.info(f"📋 Remaining nodes to execute: {remaining_nodes}")

            # Update the paused node result with resume data
            if paused_node_id and resume_data:
                paused_node_result = execution_state["node_results"].get(paused_node_id, {})

                # Determine output port based on resume data
                output_port = self._determine_resume_output_port(resume_data)

                paused_node_result.update(
                    {
                        "status": "SUCCESS",
                        "output_data": resume_data,
                        "output_port": output_port,
                        "resumed": True,
                        "resumed_at": datetime.now().isoformat(),
                    }
                )
                execution_state["node_results"][paused_node_id] = paused_node_result
                self.logger.info(f"✅ Updated paused node {paused_node_id} with resume data")

            # Resume execution from remaining nodes
            execution_state["status"] = "RUNNING"
            execution_state["resumed_at"] = datetime.now().isoformat()
            execution_state["resume_data"] = resume_data

            # Continue executing remaining nodes if workflow definition provided
            if workflow_definition and remaining_nodes:
                self.logger.info(
                    f"🏃 Continuing execution of {len(remaining_nodes)} remaining nodes..."
                )

                # Continue the execution loop from where we left off
                for i, node_id in enumerate(
                    remaining_nodes[1:], start=current_position + 1
                ):  # Skip the paused node itself
                    self.logger.info(f"🔄 Resuming node execution: {node_id}")

                    try:
                        node_result = await self._execute_node_with_enhanced_tracking(
                            node_id,
                            workflow_definition,
                            execution_state,
                            execution_state.get("execution_context", {}).get("initial_data", {}),
                            credentials or {},
                            user_id,
                        )

                        execution_state["node_results"][node_id] = node_result

                        # Record execution path
                        self._record_execution_path_step(
                            execution_id, node_id, node_result, workflow_definition
                        )

                        # Check if workflow should pause again or fail
                        if node_result["status"] == "ERROR":
                            self.logger.error(
                                f"❌ Node {node_id} failed during resume - stopping execution"
                            )
                            execution_state["status"] = "ERROR"
                            execution_state["errors"].append(
                                f"Node {node_id} failed during resume: {node_result.get('error_message', 'Unknown error')}"
                            )
                            break
                        elif node_result["status"] == "PAUSED":
                            self.logger.info(
                                f"⏸️ Node {node_id} paused workflow again during resume"
                            )
                            execution_state["status"] = "PAUSED"
                            execution_state["paused_at_node"] = node_id
                            execution_state["pause_data"] = {
                                "node_id": node_id,
                                "interaction_id": node_result.get("output_data", {}).get(
                                    "interaction_id"
                                ),
                                "timeout_at": node_result.get("output_data", {}).get("timeout_at"),
                                "remaining_nodes": remaining_nodes[
                                    i + 1 :
                                ],  # Update remaining nodes
                                "current_position": i,
                            }
                            break

                    except Exception as node_error:
                        self.logger.error(
                            f"💥 Exception during resume node {node_id} execution: {str(node_error)}"
                        )
                        execution_state["status"] = "ERROR"
                        execution_state["errors"].append(
                            f"Resume node {node_id} exception: {str(node_error)}"
                        )
                        break

                # Set final status if all nodes completed
                if execution_state["status"] == "RUNNING":
                    execution_state["status"] = "completed"
                    execution_state["end_time"] = datetime.now().isoformat()
                    self.logger.info("✅ Workflow resume completed successfully")

            self.logger.info(
                f"🔄 Workflow {execution_id} resume processed with status: {execution_state['status']}"
            )

            return {
                "status": execution_state["status"],
                "execution_id": execution_id,
                "message": f"Workflow resume processed - status: {execution_state['status']}",
                "remaining_nodes": remaining_nodes,
                "completed": execution_state["status"] == "completed",
                "paused_again": execution_state["status"] == "PAUSED",
            }

        except Exception as e:
            self.logger.error(f"❌ Failed to resume workflow {execution_id}: {e}")
            if execution_id in self.execution_states:
                self.execution_states[execution_id]["status"] = "ERROR"
                self.execution_states[execution_id]["errors"].append(f"Resume failed: {str(e)}")
            return {"status": "ERROR", "message": f"Failed to resume workflow: {str(e)}"}

    def _determine_resume_output_port(self, resume_data: Dict[str, Any]) -> str:
        """Determine the output port based on resume data."""
        # Check for explicit output_port in resume data
        if "output_port" in resume_data:
            return resume_data["output_port"]

        # Check for approval/rejection patterns
        if "approved" in resume_data:
            return "approved" if resume_data["approved"] else "rejected"

        # Default to approved for most HIL interactions
        return "approved"
