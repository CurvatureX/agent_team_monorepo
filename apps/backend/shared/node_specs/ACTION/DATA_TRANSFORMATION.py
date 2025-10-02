"""
DATA_TRANSFORMATION Action Node Specification

System action for transforming, filtering, mapping, and manipulating data.
This is a core system action for data processing within workflows.
"""

from typing import Any, Dict, List

from ...models.node_enums import ActionSubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec


class DataTransformationActionSpec(BaseNodeSpec):
    """Data transformation action specification for system data operations."""

    def __init__(self):
        super().__init__(
            type=NodeType.ACTION,
            subtype=ActionSubtype.DATA_TRANSFORMATION,
            name="Data_Transformation",
            description="Transform, filter, and manipulate data structures",
            # Configuration parameters
            configurations={
                "operation": {
                    "type": "string",
                    "default": "map",
                    "description": "数据转换操作类型",
                    "required": True,
                    "options": [
                        "map",  # 映射字段
                        "filter",  # 过滤数据
                        "aggregate",  # 聚合数据
                        "sort",  # 排序
                        "group_by",  # 分组
                        "join",  # 连接数据
                        "flatten",  # 扁平化
                        "pivot",  # 透视表
                        "custom",  # 自定义脚本
                    ],
                },
                "transformation_script": {
                    "type": "string",
                    "default": "",
                    "description": "数据转换脚本 (JavaScript/Python)",
                    "required": False,
                    "multiline": True,
                },
                "field_mapping": {
                    "type": "object",
                    "default": {},
                    "description": '字段映射配置 {"output_field": "input_field"}',
                    "required": False,
                },
                "filter_conditions": {
                    "type": "array",
                    "default": [],
                    "description": "过滤条件列表",
                    "required": False,
                },
                "sort_config": {
                    "type": "object",
                    "default": {"field": "", "direction": "asc"},
                    "description": "排序配置",
                    "required": False,
                },
                "group_by_fields": {
                    "type": "array",
                    "default": [],
                    "description": "分组字段列表",
                    "required": False,
                },
                "aggregation_functions": {
                    "type": "object",
                    "default": {},
                    "description": '聚合函数配置 {"field": "function"}',
                    "required": False,
                },
                "output_format": {
                    "type": "string",
                    "default": "json",
                    "description": "输出数据格式",
                    "required": False,
                    "options": ["json", "array", "csv", "xml"],
                },
                "preserve_metadata": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否保留原始数据的元数据",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Default runtime parameters
            default_input_params={"data": [], "context": {}, "variables": {}},
            default_output_params={
                "transformed_data": [],
                "original_count": 0,
                "output_count": 0,
                "transformation_stats": {},
                "success": False,
                "error_message": "",
            },
            # Port definitions
            input_ports=[
                {
                    "id": "main",
                    "name": "main",
                    "data_type": "dict",
                    "description": "Input data to transform",
                    "required": True,
                    "max_connections": 1,
                }
            ],
            output_ports=[
                {
                    "id": "main",
                    "name": "main",
                    "data_type": "dict",
                    "description": "Transformed data output",
                    "required": False,
                    "max_connections": -1,
                }
            ],
            # Metadata
            tags=["action", "data", "transformation", "system"],
            # Examples
            examples=[
                {
                    "name": "Field Mapping",
                    "description": "Map input fields to different output field names",
                    "configurations": {
                        "operation": "map",
                        "field_mapping": {
                            "full_name": "name",
                            "email_address": "email",
                            "user_id": "id",
                            "registration_date": "created_at",
                        },
                    },
                    "input_example": {
                        "data": [
                            {
                                "id": "123",
                                "name": "John Doe",
                                "email": "john@example.com",
                                "created_at": "2025-01-15",
                            }
                        ]
                    },
                    "expected_output": {
                        "transformed_data": [
                            {
                                "user_id": "123",
                                "full_name": "John Doe",
                                "email_address": "john@example.com",
                                "registration_date": "2025-01-15",
                            }
                        ],
                        "original_count": 1,
                        "output_count": 1,
                        "success": True,
                    },
                },
                {
                    "name": "Data Filtering",
                    "description": "Filter data based on specific conditions",
                    "configurations": {
                        "operation": "filter",
                        "filter_conditions": [
                            {"field": "status", "operator": "equals", "value": "active"},
                            {"field": "score", "operator": "greater_than", "value": 80},
                        ],
                    },
                    "input_example": {
                        "data": [
                            {"id": 1, "status": "active", "score": 95},
                            {"id": 2, "status": "inactive", "score": 85},
                            {"id": 3, "status": "active", "score": 75},
                            {"id": 4, "status": "active", "score": 90},
                        ]
                    },
                    "expected_output": {
                        "transformed_data": [
                            {"id": 1, "status": "active", "score": 95},
                            {"id": 4, "status": "active", "score": 90},
                        ],
                        "original_count": 4,
                        "output_count": 2,
                        "transformation_stats": {"filtered_out": 2, "filter_conditions_applied": 2},
                        "success": True,
                    },
                },
                {
                    "name": "Data Aggregation",
                    "description": "Group and aggregate data by specified fields",
                    "configurations": {
                        "operation": "aggregate",
                        "group_by_fields": ["department"],
                        "aggregation_functions": {
                            "salary": "avg",
                            "employee_count": "count",
                            "max_salary": "max",
                        },
                    },
                    "input_example": {
                        "data": [
                            {"department": "Engineering", "salary": 100000, "name": "Alice"},
                            {"department": "Engineering", "salary": 120000, "name": "Bob"},
                            {"department": "Sales", "salary": 80000, "name": "Charlie"},
                            {"department": "Sales", "salary": 90000, "name": "Diana"},
                        ]
                    },
                    "expected_output": {
                        "transformed_data": [
                            {
                                "department": "Engineering",
                                "salary": 110000,
                                "employee_count": 2,
                                "max_salary": 120000,
                            },
                            {
                                "department": "Sales",
                                "salary": 85000,
                                "employee_count": 2,
                                "max_salary": 90000,
                            },
                        ],
                        "original_count": 4,
                        "output_count": 2,
                        "success": True,
                    },
                },
            ],
        )


# Export the specification instance
DATA_TRANSFORMATION_ACTION_SPEC = DataTransformationActionSpec()
