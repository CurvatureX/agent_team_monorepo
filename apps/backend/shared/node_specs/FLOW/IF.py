"""
IF Flow Control Node Specification

Flow control node for conditional logic and branching in workflows.
Evaluates conditions and routes execution to different paths based on results.
"""

from typing import Any, Dict, List

from ...models.node_enums import FlowSubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec, create_port


class IfFlowSpec(BaseNodeSpec):
    """IF flow control specification for conditional workflow branching."""

    def __init__(self):
        super().__init__(
            type=NodeType.FLOW,
            subtype=FlowSubtype.IF,
            name="If_Condition",
            description="Conditional flow control with multiple branching paths",
            # Configuration parameters
            configurations={
                "condition_type": {
                    "type": "string",
                    "default": "expression",
                    "description": "条件类型",
                    "required": True,
                    "options": ["expression", "script", "field_comparison", "exists_check"],
                },
                "condition_expression": {
                    "type": "string",
                    "default": "",
                    "description": "条件表达式 (支持JavaScript语法)",
                    "required": True,
                    "multiline": True,
                },
                "conditions": {
                    "type": "array",
                    "default": [],
                    "description": "多条件配置列表",
                    "required": False,
                },
                "evaluation_mode": {
                    "type": "string",
                    "default": "all",
                    "description": "多条件评估模式",
                    "required": False,
                    "options": ["all", "any", "custom"],
                },
                "default_path": {
                    "type": "string",
                    "default": "false",
                    "description": "默认执行路径",
                    "required": False,
                    "options": ["true", "false", "error"],
                },
                "strict_mode": {
                    "type": "boolean",
                    "default": False,
                    "description": "严格模式 - 类型敏感比较",
                    "required": False,
                },
                "context_variables": {
                    "type": "array",
                    "default": [],
                    "description": "可用的上下文变量列表",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Default runtime parameters
            default_input_params={"data": {}, "context": {}, "variables": {}},
            default_output_params={
                "condition_result": False,
                "evaluation_details": {},
                "execution_path": "",
                "processed_data": {},
            },
            # Port definitions - IF nodes have multiple output paths
            input_ports=[
                create_port(
                    port_id="main",
                    name="main",
                    data_type="dict",
                    description="Input data for condition evaluation",
                    required=True,
                    max_connections=1,
                )
            ],
            output_ports=[
                create_port(
                    port_id="true",
                    name="true",
                    data_type="dict",
                    description="Output when condition evaluates to true",
                    required=False,
                    max_connections=-1,
                ),
                create_port(
                    port_id="false",
                    name="false",
                    data_type="dict",
                    description="Output when condition evaluates to false",
                    required=False,
                    max_connections=-1,
                ),
                create_port(
                    port_id="error",
                    name="error",
                    data_type="dict",
                    description="Error output when condition evaluation fails",
                    required=False,
                    max_connections=-1,
                ),
            ],
            # Metadata
            tags=["flow", "conditional", "branching", "logic"],
            # Examples
            examples=[
                {
                    "name": "Simple Number Comparison",
                    "description": "Check if a value is greater than threshold",
                    "configurations": {
                        "condition_type": "expression",
                        "condition_expression": "data.score > 80",
                        "default_path": "false",
                    },
                    "input_example": {"data": {"score": 95, "user_id": "12345"}},
                    "expected_outputs": {
                        "true": {
                            "condition_result": True,
                            "evaluation_details": {
                                "expression": "data.score > 80",
                                "evaluated_value": "95 > 80",
                                "result": True,
                            },
                            "execution_path": "true",
                            "processed_data": {"score": 95, "user_id": "12345"},
                        }
                    },
                },
                {
                    "name": "Multiple Conditions",
                    "description": "Evaluate multiple conditions with AND logic",
                    "configurations": {
                        "condition_type": "expression",
                        "condition_expression": "data.status === 'active' && data.verified === true && data.score >= 70",
                        "evaluation_mode": "all",
                        "strict_mode": True,
                    },
                    "input_example": {
                        "data": {
                            "status": "active",
                            "verified": True,
                            "score": 85,
                            "user_id": "67890",
                        }
                    },
                    "expected_outputs": {
                        "true": {
                            "condition_result": True,
                            "evaluation_details": {
                                "conditions_met": [
                                    {"condition": "status === 'active'", "result": True},
                                    {"condition": "verified === true", "result": True},
                                    {"condition": "score >= 70", "result": True},
                                ],
                                "overall_result": True,
                            },
                            "execution_path": "true",
                            "processed_data": {
                                "status": "active",
                                "verified": True,
                                "score": 85,
                                "user_id": "67890",
                            },
                        }
                    },
                },
                {
                    "name": "Field Existence Check",
                    "description": "Check if required fields exist in the data",
                    "configurations": {
                        "condition_type": "exists_check",
                        "conditions": [
                            {"field": "email", "required": True},
                            {"field": "phone", "required": False},
                        ],
                        "evaluation_mode": "all",
                    },
                    "input_example": {
                        "data": {"email": "user@example.com", "name": "John Doe", "age": 30}
                    },
                    "expected_outputs": {
                        "false": {
                            "condition_result": False,
                            "evaluation_details": {
                                "field_checks": [
                                    {
                                        "field": "email",
                                        "exists": True,
                                        "required": True,
                                        "passed": True,
                                    },
                                    {
                                        "field": "phone",
                                        "exists": False,
                                        "required": False,
                                        "passed": True,
                                    },
                                ],
                                "missing_required": [],
                                "overall_result": False,
                            },
                            "execution_path": "false",
                        }
                    },
                },
                {
                    "name": "Complex Business Logic",
                    "description": "Evaluate complex business rules with custom script",
                    "configurations": {
                        "condition_type": "script",
                        "condition_expression": """
                            // Business logic: Approve if high value customer or urgent request
                            const isHighValue = data.customer_tier === 'premium' || data.total_spent > 10000;
                            const isUrgent = data.priority === 'high' && data.request_type === 'support';
                            const hasValidAccount = data.account_status === 'active' && !data.suspended;

                            return (isHighValue || isUrgent) && hasValidAccount;
                        """,
                        "context_variables": [
                            "customer_tier",
                            "total_spent",
                            "priority",
                            "request_type",
                            "account_status",
                        ],
                    },
                    "input_example": {
                        "data": {
                            "customer_tier": "premium",
                            "total_spent": 5000,
                            "priority": "normal",
                            "request_type": "billing",
                            "account_status": "active",
                            "suspended": False,
                        }
                    },
                    "expected_outputs": {
                        "true": {
                            "condition_result": True,
                            "evaluation_details": {
                                "script_execution": {
                                    "isHighValue": True,
                                    "isUrgent": False,
                                    "hasValidAccount": True,
                                    "final_result": True,
                                }
                            },
                            "execution_path": "true",
                        }
                    },
                },
            ],
        )


# Export the specification instance
IF_FLOW_SPEC = IfFlowSpec()
