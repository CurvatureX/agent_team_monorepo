"""
Google Calendar API适配器测试
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone
import json

from workflow_engine.services.api_adapters.google_calendar import GoogleCalendarAdapter
from workflow_engine.services.api_adapters.base import (
    ValidationError, 
    AuthenticationError, 
    TemporaryError,
    OAuth2Config
)


@pytest.mark.unit
class TestGoogleCalendarAdapter:
    """Google Calendar适配器单元测试"""
    
    @pytest.fixture
    def adapter(self):
        """创建Google Calendar适配器实例"""
        return GoogleCalendarAdapter()
    
    @pytest.fixture
    def valid_credentials(self):
        """有效的Google凭证"""
        return {
            "access_token": "ya29.test_google_access_token_12345"
        }
    
    @pytest.fixture
    def sample_event_data(self):
        """示例事件数据"""
        return {
            "summary": "Test Meeting",
            "description": "A test meeting for calendar integration",
            "location": "San Francisco, CA",
            "start_datetime": "2024-12-20T10:00:00Z",
            "end_datetime": "2024-12-20T11:00:00Z",
            "attendees": ["attendee1@example.com", "attendee2@example.com"]
        }
    
    def test_adapter_initialization(self, adapter):
        """测试：适配器初始化"""
        assert adapter.provider_name == "google_calendar"
        assert adapter.BASE_URL == "https://www.googleapis.com/calendar/v3"
        assert "list_events" in adapter.OPERATIONS
        assert "create_event" in adapter.OPERATIONS
    
    def test_oauth2_config(self, adapter):
        """测试：OAuth2配置"""
        config = adapter.get_oauth2_config()
        
        assert isinstance(config, OAuth2Config)
        assert config.auth_url == "https://accounts.google.com/o/oauth2/auth"
        assert config.token_url == "https://oauth2.googleapis.com/token"
        assert "https://www.googleapis.com/auth/calendar" in config.scopes
    
    def test_validate_credentials_valid(self, adapter, valid_credentials):
        """测试：有效凭证验证"""
        assert adapter.validate_credentials(valid_credentials) is True
    
    def test_validate_credentials_invalid(self, adapter):
        """测试：无效凭证验证"""
        # 缺少access_token
        invalid_creds = {"refresh_token": "refresh_123"}
        assert adapter.validate_credentials(invalid_creds) is False
        
        # 空access_token
        empty_creds = {"access_token": ""}
        assert adapter.validate_credentials(empty_creds) is False
    
    def test_get_supported_operations(self, adapter):
        """测试：获取支持的操作"""
        operations = adapter.get_supported_operations()
        
        expected_operations = [
            "list_events", "create_event", "update_event", "delete_event",
            "get_event", "list_calendars", "create_calendar", "get_calendar",
            "search_events", "quick_add", "watch_events", "stop_watching"
        ]
        
        for op in expected_operations:
            assert op in operations
    
    def test_get_operation_description(self, adapter):
        """测试：获取操作描述"""
        description = adapter.get_operation_description("list_events")
        assert description == "列出日历事件"
        
        # 不存在的操作
        assert adapter.get_operation_description("nonexistent") is None
    
    @pytest.mark.asyncio
    async def test_call_unsupported_operation(self, adapter, valid_credentials):
        """测试：调用不支持的操作"""
        with pytest.raises(ValidationError, match="Unsupported operation"):
            await adapter.call("unsupported_op", {}, valid_credentials)
    
    @pytest.mark.asyncio
    async def test_call_invalid_credentials(self, adapter):
        """测试：使用无效凭证调用"""
        invalid_creds = {"invalid": "credentials"}
        
        with pytest.raises(ValidationError, match="Invalid credentials"):
            await adapter.call("list_events", {}, invalid_creds)


@pytest.mark.unit
class TestGoogleCalendarEvents:
    """Google Calendar事件操作测试"""
    
    @pytest.fixture
    def adapter(self):
        return GoogleCalendarAdapter()
    
    @pytest.fixture
    def valid_credentials(self):
        return {"access_token": "ya29.test_token"}
    
    @pytest.fixture
    def mock_http_response(self):
        """Mock HTTP响应"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.status_code = 200
        return mock_response
    
    @pytest.mark.asyncio
    async def test_list_events_basic(self, adapter, valid_credentials, mock_http_response):
        """测试：基本的事件列表"""
        # Mock响应数据
        mock_http_response.json.return_value = {
            "items": [
                {
                    "id": "event1",
                    "summary": "Test Event 1",
                    "start": {"dateTime": "2024-12-20T10:00:00Z"},
                    "end": {"dateTime": "2024-12-20T11:00:00Z"}
                },
                {
                    "id": "event2", 
                    "summary": "Test Event 2",
                    "start": {"dateTime": "2024-12-20T14:00:00Z"},
                    "end": {"dateTime": "2024-12-20T15:00:00Z"}
                }
            ],
            "nextPageToken": "next_page_123",
            "summary": "Test Calendar"
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_http_response):
            result = await adapter.call("list_events", {}, valid_credentials)
        
        assert result["success"] is True
        assert len(result["events"]) == 2
        assert result["next_page_token"] == "next_page_123"
        assert result["total_count"] == 2
    
    @pytest.mark.asyncio
    async def test_list_events_with_filters(self, adapter, valid_credentials, mock_http_response):
        """测试：带过滤条件的事件列表"""
        mock_http_response.json.return_value = {"items": []}
        
        parameters = {
            "calendar_id": "test@example.com",
            "time_min": "2024-12-20T00:00:00Z",
            "time_max": "2024-12-20T23:59:59Z",
            "max_results": 50,
            "q": "meeting"
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_http_response) as mock_request:
            await adapter.call("list_events", parameters, valid_credentials)
            
            # 验证请求URL包含正确的查询参数
            args, kwargs = mock_request.call_args
            url = args[1]  # 第二个参数是URL
            
            assert "calendars/test@example.com/events" in url
            assert "timeMin=" in url
            assert "timeMax=" in url
            assert "maxResults=50" in url
            assert "q=meeting" in url
    
    @pytest.mark.asyncio
    async def test_create_event_basic(self, adapter, valid_credentials, mock_http_response):
        """测试：创建基本事件"""
        mock_http_response.json.return_value = {
            "id": "created_event_123",
            "summary": "New Meeting",
            "htmlLink": "https://calendar.google.com/event?eid=xxx"
        }
        
        parameters = {
            "summary": "New Meeting",
            "description": "A new meeting",
            "start_datetime": "2024-12-20T10:00:00Z",
            "end_datetime": "2024-12-20T11:00:00Z"
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_http_response) as mock_request:
            result = await adapter.call("create_event", parameters, valid_credentials)
        
        assert result["success"] is True
        assert result["event_id"] == "created_event_123"
        assert result["html_link"] == "https://calendar.google.com/event?eid=xxx"
        
        # 验证请求数据
        args, kwargs = mock_request.call_args
        assert kwargs["json_data"]["summary"] == "New Meeting"
        assert "start" in kwargs["json_data"]
        assert "end" in kwargs["json_data"]
    
    @pytest.mark.asyncio
    async def test_create_event_missing_summary(self, adapter, valid_credentials):
        """测试：创建事件缺少必需参数"""
        parameters = {
            "description": "Missing summary",
            "start_datetime": "2024-12-20T10:00:00Z",
            "end_datetime": "2024-12-20T11:00:00Z"
        }
        
        with pytest.raises(ValidationError, match="Missing required parameter: summary"):
            await adapter.call("create_event", parameters, valid_credentials)
    
    @pytest.mark.asyncio
    async def test_create_event_missing_time(self, adapter, valid_credentials):
        """测试：创建事件缺少时间参数"""
        parameters = {
            "summary": "Meeting without time"
        }
        
        with pytest.raises(ValidationError, match="Missing required time parameters"):
            await adapter.call("create_event", parameters, valid_credentials)
    
    @pytest.mark.asyncio
    async def test_create_event_with_attendees(self, adapter, valid_credentials, mock_http_response):
        """测试：创建带参与者的事件"""
        mock_http_response.json.return_value = {"id": "event_with_attendees"}
        
        parameters = {
            "summary": "Team Meeting",
            "start_datetime": "2024-12-20T10:00:00Z",
            "end_datetime": "2024-12-20T11:00:00Z",
            "attendees": ["user1@example.com", "user2@example.com"]
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_http_response) as mock_request:
            await adapter.call("create_event", parameters, valid_credentials)
        
        # 验证参与者格式
        json_data = mock_request.call_args[1]["json_data"]
        assert "attendees" in json_data
        assert len(json_data["attendees"]) == 2
        assert json_data["attendees"][0]["email"] == "user1@example.com"
    
    @pytest.mark.asyncio
    async def test_update_event(self, adapter, valid_credentials, mock_http_response):
        """测试：更新事件"""
        mock_http_response.json.return_value = {
            "id": "updated_event_123",
            "summary": "Updated Meeting"
        }
        
        parameters = {
            "event_id": "event_123",
            "summary": "Updated Meeting",
            "description": "Updated description"
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_http_response) as mock_request:
            result = await adapter.call("update_event", parameters, valid_credentials)
        
        assert result["success"] is True
        assert result["event_id"] == "updated_event_123"
        assert "summary" in result["updated_fields"]
        assert "description" in result["updated_fields"]
        
        # 验证请求方法和URL
        args, kwargs = mock_request.call_args
        assert args[0] == "PUT"  # HTTP方法
        assert "events/event_123" in args[1]  # URL
    
    @pytest.mark.asyncio
    async def test_update_event_missing_id(self, adapter, valid_credentials):
        """测试：更新事件缺少事件ID"""
        parameters = {"summary": "Updated Meeting"}
        
        with pytest.raises(ValidationError, match="Missing required parameter: event_id"):
            await adapter.call("update_event", parameters, valid_credentials)
    
    @pytest.mark.asyncio
    async def test_update_event_no_fields(self, adapter, valid_credentials):
        """测试：更新事件没有指定要更新的字段"""
        parameters = {"event_id": "event_123"}
        
        with pytest.raises(ValidationError, match="No fields to update specified"):
            await adapter.call("update_event", parameters, valid_credentials)
    
    @pytest.mark.asyncio
    async def test_delete_event(self, adapter, valid_credentials):
        """测试：删除事件"""
        mock_response = Mock()
        mock_response.status_code = 204  # 成功删除
        
        parameters = {"event_id": "event_to_delete"}
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response) as mock_request:
            result = await adapter.call("delete_event", parameters, valid_credentials)
        
        assert result["success"] is True
        assert result["event_id"] == "event_to_delete"
        assert "deleted successfully" in result["message"]
        
        # 验证DELETE请求
        args, kwargs = mock_request.call_args
        assert args[0] == "DELETE"
    
    @pytest.mark.asyncio
    async def test_delete_event_already_deleted(self, adapter, valid_credentials):
        """测试：删除已删除的事件"""
        mock_response = Mock()
        mock_response.status_code = 410  # 已删除
        
        parameters = {"event_id": "already_deleted_event"}
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response):
            result = await adapter.call("delete_event", parameters, valid_credentials)
        
        assert result["success"] is True
        assert "already deleted" in result["message"]
    
    @pytest.mark.asyncio
    async def test_get_event(self, adapter, valid_credentials, mock_http_response):
        """测试：获取单个事件"""
        mock_http_response.json.return_value = {
            "id": "specific_event",
            "summary": "Specific Event",
            "start": {"dateTime": "2024-12-20T10:00:00Z"},
            "end": {"dateTime": "2024-12-20T11:00:00Z"}
        }
        
        parameters = {"event_id": "specific_event"}
        
        with patch.object(adapter, 'make_http_request', return_value=mock_http_response):
            result = await adapter.call("get_event", parameters, valid_credentials)
        
        assert result["success"] is True
        assert result["event"]["id"] == "specific_event"
        assert result["event"]["summary"] == "Specific Event"


