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
    """Core v2 workflow execution engine (in-memory).

    Unified execution engine supporting:
    - Sync and async execution
    - User-friendly and technical logging
    - HIL (Human-in-the-Loop) pause/resume
    - Timers, delays, retries, timeouts
    - Fan-out execution (LOOP nodes)
    - Conversion functions
    - Token tracking and credit accounting
    """

    def __init__(
        self,
        repository: Optional[ExecutionRepository] = None,
        max_workers: int = 8,
        enable_user_friendly_logging: bool = False,
    ):
        self._store = ExecutionStore()
        self._log = get_logging_service()
        self._timers = get_timer_service()
        self._repo = repository or InMemoryExecutionRepository()
        self._hil = get_hil_classifier()
        self._events = get_event_publisher()
        self._pool = _fut.ThreadPoolExecutor(max_workers=max_workers)
        self._enable_user_friendly_logging = enable_user_friendly_logging
        self._user_friendly_logger = None
        if enable_user_friendly_logging:
            try:
                from workflow_engine_v2.services.user_friendly_logger import (
                    get_user_friendly_logger,
                )

                self._user_friendly_logger = get_user_friendly_logger()
            except ImportError:
                pass

    def validate_against_specs(self, workflow: Workflow) -> None:
        # Ensure spec exists for each node (type/subtype)
        for n in workflow.nodes:
            _ = get_spec(n.type, n.subtype)
        # Additional validation for ports and configurations
        validate_workflow(workflow)

    def run(
        self, workflow: Workflow, trigger: TriggerInfo, trace_id: Optional[str] = None
    ) -> Execution:
        """Execute workflow synchronously with optional trace ID for debugging."""
        self.validate_against_specs(workflow)

        exec_id = str(uuid.uuid4())
        trace_id = trace_id or str(uuid.uuid4())

        workflow_execution = Execution(
            id=exec_id,
            execution_id=exec_id,
            workflow_id=workflow.metadata.id,
            workflow_version=workflow.metadata.version,
            status=ExecutionStatus.RUNNING,
            start_time=_now_ms(),
            trigger_info=trigger,
        )

        # User-friendly logging if enabled
        if self._user_friendly_logger:
            workflow_name = workflow.metadata.name or "Unnamed Workflow"
            self._user_friendly_logger.log_workflow_start(
                execution=workflow_execution,
                workflow_name=workflow_name,
                total_nodes=len(workflow.nodes),
                trigger_info=self._format_trigger_description(trigger),
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
            # Helper to extract value from config (may be schema dict or direct value)
            def _get_config_value(key: str, default):
                val = node.configurations.get(key, default)
                if isinstance(val, dict) and "default" in val:
                    return val.get("default", default)
                return val if val is not None else default

            max_retries = int(_get_config_value("retry_attempts", 0) or 0)
            attempt = 0
            last_exc: Exception | None = None
            start_exec = _now_ms()
            backoff = float(_get_config_value("retry_backoff_seconds", 0) or 0)
            backoff_factor = float(_get_config_value("retry_backoff_factor", 1.0) or 1.0)
            while attempt <= max_retries:
                try:
                    runner = default_runner_for(node)
                    # Timeout handling
                    exec_timeout = None
                    try:
                        timeout_val = _get_config_value("timeout_seconds", None)
                        if timeout_val is None:
                            timeout_val = _get_config_value("timeout", None)
                        if timeout_val is not None:
                            exec_timeout = float(timeout_val)
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
                            "node_output": outputs.get("result", {}),
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
                        "timeout_action": outputs.get("result", {}).get("timeout_action", "fail"),
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
            # Sanitize outputs for storage/propagation: only port fields (no control keys starting with '_')
            sanitized_outputs = (
                {k: v for k, v in outputs.items() if isinstance(k, str) and not k.startswith("_")}
                if isinstance(outputs, dict)
                else {}
            )

            # Enforce that each port payload exactly matches node.output_params keys
            def _shape_payload(payload: Any) -> Dict[str, Any]:
                allowed_defaults = node.output_params or {}
                if not isinstance(allowed_defaults, dict):
                    return payload if isinstance(payload, dict) else {}
                shaped: Dict[str, Any] = {}
                if isinstance(payload, dict):
                    for k, default_val in allowed_defaults.items():
                        shaped[k] = payload.get(k, default_val)
                else:
                    # Place primitive payload into 'data' if defined, otherwise use defaults
                    if "data" in allowed_defaults:
                        shaped = {
                            k: (payload if k == "data" else v) for k, v in allowed_defaults.items()
                        }
                    else:
                        shaped = dict(allowed_defaults)
                return shaped

            shaped_outputs = {
                port: _shape_payload(payload) for port, payload in sanitized_outputs.items()
            }
            # Keep raw outputs for conversion functions
            raw_outputs = sanitized_outputs
            node_execution.output_data = shaped_outputs
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
            self._events.node_output_update(workflow_execution, current_node_id, node_execution)
            self._events.node_completed(workflow_execution, current_node_id, node_execution)
            self._repo.save(workflow_execution)
            # Update node outputs context (by id and by name)
            execution_context.node_outputs[current_node_id] = shaped_outputs
            try:
                node_name = node.name
                execution_context.node_outputs_by_name[node_name] = shaped_outputs
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
            # BFS: Only propagate if the required output_key exists in the node's outputs
            for (
                successor_node,
                output_key,
                conversion_function,
            ) in graph.successors(current_node_id):
                # Check if output_key exists in node outputs
                # If output_key is not present, skip this connection (conditional flow)
                value = shaped_outputs.get(output_key)

                # Special case: "iteration" for fan-out (LOOP nodes)
                if output_key == "iteration" and isinstance(value, list):
                    for item in value:
                        item_value = item
                        # Apply conversion function if provided
                        if conversion_function and isinstance(conversion_function, str):
                            try:
                                converted_data = execute_conversion_function_flexible(
                                    conversion_function, {"value": item_value, "data": item_value}
                                )
                                item_value = converted_data
                            except Exception as e:
                                print(f"Conversion function failed for iteration: {e}")
                                # Keep original value on error
                        queue.append(
                            {
                                "node_id": successor_node,
                                "override": {"result": item_value},  # Default to result input
                                "parent_activation_id": node_execution.activation_id,
                            }
                        )
                    continue

                # If output_key is None, skip this connection entirely (conditional execution)
                if value is None:
                    # Try fallback to "result" only if output_key was "result"
                    if output_key == "result":
                        value = shaped_outputs.get("result", shaped_outputs)
                    else:
                        # Output key doesn't exist, skip this connection
                        continue

                successor_node_inputs = pending_inputs.setdefault(successor_node, {})

                # Apply conversion function if provided
                if conversion_function and isinstance(conversion_function, str):
                    try:
                        # Use raw output for conversion function (not shaped)
                        raw_value = raw_outputs.get(output_key)
                        if raw_value is None:
                            raw_value = raw_outputs.get("result", raw_outputs)

                        converted_data = execute_conversion_function_flexible(
                            conversion_function,
                            {"value": raw_value, "data": raw_value, "output": raw_value},
                        )
                        value = converted_data
                    except Exception as e:
                        print(f"Conversion function failed: {e}")
                        # Keep original value on error
                # Input to successor node (use "main" as default input key)
                input_key = "result"
                if input_key in successor_node_inputs:
                    existing = successor_node_inputs[input_key]
                    if isinstance(existing, list):
                        existing.append(value)
                        successor_node_inputs[input_key] = existing
                    else:
                        successor_node_inputs[input_key] = [existing, value]
                else:
                    successor_node_inputs[input_key] = value
                if self._is_node_ready(graph, successor_node, pending_inputs):
                    queue.append({"node_id": successor_node, "override": None})

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
                message="Execution completed successfully",
            )
            self._events.execution_completed(workflow_execution)
            self._repo.save(workflow_execution)
        return workflow_execution

    # Async wrappers for non-blocking execution
    async def run_async(
        self, workflow: Workflow, trigger: TriggerInfo, trace_id: Optional[str] = None
    ) -> Execution:
        """Execute workflow asynchronously."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._pool, self.run, workflow, trigger, trace_id)

    async def execute_workflow(
        self, workflow: Workflow, trigger: TriggerInfo, trace_id: Optional[str] = None
    ) -> Execution:
        """Async alias for run_async - for compatibility with ModernExecutionEngine API."""
        return await self.run_async(workflow, trigger, trace_id)

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

            # Collect inputs for node; inject context for runners
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
                    successor_node,
                    output_key,
                    conversion_function,
                ) in graph.successors(current_node_id):
                    successor_node_inputs = pending_inputs.setdefault(successor_node, {})
                    value = outputs.get(output_key)
                    if value is None:
                        value = outputs.get("result", outputs)

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

                    # Input to successor node (use "main" as default input key)
                    input_key = "result"
                    if input_key in successor_node_inputs:
                        existing = successor_node_inputs[input_key]
                        if isinstance(existing, list):
                            existing.append(value)
                            successor_node_inputs[input_key] = existing
                        else:
                            successor_node_inputs[input_key] = [existing, value]
                    else:
                        successor_node_inputs[input_key] = value

                workflow_execution.execution_sequence.append(current_node_id)
                executed.add(current_node_id)
                # Enqueue successors that are now ready
                for successor_node, _, _ in graph.successors(current_node_id):
                    if self._is_node_ready(graph, successor_node, pending_inputs):
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
        execution_context = self._store.get(execution_id)
        workflow_execution = execution_context.execution
        pending_inputs = execution_context.pending_inputs

        if workflow_execution.current_node_id != node_id:
            return workflow_execution

        # Build outputs; special handling for HIL classification
        node = execution_context.graph.nodes[node_id]
        outputs = {"result": input_data}
        ntype = node.type if isinstance(node.type, NodeType) else NodeType(str(node.type))
        if ntype == NodeType.HUMAN_IN_THE_LOOP:
            text = (
                input_data
                if isinstance(input_data, str)
                else (input_data.get("text") if isinstance(input_data, dict) else "")
            )
            label = self._hil.classify(str(text))
            port = "confirmed" if label == "approved" else label
            outputs = {port: input_data, "result": input_data}
        node_execution = workflow_execution.node_executions[node_id]
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
            successor_node,
            output_key,
            conversion_function,
        ) in execution_context.graph.successors(node_id):
            successor_node_inputs = pending_inputs.setdefault(successor_node, {})
            value = outputs.get(output_key) or outputs.get("result", outputs)

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
            # Input to successor node (use "main" as default input key)
            input_key = "result"
            if input_key in successor_node_inputs:
                existing = successor_node_inputs[input_key]
                if isinstance(existing, list):
                    existing.append(value)
                    successor_node_inputs[input_key] = existing
                else:
                    successor_node_inputs[input_key] = [existing, value]
            else:
                successor_node_inputs[input_key] = value

        # Clear waiting state
        workflow_execution.current_node_id = None
        workflow_execution.status = ExecutionStatus.RUNNING
        self._events.execution_resumed(we)

        # Continue scheduling from successors
        ready = [
            successor_node
            for successor_node, *_ in execution_context.graph.successors(node_id)
            if self._is_node_ready(execution_context.graph, successor_node, pending_inputs)
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

                for successor_node2, output_key2, _conversion in execution_context.graph.successors(
                    current_node_id
                ):
                    successor_node_inputs2 = pending_inputs.setdefault(successor_node2, {})
                    value2 = outputs.get(output_key2) or outputs.get("result", outputs)
                    input_key2 = "result"
                    if input_key2 in successor_node_inputs2:
                        existing2 = successor_node_inputs2[input_key2]
                        if isinstance(existing2, list):
                            existing2.append(value2)
                            successor_node_inputs2[input_key2] = existing2
                        else:
                            successor_node_inputs2[input_key2] = [existing2, value2]
                    else:
                        successor_node_inputs2[input_key2] = value2
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
        base = inputs.get("result", inputs)
        outputs = {port: base, "result": base}
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
            output_key,
            conversion_function,
        ) in execution_context.graph.successors(node_id):
            successor_node_inputs = pending_inputs.setdefault(successor_node, {})
            value = outputs.get(output_key) or outputs.get("result", outputs)
            # Apply conversion function if provided
            if conversion_function:
                value = execute_conversion_function_flexible(conversion_function, value)
            input_key = "result"
            if input_key in successor_node_inputs:
                existing = successor_node_inputs[input_key]
                if isinstance(existing, list):
                    existing.append(value)
                    successor_node_inputs[input_key] = existing
                else:
                    successor_node_inputs[input_key] = [existing, value]
            else:
                successor_node_inputs[input_key] = value

        workflow_execution.current_node_id = None
        workflow_execution.status = ExecutionStatus.RUNNING

        ready = [
            successor_node
            for successor_node, *_ in execution_context.graph.successors(node_id)
            if self._is_node_ready(execution_context.graph, successor_node, pending_inputs)
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
                    output_key2,
                    conversion_function2,
                ) in execution_context.graph.successors(current_node_id):
                    successor_node_inputs2 = pending_inputs.setdefault(successor_node2, {})
                    value2 = outputs2.get(output_key2) or outputs2.get("result", outputs2)
                    # Apply conversion function if provided
                    if conversion_function2:
                        value2 = execute_conversion_function_flexible(conversion_function2, value2)
                    input_key2 = "result"
                    if input_key2 in successor_node_inputs2:
                        existing2 = successor_node_inputs2[input_key2]
                        if isinstance(existing2, list):
                            existing2.append(value2)
                            successor_node_inputs2[input_key2] = existing2
                        else:
                            successor_node_inputs2[input_key2] = [existing2, value2]
                    else:
                        successor_node_inputs2[input_key2] = value2
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
        # Only start from explicitly configured trigger nodes
        # Do NOT start from all in-degree 0 nodes
        if graph.workflow.triggers:
            return list(graph.workflow.triggers)
        # Fallback: if no triggers configured, use in-degree 0 nodes
        return [node_id for node_id in graph.nodes.keys() if graph.in_degree(node_id) == 0]

    def _is_node_ready(
        self, graph: WorkflowGraph, node_id: str, pending_inputs: Dict[str, Dict[str, Any]]
    ) -> bool:
        # A node is ready when at least one incoming connection has provided data
        # Get all predecessor nodes
        predecessors = list(graph.predecessors(node_id))

        # If no predecessors, node is ready (e.g., trigger nodes)
        if not predecessors:
            return True

        # Check if at least one port has received data
        provided = pending_inputs.get(node_id, {})
        return len(provided) > 0

    def _format_trigger_description(self, trigger: TriggerInfo) -> str:
        """Format trigger information for user-friendly logging."""
        trigger_type = getattr(trigger, "trigger_type", "unknown")
        if trigger_type == "manual":
            return "Manual trigger"
        elif trigger_type == "webhook":
            return "Webhook trigger"
        elif trigger_type == "schedule":
            return "Scheduled trigger"
        elif trigger_type == "email":
            return "Email trigger"
        else:
            return f"{trigger_type.capitalize()} trigger"


__all__ = ["ExecutionEngine"]
