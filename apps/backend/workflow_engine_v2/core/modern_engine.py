"""
Modern Workflow Execution Engine V2

A streamlined, user-focused execution engine that integrates comprehensive logging
with the API Gateway's user-friendly logs endpoint. No backward compatibility concerns.

Key Features:
- User-friendly progress logging
- Real-time step tracking with input/output summaries
- Direct Supabase integration for logs
- Performance monitoring
- Error context with clear messaging
- Milestone tracking
"""

from __future__ import annotations

import asyncio
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Use absolute imports
from shared.models import ExecutionStatus
from shared.models.execution_new import Execution, TriggerInfo
from shared.models.node_enums import NodeType
from shared.models.workflow_new import Node, Workflow
from workflow_engine_v2.core.exceptions import EngineError, ExecutionFailure
from workflow_engine_v2.core.graph import WorkflowGraph
from workflow_engine_v2.core.spec import get_spec
from workflow_engine_v2.runners.factory import default_runner_for
from workflow_engine_v2.services.user_friendly_logger import LogLevel, get_user_friendly_logger


class NodeResult:
    """Result of node execution"""

    def __init__(
        self,
        node_id: str,
        success: bool,
        outputs: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        duration_ms: Optional[float] = None,
        output_summary: Optional[str] = None,
    ):
        self.node_id = node_id
        self.success = success
        self.outputs = outputs or {}
        self.error = error
        self.duration_ms = duration_ms
        self.output_summary = output_summary


