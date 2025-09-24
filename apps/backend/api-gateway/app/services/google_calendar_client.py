"""
Google Calendar API Client
高级Google Calendar API客户端，针对MCP工具优化
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)


class GoogleCalendarError(Exception):
    """Base exception for Google Calendar operations."""

    pass


class GoogleCalendarAuthError(GoogleCalendarError):
    """Authentication related errors."""

    pass


class GoogleCalendarRateLimitError(GoogleCalendarError):
    """Rate limit exceeded errors."""

    pass


class GoogleCalendarNotFoundError(GoogleCalendarError):
    """Resource not found errors."""

    pass


class GoogleCalendarValidationError(GoogleCalendarError):
    """Request validation errors."""

    pass


class GoogleCalendarClient:
    """
    Advanced Google Calendar API client optimized for MCP tool usage.
    Provides comprehensive calendar management with proper error handling.
    """

    BASE_URL = "https://www.googleapis.com/calendar/v3"

    def __init__(self, access_token: str, timeout: int = 30):
        """
        Initialize Google Calendar client.

        Args:
            access_token: OAuth access token for Google Calendar API
            timeout: Request timeout in seconds
        """
        self.access_token = access_token
        self.timeout = timeout
        self._client = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make HTTP request to Google Calendar API with proper error handling."""
        client = await self._get_client()

        try:
            response = await client.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
            )

            # Handle different response status codes
            if response.status_code == 200 or response.status_code == 201:
                return response.json()
            elif response.status_code == 204:
                # No content (successful delete)
                return {"success": True}
            elif response.status_code == 401:
                raise GoogleCalendarAuthError("Invalid or expired access token")
            elif response.status_code == 403:
                error_data = response.json() if response.content else {}
                error_message = error_data.get("error", {}).get("message", "Access forbidden")
                if "quota" in error_message.lower() or "rate" in error_message.lower():
                    raise GoogleCalendarRateLimitError(f"Rate limit exceeded: {error_message}")
                else:
                    raise GoogleCalendarAuthError(f"Access forbidden: {error_message}")
            elif response.status_code == 404:
                raise GoogleCalendarNotFoundError("Calendar or event not found")
            elif response.status_code == 400:
                error_data = response.json() if response.content else {}
                error_message = error_data.get("error", {}).get("message", "Bad request")
                raise GoogleCalendarValidationError(f"Invalid request: {error_message}")
            elif response.status_code == 429:
                raise GoogleCalendarRateLimitError("Rate limit exceeded")
            else:
                error_data = response.json() if response.content else {}
                error_message = error_data.get("error", {}).get(
                    "message", f"HTTP {response.status_code}"
                )
                raise GoogleCalendarError(f"Request failed: {error_message}")

        except httpx.RequestError as e:
            raise GoogleCalendarError(f"Network error: {str(e)}")

    # Calendar Management
    async def list_calendars(self, max_results: int = 250) -> Dict[str, Any]:
        """List user's calendars."""
        url = f"{self.BASE_URL}/users/me/calendarList"
        params = {"maxResults": min(max_results, 250)}

        return await self._make_request("GET", url, params=params)

    async def get_calendar(self, calendar_id: str = "primary") -> Dict[str, Any]:
        """Get calendar details."""
        url = f"{self.BASE_URL}/calendars/{calendar_id}"
        return await self._make_request("GET", url)

    async def create_calendar(
        self, summary: str, description: str = None, time_zone: str = None
    ) -> Dict[str, Any]:
        """Create a new calendar."""
        url = f"{self.BASE_URL}/calendars"

        calendar_data = {"summary": summary}
        if description:
            calendar_data["description"] = description
        if time_zone:
            calendar_data["timeZone"] = time_zone

        return await self._make_request("POST", url, json_data=calendar_data)

    # Event Management
    async def list_events(
        self,
        calendar_id: str = "primary",
        time_min: str = None,
        time_max: str = None,
        max_results: int = 250,
        single_events: bool = True,
        order_by: str = "startTime",
        q: str = None,
        show_deleted: bool = False,
    ) -> Dict[str, Any]:
        """List calendar events with filtering options."""
        url = f"{self.BASE_URL}/calendars/{calendar_id}/events"

        params = {
            "maxResults": min(max_results, 2500),
            "singleEvents": single_events,
        }

        if time_min:
            params["timeMin"] = self._format_datetime(time_min)
        if time_max:
            params["timeMax"] = self._format_datetime(time_max)
        if order_by and single_events:
            params["orderBy"] = order_by
        if q:
            params["q"] = q
        if show_deleted:
            params["showDeleted"] = show_deleted

        result = await self._make_request("GET", url, params=params)

        return {
            "success": True,
            "events": result.get("items", []),
            "next_page_token": result.get("nextPageToken"),
            "next_sync_token": result.get("nextSyncToken"),
            "summary": result.get("summary"),
            "total_count": len(result.get("items", [])),
            "has_more": bool(result.get("nextPageToken")),
        }

    async def get_event(self, event_id: str, calendar_id: str = "primary") -> Dict[str, Any]:
        """Get a specific event."""
        url = f"{self.BASE_URL}/calendars/{calendar_id}/events/{event_id}"
        event = await self._make_request("GET", url)
        return {"success": True, "event": event}

    async def create_event(
        self,
        calendar_id: str = "primary",
        summary: str = None,
        description: str = None,
        location: str = None,
        start: Dict[str, str] = None,
        end: Dict[str, str] = None,
        attendees: List[Dict] = None,
        reminders: Dict = None,
        recurrence: List[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create a new calendar event."""
        if not summary:
            raise GoogleCalendarValidationError("Event summary is required")

        if not start or not end:
            raise GoogleCalendarValidationError("Event start and end times are required")

        url = f"{self.BASE_URL}/calendars/{calendar_id}/events"

        event_data = {"summary": summary}

        if description:
            event_data["description"] = description
        if location:
            event_data["location"] = location

        event_data["start"] = start
        event_data["end"] = end

        if attendees:
            event_data["attendees"] = attendees
        if reminders:
            event_data["reminders"] = reminders
        if recurrence:
            event_data["recurrence"] = recurrence

        # Add any additional fields
        for key, value in kwargs.items():
            if value is not None:
                event_data[key] = value

        event = await self._make_request("POST", url, json_data=event_data)

        return {
            "success": True,
            "event": event,
            "event_id": event.get("id"),
            "html_link": event.get("htmlLink"),
        }

    async def update_event(
        self,
        event_id: str,
        calendar_id: str = "primary",
        **update_fields,
    ) -> Dict[str, Any]:
        """Update an existing event."""
        if not update_fields:
            raise GoogleCalendarValidationError("No fields to update specified")

        url = f"{self.BASE_URL}/calendars/{calendar_id}/events/{event_id}"

        # Remove None values
        update_data = {k: v for k, v in update_fields.items() if v is not None}

        event = await self._make_request("PUT", url, json_data=update_data)

        return {
            "success": True,
            "event": event,
            "event_id": event.get("id"),
            "updated_fields": list(update_data.keys()),
        }

    async def delete_event(self, event_id: str, calendar_id: str = "primary") -> Dict[str, Any]:
        """Delete an event."""
        url = f"{self.BASE_URL}/calendars/{calendar_id}/events/{event_id}"

        try:
            await self._make_request("DELETE", url)
            return {
                "success": True,
                "message": "Event deleted successfully",
                "event_id": event_id,
            }
        except GoogleCalendarNotFoundError:
            # Event might already be deleted
            return {
                "success": True,
                "message": "Event was already deleted",
                "event_id": event_id,
            }

    # Quick Add (Natural Language)
    async def quick_add_event(
        self,
        text: str,
        calendar_id: str = "primary",
        send_notifications: bool = True,
    ) -> Dict[str, Any]:
        """Create event using natural language (Google's QuickAdd)."""
        if not text.strip():
            raise GoogleCalendarValidationError("Text description is required")

        url = f"{self.BASE_URL}/calendars/{calendar_id}/events/quickAdd"
        params = {
            "text": text,
            "sendNotifications": send_notifications,
        }

        event = await self._make_request("POST", url, params=params)

        return {
            "success": True,
            "event": event,
            "event_id": event.get("id"),
            "html_link": event.get("htmlLink"),
            "parsed_text": text,
        }

    # Search
    async def search_events(
        self,
        query: str,
        calendar_id: str = "primary",
        time_min: str = None,
        time_max: str = None,
        max_results: int = 250,
        **kwargs,
    ) -> Dict[str, Any]:
        """Search for events across calendars."""
        return await self.list_events(
            calendar_id=calendar_id,
            q=query,
            time_min=time_min,
            time_max=time_max,
            max_results=max_results,
            single_events=True,
            order_by="startTime",
            **kwargs,
        )

    # Free/Busy
    async def get_freebusy(
        self,
        calendars: List[str],
        time_min: str,
        time_max: str,
        timezone: str = "UTC",
    ) -> Dict[str, Any]:
        """Get free/busy information for calendars."""
        url = f"{self.BASE_URL}/freeBusy"

        freebusy_data = {
            "timeMin": self._format_datetime(time_min),
            "timeMax": self._format_datetime(time_max),
            "timeZone": timezone,
            "items": [{"id": cal_id} for cal_id in calendars],
        }

        return await self._make_request("POST", url, json_data=freebusy_data)

    # Watch (Webhooks)
    async def watch_events(
        self,
        webhook_url: str,
        calendar_id: str = "primary",
        channel_id: str = None,
        token: str = None,
        expiration: int = None,
    ) -> Dict[str, Any]:
        """Set up webhook for calendar changes."""
        if not webhook_url:
            raise GoogleCalendarValidationError("Webhook URL is required")

        url = f"{self.BASE_URL}/calendars/{calendar_id}/events/watch"

        watch_data = {
            "id": channel_id or f"calendar_watch_{int(datetime.now().timestamp())}",
            "type": "web_hook",
            "address": webhook_url,
        }

        if token:
            watch_data["token"] = token
        if expiration:
            watch_data["expiration"] = expiration

        result = await self._make_request("POST", url, json_data=watch_data)

        return {
            "success": True,
            "channel": result,
            "channel_id": result.get("id"),
            "resource_id": result.get("resourceId"),
        }

    async def stop_watching(self, channel_id: str, resource_id: str) -> Dict[str, Any]:
        """Stop watching calendar changes."""
        url = f"{self.BASE_URL}/channels/stop"

        stop_data = {
            "id": channel_id,
            "resourceId": resource_id,
        }

        await self._make_request("POST", url, json_data=stop_data)

        return {
            "success": True,
            "message": "Channel stopped successfully",
            "channel_id": channel_id,
        }

    # Connection Test
    async def test_connection(self) -> Dict[str, Any]:
        """Test API connection and credentials."""
        try:
            calendar = await self.get_calendar("primary")
            return {
                "credentials_valid": True,
                "calendar_access": True,
                "primary_calendar": calendar.get("summary"),
                "user_email": calendar.get("id"),
            }
        except Exception as e:
            return {
                "credentials_valid": False,
                "error": str(e),
            }

    # Utility Methods
    def _format_datetime(self, dt_input) -> str:
        """Format datetime for Google Calendar API."""
        if dt_input is None:
            raise GoogleCalendarValidationError("Datetime input cannot be None")

        if isinstance(dt_input, str):
            # Ensure proper RFC3339 format
            if not dt_input.strip():
                raise GoogleCalendarValidationError("Datetime string cannot be empty")

            # If already properly formatted, return as-is
            if "T" in dt_input and ("Z" in dt_input or "+" in dt_input or dt_input.endswith(":00")):
                return dt_input

            # Try to parse and reformat
            try:
                dt = datetime.fromisoformat(dt_input.replace("Z", "+00:00"))
                return dt.isoformat()
            except ValueError:
                # Return as-is and let Google Calendar handle parsing
                return dt_input

        elif isinstance(dt_input, datetime):
            # Ensure timezone info
            if dt_input.tzinfo is None:
                dt_input = dt_input.replace(tzinfo=timezone.utc)
            return dt_input.isoformat()

        else:
            raise GoogleCalendarValidationError(f"Invalid datetime format: {type(dt_input)}")

    def _format_event_time(self, time_input) -> Dict[str, str]:
        """Format event time for Google Calendar API."""
        if isinstance(time_input, dict):
            return time_input
        elif isinstance(time_input, str):
            if "T" in time_input:
                return {"dateTime": self._format_datetime(time_input)}
            else:
                return {"date": time_input}
        elif isinstance(time_input, datetime):
            return {"dateTime": self._format_datetime(time_input)}
        else:
            raise GoogleCalendarValidationError(f"Invalid time format: {type(time_input)}")
