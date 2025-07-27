"""
Simplified Workflow Agent based on new architecture
Implements 6 core nodes: Clarification, Negotiation, Gap Analysis,
Alternative Solution Generation, Workflow Generation, and Debug
"""
import structlog
from langgraph.graph import END, StateGraph

from agents.nodes import WorkflowAgentNodes
from agents.state import (
    WorkflowState,
)

logger = structlog.get_logger()

class WorkflowAgent:
    """
    Simplified Workflow Agent based on the 6-node architecture
    """

    def __init__(self):
        self.nodes = WorkflowAgentNodes()
        self.graph = None
        self._setup_graph()

    def _setup_graph(self):
        """Setup the simplified LangGraph workflow with 6 nodes"""

        # Create the StateGraph with simplified state
        workflow = StateGraph(WorkflowState)

        # Add the 6 core nodes
        workflow.add_node("clarification", self.nodes.clarification_node)
        workflow.add_node("negotiation", self.nodes.negotiation_node)
        workflow.add_node("gap_analysis", self.nodes.gap_analysis_node)
        workflow.add_node("alternative_generation", self.nodes.alternative_solution_generation_node)
        workflow.add_node("workflow_generation", self.nodes.workflow_generation_node)
        workflow.add_node("debug", self.nodes.debug_node)

        # Set entry point
        workflow.set_entry_point("clarification")

        # Add conditional edges based on the architecture flow
        workflow.add_conditional_edges(
            "clarification",
            self.nodes.should_continue,
            {
                "negotiation": "negotiation",
                "gap_analysis": "gap_analysis",
                "END": END,
            },
        )

        workflow.add_conditional_edges(
            "negotiation",
            self.nodes.should_continue,
            {
                "clarification": "clarification",
                "END": END,
            },
        )

        workflow.add_conditional_edges(
            "gap_analysis",
            self.nodes.should_continue,
            {
                "alternative_generation": "alternative_generation",
                "workflow_generation": "workflow_generation",
                "END": END,
            },
        )

        workflow.add_conditional_edges(
            "alternative_generation",
            self.nodes.should_continue,
            {
                "negotiation": "negotiation",
                "END": END,
            },
        )

        workflow.add_conditional_edges(
            "workflow_generation",
            self.nodes.should_continue,
            {
                "debug": "debug",
                "END": END,
            },
        )

        workflow.add_conditional_edges(
            "debug",
            self.nodes.should_continue,
            {
                "workflow_generation": "workflow_generation",
                "clarification": "clarification",
                "END": END,
            },
        )

        # Compile the graph
        self.graph = workflow.compile()
        logger.info("Simplified LangGraph workflow compiled successfully with 6-node architecture")
