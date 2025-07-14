"""
Trigger Node Executor.

Handles various trigger types including manual, webhook, cron, chat, email, form, and calendar triggers.
"""

import asyncio
import json
import time
from typing import Any, Dict, List
from datetime import datetime, timedelta

from .base import BaseNodeExecutor, NodeExecutionContext, NodeExecutionResult, ExecutionStatus


class TriggerNodeExecutor(BaseNodeExecutor):
    """Executor for TRIGGER_NODE type."""
    
    def get_supported_subtypes(self) -> List[str]:
        """Get supported trigger subtypes."""
        return [
            "MANUAL",
            "WEBHOOK", 
            "CRON",
            "CHAT",
            "EMAIL",
            "FORM",
            "CALENDAR"
        ]
    
    def validate(self, node: Any) -> List[str]:
        """Validate trigger node configuration."""
        errors = []
        
        if not node.subtype:
            errors.append("Trigger subtype is required")
            return errors
        
        subtype = node.subtype
        
        if subtype == "WEBHOOK":
            errors.extend(self._validate_required_parameters(node, ["webhook_url", "method"]))
            method = node.parameters.get("method", "POST")
            if method not in ["GET", "POST", "PUT", "DELETE"]:
                errors.append(f"Invalid HTTP method: {method}")
        
        elif subtype == "CRON":
            errors.extend(self._validate_required_parameters(node, ["cron_expression"]))
            # Basic cron validation could be added here
        
        elif subtype == "CHAT":
            errors.extend(self._validate_required_parameters(node, ["platform", "channel"]))
            platform = node.parameters.get("platform")
            if platform not in ["slack", "discord", "telegram", "teams"]:
                errors.append(f"Unsupported chat platform: {platform}")
        
        elif subtype == "EMAIL":
            errors.extend(self._validate_required_parameters(node, ["email_address", "subject_filter"]))
        
        elif subtype == "FORM":
            errors.extend(self._validate_required_parameters(node, ["form_fields"]))
        
        elif subtype == "CALENDAR":
            errors.extend(self._validate_required_parameters(node, ["calendar_id", "event_type"]))
        
        return errors
    
    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute trigger node."""
        start_time = time.time()
        logs = []
        
        try:
            subtype = context.node.subtype
            logs.append(f"Executing trigger node with subtype: {subtype}")
            
            if subtype == "MANUAL":
                return self._execute_manual_trigger(context, logs, start_time)
            elif subtype == "WEBHOOK":
                return self._execute_webhook_trigger(context, logs, start_time)
            elif subtype == "CRON":
                return self._execute_cron_trigger(context, logs, start_time)
            elif subtype == "CHAT":
                return self._execute_chat_trigger(context, logs, start_time)
            elif subtype == "EMAIL":
                return self._execute_email_trigger(context, logs, start_time)
            elif subtype == "FORM":
                return self._execute_form_trigger(context, logs, start_time)
            elif subtype == "CALENDAR":
                return self._execute_calendar_trigger(context, logs, start_time)
            else:
                return self._create_error_result(
                    f"Unsupported trigger subtype: {subtype}",
                    execution_time=time.time() - start_time,
                    logs=logs
                )
        
        except Exception as e:
            return self._create_error_result(
                f"Error executing trigger: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs
            )
    
    def _execute_manual_trigger(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute manual trigger."""
        logs.append("Manual trigger executed")
        
        # Manual triggers typically pass through input data
        output_data = {
            "trigger_type": "manual",
            "triggered_at": datetime.now().isoformat(),
            "input_data": context.input_data
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_webhook_trigger(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute webhook trigger."""
        webhook_url = context.get_parameter("webhook_url")
        method = context.get_parameter("method", "POST")
        
        logs.append(f"Webhook trigger configured for {method} {webhook_url}")
        
        # In a real implementation, this would set up webhook endpoint
        # For now, simulate webhook data
        webhook_data = context.input_data.get("webhook_payload", {})
        
        output_data = {
            "trigger_type": "webhook",
            "webhook_url": webhook_url,
            "method": method,
            "payload": webhook_data,
            "triggered_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_cron_trigger(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute cron trigger."""
        cron_expression = context.get_parameter("cron_expression")
        
        logs.append(f"Cron trigger with expression: {cron_expression}")
        
        # In a real implementation, this would schedule the cron job
        # For now, simulate cron execution
        output_data = {
            "trigger_type": "cron",
            "cron_expression": cron_expression,
            "triggered_at": datetime.now().isoformat(),
            "next_run": (datetime.now() + timedelta(hours=1)).isoformat()  # Simulate next run
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_chat_trigger(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute chat trigger."""
        platform = context.get_parameter("platform")
        channel = context.get_parameter("channel")
        trigger_phrase = context.get_parameter("trigger_phrase", "")
        
        logs.append(f"Chat trigger on {platform} channel {channel}")
        
        # Simulate chat message
        message_data = context.input_data.get("message", {})
        
        output_data = {
            "trigger_type": "chat",
            "platform": platform,
            "channel": channel,
            "trigger_phrase": trigger_phrase,
            "message": message_data,
            "triggered_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_email_trigger(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute email trigger."""
        email_address = context.get_parameter("email_address")
        subject_filter = context.get_parameter("subject_filter")
        
        logs.append(f"Email trigger for {email_address} with subject filter: {subject_filter}")
        
        # Simulate email data
        email_data = context.input_data.get("email", {})
        
        output_data = {
            "trigger_type": "email",
            "email_address": email_address,
            "subject_filter": subject_filter,
            "email": email_data,
            "triggered_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_form_trigger(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute form trigger."""
        form_fields = context.get_parameter("form_fields", [])
        
        logs.append(f"Form trigger with fields: {form_fields}")
        
        # Simulate form submission
        form_data = context.input_data.get("form_submission", {})
        
        output_data = {
            "trigger_type": "form",
            "form_fields": form_fields,
            "form_data": form_data,
            "triggered_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_calendar_trigger(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute calendar trigger."""
        calendar_id = context.get_parameter("calendar_id")
        event_type = context.get_parameter("event_type")
        
        logs.append(f"Calendar trigger for {calendar_id} with event type: {event_type}")
        
        # Simulate calendar event
        event_data = context.input_data.get("calendar_event", {})
        
        output_data = {
            "trigger_type": "calendar",
            "calendar_id": calendar_id,
            "event_type": event_type,
            "event": event_data,
            "triggered_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        ) 