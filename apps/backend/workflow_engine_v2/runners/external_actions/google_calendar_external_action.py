"""
Google Calendar external action for workflow_engine_v2.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

import httpx

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models import ExecutionStatus, NodeExecutionResult
from workflow_engine_v2.core.context import NodeExecutionContext

from .base_external_action import BaseExternalAction


class GoogleCalendarExternalAction(BaseExternalAction):
    """Google Calendar external action handler for workflow_engine_v2."""

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
        calendar_id = context.node.configurations.get("calendar_id", "primary")

        # Get event details
        summary = (
            context.input_data.get("title")
            or context.input_data.get("summary")
            or context.node.configurations.get("summary")
            or context.node.configurations.get("title")
            or "Workflow Generated Event"
        )
        description = (
            context.input_data.get("description")
            or context.input_data.get("message")
            or context.node.configurations.get("description")
            or context.node.configurations.get("body")
            or "This event was created by a workflow automation."
        )

        # Get start and end times
        start_time = context.input_data.get("start_time") or context.node.configurations.get(
            "start_time"
        )
        end_time = context.input_data.get("end_time") or context.node.configurations.get("end_time")
        duration_minutes = context.node.configurations.get("duration_minutes", 60)

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

        # Create event payload
        event = {
            "summary": summary,
            "description": description,
            "start": {
                "dateTime": start_time,
                "timeZone": context.node.configurations.get("timezone", "UTC"),
            },
            "end": {
                "dateTime": end_time,
                "timeZone": context.node.configurations.get("timezone", "UTC"),
            },
        }

        # Add attendees if specified
        attendees = context.node.configurations.get("attendees", [])
        if attendees:
            event["attendees"] = [{"email": email} for email in attendees]

        # Add location if specified
        location = context.node.configurations.get("location")
        if location:
            event["location"] = location

        self.log_execution(context, f"Creating Google Calendar event: {summary}")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
                headers=headers,
                json=event,
                timeout=30.0,
            )

        if response.status_code == 200:
            result = response.json()
            self.log_execution(context, f"✅ Google Calendar event created successfully")

            return self.create_success_result(
                "create_event",
                {
                    "event_id": result.get("id"),
                    "event_url": result.get("htmlLink"),
                    "summary": result.get("summary"),
                    "description": result.get("description"),
                    "start": result.get("start"),
                    "end": result.get("end"),
                    "location": result.get("location"),
                    "attendees": result.get("attendees", []),
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
        calendar_id = context.node.configurations.get("calendar_id", "primary")
        max_results = context.node.configurations.get("max_results", 10)
        time_min = context.node.configurations.get("time_min")
        time_max = context.node.configurations.get("time_max")

        # Default to next 30 days if no time range specified
        if not time_min:
            time_min = datetime.now().isoformat() + "Z"
        if not time_max:
            time_max = (datetime.now() + timedelta(days=30)).isoformat() + "Z"

        params = {
            "timeMin": time_min,
            "timeMax": time_max,
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime",
        }

        self.log_execution(context, f"Listing Google Calendar events from {calendar_id}")

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

            events_data = []
            for event in events:
                events_data.append(
                    {
                        "id": event.get("id"),
                        "summary": event.get("summary"),
                        "description": event.get("description"),
                        "start": event.get("start"),
                        "end": event.get("end"),
                        "location": event.get("location"),
                        "html_link": event.get("htmlLink"),
                        "attendees": event.get("attendees", []),
                    }
                )

            return self.create_success_result(
                "list_events",
                {
                    "events_count": len(events_data),
                    "events": events_data,
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

    async def _list_calendars(
        self, context: NodeExecutionContext, headers: dict
    ) -> NodeExecutionResult:
        """List Google calendars."""
        self.log_execution(context, "Listing Google calendars")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/calendar/v3/users/me/calendarList",
                headers=headers,
                timeout=30.0,
            )

        if response.status_code == 200:
            result = response.json()
            calendars = result.get("items", [])
            self.log_execution(context, f"✅ Retrieved {len(calendars)} Google calendars")

            calendars_data = []
            for calendar in calendars:
                calendars_data.append(
                    {
                        "id": calendar.get("id"),
                        "summary": calendar.get("summary"),
                        "description": calendar.get("description"),
                        "primary": calendar.get("primary", False),
                        "access_role": calendar.get("accessRole"),
                        "time_zone": calendar.get("timeZone"),
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
        calendar_id = context.node.configurations.get("calendar_id", "primary")
        event_id = context.input_data.get("event_id") or context.node.configurations.get("event_id")

        if not event_id:
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message="Google Calendar update event requires 'event_id' parameter",
                error_details={"operation": "update_event", "missing": ["event_id"]},
            )

        # Get event details to update
        update_data = {}

        if "summary" in context.input_data or "summary" in context.node.configurations:
            update_data["summary"] = context.input_data.get(
                "summary"
            ) or context.node.configurations.get("summary")

        if "description" in context.input_data or "description" in context.node.configurations:
            update_data["description"] = context.input_data.get(
                "description"
            ) or context.node.configurations.get("description")

        if not update_data:
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message="No update data provided (summary, description, etc.)",
                error_details={"operation": "update_event", "event_id": event_id},
            )

        self.log_execution(context, f"Updating Google Calendar event: {event_id}")

        async with httpx.AsyncClient() as client:
            # First get the existing event
            get_response = await client.get(
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}",
                headers=headers,
                timeout=30.0,
            )

            if get_response.status_code != 200:
                error = f"Failed to get existing event: {get_response.status_code} - {get_response.text}"
                self.log_execution(context, f"❌ {error}", "ERROR")
                return NodeExecutionResult(
                    status=ExecutionStatus.ERROR,
                    error_message=error,
                    error_details={"status_code": get_response.status_code},
                )

            # Update the event with new data
            existing_event = get_response.json()
            existing_event.update(update_data)

            # Send the update
            update_response = await client.put(
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}",
                headers=headers,
                json=existing_event,
                timeout=30.0,
            )

        if update_response.status_code == 200:
            result = update_response.json()
            self.log_execution(context, f"✅ Google Calendar event updated successfully")

            return self.create_success_result(
                "update_event",
                {
                    "event_id": result.get("id"),
                    "event_url": result.get("htmlLink"),
                    "summary": result.get("summary"),
                    "description": result.get("description"),
                    "updated": result.get("updated"),
                },
            )
        else:
            error = (
                f"Google Calendar API error: {update_response.status_code} - {update_response.text}"
            )
            self.log_execution(context, f"❌ {error}", "ERROR")
            return NodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=error,
                error_details={
                    "status_code": update_response.status_code,
                    "response": update_response.text,
                },
            )


__all__ = ["GoogleCalendarExternalAction"]
