"""
External API Call Logger Service
记录外部API调用的日志、性能指标和分析数据
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.orm import Session

from .credential_encryption import CredentialEncryption
from ..models.database import get_db_session

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
            'password', 'secret', 'key', 'token', 'auth', 'authorization',
            'api_key', 'access_token', 'refresh_token', 'client_secret',
            'private_key', 'credential', 'credentials'
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
            'authorization', 'x-api-key', 'x-auth-token', 'cookie',
            'x-access-token', 'x-refresh-token', 'bearer'
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
    
    def __init__(self, database_session: Optional[Session] = None):
        """初始化API调用日志记录器
        
        Args:
            database_session: 数据库会话，如果不提供则使用默认会话
        """
        self.db_session = database_session
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
        rate_limit_reset_at: Optional[datetime] = None
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
                rate_limit_reset_at=rate_limit_reset_at
            )

            # 存储到数据库
            return await self._store_log_entry(log_entry)

        except Exception as e:
            logger.error(f"Failed to log API call: {str(e)}")
            return False

    async def _store_log_entry(self, log_entry: APICallLogEntry) -> bool:
        """存储日志条目到数据库"""
        try:
            # 使用提供的数据库会话或创建新的
            db = self.db_session or get_db_session()
            
            with db:
                # 构建INSERT语句
                insert_query = text("""
                    INSERT INTO external_api_call_logs (
                        user_id, provider, operation, api_endpoint, http_method,
                        success, status_code, response_time_ms,
                        workflow_execution_id, node_id,
                        request_data, response_data, request_headers, response_headers,
                        error_type, error_message, retry_count,
                        rate_limit_remaining, rate_limit_reset_at, called_at
                    ) VALUES (
                        :user_id, :provider, :operation, :api_endpoint, :http_method,
                        :success, :status_code, :response_time_ms,
                        :workflow_execution_id, :node_id,
                        :request_data, :response_data, :request_headers, :response_headers,
                        :error_type, :error_message, :retry_count,
                        :rate_limit_remaining, :rate_limit_reset_at, :called_at
                    )
                """)
                
                # 准备参数
                params = {
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
                    "request_data": json.dumps(log_entry.request_data) if log_entry.request_data else None,
                    "response_data": json.dumps(log_entry.response_data) if log_entry.response_data else None,
                    "request_headers": json.dumps(log_entry.request_headers) if log_entry.request_headers else None,
                    "response_headers": json.dumps(log_entry.response_headers) if log_entry.response_headers else None,
                    "error_type": log_entry.error_type,
                    "error_message": log_entry.error_message,
                    "retry_count": log_entry.retry_count,
                    "rate_limit_remaining": log_entry.rate_limit_remaining,
                    "rate_limit_reset_at": log_entry.rate_limit_reset_at,
                    "called_at": log_entry.called_at
                }
                
                # 执行插入
                result = db.execute(insert_query, params)
                db.commit()
                
                logger.debug(f"Successfully logged API call: {log_entry.provider}.{log_entry.operation} for user {log_entry.user_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to store API call log to database: {str(e)}")
            if self.db_session is None and 'db' in locals():
                # 如果是我们创建的会话，进行回滚
                try:
                    db.rollback()
                except:
                    pass
            return False

    async def get_api_call_stats(
        self,
        user_id: str,
        provider: Optional[str] = None,
        time_range_hours: int = 24
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
            # 使用提供的数据库会话或创建新的
            db = self.db_session or get_db_session()
            
            with db:
                # 构建查询条件
                where_conditions = ["user_id = :user_id"]
                where_conditions.append("called_at >= NOW() - INTERVAL :hours HOUR")
                
                params = {
                    "user_id": user_id,
                    "hours": time_range_hours
                }
                
                if provider:
                    where_conditions.append("provider = :provider")
                    params["provider"] = provider
                
                where_clause = " AND ".join(where_conditions)
                
                # 基本统计查询
                stats_query = text(f"""
                    SELECT 
                        provider,
                        COUNT(*) as total_calls,
                        COUNT(CASE WHEN success = true THEN 1 END) as successful_calls,
                        COUNT(CASE WHEN success = false THEN 1 END) as failed_calls,
                        AVG(response_time_ms) as avg_response_time,
                        MAX(response_time_ms) as max_response_time,
                        MIN(response_time_ms) as min_response_time
                    FROM external_api_call_logs 
                    WHERE {where_clause}
                    GROUP BY provider
                    ORDER BY total_calls DESC
                """)
                
                results = db.execute(stats_query, params).fetchall()
                
                stats = {
                    "user_id": user_id,
                    "time_range_hours": time_range_hours,
                    "providers": []
                }
                
                for row in results:
                    provider_stats = {
                        "provider": row[0],
                        "total_calls": row[1],
                        "successful_calls": row[2],
                        "failed_calls": row[3],
                        "success_rate": (row[2] / row[1] * 100) if row[1] > 0 else 0,
                        "avg_response_time_ms": float(row[4]) if row[4] else None,
                        "max_response_time_ms": row[5],
                        "min_response_time_ms": row[6]
                    }
                    stats["providers"].append(provider_stats)
                
                # 总体统计
                total_stats_query = text(f"""
                    SELECT 
                        COUNT(*) as total_calls,
                        COUNT(CASE WHEN success = true THEN 1 END) as successful_calls,
                        COUNT(CASE WHEN success = false THEN 1 END) as failed_calls,
                        AVG(response_time_ms) as avg_response_time
                    FROM external_api_call_logs 
                    WHERE {where_clause}
                """)
                
                total_result = db.execute(total_stats_query, params).fetchone()
                
                if total_result:
                    stats["total"] = {
                        "total_calls": total_result[0],
                        "successful_calls": total_result[1],
                        "failed_calls": total_result[2],
                        "success_rate": (total_result[1] / total_result[0] * 100) if total_result[0] > 0 else 0,
                        "avg_response_time_ms": float(total_result[3]) if total_result[3] else None
                    }
                
                return stats

        except Exception as e:
            logger.error(f"Failed to get API call stats: {str(e)}")
            return {"error": str(e)}

    async def get_recent_api_calls(
        self,
        user_id: str,
        provider: Optional[str] = None,
        limit: int = 50
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
            # 使用提供的数据库会话或创建新的
            db = self.db_session or get_db_session()
            
            with db:
                # 构建查询条件
                where_conditions = ["user_id = :user_id"]
                params = {
                    "user_id": user_id,
                    "limit": limit
                }
                
                if provider:
                    where_conditions.append("provider = :provider")
                    params["provider"] = provider
                
                where_clause = " AND ".join(where_conditions)
                
                query = text(f"""
                    SELECT 
                        provider, operation, api_endpoint, http_method,
                        success, status_code, response_time_ms,
                        error_type, error_message, called_at,
                        workflow_execution_id, retry_count
                    FROM external_api_call_logs 
                    WHERE {where_clause}
                    ORDER BY called_at DESC
                    LIMIT :limit
                """)
                
                results = db.execute(query, params).fetchall()
                
                calls = []
                for row in results:
                    call = {
                        "provider": row[0],
                        "operation": row[1],
                        "api_endpoint": row[2],
                        "http_method": row[3],
                        "success": row[4],
                        "status_code": row[5],
                        "response_time_ms": row[6],
                        "error_type": row[7],
                        "error_message": row[8],
                        "called_at": row[9].isoformat() if row[9] else None,
                        "workflow_execution_id": row[10],
                        "retry_count": row[11]
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
        node_id: Optional[str] = None
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
        response_time_ms = int((time.time() - self.start_time) * 1000)
        
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
            error_message=error_message
        )

    def set_endpoint_info(self, api_endpoint: str, http_method: str = "POST"):
        """设置端点信息"""
        self.api_endpoint = api_endpoint
        self.http_method = http_method


# ============================================================================
# 全局实例管理
# ============================================================================

_logger_instance: Optional[APICallLogger] = None


def get_api_call_logger(database_session: Optional[Session] = None) -> APICallLogger:
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