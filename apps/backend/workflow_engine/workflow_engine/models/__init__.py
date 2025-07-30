"""Data models for workflow engine - now using shared models."""

# Import SQLAlchemy models from shared
import sys
from pathlib import Path

# Add backend directory to Python path for shared models
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models.db_models import Base
from shared.models.db_models import (
    NodeTemplateDB as NodeTemplate,  # Alias for backward compatibility
)
from shared.models.db_models import WorkflowDB as Workflow  # Alias for backward compatibility
from shared.models.db_models import WorkflowExecution

# Backward compatibility aliases
WorkflowModel = Workflow
ExecutionModel = WorkflowExecution
NodeTemplateModel = NodeTemplate

__all__ = [
    "Base",
    "WorkflowExecution",
    "Workflow",
    "NodeTemplate",
    # Backward compatibility
    "WorkflowModel",
    "ExecutionModel",
    "NodeTemplateModel",
]
