"""
External Action Node测试
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone
import asyncio

from workflow_engine.nodes.external_action_node import (
    ExternalActionNodeExecutor,
    ExternalActionConfig,
    APICallResult,
    APIAdapterFactory,
    ExternalAPIProvider,
    create_external_action_executor,
    register_default_adapters
)
from workflow_engine.nodes.base import NodeExecutionContext, ExecutionStatus
from workflow_engine.services.api_adapters.base import APIError, AuthenticationError, TemporaryError


@pytest.mark.unit
class TestExternalActionConfig:
    """External Action配置测试"""
    
    def test_config_creation(self):
        """测试：配置创建"""
        config = ExternalActionConfig(
            api_service="google_calendar",
            operation="create_event",
            parameters={"summary": "Test Event"},
            retry_on_failure=True
        )
        
        assert config.api_service == "google_calendar"
        assert config.operation == "create_event"
        assert config.parameters["summary"] == "Test Event"
        assert config.retry_on_failure is True
    
    def test_config_validation_success(self):
        """测试：配置验证成功"""
        config = ExternalActionConfig(
            api_service="github",
            operation="create_issue"
        )
        
        errors = config.validate()
        assert len(errors) == 0
    
    def test_config_validation_missing_service(self):
        """测试：缺少API服务"""
        config = ExternalActionConfig(
            api_service="",
            operation="test_operation"
        )
        
        errors = config.validate()
        assert "api_service is required" in errors
    
    def test_config_validation_missing_operation(self):
        """测试：缺少操作"""
        config = ExternalActionConfig(
            api_service="slack",
            operation=""
        )
        
        errors = config.validate()
        assert "operation is required" in errors
    
    def test_config_validation_invalid_service(self):
        """测试：无效的API服务"""
        config = ExternalActionConfig(
            api_service="invalid_service",
            operation="test_operation"
        )
        
        errors = config.validate()
        assert any("Invalid api_service" in error for error in errors)


@pytest.mark.unit 
class TestAPICallResult:
    """API调用结果测试"""
    
    def test_success_result(self):
        """测试：成功结果"""
        result = APICallResult(
            success=True,
            data={"event_id": "123", "status": "created"},
            provider="google_calendar",
            operation="create_event",
            execution_time_ms=450.5
        )
        
        assert result.success is True
        assert result.data["event_id"] == "123"
        assert result.execution_time_ms == 450.5
    
    def test_error_result(self):
        """测试：错误结果"""
        result = APICallResult(
            success=False,
            data={},
            provider="github",
            operation="create_issue",
            execution_time_ms=200.0,
            error_message="Authentication failed",
            api_response_status=401
        )
        
        assert result.success is False
        assert result.error_message == "Authentication failed"
        assert result.api_response_status == 401
    
    def test_to_dict(self):
        """测试：转换为字典"""
        result = APICallResult(
            success=True,
            data={"test": "data"},
            provider="slack",
            operation="send_message",
            execution_time_ms=100.0
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["success"] is True
        assert result_dict["data"]["test"] == "data"
        assert result_dict["provider"] == "slack"
        assert result_dict["operation"] == "send_message"
        assert "timestamp" in result_dict


@pytest.mark.unit
class TestAPIAdapterFactory:
    """API适配器工厂测试"""
    
    def test_create_adapter_success(self):
        """测试：成功创建适配器"""
        # Mock adapter registry
        with patch('workflow_engine.nodes.external_action_node.APIAdapterRegistry') as mock_registry:
            mock_adapter_class = Mock()
            mock_adapter = Mock()
            mock_adapter_class.return_value = mock_adapter
            mock_registry.get_adapter_class.return_value = mock_adapter_class
            
            adapter = APIAdapterFactory.create_adapter("google_calendar")
            
            assert adapter is mock_adapter
            mock_registry.get_adapter_class.assert_called_once_with("google_calendar")
            mock_adapter_class.assert_called_once()
    
    def test_create_adapter_failure(self):
        """测试：创建适配器失败"""
        with patch('workflow_engine.nodes.external_action_node.APIAdapterRegistry') as mock_registry:
            mock_registry.get_adapter_class.side_effect = ValueError("Unknown adapter")
            
            with pytest.raises(APIError, match="Unsupported API service"):
                APIAdapterFactory.create_adapter("unknown_service")
    
    def test_get_available_adapters(self):
        """测试：获取可用适配器"""
        with patch('workflow_engine.nodes.external_action_node.APIAdapterRegistry') as mock_registry:
            mock_registry.list_adapters.return_value = ["google_calendar", "github", "slack"]
            
            adapters = APIAdapterFactory.get_available_adapters()
            
            assert "google_calendar" in adapters
            assert "github" in adapters
            assert "slack" in adapters


@pytest.mark.unit
class TestExternalActionNodeExecutor:
    """External Action Node执行器测试"""
    
    @pytest.fixture
    def executor(self):
        """创建执行器实例"""
        mock_oauth2_service = AsyncMock()
        mock_encryption_service = Mock()
        return ExternalActionNodeExecutor(
            oauth2_service=mock_oauth2_service,
            encryption_service=mock_encryption_service
        )
    
    @pytest.fixture
    def mock_context(self):
        """创建Mock执行上下文"""
        mock_node = Mock()
        mock_node.parameters = {
            "api_service": "google_calendar",
            "operation": "create_event",
            "parameters": {
                "summary": "Test Meeting",
                "start": {"dateTime": "2024-12-20T10:00:00Z"},
                "end": {"dateTime": "2024-12-20T11:00:00Z"}
            }
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
        
        assert "external_api_call" in subtypes
        assert "api_integration" in subtypes
        assert "webhook_call" in subtypes
    
    def test_validate_valid_node(self, executor):
        """测试：验证有效节点"""
        mock_node = Mock()
        mock_node.parameters = {
            "api_service": "github",
            "operation": "create_issue"
        }
        
        with patch('workflow_engine.nodes.external_action_node.APIAdapterFactory') as mock_factory:
            mock_factory.get_available_adapters.return_value = ["github", "slack"]
            
            errors = executor.validate(mock_node)
            
            assert len(errors) == 0
    
    def test_validate_invalid_node(self, executor):
        """测试：验证无效节点"""
        mock_node = Mock()
        mock_node.parameters = {
            "api_service": "",  # 缺少API服务
            "operation": "test_operation"
        }
        
        errors = executor.validate(mock_node)
        
        assert len(errors) > 0
        assert any("api_service is required" in error for error in errors)
    
    def test_validate_missing_parameters(self, executor):
        """测试：验证缺少参数的节点"""
        mock_node = Mock()
        del mock_node.parameters  # 删除parameters属性
        
        errors = executor.validate(mock_node)
        
        assert "Node missing parameters" in errors
    
    def test_parse_config(self, executor, mock_context):
        """测试：解析配置"""
        config = executor._parse_config(mock_context.node.parameters)
        
        assert config.api_service == "google_calendar"
        assert config.operation == "create_event"
        assert config.parameters["summary"] == "Test Meeting"
        assert config.retry_on_failure is True  # 默认值
    
    @pytest.mark.asyncio
    async def test_get_user_credentials_success(self, executor):
        """测试：获取用户凭证成功"""
        executor.oauth2_service.get_valid_token.return_value = "access_token_123"
        
        logs = []
        credentials = await executor._get_user_credentials("user_123", "google_calendar", logs)
        
        assert credentials == {"access_token": "access_token_123"}
        assert any("Retrieved valid credentials" in log for log in logs)
    
    @pytest.mark.asyncio
    async def test_get_user_credentials_no_token(self, executor):
        """测试：获取用户凭证失败 - 无令牌"""
        executor.oauth2_service.get_valid_token.return_value = None
        
        logs = []
        credentials = await executor._get_user_credentials("user_123", "google_calendar", logs)
        
        assert credentials is None
        assert any("No valid credentials found" in log for log in logs)
    
    @pytest.mark.asyncio
    async def test_get_user_credentials_exception(self, executor):
        """测试：获取用户凭证异常"""
        executor.oauth2_service.get_valid_token.side_effect = Exception("Token service error")
        
        logs = []
        credentials = await executor._get_user_credentials("user_123", "google_calendar", logs)
        
        assert credentials is None
        assert any("Failed to retrieve credentials" in log for log in logs)
    
    @pytest.mark.asyncio
    async def test_execute_api_call_success(self, executor):
        """测试：成功执行API调用"""
        # Mock adapter
        mock_adapter = AsyncMock()
        mock_adapter.validate_credentials.return_value = True
        mock_adapter.call.return_value = {"event_id": "123", "status": "created"}
        
        config = ExternalActionConfig(
            api_service="google_calendar",
            operation="create_event",
            parameters={"summary": "Test"}
        )
        
        credentials = {"access_token": "token_123"}
        logs = []
        
        result = await executor._execute_api_call(mock_adapter, config, credentials, logs)
        
        assert result.success is True
        assert result.data["event_id"] == "123"
        assert result.provider == "google_calendar"
        assert result.operation == "create_event"
        assert result.execution_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_execute_api_call_invalid_credentials(self, executor):
        """测试：无效凭证的API调用"""
        mock_adapter = AsyncMock()
        mock_adapter.validate_credentials.return_value = False
        
        config = ExternalActionConfig(
            api_service="github",
            operation="create_issue"
        )
        
        credentials = {"invalid": "credentials"}
        logs = []
        
        result = await executor._execute_api_call(mock_adapter, config, credentials, logs)
        
        assert result.success is False
        assert result.error_message == "Invalid credentials format"
    
    @pytest.mark.asyncio
    async def test_execute_api_call_timeout(self, executor):
        """测试：API调用超时"""
        mock_adapter = AsyncMock()
        mock_adapter.validate_credentials.return_value = True
        
        # 模拟超时
        async def slow_call(*args, **kwargs):
            await asyncio.sleep(2)
            return {"result": "too slow"}
        
        mock_adapter.call = slow_call
        
        config = ExternalActionConfig(
            api_service="slack",
            operation="send_message",
            timeout_seconds=1  # 1秒超时
        )
        
        credentials = {"access_token": "token_123"}
        logs = []
        
        result = await executor._execute_api_call(mock_adapter, config, credentials, logs)
        
        assert result.success is False
        assert "timed out" in result.error_message
    
    @pytest.mark.asyncio
    async def test_execute_api_call_api_error(self, executor):
        """测试：API错误处理"""
        mock_adapter = AsyncMock()
        mock_adapter.validate_credentials.return_value = True
        mock_adapter.call.side_effect = AuthenticationError(
            "Invalid token", 
            status_code=401,
            response_data={"error": "unauthorized"}
        )
        
        config = ExternalActionConfig(
            api_service="github",
            operation="create_issue"
        )
        
        credentials = {"access_token": "invalid_token"}
        logs = []
        
        result = await executor._execute_api_call(mock_adapter, config, credentials, logs)
        
        assert result.success is False
        assert result.error_message == "Invalid token"
        assert result.api_response_status == 401
        assert result.error_details == {"error": "unauthorized"}
    
    @pytest.mark.asyncio
    async def test_execute_success(self, executor, mock_context):
        """测试：完整的节点执行成功"""
        # Mock OAuth2 service
        executor.oauth2_service.get_valid_token.return_value = "access_token_123"
        
        # Mock adapter factory and adapter
        with patch('workflow_engine.nodes.external_action_node.APIAdapterFactory') as mock_factory:
            mock_adapter = AsyncMock()
            mock_adapter.validate_credentials.return_value = True
            mock_adapter.call.return_value = {"event_id": "123", "status": "created"}
            mock_factory.create_adapter.return_value = mock_adapter
            
            # Mock logging
            with patch.object(executor, '_log_api_call') as mock_log:
                result = await executor.execute(mock_context)
        
        assert result.status == ExecutionStatus.SUCCESS
        assert result.output_data["response_data"]["event_id"] == "123"
        assert "api_result" in result.output_data
        assert result.metadata["api_service"] == "google_calendar"
        assert result.metadata["operation"] == "create_event"
    
    @pytest.mark.asyncio
    async def test_execute_no_user_id(self, executor, mock_context):
        """测试：执行缺少用户ID"""
        # 移除user_id
        mock_context.metadata = {}
        
        result = await executor.execute(mock_context)
        
        assert result.status == ExecutionStatus.ERROR
        assert "User ID not found" in result.error_message
    
    @pytest.mark.asyncio
    async def test_execute_no_credentials(self, executor, mock_context):
        """测试：执行无凭证"""
        # Mock OAuth2 service返回None (无凭证)
        executor.oauth2_service.get_valid_token.return_value = None
        
        result = await executor.execute(mock_context)
        
        assert result.status == ExecutionStatus.ERROR
        assert "No valid credentials found" in result.error_message
    
    @pytest.mark.asyncio
    async def test_execute_config_validation_error(self, executor, mock_context):
        """测试：执行配置验证错误"""
        # 设置无效配置
        mock_context.node.parameters = {
            "api_service": "",  # 无效
            "operation": "test_operation"
        }
        
        result = await executor.execute(mock_context)
        
        assert result.status == ExecutionStatus.ERROR
        assert "Configuration validation failed" in result.error_message
    
    @pytest.mark.asyncio
    async def test_execute_api_call_failure(self, executor, mock_context):
        """测试：API调用失败"""
        # Mock OAuth2 service
        executor.oauth2_service.get_valid_token.return_value = "access_token_123"
        
        # Mock adapter factory and adapter with failure
        with patch('workflow_engine.nodes.external_action_node.APIAdapterFactory') as mock_factory:
            mock_adapter = AsyncMock()
            mock_adapter.validate_credentials.return_value = True
            mock_adapter.call.side_effect = TemporaryError("Service temporarily unavailable")
            mock_factory.create_adapter.return_value = mock_adapter
            
            with patch.object(executor, '_log_api_call') as mock_log:
                result = await executor.execute(mock_context)
        
        assert result.status == ExecutionStatus.ERROR
        assert "Service temporarily unavailable" in result.error_message
        assert result.error_details["provider"] == "google_calendar"
        assert result.error_details["operation"] == "create_event"


@pytest.mark.unit
class TestFactoryAndRegistration:
    """工厂函数和注册测试"""
    
    def test_create_external_action_executor(self):
        """测试：创建执行器"""
        mock_oauth2_service = Mock()
        mock_encryption_service = Mock()
        
        executor = create_external_action_executor(
            oauth2_service=mock_oauth2_service,
            encryption_service=mock_encryption_service
        )
        
        assert isinstance(executor, ExternalActionNodeExecutor)
        assert executor.oauth2_service is mock_oauth2_service
        assert executor.encryption_service is mock_encryption_service
    
    def test_create_external_action_executor_no_dependencies(self):
        """测试：创建执行器（无依赖）"""
        executor = create_external_action_executor()
        
        assert isinstance(executor, ExternalActionNodeExecutor)
        assert executor.oauth2_service is None
        assert executor.encryption_service is None
    
    def test_register_default_adapters(self):
        """测试：注册默认适配器"""
        with patch('workflow_engine.nodes.external_action_node.APIAdapterRegistry') as mock_registry:
            # Mock imports succeed
            with patch('workflow_engine.nodes.external_action_node.GoogleCalendarAdapter') as mock_gc:
                with patch('workflow_engine.nodes.external_action_node.GitHubAdapter') as mock_gh:
                    with patch('workflow_engine.nodes.external_action_node.SlackAdapter') as mock_slack:
                        register_default_adapters()
            
            # 验证注册调用
            expected_calls = [
                ("google_calendar", mock_gc),
                ("github", mock_gh),
                ("slack", mock_slack)
            ]
            
            assert mock_registry.register.call_count == 3


@pytest.mark.integration
class TestExternalActionNodeIntegration:
    """External Action Node集成测试"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_execution(self):
        """测试：端到端执行"""
        # 这是一个集成测试，需要真实的服务和适配器
        # 在真实环境中，这会连接到实际的OAuth2服务和API适配器
        
        # Mock all dependencies for this test
        mock_oauth2_service = AsyncMock()
        mock_oauth2_service.get_valid_token.return_value = "real_access_token"
        
        executor = ExternalActionNodeExecutor(oauth2_service=mock_oauth2_service)
        
        # Create realistic context
        mock_node = Mock()
        mock_node.parameters = {
            "api_service": "google_calendar",
            "operation": "list_events",
            "parameters": {
                "calendar_id": "primary",
                "time_min": "2024-12-01T00:00:00Z",
                "time_max": "2024-12-31T23:59:59Z"
            }
        }
        
        context = NodeExecutionContext(
            node=mock_node,
            workflow_id="integration_test_workflow",
            execution_id="integration_test_execution",
            input_data={},
            static_data={},
            credentials={},
            metadata={"user_id": "integration_test_user"}
        )
        
        # Mock the adapter
        with patch('workflow_engine.nodes.external_action_node.APIAdapterFactory') as mock_factory:
            mock_adapter = AsyncMock()
            mock_adapter.validate_credentials.return_value = True
            mock_adapter.call.return_value = {
                "events": [
                    {
                        "id": "event_1",
                        "summary": "Integration Test Event",
                        "start": {"dateTime": "2024-12-20T10:00:00Z"}
                    }
                ],
                "total_count": 1
            }
            mock_factory.create_adapter.return_value = mock_adapter
            
            with patch.object(executor, '_log_api_call') as mock_log:
                result = await executor.execute(context)
        
        # Verify successful execution
        assert result.status == ExecutionStatus.SUCCESS
        assert "events" in result.output_data["response_data"]
        assert len(result.output_data["response_data"]["events"]) == 1
        assert result.metadata["api_service"] == "google_calendar"
        assert result.metadata["operation"] == "list_events"
        
        # Verify API call was logged
        mock_log.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_multiple_provider_support(self):
        """测试：多Provider支持"""
        providers_and_operations = [
            ("google_calendar", "list_events"),
            ("github", "list_repos"),
            ("slack", "list_channels")
        ]
        
        mock_oauth2_service = AsyncMock()
        mock_oauth2_service.get_valid_token.return_value = "provider_token"
        
        executor = ExternalActionNodeExecutor(oauth2_service=mock_oauth2_service)
        
        for provider, operation in providers_and_operations:
            mock_node = Mock()
            mock_node.parameters = {
                "api_service": provider,
                "operation": operation,
                "parameters": {}
            }
            
            context = NodeExecutionContext(
                node=mock_node,
                workflow_id="multi_provider_test",
                execution_id=f"exec_{provider}",
                input_data={},
                static_data={},
                credentials={},
                metadata={"user_id": "test_user"}
            )
            
            # Mock provider-specific adapter
            with patch('workflow_engine.nodes.external_action_node.APIAdapterFactory') as mock_factory:
                mock_adapter = AsyncMock()
                mock_adapter.validate_credentials.return_value = True
                mock_adapter.call.return_value = {f"{provider}_data": "success"}
                mock_factory.create_adapter.return_value = mock_adapter
                
                with patch.object(executor, '_log_api_call'):
                    result = await executor.execute(context)
            
            assert result.status == ExecutionStatus.SUCCESS
            assert result.metadata["api_service"] == provider
            assert result.metadata["operation"] == operation
            assert f"{provider}_data" in result.output_data["response_data"]