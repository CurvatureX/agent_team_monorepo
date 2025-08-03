"""
Slack API适配器测试
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone
import json

from workflow_engine.services.api_adapters.slack import SlackAdapter
from workflow_engine.services.api_adapters.base import (
    ValidationError, 
    AuthenticationError, 
    TemporaryError,
    OAuth2Config
)


@pytest.mark.unit
class TestSlackAdapter:
    """Slack适配器单元测试"""
    
    @pytest.fixture
    def adapter(self):
        """创建Slack适配器实例"""
        return SlackAdapter()
    
    @pytest.fixture
    def valid_credentials_oauth(self):
        """有效的Slack OAuth凭证"""
        return {
            "access_token": "xoxp-test-slack-access-token-12345"
        }
    
    @pytest.fixture
    def valid_credentials_bot(self):
        """有效的Slack Bot Token凭证"""
        return {
            "bot_token": "xoxb-test-slack-bot-token-12345"
        }
    
    @pytest.fixture
    def valid_credentials_webhook(self):
        """有效的Slack Webhook凭证"""
        return {
            "webhook_url": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
        }
    
    @pytest.fixture
    def sample_message_data(self):
        """示例消息数据"""
        return {
            "channel": "#general",
            "text": "Hello from the workflow engine!",
            "username": "WorkflowBot",
            "icon_emoji": ":robot_face:"
        }
    
    def test_adapter_initialization(self, adapter):
        """测试：适配器初始化"""
        assert adapter.provider_name == "slack"
        assert adapter.BASE_URL == "https://slack.com/api"
        assert "send_message" in adapter.OPERATIONS
        assert "list_channels" in adapter.OPERATIONS
        assert "create_channel" in adapter.OPERATIONS
    
    def test_oauth2_config(self, adapter):
        """测试：OAuth2配置"""
        config = adapter.get_oauth2_config()
        
        assert isinstance(config, OAuth2Config)
        assert config.auth_url == "https://slack.com/oauth/v2/authorize"
        assert config.token_url == "https://slack.com/api/oauth.v2.access"
        assert "chat:write" in config.scopes
        assert "channels:read" in config.scopes
    
    def test_validate_credentials_oauth_valid(self, adapter, valid_credentials_oauth):
        """测试：有效OAuth凭证验证"""
        assert adapter.validate_credentials(valid_credentials_oauth) is True
    
    def test_validate_credentials_bot_valid(self, adapter, valid_credentials_bot):
        """测试：有效Bot Token凭证验证"""
        assert adapter.validate_credentials(valid_credentials_bot) is True
    
    def test_validate_credentials_webhook_valid(self, adapter, valid_credentials_webhook):
        """测试：有效Webhook凭证验证"""
        assert adapter.validate_credentials(valid_credentials_webhook) is True
    
    def test_validate_credentials_invalid(self, adapter):
        """测试：无效凭证验证"""
        # 缺少所有认证方式
        invalid_creds = {"refresh_token": "refresh_123"}
        assert adapter.validate_credentials(invalid_creds) is False
        
        # 空凭证
        empty_creds = {"access_token": "", "bot_token": "", "webhook_url": ""}
        assert adapter.validate_credentials(empty_creds) is False
    
    def test_get_supported_operations(self, adapter):
        """测试：获取支持的操作"""
        operations = adapter.get_supported_operations()
        
        expected_operations = [
            "send_message", "send_dm", "list_channels", "create_channel",
            "list_users", "get_user_info", "search_messages", "get_team_info",
            "post_webhook", "upload_file", "join_channel"
        ]
        
        for op in expected_operations:
            assert op in operations
    
    def test_get_operation_description(self, adapter):
        """测试：获取操作描述"""
        description = adapter.get_operation_description("send_message")
        assert description == "发送消息到频道"
        
        # 不存在的操作
        assert adapter.get_operation_description("nonexistent") is None
    
    def test_prepare_headers_oauth(self, adapter, valid_credentials_oauth):
        """测试：准备OAuth认证头部"""
        headers = adapter._prepare_headers(valid_credentials_oauth)
        assert headers["Authorization"] == "Bearer xoxp-test-slack-access-token-12345"
        assert headers["Content-Type"] == "application/json"
    
    def test_prepare_headers_bot(self, adapter, valid_credentials_bot):
        """测试：准备Bot Token认证头部"""
        headers = adapter._prepare_headers(valid_credentials_bot)
        assert headers["Authorization"] == "Bearer xoxb-test-slack-bot-token-12345"
    
    @pytest.mark.asyncio
    async def test_call_unsupported_operation(self, adapter, valid_credentials_oauth):
        """测试：调用不支持的操作"""
        with pytest.raises(ValidationError, match="Unsupported operation"):
            await adapter.call("unsupported_op", {}, valid_credentials_oauth)
    
    @pytest.mark.asyncio
    async def test_call_invalid_credentials(self, adapter):
        """测试：使用无效凭证调用"""
        invalid_creds = {"invalid": "credentials"}
        
        with pytest.raises(ValidationError, match="Invalid credentials"):
            await adapter.call("send_message", {}, invalid_creds)


@pytest.mark.unit
class TestSlackMessages:
    """Slack消息操作测试"""
    
    @pytest.fixture
    def adapter(self):
        return SlackAdapter()
    
    @pytest.fixture
    def valid_credentials(self):
        return {"access_token": "xoxp-test-token"}
    
    @pytest.fixture
    def mock_slack_response(self):
        """Mock Slack API响应"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.status_code = 200
        return mock_response
    
    @pytest.mark.asyncio
    async def test_send_message_basic(self, adapter, valid_credentials, mock_slack_response):
        """测试：发送基本消息"""
        # Mock响应数据
        mock_slack_response.json.return_value = {
            "ok": True,
            "channel": "C1234567890",
            "ts": "1234567890.123456",
            "message": {
                "text": "Hello World!",
                "user": "U1234567890",
                "ts": "1234567890.123456"
            }
        }
        
        parameters = {
            "channel": "#general",
            "text": "Hello World!"
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_slack_response):
            result = await adapter.call("send_message", parameters, valid_credentials)
        
        assert result["success"] is True
        assert result["ts"] == "1234567890.123456"
        assert result["channel"] == "C1234567890"
    
    @pytest.mark.asyncio
    async def test_send_message_with_formatting(self, adapter, valid_credentials, mock_slack_response):
        """测试：发送带格式的消息"""
        mock_slack_response.json.return_value = {
            "ok": True,
            "channel": "C1234567890",
            "ts": "1234567890.123456"
        }
        
        parameters = {
            "channel": "#general",
            "text": "Formatted message",
            "username": "Custom Bot",
            "icon_emoji": ":robot_face:",
            "thread_ts": "1234567890.000000",
            "unfurl_links": False,
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Bold text* and _italic text_"
                    }
                }
            ]
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_slack_response) as mock_request:
            result = await adapter.call("send_message", parameters, valid_credentials)
        
        assert result["success"] is True
        
        # 验证请求数据
        args, kwargs = mock_request.call_args
        json_data = kwargs["json_data"]
        assert json_data["username"] == "Custom Bot"
        assert json_data["icon_emoji"] == ":robot_face:"
        assert json_data["thread_ts"] == "1234567890.000000"
        assert json_data["unfurl_links"] is False
        assert "blocks" in json_data
    
    @pytest.mark.asyncio
    async def test_send_message_missing_params(self, adapter, valid_credentials):
        """测试：发送消息缺少必需参数"""
        # 缺少text
        parameters = {"channel": "#general"}
        
        with pytest.raises(ValidationError, match="Missing required parameters: channel and text"):
            await adapter.call("send_message", parameters, valid_credentials)
        
        # 缺少channel
        parameters = {"text": "Hello"}
        
        with pytest.raises(ValidationError, match="Missing required parameters: channel and text"):
            await adapter.call("send_message", parameters, valid_credentials)
    
    @pytest.mark.asyncio
    async def test_send_message_slack_error(self, adapter, valid_credentials, mock_slack_response):
        """测试：Slack API返回错误"""
        mock_slack_response.json.return_value = {
            "ok": False,
            "error": "channel_not_found"
        }
        
        parameters = {
            "channel": "#nonexistent",
            "text": "Hello"
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_slack_response):
            with pytest.raises(TemporaryError, match="channel_not_found"):
                await adapter.call("send_message", parameters, valid_credentials)
    
    @pytest.mark.asyncio
    async def test_send_dm(self, adapter, valid_credentials, mock_slack_response):
        """测试：发送私信"""
        # Mock DM频道打开响应
        dm_response = Mock()
        dm_response.is_success = True
        dm_response.json.return_value = {
            "ok": True,
            "channel": {
                "id": "D1234567890"
            }
        }
        
        # Mock消息发送响应
        msg_response = Mock()
        msg_response.is_success = True
        msg_response.json.return_value = {
            "ok": True,
            "channel": "D1234567890",
            "ts": "1234567890.123456"
        }
        
        parameters = {
            "user": "U1234567890",
            "text": "Private message"
        }
        
        with patch.object(adapter, 'make_http_request', side_effect=[dm_response, msg_response]) as mock_request:
            result = await adapter.call("send_dm", parameters, valid_credentials)
        
        assert result["success"] is True
        assert result["channel"] == "D1234567890"
        
        # 验证两次API调用
        assert mock_request.call_count == 2
        
        # 第一次调用：打开DM频道
        first_call_args = mock_request.call_args_list[0]
        assert "conversations.open" in first_call_args[0][1]
        
        # 第二次调用：发送消息
        second_call_args = mock_request.call_args_list[1]
        assert "chat.postMessage" in second_call_args[0][1]
    
    @pytest.mark.asyncio
    async def test_update_message(self, adapter, valid_credentials, mock_slack_response):
        """测试：更新消息"""
        mock_slack_response.json.return_value = {
            "ok": True,
            "channel": "C1234567890",
            "ts": "1234567890.123456",
            "message": {
                "text": "Updated message",
                "ts": "1234567890.123456"
            }
        }
        
        parameters = {
            "channel": "C1234567890",
            "ts": "1234567890.123456",
            "text": "Updated message"
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_slack_response) as mock_request:
            result = await adapter.call("update_message", parameters, valid_credentials)
        
        assert result["success"] is True
        assert result["ts"] == "1234567890.123456"
        
        # 验证请求URL
        args, kwargs = mock_request.call_args
        assert "chat.update" in args[1]
        
        # 验证请求数据
        json_data = kwargs["json_data"]
        assert json_data["channel"] == "C1234567890"
        assert json_data["ts"] == "1234567890.123456"
        assert json_data["text"] == "Updated message"


