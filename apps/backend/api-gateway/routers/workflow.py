"""
Workflow API routes
"""

from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

logger = structlog.get_logger()

router = APIRouter()


class WorkflowGenerateRequest(BaseModel):
    """Request model for workflow generation"""

    description: str
    context: Optional[Dict[str, Any]] = None


class WorkflowRefineRequest(BaseModel):
    """Request model for workflow refinement"""

    workflow_id: str
    feedback: str
    original_workflow: Dict[str, Any]


class WorkflowValidateRequest(BaseModel):
    """Request model for workflow validation"""

    workflow_data: Dict[str, Any]


class WorkflowResponse(BaseModel):
    """Response model for workflow operations"""

    success: bool
    workflow: Optional[Dict[str, Any]] = None
    suggestions: Optional[List[str]] = None
    missing_info: Optional[List[str]] = None
    errors: Optional[List[str]] = None


def get_workflow_client(request: Request):
    """Dependency to get the workflow client from app state"""
    return request.app.state.workflow_client


@router.post("/generate", response_model=WorkflowResponse)
async def generate_workflow(request: WorkflowGenerateRequest, client=Depends(get_workflow_client)):
    """Generate workflow from natural language description"""
    try:
        logger.info("Generating workflow", description=request.description)

        result = await client.generate_workflow(
            description=request.description, context=request.context
        )

        return WorkflowResponse(**result)

    except Exception as e:
        logger.error("Failed to generate workflow", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refine", response_model=WorkflowResponse)
async def refine_workflow(request: WorkflowRefineRequest, client=Depends(get_workflow_client)):
    """Refine existing workflow based on feedback"""
    try:
        logger.info("Refining workflow", workflow_id=request.workflow_id, feedback=request.feedback)

        result = await client.refine_workflow(
            workflow_id=request.workflow_id,
            feedback=request.feedback,
            workflow_data=request.original_workflow,
        )

        return WorkflowResponse(
            success=result["success"],
            workflow=result["updated_workflow"],
            suggestions=result.get("changes", []),
        )

    except Exception as e:
        logger.error("Failed to refine workflow", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate")
async def validate_workflow(request: WorkflowValidateRequest, client=Depends(get_workflow_client)):
    """Validate workflow structure and configuration"""
    try:
        logger.info("Validating workflow")

        result = await client.validate_workflow(request.workflow_data)

        return {
            "valid": result["valid"],
            "errors": result["errors"],
            "warnings": result["warnings"],
        }

    except Exception as e:
        logger.error("Failed to validate workflow", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def workflow_health():
    """Health check for workflow service"""
    return {"status": "healthy", "service": "workflow-api"}
