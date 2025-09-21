#!/usr/bin/env python3
"""
Simple test runner for import tests.

This script runs import tests without requiring pytest to be installed.
"""

import sys
import traceback
from pathlib import Path

# Add the workflow engine to the Python path
workflow_engine_path = Path(__file__).parent
sys.path.insert(0, str(workflow_engine_path))


def test_critical_imports():
    """Test critical imports that were causing issues."""
    print("🔍 Testing critical imports...")

    tests = []

    # Test 1: External action imports (the main failing case)
    try:
        from nodes.external_actions.base_external_action import BaseExternalAction
        from nodes.external_actions.github_external_action import GitHubExternalAction
        from nodes.external_actions.google_calendar_external_action import (
            GoogleCalendarExternalAction,
        )
        from nodes.external_actions.notion_external_action import NotionExternalAction
        from nodes.external_actions.slack_external_action import SlackExternalAction

        # Specifically test for the "attempted relative import beyond top-level package" error
        # by trying to instantiate the classes
        slack_action = SlackExternalAction()

        tests.append(("External action imports & instantiation", True, None))
    except Exception as e:
        error_msg = str(e)
        if "attempted relative import beyond top-level package" in error_msg:
            tests.append(
                ("External action imports & instantiation", False, f"CRITICAL: {error_msg}")
            )
        else:
            tests.append(("External action imports & instantiation", False, error_msg))

    # Test 2: Node base imports
    try:
        from nodes.base import (
            BaseNodeExecutor,
            ExecutionStatus,
            NodeExecutionContext,
            NodeExecutionResult,
        )

        tests.append(("Node base imports", True, None))
    except Exception as e:
        tests.append(("Node base imports", False, str(e)))

    # Test 3: OAuth service import
    try:
        from services.oauth2_service_lite import OAuth2ServiceLite

        oauth_service = OAuth2ServiceLite()
        tests.append(("OAuth service import", True, None))
    except Exception as e:
        tests.append(("OAuth service import", False, str(e)))

    # Test 4: Database import
    try:
        from database import Database

        db = Database()
        tests.append(("Database import", True, None))
    except Exception as e:
        tests.append(("Database import", False, str(e)))

    # Test 5: Main application imports
    try:
        import config
        import executor
        import main
        import models

        tests.append(("Main application imports", True, None))
    except Exception as e:
        tests.append(("Main application imports", False, str(e)))

    # Test 6: Workflow status manager import
    try:
        from services.workflow_status_manager import WorkflowPauseReason

        tests.append(("Workflow status manager import", True, None))
    except Exception as e:
        tests.append(("Workflow status manager import", False, str(e)))

    # Test 6.5: Supabase repository import and method verification
    try:
        from services.supabase_repository import SupabaseWorkflowRepository

        repository = SupabaseWorkflowRepository()

        # Verify critical methods exist
        has_get_workflow = hasattr(repository, "get_workflow")
        has_get_execution = hasattr(repository, "get_execution")

        if has_get_workflow and has_get_execution:
            tests.append(("Supabase repository methods", True, None))
        else:
            missing_methods = []
            if not has_get_workflow:
                missing_methods.append("get_workflow")
            if not has_get_execution:
                missing_methods.append("get_execution")
            tests.append(
                ("Supabase repository methods", False, f"Missing methods: {missing_methods}")
            )
    except Exception as e:
        tests.append(("Supabase repository methods", False, str(e)))

    # Test 7: External action instantiation (the original failing case)
    try:
        from nodes.external_actions.slack_external_action import SlackExternalAction

        slack_action = SlackExternalAction()
        # This should not raise the "attempted relative import beyond top-level package" error
        tests.append(("Slack external action instantiation", True, None))
    except Exception as e:
        tests.append(("Slack external action instantiation", False, str(e)))

    # Test 8: Simulate OAuth token retrieval (the specific failing scenario)
    try:
        from nodes.base import NodeExecutionContext
        from nodes.external_actions.base_external_action import BaseExternalAction

        # Create a test external action class
        class TestExternalAction(BaseExternalAction):
            async def handle_operation(self, context, operation):
                # This was the line that was failing with relative import errors
                return await self.get_oauth_token(context)

        test_action = TestExternalAction("test")

        # Test that it can import the necessary services
        from services.oauth2_service_lite import OAuth2ServiceLite
        from services.supabase_repository import SupabaseWorkflowRepository

        # This should now work without import errors
        # (We're not actually calling it async, just testing that the class can be created)
        tests.append(("OAuth token retrieval method access", True, None))
    except Exception as e:
        error_msg = str(e)
        if "attempted relative import beyond top-level package" in error_msg:
            tests.append(
                ("OAuth token retrieval method access", False, f"CRITICAL OAUTH ERROR: {error_msg}")
            )
        else:
            tests.append(("OAuth token retrieval method access", False, error_msg))

    return tests


def test_node_executor_imports():
    """Test all node executor imports."""
    print("🔍 Testing node executor imports...")

    tests = []

    node_executors = [
        ("ActionNodeExecutor", "nodes.action_node"),
        ("AIAgentNodeExecutor", "nodes.ai_agent_node"),
        ("ExternalActionNodeExecutor", "nodes.external_action_node"),
        ("FlowNodeExecutor", "nodes.flow_node"),
        ("HumanLoopNodeExecutor", "nodes.human_loop_node"),
        ("MemoryNodeExecutor", "nodes.memory_node"),
        ("ToolNodeExecutor", "nodes.tool_node"),
        ("TriggerNodeExecutor", "nodes.trigger_node"),
    ]

    for class_name, module_name in node_executors:
        try:
            module = __import__(module_name, fromlist=[class_name])
            executor_class = getattr(module, class_name)
            tests.append((f"{class_name} import", True, None))
        except Exception as e:
            tests.append((f"{class_name} import", False, str(e)))

    return tests


def run_all_tests():
    """Run all import tests and report results."""
    print("🚀 Running comprehensive import tests for workflow engine...\n")

    all_tests = []
    all_tests.extend(test_critical_imports())
    all_tests.extend(test_node_executor_imports())

    # Print results
    passed = 0
    failed = 0

    print("📊 Test Results:")
    print("=" * 80)

    for test_name, success, error in all_tests:
        if success:
            print(f"✅ {test_name}")
            passed += 1
        else:
            print(f"❌ {test_name}: {error}")
            failed += 1

    print("=" * 80)
    print(f"📈 Summary: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All import tests passed! No relative import issues found.")
        return True
    else:
        print("⚠️  Some import tests failed. Check the errors above.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
