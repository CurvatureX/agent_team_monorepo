"""
Basic tests for workflow_scheduler service
Tests core functionality without external dependencies
"""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from shared.models.trigger import TriggerSpec, TriggerType
from workflow_scheduler.services.deployment_service import DeploymentService
from workflow_scheduler.services.trigger_manager import TriggerManager
from workflow_scheduler.triggers.manual_trigger import ManualTrigger


class TestTriggerTypes:
    """Test trigger type definitions"""

    def test_trigger_types_exist(self):
        """Test that all expected trigger types are defined"""
        expected_types = {
            "TRIGGER_CRON",
            "TRIGGER_MANUAL",
            "TRIGGER_WEBHOOK",
            "TRIGGER_EMAIL",
            "TRIGGER_GITHUB",
        }

        actual_types = {t.value for t in TriggerType}
        assert expected_types == actual_types


class TestTriggerSpec:
    """Test trigger specification model"""

    def test_trigger_spec_creation(self):
        """Test creating a trigger specification"""
        spec = TriggerSpec(
            subtype=TriggerType.MANUAL, parameters={"require_confirmation": True}, enabled=True
        )

        assert spec.node_type == "TRIGGER_NODE"
        assert spec.subtype == TriggerType.MANUAL
        assert spec.parameters == {"require_confirmation": True}
        assert spec.enabled is True


class TestManualTrigger:
    """Test manual trigger implementation"""

    @pytest.fixture
    def manual_trigger(self):
        """Create a manual trigger for testing"""
        config = {"require_confirmation": False, "enabled": True}
        return ManualTrigger("test_workflow", config)

    def test_manual_trigger_creation(self, manual_trigger):
        """Test manual trigger initialization"""
        assert manual_trigger.workflow_id == "test_workflow"
        assert manual_trigger.trigger_type == "TRIGGER_MANUAL"
        assert manual_trigger.require_confirmation is False
        assert manual_trigger.enabled is True

    @pytest.mark.asyncio
    async def test_manual_trigger_start_stop(self, manual_trigger):
        """Test manual trigger start/stop lifecycle"""
        # Test start
        result = await manual_trigger.start()
        assert result is True

        # Test stop
        result = await manual_trigger.stop()
        assert result is True


class TestTriggerManager:
    """Test trigger manager functionality"""

    @pytest.fixture
    def mock_lock_manager(self):
        """Create a mock lock manager"""
        return Mock()

    @pytest.fixture
    def trigger_manager(self, mock_lock_manager):
        """Create a trigger manager for testing"""
        manager = TriggerManager(mock_lock_manager)
        manager.register_trigger_class(TriggerType.MANUAL, ManualTrigger)
        return manager

    def test_trigger_manager_creation(self, trigger_manager):
        """Test trigger manager initialization"""
        assert trigger_manager is not None
        assert TriggerType.MANUAL in trigger_manager._trigger_registry

    @pytest.mark.asyncio
    async def test_health_check(self, trigger_manager):
        """Test trigger manager health check"""
        health = await trigger_manager.health_check()

        assert "total_workflows" in health
        assert "total_triggers" in health
        assert "workflows" in health
        assert health["total_workflows"] == 0
        assert health["total_triggers"] == 0


class TestDeploymentService:
    """Test deployment service functionality"""

    @pytest.fixture
    def mock_trigger_manager(self):
        """Create a mock trigger manager"""
        manager = Mock()
        manager.register_triggers = AsyncMock(return_value=True)
        manager.unregister_triggers = AsyncMock(return_value=True)
        manager.get_trigger_status = AsyncMock(return_value={})
        return manager

    @pytest.fixture
    def deployment_service(self, mock_trigger_manager):
        """Create a deployment service for testing"""
        return DeploymentService(mock_trigger_manager)

    def test_deployment_service_creation(self, deployment_service):
        """Test deployment service initialization"""
        assert deployment_service is not None
        assert deployment_service.trigger_manager is not None

    @pytest.mark.asyncio
    async def test_workflow_validation(self, deployment_service):
        """Test workflow definition validation"""
        # Valid workflow
        valid_workflow = {
            "nodes": [
                {
                    "node_type": "TRIGGER_NODE",
                    "subtype": "TRIGGER_MANUAL",
                    "parameters": {"require_confirmation": False},
                }
            ]
        }

        result = await deployment_service._validate_workflow_definition(valid_workflow)
        assert result["valid"] is True
        assert result["error"] is None

        # Invalid workflow - no nodes
        invalid_workflow = {"invalid": "structure"}

        result = await deployment_service._validate_workflow_definition(invalid_workflow)
        assert result["valid"] is False
        assert "nodes" in result["error"]

    def test_extract_trigger_specs(self, deployment_service):
        """Test trigger specification extraction"""
        workflow_spec = {
            "nodes": [
                {
                    "node_type": "TRIGGER_NODE",
                    "subtype": "TRIGGER_MANUAL",
                    "parameters": {"require_confirmation": True},
                    "enabled": True,
                },
                {"node_type": "ACTION_NODE", "subtype": "HTTP_REQUEST"},
            ]
        }

        specs = deployment_service._extract_trigger_specs(workflow_spec)

        assert len(specs) == 1
        assert specs[0].subtype == TriggerType.MANUAL
        assert specs[0].parameters == {"require_confirmation": True}
        assert specs[0].enabled is True


class TestConfiguration:
    """Test configuration and settings"""

    def test_settings_import(self):
        """Test that settings can be imported"""
        from workflow_scheduler.core.config import settings

        assert settings is not None
        assert hasattr(settings, "port")
        assert hasattr(settings, "host")
        assert hasattr(settings, "debug")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
