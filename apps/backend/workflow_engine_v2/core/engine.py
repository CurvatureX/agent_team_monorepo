"""
Spec-driven execution engine (v2)

Minimal, elegant in-memory executor that:
- Validates nodes against the spec registry
- Builds a graph from connections with cycle detection
- Runs nodes in dependency order with readiness checks
- Merges inputs per port and tracks detailed execution state (v2 models)
- Supports Human-in-the-loop pause/resume
- Supports AI attachments (TOOL/MEMORY) via runners

This engine avoids legacy compatibility concerns and favors clarity and
extensibility via a small runner interface for node execution.
"""

from __future__ import annotations

import asyncio
import concurrent.futures as _fut
import os
import random
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from supabase import create_client

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Use absolute imports
from shared.models import (
    ExecutionError,
    ExecutionStatus,
    LogEntry,
    LogLevel,
    NodeError,
    NodeExecution,
    NodeExecutionDetails,
    NodeExecutionStatus,
    TokenUsage,
    TriggerInfo,
)
from shared.models.execution_new import Execution
from shared.models.node_enums import NodeType
from shared.models.workflow_new import Workflow
from shared.node_specs.base import execute_conversion_function
from workflow_engine_v2.core.exceptions import EngineError, ExecutionFailure
from workflow_engine_v2.core.graph import WorkflowGraph
from workflow_engine_v2.core.spec import get_spec
from workflow_engine_v2.core.state import ExecutionContext, ExecutionStore
from workflow_engine_v2.core.validation import validate_workflow
from workflow_engine_v2.runners.factory import default_runner_for
from workflow_engine_v2.services.events_publisher import get_event_publisher
from workflow_engine_v2.services.hil_classifier import get_hil_classifier
from workflow_engine_v2.services.logging import get_logging_service
from workflow_engine_v2.services.repository import ExecutionRepository, InMemoryExecutionRepository
from workflow_engine_v2.services.timers import get_timer_service


def _now_ms() -> int:
    return int(time.time() * 1000)


