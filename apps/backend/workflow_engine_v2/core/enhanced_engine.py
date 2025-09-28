"""
Enhanced Workflow Execution Engine with Comprehensive Logging

This module extends the existing ExecutionEngine with comprehensive logging capabilities,
providing detailed progress tracking, parameter logging, and multiple output formats
while maintaining backward compatibility with the existing engine.

Key Enhancements:
- Detailed node execution tracking with input/output parameters
- Real-time progress monitoring
- Performance metrics
- Multiple log output formats
- Error context tracking
- Trace ID support for debugging
"""

from __future__ import annotations

import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Use absolute imports
from shared.models import Execution, ExecutionStatus, LogLevel, NodeExecutionStatus, TriggerInfo
from shared.models.workflow_new import Node, Workflow
from workflow_engine_v2.core.engine import ExecutionEngine
from workflow_engine_v2.core.graph import WorkflowGraph
from workflow_engine_v2.core.spec import get_spec
from workflow_engine_v2.runners.factory import default_runner_for
from workflow_engine_v2.services.enhanced_logging_service import (
    EnhancedLoggingService,
    get_enhanced_logging_service,
)
from workflow_engine_v2.services.execution_logger import NodeExecutionPhase
from workflow_engine_v2.services.log_formatters import OutputFormat


