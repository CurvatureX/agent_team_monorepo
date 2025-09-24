"""
Base external action class for external action handlers.
"""

# DNS resolution should work normally for external APIs
# Removed IPv4-only patches that were causing connection failures

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

from nodes.base import ExecutionStatus, NodeExecutionContext, NodeExecutionResult


class BaseExternalAction(ABC):
    """Base class for all external actions."""

    def __init__(self, integration_name: str):
        self.integration_name = integration_name

    @abstractmethod
    async def handle_operation(
        self, context: NodeExecutionContext, operation: str
    ) -> NodeExecutionResult:
        """Handle the specific integration operation."""
        pass

    async def get_oauth_token(self, context: NodeExecutionContext) -> Optional[str]:
        """Get OAuth token for this integration from oauth_tokens table."""
        try:
            from services.oauth2_service_lite import OAuth2ServiceLite

            # Get user_id from workflow execution context
            user_id = None

            # First try metadata
            if hasattr(context, "metadata") and context.metadata:
                user_id = context.metadata.get("user_id")

            # Try getting from database via workflow_id
            if not user_id and context.workflow_id:
                from services.supabase_repository import SupabaseWorkflowRepository

                repository = SupabaseWorkflowRepository()
                workflow = await repository.get_workflow(context.workflow_id)
                if workflow:
                    user_id = workflow.get("user_id")

            if not user_id:
                self.log_execution(
                    context,
                    f"❌ Cannot get {self.integration_name} token: user_id not found",
                    "ERROR",
                )
                return None

            # Get OAuth token using the service
            oauth_service = OAuth2ServiceLite()
            token = await oauth_service.get_valid_token(user_id, self.integration_name)

            if token:
                self.log_execution(
                    context, f"✅ Retrieved {self.integration_name} token for user {user_id}"
                )
                return token
            else:
                self.log_execution(
                    context,
                    f"❌ No valid {self.integration_name} token found for user {user_id}",
                    "ERROR",
                )
                return None

        except Exception as e:
            self.log_execution(
                context, f"❌ Error retrieving {self.integration_name} token: {str(e)}", "ERROR"
            )
            return None

    def log_execution(self, context: NodeExecutionContext, message: str, level: str = "INFO"):
        """Log execution message with context."""
        import logging

        logger = logging.getLogger(__name__)

        log_message = f"[{self.integration_name.upper()}] {message}"

        if level == "ERROR":
            logger.error(log_message)
        elif level == "WARNING":
            logger.warning(log_message)
        else:
            logger.info(log_message)

    def create_error_result(
        self, message: str, operation: str, error_details: Dict[str, Any] = None
    ) -> NodeExecutionResult:
        """Create a standardized error result."""
        return NodeExecutionResult(
            status=ExecutionStatus.ERROR,
            error_message=message,
            error_details={
                "integration": self.integration_name,
                "operation": operation,
                "reason": "missing_oauth_token",
                "solution": f"Connect {self.integration_name.title()} account in integrations settings",
                **(error_details or {}),
            },
            metadata={
                "node_type": "external_action",
                "integration": self.integration_name,
                "operation": operation,
            },
        )

    def create_success_result(
        self, operation: str, output_data: Dict[str, Any]
    ) -> NodeExecutionResult:
        """Create a standardized success result."""
        base_output = {
            "integration_type": self.integration_name,
            "operation": operation,
            "timestamp": datetime.now().isoformat(),
        }
        base_output.update(output_data)

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=base_output,
            metadata={
                "node_type": "external_action",
                "integration": self.integration_name,
                "operation": operation,
            },
        )
