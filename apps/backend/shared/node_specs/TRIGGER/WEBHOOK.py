"""
WEBHOOK Trigger Node Specification

Webhook trigger that responds to HTTP requests. This trigger has no input ports
and produces webhook request data when an HTTP request is received.
"""

from typing import Any, Dict, List

from ...models.node_enums import NodeType, TriggerSubtype
from ..base import COMMON_CONFIGS, BaseNodeSpec


class WebhookTriggerSpec(BaseNodeSpec):
    """Webhook trigger specification following the new workflow architecture."""

    def __init__(self):
        super().__init__(
            type=NodeType.TRIGGER,
            subtype=TriggerSubtype.WEBHOOK,
            name="Webhook_Trigger",
            description="HTTP webhook trigger for external system integration",
            # Configuration parameters
            configurations={
                "webhook_path": {
                    "type": "string",
                    "default": "/webhook",
                    "description": "Webhook接收路径",
                    "required": True,
                },
                "allowed_methods": {
                    "type": "array",
                    "default": ["POST"],
                    "description": "允许的HTTP方法",
                    "required": False,
                    "options": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                },
                "authentication": {
                    "type": "string",
                    "default": "none",
                    "description": "身份验证方式",
                    "required": False,
                    "options": ["none", "header_token", "query_param", "signature"],
                },
                "auth_token": {
                    "type": "string",
                    "default": "",
                    "description": "认证令牌（authentication非none时必需）",
                    "required": False,
                    "sensitive": True,
                },
                "response_format": {
                    "type": "string",
                    "default": "json",
                    "description": "响应格式",
                    "required": False,
                    "options": ["json", "text", "html"],
                },
                **COMMON_CONFIGS,
            },
            # Parameter schemas (preferred over legacy defaults)
            input_params={},  # Triggers have no runtime inputs
            output_params={
                "headers": {
                    "type": "object",
                    "default": {},
                    "description": "HTTP headers received",
                    "required": False,
                },
                "body": {
                    "type": "object",
                    "default": {},
                    "description": "Parsed request body (JSON if applicable)",
                    "required": False,
                },
                "query_params": {
                    "type": "object",
                    "default": {},
                    "description": "Query parameters",
                    "required": False,
                },
                "method": {
                    "type": "string",
                    "default": "",
                    "description": "HTTP method",
                    "required": False,
                    "options": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                },
                "path": {
                    "type": "string",
                    "default": "",
                    "description": "Request path",
                    "required": False,
                },
                "timestamp": {
                    "type": "string",
                    "default": "",
                    "description": "ISO-8601 time when webhook was received",
                    "required": False,
                },
                "client_ip": {
                    "type": "string",
                    "default": "",
                    "description": "Client IP address",
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
                    "description": "Webhook request data including headers, body, and metadata",
                    "required": False,
                    "max_connections": -1,
                }
            ],
            # Metadata
            tags=["trigger", "webhook", "http", "external"],
            # Examples
            examples=[
                {
                    "name": "GitHub Webhook",
                    "description": "Receive GitHub repository events",
                    "configurations": {
                        "webhook_path": "/github-webhook",
                        "allowed_methods": ["POST"],
                        "authentication": "signature",
                        "auth_token": "your-github-secret",
                    },
                    "expected_output": {
                        "headers": {"content-type": "application/json", "x-github-event": "push"},
                        "body": {
                            "ref": "refs/heads/main",
                            "commits": [{"message": "Fix bug", "author": {"name": "developer"}}],
                        },
                        "query_params": {},
                        "method": "POST",
                        "path": "/github-webhook",
                        "timestamp": "2025-01-28T10:30:00Z",
                        "client_ip": "192.30.252.1",
                    },
                },
                {
                    "name": "Simple API Webhook",
                    "description": "Basic webhook for API integration",
                    "configurations": {
                        "webhook_path": "/api/webhook",
                        "allowed_methods": ["POST", "PUT"],
                        "authentication": "header_token",
                        "auth_token": "api-key-12345",
                    },
                    "expected_output": {
                        "headers": {
                            "authorization": "Bearer api-key-12345",
                            "content-type": "application/json",
                        },
                        "body": {"action": "update", "data": {"id": 123}},
                        "query_params": {"source": "external"},
                        "method": "POST",
                        "path": "/api/webhook",
                        "timestamp": "2025-01-28T11:15:00Z",
                        "client_ip": "203.0.113.1",
                    },
                },
            ],
        )


# Export the specification instance
WEBHOOK_TRIGGER_SPEC = WebhookTriggerSpec()
