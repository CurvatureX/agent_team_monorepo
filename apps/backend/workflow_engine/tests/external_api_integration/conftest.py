"""
测试配置和共享Fixtures
外部API集成测试的配置文件
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json
import uuid

# 测试用的假数据
TEST_USER_ID = "test-user-12345"
TEST_WORKFLOW_ID = "test-workflow-67890"
TEST_ENCRYPTION_KEY = "test-key-32-chars-long-12345678"

@pytest.fixture(scope="session")
def event_loop():
    """创建全局事件循环"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def test_user_id():
    """测试用户ID"""
    return TEST_USER_ID

@pytest.fixture
def test_workflow_id():
    """测试工作流ID"""
    return TEST_WORKFLOW_ID

@pytest.fixture
def mock_encryption_key():
    """Mock加密密钥"""
    return TEST_ENCRYPTION_KEY

@pytest.fixture
def mock_database():
    """Mock数据库连接"""
    db_mock = AsyncMock()
    
    # Mock查询结果
    db_mock.fetch_one = AsyncMock()
    db_mock.fetch_all = AsyncMock()
    db_mock.execute = AsyncMock()
    
    return db_mock

@pytest.fixture
def mock_redis():
    """Mock Redis连接"""
    redis_mock = AsyncMock()
    
    # Mock Redis操作
    redis_mock.get = AsyncMock()
    redis_mock.set = AsyncMock()
    redis_mock.delete = AsyncMock()
    redis_mock.exists = AsyncMock()
    
    return redis_mock

@pytest.fixture
def sample_google_calendar_credentials():
    """Google Calendar测试凭证"""
    return {
        "access_token": "ya29.test_access_token_google",
        "refresh_token": "1//test_refresh_token_google", 
        "token_type": "Bearer",
        "expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
        "scope": ["https://www.googleapis.com/auth/calendar"]
    }

@pytest.fixture
def sample_github_credentials():
    """GitHub测试凭证"""
    return {
        "access_token": "ghp_test_access_token_github",
        "token_type": "Bearer", 
        "scope": ["repo", "issues", "pull_requests"]
    }

@pytest.fixture  
def sample_slack_credentials():
    """Slack测试凭证"""
    return {
        "access_token": "xoxb-test-slack-bot-token",
        "token_type": "Bearer",
        "scope": ["chat:write", "channels:read", "files:write"]
    }

@pytest.fixture
def mock_google_calendar_response():
    """Mock Google Calendar API响应"""
    return {
        "kind": "calendar#events",
        "etag": "test_etag",
        "summary": "Test Calendar",
        "items": [
            {
                "id": "test_event_1",
                "status": "confirmed",
                "htmlLink": "https://calendar.google.com/event?eid=test",
                "created": "2025-08-01T10:00:00.000Z",
                "updated": "2025-08-01T10:00:00.000Z",
                "summary": "Test Meeting",
                "description": "This is a test meeting",
                "start": {
                    "dateTime": "2025-08-02T10:00:00+08:00",
                    "timeZone": "Asia/Shanghai"
                },
                "end": {
                    "dateTime": "2025-08-02T11:00:00+08:00",
                    "timeZone": "Asia/Shanghai"
                },
                "attendees": [
                    {
                        "email": "test@example.com",
                        "responseStatus": "accepted"
                    }
                ]
            }
        ]
    }

@pytest.fixture
def mock_github_response():
    """Mock GitHub API响应"""
    return {
        "id": 123456,
        "number": 42,
        "title": "Test Issue",
        "body": "This is a test issue description",
        "state": "open",
        "html_url": "https://github.com/test/repo/issues/42",
        "user": {
            "login": "testuser",
            "id": 12345
        },
        "labels": [
            {
                "name": "bug",
                "color": "d73a49"
            }
        ],
        "assignees": [
            {
                "login": "assignee1",
                "id": 67890
            }
        ],
        "created_at": "2025-08-02T10:00:00Z",
        "updated_at": "2025-08-02T10:00:00Z"
    }

@pytest.fixture
def mock_slack_response():
    """Mock Slack API响应"""
    return {
        "ok": True,
        "channel": "C1234567890",
        "ts": "1625097600.000100",
        "message": {
            "type": "message",
            "text": "Test message",
            "user": "U1234567890",
            "ts": "1625097600.000100",
            "team": "T1234567890"
        }
    }

