"""
HTTP Client for Workflow Service (FastAPI Migration)
Replaces gRPC client with HTTP requests to the migrated FastAPI workflow engine.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from app.config import settings
from app.utils import log_error, log_info, log_warning


class WorkflowServiceHTTPClient:
    """HTTP client for the FastAPI Workflow Service."""

    def __init__(self):
        self.base_url = (
            f"http://{settings.WORKFLOW_ENGINE_HOST}:{settings.WORKFLOW_ENGINE_HTTP_PORT}"
        )
        self.timeout = httpx.Timeout(30.0, connect=5.0)
        self.client: Optional[httpx.AsyncClient] = None
        self.connected = False

    async def connect(self):
        """Initialize HTTP client connection."""
        try:
            self.client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )

            # Test connection with health check
            response = await self.client.get("/health")

            if response.status_code == 200:
                self.connected = True
                log_info(f"✅ Connected to Workflow Engine HTTP API at {self.base_url}")
                health_data = response.json()
                log_info(f"   Service status: {health_data.get('status', 'unknown')}")
            else:
                log_error(f"❌ Workflow Engine health check failed: {response.status_code}")
                self.connected = False

        except Exception as e:
            log_error(f"❌ Failed to connect to Workflow Engine HTTP API: {e}")
            self.connected = False

    async def disconnect(self):
        """Close HTTP client connection."""
        if self.client:
            await self.client.aclose()
            self.client = None
            self.connected = False
            log_info("Disconnected from Workflow Engine HTTP API")

    async def _ensure_connected(self):
        """Ensure client is connected, reconnect if necessary."""
        if not self.connected or not self.client:
            await self.connect()

        if not self.connected:
            raise Exception("Failed to connect to Workflow Engine HTTP API")

    async def create_workflow(
        self,
        user_id: str,
        name: str,
        description: str,
        nodes: List[Dict[str, Any]],
        connections: Dict[str, Any],
        settings: Optional[Dict[str, Any]] = None,
        static_data: Optional[Dict[str, str]] = None,
        tags: Optional[List[str]] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new workflow."""
        await self._ensure_connected()

        try:
            log_info(f"📝 Creating workflow: {name} for user: {user_id}")

            # Prepare request data
            request_data = {
                "name": name,
                "description": description,
                "nodes": nodes,
                "connections": connections,
                "settings": settings
                or {"timeout": 300, "max_retries": 3, "parallel_execution": False},
                "static_data": static_data or {},
                "tags": tags or [],
                "user_id": user_id,
                "session_id": session_id,
            }

            response = await self.client.post("/v1/workflows", json=request_data)
            response.raise_for_status()

            result = response.json()
            log_info(
                f"✅ Workflow created successfully: {result.get('workflow', {}).get('id', 'unknown')}"
            )

            return result

        except httpx.HTTPStatusError as e:
            log_error(
                f"❌ HTTP error creating workflow: {e.response.status_code} - {e.response.text}"
            )
            raise Exception(f"Failed to create workflow: HTTP {e.response.status_code}")
        except Exception as e:
            log_error(f"❌ Error creating workflow: {str(e)}")
            raise

    async def get_workflow(self, workflow_id: str, user_id: str) -> Dict[str, Any]:
        """Get a workflow by ID."""
        await self._ensure_connected()

        try:
            log_info(f"📖 Getting workflow: {workflow_id} for user: {user_id}")

            response = await self.client.get(
                f"/v1/workflows/{workflow_id}", params={"user_id": user_id}
            )
            response.raise_for_status()

            result = response.json()
            found = result.get("found", False)

            if found:
                log_info(f"✅ Workflow retrieved successfully: {workflow_id}")
            else:
                log_warning(f"⚠️ Workflow not found: {workflow_id}")

            return result

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                log_warning(f"⚠️ Workflow not found: {workflow_id}")
                return {"found": False, "workflow": None, "message": "Workflow not found"}

            log_error(
                f"❌ HTTP error getting workflow: {e.response.status_code} - {e.response.text}"
            )
            raise Exception(f"Failed to get workflow: HTTP {e.response.status_code}")
        except Exception as e:
            log_error(f"❌ Error getting workflow: {str(e)}")
            raise

    async def update_workflow(
        self,
        workflow_id: str,
        user_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        nodes: Optional[List[Dict[str, Any]]] = None,
        connections: Optional[Dict[str, Any]] = None,
        settings: Optional[Dict[str, Any]] = None,
        static_data: Optional[Dict[str, str]] = None,
        tags: Optional[List[str]] = None,
        active: Optional[bool] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update an existing workflow."""
        await self._ensure_connected()

        try:
            log_info(f"📝 Updating workflow: {workflow_id} for user: {user_id}")

            # Prepare request data (only include non-None fields)
            request_data = {"user_id": user_id}

            if name is not None:
                request_data["name"] = name
            if description is not None:
                request_data["description"] = description
            if nodes is not None:
                request_data["nodes"] = nodes
            if connections is not None:
                request_data["connections"] = connections
            if settings is not None:
                request_data["settings"] = settings
            if static_data is not None:
                request_data["static_data"] = static_data
            if tags is not None:
                request_data["tags"] = tags
            if active is not None:
                request_data["active"] = active
            if session_id is not None:
                request_data["session_id"] = session_id

            response = await self.client.put(f"/v1/workflows/{workflow_id}", json=request_data)
            response.raise_for_status()

            result = response.json()
            log_info(f"✅ Workflow updated successfully: {workflow_id}")

            return result

        except httpx.HTTPStatusError as e:
            log_error(
                f"❌ HTTP error updating workflow: {e.response.status_code} - {e.response.text}"
            )
            raise Exception(f"Failed to update workflow: HTTP {e.response.status_code}")
        except Exception as e:
            log_error(f"❌ Error updating workflow: {str(e)}")
            raise

    async def delete_workflow(self, workflow_id: str, user_id: str) -> Dict[str, Any]:
        """Delete a workflow."""
        await self._ensure_connected()

        try:
            log_info(f"🗑️ Deleting workflow: {workflow_id} for user: {user_id}")

            response = await self.client.delete(
                f"/v1/workflows/{workflow_id}", params={"user_id": user_id}
            )
            response.raise_for_status()

            result = response.json()
            log_info(f"✅ Workflow deleted successfully: {workflow_id}")

            return result

        except httpx.HTTPStatusError as e:
            log_error(
                f"❌ HTTP error deleting workflow: {e.response.status_code} - {e.response.text}"
            )
            raise Exception(f"Failed to delete workflow: HTTP {e.response.status_code}")
        except Exception as e:
            log_error(f"❌ Error deleting workflow: {str(e)}")
            raise

    async def list_workflows(
        self,
        user_id: str,
        active_only: bool = False,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List workflows for a user."""
        await self._ensure_connected()

        try:
            log_info(f"📋 Listing workflows for user: {user_id}")

            params = {
                "user_id": user_id,
                "active_only": active_only,
                "limit": limit,
                "offset": offset,
            }

            if tags:
                params["tags"] = tags

            response = await self.client.get("/v1/workflows", params=params)
            response.raise_for_status()

            result = response.json()
            workflow_count = result.get("total_count", 0)
            log_info(f"✅ Listed {workflow_count} workflows for user: {user_id}")

            return result

        except httpx.HTTPStatusError as e:
            log_error(
                f"❌ HTTP error listing workflows: {e.response.status_code} - {e.response.text}"
            )
            raise Exception(f"Failed to list workflows: HTTP {e.response.status_code}")
        except Exception as e:
            log_error(f"❌ Error listing workflows: {str(e)}")
            raise

    async def execute_workflow(
        self,
        workflow_id: str,
        user_id: str,
        input_data: Optional[Dict[str, Any]] = None,
        execution_options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a workflow."""
        await self._ensure_connected()

        try:
            log_info(f"🚀 Executing workflow: {workflow_id} for user: {user_id}")

            request_data = {
                "workflow_id": workflow_id,
                "user_id": user_id,
                "input_data": input_data or {},
                "execution_options": execution_options or {},
            }

            response = await self.client.post(
                f"/v1/workflows/{workflow_id}/execute", json=request_data
            )
            response.raise_for_status()

            result = response.json()
            execution_id = result.get("execution_id", "unknown")
            log_info(f"✅ Workflow execution started: {execution_id}")

            return result

        except httpx.HTTPStatusError as e:
            log_error(
                f"❌ HTTP error executing workflow: {e.response.status_code} - {e.response.text}"
            )
            raise Exception(f"Failed to execute workflow: HTTP {e.response.status_code}")
        except Exception as e:
            log_error(f"❌ Error executing workflow: {str(e)}")
            raise

    async def get_execution_status(self, execution_id: str, user_id: str) -> Dict[str, Any]:
        """Get execution status."""
        await self._ensure_connected()

        try:
            log_info(f"📊 Getting execution status: {execution_id} for user: {user_id}")

            response = await self.client.get(
                f"/v1/workflows/executions/{execution_id}/status", params={"user_id": user_id}
            )
            response.raise_for_status()

            result = response.json()
            found = result.get("found", False)

            if found:
                execution = result.get("execution", {})
                status = execution.get("status", "unknown")
                progress = execution.get("progress_percentage", 0)
                log_info(f"✅ Execution status retrieved: {status} ({progress}%)")
            else:
                log_warning(f"⚠️ Execution not found: {execution_id}")

            return result

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                log_warning(f"⚠️ Execution not found: {execution_id}")
                return {"found": False, "execution": None, "message": "Execution not found"}

            log_error(
                f"❌ HTTP error getting execution status: {e.response.status_code} - {e.response.text}"
            )
            raise Exception(f"Failed to get execution status: HTTP {e.response.status_code}")
        except Exception as e:
            log_error(f"❌ Error getting execution status: {str(e)}")
            raise

    async def cancel_execution(
        self, execution_id: str, user_id: str, reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cancel a running execution."""
        await self._ensure_connected()

        try:
            log_info(f"⏹️ Cancelling execution: {execution_id} for user: {user_id}")

            request_data = {"execution_id": execution_id, "user_id": user_id, "reason": reason}

            response = await self.client.post(
                f"/v1/workflows/executions/{execution_id}/cancel", json=request_data
            )
            response.raise_for_status()

            result = response.json()
            log_info(f"✅ Execution cancelled successfully: {execution_id}")

            return result

        except httpx.HTTPStatusError as e:
            log_error(
                f"❌ HTTP error cancelling execution: {e.response.status_code} - {e.response.text}"
            )
            raise Exception(f"Failed to cancel execution: HTTP {e.response.status_code}")
        except Exception as e:
            log_error(f"❌ Error cancelling execution: {str(e)}")
            raise

    async def get_execution_history(
        self, user_id: str, workflow_id: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> Dict[str, Any]:
        """Get execution history."""
        await self._ensure_connected()

        try:
            log_info(f"📚 Getting execution history for user: {user_id}")

            params = {"user_id": user_id, "limit": limit, "offset": offset}

            if workflow_id:
                params["workflow_id"] = workflow_id

            response = await self.client.get("/v1/workflows/executions/history", params=params)
            response.raise_for_status()

            result = response.json()
            execution_count = result.get("total_count", 0)
            log_info(f"✅ Retrieved {execution_count} execution records for user: {user_id}")

            return result

        except httpx.HTTPStatusError as e:
            log_error(
                f"❌ HTTP error getting execution history: {e.response.status_code} - {e.response.text}"
            )
            raise Exception(f"Failed to get execution history: HTTP {e.response.status_code}")
        except Exception as e:
            log_error(f"❌ Error getting execution history: {str(e)}")
            raise

    async def validate_workflow(
        self, workflow_data: Dict[str, Any], strict_mode: bool = False
    ) -> Dict[str, Any]:
        """Validate a workflow definition."""
        await self._ensure_connected()

        try:
            log_info("✅ Validating workflow definition")

            request_data = {"workflow": workflow_data, "strict_mode": strict_mode}

            response = await self.client.post("/v1/workflows/validate", json=request_data)
            response.raise_for_status()

            result = response.json()
            validation_result = result.get("validation_result", {})
            is_valid = validation_result.get("valid", False)
            errors = validation_result.get("errors", [])
            warnings = validation_result.get("warnings", [])

            log_info(
                f"✅ Workflow validation completed: valid={is_valid}, errors={len(errors)}, warnings={len(warnings)}"
            )

            return result

        except httpx.HTTPStatusError as e:
            log_error(
                f"❌ HTTP error validating workflow: {e.response.status_code} - {e.response.text}"
            )
            raise Exception(f"Failed to validate workflow: HTTP {e.response.status_code}")
        except Exception as e:
            log_error(f"❌ Error validating workflow: {str(e)}")
            raise

    async def test_node(
        self, node_data: Dict[str, Any], user_id: str, input_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Test a single workflow node."""
        await self._ensure_connected()

        try:
            log_info(f"🧪 Testing node: {node_data.get('id', 'unknown')} for user: {user_id}")

            request_data = {"node": node_data, "input_data": input_data or {}, "user_id": user_id}

            response = await self.client.post("/v1/workflows/test-node", json=request_data)
            response.raise_for_status()

            result = response.json()
            success = result.get("success", False)
            log_info(f"✅ Node test completed: success={success}")

            return result

        except httpx.HTTPStatusError as e:
            log_error(f"❌ HTTP error testing node: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Failed to test node: HTTP {e.response.status_code}")
        except Exception as e:
            log_error(f"❌ Error testing node: {str(e)}")
            raise

    async def check_health(self) -> Dict[str, Any]:
        """Check service health."""
        try:
            if not self.client:
                await self.connect()

            response = await self.client.get("/health")
            response.raise_for_status()

            return response.json()

        except Exception as e:
            log_error(f"❌ Health check failed: {str(e)}")
            return {
                "status": "not_serving",
                "message": f"Health check failed: {str(e)}",
                "timestamp": int(datetime.now().timestamp()),
            }
