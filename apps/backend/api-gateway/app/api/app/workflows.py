"""
Workflow API endpoints with authentication and enhanced gRPC client integration
支持认证的工作流API端点
"""

import logging
import socket
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.core.database import get_supabase_admin
from app.dependencies import AuthenticatedDeps
from app.exceptions import NotFoundError, ValidationError
from app.models import (
    DeploymentResult,
    DeploymentStatus,
    ExecutionResult,
    ManualTriggerSpec,
    NewWorkflow,
    NodeTemplateListResponse,
    ResponseModel,
    Workflow,
    WorkflowCreate,
    WorkflowExecutionRequest,
    WorkflowExecutionResponse,
    WorkflowResponse,
    WorkflowUpdate,
)
from app.services.workflow_engine_http_client import get_workflow_engine_client
from app.services.workflow_scheduler_http_client import get_workflow_scheduler_client

# Node converter no longer needed - using unified models directly
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Legacy import removed - ExecuteWorkflowRequest not used in this file

logger = logging.getLogger(__name__)
router = APIRouter()

# Workflow validation and data cache
WORKFLOW_CACHE = {}
CACHE_TTL = 300  # 5 minutes TTL for workflow data


class WorkflowSummary(BaseModel):
    """Lightweight workflow model for list view - excludes detailed nodes"""

    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    tags: List[str] = []
    active: bool = True
    created_at: Optional[int] = None
    updated_at: Optional[int] = None
    version: str = "1.0"
    logo_url: Optional[str] = None  # Mapped from icon_url

    # Keep deployment and execution status for list view
    deployment_status: Optional[str] = None
    latest_execution_status: Optional[str] = None
    latest_execution_time: Optional[str] = None


class WorkflowListResponseModel(BaseModel):
    """Response model for workflow list"""

    workflows: List[WorkflowSummary]
    total_count: int
    has_more: bool


class WorkflowDetailResponse(BaseModel):
    """Workflow detail response with logo_url field"""

    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    nodes: List[Dict[str, Any]]  # Keep nodes for detail view
    connections: Dict[str, Any] = {}
    settings: Dict[str, Any] = {}
    static_data: Dict[str, str] = {}
    pin_data: Dict[str, str] = {}
    tags: List[str] = []
    active: bool = True
    created_at: Optional[int] = None
    updated_at: Optional[int] = None
    version: str = "1.0"
    logo_url: Optional[str] = None  # Mapped from icon_url


class WorkflowDetailResponseModel(BaseModel):
    """Response wrapper for workflow detail"""

    workflow: WorkflowDetailResponse
    message: Optional[str] = None


def _get_cached_workflow(workflow_id: str, user_id: str):
    """Get cached workflow data if available and not expired"""
    cache_key = f"{workflow_id}_{user_id}"
    if cache_key in WORKFLOW_CACHE:
        cached_data, timestamp = WORKFLOW_CACHE[cache_key]
        if time.time() - timestamp < CACHE_TTL:
            logger.info(f"📋 Using cached workflow data for {workflow_id}")
            return cached_data
        else:
            # Remove expired cache entry
            del WORKFLOW_CACHE[cache_key]
    return None


def _cache_workflow(workflow_id: str, user_id: str, workflow_data: dict):
    """Cache workflow data for future use"""
    cache_key = f"{workflow_id}_{user_id}"
    WORKFLOW_CACHE[cache_key] = (workflow_data, time.time())
    logger.info(f"📋 Cached workflow data for {workflow_id}")


def _clear_workflow_cache(workflow_id: str, user_id: str):
    """Clear cached workflow data when workflow is modified"""
    cache_key = f"{workflow_id}_{user_id}"
    if cache_key in WORKFLOW_CACHE:
        del WORKFLOW_CACHE[cache_key]
        logger.info(f"📋 Cleared cached workflow data for {workflow_id}")


