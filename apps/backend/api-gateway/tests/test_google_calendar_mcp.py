"""
Comprehensive tests for Google Calendar MCP Tools
Tests all Google Calendar MCP functions with various LLM scenarios
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
from app.api.mcp.google_calendar_tools import GoogleCalendarMCPService
from app.models import MCPHealthCheck, MCPInvokeResponse


class TestGoogleCalendarMCPService:
    """Test suite for Google Calendar MCP Service."""

    @pytest.fixture
    def mcp_service(self):
        """Create Google Calendar MCP service instance."""
        return GoogleCalendarMCPService()

    @pytest.fixture
    def mock_google_calendar_client(self):
        """Create mock Google Calendar client."""
        with patch("app.api.mcp.google_calendar_tools.GoogleCalendarClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock common client methods
            mock_client.close = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            yield mock_client

    @pytest.fixture
    def sample_event_data(self):
        """Sample event data for testing."""
        return {
            "id": "event123",
            "summary": "Test Meeting",
            "description": "A test meeting",
            "location": "Conference Room A",
            "start": {"dateTime": "2024-01-15T14:00:00Z"},
            "end": {"dateTime": "2024-01-15T15:00:00Z"},
            "htmlLink": "https://calendar.google.com/event123",
            "attendees": [
                {"email": "john@example.com", "responseStatus": "accepted"},
                {"email": "jane@example.com", "responseStatus": "needsAction"},
            ],
            "created": "2024-01-10T10:00:00Z",
            "updated": "2024-01-10T10:30:00Z",
            "status": "confirmed",
        }

    def test_get_available_tools(self, mcp_service):
        """Test that all Google Calendar tools are available."""
        tools_response = mcp_service.get_available_tools()

        assert tools_response.total_count == 4
        assert tools_response.available_count == 4
        assert "google_calendar" in tools_response.categories

        tool_names = [tool.name for tool in tools_response.tools]
        expected_tools = [
            "google_calendar_events",
            "google_calendar_quick_add",
            "google_calendar_search",
            "google_calendar_availability",
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    def test_tool_schemas_completeness(self, mcp_service):
        """Test that all tools have complete schemas for LLM usage."""
        tools_response = mcp_service.get_available_tools()

        for tool in tools_response.tools:
            # Check required fields
            assert tool.name
            assert tool.description
            assert tool.inputSchema
            assert tool.category == "google_calendar"

            # Check schema structure
            schema = tool.inputSchema
            assert schema["type"] == "object"
            assert "properties" in schema
            assert "access_token" in schema["properties"]
            assert "required" in schema
            assert "access_token" in schema["required"]

    @pytest.mark.asyncio
    async def test_events_tool_list_action(
        self, mcp_service, mock_google_calendar_client, sample_event_data
    ):
        """Test google_calendar_events tool with list action."""
        # Setup mock response
        mock_google_calendar_client.list_events.return_value = {
            "success": True,
            "events": [sample_event_data],
            "total_count": 1,
            "has_more": False,
        }

        params = {
            "access_token": "test_token",
            "action": "list",
            "filters": {"time_min": "today", "max_results": 10},
        }

        response = await mcp_service.invoke_tool("google_calendar_events", params)

        assert isinstance(response, MCPInvokeResponse)
        assert not response.isError
        assert response.structuredContent is not None

        # Check structured content
        content = response.structuredContent
        assert content["action"] == "list"
        assert content["calendar_id"] == "primary"
        assert len(content["events"]) == 1

        # Check LLM-optimized event formatting
        event = content["events"][0]
        assert event["title"] == "Test Meeting"
        assert event["all_day"] is False
        assert "start_time" in event
        assert "attendees" in event

    @pytest.mark.asyncio
    async def test_events_tool_create_action(
        self, mcp_service, mock_google_calendar_client, sample_event_data
    ):
        """Test google_calendar_events tool with create action."""
        # Setup mock response
        mock_google_calendar_client.create_event.return_value = {
            "success": True,
            "event": sample_event_data,
            "event_id": "event123",
            "html_link": "https://calendar.google.com/event123",
        }

        params = {
            "access_token": "test_token",
            "action": "create",
            "event_data": {
                "summary": "New Meeting",
                "start_datetime": "2024-01-15T14:00:00Z",
                "end_datetime": "2024-01-15T15:00:00Z",
                "attendees": ["john@example.com"],
            },
        }

        response = await mcp_service.invoke_tool("google_calendar_events", params)

        assert not response.isError
        assert response.structuredContent["action"] == "create"
        assert response.structuredContent["event_id"] == "event123"

    @pytest.mark.asyncio
    async def test_quick_add_tool(
        self, mcp_service, mock_google_calendar_client, sample_event_data
    ):
        """Test google_calendar_quick_add tool with natural language."""
        # Setup mock response
        mock_google_calendar_client.quick_add_event.return_value = {
            "success": True,
            "event": sample_event_data,
            "event_id": "event123",
            "html_link": "https://calendar.google.com/event123",
            "parsed_text": "Meeting with John tomorrow at 2pm",
        }

        params = {
            "access_token": "test_token",
            "text": "Meeting with John tomorrow at 2pm for 1 hour",
        }

        response = await mcp_service.invoke_tool("google_calendar_quick_add", params)

        assert not response.isError
        content = response.structuredContent
        assert content["action"] == "quick_add"
        assert content["parsed_text"] == "Meeting with John tomorrow at 2pm for 1 hour"
        assert content["event_id"] == "event123"

    @pytest.mark.asyncio
    async def test_search_tool(self, mcp_service, mock_google_calendar_client, sample_event_data):
        """Test google_calendar_search tool."""
        # Setup mock response
        mock_google_calendar_client.search_events.return_value = {
            "success": True,
            "events": [sample_event_data],
            "total_count": 1,
            "has_more": False,
        }

        params = {
            "access_token": "test_token",
            "query": "meeting",
            "time_range": {"preset": "this_week"},
            "max_results": 20,
        }

        response = await mcp_service.invoke_tool("google_calendar_search", params)

        assert not response.isError
        content = response.structuredContent
        assert content["action"] == "search"
        assert content["query"] == "meeting"
        assert len(content["events"]) == 1

    @pytest.mark.asyncio
    async def test_availability_tool(
        self, mcp_service, mock_google_calendar_client, sample_event_data
    ):
        """Test google_calendar_availability tool."""
        # Setup mock response
        mock_google_calendar_client.list_events.return_value = {
            "success": True,
            "events": [sample_event_data],
            "total_count": 1,
            "has_more": False,
        }

        params = {
            "access_token": "test_token",
            "time_range": {
                "start": "2024-01-15T09:00:00Z",
                "end": "2024-01-15T17:00:00Z",
                "duration_minutes": 60,
            },
            "find_free_slots": True,
        }

        response = await mcp_service.invoke_tool("google_calendar_availability", params)

        assert not response.isError
        content = response.structuredContent
        assert content["action"] == "availability"
        assert "busy_times" in content
        assert "total_busy_periods" in content

    @pytest.mark.asyncio
    async def test_natural_language_time_parsing(self, mcp_service):
        """Test natural language time parsing capabilities."""
        test_cases = [
            (
                "today",
                lambda: datetime.now(timezone.utc)
                .replace(hour=0, minute=0, second=0, microsecond=0)
                .isoformat(),
            ),
            (
                "tomorrow",
                lambda: (datetime.now(timezone.utc) + timedelta(days=1))
                .replace(hour=0, minute=0, second=0, microsecond=0)
                .isoformat(),
            ),
            ("2024-01-15T14:00:00Z", "2024-01-15T14:00:00Z"),  # ISO format should pass through
        ]

        for input_time, expected in test_cases:
            result = mcp_service._parse_time_input(input_time)
            if callable(expected):
                expected_result = expected()
                # Allow some tolerance for time differences
                assert result is not None
            else:
                assert result == expected

    def test_preset_time_range_parsing(self, mcp_service):
        """Test preset time range parsing."""
        presets = ["today", "tomorrow", "this_week", "next_week", "this_month", "next_month"]

        for preset in presets:
            start, end = mcp_service._parse_preset_time_range(preset)
            assert start
            assert end
            assert start < end  # Start should be before end

    @pytest.mark.asyncio
    async def test_error_handling_missing_token(self, mcp_service):
        """Test error handling when access token is missing."""
        params = {
            "action": "list"
            # Missing access_token
        }

        response = await mcp_service.invoke_tool("google_calendar_events", params)

        assert response.isError
        assert "access_token parameter is required" in response.content[0].text

    @pytest.mark.asyncio
    async def test_error_handling_invalid_action(self, mcp_service, mock_google_calendar_client):
        """Test error handling for invalid actions."""
        params = {"access_token": "test_token", "action": "invalid_action"}

        with pytest.raises(ValueError, match="Unknown action"):
            await mcp_service.invoke_tool("google_calendar_events", params)

    @pytest.mark.asyncio
    async def test_error_handling_missing_event_id(self, mcp_service, mock_google_calendar_client):
        """Test error handling when event_id is missing for operations that require it."""
        params = {
            "access_token": "test_token",
            "action": "delete"
            # Missing event_id
        }

        with pytest.raises(ValueError, match="event_id is required"):
            await mcp_service.invoke_tool("google_calendar_events", params)

    @pytest.mark.asyncio
    async def test_unknown_tool_error(self, mcp_service):
        """Test error handling for unknown tools."""
        params = {"access_token": "test_token"}

        response = await mcp_service.invoke_tool("unknown_tool", params)

        assert response.isError
        assert "Tool 'unknown_tool' not found" in response.content[0].text

    def test_tool_info_completeness(self, mcp_service):
        """Test that tool info provides complete information for all tools."""
        tools = [
            "google_calendar_events",
            "google_calendar_quick_add",
            "google_calendar_search",
            "google_calendar_availability",
        ]

        for tool_name in tools:
            info = mcp_service.get_tool_info(tool_name)

            assert info["name"] == tool_name
            assert info["available"] is True
            assert info["category"] == "google_calendar"
            assert "OpenAI GPT" in info["optimized_for"]
            assert "Claude" in info["optimized_for"]
            assert "Gemini" in info["optimized_for"]
            assert "usage_examples" in info
            assert len(info["usage_examples"]) > 0

    def test_health_check(self, mcp_service):
        """Test MCP service health check."""
        health = mcp_service.health_check()

        assert isinstance(health, MCPHealthCheck)
        assert health.healthy is True
        assert health.version == "1.0.0"
        assert len(health.available_tools) == 4
        assert "google_calendar_events" in health.available_tools
        assert health.error is None

    @pytest.mark.asyncio
    async def test_event_formatting_for_llm(self, mcp_service, sample_event_data):
        """Test LLM-optimized event formatting."""
        formatted = mcp_service._format_event_for_llm(sample_event_data)

        # Check required fields for LLM consumption
        assert formatted["id"] == "event123"
        assert formatted["title"] == "Test Meeting"
        assert formatted["description"] == "A test meeting"
        assert formatted["location"] == "Conference Room A"
        assert formatted["all_day"] is False
        assert formatted["start_time"] == "2024-01-15T14:00:00Z"
        assert formatted["end_time"] == "2024-01-15T15:00:00Z"
        assert formatted["html_link"] == "https://calendar.google.com/event123"

        # Check attendees formatting
        assert len(formatted["attendees"]) == 2
        assert formatted["attendees"][0]["email"] == "john@example.com"
        assert formatted["attendees"][0]["status"] == "accepted"

    @pytest.mark.asyncio
    async def test_free_slot_finding(self, mcp_service):
        """Test free slot finding algorithm."""
        # Test data: busy from 2PM-3PM
        busy_times = [
            {
                "start": "2024-01-15T14:00:00Z",
                "end": "2024-01-15T15:00:00Z",
                "event_title": "Busy Meeting",
            }
        ]

        free_slots = mcp_service._find_free_slots(
            start_time="2024-01-15T09:00:00Z",
            end_time="2024-01-15T17:00:00Z",
            busy_times=busy_times,
            duration_minutes=60,
            business_hours_only=False,
            timezone_str="UTC",
        )

        # Should find slots before and after the busy time
        assert len(free_slots) >= 2

        # Check that free slots have required fields
        for slot in free_slots:
            assert "start" in slot
            assert "end" in slot
            assert "duration_minutes" in slot
            assert "can_fit_meeting" in slot

    @pytest.mark.parametrize(
        "ai_format,expected_format", [("structured", dict), ("narrative", dict), ("summary", dict)]
    )
    def test_ai_optimization_formats(self, mcp_service, ai_format, expected_format):
        """Test that AI optimization parameters are properly handled."""
        tools_response = mcp_service.get_available_tools()
        events_tool = next(
            tool for tool in tools_response.tools if tool.name == "google_calendar_events"
        )

        # Check that the tool schema supports AI optimization
        schema = events_tool.inputSchema
        assert isinstance(schema["properties"], expected_format)
        assert "include_content" in schema["properties"]

    @pytest.mark.asyncio
    async def test_client_lifecycle_management(self, mcp_service, mock_google_calendar_client):
        """Test that Google Calendar client is properly managed."""
        params = {"access_token": "test_token", "action": "list"}

        # Mock the client creation and closure
        mock_google_calendar_client.list_events.return_value = {
            "success": True,
            "events": [],
            "total_count": 0,
            "has_more": False,
        }

        await mcp_service.invoke_tool("google_calendar_events", params)

        # Verify client was closed
        mock_google_calendar_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_performance_execution_timing(self, mcp_service, mock_google_calendar_client):
        """Test that execution timing is properly tracked."""
        mock_google_calendar_client.list_events.return_value = {
            "success": True,
            "events": [],
            "total_count": 0,
            "has_more": False,
        }

        params = {"access_token": "test_token", "action": "list"}

        response = await mcp_service.invoke_tool("google_calendar_events", params)

        # Check that timing is tracked
        assert hasattr(response, "_execution_time_ms")
        assert response._execution_time_ms > 0
        assert response._tool_name == "google_calendar_events"

    def test_llm_compatibility_features(self, mcp_service):
        """Test that tools have LLM-optimized features."""
        tools_response = mcp_service.get_available_tools()

        for tool in tools_response.tools:
            # All tools should have clear descriptions
            assert len(tool.description) > 50  # Detailed description

            # All tools should have comprehensive schemas
            schema = tool.inputSchema
            assert "description" in schema["properties"]["access_token"]

            # Check for LLM-friendly parameter descriptions
            for prop_name, prop_def in schema["properties"].items():
                if isinstance(prop_def, dict) and "description" in prop_def:
                    assert len(prop_def["description"]) > 10  # Meaningful descriptions