@pytest.mark.unit
class TestSlackChannels:
    """Slack频道操作测试"""
    
    @pytest.fixture
    def adapter(self):
        return SlackAdapter()
    
    @pytest.fixture
    def valid_credentials(self):
        return {"bot_token": "xoxb-test-token"}
    
    @pytest.mark.asyncio
    async def test_list_channels(self, adapter, valid_credentials):
        """测试：列出频道"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "ok": True,
            "channels": [
                {
                    "id": "C1234567890",
                    "name": "general",
                    "is_channel": True,
                    "is_private": False,
                    "is_archived": False
                },
                {
                    "id": "C0987654321",
                    "name": "random", 
                    "is_channel": True,
                    "is_private": False,
                    "is_archived": False
                }
            ],
            "response_metadata": {
                "next_cursor": "next_cursor_token"
            }
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response):
            result = await adapter.call("list_channels", {}, valid_credentials)
        
        assert result["success"] is True
        assert len(result["channels"]) == 2
        assert result["next_cursor"] == "next_cursor_token"
        assert result["total_count"] == 2
    
    @pytest.mark.asyncio
    async def test_list_channels_with_filters(self, adapter, valid_credentials):
        """测试：带过滤条件的频道列表"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "ok": True,
            "channels": []
        }
        
        parameters = {
            "types": "public_channel,private_channel",
            "exclude_archived": True,
            "limit": 100
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response) as mock_request:
            await adapter.call("list_channels", parameters, valid_credentials)
        
        # 验证请求URL包含查询参数
        args, kwargs = mock_request.call_args
        url = args[1]
        
        assert "conversations.list" in url
        assert "types=public_channel%2Cprivate_channel" in url
        assert "exclude_archived=true" in url
        assert "limit=100" in url
    
    @pytest.mark.asyncio
    async def test_create_channel(self, adapter, valid_credentials):
        """测试：创建频道"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "ok": True,
            "channel": {
                "id": "C1234567890",
                "name": "new-channel",
                "is_channel": True,
                "creator": "U1234567890"
            }
        }
        
        parameters = {
            "name": "new-channel",
            "is_private": False
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response) as mock_request:
            result = await adapter.call("create_channel", parameters, valid_credentials)
        
        assert result["success"] is True
        assert result["channel_id"] == "C1234567890"
        
        # 验证请求数据
        json_data = mock_request.call_args[1]["json_data"]
        assert json_data["name"] == "new-channel"
        assert json_data["is_private"] is False
    
    @pytest.mark.asyncio
    async def test_create_channel_missing_name(self, adapter, valid_credentials):
        """测试：创建频道缺少名称"""
        parameters = {"is_private": False}
        
        with pytest.raises(ValidationError, match="Missing required parameter: name"):
            await adapter.call("create_channel", parameters, valid_credentials)
    
    @pytest.mark.asyncio
    async def test_join_channel(self, adapter, valid_credentials):
        """测试：加入频道"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "ok": True,
            "channel": {
                "id": "C1234567890",
                "name": "channel-to-join"
            },
            "warning": "already_in_channel"
        }
        
        parameters = {"channel": "C1234567890"}
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response) as mock_request:
            result = await adapter.call("join_channel", parameters, valid_credentials)
        
        assert result["success"] is True
        assert result["warning"] == "already_in_channel"
        
        # 验证请求URL
        args, kwargs = mock_request.call_args
        assert "conversations.join" in args[1]