async def _fetch_oauth_tokens_with_retry(user_id: str) -> List[Dict[str, Any]]:
    """
    Fetch OAuth tokens with retry logic for DNS resolution failures.
    Applies the same robust patterns used in workflow scheduler database connections.
    """
    max_retries = 3
    retry_delay = 1.0

    for attempt in range(max_retries):
        try:
            logger.debug(
                f"Fetching OAuth tokens for user {user_id} (attempt {attempt + 1}/{max_retries})"
            )

            # Prefer direct Postgres for performance
            try:
                from app.core.database_direct import get_direct_pg_manager

                direct = await get_direct_pg_manager()
                tokens = await direct.get_user_oauth_tokens_fast(user_id)
                logger.debug(f"✅ Fetched OAuth tokens via direct SQL for user {user_id}")
                return tokens
            except Exception as de:
                logger.warning(
                    f"⚠️ Direct SQL token fetch failed, falling back to Supabase REST: {de}"
                )

            # Fallback to Supabase admin client
            supabase = get_supabase_admin()
            if not supabase:
                logger.error("❌ Failed to get Supabase admin client")
                return []

            oauth_tokens_result = (
                supabase.table("oauth_tokens")
                .select("provider, integration_id, access_token, refresh_token, credential_data")
                .eq("user_id", user_id)
                .eq("is_active", True)
                .execute()
            )

            logger.debug(f"✅ Successfully fetched OAuth tokens for user {user_id}")
            return oauth_tokens_result.data or []

        except Exception as e:
            error_str = str(e).lower()
            # Classify network vs other errors like workflow engine
            if any(
                keyword in error_str
                for keyword in [
                    "ssl",
                    "eof",
                    "connection",
                    "timeout",
                    "dns",
                    "resolve",
                    "name resolution",
                    "temporary failure",
                    "network",
                    "gaierror",
                ]
            ):
                logger.warning(
                    f"⚠️ Network error fetching OAuth tokens (attempt {attempt + 1}): {type(e).__name__}: {e}"
                )
                if attempt < max_retries - 1:
                    logger.info(f"Retrying OAuth token fetch in {retry_delay} seconds...")
                    time.sleep(
                        retry_delay
                    )  # Use sync sleep like workflow engine for network issues
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"❌ All {max_retries} OAuth token fetch attempts failed")
                    return []  # Return empty list instead of raising
            else:
                # Non-network error - re-raise immediately
                logger.error(f"❌ OAuth token fetch failed with non-network error: {e}")
                return []  # Return empty list for graceful degradation


