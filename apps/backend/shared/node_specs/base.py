"""
Base classes for node specifications system.

This module defines the core data structures for the node specification system,
including parameter definitions, port specifications, and node specifications.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


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
    """Specification for an input port - Updated to match new workflow spec."""

    name: str
    type: str  # ConnectionType (MAIN, AI_TOOL, AI_MEMORY, etc.)
    data_type: str = "dict"  # Data type: 'str', 'int', 'float', 'bool', 'dict', 'list'
    required: bool = False
    description: str = ""
    max_connections: int = 1  # Maximum connections, -1 for unlimited
    data_format: Optional[DataFormat] = None
    validation_schema: Optional[str] = None  # JSON Schema for validation


@dataclass
class OutputPortSpec:
    """Specification for an output port - Updated to match new workflow spec."""

    name: str
    type: str  # ConnectionType
    data_type: str = "dict"  # Data type: 'str', 'int', 'float', 'bool', 'dict', 'list'
    description: str = ""
    max_connections: int = -1  # -1 = unlimited
    data_format: Optional[DataFormat] = None
    validation_schema: Optional[str] = None  # JSON Schema for validation


@dataclass
class ManualInvocationSpec:
    """Specification for manual trigger invocation parameters."""

    supported: bool = False  # Whether manual invocation is supported
    parameter_schema: Optional[Dict[str, Any]] = None  # JSON Schema for manual parameters
    parameter_examples: Optional[List[Dict[str, Any]]] = None  # Example parameter sets
    default_parameters: Optional[Dict[str, Any]] = None  # Default parameter values
    description: str = ""  # Description of manual invocation behavior


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

    # Enhanced fields for node_templates compatibility
    display_name: Optional[str] = None  # Human-readable name for UI
    category: Optional[str] = None  # Category for grouping (e.g., "ai", "actions")
    template_id: Optional[str] = None  # Legacy template ID for migration
    is_system_template: bool = True  # Whether this is a system-provided spec

    # Manual invocation support for triggers
    manual_invocation: Optional[ManualInvocationSpec] = None

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

    def validate_spec(self) -> bool:
        """Validate that the node specification is complete and correct."""
        # Check required fields
        if not self.node_type or not self.subtype:
            return False

        # Validate port IDs are unique
        input_ids = [port.id for port in self.input_ports]
        output_ids = [port.id for port in self.output_ports]

        if len(input_ids) != len(set(input_ids)) or len(output_ids) != len(set(output_ids)):
            return False

        return True


@dataclass
class ConnectionSpec:
    """Connection specification between two ports."""

    source_port: str
    target_port: str
    connection_type: str  # ConnectionType
    conversion_function: str  # Required Python function as string
    validation_required: bool = True


# ============================================================================
# CONVERSION FUNCTION SPECIFICATION
# ============================================================================


def validate_conversion_function(func_string: str) -> bool:
    """
    Validate that a conversion function string follows the required format.

    Required format:
    'def convert(input_data: Dict[str, Any]) -> Dict[str, Any]: return transformed_data'

    Args:
        func_string: Python function as string (REQUIRED, cannot be empty)

    Returns:
        bool: True if valid, False otherwise
    """
    if not func_string or not func_string.strip():
        return False

    # Check basic structure
    if not func_string.strip().startswith("def convert("):
        return False

    if "-> Dict[str, Any]:" not in func_string:
        return False

    # Try to compile the function
    try:
        compile(func_string, "<conversion_function>", "exec")
        return True
    except SyntaxError:
        return False


def execute_conversion_function(func_string: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a conversion function string safely.

    Args:
        func_string: Python function as string (REQUIRED)
        input_data: Input data to transform

    Returns:
        Dict[str, Any]: Transformed data or original data if execution fails
    """
    if not func_string or not validate_conversion_function(func_string):
        # If no valid conversion function provided, this is an error
        # Log the issue but return original data to prevent workflow failure
        print(f"ERROR: Invalid or missing conversion function. Using passthrough.")
        return input_data

    try:
        # Create a restricted namespace for security
        namespace = {
            "Dict": Dict,
            "Any": Any,
            "__builtins__": {
                "len": len,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "list": list,
                "dict": dict,
                "range": range,
                "enumerate": enumerate,
                "zip": zip,
                "max": max,
                "min": min,
                "sum": sum,
                "abs": abs,
                "round": round,
            },
        }

        # Execute the function definition
        exec(func_string, namespace)

        # Get the convert function
        convert_func = namespace.get("convert")
        if not convert_func:
            return input_data

        # Execute the conversion
        result = convert_func(input_data)

        # Ensure result is a dictionary
        if isinstance(result, dict):
            return result
        else:
            return {"converted_data": result}

    except Exception as e:
        # Log the error but return original data to prevent workflow failure
        print(f"Conversion function execution failed: {e}")
        return input_data