@pytest.mark.unit
class TestGoogleCalendarCalendars:
    """Google Calendar日历操作测试"""
    
    @pytest.fixture
    def adapter(self):
        return GoogleCalendarAdapter()
    
    @pytest.fixture
    def valid_credentials(self):
        return {"access_token": "ya29.test_token"}
    
    @pytest.mark.asyncio
    async def test_list_calendars(self, adapter, valid_credentials):
        """测试：列出日历"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "items": [
                {
                    "id": "primary",
                    "summary": "Primary Calendar",
                    "accessRole": "owner"
                },
                {
                    "id": "work@example.com",
                    "summary": "Work Calendar", 
                    "accessRole": "writer"
                }
            ]
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response):
            result = await adapter.call("list_calendars", {}, valid_credentials)
        
        assert result["success"] is True
        assert len(result["calendars"]) == 2
        assert result["total_count"] == 2
    
    @pytest.mark.asyncio
    async def test_create_calendar(self, adapter, valid_credentials):
        """测试：创建日历"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "id": "new_calendar_123",
            "summary": "New Work Calendar",
            "timeZone": "America/Los_Angeles"
        }
        
        parameters = {
            "summary": "New Work Calendar",
            "description": "A calendar for work events",
            "time_zone": "America/Los_Angeles"
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response) as mock_request:
            result = await adapter.call("create_calendar", parameters, valid_credentials)
        
        assert result["success"] is True
        assert result["calendar_id"] == "new_calendar_123"
        
        # 验证请求数据
        json_data = mock_request.call_args[1]["json_data"]
        assert json_data["summary"] == "New Work Calendar"
        assert json_data["timeZone"] == "America/Los_Angeles"
    
    @pytest.mark.asyncio
    async def test_create_calendar_missing_summary(self, adapter, valid_credentials):
        """测试：创建日历缺少必需参数"""
        parameters = {"description": "Calendar without summary"}
        
        with pytest.raises(ValidationError, match="Missing required parameter: summary"):
            await adapter.call("create_calendar", parameters, valid_credentials)
    
    @pytest.mark.asyncio
    async def test_get_calendar(self, adapter, valid_credentials):
        """测试：获取日历详情"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "id": "primary",
            "summary": "Primary Calendar",
            "timeZone": "America/New_York",
            "description": "Main calendar"
        }
        
        parameters = {"calendar_id": "primary"}
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response):
            result = await adapter.call("get_calendar", parameters, valid_credentials)
        
        assert result["success"] is True
        assert result["calendar"]["id"] == "primary"
        assert result["calendar"]["summary"] == "Primary Calendar"


@pytest.mark.unit
class TestGoogleCalendarAdvanced:
    """Google Calendar高级功能测试"""
    
    @pytest.fixture
    def adapter(self):
        return GoogleCalendarAdapter()
    
    @pytest.fixture
    def valid_credentials(self):
        return {"access_token": "ya29.test_token"}
    
    @pytest.mark.asyncio
    async def test_search_events(self, adapter, valid_credentials):
        """测试：搜索事件"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "items": [
                {"id": "search_result_1", "summary": "Meeting with search term"}
            ]
        }
        
        parameters = {
            "q": "meeting",
            "calendar_id": "primary"
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response):
            result = await adapter.call("search_events", parameters, valid_credentials)
        
        assert result["success"] is True
        assert len(result["events"]) == 1
    
    @pytest.mark.asyncio
    async def test_search_events_missing_query(self, adapter, valid_credentials):
        """测试：搜索事件缺少查询参数"""
        parameters = {"calendar_id": "primary"}
        
        with pytest.raises(ValidationError, match="Missing required parameter: q"):
            await adapter.call("search_events", parameters, valid_credentials)
    
    @pytest.mark.asyncio
    async def test_quick_add(self, adapter, valid_credentials):
        """测试：快速添加事件"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "id": "quick_added_event",
            "summary": "Quick meeting tomorrow at 2pm",
            "start": {"dateTime": "2024-12-21T14:00:00Z"}
        }
        
        parameters = {
            "text": "Quick meeting tomorrow at 2pm",
            "send_notifications": True
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response) as mock_request:
            result = await adapter.call("quick_add", parameters, valid_credentials)
        
        assert result["success"] is True
        assert result["event_id"] == "quick_added_event"
        assert result["parsed_text"] == "Quick meeting tomorrow at 2pm"
        
        # 验证URL包含查询参数
        url = mock_request.call_args[0][1]
        assert "text=" in url
        assert "sendNotifications=True" in url
    
    @pytest.mark.asyncio
    async def test_watch_events(self, adapter, valid_credentials):
        """测试：监听事件变化"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "id": "watch_channel_123",
            "resourceId": "resource_456",
            "expiration": "1640995200000"
        }
        
        parameters = {
            "webhook_url": "https://myapp.com/webhook",
            "channel_id": "custom_channel_id"
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response) as mock_request:
            result = await adapter.call("watch_events", parameters, valid_credentials)
        
        assert result["success"] is True
        assert result["channel_id"] == "watch_channel_123"
        assert result["resource_id"] == "resource_456"
        
        # 验证请求数据
        json_data = mock_request.call_args[1]["json_data"]
        assert json_data["address"] == "https://myapp.com/webhook"
        assert json_data["type"] == "web_hook"
    
    @pytest.mark.asyncio
    async def test_stop_watching(self, adapter, valid_credentials):
        """测试：停止监听"""
        mock_response = Mock()
        mock_response.status_code = 204  # 成功停止
        
        parameters = {
            "channel_id": "channel_to_stop",
            "resource_id": "resource_to_stop"
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response) as mock_request:
            result = await adapter.call("stop_watching", parameters, valid_credentials)
        
        assert result["success"] is True
        assert "stopped successfully" in result["message"]
        
        # 验证请求数据
        json_data = mock_request.call_args[1]["json_data"]
        assert json_data["id"] == "channel_to_stop"
        assert json_data["resourceId"] == "resource_to_stop"


