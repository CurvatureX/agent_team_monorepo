"""
Flow Node Executor.

Handles flow control operations like if conditions, loops, switches, merges, etc.
"""

import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from shared.models.node_enums import NodeType, FlowSubtype
from shared.node_specs import node_spec_registry
from shared.node_specs.base import NodeSpec

from .base import BaseNodeExecutor, ExecutionStatus, NodeExecutionContext, NodeExecutionResult


class FlowNodeExecutor(BaseNodeExecutor):
    """Executor for FLOW_NODE type."""

    def _get_node_spec(self) -> Optional[NodeSpec]:
        """Get the node specification for flow nodes."""
        if node_spec_registry and self._subtype:
            # Return the specific spec for current subtype
            return node_spec_registry.get_spec(NodeType.FLOW.value, self._subtype)
        return None

    def get_supported_subtypes(self) -> List[str]:
        """Get supported flow control subtypes."""
        return [subtype.value for subtype in FlowSubtype]

    def validate(self, node: Any) -> List[str]:
        """Validate flow node configuration using spec-based validation."""
        # First use the base class validation which includes spec validation
        errors = super().validate(node)

        # If spec validation passed, we're done
        if not errors and self.spec:
            return errors

        # Fallback if spec not available
        if not node.subtype:
            errors.append("Flow subtype is required")
            return errors

        if node.subtype not in self.get_supported_subtypes():
            errors.append(f"Unsupported flow subtype: {node.subtype}")

        return errors

    def _validate_legacy(self, node: Any) -> List[str]:
        """Legacy validation for backward compatibility."""
        errors = []

        if not hasattr(node, "subtype"):
            return errors

        subtype = node.subtype

        if subtype == FlowSubtype.IF.value:
            errors.extend(self._validate_required_parameters(node, ["condition"]))

        elif subtype == FlowSubtype.FILTER.value:
            errors.extend(self._validate_required_parameters(node, ["filter_condition"]))

        elif subtype == FlowSubtype.LOOP.value:
            errors.extend(self._validate_required_parameters(node, ["loop_type"]))
            if hasattr(node, "parameters"):
                loop_type = node.parameters.get("loop_type")
                if loop_type and loop_type not in ["for_each", "while", "times"]:
                    errors.append(f"Invalid loop type: {loop_type}")

        elif subtype == FlowSubtype.SWITCH.value:
            errors.extend(self._validate_required_parameters(node, ["switch_cases"]))

        elif subtype == FlowSubtype.WAIT.value:
            errors.extend(self._validate_required_parameters(node, ["wait_type"]))
            if hasattr(node, "parameters"):
                wait_type = node.parameters.get("wait_type")
                if wait_type and wait_type not in ["time", "condition", "event"]:
                    errors.append(f"Invalid wait type: {wait_type}")

        return errors

    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute flow control node."""
        start_time = time.time()
        logs = []

        try:
            subtype = context.node.subtype
            logs.append(f"Executing flow node with subtype: {subtype}")

            if subtype == FlowSubtype.IF.value:
                return self._execute_if_condition(context, logs, start_time)
            elif subtype == FlowSubtype.FILTER.value:
                return self._execute_filter(context, logs, start_time)
            elif subtype == FlowSubtype.LOOP.value:
                return self._execute_loop(context, logs, start_time)
            elif subtype == FlowSubtype.FOR_EACH.value:
                return self._execute_loop(
                    context, logs, start_time
                )  # FOR_EACH uses same logic as LOOP
            elif subtype == FlowSubtype.WHILE.value:
                return self._execute_loop(
                    context, logs, start_time
                )  # WHILE uses same logic as LOOP
            elif subtype == FlowSubtype.MERGE.value:
                return self._execute_merge(context, logs, start_time)
            elif subtype == FlowSubtype.SWITCH.value:
                return self._execute_switch(context, logs, start_time)
            elif subtype == FlowSubtype.WAIT.value:
                return self._execute_wait(context, logs, start_time)
            elif subtype == FlowSubtype.DELAY.value:
                return self._execute_wait(
                    context, logs, start_time
                )  # DELAY uses same logic as WAIT
            elif subtype == FlowSubtype.SPLIT.value:
                return self._execute_split(context, logs, start_time)
            elif subtype == FlowSubtype.SORT.value:
                return self._execute_sort(context, logs, start_time)
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
        # Use spec-based parameter retrieval
        condition = self.get_parameter_with_spec(context, "condition")

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
        # Use spec-based parameter retrieval
        filter_condition = self.get_parameter_with_spec(context, "filter_condition")

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
        # Use spec-based parameter retrieval
        loop_type = self.get_parameter_with_spec(context, "loop_type")
        max_iterations = self.get_parameter_with_spec(context, "max_iterations")

        logs.append(f"Executing {loop_type} loop with max iterations: {max_iterations}")

        input_data = context.input_data

        if loop_type == "for_each":
            result = self._execute_for_each_loop(input_data, max_iterations)
        elif loop_type == "while":
            condition = self.get_parameter_with_spec(context, "while_condition")
            result = self._execute_while_loop(input_data, condition, max_iterations)
        elif loop_type == "times":
            times = self.get_parameter_with_spec(context, "times")
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
        # Use spec-based parameter retrieval
        merge_strategy = self.get_parameter_with_spec(context, "merge_strategy")

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
        # Use spec-based parameter retrieval
        switch_cases = self.get_parameter_with_spec(context, "switch_cases")
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
        # Use spec-based parameter retrieval
        wait_type = self.get_parameter_with_spec(context, "wait_type")

        logs.append(f"Executing wait with type: {wait_type}")

        if wait_type == "time":
            duration = self.get_parameter_with_spec(context, "duration")  # seconds
            logs.append(f"Waiting for {duration} seconds")
            # In real implementation, would actually wait
            wait_result = {"waited_seconds": duration}

        elif wait_type == "condition":
            condition = self.get_parameter_with_spec(context, "wait_condition")
            logs.append(f"Waiting for condition: {condition}")
            # In real implementation, would poll condition
            wait_result = {"condition": condition, "condition_met": True}

        elif wait_type == "event":
            event_name = self.get_parameter_with_spec(context, "event_name")
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

    def _execute_split(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute split operation."""
        # Use spec-based parameter retrieval
        split_key = self.get_parameter_with_spec(context, "split_key")
        split_type = self.get_parameter_with_spec(context, "split_type")

        logs.append(f"Splitting data by {split_key} using {split_type}")

        input_data = context.input_data

        # Split the data based on the key
        if split_type == "by_key" and isinstance(input_data, dict):
            split_result = {key: [value] for key, value in input_data.items()}
        elif split_type == "by_value" and isinstance(input_data, list):
            split_result = {str(i): item for i, item in enumerate(input_data)}
        else:
            split_result = {"all": input_data}

        output_data = {
            "flow_type": "split",
            "split_key": split_key,
            "split_type": split_type,
            "input_data": input_data,
            "split_result": split_result,
            "split_count": len(split_result),
            "split_at": datetime.now().isoformat(),
        }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_sort(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute sort operation."""
        # Use spec-based parameter retrieval
        sort_key = self.get_parameter_with_spec(context, "sort_key")
        sort_order = self.get_parameter_with_spec(context, "sort_order")

        logs.append(f"Sorting data by {sort_key} in {sort_order} order")

        input_data = context.input_data

        # Sort the data
        if isinstance(input_data, list):
            if sort_key and all(isinstance(item, dict) and sort_key in item for item in input_data):
                sorted_data = sorted(
                    input_data, key=lambda x: x[sort_key], reverse=(sort_order == "desc")
                )
            else:
                sorted_data = sorted(input_data, reverse=(sort_order == "desc"))
        else:
            sorted_data = input_data

        output_data = {
            "flow_type": "sort",
            "sort_key": sort_key,
            "sort_order": sort_order,
            "input_data": input_data,
            "sorted_data": sorted_data,
            "item_count": len(sorted_data) if isinstance(sorted_data, list) else 1,
            "sorted_at": datetime.now().isoformat(),
        }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )
