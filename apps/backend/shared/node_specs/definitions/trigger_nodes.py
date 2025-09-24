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
    ManualInvocationSpec,
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
    display_name="Manual Trigger",
    category="triggers",
    template_id="trigger_manual",
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
    manual_invocation=ManualInvocationSpec(
        supported=True,
        description="Manual triggers can be invoked directly with custom context data",
        parameter_schema={
            "type": "object",
            "properties": {
                "trigger_context": {
                    "type": "object",
                    "description": "Custom context data for manual execution",
                },
                "description": {
                    "type": "string",
                    "description": "Description of this manual execution",
                },
            },
        },
        parameter_examples=[
            {
                "name": "Simple Manual Trigger",
                "description": "Basic manual trigger execution",
                "parameters": {
                    "trigger_context": {"source": "manual", "purpose": "testing"},
                    "description": "Testing workflow manually",
                },
            },
            {
                "name": "Emergency Execution",
                "description": "Emergency workflow execution",
                "parameters": {
                    "trigger_context": {"source": "emergency", "urgency": "high"},
                    "description": "Emergency execution due to system alert",
                },
            },
        ],
        default_parameters={
            "trigger_context": {"source": "manual"},
            "description": "Manual workflow execution",
        },
    ),
)


# Cron trigger - scheduled execution
CRON_TRIGGER_SPEC = NodeSpec(
    node_type=NodeType.TRIGGER,
    subtype=TriggerSubtype.CRON,
    description="Scheduled trigger based on cron expressions",
    display_name="Cron Trigger",
    category="triggers",
    template_id="trigger_cron",
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
    manual_invocation=ManualInvocationSpec(
        supported=True,
        description="Simulate cron trigger execution with custom scheduled time",
        parameter_schema={
            "type": "object",
            "properties": {
                "scheduled_time": {
                    "type": "string",
                    "format": "date-time",
                    "description": "Simulated scheduled execution time (ISO format)",
                },
                "cron_context": {
                    "type": "object",
                    "description": "Additional context for cron execution",
                },
            },
        },
        parameter_examples=[
            {
                "name": "Test Daily Job",
                "description": "Simulate daily scheduled execution",
                "parameters": {
                    "scheduled_time": "2025-01-28T09:00:00Z",
                    "cron_context": {"job_type": "daily", "simulation": True},
                },
            },
            {
                "name": "Test Weekly Report",
                "description": "Simulate weekly report generation",
                "parameters": {
                    "scheduled_time": "2025-01-27T00:00:00Z",
                    "cron_context": {"job_type": "weekly", "report_type": "analytics"},
                },
            },
        ],
        default_parameters={"cron_context": {"simulation": True}},
    ),
)


