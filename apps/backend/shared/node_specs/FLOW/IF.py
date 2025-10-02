"""
IF Flow Control Node Specification

Flow control node for conditional logic and branching in workflows.
Evaluates conditions and routes execution to different paths based on results.
"""

from typing import Any, Dict, List

from ...models.node_enums import FlowSubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec


class IfFlowSpec(BaseNodeSpec):
    """IF flow control specification for conditional workflow branching."""

    def __init__(self):
        super().__init__(
            type=NodeType.FLOW,
            subtype=FlowSubtype.IF,
            name="If_Condition",
            description="Conditional flow control with multiple branching paths",
            # Configuration parameters (simplified — expression only)
            configurations={
                "condition_expression": {
                    "type": "string",
                    "default": "",
                    "description": "条件表达式 (仅支持表达式形式的JavaScript语法)",
                    "required": True,
                    "multiline": True,
                },
                **COMMON_CONFIGS,
            },
            # Parameter schemas (preferred over legacy defaults)
            input_params={
                "data": {
                    "type": "object",
                    "default": {},
                    "description": "Input data for condition evaluation",
                    "required": True,
                },
                "context": {
                    "type": "object",
                    "default": {},
                    "description": "Optional context variables",
                    "required": False,
                },
                "variables": {
                    "type": "object",
                    "default": {},
                    "description": "Template/runtime variables",
                    "required": False,
                },
            },
            output_params={
                "data": {
                    "type": "object",
                    "default": {},
                    "description": "Input data for condition evaluation",
                    "required": True,
                },
                "condition_result": {
                    "type": "boolean",
                    "default": False,
                    "description": "Final boolean evaluation of the condition",
                    "required": False,
                },
            },
            # Port definitions - IF nodes have multiple output paths
            input_ports=[
                {
                    "id": "main",
                    "name": "main",
                    "data_type": "dict",
                    "description": "Input data for condition evaluation",
                    "required": True,
                    "max_connections": 1,
                }
            ],
            output_ports=[
                {
                    "id": "true",
                    "name": "true",
                    "data_type": "dict",
                    "description": "Output when condition evaluates to true",
                    "required": False,
                    "max_connections": -1,
                },
                {
                    "id": "false",
                    "name": "false",
                    "data_type": "dict",
                    "description": "Output when condition evaluates to false",
                    "required": False,
                    "max_connections": -1,
                },
            ],
            # Metadata
            tags=["flow", "conditional", "branching", "logic"],
            # Examples (expression-only)
            examples=[
                {
                    "name": "Simple Number Comparison",
                    "description": "Check if a value is greater than threshold",
                    "configurations": {
                        "condition_expression": "data.score > 80",
                    },
                    "input_example": {"data": {"score": 95, "user_id": "12345"}},
                    "expected_outputs": {
                        "true": {
                            "condition_result": True,
                            "data": {"score": 95, "user_id": "12345"},
                        }
                    },
                },
                {
                    "name": "Multiple Conditions",
                    "description": "Evaluate multiple conditions with AND logic",
                    "configurations": {
                        "condition_expression": "data.status === 'active' && data.verified === true && data.score >= 70",
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
                            "data": {
                                "status": "active",
                                "verified": True,
                                "score": 85,
                                "user_id": "67890",
                            },
                        }
                    },
                },
                {
                    "name": "Complex Business Logic (Expression)",
                    "description": "Evaluate complex business rules using a single expression",
                    "configurations": {
                        "condition_expression": "((data.customer_tier === 'premium' || data.total_spent > 10000) || (data.priority === 'high' && data.request_type === 'support')) && (data.account_status === 'active' && !data.suspended)"
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
                            "data": {
                                "customer_tier": "premium",
                                "total_spent": 5000,
                                "priority": "normal",
                                "request_type": "billing",
                                "account_status": "active",
                                "suspended": False,
                            },
                        }
                    },
                },
            ],
        )


# Export the specification instance
IF_FLOW_SPEC = IfFlowSpec()
