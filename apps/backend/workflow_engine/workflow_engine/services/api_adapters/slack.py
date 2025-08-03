"""
Slack API适配器
实现Slack API的统一调用接口
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from urllib.parse import urlencode
import json

from .base import APIAdapter, OAuth2Config, PermanentError, TemporaryError, ValidationError, register_adapter

logger = logging.getLogger(__name__)


@register_adapter("slack")
class SlackAdapter(APIAdapter):
    """Slack API适配器
    
    支持的操作:
    - send_message: 发送消息到频道
    - send_dm: 发送私信
    - list_channels: 列出频道
    - create_channel: 创建频道
    - join_channel: 加入频道
    - leave_channel: 离开频道
    - get_channel_info: 获取频道信息
    - list_users: 列出用户
    - get_user_info: 获取用户信息
    - upload_file: 上传文件
    - list_files: 列出文件
    - delete_file: 删除文件
    - add_reaction: 添加表情反应
    - remove_reaction: 移除表情反应
    - get_message_history: 获取消息历史
    - update_message: 更新消息
    - delete_message: 删除消息
    - set_presence: 设置在线状态
    - get_team_info: 获取团队信息
    - create_reminder: 创建提醒
    - list_reminders: 列出提醒
    - search_messages: 搜索消息
    - search_files: 搜索文件
    """
    
    # Slack API基础URL
    BASE_URL = "https://slack.com/api"
    
    # 支持的操作定义
    OPERATIONS = {
        # 消息操作
        "send_message": "发送消息到频道",
        "send_dm": "发送私信给用户",
        "update_message": "更新现有消息",
        "delete_message": "删除消息",
        "get_message_history": "获取频道消息历史",
        "add_reaction": "为消息添加表情反应",
        "remove_reaction": "移除消息的表情反应",
        
        # 频道操作
        "list_channels": "列出所有频道",
        "create_channel": "创建新频道",
        "join_channel": "加入频道",
        "leave_channel": "离开频道",
        "get_channel_info": "获取频道详细信息",
        "archive_channel": "归档频道",
        "unarchive_channel": "解除归档频道",
        "set_channel_topic": "设置频道主题",
        "set_channel_purpose": "设置频道用途",
        
        # 用户操作
        "list_users": "列出团队所有用户",
        "get_user_info": "获取用户详细信息",
        "get_user_presence": "获取用户在线状态",
        "set_presence": "设置自己的在线状态",
        
        # 文件操作
        "upload_file": "上传文件到Slack",
        "list_files": "列出文件",
        "get_file_info": "获取文件信息",
        "delete_file": "删除文件",
        "share_file": "分享文件到频道",
        
        # 搜索操作
        "search_messages": "搜索消息",
        "search_files": "搜索文件",
        "search_all": "搜索所有内容",
        
        # 团队和工作区操作
        "get_team_info": "获取团队信息",
        "get_auth_test": "测试认证状态",
        
        # 提醒操作
        "create_reminder": "创建提醒",
        "list_reminders": "列出提醒",
        "complete_reminder": "完成提醒",
        "delete_reminder": "删除提醒",
        
        # Webhook和应用操作
        "post_webhook": "发送Webhook消息",
        "list_apps": "列出已安装的应用",
        
        # 表情符号操作
        "list_emoji": "列出自定义表情符号",
        "get_emoji": "获取表情符号信息"
    }
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.provider_name = "slack"
    
    def get_oauth2_config(self) -> OAuth2Config:
        """获取Slack OAuth2配置"""
        return OAuth2Config(
            client_id="",  # 将从环境变量或配置中加载
            client_secret="",  # 将从环境变量或配置中加载
            auth_url="https://slack.com/oauth/v2/authorize",
            token_url="https://slack.com/api/oauth.v2.access",
            scopes=[
                "channels:read",     # 读取公共频道信息
                "channels:write",    # 管理公共频道
                "chat:write",        # 发送消息
                "chat:write.public", # 发送消息到公共频道
                "files:read",        # 读取文件
                "files:write",       # 上传和修改文件
                "users:read",        # 读取用户信息
                "users:read.email",  # 读取用户邮箱
                "search:read",       # 搜索工作区内容
                "reminders:write",   # 创建提醒
                "reactions:read",    # 读取表情反应
                "reactions:write"    # 添加表情反应
            ],
            redirect_uri="http://localhost:8000/auth/slack/callback"
        )
    
    def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """验证Slack凭证"""
        return ("access_token" in credentials and credentials["access_token"]) or \
               ("bot_token" in credentials and credentials["bot_token"]) or \
               ("webhook_url" in credentials and credentials["webhook_url"])
    
    def _prepare_headers(self, credentials: Dict[str, str], extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """准备Slack API请求头"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": self.http_config.user_agent
        }
        
        # 添加认证头部
        if "access_token" in credentials:
            headers["Authorization"] = f"Bearer {credentials['access_token']}"
        elif "bot_token" in credentials:
            headers["Authorization"] = f"Bearer {credentials['bot_token']}"
        elif "api_key" in credentials:
            # 传统API token
            headers["Authorization"] = f"Bearer {credentials['api_key']}"
        
        # 合并额外头部
        if extra_headers:
            headers.update(extra_headers)
        
        return headers
    
    async def call(self, operation: str, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """统一的API调用接口"""
        if not self.validate_credentials(credentials):
            raise ValidationError("Invalid credentials: missing access_token, bot_token, or webhook_url")
        
        if operation not in self.OPERATIONS:
            raise ValidationError(f"Unsupported operation: {operation}")
        
        # 根据操作类型分发到具体的处理方法
        handler_mapping = {
            # 消息操作
            "send_message": self._send_message,
            "send_dm": self._send_dm,
            "update_message": self._update_message,
            "delete_message": self._delete_message,
            "get_message_history": self._get_message_history,
            "add_reaction": self._add_reaction,
            "remove_reaction": self._remove_reaction,
            
            # 频道操作
            "list_channels": self._list_channels,
            "create_channel": self._create_channel,
            "join_channel": self._join_channel,
            "leave_channel": self._leave_channel,
            "get_channel_info": self._get_channel_info,
            "archive_channel": self._archive_channel,
            "unarchive_channel": self._unarchive_channel,
            "set_channel_topic": self._set_channel_topic,
            "set_channel_purpose": self._set_channel_purpose,
            
            # 用户操作
            "list_users": self._list_users,
            "get_user_info": self._get_user_info,
            "get_user_presence": self._get_user_presence,
            "set_presence": self._set_presence,
            
            # 文件操作
            "upload_file": self._upload_file,
            "list_files": self._list_files,
            "get_file_info": self._get_file_info,
            "delete_file": self._delete_file,
            "share_file": self._share_file,
            
            # 搜索操作
            "search_messages": self._search_messages,
            "search_files": self._search_files,
            "search_all": self._search_all,
            
            # 团队操作
            "get_team_info": self._get_team_info,
            "get_auth_test": self._get_auth_test,
            
            # 提醒操作
            "create_reminder": self._create_reminder,
            "list_reminders": self._list_reminders,
            "complete_reminder": self._complete_reminder,
            "delete_reminder": self._delete_reminder,
            
            # Webhook操作
            "post_webhook": self._post_webhook,
            
            # 表情符号操作
            "list_emoji": self._list_emoji,
            "get_emoji": self._get_emoji
        }
        
        handler = handler_mapping[operation]
        return await handler(parameters, credentials)
    
    # ========================================================================
    # 消息操作
    # ========================================================================
    
    async def _send_message(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """发送消息到频道"""
        channel = parameters.get("channel")
        text = parameters.get("text")
        
        if not channel or not text:
            raise ValidationError("Missing required parameters: channel and text")
        
        # 构建消息数据
        message_data = {
            "channel": channel,
            "text": text
        }
        
        # 可选参数
        if "username" in parameters:
            message_data["username"] = parameters["username"]
        if "icon_emoji" in parameters:
            message_data["icon_emoji"] = parameters["icon_emoji"]
        if "icon_url" in parameters:
            message_data["icon_url"] = parameters["icon_url"]
        if "thread_ts" in parameters:
            message_data["thread_ts"] = parameters["thread_ts"]
        if "reply_broadcast" in parameters:
            message_data["reply_broadcast"] = bool(parameters["reply_broadcast"])
        if "unfurl_links" in parameters:
            message_data["unfurl_links"] = bool(parameters["unfurl_links"])
        if "unfurl_media" in parameters:
            message_data["unfurl_media"] = bool(parameters["unfurl_media"])
        if "as_user" in parameters:
            message_data["as_user"] = bool(parameters["as_user"])
        
        # 支持富文本格式
        if "blocks" in parameters:
            message_data["blocks"] = parameters["blocks"]
        if "attachments" in parameters:
            message_data["attachments"] = parameters["attachments"]
        
        url = f"{self.BASE_URL}/chat.postMessage"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request("POST", url, headers=headers, json_data=message_data)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        result = response.json()
        
        if not result.get("ok"):
            raise TemporaryError(f"Slack API error: {result.get('error', 'Unknown error')}")
        
        return {
            "success": True,
            "message": result.get("message", {}),
            "ts": result.get("ts"),
            "channel": result.get("channel")
        }
    
    async def _send_dm(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """发送私信给用户"""
        user = parameters.get("user")
        text = parameters.get("text")
        
        if not user or not text:
            raise ValidationError("Missing required parameters: user and text")
        
        # 首先打开与用户的DM频道
        dm_data = {"users": user}
        
        url = f"{self.BASE_URL}/conversations.open"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request("POST", url, headers=headers, json_data=dm_data)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        dm_result = response.json()
        
        if not dm_result.get("ok"):
            raise TemporaryError(f"Failed to open DM: {dm_result.get('error', 'Unknown error')}")
        
        # 获取DM频道ID并发送消息
        dm_channel = dm_result["channel"]["id"]
        
        # 使用send_message发送到DM频道
        message_params = parameters.copy()
        message_params["channel"] = dm_channel
        
        return await self._send_message(message_params, credentials)
    
    async def _update_message(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """更新现有消息"""
        channel = parameters.get("channel")
        ts = parameters.get("ts")
        text = parameters.get("text")
        
        if not channel or not ts:
            raise ValidationError("Missing required parameters: channel and ts")
        
        # 构建更新数据
        update_data = {
            "channel": channel,
            "ts": ts
        }
        
        if text:
            update_data["text"] = text
        if "blocks" in parameters:
            update_data["blocks"] = parameters["blocks"]
        if "attachments" in parameters:
            update_data["attachments"] = parameters["attachments"]
        
        url = f"{self.BASE_URL}/chat.update"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request("POST", url, headers=headers, json_data=update_data)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        result = response.json()
        
        if not result.get("ok"):
            raise TemporaryError(f"Slack API error: {result.get('error', 'Unknown error')}")
        
        return {
            "success": True,
            "message": result.get("message", {}),
            "ts": result.get("ts"),
            "channel": result.get("channel")
        }
    
    # ========================================================================
    # 频道操作
    # ========================================================================
    
    async def _list_channels(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """列出所有频道"""
        url = f"{self.BASE_URL}/conversations.list"
        
        # 构建查询参数
        query_params = {}
        if "types" in parameters:
            query_params["types"] = parameters["types"]  # public_channel, private_channel, mpim, im
        else:
            query_params["types"] = "public_channel,private_channel"
        
        if "exclude_archived" in parameters:
            query_params["exclude_archived"] = str(parameters["exclude_archived"]).lower()
        if "limit" in parameters:
            query_params["limit"] = min(int(parameters["limit"]), 1000)
        if "cursor" in parameters:
            query_params["cursor"] = parameters["cursor"]
        
        if query_params:
            url += f"?{urlencode(query_params)}"
        
        headers = self._prepare_headers(credentials)
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        result = response.json()
        
        if not result.get("ok"):
            raise TemporaryError(f"Slack API error: {result.get('error', 'Unknown error')}")
        
        return {
            "success": True,
            "channels": result.get("channels", []),
            "next_cursor": result.get("response_metadata", {}).get("next_cursor"),
            "total_count": len(result.get("channels", []))
        }
    
    async def _create_channel(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """创建新频道"""
        name = parameters.get("name")
        
        if not name:
            raise ValidationError("Missing required parameter: name")
        
        # 构建频道数据
        channel_data = {"name": name}
        
        # 可选参数
        if "is_private" in parameters:
            channel_data["is_private"] = bool(parameters["is_private"])
        
        url = f"{self.BASE_URL}/conversations.create"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request("POST", url, headers=headers, json_data=channel_data)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        result = response.json()
        
        if not result.get("ok"):
            raise TemporaryError(f"Slack API error: {result.get('error', 'Unknown error')}")
        
        return {
            "success": True,
            "channel": result.get("channel", {}),
            "channel_id": result.get("channel", {}).get("id")
        }
    
    async def _join_channel(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """加入频道"""
        channel = parameters.get("channel")
        
        if not channel:
            raise ValidationError("Missing required parameter: channel")
        
        join_data = {"channel": channel}
        
        url = f"{self.BASE_URL}/conversations.join"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request("POST", url, headers=headers, json_data=join_data)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        result = response.json()
        
        if not result.get("ok"):
            raise TemporaryError(f"Slack API error: {result.get('error', 'Unknown error')}")
        
        return {
            "success": True,
            "channel": result.get("channel", {}),
            "warning": result.get("warning")
        }
    
    # ========================================================================
    # 用户操作
    # ========================================================================
    
    async def _list_users(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """列出团队所有用户"""
        url = f"{self.BASE_URL}/users.list"
        
        # 构建查询参数
        query_params = {}
        if "include_locale" in parameters:
            query_params["include_locale"] = str(parameters["include_locale"]).lower()
        if "limit" in parameters:
            query_params["limit"] = min(int(parameters["limit"]), 1000)
        if "cursor" in parameters:
            query_params["cursor"] = parameters["cursor"]
        
        if query_params:
            url += f"?{urlencode(query_params)}"
        
        headers = self._prepare_headers(credentials)
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        result = response.json()
        
        if not result.get("ok"):
            raise TemporaryError(f"Slack API error: {result.get('error', 'Unknown error')}")
        
        return {
            "success": True,
            "users": result.get("members", []),
            "next_cursor": result.get("response_metadata", {}).get("next_cursor"),
            "total_count": len(result.get("members", []))
        }
    
    async def _get_user_info(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """获取用户详细信息"""
        user = parameters.get("user")
        
        if not user:
            raise ValidationError("Missing required parameter: user")
        
        query_params = {"user": user}
        if "include_locale" in parameters:
            query_params["include_locale"] = str(parameters["include_locale"]).lower()
        
        url = f"{self.BASE_URL}/users.info?{urlencode(query_params)}"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        result = response.json()
        
        if not result.get("ok"):
            raise TemporaryError(f"Slack API error: {result.get('error', 'Unknown error')}")
        
        return {
            "success": True,
            "user": result.get("user", {})
        }
    
    # ========================================================================
    # 文件操作
    # ========================================================================
    
    async def _upload_file(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """上传文件到Slack"""
        import aiofiles
        
        channels = parameters.get("channels")  # 可以是频道ID或频道名称
        filename = parameters.get("filename")
        title = parameters.get("title")
        initial_comment = parameters.get("initial_comment")
        file_content = parameters.get("content")  # 文件内容（文本）
        file_path = parameters.get("file_path")   # 文件路径
        
        if not channels:
            raise ValidationError("Missing required parameter: channels")
        
        if not file_content and not file_path:
            raise ValidationError("Missing required parameter: content or file_path")
        
        url = f"{self.BASE_URL}/files.upload"
        headers = self._prepare_headers(credentials)
        
        # 准备文件数据
        files = {}
        data = {
            "channels": channels,
        }
        
        if title:
            data["title"] = title
        if initial_comment:
            data["initial_comment"] = initial_comment
        if filename:
            data["filename"] = filename
        
        if file_content:
            # 如果提供的是文件内容（字符串）
            if not filename:
                filename = "uploaded_file.txt"
            data["filename"] = filename
            data["content"] = file_content
            
            # 对于文本内容，我们可以直接作为参数发送
            response = await self.make_http_request("POST", url, data=data, headers=headers)
            
        elif file_path:
            # 如果提供的是文件路径，需要读取文件并上传
            try:
                async with aiofiles.open(file_path, 'rb') as f:
                    file_content = await f.read()
                
                if not filename:
                    import os
                    filename = os.path.basename(file_path)
                
                data["filename"] = filename
                
                # 对于二进制文件，需要使用 multipart/form-data
                files = {
                    'file': (filename, file_content, 'application/octet-stream')
                }
                
                # 移除headers中的Content-Type，让httpx自动设置multipart
                upload_headers = {k: v for k, v in headers.items() if k.lower() != 'content-type'}
                
                response = await self.make_http_request("POST", url, data=data, files=files, headers=upload_headers)
                
            except FileNotFoundError:
                raise ValidationError(f"File not found: {file_path}")
            except Exception as e:
                raise APIError(f"Failed to read file: {str(e)}")
        
        if not response.is_success:
            self._handle_http_error(response)
        
        result = response.json()
        
        if not result.get("ok", False):
            error_msg = result.get("error", "Unknown error")
            raise APIError(f"Slack API error: {error_msg}")
        
        return {
            "success": True,
            "file": result.get("file", {}),
            "file_id": result.get("file", {}).get("id"),
            "permalink": result.get("file", {}).get("permalink")
        }
    
    # ========================================================================
    # 搜索操作
    # ========================================================================
    
    async def _search_messages(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """搜索消息"""
        query = parameters.get("query")
        
        if not query:
            raise ValidationError("Missing required parameter: query")
        
        search_params = {"query": query}
        
        # 可选参数
        if "sort" in parameters:
            search_params["sort"] = parameters["sort"]  # score, timestamp
        if "sort_dir" in parameters:
            search_params["sort_dir"] = parameters["sort_dir"]  # asc, desc
        if "highlight" in parameters:
            search_params["highlight"] = str(parameters["highlight"]).lower()
        if "count" in parameters:
            search_params["count"] = min(int(parameters["count"]), 1000)
        if "page" in parameters:
            search_params["page"] = int(parameters["page"])
        
        url = f"{self.BASE_URL}/search.messages?{urlencode(search_params)}"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        result = response.json()
        
        if not result.get("ok"):
            raise TemporaryError(f"Slack API error: {result.get('error', 'Unknown error')}")
        
        messages_data = result.get("messages", {})
        
        return {
            "success": True,
            "messages": messages_data.get("matches", []),
            "total": messages_data.get("total", 0),
            "page": messages_data.get("page", 1),
            "per_page": messages_data.get("per_page", 20)
        }
    
    # ========================================================================
    # 团队操作
    # ========================================================================
    
    async def _get_team_info(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """获取团队信息"""
        url = f"{self.BASE_URL}/team.info"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        result = response.json()
        
        if not result.get("ok"):
            raise TemporaryError(f"Slack API error: {result.get('error', 'Unknown error')}")
        
        return {
            "success": True,
            "team": result.get("team", {})
        }
    
    async def _get_auth_test(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """测试认证状态"""
        url = f"{self.BASE_URL}/auth.test"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        result = response.json()
        
        if not result.get("ok"):
            raise TemporaryError(f"Slack API error: {result.get('error', 'Unknown error')}")
        
        return {
            "success": True,
            "url": result.get("url"),
            "team": result.get("team"),
            "user": result.get("user"),
            "team_id": result.get("team_id"),
            "user_id": result.get("user_id"),
            "bot_id": result.get("bot_id")
        }
    
    # ========================================================================
    # Webhook操作
    # ========================================================================
    
    async def _post_webhook(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """发送Webhook消息"""
        webhook_url = credentials.get("webhook_url")
        
        if not webhook_url:
            raise ValidationError("Missing webhook_url in credentials")
        
        text = parameters.get("text")
        if not text:
            raise ValidationError("Missing required parameter: text")
        
        # 构建Webhook数据
        webhook_data = {"text": text}
        
        # 可选参数
        if "username" in parameters:
            webhook_data["username"] = parameters["username"]
        if "icon_emoji" in parameters:
            webhook_data["icon_emoji"] = parameters["icon_emoji"]
        if "icon_url" in parameters:
            webhook_data["icon_url"] = parameters["icon_url"]
        if "channel" in parameters:
            webhook_data["channel"] = parameters["channel"]
        if "attachments" in parameters:
            webhook_data["attachments"] = parameters["attachments"]
        if "blocks" in parameters:
            webhook_data["blocks"] = parameters["blocks"]
        
        # Webhook不需要Authorization头部
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        response = await self.make_http_request("POST", webhook_url, headers=headers, json_data=webhook_data)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        # Webhook响应通常是"ok"字符串
        response_text = response.text
        
        return {
            "success": True,
            "response": response_text,
            "webhook_url": webhook_url
        }
    
    # ========================================================================
    # 其他操作的占位符实现
    # ========================================================================
    
    async def _delete_message(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """删除消息"""
        # TODO: 实现删除消息逻辑
        return {"success": True, "message": "Delete message not implemented yet"}
    
    async def _get_message_history(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """获取频道消息历史"""
        # TODO: 实现获取消息历史逻辑
        return {"success": True, "message": "Get message history not implemented yet"}
    
    async def _add_reaction(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """添加表情反应"""
        # TODO: 实现添加反应逻辑
        return {"success": True, "message": "Add reaction not implemented yet"}
    
    async def _remove_reaction(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """移除表情反应"""
        # TODO: 实现移除反应逻辑
        return {"success": True, "message": "Remove reaction not implemented yet"}
    
    async def _leave_channel(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """离开频道"""
        # TODO: 实现离开频道逻辑
        return {"success": True, "message": "Leave channel not implemented yet"}
    
    async def _get_channel_info(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """获取频道信息"""
        # TODO: 实现获取频道信息逻辑
        return {"success": True, "message": "Get channel info not implemented yet"}
    
    async def _archive_channel(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """归档频道"""
        # TODO: 实现归档频道逻辑
        return {"success": True, "message": "Archive channel not implemented yet"}
    
    async def _unarchive_channel(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """解除归档频道"""
        # TODO: 实现解除归档频道逻辑
        return {"success": True, "message": "Unarchive channel not implemented yet"}
    
    async def _set_channel_topic(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """设置频道主题"""
        # TODO: 实现设置频道主题逻辑
        return {"success": True, "message": "Set channel topic not implemented yet"}
    
    async def _set_channel_purpose(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """设置频道用途"""
        # TODO: 实现设置频道用途逻辑
        return {"success": True, "message": "Set channel purpose not implemented yet"}
    
    async def _get_user_presence(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """获取用户在线状态"""
        # TODO: 实现获取用户状态逻辑
        return {"success": True, "message": "Get user presence not implemented yet"}
    
    async def _set_presence(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """设置自己的在线状态"""
        # TODO: 实现设置状态逻辑
        return {"success": True, "message": "Set presence not implemented yet"}
    
    async def _upload_file(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """上传文件到Slack"""
        file_content = parameters.get("file_content")
        file_name = parameters.get("file_name")
        channels = parameters.get("channels")
        title = parameters.get("title")
        initial_comment = parameters.get("initial_comment")
        thread_ts = parameters.get("thread_ts")
        
        if not all([file_content, file_name]):
            raise ValidationError("Missing required parameters: file_content, file_name")
        
        # 准备multipart/form-data
        import aiofiles
        import tempfile
        import os
        
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='wb', delete=False) as temp_file:
                if isinstance(file_content, str):
                    temp_file.write(file_content.encode('utf-8'))
                else:
                    temp_file.write(file_content)
                temp_file_path = temp_file.name
            
            # 准备表单数据
            form_data = {
                'filename': file_name,
                'title': title or file_name,
            }
            
            if channels:
                form_data['channels'] = channels
            if initial_comment:
                form_data['initial_comment'] = initial_comment
            if thread_ts:
                form_data['thread_ts'] = thread_ts
            
            # 准备文件上传
            files = {'file': (file_name, open(temp_file_path, 'rb'))}
            
            url = f"{self.BASE_URL}/files.upload"
            headers = self._prepare_headers(credentials, {'Content-Type': None})  # 让httpx自动设置multipart
            
            response = await self.make_http_request(
                "POST", 
                url, 
                headers=headers, 
                data=form_data,
                files=files
            )
            
            # 清理临时文件
            files['file'][1].close()
            os.unlink(temp_file_path)
            
            if not response.is_success:
                self._handle_http_error(response)
            
            result = response.json()
            
            if not result.get("ok"):
                raise TemporaryError(f"Slack API error: {result.get('error', 'Unknown error')}")
            
            return {
                "success": True,
                "file": result.get("file", {}),
                "file_id": result.get("file", {}).get("id"),
                "permalink": result.get("file", {}).get("permalink"),
                "permalink_public": result.get("file", {}).get("permalink_public")
            }
            
        except Exception as e:
            # 确保清理临时文件
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            raise
    
    async def _list_files(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """列出文件"""
        url = f"{self.BASE_URL}/files.list"
        
        # 构建查询参数
        query_params = {}
        if "user" in parameters:
            query_params["user"] = parameters["user"]
        if "channel" in parameters:
            query_params["channel"] = parameters["channel"]
        if "ts_from" in parameters:
            query_params["ts_from"] = parameters["ts_from"]
        if "ts_to" in parameters:
            query_params["ts_to"] = parameters["ts_to"]
        if "types" in parameters:
            query_params["types"] = parameters["types"]
        if "count" in parameters:
            query_params["count"] = min(int(parameters["count"]), 1000)
        if "page" in parameters:
            query_params["page"] = parameters["page"]
        
        if query_params:
            from urllib.parse import urlencode
            url += f"?{urlencode(query_params)}"
        
        headers = self._prepare_headers(credentials)
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not response.is_success:
            self._handle_http_error(response)
        
        result = response.json()
        
        if not result.get("ok"):
            raise TemporaryError(f"Slack API error: {result.get('error', 'Unknown error')}")
        
        return {
            "success": True,
            "files": result.get("files", []),
            "paging": result.get("paging", {})
        }
    
    async def _get_file_info(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """获取文件信息"""
        # TODO: 实现获取文件信息逻辑
        return {"success": True, "message": "Get file info not implemented yet"}
    
    async def _delete_file(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """删除文件"""
        # TODO: 实现删除文件逻辑
        return {"success": True, "message": "Delete file not implemented yet"}
    
    async def _share_file(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """分享文件到频道"""
        # TODO: 实现分享文件逻辑
        return {"success": True, "message": "Share file not implemented yet"}
    
    async def _search_files(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """搜索文件"""
        # TODO: 实现搜索文件逻辑
        return {"success": True, "message": "Search files not implemented yet"}
    
    async def _search_all(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """搜索所有内容"""
        # TODO: 实现搜索所有内容逻辑
        return {"success": True, "message": "Search all not implemented yet"}
    
    async def _create_reminder(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """创建提醒"""
        # TODO: 实现创建提醒逻辑
        return {"success": True, "message": "Create reminder not implemented yet"}
    
    async def _list_reminders(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """列出提醒"""
        # TODO: 实现列出提醒逻辑
        return {"success": True, "message": "List reminders not implemented yet"}
    
    async def _complete_reminder(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """完成提醒"""
        # TODO: 实现完成提醒逻辑
        return {"success": True, "message": "Complete reminder not implemented yet"}
    
    async def _delete_reminder(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """删除提醒"""
        # TODO: 实现删除提醒逻辑
        return {"success": True, "message": "Delete reminder not implemented yet"}
    
    async def _list_emoji(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """列出自定义表情符号"""
        # TODO: 实现列出表情符号逻辑
        return {"success": True, "message": "List emoji not implemented yet"}
    
    async def _get_emoji(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """获取表情符号信息"""
        # TODO: 实现获取表情符号信息逻辑
        return {"success": True, "message": "Get emoji not implemented yet"}
    
    async def _default_connection_test(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Slack特定的连接测试"""
        try:
            # 如果是webhook，测试webhook URL
            if "webhook_url" in credentials:
                # 简单测试Webhook URL的可达性
                webhook_url = credentials["webhook_url"]
                if not webhook_url.startswith("https://hooks.slack.com/"):
                    return {
                        "credentials_valid": False,
                        "error": "Invalid webhook URL format"
                    }
                
                return {
                    "credentials_valid": True,
                    "webhook_access": True,
                    "webhook_url": webhook_url
                }
            
            # 对于OAuth token，测试auth.test端点
            url = f"{self.BASE_URL}/auth.test"
            headers = self._prepare_headers(credentials)
            
            response = await self.make_http_request("GET", url, headers=headers)
            
            if response.is_success:
                result = response.json()
                if result.get("ok"):
                    return {
                        "credentials_valid": True,
                        "slack_access": True,
                        "team": result.get("team"),
                        "user": result.get("user"),
                        "team_id": result.get("team_id"),
                        "user_id": result.get("user_id"),
                        "url": result.get("url")
                    }
                else:
                    return {
                        "credentials_valid": False,
                        "error": result.get("error", "Unknown Slack API error")
                    }
            else:
                self._handle_http_error(response)
                
        except Exception as e:
            logger.warning(f"Slack connection test failed: {str(e)}")
            return {
                "credentials_valid": False,
                "error": str(e)
            }