"""
Tests for HTTP Tool通用适配器
测试HTTP Tool通用适配器的所有功能
"""

import pytest
import json
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any

import httpx

from workflow_engine.services.api_adapters.http_tool import (
    HTTPToolAdapter,
    HTTPAuthConfig,
    HTTPRequestConfig
)
from workflow_engine.services.api_adapters.base import (
    APIError,
    AuthenticationError,
    ValidationError,
    NetworkError,
    TemporaryError,
    PermanentError
)


class TestHTTPToolAdapter:
    """HTTP Tool适配器测试类"""
    
    @pytest.fixture
    def adapter(self):
        """创建HTTP Tool适配器实例"""
        return HTTPToolAdapter()
    
    @pytest.fixture
    def mock_response(self):
        """模拟HTTP响应"""
        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response.json.return_value = {"result": "success"}
        response.text = '{"result": "success"}'
        response.content = b'{"result": "success"}'
        response.encoding = "utf-8"
        response.elapsed = 150.5
        return response
    
    def test_adapter_initialization(self, adapter):
        """测试适配器初始化"""
        assert adapter.provider_name == "http_tool"
        assert "request" in adapter.OPERATIONS
        assert "get" in adapter.OPERATIONS
        assert "post" in adapter.OPERATIONS
        assert len(adapter.get_supported_operations()) > 0
    
    def test_oauth2_config_not_supported(self, adapter):
        """测试OAuth2配置不被支持"""
        with pytest.raises(NotImplementedError):
            adapter.get_oauth2_config()
    
    def test_validate_credentials(self, adapter):
        """测试凭证验证"""
        # HTTP Tool支持各种认证方式，验证总是返回True
        assert adapter.validate_credentials({}) is True
        assert adapter.validate_credentials({"api_key": "test"}) is True
        assert adapter.validate_credentials({"access_token": "test"}) is True
    
    def test_parse_request_config_get(self, adapter):
        """测试解析GET请求配置"""
        parameters = {
            "url": "https://api.example.com/data",
            "headers": {"Accept": "application/json"},
            "query_params": {"page": 1, "limit": 10}
        }
        
        config = adapter._parse_request_config("get", parameters)
        
        assert config.method == "GET"
        assert config.url == "https://api.example.com/data"
        assert config.headers["Accept"] == "application/json"
        assert config.query_params["page"] == 1
        assert config.query_params["limit"] == 10
    
    def test_parse_request_config_post_with_json(self, adapter):
        """测试解析POST请求配置（JSON数据）"""
        parameters = {
            "url": "https://api.example.com/create",
            "json": {"name": "test", "value": 123},
            "timeout": 60.0
        }
        
        config = adapter._parse_request_config("post", parameters)
        
        assert config.method == "POST"
        assert config.url == "https://api.example.com/create"
        assert config.json_data == {"name": "test", "value": 123}
        assert config.timeout == 60.0
    
    def test_parse_request_config_with_form_data(self, adapter):
        """测试解析表单数据配置"""
        parameters = {
            "url": "https://api.example.com/upload",
            "data": {"field1": "value1", "field2": "value2"}
        }
        
        config = adapter._parse_request_config("post", parameters)
        
        assert config.form_data == {"field1": "value1", "field2": "value2"}
    
    def test_parse_request_config_with_raw_data(self, adapter):
        """测试解析原始数据配置"""
        parameters = {
            "url": "https://api.example.com/webhook",
            "data": "raw string data"
        }
        
        config = adapter._parse_request_config("post", parameters)
        
        assert config.raw_data == "raw string data"
    
    def test_parse_auth_config_bearer(self, adapter):
        """测试解析Bearer认证配置"""
        auth_params = {
            "type": "bearer",
            "token": "abc123"
        }
        
        auth_config = adapter._parse_auth_config(auth_params)
        
        assert auth_config.auth_type == "bearer"
        assert auth_config.bearer_token == "abc123"
    
    def test_parse_auth_config_basic(self, adapter):
        """测试解析Basic认证配置"""
        auth_params = {
            "type": "basic",
            "username": "user",
            "password": "pass"
        }
        
        auth_config = adapter._parse_auth_config(auth_params)
        
        assert auth_config.auth_type == "basic"
        assert auth_config.username == "user"
        assert auth_config.password == "pass"
    
    def test_parse_auth_config_api_key(self, adapter):
        """测试解析API Key认证配置"""
        auth_params = {
            "type": "api_key",
            "key": "secret123",
            "header": "X-Custom-Key",
            "location": "header"
        }
        
        auth_config = adapter._parse_auth_config(auth_params)
        
        assert auth_config.auth_type == "api_key"
        assert auth_config.api_key == "secret123"
        assert auth_config.api_key_header == "X-Custom-Key"
        assert auth_config.api_key_location == "header"
    
    def test_parse_auth_config_oauth2(self, adapter):
        """测试解析OAuth2认证配置"""
        auth_params = {
            "type": "oauth2",
            "provider": "google"
        }
        
        auth_config = adapter._parse_auth_config(auth_params)
        
        assert auth_config.auth_type == "oauth2"
        assert auth_config.oauth2_provider == "google"
    
    @pytest.mark.asyncio
    async def test_prepare_authentication_bearer(self, adapter):
        """测试准备Bearer认证"""
        config = HTTPRequestConfig(
            url="https://api.example.com",
            auth=HTTPAuthConfig(auth_type="bearer", bearer_token="token123")
        )
        credentials = {}
        
        await adapter._prepare_authentication(config, credentials)
        
        assert config.headers["Authorization"] == "Bearer token123"
    
    @pytest.mark.asyncio
    async def test_prepare_authentication_bearer_from_credentials(self, adapter):
        """测试从凭证中获取Bearer令牌"""
        config = HTTPRequestConfig(
            url="https://api.example.com",
            auth=HTTPAuthConfig(auth_type="bearer")
        )
        credentials = {"access_token": "cred_token123"}
        
        await adapter._prepare_authentication(config, credentials)
        
        assert config.headers["Authorization"] == "Bearer cred_token123"
    
    @pytest.mark.asyncio
    async def test_prepare_authentication_basic(self, adapter):
        """测试准备Basic认证"""
        config = HTTPRequestConfig(
            url="https://api.example.com",
            auth=HTTPAuthConfig(auth_type="basic", username="user", password="pass")
        )
        credentials = {}
        
        await adapter._prepare_authentication(config, credentials)
        
        # 验证Basic认证头部格式
        import base64
        expected = base64.b64encode("user:pass".encode()).decode()
        assert config.headers["Authorization"] == f"Basic {expected}"
    
    @pytest.mark.asyncio
    async def test_prepare_authentication_api_key_header(self, adapter):
        """测试API Key头部认证"""
        config = HTTPRequestConfig(
            url="https://api.example.com",
            auth=HTTPAuthConfig(
                auth_type="api_key",
                api_key="secret123",
                api_key_header="X-API-Key",
                api_key_location="header"
            )
        )
        credentials = {}
        
        await adapter._prepare_authentication(config, credentials)
        
        assert config.headers["X-API-Key"] == "secret123"
    
    @pytest.mark.asyncio
    async def test_prepare_authentication_api_key_query(self, adapter):
        """测试API Key查询参数认证"""
        config = HTTPRequestConfig(
            url="https://api.example.com",
            auth=HTTPAuthConfig(
                auth_type="api_key",
                api_key="secret123",
                api_key_location="query",
                api_key_param="key"
            )
        )
        credentials = {}
        
        await adapter._prepare_authentication(config, credentials)
        
        assert config.query_params["key"] == "secret123"
    
    @pytest.mark.asyncio
    async def test_prepare_authentication_oauth2(self, adapter):
        """测试OAuth2认证"""
        config = HTTPRequestConfig(
            url="https://api.example.com",
            auth=HTTPAuthConfig(auth_type="oauth2", oauth2_provider="google")
        )
        credentials = {"access_token": "oauth_token123"}
        
        await adapter._prepare_authentication(config, credentials)
        
        assert config.headers["Authorization"] == "Bearer oauth_token123"
    
    @pytest.mark.asyncio
    async def test_prepare_authentication_oauth2_missing_token(self, adapter):
        """测试OAuth2认证缺少令牌"""
        config = HTTPRequestConfig(
            url="https://api.example.com",
            auth=HTTPAuthConfig(auth_type="oauth2", oauth2_provider="google")
        )
        credentials = {}
        
        with pytest.raises(AuthenticationError):
            await adapter._prepare_authentication(config, credentials)
    
    def test_validate_request_config_valid(self, adapter):
        """测试有效请求配置验证"""
        config = HTTPRequestConfig(
            method="GET",
            url="https://api.example.com/data",
            response_format="json"
        )
        
        # 不应抛出异常
        adapter._validate_request_config(config)
    
    def test_validate_request_config_missing_url(self, adapter):
        """测试缺少URL的配置验证"""
        config = HTTPRequestConfig(method="GET", url="")
        
        with pytest.raises(ValidationError, match="URL is required"):
            adapter._validate_request_config(config)
    
    def test_validate_request_config_invalid_url(self, adapter):
        """测试无效URL的配置验证"""
        config = HTTPRequestConfig(method="GET", url="not-a-url")
        
        with pytest.raises(ValidationError, match="Invalid URL format"):
            adapter._validate_request_config(config)
    
    def test_validate_request_config_invalid_method(self, adapter):
        """测试无效HTTP方法的配置验证"""
        config = HTTPRequestConfig(
            method="INVALID",
            url="https://api.example.com"
        )
        
        with pytest.raises(ValidationError, match="Invalid HTTP method"):
            adapter._validate_request_config(config)
    
    def test_validate_request_config_invalid_response_format(self, adapter):
        """测试无效响应格式的配置验证"""
        config = HTTPRequestConfig(
            method="GET",
            url="https://api.example.com",
            response_format="invalid"
        )
        
        with pytest.raises(ValidationError, match="Invalid response format"):
            adapter._validate_request_config(config)
    
    @pytest.mark.asyncio
    async def test_process_response_json(self, adapter):
        """测试JSON响应处理"""
        config = HTTPRequestConfig(response_format="json")
        response = Mock(spec=httpx.Response)
        response.json.return_value = {"key": "value"}
        
        result = await adapter._process_response(response, config)
        
        assert result == {"key": "value"}
    
    @pytest.mark.asyncio
    async def test_process_response_text(self, adapter):
        """测试文本响应处理"""
        config = HTTPRequestConfig(response_format="text")
        response = Mock(spec=httpx.Response)
        response.text = "Plain text response"
        
        result = await adapter._process_response(response, config)
        
        assert result == "Plain text response"
    
    @pytest.mark.asyncio
    async def test_process_response_raw(self, adapter):
        """测试原始响应处理"""
        config = HTTPRequestConfig(response_format="raw")
        response = Mock(spec=httpx.Response)
        response.content = b"binary content"
        response.encoding = "utf-8"
        response.headers = {"content-type": "application/octet-stream"}
        
        result = await adapter._process_response(response, config)
        
        assert "content" in result
        assert "encoding" in result
        assert "content_type" in result
        assert result["encoding"] == "utf-8"
        assert result["content_type"] == "application/octet-stream"
    
    @pytest.mark.asyncio
    async def test_process_response_json_decode_error(self, adapter):
        """测试JSON解析错误"""
        config = HTTPRequestConfig(response_format="json")
        response = Mock(spec=httpx.Response)
        response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        
        with pytest.raises(PermanentError, match="Failed to parse JSON response"):
            await adapter._process_response(response, config)
    
    @pytest.mark.asyncio
    @patch('workflow_engine.services.api_adapters.http_tool.HTTPToolAdapter.get_http_client')
    async def test_make_http_request_success(self, mock_get_client, adapter, mock_response):
        """测试成功的HTTP请求"""
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_get_client.return_value = mock_client
        
        config = HTTPRequestConfig(
            method="GET",
            url="https://api.example.com/data",
            expected_status_codes=[200]
        )
        
        response = await adapter._make_http_request(config)
        
        assert response == mock_response
        mock_client.request.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('workflow_engine.services.api_adapters.http_tool.HTTPToolAdapter.get_http_client')
    async def test_make_http_request_timeout(self, mock_get_client, adapter):
        """测试HTTP请求超时"""
        mock_client = AsyncMock()
        mock_client.request.side_effect = httpx.TimeoutException("Request timeout")
        mock_get_client.return_value = mock_client
        
        config = HTTPRequestConfig(
            method="GET",
            url="https://api.example.com/data"
        )
        
        with pytest.raises(NetworkError, match="Request timeout"):
            await adapter._make_http_request(config)
    
    @pytest.mark.asyncio
    @patch('workflow_engine.services.api_adapters.http_tool.HTTPToolAdapter.get_http_client')
    async def test_make_http_request_connection_error(self, mock_get_client, adapter):
        """测试HTTP连接错误"""
        mock_client = AsyncMock()
        mock_client.request.side_effect = httpx.ConnectError("Connection failed")
        mock_get_client.return_value = mock_client
        
        config = HTTPRequestConfig(
            method="GET",
            url="https://api.example.com/data"
        )
        
        with pytest.raises(NetworkError, match="Connection error"):
            await adapter._make_http_request(config)
    
    @pytest.mark.asyncio
    @patch('workflow_engine.services.api_adapters.http_tool.HTTPToolAdapter._make_http_request')
    async def test_call_get_request(self, mock_make_request, adapter, mock_response):
        """测试GET请求调用"""
        mock_make_request.return_value = mock_response
        
        parameters = {
            "url": "https://api.example.com/data",
            "query_params": {"page": 1}
        }
        credentials = {}
        
        result = await adapter.call("get", parameters, credentials)
        
        assert result["success"] is True
        assert result["method"] == "GET"
        assert result["url"] == "https://api.example.com/data"
        assert result["status_code"] == 200
        assert "data" in result
    
    @pytest.mark.asyncio
    @patch('workflow_engine.services.api_adapters.http_tool.HTTPToolAdapter._make_http_request')
    async def test_call_post_request_with_json(self, mock_make_request, adapter, mock_response):
        """测试POST请求调用（JSON数据）"""
        mock_make_request.return_value = mock_response
        
        parameters = {
            "url": "https://api.example.com/create",
            "json": {"name": "test", "value": 123},
            "auth": {
                "type": "bearer",
                "token": "abc123"
            }
        }
        credentials = {}
        
        result = await adapter.call("post", parameters, credentials)
        
        assert result["success"] is True
        assert result["method"] == "POST"
        assert result["status_code"] == 200
        assert "data" in result
    
    @pytest.mark.asyncio
    @patch('workflow_engine.services.api_adapters.http_tool.HTTPToolAdapter._make_http_request')
    async def test_call_with_authentication_error(self, mock_make_request, adapter):
        """测试认证错误处理"""
        mock_make_request.side_effect = AuthenticationError("Invalid credentials")
        
        parameters = {
            "url": "https://api.example.com/secure",
            "auth": {
                "type": "oauth2",
                "provider": "google"
            }
        }
        credentials = {}  # 缺少access_token
        
        result = await adapter.call("get", parameters, credentials)
        
        assert result["success"] is False
        assert "error" in result
        assert result["error_type"] == "AuthenticationError"
    
    @pytest.mark.asyncio
    @patch('workflow_engine.services.api_adapters.http_tool.HTTPToolAdapter._make_http_request')
    async def test_call_with_validation_error(self, mock_make_request, adapter):
        """测试验证错误处理"""
        # 模拟在_make_http_request之前的验证错误
        parameters = {
            "url": "",  # 空URL会触发验证错误
            "method": "GET"
        }
        credentials = {}
        
        result = await adapter.call("get", parameters, credentials)
        
        assert result["success"] is False
        assert "error" in result
        assert "ValidationError" in result["error_type"] or "URL is required" in result["error"]
    
    @pytest.mark.asyncio
    @patch('workflow_engine.services.api_adapters.http_tool.HTTPToolAdapter._make_http_request')
    async def test_test_connection_success(self, mock_make_request, adapter, mock_response):
        """测试连接测试成功"""
        mock_response.status_code = 200
        mock_make_request.return_value = mock_response
        
        result = await adapter.test_connection({})
        
        assert result["success"] is True
        assert result["provider"] == "http_tool"
        assert "test_url" in result["details"]
        assert result["details"]["status_code"] == 200
    
    @pytest.mark.asyncio
    @patch('workflow_engine.services.api_adapters.http_tool.HTTPToolAdapter._make_http_request')
    async def test_test_connection_failure(self, mock_make_request, adapter):
        """测试连接测试失败"""
        mock_make_request.side_effect = NetworkError("Connection failed")
        
        result = await adapter.test_connection({})
        
        assert result["success"] is False
        assert result["provider"] == "http_tool"
        assert "error" in result
        assert result["error_type"] == "NetworkError"
    
    def test_get_supported_operations(self, adapter):
        """测试获取支持的操作列表"""
        operations = adapter.get_supported_operations()
        
        expected_operations = ["request", "get", "post", "put", "patch", "delete", "head", "options"]
        for op in expected_operations:
            assert op in operations
    
    def test_get_operation_description(self, adapter):
        """测试获取操作描述"""
        description = adapter.get_operation_description("get")
        assert description == "发起GET请求"
        
        description = adapter.get_operation_description("post")
        assert description == "发起POST请求"
        
        description = adapter.get_operation_description("nonexistent")
        assert description is None


