"""
Human-in-the-Loop node specifications.

This module defines specifications for HUMAN_IN_THE_LOOP_NODE subtypes that enable
human interaction within workflows through various communication channels.
"""

from ...models.node_enums import HumanLoopSubtype, NodeType
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
    node_type=NodeType.HUMAN_IN_THE_LOOP,
    subtype=HumanLoopSubtype.GMAIL_INTERACTION,
    description="Send email via Gmail and wait for human response or approval with integrated response messaging",
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
        # AI Response Analysis parameters
        ParameterDef(
            name="enable_response_analysis",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Enable AI-powered response analysis to classify email responses and eliminate separate IF/AI_AGENT nodes",
        ),
        ParameterDef(
            name="system_prompt",
            type=ParameterType.STRING,
            required=False,
            description="Custom system prompt that defines the AI's role and classification behavior for analyzing responses",
        ),
        ParameterDef(
            name="response_classification_prompt",
            type=ParameterType.STRING,
            required=False,
            description="Custom user prompt for AI email response classification (works with system_prompt to override default analysis)",
        ),
        ParameterDef(
            name="classification_confidence_threshold",
            type=ParameterType.FLOAT,
            required=False,
            default_value=0.7,
            description="Minimum AI confidence score (0.0-1.0) for email response classification",
        ),
        ParameterDef(
            name="custom_classification_categories",
            type=ParameterType.JSON,
            required=False,
            default_value=["confirmed", "rejected", "unrelated"],
            description="Custom categories for email response classification",
        ),
        # Enhanced response messaging parameters
        ParameterDef(
            name="confirmed_message",
            type=ParameterType.STRING,
            required=False,
            description="Email message to send when user confirms/approves (supports templates like {{data.event_id}})",
        ),
        ParameterDef(
            name="rejected_message",
            type=ParameterType.STRING,
            required=False,
            description="Email message to send when user rejects (supports templates)",
        ),
        ParameterDef(
            name="unrelated_message",
            type=ParameterType.STRING,
            required=False,
            description="Email message to send when response is classified as unrelated (supports templates)",
        ),
        ParameterDef(
            name="timeout_message",
            type=ParameterType.STRING,
            required=False,
            description="Email message to send when timeout occurs (supports templates)",
        ),
        ParameterDef(
            name="send_responses_to_recipients",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Whether to send response messages to the original recipients",
        ),
        ParameterDef(
            name="response_recipients",
            type=ParameterType.JSON,
            required=False,
            description="Different recipients for response messages (if send_responses_to_recipients is false)",
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
            name="confirmed",
            type=ConnectionType.MAIN,
            description="Output when AI classifies email response as confirmed/approved (replaces need for separate IF node)",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"classification": "confirmed", "confidence_score": "number", "original_response": "string", "analysis_reasoning": "string", "responder": "object", "response_message_sent": "boolean", "timestamp": "string"}',
            ),
        ),
        OutputPortSpec(
            name="rejected",
            type=ConnectionType.MAIN,
            description="Output when AI classifies email response as rejected/denied (replaces need for separate IF node)",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"classification": "rejected", "confidence_score": "number", "original_response": "string", "analysis_reasoning": "string", "responder": "object", "response_message_sent": "boolean", "timestamp": "string"}',
            ),
        ),
        OutputPortSpec(
            name="unrelated",
            type=ConnectionType.MAIN,
            description="Output when AI classifies email response as unrelated or low confidence (replaces need for separate IF node)",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"classification": "unrelated", "confidence_score": "number", "original_response": "string", "analysis_reasoning": "string", "responder": "object", "response_message_sent": "boolean", "timestamp": "string"}',
            ),
        ),
        OutputPortSpec(
            name="timeout",
            type=ConnectionType.ERROR,
            description="Output when timeout occurs without response",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"classification": "timeout", "timeout_hours": "number", "response_message_sent": "boolean", "timestamp": "string"}',
            ),
        ),
    ],
    examples=[
        {
            "name": "Smart Email Expense Approval with AI Response Analysis",
            "description": "Send expense report for manager approval with AI-powered email response understanding",
            "workflow_guidance": "🎯 NEXT-GEN EMAIL HIL: This single node replaces 6+ separate nodes (HIL + AI_AGENT + IF + 3 EXTERNAL_ACTION nodes). It understands natural email responses like 'Looks good, approve it' or 'This seems too expensive, please provide more details' without requiring structured formats. All response analysis and follow-up messaging is built-in.",
            "parameters": {
                "email_template": "Please review and approve this expense:\n\n**Amount**: ${{data.expense_amount}}\n**Category**: {{data.category}}\n**Employee**: {{data.employee_name}}\n**Date**: {{data.expense_date}}\n**Description**: {{data.description}}\n**Receipt**: {{data.receipt_url}}\n\nSimply reply with your decision in your own words - I'll understand your intent!",
                "recipients": {"to": ["manager@company.com"]},
                "subject": "Smart Expense Approval: ${{data.expense_amount}} - {{data.employee_name}}",
                "timeout_hours": 72,
                "approval_type": "detailed",
                "enable_response_analysis": True,
                "classification_confidence_threshold": 0.8,
                "custom_classification_categories": ["confirmed", "rejected", "unrelated"],
                "response_classification_prompt": "Analyze this manager's email response to an expense approval request. Classify as 'confirmed' for any approval language (approve, looks good, ok, yes, etc.), 'rejected' for any rejection (too much, no, needs more info, etc.), or 'unrelated' for off-topic responses.",
                "confirmed_message": "✅ Your expense of ${{data.expense_amount}} has been approved by {{responder.display_name}} and will be processed in the next payroll. Manager's response: '{{user_response}}'",
                "rejected_message": "❌ Your expense of ${{data.expense_amount}} has been rejected by {{responder.display_name}}. Reason: '{{user_response}}'. Please provide additional documentation and resubmit.",
                "unrelated_message": "🤔 We received your email about the expense of ${{data.expense_amount}}, but couldn't determine your approval decision. Please reply with 'approve' or 'reject'.",
                "timeout_message": "⏰ Approval timeout for expense ${{data.expense_amount}}. No response received within 72 hours. Please resubmit if still needed.",
                "send_responses_to_recipients": True,
            },
        }
    ],
)


