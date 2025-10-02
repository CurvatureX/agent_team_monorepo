import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from shared.models.workflow import Workflow, WorkflowDeploymentStatus
from workflow_scheduler.dependencies import get_deployment_service
from workflow_scheduler.services.deployment_service import DeploymentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/deployment", tags=["deployment"])


class DeploymentResult(BaseModel):
    """Modern deployment result using new data model"""

    deployment_id: str
    workflow_id: str
    status: WorkflowDeploymentStatus
    message: str
    created_at: datetime


class DeploymentStatusResponse(BaseModel):
    deployment_id: str
    workflow_id: str
    status: WorkflowDeploymentStatus
    deployed_at: Optional[str] = None
    updated_at: str
    trigger_count: int
    trigger_status: Dict[str, str]


@router.post("/workflows/{workflow_id}/deploy", response_model=DeploymentResult)
async def deploy_workflow(
    workflow_id: str,
    deployment_service: DeploymentService = Depends(get_deployment_service),
):
    """Deploy a workflow by fetching it from the database"""
    try:
        logger.info(f"Deploying workflow {workflow_id}")

        # Fetch workflow from database and deploy it
        result = await deployment_service.deploy_workflow_from_database(workflow_id)

        return result

    except Exception as e:
        logger.error(f"Error deploying workflow {workflow_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Deployment failed: {str(e)}")


@router.delete("/workflows/{workflow_id}/undeploy")
async def undeploy_workflow(
    workflow_id: str,
    deployment_service: DeploymentService = Depends(get_deployment_service),
):
    """Undeploy a workflow and cleanup its triggers"""
    try:
        logger.info(f"Undeploying workflow {workflow_id}")

        success = await deployment_service.undeploy_workflow(workflow_id)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to undeploy workflow")

        return {
            "message": "Workflow undeployed successfully",
            "workflow_id": workflow_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error undeploying workflow {workflow_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Undeployment failed: {str(e)}")


@router.get("/workflows/{workflow_id}/status", response_model=Optional[DeploymentStatusResponse])
async def get_deployment_status(
    workflow_id: str,
    deployment_service: DeploymentService = Depends(get_deployment_service),
):
    """Get deployment status for a workflow"""
    try:
        status = await deployment_service.get_deployment_status(workflow_id)

        if not status:
            raise HTTPException(status_code=404, detail="Workflow deployment not found")

        return DeploymentStatusResponse(**status)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting deployment status for workflow {workflow_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.get("/workflows", response_model=List[DeploymentStatusResponse])
async def list_deployments(
    deployment_service: DeploymentService = Depends(get_deployment_service),
):
    """List all current deployments"""
    try:
        deployments = await deployment_service.list_deployments()
        return [DeploymentStatusResponse(**deployment) for deployment in deployments]

    except Exception as e:
        logger.error(f"Error listing deployments: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list deployments: {str(e)}")
