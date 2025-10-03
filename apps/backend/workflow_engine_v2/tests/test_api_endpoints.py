"""
Test API endpoints for workflow_engine_v2.
"""
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient

from shared.models.node_enums import NodeType, TriggerSubtype
from shared.models.workflow import Connection, Node, Workflow, WorkflowMetadata
from workflow_engine_v2.app.main import app
from workflow_engine_v2.services.oauth2_service import TokenResponse


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_workflow():
    """Create a sample workflow for testing."""
    metadata = WorkflowMetadata(
        id="test_workflow",
        name="Test Workflow",
        created_time=int(datetime.utcnow().timestamp() * 1000),
        created_by="test_user",
    )

    nodes = [
        Node(
            id="trigger_1",
            type=NodeType.TRIGGER.value,
            subtype=TriggerSubtype.WEBHOOK.value,
            configurations={"port": 8080},
        ),
        Node(
            id="action_1",
            type="ACTION",
            subtype="HTTP_REQUEST",
            configurations={"url": "https://api.example.com", "method": "GET"},
        ),
    ]

    connections = [
        Connection(id="conn_1", from_node="trigger_1", to_node="action_1", output_key="result")
    ]

    return Workflow(metadata=metadata, nodes=nodes, connections=connections, triggers=["trigger_1"])


