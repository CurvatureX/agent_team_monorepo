"""
Unit tests for MCP Service
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from core.mcp_exceptions import MCPParameterError, MCPToolNotFoundError, MCPValidationError
from models.mcp_models import (
    MCPInvokeResponse,
    MCPToolsResponse,
    NodeKnowledgeResponse,
    NodeKnowledgeResult,
)
from services.mcp_service import MCPService


class TestMCPService:
    """Test cases for MCPService"""

    @pytest.fixture
    def service(self):
        """Create MCPService with real client but we'll mock it per test"""
        return MCPService()

    def test_get_available_tools(self, service):
        """Test getting available tools"""
        result = service.get_available_tools()

        assert isinstance(result, MCPToolsResponse)
        assert len(result.tools) >= 2  # At least node_knowledge_retriever and elasticsearch

        tool_names = [tool.name for tool in result.tools]
        assert "node_knowledge_retriever" in tool_names
        assert "elasticsearch" in tool_names

        # Check tool structure
        for tool in result.tools:
            assert hasattr(tool, "name")
            assert hasattr(tool, "description")
            assert hasattr(tool, "parameters")
            assert isinstance(tool.parameters, dict)

    @pytest.mark.asyncio
    async def test_invoke_tool_not_found(self, service):
        """Test invoking non-existent tool"""
        with pytest.raises(MCPToolNotFoundError) as exc_info:
            await service.invoke_tool("nonexistent_tool", {})

        assert "nonexistent_tool" in str(exc_info.value.message)
        assert exc_info.value.user_message == "unknown tool"

    @pytest.mark.asyncio
    async def test_invoke_node_knowledge_retriever_success(self, service):
        """Test successful node knowledge retriever invocation"""
        # Mock successful response
        mock_response = NodeKnowledgeResponse(
            success=True,
            results=[
                NodeKnowledgeResult(
                    node_name="test_node",
                    knowledge="Test knowledge content",
                    metadata={"category": "test"},
                    similarity_score=1.0,
                )
            ],
            total_nodes=1,
            processing_time_ms=100,
        )

        # Mock the service's node knowledge client method
        service.node_knowledge_client.retrieve_node_knowledge = AsyncMock(return_value=mock_response)

        # Test invocation
        result = await service.invoke_tool(
            "node_knowledge_retriever", {"node_names": ["test_node"], "include_metadata": True}
        )

        # Assertions
        assert isinstance(result, MCPInvokeResponse)
        assert result.success is True
        assert result.result is not None
        assert result.result["success"] is True
        assert len(result.result["results"]) == 1
        assert result.result["results"][0]["node_name"] == "test_node"
        assert result.result["total_nodes"] == 1

    @pytest.mark.asyncio
    async def test_invoke_node_knowledge_retriever_empty_names(self, service):
        """Test node knowledge retriever with empty node_names"""
        with pytest.raises(MCPParameterError) as exc_info:
            await service.invoke_tool("node_knowledge_retriever", {"node_names": []})

        assert "node_names is required" in str(exc_info.value.user_message)

    @pytest.mark.asyncio
    async def test_invoke_elasticsearch_placeholder(self, service):
        """Test Elasticsearch tool placeholder"""
        result = await service.invoke_tool(
            "elasticsearch", {"index": "test_index", "query": {"match_all": {}}}
        )

        assert isinstance(result, MCPInvokeResponse)
        assert result.success is True
        assert "not yet implemented" in result.result["message"]
        assert result.result["index"] == "test_index"

    def test_validate_tool_params_success(self, service):
        """Test successful parameter validation"""
        # Should not raise exception
        service.validate_tool_params(
            "node_knowledge_retriever", {"node_names": ["test_node"], "include_metadata": True}
        )

    def test_validate_tool_params_missing_required(self, service):
        """Test parameter validation with missing required parameter"""
        with pytest.raises(MCPValidationError) as exc_info:
            service.validate_tool_params(
                "node_knowledge_retriever",
                {
                    "include_metadata": True
                    # Missing required node_names
                },
            )

        assert "validation failed" in str(exc_info.value.message).lower()

    def test_validate_tool_params_wrong_type(self, service):
        """Test parameter validation with wrong parameter type"""
        with pytest.raises(MCPValidationError) as exc_info:
            service.validate_tool_params(
                "node_knowledge_retriever",
                {"node_names": "not_an_array", "include_metadata": True},  # Should be array
            )

        assert "validation failed" in str(exc_info.value.message).lower()

    def test_validate_tool_params_tool_not_found(self, service):
        """Test parameter validation for non-existent tool"""
        with pytest.raises(MCPToolNotFoundError):
            service.validate_tool_params("nonexistent_tool", {})

    def test_get_tool_info_success(self, service):
        """Test getting tool information"""
        info = service.get_tool_info("node_knowledge_retriever")

        assert isinstance(info, dict)
        assert info["name"] == "node_knowledge_retriever"
        assert "description" in info
        assert "parameters" in info

    def test_get_tool_info_not_found(self, service):
        """Test getting info for non-existent tool"""
        with pytest.raises(MCPToolNotFoundError):
            service.get_tool_info("nonexistent_tool")

    def test_health_check_success(self, service):
        """Test successful health check"""
        service.node_knowledge_client.health_check = Mock(return_value={"healthy": True})

        result = service.health_check()

        assert result["healthy"] is True
        assert "available_tools" in result
        assert "tool_count" in result
        assert "node_knowledge_client" in result
        assert len(result["available_tools"]) >= 2

    def test_health_check_failure(self, service):
        """Test health check with client failure"""
        service.node_knowledge_client.health_check = Mock(side_effect=Exception("Client error"))

        result = service.health_check()

        assert result["healthy"] is False
        assert "error" in result
        assert "available_tools" in result  # Should still return tool info

    @pytest.mark.asyncio
    async def test_invoke_tool_client_error(self, service):
        """Test tool invocation with client error"""
        service.node_knowledge_client.retrieve_node_knowledge = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        with pytest.raises(Exception):  # Should propagate as MCPServiceError
            await service.invoke_tool("node_knowledge_retriever", {"node_names": ["test_node"]})

    @pytest.mark.asyncio
    async def test_invoke_tool_parameter_validation_integration(self, service):
        """Test that tool invocation includes parameter validation"""
        # Test with invalid parameters - should fail validation before reaching handler
        with pytest.raises(MCPValidationError):
            await service.invoke_tool(
                "elasticsearch",
                {
                    "index": "test_index"
                    # Missing required 'query' parameter
                },
            )
