import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from shared.models.node_enums import IntegrationProvider, NodeType, TriggerSubtype, ValidationResult
from shared.models.trigger import DeploymentResult, DeploymentStatus, TriggerSpec

# Note: DeploymentStatus is actually WorkflowDeploymentStatus imported from shared.models.workflow
# Valid values: UNDEPLOYED, DEPLOYING, DEPLOYED, DEPLOYMENT_FAILED
from workflow_scheduler.services.direct_db_service import DirectDBService
from workflow_scheduler.services.trigger_index_manager import TriggerIndexManager

logger = logging.getLogger(__name__)


class DeploymentService:
    """Service for managing workflow deployments and trigger configuration"""

    def __init__(self, trigger_manager, direct_db_service: Optional[DirectDBService] = None):
        self.trigger_manager = trigger_manager
        self.trigger_index_manager = TriggerIndexManager()
        # Use provided instance or create new one (backwards compatibility)
        self.direct_db_service = direct_db_service or DirectDBService()
        self._deployments: Dict[str, Dict] = {}  # In-memory storage for now

    async def deploy_workflow(self, workflow_id: str, workflow_spec: Dict) -> DeploymentResult:
        """
        Deploy a workflow with its trigger configuration

        Args:
            workflow_id: Unique workflow identifier
            workflow_spec: Complete workflow specification including triggers

        Returns:
            DeploymentResult with deployment status and details
        """
        import asyncio

        deployment_id = f"deploy_{uuid.uuid4()}"

        try:
            logger.info(f"Starting deployment of workflow {workflow_id}")

            # Async optimization: Run validation and trigger extraction in parallel
            validation_task = asyncio.create_task(self._validate_workflow_definition(workflow_spec))
            trigger_extraction_task = asyncio.create_task(
                self._extract_trigger_specs(workflow_spec)
            )

            # Run validation and trigger extraction concurrently
            validation_result, trigger_specs = await asyncio.gather(
                validation_task, trigger_extraction_task, return_exceptions=True
            )

            # Handle validation result
            if isinstance(validation_result, Exception):
                error_msg = f"Workflow validation error: {str(validation_result)}"
                await self._handle_deployment_failure(workflow_id, deployment_id, error_msg)
                return DeploymentResult(
                    deployment_id=deployment_id,
                    workflow_id=workflow_id,
                    status=DeploymentStatus.DEPLOYMENT_FAILED,
                    message=error_msg,
                )

            if validation_result["valid"] != ValidationResult.VALID:
                error_msg = f"Workflow validation failed: {validation_result['error']}"
                await self._handle_deployment_failure(workflow_id, deployment_id, error_msg)
                return DeploymentResult(
                    deployment_id=deployment_id,
                    workflow_id=workflow_id,
                    status=DeploymentStatus.DEPLOYMENT_FAILED,
                    message=error_msg,
                )

            # Handle trigger extraction result
            if isinstance(trigger_specs, Exception):
                error_msg = f"Trigger extraction error: {str(trigger_specs)}"
                await self._handle_deployment_failure(workflow_id, deployment_id, error_msg)
                return DeploymentResult(
                    deployment_id=deployment_id,
                    workflow_id=workflow_id,
                    status=DeploymentStatus.DEPLOYMENT_FAILED,
                    message=error_msg,
                )

            if not trigger_specs:
                error_msg = "No valid trigger specifications found in workflow"
                await self._handle_deployment_failure(workflow_id, deployment_id, error_msg)
                return DeploymentResult(
                    deployment_id=deployment_id,
                    workflow_id=workflow_id,
                    status=DeploymentStatus.DEPLOYMENT_FAILED,
                    message=error_msg,
                )

            # Async optimization: Run trigger registration in parallel
            trigger_manager_task = asyncio.create_task(
                self.trigger_manager.register_triggers(workflow_id, trigger_specs)
            )
            trigger_index_task = asyncio.create_task(
                self.trigger_index_manager.register_workflow_triggers(
                    workflow_id, trigger_specs, deployment_status="active"
                )
            )

            # Wait for both trigger registrations to complete
            registration_result, index_registration_result = await asyncio.gather(
                trigger_manager_task, trigger_index_task, return_exceptions=True
            )

            # Handle registration results
            if isinstance(registration_result, Exception) or not registration_result:
                error_msg = f"Failed to register triggers: {registration_result if isinstance(registration_result, Exception) else 'Unknown error'}"
                await self._handle_deployment_failure(workflow_id, deployment_id, error_msg)
                return DeploymentResult(
                    deployment_id=deployment_id,
                    workflow_id=workflow_id,
                    status=DeploymentStatus.DEPLOYMENT_FAILED,
                    message=error_msg,
                )

            if isinstance(index_registration_result, Exception) or not index_registration_result:
                # Cleanup TriggerManager registration if index registration fails
                await self.trigger_manager.unregister_triggers(workflow_id)
                error_msg = f"Failed to register triggers in index: {index_registration_result if isinstance(index_registration_result, Exception) else 'Unknown error'}"
                await self._handle_deployment_failure(workflow_id, deployment_id, error_msg)
                return DeploymentResult(
                    deployment_id=deployment_id,
                    workflow_id=workflow_id,
                    status=DeploymentStatus.DEPLOYMENT_FAILED,
                    message=error_msg,
                )

            # Ensure workflow record exists in database before updating deployment status
            logger.info(f"Creating/updating workflow record for {workflow_id}")
            workflow_creation_success = await self.direct_db_service.create_or_update_workflow(
                workflow_id=workflow_id,
                workflow_spec=workflow_spec,
                user_id=workflow_spec.get("metadata", {}).get("created_by"),
                name=workflow_spec.get("metadata", {}).get("name"),
            )

            if not workflow_creation_success:
                logger.warning(
                    f"Failed to create workflow record for {workflow_id}, but continuing with deployment"
                )

            # Get current workflow status for deployment tracking
            current_status_info = await self.direct_db_service.get_workflow_current_status(
                workflow_id
            )
            # Use enum values to avoid case mismatches; default to pending
            current_status = (
                current_status_info.get("deployment_status", DeploymentStatus.DEPLOYING.value)
                if current_status_info
                else DeploymentStatus.DEPLOYING.value
            )
            current_version = (
                current_status_info.get("deployment_version", 0) if current_status_info else 0
            )

            # Create deployment history record
            # Convert lowercase value to uppercase enum name for history table constraints
            from_status_name = (
                DeploymentStatus(current_status).name
                if current_status in {d.value for d in DeploymentStatus}
                else DeploymentStatus.DEPLOYING.name
            )

            history_success = await self.direct_db_service.create_deployment_history_record(
                workflow_id=workflow_id,
                deployment_action="DEPLOY",
                from_status=from_status_name,
                to_status=DeploymentStatus.DEPLOYED.name,
                deployment_version=current_version + 1,
                deployment_config={
                    "deployment_id": deployment_id,
                    "trigger_count": len(trigger_specs),
                    "workflow_spec": workflow_spec,
                },
            )

            # Update workflow deployment status
            deployment_success = await self.direct_db_service.update_workflow_deployment_status(
                workflow_id=workflow_id,
                deployment_status=DeploymentStatus.DEPLOYED.value,
                deployed_at=datetime.utcnow(),
                deployment_config={
                    "deployment_id": deployment_id,
                    "trigger_count": len(trigger_specs),
                    "workflow_spec": workflow_spec,
                },
                increment_version=True,
            )

            if deployment_success:
                logger.info(f"✅ Database updated successfully for workflow {workflow_id}")
            else:
                logger.warning(
                    f"⚠️ Database update failed for workflow {workflow_id}, but triggers are active"
                )

            # Store deployment record (in-memory for backward compatibility)
            deployment_record = {
                "deployment_id": deployment_id,
                "workflow_id": workflow_id,
                "workflow_spec": workflow_spec,
                "trigger_specs": trigger_specs,
                "status": DeploymentStatus.DEPLOYED,
                "deployed_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }

            self._deployments[workflow_id] = deployment_record

            logger.info(f"Workflow {workflow_id} deployed successfully: {deployment_id}")

            return DeploymentResult(
                deployment_id=deployment_id,
                workflow_id=workflow_id,
                status=DeploymentStatus.DEPLOYED,
                message=f"Workflow deployed successfully with {len(trigger_specs)} triggers",
            )

        except Exception as e:
            error_msg = f"Deployment failed for workflow {workflow_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)

            # Update workflow status to failed
            try:
                await self.direct_db_service.update_workflow_deployment_status(
                    workflow_id=workflow_id,
                    deployment_status=DeploymentStatus.DEPLOYMENT_FAILED.value,
                )
                await self.direct_db_service.create_deployment_history_record(
                    workflow_id=workflow_id,
                    deployment_action="DEPLOY_FAILED",
                    from_status=DeploymentStatus.DEPLOYING.name,
                    to_status=DeploymentStatus.DEPLOYMENT_FAILED.name,
                    deployment_version=1,
                    error_message=error_msg,
                )
            except Exception as db_error:
                logger.error(
                    f"Failed to update database after deployment error: {db_error}",
                    exc_info=True,
                )

            return DeploymentResult(
                deployment_id=deployment_id,
                workflow_id=workflow_id,
                status=DeploymentStatus.DEPLOYMENT_FAILED,
                message=error_msg,
            )

    async def deploy_workflow_from_database(self, workflow_id: str) -> DeploymentResult:
        """
        Deploy a workflow by fetching it from the database

        Args:
            workflow_id: Unique workflow identifier

        Returns:
            DeploymentResult with deployment status and details
        """
        try:
            logger.info(f"Fetching and deploying workflow {workflow_id} from database")

            # Fetch workflow from database
            workflow_record = await self.direct_db_service.get_workflow_by_id(workflow_id)

            if not workflow_record:
                error_msg = f"Workflow {workflow_id} not found in database"
                logger.error(error_msg)
                return DeploymentResult(
                    deployment_id=f"deploy_{uuid.uuid4()}",
                    workflow_id=workflow_id,
                    status=DeploymentStatus.DEPLOYMENT_FAILED,
                    message=error_msg,
                )

            # Extract workflow spec from database record
            workflow_spec = workflow_record.get("workflow_data", {})
            if not workflow_spec:
                error_msg = f"No workflow data found for workflow {workflow_id}"
                logger.error(error_msg)
                return DeploymentResult(
                    deployment_id=f"deploy_{uuid.uuid4()}",
                    workflow_id=workflow_id,
                    status=DeploymentStatus.DEPLOYMENT_FAILED,
                    message=error_msg,
                )

            # Parse JSON if it's a string
            import json

            if isinstance(workflow_spec, str):
                workflow_spec = json.loads(workflow_spec)

            logger.info(f"Successfully fetched workflow {workflow_id} from database")

            # Deploy the workflow using the existing method
            return await self.deploy_workflow(workflow_id, workflow_spec)

        except Exception as e:
            error_msg = f"Error fetching/deploying workflow {workflow_id} from database: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return DeploymentResult(
                deployment_id=f"deploy_{uuid.uuid4()}",
                workflow_id=workflow_id,
                status=DeploymentStatus.DEPLOYMENT_FAILED,
                message=error_msg,
            )

    async def undeploy_workflow(self, workflow_id: str) -> bool:
        """
        Undeploy a workflow and cleanup its triggers

        Args:
            workflow_id: Workflow to undeploy

        Returns:
            bool: True if successfully undeployed
        """
        try:
            logger.info(f"Undeploying workflow {workflow_id}")

            # Get current workflow status for deployment history
            current_status_info = await self.direct_db_service.get_workflow_current_status(
                workflow_id
            )
            current_status = (
                current_status_info.get("deployment_status", DeploymentStatus.DEPLOYED.value)
                if current_status_info
                else DeploymentStatus.DEPLOYED.value
            )
            current_version = (
                current_status_info.get("deployment_version", 1) if current_status_info else 1
            )

            # Create deployment history record
            # Use uppercase enum names for history table constraints
            from_status_name = (
                DeploymentStatus(current_status).name
                if current_status in {d.value for d in DeploymentStatus}
                else DeploymentStatus.DEPLOYED.name
            )

            await self.direct_db_service.create_deployment_history_record(
                workflow_id=workflow_id,
                deployment_action="UNDEPLOY_STARTED",
                from_status=from_status_name,
                to_status=DeploymentStatus.DEPLOYING.name,  # transitional state
                deployment_version=current_version,
            )

            # Update workflow status to UNDEPLOYING
            await self.direct_db_service.update_workflow_deployment_status(
                workflow_id=workflow_id,
                deployment_status=DeploymentStatus.DEPLOYING.value,  # transitional state
            )

            # 1. Unregister triggers from TriggerManager
            unregister_result = await self.trigger_manager.unregister_triggers(workflow_id)

            # 2. Unregister triggers from trigger index
            index_unregister_result = await self.trigger_index_manager.unregister_workflow_triggers(
                workflow_id
            )

            if unregister_result and index_unregister_result:
                # Update workflow status to UNDEPLOYED
                await self.direct_db_service.update_workflow_deployment_status(
                    workflow_id=workflow_id,
                    deployment_status=DeploymentStatus.UNDEPLOYED.value,
                    undeployed_at=datetime.utcnow(),
                )

                # Complete deployment history record
                await self.direct_db_service.create_deployment_history_record(
                    workflow_id=workflow_id,
                    deployment_action="UNDEPLOY_COMPLETED",
                    from_status=DeploymentStatus.DEPLOYING.name,
                    to_status=DeploymentStatus.UNDEPLOYED.name,
                    deployment_version=current_version,
                    deployment_config={"undeployed_at": datetime.utcnow().isoformat()},
                )
            else:
                # Update workflow status to failed
                await self.direct_db_service.update_workflow_deployment_status(
                    workflow_id=workflow_id,
                    deployment_status=DeploymentStatus.DEPLOYMENT_FAILED.value,
                )

                # Complete deployment history record with error
                await self.direct_db_service.create_deployment_history_record(
                    workflow_id=workflow_id,
                    deployment_action="UNDEPLOY_FAILED",
                    from_status=DeploymentStatus.DEPLOYING.name,
                    to_status=DeploymentStatus.DEPLOYMENT_FAILED.name,
                    deployment_version=current_version,
                    error_message="Failed to unregister triggers",
                )

            # 3. Update in-memory deployment record
            if workflow_id in self._deployments:
                self._deployments[workflow_id]["status"] = DeploymentStatus.UNDEPLOYED
                self._deployments[workflow_id]["updated_at"] = datetime.utcnow()

            logger.info(f"Workflow {workflow_id} undeployed successfully")
            return unregister_result and index_unregister_result

        except Exception as e:
            error_msg = f"Failed to undeploy workflow {workflow_id}: {e}"
            logger.error(error_msg, exc_info=True)

            # Update database with error status
            try:
                await self.direct_db_service.update_workflow_deployment_status(
                    workflow_id=workflow_id,
                    deployment_status=DeploymentStatus.DEPLOYMENT_FAILED.value,
                )
                await self.direct_db_service.create_deployment_history_record(
                    workflow_id=workflow_id,
                    deployment_action="UNDEPLOY_FAILED",
                    from_status=DeploymentStatus.DEPLOYED.value,
                    to_status=DeploymentStatus.DEPLOYMENT_FAILED.value,
                    deployment_version=1,
                    error_message=error_msg,
                )
            except Exception as db_error:
                logger.error(
                    f"Failed to update database after undeploy error: {db_error}",
                    exc_info=True,
                )

            return False

    async def update_deployment(self, workflow_id: str, workflow_spec: Dict) -> DeploymentResult:
        """
        Update an existing deployment with new workflow specification

        Args:
            workflow_id: Workflow to update
            workflow_spec: New workflow specification

        Returns:
            DeploymentResult with update status
        """
        try:
            logger.info(f"Updating deployment for workflow {workflow_id}")

            # 1. Undeploy existing triggers
            await self.undeploy_workflow(workflow_id)

            # 2. Deploy with new specification
            result = await self.deploy_workflow(workflow_id, workflow_spec)

            if result.status == DeploymentStatus.DEPLOYED:
                logger.info(f"Workflow {workflow_id} updated successfully")

            return result

        except Exception as e:
            error_msg = f"Update failed for workflow {workflow_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)

            return DeploymentResult(
                deployment_id=f"update_{uuid.uuid4()}",
                workflow_id=workflow_id,
                status=DeploymentStatus.DEPLOYMENT_FAILED,
                message=error_msg,
            )

    async def get_deployment_status(self, workflow_id: str) -> Optional[Dict]:
        """
        Get deployment status for a workflow

        Args:
            workflow_id: Workflow to check

        Returns:
            Dict with deployment information or None if not found
        """
        deployment = self._deployments.get(workflow_id)
        if not deployment:
            return None

        # Get current trigger status
        trigger_status = await self.trigger_manager.get_trigger_status(workflow_id)

        # Get indexed trigger information
        indexed_triggers = await self.trigger_index_manager.get_workflow_triggers(workflow_id)
        if indexed_triggers is None:
            indexed_triggers = []

        # Handle None case for indexed_triggers
        indexed_triggers = indexed_triggers or []

        return {
            "deployment_id": deployment["deployment_id"],
            "workflow_id": workflow_id,
            "status": deployment["status"],
            "deployed_at": deployment["deployed_at"].isoformat(),
            "updated_at": deployment["updated_at"].isoformat(),
            "trigger_count": len(deployment["trigger_specs"]),
            "trigger_status": trigger_status,
            "indexed_triggers": len(indexed_triggers),
            "trigger_details": indexed_triggers,
        }

    async def list_deployments(self) -> List[Dict]:
        """List all current deployments"""
        deployments = []

        for workflow_id, deployment in self._deployments.items():
            status_info = await self.get_deployment_status(workflow_id)
            if status_info:
                deployments.append(status_info)

        return deployments

    async def pause_workflow(self, workflow_id: str) -> bool:
        """
        Pause a deployed workflow (set triggers to paused status)

        Args:
            workflow_id: Workflow to pause

        Returns:
            bool: True if successfully paused
        """
        try:
            logger.info(f"Pausing workflow {workflow_id}")

            # Update trigger status in index
            success = await self.trigger_index_manager.update_trigger_status(workflow_id, "paused")

            # Update deployment record
            if workflow_id in self._deployments:
                self._deployments[workflow_id]["status"] = DeploymentStatus.PAUSED
                self._deployments[workflow_id]["updated_at"] = datetime.utcnow()

            if success:
                logger.info(f"Workflow {workflow_id} paused successfully")
            return success

        except Exception as e:
            logger.error(f"Failed to pause workflow {workflow_id}: {e}", exc_info=True)
            return False

    async def resume_workflow(self, workflow_id: str) -> bool:
        """
        Resume a paused workflow (set triggers to active status)

        Args:
            workflow_id: Workflow to resume

        Returns:
            bool: True if successfully resumed
        """
        try:
            logger.info(f"Resuming workflow {workflow_id}")

            # Update trigger status in index
            success = await self.trigger_index_manager.update_trigger_status(workflow_id, "active")

            # Update deployment record
            if workflow_id in self._deployments:
                self._deployments[workflow_id]["status"] = DeploymentStatus.DEPLOYED
                self._deployments[workflow_id]["updated_at"] = datetime.utcnow()

            if success:
                logger.info(f"Workflow {workflow_id} resumed successfully")
            return success

        except Exception as e:
            logger.error(f"Failed to resume workflow {workflow_id}: {e}", exc_info=True)
            return False

    async def get_index_statistics(self) -> Dict[str, Any]:
        """
        Get trigger index statistics

        Returns:
            Dictionary with index statistics
        """
        return await self.trigger_index_manager.get_index_statistics()

    async def register_github_installation(
        self,
        installation_id: int,
        account_id: int,
        account_login: str,
        account_type: str,
        repositories: List[Dict[str, Any]],
        permissions: Dict[str, str],
        user_id: Optional[str] = None,
    ) -> bool:
        """
        Register a GitHub App installation

        Args:
            installation_id: GitHub installation ID
            account_id: GitHub account ID
            account_login: GitHub account login name
            account_type: 'User' or 'Organization'
            repositories: List of accessible repositories
            permissions: Installation permissions
            user_id: Associated user ID (optional)

        Returns:
            bool: True if successfully registered
        """
        return await self.trigger_index_manager.register_github_installation(
            installation_id=installation_id,
            account_id=account_id,
            account_login=account_login,
            account_type=account_type,
            repositories=repositories,
            permissions=permissions,
            user_id=user_id,
        )

    async def get_github_installations(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get GitHub installations, optionally filtered by user

        Args:
            user_id: Optional user ID to filter by

        Returns:
            List of installation information
        """
        return await self.trigger_index_manager.get_github_installations(user_id)

    async def _validate_workflow_definition(self, workflow_spec: Dict) -> Dict:
        """
        Validate workflow definition structure

        Args:
            workflow_spec: Workflow specification to validate

        Returns:
            Dict with validation result and error message if invalid
        """
        try:
            # Basic structure validation
            if not isinstance(workflow_spec, dict):
                return {
                    "valid": ValidationResult.INVALID,
                    "error": "Workflow spec must be a dictionary",
                }

            # Check for required fields
            if "nodes" not in workflow_spec:
                return {
                    "valid": ValidationResult.INVALID,
                    "error": "Workflow spec must contain 'nodes' field",
                }

            nodes = workflow_spec["nodes"]
            if not isinstance(nodes, list):
                return {
                    "valid": ValidationResult.INVALID,
                    "error": "'nodes' must be a list",
                }

            # Check for at least one trigger node (node_type or type field)
            trigger_nodes = [node for node in nodes if node.get("type") == NodeType.TRIGGER.value]

            if not trigger_nodes:
                return {
                    "valid": ValidationResult.INVALID,
                    "error": "Workflow must contain at least one trigger node",
                }

            # Validate trigger node configurations
            for node in trigger_nodes:
                subtype = node.get("subtype")
                if not subtype or subtype not in [t.value for t in TriggerSubtype]:
                    return {
                        "valid": ValidationResult.INVALID,
                        "error": f"Invalid trigger subtype: {subtype}",
                    }

                # Basic parameter validation
                parameters = node.get("parameters", {})
                if not isinstance(parameters, dict):
                    return {
                        "valid": ValidationResult.INVALID,
                        "error": f"Trigger parameters must be a dictionary for node {node.get('id')}",
                    }

            return {"valid": ValidationResult.VALID, "error": None}

        except Exception as e:
            return {
                "valid": ValidationResult.ERROR,
                "error": f"Validation error: {str(e)}",
            }

    async def _extract_trigger_specs(self, workflow_spec: Dict) -> List[TriggerSpec]:
        """
        Extract trigger specifications from workflow definition

        Args:
            workflow_spec: Complete workflow specification

        Returns:
            List of TriggerSpec objects
        """
        trigger_specs = []

        try:
            nodes = workflow_spec.get("nodes", [])

            for node in nodes:
                if node.get("type") == NodeType.TRIGGER.value:
                    # Use configurations instead of parameters for trigger specs
                    raw_configurations = node.get("configurations", {})

                    # Extract actual values from schema objects
                    parameters = self._extract_configuration_values(raw_configurations)

                    # For GitHub triggers, resolve installation_id from oauth_tokens
                    if node.get("subtype") == "GITHUB":
                        self._resolve_github_installation_id(parameters, workflow_spec)

                    # For Slack triggers, resolve channel names to channel IDs
                    elif node.get("subtype") == "SLACK":
                        await self._resolve_slack_channel_ids(parameters, workflow_spec)

                    trigger_spec = TriggerSpec(
                        node_type=node.get("type"),
                        subtype=TriggerSubtype(node["subtype"]),
                        parameters=parameters,
                        enabled=node.get("enabled", True),
                    )
                    trigger_specs.append(trigger_spec)

            logger.info(f"Extracted {len(trigger_specs)} trigger specifications")
            return trigger_specs

        except Exception as e:
            logger.error(f"Failed to extract trigger specs: {e}", exc_info=True)
            return []

    def _extract_configuration_values(self, raw_configurations: Dict) -> Dict[str, Any]:
        """
        Extract actual configuration values from schema objects.

        Handles cases where configuration fields contain schema definitions like:
        {
            "workspace_id": {
                "type": "string",
                "default": "",
                "required": true,
                "description": "Slack工作区ID"
            }
        }

        And extracts them to actual values using defaults or provided values.

        Args:
            raw_configurations: Raw configuration dict that may contain schema objects

        Returns:
            Dict with actual configuration values
        """
        extracted_values = {}

        for key, config_value in raw_configurations.items():
            if isinstance(config_value, dict) and (
                "type" in config_value or "default" in config_value
            ):
                # This looks like a schema object, extract the actual value
                if "value" in config_value:
                    # Preferred: use explicit value if provided
                    extracted_values[key] = config_value["value"]
                elif "default" in config_value:
                    # Fallback: use default value from schema
                    extracted_values[key] = config_value["default"]
                else:
                    # Last resort: use empty value based on type
                    config_type = config_value.get("type", "string")
                    if config_type == "string":
                        extracted_values[key] = ""
                    elif config_type == "boolean":
                        extracted_values[key] = False
                    elif config_type == "number" or config_type == "integer":
                        extracted_values[key] = 0
                    elif config_type == "array":
                        extracted_values[key] = []
                    elif config_type == "object":
                        extracted_values[key] = {}
                    else:
                        extracted_values[key] = None

                logger.debug(
                    f"Extracted configuration value for {key}: {extracted_values[key]} (from schema)"
                )
            else:
                # This is already an actual value, use it directly
                extracted_values[key] = config_value
                logger.debug(f"Using direct configuration value for {key}: {config_value}")

        return extracted_values

    def _resolve_github_installation_id(self, parameters: Dict, workflow_spec: Dict):
        """
        Resolve GitHub installation_id from oauth_tokens table for the workflow owner

        Args:
            parameters: Trigger parameters to modify
            workflow_spec: Complete workflow specification
        """
        try:
            # Get workflow owner (user_id) from workflow_spec
            user_id = workflow_spec.get("user_id")
            if not user_id:
                logger.warning(
                    "No user_id found in workflow_spec, cannot resolve GitHub installation_id"
                )
                return

            # Query oauth_tokens for GitHub integration using direct_db_service
            # Use Supabase client directly for synchronous operation
            from workflow_scheduler.core.supabase_client import get_supabase_client

            supabase = get_supabase_client()
            if not supabase:
                logger.error("Supabase client not available for GitHub installation_id lookup")
                return

            # Look for GitHub OAuth token for this user
            github_token_result = (
                supabase.table("oauth_tokens")
                .select("credential_data")
                .eq("user_id", user_id)
                .eq("provider", IntegrationProvider.GITHUB.value)
                .eq("is_active", True)
                .execute()
            )

            if github_token_result.data and len(github_token_result.data) > 0:
                # Extract installation_id from credential_data
                credential_data = github_token_result.data[0].get("credential_data", {})
                installation_id = credential_data.get("installation_id")

                if installation_id:
                    parameters["github_app_installation_id"] = installation_id
                    logger.info(
                        f"Resolved GitHub installation_id to {installation_id} for user {user_id}"
                    )
                else:
                    logger.warning(
                        f"No installation_id found in GitHub credential_data for user {user_id}"
                    )
            else:
                logger.warning(f"No active GitHub integration found for user {user_id}")

        except Exception as e:
            logger.error(f"Error resolving GitHub installation_id: {e}", exc_info=True)

    async def _resolve_slack_channel_ids(self, parameters: Dict, workflow_spec: Dict):
        """
        Resolve Slack channel names to channel IDs and workspace_id during deployment

        This converts channel names like "general", "hil" to channel IDs like "C09D2JW6814"
        and automatically resolves workspace_id from user's OAuth token.

        Args:
            parameters: Trigger parameters to modify
            workflow_spec: Complete workflow specification
        """
        try:
            # Get workflow owner (user_id) from workflow_spec
            user_id = workflow_spec.get("user_id") or workflow_spec.get("metadata", {}).get(
                "created_by"
            )
            if not user_id:
                logger.warning(
                    "No user_id found in workflow_spec or metadata.created_by, cannot resolve Slack configuration"
                )
                return

            # Get user's Slack OAuth token and workspace info
            slack_token, workspace_id = await self._get_user_slack_token_and_workspace(user_id)
            if not slack_token:
                logger.warning(
                    f"No Slack OAuth token found for user {user_id}. "
                    "User must connect their Slack account in integrations settings."
                )
                return

            # Always auto-resolve workspace_id - ignore any workspace_id in workflow configuration
            if workspace_id:
                parameters["workspace_id"] = workspace_id
                logger.info(f"Auto-resolved workspace_id to '{workspace_id}' for user {user_id}")
            else:
                logger.warning(
                    f"Could not resolve workspace_id for user {user_id}. "
                    f"Ensure user has an active Slack OAuth integration."
                )

            # Resolve channel names to IDs if channels array or legacy channel_filter is specified
            # Prefer 'channels' array (node spec) over legacy 'channel_filter'
            channels_list = parameters.get("channels")
            using_channels_array = False

            if channels_list and isinstance(channels_list, list):
                # Node spec uses 'channels' array
                using_channels_array = True
                channel_filter = ",".join(str(ch) for ch in channels_list)
                logger.debug(f"Using channels array from node spec: {channels_list}")
            else:
                # Fall back to legacy channel_filter or channel
                channel_filter = parameters.get("channel_filter") or parameters.get("channel")

            if not channel_filter:
                logger.debug(
                    "No channels array, channel_filter, or channel specified for Slack trigger"
                )
                return

            # Check if all channels are already IDs (start with C)
            channel_names = [ch.strip() for ch in channel_filter.split(",")]
            all_are_ids = all(ch.startswith("C") for ch in channel_names)

            if all_are_ids:
                logger.debug(f"All channels are already IDs: {channel_names}")
                return

            # Resolve channel name(s) to ID(s)
            resolved_channel_ids = await self._resolve_channel_names_to_ids(
                channel_filter, slack_token
            )

            if resolved_channel_ids:
                # Update the parameters with resolved channel IDs
                resolved_ids_list = resolved_channel_ids.split(",")

                if using_channels_array:
                    # Update the 'channels' array with resolved IDs
                    parameters["channels"] = resolved_ids_list
                    logger.info(
                        f"Resolved Slack channels {channels_list} to {resolved_ids_list} for user {user_id}"
                    )
                else:
                    # Update legacy 'channel_filter' field
                    parameters["channel_filter"] = resolved_channel_ids
                    logger.info(
                        f"Resolved Slack channel filter '{channel_filter}' to '{resolved_channel_ids}' for user {user_id}"
                    )
            else:
                logger.warning(
                    f"Could not resolve Slack channel filter '{channel_filter}' for user {user_id}"
                )

        except Exception as e:
            logger.error(f"Error resolving Slack configuration: {e}", exc_info=True)

    async def _get_user_slack_token(self, user_id: str) -> Optional[str]:
        """
        Get the user's Slack OAuth token from the database

        Args:
            user_id: User ID to look up

        Returns:
            str: Slack access token, or None if not found
        """
        token, _ = await self._get_user_slack_token_and_workspace(user_id)
        return token

    async def _get_user_slack_token_and_workspace(
        self, user_id: str
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Get the user's Slack OAuth token and workspace_id from the database

        Args:
            user_id: User ID to look up

        Returns:
            tuple: (access_token, workspace_id) or (None, None) if not found
        """
        try:
            from workflow_scheduler.core.supabase_client import get_supabase_client

            supabase = get_supabase_client()
            if not supabase:
                logger.error("Supabase client not available")
                return None, None

            # Get user's Slack OAuth token with credential data
            oauth_result = (
                supabase.table("oauth_tokens")
                .select("access_token, credential_data")
                .eq("user_id", user_id)
                .eq("provider", IntegrationProvider.SLACK.value)
                .eq("is_active", True)
                .execute()
            )

            if not oauth_result.data:
                logger.warning(f"No active Slack OAuth token found for user {user_id}")
                return None, None

            token_record = oauth_result.data[0]
            access_token = token_record.get("access_token")
            credential_data = token_record.get("credential_data", {})

            # Extract workspace_id (team_id) from credential_data
            workspace_id = credential_data.get("team_id")

            if access_token:
                logger.debug(
                    f"Retrieved Slack token and workspace_id '{workspace_id}' for user {user_id}"
                )
                return access_token, workspace_id
            else:
                logger.warning(f"Empty access_token for user {user_id}")
                return None, workspace_id

        except Exception as e:
            logger.error(f"Error getting user Slack token and workspace: {e}", exc_info=True)
            return None, None

    async def _get_workspace_info_from_slack_api(self, access_token: str) -> Optional[str]:
        """
        Get workspace_id directly from Slack API using the new helper function.

        This method uses the Slack SDK helper function to get workspace information
        directly from Slack's auth.test endpoint.

        Args:
            access_token: Slack bot access token

        Returns:
            str: workspace_id (team_id) or None if failed
        """
        try:
            from shared.sdks.slack_sdk.client import SlackWebClient

            slack_client = SlackWebClient(token=access_token)
            workspace_info = slack_client.get_workspace_info()

            workspace_id = workspace_info.get("workspace_id")
            if workspace_id:
                logger.info(f"✅ Retrieved workspace_id '{workspace_id}' directly from Slack API")
                logger.info(f"   Team: {workspace_info.get('team_name')}")
                logger.info(f"   URL: {workspace_info.get('workspace_url')}")
                return workspace_id
            else:
                logger.warning("No workspace_id found in Slack API response")
                return None

        except Exception as e:
            logger.error(f"Error getting workspace info from Slack API: {e}")
            return None

    async def _resolve_channel_names_to_ids(
        self, channel_filter: str, slack_token: str
    ) -> Optional[str]:
        """
        Resolve channel names to channel IDs using Slack API

        Args:
            channel_filter: Channel names (single or comma-separated)
            slack_token: Slack OAuth token

        Returns:
            str: Resolved channel IDs (single or comma-separated), or None if failed
        """
        import httpx

        try:
            # Handle comma-separated channel names
            if "," in channel_filter:
                channel_names = [name.strip() for name in channel_filter.split(",")]
            else:
                channel_names = [channel_filter.strip()]

            resolved_ids = []

            async with httpx.AsyncClient(timeout=30.0) as client:
                for channel_name in channel_names:
                    # Try to find the channel by name
                    channel_id = await self._find_channel_id_by_name(
                        client, slack_token, channel_name
                    )
                    if channel_id:
                        resolved_ids.append(channel_id)
                        logger.debug(f"Resolved channel '{channel_name}' to ID '{channel_id}'")
                    else:
                        logger.warning(f"Could not find channel ID for '{channel_name}'")
                        # Keep the original name if we can't resolve it
                        resolved_ids.append(channel_name)

            if resolved_ids:
                return ",".join(resolved_ids)
            else:
                return None

        except Exception as e:
            logger.error(f"Error resolving channel names to IDs: {e}", exc_info=True)
            return None

    async def _find_channel_id_by_name(
        self, client: httpx.AsyncClient, slack_token: str, channel_name: str
    ) -> Optional[str]:
        """
        Find a single channel ID by name using Slack API

        Args:
            client: HTTP client
            slack_token: Slack OAuth token
            channel_name: Channel name to look up

        Returns:
            str: Channel ID, or None if not found
        """
        try:
            # Use conversations.list to find the channel
            response = await client.get(
                "https://slack.com/api/conversations.list",
                headers={"Authorization": f"Bearer {slack_token}"},
                params={
                    "types": "public_channel,private_channel",
                    "limit": 1000,  # Slack's max limit
                },
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    channels = data.get("channels", [])
                    for channel in channels:
                        if channel.get("name") == channel_name:
                            return channel.get("id")
                    logger.debug(f"Channel '{channel_name}' not found in {len(channels)} channels")
                else:
                    error_msg = data.get("error", "unknown")
                    logger.warning(
                        f"Slack API error looking up channel '{channel_name}': {error_msg}"
                    )
            else:
                logger.warning(f"HTTP error getting channel list: {response.status_code}")

            return None

        except Exception as e:
            logger.warning(f"Failed to find channel ID for '{channel_name}': {e}")
            return None

    async def _handle_deployment_failure(
        self, workflow_id: str, deployment_id: str, error_msg: str
    ):
        """Handle deployment failure with simple database updates"""
        try:
            # Update workflow status to failed
            await self.direct_db_service.update_workflow_deployment_status(
                workflow_id=workflow_id,
                deployment_status=DeploymentStatus.DEPLOYMENT_FAILED.value,
            )

            # Create deployment history record with error
            await self.direct_db_service.create_deployment_history_record(
                workflow_id=workflow_id,
                deployment_action="DEPLOY",
                from_status=DeploymentStatus.DEPLOYING.value,
                to_status=DeploymentStatus.DEPLOYMENT_FAILED.value,
                deployment_version=1,
                error_message=error_msg,
            )
        except Exception as db_error:
            logger.error(
                f"Failed to update database after deployment error: {db_error}",
                exc_info=True,
            )
