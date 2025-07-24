"""
Unit tests for Node Knowledge Retriever Tool
"""

from unittest.mock import AsyncMock, Mock

import pytest

from ..core.mcp_exceptions import MCPParameterError
from ..models.mcp_models import NodeKnowledgeResponse, NodeKnowledgeResult
from ..services.mcp_service import MCPService


class TestNodeKnowledgeRetrieverTool:
    """Test cases for Node Knowledge Retriever Tool functionality"""

    @pytest.fixture
    def mock_node_client(self):
        """Mock node knowledge client"""
        mock_client = Mock()
        return mock_client

    @pytest.fixture
    def service(self, mock_node_client):
        """Create MCPService with mocked node client"""
        service = MCPService()
        service.node_knowledge_client = mock_node_client
        return service

    @pytest.mark.asyncio
    async def test_node_knowledge_retriever_with_metadata(self, service, mock_node_client):
        """Test node knowledge retriever with metadata included"""
        # Mock response with metadata
        mock_response = NodeKnowledgeResponse(
            success=True,
            results=[
                NodeKnowledgeResult(
                    node_name="test_node",
                    knowledge="Test knowledge content",
                    metadata={"created_at": "2024-01-01", "category": "test", "confidence": 0.95},
                    similarity_score=1.0,
                )
            ],
            total_nodes=1,
            processing_time_ms=150,
        )

        mock_node_client.retrieve_node_knowledge = AsyncMock(return_value=mock_response)

        # Test with metadata
        result = await service.invoke_tool(
            "node_knowledge_retriever", {"node_names": ["test_node"], "include_metadata": True}
        )

        # Verify metadata is included
        assert result.success is True
        node_result = result.result["results"][0]
        assert node_result["metadata"]["category"] == "test"
        assert node_result["metadata"]["confidence"] == 0.95

        # Verify client was called with correct parameters
        mock_node_client.retrieve_node_knowledge.assert_called_once_with(
            node_names=["test_node"], include_metadata=True
        )

    @pytest.mark.asyncio
    async def test_node_knowledge_retriever_without_metadata(self, service, mock_node_client):
        """Test node knowledge retriever without metadata"""
        # Mock response
        mock_response = NodeKnowledgeResponse(
            success=True,
            results=[
                NodeKnowledgeResult(
                    node_name="test_node",
                    knowledge="Test knowledge content",
                    metadata={},  # Empty metadata when not requested
                    similarity_score=1.0,
                )
            ],
            total_nodes=1,
            processing_time_ms=100,
        )

        mock_node_client.retrieve_node_knowledge = AsyncMock(return_value=mock_response)

        # Test without metadata (default behavior)
        result = await service.invoke_tool(
            "node_knowledge_retriever", {"node_names": ["test_node"]}
        )

        # Verify metadata is empty
        assert result.success is True
        node_result = result.result["results"][0]
        assert node_result["metadata"] == {}

        # Verify client was called with correct parameters
        mock_node_client.retrieve_node_knowledge.assert_called_once_with(
            node_names=["test_node"], include_metadata=False
        )

    @pytest.mark.asyncio
    async def test_node_knowledge_retriever_multiple_nodes(self, service, mock_node_client):
        """Test node knowledge retriever with multiple nodes"""
        # Mock response for multiple nodes
        mock_response = NodeKnowledgeResponse(
            success=True,
            results=[
                NodeKnowledgeResult(
                    node_name="node1",
                    knowledge="Knowledge for node 1",
                    metadata={},
                    similarity_score=1.0,
                ),
                NodeKnowledgeResult(
                    node_name="node2",
                    knowledge="Knowledge for node 2",
                    metadata={},
                    similarity_score=0.8,
                ),
            ],
            total_nodes=2,
            processing_time_ms=200,
        )

        mock_node_client.retrieve_node_knowledge = AsyncMock(return_value=mock_response)

        # Test with multiple nodes
        result = await service.invoke_tool(
            "node_knowledge_retriever",
            {"node_names": ["node1", "node2"], "include_metadata": False},
        )

        # Verify results
        assert result.success is True
        assert result.result["total_nodes"] == 2
        assert len(result.result["results"]) == 2

        # Check individual results
        results = result.result["results"]
        assert results[0]["node_name"] == "node1"
        assert results[1]["node_name"] == "node2"
        assert results[0]["similarity_score"] == 1.0
        assert results[1]["similarity_score"] == 0.8

    @pytest.mark.asyncio
    async def test_node_knowledge_retriever_empty_node_names(self, service):
        """Test node knowledge retriever with empty node_names"""
        with pytest.raises(MCPParameterError) as exc_info:
            await service.invoke_tool("node_knowledge_retriever", {"node_names": []})

        assert "node_names is required" in exc_info.value.user_message

    @pytest.mark.asyncio
    async def test_node_knowledge_retriever_missing_node_names(self, service):
        """Test node knowledge retriever with missing node_names parameter"""
        # This should be caught by parameter validation
        with pytest.raises(Exception):  # Will be MCPValidationError from schema validation
            await service.invoke_tool(
                "node_knowledge_retriever",
                {
                    "include_metadata": True
                    # Missing node_names
                },
            )

    @pytest.mark.asyncio
    async def test_node_knowledge_retriever_processing_time(self, service, mock_node_client):
        """Test that processing time is included in response"""
        mock_response = NodeKnowledgeResponse(
            success=True,
            results=[
                NodeKnowledgeResult(
                    node_name="test_node",
                    knowledge="Test content",
                    metadata={},
                    similarity_score=1.0,
                )
            ],
            total_nodes=1,
            processing_time_ms=250,
        )

        mock_node_client.retrieve_node_knowledge = AsyncMock(return_value=mock_response)

        result = await service.invoke_tool(
            "node_knowledge_retriever", {"node_names": ["test_node"]}
        )

        assert result.success is True
        assert result.result["processing_time_ms"] == 250

    @pytest.mark.asyncio
    async def test_node_knowledge_retriever_client_error_handling(self, service, mock_node_client):
        """Test error handling when node knowledge client fails"""
        # Mock client error
        mock_node_client.retrieve_node_knowledge = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        # Should propagate as service error
        with pytest.raises(Exception):
            await service.invoke_tool("node_knowledge_retriever", {"node_names": ["test_node"]})

    def test_node_knowledge_tool_schema_validation(self, service):
        """Test that the tool schema is properly defined"""
        tool_info = service.get_tool_info("node_knowledge_retriever")

        # Verify schema structure
        assert tool_info["name"] == "node_knowledge_retriever"
        assert "description" in tool_info

        params = tool_info["parameters"]
        assert params["type"] == "object"
        assert "node_names" in params["properties"]
        assert "include_metadata" in params["properties"]
        assert "node_names" in params["required"]

        # Verify node_names is array of strings
        node_names_prop = params["properties"]["node_names"]
        assert node_names_prop["type"] == "array"
        assert node_names_prop["items"]["type"] == "string"

        # Verify include_metadata is boolean with default
        metadata_prop = params["properties"]["include_metadata"]
        assert metadata_prop["type"] == "boolean"
        assert metadata_prop["default"] is False
