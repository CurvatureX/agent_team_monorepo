"""
Services package for Workflow Engine

Core services migrated from old workflow engine structure.
Provides business logic layer for workflow operations.
"""

from .supabase_repository import SupabaseWorkflowRepository
from .validation_service import (
    TestNodeRequest,
    TestNodeResponse,
    ValidateWorkflowRequest,
    ValidateWorkflowResponse,
    ValidationService,
)
from .workflow_service import CreateWorkflowRequest, UpdateWorkflowRequest, WorkflowService

# ExecutionService imports moved to avoid circular dependency with executor
# Import ExecutionService directly when needed: from services.execution_service import ExecutionService

# Additional migrated services (lazy imports to avoid circular dependencies)
try:
    from .oauth2_service_lite import OAuth2ServiceLite
except ImportError:
    OAuth2ServiceLite = None

try:
    from .hil_service import HILWorkflowService
except ImportError:
    HILWorkflowService = None

try:
    from .unified_log_service import get_unified_log_service
except ImportError:
    get_unified_log_service = None

try:
    from .execution_log_service import ExecutionLogService
except ImportError:
    ExecutionLogService = None

try:
    from .api_call_logger import APICallTracker, get_api_call_logger
except ImportError:
    APICallTracker = None
    get_api_call_logger = None

try:
    from .channel_integration_manager import ChannelIntegrationManager
except ImportError:
    ChannelIntegrationManager = None

__all__ = [
    # Repository
    "SupabaseWorkflowRepository",
    # Workflow Service
    "WorkflowService",
    "CreateWorkflowRequest",
    "UpdateWorkflowRequest",
    # Validation Service
    "ValidationService",
    "ValidateWorkflowRequest",
    "ValidateWorkflowResponse",
    "TestNodeRequest",
    "TestNodeResponse",
    # Additional Services (conditionally available)
    "OAuth2ServiceLite",
    "HILWorkflowService",
    "get_unified_log_service",
    "ExecutionLogService",
    "APICallTracker",
    "get_api_call_logger",
    "ChannelIntegrationManager",
]

# Note: ExecutionService exports removed to avoid circular import with executor
# Import directly: from services.execution_service import ExecutionService, ExecuteWorkflowRequest, etc.
