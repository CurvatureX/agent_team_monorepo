"""
HTTP Tool通用适配器
实现通用HTTP请求工具适配器，支持所有标准HTTP方法，灵活的认证方式，可配置的请求参数和头部信息
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union
from urllib.parse import urljoin, urlparse

import httpx

from .base import (
    APIAdapter, 
    OAuth2Config, 
    RetryConfig, 
    HTTPConfig,
    APIError,
    AuthenticationError,
    ValidationError,
    NetworkError,
    TemporaryError,
    PermanentError,
    register_adapter
)

logger = logging.getLogger(__name__)


# ============================================================================
# 配置类定义
# ============================================================================

@dataclass
class HTTPAuthConfig:
    """HTTP认证配置"""
    auth_type: str  # "none", "bearer", "basic", "api_key", "oauth2"
    
    # Bearer Token认证
    bearer_token: Optional[str] = None
    
    # Basic认证
    username: Optional[str] = None
    password: Optional[str] = None
    
    # API Key认证
    api_key: Optional[str] = None
    api_key_header: str = "X-API-Key"  # 默认头部名称
    api_key_location: str = "header"  # "header" 或 "query"
    api_key_param: str = "api_key"  # 查询参数名称
    
    # OAuth2认证（使用外部凭证）
    oauth2_provider: Optional[str] = None


@dataclass 
class HTTPRequestConfig:
    """HTTP请求配置"""
    method: str = "GET"
    url: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    query_params: Dict[str, Any] = field(default_factory=dict)
    
    # 请求体配置
    json_data: Optional[Dict[str, Any]] = None
    form_data: Optional[Dict[str, Any]] = None
    raw_data: Optional[str] = None
    
    # 认证配置
    auth: Optional[HTTPAuthConfig] = None
    
    # 请求选项
    follow_redirects: bool = True
    verify_ssl: bool = True
    timeout: float = 30.0
    
    # 响应处理
    expected_status_codes: List[int] = field(default_factory=lambda: [200])
    response_format: str = "json"  # "json", "text", "raw"


# ============================================================================
# HTTP Tool适配器实现
# ============================================================================

@register_adapter("http_tool")
class HTTPToolAdapter(APIAdapter):
    """HTTP Tool通用适配器
    
    支持所有标准HTTP方法，多种认证方式，灵活的请求/响应处理。
    可以用于调用任何REST API或HTTP服务。
    """
    
    # 支持的操作定义
    OPERATIONS = {
        "request": "发起HTTP请求",
        "get": "发起GET请求",
        "post": "发起POST请求", 
        "put": "发起PUT请求",
        "patch": "发起PATCH请求",
        "delete": "发起DELETE请求",
        "head": "发起HEAD请求",
        "options": "发起OPTIONS请求"
    }
    
    def __init__(
        self,
        retry_config: Optional[RetryConfig] = None,
        http_config: Optional[HTTPConfig] = None
    ):
        super().__init__(retry_config, http_config)
        self.provider_name = "http_tool"
    
    def get_oauth2_config(self) -> OAuth2Config:
        """HTTP Tool不需要OAuth2配置"""
        raise NotImplementedError("HTTP Tool adapter does not support OAuth2")
    
    def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """验证凭证有效性
        
        HTTP Tool适配器支持多种认证方式，根据请求配置动态验证。
        """
        # HTTP Tool的凭证验证在具体请求时进行
        return True
    
    async def call(
        self, 
        operation: str, 
        parameters: Dict[str, Any],
        credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """统一的HTTP API调用接口
        
        Args:
            operation: 操作名称 ("request", "get", "post"等)
            parameters: 请求配置参数
            credentials: 认证凭证（可选，某些请求不需要认证）
            
        Returns:
            HTTP响应数据
        """
        try:
            # 解析请求配置
            request_config = self._parse_request_config(operation, parameters)
            
            # 准备认证
            await self._prepare_authentication(request_config, credentials)
            
            # 验证请求配置
            self._validate_request_config(request_config)
            
            # 发起HTTP请求
            response = await self._make_http_request(request_config)
            
            # 处理响应
            result = await self._process_response(response, request_config)
            
            return {
                "success": True,
                "method": request_config.method,
                "url": request_config.url,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "data": result,
                "execution_time_ms": getattr(response, 'elapsed', 0)
            }
            
        except Exception as e:
            logger.error(f"HTTP tool request failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def _parse_request_config(self, operation: str, parameters: Dict[str, Any]) -> HTTPRequestConfig:
        """解析请求配置"""
        # 支持的HTTP方法映射
        method_mapping = {
            "request": parameters.get("method", "GET").upper(),
            "get": "GET",
            "post": "POST", 
            "put": "PUT",
            "patch": "PATCH",
            "delete": "DELETE",
            "head": "HEAD",
            "options": "OPTIONS"
        }
        
        method = method_mapping.get(operation, "GET")
        
        # 基础配置
        config = HTTPRequestConfig(
            method=method,
            url=parameters.get("url", ""),
            headers=parameters.get("headers", {}),
            query_params=parameters.get("query_params", {}),
            follow_redirects=parameters.get("follow_redirects", True),
            verify_ssl=parameters.get("verify_ssl", True),
            timeout=parameters.get("timeout", 30.0),
            expected_status_codes=parameters.get("expected_status_codes", [200]),
            response_format=parameters.get("response_format", "json")
        )
        
        # 请求体配置
        if "json" in parameters:
            config.json_data = parameters["json"]
        elif "data" in parameters:
            if isinstance(parameters["data"], dict):
                config.form_data = parameters["data"]
            else:
                config.raw_data = str(parameters["data"])
        
        # 认证配置
        if "auth" in parameters:
            config.auth = self._parse_auth_config(parameters["auth"])
        
        return config
    
    def _parse_auth_config(self, auth_params: Dict[str, Any]) -> HTTPAuthConfig:
        """解析认证配置"""
        auth_type = auth_params.get("type", "none").lower()
        
        auth_config = HTTPAuthConfig(auth_type=auth_type)
        
        if auth_type == "bearer":
            auth_config.bearer_token = auth_params.get("token")
        elif auth_type == "basic":
            auth_config.username = auth_params.get("username")
            auth_config.password = auth_params.get("password")
        elif auth_type == "api_key":
            auth_config.api_key = auth_params.get("key")
            auth_config.api_key_header = auth_params.get("header", "X-API-Key")
            auth_config.api_key_location = auth_params.get("location", "header")
            auth_config.api_key_param = auth_params.get("param", "api_key")
        elif auth_type == "oauth2":
            auth_config.oauth2_provider = auth_params.get("provider")
        
        return auth_config
    
    async def _prepare_authentication(
        self, 
        request_config: HTTPRequestConfig, 
        credentials: Dict[str, str]
    ) -> None:
        """准备认证信息"""
        if not request_config.auth:
            return
        
        auth = request_config.auth
        
        if auth.auth_type == "bearer":
            # Bearer Token认证
            token = auth.bearer_token or credentials.get("access_token")
            if token:
                request_config.headers["Authorization"] = f"Bearer {token}"
        
        elif auth.auth_type == "basic":
            # Basic认证
            username = auth.username or credentials.get("username")
            password = auth.password or credentials.get("password")
            if username and password:
                import base64
                credentials_str = f"{username}:{password}"
                encoded = base64.b64encode(credentials_str.encode()).decode()
                request_config.headers["Authorization"] = f"Basic {encoded}"
        
        elif auth.auth_type == "api_key":
            # API Key认证
            api_key = auth.api_key or credentials.get("api_key")
            if api_key:
                if auth.api_key_location == "header":
                    request_config.headers[auth.api_key_header] = api_key
                elif auth.api_key_location == "query":
                    request_config.query_params[auth.api_key_param] = api_key
        
        elif auth.auth_type == "oauth2":
            # OAuth2认证（使用外部凭证）
            access_token = credentials.get("access_token")
            if access_token:
                request_config.headers["Authorization"] = f"Bearer {access_token}"
            else:
                raise AuthenticationError("OAuth2 access token not found in credentials")
    
    def _validate_request_config(self, config: HTTPRequestConfig) -> None:
        """验证请求配置"""
        if not config.url:
            raise ValidationError("URL is required")
        
        # 验证URL格式
        try:
            parsed = urlparse(config.url)
            if not parsed.scheme or not parsed.netloc:
                raise ValidationError("Invalid URL format")
        except Exception:
            raise ValidationError("Invalid URL format")
        
        # 验证HTTP方法
        valid_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
        if config.method.upper() not in valid_methods:
            raise ValidationError(f"Invalid HTTP method: {config.method}")
        
        # 验证响应格式
        valid_formats = ["json", "text", "raw"]
        if config.response_format not in valid_formats:
            raise ValidationError(f"Invalid response format: {config.response_format}")
    
    async def _make_http_request(self, config: HTTPRequestConfig) -> httpx.Response:
        """发起HTTP请求"""
        client = await self.get_http_client()
        
        # 准备请求参数
        request_kwargs = {
            "method": config.method,
            "url": config.url,
            "headers": config.headers,
            "params": config.query_params,
            "timeout": httpx.Timeout(config.timeout),
            "follow_redirects": config.follow_redirects
        }
        
        # 添加请求体
        if config.json_data:
            request_kwargs["json"] = config.json_data
        elif config.form_data:
            request_kwargs["data"] = config.form_data
        elif config.raw_data:
            request_kwargs["content"] = config.raw_data
        
        try:
            # 发起请求
            response = await client.request(**request_kwargs)
            
            # 检查状态码
            if response.status_code not in config.expected_status_codes:
                self._handle_http_error(response)
            
            return response
            
        except httpx.TimeoutException as e:
            raise NetworkError(f"Request timeout: {str(e)}")
        except httpx.ConnectError as e:
            raise NetworkError(f"Connection error: {str(e)}")
        except httpx.RequestError as e:
            raise NetworkError(f"Request error: {str(e)}")
    
    async def _process_response(
        self, 
        response: httpx.Response, 
        config: HTTPRequestConfig
    ) -> Any:
        """处理HTTP响应"""
        if config.response_format == "json":
            try:
                return response.json()
            except (json.JSONDecodeError, ValueError) as e:
                raise PermanentError(f"Failed to parse JSON response: {str(e)}")
        
        elif config.response_format == "text":
            return response.text
        
        elif config.response_format == "raw":
            return {
                "content": response.content.hex(),
                "encoding": response.encoding,
                "content_type": response.headers.get("content-type")
            }
        
        else:
            # 默认返回文本
            return response.text
    
    async def test_connection(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """测试HTTP连接
        
        对于HTTP Tool适配器，我们进行一个简单的HEAD请求测试
        """
        try:
            # 简单的连接测试 - 发起HEAD请求到httpbin.org
            test_config = HTTPRequestConfig(
                method="HEAD",
                url="https://httpbin.org/status/200",
                timeout=10.0,
                expected_status_codes=[200]
            )
            
            response = await self._make_http_request(test_config)
            
            return {
                "success": True,
                "provider": self.provider_name,
                "message": "HTTP tool connection test successful",
                "details": {
                    "test_url": test_config.url,
                    "status_code": response.status_code,
                    "response_time_ms": getattr(response, 'elapsed', 0)
                }
            }
            
        except Exception as e:
            logger.error(f"HTTP tool connection test failed: {str(e)}")
            return {
                "success": False,
                "provider": self.provider_name,
                "error": str(e),
                "error_type": type(e).__name__
            }