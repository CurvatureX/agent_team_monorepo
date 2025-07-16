"""
Credential Management gRPC Service Implementation
"""

import asyncio
import logging
from typing import Optional
import structlog

import grpc
from ..proto import workflow_service_pb2_grpc
from ..proto import workflow_service_pb2
from ..services.credential_service import CredentialService
from ..services.oauth2_handler import OAuth2Handler
from ..core.config import get_settings

logger = structlog.get_logger()


class CredentialGRPCService(workflow_service_pb2_grpc.IntegrationServiceServicer):
    """gRPC service for credential management operations"""
    
    def __init__(self):
        self.settings = get_settings()
        self.credential_service = CredentialService()
        self.oauth2_handler = OAuth2Handler()
    
    async def StoreOAuth2Credential(
        self, 
        request: workflow_service_pb2.StoreOAuth2CredentialRequest, 
        context: grpc.aio.ServicerContext
    ) -> workflow_service_pb2.StoreOAuth2CredentialResponse:
        """
        Store OAuth2 credential for a user
        
        Args:
            request: Store credential request
            context: gRPC context
            
        Returns:
            Store credential response
        """
        try:
            logger.info(
                "Storing OAuth2 credential",
                user_id=request.user_id,
                provider=request.provider,
                integration_id=request.integration_id
            )
            
            # Validate request
            if not request.user_id:
                await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "user_id is required")
            
            if not request.provider:
                await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "provider is required")
            
            if not request.credential or not request.credential.access_token:
                await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "credential with access_token is required")
            
            # Create OAuth2Credential object from protobuf
            from ..models.credential import OAuth2Credential
            oauth2_cred = OAuth2Credential(
                access_token=request.credential.access_token,
                refresh_token=request.credential.refresh_token,
                token_type=request.credential.token_type or "Bearer",
                expires_at=request.credential.expires_at,
                scope=request.credential.scope,
                additional_data=dict(request.credential.additional_data) if request.credential.additional_data else {}
            )
            
            # Store credential using CredentialService
            credential_id = await self.credential_service.store_credential(
                user_id=request.user_id,
                provider=request.provider,
                integration_id=request.integration_id or "",
                credential=oauth2_cred,
                metadata=dict(request.metadata) if request.metadata else {}
            )
            
            logger.info(
                "OAuth2 credential stored successfully",
                user_id=request.user_id,
                provider=request.provider,
                credential_id=credential_id
            )
            
            return workflow_service_pb2.StoreOAuth2CredentialResponse(
                success=True,
                credential_id=credential_id,
                message="Credential stored successfully"
            )
            
        except ValueError as e:
            logger.warning(
                "Invalid credential data",
                user_id=request.user_id,
                provider=request.provider,
                error=str(e)
            )
            return workflow_service_pb2.StoreOAuth2CredentialResponse(
                success=False,
                message=f"Invalid credential data: {str(e)}",
                error_code="INVALID_CREDENTIAL"
            )
        except Exception as e:
            logger.error(
                "Failed to store OAuth2 credential",
                user_id=request.user_id,
                provider=request.provider,
                error=str(e)
            )
            return workflow_service_pb2.StoreOAuth2CredentialResponse(
                success=False,
                message=f"Failed to store credential: {str(e)}",
                error_code="STORAGE_ERROR"
            )
    
    async def RefreshOAuth2Token(
        self,
        request: workflow_service_pb2.RefreshOAuth2TokenRequest,
        context: grpc.aio.ServicerContext
    ) -> workflow_service_pb2.RefreshOAuth2TokenResponse:
        """
        Refresh OAuth2 access token using refresh token
        
        Args:
            request: Refresh token request
            context: gRPC context
            
        Returns:
            Refresh token response
        """
        try:
            logger.info(
                "Refreshing OAuth2 token",
                user_id=request.user_id,
                provider=request.provider,
                integration_id=request.integration_id
            )
            
            # Validate request
            if not request.user_id:
                await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "user_id is required")
            
            if not request.provider:
                await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "provider is required")
            
            # Get existing credential
            existing_credential = await self.credential_service.get_credential(
                user_id=request.user_id,
                provider=request.provider,
                integration_id=request.integration_id or ""
            )
            
            if not existing_credential:
                return workflow_service_pb2.RefreshOAuth2TokenResponse(
                    success=False,
                    message="Credential not found",
                    error_code="CREDENTIAL_NOT_FOUND"
                )
            
            # Use refresh token from request or existing credential
            refresh_token = request.refresh_token or existing_credential.credential_data.get("refresh_token")
            if not refresh_token:
                return workflow_service_pb2.RefreshOAuth2TokenResponse(
                    success=False,
                    message="No refresh token available",
                    error_code="NO_REFRESH_TOKEN"
                )
            
            # Refresh token using OAuth2Handler
            new_credential = await self.oauth2_handler.refresh_access_token(
                refresh_token=refresh_token,
                provider=request.provider
            )
            
            # Update stored credential
            credential_id = await self.credential_service.update_credential(
                user_id=request.user_id,
                provider=request.provider,
                integration_id=request.integration_id or "",
                credential=new_credential
            )
            
            # Convert to protobuf OAuth2Credential
            pb_credential = workflow_service_pb2.OAuth2Credential(
                access_token=new_credential.access_token,
                refresh_token=new_credential.refresh_token,
                token_type=new_credential.token_type,
                expires_at=new_credential.expires_at,
                scope=new_credential.scope,
                additional_data=new_credential.additional_data or {}
            )
            
            logger.info(
                "OAuth2 token refreshed successfully",
                user_id=request.user_id,
                provider=request.provider,
                credential_id=credential_id
            )
            
            return workflow_service_pb2.RefreshOAuth2TokenResponse(
                success=True,
                credential=pb_credential,
                message="Token refreshed successfully"
            )
            
        except Exception as e:
            logger.error(
                "Failed to refresh OAuth2 token",
                user_id=request.user_id,
                provider=request.provider,
                error=str(e)
            )
            return workflow_service_pb2.RefreshOAuth2TokenResponse(
                success=False,
                message=f"Failed to refresh token: {str(e)}",
                error_code="REFRESH_ERROR"
            )
    
    async def GetCredential(
        self,
        request: workflow_service_pb2.GetCredentialRequest,
        context: grpc.aio.ServicerContext
    ) -> workflow_service_pb2.GetCredentialResponse:
        """
        Get credential for a user and provider
        
        Args:
            request: Get credential request
            context: gRPC context
            
        Returns:
            Get credential response
        """
        try:
            logger.info(
                "Getting credential",
                user_id=request.user_id,
                provider=request.provider,
                integration_id=request.integration_id
            )
            
            # Validate request
            if not request.user_id:
                await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "user_id is required")
            
            if not request.provider:
                await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "provider is required")
            
            # Get credential
            credential = await self.credential_service.get_credential(
                user_id=request.user_id,
                provider=request.provider,
                integration_id=request.integration_id or ""
            )
            
            if not credential:
                return workflow_service_pb2.GetCredentialResponse(
                    found=False,
                    message="Credential not found"
                )
            
            # Convert to protobuf CredentialConfig
            pb_credential = workflow_service_pb2.CredentialConfig(
                credential_type=credential.credential_type,
                credential_id=credential.credential_id,
                credential_data=credential.credential_data or {},
                expires_at=credential.expires_at or 0,
                is_valid=credential.is_valid
            )
            
            logger.info(
                "Credential retrieved successfully",
                user_id=request.user_id,
                provider=request.provider,
                credential_id=credential.credential_id
            )
            
            return workflow_service_pb2.GetCredentialResponse(
                found=True,
                credential=pb_credential,
                message="Credential retrieved successfully"
            )
            
        except Exception as e:
            logger.error(
                "Failed to get credential",
                user_id=request.user_id,
                provider=request.provider,
                error=str(e)
            )
            return workflow_service_pb2.GetCredentialResponse(
                found=False,
                message=f"Failed to get credential: {str(e)}",
                error_code="RETRIEVAL_ERROR"
            )
    
    async def DeleteCredential(
        self,
        request: workflow_service_pb2.DeleteCredentialRequest,
        context: grpc.aio.ServicerContext
    ) -> workflow_service_pb2.DeleteCredentialResponse:
        """
        Delete credential for a user and provider
        
        Args:
            request: Delete credential request
            context: gRPC context
            
        Returns:
            Delete credential response
        """
        try:
            logger.info(
                "Deleting credential",
                user_id=request.user_id,
                provider=request.provider,
                integration_id=request.integration_id
            )
            
            # Validate request
            if not request.user_id:
                await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "user_id is required")
            
            if not request.provider:
                await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "provider is required")
            
            # Delete credential
            success = await self.credential_service.delete_credential(
                user_id=request.user_id,
                provider=request.provider,
                integration_id=request.integration_id or ""
            )
            
            if success:
                logger.info(
                    "Credential deleted successfully",
                    user_id=request.user_id,
                    provider=request.provider
                )
                return workflow_service_pb2.DeleteCredentialResponse(
                    success=True,
                    message="Credential deleted successfully"
                )
            else:
                return workflow_service_pb2.DeleteCredentialResponse(
                    success=False,
                    message="Credential not found",
                    error_code="CREDENTIAL_NOT_FOUND"
                )
            
        except Exception as e:
            logger.error(
                "Failed to delete credential",
                user_id=request.user_id,
                provider=request.provider,
                error=str(e)
            )
            return workflow_service_pb2.DeleteCredentialResponse(
                success=False,
                message=f"Failed to delete credential: {str(e)}",
                error_code="DELETION_ERROR"
            ) 