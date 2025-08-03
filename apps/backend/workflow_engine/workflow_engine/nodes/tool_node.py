"""
Tool Node Executor.

Handles tool operations like MCP tools, calendar operations, email, HTTP requests,
and external API integrations. Extended to support the external API integration system.
"""

import json
import time
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field

from .base import BaseNodeExecutor, NodeExecutionContext, NodeExecutionResult, ExecutionStatus
from ..services.api_adapters.base import (
    APIAdapter, APIAdapterRegistry, HTTPClientMixin, HTTPConfig,
    APIError, ValidationError, NetworkError, AuthenticationError
)


@dataclass
class HTTPToolConfig:
    """HTTP工具配置"""
    method: str = "GET"
    url: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)
    body: Optional[Any] = None
    auth_config: Optional[Dict[str, Any]] = None
    timeout: int = 30
    follow_redirects: bool = True
    verify_ssl: bool = True
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        
        if not self.url:
            errors.append("URL is required")
        
        if self.method.upper() not in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]:
            errors.append(f"Invalid HTTP method: {self.method}")
        
        if self.timeout <= 0:
            errors.append("Timeout must be positive")
        
        return errors


@dataclass
class ExternalAPIToolConfig:
    """外部API工具配置"""
    api_service: str
    operation: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    credential_id: Optional[str] = None
    timeout_seconds: int = 30
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        
        if not self.api_service:
            errors.append("API service is required")
        
        if not self.operation:
            errors.append("Operation is required")
        
        # 验证API服务是否可用 - 暂时跳过，因为需要导入循环依赖
        # 在实际使用时会在execute方法中进行验证
        
        return errors


