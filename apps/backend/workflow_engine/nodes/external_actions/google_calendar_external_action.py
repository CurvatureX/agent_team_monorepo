"""
Google Calendar external action for external actions.
"""

from datetime import datetime, timedelta
from typing import Any, Dict

import httpx

from nodes.base import ExecutionStatus, NodeExecutionContext, NodeExecutionResult

from .base_external_action import BaseExternalAction


class GoogleCalendarExternalAction(BaseExternalAction):
    """Google Calendar external action handler."""

    def __init__(self):
        super().__init__("google")

    async def handle_operation(
        self, context: NodeExecutionContext, operation: str
    ) -> NodeExecutionResult:
        """Handle Google Calendar-specific operations."""
        try:
            # Get Google OAuth token from oauth_tokens table
            google_token = await self.get_oauth_token(context)

            if not google_token:
                error_msg = "❌ No Google authentication token found. Please connect your Google account in integrations settings."
                self.log_execution(context, error_msg, "ERROR")
                return self.create_error_result(error_msg, operation)

            # Prepare headers with OAuth token
            headers = {
                "Authorization": f"Bearer {google_token}",
                "Content-Type": "application/json",
            }

            # Handle different Google Calendar operations
            if operation.lower() in ["create_event", "create-event"]:
                return await self._create_event(context, headers)
            elif operation.lower() in ["list_events", "list-events"]:
                return await self._list_events(context, headers)
            elif operation.lower() in ["get_calendars", "list_calendars"]:
                return await self._list_calendars(context, headers)
            elif operation.lower() in ["update_event", "update-event"]:
                return await self._update_event(context, headers)
            else:
                # Default: list events from primary calendar
                return await self._list_events(context, headers)

        except Exception as e:
            self.log_execution(context, f"Google Calendar action failed: {str(e)}", "ERROR")
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=f"Google Calendar action failed: {str(e)}",
                error_details={"integration_type": "google_calendar", "operation": operation},
            )

    async def _create_event(
        self, context: NodeExecutionContext, headers: dict
    ) -> NodeExecutionResult:
        """Create a Google Calendar event."""
        # Get calendar ID (default to primary)
        calendar_id = context.get_parameter("calendar_id", "primary")

        # Get event details
        summary = (
            context.get_parameter("summary")
            or context.get_parameter("title")
            or context.input_data.get("title")
            or context.input_data.get("summary")
            or "Workflow Generated Event"
        )
        description = (
            context.get_parameter("description")
            or context.get_parameter("body")
            or context.input_data.get("message")
            or context.input_data.get("description")
            or "This event was created by a workflow automation."
        )

        # Get start and end times
        start_time = context.get_parameter("start_time")
        end_time = context.get_parameter("end_time")
        duration_minutes = context.get_parameter("duration_minutes", 60)

        # If no start time provided, default to 1 hour from now
        if not start_time:
            start_datetime = datetime.now() + timedelta(hours=1)
            start_time = start_datetime.isoformat()

        # If no end time provided, calculate from start + duration
        if not end_time:
            if start_time:
                start_datetime = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                end_datetime = start_datetime + timedelta(minutes=duration_minutes)
                end_time = end_datetime.isoformat()

        payload = {
            "summary": summary,
            "description": description,
            "start": {
                "dateTime": start_time,
                "timeZone": context.get_parameter("timezone", "UTC"),
            },
            "end": {
                "dateTime": end_time,
                "timeZone": context.get_parameter("timezone", "UTC"),
            },
        }

        # Add attendees if provided
        attendees = context.get_parameter("attendees", [])
        if attendees:
            if isinstance(attendees, str):
                # Single email string
                payload["attendees"] = [{"email": attendees}]
            elif isinstance(attendees, list):
                # List of emails
                payload["attendees"] = [{"email": email} for email in attendees]

        # Add location if provided
        location = context.get_parameter("location")
        if location:
            payload["location"] = location

        self.log_execution(context, f"Creating Google Calendar event: {summary}")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
                headers=headers,
                json=payload,
                timeout=30.0,
            )

        if response.status_code == 200:
            result = response.json()
            self.log_execution(
                context, f"✅ Google Calendar event created successfully: {result.get('id')}"
            )

            return self.create_success_result(
                "create_event",
                {
                    "event_id": result.get("id"),
                    "event_url": result.get("htmlLink"),
                    "summary": result.get("summary"),
                    "description": result.get("description"),
                    "start_time": result.get("start", {}).get("dateTime"),
                    "end_time": result.get("end", {}).get("dateTime"),
                    "location": result.get("location"),
                    "attendees": [
                        attendee.get("email") for attendee in result.get("attendees", [])
                    ],
                    "calendar_id": calendar_id,
                },
            )
        else:
            error = f"Google Calendar API error: {response.status_code} - {response.text}"
            self.log_execution(context, f"❌ {error}", "ERROR")
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=error,
                error_details={"status_code": response.status_code, "response": response.text},
            )

    async def _list_events(
        self, context: NodeExecutionContext, headers: dict
    ) -> NodeExecutionResult:
        """List Google Calendar events."""
        # Get calendar ID (default to primary)
        calendar_id = context.get_parameter("calendar_id", "primary")

        # Get time range parameters
        max_results = context.get_parameter("max_results", 10)
        days_ahead = context.get_parameter("days_ahead", 7)

        # Set time bounds (upcoming events only)
        time_min = datetime.now().isoformat() + "Z"
        time_max = (datetime.now() + timedelta(days=days_ahead)).isoformat() + "Z"

        params = {
            "timeMin": time_min,
            "timeMax": time_max,
            "maxResults": min(max_results, 250),  # Google API max is 2500, but keep reasonable
            "singleEvents": "true",
            "orderBy": "startTime",
        }

        self.log_execution(context, f"Listing Google Calendar events for next {days_ahead} days")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
                headers=headers,
                params=params,
                timeout=30.0,
            )

        if response.status_code == 200:
            result = response.json()
            events = result.get("items", [])
            self.log_execution(context, f"✅ Retrieved {len(events)} Google Calendar events")

            # Process events data
            events_data = []
            for event in events:
                start_time = event.get("start", {})
                end_time = event.get("end", {})

                events_data.append(
                    {
                        "id": event.get("id"),
                        "summary": event.get("summary", "No title"),
                        "description": event.get("description", "")[:200],  # Truncate description
                        "start_time": start_time.get("dateTime") or start_time.get("date"),
                        "end_time": end_time.get("dateTime") or end_time.get("date"),
                        "location": event.get("location"),
                        "url": event.get("htmlLink"),
                        "attendees": [
                            attendee.get("email") for attendee in event.get("attendees", [])
                        ],
                        "created": event.get("created"),
                    }
                )

            return self.create_success_result(
                "list_events",
                {
                    "events_count": len(events_data),
                    "events": events_data,
                    "calendar_id": calendar_id,
                    "time_range_days": days_ahead,
                },
            )
        else:
            error = f"Google Calendar API error: {response.status_code} - {response.text}"
            self.log_execution(context, f"❌ {error}", "ERROR")
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=error,
                error_details={"status_code": response.status_code, "response": response.text},
            )

    async def _list_calendars(
        self, context: NodeExecutionContext, headers: dict
    ) -> NodeExecutionResult:
        """List Google Calendars."""
        self.log_execution(context, "Listing Google Calendars")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/calendar/v3/users/me/calendarList",
                headers=headers,
                timeout=30.0,
            )

        if response.status_code == 200:
            result = response.json()
            calendars = result.get("items", [])
            self.log_execution(context, f"✅ Retrieved {len(calendars)} Google Calendars")

            # Process calendars data
            calendars_data = []
            for calendar in calendars:
                calendars_data.append(
                    {
                        "id": calendar.get("id"),
                        "summary": calendar.get("summary"),
                        "description": calendar.get("description"),
                        "primary": calendar.get("primary", False),
                        "access_role": calendar.get("accessRole"),
                        "background_color": calendar.get("backgroundColor"),
                        "foreground_color": calendar.get("foregroundColor"),
                    }
                )

            return self.create_success_result(
                "list_calendars",
                {
                    "calendars_count": len(calendars_data),
                    "calendars": calendars_data,
                },
            )
        else:
            error = f"Google Calendar API error: {response.status_code} - {response.text}"
            self.log_execution(context, f"❌ {error}", "ERROR")
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=error,
                error_details={"status_code": response.status_code, "response": response.text},
            )

    async def _update_event(
        self, context: NodeExecutionContext, headers: dict
    ) -> NodeExecutionResult:
        """Update a Google Calendar event."""
        # Get calendar and event IDs
        calendar_id = context.get_parameter("calendar_id", "primary")
        event_id = context.get_parameter("event_id")

        if not event_id:
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message="Google Calendar update event requires 'event_id' parameter",
                error_details={"operation": "update_event", "missing": ["event_id"]},
            )

        # Build update payload with only provided fields
        payload = {}

        summary = context.get_parameter("summary") or context.get_parameter("title")
        if summary:
            payload["summary"] = summary

        description = context.get_parameter("description") or context.get_parameter("body")
        if description:
            payload["description"] = description

        location = context.get_parameter("location")
        if location:
            payload["location"] = location

        start_time = context.get_parameter("start_time")
        if start_time:
            payload["start"] = {
                "dateTime": start_time,
                "timeZone": context.get_parameter("timezone", "UTC"),
            }

        end_time = context.get_parameter("end_time")
        if end_time:
            payload["end"] = {
                "dateTime": end_time,
                "timeZone": context.get_parameter("timezone", "UTC"),
            }

        if not payload:
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message="No update fields provided for Google Calendar event",
                error_details={
                    "operation": "update_event",
                    "available_fields": [
                        "summary",
                        "description",
                        "location",
                        "start_time",
                        "end_time",
                    ],
                },
            )

        self.log_execution(context, f"Updating Google Calendar event: {event_id}")

        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}",
                headers=headers,
                json=payload,
                timeout=30.0,
            )

        if response.status_code == 200:
            result = response.json()
            self.log_execution(context, f"✅ Google Calendar event updated successfully: {event_id}")

            return self.create_success_result(
                "update_event",
                {
                    "event_id": result.get("id"),
                    "event_url": result.get("htmlLink"),
                    "summary": result.get("summary"),
                    "description": result.get("description"),
                    "start_time": result.get("start", {}).get("dateTime"),
                    "end_time": result.get("end", {}).get("dateTime"),
                    "location": result.get("location"),
                    "updated_fields": list(payload.keys()),
                },
            )
        else:
            error = f"Google Calendar API error: {response.status_code} - {response.text}"
            self.log_execution(context, f"❌ {error}", "ERROR")
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=error,
                error_details={"status_code": response.status_code, "response": response.text},
            )
