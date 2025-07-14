"""
Human-in-the-Loop Node Executor.

Handles human interactions like approvals, inputs, and manual interventions.
"""

import json
import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from .base import BaseNodeExecutor, NodeExecutionContext, NodeExecutionResult, ExecutionStatus


class HumanLoopNodeExecutor(BaseNodeExecutor):
    """Executor for HUMAN_IN_THE_LOOP_NODE type."""
    
    def get_supported_subtypes(self) -> List[str]:
        """Get supported human interaction subtypes."""
        return [
            "GMAIL",
            "SLACK",
            "DISCORD",
            "TELEGRAM",
            "APP"
        ]
    
    def validate(self, node: Any) -> List[str]:
        """Validate human interaction node configuration."""
        errors = []
        
        if not node.subtype:
            errors.append("Human interaction subtype is required")
            return errors
        
        subtype = node.subtype
        
        if subtype == "GMAIL":
            errors.extend(self._validate_required_parameters(node, ["recipient_email", "subject"]))
        
        elif subtype == "SLACK":
            errors.extend(self._validate_required_parameters(node, ["channel", "message"]))
        
        elif subtype == "DISCORD":
            errors.extend(self._validate_required_parameters(node, ["channel_id", "message"]))
        
        elif subtype == "TELEGRAM":
            errors.extend(self._validate_required_parameters(node, ["chat_id", "message"]))
        
        elif subtype == "APP":
            errors.extend(self._validate_required_parameters(node, ["interaction_type"]))
        
        return errors
    
    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute human interaction node."""
        start_time = time.time()
        logs = []
        
        try:
            subtype = context.node.subtype
            logs.append(f"Executing human interaction node with subtype: {subtype}")
            
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
                    f"Unsupported human interaction subtype: {subtype}",
                    execution_time=time.time() - start_time,
                    logs=logs
                )
        
        except Exception as e:
            return self._create_error_result(
                f"Error executing human interaction: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs
            )
    
    def _execute_gmail_interaction(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute Gmail-based human interaction."""
        recipient_email = context.get_parameter("recipient_email")
        subject = context.get_parameter("subject")
        timeout_hours = context.get_parameter("timeout_hours", 24)
        
        logs.append(f"Sending approval request to {recipient_email} via Gmail")
        
        # Generate approval request
        approval_request = self._generate_approval_request(context, "email")
        
        # Simulate sending email
        email_sent = self._send_approval_email(recipient_email, subject, approval_request)
        
        # Simulate waiting for response (in real implementation, would be async)
        response = self._simulate_human_response("email", timeout_hours)
        
        output_data = {
            "interaction_type": "gmail",
            "recipient_email": recipient_email,
            "subject": subject,
            "approval_request": approval_request,
            "email_sent": email_sent,
            "response": response,
            "timeout_hours": timeout_hours,
            "requested_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_slack_interaction(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute Slack-based human interaction."""
        channel = context.get_parameter("channel")
        message = context.get_parameter("message")
        timeout_minutes = context.get_parameter("timeout_minutes", 60)
        
        logs.append(f"Sending message to Slack channel {channel}")
        
        # Generate interaction message
        interaction_message = self._generate_interaction_message(context, message)
        
        # Simulate sending Slack message
        message_sent = self._send_slack_message(channel, interaction_message)
        
        # Simulate waiting for response
        response = self._simulate_human_response("slack", timeout_minutes)
        
        output_data = {
            "interaction_type": "slack",
            "channel": channel,
            "message": interaction_message,
            "message_sent": message_sent,
            "response": response,
            "timeout_minutes": timeout_minutes,
            "requested_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_discord_interaction(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute Discord-based human interaction."""
        channel_id = context.get_parameter("channel_id")
        message = context.get_parameter("message")
        timeout_minutes = context.get_parameter("timeout_minutes", 60)
        
        logs.append(f"Sending message to Discord channel {channel_id}")
        
        # Generate interaction message
        interaction_message = self._generate_interaction_message(context, message)
        
        # Simulate sending Discord message
        message_sent = self._send_discord_message(channel_id, interaction_message)
        
        # Simulate waiting for response
        response = self._simulate_human_response("discord", timeout_minutes)
        
        output_data = {
            "interaction_type": "discord",
            "channel_id": channel_id,
            "message": interaction_message,
            "message_sent": message_sent,
            "response": response,
            "timeout_minutes": timeout_minutes,
            "requested_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_telegram_interaction(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute Telegram-based human interaction."""
        chat_id = context.get_parameter("chat_id")
        message = context.get_parameter("message")
        timeout_minutes = context.get_parameter("timeout_minutes", 60)
        
        logs.append(f"Sending message to Telegram chat {chat_id}")
        
        # Generate interaction message
        interaction_message = self._generate_interaction_message(context, message)
        
        # Simulate sending Telegram message
        message_sent = self._send_telegram_message(chat_id, interaction_message)
        
        # Simulate waiting for response
        response = self._simulate_human_response("telegram", timeout_minutes)
        
        output_data = {
            "interaction_type": "telegram",
            "chat_id": chat_id,
            "message": interaction_message,
            "message_sent": message_sent,
            "response": response,
            "timeout_minutes": timeout_minutes,
            "requested_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_app_interaction(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute app-based human interaction."""
        interaction_type = context.get_parameter("interaction_type")
        timeout_minutes = context.get_parameter("timeout_minutes", 30)
        
        logs.append(f"Creating app interaction of type: {interaction_type}")
        
        # Generate app interaction
        interaction_data = self._generate_app_interaction(context, interaction_type)
        
        # Simulate creating app notification/modal
        interaction_created = self._create_app_interaction(interaction_data)
        
        # Simulate waiting for response
        response = self._simulate_human_response("app", timeout_minutes)
        
        output_data = {
            "interaction_type": "app",
            "app_interaction_type": interaction_type,
            "interaction_data": interaction_data,
            "interaction_created": interaction_created,
            "response": response,
            "timeout_minutes": timeout_minutes,
            "requested_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _generate_approval_request(self, context: NodeExecutionContext, platform: str) -> Dict[str, Any]:
        """Generate approval request content."""
        return {
            "type": "approval_request",
            "platform": platform,
            "workflow_id": context.workflow_id,
            "execution_id": context.execution_id,
            "request_data": context.input_data,
            "approval_options": ["approve", "reject", "request_changes"],
            "generated_at": datetime.now().isoformat()
        }
    
    def _generate_interaction_message(self, context: NodeExecutionContext, base_message: str) -> str:
        """Generate interaction message."""
        return f"""
{base_message}

**Workflow Information:**
- Workflow ID: {context.workflow_id}
- Execution ID: {context.execution_id}
- Node: {context.node.name}

**Input Data:**
{json.dumps(context.input_data, indent=2)}

Please respond with your input or approval.
"""
    
    def _generate_app_interaction(self, context: NodeExecutionContext, interaction_type: str) -> Dict[str, Any]:
        """Generate app interaction data."""
        if interaction_type == "approval":
            return {
                "type": "approval",
                "title": "Approval Required",
                "description": "Please review and approve this workflow step",
                "data": context.input_data,
                "options": ["approve", "reject", "request_changes"]
            }
        elif interaction_type == "input":
            return {
                "type": "input",
                "title": "Input Required",
                "description": "Please provide the required input",
                "fields": [
                    {"name": "user_input", "type": "text", "required": True},
                    {"name": "comments", "type": "textarea", "required": False}
                ]
            }
        elif interaction_type == "review":
            return {
                "type": "review",
                "title": "Review Required",
                "description": "Please review the following information",
                "data": context.input_data,
                "options": ["confirm", "modify", "cancel"]
            }
        else:
            return {
                "type": "custom",
                "interaction_type": interaction_type,
                "data": context.input_data
            }
    
    def _send_approval_email(self, recipient: str, subject: str, content: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate sending approval email."""
        return {
            "sent": True,
            "recipient": recipient,
            "subject": subject,
            "message_id": f"msg_{int(time.time())}",
            "sent_at": datetime.now().isoformat()
        }
    
    def _send_slack_message(self, channel: str, message: str) -> Dict[str, Any]:
        """Simulate sending Slack message."""
        return {
            "sent": True,
            "channel": channel,
            "message_id": f"slack_{int(time.time())}",
            "sent_at": datetime.now().isoformat()
        }
    
    def _send_discord_message(self, channel_id: str, message: str) -> Dict[str, Any]:
        """Simulate sending Discord message."""
        return {
            "sent": True,
            "channel_id": channel_id,
            "message_id": f"discord_{int(time.time())}",
            "sent_at": datetime.now().isoformat()
        }
    
    def _send_telegram_message(self, chat_id: str, message: str) -> Dict[str, Any]:
        """Simulate sending Telegram message."""
        return {
            "sent": True,
            "chat_id": chat_id,
            "message_id": f"telegram_{int(time.time())}",
            "sent_at": datetime.now().isoformat()
        }
    
    def _create_app_interaction(self, interaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate creating app interaction."""
        return {
            "created": True,
            "interaction_id": f"app_{int(time.time())}",
            "interaction_data": interaction_data,
            "created_at": datetime.now().isoformat()
        }
    
    def _simulate_human_response(self, platform: str, timeout_minutes: int) -> Dict[str, Any]:
        """Simulate human response."""
        # In real implementation, this would wait for actual human response
        # For simulation, we'll return a mock response
        
        import random
        
        responses = {
            "email": {
                "status": "approved",
                "response": "approve",
                "comments": "Looks good to proceed",
                "responded_by": "user@example.com",
                "response_time": random.randint(5, 30)  # minutes
            },
            "slack": {
                "status": "approved",
                "response": "👍 Approved",
                "responded_by": "@john.doe",
                "response_time": random.randint(1, 10)  # minutes
            },
            "discord": {
                "status": "approved", 
                "response": "✅ Approved",
                "responded_by": "user#1234",
                "response_time": random.randint(1, 15)  # minutes
            },
            "telegram": {
                "status": "approved",
                "response": "✅ Approved",
                "responded_by": "@username",
                "response_time": random.randint(1, 20)  # minutes
            },
            "app": {
                "status": "approved",
                "response": "approve",
                "user_input": "Approved with no changes",
                "responded_by": "user_123",
                "response_time": random.randint(2, 15)  # minutes
            }
        }
        
        base_response = responses.get(platform, responses["app"])
        base_response["responded_at"] = datetime.now().isoformat()
        base_response["timeout_minutes"] = timeout_minutes
        
        return base_response 