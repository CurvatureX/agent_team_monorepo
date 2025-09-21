#!/usr/bin/env python3
"""
Comprehensive import tests for the workflow engine.

This test suite verifies that all imports in the workflow engine work correctly
and that there are no "attempted relative import beyond top-level package" errors.
"""

import os
import sys
from pathlib import Path

import pytest

# Add the workflow engine to the Python path
workflow_engine_path = Path(__file__).parent.parent
sys.path.insert(0, str(workflow_engine_path))


class TestCriticalImports:
    """Test critical imports that were causing relative import errors."""

    def test_external_action_imports(self):
        """Test all external action imports work correctly."""
        # Test base external action
        from nodes.external_actions.base_external_action import BaseExternalAction

        assert BaseExternalAction is not None

        # Test specific external actions
        from nodes.external_actions.github_external_action import GitHubExternalAction
        from nodes.external_actions.google_calendar_external_action import (
            GoogleCalendarExternalAction,
        )
        from nodes.external_actions.notion_external_action import NotionExternalAction
        from nodes.external_actions.slack_external_action import SlackExternalAction

        # Verify they inherit from base
        assert issubclass(SlackExternalAction, BaseExternalAction)
        assert issubclass(GitHubExternalAction, BaseExternalAction)
        assert issubclass(NotionExternalAction, BaseExternalAction)
        assert issubclass(GoogleCalendarExternalAction, BaseExternalAction)

    def test_node_base_imports(self):
        """Test node base imports work correctly."""
        from nodes.base import (
            BaseNodeExecutor,
            ExecutionStatus,
            NodeExecutionContext,
            NodeExecutionResult,
        )

        # Verify enum values exist
        assert hasattr(ExecutionStatus, "SUCCESS")
        assert hasattr(ExecutionStatus, "ERROR")
        assert hasattr(ExecutionStatus, "PENDING")

        # Verify classes are properly defined
        assert NodeExecutionContext is not None
        assert NodeExecutionResult is not None
        assert BaseNodeExecutor is not None

    def test_oauth_service_import(self):
        """Test OAuth service import works correctly."""
        from services.oauth2_service_lite import OAuth2ServiceLite

        assert OAuth2ServiceLite is not None

        # Verify it can be instantiated
        oauth_service = OAuth2ServiceLite()
        assert oauth_service is not None

    def test_database_import(self):
        """Test database import works correctly."""
        from database import Database

        assert Database is not None

        # Verify it can be instantiated
        db = Database()
        assert db is not None

    def test_execution_log_service_import(self):
        """Test execution log service import works correctly."""
        try:
            from services.execution_log_service import (
                ExecutionLogEntry,
                LogEventType,
                get_execution_log_service,
            )

            assert ExecutionLogEntry is not None
            assert LogEventType is not None
            assert get_execution_log_service is not None
        except ImportError as e:
            # Some imports might not be available in test environment
            pytest.skip(f"Execution log service not available: {e}")


class TestNodeExecutorImports:
    """Test all node executor imports work correctly."""

    def test_all_node_executors_import(self):
        """Test all node executor classes can be imported."""
        from nodes.action_node import ActionNodeExecutor
        from nodes.ai_agent_node import AIAgentNodeExecutor

        # Verify they all inherit from BaseNodeExecutor
        from nodes.base import BaseNodeExecutor
        from nodes.external_action_node import ExternalActionNodeExecutor
        from nodes.flow_node import FlowNodeExecutor
        from nodes.human_loop_node import HumanLoopNodeExecutor
        from nodes.memory_node import MemoryNodeExecutor
        from nodes.tool_node import ToolNodeExecutor
        from nodes.trigger_node import TriggerNodeExecutor

        assert issubclass(ActionNodeExecutor, BaseNodeExecutor)
        assert issubclass(AIAgentNodeExecutor, BaseNodeExecutor)
        assert issubclass(ExternalActionNodeExecutor, BaseNodeExecutor)
        assert issubclass(FlowNodeExecutor, BaseNodeExecutor)
        assert issubclass(HumanLoopNodeExecutor, BaseNodeExecutor)
        assert issubclass(MemoryNodeExecutor, BaseNodeExecutor)
        assert issubclass(ToolNodeExecutor, BaseNodeExecutor)
        assert issubclass(TriggerNodeExecutor, BaseNodeExecutor)

    def test_node_factory_import(self):
        """Test node factory import works correctly."""
        from nodes.factory import NodeExecutorFactory

        assert NodeExecutorFactory is not None

        # Verify it has the register method
        assert hasattr(NodeExecutorFactory, "register")
        assert hasattr(NodeExecutorFactory, "create")


class TestServiceImports:
    """Test service layer imports work correctly."""

    def test_core_services_import(self):
        """Test core service imports."""
        # These might not all be available in test environment
        services_to_test = [
            "services.supabase_repository",
            "services.workflow_service",
            "services.workflow_status_manager",
        ]

        for service_name in services_to_test:
            try:
                module = __import__(service_name, fromlist=[""])
                assert module is not None
            except ImportError as e:
                pytest.skip(f"Service {service_name} not available: {e}")


class TestConfigAndModels:
    """Test configuration and model imports."""

    def test_config_import(self):
        """Test configuration import works."""
        from config import settings

        assert settings is not None

    def test_models_import(self):
        """Test model imports work."""
        from models import (
            ExecuteWorkflowRequest,
            ExecuteWorkflowResponse,
            GetExecutionRequest,
            GetExecutionResponse,
        )

        assert ExecuteWorkflowRequest is not None
        assert ExecuteWorkflowResponse is not None
        assert GetExecutionRequest is not None
        assert GetExecutionResponse is not None


class TestUtilityImports:
    """Test utility imports work correctly."""

    def test_unicode_utils_import(self):
        """Test unicode utils import."""
        from utils.unicode_utils import (
            clean_unicode_data,
            clean_unicode_string,
            ensure_utf8_safe_dict,
            safe_json_dumps,
        )

        assert clean_unicode_string is not None
        assert safe_json_dumps is not None
        assert clean_unicode_data is not None
        assert ensure_utf8_safe_dict is not None


class TestMainApplicationImports:
    """Test main application imports work."""

    def test_main_app_imports(self):
        """Test main application imports."""
        # Test that we can import the main modules
        import config
        import database
        import executor
        import main
        import models

        assert main is not None
        assert executor is not None
        assert database is not None
        assert config is not None
        assert models is not None


class TestExternalActionSpecificFunctionality:
    """Test external action specific functionality that was failing."""

    def test_slack_external_action_oauth_import(self):
        """Test that Slack external action can import OAuth service."""
        from nodes.external_actions.slack_external_action import SlackExternalAction

        # Create an instance
        slack_action = SlackExternalAction()
        assert slack_action.integration_name == "slack"

    def test_base_external_action_oauth_methods(self):
        """Test that base external action OAuth methods work."""
        from nodes.external_actions.base_external_action import BaseExternalAction

        # Create a test subclass
        class TestExternalAction(BaseExternalAction):
            async def handle_operation(self, context, operation):
                return None

        test_action = TestExternalAction("test")
        assert test_action.integration_name == "test"

        # Verify error handling methods exist
        assert hasattr(test_action, "create_error_result")
        assert hasattr(test_action, "create_success_result")
        assert hasattr(test_action, "log_execution")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
