"""
Tool Node Executor.

Handles tool integrations including MCP tools, calendar, email, HTTP tools, etc.
"""

import json
import time
from typing import Any, Dict, List, Optional
from datetime import datetime

from .base import BaseNodeExecutor, NodeExecutionContext, NodeExecutionResult, ExecutionStatus


class ToolNodeExecutor(BaseNodeExecutor):
    """Executor for TOOL_NODE type."""
    
    def get_supported_subtypes(self) -> List[str]:
        """Get supported tool subtypes."""
        return [
            "MCP",
            "CALENDAR",
            "EMAIL",
            "HTTP"
        ]
    
    def validate(self, node: Any) -> List[str]:
        """Validate tool node configuration."""
        errors = []
        
        if not node.subtype:
            errors.append("Tool subtype is required")
            return errors
        
        subtype = node.subtype
        
        if subtype == "MCP":
            errors.extend(self._validate_required_parameters(node, ["tool_name", "tool_action"]))
        
        elif subtype == "CALENDAR":
            errors.extend(self._validate_required_parameters(node, ["calendar_provider", "action"]))
            provider = node.parameters.get("calendar_provider")
            if provider not in ["google", "outlook", "apple", "generic"]:
                errors.append(f"Unsupported calendar provider: {provider}")
        
        elif subtype == "EMAIL":
            errors.extend(self._validate_required_parameters(node, ["email_provider", "action"]))
            provider = node.parameters.get("email_provider")
            if provider not in ["gmail", "outlook", "smtp", "generic"]:
                errors.append(f"Unsupported email provider: {provider}")
        
        elif subtype == "HTTP":
            errors.extend(self._validate_required_parameters(node, ["url", "method"]))
            method = node.parameters.get("method", "GET")
            if method not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                errors.append(f"Invalid HTTP method: {method}")
        
        return errors
    
    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute tool node."""
        start_time = time.time()
        logs = []
        
        try:
            subtype = context.node.subtype
            logs.append(f"Executing tool node with subtype: {subtype}")
            
            if subtype == "MCP":
                return self._execute_mcp_tool(context, logs, start_time)
            elif subtype == "CALENDAR":
                return self._execute_calendar_tool(context, logs, start_time)
            elif subtype == "EMAIL":
                return self._execute_email_tool(context, logs, start_time)
            elif subtype == "HTTP":
                return self._execute_http_tool(context, logs, start_time)
            else:
                return self._create_error_result(
                    f"Unsupported tool subtype: {subtype}",
                    execution_time=time.time() - start_time,
                    logs=logs
                )
        
        except Exception as e:
            return self._create_error_result(
                f"Error executing tool: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs
            )
    
    def _execute_mcp_tool(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute MCP (Model Context Protocol) tool."""
        tool_name = context.get_parameter("tool_name")
        tool_action = context.get_parameter("tool_action")
        tool_parameters = context.get_parameter("tool_parameters", {})
        
        logs.append(f"Executing MCP tool: {tool_name} with action: {tool_action}")
        
        # Simulate MCP tool execution
        mcp_result = self._simulate_mcp_tool_call(tool_name, tool_action, tool_parameters, context.input_data)
        
        output_data = {
            "tool_type": "mcp",
            "tool_name": tool_name,
            "tool_action": tool_action,
            "tool_parameters": tool_parameters,
            "input_data": context.input_data,
            "mcp_result": mcp_result,
            "executed_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_calendar_tool(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute calendar tool."""
        calendar_provider = context.get_parameter("calendar_provider")
        action = context.get_parameter("action")
        
        logs.append(f"Executing {calendar_provider} calendar tool with action: {action}")
        
        # Execute calendar action
        if action == "create_event":
            result = self._create_calendar_event(context, calendar_provider)
        elif action == "list_events":
            result = self._list_calendar_events(context, calendar_provider)
        elif action == "update_event":
            result = self._update_calendar_event(context, calendar_provider)
        elif action == "delete_event":
            result = self._delete_calendar_event(context, calendar_provider)
        else:
            result = {"error": f"Unknown calendar action: {action}"}
        
        output_data = {
            "tool_type": "calendar",
            "calendar_provider": calendar_provider,
            "action": action,
            "result": result,
            "executed_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_email_tool(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute email tool."""
        email_provider = context.get_parameter("email_provider")
        action = context.get_parameter("action")
        
        logs.append(f"Executing {email_provider} email tool with action: {action}")
        
        # Execute email action
        if action == "send_email":
            result = self._send_email(context, email_provider)
        elif action == "read_emails":
            result = self._read_emails(context, email_provider)
        elif action == "search_emails":
            result = self._search_emails(context, email_provider)
        elif action == "delete_email":
            result = self._delete_email(context, email_provider)
        else:
            result = {"error": f"Unknown email action: {action}"}
        
        output_data = {
            "tool_type": "email",
            "email_provider": email_provider,
            "action": action,
            "result": result,
            "executed_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_http_tool(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute HTTP tool."""
        url = context.get_parameter("url")
        method = context.get_parameter("method", "GET")
        headers = context.get_parameter("headers", {})
        auth = context.get_parameter("auth", {})
        
        logs.append(f"Executing HTTP {method} request to {url}")
        
        # Simulate HTTP request
        http_result = self._simulate_http_request(url, method, headers, auth, context.input_data)
        
        output_data = {
            "tool_type": "http",
            "url": url,
            "method": method,
            "headers": headers,
            "auth": auth,
            "request_data": context.input_data,
            "http_result": http_result,
            "executed_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _simulate_mcp_tool_call(self, tool_name: str, action: str, parameters: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate MCP tool call."""
        # Simulate different MCP tools
        if tool_name == "file_system":
            return self._simulate_file_system_tool(action, parameters, input_data)
        elif tool_name == "database":
            return self._simulate_database_tool(action, parameters, input_data)
        elif tool_name == "web_scraper":
            return self._simulate_web_scraper_tool(action, parameters, input_data)
        elif tool_name == "ai_assistant":
            return self._simulate_ai_assistant_tool(action, parameters, input_data)
        else:
            return {
                "tool_name": tool_name,
                "action": action,
                "parameters": parameters,
                "success": True,
                "result": f"MCP tool {tool_name} executed successfully",
                "data": input_data
            }
    
    def _simulate_file_system_tool(self, action: str, parameters: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate file system MCP tool."""
        if action == "read_file":
            return {
                "action": "read_file",
                "file_path": parameters.get("file_path", ""),
                "content": "Simulated file content",
                "size": 1024,
                "success": True
            }
        elif action == "write_file":
            return {
                "action": "write_file",
                "file_path": parameters.get("file_path", ""),
                "content": input_data.get("content", ""),
                "bytes_written": len(input_data.get("content", "")),
                "success": True
            }
        else:
            return {"action": action, "success": False, "error": "Unknown file system action"}
    
    def _simulate_database_tool(self, action: str, parameters: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate database MCP tool."""
        if action == "query":
            return {
                "action": "query",
                "query": parameters.get("query", ""),
                "results": [
                    {"id": 1, "name": "Item 1", "value": 100},
                    {"id": 2, "name": "Item 2", "value": 200}
                ],
                "row_count": 2,
                "success": True
            }
        elif action == "insert":
            return {
                "action": "insert",
                "table": parameters.get("table", ""),
                "data": input_data,
                "inserted_id": 123,
                "success": True
            }
        else:
            return {"action": action, "success": False, "error": "Unknown database action"}
    
    def _simulate_web_scraper_tool(self, action: str, parameters: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate web scraper MCP tool."""
        if action == "scrape_url":
            return {
                "action": "scrape_url",
                "url": parameters.get("url", ""),
                "scraped_data": {
                    "title": "Sample Page Title",
                    "content": "Sample page content",
                    "links": ["https://example.com/link1", "https://example.com/link2"]
                },
                "success": True
            }
        else:
            return {"action": action, "success": False, "error": "Unknown web scraper action"}
    
    def _simulate_ai_assistant_tool(self, action: str, parameters: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate AI assistant MCP tool."""
        if action == "generate_text":
            return {
                "action": "generate_text",
                "prompt": parameters.get("prompt", ""),
                "generated_text": "This is simulated AI-generated text based on the prompt.",
                "model": parameters.get("model", "gpt-4"),
                "success": True
            }
        else:
            return {"action": action, "success": False, "error": "Unknown AI assistant action"}
    
    def _create_calendar_event(self, context: NodeExecutionContext, provider: str) -> Dict[str, Any]:
        """Create calendar event."""
        title = context.input_data.get("title", "New Event")
        start_time = context.input_data.get("start_time", datetime.now().isoformat())
        duration = context.input_data.get("duration", 60)  # minutes
        
        return {
            "action": "create_event",
            "provider": provider,
            "event": {
                "id": f"event_{int(time.time())}",
                "title": title,
                "start_time": start_time,
                "duration": duration,
                "created_at": datetime.now().isoformat()
            },
            "success": True
        }
    
    def _list_calendar_events(self, context: NodeExecutionContext, provider: str) -> Dict[str, Any]:
        """List calendar events."""
        start_date = context.input_data.get("start_date", datetime.now().isoformat())
        end_date = context.input_data.get("end_date", datetime.now().isoformat())
        
        return {
            "action": "list_events",
            "provider": provider,
            "date_range": {"start": start_date, "end": end_date},
            "events": [
                {
                    "id": "event_1",
                    "title": "Meeting 1",
                    "start_time": "2024-01-15T10:00:00Z",
                    "duration": 60
                },
                {
                    "id": "event_2",
                    "title": "Meeting 2", 
                    "start_time": "2024-01-15T14:00:00Z",
                    "duration": 30
                }
            ],
            "success": True
        }
    
    def _update_calendar_event(self, context: NodeExecutionContext, provider: str) -> Dict[str, Any]:
        """Update calendar event."""
        event_id = context.input_data.get("event_id", "")
        updates = context.input_data.get("updates", {})
        
        return {
            "action": "update_event",
            "provider": provider,
            "event_id": event_id,
            "updates": updates,
            "updated_at": datetime.now().isoformat(),
            "success": True
        }
    
    def _delete_calendar_event(self, context: NodeExecutionContext, provider: str) -> Dict[str, Any]:
        """Delete calendar event."""
        event_id = context.input_data.get("event_id", "")
        
        return {
            "action": "delete_event",
            "provider": provider,
            "event_id": event_id,
            "deleted_at": datetime.now().isoformat(),
            "success": True
        }
    
    def _send_email(self, context: NodeExecutionContext, provider: str) -> Dict[str, Any]:
        """Send email."""
        recipient = context.input_data.get("recipient", "")
        subject = context.input_data.get("subject", "")
        body = context.input_data.get("body", "")
        
        return {
            "action": "send_email",
            "provider": provider,
            "email": {
                "recipient": recipient,
                "subject": subject,
                "body": body,
                "message_id": f"msg_{int(time.time())}",
                "sent_at": datetime.now().isoformat()
            },
            "success": True
        }
    
    def _read_emails(self, context: NodeExecutionContext, provider: str) -> Dict[str, Any]:
        """Read emails."""
        limit = context.input_data.get("limit", 10)
        
        return {
            "action": "read_emails",
            "provider": provider,
            "emails": [
                {
                    "id": "email_1",
                    "subject": "Test Email 1",
                    "sender": "sender1@example.com",
                    "received_at": "2024-01-15T10:00:00Z"
                },
                {
                    "id": "email_2",
                    "subject": "Test Email 2",
                    "sender": "sender2@example.com",
                    "received_at": "2024-01-15T11:00:00Z"
                }
            ],
            "count": 2,
            "limit": limit,
            "success": True
        }
    
    def _search_emails(self, context: NodeExecutionContext, provider: str) -> Dict[str, Any]:
        """Search emails."""
        query = context.input_data.get("query", "")
        
        return {
            "action": "search_emails",
            "provider": provider,
            "query": query,
            "results": [
                {
                    "id": "email_search_1",
                    "subject": "Search Result 1",
                    "sender": "search1@example.com",
                    "snippet": "This email matches your search query",
                    "received_at": "2024-01-15T09:00:00Z"
                }
            ],
            "count": 1,
            "success": True
        }
    
    def _delete_email(self, context: NodeExecutionContext, provider: str) -> Dict[str, Any]:
        """Delete email."""
        email_id = context.input_data.get("email_id", "")
        
        return {
            "action": "delete_email",
            "provider": provider,
            "email_id": email_id,
            "deleted_at": datetime.now().isoformat(),
            "success": True
        }
    
    def _simulate_http_request(self, url: str, method: str, headers: Dict[str, str], auth: Dict[str, str], data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate HTTP request."""
        return {
            "url": url,
            "method": method,
            "headers": headers,
            "auth": auth,
            "request_data": data,
            "response": {
                "status_code": 200,
                "headers": {"content-type": "application/json"},
                "body": {"success": True, "message": "HTTP request completed successfully"},
                "response_time": 0.5
            },
            "success": True
        } 