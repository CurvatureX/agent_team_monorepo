"""
Node specification registry system.

This module provides the central registry for all node specifications,
including validation, lookup, and compatibility checking functionality.
"""

import importlib
import pkgutil
from typing import Any, Dict, List, Optional, Union

from .base import InputPortSpec, NodeSpec, OutputPortSpec
from .validator import NodeSpecValidator


class NodeSpecRegistry:
    """Central registry for all node specifications."""

    def __init__(self):
        self._specs: Dict[str, NodeSpec] = {}
        self._port_compatibility_cache: Dict[str, bool] = {}
        self._validator = NodeSpecValidator()
        self._load_all_specs()

    def _load_all_specs(self):
        """Load all node specifications from the definitions package."""
        loaded_count = 0
        error_count = 0

        try:
            # Import all modules in the definitions package
            from . import definitions

            # Walk through all modules in definitions package
            for importer, modname, ispkg in pkgutil.iter_modules(
                definitions.__path__, definitions.__name__ + "."
            ):
                if ispkg:  # Skip subpackages
                    continue

                try:
                    module = importlib.import_module(modname)
                    module_specs = self._load_specs_from_module(module)
                    loaded_count += module_specs
                except ImportError as e:
                    error_count += 1
                    print(f"Warning: Could not import {modname}: {e}")
                    continue
                except Exception as e:
                    error_count += 1
                    print(f"Error loading specs from {modname}: {e}")
                    continue

        except ImportError:
            # definitions package doesn't exist yet, continue without error
            print("Warning: definitions package not found, no specifications loaded")

        if loaded_count > 0:
            print(
                f"✅ Loaded {loaded_count} node specifications from {len(self._specs)} total specs"
            )
        if error_count > 0:
            print(f"⚠️  {error_count} modules had loading errors")

    def _load_specs_from_module(self, module):
        """Load specifications from a single module."""
        loaded_specs = 0
        for attr_name in dir(module):
            if attr_name.startswith("_"):  # Skip private attributes
                continue

            attr = getattr(module, attr_name)
            if isinstance(attr, NodeSpec):
                try:
                    self.register_spec(attr)
                    loaded_specs += 1
                except Exception as e:
                    print(f"Error registering spec {attr_name}: {e}")

        return loaded_specs

    def register_spec(self, spec: NodeSpec):
        """Register a node specification."""
        if not isinstance(spec, NodeSpec):
            raise ValueError(f"Expected NodeSpec, got {type(spec)}")

        if not spec.node_type or not spec.subtype:
            raise ValueError(f"NodeSpec must have node_type and subtype: {spec}")

        key = f"{spec.node_type}.{spec.subtype}"

        # Check for duplicates
        if key in self._specs:
            print(f"Warning: Overwriting existing spec for {key}")

        self._specs[key] = spec

    def get_spec(self, node_type: str, subtype: str) -> Optional[NodeSpec]:
        """Get a node specification by type and subtype."""
        # Try the direct key first (for backward compatibility)
        key = f"{node_type}.{subtype}"
        spec = self._specs.get(key)
        if spec:
            return spec

        # Try with NodeType prefix (for specs registered with enum node types)
        nodetype_key = f"NodeType.{node_type}.{subtype}"
        spec = self._specs.get(nodetype_key)
        if spec:
            return spec

        # Try with NodeType/Subtype prefixes (for new enum format)
        enum_key = f"NodeType.{node_type}.{self._get_subtype_enum_key(node_type, subtype)}"
        return self._specs.get(enum_key)

    def _get_subtype_enum_key(self, node_type: str, subtype: str) -> str:
        """Convert subtype string to its enum representation."""
        # Import enum classes to convert string to enum format
        try:
            from ..models.node_enums import (
                ActionSubtype,
                AIAgentSubtype,
                ExternalActionSubtype,
                FlowSubtype,
                HumanLoopSubtype,
                MemorySubtype,
                ToolSubtype,
                TriggerSubtype,
            )

            # Map node types to their subtype enums
            subtype_enum_map = {
                "ACTION": ActionSubtype,
                "AI_AGENT": AIAgentSubtype,
                "FLOW": FlowSubtype,
                "TRIGGER": TriggerSubtype,
                "MEMORY": MemorySubtype,
                "HUMAN_IN_THE_LOOP": HumanLoopSubtype,
                "TOOL": ToolSubtype,
                "EXTERNAL_ACTION": ExternalActionSubtype,
            }

            enum_class = subtype_enum_map.get(node_type)
            if enum_class:
                # Try to find the enum value that matches the subtype
                for enum_value in enum_class:
                    if enum_value.value == subtype:
                        return str(enum_value)

            # If no enum match found, return the subtype as-is
            return subtype

        except ImportError:
            # If enums not available, return the subtype as-is
            return subtype

    def get_specs_by_type(self, node_type: str) -> List[NodeSpec]:
        """Get all specifications for a given node type."""
        return [spec for spec in self._specs.values() if spec.node_type == node_type]

    def list_all_specs(self) -> List[NodeSpec]:
        """Get all registered specifications."""
        return list(self._specs.values())

    def get_node_types(self) -> Dict[str, List[str]]:
        """Get all node types and their subtypes."""
        result = {}
        for spec in self._specs.values():
            if spec.node_type not in result:
                result[spec.node_type] = []
            result[spec.node_type].append(spec.subtype)
        return result

    def validate_node(self, node) -> List[str]:
        """Validate a node against its specification."""
        # Debug logging to trace the exact node being validated
        import traceback

        print(f"🐛 DEBUG: Validating node with type='{node.type}', subtype='{node.subtype}'")
        print(f"🐛 DEBUG: Node has id: {getattr(node, 'id', 'NO_ID')}")
        print(f"🐛 DEBUG: Node has name: {getattr(node, 'name', 'NO_NAME')}")
        print(f"🐛 DEBUG: Call stack:")
        for line in traceback.format_stack()[-3:]:  # Show last 3 stack frames
            print(f"🐛 DEBUG: {line.strip()}")

        spec = self.get_spec(node.type, node.subtype)
        if not spec:
            print(f"🐛 DEBUG: No spec found for {node.type}.{node.subtype}")
            return [f"Unknown node type: {node.type}.{node.subtype}"]

        print(f"🐛 DEBUG: Found spec for {node.type}.{node.subtype}")
        return self._validate_against_spec(node, spec)

    def _validate_against_spec(self, node, spec: NodeSpec) -> List[str]:
        """Validate node against specification."""
        errors = []

        # Validate parameters
        param_errors = self._validator.validate_parameters(node, spec)
        errors.extend(param_errors)

        # Validate ports
        port_errors = self._validator.validate_ports(node, spec)
        errors.extend(port_errors)

        return errors

    def validate_connection(
        self, source_node, source_port: str, target_node, target_port: str
    ) -> List[str]:
        """Validate connection compatibility between two ports."""
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
            errors.append(
                f"Source node {getattr(source_node, 'id', 'unknown')} does not have output port '{source_port}'"
            )
            return errors

        # Find target input port
        target_input_port = None
        for port in target_spec.input_ports:
            if port.name == target_port:
                target_input_port = port
                break

        if not target_input_port:
            errors.append(
                f"Target node {getattr(target_node, 'id', 'unknown')} does not have input port '{target_port}'"
            )
            return errors

        # Validate port type compatibility
        if source_output_port.type != target_input_port.type:
            errors.append(
                f"Port types incompatible: {source_output_port.type} -> {target_input_port.type}"
            )

        return errors

    def get_port_spec(
        self, node_type: str, subtype: str, port_name: str, port_direction: str
    ) -> Optional[Union[InputPortSpec, OutputPortSpec]]:
        """Get specification for a specific port."""
        spec = self.get_spec(node_type, subtype)
        if not spec:
            return None

        ports = spec.input_ports if port_direction == "input" else spec.output_ports
        for port in ports:
            if port.name == port_name:
                return port

        return None

    def get_compatible_ports(
        self, node_type: str, subtype: str, port_name: str, port_direction: str
    ) -> List[tuple]:
        """Get all ports that are compatible with the given port."""
        port_spec = self.get_port_spec(node_type, subtype, port_name, port_direction)
        if not port_spec:
            return []

        compatible_ports = []
        opposite_direction = "input" if port_direction == "output" else "output"

        for spec in self._specs.values():
            opposite_ports = (
                spec.input_ports if opposite_direction == "input" else spec.output_ports
            )
            for other_port in opposite_ports:
                if other_port.type == port_spec.type:
                    compatible_ports.append((spec.node_type, spec.subtype, other_port.name))

        return compatible_ports

    def clear_cache(self):
        """Clear the compatibility cache."""
        self._port_compatibility_cache.clear()

    def reload_specs(self):
        """Reload all specifications from definitions."""
        self._specs.clear()
        self.clear_cache()
        self._load_all_specs()


# Global singleton instance
node_spec_registry = NodeSpecRegistry()
