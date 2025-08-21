"""
Google Calendar Token Refresh Manager

This service handles background token refresh for Google Calendar OAuth tokens
to ensure persistent access to Google Calendar APIs.
"""

import asyncio
import datetime
import logging
from typing import Dict, List, Optional, Tuple

import httpx

from workflow_scheduler.core.config import settings
from workflow_scheduler.core.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class GoogleCalendarTokenManager:
    """
    Manages Google Calendar OAuth token refresh operations.

    Features:
    - Monitors token expiry times (< 30 minutes remaining)
    - Refreshes tokens using refresh_token
    - Updates oauth_tokens table with new tokens
    - Handles token refresh failures gracefully
    - Runs as background task every 20 minutes
    """

    def __init__(self):
        self.is_running = False
        self._refresh_interval = 20 * 60  # Check every 20 minutes
        self._expiry_threshold = 30 * 60  # Refresh if < 30 minutes remaining
        self._task: Optional[asyncio.Task] = None

        # Google OAuth configuration
        self._token_url = "https://oauth2.googleapis.com/token"
        self._userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"

    async def start(self):
        """Start the background token refresh task."""
        if self.is_running:
            logger.warning("Google Calendar token manager is already running")
            return

        self.is_running = True
        self._task = asyncio.create_task(self._refresh_loop())
        logger.info("🔄 Started Google Calendar token refresh manager")

    async def stop(self):
        """Stop the background token refresh task."""
        self.is_running = False

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("⏹️ Stopped Google Calendar token refresh manager")

    async def _refresh_loop(self):
        """Main background loop for token refresh."""
        logger.info(
            f"🔄 Google Calendar token refresh loop started (interval: {self._refresh_interval}s)"
        )

        while self.is_running:
            try:
                await self._check_and_refresh_tokens()

                # Wait for next check interval
                await asyncio.sleep(self._refresh_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in Google Calendar token refresh loop: {e}", exc_info=True)
                # Wait a bit before retrying on error
                await asyncio.sleep(60)  # 1 minute retry delay

    async def _check_and_refresh_tokens(self):
        """Check all Google Calendar tokens and refresh those that are expiring."""
        try:
            # Get all Google Calendar tokens that need refresh
            tokens_to_refresh = await self._get_tokens_needing_refresh()

            if not tokens_to_refresh:
                logger.debug("✅ No Google Calendar tokens need refresh")
                return

            logger.info(f"🔄 Found {len(tokens_to_refresh)} Google Calendar tokens needing refresh")

            # Process each token
            refresh_results = []
            for token_record in tokens_to_refresh:
                try:
                    result = await self._refresh_single_token(token_record)
                    refresh_results.append(result)
                except Exception as e:
                    logger.error(
                        f"❌ Failed to refresh token for user {token_record.get('user_id')}: {e}",
                        exc_info=True,
                    )

            # Log summary
            successful_refreshes = sum(1 for r in refresh_results if r)
            logger.info(
                f"✅ Token refresh completed: {successful_refreshes}/{len(tokens_to_refresh)} successful"
            )

        except Exception as e:
            logger.error(f"❌ Error checking Google Calendar tokens: {e}", exc_info=True)

    async def _get_tokens_needing_refresh(self) -> List[Dict]:
        """
        Get all Google Calendar tokens that are expired or expiring soon.

        Returns:
            List of oauth_tokens records that need refresh
        """
        try:
            supabase = get_supabase_client()
            if not supabase:
                logger.error("❌ Supabase client not available")
                return []

            # Calculate threshold time (current time + threshold seconds)
            now = datetime.datetime.now(datetime.timezone.utc)
            threshold_time = now + datetime.timedelta(seconds=self._expiry_threshold)

            # Query for Google Calendar tokens that are expired or expiring soon
            result = (
                supabase.table("oauth_tokens")
                .select("*")
                .eq("integration_id", "google_calendar")
                .eq("provider", "google")
                .eq("is_active", True)
                .not_.is_("refresh_token", "null")  # Must have refresh token
                .or_(
                    f"expires_at.lt.{threshold_time.isoformat()},"  # Expiring soon
                    f"expires_at.lt.{now.isoformat()}"  # Already expired
                )
                .execute()
            )

            tokens = result.data or []

            if tokens:
                logger.info(f"🔍 Found {len(tokens)} Google Calendar tokens needing refresh:")
                for token in tokens:
                    user_email = token.get("credential_data", {}).get("user_email", "unknown")
                    expires_at = token.get("expires_at")
                    logger.info(f"   - User: {user_email}, Expires: {expires_at}")

            return tokens

        except Exception as e:
            logger.error(f"❌ Error querying tokens needing refresh: {e}", exc_info=True)
            return []

    async def _refresh_single_token(self, token_record: Dict) -> bool:
        """
        Refresh a single Google Calendar OAuth token.

        Args:
            token_record: oauth_tokens table record

        Returns:
            bool: True if refresh successful, False otherwise
        """
        user_id = token_record.get("user_id")
        user_email = token_record.get("credential_data", {}).get("user_email", "unknown")
        refresh_token = token_record.get("refresh_token")

        if not refresh_token:
            logger.warning(f"⚠️ No refresh token available for user {user_email} ({user_id})")
            return False

        try:
            logger.info(f"🔄 Refreshing Google Calendar token for user {user_email}")

            # Prepare token refresh request
            refresh_data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
            }

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            }

            # Make token refresh request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._token_url, data=refresh_data, headers=headers, timeout=30.0
                )

                if response.status_code != 200:
                    logger.error(
                        f"❌ Google token refresh failed for {user_email}: "
                        f"{response.status_code} - {response.text}"
                    )
                    return False

                token_result = response.json()
                new_access_token = token_result.get("access_token")
                new_refresh_token = token_result.get("refresh_token")  # May be None
                expires_in = token_result.get("expires_in", 3600)

                if not new_access_token:
                    logger.error(f"❌ No access token in refresh response for {user_email}")
                    return False

                # Update the token in database
                success = await self._update_token_in_database(
                    token_record,
                    new_access_token,
                    new_refresh_token
                    or refresh_token,  # Keep old refresh token if new one not provided
                    expires_in,
                )

                if success:
                    logger.info(f"✅ Successfully refreshed Google Calendar token for {user_email}")
                    return True
                else:
                    logger.error(
                        f"❌ Failed to update database after token refresh for {user_email}"
                    )
                    return False

        except httpx.TimeoutException:
            logger.error(f"⏰ Timeout refreshing Google Calendar token for {user_email}")
            return False
        except httpx.RequestError as e:
            logger.error(f"🌐 Network error refreshing token for {user_email}: {e}")
            return False
        except Exception as e:
            logger.error(
                f"❌ Unexpected error refreshing token for {user_email}: {e}", exc_info=True
            )
            return False

    async def _update_token_in_database(
        self,
        original_record: Dict,
        new_access_token: str,
        new_refresh_token: str,
        expires_in: int,
    ) -> bool:
        """
        Update the oauth_tokens table with refreshed token data.

        Args:
            original_record: Original oauth_tokens record
            new_access_token: New access token from Google
            new_refresh_token: New or existing refresh token
            expires_in: Token expiration time in seconds

        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            supabase = get_supabase_client()
            if not supabase:
                logger.error("❌ Supabase client not available for token update")
                return False

            # Calculate new expiry time
            now = datetime.datetime.now(datetime.timezone.utc)
            new_expires_at = now + datetime.timedelta(seconds=expires_in)

            # Update credential data with new expiry info
            credential_data = original_record.get("credential_data", {})
            credential_data.update(
                {
                    "expires_in": expires_in,
                    "last_refreshed": now.isoformat(),
                    "refresh_count": credential_data.get("refresh_count", 0) + 1,
                }
            )

            # Prepare update data
            update_data = {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "expires_at": new_expires_at.isoformat(),
                "credential_data": credential_data,
                "updated_at": now.isoformat(),
            }

            # Update the record
            result = (
                supabase.table("oauth_tokens")
                .update(update_data)
                .eq("id", original_record["id"])
                .execute()
            )

            if result.data:
                user_email = credential_data.get("user_email", "unknown")
                logger.info(
                    f"✅ Database updated with refreshed token for {user_email} - "
                    f"expires: {new_expires_at.isoformat()}"
                )
                return True
            else:
                logger.error("❌ No rows updated in oauth_tokens table")
                return False

        except Exception as e:
            logger.error(f"❌ Database update error: {e}", exc_info=True)
            return False

    async def force_refresh_user_token(self, user_id: str) -> Tuple[bool, str]:
        """
        Force refresh a specific user's Google Calendar token.

        Args:
            user_id: User ID to refresh token for

        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            logger.info(f"🔄 Force refreshing Google Calendar token for user {user_id}")

            # Get the user's token record
            supabase = get_supabase_client()
            if not supabase:
                return False, "Supabase client not available"

            result = (
                supabase.table("oauth_tokens")
                .select("*")
                .eq("user_id", user_id)
                .eq("integration_id", "google_calendar")
                .eq("is_active", True)
                .execute()
            )

            if not result.data:
                return False, f"No active Google Calendar token found for user {user_id}"

            token_record = result.data[0]
            success = await self._refresh_single_token(token_record)

            if success:
                return True, "Token refreshed successfully"
            else:
                return False, "Token refresh failed"

        except Exception as e:
            logger.error(f"❌ Error force refreshing token for user {user_id}: {e}", exc_info=True)
            return False, f"Error: {str(e)}"

    async def get_status(self) -> Dict:
        """
        Get current status of the token manager.

        Returns:
            Dict: Status information
        """
        try:
            supabase = get_supabase_client()
            if not supabase:
                return {
                    "status": "error",
                    "message": "Supabase client not available",
                    "is_running": self.is_running,
                }

            # Get counts of Google Calendar tokens
            total_result = (
                supabase.table("oauth_tokens")
                .select("id", count="exact")
                .eq("integration_id", "google_calendar")
                .eq("is_active", True)
                .execute()
            )

            active_result = (
                supabase.table("oauth_tokens")
                .select("id", count="exact")
                .eq("integration_id", "google_calendar")
                .eq("is_active", True)
                .not_.is_("refresh_token", "null")
                .execute()
            )

            # Get tokens needing refresh (for immediate status)
            now = datetime.datetime.now(datetime.timezone.utc)
            threshold_time = now + datetime.timedelta(seconds=self._expiry_threshold)

            expiring_result = (
                supabase.table("oauth_tokens")
                .select("id", count="exact")
                .eq("integration_id", "google_calendar")
                .eq("is_active", True)
                .not_.is_("refresh_token", "null")
                .lt("expires_at", threshold_time.isoformat())
                .execute()
            )

            return {
                "status": "healthy" if self.is_running else "stopped",
                "is_running": self.is_running,
                "refresh_interval": self._refresh_interval,
                "expiry_threshold": self._expiry_threshold,
                "token_stats": {
                    "total_google_calendar_tokens": total_result.count or 0,
                    "tokens_with_refresh_capability": active_result.count or 0,
                    "tokens_needing_refresh": expiring_result.count or 0,
                },
                "next_check": "continuous" if self.is_running else "not scheduled",
            }

        except Exception as e:
            logger.error(f"❌ Error getting token manager status: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e),
                "is_running": self.is_running,
            }


# Global instance
_token_manager: Optional[GoogleCalendarTokenManager] = None


def get_google_calendar_token_manager() -> GoogleCalendarTokenManager:
    """Get the global Google Calendar token manager instance."""
    global _token_manager
    if _token_manager is None:
        _token_manager = GoogleCalendarTokenManager()
    return _token_manager


async def initialize_google_calendar_token_manager() -> GoogleCalendarTokenManager:
    """Initialize and start the Google Calendar token manager."""
    token_manager = get_google_calendar_token_manager()
    await token_manager.start()
    return token_manager


async def cleanup_google_calendar_token_manager():
    """Stop and cleanup the Google Calendar token manager."""
    global _token_manager
    if _token_manager:
        await _token_manager.stop()
        _token_manager = None
