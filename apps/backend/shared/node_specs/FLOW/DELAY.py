"""
DELAY Flow Node Specification

Delay node for introducing time delays in workflow execution.
Supports various delay strategies including fixed delays, random delays, and conditional delays.
"""

from typing import Any, Dict, List

from shared.models.node_enums import FlowSubtype, NodeType
from shared.node_specs.base import COMMON_CONFIGS, BaseNodeSpec


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
                "duration_seconds": {
                    "type": "number",
                    "default": 5.0,
                    "min": 0.1,
                    "max": 86400,
                    "description": "固定延迟时间（秒）",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Parameter schemas (preferred over legacy defaults)
            input_params={
                "data": {
                    "type": "object",
                    "default": {},
                    "description": "Payload to pass through after delay",
                    "required": True,
                }
            },
            output_params={
                "data": {
                    "type": "object",
                    "default": {},
                    "description": "Payload after delay completion or cancellation",
                    "required": False,
                },
                "delay_info": {
                    "type": "object",
                    "default": {
                        "planned_delay_seconds": 0,
                        "actual_delay_seconds": 0,
                        "delay_start_time": "",
                        "delay_end_time": "",
                        "delay_type_used": "",
                        "was_cancelled": False,
                    },
                    "description": "Details and metrics about the delay performed",
                    "required": False,
                },
            },
            # Port definitions
            input_ports=[
                {
                    "id": "main",
                    "name": "main",
                    "data_type": "any",
                    "description": "Data to pass through after delay",
                    "required": True,
                    "max_connections": 1,
                },
                {
                    "id": "delay_config",
                    "name": "delay_config",
                    "data_type": "dict",
                    "description": "Dynamic delay configuration override",
                    "required": False,
                    "max_connections": 1,
                },
                {
                    "id": "cancel_signal",
                    "name": "cancel_signal",
                    "data_type": "boolean",
                    "description": "Signal to cancel the delay",
                    "required": False,
                    "max_connections": 1,
                },
            ],
            output_ports=[
                {
                    "id": "main",
                    "name": "main",
                    "data_type": "object",
                    "description": "Data output after delay completion",
                    "required": True,
                    "max_connections": -1,
                }
            ],
            # Metadata
            tags=["flow", "delay", "timing", "throttle", "rate-limit", "schedule"],
            # Examples (simplified node — only fixed delay behavior shown)
            examples=[
                {
                    "name": "Fixed Delay",
                    "description": "Simple fixed delay for workflow throttling",
                    "configurations": {"duration_seconds": 3.0},
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
                    "name": "Cancellable Fixed Delay",
                    "description": "Delay that gets cancelled by an external signal before completion",
                    "configurations": {"duration_seconds": 10.0},
                    "input_example": {
                        "main": {
                            "task_id": "task_001",
                            "operation": "generate_report",
                            "parameters": {"format": "pdf"},
                        },
                        "cancel_signal": True,
                    },
                    "expected_outputs": {
                        "cancelled": {
                            "task_id": "task_001",
                            "operation": "generate_report",
                            "parameters": {"format": "pdf"},
                            "delay_info": {
                                "planned_delay_seconds": 10.0,
                                "actual_delay_seconds": 2.1,
                                "delay_start_time": "2025-01-20T14:30:00Z",
                                "delay_end_time": "2025-01-20T14:30:02Z",
                                "delay_type_used": "fixed",
                                "was_cancelled": True,
                            },
                        }
                    },
                },
            ],
        )


# Export the specification instance
DELAY_FLOW_SPEC = DelayFlowSpec()
