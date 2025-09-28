"""
Enhanced Execution Models based on the new workflow specification.

This module provides comprehensive execution tracking with:
- Detailed status enumeration
- Real-time event handling
- Node-level execution tracking
- Resource consumption monitoring
- Error handling and retry logic
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

# ============================================================================
# EXECUTION STATUS ENUMS - Enhanced from original
# ============================================================================


class ExecutionStatus(str, Enum):
    """工作流执行状态 - Enhanced version"""

    NEW = "NEW"  # 新建状态
    PENDING = "PENDING"  # 等待开始
    RUNNING = "RUNNING"  # 正在执行
    PAUSED = "PAUSED"  # 暂停 (Human-in-the-loop)
    SUCCESS = "SUCCESS"  # 成功完成
    ERROR = "ERROR"  # 执行失败
    CANCELED = "CANCELED"  # 用户取消
    WAITING = "WAITING"  # 等待中
    TIMEOUT = "TIMEOUT"  # 执行超时
    WAITING_FOR_HUMAN = "WAITING_FOR_HUMAN"  # 等待人工响应

    # Additional values for workflow_engine_v2 compatibility
    SKIPPED = "SKIPPED"  # 被跳过
    COMPLETED = "COMPLETED"  # 完成状态
    CANCELLED = "CANCELLED"  # 取消状态 (alternative spelling)


class NodeExecutionStatus(str, Enum):
    """节点执行状态"""

    PENDING = "pending"  # 等待执行
    RUNNING = "running"  # 正在执行
    WAITING_INPUT = "waiting_input"  # 等待用户输入 (Human-in-the-loop)
    COMPLETED = "completed"  # 执行完成
    FAILED = "failed"  # 执行失败
    SKIPPED = "skipped"  # 被跳过
    RETRYING = "retrying"  # 正在重试


class ExecutionEventType(str, Enum):
    """执行事件类型 - 用于WebSocket实时推送"""

    EXECUTION_STARTED = "execution_started"
    NODE_STARTED = "node_started"
    NODE_COMPLETED = "node_completed"
    NODE_FAILED = "node_failed"
    NODE_OUTPUT_UPDATE = "node_output_update"  # 节点输出更新（流式输出）
    EXECUTION_PAUSED = "execution_paused"
    EXECUTION_RESUMED = "execution_resumed"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    USER_INPUT_REQUIRED = "user_input_required"


class LogLevel(str, Enum):
    """日志级别"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


# ============================================================================
# BASIC DATA STRUCTURES
# ============================================================================


class TriggerInfo(BaseModel):
    """触发信息"""

    trigger_type: str = Field(..., description="触发类型")
    trigger_data: Dict[str, Any] = Field(default_factory=dict, description="触发数据")
    user_id: Optional[str] = Field(default=None, description="触发用户")
    external_request_id: Optional[str] = Field(default=None, description="外部请求ID")
    timestamp: int = Field(..., description="触发时间戳")


class TokenUsage(BaseModel):
    """Token使用情况"""

    input_tokens: int = Field(default=0, description="输入token数")
    output_tokens: int = Field(default=0, description="输出token数")
    total_tokens: int = Field(default=0, description="总token数")


class LogEntry(BaseModel):
    """日志条目"""

    timestamp: int = Field(..., description="日志时间戳")
    level: LogLevel = Field(..., description="日志级别")
    message: str = Field(..., description="日志消息")
    node_id: Optional[str] = Field(default=None, description="关联的节点ID")
    context: Optional[Dict[str, Any]] = Field(default=None, description="上下文信息")


class ExecutionError(BaseModel):
    """执行错误信息"""

    error_code: str = Field(..., description="错误代码")
    error_message: str = Field(..., description="错误消息")
    error_node_id: Optional[str] = Field(default=None, description="出错的节点ID")
    stack_trace: Optional[str] = Field(default=None, description="堆栈跟踪")
    timestamp: int = Field(..., description="错误发生时间")
    is_retryable: bool = Field(default=False, description="是否可重试")


class NodeError(BaseModel):
    """节点错误信息"""

    error_code: str = Field(..., description="错误代码")
    error_message: str = Field(..., description="错误消息")
    error_details: Optional[Dict[str, Any]] = Field(default=None, description="错误详情")
    is_retryable: bool = Field(..., description="是否可重试")
    timestamp: int = Field(..., description="错误发生时间")


# ============================================================================
# NODE EXECUTION DETAILS
# ============================================================================


