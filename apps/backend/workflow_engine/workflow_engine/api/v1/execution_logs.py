"""
Execution Logs API Routes
执行日志API路由 - 提供实时和历史日志查询接口
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Path, Query, WebSocket, WebSocketDisconnect, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from workflow_engine.services.execution_log_service import (
    ExecutionLogEntry,
    LogEventType,
    get_execution_log_service,
)
from workflow_engine.services.unified_log_service import get_unified_log_service


# Pydantic models for API
class LogQueryParams(BaseModel):
    """日志查询参数"""

    limit: int = Field(default=100, ge=1, le=1000, description="返回条数，1-1000")
    offset: int = Field(default=0, ge=0, description="偏移量，从0开始")
    level: Optional[str] = Field(default=None, description="日志级别过滤 (INFO, ERROR, DEBUG)")
    event_type: Optional[str] = Field(default=None, description="事件类型过滤")
    start_time: Optional[datetime] = Field(default=None, description="开始时间过滤")
    end_time: Optional[datetime] = Field(default=None, description="结束时间过滤")


class PaginatedLogQueryParams(BaseModel):
    """分页日志查询参数"""

    page: int = Field(default=1, ge=1, description="页码，从1开始")
    page_size: int = Field(default=20, ge=1, le=100, description="每页条数，最大100")
    cursor: Optional[str] = Field(default=None, description="游标，用于游标分页")


class PaginationInfo(BaseModel):
    """分页信息"""

    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页条数")
    total_count: int = Field(description="总条数")
    has_next: bool = Field(description="是否有下一页")
    has_previous: bool = Field(description="是否有上一页")
    next_cursor: Optional[str] = Field(default=None, description="下一页游标")
    previous_cursor: Optional[str] = Field(default=None, description="上一页游标")


class PaginatedLogResponse(BaseModel):
    """分页日志查询响应"""

    execution_id: str
    logs: List[Dict[str, Any]]
    pagination: PaginationInfo


class LogQueryResponse(BaseModel):
    """日志查询响应"""

    execution_id: str
    total_count: int
    logs: List[Dict[str, Any]]
    pagination: Dict[str, Any]


class ActiveExecutionResponse(BaseModel):
    """活跃执行响应"""

    executions: List[Dict[str, Any]]
    total_count: int


class ExecutionStatsResponse(BaseModel):
    """执行统计响应"""

    execution_id: str
    workflow_name: str
    total_steps: int
    completed_steps: int
    failed_steps: int
    total_duration: float
    average_step_time: float
    slowest_step: Optional[Dict[str, Any]]
    performance_metrics: Dict[str, Any]


class CleanupRequest(BaseModel):
    """清理请求"""

    before_date: datetime = Field(description="删除此日期前的日志")
    keep_recent: Optional[int] = Field(default=None, description="保留最近N条执行的日志")


class LogStatsResponse(BaseModel):
    """日志统计响应"""

    total_executions: int
    active_executions: int
    total_log_entries: int
    cache_size_mb: float
    active_websocket_connections: int


# 创建路由器
router = APIRouter(prefix="/v1/workflows", tags=["execution-logs"])

# 日志记录器
logger = logging.getLogger(__name__)


@router.websocket("/executions/{execution_id}/logs/stream")
async def websocket_log_stream(
    websocket: WebSocket, execution_id: str = Path(..., description="执行ID")
):
    """
    WebSocket实时日志流

    连接到此端点以实时接收workflow执行日志。
    """
    log_service = get_execution_log_service()

    try:
        await websocket.accept()
        logger.info(f"WebSocket连接已建立: execution_id={execution_id}")

        # 添加WebSocket连接到服务
        log_service.add_websocket_connection(execution_id, websocket)

        # 发送历史日志(最近50条)
        try:
            historical_logs = await log_service.get_logs(execution_id, limit=50)
            for log_entry in historical_logs:
                await websocket.send_text(json.dumps(log_entry, ensure_ascii=False))
        except Exception as e:
            logger.warning(f"发送历史日志失败: {e}")

        # 保持连接并等待新日志
        while True:
            # WebSocket心跳检测
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket连接断开: execution_id={execution_id}")
    except Exception as e:
        logger.error(f"WebSocket连接错误: {e}")
        try:
            await websocket.close(code=1000)
        except:
            pass
    finally:
        # 清理连接
        log_service.remove_websocket_connection(execution_id, websocket)


@router.get("/executions/{execution_id}/logs/stream")
async def sse_log_stream(execution_id: str = Path(..., description="执行ID")):
    """
    Server-Sent Events (SSE) 实时日志流

    使用SSE协议推送实时日志，适合不支持WebSocket的场景。
    """
    log_service = get_execution_log_service()

    async def event_stream():
        """事件流生成器"""
        try:
            # 发送历史日志
            historical_logs = await log_service.get_logs(execution_id, limit=50)
            for log_entry in historical_logs:
                yield f"event: log_entry\\ndata: {json.dumps(log_entry, ensure_ascii=False)}\\n\\n"

            # 创建一个临时的WebSocket连接来接收实时日志
            # 这里需要一个不同的机制，因为SSE是单向的
            # 暂时实现为定期轮询最新日志

            last_timestamp = None
            if historical_logs:
                last_timestamp = historical_logs[-1].get("timestamp")

            while True:
                # 每2秒检查一次新日志
                import asyncio

                await asyncio.sleep(2)

                # 获取新日志
                new_logs = await log_service.get_logs(execution_id, limit=10)

                for log_entry in new_logs:
                    if last_timestamp and log_entry.get("timestamp") <= last_timestamp:
                        continue

                    yield f"event: log_entry\\ndata: {json.dumps(log_entry, ensure_ascii=False)}\\n\\n"
                    last_timestamp = log_entry.get("timestamp")

        except Exception as e:
            logger.error(f"SSE流错误: {e}")
            yield f"event: error\\ndata: {{'error': 'Stream interrupted'}}\\n\\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get("/executions/{execution_id}/logs", response_model=LogQueryResponse)
async def get_execution_logs(
    execution_id: str = Path(..., description="执行ID"),
    limit: int = Query(default=100, ge=1, le=1000, description="返回条数"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    level: Optional[str] = Query(default=None, description="日志级别过滤"),
    event_type: Optional[str] = Query(default=None, description="事件类型过滤"),
    start_time: Optional[datetime] = Query(default=None, description="开始时间"),
    end_time: Optional[datetime] = Query(default=None, description="结束时间"),
):
    """
    获取执行日志列表

    支持分页和多种过滤条件，用于查询历史执行日志。
    """
    log_service = get_execution_log_service()

    try:
        result = await log_service.get_logs_with_filters(
            execution_id=execution_id,
            limit=limit,
            offset=offset,
            level=level,
            event_type=event_type,
            start_time=start_time,
            end_time=end_time,
        )
        return LogQueryResponse(**result)

    except Exception as e:
        logger.error(f"获取执行日志失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "LOG_SERVICE_ERROR", "message": "获取执行日志失败", "details": str(e)},
        )


@router.get("/executions/active", response_model=ActiveExecutionResponse)
async def get_active_executions():
    """
    获取当前活跃的执行列表

    返回所有正在运行或最近活跃的workflow执行。
    """
    log_service = get_execution_log_service()

    try:
        executions = await log_service.get_active_executions()
        return ActiveExecutionResponse(executions=executions, total_count=len(executions))

    except Exception as e:
        logger.error(f"获取活跃执行失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "LOG_SERVICE_ERROR", "message": "获取活跃执行失败", "details": str(e)},
        )


@router.get("/executions/{execution_id}/stats", response_model=ExecutionStatsResponse)
async def get_execution_stats(execution_id: str = Path(..., description="执行ID")):
    """
    获取执行统计信息

    返回指定执行的详细统计信息，包括性能指标。
    """
    log_service = get_execution_log_service()

    try:
        stats = await log_service.get_execution_stats(execution_id)

        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "EXECUTION_NOT_FOUND",
                    "message": "执行记录不存在",
                    "details": f"execution_id: {execution_id}",
                },
            )

        return ExecutionStatsResponse(**stats)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取执行统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "LOG_SERVICE_ERROR", "message": "获取执行统计失败", "details": str(e)},
        )


@router.delete("/executions/logs/cleanup")
async def cleanup_old_logs(cleanup_request: CleanupRequest):
    """
    清理历史日志

    删除指定日期之前的历史日志，支持保留最近的执行记录。
    """
    log_service = get_execution_log_service()

    try:
        result = await log_service.cleanup_old_logs(
            before_date=cleanup_request.before_date, keep_recent=cleanup_request.keep_recent
        )

        return {
            "message": f"成功清理 {result['deleted']} 条历史日志",
            "deleted_count": result["deleted"],
            "cleanup_date": cleanup_request.before_date.isoformat(),
        }

    except Exception as e:
        logger.error(f"清理历史日志失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "CLEANUP_ERROR", "message": "清理历史日志失败", "details": str(e)},
        )


@router.get("/logs/stats", response_model=LogStatsResponse)
async def get_log_stats():
    """
    获取日志系统统计信息

    返回日志系统的整体统计信息，包括缓存使用情况等。
    """
    log_service = get_execution_log_service()

    try:
        stats = await log_service.get_log_stats()

        return LogStatsResponse(
            total_executions=stats.get("total_executions", 0),
            active_executions=stats.get("active_executions", 0),
            total_log_entries=stats.get("total_log_entries", 0),
            cache_size_mb=stats.get("cache_size_mb", 0.0),
            active_websocket_connections=stats.get("active_websocket_connections", 0),
        )

    except Exception as e:
        logger.error(f"获取日志统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "LOG_SERVICE_ERROR", "message": "获取日志统计失败", "details": str(e)},
        )


# 新增的分类日志查询端点


@router.get("/executions/{execution_id}/logs/business", response_model=PaginatedLogResponse)
async def get_business_logs(
    execution_id: str = Path(..., description="执行ID"),
    min_priority: int = Query(default=5, ge=1, le=10, description="最小显示优先级"),
    milestones_only: bool = Query(default=False, description="只返回里程碑事件"),
    page: int = Query(default=1, ge=1, description="页码，从1开始"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数，最大100"),
    cursor: Optional[str] = Query(default=None, description="游标，用于游标分页"),
):
    """
    获取用户友好的业务日志（支持分页）

    专门用于前端用户界面展示，返回中文友好的日志信息。
    支持offset分页和cursor分页两种模式。

    使用 milestones_only=true 可获取里程碑事件，用于执行概览和进度追踪。
    """
    unified_service = get_unified_log_service()

    try:
        result = await unified_service.get_business_logs(
            execution_id=execution_id,
            min_priority=min_priority,
            milestones_only=milestones_only,
            limit=page_size,
            page=page,
            cursor=cursor,
        )

        return PaginatedLogResponse(
            execution_id=execution_id,
            logs=result.data,
            pagination=PaginationInfo(
                page=result.page,
                page_size=result.page_size,
                total_count=result.total_count,
                has_next=result.has_next,
                has_previous=result.has_previous,
                next_cursor=result.next_cursor,
                previous_cursor=result.previous_cursor,
            ),
        )

    except Exception as e:
        logger.error(f"获取业务日志失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "BUSINESS_LOG_ERROR", "message": "获取业务日志失败", "details": str(e)},
        )


@router.get("/executions/{execution_id}/logs/technical", response_model=PaginatedLogResponse)
async def get_technical_logs(
    execution_id: str = Path(..., description="执行ID"),
    level: Optional[str] = Query(default=None, description="日志级别过滤"),
    include_stack_trace: bool = Query(default=False, description="包含错误堆栈"),
    page: int = Query(default=1, ge=1, description="页码，从1开始"),
    page_size: int = Query(default=50, ge=1, le=100, description="每页条数，最大100"),
    cursor: Optional[str] = Query(default=None, description="游标，用于游标分页"),
):
    """
    获取技术调试日志（支持分页）

    专门用于开发调试和AI Agent分析，包含详细的技术信息。
    支持offset分页和cursor分页两种模式。
    """
    unified_service = get_unified_log_service()

    try:
        result = await unified_service.get_technical_logs(
            execution_id=execution_id, level=level, limit=page_size, page=page, cursor=cursor
        )

        # 如果不包含堆栈信息，过滤掉敏感的技术细节
        if not include_stack_trace:
            for log in result.data:
                if "stack_trace" in log:
                    log["stack_trace"] = None
                if "technical_details" in log and isinstance(log["technical_details"], dict):
                    # 只保留基本的技术信息，移除敏感数据
                    basic_details = {}
                    for key in ["status_code", "response_time_ms", "api_endpoint", "model"]:
                        if key in log["technical_details"]:
                            basic_details[key] = log["technical_details"][key]
                    log["technical_details"] = basic_details

        return PaginatedLogResponse(
            execution_id=execution_id,
            logs=result.data,
            pagination=PaginationInfo(
                page=result.page,
                page_size=result.page_size,
                total_count=result.total_count,
                has_next=result.has_next,
                has_previous=result.has_previous,
                next_cursor=result.next_cursor,
                previous_cursor=result.previous_cursor,
            ),
        )

    except Exception as e:
        logger.error(f"获取技术日志失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "TECHNICAL_LOG_ERROR", "message": "获取技术日志失败", "details": str(e)},
        )


# 兼容性端点：从现有ExecutionLog迁移数据
@router.post("/executions/{execution_id}/logs/migrate")
async def migrate_legacy_logs(
    execution_id: str = Path(..., description="执行ID"), legacy_logs: List[Dict[str, Any]] = []
):
    """
    迁移现有日志到统一格式

    用于将现有的ExecutionLog格式迁移到新的统一日志格式。
    """
    unified_service = get_unified_log_service()

    try:
        migrated_count = 0

        for log_data in legacy_logs:
            # 判断是技术日志还是业务日志
            level = log_data.get("level", "INFO")
            message = log_data.get("message", "")

            # 根据日志内容判断类型
            is_business_log = any(
                [
                    "工作流" in message,
                    "步骤" in message,
                    "完成" in message,
                    "开始" in message,
                    "成功" in message,
                    "失败" in message,
                ]
            )

            if is_business_log:
                await unified_service.add_business_log(
                    execution_id=execution_id,
                    event_type="separator",  # 默认事件类型
                    technical_message=message,
                    user_friendly_message=message,  # 如果没有友好消息，使用原消息
                    level=level,
                    node_id=log_data.get("node_id"),
                    data=log_data.get("extra_data", {}),
                )
            else:
                await unified_service.add_technical_log(
                    execution_id=execution_id,
                    level=level,
                    message=message,
                    event_type="separator",
                    node_id=log_data.get("node_id"),
                    technical_details=log_data.get("extra_data", {}),
                )

            migrated_count += 1

        return {
            "message": f"成功迁移 {migrated_count} 条日志",
            "migrated_count": migrated_count,
            "execution_id": execution_id,
        }

    except Exception as e:
        logger.error(f"迁移日志失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "MIGRATION_ERROR", "message": "迁移日志失败", "details": str(e)},
        )


# 辅助函数：添加日志条目（用于测试）
@router.post("/executions/{execution_id}/logs/test")
async def add_test_log_entry(
    execution_id: str = Path(..., description="执行ID"),
    message: str = Query(..., description="日志消息"),
    event_type: str = Query(default="separator", description="事件类型"),
    level: str = Query(default="INFO", description="日志级别"),
):
    """
    添加测试日志条目

    仅用于开发和测试目的，在生产环境中应该禁用。
    """
    log_service = get_execution_log_service()

    try:
        # 创建测试日志条目
        log_entry = ExecutionLogEntry(
            execution_id=execution_id,
            event_type=LogEventType(event_type),
            timestamp=datetime.now().isoformat(),
            message=message,
            level=level,
            data={"test": True, "api_generated": True},
        )

        # 添加到日志服务
        await log_service.add_log_entry(log_entry)

        return {"message": "测试日志条目已添加", "log_entry": log_entry.to_dict()}

    except Exception as e:
        logger.error(f"添加测试日志失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "TEST_LOG_ERROR", "message": "添加测试日志失败", "details": str(e)},
        )
