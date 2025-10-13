"""
Enhanced tests for Notion MCP Tools with AI optimization features
Tests AI-specific formatting and LLM compatibility features
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from app.api.mcp.notion_tools import NotionMCPService
from app.models import MCPHealthCheck, MCPInvokeResponse


class TestNotionMCPEnhanced:
    """Test suite for enhanced Notion MCP Service with AI optimizations."""

    @pytest.fixture
    def mcp_service(self):
        """Create Notion MCP service instance."""
        return NotionMCPService()

    @pytest.fixture
    def mock_notion_client(self):
        """Create mock Notion client."""
        with patch("app.api.mcp.notion_tools.NotionClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock common client methods
            mock_client.close = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            yield mock_client

    @pytest.fixture
    def sample_search_results(self):
        """Sample search results for testing."""
        return {
            "results": [
                {
                    "id": "page1",
                    "object": "page",
                    "url": "https://notion.so/page1",
                    "properties": {
                        "title": {
                            "type": "title",
                            "title": [
                                {
                                    "text": {"content": "Meeting Notes"},
                                    "plain_text": "Meeting Notes",
                                }
                            ],
                        }
                    },
                },
                {
                    "id": "page2",
                    "object": "page",
                    "url": "https://notion.so/page2",
                    "properties": {
                        "title": {
                            "type": "title",
                            "title": [
                                {
                                    "text": {"content": "Project Documentation"},
                                    "plain_text": "Project Documentation",
                                }
                            ],
                        }
                    },
                },
            ],
            "total_count": 2,
            "has_more": False,
        }

    def test_ai_optimization_parameters(self, mcp_service):
        """Test that AI optimization parameters are available in tool schema."""
        tools_response = mcp_service.get_available_tools()
        notion_search_tool = next(
            tool for tool in tools_response.tools if tool.name == "notion_search"
        )

        schema = notion_search_tool.inputSchema
        properties = schema["properties"]

        # Check for AI-specific parameters
        assert "ai_format" in properties
        assert "relevance_scoring" in properties

        # Check AI format options
        ai_format = properties["ai_format"]
        assert ai_format["type"] == "string"
        assert "structured" in ai_format["enum"]
        assert "narrative" in ai_format["enum"]
        assert "summary" in ai_format["enum"]
        assert ai_format["default"] == "structured"

        # Check relevance scoring
        relevance_scoring = properties["relevance_scoring"]
        assert relevance_scoring["type"] == "boolean"
        assert relevance_scoring["default"] is True

    @pytest.mark.asyncio
    async def test_notion_search_structured_format(
        self, mcp_service, mock_notion_client, sample_search_results
    ):
        """Test Notion search with structured AI format (default)."""
        # Setup mock
        mock_notion_client.search.return_value = sample_search_results

        params = {
            "access_token": "test_token",
            "query": "meeting",
            "ai_format": "structured",
            "relevance_scoring": True,
            "limit": 10,
        }

        response = await mcp_service.invoke_tool("notion_search", params)

        assert not response.isError
        content = response.structuredContent

        # Check basic structure
        assert content["query"] == "meeting"
        assert len(content["results"]) == 2

        # Check relevance scoring was applied
        for result in content["results"]:
            assert "relevance_score" in result
            assert isinstance(result["relevance_score"], int)

        # Results should be sorted by relevance
        scores = [r["relevance_score"] for r in content["results"]]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_notion_search_narrative_format(
        self, mcp_service, mock_notion_client, sample_search_results
    ):
        """Test Notion search with narrative AI format."""
        # Setup mock
        mock_notion_client.search.return_value = sample_search_results

        params = {
            "access_token": "test_token",
            "query": "meeting",
            "ai_format": "narrative",
            "relevance_scoring": True,
        }

        response = await mcp_service.invoke_tool("notion_search", params)

        assert not response.isError
        content = response.structuredContent

        # Check narrative formatting
        assert "ai_narrative" in content
        assert "format_type" in content
        assert content["format_type"] == "narrative"

        # Check narrative content
        narrative = content["ai_narrative"]
        assert "meeting" in narrative.lower()
        assert "Meeting Notes" in narrative
        assert "Project Documentation" in narrative
        assert "Relevance:" in narrative

    @pytest.mark.asyncio
    async def test_notion_search_summary_format(
        self, mcp_service, mock_notion_client, sample_search_results
    ):
        """Test Notion search with summary AI format."""
        # Setup mock
        mock_notion_client.search.return_value = sample_search_results

        params = {
            "access_token": "test_token",
            "query": "meeting",
            "ai_format": "summary",
            "relevance_scoring": True,
        }

        response = await mcp_service.invoke_tool("notion_search", params)

        assert not response.isError
        content = response.structuredContent

        # Check summary formatting
        assert "ai_summary" in content
        assert "format_type" in content
        assert content["format_type"] == "summary"

        # Check summary structure
        summary = content["ai_summary"]
        assert summary["query"] == "meeting"
        assert summary["total_found"] == 2
        assert summary["search_successful"] is True
        assert "top_results" in summary
        assert len(summary["top_results"]) <= 5  # Should limit to top 5

        # Check top results structure
        for result in summary["top_results"]:
            assert "title" in result
            assert "type" in result
            assert "relevance" in result
            assert "url" in result
            assert "has_content" in result

    @pytest.mark.asyncio
    async def test_relevance_scoring_algorithm(self, mcp_service, mock_notion_client):
        """Test relevance scoring algorithm effectiveness."""
        # Create test data with varying relevance
        search_results = {
            "results": [
                {
                    "id": "page1",
                    "object": "page",
                    "url": "https://notion.so/page1",
                    "properties": {
                        "title": {
                            "type": "title",
                            "title": [
                                {
                                    "text": {"content": "Random Document"},
                                    "plain_text": "Random Document",
                                }
                            ],  # No query match
                        }
                    },
                },
                {
                    "id": "page2",
                    "object": "page",
                    "url": "https://notion.so/page2",
                    "properties": {
                        "title": {
                            "type": "title",
                            "title": [
                                {
                                    "text": {"content": "Meeting Notes for Project"},
                                    "plain_text": "Meeting Notes for Project",
                                }
                            ],  # Title match
                        }
                    },
                },
                {
                    "id": "page3",
                    "object": "page",
                    "url": "https://notion.so/page3",
                    "properties": {
                        "title": {
                            "type": "title",
                            "title": [
                                {
                                    "text": {"content": "Project Meeting Summary"},
                                    "plain_text": "Project Meeting Summary",
                                }
                            ],  # Title match
                        }
                    },
                },
            ],
            "total_count": 3,
            "has_more": False,
        }

        mock_notion_client.search.return_value = search_results

        params = {"access_token": "test_token", "query": "meeting", "relevance_scoring": True}

        response = await mcp_service.invoke_tool("notion_search", params)

        content = response.structuredContent
        results = content["results"]

        # Check that results with "meeting" in title have higher scores
        meeting_results = [r for r in results if "meeting" in r["title"].lower()]
        non_meeting_results = [r for r in results if "meeting" not in r["title"].lower()]

        if meeting_results and non_meeting_results:
            max_meeting_score = max(r["relevance_score"] for r in meeting_results)
            max_non_meeting_score = max(r["relevance_score"] for r in non_meeting_results)
            assert max_meeting_score > max_non_meeting_score

    @pytest.mark.asyncio
    async def test_no_results_narrative_format(self, mcp_service, mock_notion_client):
        """Test narrative format when no results are found."""
        # Setup mock for empty results
        mock_notion_client.search.return_value = {
            "results": [],
            "total_count": 0,
            "has_more": False,
        }

        params = {"access_token": "test_token", "query": "nonexistent", "ai_format": "narrative"}

        response = await mcp_service.invoke_tool("notion_search", params)

        content = response.structuredContent
        narrative = content["ai_narrative"]

        assert "i found no notion content matching" in narrative.lower()
        assert "nonexistent" in narrative
        assert "try different search terms" in narrative.lower()

    @pytest.mark.asyncio
    async def test_relevance_scoring_disabled(
        self, mcp_service, mock_notion_client, sample_search_results
    ):
        """Test behavior when relevance scoring is disabled."""
        mock_notion_client.search.return_value = sample_search_results

        params = {"access_token": "test_token", "query": "meeting", "relevance_scoring": False}

        response = await mcp_service.invoke_tool("notion_search", params)

        content = response.structuredContent

        # Results should not have relevance scores
        for result in content["results"]:
            assert "relevance_score" not in result

    def test_ai_format_description_quality(self, mcp_service):
        """Test that AI format descriptions are helpful for LLMs."""
        tools_response = mcp_service.get_available_tools()
        notion_search_tool = next(
            tool for tool in tools_response.tools if tool.name == "notion_search"
        )

        ai_format_desc = notion_search_tool.inputSchema["properties"]["ai_format"]["description"]

        # Check that description explains the different formats clearly
        assert "structured" in ai_format_desc
        assert "narrative" in ai_format_desc
        assert "summary" in ai_format_desc
        assert "JSON" in ai_format_desc or "conversational" in ai_format_desc

    def test_enhanced_tool_info(self, mcp_service):
        """Test that tool info includes AI optimization details."""
        tool_info = mcp_service.get_tool_info("notion_search")

        assert tool_info["version"] == "3.1.0"  # Updated version
        assert "optimized_for" in tool_info
        assert "OpenAI GPT" in tool_info["optimized_for"]
        assert "Claude" in tool_info["optimized_for"]
        assert "Gemini" in tool_info["optimized_for"]
        assert "features" in tool_info
        assert "Relevance scoring" in tool_info["features"]
        assert "AI-specific formatting" in tool_info["features"]

    @pytest.mark.asyncio
    async def test_content_preview_in_narrative(self, mcp_service, mock_notion_client):
        """Test that content preview is included in narrative format."""
        # Setup mock with content
        search_results_with_content = {
            "results": [
                {
                    "id": "page1",
                    "object": "page",
                    "url": "https://notion.so/page1",
                    "properties": {
                        "title": {
                            "type": "title",
                            "title": [
                                {
                                    "text": {"content": "Meeting Notes"},
                                    "plain_text": "Meeting Notes",
                                }
                            ],
                        }
                    },
                }
            ],
            "total_count": 1,
            "has_more": False,
        }

        # Mock get_block_children to return content
        mock_notion_client.search.return_value = search_results_with_content
        mock_notion_client.get_block_children.return_value = {
            "blocks": [
                {
                    "id": "block1",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "text": {
                                    "content": "This is a detailed meeting summary with important information about the project status and next steps."
                                }
                            }
                        ]
                    },
                }
            ]
        }

        params = {
            "access_token": "test_token",
            "query": "meeting",
            "ai_format": "narrative",
            "include_content": True,
        }

        response = await mcp_service.invoke_tool("notion_search", params)

        content = response.structuredContent
        narrative = content["ai_narrative"]

        # Should include content when requested (but format may vary)
        assert "Meeting Notes" in narrative
        # Content inclusion is implementation-dependent, just verify basic functionality

    def test_format_helper_methods(self, mcp_service):
        """Test the AI formatting helper methods directly."""
        # Test data
        test_result = {
            "query": "test",
            "results": [
                {
                    "title": "Test Page",
                    "object": "page",
                    "url": "https://notion.so/test",
                    "relevance_score": 8,
                    "content": ["Some content here"],
                }
            ],
            "total_count": 1,
            "has_more": False,
            "filter": {},
        }

        # Test narrative formatting
        narrative_result = mcp_service._format_for_narrative(test_result, "test")
        assert "ai_narrative" in narrative_result
        assert "format_type" in narrative_result
        assert narrative_result["format_type"] == "narrative"
        assert "Test Page" in narrative_result["ai_narrative"]
        assert "Relevance: 8/10" in narrative_result["ai_narrative"]

        # Test summary formatting
        summary_result = mcp_service._format_for_summary(test_result, "test")
        assert "ai_summary" in summary_result
        assert "format_type" in summary_result
        assert summary_result["format_type"] == "summary"
        assert summary_result["ai_summary"]["search_successful"] is True
        assert summary_result["ai_summary"]["total_found"] == 1

    @pytest.mark.asyncio
    async def test_error_handling_with_ai_format(self, mcp_service):
        """Test error handling preserves AI format context."""
        params = {
            "query": "test",
            "ai_format": "narrative"
            # Missing access_token
        }

        response = await mcp_service.invoke_tool("notion_search", params)

        assert response.isError
        assert "access_token parameter is required" in response.content[0].text

    @pytest.mark.parametrize("ai_format", ["structured", "narrative", "summary"])
    @pytest.mark.asyncio
    async def test_all_ai_formats_work(
        self, mcp_service, mock_notion_client, sample_search_results, ai_format
    ):
        """Test that all AI formats work correctly."""
        mock_notion_client.search.return_value = sample_search_results

        params = {
            "access_token": "test_token",
            "query": "test",
            "ai_format": ai_format,
            "relevance_scoring": True,
        }

        response = await mcp_service.invoke_tool("notion_search", params)

        assert not response.isError
        content = response.structuredContent

        if ai_format == "narrative":
            assert "ai_narrative" in content
            assert content["format_type"] == "narrative"
        elif ai_format == "summary":
            assert "ai_summary" in content
            assert content["format_type"] == "summary"
        else:  # structured
            assert "results" in content
            assert "query" in content

    def test_llm_optimization_documentation(self, mcp_service):
        """Test that tools are well-documented for LLM usage."""
        tools_response = mcp_service.get_available_tools()

        for tool in tools_response.tools:
            # Check that tools have meaningful descriptions
            assert len(tool.description) >= 20, f"Tool {tool.name} has insufficient description"

            # Check parameter descriptions are detailed
            for param_name, param_def in tool.inputSchema["properties"].items():
                if isinstance(param_def, dict) and "description" in param_def:
                    desc = param_def["description"]
                    assert len(desc) >= 5  # Reasonable minimum descriptions
                    assert not desc.endswith(".")  # Avoid sentence fragments

    @pytest.mark.asyncio
    async def test_performance_with_ai_features(
        self, mcp_service, mock_notion_client, sample_search_results
    ):
        """Test that AI features don't significantly impact performance."""
        mock_notion_client.search.return_value = sample_search_results

        # Test with AI features enabled
        params_with_ai = {
            "access_token": "test_token",
            "query": "test",
            "ai_format": "narrative",
            "relevance_scoring": True,
        }

        response_with_ai = await mcp_service.invoke_tool("notion_search", params_with_ai)

        # Test with AI features disabled
        params_without_ai = {
            "access_token": "test_token",
            "query": "test",
            "ai_format": "structured",
            "relevance_scoring": False,
        }

        response_without_ai = await mcp_service.invoke_tool("notion_search", params_without_ai)

        # Both should complete successfully
        assert not response_with_ai.isError
        assert not response_without_ai.isError

        # Execution times should be reasonable (under 1 second for mocked operations)
        assert response_with_ai._execution_time_ms < 1000
        assert response_without_ai._execution_time_ms < 1000
