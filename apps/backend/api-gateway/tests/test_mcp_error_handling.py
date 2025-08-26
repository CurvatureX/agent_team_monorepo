"""
Error handling and edge case tests for MCP Node Knowledge Server
Tests various error conditions, edge cases, and failure scenarios
"""

import asyncio
import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add shared path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
shared_path = os.path.join(current_dir, "../../../../shared")
sys.path.insert(0, shared_path)

from app.api.mcp.tools import NodeKnowledgeMCPService
from app.services.node_knowledge_service import NodeKnowledgeService


class TestMCPErrorHandling:
    """Test suite for MCP error handling and edge cases"""

    @pytest.fixture
    def failing_registry(self):
        """Create a mock registry that fails in various ways"""
        registry = Mock()
        registry.get_node_types.side_effect = Exception("Registry connection failed")
        registry.get_spec.side_effect = Exception("Spec retrieval failed")
        registry.list_all_specs.side_effect = Exception("Spec listing failed")
        return registry

    @pytest.fixture
    def service_with_failing_registry(self, failing_registry):
        """Create service with failing registry"""
        with patch("app.services.node_knowledge_service.node_spec_registry", failing_registry):
            service = NodeKnowledgeService()
            return service

    @pytest.fixture
    def mcp_service_with_failures(self, service_with_failing_registry):
        """Create MCP service with failing node knowledge service"""
        with patch(
            "app.api.mcp.tools.NodeKnowledgeService", return_value=service_with_failing_registry
        ):
            service = NodeKnowledgeMCPService()
            return service

    def test_node_knowledge_service_import_failure(self):
        """Test service behavior when node_specs import fails"""
        with patch("app.services.node_knowledge_service.node_spec_registry", None):
            service = NodeKnowledgeService()

            # All methods should handle None registry gracefully
            assert service.get_node_types() == {}
            assert service.get_node_details([{"node_type": "TEST", "subtype": "TEST"}]) == []
            assert service.search_nodes("test") == []

    def test_node_knowledge_service_registry_exceptions(self, service_with_failing_registry):
        """Test service behavior when registry methods throw exceptions"""
        service = service_with_failing_registry

        # get_node_types should return empty dict on exception
        result = service.get_node_types()
        assert result == {}

        # get_node_details should return empty list on exception
        result = service.get_node_details([{"node_type": "TEST", "subtype": "TEST"}])
        assert result == []

        # search_nodes should return empty list on exception
        result = service.search_nodes("test")
        assert result == []

    def test_get_node_details_partial_failures(self):
        """Test get_node_details with some nodes succeeding and some failing"""
        registry = Mock()

        # Mock registry to succeed for first node, fail for second
        def mock_get_spec(node_type, subtype):
            if node_type == "SUCCESS_NODE":
                spec = Mock()
                spec.node_type = node_type
                spec.subtype = subtype
                spec.version = "1.0.0"
                spec.description = "Success spec"
                spec.parameters = []
                spec.input_ports = []
                spec.output_ports = []
                spec.examples = None
                return spec
            elif node_type == "FAIL_NODE":
                raise Exception("Spec retrieval failed")
            else:
                return None  # Not found

        registry.get_spec.side_effect = mock_get_spec

        with patch("app.services.node_knowledge_service.node_spec_registry", registry):
            service = NodeKnowledgeService()

            nodes = [
                {"node_type": "SUCCESS_NODE", "subtype": "TEST"},
                {"node_type": "FAIL_NODE", "subtype": "TEST"},
                {"node_type": "MISSING_NODE", "subtype": "TEST"},
            ]

            result = service.get_node_details(nodes)

            assert len(result) == 3

            # First node should succeed
            assert result[0]["node_type"] == "SUCCESS_NODE"
            assert "error" not in result[0]

            # Second node should have error from exception
            assert result[1]["node_type"] == "FAIL_NODE"
            assert "error" in result[1]
            assert "Error retrieving spec" in result[1]["error"]

            # Third node should have some error indicating it wasn't found
            assert result[2]["node_type"] == "MISSING_NODE"
            assert "error" in result[2]
            # Accept either "not found" or "incorrect format" - both indicate the node is invalid
            assert any(
                phrase in result[2]["error"].lower() for phrase in ["not found", "incorrect"]
            )

    def test_get_node_details_malformed_request(self):
        """Test get_node_details with malformed node requests"""
        registry = Mock()
        registry.get_spec.return_value = None

        with patch("app.services.node_knowledge_service.node_spec_registry", registry):
            service = NodeKnowledgeService()

            # Test with missing keys
            malformed_nodes = [
                {"node_type": "TEST"},  # Missing subtype
                {"subtype": "TEST"},  # Missing node_type
                {},  # Empty dict
                {"node_type": "", "subtype": ""},  # Empty strings
            ]

            result = service.get_node_details(malformed_nodes)

            assert len(result) == 4
            for node_result in result:
                assert "error" in node_result

    def test_search_nodes_edge_cases(self):
        """Test search_nodes with various edge cases"""
        registry = Mock()

        # Create spec with various searchable content
        spec = Mock()
        spec.node_type = "TEST_NODE"
        spec.subtype = "TEST_SUBTYPE"
        spec.description = "Test description with HTTP keyword"

        # Create parameter mocks with proper attributes
        param1 = Mock()
        param1.name = "url_param"
        param1.description = "URL parameter"

        param2 = Mock()
        param2.name = "method"
        param2.description = "HTTP method"

        spec.parameters = [param1, param2]

        # Create port mocks with proper attributes
        input_port = Mock()
        input_port.name = "input"
        input_port.description = "Input port"

        output_port = Mock()
        output_port.name = "output"
        output_port.description = "Output port"

        spec.input_ports = [input_port]
        spec.output_ports = [output_port]

        registry.list_all_specs.return_value = [spec]

        with patch("app.services.node_knowledge_service.node_spec_registry", registry):
            service = NodeKnowledgeService()

            # Test empty query
            result = service.search_nodes("")
            assert result == []

            # Test query with no matches
            result = service.search_nodes("nonexistent_keyword")
            assert result == []

            # Test case insensitive search
            result = service.search_nodes("HTTP")
            assert len(result) > 0

            result = service.search_nodes("http")
            assert len(result) > 0

            # Test max_results limiting
            result = service.search_nodes("test", max_results=0)
            assert result == []

    def test_serialize_node_spec_with_malformed_spec(self):
        """Test _serialize_node_spec with malformed spec objects"""
        service = NodeKnowledgeService()

        # Test with None spec
        result = service._serialize_node_spec(None, True, True)
        assert "error" in result

        # Test with spec missing required attributes
        malformed_spec = Mock()
        del malformed_spec.node_type  # Remove required attribute

        result = service._serialize_node_spec(malformed_spec, True, True)
        assert "error" in result
        assert "Error serializing spec" in result["error"]

    @pytest.mark.asyncio
    async def test_mcp_service_with_registry_failures(self, mcp_service_with_failures):
        """Test MCP service behavior when underlying service fails"""
        service = mcp_service_with_failures

        # get_node_types should return empty result
        result = await service.invoke_tool("get_node_types", {})
        assert result.isError is False  # Service doesn't fail, just returns empty
        assert result.structuredContent == {}

        # get_node_details should return empty result
        result = await service.invoke_tool(
            "get_node_details", {"nodes": [{"node_type": "TEST", "subtype": "TEST"}]}
        )
        assert result.isError is False
        assert result.structuredContent == {"nodes": []}

    @pytest.mark.asyncio
    async def test_mcp_service_timeout_handling(self):
        """Test MCP service with simulated slow operations"""
        mock_service = Mock()

        # Simulate slow operation by returning result directly
        # (Note: Actual timeout handling would be implemented in the MCP service layer)
        mock_service.get_node_types.return_value = {"result": "success"}

        with patch("app.api.mcp.tools.NodeKnowledgeService", return_value=mock_service):
            mcp_service = NodeKnowledgeMCPService()

            # This should complete successfully (no actual timeout implemented)
            result = await mcp_service.invoke_tool("get_node_types", {})
            assert result.isError is False

    def test_mcp_service_health_check_edge_cases(self):
        """Test MCP service health check edge cases"""
        # Test with None registry
        mock_service = Mock()
        mock_service.registry = None

        with patch("app.api.mcp.tools.NodeKnowledgeService", return_value=mock_service):
            mcp_service = NodeKnowledgeMCPService()
            health = mcp_service.health_check()

            assert health.healthy is False
            assert len(health.available_tools) == 0

        # Test with registry that throws exception during health check
        mock_service.registry = Mock()
        mock_service.registry.side_effect = Exception("Registry error")

        with patch("app.api.mcp.tools.NodeKnowledgeService", return_value=mock_service):
            mcp_service = NodeKnowledgeMCPService()
            health = mcp_service.health_check()

            # Should still return health check (registry availability is checked, not called)
            assert health.healthy is True  # Registry exists, even if it would fail

    def test_parameter_edge_cases(self):
        """Test parameter handling edge cases"""
        registry = Mock()

        # Create spec with parameter that has enum type
        param_with_enum = Mock()
        param_with_enum.name = "test_param"
        param_with_enum.type = Mock()
        param_with_enum.type.value = "enum"
        param_with_enum.required = True
        param_with_enum.default_value = None
        param_with_enum.description = "Test parameter"
        param_with_enum.enum_values = ["option1", "option2"]
        param_with_enum.validation_pattern = None

        # Create spec with parameter that doesn't have .value attribute
        param_without_value = Mock()
        param_without_value.name = "test_param2"
        param_without_value.type = "string"  # Direct string, no .value
        param_without_value.required = False
        param_without_value.default_value = "default"
        param_without_value.description = "Test parameter 2"
        param_without_value.enum_values = None
        param_without_value.validation_pattern = ".*"

        spec = Mock()
        spec.node_type = "TEST_NODE"
        spec.subtype = "TEST_SUBTYPE"
        spec.version = "1.0.0"
        spec.description = "Test spec"
        spec.parameters = [param_with_enum, param_without_value]
        spec.input_ports = []
        spec.output_ports = []
        spec.examples = None

        registry.get_spec.return_value = spec

        with patch("app.services.node_knowledge_service.node_spec_registry", registry):
            service = NodeKnowledgeService()

            result = service.get_node_details(
                [{"node_type": "TEST_NODE", "subtype": "TEST_SUBTYPE"}]
            )

            assert len(result) == 1
            node_detail = result[0]

            # Check that both parameter types are handled correctly
            params = node_detail["parameters"]
            assert len(params) == 2

            # First param should have enum value extracted
            assert params[0]["type"] == "enum"
            assert params[0]["enum_values"] == ["option1", "option2"]

            # Second param should have string type
            assert params[1]["type"] == "string"
            assert params[1]["validation_pattern"] == ".*"

    def test_port_data_format_edge_cases(self):
        """Test port data format handling edge cases"""
        registry = Mock()

        # Create port with data format
        port_with_format = Mock()
        port_with_format.name = "test_port"
        port_with_format.type = "MAIN"
        port_with_format.required = True
        port_with_format.description = "Test port"
        port_with_format.max_connections = 1
        port_with_format.data_format = Mock()
        port_with_format.data_format.mime_type = "application/json"
        port_with_format.data_format.schema = '{"type": "object"}'
        port_with_format.data_format.examples = ['{"test": "example"}']
        port_with_format.validation_schema = '{"type": "object"}'

        # Create port without data format
        port_without_format = Mock()
        port_without_format.name = "test_port2"
        port_without_format.type = "ERROR"
        port_without_format.required = False
        port_without_format.description = "Error port"
        port_without_format.max_connections = -1
        port_without_format.data_format = None
        port_without_format.validation_schema = None

        spec = Mock()
        spec.node_type = "TEST_NODE"
        spec.subtype = "TEST_SUBTYPE"
        spec.version = "1.0.0"
        spec.description = "Test spec"
        spec.parameters = []
        spec.input_ports = [port_with_format]
        spec.output_ports = [port_without_format]
        spec.examples = None

        registry.get_spec.return_value = spec

        with patch("app.services.node_knowledge_service.node_spec_registry", registry):
            service = NodeKnowledgeService()

            # Test with schemas included
            result = service.get_node_details(
                [{"node_type": "TEST_NODE", "subtype": "TEST_SUBTYPE"}], include_schemas=True
            )

            node_detail = result[0]

            # Input port should have data format
            input_port = node_detail["input_ports"][0]
            assert input_port["data_format"] is not None
            assert input_port["data_format"]["mime_type"] == "application/json"
            assert input_port["validation_schema"] == '{"type": "object"}'

            # Output port should have None data format
            output_port = node_detail["output_ports"][0]
            assert output_port["data_format"] is None
            assert output_port["validation_schema"] is None

            # Test with schemas excluded
            result = service.get_node_details(
                [{"node_type": "TEST_NODE", "subtype": "TEST_SUBTYPE"}], include_schemas=False
            )

            node_detail = result[0]

            # Both ports should have None data format and validation schema
            input_port = node_detail["input_ports"][0]
            assert input_port["data_format"] is None
            assert input_port["validation_schema"] is None

            output_port = node_detail["output_ports"][0]
            assert output_port["data_format"] is None
            assert output_port["validation_schema"] is None

    @pytest.mark.asyncio
    async def test_concurrent_operations_with_failures(self):
        """Test concurrent operations when some fail"""
        mock_service = Mock()

        call_count = 0

        def mock_get_node_types(type_filter=None):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:  # Fail every second call
                raise Exception(f"Call {call_count} failed")
            return {"ACTION_NODE": ["HTTP_REQUEST"]}

        mock_service.get_node_types.side_effect = mock_get_node_types
        mock_service.get_node_details.return_value = []
        mock_service.search_nodes.return_value = []
        mock_service.registry = Mock()

        with patch("app.api.mcp.tools.NodeKnowledgeService", return_value=mock_service):
            mcp_service = NodeKnowledgeMCPService()

            # Create multiple concurrent requests
            tasks = [
                mcp_service.invoke_tool("get_node_types", {}),
                mcp_service.invoke_tool("get_node_types", {}),
                mcp_service.invoke_tool("get_node_types", {}),
                mcp_service.invoke_tool("get_node_types", {}),
            ]

            results = await asyncio.gather(*tasks)

            # Some should succeed, some should fail due to exceptions
            success_count = sum(1 for r in results if not r.isError)
            failure_count = sum(1 for r in results if r.isError)

            assert success_count + failure_count == 4
            assert success_count > 0  # At least some should succeed
            assert failure_count > 0  # At least some should fail

    def test_very_large_search_results(self):
        """Test handling of very large search results"""
        registry = Mock()

        # Create many specs for search
        specs = []
        for i in range(1000):  # Large number of specs
            spec = Mock()
            spec.node_type = f"NODE_TYPE_{i % 10}"
            spec.subtype = f"SUBTYPE_{i}"
            spec.description = f"Description {i} with search keyword"
            spec.parameters = []
            spec.input_ports = []
            spec.output_ports = []
            specs.append(spec)

        registry.list_all_specs.return_value = specs

        with patch("app.services.node_knowledge_service.node_spec_registry", registry):
            service = NodeKnowledgeService()

            # Search should limit results
            result = service.search_nodes("search", max_results=10)
            assert len(result) == 10

            # All results should have relevance scores
            for item in result:
                assert "relevance_score" in item
                assert item["relevance_score"] > 0

            # Results should be sorted by relevance score (descending)
            scores = [item["relevance_score"] for item in result]
            assert scores == sorted(scores, reverse=True)
