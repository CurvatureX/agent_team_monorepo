"""
Google Calendar SDK client implementation.
"""

import os
import uuid
from datetime import datetime, timedelta, timezone
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
        calendar_id = parameters.get("calendar_id", "primary")
        event_id = parameters.get("event_id")
        
        if not event_id:
            raise GoogleCalendarValidationError("Missing required parameter: event_id")
        
        # Build update data
        update_data = {}
        
        # Update basic fields if provided
        if "summary" in parameters:
            update_data["summary"] = parameters["summary"]
        
        if "description" in parameters:
            update_data["description"] = parameters["description"]
        
        if "location" in parameters:
            update_data["location"] = parameters["location"]
        
        # Update time if provided
        if "start" in parameters and "end" in parameters:
            update_data["start"] = self._format_event_time(parameters["start"])
            update_data["end"] = self._format_event_time(parameters["end"])
        elif "start_datetime" in parameters and "end_datetime" in parameters:
            update_data["start"] = {"dateTime": self._format_google_datetime(parameters["start_datetime"])}
            update_data["end"] = {"dateTime": self._format_google_datetime(parameters["end_datetime"])}
        
        # Update attendees if provided
        if "attendees" in parameters:
            update_data["attendees"] = [
                {"email": email} for email in parameters["attendees"]
            ]
        
        # Update reminders if provided
        if "reminders" in parameters:
            update_data["reminders"] = parameters["reminders"]
        
        # Update recurrence if provided
        if "recurrence" in parameters:
            update_data["recurrence"] = parameters["recurrence"]
        
        url = f"{self.base_url}/calendars/{calendar_id}/events/{event_id}"
        headers = self._prepare_headers(credentials)
        
        # Add query parameters if needed
        query_params = {}
        if parameters.get("send_notifications"):
            query_params["sendNotifications"] = "true"
        if query_params:
            url += f"?{urlencode(query_params)}"
        
        response = await self.make_http_request(
            "PATCH", url, headers=headers, json_data=update_data
        )
        
        if not (200 <= response.status_code < 300):
            self._handle_error(response)
        
        updated_event = response.json()
        return {
            "event": Event.from_dict(updated_event).__dict__,
            "event_id": updated_event.get("id"),
            "html_link": updated_event.get("htmlLink")
        }
    
    async def _delete_event(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """Delete event."""
        calendar_id = parameters.get("calendar_id", "primary")
        event_id = parameters.get("event_id")
        
        if not event_id:
            raise GoogleCalendarValidationError("Missing required parameter: event_id")
        
        url = f"{self.base_url}/calendars/{calendar_id}/events/{event_id}"
        headers = self._prepare_headers(credentials)
        
        # Add query parameters if needed
        query_params = {}
        if parameters.get("send_notifications"):
            query_params["sendNotifications"] = "true"
        if query_params:
            url += f"?{urlencode(query_params)}"
        
        response = await self.make_http_request("DELETE", url, headers=headers)
        
        if response.status_code == 204:
            # Success - no content
            return {
                "success": True,
                "message": "Event deleted successfully",
                "event_id": event_id,
                "calendar_id": calendar_id
            }
        elif response.status_code == 410:
            # Already deleted
            return {
                "success": True,
                "message": "Event was already deleted",
                "event_id": event_id,
                "calendar_id": calendar_id
            }
        else:
            self._handle_error(response)
    
    async def _get_event(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """Get single event details."""
        calendar_id = parameters.get("calendar_id", "primary")
        event_id = parameters.get("event_id")
        
        if not event_id:
            raise GoogleCalendarValidationError("Missing required parameter: event_id")
        
        url = f"{self.base_url}/calendars/{calendar_id}/events/{event_id}"
        headers = self._prepare_headers(credentials)
        
        # Add query parameters if needed
        query_params = {}
        if parameters.get("time_zone"):
            query_params["timeZone"] = parameters["time_zone"]
        if query_params:
            url += f"?{urlencode(query_params)}"
        
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not (200 <= response.status_code < 300):
            self._handle_error(response)
        
        event_data = response.json()
        event = Event.from_dict(event_data)
        
        return {
            "event": event.__dict__,
            "event_object": event,
            "event_id": event.id,
            "html_link": event.html_link,
            "calendar_id": calendar_id
        }
    
    async def _list_calendars(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """List user's calendars."""
        url = f"{self.base_url}/users/me/calendarList"
        headers = self._prepare_headers(credentials)
        
        # Build query parameters
        query_params = {}
        if parameters.get("min_access_role"):
            query_params["minAccessRole"] = parameters["min_access_role"]
        if parameters.get("show_deleted"):
            query_params["showDeleted"] = "true"
        if parameters.get("show_hidden"):
            query_params["showHidden"] = "true"
        if parameters.get("max_results"):
            query_params["maxResults"] = min(int(parameters["max_results"]), 250)
        if parameters.get("page_token"):
            query_params["pageToken"] = parameters["page_token"]
        
        if query_params:
            url += f"?{urlencode(query_params)}"
        
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not (200 <= response.status_code < 300):
            self._handle_error(response)
        
        data = response.json()
        
        # Convert to Calendar objects
        calendars = []
        for cal_data in data.get("items", []):
            calendar = Calendar(
                id=cal_data.get("id"),
                summary=cal_data.get("summary"),
                description=cal_data.get("description"),
                time_zone=cal_data.get("timeZone")
            )
            calendars.append({
                "id": calendar.id,
                "summary": calendar.summary,
                "description": calendar.description,
                "time_zone": calendar.time_zone,
                "access_role": cal_data.get("accessRole"),
                "primary": cal_data.get("primary", False),
                "selected": cal_data.get("selected", False),
                "background_color": cal_data.get("backgroundColor"),
                "foreground_color": cal_data.get("foregroundColor")
            })
        
        return {
            "calendars": calendars,
            "calendars_objects": calendars,
            "next_page_token": data.get("nextPageToken"),
            "total_count": len(calendars)
        }
    
    async def _create_calendar(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """Create new calendar."""
        # Validate required parameters
        if "summary" not in parameters:
            raise GoogleCalendarValidationError("Missing required parameter: summary")
        
        # Build calendar data directly (don't use Calendar object for creation)
        calendar_data = {
            "summary": parameters["summary"],
            "description": parameters.get("description", ""),
            "timeZone": parameters.get("time_zone", "UTC")
        }
        
        # Add optional parameters
        if parameters.get("location"):
            calendar_data["location"] = parameters["location"]
        
        url = f"{self.base_url}/calendars"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request(
            "POST", url, headers=headers, json_data=calendar_data
        )
        
        if not (200 <= response.status_code < 300):
            self._handle_error(response)
        
        created_calendar = response.json()
        new_calendar = Calendar.from_dict(created_calendar)
        
        return {
            "calendar": new_calendar.__dict__,
            "calendar_object": new_calendar,
            "calendar_id": new_calendar.id,
            "summary": new_calendar.summary
        }
    
    async def _get_calendar(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """Get calendar details."""
        calendar_id = parameters.get("calendar_id", "primary")
        
        url = f"{self.base_url}/calendars/{calendar_id}"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not (200 <= response.status_code < 300):
            self._handle_error(response)
        
        cal_data = response.json()
        calendar = Calendar.from_dict(cal_data)
        
        return {
            "calendar": calendar.__dict__,
            "calendar_object": calendar,
            "calendar_id": calendar.id,
            "summary": calendar.summary,
            "time_zone": calendar.time_zone
        }
    
    async def _search_events(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """Search events across calendars."""
        # Get search query
        query = parameters.get("q", parameters.get("query", ""))
        calendars = parameters.get("calendars", ["primary"])
        
        if isinstance(calendars, str):
            calendars = [calendars]
        
        all_events = []
        
        # Search each calendar
        for calendar_id in calendars:
            url = f"{self.base_url}/calendars/{calendar_id}/events"
            
            # Build query parameters
            query_params = {
                "q": query,
                "singleEvents": "true",
                "orderBy": "startTime"
            }
            
            # Add time range if specified
            if parameters.get("time_min"):
                query_params["timeMin"] = self._format_google_datetime(parameters["time_min"])
            if parameters.get("time_max"):
                query_params["timeMax"] = self._format_google_datetime(parameters["time_max"])
            
            # Limit results
            max_results = parameters.get("max_results", 100)
            query_params["maxResults"] = min(int(max_results), 250)
            
            url += f"?{urlencode(query_params)}"
            headers = self._prepare_headers(credentials)
            
            try:
                response = await self.make_http_request("GET", url, headers=headers)
                
                if 200 <= response.status_code < 300:
                    data = response.json()
                    for event_data in data.get("items", []):
                        event = Event.from_dict(event_data)
                        event_dict = event.__dict__
                        event_dict["calendar_id"] = calendar_id
                        all_events.append(event_dict)
            except Exception as e:
                self.logger.warning(f"Failed to search calendar {calendar_id}: {e}")
                continue
        
        # Sort by start time
        all_events.sort(key=lambda x: x.get("start", {}).get("dateTime", "") or x.get("start", {}).get("date", ""))
        
        return {
            "events": all_events,
            "total_count": len(all_events),
            "query": query,
            "calendars_searched": calendars
        }
    
    async def _quick_add(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """Quick add event using natural language."""
        calendar_id = parameters.get("calendar_id", "primary")
        text = parameters.get("text")
        
        if not text:
            raise GoogleCalendarValidationError("Missing required parameter: text")
        
        url = f"{self.base_url}/calendars/{calendar_id}/events/quickAdd"
        
        # Build query parameters
        query_params = {"text": text}
        if parameters.get("send_notifications"):
            query_params["sendNotifications"] = "true"
        
        url += f"?{urlencode(query_params)}"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request("POST", url, headers=headers)
        
        if not (200 <= response.status_code < 300):
            self._handle_error(response)
        
        event_data = response.json()
        event = Event.from_dict(event_data)
        
        return {
            "event": event.__dict__,
            "event_object": event,
            "event_id": event.id,
            "html_link": event.html_link,
            "original_text": text,
            "calendar_id": calendar_id
        }
    
    async def _watch_events(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """Set up webhook for event changes."""
        calendar_id = parameters.get("calendar_id", "primary")
        webhook_url = parameters.get("webhook_url")
        
        if not webhook_url:
            raise GoogleCalendarValidationError("Missing required parameter: webhook_url")
        
        # Generate unique channel ID if not provided
        import uuid
        channel_id = parameters.get("channel_id", str(uuid.uuid4()))
        
        # Build watch request
        watch_data = {
            "id": channel_id,
            "type": "web_hook",
            "address": webhook_url
        }
        
        # Add optional parameters
        if parameters.get("token"):
            watch_data["token"] = parameters["token"]
        
        # Set expiration (max 1 month from now)
        if parameters.get("expiration"):
            watch_data["expiration"] = str(int(parameters["expiration"]))
        else:
            # Default to 1 week
            from datetime import timedelta
            expiration = datetime.now(timezone.utc) + timedelta(days=7)
            watch_data["expiration"] = str(int(expiration.timestamp() * 1000))
        
        url = f"{self.base_url}/calendars/{calendar_id}/events/watch"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request(
            "POST", url, headers=headers, json_data=watch_data
        )
        
        if not (200 <= response.status_code < 300):
            self._handle_error(response)
        
        watch_response = response.json()
        
        return {
            "channel_id": watch_response.get("id"),
            "resource_id": watch_response.get("resourceId"),
            "resource_uri": watch_response.get("resourceUri"),
            "token": watch_response.get("token"),
            "expiration": watch_response.get("expiration"),
            "calendar_id": calendar_id,
            "webhook_url": webhook_url
        }
    
    async def _stop_watching(self, parameters: Dict[str, Any], credentials: Dict[str, str]) -> Dict[str, Any]:
        """Stop webhook monitoring."""
        channel_id = parameters.get("channel_id")
        resource_id = parameters.get("resource_id")
        
        if not channel_id or not resource_id:
            raise GoogleCalendarValidationError("Missing required parameters: channel_id and resource_id")
        
        # Build stop request
        stop_data = {
            "id": channel_id,
            "resourceId": resource_id
        }
        
        url = f"{self.base_url}/channels/stop"
        headers = self._prepare_headers(credentials)
        
        response = await self.make_http_request(
            "POST", url, headers=headers, json_data=stop_data
        )
        
        if response.status_code == 204:
            # Success - no content
            return {
                "success": True,
                "message": "Channel stopped successfully",
                "channel_id": channel_id,
                "resource_id": resource_id
            }
        else:
            self._handle_error(response)