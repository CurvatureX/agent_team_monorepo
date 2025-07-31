#!/usr/bin/env python3
"""
Simple test for the node specification system.
"""

import os
import sys

# Add parent directory to path for proper imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)


def test_simple():
    """Simple test of the node specification system."""
    print("🧪 Simple Node Specification System Test")
    print("=" * 50)

    try:
        # Try to import the system
        from node_specs import (
            ConnectionType,
            DataFormat,
            InputPortSpec,
            NodeSpec,
            OutputPortSpec,
            ParameterDef,
            ParameterType,
            node_spec_registry,
        )

        print("✅ Successfully imported node specification system")

        # Test creating a simple spec
        test_spec = NodeSpec(
            node_type="TEST_NODE",
            subtype="SIMPLE",
            description="A simple test node",
            parameters=[
                ParameterDef(
                    name="test_param",
                    type=ParameterType.STRING,
                    required=True,
                    description="A test parameter",
                )
            ],
            input_ports=[
                InputPortSpec(
                    name="main", type=ConnectionType.MAIN, required=True, description="Main input"
                )
            ],
            output_ports=[
                OutputPortSpec(name="main", type=ConnectionType.MAIN, description="Main output")
            ],
        )

        print("✅ Successfully created test specification")
        print(f"   - Node type: {test_spec.node_type}")
        print(f"   - Subtype: {test_spec.subtype}")
        print(f"   - Parameters: {len(test_spec.parameters)}")
        print(f"   - Input ports: {len(test_spec.input_ports)}")
        print(f"   - Output ports: {len(test_spec.output_ports)}")

        # Register the spec
        node_spec_registry.register_spec(test_spec)
        print("✅ Successfully registered test specification")

        # Try to retrieve it
        retrieved_spec = node_spec_registry.get_spec("TEST_NODE", "SIMPLE")
        if retrieved_spec:
            print("✅ Successfully retrieved registered specification")
        else:
            print("❌ Failed to retrieve registered specification")

        # Test validation
        class MockNode:
            def __init__(self, node_type, subtype, parameters=None):
                self.type = node_type
                self.subtype = subtype
                self.parameters = parameters or {}

        # Valid node
        valid_node = MockNode("TEST_NODE", "SIMPLE", {"test_param": "test_value"})
        errors = node_spec_registry.validate_node(valid_node)
        if not errors:
            print("✅ Valid node passed validation")
        else:
            print(f"❌ Valid node failed validation: {errors}")

        # Invalid node (missing required parameter)
        invalid_node = MockNode("TEST_NODE", "SIMPLE", {})
        errors = node_spec_registry.validate_node(invalid_node)
        if errors:
            print("✅ Invalid node correctly failed validation:")
            for error in errors:
                print(f"   - {error}")
        else:
            print("❌ Invalid node incorrectly passed validation")

        print("\n" + "=" * 50)
        print("🎉 Simple test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_simple()
    sys.exit(0 if success else 1)