# ============================================================================
# CONVERSION FUNCTION EXAMPLES
# ============================================================================

CONVERSION_FUNCTION_EXAMPLES = {
    "passthrough": """def convert(input_data: Dict[str, Any]) -> Dict[str, Any]: return input_data""",
    "add_slack_formatting": """def convert(input_data: Dict[str, Any]) -> Dict[str, Any]: return {"text": f"🎭 {input_data.get('output', '')} 🎭", "channel": "#general"}""",
    "extract_ai_response": """def convert(input_data: Dict[str, Any]) -> Dict[str, Any]: return {"message": input_data.get("output", ""), "timestamp": str(input_data.get("timestamp", ""))}""",
    "trigger_to_ai_prompt": """def convert(input_data: Dict[str, Any]) -> Dict[str, Any]: return {"user_input": input_data.get("message", "Tell me a joke"), "context": "joke_generation"}""",
    "format_notification": """def convert(input_data: Dict[str, Any]) -> Dict[str, Any]: return {"title": "Workflow Update", "body": f"Status: {input_data.get('status', 'unknown')}", "priority": "normal"}""",
}


# Connection types that correspond to the existing protocol buffer enums
class ConnectionType:
    """Standard connection types used in the workflow system."""

    MAIN = "MAIN"
    AI_TOOL = "AI_TOOL"
    AI_MEMORY = "AI_MEMORY"
    MEMORY = "MEMORY"  # Dedicated memory context connection
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
    MCP_TOOLS = "MCP_TOOLS"  # AI nodes ↔ TOOL nodes for MCP function calling


# Import NodeType for the BaseNodeSpec class
try:
    from ..models.node_enums import NodeType
except ImportError:
    from ...models.node_enums import NodeType

try:
    from ..models.workflow_new import Node, Port
except ImportError:
    from ...models.workflow_new import Node, Port


