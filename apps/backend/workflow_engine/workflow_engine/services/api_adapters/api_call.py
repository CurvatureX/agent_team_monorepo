"""
Generic API Call Adapter
通用HTTP API调用适配器
支持任意REST API调用，包含多种认证方式
"""

import logging
from typing import Dict, Any, Optional
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

logger = logging.getLogger(__name__)


@register_adapter("api_call")
class APICallAdapter(APIAdapter):
    """通用API调用适配器 - 支持任意HTTP API调用"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    async def call(self, operation: str, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """
        执行通用HTTP API调用
        
        Args:
            operation: 操作类型 (目前忽略，因为是通用调用)
            parameters: API调用参数
            credentials: 认证凭据
            
        Returns:
            API响应数据
        """
        try:
            self.logger.info(f"Generic API call with method: {parameters.get('method', 'GET')}")
            
            # 验证必需参数
            self._validate_parameters(parameters)
            
            # 准备请求参数
            method = parameters.get("method", "GET").upper()
            url = parameters["url"]
            headers = parameters.get("headers", {}).copy()
            query_params = parameters.get("query_params", {})
            body = parameters.get("body")
            timeout = int(parameters.get("timeout", 30))
            
            # 处理认证
            self._apply_authentication(headers, parameters, credentials)
            
            # 确保Content-Type
            if method in ["POST", "PUT", "PATCH"] and body and "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"
            
            # 添加用户代理
            if "User-Agent" not in headers:
                headers["User-Agent"] = "AgentTeam-Workflow-Engine/1.0"
            
            # 发送HTTP请求
            response = await self.make_http_request(
                method=method,
                url=url,
                headers=headers,
                params=query_params,
                json_data=body if isinstance(body, dict) else None,
                data=body if isinstance(body, str) else None,
                timeout=timeout
            )
            
            # 处理响应
            return await self._process_response(response, url, method)
            
        except Exception as e:
            self.logger.error(f"Generic API call failed: {e}")
            raise
    
    def get_oauth2_config(self) -> OAuth2Config:
        """通用API调用不需要特定的OAuth2配置"""
        return OAuth2Config(
            client_id="",
            client_secret="",
            auth_url="",
            token_url="",
            scopes=[]
        )
    
    def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """验证凭据（根据认证类型而定）"""
        # 对于通用API调用，认证是可选的
        return True
    
    def _validate_parameters(self, parameters: Dict[str, Any]):
        """验证API调用参数"""
        # 必需参数
        if "url" not in parameters:
            raise ValidationError("Missing required parameter: url")
        
        if "method" not in parameters:
            raise ValidationError("Missing required parameter: method")
        
        # 验证HTTP方法
        method = parameters.get("method", "").upper()
        valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
        if method not in valid_methods:
            raise ValidationError(f"Invalid HTTP method: {method}. Valid methods: {', '.join(valid_methods)}")
        
        # 验证URL格式
        url = parameters["url"]
        if not url.startswith(("http://", "https://")):
            raise ValidationError("URL must start with http:// or https://")
        
        # 验证认证类型
        auth_type = parameters.get("authentication", "none")
        valid_auth_types = ["none", "bearer", "basic", "api_key"]
        if auth_type not in valid_auth_types:
            raise ValidationError(f"Invalid authentication type: {auth_type}. Valid types: {', '.join(valid_auth_types)}")
        
        # 验证认证相关参数
        if auth_type == "bearer" and not parameters.get("auth_token"):
            raise ValidationError("auth_token is required for bearer authentication")
        
        if auth_type == "api_key" and not parameters.get("api_key_header"):
            raise ValidationError("api_key_header is required for api_key authentication")
        
        if auth_type == "api_key" and not parameters.get("auth_token"):
            raise ValidationError("auth_token is required for api_key authentication")
        
        # 验证超时值
        timeout = parameters.get("timeout", 30)
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValidationError("timeout must be a positive number")
        if timeout > 300:  # 5分钟最大超时
            raise ValidationError("timeout cannot exceed 300 seconds")
    
    def _apply_authentication(self, headers: Dict[str, str], parameters: Dict[str, Any], credentials: Dict[str, str]):
        """应用认证到请求头"""
        auth_type = parameters.get("authentication", "none")
        
        if auth_type == "none":
            return
        
        elif auth_type == "bearer":
            token = parameters.get("auth_token") or credentials.get("auth_token")
            if token:
                headers["Authorization"] = f"Bearer {token}"
        
        elif auth_type == "basic":
            # Basic认证需要username和password
            username = parameters.get("username") or credentials.get("username")
            password = parameters.get("password") or credentials.get("password")
            if username and password:
                import base64
                credentials_str = f"{username}:{password}"
                encoded_credentials = base64.b64encode(credentials_str.encode()).decode()
                headers["Authorization"] = f"Basic {encoded_credentials}"
        
        elif auth_type == "api_key":
            api_key_header = parameters.get("api_key_header", "X-API-Key")
            api_key = parameters.get("auth_token") or credentials.get("auth_token")
            if api_key:
                headers[api_key_header] = api_key
    
    async def _process_response(self, response, url: str, method: str) -> Dict[str, Any]:
        """处理HTTP响应"""
        # 获取响应数据
        response_text = ""
        response_json = None
        
        try:
            response_text = response.text
            # 尝试解析JSON
            if response.headers.get("content-type", "").startswith("application/json"):
                response_json = response.json()
        except Exception as e:
            self.logger.warning(f"Failed to parse response: {e}")
        
        # 检查响应状态
        success = 200 <= response.status_code < 300
        
        # 构建结果
        result = {
            "success": success,
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "url": url,
            "method": method,
            "response_text": response_text,
        }
        
        # 添加JSON数据（如果有）
        if response_json is not None:
            result["response_json"] = response_json
            result["data"] = response_json  # 方便访问
        
        # 添加响应大小信息
        result["content_length"] = len(response_text)
        
        # 如果不成功，抛出相应错误
        if not success:
            error_msg = f"HTTP {response.status_code}: {response.text[:200]}..."
            
            # 根据状态码分类错误
            if 400 <= response.status_code < 500:
                # 客户端错误
                if response.status_code == 401:
                    raise AuthenticationError(f"Authentication failed: {error_msg}")
                elif response.status_code == 403:
                    raise AuthenticationError(f"Access forbidden: {error_msg}")
                else:
                    raise PermanentError(error_msg)
            elif 500 <= response.status_code < 600:
                # 服务器错误
                raise TemporaryError(f"Server error: {error_msg}")
            else:
                raise PermanentError(f"Unexpected status code: {error_msg}")
        
        return result
    
    async def connection_test(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """测试API连接（通用测试）"""
        # 对于通用API调用，我们不能进行具体的连接测试
        # 因为我们不知道具体的API端点
        return {
            "credentials_valid": True,
            "message": "Generic API adapter ready. Connection test requires specific endpoint.",
            "authentication_support": ["none", "bearer", "basic", "api_key"]
        }