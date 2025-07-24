"""
Human-in-the-Loop Node Executor.

Handles human interaction operations like waiting for user input, approvals, etc.
"""

import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .base import BaseNodeExecutor, NodeExecutionContext, NodeExecutionResult, ExecutionStatus


class HumanLoopNodeExecutor(BaseNodeExecutor):
    """Executor for HUMAN_IN_THE_LOOP_NODE type."""
    
    def get_supported_subtypes(self) -> List[str]:
        """Get supported human-in-the-loop subtypes."""
        return [
            "GMAIL",
            "SLACK", 
            "DISCORD",
            "TELEGRAM",
            "APP"
        ]
    
    def validate(self, node: Any) -> List[str]:
        """Validate human-in-the-loop node configuration."""
        errors = []
        
        if not node.subtype:
            errors.append("Human-in-the-loop subtype is required")
            return errors
        
        subtype = node.subtype
        
        if subtype == "GMAIL":
            errors.extend(self._validate_required_parameters(node, ["email_template", "recipients"]))
        
        elif subtype == "SLACK":
            errors.extend(self._validate_required_parameters(node, ["channel", "message_template"]))
        
        elif subtype == "DISCORD":
            errors.extend(self._validate_required_parameters(node, ["channel_id", "message_template"]))
        
        elif subtype == "TELEGRAM":
            errors.extend(self._validate_required_parameters(node, ["chat_id", "message_template"]))
        
        elif subtype == "APP":
            errors.extend(self._validate_required_parameters(node, ["notification_type"]))
            notification_type = node.parameters.get("notification_type", "")
            if notification_type not in ["approval", "input", "review", "confirmation"]:
                errors.append(f"Invalid notification type: {notification_type}")
        
        return errors
    
    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute human-in-the-loop node."""
        start_time = time.time()
        logs = []
        
        try:
            subtype = context.node.subtype
            logs.append(f"Executing human-in-the-loop node with subtype: {subtype}")
            
            if subtype == "GMAIL":
                return self._execute_gmail_interaction(context, logs, start_time)
            elif subtype == "SLACK":
                return self._execute_slack_interaction(context, logs, start_time)
            elif subtype == "DISCORD":
                return self._execute_discord_interaction(context, logs, start_time)
            elif subtype == "TELEGRAM":
                return self._execute_telegram_interaction(context, logs, start_time)
            elif subtype == "APP":
                return self._execute_app_interaction(context, logs, start_time)
            else:
                return self._create_error_result(
                    f"Unsupported human-in-the-loop subtype: {subtype}",
                    execution_time=time.time() - start_time,
                    logs=logs
                )
        
        except Exception as e:
            return self._create_error_result(
                f"Error executing human-in-the-loop: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs
            )
    
    def _execute_gmail_interaction(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute Gmail interaction."""
        email_template = context.get_parameter("email_template", "")
        recipients = context.get_parameter("recipients", [])
        subject = context.get_parameter("subject", "Action Required")
        timeout_hours = context.get_parameter("timeout_hours", 24)
        
        logs.append(f"Gmail interaction: sending to {len(recipients)} recipients")
        
        # Mock email sending
        email_data = {
            "to": recipients,
            "subject": subject,
            "body": self._render_template(email_template, context.input_data),
            "sent_at": datetime.now().isoformat(),
            "timeout": timeout_hours
        }
        
        output_data = {
            "interaction_type": "gmail",
            "email_data": email_data,
            "recipients": recipients,
            "subject": subject,
            "status": "sent",
            "waiting_for_response": True,
            "timeout_at": (datetime.now() + timedelta(hours=timeout_hours)).isoformat(),
            "executed_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_slack_interaction(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute Slack interaction."""
        channel = context.get_parameter("channel", "")
        message_template = context.get_parameter("message_template", "")
        timeout_minutes = context.get_parameter("timeout_minutes", 60)
        
        logs.append(f"Slack interaction: sending to channel {channel}")
        
        # Mock Slack message sending
        message_data = {
            "channel": channel,
            "message": self._render_template(message_template, context.input_data),
            "sent_at": datetime.now().isoformat(),
            "timeout": timeout_minutes
        }
        
        output_data = {
            "interaction_type": "slack",
            "message_data": message_data,
            "channel": channel,
            "status": "sent",
            "waiting_for_response": True,
            "timeout_at": (datetime.now() + timedelta(minutes=timeout_minutes)).isoformat(),
            "executed_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_discord_interaction(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute Discord interaction."""
        channel_id = context.get_parameter("channel_id", "")
        message_template = context.get_parameter("message_template", "")
        timeout_minutes = context.get_parameter("timeout_minutes", 60)
        
        logs.append(f"Discord interaction: sending to channel {channel_id}")
        
        # Mock Discord message sending
        message_data = {
            "channel_id": channel_id,
            "message": self._render_template(message_template, context.input_data),
            "sent_at": datetime.now().isoformat(),
            "timeout": timeout_minutes
        }
        
        output_data = {
            "interaction_type": "discord",
            "message_data": message_data,
            "channel_id": channel_id,
            "status": "sent",
            "waiting_for_response": True,
            "timeout_at": (datetime.now() + timedelta(minutes=timeout_minutes)).isoformat(),
            "executed_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_telegram_interaction(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute Telegram interaction."""
        chat_id = context.get_parameter("chat_id", "")
        message_template = context.get_parameter("message_template", "")
        timeout_minutes = context.get_parameter("timeout_minutes", 60)
        
        logs.append(f"Telegram interaction: sending to chat {chat_id}")
        
        # Mock Telegram message sending
        message_data = {
            "chat_id": chat_id,
            "message": self._render_template(message_template, context.input_data),
            "sent_at": datetime.now().isoformat(),
            "timeout": timeout_minutes
        }
        
        output_data = {
            "interaction_type": "telegram",
            "message_data": message_data,
            "chat_id": chat_id,
            "status": "sent",
            "waiting_for_response": True,
            "timeout_at": (datetime.now() + timedelta(minutes=timeout_minutes)).isoformat(),
            "executed_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_app_interaction(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute app interaction."""
        notification_type = context.get_parameter("notification_type", "approval")
        title = context.get_parameter("title", "Action Required")
        message = context.get_parameter("message", "")
        timeout_minutes = context.get_parameter("timeout_minutes", 30)
        
        logs.append(f"App interaction: {notification_type} notification")
        
        # Mock app notification
        notification_data = {
            "type": notification_type,
            "title": title,
            "message": self._render_template(message, context.input_data),
            "sent_at": datetime.now().isoformat(),
            "timeout": timeout_minutes
        }
        
        output_data = {
            "interaction_type": "app",
            "notification_data": notification_data,
            "notification_type": notification_type,
            "title": title,
            "status": "sent",
            "waiting_for_response": True,
            "timeout_at": (datetime.now() + timedelta(minutes=timeout_minutes)).isoformat(),
            "executed_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _render_template(self, template: str, data: Dict[str, Any]) -> str:
        """Render template with data."""
        try:
            # Simple template rendering
            for key, value in data.items():
                placeholder = f"{{{{{key}}}}}"
                template = template.replace(placeholder, str(value))
            return template
        except Exception:
            return template