async def _inject_oauth_credentials(workflow_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Inject OAuth credentials from oauth_tokens table into workflow nodes.

    Updates trigger nodes and external action nodes with their corresponding OAuth tokens.
    """
    try:
        logger.info(f"🔐 Injecting OAuth credentials for workflow deployment - user {user_id}")

        # Fetch user's OAuth tokens with retry logic
        oauth_tokens_data = await _fetch_oauth_tokens_with_retry(user_id)

        if not oauth_tokens_data:
            logger.info("🔐 No OAuth tokens found for user, skipping credential injection")
            return workflow_data

        # Create provider -> token mapping with integration_id handling
        provider_tokens = {}
        for token_record in oauth_tokens_data:
            provider = token_record["provider"]
            integration_id = token_record["integration_id"]

            # Map integration_id to provider names used by workflow nodes
            provider_key = provider
            if integration_id == "github_app":
                provider_key = "github"
            elif integration_id == "google_calendar":
                provider_key = "google_calendar"
            elif integration_id == "gmail":
                provider_key = "gmail"
            # slack, notion use provider name directly

            provider_tokens[provider_key] = {
                "access_token": token_record["access_token"],
                "refresh_token": token_record["refresh_token"],
                "credential_data": token_record["credential_data"] or {},
                "integration_id": integration_id,
                "provider": provider,
            }

        logger.info(f"🔐 Found OAuth tokens for providers: {list(provider_tokens.keys())}")

        # Make a deep copy to avoid modifying the original
        updated_workflow = workflow_data.copy()

        # Process nodes in workflow_data (could be in different formats)
        nodes_data = None
        if "nodes" in updated_workflow:
            nodes_data = updated_workflow["nodes"]
        elif "workflow_data" in updated_workflow and "nodes" in updated_workflow["workflow_data"]:
            nodes_data = updated_workflow["workflow_data"]["nodes"]

        if not nodes_data:
            logger.warning("🔐 No nodes found in workflow data structure")
            return workflow_data

        # Track injected credentials for logging
        injected_count = 0

        # Process each node
        for node in nodes_data:
            node_type = node.get("node_type", node.get("type"))
            node_subtype = node.get("node_subtype", node.get("subtype"))

            if not node_type or not node_subtype:
                continue

            # Initialize parameters if not present
            if "parameters" not in node:
                node["parameters"] = {}

            # Handle External Action nodes
            if node_type == "EXTERNAL_ACTION":
                token_injected = False

                if node_subtype == "GITHUB" and "github" in provider_tokens:
                    # GitHub external actions use auth_token parameter
                    node["parameters"]["auth_token"] = provider_tokens["github"]["access_token"]
                    token_injected = True

                elif node_subtype == "SLACK" and "slack" in provider_tokens:
                    # Slack external actions use bot_token parameter
                    node["parameters"]["bot_token"] = provider_tokens["slack"]["access_token"]
                    token_injected = True

                elif node_subtype == "NOTION" and "notion" in provider_tokens:
                    # Notion external actions use access_token parameter
                    node["parameters"]["access_token"] = provider_tokens["notion"]["access_token"]
                    token_injected = True

                elif node_subtype == "GOOGLE_CALENDAR" and "google_calendar" in provider_tokens:
                    # Google Calendar external actions use access_token parameter
                    node["parameters"]["access_token"] = provider_tokens["google_calendar"][
                        "access_token"
                    ]
                    token_injected = True

                elif node_subtype == "EMAIL" and "gmail" in provider_tokens:
                    # Gmail external actions use oauth_token parameter for OAuth flow
                    node["parameters"]["oauth_token"] = provider_tokens["gmail"]["access_token"]
                    token_injected = True

                if token_injected:
                    injected_count += 1
                    logger.info(
                        f"🔐 Injected {node_subtype} credentials for node {node.get('node_id', 'unknown')}"
                    )

            # Handle Action nodes (for HTTP_REQUEST with authentication)
            elif node_type == "ACTION":
                if node_subtype == "HTTP_REQUEST":
                    # HTTP_REQUEST nodes with authentication may need OAuth tokens
                    auth_method = node["parameters"].get("authentication", "none")
                    if auth_method in ["bearer", "api_key"]:
                        # Try to inject token from any available provider if not already specified
                        if not node["parameters"].get("auth_token"):
                            # Prefer github for code-related APIs, then slack, then others
                            for provider in ["github", "slack", "notion", "google_calendar"]:
                                if provider in provider_tokens:
                                    node["parameters"]["auth_token"] = provider_tokens[provider][
                                        "access_token"
                                    ]
                                    logger.info(
                                        f"🔐 Injected {provider} token for HTTP_REQUEST node {node.get('node_id', 'unknown')}"
                                    )
                                    injected_count += 1
                                    break

            # Handle Trigger nodes - these need credentials for webhook setup and event processing
            elif node_type == "TRIGGER":
                if node_subtype == "SLACK":
                    # Slack triggers don't directly execute with bot tokens during runtime
                    # but may need workspace info for webhook registration
                    if "slack" in provider_tokens:
                        slack_data = provider_tokens["slack"]["credential_data"]
                        if "workspace_id" in slack_data:
                            node["parameters"]["workspace_id"] = slack_data["workspace_id"]
                        if "team_id" in slack_data:
                            node["parameters"]["team_id"] = slack_data["team_id"]
                        injected_count += 1
                        logger.info(
                            f"🔐 Injected Slack workspace info for trigger node {node.get('node_id', 'unknown')}"
                        )

                elif node_subtype == "GITHUB":
                    # GitHub triggers use GitHub App installation managed by scheduler
                    # Inject installation_id if available for webhook registration
                    if "github" in provider_tokens:
                        github_data = provider_tokens["github"]["credential_data"]
                        if "installation_id" in github_data:
                            node["parameters"]["github_app_installation_id"] = github_data[
                                "installation_id"
                            ]
                            injected_count += 1
                            logger.info(
                                f"🔐 Injected GitHub installation_id for trigger node {node.get('node_id', 'unknown')}"
                            )

                elif node_subtype == "EMAIL":
                    # Email triggers might need OAuth credentials for Gmail monitoring
                    if "gmail" in provider_tokens:
                        node["parameters"]["oauth_token"] = provider_tokens["gmail"]["access_token"]
                        injected_count += 1
                        logger.info(
                            f"🔐 Injected Gmail OAuth for email trigger node {node.get('node_id', 'unknown')}"
                        )

                # Note: WEBHOOK and CRON triggers typically don't need OAuth credentials
                # MANUAL triggers are user-initiated and don't need external credentials

        logger.info(f"✅ OAuth credential injection completed: {injected_count} nodes updated")
        return updated_workflow

    except Exception as e:
        logger.error(f"❌ Error injecting OAuth credentials: {e}")
        # Return original workflow data if credential injection fails
        # This ensures deployment continues even if credential injection has issues
        return workflow_data


@router.get("/node-templates", response_model=NodeTemplateListResponse)
async def list_all_node_templates(
    category: Optional[str] = None,
    node_type: Optional[str] = None,
    include_system: bool = True,
    deps: AuthenticatedDeps = Depends(),
):
    """
    List all available node templates from node specs.

    This endpoint has been updated to use the node specs system instead of
    the deprecated node_templates database table.
    """
    try:
        logger.info("Listing node templates from node specs system")

        # Import here to avoid circular imports
        from shared.services.node_specs_api_service import get_node_specs_api_service

        # Use node specs service directly for better performance and consistency
        specs_service = get_node_specs_api_service()
        templates = specs_service.list_all_node_templates(
            category_filter=category, type_filter=node_type, include_system_templates=include_system
        )

        logger.info(f"Retrieved {len(templates)} node templates from specs")
        return NodeTemplateListResponse(node_templates=templates)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing node templates from specs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/")
async def create_workflow(request: WorkflowCreate, deps: AuthenticatedDeps = Depends()):
    """
    Create a new workflow
    创建新的工作流
    """
    try:
        logger.info(f"📝 Creating workflow for user {deps.current_user.sub}")

        # Generate random icon_url
        from shared.utils.icon_utils import generate_random_icon_url

        icon_url = generate_random_icon_url()
        logger.info(f"🎨 Generated random icon_url: {icon_url}")

        # Get HTTP client
        settings = get_settings()

        http_client = await get_workflow_engine_client()

        # Pass nodes directly - they should already be in NodeData format from WorkflowCreateRequest
        nodes_list = []
        if request.nodes:
            nodes_list = [node.model_dump() for node in request.nodes]

        # Use connections as-is - now a list of Connection objects
        connections_list = (
            [conn.model_dump() for conn in request.connections] if request.connections else []
        )

        # Convert settings to dict if it's an object
        settings_dict = {}
        if request.settings:
            if hasattr(request.settings, "model_dump"):
                settings_dict = request.settings.model_dump()
            elif hasattr(request.settings, "dict"):
                settings_dict = request.settings.dict()
            elif isinstance(request.settings, dict):
                settings_dict = request.settings
            else:
                settings_dict = {}

        # Create workflow via HTTP
        result = await http_client.create_workflow(
            name=request.name,
            description=request.description,
            nodes=nodes_list,
            connections=connections_list,
            settings=settings_dict,
            static_data=getattr(request, "static_data", None) or {},
            tags=request.tags or [],
            user_id=deps.current_user.sub,
            trace_id=getattr(deps.request.state, "trace_id", None),
            icon_url=icon_url,
        )

        # Debug logging to understand response format
        logger.info(f"🐛 DEBUG: Workflow Engine response: {result}")

        # Check for Workflow Engine response format: {"id": "...", "status": "created", "workflow": {...}}
        if not result.get("workflow", {}).get("id") or result.get("status") != "created":
            logger.error(f"❌ Invalid response format from Workflow Engine: {result}")
            raise HTTPException(status_code=500, detail="Failed to create workflow")

        workflow_data = result["workflow"]

        logger.info(f"✅ Workflow created: {workflow_data['id']}")

        # Return result from workflow engine v2 as-is using JSONResponse to bypass validation
        return JSONResponse(content=result)

    except (ValidationError, HTTPException):
        raise
    except Exception as e:
        logger.error(f"❌ Error creating workflow: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str, deps: AuthenticatedDeps = Depends()):
    """
    Get a workflow with user access control
    通过ID获取工作流（支持用户访问控制）
    """
    try:
        logger.info(f"🔍 Getting workflow {workflow_id} using RLS with JWT token")

        # Get HTTP client
        settings = get_settings()

        http_client = await get_workflow_engine_client()

        # Get workflow via HTTP with JWT token for RLS
        result = await http_client.get_workflow(workflow_id, deps.access_token)
        if not result.get("found", False) or not result.get("workflow"):
            raise NotFoundError("Workflow")

        logger.info(f"✅ Workflow retrieved: {workflow_id}")

        # Return the original GetWorkflowResponse structure from workflow engine
        # This preserves the "found" field that the frontend expects
        return result

    except (NotFoundError, HTTPException):
        raise
    except Exception as e:
        logger.error(f"❌ Error getting workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: str,
    request_body: Dict[str, Any] = Body(...),  # Accept raw dict to handle flexible updates
    deps: AuthenticatedDeps = Depends(),
):
    """
    Update a workflow with user access control
    更新工作流（支持用户访问控制）
    """
    try:
        logger.info(f"📝 Updating workflow {workflow_id} for user {deps.current_user.sub}")
        logger.info(f"📦 Received request body: {request_body}")

        # Remove any workflow_id or user_id from the request body
        request_body.pop("workflow_id", None)
        request_body.pop("user_id", None)

        # Build the update request with required fields
        update_request = WorkflowUpdate(
            workflow_id=workflow_id,
            user_id=deps.current_user.sub,
            **request_body,  # All other fields from request
        )

        # Get HTTP client
        settings = get_settings()
        http_client = await get_workflow_engine_client()

        # Get only the fields that were provided (exclude_none=True)
        update_data = update_request.model_dump(exclude_none=True)

        # Debug log
        logger.info(f"📦 Update data being sent: {update_data}")

        # Remove workflow_id and user_id to avoid duplication in the call
        update_data.pop("workflow_id", None)
        update_data.pop("user_id", None)

        result = await http_client.update_workflow(
            workflow_id=workflow_id, user_id=deps.current_user.sub, **update_data
        )

        if not result.get("success", False) or not result.get("workflow"):
            raise HTTPException(status_code=500, detail="Failed to update workflow")

        # Create workflow object
        workflow = Workflow(**result["workflow"])

        # Clear cache since workflow was updated
        _clear_workflow_cache(workflow_id, deps.current_user.sub)

        logger.info(f"✅ Workflow updated: {workflow_id}")

        return WorkflowResponse(workflow=workflow, message="Workflow updated successfully")

    except (ValidationError, NotFoundError, HTTPException):
        raise
    except Exception as e:
        logger.error(f"❌ Error updating workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{workflow_id}", response_model=ResponseModel)
async def delete_workflow(workflow_id: str, deps: AuthenticatedDeps = Depends()):
    """
    Delete a workflow with user access control
    删除工作流（支持用户访问控制）
    """
    try:
        logger.info(f"🗑️ Deleting workflow {workflow_id} for user {deps.current_user.sub}")

        # Get HTTP client
        settings = get_settings()

        http_client = await get_workflow_engine_client()

        # Delete workflow via HTTP
        result = await http_client.delete_workflow(workflow_id, deps.current_user.sub)

        if not result.get("success", False):
            if "not found" in result.get("error", "").lower():
                raise NotFoundError("Workflow")
            raise HTTPException(status_code=500, detail="Failed to delete workflow")

        # Clear cache since workflow was deleted
        _clear_workflow_cache(workflow_id, deps.current_user.sub)

        logger.info(f"✅ Workflow deleted: {workflow_id}")

        return ResponseModel(success=True, message="Workflow deleted successfully")

    except (NotFoundError, HTTPException):
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=WorkflowListResponseModel)
async def list_workflows(
    active_only: bool = True,
    tags: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    deps: AuthenticatedDeps = Depends(),
):
    """
    List workflows for the current user
    列出当前用户的工作流
    """
    try:
        logger.info(f"📋 Listing workflows for user {deps.current_user.sub}")

        # Get HTTP client
        settings = get_settings()

        http_client = await get_workflow_engine_client()

        # Parse tags
        tag_list = tags.split(",") if tags else None

        # List workflows via HTTP using JWT token for RLS
        result = await http_client.list_workflows(
            access_token=deps.access_token,  # Pass JWT token for RLS
            active_only=active_only,
            tags=tag_list,
            limit=limit,
            offset=offset,
        )

        # Convert workflows to lightweight summaries with logo_url
        workflow_summaries = []
        for workflow_data in result.get("workflows", []):
            # Handle None values for tags - ensure it's always a list
            tags_value = workflow_data.get("tags")
            if tags_value is None:
                tags_value = []

            summary = WorkflowSummary(
                id=workflow_data.get("id"),
                name=workflow_data.get("name", ""),
                description=workflow_data.get("description"),
                tags=tags_value,
                active=workflow_data.get("active", True),
                created_at=workflow_data.get("created_at"),
                updated_at=workflow_data.get("updated_at"),
                version=workflow_data.get("version", "1.0"),
                logo_url=workflow_data.get("icon_url"),  # Map icon_url to logo_url
                deployment_status=workflow_data.get("deployment_status"),
                latest_execution_status=workflow_data.get("latest_execution_status"),
                latest_execution_time=workflow_data.get("latest_execution_time"),
            )
            workflow_summaries.append(summary)

        logger.info(f"✅ Listed {len(workflow_summaries)} workflows")

        return WorkflowListResponseModel(
            workflows=workflow_summaries,
            total_count=result.get("total_count", len(workflow_summaries)),
            has_more=result.get("has_more", False),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error listing workflows: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{workflow_id}/execute", response_model=WorkflowExecutionResponse)
async def execute_workflow(
    workflow_id: str,
    execution_request: WorkflowExecutionRequest,
    deps: AuthenticatedDeps = Depends(),
):
    """
    Execute a workflow with user access control
    执行工作流（支持用户访问控制）
    """
    try:
        logger.info(f"🚀 Executing workflow {workflow_id} for user {deps.current_user.sub}")

        # Get HTTP client
        settings = get_settings()

        http_client = await get_workflow_engine_client()

        # Execute workflow via HTTP
        result = await http_client.execute_workflow(
            workflow_id,
            deps.current_user.sub,
            execution_request.inputs,
            trace_id=getattr(deps.request.state, "trace_id", None),
            start_from_node=execution_request.start_from_node,
            skip_trigger_validation=execution_request.skip_trigger_validation,
        )

        if not result.get("success", False) or not result.get("execution_id"):
            raise HTTPException(status_code=500, detail="Failed to execute workflow")

        logger.info(f"✅ Workflow execution started: {result['execution_id']}")

        # Add workflow_id to the result for the response model
        result["workflow_id"] = workflow_id

        return WorkflowExecutionResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error executing workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{workflow_id}/trigger/manual", response_model=ExecutionResult)
async def trigger_manual_workflow(
    workflow_id: str,
    request: ManualTriggerSpec,
    deps: AuthenticatedDeps = Depends(),
):
    """
    Manually trigger a workflow execution
    手动触发工作流执行
    """
    try:
        logger.info(
            f"🚀 Manual trigger request for workflow {workflow_id} by user {deps.current_user.sub}"
        )

        # Get workflow scheduler client
        scheduler_client = await get_workflow_scheduler_client()

        # Trigger manual workflow
        result = await scheduler_client.trigger_manual_workflow(
            workflow_id=workflow_id,
            user_id=deps.current_user.sub,
            trace_id=getattr(deps.request.state, "trace_id", None),
            access_token=deps.access_token,
        )

        # Handle errors
        if not result.get("success", True) and result.get("error"):
            error_msg = result.get("error", "Unknown error")
            if "not found" in error_msg.lower():
                raise HTTPException(
                    status_code=404, detail="Workflow not found or no manual triggers configured"
                )
            raise HTTPException(status_code=500, detail=f"Manual trigger failed: {error_msg}")

        logger.info(
            f"✅ Manual trigger successful: {workflow_id}, execution_id: {result.get('execution_id', 'N/A')}"
        )

        # Return ExecutionResult
        return ExecutionResult(
            execution_id=result.get("execution_id", ""),
            status=result.get("status", "unknown"),
            message=result.get("message", "Manual trigger completed"),
            trigger_data=result.get("trigger_data", {}),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error triggering manual workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{workflow_id}/deploy", response_model=DeploymentResult)
async def deploy_workflow(
    workflow_id: str,
    deps: AuthenticatedDeps = Depends(),
):
    """
    Deploy a workflow with its trigger configuration
    部署工作流及其触发器配置
    """
    try:
        logger.info(f"📦 Deploying workflow {workflow_id} for user {deps.current_user.sub}")

        # Check cache first to avoid redundant workflow fetches
        cached_workflow = _get_cached_workflow(workflow_id, deps.current_user.sub)

        if cached_workflow:
            workflow_data = cached_workflow
            logger.info(f"📋 Using cached workflow data for deployment: {workflow_id}")
        else:
            # Get the workflow from workflow engine
            workflow_engine_client = await get_workflow_engine_client()
            workflow_result = await workflow_engine_client.get_workflow(
                workflow_id, deps.current_user.sub
            )

            # Check if workflow exists (workflow engine returns found:true/false and workflow data)
            if not workflow_result.get("found", False) or not workflow_result.get("workflow"):
                logger.error(f"❌ Error deploying workflow {workflow_id}: Workflow not found")
                raise HTTPException(status_code=404, detail="Workflow not found")

            workflow_data = workflow_result["workflow"]

            # Cache the workflow data for future deployments
            _cache_workflow(workflow_id, deps.current_user.sub, workflow_data)

        # Inject OAuth credentials into workflow nodes
        workflow_data_with_credentials = await _inject_oauth_credentials(
            workflow_data, deps.current_user.sub
        )

        # Update workflow with injected credentials before deployment
        if workflow_data_with_credentials != workflow_data:
            logger.info(f"🔐 Updating workflow {workflow_id} with injected OAuth credentials")

            # Update the workflow in the workflow engine with the injected credentials
            workflow_engine_client = await get_workflow_engine_client()

            # Extract the workflow data structure for the update
            update_data = {}
            if "nodes" in workflow_data_with_credentials:
                update_data["nodes"] = workflow_data_with_credentials["nodes"]
            elif "workflow_data" in workflow_data_with_credentials:
                update_data["workflow_data"] = workflow_data_with_credentials["workflow_data"]

            # Update the workflow if we have node data to update
            if update_data:
                await workflow_engine_client.update_workflow(
                    workflow_id=workflow_id, user_id=deps.current_user.sub, **update_data
                )
                logger.info(f"✅ Workflow {workflow_id} updated with OAuth credentials")

                # Clear cache since workflow was updated
                _clear_workflow_cache(workflow_id, deps.current_user.sub)

        # Get workflow scheduler client
        scheduler_client = await get_workflow_scheduler_client()

        # Deploy workflow via scheduler with updated credentials
        result = await scheduler_client.deploy_workflow(
            workflow_id=workflow_id,
            workflow_spec=workflow_data_with_credentials,
            user_id=deps.current_user.sub,
            trace_id=getattr(deps.request.state, "trace_id", None),
        )

        # Handle errors
        if not result.get("success", True) and result.get("error"):
            error_msg = result.get("error", "Unknown error")
            if "not found" in error_msg.lower():
                raise HTTPException(status_code=404, detail="Workflow not found")
            raise HTTPException(status_code=500, detail=f"Deployment failed: {error_msg}")

        logger.info(
            f"✅ Workflow deployment successful: {workflow_id}, "
            f"deployment_id: {result.get('deployment_id', 'N/A')}"
        )

        # Return DeploymentResult
        return DeploymentResult(
            deployment_id=result.get("deployment_id", ""),
            status=DeploymentStatus(result.get("status", "deployed")),
            message=result.get("message", "Workflow deployed successfully"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deploying workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{workflow_id}/undeploy", response_model=ResponseModel)
async def undeploy_workflow(
    workflow_id: str,
    deps: AuthenticatedDeps = Depends(),
):
    """
    Undeploy a workflow and cleanup its triggers
    卸载工作流并清理其触发器
    """
    try:
        logger.info(f"🗑️ Undeploying workflow {workflow_id} for user {deps.current_user.sub}")

        # Get workflow scheduler client
        scheduler_client = await get_workflow_scheduler_client()

        # Undeploy workflow
        result = await scheduler_client.undeploy_workflow(
            workflow_id=workflow_id,
            trace_id=getattr(deps.request.state, "trace_id", None),
        )

        # Handle errors
        if not result.get("success", True) and result.get("error"):
            error_msg = result.get("error", "Unknown error")
            if "not found" in error_msg.lower():
                raise HTTPException(status_code=404, detail="Workflow deployment not found")
            raise HTTPException(status_code=500, detail=f"Undeploy failed: {error_msg}")

        logger.info(f"✅ Workflow undeployed successfully: {workflow_id}")

        return ResponseModel(success=True, message="Workflow undeployed successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error undeploying workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{workflow_id}/deployment/status")
async def get_deployment_status(
    workflow_id: str,
    deps: AuthenticatedDeps = Depends(),
):
    """
    Get deployment status for a workflow
    获取工作流的部署状态
    """
    try:
        logger.info(
            f"📊 Getting deployment status for workflow {workflow_id} for user {deps.current_user.sub}"
        )

        # Get workflow scheduler client
        scheduler_client = await get_workflow_scheduler_client()

        # Get deployment status
        result = await scheduler_client.get_deployment_status(workflow_id)

        # Handle not found
        if result.get("status_code") == 404:
            raise HTTPException(status_code=404, detail="Deployment not found")

        # Handle errors
        if not result.get("success", True) and result.get("error"):
            error_msg = result.get("error", "Unknown error")
            raise HTTPException(
                status_code=500, detail=f"Failed to get deployment status: {error_msg}"
            )

        logger.info(f"✅ Retrieved deployment status for workflow: {workflow_id}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting deployment status for workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{workflow_id}/triggers/{trigger_node_id}/manual-invocation-schema")
async def get_manual_invocation_schema(
    workflow_id: str,
    trigger_node_id: str,
    deps: AuthenticatedDeps = Depends(),
) -> Dict[str, Any]:
    """
    Get manual invocation parameter schema for a specific trigger node.

    Returns the JSON schema and examples for manually invoking this trigger,
    enabling frontend forms to be dynamically generated.
    """
    try:
        logger.info(
            f"🔍 Getting manual invocation schema for trigger {trigger_node_id} in workflow {workflow_id}"
        )

        # Get workflow data to find the trigger node
        workflow_engine_client = await get_workflow_engine_client()
        workflow = await workflow_engine_client.get_workflow(
            workflow_id=workflow_id, access_token=deps.access_token
        )

        # Check if the response indicates an error (success: False) or if it's empty
        if not workflow or workflow.get("success") == False:
            error_msg = (
                workflow.get("error", "Workflow not found") if workflow else "Workflow not found"
            )
            raise HTTPException(status_code=404, detail=error_msg)

        # For successful responses, the workflow data is in the "workflow" field or might be the root
        workflow_data = workflow.get("workflow", workflow)
        nodes = workflow_data.get("nodes", [])

        # Find the specific trigger node
        trigger_node = None
        for node in nodes:
            if node.get("id") == trigger_node_id and node.get("type") == "TRIGGER":
                trigger_node = node
                break

        if not trigger_node:
            raise HTTPException(
                status_code=404, detail=f"Trigger node {trigger_node_id} not found in workflow"
            )

        # Get node spec for this trigger type
        from shared.node_specs.registry import NodeSpecRegistry

        registry = NodeSpecRegistry()
        trigger_subtype = trigger_node.get("subtype", "")

        try:
            node_spec = registry.get_spec("TRIGGER", trigger_subtype)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail=f"No specification found for trigger type: {trigger_subtype}",
            )

        if (
            not node_spec
            or not node_spec.manual_invocation
            or not node_spec.manual_invocation.supported
        ):
            raise HTTPException(
                status_code=400,
                detail=f"Manual invocation not supported for trigger type: {trigger_subtype}",
            )

        # Return comprehensive schema information
        manual_spec = node_spec.manual_invocation

        result = {
            "workflow_id": workflow_id,
            "trigger_node_id": trigger_node_id,
            "trigger_type": trigger_subtype,
            "manual_invocation": {
                "supported": manual_spec.supported,
                "description": manual_spec.description,
                "parameter_schema": manual_spec.parameter_schema,
                "parameter_examples": manual_spec.parameter_examples or [],
                "default_parameters": manual_spec.default_parameters or {},
            },
            "trigger_configuration": {
                "name": trigger_node.get("name", ""),
                "parameters": trigger_node.get("parameters", {}),
            },
        }

        logger.info(f"✅ Retrieved manual invocation schema for trigger {trigger_node_id}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting manual invocation schema: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{workflow_id}/triggers/{trigger_node_id}/manual-invoke")
async def manual_invoke_trigger(
    workflow_id: str,
    trigger_node_id: str,
    request_body: Dict[str, Any] = Body(...),
    deps: AuthenticatedDeps = Depends(),
) -> Dict[str, Any]:
    """
    Manually invoke a specific trigger with custom parameters.

    Creates a normal workflow execution with manual invocation metadata.
    """
    try:
        parameters = request_body.get("parameters", {})
        description = request_body.get("description", "Manual trigger invocation")

        logger.info(f"🚀 Manual trigger invocation: {trigger_node_id} in workflow {workflow_id}")

        # Get workflow to find trigger node type
        workflow_engine_client = await get_workflow_engine_client()
        workflow_result = await workflow_engine_client.get_workflow(
            workflow_id=workflow_id, access_token=deps.access_token
        )

        # Check if workflow retrieval was successful
        if not workflow_result.get("found", False) or not workflow_result.get("workflow"):
            if workflow_result.get("success") == False:
                error_msg = workflow_result.get("error", "Unknown error")
                logger.error(f"❌ Failed to get workflow {workflow_id}: {error_msg}")
                raise HTTPException(
                    status_code=500, detail=f"Failed to retrieve workflow: {error_msg}"
                )
            else:
                raise HTTPException(status_code=404, detail="Workflow not found")

        workflow = workflow_result["workflow"]

        # Find the trigger node
        trigger_node = None
        for node in workflow["nodes"]:
            if node["id"] == trigger_node_id:
                trigger_node = node
                break

        if not trigger_node:
            raise HTTPException(status_code=404, detail="Trigger node not found in workflow")

        # Get node schema from the public API using the node registry
        from shared.node_specs.registry import NodeSpecRegistry

        registry = NodeSpecRegistry()
        node_type = trigger_node["type"]
        node_subtype = trigger_node["subtype"]

        try:
            node_spec = registry.get_spec(node_type, node_subtype)
            if (
                not node_spec
                or not node_spec.manual_invocation
                or not node_spec.manual_invocation.supported
            ):
                raise HTTPException(
                    status_code=400,
                    detail=f"Manual invocation not supported for {node_type}.{node_subtype}",
                )

            manual_spec = node_spec.manual_invocation
            logger.info(f"✅ Manual invocation supported for {node_type}.{node_subtype}")

        except Exception as e:
            logger.error(f"❌ Error getting node spec: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to get node specification for {node_type}.{node_subtype}",
            )

        # Validate parameters against JSON schema
        if manual_spec.parameter_schema:
            try:
                import jsonschema

                jsonschema.validate(parameters, manual_spec.parameter_schema)
                logger.info("✅ Parameters validated against schema")
            except ImportError:
                logger.warning("⚠️  jsonschema not available, skipping validation")
            except jsonschema.ValidationError as e:
                raise HTTPException(
                    status_code=400, detail=f"Parameter validation failed: {e.message}"
                )

        # Merge with default parameters
        resolved_parameters = {**(manual_spec.default_parameters or {}), **parameters}

        # Get workflow engine client for direct execution (simplified architecture)
        workflow_engine_client = await get_workflow_engine_client()

        # Convert resolved parameters to string format as required by ExecuteWorkflowRequest
        trigger_data = {}
        for key, value in resolved_parameters.items():
            trigger_data[key] = str(value) if value is not None else ""

        # Add execution metadata (all as strings)
        trigger_data.update(
            {
                "trigger_type": "manual_trigger",
                "trigger_node_id": trigger_node_id,
                "original_trigger_type": node_subtype,
                "invocation_type": "manual_invoke",
                "triggered_at": datetime.now().isoformat(),
                "trace_id": getattr(deps.request.state, "trace_id", None) or str(uuid.uuid4()),
            }
        )

        # Call workflow engine directly with the correct parameters (async execution for immediate response)
        execution_result = await workflow_engine_client.execute_workflow(
            workflow_id=workflow_id,
            user_id=deps.current_user.sub,
            input_data=trigger_data,  # Pass trigger data as input_data
            trace_id=getattr(deps.request.state, "trace_id", None),
            access_token=deps.access_token,  # Pass JWT token for authentication
            async_execution=True,  # Return immediately without waiting for completion
        )

        if not execution_result.get("success", False):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to start execution: {execution_result.get('error', 'Unknown error')}",
            )

        result = {
            "success": True,
            "workflow_id": workflow_id,
            "trigger_node_id": trigger_node_id,
            "execution_id": execution_result.get("execution_id"),
            "message": "Manual trigger invocation started successfully",
            "trigger_data": {
                "trigger_type": node_subtype,
                "resolved_parameters": resolved_parameters,
            },
            "execution_url": f"/api/v1/executions/{execution_result.get('execution_id')}",
        }

        logger.info(f"✅ Manual trigger invocation started: {execution_result.get('execution_id')}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in manual trigger invocation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
