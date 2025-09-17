"""
Shared Workflow Lifecycle Utilities for Integration Tests

This module provides the WorkflowLifecycleManager class that handles
the complete workflow lifecycle for proper integration testing:

1. CREATE workflow via POST /v1/workflows
2. EXECUTE workflow via POST /v1/workflows/{id}/execute
3. MONITOR execution via GET /v1/executions/{id}
4. DELETE workflow via DELETE /v1/workflows/{id}

This replaces the old mocked approach with real API calls.
"""

import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4

import httpx

logger = logging.getLogger(__name__)


async def get_supabase_jwt_token() -> Optional[str]:
    """
    Get a JWT token from Supabase for authenticated requests.

    Returns:
        JWT token string or None if authentication fails
    """
    try:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
        test_email = os.getenv("TEST_USER_EMAIL", "daming.lu@starmates.ai")
        test_password = "test.1234!"

        if not supabase_url or not supabase_anon_key:
            logger.warning("Missing Supabase credentials for authentication")
            return None

        auth_url = f"{supabase_url}/auth/v1/token?grant_type=password"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                auth_url,
                headers={"apikey": supabase_anon_key, "Content-Type": "application/json"},
                json={"email": test_email, "password": test_password},
            )

            if response.status_code == 200:
                data = response.json()
                access_token = data.get("access_token")
                logger.info(f"✅ Successfully authenticated with Supabase")
                return access_token
            else:
                logger.error(
                    f"❌ Supabase authentication failed: {response.status_code} - {response.text}"
                )
                return None

    except Exception as e:
        logger.error(f"❌ Failed to get Supabase JWT token: {e}")
        return None


