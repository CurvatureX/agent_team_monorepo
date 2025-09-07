# 工作流相关的 Pydantic 模型
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from .common import BaseResponse, EntityModel
from .node_enums import NodeType


class PositionData(BaseModel):
    """节点位置数据"""

    x: float
    y: float


class RetryPolicyData(BaseModel):
    """重试策略数据"""

    max_tries: int = Field(default=3, ge=1, le=10)
    wait_between_tries: int = Field(default=5, ge=1, le=300)  # seconds


class NodeData(BaseModel):
    """
    工作流节点数据

    🎯 WORKFLOW GENERATION TIP:
    When using HUMAN_IN_THE_LOOP nodes, they have built-in AI response analysis capabilities.
    Use their confirmed/rejected/unrelated/timeout output ports instead of creating
    separate AI_AGENT or FLOW (IF) nodes for response classification.
    """

    id: Optional[str] = None  # 可选，系统会自动生成
    name: str
    type: str
    subtype: str
    type_version: int = Field(default=1)
    position: PositionData
    parameters: Dict[str, Any] = Field(default_factory=dict)
    credentials: Dict[str, str] = Field(default_factory=dict)
    disabled: bool = False
    on_error: str = Field(default="continue", pattern="^(continue|stop)$")
    retry_policy: Optional[RetryPolicyData] = None
    notes: Dict[str, str] = Field(default_factory=dict)
    webhooks: List[str] = Field(default_factory=list)


class ConnectionData(BaseModel):
    """连接数据"""

    node: str
    type: str
    index: int = Field(default=0)


class ConnectionArrayData(BaseModel):
    """连接数组数据"""

    connections: List[ConnectionData] = Field(default_factory=list)


class NodeConnectionsData(BaseModel):
    """节点连接数据"""

    connection_types: Dict[str, ConnectionArrayData] = Field(default_factory=dict)


class WorkflowSettingsData(BaseModel):
    """工作流设置数据"""

    timezone: Dict[str, str] = Field(default_factory=dict)
    save_execution_progress: bool = True
    save_manual_executions: bool = True
    timeout: int = Field(default=3600, ge=60, le=86400)  # 1 hour default, max 24 hours
    error_policy: str = Field(default="continue", pattern="^(continue|stop)$")
    caller_policy: str = Field(default="workflow", pattern="^(workflow|user)$")

    @field_validator("timezone", mode="before")
    @classmethod
    def validate_timezone(cls, v):
        if isinstance(v, str):
            return {"name": v}
        return v


class WorkflowData(BaseModel):
    """工作流数据"""

    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    nodes: List[NodeData]
    connections: Dict[str, Any] = Field(
        default_factory=dict
    )  # Keep as Any for now to handle validation properly
    settings: WorkflowSettingsData
    static_data: Dict[str, str] = Field(default_factory=dict)
    pin_data: Dict[str, str] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    active: bool = True
    created_at: Optional[int] = None
    updated_at: Optional[int] = None
    version: str = Field(default="1.0")

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("Workflow name cannot be empty")
        return v.strip()

    @field_validator("nodes")
    @classmethod
    def validate_nodes(cls, v):
        if not v:
            raise ValueError("Workflow must contain at least one node")
        node_ids = [node.id for node in v]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("Node IDs must be unique")
        return v

    @field_validator("connections", mode="before")
    @classmethod
    def validate_connections_format(cls, v):
        """Validate connections format and node references."""
        if not isinstance(v, dict):
            return v

        # Check each source node connection
        for source_node_id, node_connections in v.items():
            # Handle both dict and NodeConnectionsData objects
            if isinstance(node_connections, NodeConnectionsData):
                # Already a valid NodeConnectionsData object, skip validation
                continue
            elif not isinstance(node_connections, dict):
                raise ValueError(
                    f"Invalid connection format for node '{source_node_id}': must be an object"
                )

            # Detect old target-centric format and reject it
            if "main" in node_connections and isinstance(node_connections["main"], list):
                # This is the old format with nested arrays
                if len(node_connections["main"]) > 0 and isinstance(
                    node_connections["main"][0], list
                ):
                    raise ValueError(
                        f"Detected legacy connection format for node '{source_node_id}'. Use connection_types structure instead."
                    )

            # Validate new format structure
            if "connection_types" not in node_connections:
                raise ValueError(
                    f"Missing 'connection_types' in connections for node '{source_node_id}'. Required format: connection_types->main->connections"
                )

            connection_types = node_connections.get("connection_types", {})
            if not isinstance(connection_types, dict):
                raise ValueError(
                    f"'connection_types' must be an object for node '{source_node_id}'"
                )

            for conn_type, conn_array in connection_types.items():
                if not isinstance(conn_array, dict) or "connections" not in conn_array:
                    raise ValueError(
                        f"Invalid connection array format for '{source_node_id}.{conn_type}': must have 'connections' field"
                    )

                connections_list = conn_array.get("connections", [])
                if not isinstance(connections_list, list):
                    raise ValueError(
                        f"'connections' must be a list for '{source_node_id}.{conn_type}'"
                    )

                # Validate each connection has required fields
                for i, conn in enumerate(connections_list):
                    if not isinstance(conn, dict):
                        raise ValueError(
                            f"Connection {i} in '{source_node_id}.{conn_type}' must be an object"
                        )
                    if "node" not in conn:
                        raise ValueError(
                            f"Connection {i} in '{source_node_id}.{conn_type}' missing required 'node' field"
                        )

        return v


