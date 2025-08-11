"""
Execution management API endpoints with authentication
支持认证的执行管理API端点
"""

from typing import Any, Dict, Optional

from app.core.config import get_settings
from app.dependencies import AuthenticatedDeps
from app.exceptions import NotFoundError, ValidationError
from app.models import ResponseModel
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
try:
    from shared.models import Execution
except ImportError:
    import sys
    from pathlib import Path
    backend_dir = Path(__file__).parent.parent.parent.parent.parent
    sys.path.insert(0, str(backend_dir))
    from shared.models import Execution

class ExecutionCancelResponse(BaseModel):
    success: bool = Field(description="Whether cancellation was successful")
    message: str = Field(description="Result message")
    execution_id: str = Field(description="Execution ID")
from app.services.workflow_engine_http_client import get_workflow_engine_client
from shared.logging_config import get_logger
from fastapi import APIRouter, Depends, HTTPException

logger = get_logger(__name__)
router = APIRouter()


@router.get("/executions/{execution_id}", response_model=Execution)
async def get_execution_status(execution_id: str, deps: AuthenticatedDeps = Depends()):
    """
    Get execution status with user access control
    获取执行状态（支持用户访问控制）
    """
    try:
        logger.info(f"📊 Getting execution status {execution_id} for user {deps.current_user.sub}")

        # Get HTTP client
        settings = get_settings()

        http_client = await get_workflow_engine_client()

        # Get execution status via HTTP
        result = await http_client.get_execution_status(execution_id)
        if not result or result.get("error"):
            raise NotFoundError("Execution")

        logger.info(f"✅ Execution status retrieved: {execution_id}")
        
        # The result from workflow-engine should already match the Execution model
        # since both use the same shared models
        return Execution(**result)

    except (NotFoundError, HTTPException):
        raise
    except Exception as e:
        logger.error(f"❌ Error getting execution status {execution_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/executions/{execution_id}/cancel", response_model=ExecutionCancelResponse)
async def cancel_execution(execution_id: str, deps: AuthenticatedDeps = Depends()):
    """
    Cancel a running execution with user access control
    取消正在运行的执行（支持用户访问控制）
    """
    try:
        logger.info(f"🛑 Cancelling execution {execution_id} for user {deps.current_user.sub}")

        # Get HTTP client
        settings = get_settings()

        http_client = await get_workflow_engine_client()

        # Cancel execution via HTTP
        result = await http_client.cancel_execution(execution_id)
        if not result or result.get("error"):
            raise NotFoundError("Execution")

        # Check if cancellation was successful
        if not result.get("success", False):
            error_message = result.get("message", "Failed to cancel execution")
            raise HTTPException(status_code=400, detail=error_message)

        logger.info(f"✅ Execution cancelled: {execution_id}")

        return ExecutionCancelResponse(**result)

    except (NotFoundError, HTTPException):
        raise
    except Exception as e:
        logger.error(f"❌ Error cancelling execution {execution_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/workflows/{workflow_id}/executions")
async def get_workflow_execution_history(
    workflow_id: str, limit: int = 50, deps: AuthenticatedDeps = Depends()
):
    """
    Get execution history for a workflow
    获取工作流的执行历史
    """
    try:
        logger.info(
            f"📜 Getting execution history for workflow {workflow_id} (user: {deps.current_user.sub})"
        )

        # Get HTTP client
        settings = get_settings()

        http_client = await get_workflow_engine_client()

        # Get execution history via HTTP
        executions = await http_client.get_execution_history(workflow_id, limit)

        logger.info(f"✅ Retrieved {len(executions)} executions for workflow {workflow_id}")

        return {
            "workflow_id": workflow_id,
            "executions": executions,
            "total_count": len(executions),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting execution history for workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