class NodeExecutionDetails(BaseModel):
    """节点执行详情 - 根据节点类型的不同而不同"""

    # AI_Agent 特有
    ai_model: Optional[str] = Field(default=None, description="使用的AI模型")
    prompt_tokens: Optional[int] = Field(default=None, description="Prompt token数")
    completion_tokens: Optional[int] = Field(default=None, description="完成token数")
    model_response: Optional[str] = Field(default=None, description="AI模型响应")

    # External_Action 特有
    api_endpoint: Optional[str] = Field(default=None, description="API端点")
    http_method: Optional[str] = Field(default=None, description="HTTP方法")
    request_headers: Optional[Dict[str, str]] = Field(default=None, description="请求头")
    response_status: Optional[int] = Field(default=None, description="响应状态码")
    response_headers: Optional[Dict[str, str]] = Field(default=None, description="响应头")

    # Tool 特有
    tool_name: Optional[str] = Field(default=None, description="工具名称")
    tool_parameters: Optional[Dict[str, Any]] = Field(default=None, description="工具参数")
    tool_result: Optional[Any] = Field(default=None, description="工具执行结果")

    # Human_in_the_loop 特有
    user_prompt: Optional[str] = Field(default=None, description="给用户的提示")
    user_response: Optional[Any] = Field(default=None, description="用户的响应")
    waiting_since: Optional[int] = Field(default=None, description="开始等待的时间")

    # Flow 特有 (条件判断等)
    condition_result: Optional[bool] = Field(default=None, description="条件判断结果")
    branch_taken: Optional[str] = Field(default=None, description="选择的分支")

    # 通用
    logs: List[LogEntry] = Field(default_factory=list, description="执行日志")
    metrics: Optional[Dict[str, Any]] = Field(default=None, description="自定义指标")


class NodeExecution(BaseModel):
    """单个节点执行详情"""

    node_id: str = Field(..., description="节点ID")
    node_name: str = Field(..., description="节点名称")
    node_type: str = Field(..., description="节点类型")
    node_subtype: str = Field(..., description="节点子类型")

    # 执行状态
    status: NodeExecutionStatus = Field(..., description="节点执行状态")
    start_time: Optional[int] = Field(default=None, description="开始执行时间")
    end_time: Optional[int] = Field(default=None, description="结束时间")
    duration_ms: Optional[int] = Field(default=None, description="执行耗时")

    # 输入输出
    input_data: Dict[str, Any] = Field(default_factory=dict, description="输入数据，Key: input_port_id")
    output_data: Dict[str, Any] = Field(
        default_factory=dict, description="输出数据，Key: output_port_id"
    )

    # 执行详情
    execution_details: NodeExecutionDetails = Field(
        default_factory=NodeExecutionDetails, description="节点特定的执行详情"
    )

    # 错误信息
    error: Optional[NodeError] = Field(default=None, description="节点执行错误")

    # 重试信息
    retry_count: int = Field(default=0, description="重试次数")
    max_retries: int = Field(default=3, description="最大重试次数")

    # 资源消耗
    credits_consumed: int = Field(default=0, description="该节点消耗的credits")

    # 附加节点执行情况 (AI_AGENT 专用)
    attached_executions: Optional[Dict[str, "NodeExecution"]] = Field(
        default=None, description="附加的Tool/Memory节点执行情况"
    )


# ============================================================================
# MAIN EXECUTION MODEL - Enhanced
# ============================================================================


class Execution(BaseModel):
    """Enhanced execution model with detailed tracking"""

    # Basic information (maintaining compatibility with existing model)
    id: str = Field(..., description="对应数据库的 id (UUID)")
    execution_id: str = Field(..., description="对应数据库的 execution_id")
    workflow_id: str = Field(..., description="对应数据库的 workflow_id (UUID)")
    workflow_version: str = Field(default="1.0", description="工作流版本号")

    # Status and timing
    status: ExecutionStatus = Field(..., description="执行状态")
    start_time: Optional[int] = Field(default=None, description="开始执行时间戳")
    end_time: Optional[int] = Field(default=None, description="结束时间戳")
    duration_ms: Optional[int] = Field(default=None, description="总耗时")

    # Trigger information
    mode: Optional[str] = Field(default=None, description="执行模式")
    triggered_by: Optional[str] = Field(default=None, description="触发用户ID")
    trigger_info: Optional[TriggerInfo] = Field(default=None, description="详细触发信息")

    # Data and context
    run_data: Optional[Dict[str, Any]] = Field(default=None, description="运行数据")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元数据")
    execution_metadata: Optional[Dict[str, Any]] = Field(default=None, description="执行元数据")

    # Error handling
    error_message: Optional[str] = Field(default=None, description="错误消息")
    error_details: Optional[Dict[str, Any]] = Field(default=None, description="错误详情")
    error: Optional[ExecutionError] = Field(default=None, description="结构化错误信息")

    # Enhanced execution tracking
    node_executions: Dict[str, NodeExecution] = Field(
        default_factory=dict, description="节点执行详情，Key: node_id"
    )
    execution_sequence: List[str] = Field(default_factory=list, description="按执行顺序排列的node_id数组")
    current_node_id: Optional[str] = Field(default=None, description="当前正在执行的节点")
    next_nodes: List[str] = Field(default_factory=list, description="下一步将要执行的节点列表")

    # Resource consumption
    credits_consumed: int = Field(default=0, description="消耗的credits")
    tokens_used: Optional[TokenUsage] = Field(default=None, description="Token使用情况")

    # Timestamps (maintaining compatibility)
    created_at: Optional[str] = Field(default=None, description="创建时间")
    updated_at: Optional[str] = Field(default=None, description="更新时间")