# Engine specific models
class CreateWorkflowRequest(BaseModel):
    """创建工作流请求"""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    nodes: List[NodeData] = Field(..., min_items=1)
    connections: Dict[str, Any] = Field(default_factory=dict)
    settings: Optional[WorkflowSettingsData] = None
    static_data: Dict[str, str] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    user_id: str = Field(..., min_length=1)
    session_id: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("工作流名称不能为空或仅包含空格")
        return v.strip()

    @field_validator("nodes")
    @classmethod
    def validate_node_connections(cls, v):
        if not v:
            raise ValueError("工作流必须包含至少一个节点")
        # 只检查非空的节点 ID
        node_ids = [node.id for node in v if node.id is not None]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("节点ID必须唯一")
        return v

    @field_validator("connections", mode="before")
    @classmethod
    def validate_connections_format(cls, v):
        """Validate connections format and node references."""
        if not isinstance(v, dict):
            return v

        # Check each source node connection
        for source_node_id, node_connections in v.items():
            # Handle both dict and NodeConnectionsData objects
            if isinstance(node_connections, NodeConnectionsData):
                # Already a valid NodeConnectionsData object, skip validation
                continue
            elif not isinstance(node_connections, dict):
                raise ValueError(
                    f"Invalid connection format for node '{source_node_id}': must be an object"
                )

            # Detect old target-centric format and reject it
            if "main" in node_connections and isinstance(node_connections["main"], list):
                # This is the old format with nested arrays
                if len(node_connections["main"]) > 0 and isinstance(
                    node_connections["main"][0], list
                ):
                    raise ValueError(
                        f"Detected legacy connection format for node '{source_node_id}'. Use connection_types structure instead."
                    )

            # Validate new format structure
            if "connection_types" not in node_connections:
                raise ValueError(
                    f"Missing 'connection_types' in connections for node '{source_node_id}'. Required format: connection_types->main->connections"
                )

            connection_types = node_connections.get("connection_types", {})
            if not isinstance(connection_types, dict):
                raise ValueError(
                    f"'connection_types' must be an object for node '{source_node_id}'"
                )

            for conn_type, conn_array in connection_types.items():
                if not isinstance(conn_array, dict) or "connections" not in conn_array:
                    raise ValueError(
                        f"Invalid connection array format for '{source_node_id}.{conn_type}': must have 'connections' field"
                    )

                connections_list = conn_array.get("connections", [])
                if not isinstance(connections_list, list):
                    raise ValueError(
                        f"'connections' must be a list for '{source_node_id}.{conn_type}'"
                    )

                # Validate each connection has required fields
                for i, conn in enumerate(connections_list):
                    if not isinstance(conn, dict):
                        raise ValueError(
                            f"Connection {i} in '{source_node_id}.{conn_type}' must be an object"
                        )
                    if "node" not in conn:
                        raise ValueError(
                            f"Connection {i} in '{source_node_id}.{conn_type}' missing required 'node' field"
                        )

        return v


class CreateWorkflowResponse(BaseModel):
    workflow: WorkflowData
    success: bool = True
    message: str = "Workflow created successfully"


class GetWorkflowRequest(BaseModel):
    workflow_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    session_id: Optional[str] = None


