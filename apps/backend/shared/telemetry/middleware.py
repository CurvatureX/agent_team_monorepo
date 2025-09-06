"""
FastAPI 中间件 - 追踪和指标收集

提供：
1. TrackingMiddleware - 统一 tracking_id 管理
2. MetricsMiddleware - HTTP 请求指标收集
"""

import logging
import time
from typing import Callable

from fastapi import Request, Response
from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware

from .metrics import get_metrics

logger = logging.getLogger(__name__)


class TrackingMiddleware(BaseHTTPMiddleware):
    """
    统一追踪中间件

    功能：
    - 提取 OpenTelemetry trace_id 作为 tracking_id
    - 存储到 request.state 供业务代码使用
    - 在响应头中返回 X-Tracking-ID
    - 添加 span 属性便于查询
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 获取当前 span
        span = trace.get_current_span()

        if span.is_recording():
            # 直接使用 OpenTelemetry 的完整 trace_id 作为 tracking_id
            span_context = span.get_span_context()
            tracking_id = format(span_context.trace_id, "032x")

            # 存储到请求状态，供业务代码使用
            request.state.tracking_id = tracking_id

            # 添加到 span 属性，便于业务查询
            span.set_attribute("tracking.id", tracking_id)
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", str(request.url))

            # 添加用户信息（如果可用）
            if hasattr(request.state, "user_id"):
                span.set_attribute("user.id", request.state.user_id)
        else:
            # 如果没有有效的 span，使用备用标识
            tracking_id = "no-trace"
            request.state.tracking_id = tracking_id

        # 处理请求
        response = await call_next(request)

        # 在响应头中返回完整的 tracking_id 给客户端
        if hasattr(request.state, "tracking_id"):
            response.headers["X-Tracking-ID"] = request.state.tracking_id

        # 添加响应属性到 span
        if span.is_recording():
            span.set_attribute("http.status_code", response.status_code)
            span.set_attribute("http.response.size", response.headers.get("content-length", 0))

        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    HTTP 请求指标收集中间件

    收集：
    - 请求计数
    - 请求持续时间
    - 活跃请求数
    - 错误计数
    """

    def __init__(self, app, service_name: str):
        super().__init__(app)
        self.service_name = service_name
        self.metrics = get_metrics(service_name)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        tracking_id = getattr(request.state, "tracking_id", "unknown")
        endpoint = self._normalize_endpoint(request.url.path)

        # 增加活跃请求
        self.metrics.active_requests.add(
            1, {"service_name": self.service_name, "endpoint": endpoint}
        )

        try:
            response = await call_next(request)

            # 记录成功请求指标
            duration = time.time() - start_time
            status_code = str(response.status_code)

            labels = {
                "service_name": self.service_name,
                "endpoint": endpoint,
                "method": request.method,
                "status_code": status_code,
                "api_version": self._extract_api_version(request.url.path),
            }

            # 请求计数
            self.metrics.request_count.add(1, labels)

            # 请求持续时间
            self.metrics.request_duration.record(
                duration,
                {"service_name": self.service_name, "endpoint": endpoint, "method": request.method},
            )

            # 记录业务指标
            self._record_business_metrics(request, response, tracking_id)

            # 记录请求日志
            logger.info(
                f"{request.method} {request.url.path} - {status_code}",
                extra={
                    "tracking_id": tracking_id,
                    "request_method": request.method,
                    "request_path": request.url.path,
                    "request_duration": duration,
                    "response_status": response.status_code,
                    "response_size": response.headers.get("content-length", 0),
                    "user_id": getattr(request.state, "user_id", None),
                    "session_id": getattr(request.state, "session_id", None),
                },
            )

            return response

        except Exception as e:
            # 记录错误指标
            self.metrics.request_errors.add(
                1,
                {
                    "service_name": self.service_name,
                    "endpoint": endpoint,
                    "method": request.method,
                    "error_type": type(e).__name__,
                    "status_code": "500",
                },
            )

            # 记录错误日志
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "tracking_id": tracking_id,
                    "request_method": request.method,
                    "request_path": request.url.path,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )

            raise

        finally:
            # 减少活跃请求
            self.metrics.active_requests.add(
                -1, {"service_name": self.service_name, "endpoint": endpoint}
            )

    def _normalize_endpoint(self, path: str) -> str:
        """标准化端点路径，将参数替换为占位符"""
        # 简单的路径标准化，可以根据需要扩展
        import re

        # 替换 UUID 格式的参数
        path = re.sub(
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "/{id}", path
        )

        # 替换数字 ID
        path = re.sub(r"/\d+", "/{id}", path)

        return path

    def _extract_api_version(self, path: str) -> str:
        """从路径中提取 API 版本"""
        if "/v1/" in path:
            return "v1"
        elif "/v2/" in path:
            return "v2"
        return "unknown"

    def _record_business_metrics(
        self, request: Request, response: Response, tracking_id: str
    ) -> None:
        """记录业务相关指标"""
        try:
            # API 使用情况
            if hasattr(request.state, "api_key_id"):
                self.metrics.api_key_usage.add(
                    1,
                    {
                        "api_key_id": request.state.api_key_id,
                        "client_name": getattr(request.state, "client_name", "unknown"),
                        "service_name": self.service_name,
                        "endpoint": self._normalize_endpoint(request.url.path),
                        "success": str(response.status_code < 400),
                    },
                )

            # 端点使用统计
            self.metrics.endpoint_usage.add(
                1,
                {
                    "service_name": self.service_name,
                    "endpoint": self._normalize_endpoint(request.url.path),
                    "api_version": self._extract_api_version(request.url.path),
                    "user_segment": getattr(request.state, "user_segment", "unknown"),
                },
            )

            # 用户活动
            if hasattr(request.state, "user_id"):
                self.metrics.user_activity.add(
                    1,
                    {
                        "user_id": request.state.user_id,
                        "activity_type": "api_request",
                        "service_name": self.service_name,
                        "session_id": getattr(request.state, "session_id", "unknown"),
                    },
                )

        except Exception as e:
            logger.warning(f"Failed to record business metrics: {e}")