# ============================================================================
# REAL-TIME UPDATE MODELS
# ============================================================================


class ExecutionUpdateData(BaseModel):
    """执行更新数据"""

    node_id: Optional[str] = Field(default=None, description="节点ID")
    node_execution: Optional[NodeExecution] = Field(default=None, description="节点执行信息")
    partial_output: Optional[Dict[str, Any]] = Field(default=None, description="流式输出的部分数据")
    execution_status: Optional[ExecutionStatus] = Field(default=None, description="执行状态")
    error: Optional[Union[ExecutionError, NodeError]] = Field(default=None, description="错误信息")
    user_input_request: Optional[Dict[str, Any]] = Field(default=None, description="用户输入请求")


class ExecutionUpdateEvent(BaseModel):
    """实时更新事件 - 用于WebSocket推送"""

    event_type: ExecutionEventType = Field(..., description="事件类型")
    execution_id: str = Field(..., description="执行ID")
    timestamp: int = Field(..., description="事件时间戳")
    data: ExecutionUpdateData = Field(..., description="更新数据")


# ============================================================================
# SUMMARY MODELS FOR LISTING
# ============================================================================


class ExecutionSummary(BaseModel):
    """执行摘要 - 用于列表显示"""

    execution_id: str = Field(..., description="执行ID")
    workflow_id: str = Field(..., description="工作流ID")
    workflow_name: str = Field(..., description="工作流名称")
    status: ExecutionStatus = Field(..., description="执行状态")
    start_time: Optional[int] = Field(default=None, description="开始时间")
    end_time: Optional[int] = Field(default=None, description="结束时间")
    duration_ms: Optional[int] = Field(default=None, description="执行耗时")
    trigger_type: str = Field(..., description="触发类型")
    triggered_by: Optional[str] = Field(default=None, description="触发用户")
    credits_consumed: int = Field(default=0, description="消耗的credits")
    error_summary: Optional[str] = Field(default=None, description="错误摘要")


# ============================================================================
# API REQUEST/RESPONSE MODELS
# ============================================================================


class GetExecutionResponse(BaseModel):
    """获取执行详情响应"""

    execution: Execution = Field(..., description="执行详情")
    workflow_definition: Optional[Dict[str, Any]] = Field(default=None, description="工作流定义")


class GetExecutionsResponse(BaseModel):
    """获取执行列表响应"""

    executions: List[ExecutionSummary] = Field(..., description="执行列表")
    total_count: int = Field(..., description="总数量")
    page: int = Field(default=1, description="当前页")
    page_size: int = Field(default=20, description="每页大小")


class ExecutionActionRequest(BaseModel):
    """用户操作请求"""

    action: str = Field(..., description="操作类型: pause, resume, cancel, retry_node")
    node_id: Optional[str] = Field(default=None, description="节点ID，retry_node时需要")


class UserInputRequest(BaseModel):
    """用户输入请求"""

    execution_id: str = Field(..., description="执行ID")
    node_id: str = Field(..., description="节点ID")
    input_data: Any = Field(..., description="输入数据")


class ExecutionActionResponse(BaseModel):
    """执行操作响应"""

    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="响应消息")
    execution_status: Optional[ExecutionStatus] = Field(default=None, description="执行状态")


class SubscriptionResponse(BaseModel):
    """WebSocket订阅响应"""

    subscription_id: str = Field(..., description="订阅ID")
    execution_id: str = Field(..., description="执行ID")
    status: str = Field(..., description="订阅状态")
    message: Optional[str] = Field(default=None, description="消息")


# ============================================================================
# NODE EXECUTION RESULT - From workflow_engine_v2
# ============================================================================


class NodeExecutionResult(BaseModel):
    """Result of node execution - migrated from workflow_engine_v2.core.models."""

    status: ExecutionStatus = Field(..., description="Execution status")
    output_data: Dict[str, Any] = Field(
        default_factory=dict, description="Output data from node execution"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if execution failed"
    )
    error_details: Optional[Dict[str, Any]] = Field(
        default=None, description="Detailed error information"
    )
    execution_time_ms: Optional[float] = Field(
        default=None, description="Execution time in milliseconds"
    )
    logs: Optional[List[str]] = Field(default=None, description="Execution logs")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "status": self.status.value,
            "output_data": self.output_data,
            "error_message": self.error_message,
            "error_details": self.error_details,
            "execution_time_ms": self.execution_time_ms,
            "logs": self.logs or [],
            "metadata": self.metadata or {},
        }


# ============================================================================
# LEGACY COMPATIBILITY
# ============================================================================

# Legacy compatibility - alias the original ExecutionLog model
ExecutionLog = LogEntry

# Fix forward reference for NodeExecution.attached_executions
NodeExecution.model_rebuild()
