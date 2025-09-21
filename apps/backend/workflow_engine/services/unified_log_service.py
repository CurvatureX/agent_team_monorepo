"""
统一执行日志服务
支持技术调试日志和用户友好业务日志
"""

import asyncio
import base64
import json
import logging

# Import database models
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

try:
    from models.database import get_db_session
    from shared.models.db_models import (
        DisplayPriorityEnum,
        LogCategoryEnum,
        LogEventTypeEnum,
        LogLevelEnum,
        WorkflowExecutionLog,
    )
    from sqlalchemy.orm import Session

    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    WorkflowExecutionLog = None
    LogLevelEnum = None
    LogEventTypeEnum = None
    LogCategoryEnum = None
    DisplayPriorityEnum = None

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


@dataclass
class PaginationResult:
    """分页查询结果"""

    data: List[Dict[str, Any]]
    total_count: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool
    next_cursor: Optional[str] = None
    previous_cursor: Optional[str] = None


@dataclass
class UnifiedLogEntry:
    """统一日志条目"""

    execution_id: str
    log_category: str  # LogCategoryEnum
    event_type: str  # LogEventTypeEnum
    level: str  # LogLevelEnum
    message: str
    timestamp: Optional[str] = None
    user_friendly_message: Optional[str] = None
    display_priority: int = 5
    is_milestone: bool = False

    # 节点信息
    node_id: Optional[str] = None
    node_name: Optional[str] = None
    node_type: Optional[str] = None

    # 进度信息
    step_number: Optional[int] = None
    total_steps: Optional[int] = None
    progress_percentage: Optional[float] = None
    duration_seconds: Optional[int] = None

    # 结构化数据
    data: Optional[Dict[str, Any]] = None
    technical_details: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None
    performance_metrics: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.data is None:
            self.data = {}
        if self.technical_details is None:
            self.technical_details = {}
        if self.performance_metrics is None:
            self.performance_metrics = {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "execution_id": self.execution_id,
            "log_category": self.log_category,
            "event_type": self.event_type,
            "level": self.level,
            "message": self.message,
            "user_friendly_message": self.user_friendly_message,
            "display_priority": self.display_priority,
            "is_milestone": self.is_milestone,
            "timestamp": self.timestamp,
            "node_id": self.node_id,
            "node_name": self.node_name,
            "node_type": self.node_type,
            "step_number": self.step_number,
            "total_steps": self.total_steps,
            "progress_percentage": self.progress_percentage,
            "duration_seconds": self.duration_seconds,
            "data": self.data,
            "technical_details": self.technical_details,
            "stack_trace": self.stack_trace,
            "performance_metrics": self.performance_metrics,
        }


