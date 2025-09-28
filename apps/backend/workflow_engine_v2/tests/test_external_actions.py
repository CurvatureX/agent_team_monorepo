"""
Test external action implementations for workflow_engine_v2.
"""
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models import ExecutionStatus, NodeExecutionResult
from shared.models.node_enums import ExternalActionSubtype, NodeType
from shared.models.workflow_new import Node
from workflow_engine_v2.runners.external_actions.github_external_action import GitHubExternalAction
from workflow_engine_v2.runners.external_actions.google_calendar_external_action import (
    GoogleCalendarExternalAction,
)
from workflow_engine_v2.runners.external_actions.notion_external_action import NotionExternalAction
from workflow_engine_v2.runners.external_actions.slack_external_action import SlackExternalAction


@pytest.fixture
def sample_node():
    """Create a sample node for testing."""
    return Node(
        id="test_node",
        name="test_external_action",
        description="Test node for external action testing",
        type=NodeType.EXTERNAL_ACTION.value,
        subtype=ExternalActionSubtype.SLACK.value,
        configurations={
            "action_type": "send_message",
            "channel": "general",
            "message": "Test message",
        },
    )


@pytest.fixture
def mock_context(sample_node):
    """Create mock execution context."""
    context = MagicMock()
    context.execution_id = "exec_123"
    context.node = sample_node
    context.input_data = {"main": {"text": "Test input"}}
    context.workflow_id = "workflow_123"
    context.execution = {"user_id": "test_user_123"}
    return context


class TestSlackExternalAction:
    """Test Slack external action implementation."""

    @pytest.fixture
    def slack_action(self):
        return SlackExternalAction()

    @pytest.mark.asyncio
    async def test_send_message_success(self, slack_action, mock_context):
        """Test successful Slack message sending."""
        mock_context.node.configurations = {
            "action_type": "send_message",
            "channel": "general",
            "message": "Hello Slack!",
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"ok": True, "message": {"ts": "1234567890.123456"}}
            mock_client.post.return_value = mock_response

            with patch.object(
                slack_action.oauth_service,
                "get_valid_token",
                new_callable=AsyncMock,
                return_value="slack_token",
            ):
                result = await slack_action.execute(mock_context)

                assert isinstance(result, NodeExecutionResult)
                assert result.status == ExecutionStatus.SUCCESS
                assert "message_timestamp" in result.output_data["main"]

    @pytest.mark.asyncio
    async def test_list_channels_success(self, slack_action, mock_context):
        """Test successful Slack channel listing."""
        mock_context.node.configurations = {"action_type": "list_channels"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "ok": True,
                "channels": [
                    {"id": "C1234567890", "name": "general", "is_private": False},
                    {"id": "C0987654321", "name": "random", "is_private": False},
                ],
            }
            mock_client.get.return_value = mock_response

            with patch.object(
                slack_action.oauth_service,
                "get_valid_token",
                new_callable=AsyncMock,
                return_value="slack_token",
            ):
                result = await slack_action.execute(mock_context)

                assert result.status == ExecutionStatus.SUCCESS
                assert len(result.output_data["main"]["channels"]) == 2
                assert result.output_data["main"]["channels"][0]["name"] == "general"

    @pytest.mark.asyncio
    async def test_missing_oauth_token(self, slack_action, mock_context):
        """Test handling of missing OAuth token."""
        with patch.object(
            slack_action.oauth_service, "get_valid_token", new_callable=AsyncMock, return_value=None
        ):
            result = await slack_action.execute(mock_context)

            assert result.status == ExecutionStatus.ERROR
            assert "missing_oauth_token" in result.error_details["reason"]