@pytest.mark.unit
class TestGoogleCalendarUtilities:
    """Google Calendar工具函数测试"""
    
    @pytest.fixture
    def adapter(self):
        return GoogleCalendarAdapter()
    
    def test_format_datetime_string(self, adapter):
        """测试：格式化字符串日期时间"""
        dt_string = "2024-12-20T10:00:00Z"
        result = adapter._format_datetime(dt_string)
        assert result == dt_string
    
    def test_format_datetime_object(self, adapter):
        """测试：格式化datetime对象"""
        dt = datetime(2024, 12, 20, 10, 0, 0, tzinfo=timezone.utc)
        result = adapter._format_datetime(dt)
        assert result == "2024-12-20T10:00:00+00:00"
    
    def test_format_datetime_naive(self, adapter):
        """测试：格式化无时区的datetime对象"""
        dt = datetime(2024, 12, 20, 10, 0, 0)
        result = adapter._format_datetime(dt)
        assert result == "2024-12-20T10:00:00+00:00"
    
    def test_format_event_time_dict(self, adapter):
        """测试：格式化事件时间字典"""
        time_dict = {"dateTime": "2024-12-20T10:00:00Z"}
        result = adapter._format_event_time(time_dict)
        assert result == time_dict
    
    def test_format_event_time_string_datetime(self, adapter):
        """测试：格式化事件时间字符串（日期时间）"""
        time_string = "2024-12-20T10:00:00Z"
        result = adapter._format_event_time(time_string)
        assert result == {"dateTime": time_string}
    
    def test_format_event_time_string_date(self, adapter):
        """测试：格式化事件时间字符串（日期）"""
        date_string = "2024-12-20"
        result = adapter._format_event_time(date_string)
        assert result == {"date": date_string}
    
    def test_format_event_time_datetime_object(self, adapter):
        """测试：格式化事件时间datetime对象"""
        dt = datetime(2024, 12, 20, 10, 0, 0, tzinfo=timezone.utc)
        result = adapter._format_event_time(dt)
        assert "dateTime" in result
        assert result["dateTime"] == "2024-12-20T10:00:00+00:00"


