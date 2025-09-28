"""
OAuth2 service for workflow_engine_v2.

Provides OAuth2 token exchange, refresh, and credential management
for external service integrations.
"""

from __future__ import annotations

import base64
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models.supabase import create_supabase_client

from .credential_encryption import CredentialEncryption

logger = logging.getLogger(__name__)


@dataclass
class TokenResponse:
    """OAuth token response."""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_at: Optional[datetime] = None
    scope: Optional[str] = None


class OAuth2ServiceV2:
    """OAuth2 service for external action integrations."""

    def __init__(self):
        """Initialize OAuth2 service."""
        self.logger = logging.getLogger(__name__)

        # Initialize credential encryption service
        credential_encryption_key = os.getenv(
            "CREDENTIAL_ENCRYPTION_KEY", "MMfaVOL8LCWT8kWM9dSUVDSPVF0+A3wMGO1+kEHG85o="
        )
        self.credential_encryption = CredentialEncryption(credential_encryption_key)

        # Initialize Supabase database client
        self.supabase_client = create_supabase_client()
        if not self.supabase_client:
            self.logger.warning("Supabase client not initialized - credential operations will fail")

        # OAuth provider configuration mapping
        self.oauth_provider_configurations = {
            "google": {
                "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
                "token_url": "https://oauth2.googleapis.com/token",
                "scopes": [
                    "https://www.googleapis.com/auth/calendar",
                    "https://www.googleapis.com/auth/calendar.events",
                ],
            },
            "github": {
                "client_id": os.getenv("GITHUB_CLIENT_ID", ""),
                "client_secret": os.getenv("GITHUB_CLIENT_SECRET", ""),
                "token_url": "https://github.com/login/oauth/access_token",
                "scopes": ["repo", "user"],
            },
            "slack": {
                "client_id": os.getenv("SLACK_CLIENT_ID", ""),
                "client_secret": os.getenv("SLACK_CLIENT_SECRET", ""),
                "token_url": "https://slack.com/api/oauth.v2.access",
                "scopes": ["chat:write", "channels:read"],
            },
            "notion": {
                "client_id": os.getenv("NOTION_CLIENT_ID", ""),
                "client_secret": os.getenv("NOTION_CLIENT_SECRET", ""),
                "token_url": "https://api.notion.com/v1/oauth/token",
                "scopes": [],
            },
            "api_call": {
                "client_id": os.getenv("API_CALL_CLIENT_ID", ""),
                "client_secret": os.getenv("API_CALL_CLIENT_SECRET", ""),
                "token_url": os.getenv("API_CALL_TOKEN_URL", ""),
                "scopes": os.getenv("API_CALL_SCOPES", "").split(",")
                if os.getenv("API_CALL_SCOPES")
                else [],
            },
        }

    def check_user_exists(self, user_id: str) -> bool:
        """Check if user exists in auth.users table."""
        if not self.supabase_client_client:
            self.logger.error("Supabase client not initialized")
            return False

        try:
            user_existence_result = self.supabase_client_client.rpc(
                "check_user_exists", {"user_id": user_id}
            ).execute()
            return user_existence_result.data is True
        except Exception as user_check_error:
            self.logger.error(f"Error checking user existence {user_id}: {user_check_error}")
            return False

    async def exchange_code_for_token(
        self, code: str, client_id: str, redirect_uri: str, provider: str
    ) -> TokenResponse:
        """Exchange authorization code for access token."""
        self.logger.info(f"Exchanging authorization code for {provider}")

        if provider not in self.oauth_provider_configurations:
            raise ValueError(f"Unsupported OAuth provider: {provider}")

        provider_oauth_config = self.oauth_provider_configurations[provider]

        # Prepare token exchange request data
        token_exchange_data = {
            "grant_type": "authorization_code",
            "client_id": client_id or provider_oauth_config["client_id"],
            "client_secret": provider_oauth_config["client_secret"],
            "code": code,
            "redirect_uri": redirect_uri,
        }

        request_headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        # Special handling for different OAuth providers
        if provider == "notion":
            # Notion requires Basic authentication header
            basic_auth_string = (
                f"{provider_oauth_config['client_id']}:{provider_oauth_config['client_secret']}"
            )
            basic_auth_encoded = base64.b64encode(basic_auth_string.encode()).decode()
            request_headers["Authorization"] = f"Basic {basic_auth_encoded}"
            # Remove client_secret from body for Notion
            del token_exchange_data["client_secret"]

        # Send token exchange request to OAuth provider
        async with httpx.AsyncClient() as http_client:
            try:
                token_response = await http_client.post(
                    provider_oauth_config["token_url"],
                    data=token_exchange_data,
                    headers=request_headers,
                    timeout=30.0,
                )

                if not token_response.is_success:
                    error_response_text = token_response.text
                    self.logger.error(
                        f"Token exchange failed: {token_response.status_code} - {error_response_text}"
                    )
                    raise Exception(
                        f"Token exchange failed: {token_response.status_code} - {error_response_text}"
                    )

                # Parse OAuth token response
                oauth_token_data = token_response.json()
                self.logger.info(f"Token exchange successful for {provider}")

                # Extract token information from response
                access_token = oauth_token_data.get("access_token")
                if not access_token:
                    raise Exception("No access token in OAuth response")

                refresh_token = oauth_token_data.get("refresh_token")
                token_type = oauth_token_data.get("token_type", "Bearer")
                expires_in_seconds = oauth_token_data.get("expires_in")
                token_scope = oauth_token_data.get("scope", "")

                # Calculate token expiration timestamp
                token_expires_at = None
                if expires_in_seconds:
                    try:
                        token_expires_at = datetime.now(timezone.utc) + timedelta(
                            seconds=int(expires_in_seconds)
                        )
                    except (ValueError, TypeError):
                        self.logger.warning(f"Invalid expires_in value: {expires_in_seconds}")

                return TokenResponse(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    token_type=token_type,
                    expires_at=token_expires_at,
                    scope=token_scope,
                )

            except httpx.RequestError as e:
                self.logger.error(f"Network error during token exchange: {str(e)}")
                raise Exception(f"Network error: {str(e)}")

    async def store_user_credentials(
        self, user_id: str, provider: str, token_response: TokenResponse
    ) -> bool:
        """Store user credentials to oauth_tokens table."""
        try:
            if not self.supabase_client:
                self.logger.error("Supabase client not initialized")
                return False

            # Check if user exists
            if not self.check_user_exists(user_id):
                self.logger.error(f"User does not exist in auth.users: {user_id}")
                return False

            # Map OAuth provider to integration identifier for database consistency
            integration_identifier = "google_calendar" if provider == "google" else provider

            oauth_credential_metadata = {
                "scope": token_response.scope,
                "token_type": token_response.token_type,
                "expires_in": int(
                    (token_response.expires_at - datetime.now(timezone.utc)).total_seconds()
                )
                if token_response.expires_at
                else None,
                "callback_timestamp": datetime.now(timezone.utc).isoformat(),
            }

            oauth_token_record = {
                "user_id": user_id,
                "integration_id": integration_identifier,
                "provider": provider,
                "access_token": token_response.access_token,
                "refresh_token": token_response.refresh_token,
                "expires_at": token_response.expires_at.isoformat()
                if token_response.expires_at
                else None,
                "token_type": token_response.token_type,
                "is_active": True,
                "credential_data": oauth_credential_metadata,
            }

            # Check for existing OAuth token record to update or insert
            existing_token_query = (
                self.supabase_client.table("oauth_tokens")
                .select("id")
                .eq("user_id", user_id)
                .or_(f"provider.eq.{provider},integration_id.eq.{integration_identifier}")
                .limit(1)
                .execute()
            )

            if existing_token_query.data:
                existing_token_id = existing_token_query.data[0]["id"]
                self.supabase_client.table("oauth_tokens").update(oauth_token_record).eq(
                    "id", existing_token_id
                ).execute()
            else:
                self.supabase_client.table("oauth_tokens").insert(oauth_token_record).execute()

            self.logger.info(
                f"Successfully stored credentials for user {user_id}, provider {provider}"
            )
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to store credentials for user {user_id}, provider {provider}: {e}"
            )
            return False

    async def get_valid_token(self, user_id: str, provider: str) -> Optional[str]:
        """Get valid access token, refresh if expired."""
        try:
            if not self.supabase_client:
                return None

            # Query oauth_tokens table by user_id and provider
            result = (
                self.supabase_client.table("oauth_tokens")
                .select("access_token, refresh_token, expires_at, is_active")
                .eq("user_id", user_id)
                .eq("provider", provider)
                .order("updated_at", desc=True)
                .limit(1)
                .execute()
            )

            if not result.data:
                self.logger.debug(f"No credentials found for user {user_id}, provider {provider}")
                return None

            row = result.data[0]
            access_token = row.get("access_token")
            refresh_token = row.get("refresh_token")
            expires_at = row.get("expires_at")
            is_active = row.get("is_active")

            if not is_active:
                self.logger.debug(
                    f"Credentials marked as invalid for user {user_id}, provider {provider}"
                )
                return None

            # Check if access token is expired
            now = datetime.now(timezone.utc)
            token_expired = False

            if expires_at:
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))

                # 5 minute buffer to avoid API calls with expired tokens
                buffer_time = timedelta(minutes=5)
                if expires_at <= (now + buffer_time):
                    token_expired = True
                    self.logger.info(
                        f"Access token expired or about to expire for user {user_id}, provider {provider}"
                    )

            # If not expired, return token
            if not token_expired:
                self.logger.debug(f"Retrieved valid token for user {user_id}, provider {provider}")
                return access_token

            # Try to refresh token
            if not refresh_token:
                self.logger.warning(
                    f"Access token expired but no refresh token for user {user_id}, provider {provider}"
                )
                return None

            new_token_response = await self._refresh_access_token(refresh_token, provider)

            if new_token_response:
                # Store new token info
                await self.store_user_credentials(user_id, provider, new_token_response)
                self.logger.info(
                    f"Successfully refreshed token for user {user_id}, provider {provider}"
                )
                return new_token_response.access_token
            else:
                self.logger.warning(
                    f"Failed to refresh token for user {user_id}, provider {provider}"
                )
                # Mark credentials as invalid
                await self._mark_credentials_invalid(user_id, provider, "refresh_failed")
                return None

        except Exception as e:
            self.logger.error(
                f"Failed to get valid token for user {user_id}, provider {provider}: {e}"
            )
            return None

    async def _refresh_access_token(
        self, refresh_token: str, provider: str
    ) -> Optional[TokenResponse]:
        """Refresh access token using refresh token."""
        try:
            provider_config = self.oauth_provider_configurations.get(provider)
            if not provider_config:
                self.logger.error(f"No configuration found for provider: {provider}")
                return None

            # Build refresh token request
            data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": provider_config["client_id"],
                "client_secret": provider_config["client_secret"],
            }

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            }

            # Special handling for different providers
            if provider == "slack":
                # Slack uses Basic auth for refresh
                auth_string = f"{provider_config['client_id']}:{provider_config['client_secret']}"
                auth_encoded = base64.b64encode(auth_string.encode()).decode()
                headers["Authorization"] = f"Basic {auth_encoded}"
            elif provider == "notion":
                # Notion requires Basic auth
                auth_string = f"{provider_config['client_id']}:{provider_config['client_secret']}"
                auth_encoded = base64.b64encode(auth_string.encode()).decode()
                headers["Authorization"] = f"Basic {auth_encoded}"
                del data["client_secret"]

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    provider_config["token_url"], data=data, headers=headers, timeout=30.0
                )

                if response.status_code != 200:
                    self.logger.error(
                        f"Token refresh failed for provider {provider}: {response.status_code} - {response.text}"
                    )
                    return None

                token_response = response.json()
                access_token = token_response.get("access_token")

                if not access_token:
                    self.logger.error(
                        f"No access token in refresh response for provider {provider}"
                    )
                    return None

                # Build new TokenResponse
                new_refresh_token = token_response.get("refresh_token", refresh_token)
                token_type = token_response.get("token_type", "Bearer")
                expires_in = token_response.get("expires_in")
                scope = token_response.get("scope", "")

                expires_at = None
                if expires_in:
                    expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))

                return TokenResponse(
                    access_token=access_token,
                    refresh_token=new_refresh_token,
                    token_type=token_type,
                    expires_at=expires_at,
                    scope=scope,
                )

        except Exception as e:
            self.logger.error(f"Exception during token refresh for provider {provider}: {e}")
            return None

    async def _mark_credentials_invalid(self, user_id: str, provider: str, reason: str):
        """Mark credentials as invalid."""
        try:
            if not self.supabase_client:
                return

            # Map provider to integration_id
            integration_id = "google_calendar" if provider == "google" else provider

            matches = (
                self.supabase_client.table("oauth_tokens")
                .select("id, credential_data")
                .eq("user_id", user_id)
                .or_(f"provider.eq.{provider},integration_id.eq.{integration_id}")
                .execute()
            )

            for row in matches.data or []:
                cred = row.get("credential_data") or {}
                cred["validation_error"] = reason
                self.supabase_client.table("oauth_tokens").update(
                    {
                        "is_active": False,
                        "credential_data": cred,
                    }
                ).eq("id", row["id"]).execute()

            self.logger.info(
                f"Marked credentials as invalid for user {user_id}, provider {provider}, reason: {reason}"
            )
        except Exception as e:
            self.logger.error(
                f"Failed to mark credentials invalid for user {user_id}, provider {provider}: {e}"
            )

    def get_install_url(self, provider: str, redirect_uri: str, state: Optional[str] = None) -> str:
        """Generate OAuth install URL for provider."""
        if provider not in self.oauth_provider_configurations:
            raise ValueError(f"Unsupported provider: {provider}")

        config = self.oauth_provider_configurations[provider]

        # Base URLs for different providers
        auth_urls = {
            "google": "https://accounts.google.com/o/oauth2/auth",
            "github": "https://github.com/login/oauth/authorize",
            "slack": "https://slack.com/oauth/v2/authorize",
            "notion": "https://api.notion.com/v1/oauth/authorize",
        }

        if provider not in auth_urls:
            raise ValueError(f"No auth URL configured for provider: {provider}")

        params = {
            "client_id": config["client_id"],
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(config["scopes"]),
        }

        if state:
            params["state"] = state

        # Build URL
        auth_url = auth_urls[provider]
        param_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{auth_url}?{param_string}"


__all__ = ["OAuth2ServiceV2", "TokenResponse"]