class TestGitHubExternalAction:
    """Test GitHub external action implementation."""

    @pytest.fixture
    def github_action(self):
        return GitHubExternalAction()

    @pytest.mark.asyncio
    async def test_create_issue_success(self, github_action, mock_context):
        """Test successful GitHub issue creation."""
        mock_context.node.configurations = {
            "action_type": "create_issue",
            "repo_owner": "testuser",
            "repo_name": "testrepo",
            "title": "Test Issue",
            "body": "This is a test issue",
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.json.return_value = {
                "number": 42,
                "title": "Test Issue",
                "html_url": "https://github.com/testuser/testrepo/issues/42",
            }
            mock_client.post.return_value = mock_response

            with patch.object(
                github_action.oauth_service,
                "get_valid_token",
                new_callable=AsyncMock,
                return_value="github_token",
            ):
                result = await github_action.execute(mock_context)

                assert result.status == ExecutionStatus.SUCCESS
                assert result.output_data["main"]["issue_number"] == 42
                assert "html_url" in result.output_data["main"]

    @pytest.mark.asyncio
    async def test_create_pr_success(self, github_action, mock_context):
        """Test successful GitHub PR creation."""
        mock_context.node.configurations = {
            "action_type": "create_pr",
            "repo_owner": "testuser",
            "repo_name": "testrepo",
            "title": "Test PR",
            "body": "This is a test PR",
            "head": "feature-branch",
            "base": "main",
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.json.return_value = {
                "number": 123,
                "title": "Test PR",
                "html_url": "https://github.com/testuser/testrepo/pull/123",
            }
            mock_client.post.return_value = mock_response

            with patch.object(
                github_action.oauth_service,
                "get_valid_token",
                new_callable=AsyncMock,
                return_value="github_token",
            ):
                result = await github_action.execute(mock_context)

                assert result.status == ExecutionStatus.SUCCESS
                assert result.output_data["main"]["pr_number"] == 123


class TestGoogleCalendarExternalAction:
    """Test Google Calendar external action implementation."""

    @pytest.fixture
    def calendar_action(self):
        return GoogleCalendarExternalAction()

    @pytest.mark.asyncio
    async def test_create_event_success(self, calendar_action, mock_context):
        """Test successful Google Calendar event creation."""
        mock_context.node.configurations = {
            "action_type": "create_event",
            "calendar_id": "primary",
            "summary": "Test Event",
            "start_time": "2024-01-01T10:00:00Z",
            "end_time": "2024-01-01T11:00:00Z",
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "id": "event_123",
                "summary": "Test Event",
                "htmlLink": "https://calendar.google.com/event?eid=event_123",
            }
            mock_client.post.return_value = mock_response

            with patch.object(
                calendar_action.oauth_service,
                "get_valid_token",
                new_callable=AsyncMock,
                return_value="google_token",
            ):
                result = await calendar_action.execute(mock_context)

                assert result.status == ExecutionStatus.SUCCESS
                assert result.output_data["main"]["event_id"] == "event_123"
                assert "htmlLink" in result.output_data["main"]

    @pytest.mark.asyncio
    async def test_list_events_success(self, calendar_action, mock_context):
        """Test successful Google Calendar event listing."""
        mock_context.node.configurations = {"action_type": "list_events", "calendar_id": "primary"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "items": [
                    {"id": "event1", "summary": "Meeting 1"},
                    {"id": "event2", "summary": "Meeting 2"},
                ]
            }
            mock_client.get.return_value = mock_response

            with patch.object(
                calendar_action.oauth_service,
                "get_valid_token",
                new_callable=AsyncMock,
                return_value="google_token",
            ):
                result = await calendar_action.execute(mock_context)

                assert result.status == ExecutionStatus.SUCCESS
                assert len(result.output_data["main"]["events"]) == 2


class TestNotionExternalAction:
    """Test Notion external action implementation."""

    @pytest.fixture
    def notion_action(self):
        return NotionExternalAction()

    @pytest.mark.asyncio
    async def test_search_success(self, notion_action, mock_context):
        """Test successful Notion search."""
        mock_context.node.configurations = {"action_type": "search", "query": "test query"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "results": [
                    {"id": "page1", "object": "page", "properties": {"title": "Page 1"}},
                    {"id": "page2", "object": "page", "properties": {"title": "Page 2"}},
                ]
            }
            mock_client.post.return_value = mock_response

            with patch.object(
                notion_action.oauth_service,
                "get_valid_token",
                new_callable=AsyncMock,
                return_value="notion_token",
            ):
                result = await notion_action.execute(mock_context)

                assert result.status == ExecutionStatus.SUCCESS
                assert len(result.output_data["main"]["results"]) == 2

    @pytest.mark.asyncio
    async def test_create_page_success(self, notion_action, mock_context):
        """Test successful Notion page creation."""
        mock_context.node.configurations = {
            "action_type": "create_page",
            "parent_page_id": "parent_123",
            "title": "New Page",
            "content": "This is the content",
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "id": "new_page_123",
                "url": "https://notion.so/new_page_123",
                "properties": {"title": "New Page"},
            }
            mock_client.post.return_value = mock_response

            with patch.object(
                notion_action.oauth_service,
                "get_valid_token",
                new_callable=AsyncMock,
                return_value="notion_token",
            ):
                result = await notion_action.execute(mock_context)

                assert result.status == ExecutionStatus.SUCCESS
                assert result.output_data["main"]["page_id"] == "new_page_123"
                assert "url" in result.output_data["main"]


class TestExternalActionError:
    """Test error handling in external actions."""

    @pytest.fixture
    def slack_action(self):
        return SlackExternalAction()

    @pytest.mark.asyncio
    async def test_unsupported_action_type(self, slack_action, mock_context):
        """Test handling of unsupported action type."""
        mock_context.node.configurations = {"action_type": "unsupported_action"}

        result = await slack_action.execute(mock_context)
        assert result.status == ExecutionStatus.ERROR
        assert "unsupported_action_type" in result.error_details["reason"]

    @pytest.mark.asyncio
    async def test_api_request_failure(self, slack_action, mock_context):
        """Test handling of API request failures."""
        mock_context.node.configurations = {
            "action_type": "send_message",
            "channel": "general",
            "message": "Test",
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_client.post.return_value = mock_response

            with patch.object(
                slack_action.oauth_service,
                "get_valid_token",
                new_callable=AsyncMock,
                return_value="slack_token",
            ):
                result = await slack_action.execute(mock_context)

                assert result.status == ExecutionStatus.ERROR
                assert result.error_message is not None
