"""
WAIT Flow Node Specification

Wait node for pausing workflow execution until specific conditions are met.
Supports various wait strategies including event-based, condition-based, and time-based waiting.
"""

from typing import Any, Dict, List

from ...models.node_enums import FlowSubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec, create_port


class WaitFlowSpec(BaseNodeSpec):
    """Wait flow node specification for conditional workflow pausing."""

    def __init__(self):
        super().__init__(
            type=NodeType.FLOW,
            subtype=FlowSubtype.WAIT,
            name="Wait",
            description="Pause workflow execution until specific conditions are met or events occur",
            # Configuration parameters
            configurations={
                "wait_type": {
                    "type": "string",
                    "default": "condition",
                    "description": "等待类型",
                    "required": True,
                    "options": [
                        "condition",  # Wait for condition to be true
                        "event",  # Wait for specific event
                        "signal",  # Wait for external signal
                        "resource",  # Wait for resource availability
                        "approval",  # Wait for human approval
                        "webhook",  # Wait for webhook call
                        "file",  # Wait for file existence/change
                        "api_response",  # Wait for API to return specific response
                        "queue_message",  # Wait for message in queue
                        "database_change",  # Wait for database state change
                    ],
                },
                "wait_condition": {
                    "type": "string",
                    "default": "",
                    "description": "等待条件表达式",
                    "required": False,
                    "multiline": True,
                },
                "check_interval_seconds": {
                    "type": "number",
                    "default": 5.0,
                    "min": 0.1,
                    "max": 300,
                    "description": "条件检查间隔（秒）",
                    "required": False,
                },
                "timeout_seconds": {
                    "type": "number",
                    "default": 300,
                    "min": 1,
                    "max": 86400,
                    "description": "等待超时时间（秒）",
                    "required": False,
                },
                "max_attempts": {
                    "type": "integer",
                    "default": -1,
                    "min": -1,
                    "max": 1000,
                    "description": "最大尝试次数（-1为无限制）",
                    "required": False,
                },
                "event_config": {
                    "type": "object",
                    "default": {},
                    "description": "事件配置",
                    "required": False,
                },
                "webhook_config": {
                    "type": "object",
                    "default": {
                        "endpoint_path": "/webhook/wait",
                        "method": "POST",
                        "expected_payload": {},
                        "authentication_required": True,
                    },
                    "description": "Webhook配置",
                    "required": False,
                },
                "file_config": {
                    "type": "object",
                    "default": {
                        "file_path": "",
                        "watch_type": "existence",
                        "file_pattern": "",
                        "check_content": False,
                        "expected_content": "",
                    },
                    "description": "文件等待配置",
                    "required": False,
                },
                "api_config": {
                    "type": "object",
                    "default": {
                        "url": "",
                        "method": "GET",
                        "headers": {},
                        "expected_status": 200,
                        "expected_response": {},
                        "retry_on_failure": True,
                    },
                    "description": "API响应等待配置",
                    "required": False,
                },
                "queue_config": {
                    "type": "object",
                    "default": {
                        "queue_name": "",
                        "message_filter": {},
                        "consume_message": True,
                        "queue_type": "redis",
                    },
                    "description": "队列消息等待配置",
                    "required": False,
                },
                "database_config": {
                    "type": "object",
                    "default": {
                        "connection_string": "",
                        "table_name": "",
                        "condition_query": "",
                        "expected_result": {},
                    },
                    "description": "数据库变更等待配置",
                    "required": False,
                },
                "resource_config": {
                    "type": "object",
                    "default": {
                        "resource_type": "cpu",
                        "availability_threshold": 80,
                        "check_method": "system_metrics",
                    },
                    "description": "资源可用性配置",
                    "required": False,
                },
                "exponential_backoff": {
                    "type": "boolean",
                    "default": False,
                    "description": "是否使用指数退避",
                    "required": False,
                },
                "backoff_multiplier": {
                    "type": "number",
                    "default": 1.5,
                    "min": 1.1,
                    "max": 3.0,
                    "description": "退避乘数",
                    "required": False,
                },
                "pass_through_data": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否透传输入数据",
                    "required": False,
                },
                "include_wait_metadata": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否包含等待元数据",
                    "required": False,
                },
                "cancellable": {
                    "type": "boolean",
                    "default": True,
                    "description": "等待是否可以被取消",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Default runtime parameters
            default_input_params={"data": {}, "context": {}, "variables": {}},
            default_output_params={
                "data": {},
                "wait_result": {
                    "condition_met": False,
                    "wait_duration_seconds": 0,
                    "attempts_made": 0,
                    "wait_start_time": "",
                    "wait_end_time": "",
                    "timeout_occurred": False,
                    "was_cancelled": False,
                },
                "trigger_data": {},
            },
            # Port definitions
            input_ports=[
                create_port(
                    port_id="main",
                    name="main",
                    data_type="any",
                    description="Data to pass through after wait completion",
                    required=True,
                    max_connections=1,
                ),
                create_port(
                    port_id="wait_config",
                    name="wait_config",
                    data_type="dict",
                    description="Dynamic wait configuration override",
                    required=False,
                    max_connections=1,
                ),
                create_port(
                    port_id="cancel_signal",
                    name="cancel_signal",
                    data_type="boolean",
                    description="Signal to cancel the wait",
                    required=False,
                    max_connections=1,
                ),
                create_port(
                    port_id="trigger_event",
                    name="trigger_event",
                    data_type="any",
                    description="External event trigger to complete wait",
                    required=False,
                    max_connections=1,
                ),
            ],
            output_ports=[
                create_port(
                    port_id="completed",
                    name="completed",
                    data_type="any",
                    description="Data output when wait condition is satisfied",
                    required=True,
                    max_connections=-1,
                ),
                create_port(
                    port_id="timeout",
                    name="timeout",
                    data_type="any",
                    description="Data output when wait timeout is reached",
                    required=False,
                    max_connections=-1,
                ),
                create_port(
                    port_id="cancelled",
                    name="cancelled",
                    data_type="any",
                    description="Data output when wait is cancelled",
                    required=False,
                    max_connections=-1,
                ),
                create_port(
                    port_id="failed",
                    name="failed",
                    data_type="any",
                    description="Data output when wait fails due to error",
                    required=False,
                    max_connections=-1,
                ),
            ],
            # Metadata
            tags=["flow", "wait", "condition", "event", "synchronization", "pause"],
            # Examples
            examples=[
                {
                    "name": "Condition-based Wait",
                    "description": "Wait for a specific condition to become true",
                    "configurations": {
                        "wait_type": "condition",
                        "wait_condition": "data.status === 'processed' && data.confidence_score > 0.8",
                        "check_interval_seconds": 2.0,
                        "timeout_seconds": 60,
                        "max_attempts": 30,
                        "pass_through_data": True,
                    },
                    "input_example": {
                        "main": {
                            "job_id": "job_12345",
                            "status": "processing",
                            "confidence_score": 0.65,
                            "started_at": "2025-01-20T14:30:00Z",
                        }
                    },
                    "expected_outputs": {
                        "completed": {
                            "job_id": "job_12345",
                            "status": "processed",
                            "confidence_score": 0.85,
                            "started_at": "2025-01-20T14:30:00Z",
                            "wait_result": {
                                "condition_met": True,
                                "wait_duration_seconds": 24.5,
                                "attempts_made": 12,
                                "wait_start_time": "2025-01-20T14:30:00Z",
                                "wait_end_time": "2025-01-20T14:30:25Z",
                                "timeout_occurred": False,
                                "was_cancelled": False,
                                "final_condition_check": "data.status === 'processed' && data.confidence_score > 0.8 = true",
                            },
                        }
                    },
                },
                {
                    "name": "Webhook Wait",
                    "description": "Wait for webhook callback with specific payload",
                    "configurations": {
                        "wait_type": "webhook",
                        "webhook_config": {
                            "endpoint_path": "/webhook/payment-confirmed",
                            "method": "POST",
                            "expected_payload": {
                                "payment_id": "{{payment_id}}",
                                "status": "confirmed",
                            },
                            "authentication_required": True,
                        },
                        "timeout_seconds": 300,
                        "pass_through_data": True,
                        "include_wait_metadata": True,
                    },
                    "input_example": {
                        "main": {
                            "order_id": "ORD-2025-001",
                            "payment_id": "PAY-12345",
                            "amount": 99.99,
                            "currency": "USD",
                            "customer_email": "customer@example.com",
                        }
                    },
                    "expected_outputs": {
                        "completed": {
                            "order_id": "ORD-2025-001",
                            "payment_id": "PAY-12345",
                            "amount": 99.99,
                            "currency": "USD",
                            "customer_email": "customer@example.com",
                            "wait_result": {
                                "condition_met": True,
                                "wait_duration_seconds": 45.2,
                                "attempts_made": 1,
                                "wait_start_time": "2025-01-20T14:30:00Z",
                                "wait_end_time": "2025-01-20T14:30:45Z",
                                "timeout_occurred": False,
                                "was_cancelled": False,
                                "webhook_received": True,
                            },
                            "trigger_data": {
                                "webhook_payload": {
                                    "payment_id": "PAY-12345",
                                    "status": "confirmed",
                                    "transaction_id": "TXN-67890",
                                    "confirmed_at": "2025-01-20T14:30:45Z",
                                }
                            },
                        }
                    },
                },
                {
                    "name": "File Existence Wait",
                    "description": "Wait for file to be created or modified",
                    "configurations": {
                        "wait_type": "file",
                        "file_config": {
                            "file_path": "/data/exports/daily_report_{{date}}.csv",
                            "watch_type": "creation",
                            "file_pattern": "daily_report_*.csv",
                            "check_content": True,
                            "expected_content": "Total Records:",
                        },
                        "check_interval_seconds": 10.0,
                        "timeout_seconds": 600,
                        "exponential_backoff": True,
                        "backoff_multiplier": 1.2,
                    },
                    "input_example": {
                        "main": {
                            "export_job_id": "export_001",
                            "date": "2025-01-20",
                            "requested_format": "csv",
                            "notification_email": "admin@company.com",
                        }
                    },
                    "expected_outputs": {
                        "completed": {
                            "export_job_id": "export_001",
                            "date": "2025-01-20",
                            "requested_format": "csv",
                            "notification_email": "admin@company.com",
                            "wait_result": {
                                "condition_met": True,
                                "wait_duration_seconds": 180.5,
                                "attempts_made": 15,
                                "wait_start_time": "2025-01-20T14:30:00Z",
                                "wait_end_time": "2025-01-20T14:33:01Z",
                                "timeout_occurred": False,
                                "was_cancelled": False,
                                "file_found": True,
                            },
                            "trigger_data": {
                                "file_path": "/data/exports/daily_report_2025-01-20.csv",
                                "file_size": 1048576,
                                "file_created_at": "2025-01-20T14:33:01Z",
                                "content_verified": True,
                            },
                        }
                    },
                },
                {
                    "name": "API Response Wait with Timeout",
                    "description": "Wait for API to return expected response, handling timeout",
                    "configurations": {
                        "wait_type": "api_response",
                        "api_config": {
                            "url": "https://api.example.com/jobs/{{job_id}}/status",
                            "method": "GET",
                            "headers": {"Authorization": "Bearer {{api_token}}"},
                            "expected_status": 200,
                            "expected_response": {"status": "completed"},
                            "retry_on_failure": True,
                        },
                        "check_interval_seconds": 5.0,
                        "timeout_seconds": 120,
                        "max_attempts": 24,
                        "exponential_backoff": True,
                    },
                    "input_example": {
                        "main": {
                            "job_id": "background_job_456",
                            "api_token": "token_abc123",
                            "submitted_at": "2025-01-20T14:30:00Z",
                            "priority": "high",
                        }
                    },
                    "expected_outputs": {
                        "timeout": {
                            "job_id": "background_job_456",
                            "api_token": "token_abc123",
                            "submitted_at": "2025-01-20T14:30:00Z",
                            "priority": "high",
                            "wait_result": {
                                "condition_met": False,
                                "wait_duration_seconds": 120.0,
                                "attempts_made": 24,
                                "wait_start_time": "2025-01-20T14:30:00Z",
                                "wait_end_time": "2025-01-20T14:32:00Z",
                                "timeout_occurred": True,
                                "was_cancelled": False,
                                "last_api_response": {
                                    "status": "processing",
                                    "progress": 85,
                                    "estimated_completion": "2025-01-20T14:35:00Z",
                                },
                            },
                        }
                    },
                },
            ],
        )


# Export the specification instance
WAIT_FLOW_SPEC = WaitFlowSpec()