@pytest.mark.unit
class TestSlackUsers:
    """Slack用户操作测试"""
    
    @pytest.fixture
    def adapter(self):
        return SlackAdapter()
    
    @pytest.fixture
    def valid_credentials(self):
        return {"access_token": "xoxp-test-token"}
    
    @pytest.mark.asyncio
    async def test_list_users(self, adapter, valid_credentials):
        """测试：列出用户"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "ok": True,
            "members": [
                {
                    "id": "U1234567890",
                    "name": "john.doe",
                    "real_name": "John Doe",
                    "is_bot": False,
                    "deleted": False
                },
                {
                    "id": "U0987654321",
                    "name": "jane.smith",
                    "real_name": "Jane Smith",
                    "is_bot": False,
                    "deleted": False
                }
            ],
            "response_metadata": {
                "next_cursor": ""
            }
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response):
            result = await adapter.call("list_users", {}, valid_credentials)
        
        assert result["success"] is True
        assert len(result["users"]) == 2
        assert result["total_count"] == 2
    
    @pytest.mark.asyncio
    async def test_get_user_info(self, adapter, valid_credentials):
        """测试：获取用户信息"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "ok": True,
            "user": {
                "id": "U1234567890",
                "name": "john.doe",
                "real_name": "John Doe",
                "profile": {
                    "email": "john@example.com",
                    "display_name": "John"
                }
            }
        }
        
        parameters = {"user": "U1234567890"}
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response) as mock_request:
            result = await adapter.call("get_user_info", parameters, valid_credentials)
        
        assert result["success"] is True
        assert result["user"]["id"] == "U1234567890"
        assert result["user"]["real_name"] == "John Doe"
        
        # 验证请求URL
        args, kwargs = mock_request.call_args
        url = args[1]
        assert "users.info" in url
        assert "user=U1234567890" in url
    
    @pytest.mark.asyncio
    async def test_get_user_info_missing_user(self, adapter, valid_credentials):
        """测试：获取用户信息缺少用户ID"""
        parameters = {}
        
        with pytest.raises(ValidationError, match="Missing required parameter: user"):
            await adapter.call("get_user_info", parameters, valid_credentials)


