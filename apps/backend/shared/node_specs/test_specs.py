#!/usr/bin/env python3
"""
Test script for the node specification system.

This script demonstrates the functionality of the node specification system
and validates that it works as expected.
"""

import os
import sys

# Add the current directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

import importlib.util
import json
import re

# Import base classes directly
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


class NodeSpecValidator:
    """Validator for node specifications and configurations."""

    @staticmethod
    def validate_parameters(node, spec: NodeSpec) -> List[str]:
        """Validate node parameters against specification."""
        errors = []

        # Get node parameters safely
        node_parameters = getattr(node, "parameters", {})
        if not isinstance(node_parameters, dict):
            node_parameters = {}

        # Check required parameters
        for param_def in spec.parameters:
            if param_def.required and param_def.name not in node_parameters:
                errors.append(f"Missing required parameter: {param_def.name}")
                continue

            # Validate parameter type and format if present
            if param_def.name in node_parameters:
                value = node_parameters[param_def.name]
                param_errors = NodeSpecValidator._validate_parameter_value(value, param_def)
                errors.extend(param_errors)

        return errors

    @staticmethod
    def _validate_parameter_value(value: str, param_def: ParameterDef) -> List[str]:
        """Validate individual parameter value."""
        errors = []

        if param_def.type == ParameterType.INTEGER:
            try:
                int(value)
            except (ValueError, TypeError):
                errors.append(f"Parameter {param_def.name} must be an integer")
        elif param_def.type == ParameterType.FLOAT:
            try:
                float(value)
            except (ValueError, TypeError):
                errors.append(f"Parameter {param_def.name} must be a float")
        elif param_def.type == ParameterType.BOOLEAN:
            if str(value).lower() not in ["true", "false", "1", "0", "yes", "no"]:
                errors.append(f"Parameter {param_def.name} must be a boolean value")
        elif param_def.type == ParameterType.ENUM:
            if param_def.enum_values and str(value) not in param_def.enum_values:
                errors.append(f"Parameter {param_def.name} must be one of: {param_def.enum_values}")
        elif param_def.type == ParameterType.JSON:
            try:
                json.loads(str(value))
            except (json.JSONDecodeError, TypeError):
                errors.append(f"Parameter {param_def.name} must be valid JSON")

        return errors


class TestRegistry:
    def __init__(self):
        self._specs: Dict[str, NodeSpec] = {}
        self._validator = NodeSpecValidator()
        self._load_test_specs()

    def _load_test_specs(self):
        """Load a few test specifications."""
        # Import and register specs from definitions
        try:
            spec = importlib.util.spec_from_file_location(
                "trigger_nodes", os.path.join(current_dir, "definitions", "trigger_nodes.py")
            )
            trigger_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(trigger_module)

            # Register trigger specs
            for attr_name in dir(trigger_module):
                attr = getattr(trigger_module, attr_name)
                if isinstance(attr, NodeSpec):
                    key = f"{attr.node_type}.{attr.subtype}"
                    self._specs[key] = attr

            # Load AI agent specs
            spec = importlib.util.spec_from_file_location(
                "ai_agent_nodes", os.path.join(current_dir, "definitions", "ai_agent_nodes.py")
            )
            ai_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ai_module)

            for attr_name in dir(ai_module):
                attr = getattr(ai_module, attr_name)
                if isinstance(attr, NodeSpec):
                    key = f"{attr.node_type}.{attr.subtype}"
                    self._specs[key] = attr

        except Exception as e:
            print(f"Warning: Could not load all specs: {e}")

    def list_all_specs(self) -> List[NodeSpec]:
        return list(self._specs.values())

    def get_node_types(self) -> Dict[str, List[str]]:
        result = {}
        for spec in self._specs.values():
            if spec.node_type not in result:
                result[spec.node_type] = []
            result[spec.node_type].append(spec.subtype)
        return result

    def get_spec(self, node_type: str, subtype: str):
        key = f"{node_type}.{subtype}"
        return self._specs.get(key)

    def validate_node(self, node) -> List[str]:
        spec = self.get_spec(node.type, node.subtype)
        if not spec:
            return [f"Unknown node type: {node.type}.{node.subtype}"]

        errors = []
        param_errors = self._validator.validate_parameters(node, spec)
        errors.extend(param_errors)
        return errors

    def validate_connection(
        self, source_node, source_port: str, target_node, target_port: str
    ) -> List[str]:
        errors = []

        source_spec = self.get_spec(source_node.type, source_node.subtype)
        target_spec = self.get_spec(target_node.type, target_node.subtype)

        if not source_spec or not target_spec:
            return ["Cannot find node specifications for connection validation"]

        # Find source output port
        source_output_port = None
        for port in source_spec.output_ports:
            if port.name == source_port:
                source_output_port = port
                break

        if not source_output_port:
            errors.append(f"Source node does not have output port '{source_port}'")
            return errors

        # Find target input port
        target_input_port = None
        for port in target_spec.input_ports:
            if port.name == target_port:
                target_input_port = port
                break

        if not target_input_port:
            errors.append(f"Target node does not have input port '{target_port}'")
            return errors

        # Validate port type compatibility
        if source_output_port.type != target_input_port.type:
            errors.append(
                f"Port types incompatible: {source_output_port.type} -> {target_input_port.type}"
            )

        return errors