@pytest.fixture
def mock_oauth2_config():
    """Mock OAuth2配置"""
    return {
        "google_calendar": {
            "client_id": "test_google_client_id",
            "client_secret": "test_google_client_secret",
            "redirect_uri": "http://localhost:8000/auth/google/callback",
            "auth_url": "https://accounts.google.com/o/oauth2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "scopes": ["https://www.googleapis.com/auth/calendar"]
        },
        "github": {
            "client_id": "test_github_client_id", 
            "client_secret": "test_github_client_secret",
            "redirect_uri": "http://localhost:8000/auth/github/callback",
            "auth_url": "https://github.com/login/oauth/authorize",
            "token_url": "https://github.com/login/oauth/access_token",
            "scopes": ["repo", "read:user"]
        },
        "slack": {
            "client_id": "test_slack_client_id",
            "client_secret": "test_slack_client_secret", 
            "redirect_uri": "http://localhost:8000/auth/slack/callback",
            "auth_url": "https://slack.com/oauth/v2/authorize",
            "token_url": "https://slack.com/api/oauth.v2.access",
            "scopes": ["chat:write", "channels:read"]
        }
    }

@pytest.fixture
def mock_http_response():
    """Mock HTTP响应"""
    response_mock = Mock()
    response_mock.status_code = 200
    response_mock.headers = {"content-type": "application/json"}
    response_mock.json.return_value = {"success": True, "data": "test"}
    response_mock.text = '{"success": true, "data": "test"}'
    response_mock.raise_for_status = Mock()
    return response_mock

@pytest.fixture
def sample_node_config():
    """示例节点配置"""
    return {
        "node_type": "EXTERNAL_ACTION",
        "name": "Test External Action",
        "parameters": {
            "api_service": "google_calendar",
            "operation": "list_events",
            "parameters": {
                "calendar_id": "primary",
                "time_min": "2025-08-01T00:00:00Z",
                "time_max": "2025-08-31T23:59:59Z"
            }
        }
    }

@pytest.fixture
def sample_execution_context():
    """示例执行上下文"""
    return {
        "execution_id": str(uuid.uuid4()),
        "workflow_id": TEST_WORKFLOW_ID,
        "user_id": TEST_USER_ID,
        "node_id": str(uuid.uuid4()),
        "input_data": {"test": "data"},
        "variables": {},
        "metadata": {}
    }

# 测试辅助函数
def create_mock_adapter(api_service: str, mock_response: Dict[str, Any]):
    """创建Mock API适配器"""
    adapter_mock = AsyncMock()
    adapter_mock.call = AsyncMock(return_value=mock_response)
    adapter_mock.validate_credentials = Mock(return_value=True)
    adapter_mock.get_oauth2_config = Mock(return_value={
        "client_id": f"test_{api_service}_client_id",
        "scopes": ["test_scope"]
    })
    return adapter_mock

def create_mock_credentials_db_record(provider: str, user_id: str = TEST_USER_ID):
    """创建Mock凭证数据库记录"""
    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "provider": provider,
        "credential_type": "oauth2",
        "encrypted_access_token": "encrypted_access_token",
        "encrypted_refresh_token": "encrypted_refresh_token", 
        "token_expires_at": datetime.now() + timedelta(hours=1),
        "scope": ["test_scope"],
        "is_valid": True,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }

def assert_node_result_success(result: Dict[str, Any], expected_data: Optional[Dict[str, Any]] = None):
    """断言节点执行结果成功"""
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result
    assert "metadata" in result
    
    if expected_data:
        assert result["data"] == expected_data

def assert_node_result_failure(result: Dict[str, Any], expected_error_type: Optional[str] = None):
    """断言节点执行结果失败"""
    assert result["success"] is False
    assert result["error"] is not None
    
    if expected_error_type:
        assert expected_error_type in str(result["error"])

# Pytest标记
pytest.mark.unit = pytest.mark.mark("unit", "单元测试")
pytest.mark.integration = pytest.mark.mark("integration", "集成测试") 
pytest.mark.external_api = pytest.mark.mark("external_api", "外部API测试")
pytest.mark.oauth2 = pytest.mark.mark("oauth2", "OAuth2相关测试")
pytest.mark.slow = pytest.mark.mark("slow", "慢速测试")