class BaseNodeSpec(BaseModel):
    """Base class for all node specifications following the new workflow spec.

    Note on params fields:
    - input_params/output_params: schema-style parameter definitions (like configurations)
      Each param is a dict with at least: type, default, description, required,
      and optional options for enums.
    - default_input_params/default_output_params: legacy defaults used by many
      existing node specs. Kept for backward compatibility.

    When creating a node instance, runtime input/output params are derived from
    input_params/output_params defaults if provided, otherwise from the legacy
    default_* dictionaries.
    """

    # Core node identification
    type: NodeType = Field(..., description="节点大类")
    subtype: str = Field(..., description="节点细分种类")

    # Node metadata
    name: str = Field(..., description="节点名称，不可包含空格")
    description: str = Field(..., description="节点的一句话简介")

    # Configuration and parameters
    configurations: Dict[str, Any] = Field(default_factory=dict, description="节点配置参数")

    # New schema-style param definitions (preferred)
    input_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="输入参数定义（同configurations格式，包含type/default/description/required等）",
    )
    output_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="输出参数定义（同configurations格式，包含type/default/description/required等）",
    )

    # Legacy runtime default params (backward compatibility)
    default_input_params: Dict[str, Any] = Field(
        default_factory=dict, description="默认运行时输入参数（兼容旧版）"
    )
    default_output_params: Dict[str, Any] = Field(
        default_factory=dict, description="默认运行时输出参数（兼容旧版）"
    )

    # Port definitions
    input_ports: List[Port] = Field(default_factory=list, description="输入端口列表")
    output_ports: List[Port] = Field(default_factory=list, description="输出端口列表")

    # Attached nodes (只适用于AI_AGENT Node)
    attached_nodes: Optional[List[str]] = Field(
        default=None, description="附加节点ID列表，只适用于AI_AGENT节点调用TOOL和MEMORY节点"
    )

    # Optional metadata
    version: str = Field(default="1.0", description="节点规范版本")
    tags: List[str] = Field(default_factory=list, description="节点标签")

    # Examples and documentation
    examples: Optional[List[Dict[str, Any]]] = Field(default=None, description="使用示例")

    def create_node_instance(
        self,
        node_id: str,
        position: Optional[Dict[str, float]] = None,
        attached_nodes: Optional[List[str]] = None,
    ) -> Node:
        """Create a Node instance based on this specification."""
        # For AI_AGENT nodes, use attached_nodes if provided, otherwise use spec default
        final_attached_nodes = attached_nodes if attached_nodes is not None else self.attached_nodes

        # Derive runtime params from schema definitions if available; otherwise use legacy defaults
        def _derive_defaults_from_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
            try:
                return {
                    key: (spec.get("default") if isinstance(spec, dict) else None)
                    for key, spec in (schema or {}).items()
                }
            except Exception:
                return {}

        runtime_input_defaults = (
            self.default_input_params.copy()
            if self.default_input_params
            else _derive_defaults_from_schema(self.input_params)
        )
        runtime_output_defaults = (
            self.default_output_params.copy()
            if self.default_output_params
            else _derive_defaults_from_schema(self.output_params)
        )
        # Extract default values from configuration schemas
        runtime_configurations = _derive_defaults_from_schema(self.configurations)

        node_data = {
            "id": node_id,
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "subtype": self.subtype,
            "configurations": runtime_configurations,
            "input_params": runtime_input_defaults,
            "output_params": runtime_output_defaults,
            "input_ports": self.input_ports.copy(),
            "output_ports": self.output_ports.copy(),
            "position": position,
        }

        # Only add attached_nodes if it's not None (AI_AGENT specific)
        if final_attached_nodes is not None:
            node_data["attached_nodes"] = final_attached_nodes

        return Node(**node_data)

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate a configuration against this specification."""
        # Basic validation - can be extended by subclasses
        required_keys = set()
        for key, value in self.configurations.items():
            if isinstance(value, dict) and value.get("required", False):
                required_keys.add(key)

        return all(key in config for key in required_keys)


# Common port configurations for reuse
COMMON_PORTS = {
    "main_input": {
        "id": "main",
        "name": "main",
        "data_type": "dict",
        "description": "主输入端口",
        "required": True,
        "max_connections": 1,
    },
    "main_output": {
        "id": "main",
        "name": "main",
        "data_type": "dict",
        "description": "主输出端口",
        "required": False,
        "max_connections": -1,
    },
    "error_output": {
        "id": "error",
        "name": "error",
        "data_type": "dict",
        "description": "错误输出端口",
        "required": False,
        "max_connections": -1,
    },
}


# Common configuration schemas
COMMON_CONFIGS = {
    "timeout": {
        "type": "integer",
        "default": 30,
        "min": 1,
        "max": 300,
        "description": "执行超时时间（秒）",
        "required": False,
    },
    "retry_attempts": {
        "type": "integer",
        "default": 3,
        "min": 0,
        "max": 10,
        "description": "失败重试次数",
        "required": False,
    },
    "enabled": {
        "type": "boolean",
        "default": True,
        "description": "是否启用此节点",
        "required": False,
    },
}
