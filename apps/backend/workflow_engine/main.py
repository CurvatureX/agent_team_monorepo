#!/usr/bin/env python3
"""
Workflow Engine - Simple FastAPI Application

A clean, simple workflow execution engine that:
1. Receives workflow execution requests via HTTP
2. Executes workflows through nodes
3. Returns results immediately for async execution
4. Supports synchronous execution for testing

No complex nested structures, just simple, clear code.
"""

# DNS resolution should work normally in Docker
# Removed IPv4-only patch that was causing resolution failures

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from shared.models.db_models import WorkflowStatusEnum

# Import our migrated modules
from config import settings
from database import Database
from executor import WorkflowExecutor
from models import (
    ExecuteWorkflowRequest,
    ExecuteWorkflowResponse,
    GetExecutionRequest,
    GetExecutionResponse,
)
from services.oauth2_service_lite import OAuth2ServiceLite
from utils.unicode_utils import clean_unicode_data, ensure_utf8_safe_dict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Workflow Engine", description="Simple, clean workflow execution engine", version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
db = Database()
executor = WorkflowExecutor(db)

# ---- Credentials API (migrated from legacy) ----


class CredentialCheckRequest(BaseModel):
    user_id: str
    provider: str


class CredentialCheckResponse(BaseModel):
    has_credentials: bool
    provider: str
    user_id: str


class CredentialStatusRequest(BaseModel):
    user_id: str


class CredentialStatusResponse(BaseModel):
    user_id: str
    providers: Dict[str, Dict[str, Any]]


class CredentialGetRequest(BaseModel):
    user_id: str
    provider: str


class CredentialGetResponse(BaseModel):
    has_credentials: bool
    provider: str
    user_id: str
    credentials: Optional[Dict[str, Any]] = None


class CredentialStoreRequest(BaseModel):
    user_id: str
    provider: str
    authorization_code: str
    client_id: str
    redirect_uri: str


class CredentialStoreResponse(BaseModel):
    success: bool
    message: str
    provider: str
    user_id: str


@app.post("/v1/credentials/check", response_model=CredentialCheckResponse)
async def check_credentials(request: CredentialCheckRequest):
    try:
        svc = OAuth2ServiceLite()
        token = await svc.get_valid_token(request.user_id, request.provider)
        return CredentialCheckResponse(
            has_credentials=token is not None,
            provider=request.provider,
            user_id=request.user_id,
        )
    except Exception as e:
        logger.error(f"Failed to check credentials: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check credentials: {str(e)}")


@app.post("/v1/credentials/status", response_model=CredentialStatusResponse)
async def get_authorization_status(request: CredentialStatusRequest):
    try:
        svc = OAuth2ServiceLite()
        providers = ["google", "github", "slack", "email", "api_call"]
        status: Dict[str, Dict[str, Any]] = {}

        if not getattr(svc, "supabase", None):
            return CredentialStatusResponse(user_id=request.user_id, providers={})

        for provider in providers:
            try:
                # map provider -> integration_id as in service
                integration_id = "google_calendar" if provider == "google" else provider
                resp = (
                    svc.supabase.table("oauth_tokens")
                    .select("access_token, refresh_token, expires_at, is_active, updated_at")
                    .eq("user_id", request.user_id)
                    .or_(f"provider.eq.{provider},integration_id.eq.{integration_id}")
                    .order("updated_at", desc=True)
                    .limit(1)
                    .execute()
                )
                if not resp.data:
                    status[provider] = {
                        "authorized": False,
                        "status": "not_authorized",
                        "message": "No authorization found. Please authorize this provider.",
                        "requires_auth": True,
                        "expires_at": None,
                        "last_updated": None,
                    }
                    continue

                row = resp.data[0]
                expires_at = row.get("expires_at")
                is_active = row.get("is_active", False)
                now_status = {
                    "authorized": bool(is_active),
                    "status": "valid" if is_active else "invalid",
                    "message": "Authorization is valid and active."
                    if is_active
                    else "Authorization invalid.",
                    "requires_auth": not is_active,
                    "expires_at": expires_at,
                    "last_updated": row.get("updated_at"),
                }
                status[provider] = now_status
            except Exception as e:
                status[provider] = {"authorized": False, "error": str(e)}

        return CredentialStatusResponse(user_id=request.user_id, providers=status)
    except Exception as e:
        logger.error(f"Failed to get authorization status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get authorization status: {str(e)}")


