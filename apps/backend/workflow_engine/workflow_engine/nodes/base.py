"""
Base classes for node executors.
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

try:
    from proto import workflow_pb2
except ImportError:
    # Fallback for when proto files are not generated
    workflow_pb2 = None

try:
    from ..utils.template_resolver import TemplateResolver
except ImportError:
    # Fallback if template resolver not available
    TemplateResolver = None

try:
    from shared.node_specs import node_spec_registry
    from shared.node_specs.base import InputPortSpec, NodeSpec, OutputPortSpec, ParameterType
except ImportError:
    # Fallback for when node specs are not available
    node_spec_registry = None
    NodeSpec = None
    InputPortSpec = None
    OutputPortSpec = None
    ParameterType = None


class ExecutionStatus(Enum):
    """Execution status for nodes."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


@dataclass
class NodeExecutionContext:
    """Context for node execution."""

    node: Any  # workflow_pb2.Node when available
    workflow_id: str
    execution_id: str
    input_data: Dict[str, Any]
    static_data: Dict[str, Any]
    credentials: Dict[str, Any]
    metadata: Dict[str, Any]

    def get_parameter(self, key: str, default: Any = None) -> Any:
        """Get node parameter value with template resolution support."""
        # Handle case where parameters might be a string (JSON)
        if isinstance(self.node.parameters, str):
            import json

            try:
                parameters = json.loads(self.node.parameters)
            except:
                return default
        else:
            parameters = self.node.parameters

        if hasattr(parameters, "get"):
            value = parameters.get(key, default)
            
            # Resolve template variables if TemplateResolver is available
            if TemplateResolver and value is not None:
                # Build resolution context
                context = {
                    "payload": self.input_data.get("payload", {}),
                    "trigger": self.input_data,
                    "static": self.static_data,
                    "workflow": {"id": self.workflow_id},
                    "execution": {"id": self.execution_id},
                    "metadata": self.metadata,
                    "data": self.input_data,  # Alias for input data
                }
                
                # Resolve the value
                resolved_value = TemplateResolver.resolve_value(value, context)
                return resolved_value if resolved_value is not None else default
            
            return value
        else:
            return default
    
    def get_resolved_parameters(self) -> Dict[str, Any]:
        """Get all parameters with template variables resolved."""
        # Handle case where parameters might be a string (JSON)
        if isinstance(self.node.parameters, str):
            import json

            try:
                parameters = json.loads(self.node.parameters)
            except:
                return {}
        else:
            parameters = self.node.parameters if hasattr(self.node.parameters, "items") else {}

        if not TemplateResolver:
            return dict(parameters) if hasattr(parameters, "items") else {}
        
        # Build resolution context
        context = {
            "payload": self.input_data.get("payload", {}),
            "trigger": self.input_data,
            "static": self.static_data,
            "workflow": {"id": self.workflow_id},
            "execution": {"id": self.execution_id},
            "metadata": self.metadata,
            "data": self.input_data,  # Alias for input data
        }
        
        # Resolve all parameters
        return TemplateResolver.resolve_parameters(dict(parameters), context)

    def get_credential(self, key: str, default: Any = None) -> Any:
        """Get credential value."""
        return self.credentials.get(key, default)


@dataclass
class NodeExecutionResult:
    """Result of node execution."""

    status: ExecutionStatus
    output_data: Dict[str, Any]
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    execution_time: Optional[float] = None
    logs: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.logs is None:
            self.logs = []
        if self.metadata is None:
            self.metadata = {}


class BaseNodeExecutor(ABC):
    """Base class for all node executors."""

    def __init__(self, subtype: Optional[str] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._subtype = subtype  # Set subtype first
        self.spec = self._get_node_spec()  # Now _subtype is available

    def _get_node_spec(self) -> Optional[NodeSpec]:
        """Get the node specification for this executor.

        Override this method in subclasses to return the specific NodeSpec.
        """
        return None

    @abstractmethod
    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute the node with given context."""
        pass

    def validate(self, node: Any) -> List[str]:  # workflow_pb2.Node when available
        """Validate node configuration using node specifications."""
        errors = []

        print(f"🐛 DEBUG: BaseNodeExecutor.validate() called")
        print(f"🐛 DEBUG: Executor self._subtype BEFORE: {getattr(self, '_subtype', 'NOT_SET')}")
        print(f"🐛 DEBUG: Node.subtype: {getattr(node, 'subtype', 'NO_SUBTYPE')}")

        # Store subtype for dynamic spec retrieval
        if hasattr(node, "subtype"):
            self._subtype = node.subtype
            print(f"🐛 DEBUG: Set self._subtype TO: {self._subtype}")
            # Get the specific spec for this subtype
            if node_spec_registry and hasattr(node, "type"):
                self.spec = node_spec_registry.get_spec(node.type, node.subtype)

        # Use node spec validation if available
        if node_spec_registry:
            try:
                print(
                    f"🐛 DEBUG: About to call validate_node with node.subtype = {getattr(node, 'subtype', 'NO_SUBTYPE')}"
                )
                spec_errors = node_spec_registry.validate_node(node)
                errors.extend(spec_errors)
            except Exception as e:
                self.logger.warning(f"Node spec validation failed: {e}")
                # Fall back to legacy validation
                legacy_errors = self._validate_legacy(node)
                errors.extend(legacy_errors)
        else:
            # If spec registry not available, use legacy validation
            legacy_errors = self._validate_legacy(node)
            errors.extend(legacy_errors)

        return errors

    def _validate_legacy(self, node: Any) -> List[str]:
        """Legacy validation method. Override in subclasses for custom validation."""
        return []

    @abstractmethod
    def get_supported_subtypes(self) -> List[str]:
        """Get list of supported node subtypes."""
        pass

    def can_execute(self, node: Any) -> bool:  # workflow_pb2.Node when available
        """Check if this executor can handle the given node."""
        return node.subtype in self.get_supported_subtypes()

    def get_input_port_specs(self) -> List[InputPortSpec]:
        """Get input port specifications for this node type."""
        if self.spec and InputPortSpec:
            return self.spec.input_ports
        return []

    def get_output_port_specs(self) -> List[OutputPortSpec]:
        """Get output port specifications for this node type."""
        if self.spec and OutputPortSpec:
            return self.spec.output_ports
        return []

    def validate_input_data(self, port_name: str, data: Dict[str, Any]) -> List[str]:
        """Validate input port data against specification."""
        if not self.spec:
            return []

        # Find the port specification
        port_spec = None
        for port in self.spec.input_ports:
            if port.name == port_name:
                port_spec = port
                break

        if not port_spec:
            return [f"Unknown input port: {port_name}"]

        # Validate data format if spec is available
        try:
            from shared.node_specs.validator import NodeSpecValidator

            return NodeSpecValidator.validate_port_data(port_spec, data)
        except ImportError:
            return []

    def validate_output_data(self, port_name: str, data: Dict[str, Any]) -> List[str]:
        """Validate output port data against specification."""
        if not self.spec:
            return []

        # Find the port specification
        port_spec = None
        for port in self.spec.output_ports:
            if port.name == port_name:
                port_spec = port
                break

        if not port_spec:
            return [f"Unknown output port: {port_name}"]

        # Validate data format if spec is available
        try:
            from shared.node_specs.validator import NodeSpecValidator

            return NodeSpecValidator.validate_port_data(port_spec, data)
        except ImportError:
            return []

    def prepare_execution(self, context: NodeExecutionContext) -> None:
        """Prepare for execution (optional override)."""
        pass

    def cleanup_execution(self, context: NodeExecutionContext) -> None:
        """Cleanup after execution (optional override)."""
        pass

    def _create_success_result(
        self,
        output_data: Dict[str, Any],
        execution_time: Optional[float] = None,
        logs: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> NodeExecutionResult:
        """Helper to create success result."""
        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data=output_data,
            execution_time=execution_time,
            logs=logs or [],
            metadata=metadata or {},
        )

    def _create_error_result(
        self,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None,
        execution_time: Optional[float] = None,
        logs: Optional[List[str]] = None,
    ) -> NodeExecutionResult:
        """Helper to create error result."""
        return NodeExecutionResult(
            status=ExecutionStatus.ERROR,
            output_data={},
            error_message=error_message,
            error_details=error_details or {},
            execution_time=execution_time,
            logs=logs or [],
        )

    def _validate_required_parameters(self, node: Any, required_params: List[str]) -> List[str]:
        """Validate required parameters exist."""
        errors = []
        for param in required_params:
            if param not in node.parameters or not node.parameters[param]:
                errors.append(f"Missing required parameter: {param}")
        return errors

    def _validate_required_credentials(
        self, context: NodeExecutionContext, required_creds: List[str]
    ) -> List[str]:
        """Validate required credentials exist."""
        errors = []
        for cred in required_creds:
            if cred not in context.credentials or not context.credentials[cred]:
                errors.append(f"Missing required credential: {cred}")
        return errors

    def get_parameter_with_spec(self, context: NodeExecutionContext, param_name: str) -> Any:
        """Get parameter value with type conversion based on spec."""
        raw_value = context.get_parameter(param_name)

        if self.spec:
            param_def = self.spec.get_parameter(param_name)
            if param_def:
                # Use default value if not provided
                if raw_value is None and param_def.default_value is not None:
                    raw_value = param_def.default_value

                # Type conversion based on spec
                if raw_value is not None and hasattr(param_def, "type"):
                    try:
                        if param_def.type == ParameterType.INTEGER:
                            return int(raw_value)
                        elif param_def.type == ParameterType.FLOAT:
                            return float(raw_value)
                        elif param_def.type == ParameterType.BOOLEAN:
                            if isinstance(raw_value, str):
                                return raw_value.lower() in ("true", "1", "yes")
                            return bool(raw_value)
                        elif param_def.type == ParameterType.JSON:
                            if isinstance(raw_value, str):
                                return json.loads(raw_value)
                            return raw_value
                    except (ValueError, json.JSONDecodeError) as e:
                        self.logger.warning(f"Failed to convert parameter {param_name}: {e}")
                        return raw_value

        return raw_value

    def validate_parameters_with_spec(self, node: Any) -> List[str]:
        """Validate parameters using node specification."""
        if not self.spec or not node_spec_registry:
            return []

        return node_spec_registry.validate_parameters(node, self.spec)
