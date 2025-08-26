"""
Credentials API endpoints for OAuth2 credential management
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
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


class CredentialGetRequest(BaseModel):
    """Request model for getting stored credential details"""

    user_id: str
    provider: str


class CredentialGetResponse(BaseModel):
    """Response model for getting credential details"""

    has_credentials: bool
    provider: str
    user_id: str
    credentials: Dict[str, Any] = None


class CredentialStatusRequest(BaseModel):
    """Request model for getting authorization status for all providers"""

    user_id: str


class CredentialStatusResponse(BaseModel):
    """Response model for authorization status"""

    user_id: str
    providers: Dict[str, Dict[str, Any]]


@router.post("/credentials/check", response_model=CredentialCheckResponse)
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

            logger.info(
                f"Credential check result for user {request.user_id}, provider {request.provider}: {has_credentials}"
            )

            return CredentialCheckResponse(
                has_credentials=has_credentials, provider=request.provider, user_id=request.user_id
            )

    except Exception as e:
        logger.error(
            f"Failed to check credentials for user {request.user_id}, provider {request.provider}: {e}"
        )
        raise HTTPException(status_code=500, detail=f"Failed to check credentials: {str(e)}")


@router.post("/credentials/status", response_model=CredentialStatusResponse)
async def get_authorization_status(request: CredentialStatusRequest):
    """
    Get authorization status for all external API providers

    Args:
        request: Status request containing user_id

    Returns:
        CredentialStatusResponse with status for all providers
    """
    try:
        logger.info(f"Getting authorization status for user {request.user_id}")

        # Supported providers list
        supported_providers = ["google_calendar", "github", "slack", "email", "api_call"]

        providers_status = {}

        with get_db_session() as db:
            oauth2_service = OAuth2ServiceLite(db)

            for provider in supported_providers:
                try:
                    # Get detailed credential status
                    from datetime import datetime, timedelta, timezone

                    from sqlalchemy import text

                    query = text(
                        """
                        SELECT client_id, token_expires_at, created_at, updated_at,
                               is_valid, validation_error, encrypted_refresh_token,
                               refresh_token_expires_at
                        FROM user_external_credentials
                        WHERE user_id = :user_id AND provider = :provider
                        ORDER BY updated_at DESC
                        LIMIT 1
                    """
                    )

                    result = db.execute(
                        query, {"user_id": request.user_id, "provider": provider}
                    ).fetchone()

                    if not result:
                        # No credentials stored
                        providers_status[provider] = {
                            "authorized": False,
                            "status": "not_authorized",
                            "message": "No authorization found. Please authorize this provider.",
                            "requires_auth": True,
                            "client_id": None,
                            "expires_at": None,
                            "last_updated": None,
                        }
                        continue

                    (
                        client_id,
                        expires_at,
                        created_at,
                        updated_at,
                        is_valid,
                        validation_error,
                        encrypted_refresh_token,
                        refresh_expires_at,
                    ) = result

                    # Check if credentials are marked as invalid
                    if not is_valid:
                        requires_reauth = True
                        status = "invalid"

                        if validation_error == "refresh_token_expired":
                            message = "Authorization expired. Please re-authorize this provider."
                            status = "refresh_expired"
                        elif validation_error == "refresh_failed":
                            message = (
                                "Authorization refresh failed. Please re-authorize this provider."
                            )
                            status = "refresh_failed"
                        else:
                            message = (
                                f"Authorization invalid: {validation_error or 'Unknown reason'}"
                            )

                        providers_status[provider] = {
                            "authorized": False,
                            "status": status,
                            "message": message,
                            "requires_auth": requires_reauth,
                            "client_id": client_id,
                            "expires_at": expires_at.isoformat() if expires_at else None,
                            "last_updated": updated_at.isoformat() if updated_at else None,
                            "error": validation_error,
                        }
                        continue

                    # Check if access token is expired or about to expire
                    now = datetime.now(timezone.utc)
                    token_status = "valid"
                    message = "Authorization is valid and active."

                    if expires_at:
                        if isinstance(expires_at, str):
                            expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))

                        buffer_time = timedelta(minutes=5)
                        if expires_at <= (now + buffer_time):
                            # Access token expired, check refresh token
                            if not encrypted_refresh_token:
                                token_status = "expired_no_refresh"
                                message = "Access token expired and no refresh token available. Please re-authorize."
                                authorized = False
                                requires_auth = True
                            else:
                                # Check refresh token expiration
                                if refresh_expires_at:
                                    if isinstance(refresh_expires_at, str):
                                        refresh_expires_at = datetime.fromisoformat(
                                            refresh_expires_at.replace("Z", "+00:00")
                                        )

                                    if refresh_expires_at <= now:
                                        token_status = "refresh_expired"
                                        message = "Refresh token expired. Please re-authorize this provider."
                                        authorized = False
                                        requires_auth = True
                                    else:
                                        token_status = "will_refresh"
                                        message = "Access token expired but will be automatically refreshed."
                                        authorized = True
                                        requires_auth = False
                                else:
                                    # No refresh expiration time, assume it's still valid
                                    token_status = "will_refresh"
                                    message = (
                                        "Access token expired but will be automatically refreshed."
                                    )
                                    authorized = True
                                    requires_auth = False
                        else:
                            authorized = True
                            requires_auth = False
                            time_to_expire = expires_at - now
                            if time_to_expire.total_seconds() < 3600:  # Less than 1 hour
                                message = f"Authorization valid, expires in {int(time_to_expire.total_seconds()/60)} minutes."
                            elif time_to_expire.days < 1:
                                message = f"Authorization valid, expires in {int(time_to_expire.total_seconds()/3600)} hours."
                            else:
                                message = (
                                    f"Authorization valid, expires in {time_to_expire.days} days."
                                )
                    else:
                        # No expiration time
                        authorized = True
                        requires_auth = False

                    providers_status[provider] = {
                        "authorized": authorized,
                        "status": token_status,
                        "message": message,
                        "requires_auth": requires_auth,
                        "client_id": client_id,
                        "expires_at": expires_at.isoformat() if expires_at else None,
                        "last_updated": updated_at.isoformat() if updated_at else None,
                    }

                except Exception as e:
                    logger.warning(f"Failed to check status for provider {provider}: {e}")
                    providers_status[provider] = {
                        "authorized": False,
                        "error": f"Failed to check: {str(e)}",
                    }

        logger.info(
            f"Authorization status retrieved for user {request.user_id}: {list(providers_status.keys())}"
        )

        return CredentialStatusResponse(user_id=request.user_id, providers=providers_status)

    except Exception as e:
        logger.error(f"Failed to get authorization status for user {request.user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get authorization status: {str(e)}")


@router.post("/credentials/get", response_model=CredentialGetResponse)
async def get_credentials(request: CredentialGetRequest):
    """
    Get stored credential details for a specific provider (for debugging/testing)

    Args:
        request: Credential get request containing user_id and provider

    Returns:
        CredentialGetResponse with credential details if available
    """
    try:
        logger.info(f"Getting credentials for user {request.user_id}, provider {request.provider}")

        with get_db_session() as db:
            from sqlalchemy import text

            # Query the stored credentials
            query = text(
                """
                SELECT encrypted_additional_data, client_id, encrypted_access_token, encrypted_refresh_token,
                       token_expires_at, created_at, updated_at
                FROM user_external_credentials
                WHERE user_id = :user_id AND provider = :provider
                ORDER BY updated_at DESC
                LIMIT 1
            """
            )

            result = db.execute(
                query, {"user_id": request.user_id, "provider": request.provider}
            ).fetchone()

            if result:
                # Build credential details (excluding sensitive refresh token for security)
                credentials = {
                    "additional_data": "***encrypted***"
                    if result.encrypted_additional_data
                    else None,
                    "client_id": result.client_id,
                    "has_access_token": bool(result.encrypted_access_token),
                    "expires_at": result.token_expires_at.isoformat()
                    if result.token_expires_at
                    else None,
                    "created_at": result.created_at.isoformat() if result.created_at else None,
                    "updated_at": result.updated_at.isoformat() if result.updated_at else None,
                }

                logger.info(
                    f"Found credentials for user {request.user_id}, provider {request.provider}"
                )

                return CredentialGetResponse(
                    has_credentials=True,
                    provider=request.provider,
                    user_id=request.user_id,
                    credentials=credentials,
                )
            else:
                logger.info(
                    f"No credentials found for user {request.user_id}, provider {request.provider}"
                )

                return CredentialGetResponse(
                    has_credentials=False,
                    provider=request.provider,
                    user_id=request.user_id,
                    credentials=None,
                )

    except Exception as e:
        logger.error(
            f"Failed to get credentials for user {request.user_id}, provider {request.provider}: {e}"
        )
        raise HTTPException(status_code=500, detail=f"Failed to get credentials: {str(e)}")


@router.post("/credentials/store", response_model=CredentialStoreResponse)
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
                provider=request.provider,
            )

            logger.info(f"Token exchange successful, storing credentials...")

            # Step 2: Store the credentials
            stored = await oauth2_service.store_user_credentials(
                user_id=request.user_id, provider=request.provider, token_response=token_response
            )

            if stored:
                logger.info(
                    f"Successfully stored credentials for user {request.user_id}, provider {request.provider}"
                )
                return CredentialStoreResponse(
                    success=True,
                    message="Credentials stored successfully",
                    provider=request.provider,
                    user_id=request.user_id,
                )
            else:
                logger.error(
                    f"Failed to store credentials for user {request.user_id}, provider {request.provider}"
                )
                raise HTTPException(
                    status_code=500, detail="Failed to store credentials in database"
                )

    except Exception as e:
        logger.error(
            f"Failed to store credentials for user {request.user_id}, provider {request.provider}: {e}"
        )
        raise HTTPException(status_code=400, detail=f"Failed to store credentials: {str(e)}")


@router.delete("/credentials/{user_id}/{provider}")
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
            delete_query = text(
                """
                DELETE FROM user_external_credentials
                WHERE user_id = :user_id AND provider = :provider
            """
            )
            result = db.execute(delete_query, {"user_id": user_id, "provider": provider})
            db.commit()

            deleted_count = result.rowcount

            if deleted_count > 0:
                logger.info(
                    f"Successfully deleted credentials for user {user_id}, provider {provider}"
                )
                return {"success": True, "message": "Credentials deleted successfully"}
            else:
                logger.warning(
                    f"No credentials found to delete for user {user_id}, provider {provider}"
                )
                return {"success": True, "message": "No credentials found to delete"}

    except Exception as e:
        logger.error(f"Failed to delete credentials for user {user_id}, provider {provider}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete credentials: {str(e)}")
