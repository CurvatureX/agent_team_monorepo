"""
Unit tests for MCP Tools Service
Tests the MCP service layer functionality
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
from app.api.mcp.tools import NodeKnowledgeMCPService


class TestNodeKnowledgeMCPService:
    """Test suite for NodeKnowledgeMCPService"""

    @pytest.fixture
    def mock_node_knowledge_service(self):
        """Create a mock NodeKnowledgeService"""
        service = Mock()

        # Mock get_node_types
        service.get_node_types.return_value = {
            "ACTION_NODE": ["HTTP_REQUEST", "RUN_CODE"],
            "AI_AGENT_NODE": ["OPENAI_NODE", "CLAUDE_NODE"],
            "FLOW_NODE": ["IF", "LOOP"],
        }

        # Mock get_node_details
        service.get_node_details.return_value = [
            {
                "node_type": "ACTION_NODE",
                "subtype": "HTTP_REQUEST",
                "version": "1.0.0",
                "description": "Make HTTP requests to external APIs",
                "parameters": [
                    {
                        "name": "url",
                        "type": "string",
                        "required": True,
                        "description": "Request URL",
                    }
                ],
                "input_ports": [],
                "output_ports": [],
                "examples": [{"name": "test"}],
            }
        ]

        # Mock registry availability
        service.registry = Mock()

        return service

    @pytest.fixture
    def mcp_service(self, mock_node_knowledge_service):
        """Create MCP service with mocked dependencies"""
        with patch(
            "app.api.mcp.tools.NodeKnowledgeService", return_value=mock_node_knowledge_service
        ):
            service = NodeKnowledgeMCPService()
            return service

    @pytest.fixture
    def mcp_service_no_registry(self):
        """Create MCP service without registry"""
        mock_service = Mock()
        mock_service.registry = None

        with patch("app.api.mcp.tools.NodeKnowledgeService", return_value=mock_service):
            service = NodeKnowledgeMCPService()
            return service

    def test_init(self, mcp_service):
        """Test MCP service initialization"""
        assert mcp_service.node_knowledge is not None

    def test_get_available_tools(self, mcp_service):
        """Test getting available MCP tools"""
        result = mcp_service.get_available_tools()

        assert result.success is True
        assert len(result.tools) == 2
        assert result.total_count == 2
        assert result.available_count == 2

        tool_names = [tool.name for tool in result.tools]
        assert "get_node_types" in tool_names
        assert "get_node_details" in tool_names

        # Check tool categories
        assert "workflow" in result.categories

    def test_get_available_tools_structure(self, mcp_service):
        """Test the structure of available tools"""
        result = mcp_service.get_available_tools()

        for tool in result.tools:
            assert hasattr(tool, "name")
            assert hasattr(tool, "description")
            assert hasattr(tool, "inputSchema")
            assert hasattr(tool, "category")
            assert hasattr(tool, "tags")

            # Check parameters structure
            assert "type" in tool.inputSchema
            assert "properties" in tool.inputSchema
            assert tool.inputSchema["type"] == "object"

    @pytest.mark.asyncio
    async def test_invoke_get_node_types(self, mcp_service):
        """Test invoking get_node_types tool"""
        result = await mcp_service.invoke_tool("get_node_types", {})

        assert result.isError is False
        assert result._tool_name == "get_node_types"
        assert result.structuredContent is not None
        assert isinstance(result.structuredContent, dict)
        assert "ACTION_NODE" in result.structuredContent
        assert result._execution_time_ms is not None
        assert result._execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_invoke_get_node_types_with_filter(self, mcp_service):
        """Test invoking get_node_types with filter"""
        # Configure mock to return filtered results
        mcp_service.node_knowledge.get_node_types.return_value = {
            "ACTION_NODE": ["HTTP_REQUEST", "RUN_CODE"]
        }

        result = await mcp_service.invoke_tool("get_node_types", {"type_filter": "ACTION_NODE"})

        assert result.isError is False
        assert result.structuredContent is not None
        mcp_service.node_knowledge.get_node_types.assert_called_once_with("ACTION_NODE")

    @pytest.mark.asyncio
    async def test_invoke_get_node_details(self, mcp_service):
        """Test invoking get_node_details tool"""
        params = {
            "nodes": [{"node_type": "ACTION_NODE", "subtype": "HTTP_REQUEST"}],
            "include_examples": True,
            "include_schemas": True,
        }

        result = await mcp_service.invoke_tool("get_node_details", params)

        assert result.isError is False
        assert result._tool_name == "get_node_details"
        assert result.structuredContent is not None
        assert isinstance(result.structuredContent, dict)
        assert "nodes" in result.structuredContent
        assert len(result.structuredContent["nodes"]) == 1

        node_detail = result.structuredContent["nodes"][0]
        assert node_detail["node_type"] == "ACTION_NODE"
        assert node_detail["subtype"] == "HTTP_REQUEST"

        # Verify the service was called with correct parameters
        mcp_service.node_knowledge.get_node_details.assert_called_once_with(
            [{"node_type": "ACTION_NODE", "subtype": "HTTP_REQUEST"}], True, True
        )

    @pytest.mark.asyncio
    async def test_invoke_get_node_details_with_defaults(self, mcp_service):
        """Test invoking get_node_details with default parameters"""
        params = {"nodes": [{"node_type": "ACTION_NODE", "subtype": "HTTP_REQUEST"}]}

        result = await mcp_service.invoke_tool("get_node_details", params)

        assert result.isError is False
        # Should use default values for include_examples and include_schemas
        mcp_service.node_knowledge.get_node_details.assert_called_once_with(
            [{"node_type": "ACTION_NODE", "subtype": "HTTP_REQUEST"}], True, True
        )

    @pytest.mark.asyncio
    async def test_invoke_invalid_tool(self, mcp_service):
        """Test invoking non-existent tool"""
        result = await mcp_service.invoke_tool("invalid_tool", {})

        assert result.isError is True
        assert result._tool_name == "invalid_tool"
        assert len(result.content) > 0
        assert "Tool 'invalid_tool' not found" in result.content[0].text
        assert result._execution_time_ms is not None

    def test_get_tool_info_valid_tools(self, mcp_service):
        """Test getting info for valid tools"""
        valid_tools = ["get_node_types", "get_node_details"]

        for tool_name in valid_tools:
            info = mcp_service.get_tool_info(tool_name)

            assert info["name"] == tool_name
            assert info["available"] is True
            assert "description" in info
            assert "version" in info
            assert "category" in info
            assert "usage_examples" in info
            assert isinstance(info["usage_examples"], list)

    def test_get_tool_info_invalid_tool(self, mcp_service):
        """Test getting info for invalid tool"""
        info = mcp_service.get_tool_info("invalid_tool")

        assert info["name"] == "invalid_tool"
        assert info["available"] is False
        assert "error" in info
        assert info["error"] == "Tool not found"

    def test_health_check_healthy(self, mcp_service):
        """Test health check when service is healthy"""
        result = mcp_service.health_check()

        assert result.healthy is True
        assert result.version == "3.0.0"
        assert len(result.available_tools) == 2
        assert "get_node_types" in result.available_tools
        assert "get_node_details" in result.available_tools
        assert result.timestamp is not None

    def test_health_check_unhealthy(self, mcp_service_no_registry):
        """Test health check when service is unhealthy"""
        result = mcp_service_no_registry.health_check()

        assert result.healthy is False
        assert result.version == "3.0.0"
        assert len(result.available_tools) == 0
        assert result.timestamp is not None

    @pytest.mark.asyncio
    async def test_tool_execution_timing(self, mcp_service):
        """Test that tool execution includes timing information"""
        result = await mcp_service.invoke_tool("get_node_types", {})

        assert result._execution_time_ms is not None
        assert result._execution_time_ms > 0
        assert isinstance(result._execution_time_ms, float)

    @pytest.mark.asyncio
    async def test_tool_with_empty_params(self, mcp_service):
        """Test tools with empty parameters"""
        # get_node_types with empty params
        result = await mcp_service.invoke_tool("get_node_types", {})
        assert result.isError is False

    @pytest.mark.asyncio
    async def test_concurrent_tool_invocation(self, mcp_service):
        """Test concurrent tool invocations"""
        # Create multiple concurrent requests
        tasks = [
            mcp_service.invoke_tool("get_node_types", {}),
            mcp_service.invoke_tool(
                "get_node_details",
                {"nodes": [{"node_type": "ACTION_NODE", "subtype": "HTTP_REQUEST"}]},
            ),
        ]

        results = await asyncio.gather(*tasks)

        # All should succeed
        for result in results:
            assert result.isError is False
            assert result._execution_time_ms is not None

    @pytest.mark.asyncio
    async def test_large_node_list_handling(self, mcp_service):
        """Test handling large list of nodes in get_node_details"""
        # Create a large list of nodes
        large_node_list = [{"node_type": "ACTION_NODE", "subtype": f"TYPE_{i}"} for i in range(100)]

        # Mock response for large list
        large_response = [
            {"node_type": "ACTION_NODE", "subtype": f"TYPE_{i}", "description": f"Node {i}"}
            for i in range(100)
        ]
        mcp_service.node_knowledge.get_node_details.return_value = large_response

        result = await mcp_service.invoke_tool("get_node_details", {"nodes": large_node_list})

        assert result.isError is False
        assert "nodes" in result.structuredContent
        assert len(result.structuredContent["nodes"]) == 100

    def test_tool_parameter_validation_structure(self, mcp_service):
        """Test that tool parameter schemas are properly structured"""
        tools_response = mcp_service.get_available_tools()

        for tool in tools_response.tools:
            params = tool.inputSchema

            # All tools should have proper JSON Schema structure
            assert params["type"] == "object"
            assert "properties" in params

            if tool.name == "get_node_types":
                # Should have optional type_filter
                assert "type_filter" in params["properties"]
                assert params["properties"]["type_filter"]["type"] == "string"
                assert "enum" in params["properties"]["type_filter"]

            elif tool.name == "get_node_details":
                # Should have required nodes array
                assert "nodes" in params["properties"]
                assert params["properties"]["nodes"]["type"] == "array"
                assert "required" in params
                assert "nodes" in params["required"]

    @pytest.mark.asyncio
    async def test_response_timestamp_and_metadata(self, mcp_service):
        """Test that responses include proper timestamp and metadata"""
        result = await mcp_service.invoke_tool("get_node_types", {})

        assert result.isError is False
        assert result._tool_name == "get_node_types"
        assert result._execution_time_ms is not None
        assert isinstance(result._execution_time_ms, float)
        # Note: timestamp and request_id are set by the HTTP layer, not the service layer
