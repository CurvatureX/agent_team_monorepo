# 共享 Pydantic 模型
# 集中管理所有服务的数据模型，确保一致性和复用性

from .agent import *
from .common import *
from .execution import *
from .trigger import *
from .workflow import *

__all__ = [
    # Common models
    "BaseResponse",
    "ErrorResponse",
    "HealthResponse",
    # Workflow models
    "PositionData",
    "RetryPolicyData",
    "NodeData",
    "ConnectionData",
    "ConnectionArrayData",
    "NodeConnectionsData",
    "ConnectionsMapData",
    "WorkflowSettingsData",
    "WorkflowData",
    "CreateWorkflowRequest",
    "CreateWorkflowResponse",
    "GetWorkflowRequest",
    "GetWorkflowResponse",
    "UpdateWorkflowRequest",
    "UpdateWorkflowResponse",
    "DeleteWorkflowRequest",
    "DeleteWorkflowResponse",
    "ListWorkflowsRequest",
    "ListWorkflowsResponse",
    "ExecuteWorkflowRequest",
    "ExecuteWorkflowResponse",
    # Agent models
    "WorkflowGenerationRequest",
    "WorkflowGenerationResponse",
    "WorkflowRefinementRequest",
    "WorkflowRefinementResponse",
    "WorkflowValidationRequest",
    "WorkflowValidationResponse",
    # Execution models
    "ExecutionStatusRequest",
    "ExecutionStatusResponse",
    "CancelExecutionRequest",
    "CancelExecutionResponse",
    "ExecutionHistoryRequest",
    "ExecutionHistoryResponse",
    # Trigger models
    "TriggerData",
    "CreateTriggerRequest",
    "CreateTriggerResponse",
    "GetTriggerRequest",
    "GetTriggerResponse",
    "UpdateTriggerRequest",
    "UpdateTriggerResponse",
    "DeleteTriggerRequest",
    "DeleteTriggerResponse",
    "ListTriggersRequest",
    "ListTriggersResponse",
    "FireTriggerRequest",
    "FireTriggerResponse",
]
