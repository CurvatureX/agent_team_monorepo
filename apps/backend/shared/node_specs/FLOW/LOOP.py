"""
LOOP Flow Control Node Specification

Flow control node for iterative processing and loops in workflows.
Executes contained nodes repeatedly based on loop conditions and iteration logic.
"""

from typing import Any, Dict, List

from ...models.node_enums import FlowSubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec


class LoopFlowSpec(BaseNodeSpec):
    """LOOP flow control specification for iterative workflow processing."""

    def __init__(self):
        super().__init__(
            type=NodeType.FLOW,
            subtype=FlowSubtype.LOOP,
            name="Loop_Iterator",
            description="Iterative flow control for repeated execution with loop conditions",
            # Configuration parameters
            configurations={
                "loop_type": {
                    "type": "string",
                    "default": "for_range",
                    "description": "循环类型",
                    "required": True,
                    "options": ["for_range", "for_each", "while"],
                },
                "loop_condition": {
                    "type": "string",
                    "default": "",
                    "description": "循环条件表达式",
                    "required": False,
                    "multiline": True,
                },
                "start_value": {
                    "type": "integer",
                    "default": 0,
                    "description": "起始值 (for_range)",
                    "required": False,
                },
                "end_value": {
                    "type": "integer",
                    "default": 10,
                    "description": "结束值 (for_range)",
                    "required": False,
                },
                "max_iterations": {
                    "type": "integer",
                    "default": 100,
                    "min": 1,
                    "max": 10000,
                    "description": "最大迭代次数",
                    "required": False,
                },
                "iteration_variable": {
                    "type": "string",
                    "default": "index",
                    "description": "迭代变量名",
                    "required": False,
                },
                "array_path": {
                    "type": "string",
                    "default": "",
                    "description": "数组路径 (for_each)",
                    "required": False,
                },
                "break_on_error": {
                    "type": "boolean",
                    "default": True,
                    "description": "遇到错误时是否中断循环",
                    "required": False,
                },
                "collect_results": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否收集所有迭代结果",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Parameter schemas (preferred over legacy defaults)
            input_params={
                "data": {
                    "type": "object",
                    "default": {},
                    "description": "Primary input data for loop body",
                    "required": True,
                },
                "context": {
                    "type": "object",
                    "default": {},
                    "description": "Optional context variables",
                    "required": False,
                },
                "loop_data": {
                    "type": "array",
                    "default": [],
                    "description": "Array to iterate over (for_each mode)",
                    "required": False,
                },
            },
            output_params={
                "final_result": {
                    "type": "object",
                    "default": {},
                    "description": "Aggregated result after loop completion",
                    "required": False,
                },
                "iteration_results": {
                    "type": "array",
                    "default": [],
                    "description": "Per-iteration outputs collected when enabled",
                    "required": False,
                },
                "successful_iterations": {
                    "type": "integer",
                    "default": 0,
                    "description": "Number of successful iterations",
                    "required": False,
                },
                "failed_iterations": {
                    "type": "integer",
                    "default": 0,
                    "description": "Number of iterations that failed",
                    "required": False,
                },
            },
            # Port definitions - Loop nodes have special iteration control ports
            input_ports=[
                {
                    "id": "main",
                    "name": "main",
                    "data_type": "dict",
                    "description": "Input data for loop processing",
                    "required": True,
                    "max_connections": 1,
                }
            ],
            output_ports=[
                {
                    "id": "iteration",
                    "name": "iteration",
                    "data_type": "dict",
                    "description": "Output for each iteration of the loop",
                    "required": False,
                    "max_connections": -1,
                },
                {
                    "id": "completed",
                    "name": "completed",
                    "data_type": "dict",
                    "description": "Output when loop completes normally",
                    "required": False,
                    "max_connections": -1,
                },
            ],
            # Examples
            examples=[
                {
                    "name": "Range Loop",
                    "description": "Simple for loop with range iteration",
                    "configurations": {
                        "loop_type": "for_range",
                        "start_value": 1,
                        "end_value": 5,
                        "iteration_variable": "counter",
                    },
                    "input_example": {"data": {"base_message": "Processing item"}},
                    "expected_outputs": {
                        "completed": {
                            "final_result": {"base_message": "Processing item", "counter": 5},
                            "iteration_results": [
                                {"counter": 1, "message": "Processing item 1"},
                                {"counter": 2, "message": "Processing item 2"},
                                {"counter": 3, "message": "Processing item 3"},
                                {"counter": 4, "message": "Processing item 4"},
                                {"counter": 5, "message": "Processing item 5"},
                            ],
                            "successful_iterations": 5,
                            "failed_iterations": 0,
                        }
                    },
                },
                {
                    "name": "Array Iteration",
                    "description": "For-each loop over array elements",
                    "configurations": {
                        "loop_type": "for_each",
                        "array_path": "data.users",
                        "iteration_variable": "user",
                        "collect_results": True,
                    },
                    "input_example": {
                        "data": {
                            "users": [
                                {"id": 1, "name": "Alice", "status": "active"},
                                {"id": 2, "name": "Bob", "status": "inactive"},
                                {"id": 3, "name": "Charlie", "status": "active"},
                            ]
                        }
                    },
                    "expected_outputs": {
                        "completed": {
                            "final_result": {"processed_count": 3},
                            "iteration_results": [
                                {
                                    "user": {"id": 1, "name": "Alice", "status": "active"},
                                    "processed": True,
                                },
                                {
                                    "user": {"id": 2, "name": "Bob", "status": "inactive"},
                                    "processed": True,
                                },
                                {
                                    "user": {"id": 3, "name": "Charlie", "status": "active"},
                                    "processed": True,
                                },
                            ],
                            "successful_iterations": 3,
                            "failed_iterations": 0,
                        }
                    },
                },
                {
                    "name": "While Condition Loop",
                    "description": "While loop with dynamic condition",
                    "configurations": {
                        "loop_type": "while",
                        "loop_condition": "data.retry_count < 3 && !data.success",
                        "max_iterations": 5,
                        "iteration_variable": "attempt",
                    },
                    "input_example": {
                        "data": {"retry_count": 0, "success": False, "task": "api_call"}
                    },
                    "expected_outputs": {
                        "completed": {
                            "final_result": {
                                "retry_count": 3,
                                "success": False,
                                "task": "api_call",
                                "attempt": 3,
                            },
                            "iteration_results": [
                                {"attempt": 1, "retry_count": 1, "success": False},
                                {"attempt": 2, "retry_count": 2, "success": False},
                                {"attempt": 3, "retry_count": 3, "success": False},
                            ],
                            "successful_iterations": 3,
                            "failed_iterations": 0,
                        }
                    },
                },
            ],
        )


# Export the specification instance
LOOP_FLOW_SPEC = LoopFlowSpec()
