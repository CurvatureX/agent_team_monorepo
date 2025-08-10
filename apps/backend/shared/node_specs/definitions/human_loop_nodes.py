"""
Human-in-the-Loop node specifications.

This module defines specifications for HUMAN_IN_THE_LOOP_NODE subtypes that enable
human interaction within workflows through various communication channels.
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

# GMAIL Human Loop Node
GMAIL_HUMAN_LOOP_SPEC = NodeSpec(
    node_type="HUMAN_IN_THE_LOOP",
    subtype="HUMAN_GMAIL",
    description="Send email via Gmail and wait for human response or approval",
    parameters=[
        ParameterDef(
            name="email_template",
            type=ParameterType.STRING,
            required=True,
            description="Email template with placeholders for dynamic content",
        ),
        ParameterDef(
            name="recipients",
            type=ParameterType.JSON,
            required=True,
            description="List of email recipients (to, cc, bcc)",
        ),
        ParameterDef(
            name="subject",
            type=ParameterType.STRING,
            required=False,
            default_value="Workflow Approval Required",
            description="Email subject line",
        ),
        ParameterDef(
            name="timeout_hours",
            type=ParameterType.INTEGER,
            required=False,
            default_value=24,
            description="Hours to wait for response before timeout",
        ),
        ParameterDef(
            name="approval_type",
            type=ParameterType.ENUM,
            required=False,
            default_value="simple",
            enum_values=["simple", "detailed", "custom"],
            description="Type of approval interface to include",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=True,
            description="Data to include in the email and approval context",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"data": "object", "context": "object", "approval_data": "object"}',
            ),
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="approved",
            type=ConnectionType.MAIN,
            description="Output when human approves the request",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"approved": true, "response": "string", "timestamp": "string", "approver": "string"}',
            ),
        ),
        OutputPortSpec(
            name="rejected",
            type=ConnectionType.MAIN,
            description="Output when human rejects the request",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"approved": false, "reason": "string", "timestamp": "string", "approver": "string"}',
            ),
        ),
        OutputPortSpec(
            name="timeout",
            type=ConnectionType.ERROR,
            description="Output when timeout occurs without response",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"timeout": true, "timeout_hours": "number", "timestamp": "string"}',
            ),
        ),
    ],
    examples=[
        {
            "name": "Expense Approval",
            "description": "Send expense report for manager approval",
            "parameters": {
                "email_template": "Please review and approve this expense: {{expense_amount}}",
                "recipients": {"to": ["manager@company.com"]},
                "subject": "Expense Approval: {{expense_amount}}",
            },
        }
    ],
)


# SLACK Human Loop Node
SLACK_HUMAN_LOOP_SPEC = NodeSpec(
    node_type="HUMAN_IN_THE_LOOP",
    subtype="HUMAN_SLACK",
    description="Send Slack message and wait for human response or approval",
    parameters=[
        ParameterDef(
            name="channel",
            type=ParameterType.STRING,
            required=True,
            description="Slack channel ID or name",
        ),
        ParameterDef(
            name="message",
            type=ParameterType.STRING,
            required=True,
            description="Message content",
        ),
        ParameterDef(
            name="approval_buttons",
            type=ParameterType.JSON,
            required=False,
            default_value=["Approve", "Reject"],
            description="Approval buttons",
        ),
        ParameterDef(
            name="timeout_minutes",
            type=ParameterType.INTEGER,
            required=False,
            default_value=60,
            description="Timeout in minutes",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=True,
            description="Data to include in the Slack message",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"message_data": "object", "context": "object"}',
            ),
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="approved",
            type=ConnectionType.MAIN,
            description="Output when user approves via Slack",
        ),
        OutputPortSpec(
            name="rejected",
            type=ConnectionType.MAIN,
            description="Output when user rejects via Slack",
        ),
        OutputPortSpec(
            name="timeout",
            type=ConnectionType.ERROR,
            description="Output when timeout occurs",
        ),
    ],
)


# DISCORD Human Loop Node
DISCORD_HUMAN_LOOP_SPEC = NodeSpec(
    node_type="HUMAN_IN_THE_LOOP",
    subtype="HUMAN_DISCORD",
    description="Send Discord message and wait for human response",
    parameters=[
        ParameterDef(
            name="channel_id",
            type=ParameterType.STRING,
            required=True,
            description="Discord channel ID",
        ),
        ParameterDef(
            name="message_template",
            type=ParameterType.STRING,
            required=True,
            description="Message template with placeholders",
        ),
        ParameterDef(
            name="timeout_minutes",
            type=ParameterType.INTEGER,
            required=False,
            default_value=30,
            description="Minutes to wait for response",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=True,
            description="Data for Discord message",
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="response",
            type=ConnectionType.MAIN,
            description="Human response from Discord",
        ),
        OutputPortSpec(
            name="timeout",
            type=ConnectionType.ERROR,
            description="Timeout without response",
        ),
    ],
)


# TELEGRAM Human Loop Node
TELEGRAM_HUMAN_LOOP_SPEC = NodeSpec(
    node_type="HUMAN_IN_THE_LOOP",
    subtype="HUMAN_TELEGRAM",
    description="Send Telegram message and wait for human response",
    parameters=[
        ParameterDef(
            name="chat_id",
            type=ParameterType.STRING,
            required=True,
            description="Telegram chat ID",
        ),
        ParameterDef(
            name="message_template",
            type=ParameterType.STRING,
            required=True,
            description="Message template with placeholders",
        ),
        ParameterDef(
            name="timeout_minutes",
            type=ParameterType.INTEGER,
            required=False,
            default_value=30,
            description="Minutes to wait for response",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=True,
            description="Data for Telegram message",
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="response",
            type=ConnectionType.MAIN,
            description="Human response from Telegram",
        ),
        OutputPortSpec(
            name="timeout",
            type=ConnectionType.ERROR,
            description="Timeout without response",
        ),
    ],
)


# APP Human Loop Node
APP_HUMAN_LOOP_SPEC = NodeSpec(
    node_type="HUMAN_IN_THE_LOOP",
    subtype="HUMAN_APP",
    description="Send in-app notification and wait for human interaction",
    parameters=[
        ParameterDef(
            name="notification_type",
            type=ParameterType.ENUM,
            required=True,
            enum_values=["approval", "input", "review", "confirmation"],
            description="Type of human interaction required",
        ),
        ParameterDef(
            name="title",
            type=ParameterType.STRING,
            required=False,
            default_value="Action Required",
            description="Notification title",
        ),
        ParameterDef(
            name="message",
            type=ParameterType.STRING,
            required=True,
            description="Notification message content",
        ),
        ParameterDef(
            name="timeout_minutes",
            type=ParameterType.INTEGER,
            required=False,
            default_value=60,
            description="Minutes to wait for response",
        ),
        ParameterDef(
            name="priority",
            type=ParameterType.ENUM,
            required=False,
            default_value="normal",
            enum_values=["low", "normal", "high", "urgent"],
            description="Notification priority level",
        ),
        ParameterDef(
            name="required_fields",
            type=ParameterType.JSON,
            required=False,
            default_value=[],
            description="Fields that require user input",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=True,
            description="Data for the human interaction",
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="completed",
            type=ConnectionType.MAIN,
            description="Output when human completes the interaction",
        ),
        OutputPortSpec(
            name="timeout",
            type=ConnectionType.ERROR,
            description="Output when timeout occurs",
        ),
    ],
)
