"""
Google Calendar API client for workflow integrations.

This module provides a comprehensive client for Google Calendar API v3,
supporting full CRUD operations on calendar events with proper error
handling, authentication, and data validation.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from workflow_engine.clients.base_client import BaseAPIClient, PaginatedResponse
from workflow_engine.models.credential import OAuth2Credential


logger = logging.getLogger(__name__)


class GoogleCalendarError(Exception):
    """Google Calendar specific error."""
    pass


class CalendarNotFoundError(GoogleCalendarError):
    """Raised when specified calendar is not found."""
    pass


class EventNotFoundError(GoogleCalendarError):
    """Raised when specified event is not found."""
    pass


class GoogleCalendarClient(BaseAPIClient):
    """
    Google Calendar API v3 client.
    
    Provides full CRUD operations for calendar events with support for
    multiple calendars, time zone handling, and automatic token refresh.
    """
    
    def __init__(self, credentials: OAuth2Credential):
        """Initialize Google Calendar client."""
        if not credentials:
            raise ValueError("Google Calendar credentials are required")
        super().__init__(credentials)
    
    def _get_base_url(self) -> str:
        """Get Google Calendar API base URL."""
        return "https://www.googleapis.com/calendar/v3"
    
    def _get_service_name(self) -> str:
        """Get service name for logging."""
        return "Google Calendar"
    
    async def list_calendars(self) -> List[Dict[str, Any]]:
        """
        List available calendars for the authenticated user.
        
        Returns:
            List of calendar objects with id, summary, description, etc.
            
        Raises:
            GoogleCalendarError: If the request fails
        """
        try:
            response = await self._make_request("GET", "/users/me/calendarList")
            return response.get("items", [])
        except Exception as e:
            logger.error(f"Failed to list calendars: {e}")
            raise GoogleCalendarError(f"Failed to list calendars: {e}")
    
    async def create_event(
        self, 
        calendar_id: str, 
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new calendar event.
        
        Args:
            calendar_id: Calendar ID (use "primary" for primary calendar)
            event_data: Event data following Google Calendar API format:
                {
                    "summary": "Event title",
                    "description": "Event description",
                    "start": {
                        "dateTime": "2025-01-20T10:00:00Z",
                        "timeZone": "UTC"
                    },
                    "end": {
                        "dateTime": "2025-01-20T11:00:00Z", 
                        "timeZone": "UTC"
                    },
                    "attendees": [
                        {"email": "attendee@example.com"}
                    ],
                    "location": "Meeting Room 1"
                }
                
        Returns:
            Created event data with ID, URL, etc.
            
        Raises:
            GoogleCalendarError: If event creation fails
            CalendarNotFoundError: If calendar doesn't exist
        """
        # Validate required fields
        self._validate_event_data(event_data)
        
        try:
            endpoint = f"/calendars/{quote(calendar_id)}/events"
            response = await self._make_request("POST", endpoint, json=event_data)
            
            logger.info(f"Created event '{response.get('summary')}' in calendar {calendar_id}")
            return response
            
        except Exception as e:
            if "notFound" in str(e):
                raise CalendarNotFoundError(f"Calendar '{calendar_id}' not found")
            logger.error(f"Failed to create event: {e}")
            raise GoogleCalendarError(f"Failed to create event: {e}")
    
    async def list_events(
        self,
        calendar_id: str,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        max_results: int = 250,
        single_events: bool = True,
        order_by: str = "startTime",
        page_token: Optional[str] = None
    ) -> PaginatedResponse:
        """
        List events from a calendar within a time range.
        
        Args:
            calendar_id: Calendar ID (use "primary" for primary calendar)
            time_min: Lower bound (ISO 8601) for events to be returned
            time_max: Upper bound (ISO 8601) for events to be returned  
            max_results: Maximum number of events returned (1-2500)
            single_events: Whether to expand recurring events
            order_by: Order of events ("startTime" or "updated")
            page_token: Token for pagination
            
        Returns:
            PaginatedResponse with events and pagination info
            
        Raises:
            GoogleCalendarError: If listing fails
            CalendarNotFoundError: If calendar doesn't exist
        """
        try:
            # Build query parameters
            params = {
                "maxResults": min(max_results, 2500),
                "singleEvents": single_events,
                "orderBy": order_by
            }
            
            if time_min:
                params["timeMin"] = self._normalize_datetime(time_min)
            if time_max:
                params["timeMax"] = self._normalize_datetime(time_max)
            if page_token:
                params["pageToken"] = page_token
            
            endpoint = f"/calendars/{quote(calendar_id)}/events"
            response = await self._make_request("GET", endpoint, params=params)
            
            events = response.get("items", [])
            next_page_token = response.get("nextPageToken")
            
            logger.info(f"Listed {len(events)} events from calendar {calendar_id}")
            return PaginatedResponse(events, next_page_token)
            
        except Exception as e:
            if "notFound" in str(e):
                raise CalendarNotFoundError(f"Calendar '{calendar_id}' not found")
            logger.error(f"Failed to list events: {e}")
            raise GoogleCalendarError(f"Failed to list events: {e}")
    
    async def get_event(
        self, 
        calendar_id: str, 
        event_id: str
    ) -> Dict[str, Any]:
        """
        Get a specific event by ID.
        
        Args:
            calendar_id: Calendar ID
            event_id: Event ID
            
        Returns:
            Event data
            
        Raises:
            EventNotFoundError: If event doesn't exist
            GoogleCalendarError: If request fails
        """
        try:
            endpoint = f"/calendars/{quote(calendar_id)}/events/{quote(event_id)}"
            response = await self._make_request("GET", endpoint)
            
            logger.info(f"Retrieved event {event_id} from calendar {calendar_id}")
            return response
            
        except Exception as e:
            if "notFound" in str(e):
                raise EventNotFoundError(f"Event '{event_id}' not found in calendar '{calendar_id}'")
            logger.error(f"Failed to get event: {e}")
            raise GoogleCalendarError(f"Failed to get event: {e}")
    
    async def update_event(
        self,
        calendar_id: str,
        event_id: str,
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an existing calendar event.
        
        Args:
            calendar_id: Calendar ID
            event_id: Event ID to update
            event_data: Updated event data (same format as create_event)
            
        Returns:
            Updated event data
            
        Raises:
            EventNotFoundError: If event doesn't exist
            GoogleCalendarError: If update fails
        """
        # Validate event data
        self._validate_event_data(event_data, is_update=True)
        
        try:
            endpoint = f"/calendars/{quote(calendar_id)}/events/{quote(event_id)}"
            response = await self._make_request("PUT", endpoint, json=event_data)
            
            logger.info(f"Updated event {event_id} in calendar {calendar_id}")
            return response
            
        except Exception as e:
            if "notFound" in str(e):
                raise EventNotFoundError(f"Event '{event_id}' not found in calendar '{calendar_id}'")
            logger.error(f"Failed to update event: {e}")
            raise GoogleCalendarError(f"Failed to update event: {e}")
    
    async def delete_event(
        self,
        calendar_id: str,
        event_id: str
    ) -> bool:
        """
        Delete a calendar event.
        
        Args:
            calendar_id: Calendar ID
            event_id: Event ID to delete
            
        Returns:
            True if deletion was successful
            
        Raises:
            EventNotFoundError: If event doesn't exist
            GoogleCalendarError: If deletion fails
        """
        try:
            endpoint = f"/calendars/{quote(calendar_id)}/events/{quote(event_id)}"
            await self._make_request("DELETE", endpoint)
            
            logger.info(f"Deleted event {event_id} from calendar {calendar_id}")
            return True
            
        except Exception as e:
            if "notFound" in str(e):
                raise EventNotFoundError(f"Event '{event_id}' not found in calendar '{calendar_id}'")
            logger.error(f"Failed to delete event: {e}")
            raise GoogleCalendarError(f"Failed to delete event: {e}")
    
    def _validate_event_data(self, event_data: Dict[str, Any], is_update: bool = False):
        """
        Validate event data structure.
        
        Args:
            event_data: Event data to validate
            is_update: Whether this is for an update operation
            
        Raises:
            ValueError: If event data is invalid
        """
        if not isinstance(event_data, dict):
            raise ValueError("Event data must be a dictionary")
        
        # For updates, only validate provided fields
        if not is_update:
            # Required fields for new events
            if not event_data.get("summary"):
                raise ValueError("Event summary is required")
            
            if "start" not in event_data:
                raise ValueError("Event start time is required")
            
            if "end" not in event_data:
                raise ValueError("Event end time is required")
        
        # Validate start/end time format if provided
        for time_field in ["start", "end"]:
            if time_field in event_data:
                time_data = event_data[time_field]
                if not isinstance(time_data, dict):
                    raise ValueError(f"Event {time_field} must be an object")
                
                # Must have either dateTime or date
                if "dateTime" not in time_data and "date" not in time_data:
                    raise ValueError(f"Event {time_field} must have either 'dateTime' or 'date'")
        
        # Validate attendees format if provided
        if "attendees" in event_data:
            attendees = event_data["attendees"]
            if not isinstance(attendees, list):
                raise ValueError("Event attendees must be a list")
            
            for attendee in attendees:
                if not isinstance(attendee, dict) or "email" not in attendee:
                    raise ValueError("Each attendee must have an email field")
    
    def _normalize_datetime(self, dt_string: str) -> str:
        """
        Normalize datetime string to RFC3339 format.
        
        Args:
            dt_string: Datetime string in various formats
            
        Returns:
            RFC3339 formatted datetime string
        """
        try:
            # Handle various datetime formats
            if "T" in dt_string and dt_string.endswith("Z"):
                return dt_string  # Already in RFC3339 format
            
            # Try to parse and convert to RFC3339
            if "T" in dt_string:
                dt = datetime.fromisoformat(dt_string.replace("Z", "+00:00"))
            else:
                dt = datetime.fromisoformat(dt_string)
            
            # Convert to UTC if no timezone info
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=None)
                return dt.isoformat() + "Z"
            else:
                return dt.isoformat()
                
        except ValueError:
            # Return as-is if parsing fails
            return dt_string
    
    async def quick_add_event(
        self,
        calendar_id: str,
        text: str
    ) -> Dict[str, Any]:
        """
        Create an event using Google's Quick Add feature.
        
        Args:
            calendar_id: Calendar ID
            text: Natural language event description
                  e.g., "Meeting with John tomorrow 2pm"
                  
        Returns:
            Created event data
            
        Raises:
            GoogleCalendarError: If quick add fails
        """
        try:
            endpoint = f"/calendars/{quote(calendar_id)}/events/quickAdd"
            params = {"text": text}
            response = await self._make_request("POST", endpoint, params=params)
            
            logger.info(f"Quick added event: {text}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to quick add event: {e}")
            raise GoogleCalendarError(f"Failed to quick add event: {e}")
    
    async def get_free_busy(
        self,
        calendar_ids: List[str],
        time_min: str,
        time_max: str
    ) -> Dict[str, Any]:
        """
        Get free/busy information for calendars.
        
        Args:
            calendar_ids: List of calendar IDs to check
            time_min: Start time (ISO 8601)
            time_max: End time (ISO 8601)
            
        Returns:
            Free/busy data for each calendar
            
        Raises:
            GoogleCalendarError: If request fails
        """
        try:
            data = {
                "timeMin": self._normalize_datetime(time_min),
                "timeMax": self._normalize_datetime(time_max),
                "items": [{"id": cal_id} for cal_id in calendar_ids]
            }
            
            response = await self._make_request("POST", "/freeBusy", json=data)
            
            logger.info(f"Retrieved free/busy for {len(calendar_ids)} calendars")
            return response
            
        except Exception as e:
            logger.error(f"Failed to get free/busy: {e}")
            raise GoogleCalendarError(f"Failed to get free/busy: {e}") 