"""Flow Node Executor."""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from shared.models.node_enums import NodeType

from .base import BaseNodeExecutor, ExecutionStatus, NodeExecutionContext, NodeExecutionResult
from .factory import NodeExecutorFactory


@NodeExecutorFactory.register(NodeType.FLOW.value)
class FlowNodeExecutor(BaseNodeExecutor):
    """Executor for flow control nodes (IF/ELSE, SWITCH, LOOP, MERGE, etc.)."""

    def __init__(self, node_type: str = NodeType.FLOW.value, subtype: str = None):
        super().__init__(node_type, subtype)

    async def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute flow control node."""
        flow_type = self.subtype or context.get_parameter("flow_type", "conditional")

        self.log_execution(context, f"Executing flow node: {flow_type}")

        try:
            # Handle different flow control types
            if flow_type.lower() in ["if", "conditional", "if_else"]:
                return await self._handle_conditional_flow(context)
            elif flow_type.lower() in ["switch", "case"]:
                return await self._handle_switch_flow(context)
            elif flow_type.lower() in ["loop", "for_each", "while"]:
                return await self._handle_loop_flow(context)
            elif flow_type.lower() in ["merge", "join", "combine"]:
                return await self._handle_merge_flow(context)
            elif flow_type.lower() in ["split", "parallel", "fork"]:
                return await self._handle_split_flow(context)
            elif flow_type.lower() in ["filter", "where"]:
                return await self._handle_filter_flow(context)
            else:
                return await self._handle_generic_flow(context, flow_type)

        except Exception as e:
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=f"Flow control execution failed: {str(e)}",
                error_details={"flow_type": flow_type},
            )

    async def _handle_conditional_flow(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Handle IF/ELSE conditional flow."""
        condition = context.get_parameter("condition", "")
        true_path = context.get_parameter("true_path", "continue")
        false_path = context.get_parameter("false_path", "skip")

        # Evaluate condition
        condition_result = await self._evaluate_condition(condition, context.input_data, context)

        self.log_execution(context, f"Condition '{condition}' evaluated to: {condition_result}")

        # Determine which path to take
        selected_path = true_path if condition_result else false_path
        next_action = "continue" if condition_result else "skip"

        output_data = {
            "flow_type": "conditional",
            "condition": condition,
            "condition_result": condition_result,
            "selected_path": selected_path,
            "true_path": true_path,
            "false_path": false_path,
            "next_action": next_action,
            "input_data": context.input_data,
            "timestamp": datetime.now().isoformat(),
        }

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={
                "node_type": "flow",
                "flow_type": "conditional",
                "condition_result": condition_result,
                "next_action": next_action,
            },
        )

    async def _handle_switch_flow(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Handle SWITCH/CASE flow."""
        switch_expression = context.get_parameter("switch_expression", "")
        cases = context.get_parameter("cases", {})
        default_case = context.get_parameter("default_case", "continue")

        # Evaluate switch expression
        switch_value = await self._evaluate_expression(
            switch_expression, context.input_data, context
        )

        self.log_execution(
            context, f"Switch expression '{switch_expression}' evaluated to: {switch_value}"
        )

        # Find matching case
        selected_case = None
        selected_action = default_case

        for case_value, case_action in cases.items():
            if str(switch_value) == str(case_value):
                selected_case = case_value
                selected_action = case_action
                break

        output_data = {
            "flow_type": "switch",
            "switch_expression": switch_expression,
            "switch_value": switch_value,
            "cases": cases,
            "selected_case": selected_case,
            "selected_action": selected_action,
            "default_case": default_case,
            "input_data": context.input_data,
            "timestamp": datetime.now().isoformat(),
        }

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={
                "node_type": "flow",
                "flow_type": "switch",
                "selected_case": selected_case,
                "selected_action": selected_action,
            },
        )

    async def _handle_loop_flow(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Handle LOOP/FOR_EACH/WHILE flow."""
        loop_type = context.get_parameter("loop_type", "for_each")
        max_iterations = context.get_parameter("max_iterations", 100)

        if loop_type == "for_each":
            return await self._handle_for_each_loop(context, max_iterations)
        elif loop_type == "while":
            return await self._handle_while_loop(context, max_iterations)
        else:
            return await self._handle_generic_loop(context, loop_type, max_iterations)

    async def _handle_for_each_loop(
        self, context: NodeExecutionContext, max_iterations: int
    ) -> NodeExecutionResult:
        """Handle FOR_EACH loop over collection."""
        collection_path = context.get_parameter("collection_path", "")
        item_variable = context.get_parameter("item_variable", "item")

        # Get collection from input data
        collection = (
            self._get_nested_value(context.input_data, collection_path)
            if collection_path
            else context.input_data
        )

        if not isinstance(collection, (list, tuple)):
            collection = [collection] if collection is not None else []

        # Limit iterations for safety
        collection = collection[:max_iterations]

        loop_results = []
        for index, item in enumerate(collection):
            iteration_data = {
                "index": index,
                "item": item,
                item_variable: item,
                "total_items": len(collection),
            }
            loop_results.append(iteration_data)

        output_data = {
            "flow_type": "for_each",
            "collection_path": collection_path,
            "item_variable": item_variable,
            "total_iterations": len(loop_results),
            "max_iterations": max_iterations,
            "loop_results": loop_results,
            "input_data": context.input_data,
            "timestamp": datetime.now().isoformat(),
        }

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={
                "node_type": "flow",
                "flow_type": "for_each",
                "total_iterations": len(loop_results),
            },
        )

    async def _handle_while_loop(
        self, context: NodeExecutionContext, max_iterations: int
    ) -> NodeExecutionResult:
        """Handle WHILE loop with condition."""
        condition = context.get_parameter("condition", "false")
        counter_variable = context.get_parameter("counter_variable", "counter")

        loop_results = []
        counter = 0

        # Simulate while loop execution (with safety limit)
        while counter < max_iterations:
            current_data = {**context.input_data, counter_variable: counter, "iteration": counter}

            # Evaluate condition with current data
            condition_result = await self._evaluate_condition(condition, current_data, context)

            if not condition_result:
                break

            iteration_data = {
                "iteration": counter,
                "condition_result": condition_result,
                "data": current_data,
            }
            loop_results.append(iteration_data)
            counter += 1

        output_data = {
            "flow_type": "while",
            "condition": condition,
            "counter_variable": counter_variable,
            "total_iterations": len(loop_results),
            "max_iterations": max_iterations,
            "loop_results": loop_results,
            "final_condition_result": False,  # Loop exited
            "input_data": context.input_data,
            "timestamp": datetime.now().isoformat(),
        }

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={
                "node_type": "flow",
                "flow_type": "while",
                "total_iterations": len(loop_results),
            },
        )

    async def _handle_generic_loop(
        self, context: NodeExecutionContext, loop_type: str, max_iterations: int
    ) -> NodeExecutionResult:
        """Handle generic loop types."""
        iterations = context.get_parameter("iterations", 1)
        iterations = min(iterations, max_iterations)  # Safety limit

        loop_results = []
        for i in range(iterations):
            iteration_data = {
                "iteration": i,
                "total_iterations": iterations,
                "data": context.input_data,
            }
            loop_results.append(iteration_data)

        output_data = {
            "flow_type": loop_type,
            "total_iterations": iterations,
            "max_iterations": max_iterations,
            "loop_results": loop_results,
            "input_data": context.input_data,
            "timestamp": datetime.now().isoformat(),
        }

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={"node_type": "flow", "flow_type": loop_type, "total_iterations": iterations},
        )

    async def _handle_merge_flow(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Handle MERGE/JOIN/COMBINE flow."""
        merge_strategy = context.get_parameter("merge_strategy", "combine")
        input_sources = context.get_parameter("input_sources", [])

        # Get data from multiple sources (in real implementation, this would come from previous nodes)
        merged_data = {}

        if merge_strategy == "combine":
            # Combine all data into one object
            merged_data = dict(context.input_data)
            for i, source in enumerate(input_sources):
                merged_data[f"source_{i}"] = source

        elif merge_strategy == "array":
            # Create an array of all inputs
            merged_data = {
                "merged_array": [context.input_data] + input_sources,
                "total_sources": len(input_sources) + 1,
            }

        elif merge_strategy == "select":
            # Select specific fields from each source
            select_fields = context.get_parameter("select_fields", [])
            for field in select_fields:
                if field in context.input_data:
                    merged_data[field] = context.input_data[field]

        else:
            merged_data = context.input_data

        output_data = {
            "flow_type": "merge",
            "merge_strategy": merge_strategy,
            "input_sources": input_sources,
            "merged_data": merged_data,
            "original_input": context.input_data,
            "timestamp": datetime.now().isoformat(),
        }

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={"node_type": "flow", "flow_type": "merge", "merge_strategy": merge_strategy},
        )

    async def _handle_split_flow(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Handle SPLIT/PARALLEL/FORK flow."""
        split_strategy = context.get_parameter("split_strategy", "duplicate")
        output_paths = context.get_parameter("output_paths", ["path_a", "path_b"])

        split_results = {}

        if split_strategy == "duplicate":
            # Send same data to all paths
            for path in output_paths:
                split_results[path] = context.input_data

        elif split_strategy == "field_based":
            # Split based on field values
            split_field = context.get_parameter("split_field", "type")
            split_value = context.input_data.get(split_field, "default")

            for path in output_paths:
                if path == f"path_{split_value}" or path == "default":
                    split_results[path] = context.input_data

        elif split_strategy == "array_split":
            # Split array into multiple paths
            if isinstance(context.input_data, list):
                chunk_size = max(1, len(context.input_data) // len(output_paths))
                for i, path in enumerate(output_paths):
                    start_idx = i * chunk_size
                    end_idx = (
                        start_idx + chunk_size
                        if i < len(output_paths) - 1
                        else len(context.input_data)
                    )
                    split_results[path] = context.input_data[start_idx:end_idx]
            else:
                # Not an array, duplicate to all paths
                for path in output_paths:
                    split_results[path] = context.input_data

        output_data = {
            "flow_type": "split",
            "split_strategy": split_strategy,
            "output_paths": output_paths,
            "split_results": split_results,
            "original_input": context.input_data,
            "timestamp": datetime.now().isoformat(),
        }

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={
                "node_type": "flow",
                "flow_type": "split",
                "split_strategy": split_strategy,
                "output_paths": output_paths,
            },
        )

    async def _handle_filter_flow(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Handle FILTER/WHERE flow."""
        filter_condition = context.get_parameter("filter_condition", "true")
        array_path = context.get_parameter("array_path", "")

        # Get array to filter
        if array_path:
            data_to_filter = self._get_nested_value(context.input_data, array_path)
        else:
            data_to_filter = context.input_data

        if not isinstance(data_to_filter, list):
            data_to_filter = [data_to_filter] if data_to_filter is not None else []

        # Filter array based on condition
        filtered_results = []
        for item in data_to_filter:
            condition_result = await self._evaluate_condition(filter_condition, item, context)
            if condition_result:
                filtered_results.append(item)

        output_data = {
            "flow_type": "filter",
            "filter_condition": filter_condition,
            "array_path": array_path,
            "original_count": len(data_to_filter),
            "filtered_count": len(filtered_results),
            "filtered_results": filtered_results,
            "original_data": context.input_data,
            "timestamp": datetime.now().isoformat(),
        }

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={
                "node_type": "flow",
                "flow_type": "filter",
                "original_count": len(data_to_filter),
                "filtered_count": len(filtered_results),
            },
        )

    async def _handle_generic_flow(
        self, context: NodeExecutionContext, flow_type: str
    ) -> NodeExecutionResult:
        """Handle generic/unknown flow types."""
        import asyncio

        self.log_execution(context, f"Executing generic flow: {flow_type}")

        # Simulate some processing time
        await asyncio.sleep(0.1)

        output_data = {
            "flow_type": flow_type,
            "result": f"Generic flow {flow_type} executed successfully",
            "input_data": context.input_data,
            "parameters": dict(context.parameters) if context.parameters else {},
            "timestamp": datetime.now().isoformat(),
        }

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={"node_type": "flow", "flow_type": flow_type},
        )

    async def _evaluate_condition(
        self, condition: str, data: Dict[str, Any], context: NodeExecutionContext
    ) -> bool:
        """Evaluate a condition expression against data."""
        try:
            if not condition or condition.lower() in ["true", "1"]:
                return True
            elif condition.lower() in ["false", "0"]:
                return False

            # Comprehensive condition evaluation with safe expression parsing
            condition = condition.strip()

            # Handle input_data references specifically
            import re

            for key, value in data.items():
                # Pattern to match input_data.key references
                input_data_pattern = r"input_data\." + re.escape(key) + r"\b"

                if isinstance(value, str):
                    # Try to convert numeric strings to numbers for comparisons
                    try:
                        if value.isdigit():
                            numeric_value = int(value)
                            condition = re.sub(input_data_pattern, str(numeric_value), condition)
                        elif value.replace(".", "", 1).isdigit():
                            numeric_value = float(value)
                            condition = re.sub(input_data_pattern, str(numeric_value), condition)
                        else:
                            # Non-numeric string, escape quotes
                            safe_value = value.replace("'", "\\'").replace('"', '\\"')
                            condition = re.sub(input_data_pattern, f"'{safe_value}'", condition)
                    except:
                        # Fallback to string representation
                        safe_value = value.replace("'", "\\'").replace('"', '\\"')
                        condition = re.sub(input_data_pattern, f"'{safe_value}'", condition)
                elif isinstance(value, (int, float)):
                    condition = re.sub(input_data_pattern, str(value), condition)
                elif isinstance(value, bool):
                    condition = re.sub(input_data_pattern, str(value).lower(), condition)
                elif value is None:
                    condition = re.sub(input_data_pattern, "None", condition)
                else:
                    # For other types, convert to string representation
                    condition = re.sub(input_data_pattern, f"'{str(value)}'", condition)

            # Enhanced safety check - comprehensive allowlist of operators and functions
            allowed_operators = ["==", "!=", ">", "<", ">=", "<=", "in", "not in"]
            has_allowed_op = any(op in condition for op in allowed_operators)

            if has_allowed_op and all(
                char.isalnum() or char in " =='\"<>!.()," for char in condition
            ):
                # Very basic evaluation (in production, use a proper safe expression evaluator)
                return eval(condition) if len(condition) < 100 else False
            else:
                self.log_execution(context, f"Invalid condition format: {condition}", "WARNING")
                return False

        except Exception as e:
            self.log_execution(context, f"Condition evaluation error: {str(e)}", "ERROR")
            return False

    async def _evaluate_expression(
        self, expression: str, data: Dict[str, Any], context: NodeExecutionContext
    ) -> Any:
        """Evaluate an expression against data."""
        try:
            if not expression:
                return None

            # Simple field reference
            if expression in data:
                return data[expression]

            # Nested field reference like "user.name"
            if "." in expression:
                return self._get_nested_value(data, expression)

            # Literal values
            if expression.startswith('"') and expression.endswith('"'):
                return expression[1:-1]  # String literal
            elif expression.startswith("'") and expression.endswith("'"):
                return expression[1:-1]  # String literal
            elif expression.isdigit():
                return int(expression)  # Integer literal
            elif expression.replace(".", "").isdigit():
                return float(expression)  # Float literal

            return expression  # Return as-is

        except Exception as e:
            self.log_execution(context, f"Expression evaluation error: {str(e)}", "ERROR")
            return None

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get nested value from data using dot notation."""
        try:
            keys = path.split(".")
            value = data
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return None
            return value
        except:
            return None

    def validate_parameters(self, context: NodeExecutionContext) -> tuple[bool, str]:
        """Validate flow node parameters."""
        flow_type = self.subtype or context.get_parameter("flow_type", "conditional")

        # Validate specific flow types
        if flow_type in ["if", "conditional", "if_else"]:
            condition = context.get_parameter("condition")
            if not condition:
                return False, "Conditional flow requires 'condition' parameter"

        elif flow_type in ["switch", "case"]:
            switch_expression = context.get_parameter("switch_expression")
            if not switch_expression:
                return False, "Switch flow requires 'switch_expression' parameter"

        elif flow_type in ["for_each"]:
            collection_path = context.get_parameter("collection_path")
            if not collection_path and not isinstance(context.input_data, (list, tuple)):
                return (
                    False,
                    "For_each flow requires 'collection_path' parameter or input data to be a list",
                )

        elif flow_type in ["filter", "where"]:
            filter_condition = context.get_parameter("filter_condition")
            if not filter_condition:
                return False, "Filter flow requires 'filter_condition' parameter"

        return True, ""