@app.post("/v1/credentials/get", response_model=CredentialGetResponse)
async def get_credentials(request: CredentialGetRequest):
    try:
        svc = OAuth2ServiceLite()
        if not getattr(svc, "supabase", None):
            return CredentialGetResponse(
                has_credentials=False, provider=request.provider, user_id=request.user_id
            )

        integration_id = "google_calendar" if request.provider == "google" else request.provider
        resp = (
            svc.supabase.table("oauth_tokens")
            .select("provider, access_token, refresh_token, expires_at, token_type, updated_at")
            .eq("user_id", request.user_id)
            .or_(f"provider.eq.{request.provider},integration_id.eq.{integration_id}")
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )

        if not resp.data:
            return CredentialGetResponse(
                has_credentials=False, provider=request.provider, user_id=request.user_id
            )

        row = resp.data[0]
        credentials = {
            "has_access_token": bool(row.get("access_token")),
            "expires_at": row.get("expires_at"),
            "token_type": row.get("token_type"),
            "updated_at": row.get("updated_at"),
        }
        return CredentialGetResponse(
            has_credentials=True,
            provider=request.provider,
            user_id=request.user_id,
            credentials=credentials,
        )
    except Exception as e:
        logger.error(f"Failed to get credentials: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get credentials: {str(e)}")