class TestHealthEndpoint:
    """Test health endpoint."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["service"] == "workflow_engine_v2"


class TestWorkflowEndpoints:
    """Test workflow CRUD endpoints."""

    def test_create_workflow(self, client, sample_workflow):
        """Test creating a workflow."""
        create_data = {
            "workflow_id": sample_workflow.metadata.id,
            "name": sample_workflow.metadata.name,
            "created_by": sample_workflow.metadata.created_by,
            "nodes": [node.model_dump() for node in sample_workflow.nodes],
            "connections": [conn.model_dump() for conn in sample_workflow.connections],
            "triggers": sample_workflow.triggers,
            "created_time_ms": sample_workflow.metadata.created_time,
        }

        response = client.post("/api/v2/workflows", json=create_data)
        assert response.status_code == 200

        workflow_data = response.json()
        assert workflow_data["metadata"]["id"] == sample_workflow.metadata.id
        assert workflow_data["metadata"]["name"] == sample_workflow.metadata.name

    def test_get_workflow(self, client, sample_workflow):
        """Test getting a workflow by ID."""
        # First create the workflow
        create_data = {
            "workflow_id": sample_workflow.metadata.id,
            "name": sample_workflow.metadata.name,
            "created_by": sample_workflow.metadata.created_by,
            "nodes": [node.model_dump() for node in sample_workflow.nodes],
            "connections": [conn.model_dump() for conn in sample_workflow.connections],
            "triggers": sample_workflow.triggers,
        }
        client.post("/api/v2/workflows", json=create_data)

        # Then get it
        response = client.get(f"/api/v2/workflows/{sample_workflow.metadata.id}")
        assert response.status_code == 200

        workflow_data = response.json()
        assert workflow_data["metadata"]["id"] == sample_workflow.metadata.id

    def test_get_nonexistent_workflow(self, client):
        """Test getting a non-existent workflow."""
        response = client.get("/api/v2/workflows/nonexistent_id")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_list_workflows(self, client):
        """Test listing workflows."""
        response = client.get("/api/v2/workflows")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_update_workflow(self, client, sample_workflow):
        """Test updating a workflow."""
        # First create the workflow
        create_data = {
            "workflow_id": sample_workflow.metadata.id,
            "name": sample_workflow.metadata.name,
            "created_by": sample_workflow.metadata.created_by,
            "nodes": [node.model_dump() for node in sample_workflow.nodes],
            "connections": [conn.model_dump() for conn in sample_workflow.connections],
            "triggers": sample_workflow.triggers,
        }
        create_response = client.post("/api/v2/workflows", json=create_data)
        created_workflow = create_response.json()

        # Update the workflow name
        created_workflow["metadata"]["name"] = "Updated Workflow Name"

        response = client.put(
            f"/api/v2/workflows/{sample_workflow.metadata.id}", json=created_workflow
        )
        assert response.status_code == 200

        updated_workflow = response.json()
        assert updated_workflow["metadata"]["name"] == "Updated Workflow Name"

    def test_delete_workflow(self, client, sample_workflow):
        """Test deleting a workflow."""
        # First create the workflow
        create_data = {
            "workflow_id": sample_workflow.metadata.id,
            "name": sample_workflow.metadata.name,
            "created_by": sample_workflow.metadata.created_by,
            "nodes": [node.model_dump() for node in sample_workflow.nodes],
            "connections": [conn.model_dump() for conn in sample_workflow.connections],
            "triggers": sample_workflow.triggers,
        }
        client.post("/api/v2/workflows", json=create_data)

        # Then delete it
        response = client.delete(f"/api/v2/workflows/{sample_workflow.metadata.id}")
        assert response.status_code == 200
        assert response.json()["deleted"] is True

    def test_import_workflow(self, client, sample_workflow):
        """Test importing a workflow."""
        workflow_data = sample_workflow.model_dump()
        import_data = {"data": workflow_data}

        response = client.post("/api/v2/workflows/import", json=import_data)
        assert response.status_code == 200

        imported_workflow = response.json()
        assert imported_workflow["metadata"]["id"] == sample_workflow.metadata.id


class TestExecutionEndpoints:
    """Test execution endpoints."""

    def test_execute_workflow(self, client, sample_workflow):
        """Test executing a workflow."""
        # First create the workflow
        create_data = {
            "workflow_id": sample_workflow.metadata.id,
            "name": sample_workflow.metadata.name,
            "created_by": sample_workflow.metadata.created_by,
            "nodes": [node.model_dump() for node in sample_workflow.nodes],
            "connections": [conn.model_dump() for conn in sample_workflow.connections],
            "triggers": sample_workflow.triggers,
        }
        client.post("/api/v2/workflows", json=create_data)

        # Execute the workflow
        execute_data = {"trigger_type": "manual", "trigger_data": {"test": "data"}}

        response = client.post(
            f"/api/v2/workflows/{sample_workflow.metadata.id}/execute", json=execute_data
        )
        assert response.status_code == 200

        execution_data = response.json()
        assert "execution_id" in execution_data
        assert execution_data["workflow_id"] == sample_workflow.metadata.id

    def test_execute_nonexistent_workflow(self, client):
        """Test executing a non-existent workflow."""
        execute_data = {"trigger_type": "manual", "trigger_data": {"test": "data"}}

        response = client.post("/api/v2/workflows/nonexistent/execute", json=execute_data)
        assert response.status_code == 404

    def test_get_execution(self, client, sample_workflow):
        """Test getting an execution by ID."""
        # Create workflow and execute it
        create_data = {
            "workflow_id": sample_workflow.metadata.id,
            "name": sample_workflow.metadata.name,
            "created_by": sample_workflow.metadata.created_by,
            "nodes": [node.model_dump() for node in sample_workflow.nodes],
            "connections": [conn.model_dump() for conn in sample_workflow.connections],
            "triggers": sample_workflow.triggers,
        }
        client.post("/api/v2/workflows", json=create_data)

        execute_response = client.post(
            f"/api/v2/workflows/{sample_workflow.metadata.id}/execute",
            json={"trigger_type": "manual", "trigger_data": {}},
        )
        execution_id = execute_response.json()["execution_id"]

        # Get the execution
        response = client.get(f"/api/v2/executions/{execution_id}")
        assert response.status_code == 200

        execution_data = response.json()
        assert execution_data["execution_id"] == execution_id

    def test_list_executions(self, client):
        """Test listing executions."""
        response = client.get("/api/v2/executions")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_executions_with_pagination(self, client):
        """Test listing executions with pagination."""
        response = client.get("/api/v2/executions?limit=10&offset=0")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_cancel_execution(self, client, sample_workflow):
        """Test cancelling an execution."""
        # Create workflow and execute it
        create_data = {
            "workflow_id": sample_workflow.metadata.id,
            "name": sample_workflow.metadata.name,
            "created_by": sample_workflow.metadata.created_by,
            "nodes": [node.model_dump() for node in sample_workflow.nodes],
            "connections": [conn.model_dump() for conn in sample_workflow.connections],
            "triggers": sample_workflow.triggers,
        }
        client.post("/api/v2/workflows", json=create_data)

        execute_response = client.post(
            f"/api/v2/workflows/{sample_workflow.metadata.id}/execute",
            json={"trigger_type": "manual", "trigger_data": {}},
        )
        execution_id = execute_response.json()["execution_id"]

        # Cancel the execution
        response = client.post(f"/api/v2/executions/{execution_id}/cancel")
        assert response.status_code == 200


class TestCredentialEndpoints:
    """Test credential management endpoints."""

    @patch("workflow_engine_v2.app.main.oauth_svc")
    def test_check_credentials(self, mock_oauth_svc, client):
        """Test checking user credentials."""
        # Mock the OAuth service
        mock_oauth_svc.get_valid_token = AsyncMock(return_value="valid_token")

        check_data = {"user_id": "user123", "provider": "google"}

        response = client.post("/api/v2/credentials/check", json=check_data)
        assert response.status_code == 200

        result = response.json()
        assert result["has_credentials"] is True
        assert result["provider"] == "google"

    @patch("workflow_engine_v2.app.main.oauth_svc")
    def test_check_credentials_not_found(self, mock_oauth_svc, client):
        """Test checking non-existent credentials."""
        mock_oauth_svc.get_valid_token = AsyncMock(return_value=None)

        check_data = {"user_id": "user123", "provider": "github"}

        response = client.post("/api/v2/credentials/check", json=check_data)
        assert response.status_code == 200

        result = response.json()
        assert result["has_credentials"] is False
        assert result["provider"] == "github"

    @patch("workflow_engine_v2.app.main.oauth_svc")
    def test_store_credentials(self, mock_oauth_svc, client):
        """Test storing user credentials."""
        # Mock OAuth service methods
        token_response = TokenResponse(
            access_token="new_token",
            refresh_token="refresh_token",
            expires_in=3600,
            token_type="Bearer",
        )
        mock_oauth_svc.exchange_code_for_token = AsyncMock(return_value=token_response)
        mock_oauth_svc.store_user_credentials = AsyncMock(return_value=True)

        store_data = {
            "user_id": "user123",
            "provider": "google",
            "code": "auth_code_123",
            "redirect_uri": "http://localhost:3000/callback",
            "client_id": "google_client_id",
        }

        response = client.post("/api/v2/credentials/store", json=store_data)
        assert response.status_code == 200

        result = response.json()
        assert result["success"] is True
        assert result["provider"] == "google"

    def test_delete_credentials(self, client):
        """Test deleting user credentials."""
        response = client.delete("/api/v2/credentials/user123/google")
        assert response.status_code == 200

        result = response.json()
        assert result["deleted"] is False  # Not implemented yet
        assert "not implemented" in result["message"].lower()


class TestNodeSpecEndpoints:
    """Test node specification endpoints."""

    def test_get_all_node_specs(self, client):
        """Test getting all node specifications."""
        response = client.get("/api/v2/node-specs")
        assert response.status_code == 200

        specs = response.json()["specs"]
        assert isinstance(specs, dict)

        # Should have common node types
        expected_types = [
            NodeType.TRIGGER.value,
            NodeType.ACTION.value,
            NodeType.EXTERNAL_ACTION.value,
            NodeType.FLOW.value,
            NodeType.AI_AGENT.value,
            NodeType.MEMORY.value,
        ]
        for node_type in expected_types:
            assert node_type in specs

    def test_get_node_type_specs(self, client):
        """Test getting specifications for a specific node type."""
        response = client.get("/api/v2/node-specs/ACTION")
        assert response.status_code == 200

        result = response.json()
        assert result["node_type"] == "ACTION"
        assert "subtypes" in result
        assert isinstance(result["subtypes"], dict)

    def test_get_invalid_node_type_specs(self, client):
        """Test getting specifications for invalid node type."""
        response = client.get("/api/v2/node-specs/INVALID_TYPE")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestValidationEndpoints:
    """Test workflow validation endpoints."""

    def test_validate_workflow_by_id(self, client, sample_workflow):
        """Test validating a workflow by ID."""
        # First create the workflow
        create_data = {
            "workflow_id": sample_workflow.metadata.id,
            "name": sample_workflow.metadata.name,
            "created_by": sample_workflow.metadata.created_by,
            "nodes": [node.model_dump() for node in sample_workflow.nodes],
            "connections": [conn.model_dump() for conn in sample_workflow.connections],
            "triggers": sample_workflow.triggers,
        }
        client.post("/api/v2/workflows", json=create_data)

        # Validate the workflow
        response = client.post(f"/api/v2/workflows/{sample_workflow.metadata.id}/validate")
        assert response.status_code == 200

        result = response.json()
        assert result["workflow_id"] == sample_workflow.metadata.id
        assert "is_valid" in result
        assert "errors" in result
        assert "warnings" in result

    def test_validate_workflow_data(self, client, sample_workflow):
        """Test validating workflow data without storing."""
        validate_data = {"workflow": sample_workflow.model_dump()}

        response = client.post("/api/v2/workflows/validate", json=validate_data)
        assert response.status_code == 200

        result = response.json()
        assert result["workflow_id"] == sample_workflow.metadata.id
        assert "is_valid" in result
        assert "errors" in result
        assert "warnings" in result

    def test_validate_nonexistent_workflow(self, client):
        """Test validating a non-existent workflow."""
        response = client.post("/api/v2/workflows/nonexistent/validate")
        assert response.status_code == 404


class TestLoggingEndpoints:
    """Test logging endpoints."""

    def test_get_execution_logs(self, client, sample_workflow):
        """Test getting execution logs."""
        # Create and execute workflow first
        create_data = {
            "workflow_id": sample_workflow.metadata.id,
            "name": sample_workflow.metadata.name,
            "created_by": sample_workflow.metadata.created_by,
            "nodes": [node.model_dump() for node in sample_workflow.nodes],
            "connections": [conn.model_dump() for conn in sample_workflow.connections],
            "triggers": sample_workflow.triggers,
        }
        client.post("/api/v2/workflows", json=create_data)

        execute_response = client.post(
            f"/api/v2/workflows/{sample_workflow.metadata.id}/execute",
            json={"trigger_type": "manual", "trigger_data": {}},
        )
        execution_id = execute_response.json()["execution_id"]

        # Get logs
        response = client.get(f"/api/v2/workflows/executions/{execution_id}/logs")
        assert response.status_code == 200

        result = response.json()
        assert result["execution_id"] == execution_id
        assert "logs" in result
        assert "total_count" in result

    def test_get_execution_logs_with_pagination(self, client, sample_workflow):
        """Test getting execution logs with pagination."""
        # Create and execute workflow first
        create_data = {
            "workflow_id": sample_workflow.metadata.id,
            "name": sample_workflow.metadata.name,
            "created_by": sample_workflow.metadata.created_by,
            "nodes": [node.model_dump() for node in sample_workflow.nodes],
            "connections": [conn.model_dump() for conn in sample_workflow.connections],
            "triggers": sample_workflow.triggers,
        }
        client.post("/api/v2/workflows", json=create_data)

        execute_response = client.post(
            f"/api/v2/workflows/{sample_workflow.metadata.id}/execute",
            json={"trigger_type": "manual", "trigger_data": {}},
        )
        execution_id = execute_response.json()["execution_id"]

        # Get logs with pagination
        response = client.get(f"/api/v2/workflows/executions/{execution_id}/logs?limit=10&offset=0")
        assert response.status_code == 200


class TestTimerEndpoints:
    """Test timer-related endpoints."""

    def test_resume_due_timers(self, client):
        """Test resuming due timers."""
        response = client.post("/api/v2/executions/resume/due-timers")
        assert response.status_code == 200

        result = response.json()
        assert result["resumed"] is True
