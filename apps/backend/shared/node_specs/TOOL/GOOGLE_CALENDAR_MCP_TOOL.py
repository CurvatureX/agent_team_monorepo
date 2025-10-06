"""
GOOGLE_CALENDAR_MCP_TOOL Tool Node Specification

MCP tool for Google Calendar integration capabilities.
This tool is attached to AI_AGENT nodes and provides Google Calendar
event management through the MCP protocol.

Note: TOOL nodes are attached to AI_AGENT nodes via attached_nodes,
not connected through input/output ports.
"""

from typing import Any, Dict, List

from ...models.node_enums import NodeType, ToolSubtype
from ..base import COMMON_CONFIGS, BaseNodeSpec


class GoogleCalendarMCPToolSpec(BaseNodeSpec):
    """Google Calendar MCP Tool specification for AI_AGENT attached functionality."""

    def __init__(self):
        super().__init__(
            type=NodeType.TOOL,
            subtype=ToolSubtype.GOOGLE_CALENDAR_MCP_TOOL,
            name="Google_Calendar_MCP_Tool",
            description="Google Calendar MCP tool for event management and scheduling through MCP protocol",
            # Configuration parameters
            configurations={
                "mcp_server_url": {
                    "type": "string",
                    "default": "http://localhost:8000/api/v1/mcp",
                    "description": "MCP服务器URL",
                    "required": True,
                },
                "access_token": {
                    "type": "string",
                    "default": "{{$placeholder}}",
                    "description": "Google OAuth access token for Calendar API authentication",
                    "required": True,
                    "sensitive": True,
                },
                "default_calendar_id": {
                    "type": "string",
                    "default": "primary",
                    "description": "默认日历ID",
                    "required": False,
                },
                "available_tools": {
                    "type": "array",
                    "default": [
                        "google_calendar_events",
                        "google_calendar_quick_add",
                        "google_calendar_search",
                        "google_calendar_availability",
                    ],
                    "description": "可用的Google Calendar工具列表",
                    "required": False,
                    "options": [
                        "google_calendar_events",
                        "google_calendar_quick_add",
                        "google_calendar_search",
                        "google_calendar_availability",
                        "google_calendar_date_query",
                    ],
                },
                "timezone": {
                    "type": "string",
                    "default": "UTC",
                    "description": "默认时区",
                    "required": False,
                },
                "max_results": {
                    "type": "integer",
                    "default": 20,
                    "min": 1,
                    "max": 250,
                    "description": "最大结果数量",
                    "required": False,
                },
                "enable_natural_language": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否启用自然语言解析",
                    "required": False,
                },
                "business_hours_only": {
                    "type": "boolean",
                    "default": False,
                    "description": "是否仅考虑工作时间",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Schema-style runtime parameters for tool execution
            input_params={
                "tool_name": {
                    "type": "string",
                    "default": "",
                    "description": "MCP tool function name to invoke",
                    "required": True,
                },
                "function_args": {
                    "type": "object",
                    "default": {},
                    "description": "Arguments for the selected tool function",
                    "required": False,
                },
                "context": {
                    "type": "object",
                    "default": {},
                    "description": "Optional context to pass along with the tool call",
                    "required": False,
                },
                "call_id": {
                    "type": "string",
                    "default": "",
                    "description": "Optional correlation ID for tracing",
                    "required": False,
                },
            },
            output_params={
                "result": {
                    "type": "object",
                    "default": {},
                    "description": "Result payload returned by the MCP tool",
                    "required": False,
                },
                "success": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether the MCP tool invocation succeeded",
                    "required": False,
                },
                "error_message": {
                    "type": "string",
                    "default": "",
                    "description": "Error details if invocation failed",
                    "required": False,
                },
                "execution_time": {
                    "type": "number",
                    "default": 0.0,
                    "description": "Execution time in seconds",
                    "required": False,
                },
                "cached": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether the result was served from cache",
                    "required": False,
                },
                "calendar_id": {
                    "type": "string",
                    "default": "",
                    "description": "Calendar ID involved in the operation",
                    "required": False,
                },
                "event_id": {
                    "type": "string",
                    "default": "",
                    "description": "Event ID created or referenced by the operation",
                    "required": False,
                },
            },
            # TOOL nodes have no ports - they are attached to AI_AGENT nodes            # Tools don't have attached_nodes (only AI_AGENT has this)
            attached_nodes=None,
            # Metadata
            tags=["tool", "mcp", "google-calendar", "scheduling", "events", "attached"],
            # Examples
            examples=[
                {
                    "name": "List Calendar Events",
                    "description": "List events from Google Calendar with natural language filtering",
                    "configurations": {
                        "mcp_server_url": "http://localhost:8000/api/v1/mcp",
                        "access_token": "oauth_token_123",
                        "default_calendar_id": "primary",
                        "available_tools": ["google_calendar_events"],
                        "timezone": "America/New_York",
                        "max_results": 10,
                    },
                    "usage_example": {
                        "attached_to": "calendar_assistant_ai",
                        "function_call": {
                            "tool_name": "google_calendar_events",
                            "function_args": {
                                "access_token": "oauth_token_123",
                                "action": "list",
                                "calendar_id": "primary",
                                "filters": {
                                    "time_min": "today",
                                    "time_max": "next week",
                                    "max_results": 10,
                                    "query": "meeting",
                                    "single_events": True,
                                    "order_by": "startTime",
                                },
                                "include_content": True,
                            },
                            "context": {"user_request": "Show me all meetings this week"},
                        },
                        "expected_result": {
                            "result": {
                                "action": "list",
                                "calendar_id": "primary",
                                "events": [
                                    {
                                        "id": "event_123",
                                        "title": "Team Standup",
                                        "start_time": "2025-01-20T09:00:00-05:00",
                                        "end_time": "2025-01-20T09:30:00-05:00",
                                        "location": "Conference Room A",
                                        "attendees": [
                                            {"email": "alice@example.com", "status": "accepted"},
                                            {"email": "bob@example.com", "status": "needsAction"},
                                        ],
                                        "all_day": False,
                                        "timezone": "America/New_York",
                                    }
                                ],
                                "total_count": 5,
                                "has_more": False,
                            },
                            "success": True,
                            "execution_time": 1.5,
                            "calendar_id": "primary",
                        },
                    },
                },
                {
                    "name": "Quick Add Natural Language Event",
                    "description": "Create events using natural language descriptions",
                    "configurations": {
                        "mcp_server_url": "http://localhost:8000/api/v1/mcp",
                        "access_token": "oauth_token_456",
                        "available_tools": ["google_calendar_quick_add"],
                        "enable_natural_language": True,
                    },
                    "usage_example": {
                        "attached_to": "scheduling_ai",
                        "function_call": {
                            "tool_name": "google_calendar_quick_add",
                            "function_args": {
                                "access_token": "oauth_token_456",
                                "text": "Lunch meeting with Sarah tomorrow at 12:30pm for 1 hour at Downtown Cafe",
                                "calendar_id": "primary",
                                "send_notifications": True,
                            },
                            "context": {"user_request": "Schedule lunch with Sarah tomorrow"},
                        },
                        "expected_result": {
                            "result": {
                                "action": "quick_add",
                                "calendar_id": "primary",
                                "parsed_text": "Lunch meeting with Sarah tomorrow at 12:30pm for 1 hour at Downtown Cafe",
                                "event": {
                                    "id": "event_new_789",
                                    "title": "Lunch meeting with Sarah",
                                    "start_time": "2025-01-21T12:30:00-05:00",
                                    "end_time": "2025-01-21T13:30:00-05:00",
                                    "location": "Downtown Cafe",
                                    "html_link": "https://calendar.google.com/event?eid=event_new_789",
                                },
                                "event_id": "event_new_789",
                            },
                            "success": True,
                            "execution_time": 0.9,
                            "calendar_id": "primary",
                            "event_id": "event_new_789",
                        },
                    },
                },
                {
                    "name": "Check Availability",
                    "description": "Find free time slots for scheduling meetings",
                    "configurations": {
                        "mcp_server_url": "http://localhost:8000/api/v1/mcp",
                        "access_token": "oauth_token_789",
                        "available_tools": ["google_calendar_availability"],
                        "business_hours_only": True,
                        "timezone": "UTC",
                    },
                    "usage_example": {
                        "attached_to": "meeting_scheduler_ai",
                        "function_call": {
                            "tool_name": "google_calendar_availability",
                            "function_args": {
                                "access_token": "oauth_token_789",
                                "calendars": ["primary"],
                                "time_range": {
                                    "start": "tomorrow 9am",
                                    "end": "tomorrow 5pm",
                                    "duration_minutes": 60,
                                },
                                "find_free_slots": True,
                                "business_hours_only": True,
                                "timezone": "UTC",
                            },
                            "context": {"meeting_duration": 60, "preferred_time": "business_hours"},
                        },
                        "expected_result": {
                            "result": {
                                "action": "availability",
                                "calendars_checked": ["primary"],
                                "time_range": {
                                    "start": "2025-01-21T09:00:00Z",
                                    "end": "2025-01-21T17:00:00Z",
                                },
                                "busy_times": [
                                    {
                                        "start": "2025-01-21T10:00:00Z",
                                        "end": "2025-01-21T11:00:00Z",
                                        "event_title": "Team Meeting",
                                        "calendar": "primary",
                                    }
                                ],
                                "free_slots": [
                                    {
                                        "start": "2025-01-21T09:00:00Z",
                                        "end": "2025-01-21T10:00:00Z",
                                        "duration_minutes": 60,
                                        "can_fit_meeting": True,
                                    },
                                    {
                                        "start": "2025-01-21T11:00:00Z",
                                        "end": "2025-01-21T17:00:00Z",
                                        "duration_minutes": 360,
                                        "can_fit_meeting": True,
                                    },
                                ],
                                "available_slots_count": 2,
                            },
                            "success": True,
                            "execution_time": 1.3,
                            "calendar_id": "primary",
                        },
                    },
                },
            ],
        )


# Export the specification instance
GOOGLE_CALENDAR_MCP_TOOL_SPEC = GoogleCalendarMCPToolSpec()
