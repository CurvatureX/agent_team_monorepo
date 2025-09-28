"""
MERGE Flow Node Specification

Merge node for combining multiple data streams into a single output stream.
Supports various merge strategies including concatenation, union, intersection, and custom merge functions.
"""

from typing import Any, Dict, List

from ...models.node_enums import FlowSubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec, create_port


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
                        "concatenate",  # Combine arrays/lists end-to-end
                        "union",  # Combine unique elements from all inputs
                        "intersection",  # Only elements common to all inputs
                        "merge_objects",  # Merge object properties (last wins)
                        "deep_merge",  # Deep merge objects recursively
                        "zip",  # Combine inputs element-wise
                        "custom_function",  # Use custom merge logic
                        "first_available",  # Use first non-null/non-empty input
                        "priority_merge",  # Merge based on input priority
                    ],
                },
                "merge_key": {
                    "type": "string",
                    "default": "",
                    "description": "合并时使用的键字段",
                    "required": False,
                },
                "wait_for_all": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否等待所有输入都有数据",
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
                "custom_merge_function": {
                    "type": "string",
                    "default": "",
                    "description": "自定义合并函数（JavaScript代码）",
                    "required": False,
                    "multiline": True,
                },
                "input_priorities": {
                    "type": "object",
                    "default": {},
                    "description": "输入优先级配置",
                    "required": False,
                },
                "null_handling": {
                    "type": "string",
                    "default": "include",
                    "description": "空值处理方式",
                    "required": False,
                    "options": ["include", "exclude", "replace_with_default"],
                },
                "default_value": {
                    "type": "any",
                    "default": None,
                    "description": "空值替换的默认值",
                    "required": False,
                },
                "output_format": {
                    "type": "string",
                    "default": "array",
                    "description": "输出格式",
                    "required": False,
                    "options": ["array", "object", "single_value", "nested_object"],
                },
                **COMMON_CONFIGS,
            },
            # Default runtime parameters
            default_input_params={"data_streams": [], "metadata": {}, "timestamps": []},
            default_output_params={
                "merged_data": [],
                "merge_stats": {
                    "total_inputs": 0,
                    "items_merged": 0,
                    "duplicates_removed": 0,
                    "merge_time_ms": 0,
                },
                "source_mapping": [],
            },
            # Port definitions
            input_ports=[
                create_port(
                    port_id="input_1",
                    name="input_1",
                    data_type="any",
                    description="First data stream to merge",
                    required=True,
                    max_connections=1,
                ),
                create_port(
                    port_id="input_2",
                    name="input_2",
                    data_type="any",
                    description="Second data stream to merge",
                    required=True,
                    max_connections=1,
                ),
                create_port(
                    port_id="input_3",
                    name="input_3",
                    data_type="any",
                    description="Optional third data stream",
                    required=False,
                    max_connections=1,
                ),
                create_port(
                    port_id="input_4",
                    name="input_4",
                    data_type="any",
                    description="Optional fourth data stream",
                    required=False,
                    max_connections=1,
                ),
                create_port(
                    port_id="input_5",
                    name="input_5",
                    data_type="any",
                    description="Optional fifth data stream",
                    required=False,
                    max_connections=1,
                ),
            ],
            output_ports=[
                create_port(
                    port_id="merged",
                    name="merged",
                    data_type="any",
                    description="Combined output from all input streams",
                    required=True,
                    max_connections=-1,
                ),
                create_port(
                    port_id="metadata",
                    name="metadata",
                    data_type="dict",
                    description="Merge operation metadata and statistics",
                    required=False,
                    max_connections=-1,
                ),
            ],
            # Metadata
            tags=["flow", "merge", "combine", "data-flow", "aggregation"],
            # Examples
            examples=[
                {
                    "name": "Array Concatenation",
                    "description": "Merge multiple arrays into a single combined array",
                    "configurations": {
                        "merge_strategy": "concatenate",
                        "wait_for_all": True,
                        "handle_duplicates": "keep_all",
                        "output_format": "array",
                    },
                    "input_example": {
                        "input_1": [1, 2, 3],
                        "input_2": [4, 5, 6],
                        "input_3": [7, 8, 9],
                    },
                    "expected_outputs": {
                        "merged": [1, 2, 3, 4, 5, 6, 7, 8, 9],
                        "metadata": {
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
                        },
                    },
                },
                {
                    "name": "Object Deep Merge",
                    "description": "Deep merge configuration objects from multiple sources",
                    "configurations": {
                        "merge_strategy": "deep_merge",
                        "wait_for_all": True,
                        "null_handling": "exclude",
                        "output_format": "object",
                    },
                    "input_example": {
                        "input_1": {
                            "database": {
                                "host": "localhost",
                                "port": 5432,
                                "settings": {"timeout": 30},
                            },
                            "features": ["auth", "cache"],
                        },
                        "input_2": {
                            "database": {
                                "host": "production.db",
                                "ssl": True,
                                "settings": {"pool_size": 10},
                            },
                            "features": ["logging"],
                            "version": "2.1.0",
                        },
                    },
                    "expected_outputs": {
                        "merged": {
                            "database": {
                                "host": "production.db",
                                "port": 5432,
                                "ssl": True,
                                "settings": {"timeout": 30, "pool_size": 10},
                            },
                            "features": ["auth", "cache", "logging"],
                            "version": "2.1.0",
                        },
                        "metadata": {
                            "merge_stats": {
                                "total_inputs": 2,
                                "items_merged": 1,
                                "duplicates_removed": 0,
                                "merge_time_ms": 12,
                            }
                        },
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
                        "output_format": "array",
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
                        "merged": [
                            {"id": 1, "name": "Alice", "team": "Engineering"},
                            {"id": 2, "name": "Bob", "team": "Product"},
                            {"id": 3, "name": "Carol", "team": "Marketing"},
                        ],
                        "metadata": {
                            "merge_stats": {
                                "total_inputs": 2,
                                "items_merged": 3,
                                "duplicates_removed": 1,
                                "merge_time_ms": 8,
                            },
                            "duplicate_resolution": "kept_last_occurrence",
                        },
                    },
                },
                {
                    "name": "Priority-based Merge",
                    "description": "Merge data with input prioritization for conflict resolution",
                    "configurations": {
                        "merge_strategy": "priority_merge",
                        "input_priorities": {"input_1": 1, "input_2": 3, "input_3": 2},
                        "wait_for_all": False,
                        "timeout_seconds": 60,
                        "output_format": "object",
                    },
                    "input_example": {
                        "input_1": {"status": "draft", "priority": "low"},
                        "input_2": {"status": "published", "author": "system"},
                        "input_3": {"priority": "high", "updated_at": "2025-01-20T10:00:00Z"},
                    },
                    "expected_outputs": {
                        "merged": {
                            "status": "published",
                            "priority": "high",
                            "author": "system",
                            "updated_at": "2025-01-20T10:00:00Z",
                        },
                        "metadata": {
                            "merge_stats": {
                                "total_inputs": 3,
                                "items_merged": 1,
                                "duplicates_removed": 0,
                                "merge_time_ms": 3,
                            },
                            "priority_order": ["input_2", "input_3", "input_1"],
                            "conflicts_resolved": ["priority", "status"],
                        },
                    },
                },
            ],
        )


# Export the specification instance
MERGE_FLOW_SPEC = MergeFlowSpec()
