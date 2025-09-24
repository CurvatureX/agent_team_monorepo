"""
External API Call Logger Service
记录外部API调用的日志、性能指标和分析数据
"""

import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from supabase import Client, create_client

from .credential_encryption import CredentialEncryption

logger = logging.getLogger(__name__)


# ============================================================================
# 数据模型定义
# ============================================================================


@dataclass
class APICallLogEntry:
    """API调用日志条目"""

    user_id: str
    provider: str
    operation: str
    api_endpoint: str
    http_method: str
    success: bool
    status_code: Optional[int] = None
    response_time_ms: Optional[int] = None
    workflow_execution_id: Optional[str] = None
    node_id: Optional[str] = None
    request_data: Optional[Dict[str, Any]] = None
    response_data: Optional[Dict[str, Any]] = None
    request_headers: Optional[Dict[str, str]] = None
    response_headers: Optional[Dict[str, str]] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    rate_limit_remaining: Optional[int] = None
    rate_limit_reset_at: Optional[datetime] = None
    called_at: Optional[datetime] = None

    def __post_init__(self):
        """后处理初始化"""
        if self.called_at is None:
            self.called_at = datetime.now(timezone.utc)

        # 清理敏感数据
        self.request_data = self._sanitize_data(self.request_data)
        self.request_headers = self._sanitize_headers(self.request_headers)
        self.response_headers = self._sanitize_headers(self.response_headers)

    def _sanitize_data(self, data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """清理请求数据中的敏感信息"""
        if not data:
            return data

        sensitive_fields = {
            "password",
            "secret",
            "key",
            "token",
            "auth",
            "authorization",
            "api_key",
            "access_token",
            "refresh_token",
            "client_secret",
            "private_key",
            "credential",
            "credentials",
        }

        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in sensitive_fields):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_data(value)
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                sanitized[key] = [self._sanitize_data(item) for item in value]
            else:
                sanitized[key] = value

        return sanitized

    def _sanitize_headers(self, headers: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
        """清理请求头中的敏感信息"""
        if not headers:
            return headers

        sensitive_headers = {
            "authorization",
            "x-api-key",
            "x-auth-token",
            "cookie",
            "x-access-token",
            "x-refresh-token",
            "bearer",
        }

        sanitized = {}
        for key, value in headers.items():
            if key.lower() in sensitive_headers:
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value

        return sanitized


# ============================================================================
# API调用日志记录器
# ============================================================================


class APICallLogger:
    """外部API调用日志记录器

    负责记录所有外部API调用的详细信息，包括：
    - 请求和响应数据
    - 性能指标
    - 错误信息
    - 限流信息
    - 重试次数
    """

    def __init__(self, database_session: Optional[object] = None):
        """初始化API调用日志记录器

        Args:
            database_session: 数据库会话，如果不提供则使用默认会话
        """
        # Deprecated param kept for compatibility; use Supabase client instead
        self.db_session = None
        import os

        self.supabase: Optional[Client] = None
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SECRET_KEY")
        if supabase_url and supabase_key:
            try:
                self.supabase = create_client(supabase_url, supabase_key)
            except Exception as e:
                logger.error(f"Failed to init Supabase client: {e}")
                self.supabase = None
        self.encryption_service: Optional[CredentialEncryption] = None

    async def log_api_call(
        self,
        user_id: str,
        provider: str,
        operation: str,
        api_endpoint: str,
        http_method: str = "POST",
        success: bool = True,
        status_code: Optional[int] = None,
        response_time_ms: Optional[int] = None,
        workflow_execution_id: Optional[str] = None,
        node_id: Optional[str] = None,
        request_data: Optional[Dict[str, Any]] = None,
        response_data: Optional[Dict[str, Any]] = None,
        request_headers: Optional[Dict[str, str]] = None,
        response_headers: Optional[Dict[str, str]] = None,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        retry_count: int = 0,
        rate_limit_remaining: Optional[int] = None,
        rate_limit_reset_at: Optional[datetime] = None,
    ) -> bool:
        """记录API调用日志

        Args:
            user_id: 用户ID
            provider: API提供商
            operation: 操作类型
            api_endpoint: API端点URL
            http_method: HTTP方法
            success: 是否成功
            status_code: HTTP状态码
            response_time_ms: 响应时间（毫秒）
            workflow_execution_id: 工作流执行ID
            node_id: 节点ID
            request_data: 请求数据（会被清理）
            response_data: 响应数据
            request_headers: 请求头（会被清理）
            response_headers: 响应头（会被清理）
            error_type: 错误类型
            error_message: 错误消息
            retry_count: 重试次数
            rate_limit_remaining: 剩余API调用次数
            rate_limit_reset_at: 限流重置时间

        Returns:
            是否成功记录日志
        """
        try:
            # 创建日志条目
            log_entry = APICallLogEntry(
                user_id=user_id,
                provider=provider,
                operation=operation,
                api_endpoint=api_endpoint,
                http_method=http_method,
                success=success,
                status_code=status_code,
                response_time_ms=response_time_ms,
                workflow_execution_id=workflow_execution_id,
                node_id=node_id,
                request_data=request_data,
                response_data=response_data,
                request_headers=request_headers,
                response_headers=response_headers,
                error_type=error_type,
                error_message=error_message,
                retry_count=retry_count,
                rate_limit_remaining=rate_limit_remaining,
                rate_limit_reset_at=rate_limit_reset_at,
            )

            # 存储到数据库
            return await self._store_log_entry(log_entry)

        except Exception as e:
            logger.error(f"Failed to log API call: {str(e)}")
            return False

    async def _store_log_entry(self, log_entry: APICallLogEntry) -> bool:
        """存储日志条目到数据库"""
        try:
            if not self.supabase:
                logger.error("Supabase client not initialized for APICallLogger")
                return False

            record = {
                "user_id": log_entry.user_id,
                "provider": log_entry.provider,
                "operation": log_entry.operation,
                "api_endpoint": log_entry.api_endpoint,
                "http_method": log_entry.http_method,
                "success": log_entry.success,
                "status_code": log_entry.status_code,
                "response_time_ms": log_entry.response_time_ms,
                "workflow_execution_id": log_entry.workflow_execution_id,
                "node_id": log_entry.node_id,
                "request_data": log_entry.request_data,
                "response_data": log_entry.response_data,
                "request_headers": log_entry.request_headers,
                "response_headers": log_entry.response_headers,
                "error_type": log_entry.error_type,
                "error_message": log_entry.error_message,
                "retry_count": log_entry.retry_count,
                "rate_limit_remaining": log_entry.rate_limit_remaining,
                "rate_limit_reset_at": log_entry.rate_limit_reset_at.isoformat()
                if log_entry.rate_limit_reset_at
                else None,
                "called_at": log_entry.called_at.isoformat() if log_entry.called_at else None,
            }

            self.supabase.table("external_api_call_logs").insert(record).execute()
            logger.debug(
                f"Successfully logged API call: {log_entry.provider}.{log_entry.operation} for user {log_entry.user_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to store API call log to database: {str(e)}")
            if self.db_session is None and "db" in locals():
                # 如果是我们创建的会话，进行回滚
                try:
                    db.rollback()
                except:
                    pass
            return False

    async def get_api_call_stats(
        self, user_id: str, provider: Optional[str] = None, time_range_hours: int = 24
    ) -> Dict[str, Any]:
        """获取API调用统计信息

        Args:
            user_id: 用户ID
            provider: API提供商（可选）
            time_range_hours: 时间范围（小时）

        Returns:
            统计信息字典
        """
        try:
            if not self.supabase:
                return {
                    "user_id": user_id,
                    "time_range_hours": time_range_hours,
                    "providers": [],
                    "total": {},
                }

            # Calculate time range
            from datetime import datetime, timedelta

            start_time = (datetime.now() - timedelta(hours=time_range_hours)).isoformat()

            # Get aggregate stats using raw SQL query
            query = f"""
            SELECT
                provider,
                COUNT(*) as call_count,
                SUM(CASE WHEN success THEN 1 ELSE 0 END) as success_count,
                SUM(CASE WHEN success THEN 0 ELSE 1 END) as failure_count,
                AVG(response_time_ms) as avg_response_time,
                SUM(tokens_used) as total_tokens,
                SUM(cost_usd) as total_cost
            FROM api_call_logs
            WHERE user_id = '{user_id}'
            AND created_at >= '{start_time}'
            GROUP BY provider
            ORDER BY call_count DESC
            """

            # Execute the query using rpc
            result = self.supabase.rpc("execute_sql", {"query": query}).execute()

            providers = []
            total_stats = {
                "total_calls": 0,
                "total_successes": 0,
                "total_failures": 0,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
            }

            for row in result.data or []:
                provider_stats = {
                    "provider": row["provider"],
                    "calls": int(row["call_count"]),
                    "successes": int(row["success_count"]),
                    "failures": int(row["failure_count"]),
                    "avg_response_time_ms": float(row["avg_response_time"] or 0),
                    "tokens_used": int(row["total_tokens"] or 0),
                    "cost_usd": float(row["total_cost"] or 0),
                }
                providers.append(provider_stats)

                # Accumulate totals
                total_stats["total_calls"] += provider_stats["calls"]
                total_stats["total_successes"] += provider_stats["successes"]
                total_stats["total_failures"] += provider_stats["failures"]
                total_stats["total_tokens"] += provider_stats["tokens_used"]
                total_stats["total_cost_usd"] += provider_stats["cost_usd"]

            return {
                "user_id": user_id,
                "time_range_hours": time_range_hours,
                "providers": providers,
                "total": total_stats,
                "generated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get API call stats: {str(e)}")
            return {
                "user_id": user_id,
                "time_range_hours": time_range_hours,
                "providers": [],
                "total": {},
                "error": str(e),
            }

    async def get_recent_api_calls(
        self, user_id: str, provider: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取最近的API调用记录

        Args:
            user_id: 用户ID
            provider: API提供商（可选）
            limit: 返回记录数量限制

        Returns:
            API调用记录列表
        """
        try:
            if not self.supabase:
                return []

            query = (
                self.supabase.table("external_api_call_logs")
                .select(
                    "provider, operation, api_endpoint, http_method, success, status_code, response_time_ms, error_type, error_message, called_at, workflow_execution_id, retry_count"
                )
                .eq("user_id", user_id)
                .order("called_at", desc=True)
                .limit(limit)
            )
            if provider:
                query = query.eq("provider", provider)

            results = query.execute()
            rows = results.data or []
            calls: List[Dict[str, Any]] = []
            for row in rows:
                call = {
                    "provider": row.get("provider"),
                    "operation": row.get("operation"),
                    "api_endpoint": row.get("api_endpoint"),
                    "http_method": row.get("http_method"),
                    "success": row.get("success"),
                    "status_code": row.get("status_code"),
                    "response_time_ms": row.get("response_time_ms"),
                    "error_type": row.get("error_type"),
                    "error_message": row.get("error_message"),
                    "called_at": row.get("called_at"),
                    "workflow_execution_id": row.get("workflow_execution_id"),
                    "retry_count": row.get("retry_count"),
                }
                calls.append(call)

            return calls

        except Exception as e:
            logger.error(f"Failed to get recent API calls: {str(e)}")
            return []


# ============================================================================
# 性能监控装饰器
# ============================================================================


class APICallTracker:
    """API调用跟踪器装饰器

    用于自动跟踪API调用的性能和结果。
    """

    def __init__(
        self,
        logger: APICallLogger,
        user_id: str,
        provider: str,
        operation: str,
        workflow_execution_id: Optional[str] = None,
        node_id: Optional[str] = None,
    ):
        """初始化API调用跟踪器

        Args:
            logger: API调用日志记录器
            user_id: 用户ID
            provider: API提供商
            operation: 操作类型
            workflow_execution_id: 工作流执行ID
            node_id: 节点ID
        """
        self.logger = logger
        self.user_id = user_id
        self.provider = provider
        self.operation = operation
        self.workflow_execution_id = workflow_execution_id
        self.node_id = node_id
        self.start_time = None
        self.api_endpoint = ""
        self.http_method = "POST"

    async def __aenter__(self):
        """进入异步上下文"""
        self.start_time = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出异步上下文"""
        if self.start_time is not None:
            response_time_ms = int((time.time() - self.start_time) * 1000)
        else:
            response_time_ms = 0

        success = exc_type is None
        error_type = None
        error_message = None

        if exc_type:
            error_type = exc_type.__name__
            error_message = str(exc_val) if exc_val else ""

        # 记录API调用
        await self.logger.log_api_call(
            user_id=self.user_id,
            provider=self.provider,
            operation=self.operation,
            api_endpoint=self.api_endpoint,
            http_method=self.http_method,
            success=success,
            response_time_ms=response_time_ms,
            workflow_execution_id=self.workflow_execution_id,
            node_id=self.node_id,
            error_type=error_type,
            error_message=error_message,
        )

    def set_endpoint_info(self, api_endpoint: str, http_method: str = "POST"):
        """设置端点信息"""
        self.api_endpoint = api_endpoint
        self.http_method = http_method


# ============================================================================
# 全局实例管理
# ============================================================================

_logger_instance: Optional[APICallLogger] = None


def get_api_call_logger(database_session: Optional[object] = None) -> APICallLogger:
    """获取API调用日志记录器实例

    Args:
        database_session: 数据库会话

    Returns:
        APICallLogger实例
    """
    global _logger_instance

    if _logger_instance is None:
        _logger_instance = APICallLogger(database_session)

    return _logger_instance


def reset_api_call_logger():
    """重置API调用日志记录器实例（主要用于测试）"""
    global _logger_instance
    _logger_instance = None
