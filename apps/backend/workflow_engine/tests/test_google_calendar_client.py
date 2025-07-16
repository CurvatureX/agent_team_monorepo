"""
Unit tests for GoogleCalendarClient.

Tests Google Calendar API client functionality including CRUD operations,
authentication, error handling, and data validation.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch, MagicMock

import httpx

from workflow_engine.clients.google_calendar_client import (
    GoogleCalendarClient,
    GoogleCalendarError,
    CalendarNotFoundError,
    EventNotFoundError
)
from workflow_engine.clients.base_client import (
    APIClientError,
    TokenExpiredError,
    RateLimitError,
    PaginatedResponse
)
from workflow_engine.models.credential import OAuth2Credential


class TestGoogleCalendarClient:
    """Test cases for GoogleCalendarClient."""
    
    @pytest.fixture
    def mock_credentials(self):
        """Create mock OAuth2 credentials."""
        return OAuth2Credential(
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_type="Bearer",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            provider="google_calendar"
        )
    
    @pytest.fixture
    def client(self, mock_credentials):
        """Create GoogleCalendarClient instance for testing."""
        return GoogleCalendarClient(mock_credentials)
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings for client configuration."""
        settings = Mock()
        settings.api_timeout_connect = 5
        settings.api_timeout_read = 30
        settings.api_max_retries = 3
        settings.get_retry_delays.return_value = [2, 4, 8]
        return settings
    
    def test_client_initialization(self, mock_credentials):
        """Test client initialization."""
        client = GoogleCalendarClient(mock_credentials)
        assert client.credentials == mock_credentials
        assert client._get_base_url() == "https://www.googleapis.com/calendar/v3"
        assert client._get_service_name() == "Google Calendar"
    
    def test_client_initialization_without_credentials(self):
        """Test client initialization without credentials."""
        with pytest.raises(ValueError, match="Google Calendar credentials are required"):
            GoogleCalendarClient(None)
    
    @pytest.mark.asyncio
    async def test_list_calendars_success(self, client, mock_settings):
        """Test successful calendar listing."""
        expected_calendars = [
            {"id": "primary", "summary": "Primary Calendar"},
            {"id": "cal2", "summary": "Work Calendar"}
        ]
        
        with patch('workflow_engine.clients.google_calendar_client.get_settings', return_value=mock_settings), \
             patch.object(client, '_make_request', return_value={"items": expected_calendars}) as mock_request:
            
            calendars = await client.list_calendars()
            
            assert calendars == expected_calendars
            mock_request.assert_called_once_with("GET", "/users/me/calendarList")
    
    @pytest.mark.asyncio
    async def test_create_event_success(self, client, mock_settings):
        """Test successful event creation."""
        event_data = {
            "summary": "Test Event",
            "description": "Test Description",
            "start": {
                "dateTime": "2025-01-20T10:00:00Z",
                "timeZone": "UTC"
            },
            "end": {
                "dateTime": "2025-01-20T11:00:00Z",
                "timeZone": "UTC"
            }
        }
        
        expected_response = {
            "id": "event123",
            "summary": "Test Event",
            "htmlLink": "https://calendar.google.com/event?eid=event123"
        }
        
        with patch('workflow_engine.clients.google_calendar_client.get_settings', return_value=mock_settings), \
             patch.object(client, '_make_request', return_value=expected_response) as mock_request:
            
            result = await client.create_event("primary", event_data)
            
            assert result == expected_response
            mock_request.assert_called_once_with("POST", "/calendars/primary/events", json=event_data)
    
    @pytest.mark.asyncio
    async def test_create_event_validation_error(self, client):
        """Test event creation with invalid data."""
        # Missing summary
        invalid_data = {
            "start": {"dateTime": "2025-01-20T10:00:00Z"},
            "end": {"dateTime": "2025-01-20T11:00:00Z"}
        }
        
        with pytest.raises(ValueError, match="Event summary is required"):
            await client.create_event("primary", invalid_data)
        
        # Missing start time
        invalid_data = {
            "summary": "Test Event",
            "end": {"dateTime": "2025-01-20T11:00:00Z"}
        }
        
        with pytest.raises(ValueError, match="Event start time is required"):
            await client.create_event("primary", invalid_data)
    
    @pytest.mark.asyncio
    async def test_create_event_calendar_not_found(self, client, mock_settings):
        """Test event creation with non-existent calendar."""
        event_data = {
            "summary": "Test Event",
            "start": {"dateTime": "2025-01-20T10:00:00Z"},
            "end": {"dateTime": "2025-01-20T11:00:00Z"}
        }
        
        with patch('workflow_engine.clients.google_calendar_client.get_settings', return_value=mock_settings), \
             patch.object(client, '_make_request', side_effect=Exception("notFound")) as mock_request:
            
            with pytest.raises(CalendarNotFoundError, match="Calendar 'invalid_calendar' not found"):
                await client.create_event("invalid_calendar", event_data)
    
    @pytest.mark.asyncio
    async def test_list_events_success(self, client, mock_settings):
        """Test successful event listing."""
        expected_events = [
            {"id": "event1", "summary": "Event 1"},
            {"id": "event2", "summary": "Event 2"}
        ]
        
        expected_response = {
            "items": expected_events,
            "nextPageToken": "next_token_123"
        }
        
        with patch('workflow_engine.clients.google_calendar_client.get_settings', return_value=mock_settings), \
             patch.object(client, '_make_request', return_value=expected_response) as mock_request:
            
            result = await client.list_events(
                "primary", 
                time_min="2025-01-20T00:00:00Z",
                time_max="2025-01-21T00:00:00Z"
            )
            
            assert isinstance(result, PaginatedResponse)
            assert result.items == expected_events
            assert result.next_page_token == "next_token_123"
            assert result.has_more is True
            
            # Verify request parameters
            args, kwargs = mock_request.call_args
            assert args[0] == "GET"
            assert args[1] == "/calendars/primary/events"
            assert kwargs["params"]["timeMin"] == "2025-01-20T00:00:00Z"
            assert kwargs["params"]["timeMax"] == "2025-01-21T00:00:00Z"
    
    @pytest.mark.asyncio
    async def test_get_event_success(self, client, mock_settings):
        """Test successful event retrieval."""
        expected_event = {
            "id": "event123",
            "summary": "Test Event",
            "start": {"dateTime": "2025-01-20T10:00:00Z"}
        }
        
        with patch('workflow_engine.clients.google_calendar_client.get_settings', return_value=mock_settings), \
             patch.object(client, '_make_request', return_value=expected_event) as mock_request:
            
            result = await client.get_event("primary", "event123")
            
            assert result == expected_event
            mock_request.assert_called_once_with("GET", "/calendars/primary/events/event123")
    
    @pytest.mark.asyncio
    async def test_get_event_not_found(self, client, mock_settings):
        """Test event retrieval with non-existent event."""
        with patch('workflow_engine.clients.google_calendar_client.get_settings', return_value=mock_settings), \
             patch.object(client, '_make_request', side_effect=Exception("notFound")):
            
            with pytest.raises(EventNotFoundError, match="Event 'nonexistent' not found"):
                await client.get_event("primary", "nonexistent")
    
    @pytest.mark.asyncio
    async def test_update_event_success(self, client, mock_settings):
        """Test successful event update."""
        update_data = {
            "summary": "Updated Event",
            "start": {"dateTime": "2025-01-20T11:00:00Z"},
            "end": {"dateTime": "2025-01-20T12:00:00Z"}
        }
        
        expected_response = {
            "id": "event123",
            "summary": "Updated Event"
        }
        
        with patch('workflow_engine.clients.google_calendar_client.get_settings', return_value=mock_settings), \
             patch.object(client, '_make_request', return_value=expected_response) as mock_request:
            
            result = await client.update_event("primary", "event123", update_data)
            
            assert result == expected_response
            mock_request.assert_called_once_with("PUT", "/calendars/primary/events/event123", json=update_data)
    
    @pytest.mark.asyncio
    async def test_delete_event_success(self, client, mock_settings):
        """Test successful event deletion."""
        with patch('workflow_engine.clients.google_calendar_client.get_settings', return_value=mock_settings), \
             patch.object(client, '_make_request', return_value={}) as mock_request:
            
            result = await client.delete_event("primary", "event123")
            
            assert result is True
            mock_request.assert_called_once_with("DELETE", "/calendars/primary/events/event123")
    
    @pytest.mark.asyncio
    async def test_delete_event_not_found(self, client, mock_settings):
        """Test event deletion with non-existent event."""
        with patch('workflow_engine.clients.google_calendar_client.get_settings', return_value=mock_settings), \
             patch.object(client, '_make_request', side_effect=Exception("notFound")):
            
            with pytest.raises(EventNotFoundError, match="Event 'nonexistent' not found"):
                await client.delete_event("primary", "nonexistent")
    
    def test_validate_event_data_valid(self, client):
        """Test event data validation with valid data."""
        valid_data = {
            "summary": "Test Event",
            "start": {"dateTime": "2025-01-20T10:00:00Z"},
            "end": {"dateTime": "2025-01-20T11:00:00Z"},
            "attendees": [{"email": "test@example.com"}]
        }
        
        # Should not raise any exception
        client._validate_event_data(valid_data)
    
    def test_validate_event_data_invalid(self, client):
        """Test event data validation with invalid data."""
        # Invalid attendees format
        invalid_data = {
            "summary": "Test Event",
            "start": {"dateTime": "2025-01-20T10:00:00Z"},
            "end": {"dateTime": "2025-01-20T11:00:00Z"},
            "attendees": [{"name": "No Email"}]  # Missing email
        }
        
        with pytest.raises(ValueError, match="Each attendee must have an email field"):
            client._validate_event_data(invalid_data)
    
    def test_validate_event_data_update(self, client):
        """Test event data validation for updates."""
        # For updates, summary is not required
        update_data = {
            "description": "Updated description"
        }
        
        # Should not raise any exception
        client._validate_event_data(update_data, is_update=True)
    
    def test_normalize_datetime(self, client):
        """Test datetime normalization."""
        # Already in RFC3339 format
        dt1 = "2025-01-20T10:00:00Z"
        assert client._normalize_datetime(dt1) == dt1
        
        # ISO format without timezone
        dt2 = "2025-01-20T10:00:00"
        result2 = client._normalize_datetime(dt2)
        assert result2.endswith("Z")
        
        # Invalid format should be returned as-is
        dt3 = "invalid datetime"
        assert client._normalize_datetime(dt3) == dt3
    
    @pytest.mark.asyncio
    async def test_quick_add_event_success(self, client, mock_settings):
        """Test successful quick add event."""
        expected_response = {
            "id": "quick_event123",
            "summary": "Meeting with John tomorrow 2pm"
        }
        
        with patch('workflow_engine.clients.google_calendar_client.get_settings', return_value=mock_settings), \
             patch.object(client, '_make_request', return_value=expected_response) as mock_request:
            
            result = await client.quick_add_event("primary", "Meeting with John tomorrow 2pm")
            
            assert result == expected_response
            mock_request.assert_called_once_with(
                "POST", 
                "/calendars/primary/events/quickAdd",
                params={"text": "Meeting with John tomorrow 2pm"}
            )
    
    @pytest.mark.asyncio
    async def test_get_free_busy_success(self, client, mock_settings):
        """Test successful free/busy retrieval."""
        expected_response = {
            "calendars": {
                "primary": {
                    "busy": [
                        {
                            "start": "2025-01-20T10:00:00Z",
                            "end": "2025-01-20T11:00:00Z"
                        }
                    ]
                }
            }
        }
        
        with patch('workflow_engine.clients.google_calendar_client.get_settings', return_value=mock_settings), \
             patch.object(client, '_make_request', return_value=expected_response) as mock_request:
            
            result = await client.get_free_busy(
                ["primary"], 
                "2025-01-20T00:00:00Z", 
                "2025-01-21T00:00:00Z"
            )
            
            assert result == expected_response
            
            # Verify request data
            args, kwargs = mock_request.call_args
            assert args[0] == "POST"
            assert args[1] == "/freeBusy"
            assert kwargs["json"]["timeMin"] == "2025-01-20T00:00:00Z"
            assert kwargs["json"]["timeMax"] == "2025-01-21T00:00:00Z"
            assert kwargs["json"]["items"] == [{"id": "primary"}]
    
    @pytest.mark.asyncio
    async def test_error_handling_google_calendar_error(self, client, mock_settings):
        """Test Google Calendar specific error handling."""
        with patch('workflow_engine.clients.google_calendar_client.get_settings', return_value=mock_settings), \
             patch.object(client, '_make_request', side_effect=Exception("API Error")):
            
            with pytest.raises(GoogleCalendarError, match="Failed to list calendars: API Error"):
                await client.list_calendars()
    
    @pytest.mark.asyncio
    async def test_client_close(self, client):
        """Test client resource cleanup."""
        # Mock HTTP client
        mock_http_client = AsyncMock()
        client._http_client = mock_http_client
        
        await client.close()
        
        mock_http_client.aclose.assert_called_once()
        assert client._http_client is None