class ModernExecutionEngine:
    """Modern workflow execution engine with comprehensive user-friendly logging"""

    def __init__(self, max_concurrent_nodes: int = 5):
        self.max_concurrent_nodes = max_concurrent_nodes
        self.logger = get_user_friendly_logger()

    async def execute_workflow(
        self, workflow: Workflow, trigger: TriggerInfo, trace_id: Optional[str] = None
    ) -> Execution:
        """Execute a workflow with comprehensive logging"""

        # Generate execution ID and trace ID
        execution_id = str(uuid.uuid4())
        trace_id = trace_id or str(uuid.uuid4())

        # Create execution object
        execution = Execution(
            id=execution_id,
            execution_id=execution_id,
            workflow_id=workflow.metadata.id,
            workflow_version=workflow.metadata.version,
            status=ExecutionStatus.RUNNING,
            start_time=int(time.time() * 1000),
            trigger_info=trigger,
        )

        # Prepare for user-friendly logging (log actual total after graph filter)
        workflow_name = workflow.metadata.name or "Unnamed Workflow"
        trigger_description = self._get_trigger_description(trigger)

        start_time = time.time()

        try:
            # Validate workflow
            self._validate_workflow(workflow)

            # Build execution graph
            graph = WorkflowGraph(workflow)

            # Determine entry nodes based on invoked trigger type
            entry_nodes: List[str] = []
            try:
                invoked_type = (
                    trigger.trigger_type if hasattr(trigger, "trigger_type") else None
                ) or ""
                invoked_type = str(invoked_type).upper()
                if invoked_type:
                    from shared.models.node_enums import NodeType as _NodeType

                    for n in workflow.nodes:
                        ntype = str(n.type).upper()
                        nsub = str(n.subtype).upper() if n.subtype else ""
                        if ntype == _NodeType.TRIGGER.value and nsub == invoked_type:
                            entry_nodes.append(n.id)
            except Exception:
                entry_nodes = []

            # Compute execution order and restrict to nodes reachable from entry nodes if provided
            full_order = graph.topo_order()  # Raises on cycle
            if entry_nodes:
                allowed = set(graph.reachable_from(entry_nodes)) | set(entry_nodes)
                execution_order = [nid for nid in full_order if nid in allowed]
            else:
                execution_order = full_order

            # Add graph debugging
            import logging

            logger = logging.getLogger(__name__)
            logger.debug(f"🔗 WORKFLOW CONNECTIONS: {len(workflow.connections)}")
            for conn in workflow.connections:
                logger.debug(
                    f"   📎 {conn.from_node}:{conn.from_port} → {conn.to_node}:{conn.to_port}"
                )
            logger.debug(f"📊 EXECUTION ORDER: {execution_order}")
            logger.debug(f"🎯 TOTAL NODES TO EXECUTE: {len(execution_order)}")
            if entry_nodes and len(execution_order) <= len(entry_nodes):
                logger.warning(
                    f"No downstream nodes reachable from trigger(s) {entry_nodes}. "
                    f"Verify workflow.connections have edges from these trigger node IDs to next nodes."
                )

            # Initialize user-friendly logging with accurate step count
            self.logger.log_workflow_start(
                execution=execution,
                workflow_name=workflow_name,
                total_nodes=len(execution_order),
                trigger_info=trigger_description,
            )

            # Execute workflow
            results = await self._execute_nodes(
                execution=execution, workflow=workflow, graph=graph, execution_order=execution_order
            )

            # Determine final status
            failed_results = [r for r in results.values() if not r.success]
            if failed_results:
                execution.status = ExecutionStatus.ERROR
                # Add detailed debugging for failed nodes
                import logging

                logger = logging.getLogger(__name__)
                logger.error(
                    f"🔍 DEBUG: {len(failed_results)} nodes failed out of {len(results)} total"
                )
                for result in failed_results:
                    logger.error(f"🔍 FAILED NODE: {result.node_id} - Success: {result.success}")
                    if hasattr(result, "error_message"):
                        logger.error(f"🔍 ERROR MESSAGE: {result.error_message}")
                    if hasattr(result, "outputs"):
                        logger.error(f"🔍 OUTPUTS: {result.outputs}")
                    if hasattr(result, "debug_info"):
                        logger.error(f"🔍 DEBUG INFO: {result.debug_info}")
                self.logger.log_workflow_complete(
                    execution=execution,
                    success=False,
                    duration_ms=(time.time() - start_time) * 1000,
                    summary={
                        "failed_nodes": len(failed_results),
                        "successful_nodes": len(results) - len(failed_results),
                        "error_summary": failed_results[0].error if failed_results else None,
                    },
                )
            else:
                execution.status = ExecutionStatus.COMPLETED
                self.logger.log_workflow_complete(
                    execution=execution,
                    success=True,
                    duration_ms=(time.time() - start_time) * 1000,
                    summary={"total_nodes": len(results), "successful_nodes": len(results)},
                )

            execution.end_time = int(time.time() * 1000)
            return execution

        except Exception as e:
            execution.status = ExecutionStatus.ERROR
            execution.end_time = int(time.time() * 1000)

            self.logger.log_workflow_complete(
                execution=execution,
                success=False,
                duration_ms=(time.time() - start_time) * 1000,
                summary={"error": str(e), "error_type": type(e).__name__},
            )

            raise ExecutionFailure(f"Workflow execution failed: {str(e)}") from e

    async def _execute_nodes(
        self,
        execution: Execution,
        workflow: Workflow,
        graph: WorkflowGraph,
        execution_order: List[str],
    ) -> Dict[str, NodeResult]:
        """Execute workflow nodes in dependency order"""

        results: Dict[str, NodeResult] = {}
        pending_inputs: Dict[str, Dict[str, Any]] = {n.id: {} for n in workflow.nodes}

        # Process nodes in topological order
        import logging

        logger = logging.getLogger(__name__)

        for node_id in execution_order:
            node = graph.nodes[node_id]
            logger.debug(f"🔄 PROCESSING NODE: {node_id}")

            # Check if node is ready (all dependencies completed)
            dependencies_ready = self._are_dependencies_ready(node_id, graph, results)
            logger.debug(f"   ✅ Dependencies ready: {dependencies_ready}")
            if not dependencies_ready:
                # Should not happen with proper topological ordering
                logger.warning(f"   ⚠️ SKIPPING {node_id} - dependencies not ready")
                continue

            # Prepare input data from predecessor nodes
            input_data = pending_inputs.get(node_id, {})
            self._populate_node_inputs(node, graph, results, input_data)

            # Execute node
            try:
                result = await self._execute_single_node(
                    execution=execution, node=node, input_data=input_data
                )
                results[node_id] = result

                # Propagate outputs to successor nodes
                if result.success and result.outputs:
                    self._propagate_outputs(node, graph, result.outputs, pending_inputs)

            except Exception as e:
                # Node execution failed
                result = NodeResult(
                    node_id=node_id,
                    success=False,
                    error=str(e),
                    output_summary=f"Execution failed: {str(e)}",
                )
                results[node_id] = result

                self.logger.log_node_complete(
                    execution_id=execution.execution_id,
                    node_id=node_id,
                    success=False,
                    error_message=str(e),
                )

                # Decide whether to continue or fail workflow
                if self._should_stop_on_failure(node, workflow):
                    break

        return results

    async def _execute_single_node(
        self, execution: Execution, node: Node, input_data: Dict[str, Any]
    ) -> NodeResult:
        """Execute a single node with comprehensive logging"""

        # Create input summary for logging
        input_summary = self._create_parameter_summary(input_data, "input")

        # Log node start
        self.logger.log_node_start(
            execution_id=execution.execution_id, node=node, input_summary=input_summary
        )

        start_time = time.time()

        try:
            # Log input validation phase
            self.logger.log_node_phase(
                execution_id=execution.execution_id,
                node_id=node.id,
                phase="VALIDATING_INPUTS",
                details=f"Validating {len(input_data)} input parameters",
            )

            # Get node specification and runner
            spec = get_spec(node.type, node.subtype)
            runner = default_runner_for(node)

            # Log processing phase
            self.logger.log_node_phase(
                execution_id=execution.execution_id, node_id=node.id, phase="PROCESSING"
            )

            # Execute node
            context = {
                "execution_id": execution.execution_id,
                "node_id": node.id,
                "trace_id": getattr(execution, "trace_id", None),
            }

            # Add detailed execution logging with clear formatting
            import json
            import logging

            logger = logging.getLogger(__name__)

            # Format node name clearly
            node_name = node.name or node.id
            logger.info(f"\n{'='*80}")
            logger.info(f"[{node_name}] Starting execution")
            logger.info(f"  Type: {node.type}.{node.subtype}")
            logger.info(f"  Node ID: {node.id}")

            # Log inputs clearly
            if input_data:
                logger.info(f"\n[{node_name}] 📥 INPUTS:")
                for port_name, port_data in input_data.items():
                    if isinstance(port_data, dict):
                        logger.info(f"  • {port_name}:")
                        for key, value in list(port_data.items())[:5]:  # Show first 5 items
                            value_str = (
                                json.dumps(value)[:200]
                                if not isinstance(value, (str, int, float, bool))
                                else str(value)
                            )
                            logger.info(f"    - {key}: {value_str}")
                        if len(port_data) > 5:
                            logger.info(f"    ... and {len(port_data) - 5} more fields")
                    else:
                        value_str = str(port_data)[:200]
                        logger.info(f"  • {port_name}: {value_str}")
            else:
                logger.info(f"\n[{node_name}] 📥 INPUTS: (none)")

            logger.info(f"\n[{node_name}] 🏃 Executing with {type(runner).__name__}...")

            if hasattr(runner, "run_async"):
                result_data = await runner.run_async(node=node, inputs=input_data, context=context)
            else:
                # Run sync runner in thread pool
                loop = asyncio.get_event_loop()
                result_data = await loop.run_in_executor(
                    None, runner.run, node, input_data, execution.trigger_info
                )

            # Process results
            duration_ms = (time.time() - start_time) * 1000
            outputs = result_data.get("outputs", {}) if isinstance(result_data, dict) else {}

            # If no outputs at root level, check for result output port (common pattern)
            if not outputs and isinstance(result_data, dict) and "result" in result_data:
                outputs = {"result": result_data["result"]}

            # Log outputs clearly
            logger.info(f"\n[{node_name}] 📤 OUTPUTS:")
            if outputs:
                for port_name, port_data in outputs.items():
                    if isinstance(port_data, dict):
                        logger.info(f"  • {port_name}:")
                        for key, value in list(port_data.items())[:5]:  # Show first 5 items
                            value_str = (
                                json.dumps(value)[:200]
                                if not isinstance(value, (str, int, float, bool))
                                else str(value)
                            )
                            logger.info(f"    - {key}: {value_str}")
                        if len(port_data) > 5:
                            logger.info(f"    ... and {len(port_data) - 5} more fields")
                    else:
                        value_str = str(port_data)[:200]
                        logger.info(f"  • {port_name}: {value_str}")
            else:
                logger.info(f"  (no outputs)")

            # Check for errors in result
            if isinstance(result_data, dict) and "error" in result_data:
                logger.warning(f"\n[{node_name}] ⚠️  ERROR in result:")
                error_info = result_data["error"]
                if isinstance(error_info, dict):
                    logger.warning(f"  Message: {error_info.get('message', 'Unknown error')}")
                    if "details" in error_info:
                        logger.warning(
                            f"  Details: {json.dumps(error_info['details'], indent=2)[:300]}"
                        )
                else:
                    logger.warning(f"  {error_info}")

            logger.info(f"\n[{node_name}] ✅ Completed in {duration_ms:.2f}ms")
            logger.info(f"{'='*80}\n")
            output_summary = self._create_parameter_summary(outputs, "output")

            # Handle special node types
            if str(node.type) == "HUMAN_IN_THE_LOOP":
                self._handle_hil_node(execution.execution_id, node, result_data)

            # Log completion
            self.logger.log_node_complete(
                execution_id=execution.execution_id,
                node_id=node.id,
                success=True,
                duration_ms=duration_ms,
                output_summary=output_summary,
            )

            return NodeResult(
                node_id=node.id,
                success=True,
                outputs=outputs,
                duration_ms=duration_ms,
                output_summary=output_summary,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_message = str(e)

            # Add detailed error logging for debugging
            import logging
            import traceback

            logger = logging.getLogger(__name__)
            node_name = node.name or node.id

            logger.error(f"\n[{node_name}] ❌ EXECUTION FAILED")
            logger.error(f"  Error: {error_message}")
            logger.error(f"  Duration: {duration_ms:.2f}ms")
            logger.error(f"  Traceback:\n{traceback.format_exc()}")
            logger.error(f"{'='*80}\n")

            self.logger.log_node_complete(
                execution_id=execution.execution_id,
                node_id=node.id,
                success=False,
                duration_ms=duration_ms,
                error_message=error_message,
            )

            return NodeResult(
                node_id=node.id, success=False, error=error_message, duration_ms=duration_ms
            )

    def _handle_hil_node(self, execution_id: str, node: Node, result_data: Any):
        """Handle special logging for Human-in-the-Loop nodes"""
        config = dict(node.configurations) if node.configurations else {}

        interaction_type = config.get("interaction_type", "approval")
        timeout_minutes = config.get("timeout_minutes", 60)

        message = f"Waiting for {interaction_type}"
        if "message_template" in config:
            message = (
                config["message_template"][:100] + "..."
                if len(config["message_template"]) > 100
                else config["message_template"]
            )

        self.logger.log_human_interaction(
            execution_id=execution_id,
            node_id=node.id,
            interaction_type=interaction_type,
            message=message,
            timeout_minutes=timeout_minutes,
        )

    def _create_parameter_summary(self, parameters: Dict[str, Any], param_type: str) -> str:
        """Create a concise summary of parameters for user-friendly logging"""
        if not parameters:
            return f"No {param_type} parameters"

        if len(parameters) == 1:
            key, value = next(iter(parameters.items()))
            if isinstance(value, str) and len(value) < 50:
                return f"{key}: '{value}'"
            elif isinstance(value, (int, float, bool)):
                return f"{key}: {value}"
            elif isinstance(value, (list, dict)):
                return f"{key}: {type(value).__name__}({len(value)} items)"
            else:
                return f"{key}: {type(value).__name__}"

        # Multiple parameters
        param_summary = []
        for key, value in list(parameters.items())[:3]:  # Show first 3 params
            if isinstance(value, str) and len(value) < 30:
                param_summary.append(f"{key}: '{value}'")
            elif isinstance(value, (int, float, bool)):
                param_summary.append(f"{key}: {value}")
            elif isinstance(value, (list, dict)):
                param_summary.append(f"{key}: {type(value).__name__}({len(value)})")
            else:
                param_summary.append(f"{key}: {type(value).__name__}")

        result = ", ".join(param_summary)
        if len(parameters) > 3:
            result += f" + {len(parameters) - 3} more"

        return result

    def _get_trigger_description(self, trigger: TriggerInfo) -> str:
        """Get user-friendly description of trigger"""
        trigger_type = trigger.trigger_type

        descriptions = {
            "MANUAL": "manual trigger",
            "WEBHOOK": f"webhook from {getattr(trigger, 'source', 'external system')}",
            "CRON": f"scheduled trigger",
            "SLACK": f"Slack message",
            "EMAIL": f"email trigger",
            "GITHUB": f"GitHub event",
        }

        return descriptions.get(trigger_type, f"{trigger_type.lower()} trigger")

    def _validate_workflow(self, workflow: Workflow):
        """Validate workflow before execution"""
        if not workflow.nodes:
            raise EngineError("Workflow has no nodes")

        # Validate that all nodes have valid specs and required configurations
        for node in workflow.nodes:
            try:
                spec = get_spec(node.type, node.subtype)

                # Validate external action nodes have required action_type
                if node.type == NodeType.EXTERNAL_ACTION:
                    if not node.configurations or not node.configurations.get("action_type"):
                        # Auto-fix missing action_type with sensible defaults
                        if not node.configurations:
                            node.configurations = {}

                        # Set default action_type based on external action subtype
                        default_actions = {
                            "SLACK": "send_message",
                            "GITHUB": "create_issue",
                            "GOOGLE_CALENDAR": "create_event",
                            "NOTION": "create_page",
                        }

                        default_action = default_actions.get(node.subtype, "default_action")
                        node.configurations["action_type"] = default_action

                        import logging

                        logger = logging.getLogger(__name__)
                        logger.info(
                            f"🔧 Auto-fixed missing action_type for {node.id}: {default_action}"
                        )

            except Exception as e:
                raise EngineError(f"Invalid node type/subtype: {node.type}.{node.subtype} - {e}")

    def _are_dependencies_ready(
        self, node_id: str, graph: WorkflowGraph, results: Dict[str, NodeResult]
    ) -> bool:
        """Check if all dependencies of a node are completed successfully"""
        predecessors = list(graph.predecessors(node_id))

        for pred_tuple in predecessors:
            # pred_tuple is (from_node, from_port, to_port, conversion_function)
            pred_node_id = pred_tuple[0]  # Extract the actual node ID
            if pred_node_id not in results or not results[pred_node_id].success:
                return False

        return True

    def _populate_node_inputs(
        self,
        node: Node,
        graph: WorkflowGraph,
        results: Dict[str, NodeResult],
        input_data: Dict[str, Any],
    ):
        """Populate node inputs from predecessor outputs using output_key"""
        # Find connections that target this node
        for connection in graph.workflow.connections:
            if connection.to_node == node.id:
                source_result = results.get(connection.from_node)
                if source_result and source_result.success:
                    # Use output_key if available (new), fallback to from_port (legacy compatibility)
                    output_key = getattr(connection, "output_key", None) or getattr(
                        connection, "from_port", "main"
                    )
                    source_output = source_result.outputs.get(output_key, {})

                    # Apply data transformation if present
                    if connection.conversion_function:
                        try:
                            # Execute conversion function directly
                            exec_globals = {}
                            exec(connection.conversion_function, exec_globals)

                            # Find the conversion function (try common names)
                            convert_func = (
                                exec_globals.get("convert")
                                or exec_globals.get("convert_trigger_to_ai")
                                or exec_globals.get("convert_ai_to_slack")
                            )

                            if convert_func:
                                converted_data = convert_func(source_output)
                                input_data[connection.to_port] = converted_data
                            else:
                                # No conversion function found, pass through
                                input_data[connection.to_port] = source_output

                            # Add debug logging
                            import logging

                            logger = logging.getLogger(__name__)
                            logger.debug(
                                f"🔄 TRANSFORMATION: {connection.from_node}:{connection.from_port} → {connection.to_node}:{connection.to_port}"
                            )
                            logger.debug(f"   📥 INPUT: {source_output}")
                            logger.debug(
                                f"   🔧 FUNCTION: {connection.conversion_function[:100]}..."
                            )
                            logger.debug(f"   📤 CONVERTED: {converted_data}")

                        except Exception as e:
                            # Log transformation error but continue with raw data
                            import logging

                            logger = logging.getLogger(__name__)
                            logger.error(f"❌ Data transformation failed: {e}")
                            input_data[connection.to_port] = source_output
                    else:
                        input_data[connection.to_port] = source_output

    def _propagate_outputs(
        self,
        node: Node,
        graph: WorkflowGraph,
        outputs: Dict[str, Any],
        pending_inputs: Dict[str, Dict[str, Any]],
    ):
        """Propagate node outputs to downstream nodes using output_key"""
        for connection in graph.workflow.connections:
            if connection.from_node == node.id:
                # Use output_key if available (new), fallback to from_port (legacy compatibility)
                output_key = getattr(connection, "output_key", None) or getattr(
                    connection, "from_port", "main"
                )

                # Get output data from the specified key
                output_data = outputs.get(output_key, {})

                # For input key, use to_port if available for backward compatibility, otherwise default to 'main'
                input_key = getattr(connection, "to_port", "main")

                if connection.to_node in pending_inputs:
                    pending_inputs[connection.to_node][input_key] = output_data

    def _should_stop_on_failure(self, node: Node, workflow: Workflow) -> bool:
        """Determine if workflow should stop when this node fails"""
        # Check node-specific settings (could be configured)
        node_config = dict(node.configurations) if node.configurations else {}
        if node_config.get("continue_on_failure", False):
            return False

        # Check workflow-level settings
        workflow_settings = workflow.metadata.settings if workflow.metadata.settings else {}
        if workflow_settings.get("continue_on_failure", False):
            return False

        # Default: stop on any failure
        return True

    def log_milestone(
        self,
        execution_id: str,
        message: str,
        user_message: str,
        data: Optional[Dict[str, Any]] = None,
    ):
        """Log a custom milestone for the execution"""
        self.logger.log_custom_milestone(
            execution_id=execution_id,
            message=message,
            user_message=user_message,
            level=LogLevel.INFO,
            data=data,
        )

    def get_execution_progress(self, execution_id: str) -> Dict[str, Any]:
        """Get current execution progress"""
        return self.logger._progress_tracker.get_execution_progress(execution_id)


__all__ = ["ModernExecutionEngine", "NodeResult"]
