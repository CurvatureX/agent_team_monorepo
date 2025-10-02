"""
MANUAL Trigger Node Specification

Manual trigger activated by user action. This trigger has no input ports
and produces execution context when manually invoked.
"""

from typing import Any, Dict, List

from ...models.node_enums import NodeType, TriggerSubtype
from ..base import COMMON_CONFIGS, BaseNodeSpec


class ManualTriggerSpec(BaseNodeSpec):
    """Manual trigger specification following the new workflow architecture."""

    def __init__(self):
        super().__init__(
            type=NodeType.TRIGGER,
            subtype=TriggerSubtype.MANUAL,
            name="Manual_Trigger",
            description="Manual trigger activated by user action",
            # Configuration parameters (no longer "parameters")
            configurations={
                "trigger_name": {
                    "type": "string",
                    "default": "Manual Trigger",
                    "description": "显示名称",
                    "required": False,
                },
                "description": {
                    "type": "string",
                    "default": "",
                    "description": "触发器描述",
                    "required": False,
                },
                **COMMON_CONFIGS,  # Include common configurations
            },
            # Parameter schemas (preferred over legacy defaults)
            input_params={},  # Triggers have no runtime inputs
            output_params={
                "trigger_time": {
                    "type": "string",
                    "default": "",
                    "description": "ISO-8601 time when user triggered execution",
                    "required": False,
                },
                "execution_id": {
                    "type": "string",
                    "default": "",
                    "description": "Execution identifier for correlation",
                    "required": False,
                },
                "user_id": {
                    "type": "string",
                    "default": "",
                    "description": "ID of the user who triggered",
                    "required": False,
                },
                "trigger_message": {
                    "type": "string",
                    "default": "",
                    "description": "Human-friendly trigger message",
                    "required": False,
                },
            },
            # Port definitions using new Port model            # Metadata
            tags=["trigger", "manual", "user-initiated"],
            # Examples
            examples=[
                {
                    "name": "Simple Manual Trigger",
                    "description": "Basic manual workflow execution",
                    "configurations": {
                        "trigger_name": "Start Workflow",
                        "description": "Manually start the data processing workflow",
                    },
                    "expected_output": {
                        "trigger_time": "2025-01-28T10:30:00Z",
                        "execution_id": "exec_123",
                        "user_id": "user_456",
                        "trigger_message": "Manually started data processing workflow",
                    },
                },
                {
                    "name": "Emergency Trigger",
                    "description": "Emergency workflow execution",
                    "configurations": {
                        "trigger_name": "Emergency Response",
                        "description": "Emergency execution due to system alert",
                    },
                    "expected_output": {
                        "trigger_time": "2025-01-28T15:45:00Z",
                        "execution_id": "exec_789",
                        "user_id": "admin_001",
                        "trigger_message": "Emergency response triggered due to system failure alert",
                    },
                },
            ],
        )


# Export the specification instance
MANUAL_TRIGGER_SPEC = ManualTriggerSpec()
