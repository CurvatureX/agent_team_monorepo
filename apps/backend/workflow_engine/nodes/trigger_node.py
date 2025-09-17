"""
Trigger Node Executor.

Handles manual, webhook, and scheduled triggers.
"""

from datetime import datetime
from typing import Any, Dict

from shared.models.node_enums import NodeType, TriggerSubtype

from .base import BaseNodeExecutor, ExecutionStatus, NodeExecutionContext, NodeExecutionResult
from .factory import NodeExecutorFactory


@NodeExecutorFactory.register(NodeType.TRIGGER.value)
class TriggerNodeExecutor(BaseNodeExecutor):
    """Executor for trigger nodes."""

    def __init__(self, node_type: str = NodeType.TRIGGER.value, subtype: str = None):
        super().__init__(node_type, subtype)

    async def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute trigger node."""
        trigger_type = self.subtype or context.get_parameter(
            "trigger_type", TriggerSubtype.MANUAL.value
        )

        self.log_execution(context, f"Executing trigger node: {trigger_type}")

        # For trigger nodes, we mainly prepare the initial data
        output_data = {
            "trigger_type": trigger_type,
            "triggered_at": datetime.now().isoformat(),
            "trigger_data": context.input_data,
            "workflow_id": context.workflow_id,
            "execution_id": context.execution_id,
        }

        # Handle different trigger types
        if trigger_type == TriggerSubtype.MANUAL.value:
            output_data.update(
                {
                    "source": "manual_execution",
                    "initiated_by": context.get_parameter("user_id", "system"),
                }
            )

        elif trigger_type == TriggerSubtype.WEBHOOK.value:
            output_data.update(
                {"source": "webhook", "webhook_data": context.input_data.get("payload", {})}
            )

        elif trigger_type == TriggerSubtype.CRON.value:
            output_data.update(
                {"source": "scheduler", "schedule_info": context.get_parameter("schedule", {})}
            )

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            metadata={
                "node_type": "trigger",
                "trigger_type": trigger_type,
                "execution_timestamp": datetime.now().isoformat(),
            },
        )

    def validate_parameters(self, context: NodeExecutionContext) -> tuple[bool, str]:
        """Validate trigger node parameters."""
        # Basic validation for trigger nodes
        return True, ""
