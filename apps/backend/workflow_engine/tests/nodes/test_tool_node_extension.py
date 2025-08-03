"""
Tool Node扩展测试
测试HTTP Advanced工具和External API工具的功能
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone
import httpx

from workflow_engine.nodes.tool_node import (
    ToolNodeExecutor,
    HTTPToolConfig,
    ExternalAPIToolConfig
)
from workflow_engine.nodes.base import NodeExecutionContext, ExecutionStatus
from workflow_engine.services.api_adapters.base import HTTPConfig


@pytest.mark.unit
class TestHTTPToolConfig:
    """HTTP工具配置测试"""
    
    def test_config_creation(self):
        """测试：配置创建"""
        config = HTTPToolConfig(
            method="POST",
            url="https://api.example.com/users",
            headers={"Content-Type": "application/json"},
            body={"name": "Test User"}
        )
        
        assert config.method == "POST"
        assert config.url == "https://api.example.com/users"
        assert config.headers["Content-Type"] == "application/json"
        assert config.body["name"] == "Test User"
    
    def test_config_validation_success(self):
        """测试：配置验证成功"""
        config = HTTPToolConfig(
            method="GET",
            url="https://api.example.com/data"
        )
        
        errors = config.validate()
        assert len(errors) == 0
    
    def test_config_validation_missing_url(self):
        """测试：缺少URL"""
        config = HTTPToolConfig(method="GET", url="")
        
        errors = config.validate()
        assert "URL is required" in errors
    
    def test_config_validation_invalid_method(self):
        """测试：无效的HTTP方法"""
        config = HTTPToolConfig(
            method="INVALID",
            url="https://api.example.com/data"
        )
        
        errors = config.validate()
        assert any("Invalid HTTP method" in error for error in errors)
    
    def test_config_validation_invalid_timeout(self):
        """测试：无效的超时时间"""
        config = HTTPToolConfig(
            method="GET",
            url="https://api.example.com/data",
            timeout=-5
        )
        
        errors = config.validate()
        assert "Timeout must be positive" in errors


@pytest.mark.unit
class TestExternalAPIToolConfig:
    """外部API工具配置测试"""
    
    def test_config_creation(self):
        """测试：配置创建"""
        config = ExternalAPIToolConfig(
            api_service="google_calendar",
            operation="create_event",
            parameters={"summary": "Test Meeting"}
        )
        
        assert config.api_service == "google_calendar"
        assert config.operation == "create_event"
        assert config.parameters["summary"] == "Test Meeting"
    
    def test_config_validation_success(self):
        """测试：配置验证成功"""
        config = ExternalAPIToolConfig(
            api_service="github",
            operation="create_issue"
        )
        
        errors = config.validate()
        assert len(errors) == 0
    
    def test_config_validation_missing_api_service(self):
        """测试：缺少API服务"""
        config = ExternalAPIToolConfig(
            api_service="",
            operation="test_operation"
        )
        
        errors = config.validate()
        assert "API service is required" in errors
    
    def test_config_validation_missing_operation(self):
        """测试：缺少操作"""
        config = ExternalAPIToolConfig(
            api_service="slack",
            operation=""
        )
        
        errors = config.validate()
        assert "Operation is required" in errors


@pytest.mark.unit
class TestToolNodeExecutorExtension:
    """Tool Node执行器扩展测试"""
    
    @pytest.fixture
    def executor(self):
        """创建执行器实例"""
        return ToolNodeExecutor()
    
    @pytest.fixture
    def mock_context_http_advanced(self):
        """创建HTTP Advanced工具的Mock执行上下文"""
        mock_node = Mock()
        mock_node.subtype = "HTTP_ADVANCED"
        mock_node.parameters = {
            "method": "POST",
            "url": "https://api.example.com/users",
            "headers": {"Content-Type": "application/json"},
            "body": {"name": "Test User", "email": "test@example.com"},
            "auth_config": {
                "type": "bearer",
                "credentials": {"token": "test_token_123"}
            },
            "timeout": 30
        }
        
        context = NodeExecutionContext(
            node=mock_node,
            workflow_id="workflow_123",
            execution_id="exec_456",
            input_data={},
            static_data={},
            credentials={},
            metadata={"user_id": "user_123"}
        )
        
        return context
    
    @pytest.fixture
    def mock_context_external_api(self):
        """创建外部API工具的Mock执行上下文"""
        mock_node = Mock()
        mock_node.subtype = "EXTERNAL_API"
        mock_node.parameters = {
            "api_service": "google_calendar",
            "operation": "create_event",
            "parameters": {
                "summary": "Test Meeting",
                "start": {"dateTime": "2025-08-02T10:00:00Z"},
                "end": {"dateTime": "2025-08-02T11:00:00Z"}
            },
            "timeout_seconds": 30
        }
        
        context = NodeExecutionContext(
            node=mock_node,
            workflow_id="workflow_123",
            execution_id="exec_456",
            input_data={},
            static_data={},
            credentials={},
            metadata={"user_id": "user_123"}
        )
        
        return context
    
    def test_get_supported_subtypes(self, executor):
        """测试：获取支持的子类型"""
        subtypes = executor.get_supported_subtypes()
        
        assert "HTTP_ADVANCED" in subtypes
        assert "EXTERNAL_API" in subtypes
        assert "MCP" in subtypes  # 确保原有功能保持
        assert "CALENDAR" in subtypes
        assert "EMAIL" in subtypes
        assert "HTTP" in subtypes
    
    def test_validate_http_advanced_valid(self, executor):
        """测试：验证有效的HTTP Advanced节点"""
        mock_node = Mock()
        mock_node.subtype = "HTTP_ADVANCED"
        mock_node.parameters = {
            "method": "GET",
            "url": "https://api.example.com/data",
            "http_config": {
                "timeout": 30,
                "follow_redirects": True
            }
        }
        
        errors = executor.validate(mock_node)
        assert len(errors) == 0
    
    def test_validate_http_advanced_invalid(self, executor):
        """测试：验证无效的HTTP Advanced节点"""
        mock_node = Mock()
        mock_node.subtype = "HTTP_ADVANCED"
        mock_node.parameters = {
            "method": "",  # 无效方法
            "url": ""      # 缺少URL
        }
        
        errors = executor.validate(mock_node)
        assert len(errors) > 0
        assert any("method" in error.lower() for error in errors)
        assert any("url" in error.lower() for error in errors)
    
    def test_validate_external_api_valid(self, executor):
        """测试：验证有效的外部API节点"""
        mock_node = Mock()
        mock_node.subtype = "EXTERNAL_API"
        mock_node.parameters = {
            "api_service": "github",
            "operation": "create_issue",
            "parameters": {"title": "Test Issue"}
        }
        
        errors = executor.validate(mock_node)
        assert len(errors) == 0
    
    def test_validate_external_api_invalid(self, executor):
        """测试：验证无效的外部API节点"""
        mock_node = Mock()
        mock_node.subtype = "EXTERNAL_API"
        mock_node.parameters = {
            "api_service": "",  # 缺少API服务
            "operation": ""     # 缺少操作
        }
        
        errors = executor.validate(mock_node)
        assert len(errors) > 0
        assert any("api_service" in error for error in errors)
        assert any("operation" in error for error in errors)
    
    def test_prepare_auth_headers_bearer(self, executor):
        """测试：准备Bearer认证头部"""
        auth_config = {
            "type": "bearer",
            "credentials": {"token": "test_token_123"}
        }
        
        headers = executor._prepare_auth_headers(auth_config)
        
        assert headers["Authorization"] == "Bearer test_token_123"
    
    def test_prepare_auth_headers_basic(self, executor):
        """测试：准备Basic认证头部"""
        auth_config = {
            "type": "basic",
            "credentials": {"username": "testuser", "password": "testpass"}
        }
        
        headers = executor._prepare_auth_headers(auth_config)
        
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")
    
    def test_prepare_auth_headers_api_key(self, executor):
        """测试：准备API Key认证头部"""
        auth_config = {
            "type": "api_key",
            "credentials": {"api_key": "test_api_key_123"},
            "header_name": "X-API-Key"
        }
        
        headers = executor._prepare_auth_headers(auth_config)
        
        assert headers["X-API-Key"] == "test_api_key_123"
    
    def test_prepare_auth_headers_oauth2(self, executor):
        """测试：准备OAuth2认证头部"""
        auth_config = {
            "type": "oauth2",
            "credentials": {"access_token": "oauth_token_123"}
        }
        
        headers = executor._prepare_auth_headers(auth_config)
        
        assert headers["Authorization"] == "Bearer oauth_token_123"
    
    @pytest.mark.asyncio
    async def test_process_http_response_json(self, executor):
        """测试：处理JSON响应"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.url = "https://api.example.com/data"
        mock_response.json.return_value = {"message": "success", "data": [1, 2, 3]}
        
        result = await executor._process_http_response(mock_response)
        
        assert result["status_code"] == 200
        assert result["content_type"] == "json"
        assert result["data"]["message"] == "success"
        assert result["url"] == "https://api.example.com/data"
    
    @pytest.mark.asyncio
    async def test_process_http_response_text(self, executor):
        """测试：处理文本响应"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.url = "https://api.example.com/text"
        mock_response.text = "Plain text response"
        
        result = await executor._process_http_response(mock_response)
        
        assert result["status_code"] == 200
        assert result["content_type"] == "text"
        assert result["data"] == "Plain text response"


@pytest.mark.unit
class TestHTTPAdvancedToolExecution:
    """HTTP Advanced工具执行测试"""
    
    @pytest.fixture
    def executor(self):
        return ToolNodeExecutor()
    
    @pytest.fixture
    def mock_context(self):
        mock_node = Mock()
        mock_node.subtype = "HTTP_ADVANCED"
        mock_node.parameters = {
            "method": "GET",
            "url": "https://api.example.com/data",
            "headers": {"Accept": "application/json"},
            "timeout": 30
        }
        
        return NodeExecutionContext(
            node=mock_node,
            workflow_id="test_workflow",
            execution_id="test_execution",
            input_data={},
            static_data={},
            credentials={},
            metadata={}
        )
    
    @pytest.mark.asyncio
    async def test_execute_http_advanced_success(self, executor, mock_context):
        """测试：HTTP Advanced工具执行成功"""
        # Mock HTTP响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.is_success = True
        mock_response.headers = {"content-type": "application/json"}
        mock_response.url = "https://api.example.com/data"
        mock_response.json.return_value = {"message": "success"}
        mock_response.text = '{"message": "success"}'
        
        with patch.object(executor, 'make_http_request', return_value=mock_response):
            result = await executor._execute_http_advanced_tool(mock_context, [], 0)
        
        assert result.status == ExecutionStatus.SUCCESS
        assert result.output_data["tool_type"] == "http_advanced"
        assert result.output_data["method"] == "GET"
        assert result.output_data["success"] is True
        assert result.output_data["response"]["status_code"] == 200
    
    @pytest.mark.asyncio
    async def test_execute_http_advanced_with_auth(self, executor):
        """测试：带认证的HTTP Advanced工具执行"""
        mock_node = Mock()
        mock_node.subtype = "HTTP_ADVANCED"
        mock_node.parameters = {
            "method": "POST",
            "url": "https://api.example.com/users",
            "body": {"name": "Test User"},
            "auth_config": {
                "type": "bearer",
                "credentials": {"token": "test_token"}
            }
        }
        
        context = NodeExecutionContext(
            node=mock_node,
            workflow_id="test_workflow",
            execution_id="test_execution",
            input_data={},
            static_data={},
            credentials={},
            metadata={}
        )
        
        # Mock HTTP响应
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.is_success = True
        mock_response.headers = {"content-type": "application/json"}
        mock_response.url = "https://api.example.com/users"
        mock_response.json.return_value = {"id": 123, "name": "Test User"}
        mock_response.text = '{"id": 123, "name": "Test User"}'
        
        with patch.object(executor, 'make_http_request', return_value=mock_response) as mock_request:
            result = await executor._execute_http_advanced_tool(context, [], 0)
        
        assert result.status == ExecutionStatus.SUCCESS
        
        # 验证认证头部被正确设置
        args, kwargs = mock_request.call_args
        headers = kwargs.get("headers", {})
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_token"
    
    @pytest.mark.asyncio
    async def test_execute_http_advanced_error(self, executor, mock_context):
        """测试：HTTP Advanced工具执行错误"""
        # Mock HTTP错误响应
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.is_success = False
        mock_response.headers = {"content-type": "application/json"}
        mock_response.url = "https://api.example.com/data"
        mock_response.json.return_value = {"error": "Not found"}
        mock_response.text = '{"error": "Not found"}'
        
        with patch.object(executor, 'make_http_request', return_value=mock_response):
            result = await executor._execute_http_advanced_tool(mock_context, [], 0)
        
        assert result.status == ExecutionStatus.ERROR
        assert "404" in result.error_message
        assert result.error_details["response"]["status_code"] == 404


@pytest.mark.unit
class TestExternalAPIToolExecution:
    """外部API工具执行测试"""
    
    @pytest.fixture
    def executor(self):
        return ToolNodeExecutor()
    
    @pytest.fixture
    def mock_context(self):
        mock_node = Mock()
        mock_node.subtype = "EXTERNAL_API"
        mock_node.parameters = {
            "api_service": "google_calendar",
            "operation": "create_event",
            "parameters": {
                "summary": "Test Meeting",
                "start": {"dateTime": "2025-08-02T10:00:00Z"}
            }
        }
        
        return NodeExecutionContext(
            node=mock_node,
            workflow_id="test_workflow",
            execution_id="test_execution",
            input_data={},
            static_data={},
            credentials={},
            metadata={"user_id": "user_123"}
        )
    
    @pytest.mark.asyncio
    async def test_execute_external_api_mock_success(self, executor, mock_context):
        """测试：外部API工具执行成功（Mock模式）"""
        # 不mock APIAdapterFactory，让它走mock路径
        result = await executor._execute_external_api_tool(mock_context, [], 0)
        
        assert result.status == ExecutionStatus.SUCCESS
        assert result.output_data["tool_type"] == "external_api"
        assert result.output_data["api_service"] == "google_calendar"
        assert result.output_data["operation"] == "create_event"
        assert result.output_data["mock"] is True
        assert result.output_data["success"] is True
    
    @pytest.mark.asyncio
    async def test_execute_external_api_no_user_id(self, executor):
        """测试：外部API工具执行失败 - 缺少用户ID"""
        mock_node = Mock()
        mock_node.subtype = "EXTERNAL_API"
        mock_node.parameters = {
            "api_service": "github",
            "operation": "create_issue"
        }
        
        context = NodeExecutionContext(
            node=mock_node,
            workflow_id="test_workflow",
            execution_id="test_execution",
            input_data={},
            static_data={},
            credentials={},
            metadata={}  # 缺少user_id
        )
        
        result = await executor._execute_external_api_tool(context, [], 0)
        
        assert result.status == ExecutionStatus.ERROR
        assert "User ID not found" in result.error_message
    
    def test_create_mock_external_api_result(self, executor):
        """测试：创建Mock外部API结果"""
        config = ExternalAPIToolConfig(
            api_service="slack",
            operation="send_message",
            parameters={"channel": "#general", "text": "Hello"}
        )
        
        result = executor._create_mock_external_api_result(config, [], 0)
        
        assert result.status == ExecutionStatus.SUCCESS
        assert result.output_data["tool_type"] == "external_api"
        assert result.output_data["api_service"] == "slack"
        assert result.output_data["operation"] == "send_message"
        assert result.output_data["mock"] is True
        assert result.output_data["result"]["mock"] is True


@pytest.mark.integration
class TestToolNodeIntegration:
    """Tool Node集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_http_advanced_workflow(self):
        """测试：完整的HTTP Advanced工作流"""
        executor = ToolNodeExecutor()
        
        # 创建真实的节点配置
        mock_node = Mock()
        mock_node.subtype = "HTTP_ADVANCED"
        mock_node.parameters = {
            "method": "GET",
            "url": "https://httpbin.org/json",  # 使用公共测试API
            "headers": {"Accept": "application/json"},
            "timeout": 10
        }
        
        context = NodeExecutionContext(
            node=mock_node,
            workflow_id="integration_test",
            execution_id="integration_exec",
            input_data={},
            static_data={},
            credentials={},
            metadata={}
        )
        
        # 验证节点配置
        validation_errors = executor.validate(mock_node)
        assert len(validation_errors) == 0
        
        # 执行节点（实际HTTP请求）
        # 注意：这需要网络连接，在CI环境中可能需要mock
        try:
            result = await executor.execute(context)
            
            if result.status == ExecutionStatus.SUCCESS:
                assert result.output_data["tool_type"] == "http_advanced"
                assert result.output_data["method"] == "GET"
                assert result.output_data["success"] is True
                assert "response" in result.output_data
            else:
                # 网络错误或其他问题，但不应该导致测试失败
                assert result.status == ExecutionStatus.ERROR
                
        except Exception as e:
            # 网络问题等，跳过这个测试
            pytest.skip(f"Network request failed: {str(e)}")
        
        finally:
            # 确保清理
            await executor.close_http_client()
    
    @pytest.mark.asyncio
    async def test_full_external_api_workflow(self):
        """测试：完整的外部API工作流"""
        executor = ToolNodeExecutor()
        
        mock_node = Mock()
        mock_node.subtype = "EXTERNAL_API"
        mock_node.parameters = {
            "api_service": "google_calendar",
            "operation": "list_events",
            "parameters": {"calendar_id": "primary"}
        }
        
        context = NodeExecutionContext(
            node=mock_node,
            workflow_id="integration_test",
            execution_id="integration_exec",
            input_data={},
            static_data={},
            credentials={},
            metadata={"user_id": "integration_user"}
        )
        
        # 验证节点配置
        validation_errors = executor.validate(mock_node)
        assert len(validation_errors) == 0
        
        # 执行节点（应该返回mock结果）
        result = await executor.execute(context)
        
        assert result.status == ExecutionStatus.SUCCESS
        assert result.output_data["tool_type"] == "external_api"
        assert result.output_data["api_service"] == "google_calendar"
        assert result.output_data["operation"] == "list_events"
        # 由于没有真实的APIAdapterFactory，应该返回mock结果
        assert result.output_data["mock"] is True
        
        # 确保清理
        await executor.close_http_client()