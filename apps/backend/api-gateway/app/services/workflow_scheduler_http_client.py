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
        # Connection pool for better performance
        self._client = None
        self._limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with connection pooling"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                limits=self._limits,
                http2=True,  # Enable HTTP/2 for multiplexing
            )
        return self._client

    async def connect(self):
        """Test connection to workflow scheduler service"""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/health")
            response.raise_for_status()
            self.connected = True
            log_info(f"✅ Connected to Workflow Scheduler at {self.base_url}")
        except Exception as e:
            log_error(f"❌ Failed to connect to Workflow Scheduler: {e}")
            self.connected = False
            raise

    async def close(self):
        """Close HTTP connection and client"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        self.connected = False
        log_info("Closed Workflow Scheduler HTTP connection")

    async def trigger_manual_workflow(
        self,
        workflow_id: str,
        user_id: str = "system",
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Manually trigger a workflow execution"""
        if not self.connected:
            await self.connect()

        try:
            request_data = {}

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

    async def deploy_workflow(
        self,
        workflow_id: str,
        workflow_spec: Dict[str, Any],
        user_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Deploy a workflow with its trigger configuration"""
        if not self.connected:
            await self.connect()

        try:
            # Ensure user_id is included in workflow_spec for OAuth resolution
            enhanced_workflow_spec = workflow_spec.copy()
            if user_id:
                enhanced_workflow_spec["user_id"] = user_id
                log_info(f"📨 Deploy workflow request for: {workflow_id} (user: {user_id})")
            else:
                log_info(f"📨 Deploy workflow request for: {workflow_id}")

            request_data = {
                "workflow_spec": enhanced_workflow_spec,
            }

            headers = {}
            if trace_id:
                headers["X-Trace-ID"] = trace_id

            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/api/v1/deployment/workflows/{workflow_id}/deploy",
                json=request_data,
                headers=headers,
            )
            response.raise_for_status()

            data = response.json()
            log_info(
                f"✅ Workflow deployment completed: {workflow_id}, "
                f"deployment_id: {data.get('deployment_id', 'N/A')}, "
                f"status: {data.get('status', 'unknown')}"
            )
            return data

        except httpx.HTTPStatusError as e:
            # Try to extract detailed error message from response
            error_detail = f"HTTP {e.response.status_code}"
            try:
                error_response = e.response.json()
                if "detail" in error_response:
                    error_detail = error_response["detail"]
                elif "message" in error_response:
                    error_detail = error_response["message"]
                else:
                    error_detail = str(error_response)
            except Exception:
                # Fallback to text response if JSON parsing fails
                try:
                    error_detail = e.response.text or error_detail
                except Exception:
                    pass

            log_error(f"❌ HTTP error deploying workflow: {e.response.status_code} - {error_detail}")
            return {"success": False, "error": error_detail}
        except Exception as e:
            log_error(f"❌ Error deploying workflow: {e}")
            return {"success": False, "error": str(e)}

    async def undeploy_workflow(
        self,
        workflow_id: str,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Undeploy a workflow and cleanup its triggers"""
        if not self.connected:
            await self.connect()

        try:
            log_info(f"📨 Undeploy workflow request for: {workflow_id}")

            headers = {}
            if trace_id:
                headers["X-Trace-ID"] = trace_id

            client = await self._get_client()
            response = await client.delete(
                f"{self.base_url}/api/v1/deployment/workflows/{workflow_id}/undeploy",
                headers=headers,
            )
            response.raise_for_status()

            data = response.json()
            log_info(f"✅ Workflow undeployed: {workflow_id}")
            return data

        except httpx.HTTPStatusError as e:
            # Try to extract detailed error message from response
            error_detail = f"HTTP {e.response.status_code}"
            try:
                error_response = e.response.json()
                if "detail" in error_response:
                    error_detail = error_response["detail"]
                elif "message" in error_response:
                    error_detail = error_response["message"]
                else:
                    error_detail = str(error_response)
            except Exception:
                # Fallback to text response if JSON parsing fails
                try:
                    error_detail = e.response.text or error_detail
                except Exception:
                    pass

            log_error(
                f"❌ HTTP error undeploying workflow: {e.response.status_code} - {error_detail}"
            )
            return {"success": False, "error": error_detail}
        except Exception as e:
            log_error(f"❌ Error undeploying workflow: {e}")
            return {"success": False, "error": str(e)}

    async def get_deployment_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get deployment status for a workflow"""
        if not self.connected:
            await self.connect()

        try:
            log_info(f"📨 Getting deployment status for workflow: {workflow_id}")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/deployment/workflows/{workflow_id}/status"
                )
                response.raise_for_status()

                data = response.json()
                log_info(f"✅ Retrieved deployment status for workflow: {workflow_id}")
                return data

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                log_info(f"⚠️ Workflow deployment not found: {workflow_id}")
                return {"success": False, "error": "Deployment not found", "status_code": 404}
            log_error(f"❌ HTTP error getting deployment status: {e.response.status_code}")
            return {"success": False, "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            log_error(f"❌ Error getting deployment status: {e}")
            return {"success": False, "error": str(e)}

    async def trigger_workflow_execution(
        self,
        workflow_id: str,
        trigger_metadata: Dict[str, Any],
        input_data: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Trigger a workflow execution with custom metadata and input data"""
        if not self.connected:
            await self.connect()

        try:
            log_info(
                f"📨 Triggering workflow execution: {workflow_id} with metadata: "
                f"{trigger_metadata.get('trigger_type', 'unknown')}"
            )

            request_data = {
                "trigger_metadata": trigger_metadata,
                "input_data": input_data or {},
            }

            headers = {}
            if trace_id:
                headers["X-Trace-ID"] = trace_id

            params = {}
            if user_id:
                params["user_id"] = user_id

            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/api/v1/executions/workflows/{workflow_id}/trigger",
                json=request_data,
                params=params,
                headers=headers,
            )
            response.raise_for_status()

            data = response.json()
            log_info(
                f"✅ Workflow execution triggered: {workflow_id}, "
                f"execution_id: {data.get('execution_id', 'N/A')}"
            )
            return data

        except httpx.HTTPStatusError as e:
            # Try to extract detailed error message from response
            error_detail = f"HTTP {e.response.status_code}"
            try:
                error_response = e.response.json()
                if "detail" in error_response:
                    error_detail = error_response["detail"]
                elif "message" in error_response:
                    error_detail = error_response["message"]
                else:
                    error_detail = str(error_response)
            except Exception:
                # Fallback to text response if JSON parsing fails
                try:
                    error_detail = e.response.text or error_detail
                except Exception:
                    pass

            log_error(
                f"❌ HTTP error triggering workflow execution: {e.response.status_code} - {error_detail}"
            )
            return {"success": False, "error": error_detail}
        except Exception as e:
            log_error(f"❌ Error triggering workflow execution: {e}")
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
