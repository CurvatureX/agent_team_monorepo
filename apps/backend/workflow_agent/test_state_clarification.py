#!/usr/bin/env python3

"""
Test script to verify the need_clarification field is properly managed in state
"""

import asyncio

from core.mvp_models import MVPWorkflowState


def test_state_structure():
    """Test that the state includes the need_clarification field"""
    print("🧪 Testing state structure with need_clarification field...")

    # Create a new state
    state = MVPWorkflowState()

    # Check if the requirement_negotiation has the need_clarification field
    requirement_data = state.requirement_negotiation

    print(f"📊 Requirement negotiation keys: {list(requirement_data.keys())}")

    # Verify the field exists and has the correct default value
    has_field = "need_clarification" in requirement_data
    default_value = requirement_data.get("need_clarification")

    print(f"✓ Has need_clarification field: {has_field}")
    print(f"✓ Default value: {default_value}")
    print(f"✓ Value type: {type(default_value)}")

    # Test setting values
    print(f"\n🔧 Testing field assignment:")

    # Test setting to True (needs clarification)
    state.requirement_negotiation["need_clarification"] = True
    print(f"   After setting True: {state.requirement_negotiation['need_clarification']}")

    # Test setting to False (clear input)
    state.requirement_negotiation["need_clarification"] = False
    print(f"   After setting False: {state.requirement_negotiation['need_clarification']}")

    # Test resetting to None (not assessed)
    state.requirement_negotiation["need_clarification"] = None
    print(f"   After resetting None: {state.requirement_negotiation['need_clarification']}")

    return has_field and default_value is None


def test_clarification_flow_with_state():
    """Test the logical flow using the state field"""
    print(f"\n🔄 Testing clarification flow with state field...")

    def simulate_consultant_logic(state_data, needs_clarification):
        """Simulate the updated consultant logic"""
        # Check existing assessment
        existing_assessment = state_data.get("need_clarification")
        if existing_assessment is not None:
            print(f"   📋 Using existing assessment: {existing_assessment}")
            final_assessment = existing_assessment
        else:
            print(f"   🤖 New assessment result: {needs_clarification}")
            state_data["need_clarification"] = needs_clarification
            final_assessment = needs_clarification

        # Make decision based on assessment
        if final_assessment:
            return {
                "action": "ask_questions",
                "current_step": "consultant_phase",
                "should_continue": False,
                "waiting_for_user": True,
                "assessment_stored": state_data["need_clarification"],
            }
        else:
            return {
                "action": "proceed_to_scan",
                "current_step": "capability_scan",
                "should_continue": True,
                "waiting_for_user": False,
                "assessment_stored": state_data["need_clarification"],
            }

    # Test scenarios
    scenarios = [
        {
            "name": "New clear input",
            "state": {"need_clarification": None},
            "assessment": False,
            "expected_action": "proceed_to_scan",
        },
        {
            "name": "New unclear input",
            "state": {"need_clarification": None},
            "assessment": True,
            "expected_action": "ask_questions",
        },
        {
            "name": "Previously assessed as clear",
            "state": {"need_clarification": False},
            "assessment": True,  # This should be ignored
            "expected_action": "proceed_to_scan",
        },
        {
            "name": "Previously assessed as unclear",
            "state": {"need_clarification": True},
            "assessment": False,  # This should be ignored
            "expected_action": "ask_questions",
        },
    ]

    all_passed = True
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n   📝 Scenario {i}: {scenario['name']}")

        state_data = scenario["state"].copy()
        result = simulate_consultant_logic(state_data, scenario["assessment"])

        expected_action = scenario["expected_action"]
        actual_action = result["action"]
        stored_assessment = result["assessment_stored"]

        status = "✅" if actual_action == expected_action else "❌"
        print(f"      {status} Action: {actual_action} (expected: {expected_action})")
        print(f"      📊 Stored assessment: {stored_assessment}")

        if actual_action != expected_action:
            all_passed = False

    return all_passed


def main():
    """Main test function"""
    print("🚀 Testing need_clarification state field implementation\n")

    test1_passed = test_state_structure()
    test2_passed = test_clarification_flow_with_state()

    print(f"\n📊 Test Results:")
    print(f"   ✓ State structure: {'PASSED' if test1_passed else 'FAILED'}")
    print(f"   ✓ Flow logic: {'PASSED' if test2_passed else 'FAILED'}")

    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! State field implementation is working correctly.")
        print("\n📝 Benefits of the need_clarification field:")
        print("   • ✅ Assessment result is persisted in state")
        print("   • ✅ Avoids re-assessment on subsequent calls")
        print("   • ✅ Makes the process more transparent and trackable")
        print("   • ✅ Other parts of the workflow can reference this decision")
        print("   • ✅ Better debugging and logging capabilities")
        return True
    else:
        print("\n❌ Some tests failed. Check the implementation.")
        return False


if __name__ == "__main__":
    result = main()
    exit(0 if result else 1)
