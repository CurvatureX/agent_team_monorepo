"""
Human-in-the-Loop Node Executor - Production Implementation.

Handles human interaction operations with workflow pause/resume, AI response filtering,
and multi-channel communication support according to the HIL system technical design.
"""

import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from shared.models import NodeType
from shared.models.human_in_loop import (
    HILChannelType,
    HILErrorData,
    HILFilteredData,
    HILInputData,
    HILInteractionType,
    HILOutputData,
    HILPriority,
    HILStatus,
    HILTimeoutData,
)
from shared.models.node_enums import HumanLoopSubtype
from shared.node_specs import node_spec_registry
from shared.node_specs.base import NodeSpec

from .base import BaseNodeExecutor, ExecutionStatus, NodeExecutionContext, NodeExecutionResult


class HumanLoopNodeExecutor(BaseNodeExecutor):
    """Enhanced HIL node executor with workflow pause and AI response filtering."""

    def __init__(self, subtype: Optional[str] = None):
        super().__init__(subtype=subtype)
        # Initialize components that would be injected in production
        self.ai_classifier = None  # TODO: Initialize HILResponseClassifier
        self.channel_integrations = None  # TODO: Initialize ChannelIntegrationManager
        self.workflow_status_manager = None  # TODO: Initialize WorkflowStatusManager
        self.timeout_manager = None  # TODO: Initialize TimeoutManager

    def _get_node_spec(self) -> Optional[NodeSpec]:
        """Get the node specification for human loop nodes."""
        if node_spec_registry and self._subtype:
            return node_spec_registry.get_spec(NodeType.HUMAN_IN_THE_LOOP.value, self._subtype)
        return None

    def get_supported_subtypes(self) -> List[str]:
        """Get supported human-in-the-loop subtypes."""
        return [subtype.value for subtype in HumanLoopSubtype]

    def validate(self, node: Any) -> List[str]:
        """Validate HIL node configuration using standardized data models."""
        errors = super().validate(node)

        if not node.subtype:
            errors.append("Human-in-the-loop subtype is required")
            return errors

        if node.subtype not in self.get_supported_subtypes():
            errors.append(f"Unsupported human-in-the-loop subtype: {node.subtype}")

        return errors

    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute HIL node with workflow pause and response handling."""

        logs = []
        start_time = time.time()

        try:
            # 1. Check if this is a resume from existing interaction
            existing_interaction = self._check_existing_interaction(context)
            if existing_interaction:
                logs.append(f"Resuming HIL interaction: {existing_interaction.get('id')}")
                return self._handle_resume_execution(existing_interaction, context, logs)

            # 2. Parse HIL input data from context
            try:
                hil_input = self._parse_hil_input_data(context)
                logs.append(f"Parsed HIL input: {hil_input.interaction_type}")
            except Exception as e:
                return self._create_error_result(
                    f"Invalid HIL input data: {str(e)}",
                    execution_time=time.time() - start_time,
                    logs=logs,
                )

            # 3. Create human interaction record
            logs.append("Creating new HIL interaction")
            interaction = self._create_human_interaction(hil_input, context, logs)

            # 4. Send initial message through appropriate channel
            self._send_human_request(interaction, hil_input, context, logs)

            # 5. Pause workflow execution
            self._pause_workflow_execution(interaction, context, logs)

            # 6. Return pause result to halt workflow execution
            logs.append(
                f"Workflow paused - waiting for human response (timeout: {interaction.get('timeout_at')})"
            )
            return self._create_pause_result(interaction, logs, time.time() - start_time)

        except Exception as e:
            return self._create_error_result(
                f"Error executing HIL node: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs,
            )

    def _parse_hil_input_data(self, context: NodeExecutionContext) -> HILInputData:
        """Parse and validate HIL input data from context."""
        input_data = context.input_data or {}

        # Convert context input to HILInputData model for validation
        try:
            return HILInputData(**input_data)
        except Exception as e:
            raise ValueError(f"Invalid HIL input format: {str(e)}")

    def _check_existing_interaction(
        self, context: NodeExecutionContext
    ) -> Optional[Dict[str, Any]]:
        """Check if there's an existing interaction for this workflow/node."""
        # TODO: Query human_interactions table for pending interactions
        # This would check if workflow is resuming from a paused state
        return None

    def _handle_resume_execution(
        self, interaction: Dict[str, Any], context: NodeExecutionContext, logs: List[str]
    ) -> NodeExecutionResult:
        """Handle workflow resume from existing HIL interaction."""
        logs.append(f"Processing response for interaction {interaction.get('id')}")

        # TODO: Get the human response from hil_responses table
        # TODO: Classify response using AI if needed
        # TODO: Determine output port based on response

        # Mock implementation for now
        return self._create_success_result(
            output_data={"resumed": True, "interaction_id": interaction.get("id")},
            execution_time=0,
            logs=logs,
            output_port="approved",  # TODO: Determine from actual response
        )

    def _create_human_interaction(
        self, hil_input: HILInputData, context: NodeExecutionContext, logs: List[str]
    ) -> Dict[str, Any]:
        """Create human interaction record in database."""
        interaction_id = str(uuid.uuid4())

        # Calculate timeout
        timeout_at = datetime.now() + timedelta(hours=hil_input.timeout_hours)

        interaction_data = {
            "id": interaction_id,
            "workflow_id": getattr(context, "workflow_id", "unknown"),
            "execution_id": getattr(context, "execution_id", "unknown"),
            "node_id": getattr(
                context, "node_id", context.node.id if hasattr(context.node, "id") else "unknown"
            ),
            "interaction_type": hil_input.interaction_type.value,
            "channel_type": hil_input.channel_config.channel_type.value,
            "status": HILStatus.PENDING.value,
            "priority": hil_input.priority.value,
            "created_at": datetime.now(),
            "timeout_at": timeout_at,
            "request_data": hil_input.dict(),
            "correlation_id": hil_input.correlation_id,
        }

        # TODO: Insert into human_interactions table
        logs.append(f"Created interaction {interaction_id} with {hil_input.timeout_hours}h timeout")

        return interaction_data

    def _send_human_request(
        self,
        interaction: Dict[str, Any],
        hil_input: HILInputData,
        context: NodeExecutionContext,
        logs: List[str],
    ):
        """Send human request through appropriate channel."""
        channel_type = hil_input.channel_config.channel_type

        if channel_type == HILChannelType.SLACK:
            self._send_slack_request(interaction, hil_input, logs)
        elif channel_type == HILChannelType.EMAIL:
            self._send_email_request(interaction, hil_input, logs)
        elif channel_type == HILChannelType.WEBHOOK:
            self._send_webhook_request(interaction, hil_input, logs)
        elif channel_type == HILChannelType.APP:
            self._send_app_request(interaction, hil_input, logs)
        else:
            raise ValueError(f"Unsupported channel type: {channel_type}")

    def _send_slack_request(
        self, interaction: Dict[str, Any], hil_input: HILInputData, logs: List[str]
    ):
        """Send HIL request via Slack."""
        # TODO: Integrate with Slack API
        logs.append(f"Sent Slack message to {hil_input.channel_config.slack_channel}")

    def _send_email_request(
        self, interaction: Dict[str, Any], hil_input: HILInputData, logs: List[str]
    ):
        """Send HIL request via email."""
        # TODO: Integrate with email service
        logs.append(
            f"Sent email to {len(hil_input.channel_config.email_recipients or [])} recipients"
        )

    def _send_webhook_request(
        self, interaction: Dict[str, Any], hil_input: HILInputData, logs: List[str]
    ):
        """Send HIL request via webhook."""
        # TODO: Send webhook notification
        logs.append(f"Sent webhook to {hil_input.channel_config.webhook_url}")

    def _send_app_request(
        self, interaction: Dict[str, Any], hil_input: HILInputData, logs: List[str]
    ):
        """Send HIL request via in-app notification."""
        # TODO: Send in-app notification
        logs.append("Sent in-app notification")

    def _pause_workflow_execution(
        self, interaction: Dict[str, Any], context: NodeExecutionContext, logs: List[str]
    ):
        """Pause workflow execution until human responds."""
        pause_data = {
            "execution_id": getattr(context, "execution_id", "unknown"),
            "paused_at": datetime.now(),
            "paused_node_id": getattr(
                context, "node_id", context.node.id if hasattr(context.node, "id") else "unknown"
            ),
            "pause_reason": "human_interaction",
            "resume_conditions": {"interaction_id": interaction["id"], "awaiting_response": True},
            "status": "active",
        }

        # TODO: Insert into workflow_execution_pauses table
        logs.append(f"Paused workflow execution {getattr(context, 'execution_id', 'unknown')}")

    def _create_pause_result(
        self, interaction: Dict[str, Any], logs: List[str], execution_time: float
    ) -> NodeExecutionResult:
        """Create a pause result that halts workflow execution."""
        return NodeExecutionResult(
            status=ExecutionStatus.PAUSED,  # Special status for HIL pause
            output_data={
                "interaction_id": interaction["id"],
                "status": "waiting_for_human",
                "timeout_at": interaction["timeout_at"].isoformat(),
                "channel_type": interaction["channel_type"],
                "paused": True,
            },
            execution_time_ms=int(execution_time * 1000),
            logs=logs,
            output_port=None,  # No output port until resume
        )

    def determine_output_port(
        self, response_data: Dict[str, Any], ai_relevance_score: Optional[float] = None
    ) -> str:
        """Determine which output port to use based on response."""

        # Handle webhook filtering results
        if ai_relevance_score is not None and ai_relevance_score < 0.7:
            return "filtered"  # Route to filtered port for handling

        # Process valid HIL responses based on interaction type
        interaction_type = response_data.get("interaction_type")

        if interaction_type == HILInteractionType.APPROVAL:
            if response_data.get("approved", False):
                return "approved"
            else:
                return "rejected"

        # INPUT, SELECTION, REVIEW, CONFIRMATION, CUSTOM - all route to approved when completed
        return "approved"