class EnhancedExecutionEngine(ExecutionEngine):
    """Enhanced execution engine with comprehensive logging capabilities"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._enhanced_logging = get_enhanced_logging_service()
        self._trace_id: Optional[str] = None

    def run(
        self, workflow: Workflow, trigger: TriggerInfo, trace_id: Optional[str] = None
    ) -> Execution:
        """Run workflow with enhanced logging"""

        # Generate trace ID for this execution
        self._trace_id = trace_id or str(uuid.uuid4())

        # Validate against specs
        self.validate_against_specs(workflow)

        exec_id = str(uuid.uuid4())
        workflow_execution = Execution(
            id=exec_id,
            execution_id=exec_id,
            workflow_id=workflow.metadata.id,
            workflow_version=workflow.metadata.version,
            status=ExecutionStatus.RUNNING,
            start_time=int(time.time() * 1000),
            trigger_info=trigger,
        )

        # Enhanced workflow start logging
        self._enhanced_logging.log_workflow_start(
            execution=workflow_execution,
            trigger=trigger,
            workflow_context={
                "workflow_name": workflow.metadata.name,
                "workflow_description": workflow.metadata.description,
                "node_count": len(workflow.nodes),
                "connection_count": len(workflow.connections),
                "trace_id": self._trace_id,
            },
            trace_id=self._trace_id,
        )

        # Save execution to repository
        self._events.execution_started(workflow_execution)
        self._repo.save(workflow_execution)

        try:
            # Execute workflow with enhanced tracking
            self._execute_workflow_with_tracking(workflow, workflow_execution)

            # Final status determination
            final_status = self._determine_final_status(workflow_execution)
            workflow_execution.status = final_status
            workflow_execution.end_time = int(time.time() * 1000)

            # Enhanced completion logging
            execution_summary = self._create_execution_summary(workflow_execution)
            self._enhanced_logging.log_workflow_complete(
                execution=workflow_execution,
                final_status=final_status,
                summary=execution_summary,
                trace_id=self._trace_id,
            )

        except Exception as e:
            # Handle execution failure
            workflow_execution.status = ExecutionStatus.FAILED
            workflow_execution.end_time = int(time.time() * 1000)

            self._enhanced_logging.log_workflow_complete(
                execution=workflow_execution,
                final_status=ExecutionStatus.FAILED,
                summary={"error": str(e), "error_type": type(e).__name__},
                trace_id=self._trace_id,
            )
            raise

        finally:
            self._repo.save(workflow_execution)

        return workflow_execution

    async def _execute_workflow_with_tracking(self, workflow: Workflow, execution: Execution):
        """Execute workflow with comprehensive node tracking"""

        graph = WorkflowGraph(workflow)
        _ = graph.topo_order()  # Raises on cycle

        # Track data flow per node input ports
        pending_inputs: Dict[str, Dict[str, Any]] = {node_id: {} for node_id in graph.nodes.keys()}

        # Initialize node execution records
        for node_id, node in graph.nodes.items():
            execution.node_executions[node_id] = {
                "node_id": node_id,
                "node_name": node.name,
                "node_type": node.type.value if hasattr(node.type, "value") else str(node.type),
                "node_subtype": node.subtype,
                "status": NodeExecutionStatus.PENDING,
            }

        # Execute nodes with enhanced tracking
        executed_nodes: set[str] = set()
        run_counts: Dict[str, int] = {}

        # Get initial ready nodes
        queue: List[str] = self._get_initial_ready_nodes(graph)

        while queue:
            node_id = queue.pop(0)
            node = graph.nodes[node_id]

            # Check if node is ready
            if not self._is_node_ready(node_id, graph, pending_inputs, executed_nodes):
                continue

            # Track execution count
            run_counts[node_id] = run_counts.get(node_id, 0) + 1

            try:
                # Execute node with comprehensive tracking
                await self._execute_node_with_tracking(
                    node=node, execution=execution, graph=graph, pending_inputs=pending_inputs
                )

                executed_nodes.add(node_id)

                # Add downstream nodes to queue
                for successor_id in graph.successors(node_id):
                    if successor_id not in executed_nodes and successor_id not in queue:
                        queue.append(successor_id)

            except Exception as e:
                # Mark node as failed
                execution.node_executions[node_id]["status"] = NodeExecutionStatus.FAILED
                execution.node_executions[node_id]["error"] = str(e)

                self._enhanced_logging.log_custom(
                    execution=execution,
                    level=LogLevel.ERROR,
                    message=f"Node execution failed: {node.name} - {str(e)}",
                    node_id=node_id,
                    structured_data={"error_type": type(e).__name__},
                    trace_id=self._trace_id,
                )

                # Decide whether to continue or fail entire workflow
                if self._should_fail_workflow_on_node_error(node, execution):
                    raise

    async def _execute_node_with_tracking(
        self,
        node: Node,
        execution: Execution,
        graph: WorkflowGraph,
        pending_inputs: Dict[str, Dict[str, Any]],
    ):
        """Execute a single node with comprehensive tracking"""

        # Prepare input parameters
        input_parameters = pending_inputs.get(node.id, {})
        configuration = dict(node.configurations) if node.configurations else {}

        # Use enhanced logging service to track node execution
        async with self._enhanced_logging.track_node_execution(
            node=node,
            execution=execution,
            input_parameters=input_parameters,
            configuration=configuration,
            trace_id=self._trace_id,
        ) as context:
            # Update execution record
            execution.node_executions[node.id]["status"] = NodeExecutionStatus.RUNNING
            execution.node_executions[node.id]["start_time"] = int(time.time() * 1000)

            # Phase: Input Validation
            self._enhanced_logging.update_node_phase(
                node_id=node.id,
                phase=NodeExecutionPhase.VALIDATING_INPUTS,
                details={"input_count": len(input_parameters)},
                trace_id=self._trace_id,
            )

            # Get node spec and runner
            spec = get_spec(node.type, node.subtype)
            runner = default_runner_for(node.type)

            # Phase: Processing
            self._enhanced_logging.update_node_phase(
                node_id=node.id,
                phase=NodeExecutionPhase.PROCESSING,
                details={"spec": spec.__class__.__name__, "runner": runner.__class__.__name__},
                trace_id=self._trace_id,
            )

            # Execute the node
            if hasattr(runner, "run_async"):
                # Async execution
                result = await runner.run_async(
                    node=node,
                    inputs=input_parameters,
                    context={"execution_id": execution.execution_id, "trace_id": self._trace_id},
                )
            else:
                # Sync execution (run in thread pool)
                import asyncio

                result = await asyncio.get_event_loop().run_in_executor(
                    self._pool,
                    runner.run,
                    node,
                    input_parameters,
                    {"execution_id": execution.execution_id, "trace_id": self._trace_id},
                )

            # Phase: Completing
            self._enhanced_logging.update_node_phase(
                node_id=node.id, phase=NodeExecutionPhase.COMPLETING, trace_id=self._trace_id
            )

            # Process results
            output_parameters = result.get("outputs", {}) if isinstance(result, dict) else {}

            # Log output parameters
            if output_parameters:
                self._enhanced_logging.log_node_output(
                    node_id=node.id,
                    execution_id=execution.execution_id,
                    output_parameters=output_parameters,
                    trace_id=self._trace_id,
                )

            # Update execution record
            execution.node_executions[node.id]["status"] = NodeExecutionStatus.COMPLETED
            execution.node_executions[node.id]["end_time"] = int(time.time() * 1000)
            execution.node_executions[node.id]["outputs"] = output_parameters

            # Propagate outputs to downstream nodes
            self._propagate_outputs(node.id, output_parameters, graph, pending_inputs)

    def _get_initial_ready_nodes(self, graph: WorkflowGraph) -> List[str]:
        """Get initial nodes that are ready to execute"""
        return [
            node_id for node_id in graph.nodes.keys() if len(list(graph.predecessors(node_id))) == 0
        ]

    def _is_node_ready(
        self,
        node_id: str,
        graph: WorkflowGraph,
        pending_inputs: Dict[str, Dict[str, Any]],
        executed_nodes: set[str],
    ) -> bool:
        """Check if a node is ready for execution"""
        # Check if all predecessor nodes have been executed
        for pred_id in graph.predecessors(node_id):
            if pred_id not in executed_nodes:
                return False
        return True

    def _propagate_outputs(
        self,
        node_id: str,
        outputs: Dict[str, Any],
        graph: WorkflowGraph,
        pending_inputs: Dict[str, Dict[str, Any]],
    ):
        """Propagate node outputs to downstream nodes"""
        for successor_id in graph.successors(node_id):
            # Find connections from this node to successor
            for connection in graph.workflow.connections:
                if connection.from_node == node_id and connection.to_node == successor_id:
                    # Copy output to successor's input
                    output_data = outputs.get(connection.from_port, {})
                    pending_inputs[successor_id][connection.to_port] = output_data

    def _determine_final_status(self, execution: Execution) -> ExecutionStatus:
        """Determine the final status of workflow execution"""
        failed_nodes = [
            node_exec
            for node_exec in execution.node_executions.values()
            if node_exec.get("status") == NodeExecutionStatus.FAILED
        ]

        if failed_nodes:
            return ExecutionStatus.FAILED

        return ExecutionStatus.COMPLETED

    def _should_fail_workflow_on_node_error(self, node: Node, execution: Execution) -> bool:
        """Determine if workflow should fail when a node errors"""
        # This could be configurable based on node settings or workflow settings
        # For now, fail the entire workflow on any node error
        return True

    def _create_execution_summary(self, execution: Execution) -> Dict[str, Any]:
        """Create a comprehensive execution summary"""
        node_statuses = {}
        total_duration = 0

        for node_id, node_exec in execution.node_executions.items():
            status = node_exec.get("status", "unknown")
            node_statuses[status] = node_statuses.get(status, 0) + 1

            # Calculate duration if available
            start_time = node_exec.get("start_time")
            end_time = node_exec.get("end_time")
            if start_time and end_time:
                total_duration += end_time - start_time

        return {
            "total_nodes": len(execution.node_executions),
            "node_statuses": node_statuses,
            "total_duration_ms": total_duration,
            "workflow_duration_ms": (execution.end_time or int(time.time() * 1000))
            - execution.start_time,
            "success_rate": node_statuses.get(NodeExecutionStatus.COMPLETED, 0)
            / len(execution.node_executions)
            if execution.node_executions
            else 0,
            "trace_id": self._trace_id,
        }

    # Enhanced query methods

    def get_execution_logs(
        self,
        execution_id: str,
        format_type: OutputFormat = OutputFormat.CONSOLE,
        node_id: Optional[str] = None,
    ) -> str:
        """Get formatted execution logs"""
        return self._enhanced_logging.get_execution_logs(
            execution_id=execution_id, format_type=format_type, node_id=node_id
        )

    def get_execution_summary(
        self, execution_id: str, format_type: OutputFormat = OutputFormat.CONSOLE
    ) -> str:
        """Get formatted execution summary"""
        return self._enhanced_logging.get_execution_summary(
            execution_id=execution_id, format_type=format_type
        )

    def get_node_execution_details(
        self, execution_id: str, node_id: str, format_type: OutputFormat = OutputFormat.JSON_PRETTY
    ) -> str:
        """Get detailed node execution information"""
        return self._enhanced_logging.get_node_execution_details(
            execution_id=execution_id, node_id=node_id, format_type=format_type
        )

    def export_execution_logs(
        self,
        execution_id: str,
        file_path: str,
        format_type: OutputFormat = OutputFormat.JSON_PRETTY,
    ):
        """Export execution logs to file"""
        self._enhanced_logging.export_execution_logs(
            execution_id=execution_id, file_path=file_path, format_type=format_type
        )

    def print_execution_summary(self, execution_id: str, detailed: bool = False):
        """Print execution summary to console"""
        format_type = OutputFormat.CONSOLE_DETAILED if detailed else OutputFormat.CONSOLE
        summary = self.get_execution_summary(execution_id, format_type)
        print(summary)

    def print_execution_logs(
        self, execution_id: str, node_id: Optional[str] = None, detailed: bool = False
    ):
        """Print execution logs to console"""
        format_type = OutputFormat.CONSOLE_DETAILED if detailed else OutputFormat.CONSOLE
        logs = self.get_execution_logs(execution_id, format_type, node_id)
        print(logs)


__all__ = ["EnhancedExecutionEngine"]
