"""
Unit tests for Node Knowledge Client
"""

from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest

from ..clients.node_knowledge_client import NodeKnowledgeClient
from ..core.mcp_exceptions import MCPDatabaseError, MCPParameterError
from ..models.mcp_models import NodeKnowledgeResponse, NodeKnowledgeResult


class TestNodeKnowledgeClient:
    """Test cases for NodeKnowledgeClient"""

    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client"""
        mock_client = Mock()
        mock_table = Mock()
        mock_client.table.return_value = mock_table
        return mock_client, mock_table

    @pytest.fixture
    def client(self, mock_supabase_client):
        """Create NodeKnowledgeClient with mocked Supabase"""
        mock_client, _ = mock_supabase_client

        with patch(
            "apps.backend.api_gateway.clients.node_knowledge_client.create_client"
        ) as mock_create:
            mock_create.return_value = mock_client
            client = NodeKnowledgeClient()
            return client

    @pytest.mark.asyncio
    async def test_retrieve_node_knowledge_success(self, client, mock_supabase_client):
        """Test successful node knowledge retrieval"""
        mock_client, mock_table = mock_supabase_client

        # Mock successful response
        mock_response = Mock()
        mock_response.data = [
            {
                "id": "1",
                "node_type": "test",
                "node_subtype": "example",
                "title": "test_node",
                "description": "Test node description",
                "content": "Test node knowledge content",
                "metadata": {"category": "test"},
            }
        ]

        mock_query = Mock()
        mock_query.execute.return_value = mock_response
        mock_table.select.return_value.eq.return_value = mock_query

        # Test the method
        result = await client.retrieve_node_knowledge(["test_node"], include_metadata=True)

        # Assertions
        assert isinstance(result, NodeKnowledgeResponse)
        assert result.success is True
        assert result.total_nodes == 1
        assert len(result.results) == 1

        node_result = result.results[0]
        assert node_result.node_name == "test_node"
        assert node_result.knowledge == "Test node knowledge content"
        assert node_result.metadata == {"category": "test"}
        assert node_result.similarity_score == 1.0

    @pytest.mark.asyncio
    async def test_retrieve_node_knowledge_empty_names(self, client):
        """Test error when node_names is empty"""
        with pytest.raises(MCPParameterError) as exc_info:
            await client.retrieve_node_knowledge([])

        assert "node_names is required" in str(exc_info.value.user_message)

    @pytest.mark.asyncio
    async def test_retrieve_node_knowledge_no_metadata(self, client, mock_supabase_client):
        """Test node knowledge retrieval without metadata"""
        mock_client, mock_table = mock_supabase_client

        # Mock successful response
        mock_response = Mock()
        mock_response.data = [
            {
                "id": "1",
                "node_type": "test",
                "node_subtype": "example",
                "title": "test_node",
                "description": "Test node description",
                "content": "Test node knowledge content",
                "metadata": {"category": "test"},
            }
        ]

        mock_query = Mock()
        mock_query.execute.return_value = mock_response
        mock_table.select.return_value.eq.return_value = mock_query

        # Test without metadata
        result = await client.retrieve_node_knowledge(["test_node"], include_metadata=False)

        # Assertions
        assert result.success is True
        node_result = result.results[0]
        assert node_result.metadata == {}

    @pytest.mark.asyncio
    async def test_retrieve_node_knowledge_not_found(self, client, mock_supabase_client):
        """Test node knowledge retrieval when node not found"""
        mock_client, mock_table = mock_supabase_client

        # Mock empty response
        mock_response = Mock()
        mock_response.data = []

        mock_query = Mock()
        mock_query.execute.return_value = mock_response
        mock_table.select.return_value.eq.return_value = mock_query

        # Test the method
        result = await client.retrieve_node_knowledge(["nonexistent_node"])

        # Assertions
        assert result.success is True
        assert result.total_nodes == 1
        node_result = result.results[0]
        assert node_result.node_name == "nonexistent_node"
        assert "not found" in node_result.knowledge
        assert node_result.similarity_score == 0.0

    @pytest.mark.asyncio
    async def test_retrieve_node_knowledge_database_error(self, client, mock_supabase_client):
        """Test database error handling"""
        mock_client, mock_table = mock_supabase_client

        # Mock database error
        mock_query = Mock()
        mock_query.execute.side_effect = Exception("Database connection failed")
        mock_table.select.return_value.eq.return_value = mock_query

        # Test the method - should handle error gracefully
        result = await client.retrieve_node_knowledge(["test_node"])

        # Should return empty result for failed node
        assert result.success is True
        assert result.total_nodes == 1
        node_result = result.results[0]
        assert node_result.node_name == "test_node"
        assert node_result.knowledge == ""

    @pytest.mark.asyncio
    async def test_retrieve_multiple_nodes(self, client, mock_supabase_client):
        """Test retrieving multiple nodes"""
        mock_client, mock_table = mock_supabase_client

        # Mock responses for different nodes
        def mock_execute():
            mock_response = Mock()
            mock_response.data = [
                {
                    "id": "1",
                    "node_type": "test",
                    "node_subtype": "example",
                    "title": "test_node_1",
                    "description": "Test node 1",
                    "content": "Content for node 1",
                    "metadata": {},
                }
            ]
            return mock_response

        mock_query = Mock()
        mock_query.execute = mock_execute
        mock_table.select.return_value.eq.return_value = mock_query

        # Test multiple nodes
        result = await client.retrieve_node_knowledge(["node1", "node2"])

        # Assertions
        assert result.success is True
        assert result.total_nodes == 2
        assert len(result.results) == 2

    def test_health_check_success(self, client, mock_supabase_client):
        """Test successful health check"""
        mock_client, mock_table = mock_supabase_client

        # Mock successful health check response
        mock_response = Mock()
        mock_response.data = [{"id": "1"}]

        mock_query = Mock()
        mock_query.execute.return_value = mock_response
        mock_table.select.return_value.limit.return_value = mock_query

        # Test health check
        result = client.health_check()

        # Assertions
        assert result["healthy"] is True
        assert result["total_records"] == 1

    def test_health_check_failure(self, client, mock_supabase_client):
        """Test health check failure"""
        mock_client, mock_table = mock_supabase_client

        # Mock health check error
        mock_query = Mock()
        mock_query.execute.side_effect = Exception("Connection failed")
        mock_table.select.return_value.limit.return_value = mock_query

        # Test health check
        result = client.health_check()

        # Assertions
        assert result["healthy"] is False
        assert "error" in result

    def test_initialization_without_credentials(self):
        """Test client initialization without Supabase credentials"""
        with patch("apps.backend.api_gateway.core.config.settings") as mock_settings:
            mock_settings.NODE_KNOWLEDGE_SUPABASE_URL = ""
            mock_settings.NODE_KNOWLEDGE_SUPABASE_KEY = ""

            client = NodeKnowledgeClient()
            assert client.supabase is None
