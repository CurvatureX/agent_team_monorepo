"""
Tests for Credential Management gRPC Service
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

import grpc
from grpc.aio import Channel

from workflow_engine.proto import workflow_service_pb2
from workflow_engine.proto import workflow_service_pb2_grpc
from workflow_engine.services.credential_grpc_service import CredentialGRPCService
from workflow_engine.models.credential import OAuth2Credential, CredentialConfig


@pytest.fixture
def grpc_service():
    """Create CredentialGRPCService instance with mocked dependencies"""
    service = CredentialGRPCService()
    
    # Mock the dependencies
    service.credential_service = AsyncMock()
    service.oauth2_handler = AsyncMock()
    
    return service


@pytest.fixture
def mock_context():
    """Create mock gRPC context"""
    context = AsyncMock(spec=grpc.aio.ServicerContext)
    return context


class TestStoreOAuth2Credential:
    """Test StoreOAuth2Credential RPC method"""
    
    @pytest.mark.asyncio
    async def test_store_credential_success(self, grpc_service, mock_context):
        """Test successful credential storage"""
        # Mock credential service
        grpc_service.credential_service.store_credential.return_value = "credential_123"
        
        # Create request
        oauth2_cred = workflow_service_pb2.OAuth2Credential(
            access_token="access_token_123",
            refresh_token="refresh_token_123",
            token_type="Bearer",
            expires_at=1640995200,
            scope="calendar.events",
            additional_data={"provider": "google"}
        )
        
        request = workflow_service_pb2.StoreOAuth2CredentialRequest(
            user_id="user_123",
            provider="google_calendar",
            integration_id="integration_123",
            credential=oauth2_cred,
            metadata={"source": "oauth_flow"}
        )
        
        # Call method
        response = await grpc_service.StoreOAuth2Credential(request, mock_context)
        
        # Verify response
        assert response.success is True
        assert response.credential_id == "credential_123"
        assert response.message == "Credential stored successfully"
        assert response.error_code == ""
        
        # Verify credential service was called correctly
        grpc_service.credential_service.store_credential.assert_called_once()
        call_args = grpc_service.credential_service.store_credential.call_args
        
        assert call_args[1]["user_id"] == "user_123"
        assert call_args[1]["provider"] == "google_calendar"
        assert call_args[1]["integration_id"] == "integration_123"
        assert isinstance(call_args[1]["credential"], OAuth2Credential)
        assert call_args[1]["credential"].access_token == "access_token_123"
    
    @pytest.mark.asyncio
    async def test_store_credential_missing_user_id(self, grpc_service, mock_context):
        """Test storing credential without user_id"""
        oauth2_cred = workflow_service_pb2.OAuth2Credential(
            access_token="access_token_123"
        )
        
        request = workflow_service_pb2.StoreOAuth2CredentialRequest(
            user_id="",  # Missing user_id
            provider="google_calendar",
            credential=oauth2_cred
        )
        
        # Mock context.abort
        mock_context.abort = AsyncMock()
        
        # Call method - should abort
        await grpc_service.StoreOAuth2Credential(request, mock_context)
        
        # Verify abort was called
        mock_context.abort.assert_called_once_with(
            grpc.StatusCode.INVALID_ARGUMENT, 
            "user_id is required"
        )
    
    @pytest.mark.asyncio
    async def test_store_credential_service_error(self, grpc_service, mock_context):
        """Test credential storage service error"""
        # Mock credential service to raise exception
        grpc_service.credential_service.store_credential.side_effect = Exception("Database error")
        
        oauth2_cred = workflow_service_pb2.OAuth2Credential(
            access_token="access_token_123"
        )
        
        request = workflow_service_pb2.StoreOAuth2CredentialRequest(
            user_id="user_123",
            provider="google_calendar",
            credential=oauth2_cred
        )
        
        # Call method
        response = await grpc_service.StoreOAuth2Credential(request, mock_context)
        
        # Verify error response
        assert response.success is False
        assert "Failed to store credential" in response.message
        assert response.error_code == "STORAGE_ERROR"


class TestRefreshOAuth2Token:
    """Test RefreshOAuth2Token RPC method"""
    
    @pytest.mark.asyncio
    async def test_refresh_token_success(self, grpc_service, mock_context):
        """Test successful token refresh"""
        # Mock existing credential
        existing_cred = CredentialConfig(
            credential_type="oauth2",
            credential_id="cred_123",
            credential_data={"refresh_token": "refresh_123"},
            expires_at=1640995200,
            is_valid=True
        )
        grpc_service.credential_service.get_credential.return_value = existing_cred
        
        # Mock OAuth2 handler
        new_oauth2_cred = OAuth2Credential(
            access_token="new_access_token",
            refresh_token="refresh_123",
            token_type="Bearer",
            expires_at=1641081600,
            scope="calendar.events"
        )
        grpc_service.oauth2_handler.refresh_access_token.return_value = new_oauth2_cred
        grpc_service.credential_service.update_credential.return_value = "cred_123"
        
        # Create request
        request = workflow_service_pb2.RefreshOAuth2TokenRequest(
            user_id="user_123",
            provider="google_calendar",
            integration_id="integration_123"
        )
        
        # Call method
        response = await grpc_service.RefreshOAuth2Token(request, mock_context)
        
        # Verify response
        assert response.success is True
        assert response.credential.access_token == "new_access_token"
        assert response.credential.refresh_token == "refresh_123"
        assert response.message == "Token refreshed successfully"
        
        # Verify services were called
        grpc_service.oauth2_handler.refresh_access_token.assert_called_once_with(
            refresh_token="refresh_123",
            provider="google_calendar"
        )
    
    @pytest.mark.asyncio
    async def test_refresh_token_not_found(self, grpc_service, mock_context):
        """Test token refresh when credential not found"""
        # Mock credential service to return None
        grpc_service.credential_service.get_credential.return_value = None
        
        request = workflow_service_pb2.RefreshOAuth2TokenRequest(
            user_id="user_123",
            provider="google_calendar"
        )
        
        # Call method
        response = await grpc_service.RefreshOAuth2Token(request, mock_context)
        
        # Verify error response
        assert response.success is False
        assert response.message == "Credential not found"
        assert response.error_code == "CREDENTIAL_NOT_FOUND"


class TestGetCredential:
    """Test GetCredential RPC method"""
    
    @pytest.mark.asyncio
    async def test_get_credential_success(self, grpc_service, mock_context):
        """Test successful credential retrieval"""
        # Mock credential service
        mock_credential = CredentialConfig(
            credential_type="oauth2",
            credential_id="cred_123",
            credential_data={"encrypted_token": "encrypted_data"},
            expires_at=1640995200,
            is_valid=True
        )
        grpc_service.credential_service.get_credential.return_value = mock_credential
        
        # Create request
        request = workflow_service_pb2.GetCredentialRequest(
            user_id="user_123",
            provider="google_calendar",
            integration_id="integration_123"
        )
        
        # Call method
        response = await grpc_service.GetCredential(request, mock_context)
        
        # Verify response
        assert response.found is True
        assert response.credential.credential_type == "oauth2"
        assert response.credential.credential_id == "cred_123"
        assert response.credential.expires_at == 1640995200
        assert response.credential.is_valid is True
        assert response.message == "Credential retrieved successfully"
        
        # Verify service was called
        grpc_service.credential_service.get_credential.assert_called_once_with(
            user_id="user_123",
            provider="google_calendar",
            integration_id="integration_123"
        )
    
    @pytest.mark.asyncio
    async def test_get_credential_not_found(self, grpc_service, mock_context):
        """Test getting non-existent credential"""
        # Mock credential service to return None
        grpc_service.credential_service.get_credential.return_value = None
        
        request = workflow_service_pb2.GetCredentialRequest(
            user_id="user_123",
            provider="google_calendar"
        )
        
        # Call method
        response = await grpc_service.GetCredential(request, mock_context)
        
        # Verify response
        assert response.found is False
        assert response.message == "Credential not found"


class TestDeleteCredential:
    """Test DeleteCredential RPC method"""
    
    @pytest.mark.asyncio
    async def test_delete_credential_success(self, grpc_service, mock_context):
        """Test successful credential deletion"""
        # Mock credential service
        grpc_service.credential_service.delete_credential.return_value = True
        
        # Create request
        request = workflow_service_pb2.DeleteCredentialRequest(
            user_id="user_123",
            provider="google_calendar",
            integration_id="integration_123"
        )
        
        # Call method
        response = await grpc_service.DeleteCredential(request, mock_context)
        
        # Verify response
        assert response.success is True
        assert response.message == "Credential deleted successfully"
        assert response.error_code == ""
        
        # Verify service was called
        grpc_service.credential_service.delete_credential.assert_called_once_with(
            user_id="user_123",
            provider="google_calendar",
            integration_id="integration_123"
        )
    
    @pytest.mark.asyncio
    async def test_delete_credential_not_found(self, grpc_service, mock_context):
        """Test deleting non-existent credential"""
        # Mock credential service to return False
        grpc_service.credential_service.delete_credential.return_value = False
        
        request = workflow_service_pb2.DeleteCredentialRequest(
            user_id="user_123",
            provider="google_calendar"
        )
        
        # Call method
        response = await grpc_service.DeleteCredential(request, mock_context)
        
        # Verify response
        assert response.success is False
        assert response.message == "Credential not found"
        assert response.error_code == "CREDENTIAL_NOT_FOUND"
    
    @pytest.mark.asyncio
    async def test_delete_credential_service_error(self, grpc_service, mock_context):
        """Test credential deletion service error"""
        # Mock credential service to raise exception
        grpc_service.credential_service.delete_credential.side_effect = Exception("Database error")
        
        request = workflow_service_pb2.DeleteCredentialRequest(
            user_id="user_123",
            provider="google_calendar"
        )
        
        # Call method
        response = await grpc_service.DeleteCredential(request, mock_context)
        
        # Verify error response
        assert response.success is False
        assert "Failed to delete credential" in response.message
        assert response.error_code == "DELETION_ERROR"


class TestInputValidation:
    """Test input validation across all methods"""
    
    @pytest.mark.asyncio
    async def test_missing_provider_validation(self, grpc_service, mock_context):
        """Test validation when provider is missing"""
        mock_context.abort = AsyncMock()
        
        # Test with GetCredential (similar validation applies to all methods)
        request = workflow_service_pb2.GetCredentialRequest(
            user_id="user_123",
            provider="",  # Missing provider
            integration_id="integration_123"
        )
        
        await grpc_service.GetCredential(request, mock_context)
        
        mock_context.abort.assert_called_once_with(
            grpc.StatusCode.INVALID_ARGUMENT,
            "provider is required"
        ) 