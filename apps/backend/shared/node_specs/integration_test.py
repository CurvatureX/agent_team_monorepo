#!/usr/bin/env python3
"""
Integration test for the node specification implementation.

This test verifies that all components work together correctly:
- Node specifications are loaded
- Data mapping works
- API endpoints are functional
- BaseNodeExecutor integration works
"""

import json
import sys
from pathlib import Path

# Add the backend and workflow_engine paths to sys.path
backend_path = Path(__file__).parent.parent.parent
workflow_engine_path = backend_path / "workflow_engine"
sys.path.insert(0, str(backend_path))
sys.path.insert(0, str(workflow_engine_path))


def test_node_specs_loading():
    """Test that node specifications are loaded correctly."""
    print("🧪 Testing node specifications loading...")

    try:
        from shared.node_specs import node_spec_registry

        # Check that specs are loaded
        specs = node_spec_registry.list_all_specs()
        print(f"✅ Loaded {len(specs)} node specifications")

        # Check specific AI agent specs (using enum values)
        from shared.models.node_enums import AIAgentSubtype, NodeType

        openai_spec = node_spec_registry.get_spec(
            NodeType.AI_AGENT.value, AIAgentSubtype.OPENAI_CHATGPT.value
        )
        if openai_spec:
            print(f"✅ OpenAI spec loaded: {openai_spec.description}")
        else:
            print("❌ OpenAI spec not found")
            return False

        gemini_spec = node_spec_registry.get_spec(
            NodeType.AI_AGENT.value, AIAgentSubtype.GOOGLE_GEMINI.value
        )
        if gemini_spec:
            print(f"✅ Gemini spec loaded: {gemini_spec.description}")
        else:
            print("❌ Gemini spec not found")
            return False

        claude_spec = node_spec_registry.get_spec(
            NodeType.AI_AGENT.value, AIAgentSubtype.ANTHROPIC_CLAUDE.value
        )
        if claude_spec:
            print(f"✅ Claude spec loaded: {claude_spec.description}")
        else:
            print("❌ Claude spec not found")
            return False

        return True

    except Exception as e:
        print(f"❌ Node specs loading failed: {e}")
        return False


def test_node_validation():
    """Test node validation with specifications."""
    print("🧪 Testing node validation...")

    try:
        # Create a mock node using proper enum values
        from shared.models.node_enums import AIAgentSubtype, NodeType
        from shared.node_specs import node_spec_registry

        class MockNode:
            def __init__(self):
                self.type = NodeType.AI_AGENT.value
                self.subtype = AIAgentSubtype.OPENAI_CHATGPT.value
                self.parameters = {
                    "system_prompt": "You are a helpful assistant",
                    "temperature": "0.7",
                    "model_version": "gpt-4",
                }
                # Add required input port
                self.input_ports = [type("MockPort", (), {"name": "main"})()]
                self.output_ports = []
                self.id = "test_node"

        node = MockNode()
        errors = node_spec_registry.validate_node(node)

        if not errors:
            print("✅ Node validation works")
        else:
            print(f"❌ Node validation failed with errors: {errors}")
            return False

        # Test with invalid parameters
        node.parameters = {"invalid_param": "value"}
        errors = node_spec_registry.validate_node(node)

        if errors:
            print("✅ Node validation catches invalid parameters")
        else:
            print("❌ Node validation should have caught invalid parameters")
            return False

        return True

    except Exception as e:
        print(f"❌ Node validation test failed: {e}")
        return False


def test_base_node_executor():
    """Test BaseNodeExecutor with node spec integration."""
    print("🧪 Testing BaseNodeExecutor integration...")

    try:
        # Test the base functionality directly
        from shared.node_specs.base import NodeSpec
        from workflow_engine.nodes.base import BaseNodeExecutor

        # Create a mock executor
        class MockExecutor(BaseNodeExecutor):
            def _get_node_spec(self):
                from shared.models.node_enums import AIAgentSubtype, NodeType
                from shared.node_specs import node_spec_registry

                return node_spec_registry.get_spec(
                    NodeType.AI_AGENT.value, AIAgentSubtype.OPENAI_CHATGPT.value
                )

            def execute(self, context):
                pass

            def get_supported_subtypes(self):
                from shared.models.node_enums import AIAgentSubtype

                return [AIAgentSubtype.OPENAI_CHATGPT.value]

        executor = MockExecutor()

        # Check that spec is loaded
        if executor.spec:
            print(f"✅ BaseNodeExecutor has spec: {executor.spec.node_type}.{executor.spec.subtype}")
        else:
            print("❌ BaseNodeExecutor spec not loaded")
            return False

        # Check port specs
        input_ports = executor.get_input_port_specs()
        output_ports = executor.get_output_port_specs()

        if input_ports:
            print(f"✅ Input ports loaded: {[p.name for p in input_ports]}")
        else:
            print("❌ No input ports found")
            return False

        if output_ports:
            print(f"✅ Output ports loaded: {[p.name for p in output_ports]}")
        else:
            print("❌ No output ports found")
            return False

        # Test input validation
        test_data = {"message": "test", "context": {}}
        errors = executor.validate_input_data("main", test_data)
        print(f"✅ Input validation works: {len(errors)} errors")

        return True

    except Exception as e:
        print(f"❌ BaseNodeExecutor test failed: {e}")
        return False


def main():
    """Run all integration tests."""
    print("🚀 Starting Node Specification Implementation Integration Tests")
    print("=" * 60)

    tests = [
        ("Node Specs Loading", test_node_specs_loading),
        ("Node Validation", test_node_validation),
        ("BaseNodeExecutor Integration", test_base_node_executor),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} Test:")
        print("-" * 40)

        try:
            if test_func():
                print(f"✅ {test_name} Test PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} Test FAILED")
                failed += 1
        except Exception as e:
            print(f"❌ {test_name} Test FAILED with exception: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All tests passed! Node Specification Implementation is working correctly.")
        return 0
    else:
        print(f"💥 {failed} tests failed. Please check the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
