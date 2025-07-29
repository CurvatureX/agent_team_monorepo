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
    WorkflowStage,
)

logger = structlog.get_logger()

class WorkflowAgent:
    """
    Simplified Workflow Agent based on the 6-node architecture with dynamic routing and interception
    """

    def __init__(self):
        self.nodes = WorkflowAgentNodes()
        self.graph = None
        self._setup_graph()

    def _setup_graph(self):
        """Setup the simplified LangGraph workflow with dynamic router and 6 nodes"""

        # Create the StateGraph with simplified state
        workflow = StateGraph(WorkflowState)

        # Add the dynamic router node as entry point
        workflow.add_node("router", self._route_to_stage)
        
        # Add the 6 core nodes with interception
        workflow.add_node("clarification", self.nodes.clarification_node)
        workflow.add_node("negotiation", self.nodes.negotiation_node)
        workflow.add_node("gap_analysis", self.nodes.gap_analysis_node)
        workflow.add_node("alternative_generation", self.nodes.alternative_solution_generation_node)
        workflow.add_node("workflow_generation", self.nodes.workflow_generation_node)
        workflow.add_node("debug", self.nodes.debug_node)

        # Set router as entry point instead of clarification
        workflow.set_entry_point("router")

        # Router routes to appropriate stage based on current state
        workflow.add_conditional_edges(
            "router",
            self._get_current_stage,
            {
                WorkflowStage.CLARIFICATION: "clarification",
                WorkflowStage.NEGOTIATION: "negotiation", 
                WorkflowStage.GAP_ANALYSIS: "gap_analysis",
                WorkflowStage.ALTERNATIVE_GENERATION: "alternative_generation",
                WorkflowStage.WORKFLOW_GENERATION: "workflow_generation",
                WorkflowStage.DEBUG: "debug",
                WorkflowStage.COMPLETED: END,
            },
        )

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
        logger.info("LangGraph workflow compiled successfully with dynamic router, interception, and 6-node architecture")

    def _route_to_stage(self, state: WorkflowState) -> WorkflowState:
        """
        Router node that determines where to start execution based on current stage.
        This is a lightweight pass-through node that just logs the routing decision.
        """
        current_stage = state.get("stage", WorkflowStage.CLARIFICATION)
        session_id = state.get("session_id", "unknown")
        
        logger.info(
            "🎯 Dynamic Router: Directing execution flow",
            session_id=session_id,
            current_stage=current_stage,
            router_action="route_to_stage"
        )
        
        # Return state unchanged - router is just for flow control
        return state

    def _get_current_stage(self, state: WorkflowState) -> str:
        """
        Get current stage for conditional routing from router node.
        This determines which node the router will direct to.
        """
        current_stage = state.get("stage", WorkflowStage.CLARIFICATION)
        session_id = state.get("session_id", "unknown")
        
        logger.info(
            "🔀 Router Decision: Determining next node",
            session_id=session_id,
            current_stage=current_stage,
            next_node=current_stage,  # stage maps directly to node name
            routing_logic="stage_to_node_mapping"
        )
        
        return current_stage
