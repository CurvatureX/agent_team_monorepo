"""
Google Calendar API适配器
实现Google Calendar API的统一调用接口
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from urllib.parse import urlencode
import json

from .base import APIAdapter, OAuth2Config, PermanentError, TemporaryError, ValidationError, register_adapter

logger = logging.getLogger(__name__)


@register_adapter("google_calendar")
class GoogleCalendarAdapter(APIAdapter):
    """Google Calendar API适配器
    
    支持的操作:
    - list_events: 列出日历事件
    - create_event: 创建新事件
    - update_event: 更新事件
    - delete_event: 删除事件
    - get_event: 获取单个事件详情
    - list_calendars: 列出用户的日历
    - create_calendar: 创建新日历
    - get_calendar: 获取日历详情
    - search_events: 搜索事件
    """
    
    # Google Calendar API基础URL
    BASE_URL = "https://www.googleapis.com/calendar/v3"
    
    # 支持的操作定义
    OPERATIONS = {
        "list_events": "列出日历事件",
        "create_event": "创建新的日历事件",
        "update_event": "更新现有事件",
        "delete_event": "删除事件",
        "get_event": "获取单个事件详情",
        "list_calendars": "列出用户的所有日历",
        "create_calendar": "创建新的日历",
        "get_calendar": "获取日历详情",
        "search_events": "在日历中搜索事件",
        "quick_add": "快速添加事件（自然语言）",
        "watch_events": "监听事件变化（Webhook）",
        "stop_watching": "停止监听事件变化"
    }
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.provider_name = "google_calendar"
    
    def get_oauth2_config(self) -> OAuth2Config:
        """获取Google Calendar OAuth2配置"""
        return OAuth2Config(
            client_id="",  # 将从环境变量或配置中加载
            client_secret="",  # 将从环境变量或配置中加载
            auth_url="https://accounts.google.com/o/oauth2/auth",
            token_url="https://oauth2.googleapis.com/token",
            revoke_url="https://oauth2.googleapis.com/revoke",
            scopes=[
                "https://www.googleapis.com/auth/calendar",
                "https://www.googleapis.com/auth/calendar.events"
            ],
            redirect_uri="http://localhost:8000/auth/google/callback"
        )
    
    def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """验证Google Calendar凭证"""
        required_fields = ["access_token"]
        return all(field in credentials and credentials[field] for field in required_fields)
    
    async def call(self, operation: str, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """统一的API调用接口"""
        if not self.validate_credentials(credentials):
            raise ValidationError("Invalid credentials: missing access_token")
        
        if operation not in self.OPERATIONS:
            raise ValidationError(f"Unsupported operation: {operation}")
        
        # 根据操作类型分发到具体的处理方法
        handler_mapping = {
            "list_events": self._list_events,
            "create_event": self._create_event,
            "update_event": self._update_event,
            "delete_event": self._delete_event,
            "get_event": self._get_event,
            "list_calendars": self._list_calendars,
            "create_calendar": self._create_calendar,
            "get_calendar": self._get_calendar,
            "search_events": self._search_events,
            "quick_add": self._quick_add,
            "watch_events": self._watch_events,
            "stop_watching": self._stop_watching
        }
        
        handler = handler_mapping[operation]
        return await handler(parameters, credentials)
    
    async def _list_events(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """列出日历事件"""
        calendar_id = parameters.get("calendar_id", "primary")
        
        # 构建查询参数
        query_params = {}
        
        # 时间范围过滤
        if "time_min" in parameters:
            query_params["timeMin"] = self._format_datetime(parameters["time_min"])
        if "time_max" in parameters:
            query_params["timeMax"] = self._format_datetime(parameters["time_max"])
        
        # 其他过滤参数
        if "max_results" in parameters:
            query_params["maxResults"] = min(int(parameters["max_results"]), 2500)
        if "single_events" in parameters:
            query_params["singleEvents"] = bool(parameters["single_events"])
        if "order_by" in parameters:
            query_params["orderBy"] = parameters["order_by"]
        if "q" in parameters:
            query_params["q"] = parameters["q"]
        if "show_deleted" in parameters:
            query_params["showDeleted"] = bool(parameters["show_deleted"])
        
        url = f"{self.BASE_URL}/calendars/{calendar_id}/events"
        if query_params:
            url += f"?{urlencode(query_params)}"
        
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        data = response.json()
        
        return {
            "success": True,
            "events": data.get("items", []),
            "next_page_token": data.get("nextPageToken"),
            "next_sync_token": data.get("nextSyncToken"),
            "summary": data.get("summary"),
            "total_count": len(data.get("items", []))
        }
    
    async def _create_event(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """创建新的日历事件"""
        calendar_id = parameters.get("calendar_id", "primary")
        
        # 验证必需参数
        if "summary" not in parameters:
            raise ValidationError("Missing required parameter: summary")
        
        # 构建事件数据
        event_data = {
            "summary": parameters["summary"]
        }
        
        # 可选参数
        if "description" in parameters:
            event_data["description"] = parameters["description"]
        if "location" in parameters:
            event_data["location"] = parameters["location"]
        
        # 时间设置
        if "start" in parameters and "end" in parameters:
            event_data["start"] = self._format_event_time(parameters["start"])
            event_data["end"] = self._format_event_time(parameters["end"])
        elif "start_datetime" in parameters and "end_datetime" in parameters:
            event_data["start"] = {"dateTime": self._format_datetime(parameters["start_datetime"])}
            event_data["end"] = {"dateTime": self._format_datetime(parameters["end_datetime"])}
        elif "date" in parameters:
            # 全天事件
            event_data["start"] = {"date": parameters["date"]}
            event_data["end"] = {"date": parameters["date"]}
        else:
            raise ValidationError("Missing required time parameters")
        
        # 参与者
        if "attendees" in parameters:
            event_data["attendees"] = [
                {"email": email} for email in parameters["attendees"]
            ]
        
        # 提醒设置
        if "reminders" in parameters:
            event_data["reminders"] = parameters["reminders"]
        
        # 重复规则
        if "recurrence" in parameters:
            event_data["recurrence"] = parameters["recurrence"]
        
        url = f"{self.BASE_URL}/calendars/{calendar_id}/events"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request(
            "POST", url, headers=headers, json_data=event_data
        )
        
        if not response.is_success:
            self._handle_http_error(response)
        
        event = response.json()
        
        return {
            "success": True,
            "event": event,
            "event_id": event.get("id"),
            "html_link": event.get("htmlLink")
        }
    
    async def _update_event(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """更新现有事件"""
        calendar_id = parameters.get("calendar_id", "primary")
        event_id = parameters.get("event_id")
        
        if not event_id:
            raise ValidationError("Missing required parameter: event_id")
        
        # 构建更新数据
        update_data = {}
        
        # 可更新的字段
        updateable_fields = [
            "summary", "description", "location", "start", "end",
            "attendees", "reminders", "recurrence", "transparency",
            "visibility", "status"
        ]
        
        for field in updateable_fields:
            if field in parameters:
                if field in ["start", "end"]:
                    update_data[field] = self._format_event_time(parameters[field])
                elif field == "attendees":
                    update_data[field] = [
                        {"email": email} for email in parameters[field]
                    ]
                else:
                    update_data[field] = parameters[field]
        
        if not update_data:
            raise ValidationError("No fields to update specified")
        
        url = f"{self.BASE_URL}/calendars/{calendar_id}/events/{event_id}"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request(
            "PUT", url, headers=headers, json_data=update_data
        )
        
        if not response.is_success:
            self._handle_http_error(response)
        
        event = response.json()
        
        return {
            "success": True,
            "event": event,
            "event_id": event.get("id"),
            "updated_fields": list(update_data.keys())
        }
    
    async def _delete_event(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """删除事件"""
        calendar_id = parameters.get("calendar_id", "primary")
        event_id = parameters.get("event_id")
        
        if not event_id:
            raise ValidationError("Missing required parameter: event_id")
        
        url = f"{self.BASE_URL}/calendars/{calendar_id}/events/{event_id}"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request("DELETE", url, headers=headers)
        
        if response.status_code == 204:
            # 成功删除
            return {
                "success": True,
                "message": "Event deleted successfully",
                "event_id": event_id
            }
        elif response.status_code == 410:
            # 事件已被删除
            return {
                "success": True,
                "message": "Event was already deleted",
                "event_id": event_id
            }
        else:
            self._handle_http_error(response)
    
    async def _get_event(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """获取单个事件详情"""
        calendar_id = parameters.get("calendar_id", "primary")
        event_id = parameters.get("event_id")
        
        if not event_id:
            raise ValidationError("Missing required parameter: event_id")
        
        url = f"{self.BASE_URL}/calendars/{calendar_id}/events/{event_id}"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        event = response.json()
        
        return {
            "success": True,
            "event": event
        }
    
    async def _list_calendars(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """列出用户的所有日历"""
        query_params = {}
        
        if "max_results" in parameters:
            query_params["maxResults"] = min(int(parameters["max_results"]), 250)
        if "min_access_role" in parameters:
            query_params["minAccessRole"] = parameters["min_access_role"]
        
        url = f"{self.BASE_URL}/users/me/calendarList"
        if query_params:
            url += f"?{urlencode(query_params)}"
        
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        data = response.json()
        
        return {
            "success": True,
            "calendars": data.get("items", []),
            "next_page_token": data.get("nextPageToken"),
            "total_count": len(data.get("items", []))
        }
    
    async def _create_calendar(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """创建新的日历"""
        if "summary" not in parameters:
            raise ValidationError("Missing required parameter: summary")
        
        calendar_data = {
            "summary": parameters["summary"]
        }
        
        # 可选参数
        if "description" in parameters:
            calendar_data["description"] = parameters["description"]
        if "time_zone" in parameters:
            calendar_data["timeZone"] = parameters["time_zone"]
        if "location" in parameters:
            calendar_data["location"] = parameters["location"]
        
        url = f"{self.BASE_URL}/calendars"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request(
            "POST", url, headers=headers, json_data=calendar_data
        )
        
        if not response.is_success:
            self._handle_http_error(response)
        
        calendar = response.json()
        
        return {
            "success": True,
            "calendar": calendar,
            "calendar_id": calendar.get("id")
        }
    
    async def _get_calendar(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """获取日历详情"""
        calendar_id = parameters.get("calendar_id", "primary")
        
        url = f"{self.BASE_URL}/calendars/{calendar_id}"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        calendar = response.json()
        
        return {
            "success": True,
            "calendar": calendar
        }
    
    async def _search_events(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """搜索事件"""
        if "q" not in parameters:
            raise ValidationError("Missing required parameter: q (search query)")
        
        # 使用list_events的搜索功能
        search_params = {
            "q": parameters["q"],
            "single_events": True,
            "order_by": "startTime"
        }
        
        # 合并其他参数
        search_params.update({k: v for k, v in parameters.items() if k != "q"})
        
        return await self._list_events(search_params, credentials)
    
    async def _quick_add(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """快速添加事件（自然语言）"""
        calendar_id = parameters.get("calendar_id", "primary")
        text = parameters.get("text")
        
        if not text:
            raise ValidationError("Missing required parameter: text")
        
        query_params = {"text": text}
        if "send_notifications" in parameters:
            query_params["sendNotifications"] = bool(parameters["send_notifications"])
        
        url = f"{self.BASE_URL}/calendars/{calendar_id}/events/quickAdd?{urlencode(query_params)}"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request("POST", url, headers=headers)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        event = response.json()
        
        return {
            "success": True,
            "event": event,
            "event_id": event.get("id"),
            "parsed_text": text
        }
    
    async def _watch_events(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """监听事件变化（设置Webhook）"""
        calendar_id = parameters.get("calendar_id", "primary")
        webhook_url = parameters.get("webhook_url")
        
        if not webhook_url:
            raise ValidationError("Missing required parameter: webhook_url")
        
        watch_data = {
            "id": parameters.get("channel_id", f"calendar_watch_{int(datetime.now().timestamp())}"),
            "type": "web_hook",
            "address": webhook_url
        }
        
        # 可选参数
        if "token" in parameters:
            watch_data["token"] = parameters["token"]
        if "expiration" in parameters:
            watch_data["expiration"] = parameters["expiration"]
        
        url = f"{self.BASE_URL}/calendars/{calendar_id}/events/watch"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request(
            "POST", url, headers=headers, json_data=watch_data
        )
        
        if not response.is_success:
            self._handle_http_error(response)
        
        watch_response = response.json()
        
        return {
            "success": True,
            "channel": watch_response,
            "channel_id": watch_response.get("id"),
            "resource_id": watch_response.get("resourceId")
        }
    
    async def _stop_watching(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """停止监听事件变化"""
        channel_id = parameters.get("channel_id")
        resource_id = parameters.get("resource_id")
        
        if not channel_id or not resource_id:
            raise ValidationError("Missing required parameters: channel_id and resource_id")
        
        stop_data = {
            "id": channel_id,
            "resourceId": resource_id
        }
        
        url = f"{self.BASE_URL}/channels/stop"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request(
            "POST", url, headers=headers, json_data=stop_data
        )
        
        if response.status_code == 204:
            return {
                "success": True,
                "message": "Channel stopped successfully",
                "channel_id": channel_id
            }
        else:
            self._handle_http_error(response)
    
    async def _default_connection_test(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Google Calendar特定的连接测试"""
        # 尝试获取主日历信息
        try:
            url = f"{self.BASE_URL}/calendars/primary"
            headers = self._prepare_headers(credentials)
            
            response = await self.make_http_request("GET", url, headers=headers)
            
            if response.is_success:
                calendar_data = response.json()
                return {
                    "credentials_valid": True,
                    "calendar_access": True,
                    "primary_calendar": calendar_data.get("summary"),
                    "user_email": calendar_data.get("id")
                }
            else:
                self._handle_http_error(response)
                
        except Exception as e:
            logger.warning(f"Google Calendar connection test failed: {str(e)}")
            return {
                "credentials_valid": False,
                "error": str(e)
            }
    
    def _format_datetime(self, dt_input) -> str:
        """格式化日期时间为Google Calendar API格式"""
        if isinstance(dt_input, str):
            # 假设已经是正确格式的字符串
            return dt_input
        elif isinstance(dt_input, datetime):
            # 确保是UTC时间并格式化
            if dt_input.tzinfo is None:
                dt_input = dt_input.replace(tzinfo=timezone.utc)
            return dt_input.isoformat()
        else:
            raise ValidationError(f"Invalid datetime format: {type(dt_input)}")
    
    def _format_event_time(self, time_input) -> Dict[str, str]:
        """格式化事件时间"""
        if isinstance(time_input, dict):
            # 已经是正确格式
            return time_input
        elif isinstance(time_input, str):
            # 尝试解析字符串
            if "T" in time_input:
                # 日期时间格式
                return {"dateTime": time_input}
            else:
                # 日期格式
                return {"date": time_input}
        elif isinstance(time_input, datetime):
            # datetime对象
            return {"dateTime": self._format_datetime(time_input)}
        else:
            raise ValidationError(f"Invalid time format: {type(time_input)}")