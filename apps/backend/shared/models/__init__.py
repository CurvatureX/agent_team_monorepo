# 共享 Pydantic 模型
# 集中管理所有服务的数据模型，确保一致性和复用性

from .common import *
from .workflow import *
from .conversation import *

__all__ = [
    # Common models
    "BaseResponse",
    "ErrorResponse",
    "HealthResponse",
    "HealthStatus",
    "ServiceStatus",
    "ServiceHealthCheck",
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
    # Conversation models (ProcessConversation interface)
    "WorkflowContext",
    "ConversationRequest", 
    "ConversationResponse",
    "ResponseType",
    "ErrorContent",
]