class WorkflowLifecycleManager:
    """
    Manages complete workflow lifecycle for integration testing.

    This class provides methods to create, execute, monitor, and delete
    workflows using real API endpoints instead of mocked definitions.
    """

    def __init__(self, app_client):
        self.app_client = app_client
        self.created_workflows: List[str] = []
        self.executions: List[str] = []
        self.auth_token: Optional[str] = None

    async def _ensure_authenticated(self):
        """Ensure we have a valid JWT token for authenticated requests."""
        if not self.auth_token:
            logger.info("🔑 Getting Supabase JWT token for authenticated requests...")
            self.auth_token = await get_supabase_jwt_token()
            if self.auth_token:
                logger.info("✅ Successfully obtained JWT token")
            else:
                logger.warning("⚠️ Failed to obtain JWT token - proceeding without authentication")

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for requests."""
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    async def create_workflow(self, workflow_definition: Dict[str, Any]) -> str:
        """
        Create a workflow via POST /v1/workflows API endpoint.

        Args:
            workflow_definition: Complete workflow definition with nodes and connections

        Returns:
            workflow_id: The ID of the created workflow

        Raises:
            AssertionError: If workflow creation fails
        """
        # Ensure we have authentication
        await self._ensure_authenticated()

        # Ensure workflow has an ID
        if "id" not in workflow_definition:
            workflow_definition["id"] = f"test-workflow-{uuid4().hex[:8]}"

        logger.info(f"Creating workflow: {workflow_definition['id']}")

        # Call real API endpoint with authentication
        # Clean potential problematic Unicode before JSON serialization
        try:
            from workflow_engine.utils.unicode_utils import ensure_utf8_safe_dict

            cleaned_workflow = ensure_utf8_safe_dict(workflow_definition)
        except Exception:
            cleaned_workflow = workflow_definition

        # Add user_id to the workflow if authentication is available
        if self.auth_token and "user_id" not in cleaned_workflow:
            # Extract user_id from JWT token payload if possible
            try:
                import base64
                import json

                # Decode JWT payload (middle part)
                payload_part = self.auth_token.split(".")[1]
                # Add padding if needed
                payload_part += "=" * (4 - len(payload_part) % 4)
                payload = json.loads(base64.b64decode(payload_part))
                user_id = payload.get("sub")  # 'sub' is the standard JWT claim for user ID
                if user_id:
                    cleaned_workflow["user_id"] = user_id
                    logger.info(f"🔑 Added user_id to workflow: {user_id}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to extract user_id from JWT: {e}")

        resp = await self.app_client.post(
            "/v1/workflows", json=cleaned_workflow, headers=self._get_auth_headers()
        )

        if resp.status_code != 200:
            error_detail = resp.text
            logger.error(f"Failed to create workflow: {resp.status_code} - {error_detail}")

            # If this is a configuration issue, provide helpful guidance
            if "SUPABASE_URL must be configured" in error_detail:
                raise AssertionError(
                    f"Workflow creation failed due to missing database configuration.\n"
                    f"This is expected for new lifecycle tests that use real API endpoints.\n"
                    f"To run these tests, configure Supabase environment variables:\n"
                    f"- SUPABASE_URL\n"
                    f"- SUPABASE_SECRET_KEY\n"
                    f"Response: {resp.status_code} - {error_detail}"
                )
            else:
                raise AssertionError(
                    f"Failed to create workflow: {resp.status_code} - {error_detail}"
                )

        data = resp.json()
        workflow_id = data.get("id")

        if not workflow_id:
            raise AssertionError(f"No workflow ID returned from creation: {data}")

        # Track for cleanup
        self.created_workflows.append(workflow_id)
        logger.info(f"✅ Created workflow: {workflow_id}")

        return workflow_id

    async def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get workflow definition via GET /v1/workflows/{id} API endpoint.

        Args:
            workflow_id: ID of the workflow to retrieve

        Returns:
            workflow: The workflow definition from database

        Raises:
            AssertionError: If workflow retrieval fails
        """
        # Ensure we have authentication
        await self._ensure_authenticated()

        logger.info(f"Retrieving workflow: {workflow_id}")

        resp = await self.app_client.get(
            f"/v1/workflows/{workflow_id}", headers=self._get_auth_headers()
        )

        if resp.status_code != 200:
            raise AssertionError(
                f"Failed to get workflow {workflow_id}: {resp.status_code} - {resp.text}"
            )

        data = resp.json()

        if not data.get("found"):
            raise AssertionError(f"Workflow not found: {workflow_id}")

        workflow = data.get("workflow", {})
        logger.info(
            f"✅ Retrieved workflow: {workflow_id} with {len(workflow.get('nodes', []))} nodes"
        )

        return workflow

    async def execute_workflow(
        self,
        workflow_id: str,
        trigger_data: Dict[str, Any],
        user_id: str = "test_user",
        async_execution: bool = False,
    ) -> str:
        """
        Execute workflow via POST /v1/workflows/{id}/execute API endpoint.

        Args:
            workflow_id: ID of workflow to execute
            trigger_data: Data to pass to workflow trigger
            user_id: User ID for execution
            async_execution: Whether to execute asynchronously

        Returns:
            execution_id: The ID of the created execution

        Raises:
            AssertionError: If workflow execution fails
        """
        # Ensure we have authentication
        await self._ensure_authenticated()

        logger.info(f"Executing workflow: {workflow_id} (async: {async_execution})")

        request_data = {
            "workflow_id": workflow_id,
            "user_id": user_id,
            "trigger_data": trigger_data,
            "async_execution": async_execution,
        }

        # Clean Unicode before sending request to avoid JSON surrogate issues
        try:
            from workflow_engine.utils.unicode_utils import ensure_utf8_safe_dict

            cleaned_request_data = ensure_utf8_safe_dict(request_data)
        except Exception:
            cleaned_request_data = request_data

        resp = await self.app_client.post(
            f"/v1/workflows/{workflow_id}/execute",
            json=cleaned_request_data,
            headers=self._get_auth_headers(),
        )

        if resp.status_code != 200:
            raise AssertionError(
                f"Failed to execute workflow {workflow_id}: {resp.status_code} - {resp.text}"
            )

        data = resp.json()
        execution_id = data.get("execution_id")

        if not execution_id:
            raise AssertionError(f"No execution ID returned from execution: {data}")

        # Track for monitoring
        self.executions.append(execution_id)
        logger.info(f"✅ Started execution: {execution_id}")

        return execution_id

    async def monitor_execution(
        self, execution_id: str, timeout_seconds: int = 30
    ) -> Dict[str, Any]:
        """
        Monitor execution until completion via GET /v1/executions/{id} API endpoint.

        Args:
            execution_id: ID of execution to monitor
            timeout_seconds: Maximum time to wait for completion

        Returns:
            execution_status: Final execution status and details

        Raises:
            TimeoutError: If execution doesn't complete within timeout
            AssertionError: If execution status retrieval fails
        """
        logger.info(f"Monitoring execution: {execution_id} (timeout: {timeout_seconds}s)")

        start_time = time.time()
        last_status = "UNKNOWN"

        while time.time() - start_time < timeout_seconds:
            resp = await self.app_client.get(
                f"/v1/executions/{execution_id}", headers=self._get_auth_headers()
            )

            if resp.status_code != 200:
                raise AssertionError(
                    f"Failed to get execution status {execution_id}: {resp.status_code} - {resp.text}"
                )

            data = resp.json()
            status = data.get("status", "").upper()

            # Log status changes
            if status != last_status:
                logger.info(f"📊 Execution {execution_id} status: {last_status} → {status}")
                last_status = status

            # Check if execution is complete
            if status in ["COMPLETED", "SUCCESS", "FAILED", "CANCELLED", "ERROR"]:
                logger.info(f"✅ Execution completed: {execution_id} with status {status}")
                # Normalize shape to include a boolean success field for assertions
                data["success"] = status in ["COMPLETED", "SUCCESS"]
                return data

            # Wait before checking again
            await asyncio.sleep(1)

        raise TimeoutError(
            f"Execution {execution_id} did not complete within {timeout_seconds} seconds. Last status: {last_status}"
        )

    async def execute_and_wait(
        self,
        workflow_id: str,
        trigger_data: Dict[str, Any],
        user_id: str = "test_user",
        timeout_seconds: int = 30,
    ) -> Dict[str, Any]:
        """
        Execute workflow and wait for completion (convenience method).

        This combines execute_workflow and monitor_execution for synchronous testing.

        Args:
            workflow_id: ID of workflow to execute
            trigger_data: Data to pass to workflow trigger
            user_id: User ID for execution
            timeout_seconds: Maximum time to wait for completion

        Returns:
            execution_status: Final execution status and details
        """
        execution_id = await self.execute_workflow(
            workflow_id, trigger_data, user_id, async_execution=False
        )
        return await self.monitor_execution(execution_id, timeout_seconds)

    async def delete_workflow(self, workflow_id: str) -> bool:
        """
        Delete workflow via DELETE /v1/workflows/{id} API endpoint.

        Args:
            workflow_id: ID of workflow to delete

        Returns:
            success: True if deletion succeeded

        Raises:
            AssertionError: If workflow deletion fails
        """
        # Ensure we have authentication
        await self._ensure_authenticated()

        logger.info(f"Deleting workflow: {workflow_id}")

        resp = await self.app_client.delete(
            f"/v1/workflows/{workflow_id}", headers=self._get_auth_headers()
        )

        if resp.status_code != 200:
            raise AssertionError(
                f"Failed to delete workflow {workflow_id}: {resp.status_code} - {resp.text}"
            )

        # Remove from tracking
        if workflow_id in self.created_workflows:
            self.created_workflows.remove(workflow_id)

        logger.info(f"✅ Deleted workflow: {workflow_id}")
        return True

    async def verify_workflow_deleted(self, workflow_id: str) -> bool:
        """
        Verify workflow is deleted by attempting to retrieve it.

        Args:
            workflow_id: ID of workflow to check

        Returns:
            is_deleted: True if workflow is not found (successfully deleted)
        """
        logger.info(f"Verifying deletion of workflow: {workflow_id}")

        resp = await self.app_client.get(
            f"/v1/workflows/{workflow_id}", headers=self._get_auth_headers()
        )

        if resp.status_code == 404:
            logger.info(f"✅ Verified workflow deleted: {workflow_id}")
            return True
        elif resp.status_code == 200:
            data = resp.json()
            if not data.get("found"):
                logger.info(f"✅ Verified workflow deleted: {workflow_id}")
                return True
            else:
                logger.warning(f"⚠️ Workflow still exists: {workflow_id}")
                return False
        else:
            logger.error(f"❌ Failed to verify deletion: {resp.status_code} - {resp.text}")
            return False

    async def cleanup_all(self) -> Dict[str, Any]:
        """
        Clean up all created workflows.

        Returns:
            cleanup_report: Summary of cleanup operations
        """
        cleanup_report = {"workflows_cleaned": 0, "workflows_failed": 0, "errors": []}

        logger.info(f"Cleaning up {len(self.created_workflows)} workflows")

        for workflow_id in self.created_workflows.copy():
            try:
                await self.delete_workflow(workflow_id)
                cleanup_report["workflows_cleaned"] += 1
            except Exception as e:
                cleanup_report["workflows_failed"] += 1
                cleanup_report["errors"].append(f"Failed to cleanup {workflow_id}: {str(e)}")
                logger.error(f"Failed to cleanup workflow {workflow_id}: {e}")

        logger.info(
            f"Cleanup completed: {cleanup_report['workflows_cleaned']} cleaned, {cleanup_report['workflows_failed']} failed"
        )
        return cleanup_report

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about lifecycle operations.

        Returns:
            stats: Current statistics
        """
        return {
            "workflows_created": len(self.created_workflows),
            "executions_started": len(self.executions),
            "created_workflow_ids": self.created_workflows.copy(),
            "execution_ids": self.executions.copy(),
        }


def create_lifecycle_manager(app_client) -> WorkflowLifecycleManager:
    """
    Factory function to create a WorkflowLifecycleManager.

    Args:
        app_client: HTTP client for API calls

    Returns:
        manager: Configured lifecycle manager
    """
    return WorkflowLifecycleManager(app_client)


async def execute_full_workflow_lifecycle(
    app_client,
    workflow_definition: Dict[str, Any],
    trigger_data: Dict[str, Any],
    timeout_seconds: int = 30,
) -> Dict[str, Any]:
    """
    Execute complete workflow lifecycle in one function call.

    This is a convenience function that performs:
    1. CREATE workflow
    2. EXECUTE workflow
    3. MONITOR execution
    4. DELETE workflow

    Args:
        app_client: HTTP client for API calls
        workflow_definition: Complete workflow definition
        trigger_data: Data for workflow execution
        timeout_seconds: Maximum time to wait for execution

    Returns:
        lifecycle_result: Complete results of lifecycle operations
    """
    manager = create_lifecycle_manager(app_client)

    try:
        # 1. CREATE
        workflow_id = await manager.create_workflow(workflow_definition)

        # 2. EXECUTE & MONITOR
        execution_result = await manager.execute_and_wait(
            workflow_id, trigger_data, timeout_seconds=timeout_seconds
        )

        # 3. DELETE
        await manager.delete_workflow(workflow_id)

        # 4. VERIFY DELETION
        is_deleted = await manager.verify_workflow_deleted(workflow_id)

        return {
            "success": True,
            "workflow_id": workflow_id,
            "execution_id": execution_result.get("execution_id"),
            "execution_status": execution_result.get("status"),
            "execution_result": execution_result,
            "workflow_deleted": is_deleted,
            "lifecycle_complete": True,
        }

    except Exception as e:
        # Ensure cleanup even if test fails
        await manager.cleanup_all()

        return {
            "success": False,
            "error": str(e),
            "lifecycle_complete": False,
            "cleanup_attempted": True,
        }
