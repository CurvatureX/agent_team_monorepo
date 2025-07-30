"""
Execution Context for Data Mapping

Provides environment variables and runtime information for data transformations.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class ExecutionContext:
    """Execution context providing environment variables and runtime information."""

    workflow_id: str
    execution_id: str
    node_id: str
    current_time: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    environment: str = "production"

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for template variables."""
        return {
            "workflow_id": self.workflow_id,
            "execution_id": self.execution_id,
            "node_id": self.node_id,
            "current_time": self.current_time,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "environment": self.environment,
        }

    @classmethod
    def create_default(
        cls, workflow_id: str, execution_id: str, node_id: str
    ) -> "ExecutionContext":
        """Create a default execution context with current timestamp."""
        return cls(
            workflow_id=workflow_id,
            execution_id=execution_id,
            node_id=node_id,
            current_time=datetime.now().isoformat(),
        )
