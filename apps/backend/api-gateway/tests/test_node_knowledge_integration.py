"""
Integration tests for NodeKnowledgeService using real node specifications.

This demonstrates the better testing approach - using real specs and real logic
instead of extensive mocking.
"""

import pytest
from app.services.node_knowledge_service import NodeKnowledgeService


class TestNodeKnowledgeServiceIntegration:
    """Integration tests using real node specifications"""

    @pytest.fixture
    def service(self):
        """Create service with real registry"""
        return NodeKnowledgeService()

    def test_get_real_node_types(self, service):
        """Test getting real node types from the registry"""
        result = service.get_node_types()

        # Should return actual node types from the specs
        assert isinstance(result, dict)
        assert len(result) > 0

        # Should contain expected real node types
        expected_types = ["ACTION", "AI_AGENT", "FLOW"]
        for expected_type in expected_types:
            assert expected_type in result
            assert isinstance(result[expected_type], list)
            assert len(result[expected_type]) > 0

    def test_get_real_node_details(self, service):
        """Test getting real node details"""
        # Use actual nodes that exist in the registry
        real_nodes = [
            {"node_type": "ACTION", "subtype": "HTTP_REQUEST"},
            {"node_type": "AI_AGENT", "subtype": "OPENAI_NODE"},
            {"node_type": "FLOW", "subtype": "IF"},
        ]

        result = service.get_node_details(real_nodes)

        assert len(result) == 3
        for node_detail in result:
            # Should have all expected fields for real nodes
            assert "node_type" in node_detail
            assert "subtype" in node_detail
            assert "description" in node_detail
            assert "parameters" in node_detail
            assert "input_ports" in node_detail
            assert "output_ports" in node_detail
            assert "version" in node_detail
            # Should not have error field for valid nodes
            assert "error" not in node_detail

    def test_get_nonexistent_node_details(self, service):
        """Test handling of non-existent nodes"""
        fake_nodes = [
            {"node_type": "FAKE_NODE", "subtype": "FAKE_SUBTYPE"},
        ]

        result = service.get_node_details(fake_nodes)

        assert len(result) == 1
        assert "error" in result[0]
        assert result[0]["error"] == "Node specification not found"
        assert result[0]["node_type"] == "FAKE_NODE"
        assert result[0]["subtype"] == "FAKE_SUBTYPE"

    def test_search_real_nodes(self, service):
        """Test searching real nodes"""
        # Search for HTTP - should find HTTP_REQUEST node
        result = service.search_nodes("HTTP")

        assert isinstance(result, list)
        assert len(result) > 0

        # Should find the HTTP_REQUEST node
        http_nodes = [r for r in result if r["subtype"] == "HTTP_REQUEST"]
        assert len(http_nodes) > 0

        # Should have relevance score
        for node in result:
            assert "relevance_score" in node
            assert node["relevance_score"] > 0

    def test_search_with_no_matches(self, service):
        """Test searching with query that has no matches"""
        result = service.search_nodes("nonexistent_functionality_xyz")

        assert isinstance(result, list)
        assert len(result) == 0

    def test_search_empty_query(self, service):
        """Test searching with empty query"""
        result = service.search_nodes("")

        assert isinstance(result, list)
        assert len(result) == 0

    def test_performance_with_real_specs(self, service):
        """Test performance using real node specifications"""
        # Get all available node types
        all_types = service.get_node_types()

        # Create list of real nodes for testing
        real_nodes = []
        for node_type, subtypes in all_types.items():
            for subtype in subtypes[:2]:  # Take first 2 subtypes per type
                real_nodes.append({"node_type": node_type, "subtype": subtype})

        # Should have some real nodes to test with
        assert len(real_nodes) > 10

        # Test getting details for many real nodes
        result = service.get_node_details(real_nodes)

        # All should succeed since we're using real nodes
        assert len(result) == len(real_nodes)

        for node_detail in result:
            assert "error" not in node_detail
            assert "parameters" in node_detail
            assert "input_ports" in node_detail
            assert "output_ports" in node_detail

    def test_node_types_filtering(self, service):
        """Test filtering node types"""
        # Test filtering by specific type
        result = service.get_node_types("ACTION")

        assert isinstance(result, dict)
        assert len(result) == 1
        assert "ACTION" in result
        assert len(result["ACTION"]) > 0

        # Should not contain other types
        assert "AI_AGENT" not in result
        assert "FLOW" not in result

    def test_detailed_search_results(self, service):
        """Test search with detailed results"""
        result = service.search_nodes("HTTP", include_details=True)

        assert isinstance(result, list)
        assert len(result) > 0

        # With include_details=True, should have full spec information
        for node in result:
            assert "node_type" in node
            assert "subtype" in node
            assert "description" in node
            assert "parameters" in node
            assert "input_ports" in node
            assert "output_ports" in node
            assert "relevance_score" in node

    def test_case_insensitive_search(self, service):
        """Test that search is case insensitive"""
        result_upper = service.search_nodes("HTTP")
        result_lower = service.search_nodes("http")
        result_mixed = service.search_nodes("Http")

        # All should return the same results
        assert len(result_upper) == len(result_lower) == len(result_mixed)

        if result_upper:  # If we found any results
            assert result_upper[0]["subtype"] == result_lower[0]["subtype"]
            assert result_upper[0]["subtype"] == result_mixed[0]["subtype"]
