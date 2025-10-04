import pytest

from workflow_agent.agents.nodes import WorkflowAgentNodes
from workflow_agent.agents.state import WorkflowStage


def _make_nodes() -> WorkflowAgentNodes:
    """Construct WorkflowAgentNodes without running the heavy initializer."""
    return WorkflowAgentNodes.__new__(WorkflowAgentNodes)

def test_ensure_node_descriptions_populates_missing_descriptions():
    nodes = _make_nodes()
    workflow = {
        "description": "High level workflow",
        "nodes": [
            {
                "id": "node-1",
                "name": "Process Slack message",
                "type": "ACTION",
                "subtype": "SLACK_MESSAGE",
            },
            {
                "id": "node-2",
                "name": "Persist to Notion",
                "type": "ACTION",
                "subtype": "NOTION_UPDATE",
                "description": "",
            },
        ],
    }

    nodes._ensure_node_descriptions(workflow, intent_summary="Sync tasks with Notion")

    for node in workflow["nodes"]:
        assert isinstance(node.get("description"), str) and node["description"].strip(), (
            "Node descriptions should be assigned when missing or blank"
        )


def test_ensure_node_descriptions_raises_when_still_missing():
    nodes = _make_nodes()
    workflow = {"nodes": ["not-a-dict"]}

    with pytest.raises(ValueError):
        nodes._ensure_node_descriptions(workflow)


def test_fail_workflow_generation_marks_state_failed():
    nodes = _make_nodes()
    state = {
        "stage": WorkflowStage.WORKFLOW_GENERATION,
        "conversations": [],
    }

    nodes._fail_workflow_generation(
        state,
        error_message="LLM returned empty response",
        user_message="Unable to create workflow",
    )

    assert state["stage"] == WorkflowStage.FAILED
    assert state["workflow_generation_failed"] is True
    assert state["final_error_message"] == "LLM returned empty response"
    assert "generation_diagnostics" not in state
    assert "current_workflow" not in state
    assert state["conversations"][-1]["role"] == "assistant"
