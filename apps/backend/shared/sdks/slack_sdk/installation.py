"""
Slack OAuth installation manager.

Handles OAuth flow for Slack app installation, token management,
and workspace-specific configurations.
"""

import hashlib
import hmac
import json
import secrets
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from .exceptions import SlackAPIError, SlackAuthError


class SlackInstallationManager:
    """
    Manages Slack OAuth installation process and token storage.

    Handles the OAuth 2.0 flow for installing Slack apps in workspaces,
    including state verification, token exchange, and installation storage.
    """

    OAUTH_AUTHORIZE_URL = "https://slack.com/oauth/v2/authorize"
    OAUTH_ACCESS_URL = "https://slack.com/api/oauth.v2.access"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        signing_secret: str,
        redirect_uri: str,
        scopes: List[str],
        user_scopes: Optional[List[str]] = None,
    ):
        """
        Initialize Slack installation manager.

        Args:
            client_id: Slack app client ID
            client_secret: Slack app client secret
            signing_secret: Slack app signing secret for request verification
            redirect_uri: OAuth redirect URI
            scopes: Bot token scopes to request
            user_scopes: User token scopes to request (optional)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.signing_secret = signing_secret
        self.redirect_uri = redirect_uri
        self.scopes = scopes
        self.user_scopes = user_scopes or []

        self.http_client = httpx.Client(timeout=30)

    def generate_install_url(
        self,
        state: Optional[str] = None,
        team_id: Optional[str] = None,
    ) -> tuple[str, str]:
        """
        Generate OAuth install URL for Slack app installation.

        Args:
            state: Optional custom state parameter
            team_id: Optional team ID to pre-select workspace

        Returns:
            Tuple of (install_url, state_value)
        """
        if state is None:
            state = secrets.token_urlsafe(32)

        params = {
            "client_id": self.client_id,
            "scope": ",".join(self.scopes),
            "redirect_uri": self.redirect_uri,
            "state": state,
        }

        if self.user_scopes:
            params["user_scope"] = ",".join(self.user_scopes)

        if team_id:
            params["team"] = team_id

        install_url = f"{self.OAUTH_AUTHORIZE_URL}?{urlencode(params)}"
        return install_url, state

    def handle_oauth_callback(
        self,
        code: str,
        state: str,
        expected_state: str,
    ) -> Dict[str, Any]:
        """
        Handle OAuth callback and exchange code for tokens.

        Args:
            code: Authorization code from Slack
            state: State parameter from callback
            expected_state: Expected state value for verification

        Returns:
            Installation data including tokens and team info

        Raises:
            SlackAuthError: If state verification fails or OAuth exchange fails
        """
        # Verify state parameter
        if not hmac.compare_digest(state, expected_state):
            raise SlackAuthError(
                f"Invalid state parameter. Expected: {expected_state}, Got: {state}"
            )

        # Exchange code for access token
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
        }

        try:
            response = self.http_client.post(self.OAUTH_ACCESS_URL, data=data)
            response.raise_for_status()
            result = response.json()

            if not result.get("ok", False):
                error = result.get("error", "unknown_error")
                raise SlackAuthError(f"OAuth token exchange failed: {error}")

            # Extract installation data
            installation_data = {
                "team_id": result.get("team", {}).get("id"),
                "team_name": result.get("team", {}).get("name"),
                "bot_token": result.get("access_token"),
                "bot_user_id": result.get("bot_user_id"),
                "scope": result.get("scope"),
                "token_type": result.get("token_type"),
                "app_id": result.get("app_id"),
                "enterprise_id": result.get("enterprise", {}).get("id")
                if result.get("enterprise")
                else None,
                "enterprise_name": result.get("enterprise", {}).get("name")
                if result.get("enterprise")
                else None,
                "is_enterprise_install": result.get("is_enterprise_install", False),
            }

            # Include user token if user scopes were requested
            if "authed_user" in result and result["authed_user"].get("access_token"):
                installation_data.update(
                    {
                        "user_token": result["authed_user"]["access_token"],
                        "user_id": result["authed_user"]["id"],
                        "user_scope": result["authed_user"].get("scope"),
                    }
                )

            return installation_data

        except httpx.RequestError as e:
            raise SlackAuthError(f"OAuth request failed: {str(e)}")
        except json.JSONDecodeError:
            raise SlackAuthError("Invalid JSON response from Slack OAuth")

    def verify_request_signature(
        self,
        body: str,
        timestamp: str,
        signature: str,
    ) -> bool:
        """
        Verify Slack request signature for webhooks and events.

        Args:
            body: Raw request body
            timestamp: X-Slack-Request-Timestamp header
            signature: X-Slack-Signature header

        Returns:
            True if signature is valid, False otherwise
        """
        # Check timestamp to prevent replay attacks (within 5 minutes)
        import time

        if abs(time.time() - int(timestamp)) > 300:
            return False

        # Create signature
        sig_basestring = f"v0:{timestamp}:{body}"
        computed_signature = (
            "v0="
            + hmac.new(
                self.signing_secret.encode(), sig_basestring.encode(), hashlib.sha256
            ).hexdigest()
        )

        return hmac.compare_digest(computed_signature, signature)

    def revoke_token(self, token: str) -> bool:
        """
        Revoke a Slack token.

        Args:
            token: Token to revoke

        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.http_client.post(
                "https://slack.com/api/auth.revoke",
                headers={"Authorization": f"Bearer {token}"},
                data={"token": token},
            )

            response.raise_for_status()
            result = response.json()
            return result.get("ok", False)

        except (httpx.RequestError, json.JSONDecodeError):
            return False

    def close(self):
        """Close HTTP client."""
        self.http_client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