class GetWorkflowResponse(BaseModel):
    """获取工作流响应"""

    workflow: Optional[WorkflowData] = None
    found: bool
    message: str = ""


class UpdateWorkflowRequest(BaseModel):
    """更新工作流请求"""

    workflow_id: str = Field(..., min_length=1)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    nodes: Optional[List[NodeData]] = None
    connections: Optional[Dict[str, Any]] = None
    settings: Optional[WorkflowSettingsData] = None
    static_data: Optional[Dict[str, str]] = None
    tags: Optional[List[str]] = None
    active: Optional[bool] = None
    user_id: str = Field(..., min_length=1)
    session_id: Optional[str] = None

    @field_validator("connections", mode="before")
    @classmethod
    def validate_connections_format(cls, v):
        """Validate connections format when provided."""
        if v is None:
            return v
        if not isinstance(v, dict):
            return v

        # Check each source node connection
        for source_node_id, node_connections in v.items():
            # Handle both dict and NodeConnectionsData objects
            if isinstance(node_connections, NodeConnectionsData):
                # Already a valid NodeConnectionsData object, skip validation
                continue
            elif not isinstance(node_connections, dict):
                raise ValueError(
                    f"Invalid connection format for node '{source_node_id}': must be an object"
                )

            # Detect old target-centric format and reject it
            if "main" in node_connections and isinstance(node_connections["main"], list):
                # This is the old format with nested arrays
                if len(node_connections["main"]) > 0 and isinstance(
                    node_connections["main"][0], list
                ):
                    raise ValueError(
                        f"Detected legacy connection format for node '{source_node_id}'. Use connection_types structure instead."
                    )

            # Validate new format structure
            if "connection_types" not in node_connections:
                raise ValueError(
                    f"Missing 'connection_types' in connections for node '{source_node_id}'. Required format: connection_types->main->connections"
                )

            connection_types = node_connections.get("connection_types", {})
            if not isinstance(connection_types, dict):
                raise ValueError(
                    f"'connection_types' must be an object for node '{source_node_id}'"
                )

            for conn_type, conn_array in connection_types.items():
                if not isinstance(conn_array, dict) or "connections" not in conn_array:
                    raise ValueError(
                        f"Invalid connection array format for '{source_node_id}.{conn_type}': must have 'connections' field"
                    )

                connections_list = conn_array.get("connections", [])
                if not isinstance(connections_list, list):
                    raise ValueError(
                        f"'connections' must be a list for '{source_node_id}.{conn_type}'"
                    )

                # Validate each connection has required fields
                for i, conn in enumerate(connections_list):
                    if not isinstance(conn, dict):
                        raise ValueError(
                            f"Connection {i} in '{source_node_id}.{conn_type}' must be an object"
                        )
                    if "node" not in conn:
                        raise ValueError(
                            f"Connection {i} in '{source_node_id}.{conn_type}' missing required 'node' field"
                        )

        return v


class UpdateWorkflowResponse(BaseModel):
    workflow: WorkflowData
    success: bool = True
    message: str = "Workflow updated successfully"


class DeleteWorkflowRequest(BaseModel):
    workflow_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)


class DeleteWorkflowResponse(BaseModel):
    success: bool = True
    message: str = "Workflow deleted successfully"


class ListWorkflowsRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    active_only: bool = True
    tags: List[str] = Field(default_factory=list)
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class ListWorkflowsResponse(BaseModel):
    """列表工作流响应"""

    workflows: List[WorkflowData]
    total_count: int
    has_more: bool


class ExecuteWorkflowRequest(BaseModel):
    """执行工作流请求"""

    workflow_id: str = Field(..., min_length=1)
    trigger_data: Dict[str, str] = Field(default_factory=dict)
    user_id: str = Field(..., min_length=1)
    session_id: Optional[str] = None
    
    # 新增参数：支持从指定节点开始执行
    start_from_node: Optional[str] = Field(
        default=None, 
        description="指定从哪个节点开始执行，为空时从触发器节点开始",
        example="ai_message_classification"
    )
    skip_trigger_validation: bool = Field(
        default=False,
        description="是否跳过触发器验证，用于从中间节点开始执行时使用"
    )
    
    # 新增：当使用start_from_node时，可以提供自定义输入数据
    inputs: Optional[Dict[str, Any]] = Field(
        default=None,
        description="当使用start_from_node时的自定义输入数据，将传递给起始节点"
    )


