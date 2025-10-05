import pytest

from workflow_agent.agents.nodes import WorkflowAgentNodes


def _make_nodes() -> WorkflowAgentNodes:
    return WorkflowAgentNodes.__new__(WorkflowAgentNodes)


def test_validation_finds_tool_memory_connections():
    nodes = _make_nodes()
    workflow = {
        "nodes": [
            {"id": "ai", "type": "AI_AGENT", "subtype": "OPENAI", "name": "ai"},
            {"id": "tool1", "type": "TOOL", "subtype": "SOME_TOOL", "name": "t1"},
            {"id": "mem1", "type": "MEMORY", "subtype": "CONVERSATION_BUFFER", "name": "m1"},
            {"id": "act", "type": "ACTION", "subtype": "HTTP_REQUEST", "name": "act"},
        ],
        "connections": [
            {
                "id": "c1",
                "from_node": "ai",
                "to_node": "tool1",
                "output_key": "result",
                "conversion_function": "",
            },
            {
                "id": "c2",
                "from_node": "mem1",
                "to_node": "ai",
                "output_key": "result",
                "conversion_function": "",
            },
            {
                "id": "c3",
                "from_node": "ai",
                "to_node": "act",
                "output_key": "result",
                "conversion_function": "",
            },
        ],
    }

    errors = nodes._validate_no_tool_memory_connections(workflow)
    assert len(errors) == 2
    assert any("tool1" in e for e in errors)
    assert any("mem1" in e for e in errors)


def test_validation_passes_when_no_tool_memory_in_connections():
    nodes = _make_nodes()
    workflow = {
        "nodes": [
            {
                "id": "ai",
                "type": "AI_AGENT",
                "subtype": "OPENAI",
                "name": "ai",
                "attached_nodes": ["tool1", "mem1"],
            },
            {"id": "tool1", "type": "TOOL", "subtype": "SOME_TOOL", "name": "t1"},
            {"id": "mem1", "type": "MEMORY", "subtype": "CONVERSATION_BUFFER", "name": "m1"},
            {"id": "act", "type": "ACTION", "subtype": "HTTP_REQUEST", "name": "act"},
        ],
        "connections": [
            {
                "id": "c3",
                "from_node": "ai",
                "to_node": "act",
                "output_key": "result",
                "conversion_function": "",
            },
        ],
    }

    errors = nodes._validate_no_tool_memory_connections(workflow)
    assert errors == []
