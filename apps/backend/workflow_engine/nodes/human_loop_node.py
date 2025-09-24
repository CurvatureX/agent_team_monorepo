"""Human Loop Node Executor - No Mock Responses."""
from datetime import datetime
from typing import Any, Dict, Optional

from shared.models.node_enums import HumanLoopSubtype, NodeType

from .base import BaseNodeExecutor, ExecutionStatus, NodeExecutionContext, NodeExecutionResult
from .factory import NodeExecutorFactory


@NodeExecutorFactory.register(NodeType.HUMAN_IN_THE_LOOP.value)
class HumanLoopNodeExecutor(BaseNodeExecutor):
    """Executor for Human-in-the-Loop nodes - Returns errors instead of mock responses."""

    def __init__(self, node_type: str = NodeType.HUMAN_IN_THE_LOOP.value, subtype: str = None):
        super().__init__(node_type, subtype)

    async def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute human-in-the-loop node."""
        interaction_type = self.subtype or context.get_parameter("interaction_type", "approval")
        title = context.get_parameter("title", "Human Input Required")
        description = context.get_parameter("description", "Please provide the requested input")

        self.log_execution(context, f"Human-in-the-loop requested: {interaction_type}")

        # Return error for all human-in-the-loop interactions instead of mock responses
        return NodeExecutionResult(
            status=ExecutionStatus.ERROR,
            error_message=f"Human-in-the-loop functionality not implemented: {interaction_type}",
            error_details={
                "interaction_type": interaction_type,
                "title": title,
                "description": description,
                "reason": "human_interaction_not_implemented",
                "solution": "Implement real human-in-the-loop functionality with actual user interface and interaction handling",
                "supported_types": [
                    HumanLoopSubtype.IN_APP_APPROVAL.value,
                    HumanLoopSubtype.FORM_SUBMISSION.value,
                    HumanLoopSubtype.MANUAL_REVIEW.value,
                    "selection",
                ],
            },
            metadata={"node_type": "human_loop", "interaction_type": interaction_type},
        )

    def validate_parameters(self, context: NodeExecutionContext) -> tuple[bool, str]:
        """Validate human loop node parameters."""
        interaction_type = self.subtype or context.get_parameter("interaction_type")

        if not interaction_type:
            return False, "Human loop node requires 'interaction_type' parameter"

        supported_types = [
            HumanLoopSubtype.IN_APP_APPROVAL.value,
            HumanLoopSubtype.FORM_SUBMISSION.value,
            HumanLoopSubtype.MANUAL_REVIEW.value,
            "approval",
            "input",
            "selection",
            "review",
        ]

        if interaction_type not in supported_types:
            return (
                False,
                f"Unsupported interaction type: {interaction_type}. Supported: {supported_types}",
            )

        return True, ""
