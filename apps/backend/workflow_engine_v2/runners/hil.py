"""Human-in-the-loop runner for workflow_engine_v2 with complete HIL functionality."""

from __future__ import annotations

import logging
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Use absolute imports
from shared.models import TriggerInfo
from shared.models.human_in_loop import HILChannelType, HILInteractionType
from shared.models.workflow import Node
from workflow_engine_v2.runners.base import NodeRunner
from workflow_engine_v2.services.hil_service import HILWorkflowServiceV2

logger = logging.getLogger(__name__)


class HILRunner(NodeRunner):
    """Human-in-the-loop runner with complete workflow pause/resume functionality."""

    def __init__(self):
        self.hil_service = HILWorkflowServiceV2()

    def run(self, node: Node, inputs: Dict[str, Any], trigger: TriggerInfo) -> Dict[str, Any]:
        """
        Execute HIL node with complete workflow pause and interaction creation.

        This implementation creates a real HIL interaction, stores it in the database,
        and returns the appropriate signals for workflow pause management.
        """
        try:
            # Extract HIL parameters from node configuration
            hil_config = self._extract_hil_configuration(node)

            # Validate required parameters
            validation_error = self._validate_hil_parameters(hil_config)
            if validation_error:
                return validation_error

            # Extract execution context
            ctx = inputs.get("_ctx")
            if not ctx:
                return self._error_response(
                    "Missing execution context", "missing_execution_context"
                )

            # Extract user context
            user_id = self._extract_user_id(trigger, ctx)
            if not user_id:
                return self._error_response(
                    "User ID required for HIL interactions", "missing_user_id"
                )

            # Create HIL interaction in database
            interaction_id = self._create_hil_interaction(
                node, inputs, trigger, ctx, hil_config, user_id
            )

            if not interaction_id:
                return self._error_response(
                    "Failed to create HIL interaction", "interaction_creation_failed"
                )

            workflow_log_id = "unknown"
            if ctx and hasattr(ctx, "workflow"):
                wf_obj = getattr(ctx, "workflow")
                workflow_log_id = (
                    getattr(wf_obj, "workflow_id", None)
                    or getattr(getattr(wf_obj, "metadata", None), "id", None)
                    or getattr(wf_obj, "id", None)
                    or "unknown"
                )

            logger.info(
                f"Created HIL interaction {interaction_id} for workflow {workflow_log_id}"
            )

            # Return workflow pause signals
            timeout_at = (
                datetime.utcnow() + timedelta(seconds=hil_config["timeout_seconds"])
            ).isoformat()
            payload = {
                "status": "waiting_for_human",
                "interaction_id": interaction_id,
                "interaction_type": hil_config["interaction_type"],
                "channel_type": hil_config["channel_type"],
                "timeout_at": timeout_at,
                "message": hil_config.get("message", "Human input required"),
                "timeout_action": hil_config.get("timeout_action", "fail"),
            }

            return {
                "_hil_wait": True,
                "_hil_interaction_id": interaction_id,
                "_hil_timeout_seconds": hil_config["timeout_seconds"],
                "_hil_node_id": node.id,
                "main": payload,
                "result": payload,
            }

        except Exception as e:
            logger.error(f"HIL runner error: {str(e)}")
            return self._error_response(f"HIL execution failed: {str(e)}", "hil_execution_error")

    def _extract_hil_configuration(self, node: Node) -> Dict[str, Any]:
        """Extract and normalize HIL configuration from node."""
        config = node.configurations.copy()

        # Set defaults
        hil_config = {
            "interaction_type": config.get("interaction_type", "approval"),
            "channel_type": config.get("channel_type", "slack"),
            "timeout_seconds": int(config.get("timeout_seconds", 3600)),  # 1 hour default
            "title": config.get("title", "Human Input Required"),
            "description": config.get("description", "Please provide your response"),
            "message": config.get("message"),
            "approval_options": config.get("approval_options", ["approve", "reject"]),
            "input_fields": config.get("input_fields", []),
            "selection_options": config.get("selection_options", []),
            "review_criteria": config.get("review_criteria", []),
            "template_variables": config.get("template_variables", {}),
            "response_messages": config.get("response_messages", {}),
            "timeout_action": config.get(
                "timeout_action", "fail"
            ),  # fail, continue, default_response
            "channel_config": config.get("channel_config", {}),
            "priority": config.get("priority", "normal"),
        }

        channel_aliases = {"in_app": "app"}
        channel_key = str(hil_config["channel_type"]).lower()
        hil_config["channel_type"] = channel_aliases.get(channel_key, channel_key)

        return hil_config

    def _validate_hil_parameters(self, hil_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate HIL configuration parameters."""
        errors = []

        # Validate interaction type
        valid_interaction_types = ["approval", "input", "selection", "review"]
        if hil_config["interaction_type"] not in valid_interaction_types:
            errors.append(
                f"Invalid interaction_type: {hil_config['interaction_type']}. Must be one of: {valid_interaction_types}"
            )

        # Validate channel type
        valid_channel_types = ["slack", "email", "webhook", "in_app", "app"]
        if hil_config["channel_type"] not in valid_channel_types:
            errors.append(
                f"Invalid channel_type: {hil_config['channel_type']}. Must be one of: {valid_channel_types}"
            )

        # Validate timeout
        if hil_config["timeout_seconds"] < 60:  # Minimum 1 minute
            errors.append("timeout_seconds must be at least 60 seconds")

        if hil_config["timeout_seconds"] > 86400:  # Maximum 24 hours
            errors.append("timeout_seconds must not exceed 86400 seconds (24 hours)")

        # Validate interaction-specific requirements
        if hil_config["interaction_type"] == "input" and not hil_config["input_fields"]:
            errors.append("input_fields required for input interaction type")

        if hil_config["interaction_type"] == "selection" and not hil_config["selection_options"]:
            errors.append("selection_options required for selection interaction type")

        if errors:
            return self._error_response(
                "HIL configuration validation failed",
                "invalid_configuration",
                {"validation_errors": errors},
            )

        return None

    def _extract_user_id(self, trigger: TriggerInfo, ctx: Any) -> Optional[str]:
        """Extract user ID from trigger or execution context."""
        # Try trigger first
        if trigger and hasattr(trigger, "user_id") and trigger.user_id:
            return trigger.user_id

        # Try execution context
        if (
            ctx
            and hasattr(ctx, "execution")
            and ctx.execution
            and hasattr(ctx.execution, "user_id")
        ):
            return ctx.execution.user_id

        # Try workflow context
        if ctx and hasattr(ctx, "workflow") and ctx.workflow and hasattr(ctx.workflow, "user_id"):
            return ctx.workflow.user_id

        return None

    def _create_hil_interaction(
        self,
        node: Node,
        inputs: Dict[str, Any],
        trigger: TriggerInfo,
        ctx: Any,
        hil_config: Dict[str, Any],
        user_id: str,
    ) -> Optional[str]:
        """Create HIL interaction in database via HIL service."""
        try:
            # Prepare interaction data
            try:
                interaction_type = HILInteractionType(hil_config["interaction_type"])
            except ValueError:
                interaction_type = HILInteractionType.APPROVAL

            channel_value = hil_config["channel_type"]
            try:
                channel_type = HILChannelType(channel_value)
            except ValueError:
                # Allow alias 'app'
                if channel_value == "app":
                    channel_type = HILChannelType.APP
                else:
                    raise

            # Build request data
            workflow_obj = getattr(ctx, "workflow", None)
            workflow_id = None
            if workflow_obj is not None:
                workflow_id = getattr(workflow_obj, "workflow_id", None)
                if not workflow_id and hasattr(workflow_obj, "metadata"):
                    workflow_id = getattr(workflow_obj.metadata, "id", None)
                if not workflow_id and hasattr(workflow_obj, "id"):
                    workflow_id = workflow_obj.id

            execution_obj = getattr(ctx, "execution", None)
            execution_id = None
            if execution_obj is not None:
                execution_id = getattr(execution_obj, "execution_id", None)
                if not execution_id and hasattr(execution_obj, "id"):
                    execution_id = execution_obj.id

            request_data = {
                "title": hil_config["title"],
                "description": hil_config["description"],
                "message": hil_config.get("message"),
                "approval_options": hil_config.get("approval_options"),
                "input_fields": hil_config.get("input_fields"),
                "selection_options": hil_config.get("selection_options"),
                "review_criteria": hil_config.get("review_criteria"),
                "template_variables": hil_config.get("template_variables", {}),
                "response_messages": hil_config.get("response_messages", {}),
                "timeout_action": hil_config["timeout_action"],
                "channel_config": hil_config.get("channel_config", {}),
                "node_configurations": node.configurations,
                "input_data": inputs.get("main", {}),
                "workflow_context": {
                    "workflow_id": workflow_id,
                    "execution_id": execution_id,
                    "node_id": node.id,
                    "node_name": node.name,
                    "node_description": node.description,
                },
            }

            # Create interaction using HIL service
            interaction_id = self.hil_service.create_interaction_sync(
                workflow_id=workflow_id or str(uuid.uuid4()),
                execution_id=execution_id or str(uuid.uuid4()),
                node_id=node.id,
                user_id=user_id,
                interaction_type=interaction_type,
                channel_type=channel_type,
                request_data=request_data,
                timeout_seconds=hil_config["timeout_seconds"],
                priority=hil_config.get("priority", "normal"),
            )

            return interaction_id

        except Exception as e:
            logger.error(f"Failed to create HIL interaction: {str(e)}")
            return None

    def _error_response(
        self, message: str, error_code: str, details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create structured error response."""
        error_data = {
            "error": True,
            "error_message": message,
            "error_code": error_code,
            "node_type": "HIL",
        }

        if details:
            error_data["error_details"] = details

        return error_data


__all__ = ["HILRunner"]
