"""
Credentials API endpoints for OAuth2 credential management
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from workflow_engine.models.database import get_db_session
from workflow_engine.services.oauth2_service_lite import OAuth2ServiceLite

logger = logging.getLogger(__name__)

router = APIRouter()


class CredentialCheckRequest(BaseModel):
    """Request model for checking if user has stored credentials"""
    user_id: str
    provider: str


class CredentialCheckResponse(BaseModel):
    """Response model for credential check"""
    has_credentials: bool
    provider: str
    user_id: str


class CredentialStoreRequest(BaseModel):
    """Request model for storing OAuth2 credentials"""
    user_id: str
    provider: str
    authorization_code: str
    client_id: str
    redirect_uri: str


class CredentialStoreResponse(BaseModel):
    """Response model for credential storage"""
    success: bool
    message: str
    provider: str
    user_id: str


@router.post("/api/v1/credentials/check", response_model=CredentialCheckResponse)
async def check_credentials(request: CredentialCheckRequest):
    """
    Check if user has stored credentials for a specific provider
    
    Args:
        request: Credential check request containing user_id and provider
        
    Returns:
        CredentialCheckResponse indicating if credentials exist
    """
    try:
        logger.info(f"Checking credentials for user {request.user_id}, provider {request.provider}")
        
        with get_db_session() as db:
            oauth2_service = OAuth2ServiceLite(db)
            
            # Check if user has valid stored token
            access_token = await oauth2_service.get_valid_token(request.user_id, request.provider)
            has_credentials = access_token is not None
            
            logger.info(f"Credential check result for user {request.user_id}, provider {request.provider}: {has_credentials}")
            
            return CredentialCheckResponse(
                has_credentials=has_credentials,
                provider=request.provider,
                user_id=request.user_id
            )
            
    except Exception as e:
        logger.error(f"Failed to check credentials for user {request.user_id}, provider {request.provider}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check credentials: {str(e)}"
        )


@router.post("/api/v1/credentials/store", response_model=CredentialStoreResponse)
async def store_credentials(request: CredentialStoreRequest):
    """
    Store OAuth2 credentials after exchanging authorization code for tokens
    
    Args:
        request: Credential store request containing authorization code and OAuth2 parameters
        
    Returns:
        CredentialStoreResponse indicating success or failure
    """
    try:
        logger.info(f"Storing credentials for user {request.user_id}, provider {request.provider}")
        
        with get_db_session() as db:
            oauth2_service = OAuth2ServiceLite(db)
            
            # Step 1: Exchange authorization code for tokens
            logger.info(f"Exchanging authorization code for tokens...")
            token_response = await oauth2_service.exchange_code_for_token(
                code=request.authorization_code,
                client_id=request.client_id,
                redirect_uri=request.redirect_uri,
                provider=request.provider
            )
            
            logger.info(f"Token exchange successful, storing credentials...")
            
            # Step 2: Store the credentials
            stored = await oauth2_service.store_user_credentials(
                user_id=request.user_id,
                provider=request.provider,
                token_response=token_response
            )
            
            if stored:
                logger.info(f"Successfully stored credentials for user {request.user_id}, provider {request.provider}")
                return CredentialStoreResponse(
                    success=True,
                    message="Credentials stored successfully",
                    provider=request.provider,
                    user_id=request.user_id
                )
            else:
                logger.error(f"Failed to store credentials for user {request.user_id}, provider {request.provider}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to store credentials in database"
                )
                
    except Exception as e:
        logger.error(f"Failed to store credentials for user {request.user_id}, provider {request.provider}: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to store credentials: {str(e)}"
        )


@router.delete("/api/v1/credentials/{user_id}/{provider}")
async def delete_credentials(user_id: str, provider: str):
    """
    Delete stored credentials for a specific user and provider
    
    Args:
        user_id: User ID
        provider: Provider name (e.g., 'google_calendar')
        
    Returns:
        Success message
    """
    try:
        logger.info(f"Deleting credentials for user {user_id}, provider {provider}")
        
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
                logger.info(f"Successfully deleted credentials for user {user_id}, provider {provider}")
                return {"success": True, "message": "Credentials deleted successfully"}
            else:
                logger.warning(f"No credentials found to delete for user {user_id}, provider {provider}")
                return {"success": True, "message": "No credentials found to delete"}
                
    except Exception as e:
        logger.error(f"Failed to delete credentials for user {user_id}, provider {provider}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete credentials: {str(e)}"
        )