@pytest.mark.unit
class TestSlackSearch:
    """Slack搜索操作测试"""
    
    @pytest.fixture
    def adapter(self):
        return SlackAdapter()
    
    @pytest.fixture
    def valid_credentials(self):
        return {"access_token": "xoxp-test-token"}
    
    @pytest.mark.asyncio
    async def test_search_messages(self, adapter, valid_credentials):
        """测试：搜索消息"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "ok": True,
            "messages": {
                "total": 2,
                "page": 1,
                "per_page": 20,
                "matches": [
                    {
                        "type": "message",
                        "channel": {
                            "id": "C1234567890",
                            "name": "general"
                        },
                        "text": "This is a test message",
                        "ts": "1234567890.123456"
                    },
                    {
                        "type": "message",
                        "channel": {
                            "id": "C0987654321",
                            "name": "random"
                        },
                        "text": "Another test message",
                        "ts": "1234567891.123456"
                    }
                ]
            }
        }
        
        parameters = {
            "query": "test message",
            "sort": "timestamp",
            "sort_dir": "desc",
            "count": 20
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response) as mock_request:
            result = await adapter.call("search_messages", parameters, valid_credentials)
        
        assert result["success"] is True
        assert result["total"] == 2
        assert len(result["messages"]) == 2
        assert result["page"] == 1
        assert result["per_page"] == 20
        
        # 验证请求URL
        args, kwargs = mock_request.call_args
        url = args[1]
        assert "search.messages" in url
        assert "query=test+message" in url
        assert "sort=timestamp" in url
        assert "sort_dir=desc" in url
    
    @pytest.mark.asyncio
    async def test_search_messages_missing_query(self, adapter, valid_credentials):
        """测试：搜索消息缺少查询参数"""
        parameters = {"sort": "timestamp"}
        
        with pytest.raises(ValidationError, match="Missing required parameter: query"):
            await adapter.call("search_messages", parameters, valid_credentials)


@pytest.mark.unit
class TestSlackTeam:
    """Slack团队操作测试"""
    
    @pytest.fixture
    def adapter(self):
        return SlackAdapter()
    
    @pytest.fixture
    def valid_credentials(self):
        return {"bot_token": "xoxb-test-token"}
    
    @pytest.mark.asyncio
    async def test_get_team_info(self, adapter, valid_credentials):
        """测试：获取团队信息"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "ok": True,
            "team": {
                "id": "T1234567890",
                "name": "Test Team",
                "domain": "test-team",
                "email_domain": "example.com"
            }
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response):
            result = await adapter.call("get_team_info", {}, valid_credentials)
        
        assert result["success"] is True
        assert result["team"]["id"] == "T1234567890"
        assert result["team"]["name"] == "Test Team"
    
    @pytest.mark.asyncio
    async def test_get_auth_test(self, adapter, valid_credentials):
        """测试：认证测试"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "ok": True,
            "url": "https://test-team.slack.com/",
            "team": "Test Team",
            "user": "testbot",
            "team_id": "T1234567890",
            "user_id": "U1234567890",
            "bot_id": "B1234567890"
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response):
            result = await adapter.call("get_auth_test", {}, valid_credentials)
        
        assert result["success"] is True
        assert result["team_id"] == "T1234567890"
        assert result["user_id"] == "U1234567890"
        assert result["bot_id"] == "B1234567890"


@pytest.mark.unit
class TestSlackWebhook:
    """Slack Webhook操作测试"""
    
    @pytest.fixture
    def adapter(self):
        return SlackAdapter()
    
    @pytest.fixture
    def valid_webhook_credentials(self):
        return {
            "webhook_url": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
        }
    
    @pytest.mark.asyncio
    async def test_post_webhook(self, adapter, valid_webhook_credentials):
        """测试：发送Webhook消息"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.text = "ok"
        
        parameters = {
            "text": "Hello from webhook!",
            "username": "WebhookBot",
            "icon_emoji": ":ghost:",
            "channel": "#testing"
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response) as mock_request:
            result = await adapter.call("post_webhook", parameters, valid_webhook_credentials)
        
        assert result["success"] is True
        assert result["response"] == "ok"
        assert result["webhook_url"] == valid_webhook_credentials["webhook_url"]
        
        # 验证请求数据
        args, kwargs = mock_request.call_args
        assert args[1] == valid_webhook_credentials["webhook_url"]  # URL
        
        json_data = kwargs["json_data"]
        assert json_data["text"] == "Hello from webhook!"
        assert json_data["username"] == "WebhookBot"
        assert json_data["icon_emoji"] == ":ghost:"
        assert json_data["channel"] == "#testing"
        
        # 验证Webhook请求不包含Authorization头部
        headers = kwargs["headers"]
        assert "Authorization" not in headers
    
    @pytest.mark.asyncio
    async def test_post_webhook_missing_url(self, adapter):
        """测试：Webhook缺少URL"""
        invalid_credentials = {"access_token": "some_token"}
        parameters = {"text": "Hello"}
        
        with pytest.raises(ValidationError, match="Missing webhook_url in credentials"):
            await adapter.call("post_webhook", parameters, invalid_credentials)
    
    @pytest.mark.asyncio
    async def test_post_webhook_missing_text(self, adapter, valid_webhook_credentials):
        """测试：Webhook缺少文本"""
        parameters = {"username": "Bot"}
        
        with pytest.raises(ValidationError, match="Missing required parameter: text"):
            await adapter.call("post_webhook", parameters, valid_webhook_credentials)


