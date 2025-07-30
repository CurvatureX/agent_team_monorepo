"""
Tool Node Executor.

Handles tool operations like MCP tools, calendar operations, email, etc.
"""

import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .base import BaseNodeExecutor, ExecutionStatus, NodeExecutionContext, NodeExecutionResult

try:
    from shared.node_specs import node_spec_registry
    from shared.node_specs.base import NodeSpec
except ImportError:
    node_spec_registry = None
    NodeSpec = None


class ToolNodeExecutor(BaseNodeExecutor):
    """Executor for TOOL_NODE type."""

    def _get_node_spec(self) -> Optional[NodeSpec]:
        """Get the node specification for tool nodes."""
        if node_spec_registry:
            # Return the MCP spec as default (most comprehensive)
            return node_spec_registry.get_spec("TOOL_NODE", "TOOL_GOOGLE_CALENDAR_MCP")
        return None

    def get_supported_subtypes(self) -> List[str]:
        """Get supported tool subtypes."""
        return [
            "TOOL_GOOGLE_CALENDAR_MCP",
            "TOOL_NOTION_MCP",
            "TOOL_CALENDAR",
            "TOOL_EMAIL",
            "TOOL_HTTP",
            "TOOL_CODE_EXECUTION",
        ]

    def validate(self, node: Any) -> List[str]:
        """Validate tool node configuration."""
        errors = []

        if not node.subtype:
            errors.append("Tool subtype is required")
            return errors

        subtype = node.subtype

        if subtype in ["TOOL_GOOGLE_CALENDAR_MCP", "TOOL_NOTION_MCP"]:
            errors.extend(self._validate_required_parameters(node, ["tool_name", "operation"]))

        elif subtype == "TOOL_CALENDAR":
            errors.extend(self._validate_required_parameters(node, ["calendar_id", "operation"]))
            operation = node.parameters.get("operation", "")
            if operation not in ["list_events", "create_event", "update_event", "delete_event"]:
                errors.append(f"Invalid calendar operation: {operation}")

        elif subtype == "TOOL_EMAIL":
            errors.extend(self._validate_required_parameters(node, ["operation"]))
            operation = node.parameters.get("operation", "")
            if operation not in ["send", "read", "search", "delete"]:
                errors.append(f"Invalid email operation: {operation}")

        elif subtype == "TOOL_HTTP":
            errors.extend(self._validate_required_parameters(node, ["method", "url"]))
            method = node.parameters.get("method", "").upper()
            if method not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                errors.append(f"Invalid HTTP method: {method}")

        elif subtype == "TOOL_CODE_EXECUTION":
            errors.extend(self._validate_required_parameters(node, ["code"]))
            language = node.parameters.get("language", "python")
            if language not in ["python", "javascript", "bash", "sql"]:
                errors.append(f"Unsupported code language: {language}")

        return errors

    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute tool node."""
        start_time = time.time()
        logs = []

        try:
            subtype = context.node.subtype
            logs.append(f"Executing tool node with subtype: {subtype}")

            if subtype in ["TOOL_GOOGLE_CALENDAR_MCP", "TOOL_NOTION_MCP"]:
                return self._execute_mcp_tool(context, logs, start_time)
            elif subtype == "TOOL_CALENDAR":
                return self._execute_calendar_tool(context, logs, start_time)
            elif subtype == "TOOL_EMAIL":
                return self._execute_email_tool(context, logs, start_time)
            elif subtype == "TOOL_HTTP":
                return self._execute_http_tool(context, logs, start_time)
            elif subtype == "TOOL_CODE_EXECUTION":
                return self._execute_code_tool(context, logs, start_time)
            else:
                return self._create_error_result(
                    f"Unsupported tool subtype: {subtype}",
                    execution_time=time.time() - start_time,
                    logs=logs,
                )

        except Exception as e:
            return self._create_error_result(
                f"Error executing tool: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs,
            )

    def _execute_mcp_tool(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute MCP tool."""
        tool_name = context.get_parameter("tool_name", "")
        operation = context.get_parameter("operation", "")
        parameters = context.get_parameter("parameters", {})

        logs.append(f"MCP tool: {tool_name}, operation: {operation}")

        # Mock MCP tool execution
        tool_result = {
            "tool_name": tool_name,
            "operation": operation,
            "parameters": parameters,
            "result": f"Mock result from {tool_name} tool",
            "executed_at": datetime.now().isoformat(),
        }

        output_data = {
            "tool_type": "mcp",
            "tool_name": tool_name,
            "operation": operation,
            "parameters": parameters,
            "result": tool_result,
            "success": True,
            "executed_at": datetime.now().isoformat(),
        }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_calendar_tool(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute calendar tool."""
        calendar_id = context.get_parameter("calendar_id", "primary")
        operation = context.get_parameter("operation", "list_events")
        start_date = context.get_parameter("start_date", "")
        end_date = context.get_parameter("end_date", "")

        logs.append(f"Calendar tool: {operation} on {calendar_id}")

        # Mock calendar operations
        if operation == "list_events":
            events = self._mock_list_events(calendar_id, start_date, end_date)
            result = {"events": events, "count": len(events)}
        elif operation == "create_event":
            event_data = context.get_parameter("event_data", {})
            result = self._mock_create_event(calendar_id, event_data)
        elif operation == "update_event":
            event_id = context.get_parameter("event_id", "")
            event_data = context.get_parameter("event_data", {})
            result = self._mock_update_event(calendar_id, event_id, event_data)
        elif operation == "delete_event":
            event_id = context.get_parameter("event_id", "")
            result = self._mock_delete_event(calendar_id, event_id)
        else:
            result = {"error": f"Unknown operation: {operation}"}

        output_data = {
            "tool_type": "calendar",
            "calendar_id": calendar_id,
            "operation": operation,
            "result": result,
            "success": "error" not in result,
            "executed_at": datetime.now().isoformat(),
        }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_email_tool(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute email tool."""
        operation = context.get_parameter("operation", "send")
        email_provider = context.get_parameter("email_provider", "gmail")

        logs.append(f"Email tool: {operation} via {email_provider}")

        # Mock email operations
        if operation == "send":
            to_recipients = context.get_parameter("to", [])
            subject = context.get_parameter("subject", "")
            body = context.get_parameter("body", "")
            result = self._mock_send_email(to_recipients, subject, body)
        elif operation == "read":
            query = context.get_parameter("query", "")
            result = self._mock_read_emails(query)
        elif operation == "search":
            search_query = context.get_parameter("search_query", "")
            result = self._mock_search_emails(search_query)
        elif operation == "delete":
            email_ids = context.get_parameter("email_ids", [])
            result = self._mock_delete_emails(email_ids)
        else:
            result = {"error": f"Unknown operation: {operation}"}

        output_data = {
            "tool_type": "email",
            "operation": operation,
            "email_provider": email_provider,
            "result": result,
            "success": "error" not in result,
            "executed_at": datetime.now().isoformat(),
        }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _execute_http_tool(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute HTTP tool."""
        method = context.get_parameter("method", "GET").upper()
        url = context.get_parameter("url", "")
        headers = context.get_parameter("headers", {})
        data = context.get_parameter("data", {})
        timeout = context.get_parameter("timeout", 30)

        logs.append(f"HTTP tool: {method} {url}")

        # Mock HTTP request
        mock_response = {
            "status_code": 200,
            "headers": {"content-type": "application/json"},
            "body": json.dumps({"message": "Mock HTTP response"}),
            "url": url,
            "method": method,
        }

        output_data = {
            "tool_type": "http",
            "method": method,
            "url": url,
            "headers": headers,
            "data": data,
            "response": mock_response,
            "success": True,
            "executed_at": datetime.now().isoformat(),
        }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )

    def _mock_list_events(
        self, calendar_id: str, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """Mock list calendar events."""
        return [
            {
                "id": "event_1",
                "title": "Team Meeting",
                "start": "2024-01-15T10:00:00Z",
                "end": "2024-01-15T11:00:00Z",
                "description": "Weekly team sync",
            },
            {
                "id": "event_2",
                "title": "Client Call",
                "start": "2024-01-15T14:00:00Z",
                "end": "2024-01-15T15:00:00Z",
                "description": "Project review",
            },
        ]

    def _mock_create_event(self, calendar_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock create calendar event."""
        return {
            "id": f"event_{int(time.time())}",
            "title": event_data.get("title", "New Event"),
            "start": event_data.get("start", ""),
            "end": event_data.get("end", ""),
            "created": True,
        }

    def _mock_update_event(
        self, calendar_id: str, event_id: str, event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mock update calendar event."""
        return {"id": event_id, "updated": True, "changes": event_data}

    def _mock_delete_event(self, calendar_id: str, event_id: str) -> Dict[str, Any]:
        """Mock delete calendar event."""
        return {"id": event_id, "deleted": True}

    def _mock_send_email(self, to_recipients: List[str], subject: str, body: str) -> Dict[str, Any]:
        """Mock send email."""
        return {
            "message_id": f"msg_{int(time.time())}",
            "to": to_recipients,
            "subject": subject,
            "sent": True,
        }

    def _mock_read_emails(self, query: str) -> List[Dict[str, Any]]:
        """Mock read emails."""
        return [
            {
                "id": "email_1",
                "subject": "Important Update",
                "from": "sender@example.com",
                "date": "2024-01-15T09:00:00Z",
                "body": "This is an important email.",
            }
        ]

    def _mock_search_emails(self, search_query: str) -> List[Dict[str, Any]]:
        """Mock search emails."""
        return [
            {
                "id": "email_2",
                "subject": "Search Result",
                "from": "search@example.com",
                "date": "2024-01-15T08:00:00Z",
                "body": "This email matches the search query.",
            }
        ]

    def _mock_delete_emails(self, email_ids: List[str]) -> Dict[str, Any]:
        """Mock delete emails."""
        return {"deleted_ids": email_ids, "deleted_count": len(email_ids)}

    def _execute_code_tool(
        self, context: NodeExecutionContext, logs: List[str], start_time: float
    ) -> NodeExecutionResult:
        """Execute code execution tool."""
        code = context.get_parameter("code", "")
        language = context.get_parameter("language", "python")

        logs.append(f"Code Execution Tool: {language} - {len(code)} characters")

        # Mock code execution (in real implementation, would use sandbox)
        output_data = {
            "tool_type": "code_execution",
            "language": language,
            "code": code,
            "status": "executed",
            "output": f"Mock execution result for {language} code",
            "execution_time": 0.1,
            "executed_at": datetime.now().isoformat(),
        }

        return self._create_success_result(
            output_data=output_data, execution_time=time.time() - start_time, logs=logs
        )
