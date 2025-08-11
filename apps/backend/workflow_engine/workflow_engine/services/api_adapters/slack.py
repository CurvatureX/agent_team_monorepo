"""
Slack API Adapter
基于shared/sdks/slack_sdk的Slack集成适配器
支持消息发送、Block Kit、文件上传等操作
"""

from typing import Dict, Any, Optional, List
import json

from .base import (
    APIAdapter, 
    OAuth2Config, 
    ValidationError, 
    AuthenticationError,
    TemporaryError,
    PermanentError,
    register_adapter
)

from shared.logging_config import get_logger
logger = get_logger(__name__)


@register_adapter("slack")
class SlackAdapter(APIAdapter):
    """Slack API适配器 - 集成Slack SDK功能"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = "https://slack.com/api"
    
    async def call(self, operation: str, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """
        执行Slack API操作
        
        Args:
            operation: Slack操作类型 (目前主要是send_message)
            parameters: 操作参数
            credentials: 认证凭据
            
        Returns:
            Slack API响应数据
        """
        try:
            self.logger.info(f"Slack operation: {operation} with params: {list(parameters.keys())}")
            
            # 验证凭据
            if not self.validate_credentials(credentials):
                raise AuthenticationError("Invalid Slack credentials")
            
            # 验证参数
            self._validate_parameters(operation, parameters)
            
            # 根据操作类型调用相应的方法
            if operation == "send_message" or operation == "post_message":
                return await self._send_message(parameters, credentials)
            elif operation == "update_message":
                return await self._update_message(parameters, credentials)
            elif operation == "delete_message":
                return await self._delete_message(parameters, credentials)
            elif operation == "upload_file":
                return await self._upload_file(parameters, credentials)
            elif operation == "get_user_info":
                return await self._get_user_info(parameters, credentials)
            elif operation == "list_channels":
                return await self._list_channels(parameters, credentials)
            else:
                # 默认为发送消息
                return await self._send_message(parameters, credentials)
                
        except Exception as e:
            self.logger.error(f"Slack API call failed: {e}")
            raise
    
    def get_oauth2_config(self) -> OAuth2Config:
        """获取Slack OAuth2配置"""
        import os
        return OAuth2Config(
            client_id=os.getenv("SLACK_CLIENT_ID", ""),
            client_secret=os.getenv("SLACK_CLIENT_SECRET", ""),
            auth_url="https://slack.com/oauth/v2/authorize",
            token_url="https://slack.com/api/oauth.v2.access",
            scopes=["chat:write", "channels:read"]
        )
    
    def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """验证Slack凭据"""
        return "bot_token" in credentials or "access_token" in credentials
    
    def _validate_parameters(self, operation: str, parameters: Dict[str, Any]):
        """验证操作参数"""
        required_params = {
            "send_message": ["channel", "message"],
            "post_message": ["channel", "message"],
            "update_message": ["channel", "ts", "message"],
            "delete_message": ["channel", "ts"],
            "upload_file": ["channels", "file_content"],
            "get_user_info": ["user_id"],
            "list_channels": []  # 无必需参数
        }
        
        # 默认为send_message的参数要求
        required = required_params.get(operation, ["channel", "message"])
        
        for param in required:
            if param not in parameters:
                raise ValidationError(f"Missing required parameter: {param}")
    
    async def _send_message(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """发送Slack消息"""
        # 构建消息数据
        message_data = {
            "channel": parameters["channel"],
            "text": parameters["message"]
        }
        
        # 可选参数
        if "username" in parameters:
            message_data["username"] = parameters["username"]
        
        if "icon_emoji" in parameters:
            message_data["icon_emoji"] = parameters["icon_emoji"]
        elif "icon_url" in parameters:
            message_data["icon_url"] = parameters["icon_url"]
        
        if "thread_ts" in parameters:
            message_data["thread_ts"] = parameters["thread_ts"]
        
        # 处理attachments
        if "attachments" in parameters and parameters["attachments"]:
            if isinstance(parameters["attachments"], list):
                message_data["attachments"] = json.dumps(parameters["attachments"])
            else:
                message_data["attachments"] = parameters["attachments"]
        
        # 处理blocks (Block Kit)
        if "blocks" in parameters and parameters["blocks"]:
            if isinstance(parameters["blocks"], list):
                message_data["blocks"] = json.dumps(parameters["blocks"])
            else:
                message_data["blocks"] = parameters["blocks"]
        
        # 发送请求
        response = await self.make_http_request(
            method="POST",
            url=f"{self.base_url}/chat.postMessage",
            headers=self._prepare_headers(credentials),
            json_data=message_data
        )
        
        if not response.is_success:
            self._handle_http_error(response)
        
        result = response.json()
        
        # 检查Slack API错误
        if not result.get("ok", False):
            error = result.get("error", "unknown_error")
            raise PermanentError(f"Slack API error: {error}")
        
        return {
            "success": True,
            "ts": result["ts"],
            "channel": result["channel"],
            "message": result.get("message", {}),
            "response": result
        }
    
    async def _update_message(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """更新Slack消息"""
        message_data = {
            "channel": parameters["channel"],
            "ts": parameters["ts"],
            "text": parameters["message"]
        }
        
        # 处理blocks和attachments
        if "blocks" in parameters and parameters["blocks"]:
            if isinstance(parameters["blocks"], list):
                message_data["blocks"] = json.dumps(parameters["blocks"])
            else:
                message_data["blocks"] = parameters["blocks"]
        
        if "attachments" in parameters and parameters["attachments"]:
            if isinstance(parameters["attachments"], list):
                message_data["attachments"] = json.dumps(parameters["attachments"])
            else:
                message_data["attachments"] = parameters["attachments"]
        
        response = await self.make_http_request(
            method="POST",
            url=f"{self.base_url}/chat.update",
            headers=self._prepare_headers(credentials),
            json_data=message_data
        )
        
        if not response.is_success:
            self._handle_http_error(response)
        
        result = response.json()
        
        if not result.get("ok", False):
            error = result.get("error", "unknown_error")
            raise PermanentError(f"Slack API error: {error}")
        
        return {
            "success": True,
            "ts": result["ts"],
            "channel": result["channel"],
            "updated": True,
            "response": result
        }
    
    async def _delete_message(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """删除Slack消息"""
        message_data = {
            "channel": parameters["channel"],
            "ts": parameters["ts"]
        }
        
        response = await self.make_http_request(
            method="POST",
            url=f"{self.base_url}/chat.delete",
            headers=self._prepare_headers(credentials),
            json_data=message_data
        )
        
        if not response.is_success:
            self._handle_http_error(response)
        
        result = response.json()
        
        if not result.get("ok", False):
            error = result.get("error", "unknown_error")
            raise PermanentError(f"Slack API error: {error}")
        
        return {
            "success": True,
            "ts": result["ts"],
            "channel": result["channel"],
            "deleted": True,
            "response": result
        }
    
    async def _upload_file(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """上传文件到Slack"""
        file_data = {
            "channels": parameters["channels"],
            "content": parameters["file_content"]
        }
        
        # 可选参数
        if "filename" in parameters:
            file_data["filename"] = parameters["filename"]
        if "filetype" in parameters:
            file_data["filetype"] = parameters["filetype"]
        if "title" in parameters:
            file_data["title"] = parameters["title"]
        if "initial_comment" in parameters:
            file_data["initial_comment"] = parameters["initial_comment"]
        
        response = await self.make_http_request(
            method="POST",
            url=f"{self.base_url}/files.upload",
            headers=self._prepare_headers(credentials),
            json_data=file_data
        )
        
        if not response.is_success:
            self._handle_http_error(response)
        
        result = response.json()
        
        if not result.get("ok", False):
            error = result.get("error", "unknown_error")
            raise PermanentError(f"Slack API error: {error}")
        
        file_info = result.get("file", {})
        return {
            "success": True,
            "file_id": file_info.get("id"),
            "file_url": file_info.get("url_private"),
            "filename": file_info.get("name"),
            "file": file_info,
            "response": result
        }
    
    async def _get_user_info(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """获取用户信息"""
        user_data = {
            "user": parameters["user_id"]
        }
        
        response = await self.make_http_request(
            method="POST",
            url=f"{self.base_url}/users.info",
            headers=self._prepare_headers(credentials),
            json_data=user_data
        )
        
        if not response.is_success:
            self._handle_http_error(response)
        
        result = response.json()
        
        if not result.get("ok", False):
            error = result.get("error", "unknown_error")
            raise PermanentError(f"Slack API error: {error}")
        
        user_info = result.get("user", {})
        return {
            "success": True,
            "user_id": user_info.get("id"),
            "username": user_info.get("name"),
            "display_name": user_info.get("profile", {}).get("display_name"),
            "email": user_info.get("profile", {}).get("email"),
            "user": user_info,
            "response": result
        }
    
    async def _list_channels(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """列出频道"""
        channel_data = {
            "exclude_archived": parameters.get("exclude_archived", True),
            "limit": min(int(parameters.get("limit", 100)), 1000)
        }
        
        if "cursor" in parameters:
            channel_data["cursor"] = parameters["cursor"]
        
        response = await self.make_http_request(
            method="POST",
            url=f"{self.base_url}/conversations.list",
            headers=self._prepare_headers(credentials),
            json_data=channel_data
        )
        
        if not response.is_success:
            self._handle_http_error(response)
        
        result = response.json()
        
        if not result.get("ok", False):
            error = result.get("error", "unknown_error")
            raise PermanentError(f"Slack API error: {error}")
        
        channels = result.get("channels", [])
        return {
            "success": True,
            "total_count": len(channels),
            "channels": channels,
            "next_cursor": result.get("response_metadata", {}).get("next_cursor"),
            "response": result
        }
    
    def _prepare_headers(self, credentials: Dict[str, str]) -> Dict[str, str]:
        """准备Slack API请求头"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AgentTeam-Workflow-Engine/1.0"
        }
        
        # 添加认证
        token = credentials.get("bot_token") or credentials.get("access_token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        return headers