@pytest.mark.integration
class TestSlackIntegration:
    """Slack适配器集成测试"""
    
    @pytest.mark.asyncio
    async def test_connection_test_oauth_success(self):
        """测试：OAuth连接测试成功"""
        adapter = SlackAdapter()
        valid_credentials = {"access_token": "xoxp-valid-token"}
        
        # Mock成功的API响应
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "ok": True,
            "url": "https://test-team.slack.com/",
            "team": "Test Team",
            "user": "testuser",
            "team_id": "T1234567890",
            "user_id": "U1234567890"
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response):
            result = await adapter.test_connection(valid_credentials)
        
        assert result["success"] is True
        assert result["provider"] == "slack"
        assert "slack_access" in result["details"]
        assert result["details"]["team"] == "Test Team"
        assert result["details"]["user"] == "testuser"
    
    @pytest.mark.asyncio
    async def test_connection_test_webhook_success(self):
        """测试：Webhook连接测试成功"""
        adapter = SlackAdapter()
        valid_credentials = {
            "webhook_url": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
        }
        
        result = await adapter.test_connection(valid_credentials)
        
        assert result["success"] is True
        assert result["provider"] == "slack"
        assert "webhook_access" in result["details"]
        assert result["details"]["webhook_url"] == valid_credentials["webhook_url"]
    
    @pytest.mark.asyncio
    async def test_connection_test_invalid_webhook(self):
        """测试：无效Webhook URL"""
        adapter = SlackAdapter()
        invalid_credentials = {
            "webhook_url": "https://invalid-webhook-url.com/hook"
        }
        
        result = await adapter.test_connection(invalid_credentials)
        
        assert result["success"] is False
        assert "Invalid webhook URL format" in result["error"]
    
    @pytest.mark.asyncio
    async def test_connection_test_failure(self):
        """测试：连接测试失败"""
        adapter = SlackAdapter()
        invalid_credentials = {"access_token": "xoxp-invalid-token"}
        
        # Mock失败的API响应
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "ok": False,
            "error": "invalid_auth"
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response):
            result = await adapter.test_connection(invalid_credentials)
        
        assert result["success"] is False
        assert "invalid_auth" in result["error"]
    
    @pytest.mark.asyncio
    async def test_context_manager_usage(self):
        """测试：上下文管理器使用"""
        valid_credentials = {"bot_token": "xoxb-test-token"}
        
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "ok": True,
            "channels": []
        }
        
        async with SlackAdapter() as adapter:
            with patch.object(adapter, 'make_http_request', return_value=mock_response):
                result = await adapter.call("list_channels", {}, valid_credentials)
                assert result["success"] is True
        
        # 验证HTTP客户端已关闭
        assert adapter._client is None