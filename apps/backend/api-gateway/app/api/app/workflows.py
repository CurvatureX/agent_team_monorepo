"""
Workflow API endpoints with authentication and enhanced gRPC client integration
支持认证的工作流API端点
"""

import logging
import time
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

logger = logging.getLogger(__name__)
router = APIRouter()

# Workflow validation and data cache
WORKFLOW_CACHE = {}
CACHE_TTL = 300  # 5 minutes TTL for workflow data


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


async def _inject_oauth_credentials(workflow_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Inject OAuth credentials from oauth_tokens table into workflow nodes.

    Updates trigger nodes and external action nodes with their corresponding OAuth tokens.
    """
    try:
        logger.info(f"🔐 Injecting OAuth credentials for workflow deployment - user {user_id}")

        # Get Supabase admin client for database access (need admin to access oauth_tokens)
        supabase = get_supabase_admin()

        # Fetch user's OAuth tokens
        oauth_tokens_result = (
            supabase.table("oauth_tokens")
            .select("provider, integration_id, access_token, refresh_token, credential_data")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .execute()
        )

        if not oauth_tokens_result.data:
            logger.info("🔐 No OAuth tokens found for user, skipping credential injection")
            return workflow_data

        # Create provider -> token mapping with integration_id handling
        provider_tokens = {}
        for token_record in oauth_tokens_result.data:
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


@router.post("/", response_model=WorkflowResponse)
async def create_workflow(request: WorkflowCreate, deps: AuthenticatedDeps = Depends()):
    """
    Create a new workflow
    创建新的工作流
    """
    try:
        logger.info(f"📝 Creating workflow for user {deps.current_user.sub}")

        # Get HTTP client
        settings = get_settings()

        http_client = await get_workflow_engine_client()

        # Pass nodes directly - they should already be in NodeData format from WorkflowCreateRequest
        nodes_list = []
        if request.nodes:
            nodes_list = [node.model_dump() for node in request.nodes]

        # Use connections as-is (no conversion needed - using unified models)
        connections_dict = request.connections or {}

        # Create workflow via HTTP
        result = await http_client.create_workflow(
            name=request.name,
            description=request.description,
            nodes=nodes_list,
            connections=connections_dict,
            settings=request.settings or {},
            static_data=getattr(request, "static_data", None) or {},
            tags=request.tags or [],
            user_id=deps.current_user.sub,
            trace_id=getattr(deps.request.state, "trace_id", None),
        )

        if not result.get("success", False) or not result.get("workflow", {}).get("id"):
            raise HTTPException(status_code=500, detail="Failed to create workflow")

        workflow_data = result["workflow"]

        logger.info(f"✅ Workflow created: {workflow_data['id']}")

        # Create workflow object
        workflow = Workflow(**workflow_data)

        return WorkflowResponse(workflow=workflow, message="Workflow created successfully")

    except (ValidationError, HTTPException):
        raise
    except Exception as e:
        logger.error(f"❌ Error creating workflow: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: str, deps: AuthenticatedDeps = Depends()):
    """
    Get a workflow with user access control
    通过ID获取工作流（支持用户访问控制）
    """
    try:
        logger.info(f"🔍 Getting workflow {workflow_id} for user {deps.current_user.sub}")

        # Get HTTP client
        settings = get_settings()

        http_client = await get_workflow_engine_client()

        # Get workflow via HTTP
        result = await http_client.get_workflow(workflow_id, deps.current_user.sub)
        if not result.get("found", False) or not result.get("workflow"):
            raise NotFoundError("Workflow")

        # Create workflow object using WorkflowData
        from shared.models.workflow import WorkflowData

        workflow = WorkflowData(**result["workflow"])

        logger.info(f"✅ Workflow retrieved: {workflow_id}")

        return WorkflowResponse(workflow=workflow, message="Workflow retrieved successfully")

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


@router.get("/", response_model=dict)
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

        # List workflows via HTTP
        result = await http_client.list_workflows(
            user_id=deps.current_user.sub,
            active_only=active_only,
            tags=tag_list,
            limit=limit,
            offset=offset,
        )

        logger.info(f"✅ Listed {len(result.get('workflows', []))} workflows")

        return result

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
