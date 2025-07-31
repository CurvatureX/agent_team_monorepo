"""
Flow Node Executor.

Handles flow control operations like if conditions, loops, switches, merges, etc.
"""

import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import BaseNodeExecutor, ExecutionStatus, NodeExecutionContext, NodeExecutionResult

try:
    from shared.node_specs import node_spec_registry
    from shared.node_specs.base import NodeSpec
except ImportError:
    node_spec_registry = None
    NodeSpec = None


class FlowNodeExecutor(BaseNodeExecutor):
    """Executor for FLOW_NODE type."""

    def _get_node_spec(self) -> Optional[NodeSpec]:
        """Get the node specification for flow nodes."""
        if node_spec_registry:
            # Return the IF spec as default (most commonly used)
            return node_spec_registry.get_spec("FLOW_NODE", "IF")
        return None

    def get_supported_subtypes(self) -> List[str]:
        """Get supported flow control subtypes."""
        return ["IF", "FILTER", "LOOP", "MERGE", "SWITCH", "WAIT"]

    def validate(self, node: Any) -> List[str]:
        """Validate flow node configuration."""
        errors = []

        if not node.subtype:
            errors.append("Flow subtype is required")
            return errors

        subtype = node.subtype

        if subtype == "IF":
            errors.extend(self._validate_required_parameters(node, ["condition"]))

        elif subtype == "FILTER":
            errors.extend(self._validate_required_parameters(node, ["filter_condition"]))

        elif subtype == "LOOP":
            errors.extend(self._validate_required_parameters(node, ["loop_type"]))
            loop_type = node.parameters.get("loop_type")
            if loop_type not in ["for_each", "while", "times"]:
                errors.append(f"Invalid loop type: {loop_type}")

        elif subtype == "SWITCH":
            errors.extend(self._validate_required_parameters(node, ["switch_cases"]))

        elif subtype == "WAIT":
            errors.extend(self._validate_required_parameters(node, ["wait_type"]))
            wait_type = node.parameters.get("wait_type")
            if wait_type not in ["time", "condition", "event"]:
                errors.append(f"Invalid wait type: {wait_type}")

        return errors

    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute flow control node."""
        start_time = time.time()
        logs = []

        try:
            subtype = context.node.subtype
            logs.append(f"Executing flow node with subtype: {subtype}")

            if subtype == "IF":
                return self._execute_if_condition(context, logs, start_time)
            elif subtype == "FILTER":
                return self._execute_filter(context, logs, start_time)
            elif subtype == "LOOP":
                return self._execute_loop(context, logs, start_time)
            elif subtype == "MERGE":
                return self._execute_merge(context, logs, start_time)
            elif subtype == "SWITCH":
                return self._execute_switch(context, logs, start_time)
            elif subtype == "WAIT":
                return self._execute_wait(context, logs, start_time)
            else:
                return self._create_error_result(
                    f"Unsupported flow subtype: {subtype}",
                    execution_time=time.time() - start_time,
                    logs=logs,
                )

        except Exception as e:
            return self._create_error_result(
                f"Error executing flow control: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs,
            )

    def _execute_if_condition(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute if condition."""
        condition = context.get_parameter("condition")

        logs.append(f"Evaluating if condition: {condition}")

        # Evaluate condition
        condition_result = self._evaluate_condition(condition, context.input_data)

        output_data = {
            "flow_type": "if",
            "condition": condition,
            "condition_result": condition_result,
            "input_data": context.input_data,
            "evaluated_at": datetime.now().isoformat(),
        }

        # Add routing information
        if condition_result:
            output_data["next_route"] = "true_branch"
            logs.append("Condition evaluated to TRUE")
        else:
            output_data["next_route"] = "false_branch"
            logs.append("Condition evaluated to FALSE")

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_filter(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute filter operation."""
        filter_condition = context.get_parameter("filter_condition")

        logs.append(f"Applying filter: {filter_condition}")

        input_data = context.input_data

        # Apply filter
        if isinstance(input_data, list):
            filtered_data = self._filter_list(input_data, filter_condition)
        elif isinstance(input_data, dict):
            filtered_data = self._filter_dict(input_data, filter_condition)
        else:
            filtered_data = input_data

        output_data = {
            "flow_type": "filter",
            "filter_condition": filter_condition,
            "original_data": input_data,
            "filtered_data": filtered_data,
            "original_count": len(input_data) if isinstance(input_data, (list, dict)) else 1,
            "filtered_count": len(filtered_data) if isinstance(filtered_data, (list, dict)) else 1,
            "filtered_at": datetime.now().isoformat(),
        }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_loop(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute loop operation."""
        loop_type = context.get_parameter("loop_type")
        max_iterations = context.get_parameter("max_iterations", 100)

        logs.append(f"Executing {loop_type} loop with max iterations: {max_iterations}")

        input_data = context.input_data

        if loop_type == "for_each":
            result = self._execute_for_each_loop(input_data, max_iterations)
        elif loop_type == "while":
            condition = context.get_parameter("while_condition", "true")
            result = self._execute_while_loop(input_data, condition, max_iterations)
        elif loop_type == "times":
            times = context.get_parameter("times", 1)
            result = self._execute_times_loop(input_data, times)
        else:
            result = {"error": f"Unknown loop type: {loop_type}"}

        output_data = {
            "flow_type": "loop",
            "loop_type": loop_type,
            "max_iterations": max_iterations,
            "input_data": input_data,
            "loop_result": result,
            "executed_at": datetime.now().isoformat(),
        }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_merge(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute merge operation."""
        merge_strategy = context.get_parameter("merge_strategy", "combine")

        logs.append(f"Merging data with strategy: {merge_strategy}")

        input_data = context.input_data

        # Simulate merging multiple data sources
        if merge_strategy == "combine":
            merged_data = self._combine_data(input_data)
        elif merge_strategy == "union":
            merged_data = self._union_data(input_data)
        elif merge_strategy == "intersection":
            merged_data = self._intersection_data(input_data)
        else:
            merged_data = input_data

        output_data = {
            "flow_type": "merge",
            "merge_strategy": merge_strategy,
            "input_data": input_data,
            "merged_data": merged_data,
            "merged_at": datetime.now().isoformat(),
        }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_switch(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute switch operation."""
        switch_cases = context.get_parameter("switch_cases", [])
        switch_value = context.input_data.get("switch_value", "")

        logs.append(f"Executing switch with value: {switch_value}")

        # Find matching case
        matched_case = None
        for case in switch_cases:
            if case.get("value") == switch_value:
                matched_case = case
                break

        if not matched_case:
            # Use default case if available
            matched_case = next(
                (case for case in switch_cases if case.get("is_default", False)), None
            )

        output_data = {
            "flow_type": "switch",
            "switch_value": switch_value,
            "switch_cases": switch_cases,
            "matched_case": matched_case,
            "next_route": matched_case.get("route", "default") if matched_case else "default",
            "switched_at": datetime.now().isoformat(),
        }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_wait(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute wait operation."""
        wait_type = context.get_parameter("wait_type")

        logs.append(f"Executing wait with type: {wait_type}")

        if wait_type == "time":
            duration = context.get_parameter("duration", 1)  # seconds
            logs.append(f"Waiting for {duration} seconds")
            # In real implementation, would actually wait
            wait_result = {"waited_seconds": duration}

        elif wait_type == "condition":
            condition = context.get_parameter("wait_condition", "true")
            logs.append(f"Waiting for condition: {condition}")
            # In real implementation, would poll condition
            wait_result = {"condition": condition, "condition_met": True}

        elif wait_type == "event":
            event_name = context.get_parameter("event_name", "unknown")
            logs.append(f"Waiting for event: {event_name}")
            # In real implementation, would wait for event
            wait_result = {"event_name": event_name, "event_received": True}

        else:
            wait_result = {"error": f"Unknown wait type: {wait_type}"}

        output_data = {
            "flow_type": "wait",
            "wait_type": wait_type,
            "wait_result": wait_result,
            "waited_at": datetime.now().isoformat(),
        }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _evaluate_condition(self, condition: str, data: Dict[str, Any]) -> bool:
        """Evaluate a condition expression."""
        # Simple condition evaluation
        # In real implementation, would use a proper expression evaluator

        if condition == "true":
            return True
        elif condition == "false":
            return False

        # Check for simple data-based conditions
        if ">" in condition:
            parts = condition.split(">")
            if len(parts) == 2:
                left = data.get(parts[0].strip(), 0)
                right = float(parts[1].strip())
                return left > right

        if "==" in condition:
            parts = condition.split("==")
            if len(parts) == 2:
                left = data.get(parts[0].strip(), "")
                right = parts[1].strip().strip("\"'")
                return str(left) == right

        # Default to false for unknown conditions
        return False

    def _filter_list(self, data: List[Any], condition: Dict[str, Any]) -> List[Any]:
        """Filter a list based on condition."""
        # Simulate list filtering
        return [item for item in data if self._item_matches_condition(item, condition)]

    def _filter_dict(self, data: Dict[str, Any], condition: Dict[str, Any]) -> Dict[str, Any]:
        """Filter a dictionary based on condition."""
        # Simulate dict filtering
        return {k: v for k, v in data.items() if self._item_matches_condition(v, condition)}

    def _item_matches_condition(self, item: Any, condition: Dict[str, Any]) -> bool:
        """Check if an item matches the filter condition."""
        # Simple condition matching
        if isinstance(condition, dict):
            for key, value in condition.items():
                if isinstance(item, dict) and item.get(key) != value:
                    return False
        return True

    def _execute_for_each_loop(self, data: Dict[str, Any], max_iterations: int) -> Dict[str, Any]:
        """Execute for-each loop."""
        items = data.get("items", [])
        processed_items = []

        for i, item in enumerate(items[:max_iterations]):
            processed_items.append({"index": i, "item": item, "processed": True})

        return {
            "type": "for_each",
            "total_items": len(items),
            "processed_items": processed_items,
            "iterations": min(len(items), max_iterations),
        }

    def _execute_while_loop(
        self, data: Dict[str, Any], condition: str, max_iterations: int
    ) -> Dict[str, Any]:
        """Execute while loop."""
        iterations = 0

        # Simulate while loop (would evaluate condition in real implementation)
        while iterations < max_iterations and iterations < 5:  # Limit for simulation
            iterations += 1

        return {
            "type": "while",
            "condition": condition,
            "iterations": iterations,
            "max_iterations": max_iterations,
        }

    def _execute_times_loop(self, data: Dict[str, Any], times: int) -> Dict[str, Any]:
        """Execute times loop."""
        results = []

        for i in range(times):
            results.append({"iteration": i + 1, "data": data})

        return {"type": "times", "times": times, "results": results}

    def _combine_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Combine multiple data sources."""
        # Simulate data combination
        return {"combined": True, "source_data": data, "combined_at": datetime.now().isoformat()}

    def _union_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Union multiple data sources."""
        # Simulate data union
        return {"union": True, "source_data": data, "union_at": datetime.now().isoformat()}

    def _intersection_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Intersect multiple data sources."""
        # Simulate data intersection
        return {
            "intersection": True,
            "source_data": data,
            "intersection_at": datetime.now().isoformat(),
        }
