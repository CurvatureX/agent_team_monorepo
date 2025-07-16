"""
OAuth2 API routes
"""

from typing import Optional
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from ..schemas.oauth import (
    AuthURLRequest, 
    AuthURLResponse, 
    CallbackResponse, 
    OAuthErrorResponse
)
from ..core.grpc_client import WorkflowAgentClient

logger = structlog.get_logger()

router = APIRouter()

# Supported OAuth2 providers
SUPPORTED_PROVIDERS = ["google_calendar", "github", "slack"]

# Default scopes for each provider
DEFAULT_SCOPES = {
    "google_calendar": ["https://www.googleapis.com/auth/calendar.events"],
    "github": ["repo", "user"],
    "slack": ["chat:write", "channels:read"]
}


def get_workflow_client(request: Request) -> WorkflowAgentClient:
    """Dependency to get the workflow client from app state"""
    return request.app.state.workflow_client


@router.get("/authorize/{provider}", response_model=AuthURLResponse)
async def generate_auth_url(
    provider: str,
    user_id: str = Query(..., description="User identifier"),
    scopes: Optional[str] = Query(default=None, description="Comma-separated list of scopes"),
    redirect_uri: Optional[str] = Query(default=None, description="Custom redirect URI"),
    workflow_client: WorkflowAgentClient = Depends(get_workflow_client)
) -> AuthURLResponse:
    """
    Generate OAuth2 authorization URL for the specified provider
    
    Args:
        provider: OAuth2 provider (google_calendar, github, slack)
        user_id: User identifier
        scopes: Optional comma-separated scopes (uses defaults if not provided)
        redirect_uri: Optional custom redirect URI
        workflow_client: gRPC client for workflow engine
        
    Returns:
        AuthURLResponse containing the authorization URL and state
    """
    try:
        logger.info(
            "Generating OAuth2 authorization URL",
            provider=provider,
            user_id=user_id,
            scopes=scopes
        )
        
        # Validate provider
        if provider not in SUPPORTED_PROVIDERS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported provider: {provider}. Supported providers: {SUPPORTED_PROVIDERS}"
            )
        
        # Parse scopes or use defaults
        scope_list = []
        if scopes:
            scope_list = [scope.strip() for scope in scopes.split(",")]
        else:
            scope_list = DEFAULT_SCOPES.get(provider, [])
        
        # TODO: Call workflow_engine gRPC service to generate auth URL
        # This will be implemented when OAuth2Handler is available
        # For now, return a placeholder response
        
        # Placeholder implementation - will be replaced with actual gRPC call
        auth_url = f"https://oauth.example.com/{provider}/authorize?user_id={user_id}&scopes={','.join(scope_list)}"
        state = f"state_{user_id}_{provider}"
        
        logger.info(
            "OAuth2 authorization URL generated successfully",
            provider=provider,
            user_id=user_id,
            auth_url=auth_url
        )
        
        return AuthURLResponse(
            success=True,
            auth_url=auth_url,
            state=state
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to generate OAuth2 authorization URL",
            provider=provider,
            user_id=user_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate authorization URL: {str(e)}"
        )


@router.get("/callback/{provider}", response_model=CallbackResponse)
async def oauth_callback(
    provider: str,
    code: str = Query(..., description="Authorization code from OAuth2 provider"),
    state: str = Query(..., description="State parameter for CSRF protection"),
    error: Optional[str] = Query(default=None, description="Error from OAuth2 provider"),
    error_description: Optional[str] = Query(default=None, description="Error description from OAuth2 provider"),
    workflow_client: WorkflowAgentClient = Depends(get_workflow_client)
) -> CallbackResponse:
    """
    Handle OAuth2 callback from provider
    
    Args:
        provider: OAuth2 provider (google_calendar, github, slack)
        code: Authorization code from provider
        state: State parameter for CSRF protection
        error: Optional error code from provider
        error_description: Optional error description from provider
        workflow_client: gRPC client for workflow engine
        
    Returns:
        CallbackResponse indicating success or failure
    """
    try:
        logger.info(
            "Processing OAuth2 callback",
            provider=provider,
            state=state,
            has_error=error is not None
        )
        
        # Validate provider
        if provider not in SUPPORTED_PROVIDERS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported provider: {provider}"
            )
        
        # Check for OAuth2 errors
        if error:
            logger.warning(
                "OAuth2 callback received error",
                provider=provider,
                error=error,
                error_description=error_description
            )
            return CallbackResponse(
                success=False,
                message=f"OAuth2 authorization failed: {error}",
                error=f"{error}: {error_description}" if error_description else error
            )
        
        # TODO: Call workflow_engine gRPC service to exchange code for tokens
        # This will be implemented when OAuth2Handler and CredentialService are available
        # For now, return a placeholder response
        
        # Placeholder implementation - will be replaced with actual gRPC call
        credential_id = f"cred_{provider}_{state.split('_')[1] if '_' in state else 'unknown'}"
        
        logger.info(
            "OAuth2 callback processed successfully",
            provider=provider,
            credential_id=credential_id
        )
        
        return CallbackResponse(
            success=True,
            message=f"Successfully authorized {provider} integration",
            credential_id=credential_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to process OAuth2 callback",
            provider=provider,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process OAuth2 callback: {str(e)}"
        )


@router.get("/providers")
async def list_providers():
    """
    List supported OAuth2 providers and their default scopes
    
    Returns:
        Dictionary of supported providers and their configurations
    """
    return {
        "providers": {
            provider: {
                "name": provider.replace("_", " ").title(),
                "default_scopes": scopes
            }
            for provider, scopes in DEFAULT_SCOPES.items()
        }
    } 