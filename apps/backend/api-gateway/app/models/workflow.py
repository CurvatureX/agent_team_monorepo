"""
Workflow Models
工作流相关的数据模型
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator

from .base import BaseModel, EntityModel


class WorkflowStatus(str, Enum):
    """工作流状态枚举"""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class WorkflowType(str, Enum):
    """工作流类型枚举"""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    HYBRID = "hybrid"


class NodeType(str, Enum):
    """节点类型枚举"""

    TRIGGER = "trigger"
    ACTION = "action"
    CONDITION = "condition"
    LOOP = "loop"
    WEBHOOK = "webhook"
    API_CALL = "api_call"
    EMAIL = "email"
    DELAY = "delay"


class WorkflowNode(BaseModel):
    """
    工作流节点模型
    """

    id: str = Field(description="节点唯一标识符")
    type: NodeType = Field(description="节点类型")
    name: str = Field(description="节点名称")
    description: Optional[str] = Field(default=None, description="节点描述")
    config: Dict[str, Any] = Field(default_factory=dict, description="节点配置")
    position: Optional[Dict[str, float]] = Field(default=None, description="节点在画布上的位置 {x, y}")
    connections: List[str] = Field(default_factory=list, description="连接到的下一个节点ID列表")
    enabled: bool = Field(default=True, description="节点是否启用")


class WorkflowEdge(BaseModel):
    """
    工作流连接边模型
    """

    id: str = Field(description="边的唯一标识符")
    source: str = Field(description="源节点ID")
    target: str = Field(description="目标节点ID")
    condition: Optional[str] = Field(default=None, description="边的条件表达式")
    label: Optional[str] = Field(default=None, description="边的标签")


class WorkflowCreate(BaseModel):
    """
    工作流创建请求模型
    """

    name: str = Field(description="工作流名称")
    description: Optional[str] = Field(default=None, description="工作流描述")
    type: WorkflowType = Field(default=WorkflowType.SEQUENTIAL, description="工作流类型")
    nodes: List[WorkflowNode] = Field(default_factory=list, description="工作流节点列表")
    edges: List[WorkflowEdge] = Field(default_factory=list, description="工作流连接边列表")
    connections: Optional[Dict[str, Any]] = Field(default_factory=dict, description="节点连接信息（兼容性字段）")
    variables: Dict[str, Any] = Field(default_factory=dict, description="工作流变量")
    settings: Dict[str, Any] = Field(default_factory=dict, description="工作流设置")
    tags: List[str] = Field(default_factory=list, description="工作流标签")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="工作流元数据")

    @field_validator("nodes")
    @classmethod
    def validate_nodes(cls, v):
        """验证节点列表"""
        if not v:
            return v

        # 检查节点ID是否唯一
        node_ids = [node.id for node in v]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("Node IDs must be unique")

        return v

    @field_validator("edges")
    @classmethod
    def validate_edges(cls, v, info):
        """验证连接边"""
        if not v or not hasattr(info, "data") or "nodes" not in info.data:
            return v

        node_ids = {node.id for node in info.data["nodes"]}

        for edge in v:
            if edge.source not in node_ids:
                raise ValueError(f"Edge source '{edge.source}' not found in nodes")
            if edge.target not in node_ids:
                raise ValueError(f"Edge target '{edge.target}' not found in nodes")

        return v


class WorkflowUpdate(BaseModel):
    """
    工作流更新请求模型
    """

    name: Optional[str] = Field(default=None, description="工作流名称")
    description: Optional[str] = Field(default=None, description="工作流描述")
    status: Optional[WorkflowStatus] = Field(default=None, description="工作流状态")
    nodes: Optional[List[WorkflowNode]] = Field(default=None, description="工作流节点列表")
    edges: Optional[List[WorkflowEdge]] = Field(default=None, description="工作流连接边列表")
    variables: Optional[Dict[str, Any]] = Field(default=None, description="工作流变量")
    settings: Optional[Dict[str, Any]] = Field(default=None, description="工作流设置")
    tags: Optional[List[str]] = Field(default=None, description="工作流标签")


class Workflow(EntityModel):
    """
    工作流模型
    表示完整的工作流定义
    """

    user_id: str = Field(description="工作流所有者用户ID")
    name: str = Field(description="工作流名称")
    description: Optional[str] = Field(default=None, description="工作流描述")
    type: WorkflowType = Field(default=WorkflowType.SEQUENTIAL, description="工作流类型")
    status: WorkflowStatus = Field(default=WorkflowStatus.DRAFT, description="工作流状态")
    version: int = Field(default=1, description="工作流版本号")
    nodes: List[WorkflowNode] = Field(default_factory=list, description="工作流节点列表")
    edges: List[WorkflowEdge] = Field(default_factory=list, description="工作流连接边列表")
    variables: Dict[str, Any] = Field(default_factory=dict, description="工作流变量")
    settings: Dict[str, Any] = Field(default_factory=dict, description="工作流设置")
    tags: List[str] = Field(default_factory=list, description="工作流标签")
    execution_count: int = Field(default=0, description="执行次数")
    last_execution: Optional[str] = Field(default=None, description="最后执行时间")

    def is_executable(self) -> bool:
        """判断工作流是否可执行"""
        return self.status in [WorkflowStatus.ACTIVE] and len(self.nodes) > 0

    def get_trigger_nodes(self) -> List[WorkflowNode]:
        """获取触发器节点"""
        return [node for node in self.nodes if node.type == NodeType.TRIGGER]


class WorkflowExecution(EntityModel):
    """
    工作流执行记录模型
    """

    workflow_id: str = Field(description="工作流ID")
    session_id: Optional[str] = Field(default=None, description="关联的会话ID")
    user_id: str = Field(description="执行用户ID")
    status: str = Field(
        default="running", description="执行状态 (running, completed, failed, cancelled)"
    )
    input_data: Dict[str, Any] = Field(default_factory=dict, description="输入数据")
    output_data: Optional[Dict[str, Any]] = Field(default=None, description="输出数据")
    error_message: Optional[str] = Field(default=None, description="错误消息")
    start_time: Optional[str] = Field(default=None, description="开始时间")
    end_time: Optional[str] = Field(default=None, description="结束时间")
    duration_ms: Optional[int] = Field(default=None, description="执行持续时间（毫秒）")
    node_executions: List[Dict[str, Any]] = Field(default_factory=list, description="节点执行记录")


class WorkflowResponse(BaseModel):
    """
    工作流响应模型
    """

    workflow: Workflow = Field(description="工作流信息")
    message: Optional[str] = Field(default=None, description="响应消息")


class WorkflowListResponse(BaseModel):
    """
    工作流列表响应模型
    """

    workflows: List[Workflow] = Field(default_factory=list, description="工作流列表")
    total_count: int = Field(default=0, description="总数量")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=20, description="每页大小")


class WorkflowExecutionRequest(BaseModel):
    """
    工作流执行请求模型
    """

    inputs: Dict[str, Any] = Field(default_factory=dict, description="执行时的输入参数")
    settings: Optional[Dict[str, Any]] = Field(default=None, description="执行时的特殊设置")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="执行元数据")


class WorkflowExecutionResponse(BaseModel):
    """
    工作流执行响应模型
    """

    execution_id: str = Field(description="执行ID")
    workflow_id: str = Field(description="工作流ID")
    status: str = Field(description="执行状态")
    message: Optional[str] = Field(default=None, description="响应消息")
    started_at: Optional[str] = Field(default=None, description="开始执行时间")