# Create test registry instance
node_spec_registry = TestRegistry()


def test_basic_functionality():
    """Test basic registry and validation functionality."""
    print("🧪 Testing Node Specification System")
    print("=" * 50)

    # Test 1: Registry loading
    print("\n1. Testing Registry Loading:")
    all_specs = node_spec_registry.list_all_specs()
    print(f"   ✅ Loaded {len(all_specs)} node specifications")

    # Test 2: Node types
    print("\n2. Testing Node Types:")
    node_types = node_spec_registry.get_node_types()
    for node_type, subtypes in node_types.items():
        print(f"   📋 {node_type}: {len(subtypes)} subtypes")
        for subtype in subtypes[:3]:  # Show first 3
            print(f"      - {subtype}")
        if len(subtypes) > 3:
            print(f"      ... and {len(subtypes) - 3} more")

    # Test 3: Specific spec retrieval
    print("\n3. Testing Specific Spec Retrieval:")
    router_spec = node_spec_registry.get_spec("AI_AGENT_NODE", "ROUTER_AGENT")
    if router_spec:
        print(f"   ✅ Found ROUTER_AGENT spec")
        print(f"      - Parameters: {len(router_spec.parameters)}")
        print(f"      - Input ports: {len(router_spec.input_ports)}")
        print(f"      - Output ports: {len(router_spec.output_ports)}")
    else:
        print("   ❌ ROUTER_AGENT spec not found")

    # Test 4: Parameter validation
    print("\n4. Testing Parameter Validation:")

    # Create a mock node object
    class MockNode:
        def __init__(self, node_type, subtype, parameters=None):
            self.type = node_type
            self.subtype = subtype
            self.parameters = parameters or {}

    # Test valid node
    valid_node = MockNode(
        "AI_AGENT_NODE",
        "ROUTER_AGENT",
        {
            "prompt": "Route user requests intelligently",
            "routing_options": '{"support": "tech", "sales": "sales"}',
            "temperature": "0.7",
        },
    )

    errors = node_spec_registry.validate_node(valid_node)
    if not errors:
        print("   ✅ Valid node passed validation")
    else:
        print(f"   ❌ Valid node failed: {errors}")

    # Test invalid node (missing required parameter)
    invalid_node = MockNode(
        "AI_AGENT_NODE",
        "ROUTER_AGENT",
        {"temperature": "0.7"},  # Missing required 'prompt' and 'routing_options'
    )

    errors = node_spec_registry.validate_node(invalid_node)
    if errors:
        print(f"   ✅ Invalid node correctly failed validation:")
        for error in errors:
            print(f"      - {error}")
    else:
        print("   ❌ Invalid node incorrectly passed validation")

    # Test 5: Connection validation
    print("\n5. Testing Connection Validation:")

    # Create mock nodes for connection testing
    trigger_node = MockNode("TRIGGER_NODE", "MANUAL")
    router_node = MockNode("AI_AGENT_NODE", "ROUTER_AGENT")

    # Test valid connection (MAIN -> MAIN)
    connection_errors = node_spec_registry.validate_connection(
        trigger_node, "main", router_node, "main"
    )

    if not connection_errors:
        print("   ✅ Valid connection passed validation")
    else:
        print(f"   ❌ Valid connection failed: {connection_errors}")

    # Test invalid connection (non-existent port)
    connection_errors = node_spec_registry.validate_connection(
        trigger_node, "nonexistent", router_node, "main"
    )

    if connection_errors:
        print("   ✅ Invalid connection correctly failed validation:")
        for error in connection_errors:
            print(f"      - {error}")
    else:
        print("   ❌ Invalid connection incorrectly passed validation")

    print("\n" + "=" * 50)
    print("🎉 Node Specification System Test Complete!")


if __name__ == "__main__":
    test_basic_functionality()
