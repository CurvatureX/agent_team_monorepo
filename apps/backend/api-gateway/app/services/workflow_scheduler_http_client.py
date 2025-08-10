"""
HTTP Client for Workflow Scheduler Service
Provides HTTP/FastAPI calls to the workflow scheduler service
"""

import asyncio
from typing import Any, Dict, List, Optional

import httpx
from app.core.config import get_settings
from app.utils.logger import log_error, log_info

settings = get_settings()


class WorkflowSchedulerHTTPClient:
    """
    HTTP client for the Workflow Scheduler FastAPI service
    Handles trigger management and workflow scheduling operations
    """

    def __init__(self):
        self.base_url = settings.workflow_scheduler_http_url
        self.timeout = httpx.Timeout(30.0, connect=5.0)
        self.connected = False

    async def connect(self):
        """Test connection to workflow scheduler service"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/health")
                response.raise_for_status()
                self.connected = True
                log_info(f"✅ Connected to Workflow Scheduler at {self.base_url}")
        except Exception as e:
            log_error(f"❌ Failed to connect to Workflow Scheduler: {e}")
            self.connected = False
            raise

    async def close(self):
        """Close HTTP connection (no-op for HTTP)"""
        self.connected = False
        log_info("Closed Workflow Scheduler HTTP connection")

    async def trigger_manual_workflow(
        self,
        workflow_id: str,
        user_id: str = "system",
        confirmation: bool = False,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Manually trigger a workflow execution"""
        if not self.connected:
            await self.connect()

        try:
            request_data = {
                "confirmation": confirmation,
            }

            log_info(f"📨 Manual trigger request for workflow: {workflow_id} by user: {user_id}")

            headers = {}
            if trace_id:
                headers["X-Trace-ID"] = trace_id

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/triggers/workflows/{workflow_id}/manual",
                    json=request_data,
                    params={"user_id": user_id},
                    headers=headers,
                )
                response.raise_for_status()

                data = response.json()
                log_info(
                    f"✅ Manual trigger completed: {workflow_id}, "
                    f"execution_id: {data.get('execution_id', 'N/A')}, "
                    f"status: {data.get('status', 'unknown')}"
                )
                return data

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                # Handle confirmation required case
                try:
                    error_data = e.response.json()
                    if error_data.get("detail", {}).get("confirmation_required"):
                        log_info(f"⚠️ Confirmation required for workflow: {workflow_id}")
                        return {
                            "success": False,
                            "status": "confirmation_required",
                            "message": error_data["detail"]["message"],
                            "confirmation_required": True,
                            "trigger_data": error_data["detail"].get("trigger_data", {}),
                        }
                except Exception:
                    pass

            log_error(f"❌ HTTP error triggering manual workflow: {e.response.status_code}")
            return {"success": False, "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            log_error(f"❌ Error triggering manual workflow: {e}")
            return {"success": False, "error": str(e)}

    async def get_trigger_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get status of all triggers for a workflow"""
        if not self.connected:
            await self.connect()

        try:
            log_info(f"📨 Getting trigger status for workflow: {workflow_id}")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/triggers/workflows/{workflow_id}/status"
                )
                response.raise_for_status()

                data = response.json()
                log_info(f"✅ Retrieved trigger status for workflow: {workflow_id}")
                return data

        except httpx.HTTPStatusError as e:
            log_error(f"❌ HTTP error getting trigger status: {e.response.status_code}")
            return {"success": False, "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            log_error(f"❌ Error getting trigger status: {e}")
            return {"success": False, "error": str(e)}

    async def get_trigger_types(self) -> Dict[str, Any]:
        """Get all available trigger types"""
        if not self.connected:
            await self.connect()

        try:
            log_info("📨 Getting available trigger types")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/v1/triggers/types")
                response.raise_for_status()

                data = response.json()
                log_info("✅ Retrieved trigger types")
                return data

        except httpx.HTTPStatusError as e:
            log_error(f"❌ HTTP error getting trigger types: {e.response.status_code}")
            return {"success": False, "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            log_error(f"❌ Error getting trigger types: {e}")
            return {"success": False, "error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """Get health status of the workflow scheduler"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/health")
                response.raise_for_status()

                data = response.json()
                return {"success": True, "status": "healthy", "details": data}

        except httpx.HTTPStatusError as e:
            log_error(f"❌ HTTP error during health check: {e.response.status_code}")
            return {
                "success": False,
                "status": "unhealthy",
                "error": f"HTTP {e.response.status_code}",
            }
        except Exception as e:
            log_error(f"❌ Error during health check: {e}")
            return {"success": False, "status": "unreachable", "error": str(e)}


# Global HTTP client instance
workflow_scheduler_client = WorkflowSchedulerHTTPClient()


async def get_workflow_scheduler_client() -> WorkflowSchedulerHTTPClient:
    """Get workflow scheduler HTTP client instance"""
    return workflow_scheduler_client
