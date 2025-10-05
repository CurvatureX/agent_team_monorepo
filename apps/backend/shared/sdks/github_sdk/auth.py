"""GitHub App authentication utilities."""

import time
from datetime import datetime, timedelta
from typing import Dict, Optional

import jwt
from cryptography.hazmat.primitives import serialization

from .exceptions import GitHubAuthError


class GitHubAuth:
    """Handles GitHub App authentication and JWT generation."""

    def __init__(self, app_id: str, private_key: str):
        self.app_id = app_id
        self.private_key = private_key
        self._parsed_private_key = None
        self._installation_tokens: Dict[int, Dict] = {}

        # Parse private key on initialization
        self._parse_private_key()

    def _parse_private_key(self):
        """Parse the private key for JWT signing."""
        try:
            if isinstance(self.private_key, str):
                # Handle both file paths and direct key content
                if self.private_key.startswith("-----BEGIN"):
                    key_content = self.private_key
                else:
                    with open(self.private_key, "r") as f:
                        key_content = f.read()
            else:
                key_content = self.private_key

            self._parsed_private_key = serialization.load_pem_private_key(
                key_content.encode("utf-8"), password=None
            )
        except Exception as e:
            raise GitHubAuthError(f"Failed to parse private key: {str(e)}")

    def generate_jwt_token(self, expiration_minutes: int = 10) -> str:
        """Generate JWT token for GitHub App authentication."""
        if not self._parsed_private_key:
            raise GitHubAuthError("Private key not properly initialized")

        import time

        now = int(time.time())
        payload = {
            "iat": now - 60,  # Issued 1 minute ago to account for clock skew
            "exp": now + (expiration_minutes * 60),
            "iss": self.app_id,
        }

        try:
            return jwt.encode(payload, self._parsed_private_key, algorithm="RS256")
        except Exception as e:
            raise GitHubAuthError(f"Failed to generate JWT token: {str(e)}")

    def is_installation_token_valid(self, installation_id: int) -> bool:
        """Check if cached installation token is still valid."""
        if installation_id not in self._installation_tokens:
            return False

        token_data = self._installation_tokens[installation_id]
        expires_at = datetime.fromisoformat(token_data["expires_at"].replace("Z", "+00:00"))

        # Consider token expired if it expires within 5 minutes
        from datetime import timezone

        now_utc = datetime.now(timezone.utc)
        return expires_at > now_utc + timedelta(minutes=5)

    def cache_installation_token(self, installation_id: int, token: str, expires_at: str):
        """Cache installation token for reuse."""
        from datetime import timezone

        self._installation_tokens[installation_id] = {
            "token": token,
            "expires_at": expires_at,
            "cached_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_cached_installation_token(self, installation_id: int) -> Optional[str]:
        """Get cached installation token if valid."""
        if self.is_installation_token_valid(installation_id):
            return self._installation_tokens[installation_id]["token"]

        # Remove expired token
        self._installation_tokens.pop(installation_id, None)
        return None

    def clear_installation_token_cache(self, installation_id: int = None):
        """Clear installation token cache."""
        if installation_id:
            self._installation_tokens.pop(installation_id, None)
        else:
            self._installation_tokens.clear()

    @staticmethod
    def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
        """Verify GitHub webhook signature."""
        import hashlib
        import hmac

        if not signature.startswith("sha256="):
            return False

        expected_signature = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

        received_signature = signature[7:]  # Remove 'sha256=' prefix

        return hmac.compare_digest(expected_signature, received_signature)
