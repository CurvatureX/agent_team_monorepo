"""
Rate Limiting Middleware for Three-Layer API Architecture
支持按路径前缀、用户ID、IP地址的分层限流策略
"""

import json
import time

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
from typing import Any, Dict, Optional

from app.core.config import get_settings

settings = get_settings()
import logging

logger = logging.getLogger("app.middleware.rate_limit")
from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse


class RateLimitConfig:
    """限流配置管理"""

    # Public API 限流配置 (按IP地址)
    PUBLIC_LIMITS = {
        "global": "1000/hour",  # 全局限制
        "/api/v1/public/health": "100/minute",  # 健康检查
        "/api/v1/public/status": "60/minute",  # 服务状态
        "/api/v1/public/docs": "10/minute",  # 文档访问
        "/api/v1/public/validation": "30/minute",  # 验证服务
    }

    # App API 用户限流配置 (按用户ID)
    APP_LIMITS = {
        "authenticated_user": "10000/hour",  # 认证用户全局限制
        "/api/v1/app/chat/stream": "100/hour",  # 聊天流式接口
        "/api/v1/app/sessions": "1000/hour",  # 会话操作
        "/api/v1/app/workflows": "500/hour",  # 工作流 CRUD 操作
        "/api/v1/app/workflows/execute": "100/hour",  # 工作流执行
        "/api/v1/app/executions": "200/hour",  # 执行状态查询
        "/api/v1/app/auth": "200/hour",  # 用户认证相关
    }

    # MCP API 客户端限流配置 (按API Key)
    MCP_LIMITS = {
        "api_client": "50000/hour",  # API 客户端全局限制
        "/api/v1/mcp/invoke": "1000/hour",  # 工具调用
        "/api/v1/mcp/tools": "5000/hour",  # 工具列表查询
        "/api/v1/mcp/health": "1000/hour",  # 健康检查
    }


class RateLimiter:
    """Redis based rate limiter with sliding window algorithm"""

    def __init__(self):
        self.redis_client = None
        self._init_redis()

    def _init_redis(self):
        """初始化Redis连接"""
        try:
            if REDIS_AVAILABLE and settings.REDIS_URL:
                self.redis_client = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                )
                # 测试连接
                self.redis_client.ping()
                logger.info("Rate limiter Redis connected")
            else:
                if not REDIS_AVAILABLE:
                    logger.warning("Redis module not available, rate limiting disabled")
                else:
                    logger.warning("Redis URL not configured, rate limiting disabled")
        except Exception as e:
            logger.error(f"Failed to connect to Redis for rate limiting: {e}")
            self.redis_client = None

    def _parse_limit(self, limit_str: str) -> tuple[int, int]:
        """解析限流配置字符串，返回 (count, seconds)"""
        parts = limit_str.split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid limit format: {limit_str}")

        count = int(parts[0])
        time_unit = parts[1].lower()

        if time_unit == "second":
            seconds = 1
        elif time_unit == "minute":
            seconds = 60
        elif time_unit == "hour":
            seconds = 3600
        elif time_unit == "day":
            seconds = 86400
        else:
            raise ValueError(f"Unsupported time unit: {time_unit}")

        return count, seconds

    async def check_rate_limit(
        self, key: str, limit_str: str, request: Request
    ) -> tuple[bool, Dict[str, Any]]:
        """
        检查是否超过限流

        Returns:
            (allowed: bool, info: dict)
        """
        if not self.redis_client:
            # Redis不可用时允许所有请求
            return True, {"status": "no_limit", "reason": "redis_unavailable"}

        try:
            count, window_seconds = self._parse_limit(limit_str)
            current_time = int(time.time())
            window_start = current_time - window_seconds

            # 使用滑动窗口算法
            pipe = self.redis_client.pipeline()

            # 移除过期的记录
            pipe.zremrangebyscore(key, 0, window_start)

            # 获取当前窗口内的请求数
            pipe.zcard(key)

            # 添加当前请求
            pipe.zadd(key, {f"{current_time}:{hash(str(request.url))}": current_time})

            # 设置过期时间
            pipe.expire(key, window_seconds + 10)

            results = pipe.execute()
            current_count = results[1]  # zcard 的结果

            allowed = current_count < count

            info = {
                "status": "allowed" if allowed else "rejected",
                "current_count": current_count,
                "limit": count,
                "window_seconds": window_seconds,
                "reset_time": current_time + (window_seconds - (current_time % window_seconds)),
                "retry_after": 1 if not allowed else None,
            }

            return allowed, info

        except Exception as e:
            logger.error(f"Rate limit check error [{key}]: {e}")
            # Redis错误时允许请求
            return True, {"status": "error", "reason": str(e)}


