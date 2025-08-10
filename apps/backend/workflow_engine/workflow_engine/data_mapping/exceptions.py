"""
Data Mapping System Exceptions

Custom exception classes for data mapping operations.
"""


class DataMappingError(Exception):
    """Base exception for data mapping operations."""

    pass


class FieldExtractionError(DataMappingError):
    """Exception raised when field extraction fails."""

    pass


class TransformationError(DataMappingError):
    """Exception raised when data transformation fails."""

    pass


class ValidationError(DataMappingError):
    """Exception raised when data validation fails."""

    pass


class ConnectionExecutionError(DataMappingError):
    """Exception raised when connection execution fails."""

    pass


class TemplateRenderError(DataMappingError):
    """Exception raised when template rendering fails."""

    pass


class ScriptExecutionError(DataMappingError):
    """Exception raised when script execution fails."""

    pass


class JSONPathError(DataMappingError):
    """Exception raised when JSONPath operation fails."""

    pass


class FunctionNotFoundError(DataMappingError):
    """Exception raised when a transform function is not found."""

    pass
