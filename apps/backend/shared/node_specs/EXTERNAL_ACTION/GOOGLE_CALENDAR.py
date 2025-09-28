"""
GOOGLE_CALENDAR External Action Node Specification

Google Calendar action node for performing calendar operations including
event management, scheduling, meeting coordination, and calendar automation.
"""

from typing import Any, Dict, List

from ...models.node_enums import ExternalActionSubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec, create_port


class GoogleCalendarActionSpec(BaseNodeSpec):
    """Google Calendar action specification for calendar operations."""

    def __init__(self):
        super().__init__(
            type=NodeType.EXTERNAL_ACTION,
            subtype=ExternalActionSubtype.GOOGLE_CALENDAR,
            name="Google_Calendar_Action",
            description="Perform Google Calendar operations including event management, scheduling, and calendar automation",
            # Configuration parameters
            configurations={
                "access_token": {
                    "type": "string",
                    "default": "",
                    "description": "OAuth2 access token for Google Calendar API authentication",
                    "required": True,
                    "sensitive": True,
                },
                "refresh_token": {
                    "type": "string",
                    "default": "",
                    "description": "OAuth2 refresh token for token renewal",
                    "required": False,
                    "sensitive": True,
                },
                "action_type": {
                    "type": "string",
                    "default": "create_event",
                    "description": "Google日历操作类型",
                    "required": True,
                    "options": [
                        # Core SDK Operations - aligned with GoogleCalendarSDK
                        "list_events",  # List calendar events
                        "create_event",  # Create new calendar event
                        "update_event",  # Update existing event
                        "delete_event",  # Delete event
                        "get_event",  # Get single event details
                        "list_calendars",  # List user's calendars
                        "create_calendar",  # Create new calendar
                        "get_calendar",  # Get calendar details
                        "search_events",  # Search events in calendar
                        "quick_add",  # Quick add event using natural language
                        "watch_events",  # Set up webhook for event changes
                        "stop_watching",  # Stop webhook monitoring
                        # MCP-aligned Operations
                        "google_calendar_list_calendars",  # MCP: List calendars
                        "google_calendar_create_event",  # MCP: Create event
                        "google_calendar_list_events",  # MCP: List events
                        "google_calendar_update_event",  # MCP: Update event
                        "google_calendar_delete_event",  # MCP: Delete event
                        "google_calendar_add_attendees_to_event",  # MCP: Add attendees to event
                    ],
                },
                "calendar_id": {
                    "type": "string",
                    "default": "primary",
                    "description": "日历ID",
                    "required": False,
                },
                # Event creation/update parameters (aligned with SDK)
                "summary": {
                    "type": "string",
                    "default": "",
                    "description": "Event title/summary",
                    "required": False,
                },
                "description": {
                    "type": "string",
                    "default": "",
                    "description": "Event description",
                    "required": False,
                },
                "location": {
                    "type": "string",
                    "default": "",
                    "description": "Event location",
                    "required": False,
                },
                "start": {
                    "type": "object",
                    "default": {},
                    "description": "Event start time (dateTime or date)",
                    "required": False,
                },
                "end": {
                    "type": "object",
                    "default": {},
                    "description": "Event end time (dateTime or date)",
                    "required": False,
                },
                "start_datetime": {
                    "type": "string",
                    "default": "",
                    "description": "Event start datetime (ISO format)",
                    "required": False,
                },
                "end_datetime": {
                    "type": "string",
                    "default": "",
                    "description": "Event end datetime (ISO format)",
                    "required": False,
                },
                "date": {
                    "type": "string",
                    "default": "",
                    "description": "Date for all-day events (YYYY-MM-DD format)",
                    "required": False,
                },
                "attendees": {
                    "type": "array",
                    "default": [],
                    "description": "List of attendees (email strings or objects)",
                    "required": False,
                },
                "event_id": {
                    "type": "string",
                    "default": "",
                    "description": "Event ID for update/delete operations",
                    "required": False,
                },
                "reminders": {
                    "type": "object",
                    "default": {},
                    "description": "Event reminders configuration",
                    "required": False,
                },
                "recurrence": {
                    "type": "array",
                    "default": [],
                    "description": "Recurrence rules for repeating events",
                    "required": False,
                },
                # List/Search parameters (aligned with SDK)
                "time_min": {
                    "type": "string",
                    "default": "",
                    "description": "Lower bound for event search (ISO datetime)",
                    "required": False,
                },
                "time_max": {
                    "type": "string",
                    "default": "",
                    "description": "Upper bound for event search (ISO datetime)",
                    "required": False,
                },
                "max_results": {
                    "type": "integer",
                    "default": 250,
                    "description": "Maximum number of events to return (1-2500)",
                    "required": False,
                },
                "single_events": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to expand recurring events into instances",
                    "required": False,
                },
                "order_by": {
                    "type": "string",
                    "default": "startTime",
                    "description": "Order of events (startTime or updated)",
                    "required": False,
                    "options": ["startTime", "updated"],
                },
                "show_deleted": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether to include deleted events",
                    "required": False,
                },
                "q": {
                    "type": "string",
                    "default": "",
                    "description": "Free text search query",
                    "required": False,
                },
                "query": {
                    "type": "string",
                    "default": "",
                    "description": "Search query (alias for q parameter)",
                    "required": False,
                },
                "text": {
                    "type": "string",
                    "default": "",
                    "description": "Natural language text for quick_add operation",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Default runtime parameters
            default_input_params={"data": {}, "context": {}, "variables": {}},
            default_output_params={
                "success": False,
                "google_response": {},
                "event": {},
                "events": [],
                "calendars": [],
                "next_page_token": "",
                "next_sync_token": "",
                "html_link": "",
                "event_id": "",
                "event_url": "",
                "calendar_url": "",
                "meeting_link": "",
                "error_message": "",
                "execution_metadata": {},
            },
            # Port definitions
            input_ports=[
                create_port(
                    port_id="main",
                    name="main",
                    data_type="dict",
                    description="Input data for Google Calendar action",
                    required=True,
                    max_connections=1,
                )
            ],
            output_ports=[
                create_port(
                    port_id="success",
                    name="success",
                    data_type="dict",
                    description="Output when Google Calendar action succeeds",
                    required=True,
                    max_connections=-1,
                ),
                create_port(
                    port_id="error",
                    name="error",
                    data_type="dict",
                    description="Output when Google Calendar action fails",
                    required=False,
                    max_connections=-1,
                ),
            ],
            # Metadata
            tags=[
                "external-action",
                "google-calendar",
                "scheduling",
                "events",
                "meetings",
                "productivity",
            ],
            # Examples
            examples=[
                {
                    "name": "Create Team Meeting Event",
                    "description": "Create recurring team meeting with attendees and Google Meet link",
                    "configurations": {
                        "access_token": "ya29.a0AfH6SMC_example_access_token",
                        "action_type": "create_event",
                        "calendar_id": "primary",
                        "summary": "{{meeting_title}}",
                        "description": "{{meeting_agenda}}\\n\\n**Attendees:** {{attendee_list}}\\n**Meeting Type:** {{meeting_type}}\\n\\n**Agenda Items:**\\n{{agenda_items}}",
                        "location": "{{meeting_location}}",
                        "start_datetime": "{{start_datetime}}",
                        "end_datetime": "{{end_datetime}}",
                        "attendees": "{{attendees}}",
                        "recurrence": [
                            "RRULE:FREQ={{recurrence_frequency}};BYDAY={{recurrence_days}}"
                        ],
                    },
                    "input_example": {
                        "data": {
                            "meeting_title": "Weekly Engineering Standup",
                            "meeting_agenda": "Weekly team sync to discuss progress, blockers, and upcoming tasks",
                            "attendee_list": "Engineering Team, Product Manager, Scrum Master",
                            "meeting_type": "Team Standup",
                            "agenda_items": "- Sprint progress review\\n- Blocker discussion\\n- Next week planning",
                            "meeting_location": "Conference Room A / Google Meet",
                            "start_datetime": "2025-01-21T09:00:00",
                            "end_datetime": "2025-01-21T09:30:00",
                            "timezone": "America/Los_Angeles",
                            "attendees": [
                                {"email": "dev1@company.com", "displayName": "Alice Developer"},
                                {"email": "dev2@company.com", "displayName": "Bob Engineer"},
                                {"email": "pm@company.com", "displayName": "Carol PM"},
                            ],
                            "recurrence_frequency": "WEEKLY",
                            "recurrence_days": ["MO"],
                        }
                    },
                    "expected_outputs": {
                        "success": {
                            "success": True,
                            "google_response": {
                                "id": "abc123def456ghi789",
                                "summary": "Weekly Engineering Standup",
                                "htmlLink": "https://calendar.google.com/calendar/event?eid=abc123def456ghi789",
                                "start": {
                                    "dateTime": "2025-01-21T09:00:00-08:00",
                                    "timeZone": "America/Los_Angeles",
                                },
                                "end": {
                                    "dateTime": "2025-01-21T09:30:00-08:00",
                                    "timeZone": "America/Los_Angeles",
                                },
                                "attendees": [
                                    {"email": "dev1@company.com", "responseStatus": "needsAction"},
                                    {"email": "dev2@company.com", "responseStatus": "needsAction"},
                                    {"email": "pm@company.com", "responseStatus": "needsAction"},
                                ],
                                "hangoutLink": "https://meet.google.com/abc-defg-hij",
                                "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=MO"],
                            },
                            "event_id": "abc123def456ghi789",
                            "event_url": "https://calendar.google.com/calendar/event?eid=abc123def456ghi789",
                            "meeting_link": "https://meet.google.com/abc-defg-hij",
                            "execution_metadata": {
                                "action_type": "create_event",
                                "calendar_id": "primary",
                                "attendees_invited": 3,
                                "meeting_created": True,
                                "recurring_event": True,
                                "execution_time_ms": 850,
                            },
                        }
                    },
                },
                {
                    "name": "Find Available Meeting Time",
                    "description": "Find optimal meeting time across multiple attendees' calendars",
                    "configurations": {
                        "access_token": "ya29.a0AfH6SMC_example_access_token",
                        "refresh_token": "1//04_example_refresh_token",
                        "action_type": "find_meeting_time",
                        "time_min": "{{search_start}}",
                        "time_max": "{{search_end}}",
                        "single_events": True,
                    },
                    "input_example": {
                        "data": {
                            "search_start": "2025-01-22T00:00:00Z",
                            "search_end": "2025-01-26T23:59:59Z",
                            "required_attendees": ["manager@company.com", "lead@company.com"],
                            "optional_attendees": ["consultant@company.com"],
                            "meeting_duration": 60,
                            "priority": "high",
                            "meeting_purpose": "quarterly_review",
                        }
                    },
                    "expected_outputs": {
                        "success": {
                            "success": True,
                            "google_response": {
                                "suggestions": [
                                    {
                                        "start": "2025-01-23T10:00:00-08:00",
                                        "end": "2025-01-23T11:00:00-08:00",
                                        "score": 95,
                                        "conflicts": [],
                                        "available_attendees": [
                                            "manager@company.com",
                                            "lead@company.com",
                                            "consultant@company.com",
                                        ],
                                    },
                                    {
                                        "start": "2025-01-24T14:00:00-08:00",
                                        "end": "2025-01-24T15:00:00-08:00",
                                        "score": 88,
                                        "conflicts": [],
                                        "available_attendees": [
                                            "manager@company.com",
                                            "lead@company.com",
                                        ],
                                    },
                                ]
                            },
                            "execution_metadata": {
                                "action_type": "find_meeting_time",
                                "calendars_checked": 3,
                                "time_slots_analyzed": 120,
                                "suggestions_found": 2,
                                "best_match_score": 95,
                                "execution_time_ms": 2200,
                            },
                        }
                    },
                },
                {
                    "name": "Book Conference Room with Equipment",
                    "description": "Book conference room with specific equipment and capacity requirements",
                    "configurations": {
                        "access_token": "ya29.a0AfH6SMC_example_access_token",
                        "action_type": "book_room",
                        "summary": "{{meeting_title}} - {{room_name}}",
                        "description": "**Meeting Details:**\\n{{meeting_description}}\\n\\n**Room Features:**\\n{{room_features}}\\n\\n**Equipment Reserved:**\\n{{equipment_list}}",
                        "start_datetime": "{{start_datetime}}",
                        "end_datetime": "{{end_datetime}}",
                        "attendees": "{{attendees}}",
                    },
                    "input_example": {
                        "data": {
                            "room_email": "conf-room-a@company.com",
                            "room_name": "Conference Room A",
                            "min_capacity": 12,
                            "required_equipment": ["projector", "whiteboard", "video_conference"],
                            "required_features": ["av_equipment", "teleconference"],
                            "meeting_title": "Q1 Board Meeting",
                            "meeting_description": "Quarterly board meeting to review financial results and strategic initiatives",
                            "room_features": "- 4K Projector\\n- Interactive Whiteboard\\n- Video Conferencing System\\n- Premium Audio",
                            "equipment_list": "- Projector reserved\\n- Whiteboard materials\\n- VC system configured",
                            "start_datetime": "2025-01-25T14:00:00",
                            "end_datetime": "2025-01-25T16:00:00",
                            "timezone": "America/New_York",
                            "attendees": [
                                {"email": "ceo@company.com", "displayName": "CEO"},
                                {"email": "cfo@company.com", "displayName": "CFO"},
                                {"email": "board1@company.com", "displayName": "Board Member 1"},
                            ],
                        }
                    },
                    "expected_outputs": {
                        "success": {
                            "success": True,
                            "google_response": {
                                "id": "room789meeting456book",
                                "summary": "Q1 Board Meeting - Conference Room A",
                                "location": "Conference Room A, 15th Floor",
                                "start": {
                                    "dateTime": "2025-01-25T14:00:00-05:00",
                                    "timeZone": "America/New_York",
                                },
                                "end": {
                                    "dateTime": "2025-01-25T16:00:00-05:00",
                                    "timeZone": "America/New_York",
                                },
                                "attendees": [
                                    {
                                        "email": "conf-room-a@company.com",
                                        "resource": True,
                                        "responseStatus": "accepted",
                                    },
                                    {"email": "ceo@company.com", "responseStatus": "needsAction"},
                                    {"email": "cfo@company.com", "responseStatus": "needsAction"},
                                ],
                            },
                            "event_id": "room789meeting456book",
                            "event_url": "https://calendar.google.com/calendar/event?eid=room789meeting456book",
                            "execution_metadata": {
                                "action_type": "book_room",
                                "room_booked": "conf-room-a@company.com",
                                "capacity_met": True,
                                "equipment_reserved": True,
                                "attendees_notified": 3,
                                "execution_time_ms": 950,
                            },
                        }
                    },
                },
                {
                    "name": "Update Recurring Meeting Series",
                    "description": "Update all future instances of a recurring meeting series",
                    "configurations": {
                        "access_token": "ya29.a0AfH6SMC_example_access_token",
                        "action_type": "update_series",
                        "calendar_id": "primary",
                        "event_id": "{{series_event_id}}",
                        "summary": "{{updated_title}}",
                        "description": "{{updated_description}}",
                        "location": "{{updated_location}}",
                        "start_datetime": "{{new_start_time}}",
                        "end_datetime": "{{new_end_time}}",
                        "attendees": "{{updated_attendees}}",
                    },
                    "input_example": {
                        "data": {
                            "series_event_id": "weekly123standup456series",
                            "updated_title": "Weekly Engineering Standup (Extended)",
                            "updated_description": "Extended weekly team sync - now 45 minutes to include retrospective discussion",
                            "updated_location": "Conference Room B / Google Meet",
                            "new_start_time": "2025-01-27T09:00:00",
                            "new_end_time": "2025-01-27T09:45:00",
                            "timezone": "America/Los_Angeles",
                            "updated_attendees": [
                                {"email": "dev1@company.com", "displayName": "Alice Developer"},
                                {"email": "dev2@company.com", "displayName": "Bob Engineer"},
                                {"email": "dev3@company.com", "displayName": "Charlie Coder"},
                                {"email": "pm@company.com", "displayName": "Carol PM"},
                            ],
                            "change_reason": "Extended time for retrospective",
                            "effective_date": "2025-01-27",
                        }
                    },
                    "expected_outputs": {
                        "success": {
                            "success": True,
                            "google_response": {
                                "id": "weekly123standup456series",
                                "summary": "Weekly Engineering Standup (Extended)",
                                "htmlLink": "https://calendar.google.com/calendar/event?eid=weekly123standup456series",
                                "start": {
                                    "dateTime": "2025-01-27T09:00:00-08:00",
                                    "timeZone": "America/Los_Angeles",
                                },
                                "end": {
                                    "dateTime": "2025-01-27T09:45:00-08:00",
                                    "timeZone": "America/Los_Angeles",
                                },
                                "attendees": [
                                    {"email": "dev1@company.com", "responseStatus": "accepted"},
                                    {"email": "dev2@company.com", "responseStatus": "accepted"},
                                    {"email": "dev3@company.com", "responseStatus": "needsAction"},
                                    {"email": "pm@company.com", "responseStatus": "accepted"},
                                ],
                                "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=MO"],
                            },
                            "event_id": "weekly123standup456series",
                            "event_url": "https://calendar.google.com/calendar/event?eid=weekly123standup456series",
                            "execution_metadata": {
                                "action_type": "update_series",
                                "calendar_id": "primary",
                                "series_updated": True,
                                "future_instances_affected": 52,
                                "new_attendee_added": 1,
                                "duration_extended_minutes": 15,
                                "execution_time_ms": 1200,
                            },
                        }
                    },
                },
            ],
        )


# Export the specification instance
GOOGLE_CALENDAR_EXTERNAL_ACTION_SPEC = GoogleCalendarActionSpec()
