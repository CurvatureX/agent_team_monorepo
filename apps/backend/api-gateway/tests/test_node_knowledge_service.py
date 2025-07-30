"""
Unit tests for NodeKnowledgeService
Tests the core node knowledge functionality without HTTP dependencies
"""

import os
import sys
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add shared path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
shared_path = os.path.join(current_dir, "../../../../shared")
sys.path.insert(0, shared_path)

from app.services.node_knowledge_service import NodeKnowledgeService


class TestNodeKnowledgeService:
    """Test suite for NodeKnowledgeService"""

    @pytest.fixture
    def mock_registry(self):
        """Create a mock node registry"""
        registry = Mock()

        # Mock node types
        registry.get_node_types.return_value = {
            "ACTION_NODE": ["HTTP_REQUEST", "RUN_CODE"],
            "AI_AGENT_NODE": ["OPENAI_NODE", "CLAUDE_NODE"],
            "FLOW_NODE": ["IF", "LOOP"],
        }

        # Mock node specs
        mock_spec = Mock()
        mock_spec.node_type = "ACTION_NODE"
        mock_spec.subtype = "HTTP_REQUEST"
        mock_spec.version = "1.0.0"
        mock_spec.description = "Make HTTP requests to external APIs"
        mock_spec.parameters = []
        mock_spec.input_ports = []
        mock_spec.output_ports = []
        mock_spec.examples = [{"name": "test", "description": "test example"}]

        registry.get_spec.return_value = mock_spec
        registry.list_all_specs.return_value = [mock_spec]

        return registry

    @pytest.fixture
    def service_with_registry(self, mock_registry):
        """Create service with mocked registry"""
        with patch("app.services.node_knowledge_service.node_spec_registry", mock_registry):
            service = NodeKnowledgeService()
            return service

    @pytest.fixture
    def service_without_registry(self):
        """Create service without registry (simulates import failure)"""
        with patch("app.services.node_knowledge_service.node_spec_registry", None):
            service = NodeKnowledgeService()
            return service

    def test_init_with_registry(self, service_with_registry):
        """Test service initialization with registry"""
        assert service_with_registry.registry is not None

    def test_init_without_registry(self, service_without_registry):
        """Test service initialization without registry"""
        assert service_without_registry.registry is None

    def test_get_node_types_all(self, service_with_registry):
        """Test getting all node types"""
        result = service_with_registry.get_node_types()

        assert isinstance(result, dict)
        assert "ACTION_NODE" in result
        assert "AI_AGENT_NODE" in result
        assert "FLOW_NODE" in result
        assert result["ACTION_NODE"] == ["HTTP_REQUEST", "RUN_CODE"]

    def test_get_node_types_filtered(self, service_with_registry):
        """Test getting filtered node types"""
        result = service_with_registry.get_node_types("ACTION_NODE")

        assert isinstance(result, dict)
        assert len(result) == 1
        assert "ACTION_NODE" in result
        assert "AI_AGENT_NODE" not in result

    def test_get_node_types_no_registry(self, service_without_registry):
        """Test getting node types without registry"""
        result = service_without_registry.get_node_types()

        assert result == {}

    def test_get_node_types_with_exception(self, service_with_registry):
        """Test error handling in get_node_types"""
        service_with_registry.registry.get_node_types.side_effect = Exception("Test error")

        result = service_with_registry.get_node_types()
        assert result == {}

    def test_get_node_details_success(self, service_with_registry):
        """Test successful node details retrieval"""
        nodes = [{"node_type": "ACTION_NODE", "subtype": "HTTP_REQUEST"}]

        result = service_with_registry.get_node_details(nodes)

        assert isinstance(result, list)
        assert len(result) == 1

        node_detail = result[0]
        assert node_detail["node_type"] == "ACTION_NODE"
        assert node_detail["subtype"] == "HTTP_REQUEST"
        assert node_detail["description"] == "Make HTTP requests to external APIs"
        assert "parameters" in node_detail
        assert "input_ports" in node_detail
        assert "output_ports" in node_detail

    def test_get_node_details_not_found(self, service_with_registry):
        """Test node details for non-existent node"""
        service_with_registry.registry.get_spec.return_value = None
        nodes = [{"node_type": "INVALID_NODE", "subtype": "INVALID_SUBTYPE"}]

        result = service_with_registry.get_node_details(nodes)

        assert len(result) == 1
        assert "error" in result[0]
        assert result[0]["error"] == "Node specification not found"

    def test_get_node_details_no_registry(self, service_without_registry):
        """Test node details without registry"""
        nodes = [{"node_type": "ACTION_NODE", "subtype": "HTTP_REQUEST"}]

        result = service_without_registry.get_node_details(nodes)

        assert result == []

    def test_get_node_details_with_options(self, service_with_registry):
        """Test node details with different options"""
        nodes = [{"node_type": "ACTION_NODE", "subtype": "HTTP_REQUEST"}]

        # Test without examples
        result = service_with_registry.get_node_details(nodes, include_examples=False)
        assert "examples" not in result[0]

        # Test without schemas
        result = service_with_registry.get_node_details(nodes, include_schemas=False)
        for port in result[0]["input_ports"] + result[0]["output_ports"]:
            assert port["data_format"] is None
            assert port["validation_schema"] is None

    def test_get_node_details_exception_handling(self, service_with_registry):
        """Test exception handling in get_node_details"""
        service_with_registry.registry.get_spec.side_effect = Exception("Test error")
        nodes = [{"node_type": "ACTION_NODE", "subtype": "HTTP_REQUEST"}]

        result = service_with_registry.get_node_details(nodes)

        assert len(result) == 1
        assert "error" in result[0]
        assert "Error retrieving spec" in result[0]["error"]

    def test_search_nodes_success(self, service_with_registry):
        """Test successful node search"""
        result = service_with_registry.search_nodes("HTTP request", max_results=5)

        assert isinstance(result, list)
        assert len(result) <= 5

        if result:
            search_result = result[0]
            assert "node_type" in search_result
            assert "subtype" in search_result
            assert "relevance_score" in search_result
            assert search_result["relevance_score"] > 0

    def test_search_nodes_with_details(self, service_with_registry):
        """Test node search with details"""
        result = service_with_registry.search_nodes("HTTP", include_details=True)

        if result:
            search_result = result[0]
            assert "description" in search_result
            assert "parameters" in search_result
            assert "input_ports" in search_result
            assert "output_ports" in search_result

    def test_search_nodes_no_registry(self, service_without_registry):
        """Test node search without registry"""
        result = service_without_registry.search_nodes("HTTP")

        assert result == []

    def test_search_nodes_with_exception(self, service_with_registry):
        """Test search nodes with exception"""
        service_with_registry.registry.list_all_specs.side_effect = Exception("Test error")

        result = service_with_registry.search_nodes("HTTP")

        assert result == []

    def test_serialize_node_spec_success(self, service_with_registry):
        """Test successful node spec serialization"""
        mock_spec = Mock()
        mock_spec.node_type = "ACTION_NODE"
        mock_spec.subtype = "HTTP_REQUEST"
        mock_spec.version = "1.0.0"
        mock_spec.description = "Test description"
        mock_spec.parameters = []
        mock_spec.input_ports = []
        mock_spec.output_ports = []
        mock_spec.examples = [{"test": "example"}]

        result = service_with_registry._serialize_node_spec(mock_spec, True, True)

        assert result["node_type"] == "ACTION_NODE"
        assert result["subtype"] == "HTTP_REQUEST"
        assert result["version"] == "1.0.0"
        assert result["description"] == "Test description"
        assert "parameters" in result
        assert "input_ports" in result
        assert "output_ports" in result
        assert "examples" in result

    def test_serialize_node_spec_without_examples(self, service_with_registry):
        """Test node spec serialization without examples"""
        mock_spec = Mock()
        mock_spec.node_type = "ACTION_NODE"
        mock_spec.subtype = "HTTP_REQUEST"
        mock_spec.version = "1.0.0"
        mock_spec.description = "Test description"
        mock_spec.parameters = []
        mock_spec.input_ports = []
        mock_spec.output_ports = []
        mock_spec.examples = [{"test": "example"}]

        result = service_with_registry._serialize_node_spec(mock_spec, False, True)

        assert "examples" not in result

    def test_serialize_node_spec_with_exception(self, service_with_registry):
        """Test node spec serialization with exception"""
        mock_spec = Mock()
        mock_spec.node_type = "ACTION_NODE"
        mock_spec.subtype = "HTTP_REQUEST"
        # Simulate exception by making an attribute access fail
        type(mock_spec).version = Mock(side_effect=Exception("Test error"))

        result = service_with_registry._serialize_node_spec(mock_spec, True, True)

        assert "error" in result
        assert "Error serializing spec" in result["error"]

    def test_search_scoring(self, service_with_registry):
        """Test search relevance scoring"""
        # Create mock specs with different relevance levels
        http_spec = Mock()
        http_spec.node_type = "ACTION_NODE"
        http_spec.subtype = "HTTP_REQUEST"
        http_spec.description = "Make HTTP requests to external APIs"
        http_spec.parameters = []
        http_spec.input_ports = []
        http_spec.output_ports = []

        email_spec = Mock()
        email_spec.node_type = "TOOL_NODE"
        email_spec.subtype = "EMAIL"
        email_spec.description = "Send email notifications"
        email_spec.parameters = []
        email_spec.input_ports = []
        email_spec.output_ports = []

        service_with_registry.registry.list_all_specs.return_value = [http_spec, email_spec]

        # Search for "HTTP" should score HTTP_REQUEST higher
        result = service_with_registry.search_nodes("HTTP")

        assert len(result) >= 1
        # The HTTP_REQUEST node should have a higher score due to description match
        http_result = next((r for r in result if r["subtype"] == "HTTP_REQUEST"), None)
        assert http_result is not None
        assert http_result["relevance_score"] > 0

    def test_multiple_node_details_request(self, service_with_registry):
        """Test requesting details for multiple nodes"""
        nodes = [
            {"node_type": "ACTION_NODE", "subtype": "HTTP_REQUEST"},
            {"node_type": "AI_AGENT_NODE", "subtype": "OPENAI_NODE"},
        ]

        # Mock different specs for different nodes
        def mock_get_spec(node_type, subtype):
            spec = Mock()
            spec.node_type = node_type
            spec.subtype = subtype
            spec.version = "1.0.0"
            spec.description = f"{node_type} {subtype} description"
            spec.parameters = []
            spec.input_ports = []
            spec.output_ports = []
            spec.examples = None
            return spec

        service_with_registry.registry.get_spec.side_effect = mock_get_spec

        result = service_with_registry.get_node_details(nodes)

        assert len(result) == 2
        assert result[0]["node_type"] == "ACTION_NODE"
        assert result[0]["subtype"] == "HTTP_REQUEST"
        assert result[1]["node_type"] == "AI_AGENT_NODE"
        assert result[1]["subtype"] == "OPENAI_NODE"
