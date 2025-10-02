"""
HTTP_REQUEST Action Node Specification

System action for making HTTP requests. This is an internal system action
for API calls, webhook requests, and HTTP-based integrations.
"""

from typing import Any, Dict, List

from shared.models.node_enums import ActionSubtype, NodeType
from shared.node_specs.base import COMMON_CONFIGS, BaseNodeSpec


class HTTPRequestActionSpec(BaseNodeSpec):
    """HTTP Request action specification for system HTTP operations."""

    def __init__(self):
        super().__init__(
            type=NodeType.ACTION,
            subtype=ActionSubtype.HTTP_REQUEST,
            name="HTTP_Request",
            description="Make HTTP requests to APIs and web services",
            # Configuration parameters
            configurations={
                "method": {
                    "type": "string",
                    "default": "GET",
                    "description": "HTTP请求方法",
                    "required": True,
                    "options": ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
                },
                "url": {
                    "type": "string",
                    "default": "",
                    "description": "请求URL，支持变量替换 {{variable}}",
                    "required": True,
                },
                "headers": {
                    "type": "object",
                    "default": {
                        "Content-Type": "application/json",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
                    },
                    "description": "HTTP请求头",
                    "required": False,
                },
                "query_params": {
                    "type": "object",
                    "default": {},
                    "description": "URL查询参数",
                    "required": False,
                },
                "body_type": {
                    "type": "string",
                    "default": "json",
                    "description": "请求体类型",
                    "required": False,
                    "options": ["json", "form", "raw", "none"],
                },
                "follow_redirects": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否跟随HTTP重定向",
                    "required": False,
                },
                "max_redirects": {
                    "type": "integer",
                    "default": 5,
                    "min": 0,
                    "max": 20,
                    "description": "最大重定向次数",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Default runtime parameters
            default_input_params={
                "body": {},
                "url_variables": {},
                "dynamic_headers": {},
                "dynamic_query_params": {},
            },
            default_output_params={
                "status_code": 0,
                "headers": {},
                "body": "",
                "json": {},
                "success": False,
                "error_message": "",
                "response_time": 0,
                "url": "",
                "redirects": [],
            },
            # Port definitions with comprehensive schemas
            input_ports=[
                {
                    "id": "main",
                    "name": "main",
                    "data_type": "dict",
                    "description": "HTTP request configuration",
                    "required": True,
                    "max_connections": 1,
                }
            ],
            output_ports=[
                {
                    "id": "main",
                    "name": "main",
                    "data_type": "dict",
                    "description": "HTTP response data",
                    "required": False,
                    "max_connections": -1,
                }
            ],
            # Metadata
            tags=["action", "http", "api", "system"],
            # Examples
            examples=[
                {
                    "name": "REST API Call",
                    "description": "Call a REST API to get user information",
                    "configurations": {
                        "method": "GET",
                        "url": "https://api.example.com/users/{{user_id}}",
                        "headers": {
                            "Authorization": "Bearer {{api_token}}",
                            "Accept": "application/json",
                        },
                    },
                    "input_example": {
                        "url_variables": {"user_id": "12345", "api_token": "bearer_token_abcdef"}
                    },
                    "expected_output": {
                        "status_code": 200,
                        "headers": {"content-type": "application/json"},
                        "json": {"id": "12345", "name": "John Doe", "email": "john@example.com"},
                        "success": True,
                        "response_time": 0.45,
                        "url": "https://api.example.com/users/12345",
                    },
                },
                {
                    "name": "POST Data Submission",
                    "description": "Submit form data to an API endpoint",
                    "configurations": {
                        "method": "POST",
                        "url": "https://webhook.site/unique-id",
                        "body_type": "json",
                        "headers": {"Content-Type": "application/json"},
                    },
                    "input_example": {
                        "body": {
                            "name": "Alice Smith",
                            "email": "alice@example.com",
                            "message": "Hello from workflow!",
                        }
                    },
                    "expected_output": {
                        "status_code": 200,
                        "headers": {"content-type": "application/json"},
                        "json": {"success": True, "id": "msg_789"},
                        "success": True,
                        "response_time": 0.78,
                    },
                },
                {
                    "name": "Health Check",
                    "description": "Check if a service is healthy",
                    "configurations": {
                        "method": "GET",
                        "url": "https://api.service.com/health",
                        "timeout": 10,
                        "retry_attempts": 1,
                    },
                    "input_example": {},
                    "expected_output": {
                        "status_code": 200,
                        "body": "OK",
                        "success": True,
                        "response_time": 0.12,
                    },
                },
            ],
        )


# Export the specification instance
HTTP_REQUEST_ACTION_SPEC = HTTPRequestActionSpec()