class ToolNodeExecutor(BaseNodeExecutor, HTTPClientMixin):
    """Executor for TOOL_NODE type.
    
    Extended to support HTTP tools and external API integration.
    """
    
    def __init__(self, http_config: Optional[HTTPConfig] = None):
        super().__init__()
        HTTPClientMixin.__init__(self, http_config)
    
    def get_supported_subtypes(self) -> List[str]:
        """Get supported tool subtypes."""
        return [
            "MCP",
            "CALENDAR", 
            "EMAIL",
            "HTTP",
            "HTTP_ADVANCED",  # 高级HTTP工具，支持更多认证方式
            "EXTERNAL_API"    # 外部API调用工具
        ]
    
    def validate(self, node: Any) -> List[str]:
        """Validate tool node configuration."""
        errors = []
        
        if not node.subtype:
            errors.append("Tool subtype is required")
            return errors
        
        subtype = node.subtype
        
        if subtype == "MCP":
            errors.extend(self._validate_required_parameters(node, ["tool_name", "operation"]))
        
        elif subtype == "CALENDAR":
            errors.extend(self._validate_required_parameters(node, ["calendar_id", "operation"]))
            operation = node.parameters.get("operation", "")
            if operation not in ["list_events", "create_event", "update_event", "delete_event"]:
                errors.append(f"Invalid calendar operation: {operation}")
        
        elif subtype == "EMAIL":
            errors.extend(self._validate_required_parameters(node, ["operation"]))
            operation = node.parameters.get("operation", "")
            if operation not in ["send", "read", "search", "delete"]:
                errors.append(f"Invalid email operation: {operation}")
        
        elif subtype == "HTTP":
            errors.extend(self._validate_required_parameters(node, ["method", "url"]))
            method = node.parameters.get("method", "").upper()
            if method not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                errors.append(f"Invalid HTTP method: {method}")
        
        elif subtype == "HTTP_ADVANCED":
            errors.extend(self._validate_required_parameters(node, ["method", "url"]))
            # 验证HTTP工具配置
            try:
                config_data = node.parameters.get("http_config", {})
                config = HTTPToolConfig(**config_data)
                errors.extend(config.validate())
            except Exception as e:
                errors.append(f"Invalid HTTP tool configuration: {str(e)}")
        
        elif subtype == "EXTERNAL_API":
            errors.extend(self._validate_required_parameters(node, ["api_service", "operation"]))
            # 验证外部API配置
            try:
                config_data = {
                    "api_service": node.parameters.get("api_service", ""),
                    "operation": node.parameters.get("operation", ""),
                    "parameters": node.parameters.get("parameters", {}),
                    "credential_id": node.parameters.get("credential_id"),
                    "timeout_seconds": node.parameters.get("timeout_seconds", 30)
                }
                config = ExternalAPIToolConfig(**config_data)
                errors.extend(config.validate())
            except Exception as e:
                errors.append(f"Invalid external API configuration: {str(e)}")
        
        return errors
    
    async def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute tool node."""
        start_time = time.time()
        logs = []
        
        try:
            subtype = context.node.subtype
            logs.append(f"Executing tool node with subtype: {subtype}")
            
            if subtype == "MCP":
                return self._execute_mcp_tool(context, logs, start_time)
            elif subtype == "CALENDAR":
                return self._execute_calendar_tool(context, logs, start_time)
            elif subtype == "EMAIL":
                return self._execute_email_tool(context, logs, start_time)
            elif subtype == "HTTP":
                return self._execute_http_tool(context, logs, start_time)
            elif subtype == "HTTP_ADVANCED":
                return await self._execute_http_advanced_tool(context, logs, start_time)
            elif subtype == "EXTERNAL_API":
                return await self._execute_external_api_tool(context, logs, start_time)
            else:
                return self._create_error_result(
                    f"Unsupported tool subtype: {subtype}",
                    execution_time=time.time() - start_time,
                    logs=logs
                )
        
        except Exception as e:
            return self._create_error_result(
                f"Error executing tool: {str(e)}",
                error_details={"exception": str(e), "exception_type": type(e).__name__},
                execution_time=time.time() - start_time,
                logs=logs
            )
        finally:
            # 确保清理HTTP客户端
            try:
                await self.close_http_client()
            except Exception:
                pass
    
    async def cleanup_execution(self, context: NodeExecutionContext) -> None:
        """清理执行环境。"""
        await self.close_http_client()
        super().cleanup_execution(context)
    
    def _execute_mcp_tool(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute MCP tool."""
        tool_name = context.get_parameter("tool_name", "")
        operation = context.get_parameter("operation", "")
        parameters = context.get_parameter("parameters", {})
        
        logs.append(f"MCP tool: {tool_name}, operation: {operation}")
        
        # Mock MCP tool execution
        tool_result = {
            "tool_name": tool_name,
            "operation": operation,
            "parameters": parameters,
            "result": f"Mock result from {tool_name} tool",
            "executed_at": datetime.now().isoformat()
        }
        
        output_data = {
            "tool_type": "mcp",
            "tool_name": tool_name,
            "operation": operation,
            "parameters": parameters,
            "result": tool_result,
            "success": True,
            "executed_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_calendar_tool(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute calendar tool."""
        calendar_id = context.get_parameter("calendar_id", "primary")
        operation = context.get_parameter("operation", "list_events")
        start_date = context.get_parameter("start_date", "")
        end_date = context.get_parameter("end_date", "")
        
        logs.append(f"Calendar tool: {operation} on {calendar_id}")
        
        # Mock calendar operations
        if operation == "list_events":
            events = self._mock_list_events(calendar_id, start_date, end_date)
            result = {"events": events, "count": len(events)}
        elif operation == "create_event":
            event_data = context.get_parameter("event_data", {})
            result = self._mock_create_event(calendar_id, event_data)
        elif operation == "update_event":
            event_id = context.get_parameter("event_id", "")
            event_data = context.get_parameter("event_data", {})
            result = self._mock_update_event(calendar_id, event_id, event_data)
        elif operation == "delete_event":
            event_id = context.get_parameter("event_id", "")
            result = self._mock_delete_event(calendar_id, event_id)
        else:
            result = {"error": f"Unknown operation: {operation}"}
        
        output_data = {
            "tool_type": "calendar",
            "calendar_id": calendar_id,
            "operation": operation,
            "result": result,
            "success": "error" not in result,
            "executed_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_email_tool(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute email tool."""
        operation = context.get_parameter("operation", "send")
        email_provider = context.get_parameter("email_provider", "gmail")
        
        logs.append(f"Email tool: {operation} via {email_provider}")
        
        # Mock email operations
        if operation == "send":
            to_recipients = context.get_parameter("to", [])
            subject = context.get_parameter("subject", "")
            body = context.get_parameter("body", "")
            result = self._mock_send_email(to_recipients, subject, body)
        elif operation == "read":
            query = context.get_parameter("query", "")
            result = self._mock_read_emails(query)
        elif operation == "search":
            search_query = context.get_parameter("search_query", "")
            result = self._mock_search_emails(search_query)
        elif operation == "delete":
            email_ids = context.get_parameter("email_ids", [])
            result = self._mock_delete_emails(email_ids)
        else:
            result = {"error": f"Unknown operation: {operation}"}
        
        output_data = {
            "tool_type": "email",
            "operation": operation,
            "email_provider": email_provider,
            "result": result,
            "success": "error" not in result,
            "executed_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _execute_http_tool(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute HTTP tool."""
        method = context.get_parameter("method", "GET").upper()
        url = context.get_parameter("url", "")
        headers = context.get_parameter("headers", {})
        data = context.get_parameter("data", {})
        timeout = context.get_parameter("timeout", 30)
        
        logs.append(f"HTTP tool: {method} {url}")
        
        # Mock HTTP request
        mock_response = {
            "status_code": 200,
            "headers": {"content-type": "application/json"},
            "body": json.dumps({"message": "Mock HTTP response"}),
            "url": url,
            "method": method
        }
        
        output_data = {
            "tool_type": "http",
            "method": method,
            "url": url,
            "headers": headers,
            "data": data,
            "response": mock_response,
            "success": True,
            "executed_at": datetime.now().isoformat()
        }
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=time.time() - start_time,
            logs=logs
        )
    
    def _mock_list_events(self, calendar_id: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Mock list calendar events."""
        return [
            {
                "id": "event_1",
                "title": "Team Meeting",
                "start": "2024-01-15T10:00:00Z",
                "end": "2024-01-15T11:00:00Z",
                "description": "Weekly team sync"
            },
            {
                "id": "event_2", 
                "title": "Client Call",
                "start": "2024-01-15T14:00:00Z",
                "end": "2024-01-15T15:00:00Z",
                "description": "Project review"
            }
        ]
    
    def _mock_create_event(self, calendar_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock create calendar event."""
        return {
            "id": f"event_{int(time.time())}",
            "title": event_data.get("title", "New Event"),
            "start": event_data.get("start", ""),
            "end": event_data.get("end", ""),
            "created": True
        }
    
    def _mock_update_event(self, calendar_id: str, event_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock update calendar event."""
        return {
            "id": event_id,
            "updated": True,
            "changes": event_data
        }
    
    def _mock_delete_event(self, calendar_id: str, event_id: str) -> Dict[str, Any]:
        """Mock delete calendar event."""
        return {
            "id": event_id,
            "deleted": True
        }
    
    def _mock_send_email(self, to_recipients: List[str], subject: str, body: str) -> Dict[str, Any]:
        """Mock send email."""
        return {
            "message_id": f"msg_{int(time.time())}",
            "to": to_recipients,
            "subject": subject,
            "sent": True
        }
    
    def _mock_read_emails(self, query: str) -> List[Dict[str, Any]]:
        """Mock read emails."""
        return [
            {
                "id": "email_1",
                "subject": "Important Update",
                "from": "sender@example.com",
                "date": "2024-01-15T09:00:00Z",
                "body": "This is an important email."
            }
        ]
    
    def _mock_search_emails(self, search_query: str) -> List[Dict[str, Any]]:
        """Mock search emails."""
        return [
            {
                "id": "email_2",
                "subject": "Search Result",
                "from": "search@example.com",
                "date": "2024-01-15T08:00:00Z",
                "body": "This email matches the search query."
            }
        ]
    
    def _mock_delete_emails(self, email_ids: List[str]) -> Dict[str, Any]:
        """Mock delete emails."""
        return {
            "deleted_ids": email_ids,
            "deleted_count": len(email_ids)
        }
    
    async def _execute_http_advanced_tool(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """执行高级HTTP工具。"""
        try:
            # 解析配置
            config_data = context.get_parameter("http_config", {})
            config_data.update({
                "method": context.get_parameter("method", "GET"),
                "url": context.get_parameter("url", ""),
                "headers": context.get_parameter("headers", {}),
                "params": context.get_parameter("params", {}),
                "body": context.get_parameter("body"),
                "auth_config": context.get_parameter("auth_config"),
                "timeout": context.get_parameter("timeout", 30),
                "follow_redirects": context.get_parameter("follow_redirects", True),
                "verify_ssl": context.get_parameter("verify_ssl", True)
            })
            
            config = HTTPToolConfig(**config_data)
            
            # 验证配置
            config_errors = config.validate()
            if config_errors:
                return self._create_error_result(
                    f"HTTP tool configuration validation failed: {'; '.join(config_errors)}",
                    execution_time=(time.time() - start_time) * 1000,
                    logs=logs
                )
            
            logs.append(f"HTTP Advanced tool: {config.method} {config.url}")
            
            # 准备请求头部
            headers = config.headers.copy()
            
            # 处理认证
            if config.auth_config:
                headers.update(self._prepare_auth_headers(config.auth_config))
            
            # 准备请求数据
            json_data = None
            data = None
            
            if config.body is not None:
                if isinstance(config.body, dict):
                    json_data = config.body
                    if "Content-Type" not in headers:
                        headers["Content-Type"] = "application/json"
                else:
                    data = config.body
            
            # 执行HTTP请求
            response = await self.make_http_request(
                method=config.method.upper(),
                url=config.url,
                headers=headers,
                params=config.params,
                json_data=json_data,
                data=data,
                timeout=config.timeout
            )
            
            # 处理响应
            response_data = await self._process_http_response(response)
            
            execution_time = (time.time() - start_time) * 1000
            
            output_data = {
                "tool_type": "http_advanced",
                "method": config.method.upper(),
                "url": config.url,
                "request_headers": headers,
                "request_params": config.params,
                "request_body": config.body,
                "response": response_data,
                "success": response.is_success,
                "execution_time_ms": execution_time,
                "executed_at": datetime.now().isoformat()
            }
            
            if response.is_success:
                logs.append(f"HTTP request completed successfully: {response.status_code}")
                return self._create_success_result(
                    output_data=output_data,
                    execution_time=execution_time,
                    logs=logs
                )
            else:
                logs.append(f"HTTP request failed: {response.status_code}")
                return self._create_error_result(
                    f"HTTP request failed with status {response.status_code}",
                    error_details={"response": response_data},
                    execution_time=execution_time,
                    logs=logs
                )
                
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            error_msg = f"HTTP Advanced tool execution failed: {str(e)}"
            logs.append(error_msg)
            
            return self._create_error_result(
                error_msg,
                error_details={"exception_type": type(e).__name__},
                execution_time=execution_time,
                logs=logs
            )
    
    async def _execute_external_api_tool(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """执行外部API工具。"""
        try:
            # 解析配置
            config_data = {
                "api_service": context.get_parameter("api_service", ""),
                "operation": context.get_parameter("operation", ""),
                "parameters": context.get_parameter("parameters", {}),
                "credential_id": context.get_parameter("credential_id"),
                "timeout_seconds": context.get_parameter("timeout_seconds", 30)
            }
            
            config = ExternalAPIToolConfig(**config_data)
            
            # 验证配置
            config_errors = config.validate()
            if config_errors:
                return self._create_error_result(
                    f"External API tool configuration validation failed: {'; '.join(config_errors)}",
                    execution_time=(time.time() - start_time) * 1000,
                    logs=logs
                )
            
            logs.append(f"External API tool: {config.api_service}.{config.operation}")
            
            # 检查API适配器是否可用
            try:
                from .external_action_node import APIAdapterFactory
                available_adapters = APIAdapterFactory.get_available_adapters()
                if config.api_service not in available_adapters:
                    return self._create_error_result(
                        f"API service '{config.api_service}' not available. Available: {available_adapters}",
                        execution_time=(time.time() - start_time) * 1000,
                        logs=logs
                    )
            except ImportError:
                # 如果没有APIAdapterFactory，返回Mock结果
                logs.append("APIAdapterFactory not available, returning mock result")
                return self._create_mock_external_api_result(config, logs, start_time)
            
            # 获取用户凭证（模拟）
            user_id = context.metadata.get('user_id')
            if not user_id:
                return self._create_error_result(
                    "User ID not found in execution context",
                    execution_time=(time.time() - start_time) * 1000,
                    logs=logs
                )
            
            # 模拟凭证获取（实际中需要使用OAuth2服务）
            credentials = {"access_token": f"mock_token_for_{config.api_service}"}
            logs.append(f"Retrieved mock credentials for {config.api_service}")
            
            # 创建API适配器（模拟）
            try:
                adapter = APIAdapterFactory.create_adapter(config.api_service)
                logs.append(f"Created {config.api_service} adapter")
                
                # 执行API调用
                result = await adapter.call(config.operation, config.parameters, credentials)
                
                execution_time = (time.time() - start_time) * 1000
                
                output_data = {
                    "tool_type": "external_api",
                    "api_service": config.api_service,
                    "operation": config.operation,
                    "parameters": config.parameters,
                    "result": result,
                    "success": True,
                    "execution_time_ms": execution_time,
                    "executed_at": datetime.now().isoformat()
                }
                
                logs.append(f"External API call completed successfully")
                return self._create_success_result(
                    output_data=output_data,
                    execution_time=execution_time,
                    logs=logs
                )
                
            except Exception as e:
                logs.append(f"External API call failed: {str(e)}")
                return self._create_error_result(
                    f"External API call failed: {str(e)}",
                    error_details={
                        "api_service": config.api_service,
                        "operation": config.operation,
                        "exception_type": type(e).__name__
                    },
                    execution_time=(time.time() - start_time) * 1000,
                    logs=logs
                )
                
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            error_msg = f"External API tool execution failed: {str(e)}"
            logs.append(error_msg)
            
            return self._create_error_result(
                error_msg,
                error_details={"exception_type": type(e).__name__},
                execution_time=execution_time,
                logs=logs
            )
    
    def _prepare_auth_headers(self, auth_config: Dict[str, Any]) -> Dict[str, str]:
        """准备认证头部。"""
        headers = {}
        auth_type = auth_config.get("type", "").lower()
        credentials = auth_config.get("credentials", {})
        
        if auth_type == "bearer":
            token = credentials.get("token", "")
            if token:
                headers["Authorization"] = f"Bearer {token}"
                
        elif auth_type == "basic":
            username = credentials.get("username", "")
            password = credentials.get("password", "")
            if username and password:
                import base64
                auth_string = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers["Authorization"] = f"Basic {auth_string}"
                
        elif auth_type == "api_key":
            api_key = credentials.get("api_key", "")
            header_name = auth_config.get("header_name", "X-API-Key")
            if api_key:
                headers[header_name] = api_key
                
        elif auth_type == "oauth2":
            access_token = credentials.get("access_token", "")
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"
        
        return headers
    
    async def _process_http_response(self, response) -> Dict[str, Any]:
        """处理HTTP响应。"""
        response_data = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "url": str(response.url)
        }
        
        # 尝试解析响应体
        try:
            content_type = response.headers.get("content-type", "").lower()
            if "application/json" in content_type:
                response_data["data"] = response.json()
                response_data["content_type"] = "json"
            else:
                response_data["data"] = response.text
                response_data["content_type"] = "text"
        except Exception:
            response_data["data"] = response.text
            response_data["content_type"] = "text"
        
        return response_data
    
    def _create_mock_external_api_result(self, config: ExternalAPIToolConfig, logs: List[str], start_time: float) -> NodeExecutionResult:
        """创建Mock外部API结果。"""
        mock_result = {
            "mock": True,
            "api_service": config.api_service,
            "operation": config.operation,
            "message": f"Mock result for {config.api_service}.{config.operation}",
            "parameters": config.parameters,
            "timestamp": datetime.now().isoformat()
        }
        
        execution_time = (time.time() - start_time) * 1000
        
        output_data = {
            "tool_type": "external_api",
            "api_service": config.api_service,
            "operation": config.operation,
            "parameters": config.parameters,
            "result": mock_result,
            "success": True,
            "mock": True,
            "execution_time_ms": execution_time,
            "executed_at": datetime.now().isoformat()
        }
        
        logs.append(f"Returned mock result for {config.api_service}.{config.operation}")
        
        return self._create_success_result(
            output_data=output_data,
            execution_time=execution_time,
            logs=logs
        )
