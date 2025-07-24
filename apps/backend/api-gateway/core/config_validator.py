"""
Configuration validation for API Gateway
"""

import os
from typing import Any, Dict, List, Optional

import structlog
from pydantic import ValidationError

from .config import settings
from .mcp_exceptions import MCPError, MCPErrorType

logger = structlog.get_logger()


class ConfigurationError(Exception):
    """Configuration validation error"""

    def __init__(self, message: str, missing_vars: Optional[List[str]] = None):
        self.message = message
        self.missing_vars = missing_vars or []
        super().__init__(message)


class ConfigValidator:
    """Configuration validator for API Gateway"""

    def __init__(self):
        self.validation_errors: List[str] = []
        self.warnings: List[str] = []

    def validate_all(self) -> Dict[str, Any]:
        """
        Validate all configuration settings

        Returns:
            Dict with validation results

        Raises:
            ConfigurationError: If critical configuration is missing
        """
        logger.info("Starting configuration validation")

        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "mcp_enabled": settings.MCP_ENABLED,
        }

        # Validate core settings
        self._validate_core_settings()

        # Validate MCP settings if enabled
        if settings.MCP_ENABLED:
            self._validate_mcp_settings()

        # Validate gRPC settings
        self._validate_grpc_settings()

        # Validate security settings
        self._validate_security_settings()

        # Compile results
        validation_result["errors"] = self.validation_errors
        validation_result["warnings"] = self.warnings
        validation_result["valid"] = len(self.validation_errors) == 0

        if self.validation_errors:
            logger.error(
                "Configuration validation failed",
                errors=self.validation_errors,
                warnings=self.warnings,
            )
            raise ConfigurationError(
                f"Configuration validation failed: {'; '.join(self.validation_errors)}",
                missing_vars=self._extract_missing_vars(),
            )

        if self.warnings:
            logger.warning(
                "Configuration validation completed with warnings", warnings=self.warnings
            )
        else:
            logger.info("Configuration validation completed successfully")

        return validation_result

    def _validate_core_settings(self):
        """Validate core application settings"""
        # Check APP_NAME
        if not settings.APP_NAME or settings.APP_NAME.strip() == "":
            self.validation_errors.append("APP_NAME cannot be empty")

        # Check CORS origins
        if not settings.ALLOWED_ORIGINS:
            self.warnings.append(
                "No CORS origins configured - API may not be accessible from browsers"
            )

    def _validate_mcp_settings(self):
        """Validate MCP service settings"""
        logger.info("Validating MCP configuration")

        # Check Node Knowledge Supabase settings
        if not settings.NODE_KNOWLEDGE_SUPABASE_URL:
            self.validation_errors.append(
                "NODE_KNOWLEDGE_SUPABASE_URL is required when MCP is enabled"
            )

        if not settings.NODE_KNOWLEDGE_SUPABASE_KEY:
            self.validation_errors.append(
                "NODE_KNOWLEDGE_SUPABASE_KEY is required when MCP is enabled"
            )

        # Validate Supabase URL format
        if (
            settings.NODE_KNOWLEDGE_SUPABASE_URL
            and not settings.NODE_KNOWLEDGE_SUPABASE_URL.startswith(("http://", "https://"))
        ):
            self.validation_errors.append(
                "NODE_KNOWLEDGE_SUPABASE_URL must be a valid HTTP/HTTPS URL"
            )

        # Validate threshold range
        if not (0.0 <= settings.NODE_KNOWLEDGE_DEFAULT_THRESHOLD <= 1.0):
            self.validation_errors.append(
                "NODE_KNOWLEDGE_DEFAULT_THRESHOLD must be between 0.0 and 1.0"
            )

        # Validate max results
        if settings.MCP_MAX_RESULTS_PER_TOOL <= 0:
            self.validation_errors.append("MCP_MAX_RESULTS_PER_TOOL must be greater than 0")

        # Check Elasticsearch settings (warn if not configured)
        if not settings.ELASTICSEARCH_HOST or settings.ELASTICSEARCH_HOST == "localhost":
            self.warnings.append(
                "Elasticsearch host not configured - elasticsearch tool will not be available"
            )

        if settings.ELASTICSEARCH_PORT <= 0 or settings.ELASTICSEARCH_PORT > 65535:
            self.validation_errors.append(
                "ELASTICSEARCH_PORT must be a valid port number (1-65535)"
            )

    def _validate_grpc_settings(self):
        """Validate gRPC connection settings"""
        if not settings.WORKFLOW_AGENT_HOST:
            self.validation_errors.append("WORKFLOW_AGENT_HOST is required")

        if settings.WORKFLOW_AGENT_PORT <= 0 or settings.WORKFLOW_AGENT_PORT > 65535:
            self.validation_errors.append(
                "WORKFLOW_AGENT_PORT must be a valid port number (1-65535)"
            )

    def _validate_security_settings(self):
        """Validate security-related settings"""
        # Check SECRET_KEY
        if not settings.SECRET_KEY or settings.SECRET_KEY == "your-secret-key-here":
            self.validation_errors.append(
                "SECRET_KEY must be set to a secure value (not the default placeholder)"
            )

        if len(settings.SECRET_KEY) < 32:
            self.warnings.append(
                "SECRET_KEY should be at least 32 characters long for better security"
            )

        # Check token expiration
        if settings.ACCESS_TOKEN_EXPIRE_MINUTES <= 0:
            self.validation_errors.append("ACCESS_TOKEN_EXPIRE_MINUTES must be greater than 0")

    def _extract_missing_vars(self) -> List[str]:
        """Extract environment variable names from error messages"""
        missing_vars = []
        for error in self.validation_errors:
            if "is required" in error:
                # Extract variable name from error message
                var_name = error.split(" is required")[0].split()[-1]
                if var_name.isupper():
                    missing_vars.append(var_name)
        return missing_vars

    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration (without sensitive data)"""
        return {
            "app_name": settings.APP_NAME,
            "debug": settings.DEBUG,
            "mcp_enabled": settings.MCP_ENABLED,
            "mcp_max_results": settings.MCP_MAX_RESULTS_PER_TOOL,
            "node_knowledge_threshold": settings.NODE_KNOWLEDGE_DEFAULT_THRESHOLD,
            "workflow_agent_host": settings.WORKFLOW_AGENT_HOST,
            "workflow_agent_port": settings.WORKFLOW_AGENT_PORT,
            "elasticsearch_host": settings.ELASTICSEARCH_HOST,
            "elasticsearch_port": settings.ELASTICSEARCH_PORT,
            "cors_origins_count": len(settings.ALLOWED_ORIGINS),
            "supabase_url_configured": bool(settings.NODE_KNOWLEDGE_SUPABASE_URL),
            "supabase_key_configured": bool(settings.NODE_KNOWLEDGE_SUPABASE_KEY),
        }


def validate_environment_variables() -> Dict[str, Any]:
    """
    Validate environment variables and return validation results

    Returns:
        Dict with validation results

    Raises:
        ConfigurationError: If critical configuration is missing
    """
    validator = ConfigValidator()
    return validator.validate_all()


def get_missing_env_vars_message(missing_vars: List[str]) -> str:
    """Generate helpful error message for missing environment variables"""
    if not missing_vars:
        return ""

    message = "Missing required environment variables:\n"
    for var in missing_vars:
        message += f"  - {var}\n"

    message += "\nPlease set these variables in your .env file or environment.\n"
    message += "Example .env file entries:\n"

    for var in missing_vars:
        if "SUPABASE_URL" in var:
            message += f"{var}=https://your-project.supabase.co\n"
        elif "SUPABASE_KEY" in var:
            message += f"{var}=your-supabase-anon-key\n"
        elif "SECRET_KEY" in var:
            message += f"{var}=your-secure-secret-key-here\n"
        elif "HOST" in var:
            message += f"{var}=localhost\n"
        elif "PORT" in var:
            message += f"{var}=50051\n"
        else:
            message += f"{var}=your-value-here\n"

    return message
