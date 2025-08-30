#!/usr/bin/env python3
"""
Comprehensive test for the revamped Node Specification System.

This test demonstrates the new provider-based AI agents and validates
all core functionality of the system.
"""

import os
import sys

# Add parent directory to path for proper imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from shared.models.node_enums import AnthropicModel, GoogleGeminiModel, OpenAIModel


def test_revamped_system():
    """Test the revamped node specification system with provider-based AI agents."""
    print("🚀 Testing Revamped Node Specification System v2.0")
    print("=" * 60)

    try:
        # Import the system
        from node_specs import (
            ConnectionType,
            DataFormat,
            InputPortSpec,
            NodeSpec,
            NodeSpecValidator,
            OutputPortSpec,
            ParameterDef,
            ParameterType,
            node_spec_registry,
        )

        print("✅ Successfully imported revamped node specification system")

        # Test 1: Load and verify AI Agent specifications
        print("\n📋 Test 1: AI Agent Provider Specifications")
        print("-" * 40)

        ai_providers = ["GEMINI_NODE", "OPENAI_NODE", "CLAUDE_NODE"]
        for provider in ai_providers:
            spec = node_spec_registry.get_spec("AI_AGENT_NODE", provider)
            if spec:
                print(
                    f"✅ {provider}: {len(spec.parameters)} parameters, {len(spec.input_ports)} inputs, {len(spec.output_ports)} outputs"
                )

                # Check for required system_prompt
                system_prompt_param = spec.get_parameter("system_prompt")
                if system_prompt_param and system_prompt_param.required:
                    print(f"   📝 System prompt is required ✓")
                else:
                    print(f"   ❌ System prompt parameter missing or not required")

                # Check for provider-specific parameters
                model_param = spec.get_parameter("model_version")
                if model_param:
                    print(f"   🤖 Model versions: {model_param.enum_values}")

            else:
                print(f"❌ {provider} specification not found")

        # Test 2: Validate AI Agent configurations
        print("\n🧪 Test 2: AI Agent Configuration Validation")
        print("-" * 40)

        class MockNode:
            def __init__(self, node_type, subtype, parameters=None):
                self.type = node_type
                self.subtype = subtype
                self.parameters = parameters or {}

        # Valid Gemini node
        gemini_node = MockNode(
            "AI_AGENT_NODE",
            "GEMINI_NODE",
            {
                "system_prompt": "You are a data analysis expert. Analyze the provided data for trends and insights.",
                "model_version": GoogleGeminiModel.GEMINI_2_5_FLASH_LITE.value,
                "temperature": "0.7",
                "safety_settings": '{"harassment": "BLOCK_MEDIUM_AND_ABOVE"}',
            },
        )

        errors = node_spec_registry.validate_node(gemini_node)
        if not errors:
            print("✅ Valid Gemini node passed validation")
        else:
            print(f"❌ Valid Gemini node failed: {errors}")

        # Valid OpenAI node
        openai_node = MockNode(
            "AI_AGENT_NODE",
            "OPENAI_NODE",
            {
                "system_prompt": "You are a helpful customer service assistant.",
                "model_version": OpenAIModel.GPT_5_NANO.value,
                "temperature": "0.5",
                "presence_penalty": "0.1",
                "frequency_penalty": "0.2",
            },
        )

        errors = node_spec_registry.validate_node(openai_node)
        if not errors:
            print("✅ Valid OpenAI node passed validation")
        else:
            print(f"❌ Valid OpenAI node failed: {errors}")

        # Valid Claude node
        claude_node = MockNode(
            "AI_AGENT_NODE",
            "CLAUDE_NODE",
            {
                "system_prompt": "You are a code review assistant. Analyze code for security and performance issues.",
                "model_version": AnthropicModel.CLAUDE_HAIKU_3_5.value,
                "temperature": "0.3",
                "stop_sequences": '["STOP", "END"]',
            },
        )

        errors = node_spec_registry.validate_node(claude_node)
        if not errors:
            print("✅ Valid Claude node passed validation")
        else:
            print(f"❌ Valid Claude node failed: {errors}")

        # Test 3: Invalid configurations should fail
        print("\n🚫 Test 3: Invalid Configuration Validation")
        print("-" * 40)

        # Missing required system_prompt
        invalid_node1 = MockNode(
            "AI_AGENT_NODE",
            "CLAUDE_NODE",
            {
                "model_version": AnthropicModel.CLAUDE_HAIKU_3_5.value,
                "temperature": "0.5"
                # Missing system_prompt
            },
        )

        errors = node_spec_registry.validate_node(invalid_node1)
        if errors and "system_prompt" in str(errors):
            print("✅ Missing system_prompt correctly failed validation")
        else:
            print(f"❌ Missing system_prompt should fail validation: {errors}")

        # Invalid temperature range
        invalid_node2 = MockNode(
            "AI_AGENT_NODE",
            "OPENAI_NODE",
            {"system_prompt": "Test prompt", "temperature": "1.5"},  # Invalid: > 1.0
        )

        errors = node_spec_registry.validate_node(invalid_node2)
        if errors and "temperature" in str(errors):
            print("✅ Invalid temperature correctly failed validation")
        else:
            print(f"❌ Invalid temperature should fail validation: {errors}")

        # Invalid model version
        invalid_node3 = MockNode(
            "AI_AGENT_NODE",
            "GEMINI_NODE",
            {
                "system_prompt": "Test prompt",
                "model_version": OpenAIModel.GPT_5_NANO.value,
            },  # Wrong provider model
        )

        errors = node_spec_registry.validate_node(invalid_node3)
        if errors and "model_version" in str(errors):
            print("✅ Invalid model version correctly failed validation")
        else:
            print(f"❌ Invalid model version should fail validation: {errors}")

        # Test 4: Connection validation between different node types
        print("\n🔗 Test 4: Node Connection Validation")
        print("-" * 40)

        # Create various node types for connection testing
        trigger_node = MockNode("TRIGGER_NODE", "WEBHOOK", {})
        ai_node = MockNode("AI_AGENT_NODE", "CLAUDE_NODE", {})
        action_node = MockNode("ACTION_NODE", "HTTP_REQUEST", {})
        flow_node = MockNode("FLOW_NODE", "IF", {})

        # Test valid connections (MAIN -> MAIN)
        test_connections = [
            (trigger_node, "main", ai_node, "main", "Trigger → AI Agent"),
            (ai_node, "main", action_node, "main", "AI Agent → Action"),
            (action_node, "main", flow_node, "main", "Action → Flow Control"),
        ]

        for source, source_port, target, target_port, description in test_connections:
            errors = node_spec_registry.validate_connection(
                source, source_port, target, target_port
            )
            if not errors:
                print(f"✅ {description} connection valid")
            else:
                print(f"❌ {description} connection failed: {errors}")

        # Test 5: System prompt examples and use cases
        print("\n📝 Test 5: System Prompt Examples")
        print("-" * 40)

        prompt_examples = [
            {
                "name": "Data Analyst",
                "prompt": """You are a data analyst. Analyze the provided dataset and:
1. Identify key trends and patterns
2. Detect outliers and anomalies
3. Provide actionable insights
4. Rate data quality (1-10)
Format response as structured JSON.""",
                "provider": "GEMINI_NODE",
            },
            {
                "name": "Customer Router",
                "prompt": """Route customer inquiries to the right department:
- "billing" for payment/invoice issues
- "technical" for product problems
- "sales" for new purchases
- "general" for everything else

Respond with: {"department": "...", "confidence": 0.95, "reason": "..."}""",
                "provider": "OPENAI_NODE",
            },
            {
                "name": "Code Reviewer",
                "prompt": """Review code for:
- Security vulnerabilities
- Performance issues
- Best practices adherence
- Potential bugs

Provide specific feedback with line numbers and improvement suggestions.""",
                "provider": "CLAUDE_NODE",
            },
        ]

        for example in prompt_examples:
            test_node = MockNode(
                "AI_AGENT_NODE",
                example["provider"],
                {"system_prompt": example["prompt"], "temperature": "0.5"},
            )

            errors = node_spec_registry.validate_node(test_node)
            if not errors:
                print(f"✅ {example['name']} ({example['provider']}) - Valid configuration")
            else:
                print(f"❌ {example['name']} failed validation: {errors}")

        # Test 6: Registry statistics and overview
        print("\n📊 Test 6: System Overview")
        print("-" * 40)

        all_specs = node_spec_registry.list_all_specs()
        node_types = node_spec_registry.get_node_types()

        print(f"📈 Total specifications loaded: {len(all_specs)}")
        print(f"📋 Node types available: {len(node_types)}")

        for node_type, subtypes in node_types.items():
            print(f"   🔹 {node_type}: {len(subtypes)} subtypes")
            if node_type == "AI_AGENT_NODE":
                print(f"      → {', '.join(subtypes)} (Provider-based)")
            else:
                print(f"      → {', '.join(subtypes[:3])}{'...' if len(subtypes) > 3 else ''}")

        print("\n" + "=" * 60)
        print("🎉 Revamped Node Specification System Test Complete!")
        print("✨ Key improvements:")
        print("   🤖 Provider-based AI agents (Gemini, OpenAI, Claude)")
        print("   📝 System prompt-driven functionality")
        print("   🔧 Enhanced validation and error handling")
        print("   📚 Comprehensive documentation and examples")
        print("   🚀 Simplified, flexible architecture")

        return True

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_revamped_system()
    sys.exit(0 if success else 1)