# SLACK Human Loop Node
SLACK_HUMAN_LOOP_SPEC = NodeSpec(
    node_type=NodeType.HUMAN_IN_THE_LOOP,
    subtype=HumanLoopSubtype.SLACK_INTERACTION,
    description="Send Slack message and wait for human response or approval with integrated response messaging",
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
        # AI Response Analysis parameters
        ParameterDef(
            name="enable_response_analysis",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Enable AI-powered response analysis to classify user responses and eliminate separate IF/AI_AGENT nodes",
        ),
        ParameterDef(
            name="system_prompt",
            type=ParameterType.STRING,
            required=False,
            description="Custom system prompt that defines the AI's role and classification behavior for analyzing responses",
        ),
        ParameterDef(
            name="response_classification_prompt",
            type=ParameterType.STRING,
            required=False,
            description="Custom user prompt for AI response classification (works with system_prompt to override default analysis)",
        ),
        ParameterDef(
            name="classification_confidence_threshold",
            type=ParameterType.FLOAT,
            required=False,
            default_value=0.7,
            description="Minimum AI confidence score (0.0-1.0) for response classification",
        ),
        ParameterDef(
            name="custom_classification_categories",
            type=ParameterType.JSON,
            required=False,
            default_value=["confirmed", "rejected", "unrelated"],
            description="Custom categories for response classification",
        ),
        # Enhanced response messaging parameters
        ParameterDef(
            name="confirmed_message",
            type=ParameterType.STRING,
            required=False,
            description="Message to send when user confirms/approves (supports templates like {{data.event_id}})",
        ),
        ParameterDef(
            name="rejected_message",
            type=ParameterType.STRING,
            required=False,
            description="Message to send when user rejects (supports templates)",
        ),
        ParameterDef(
            name="unrelated_message",
            type=ParameterType.STRING,
            required=False,
            description="Message to send when response is classified as unrelated (supports templates)",
        ),
        ParameterDef(
            name="timeout_message",
            type=ParameterType.STRING,
            required=False,
            description="Message to send when timeout occurs (supports templates)",
        ),
        ParameterDef(
            name="send_responses_to_channel",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Whether to send response messages to the same channel",
        ),
        ParameterDef(
            name="response_channel",
            type=ParameterType.STRING,
            required=False,
            description="Different channel for response messages (if send_responses_to_channel is false)",
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
            name="confirmed",
            type=ConnectionType.MAIN,
            description="Output when AI classifies response as confirmed/approved (replaces need for separate IF node)",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"classification": "confirmed", "confidence_score": "number", "original_response": "string", "analysis_reasoning": "string", "responder": "object", "response_message_sent": "boolean", "timestamp": "string"}',
            ),
        ),
        OutputPortSpec(
            name="rejected",
            type=ConnectionType.MAIN,
            description="Output when AI classifies response as rejected/denied (replaces need for separate IF node)",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"classification": "rejected", "confidence_score": "number", "original_response": "string", "analysis_reasoning": "string", "responder": "object", "response_message_sent": "boolean", "timestamp": "string"}',
            ),
        ),
        OutputPortSpec(
            name="unrelated",
            type=ConnectionType.MAIN,
            description="Output when AI classifies response as unrelated or low confidence (replaces need for separate IF node)",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"classification": "unrelated", "confidence_score": "number", "original_response": "string", "analysis_reasoning": "string", "responder": "object", "response_message_sent": "boolean", "timestamp": "string"}',
            ),
        ),
        OutputPortSpec(
            name="timeout",
            type=ConnectionType.ERROR,
            description="Output when timeout occurs without any response (includes timeout message sent status)",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"classification": "timeout", "timeout_minutes": "number", "response_message_sent": "boolean", "timestamp": "string"}',
            ),
        ),
    ],
    examples=[
        {
            "name": "Calendar Event Confirmation with AI Response Analysis",
            "description": "Slack approval for calendar event with AI-powered response classification and automatic response messages",
            "workflow_guidance": "🎯 REVOLUTIONARY: This single HIL node replaces 6+ separate nodes (1 HIL + 1 AI_AGENT + 1 IF + 3 EXTERNAL_ACTION nodes). It uses AI to analyze any user response and automatically classifies it as confirmed/rejected/unrelated. No need for separate IF nodes or AI_AGENT nodes for response analysis!",
            "parameters": {
                "channel": "#calendar-approvals",
                "message": "Please confirm this calendar event:\n\n**Title**: {{data.title}}\n**Start**: {{data.start_datetime}}\n**End**: {{data.end_datetime}}\n**Location**: {{data.location}}\n\nRespond with any message - I'll understand your intent!",
                "approval_buttons": ["Confirm", "Reject"],
                "timeout_minutes": 1440,
                "enable_response_analysis": True,
                "classification_confidence_threshold": 0.75,
                "custom_classification_categories": ["confirmed", "rejected", "unrelated"],
                "response_classification_prompt": "Analyze this response to a calendar event confirmation. Classify as 'confirmed' if user wants the event created, 'rejected' if they want to cancel/modify, or 'unrelated' if the response doesn't address the calendar request.",
                "confirmed_message": "✅ Calendar event '{{data.title}}' has been created successfully! Event ID: {{data.event_id}} (AI confidence: {{ai_confidence}})",
                "rejected_message": "❌ Calendar event creation was cancelled per your request.",
                "unrelated_message": "🤔 I didn't understand your response about '{{data.title}}'. Please respond with 'yes' to confirm or 'no' to cancel.",
                "timeout_message": "⏰ No confirmation received for calendar event '{{data.title}}'. Event creation was cancelled due to timeout.",
                "send_responses_to_channel": True,
            },
        },
        {
            "name": "Smart Expense Approval with AI Response Analysis",
            "description": "Manager approval with AI-powered response understanding and finance channel notifications",
            "workflow_guidance": "🎯 ULTRA-COMPACT SOLUTION: This single HIL node replaces 7+ nodes (HIL + AI_AGENT + IF + 4 EXTERNAL_ACTION nodes). It understands natural language responses like 'looks good, approve it' or 'no, too expensive' without requiring exact button clicks. All response analysis and messaging is built-in.",
            "parameters": {
                "channel": "@manager.smith",
                "message": "Please review and approve this expense:\n\n**Amount**: ${{data.amount}}\n**Category**: {{data.category}}\n**Description**: {{data.description}}\n**Receipt**: {{data.receipt_url}}\n\nJust tell me your decision in your own words!",
                "approval_buttons": ["Approve", "Reject", "Request More Info"],
                "timeout_minutes": 2880,
                "enable_response_analysis": True,
                "classification_confidence_threshold": 0.8,
                "custom_classification_categories": ["confirmed", "rejected", "unrelated"],
                "response_classification_prompt": "Analyze the manager's response to an expense approval request. Classify as 'confirmed' for any approval (looks good, approve, yes, ok to pay, etc.), 'rejected' for any rejection (too much, no, deny, need more info, etc.), or 'unrelated' for off-topic responses.",
                "confirmed_message": "✅ Expense of ${{data.amount}} has been approved by {{responder.display_name}} and will be processed in next payroll.",
                "rejected_message": "❌ Expense request for ${{data.amount}} has been rejected by {{responder.display_name}}. Reason: {{user_response}}",
                "unrelated_message": "🤔 Could you please clarify your decision on the ${{data.amount}} expense? Respond with 'approve' or 'reject'.",
                "timeout_message": "⏰ Expense approval request for ${{data.amount}} timed out. Please resubmit if still needed.",
                "send_responses_to_channel": False,
                "response_channel": "#finance-notifications",
            },
        },
    ],
)