@app.post("/v1/credentials/store", response_model=CredentialStoreResponse)
async def store_credentials(request: CredentialStoreRequest):
    try:
        svc = OAuth2ServiceLite()
        token = await svc.exchange_code_for_token(
            code=request.authorization_code,
            client_id=request.client_id,
            redirect_uri=request.redirect_uri,
            provider=request.provider,
        )
        ok = await svc.store_user_credentials(request.user_id, request.provider, token)
        if not ok:
            raise HTTPException(status_code=500, detail="Failed to store credentials")
        return CredentialStoreResponse(
            success=True,
            message="Credentials stored successfully",
            provider=request.provider,
            user_id=request.user_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to store credentials: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to store credentials: {str(e)}")


@app.delete("/v1/credentials/{user_id}/{provider}")
async def delete_credentials(user_id: str, provider: str):
    try:
        svc = OAuth2ServiceLite()
        if not getattr(svc, "supabase", None):
            return {"success": False, "message": "Supabase not configured"}

        integration_id = "google_calendar" if provider == "google" else provider
        (
            svc.supabase.table("oauth_tokens")
            .delete()
            .eq("user_id", user_id)
            .or_(f"provider.eq.{provider},integration_id.eq.{integration_id}")
            .execute()
        )
        return {"success": True, "message": "Credentials deleted successfully"}
    except Exception as e:
        logger.error(f"Failed to delete credentials: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete credentials: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint with database connectivity test"""
    try:
        # Test database connection to ensure service is fully functional
        db_healthy = await db.test_connection()
        if db_healthy:
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}
        else:
            # Service can still be partially functional without DB
            return {
                "status": "degraded",
                "timestamp": datetime.now().isoformat(),
                "message": "Database connection issues",
            }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        # Return degraded instead of 503 for SSL issues
        if "SSL" in str(e) or "EOF" in str(e):
            return {
                "status": "degraded",
                "timestamp": datetime.now().isoformat(),
                "message": "SSL connection issues",
            }
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.post("/v1/workflows/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str, request: ExecuteWorkflowRequest, http_request: Request
):
    """
    Execute a workflow - THE CORE ENDPOINT

    This is where ALL workflow execution requests come through.
    Simple, clean, and handles both async and sync execution.
    """

    # 🔥 DEBUG: Log the request (this should ALWAYS appear if endpoint is hit)
    logger.debug(f"🔥 WORKFLOW EXECUTE ENDPOINT HIT!")
    logger.debug(f"🔥 Workflow ID: {workflow_id}")
    logger.debug(f"🔥 Request: {request.model_dump()}")
    logger.debug(f"🔥 Async execution: {request.async_execution}")

    try:
        # Clean request data to prevent Unicode issues
        request_dict = request.model_dump()
        cleaned_request_dict = clean_unicode_data(request_dict)

        # Generate execution ID
        execution_id = str(uuid4())

        # Get JWT token from request headers
        auth_header = http_request.headers.get("authorization", "")
        access_token = (
            auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else None
        )

        logger.info(f"🚀 Starting workflow execution: {workflow_id} -> {execution_id}")
        logger.info(f"🔄 Async mode: {request.async_execution}")

        if request.async_execution:
            # 🎯 ASYNC EXECUTION - Return immediately within 1 second
            logger.info(f"⚡ ASYNC: Starting background execution for {execution_id}")

            # Create execution record immediately
            await db.create_execution_record(execution_id, workflow_id, request.user_id, "NEW")

            # Start workflow in background (don't await) with cleaned data
            # Recreate request object with cleaned data for Unicode safety
            cleaned_request = ExecuteWorkflowRequest(**cleaned_request_dict)
            asyncio.create_task(
                executor.execute_workflow_background(
                    execution_id, workflow_id, cleaned_request, access_token
                )
            )

            # Return immediately - THIS IS THE KEY FIX!
            return ExecuteWorkflowResponse(
                execution_id=execution_id,
                status="NEW",
                success=True,
                message="Workflow execution started asynchronously",
            )
        else:
            # 🔄 SYNC EXECUTION - Wait for completion
            logger.info(f"🔄 SYNC: Executing workflow synchronously for {execution_id}")

            # Use cleaned request for Unicode safety
            cleaned_request = ExecuteWorkflowRequest(**cleaned_request_dict)
            result = await executor.execute_workflow_sync(
                execution_id, workflow_id, cleaned_request, access_token
            )

            return ExecuteWorkflowResponse(
                execution_id=execution_id,
                status=result.get("status", "COMPLETED"),
                success=result.get("success", True),
                message=result.get("message", "Workflow execution completed"),
            )

    except Exception as e:
        logger.error(f"❌ Workflow execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/executions/{execution_id}")
async def get_execution_status(execution_id: str):
    """Get execution status"""
    try:
        status = await db.get_execution_status(execution_id)
        if not status:
            raise HTTPException(status_code=404, detail="Execution not found")
        return status
    except Exception as e:
        logger.error(f"❌ Failed to get execution status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/workflows")
async def list_workflows():
    """List workflows"""
    try:
        workflows = await db.list_workflows()
        return {"workflows": workflows}
    except Exception as e:
        logger.error(f"❌ Failed to list workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/workflows")
async def create_workflow(workflow_data: dict):
    """Create a new workflow"""
    try:
        # Use Supabase repository to persist workflow (RLS via Authorization header optional)
        from services.supabase_repository import SupabaseWorkflowRepository

        # No request object here for headers; accept service role by default
        repo = SupabaseWorkflowRepository(access_token=None)
        # Minimal validation: ensure workflow_data is dict
        if not isinstance(workflow_data, dict):
            raise HTTPException(status_code=400, detail="Invalid workflow payload")

        # Handle both test format and production format
        if "workflow_data" not in workflow_data and (
            "nodes" in workflow_data or "connections" in workflow_data
        ):
            # This is test format - convert to database format
            logger.debug("Converting test format workflow data to database format")
            # For test environments, use NULL user_id to avoid foreign key constraint
            test_user_id = workflow_data.get("user_id")
            if not test_user_id or test_user_id == "test_user":
                test_user_id = None  # Use NULL to avoid foreign key constraint in tests

            import time

            now = int(time.time() * 1000)  # Unix timestamp in milliseconds (BIGINT)

            # Handle ID generation - convert non-UUID strings to UUIDs
            provided_id = workflow_data.get("id")
            if provided_id:
                try:
                    # Try to parse as UUID to validate format
                    import uuid

                    uuid.UUID(provided_id)
                    workflow_id = provided_id
                except ValueError:
                    # Not a valid UUID, generate one
                    workflow_id = str(uuid4())
                    logger.info(f"Converting non-UUID ID '{provided_id}' to UUID: {workflow_id}")
            else:
                workflow_id = str(uuid4())

            formatted_data = {
                "id": workflow_id,
                "name": workflow_data.get("name", "Test Workflow"),
                "description": workflow_data.get("description", ""),
                "user_id": test_user_id,
                "active": workflow_data.get("active", True),
                "tags": workflow_data.get("tags", []),
                "version": workflow_data.get("version", 1),
                "deployment_status": WorkflowStatusEnum.DRAFT.value,
                "created_at": now,
                "updated_at": now,
                "workflow_data": {
                    "nodes": workflow_data.get("nodes", []),
                    "connections": workflow_data.get("connections", {}),
                    "settings": workflow_data.get("settings", {}),
                    "static_data": workflow_data.get("static_data", {}),
                },
            }
            workflow_data = formatted_data

        created = await repo.create_workflow(workflow_data)
        if not created:
            raise HTTPException(status_code=500, detail="Failed to create workflow")
        return {"id": created.get("id"), "status": "created", "workflow": created}
    except Exception as e:
        logger.error(f"❌ Failed to create workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get workflow details from database"""
    try:
        logger.info(f"🔍 Getting workflow {workflow_id}")

        # Use SupabaseWorkflowRepository to avoid client corruption issues
        from services.supabase_repository import SupabaseWorkflowRepository

        logger.info(f"🔍 Using SupabaseWorkflowRepository to get workflow")
        repository = SupabaseWorkflowRepository()
        workflow_data = await repository.get_workflow(workflow_id)

        if not workflow_data:
            logger.warning(f"❌ Workflow {workflow_id} not found")
            return {"found": False, "workflow": None}
        logger.info(f"✅ Found workflow: {workflow_id}")

        # Transform the workflow data to match the canonical shared model structure
        # Extract nodes and connections from workflow_data JSONB field to top level
        transformed_workflow = dict(workflow_data)  # Start with all existing fields

        # Extract workflow definition from workflow_data JSONB field
        if workflow_data.get("workflow_data"):
            workflow_definition = workflow_data["workflow_data"]
            if isinstance(workflow_definition, dict):
                # Move nodes and connections to top level (overriding any existing ones)
                transformed_workflow["nodes"] = workflow_definition.get("nodes", [])
                transformed_workflow["connections"] = workflow_definition.get("connections", {})
                logger.info(
                    f"🔧 Extracted {len(transformed_workflow['nodes'])} nodes from workflow_data"
                )
            else:
                logger.warning(f"⚠️ workflow_data is not a dict for workflow {workflow_id}")
                # Initialize empty if workflow_data is not a dict
                transformed_workflow["nodes"] = []
                transformed_workflow["connections"] = {}
        else:
            logger.warning(f"⚠️ No workflow_data found for workflow {workflow_id}")
            # Initialize empty if no workflow_data
            transformed_workflow["nodes"] = []
            transformed_workflow["connections"] = {}

        return {"found": True, "workflow": transformed_workflow}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get workflow {workflow_id}: {e}")
        logger.error(f"❌ Exception type: {type(e)}")
        import traceback

        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/v1/workflows/{workflow_id}")
async def update_workflow(workflow_id: str, workflow_data: dict):
    """Update workflow"""
    try:
        from services.supabase_repository import SupabaseWorkflowRepository

        repo = SupabaseWorkflowRepository(access_token=None)
        if not isinstance(workflow_data, dict):
            raise HTTPException(status_code=400, detail="Invalid workflow payload")
        updated = await repo.update_workflow(workflow_id, workflow_data)
        if not updated:
            raise HTTPException(status_code=404, detail="Workflow not found or not updated")
        return {"id": workflow_id, "status": "updated", "workflow": updated}
    except Exception as e:
        logger.error(f"❌ Failed to update workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/v1/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """Delete workflow"""
    try:
        from services.supabase_repository import SupabaseWorkflowRepository

        repo = SupabaseWorkflowRepository(access_token=None)
        deleted = await repo.delete_workflow(workflow_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return {"id": workflow_id, "status": "deleted"}
    except Exception as e:
        logger.error(f"❌ Failed to delete workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/executions/{execution_id}/cancel")
async def cancel_execution(execution_id: str):
    """Cancel running execution"""
    try:
        # Update execution status in DB to CANCELLED
        await db.update_execution_status(execution_id, "CANCELLED")
        status = await db.get_execution_status(execution_id)
        if not status:
            raise HTTPException(status_code=404, detail="Execution not found")
        return {"execution_id": execution_id, "status": status.get("status", "CANCELLED")}
    except Exception as e:
        logger.error(f"❌ Failed to cancel execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/workflows/{workflow_id}/executions")
async def get_workflow_executions(workflow_id: str, limit: int = 20):
    """Get execution history for workflow - OPTIMIZED VERSION"""
    try:
        logger.info(f"🔍 Getting executions for workflow {workflow_id} (limit: {limit}) - optimized")

        # Use optimized SupabaseWorkflowRepository instead of slow database.py
        from services.supabase_repository import SupabaseWorkflowRepository

        # Use service role for performance (no RLS overhead for this read-only query)
        repository = SupabaseWorkflowRepository(access_token=None)
        executions, total_count = await repository.list_executions(
            workflow_id=workflow_id, limit=limit, offset=0
        )

        logger.info(f"✅ Found {len(executions)} executions for workflow {workflow_id} (optimized)")

        return {"workflow_id": workflow_id, "executions": executions, "total": total_count}
    except Exception as e:
        logger.error(f"❌ OPTIMIZATION FAILED - falling back to old method: {e}")
        # Fallback to old method if optimization fails
        executions = await db.get_workflow_executions(workflow_id, limit)
        return {"workflow_id": workflow_id, "executions": executions, "total": len(executions)}


@app.post("/v1/workflows/{workflow_id}/nodes/{node_id}/execute")
async def execute_single_node(workflow_id: str, node_id: str, request: dict):
    """Execute a single workflow node"""
    try:
        logger.info(f"🔧 Executing single node: {workflow_id}/{node_id}")

        # Get workflow definition
        workflow_definition = await executor.get_workflow_definition(workflow_id)
        if not workflow_definition:
            raise HTTPException(status_code=404, detail="Workflow not found")

        # Find the specific node
        node = None
        for n in workflow_definition.get("nodes", []):
            if n.get("id") == node_id:
                node = n
                break

        if not node:
            raise HTTPException(status_code=404, detail="Node not found")

        # Execute the node
        execution_id = str(uuid4())
        result = await executor.execute_single_node(
            node,
            workflow_id,
            execution_id,
            request.get("input_data", {}),
            request.get("access_token"),
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Single node execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_node_category(node_type: str) -> str:
    """Get node category - just use the node type directly for consistency."""
    from shared.models.node_enums import NodeType

    try:
        # Validate it's a valid NodeType and return it directly
        NodeType(node_type)
        return node_type.lower()
    except ValueError:
        return "unknown"


def _get_node_parameters(node_type: str) -> Dict[str, Any]:
    """Get comprehensive node parameter specifications from shared models."""
    from shared.models.node_enums import (
        ActionSubtype,
        AIAgentSubtype,
        AnthropicModel,
        ExternalActionSubtype,
        FlowSubtype,
        GoogleGeminiModel,
        HumanLoopSubtype,
        MemorySubtype,
        NodeType,
        OpenAIModel,
        ToolSubtype,
        TriggerSubtype,
        get_valid_subtypes,
    )

    try:
        node_type_enum = NodeType(node_type)
    except ValueError:
        return {}

    # Get valid subtypes for this node type
    valid_subtypes = get_valid_subtypes(node_type_enum)

    parameter_specs = {
        NodeType.TRIGGER: {
            "trigger_type": {
                "type": "string",
                "required": True,
                "description": "Type of trigger",
                "enum": valid_subtypes,
            },
            "webhook_url": {
                "type": "string",
                "required": False,
                "description": "Webhook URL for webhook triggers",
            },
            "schedule": {
                "type": "string",
                "required": False,
                "description": "Cron schedule for scheduled triggers",
            },
        },
        NodeType.AI_AGENT: {
            "ai_subtype": {
                "type": "string",
                "required": True,
                "description": "AI provider subtype",
                "enum": valid_subtypes,
            },
            "model_version": {
                "type": "string",
                "required": True,
                "description": "AI model version",
                "enum": list(OpenAIModel) + list(AnthropicModel) + list(GoogleGeminiModel),
            },
            "system_prompt": {
                "type": "string",
                "required": False,
                "description": "System prompt for AI",
            },
            "max_tokens": {
                "type": "integer",
                "required": False,
                "description": "Maximum tokens to generate",
                "minimum": 1,
                "maximum": 200000,
            },
            "temperature": {
                "type": "number",
                "required": False,
                "description": "Sampling temperature (0.0-2.0)",
                "minimum": 0.0,
                "maximum": 2.0,
            },
        },
        NodeType.ACTION: {
            "action_subtype": {
                "type": "string",
                "required": True,
                "description": "Type of action to perform",
                "enum": valid_subtypes,
            },
            "url": {"type": "string", "required": False, "description": "URL for HTTP requests"},
            "method": {
                "type": "string",
                "required": False,
                "description": "HTTP method",
                "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
            },
            "headers": {"type": "object", "required": False, "description": "HTTP headers"},
            "transform_script": {
                "type": "string",
                "required": False,
                "description": "Data transformation script",
            },
            "transform_type": {
                "type": "string",
                "required": False,
                "description": "Transformation type",
                "enum": ["jq", "jsonpath", "python", "mapping"],
            },
        },
        NodeType.EXTERNAL_ACTION: {
            "integration_subtype": {
                "type": "string",
                "required": True,
                "description": "External integration type",
                "enum": valid_subtypes,
            },
            "operation": {
                "type": "string",
                "required": True,
                "description": "Operation to perform",
            },
            "channel": {"type": "string", "required": False, "description": "Channel or recipient"},
            "message": {"type": "string", "required": False, "description": "Message content"},
            "webhook_url": {
                "type": "string",
                "required": False,
                "description": "Webhook URL for webhook actions",
            },
        },
        NodeType.FLOW: {
            "flow_subtype": {
                "type": "string",
                "required": True,
                "description": "Flow control type",
                "enum": valid_subtypes,
            },
            "condition": {
                "type": "string",
                "required": False,
                "description": "Condition expression for IF/WHILE nodes",
            },
            "cases": {
                "type": "array",
                "required": False,
                "description": "Switch cases for SWITCH nodes",
            },
            "loop_limit": {
                "type": "integer",
                "required": False,
                "description": "Maximum loop iterations",
                "minimum": 1,
                "maximum": 10000,
            },
        },
        NodeType.HUMAN_IN_THE_LOOP: {
            "interaction_subtype": {
                "type": "string",
                "required": True,
                "description": "Human interaction type",
                "enum": valid_subtypes,
            },
            "title": {"type": "string", "required": True, "description": "Interaction title"},
            "description": {
                "type": "string",
                "required": False,
                "description": "Interaction description",
            },
            "timeout_seconds": {
                "type": "integer",
                "required": False,
                "description": "Timeout in seconds",
                "minimum": 60,
                "maximum": 604800,  # 7 days
            },
            "channels": {
                "type": "array",
                "required": False,
                "description": "Notification channels",
                "items": {"type": "string"},
            },
        },
        NodeType.TOOL: {
            "tool_subtype": {
                "type": "string",
                "required": True,
                "description": "Tool type",
                "enum": valid_subtypes,
            },
            "tool_name": {"type": "string", "required": True, "description": "Tool name"},
            "operation": {"type": "string", "required": True, "description": "Tool operation"},
            "parameters": {"type": "object", "required": False, "description": "Tool parameters"},
        },
        NodeType.MEMORY: {
            "memory_subtype": {
                "type": "string",
                "required": True,
                "description": "Memory storage type",
                "enum": valid_subtypes,
            },
            "operation": {
                "type": "string",
                "required": True,
                "description": "Memory operation",
                "enum": ["store", "retrieve", "update", "delete", "search"],
            },
            "key": {"type": "string", "required": False, "description": "Memory key"},
            "ttl_seconds": {
                "type": "integer",
                "required": False,
                "description": "Time to live in seconds",
                "minimum": 60,
            },
        },
    }

    return parameter_specs.get(node_type_enum, {})


@app.get("/api/v1/node-specs")
async def list_node_specs():
    """List all node specifications"""
    try:
        from nodes import NodeExecutorFactory
        from nodes.base import NodeExecutionContext

        specs = []
        for node_type in NodeExecutorFactory.get_registered_types():
            try:
                # Create executor to get detailed specifications
                executor = NodeExecutorFactory.create_executor(node_type)

                # Get parameter information by inspecting validate_parameters method
                spec_info = {
                    "type": node_type,
                    "name": node_type.replace("_", " ").title(),
                    "description": executor.__doc__
                    or f"Executor for {node_type.replace('_', ' ').lower()} nodes",
                    "version": "1.0.0",
                    "category": _get_node_category(node_type),
                    "parameters": _get_node_parameters(node_type),
                    "input_ports": ["input_data"],
                    "output_ports": ["output_data", "error_data"],
                    "supports_async": True,
                    "validation_required": True,
                }

                specs.append(spec_info)

            except Exception as e:
                logger.warning(f"Failed to get detailed spec for {node_type}: {e}")
                # Fallback to basic spec
                specs.append(
                    {
                        "type": node_type,
                        "name": node_type.replace("_", " ").title(),
                        "description": f"Specification for {node_type} nodes",
                        "version": "1.0.0",
                        "category": "unknown",
                    }
                )

        return {"specs": specs, "total": len(specs), "generated_at": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"❌ Failed to list node specs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/node-specs/{node_type}")
async def get_node_spec(node_type: str):
    """Get specific node specification"""
    try:
        from nodes import NodeExecutorFactory

        if not NodeExecutorFactory.is_registered(node_type):
            raise HTTPException(status_code=404, detail="Node type not found")

        # Provide a minimal spec derived from registration; full specs TBD
        return {
            "type": node_type,
            "name": node_type.replace("_", " ").title(),
            "description": f"Node type {node_type}",
            "version": "1.0.0",
            "parameters": {"required": [], "optional": [], "schema": {}},
            "input_ports": [],
            "output_ports": [],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get node spec: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/workflows/executions/{execution_id}/logs")
async def get_execution_logs(
    execution_id: str,
    limit: int = 100,
    offset: int = 0,
    level: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
):
    """
    Get execution logs from database
    """
    try:
        logger.info(f"📋 Getting execution logs for {execution_id}")

        # Build query
        query = (
            db.client.table("workflow_execution_logs").select("*").eq("execution_id", execution_id)
        )

        # Add filters
        if level:
            query = query.eq("level", level.upper())
        if start_time:
            query = query.gte("created_at", start_time)
        if end_time:
            query = query.lte("created_at", end_time)

        # Order by created_at and apply pagination
        query = query.order("created_at", desc=False).range(offset, offset + limit - 1)

        result = query.execute()

        logs = result.data if result.data else []

        # Get total count (separate query for total)
        count_result = (
            db.client.table("workflow_execution_logs")
            .select("*", count="exact")
            .eq("execution_id", execution_id)
            .execute()
        )
        total_count = count_result.count if count_result.count is not None else 0

        logger.info(
            f"✅ Retrieved {len(logs)} logs for execution {execution_id} (total: {total_count})"
        )

        return {
            "execution_id": execution_id,
            "logs": logs,
            "total_count": total_count,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": (offset + len(logs)) < total_count,
            },
        }

    except Exception as e:
        logger.error(f"❌ Failed to get execution logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
