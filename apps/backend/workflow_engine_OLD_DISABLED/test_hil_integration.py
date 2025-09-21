#!/usr/bin/env python3
"""
Test HIL Integration - Verify HIL node executor with real Slack integration.

Tests the enhanced HIL system with integrated response messaging capabilities.
"""

import json
import os
import sys
from datetime import datetime, timedelta

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.models.human_in_loop import (
    HILChannelConfig,
    HILChannelType,
    HILInputData,
    HILInteractionType,
    HILPriority,
)
from shared.models.node_enums import HumanLoopSubtype
from workflow_engine.workflow_engine.nodes.base import NodeExecutionContext
from workflow_engine.workflow_engine.nodes.human_loop_node import HumanLoopNodeExecutor


def test_hil_slack_integration():
    """Test HIL node executor with Slack integration."""
    print("🧪 Testing HIL Node Executor with Slack Integration\n")

    # Create HIL node executor
    hil_executor = HumanLoopNodeExecutor(subtype=HumanLoopSubtype.SLACK_INTERACTION.value)
    print(f"✅ Created HIL executor for {HumanLoopSubtype.SLACK_INTERACTION.value}")

    # Check Slack integration status
    slack_available = hil_executor.slack_client is not None
    print(f"📱 Slack client available: {'✅ Yes' if slack_available else '❌ No'}")

    # Check HIL service status
    hil_service_status = hil_executor.hil_service.get_service_status()
    print(f"🔧 HIL service status: {hil_service_status}")

    # Test node specification support
    supported_subtypes = hil_executor.get_supported_subtypes()
    print(f"🔧 Supported HIL subtypes: {', '.join(supported_subtypes)}")

    return slack_available


def test_hil_input_validation():
    """Test HIL input data validation."""
    print("\n🧪 Testing HIL Input Data Validation\n")

    try:
        # Create valid HIL input data
        channel_config = HILChannelConfig(
            channel_type=HILChannelType.SLACK,
            slack_channel="#test-channel",
        )

        hil_input = HILInputData(
            interaction_type=HILInteractionType.APPROVAL,
            question="Approve deployment to production?",
            priority=HILPriority.HIGH,
            timeout_hours=2,
            channel_config=channel_config,
            context_data={"deployment_id": "deploy-123", "environment": "production"},
            correlation_id="test-correlation-123",
        )

        print(f"✅ HIL input validation passed")
        print(f"   Interaction Type: {hil_input.interaction_type.value}")
        print(f"   Priority: {hil_input.priority.value}")
        print(f"   Timeout: {hil_input.timeout_hours} hours")
        print(f"   Channel: {hil_input.channel_config.slack_channel}")
        return True

    except Exception as e:
        print(f"❌ HIL input validation failed: {e}")
        return False


def test_hil_node_spec_integration():
    """Test HIL node with enhanced specifications including response messaging."""
    print("\n🧪 Testing Enhanced HIL Node Specifications\n")

    # Create HIL node executor
    hil_executor = HumanLoopNodeExecutor(subtype=HumanLoopSubtype.SLACK_INTERACTION.value)

    # Create mock execution context with enhanced parameters
    mock_context = type(
        "MockContext",
        (),
        {
            "input_data": {
                # Basic HIL parameters
                "question": "Approve this calendar event creation?",
                "priority": "HIGH",
                "timeout_hours": 2,
                "slack_channel": "#approvals",
                # Enhanced response messaging parameters (from node specs)
                "approved_message": "✅ Calendar event approved! Event created: {{data.event_id}}",
                "rejected_message": "❌ Calendar event rejected by {{responder.username}}",
                "timeout_message": "⏰ Approval request timed out for event {{data.event_id}}",
                "send_responses_to_channel": True,
                "response_channel": "#calendar-updates",
            },
            "workflow_id": "wf-calendar-123",
            "execution_id": "exec-456",
            "node_id": "node-hil-789",
            "parameters": {},
        },
    )()

    # Test response message handling
    try:
        interaction_id = "test-interaction-123"
        response_data = {
            "approved": True,
            "responder": {"username": "john.doe"},
            "context_data": {"event_id": "cal-event-456"},
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Test the response handling method
        result = hil_executor.handle_hil_response_with_messaging(
            interaction_id=interaction_id, response_data=response_data, context=mock_context
        )

        print(f"✅ HIL response handling test passed")
        print(f"   Status: {result.status}")
        print(f"   Output Port: {result.output_port}")
        print(f"   Messaging Success: {result.output_data.get('messaging_success')}")
        print(f"   Logs: {result.logs}")

        return True

    except Exception as e:
        print(f"❌ HIL response handling test failed: {e}")
        return False


def test_message_template_processing():
    """Test message template variable substitution."""
    print("\n🧪 Testing Message Template Processing\n")

    hil_executor = HumanLoopNodeExecutor(subtype=HumanLoopSubtype.SLACK_INTERACTION.value)

    # Test template processing
    template = "✅ Event {{data.event_id}} approved by {{responder.username}} at {{timestamp}}"
    context_data = {
        "data": {"event_id": "cal-123"},
        "responder": {"username": "jane.smith"},
        "timestamp": "2025-01-15T10:30:00Z",
    }

    processed = hil_executor._process_message_template(template, context_data)
    expected = "✅ Event cal-123 approved by jane.smith at 2025-01-15T10:30:00Z"

    if processed == expected:
        print(f"✅ Template processing test passed")
        print(f"   Template: {template}")
        print(f"   Processed: {processed}")
        return True
    else:
        print(f"❌ Template processing test failed")
        print(f"   Expected: {expected}")
        print(f"   Got: {processed}")
        return False


def main():
    """Run all HIL integration tests."""
    print("🚀 HIL Integration Test Suite")
    print("=" * 50)

    tests = [
        ("Slack Integration", test_hil_slack_integration),
        ("Input Validation", test_hil_input_validation),
        ("Node Spec Integration", test_hil_node_spec_integration),
        ("Message Template Processing", test_message_template_processing),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
                print(f"\n✅ {test_name}: PASSED")
            else:
                print(f"\n❌ {test_name}: FAILED")
        except Exception as e:
            print(f"\n💥 {test_name}: ERROR - {e}")

    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! HIL integration is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