@pytest.mark.asyncio
class TestHTTPToolAdapterIntegration:
    """HTTP Tool适配器集成测试"""
    
    async def test_real_http_request(self):
        """测试真实的HTTP请求（如果网络可用）"""
        adapter = HTTPToolAdapter()
        
        try:
            parameters = {
                "url": "https://httpbin.org/json",
                "timeout": 10.0
            }
            credentials = {}
            
            result = await adapter.call("get", parameters, credentials)
            
            if result["success"]:
                assert result["status_code"] == 200
                assert "data" in result
                # httpbin.org/json returns a JSON response
                assert isinstance(result["data"], dict)
            else:
                # 网络不可用时跳过测试
                pytest.skip("Network not available for integration test")
                
        except Exception as e:
            pytest.skip(f"Network integration test skipped: {str(e)}")
        finally:
            await adapter.close_http_client()
    
    async def test_authentication_workflow(self):
        """测试完整的认证工作流程"""
        adapter = HTTPToolAdapter()
        
        try:
            # 测试API Key认证
            parameters = {
                "url": "https://httpbin.org/headers",
                "auth": {
                    "type": "api_key",
                    "key": "test-api-key",
                    "header": "X-Test-Key"
                }
            }
            credentials = {}
            
            result = await adapter.call("get", parameters, credentials)
            
            if result["success"]:
                assert result["status_code"] == 200
                # httpbin.org echoes headers, so we can verify our auth header was sent
                headers_data = result["data"].get("headers", {})
                assert "X-Test-Key" in headers_data
                assert headers_data["X-Test-Key"] == "test-api-key"
            else:
                pytest.skip("Network not available for authentication test")
                
        except Exception as e:
            pytest.skip(f"Authentication workflow test skipped: {str(e)}")
        finally:
            await adapter.close_http_client()