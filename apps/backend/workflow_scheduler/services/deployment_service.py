import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from shared.models.trigger import DeploymentResult, DeploymentStatus, TriggerSpec, TriggerType
from workflow_scheduler.services.trigger_index_manager import TriggerIndexManager

logger = logging.getLogger(__name__)


class DeploymentService:
    """Service for managing workflow deployments and trigger configuration"""

    def __init__(self, trigger_manager):
        self.trigger_manager = trigger_manager
        self.trigger_index_manager = TriggerIndexManager()
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
        deployment_id = f"deploy_{uuid.uuid4()}"

        try:
            logger.info(f"Starting deployment of workflow {workflow_id}")

            # 1. Validate workflow definition
            validation_result = await self._validate_workflow_definition(workflow_spec)
            if not validation_result["valid"]:
                return DeploymentResult(
                    deployment_id=deployment_id,
                    status=DeploymentStatus.FAILED,
                    message=f"Workflow validation failed: {validation_result['error']}",
                )

            # 2. Extract trigger specifications
            trigger_specs = self._extract_trigger_specs(workflow_spec)
            if not trigger_specs:
                return DeploymentResult(
                    deployment_id=deployment_id,
                    status=DeploymentStatus.FAILED,
                    message="No valid trigger specifications found in workflow",
                )

            # 3. Register triggers with TriggerManager
            registration_result = await self.trigger_manager.register_triggers(
                workflow_id, trigger_specs
            )

            if not registration_result:
                return DeploymentResult(
                    deployment_id=deployment_id,
                    status=DeploymentStatus.FAILED,
                    message="Failed to register triggers",
                )

            # 4. Register triggers in the trigger index for fast lookup
            index_registration_result = await self.trigger_index_manager.register_workflow_triggers(
                workflow_id, trigger_specs, deployment_status="active"
            )

            if not index_registration_result:
                # Cleanup TriggerManager registration if index registration fails
                await self.trigger_manager.unregister_triggers(workflow_id)
                return DeploymentResult(
                    deployment_id=deployment_id,
                    status=DeploymentStatus.FAILED,
                    message="Failed to register triggers in index",
                )

            # 5. Store deployment record
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
                status=DeploymentStatus.DEPLOYED,
                message=f"Workflow deployed successfully with {len(trigger_specs)} triggers",
            )

        except Exception as e:
            error_msg = f"Deployment failed for workflow {workflow_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)

            return DeploymentResult(
                deployment_id=deployment_id, status=DeploymentStatus.FAILED, message=error_msg
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

            # 1. Unregister triggers from TriggerManager
            unregister_result = await self.trigger_manager.unregister_triggers(workflow_id)

            # 2. Unregister triggers from trigger index
            index_unregister_result = await self.trigger_index_manager.unregister_workflow_triggers(
                workflow_id
            )

            # 3. Update deployment record
            if workflow_id in self._deployments:
                self._deployments[workflow_id]["status"] = DeploymentStatus.UNDEPLOYED
                self._deployments[workflow_id]["updated_at"] = datetime.utcnow()

            logger.info(f"Workflow {workflow_id} undeployed successfully")
            return unregister_result and index_unregister_result

        except Exception as e:
            logger.error(f"Failed to undeploy workflow {workflow_id}: {e}", exc_info=True)
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
                status=DeploymentStatus.FAILED,
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
                return {"valid": False, "error": "Workflow spec must be a dictionary"}

            # Check for required fields
            if "nodes" not in workflow_spec:
                return {"valid": False, "error": "Workflow spec must contain 'nodes' field"}

            nodes = workflow_spec["nodes"]
            if not isinstance(nodes, list):
                return {"valid": False, "error": "'nodes' must be a list"}

            # Check for at least one trigger node (node_type or type field)
            trigger_nodes = [
                node
                for node in nodes
                if node.get("node_type") == "TRIGGER_NODE" or node.get("type") == "TRIGGER"
            ]

            if not trigger_nodes:
                return {"valid": False, "error": "Workflow must contain at least one trigger node"}

            # Validate trigger node configurations
            for node in trigger_nodes:
                subtype = node.get("subtype")
                if not subtype or subtype not in [t.value for t in TriggerType]:
                    return {"valid": False, "error": f"Invalid trigger subtype: {subtype}"}

                # Basic parameter validation
                parameters = node.get("parameters", {})
                if not isinstance(parameters, dict):
                    return {
                        "valid": False,
                        "error": f"Trigger parameters must be a dictionary for node {node.get('id')}",
                    }

            return {"valid": True, "error": None}

        except Exception as e:
            return {"valid": False, "error": f"Validation error: {str(e)}"}

    def _extract_trigger_specs(self, workflow_spec: Dict) -> List[TriggerSpec]:
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
                if node.get("node_type") == "TRIGGER_NODE" or node.get("type") == "TRIGGER":
                    trigger_spec = TriggerSpec(
                        node_type=node.get("node_type", node.get("type")),
                        subtype=TriggerType(node["subtype"]),
                        parameters=node.get("parameters", {}),
                        enabled=node.get("enabled", True),
                    )
                    trigger_specs.append(trigger_spec)

            logger.info(f"Extracted {len(trigger_specs)} trigger specifications")
            return trigger_specs

        except Exception as e:
            logger.error(f"Failed to extract trigger specs: {e}", exc_info=True)
            return []
