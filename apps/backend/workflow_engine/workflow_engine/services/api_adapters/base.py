"""
API适配器基类和通用功能
定义统一的API调用接口和错误处理机制
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable, Type, Union
from datetime import datetime, timedelta
import json

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

logger = logging.getLogger(__name__)


# ============================================================================
# 异常类定义
# ============================================================================

class APIError(Exception):
    """API调用错误基类"""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}
        self.timestamp = datetime.now()


class AuthenticationError(APIError):
    """认证错误 - 需要重新授权"""
    pass


class AuthorizationError(APIError):
    """授权错误 - 权限不足"""
    pass


class RateLimitError(APIError):
    """频率限制错误 - 需要等待重试"""
    
    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class TemporaryError(APIError):
    """临时错误 - 可以重试"""
    pass


class PermanentError(APIError):
    """永久错误 - 不应重试"""
    pass


class ValidationError(APIError):
    """参数验证错误"""
    pass


class NetworkError(APIError):
    """网络连接错误"""
    pass


# ============================================================================
# 配置类定义
# ============================================================================

@dataclass
class RetryConfig:
    """重试策略配置"""
    max_retries: int = 3
    backoff_factor: float = 2.0  # 指数退避系数
    max_backoff: float = 60.0    # 最大退避时间(秒)
    min_backoff: float = 1.0     # 最小退避时间(秒)
    retry_on: List[Type[Exception]] = field(default_factory=lambda: [
        TemporaryError, 
        RateLimitError, 
        NetworkError,
        httpx.TimeoutException,
        httpx.ConnectError
    ])
    
    def to_tenacity_retry(self):
        """转换为tenacity重试装饰器"""
        return retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(
                multiplier=self.backoff_factor,
                min=self.min_backoff,
                max=self.max_backoff
            ),
            retry=retry_if_exception_type(tuple(self.retry_on)),
            before_sleep=before_sleep_log(logger, logging.WARNING)
        )


@dataclass
class OAuth2Config:
    """OAuth2配置"""
    client_id: str
    client_secret: str
    auth_url: str
    token_url: str
    revoke_url: Optional[str] = None
    scopes: List[str] = field(default_factory=list)
    redirect_uri: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "auth_url": self.auth_url,
            "token_url": self.token_url,
            "revoke_url": self.revoke_url,
            "scopes": self.scopes,
            "redirect_uri": self.redirect_uri
        }


@dataclass
class HTTPConfig:
    """HTTP客户端配置"""
    timeout: float = 30.0
    max_connections: int = 100
    max_keepalive_connections: int = 20
    keepalive_expiry: float = 5.0
    follow_redirects: bool = True
    verify_ssl: bool = True
    user_agent: str = "WorkflowEngine/1.0"
    
    def to_httpx_limits(self) -> httpx.Limits:
        """转换为httpx连接限制"""
        return httpx.Limits(
            max_connections=self.max_connections,
            max_keepalive_connections=self.max_keepalive_connections,
            keepalive_expiry=self.keepalive_expiry
        )


# ============================================================================
# 通用功能混入类
# ============================================================================

class RetryMixin:
    """重试功能混入类"""
    
    def __init__(self, retry_config: Optional[RetryConfig] = None):
        self.retry_config = retry_config or RetryConfig()
    
    async def call_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """带重试的函数调用"""
        retry_decorator = self.retry_config.to_tenacity_retry()
        
        @retry_decorator
        async def _retry_wrapper():
            return await func(*args, **kwargs)
        
        return await _retry_wrapper()


class RateLimitMixin:
    """限流处理混入类"""
    
    def __init__(self):
        self._rate_limit_info = {}
    
    def check_rate_limit(self, response: httpx.Response, provider: str) -> None:
        """检查并处理API限流"""
        headers = response.headers
        
        # 通用限流头部检查
        rate_limit_remaining = self._get_rate_limit_remaining(headers)
        rate_limit_reset = self._get_rate_limit_reset(headers)
        
        if rate_limit_remaining is not None:
            self._rate_limit_info[provider] = {
                "remaining": rate_limit_remaining,
                "reset_at": rate_limit_reset,
                "checked_at": datetime.now()
            }
        
        # 如果触发限流，抛出RateLimitError
        if response.status_code == 429:
            retry_after = self._get_retry_after(headers)
            raise RateLimitError(
                f"Rate limit exceeded for {provider}",
                retry_after=retry_after,
                status_code=response.status_code,
                response_data=self._safe_json_response(response)
            )
    
    def _get_rate_limit_remaining(self, headers: httpx.Headers) -> Optional[int]:
        """获取剩余API调用次数"""
        # 尝试常见的限流头部
        for header in ["X-RateLimit-Remaining", "X-Rate-Limit-Remaining", "RateLimit-Remaining"]:
            if header in headers:
                try:
                    return int(headers[header])
                except (ValueError, TypeError):
                    continue
        return None
    
    def _get_rate_limit_reset(self, headers: httpx.Headers) -> Optional[datetime]:
        """获取限流重置时间"""
        for header in ["X-RateLimit-Reset", "X-Rate-Limit-Reset", "RateLimit-Reset"]:
            if header in headers:
                try:
                    # 尝试解析Unix时间戳
                    timestamp = int(headers[header])
                    return datetime.fromtimestamp(timestamp)
                except (ValueError, TypeError):
                    continue
        return None
    
    def _get_retry_after(self, headers: httpx.Headers) -> Optional[int]:
        """获取重试等待时间"""
        if "Retry-After" in headers:
            try:
                return int(headers["Retry-After"])
            except (ValueError, TypeError):
                pass
        return None
    
    def _safe_json_response(self, response: httpx.Response) -> Dict[str, Any]:
        """安全地解析JSON响应"""
        try:
            return response.json()
        except (json.JSONDecodeError, ValueError):
            return {"raw_response": response.text[:500]}


class HTTPClientMixin:
    """HTTP客户端功能混入类"""
    
    def __init__(self, http_config: Optional[HTTPConfig] = None):
        self.http_config = http_config or HTTPConfig()
        self._client: Optional[httpx.AsyncClient] = None
    
    async def get_http_client(self) -> httpx.AsyncClient:
        """获取HTTP客户端实例"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.http_config.timeout),
                limits=self.http_config.to_httpx_limits(),
                follow_redirects=self.http_config.follow_redirects,
                verify=self.http_config.verify_ssl,
                headers={"User-Agent": self.http_config.user_agent}
            )
        return self._client
    
    async def close_http_client(self):
        """关闭HTTP客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def make_http_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        **kwargs
    ) -> httpx.Response:
        """发起HTTP请求"""
        client = await self.get_http_client()
        
        try:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                data=data,
                **kwargs
            )
            return response
        except httpx.TimeoutException as e:
            raise NetworkError(f"Request timeout: {str(e)}")
        except httpx.ConnectError as e:
            raise NetworkError(f"Connection error: {str(e)}")
        except httpx.RequestError as e:
            raise NetworkError(f"Request error: {str(e)}")


# ============================================================================
# API适配器抽象基类
# ============================================================================

class APIAdapter(ABC, RetryMixin, RateLimitMixin, HTTPClientMixin):
    """API适配器抽象基类
    
    定义统一的API调用接口，所有具体的API适配器都应继承此类。
    提供重试、限流、HTTP客户端等通用功能。
    """
    
    def __init__(
        self,
        retry_config: Optional[RetryConfig] = None,
        http_config: Optional[HTTPConfig] = None
    ):
        RetryMixin.__init__(self, retry_config)
        RateLimitMixin.__init__(self)
        HTTPClientMixin.__init__(self, http_config)
        
        self.provider_name = self.__class__.__name__.lower().replace("adapter", "")
        self._last_request_time: Optional[datetime] = None
    
    @abstractmethod
    async def call(
        self, 
        operation: str, 
        parameters: Dict[str, Any],
        credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """统一的API调用接口
        
        Args:
            operation: 操作名称 (如 "list_events", "create_issue")
            parameters: 操作参数
            credentials: 认证凭证
            
        Returns:
            API响应数据
            
        Raises:
            APIError: API调用失败时抛出相应的错误
        """
        pass
    
    @abstractmethod
    def get_oauth2_config(self) -> OAuth2Config:
        """获取OAuth2配置
        
        Returns:
            OAuth2配置对象
        """
        pass
    
    @abstractmethod
    def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """验证凭证有效性
        
        Args:
            credentials: 要验证的凭证
            
        Returns:
            凭证是否有效
        """
        pass
    
    def get_supported_operations(self) -> List[str]:
        """获取支持的操作列表
        
        Returns:
            支持的操作名称列表
        """
        if hasattr(self, 'OPERATIONS'):
            return list(self.OPERATIONS.keys())
        return []
    
    def get_operation_description(self, operation: str) -> Optional[str]:
        """获取操作描述
        
        Args:
            operation: 操作名称
            
        Returns:
            操作描述，如果操作不存在则返回None
        """
        if hasattr(self, 'OPERATIONS'):
            return self.OPERATIONS.get(operation)
        return None
    
    async def test_connection(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """测试API连接
        
        Args:
            credentials: 认证凭证
            
        Returns:
            测试结果字典，包含success字段和相关信息
        """
        try:
            # 子类可以重写此方法实现具体的连接测试
            result = await self._default_connection_test(credentials)
            return {
                "success": True,
                "provider": self.provider_name,
                "message": "Connection test successful",
                "details": result
            }
        except Exception as e:
            logger.error(f"Connection test failed for {self.provider_name}: {str(e)}")
            return {
                "success": False,
                "provider": self.provider_name,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def _default_connection_test(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """默认的连接测试实现
        
        子类可以重写此方法实现具体的测试逻辑。
        """
        # 默认只验证凭证格式
        is_valid = self.validate_credentials(credentials)
        if not is_valid:
            raise ValidationError("Invalid credentials format")
        
        return {"credentials_valid": True}
    
    def _handle_http_error(self, response: httpx.Response) -> None:
        """处理HTTP响应错误
        
        Args:
            response: HTTP响应对象
            
        Raises:
            APIError: 根据状态码抛出相应的错误
        """
        status_code = response.status_code
        response_data = self._safe_json_response(response)
        
        # 检查限流
        self.check_rate_limit(response, self.provider_name)
        
        # 根据状态码分类错误
        if status_code == 401:
            raise AuthenticationError(
                "Authentication failed - invalid or expired credentials",
                status_code=status_code,
                response_data=response_data
            )
        elif status_code == 403:
            raise AuthorizationError(
                "Authorization failed - insufficient permissions",
                status_code=status_code,
                response_data=response_data
            )
        elif status_code == 429:
            # 限流错误已在check_rate_limit中处理
            pass
        elif 400 <= status_code < 500:
            # 客户端错误 - 通常不应重试
            raise PermanentError(
                f"Client error: {response_data.get('message', 'Unknown error')}",
                status_code=status_code,
                response_data=response_data
            )
        elif 500 <= status_code < 600:
            # 服务器错误 - 可以重试
            raise TemporaryError(
                f"Server error: {response_data.get('message', 'Internal server error')}",
                status_code=status_code,
                response_data=response_data
            )
        else:
            # 未知错误
            raise APIError(
                f"Unexpected status code: {status_code}",
                status_code=status_code,
                response_data=response_data
            )
    
    def _prepare_headers(self, credentials: Dict[str, str], extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """准备HTTP请求头
        
        Args:
            credentials: 认证凭证
            extra_headers: 额外的请求头
            
        Returns:
            完整的请求头字典
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": self.http_config.user_agent
        }
        
        # 添加认证头部
        if "access_token" in credentials:
            headers["Authorization"] = f"Bearer {credentials['access_token']}"
        elif "api_key" in credentials:
            # API密钥认证，具体格式由子类决定
            headers.update(self._prepare_api_key_headers(credentials))
        
        # 合并额外头部
        if extra_headers:
            headers.update(extra_headers)
        
        return headers
    
    def _prepare_api_key_headers(self, credentials: Dict[str, str]) -> Dict[str, str]:
        """准备API密钥认证头部
        
        子类可以重写此方法实现特定的API密钥认证格式。
        
        Args:
            credentials: 包含API密钥的凭证
            
        Returns:
            API密钥认证头部
        """
        return {"Authorization": f"Bearer {credentials['api_key']}"}
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close_http_client()


