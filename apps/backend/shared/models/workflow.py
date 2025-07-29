# 工作流相关的 Pydantic 模型
from typing import List, Dict, Optional
from enum import Enum
from pydantic import BaseModel, Field, validator

from .common import BaseResponse


class PositionData(BaseModel):
    """节点位置数据"""
    x: float
    y: float


class RetryPolicyData(BaseModel):
    """重试策略数据"""
    max_tries: int = Field(default=3, ge=1, le=10)
    wait_between_tries: int = Field(default=5, ge=1, le=300)  # seconds


class NodeData(BaseModel):
    """工作流节点数据"""
    id: str
    name: str
    type: str
    subtype: Optional[str] = None
    type_version: int = Field(default=1)
    position: PositionData
    parameters: Dict[str, str] = Field(default_factory=dict)
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


class ConnectionsMapData(BaseModel):
    """连接映射数据"""
    connections: Dict[str, NodeConnectionsData] = Field(default_factory=dict)


class WorkflowSettingsData(BaseModel):
    """工作流设置数据"""
    timezone: Dict[str, str] = Field(default_factory=dict)
    save_execution_progress: bool = True
    save_manual_executions: bool = True
    timeout: int = Field(default=3600, ge=60, le=86400)  # 1 hour default, max 24 hours
    error_policy: str = Field(default="continue", pattern="^(continue|stop)$")
    caller_policy: str = Field(default="workflow", pattern="^(workflow|user)$")


class WorkflowData(BaseModel):
    """工作流数据"""
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    nodes: List[NodeData]
    connections: ConnectionsMapData
    settings: WorkflowSettingsData
    static_data: Dict[str, str] = Field(default_factory=dict)
    pin_data: Dict[str, str] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    active: bool = True
    created_at: Optional[int] = None
    updated_at: Optional[int] = None
    version: str = Field(default="1.0")

    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('工作流名称不能为空')
        return v.strip()

    @validator('nodes')
    def validate_nodes(cls, v):
        if not v:
            raise ValueError('工作流必须包含至少一个节点')
        node_ids = [node.id for node in v]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError('节点ID必须唯一')
        return v


# Engine specific models
class CreateWorkflowRequest(BaseModel):
    """创建工作流请求"""
    name: str = Field(..., min_length=1, max_length=255, description="工作流名称")
    description: Optional[str] = Field(None, max_length=1000, description="工作流描述")
    nodes: List[NodeData] = Field(..., min_items=1, description="至少需要一个节点")
    connections: ConnectionsMapData
    settings: Optional[WorkflowSettingsData] = None
    static_data: Dict[str, str] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    user_id: str = Field(..., min_length=1, description="用户ID")
    session_id: Optional[str] = None

    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('工作流名称不能为空或仅包含空格')
        return v.strip()

    @validator('nodes')
    def validate_node_connections(cls, v):
        if not v:
            raise ValueError('工作流必须包含至少一个节点')
        node_ids = [node.id for node in v]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError('节点ID必须唯一')
        return v


class CreateWorkflowResponse(BaseResponse):
    """创建工作流响应"""
    workflow: WorkflowData

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "工作流创建成功",
                "workflow": {
                    "id": "wf_123456",
                    "name": "邮件处理工作流",
                    "description": "自动处理传入邮件",
                    "nodes": [],
                    "connections": {},
                    "settings": {}
                }
            }
        }


class GetWorkflowRequest(BaseModel):
    """获取工作流请求"""
    workflow_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)


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
    connections: Optional[ConnectionsMapData] = None
    settings: Optional[WorkflowSettingsData] = None
    static_data: Optional[Dict[str, str]] = None
    tags: Optional[List[str]] = None
    active: Optional[bool] = None
    user_id: str = Field(..., min_length=1)
    session_id: Optional[str] = None


class UpdateWorkflowResponse(BaseResponse):
    """更新工作流响应"""
    workflow: WorkflowData

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "工作流更新成功",
                "workflow": {
                    "id": "wf_123456",
                    "name": "更新的工作流",
                    "description": "更新后的描述",
                    "nodes": [],
                    "connections": {},
                    "settings": {}
                }
            }
        }


class DeleteWorkflowRequest(BaseModel):
    """删除工作流请求"""
    workflow_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)


class DeleteWorkflowResponse(BaseResponse):
    """删除工作流响应"""
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "工作流删除成功"
            }
        }


class ListWorkflowsRequest(BaseModel):
    """列表工作流请求"""
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


class ExecuteWorkflowResponse(BaseResponse):
    """执行工作流响应"""
    execution_id: str
    status: str = "running"

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "工作流执行已启动",
                "execution_id": "exec_123456",
                "status": "running"
            }
        }