# 全局限流器实例
rate_limiter = RateLimiter()


def get_client_identifier(request: Request) -> str:
    """获取客户端标识符"""
    # 优先使用用户ID
    if hasattr(request.state, "user") and request.state.user:
        return f"user:{request.state.user.get('sub', 'unknown')}"

    # 其次使用API客户端ID
    if hasattr(request.state, "client") and request.state.client:
        return f"client:{request.state.client.get('id', 'unknown')}"

    # 最后使用IP地址
    return get_ip_address(request)


def get_ip_address(request: Request) -> str:
    """获取真实IP地址"""
    # 检查代理头
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # 取第一个IP（客户端真实IP）
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # 回退到直连IP
    return str(request.client.host) if request.client else "unknown"


async def check_rate_limit_for_request(request: Request) -> tuple[bool, Dict[str, Any]]:
    """为请求检查限流状态"""
    path = request.url.path

    # 确定限流配置和标识符前缀
    if path.startswith("/api/v1/public/"):
        limits = RateLimitConfig.PUBLIC_LIMITS
        identifier = f"ip:{get_ip_address(request)}"
        layer = "public"
    elif path.startswith("/api/v1/app/"):
        limits = RateLimitConfig.APP_LIMITS
        user_id = getattr(request.state, "user", {}).get("sub", "anonymous")
        identifier = f"user:{user_id}"
        layer = "app"
    elif path.startswith("/api/v1/mcp/"):
        limits = RateLimitConfig.MCP_LIMITS
        client_id = getattr(request.state, "client", {}).get("id", "anonymous")
        identifier = f"client:{client_id}"
        layer = "mcp"
    else:
        # 非三层API路径，不限流
        return True, {"status": "no_limit", "reason": "non_layered_api"}

    # 检查特定路径限制
    specific_limit = limits.get(path)
    if specific_limit:
        key = f"rate_limit:{layer}:{identifier}:{path}"
        allowed, info = await rate_limiter.check_rate_limit(key, specific_limit, request)
        if not allowed:
            info["limit_type"] = "path_specific"
            info["path"] = path
            return False, info

    # 检查全局限制
    global_keys = [k for k in limits.keys() if not k.startswith("/")]
    if global_keys:
        global_key = global_keys[0]
        global_limit = limits[global_key]
        key = f"rate_limit:{layer}:{identifier}:global"
        allowed, info = await rate_limiter.check_rate_limit(key, global_limit, request)
        if not allowed:
            info["limit_type"] = "global"
            info["layer"] = layer
            return False, info

    return True, {"status": "allowed", "layer": layer}


async def rate_limit_middleware(request: Request, call_next):
    """三层API限流中间件"""

    # 跳过不需要限流的路径
    if not settings.PUBLIC_RATE_LIMIT_ENABLED:
        return await call_next(request)

    # 检查限流
    allowed, info = await check_rate_limit_for_request(request)

    if not allowed:
        logger.warning(f"Rate limit exceeded: {request.method} {request.url.path} "
                      f"[{info.get('limit_type', 'unknown')}] "
                      f"{info.get('current_count', 0)}/{info.get('limit', 0)}")

        # 构建限流响应
        headers = {}
        if info.get("retry_after"):
            headers["Retry-After"] = str(info["retry_after"])

        # 添加限流信息头
        headers.update(
            {
                "X-RateLimit-Limit": str(info.get("limit", 0)),
                "X-RateLimit-Remaining": str(
                    max(0, info.get("limit", 0) - info.get("current_count", 0))
                ),
                "X-RateLimit-Reset": str(info.get("reset_time", 0)),
            }
        )

        return JSONResponse(
            status_code=429,
            content={
                "error": "rate_limit_exceeded",
                "message": f"Rate limit exceeded for {info.get('limit_type', 'unknown')} requests",
                "limit": info.get("limit"),
                "current": info.get("current_count"),
                "reset_time": info.get("reset_time"),
                "retry_after": info.get("retry_after"),
            },
            headers=headers,
        )

    # 允许请求继续
    response = await call_next(request)

    # 添加限流信息到响应头
    if info.get("limit"):
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, info["limit"] - info.get("current_count", 0))
        )
        if info.get("reset_time"):
            response.headers["X-RateLimit-Reset"] = str(info["reset_time"])

    return response
