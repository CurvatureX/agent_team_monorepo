"""
SWITCH Flow Control Node Specification

Flow control node for multi-way branching based on switch-case logic.
Routes execution to different paths based on case matching and expressions.
"""

from typing import Any, Dict, List

from ...models.node_enums import FlowSubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec, create_port


class SwitchFlowSpec(BaseNodeSpec):
    """SWITCH flow control specification for multi-way conditional branching."""

    def __init__(self):
        super().__init__(
            type=NodeType.FLOW,
            subtype=FlowSubtype.SWITCH,
            name="Switch_Case",
            description="Multi-way flow control with switch-case logic and pattern matching",
            # Configuration parameters
            configurations={
                "switch_expression": {
                    "type": "string",
                    "default": "",
                    "description": "切换表达式，用于评估匹配值",
                    "required": True,
                },
                "cases": {
                    "type": "array",
                    "default": [],
                    "description": "案例配置列表",
                    "required": True,
                },
                "case_type": {
                    "type": "string",
                    "default": "exact_match",
                    "description": "案例匹配类型",
                    "required": False,
                    "options": [
                        "exact_match",
                        "pattern_match",
                        "range_match",
                        "type_match",
                        "regex_match",
                    ],
                },
                "default_case": {
                    "type": "string",
                    "default": "default",
                    "description": "默认案例名称",
                    "required": False,
                },
                "strict_mode": {
                    "type": "boolean",
                    "default": False,
                    "description": "严格模式 - 类型敏感匹配",
                    "required": False,
                },
                "allow_fallthrough": {
                    "type": "boolean",
                    "default": False,
                    "description": "允许案例穿透执行",
                    "required": False,
                },
                "case_sensitivity": {
                    "type": "boolean",
                    "default": True,
                    "description": "字符串匹配是否区分大小写",
                    "required": False,
                },
                "multiple_match": {
                    "type": "boolean",
                    "default": False,
                    "description": "是否允许多案例匹配",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Default runtime parameters
            default_input_params={"data": {}, "context": {}, "switch_value": None},
            default_output_params={
                "matched_cases": [],
                "switch_value": None,
                "evaluation_result": "",
                "executed_path": "",
                "processed_data": {},
            },
            # Port definitions - Switch nodes have dynamic output ports based on cases
            input_ports=[
                create_port(
                    port_id="main",
                    name="main",
                    data_type="dict",
                    description="Input data for switch evaluation",
                    required=True,
                    max_connections=1,
                )
            ],
            output_ports=[
                create_port(
                    port_id="case_1",
                    name="case_1",
                    data_type="dict",
                    description="Output for case 1 match",
                    required=False,
                    max_connections=-1,
                ),
                create_port(
                    port_id="case_2",
                    name="case_2",
                    data_type="dict",
                    description="Output for case 2 match",
                    required=False,
                    max_connections=-1,
                ),
                create_port(
                    port_id="case_3",
                    name="case_3",
                    data_type="dict",
                    description="Output for case 3 match",
                    required=False,
                    max_connections=-1,
                ),
                create_port(
                    port_id="default",
                    name="default",
                    data_type="dict",
                    description="Default output when no cases match",
                    required=False,
                    max_connections=-1,
                ),
                create_port(
                    port_id="error",
                    name="error",
                    data_type="dict",
                    description="Error output when switch evaluation fails",
                    required=False,
                    max_connections=-1,
                ),
            ],
            # Metadata
            tags=["flow", "switch", "case", "branching", "conditional"],
            # Examples
            examples=[
                {
                    "name": "User Type Routing",
                    "description": "Route users to different workflows based on their type",
                    "configurations": {
                        "switch_expression": "data.user.type",
                        "case_type": "exact_match",
                        "cases": [
                            {"case_id": "case_1", "value": "admin", "label": "Administrator"},
                            {"case_id": "case_2", "value": "moderator", "label": "Moderator"},
                            {"case_id": "case_3", "value": "user", "label": "Regular User"},
                        ],
                        "default_case": "default",
                    },
                    "input_example": {
                        "data": {
                            "user": {
                                "id": "12345",
                                "name": "John Doe",
                                "type": "admin",
                                "permissions": ["read", "write", "admin"],
                            },
                            "action": "login",
                        }
                    },
                    "expected_outputs": {
                        "case_1": {
                            "matched_cases": ["case_1"],
                            "switch_value": "admin",
                            "evaluation_result": "admin",
                            "executed_path": "case_1",
                            "processed_data": {
                                "user": {
                                    "id": "12345",
                                    "name": "John Doe",
                                    "type": "admin",
                                    "permissions": ["read", "write", "admin"],
                                },
                                "action": "login",
                                "user_category": "administrator",
                            },
                        }
                    },
                },
                {
                    "name": "HTTP Status Code Handling",
                    "description": "Handle different HTTP response status codes",
                    "configurations": {
                        "switch_expression": "data.response.status_code",
                        "case_type": "range_match",
                        "cases": [
                            {"case_id": "case_1", "range": [200, 299], "label": "Success"},
                            {"case_id": "case_2", "range": [400, 499], "label": "Client Error"},
                            {"case_id": "case_3", "range": [500, 599], "label": "Server Error"},
                        ],
                        "default_case": "default",
                    },
                    "input_example": {
                        "data": {
                            "response": {
                                "status_code": 404,
                                "body": "Not Found",
                                "headers": {"content-type": "application/json"},
                            },
                            "request_id": "req_789",
                        }
                    },
                    "expected_outputs": {
                        "case_2": {
                            "matched_cases": ["case_2"],
                            "switch_value": 404,
                            "evaluation_result": "client_error",
                            "executed_path": "case_2",
                            "processed_data": {
                                "response": {
                                    "status_code": 404,
                                    "body": "Not Found",
                                    "headers": {"content-type": "application/json"},
                                },
                                "request_id": "req_789",
                                "error_category": "client_error",
                                "retry_recommended": False,
                            },
                        }
                    },
                },
                {
                    "name": "File Type Processing",
                    "description": "Process files differently based on file extension",
                    "configurations": {
                        "switch_expression": "data.file.extension.toLowerCase()",
                        "case_type": "pattern_match",
                        "cases": [
                            {
                                "case_id": "case_1",
                                "pattern": ["jpg", "png", "gif"],
                                "label": "Image Files",
                            },
                            {
                                "case_id": "case_2",
                                "pattern": ["pdf", "doc", "docx"],
                                "label": "Document Files",
                            },
                            {
                                "case_id": "case_3",
                                "pattern": ["mp4", "avi", "mov"],
                                "label": "Video Files",
                            },
                        ],
                        "case_sensitivity": False,
                        "default_case": "default",
                    },
                    "input_example": {
                        "data": {
                            "file": {
                                "name": "presentation.PDF",
                                "extension": "PDF",
                                "size": 2048576,
                                "path": "/uploads/presentation.PDF",
                            }
                        }
                    },
                    "expected_outputs": {
                        "case_2": {
                            "matched_cases": ["case_2"],
                            "switch_value": "pdf",
                            "evaluation_result": "document_files",
                            "executed_path": "case_2",
                            "processed_data": {
                                "file": {
                                    "name": "presentation.PDF",
                                    "extension": "PDF",
                                    "size": 2048576,
                                    "path": "/uploads/presentation.PDF",
                                },
                                "file_type": "document",
                                "processing_pipeline": "document_extraction",
                            },
                        }
                    },
                },
                {
                    "name": "Priority Level Switch",
                    "description": "Handle tasks based on priority levels with multiple matching",
                    "configurations": {
                        "switch_expression": "data.task.priority",
                        "case_type": "exact_match",
                        "cases": [
                            {
                                "case_id": "case_1",
                                "value": "critical",
                                "label": "Critical Priority",
                            },
                            {"case_id": "case_2", "value": "high", "label": "High Priority"},
                            {"case_id": "case_3", "value": "normal", "label": "Normal Priority"},
                        ],
                        "multiple_match": False,
                        "strict_mode": True,
                    },
                    "input_example": {
                        "data": {
                            "task": {
                                "id": "task_456",
                                "title": "Database backup",
                                "priority": "critical",
                                "assigned_to": "ops_team",
                            }
                        }
                    },
                    "expected_outputs": {
                        "case_1": {
                            "matched_cases": ["case_1"],
                            "switch_value": "critical",
                            "evaluation_result": "critical",
                            "executed_path": "case_1",
                            "processed_data": {
                                "task": {
                                    "id": "task_456",
                                    "title": "Database backup",
                                    "priority": "critical",
                                    "assigned_to": "ops_team",
                                },
                                "escalation_level": "immediate",
                                "notification_channels": ["slack", "email", "sms"],
                            },
                        }
                    },
                },
            ],
        )


# Export the specification instance
SWITCH_FLOW_SPEC = SwitchFlowSpec()
