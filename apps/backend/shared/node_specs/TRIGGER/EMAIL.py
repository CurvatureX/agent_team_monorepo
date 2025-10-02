"""
EMAIL Trigger Node Specification

Email trigger for incoming email events. This trigger has no input ports
and produces execution context when emails are received.
"""

from typing import Any, Dict, List

from ...models.node_enums import NodeType, TriggerSubtype
from ..base import COMMON_CONFIGS, BaseNodeSpec


class EmailTriggerSpec(BaseNodeSpec):
    """Email trigger specification for incoming email processing."""

    def __init__(self):
        super().__init__(
            type=NodeType.TRIGGER,
            subtype=TriggerSubtype.EMAIL,
            name="Email_Trigger",
            description="Email trigger for processing incoming emails and attachments",
            # Configuration parameters
            configurations={
                "email_provider": {
                    "type": "string",
                    "default": "imap",
                    "description": "邮件服务提供商类型",
                    "required": True,
                    "options": ["imap", "gmail_api", "outlook_api", "webhook"],
                },
                "server_config": {
                    "type": "object",
                    "default": {"host": "", "port": 993, "use_ssl": True},
                    "description": "邮件服务器配置",
                    "required": True,
                },
                "credentials": {
                    "type": "object",
                    "default": {"username": "", "password": ""},
                    "description": "邮件账户凭据",
                    "required": True,
                    "sensitive": True,
                },
                "mailbox": {
                    "type": "string",
                    "default": "INBOX",
                    "description": "监听的邮箱文件夹",
                    "required": False,
                },
                "filter_criteria": {
                    "type": "object",
                    "default": {},
                    "description": "邮件过滤条件",
                    "required": False,
                },
                "subject_keywords": {
                    "type": "array",
                    "default": [],
                    "description": "主题关键词过滤器",
                    "required": False,
                },
                "sender_whitelist": {
                    "type": "array",
                    "default": [],
                    "description": "发件人白名单",
                    "required": False,
                },
                "process_attachments": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否处理附件",
                    "required": False,
                },
                "attachment_types": {
                    "type": "array",
                    "default": ["pdf", "doc", "docx", "txt", "csv", "xlsx"],
                    "description": "允许的附件类型",
                    "required": False,
                },
                "max_attachment_size": {
                    "type": "integer",
                    "default": 10485760,
                    "min": 1024,
                    "max": 52428800,
                    "description": "最大附件大小（字节）",
                    "required": False,
                },
                "polling_interval": {
                    "type": "integer",
                    "default": 300,
                    "min": 30,
                    "max": 3600,
                    "description": "邮件检查间隔（秒）",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Parameter schemas (preferred over legacy defaults)
            input_params={},  # Triggers have no runtime inputs
            output_params={
                "trigger_time": {
                    "type": "string",
                    "default": "",
                    "description": "ISO-8601 trigger time",
                    "required": False,
                },
                "execution_id": {
                    "type": "string",
                    "default": "",
                    "description": "Execution identifier",
                    "required": False,
                },
                "email_id": {
                    "type": "string",
                    "default": "",
                    "description": "Provider-specific email ID",
                    "required": False,
                },
                "sender": {
                    "type": "string",
                    "default": "",
                    "description": "Sender email address",
                    "required": False,
                },
                "recipient": {
                    "type": "string",
                    "default": "",
                    "description": "Recipient email address",
                    "required": False,
                },
                "subject": {
                    "type": "string",
                    "default": "",
                    "description": "Email subject",
                    "required": False,
                },
                "body_text": {
                    "type": "string",
                    "default": "",
                    "description": "Plain text body",
                    "required": False,
                },
                "body_html": {
                    "type": "string",
                    "default": "",
                    "description": "HTML body",
                    "required": False,
                },
                "attachments": {
                    "type": "array",
                    "default": [],
                    "description": "List of attachments with metadata",
                    "required": False,
                },
                "received_date": {
                    "type": "string",
                    "default": "",
                    "description": "ISO-8601 received time",
                    "required": False,
                },
                "trigger_message": {
                    "type": "string",
                    "default": "",
                    "description": "Human-friendly description",
                    "required": False,
                },
                "email_headers": {
                    "type": "object",
                    "default": {},
                    "description": "Email header key-values",
                    "required": False,
                },
            },
            # Port definitions
            input_ports=[],  # Triggers have no input ports
            output_ports=[
                {
                    "id": "main",
                    "name": "main",
                    "data_type": "dict",
                    "description": "Email event output with message content and attachments",
                    "required": False,
                    "max_connections": -1,
                }
            ],
            # Metadata
            tags=["trigger", "email", "imap", "communication", "automation"],
            # Examples
            examples=[
                {
                    "name": "Support Ticket Email",
                    "description": "Process incoming support emails to create tickets",
                    "configurations": {
                        "email_provider": "imap",
                        "server_config": {"host": "imap.gmail.com", "port": 993, "use_ssl": True},
                        "credentials": {
                            "username": "support@company.com",
                            "password": "email_password_123",
                        },
                        "mailbox": "INBOX",
                        "subject_keywords": ["support", "help", "issue", "problem"],
                        "process_attachments": True,
                        "polling_interval": 60,
                    },
                    "expected_output": {
                        "trigger_time": "2025-01-20T14:30:00Z",
                        "execution_id": "email_exec_123",
                        "email_id": "msg_456789",
                        "sender": "customer@example.com",
                        "recipient": "support@company.com",
                        "subject": "Support: Login issues with mobile app",
                        "body_text": "Hi, I'm experiencing login issues with the mobile app. The app crashes when I try to sign in.",
                        "body_html": "<p>Hi, I'm experiencing login issues with the mobile app. The app crashes when I try to sign in.</p>",
                        "attachments": [
                            {
                                "filename": "crash_log.txt",
                                "size": 2048,
                                "content_type": "text/plain",
                                "content": "base64_encoded_content",
                            }
                        ],
                        "received_date": "2025-01-20T14:25:00Z",
                        "trigger_message": "Support email received from customer@example.com: Login issues with mobile app",
                        "email_headers": {
                            "message-id": "<msg_456789@example.com>",
                            "date": "Mon, 20 Jan 2025 14:25:00 +0000",
                        },
                    },
                },
                {
                    "name": "Invoice Processing Email",
                    "description": "Process incoming invoices from approved vendors",
                    "configurations": {
                        "email_provider": "gmail_api",
                        "credentials": {
                            "client_id": "gmail_client_id",
                            "client_secret": "gmail_client_secret",
                            "refresh_token": "gmail_refresh_token",
                        },
                        "mailbox": "invoices",
                        "sender_whitelist": [
                            "accounting@vendor1.com",
                            "billing@vendor2.com",
                            "invoices@vendor3.com",
                        ],
                        "process_attachments": True,
                        "attachment_types": ["pdf", "xlsx"],
                        "max_attachment_size": 20971520,
                    },
                    "expected_output": {
                        "trigger_time": "2025-01-20T16:15:00Z",
                        "execution_id": "email_exec_456",
                        "email_id": "gmail_msg_789",
                        "sender": "accounting@vendor1.com",
                        "recipient": "invoices@company.com",
                        "subject": "Invoice #INV-2025-001",
                        "body_text": "Please find attached invoice #INV-2025-001 for services rendered in January 2025.",
                        "body_html": "<p>Please find attached invoice #INV-2025-001 for services rendered in January 2025.</p>",
                        "attachments": [
                            {
                                "filename": "INV-2025-001.pdf",
                                "size": 524288,
                                "content_type": "application/pdf",
                                "content": "base64_encoded_pdf_content",
                            }
                        ],
                        "received_date": "2025-01-20T16:10:00Z",
                        "trigger_message": "Invoice email received from accounting@vendor1.com: Invoice #INV-2025-001",
                        "email_headers": {
                            "message-id": "<gmail_msg_789@vendor1.com>",
                            "x-priority": "3",
                        },
                    },
                },
                {
                    "name": "Newsletter Subscription",
                    "description": "Process newsletter subscription confirmations",
                    "configurations": {
                        "email_provider": "webhook",
                        "server_config": {
                            "webhook_url": "https://api.company.com/webhooks/email",
                            "secret_key": "webhook_secret_123",
                        },
                        "filter_criteria": {
                            "subject_contains": "newsletter",
                            "body_contains": "subscribe",
                        },
                        "process_attachments": False,
                    },
                    "expected_output": {
                        "trigger_time": "2025-01-20T18:45:00Z",
                        "execution_id": "email_exec_789",
                        "email_id": "webhook_msg_101",
                        "sender": "newuser@example.com",
                        "recipient": "newsletter@company.com",
                        "subject": "Please confirm newsletter subscription",
                        "body_text": "I would like to subscribe to your weekly newsletter about product updates.",
                        "body_html": "<p>I would like to subscribe to your weekly newsletter about product updates.</p>",
                        "attachments": [],
                        "received_date": "2025-01-20T18:40:00Z",
                        "trigger_message": "Newsletter subscription request from newuser@example.com",
                        "email_headers": {
                            "from": "newuser@example.com",
                            "to": "newsletter@company.com",
                        },
                    },
                },
                {
                    "name": "Alert System Email",
                    "description": "Process system alert emails from monitoring tools",
                    "configurations": {
                        "email_provider": "imap",
                        "server_config": {"host": "mail.company.com", "port": 993, "use_ssl": True},
                        "credentials": {
                            "username": "alerts@company.com",
                            "password": "alerts_password_456",
                        },
                        "mailbox": "INBOX",
                        "subject_keywords": ["ALERT", "WARNING", "CRITICAL", "DOWN"],
                        "sender_whitelist": [
                            "monitoring@company.com",
                            "nagios@company.com",
                            "alerts@datadog.com",
                        ],
                        "process_attachments": False,
                        "polling_interval": 30,
                    },
                    "expected_output": {
                        "trigger_time": "2025-01-20T20:30:00Z",
                        "execution_id": "email_exec_202",
                        "email_id": "alert_msg_303",
                        "sender": "monitoring@company.com",
                        "recipient": "alerts@company.com",
                        "subject": "CRITICAL: Database server is down",
                        "body_text": "Database server db-prod-01 is not responding. Last check failed at 2025-01-20 20:25:00 UTC.",
                        "body_html": "<p><strong>Database server db-prod-01 is not responding.</strong><br>Last check failed at 2025-01-20 20:25:00 UTC.</p>",
                        "attachments": [],
                        "received_date": "2025-01-20T20:25:00Z",
                        "trigger_message": "Critical alert received: Database server is down",
                        "email_headers": {"x-priority": "1", "x-alert-level": "critical"},
                    },
                },
            ],
        )


# Export the specification instance
EMAIL_TRIGGER_SPEC = EmailTriggerSpec()
