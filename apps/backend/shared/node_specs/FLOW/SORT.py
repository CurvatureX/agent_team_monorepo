"""
SORT Flow Node Specification

Sort node for ordering data based on specified criteria.
Supports various sorting strategies, multiple sort keys, and custom comparison functions.
"""

from typing import Any, Dict, List

from ...models.node_enums import FlowSubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec, create_port


class SortFlowSpec(BaseNodeSpec):
    """Sort flow node specification for data ordering and arrangement."""

    def __init__(self):
        super().__init__(
            type=NodeType.FLOW,
            subtype=FlowSubtype.SORT,
            name="Sort",
            description="Sort data based on one or multiple criteria with configurable ordering strategies",
            # Configuration parameters
            configurations={
                "sort_keys": {
                    "type": "array",
                    "default": [],
                    "description": "排序键配置列表",
                    "required": True,
                },
                "sort_strategy": {
                    "type": "string",
                    "default": "field_based",
                    "description": "排序策略",
                    "required": True,
                    "options": [
                        "field_based",  # Sort by field values
                        "custom_function",  # Custom comparison function
                        "natural_sort",  # Natural/human-friendly sorting
                        "numeric_aware",  # Numeric-aware string sorting
                        "date_aware",  # Date/time aware sorting
                        "case_insensitive",  # Case-insensitive string sorting
                        "locale_aware",  # Locale-specific sorting
                        "multi_criteria",  # Multiple field sorting with priorities
                        "random_shuffle",  # Random ordering
                    ],
                },
                "default_order": {
                    "type": "string",
                    "default": "asc",
                    "description": "默认排序顺序",
                    "required": False,
                    "options": ["asc", "desc"],
                },
                "stable_sort": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否使用稳定排序",
                    "required": False,
                },
                "null_handling": {
                    "type": "string",
                    "default": "last",
                    "description": "空值处理方式",
                    "required": False,
                    "options": ["first", "last", "exclude"],
                },
                "custom_comparator": {
                    "type": "string",
                    "default": "",
                    "description": "自定义比较函数（JavaScript代码）",
                    "required": False,
                    "multiline": True,
                },
                "case_sensitive": {
                    "type": "boolean",
                    "default": True,
                    "description": "字符串比较是否区分大小写",
                    "required": False,
                },
                "locale": {
                    "type": "string",
                    "default": "en-US",
                    "description": "本地化设置",
                    "required": False,
                },
                "nested_field_support": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否支持嵌套字段访问",
                    "required": False,
                },
                "preserve_original_order": {
                    "type": "boolean",
                    "default": False,
                    "description": "是否保留原始索引信息",
                    "required": False,
                },
                "max_items": {
                    "type": "integer",
                    "default": -1,
                    "min": -1,
                    "description": "排序的最大项目数（-1为不限制）",
                    "required": False,
                },
                "performance_mode": {
                    "type": "string",
                    "default": "balanced",
                    "description": "性能模式",
                    "required": False,
                    "options": ["fast", "balanced", "memory_efficient"],
                },
                "error_handling": {
                    "type": "string",
                    "default": "skip_invalid",
                    "description": "错误处理方式",
                    "required": False,
                    "options": ["skip_invalid", "fail_on_error", "use_fallback_value"],
                },
                "fallback_value": {
                    "type": "any",
                    "default": "",
                    "description": "错误时的回退值",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Default runtime parameters
            default_input_params={"data": [], "metadata": {}, "sort_override": {}},
            default_output_params={
                "sorted_data": [],
                "sort_stats": {
                    "total_items": 0,
                    "items_sorted": 0,
                    "sort_time_ms": 0,
                    "comparisons_made": 0,
                },
                "original_indices": [],
                "validation_errors": [],
            },
            # Port definitions
            input_ports=[
                create_port(
                    port_id="main",
                    name="main",
                    data_type="any",
                    description="Data to be sorted",
                    required=True,
                    max_connections=1,
                ),
                create_port(
                    port_id="sort_config",
                    name="sort_config",
                    data_type="dict",
                    description="Dynamic sort configuration override",
                    required=False,
                    max_connections=1,
                ),
            ],
            output_ports=[
                create_port(
                    port_id="sorted",
                    name="sorted",
                    data_type="any",
                    description="Sorted data output",
                    required=True,
                    max_connections=-1,
                ),
                create_port(
                    port_id="metadata",
                    name="metadata",
                    data_type="dict",
                    description="Sort operation metadata and statistics",
                    required=False,
                    max_connections=-1,
                ),
            ],
            # Metadata
            tags=["flow", "sort", "order", "arrange", "data-processing"],
            # Examples
            examples=[
                {
                    "name": "Simple Field Sort",
                    "description": "Sort array of objects by a single field",
                    "configurations": {
                        "sort_strategy": "field_based",
                        "sort_keys": [{"field": "name", "order": "asc"}],
                        "stable_sort": True,
                        "null_handling": "last",
                    },
                    "input_example": {
                        "main": [
                            {"name": "Charlie", "age": 30, "score": 85},
                            {"name": "Alice", "age": 25, "score": 92},
                            {"name": "Bob", "age": 35, "score": 78},
                            {"name": None, "age": 28, "score": 88},
                        ]
                    },
                    "expected_outputs": {
                        "sorted": [
                            {"name": "Alice", "age": 25, "score": 92},
                            {"name": "Bob", "age": 35, "score": 78},
                            {"name": "Charlie", "age": 30, "score": 85},
                            {"name": None, "age": 28, "score": 88},
                        ],
                        "metadata": {
                            "sort_stats": {
                                "total_items": 4,
                                "items_sorted": 4,
                                "sort_time_ms": 2,
                                "comparisons_made": 6,
                            },
                            "original_indices": [1, 2, 0, 3],
                        },
                    },
                },
                {
                    "name": "Multi-Field Sort with Priorities",
                    "description": "Sort by multiple fields with different priorities and orders",
                    "configurations": {
                        "sort_strategy": "multi_criteria",
                        "sort_keys": [
                            {"field": "department", "order": "asc", "priority": 1},
                            {"field": "salary", "order": "desc", "priority": 2},
                            {"field": "name", "order": "asc", "priority": 3},
                        ],
                        "stable_sort": True,
                    },
                    "input_example": {
                        "main": [
                            {"name": "Alice", "department": "Engineering", "salary": 95000},
                            {"name": "Bob", "department": "Engineering", "salary": 85000},
                            {"name": "Carol", "department": "Design", "salary": 78000},
                            {"name": "David", "department": "Engineering", "salary": 95000},
                            {"name": "Eve", "department": "Design", "salary": 82000},
                        ]
                    },
                    "expected_outputs": {
                        "sorted": [
                            {"name": "Eve", "department": "Design", "salary": 82000},
                            {"name": "Carol", "department": "Design", "salary": 78000},
                            {"name": "Alice", "department": "Engineering", "salary": 95000},
                            {"name": "David", "department": "Engineering", "salary": 95000},
                            {"name": "Bob", "department": "Engineering", "salary": 85000},
                        ],
                        "metadata": {
                            "sort_stats": {
                                "total_items": 5,
                                "items_sorted": 5,
                                "sort_time_ms": 4,
                                "comparisons_made": 12,
                            },
                            "sort_criteria_applied": ["department", "salary", "name"],
                        },
                    },
                },
                {
                    "name": "Natural Sort with Numbers",
                    "description": "Natural sorting that handles numeric strings properly",
                    "configurations": {
                        "sort_strategy": "natural_sort",
                        "sort_keys": [{"field": "filename", "order": "asc"}],
                        "case_sensitive": False,
                    },
                    "input_example": {
                        "main": [
                            {"filename": "file10.txt", "size": 1024},
                            {"filename": "file2.txt", "size": 512},
                            {"filename": "File1.txt", "size": 256},
                            {"filename": "file20.txt", "size": 2048},
                            {"filename": "file3.txt", "size": 768},
                        ]
                    },
                    "expected_outputs": {
                        "sorted": [
                            {"filename": "File1.txt", "size": 256},
                            {"filename": "file2.txt", "size": 512},
                            {"filename": "file3.txt", "size": 768},
                            {"filename": "file10.txt", "size": 1024},
                            {"filename": "file20.txt", "size": 2048},
                        ],
                        "metadata": {
                            "sort_stats": {
                                "total_items": 5,
                                "items_sorted": 5,
                                "sort_time_ms": 3,
                                "comparisons_made": 8,
                            },
                            "sort_type": "natural_alphanumeric",
                        },
                    },
                },
                {
                    "name": "Custom Comparator Sort",
                    "description": "Advanced sorting using custom JavaScript comparison function",
                    "configurations": {
                        "sort_strategy": "custom_function",
                        "custom_comparator": "function(a, b) { const scoreA = (a.performance * 0.7) + (a.experience * 0.3); const scoreB = (b.performance * 0.7) + (b.experience * 0.3); return scoreB - scoreA; }",
                        "stable_sort": True,
                        "preserve_original_order": True,
                    },
                    "input_example": {
                        "main": [
                            {"name": "Alice", "performance": 90, "experience": 5},
                            {"name": "Bob", "performance": 85, "experience": 8},
                            {"name": "Carol", "performance": 95, "experience": 3},
                            {"name": "David", "performance": 80, "experience": 10},
                        ]
                    },
                    "expected_outputs": {
                        "sorted": [
                            {"name": "Carol", "performance": 95, "experience": 3},
                            {"name": "Alice", "performance": 90, "experience": 5},
                            {"name": "Bob", "performance": 85, "experience": 8},
                            {"name": "David", "performance": 80, "experience": 10},
                        ],
                        "metadata": {
                            "sort_stats": {
                                "total_items": 4,
                                "items_sorted": 4,
                                "sort_time_ms": 5,
                                "comparisons_made": 6,
                            },
                            "original_indices": [2, 0, 1, 3],
                            "custom_function_used": True,
                        },
                    },
                },
            ],
        )


# Export the specification instance
SORT_FLOW_SPEC = SortFlowSpec()
