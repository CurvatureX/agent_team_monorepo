#!/usr/bin/env python3
"""
Test script to validate the connection format fixes.
"""

import os
import sys

sys.path.append("/Users/jingweizhang/Workspace/agent_team_monorepo/apps/backend")

from pydantic import ValidationError

from shared.models.workflow import (
    ConnectionArrayData,
    ConnectionData,
    NodeConnectionsData,
    NodeData,
    PositionData,
    WorkflowData,
    WorkflowSettingsData,
)


def test_correct_connection_format():
    """Test that correct connection format validates successfully."""
    print("🧪 Testing correct connection format...")

    try:
        # Create valid workflow data with correct connection format
        nodes = [
            NodeData(
                id="trigger_node",
                name="Trigger",
                type="TRIGGER",
                subtype="MANUAL",
                position=PositionData(x=100, y=100),
            ),
            NodeData(
                id="action_node",
                name="Action",
                type="ACTION",
                subtype="HTTP",
                position=PositionData(x=300, y=100),
            ),
        ]

        # Correct connection format
        connections = {
            "trigger_node": NodeConnectionsData(
                connection_types={
                    "main": ConnectionArrayData(
                        connections=[ConnectionData(node="action_node", type="main", index=0)]
                    )
                }
            )
        }

        workflow = WorkflowData(
            name="Test Workflow",
            nodes=nodes,
            connections=connections,
            settings=WorkflowSettingsData(),
        )

        print("✅ Correct connection format validated successfully!")
        return True

    except ValidationError as e:
        print(f"❌ Unexpected validation error for correct format: {e}")
        return False


def test_incorrect_connection_format():
    """Test that incorrect connection formats are rejected."""
    print("🧪 Testing incorrect connection format...")

    try:
        nodes = [
            NodeData(
                id="trigger_node",
                name="Trigger",
                type="TRIGGER",
                subtype="MANUAL",
                position=PositionData(x=100, y=100),
            ),
            NodeData(
                id="action_node",
                name="Action",
                type="ACTION",
                subtype="HTTP",
                position=PositionData(x=300, y=100),
            ),
        ]

        # Incorrect connection format (old target-centric format)
        incorrect_connections = {
            "action_node": {"main": [[{"node": "trigger_node", "type": "main", "index": 0}]]}
        }

        workflow = WorkflowData(
            name="Test Workflow",
            nodes=nodes,
            connections=incorrect_connections,
            settings=WorkflowSettingsData(),
        )

        print("❌ Incorrect connection format was accepted (should have failed!)")
        return False

    except ValidationError as e:
        print(f"✅ Incorrect connection format correctly rejected: {e}")
        return True


def test_missing_connection_types():
    """Test that connections missing connection_types are rejected."""
    print("🧪 Testing missing connection_types...")

    try:
        nodes = [
            NodeData(
                id="trigger_node",
                name="Trigger",
                type="TRIGGER",
                subtype="MANUAL",
                position=PositionData(x=100, y=100),
            )
        ]

        # Missing connection_types
        invalid_connections = {"trigger_node": {"invalid_structure": "test"}}

        workflow = WorkflowData(
            name="Test Workflow",
            nodes=nodes,
            connections=invalid_connections,
            settings=WorkflowSettingsData(),
        )

        print("❌ Invalid connection structure was accepted (should have failed!)")
        return False

    except ValidationError as e:
        print(f"✅ Invalid connection structure correctly rejected: {e}")
        return True


def main():
    """Run all tests."""
    print("🚀 Testing Connection Format Validation Fixes")
    print("=" * 50)

    tests = [
        test_correct_connection_format,
        test_incorrect_connection_format,
        test_missing_connection_types,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print("📊 Test Results:")
    print(f"   Passed: {passed}/{total}")

    if passed == total:
        print("🎉 All tests passed! Connection format validation is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Connection format validation needs fixes.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
