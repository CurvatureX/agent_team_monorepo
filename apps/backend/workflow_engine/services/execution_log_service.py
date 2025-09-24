"""
Workflow执行日志服务
负责存储、缓存和推送用户友好的workflow执行日志
"""

import asyncio
import json
import logging
import time
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from threading import Lock
from typing import Any, AsyncGenerator, Dict, List, Optional

# Import Unicode utilities for safe logging
try:
    from utils.unicode_utils import clean_unicode_data, safe_json_dumps, safe_json_loads

    UNICODE_UTILS_AVAILABLE = True
except ImportError:
    UNICODE_UTILS_AVAILABLE = False

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    import sys
    from pathlib import Path

    # Import database connection from the main database module
    from database import Database
    from sqlalchemy.orm import Session

    # Import database models from shared package
    backend_dir = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(backend_dir))
    from shared.models.db_models import LogEventTypeEnum, LogLevelEnum, WorkflowExecutionLog

    DATABASE_AVAILABLE = True

except ImportError as e:
    DATABASE_AVAILABLE = False
    WorkflowExecutionLog = None
    LogLevelEnum = None
    LogEventTypeEnum = None


class LogEventType(str, Enum):
    """日志事件类型"""

    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_PROGRESS = "workflow_progress"
    STEP_STARTED = "step_started"
    STEP_INPUT = "step_input"
    STEP_OUTPUT = "step_output"
    STEP_COMPLETED = "step_completed"
    STEP_ERROR = "step_error"
    SEPARATOR = "separator"


@dataclass
class ExecutionLogEntry:
    """执行日志条目"""

    execution_id: str
    event_type: LogEventType
    timestamp: str
    message: str
    data: Optional[Dict[str, Any]] = None
    level: str = "INFO"  # INFO, ERROR, DEBUG

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = asdict(self)
        result["timestamp"] = self.timestamp

        # Clean Unicode data before returning
        if UNICODE_UTILS_AVAILABLE:
            result = clean_unicode_data(result)

        return result


