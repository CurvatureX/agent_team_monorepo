"""
Unit tests for configuration system.

Tests all configuration functionality including validation,
OAuth2 provider configuration, and environment variable handling.
"""

import os
import pytest
from unittest.mock import patch

from workflow_engine.core.config import Settings, get_settings


class TestSettings:
    """Test cases for Settings class."""
    
    def test_settings_default_values(self):
        """Test that settings have reasonable default values."""
        settings = Settings()
        
        # Basic settings should have defaults
        assert settings.database_url.startswith("postgresql://")
        assert settings.grpc_host == "0.0.0.0"
        assert settings.grpc_port == 50051
        assert settings.log_level == "INFO"
        
        # Tool integration defaults
        assert settings.credential_encryption_key == "your-credential-encryption-key"
        assert settings.oauth2_state_expiry == 1800
        assert settings.redis_url == "redis://localhost:6379/1"
        assert settings.api_timeout_connect == 5
        assert settings.api_timeout_read == 30
        assert settings.api_max_retries == 3
        assert settings.api_retry_delays == "2,4,8"
        assert settings.max_concurrent_requests_per_user == 10
        assert settings.max_response_size_mb == 10
    
    def test_settings_from_environment_variables(self):
        """Test that settings load from environment variables."""
        env_vars = {
            "DATABASE_URL": "postgresql://test:test@test:5432/test",
            "GRPC_PORT": "60051",
            "LOG_LEVEL": "DEBUG",
            "CREDENTIAL_ENCRYPTION_KEY": "test_encryption_key_that_is_long_enough",
            "OAUTH2_STATE_EXPIRY": "3600",
            "REDIS_URL": "redis://test:6379/2",
            "API_TIMEOUT_CONNECT": "10",
            "API_TIMEOUT_READ": "60",
            "API_MAX_RETRIES": "5",
            "API_RETRY_DELAYS": "1,2,4,8,16",
            "MAX_CONCURRENT_REQUESTS_PER_USER": "20",
            "MAX_RESPONSE_SIZE_MB": "50",
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            
            assert settings.database_url == "postgresql://test:test@test:5432/test"
            assert settings.grpc_port == 60051
            assert settings.log_level == "DEBUG"
            assert settings.credential_encryption_key == "test_encryption_key_that_is_long_enough"
            assert settings.oauth2_state_expiry == 3600
            assert settings.redis_url == "redis://test:6379/2"
            assert settings.api_timeout_connect == 10
            assert settings.api_timeout_read == 60
            assert settings.api_max_retries == 5
            assert settings.api_retry_delays == "1,2,4,8,16"
            assert settings.max_concurrent_requests_per_user == 20
            assert settings.max_response_size_mb == 50
    
    def test_oauth2_provider_environment_variables(self):
        """Test OAuth2 provider configuration from environment."""
        env_vars = {
            "GOOGLE_OAUTH_CLIENT_ID": "google_client_id",
            "GOOGLE_OAUTH_CLIENT_SECRET": "google_client_secret",
            "GITHUB_OAUTH_CLIENT_ID": "github_client_id",
            "GITHUB_OAUTH_CLIENT_SECRET": "github_client_secret",
            "SLACK_OAUTH_CLIENT_ID": "slack_client_id",
            "SLACK_OAUTH_CLIENT_SECRET": "slack_client_secret",
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            
            assert settings.google_oauth_client_id == "google_client_id"
            assert settings.google_oauth_client_secret == "google_client_secret"
            assert settings.github_oauth_client_id == "github_client_id"
            assert settings.github_oauth_client_secret == "github_client_secret"
            assert settings.slack_oauth_client_id == "slack_client_id"
            assert settings.slack_oauth_client_secret == "slack_client_secret"
    
    def test_get_retry_delays(self):
        """Test parsing of retry delays configuration."""
        settings = Settings()
        
        # Test default value
        assert settings.get_retry_delays() == [2, 4, 8]
        
        # Test custom value
        settings.api_retry_delays = "1,3,5,10"
        assert settings.get_retry_delays() == [1, 3, 5, 10]
        
        # Test single value
        settings.api_retry_delays = "5"
        assert settings.get_retry_delays() == [5]
        
        # Test with spaces
        settings.api_retry_delays = " 1 , 2 , 3 "
        assert settings.get_retry_delays() == [1, 2, 3]
    
    def test_get_retry_delays_invalid(self):
        """Test parsing of invalid retry delays returns default."""
        settings = Settings()
        
        # Test invalid format
        settings.api_retry_delays = "not,valid,numbers"
        assert settings.get_retry_delays() == [2, 4, 8]
        
        # Test empty string
        settings.api_retry_delays = ""
        assert settings.get_retry_delays() == [2, 4, 8]
        
        # Test None (shouldn't happen in normal usage)
        settings.api_retry_delays = None
        assert settings.get_retry_delays() == [2, 4, 8]
    
    def test_get_max_response_size_bytes(self):
        """Test calculation of maximum response size in bytes."""
        settings = Settings()
        
        # Test default value (10 MB)
        assert settings.get_max_response_size_bytes() == 10 * 1024 * 1024
        
        # Test custom value
        settings.max_response_size_mb = 50
        assert settings.get_max_response_size_bytes() == 50 * 1024 * 1024
    
    def test_validate_encryption_key_valid(self):
        """Test encryption key validation with valid key."""
        settings = Settings()
        settings.credential_encryption_key = "this_is_a_valid_key_that_is_long_enough"
        
        # Should not raise exception
        settings.validate_encryption_key()
    
    def test_validate_encryption_key_too_short(self):
        """Test encryption key validation with short key."""
        settings = Settings()
        settings.credential_encryption_key = "short"
        
        with pytest.raises(ValueError, match="must be at least 32 characters"):
            settings.validate_encryption_key()
    
    def test_validate_oauth2_providers_all_configured(self):
        """Test OAuth2 provider validation when all providers are configured."""
        settings = Settings()
        settings.google_oauth_client_id = "google_id"
        settings.google_oauth_client_secret = "google_secret"
        settings.github_oauth_client_id = "github_id"
        settings.github_oauth_client_secret = "github_secret"
        settings.slack_oauth_client_id = "slack_id"
        settings.slack_oauth_client_secret = "slack_secret"
        
        missing = settings.validate_oauth2_providers()
        assert missing == []
    
    def test_validate_oauth2_providers_missing_some(self):
        """Test OAuth2 provider validation when some providers are missing."""
        settings = Settings()
        settings.google_oauth_client_id = "google_id"
        settings.google_oauth_client_secret = "google_secret"
        # GitHub and Slack not configured
        
        missing = settings.validate_oauth2_providers()
        assert "GitHub" in missing
        assert "Slack" in missing
        assert "Google Calendar" not in missing
    
    def test_validate_oauth2_providers_all_missing(self):
        """Test OAuth2 provider validation when all providers are missing."""
        settings = Settings()
        # All providers use default None values
        
        missing = settings.validate_oauth2_providers()
        assert "Google Calendar" in missing
        assert "GitHub" in missing
        assert "Slack" in missing
        assert len(missing) == 3
    
    def test_get_oauth2_config_google(self):
        """Test getting Google OAuth2 configuration."""
        settings = Settings()
        settings.google_oauth_client_id = "google_client_id"
        settings.google_oauth_client_secret = "google_client_secret"
        
        config = settings.get_oauth2_config("google_calendar")
        
        assert config["client_id"] == "google_client_id"
        assert config["client_secret"] == "google_client_secret"
        assert config["auth_url"] == "https://accounts.google.com/o/oauth2/v2/auth"
        assert config["token_url"] == "https://oauth2.googleapis.com/token"
        assert "https://www.googleapis.com/auth/calendar.events" in config["scopes"]
    
    def test_get_oauth2_config_github(self):
        """Test getting GitHub OAuth2 configuration."""
        settings = Settings()
        settings.github_oauth_client_id = "github_client_id"
        settings.github_oauth_client_secret = "github_client_secret"
        
        config = settings.get_oauth2_config("github")
        
        assert config["client_id"] == "github_client_id"
        assert config["client_secret"] == "github_client_secret"
        assert config["auth_url"] == "https://github.com/login/oauth/authorize"
        assert config["token_url"] == "https://github.com/login/oauth/access_token"
        assert "repo" in config["scopes"]
        assert "read:user" in config["scopes"]
    
    def test_get_oauth2_config_slack(self):
        """Test getting Slack OAuth2 configuration."""
        settings = Settings()
        settings.slack_oauth_client_id = "slack_client_id"
        settings.slack_oauth_client_secret = "slack_client_secret"
        
        config = settings.get_oauth2_config("slack")
        
        assert config["client_id"] == "slack_client_id"
        assert config["client_secret"] == "slack_client_secret"
        assert config["auth_url"] == "https://slack.com/oauth/v2/authorize"
        assert config["token_url"] == "https://slack.com/api/oauth.v2.access"
        assert "chat:write" in config["scopes"]
        assert "channels:read" in config["scopes"]
    
    def test_get_oauth2_config_unknown_provider(self):
        """Test getting OAuth2 configuration for unknown provider."""
        settings = Settings()
        
        with pytest.raises(ValueError, match="Unknown OAuth2 provider"):
            settings.get_oauth2_config("unknown_provider")


class TestGlobalSettings:
    """Test cases for global settings functions."""
    
    def test_get_settings_singleton(self):
        """Test that get_settings returns singleton instance."""
        # Clear global instance
        import workflow_engine.core.config as config_module
        config_module._settings = None
        
        instance1 = get_settings()
        instance2 = get_settings()
        
        assert instance1 is instance2
    
    def test_get_settings_with_environment(self):
        """Test get_settings with environment variables."""
        env_vars = {
            "LOG_LEVEL": "DEBUG",
            "CREDENTIAL_ENCRYPTION_KEY": "test_key_for_get_settings_function"
        }
        
        with patch.dict(os.environ, env_vars):
            # Clear global instance
            import workflow_engine.core.config as config_module
            config_module._settings = None
            
            settings = get_settings()
            assert settings.log_level == "DEBUG"
            assert settings.credential_encryption_key == "test_key_for_get_settings_function"


class TestConfigurationIntegration:
    """Integration tests for configuration system."""
    
    def test_production_like_configuration(self):
        """Test production-like configuration scenario."""
        production_env = {
            "DATABASE_URL": "postgresql://user:pass@db.example.com:5432/prod_db",
            "REDIS_URL": "redis://redis.example.com:6379/1",
            "CREDENTIAL_ENCRYPTION_KEY": "super_secure_production_key_that_is_very_long",
            "OAUTH2_STATE_EXPIRY": "1800",
            "API_TIMEOUT_CONNECT": "3",
            "API_TIMEOUT_READ": "30",
            "API_MAX_RETRIES": "3",
            "MAX_CONCURRENT_REQUESTS_PER_USER": "5",
            "MAX_RESPONSE_SIZE_MB": "5",
            "GOOGLE_OAUTH_CLIENT_ID": "prod_google_client_id",
            "GOOGLE_OAUTH_CLIENT_SECRET": "prod_google_client_secret",
            "GITHUB_OAUTH_CLIENT_ID": "prod_github_client_id",
            "GITHUB_OAUTH_CLIENT_SECRET": "prod_github_client_secret",
            "SLACK_OAUTH_CLIENT_ID": "prod_slack_client_id",
            "SLACK_OAUTH_CLIENT_SECRET": "prod_slack_client_secret",
        }
        
        with patch.dict(os.environ, production_env):
            settings = Settings()
            
            # Validate encryption key
            settings.validate_encryption_key()  # Should not raise
            
            # Validate OAuth2 providers
            missing_providers = settings.validate_oauth2_providers()
            assert missing_providers == []  # All providers configured
            
            # Test configuration retrieval
            google_config = settings.get_oauth2_config("google_calendar")
            assert google_config["client_id"] == "prod_google_client_id"
            
            github_config = settings.get_oauth2_config("github")
            assert github_config["client_id"] == "prod_github_client_id"
            
            slack_config = settings.get_oauth2_config("slack")
            assert slack_config["client_id"] == "prod_slack_client_id"
            
            # Test utility methods
            assert settings.get_retry_delays() == [2, 4, 8]
            assert settings.get_max_response_size_bytes() == 5 * 1024 * 1024
    
    def test_development_configuration(self):
        """Test development configuration scenario."""
        dev_env = {
            "DATABASE_URL": "postgresql://postgres:password@localhost:5432/dev_db",
            "CREDENTIAL_ENCRYPTION_KEY": "dev_key_for_testing_not_secure_enough",
            "LOG_LEVEL": "DEBUG",
            "API_TIMEOUT_READ": "120",  # Longer timeout for debugging
            "MAX_RESPONSE_SIZE_MB": "100",  # Larger limit for development
        }
        
        with patch.dict(os.environ, dev_env):
            settings = Settings()
            
            assert settings.log_level == "DEBUG"
            assert settings.api_timeout_read == 120
            assert settings.max_response_size_mb == 100
            
            # OAuth2 providers might not be configured in development
            missing_providers = settings.validate_oauth2_providers()
            # This is OK for development, just check that function works
            assert isinstance(missing_providers, list)


@pytest.fixture(autouse=True)
def cleanup_global_settings():
    """Cleanup global settings instance after each test."""
    yield
    # Reset global instance
    import workflow_engine.core.config as config_module
    config_module._settings = None 