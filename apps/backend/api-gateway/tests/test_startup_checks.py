"""
Tests for startup health checks
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from core.config_validator import ConfigurationError
from core.startup_checks import (
    StartupCheckError,
    StartupHealthChecker,
    log_startup_status,
    run_startup_checks,
)


class TestStartupHealthChecker:
    """Test startup health checker"""

    @pytest.fixture
    def checker(self):
        """Create a startup health checker instance"""
        return StartupHealthChecker()

    @pytest.mark.asyncio
    async def test_run_all_checks_success(self, checker):
        """Test successful startup checks"""
        with (
            patch.object(checker, "_check_configuration") as mock_config,
            patch.object(checker, "_check_supabase_connection") as mock_supabase,
            patch.object(checker, "_check_node_knowledge_service") as mock_node_knowledge,
            patch("core.startup_checks.settings") as mock_settings,
        ):
            mock_settings.MCP_ENABLED = True

            # Mock successful checks
            mock_config.return_value = {
                "healthy": True,
                "status": "passed",
                "message": "Configuration validation successful",
            }
            mock_supabase.return_value = {
                "healthy": True,
                "status": "connected",
                "message": "Supabase connection successful",
            }
            mock_node_knowledge.return_value = {
                "healthy": True,
                "status": "healthy",
                "message": "Node Knowledge service is operational",
            }

            result = await checker.run_all_checks()

            assert result["healthy"] is True
            assert len(result["errors"]) == 0
            assert "configuration" in result["checks"]
            assert "supabase" in result["checks"]
            assert "node_knowledge" in result["checks"]

    @pytest.mark.asyncio
    async def test_run_all_checks_mcp_disabled(self, checker):
        """Test startup checks when MCP is disabled"""
        with (
            patch.object(checker, "_check_configuration") as mock_config,
            patch("core.startup_checks.settings") as mock_settings,
        ):
            mock_settings.MCP_ENABLED = False

            mock_config.return_value = {
                "healthy": True,
                "status": "passed",
                "message": "Configuration validation successful",
            }

            result = await checker.run_all_checks()

            assert result["healthy"] is True
            assert result["checks"]["supabase"]["status"] == "skipped"
            assert result["checks"]["node_knowledge"]["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_check_configuration_success(self, checker):
        """Test successful configuration check"""
        with patch(
            "core.startup_checks.validate_environment_variables"
        ) as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "errors": [],
                "warnings": ["Some warning"],
            }

            result = await checker._check_configuration()

            assert result["healthy"] is True
            assert result["status"] == "passed"
            assert result["warnings"] == ["Some warning"]

    @pytest.mark.asyncio
    async def test_check_configuration_failure(self, checker):
        """Test configuration check failure"""
        with patch(
            "core.startup_checks.validate_environment_variables"
        ) as mock_validate:
            mock_validate.side_effect = ConfigurationError("Config error", ["TEST_VAR"])

            result = await checker._check_configuration()

            assert result["healthy"] is False
            assert result["status"] == "failed"
            assert "Config error" in result["error"]
            assert result["missing_vars"] == ["TEST_VAR"]

    @pytest.mark.asyncio
    async def test_check_supabase_connection_success(self, checker):
        """Test successful Supabase connection check"""
        with (
            patch("core.startup_checks.create_client") as mock_create_client,
            patch("core.startup_checks.settings") as mock_settings,
        ):
            mock_settings.NODE_KNOWLEDGE_SUPABASE_URL = "https://test.supabase.co"
            mock_settings.NODE_KNOWLEDGE_SUPABASE_KEY = "test-key"

            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.data = [{"id": 1}]
            mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value = (
                mock_response
            )
            mock_create_client.return_value = mock_client

            result = await checker._check_supabase_connection()

            assert result["healthy"] is True
            assert result["status"] == "connected"
            assert result["details"]["test_query_results"] == 1

    @pytest.mark.asyncio
    async def test_check_node_knowledge_service_success(self, checker):
        """Test successful Node Knowledge service check"""
        with patch("core.startup_checks.get_node_knowledge_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.health_check.return_value = {
                "healthy": True,
                "total_records": 10,
            }
            mock_client_class = Mock()
            mock_client_class.return_value = mock_client
            mock_get_client.return_value = mock_client_class

            result = await checker._check_node_knowledge_service()

            assert result["healthy"] is True
            assert result["status"] == "healthy"
            assert result["details"]["total_records"] == 10


class TestUtilityFunctions:
    """Test utility functions"""

    @pytest.mark.asyncio
    async def test_run_startup_checks_success(self):
        """Test successful startup checks function"""
        with patch("core.startup_checks.StartupHealthChecker") as mock_checker_class:
            mock_checker = MagicMock()
            mock_checker.run_all_checks = AsyncMock(return_value={"healthy": True})
            mock_checker_class.return_value = mock_checker

            result = await run_startup_checks()

            assert result["healthy"] is True
            mock_checker.run_all_checks.assert_called_once()

    def test_log_startup_status_success(self):
        """Test logging successful startup status"""
        check_results = {
            "healthy": True,
            "checks": {
                "configuration": {"healthy": True, "status": "passed", "message": "OK"},
                "supabase": {"healthy": True, "status": "connected", "message": "Connected"},
            },
        }

        with (
            patch("core.startup_checks.logger") as mock_logger,
            patch("core.startup_checks.settings") as mock_settings,
        ):
            mock_settings.MCP_ENABLED = True

            log_startup_status(check_results)

            # Verify success log was called
            mock_logger.info.assert_called()
            calls = mock_logger.info.call_args_list
            assert any("startup successful" in str(call) for call in calls)
