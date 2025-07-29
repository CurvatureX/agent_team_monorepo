"""
This __init__.py file serves as the central hub for all Pydantic models
in the 'shared' directory. By importing and exposing all models here,
we can simplify imports in other parts of the application.

Instead of writing:
from shared.models.workflow import WorkflowData
from shared.models.agent import WorkflowGenerationRequest

You can simply write:
from shared.models import WorkflowData, WorkflowGenerationRequest

This approach offers several advantages:
1.  **Simplified Imports**: Reduces the verbosity and complexity of import statements.
2.  **Centralized Management**: Provides a single place to see all available shared models.
3.  **Refactoring Ease**: If model files are restructured, only this file needs to be
    updated, not every file that imports them.
4.  **Clear Public API**: Explicitly defines which models are part of the shared public
    interface of this module.
"""

# Import all models from the respective files
from .common import *
from .workflow import *
from .agent import *
from .execution import *
from .trigger import *
from .node import *

# Use __all__ to explicitly define the public API of this module
__all__ = [
    # common.py
    "BaseResponse",
    "ErrorResponse",
    "HealthStatus",
    "HealthResponse",
    # workflow.py
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
    # agent.py
    "WorkflowGenerationRequest",
    "WorkflowGenerationResponse",
    "WorkflowRefinementRequest",
    "WorkflowRefinementResponse",
    "WorkflowValidationRequest",
    "WorkflowValidationResponse",
    # execution.py
    "ExecutionStatus",
    "ExecutionLog",
    "Execution",
    # trigger.py
    "TriggerType",
    "Trigger",
    # node.py
    "NodeTemplate",
]
