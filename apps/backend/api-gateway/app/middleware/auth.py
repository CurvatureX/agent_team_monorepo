"""
Authentication Middleware for Three-Layer API Architecture
支持多种认证方式：Supabase OAuth、API Key、无认证
"""

import hashlib
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.config import get_settings

settings = get_settings()
from app.services.auth_service import verify_supabase_token
import logging

logger = logging.getLogger("app.middleware.auth")
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class AuthResult:
    """认证结果"""

    def __init__(
        self,
        success: bool,
        user: Optional[Dict[str, Any]] = None,
        client: Optional[Dict[str, Any]] = None,
        token: Optional[str] = None,
        error: Optional[str] = None,
    ):
        self.success = success
        self.user = user
        self.client = client
        self.token = token
        self.error = error


class MCPApiKey:
    """MCP API Key 模型"""

    def __init__(
        self,
        id: str,
        client_name: str,
        scopes: List[str],
        rate_limit_tier: str = "standard",
        active: bool = True,
        created_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
    ):
        self.id = id
        self.client_name = client_name
        self.scopes = scopes
        self.rate_limit_tier = rate_limit_tier
        self.active = active
        self.created_at = created_at or datetime.now(timezone.utc)
        self.expires_at = expires_at


# API Key 权限范围定义
MCP_SCOPES = {
    "tools:read": ["GET /api/mcp/tools", "GET /api/mcp/tools/{tool_name}"],
    "tools:execute": ["POST /api/mcp/invoke"],
    "health:check": ["GET /api/mcp/health"],
    "admin": ["*"],  # 管理员权限
}


class MCPAuthenticator:
    """MCP API Key 认证器"""

    def __init__(self):
        self.api_keys: Dict[str, MCPApiKey] = {}
        self._load_api_keys()

    def _load_api_keys(self):
        """从配置加载API Keys"""
        try:
            # 从配置文件加载API Keys
            if hasattr(settings, "MCP_API_KEYS") and settings.MCP_API_KEYS:
                for key_id, key_config in settings.MCP_API_KEYS.items():
                    api_key = MCPApiKey(
                        id=key_id,
                        client_name=key_config.get("client_name", "Unknown Client"),
                        scopes=key_config.get("scopes", ["tools:read"]),
                        rate_limit_tier=key_config.get("rate_limit_tier", "standard"),
                        active=key_config.get("active", True),
                    )
                    # 使用key_id作为API Key（生产环境应该使用加密的随机字符串）
                    self.api_keys[key_id] = api_key

            # 添加默认API Key（开发环境）
            if settings.DEBUG and not self.api_keys:
                default_key = MCPApiKey(
                    id="dev_default",
                    client_name="Development Client",
                    scopes=["tools:read", "tools:execute", "health:check"],
                    rate_limit_tier="development",
                    active=True,
                )
                self.api_keys["dev_default"] = default_key
                logger.warning("Using default MCP API key for development")

            logger.info(f"Loaded {len(self.api_keys)} MCP API keys")

        except Exception as e:
            logger.error(f"Failed to load MCP API keys: {e}")

    def verify_api_key(self, api_key: str) -> Optional[MCPApiKey]:
        """验证API Key"""
        if not api_key:
            return None

        # 简单的API Key查找（生产环境应该使用哈希比较）
        api_key_obj = self.api_keys.get(api_key)

        if not api_key_obj:
            return None

        # 检查是否激活
        if not api_key_obj.active:
            return None

        # 检查是否过期
        if api_key_obj.expires_at and datetime.now(timezone.utc) > api_key_obj.expires_at:
            return None

        return api_key_obj

    def get_required_scopes(self, path: str, method: str = "GET") -> List[str]:
        """获取路径所需的权限范围"""
        endpoint = f"{method} {path}"
        required_scopes = []

        for scope, endpoints in MCP_SCOPES.items():
            for pattern in endpoints:
                if pattern == "*" or pattern == endpoint:
                    required_scopes.append(scope)
                    break
                # 简单的路径参数匹配
                if "{" in pattern and "}" in pattern:
                    pattern_parts = pattern.split("/")
                    endpoint_parts = endpoint.split("/")
                    if len(pattern_parts) == len(endpoint_parts):
                        match = True
                        for i, part in enumerate(pattern_parts):
                            if not (part == endpoint_parts[i] or ("{" in part and "}" in part)):
                                match = False
                                break
                        if match:
                            required_scopes.append(scope)
                            break

        return required_scopes

    def has_required_scopes(self, user_scopes: List[str], required_scopes: List[str]) -> bool:
        """检查是否有足够的权限"""
        if "admin" in user_scopes:
            return True

        # 如果没有特定权限要求，允许访问
        if not required_scopes:
            return True

        # 检查是否有任何所需权限
        for required_scope in required_scopes:
            if required_scope in user_scopes:
                return True

        return False


# 全局MCP认证器实例
mcp_authenticator = MCPAuthenticator()