# Webhook trigger - HTTP endpoint
WEBHOOK_TRIGGER_SPEC = NodeSpec(
    node_type=NodeType.TRIGGER,
    subtype=TriggerSubtype.WEBHOOK,
    description="HTTP webhook trigger that responds to incoming requests",
    display_name="Webhook Trigger",
    category="triggers",
    template_id="trigger_webhook",
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
    manual_invocation=ManualInvocationSpec(
        supported=True,
        description="Simulate webhook HTTP requests with custom headers, body, and query parameters",
        parameter_schema={
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                    "default": "POST",
                    "description": "HTTP method",
                },
                "headers": {
                    "type": "object",
                    "description": "HTTP headers",
                    "default": {"Content-Type": "application/json"},
                },
                "body": {"type": "object", "description": "Request body payload"},
                "query_params": {"type": "object", "description": "URL query parameters"},
            },
        },
        parameter_examples=[
            {
                "name": "Simple API Webhook",
                "description": "Basic webhook with JSON payload",
                "parameters": {
                    "method": "POST",
                    "headers": {"Content-Type": "application/json", "X-Source": "api"},
                    "body": {"event": "user.created", "user_id": 123},
                },
            },
            {
                "name": "GitHub Push Webhook",
                "description": "Simulate GitHub push event",
                "parameters": {
                    "method": "POST",
                    "headers": {"X-GitHub-Event": "push"},
                    "body": {
                        "ref": "refs/heads/main",
                        "repository": {"name": "test-repo"},
                        "commits": [{"message": "Test commit"}],
                    },
                },
            },
            {
                "name": "Form Data Webhook",
                "description": "Webhook with form data",
                "parameters": {
                    "method": "POST",
                    "headers": {"Content-Type": "application/x-www-form-urlencoded"},
                    "body": {"name": "John Doe", "email": "john@example.com"},
                },
            },
        ],
        default_parameters={
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "body": {},
        },
    ),
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
            description="Slack workspace ID to monitor (auto-resolved from user's OAuth token - should not be manually configured)",
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
    manual_invocation=ManualInvocationSpec(
        supported=True,
        description="Simulate Slack events like messages, mentions, and interactions",
        parameter_schema={
            "type": "object",
            "properties": {
                "event_type": {
                    "type": "string",
                    "enum": [
                        "message",
                        "app_mention",
                        "reaction_added",
                        "pin_added",
                        "file_shared",
                    ],
                    "default": "message",
                    "description": "Type of Slack event to simulate",
                },
                "message": {"type": "string", "description": "Message text content"},
                "user_id": {
                    "type": "string",
                    "default": "U1234567890",
                    "description": "Slack user ID",
                },
                "channel_name": {
                    "type": "string",
                    "default": "general",
                    "description": "Slack channel name",
                },
                "thread_ts": {"type": "string", "description": "Thread timestamp (optional)"},
            },
            "required": ["message"],
        },
        parameter_examples=[
            {
                "name": "Simple Message",
                "description": "Basic Slack message",
                "parameters": {
                    "event_type": "message",
                    "message": "Hello from the workflow!",
                    "user_id": "U1234567890",
                    "channel_name": "general",
                },
            },
            {
                "name": "Bot Mention",
                "description": "Message mentioning the bot",
                "parameters": {
                    "event_type": "app_mention",
                    "message": "@bot please help with this task",
                    "user_id": "U1234567890",
                    "channel_name": "support",
                },
            },
            {
                "name": "Thread Reply",
                "description": "Reply in a thread",
                "parameters": {
                    "event_type": "message",
                    "message": "This is a thread reply",
                    "user_id": "U1234567890",
                    "channel_name": "general",
                    "thread_ts": "1642505400.123456",
                },
            },
        ],
        default_parameters={
            "event_type": "message",
            "user_id": "U1234567890",
            "channel_name": "general",
        },
    ),
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
    manual_invocation=ManualInvocationSpec(
        supported=True,
        description="Simulate incoming email messages with custom sender, subject, and content",
        parameter_schema={
            "type": "object",
            "properties": {
                "from": {
                    "type": "string",
                    "format": "email",
                    "description": "Email sender address",
                },
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {"type": "string", "description": "Email body content"},
                "to": {
                    "type": "string",
                    "format": "email",
                    "description": "Email recipient (optional)",
                },
                "attachments": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of attachment filenames",
                },
            },
            "required": ["from", "subject", "body"],
        },
        parameter_examples=[
            {
                "name": "Customer Support Email",
                "description": "Simulate customer support request",
                "parameters": {
                    "from": "customer@example.com",
                    "subject": "Login Issue - Urgent",
                    "body": "I cannot access my account. Please help!",
                    "attachments": ["screenshot.png"],
                },
            },
            {
                "name": "Newsletter Email",
                "description": "Simulate newsletter subscription",
                "parameters": {
                    "from": "newsletter@company.com",
                    "subject": "Weekly Update - January 2025",
                    "body": "Here are this week's highlights...",
                    "attachments": [],
                },
            },
        ],
        default_parameters={"attachments": []},
    ),
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
            name="event_config",
            type=ParameterType.JSON,
            required=True,
            description="Event-specific configuration. Each key is an event type with its filters. See enum_values for supported events.",
            enum_values=[
                "push",
                "pull_request",
                "pull_request_review",
                "pull_request_review_comment",
                "pull_request_review_thread",
                "issues",
                "issue_comment",
                "commit_comment",
                "release",
                "create",
                "delete",
                "fork",
                "repository",
                "workflow_run",
                "workflow_dispatch",
                "workflow_job",
                "label",
                "milestone",
                "star",
                "watch",
            ],
        ),
        ParameterDef(
            name="author_filter",
            type=ParameterType.STRING,
            required=False,
            description="Global filter by commit/PR/issue author (username or regex pattern). Applies to all events.",
        ),
        ParameterDef(
            name="ignore_bots",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Globally ignore events from bot accounts (users with [bot] suffix or type 'Bot')",
        ),
        ParameterDef(
            name="require_signature_verification",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Verify GitHub webhook signature for security",
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
                schema='{"event": "string", "action": "string", "repository": "object", "sender": "object", "payload": "object", "timestamp": "string", "review_state": "string", "ref_type": "string", "workflow": "object", "job": "object"}',
                examples=[
                    '{"event": "push", "action": null, "repository": {"name": "my-repo", "owner": {"login": "user"}}, "sender": {"login": "developer"}, "payload": {"ref": "refs/heads/main", "commits": [{"message": "Fix bug"}]}, "timestamp": "2025-01-28T10:30:00Z"}',
                    '{"event": "pull_request", "action": "opened", "repository": {"name": "my-repo", "owner": {"login": "user"}}, "sender": {"login": "contributor"}, "payload": {"number": 42, "title": "New feature", "draft": false}, "timestamp": "2025-01-28T10:30:00Z"}',
                    '{"event": "pull_request_review", "action": "submitted", "review_state": "approved", "repository": {"name": "my-repo", "owner": {"login": "user"}}, "sender": {"login": "reviewer"}, "payload": {"review": {"state": "approved", "body": "LGTM"}}, "timestamp": "2025-01-28T10:30:00Z"}',
                    '{"event": "workflow_run", "action": "completed", "repository": {"name": "my-repo", "owner": {"login": "user"}}, "sender": {"login": "github-actions[bot]"}, "workflow": {"name": "CI", "path": ".github/workflows/ci.yml"}, "payload": {"conclusion": "success", "run_number": 123}, "timestamp": "2025-01-28T10:30:00Z"}',
                    '{"event": "create", "action": null, "ref_type": "branch", "repository": {"name": "my-repo", "owner": {"login": "user"}}, "sender": {"login": "developer"}, "payload": {"ref": "feature-branch", "ref_type": "branch"}, "timestamp": "2025-01-28T10:30:00Z"}',
                ],
            ),
            validation_schema='{"type": "object", "properties": {"event": {"type": "string"}, "action": {"type": ["string", "null"]}, "repository": {"type": "object"}, "sender": {"type": "object"}, "payload": {"type": "object"}, "timestamp": {"type": "string"}, "review_state": {"type": ["string", "null"]}, "ref_type": {"type": ["string", "null"]}, "workflow": {"type": ["object", "null"]}, "job": {"type": ["object", "null"]}}, "required": ["event", "repository", "sender", "payload", "timestamp"]}',
        )
    ],
    manual_invocation=ManualInvocationSpec(
        supported=True,
        description="Simulate GitHub webhook events like push, pull request, and workflow events",
        parameter_schema={
            "type": "object",
            "properties": {
                "event": {
                    "type": "string",
                    "enum": [
                        "push",
                        "pull_request",
                        "issues",
                        "release",
                        "workflow_run",
                        "create",
                        "delete",
                    ],
                    "default": "push",
                    "description": "GitHub event type",
                },
                "action": {
                    "type": "string",
                    "description": "Event action (e.g., opened, closed, synchronize)",
                },
                "repository": {
                    "type": "string",
                    "pattern": "^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$",
                    "description": "Repository in owner/name format",
                },
                "ref": {"type": "string", "description": "Git reference (branch/tag)"},
                "payload": {"type": "object", "description": "Event-specific payload data"},
            },
            "required": ["event", "repository"],
        },
        parameter_examples=[
            {
                "name": "Push to Main",
                "description": "Simulate push to main branch",
                "parameters": {
                    "event": "push",
                    "repository": "myorg/myrepo",
                    "ref": "refs/heads/main",
                    "payload": {"commits": [{"message": "Fix critical bug", "id": "abc123"}]},
                },
            },
            {
                "name": "Pull Request Opened",
                "description": "Simulate new pull request",
                "parameters": {
                    "event": "pull_request",
                    "action": "opened",
                    "repository": "myorg/myrepo",
                    "payload": {"number": 42, "title": "Add new feature", "draft": False},
                },
            },
            {
                "name": "Release Created",
                "description": "Simulate new release",
                "parameters": {
                    "event": "release",
                    "action": "published",
                    "repository": "myorg/myrepo",
                    "payload": {"tag_name": "v1.2.0", "name": "Version 1.2.0"},
                },
            },
        ],
        default_parameters={"event": "push", "ref": "refs/heads/main"},
    ),
)
