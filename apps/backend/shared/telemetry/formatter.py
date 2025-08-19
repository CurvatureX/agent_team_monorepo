"""
CloudWatch 优化的日志格式化器

提供：
1. 结构化 JSON 日志格式
2. 自动包含 tracking_id
3. CloudWatch Logs Insights 优化
4. ERROR 级别自动创建 Span Events
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Set

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode


class CloudWatchTracingFormatter(logging.Formatter):
    """
    CloudWatch 优化的追踪日志格式化器

    特性：
    - JSON 格式输出
    - 自动包含 tracking_id (使用 OpenTelemetry trace_id)
    - 支持嵌套字段便于 CloudWatch 查询
    - ERROR 级别自动创建 OpenTelemetry Span Events
    - 字段数量限制避免 CloudWatch 截断
    """

    # 排除的内部字段
    EXCLUDED_FIELDS: Set[str] = {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "getMessage",
        "message",
    }

    # 最大字段数量限制
    MAX_FIELDS = 900

    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为 CloudWatch 优化的 JSON 格式"""

        # 获取当前请求的 tracking_id
        tracking_id = self._get_tracking_id(record)

        # 基础日志条目
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        # 构建文件位置信息 (更简洁的格式)
        file_location = f"{record.filename}:{record.lineno}"

        log_entry = {
            "@timestamp": timestamp,
            "@level": record.levelname,
            "@message": record.getMessage(),
            "level": record.levelname,  # 重复字段，便于查询
            "timestamp": timestamp,  # 重复字段，便于查询
            "file": file_location,  # 新增：文件:行号 格式
            "service": self.service_name,
            "tracking_id": tracking_id,
            "source": {
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
                "filename": record.filename,
                "pathname": record.pathname,
            },
        }

        # 处理异常信息
        if record.exc_info:
            log_entry["exception"] = {
                "class": record.exc_info[1].__class__.__name__,
                "message": str(record.exc_info[1]),
                "stack_trace": self.formatException(record.exc_info),
            }

        # 结构化额外字段
        self._add_structured_fields(log_entry, record)

        # 添加追踪信息
        self._add_tracing_info(log_entry, tracking_id)

        # ERROR 级别自动创建 span event
        if record.levelno >= logging.ERROR:
            self._create_span_event(record, tracking_id)

        # 限制字段数量
        log_entry = self._limit_fields(log_entry)

        return json.dumps(log_entry, ensure_ascii=False, separators=(",", ":"))

    def _get_tracking_id(self, record: logging.LogRecord) -> str:
        """获取 tracking_id"""

        # 优先使用记录中的 tracking_id
        tracking_id = getattr(record, "tracking_id", None)
        if tracking_id:
            return tracking_id

        # 从当前 span 获取 trace_id
        span = trace.get_current_span()
        if span.is_recording():
            span_context = span.get_span_context()
            return format(span_context.trace_id, "032x")

        return "unknown"

    def _add_structured_fields(self, log_entry: Dict[str, Any], record: logging.LogRecord) -> None:
        """添加结构化字段，按类型分组便于 CloudWatch 查询"""

        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in self.EXCLUDED_FIELDS:
                extra_fields[key] = value

        # HTTP 请求相关字段
        if any(k.startswith("request_") for k in extra_fields.keys()):
            log_entry["request"] = {}
            for key, value in extra_fields.items():
                if key.startswith("request_"):
                    field_name = key.replace("request_", "")
                    log_entry["request"][field_name] = value

        # HTTP 响应相关字段
        if any(k.startswith("response_") for k in extra_fields.keys()):
            log_entry["response"] = {}
            for key, value in extra_fields.items():
                if key.startswith("response_"):
                    field_name = key.replace("response_", "")
                    log_entry["response"][field_name] = value

        # 用户相关字段
        if any(k.startswith("user_") for k in extra_fields.keys()):
            log_entry["user"] = {}
            for key, value in extra_fields.items():
                if key.startswith("user_"):
                    field_name = key.replace("user_", "")
                    log_entry["user"][field_name] = value

        # 会话相关字段
        if any(k.startswith("session_") for k in extra_fields.keys()):
            log_entry["session"] = {}
            for key, value in extra_fields.items():
                if key.startswith("session_"):
                    field_name = key.replace("session_", "")
                    log_entry["session"][field_name] = value

        # 工作流相关字段
        if any(k.startswith("workflow_") for k in extra_fields.keys()):
            log_entry["workflow"] = {}
            for key, value in extra_fields.items():
                if key.startswith("workflow_"):
                    field_name = key.replace("workflow_", "")
                    log_entry["workflow"][field_name] = value

        # 操作相关字段
        if any(k.startswith("operation_") for k in extra_fields.keys()):
            log_entry["operation"] = {}
            for key, value in extra_fields.items():
                if key.startswith("operation_"):
                    field_name = key.replace("operation_", "")
                    log_entry["operation"][field_name] = value

        # 错误相关字段
        if any(k.startswith("error_") for k in extra_fields.keys()):
            log_entry["error"] = {}
            for key, value in extra_fields.items():
                if key.startswith("error_"):
                    field_name = key.replace("error_", "")
                    log_entry["error"][field_name] = value

        # 其他字段直接添加
        for key, value in extra_fields.items():
            if not any(
                key.startswith(prefix)
                for prefix in [
                    "request_",
                    "response_",
                    "user_",
                    "session_",
                    "workflow_",
                    "operation_",
                    "error_",
                ]
            ):
                log_entry[key] = value

    def _add_tracing_info(self, log_entry: Dict[str, Any], tracking_id: str) -> None:
        """添加追踪信息"""

        span = trace.get_current_span()
        if span.is_recording():
            span_context = span.get_span_context()
            log_entry["tracing"] = {
                "trace_id": tracking_id,  # 与 tracking_id 相同
                "span_id": format(span_context.span_id, "016x"),
            }

    def _create_span_event(self, record: logging.LogRecord, tracking_id: str) -> None:
        """为 ERROR 级别日志创建 OpenTelemetry Span Event"""

        span = trace.get_current_span()
        if not span or not span.get_span_context().is_valid:
            return

        try:
            # 记录异常信息
            if record.exc_info:
                exception = record.exc_info[1]
                span.record_exception(exception)
                span.set_status(Status(StatusCode.ERROR, record.getMessage()))

            # 创建错误事件
            span.add_event(
                name="error_log",
                attributes={
                    "log.level": record.levelname,
                    "log.message": record.getMessage(),
                    "log.logger": record.name,
                    "log.module": record.module,
                    "log.function": record.funcName,
                    "log.line": record.lineno,
                    "tracking.id": tracking_id,
                    "error.type": (
                        type(record.exc_info[1]).__name__ if record.exc_info else "UnknownError"
                    ),
                },
                timestamp=time.time_ns(),
            )

        except Exception as e:
            # 避免日志记录导致的错误影响主流程
            print(f"Failed to create span event: {e}")

    def _count_fields(self, obj: Any, depth: int = 0) -> int:
        """递归计算对象中的字段数量"""
        if depth > 5:  # 防止无限递归
            return 1

        if isinstance(obj, dict):
            count = len(obj)
            for value in obj.values():
                count += self._count_fields(value, depth + 1)
            return count
        elif isinstance(obj, (list, tuple)):
            count = len(obj)
            for item in obj:
                count += self._count_fields(item, depth + 1)
            return count
        else:
            return 1

    def _limit_fields(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """限制字段数量，避免 CloudWatch 截断"""

        if self._count_fields(log_entry) <= self.MAX_FIELDS:
            return log_entry

        # 保留核心字段，移除详细字段
        essential_fields = {
            "@timestamp",
            "@level",
            "@message",
            "service",
            "tracking_id",
            "source",
            "tracing",
        }

        limited_entry = {}
        for key, value in log_entry.items():
            if key in essential_fields:
                limited_entry[key] = value
            elif isinstance(value, dict) and len(value) <= 5:
                # 保留小的嵌套对象
                limited_entry[key] = value

        # 添加字段截断警告
        limited_entry["_field_limit_exceeded"] = True
        limited_entry["_original_field_count"] = self._count_fields(log_entry)

        return limited_entry