class UnifiedExecutionLogService:
    """统一执行日志服务 - 支持技术和业务日志"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Redis连接
        self.redis_client = None
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host="localhost", port=6379, db=1, decode_responses=True
                )
                self.redis_client.ping()
                self.logger.info("Redis connection established for unified log service")
            except Exception as e:
                self.logger.warning(f"Redis connection failed: {e}")
                self.redis_client = None

        # 内存缓存
        self._memory_cache: Dict[str, List[UnifiedLogEntry]] = {}

        # WebSocket连接管理
        self._websocket_connections: Dict[str, List[Any]] = {}

    async def add_technical_log(
        self,
        execution_id: str,
        level: str,
        message: str,
        event_type: str,
        node_id: Optional[str] = None,
        node_name: Optional[str] = None,
        node_type: Optional[str] = None,
        technical_details: Optional[Dict[str, Any]] = None,
        stack_trace: Optional[str] = None,
        performance_metrics: Optional[Dict[str, Any]] = None,
        duration_seconds: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None,
    ):
        """添加技术调试日志"""
        log_entry = UnifiedLogEntry(
            execution_id=execution_id,
            log_category=LogCategoryEnum.TECHNICAL.value if LogCategoryEnum else "technical",
            level=level,
            message=message,
            event_type=event_type,
            node_id=node_id,
            node_name=node_name,
            node_type=node_type,
            technical_details=technical_details,
            stack_trace=stack_trace,
            performance_metrics=performance_metrics,
            duration_seconds=duration_seconds,
            data=data,
            display_priority=DisplayPriorityEnum.LOW.value
            if DisplayPriorityEnum
            else 3,  # 技术日志通常优先级较低
        )
        await self._store_log_entry(log_entry)

    async def add_business_log(
        self,
        execution_id: str,
        event_type: str,
        technical_message: str,
        user_friendly_message: str,
        level: str = "INFO",
        display_priority: Optional[int] = None,
        is_milestone: bool = False,
        step_number: Optional[int] = None,
        total_steps: Optional[int] = None,
        progress_percentage: Optional[float] = None,
        duration_seconds: Optional[int] = None,
        node_id: Optional[str] = None,
        node_name: Optional[str] = None,
        node_type: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ):
        """添加业务友好日志"""
        if display_priority is None:
            display_priority = DisplayPriorityEnum.NORMAL.value if DisplayPriorityEnum else 5

        log_entry = UnifiedLogEntry(
            execution_id=execution_id,
            log_category=LogCategoryEnum.BUSINESS.value if LogCategoryEnum else "business",
            level=level,
            message=technical_message,
            user_friendly_message=user_friendly_message,
            event_type=event_type,
            display_priority=display_priority,
            is_milestone=is_milestone,
            step_number=step_number,
            total_steps=total_steps,
            progress_percentage=progress_percentage,
            duration_seconds=duration_seconds,
            node_id=node_id,
            node_name=node_name,
            node_type=node_type,
            data=data,
        )
        await self._store_log_entry(log_entry)

    async def _store_log_entry(self, entry: UnifiedLogEntry):
        """存储日志条目"""
        try:
            # 1. 存储到Redis缓存
            if self.redis_client:
                await self._store_to_redis(entry)
            else:
                await self._store_to_memory(entry)

            # 2. 推送到WebSocket连接
            await self._push_to_websockets(entry)

            # 3. 异步存储到数据库
            asyncio.create_task(self._store_to_database(entry))

        except Exception as e:
            self.logger.error(f"Failed to store log entry: {e}")

    async def _store_to_redis(self, entry: UnifiedLogEntry):
        """存储到Redis"""
        try:
            # 分类存储 - 技术日志和业务日志分开缓存
            tech_key = f"workflow_logs:technical:{entry.execution_id}"
            business_key = f"workflow_logs:business:{entry.execution_id}"

            value = json.dumps(entry.to_dict(), ensure_ascii=False)

            if entry.log_category == (
                LogCategoryEnum.TECHNICAL.value if LogCategoryEnum else "technical"
            ):
                self.redis_client.lpush(tech_key, value)
                self.redis_client.expire(tech_key, 24 * 3600)  # 24小时过期
            else:
                self.redis_client.lpush(business_key, value)
                self.redis_client.expire(business_key, 7 * 24 * 3600)  # 业务日志保留7天

            # 全局最近日志
            global_key = f"recent_logs:{entry.log_category}"
            self.redis_client.lpush(global_key, value)
            self.redis_client.ltrim(global_key, 0, 999)  # 保留最近1000条

        except Exception as e:
            self.logger.error(f"Failed to store to Redis: {e}")
            await self._store_to_memory(entry)

    async def _store_to_memory(self, entry: UnifiedLogEntry):
        """存储到内存缓存"""
        cache_key = f"{entry.execution_id}:{entry.log_category}"
        if cache_key not in self._memory_cache:
            self._memory_cache[cache_key] = []

        self._memory_cache[cache_key].append(entry)

        # 限制内存缓存大小
        if len(self._memory_cache[cache_key]) > 500:
            self._memory_cache[cache_key] = self._memory_cache[cache_key][-200:]

    async def _store_to_database(self, entry: UnifiedLogEntry):
        """存储到数据库"""
        if not DATABASE_AVAILABLE:
            return

        try:
            db = get_db_session()
            try:
                db_log = WorkflowExecutionLog(
                    execution_id=entry.execution_id,
                    log_category=LogCategoryEnum(entry.log_category),
                    event_type=entry.event_type,  # Pass string directly, SQLAlchemy will handle enum conversion
                    level=LogLevelEnum(entry.level),
                    message=entry.message,
                    user_friendly_message=entry.user_friendly_message,
                    display_priority=entry.display_priority,
                    is_milestone=entry.is_milestone,
                    data=entry.data or {},
                    node_id=entry.node_id,
                    node_name=entry.node_name,
                    node_type=entry.node_type,
                    step_number=entry.step_number,
                    total_steps=entry.total_steps,
                    progress_percentage=entry.progress_percentage,
                    duration_seconds=entry.duration_seconds,
                    technical_details=entry.technical_details or {},
                    stack_trace=entry.stack_trace,
                    performance_metrics=entry.performance_metrics or {},
                )

                db.add(db_log)
                db.commit()

            finally:
                db.close()

        except Exception as e:
            self.logger.error(f"Failed to store to database: {e}")

    async def _push_to_websockets(self, entry: UnifiedLogEntry):
        """推送到WebSocket连接"""
        execution_id = entry.execution_id
        if execution_id in self._websocket_connections:
            active_connections = []
            for websocket in self._websocket_connections[execution_id]:
                try:
                    await websocket.send_text(json.dumps(entry.to_dict(), ensure_ascii=False))
                    active_connections.append(websocket)
                except Exception:
                    pass

            self._websocket_connections[execution_id] = active_connections
            if not active_connections:
                del self._websocket_connections[execution_id]

    async def get_business_logs(
        self,
        execution_id: str,
        min_priority: int = 5,
        milestones_only: bool = False,
        limit: int = 100,
        page: int = 1,
        cursor: Optional[str] = None,
    ) -> PaginationResult:
        """获取业务友好日志 - 前端用户界面（支持分页）"""
        # 验证参数
        limit = max(1, min(limit, 100))  # 限制每页最多100条
        page = max(1, page)

        try:
            # 优先从数据库获取（支持更准确的分页）
            if DATABASE_AVAILABLE:
                return await self._get_business_logs_from_database_paginated(
                    execution_id, min_priority, milestones_only, limit, page, cursor
                )

            # 备选：从Redis获取（较简单的分页支持）
            if self.redis_client:
                return await self._get_business_logs_from_redis_paginated(
                    execution_id, min_priority, milestones_only, limit, page
                )

            return PaginationResult(
                data=[],
                total_count=0,
                page=page,
                page_size=limit,
                has_next=False,
                has_previous=False,
            )

        except Exception as e:
            self.logger.error(f"Failed to get business logs: {e}")
            return PaginationResult(
                data=[],
                total_count=0,
                page=page,
                page_size=limit,
                has_next=False,
                has_previous=False,
            )

    async def get_technical_logs(
        self,
        execution_id: str,
        level: Optional[str] = None,
        limit: int = 100,
        page: int = 1,
        cursor: Optional[str] = None,
    ) -> PaginationResult:
        """获取技术调试日志 - AI Agent分析（支持分页）"""
        # 验证参数
        limit = max(1, min(limit, 100))
        page = max(1, page)

        try:
            # 优先从数据库获取（支持更准确的分页）
            if DATABASE_AVAILABLE:
                return await self._get_technical_logs_from_database_paginated(
                    execution_id, level, limit, page, cursor
                )

            # 备选：从Redis获取
            if self.redis_client:
                return await self._get_technical_logs_from_redis_paginated(
                    execution_id, level, limit, page
                )

            return PaginationResult(
                data=[],
                total_count=0,
                page=page,
                page_size=limit,
                has_next=False,
                has_previous=False,
            )

        except Exception as e:
            self.logger.error(f"Failed to get technical logs: {e}")
            return PaginationResult(
                data=[],
                total_count=0,
                page=page,
                page_size=limit,
                has_next=False,
                has_previous=False,
            )

    async def _get_business_logs_from_redis(
        self, execution_id: str, min_priority: int, milestones_only: bool, limit: int, offset: int
    ) -> List[Dict[str, Any]]:
        """从Redis获取业务日志"""
        try:
            key = f"workflow_logs:business:{execution_id}"
            raw_logs = self.redis_client.lrange(key, 0, -1)

            logs = []
            for raw_log in reversed(raw_logs):
                log = json.loads(raw_log)

                # 应用过滤条件
                if log.get("display_priority", 5) < min_priority:
                    continue
                if milestones_only and not log.get("is_milestone", False):
                    continue

                logs.append(log)

            # 应用分页
            return logs[offset : offset + limit]

        except Exception as e:
            self.logger.error(f"Failed to get business logs from Redis: {e}")
            return []

    async def _get_business_logs_from_database(
        self, execution_id: str, min_priority: int, milestones_only: bool, limit: int, offset: int
    ) -> List[Dict[str, Any]]:
        """从数据库获取业务日志"""
        try:
            db = get_db_session()
            try:
                query = db.query(WorkflowExecutionLog).filter(
                    WorkflowExecutionLog.execution_id == execution_id,
                    WorkflowExecutionLog.log_category == LogCategoryEnum.BUSINESS,
                    WorkflowExecutionLog.display_priority >= min_priority,
                )

                if milestones_only:
                    query = query.filter(WorkflowExecutionLog.is_milestone == True)

                results = (
                    query.order_by(WorkflowExecutionLog.created_at.asc())
                    .offset(offset)
                    .limit(limit)
                    .all()
                )

                logs = []
                for log_entry in results:
                    log_dict = log_entry.to_dict()
                    # 优先显示用户友好消息
                    log_dict["display_message"] = log_entry.display_message
                    logs.append(log_dict)

                return logs

            finally:
                db.close()

        except Exception as e:
            self.logger.error(f"Failed to get business logs from database: {e}")
            return []

    async def _get_business_logs_from_database_paginated(
        self,
        execution_id: str,
        min_priority: int,
        milestones_only: bool,
        limit: int,
        page: int,
        cursor: Optional[str] = None,
    ) -> PaginationResult:
        """从数据库获取业务日志（分页）"""
        try:
            db = get_db_session()
            try:
                # 构建基础查询
                base_query = db.query(WorkflowExecutionLog).filter(
                    WorkflowExecutionLog.execution_id == execution_id,
                    WorkflowExecutionLog.log_category == LogCategoryEnum.BUSINESS,
                    WorkflowExecutionLog.display_priority >= min_priority,
                )

                if milestones_only:
                    base_query = base_query.filter(WorkflowExecutionLog.is_milestone == True)

                # 获取总数量
                total_count = base_query.count()

                # 处理游标分页
                if cursor:
                    try:
                        cursor_data = json.loads(base64.b64decode(cursor).decode("utf-8"))
                        cursor_timestamp = cursor_data.get("timestamp")
                        cursor_id = cursor_data.get("id")

                        if cursor_timestamp and cursor_id:
                            # 游标分页查询
                            base_query = base_query.filter(
                                (WorkflowExecutionLog.created_at > cursor_timestamp)
                                | (
                                    (WorkflowExecutionLog.created_at == cursor_timestamp)
                                    & (WorkflowExecutionLog.id > cursor_id)
                                )
                            )
                    except Exception as e:
                        self.logger.warning(
                            f"Invalid cursor, falling back to offset pagination: {e}"
                        )
                        cursor = None

                # 如果没有有效游标，使用offset分页
                if not cursor:
                    offset = (page - 1) * limit
                    base_query = base_query.offset(offset)

                # 执行查询
                results = (
                    base_query.order_by(
                        WorkflowExecutionLog.created_at.asc(), WorkflowExecutionLog.id.asc()
                    )
                    .limit(limit + 1)
                    .all()
                )  # +1用于检测是否有下一页

                # 处理结果
                has_next = len(results) > limit
                if has_next:
                    results = results[:limit]

                logs = []
                last_item = None
                for log_entry in results:
                    log_dict = log_entry.to_dict()
                    log_dict["display_message"] = log_entry.display_message
                    logs.append(log_dict)
                    last_item = log_entry

                # 生成下一页游标
                next_cursor = None
                if has_next and last_item:
                    cursor_data = {
                        "timestamp": last_item.created_at.isoformat(),
                        "id": last_item.id,
                    }
                    next_cursor = base64.b64encode(json.dumps(cursor_data).encode("utf-8")).decode(
                        "utf-8"
                    )

                # 计算分页信息
                has_previous = page > 1 if not cursor else bool(cursor)

                return PaginationResult(
                    data=logs,
                    total_count=total_count,
                    page=page,
                    page_size=limit,
                    has_next=has_next,
                    has_previous=has_previous,
                    next_cursor=next_cursor,
                )

            finally:
                db.close()

        except Exception as e:
            self.logger.error(f"Failed to get paginated business logs from database: {e}")
            return PaginationResult(
                data=[],
                total_count=0,
                page=page,
                page_size=limit,
                has_next=False,
                has_previous=False,
            )

    async def _get_technical_logs_from_redis(
        self, execution_id: str, level: Optional[str], limit: int, offset: int
    ) -> List[Dict[str, Any]]:
        """从Redis获取技术日志"""
        try:
            key = f"workflow_logs:technical:{execution_id}"
            raw_logs = self.redis_client.lrange(key, 0, -1)

            logs = []
            for raw_log in reversed(raw_logs):
                log = json.loads(raw_log)

                if level and log.get("level") != level:
                    continue

                logs.append(log)

            return logs[offset : offset + limit]

        except Exception as e:
            self.logger.error(f"Failed to get technical logs from Redis: {e}")
            return []

    async def _get_business_logs_from_redis_paginated(
        self, execution_id: str, min_priority: int, milestones_only: bool, limit: int, page: int
    ) -> PaginationResult:
        """从Redis获取业务日志（简单分页）"""
        try:
            key = f"workflow_logs:business:{execution_id}"
            raw_logs = self.redis_client.lrange(key, 0, -1)

            # 过滤日志
            all_logs = []
            for raw_log in reversed(raw_logs):  # 按时间正序
                log = json.loads(raw_log)

                if log.get("display_priority", 5) < min_priority:
                    continue
                if milestones_only and not log.get("is_milestone", False):
                    continue

                all_logs.append(log)

            # 分页计算
            total_count = len(all_logs)
            offset = (page - 1) * limit
            logs = all_logs[offset : offset + limit]

            has_next = offset + limit < total_count
            has_previous = page > 1

            return PaginationResult(
                data=logs,
                total_count=total_count,
                page=page,
                page_size=limit,
                has_next=has_next,
                has_previous=has_previous,
            )

        except Exception as e:
            self.logger.error(f"Failed to get paginated business logs from Redis: {e}")
            return PaginationResult(
                data=[],
                total_count=0,
                page=page,
                page_size=limit,
                has_next=False,
                has_previous=False,
            )

    async def _get_technical_logs_from_redis_paginated(
        self, execution_id: str, level: Optional[str], limit: int, page: int
    ) -> PaginationResult:
        """从Redis获取技术日志（简单分页）"""
        try:
            key = f"workflow_logs:technical:{execution_id}"
            raw_logs = self.redis_client.lrange(key, 0, -1)

            # 过滤日志
            all_logs = []
            for raw_log in reversed(raw_logs):  # 按时间正序
                log = json.loads(raw_log)

                if level and log.get("level") != level:
                    continue

                all_logs.append(log)

            # 分页计算
            total_count = len(all_logs)
            offset = (page - 1) * limit
            logs = all_logs[offset : offset + limit]

            has_next = offset + limit < total_count
            has_previous = page > 1

            return PaginationResult(
                data=logs,
                total_count=total_count,
                page=page,
                page_size=limit,
                has_next=has_next,
                has_previous=has_previous,
            )

        except Exception as e:
            self.logger.error(f"Failed to get paginated technical logs from Redis: {e}")
            return PaginationResult(
                data=[],
                total_count=0,
                page=page,
                page_size=limit,
                has_next=False,
                has_previous=False,
            )

    async def _get_technical_logs_from_database(
        self, execution_id: str, level: Optional[str], limit: int, offset: int
    ) -> List[Dict[str, Any]]:
        """从数据库获取技术日志"""
        try:
            db = get_db_session()
            try:
                query = db.query(WorkflowExecutionLog).filter(
                    WorkflowExecutionLog.execution_id == execution_id,
                    WorkflowExecutionLog.log_category == LogCategoryEnum.TECHNICAL,
                )

                if level:
                    query = query.filter(WorkflowExecutionLog.level == LogLevelEnum(level))

                results = (
                    query.order_by(WorkflowExecutionLog.created_at.asc())
                    .offset(offset)
                    .limit(limit)
                    .all()
                )

                return [log_entry.to_dict() for log_entry in results]

            finally:
                db.close()

        except Exception as e:
            self.logger.error(f"Failed to get technical logs from database: {e}")
            return []

    async def _get_technical_logs_from_database_paginated(
        self,
        execution_id: str,
        level: Optional[str],
        limit: int,
        page: int,
        cursor: Optional[str] = None,
    ) -> PaginationResult:
        """从数据库获取技术日志（分页）"""
        try:
            db = get_db_session()
            try:
                # 构建基础查询
                base_query = db.query(WorkflowExecutionLog).filter(
                    WorkflowExecutionLog.execution_id == execution_id,
                    WorkflowExecutionLog.log_category == LogCategoryEnum.TECHNICAL,
                )

                if level:
                    base_query = base_query.filter(
                        WorkflowExecutionLog.level == LogLevelEnum(level)
                    )

                # 获取总数量
                total_count = base_query.count()

                # 处理游标分页
                if cursor:
                    try:
                        cursor_data = json.loads(base64.b64decode(cursor).decode("utf-8"))
                        cursor_timestamp = cursor_data.get("timestamp")
                        cursor_id = cursor_data.get("id")

                        if cursor_timestamp and cursor_id:
                            base_query = base_query.filter(
                                (WorkflowExecutionLog.created_at > cursor_timestamp)
                                | (
                                    (WorkflowExecutionLog.created_at == cursor_timestamp)
                                    & (WorkflowExecutionLog.id > cursor_id)
                                )
                            )
                    except Exception as e:
                        self.logger.warning(
                            f"Invalid cursor, falling back to offset pagination: {e}"
                        )
                        cursor = None

                # 如果没有有效游标，使用offset分页
                if not cursor:
                    offset = (page - 1) * limit
                    base_query = base_query.offset(offset)

                # 执行查询
                results = (
                    base_query.order_by(
                        WorkflowExecutionLog.created_at.asc(), WorkflowExecutionLog.id.asc()
                    )
                    .limit(limit + 1)
                    .all()
                )

                # 处理结果
                has_next = len(results) > limit
                if has_next:
                    results = results[:limit]

                logs = [log_entry.to_dict() for log_entry in results]

                # 生成下一页游标
                next_cursor = None
                if has_next and results:
                    last_item = results[-1]
                    cursor_data = {
                        "timestamp": last_item.created_at.isoformat(),
                        "id": last_item.id,
                    }
                    next_cursor = base64.b64encode(json.dumps(cursor_data).encode("utf-8")).decode(
                        "utf-8"
                    )

                has_previous = page > 1 if not cursor else bool(cursor)

                return PaginationResult(
                    data=logs,
                    total_count=total_count,
                    page=page,
                    page_size=limit,
                    has_next=has_next,
                    has_previous=has_previous,
                    next_cursor=next_cursor,
                )

            finally:
                db.close()

        except Exception as e:
            self.logger.error(f"Failed to get paginated technical logs from database: {e}")
            return PaginationResult(
                data=[],
                total_count=0,
                page=page,
                page_size=limit,
                has_next=False,
                has_previous=False,
            )

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

    def clear_logs(self, execution_id: str):
        """清空日志缓存"""
        if self.redis_client:
            self.redis_client.delete(f"workflow_logs:business:{execution_id}")
            self.redis_client.delete(f"workflow_logs:technical:{execution_id}")

        # 清空内存缓存
        keys_to_remove = [k for k in self._memory_cache.keys() if k.startswith(execution_id)]
        for key in keys_to_remove:
            del self._memory_cache[key]


# 全局服务实例
_unified_log_service: Optional[UnifiedExecutionLogService] = None


def get_unified_log_service() -> UnifiedExecutionLogService:
    """获取统一日志服务单例"""
    global _unified_log_service
    if _unified_log_service is None:
        _unified_log_service = UnifiedExecutionLogService()
    return _unified_log_service


# 便捷函数 - 与现有的BusinessLogger兼容
def create_legacy_compatible_logger(execution_id: str, workflow_name: str = "Unnamed Workflow"):
    """创建与现有BusinessLogger兼容的日志记录器"""

    class LegacyCompatibleLogger:
        def __init__(self, execution_id: str, workflow_name: str):
            self.execution_id = execution_id
            self.workflow_name = workflow_name
            self.service = get_unified_log_service()

        async def workflow_started(self, total_steps: int, trigger_info: Optional[str] = None):
            trigger_msg = f" | 触发方式: {trigger_info}" if trigger_info else ""
            technical_msg = f"Starting workflow: {self.workflow_name} with {total_steps} steps"
            user_msg = f"🚀 开始执行: {self.workflow_name} | 总步骤: {total_steps}{trigger_msg}"

            await self.service.add_business_log(
                execution_id=self.execution_id,
                event_type="workflow_started",
                technical_message=technical_msg,
                user_friendly_message=user_msg,
                display_priority=DisplayPriorityEnum.HIGH.value if DisplayPriorityEnum else 7,
                is_milestone=True,
                total_steps=total_steps,
            )

        async def step_completed(
            self, step_name: str, duration_seconds: float, status: str = "SUCCESS"
        ):
            technical_msg = f"Step '{step_name}' completed with status: {status}"
            icon = "✅" if status == "SUCCESS" else "❌" if status == "ERROR" else "⏸️"
            user_msg = f"{icon} {step_name} | 状态: {status} | 耗时: {duration_seconds:.1f}秒"

            await self.service.add_business_log(
                execution_id=self.execution_id,
                event_type="step_completed",
                technical_message=technical_msg,
                user_friendly_message=user_msg,
                display_priority=DisplayPriorityEnum.NORMAL.value if DisplayPriorityEnum else 5,
                duration_seconds=int(duration_seconds),
                node_name=step_name,
            )

    return LegacyCompatibleLogger(execution_id, workflow_name)
