"""
FastAPI Dependencies for Dependency Injection
依赖注入函数，遵循FastAPI最佳实践
"""

from typing import Any, Dict, Generator, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from app.core.config import Settings, get_settings
from app.core.database import (
    DatabaseManager,
    get_database_manager,
    get_redis,
    get_supabase,
    get_supabase_admin,
)
from app.models import AuthClient, AuthUser
from app.services.auth_service import verify_supabase_token
from app.utils.logger import get_logger

logger = get_logger(__name__)

# HTTP Bearer认证方案
security = HTTPBearer(auto_error=False)


# =============================================================================
# 配置依赖
# =============================================================================


def get_app_settings() -> Settings:
    """获取应用配置（依赖注入）"""
    return get_settings()


# =============================================================================
# 数据库依赖
# =============================================================================


async def get_db_manager() -> DatabaseManager:
    """获取数据库管理器（依赖注入）"""
    manager = get_database_manager()
    if not manager._initialized:
        await manager.initialize()
    return manager


def get_supabase_client() -> Optional[Client]:
    """获取Supabase客户端（依赖注入）"""
    return get_supabase()


def get_supabase_admin_client() -> Optional[Client]:
    """获取Supabase管理员客户端（依赖注入）"""
    return get_supabase_admin()


def get_redis_client() -> Optional[Any]:
    """获取Redis客户端（依赖注入）"""
    return get_redis()


# =============================================================================
# 认证依赖
# =============================================================================


async def get_authorization_header(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[str]:
    """
    获取Authorization头部的token
    优先从request.state获取中间件已提取的token
    """
    # 优先使用中间件存储的 token
    if hasattr(request.state, "access_token") and request.state.access_token:
        return request.state.access_token

    # 否则从头部提取
    if credentials and credentials.scheme.lower() == "bearer":
        return credentials.credentials
    return None


async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(get_authorization_header),
    settings: Settings = Depends(get_app_settings),
) -> Optional[AuthUser]:
    """
    获取当前认证用户（可选认证）
    优先使用中间件已验证的用户信息，避免重复验证
    """
    # 1. 首先检查中间件是否已经验证并存储了用户信息
    if hasattr(request.state, "user") and request.state.user:
        try:
            # 使用中间件已验证的用户数据
            logger.debug("Using cached user from middleware, skipping JWT verification")
            return AuthUser(**request.state.user)
        except Exception as e:
            logger.warning(f"Failed to create AuthUser from request.state: {e}")

    # 2. 如果中间件未验证（例如可选认证的端点），则手动验证
    if not token:
        return None

    if not settings.SUPABASE_AUTH_ENABLED:
        return None

    try:
        user_data = await verify_supabase_token(token)
        if user_data:
            return AuthUser(**user_data)
        return None
    except Exception as e:
        logger.warning(f"Token verification failed: {e}")
        return None


