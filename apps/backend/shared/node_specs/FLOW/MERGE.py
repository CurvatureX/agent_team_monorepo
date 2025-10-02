"""
MERGE Flow Node Specification

Merge node for combining multiple data streams into a single output stream.
Supports two strategies: concatenation and union (with optional de-duplication).
"""

from typing import Any, Dict, List

from ...models.node_enums import FlowSubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec


class MergeFlowSpec(BaseNodeSpec):
    """Merge flow node specification for data stream combination."""

    def __init__(self):
        super().__init__(
            type=NodeType.FLOW,
            subtype=FlowSubtype.MERGE,
            name="Merge",
            description="Combine multiple data streams into a single output using various merge strategies",
            # Configuration parameters
            configurations={
                "merge_strategy": {
                    "type": "string",
                    "default": "concatenate",
                    "description": "数据合并策略",
                    "required": True,
                    "options": [
                        "concatenate",
                        "union",
                    ],
                },
                "merge_key": {
                    "type": "string",
                    "default": "",
                    "description": "合并时使用的键字段",
                    "required": False,
                },
                "timeout_seconds": {
                    "type": "integer",
                    "default": 300,
                    "min": 1,
                    "max": 3600,
                    "description": "等待超时时间（秒）",
                    "required": False,
                },
                "handle_duplicates": {
                    "type": "string",
                    "default": "keep_all",
                    "description": "重复数据处理方式",
                    "required": False,
                    "options": ["keep_all", "keep_first", "keep_last", "remove_duplicates"],
                },
                # Output format is always array for simplified strategies
                **COMMON_CONFIGS,
            },
            # Parameter schemas (preferred over legacy defaults)
            input_params={
                "data": {
                    "type": "array",
                    "default": [],
                    "description": "List of input streams to merge",
                    "required": True,
                },
                "metadata": {
                    "type": "object",
                    "default": {},
                    "description": "Optional metadata for merge operation",
                    "required": False,
                },
                "timestamps": {
                    "type": "array",
                    "default": [],
                    "description": "Optional timestamps for inputs to assist merge",
                    "required": False,
                },
            },
            output_params={
                "merged_data": {
                    "type": "array",
                    "default": [],
                    "description": "Merged output according to selected strategy",
                    "required": False,
                },
                "merge_stats": {
                    "type": "object",
                    "default": {
                        "total_inputs": 0,
                        "items_merged": 0,
                        "duplicates_removed": 0,
                        "merge_time_ms": 0,
                    },
                    "description": "Merge statistics and timing",
                    "required": False,
                },
                "source_mapping": {
                    "type": "array",
                    "default": [],
                    "description": "Mapping of merged segments to source inputs",
                    "required": False,
                },
            },  # Examples
            examples=[
                {
                    "name": "Array Concatenation",
                    "description": "Merge multiple arrays into a single combined array",
                    "configurations": {
                        "merge_strategy": "concatenate",
                        "wait_for_all": True,
                        "handle_duplicates": "keep_all",
                    },
                    "input_example": {
                        "input_1": [1, 2, 3],
                        "input_2": [4, 5, 6],
                        "input_3": [7, 8, 9],
                    },
                    "expected_outputs": {
                        "result": {
                            "merged_data": [1, 2, 3, 4, 5, 6, 7, 8, 9],
                            "merge_stats": {
                                "total_inputs": 3,
                                "items_merged": 9,
                                "duplicates_removed": 0,
                                "merge_time_ms": 5,
                            },
                            "source_mapping": [
                                {"source": "input_1", "range": [0, 2]},
                                {"source": "input_2", "range": [3, 5]},
                                {"source": "input_3", "range": [6, 8]},
                            ],
                        }
                    },
                },
                {
                    "name": "Data Union with Deduplication",
                    "description": "Combine datasets and remove duplicates based on unique identifiers",
                    "configurations": {
                        "merge_strategy": "union",
                        "merge_key": "id",
                        "handle_duplicates": "remove_duplicates",
                        "wait_for_all": True,
                    },
                    "input_example": {
                        "input_1": [
                            {"id": 1, "name": "Alice", "team": "Engineering"},
                            {"id": 2, "name": "Bob", "team": "Design"},
                        ],
                        "input_2": [
                            {"id": 2, "name": "Bob", "team": "Product"},
                            {"id": 3, "name": "Carol", "team": "Marketing"},
                        ],
                    },
                    "expected_outputs": {
                        "result": {
                            "merged_data": [
                                {"id": 1, "name": "Alice", "team": "Engineering"},
                                {"id": 2, "name": "Bob", "team": "Product"},
                                {"id": 3, "name": "Carol", "team": "Marketing"},
                            ],
                            "merge_stats": {
                                "total_inputs": 2,
                                "items_merged": 3,
                                "duplicates_removed": 1,
                                "merge_time_ms": 8,
                            },
                        }
                    },
                },
            ],
        )


# Export the specification instance
MERGE_FLOW_SPEC = MergeFlowSpec()
