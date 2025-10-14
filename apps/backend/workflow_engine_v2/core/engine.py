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
import json as _json
import logging
import os
import random
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from supabase import create_client

logger = logging.getLogger(__name__)

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
from shared.models.workflow import Workflow
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
from workflow_engine_v2.utils.run_data import build_run_data_snapshot


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
        # Allow only a very small set of builtins and a safe importer that permits json only
        def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "json":
                return _json
            raise ImportError(f"Unsafe import blocked: {name}")

        namespace = {
            "Dict": Dict,
            "Any": Any,
            # Expose json directly so conversions can use it without importing
            "json": _json,
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
                # Common safe builtins often needed in conversions
                "sorted": sorted,
                "any": any,
                "all": all,
                "isinstance": isinstance,
                "type": type,
                # Safe, narrowly-scoped import support (json only)
                "__import__": _safe_import,
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
                    get_async_user_friendly_logger,
                )

                self._user_friendly_logger = get_async_user_friendly_logger()
            except ImportError:
                pass

    def _persist_execution(self, execution: Execution) -> None:
        """Persist execution state and maintain a run_data snapshot."""
        try:
            execution.run_data = build_run_data_snapshot(execution)
        except Exception as snapshot_error:  # pragma: no cover - defensive logging only
            logging.getLogger(__name__).warning(
                "Failed to build run_data snapshot for execution %s: %s",
                execution.execution_id,
                snapshot_error,
            )
        self._repo.save(execution)

    def _snapshot_execution(self, execution: Execution) -> Execution:
        """Ensure run_data is populated before returning execution state."""
        try:
            execution.run_data = build_run_data_snapshot(execution)
        except Exception as snapshot_error:  # pragma: no cover - defensive logging only
            logging.getLogger(__name__).warning(
                "Failed to snapshot run_data for execution %s: %s",
                execution.execution_id,
                snapshot_error,
            )
        return execution

    def validate_against_specs(self, workflow: Workflow) -> None:
        # Ensure spec exists for each node (type/subtype)
        for n in workflow.nodes:
            _ = get_spec(n.type, n.subtype)
        # Additional validation for ports and configurations
        validate_workflow(workflow)

    def run(
        self,
        workflow: Workflow,
        trigger: TriggerInfo,
        workflow_id: str,
        trace_id: Optional[str] = None,
        start_from_node: Optional[str] = None,
        skip_trigger_validation: bool = False,
        execution_id: Optional[str] = None,
    ) -> Execution:
        """Execute workflow synchronously with required workflow ID.

        Args:
            workflow: The workflow to execute
            trigger: Trigger information
            workflow_id: Database table workflow ID (REQUIRED - do NOT use workflow.metadata.id)
            trace_id: Optional trace ID for debugging
            start_from_node: Optional node ID to start execution from (skips upstream nodes)
            skip_trigger_validation: Whether to skip trigger validation when using start_from_node
        """
        logger.info(
            f"🟢 ENTERED run() method for execution_id={execution_id}, workflow_id={workflow_id}"
        )
        self.validate_against_specs(workflow)
        logger.info(f"🟢 Validation complete for {execution_id}")

        exec_id = execution_id or str(uuid.uuid4())
        trace_id = trace_id or str(uuid.uuid4())

        # IMPORTANT: Use the provided workflow_id from database, NOT workflow.metadata.id
        # The database table ID is the authoritative source

        workflow_execution = Execution(
            id=exec_id,
            execution_id=exec_id,
            workflow_id=workflow_id,
            workflow_version=workflow.metadata.version,
            status=ExecutionStatus.RUNNING,
            start_time=_now_ms(),
            trigger_info=trigger,
        )
        we = workflow_execution  # Legacy alias used in downstream helpers

        # User-friendly logging if enabled
        if self._user_friendly_logger:
            workflow_name = workflow.metadata.name or "Unnamed Workflow"
            self._user_friendly_logger.log_workflow_start(
                execution=workflow_execution,
                workflow_name=workflow_name,
                total_nodes=len(workflow.nodes),
                trigger_info=self._format_trigger_description(trigger),
            )
            # NOTE: Do NOT call _flush_logs() here - it makes blocking database calls
            # The background OutboxFlusher thread will handle flushing automatically

        logger.info(f"🔵 About to log execution started")
        self._log.log(workflow_execution, level=LogLevel.INFO, message="Execution started")
        logger.info(f"🔵 About to publish execution_started event")
        self._events.execution_started(workflow_execution)
        logger.info(f"🔵 About to persist execution to database")
        self._persist_execution(workflow_execution)
        logger.info(f"🔵 Execution persisted successfully")

        # Update workflow's latest_execution_time and latest_execution_id when execution starts
        self._update_workflow_execution_fields(
            workflow_id=workflow_id,
            latest_execution_time=workflow_execution.start_time,
            latest_execution_id=workflow_execution.execution_id,
        )

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

        # Determine starting nodes
        if start_from_node:
            # Start from specified node, passing trigger_data directly as inputs
            if start_from_node not in graph.nodes:
                raise ValueError(f"start_from_node '{start_from_node}' not found in workflow")

            logger.info(f"🎯 Starting execution from node: {start_from_node}")
            logger.info(f"📥 Trigger data will be passed directly to {start_from_node}")

            # Initialize pending_inputs for the start node with trigger_data
            trigger_data = trigger.trigger_data if trigger.trigger_data else {}
            pending_inputs[start_from_node] = {"result": trigger_data}

            queue: List[Dict[str, Any]] = [{"node_id": start_from_node, "override": None}]
        else:
            # Normal execution: start from initial ready nodes
            queue: List[Dict[str, Any]] = [
                {"node_id": node_id, "override": None}
                for node_id in self._get_initial_ready_nodes(graph)
            ]
        while queue:
            task = queue.pop(0)
            current_node_id = task["node_id"]
            override = task.get("override")
            is_fanout_run = override is not None

            logger.info(
                f"📤 QUEUE: Popped node {current_node_id} from queue (queue_size={len(queue)}, is_fanout={is_fanout_run})"
            )
            logger.info(
                f"📋 QUEUE: executed_main={executed_main}, checking if {current_node_id} already executed"
            )

            if not is_fanout_run and current_node_id in executed_main:
                logger.info(f"⏭️ QUEUE: Skipping {current_node_id} - already in executed_main")
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

            # Prepare inputs for execution
            inputs: Dict[str, Any] = {}
            if is_fanout_run:
                inputs.update(override or {})
            else:
                inputs.update(pending_inputs.get(current_node_id, {}))
            inputs["_ctx"] = execution_context

            # Log node execution start with detailed information
            clean_inputs = {k: v for k, v in inputs.items() if not k.startswith("_")}

            # Backend developer logs (keep verbose with emoji for debugging)
            logger.info("=" * 80)
            logger.info(f"🚀 Executing Node: {node.name}")
            logger.info(f"   Type: {node.type}, Subtype: {node.subtype}")
            logger.info(f"   Node ID: {current_node_id}")
            logger.info(f"📥 Input Parameters: {clean_inputs}")
            logger.info("=" * 80)

            # User-facing logs (concise, no emoji, structured data)
            if self._user_friendly_logger:
                self._user_friendly_logger.log_node_start(
                    execution_id=workflow_execution.execution_id,
                    node=node,
                    input_summary=clean_inputs,  # Pass clean dict
                )

            self._events.node_started(workflow_execution, current_node_id, node_execution)

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

            logger.info(
                f"🔄 RETRY LOOP: Starting retry loop for {current_node_id}, max_retries={max_retries}"
            )

            while attempt <= max_retries:
                logger.info(f"🔄 RETRY LOOP: Attempt {attempt}/{max_retries} for {current_node_id}")
                try:
                    runner = default_runner_for(node)
                    logger.info(
                        f"🔄 RETRY LOOP: Got runner {type(runner).__name__} for {current_node_id}"
                    )

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
                        logger.info(
                            f"⏱️ RETRY LOOP: About to call runner.run() via ThreadPool (timeout={exec_timeout}s) for {current_node_id}"
                        )
                        future = self._pool.submit(runner.run, node, inputs, trigger)
                        outputs = future.result(timeout=max(0.001, exec_timeout))
                    else:
                        logger.info(
                            f"🎯 RETRY LOOP: About to call runner.run() directly (no timeout) for {current_node_id}"
                        )
                        outputs = runner.run(node, inputs, trigger)

                    logger.info(
                        f"✅ RETRY LOOP: runner.run() completed successfully for {current_node_id}"
                    )
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
                node_execution.status = NodeExecutionStatus.FAILED
                workflow_execution.status = ExecutionStatus.ERROR
                workflow_execution.end_time = _now_ms()
                workflow_execution.duration_ms = workflow_execution.end_time - (
                    workflow_execution.start_time or workflow_execution.end_time
                )
                error_msg = str(last_exc)
                self._log.log(
                    workflow_execution,
                    level=LogLevel.ERROR,
                    message=f"Node {node.name} failed",
                    node_id=current_node_id,
                )
                self._events.node_failed(workflow_execution, current_node_id, node_execution)
                self._events.execution_failed(workflow_execution)
                try:
                    # NodeError and ExecutionError already imported above
                    node_execution.error = NodeError(
                        error_code="NODE_EXEC_ERROR",
                        error_message=error_msg,
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
                self._persist_execution(we)

                # CRITICAL: Log completion BEFORE breaking to capture exception details
                if self._user_friendly_logger:
                    try:
                        # Capture input params for error logging
                        clean_inputs = {k: v for k, v in inputs.items() if not k.startswith("_")}
                        self._user_friendly_logger.log_node_complete(
                            execution_id=workflow_execution.execution_id,
                            node_id=current_node_id,
                            success=False,
                            duration_ms=node_execution.duration_ms,
                            output_summary={
                                "input_params": clean_inputs,
                                "error": error_msg,
                            },
                            error_message=error_msg,
                        )
                        # Background flusher will handle persistence
                        logger.info(f"✅ Logged error for exception-failed node {current_node_id}")
                    except Exception as log_err:
                        logger.error(f"❌ Failed to log node exception: {log_err}")

                # Update workflow execution fields to mark failure
                self._update_workflow_execution_fields(
                    workflow_id=workflow_id,
                    latest_execution_status=ExecutionStatus.ERROR.value,
                    latest_execution_id=workflow_execution.execution_id,
                )

                # Update workflow statistics (even for failed executions)
                self._update_workflow_statistics(
                    workflow_id=workflow_id,
                    duration_ms=workflow_execution.duration_ms or 0,
                    credits_consumed=workflow_execution.credits_consumed or 0,
                    success=False,
                    execution_time=workflow_execution.end_time or _now_ms(),
                )

                # CRITICAL: Break from the outer queue loop to stop workflow execution
                # Clear the queue to prevent any remaining nodes from executing
                queue.clear()
                break

            # HIL (Human-in-the-Loop) Wait handling with database persistence
            if outputs.get("_hil_wait"):
                node_execution.input_data = inputs
                node_execution.status = NodeExecutionStatus.WAITING_INPUT
                workflow_execution.current_node_id = current_node_id
                workflow_execution.status = ExecutionStatus.WAITING_FOR_HUMAN

                # Create workflow execution pause record for HIL
                try:
                    hil_output = outputs.get("result")
                    if not hil_output and isinstance(outputs, dict):
                        hil_output = outputs.get("main")
                    if not hil_output:
                        hil_output = {}

                    pause_data = {
                        "hil_interaction_id": outputs.get("_hil_interaction_id"),
                        "hil_timeout_seconds": outputs.get("_hil_timeout_seconds"),
                        "hil_node_id": outputs.get("_hil_node_id"),
                        "pause_context": {
                            "node_output": hil_output,
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
                        "timeout_action": hil_output.get("timeout_action", "fail"),
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

                self._events.user_input_required(
                    workflow_execution, current_node_id, node_execution
                )
                return self._snapshot_execution(workflow_execution)
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
                return self._snapshot_execution(workflow_execution)
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
                return self._snapshot_execution(workflow_execution)

            # Streaming support: publish partial chunks if provided
            try:
                chunks = outputs.get("_stream_chunks") if isinstance(outputs, dict) else None
                if chunks and isinstance(chunks, list):
                    for ch in chunks:
                        self._events.node_output_update(
                            workflow_execution,
                            current_node_id,
                            node_execution,
                            partial={"stream": ch},
                        )
            except Exception:
                pass
            # Sanitize outputs for storage/propagation: only port fields (no control keys starting with '_')
            sanitized_outputs = (
                {k: v for k, v in outputs.items() if isinstance(k, str) and not k.startswith("_")}
                if isinstance(outputs, dict)
                else {}
            )

            # Enforce that each port payload exactly matches node spec output_params keys
            def _shape_payload(payload: Any) -> Dict[str, Any]:
                # Get output_params from node spec registry, not from node definition
                try:
                    spec = get_spec(node.type, node.subtype)
                    allowed_defaults = getattr(spec, "output_params", {}) or {}
                except Exception:
                    # Fallback to node.output_params if spec not available
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

            # Fail-fast: Check if node execution returned success=False
            # Many nodes (TOOL, EXTERNAL_ACTION, etc.) return {"result": {"success": False, ...}}
            # to indicate failure without throwing an exception
            node_failed = False
            try:
                for port_data in shaped_outputs.values():
                    if isinstance(port_data, dict) and port_data.get("success") is False:
                        error_msg = port_data.get("error_message", "Node execution failed")
                        logger.error(f"❌ Node {node.name} returned success=False: {error_msg}")

                        # Mark node as failed
                        node_execution.status = NodeExecutionStatus.FAILED
                        node_execution.error = NodeError(
                            error_code="NODE_EXECUTION_FAILED",
                            error_message=error_msg,
                            error_details={"node_output": port_data},
                            is_retryable=False,
                            timestamp=_now_ms(),
                        )

                        # Mark workflow as error
                        workflow_execution.status = ExecutionStatus.ERROR
                        workflow_execution.end_time = _now_ms()
                        workflow_execution.duration_ms = workflow_execution.end_time - (
                            workflow_execution.start_time or workflow_execution.end_time
                        )
                        workflow_execution.error = ExecutionError(
                            error_code="EXECUTION_FAILED",
                            error_message=f"Node {node.name} failed: {error_msg}",
                            error_node_id=current_node_id,
                            stack_trace=None,
                            timestamp=_now_ms(),
                            is_retryable=False,
                        )

                        # Log and notify
                        self._log.log(
                            workflow_execution,
                            level=LogLevel.ERROR,
                            message=f"Node {node.name} failed with success=False",
                            node_id=current_node_id,
                        )
                        self._events.node_failed(
                            workflow_execution, current_node_id, node_execution
                        )
                        self._events.execution_failed(workflow_execution)
                        self._persist_execution(workflow_execution)

                        # CRITICAL: Log completion BEFORE breaking to capture error details
                        if self._user_friendly_logger:
                            try:
                                clean_outputs = {
                                    k: v for k, v in shaped_outputs.items() if not k.startswith("_")
                                }
                                clean_inputs = {
                                    k: v for k, v in inputs.items() if not k.startswith("_")
                                }
                                self._user_friendly_logger.log_node_complete(
                                    execution_id=workflow_execution.execution_id,
                                    node_id=current_node_id,
                                    success=False,
                                    duration_ms=node_execution.duration_ms,
                                    output_summary={
                                        "input_params": clean_inputs,
                                        "output_params": clean_outputs,
                                        "error": error_msg,
                                    },
                                    error_message=error_msg,
                                )
                                # Background flusher will handle persistence
                                logger.info(f"✅ Logged error for failed node {current_node_id}")
                            except Exception as log_err:
                                logger.error(f"❌ Failed to log node failure: {log_err}")

                        # Update workflow execution fields to mark failure
                        self._update_workflow_execution_fields(
                            workflow_id=workflow_id,
                            latest_execution_status=ExecutionStatus.ERROR.value,
                            latest_execution_id=workflow_execution.execution_id,
                        )

                        # Update workflow statistics (even for failed executions)
                        self._update_workflow_statistics(
                            workflow_id=workflow_id,
                            duration_ms=workflow_execution.duration_ms or 0,
                            credits_consumed=workflow_execution.credits_consumed or 0,
                            success=False,
                            execution_time=workflow_execution.end_time or _now_ms(),
                        )

                        node_failed = True
                        break  # Stop checking other ports
            except Exception as check_err:
                logger.warning(f"Failed to check node success status: {check_err}")

            # If node failed, stop workflow execution
            if node_failed:
                # CRITICAL: Clear the queue to prevent any remaining nodes from executing
                queue.clear()
                break
            # Merge execution details patch if provided by runner
            try:
                details_patch = outputs.get("_details") if isinstance(outputs, dict) else None
                if details_patch:
                    for k, v in details_patch.items():
                        setattr(node_execution.execution_details, k, v)
            except Exception:
                pass
            # Track AI tool usage for user-facing logs
            try:
                if node.type == "AI_AGENT" and isinstance(outputs, dict):
                    details = outputs.get("_details", {})
                    tool_calls = details.get("tool_calls", [])

                    if tool_calls and self._user_friendly_logger:
                        for tool_call in tool_calls:
                            self._user_friendly_logger.log_tool_usage(
                                execution_id=workflow_execution.execution_id,
                                node_id=current_node_id,
                                node_name=node.name,
                                tool_name=tool_call.get("name", "unknown"),
                                tool_input=tool_call.get("input"),
                                tool_output=tool_call.get("output"),
                            )
            except Exception as e:
                logger.debug(f"Failed to log tool usage: {e}")

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

            # Log node execution completion with output details
            clean_outputs = {k: v for k, v in shaped_outputs.items() if not k.startswith("_")}

            # Backend developer logs (keep verbose with emoji for debugging)
            logger.info("=" * 80)
            logger.info(f"✅ Node Completed: {node.name}")
            logger.info(f"   Node ID: {current_node_id}")
            logger.info(f"📥 Input Parameters: {clean_inputs}")
            logger.info(f"📤 Output Parameters: {clean_outputs}")
            logger.info("=" * 80)
            logger.info(
                f"🟢 POST-COMPLETION: Starting post-node-completion processing for {current_node_id}"
            )

            try:
                # User-facing logs (concise, no emoji, structured data)
                logger.info(f"🟡 POST-COMPLETION: About to call user-friendly logger")
                try:
                    if self._user_friendly_logger:
                        self._user_friendly_logger.log_node_complete(
                            execution_id=workflow_execution.execution_id,
                            node_id=current_node_id,
                            success=True,
                            duration_ms=node_execution.duration_ms,
                            output_summary={
                                "input_params": clean_inputs,
                                "output_params": clean_outputs,
                            },
                        )
                        # Background flusher will handle persistence (no blocking flush needed)
                        logger.info(f"✅ Logged completion for node {current_node_id}")
                except Exception as log_err:
                    logger.error(f"❌ User-friendly logger failed: {log_err}")
                    import traceback

                    logger.error(f"Traceback: {traceback.format_exc()}")

                logger.info(f"🔍 Before events for node {current_node_id}")
                try:
                    self._events.node_output_update(
                        workflow_execution, current_node_id, node_execution
                    )
                    logger.info(f"✓ node_output_update complete")
                    self._events.node_completed(workflow_execution, current_node_id, node_execution)
                    logger.info(f"✓ node_completed event complete")
                except Exception as event_err:
                    logger.error(f"❌ Event publishing failed: {event_err}")
                    import traceback

                    logger.error(f"Traceback: {traceback.format_exc()}")

                logger.info(f"🔍 About to persist execution for node {current_node_id}")
                self._persist_execution(workflow_execution)
                logger.info(f"✓ Persist complete for node {current_node_id}")
                # Update node outputs context (by id and by name)
                execution_context.node_outputs[current_node_id] = shaped_outputs
                try:
                    node_name = node.name
                    execution_context.node_outputs_by_name[node_name] = shaped_outputs
                except Exception:
                    pass

                logger.info(f"🚦 Starting successor propagation for node {current_node_id}")
                # Propagate, including fan-out
                # BFS: Only propagate if the required output_key exists in the node's outputs
                successors_list = list(graph.successors(current_node_id))
                logger.info(
                    f"🔗 Found {len(successors_list)} successor(s) for node {current_node_id}: {successors_list}"
                )
                for (
                    successor_node,
                    output_key,
                    conversion_function,
                ) in successors_list:
                    logger.info(
                        f"📍 Processing successor: {successor_node}, output_key: {output_key}"
                    )
                    # Check if output_key exists in node outputs
                    # If output_key is not present, skip this connection (conditional flow)
                    value = shaped_outputs.get(output_key)
                    logger.info(f"📊 Value for output_key '{output_key}': {value is not None}")

                    # Special case: "iteration" for fan-out (LOOP nodes)
                    if output_key == "iteration" and isinstance(value, list):
                        for item in value:
                            item_value = item
                            # Apply conversion function if provided
                            if conversion_function and isinstance(conversion_function, str):
                                try:
                                    # Engine has already extracted the iteration item
                                    # Conversion function receives the extracted value directly
                                    wrapped_input = {
                                        "value": item_value,  # ✅ Direct access
                                        "output": item_value,  # ✅ Alias
                                        "data": {"result": item_value},  # Legacy (deprecated)
                                    }
                                    converted_data = execute_conversion_function_flexible(
                                        conversion_function,
                                        wrapped_input,
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
                            # RESPONSIBILITY: Extract the specific output using output_key from connection
                            # The conversion function receives the ALREADY EXTRACTED value, not the full node output
                            raw_value = raw_outputs.get(output_key)
                            if raw_value is None:
                                raw_value = raw_outputs.get("result", raw_outputs)

                            # Wrap extracted value for conversion function access
                            # Conversion functions should use input_data["value"] or input_data["output"]
                            # to access the already-extracted output (NOT nested extraction)
                            wrapped_input = {
                                "value": raw_value,  # ✅ Direct access to extracted output
                                "output": raw_value,  # ✅ Alias for extracted output
                                "data": {"result": raw_value},  # Legacy nested format (deprecated)
                            }
                            converted_data = execute_conversion_function_flexible(
                                conversion_function,
                                wrapped_input,
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
                        logger.info(
                            f"➕ QUEUE: Adding successor {successor_node} to queue (from {current_node_id})"
                        )
                        queue.append({"node_id": successor_node, "override": None})
                        logger.info(
                            f"📊 QUEUE: Current queue size: {len(queue)}, queue={[t['node_id'] for t in queue]}"
                        )
            except Exception as post_completion_err:
                logger.error(
                    f"❌❌❌ CRITICAL: Post-completion processing failed for {current_node_id}: {post_completion_err}"
                )
                import traceback

                logger.error(f"Full traceback: {traceback.format_exc()}")
                raise  # Re-raise to trigger fail-fast

            workflow_execution.execution_sequence.append(current_node_id)
            if not is_fanout_run:
                executed_main.add(current_node_id)
                logger.info(
                    f"✅ QUEUE: Added {current_node_id} to executed_main. Total executed: {len(executed_main)}"
                )

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
            self._persist_execution(workflow_execution)

            # User-friendly workflow completion log
            if self._user_friendly_logger:
                try:
                    self._user_friendly_logger.log_workflow_complete(
                        execution=workflow_execution,
                        success=True,
                        duration_ms=workflow_execution.duration_ms,
                        summary={
                            "total_nodes": len(workflow.nodes),
                            "executed_nodes": len(workflow_execution.execution_sequence),
                        },
                    )
                    # Background flusher will handle persistence
                except Exception as log_err:
                    logger.error(f"❌ Failed to log workflow completion: {log_err}")

            # Update workflow's latest_execution_status when execution completes successfully
            self._update_workflow_execution_fields(
                workflow_id=workflow_id,
                latest_execution_status=ExecutionStatus.SUCCESS.value,
                latest_execution_id=workflow_execution.execution_id,
            )

            # Update workflow statistics
            self._update_workflow_statistics(
                workflow_id=workflow_id,
                duration_ms=workflow_execution.duration_ms or 0,
                credits_consumed=workflow_execution.credits_consumed or 0,
                success=True,
                execution_time=workflow_execution.end_time or _now_ms(),
            )
        else:
            # User-friendly workflow failure log
            if self._user_friendly_logger:
                try:
                    error_summary = {"total_nodes": len(workflow.nodes)}
                    if workflow_execution.error:
                        error_summary["error_message"] = workflow_execution.error.error_message
                        error_summary["error_node"] = workflow_execution.error.error_node_id

                    self._user_friendly_logger.log_workflow_complete(
                        execution=workflow_execution,
                        success=False,
                        duration_ms=workflow_execution.duration_ms,
                        summary=error_summary,
                    )
                    # Background flusher will handle persistence
                except Exception as log_err:
                    logger.error(f"❌ Failed to log workflow failure: {log_err}")

            # Update workflow's latest_execution_status when execution fails
            self._update_workflow_execution_fields(
                workflow_id=workflow_id,
                latest_execution_status=ExecutionStatus.ERROR.value,
                latest_execution_id=workflow_execution.execution_id,
            )

            # Update workflow statistics (even for failed executions)
            self._update_workflow_statistics(
                workflow_id=workflow_id,
                duration_ms=workflow_execution.duration_ms or 0,
                credits_consumed=workflow_execution.credits_consumed or 0,
                success=False,
                execution_time=workflow_execution.end_time or _now_ms(),
            )

        # CRITICAL: Flush all pending logs before returning
        if self._user_friendly_logger:
            try:
                self._user_friendly_logger.flush_sync(timeout=2.0)
                logger.info("✅ Flushed user-friendly logs before execution return")
            except Exception as flush_err:
                logger.error(f"⚠️ Failed to flush logs: {flush_err}")

        return self._snapshot_execution(workflow_execution)

    # Async wrappers for non-blocking execution
    async def run_async(
        self,
        workflow: Workflow,
        trigger: TriggerInfo,
        workflow_id: str,
        trace_id: Optional[str] = None,
        start_from_node: Optional[str] = None,
        skip_trigger_validation: bool = False,
        execution_id: Optional[str] = None,
    ) -> Execution:
        """Execute workflow asynchronously."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._pool,
            self.run,
            workflow,
            trigger,
            workflow_id,
            trace_id,
            start_from_node,
            skip_trigger_validation,
            execution_id,
        )

    async def execute_workflow(
        self,
        workflow: Workflow,
        trigger: TriggerInfo,
        workflow_id: str,
        trace_id: Optional[str] = None,
        start_from_node: Optional[str] = None,
        skip_trigger_validation: bool = False,
        execution_id: Optional[str] = None,
    ) -> Execution:
        """Async alias for run_async - for compatibility with ModernExecutionEngine API."""
        return await self.run_async(
            workflow,
            trigger,
            workflow_id,
            trace_id,
            start_from_node,
            skip_trigger_validation,
            execution_id,
        )

    # -------- Engine control API --------

    def resume_with_user_input(self, execution_id: str, node_id: str, input_data: Any) -> Execution:
        """Resume an execution waiting on HIL node with provided user input."""
        execution_context = self._store.get(execution_id)
        workflow_execution = execution_context.execution
        pending_inputs = execution_context.pending_inputs

        if workflow_execution.current_node_id != node_id:
            return self._snapshot_execution(workflow_execution)

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
        self._events.node_output_update(workflow_execution, node_id, node_execution)
        self._events.node_completed(workflow_execution, node_id, node_execution)
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
                    # Engine extracted value using output_key
                    # Conversion function receives already-extracted value
                    wrapped_input = {
                        "value": value,  # ✅ Direct access to extracted output
                        "output": value,  # ✅ Alias
                        "data": {"result": value},  # Legacy (deprecated)
                    }
                    converted_data = execute_conversion_function_flexible(
                        conversion_function, wrapped_input
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
        self._events.execution_resumed(workflow_execution)

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
            inputs["_ctx"] = execution_context
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
                    return self._snapshot_execution(workflow_execution)
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
                message="Execution completed successfully",
            )
            self._persist_execution(workflow_execution)

            # Update workflow's latest_execution_status when resumed execution completes successfully
            self._update_workflow_execution_fields(
                workflow_id=workflow_execution.workflow_id,
                latest_execution_status=ExecutionStatus.SUCCESS.value,
                latest_execution_id=workflow_execution.execution_id,
            )

            # Update workflow statistics
            self._update_workflow_statistics(
                workflow_id=workflow_execution.workflow_id,
                duration_ms=workflow_execution.duration_ms or 0,
                credits_consumed=workflow_execution.credits_consumed or 0,
                success=True,
                execution_time=workflow_execution.end_time or _now_ms(),
            )
        else:
            # Update workflow's latest_execution_status when resumed execution fails
            self._update_workflow_execution_fields(
                workflow_id=workflow_execution.workflow_id,
                latest_execution_status=ExecutionStatus.ERROR.value,
                latest_execution_id=workflow_execution.execution_id,
            )

            # Update workflow statistics (even for failed executions)
            self._update_workflow_statistics(
                workflow_id=workflow_execution.workflow_id,
                duration_ms=workflow_execution.duration_ms or 0,
                credits_consumed=workflow_execution.credits_consumed or 0,
                success=False,
                execution_time=workflow_execution.end_time or _now_ms(),
            )

        return self._snapshot_execution(workflow_execution)

    def _update_workflow_statistics(
        self,
        workflow_id: str,
        duration_ms: int,
        credits_consumed: int,
        success: bool,
        execution_time: int,
    ) -> bool:
        """Update workflow statistics in workflow_data.metadata.statistics."""
        try:
            # Create Supabase client for database operations
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

            if not supabase_url or not supabase_key:
                logger.warning("Supabase credentials not available, skipping statistics update")
                return False

            client = create_client(supabase_url, supabase_key)

            # Get current workflow_data
            result = (
                client.table("workflows").select("workflow_data").eq("id", workflow_id).execute()
            )

            if not result.data:
                logger.warning(f"Workflow {workflow_id} not found, skipping statistics update")
                return False

            workflow_data = result.data[0].get("workflow_data", {})

            # Ensure metadata and statistics exist
            if "metadata" not in workflow_data:
                workflow_data["metadata"] = {}

            metadata = workflow_data["metadata"]
            if "statistics" not in metadata:
                metadata["statistics"] = {
                    "total_runs": 0,
                    "average_duration_ms": 0,
                    "total_credits": 0,
                    "last_success_time": None,
                }

            stats = metadata["statistics"]

            # Update statistics
            old_total_runs = stats.get("total_runs", 0)
            old_avg_duration = stats.get("average_duration_ms", 0)
            old_total_credits = stats.get("total_credits", 0)

            # Calculate new values
            new_total_runs = old_total_runs + 1
            # Calculate running average: new_avg = (old_avg * old_count + new_value) / new_count
            new_avg_duration = int(
                (old_avg_duration * old_total_runs + duration_ms) / new_total_runs
            )
            new_total_credits = old_total_credits + credits_consumed

            stats["total_runs"] = new_total_runs
            stats["average_duration_ms"] = new_avg_duration
            stats["total_credits"] = new_total_credits

            # Update last_success_time only if execution was successful
            if success:
                stats["last_success_time"] = execution_time

            # Save updated workflow_data back to database
            update_result = (
                client.table("workflows")
                .update({"workflow_data": workflow_data})
                .eq("id", workflow_id)
                .execute()
            )

            if update_result.data:
                logger.info(
                    f"✅ Updated workflow {workflow_id} statistics: "
                    f"runs={new_total_runs}, avg_duration={new_avg_duration}ms, "
                    f"credits={new_total_credits}"
                )
                return True

            return False

        except Exception as e:
            # Log error but don't fail execution
            logger.warning(f"Failed to update workflow statistics: {str(e)}")
            import traceback

            logger.warning(f"Traceback: {traceback.format_exc()}")
            return False

    def _update_workflow_execution_fields(
        self,
        workflow_id: str,
        latest_execution_status: Optional[str] = None,
        latest_execution_time: Optional[int] = None,
        latest_execution_id: Optional[str] = None,
    ) -> bool:
        """Update workflow's latest/last execution fields.

        Persists top-level columns (latest_execution_*) and also mirrors into
        workflow_data.metadata as last_execution_* so API consumers can rely on
        metadata without additional lookups. Updates occur on start, success, or error.
        """
        try:
            # Create Supabase client for database operations
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

            if not supabase_url or not supabase_key:
                logger.warning("Supabase credentials not available, skipping workflow update")
                return False

            client = create_client(supabase_url, supabase_key)

            # Build update data for top-level workflow columns
            update_data = {}
            if latest_execution_status is not None:
                update_data["latest_execution_status"] = latest_execution_status
            if latest_execution_time is not None:
                # Convert milliseconds to timestamp
                from datetime import datetime

                update_data["latest_execution_time"] = datetime.fromtimestamp(
                    latest_execution_time / 1000
                ).isoformat()
            if latest_execution_id is not None:
                update_data["latest_execution_id"] = latest_execution_id

            if not update_data:
                return False

            # Update workflow record
            result = client.table("workflows").update(update_data).eq("id", workflow_id).execute()

            if result.data:
                logger.info(f"✅ Updated workflow {workflow_id} execution fields: {update_data}")
                # Also mirror into workflow_data.metadata.last_execution_* for consistency
                try:
                    # Determine a sensible ms timestamp if not provided (e.g., completion/error)
                    import time as _time

                    last_time_ms = (
                        latest_execution_time
                        if isinstance(latest_execution_time, (int, float))
                        else int(_time.time() * 1000)
                    )

                    wf_sel = (
                        client.table("workflows")
                        .select("workflow_data")
                        .eq("id", workflow_id)
                        .limit(1)
                        .execute()
                    )
                    if wf_sel.data:
                        wf_data = wf_sel.data[0].get("workflow_data") or {}
                        # Ensure dict
                        if isinstance(wf_data, dict):
                            metadata = wf_data.get("metadata") or {}
                            if not isinstance(metadata, dict):
                                metadata = {}
                            if latest_execution_status is not None:
                                try:
                                    metadata["last_execution_status"] = str(
                                        latest_execution_status
                                    ).upper()
                                except Exception:
                                    metadata["last_execution_status"] = latest_execution_status
                            # Always update time to reflect this event
                            metadata["last_execution_time"] = int(last_time_ms)
                            if latest_execution_id is not None:
                                metadata["last_execution_id"] = latest_execution_id
                            wf_data["metadata"] = metadata
                            client.table("workflows").update({"workflow_data": wf_data}).eq(
                                "id", workflow_id
                            ).execute()
                except Exception as mirror_err:  # pragma: no cover - best effort
                    logger.warning(
                        f"⚠️ Failed to mirror last_execution_* into metadata for {workflow_id}: {mirror_err}"
                    )
                return True

            return False

        except Exception as e:
            # Log error but don't fail execution
            logger.warning(f"Failed to update workflow execution fields: {str(e)}")
            return False

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

        except Exception as e:
            message = str(e)
            if "pause_data" in message or "hil_interaction_id" in message or "node_id" in message:
                try:
                    fallback_record = {
                        "execution_id": execution_id,
                        "paused_node_id": node_id,
                        "pause_reason": pause_reason,
                        "resume_conditions": {
                            "conditions": resume_conditions,
                            "pause_context": pause_data,
                        },
                        "status": "active",
                        "paused_at": datetime.utcnow().isoformat(),
                        "resume_trigger": None,
                    }
                    result = (
                        client.table("workflow_execution_pauses").insert(fallback_record).execute()
                    )
                    if result.data:
                        return result.data[0]["id"]
                except Exception as fallback_error:
                    message = f"Fallback pause insert failed: {fallback_error}"
                    if hasattr(self, "_log"):
                        self._log.log(
                            None,
                            level=LogLevel.ERROR,
                            message=message,
                            node_id=node_id,
                        )
                    return None
            else:
                if hasattr(self, "_log"):
                    self._log.log(
                        None,
                        level=LogLevel.ERROR,
                        message=f"Failed to create workflow pause record: {message}",
                        node_id=node_id,
                    )
                return None

        else:
            return None

        return None

    def resume_timer(
        self, execution_id: str, node_id: str, *, reason: str = "delay", port: str = "main"
    ) -> Execution:
        """Resume a timer-waiting node after delay has elapsed."""
        execution_context = self._store.get(execution_id)
        workflow_execution = execution_context.execution
        pending_inputs = execution_context.pending_inputs
        if workflow_execution.current_node_id != node_id:
            return self._snapshot_execution(workflow_execution)

        node_execution = workflow_execution.node_executions[node_id]
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
        self._events.node_output_update(workflow_execution, node_id, node_execution)
        self._events.node_completed(workflow_execution, node_id, node_execution)

        for (
            successor_node,
            output_key,
            conversion_function,
        ) in execution_context.graph.successors(node_id):
            successor_node_inputs = pending_inputs.setdefault(successor_node, {})
            value = outputs.get(output_key) or outputs.get("result", outputs)
            # Apply conversion function if provided
            if conversion_function:
                # Engine extracted value using output_key
                # Conversion function receives already-extracted value
                wrapped_input = {
                    "value": value,  # ✅ Direct access to extracted output
                    "output": value,  # ✅ Alias
                    "data": {"result": value},  # Legacy (deprecated)
                }
                value = execute_conversion_function_flexible(conversion_function, wrapped_input)
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
            inputs2["_ctx"] = execution_context
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
                    return self._snapshot_execution(workflow_execution)
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
                    return self._snapshot_execution(workflow_execution)
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
                        # Engine extracted value using output_key
                        # Conversion function receives already-extracted value
                        wrapped_input2 = {
                            "value": value2,  # ✅ Direct access to extracted output
                            "output": value2,  # ✅ Alias
                            "data": {"result": value2},  # Legacy (deprecated)
                        }
                        value2 = execute_conversion_function_flexible(
                            conversion_function2, wrapped_input2
                        )
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

            # Update workflow's latest_execution_status when timer-resumed execution completes successfully
            self._update_workflow_execution_fields(
                workflow_id=workflow_execution.workflow_id,
                latest_execution_status=ExecutionStatus.SUCCESS.value,
                latest_execution_id=workflow_execution.execution_id,
            )

            # Update workflow statistics
            self._update_workflow_statistics(
                workflow_id=workflow_execution.workflow_id,
                duration_ms=workflow_execution.duration_ms or 0,
                credits_consumed=workflow_execution.credits_consumed or 0,
                success=True,
                execution_time=workflow_execution.end_time or _now_ms(),
            )
        else:
            # Update workflow's latest_execution_status when timer-resumed execution fails
            self._update_workflow_execution_fields(
                workflow_id=workflow_execution.workflow_id,
                latest_execution_status=ExecutionStatus.ERROR.value,
                latest_execution_id=workflow_execution.execution_id,
            )

            # Update workflow statistics (even for failed executions)
            self._update_workflow_statistics(
                workflow_id=workflow_execution.workflow_id,
                duration_ms=workflow_execution.duration_ms or 0,
                credits_consumed=workflow_execution.credits_consumed or 0,
                success=False,
                execution_time=workflow_execution.end_time or _now_ms(),
            )

        return self._snapshot_execution(workflow_execution)

    def resume_due_timers(self) -> None:
        """Check and resume all due timers across executions."""
        for execution_id, node_id, reason, port in self._timers.due():
            self.resume_timer(execution_id, node_id, reason=reason, port=port)

    # Control operations
    def pause(self, execution_id: str) -> Execution:
        execution_context = self._store.get(execution_id)
        execution_context.execution.status = ExecutionStatus.PAUSED
        self._events.execution_paused(execution_context.execution)
        return execution_context.execution

    def cancel(self, execution_id: str) -> Execution:
        execution_context = self._store.get(execution_id)
        execution_context.execution.status = ExecutionStatus.CANCELED
        execution_context.execution.end_time = _now_ms()
        self._events.execution_failed(execution_context.execution)
        return execution_context.execution

    def retry_node(self, execution_id: str, node_id: str) -> Execution:
        execution_context = self._store.get(execution_id)
        workflow_execution = execution_context.execution
        if node_id in workflow_execution.node_executions:
            node_execution = workflow_execution.node_executions[node_id]
            node_execution.status = NodeExecutionStatus.PENDING
            node_execution.error = None
        return self._snapshot_execution(workflow_execution)

    # -------- Helpers --------

    def _get_initial_ready_nodes(self, graph: WorkflowGraph) -> List[str]:
        # Only start from explicitly configured trigger nodes
        # Do NOT start from all in-degree 0 nodes
        if graph.workflow.triggers:
            # Filter triggers to those present in the execution graph (excludes attached nodes)
            return [tid for tid in graph.workflow.triggers if tid in graph.nodes]
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
