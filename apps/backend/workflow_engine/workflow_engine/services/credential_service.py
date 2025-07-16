"""
Credential management service for OAuth2 tokens and API credentials.

This service provides secure storage, retrieval, and management of API credentials
with encryption, user isolation, and database locking for concurrency safety.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy import and_, select, update, delete
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from workflow_engine.core.config import get_settings
from workflow_engine.core.encryption import get_encryption, EncryptionError, DecryptionError
from workflow_engine.models.database import get_db, SessionLocal
from workflow_engine.models.credential import OAuthToken, CredentialConfig, OAuth2Credential


logger = logging.getLogger(__name__)


class CredentialServiceError(Exception):
    """Base exception for credential service errors."""
    pass


class CredentialNotFoundError(CredentialServiceError):
    """Raised when credential is not found."""
    pass


class CredentialPermissionError(CredentialServiceError):
    """Raised when user lacks permission to access credential."""
    pass


class CredentialStorageError(CredentialServiceError):
    """Raised when credential storage fails."""
    pass


class CredentialService:
    """
    Service for managing API credentials and OAuth2 tokens.
    
    Provides secure CRUD operations with encryption, user isolation,
    and database locking for concurrent access safety.
    """
    
    def __init__(self, session: Optional[Session] = None):
        """
        Initialize credential service.
        
        Args:
            session: Optional SQLAlchemy session. If not provided, creates new session.
        """
        self.session = session
        self._should_close_session = session is None
        self.encryption = get_encryption()
        self.settings = get_settings()
    
    def __enter__(self):
        """Context manager entry."""
        if self.session is None:
            self.session = SessionLocal()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._should_close_session and self.session:
            self.session.close()
    
    async def get_credential(
        self,
        user_id: str,
        provider: str,
        integration_id: Optional[str] = None
    ) -> Optional[OAuth2Credential]:
        """
        Get credential for user and provider.
        
        Args:
            user_id: User ID
            provider: OAuth2 provider name
            integration_id: Optional integration ID for filtering
            
        Returns:
            OAuth2Credential if found, None otherwise
            
        Raises:
            CredentialServiceError: If retrieval fails
        """
        try:
            # Build query with user isolation
            query = select(OAuthToken).where(
                and_(
                    OAuthToken.user_id == UUID(user_id),
                    OAuthToken.provider == provider,
                    OAuthToken.is_active == True
                )
            )
            
            if integration_id:
                query = query.where(OAuthToken.integration_id == integration_id)
            
            # Execute query
            result = self.session.execute(query)
            oauth_token = result.scalar_one_or_none()
            
            if not oauth_token:
                return None
            
            # Decrypt sensitive data
            try:
                access_token = self.encryption.decrypt(oauth_token.access_token)
                refresh_token = None
                if oauth_token.refresh_token:
                    refresh_token = self.encryption.decrypt(oauth_token.refresh_token)
                
                # Decrypt sensitive fields in credential_data
                credential_data = oauth_token.credential_data or {}
                decrypted_data = self._decrypt_credential_data(credential_data)
                
                return OAuth2Credential(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    token_type=oauth_token.token_type,
                    expires_at=oauth_token.expires_at,
                    **decrypted_data
                )
                
            except (DecryptionError, EncryptionError) as e:
                logger.error(f"Failed to decrypt credential for user {user_id}, provider {provider}: {e}")
                raise CredentialServiceError(f"Failed to decrypt credential: {e}") from e
                
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving credential: {e}")
            raise CredentialServiceError(f"Database error: {e}") from e
    
    async def store_credential(
        self,
        user_id: str,
        provider: str,
        credential: CredentialConfig,
        integration_id: Optional[str] = None
    ) -> str:
        """
        Store credential with encryption.
        
        Args:
            user_id: User ID
            provider: OAuth2 provider name
            credential: Credential configuration to store
            integration_id: Optional integration ID
            
        Returns:
            Credential ID
            
        Raises:
            CredentialStorageError: If storage fails
        """
        try:
            # Encrypt sensitive data
            encrypted_access_token = self.encryption.encrypt(credential.access_token)
            encrypted_refresh_token = None
            if credential.refresh_token:
                encrypted_refresh_token = self.encryption.encrypt(credential.refresh_token)
            
            # Encrypt sensitive fields in credential_data
            encrypted_credential_data = self._encrypt_credential_data(credential.credential_data)
            
            # Check if credential already exists (for update)
            existing = await self._get_existing_credential(user_id, provider, integration_id)
            
            if existing:
                # Update existing credential
                update_data = {
                    OAuthToken.access_token: encrypted_access_token,
                    OAuthToken.refresh_token: encrypted_refresh_token,
                    OAuthToken.token_type: credential.token_type,
                    OAuthToken.expires_at: credential.expires_at,
                    OAuthToken.credential_data: encrypted_credential_data,
                    OAuthToken.is_active: True,
                    OAuthToken.updated_at: datetime.utcnow()
                }
                
                stmt = update(OAuthToken).where(
                    OAuthToken.id == existing.id
                ).values(**update_data)
                
                self.session.execute(stmt)
                credential_id = str(existing.id)
                
            else:
                # Create new credential
                new_credential = OAuthToken(
                    id=uuid4(),
                    user_id=UUID(user_id),
                    integration_id=integration_id,
                    provider=provider,
                    access_token=encrypted_access_token,
                    refresh_token=encrypted_refresh_token,
                    token_type=credential.token_type,
                    expires_at=credential.expires_at,
                    credential_data=encrypted_credential_data,
                    is_active=True
                )
                
                self.session.add(new_credential)
                self.session.flush()  # Get the ID
                credential_id = str(new_credential.id)
            
            # Commit transaction
            self.session.commit()
            
            logger.info(f"Stored credential for user {user_id}, provider {provider}")
            return credential_id
            
        except IntegrityError as e:
            self.session.rollback()
            logger.error(f"Integrity error storing credential: {e}")
            raise CredentialStorageError(f"Credential storage failed: {e}") from e
            
        except (EncryptionError, SQLAlchemyError) as e:
            self.session.rollback()
            logger.error(f"Error storing credential: {e}")
            raise CredentialStorageError(f"Credential storage failed: {e}") from e
    
    async def refresh_oauth_token(
        self,
        user_id: str,
        provider: str,
        integration_id: Optional[str] = None
    ) -> bool:
        """
        Refresh OAuth2 token with row-level locking.
        
        Args:
            user_id: User ID
            provider: OAuth2 provider name
            integration_id: Optional integration ID
            
        Returns:
            True if refresh successful, False otherwise
            
        Raises:
            CredentialServiceError: If refresh fails
        """
        try:
            # Use SELECT FOR UPDATE for row-level locking
            query = select(OAuthToken).where(
                and_(
                    OAuthToken.user_id == UUID(user_id),
                    OAuthToken.provider == provider,
                    OAuthToken.is_active == True
                )
            ).with_for_update()
            
            if integration_id:
                query = query.where(OAuthToken.integration_id == integration_id)
            
            result = self.session.execute(query)
            oauth_token = result.scalar_one_or_none()
            
            if not oauth_token:
                raise CredentialNotFoundError(f"Credential not found for user {user_id}, provider {provider}")
            
            # Check if refresh token exists
            if not oauth_token.refresh_token:
                raise CredentialServiceError("No refresh token available")
            
            # Decrypt refresh token
            try:
                refresh_token = self.encryption.decrypt(oauth_token.refresh_token)
            except DecryptionError as e:
                raise CredentialServiceError(f"Failed to decrypt refresh token: {e}") from e
            
            # Get OAuth2 configuration for provider
            oauth_config = self.settings.get_oauth2_config(provider)
            
            # Make token refresh request
            new_tokens = await self._refresh_token_request(
                oauth_config["token_url"],
                oauth_config["client_id"],
                oauth_config["client_secret"],
                refresh_token
            )
            
            # Update stored tokens
            encrypted_access_token = self.encryption.encrypt(new_tokens["access_token"])
            new_refresh_token = new_tokens.get("refresh_token")
            encrypted_refresh_token = None
            if new_refresh_token:
                encrypted_refresh_token = self.encryption.encrypt(new_refresh_token)
            
            # Calculate new expiry
            expires_at = None
            expires_in = new_tokens.get("expires_in")
            if expires_in:
                expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))
            
            # Update credential
            update_data = {
                OAuthToken.access_token: encrypted_access_token,
                OAuthToken.token_type: new_tokens.get("token_type", "Bearer"),
                OAuthToken.expires_at: expires_at,
                OAuthToken.updated_at: datetime.utcnow()
            }
            
            if encrypted_refresh_token:
                update_data[OAuthToken.refresh_token] = encrypted_refresh_token
            
            stmt = update(OAuthToken).where(
                OAuthToken.id == oauth_token.id
            ).values(**update_data)
            
            self.session.execute(stmt)
            self.session.commit()
            
            logger.info(f"Refreshed token for user {user_id}, provider {provider}")
            return True
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Database error refreshing token: {e}")
            raise CredentialServiceError(f"Token refresh failed: {e}") from e
    
    async def delete_credential(
        self,
        user_id: str,
        provider: str,
        integration_id: Optional[str] = None
    ) -> bool:
        """
        Delete credential for user and provider.
        
        Args:
            user_id: User ID
            provider: OAuth2 provider name
            integration_id: Optional integration ID
            
        Returns:
            True if credential was deleted, False if not found
            
        Raises:
            CredentialServiceError: If deletion fails
        """
        try:
            # Build delete query with user isolation
            query = delete(OAuthToken).where(
                and_(
                    OAuthToken.user_id == UUID(user_id),
                    OAuthToken.provider == provider
                )
            )
            
            if integration_id:
                query = query.where(OAuthToken.integration_id == integration_id)
            
            result = self.session.execute(query)
            rows_deleted = result.rowcount
            
            self.session.commit()
            
            if rows_deleted > 0:
                logger.info(f"Deleted credential for user {user_id}, provider {provider}")
                return True
            else:
                return False
                
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Database error deleting credential: {e}")
            raise CredentialServiceError(f"Credential deletion failed: {e}") from e
    
    async def list_credentials(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List all credentials for a user (without sensitive data).
        
        Args:
            user_id: User ID
            
        Returns:
            List of credential metadata
        """
        try:
            query = select(OAuthToken).where(
                and_(
                    OAuthToken.user_id == UUID(user_id),
                    OAuthToken.is_active == True
                )
            ).order_by(OAuthToken.created_at.desc())
            
            result = self.session.execute(query)
            credentials = result.scalars().all()
            
            return [cred.to_dict(include_sensitive=False) for cred in credentials]
            
        except SQLAlchemyError as e:
            logger.error(f"Database error listing credentials: {e}")
            raise CredentialServiceError(f"Failed to list credentials: {e}") from e
    
    # Private helper methods
    
    async def _get_existing_credential(
        self,
        user_id: str,
        provider: str,
        integration_id: Optional[str] = None
    ) -> Optional[OAuthToken]:
        """Get existing credential for update operations."""
        query = select(OAuthToken).where(
            and_(
                OAuthToken.user_id == UUID(user_id),
                OAuthToken.provider == provider
            )
        )
        
        if integration_id:
            query = query.where(OAuthToken.integration_id == integration_id)
        
        result = self.session.execute(query)
        return result.scalar_one_or_none()
    
    def _encrypt_credential_data(self, credential_data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive fields in credential data."""
        if not credential_data:
            return {}
        
        # Fields that should be encrypted
        sensitive_fields = ["client_secret", "api_key", "secret_key", "private_key"]
        
        encrypted_data = credential_data.copy()
        for field in sensitive_fields:
            if field in encrypted_data and encrypted_data[field] is not None:
                encrypted_data[field] = self.encryption.encrypt(str(encrypted_data[field]))
        
        return encrypted_data
    
    def _decrypt_credential_data(self, credential_data: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt sensitive fields in credential data."""
        if not credential_data:
            return {}
        
        # Fields that should be decrypted
        sensitive_fields = ["client_secret", "api_key", "secret_key", "private_key"]
        
        decrypted_data = credential_data.copy()
        for field in sensitive_fields:
            if field in decrypted_data and decrypted_data[field] is not None:
                try:
                    decrypted_data[field] = self.encryption.decrypt(decrypted_data[field])
                except DecryptionError:
                    # Field might not be encrypted (backward compatibility)
                    pass
        
        return decrypted_data
    
    async def _refresh_token_request(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        refresh_token: str
    ) -> Dict[str, Any]:
        """Make HTTP request to refresh OAuth2 token."""
        import httpx
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        }
        
        timeout = httpx.Timeout(
            connect=self.settings.api_timeout_connect,
            read=self.settings.api_timeout_read
        )
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                token_url,
                data=data,
                headers={"Accept": "application/json"}
            )
            
            if response.status_code != 200:
                raise CredentialServiceError(
                    f"Token refresh failed with status {response.status_code}: {response.text}"
                )
            
            return response.json()


# Global service instance for convenience
_credential_service: Optional[CredentialService] = None


def get_credential_service(session: Optional[Session] = None) -> CredentialService:
    """
    Get credential service instance.
    
    Args:
        session: Optional SQLAlchemy session
        
    Returns:
        CredentialService instance
    """
    if session:
        return CredentialService(session)
    
    global _credential_service
    if _credential_service is None:
        _credential_service = CredentialService()
    return _credential_service 