class ExecuteWorkflowResponse(BaseModel):
    execution_id: str
    status: str = "running"
    success: bool = True
    message: str = "Workflow execution started"


# API Gateway特有的工作流模型
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


# Legacy NodeType removed - now using authoritative enums from shared.models.node_enums
# All services should import NodeType from shared.models directly


class WorkflowEdge(BaseModel):
    """
    工作流连接边模型
    """

    id: str = Field(description="边的唯一标识符")
    source: str = Field(description="源节点ID")
    target: str = Field(description="目标节点ID")
    condition: Optional[str] = Field(default=None, description="边的条件表达式")
    label: Optional[str] = Field(default=None, description="边的标签")


# Duplicate definitions removed - use the workflow-engine specific models above
# API Gateway should use CreateWorkflowRequest and UpdateWorkflowRequest defined earlier


class WorkflowExecutionRecord(EntityModel):
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

    workflow: WorkflowData = Field(description="工作流信息")
    message: Optional[str] = Field(default=None, description="响应消息")


class WorkflowListResponse(BaseModel):
    """
    工作流列表响应模型
    """

    workflows: List[WorkflowData] = Field(default_factory=list, description="工作流列表")
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
    
    # 新增参数：支持从指定节点开始执行
    start_from_node: Optional[str] = Field(
        default=None, 
        description="指定从哪个节点开始执行，为空时从触发器节点开始",
        example="ai_message_classification"
    )
    skip_trigger_validation: bool = Field(
        default=False,
        description="是否跳过触发器验证，用于从中间节点开始执行时使用"
    )


class WorkflowExecutionResponse(BaseModel):
    """
    工作流执行响应模型
    """

    execution_id: str = Field(description="执行ID")
    workflow_id: str = Field(description="工作流ID")
    status: str = Field(description="执行状态")
    message: Optional[str] = Field(default=None, description="响应消息")
    started_at: Optional[str] = Field(default=None, description="开始执行时间")


class NodeTemplate(BaseModel):
    """
    Node Template Model
    """

    id: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    node_type: str
    node_subtype: str
    version: Optional[str] = "1.0.0"
    is_system_template: bool = False
    default_parameters: Optional[Dict[str, Any]] = None
    required_parameters: Optional[List[str]] = None
    parameter_schema: Optional[Dict[str, Any]] = None


class NodeTemplateListResponse(BaseModel):
    """
    Response model for a list of node templates.
    """

    node_templates: List[NodeTemplate] = Field(default_factory=list)


# Single Node Execution Models
class ExecuteSingleNodeRequest(BaseModel):
    """
    请求执行工作流中的单个节点
    """

    user_id: str = Field(..., description="用户ID", min_length=1)
    input_data: Dict[str, Any] = Field(default_factory=dict, description="节点执行的输入数据")
    execution_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="执行上下文配置",
        example={
            "use_previous_results": False,
            "previous_execution_id": None,
            "override_parameters": {},
            "credentials": {},
        },
    )

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "00000000-0000-0000-0000-000000000123",
                "input_data": {"url": "https://api.example.com", "method": "GET"},
                "execution_context": {
                    "use_previous_results": False,
                    "override_parameters": {"timeout": "30"},
                },
            }
        }


class SingleNodeExecutionResponse(BaseModel):
    """
    单节点执行响应
    """

    execution_id: str = Field(..., description="执行ID")
    node_id: str = Field(..., description="节点ID")
    workflow_id: str = Field(..., description="工作流ID")
    status: str = Field(..., description="执行状态")
    output_data: Dict[str, Any] = Field(default_factory=dict, description="节点输出数据")
    execution_time: float = Field(..., description="执行时间（秒）")
    logs: List[str] = Field(default_factory=list, description="执行日志")
    error_message: Optional[str] = Field(None, description="错误信息")

    class Config:
        json_schema_extra = {
            "example": {
                "execution_id": "single-node-exec-123",
                "node_id": "http_request_node",
                "workflow_id": "workflow-456",
                "status": "COMPLETED",
                "output_data": {"response_code": 200, "response_body": {"data": "example"}},
                "execution_time": 1.23,
                "logs": ["Starting HTTP request...", "Request completed"],
                "error_message": None,
            }
        }
