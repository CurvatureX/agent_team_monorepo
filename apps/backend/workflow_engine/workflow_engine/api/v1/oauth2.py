"""
OAuth2 authorization endpoints for external services
Supports Google Calendar, Slack, Notion, GitHub and other OAuth2 providers
"""

import logging
import os
import secrets
from typing import Optional
from urllib.parse import urlencode, quote

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel

from workflow_engine.models.database import get_db_session
from workflow_engine.services.oauth2_service_lite import OAuth2ServiceLite

logger = logging.getLogger(__name__)

router = APIRouter()


class OAuth2AuthorizeRequest(BaseModel):
    """Request model for OAuth2 authorization"""
    user_id: str
    provider: str
    redirect_uri: Optional[str] = None


class OAuth2CallbackResponse(BaseModel):
    """Response model for OAuth2 callback"""
    success: bool
    message: str
    provider: str
    user_id: Optional[str] = None


# OAuth2 provider configurations
OAUTH2_PROVIDERS = {
    "google_calendar": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "scopes": [
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/calendar.events"
        ],
        "access_type": "offline",
        "prompt": "consent"
    },
    "slack": {
        "auth_url": "https://slack.com/oauth/v2/authorize",
        "scopes": [
            "chat:write",
            "channels:read",
            "channels:write",
            "files:write",
            "groups:read",
            "users:read",
            "team:read"
        ],
        "user_scope": None  # Slack uses bot scopes
    },
    "notion": {
        "auth_url": "https://api.notion.com/v1/oauth/authorize",
        "scopes": [],  # Notion doesn't use traditional scopes
        "owner": "user"
    },
    "github": {
        "auth_url": "https://github.com/login/oauth/authorize",
        "scopes": ["repo", "user", "workflow"]
    }
}


@router.get("/oauth2/{provider}/authorize")
async def oauth2_authorize(
    provider: str,
    user_id: str = Query(..., description="User ID"),
    redirect_uri: Optional[str] = Query(None, description="Custom redirect URI")
):
    """
    Generate OAuth2 authorization URL for a provider
    
    Args:
        provider: OAuth2 provider name (google_calendar, slack, notion, github)
        user_id: User ID
        redirect_uri: Optional custom redirect URI
        
    Returns:
        Redirect to provider's OAuth2 authorization page
    """
    try:
        logger.info(f"OAuth2 authorization request for provider: {provider}, user: {user_id}")
        
        if provider not in OAUTH2_PROVIDERS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported provider: {provider}"
            )
        
        with get_db_session() as db:
            oauth2_service = OAuth2ServiceLite(db)
            
            # Get provider configuration
            provider_config = OAUTH2_PROVIDERS[provider]
            oauth_config = oauth2_service.provider_configs.get(provider, {})
            
            client_id = oauth_config.get("client_id")
            if not client_id:
                raise HTTPException(
                    status_code=500,
                    detail=f"OAuth2 client ID not configured for {provider}"
                )
            
            # Generate state parameter for security
            state = secrets.token_urlsafe(32)
            
            # Store state in Redis or database for validation
            # For now, we'll include user_id in state (in production, store in Redis)
            state_with_user = f"{state}:{user_id}"
            
            # Determine redirect URI
            if not redirect_uri:
                base_url = os.getenv("API_BASE_URL", "http://localhost:8002")
                redirect_uri = f"{base_url}/api/v1/oauth2/{provider}/callback"
            
            # Build authorization URL
            auth_params = {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "state": state_with_user,
                "response_type": "code"
            }
            
            # Add provider-specific parameters
            if provider == "google_calendar":
                auth_params["scope"] = " ".join(provider_config["scopes"])
                auth_params["access_type"] = provider_config["access_type"]
                auth_params["prompt"] = provider_config["prompt"]
                
            elif provider == "slack":
                auth_params["scope"] = ",".join(provider_config["scopes"])
                
            elif provider == "notion":
                auth_params["owner"] = provider_config["owner"]
                auth_params["response_type"] = "code"
                
            elif provider == "github":
                auth_params["scope"] = " ".join(provider_config["scopes"])
            
            # Build the authorization URL
            auth_url = f"{provider_config['auth_url']}?{urlencode(auth_params)}"
            
            logger.info(f"Redirecting to OAuth2 authorization URL for {provider}")
            return RedirectResponse(url=auth_url, status_code=302)
            
    except Exception as e:
        logger.error(f"Failed to generate OAuth2 authorization URL for {provider}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate authorization URL: {str(e)}"
        )


