"""
Unit tests for NodeIdGenerator
"""

import pytest

from shared.models.node_enums import ActionSubtype, FlowSubtype, NodeType, TriggerSubtype
from workflow_engine.utils.node_id_generator import NodeIdGenerator


class TestNodeIdGenerator:
    """Test cases for NodeIdGenerator."""

    def test_is_valid_node_id(self):
        """Test node ID validation."""
        # Valid IDs
        assert NodeIdGenerator.is_valid_node_id("node_123")
        assert NodeIdGenerator.is_valid_node_id("trigger_manual_a3b4c5d6")
        assert NodeIdGenerator.is_valid_node_id("_private_node")
        assert NodeIdGenerator.is_valid_node_id("node-with-hyphens")
        assert NodeIdGenerator.is_valid_node_id("UPPERCASE_NODE")

        # Invalid IDs
        assert not NodeIdGenerator.is_valid_node_id("")
        assert not NodeIdGenerator.is_valid_node_id("a")  # Too short
        assert not NodeIdGenerator.is_valid_node_id("ab")  # Too short
        assert not NodeIdGenerator.is_valid_node_id("123_node")  # Starts with number
        assert not NodeIdGenerator.is_valid_node_id("node with spaces")
        assert not NodeIdGenerator.is_valid_node_id("node@special")
        assert not NodeIdGenerator.is_valid_node_id("node.with.dots")
        assert not NodeIdGenerator.is_valid_node_id("a" * 101)  # Too long

        # Reserved keywords
        assert not NodeIdGenerator.is_valid_node_id("start")
        assert not NodeIdGenerator.is_valid_node_id("end")
        assert not NodeIdGenerator.is_valid_node_id("workflow")

    def test_generate_node_id(self):
        """Test node ID generation."""
        existing_ids = {"trigger_manual_12345678", "action_http_request_87654321"}

        # Generate new ID
        node_id = NodeIdGenerator.generate_node_id(
            node_type=NodeType.ACTION.value,
            node_subtype=ActionSubtype.HTTP_REQUEST.value,
            node_name="Call API",
            existing_ids=existing_ids,
        )

        # Check format
        assert node_id.startswith("action_http_request_")
        assert len(node_id) > len("action_http_request_")
        assert node_id not in existing_ids
        assert NodeIdGenerator.is_valid_node_id(node_id)

    def test_clean_identifier(self):
        """Test identifier cleaning."""
        # Test various inputs
        assert NodeIdGenerator._clean_identifier("ACTION_NODE") == "action"
        assert NodeIdGenerator._clean_identifier("HTTP REQUEST") == "http_request"
        assert NodeIdGenerator._clean_identifier("API-Call") == "api_call"
        assert NodeIdGenerator._clean_identifier("123test") == "n123test"
        assert NodeIdGenerator._clean_identifier("@#$%") == "unknown"
        assert NodeIdGenerator._clean_identifier("") == "unknown"
        assert NodeIdGenerator._clean_identifier("  spaces  ") == "spaces"

    def test_ensure_unique_node_ids_no_changes(self):
        """Test ensuring unique IDs when all are already valid."""
        nodes = [
            {
                "id": "trigger_manual_12345678",
                "name": "Start",
                "type": NodeType.TRIGGER.value,
                "subtype": TriggerSubtype.MANUAL.value,
            },
            {
                "id": "action_http_87654321",
                "name": "API Call",
                "type": NodeType.ACTION.value,
                "subtype": ActionSubtype.HTTP_REQUEST.value,
            },
        ]

        result = NodeIdGenerator.ensure_unique_node_ids(nodes.copy())

        # No changes should be made
        assert result[0]["id"] == "trigger_manual_12345678"
        assert result[1]["id"] == "action_http_87654321"

    def test_ensure_unique_node_ids_empty_ids(self):
        """Test generating IDs for nodes without IDs."""
        nodes = [
            {
                "id": "",
                "name": "Start",
                "type": NodeType.TRIGGER.value,
                "subtype": TriggerSubtype.MANUAL.value,
            },
            {
                "id": None,
                "name": "API Call",
                "type": NodeType.ACTION.value,
                "subtype": ActionSubtype.HTTP_REQUEST.value,
            },
            {
                "name": "End",
                "type": NodeType.ACTION.value,
                "subtype": ActionSubtype.DATA_TRANSFORMATION.value,
            },  # No id field
        ]

        result = NodeIdGenerator.ensure_unique_node_ids(nodes)

        # All should have valid IDs
        for node in result:
            assert "id" in node
            assert NodeIdGenerator.is_valid_node_id(node["id"])

        # All IDs should be unique
        ids = [node["id"] for node in result]
        assert len(ids) == len(set(ids))

    def test_ensure_unique_node_ids_duplicates(self):
        """Test handling duplicate IDs."""
        nodes = [
            {
                "id": "node_1",
                "name": "First",
                "type": NodeType.ACTION.value,
                "subtype": ActionSubtype.HTTP_REQUEST.value,
            },
            {
                "id": "node_1",
                "name": "Second",
                "type": NodeType.ACTION.value,
                "subtype": ActionSubtype.HTTP_REQUEST.value,
            },
            {
                "id": "node_1",
                "name": "Third",
                "type": NodeType.TRIGGER.value,
                "subtype": TriggerSubtype.MANUAL.value,
            },
        ]

        result = NodeIdGenerator.ensure_unique_node_ids(nodes)

        # First node should keep its ID
        assert result[0]["id"] == "node_1"

        # Other nodes should get new IDs
        assert result[1]["id"] != "node_1"
        assert result[2]["id"] != "node_1"
        assert result[1]["id"] != result[2]["id"]

        # All should be valid
        for node in result:
            assert NodeIdGenerator.is_valid_node_id(node["id"])

    def test_ensure_unique_node_ids_reserved_keywords(self):
        """Test handling reserved keywords."""
        nodes = [
            {
                "id": "start",
                "name": "Start Node",
                "type": NodeType.TRIGGER.value,
                "subtype": TriggerSubtype.MANUAL.value,
            },
            {
                "id": "end",
                "name": "End Node",
                "type": NodeType.ACTION.value,
                "subtype": ActionSubtype.HTTP_REQUEST.value,
            },
            {
                "id": "workflow",
                "name": "Workflow Node",
                "type": NodeType.ACTION.value,
                "subtype": ActionSubtype.DATA_TRANSFORMATION.value,
            },
        ]

        result = NodeIdGenerator.ensure_unique_node_ids(nodes)

        # All reserved IDs should be replaced
        for node in result:
            assert node["id"] not in NodeIdGenerator.RESERVED_IDS
            assert NodeIdGenerator.is_valid_node_id(node["id"])

    def test_update_connection_references(self):
        """Test updating connection references after ID changes."""
        connections = {
            "old_node_1": {
                "connection_types": {
                    "main": {
                        "connections": [
                            {"node": "old_node_2", "type": "main", "index": 0},
                            {"node": "old_node_3", "type": "main", "index": 1},
                        ]
                    }
                }
            },
            "old_node_2": {
                "connection_types": {
                    "main": {"connections": [{"node": "old_node_3", "type": "main", "index": 0}]}
                }
            },
            "old_node_3": {"connection_types": {}},
        }

        id_mapping = {
            "old_node_1": "trigger_manual_12345678",
            "old_node_2": "action_http_87654321",
            "old_node_3": "flow_if_abcdef12",
        }

        result = NodeIdGenerator.update_connection_references(connections, id_mapping)

        # Check source IDs are updated
        assert "trigger_manual_12345678" in result
        assert "action_http_87654321" in result
        assert "flow_if_abcdef12" in result
        assert "old_node_1" not in result

        # Check target IDs in connections are updated
        main_conns = result["trigger_manual_12345678"]["connection_types"]["main"]["connections"]
        assert main_conns[0]["node"] == "action_http_87654321"
        assert main_conns[1]["node"] == "flow_if_abcdef12"

        main_conns = result["action_http_87654321"]["connection_types"]["main"]["connections"]
        assert main_conns[0]["node"] == "flow_if_abcdef12"

    def test_migrate_legacy_ids(self):
        """Test migrating legacy IDs."""
        nodes = [
            {
                "id": "http_request_google",
                "name": "Google Request",
                "type": NodeType.ACTION.value,
                "subtype": ActionSubtype.HTTP_REQUEST.value,
            },
            {
                "id": "if_condition",
                "name": "Check Status",
                "type": NodeType.FLOW.value,
                "subtype": FlowSubtype.IF.value,
            },
            {
                "id": "1234",
                "name": "Invalid ID",
                "type": NodeType.TRIGGER.value,
                "subtype": TriggerSubtype.MANUAL.value,
            },
        ]

        id_mapping = NodeIdGenerator.migrate_legacy_ids(nodes)

        # All nodes should have new IDs
        assert len(id_mapping) == 3

        # All new IDs should be valid
        for old_id, new_id in id_mapping.items():
            assert NodeIdGenerator.is_valid_node_id(new_id)
            assert new_id != old_id

        # Nodes should be updated
        for node in nodes:
            assert node["id"] in id_mapping.values()
            assert NodeIdGenerator.is_valid_node_id(node["id"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
