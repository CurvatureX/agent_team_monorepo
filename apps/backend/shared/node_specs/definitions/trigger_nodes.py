"""
Trigger node specifications.

This module defines specifications for all TRIGGER_NODE subtypes including
manual triggers, webhooks, cron jobs, chat triggers, and other event-based triggers.
"""

from ...models.node_enums import NodeType, TriggerSubtype
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
    node_type=NodeType.TRIGGER,
    subtype=TriggerSubtype.MANUAL,
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
    node_type=NodeType.TRIGGER,
    subtype=TriggerSubtype.CRON,
    description="Scheduled trigger based on cron expressions",
    parameters=[
        ParameterDef(
            name="cron_expression",
            type=ParameterType.CRON_EXPRESSION,
            required=True,
            description="Cron time expression (e.g., '0 9 * * MON-FRI')",
            validation_pattern=None,  # Use croniter validation in validator.py instead of regex
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
            default_value=True,
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
    node_type=NodeType.TRIGGER,
    subtype=TriggerSubtype.WEBHOOK,
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
            default_value=True,
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


# Slack trigger - Slack interaction trigger
SLACK_TRIGGER_SPEC = NodeSpec(
    node_type=NodeType.TRIGGER,
    subtype=TriggerSubtype.SLACK,
    description="Slack trigger that responds to Slack interactions and events",
    parameters=[
        ParameterDef(
            name="workspace_id",
            type=ParameterType.STRING,
            required=False,
            description="Slack workspace ID to monitor (default: all connected workspaces)",
        ),
        ParameterDef(
            name="channel_filter",
            type=ParameterType.STRING,
            required=False,
            description="Channel filter (channel ID, name, or regex pattern)",
        ),
        ParameterDef(
            name="event_types",
            type=ParameterType.JSON,
            required=False,
            default_value=["message", "app_mention"],
            enum_values=[
                "message",
                "app_mention",
                "reaction_added",
                "pin_added",
                "file_shared",
                "slash_command",
                "interactive_message",
                "button_click",
            ],
            description="Slack event types to listen for",
        ),
        ParameterDef(
            name="mention_required",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=False,
            description="Whether bot mention is required to trigger",
        ),
        ParameterDef(
            name="command_prefix",
            type=ParameterType.STRING,
            required=False,
            description="Command prefix to respond to (e.g., '!', '/')",
        ),
        ParameterDef(
            name="user_filter",
            type=ParameterType.STRING,
            required=False,
            description="Filter by user ID or username (regex pattern)",
        ),
        ParameterDef(
            name="ignore_bots",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Ignore messages from bot users",
        ),
        ParameterDef(
            name="require_thread",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=False,
            description="Only trigger on messages in threads",
        ),
    ],
    input_ports=[],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Slack event data",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"event_type": "string", "message": "string", "user_id": "string", "channel_id": "string", "team_id": "string", "timestamp": "string", "thread_ts": "string", "event_data": "object"}',
                examples=[
                    '{"event_type": "message", "message": "Hello bot!", "user_id": "U1234567890", "channel_id": "C1234567890", "team_id": "T1234567890", "timestamp": "2025-01-28T10:30:00Z", "thread_ts": null, "event_data": {"client_msg_id": "xxx", "text": "Hello bot!"}}',
                    '{"event_type": "app_mention", "message": "@bot help me", "user_id": "U1234567890", "channel_id": "C1234567890", "team_id": "T1234567890", "timestamp": "2025-01-28T10:30:00Z", "thread_ts": "1642505400.123456", "event_data": {"text": "<@U0BOTUSER> help me"}}',
                ],
            ),
            validation_schema='{"type": "object", "properties": {"event_type": {"type": "string"}, "message": {"type": "string"}, "user_id": {"type": "string"}, "channel_id": {"type": "string"}, "team_id": {"type": "string"}, "timestamp": {"type": "string"}, "thread_ts": {"type": ["string", "null"]}, "event_data": {"type": "object"}}, "required": ["event_type", "user_id", "channel_id", "team_id", "timestamp"]}',
        )
    ],
)