def execute_conversion_function_flexible(
    conversion_function: str, input_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute a conversion function with support for both named and anonymous functions.

    Supports:
    - def convert(input_data: Dict[str, Any]) -> Dict[str, Any]: return transformed_data
    - lambda input_data: transformed_data
    - def any_name(input_data: Dict[str, Any]) -> Dict[str, Any]: return transformed_data

    Args:
        conversion_function: Python function as string
        input_data: Input data to transform

    Returns:
        Dict[str, Any]: Transformed data or original data if execution fails
    """
    if not conversion_function or not conversion_function.strip():
        return input_data

    try:
        # Create a restricted namespace for security
        namespace = {
            "Dict": Dict,
            "Any": Any,
            "__builtins__": {
                "len": len,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "list": list,
                "dict": dict,
                "range": range,
                "enumerate": enumerate,
                "zip": zip,
                "max": max,
                "min": min,
                "sum": sum,
                "abs": abs,
                "round": round,
            },
        }

        # Handle lambda functions
        if conversion_function.strip().startswith("lambda"):
            # Execute lambda directly
            func = eval(conversion_function, namespace)
            result = func(input_data)
        else:
            # Handle def functions (named or anonymous)
            exec(conversion_function, namespace)

            # Try to find any function in the namespace (ignoring the name)
            func = None
            for name, obj in namespace.items():
                if callable(obj) and name not in ["Dict", "Any"] and not name.startswith("__"):
                    func = obj
                    break

            if not func:
                print(f"ERROR: No function found in conversion_function")
                return input_data

            result = func(input_data)

        # Ensure result is a dictionary
        if isinstance(result, dict):
            return result
        else:
            return {"converted_data": result}

    except Exception as e:
        print(f"Conversion function execution failed: {e}")
        return input_data


class ExecutionEngine:
    """Core v2 workflow execution engine (in-memory)."""

    def __init__(self, repository: Optional[ExecutionRepository] = None, max_workers: int = 8):
        self._store = ExecutionStore()
        self._log = get_logging_service()
        self._timers = get_timer_service()
        self._repo = repository or InMemoryExecutionRepository()
        self._hil = get_hil_classifier()
        self._events = get_event_publisher()
        self._pool = _fut.ThreadPoolExecutor(max_workers=max_workers)

    def validate_against_specs(self, workflow: Workflow) -> None:
        # Ensure spec exists for each node (type/subtype)
        for n in workflow.nodes:
            _ = get_spec(n.type, n.subtype)
        # Additional validation for ports and configurations
        validate_workflow(workflow)

    def run(self, workflow: Workflow, trigger: TriggerInfo) -> Execution:
        self.validate_against_specs(workflow)

        exec_id = str(uuid.uuid4())
        workflow_execution = Execution(
            id=exec_id,
            execution_id=exec_id,
            workflow_id=workflow.metadata.id,
            workflow_version=workflow.metadata.version,
            status=ExecutionStatus.RUNNING,
            start_time=_now_ms(),
            trigger_info=trigger,
        )
        self._log.log(workflow_execution, level=LogLevel.INFO, message="Execution started")
        self._events.execution_started(workflow_execution)
        self._repo.save(workflow_execution)

        graph = WorkflowGraph(workflow)
        _ = graph.topo_order()  # Raises on cycle

        # Track data flow per node input ports
        pending_inputs: Dict[str, Dict[str, Any]] = {node_id: {} for node_id in graph.nodes.keys()}

        # Initialize node execution records
        for node_id, node in graph.nodes.items():
            workflow_execution.node_executions[node_id] = NodeExecution(
                node_id=node_id,
                node_name=node.name,
                node_type=node.type.value if hasattr(node.type, "value") else str(node.type),
                node_subtype=node.subtype,
                status=NodeExecutionStatus.PENDING,
            )

        # Prepare execution context and store
        execution_context = ExecutionContext(
            workflow=workflow,
            graph=graph,
            execution=workflow_execution,
            pending_inputs=pending_inputs,
        )
        self._store.put(execution_context)

        # New task-queue execution (supports fan-out and retries)
        executed_main: set[str] = set()
        run_counts: Dict[str, int] = {}
        queue: List[Dict[str, Any]] = [
            {"node_id": node_id, "override": None}
            for node_id in self._get_initial_ready_nodes(graph)
        ]
        while queue:
            task = queue.pop(0)
            current_node_id = task["node_id"]
            override = task.get("override")
            is_fanout_run = override is not None
            if not is_fanout_run and current_node_id in executed_main:
                continue
            node = graph.nodes[current_node_id]

            node_execution = workflow_execution.node_executions[current_node_id]
            # Assign activation and lineage
            try:
                node_execution.activation_id = str(uuid.uuid4())
                if is_fanout_run:
                    node_execution.parent_activation_id = task.get("parent_activation_id")
                else:
                    node_execution.parent_activation_id = None
            except Exception:
                pass
            node_execution.status = NodeExecutionStatus.RUNNING
            node_execution.start_time = _now_ms()
            self._log.log(
                workflow_execution,
                level=LogLevel.INFO,
                message=f"Node {node.name} started",
                node_id=current_node_id,
            )
            self._events.node_started(workflow_execution, current_node_id, node_execution)

            inputs: Dict[str, Any] = {}
            if is_fanout_run:
                inputs.update(override or {})
            else:
                inputs.update(pending_inputs.get(current_node_id, {}))
            inputs["_ctx"] = execution_context

            # Simple retry loop
            max_retries = int(node.configurations.get("retry_attempts", 0) or 0)
            attempt = 0
            last_exc: Exception | None = None
            start_exec = _now_ms()
            backoff = float(node.configurations.get("retry_backoff_seconds", 0) or 0)
            backoff_factor = float(node.configurations.get("retry_backoff_factor", 1.0) or 1.0)
            while attempt <= max_retries:
                try:
                    runner = default_runner_for(node)
                    # Timeout handling
                    exec_timeout = None
                    try:
                        if node.configurations.get("timeout_seconds") is not None:
                            exec_timeout = float(node.configurations.get("timeout_seconds"))
                        elif node.configurations.get("timeout") is not None:
                            exec_timeout = float(node.configurations.get("timeout"))
                    except Exception:
                        exec_timeout = None
                    if exec_timeout and exec_timeout > 0:
                        future = self._pool.submit(runner.run, node, inputs, trigger)
                        outputs = future.result(timeout=max(0.001, exec_timeout))
                    else:
                        outputs = runner.run(node, inputs, trigger)
                    last_exc = None
                    break
                except Exception as e:
                    last_exc = e
                    attempt += 1
                    node_execution.status = (
                        NodeExecutionStatus.RETRYING
                        if attempt <= max_retries
                        else NodeExecutionStatus.FAILED
                    )
                    if attempt > max_retries:
                        break
                    # Backoff sleep (blocking; for more sophistication use async)
                    try:
                        delay = (
                            backoff * (backoff_factor ** max(0, attempt - 1)) if backoff > 0 else 0
                        )
                        jitter = float(node.configurations.get("retry_jitter_seconds", 0) or 0)
                        if jitter > 0:
                            delay += random.uniform(0, jitter)
                        if delay > 0:
                            time.sleep(min(delay, 5))  # cap small to avoid test stalls
                    except Exception:
                        pass

            duration = _now_ms() - start_exec
            timeout_sec = node.configurations.get("timeout")
            if timeout_sec is not None:
                try:
                    if duration > float(timeout_sec) * 1000:
                        last_exc = last_exc or Exception("Node execution timed out")
                except Exception:
                    pass

            if last_exc is not None:
                node_execution.end_time = _now_ms()
                node_execution.duration_ms = (
                    (node_execution.end_time - node_execution.start_time)
                    if node_execution.start_time
                    else None
                )
                workflow_execution.status = ExecutionStatus.ERROR
                self._log.log(
                    workflow_execution,
                    level=LogLevel.ERROR,
                    message=f"Node {node.name} failed",
                    node_id=current_node_id,
                )
                self._events.node_failed(workflow_execution, current_node_id, ne)
                self._events.execution_failed(we)
                try:
                    # NodeError and ExecutionError already imported above
                    node_execution.error = NodeError(
                        error_code="NODE_EXEC_ERROR",
                        error_message=str(last_exc),
                        error_details={"attempt": attempt, "node_id": current_node_id},
                        is_retryable=(attempt <= max_retries),
                        timestamp=_now_ms(),
                    )
                    workflow_execution.error = ExecutionError(
                        error_code="EXECUTION_FAILED",
                        error_message=f"Node {node.name} failed: {last_exc}",
                        error_node_id=current_node_id,
                        stack_trace=None,
                        timestamp=_now_ms(),
                        is_retryable=False,
                    )
                except Exception:
                    pass
                self._repo.save(we)
                break

            # HIL (Human-in-the-Loop) Wait handling with database persistence
            if outputs.get("_hil_wait"):
                node_execution.input_data = inputs
                node_execution.status = NodeExecutionStatus.WAITING_INPUT
                workflow_execution.current_node_id = current_node_id
                workflow_execution.status = ExecutionStatus.WAITING_FOR_HUMAN

                # Create workflow execution pause record for HIL
                try:
                    pause_data = {
                        "hil_interaction_id": outputs.get("_hil_interaction_id"),
                        "hil_timeout_seconds": outputs.get("_hil_timeout_seconds"),
                        "hil_node_id": outputs.get("_hil_node_id"),
                        "pause_context": {
                            "node_output": outputs.get("main", {}),
                            "execution_context": {
                                "execution_id": workflow_execution.execution_id,
                                "workflow_id": workflow_execution.workflow_id,
                                "current_node": current_node_id,
                                "node_name": node.name if node else current_node_id,
                            },
                        },
                    }

                    resume_conditions = {
                        "type": "human_response",
                        "interaction_id": outputs.get("_hil_interaction_id"),
                        "required_fields": ["response_data", "response_type"],
                        "timeout_action": outputs.get("main", {}).get("timeout_action", "fail"),
                    }

                    # Store pause record in database if we have Supabase client
                    if hasattr(self, "_create_workflow_pause"):
                        pause_id = self._create_workflow_pause(
                            execution_id=workflow_execution.execution_id,
                            node_id=current_node_id,
                            pause_reason="human_interaction",
                            pause_data=pause_data,
                            resume_conditions=resume_conditions,
                            hil_interaction_id=outputs.get("_hil_interaction_id"),
                        )

                        if pause_id:
                            self._log.log(
                                workflow_execution,
                                level=LogLevel.INFO,
                                message=f"Workflow paused for HIL interaction {outputs.get('_hil_interaction_id')}",
                                node_id=current_node_id,
                            )

                    # Schedule timeout if specified
                    hil_timeout_seconds = outputs.get("_hil_timeout_seconds")
                    if hil_timeout_seconds and hasattr(self, "_timers"):
                        timeout_ms = int(hil_timeout_seconds) * 1000
                        self._timers.schedule(
                            workflow_execution.execution_id,
                            current_node_id,
                            timeout_ms,
                            reason="hil_timeout",
                            port="timeout",
                            metadata={"interaction_id": outputs.get("_hil_interaction_id")},
                        )

                except Exception as e:
                    self._log.log(
                        workflow_execution,
                        level=LogLevel.ERROR,
                        message=f"Failed to create HIL pause record: {str(e)}",
                        node_id=current_node_id,
                    )

                self._events.user_input_required(workflow_execution, current_node_id, ne)
                return workflow_execution
            if outputs.get("_wait"):
                if "_wait_timeout_ms" in outputs:
                    try:
                        timeout_ms = int(outputs.get("_wait_timeout_ms") or 0)
                    except Exception:
                        timeout_ms = 0
                    if timeout_ms > 0:
                        self._timers.schedule(
                            workflow_execution.execution_id,
                            current_node_id,
                            timeout_ms,
                            reason="wait_timeout",
                            port="timeout",
                        )
                node_execution.input_data = inputs
                node_execution.status = NodeExecutionStatus.WAITING_INPUT
                workflow_execution.current_node_id = current_node_id
                workflow_execution.status = ExecutionStatus.WAITING
                self._events.execution_paused(we)
                return workflow_execution
            if "_delay_ms" in outputs:
                delay_ms = int(outputs.get("_delay_ms") or 0)
                self._timers.schedule(
                    workflow_execution.execution_id,
                    current_node_id,
                    delay_ms,
                    reason="delay",
                    port="main",
                )
                node_execution.input_data = inputs
                node_execution.status = NodeExecutionStatus.WAITING_INPUT
                workflow_execution.current_node_id = current_node_id
                workflow_execution.status = ExecutionStatus.WAITING
                self._events.execution_paused(we)
                return workflow_execution

            # Streaming support: publish partial chunks if provided
            try:
                chunks = outputs.get("_stream_chunks") if isinstance(outputs, dict) else None
                if chunks and isinstance(chunks, list):
                    for ch in chunks:
                        self._events.node_output_update(
                            workflow_execution, current_node_id, ne, partial={"stream": ch}
                        )
            except Exception:
                pass
            node_execution.output_data = outputs
            node_execution.input_data = inputs
            node_execution.status = NodeExecutionStatus.COMPLETED
            node_execution.end_time = _now_ms()
            node_execution.duration_ms = (
                (node_execution.end_time - node_execution.start_time)
                if node_execution.start_time
                else None
            )
            # Merge execution details patch if provided by runner
            try:
                details_patch = outputs.get("_details") if isinstance(outputs, dict) else None
                if details_patch:
                    for k, v in details_patch.items():
                        setattr(node_execution.execution_details, k, v)
            except Exception:
                pass
            # Token usage aggregation
            try:
                token_info = outputs.get("_tokens") if isinstance(outputs, dict) else None
                if token_info:
                    # TokenUsage already imported above
                    tu = workflow_execution.tokens_used or TokenUsage()
                    tu.input_tokens = (tu.input_tokens or 0) + int(token_info.get("input", 0) or 0)
                    tu.output_tokens = (tu.output_tokens or 0) + int(
                        token_info.get("output", 0) or 0
                    )
                    tu.total_tokens = (tu.input_tokens or 0) + (tu.output_tokens or 0)
                    workflow_execution.tokens_used = tu
            except Exception:
                pass
            # Resource accounting (credits)
            try:
                credit_cost = int(node.configurations.get("credit_cost", 0) or 0)
            except Exception:
                credit_cost = 0
            node_execution.credits_consumed = credit_cost
            try:
                workflow_execution.credits_consumed = (
                    workflow_execution.credits_consumed or 0
                ) + credit_cost
            except Exception:
                pass
            run_counts[current_node_id] = run_counts.get(current_node_id, 0) + 1
            if node_execution.execution_details.metrics is None:
                node_execution.execution_details.metrics = {}
            node_execution.execution_details.metrics["runs"] = run_counts[current_node_id]
            self._log.log(
                workflow_execution,
                level=LogLevel.INFO,
                message=f"Node {node.name} completed",
                node_id=current_node_id,
            )
            self._events.node_output_update(workflow_execution, current_node_id, ne)
            self._events.node_completed(workflow_execution, current_node_id, ne)
            self._repo.save(we)
            # Update node outputs context (by id and by name)
            execution_context.node_outputs[current_node_id] = outputs
            try:
                node_name = node.name
                execution_context.node_outputs_by_name[node_name] = outputs
            except Exception:
                pass

            # Record node run (append copy)
            try:
                # Deep copy NodeExecution for run record
                run_record = NodeExecution(**node_execution.model_dump())
                workflow_execution.node_runs.setdefault(current_node_id, []).append(run_record)
            except Exception:
                pass

            # Propagate, including fan-out
            for (
                successor_nodeessor_node,
                from_port,
                to_port,
                conversion_function,
            ) in graph.successors(current_node_id):
                if from_port == "iteration" and isinstance(outputs.get("iteration"), list):
                    for item in outputs["iteration"]:
                        value = item
                        # Apply conversion function if provided
                        if conversion_function and isinstance(conversion_function, str):
                            try:
                                converted_data = execute_conversion_function_flexible(
                                    conversion_function, {"value": value, "data": value}
                                )
                                value = converted_data
                            except Exception as e:
                                print(f"Conversion function failed for iteration: {e}")
                                # Keep original value on error
                        queue.append(
                            {
                                "node_id": successor_nodeessor_node,
                                "override": {to_port: value},
                                "parent_activation_id": node_execution.activation_id,
                            }
                        )
                    continue
                successor_node_inputs = pending_inputs.setdefault(successor_nodeessor_node, {})
                value = outputs.get(from_port)
                if value is None:
                    value = outputs.get("main", outputs)

                # Apply conversion function if provided
                if conversion_function and isinstance(conversion_function, str):
                    try:
                        converted_data = execute_conversion_function_flexible(
                            conversion_function, {"value": value, "data": value, "output": value}
                        )
                        value = converted_data
                    except Exception as e:
                        print(f"Conversion function failed: {e}")
                        # Keep original value on error
                if to_port in successor_node_inputs:
                    existing = successor_node_inputs[to_port]
                    if isinstance(existing, list):
                        existing.append(value)
                        successor_node_inputs[to_port] = existing
                    else:
                        successor_node_inputs[to_port] = [existing, value]
                else:
                    successor_node_inputs[to_port] = value
                if self._is_node_ready(graph, successor_nodeessor_node, pending_inputs):
                    queue.append({"node_id": successor_nodeessor_node, "override": None})

            workflow_execution.execution_sequence.append(current_node_id)
            if not is_fanout_run:
                executed_main.add(current_node_id)

        if workflow_execution.status != ExecutionStatus.ERROR:
            workflow_execution.status = ExecutionStatus.SUCCESS
            workflow_execution.end_time = _now_ms()
            workflow_execution.duration_ms = workflow_execution.end_time - (
                workflow_execution.start_time or workflow_execution.end_time
            )
            self._log.log(
                workflow_execution,
                level=LogLevel.INFO,
                message="Execution completed successor_nodeessfully",
            )
            self._events.execution_completed(we)
            self._repo.save(we)
        return workflow_execution

    # Async conversion_functionenience wrapper for non-blocking run
    async def run_async(self, workflow: Workflow, trigger: TriggerInfo) -> Execution:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._pool, self.run, workflow, trigger)

        # Execute nodes in dependency order with readiness checks
        executed: set[str] = set()
        ready = self._get_initial_ready_nodes(graph)
        while ready:
            current_node_id = ready.pop(0)
            if current_node_id in executed:
                continue
            node = graph.nodes[current_node_id]

            ne = workflow_execution.node_executions[current_node_id]
            node_execution.status = NodeExecutionStatus.RUNNING
            node_execution.start_time = _now_ms()
            self._log.log(
                workflow_execution,
                level=LogLevel.INFO,
                message=f"Node {node.name} started",
                node_id=current_node_id,
            )

            # Collect inputs merged by to_port; inject context for runners
            inputs: Dict[str, Any] = pending_inputs.get(current_node_id, {})
            inputs["_ctx"] = ctx

            # Execute node via runner
            try:
                runner = default_runner_for(node)
                outputs = runner.run(node, inputs, trigger)
                # Handle HIL wait markers
                if outputs.get("_hil_wait"):
                    node_execution.input_data = inputs
                    node_execution.status = NodeExecutionStatus.WAITING_INPUT
                    workflow_execution.current_node_id = current_node_id
                    workflow_execution.status = ExecutionStatus.WAITING_FOR_HUMAN
                    # Return and allow caller to resume later
                    return workflow_execution
                # Handle wait markers
                if outputs.get("_wait"):
                    # Schedule optional timeout before returning
                    if "_wait_timeout_ms" in outputs:
                        try:
                            timeout_ms = int(outputs.get("_wait_timeout_ms") or 0)
                        except Exception:
                            timeout_ms = 0
                        if timeout_ms > 0:
                            self._timers.schedule(
                                workflow_execution.execution_id,
                                current_node_id,
                                timeout_ms,
                                reason="wait_timeout",
                                port="timeout",
                            )
                    node_execution.input_data = inputs
                    node_execution.status = NodeExecutionStatus.WAITING_INPUT
                    workflow_execution.current_node_id = current_node_id
                    workflow_execution.status = ExecutionStatus.WAITING
                    return workflow_execution
                # Handle delay markers
                if "_delay_ms" in outputs:
                    delay_ms = int(outputs.get("_delay_ms") or 0)
                    self._timers.schedule(
                        workflow_execution.execution_id,
                        current_node_id,
                        delay_ms,
                        reason="delay",
                        port="main",
                    )
                    node_execution.input_data = inputs
                    node_execution.status = NodeExecutionStatus.WAITING_INPUT
                    workflow_execution.current_node_id = current_node_id
                    workflow_execution.status = ExecutionStatus.WAITING
                    return workflow_execution
                node_execution.output_data = outputs
                node_execution.input_data = inputs
                node_execution.status = NodeExecutionStatus.COMPLETED
                node_execution.end_time = _now_ms()
                node_execution.duration_ms = (
                    (node_execution.end_time - node_execution.start_time)
                    if node_execution.start_time
                    else None
                )
                self._log.log(
                    workflow_execution,
                    level=LogLevel.INFO,
                    message=f"Node {node.name} completed",
                    node_id=current_node_id,
                )
                self._repo.save(we)

                # Propagate according to graph connections
                for (
                    successor_nodeessor_node,
                    from_port,
                    to_port,
                    conversion_function,
                ) in graph.successors(current_node_id):
                    successor_node_inputs = pending_inputs.setdefault(successor_nodeessor_node, {})
                    value = outputs.get(from_port)
                    if value is None:
                        value = outputs.get("main", outputs)

                    # Apply conversion function if provided
                    if conversion_function and isinstance(conversion_function, str):
                        try:
                            converted_data = execute_conversion_function_flexible(
                                conversion_function,
                                {"value": value, "data": value, "output": value},
                            )
                            value = converted_data
                        except Exception as e:
                            print(f"Conversion function failed: {e}")
                            # Keep original value on error

                    # Merge values if multiple upstream connections target same to_port
                    if to_port in successor_node_inputs:
                        existing = successor_node_inputs[to_port]
                        if isinstance(existing, list):
                            existing.append(value)
                            successor_node_inputs[to_port] = existing
                        else:
                            successor_node_inputs[to_port] = [existing, value]
                    else:
                        successor_node_inputs[to_port] = value

                workflow_execution.execution_sequence.append(current_node_id)
                executed.add(current_node_id)
                # Enqueue successors that are now ready
                for successor_nodeessor_node, _, _ in graph.successors(current_node_id):
                    if self._is_node_ready(graph, successor_nodeessor_node, pending_inputs):
                        ready.append(successor_node)

            except Exception:
                node_execution.status = NodeExecutionStatus.FAILED
                node_execution.end_time = _now_ms()
                node_execution.duration_ms = (
                    (node_execution.end_time - node_execution.start_time)
                    if node_execution.start_time
                    else None
                )
                workflow_execution.status = ExecutionStatus.ERROR
                self._log.log(
                    workflow_execution,
                    level=LogLevel.ERROR,
                    message=f"Node {node.name} failed",
                    node_id=current_node_id,
                )
                self._repo.save(we)
                break

        if workflow_execution.status != ExecutionStatus.ERROR:
            workflow_execution.status = ExecutionStatus.SUCCESS
            workflow_execution.end_time = _now_ms()
            workflow_execution.duration_ms = workflow_execution.end_time - (
                workflow_execution.start_time or workflow_execution.end_time
            )
            self._log.log(
                workflow_execution,
                level=LogLevel.INFO,
                message="Execution completed successor_nodeessfully",
            )
            self._repo.save(we)

        return workflow_execution

    # -------- Engine control API --------

    def resume_with_user_input(self, execution_id: str, node_id: str, input_data: Any) -> Execution:
        """Resume an execution waiting on HIL node with provided user input."""
        ctx = self._store.get(execution_id)
        we = execution_context.execution
        pending_inputs = execution_context.pending_inputs

        if workflow_execution.current_node_id != node_id:
            return workflow_execution

        # Build outputs; special handling for HIL classification
        node = execution_context.graph.nodes[node_id]
        outputs = {"main": input_data}
        ntype = node.type if isinstance(node.type, NodeType) else NodeType(str(node.type))
        if ntype == NodeType.HUMAN_IN_THE_LOOP:
            text = (
                input_data
                if isinstance(input_data, str)
                else (input_data.get("text") if isinstance(input_data, dict) else "")
            )
            label = self._hil.classify(str(text))
            port = "confirmed" if label == "approved" else label
            outputs = {port: input_data, "main": input_data}
        ne = workflow_execution.node_executions[node_id]
        node_execution.output_data = outputs
        node_execution.status = NodeExecutionStatus.COMPLETED
        node_execution.end_time = _now_ms()
        node_execution.duration_ms = node_execution.end_time - (
            node_execution.start_time or node_execution.end_time
        )
        workflow_execution.execution_sequence.append(node_id)
        # Publish events and update node outputs
        self._events.node_output_update(workflow_execution, node_id, ne)
        self._events.node_completed(workflow_execution, node_id, ne)
        execution_context.node_outputs[node_id] = outputs
        try:
            execution_context.node_outputs_by_name[node.name] = outputs
        except Exception:
            pass

        # Update node outputs and propagate to successors
        execution_context.node_outputs[node_id] = outputs
        try:
            node_name = execution_context.graph.nodes[node_id].name
            execution_context.node_outputs_by_name[node_name] = outputs
        except Exception:
            pass
        # Propagate to successors
        for (
            successor_nodeessor_node,
            from_port,
            to_port,
            conversion_function,
        ) in execution_context.graph.successors(node_id):
            successor_node_inputs = pending_inputs.setdefault(successor_nodeessor_node, {})
            value = outputs.get(from_port) or outputs.get("main", outputs)

            # Apply conversion function if provided
            if conversion_function and isinstance(conversion_function, str):
                try:
                    converted_data = execute_conversion_function_flexible(
                        conversion_function, {"value": value, "data": value, "output": value}
                    )
                    value = converted_data
                except Exception as e:
                    print(f"Conversion function failed: {e}")
                    # Keep original value on error
            if to_port in successor_node_inputs:
                existing = successor_node_inputs[to_port]
                if isinstance(existing, list):
                    existing.append(value)
                    successor_node_inputs[to_port] = existing
                else:
                    successor_node_inputs[to_port] = [existing, value]
            else:
                successor_node_inputs[to_port] = value

        # Clear waiting state
        workflow_execution.current_node_id = None
        workflow_execution.status = ExecutionStatus.RUNNING
        self._events.execution_resumed(we)

        # Continue scheduling from successors
        ready = [
            successor_node
            for successor_nodeessor_node, *_ in execution_context.graph.successors(node_id)
            if self._is_node_ready(
                execution_context.graph, successor_nodeessor_node, pending_inputs
            )
        ]
        executed = set(workflow_execution.execution_sequence)
        while ready:
            current_node_id = ready.pop(0)
            if current_node_id in executed:
                continue
            node = execution_context.graph.nodes[current_node_id]
            node_execution2 = workflow_execution.node_executions[current_node_id]
            node_execution2.status = NodeExecutionStatus.RUNNING
            node_execution2.start_time = _now_ms()
            inputs = pending_inputs.get(current_node_id, {})
            inputs["_ctx"] = ctx
            try:
                runner = default_runner_for(node)
                outputs = runner.run(
                    node,
                    inputs,
                    TriggerInfo(trigger_type="resume", trigger_data={}, timestamp=_now_ms()),
                )
                if outputs.get("_hil_wait"):
                    node_execution2.input_data = inputs
                    node_execution2.status = NodeExecutionStatus.WAITING_INPUT
                    workflow_execution.current_node_id = current_node_id
                    workflow_execution.status = ExecutionStatus.WAITING_FOR_HUMAN
                    return workflow_execution
                node_execution2.output_data = outputs
                node_execution2.input_data = inputs
                node_execution2.status = NodeExecutionStatus.COMPLETED
                node_execution2.end_time = _now_ms()
                node_execution2.duration_ms = (
                    (node_execution2.end_time - node_execution2.start_time)
                    if node_execution2.start_time
                    else None
                )

                for successor_node2, from_port2, to_port2 in execution_context.graph.successors(
                    current_node_id
                ):
                    successor_node_inputs2 = pending_inputs.setdefault(successor_node2, {})
                    value2 = outputs.get(from_port2) or outputs.get("main", outputs)
                    if to_port2 in successor_node_inputs2:
                        existing2 = successor_node_inputs2[to_port2]
                        if isinstance(existing2, list):
                            existing2.append(value2)
                            successor_node_inputs2[to_port2] = existing2
                        else:
                            successor_node_inputs2[to_port2] = [existing2, value2]
                    else:
                        successor_node_inputs2[to_port2] = value2
                executed.add(current_node_id)
                for successor_node2, _, _ in execution_context.graph.successors(current_node_id):
                    if self._is_node_ready(
                        execution_context.graph, successor_node2, pending_inputs
                    ):
                        ready.append(successor_node2)
            except Exception:
                node_execution2.status = NodeExecutionStatus.FAILED
                node_execution2.end_time = _now_ms()
                node_execution2.duration_ms = node_execution2.end_time - (
                    node_execution2.start_time or node_execution2.end_time
                )
                workflow_execution.status = ExecutionStatus.ERROR
                break

        if workflow_execution.status != ExecutionStatus.ERROR:
            workflow_execution.status = ExecutionStatus.SUCCESS
            workflow_execution.end_time = _now_ms()
            workflow_execution.duration_ms = workflow_execution.end_time - (
                workflow_execution.start_time or workflow_execution.end_time
            )
            self._log.log(
                workflow_execution,
                level=LogLevel.INFO,
                message="Execution completed successor_nodeessfully",
            )
            self._repo.save(we)
        return workflow_execution

    def _create_workflow_pause(
        self,
        execution_id: str,
        node_id: str,
        pause_reason: str,
        pause_data: Dict[str, Any],
        resume_conditions: Dict[str, Any],
        hil_interaction_id: Optional[str] = None,
    ) -> Optional[str]:
        """Create workflow execution pause record in database."""
        try:
            # Create Supabase client for database operations
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

            if not supabase_url or not supabase_key:
                return None

            client = create_client(supabase_url, supabase_key)

            # Create pause record
            pause_record = {
                "execution_id": execution_id,
                "node_id": node_id,
                "pause_reason": pause_reason,
                "pause_data": pause_data,
                "resume_conditions": resume_conditions,
                "status": "active",
                "paused_at": datetime.utcnow().isoformat(),
            }

            if hil_interaction_id:
                pause_record["hil_interaction_id"] = hil_interaction_id

            result = client.table("workflow_execution_pauses").insert(pause_record).execute()

            if result.data:
                return result.data[0]["id"]

            return None

        except Exception as e:
            # Log error but don't fail execution
            if hasattr(self, "_log"):
                self._log.log(
                    None,
                    level=LogLevel.ERROR,
                    message=f"Failed to create workflow pause record: {str(e)}",
                    node_id=node_id,
                )
            return None

    def resume_timer(
        self, execution_id: str, node_id: str, *, reason: str = "delay", port: str = "main"
    ) -> Execution:
        """Resume a timer-waiting node after delay has elapsed."""
        ctx = self._store.get(execution_id)
        we = execution_context.execution
        pending_inputs = execution_context.pending_inputs
        if workflow_execution.current_node_id != node_id:
            return workflow_execution

        ne = workflow_execution.node_executions[node_id]
        inputs = pending_inputs.get(node_id, {})
        base = inputs.get("main", inputs)
        outputs = {port: base, "main": base}
        node_execution.output_data = outputs
        node_execution.status = NodeExecutionStatus.COMPLETED
        node_execution.end_time = _now_ms()
        node_execution.duration_ms = node_execution.end_time - (
            node_execution.start_time or node_execution.end_time
        )
        workflow_execution.execution_sequence.append(node_id)
        # Update node outputs context and publish events
        execution_context.node_outputs[node_id] = outputs
        try:
            node_name = execution_context.graph.nodes[node_id].name
            execution_context.node_outputs_by_name[node_name] = outputs
        except Exception:
            pass
        self._events.node_output_update(workflow_execution, node_id, ne)
        self._events.node_completed(workflow_execution, node_id, ne)

        for (
            successor_node,
            from_port,
            to_port,
            conversion_function,
        ) in execution_context.graph.successors(node_id):
            successor_node_inputs = pending_inputs.setdefault(successor_node, {})
            value = outputs.get(from_port) or outputs.get("main", outputs)
            # Apply conversion function if provided
            if conversion_function:
                value = execute_conversion_function_flexible(conversion_function, value)
            if to_port in successor_node_inputs:
                existing = successor_node_inputs[to_port]
                if isinstance(existing, list):
                    existing.append(value)
                    successor_node_inputs[to_port] = existing
                else:
                    successor_node_inputs[to_port] = [existing, value]
            else:
                successor_node_inputs[to_port] = value

        workflow_execution.current_node_id = None
        workflow_execution.status = ExecutionStatus.RUNNING

        ready = [
            successor_node
            for successor_nodeessor_node, *_ in execution_context.graph.successors(node_id)
            if self._is_node_ready(
                execution_context.graph, successor_nodeessor_node, pending_inputs
            )
        ]
        executed = set(workflow_execution.execution_sequence)
        while ready:
            current_node_id = ready.pop(0)
            if current_node_id in executed:
                continue
            node = execution_context.graph.nodes[current_node_id]
            node_execution2 = workflow_execution.node_executions[current_node_id]
            node_execution2.status = NodeExecutionStatus.RUNNING
            node_execution2.start_time = _now_ms()
            inputs2 = pending_inputs.get(current_node_id, {})
            inputs2["_ctx"] = ctx
            try:
                runner = default_runner_for(node)
                outputs2 = runner.run(
                    node,
                    inputs2,
                    TriggerInfo(trigger_type="resume", trigger_data={}, timestamp=_now_ms()),
                )
                if outputs2.get("_hil_wait"):
                    node_execution2.input_data = inputs2
                    node_execution2.status = NodeExecutionStatus.WAITING_INPUT
                    workflow_execution.current_node_id = current_node_id
                    workflow_execution.status = ExecutionStatus.WAITING_FOR_HUMAN
                    return workflow_execution
                if "_wait_timeout_ms" in outputs2:
                    timeout_ms2 = int(outputs2.get("_wait_timeout_ms") or 0)
                    if timeout_ms2 > 0:
                        self._timers.schedule(
                            workflow_execution.execution_id,
                            current_node_id,
                            timeout_ms2,
                            reason="wait_timeout",
                            port="timeout",
                        )
                if "_delay_ms" in outputs2:
                    delay_ms2 = int(outputs2.get("_delay_ms") or 0)
                    self._timers.schedule(
                        workflow_execution.execution_id,
                        current_node_id,
                        delay_ms2,
                        reason="delay",
                        port="main",
                    )
                    node_execution2.input_data = inputs2
                    node_execution2.status = NodeExecutionStatus.WAITING_INPUT
                    workflow_execution.current_node_id = current_node_id
                    workflow_execution.status = ExecutionStatus.WAITING
                    return workflow_execution
                node_execution2.output_data = outputs2
                node_execution2.input_data = inputs2
                node_execution2.status = NodeExecutionStatus.COMPLETED
                node_execution2.end_time = _now_ms()
                node_execution2.duration_ms = node_execution2.end_time - (
                    node_execution2.start_time or node_execution2.end_time
                )
                for (
                    successor_node2,
                    from_port2,
                    to_port2,
                    conversion_function2,
                ) in execution_context.graph.successors(current_node_id):
                    successor_node_inputs2 = pending_inputs.setdefault(successor_node2, {})
                    value2 = outputs2.get(from_port2) or outputs2.get("main", outputs2)
                    # Apply conversion function if provided
                    if conversion_function2:
                        value2 = execute_conversion_function_flexible(conversion_function2, value2)
                    if to_port2 in successor_node_inputs2:
                        existing2 = successor_node_inputs2[to_port2]
                        if isinstance(existing2, list):
                            existing2.append(value2)
                            successor_node_inputs2[to_port2] = existing2
                        else:
                            successor_node_inputs2[to_port2] = [existing2, value2]
                    else:
                        successor_node_inputs2[to_port2] = value2
                executed.add(current_node_id)
                for successor_node2, _, _ in execution_context.graph.successors(current_node_id):
                    if self._is_node_ready(
                        execution_context.graph, successor_node2, pending_inputs
                    ):
                        ready.append(successor_node2)
            except Exception:
                node_execution2.status = NodeExecutionStatus.FAILED
                node_execution2.end_time = _now_ms()
                node_execution2.duration_ms = node_execution2.end_time - (
                    node_execution2.start_time or node_execution2.end_time
                )
                workflow_execution.status = ExecutionStatus.ERROR
                break

        if workflow_execution.status != ExecutionStatus.ERROR:
            workflow_execution.status = ExecutionStatus.SUCCESS
            workflow_execution.end_time = _now_ms()
            workflow_execution.duration_ms = workflow_execution.end_time - (
                workflow_execution.start_time or workflow_execution.end_time
            )
        return workflow_execution

    def resume_due_timers(self) -> None:
        """Check and resume all due timers across executions."""
        for execution_id, node_id, reason, port in self._timers.due():
            self.resume_timer(execution_id, node_id, reason=reason, port=port)

    # Control operations
    def pause(self, execution_id: str) -> Execution:
        ctx = self._store.get(execution_id)
        execution_context.execution.status = ExecutionStatus.PAUSED
        self._events.execution_paused(execution_context.execution)
        return execution_context.execution

    def cancel(self, execution_id: str) -> Execution:
        ctx = self._store.get(execution_id)
        execution_context.execution.status = ExecutionStatus.CANCELED
        execution_context.execution.end_time = _now_ms()
        self._events.execution_failed(execution_context.execution)
        return execution_context.execution

    def retry_node(self, execution_id: str, node_id: str) -> Execution:
        ctx = self._store.get(execution_id)
        we = execution_context.execution
        if node_id in workflow_execution.node_executions:
            ne = workflow_execution.node_executions[node_id]
            node_execution.status = NodeExecutionStatus.PENDING
            node_execution.error = None
        return workflow_execution

    # -------- Helpers --------

    def _get_initial_ready_nodes(self, graph: WorkflowGraph) -> List[str]:
        # Triggers are always ready; otherwise in-degree 0 nodes
        roots = graph.sources()
        return list(roots)

    def _is_node_ready(
        self, graph: WorkflowGraph, node_id: str, pending_inputs: Dict[str, Dict[str, Any]]
    ) -> bool:
        node = graph.nodes[node_id]
        required_ports = [p.id for p in node.input_ports if getattr(p, "required", True)]
        if not required_ports:
            return True
        provided = pending_inputs.get(node_id, {})
        return all(rp in provided for rp in required_ports)


__all__ = ["ExecutionEngine"]