# ============================================================================
# 工厂模式支持
# ============================================================================

class APIAdapterRegistry:
    """API适配器注册表"""
    
    _adapters: Dict[str, Type[APIAdapter]] = {}
    
    @classmethod
    def register(cls, name: str, adapter_class: Type[APIAdapter]):
        """注册API适配器
        
        Args:
            name: 适配器名称
            adapter_class: 适配器类
        """
        cls._adapters[name] = adapter_class
        logger.info(f"Registered API adapter: {name}")
    
    @classmethod
    def get_adapter_class(cls, name: str) -> Type[APIAdapter]:
        """获取API适配器类
        
        Args:
            name: 适配器名称
            
        Returns:
            适配器类
            
        Raises:
            ValueError: 适配器不存在时抛出
        """
        if name not in cls._adapters:
            raise ValueError(f"Unknown API adapter: {name}")
        return cls._adapters[name]
    
    @classmethod
    def create_adapter(
        cls, 
        name: str, 
        retry_config: Optional[RetryConfig] = None,
        http_config: Optional[HTTPConfig] = None
    ) -> APIAdapter:
        """创建API适配器实例
        
        Args:
            name: 适配器名称
            retry_config: 重试配置
            http_config: HTTP配置
            
        Returns:
            适配器实例
        """
        adapter_class = cls.get_adapter_class(name)
        return adapter_class(retry_config=retry_config, http_config=http_config)
    
    @classmethod
    def list_adapters(cls) -> List[str]:
        """列出所有已注册的适配器
        
        Returns:
            适配器名称列表
        """
        return list(cls._adapters.keys())


# 适配器注册装饰器
def register_adapter(name: str):
    """适配器注册装饰器
    
    Usage:
        @register_adapter("google_calendar")
        class GoogleCalendarAdapter(APIAdapter):
            pass
    """
    def decorator(adapter_class: Type[APIAdapter]):
        APIAdapterRegistry.register(name, adapter_class)
        return adapter_class
    return decorator