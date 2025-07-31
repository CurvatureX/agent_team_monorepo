"""
External Action Node Executor.

Handles external action operations for integrating with third-party systems
like GitHub, Google Calendar, Trello, Slack, etc.
"""

import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from .base import BaseNodeExecutor, ExecutionStatus, NodeExecutionContext, NodeExecutionResult

try:
    from shared.node_specs import node_spec_registry
    from shared.node_specs.base import NodeSpec
except ImportError:
    node_spec_registry = None
    NodeSpec = None


class ExternalActionNodeExecutor(BaseNodeExecutor):
    """Executor for EXTERNAL_ACTION_NODE type."""

    def _get_node_spec(self) -> Optional[NodeSpec]:
        """Get the node specification for external action nodes."""
        if node_spec_registry:
            # Return the API_CALL spec as default (most commonly used)
            return node_spec_registry.get_spec("EXTERNAL_ACTION_NODE", "API_CALL")
        return None

    def get_supported_subtypes(self) -> List[str]:
        """Get supported external action subtypes."""
        return [
            "GITHUB",
            "GOOGLE_CALENDAR",
            "TRELLO",
            "EMAIL",
            "SLACK",
            "API_CALL",
            "WEBHOOK",
            "NOTIFICATION",
        ]

    def validate(self, node: Any) -> List[str]:
        """Validate external action node configuration."""
        errors = []

        if not node.subtype:
            errors.append("External action subtype is required")
            return errors

        subtype = node.subtype

        if subtype == "GITHUB":
            errors.extend(self._validate_required_parameters(node, ["action", "repository"]))

        elif subtype == "GOOGLE_CALENDAR":
            errors.extend(self._validate_required_parameters(node, ["action", "calendar_id"]))

        elif subtype == "TRELLO":
            errors.extend(self._validate_required_parameters(node, ["action", "board_id"]))

        elif subtype == "EMAIL":
            errors.extend(self._validate_required_parameters(node, ["action"]))
            if node.parameters.get("action") == "send":
                errors.extend(self._validate_required_parameters(node, ["recipients", "subject"]))

        elif subtype == "SLACK":
            errors.extend(self._validate_required_parameters(node, ["action", "channel"]))

        elif subtype == "API_CALL":
            errors.extend(self._validate_required_parameters(node, ["method", "url"]))
            method = node.parameters.get("method", "").upper()
            if method not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                errors.append(f"Invalid HTTP method: {method}")

        elif subtype == "WEBHOOK":
            errors.extend(self._validate_required_parameters(node, ["url", "payload"]))

        elif subtype == "NOTIFICATION":
            errors.extend(self._validate_required_parameters(node, ["type", "message", "target"]))
            notification_type = node.parameters.get("type", "")
            if notification_type not in ["push", "sms", "email", "in_app"]:
                errors.append(f"Invalid notification type: {notification_type}")

        return errors

    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute external action node."""
        start_time = time.time()
        logs = []

        try:
            subtype = context.node.subtype
            logs.append(f"Executing external action node with subtype: {subtype}")

            if subtype == "GITHUB":
                return self._execute_github_action(context, logs, start_time)
            elif subtype == "GOOGLE_CALENDAR":
                return self._execute_google_calendar_action(context, logs, start_time)
            elif subtype == "TRELLO":
                return self._execute_trello_action(context, logs, start_time)
            elif subtype == "EMAIL":
                return self._execute_email_action(context, logs, start_time)
            elif subtype == "SLACK":
                return self._execute_slack_action(context, logs, start_time)
            elif subtype == "API_CALL":
                return self._execute_api_call_action(context, logs, start_time)
            elif subtype == "WEBHOOK":
                return self._execute_webhook_action(context, logs, start_time)
            elif subtype == "NOTIFICATION":
                return self._execute_notification_action(context, logs, start_time)
            else:
                return self._create_error_result(
                    f"Unsupported external action subtype: {subtype}",
                    execution_time=time.time() - start_time,
                    logs=logs,
                )

        except Exception as e:
            return self._create_error_result(
                f"Error executing external action: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs,
            )

    def _execute_github_action(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute GitHub action."""
        action = context.get_parameter("action")
        repository = context.get_parameter("repository")

        logs.append(f"GitHub action: {action} on repository: {repository}")

        # Mock implementation - replace with actual GitHub API calls
        output_data = {
            "provider": "github",
            "action": action,
            "repository": repository,
            "result": f"Mock GitHub {action} result",
            "executed_at": datetime.now().isoformat(),
        }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_google_calendar_action(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute Google Calendar action."""
        action = context.get_parameter("action")
        calendar_id = context.get_parameter("calendar_id")

        logs.append(f"Google Calendar action: {action} on calendar: {calendar_id}")

        # Mock implementation - replace with actual Google Calendar API calls
        output_data = {
            "provider": "google_calendar",
            "action": action,
            "calendar_id": calendar_id,
            "result": f"Mock Google Calendar {action} result",
            "executed_at": datetime.now().isoformat(),
        }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_trello_action(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute Trello action."""
        action = context.get_parameter("action")
        board_id = context.get_parameter("board_id")

        logs.append(f"Trello action: {action} on board: {board_id}")

        # Mock implementation - replace with actual Trello API calls
        output_data = {
            "provider": "trello",
            "action": action,
            "board_id": board_id,
            "result": f"Mock Trello {action} result",
            "executed_at": datetime.now().isoformat(),
        }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_email_action(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute email action."""
        action = context.get_parameter("action")

        logs.append(f"Email action: {action}")

        # Mock implementation - replace with actual email API calls
        output_data = {
            "provider": "email",
            "action": action,
            "result": f"Mock email {action} result",
            "executed_at": datetime.now().isoformat(),
        }

        if action == "send":
            recipients = context.get_parameter("recipients", [])
            subject = context.get_parameter("subject", "")
            output_data.update({"recipients": recipients, "subject": subject})

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_slack_action(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute Slack action."""
        action = context.get_parameter("action")
        channel = context.get_parameter("channel")

        logs.append(f"Slack action: {action} in channel: {channel}")

        # Mock implementation - replace with actual Slack API calls
        output_data = {
            "provider": "slack",
            "action": action,
            "channel": channel,
            "result": f"Mock Slack {action} result",
            "executed_at": datetime.now().isoformat(),
        }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_api_call_action(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute generic API call action."""
        method = context.get_parameter("method", "GET").upper()
        url = context.get_parameter("url")
        headers = context.get_parameter("headers", {})

        logs.append(f"API call: {method} {url}")

        # Mock implementation - replace with actual HTTP requests
        output_data = {
            "method": method,
            "url": url,
            "headers": headers,
            "status_code": 200,
            "response": f"Mock {method} response from {url}",
            "executed_at": datetime.now().isoformat(),
        }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_webhook_action(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute webhook action."""
        url = context.get_parameter("url")
        payload = context.get_parameter("payload", {})

        logs.append(f"Webhook: POST to {url}")

        # Mock implementation - replace with actual webhook sending
        output_data = {
            "url": url,
            "payload": payload,
            "status_code": 200,
            "response": "Mock webhook sent successfully",
            "executed_at": datetime.now().isoformat(),
        }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_notification_action(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute notification action."""
        notification_type = context.get_parameter("type")
        message = context.get_parameter("message")
        target = context.get_parameter("target")

        logs.append(f"Notification: {notification_type} to {target}")

        # Mock implementation - replace with actual notification service
        output_data = {
            "type": notification_type,
            "message": message,
            "target": target,
            "status": "sent",
            "result": f"Mock {notification_type} notification sent",
            "executed_at": datetime.now().isoformat(),
        }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )
