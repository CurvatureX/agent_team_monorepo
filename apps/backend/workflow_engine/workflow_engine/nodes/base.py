"""
Base classes for node executors.
"""

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
    from shared.node_specs import node_spec_registry
    from shared.node_specs.base import InputPortSpec, NodeSpec, OutputPortSpec
    from workflow_engine.data_mapping.processor import DataMappingProcessor
except ImportError:
    # Fallback for when node specs are not available
    node_spec_registry = None
    NodeSpec = None
    InputPortSpec = None
    OutputPortSpec = None
    DataMappingProcessor = None


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
        """Get node parameter value."""
        return self.node.parameters.get(key, default)

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

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.spec = self._get_node_spec()
        self.data_mapper = DataMappingProcessor() if DataMappingProcessor else None

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

        # Use node spec validation if available
        if self.spec and node_spec_registry:
            try:
                spec_errors = node_spec_registry.validate_node(node)
                errors.extend(spec_errors)
            except Exception as e:
                self.logger.warning(f"Node spec validation failed: {e}")

        # Call legacy validation method for backward compatibility
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
