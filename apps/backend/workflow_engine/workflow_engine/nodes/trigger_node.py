"""
Trigger Node Executor.

Handles trigger operations like manual triggers, webhooks, cron schedules, etc.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from croniter import croniter

from shared.models import NodeType
from shared.models.node_enums import TriggerSubtype
from shared.node_specs import node_spec_registry
from shared.node_specs.base import NodeSpec

from .base import BaseNodeExecutor, ExecutionStatus, NodeExecutionContext, NodeExecutionResult


class TriggerNodeExecutor(BaseNodeExecutor):
    """Executor for TRIGGER_NODE type."""

    def _get_node_spec(self) -> Optional[NodeSpec]:
        """Get the node specification for trigger nodes."""
        if node_spec_registry and self._subtype:
            # Use unified format - remove TRIGGER_ prefix if present for compatibility
            normalized_subtype = self._subtype
            if self._subtype.startswith("TRIGGER_"):
                normalized_subtype = self._subtype[8:]  # Remove "TRIGGER_" prefix
            # Return the specific spec for current subtype using unified format
            return node_spec_registry.get_spec(NodeType.TRIGGER.value, normalized_subtype)
        return None

    def get_supported_subtypes(self) -> List[str]:
        """Get supported trigger subtypes."""
        # Use unified enum values - support both legacy and unified formats
        unified_subtypes = [subtype.value for subtype in TriggerSubtype]
        legacy_subtypes = [f"TRIGGER_{subtype.value}" for subtype in TriggerSubtype]
        return unified_subtypes + legacy_subtypes

    def validate(self, node: Any) -> List[str]:
        """Validate trigger node configuration using spec-based validation."""
        # First use the base class validation which includes spec validation
        errors = super().validate(node)

        # If spec validation passed, we're done
        if not errors and self.spec:
            return errors

        # Fallback if spec not available
        if not node.subtype:
            errors.append("Trigger subtype is required")
            return errors

        if node.subtype not in self.get_supported_subtypes():
            errors.append(f"Unsupported trigger subtype: {node.subtype}")

        return errors

    def _validate_legacy(self, node: Any) -> List[str]:
        """Legacy validation for backward compatibility."""
        errors = []

        if not hasattr(node, "subtype"):
            return errors

        subtype = node.subtype

        if subtype == f"TRIGGER_{TriggerSubtype.WEBHOOK.value}":
            # Note: The spec uses webhook_path and http_method, not method and path
            if hasattr(node, "parameters"):
                http_method = node.parameters.get("http_method", "").upper()
                if http_method and http_method not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    errors.append(f"Invalid HTTP method: {http_method}")

        elif subtype == f"TRIGGER_{TriggerSubtype.CRON.value}":
            errors.extend(self._validate_required_parameters(node, ["cron_expression"]))
            if hasattr(node, "parameters"):
                cron_expr = node.parameters.get("cron_expression", "")
                if cron_expr and not self._is_valid_cron(cron_expr):
                    errors.append(f"Invalid cron expression: {cron_expr}")

        return errors

    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute trigger node."""
        start_time = time.time()
        logs = []

        try:
            subtype = context.node.subtype
            self.logger.info(f"Executing trigger node with subtype: {subtype}")

            if subtype == TriggerSubtype.MANUAL.value:
                return self._execute_manual_trigger(context, logs, start_time)
            elif subtype == TriggerSubtype.WEBHOOK.value:
                return self._execute_webhook_trigger(context, logs, start_time)
            elif subtype == TriggerSubtype.CRON.value:
                return self._execute_cron_trigger(context, logs, start_time)
            elif subtype == TriggerSubtype.EMAIL.value:
                return self._execute_email_trigger(context, logs, start_time)
            elif subtype == TriggerSubtype.GITHUB.value:
                return self._execute_github_trigger(context, logs, start_time)
            elif subtype == TriggerSubtype.SLACK.value:
                return self._execute_slack_trigger(context, logs, start_time)
            else:
                return self._create_error_result(
                    f"Unsupported trigger subtype: {subtype}",
                    execution_time=time.time() - start_time,
                    logs=logs,
                )

        except Exception as e:
            return self._create_error_result(
                f"Error executing trigger: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs,
            )

    def _execute_manual_trigger(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute manual trigger."""
        logs.append("Executing manual trigger")
        # Use spec-based parameter retrieval
        trigger_name = self.get_parameter_with_spec(context, "trigger_name")
        description = self.get_parameter_with_spec(context, "description")

        logs.append(f"Manual trigger '{trigger_name}' activated")
        self.logger.info(f"Manual trigger executed")

        # Extract content from input data for standard communication format
        content = self._extract_trigger_content(context.input_data, "manual")

        # Use standard communication format
        output_data = {
            "content": content,
            "metadata": {
                "trigger_type": "manual",
                "trigger_name": trigger_name,
                "description": description,
                "triggered_at": datetime.now().isoformat(),
                "user_id": context.metadata.get("user_id"),
                "session_id": context.metadata.get("session_id"),
                "input_data": context.input_data,
            },
            "format_type": "text",
            "source_node": context.node.id if hasattr(context, "node") and context.node else None,
            "timestamp": datetime.now().isoformat(),
        }

        logs.append("Manual trigger completed successfully")
        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_webhook_trigger(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute webhook trigger."""
        logs.append("Processing webhook trigger")
        method = context.get_parameter("method", "POST").upper()
        path = context.get_parameter("path", "/webhook")
        authentication = context.get_parameter("authentication", "none")

        self.logger.info(f"Webhook trigger: {method} {path}, auth: {authentication}")

        # Extract webhook data from input
        webhook_data = context.input_data.get("webhook_data", {})

        output_data = {
            "trigger_type": "webhook",
            "method": method,
            "path": path,
            "authentication": authentication,
            "webhook_data": webhook_data,
            "headers": context.input_data.get("headers", {}),
            "query_params": context.input_data.get("query_params", {}),
            "body": context.input_data.get("body", {}),
            "triggered_at": datetime.now().isoformat(),
        }

        logs.append("Webhook trigger processed successfully")
        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_cron_trigger(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute cron trigger."""
        logs.append("Executing cron trigger")
        cron_expression = context.get_parameter("cron_expression", "0 9 * * MON")
        timezone = context.get_parameter("timezone", "UTC")

        self.logger.info(f"Cron trigger: {cron_expression} ({timezone})")

        # Check if it's time to trigger
        now = datetime.now()
        cron_iter = croniter(cron_expression, now)
        next_run = cron_iter.get_next(datetime)

        output_data = {
            "trigger_type": "cron",
            "cron_expression": cron_expression,
            "timezone": timezone,
            "current_time": now.isoformat(),
            "next_run": next_run.isoformat(),
            "should_trigger": now >= next_run,
            "triggered_at": datetime.now().isoformat(),
        }

        logs.append(f"Cron trigger scheduled: {cron_expression}")
        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_github_trigger(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute GitHub trigger."""
        repository = context.get_parameter("repository", "")
        event_filter = context.get_parameter("event_filter", "")
        webhook_secret = context.get_parameter("webhook_secret", "")

        self.logger.info(f"GitHub trigger: {repository}, filter: {event_filter}")

        # Extract GitHub content for standard communication format
        content = self._extract_trigger_content(context.input_data, "github")

        # Extract GitHub webhook data from input
        github_data = context.input_data.get("github_data", {})

        # Use standard communication format
        output_data = {
            "content": content,
            "metadata": {
                "trigger_type": "github",
                "repository": repository,
                "event_filter": event_filter,
                "github_data": github_data,
                "event": github_data.get("event", ""),
                "action": github_data.get("action", ""),
                "sender": github_data.get("sender", {}),
                "triggered_at": datetime.now().isoformat(),
            },
            "format_type": "text",
            "source_node": context.node.id if hasattr(context, "node") and context.node else None,
            "timestamp": datetime.now().isoformat(),
        }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_email_trigger(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute email trigger."""
        email_filter = context.get_parameter("email_filter", "")
        email_provider = context.get_parameter("email_provider", "gmail")

        self.logger.info(f"Email trigger: {email_provider}, filter: {email_filter}")

        # Extract email data from input
        email_data = context.input_data.get("email_data", {})

        output_data = {
            "trigger_type": "email",
            "email_provider": email_provider,
            "email_filter": email_filter,
            "email_data": email_data,
            "subject": email_data.get("subject", ""),
            "sender": email_data.get("sender", ""),
            "recipients": email_data.get("recipients", []),
            "body": email_data.get("body", ""),
            "triggered_at": datetime.now().isoformat(),
        }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_slack_trigger(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute Slack trigger."""
        channel = context.get_parameter("channel", "")
        message_filter = context.get_parameter("message_filter", "")
        bot_token = context.get_parameter("bot_token", "")

        self.logger.info(f"Slack trigger: {channel}, filter: {message_filter}")

        # Extract Slack message content for standard communication format
        content = self._extract_trigger_content(context.input_data, "slack")

        # Extract Slack webhook data from input
        slack_data = context.input_data.get("slack_data", {})

        # Use standard communication format
        output_data = {
            "content": content,
            "metadata": {
                "trigger_type": "slack",
                "channel": channel,
                "message_filter": message_filter,
                "slack_data": slack_data,
                "text": slack_data.get("text", ""),
                "user": slack_data.get("user", ""),
                "event_timestamp": slack_data.get("timestamp", ""),
                "triggered_at": datetime.now().isoformat(),
            },
            "format_type": "text",
            "source_node": context.node.id if hasattr(context, "node") and context.node else None,
            "timestamp": datetime.now().isoformat(),
        }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _extract_trigger_content(self, input_data: Dict[str, Any], trigger_type: str) -> str:
        """Extract meaningful content from trigger input data for standard communication format."""
        if not input_data:
            return f"Triggered by {trigger_type} event"

        # Handle different trigger types
        if trigger_type == "slack":
            # Extract Slack message content
            slack_data = input_data.get("slack_data", {})
            if slack_data and "text" in slack_data:
                return slack_data["text"]

            # Check for payload structure (webhook format)
            if "payload" in input_data:
                payload = input_data["payload"]
                if isinstance(payload, dict):
                    # Slack event format
                    if "event" in payload and "text" in payload["event"]:
                        return payload["event"]["text"]

            # Check direct text field
            if "text" in input_data:
                return input_data["text"]

        elif trigger_type == "github":
            # Extract GitHub event content
            github_data = input_data.get("github_data", {})
            if github_data:
                # Try to extract meaningful content from GitHub event
                action = github_data.get("action", "")
                event_type = github_data.get("event", "")
                if action and event_type:
                    return f"GitHub {event_type} event: {action}"
                elif event_type:
                    return f"GitHub {event_type} event"

        elif trigger_type == "email":
            # Extract email content
            email_data = input_data.get("email_data", {})
            if email_data:
                subject = email_data.get("subject", "")
                body = email_data.get("body", "")
                if subject:
                    return f"Email: {subject}"
                elif body:
                    return f"Email content: {body[:100]}..."  # Truncate long content

        elif trigger_type == "webhook":
            # Extract webhook content
            if "body" in input_data:
                body = input_data["body"]
                if isinstance(body, dict):
                    # Look for common message fields
                    for field in ["message", "text", "content", "data"]:
                        if field in body and body[field]:
                            return str(body[field])
                elif isinstance(body, str):
                    return body

        elif trigger_type == "manual":
            # Extract manual trigger content
            if "message" in input_data:
                return str(input_data["message"])
            elif "text" in input_data:
                return str(input_data["text"])

        # Fallback: try to find any meaningful text content
        for field in ["message", "text", "content", "data", "payload"]:
            if field in input_data and input_data[field]:
                value = input_data[field]
                if isinstance(value, str):
                    return value
                elif isinstance(value, dict) and "text" in value:
                    return str(value["text"])

        # Final fallback
        return f"Triggered by {trigger_type} event"

    def _is_valid_cron(self, cron_expression: str) -> bool:
        """Validate cron expression."""
        try:
            croniter(cron_expression)
            return True
        except Exception:
            return False
