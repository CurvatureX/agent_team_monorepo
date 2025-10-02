"""
New Workflow Models based on the tech design specification.

This module implements the complete workflow specification including:
- Port definitions with proper data types and validation
- Node specifications with configurations and parameters
- Connection definitions with conversion functions
- Workflow metadata and statistics
- Execution models with detailed status tracking
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator

from .common import NodeTemplate

# Import execution-related enums from execution_new.py (single source of truth)
from .execution_new import (
    ExecutionEventType,
    ExecutionStatus,
    LogLevel,
    NodeExecutionStatus,
    TriggerInfo,
)

# ============================================================================
# ENUMS - Status and Type Definitions
# ============================================================================


class WorkflowDeploymentStatus(str, Enum):
    """工作流部署状态"""

    PENDING = "pending"  # 等待部署
    DEPLOYED = "deployed"  # 已部署
    FAILED = "failed"  # 部署失败
    UNDEPLOYED = "undeployed"  # 已取消部署


# ============================================================================
# CONNECTION MODELS
# ============================================================================


class Connection(BaseModel):
    """连接定义 - 符合 new_workflow_spec.md 规范"""

    id: str = Field(..., description="连接的唯一标识符")
    from_node: str = Field(..., description="源节点的ID")
    to_node: str = Field(..., description="目标节点的ID")
    output_key: str = Field(
        default="result", description="从源节点的哪个输出获取数据（如 'result', 'true', 'false'）"
    )
    conversion_function: Optional[str] = Field(default=None, description="数据转换函数")


# ============================================================================
# NODE MODELS
# ============================================================================


class Node(BaseModel):
    """节点定义"""

    id: str = Field(..., description="节点的唯一标识符")
    name: str = Field(..., description="节点名称，不可包含空格")
    description: str = Field(..., description="节点的一句话简介")
    type: str = Field(..., description="节点大类")  # Using string to avoid import dependency
    subtype: str = Field(..., description="节点细分种类")
    configurations: Dict[str, Any] = Field(default_factory=dict, description="节点配置参数")
    input_params: Dict[str, Any] = Field(default_factory=dict, description="运行时输入参数")
    output_params: Dict[str, Any] = Field(default_factory=dict, description="运行时输出参数")
    position: Optional[Dict[str, float]] = Field(default=None, description="节点在画布上的位置")

    # AI_AGENT specific field - attached nodes for TOOL and MEMORY
    attached_nodes: Optional[List[str]] = Field(
        default=None, description="附加节点ID列表，只适用于AI_AGENT节点调用TOOL和MEMORY节点"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if " " in v:
            raise ValueError("节点名称不可包含空格")
        return v


# ============================================================================
# WORKFLOW METADATA AND STATISTICS
# ============================================================================


class WorkflowStatistics(BaseModel):
    """工作流统计信息"""

    total_runs: int = Field(default=0, description="总运行次数")
    average_duration_ms: int = Field(default=0, description="平均耗时（毫秒）")
    total_credits: int = Field(default=0, description="总消耗的credits")
    last_success_time: Optional[int] = Field(default=None, description="最后成功时间戳")


class WorkflowMetadata(BaseModel):
    """工作流元数据"""

    id: str = Field(..., description="UUID唯一标识符")
    name: str = Field(..., description="工作流名称")
    icon_url: Optional[str] = Field(default=None, description="工作流图标链接")
    description: Optional[str] = Field(default=None, description="工作流描述")
    deployment_status: WorkflowDeploymentStatus = Field(
        default=WorkflowDeploymentStatus.PENDING, description="部署状态"
    )
    last_execution_status: Optional[ExecutionStatus] = Field(default=None, description="上次运行状态")
    last_execution_time: Optional[int] = Field(default=None, description="上次运行时间戳（毫秒）")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    created_time: int = Field(..., description="创建时间戳（毫秒）")
    parent_workflow: Optional[str] = Field(default=None, description="模板原始工作流ID")
    statistics: WorkflowStatistics = Field(default_factory=WorkflowStatistics, description="统计信息")
    version: str = Field(default="1.0", description="版本号")
    created_by: str = Field(..., description="创建用户ID")
    updated_by: Optional[str] = Field(default=None, description="最后更新用户ID")


# ============================================================================
# WORKFLOW DEFINITION
# ============================================================================


class CreateWorkflowRequest(BaseModel):
    """创建工作流请求模型 - Updated to match new node specs format"""

    # New format - matches comprehensive_personal_assistant_workflow.json
    nodes: List[Dict[str, Any]] = Field(..., description="节点列表")
    metadata: Dict[str, Any] = Field(..., description="工作流元数据，包含name, description等")
    triggers: List[str] = Field(..., description="触发器节点ID列表")
    connections: List[Dict[str, Any]] = Field(default_factory=list, description="连接列表")


class UpdateWorkflowRequest(BaseModel):
    """更新工作流请求模型"""

    user_id: Optional[str] = Field(default=None, description="用户ID")
    name: Optional[str] = Field(default=None, description="工作流名称")
    description: Optional[str] = Field(default=None, description="工作流描述")
    nodes: Optional[List[Dict[str, Any]]] = Field(default=None, description="节点列表")
    connections: Optional[List[Dict[str, Any]]] = Field(default=None, description="连接列表")
    triggers: Optional[List[str]] = Field(default=None, description="触发器节点ID列表")
    tags: Optional[List[str]] = Field(default=None, description="标签列表")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="额外元数据")


class NodeTemplateListResponse(BaseModel):
    """Response model for a list of node templates"""

    node_templates: List[NodeTemplate] = Field(default_factory=list)


class WorkflowExecutionRequest(BaseModel):
    """工作流执行请求模型"""

    inputs: Dict[str, Any] = Field(default_factory=dict, description="执行时的输入参数")
    settings: Optional[Dict[str, Any]] = Field(default=None, description="执行时的特殊设置")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="执行元数据")
    start_from_node: Optional[str] = Field(default=None, description="从指定节点开始执行")
    skip_trigger_validation: bool = Field(default=False, description="是否跳过触发器验证")


class WorkflowExecutionResponse(BaseModel):
    """工作流执行响应模型"""

    execution_id: str = Field(description="执行ID")
    workflow_id: str = Field(description="工作流ID")
    status: str = Field(description="执行状态")
    message: Optional[str] = Field(default=None, description="响应消息")
    started_at: Optional[str] = Field(default=None, description="开始执行时间")


class WorkflowResponse(BaseModel):
    """工作流响应模型"""

    workflow: "Workflow" = Field(
        description="工作流信息"
    )  # Forward reference since Workflow is defined later
    message: Optional[str] = Field(default=None, description="响应消息")


class Workflow(BaseModel):
    """完整工作流定义"""

    metadata: WorkflowMetadata = Field(..., description="工作流元数据")
    nodes: List[Node] = Field(..., description="节点列表")
    connections: List[Connection] = Field(default_factory=list, description="连接列表")
    triggers: List[str] = Field(default_factory=list, description="触发器节点ID列表")

    @field_validator("nodes")
    @classmethod
    def validate_nodes(cls, v):
        if not v:
            raise ValueError("工作流必须包含至少一个节点")
        node_ids = [node.id for node in v]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("节点ID必须唯一")
        return v

    @field_validator("connections")
    @classmethod
    def validate_connections(cls, v, info):
        """验证连接的有效性"""
        if "nodes" in info.data:
            node_ids = {node.id for node in info.data["nodes"]}
            for conn in v:
                if conn.from_node not in node_ids:
                    raise ValueError(f"连接中的源节点 '{conn.from_node}' 不存在")
                if conn.to_node not in node_ids:
                    raise ValueError(f"连接中的目标节点 '{conn.to_node}' 不存在")
        return v


# Legacy alias for backward compatibility
WorkflowData = Workflow


# ============================================================================
# EXECUTION MODELS
# ============================================================================


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
    input_data: Dict[str, Any] = Field(default_factory=dict, description="输入数据")
    output_data: Dict[str, Any] = Field(default_factory=dict, description="输出数据")

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


class WorkflowExecution(BaseModel):
    """工作流执行整体状态"""

    # 基础信息
    execution_id: str = Field(..., description="执行实例的唯一标识")
    workflow_id: str = Field(..., description="对应的Workflow ID")
    workflow_version: str = Field(default="1.0", description="Workflow版本号")

    # 执行状态
    status: ExecutionStatus = Field(..., description="整体执行状态")
    start_time: Optional[int] = Field(default=None, description="开始执行时间")
    end_time: Optional[int] = Field(default=None, description="结束时间")
    duration_ms: Optional[int] = Field(default=None, description="总耗时")

    # 触发信息
    trigger_info: TriggerInfo = Field(..., description="触发相关信息")

    # 节点执行详情
    node_executions: Dict[str, NodeExecution] = Field(
        default_factory=dict, description="节点执行详情，Key: node_id"
    )
    execution_sequence: List[str] = Field(default_factory=list, description="按执行顺序排列的node_id数组")

    # 当前状态
    current_node_id: Optional[str] = Field(default=None, description="当前正在执行的节点")
    next_nodes: List[str] = Field(default_factory=list, description="下一步将要执行的节点列表")

    # 错误信息
    error: Optional[ExecutionError] = Field(default=None, description="执行错误信息")

    # 资源消耗
    credits_consumed: int = Field(default=0, description="消耗的credits")
    tokens_used: Optional[TokenUsage] = Field(default=None, description="Token使用情况")

    # 元数据
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="执行元数据")
    created_at: Optional[str] = Field(default=None, description="创建时间")
    updated_at: Optional[str] = Field(default=None, description="更新时间")


# ============================================================================
# WEBSOCKET EVENTS
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
# API REQUEST/RESPONSE MODELS
# ============================================================================


class WorkflowExecutionSummary(BaseModel):
    """工作流执行摘要 - 用于列表显示"""

    execution_id: str = Field(..., description="执行ID")
    workflow_id: str = Field(..., description="工作流ID")
    workflow_name: str = Field(..., description="工作流名称")
    status: ExecutionStatus = Field(..., description="执行状态")
    start_time: Optional[int] = Field(default=None, description="开始时间")
    end_time: Optional[int] = Field(default=None, description="结束时间")
    duration_ms: Optional[int] = Field(default=None, description="执行耗时")
    trigger_type: str = Field(..., description="触发类型")
    credits_consumed: int = Field(default=0, description="消耗的credits")
    error_summary: Optional[str] = Field(default=None, description="错误摘要")


class GetExecutionResponse(BaseModel):
    """获取执行详情响应"""

    execution: WorkflowExecution = Field(..., description="执行详情")
    workflow_definition: Optional[Workflow] = Field(default=None, description="工作流定义")


class GetExecutionsResponse(BaseModel):
    """获取执行列表响应"""

    executions: List[WorkflowExecutionSummary] = Field(..., description="执行列表")
    total_count: int = Field(..., description="总数量")
    page: int = Field(default=1, description="当前页")
    page_size: int = Field(default=20, description="每页大小")


class SubscriptionResponse(BaseModel):
    """WebSocket订阅响应"""

    subscription_id: str = Field(..., description="订阅ID")
    execution_id: str = Field(..., description="执行ID")
    status: str = Field(..., description="订阅状态")
    message: Optional[str] = Field(default=None, description="消息")


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


# Fix forward reference for NodeExecution.attached_executions
NodeExecution.model_rebuild()
