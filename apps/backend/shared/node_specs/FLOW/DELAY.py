"""
DELAY Flow Node Specification

Delay node for introducing time delays in workflow execution.
Supports various delay strategies including fixed delays, random delays, and conditional delays.
"""

from typing import Any, Dict, List

from ...models.node_enums import FlowSubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec, create_port


class DelayFlowSpec(BaseNodeSpec):
    """Delay flow node specification for workflow timing control."""

    def __init__(self):
        super().__init__(
            type=NodeType.FLOW,
            subtype=FlowSubtype.DELAY,
            name="Delay",
            description="Introduce configurable time delays in workflow execution with various delay strategies",
            # Configuration parameters
            configurations={
                "delay_type": {
                    "type": "string",
                    "default": "fixed",
                    "description": "延迟类型",
                    "required": True,
                    "options": [
                        "fixed",  # Fixed delay duration
                        "random",  # Random delay within range
                        "exponential",  # Exponential backoff delay
                        "linear_backoff",  # Linear increasing delay
                        "conditional",  # Delay based on conditions
                        "dynamic",  # Delay determined at runtime
                        "rate_limited",  # Delay to maintain rate limits
                        "scheduled",  # Delay until specific time
                    ],
                },
                "duration_seconds": {
                    "type": "number",
                    "default": 5.0,
                    "min": 0.1,
                    "max": 86400,
                    "description": "固定延迟时间（秒）",
                    "required": False,
                },
                "min_delay_seconds": {
                    "type": "number",
                    "default": 1.0,
                    "min": 0.1,
                    "max": 3600,
                    "description": "最小延迟时间（秒）",
                    "required": False,
                },
                "max_delay_seconds": {
                    "type": "number",
                    "default": 10.0,
                    "min": 0.1,
                    "max": 86400,
                    "description": "最大延迟时间（秒）",
                    "required": False,
                },
                "backoff_multiplier": {
                    "type": "number",
                    "default": 2.0,
                    "min": 1.1,
                    "max": 10.0,
                    "description": "退避乘数",
                    "required": False,
                },
                "retry_count": {
                    "type": "integer",
                    "default": 0,
                    "min": 0,
                    "max": 10,
                    "description": "重试计数（用于退避计算）",
                    "required": False,
                },
                "jitter_enabled": {
                    "type": "boolean",
                    "default": False,
                    "description": "是否启用随机抖动",
                    "required": False,
                },
                "jitter_percentage": {
                    "type": "number",
                    "default": 10.0,
                    "min": 0.0,
                    "max": 50.0,
                    "description": "抖动百分比",
                    "required": False,
                },
                "conditional_delay": {
                    "type": "object",
                    "default": {},
                    "description": "条件延迟配置",
                    "required": False,
                },
                "rate_limit_config": {
                    "type": "object",
                    "default": {"max_requests": 100, "time_window_seconds": 60, "bucket_size": 10},
                    "description": "速率限制配置",
                    "required": False,
                },
                "scheduled_time": {
                    "type": "string",
                    "default": "",
                    "description": "计划执行时间（ISO 8601格式）",
                    "required": False,
                },
                "timezone": {
                    "type": "string",
                    "default": "UTC",
                    "description": "时区设置",
                    "required": False,
                },
                "pass_through_data": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否透传输入数据",
                    "required": False,
                },
                "add_delay_metadata": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否添加延迟元数据",
                    "required": False,
                },
                "cancellable": {
                    "type": "boolean",
                    "default": True,
                    "description": "延迟是否可以被取消",
                    "required": False,
                },
                "max_total_delay": {
                    "type": "number",
                    "default": 300.0,
                    "min": 1.0,
                    "max": 3600,
                    "description": "最大总延迟时间（秒）",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Default runtime parameters
            default_input_params={"data": {}, "metadata": {}, "execution_context": {}},
            default_output_params={
                "data": {},
                "delay_info": {
                    "planned_delay_seconds": 0,
                    "actual_delay_seconds": 0,
                    "delay_start_time": "",
                    "delay_end_time": "",
                    "delay_type_used": "",
                    "was_cancelled": False,
                },
                "execution_metadata": {},
            },
            # Port definitions
            input_ports=[
                create_port(
                    port_id="main",
                    name="main",
                    data_type="any",
                    description="Data to pass through after delay",
                    required=True,
                    max_connections=1,
                ),
                create_port(
                    port_id="delay_config",
                    name="delay_config",
                    data_type="dict",
                    description="Dynamic delay configuration override",
                    required=False,
                    max_connections=1,
                ),
                create_port(
                    port_id="cancel_signal",
                    name="cancel_signal",
                    data_type="boolean",
                    description="Signal to cancel the delay",
                    required=False,
                    max_connections=1,
                ),
            ],
            output_ports=[
                create_port(
                    port_id="delayed",
                    name="delayed",
                    data_type="any",
                    description="Data output after delay completion",
                    required=True,
                    max_connections=-1,
                ),
                create_port(
                    port_id="cancelled",
                    name="cancelled",
                    data_type="any",
                    description="Data output if delay was cancelled",
                    required=False,
                    max_connections=-1,
                ),
                create_port(
                    port_id="timeout",
                    name="timeout",
                    data_type="any",
                    description="Data output if maximum delay was exceeded",
                    required=False,
                    max_connections=-1,
                ),
            ],
            # Metadata
            tags=["flow", "delay", "timing", "throttle", "rate-limit", "schedule"],
            # Examples
            examples=[
                {
                    "name": "Fixed Delay",
                    "description": "Simple fixed delay for workflow throttling",
                    "configurations": {
                        "delay_type": "fixed",
                        "duration_seconds": 3.0,
                        "pass_through_data": True,
                        "add_delay_metadata": True,
                    },
                    "input_example": {
                        "main": {
                            "user_id": 12345,
                            "action": "send_notification",
                            "message": "Welcome to our service!",
                        }
                    },
                    "expected_outputs": {
                        "delayed": {
                            "user_id": 12345,
                            "action": "send_notification",
                            "message": "Welcome to our service!",
                            "delay_info": {
                                "planned_delay_seconds": 3.0,
                                "actual_delay_seconds": 3.01,
                                "delay_start_time": "2025-01-20T14:30:00Z",
                                "delay_end_time": "2025-01-20T14:30:03Z",
                                "delay_type_used": "fixed",
                                "was_cancelled": False,
                            },
                        }
                    },
                },
                {
                    "name": "Random Delay with Jitter",
                    "description": "Random delay within range with additional jitter for load distribution",
                    "configurations": {
                        "delay_type": "random",
                        "min_delay_seconds": 2.0,
                        "max_delay_seconds": 8.0,
                        "jitter_enabled": True,
                        "jitter_percentage": 15.0,
                        "pass_through_data": True,
                    },
                    "input_example": {
                        "main": {
                            "batch_id": "batch_001",
                            "items": [1, 2, 3, 4, 5],
                            "priority": "normal",
                        }
                    },
                    "expected_outputs": {
                        "delayed": {
                            "batch_id": "batch_001",
                            "items": [1, 2, 3, 4, 5],
                            "priority": "normal",
                            "delay_info": {
                                "planned_delay_seconds": 5.2,
                                "actual_delay_seconds": 5.78,
                                "delay_start_time": "2025-01-20T14:30:00Z",
                                "delay_end_time": "2025-01-20T14:30:06Z",
                                "delay_type_used": "random_with_jitter",
                                "was_cancelled": False,
                                "base_random_delay": 5.2,
                                "jitter_applied": 0.58,
                            },
                        }
                    },
                },
                {
                    "name": "Exponential Backoff",
                    "description": "Exponential backoff delay for retry scenarios",
                    "configurations": {
                        "delay_type": "exponential",
                        "min_delay_seconds": 1.0,
                        "max_delay_seconds": 60.0,
                        "backoff_multiplier": 2.0,
                        "retry_count": 3,
                        "jitter_enabled": True,
                        "jitter_percentage": 25.0,
                    },
                    "input_example": {
                        "main": {
                            "api_endpoint": "https://api.example.com/users",
                            "request_data": {"user_id": 123},
                            "retry_attempt": 3,
                            "last_error": "rate_limit_exceeded",
                        }
                    },
                    "expected_outputs": {
                        "delayed": {
                            "api_endpoint": "https://api.example.com/users",
                            "request_data": {"user_id": 123},
                            "retry_attempt": 3,
                            "last_error": "rate_limit_exceeded",
                            "delay_info": {
                                "planned_delay_seconds": 8.0,
                                "actual_delay_seconds": 9.6,
                                "delay_start_time": "2025-01-20T14:30:00Z",
                                "delay_end_time": "2025-01-20T14:30:10Z",
                                "delay_type_used": "exponential_backoff",
                                "was_cancelled": False,
                                "base_delay": 8.0,
                                "backoff_calculation": "1.0 * (2.0 ^ 3) = 8.0",
                                "jitter_applied": 1.6,
                            },
                        }
                    },
                },
                {
                    "name": "Rate Limited Delay",
                    "description": "Intelligent delay to maintain API rate limits",
                    "configurations": {
                        "delay_type": "rate_limited",
                        "rate_limit_config": {
                            "max_requests": 50,
                            "time_window_seconds": 60,
                            "bucket_size": 5,
                            "current_count": 47,
                        },
                        "pass_through_data": True,
                        "cancellable": True,
                    },
                    "input_example": {
                        "main": {
                            "api_call": "create_user",
                            "user_data": {"name": "John Doe", "email": "john@example.com"},
                            "timestamp": "2025-01-20T14:30:00Z",
                        }
                    },
                    "expected_outputs": {
                        "delayed": {
                            "api_call": "create_user",
                            "user_data": {"name": "John Doe", "email": "john@example.com"},
                            "timestamp": "2025-01-20T14:30:00Z",
                            "delay_info": {
                                "planned_delay_seconds": 12.5,
                                "actual_delay_seconds": 12.5,
                                "delay_start_time": "2025-01-20T14:30:00Z",
                                "delay_end_time": "2025-01-20T14:30:13Z",
                                "delay_type_used": "rate_limited",
                                "was_cancelled": False,
                                "rate_limit_status": {
                                    "requests_remaining": 3,
                                    "window_reset_time": "2025-01-20T14:31:00Z",
                                    "calculated_delay": 12.5,
                                },
                            },
                        }
                    },
                },
                {
                    "name": "Scheduled Delay Until Specific Time",
                    "description": "Delay execution until a specific scheduled time",
                    "configurations": {
                        "delay_type": "scheduled",
                        "scheduled_time": "2025-01-20T15:00:00Z",
                        "timezone": "UTC",
                        "max_total_delay": 3600,
                        "cancellable": True,
                        "pass_through_data": True,
                    },
                    "input_example": {
                        "main": {
                            "scheduled_task": "daily_report_generation",
                            "report_config": {"date_range": "yesterday", "include_charts": True},
                        }
                    },
                    "expected_outputs": {
                        "delayed": {
                            "scheduled_task": "daily_report_generation",
                            "report_config": {"date_range": "yesterday", "include_charts": True},
                            "delay_info": {
                                "planned_delay_seconds": 1800,
                                "actual_delay_seconds": 1800,
                                "delay_start_time": "2025-01-20T14:30:00Z",
                                "delay_end_time": "2025-01-20T15:00:00Z",
                                "delay_type_used": "scheduled",
                                "was_cancelled": False,
                                "scheduled_time": "2025-01-20T15:00:00Z",
                                "actual_execution_time": "2025-01-20T15:00:00Z",
                            },
                        }
                    },
                },
            ],
        )


# Export the specification instance
DELAY_FLOW_SPEC = DelayFlowSpec()
