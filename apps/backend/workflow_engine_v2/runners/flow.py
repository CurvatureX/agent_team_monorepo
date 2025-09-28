"""Flow node runners: IF, SWITCH, MERGE."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Use absolute imports
from shared.models import TriggerInfo
from shared.models.workflow_new import Node

from ..core.expr import get_path
from ..core.template import _eval_expression, eval_boolean
from ..services.timers import get_timer_service
from .base import NodeRunner


class IfRunner(NodeRunner):
    def run(self, node: Node, inputs: Dict[str, Any], trigger: TriggerInfo) -> Dict[str, Any]:
        data = inputs.get("main", inputs)
        expr = str(
            node.configurations.get("condition_expression")
            or node.configurations.get("expression")
            or ""
        )
        ctx = {"input": data, "config": node.configurations, "inputs": inputs}
        engine_ctx = inputs.get("_ctx") if isinstance(inputs, dict) else None
        if engine_ctx:
            ctx["nodes_id"] = getattr(engine_ctx, "node_outputs", {})
            ctx["nodes_name"] = getattr(engine_ctx, "node_outputs_by_name", {})
        result = eval_boolean(expr, ctx) if expr else False
        return {
            "true": data if result else None,
            "false": data if not result else None,
            "main": data,
        }


class SwitchRunner(NodeRunner):
    def run(self, node: Node, inputs: Dict[str, Any], trigger: TriggerInfo) -> Dict[str, Any]:
        cfg = node.configurations
        data = inputs.get("main", inputs)
        expr = str(cfg.get("switch_expression", ""))
        ctx = {"input": data, "config": cfg, "inputs": inputs}
        engine_ctx = inputs.get("_ctx") if isinstance(inputs, dict) else None
        if engine_ctx:
            ctx["nodes_id"] = getattr(engine_ctx, "node_outputs", {})
            ctx["nodes_name"] = getattr(engine_ctx, "node_outputs_by_name", {})
        switch_value = _eval_expression(expr, ctx) if expr else None
        default_port = cfg.get("default_case", "default")
        out: Dict[str, Any] = {"main": data}
        matched_ports = []
        for case in cfg.get("cases", []) or []:
            port = case.get("case_id") or case.get("name") or case.get("value")
            if port is None:
                continue
            if case.get("value") == switch_value:
                out[port] = data
                matched_ports.append(port)
        if not matched_ports:
            out[default_port] = data
        return out


class SplitRunner(NodeRunner):
    """SPLIT: partition data into multiple outputs based on predicate or keys.

    Config options:
    - by_key: list of keys to split (dict input)
    - predicate_paths: dict of port -> dot-path predicate (truthy goes to that port)
    Defaults to pass-through on 'main' if no config matches.
    """

    def run(self, node: Node, inputs: Dict[str, Any], trigger: TriggerInfo) -> Dict[str, Any]:
        cfg = node.configurations or {}
        data = inputs.get("main", inputs)
        out: Dict[str, Any] = {}
        preds = cfg.get("predicate_paths", {}) or {}
        if isinstance(preds, dict) and preds:
            for port, path in preds.items():
                val = get_path(data, str(path)) if isinstance(path, str) else None
                if val:
                    out[port] = data
        elif isinstance(cfg.get("by_key"), list) and isinstance(data, dict):
            for k in cfg["by_key"]:
                if k in data:
                    out[str(k)] = data[k]
        if not out:
            out["main"] = data
        return out


class MergeRunner(NodeRunner):
    def run(self, node: Node, inputs: Dict[str, Any], trigger: TriggerInfo) -> Dict[str, Any]:
        values = [v for k, v in inputs.items() if not k.startswith("_")]
        return {"merged": values, "metadata": {"total_inputs": len(values)}}


class FilterRunner(NodeRunner):
    def run(self, node: Node, inputs: Dict[str, Any], trigger: TriggerInfo) -> Dict[str, Any]:
        data = inputs.get("main", inputs)
        expr = node.configurations.get("predicate_expression") or node.configurations.get(
            "expression"
        )
        ctx = {"input": data, "config": node.configurations, "inputs": inputs}
        engine_ctx = inputs.get("_ctx") if isinstance(inputs, dict) else None
        if engine_ctx:
            ctx["nodes_id"] = getattr(engine_ctx, "node_outputs", {})
            ctx["nodes_name"] = getattr(engine_ctx, "node_outputs_by_name", {})
        ok = True
        if expr:
            val = _eval_expression(str(expr), ctx)
            ok = bool(val)
        return {"main": data if ok else None, "filtered": (None if ok else data)}


class SortRunner(NodeRunner):
    def run(self, node: Node, inputs: Dict[str, Any], trigger: TriggerInfo) -> Dict[str, Any]:
        data = inputs.get("main", inputs)
        items = (
            data if isinstance(data, list) else data.get("items") if isinstance(data, dict) else []
        )
        key_path = node.configurations.get("key_path") or node.configurations.get("sort_key")
        reverse = bool(node.configurations.get("descending", False))
        if not isinstance(items, list):
            return {"main": data}
        if key_path:

            def _key(it):
                return get_path(it, str(key_path)) if isinstance(it, (dict, list)) else it

            sorted_items = sorted(items, key=_key, reverse=reverse)
        else:
            sorted_items = sorted(items, reverse=reverse)
        if isinstance(data, dict):
            out = dict(data)
            out["items"] = sorted_items
            return {"main": out}
        return {"main": sorted_items}


class DelayRunner(NodeRunner):
    """Implements WAIT/DELAY semantics by scheduling a timer and signaling engine to pause."""

    def run(self, node: Node, inputs: Dict[str, Any], trigger: TriggerInfo) -> Dict[str, Any]:
        # The engine will schedule and pause based on this marker
        cfg = dict(node.configurations or {})
        # Allow dynamic override
        if isinstance(inputs, dict) and isinstance(inputs.get("delay_config"), dict):
            cfg.update(inputs.get("delay_config"))
        delay_ms = int(cfg.get("delay_ms") or 0)
        # Support various config names from spec
        if delay_ms == 0 and ("delay_seconds" in cfg or "duration_seconds" in cfg):
            sec = cfg.get("delay_seconds", cfg.get("duration_seconds", 0))
            try:
                delay_ms = int(float(sec) * 1000)
            except Exception:
                delay_ms = 0
        return {"_delay_ms": max(0, delay_ms), "main": inputs.get("main", inputs)}


class WaitRunner(NodeRunner):
    """Implements WAIT semantics by pausing until external resume.

    Engine will set execution to WAITING; caller should use resume_with_user_input
    to continue and pass the awaited data.
    """

    def run(self, node: Node, inputs: Dict[str, Any], trigger: TriggerInfo) -> Dict[str, Any]:
        # Condition-based wait: if wait_condition evaluates true, pass through; else wait
        cfg = dict(node.configurations or {})
        # Dynamic override via wait_config port
        if isinstance(inputs, dict) and isinstance(inputs.get("wait_config"), dict):
            cfg.update(inputs.get("wait_config"))
        data = inputs.get("main", inputs)
        # Cancel signal short-circuit
        if isinstance(inputs, dict) and inputs.get("cancel_signal"):
            return {"cancelled": data, "main": data}
        # External event short-circuit
        if isinstance(inputs, dict) and inputs.get("trigger_event") is not None:
            return {"completed": inputs.get("trigger_event"), "main": data}
        cond = cfg.get("wait_condition")
        if cond:
            ctx = {"input": data, "config": cfg, "inputs": inputs}
            engine_ctx = inputs.get("_ctx") if isinstance(inputs, dict) else None
            if engine_ctx:
                ctx["nodes_id"] = getattr(engine_ctx, "node_outputs", {})
                ctx["nodes_name"] = getattr(engine_ctx, "node_outputs_by_name", {})
            if bool(_eval_expression(str(cond), ctx)):
                return {"completed": data, "main": data}
        out = {"_wait": True, "main": data}
        timeout_ms = None
        if "timeout_seconds" in cfg:
            try:
                timeout_ms = int(float(cfg.get("timeout_seconds")) * 1000)
            except Exception:
                timeout_ms = None
        if timeout_ms and timeout_ms > 0:
            out["_wait_timeout_ms"] = timeout_ms
        return out


class TimeoutRunner(NodeRunner):
    """TIMEOUT flow: transition to timeout after specified period unless bypass condition.

    - If condition_expression/expression evaluates true, pass-through immediately (main->timeout or completed depending on config)
    - Otherwise, schedule a timeout using engine semantics (engine will treat like WAIT with timeout)
    """

    def run(self, node: Node, inputs: Dict[str, Any], trigger: TriggerInfo) -> Dict[str, Any]:
        cfg = node.configurations or {}
        data = inputs.get("main", inputs)
        cond = cfg.get("condition_expression") or cfg.get("expression")
        if cond:
            ctx = {"input": data, "config": cfg, "inputs": inputs}
            engine_ctx = inputs.get("_ctx") if isinstance(inputs, dict) else None
            if engine_ctx:
                ctx["nodes_id"] = getattr(engine_ctx, "node_outputs", {})
                ctx["nodes_name"] = getattr(engine_ctx, "node_outputs_by_name", {})
            if eval_boolean(str(cond), ctx):
                # immediate timeout path or completed based on config
                if bool(cfg.get("immediate_timeout", False)):
                    return {"timeout": data, "main": data}
                return {"completed": data, "main": data}

        timeout_ms = 0
        try:
            if cfg.get("timeout_seconds") is not None:
                timeout_ms = int(float(cfg.get("timeout_seconds")) * 1000)
            elif cfg.get("timeout_ms") is not None:
                timeout_ms = int(cfg.get("timeout_ms"))
        except Exception:
            timeout_ms = 0
        # Use same engine mechanic as WAIT: engine will interpret _wait + _wait_timeout_ms
        out = {"_wait": True, "_wait_timeout_ms": max(0, timeout_ms), "main": data}
        return out


class LoopRunner(NodeRunner):
    """Simplified LOOP: supports for_range and for_each (aggregate results).

    Outputs:
    - iteration: list of per-iteration data
    - completed: main data with summary stats
    """

    def run(self, node: Node, inputs: Dict[str, Any], trigger: TriggerInfo) -> Dict[str, Any]:
        cfg = node.configurations
        data = inputs.get("main", inputs)
        results = []
        loop_type = cfg.get("loop_type", "for_range")
        max_iter = int(cfg.get("max_iterations", 100))
        iter_var = cfg.get("iteration_variable", "index")

        if loop_type == "for_each":
            arr_path = str(cfg.get("array_path", ""))
            arr = (
                get_path({"data": data} if not isinstance(data, dict) else data, arr_path)
                if arr_path
                else None
            )
            if not isinstance(arr, list):
                arr = []
            for idx, item in enumerate(arr[:max_iter], start=1):
                results.append({iter_var: item})
        elif loop_type == "while":
            cond = cfg.get("loop_condition") or cfg.get("condition") or ""
            i = 0
            while i < max_iter:
                ctx = {"input": data, "config": cfg, "iteration": i}
                engine_ctx = inputs.get("_ctx") if isinstance(inputs, dict) else None
                if engine_ctx:
                    ctx["nodes_id"] = getattr(engine_ctx, "node_outputs", {})
                    ctx["nodes_name"] = getattr(engine_ctx, "node_outputs_by_name", {})
                if cond and not eval_boolean(str(cond), ctx):
                    break
                results.append({iter_var: i})
                i += 1
        else:
            start = int(cfg.get("start_value", 0))
            end = int(cfg.get("end_value", 0))
            step = int(cfg.get("step_value", 1)) or 1
            count = 0
            i = start
            cmp = (lambda x: x <= end) if step >= 0 else (lambda x: x >= end)
            while cmp(i) and count < max_iter:
                results.append({iter_var: i})
                i += step
                count += 1

        summary = {
            "total_iterations": len(results),
            "successful_iterations": len(results),
            "failed_iterations": 0,
            "loop_completed": True,
        }
        if isinstance(data, dict):
            completed = dict(data)
            completed.update(summary)
        else:
            completed = summary

        return {
            "iteration": results,
            "completed": completed,
            "main": completed,
        }


class ForEachRunner(NodeRunner):
    """Splits a list into individual items for downstream processing.

    Outputs a list under 'items'. Downstream nodes can rely on receiving a list
    and process items individually or via subsequent LOOP.
    """

    def run(self, node: Node, inputs: Dict[str, Any], trigger: TriggerInfo) -> Dict[str, Any]:
        data = inputs.get("main", inputs)
        if isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
            items = data["items"]
        elif isinstance(data, list):
            items = data
        else:
            items = [data]
        # Emit iteration list to trigger fan-out in engine
        return {"iteration": items, "main": items}


__all__ = [
    "IfRunner",
    "SwitchRunner",
    "MergeRunner",
    "FilterRunner",
    "SortRunner",
    "DelayRunner",
    "WaitRunner",
    "LoopRunner",
    "ForEachRunner",
    "SplitRunner",
]
