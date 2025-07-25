"""
Tests for configuration validation
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from core.config_validator import (
    ConfigurationError,
    ConfigValidator,
    get_missing_env_vars_message,
    validate_environment_variables,
)


class TestConfigValidator:
    """Test configuration validator"""

    def test_validate_all_success(self):
        """Test successful validation with all required settings"""
        with patch("core.config_validator.settings") as mock_settings:
            # Mock valid settings
            mock_settings.APP_NAME = "Test API Gateway"
            mock_settings.MCP_ENABLED = True
            mock_settings.NODE_KNOWLEDGE_SUPABASE_URL = "https://test.supabase.co"
            mock_settings.NODE_KNOWLEDGE_SUPABASE_KEY = "test-key"
            mock_settings.NODE_KNOWLEDGE_DEFAULT_THRESHOLD = 0.5
            mock_settings.MCP_MAX_RESULTS_PER_TOOL = 100
            mock_settings.WORKFLOW_AGENT_HOST = "localhost"
            mock_settings.WORKFLOW_AGENT_PORT = 50051
            mock_settings.SECRET_KEY = "a-very-secure-secret-key-that-is-long-enough"
            mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
            mock_settings.ALLOWED_ORIGINS = ["http://localhost:3000"]
            mock_settings.ELASTICSEARCH_HOST = "localhost"
            mock_settings.ELASTICSEARCH_PORT = 9200

            validator = ConfigValidator()
            result = validator.validate_all()

            assert result["valid"] is True
            assert len(result["errors"]) == 0

    def test_validate_mcp_disabled(self):
        """Test validation when MCP is disabled"""
        with patch("core.config_validator.settings") as mock_settings:
            # Mock settings with MCP disabled
            mock_settings.APP_NAME = "Test API Gateway"
            mock_settings.MCP_ENABLED = False
            mock_settings.NODE_KNOWLEDGE_SUPABASE_URL = ""
            mock_settings.NODE_KNOWLEDGE_SUPABASE_KEY = ""
            mock_settings.NODE_KNOWLEDGE_DEFAULT_THRESHOLD = 0.5
            mock_settings.MCP_MAX_RESULTS_PER_TOOL = 100
            mock_settings.WORKFLOW_AGENT_HOST = "localhost"
            mock_settings.WORKFLOW_AGENT_PORT = 50051
            mock_settings.SECRET_KEY = "a-very-secure-secret-key-that-is-long-enough"
            mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
            mock_settings.ALLOWED_ORIGINS = ["http://localhost:3000"]
            mock_settings.ELASTICSEARCH_HOST = "localhost"
            mock_settings.ELASTICSEARCH_PORT = 9200

            validator = ConfigValidator()
            result = validator.validate_all()

            assert result["valid"] is True
            assert result["mcp_enabled"] is False

    def test_missing_supabase_credentials(self):
        """Test validation failure when Supabase credentials are missing"""
        with patch("core.config_validator.settings") as mock_settings:
            mock_settings.APP_NAME = "Test API Gateway"
            mock_settings.MCP_ENABLED = True
            mock_settings.NODE_KNOWLEDGE_SUPABASE_URL = ""
            mock_settings.NODE_KNOWLEDGE_SUPABASE_KEY = ""
            mock_settings.NODE_KNOWLEDGE_DEFAULT_THRESHOLD = 0.5
            mock_settings.MCP_MAX_RESULTS_PER_TOOL = 100
            mock_settings.WORKFLOW_AGENT_HOST = "localhost"
            mock_settings.WORKFLOW_AGENT_PORT = 50051
            mock_settings.SECRET_KEY = "secure-key"
            mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
            mock_settings.ALLOWED_ORIGINS = ["http://localhost:3000"]
            mock_settings.ELASTICSEARCH_HOST = "localhost"
            mock_settings.ELASTICSEARCH_PORT = 9200

            validator = ConfigValidator()

            with pytest.raises(ConfigurationError) as exc_info:
                validator.validate_all()

            assert "NODE_KNOWLEDGE_SUPABASE_URL is required" in str(exc_info.value)
            assert "NODE_KNOWLEDGE_SUPABASE_KEY is required" in str(exc_info.value)

    def test_default_secret_key(self):
        """Test validation failure with default secret key"""
        with patch("core.config_validator.settings") as mock_settings:
            mock_settings.APP_NAME = "Test API Gateway"
            mock_settings.MCP_ENABLED = False
            mock_settings.NODE_KNOWLEDGE_DEFAULT_THRESHOLD = 0.5
            mock_settings.MCP_MAX_RESULTS_PER_TOOL = 100
            mock_settings.WORKFLOW_AGENT_HOST = "localhost"
            mock_settings.WORKFLOW_AGENT_PORT = 50051
            mock_settings.SECRET_KEY = "your-secret-key-here"  # Default value
            mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
            mock_settings.ALLOWED_ORIGINS = ["http://localhost:3000"]
            mock_settings.ELASTICSEARCH_HOST = "localhost"
            mock_settings.ELASTICSEARCH_PORT = 9200

            validator = ConfigValidator()

            with pytest.raises(ConfigurationError) as exc_info:
                validator.validate_all()

            assert "SECRET_KEY must be set to a secure value" in str(exc_info.value)

    @patch("core.config_validator.ConfigValidator.validate_all")
    def test_validate_environment_variables_success(self, mock_validate):
        """Test successful environment variables validation"""
        mock_validate.return_value = {"valid": True, "errors": [], "warnings": []}

        result = validate_environment_variables()

        assert result["valid"] is True
        mock_validate.assert_called_once()


class TestUtilityFunctions:
    """Test utility functions"""

    def test_get_missing_env_vars_message(self):
        """Test missing environment variables message generation"""
        missing_vars = ["NODE_KNOWLEDGE_SUPABASE_URL", "SECRET_KEY"]
        message = get_missing_env_vars_message(missing_vars)

        assert "Missing required environment variables:" in message
        assert "NODE_KNOWLEDGE_SUPABASE_URL" in message
        assert "SECRET_KEY" in message
        assert "https://your-project.supabase.co" in message
        assert "your-secure-secret-key-here" in message

    def test_get_missing_env_vars_message_empty(self):
        """Test empty missing variables list"""
        message = get_missing_env_vars_message([])
        assert message == ""
