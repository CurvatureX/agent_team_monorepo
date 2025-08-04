"""
HTTP Client for Workflow Engine Service
Replaces the gRPC client with HTTP/FastAPI calls
"""

import asyncio
from typing import Any, Dict, List, Optional

import httpx
from app.core.config import get_settings
from app.utils.logger import log_error, log_info

settings = get_settings()


class WorkflowEngineHTTPClient:
    """
    HTTP client for the Workflow Engine FastAPI service
    Replaces the gRPC WorkflowService interface with HTTP calls
    """

    def __init__(self):
        self.base_url = (
            settings.WORKFLOW_ENGINE_URL or f"http://{settings.WORKFLOW_ENGINE_HOST}:8002"
        )
        self.timeout = httpx.Timeout(30.0, connect=5.0)
        self.connected = False

    async def connect(self):
        """Test connection to workflow engine service"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/health")
                response.raise_for_status()
                self.connected = True
                log_info(f"✅ Connected to Workflow Engine at {self.base_url}")
        except Exception as e:
            log_error(f"❌ Failed to connect to Workflow Engine: {e}")
            self.connected = False
            raise

    async def close(self):
        """Close HTTP connection (no-op for HTTP)"""
        self.connected = False
        log_info("Closed Workflow Engine HTTP connection")

    async def list_all_node_templates(
        self,
        category_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        include_system_templates: bool = True,
    ) -> List[Dict[str, Any]]:
        """List all available node templates via HTTP"""
        if not self.connected:
            await self.connect()

        try:
            # Prepare query parameters
            params = {"include_system_templates": include_system_templates}
            if category_filter:
                params["category_filter"] = category_filter
            if type_filter:
                params["type_filter"] = type_filter

            log_info(f"📨 HTTP request to {self.base_url}/v1/workflows/node-templates")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/v1/workflows/node-templates", params=params)
                response.raise_for_status()

                data = response.json()
                # The workflow engine returns the array directly
                templates = data if isinstance(data, list) else data.get("node_templates", [])
                log_info(f"✅ Retrieved {len(templates)} node templates")
                return templates

        except httpx.HTTPStatusError as e:
            log_error(f"❌ HTTP error listing node templates: {e.response.status_code}")
            return []
        except Exception as e:
            log_error(f"❌ Error listing node templates: {e}")
            return []

    async def create_workflow(
        self,
        name: str,
        description: Optional[str] = None,
        nodes: List[Dict[str, Any]] = None,
        connections: Dict[str, Any] = None,
        settings: Optional[Dict[str, Any]] = None,
        static_data: Optional[Dict[str, str]] = None,
        tags: Optional[List[str]] = None,
        user_id: str = "anonymous",
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new workflow via HTTP"""
        if not self.connected:
            await self.connect()

        try:
            request_data = {
                "name": name,
                "description": description,
                "nodes": nodes or [],
                "connections": connections or {},
                "settings": settings or {},
                "static_data": static_data or {},
                "tags": tags or [],
                "user_id": user_id,
                "session_id": session_id,
            }

            log_info(f"📨 HTTP request to create workflow: {name}")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/v1/workflows", json=request_data)
                response.raise_for_status()

                data = response.json()
                log_info(f"✅ Created workflow: {data.get('workflow', {}).get('id', 'unknown')}")
                return data

        except httpx.HTTPStatusError as e:
            log_error(f"❌ HTTP error creating workflow: {e.response.status_code}")
            return {"success": False, "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            log_error(f"❌ Error creating workflow: {e}")
            return {"success": False, "error": str(e)}

    async def get_workflow(self, workflow_id: str, user_id: str) -> Dict[str, Any]:
        """Get workflow by ID via HTTP"""
        if not self.connected:
            await self.connect()

        try:
            log_info(f"📨 HTTP request to get workflow: {workflow_id}")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/v1/workflows/{workflow_id}", params={"user_id": user_id}
                )
                response.raise_for_status()

                data = response.json()
                log_info(f"✅ Retrieved workflow: {workflow_id}")
                return data

        except httpx.HTTPStatusError as e:
            log_error(f"❌ HTTP error getting workflow: {e.response.status_code}")
            return {"success": False, "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            log_error(f"❌ Error getting workflow: {e}")
            return {"success": False, "error": str(e)}

    async def execute_workflow(
        self, workflow_id: str, user_id: str, input_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute workflow via HTTP"""
        if not self.connected:
            await self.connect()

        try:
            request_data = {
                "workflow_id": workflow_id,
                "user_id": user_id,
                "input_data": input_data or {},
            }

            log_info(f"📨 HTTP request to execute workflow: {workflow_id}")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/v1/workflows/{workflow_id}/execute", json=request_data
                )
                response.raise_for_status()

                data = response.json()
                log_info(f"✅ Executed workflow: {workflow_id}")
                return data

        except httpx.HTTPStatusError as e:
            log_error(f"❌ HTTP error executing workflow: {e.response.status_code}")
            return {"success": False, "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            log_error(f"❌ Error executing workflow: {e}")
            return {"success": False, "error": str(e)}

    async def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Get execution status via HTTP"""
        if not self.connected:
            await self.connect()

        try:
            log_info(f"📨 HTTP request to get execution status: {execution_id}")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/v1/executions/{execution_id}")
                response.raise_for_status()

                data = response.json()
                log_info(f"✅ Retrieved execution status: {execution_id}")
                return data

        except httpx.HTTPStatusError as e:
            log_error(f"❌ HTTP error getting execution status: {e.response.status_code}")
            return {"success": False, "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            log_error(f"❌ Error getting execution status: {e}")
            return {"success": False, "error": str(e)}

    async def cancel_execution(self, execution_id: str) -> Dict[str, Any]:
        """Cancel execution via HTTP"""
        if not self.connected:
            await self.connect()

        try:
            log_info(f"📨 HTTP request to cancel execution: {execution_id}")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/v1/executions/{execution_id}/cancel")
                response.raise_for_status()

                data = response.json()
                log_info(f"✅ Cancelled execution: {execution_id}")
                return data

        except httpx.HTTPStatusError as e:
            log_error(f"❌ HTTP error cancelling execution: {e.response.status_code}")
            return {"success": False, "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            log_error(f"❌ Error cancelling execution: {e}")
            return {"success": False, "error": str(e)}

    async def get_execution_history(
        self, workflow_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get execution history for a workflow via HTTP"""
        if not self.connected:
            await self.connect()

        try:
            log_info(f"📨 HTTP request to get execution history: {workflow_id}")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/v1/workflows/{workflow_id}/executions",
                    params={"limit": limit},
                )
                response.raise_for_status()

                data = response.json()
                log_info(f"✅ Retrieved execution history: {workflow_id}")
                return data

        except httpx.HTTPStatusError as e:
            log_error(f"❌ HTTP error getting execution history: {e.response.status_code}")
            return []
        except Exception as e:
            log_error(f"❌ Error getting execution history: {e}")
            return []

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
    ) -> Dict[str, Any]:
        """Update workflow via HTTP"""
        if not self.connected:
            await self.connect()

        try:
            # Build update data - only include non-None values
            update_data = {"user_id": user_id}
            if name is not None:
                update_data["name"] = name
            if description is not None:
                update_data["description"] = description
            if nodes is not None:
                update_data["nodes"] = nodes
            if connections is not None:
                update_data["connections"] = connections
            if settings is not None:
                update_data["settings"] = settings
            if static_data is not None:
                update_data["static_data"] = static_data
            if tags is not None:
                update_data["tags"] = tags
            if active is not None:
                update_data["active"] = active

            log_info(f"📨 HTTP request to update workflow: {workflow_id}")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(
                    f"{self.base_url}/v1/workflows/{workflow_id}", json=update_data
                )
                response.raise_for_status()

                data = response.json()
                log_info(f"✅ Updated workflow: {workflow_id}")
                return data

        except httpx.HTTPStatusError as e:
            log_error(f"❌ HTTP error updating workflow: {e.response.status_code}")
            return {"success": False, "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            log_error(f"❌ Error updating workflow: {e}")
            return {"success": False, "error": str(e)}

    async def delete_workflow(self, workflow_id: str, user_id: str) -> Dict[str, Any]:
        """Delete workflow via HTTP"""
        if not self.connected:
            await self.connect()

        try:
            log_info(f"📨 HTTP request to delete workflow: {workflow_id}")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(
                    f"{self.base_url}/v1/workflows/{workflow_id}", params={"user_id": user_id}
                )
                response.raise_for_status()

                data = response.json()
                log_info(f"✅ Deleted workflow: {workflow_id}")
                return data

        except httpx.HTTPStatusError as e:
            log_error(f"❌ HTTP error deleting workflow: {e.response.status_code}")
            return {"success": False, "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            log_error(f"❌ Error deleting workflow: {e}")
            return {"success": False, "error": str(e)}

    async def list_workflows(
        self,
        user_id: str,
        active_only: bool = True,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List workflows via HTTP"""
        if not self.connected:
            await self.connect()

        try:
            # Build query parameters
            params = {
                "user_id": user_id,
                "active_only": active_only,
                "limit": limit,
                "offset": offset,
            }
            if tags:
                params["tags"] = ",".join(tags)

            log_info(f"📨 HTTP request to list workflows for user: {user_id}")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/v1/workflows", params=params)
                response.raise_for_status()

                data = response.json()
                log_info(f"✅ Listed workflows for user: {user_id}")
                return data

        except httpx.HTTPStatusError as e:
            log_error(f"❌ HTTP error listing workflows: {e.response.status_code}")
            return {"workflows": [], "total_count": 0, "has_more": False}
        except Exception as e:
            log_error(f"❌ Error listing workflows: {e}")
            return {"workflows": [], "total_count": 0, "has_more": False}


# Global HTTP client instance
workflow_engine_client = WorkflowEngineHTTPClient()


async def get_workflow_engine_client() -> WorkflowEngineHTTPClient:
    """Get workflow engine HTTP client instance"""
    return workflow_engine_client
