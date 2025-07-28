"""
Execution management API endpoints with authentication
支持认证的执行管理API端点
"""

from typing import Any, Dict, Optional

from app.dependencies import AuthenticatedDeps
from app.exceptions import NotFoundError, ValidationError
from app.models.base import ResponseModel
from app.models.execution import ExecutionCancelResponse, ExecutionStatusResponse
from app.services.enhanced_grpc_client import get_workflow_client
from app.utils.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException

logger = get_logger(__name__)
router = APIRouter()


@router.get("/executions/{execution_id}", response_model=ExecutionStatusResponse)
async def get_execution_status(execution_id: str, deps: AuthenticatedDeps = Depends()):
    """
    Get execution status with user access control
    获取执行状态（支持用户访问控制）
    """
    try:
        logger.info(f"📊 Getting execution status {execution_id} for user {deps.current_user.sub}")

        # Get gRPC client
        grpc_client = await get_workflow_client()
        if not grpc_client:
            raise HTTPException(status_code=500, detail="Workflow service unavailable")

        # Get execution status with user context
        result = await grpc_client.get_execution_status(execution_id, user_id=deps.current_user.sub)
        if not result:
            raise NotFoundError("Execution")

        logger.info(f"✅ Execution status retrieved: {execution_id}")

        return ExecutionStatusResponse(**result)

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

        # Get gRPC client
        grpc_client = await get_workflow_client()
        if not grpc_client:
            raise HTTPException(status_code=500, detail="Workflow service unavailable")

        # Cancel execution with user context
        result = await grpc_client.cancel_execution(execution_id, user_id=deps.current_user.sub)
        if not result:
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
