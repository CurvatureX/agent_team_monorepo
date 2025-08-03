"""
Tests for External APIs Router
外部API路由测试
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import status

from app.main import create_app
from app.models.external_api import ExternalAPIProvider


@pytest.fixture
def client():
    """创建测试客户端"""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_auth_user():
    """Mock认证用户"""
    return {
        "sub": "test_user_123",
        "email": "test@example.com",
        "email_verified": True
    }


@pytest.fixture
def auth_headers():
    """认证头部"""
    return {"Authorization": "Bearer mock_jwt_token"}


class TestExternalAPIsAuth:
    """外部API认证测试"""
    
    def test_auth_required_for_all_endpoints(self, client):
        """测试：所有端点都需要认证"""
        endpoints = [
            "/api/app/external-apis/auth/authorize",
            "/api/app/external-apis/credentials",
            "/api/app/external-apis/test-call",
            "/api/app/external-apis/status",
            "/api/app/external-apis/metrics"
        ]
        
        for endpoint in endpoints:
            if "authorize" in endpoint or "test-call" in endpoint:
                # POST端点
                response = client.post(endpoint)
            elif "credentials/google" in endpoint:
                # DELETE端点
                response = client.delete(endpoint)
            else:
                # GET端点
                response = client.get(endpoint)
            
            assert response.status_code in [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
                status.HTTP_422_UNPROCESSABLE_ENTITY  # 可能因为缺少认证依赖而导致
            ]


class TestOAuth2Authorization:
    """OAuth2授权测试"""
    
    @patch('app.dependencies.verify_supabase_token')
    def test_start_oauth2_authorization_success(self, mock_verify, client, mock_auth_user, auth_headers):
        """测试：成功启动OAuth2授权"""
        mock_verify.return_value = mock_auth_user
        
        request_data = {
            "provider": "google_calendar",
            "scopes": ["https://www.googleapis.com/auth/calendar"],
            "redirect_url": "https://app.example.com/callback"
        }
        
        response = client.post(
            "/api/app/external-apis/auth/authorize",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "auth_url" in data
        assert "state" in data
        assert "expires_at" in data
        assert data["provider"] == "google_calendar"
        assert "mock_client" in data["auth_url"]
    
    @patch('app.dependencies.verify_supabase_token')
    def test_start_oauth2_authorization_invalid_provider(self, mock_verify, client, mock_auth_user, auth_headers):
        """测试：无效的API提供商"""
        mock_verify.return_value = mock_auth_user
        
        request_data = {
            "provider": "invalid_provider",
            "scopes": []
        }
        
        response = client.post(
            "/api/app/external-apis/auth/authorize",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @patch('app.dependencies.verify_supabase_token')
    def test_oauth2_callback_success(self, mock_verify, client, mock_auth_user, auth_headers):
        """测试：成功处理OAuth2回调"""
        mock_verify.return_value = mock_auth_user
        
        state = f"state_google_calendar_{mock_auth_user['sub']}_1234567890"
        
        response = client.get(
            f"/api/app/external-apis/auth/callback?code=test_code_123&state={state}&provider=google_calendar",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "access_token" in data
        assert "token_type" in data
        assert data["provider"] == "google_calendar"
        assert data["token_type"] == "Bearer"
    
    @patch('app.dependencies.verify_supabase_token')
    def test_oauth2_callback_invalid_state(self, mock_verify, client, mock_auth_user, auth_headers):
        """测试：无效的state参数"""
        mock_verify.return_value = mock_auth_user
        
        response = client.get(
            "/api/app/external-apis/auth/callback?code=test_code_123&state=invalid_state&provider=google_calendar",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Invalid state parameter" in data["detail"]


class TestCredentialManagement:
    """凭证管理测试"""
    
    @patch('app.dependencies.verify_supabase_token')
    def test_list_user_credentials_success(self, mock_verify, client, mock_auth_user, auth_headers):
        """测试：成功获取用户凭证列表"""
        mock_verify.return_value = mock_auth_user
        
        response = client.get(
            "/api/app/external-apis/credentials",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "credentials" in data
        assert "total_count" in data
        assert isinstance(data["credentials"], list)
        assert data["total_count"] >= 0
        
        # 检查Mock数据结构
        if data["credentials"]:
            credential = data["credentials"][0]
            assert "provider" in credential
            assert "is_valid" in credential
            assert "scope" in credential
            assert "created_at" in credential
    
    @patch('app.dependencies.verify_supabase_token')
    def test_revoke_credential_success(self, mock_verify, client, mock_auth_user, auth_headers):
        """测试：成功撤销凭证"""
        mock_verify.return_value = mock_auth_user
        
        response = client.delete(
            "/api/app/external-apis/credentials/google_calendar",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["success"] is True
        assert "google_calendar" in data["message"]
        assert "details" in data
        assert data["details"]["provider"] == "google_calendar"
    
    @patch('app.dependencies.verify_supabase_token')
    def test_revoke_credential_invalid_provider(self, mock_verify, client, mock_auth_user, auth_headers):
        """测试：撤销无效提供商的凭证"""
        mock_verify.return_value = mock_auth_user
        
        response = client.delete(
            "/api/app/external-apis/credentials/invalid_provider",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestAPITesting:
    """API测试功能测试"""
    
    @patch('app.dependencies.verify_supabase_token')
    def test_test_api_call_success(self, mock_verify, client, mock_auth_user, auth_headers):
        """测试：成功执行API测试调用"""
        mock_verify.return_value = mock_auth_user
        
        request_data = {
            "provider": "google_calendar",
            "operation": "list_events",
            "parameters": {
                "calendar_id": "primary",
                "time_min": "2025-08-01T00:00:00Z"
            },
            "timeout_seconds": 30
        }
        
        response = client.post(
            "/api/app/external-apis/test-call",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["success"] is True
        assert data["provider"] == "google_calendar"
        assert data["operation"] == "list_events"
        assert "execution_time_ms" in data
        assert "result" in data
    
    @patch('app.dependencies.verify_supabase_token')
    def test_test_api_call_invalid_provider(self, mock_verify, client, mock_auth_user, auth_headers):
        """测试：无效提供商的API测试调用"""
        mock_verify.return_value = mock_auth_user
        
        request_data = {
            "provider": "invalid_provider",
            "operation": "test_operation",
            "parameters": {}
        }
        
        response = client.post(
            "/api/app/external-apis/test-call",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestStatusAndMetrics:
    """状态和指标测试"""
    
    @patch('app.dependencies.verify_supabase_token')
    def test_get_external_api_status_success(self, mock_verify, client, mock_auth_user, auth_headers):
        """测试：成功获取外部API状态"""
        mock_verify.return_value = mock_auth_user
        
        response = client.get(
            "/api/app/external-apis/status",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "providers" in data
        assert "total_available" in data
        assert "last_updated" in data
        assert isinstance(data["providers"], list)
        
        # 检查提供商状态结构
        if data["providers"]:
            provider_status = data["providers"][0]
            assert "provider" in provider_status
            assert "available" in provider_status
            assert "operations" in provider_status
            assert "last_check" in provider_status
    
    @patch('app.dependencies.verify_supabase_token')
    def test_get_external_api_metrics_success(self, mock_verify, client, mock_auth_user, auth_headers):
        """测试：成功获取外部API指标"""
        mock_verify.return_value = mock_auth_user
        
        response = client.get(
            "/api/app/external-apis/metrics?time_range=24h",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "metrics" in data
        assert "time_range" in data
        assert "generated_at" in data
        assert data["time_range"] == "24h"
        assert isinstance(data["metrics"], list)
        
        # 检查指标结构
        if data["metrics"]:
            metric = data["metrics"][0]
            assert "provider" in metric
            assert "total_calls" in metric
            assert "successful_calls" in metric
            assert "failed_calls" in metric
            assert "success_rate" in metric
    
    @patch('app.dependencies.verify_supabase_token')
    def test_get_external_api_metrics_invalid_time_range(self, mock_verify, client, mock_auth_user, auth_headers):
        """测试：无效时间范围的指标查询"""
        mock_verify.return_value = mock_auth_user
        
        response = client.get(
            "/api/app/external-apis/metrics?time_range=invalid",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Invalid time range" in data["detail"]


class TestErrorHandling:
    """错误处理测试"""
    
    @patch('app.dependencies.verify_supabase_token')
    def test_endpoint_without_auth_dependency(self, mock_verify, client):
        """测试：缺少认证依赖的端点"""
        # 不提供认证头部
        response = client.get("/api/app/external-apis/status")
        
        # 应该返回认证错误
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ]
    
    def test_malformed_request_data(self, client, auth_headers):
        """测试：格式错误的请求数据"""
        # 发送无效JSON
        response = client.post(
            "/api/app/external-apis/auth/authorize",
            data="invalid json",
            headers={**auth_headers, "Content-Type": "application/json"}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestExternalAPIProviderEnum:
    """外部API提供商枚举测试"""
    
    def test_provider_enum_values(self):
        """测试：提供商枚举值"""
        assert ExternalAPIProvider.GOOGLE_CALENDAR.value == "google_calendar"
        assert ExternalAPIProvider.GITHUB.value == "github"
        assert ExternalAPIProvider.SLACK.value == "slack"
        assert ExternalAPIProvider.HTTP_TOOL.value == "http_tool"
    
    def test_provider_enum_list(self):
        """测试：获取所有提供商"""
        providers = list(ExternalAPIProvider)
        assert len(providers) == 4
        assert ExternalAPIProvider.GOOGLE_CALENDAR in providers
        assert ExternalAPIProvider.GITHUB in providers
        assert ExternalAPIProvider.SLACK in providers
        assert ExternalAPIProvider.HTTP_TOOL in providers