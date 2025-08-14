"""
Base classes for node specifications system.

This module defines the core data structures for the node specification system,
including parameter definitions, port specifications, and node specifications.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class ParameterType(Enum):
    """Supported parameter types for node configuration."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ENUM = "enum"
    JSON = "json"
    FILE = "file"
    URL = "url"
    EMAIL = "email"
    CRON_EXPRESSION = "cron"


@dataclass
class ParameterDef:
    """Definition of a node parameter."""

    name: str
    type: ParameterType
    required: bool = False
    default_value: Optional[str] = None
    enum_values: Optional[List[str]] = None
    description: str = ""
    validation_pattern: Optional[str] = None


@dataclass
class DataFormat:
    """Data format specification for ports."""

    mime_type: str = "application/json"
    schema: Optional[str] = None  # JSON Schema
    examples: Optional[List[str]] = None


@dataclass
class InputPortSpec:
    """Specification for an input port."""

    name: str
    type: str  # ConnectionType (MAIN, AI_TOOL, AI_MEMORY, etc.)
    required: bool = False
    description: str = ""
    max_connections: int = 1  # Maximum connections, -1 for unlimited
    data_format: Optional[DataFormat] = None
    validation_schema: Optional[str] = None  # JSON Schema for validation


@dataclass
class OutputPortSpec:
    """Specification for an output port."""

    name: str
    type: str  # ConnectionType
    description: str = ""
    max_connections: int = -1  # -1 = unlimited
    data_format: Optional[DataFormat] = None
    validation_schema: Optional[str] = None  # JSON Schema for validation


@dataclass
class NodeSpec:
    """Complete specification for a node type."""

    node_type: str
    subtype: str
    version: str = "1.0.0"
    description: str = ""
    parameters: List[ParameterDef] = field(default_factory=list)
    input_ports: List[InputPortSpec] = field(default_factory=list)
    output_ports: List[OutputPortSpec] = field(default_factory=list)
    examples: Optional[List[Dict[str, Any]]] = None

    def get_parameter(self, name: str) -> Optional[ParameterDef]:
        """Get a parameter definition by name."""
        for param in self.parameters:
            if param.name == name:
                return param
        return None

    def get_input_port(self, name: str) -> Optional[InputPortSpec]:
        """Get an input port specification by name."""
        for port in self.input_ports:
            if port.name == name:
                return port
        return None

    def get_output_port(self, name: str) -> Optional[OutputPortSpec]:
        """Get an output port specification by name."""
        for port in self.output_ports:
            if port.name == name:
                return port
        return None

    def get_required_parameters(self) -> List[ParameterDef]:
        """Get all required parameters."""
        return [p for p in self.parameters if p.required]

    def get_required_input_ports(self) -> List[InputPortSpec]:
        """Get all required input ports."""
        return [p for p in self.input_ports if p.required]


@dataclass
class ConnectionSpec:
    """Connection specification between two ports."""

    source_port: str
    target_port: str
    connection_type: str  # ConnectionType
    validation_required: bool = True


# Connection types that correspond to the existing protocol buffer enums
class ConnectionType:
    """Standard connection types used in the workflow system."""

    MAIN = "MAIN"
    AI_TOOL = "AI_TOOL"
    AI_MEMORY = "AI_MEMORY"
    AI_LANGUAGE_MODEL = "AI_LANGUAGE_MODEL"
    ERROR = "ERROR"
    WEBHOOK = "WEBHOOK"
    HUMAN_INPUT = "HUMAN_INPUT"
    TRIGGER = "TRIGGER"
    SCHEDULE = "SCHEDULE"
    EMAIL = "EMAIL"
    SLACK = "SLACK"
    DATABASE = "DATABASE"
    FILE = "FILE"
    HTTP = "HTTP"