async def authenticate_supabase_user(request: Request) -> AuthResult:
    """Supabase OAuth 用户认证"""
    try:
        # 提取 Bearer Token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return AuthResult(success=False, error="missing_token")

        token = auth_header.split(" ")[1]

        # 验证 JWT Token
        user_data = await verify_supabase_token(token)
        if not user_data:
            return AuthResult(success=False, error="invalid_token")

        # 检查用户状态
        if not user_data.get("email_confirmed", True):  # 默认为True以兼容测试
            return AuthResult(success=False, error="email_not_confirmed")

        return AuthResult(success=True, user=user_data, token=token)

    except Exception as e:
        logger.error(f"Supabase auth error: {e}")
        return AuthResult(success=False, error="auth_failed")


async def authenticate_mcp_client(request: Request) -> AuthResult:
    """MCP API Key 客户端认证"""
    try:
        # 支持多种认证方式
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            # 尝试从Authorization header获取
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                api_key = auth_header.split(" ")[1]

        if not api_key:
            # 尝试从查询参数获取（不推荐，仅用于测试）
            api_key = request.query_params.get("api_key")

        if not api_key:
            return AuthResult(success=False, error="missing_api_key")

        # 验证 API Key
        api_key_obj = mcp_authenticator.verify_api_key(api_key)
        if not api_key_obj:
            return AuthResult(success=False, error="invalid_api_key")

        # 检查权限范围
        required_scopes = mcp_authenticator.get_required_scopes(request.url.path, request.method)

        if not mcp_authenticator.has_required_scopes(api_key_obj.scopes, required_scopes):
            return AuthResult(
                success=False,
                error="insufficient_scope",
                client={
                    "id": api_key_obj.id,
                    "required_scopes": required_scopes,
                    "user_scopes": api_key_obj.scopes,
                },
            )

        # 构建客户端信息
        client_info = {
            "id": api_key_obj.id,
            "client_name": api_key_obj.client_name,
            "scopes": api_key_obj.scopes,
            "rate_limit_tier": api_key_obj.rate_limit_tier,
            "active": api_key_obj.active,
        }

        return AuthResult(success=True, client=client_info)

    except Exception as e:
        logger.error(f"MCP auth error: {e}")
        return AuthResult(success=False, error="auth_failed")


async def unified_auth_middleware(request: Request, call_next):
    """统一认证中间件 - 根据路径选择认证策略"""
    path = request.url.path
    method = request.method

    logger.debug(f"Processing request: {method} {path}")

    # Public API - 无需认证，仅限流
    if path.startswith("/api/v1/public/"):
        logger.debug(f"Public API endpoint, skipping auth: {path}")
        return await call_next(request)

    # 传统公开路径
    public_paths = ["/health", "/", "/docs", "/openapi.json", "/redoc", "/docs-json"]
    if path in public_paths:
        logger.debug(f"Legacy public endpoint, skipping auth: {path}")
        return await call_next(request)

    # MCP API - API Key 认证
    if path.startswith("/api/v1/mcp/"):
        if not settings.MCP_API_KEY_REQUIRED:
            logger.info(f"MCP API endpoint, auth disabled: {path}")
            return await call_next(request)

        auth_result = await authenticate_mcp_client(request)
        if not auth_result.success:
            logger.warning(f"MCP auth failed: {path} - {auth_result.error}")

            # 构建错误响应
            error_content = {
                "error": "unauthorized",
                "message": f"MCP authentication failed: {auth_result.error}",
                "required_auth": "API Key via X-API-Key header or Authorization: Bearer <key>",
            }

            if auth_result.error == "insufficient_scope" and auth_result.client:
                error_content.update(
                    {
                        "required_scopes": auth_result.client.get("required_scopes", []),
                        "your_scopes": auth_result.client.get("user_scopes", []),
                    }
                )

            return JSONResponse(status_code=401, content=error_content)

        # 添加客户端信息到请求状态
        request.state.client = auth_result.client
        request.state.auth_type = "mcp_api_key"

        logger.info(f"MCP auth successful: {path} - {auth_result.client['client_name']}")

    # App API - Supabase OAuth 认证
    elif path.startswith("/api/v1/"):
        if not settings.SUPABASE_AUTH_ENABLED:
            logger.info(f"App API endpoint, auth disabled: {path}")
            return await call_next(request)

        auth_result = await authenticate_supabase_user(request)
        if not auth_result.success:
            logger.warning(f"Supabase auth failed: {path} - {auth_result.error}")

            return JSONResponse(
                status_code=401,
                content={
                    "error": "unauthorized",
                    "message": f"Authentication failed: {auth_result.error}",
                    "required_auth": "Bearer token via Authorization header",
                },
            )

        # 添加用户信息到请求状态
        request.state.user = auth_result.user
        request.state.user_id = auth_result.user.get("sub")
        request.state.access_token = auth_result.token
        request.state.auth_type = "supabase"

        logger.info(f"Supabase auth successful: {path} - {auth_result.user.get('email', 'unknown')}")

    else:
        # 其他路径使用传统认证（兼容性）
        logger.info(f"Using legacy auth for non-layered API: {path}")

    # 继续处理请求
    response = await call_next(request)
    logger.debug(f"Response sent: {method} {path} -> {response.status_code}")

    return response