async def get_required_user(
    current_user: Optional[AuthUser] = Depends(get_current_user),
) -> AuthUser:
    """
    获取当前认证用户（必需认证）
    如果未认证则抛出401错误
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


async def get_optional_user(
    current_user: Optional[AuthUser] = Depends(get_current_user),
) -> Optional[AuthUser]:
    """
    获取当前用户（可选）
    不会抛出错误，用于支持游客访问的端点
    """
    return current_user


async def get_user_supabase_client(
    request: Request,
    token: Optional[str] = Depends(get_authorization_header),
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> Optional[Client]:
    """获取用户特定的Supabase客户端（带RLS支持）"""
    # 优先使用中间件存储的 token
    access_token = None
    if hasattr(request.state, "access_token") and request.state.access_token:
        access_token = request.state.access_token
    else:
        access_token = token

    if not access_token:
        return None

    try:
        return db_manager.create_user_client(access_token)
    except Exception as e:
        logger.warning(f"Failed to create user Supabase client: {e}")
        return None


# =============================================================================
# MCP API认证依赖
# =============================================================================


async def get_mcp_api_key(request: Request) -> Optional[str]:
    """从请求中提取MCP API Key"""
    # 1. 检查X-API-Key头部
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return api_key

    # 2. 检查Authorization Bearer头部
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]

    # 3. 检查查询参数（不推荐，仅用于测试）
    api_key = request.query_params.get("api_key")
    if api_key:
        return api_key

    return None


async def get_mcp_client(
    api_key: Optional[str] = Depends(get_mcp_api_key),
    settings: Settings = Depends(get_app_settings),
) -> Optional[AuthClient]:
    """
    获取MCP客户端信息（可选认证）
    返回None表示未提供API Key或验证失败
    """
    if not api_key:
        return None

    if not settings.MCP_API_KEY_REQUIRED:
        return None

    try:
        # 验证API Key
        from app.middleware.auth import mcp_authenticator

        api_key_obj = mcp_authenticator.verify_api_key(api_key)
        if api_key_obj:
            return AuthClient(
                client_id=api_key_obj.id,
                client_name=api_key_obj.client_name,
                scopes=api_key_obj.scopes,
                metadata={
                    "rate_limit_tier": api_key_obj.rate_limit_tier,
                    "active": api_key_obj.active,
                },
            )
        return None
    except Exception as e:
        logger.warning(f"MCP API key verification failed: {e}")
        return None


async def get_required_mcp_client(
    mcp_client: Optional[AuthClient] = Depends(get_mcp_client),
) -> AuthClient:
    """
    获取MCP客户端（必需认证）
    如果未提供有效API Key则抛出401错误
    """
    if not mcp_client:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "unauthorized",
                "message": "Valid MCP API key required",
                "required_auth": "API Key via X-API-Key header or Authorization: Bearer <key>",
            },
        )
    return mcp_client


# =============================================================================
# 路径参数依赖
# =============================================================================


async def get_session_id(session_id: str) -> str:
    """验证并返回会话ID"""
    if not session_id or not session_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Session ID is required"
        )
    return session_id.strip()


async def get_workflow_id(workflow_id: str) -> str:
    """验证并返回工作流ID"""
    if not workflow_id or not workflow_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Workflow ID is required"
        )
    return workflow_id.strip()


async def get_tool_name(tool_name: str) -> str:
    """验证并返回工具名称"""
    if not tool_name or not tool_name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tool name is required")
    return tool_name.strip()


# =============================================================================
# 权限检查依赖
# =============================================================================


def require_scope(required_scope: str):
    """
    创建权限范围检查依赖

    Args:
        required_scope: 所需的权限范围

    Returns:
        依赖函数
    """

    async def check_scope(mcp_client: AuthClient = Depends(get_required_mcp_client)) -> AuthClient:
        """检查MCP客户端是否有所需权限"""
        if "admin" in mcp_client.scopes:
            return mcp_client

        if required_scope not in mcp_client.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "insufficient_scope",
                    "message": f"Required scope: {required_scope}",
                    "your_scopes": mcp_client.scopes,
                    "required_scope": required_scope,
                },
            )

        return mcp_client

    return check_scope


# =============================================================================
# 请求上下文依赖
# =============================================================================


async def get_request_context(
    request: Request,
    current_user: Optional[AuthUser] = Depends(get_optional_user),
    mcp_client: Optional[AuthClient] = Depends(get_mcp_client),
    settings: Settings = Depends(get_app_settings),
) -> Dict[str, Any]:
    """
    获取请求上下文信息
    包含用户信息、客户端信息、IP地址等
    """
    # 获取客户端IP
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    else:
        client_ip = request.headers.get(
            "X-Real-IP", str(request.client.host) if request.client else "unknown"
        )

    context = {
        "request_id": getattr(request.state, "request_id", None),
        "path": request.url.path,
        "method": request.method,
        "client_ip": client_ip,
        "user_agent": request.headers.get("User-Agent"),
        "timestamp": None,  # 会在中间件中设置
        "user": current_user.model_dump() if current_user else None,
        "mcp_client": mcp_client.model_dump() if mcp_client else None,
        "auth_type": None,  # 会在中间件中设置
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
    }

    return context


# =============================================================================
# 限流依赖
# =============================================================================


async def check_rate_limit(
    request: Request, settings: Settings = Depends(get_app_settings)
) -> bool:
    """
    检查请求是否被限流
    这个函数会在中间件中调用，这里提供依赖注入版本
    """
    if not settings.PUBLIC_RATE_LIMIT_ENABLED:
        return True

    try:
        from app.middleware.rate_limit import check_rate_limit_for_request

        allowed, _ = await check_rate_limit_for_request(request)
        return allowed
    except Exception as e:
        logger.warning(f"Rate limit check failed: {e}")
        return True  # 在错误情况下允许请求


# =============================================================================
# 常用组合依赖
# =============================================================================


class CommonDeps:
    """常用依赖组合类"""

    def __init__(
        self,
        settings: Settings = Depends(get_app_settings),
        db_manager: DatabaseManager = Depends(get_db_manager),
        current_user: Optional[AuthUser] = Depends(get_optional_user),
        request_context: Dict[str, Any] = Depends(get_request_context),
    ):
        self.settings = settings
        self.db_manager = db_manager
        self.current_user = current_user
        self.request_context = request_context


class AuthenticatedDeps:
    """需要认证的依赖组合类"""

    def __init__(
        self,
        request: Request,
        settings: Settings = Depends(get_app_settings),
        db_manager: DatabaseManager = Depends(get_db_manager),
        current_user: AuthUser = Depends(get_required_user),
        user_supabase: Optional[Client] = Depends(get_user_supabase_client),
        access_token: Optional[str] = Depends(get_authorization_header),
        request_context: Dict[str, Any] = Depends(get_request_context),
    ):
        self.request = request
        self.settings = settings
        self.db_manager = db_manager
        self.current_user = current_user
        self.user_supabase = user_supabase
        self.access_token = access_token
        self.request_context = request_context

    @property
    def user_data(self) -> Dict[str, Any]:
        """Get user data as dictionary for compatibility"""
        return self.current_user.model_dump() if self.current_user else {}


class MCPDeps:
    """MCP API依赖组合类"""

    def __init__(
        self,
        settings: Settings = Depends(get_app_settings),
        mcp_client: AuthClient = Depends(get_required_mcp_client),
        request_context: Dict[str, Any] = Depends(get_request_context),
    ):
        self.settings = settings
        self.mcp_client = mcp_client
        self.request_context = request_context
