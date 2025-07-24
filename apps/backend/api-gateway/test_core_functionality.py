#!/usr/bin/env python3
"""
Test script to verify core functionality without external dependencies
"""

import asyncio
import os
import sys
from unittest.mock import MagicMock, patch

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config_validator import ConfigurationError, ConfigValidator, get_missing_env_vars_message
from core.startup_checks import StartupCheckError, StartupHealthChecker


def test_missing_env_vars_message():
    """Test missing environment variables message generation"""
    print("Testing Missing Environment Variables Message...")

    missing_vars = ["NODE_KNOWLEDGE_SUPABASE_URL", "SECRET_KEY", "WORKFLOW_AGENT_HOST"]
    message = get_missing_env_vars_message(missing_vars)

    assert "Missing required environment variables:" in message
    assert "NODE_KNOWLEDGE_SUPABASE_URL" in message
    assert "SECRET_KEY" in message
    assert "WORKFLOW_AGENT_HOST" in message
    assert "https://your-project.supabase.co" in message
    assert "your-secure-secret-key-here" in message
    assert "localhost" in message

    print("✅ Missing environment variables message test passed")

    # Test empty list
    empty_message = get_missing_env_vars_message([])
    assert empty_message == ""
    print("✅ Empty missing variables list test passed")


def test_config_validation_edge_cases():
    """Test configuration validation edge cases"""
    print("Testing Configuration Validation Edge Cases...")

    # Test invalid threshold values
    with patch("core.config_validator.settings") as mock_settings:
        mock_settings.APP_NAME = "Test API Gateway"
        mock_settings.MCP_ENABLED = True
        mock_settings.NODE_KNOWLEDGE_SUPABASE_URL = "https://test.supabase.co"
        mock_settings.NODE_KNOWLEDGE_SUPABASE_KEY = "test-key"
        mock_settings.NODE_KNOWLEDGE_DEFAULT_THRESHOLD = 1.5  # Invalid
        mock_settings.MCP_MAX_RESULTS_PER_TOOL = 100
        mock_settings.WORKFLOW_AGENT_HOST = "localhost"
        mock_settings.WORKFLOW_AGENT_PORT = 50051
        mock_settings.SECRET_KEY = "secure-key"
        mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        mock_settings.ALLOWED_ORIGINS = ["http://localhost:3000"]
        mock_settings.ELASTICSEARCH_HOST = "localhost"
        mock_settings.ELASTICSEARCH_PORT = 9200

        validator = ConfigValidator()

        try:
            validator.validate_all()
            assert False, "Should have raised ConfigurationError"
        except ConfigurationError as e:
            assert "must be between 0.0 and 1.0" in str(e)
            print("✅ Invalid threshold validation test passed")

    # Test invalid port numbers
    with patch("core.config_validator.settings") as mock_settings:
        mock_settings.APP_NAME = "Test API Gateway"
        mock_settings.MCP_ENABLED = False
        mock_settings.WORKFLOW_AGENT_HOST = "localhost"
        mock_settings.WORKFLOW_AGENT_PORT = 0  # Invalid
        mock_settings.SECRET_KEY = "secure-key"
        mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        mock_settings.ALLOWED_ORIGINS = ["http://localhost:3000"]
        mock_settings.ELASTICSEARCH_HOST = "localhost"
        mock_settings.ELASTICSEARCH_PORT = 70000  # Invalid

        validator = ConfigValidator()

        try:
            validator.validate_all()
            assert False, "Should have raised ConfigurationError"
        except ConfigurationError as e:
            error_message = str(e)
            # Check that at least one port validation error is present
            assert (
                "WORKFLOW_AGENT_PORT must be a valid port number" in error_message
                or "ELASTICSEARCH_PORT must be a valid port number" in error_message
            )
            print("✅ Invalid port numbers validation test passed")


async def test_startup_checks_edge_cases():
    """Test startup checks edge cases"""
    print("Testing Startup Checks Edge Cases...")

    checker = StartupHealthChecker()

    # Test configuration check failure
    with patch("core.startup_checks.validate_environment_variables") as mock_validate:
        mock_validate.side_effect = ConfigurationError("Config error", ["TEST_VAR"])

        result = await checker._check_configuration()

        assert result["healthy"] is False
        assert result["status"] == "failed"
        assert "Config error" in result["error"]
        assert result["missing_vars"] == ["TEST_VAR"]
        print("✅ Configuration check failure test passed")

    # Test Supabase connection with missing credentials
    with patch("core.startup_checks.settings") as mock_settings:
        mock_settings.NODE_KNOWLEDGE_SUPABASE_URL = ""
        mock_settings.NODE_KNOWLEDGE_SUPABASE_KEY = ""

        result = await checker._check_supabase_connection()

        assert result["healthy"] is False
        assert result["status"] == "failed"
        assert "credentials not configured" in result["error"]
        print("✅ Missing Supabase credentials test passed")

    # Test Supabase connection failure
    with (
        patch("core.startup_checks.create_client") as mock_create_client,
        patch("core.startup_checks.settings") as mock_settings,
    ):
        mock_settings.NODE_KNOWLEDGE_SUPABASE_URL = "https://test.supabase.co"
        mock_settings.NODE_KNOWLEDGE_SUPABASE_KEY = "test-key"
        mock_create_client.side_effect = Exception("Connection failed")

        result = await checker._check_supabase_connection()

        assert result["healthy"] is False
        assert result["status"] == "failed"
        assert "Connection failed" in result["error"]
        print("✅ Supabase connection failure test passed")


def test_config_validator_warnings():
    """Test configuration validator warnings generation"""
    print("Testing Configuration Validator Warnings...")

    with patch("core.config_validator.settings") as mock_settings:
        mock_settings.APP_NAME = "Test API Gateway"
        mock_settings.MCP_ENABLED = True
        mock_settings.NODE_KNOWLEDGE_SUPABASE_URL = "https://test.supabase.co"
        mock_settings.NODE_KNOWLEDGE_SUPABASE_KEY = "test-key"
        mock_settings.NODE_KNOWLEDGE_DEFAULT_THRESHOLD = 0.5
        mock_settings.MCP_MAX_RESULTS_PER_TOOL = 100
        mock_settings.WORKFLOW_AGENT_HOST = "localhost"
        mock_settings.WORKFLOW_AGENT_PORT = 50051
        mock_settings.SECRET_KEY = "short"  # Too short but not invalid
        mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        mock_settings.ALLOWED_ORIGINS = []  # Empty CORS origins
        mock_settings.ELASTICSEARCH_HOST = "localhost"  # Default value
        mock_settings.ELASTICSEARCH_PORT = 9200

        validator = ConfigValidator()
        result = validator.validate_all()

        assert result["valid"] is True
        assert len(result["warnings"]) > 0
        assert any("CORS origins" in warning for warning in result["warnings"])
        assert any("32 characters long" in warning for warning in result["warnings"])
        print("✅ Configuration warnings test passed")


async def main():
    """Run all core functionality tests"""
    print("🚀 Starting core functionality tests...\n")

    try:
        test_missing_env_vars_message()
        test_config_validation_edge_cases()
        await test_startup_checks_edge_cases()
        test_config_validator_warnings()

        print(
            "\n✅ All core functionality tests passed! Implementation is robust and handles edge cases correctly."
        )

    except Exception as e:
        print(f"\n❌ Core functionality test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
