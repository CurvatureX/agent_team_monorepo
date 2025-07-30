# Data Mapping System for Workflow Engine

from .context import ExecutionContext
from .engines import FunctionRegistry, JSONPathParser, ScriptEngine, TemplateEngine
from .exceptions import (
    ConnectionExecutionError,
    DataMappingError,
    FieldExtractionError,
    TransformationError,
    ValidationError,
)
from .executors import ConnectionExecutor, NodeExecutionResult
from .processor import (
    DataMapping,
    DataMappingProcessor,
    FieldMapping,
    FieldTransform,
    MappingType,
    TransformType,
)
from .validators import DataMappingValidator

__all__ = [
    # Core processor
    "DataMappingProcessor",
    "DataMapping",
    "FieldMapping",
    "FieldTransform",
    "MappingType",
    "TransformType",
    # Executors
    "ConnectionExecutor",
    "NodeExecutionResult",
    # Validators
    "DataMappingValidator",
    # Engines
    "TemplateEngine",
    "ScriptEngine",
    "JSONPathParser",
    "FunctionRegistry",
    # Exceptions
    "DataMappingError",
    "FieldExtractionError",
    "TransformationError",
    "ValidationError",
    "ConnectionExecutionError",
    # Context
    "ExecutionContext",
]
