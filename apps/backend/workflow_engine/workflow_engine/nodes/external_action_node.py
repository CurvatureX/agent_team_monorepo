"""
External Action Node Executor.

Handles external API calls to third-party services like GitHub, Google Calendar, Trello, Email, Slack, etc.
"""

import json
import time
from typing import Any, Dict, List, Optional
from datetime import datetime
import asyncio

from .base import BaseNodeExecutor, NodeExecutionContext, NodeExecutionResult, ExecutionStatus


class ExternalActionNodeExecutor(BaseNodeExecutor):
    """Executor for EXTERNAL_ACTION_NODE type."""
    
    def get_supported_subtypes(self) -> List[str]:
        """Get supported external action subtypes."""
        return [
            "GITHUB",
            "GOOGLE_CALENDAR",
            "TRELLO", 
            "EMAIL",
            "SLACK",
            "API_CALL"
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
            errors.extend(self._validate_required_parameters(node, ["action", "recipient"]))
            
        elif subtype == "SLACK":
            errors.extend(self._validate_required_parameters(node, ["action", "channel"]))
            
        elif subtype == "API_CALL":
            errors.extend(self._validate_required_parameters(node, ["url", "method"]))
            method = node.parameters.get("method", "GET")
            if method not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                errors.append(f"Invalid HTTP method: {method}")
        
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
                return self._execute_api_call(context, logs, start_time)
            else:
                return self._create_error_result(
                    f"Unsupported external action subtype: {subtype}",
                    execution_time=time.time() - start_time,
                    logs=logs
                )
        
        except Exception as e:
            return self._create_error_result(
                f"Error executing external action: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs
            )
    
    def _execute_github_action(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute GitHub action."""
        action = context.get_parameter("action")
        repository = context.get_parameter("repository")
        
        logs.append(f"GitHub action: {action} on repository {repository}")
        
        # Simulate GitHub API call
        if action == "create_issue":
            title = context.input_data.get("title", "New Issue")
            body = context.input_data.get("body", "")
            
            result = {
                "action": "create_issue",
                "repository": repository,
                "issue": {
                    "id": 12345,
                    "number": 42,
                    "title": title,
                    "body": body,
                    "state": "open",
                    "created_at": datetime.now().isoformat()
                }
            }
            
        elif action == "create_pr":
            title = context.input_data.get("title", "New PR")
            branch = context.input_data.get("branch", "feature/new-feature")
            
            result = {
                "action": "create_pr",
                "repository": repository,
                "pull_request": {
                    "id": 67890,
                    "number": 123,
                    "title": title,
                    "head": branch,
                    "base": "main",
                    "state": "open",
                    "created_at": datetime.now().isoformat()
                }
            }
            
        else:
            result = {
                "action": action,
                "repository": repository,
                "status": "completed",
                "message": f"GitHub action {action} executed successfully"
            }
        
        return self._create_success_result(
            output_data=result,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_google_calendar_action(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute Google Calendar action."""
        action = context.get_parameter("action")
        calendar_id = context.get_parameter("calendar_id")
        
        logs.append(f"Google Calendar action: {action} on calendar {calendar_id}")
        
        if action == "create_event":
            title = context.input_data.get("title", "New Event")
            start_time_str = context.input_data.get("start_time", datetime.now().isoformat())
            duration = context.input_data.get("duration", 60)  # minutes
            
            result = {
                "action": "create_event",
                "calendar_id": calendar_id,
                "event": {
                    "id": "event_12345",
                    "title": title,
                    "start_time": start_time_str,
                    "duration": duration,
                    "status": "confirmed",
                    "created_at": datetime.now().isoformat()
                }
            }
            
        elif action == "list_events":
            result = {
                "action": "list_events",
                "calendar_id": calendar_id,
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
                ]
            }
            
        else:
            result = {
                "action": action,
                "calendar_id": calendar_id,
                "status": "completed"
            }
        
        return self._create_success_result(
            output_data=result,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_trello_action(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute Trello action."""
        action = context.get_parameter("action")
        board_id = context.get_parameter("board_id")
        
        logs.append(f"Trello action: {action} on board {board_id}")
        
        if action == "create_card":
            title = context.input_data.get("title", "New Card")
            description = context.input_data.get("description", "")
            list_id = context.input_data.get("list_id", "todo")
            
            result = {
                "action": "create_card",
                "board_id": board_id,
                "card": {
                    "id": "card_12345",
                    "title": title,
                    "description": description,
                    "list_id": list_id,
                    "created_at": datetime.now().isoformat()
                }
            }
            
        elif action == "move_card":
            card_id = context.input_data.get("card_id")
            target_list = context.input_data.get("target_list")
            
            result = {
                "action": "move_card",
                "board_id": board_id,
                "card_id": card_id,
                "target_list": target_list,
                "status": "moved"
            }
            
        else:
            result = {
                "action": action,
                "board_id": board_id,
                "status": "completed"
            }
        
        return self._create_success_result(
            output_data=result,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_email_action(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute email action."""
        action = context.get_parameter("action")
        recipient = context.get_parameter("recipient")
        
        logs.append(f"Email action: {action} to {recipient}")
        
        if action == "send_email":
            subject = context.input_data.get("subject", "No Subject")
            body = context.input_data.get("body", "")
            
            result = {
                "action": "send_email",
                "recipient": recipient,
                "subject": subject,
                "body": body,
                "message_id": "msg_12345",
                "sent_at": datetime.now().isoformat(),
                "status": "sent"
            }
            
        else:
            result = {
                "action": action,
                "recipient": recipient,
                "status": "completed"
            }
        
        return self._create_success_result(
            output_data=result,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_slack_action(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute Slack action."""
        action = context.get_parameter("action")
        channel = context.get_parameter("channel")
        
        logs.append(f"Slack action: {action} in channel {channel}")
        
        if action == "send_message":
            message = context.input_data.get("message", "")
            
            result = {
                "action": "send_message",
                "channel": channel,
                "message": message,
                "message_id": "msg_12345",
                "sent_at": datetime.now().isoformat(),
                "status": "sent"
            }
            
        elif action == "create_channel":
            channel_name = context.input_data.get("channel_name")
            
            result = {
                "action": "create_channel",
                "channel_name": channel_name,
                "channel_id": "C1234567890",
                "created_at": datetime.now().isoformat(),
                "status": "created"
            }
            
        else:
            result = {
                "action": action,
                "channel": channel,
                "status": "completed"
            }
        
        return self._create_success_result(
            output_data=result,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_api_call(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute generic API call."""
        url = context.get_parameter("url")
        method = context.get_parameter("method", "GET")
        headers = context.get_parameter("headers", {})
        
        logs.append(f"API call: {method} {url}")
        
        # Simulate API call
        request_data = context.input_data.get("request_data", {})
        
        result = {
            "action": "api_call",
            "url": url,
            "method": method,
            "headers": headers,
            "request_data": request_data,
            "response": {
                "status_code": 200,
                "data": {"success": True, "message": "API call completed"},
                "headers": {"content-type": "application/json"}
            },
            "called_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=result,
            execution_time=time.time() - start_time,
            logs=logs
        ) 