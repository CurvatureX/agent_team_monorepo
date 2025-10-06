"""
Authentication Middleware for Three-Layer API Architecture
支持多种认证方式：Supabase OAuth、API Key、无认证
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.services.auth_service import verify_supabase_token
from fastapi import Request
from fastapi.responses import JSONResponse

settings = get_settings()
logger = logging.getLogger("app.middleware.auth")


def log_jwt_issue_summary(error_type: str, client_info: dict, additional_data: dict = None):
    """
    Log JWT issues in a structured format for monitoring and alerting

    Args:
        error_type: Type of JWT issue (malformed_token, empty_token, etc.)
        client_info: Client information (IP, user agent, path)
        additional_data: Additional data specific to the error type
    """
    summary = {
        "event": "jwt_auth_failure",
        "error_type": error_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "client_info": client_info,
    }

    if additional_data:
        summary.update(additional_data)

    # Use a specific logger for monitoring systems to pick up
    monitoring_logger = logging.getLogger("app.monitoring.jwt_auth")
    monitoring_logger.warning(f"JWT_AUTH_FAILURE: {summary}")

    return summary


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
    "tools:read": ["GET /api/v1/mcp/tools", "GET /api/v1/mcp/tools/{tool_name}"],
    "tools:execute": ["POST /api/v1/mcp/invoke"],
    "health:check": ["GET /api/v1/mcp/health"],
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


def _validate_jwt_format_middleware(token: str) -> bool:
    """
    Validate JWT token format in middleware
    JWT should have exactly 3 segments separated by dots
    """
    if not token or not isinstance(token, str):
        return False

    # JWT tokens should have exactly 3 parts separated by dots
    parts = token.split(".")
    if len(parts) != 3:
        return False

    # Each part should be non-empty
    if any(not part or part.strip() == "" for part in parts):
        return False

    # Basic length check - JWT parts are typically base64 encoded and have minimum lengths
    if any(len(part) < 4 for part in parts):
        return False

    return True


async def authenticate_supabase_user(request: Request) -> AuthResult:
    """Supabase OAuth 用户认证"""
    try:
        # Get client info for logging
        client_ip = request.headers.get(
            "X-Real-IP", request.headers.get("X-Forwarded-For", "unknown")
        )
        user_agent = request.headers.get("User-Agent", "unknown")[:100]  # Truncate long agents

        # 提取 Bearer Token
        auth_header = request.headers.get("Authorization")

        # Log authorization header analysis
        header_info = {
            "path": request.url.path,
            "method": request.method,
            "client_ip": client_ip.split(",")[0].strip() if client_ip != "unknown" else "unknown",
            "user_agent_prefix": user_agent,
            "has_auth_header": bool(auth_header),
            "auth_header_length": len(auth_header) if auth_header else 0,
            "starts_with_bearer": auth_header.startswith("Bearer ") if auth_header else False,
        }
        logger.debug(f"Auth request analysis: {header_info}")

        if not auth_header or not auth_header.startswith("Bearer "):
            logger.info(f"Missing or invalid Authorization header: {header_info}")
            return AuthResult(success=False, error="missing_token")

        # Safe token extraction to handle malformed Authorization headers
        parts = auth_header.split(" ", 1)  # Split only on first space
        if len(parts) != 2:
            logger.warning(
                f"Malformed Authorization header: missing token after 'Bearer'. "
                f"Header: '{auth_header[:50]}...', Parts count: {len(parts)}, "
                f"Client: {header_info['client_ip']}"
            )
            return AuthResult(success=False, error="malformed_auth_header")

        token = parts[1].strip()
        if not token:
            logger.warning(
                f"Empty token in Authorization header. "
                f"Header: '{auth_header[:50]}...', Token after strip: '{token}', "
                f"Client: {header_info['client_ip']}"
            )

            # Log for monitoring systems
            log_jwt_issue_summary(
                error_type="empty_jwt_token",
                client_info={
                    "ip": header_info["client_ip"],
                    "user_agent": header_info["user_agent_prefix"],
                    "path": header_info["path"],
                    "method": header_info["method"],
                },
                additional_data={
                    "auth_header_preview": auth_header[:50] + "..."
                    if len(auth_header) > 50
                    else auth_header
                },
            )

            return AuthResult(success=False, error="empty_token")

        # Log token extraction details
        token_details = {
            "token_length": len(token),
            "token_prefix": token[:20] + "..." if len(token) > 20 else token,
            "token_suffix": "..." + token[-10:] if len(token) > 30 else "",
            "segment_count": len(token.split(".")),
            "appears_base64": all(c.isalnum() or c in "-_=" for c in token.replace(".", "")),
        }
        logger.debug(f"Token extraction details: {token_details}")

        # Early validation of JWT format to prevent malformed tokens from reaching Supabase
        if not _validate_jwt_format_middleware(token):
            # Log detailed information about malformed tokens for pattern analysis
            malformed_pattern = {
                "error_type": "malformed_jwt_token",
                "client_ip": header_info["client_ip"],
                "user_agent": header_info["user_agent_prefix"],
                "path": header_info["path"],
                "token_analysis": token_details,
                "common_issues": {
                    "too_few_segments": len(token.split(".")) < 3,
                    "too_many_segments": len(token.split(".")) > 3,
                    "empty_segments": any(not seg.strip() for seg in token.split(".")),
                    "too_short_segments": any(len(seg) < 4 for seg in token.split(".")),
                },
            }
            logger.warning(f"Malformed JWT token pattern detected: {malformed_pattern}")

            # Log for monitoring systems
            log_jwt_issue_summary(
                error_type="malformed_jwt_token",
                client_info={
                    "ip": header_info["client_ip"],
                    "user_agent": header_info["user_agent_prefix"],
                    "path": header_info["path"],
                    "method": header_info["method"],
                },
                additional_data={
                    "token_length": token_details["token_length"],
                    "segment_count": token_details["segment_count"],
                    "pattern_analysis": malformed_pattern["common_issues"],
                },
            )

            return AuthResult(success=False, error="malformed_token")

        # 验证 JWT Token
        user_data = await verify_supabase_token(token)
        if not user_data:
            logger.info(
                f"JWT token validation failed with Supabase. "
                f"Client: {header_info['client_ip']}, Path: {header_info['path']}, "
                f"Token length: {len(token)}, Segments: {len(token.split('.'))}"
            )
            return AuthResult(success=False, error="invalid_token")

        # 检查用户状态
        if not user_data.get("email_confirmed", True):  # 默认为True以兼容测试
            logger.info(
                f"Email not confirmed for user: {user_data.get('email', 'unknown')} "
                f"from {header_info['client_ip']}"
            )
            return AuthResult(success=False, error="email_not_confirmed")

        # Log successful authentication
        logger.info(
            f"Successful JWT authentication: user={user_data.get('email', 'unknown')}, "
            f"client={header_info['client_ip']}, path={header_info['path']}"
        )

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
                # Safe token extraction to handle malformed Authorization headers
                parts = auth_header.split(" ", 1)  # Split only on first space
                if len(parts) == 2:
                    api_key = parts[1].strip()
                    if not api_key:
                        api_key = None  # Empty token

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
        # Exception: Internal endpoints for service-to-service communication
        internal_endpoints = ["/api/v1/mcp/tools/internal", "/api/v1/mcp/invoke/internal"]
        if path in internal_endpoints:
            logger.info(f"🔓 Internal MCP endpoint, skipping auth: {path}")
            return await call_next(request)

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

            # Provide more specific error messages for different failure types
            if auth_result.error in ["malformed_token", "malformed_auth_header", "empty_token"]:
                error_messages = {
                    "malformed_token": (
                        "Invalid JWT token format: "
                        "token must contain exactly 3 segments separated by dots"
                    ),
                    "malformed_auth_header": (
                        "Malformed Authorization header: " "format must be 'Bearer <token>'"
                    ),
                    "empty_token": (
                        "Empty token in Authorization header: " "token cannot be blank"
                    ),
                }
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "bad_request",
                        "message": error_messages.get(auth_result.error, "Invalid request format"),
                        "required_auth": "Bearer token via Authorization header",
                    },
                )
            else:
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

        logger.info(
            f"Supabase auth successful: {path} - {auth_result.user.get('email', 'unknown')}"
        )

    else:
        # 其他路径使用传统认证（兼容性）
        logger.info(f"Using legacy auth for non-layered API: {path}")

    # 继续处理请求
    response = await call_next(request)
    logger.debug(f"Response sent: {method} {path} -> {response.status_code}")

    return response
