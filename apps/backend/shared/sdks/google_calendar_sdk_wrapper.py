"""
Google Calendar SDK wrapper for workflow engine integration.

This module provides a unified interface for Google Calendar operations compatible with
the external action node system, following the same pattern as Notion SDK.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from .base import APIResponse, AuthenticationError, BaseSDK, OAuth2Config, SDKError
from .google_calendar_sdk import (
    GoogleCalendarError,
    GoogleCalendarAuthError,
    GoogleCalendarNotFoundError,
    GoogleCalendarPermissionError,
    GoogleCalendarRateLimitError,
    GoogleCalendarValidationError,
)


class GoogleCalendarSDK(BaseSDK):
    """Google Calendar SDK wrapper for external action nodes."""

    def __init__(self):
        """Initialize Google Calendar SDK wrapper."""
        super().__init__()
        self.logger = logging.getLogger(__name__)

    @property
    def base_url(self) -> str:
        """Get the base URL for the Google Calendar API."""
        return "https://www.googleapis.com/calendar/v3"

    @property
    def supported_operations(self) -> Dict[str, str]:
        """Get supported operations and their descriptions."""
        return {
            # Event operations
            "event_list": "List calendar events with filtering",
            "event_create": "Create a new calendar event",
            "event_get": "Get a specific event by ID",
            "event_update": "Update an existing event",
            "event_delete": "Delete an event",
            "event_search": "Search events across calendars",
            "event_quick_add": "Quick add event using natural language",
            
            # Calendar operations
            "calendar_list": "List user's calendars",
            "calendar_get": "Get calendar details",
            "calendar_create": "Create a new calendar",
            "calendar_update": "Update calendar settings",
            "calendar_delete": "Delete a calendar",
            
            # Advanced operations
            "event_instances": "Get recurring event instances",
            "event_move": "Move event to another calendar",
            "freebusy_query": "Query free/busy information",
            "watch_events": "Set up webhook for event changes",
            "stop_watching": "Stop webhook monitoring",
        }

    def get_oauth2_config(self) -> OAuth2Config:
        """Get OAuth2 configuration for Google Calendar."""
        return OAuth2Config(
            client_id="",  # To be configured by deployment
            client_secret="",  # To be configured by deployment
            auth_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            scopes=[
                "https://www.googleapis.com/auth/calendar",
                "https://www.googleapis.com/auth/calendar.events",
                "https://www.googleapis.com/auth/calendar.readonly",
            ],
            redirect_uri="",  # To be configured by deployment
        )

    def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """Validate that the provided credentials are valid."""
        access_token = credentials.get("access_token")
        if not access_token:
            return False
        
        # Basic validation - token should be non-empty
        return len(access_token) > 10

    async def call_operation(
        self, operation: str, parameters: Dict[str, Any], credentials: Dict[str, str]
    ) -> APIResponse:
        """
        Execute a Google Calendar operation.

        Args:
            operation: Operation to perform
            parameters: Operation parameters
            credentials: Authentication credentials

        Returns:
            APIResponse with result or error
        """
        if operation not in self.supported_operations:
            return APIResponse(
                success=False, error=f"Unsupported operation: {operation}", status_code=400
            )

        access_token = credentials.get("access_token")
        if not access_token:
            return APIResponse(
                success=False, error="Missing access_token in credentials", status_code=401
            )

        try:
            # Route to specific operation handler
            if operation == "event_list":
                return await self._handle_event_list(access_token, parameters)
            elif operation == "event_create":
                return await self._handle_event_create(access_token, parameters)
            elif operation == "event_get":
                return await self._handle_event_get(access_token, parameters)
            elif operation == "event_update":
                return await self._handle_event_update(access_token, parameters)
            elif operation == "event_delete":
                return await self._handle_event_delete(access_token, parameters)
            elif operation == "event_search":
                return await self._handle_event_search(access_token, parameters)
            elif operation == "event_quick_add":
                return await self._handle_event_quick_add(access_token, parameters)
            elif operation == "calendar_list":
                return await self._handle_calendar_list(access_token, parameters)
            elif operation == "calendar_get":
                return await self._handle_calendar_get(access_token, parameters)
            elif operation == "calendar_create":
                return await self._handle_calendar_create(access_token, parameters)
            elif operation == "calendar_update":
                return await self._handle_calendar_update(access_token, parameters)
            elif operation == "calendar_delete":
                return await self._handle_calendar_delete(access_token, parameters)
            elif operation == "event_instances":
                return await self._handle_event_instances(access_token, parameters)
            elif operation == "event_move":
                return await self._handle_event_move(access_token, parameters)
            elif operation == "freebusy_query":
                return await self._handle_freebusy_query(access_token, parameters)
            elif operation == "watch_events":
                return await self._handle_watch_events(access_token, parameters)
            elif operation == "stop_watching":
                return await self._handle_stop_watching(access_token, parameters)
            else:
                return APIResponse(
                    success=False,
                    error=f"Operation {operation} not implemented",
                    status_code=501,
                )

        except GoogleCalendarAuthError as e:
            self.logger.error(f"Google Calendar auth error: {e}")
            return APIResponse(
                success=False, error=f"Authentication failed: {str(e)}", status_code=401
            )
        except GoogleCalendarRateLimitError as e:
            self.logger.warning(f"Google Calendar rate limit: {e}")
            return APIResponse(
                success=False, error=f"Rate limit exceeded: {str(e)}", status_code=429
            )
        except GoogleCalendarPermissionError as e:
            self.logger.error(f"Google Calendar permission error: {e}")
            return APIResponse(
                success=False, error=f"Permission denied: {str(e)}", status_code=403
            )
        except GoogleCalendarNotFoundError as e:
            self.logger.error(f"Google Calendar not found error: {e}")
            return APIResponse(
                success=False, error=f"Resource not found: {str(e)}", status_code=404
            )
        except GoogleCalendarError as e:
            self.logger.error(f"Google Calendar API error: {e}")
            return APIResponse(
                success=False,
                error=f"API error: {str(e)}",
                status_code=getattr(e, "status_code", 500),
            )
        except Exception as e:
            self.logger.error(f"Unexpected error in Google Calendar SDK: {e}")
            return APIResponse(success=False, error=f"Unexpected error: {str(e)}", status_code=500)

    async def _handle_event_list(
        self, access_token: str, parameters: Dict[str, Any]
    ) -> APIResponse:
        """Handle list events operation."""
        calendar_id = parameters.get("calendar_id", "primary")
        
        # Build query parameters
        query_params = {}
        
        # Time range filters
        time_min = parameters.get("time_min")
        time_max = parameters.get("time_max")
        
        if time_min:
            query_params["timeMin"] = self._format_datetime(time_min)
        if time_max:
            query_params["timeMax"] = self._format_datetime(time_max)
        
        # Pagination and sorting
        max_results = parameters.get("max_results", 250)
        if max_results:
            query_params["maxResults"] = min(int(max_results), 2500)
        
        if parameters.get("page_token"):
            query_params["pageToken"] = parameters["page_token"]
        
        # Other filters
        if parameters.get("single_events") is not None:
            query_params["singleEvents"] = str(parameters["single_events"]).lower()
        
        if parameters.get("order_by"):
            query_params["orderBy"] = parameters["order_by"]
        
        if parameters.get("q"):  # Search query
            query_params["q"] = parameters["q"]
        
        if parameters.get("show_deleted") is not None:
            query_params["showDeleted"] = str(parameters["show_deleted"]).lower()
        
        if parameters.get("show_hidden") is not None:
            query_params["showHiddenInvitations"] = str(parameters["show_hidden"]).lower()
        
        # Make API request
        url = f"{self.base_url}/calendars/{calendar_id}/events"
        if query_params:
            url += f"?{urlencode(query_params)}"
        
        headers = self._prepare_headers(access_token)
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not self._is_success(response.status_code):
            self._handle_error_response(response)
        
        data = response.json()
        
        # Format response
        events = []
        for event_data in data.get("items", []):
            events.append(self._format_event(event_data))
        
        return APIResponse(
            success=True,
            data={
                "events": events,
                "total_count": len(events),
                "next_page_token": data.get("nextPageToken"),
                "next_sync_token": data.get("nextSyncToken"),
                "calendar_id": calendar_id,
                "time_zone": data.get("timeZone"),
            },
            status_code=200,
        )

    async def _handle_event_create(
        self, access_token: str, parameters: Dict[str, Any]
    ) -> APIResponse:
        """Handle create event operation."""
        calendar_id = parameters.get("calendar_id", "primary")
        
        # Validate required fields
        if not parameters.get("summary"):
            return APIResponse(
                success=False,
                error="Event summary is required",
                status_code=400,
            )
        
        # Build event data
        event_data = {
            "summary": parameters["summary"],
        }
        
        # Add optional fields
        if parameters.get("description"):
            event_data["description"] = parameters["description"]
        
        if parameters.get("location"):
            event_data["location"] = parameters["location"]
        
        # Handle date/time
        start = parameters.get("start")
        end = parameters.get("end")
        
        if not start or not end:
            return APIResponse(
                success=False,
                error="Start and end times are required",
                status_code=400,
            )
        
        # Determine if it's an all-day event or timed event
        if isinstance(start, str) and "T" not in start:
            # All-day event
            event_data["start"] = {"date": start}
            event_data["end"] = {"date": end}
        else:
            # Timed event
            event_data["start"] = {"dateTime": self._format_datetime(start)}
            event_data["end"] = {"dateTime": self._format_datetime(end)}
            
            # Add timezone if provided
            if parameters.get("time_zone"):
                event_data["start"]["timeZone"] = parameters["time_zone"]
                event_data["end"]["timeZone"] = parameters["time_zone"]
        
        # Handle attendees
        if parameters.get("attendees"):
            attendees = parameters["attendees"]
            if isinstance(attendees, str):
                attendees = [attendees]
            event_data["attendees"] = [{"email": email} for email in attendees]
            
            # Set notification settings
            if parameters.get("send_notifications") is not None:
                event_data["sendNotifications"] = parameters["send_notifications"]
        
        # Handle reminders
        if parameters.get("reminders"):
            event_data["reminders"] = parameters["reminders"]
        elif parameters.get("reminder_minutes"):
            # Simple reminder setup
            minutes = parameters["reminder_minutes"]
            event_data["reminders"] = {
                "useDefault": False,
                "overrides": [{"method": "popup", "minutes": int(minutes)}],
            }
        
        # Handle recurrence
        if parameters.get("recurrence"):
            event_data["recurrence"] = parameters["recurrence"]
        elif parameters.get("recurrence_rule"):
            # Simple recurrence rule
            event_data["recurrence"] = [parameters["recurrence_rule"]]
        
        # Handle conference data
        if parameters.get("add_conference"):
            event_data["conferenceData"] = {
                "createRequest": {
                    "requestId": f"conference-{datetime.now().timestamp()}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            }
        
        # Make API request
        url = f"{self.base_url}/calendars/{calendar_id}/events"
        headers = self._prepare_headers(access_token)
        
        # Add conference data parameter if needed
        if parameters.get("add_conference"):
            url += "?conferenceDataVersion=1"
        
        response = await self.make_http_request(
            "POST", url, headers=headers, json_data=event_data
        )
        
        if not self._is_success(response.status_code):
            self._handle_error_response(response)
        
        created_event = response.json()
        
        return APIResponse(
            success=True,
            data={
                "event": self._format_event(created_event),
                "event_id": created_event.get("id"),
                "html_link": created_event.get("htmlLink"),
                "calendar_id": calendar_id,
            },
            status_code=201,
        )

    async def _handle_event_get(
        self, access_token: str, parameters: Dict[str, Any]
    ) -> APIResponse:
        """Handle get event operation."""
        calendar_id = parameters.get("calendar_id", "primary")
        event_id = parameters.get("event_id")
        
        if not event_id:
            return APIResponse(
                success=False,
                error="event_id is required",
                status_code=400,
            )
        
        url = f"{self.base_url}/calendars/{calendar_id}/events/{event_id}"
        headers = self._prepare_headers(access_token)
        
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not self._is_success(response.status_code):
            self._handle_error_response(response)
        
        event_data = response.json()
        
        return APIResponse(
            success=True,
            data={
                "event": self._format_event(event_data),
                "calendar_id": calendar_id,
            },
            status_code=200,
        )

    async def _handle_event_update(
        self, access_token: str, parameters: Dict[str, Any]
    ) -> APIResponse:
        """Handle update event operation."""
        calendar_id = parameters.get("calendar_id", "primary")
        event_id = parameters.get("event_id")
        
        if not event_id:
            return APIResponse(
                success=False,
                error="event_id is required",
                status_code=400,
            )
        
        # First, get the existing event
        url = f"{self.base_url}/calendars/{calendar_id}/events/{event_id}"
        headers = self._prepare_headers(access_token)
        
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not self._is_success(response.status_code):
            self._handle_error_response(response)
        
        event_data = response.json()
        
        # Update fields
        if "summary" in parameters:
            event_data["summary"] = parameters["summary"]
        
        if "description" in parameters:
            event_data["description"] = parameters["description"]
        
        if "location" in parameters:
            event_data["location"] = parameters["location"]
        
        # Update date/time if provided
        if "start" in parameters and "end" in parameters:
            start = parameters["start"]
            end = parameters["end"]
            
            if isinstance(start, str) and "T" not in start:
                event_data["start"] = {"date": start}
                event_data["end"] = {"date": end}
            else:
                event_data["start"] = {"dateTime": self._format_datetime(start)}
                event_data["end"] = {"dateTime": self._format_datetime(end)}
                
                if parameters.get("time_zone"):
                    event_data["start"]["timeZone"] = parameters["time_zone"]
                    event_data["end"]["timeZone"] = parameters["time_zone"]
        
        # Update attendees if provided
        if "attendees" in parameters:
            attendees = parameters["attendees"]
            if isinstance(attendees, str):
                attendees = [attendees]
            event_data["attendees"] = [{"email": email} for email in attendees]
        
        # Update reminders if provided
        if "reminders" in parameters:
            event_data["reminders"] = parameters["reminders"]
        
        # Make update request
        response = await self.make_http_request(
            "PUT", url, headers=headers, json_data=event_data
        )
        
        if not self._is_success(response.status_code):
            self._handle_error_response(response)
        
        updated_event = response.json()
        
        return APIResponse(
            success=True,
            data={
                "event": self._format_event(updated_event),
                "event_id": updated_event.get("id"),
                "html_link": updated_event.get("htmlLink"),
                "calendar_id": calendar_id,
            },
            status_code=200,
        )

    async def _handle_event_delete(
        self, access_token: str, parameters: Dict[str, Any]
    ) -> APIResponse:
        """Handle delete event operation."""
        calendar_id = parameters.get("calendar_id", "primary")
        event_id = parameters.get("event_id")
        
        if not event_id:
            return APIResponse(
                success=False,
                error="event_id is required",
                status_code=400,
            )
        
        url = f"{self.base_url}/calendars/{calendar_id}/events/{event_id}"
        headers = self._prepare_headers(access_token)
        
        # Add send notifications parameter if specified
        if parameters.get("send_notifications"):
            url += "?sendNotifications=true"
        
        response = await self.make_http_request("DELETE", url, headers=headers)
        
        if not self._is_success(response.status_code):
            self._handle_error_response(response)
        
        return APIResponse(
            success=True,
            data={
                "deleted": True,
                "event_id": event_id,
                "calendar_id": calendar_id,
            },
            status_code=204,
        )

    async def _handle_event_search(
        self, access_token: str, parameters: Dict[str, Any]
    ) -> APIResponse:
        """Handle search events operation."""
        query = parameters.get("query", "")
        calendars = parameters.get("calendars", ["primary"])
        
        if isinstance(calendars, str):
            calendars = [calendars]
        
        all_events = []
        
        # Search across specified calendars
        for calendar_id in calendars:
            query_params = {
                "q": query,
                "singleEvents": "true",
                "orderBy": "startTime",
            }
            
            # Add time range if specified
            if parameters.get("time_min"):
                query_params["timeMin"] = self._format_datetime(parameters["time_min"])
            if parameters.get("time_max"):
                query_params["timeMax"] = self._format_datetime(parameters["time_max"])
            
            # Limit results per calendar
            max_per_calendar = parameters.get("max_per_calendar", 100)
            query_params["maxResults"] = min(int(max_per_calendar), 250)
            
            url = f"{self.base_url}/calendars/{calendar_id}/events?{urlencode(query_params)}"
            headers = self._prepare_headers(access_token)
            
            try:
                response = await self.make_http_request("GET", url, headers=headers)
                
                if self._is_success(response.status_code):
                    data = response.json()
                    for event_data in data.get("items", []):
                        event = self._format_event(event_data)
                        event["calendar_id"] = calendar_id
                        all_events.append(event)
            except Exception as e:
                self.logger.warning(f"Failed to search calendar {calendar_id}: {e}")
                continue
        
        # Sort all events by start time
        all_events.sort(key=lambda x: x.get("start_time", ""))
        
        return APIResponse(
            success=True,
            data={
                "events": all_events,
                "total_count": len(all_events),
                "query": query,
                "calendars_searched": calendars,
            },
            status_code=200,
        )

    async def _handle_event_quick_add(
        self, access_token: str, parameters: Dict[str, Any]
    ) -> APIResponse:
        """Handle quick add event using natural language."""
        calendar_id = parameters.get("calendar_id", "primary")
        text = parameters.get("text")
        
        if not text:
            return APIResponse(
                success=False,
                error="text parameter is required for quick add",
                status_code=400,
            )
        
        url = f"{self.base_url}/calendars/{calendar_id}/events/quickAdd"
        query_params = {"text": text}
        
        if parameters.get("send_notifications"):
            query_params["sendNotifications"] = "true"
        
        url += f"?{urlencode(query_params)}"
        headers = self._prepare_headers(access_token)
        
        response = await self.make_http_request("POST", url, headers=headers)
        
        if not self._is_success(response.status_code):
            self._handle_error_response(response)
        
        created_event = response.json()
        
        return APIResponse(
            success=True,
            data={
                "event": self._format_event(created_event),
                "event_id": created_event.get("id"),
                "html_link": created_event.get("htmlLink"),
                "calendar_id": calendar_id,
                "original_text": text,
            },
            status_code=201,
        )

    async def _handle_calendar_list(
        self, access_token: str, parameters: Dict[str, Any]
    ) -> APIResponse:
        """Handle list calendars operation."""
        query_params = {}
        
        if parameters.get("min_access_role"):
            query_params["minAccessRole"] = parameters["min_access_role"]
        
        if parameters.get("show_hidden"):
            query_params["showHidden"] = "true"
        
        if parameters.get("show_deleted"):
            query_params["showDeleted"] = "true"
        
        url = f"{self.base_url}/users/me/calendarList"
        if query_params:
            url += f"?{urlencode(query_params)}"
        
        headers = self._prepare_headers(access_token)
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not self._is_success(response.status_code):
            self._handle_error_response(response)
        
        data = response.json()
        
        calendars = []
        for cal_data in data.get("items", []):
            calendars.append({
                "id": cal_data.get("id"),
                "summary": cal_data.get("summary"),
                "description": cal_data.get("description"),
                "time_zone": cal_data.get("timeZone"),
                "access_role": cal_data.get("accessRole"),
                "primary": cal_data.get("primary", False),
                "selected": cal_data.get("selected", False),
                "background_color": cal_data.get("backgroundColor"),
                "foreground_color": cal_data.get("foregroundColor"),
            })
        
        return APIResponse(
            success=True,
            data={
                "calendars": calendars,
                "total_count": len(calendars),
            },
            status_code=200,
        )

    async def _handle_calendar_get(
        self, access_token: str, parameters: Dict[str, Any]
    ) -> APIResponse:
        """Handle get calendar operation."""
        calendar_id = parameters.get("calendar_id", "primary")
        
        url = f"{self.base_url}/calendars/{calendar_id}"
        headers = self._prepare_headers(access_token)
        
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not self._is_success(response.status_code):
            self._handle_error_response(response)
        
        cal_data = response.json()
        
        return APIResponse(
            success=True,
            data={
                "calendar": {
                    "id": cal_data.get("id"),
                    "summary": cal_data.get("summary"),
                    "description": cal_data.get("description"),
                    "time_zone": cal_data.get("timeZone"),
                    "location": cal_data.get("location"),
                }
            },
            status_code=200,
        )

    async def _handle_calendar_create(
        self, access_token: str, parameters: Dict[str, Any]
    ) -> APIResponse:
        """Handle create calendar operation."""
        if not parameters.get("summary"):
            return APIResponse(
                success=False,
                error="Calendar summary is required",
                status_code=400,
            )
        
        calendar_data = {
            "summary": parameters["summary"],
        }
        
        if parameters.get("description"):
            calendar_data["description"] = parameters["description"]
        
        if parameters.get("time_zone"):
            calendar_data["timeZone"] = parameters["time_zone"]
        
        if parameters.get("location"):
            calendar_data["location"] = parameters["location"]
        
        url = f"{self.base_url}/calendars"
        headers = self._prepare_headers(access_token)
        
        response = await self.make_http_request(
            "POST", url, headers=headers, json_data=calendar_data
        )
        
        if not self._is_success(response.status_code):
            self._handle_error_response(response)
        
        created_calendar = response.json()
        
        return APIResponse(
            success=True,
            data={
                "calendar": {
                    "id": created_calendar.get("id"),
                    "summary": created_calendar.get("summary"),
                    "description": created_calendar.get("description"),
                    "time_zone": created_calendar.get("timeZone"),
                }
            },
            status_code=201,
        )

    async def _handle_calendar_update(
        self, access_token: str, parameters: Dict[str, Any]
    ) -> APIResponse:
        """Handle update calendar operation."""
        calendar_id = parameters.get("calendar_id")
        
        if not calendar_id:
            return APIResponse(
                success=False,
                error="calendar_id is required",
                status_code=400,
            )
        
        # Get existing calendar
        url = f"{self.base_url}/calendars/{calendar_id}"
        headers = self._prepare_headers(access_token)
        
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not self._is_success(response.status_code):
            self._handle_error_response(response)
        
        calendar_data = response.json()
        
        # Update fields
        if "summary" in parameters:
            calendar_data["summary"] = parameters["summary"]
        
        if "description" in parameters:
            calendar_data["description"] = parameters["description"]
        
        if "time_zone" in parameters:
            calendar_data["timeZone"] = parameters["time_zone"]
        
        if "location" in parameters:
            calendar_data["location"] = parameters["location"]
        
        # Make update request
        response = await self.make_http_request(
            "PUT", url, headers=headers, json_data=calendar_data
        )
        
        if not self._is_success(response.status_code):
            self._handle_error_response(response)
        
        updated_calendar = response.json()
        
        return APIResponse(
            success=True,
            data={
                "calendar": {
                    "id": updated_calendar.get("id"),
                    "summary": updated_calendar.get("summary"),
                    "description": updated_calendar.get("description"),
                    "time_zone": updated_calendar.get("timeZone"),
                }
            },
            status_code=200,
        )

    async def _handle_calendar_delete(
        self, access_token: str, parameters: Dict[str, Any]
    ) -> APIResponse:
        """Handle delete calendar operation."""
        calendar_id = parameters.get("calendar_id")
        
        if not calendar_id:
            return APIResponse(
                success=False,
                error="calendar_id is required",
                status_code=400,
            )
        
        if calendar_id == "primary":
            return APIResponse(
                success=False,
                error="Cannot delete primary calendar",
                status_code=400,
            )
        
        url = f"{self.base_url}/calendars/{calendar_id}"
        headers = self._prepare_headers(access_token)
        
        response = await self.make_http_request("DELETE", url, headers=headers)
        
        if not self._is_success(response.status_code):
            self._handle_error_response(response)
        
        return APIResponse(
            success=True,
            data={
                "deleted": True,
                "calendar_id": calendar_id,
            },
            status_code=204,
        )

    async def _handle_event_instances(
        self, access_token: str, parameters: Dict[str, Any]
    ) -> APIResponse:
        """Handle get recurring event instances."""
        calendar_id = parameters.get("calendar_id", "primary")
        event_id = parameters.get("event_id")
        
        if not event_id:
            return APIResponse(
                success=False,
                error="event_id is required for getting instances",
                status_code=400,
            )
        
        query_params = {}
        
        if parameters.get("time_min"):
            query_params["timeMin"] = self._format_datetime(parameters["time_min"])
        
        if parameters.get("time_max"):
            query_params["timeMax"] = self._format_datetime(parameters["time_max"])
        
        if parameters.get("max_results"):
            query_params["maxResults"] = min(int(parameters["max_results"]), 250)
        
        url = f"{self.base_url}/calendars/{calendar_id}/events/{event_id}/instances"
        if query_params:
            url += f"?{urlencode(query_params)}"
        
        headers = self._prepare_headers(access_token)
        response = await self.make_http_request("GET", url, headers=headers)
        
        if not self._is_success(response.status_code):
            self._handle_error_response(response)
        
        data = response.json()
        
        instances = []
        for instance_data in data.get("items", []):
            instances.append(self._format_event(instance_data))
        
        return APIResponse(
            success=True,
            data={
                "instances": instances,
                "total_count": len(instances),
                "recurring_event_id": event_id,
                "calendar_id": calendar_id,
            },
            status_code=200,
        )

    async def _handle_event_move(
        self, access_token: str, parameters: Dict[str, Any]
    ) -> APIResponse:
        """Handle move event to another calendar."""
        source_calendar_id = parameters.get("source_calendar_id", "primary")
        destination_calendar_id = parameters.get("destination_calendar_id")
        event_id = parameters.get("event_id")
        
        if not event_id:
            return APIResponse(
                success=False,
                error="event_id is required",
                status_code=400,
            )
        
        if not destination_calendar_id:
            return APIResponse(
                success=False,
                error="destination_calendar_id is required",
                status_code=400,
            )
        
        url = f"{self.base_url}/calendars/{source_calendar_id}/events/{event_id}/move"
        query_params = {"destination": destination_calendar_id}
        
        if parameters.get("send_notifications"):
            query_params["sendNotifications"] = "true"
        
        url += f"?{urlencode(query_params)}"
        headers = self._prepare_headers(access_token)
        
        response = await self.make_http_request("POST", url, headers=headers)
        
        if not self._is_success(response.status_code):
            self._handle_error_response(response)
        
        moved_event = response.json()
        
        return APIResponse(
            success=True,
            data={
                "event": self._format_event(moved_event),
                "event_id": moved_event.get("id"),
                "source_calendar": source_calendar_id,
                "destination_calendar": destination_calendar_id,
            },
            status_code=200,
        )

    async def _handle_freebusy_query(
        self, access_token: str, parameters: Dict[str, Any]
    ) -> APIResponse:
        """Handle query free/busy information."""
        calendars = parameters.get("calendars", ["primary"])
        
        if isinstance(calendars, str):
            calendars = [calendars]
        
        time_min = parameters.get("time_min")
        time_max = parameters.get("time_max")
        
        if not time_min or not time_max:
            return APIResponse(
                success=False,
                error="time_min and time_max are required for free/busy query",
                status_code=400,
            )
        
        request_data = {
            "timeMin": self._format_datetime(time_min),
            "timeMax": self._format_datetime(time_max),
            "items": [{"id": cal_id} for cal_id in calendars],
        }
        
        if parameters.get("time_zone"):
            request_data["timeZone"] = parameters["time_zone"]
        
        url = f"{self.base_url}/freeBusy"
        headers = self._prepare_headers(access_token)
        
        response = await self.make_http_request(
            "POST", url, headers=headers, json_data=request_data
        )
        
        if not self._is_success(response.status_code):
            self._handle_error_response(response)
        
        data = response.json()
        
        # Format free/busy data
        calendars_freebusy = {}
        for cal_id, cal_data in data.get("calendars", {}).items():
            busy_times = []
            for busy in cal_data.get("busy", []):
                busy_times.append({
                    "start": busy.get("start"),
                    "end": busy.get("end"),
                })
            
            calendars_freebusy[cal_id] = {
                "busy": busy_times,
                "errors": cal_data.get("errors"),
            }
        
        return APIResponse(
            success=True,
            data={
                "calendars": calendars_freebusy,
                "time_min": time_min,
                "time_max": time_max,
            },
            status_code=200,
        )

    async def _handle_watch_events(
        self, access_token: str, parameters: Dict[str, Any]
    ) -> APIResponse:
        """Handle set up webhook for event changes."""
        calendar_id = parameters.get("calendar_id", "primary")
        webhook_url = parameters.get("webhook_url")
        
        if not webhook_url:
            return APIResponse(
                success=False,
                error="webhook_url is required for watching events",
                status_code=400,
            )
        
        # Generate unique channel ID
        channel_id = parameters.get("channel_id", f"channel-{datetime.now().timestamp()}")
        
        request_data = {
            "id": channel_id,
            "type": "web_hook",
            "address": webhook_url,
        }
        
        # Add optional parameters
        if parameters.get("token"):
            request_data["token"] = parameters["token"]
        
        if parameters.get("expiration"):
            request_data["expiration"] = str(int(parameters["expiration"]))
        
        url = f"{self.base_url}/calendars/{calendar_id}/events/watch"
        headers = self._prepare_headers(access_token)
        
        response = await self.make_http_request(
            "POST", url, headers=headers, json_data=request_data
        )
        
        if not self._is_success(response.status_code):
            self._handle_error_response(response)
        
        watch_data = response.json()
        
        return APIResponse(
            success=True,
            data={
                "channel_id": watch_data.get("id"),
                "resource_id": watch_data.get("resourceId"),
                "resource_uri": watch_data.get("resourceUri"),
                "expiration": watch_data.get("expiration"),
                "calendar_id": calendar_id,
            },
            status_code=201,
        )

    async def _handle_stop_watching(
        self, access_token: str, parameters: Dict[str, Any]
    ) -> APIResponse:
        """Handle stop webhook monitoring."""
        channel_id = parameters.get("channel_id")
        resource_id = parameters.get("resource_id")
        
        if not channel_id or not resource_id:
            return APIResponse(
                success=False,
                error="channel_id and resource_id are required to stop watching",
                status_code=400,
            )
        
        request_data = {
            "id": channel_id,
            "resourceId": resource_id,
        }
        
        url = f"{self.base_url}/channels/stop"
        headers = self._prepare_headers(access_token)
        
        response = await self.make_http_request(
            "POST", url, headers=headers, json_data=request_data
        )
        
        if not self._is_success(response.status_code):
            self._handle_error_response(response)
        
        return APIResponse(
            success=True,
            data={
                "stopped": True,
                "channel_id": channel_id,
                "resource_id": resource_id,
            },
            status_code=204,
        )

    def _prepare_headers(self, access_token: str) -> Dict[str, str]:
        """Prepare headers for Google Calendar API requests."""
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _is_success(self, status_code: int) -> bool:
        """Check if status code indicates success."""
        return 200 <= status_code < 300

    def _handle_error_response(self, response) -> None:
        """Handle error responses from Google Calendar API."""
        status_code = response.status_code
        
        try:
            error_data = response.json()
            error_message = error_data.get("error", {}).get("message", "Unknown error")
        except:
            error_message = response.text or f"HTTP {status_code}"
        
        if status_code == 401:
            raise GoogleCalendarAuthError(f"Authentication failed: {error_message}")
        elif status_code == 403:
            raise GoogleCalendarPermissionError(f"Permission denied: {error_message}")
        elif status_code == 404:
            raise GoogleCalendarNotFoundError(f"Resource not found: {error_message}")
        elif status_code == 429:
            raise GoogleCalendarRateLimitError(f"Rate limit exceeded: {error_message}")
        elif 400 <= status_code < 500:
            raise GoogleCalendarValidationError(f"Validation error: {error_message}")
        elif 500 <= status_code < 600:
            raise GoogleCalendarError(f"Server error: {error_message}")
        else:
            raise GoogleCalendarError(f"Unexpected error: {error_message}")

    def _format_datetime(self, dt_input) -> str:
        """Format datetime for Google Calendar API."""
        if dt_input is None:
            return None
        
        if isinstance(dt_input, str):
            # Already formatted
            return dt_input
        elif isinstance(dt_input, datetime):
            # Ensure timezone aware
            if dt_input.tzinfo is None:
                dt_input = dt_input.replace(tzinfo=timezone.utc)
            return dt_input.isoformat()
        else:
            # Try to convert
            try:
                dt = datetime.fromisoformat(str(dt_input))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.isoformat()
            except:
                return str(dt_input)

    def _format_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format event data for consistent response."""
        formatted = {
            "id": event_data.get("id"),
            "summary": event_data.get("summary", ""),
            "description": event_data.get("description", ""),
            "location": event_data.get("location", ""),
            "status": event_data.get("status", "confirmed"),
            "html_link": event_data.get("htmlLink"),
            "created": event_data.get("created"),
            "updated": event_data.get("updated"),
        }
        
        # Handle start/end times
        start = event_data.get("start", {})
        end = event_data.get("end", {})
        
        if "dateTime" in start:
            formatted["start_time"] = start["dateTime"]
            formatted["all_day"] = False
        elif "date" in start:
            formatted["start_time"] = start["date"]
            formatted["all_day"] = True
        
        if "dateTime" in end:
            formatted["end_time"] = end["dateTime"]
        elif "date" in end:
            formatted["end_time"] = end["date"]
        
        # Handle attendees
        if event_data.get("attendees"):
            formatted["attendees"] = [
                {
                    "email": att.get("email"),
                    "display_name": att.get("displayName"),
                    "response_status": att.get("responseStatus"),
                    "organizer": att.get("organizer", False),
                }
                for att in event_data["attendees"]
            ]
        
        # Handle organizer
        if event_data.get("organizer"):
            formatted["organizer"] = {
                "email": event_data["organizer"].get("email"),
                "display_name": event_data["organizer"].get("displayName"),
            }
        
        # Handle recurrence
        if event_data.get("recurrence"):
            formatted["recurrence"] = event_data["recurrence"]
            formatted["recurring"] = True
        else:
            formatted["recurring"] = False
        
        # Handle reminders
        if event_data.get("reminders"):
            formatted["reminders"] = event_data["reminders"]
        
        # Handle conference data
        if event_data.get("conferenceData"):
            conf_data = event_data["conferenceData"]
            formatted["conference"] = {
                "type": conf_data.get("conferenceSolution", {}).get("name"),
                "entry_points": conf_data.get("entryPoints", []),
            }
        
        return formatted