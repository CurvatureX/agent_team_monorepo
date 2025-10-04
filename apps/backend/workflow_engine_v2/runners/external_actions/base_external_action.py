"""
Base external action class for external action handlers in workflow_engine_v2.
"""

from __future__ import annotations

import logging
import sys
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models import ExecutionStatus, NodeExecutionResult
from shared.models.execution_new import LogLevel
from workflow_engine_v2.core.context import NodeExecutionContext
from workflow_engine_v2.services.oauth2_service import OAuth2ServiceV2


class BaseExternalAction(ABC):
    """Base class for all external actions in workflow_engine_v2."""

    def __init__(self, integration_name: str):
        self.integration_name = integration_name
        self.logger = logging.getLogger(__name__)
        self.oauth_service = OAuth2ServiceV2()

    async def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute the external action based on node configuration."""
        try:
            # Extract operation with priority: input_params > configurations
            # This allows AI agents to dynamically control action_type via their output

            # Check multiple locations for action_type (handles conversion function wrapping)
            operation = (
                context.input_data.get("action_type")  # Direct top-level
                or context.input_data.get("result", {}).get("action_type")  # Inside 'result' key
                or context.node.configurations.get("action_type")  # Configuration static
                or "default"  # Fallback
            )

            # Call the specific implementation
            return await self.handle_operation(context, operation)

        except Exception as e:
            self.log_execution(
                context, f"External action execution failed: {str(e)}", LogLevel.ERROR.value
            )
            return self.create_error_result(
                f"External action execution failed: {str(e)}",
                context.node.configurations.get("action_type", "unknown"),
                {"exception": str(e), "exception_type": type(e).__name__},
            )

    @abstractmethod
    async def handle_operation(
        self, context: NodeExecutionContext, operation: str
    ) -> NodeExecutionResult:
        """Handle the specific integration operation."""
        pass

    async def get_oauth_token(self, context: NodeExecutionContext) -> Optional[str]:
        """Get OAuth token for this integration from oauth_tokens table."""
        try:
            # Get user_id from multiple sources (prioritized)
            user_id = None

            # 1. Try from trigger (highest priority for workflow executions)
            if context.trigger:
                user_id = getattr(context.trigger, "user_id", None)

            # 2. Try from context metadata
            if not user_id and hasattr(context, "metadata") and context.metadata:
                user_id = context.metadata.get("user_id")

            # 3. Try from execution object (if it's a dict)
            if not user_id and context.execution:
                if isinstance(context.execution, dict):
                    user_id = context.execution.get("user_id")
                elif hasattr(context.execution, "user_id"):
                    user_id = getattr(context.execution, "user_id", None)

            if not user_id:
                self.log_execution(
                    context,
                    f"❌ Cannot get {self.integration_name} token: user_id not found in trigger, metadata, or execution",
                    LogLevel.ERROR.value,
                )
                return None

            # Get OAuth token using the service
            token = await self.oauth_service.get_valid_token(user_id, self.integration_name)

            if token:
                self.log_execution(
                    context, f"✅ Retrieved {self.integration_name} token for user {user_id}"
                )
                return token
            else:
                self.log_execution(
                    context,
                    f"❌ No valid {self.integration_name} token found for user {user_id}",
                    LogLevel.ERROR.value,
                )
                return None

        except Exception as e:
            self.log_execution(
                context,
                f"❌ Error retrieving {self.integration_name} token: {str(e)}",
                LogLevel.ERROR.value,
            )
            return None

    def log_execution(self, context: NodeExecutionContext, message: str, level: str = "INFO"):
        """Log execution message with context."""
        log_message = f"[{self.integration_name.upper()}] {message}"

        if level == LogLevel.ERROR.value:
            self.logger.error(log_message)
        elif level == "WARNING":
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)

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
            output_data={"main": base_output},
            metadata={
                "node_type": "external_action",
                "integration": self.integration_name,
                "operation": operation,
            },
        )


__all__ = ["BaseExternalAction"]
