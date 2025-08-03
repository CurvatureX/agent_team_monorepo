"""
API适配器基类测试
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import httpx
from datetime import datetime

from workflow_engine.services.api_adapters.base import (
    APIAdapter,
    APIError,
    AuthenticationError,
    RateLimitError,
    TemporaryError,
    PermanentError,
    RetryConfig,
    OAuth2Config,
    HTTPConfig,
    APIAdapterRegistry,
    register_adapter
)


class TestAPIAdapter(APIAdapter):
    """测试用的API适配器实现"""
    
    OPERATIONS = {
        "test_operation": "测试操作",
        "failing_operation": "会失败的操作"
    }
    
    async def call(self, operation: str, parameters: dict, credentials: dict) -> dict:
        if operation == "test_operation":
            return {"success": True, "data": parameters}
        elif operation == "failing_operation":
            raise TemporaryError("This operation always fails")
        else:
            raise ValueError(f"Unknown operation: {operation}")
    
    def get_oauth2_config(self) -> OAuth2Config:
        return OAuth2Config(
            client_id="test_client_id",
            client_secret="test_client_secret", 
            auth_url="https://example.com/auth",
            token_url="https://example.com/token",
            scopes=["test_scope"]
        )
    
    def validate_credentials(self, credentials: dict) -> bool:
        return "access_token" in credentials and len(credentials["access_token"]) > 0


@pytest.mark.unit
class TestAPIAdapterBase:
    """API适配器基类单元测试"""
    
    @pytest.fixture
    def test_adapter(self):
        """创建测试适配器实例"""
        return TestAPIAdapter()
    
    @pytest.fixture
    def test_credentials(self):
        """测试凭证"""
        return {"access_token": "test_token_12345"}
    
    @pytest.mark.asyncio
    async def test_adapter_initialization(self):
        """测试：适配器初始化"""
        adapter = TestAPIAdapter()
        assert adapter.provider_name == "testapi"
        assert adapter.retry_config.max_retries == 3
        assert adapter.http_config.timeout == 30.0
    
    @pytest.mark.asyncio
    async def test_successful_api_call(self, test_adapter, test_credentials):
        """测试：成功的API调用"""
        result = await test_adapter.call(
            operation="test_operation",
            parameters={"param1": "value1"},
            credentials=test_credentials
        )
        
        assert result["success"] is True
        assert result["data"]["param1"] == "value1"
    
    @pytest.mark.asyncio
    async def test_api_call_with_retry(self, test_adapter, test_credentials):
        """测试：带重试的API调用"""
        # 使用retry机制调用会失败的操作
        # tenacity会包装异常为RetryError
        from tenacity import RetryError
        with pytest.raises(RetryError):
            await test_adapter.call_with_retry(
                test_adapter.call,
                operation="failing_operation",
                parameters={},
                credentials=test_credentials
            )
    
    def test_get_supported_operations(self, test_adapter):
        """测试：获取支持的操作列表"""
        operations = test_adapter.get_supported_operations()
        assert "test_operation" in operations
        assert "failing_operation" in operations
    
    def test_get_operation_description(self, test_adapter):
        """测试：获取操作描述"""
        description = test_adapter.get_operation_description("test_operation")
        assert description == "测试操作"
        
        # 测试不存在的操作
        description = test_adapter.get_operation_description("nonexistent")
        assert description is None
    
    def test_oauth2_config(self, test_adapter):
        """测试：OAuth2配置"""
        config = test_adapter.get_oauth2_config()
        assert config.client_id == "test_client_id"
        assert config.auth_url == "https://example.com/auth"
        assert "test_scope" in config.scopes
    
    def test_validate_credentials(self, test_adapter, test_credentials):
        """测试：凭证验证"""
        # 有效凭证
        assert test_adapter.validate_credentials(test_credentials) is True
        
        # 无效凭证
        invalid_credentials = {"invalid": "token"}
        assert test_adapter.validate_credentials(invalid_credentials) is False
        
        # 空凭证
        empty_credentials = {"access_token": ""}
        assert test_adapter.validate_credentials(empty_credentials) is False
    
    @pytest.mark.asyncio
    async def test_connection_test(self, test_adapter, test_credentials):
        """测试：连接测试"""
        result = await test_adapter.test_connection(test_credentials)
        
        assert result["success"] is True
        assert result["provider"] == "testapi"
        assert "credentials_valid" in result["details"]
    
    @pytest.mark.asyncio
    async def test_connection_test_failure(self, test_adapter):
        """测试：连接测试失败"""
        invalid_credentials = {"invalid": "token"}
        result = await test_adapter.test_connection(invalid_credentials)
        
        assert result["success"] is False
        assert "error" in result
    
    def test_prepare_headers(self, test_adapter, test_credentials):
        """测试：准备请求头"""
        headers = test_adapter._prepare_headers(test_credentials)
        
        assert headers["Authorization"] == "Bearer test_token_12345"
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"
    
    def test_prepare_headers_with_api_key(self, test_adapter):
        """测试：使用API密钥准备请求头"""
        credentials = {"api_key": "test_api_key"}
        headers = test_adapter._prepare_headers(credentials)
        
        assert headers["Authorization"] == "Bearer test_api_key"
    
    def test_prepare_headers_with_extra(self, test_adapter, test_credentials):
        """测试：添加额外请求头"""
        extra_headers = {"X-Custom-Header": "custom_value"}
        headers = test_adapter._prepare_headers(test_credentials, extra_headers)
        
        assert headers["X-Custom-Header"] == "custom_value"
        assert headers["Authorization"] == "Bearer test_token_12345"
    
    @pytest.mark.asyncio
    async def test_http_client_lifecycle(self, test_adapter):
        """测试：HTTP客户端生命周期"""
        # 初始状态没有客户端
        assert test_adapter._client is None
        
        # 获取客户端
        client = await test_adapter.get_http_client()
        assert isinstance(client, httpx.AsyncClient)
        assert test_adapter._client is client
        
        # 再次获取应该返回同一实例
        client2 = await test_adapter.get_http_client()
        assert client2 is client
        
        # 关闭客户端
        await test_adapter.close_http_client()
        assert test_adapter._client is None
    
    @pytest.mark.asyncio 
    async def test_context_manager(self, test_credentials):
        """测试：异步上下文管理器"""
        async with TestAPIAdapter() as adapter:
            result = await adapter.call(
                operation="test_operation",
                parameters={"test": "data"},
                credentials=test_credentials
            )
            assert result["success"] is True
        
        # 上下文结束后客户端应该已关闭
        assert adapter._client is None


@pytest.mark.unit
class TestRetryConfig:
    """重试配置测试"""
    
    def test_default_retry_config(self):
        """测试：默认重试配置"""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.backoff_factor == 2.0
        assert config.max_backoff == 60.0
        assert TemporaryError in config.retry_on
    
    def test_custom_retry_config(self):
        """测试：自定义重试配置"""
        config = RetryConfig(
            max_retries=5,
            backoff_factor=1.5,
            retry_on=[RateLimitError]
        )
        assert config.max_retries == 5
        assert config.backoff_factor == 1.5
        assert config.retry_on == [RateLimitError]


@pytest.mark.unit 
class TestOAuth2Config:
    """OAuth2配置测试"""
    
    def test_oauth2_config_creation(self):
        """测试：OAuth2配置创建"""
        config = OAuth2Config(
            client_id="test_id",
            client_secret="test_secret",
            auth_url="https://auth.example.com",
            token_url="https://token.example.com",
            scopes=["read", "write"]
        )
        
        assert config.client_id == "test_id"
        assert config.client_secret == "test_secret"
        assert config.scopes == ["read", "write"]
    
    def test_oauth2_config_to_dict(self):
        """测试：OAuth2配置转换为字典"""
        config = OAuth2Config(
            client_id="test_id",
            client_secret="test_secret",
            auth_url="https://auth.example.com",
            token_url="https://token.example.com"
        )
        
        config_dict = config.to_dict()
        assert config_dict["client_id"] == "test_id"
        assert config_dict["auth_url"] == "https://auth.example.com"


@pytest.mark.unit
class TestHTTPConfig:
    """HTTP配置测试"""
    
    def test_default_http_config(self):
        """测试：默认HTTP配置"""
        config = HTTPConfig()
        assert config.timeout == 30.0
        assert config.max_connections == 100
        assert config.verify_ssl is True
    
    def test_httpx_limits_conversion(self):
        """测试：转换为httpx限制对象"""
        config = HTTPConfig(max_connections=50, max_keepalive_connections=10)
        limits = config.to_httpx_limits()
        
        assert limits.max_connections == 50
        assert limits.max_keepalive_connections == 10


@pytest.mark.unit
class TestAPIAdapterRegistry:
    """API适配器注册表测试"""
    
    def test_register_and_get_adapter(self):
        """测试：注册和获取适配器"""
        # 清空注册表
        APIAdapterRegistry._adapters.clear()
        
        # 注册适配器
        APIAdapterRegistry.register("test_adapter", TestAPIAdapter)
        
        # 获取适配器类
        adapter_class = APIAdapterRegistry.get_adapter_class("test_adapter")
        assert adapter_class is TestAPIAdapter
        
        # 创建适配器实例
        adapter = APIAdapterRegistry.create_adapter("test_adapter")
        assert isinstance(adapter, TestAPIAdapter)
    
    def test_unknown_adapter_error(self):
        """测试：获取未知适配器抛出错误"""
        APIAdapterRegistry._adapters.clear()
        
        with pytest.raises(ValueError, match="Unknown API adapter"):
            APIAdapterRegistry.get_adapter_class("unknown_adapter")
    
    def test_list_adapters(self):
        """测试：列出所有适配器"""
        APIAdapterRegistry._adapters.clear()
        APIAdapterRegistry.register("adapter1", TestAPIAdapter)
        APIAdapterRegistry.register("adapter2", TestAPIAdapter)
        
        adapters = APIAdapterRegistry.list_adapters()
        assert "adapter1" in adapters
        assert "adapter2" in adapters
    
    def test_register_decorator(self):
        """测试：注册装饰器"""
        APIAdapterRegistry._adapters.clear()
        
        @register_adapter("decorated_adapter")
        class DecoratedAdapter(APIAdapter):
            async def call(self, operation, parameters, credentials):
                return {}
            
            def get_oauth2_config(self):
                return OAuth2Config("", "", "", "")
            
            def validate_credentials(self, credentials):
                return True
        
        # 验证装饰器已注册适配器
        adapter_class = APIAdapterRegistry.get_adapter_class("decorated_adapter")
        assert adapter_class is DecoratedAdapter


@pytest.mark.unit
class TestAPIErrors:
    """API错误类测试"""
    
    def test_api_error_base(self):
        """测试：基础API错误"""
        error = APIError("Test error", status_code=400, response_data={"key": "value"})
        
        assert str(error) == "Test error"
        assert error.status_code == 400
        assert error.response_data == {"key": "value"}
        assert isinstance(error.timestamp, datetime)
    
    def test_authentication_error(self):
        """测试：认证错误"""
        error = AuthenticationError("Auth failed", status_code=401)
        assert isinstance(error, APIError)
        assert error.status_code == 401
    
    def test_rate_limit_error(self):
        """测试：限流错误"""
        error = RateLimitError("Rate limited", retry_after=60)
        assert isinstance(error, APIError)
        assert error.retry_after == 60
    
    def test_temporary_error(self):
        """测试：临时错误"""
        error = TemporaryError("Temporary failure")
        assert isinstance(error, APIError)
    
    def test_permanent_error(self):
        """测试：永久错误"""
        error = PermanentError("Permanent failure")
        assert isinstance(error, APIError)