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

from .base import BaseNodeExecutor, ExecutionStatus, NodeExecutionContext, NodeExecutionResult

try:
    from shared.node_specs import node_spec_registry
    from shared.node_specs.base import NodeSpec
except ImportError:
    node_spec_registry = None
    NodeSpec = None


class TriggerNodeExecutor(BaseNodeExecutor):
    """Executor for TRIGGER_NODE type."""

    def _get_node_spec(self) -> Optional[NodeSpec]:
        """Get the node specification for trigger nodes."""
        if node_spec_registry:
            # Return the MANUAL spec as default (most commonly used)
            return node_spec_registry.get_spec("TRIGGER_NODE", "TRIGGER_MANUAL")
        return None

    def get_supported_subtypes(self) -> List[str]:
        """Get supported trigger subtypes."""
        return [
            "TRIGGER_MANUAL",
            "TRIGGER_WEBHOOK",
            "TRIGGER_CRON",
            "TRIGGER_CHAT",
            "TRIGGER_EMAIL",
            "TRIGGER_FORM",
            "TRIGGER_CALENDAR",
        ]

    def validate(self, node: Any) -> List[str]:
        """Validate trigger node configuration."""
        errors = []

        if not node.subtype:
            errors.append("Trigger subtype is required")
            return errors

        subtype = node.subtype

        if subtype == "TRIGGER_WEBHOOK":
            errors.extend(self._validate_required_parameters(node, ["method", "path"]))
            method = node.parameters.get("method", "").upper()
            if method not in ["GET", "POST", "PUT", "DELETE"]:
                errors.append(f"Invalid HTTP method: {method}")

        elif subtype == "TRIGGER_CRON":
            errors.extend(self._validate_required_parameters(node, ["cron_expression"]))
            cron_expr = node.parameters.get("cron_expression", "")
            if not self._is_valid_cron(cron_expr):
                errors.append(f"Invalid cron expression: {cron_expr}")

        elif subtype == "TRIGGER_EMAIL":
            errors.extend(self._validate_required_parameters(node, ["email_filter"]))

        elif subtype == "TRIGGER_CALENDAR":
            errors.extend(self._validate_required_parameters(node, ["calendar_id"]))

        return errors

    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute trigger node."""
        start_time = time.time()
        logs = []

        try:
            subtype = context.node.subtype
            logs.append(f"Executing trigger node with subtype: {subtype}")

            if subtype == "TRIGGER_MANUAL":
                return self._execute_manual_trigger(context, logs, start_time)
            elif subtype == "TRIGGER_WEBHOOK":
                return self._execute_webhook_trigger(context, logs, start_time)
            elif subtype == "TRIGGER_CRON":
                return self._execute_cron_trigger(context, logs, start_time)
            elif subtype == "TRIGGER_CHAT":
                return self._execute_chat_trigger(context, logs, start_time)
            elif subtype == "TRIGGER_EMAIL":
                return self._execute_email_trigger(context, logs, start_time)
            elif subtype == "TRIGGER_FORM":
                return self._execute_form_trigger(context, logs, start_time)
            elif subtype == "TRIGGER_CALENDAR":
                return self._execute_calendar_trigger(context, logs, start_time)
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
        require_confirmation = context.get_parameter("require_confirmation", False)

        logs.append(f"Manual trigger executed, confirmation required: {require_confirmation}")

        output_data = {
            "trigger_type": "manual",
            "triggered_at": datetime.now().isoformat(),
            "require_confirmation": require_confirmation,
            "input_data": context.input_data,
            "user_id": context.metadata.get("user_id"),
            "session_id": context.metadata.get("session_id"),
        }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_webhook_trigger(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute webhook trigger."""
        method = context.get_parameter("method", "POST").upper()
        path = context.get_parameter("path", "/webhook")
        authentication = context.get_parameter("authentication", "none")

        logs.append(f"Webhook trigger: {method} {path}, auth: {authentication}")

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

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_cron_trigger(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute cron trigger."""
        cron_expression = context.get_parameter("cron_expression", "0 9 * * MON")
        timezone = context.get_parameter("timezone", "UTC")

        logs.append(f"Cron trigger: {cron_expression} ({timezone})")

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

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_chat_trigger(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute chat trigger."""
        chat_platform = context.get_parameter("chat_platform", "general")
        message_filter = context.get_parameter("message_filter", "")

        logs.append(f"Chat trigger: {chat_platform}, filter: {message_filter}")

        # Extract chat data from input
        chat_data = context.input_data.get("chat_data", {})

        output_data = {
            "trigger_type": "chat",
            "chat_platform": chat_platform,
            "message_filter": message_filter,
            "chat_data": chat_data,
            "message": chat_data.get("message", ""),
            "user": chat_data.get("user", ""),
            "channel": chat_data.get("channel", ""),
            "triggered_at": datetime.now().isoformat(),
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

        logs.append(f"Email trigger: {email_provider}, filter: {email_filter}")

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

    def _execute_form_trigger(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute form trigger."""
        form_id = context.get_parameter("form_id", "")
        form_fields = context.get_parameter("form_fields", [])

        logs.append(f"Form trigger: {form_id}, fields: {form_fields}")

        # Extract form data from input
        form_data = context.input_data.get("form_data", {})

        output_data = {
            "trigger_type": "form",
            "form_id": form_id,
            "form_fields": form_fields,
            "form_data": form_data,
            "submitted_by": form_data.get("submitted_by", ""),
            "submission_time": form_data.get("submission_time", ""),
            "triggered_at": datetime.now().isoformat(),
        }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_calendar_trigger(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute calendar trigger."""
        calendar_id = context.get_parameter("calendar_id", "primary")
        event_filter = context.get_parameter("event_filter", "")

        logs.append(f"Calendar trigger: {calendar_id}, filter: {event_filter}")

        # Extract calendar data from input
        calendar_data = context.input_data.get("calendar_data", {})

        output_data = {
            "trigger_type": "calendar",
            "calendar_id": calendar_id,
            "event_filter": event_filter,
            "calendar_data": calendar_data,
            "events": calendar_data.get("events", []),
            "event_count": len(calendar_data.get("events", [])),
            "triggered_at": datetime.now().isoformat(),
        }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _is_valid_cron(self, cron_expression: str) -> bool:
        """Validate cron expression."""
        try:
            croniter(cron_expression)
            return True
        except Exception:
            return False
