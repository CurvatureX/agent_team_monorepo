"""
CRON Trigger Node Specification

Cron trigger for scheduled workflow execution. This trigger has no input ports
and produces execution context based on cron schedule.
"""

from typing import Any, Dict, List

from shared.models.node_enums import NodeType, TriggerSubtype
from shared.node_specs.base import COMMON_CONFIGS, BaseNodeSpec


class CronTriggerSpec(BaseNodeSpec):
    """Cron trigger specification following the new workflow architecture."""

    def __init__(self):
        super().__init__(
            type=NodeType.TRIGGER,
            subtype=TriggerSubtype.CRON,
            name="Cron_Trigger",
            description="Scheduled trigger based on cron expression",
            # Configuration parameters
            configurations={
                "cron_expression": {
                    "type": "string",
                    "default": "0 9 * * *",  # Daily at 9 AM
                    "description": "Cron表达式定义执行计划",
                    "required": True,
                    "validation_pattern": r"^(\*|[0-5]?\d)(\s+(\*|[0-1]?\d|2[0-3]))(\s+(\*|[12]?\d|3[01]))(\s+(\*|[1-9]|1[0-2]))(\s+(\*|[0-6]))$",
                },
                "timezone": {
                    "type": "string",
                    "default": "UTC",
                    "description": "执行时区",
                    "required": False,
                },
                "max_missed_runs": {
                    "type": "integer",
                    "default": 3,
                    "min": 1,
                    "max": 10,
                    "description": "最大允许错过的执行次数",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Parameter schemas (preferred over legacy defaults)
            input_params={},  # Triggers have no runtime inputs
            output_params={
                "trigger_time": {
                    "type": "string",
                    "default": "",
                    "description": "ISO-8601 time when the cron fired",
                    "required": False,
                },
                "scheduled_time": {
                    "type": "string",
                    "default": "",
                    "description": "ISO-8601 scheduled time per cron",
                    "required": False,
                },
                "execution_id": {
                    "type": "string",
                    "default": "",
                    "description": "Execution identifier for correlation",
                    "required": False,
                },
                "cron_expression": {
                    "type": "string",
                    "default": "",
                    "description": "Cron expression used",
                    "required": False,
                },
                "timezone": {
                    "type": "string",
                    "default": "",
                    "description": "Timezone used for evaluation",
                    "required": False,
                },
                "trigger_message": {
                    "type": "string",
                    "default": "",
                    "description": "Human-friendly trigger message",
                    "required": False,
                },
            },
            # Port definitions
            input_ports=[],  # Triggers have no input ports
            output_ports=[
                {
                    "id": "main",
                    "name": "main",
                    "data_type": "dict",
                    "description": "Scheduled execution output with timing information",
                    "required": False,
                    "max_connections": -1,
                }
            ],
            # Metadata
            tags=["trigger", "cron", "scheduled", "time-based"],
            # Examples
            examples=[
                {
                    "name": "Daily Morning Report",
                    "description": "Generate daily report every morning at 9 AM",
                    "configurations": {
                        "cron_expression": "0 9 * * *",
                        "timezone": "America/New_York",
                        "active": True,
                    },
                    "expected_output": {
                        "trigger_time": "2025-01-28T14:00:00Z",
                        "scheduled_time": "2025-01-28T14:00:00Z",
                        "execution_id": "cron_exec_123",
                        "cron_expression": "0 9 * * *",
                        "timezone": "America/New_York",
                        "execution_count": 42,
                        "trigger_message": "Daily morning report scheduled execution",
                    },
                },
                {
                    "name": "Weekly Cleanup",
                    "description": "Run cleanup process every Sunday at midnight",
                    "configurations": {
                        "cron_expression": "0 0 * * 0",
                        "timezone": "UTC",
                        "active": True,
                        "execution_window_minutes": 30,
                    },
                    "expected_output": {
                        "trigger_time": "2025-02-02T00:00:00Z",
                        "scheduled_time": "2025-02-02T00:00:00Z",
                        "execution_id": "cron_exec_456",
                        "cron_expression": "0 0 * * 0",
                        "timezone": "UTC",
                        "execution_count": 8,
                        "trigger_message": "Weekly cleanup process scheduled execution",
                    },
                },
                {
                    "name": "Hourly Health Check",
                    "description": "System health check every hour during business hours",
                    "configurations": {
                        "cron_expression": "0 9-17 * * 1-5",  # 9 AM to 5 PM, Mon-Fri
                        "timezone": "UTC",
                        "active": True,
                        "max_missed_runs": 2,
                    },
                    "expected_output": {
                        "trigger_time": "2025-01-28T15:00:00Z",
                        "scheduled_time": "2025-01-28T15:00:00Z",
                        "execution_id": "cron_exec_789",
                        "cron_expression": "0 9-17 * * 1-5",
                        "timezone": "UTC",
                        "execution_count": 156,
                        "trigger_message": "Hourly health check scheduled execution",
                    },
                },
            ],
        )


# Export the specification instance
CRON_TRIGGER_SPEC = CronTriggerSpec()
