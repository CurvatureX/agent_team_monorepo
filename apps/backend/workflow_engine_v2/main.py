"""
Workflow Engine V2 - Main Application

Modern FastAPI-based workflow execution engine with comprehensive user-friendly logging.
Integrates seamlessly with the API Gateway's logs endpoint system.

Features:
- Modern execution engine with detailed progress tracking
- User-friendly logs exposed via /api/v2/workflows/executions/{execution_id}/logs
- Real-time log streaming
- Direct Supabase integration
- No backward compatibility concerns
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Use absolute imports
from shared.models import TriggerInfo
from shared.models.execution_new import Execution
from shared.models.trigger import DeploymentStatus
from shared.models.workflow_new import Workflow
from workflow_engine_v2.api.logs_endpoints import router as logs_router
from workflow_engine_v2.core.modern_engine import ModernExecutionEngine
from workflow_engine_v2.services.oauth2_service import OAuth2ServiceV2, TokenResponse
from workflow_engine_v2.services.unified_log_service import UnifiedLogServiceV2
from workflow_engine_v2.services.workflow import WorkflowServiceV2
from workflow_engine_v2.services.workflow_status_manager import WorkflowStatusManagerV2

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Request/Response Models
class ExecuteWorkflowRequest(BaseModel):
    """Request to execute a workflow"""

    workflow: Dict[str, Any]  # Workflow data as dict
    trigger: Dict[str, Any]  # Trigger info as dict
    trace_id: Optional[str] = None


class ExecuteWorkflowResponse(BaseModel):
    """Response from workflow execution"""

    success: bool
    execution_id: str
    execution: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    version: str
    uptime_seconds: float
    service: str


# Workflow CRUD Models (local to this service)
class CreateWorkflowRequestV2(BaseModel):
    """Request to create a workflow"""

    workflow_id: Optional[str] = None
    name: str
    created_by: str
    created_time_ms: Optional[int] = None
    nodes: List[Dict[str, Any]]
    connections: List[Dict[str, Any]]
    triggers: Optional[List[str]] = []


class CreateWorkflowResponse(BaseModel):
    """Response from creating a workflow"""

    workflow: Dict[str, Any]


class GetWorkflowResponse(BaseModel):
    """Response from getting a workflow"""

    found: bool
    workflow: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


# Create FastAPI app
app = FastAPI(
    title="Workflow Engine V2",
    description="Modern workflow execution engine with comprehensive user-friendly logging",
    version="2.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include logs router
app.include_router(logs_router)

# Global engine instance
engine = ModernExecutionEngine()

# Global workflow service instance
workflow_service = WorkflowServiceV2()

# Track app start time for uptime
import time

START_TIME = time.time()


@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info("🚀 Workflow Engine V2 starting up...")
    logger.info("✅ Modern execution engine initialized")
    logger.info("✅ User-friendly logging system active")
    logger.info("✅ Logs API endpoints ready")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("🛑 Workflow Engine V2 shutting down...")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        version="2.0.0",
        uptime_seconds=time.time() - START_TIME,
        service="workflow_engine_v2",
    )


@app.post("/api/v2/workflows/{workflow_id}/execute", response_model=ExecuteWorkflowResponse)
async def execute_workflow_by_id(
    workflow_id: str,
    request: dict,  # Accept flexible JSON payload
    background_tasks: BackgroundTasks,
):
    """Execute a workflow by ID with comprehensive logging (API Gateway compatible endpoint)"""

    try:
        logger.info(f"📝 Received workflow execution request for workflow {workflow_id}")

        # Extract parameters from API Gateway request format
        trigger_data = request.get("trigger", {})
        # TODO: In production, user_id should come from authenticated JWT token from API Gateway
        user_id = trigger_data.get("user_id")
        input_data = request.get("input_data") or request.get("trigger_data", {})
        trace_id = request.get("trace_id")
        async_execution = request.get("async_execution", True)

        # Retrieve the actual workflow from the workflow service
        workflow = workflow_service.get_workflow(workflow_id)
        if not workflow:
            logger.error(f"❌ Workflow {workflow_id} not found")
            return ExecuteWorkflowResponse(
                success=False,
                execution_id="",
                execution=None,
                error=f"Workflow {workflow_id} not found",
            )

        # Create TriggerInfo object
        trigger = TriggerInfo(
            trigger_type="MANUAL",
            trigger_data=input_data,
            user_id=user_id,
            timestamp=int(time.time() * 1000),
        )

        logger.info(f"🎯 Executing workflow: {workflow.metadata.name} (async: {async_execution})")

        if async_execution:
            # Return immediately for async execution
            execution_id = str(uuid.uuid4())
            logger.info(f"⚡ ASYNC: Starting background execution for {execution_id}")

            # Start actual background task execution
            async def execute_in_background():
                try:
                    logger.info(f"🚀 Background execution started for {execution_id}")
                    execution = await engine.execute_workflow(
                        workflow=workflow, trigger=trigger, trace_id=trace_id
                    )
                    logger.info(
                        f"✅ Background execution completed for {execution_id}: {execution.status}"
                    )
                except Exception as e:
                    logger.error(f"❌ Background execution failed for {execution_id}: {e}")

            # Add to background tasks
            background_tasks.add_task(execute_in_background)

            return ExecuteWorkflowResponse(
                success=True,
                execution_id=execution_id,
                execution={
                    "id": execution_id,
                    "execution_id": execution_id,
                    "workflow_id": workflow_id,
                    "status": "RUNNING",
                    "start_time": int(time.time() * 1000),
                    "end_time": None,
                },
            )
        else:
            # Execute synchronously
            execution = await engine.execute_workflow(
                workflow=workflow, trigger=trigger, trace_id=trace_id
            )

            logger.info(
                f"✅ Workflow execution completed: {execution.execution_id} (status: {execution.status})"
            )

            return ExecuteWorkflowResponse(
                success=execution.status.value == "COMPLETED",
                execution_id=execution.execution_id,
                execution={
                    "id": execution.id,
                    "execution_id": execution.execution_id,
                    "workflow_id": execution.workflow_id,
                    "status": execution.status.value,
                    "start_time": execution.start_time,
                    "end_time": execution.end_time,
                },
            )

    except Exception as e:
        logger.error(f"❌ Workflow execution failed: {str(e)}")
        logger.error(f"❌ Exception type: {type(e).__name__}")
        import traceback

        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        return ExecuteWorkflowResponse(success=False, execution_id="", error=str(e))


@app.post("/api/v2/execute", response_model=ExecuteWorkflowResponse)
async def execute_workflow(request: ExecuteWorkflowRequest, background_tasks: BackgroundTasks):
    """Execute a workflow with comprehensive logging (original endpoint)"""

    try:
        logger.info(f"📝 Received workflow execution request (original endpoint)")

        # Convert dict to Workflow object
        workflow_dict = request.workflow
        trigger_dict = request.trigger

        # Create Workflow object
        from shared.models.workflow_new import WorkflowMetadata

        workflow = Workflow(
            metadata=WorkflowMetadata(
                id=workflow_dict.get("id", "unknown"),
                name=workflow_dict.get("name", "Unnamed Workflow"),
                description=workflow_dict.get("description", ""),
                version=workflow_dict.get("version", 1),
            ),
            nodes=workflow_dict.get("nodes", []),
            connections=workflow_dict.get("connections", []),
        )

        # Create TriggerInfo object
        trigger = TriggerInfo(
            type=trigger_dict.get("type", "MANUAL"),
            source=trigger_dict.get("source", "api"),
            timestamp=trigger_dict.get("timestamp"),
        )

        logger.info(f"🎯 Executing workflow: {workflow.metadata.name} ({len(workflow.nodes)} nodes)")

        # Execute workflow
        execution = await engine.execute_workflow(
            workflow=workflow, trigger=trigger, trace_id=request.trace_id
        )

        logger.info(
            f"✅ Workflow execution completed: {execution.execution_id} (status: {execution.status})"
        )

        return ExecuteWorkflowResponse(
            success=execution.status.value == "COMPLETED",
            execution_id=execution.execution_id,
            execution={
                "id": execution.id,
                "execution_id": execution.execution_id,
                "workflow_id": execution.workflow_id,
                "status": execution.status.value,
                "start_time": execution.start_time,
                "end_time": execution.end_time,
            },
        )

    except Exception as e:
        logger.error(f"❌ Workflow execution failed: {str(e)}")
        logger.error(f"❌ Exception type: {type(e).__name__}")
        import traceback

        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        return ExecuteWorkflowResponse(success=False, execution_id="", error=str(e))


@app.get("/api/v2/executions/{execution_id}")
async def get_execution_status(execution_id: str):
    """Get execution status"""
    try:
        # Use workflow status manager to get real execution status
        status_manager = WorkflowStatusManagerV2()

        # Get execution status from database
        execution_status = await status_manager.get_execution_status(execution_id)

        if execution_status:
            return {
                "id": execution_id,
                "execution_id": execution_id,
                "workflow_id": execution_status.get("workflow_id", "unknown"),
                "status": execution_status.get("status", "UNKNOWN"),
                "start_time": execution_status.get("start_time"),
                "end_time": execution_status.get("end_time"),
                "created_at": execution_status.get("created_at"),
                "updated_at": execution_status.get("updated_at"),
            }
        else:
            # Execution not found
            raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")
    except Exception as e:
        logger.error(f"❌ Error getting execution status for {execution_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v2/executions/{execution_id}/progress")
async def get_execution_progress(execution_id: str):
    """Get execution progress"""
    try:
        progress = engine.get_execution_progress(execution_id)
        return {"execution_id": execution_id, "progress": progress}
    except Exception as e:
        return {"execution_id": execution_id, "error": str(e), "progress": {}}


@app.post("/api/v2/executions/{execution_id}/milestone")
async def log_milestone(
    execution_id: str, message: str, user_message: str, data: Optional[Dict[str, Any]] = None
):
    """Log a custom milestone for an execution"""
    try:
        engine.log_milestone(execution_id, message, user_message, data)
        return {"success": True, "execution_id": execution_id}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/v2/workflows/{workflow_id}/deploy")
async def deploy_workflow(workflow_id: str, request: dict):
    """Deploy a workflow to make it executable"""
    try:
        logger.info(f"🚀 Deploying workflow {workflow_id}")

        # Get the workflow
        workflow = workflow_service.get_workflow(workflow_id)
        if not workflow:
            logger.error(f"❌ Workflow {workflow_id} not found for deployment")
            return {"success": False, "error": f"Workflow {workflow_id} not found"}

        # Using imported DeploymentStatus enum instead of hardcoded strings

        # Update deployment status to deployed in database
        if workflow_service.supabase:
            try:
                workflow_service.supabase.table("workflows").update(
                    {
                        "deployment_status": DeploymentStatus.DEPLOYED.value,
                        "updated_at": int(time.time() * 1000),
                    }
                ).eq("id", workflow_id).execute()
                logger.info(f"💾 Updated deployment status for workflow {workflow_id} in database")
            except Exception as e:
                logger.warning(f"⚠️ Failed to update deployment status in database: {e}")

        # Update in-memory workflow
        workflow.metadata.deployment_status = DeploymentStatus.DEPLOYED.value
        workflow_service.update_workflow(workflow)

        logger.info(f"✅ Workflow {workflow_id} deployed successfully")

        return {
            "success": True,
            "deployment_id": str(uuid.uuid4()),
            "status": DeploymentStatus.DEPLOYED.value,
            "message": "Workflow deployed successfully",
            "workflow_id": workflow_id,
        }

    except Exception as e:
        logger.error(f"❌ Error deploying workflow {workflow_id}: {e}")
        return {"success": False, "error": str(e)}


# Cancel execution endpoint (v1 prefix for compatibility)
@app.post("/v1/executions/{execution_id}/cancel")
async def cancel_execution(execution_id: str):
    """Cancel execution"""
    try:
        logger.info(f"🛑 Cancel request for execution {execution_id}")
        # Use workflow status manager to cancel real execution
        status_manager = WorkflowStatusManagerV2()

        # Update execution status to CANCELLED
        from shared.models import ExecutionStatus

        success = await status_manager.update_execution_status(
            execution_id,
            ExecutionStatus.CANCELLED,
            error_message="Execution cancelled by user request",
        )

        return {
            "success": success,
            "message": f"Execution {execution_id} cancellation {'completed' if success else 'failed'}",
            "execution_id": execution_id,
        }
    except Exception as e:
        logger.error(f"❌ Error canceling execution {execution_id}: {e}")
        return {"success": False, "error": str(e), "execution_id": execution_id}


@app.get("/api/v2/workflows/{workflow_id}/executions")
async def get_execution_history(workflow_id: str, limit: int = 50):
    """Get execution history for a workflow"""
    try:
        logger.info(f"📋 Getting execution history for workflow {workflow_id}")

        # Use workflow status manager to get real execution data
        status_manager = WorkflowStatusManagerV2()

        # Get execution summary which includes recent executions
        summary = await status_manager.get_workflow_execution_summary(workflow_id)

        # Extract recent executions from summary
        executions = summary.get("recent_executions", [])

        # If we have executions, format them properly
        formatted_executions = []
        for execution in executions[:limit]:
            formatted_executions.append(
                {
                    "id": execution.get("execution_id", execution.get("id")),
                    "execution_id": execution.get("execution_id", execution.get("id")),
                    "workflow_id": workflow_id,
                    "status": execution.get("status", "UNKNOWN"),
                    "start_time": execution.get("start_time"),
                    "end_time": execution.get("end_time"),
                    "created_at": execution.get("created_at"),
                    "updated_at": execution.get("updated_at"),
                }
            )

        return {
            "workflows": formatted_executions,
            "total_count": summary.get("total_executions", len(formatted_executions)),
            "has_more": summary.get("total_executions", 0) > limit,
        }
    except Exception as e:
        logger.error(f"❌ Error getting execution history for workflow {workflow_id}: {e}")
        return {"workflows": [], "total_count": 0, "has_more": False}


# Workflow CRUD Endpoints
@app.post("/api/v2/workflows", response_model=CreateWorkflowResponse)
async def create_workflow(request: CreateWorkflowRequestV2):
    """Create a new workflow"""
    try:
        logger.info(f"📝 Creating workflow: {request.name} for user {request.created_by}")

        # Use provided workflow ID or generate one
        workflow_id = request.workflow_id or str(uuid.uuid4())
        created_time_ms = request.created_time_ms or int(time.time() * 1000)

        # Create workflow using the service
        workflow = workflow_service.create_workflow(
            workflow_id=workflow_id,
            name=request.name,
            created_by=request.created_by,
            created_time_ms=created_time_ms,
            nodes=request.nodes,
            connections=request.connections,
            triggers=request.triggers or [],
            metadata={},
        )

        logger.info(f"✅ Workflow created: {workflow_id}")

        # Convert workflow to dict for response
        workflow_dict = workflow.model_dump()

        # Add additional fields expected by API Gateway
        workflow_dict.update(
            {
                "id": workflow_id,
                "user_id": request.created_by,
                "active": True,
                "created_at": created_time_ms,
                "updated_at": created_time_ms,
                "deployment_status": DeploymentStatus.PENDING.value,
                "latest_execution_status": None,
                "latest_execution_time": None,
                "latest_execution_id": None,
            }
        )

        return CreateWorkflowResponse(workflow=workflow_dict)

    except Exception as e:
        logger.error(f"❌ Error creating workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create workflow: {str(e)}")


@app.get("/api/v2/workflows/{workflow_id}", response_model=GetWorkflowResponse)
async def get_workflow(workflow_id: str):
    """Get a workflow by ID"""
    try:
        logger.info(f"🔍 Getting workflow: {workflow_id}")

        workflow = workflow_service.get_workflow(workflow_id)
        if workflow:
            workflow_dict = workflow.model_dump()
            return GetWorkflowResponse(found=True, workflow=workflow_dict)
        else:
            return GetWorkflowResponse(found=False, message="Workflow not found")

    except Exception as e:
        logger.error(f"❌ Error getting workflow {workflow_id}: {e}")
        return GetWorkflowResponse(found=False, message=f"Error: {str(e)}")


# === V1 Compatibility Endpoints ===


@app.get("/v1/workflows")
async def list_workflows():
    """List all workflows (v1 compatibility)"""
    try:
        logger.info("📋 Listing all workflows")
        workflows = workflow_service.list_workflows()

        # Convert to v1 format
        workflow_list = []
        for workflow in workflows:
            workflow_dict = workflow.model_dump()
            workflow_list.append(
                {
                    "id": workflow_dict["metadata"]["id"],
                    "name": workflow_dict["metadata"]["name"],
                    "description": workflow_dict["metadata"].get("description"),
                    "deployment_status": workflow_dict["metadata"].get(
                        "deployment_status", DeploymentStatus.PENDING.value
                    ),
                    "created_at": workflow_dict["metadata"]["created_time"],
                    "updated_at": workflow_dict["metadata"]["created_time"],
                    "user_id": workflow_dict["metadata"]["created_by"],
                    "active": True,
                    "nodes": workflow_dict["nodes"],
                    "connections": workflow_dict["connections"],
                }
            )

        return {"workflows": workflow_list}

    except Exception as e:
        logger.error(f"❌ Error listing workflows: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.put("/v1/workflows/{workflow_id}")
async def update_workflow_v1(workflow_id: str, request: dict):
    """Update a workflow (v1 compatibility)"""
    try:
        logger.info(f"📝 Updating workflow {workflow_id}")

        # Get existing workflow
        existing_workflow = workflow_service.get_workflow(workflow_id)
        if not existing_workflow:
            raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

        # Update the workflow - for now just update the name and description
        if "name" in request:
            existing_workflow.metadata.name = request["name"]
        if "description" in request:
            existing_workflow.metadata.description = request["description"]

        # Update workflow
        updated_workflow = workflow_service.update_workflow(existing_workflow)

        return {"success": True, "workflow": updated_workflow.model_dump()}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/v1/workflows/{workflow_id}")
async def delete_workflow_v1(workflow_id: str):
    """Delete a workflow (v1 compatibility)"""
    try:
        logger.info(f"🗑️ Deleting workflow {workflow_id}")

        success = workflow_service.delete_workflow(workflow_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

        return {"success": True, "message": f"Workflow {workflow_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Node specifications endpoints
@app.get("/api/v1/node-specs")
async def get_node_specs():
    """Get all node specifications (v1 compatibility)"""
    try:
        logger.info("📋 Getting all node specifications")

        # Import the spec registry to get all available specs
        from shared.node_specs.registry import SPEC_REGISTRY

        specs = []
        for key, spec_class in SPEC_REGISTRY.items():
            node_type, subtype = key
            spec_instance = spec_class()

            specs.append(
                {
                    "node_type": node_type.value,
                    "subtype": subtype.value,
                    "name": spec_instance.name,
                    "description": spec_instance.description,
                    "input_ports": [port.model_dump() for port in spec_instance.input_ports],
                    "output_ports": [port.model_dump() for port in spec_instance.output_ports],
                    "configuration_schema": spec_instance.configuration_schema,
                    "category": getattr(spec_instance, "category", "general"),
                }
            )

        return {"specs": specs}

    except Exception as e:
        logger.error(f"❌ Error getting node specs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/node-specs/{node_type}")
async def get_node_spec(node_type: str):
    """Get specifications for a specific node type (v1 compatibility)"""
    try:
        logger.info(f"📋 Getting node specifications for {node_type}")

        from shared.node_specs.registry import SPEC_REGISTRY

        specs = []
        for key, spec_class in SPEC_REGISTRY.items():
            key_node_type, subtype = key
            if key_node_type.value == node_type:
                spec_instance = spec_class()
                specs.append(
                    {
                        "node_type": key_node_type.value,
                        "subtype": subtype.value,
                        "name": spec_instance.name,
                        "description": spec_instance.description,
                        "input_ports": [port.model_dump() for port in spec_instance.input_ports],
                        "output_ports": [port.model_dump() for port in spec_instance.output_ports],
                        "configuration_schema": spec_instance.configuration_schema,
                        "category": getattr(spec_instance, "category", "general"),
                    }
                )

        if not specs:
            raise HTTPException(
                status_code=404, detail=f"No specifications found for node type: {node_type}"
            )

        return {"specs": specs}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting node spec for {node_type}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Single node execution endpoint
@app.post("/v1/workflows/{workflow_id}/nodes/{node_id}/execute")
async def execute_single_node(workflow_id: str, node_id: str, request: dict):
    """Execute a single node for testing (v1 compatibility)"""
    try:
        logger.info(f"🎯 Executing single node {node_id} in workflow {workflow_id}")

        # Get the workflow
        workflow = workflow_service.get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

        # Find the specific node
        target_node = None
        for node in workflow.nodes:
            if node.id == node_id:
                target_node = node
                break

        if not target_node:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found in workflow")

        # Execute just this node using the modern engine
        execution_id = str(uuid.uuid4())

        # Create a simple execution context
        # Create minimal execution for single node test
        execution = Execution(
            execution_id=execution_id,
            workflow_id=workflow_id,
            status="RUNNING",
            trigger_data=request.get("trigger_data", {}),
            user_id=request.get("user_id", "test-user"),
            created_at=time.time() * 1000,
        )

        # Initialize the modern engine
        modern_engine = ModernExecutionEngine()

        # Prepare input data from request
        input_data = request.get("input_data", {})
        if not input_data and request.get("trigger_data"):
            input_data = {"main": request.get("trigger_data")}

        # Execute the single node
        node_result = await modern_engine._execute_single_node(
            execution=execution, node=target_node, input_data=input_data
        )

        logger.info(f"✅ Single node {node_id} executed successfully")

        return {
            "success": node_result.success,
            "execution_id": execution_id,
            "node_id": node_id,
            "status": "COMPLETED" if node_result.success else "FAILED",
            "message": f"Single node {node_id} executed successfully",
            "result": {
                "outputs": node_result.outputs,
                "duration_ms": node_result.duration_ms,
                "output_summary": node_result.output_summary,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error executing single node {node_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Execution logs endpoint
@app.get("/v1/workflows/executions/{execution_id}/logs")
async def get_execution_logs(execution_id: str):
    """Get execution logs (v1 compatibility)"""
    try:
        logger.info(f"📋 Getting execution logs for {execution_id}")

        # Use unified log service to get real logs
        log_service = UnifiedLogServiceV2()

        logs = await log_service.get_execution_logs(execution_id, limit=100)

        # Convert to expected format
        formatted_logs = []
        for log in logs:
            formatted_logs.append(
                {
                    "timestamp": log.get("timestamp", int(time.time() * 1000)),
                    "level": log.get("level", "INFO"),
                    "message": log.get("message", ""),
                    "node_id": log.get("node_id"),
                    "component": log.get("component", "engine"),
                }
            )

        return {"logs": formatted_logs, "execution_id": execution_id}

    except Exception as e:
        logger.error(f"❌ Error getting execution logs for {execution_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# === Credentials Management Endpoints ===


@app.post("/v1/credentials/check")
async def check_credentials(request: dict):
    """Check if credentials exist for a provider (v1 compatibility)"""
    try:
        user_id = request.get("user_id")
        provider = request.get("provider")

        logger.info(f"🔑 Checking credentials for user {user_id}, provider {provider}")

        # Use OAuth2 service to check real credentials
        oauth_service = OAuth2ServiceV2()

        # Check if we have a valid token for this user/provider
        token = await oauth_service.get_valid_token(user_id, provider)
        has_credentials = token is not None

        return {
            "success": True,
            "has_credentials": has_credentials,
            "provider": provider,
            "user_id": user_id,
            "message": "Credentials found" if has_credentials else "No valid credentials found",
        }

    except Exception as e:
        logger.error(f"❌ Error checking credentials: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/v1/credentials/status")
async def get_credentials_status(request: dict):
    """Get credentials status for multiple providers (v1 compatibility)"""
    try:
        user_id = request.get("user_id")
        providers = request.get("providers", [])

        logger.info(f"📊 Getting credentials status for user {user_id}")

        # Use OAuth2 service to get real status for each provider
        oauth_service = OAuth2ServiceV2()

        status = {}
        for provider in providers:
            # Check if we have valid credentials for this provider
            token = await oauth_service.get_valid_token(user_id, provider)
            has_credentials = token is not None

            status[provider] = {
                "has_credentials": has_credentials,
                "expires_at": None,  # OAuth service doesn't expose expiry details
                "last_validated": None,  # OAuth service doesn't track validation time
            }

        return {"success": True, "user_id": user_id, "credentials_status": status}

    except Exception as e:
        logger.error(f"❌ Error getting credentials status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/v1/credentials/get")
async def get_credentials(request: dict):
    """Get credentials for a provider (v1 compatibility)"""
    try:
        user_id = request.get("user_id")
        provider = request.get("provider")

        logger.info(f"🔑 Getting credentials for user {user_id}, provider {provider}")

        # Use OAuth2 service to get real credentials
        oauth_service = OAuth2ServiceV2()

        # Get valid token for this user/provider
        token = await oauth_service.get_valid_token(user_id, provider)

        if token:
            return {
                "success": True,
                "provider": provider,
                "user_id": user_id,
                "credentials": {"access_token": token},
                "message": "Credentials retrieved successfully",
            }
        else:
            return {
                "success": False,
                "provider": provider,
                "user_id": user_id,
                "credentials": None,
                "message": "No valid credentials found for this provider",
            }

    except Exception as e:
        logger.error(f"❌ Error getting credentials: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/v1/credentials/store")
async def store_credentials(request: dict):
    """Store credentials for a provider (v1 compatibility)"""
    try:
        user_id = request.get("user_id")
        provider = request.get("provider")
        credentials = request.get("credentials", {})

        logger.info(f"💾 Storing credentials for user {user_id}, provider {provider}")

        # Use OAuth2 service to store real credentials
        oauth_service = OAuth2ServiceV2()

        # Create TokenResponse from credentials

        access_token = credentials.get("access_token")
        refresh_token = credentials.get("refresh_token")

        if not access_token:
            return {
                "success": False,
                "provider": provider,
                "user_id": user_id,
                "message": "Missing access_token in credentials",
            }

        token_response = TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=credentials.get("expires_in", 3600),
        )

        # Store credentials using OAuth2 service
        success = await oauth_service.store_user_credentials(user_id, provider, token_response)

        return {
            "success": success,
            "provider": provider,
            "user_id": user_id,
            "message": "Credentials stored successfully"
            if success
            else "Failed to store credentials",
        }

    except Exception as e:
        logger.error(f"❌ Error storing credentials: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/v1/credentials/{user_id}/{provider}")
async def delete_credentials(user_id: str, provider: str):
    """Delete credentials for a provider (v1 compatibility)"""
    try:
        logger.info(f"🗑️ Deleting credentials for user {user_id}, provider {provider}")

        # Use OAuth2 service to delete real credentials
        oauth_service = OAuth2ServiceV2()

        # Delete credentials by marking them as invalid in the OAuth service
        try:
            # OAuth2 service doesn't have delete, but we can mark as invalid
            await oauth_service._mark_credentials_invalid(
                user_id, provider, "User requested deletion"
            )

            return {
                "success": True,
                "provider": provider,
                "user_id": user_id,
                "message": "Credentials deleted successfully",
            }
        except Exception as delete_error:
            logger.error(f"Failed to delete credentials: {delete_error}")
            return {
                "success": False,
                "provider": provider,
                "user_id": user_id,
                "message": "Failed to delete credentials",
            }

    except Exception as e:
        logger.error(f"❌ Error deleting credentials: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"🚨 Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500, content={"error": "Internal server error", "detail": str(exc)}
    )


def main():
    """Main entry point"""
    import os

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8002"))

    logger.info(f"🚀 Starting Workflow Engine V2 on {host}:{port}")

    uvicorn.run("main:app", host=host, port=port, reload=True, log_level="info")


if __name__ == "__main__":
    main()


__all__ = ["app", "engine"]