class ExecutionLogService:
    """
    工作流执行日志服务

    功能:
    1. 实时日志存储和缓存
    2. 历史日志查询
    3. 流式日志推送
    4. 用户友好的日志格式化
    5. 批量写入优化（仅用户友好日志存储到Supabase）
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Redis连接用于实时缓存和推送
        self.redis_client = None
        if REDIS_AVAILABLE:
            try:
                import os

                import redis

                # Use environment variable or fall back to localhost
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
                # Parse Redis URL and set db=1 for logs
                if "redis://" in redis_url:
                    # Extract base URL and set db=1
                    base_url = (
                        redis_url.split("/")[0] + "//" + redis_url.split("//")[1].split("/")[0]
                    )
                    redis_url = base_url + "/1"  # Use db=1 for logs

                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                # 测试连接
                self.redis_client.ping()
                self.logger.info("Redis connection established for log service")
            except Exception as e:
                self.logger.warning(f"Redis connection failed: {e}")
                self.redis_client = None

        # 内存缓存作为Redis的备选方案
        self._memory_cache: Dict[str, List[ExecutionLogEntry]] = {}

        # WebSocket连接管理
        self._websocket_connections: Dict[str, List[Any]] = {}

        # 批量写入缓冲区 - 仅存储用户友好日志
        self._batch_buffer: deque = deque()
        self._buffer_lock = Lock()
        self._batch_writer_task = None
        self._shutdown = False

        # 启动批量写入任务
        self._start_batch_writer()

        # Note: Log cleanup (10-day TTL) is handled by database-level pg_cron job
        # See migration: 20250913000002_add_log_ttl_function.sql

    def _clean_log_entry(self, entry: ExecutionLogEntry) -> ExecutionLogEntry:
        """Clean log entry to prevent Unicode serialization issues."""
        if not UNICODE_UTILS_AVAILABLE:
            return entry

        try:
            # Clean the message
            cleaned_message = clean_unicode_data(entry.message)

            # Clean the data if present
            cleaned_data = None
            if entry.data:
                cleaned_data = clean_unicode_data(entry.data)

            # Create new entry with cleaned data
            return ExecutionLogEntry(
                execution_id=entry.execution_id,
                event_type=entry.event_type,
                timestamp=entry.timestamp,
                message=cleaned_message,
                data=cleaned_data,
                level=entry.level,
            )
        except Exception as e:
            self.logger.warning(f"Failed to clean log entry, using fallback: {e}")
            # Fallback: return entry with simplified data
            return ExecutionLogEntry(
                execution_id=entry.execution_id,
                event_type=entry.event_type,
                timestamp=entry.timestamp,
                message="[LOG_UNICODE_CLEANED]",
                data={"original_message": str(entry.message)[:100]},  # Truncate to prevent issues
                level=entry.level,
            )

    async def add_log_entry(self, entry: ExecutionLogEntry):
        """添加日志条目"""
        try:
            # Clean the entry first to prevent Unicode issues
            entry = self._clean_log_entry(entry)
            self.logger.debug(f"🔥 DEBUG: Adding log entry {entry.execution_id}: {entry.message}")

            # 1. 存储到Redis缓存（所有日志）
            if self.redis_client:
                await self._store_to_redis(entry)
            else:
                # 备选：存储到内存缓存
                await self._store_to_memory(entry)

            # 2. 推送到WebSocket连接
            await self._push_to_websockets(entry)

            # 3. 仅用户友好日志添加到批量写入缓冲区
            is_user_friendly = self._is_user_friendly_log(entry)
            self.logger.debug(
                f"🔥 DEBUG: Is user friendly: {is_user_friendly} for {entry.execution_id}"
            )

            if is_user_friendly:
                await self._add_to_batch_buffer(entry)
                self.logger.debug(f"🔥 DEBUG: Added to batch buffer: {entry.execution_id}")

                # DIRECT DATABASE WRITE for debugging - bypass batch system
                try:
                    await self._direct_write_to_database(entry)
                    self.logger.debug(
                        f"🔥 DEBUG: Direct database write successful for {entry.execution_id}"
                    )
                except Exception as direct_error:
                    self.logger.error(f"🔥 Direct database write failed: {direct_error}")

        except Exception as e:
            self.logger.error(f"Failed to add log entry: {e}")

    async def _direct_write_to_database(self, entry: ExecutionLogEntry):
        """Direct database write for debugging - bypasses batch system"""
        if not DATABASE_AVAILABLE:
            return

        try:
            db = Database()
            node_info = self._extract_node_info_from_data(entry.data)

            log_record = {
                "execution_id": entry.execution_id,
                "log_category": "business",
                "event_type": entry.event_type.value,
                "level": entry.level.upper(),
                "message": entry.message,
                "data": entry.data or {},
                "node_id": node_info.get("node_id"),
                "node_name": node_info.get("node_name"),
                "node_type": node_info.get("node_type"),
                "step_number": node_info.get("step_number"),
                "total_steps": node_info.get("total_steps"),
                "duration_seconds": node_info.get("duration_seconds"),
                "user_friendly_message": entry.data.get("user_friendly_message")
                if entry.data
                else None,
                "display_priority": entry.data.get("display_priority", 5) if entry.data else 5,
                "is_milestone": entry.data.get("is_milestone", False) if entry.data else False,
            }

            # Clean the log record to ensure it's safe for database insertion
            if UNICODE_UTILS_AVAILABLE:
                log_record = clean_unicode_data(log_record)

            result = db.client.table("workflow_execution_logs").insert([log_record]).execute()
            # Clean the result before logging to prevent Unicode issues
            if UNICODE_UTILS_AVAILABLE:
                cleaned_result = clean_unicode_data(str(result)[:500])  # Truncate and clean
                self.logger.debug(f"🔥 DEBUG: Direct insert result: {cleaned_result}")
            else:
                # Fallback: just log success without details
                self.logger.debug(f"🔥 DEBUG: Direct insert completed successfully")

        except Exception as e:
            self.logger.error(f"Direct database write error: {e}")
            raise

    def _is_user_friendly_log(self, entry: ExecutionLogEntry) -> bool:
        """判断是否为用户友好日志（需要存储到Supabase）"""
        # 检查是否有用户友好的消息或者是重要的里程碑事件
        if entry.data and entry.data.get("user_friendly_message"):
            return True

        # 检查是否为重要的里程碑事件
        milestone_events = {
            "workflow_started",
            "workflow_completed",
            "step_completed",
            "step_error",
        }

        if entry.event_type in milestone_events:
            return True

        # 检查是否为高优先级日志
        if entry.data and entry.data.get("display_priority", 5) >= 7:
            return True

        return False

    async def _add_to_batch_buffer(self, entry: ExecutionLogEntry):
        """添加用户友好日志到批量写入缓冲区"""
        try:
            with self._buffer_lock:
                self._batch_buffer.append(entry)

            # 如果缓冲区过大，立即触发写入
            if len(self._batch_buffer) >= 50:  # 达到50条立即写入
                asyncio.create_task(self._flush_batch_buffer())

        except Exception as e:
            self.logger.error(f"Failed to add to batch buffer: {e}")

    def _start_batch_writer(self):
        """启动批量写入后台任务"""
        if not DATABASE_AVAILABLE:
            self.logger.debug("🔥 DEBUG: DATABASE_AVAILABLE is False, batch writer not started")
            return

        self.logger.debug("🔥 DEBUG: Starting batch writer initialization")

        async def batch_writer():
            self.logger.debug("🔥 DEBUG: Batch writer started successfully")
            while not self._shutdown:
                try:
                    await asyncio.sleep(1.0)  # 每1秒执行一次
                    await self._flush_batch_buffer()
                except Exception as e:
                    self.logger.error(f"Batch writer error: {e}")

        # 在事件循环中启动后台任务
        try:
            # Try to get the running event loop (modern approach)
            loop = asyncio.get_running_loop()
            self._batch_writer_task = loop.create_task(batch_writer())
            self.logger.debug("🔥 DEBUG: Batch writer task created successfully")
        except RuntimeError:
            # No running event loop, defer task creation
            self.logger.debug("🔥 DEBUG: No running event loop, deferring batch writer start")
            self._batch_writer_task = None

    async def _flush_batch_buffer(self):
        """批量写入缓冲区中的日志到数据库"""
        if not DATABASE_AVAILABLE:
            self.logger.debug("🔥 DEBUG: DATABASE_AVAILABLE is False, cannot flush")
            return

        # 获取待写入的日志条目
        entries_to_write = []
        with self._buffer_lock:
            if not self._batch_buffer:
                return  # 缓冲区为空

            # 一次最多处理100条日志
            batch_size = min(len(self._batch_buffer), 100)
            self.logger.debug(f"🔥 DEBUG: Flushing {batch_size} entries from buffer")
            for _ in range(batch_size):
                if self._batch_buffer:
                    entries_to_write.append(self._batch_buffer.popleft())

        if not entries_to_write:
            self.logger.debug("🔥 DEBUG: No entries to write after dequeue")
            return

        try:
            # Use the Database class to get Supabase client
            db = Database()

            # Create log entries for Supabase
            log_records = []
            for entry in entries_to_write:
                # Extract node information
                node_info = self._extract_node_info_from_data(entry.data)

                # Extract user-friendly message and metadata
                user_friendly_message = None
                display_priority = 5
                is_milestone = False

                if entry.data:
                    user_friendly_message = entry.data.get("user_friendly_message")
                    display_priority = entry.data.get("display_priority", 5)
                    is_milestone = entry.data.get("is_milestone", False)

                # Create record for Supabase (note: created_at is auto-generated by database)
                log_record = {
                    "execution_id": entry.execution_id,
                    "log_category": "business",  # User-friendly logs are business category
                    "event_type": entry.event_type.value,
                    "level": entry.level.upper(),
                    "message": entry.message,
                    "data": entry.data or {},
                    "node_id": node_info.get("node_id"),
                    "node_name": node_info.get("node_name"),
                    "node_type": node_info.get("node_type"),
                    "step_number": node_info.get("step_number"),
                    "total_steps": node_info.get("total_steps"),
                    "duration_seconds": node_info.get("duration_seconds"),
                    "user_friendly_message": user_friendly_message,
                    "display_priority": display_priority,
                    "is_milestone": is_milestone
                    # Note: created_at timestamp is auto-generated by Supabase
                }

                # Clean the log record before adding to batch
                if UNICODE_UTILS_AVAILABLE:
                    log_record = clean_unicode_data(log_record)

                log_records.append(log_record)

            # Insert into Supabase
            if log_records:
                result = db.client.table("workflow_execution_logs").insert(log_records).execute()

                self.logger.info(
                    f"Successfully wrote {len(log_records)} user-friendly logs to database"
                )

        except Exception as e:
            self.logger.error(f"Failed to flush batch buffer to database: {e}")

            # 失败的日志重新放回缓冲区头部
            with self._buffer_lock:
                for entry in reversed(entries_to_write):
                    self._batch_buffer.appendleft(entry)

    async def shutdown(self):
        """关闭服务，确保所有缓冲区的日志都被写入"""
        self._shutdown = True

        # 等待批量写入任务完成
        if self._batch_writer_task:
            await self._batch_writer_task

        # 最后一次刷新缓冲区
        await self._flush_batch_buffer()

        self.logger.info("ExecutionLogService shutdown completed")

    async def _store_to_redis(self, entry: ExecutionLogEntry):
        """存储到Redis"""
        try:
            key = f"workflow_logs:{entry.execution_id}"
            # Use safe JSON serialization to prevent Unicode issues
            if UNICODE_UTILS_AVAILABLE:
                value = safe_json_dumps(entry.to_dict())
            else:
                value = json.dumps(entry.to_dict(), ensure_ascii=True)

            # 使用list存储日志条目，按时间顺序
            self.redis_client.lpush(key, value)

            # 设置过期时间(24小时)，避免Redis内存无限增长
            self.redis_client.expire(key, 24 * 3600)

            # 也存储到全局最近日志列表(用于管理界面)
            self.redis_client.lpush("recent_workflow_logs", value)
            self.redis_client.ltrim("recent_workflow_logs", 0, 999)  # 只保留最近1000条

        except Exception as e:
            self.logger.error(f"Failed to store to Redis: {e}")
            # 备选：存储到内存
            await self._store_to_memory(entry)

    async def _store_to_memory(self, entry: ExecutionLogEntry):
        """存储到内存缓存"""
        if entry.execution_id not in self._memory_cache:
            self._memory_cache[entry.execution_id] = []

        self._memory_cache[entry.execution_id].append(entry)

        # 限制内存缓存大小
        if len(self._memory_cache[entry.execution_id]) > 1000:
            self._memory_cache[entry.execution_id] = self._memory_cache[entry.execution_id][-500:]

    def _convert_to_db_event_type(self, event_type: LogEventType) -> LogEventTypeEnum:
        """转换事件类型到数据库枚举"""
        # 直接映射，因为枚举值相同
        return LogEventTypeEnum(event_type.value)

    def _convert_to_db_level(self, level: str) -> LogLevelEnum:
        """转换日志级别到数据库枚举"""
        try:
            return LogLevelEnum(level.upper())
        except ValueError:
            return LogLevelEnum.INFO

    def _extract_node_info_from_data(self, data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """从日志数据中提取节点信息"""
        if not data:
            return {}

        node_info = {}

        # 提取节点相关信息
        if "node_id" in data:
            node_info["node_id"] = data["node_id"]
        if "node_name" in data or "step_name" in data:
            node_info["node_name"] = data.get("node_name") or data.get("step_name")
        if "node_type" in data:
            node_info["node_type"] = data["node_type"]

        # 提取步骤信息
        if "step_number" in data:
            node_info["step_number"] = data["step_number"]
        if "total_steps" in data:
            node_info["total_steps"] = data["total_steps"]

        # 提取性能信息
        if "duration_seconds" in data:
            # 确保是整数(数据库字段类型)
            try:
                node_info["duration_seconds"] = int(float(data["duration_seconds"]))
            except (ValueError, TypeError):
                pass

        return node_info

    async def _push_to_websockets(self, entry: ExecutionLogEntry):
        """推送到WebSocket连接"""
        execution_id = entry.execution_id
        if execution_id in self._websocket_connections:
            # 移除已断开的连接
            active_connections = []
            for websocket in self._websocket_connections[execution_id]:
                try:
                    # Use safe JSON serialization for WebSocket messages
                    if UNICODE_UTILS_AVAILABLE:
                        message = safe_json_dumps(entry.to_dict())
                    else:
                        message = json.dumps(entry.to_dict(), ensure_ascii=True)
                    await websocket.send_text(message)
                    active_connections.append(websocket)
                except Exception:
                    # 连接已断开，忽略
                    pass

            self._websocket_connections[execution_id] = active_connections
            if not active_connections:
                del self._websocket_connections[execution_id]

    async def get_logs(
        self, execution_id: str, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取执行日志(普通接口)"""
        try:
            # 1. 先尝试从Redis获取
            if self.redis_client:
                logs = await self._get_logs_from_redis(execution_id, limit, offset)
                if logs:
                    return logs

            # 2. 备选：从内存缓存获取
            if execution_id in self._memory_cache:
                entries = self._memory_cache[execution_id]
                start_idx = offset
                end_idx = min(offset + limit, len(entries))
                return [entry.to_dict() for entry in entries[start_idx:end_idx]]

            # 3. 最后：从数据库获取历史记录
            return await self._get_logs_from_database(execution_id, limit, offset)

        except Exception as e:
            self.logger.error(f"Failed to get logs: {e}")
            return []

    async def _get_logs_from_redis(
        self, execution_id: str, limit: int, offset: int
    ) -> List[Dict[str, Any]]:
        """从Redis获取日志"""
        try:
            key = f"workflow_logs:{execution_id}"
            # Redis的list是LIFO，需要反向获取
            raw_logs = self.redis_client.lrange(key, offset, offset + limit - 1)
            logs = []
            for raw_log in reversed(raw_logs):  # 反转以获得正确的时间顺序
                logs.append(json.loads(raw_log))
            return logs
        except Exception as e:
            self.logger.error(f"Failed to get logs from Redis: {e}")
            return []

    async def _get_logs_from_database(
        self, execution_id: str, limit: int, offset: int
    ) -> List[Dict[str, Any]]:
        """从数据库获取历史日志（使用 Supabase Python 客户端）"""
        try:
            db = Database()
            if not db.client:
                return []

            response = (
                db.client.table("workflow_execution_logs")
                .select("*")
                .eq("execution_id", execution_id)
                .order("created_at", desc=False)
                .range(offset, offset + limit - 1)
                .execute()
            )

            logs: List[Dict[str, Any]] = []
            for log_entry in response.data or []:
                log_dict = {
                    "execution_id": log_entry.get("execution_id"),
                    "event_type": log_entry.get("event_type"),
                    "timestamp": log_entry.get("created_at"),
                    "message": log_entry.get("message"),
                    "level": log_entry.get("level"),
                    "data": log_entry.get("data") or {},
                }

                # 附加节点信息
                for key in [
                    "node_id",
                    "node_name",
                    "node_type",
                    "step_number",
                    "total_steps",
                    "duration_seconds",
                ]:
                    if log_entry.get(key) is not None:
                        log_dict["data"][key] = log_entry.get(key)

                logs.append(log_dict)

            return logs

        except Exception as e:
            self.logger.error(f"Failed to get logs from database: {e}")
            return []

    def add_websocket_connection(self, execution_id: str, websocket: Any):
        """添加WebSocket连接"""
        if execution_id not in self._websocket_connections:
            self._websocket_connections[execution_id] = []
        self._websocket_connections[execution_id].append(websocket)

        self.logger.info(f"Added WebSocket connection for execution {execution_id}")

    def remove_websocket_connection(self, execution_id: str, websocket: Any):
        """移除WebSocket连接"""
        if execution_id in self._websocket_connections:
            try:
                self._websocket_connections[execution_id].remove(websocket)
                if not self._websocket_connections[execution_id]:
                    del self._websocket_connections[execution_id]
            except ValueError:
                pass

        self.logger.info(f"Removed WebSocket connection for execution {execution_id}")

    async def get_active_executions(self) -> List[Dict[str, Any]]:
        """获取当前活跃的执行列表"""
        active_executions = []

        if self.redis_client:
            # 从Redis获取活跃执行
            pattern = "workflow_logs:*"
            keys = self.redis_client.keys(pattern)

            for key in keys:
                execution_id = key.replace("workflow_logs:", "")
                # 获取最后一条日志来判断状态
                latest_log_raw = self.redis_client.lindex(key, 0)
                if latest_log_raw:
                    latest_log = json.loads(latest_log_raw)
                    active_executions.append(
                        {
                            "execution_id": execution_id,
                            "last_activity": latest_log.get("timestamp"),
                            "status": self._infer_status_from_log(latest_log),
                        }
                    )

        return active_executions

    def _infer_status_from_log(self, log: Dict[str, Any]) -> str:
        """从日志推断执行状态"""
        event_type = log.get("event_type")

        if event_type == LogEventType.WORKFLOW_COMPLETED:
            # 检查是否成功完成
            message = log.get("message", "")
            if "成功" in message or "完成" in message:
                return "SUCCESS"
            elif "失败" in message or "错误" in message:
                return "ERROR"
            elif "暂停" in message:
                return "PAUSED"
        elif event_type == LogEventType.STEP_ERROR:
            return "ERROR"
        elif event_type in [LogEventType.STEP_STARTED, LogEventType.WORKFLOW_PROGRESS]:
            return "RUNNING"

        return "UNKNOWN"

    async def get_logs_with_filters(
        self,
        execution_id: str,
        limit: int = 100,
        offset: int = 0,
        level: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """获取带过滤条件的执行日志"""
        try:
            # 优先从Redis获取(实时数据)
            if self.redis_client:
                logs = await self._get_filtered_logs_from_redis(
                    execution_id, limit, offset, level, event_type
                )
                if logs:
                    return {
                        "execution_id": execution_id,
                        "total_count": len(logs),
                        "logs": logs,
                        "pagination": {
                            "limit": limit,
                            "offset": offset,
                            "has_more": len(logs) >= limit,
                        },
                    }

            # 从数据库获取历史数据
            if DATABASE_AVAILABLE:
                logs, total_count = await self._get_filtered_logs_from_database(
                    execution_id, limit, offset, level, event_type, start_time, end_time
                )
                return {
                    "execution_id": execution_id,
                    "total_count": total_count,
                    "logs": logs,
                    "pagination": {
                        "limit": limit,
                        "offset": offset,
                        "has_more": (offset + len(logs)) < total_count,
                    },
                }

            return {
                "execution_id": execution_id,
                "total_count": 0,
                "logs": [],
                "pagination": {"limit": limit, "offset": offset, "has_more": False},
            }

        except Exception as e:
            self.logger.error(f"Failed to get filtered logs: {e}")
            return {
                "execution_id": execution_id,
                "total_count": 0,
                "logs": [],
                "pagination": {"limit": limit, "offset": offset, "has_more": False},
            }

    async def _get_filtered_logs_from_redis(
        self,
        execution_id: str,
        limit: int,
        offset: int,
        level: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """从Redis获取过滤后的日志"""
        try:
            key = f"workflow_logs:{execution_id}"
            # 获取所有日志
            raw_logs = self.redis_client.lrange(key, 0, -1)
            logs = []

            for raw_log in reversed(raw_logs):  # 时间顺序
                log = json.loads(raw_log)

                # 应用过滤条件
                if level and log.get("level") != level:
                    continue
                if event_type and log.get("event_type") != event_type:
                    continue

                logs.append(log)

            # 应用分页
            return logs[offset : offset + limit]

        except Exception as e:
            self.logger.error(f"Failed to get filtered logs from Redis: {e}")
            return []

    async def _get_filtered_logs_from_database(
        self,
        execution_id: str,
        limit: int,
        offset: int,
        level: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> tuple[List[Dict[str, Any]], int]:
        """从数据库获取过滤后的日志（使用 Supabase 客户端）"""
        try:
            db = Database()
            if not db.client:
                return [], 0

            query = (
                db.client.table("workflow_execution_logs")
                .select("*", count="exact")
                .eq("execution_id", execution_id)
            )
            if level:
                query = query.eq("level", level.upper())
            if event_type:
                query = query.eq("event_type", event_type)
            if start_time:
                query = query.gte("created_at", start_time.isoformat())
            if end_time:
                query = query.lte("created_at", end_time.isoformat())

            resp = query.order("created_at", desc=False).range(offset, offset + limit - 1).execute()

            logs: List[Dict[str, Any]] = []
            for row in resp.data or []:
                logs.append(
                    {
                        "execution_id": row.get("execution_id"),
                        "event_type": row.get("event_type"),
                        "timestamp": row.get("created_at"),
                        "message": row.get("message"),
                        "level": row.get("level"),
                        "data": row.get("data") or {},
                    }
                )

            return logs, (resp.count or 0)

        except Exception as e:
            self.logger.error(f"Failed to get filtered logs from database: {e}")
            return [], 0

    async def get_execution_stats(self, execution_id: str) -> Dict[str, Any]:
        """获取执行统计信息"""
        try:
            # 使用 Supabase 获取统计信息
            db = Database()
            if not db.client:
                return {}

            resp = (
                db.client.table("workflow_execution_logs")
                .select("*")
                .eq("execution_id", execution_id)
                .order("created_at", desc=False)
                .limit(1000)
                .execute()
            )

            rows = resp.data or []
            if not rows:
                return {}

            total_steps = 0
            completed_steps = 0
            failed_steps = 0
            total_duration = 0
            step_durations = []
            workflow_name = "未知工作流"

            for row in rows:
                event_type = row.get("event_type")
                data = row.get("data") or {}
                if event_type == LogEventType.WORKFLOW_STARTED.value:
                    workflow_name = data.get("workflow_name", "未知工作流")
                    total_steps = data.get("total_steps", 0) or 0
                elif event_type == LogEventType.STEP_COMPLETED.value:
                    status = data.get("status")
                    if status == "SUCCESS":
                        completed_steps += 1
                    else:
                        failed_steps += 1
                    duration = row.get("duration_seconds")
                    if duration:
                        step_durations.append(
                            {
                                "name": row.get("node_name") or f"步骤{row.get('step_number')}",
                                "duration": duration,
                            }
                        )
                        total_duration += duration

            slowest_step = (
                max(step_durations, key=lambda x: x["duration"]) if step_durations else None
            )
            average_step_time = total_duration / len(step_durations) if step_durations else 0

            return {
                "execution_id": execution_id,
                "workflow_name": workflow_name,
                "total_steps": total_steps,
                "completed_steps": completed_steps,
                "failed_steps": failed_steps,
                "total_duration": total_duration,
                "average_step_time": average_step_time,
                "slowest_step": slowest_step,
                "performance_metrics": {
                    "step_count": len(step_durations),
                    "success_rate": (completed_steps / (completed_steps + failed_steps))
                    if (completed_steps + failed_steps) > 0
                    else 0,
                },
            }

        except Exception as e:
            self.logger.error(f"Failed to get execution stats: {e}")
            return {}

    async def cleanup_old_logs(
        self, before_date: datetime, keep_recent: Optional[int] = None
    ) -> Dict[str, int]:
        """清理历史日志"""
        try:
            db = Database()
            if not db.client:
                return {"deleted": 0}

            db.client.table("workflow_execution_logs").delete().lt(
                "created_at", before_date.isoformat()
            ).execute()

            return {"deleted": 0}

        except Exception as e:
            self.logger.error(f"Failed to cleanup old logs: {e}")
            return {"deleted": 0}

    async def get_log_stats(self) -> Dict[str, Any]:
        """获取日志统计信息"""
        try:
            stats = {}

            # Redis统计
            if self.redis_client:
                active_keys = self.redis_client.keys("workflow_logs:*")
                stats["active_executions"] = len(active_keys)

                # 计算Redis缓存使用情况
                redis_info = self.redis_client.info("memory")
                stats["cache_size_mb"] = round(redis_info.get("used_memory", 0) / (1024 * 1024), 2)

            # 数据库统计（Supabase）
            try:
                db = Database()
                if db.client:
                    count_resp = (
                        db.client.table("workflow_execution_logs")
                        .select("id", count="exact")
                        .execute()
                    )
                    stats["total_log_entries"] = count_resp.count or 0
            except Exception:
                pass

            # 内存缓存统计
            stats["memory_cache_executions"] = len(self._memory_cache)
            stats["active_websocket_connections"] = sum(
                len(connections) for connections in self._websocket_connections.values()
            )

            return stats

        except Exception as e:
            self.logger.error(f"Failed to get log stats: {e}")
            return {}


# 全局服务实例
_log_service: Optional[ExecutionLogService] = None


def get_execution_log_service() -> ExecutionLogService:
    """获取执行日志服务单例"""
    global _log_service
    if _log_service is None:
        _log_service = ExecutionLogService()
    return _log_service