@pytest.mark.integration
class TestGoogleCalendarIntegration:
    """Google Calendar适配器集成测试"""
    
    @pytest.mark.asyncio
    async def test_connection_test_success(self):
        """测试：连接测试成功"""
        adapter = GoogleCalendarAdapter()
        valid_credentials = {"access_token": "valid_token"}
        
        # Mock成功的API响应
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "id": "user@example.com",
            "summary": "User's Calendar"
        }
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response):
            result = await adapter.test_connection(valid_credentials)
        
        assert result["success"] is True
        assert result["provider"] == "google_calendar"
        assert "calendar_access" in result["details"]
    
    @pytest.mark.asyncio
    async def test_connection_test_failure(self):
        """测试：连接测试失败"""
        adapter = GoogleCalendarAdapter()
        invalid_credentials = {"access_token": "invalid_token"}
        
        # Mock失败的API响应
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 401
        
        with patch.object(adapter, 'make_http_request', return_value=mock_response):
            with patch.object(adapter, '_handle_http_error', side_effect=AuthenticationError("Invalid token")):
                result = await adapter.test_connection(invalid_credentials)
        
        assert result["success"] is False
        assert "error" in result
    
    @pytest.mark.asyncio 
    async def test_context_manager_usage(self):
        """测试：上下文管理器使用"""
        valid_credentials = {"access_token": "test_token"}
        
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {"items": []}
        
        async with GoogleCalendarAdapter() as adapter:
            with patch.object(adapter, 'make_http_request', return_value=mock_response):
                result = await adapter.call("list_events", {}, valid_credentials)
                assert result["success"] is True
        
        # 验证HTTP客户端已关闭
        assert adapter._client is None