"""
统一监控 SDK - OpenTelemetry 完整配置

提供一站式的遥测配置，包括：
- OpenTelemetry 追踪配置
- 自动装配 FastAPI 和 HTTP 客户端
- 指标导出配置
- 日志关联配置
"""

import os
from typing import Optional
import logging  # Keep for constants like logging.INFO
from fastapi import FastAPI

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.resources import Resource

# 自动装配
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
try:
    from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

from .formatter import CloudWatchTracingFormatter


def setup_telemetry(
    app: FastAPI,
    service_name: str,
    service_version: str = "1.0.0",
    otlp_endpoint: str = "http://localhost:4317",
    prometheus_port: int = 8000
) -> None:
    """
    设置完整的 OpenTelemetry 遥测栈
    
    Args:
        app: FastAPI 应用实例
        service_name: 服务名称 (api-gateway, workflow-agent, workflow-engine)
        service_version: 服务版本
        otlp_endpoint: OpenTelemetry Collector 端点
        prometheus_port: Prometheus 指标端口
    """
    
    # 1. 配置资源属性
    resource = Resource.create({
        "service.name": service_name,
        "service.version": service_version,
        "deployment.environment": os.getenv("ENVIRONMENT", "dev"),
        "project": "starmates-ai-team"
    })
    
    # 2. 配置追踪
    _setup_tracing(resource, otlp_endpoint)
    
    # 3. 配置指标
    _setup_metrics(resource, otlp_endpoint, prometheus_port)
    
    # 4. 配置日志
    _setup_logging(service_name)
    
    # 5. 自动装配
    _setup_auto_instrumentation(app)
    
    from shared.logging_config import get_logger
    logger = get_logger(__name__)
    logger.info(f"OpenTelemetry telemetry initialized for {service_name}")


def _setup_tracing(resource: Resource, otlp_endpoint: str) -> None:
    """配置 OpenTelemetry 追踪"""
    
    # 创建 TracerProvider
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)
    
    # 配置 OTLP 导出器
    otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)


def _setup_metrics(resource: Resource, otlp_endpoint: str, prometheus_port: int) -> None:
    """配置 OpenTelemetry 指标"""
    
    # 创建指标读取器
    readers = []
    
    # Prometheus 导出器 (本地)
    prometheus_reader = PrometheusMetricReader()
    readers.append(prometheus_reader)
    
    # OTLP 导出器 (Grafana Cloud)
    otlp_metric_exporter = OTLPMetricExporter(endpoint=otlp_endpoint, insecure=True)
    otlp_reader = PeriodicExportingMetricReader(
        exporter=otlp_metric_exporter,
        export_interval_millis=10000  # 10秒导出一次
    )
    readers.append(otlp_reader)
    
    # 创建 MeterProvider
    meter_provider = MeterProvider(resource=resource, metric_readers=readers)
    metrics.set_meter_provider(meter_provider)


def _setup_logging(service_name: str) -> None:
    """配置结构化日志 - 如果尚未配置"""
    
    # 如果已经配置了日志（比如在 main.py 中使用了 shared.logging），不要覆盖
    # Get root logger from shared config
    import logging
    logger = logging.getLogger()
    if logger.handlers:
        # 日志已经配置，跳过
        return
    
    # 如果没有配置，使用 shared.logging_config 模块进行配置
    try:
        from ..logging_config import setup_logging as shared_setup_logging
        shared_setup_logging(
            service_name=service_name,
            log_level=os.getenv("LOG_LEVEL", "INFO")
        )
    except ImportError:
        # 如果无法导入 shared.logging，使用基本配置
        log_format = os.getenv("LOG_FORMAT", "simple")
        logger.setLevel(logging.INFO)
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        if log_format == "json":
            formatter = CloudWatchTracingFormatter(service_name=service_name)
        else:
            formatter = logging.Formatter(
                fmt="%(levelname)s:     %(asctime)s - %(name)s - [%(filename)s:%(lineno)d] - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # 配置第三方库日志级别
        # These are handled by shared logging config's _configure_third_party_loggers()
        # But we can still set them here for extra safety
        import logging
        logging.getLogger("uvicorn").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("opentelemetry").setLevel(logging.WARNING)


def _setup_auto_instrumentation(app: FastAPI) -> None:
    """配置自动装配"""
    
    # FastAPI 自动装配
    FastAPIInstrumentor.instrument_app(app)
    
    # HTTP 客户端自动装配
    RequestsInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()
    
    # 数据库自动装配 (如果使用 PostgreSQL)
    if HAS_PSYCOPG2:
        try:
            Psycopg2Instrumentor().instrument()
        except Exception:
            # 如果装配失败，跳过
            pass


def get_tracer(name: str) -> trace.Tracer:
    """获取命名的 Tracer 实例"""
    return trace.get_tracer(name)


def get_meter(name: str) -> metrics.Meter:
    """获取命名的 Meter 实例"""
    return metrics.get_meter(name)