class TestGoogleCalendarClientIntegration:
    """Integration tests for GoogleCalendarClient."""
    
    @pytest.mark.asyncio
    async def test_token_refresh_integration(self):
        """Test automatic token refresh integration."""
        # Create expired credentials
        expired_credentials = OAuth2Credential(
            access_token="expired_token",
            refresh_token="refresh_token",
            token_type="Bearer",
            expires_at=datetime.utcnow() - timedelta(minutes=1),  # Expired
            provider="google_calendar"
        )
        
        client = GoogleCalendarClient(expired_credentials)
        
        # Mock the OAuth2 handler for token refresh
        mock_oauth2_handler = AsyncMock()
        new_credential = OAuth2Credential(
            access_token="new_access_token",
            refresh_token="new_refresh_token",
            token_type="Bearer",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            provider="google_calendar"
        )
        mock_oauth2_handler.refresh_access_token.return_value = new_credential
        
        with patch('workflow_engine.clients.google_calendar_client.get_settings') as mock_settings, \
             patch('workflow_engine.services.oauth2_handler.get_oauth2_handler', return_value=mock_oauth2_handler), \
             patch.object(client, '_make_request', return_value={"items": []}) as mock_request:
            
            mock_settings.return_value.api_timeout_connect = 5
            mock_settings.return_value.api_timeout_read = 30
            mock_settings.return_value.api_max_retries = 3
            mock_settings.return_value.get_retry_delays.return_value = [2, 4, 8]
            
            # This should trigger token refresh
            await client.list_calendars()
            
            # Verify token was refreshed
            assert client.credentials.access_token == "new_access_token"
            mock_oauth2_handler.refresh_access_token.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__]) 