"""
Trigger node specifications.

This module defines specifications for all TRIGGER_NODE subtypes including
manual triggers, webhooks, cron jobs, chat triggers, and other event-based triggers.
"""

from ..base import (
    ConnectionType,
    DataFormat,
    InputPortSpec,
    NodeSpec,
    OutputPortSpec,
    ParameterDef,
    ParameterType,
)

# Manual trigger - started by user action
MANUAL_TRIGGER_SPEC = NodeSpec(
    node_type="TRIGGER_NODE",
    subtype="TRIGGER_MANUAL",
    description="Manual trigger activated by user action",
    parameters=[
        ParameterDef(
            name="trigger_name",
            type=ParameterType.STRING,
            required=False,
            default_value="Manual Trigger",
            description="Display name for the trigger",
        ),
        ParameterDef(
            name="description",
            type=ParameterType.STRING,
            required=False,
            description="Description of what this trigger does",
        ),
    ],
    input_ports=[],  # Trigger nodes have no input ports
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Triggered execution output",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"trigger_time": "string", "execution_id": "string", "user_id": "string"}',
                examples=[
                    '{"trigger_time": "2025-01-28T10:30:00Z", "execution_id": "exec_123", "user_id": "user_456"}'
                ],
            ),
            validation_schema='{"type": "object", "properties": {"trigger_time": {"type": "string"}, "execution_id": {"type": "string"}, "user_id": {"type": "string"}}, "required": ["trigger_time", "execution_id"]}',
        )
    ],
)


# Cron trigger - scheduled execution
CRON_TRIGGER_SPEC = NodeSpec(
    node_type="TRIGGER_NODE",
    subtype="TRIGGER_CRON",
    description="Scheduled trigger based on cron expressions",
    parameters=[
        ParameterDef(
            name="cron_expression",
            type=ParameterType.CRON_EXPRESSION,
            required=True,
            description="Cron time expression (e.g., '0 9 * * MON-FRI')",
            validation_pattern=r"^(\*|[0-9,\-/]+)\s+(\*|[0-9,\-/]+)\s+(\*|[0-9,\-/]+)\s+(\*|[0-9,\-/]+)\s+(\*|[0-9,\-/]+)$",
        ),
        ParameterDef(
            name="timezone",
            type=ParameterType.STRING,
            required=False,
            default_value="UTC",
            description="Timezone for the cron expression",
        ),
        ParameterDef(
            name="enabled",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value="true",
            description="Whether the cron trigger is active",
        ),
    ],
    input_ports=[],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Scheduled execution output",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"trigger_time": "string", "execution_id": "string", "scheduled_time": "string"}',
                examples=[
                    '{"trigger_time": "2025-01-28T09:00:00Z", "execution_id": "exec_789", "scheduled_time": "2025-01-28T09:00:00Z"}'
                ],
            ),
            validation_schema='{"type": "object", "properties": {"trigger_time": {"type": "string"}, "execution_id": {"type": "string"}, "scheduled_time": {"type": "string"}}, "required": ["trigger_time", "execution_id", "scheduled_time"]}',
        )
    ],
)


# Webhook trigger - HTTP endpoint
WEBHOOK_TRIGGER_SPEC = NodeSpec(
    node_type="TRIGGER_NODE",
    subtype="TRIGGER_WEBHOOK",
    description="HTTP webhook trigger that responds to incoming requests",
    parameters=[
        ParameterDef(
            name="webhook_path",
            type=ParameterType.STRING,
            required=False,
            description="Custom path for the webhook (auto-generated if not provided)",
        ),
        ParameterDef(
            name="http_method",
            type=ParameterType.ENUM,
            required=False,
            default_value="POST",
            enum_values=["GET", "POST", "PUT", "PATCH", "DELETE"],
            description="HTTP method to accept",
        ),
        ParameterDef(
            name="authentication_required",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value="true",
            description="Whether authentication is required",
        ),
        ParameterDef(
            name="response_format",
            type=ParameterType.ENUM,
            required=False,
            default_value="json",
            enum_values=["json", "text", "html"],
            description="Response format to return",
        ),
    ],
    input_ports=[],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Webhook request data",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"headers": "object", "body": "object", "query_params": "object", "method": "string", "path": "string"}',
                examples=[
                    '{"headers": {"content-type": "application/json"}, "body": {"message": "hello"}, "query_params": {"param1": "value1"}, "method": "POST", "path": "/webhook/123"}'
                ],
            ),
            validation_schema='{"type": "object", "properties": {"headers": {"type": "object"}, "body": {"type": "object"}, "query_params": {"type": "object"}, "method": {"type": "string"}, "path": {"type": "string"}}, "required": ["method", "path"]}',
        )
    ],
)


# Chat trigger - messaging platform integration
CHAT_TRIGGER_SPEC = NodeSpec(
    node_type="TRIGGER_NODE",
    subtype="TRIGGER_CHAT",
    description="Chat message trigger from messaging platforms",
    parameters=[
        ParameterDef(
            name="platform",
            type=ParameterType.ENUM,
            required=True,
            enum_values=["slack", "discord", "telegram", "teams", "generic"],
            description="Chat platform to monitor",
        ),
        ParameterDef(
            name="channel_filter",
            type=ParameterType.STRING,
            required=False,
            description="Channel or room filter (regex pattern)",
        ),
        ParameterDef(
            name="mention_required",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value="false",
            description="Whether bot mention is required to trigger",
        ),
        ParameterDef(
            name="command_prefix",
            type=ParameterType.STRING,
            required=False,
            description="Command prefix to respond to (e.g., '!', '/')",
        ),
    ],
    input_ports=[],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Chat message data",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"message": "string", "user_id": "string", "channel_id": "string", "platform": "string", "timestamp": "string"}',
                examples=[
                    '{"message": "Hello bot!", "user_id": "user123", "channel_id": "general", "platform": "slack", "timestamp": "2025-01-28T10:30:00Z"}'
                ],
            ),
            validation_schema='{"type": "object", "properties": {"message": {"type": "string"}, "user_id": {"type": "string"}, "channel_id": {"type": "string"}, "platform": {"type": "string"}, "timestamp": {"type": "string"}}, "required": ["message", "user_id", "platform", "timestamp"]}',
        )
    ],
)


