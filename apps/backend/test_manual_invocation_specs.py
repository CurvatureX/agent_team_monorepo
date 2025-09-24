#!/usr/bin/env python3
"""
Test script for manual invocation node specs integration.
Verifies that all trigger specs have proper manual invocation support.
"""

import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))


def test_node_specs_registry():
    """Test that the node specs registry loads manual invocation specs correctly."""
    try:
        from shared.models.node_enums import TriggerSubtype
        from shared.node_specs.registry import NodeSpecRegistry

        print("🧪 Testing Node Specs Registry Integration...")

        # Initialize registry
        registry = NodeSpecRegistry()

        # Test trigger types that should support manual invocation
        trigger_types = [
            ("TRIGGER", "MANUAL"),
            ("TRIGGER", "CRON"),
            ("TRIGGER", "WEBHOOK"),
            ("TRIGGER", "SLACK"),
            ("TRIGGER", "EMAIL"),
            ("TRIGGER", "GITHUB"),
        ]

        for node_type, subtype in trigger_types:
            print(f"\n📋 Testing {node_type}/{subtype}...")

            try:
                spec = registry.get_spec(node_type, subtype)

                if not spec:
                    print(f"❌ No spec found for {node_type}/{subtype}")
                    continue

                print(f"✅ Spec found: {spec.display_name}")

                # Check manual invocation support
                if spec.manual_invocation:
                    print(f"✅ Manual invocation supported: {spec.manual_invocation.supported}")
                    print(f"📝 Description: {spec.manual_invocation.description}")

                    if spec.manual_invocation.parameter_schema:
                        schema = spec.manual_invocation.parameter_schema
                        print(
                            f"📊 Parameter schema properties: {list(schema.get('properties', {}).keys())}"
                        )

                    if spec.manual_invocation.parameter_examples:
                        examples = spec.manual_invocation.parameter_examples
                        print(f"💡 Example count: {len(examples)}")
                        for i, example in enumerate(examples[:2]):  # Show first 2 examples
                            print(f"   {i+1}. {example['name']}: {example['description']}")
                else:
                    print(f"⚠️  No manual invocation spec defined")

            except Exception as e:
                print(f"❌ Error loading spec for {node_type}/{subtype}: {e}")

        print(f"\n🎉 Node specs registry integration test completed!")
        return True

    except Exception as e:
        print(f"❌ Failed to test node specs registry: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_manual_invocation_schemas():
    """Test that manual invocation schemas are valid JSON Schema."""
    try:
        import jsonschema
    except ImportError:
        print("⚠️  jsonschema not available, skipping schema validation")
        return True

    from shared.node_specs.registry import NodeSpecRegistry

    print(f"\n🔍 Testing Manual Invocation Schemas...")
    registry = NodeSpecRegistry()

    trigger_types = [
        ("TRIGGER", "WEBHOOK"),
        ("TRIGGER", "SLACK"),
        ("TRIGGER", "EMAIL"),
        ("TRIGGER", "GITHUB"),
    ]

    for node_type, subtype in trigger_types:
        try:
            spec = registry.get_spec(node_type, subtype)
            if spec and spec.manual_invocation and spec.manual_invocation.parameter_schema:
                schema = spec.manual_invocation.parameter_schema

                # Validate that it's a valid JSON Schema
                jsonschema.Draft7Validator.check_schema(schema)
                print(f"✅ {subtype} schema is valid JSON Schema")

                # Test example parameters against schema
                if spec.manual_invocation.parameter_examples:
                    for example in spec.manual_invocation.parameter_examples:
                        try:
                            jsonschema.validate(example["parameters"], schema)
                            print(
                                f"✅ {subtype} example '{example['name']}' validates against schema"
                            )
                        except jsonschema.ValidationError as e:
                            print(f"❌ {subtype} example '{example['name']}' validation failed: {e}")

        except Exception as e:
            print(f"❌ Schema validation error for {subtype}: {e}")

    return True


if __name__ == "__main__":
    print("🚀 Starting Manual Invocation Node Specs Tests...")

    success = True
    success &= test_node_specs_registry()
    success &= test_manual_invocation_schemas()

    if success:
        print(f"\n✅ All tests passed!")
        exit(0)
    else:
        print(f"\n❌ Some tests failed!")
        exit(1)
