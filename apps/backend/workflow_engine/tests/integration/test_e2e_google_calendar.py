"""
End-to-end integration tests for Google Calendar tool.

This module tests the complete Google Calendar integration flow including:
- OAuth2 credential management
- Calendar API operations
- Tool node execution
- Error handling and recovery
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from workflow_engine.clients.google_calendar_client import GoogleCalendarClient
from workflow_engine.services.credential_service import CredentialService
from workflow_engine.services.oauth2_handler import OAuth2Handler
from workflow_engine.nodes.tool_node import ToolNodeExecutor
from workflow_engine.models.credential import OAuth2Credential
from workflow_engine.core.config import get_settings
from workflow_engine.nodes.base import NodeExecutionContext


@pytest.fixture
def mock_valid_credentials():
    """Create valid mock OAuth2 credentials for Google Calendar."""
    credentials = OAuth2Credential()
    credentials.provider = "google_calendar"
    credentials.access_token = "test_access_token"
    credentials.refresh_token = "test_refresh_token"
    credentials.expires_at = int((datetime.now() + timedelta(hours=1)).timestamp())
    credentials.credential_data = {
        "token_type": "Bearer",
        "scope": "https://www.googleapis.com/auth/calendar.events"
    }
    return credentials


@pytest.fixture
def mock_expired_credentials():
    """Create expired mock OAuth2 credentials."""
    credentials = OAuth2Credential()
    credentials.provider = "google_calendar"
    credentials.access_token = "expired_access_token"
    credentials.refresh_token = "test_refresh_token"
    credentials.expires_at = int((datetime.now() - timedelta(hours=1)).timestamp())
    return credentials


class TestGoogleCalendarE2E:
    """End-to-end tests for Google Calendar integration."""
    
    @pytest.mark.asyncio
    async def test_complete_calendar_event_lifecycle(self, mock_valid_credentials):
        """Test complete event lifecycle: create, list, update, delete."""
        
        # Mock Google Calendar API responses
        created_event = {
            "id": "test_event_123",
            "summary": "Test Meeting",
            "start": {"dateTime": "2025-01-20T10:00:00Z"},
            "end": {"dateTime": "2025-01-20T11:00:00Z"},
            "htmlLink": "https://calendar.google.com/event?eid=test123"
        }
        
        updated_event = {**created_event, "summary": "Updated Test Meeting"}
        
        events_list = {
            "items": [created_event],
            "nextPageToken": None
        }
        
        with patch.object(GoogleCalendarClient, '_make_request') as mock_request:
            # Set up mock responses for different operations
            mock_request.side_effect = [
                created_event,  # create_event
                events_list,    # list_events
                updated_event,  # update_event
                {}              # delete_event
            ]
            
            client = GoogleCalendarClient(mock_valid_credentials)
            
            # Test 1: Create event
            event_data = {
                "summary": "Test Meeting",
                "start": {"dateTime": "2025-01-20T10:00:00Z"},
                "end": {"dateTime": "2025-01-20T11:00:00Z"}
            }
            
            result = await client.create_event("primary", event_data)
            assert result["id"] == "test_event_123"
            assert result["summary"] == "Test Meeting"
            
            # Test 2: List events
            events = await client.list_events(
                "primary",
                "2025-01-20T00:00:00Z",
                "2025-01-20T23:59:59Z"
            )
            assert len(events) == 1
            assert events[0]["id"] == "test_event_123"
            
            # Test 3: Update event
            updated_data = {**event_data, "summary": "Updated Test Meeting"}
            result = await client.update_event("primary", "test_event_123", updated_data)
            assert result["summary"] == "Updated Test Meeting"
            
            # Test 4: Delete event
            result = await client.delete_event("primary", "test_event_123")
            assert result == {}
            
            # Verify all API calls were made
            assert mock_request.call_count == 4
    
    @pytest.mark.asyncio
    async def test_oauth2_token_refresh_flow(self, mock_expired_credentials):
        """Test automatic token refresh when credentials are expired."""
        
        refreshed_credentials = OAuth2Credential()
        refreshed_credentials.provider = "google_calendar"
        refreshed_credentials.access_token = "new_access_token"
        refreshed_credentials.refresh_token = "test_refresh_token"
        refreshed_credentials.expires_at = int((datetime.now() + timedelta(hours=1)).timestamp())
        
        with patch.object(GoogleCalendarClient, '_refresh_credentials_if_needed') as mock_refresh:
            mock_refresh.return_value = refreshed_credentials
            
            with patch.object(GoogleCalendarClient, '_make_request') as mock_request:
                mock_request.return_value = {"id": "test_event"}
                
                client = GoogleCalendarClient(mock_expired_credentials)
                
                # This should trigger token refresh
                await client.create_event("primary", {
                    "summary": "Test Event",
                    "start": {"dateTime": "2025-01-20T10:00:00Z"},
                    "end": {"dateTime": "2025-01-20T11:00:00Z"}
                })
                
                # Verify refresh was called
                mock_refresh.assert_called_once()
                
                # Verify API call was made with refreshed credentials
                mock_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_tool_node_calendar_execution(self, mock_valid_credentials):
        """Test Google Calendar tool execution through ToolNodeExecutor."""
        
        # Mock credential service
        mock_credential_service = AsyncMock(spec=CredentialService)
        mock_credential_service.get_credential.return_value = mock_valid_credentials
        
        # Mock Google Calendar API response
        api_response = {
            "id": "tool_test_event",
            "summary": "Tool Test Event",
            "start": {"dateTime": "2025-01-20T14:00:00Z"},
            "end": {"dateTime": "2025-01-20T15:00:00Z"}
        }
        
        with patch('workflow_engine.services.credential_service.CredentialService', return_value=mock_credential_service):
            with patch.object(GoogleCalendarClient, '_make_request', return_value=api_response) as mock_request:
                
                # Create mock execution context
                context = MagicMock(spec=NodeExecutionContext)
                context.get_parameter.side_effect = lambda key, default=None: {
                    "provider": "google_calendar",
                    "action": "create_event",
                    "calendar_id": "primary",
                    "user_id": "test_user"
                }.get(key, default)
                
                context.input_data = {
                    "summary": "Tool Test Event",
                    "start": {"dateTime": "2025-01-20T14:00:00Z"},
                    "end": {"dateTime": "2025-01-20T15:00:00Z"},
                    "description": "Created via tool node"
                }
                
                # Execute tool
                executor = ToolNodeExecutor()
                result = executor._execute_calendar_tool(context, [], 0.0)
                
                # Verify result
                assert result.status.value == "SUCCESS"
                assert "tool_type" in result.output_data
                assert result.output_data["tool_type"] == "calendar"
                assert result.output_data["action"] == "create_event"
                
                # Verify credential was retrieved
                mock_credential_service.get_credential.assert_called_once_with("test_user", "google_calendar")
                
                # Verify API was called
                mock_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_calendar_error_handling_and_retry(self, mock_valid_credentials):
        """Test error handling and retry mechanism for Calendar API."""
        
        # Mock initial failures followed by success
        responses = [
            Exception("500 Internal Server Error"),  # First attempt fails
            Exception("503 Service Unavailable"),    # Second attempt fails
            {"id": "retry_success_event"}            # Third attempt succeeds
        ]
        
        with patch.object(GoogleCalendarClient, '_make_request') as mock_request:
            mock_request.side_effect = responses
            
            client = GoogleCalendarClient(mock_valid_credentials)
            
            # This should retry and eventually succeed
            with patch('asyncio.sleep'):  # Speed up the test
                result = await client.create_event("primary", {
                    "summary": "Retry Test Event",
                    "start": {"dateTime": "2025-01-20T16:00:00Z"},
                    "end": {"dateTime": "2025-01-20T17:00:00Z"}
                })
            
            assert result["id"] == "retry_success_event"
            assert mock_request.call_count == 3  # Should have retried 3 times
    
    @pytest.mark.asyncio
    async def test_multi_calendar_support(self, mock_valid_credentials):
        """Test operations on multiple calendars."""
        
        # Mock responses for different calendars
        calendar_responses = {
            "primary": {"id": "primary_event"},
            "work_calendar": {"id": "work_event"},
            "personal_calendar": {"id": "personal_event"}
        }
        
        with patch.object(GoogleCalendarClient, '_make_request') as mock_request:
            mock_request.side_effect = lambda method, url, **kwargs: {
                "/calendars/primary/events": calendar_responses["primary"],
                "/calendars/work_calendar/events": calendar_responses["work_calendar"],
                "/calendars/personal_calendar/events": calendar_responses["personal_calendar"]
            }.get(url, {})
            
            client = GoogleCalendarClient(mock_valid_credentials)
            
            # Test creating events in different calendars
            for calendar_id in ["primary", "work_calendar", "personal_calendar"]:
                result = await client.create_event(calendar_id, {
                    "summary": f"Event in {calendar_id}",
                    "start": {"dateTime": "2025-01-20T18:00:00Z"},
                    "end": {"dateTime": "2025-01-20T19:00:00Z"}
                })
                
                expected_id = calendar_responses[calendar_id]["id"]
                assert result["id"] == expected_id
            
            # Verify all calendar APIs were called
            assert mock_request.call_count == 3
    
    @pytest.mark.asyncio
    async def test_performance_benchmarks(self, mock_valid_credentials):
        """Test performance benchmarks for Calendar operations."""
        
        with patch.object(GoogleCalendarClient, '_make_request') as mock_request:
            mock_request.return_value = {"id": "perf_test_event"}
            
            client = GoogleCalendarClient(mock_valid_credentials)
            
            # Measure create_event performance
            start_time = datetime.now()
            
            await client.create_event("primary", {
                "summary": "Performance Test Event",
                "start": {"dateTime": "2025-01-20T20:00:00Z"},
                "end": {"dateTime": "2025-01-20T21:00:00Z"}
            })
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Performance should be under 5 seconds (excluding actual API latency)
            assert execution_time < 5.0
            
            # Test concurrent operations
            start_time = datetime.now()
            
            tasks = []
            for i in range(5):
                task = client.create_event("primary", {
                    "summary": f"Concurrent Event {i}",
                    "start": {"dateTime": "2025-01-20T22:00:00Z"},
                    "end": {"dateTime": "2025-01-20T23:00:00Z"}
                })
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            
            concurrent_time = (datetime.now() - start_time).total_seconds()
            
            # Concurrent execution should not significantly increase time
            assert concurrent_time < 10.0
            assert mock_request.call_count == 6  # 1 + 5 concurrent calls


class TestGoogleCalendarIntegrationErrors:
    """Test error scenarios and edge cases."""
    
    @pytest.mark.asyncio
    async def test_invalid_credentials_handling(self):
        """Test handling of invalid credentials."""
        
        invalid_credentials = OAuth2Credential()
        invalid_credentials.provider = "google_calendar"
        invalid_credentials.access_token = "invalid_token"
        
        with patch.object(GoogleCalendarClient, '_make_request') as mock_request:
            mock_request.side_effect = Exception("401 Unauthorized")
            
            client = GoogleCalendarClient(invalid_credentials)
            
            with pytest.raises(Exception) as exc_info:
                await client.create_event("primary", {
                    "summary": "Should Fail",
                    "start": {"dateTime": "2025-01-20T10:00:00Z"},
                    "end": {"dateTime": "2025-01-20T11:00:00Z"}
                })
            
            assert "401 Unauthorized" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_network_timeout_handling(self, mock_valid_credentials):
        """Test handling of network timeouts."""
        
        with patch.object(GoogleCalendarClient, '_make_request') as mock_request:
            mock_request.side_effect = Exception("Request timeout")
            
            client = GoogleCalendarClient(mock_valid_credentials)
            
            with pytest.raises(Exception) as exc_info:
                await client.create_event("primary", {
                    "summary": "Timeout Test",
                    "start": {"dateTime": "2025-01-20T10:00:00Z"},
                    "end": {"dateTime": "2025-01-20T11:00:00Z"}
                })
            
            assert "timeout" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio 
    async def test_malformed_event_data_handling(self, mock_valid_credentials):
        """Test handling of malformed event data."""
        
        client = GoogleCalendarClient(mock_valid_credentials)
        
        # Test missing required fields
        with pytest.raises(Exception):
            await client.create_event("primary", {})
        
        # Test invalid date format
        with pytest.raises(Exception):
            await client.create_event("primary", {
                "summary": "Invalid Date Test",
                "start": {"dateTime": "invalid-date"},
                "end": {"dateTime": "2025-01-20T11:00:00Z"}
            }) 