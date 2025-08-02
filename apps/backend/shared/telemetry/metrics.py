"""
核心指标定义

定义所有服务共享的 OpenTelemetry 指标：
- HTTP 基础指标
- 业务指标
- AI 专项指标
"""

from dataclasses import dataclass
from typing import Dict, Any
from opentelemetry import metrics


@dataclass
class ServiceMetrics:
    """服务指标集合"""
    
    # HTTP 基础指标
    request_count: metrics.Counter
    request_duration: metrics.Histogram
    request_errors: metrics.Counter
    active_requests: metrics.UpDownCounter
    
    # 业务指标
    api_key_usage: metrics.Counter
    endpoint_usage: metrics.Counter
    user_activity: metrics.Counter
    
    # AI 专项指标
    ai_requests: metrics.Counter
    ai_tokens: metrics.Counter
    ai_cost: metrics.Counter
    
    # 工作流指标
    workflow_success_rate: metrics.Histogram


def get_metrics(service_name: str) -> ServiceMetrics:
    """
    获取服务的指标实例
    
    Args:
        service_name: 服务名称
        
    Returns:
        ServiceMetrics: 指标集合
    """
    
    meter = metrics.get_meter(f"{service_name}-metrics")
    
    # HTTP 基础指标
    request_count = meter.create_counter(
        name="request_count",
        description="Total number of HTTP requests",
        unit="1"
    )
    
    request_duration = meter.create_histogram(
        name="request_duration_seconds",
        description="HTTP request duration in seconds",
        unit="s"
    )
    
    request_errors = meter.create_counter(
        name="request_errors_total",
        description="Total number of HTTP request errors",
        unit="1"
    )
    
    active_requests = meter.create_up_down_counter(
        name="active_requests",
        description="Number of active HTTP requests",
        unit="1"
    )
    
    # 业务指标
    api_key_usage = meter.create_counter(
        name="api_key_usage_total",
        description="API key usage by client",
        unit="1"
    )
    
    endpoint_usage = meter.create_counter(
        name="endpoint_usage_total",
        description="Endpoint usage frequency",
        unit="1"
    )
    
    user_activity = meter.create_counter(
        name="user_activity_total",
        description="User activity events",
        unit="1"
    )
    
    # AI 专项指标
    ai_requests = meter.create_counter(
        name="ai_requests_total",
        description="Total AI model requests",
        unit="1"
    )
    
    ai_tokens = meter.create_counter(
        name="ai_tokens_total",
        description="Total AI tokens consumed",
        unit="1"
    )
    
    ai_cost = meter.create_counter(
        name="ai_cost_total",
        description="Total AI cost in USD",
        unit="1"
    )
    
    # 工作流指标
    workflow_success_rate = meter.create_histogram(
        name="workflow_success_rate",
        description="Workflow execution success rate",
        unit="1"
    )
    
    return ServiceMetrics(
        request_count=request_count,
        request_duration=request_duration,
        request_errors=request_errors,
        active_requests=active_requests,
        api_key_usage=api_key_usage,
        endpoint_usage=endpoint_usage,
        user_activity=user_activity,
        ai_requests=ai_requests,
        ai_tokens=ai_tokens,
        ai_cost=ai_cost,
        workflow_success_rate=workflow_success_rate
    )


def record_ai_usage(
    service_name: str,
    model: str,
    provider: str,
    input_tokens: int,
    output_tokens: int,
    cost: float,
    tracking_id: str
) -> None:
    """
    记录 AI 使用指标
    
    Args:
        service_name: 服务名称
        model: AI 模型名称
        provider: AI 提供商
        input_tokens: 输入 token 数
        output_tokens: 输出 token 数
        cost: 成本
        tracking_id: 追踪 ID
    """
    
    metrics_instance = get_metrics(service_name)
    
    labels = {
        "model": model,
        "provider": provider,
        "environment": "dev",  # 可以从环境变量获取
        "tracking_id": tracking_id
    }
    
    # 记录请求
    metrics_instance.ai_requests.add(1, labels)
    
    # 记录 token 使用
    input_labels = {**labels, "token_type": "input"}
    output_labels = {**labels, "token_type": "output"}
    
    metrics_instance.ai_tokens.add(input_tokens, input_labels)
    metrics_instance.ai_tokens.add(output_tokens, output_labels)
    
    # 记录成本
    metrics_instance.ai_cost.add(cost, labels)


def record_workflow_execution(
    service_name: str,
    workflow_type: str,
    complexity_level: str,
    success: bool,
    execution_time: float,
    tracking_id: str
) -> None:
    """
    记录工作流执行指标
    
    Args:
        service_name: 服务名称
        workflow_type: 工作流类型
        complexity_level: 复杂度级别
        success: 是否成功
        execution_time: 执行时间
        tracking_id: 追踪 ID
    """
    
    metrics_instance = get_metrics(service_name)
    
    labels = {
        "workflow_type": workflow_type,
        "complexity_level": complexity_level,
        "tracking_id": tracking_id
    }
    
    # 记录成功率 (1.0 表示成功，0.0 表示失败)
    success_rate = 1.0 if success else 0.0
    metrics_instance.workflow_success_rate.record(success_rate, labels)


# 标准化标签辅助函数
def get_standard_labels(
    service_name: str,
    endpoint: str = "",
    method: str = "",
    status_code: str = "",
    **kwargs
) -> Dict[str, Any]:
    """
    获取标准化标签
    
    Args:
        service_name: 服务名称
        endpoint: 端点
        method: HTTP 方法
        status_code: 状态码
        **kwargs: 其他标签
        
    Returns:
        Dict[str, Any]: 标准化标签字典
    """
    
    labels = {
        "service_name": service_name,
        "environment": "dev",  # 可以从环境变量获取
        "project": "starmates-ai-team"
    }
    
    if endpoint:
        labels["endpoint"] = endpoint
    if method:
        labels["method"] = method
    if status_code:
        labels["status_code"] = status_code
    
    # 添加额外标签
    labels.update(kwargs)
    
    return labels