@router.get("/oauth2/{provider}/callback")
async def oauth2_callback(
    provider: str,
    code: Optional[str] = Query(None, description="Authorization code"),
    state: Optional[str] = Query(None, description="State parameter"),
    error: Optional[str] = Query(None, description="Error from provider")
):
    """
    Handle OAuth2 callback from provider
    
    Args:
        provider: OAuth2 provider name
        code: Authorization code from provider
        state: State parameter for security validation
        error: Error message if authorization failed
        
    Returns:
        HTML page with success/error message and JavaScript to close window
    """
    try:
        logger.info(f"OAuth2 callback for provider: {provider}")
        
        # Check for authorization errors
        if error:
            logger.error(f"OAuth2 authorization error for {provider}: {error}")
            return HTMLResponse(content=f"""
                <html>
                <head><title>Authorization Failed</title></head>
                <body>
                    <h2>Authorization Failed</h2>
                    <p>Error: {error}</p>
                    <p>Please close this window and try again.</p>
                    <script>
                        window.opener.postMessage({{
                            type: 'oauth2-callback',
                            provider: '{provider}',
                            success: false,
                            error: '{error}'
                        }}, '*');
                        setTimeout(() => window.close(), 3000);
                    </script>
                </body>
                </html>
            """)
        
        if not code:
            raise HTTPException(
                status_code=400,
                detail="No authorization code received"
            )
        
        if not state:
            raise HTTPException(
                status_code=400,
                detail="No state parameter received"
            )
        
        # Extract user_id from state
        try:
            state_token, user_id = state.rsplit(":", 1)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid state parameter"
            )
        
        logger.info(f"Processing OAuth2 callback for user: {user_id}")
        
        with get_db_session() as db:
            oauth2_service = OAuth2ServiceLite(db)
            
            # Determine redirect URI
            base_url = os.getenv("API_BASE_URL", "http://localhost:8002")
            redirect_uri = f"{base_url}/api/v1/oauth2/{provider}/callback"
            
            # Exchange authorization code for tokens
            oauth_config = oauth2_service.provider_configs.get(provider, {})
            client_id = oauth_config.get("client_id")
            
            token_response = await oauth2_service.exchange_code_for_token(
                code=code,
                client_id=client_id,
                redirect_uri=redirect_uri,
                provider=provider
            )
            
            # Store the credentials
            stored = await oauth2_service.store_user_credentials(
                user_id=user_id,
                provider=provider,
                token_response=token_response
            )
            
            if stored:
                logger.info(f"Successfully stored OAuth2 credentials for user {user_id}, provider {provider}")
                
                # Return success HTML with auto-close
                return HTMLResponse(content=f"""
                    <html>
                    <head><title>Authorization Successful</title></head>
                    <body>
                        <h2>Authorization Successful!</h2>
                        <p>You have successfully authorized {provider}.</p>
                        <p>This window will close automatically...</p>
                        <script>
                            window.opener.postMessage({{
                                type: 'oauth2-callback',
                                provider: '{provider}',
                                success: true,
                                userId: '{user_id}'
                            }}, '*');
                            setTimeout(() => window.close(), 2000);
                        </script>
                    </body>
                    </html>
                """)
            else:
                raise Exception("Failed to store credentials")
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to handle OAuth2 callback for {provider}: {e}")
        
        # Return error HTML
        return HTMLResponse(content=f"""
            <html>
            <head><title>Authorization Failed</title></head>
            <body>
                <h2>Authorization Failed</h2>
                <p>Error: {str(e)}</p>
                <p>Please close this window and try again.</p>
                <script>
                    window.opener.postMessage({{
                        type: 'oauth2-callback',
                        provider: '{provider}',
                        success: false,
                        error: '{str(e)}'
                    }}, '*');
                    setTimeout(() => window.close(), 3000);
                </script>
            </body>
            </html>
        """)


@router.post("/oauth2/{provider}/refresh")
async def refresh_token(
    provider: str,
    user_id: str = Query(..., description="User ID")
):
    """
    Refresh OAuth2 access token for a provider
    
    Args:
        provider: OAuth2 provider name
        user_id: User ID
        
    Returns:
        Success/failure status
    """
    try:
        logger.info(f"Refreshing OAuth2 token for provider: {provider}, user: {user_id}")
        
        with get_db_session() as db:
            oauth2_service = OAuth2ServiceLite(db)
            
            # Get current credentials
            credentials = await oauth2_service.get_user_credentials(user_id, provider)
            if not credentials:
                raise HTTPException(
                    status_code=404,
                    detail=f"No credentials found for {provider}"
                )
            
            # Refresh the token
            refreshed = await oauth2_service.refresh_access_token(user_id, provider)
            
            if refreshed:
                return {
                    "success": True,
                    "message": f"Successfully refreshed token for {provider}"
                }
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to refresh token"
                )
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to refresh OAuth2 token for {provider}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh token: {str(e)}"
        )


@router.delete("/oauth2/{provider}/revoke")
async def revoke_authorization(
    provider: str,
    user_id: str = Query(..., description="User ID")
):
    """
    Revoke OAuth2 authorization for a provider
    
    Args:
        provider: OAuth2 provider name
        user_id: User ID
        
    Returns:
        Success/failure status
    """
    try:
        logger.info(f"Revoking OAuth2 authorization for provider: {provider}, user: {user_id}")
        
        with get_db_session() as db:
            from sqlalchemy import text
            
            # Delete credentials from database
            delete_query = text("""
                DELETE FROM user_external_credentials 
                WHERE user_id = :user_id AND provider = :provider
            """)
            
            result = db.execute(delete_query, {
                "user_id": user_id,
                "provider": provider
            })
            db.commit()
            
            deleted_count = result.rowcount
            
            if deleted_count > 0:
                logger.info(f"Successfully revoked OAuth2 authorization for user {user_id}, provider {provider}")
                return {
                    "success": True,
                    "message": f"Authorization revoked for {provider}"
                }
            else:
                return {
                    "success": True,
                    "message": f"No authorization found for {provider}"
                }
                
    except Exception as e:
        logger.error(f"Failed to revoke OAuth2 authorization for {provider}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to revoke authorization: {str(e)}"
        )