"""
Google Calendar SDK client implementation.
"""

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from ..base import APIResponse, BaseSDK, OAuth2Config
from .exceptions import (
    GoogleCalendarError,
    GoogleCalendarAuthError,
    GoogleCalendarNotFoundError,
    GoogleCalendarPermissionError,
    GoogleCalendarRateLimitError,
    GoogleCalendarValidationError,
)
from .models import Calendar, Event


class GoogleCalendarSDK(BaseSDK):
    """Google Calendar SDK client."""
    
    @property
    def base_url(self) -> str:
        return "https://www.googleapis.com/calendar/v3"
    
    @property
    def supported_operations(self) -> Dict[str, str]:
        return {
            "list_events": "List calendar events",
            "create_event": "Create new calendar event",
            "update_event": "Update existing event",
            "delete_event": "Delete event",
            "get_event": "Get single event details",
            "list_calendars": "List user's calendars",
            "create_calendar": "Create new calendar",
            "get_calendar": "Get calendar details",
            "search_events": "Search events in calendar",
            "quick_add": "Quick add event using natural language",
            "watch_events": "Set up webhook for event changes",
            "stop_watching": "Stop webhook monitoring"
        }
    
    def get_oauth2_config(self) -> OAuth2Config:
        """Get Google Calendar OAuth2 configuration."""
        return OAuth2Config(
            client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
            auth_url="https://accounts.google.com/o/oauth2/auth",
            token_url="https://oauth2.googleapis.com/token",
            revoke_url="https://oauth2.googleapis.com/revoke",
            scopes=[
                "https://www.googleapis.com/auth/calendar",
                "https://www.googleapis.com/auth/calendar.events"
            ],
            redirect_uri=os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8002/api/v1/oauth2/google/callback")
        )
    
    def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """Validate Google Calendar credentials."""
        return "access_token" in credentials and bool(credentials["access_token"])
    
    async def call_operation(
        self, 
        operation: str, 
        parameters: Dict[str, Any], 
        credentials: Dict[str, str]
    ) -> APIResponse:
        """Execute Google Calendar API operation."""
        if not self.validate_credentials(credentials):
            return APIResponse(
                success=False,
                error="Invalid credentials: missing access_token",
                provider="google_calendar",
                operation=operation
            )
        
        if operation not in self.supported_operations:
            return APIResponse(
                success=False,
                error=f"Unsupported operation: {operation}",
                provider="google_calendar",
                operation=operation
            )
        
        try:
            # Route to specific operation handler
            handler_map = {
                "list_events": self._list_events,
                "create_event": self._create_event,
                "update_event": self._update_event,
                "delete_event": self._delete_event,
                "get_event": self._get_event,
                "list_calendars": self._list_calendars,
                "create_calendar": self._create_calendar,
                "get_calendar": self._get_calendar,
                "search_events": self._search_events,
                "quick_add": self._quick_add,
                "watch_events": self._watch_events,
                "stop_watching": self._stop_watching
            }
            
            handler = handler_map[operation]
            result = await handler(parameters, credentials)
            
            return APIResponse(
                success=True,
                data=result,
                provider="google_calendar",
                operation=operation
            )
            
        except (GoogleCalendarAuthError, GoogleCalendarPermissionError) as e:
            return APIResponse(
                success=False,
                error=str(e),
                provider="google_calendar",
                operation=operation,
                status_code=401 if isinstance(e, GoogleCalendarAuthError) else 403
            )
        except GoogleCalendarRateLimitError as e:
            return APIResponse(
                success=False,
                error=str(e),
                provider="google_calendar",
                operation=operation,
                status_code=429
            )
        except Exception as e:
            self.logger.error(f"Google Calendar {operation} failed: {str(e)}")
            return APIResponse(
                success=False,
                error=str(e),
                provider="google_calendar",
                operation=operation
            )
    
    async def _list_events(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """List calendar events."""
        calendar_id = parameters.get("calendar_id", "primary")
        
        # Build query parameters
        query_params = {}
        
        # Time range filters
        if "time_min" in parameters and parameters["time_min"] is not None:
            query_params["timeMin"] = self._format_google_datetime(parameters["time_min"])
        if "time_max" in parameters and parameters["time_max"] is not None:
            query_params["timeMax"] = self._format_google_datetime(parameters["time_max"])
        
        # Other filters
        if "max_results" in parameters:
            query_params["maxResults"] = min(int(parameters["max_results"]), 2500)
        if "single_events" in parameters:
            query_params["singleEvents"] = bool(parameters["single_events"])
        if "order_by" in parameters:
            query_params["orderBy"] = parameters["order_by"]
        if "q" in parameters:
            query_params["q"] = parameters["q"]
        if "show_deleted" in parameters:
            query_params["showDeleted"] = bool(parameters["show_deleted"])
        
        url = f"{self.base_url}/calendars/{calendar_id}/events"
        if query_params:
            url += f"?{urlencode(query_params)}"
        
        headers = self._prepare_headers(credentials)
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not (200 <= response.status_code < 300):
            self._handle_error(response)
        
        data = response.json()
        
        # Convert to Event objects
        events = [Event.from_dict(event_data) for event_data in data.get("items", [])]
        
        return {
            "events": [event.__dict__ for event in events],  # Convert to dict for serialization
            "events_objects": events,  # Keep objects for internal use
            "next_page_token": data.get("nextPageToken"),
            "next_sync_token": data.get("nextSyncToken"),
            "summary": data.get("summary"),
            "total_count": len(events)
        }
    
    async def _create_event(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """Create new calendar event."""
        calendar_id = parameters.get("calendar_id", "primary")
        
        # Validate required parameters
        if "summary" not in parameters:
            raise GoogleCalendarValidationError("Missing required parameter: summary")
        
        # Create Event object to validate data
        event = Event(
            summary=parameters["summary"],
            description=parameters.get("description"),
            location=parameters.get("location")
        )
        
        # Handle time settings
        if "start" in parameters and "end" in parameters:
            event_data = event.to_dict()
            event_data["start"] = self._format_event_time(parameters["start"])
            event_data["end"] = self._format_event_time(parameters["end"])
        elif "start_datetime" in parameters and "end_datetime" in parameters:
            event_data = event.to_dict()
            event_data["start"] = {"dateTime": self._format_google_datetime(parameters["start_datetime"])}
            event_data["end"] = {"dateTime": self._format_google_datetime(parameters["end_datetime"])}
        elif "date" in parameters:
            # All-day event
            event_data = event.to_dict()
            event_data["start"] = {"date": parameters["date"]}
            event_data["end"] = {"date": parameters["date"]}
        else:
            raise GoogleCalendarValidationError("Missing required time parameters")
        
        # Handle attendees
        if "attendees" in parameters:
            event_data["attendees"] = [
                {"email": email} for email in parameters["attendees"]
            ]
        
        # Handle other optional parameters
        if "reminders" in parameters:
            event_data["reminders"] = parameters["reminders"]
        if "recurrence" in parameters:
            event_data["recurrence"] = parameters["recurrence"]
        
        url = f"{self.base_url}/calendars/{calendar_id}/events"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request(
            "POST", url, headers=headers, json_data=event_data
        )
        
        if not (200 <= response.status_code < 300):
            self._handle_error(response)
        
        event_response = response.json()
        created_event = Event.from_dict(event_response)
        
        return {
            "event": created_event.__dict__,
            "event_object": created_event,
            "event_id": created_event.id,
            "html_link": created_event.html_link
        }
    
    # ... (继续其他方法的实现)
    
    async def _test_connection_impl(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Google Calendar specific connection test."""
        try:
            url = f"{self.base_url}/calendars/primary"
            headers = self._prepare_headers(credentials)
            
            response = await self.make_http_request("GET", url, headers=headers)
            
            if 200 <= response.status_code < 300:
                calendar_data = response.json()
                return {
                    "credentials_valid": True,
                    "calendar_access": True,
                    "primary_calendar": calendar_data.get("summary"),
                    "user_email": calendar_data.get("id")
                }
            else:
                self._handle_error(response)
                
        except Exception as e:
            return {
                "credentials_valid": False,
                "error": str(e)
            }
    
    def _prepare_headers(self, credentials: Dict[str, str]) -> Dict[str, str]:
        """Prepare Google Calendar API headers."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AgentTeam-Workflow-Engine/1.0"
        }
        
        if "access_token" in credentials:
            headers["Authorization"] = f"Bearer {credentials['access_token']}"
        
        return headers
    
    def _handle_error(self, response) -> None:
        """Handle HTTP error responses."""
        if response.status_code == 401:
            raise GoogleCalendarAuthError("Authentication failed")
        elif response.status_code == 403:
            raise GoogleCalendarPermissionError("Insufficient permissions")
        elif response.status_code == 404:
            raise GoogleCalendarNotFoundError("Resource not found")
        elif response.status_code == 429:
            raise GoogleCalendarRateLimitError("Rate limit exceeded")
        elif 400 <= response.status_code < 500:
            raise GoogleCalendarError(f"Client error: {response.status_code}")
        elif 500 <= response.status_code < 600:
            raise GoogleCalendarError(f"Server error: {response.status_code}")
        else:
            raise GoogleCalendarError(f"Unexpected error: {response.status_code}")
    
    def _format_google_datetime(self, dt_input) -> str:
        """Format datetime for Google Calendar API."""
        if dt_input is None:
            raise GoogleCalendarValidationError("Datetime input cannot be None")
        elif isinstance(dt_input, str):
            if not dt_input.strip():
                raise GoogleCalendarValidationError("Datetime string cannot be empty")
            return dt_input
        elif isinstance(dt_input, datetime):
            # Ensure UTC timezone and format
            if dt_input.tzinfo is None:
                dt_input = dt_input.replace(tzinfo=timezone.utc)
            return dt_input.isoformat()
        else:
            raise GoogleCalendarValidationError(f"Invalid datetime format: {type(dt_input)} (value: {dt_input})")
    
    def _format_event_time(self, time_input) -> Dict[str, str]:
        """Format event time for Google Calendar API."""
        if isinstance(time_input, dict):
            return time_input
        elif isinstance(time_input, str):
            if "T" in time_input:
                return {"dateTime": time_input}
            else:
                return {"date": time_input}
        elif isinstance(time_input, datetime):
            return {"dateTime": self._format_google_datetime(time_input)}
        else:
            raise GoogleCalendarValidationError(f"Invalid time format: {type(time_input)}")
    
    # Placeholder methods for other operations - can be implemented as needed
    async def _update_event(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """Update existing event."""
        # Implementation similar to create_event but with PATCH
        raise NotImplementedError("Update event not yet implemented")
    
    async def _delete_event(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """Delete event."""
        raise NotImplementedError("Delete event not yet implemented")
    
    async def _get_event(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """Get single event details."""
        raise NotImplementedError("Get event not yet implemented")
    
    async def _list_calendars(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """List user's calendars."""
        raise NotImplementedError("List calendars not yet implemented")
    
    async def _create_calendar(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """Create new calendar."""
        raise NotImplementedError("Create calendar not yet implemented")
    
    async def _get_calendar(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """Get calendar details."""
        raise NotImplementedError("Get calendar not yet implemented")
    
    async def _search_events(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """Search events."""
        raise NotImplementedError("Search events not yet implemented")
    
    async def _quick_add(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """Quick add event using natural language."""
        raise NotImplementedError("Quick add not yet implemented")
    
    async def _watch_events(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """Set up webhook for event changes."""
        raise NotImplementedError("Watch events not yet implemented")
    
    async def _stop_watching(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """Stop webhook monitoring."""
        raise NotImplementedError("Stop watching not yet implemented")