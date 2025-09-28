"""
FILTER Flow Node Specification

Filter node for selecting/excluding data based on specified criteria.
Supports various filter conditions, expressions, and custom filter functions.
"""

from typing import Any, Dict, List

from ...models.node_enums import FlowSubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec, create_port


class FilterFlowSpec(BaseNodeSpec):
    """Filter flow node specification for data selection and exclusion."""

    def __init__(self):
        super().__init__(
            type=NodeType.FLOW,
            subtype=FlowSubtype.FILTER,
            name="Filter",
            description="Filter data based on conditions, expressions, or custom logic to select or exclude items",
            # Configuration parameters
            configurations={
                "filter_mode": {
                    "type": "string",
                    "default": "include",
                    "description": "过滤模式",
                    "required": True,
                    "options": ["include", "exclude", "partition"],
                },
                "filter_type": {
                    "type": "string",
                    "default": "simple_condition",
                    "description": "过滤器类型",
                    "required": True,
                    "options": [
                        "simple_condition",  # field operator value
                        "complex_expression",  # JavaScript expression
                        "custom_function",  # Custom filter function
                        "regex_pattern",  # Regular expression matching
                        "range_filter",  # Numeric/date range filtering
                        "exists_filter",  # Field existence check
                        "type_filter",  # Data type filtering
                        "array_contains",  # Array membership testing
                        "fuzzy_match",  # Fuzzy string matching
                    ],
                },
                "conditions": {
                    "type": "array",
                    "default": [],
                    "description": "过滤条件列表",
                    "required": True,
                },
                "logical_operator": {
                    "type": "string",
                    "default": "AND",
                    "description": "多条件逻辑操作符",
                    "required": False,
                    "options": ["AND", "OR", "NOT"],
                },
                "custom_filter_function": {
                    "type": "string",
                    "default": "",
                    "description": "自定义过滤函数（JavaScript代码）",
                    "required": False,
                    "multiline": True,
                },
                "case_sensitive": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否区分大小写",
                    "required": False,
                },
                "null_handling": {
                    "type": "string",
                    "default": "exclude",
                    "description": "空值处理方式",
                    "required": False,
                    "options": ["include", "exclude", "treat_as_empty"],
                },
                "nested_field_support": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否支持嵌套字段访问",
                    "required": False,
                },
                "max_results": {
                    "type": "integer",
                    "default": -1,
                    "min": -1,
                    "description": "最大结果数量（-1为不限制）",
                    "required": False,
                },
                "sort_filtered_results": {
                    "type": "boolean",
                    "default": False,
                    "description": "是否对过滤结果排序",
                    "required": False,
                },
                "sort_field": {
                    "type": "string",
                    "default": "",
                    "description": "排序字段",
                    "required": False,
                },
                "sort_order": {
                    "type": "string",
                    "default": "asc",
                    "description": "排序顺序",
                    "required": False,
                    "options": ["asc", "desc"],
                },
                "error_handling": {
                    "type": "string",
                    "default": "skip_invalid",
                    "description": "错误处理方式",
                    "required": False,
                    "options": ["skip_invalid", "fail_on_error", "include_with_warning"],
                },
                **COMMON_CONFIGS,
            },
            # Default runtime parameters
            default_input_params={"data": [], "metadata": {}, "context": {}},
            default_output_params={
                "filtered_data": [],
                "excluded_data": [],
                "filter_stats": {
                    "total_input": 0,
                    "items_passed": 0,
                    "items_filtered": 0,
                    "filter_time_ms": 0,
                },
                "validation_errors": [],
            },
            # Port definitions
            input_ports=[
                create_port(
                    port_id="main",
                    name="main",
                    data_type="any",
                    description="Data to be filtered",
                    required=True,
                    max_connections=1,
                ),
                create_port(
                    port_id="filter_config",
                    name="filter_config",
                    data_type="dict",
                    description="Dynamic filter configuration override",
                    required=False,
                    max_connections=1,
                ),
            ],
            output_ports=[
                create_port(
                    port_id="passed",
                    name="passed",
                    data_type="any",
                    description="Data that passed the filter criteria",
                    required=True,
                    max_connections=-1,
                ),
                create_port(
                    port_id="filtered",
                    name="filtered",
                    data_type="any",
                    description="Data that was filtered out (only in partition mode)",
                    required=False,
                    max_connections=-1,
                ),
                create_port(
                    port_id="statistics",
                    name="statistics",
                    data_type="dict",
                    description="Filter operation statistics and metadata",
                    required=False,
                    max_connections=-1,
                ),
            ],
            # Metadata
            tags=["flow", "filter", "select", "condition", "data-processing"],
            # Examples
            examples=[
                {
                    "name": "Simple Field Filter",
                    "description": "Filter array of objects based on field value condition",
                    "configurations": {
                        "filter_mode": "include",
                        "filter_type": "simple_condition",
                        "conditions": [
                            {"field": "status", "operator": "equals", "value": "active"}
                        ],
                        "null_handling": "exclude",
                    },
                    "input_example": {
                        "main": [
                            {"id": 1, "name": "Alice", "status": "active", "age": 30},
                            {"id": 2, "name": "Bob", "status": "inactive", "age": 25},
                            {"id": 3, "name": "Carol", "status": "active", "age": 35},
                            {"id": 4, "name": "David", "status": None, "age": 28},
                        ]
                    },
                    "expected_outputs": {
                        "passed": [
                            {"id": 1, "name": "Alice", "status": "active", "age": 30},
                            {"id": 3, "name": "Carol", "status": "active", "age": 35},
                        ],
                        "statistics": {
                            "filter_stats": {
                                "total_input": 4,
                                "items_passed": 2,
                                "items_filtered": 2,
                                "filter_time_ms": 3,
                            },
                            "validation_errors": [],
                        },
                    },
                },
                {
                    "name": "Complex Multi-Condition Filter",
                    "description": "Filter with multiple conditions using AND/OR logic",
                    "configurations": {
                        "filter_mode": "include",
                        "filter_type": "simple_condition",
                        "conditions": [
                            {"field": "age", "operator": "greater_than", "value": 25},
                            {
                                "field": "department",
                                "operator": "in",
                                "value": ["Engineering", "Product"],
                            },
                        ],
                        "logical_operator": "AND",
                        "sort_filtered_results": True,
                        "sort_field": "age",
                        "sort_order": "desc",
                    },
                    "input_example": {
                        "main": [
                            {"name": "Alice", "age": 30, "department": "Engineering"},
                            {"name": "Bob", "age": 24, "department": "Engineering"},
                            {"name": "Carol", "age": 35, "department": "Marketing"},
                            {"name": "David", "age": 28, "department": "Product"},
                            {"name": "Eve", "age": 32, "department": "Product"},
                        ]
                    },
                    "expected_outputs": {
                        "passed": [
                            {"name": "Carol", "age": 35, "department": "Marketing"},
                            {"name": "Eve", "age": 32, "department": "Product"},
                            {"name": "Alice", "age": 30, "department": "Engineering"},
                            {"name": "David", "age": 28, "department": "Product"},
                        ],
                        "statistics": {
                            "filter_stats": {
                                "total_input": 5,
                                "items_passed": 4,
                                "items_filtered": 1,
                                "filter_time_ms": 5,
                            }
                        },
                    },
                },
                {
                    "name": "Range Filter with Partitioning",
                    "description": "Partition data into included and excluded sets based on numeric range",
                    "configurations": {
                        "filter_mode": "partition",
                        "filter_type": "range_filter",
                        "conditions": [
                            {"field": "score", "min_value": 70, "max_value": 100, "inclusive": True}
                        ],
                        "sort_filtered_results": True,
                        "sort_field": "score",
                        "sort_order": "desc",
                    },
                    "input_example": {
                        "main": [
                            {"student": "Alice", "score": 85, "subject": "Math"},
                            {"student": "Bob", "score": 65, "subject": "Math"},
                            {"student": "Carol", "score": 92, "subject": "Math"},
                            {"student": "David", "score": 58, "subject": "Math"},
                            {"student": "Eve", "score": 78, "subject": "Math"},
                        ]
                    },
                    "expected_outputs": {
                        "passed": [
                            {"student": "Carol", "score": 92, "subject": "Math"},
                            {"student": "Alice", "score": 85, "subject": "Math"},
                            {"student": "Eve", "score": 78, "subject": "Math"},
                        ],
                        "filtered": [
                            {"student": "Bob", "score": 65, "subject": "Math"},
                            {"student": "David", "score": 58, "subject": "Math"},
                        ],
                        "statistics": {
                            "filter_stats": {
                                "total_input": 5,
                                "items_passed": 3,
                                "items_filtered": 2,
                                "filter_time_ms": 4,
                            },
                            "range_stats": {"min_passed": 78, "max_passed": 92, "avg_passed": 85},
                        },
                    },
                },
                {
                    "name": "Custom JavaScript Filter",
                    "description": "Advanced filtering using custom JavaScript function",
                    "configurations": {
                        "filter_mode": "include",
                        "filter_type": "custom_function",
                        "custom_filter_function": "function(item) { return item.email && item.email.endsWith('@company.com') && item.is_active === true && new Date(item.last_login) > new Date(Date.now() - 30*24*60*60*1000); }",
                        "max_results": 10,
                        "error_handling": "skip_invalid",
                    },
                    "input_example": {
                        "main": [
                            {
                                "name": "Alice",
                                "email": "alice@company.com",
                                "is_active": True,
                                "last_login": "2025-01-15T10:00:00Z",
                            },
                            {
                                "name": "Bob",
                                "email": "bob@external.com",
                                "is_active": True,
                                "last_login": "2025-01-18T14:30:00Z",
                            },
                            {
                                "name": "Carol",
                                "email": "carol@company.com",
                                "is_active": False,
                                "last_login": "2024-12-20T09:15:00Z",
                            },
                        ]
                    },
                    "expected_outputs": {
                        "passed": [
                            {
                                "name": "Alice",
                                "email": "alice@company.com",
                                "is_active": True,
                                "last_login": "2025-01-15T10:00:00Z",
                            }
                        ],
                        "statistics": {
                            "filter_stats": {
                                "total_input": 3,
                                "items_passed": 1,
                                "items_filtered": 2,
                                "filter_time_ms": 8,
                            },
                            "validation_errors": [],
                        },
                    },
                },
            ],
        )


# Export the specification instance
FILTER_FLOW_SPEC = FilterFlowSpec()
