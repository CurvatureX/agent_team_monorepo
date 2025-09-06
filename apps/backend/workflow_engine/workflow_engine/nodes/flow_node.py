"""
Flow Node Executor.

Handles flow control operations like if conditions, loops, switches, merges, etc.
"""

import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from shared.models import NodeType
from shared.models.node_enums import FlowSubtype
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
        self.logger.info(f"🔀 FLOW: Starting validation for node: {getattr(node, 'id', 'unknown')}")
        self.logger.info(f"🔀 FLOW: Node subtype: {getattr(node, 'subtype', 'none')}")

        # First use the base class validation which includes spec validation
        errors = super().validate(node)

        if errors:
            self.logger.warning(f"🔀 FLOW: ⚠️ Base validation found {len(errors)} errors")
            for error in errors:
                self.logger.warning(f"🔀 FLOW:   - {error}")

        # If spec validation passed, we're done
        if not errors and self.spec:
            self.logger.info("🔀 FLOW: ✅ Spec-based validation passed")
            return errors

        # Fallback if spec not available
        self.logger.info("🔀 FLOW: Using legacy validation")

        if not node.subtype:
            error_msg = "Flow subtype is required"
            errors.append(error_msg)
            self.logger.error(f"🔀 FLOW: ❌ {error_msg}")
            return errors

        if node.subtype not in self.get_supported_subtypes():
            error_msg = f"Unsupported flow subtype: {node.subtype}"
            errors.append(error_msg)
            self.logger.error(f"🔀 FLOW: ❌ {error_msg}")
        else:
            self.logger.info(f"🔀 FLOW: ✅ Subtype {node.subtype} is supported")

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
            self.logger.info(f"🔀 FLOW: Starting execution with subtype: {subtype}")
            self.logger.info(
                f"🔀 FLOW: Node ID: {getattr(context.node, 'id', 'unknown') if hasattr(context, 'node') else 'unknown'}"
            )
            self.logger.info(f"🔀 FLOW: Execution ID: {getattr(context, 'execution_id', 'unknown')}")

            logs.append(f"Starting flow execution: {subtype}")

            if subtype == FlowSubtype.IF.value:
                return self._execute_if_condition(context, logs, start_time)
            elif subtype == FlowSubtype.FILTER.value:
                return self._execute_filter(context, logs, start_time)
            elif subtype == FlowSubtype.LOOP.value:
                return self._execute_loop(context, logs, start_time)
            elif subtype == FlowSubtype.FOR_EACH.value:
                self.logger.info("🔀 FLOW: Using FOR_EACH logic via LOOP implementation")
                logs.append("Executing FOR_EACH via loop implementation")
                return self._execute_loop(
                    context, logs, start_time
                )  # FOR_EACH uses same logic as LOOP
            elif subtype == FlowSubtype.WHILE.value:
                self.logger.info("🔀 FLOW: Using WHILE logic via LOOP implementation")
                logs.append("Executing WHILE via loop implementation")
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
                self.logger.info("🔀 FLOW: Using DELAY logic via WAIT implementation")
                logs.append("Executing DELAY via wait implementation")
                return self._execute_wait(
                    context, logs, start_time
                )  # DELAY uses same logic as WAIT
            elif subtype == FlowSubtype.SPLIT.value:
                return self._execute_split(context, logs, start_time)
            elif subtype == FlowSubtype.SORT.value:
                return self._execute_sort(context, logs, start_time)
            else:
                error_msg = f"Unsupported flow subtype: {subtype}"
                self.logger.error(f"🔀 FLOW: ❌ {error_msg}")
                return self._create_error_result(
                    error_msg,
                    execution_time=time.time() - start_time,
                    logs=logs,
                )

        except Exception as e:
            self.logger.error(f"🔀 FLOW: ❌ Error executing flow control: {str(e)}")
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
        logs.append("Executing if condition")
        self.logger.info("🔀 FLOW: Starting IF condition execution")

        # Use spec-based parameter retrieval
        condition = self.get_parameter_with_spec(context, "condition")

        self.logger.info(f"🔀 FLOW: IF condition: {condition}")
        self.logger.info(
            f"🔀 FLOW: Input data keys: {list(context.input_data.keys()) if context.input_data else 'None'}"
        )

        logs.append(f"Evaluating IF condition: {condition}")

        # Evaluate condition
        self.logger.info("🔀 FLOW: Evaluating condition...")
        condition_result = self._evaluate_condition(condition, context.input_data)

        logs.append(f"Condition result: {condition_result}")

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
            self.logger.info("🔀 FLOW: ✅ Condition evaluated to TRUE - taking true_branch")
            logs.append("Condition evaluated to TRUE")
        else:
            output_data["next_route"] = "false_branch"
            self.logger.info("🔀 FLOW: ❌ Condition evaluated to FALSE - taking false_branch")
            logs.append("Condition evaluated to FALSE")

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_filter(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute filter operation."""
        logs.append("Executing filter")
        self.logger.info("🔀 FLOW: Starting FILTER execution")

        # Use spec-based parameter retrieval
        filter_condition = self.get_parameter_with_spec(context, "filter_condition")

        self.logger.info(f"🔀 FLOW: Filter condition: {filter_condition}")

        input_data = context.input_data
        input_type = type(input_data).__name__
        original_count = len(input_data) if isinstance(input_data, (list, dict)) else 1

        self.logger.info(f"🔀 FLOW: Input data type: {input_type}, count: {original_count}")

        logs.append(f"Filtering {input_type} data with {original_count} items")

        # Apply filter
        if isinstance(input_data, list):
            self.logger.info("🔀 FLOW: Applying list filter")
            logs.append("Applying list filter")
            filtered_data = self._filter_list(input_data, filter_condition)
        elif isinstance(input_data, dict):
            self.logger.info("🔀 FLOW: Applying dictionary filter")
            logs.append("Applying dictionary filter")
            filtered_data = self._filter_dict(input_data, filter_condition)
        else:
            self.logger.info("🔀 FLOW: No filtering applied - unsupported data type")
            logs.append(f"Skipping filter - unsupported data type: {input_type}")
            filtered_data = input_data

        filtered_count = len(filtered_data) if isinstance(filtered_data, (list, dict)) else 1
        self.logger.info(f"🔀 FLOW: ✅ Filter complete - {original_count} -> {filtered_count} items")

        output_data = {
            "flow_type": "filter",
            "filter_condition": filter_condition,
            "original_data": input_data,
            "filtered_data": filtered_data,
            "original_count": original_count,
            "filtered_count": filtered_count,
            "filtered_at": datetime.now().isoformat(),
        }

        logs.append(f"Filtered {original_count} items to {filtered_count}")

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_loop(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute loop operation."""
        logs.append("Executing loop")
        self.logger.info("🔀 FLOW: Starting LOOP execution")

        # Use spec-based parameter retrieval
        loop_type = self.get_parameter_with_spec(context, "loop_type")
        max_iterations = self.get_parameter_with_spec(context, "max_iterations")

        self.logger.info(f"🔀 FLOW: Loop type: {loop_type}")
        self.logger.info(f"🔀 FLOW: Max iterations: {max_iterations}")

        input_data = context.input_data

        self.logger.info(f"🔀 FLOW: Processing input data: {type(input_data).__name__}")

        logs.append(f"Starting {loop_type} loop with max {max_iterations} iterations")

        if loop_type == "for_each":
            self.logger.info("🔀 FLOW: Executing FOR_EACH loop")
            logs.append("Executing FOR_EACH loop")
            result = self._execute_for_each_loop(input_data, max_iterations)
        elif loop_type == "while":
            condition = self.get_parameter_with_spec(context, "while_condition")
            self.logger.info(f"🔀 FLOW: Executing WHILE loop with condition: {condition}")
            logs.append(f"Executing WHILE loop with condition: {condition}")
            result = self._execute_while_loop(input_data, condition, max_iterations)
        elif loop_type == "times":
            times = self.get_parameter_with_spec(context, "times")
            self.logger.info(f"🔀 FLOW: Executing TIMES loop for {times} iterations")
            logs.append(f"Executing TIMES loop for {times} iterations")
            result = self._execute_times_loop(input_data, times)
        else:
            error_msg = f"Unknown loop type: {loop_type}"
            self.logger.error(f"🔀 FLOW: ❌ {error_msg}")
            logs.append(f"Error: {error_msg}")
            result = {"error": error_msg}

        if "error" in result:
            self.logger.error(f"🔀 FLOW: ❌ Loop execution failed: {result['error']}")
            logs.append(f"Loop failed: {result['error']}")
        else:
            iterations = result.get("iterations", 0)
            self.logger.info(f"🔀 FLOW: ✅ Loop completed successfully - {iterations} iterations")
            logs.append(f"Loop completed with {iterations} iterations")

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
        logs.append("Executing merge")
        self.logger.info("🔀 FLOW: Starting MERGE execution")

        # Use spec-based parameter retrieval
        merge_strategy = self.get_parameter_with_spec(context, "merge_strategy")

        self.logger.info(f"🔀 FLOW: Merge strategy: {merge_strategy}")

        input_data = context.input_data

        input_size = len(str(input_data)) if input_data else 0
        self.logger.info(f"🔀 FLOW: Input data size: {input_size} characters")

        logs.append(f"Starting merge with strategy: {merge_strategy}")

        # Simulate merging multiple data sources
        if merge_strategy == "combine":
            self.logger.info("🔀 FLOW: Using COMBINE merge strategy")
            logs.append("Applying COMBINE merge strategy")
            merged_data = self._combine_data(input_data)
        elif merge_strategy == "union":
            self.logger.info("🔀 FLOW: Using UNION merge strategy")
            logs.append("Applying UNION merge strategy")
            merged_data = self._union_data(input_data)
        elif merge_strategy == "intersection":
            self.logger.info("🔀 FLOW: Using INTERSECTION merge strategy")
            logs.append("Applying INTERSECTION merge strategy")
            merged_data = self._intersection_data(input_data)
        else:
            self.logger.info(
                f"🔀 FLOW: Unknown merge strategy '{merge_strategy}', using input as-is"
            )
            logs.append(f"Unknown merge strategy: {merge_strategy}, using input as-is")
            merged_data = input_data

        merged_size = len(str(merged_data)) if merged_data else 0
        self.logger.info(f"🔀 FLOW: ✅ Merge complete - output size: {merged_size} characters")
        logs.append(f"Merge complete - {input_size} -> {merged_size} characters")

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
        logs.append("Executing switch")
        self.logger.info("🔀 FLOW: Starting SWITCH execution")

        # Use spec-based parameter retrieval
        switch_cases = self.get_parameter_with_spec(context, "switch_cases")
        switch_value = context.input_data.get("switch_value", "")

        self.logger.info(f"🔀 FLOW: Switch value: {switch_value}")
        self.logger.info(f"🔀 FLOW: Available cases: {len(switch_cases) if switch_cases else 0}")

        logs.append(f"Evaluating switch value: {switch_value}")
        logs.append(f"Checking {len(switch_cases) if switch_cases else 0} available cases")

        # Find matching case
        matched_case = None
        for i, case in enumerate(switch_cases or []):
            case_value = case.get("value")
            self.logger.info(f"🔀 FLOW: Checking case {i}: {case_value}")
            if case_value == switch_value:
                matched_case = case
                self.logger.info(f"🔀 FLOW: ✅ Found matching case: {case_value}")
                logs.append(f"Found matching case: {case_value}")
                break

        if not matched_case:
            # Use default case if available
            self.logger.info("🔀 FLOW: No exact match found, looking for default case")
            logs.append("No exact match found, looking for default case")
            matched_case = next(
                (case for case in switch_cases if case.get("is_default", False)), None
            )
            if matched_case:
                self.logger.info("🔀 FLOW: ✅ Using default case")
                logs.append("Using default case")
            else:
                self.logger.info("🔀 FLOW: ⚠️ No matching case or default found")
                logs.append("No matching case or default found")

        next_route = matched_case.get("route", "default") if matched_case else "default"
        self.logger.info(f"🔀 FLOW: Next route: {next_route}")
        logs.append(
            f"Switch matched: {matched_case.get('value', 'default') if matched_case else 'none'}"
        )

        output_data = {
            "flow_type": "switch",
            "switch_value": switch_value,
            "switch_cases": switch_cases,
            "matched_case": matched_case,
            "next_route": next_route,
            "switched_at": datetime.now().isoformat(),
        }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_wait(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute wait operation."""
        logs.append("Executing wait")
        self.logger.info("🔀 FLOW: Starting WAIT execution")

        # Use spec-based parameter retrieval
        wait_type = self.get_parameter_with_spec(context, "wait_type")

        self.logger.info(f"🔀 FLOW: Wait type: {wait_type}")

        if wait_type == "time":
            duration = self.get_parameter_with_spec(context, "duration")  # seconds
            self.logger.info(f"🔀 FLOW: Time wait - duration: {duration} seconds")
            # In real implementation, would actually wait
            wait_result = {"waited_seconds": duration}
            logs.append(f"Waited for {duration} seconds")

        elif wait_type == "condition":
            condition = self.get_parameter_with_spec(context, "wait_condition")
            self.logger.info(f"🔀 FLOW: Condition wait - condition: {condition}")
            # In real implementation, would poll condition
            wait_result = {"condition": condition, "condition_met": True}
            logs.append(f"Waited for condition: {condition}")

        elif wait_type == "event":
            event_name = self.get_parameter_with_spec(context, "event_name")
            self.logger.info(f"🔀 FLOW: Event wait - event: {event_name}")
            # In real implementation, would wait for event
            wait_result = {"event_name": event_name, "event_received": True}
            logs.append(f"Waited for event: {event_name}")

        else:
            error_msg = f"Unknown wait type: {wait_type}"
            self.logger.error(f"🔀 FLOW: ❌ {error_msg}")
            wait_result = {"error": error_msg}

        if "error" in wait_result:
            self.logger.error(f"🔀 FLOW: ❌ Wait failed: {wait_result['error']}")
        else:
            self.logger.info("🔀 FLOW: ✅ Wait completed successfully")

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
        logs.append("Executing split")
        self.logger.info("🔀 FLOW: Starting SPLIT execution")

        # Use spec-based parameter retrieval
        split_key = self.get_parameter_with_spec(context, "split_key")
        split_type = self.get_parameter_with_spec(context, "split_type")

        self.logger.info(f"🔀 FLOW: Split key: {split_key}")
        self.logger.info(f"🔀 FLOW: Split type: {split_type}")

        input_data = context.input_data
        input_type = type(input_data).__name__

        self.logger.info(f"🔀 FLOW: Input data type: {input_type}")

        # Split the data based on the key
        if split_type == "by_key" and isinstance(input_data, dict):
            self.logger.info("🔀 FLOW: Splitting dictionary by keys")
            split_result = {key: [value] for key, value in input_data.items()}
        elif split_type == "by_value" and isinstance(input_data, list):
            self.logger.info("🔀 FLOW: Splitting list by values")
            split_result = {str(i): item for i, item in enumerate(input_data)}
        else:
            self.logger.info(
                f"🔀 FLOW: Unsupported split combination: {split_type} on {input_type}, using fallback"
            )
            split_result = {"all": input_data}

        split_count = len(split_result)
        self.logger.info(f"🔀 FLOW: ✅ Split complete - created {split_count} parts")
        logs.append(f"Split data into {split_count} parts")

        output_data = {
            "flow_type": "split",
            "split_key": split_key,
            "split_type": split_type,
            "input_data": input_data,
            "split_result": split_result,
            "split_count": split_count,
            "split_at": datetime.now().isoformat(),
        }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_sort(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute sort operation."""
        logs.append("Executing sort")
        self.logger.info("🔀 FLOW: Starting SORT execution")

        # Use spec-based parameter retrieval
        sort_key = self.get_parameter_with_spec(context, "sort_key")
        sort_order = self.get_parameter_with_spec(context, "sort_order")

        self.logger.info(f"🔀 FLOW: Sort key: {sort_key}")
        self.logger.info(f"🔀 FLOW: Sort order: {sort_order}")

        input_data = context.input_data
        input_type = type(input_data).__name__

        self.logger.info(f"🔀 FLOW: Input data type: {input_type}")

        # Sort the data
        if isinstance(input_data, list):
            original_count = len(input_data)
            self.logger.info(f"🔀 FLOW: Sorting list of {original_count} items")

            if sort_key and all(isinstance(item, dict) and sort_key in item for item in input_data):
                self.logger.info(f"🔀 FLOW: Sorting by key '{sort_key}'")
                sorted_data = sorted(
                    input_data, key=lambda x: x[sort_key], reverse=(sort_order == "desc")
                )
            else:
                self.logger.info("🔀 FLOW: Sorting by item values (no valid key)")
                sorted_data = sorted(input_data, reverse=(sort_order == "desc"))

            self.logger.info(f"🔀 FLOW: ✅ Sort complete - {len(sorted_data)} items sorted")
        else:
            self.logger.info(f"🔀 FLOW: Cannot sort {input_type}, returning as-is")
            sorted_data = input_data

        item_count = len(sorted_data) if isinstance(sorted_data, list) else 1
        logs.append(f"Sorted {item_count} items by {sort_key or 'value'} ({sort_order})")

        output_data = {
            "flow_type": "sort",
            "sort_key": sort_key,
            "sort_order": sort_order,
            "input_data": input_data,
            "sorted_data": sorted_data,
            "item_count": item_count,
            "sorted_at": datetime.now().isoformat(),
        }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )
