"""
Workflow执行日志服务
负责存储、缓存和推送用户友好的workflow执行日志
"""

import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    from sqlalchemy.orm import Session

    from ..models.database import get_db_session

    DATABASE_AVAILABLE = True

    # Import database models
    import sys
    from pathlib import Path

    backend_dir = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(backend_dir))
    from shared.models.db_models import LogEventTypeEnum, LogLevelEnum, WorkflowExecutionLog

except ImportError:
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
        return result


class ExecutionLogService:
    """
    工作流执行日志服务

    功能:
    1. 实时日志存储和缓存
    2. 历史日志查询
    3. 流式日志推送
    4. 用户友好的日志格式化
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Redis连接用于实时缓存和推送
        self.redis_client = None
        if REDIS_AVAILABLE:
            try:
                import redis

                self.redis_client = redis.Redis(
                    host="localhost", port=6379, db=1, decode_responses=True  # 使用db=1专门存储日志
                )
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

    async def add_log_entry(self, entry: ExecutionLogEntry):
        """添加日志条目"""
        try:
            # 1. 存储到Redis缓存
            if self.redis_client:
                await self._store_to_redis(entry)
            else:
                # 备选：存储到内存缓存
                await self._store_to_memory(entry)

            # 2. 推送到WebSocket连接
            await self._push_to_websockets(entry)

            # 3. 异步存储到数据库(历史记录)
            asyncio.create_task(self._store_to_database(entry))

        except Exception as e:
            self.logger.error(f"Failed to add log entry: {e}")

    async def _store_to_redis(self, entry: ExecutionLogEntry):
        """存储到Redis"""
        try:
            key = f"workflow_logs:{entry.execution_id}"
            value = json.dumps(entry.to_dict(), ensure_ascii=False)

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

    async def _store_to_database(self, entry: ExecutionLogEntry):
        """异步存储到数据库(历史记录)"""
        if not DATABASE_AVAILABLE:
            return

        try:
            db = get_db_session()
            try:
                # 转换事件类型到数据库枚举
                event_type_enum = self._convert_to_db_event_type(entry.event_type)
                level_enum = self._convert_to_db_level(entry.level)

                # 从数据中提取节点信息
                node_info = self._extract_node_info_from_data(entry.data)

                # 创建数据库记录
                db_log = WorkflowExecutionLog(
                    execution_id=entry.execution_id,
                    event_type=event_type_enum,
                    level=level_enum,
                    message=entry.message,
                    data=entry.data or {},
                    node_id=node_info.get("node_id"),
                    node_name=node_info.get("node_name"),
                    node_type=node_info.get("node_type"),
                    step_number=node_info.get("step_number"),
                    total_steps=node_info.get("total_steps"),
                    duration_seconds=node_info.get("duration_seconds"),
                )

                db.add(db_log)
                db.commit()

            finally:
                db.close()

        except Exception as e:
            self.logger.error(f"Failed to store to database: {e}")

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
                    await websocket.send_text(json.dumps(entry.to_dict(), ensure_ascii=False))
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
        """从数据库获取历史日志"""
        if not DATABASE_AVAILABLE:
            return []

        try:
            db = get_db_session()
            try:
                # 查询执行日志，按时间排序
                query = (
                    db.query(WorkflowExecutionLog)
                    .filter(WorkflowExecutionLog.execution_id == execution_id)
                    .order_by(WorkflowExecutionLog.created_at.asc())
                    .offset(offset)
                    .limit(limit)
                )

                logs = []
                for log_entry in query.all():
                    # 转换为统一格式
                    log_dict = {
                        "execution_id": log_entry.execution_id,
                        "event_type": log_entry.event_type.value,
                        "timestamp": log_entry.created_at.isoformat(),
                        "message": log_entry.message,
                        "level": log_entry.level.value,
                        "data": log_entry.data or {},
                    }

                    # 添加节点信息到data中
                    if log_entry.node_id:
                        log_dict["data"]["node_id"] = log_entry.node_id
                    if log_entry.node_name:
                        log_dict["data"]["node_name"] = log_entry.node_name
                    if log_entry.node_type:
                        log_dict["data"]["node_type"] = log_entry.node_type
                    if log_entry.step_number is not None:
                        log_dict["data"]["step_number"] = log_entry.step_number
                    if log_entry.total_steps is not None:
                        log_dict["data"]["total_steps"] = log_entry.total_steps
                    if log_entry.duration_seconds is not None:
                        log_dict["data"]["duration_seconds"] = log_entry.duration_seconds

                    logs.append(log_dict)

                return logs

            finally:
                db.close()

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
        """从数据库获取过滤后的日志"""
        try:
            db = get_db_session()
            try:
                # 构建基础查询
                query = db.query(WorkflowExecutionLog).filter(
                    WorkflowExecutionLog.execution_id == execution_id
                )

                # 应用过滤条件
                if level:
                    query = query.filter(WorkflowExecutionLog.level == LogLevelEnum(level.upper()))
                if event_type:
                    query = query.filter(
                        WorkflowExecutionLog.event_type == LogEventTypeEnum(event_type)
                    )
                if start_time:
                    query = query.filter(WorkflowExecutionLog.created_at >= start_time)
                if end_time:
                    query = query.filter(WorkflowExecutionLog.created_at <= end_time)

                # 获取总数
                total_count = query.count()

                # 应用分页和排序
                results = (
                    query.order_by(WorkflowExecutionLog.created_at.asc())
                    .offset(offset)
                    .limit(limit)
                    .all()
                )

                # 转换为字典格式
                logs = []
                for log_entry in results:
                    log_dict = {
                        "execution_id": log_entry.execution_id,
                        "event_type": log_entry.event_type.value,
                        "timestamp": log_entry.created_at.isoformat(),
                        "message": log_entry.message,
                        "level": log_entry.level.value,
                        "data": log_entry.data or {},
                    }
                    logs.append(log_dict)

                return logs, total_count

            finally:
                db.close()

        except Exception as e:
            self.logger.error(f"Failed to get filtered logs from database: {e}")
            return [], 0

    async def get_execution_stats(self, execution_id: str) -> Dict[str, Any]:
        """获取执行统计信息"""
        try:
            # 从数据库获取统计信息
            if not DATABASE_AVAILABLE:
                return {}

            db = get_db_session()
            try:
                # 基础统计查询
                logs = (
                    db.query(WorkflowExecutionLog)
                    .filter(WorkflowExecutionLog.execution_id == execution_id)
                    .all()
                )

                if not logs:
                    return {}

                # 计算统计信息
                total_steps = 0
                completed_steps = 0
                failed_steps = 0
                total_duration = 0
                step_durations = []
                workflow_name = "未知工作流"

                for log in logs:
                    # 从工作流开始日志中提取工作流名称
                    if log.event_type == LogEventTypeEnum.WORKFLOW_STARTED:
                        workflow_name = log.data.get("workflow_name", "未知工作流")
                        total_steps = log.total_steps or 0

                    # 统计完成的步骤
                    elif log.event_type == LogEventTypeEnum.STEP_COMPLETED:
                        if log.data and log.data.get("status") == "SUCCESS":
                            completed_steps += 1
                        else:
                            failed_steps += 1

                        # 收集步骤耗时
                        if log.duration_seconds:
                            step_durations.append(
                                {
                                    "name": log.node_name or f"步骤{log.step_number}",
                                    "duration": log.duration_seconds,
                                }
                            )
                            total_duration += log.duration_seconds

                # 计算最慢步骤
                slowest_step = None
                if step_durations:
                    slowest_step = max(step_durations, key=lambda x: x["duration"])

                # 计算平均步骤时间
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

            finally:
                db.close()

        except Exception as e:
            self.logger.error(f"Failed to get execution stats: {e}")
            return {}

    async def cleanup_old_logs(
        self, before_date: datetime, keep_recent: Optional[int] = None
    ) -> Dict[str, int]:
        """清理历史日志"""
        try:
            if not DATABASE_AVAILABLE:
                return {"deleted": 0}

            db = get_db_session()
            try:
                # 构建删除查询
                query = db.query(WorkflowExecutionLog).filter(
                    WorkflowExecutionLog.created_at < before_date
                )

                # 如果指定保留最近的记录数，需要更复杂的查询
                if keep_recent:
                    # 获取每个execution_id的最新记录
                    subquery = db.query(WorkflowExecutionLog.execution_id).distinct().subquery()

                    # 这里需要更复杂的SQL来保留每个执行的最近N条记录
                    # 为简化，暂时只按日期删除
                    pass

                # 执行删除
                deleted_count = query.count()
                query.delete()
                db.commit()

                return {"deleted": deleted_count}

            finally:
                db.close()

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

            # 数据库统计
            if DATABASE_AVAILABLE:
                db = get_db_session()
                try:
                    # 总日志条目数
                    total_logs = db.query(WorkflowExecutionLog).count()
                    stats["total_log_entries"] = total_logs

                    # 不同执行的数量
                    distinct_executions = (
                        db.query(WorkflowExecutionLog.execution_id).distinct().count()
                    )
                    stats["total_executions"] = distinct_executions

                finally:
                    db.close()

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
