"""
Workflow Engine Client for API integration
Handles communication with the workflow_engine service
"""

import json
import logging
from typing import Any, Dict, Optional

import httpx
from httpx import AsyncClient, Response

from workflow_agent.core.config import settings

logger = logging.getLogger(__name__)


class WorkflowEngineClient:
    """Client for interacting with workflow engine API"""

    def __init__(self):
        self.base_url = settings.WORKFLOW_ENGINE_URL
        self.timeout = settings.WORKFLOW_ENGINE_TIMEOUT
        logger.info(f"WorkflowEngineClient initialized with URL: {self.base_url}")

    async def create_workflow(
        self, workflow_data: Dict[str, Any], user_id: str = "test_user", session_id: str = None
    ) -> Dict[str, Any]:
        """
        Create a workflow in the workflow engine

        Args:
            workflow_data: The workflow JSON structure from workflow generation node
            user_id: User ID for workflow ownership

        Returns:
            Created workflow data including workflow_id
        """
        async with AsyncClient(timeout=self.timeout) as client:
            try:
                # Convert parameters to correct types for workflow engine
                # Make a deep copy to avoid modifying original data
                import copy

                workflow_copy = copy.deepcopy(workflow_data)
                nodes = workflow_copy.get("nodes", [])
                for node in nodes:
                    # Validate node type format - workflow_engine expects uppercase types with _NODE suffix
                    if "type" in node:
                        node_type = node["type"]
                        logger.info(f"Original node type: {node_type}")

                        # Handle node types with dots (e.g., "TRIGGER_NODE.TRIGGER_SCHEDULE")
                        # This format should not normally appear from LLM, but handle it just in case
                        if "." in node_type:
                            # Split the type
                            parts = node_type.split(".")
                            base_type = parts[0]
                            sub_type = parts[1] if len(parts) > 1 else None

                            # Workflow engine expects uppercase types, just use the base type
                            node["type"] = base_type

                            # The subtype should already be in the node's subtype field
                            # Only add to node if missing
                            if sub_type and "subtype" not in node:
                                node["subtype"] = sub_type

                            logger.info(
                                f"Handled dotted type: {node_type} -> type={base_type}, subtype={sub_type}"
                            )
                        else:
                            # Workflow engine expects uppercase node types with _NODE suffix
                            # LLM should already be outputting correct format from MCP tools
                            # No mapping needed - keep the original type
                            logger.info(f"Node type kept as-is: {node_type}")

                    # Ensure credentials is a dict, not None
                    if "credentials" not in node or node.get("credentials") is None:
                        node["credentials"] = {}

                    # Fix retry_policy if needed
                    if "retry_policy" in node:
                        retry = node["retry_policy"]
                        if isinstance(retry, dict):
                            if "max_tries" in retry and isinstance(
                                retry["max_tries"], (int, float)
                            ):
                                if retry["max_tries"] < 1:
                                    retry["max_tries"] = 1

                    # Note: Template variables like {{payload.number}} are now handled by
                    # the workflow_engine's template resolver, so we don't need to convert them here

                    if "parameters" in node and node["parameters"]:
                        # Smart parameter type handling based on common patterns
                        for key, value in list(node["parameters"].items()):
                            # Skip if already correct type
                            if value is None:
                                # Remove None values
                                del node["parameters"][key]
                                continue

                            # Handle string values that might need conversion
                            if isinstance(value, str):
                                # Keep template variables as strings - they'll be resolved by workflow_engine
                                # Templates can be: {{var}}, ${var}, <%var%> or other patterns
                                if any(
                                    pattern in value for pattern in ["{{", "}}", "${", "<%", "%>"]
                                ):
                                    # This is a template variable, keep as string
                                    # The workflow_engine's template resolver will handle it at runtime
                                    continue

                                # Boolean conversion (only for non-template strings)
                                if value.lower() in ["true", "false"]:
                                    node["parameters"][key] = value.lower() == "true"
                                # JSON object/array detection
                                elif value.startswith(("{", "[")) and value.endswith(("}", "]")):
                                    try:
                                        node["parameters"][key] = json.loads(value)
                                    except json.JSONDecodeError:
                                        pass  # Keep as string if not valid JSON
                                # Number detection (only for literal numbers, not templates)
                                elif key in [
                                    "timeout",
                                    "max_tries",
                                    "wait_between_tries",
                                    "milestone",
                                ]:
                                    try:
                                        # Try integer first
                                        if "." not in value:
                                            node["parameters"][key] = int(value)
                                        else:
                                            node["parameters"][key] = float(value)
                                    except ValueError:
                                        pass  # Keep as string if not a number

                            # Handle dict that should be JSON string (reverse case)
                            elif isinstance(value, dict) and key in ["event_config", "headers"]:
                                # Some fields expect JSON strings, not objects
                                node["parameters"][key] = json.dumps(value)

                # Fix settings if needed
                settings = workflow_copy.get("settings", {})
                if settings:
                    # Ensure timeout is at least 60
                    if "timeout" in settings and isinstance(settings["timeout"], (int, float)):
                        if settings["timeout"] < 60:
                            settings["timeout"] = 60

                # Prepare the request data according to CreateWorkflowRequest model
                request_data = {
                    "name": workflow_copy.get("name", "Automated Workflow"),
                    "description": workflow_copy.get("description", ""),
                    "nodes": nodes,  # Use the modified nodes
                    "connections": workflow_copy.get("connections", {}),
                    "settings": settings if settings else None,
                    "static_data": workflow_copy.get("static_data", {}),
                    "tags": workflow_copy.get("tags", ["debug", "test"]),
                    "user_id": user_id,
                }

                # Add session_id if provided
                if session_id:
                    request_data["session_id"] = session_id

                logger.info(
                    f"Creating workflow in engine - Total nodes: {len(request_data.get('nodes', []))}"
                )
                logger.info(
                    f"📦 Full Workflow Creation Request: {json.dumps(request_data, indent=2)}"
                )

                response = await client.post(
                    f"{self.base_url}/v1/workflows",
                    json=request_data,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(
                        f"Workflow created successfully: {result.get('workflow', {}).get('id')}"
                    )
                    return result
                else:
                    error_msg = (
                        f"Failed to create workflow: {response.status_code} - {response.text}"
                    )
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
                        "status_code": response.status_code,
                    }

            except httpx.TimeoutException:
                error_msg = f"Timeout creating workflow after {self.timeout}s"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
            except Exception as e:
                error_msg = f"Error creating workflow: {str(e)}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}

    async def execute_workflow(
        self,
        workflow_id: str,
        trigger_data: Optional[Dict[str, Any]] = None,
        user_id: str = "test_user",
    ) -> Dict[str, Any]:
        """
        Execute a workflow in the workflow engine

        Args:
            workflow_id: ID of the workflow to execute
            trigger_data: Input data for workflow execution
            user_id: User ID for execution context

        Returns:
            Execution result including execution_id and status
        """
        async with AsyncClient(timeout=self.timeout) as client:
            try:
                # Prepare execution request
                # Note: trigger_data should already have all values as strings from TestDataGenerator
                request_data = {
                    "workflow_id": workflow_id,
                    "trigger_data": trigger_data or {},
                    "user_id": user_id,
                }

                logger.info(f"Executing workflow: {workflow_id}")
                logger.info(f"📦 Execute Request Data: {json.dumps(request_data, indent=2)}")

                response = await client.post(
                    f"{self.base_url}/v1/workflows/{workflow_id}/execute",
                    json=request_data,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Workflow execution started: {result.get('execution_id')}")
                    return result
                else:
                    error_msg = (
                        f"Failed to execute workflow: {response.status_code} - {response.text}"
                    )
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
                        "status_code": response.status_code,
                    }

            except httpx.TimeoutException:
                error_msg = f"Timeout executing workflow after {self.timeout}s"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
            except Exception as e:
                error_msg = f"Error executing workflow: {str(e)}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}

    async def get_workflow(self, workflow_id: str, user_id: str = "test_user") -> Dict[str, Any]:
        """
        Get an existing workflow from the workflow engine

        Args:
            workflow_id: ID of the workflow to retrieve
            user_id: User ID for authorization

        Returns:
            Workflow data or error response
        """
        async with AsyncClient(timeout=self.timeout) as client:
            try:
                logger.info(f"Fetching workflow: {workflow_id} for user: {user_id}")
                
                response = await client.get(
                    f"{self.base_url}/v1/workflows/{workflow_id}",
                    params={"user_id": user_id},
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("found"):
                        logger.info(f"Workflow {workflow_id} retrieved successfully")
                        return {
                            "success": True,
                            "workflow": result.get("workflow"),
                        }
                    else:
                        logger.warning(f"Workflow {workflow_id} not found")
                        return {
                            "success": False,
                            "error": "Workflow not found",
                            "status_code": 404,
                        }
                else:
                    error_msg = f"Failed to get workflow: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
                        "status_code": response.status_code,
                    }

            except httpx.TimeoutException:
                error_msg = f"Timeout getting workflow after {self.timeout}s"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
            except Exception as e:
                error_msg = f"Error getting workflow: {str(e)}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}

    async def update_workflow(
        self, workflow_id: str, workflow_data: Dict[str, Any], user_id: str = "test_user"
    ) -> Dict[str, Any]:
        """
        Update an existing workflow in the workflow engine

        Args:
            workflow_id: ID of the workflow to update
            workflow_data: The updated workflow JSON structure
            user_id: User ID for authorization

        Returns:
            Updated workflow data including workflow_id
        """
        async with AsyncClient(timeout=self.timeout) as client:
            try:
                # Convert parameters to correct types (same as create_workflow)
                import copy

                workflow_copy = copy.deepcopy(workflow_data)
                nodes = workflow_copy.get("nodes", [])
                
                # Apply the same node processing as create_workflow
                for node in nodes:
                    # Handle node type format
                    if "type" in node:
                        node_type = node["type"]
                        if "." in node_type:
                            parts = node_type.split(".")
                            base_type = parts[0]
                            sub_type = parts[1] if len(parts) > 1 else None
                            node["type"] = base_type
                            if sub_type and "subtype" not in node:
                                node["subtype"] = sub_type

                    # Ensure credentials is a dict
                    if "credentials" not in node or node.get("credentials") is None:
                        node["credentials"] = {}

                    # Fix retry_policy if needed
                    if "retry_policy" in node:
                        retry = node["retry_policy"]
                        if isinstance(retry, dict):
                            if "max_tries" in retry and isinstance(retry["max_tries"], (int, float)):
                                if retry["max_tries"] < 1:
                                    retry["max_tries"] = 1

                    # Smart parameter type handling
                    if "parameters" in node and node["parameters"]:
                        for key, value in list(node["parameters"].items()):
                            if value is None:
                                del node["parameters"][key]
                                continue

                            if isinstance(value, str):
                                # Keep template variables as strings
                                if any(pattern in value for pattern in ["{{", "}}", "${", "<%", "%>"]):
                                    continue

                                # Boolean conversion
                                if value.lower() in ["true", "false"]:
                                    node["parameters"][key] = value.lower() == "true"
                                # JSON object/array detection
                                elif value.startswith(("{", "[")) and value.endswith(("}", "]")):
                                    try:
                                        node["parameters"][key] = json.loads(value)
                                    except json.JSONDecodeError:
                                        pass
                                # Number detection
                                elif key in ["timeout", "max_tries", "wait_between_tries", "milestone"]:
                                    try:
                                        if "." not in value:
                                            node["parameters"][key] = int(value)
                                        else:
                                            node["parameters"][key] = float(value)
                                    except ValueError:
                                        pass

                            # Handle dict that should be JSON string
                            elif isinstance(value, dict) and key in ["event_config", "headers"]:
                                node["parameters"][key] = json.dumps(value)

                # Fix settings if needed
                settings = workflow_copy.get("settings", {})
                if settings:
                    if "timeout" in settings and isinstance(settings["timeout"], (int, float)):
                        if settings["timeout"] < 60:
                            settings["timeout"] = 60

                # Prepare the update request data
                request_data = {
                    "workflow_id": workflow_id,
                    "user_id": user_id,
                    "name": workflow_copy.get("name"),
                    "description": workflow_copy.get("description"),
                    "nodes": nodes,
                    "connections": workflow_copy.get("connections"),
                    "settings": settings if settings else None,
                    "tags": workflow_copy.get("tags"),
                }

                logger.info(f"Updating workflow {workflow_id} in engine")
                logger.info(f"📦 Update Request Data: {json.dumps(request_data, indent=2)}")

                response = await client.put(
                    f"{self.base_url}/v1/workflows/{workflow_id}",
                    json=request_data,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Workflow {workflow_id} updated successfully")
                    return result
                else:
                    error_msg = f"Failed to update workflow: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
                        "status_code": response.status_code,
                    }

            except httpx.TimeoutException:
                error_msg = f"Timeout updating workflow after {self.timeout}s"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
            except Exception as e:
                error_msg = f"Error updating workflow: {str(e)}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}

    async def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """
        Get the status of a workflow execution

        Args:
            execution_id: ID of the execution to check

        Returns:
            Execution status and results
        """
        async with AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(f"{self.base_url}/v1/executions/{execution_id}")

                if response.status_code == 200:
                    return response.json()
                else:
                    error_msg = f"Failed to get execution status: {response.status_code}"
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
                        "status_code": response.status_code,
                    }

            except Exception as e:
                error_msg = f"Error getting execution status: {str(e)}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}

    async def validate_and_execute_workflow(
        self,
        workflow_data: Dict[str, Any],
        test_data: Optional[Dict[str, Any]] = None,
        user_id: str = "test_user",
    ) -> Dict[str, Any]:
        """
        Create, validate, and execute a workflow in one operation

        Args:
            workflow_data: The workflow JSON structure
            test_data: Test input data for execution
            user_id: User ID for workflow ownership

        Returns:
            Complete execution result including any errors
        """
        # Step 1: Create the workflow
        create_result = await self.create_workflow(workflow_data, user_id)

        if not create_result.get("success", True):
            return {
                "success": False,
                "stage": "creation",
                "error": create_result.get("error", "Failed to create workflow"),
                "details": create_result,
            }

        workflow_id = create_result.get("workflow", {}).get("id")
        if not workflow_id:
            return {
                "success": False,
                "stage": "creation",
                "error": "No workflow ID returned from creation",
            }

        # Step 2: Execute the workflow with test data
        execute_result = await self.execute_workflow(workflow_id, test_data, user_id)

        if not execute_result.get("success", True):
            return {
                "success": False,
                "stage": "execution",
                "workflow_id": workflow_id,
                "error": execute_result.get("error", "Failed to execute workflow"),
                "details": execute_result,
            }

        execution_id = execute_result.get("execution_id")

        # Step 3: Wait for execution to complete and get results
        # In a real implementation, we might want to poll for status
        # For now, we'll return the initial execution result

        return {
            "success": True,
            "workflow_id": workflow_id,
            "execution_id": execution_id,
            "status": execute_result.get("status", "running"),
            "message": "Workflow created and execution started successfully",
        }