# Email trigger - email monitoring
EMAIL_TRIGGER_SPEC = NodeSpec(
    node_type=NodeType.TRIGGER,
    subtype=TriggerSubtype.EMAIL,
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
            default_value=True,
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


# GitHub trigger - repository event based
GITHUB_TRIGGER_SPEC = NodeSpec(
    node_type=NodeType.TRIGGER,
    subtype=TriggerSubtype.GITHUB,
    description="GitHub repository trigger for code events and workflows",
    parameters=[
        ParameterDef(
            name="github_app_installation_id",
            type=ParameterType.STRING,
            required=True,
            description="GitHub App installation ID for the connected repository",
        ),
        ParameterDef(
            name="repository",
            type=ParameterType.STRING,
            required=True,
            description="Repository in format 'owner/repo' (e.g., 'microsoft/vscode')",
            validation_pattern=r"^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$",
        ),
        ParameterDef(
            name="events",
            type=ParameterType.JSON,
            required=True,
            description="GitHub webhook events to listen for",
            enum_values=[
                "push",
                "pull_request",
                "pull_request_review",
                "issues",
                "issue_comment",
                "release",
                "deployment",
                "deployment_status",
                "create",
                "delete",
                "fork",
                "star",
                "watch",
                "repository",
                "member",
                "team_add",
                "workflow_run",
                "workflow_dispatch",
                "schedule",
                "check_run",
                "check_suite",
            ],
        ),
        ParameterDef(
            name="branches",
            type=ParameterType.JSON,
            required=False,
            description="Branch filter (only for push/pull_request events). Empty means all branches",
        ),
        ParameterDef(
            name="paths",
            type=ParameterType.JSON,
            required=False,
            description="File path filters using glob patterns (e.g., ['src/**', '*.md'])",
        ),
        ParameterDef(
            name="action_filter",
            type=ParameterType.JSON,
            required=False,
            description="Action types to filter on (e.g., ['opened', 'closed', 'synchronize'] for PRs)",
        ),
        ParameterDef(
            name="author_filter",
            type=ParameterType.STRING,
            required=False,
            description="Filter by commit/PR author (username or regex pattern)",
        ),
        ParameterDef(
            name="label_filter",
            type=ParameterType.JSON,
            required=False,
            description="Filter by issue/PR labels (any match triggers)",
        ),
        ParameterDef(
            name="ignore_bots",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Ignore events from bot accounts",
        ),
        ParameterDef(
            name="require_signature_verification",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Verify GitHub webhook signature for security",
        ),
        ParameterDef(
            name="draft_pr_handling",
            type=ParameterType.ENUM,
            required=False,
            default_value="ignore",
            enum_values=["ignore", "include", "only"],
            description="How to handle draft pull requests",
        ),
    ],
    input_ports=[],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="GitHub event data",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"event": "string", "action": "string", "repository": "object", "sender": "object", "payload": "object", "timestamp": "string"}',
                examples=[
                    '{"event": "push", "action": null, "repository": {"name": "my-repo", "owner": {"login": "user"}}, "sender": {"login": "developer"}, "payload": {"commits": [{"message": "Fix bug"}]}, "timestamp": "2025-01-28T10:30:00Z"}',
                    '{"event": "pull_request", "action": "opened", "repository": {"name": "my-repo", "owner": {"login": "user"}}, "sender": {"login": "contributor"}, "payload": {"number": 42, "title": "New feature"}, "timestamp": "2025-01-28T10:30:00Z"}',
                ],
            ),
            validation_schema='{"type": "object", "properties": {"event": {"type": "string"}, "action": {"type": ["string", "null"]}, "repository": {"type": "object"}, "sender": {"type": "object"}, "payload": {"type": "object"}, "timestamp": {"type": "string"}}, "required": ["event", "repository", "sender", "payload", "timestamp"]}',
        )
    ],
)