# Email trigger - email monitoring
EMAIL_TRIGGER_SPEC = NodeSpec(
    node_type="TRIGGER_NODE",
    subtype="TRIGGER_EMAIL",
    description="Email trigger that monitors incoming emails",
    parameters=[
        ParameterDef(
            name="email_filter",
            type=ParameterType.STRING,
            required=False,
            description="Email filter criteria (from, subject, etc.)",
        ),
        ParameterDef(
            name="folder",
            type=ParameterType.STRING,
            required=False,
            default_value="INBOX",
            description="Email folder to monitor",
        ),
        ParameterDef(
            name="mark_as_read",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value="true",
            description="Mark processed emails as read",
        ),
        ParameterDef(
            name="attachment_processing",
            type=ParameterType.ENUM,
            required=False,
            default_value="include",
            enum_values=["include", "exclude", "only"],
            description="How to handle email attachments",
        ),
    ],
    input_ports=[],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Email data",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"from": "string", "to": "string", "subject": "string", "body": "string", "attachments": "array", "timestamp": "string"}',
                examples=[
                    '{"from": "sender@example.com", "to": "recipient@example.com", "subject": "Important Message", "body": "Email content here", "attachments": [], "timestamp": "2025-01-28T10:30:00Z"}'
                ],
            ),
            validation_schema='{"type": "object", "properties": {"from": {"type": "string"}, "to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}, "attachments": {"type": "array"}, "timestamp": {"type": "string"}}, "required": ["from", "subject", "timestamp"]}',
        )
    ],
)


# Form trigger - web form submission
FORM_TRIGGER_SPEC = NodeSpec(
    node_type="TRIGGER_NODE",
    subtype="TRIGGER_FORM",
    description="Web form submission trigger",
    parameters=[
        ParameterDef(
            name="form_name",
            type=ParameterType.STRING,
            required=True,
            description="Name identifier for the form",
        ),
        ParameterDef(
            name="validation_schema",
            type=ParameterType.JSON,
            required=False,
            description="JSON schema for form validation",
        ),
        ParameterDef(
            name="success_redirect",
            type=ParameterType.URL,
            required=False,
            description="URL to redirect after successful submission",
        ),
        ParameterDef(
            name="require_captcha",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value="false",
            description="Whether to require CAPTCHA verification",
        ),
    ],
    input_ports=[],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Form submission data",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"form_data": "object", "submitter_ip": "string", "timestamp": "string", "user_agent": "string"}',
                examples=[
                    '{"form_data": {"name": "John Doe", "email": "john@example.com"}, "submitter_ip": "192.168.1.1", "timestamp": "2025-01-28T10:30:00Z", "user_agent": "Mozilla/5.0..."}'
                ],
            ),
            validation_schema='{"type": "object", "properties": {"form_data": {"type": "object"}, "submitter_ip": {"type": "string"}, "timestamp": {"type": "string"}, "user_agent": {"type": "string"}}, "required": ["form_data", "timestamp"]}',
        )
    ],
)


# Calendar trigger - calendar event based
CALENDAR_TRIGGER_SPEC = NodeSpec(
    node_type="TRIGGER_NODE",
    subtype="TRIGGER_CALENDAR",
    description="Calendar event trigger for meetings and appointments",
    parameters=[
        ParameterDef(
            name="calendar_id",
            type=ParameterType.STRING,
            required=False,
            description="Specific calendar ID to monitor (default: primary)",
        ),
        ParameterDef(
            name="event_type",
            type=ParameterType.ENUM,
            required=False,
            default_value="upcoming",
            enum_values=["upcoming", "starting", "ending", "cancelled"],
            description="Type of calendar event to trigger on",
        ),
        ParameterDef(
            name="advance_minutes",
            type=ParameterType.INTEGER,
            required=False,
            default_value="15",
            description="Minutes before event to trigger (for upcoming events)",
        ),
        ParameterDef(
            name="event_filter",
            type=ParameterType.STRING,
            required=False,
            description="Filter events by title or description (regex)",
        ),
    ],
    input_ports=[],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Calendar event data",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"event_id": "string", "title": "string", "start_time": "string", "end_time": "string", "attendees": "array", "description": "string"}',
                examples=[
                    '{"event_id": "evt_123", "title": "Team Meeting", "start_time": "2025-01-28T14:00:00Z", "end_time": "2025-01-28T15:00:00Z", "attendees": ["alice@example.com"], "description": "Weekly team sync"}'
                ],
            ),
            validation_schema='{"type": "object", "properties": {"event_id": {"type": "string"}, "title": {"type": "string"}, "start_time": {"type": "string"}, "end_time": {"type": "string"}, "attendees": {"type": "array"}, "description": {"type": "string"}}, "required": ["event_id", "title", "start_time"]}',
        )
    ],
)