# DISCORD Human Loop Node
DISCORD_HUMAN_LOOP_SPEC = NodeSpec(
    node_type=NodeType.HUMAN_IN_THE_LOOP,
    subtype=HumanLoopSubtype.DISCORD_INTERACTION,
    description="Send Discord message and wait for human response with integrated response messaging",
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
        # AI Response Analysis parameters
        ParameterDef(
            name="enable_response_analysis",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Enable AI-powered response analysis to classify Discord responses and eliminate separate IF/AI_AGENT nodes",
        ),
        ParameterDef(
            name="system_prompt",
            type=ParameterType.STRING,
            required=False,
            description="Custom system prompt that defines the AI's role and classification behavior for analyzing responses",
        ),
        ParameterDef(
            name="response_classification_prompt",
            type=ParameterType.STRING,
            required=False,
            description="Custom user prompt for AI Discord response classification (works with system_prompt to override default analysis)",
        ),
        ParameterDef(
            name="classification_confidence_threshold",
            type=ParameterType.FLOAT,
            required=False,
            default_value=0.7,
            description="Minimum AI confidence score (0.0-1.0) for Discord response classification",
        ),
        ParameterDef(
            name="custom_classification_categories",
            type=ParameterType.JSON,
            required=False,
            default_value=["confirmed", "rejected", "unrelated"],
            description="Custom categories for Discord response classification",
        ),
        # Enhanced response messaging parameters
        ParameterDef(
            name="confirmed_message",
            type=ParameterType.STRING,
            required=False,
            description="Discord message to send when user confirms/approves (supports templates like {{data.event_id}})",
        ),
        ParameterDef(
            name="rejected_message",
            type=ParameterType.STRING,
            required=False,
            description="Discord message to send when user rejects (supports templates)",
        ),
        ParameterDef(
            name="unrelated_message",
            type=ParameterType.STRING,
            required=False,
            description="Discord message to send when response is classified as unrelated (supports templates)",
        ),
        ParameterDef(
            name="timeout_message",
            type=ParameterType.STRING,
            required=False,
            description="Discord message to send when timeout occurs (supports templates)",
        ),
        ParameterDef(
            name="send_responses_to_channel",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Whether to send response messages to the same channel",
        ),
        ParameterDef(
            name="response_channel_id",
            type=ParameterType.STRING,
            required=False,
            description="Different Discord channel ID for response messages (if send_responses_to_channel is false)",
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
    examples=[
        {
            "name": "Team Decision with Integrated Discord Messaging",
            "description": "Discord approval for team decisions with automatic response notifications",
            "workflow_guidance": "🎯 COMPLETE HIL SOLUTION: This single node handles Discord message sending, approval collection, AND response messaging. Do NOT add separate EXTERNAL_ACTION nodes for approved_message, rejected_message, or timeout_message - they are built into this node.",
            "parameters": {
                "channel_id": "123456789012345678",
                "message_template": "🗳️ **Team Decision Required**\n\n{{data.decision_topic}}\n\n**Proposed Action**: {{data.action}}\n**Impact**: {{data.impact}}\n**Deadline**: {{data.deadline}}",
                "timeout_minutes": 720,
                "approved_message": "✅ Team decision approved! {{data.action}} will proceed as planned.",
                "rejected_message": "❌ Team decision rejected. {{data.action}} will not proceed.",
                "timeout_message": "⏰ No response received for team decision on {{data.decision_topic}}. Decision is deferred.",
                "send_responses_to_channel": True,
            },
        }
    ],
)


# TELEGRAM Human Loop Node
TELEGRAM_HUMAN_LOOP_SPEC = NodeSpec(
    node_type=NodeType.HUMAN_IN_THE_LOOP,
    subtype=HumanLoopSubtype.TELEGRAM_INTERACTION,
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
    node_type=NodeType.HUMAN_IN_THE_LOOP,
    subtype=HumanLoopSubtype.IN_APP_APPROVAL,
    description="Send in-app notification and wait for human interaction with integrated response messaging",
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
        # AI Response Analysis parameters
        ParameterDef(
            name="enable_response_analysis",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Enable AI-powered response analysis to classify in-app responses and eliminate separate IF/AI_AGENT nodes",
        ),
        ParameterDef(
            name="system_prompt",
            type=ParameterType.STRING,
            required=False,
            description="Custom system prompt that defines the AI's role and classification behavior for analyzing responses",
        ),
        ParameterDef(
            name="response_classification_prompt",
            type=ParameterType.STRING,
            required=False,
            description="Custom user prompt for AI in-app response classification (works with system_prompt to override default analysis)",
        ),
        ParameterDef(
            name="classification_confidence_threshold",
            type=ParameterType.FLOAT,
            required=False,
            default_value=0.7,
            description="Minimum AI confidence score (0.0-1.0) for in-app response classification",
        ),
        ParameterDef(
            name="custom_classification_categories",
            type=ParameterType.JSON,
            required=False,
            default_value=["confirmed", "rejected", "unrelated"],
            description="Custom categories for in-app response classification",
        ),
        # Enhanced response messaging parameters
        ParameterDef(
            name="confirmed_message",
            type=ParameterType.STRING,
            required=False,
            description="In-app notification to send when user confirms/approves (supports templates like {{data.event_id}})",
        ),
        ParameterDef(
            name="rejected_message",
            type=ParameterType.STRING,
            required=False,
            description="In-app notification to send when user rejects (supports templates)",
        ),
        ParameterDef(
            name="unrelated_message",
            type=ParameterType.STRING,
            required=False,
            description="In-app notification to send when response is classified as unrelated (supports templates)",
        ),
        ParameterDef(
            name="timeout_message",
            type=ParameterType.STRING,
            required=False,
            description="In-app notification to send when timeout occurs (supports templates)",
        ),
        ParameterDef(
            name="send_responses_to_user",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Whether to send response notifications to the same user",
        ),
        ParameterDef(
            name="response_user_ids",
            type=ParameterType.JSON,
            required=False,
            description="Different user IDs for response notifications (if send_responses_to_user is false)",
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
    examples=[
        {
            "name": "Document Review with In-App Notifications",
            "description": "In-app approval for document reviews with automatic status notifications",
            "workflow_guidance": "🎯 ALL-IN-ONE HIL NODE: This node sends the review request, waits for approval, AND sends response notifications. Do NOT create additional EXTERNAL_ACTION nodes for approved_message, rejected_message, or timeout_message - they are integrated into this single node.",
            "parameters": {
                "notification_type": "review",
                "title": "Document Review Required",
                "message": "Please review and approve this document:\n\n**Title**: {{data.doc_title}}\n**Author**: {{data.author}}\n**Summary**: {{data.summary}}\n**Changes**: {{data.changes}}",
                "timeout_minutes": 2880,
                "priority": "high",
                "approved_message": "✅ Document '{{data.doc_title}}' has been approved and published.",
                "rejected_message": "❌ Document '{{data.doc_title}}' requires revision before approval.",
                "timeout_message": "⏰ Review timeout for document '{{data.doc_title}}'. Please review when available.",
                "send_responses_to_user": True,
            },
        }
    ],
)


# Human Approval - Generic approval workflow
APPROVAL_SPEC = NodeSpec(
    node_type=NodeType.HUMAN_IN_THE_LOOP,
    subtype="APPROVAL",  # Using string to avoid conflict
    description="Wait for human approval before proceeding",
    display_name="Human Approval",
    category="human_interaction",
    template_id="human_approval",
    parameters=[
        ParameterDef(
            name="approval_message",
            type=ParameterType.STRING,
            required=True,
            description="Message to display for approval request",
        ),
        ParameterDef(
            name="timeout_hours",
            type=ParameterType.INTEGER,
            required=False,
            default_value=24,
            description="Hours to wait for approval before timeout",
        ),
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=False,
            description="Data to include in approval request",
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="approved",
            type=ConnectionType.MAIN,
            description="Output when request is approved",
        ),
        OutputPortSpec(
            name="rejected",
            type=ConnectionType.ERROR,
            description="Output when request is rejected",
        ),
    ],
)
