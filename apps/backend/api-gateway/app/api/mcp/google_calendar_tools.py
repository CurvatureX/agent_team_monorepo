"""
Google Calendar MCP API - Comprehensive calendar management tools
支持OpenAI、Claude和Gemini的Google Calendar MCP集成
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.models import MCPContentItem, MCPHealthCheck, MCPInvokeResponse, MCPTool, MCPToolsResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)


class GoogleCalendarMCPService:
    """Comprehensive MCP service for Google Calendar operations optimized for all LLMs."""

    def __init__(self):
        # No global client - use per-request OAuth tokens
        pass

    def get_available_tools(self) -> MCPToolsResponse:
        """Get available Google Calendar tools optimized for OpenAI, Claude, and Gemini."""
        tools = [
            MCPTool(
                name="google_calendar_events",
                description="Universal calendar event management (list, create, update, delete) with smart natural language support for all LLMs",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "access_token": {
                            "type": "string",
                            "description": "Google Calendar OAuth access token",
                        },
                        "action": {
                            "type": "string",
                            "enum": ["list", "create", "update", "delete", "get"],
                            "description": "Action to perform on calendar events",
                        },
                        "calendar_id": {
                            "type": "string",
                            "default": "primary",
                            "description": "Calendar ID (default: primary calendar)",
                        },
                        "event_id": {
                            "type": "string",
                            "description": "Event ID (required for get/update/delete actions)",
                        },
                        # Smart event creation with natural language support
                        "event_data": {
                            "type": "object",
                            "properties": {
                                "summary": {
                                    "type": "string",
                                    "description": "Event title/summary",
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Event description/details",
                                },
                                "location": {
                                    "type": "string",
                                    "description": "Event location (address, meeting room, virtual link)",
                                },
                                "start_datetime": {
                                    "type": "string",
                                    "description": "Start time in ISO format (e.g., '2024-01-15T14:00:00Z') or natural language",
                                },
                                "end_datetime": {
                                    "type": "string",
                                    "description": "End time in ISO format (e.g., '2024-01-15T15:00:00Z') or natural language",
                                },
                                "all_day": {
                                    "type": "boolean",
                                    "default": False,
                                    "description": "Whether this is an all-day event",
                                },
                                "attendees": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "List of attendee email addresses",
                                },
                                "reminders": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "method": {
                                                "type": "string",
                                                "enum": ["email", "popup"],
                                            },
                                            "minutes": {
                                                "type": "integer",
                                                "description": "Minutes before event",
                                            },
                                        },
                                    },
                                    "description": "Event reminders",
                                },
                                "recurrence": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Recurrence rules (RRULE format)",
                                },
                                "timezone": {
                                    "type": "string",
                                    "default": "UTC",
                                    "description": "Event timezone",
                                },
                            },
                            "description": "Event details for create/update actions",
                        },
                        # Smart filtering for list action
                        "filters": {
                            "type": "object",
                            "properties": {
                                "time_min": {
                                    "type": "string",
                                    "description": "Start time filter (ISO format or natural language like 'today', 'next week')",
                                },
                                "time_max": {
                                    "type": "string",
                                    "description": "End time filter (ISO format or natural language)",
                                },
                                "query": {
                                    "type": "string",
                                    "description": "Search query for event title/description",
                                },
                                "max_results": {
                                    "type": "integer",
                                    "default": 10,
                                    "minimum": 1,
                                    "maximum": 250,
                                    "description": "Maximum number of events to return",
                                },
                                "order_by": {
                                    "type": "string",
                                    "enum": ["startTime", "updated"],
                                    "default": "startTime",
                                    "description": "How to order the results",
                                },
                                "single_events": {
                                    "type": "boolean",
                                    "default": True,
                                    "description": "Expand recurring events into instances",
                                },
                            },
                            "description": "Filtering options for list action",
                        },
                        "include_content": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include full event details in response",
                        },
                    },
                    "required": ["access_token", "action"],
                },
                category="google_calendar",
                tags=["events", "calendar", "scheduling", "crud"],
            ),
            MCPTool(
                name="google_calendar_quick_add",
                description="Smart natural language event creation optimized for LLM workflows - just describe the event naturally",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "access_token": {
                            "type": "string",
                            "description": "Google Calendar OAuth access token",
                        },
                        "text": {
                            "type": "string",
                            "description": "Natural language event description (e.g., 'Meeting with John tomorrow at 2pm for 1 hour')",
                        },
                        "calendar_id": {
                            "type": "string",
                            "default": "primary",
                            "description": "Calendar ID to add event to",
                        },
                        "send_notifications": {
                            "type": "boolean",
                            "default": True,
                            "description": "Send notifications to attendees",
                        },
                    },
                    "required": ["access_token", "text"],
                },
                category="google_calendar",
                tags=["quick-add", "natural-language", "ai-friendly"],
            ),
            MCPTool(
                name="google_calendar_search",
                description="Advanced calendar search with smart filtering for finding events across time periods",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "access_token": {
                            "type": "string",
                            "description": "Google Calendar OAuth access token",
                        },
                        "query": {
                            "type": "string",
                            "description": "Search query text (searches titles, descriptions, locations)",
                        },
                        "calendar_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific calendars to search (default: all accessible calendars)",
                        },
                        "time_range": {
                            "type": "object",
                            "properties": {
                                "start": {
                                    "type": "string",
                                    "description": "Search start time (ISO format or natural language)",
                                },
                                "end": {
                                    "type": "string",
                                    "description": "Search end time (ISO format or natural language)",
                                },
                                "preset": {
                                    "type": "string",
                                    "enum": [
                                        "today",
                                        "tomorrow",
                                        "yesterday",
                                        "this_week",
                                        "next_week",
                                        "last_week",
                                        "this_month",
                                        "next_month",
                                        "last_month",
                                        "this_quarter",
                                        "next_quarter",
                                        "this_year",
                                        "next_year",
                                    ],
                                    "description": "Preset time range for convenient date-based queries",
                                },
                            },
                            "description": "Time range for search",
                        },
                        "max_results": {
                            "type": "integer",
                            "default": 20,
                            "minimum": 1,
                            "maximum": 100,
                            "description": "Maximum events to return",
                        },
                        "include_details": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include full event details in results",
                        },
                    },
                    "required": ["access_token", "query"],
                },
                category="google_calendar",
                tags=["search", "filter", "find-events"],
            ),
            MCPTool(
                name="google_calendar_availability",
                description="Smart availability checking and free/busy time analysis for scheduling optimization",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "access_token": {
                            "type": "string",
                            "description": "Google Calendar OAuth access token",
                        },
                        "calendars": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Calendar IDs to check (default: primary calendar)",
                        },
                        "time_range": {
                            "type": "object",
                            "properties": {
                                "start": {
                                    "type": "string",
                                    "description": "Check start time (ISO format or natural language)",
                                },
                                "end": {
                                    "type": "string",
                                    "description": "Check end time (ISO format or natural language)",
                                },
                                "duration_minutes": {
                                    "type": "integer",
                                    "description": "Meeting duration in minutes (for finding free slots)",
                                },
                            },
                            "required": ["start", "end"],
                            "description": "Time range to check availability",
                        },
                        "find_free_slots": {
                            "type": "boolean",
                            "default": False,
                            "description": "Find available free time slots",
                        },
                        "business_hours_only": {
                            "type": "boolean",
                            "default": False,
                            "description": "Only consider business hours (9 AM - 5 PM)",
                        },
                        "timezone": {
                            "type": "string",
                            "default": "UTC",
                            "description": "Timezone for the check",
                        },
                    },
                    "required": ["access_token", "time_range"],
                },
                category="google_calendar",
                tags=["availability", "free-busy", "scheduling"],
            ),
            MCPTool(
                name="google_calendar_date_query",
                description="Advanced date-based calendar queries with flexible natural language date parsing and smart filtering",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "access_token": {
                            "type": "string",
                            "description": "Google Calendar OAuth access token",
                        },
                        "date_query": {
                            "type": "string",
                            "description": "Natural language date query (e.g., 'events next Tuesday', 'meetings last week', 'appointments in March 2024')",
                        },
                        "date_range": {
                            "type": "object",
                            "properties": {
                                "start_date": {
                                    "type": "string",
                                    "description": "Start date (YYYY-MM-DD, ISO format, or natural language like 'next Monday')",
                                },
                                "end_date": {
                                    "type": "string",
                                    "description": "End date (YYYY-MM-DD, ISO format, or natural language)",
                                },
                                "duration": {
                                    "type": "string",
                                    "enum": ["day", "week", "month", "quarter", "year"],
                                    "description": "Duration from start_date (alternative to end_date)",
                                },
                                "relative": {
                                    "type": "string",
                                    "enum": ["past", "future", "current"],
                                    "description": "Time direction relative to now",
                                },
                            },
                            "description": "Structured date range specification",
                        },
                        "filters": {
                            "type": "object",
                            "properties": {
                                "event_type": {
                                    "type": "string",
                                    "enum": [
                                        "meeting",
                                        "appointment",
                                        "reminder",
                                        "all-day",
                                        "recurring",
                                        "single",
                                    ],
                                    "description": "Filter by event type characteristics",
                                },
                                "attendee_count": {
                                    "type": "object",
                                    "properties": {
                                        "min": {
                                            "type": "integer",
                                            "description": "Minimum attendees",
                                        },
                                        "max": {
                                            "type": "integer",
                                            "description": "Maximum attendees",
                                        },
                                    },
                                    "description": "Filter by number of attendees",
                                },
                                "duration_minutes": {
                                    "type": "object",
                                    "properties": {
                                        "min": {
                                            "type": "integer",
                                            "description": "Minimum duration",
                                        },
                                        "max": {
                                            "type": "integer",
                                            "description": "Maximum duration",
                                        },
                                    },
                                    "description": "Filter by event duration",
                                },
                                "keywords": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Keywords to search in title/description",
                                },
                                "exclude_keywords": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Keywords to exclude from results",
                                },
                                "organizer": {
                                    "type": "string",
                                    "description": "Filter by event organizer email",
                                },
                                "status": {
                                    "type": "string",
                                    "enum": ["confirmed", "tentative", "cancelled"],
                                    "description": "Filter by event status",
                                },
                            },
                            "description": "Advanced filtering options",
                        },
                        "group_by": {
                            "type": "string",
                            "enum": [
                                "date",
                                "week",
                                "month",
                                "organizer",
                                "duration",
                                "attendee_count",
                            ],
                            "description": "Group results by specified criteria",
                        },
                        "sort_by": {
                            "type": "string",
                            "enum": [
                                "start_time",
                                "duration",
                                "attendee_count",
                                "created_time",
                                "updated_time",
                            ],
                            "default": "start_time",
                            "description": "Sort results by specified field",
                        },
                        "sort_order": {
                            "type": "string",
                            "enum": ["asc", "desc"],
                            "default": "asc",
                            "description": "Sort order (ascending or descending)",
                        },
                        "max_results": {
                            "type": "integer",
                            "default": 50,
                            "minimum": 1,
                            "maximum": 500,
                            "description": "Maximum events to return",
                        },
                        "include_analytics": {
                            "type": "boolean",
                            "default": False,
                            "description": "Include analytical summary (total time, meeting patterns, etc.)",
                        },
                        "ai_format": {
                            "type": "string",
                            "enum": ["structured", "narrative", "summary"],
                            "default": "structured",
                            "description": "AI-optimized output format",
                        },
                    },
                    "required": ["access_token"],
                    "oneOf": [{"required": ["date_query"]}, {"required": ["date_range"]}],
                },
                category="google_calendar",
                tags=["date-query", "advanced-search", "analytics", "natural-language"],
            ),
        ]

        return MCPToolsResponse(
            tools=tools,
            total_count=len(tools),
            available_count=len(tools),
            categories=["google_calendar"],
        )

    async def invoke_tool(self, tool_name: str, params: Dict[str, Any]) -> MCPInvokeResponse:
        """Invoke specified Google Calendar tool with comprehensive error handling."""
        start_time = time.time()

        # Extract access token from parameters
        access_token = params.get("access_token")
        if not access_token:
            response = MCPInvokeResponse(
                content=[
                    MCPContentItem(
                        type="text",
                        text="Error: access_token parameter is required for Google Calendar tools.",
                    )
                ],
                isError=True,
            )
            response._tool_name = tool_name
            response._execution_time_ms = round((time.time() - start_time) * 1000, 2)
            return response

        try:
            if tool_name == "google_calendar_events":
                result = await self._handle_events(params)
            elif tool_name == "google_calendar_quick_add":
                result = await self._handle_quick_add(params)
            elif tool_name == "google_calendar_search":
                result = await self._handle_search(params)
            elif tool_name == "google_calendar_availability":
                result = await self._handle_availability(params)
            elif tool_name == "google_calendar_date_query":
                result = await self._handle_date_query(params)
            else:
                response = MCPInvokeResponse(
                    content=[
                        MCPContentItem(type="text", text=f"Error: Tool '{tool_name}' not found")
                    ],
                    isError=True,
                )
                response._tool_name = tool_name
                response._execution_time_ms = round((time.time() - start_time) * 1000, 2)
                return response

            # Convert result to MCP-compliant content format
            content = [
                MCPContentItem(type="text", text=f"Tool '{tool_name}' executed successfully")
            ]

            response = MCPInvokeResponse(content=content, isError=False, structuredContent=result)
            response._tool_name = tool_name
            response._execution_time_ms = round((time.time() - start_time) * 1000, 2)
            return response

        except Exception as e:
            error_msg = f"Google Calendar tool execution failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            response = MCPInvokeResponse(
                content=[MCPContentItem(type="text", text=error_msg)],
                isError=True,
            )
            response._tool_name = tool_name
            response._execution_time_ms = round((time.time() - start_time) * 1000, 2)
            return response

    async def _handle_events(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle universal event management operations."""
        from app.services.google_calendar_client import GoogleCalendarClient

        action = params.get("action")
        access_token = params.get("access_token")
        calendar_id = params.get("calendar_id", "primary")

        # Create client with user's token
        client = GoogleCalendarClient(access_token=access_token)

        try:
            if action == "list":
                filters = params.get("filters", {})

                # Parse natural language time filters
                time_min = self._parse_time_input(filters.get("time_min"))
                time_max = self._parse_time_input(filters.get("time_max"))

                list_params = {
                    "calendar_id": calendar_id,
                    "time_min": time_min,
                    "time_max": time_max,
                    "max_results": filters.get("max_results", 10),
                    "single_events": filters.get("single_events", True),
                    "order_by": filters.get("order_by", "startTime"),
                    "q": filters.get("query"),
                }

                # Remove None values
                list_params = {k: v for k, v in list_params.items() if v is not None}

                result = await client.list_events(**list_params)

                # Enhanced formatting for LLMs
                events = result.get("events", [])
                formatted_events = []

                for event in events:
                    formatted_event = self._format_event_for_llm(event)
                    formatted_events.append(formatted_event)

                return {
                    "action": "list",
                    "calendar_id": calendar_id,
                    "events": formatted_events,
                    "total_count": len(formatted_events),
                    "has_more": result.get("has_more", False),
                    "filters_applied": filters,
                }

            elif action == "create":
                event_data = params.get("event_data", {})

                # Smart event creation with natural language parsing
                create_params = await self._prepare_event_data(event_data)
                create_params["calendar_id"] = calendar_id

                result = await client.create_event(**create_params)

                return {
                    "action": "create",
                    "calendar_id": calendar_id,
                    "event": self._format_event_for_llm(result.get("event", {})),
                    "event_id": result.get("event_id"),
                    "html_link": result.get("html_link"),
                }

            elif action == "update":
                event_id = params.get("event_id")
                if not event_id:
                    raise ValueError("event_id is required for update action")

                event_data = params.get("event_data", {})
                update_params = await self._prepare_event_data(event_data)
                update_params["calendar_id"] = calendar_id
                update_params["event_id"] = event_id

                result = await client.update_event(**update_params)

                return {
                    "action": "update",
                    "calendar_id": calendar_id,
                    "event_id": event_id,
                    "event": self._format_event_for_llm(result.get("event", {})),
                    "updated_fields": result.get("updated_fields", []),
                }

            elif action == "delete":
                event_id = params.get("event_id")
                if not event_id:
                    raise ValueError("event_id is required for delete action")

                result = await client.delete_event(calendar_id=calendar_id, event_id=event_id)

                return {
                    "action": "delete",
                    "calendar_id": calendar_id,
                    "event_id": event_id,
                    "success": result.get("success", False),
                    "message": result.get("message", ""),
                }

            elif action == "get":
                event_id = params.get("event_id")
                if not event_id:
                    raise ValueError("event_id is required for get action")

                result = await client.get_event(calendar_id=calendar_id, event_id=event_id)

                return {
                    "action": "get",
                    "calendar_id": calendar_id,
                    "event_id": event_id,
                    "event": self._format_event_for_llm(result.get("event", {})),
                }

            else:
                raise ValueError(f"Unknown action: {action}")

        finally:
            await client.close()

    async def _handle_quick_add(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle natural language event creation."""
        from app.services.google_calendar_client import GoogleCalendarClient

        access_token = params.get("access_token")
        text = params.get("text")
        calendar_id = params.get("calendar_id", "primary")
        send_notifications = params.get("send_notifications", True)

        if not text:
            raise ValueError("text parameter is required for quick add")

        client = GoogleCalendarClient(access_token=access_token)

        try:
            result = await client.quick_add_event(
                calendar_id=calendar_id, text=text, send_notifications=send_notifications
            )

            return {
                "action": "quick_add",
                "calendar_id": calendar_id,
                "parsed_text": text,
                "event": self._format_event_for_llm(result.get("event", {})),
                "event_id": result.get("event_id"),
                "html_link": result.get("html_link"),
            }

        finally:
            await client.close()

    async def _handle_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle advanced calendar search."""
        from app.services.google_calendar_client import GoogleCalendarClient

        access_token = params.get("access_token")
        query = params.get("query")
        calendar_ids = params.get("calendar_ids", ["primary"])
        time_range = params.get("time_range", {})
        max_results = params.get("max_results", 20)
        include_details = params.get("include_details", True)

        if not query:
            raise ValueError("query parameter is required for search")

        client = GoogleCalendarClient(access_token=access_token)

        try:
            # Parse time range
            if time_range.get("preset"):
                time_min, time_max = self._parse_preset_time_range(time_range["preset"])
            else:
                time_min = self._parse_time_input(time_range.get("start"))
                time_max = self._parse_time_input(time_range.get("end"))

            all_events = []

            # Search across specified calendars
            for calendar_id in calendar_ids:
                search_params = {
                    "calendar_id": calendar_id,
                    "q": query,
                    "time_min": time_min,
                    "time_max": time_max,
                    "max_results": max_results,
                    "single_events": True,
                    "order_by": "startTime",
                }

                # Remove None values
                search_params = {k: v for k, v in search_params.items() if v is not None}

                result = await client.search_events(**search_params)
                events = result.get("events", [])

                for event in events:
                    event["source_calendar"] = calendar_id
                    all_events.append(event)

            # Sort all events by start time
            all_events.sort(
                key=lambda e: e.get("start", {}).get("dateTime", e.get("start", {}).get("date", ""))
            )

            # Limit results
            all_events = all_events[:max_results]

            # Format for LLMs
            formatted_events = []
            for event in all_events:
                formatted_event = self._format_event_for_llm(event)
                formatted_events.append(formatted_event)

            return {
                "action": "search",
                "query": query,
                "calendars_searched": calendar_ids,
                "time_range": time_range,
                "events": formatted_events,
                "total_found": len(formatted_events),
            }

        finally:
            await client.close()

    async def _handle_availability(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle availability checking and free slot finding."""
        from app.services.google_calendar_client import GoogleCalendarClient

        access_token = params.get("access_token")
        calendars = params.get("calendars", ["primary"])
        time_range = params.get("time_range", {})
        find_free_slots = params.get("find_free_slots", False)
        business_hours_only = params.get("business_hours_only", False)
        timezone_str = params.get("timezone", "UTC")

        # Parse time range
        start_time = self._parse_time_input(time_range.get("start"))
        end_time = self._parse_time_input(time_range.get("end"))
        duration_minutes = time_range.get("duration_minutes", 60)

        if not start_time or not end_time:
            raise ValueError("start and end times are required for availability check")

        client = GoogleCalendarClient(access_token=access_token)

        try:
            # Get events for all calendars in the time range
            all_events = []

            for calendar_id in calendars:
                result = await client.list_events(
                    calendar_id=calendar_id,
                    time_min=start_time,
                    time_max=end_time,
                    single_events=True,
                    order_by="startTime",
                )

                events = result.get("events", [])
                for event in events:
                    event["source_calendar"] = calendar_id
                    all_events.append(event)

            # Analyze availability
            busy_times = []
            for event in all_events:
                # Skip all-day events or events without specific times
                start = event.get("start", {})
                end = event.get("end", {})

                if "dateTime" in start and "dateTime" in end:
                    busy_times.append(
                        {
                            "start": start["dateTime"],
                            "end": end["dateTime"],
                            "event_title": event.get("summary", "Busy"),
                            "calendar": event.get("source_calendar"),
                        }
                    )

            result = {
                "action": "availability",
                "calendars_checked": calendars,
                "time_range": {
                    "start": start_time,
                    "end": end_time,
                },
                "busy_times": busy_times,
                "total_busy_periods": len(busy_times),
            }

            # Find free slots if requested
            if find_free_slots:
                free_slots = self._find_free_slots(
                    start_time,
                    end_time,
                    busy_times,
                    duration_minutes,
                    business_hours_only,
                    timezone_str,
                )
                result["free_slots"] = free_slots
                result["available_slots_count"] = len(free_slots)

            return result

        finally:
            await client.close()

    async def _handle_date_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle advanced date-based calendar queries with natural language support."""
        from app.services.google_calendar_client import GoogleCalendarClient

        access_token = params.get("access_token")
        date_query = params.get("date_query")
        date_range = params.get("date_range", {})
        filters = params.get("filters", {})
        group_by = params.get("group_by")
        sort_by = params.get("sort_by", "start_time")
        sort_order = params.get("sort_order", "asc")
        max_results = params.get("max_results", 50)
        include_analytics = params.get("include_analytics", False)
        ai_format = params.get("ai_format", "structured")

        # Parse date range from either natural language query or structured input
        if date_query:
            start_time, end_time = self._parse_natural_date_query(date_query)
        else:
            start_time = self._parse_time_input(date_range.get("start_date"))
            end_time = self._parse_time_input(date_range.get("end_date"))

            # Handle duration-based end time
            if not end_time and date_range.get("duration") and start_time:
                end_time = self._calculate_end_time(start_time, date_range.get("duration"))

        if not start_time or not end_time:
            raise ValueError("Could not parse date range from query or parameters")

        client = GoogleCalendarClient(access_token=access_token)

        try:
            # Get events in the date range
            result = await client.list_events(
                calendar_id="primary",
                time_min=start_time,
                time_max=end_time,
                max_results=max_results,
                single_events=True,
                order_by="startTime",
            )

            events = result.get("events", [])

            # Apply advanced filters
            filtered_events = self._apply_advanced_filters(events, filters)

            # Sort events
            sorted_events = self._sort_events(filtered_events, sort_by, sort_order)

            # Format events for LLM consumption
            formatted_events = [self._format_event_for_llm(event) for event in sorted_events]

            # Group events if requested
            grouped_events = {}
            if group_by:
                grouped_events = self._group_events(formatted_events, group_by)

            # Calculate analytics if requested
            analytics = {}
            if include_analytics:
                analytics = self._calculate_analytics(formatted_events, start_time, end_time)

            result = {
                "action": "date_query",
                "date_query": date_query,
                "date_range": {
                    "start": start_time,
                    "end": end_time,
                },
                "total_events": len(formatted_events),
                "events": formatted_events,
                "grouped_events": grouped_events if group_by else None,
                "analytics": analytics if include_analytics else None,
                "filters_applied": filters,
                "sort_by": sort_by,
                "sort_order": sort_order,
            }

            # Apply AI formatting
            if ai_format == "narrative":
                return self._format_date_query_for_narrative(result)
            elif ai_format == "summary":
                return self._format_date_query_for_summary(result)
            else:
                return result

        finally:
            await client.close()

    def _parse_natural_date_query(self, query: str) -> tuple[str, str]:
        """Parse natural language date query into start and end times."""
        query_lower = query.lower()
        now = datetime.now(timezone.utc)

        # Common patterns
        if "today" in query_lower:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        elif "tomorrow" in query_lower:
            start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        elif "yesterday" in query_lower:
            start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        elif "this week" in query_lower:
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=7)
        elif "next week" in query_lower:
            start = now - timedelta(days=now.weekday()) + timedelta(days=7)
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=7)
        elif "last week" in query_lower:
            start = now - timedelta(days=now.weekday()) - timedelta(days=7)
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=7)
        elif "this month" in query_lower:
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            next_month = (
                start.replace(month=start.month + 1)
                if start.month < 12
                else start.replace(year=start.year + 1, month=1)
            )
            end = next_month
        else:
            # Default to today if can't parse
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)

        return start.isoformat(), end.isoformat()

    def _calculate_end_time(self, start_time: str, duration: str) -> str:
        """Calculate end time based on start time and duration."""
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))

        if duration == "day":
            end_dt = start_dt + timedelta(days=1)
        elif duration == "week":
            end_dt = start_dt + timedelta(weeks=1)
        elif duration == "month":
            end_dt = start_dt + timedelta(days=30)  # Approximate
        elif duration == "quarter":
            end_dt = start_dt + timedelta(days=90)  # Approximate
        elif duration == "year":
            end_dt = start_dt + timedelta(days=365)  # Approximate
        else:
            end_dt = start_dt + timedelta(days=1)  # Default to day

        return end_dt.isoformat()

    def _apply_advanced_filters(self, events: List[Dict], filters: Dict) -> List[Dict]:
        """Apply advanced filtering to events."""
        filtered = events

        # Filter by event type
        if filters.get("event_type"):
            event_type = filters["event_type"]
            if event_type == "all-day":
                filtered = [e for e in filtered if "date" in e.get("start", {})]
            elif event_type == "recurring":
                filtered = [e for e in filtered if e.get("recurringEventId")]
            elif event_type == "single":
                filtered = [e for e in filtered if not e.get("recurringEventId")]

        # Filter by attendee count
        if filters.get("attendee_count"):
            min_count = filters["attendee_count"].get("min", 0)
            max_count = filters["attendee_count"].get("max", 999)
            filtered = [
                e for e in filtered if min_count <= len(e.get("attendees", [])) <= max_count
            ]

        # Filter by keywords
        if filters.get("keywords"):
            keywords = [k.lower() for k in filters["keywords"]]
            filtered = [
                e
                for e in filtered
                if any(
                    keyword in (e.get("summary", "") + " " + e.get("description", "")).lower()
                    for keyword in keywords
                )
            ]

        # Filter by exclude keywords
        if filters.get("exclude_keywords"):
            exclude_keywords = [k.lower() for k in filters["exclude_keywords"]]
            filtered = [
                e
                for e in filtered
                if not any(
                    keyword in (e.get("summary", "") + " " + e.get("description", "")).lower()
                    for keyword in exclude_keywords
                )
            ]

        # Filter by organizer
        if filters.get("organizer"):
            organizer_email = filters["organizer"]
            filtered = [
                e for e in filtered if e.get("organizer", {}).get("email") == organizer_email
            ]

        # Filter by status
        if filters.get("status"):
            status = filters["status"]
            filtered = [e for e in filtered if e.get("status") == status]

        return filtered

    def _sort_events(self, events: List[Dict], sort_by: str, sort_order: str) -> List[Dict]:
        """Sort events by specified criteria."""
        reverse = sort_order == "desc"

        if sort_by == "start_time":
            return sorted(
                events,
                key=lambda e: e.get("start", {}).get(
                    "dateTime", e.get("start", {}).get("date", "")
                ),
                reverse=reverse,
            )
        elif sort_by == "duration":
            return sorted(events, key=lambda e: self._calculate_event_duration(e), reverse=reverse)
        elif sort_by == "attendee_count":
            return sorted(events, key=lambda e: len(e.get("attendees", [])), reverse=reverse)
        elif sort_by == "created_time":
            return sorted(events, key=lambda e: e.get("created", ""), reverse=reverse)
        elif sort_by == "updated_time":
            return sorted(events, key=lambda e: e.get("updated", ""), reverse=reverse)
        else:
            return events

    def _group_events(self, events: List[Dict], group_by: str) -> Dict[str, List[Dict]]:
        """Group events by specified criteria."""
        groups = {}

        for event in events:
            if group_by == "date":
                start_time = event.get("start_time", "")
                key = start_time[:10] if start_time else "unknown"
            elif group_by == "organizer":
                key = event.get("organizer", {}).get("email", "unknown")
            elif group_by == "duration":
                duration = self._calculate_event_duration(event)
                if duration <= 30:
                    key = "short (≤30min)"
                elif duration <= 60:
                    key = "medium (30-60min)"
                else:
                    key = "long (>60min)"
            elif group_by == "attendee_count":
                count = len(event.get("attendees", []))
                if count == 0:
                    key = "no attendees"
                elif count <= 2:
                    key = "small (1-2 people)"
                elif count <= 5:
                    key = "medium (3-5 people)"
                else:
                    key = "large (6+ people)"
            else:
                key = "other"

            if key not in groups:
                groups[key] = []
            groups[key].append(event)

        return groups

    def _calculate_analytics(
        self, events: List[Dict], start_time: str, end_time: str
    ) -> Dict[str, Any]:
        """Calculate analytical summary of events."""
        total_events = len(events)
        total_duration = sum(self._calculate_event_duration(event) for event in events)

        # Event types
        all_day_count = len([e for e in events if e.get("all_day")])
        recurring_count = len([e for e in events if "recurring" in str(e)])

        # Attendees analysis
        attendee_counts = [len(e.get("attendees", [])) for e in events]
        avg_attendees = sum(attendee_counts) / len(attendee_counts) if attendee_counts else 0

        # Time analysis
        avg_duration = total_duration / total_events if total_events > 0 else 0

        return {
            "total_events": total_events,
            "total_duration_minutes": total_duration,
            "average_duration_minutes": round(avg_duration, 1),
            "all_day_events": all_day_count,
            "recurring_events": recurring_count,
            "average_attendees": round(avg_attendees, 1),
            "time_period": {
                "start": start_time,
                "end": end_time,
                "duration_days": self._calculate_period_days(start_time, end_time),
            },
        }

    def _calculate_event_duration(self, event: Dict) -> int:
        """Calculate event duration in minutes."""
        start = event.get("start", {})
        end = event.get("end", {})

        if "dateTime" in start and "dateTime" in end:
            start_dt = datetime.fromisoformat(start["dateTime"].replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end["dateTime"].replace("Z", "+00:00"))
            return int((end_dt - start_dt).total_seconds() / 60)
        else:
            return 0  # All-day events or invalid times

    def _calculate_period_days(self, start_time: str, end_time: str) -> int:
        """Calculate number of days in the period."""
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        return (end_dt - start_dt).days

    def _format_date_query_for_narrative(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format date query results as narrative text."""
        events = result["events"]
        total_events = result["total_events"]
        analytics = result.get("analytics", {})

        narrative = f"I found {total_events} calendar events"

        if result.get("date_query"):
            narrative += f" for your query '{result['date_query']}'"

        date_start = result["date_range"]["start"][:10]
        date_end = result["date_range"]["end"][:10]
        narrative += f" from {date_start} to {date_end}:\n\n"

        # Add event details
        for i, event in enumerate(events[:10], 1):  # Show first 10
            title = event.get("title", "Untitled")
            start_time = event.get("start_time", "")
            duration = self._calculate_event_duration(event)

            narrative += f"{i}. **{title}**\n"
            if start_time:
                narrative += f"   🕐 {start_time[:16]} ({duration} min)\n"

            if event.get("location"):
                narrative += f"   📍 {event['location']}\n"

            attendees = event.get("attendees", [])
            if attendees:
                narrative += f"   👥 {len(attendees)} attendees\n"

            narrative += "\n"

        # Add analytics summary
        if analytics:
            narrative += f"\n📊 **Summary:**\n"
            narrative += (
                f"- Total time in meetings: {analytics.get('total_duration_minutes', 0)} minutes\n"
            )
            narrative += f"- Average meeting length: {analytics.get('average_duration_minutes', 0)} minutes\n"
            narrative += f"- Average attendees: {analytics.get('average_attendees', 0)}\n"

        return {**result, "ai_narrative": narrative, "format_type": "narrative"}

    def _format_date_query_for_summary(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format date query results as summary."""
        events = result["events"]
        analytics = result.get("analytics", {})

        summary = {
            "query_successful": len(events) > 0,
            "total_events_found": len(events),
            "date_range": result["date_range"],
            "filters_applied": bool(result.get("filters_applied")),
            "event_breakdown": {
                "all_day": len([e for e in events if e.get("all_day")]),
                "timed": len([e for e in events if not e.get("all_day")]),
                "with_attendees": len([e for e in events if e.get("attendees")]),
            },
            "top_events": [],
        }

        # Add top events
        for event in events[:5]:
            summary["top_events"].append(
                {
                    "title": event.get("title", "Untitled"),
                    "start_time": event.get("start_time"),
                    "duration_minutes": self._calculate_event_duration(event),
                    "attendee_count": len(event.get("attendees", [])),
                    "has_location": bool(event.get("location")),
                }
            )

        # Add analytics if available
        if analytics:
            summary["analytics"] = analytics

        return {**result, "ai_summary": summary, "format_type": "summary"}

    def _parse_time_input(self, time_input: Optional[str]) -> Optional[str]:
        """Parse natural language or ISO time input into Google Calendar format."""
        if not time_input:
            return None

        # If already in ISO format, return as-is
        if "T" in time_input and (
            "Z" in time_input or "+" in time_input or time_input.endswith(":00")
        ):
            return time_input

        # Handle natural language
        now = datetime.now(timezone.utc)

        if time_input.lower() in ["now", "today"]:
            return now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        elif time_input.lower() == "tomorrow":
            tomorrow = now + timedelta(days=1)
            return tomorrow.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        elif time_input.lower() == "yesterday":
            yesterday = now - timedelta(days=1)
            return yesterday.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        elif time_input.lower() in ["this week", "week"]:
            # Start of this week (Monday)
            days_since_monday = now.weekday()
            monday = now - timedelta(days=days_since_monday)
            return monday.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        elif time_input.lower() in ["next week"]:
            # Start of next week
            days_since_monday = now.weekday()
            next_monday = now + timedelta(days=7 - days_since_monday)
            return next_monday.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        elif time_input.lower() in ["this month", "month"]:
            # Start of this month
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        elif time_input.lower() in ["next month"]:
            # Start of next month
            if now.month == 12:
                next_month = now.replace(
                    year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0
                )
            else:
                next_month = now.replace(
                    month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0
                )
            return next_month.isoformat()

        # If we can't parse, return as-is and let Google Calendar handle it
        return time_input

    def _parse_preset_time_range(self, preset: str) -> tuple[str, str]:
        """Parse preset time ranges into start/end times."""
        now = datetime.now(timezone.utc)

        if preset == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        elif preset == "tomorrow":
            start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        elif preset == "this_week":
            days_since_monday = now.weekday()
            start = (now - timedelta(days=days_since_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            end = start + timedelta(days=7)
        elif preset == "next_week":
            days_since_monday = now.weekday()
            start = (now + timedelta(days=7 - days_since_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            end = start + timedelta(days=7)
        elif preset == "this_month":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if now.month == 12:
                end = start.replace(year=start.year + 1, month=1)
            else:
                end = start.replace(month=start.month + 1)
        elif preset == "next_month":
            if now.month == 12:
                start = now.replace(
                    year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0
                )
                end = start.replace(month=2)
            else:
                start = now.replace(
                    month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0
                )
                if start.month == 12:
                    end = start.replace(year=start.year + 1, month=1)
                else:
                    end = start.replace(month=start.month + 1)
        else:
            # Default to today
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)

        return start.isoformat(), end.isoformat()

    async def _prepare_event_data(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare event data for Google Calendar API with smart parsing."""
        prepared = {}

        if event_data.get("summary"):
            prepared["summary"] = event_data["summary"]

        if event_data.get("description"):
            prepared["description"] = event_data["description"]

        if event_data.get("location"):
            prepared["location"] = event_data["location"]

        # Handle time parsing
        if event_data.get("all_day"):
            # All-day event
            start_date = self._parse_date_only(event_data.get("start_datetime"))
            end_date = self._parse_date_only(
                event_data.get("end_datetime", event_data.get("start_datetime"))
            )
            prepared["start"] = {"date": start_date}
            prepared["end"] = {"date": end_date}
        else:
            # Timed event
            start_datetime = self._parse_time_input(event_data.get("start_datetime"))
            end_datetime = self._parse_time_input(event_data.get("end_datetime"))

            if start_datetime:
                prepared["start"] = {"dateTime": start_datetime}
            if end_datetime:
                prepared["end"] = {"dateTime": end_datetime}

        # Handle attendees
        if event_data.get("attendees"):
            prepared["attendees"] = [{"email": email} for email in event_data["attendees"]]

        # Handle reminders
        if event_data.get("reminders"):
            prepared["reminders"] = {"useDefault": False, "overrides": event_data["reminders"]}

        # Handle recurrence
        if event_data.get("recurrence"):
            prepared["recurrence"] = event_data["recurrence"]

        return prepared

    def _parse_date_only(self, date_input: Optional[str]) -> str:
        """Parse date input for all-day events."""
        if not date_input:
            return datetime.now(timezone.utc).date().isoformat()

        # Extract date part from datetime string
        if "T" in date_input:
            return date_input.split("T")[0]

        # Handle natural language
        parsed_time = self._parse_time_input(date_input)
        if parsed_time:
            return parsed_time.split("T")[0]

        return date_input

    def _format_event_for_llm(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Format event data for optimal LLM consumption."""
        formatted = {
            "id": event.get("id"),
            "title": event.get("summary", "No Title"),
            "description": event.get("description"),
            "location": event.get("location"),
            "html_link": event.get("htmlLink"),
            "calendar": event.get("source_calendar", "unknown"),
        }

        # Parse and format times
        start = event.get("start", {})
        end = event.get("end", {})

        if "dateTime" in start:
            # Timed event
            formatted["start_time"] = start["dateTime"]
            formatted["end_time"] = end.get("dateTime")
            formatted["all_day"] = False
            formatted["timezone"] = start.get("timeZone", "UTC")
        elif "date" in start:
            # All-day event
            formatted["date"] = start["date"]
            formatted["end_date"] = end.get("date")
            formatted["all_day"] = True

        # Attendees
        attendees = event.get("attendees", [])
        if attendees:
            formatted["attendees"] = [
                {
                    "email": attendee.get("email"),
                    "status": attendee.get("responseStatus"),
                    "organizer": attendee.get("organizer", False),
                }
                for attendee in attendees
            ]

        # Status and visibility
        formatted["status"] = event.get("status")
        formatted["created"] = event.get("created")
        formatted["updated"] = event.get("updated")

        return formatted

    def _find_free_slots(
        self,
        start_time: str,
        end_time: str,
        busy_times: List[Dict],
        duration_minutes: int,
        business_hours_only: bool,
        timezone_str: str,
    ) -> List[Dict]:
        """Find available free time slots."""
        from datetime import datetime, timedelta

        import pytz

        # Parse times
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))

        # Convert to specified timezone
        try:
            tz = pytz.timezone(timezone_str)
            start_dt = start_dt.astimezone(tz)
            end_dt = end_dt.astimezone(tz)
        except:
            # Fallback to UTC
            tz = pytz.UTC

        # Sort busy times
        busy_periods = []
        for busy in busy_times:
            busy_start = datetime.fromisoformat(busy["start"].replace("Z", "+00:00")).astimezone(tz)
            busy_end = datetime.fromisoformat(busy["end"].replace("Z", "+00:00")).astimezone(tz)
            busy_periods.append((busy_start, busy_end))

        busy_periods.sort()

        # Find free slots
        free_slots = []
        current_time = start_dt

        for busy_start, busy_end in busy_periods:
            # Check if there's a gap before this busy period
            if current_time < busy_start:
                gap_duration = (busy_start - current_time).total_seconds() / 60

                if gap_duration >= duration_minutes:
                    # Check business hours constraint
                    if not business_hours_only or self._is_business_hours(current_time, busy_start):
                        free_slots.append(
                            {
                                "start": current_time.isoformat(),
                                "end": busy_start.isoformat(),
                                "duration_minutes": gap_duration,
                                "can_fit_meeting": gap_duration >= duration_minutes,
                            }
                        )

            current_time = max(current_time, busy_end)

        # Check for time after last busy period
        if current_time < end_dt:
            gap_duration = (end_dt - current_time).total_seconds() / 60
            if gap_duration >= duration_minutes:
                if not business_hours_only or self._is_business_hours(current_time, end_dt):
                    free_slots.append(
                        {
                            "start": current_time.isoformat(),
                            "end": end_dt.isoformat(),
                            "duration_minutes": gap_duration,
                            "can_fit_meeting": gap_duration >= duration_minutes,
                        }
                    )

        return free_slots

    def _is_business_hours(self, start_dt: datetime, end_dt: datetime) -> bool:
        """Check if time period overlaps with business hours (9 AM - 5 PM)."""
        # Simple business hours check
        start_hour = start_dt.hour
        end_hour = end_dt.hour

        # Check if any part of the time period is within business hours
        return not (end_hour <= 9 or start_hour >= 17)

    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific Google Calendar tool."""
        tools_map = {
            "google_calendar_events": {
                "name": "google_calendar_events",
                "description": "Universal calendar event management with smart natural language support",
                "version": "1.0.0",
                "available": True,
                "category": "google_calendar",
                "optimized_for": ["OpenAI GPT", "Claude", "Gemini"],
                "features": ["CRUD operations", "Natural language parsing", "Smart filtering"],
                "usage_examples": [
                    {
                        "access_token": "your-token",
                        "action": "list",
                        "filters": {"time_min": "today", "max_results": 5},
                    },
                    {
                        "access_token": "your-token",
                        "action": "create",
                        "event_data": {
                            "summary": "Team Meeting",
                            "start_datetime": "2024-01-15T14:00:00Z",
                            "end_datetime": "2024-01-15T15:00:00Z",
                            "attendees": ["john@example.com"],
                        },
                    },
                ],
            },
            "google_calendar_quick_add": {
                "name": "google_calendar_quick_add",
                "description": "Natural language event creation optimized for LLM workflows",
                "version": "1.0.0",
                "available": True,
                "category": "google_calendar",
                "optimized_for": ["OpenAI GPT", "Claude", "Gemini"],
                "features": ["Natural language parsing", "Google's QuickAdd API", "AI-friendly"],
                "usage_examples": [
                    {
                        "access_token": "your-token",
                        "text": "Meeting with Sarah tomorrow at 2pm for 1 hour",
                    },
                    {"access_token": "your-token", "text": "Lunch with client next Friday at noon"},
                ],
            },
            "google_calendar_search": {
                "name": "google_calendar_search",
                "description": "Advanced calendar search with smart filtering",
                "version": "1.0.0",
                "available": True,
                "category": "google_calendar",
                "optimized_for": ["OpenAI GPT", "Claude", "Gemini"],
                "features": ["Multi-calendar search", "Time range presets", "Natural language"],
                "usage_examples": [
                    {
                        "access_token": "your-token",
                        "query": "meeting",
                        "time_range": {"preset": "this_week"},
                    }
                ],
            },
            "google_calendar_availability": {
                "name": "google_calendar_availability",
                "description": "Smart availability checking and free slot finding",
                "version": "1.0.0",
                "available": True,
                "category": "google_calendar",
                "optimized_for": ["OpenAI GPT", "Claude", "Gemini"],
                "features": [
                    "Free/busy analysis",
                    "Free slot detection",
                    "Business hours filtering",
                ],
                "usage_examples": [
                    {
                        "access_token": "your-token",
                        "time_range": {
                            "start": "tomorrow",
                            "end": "tomorrow",
                            "duration_minutes": 60,
                        },
                        "find_free_slots": True,
                    }
                ],
            },
        }

        return tools_map.get(
            tool_name,
            {
                "name": tool_name,
                "description": f"Tool '{tool_name}' not found",
                "available": False,
                "error": "Tool not found",
            },
        )

    def health_check(self) -> MCPHealthCheck:
        """MCP service health check."""
        available_tools = [
            "google_calendar_events",
            "google_calendar_quick_add",
            "google_calendar_search",
            "google_calendar_availability",
            "google_calendar_date_query",
        ]

        # All tools are available since tokens are provided per-request
        healthy = True

        return MCPHealthCheck(
            healthy=healthy,
            version="1.0.0",
            available_tools=available_tools,
            timestamp=int(time.time()),
            error=None,
        )


# Initialize Google Calendar MCP service
google_calendar_mcp_service = GoogleCalendarMCPService()
