"""
Simplified Workflow Agent based on new architecture
Implements 4 core nodes: Clarification, Gap Analysis,
Workflow Generation, and Debug
"""
from langgraph.graph import END, StateGraph

import logging
from .nodes import WorkflowAgentNodes
from .state import (
    WorkflowState,
)

logger = logging.getLogger(__name__)

class WorkflowAgent:
    """
    Simplified Workflow Agent based on the 6-node architecture with dynamic routing and interception
    """

    def __init__(self):
        self.nodes = WorkflowAgentNodes()
        self.graph = None
        self._setup_graph()

    def _setup_graph(self):
        """Setup the simplified LangGraph workflow with 4 nodes"""

        # Create the StateGraph with simplified state
        workflow = StateGraph(WorkflowState)

        # Add the 4 core nodes (removed negotiation, router, and alternative_generation)
        workflow.add_node("clarification", self.nodes.clarification_node)
        workflow.add_node("gap_analysis", self.nodes.gap_analysis_node)
        workflow.add_node("workflow_generation", self.nodes.workflow_generation_node)
        workflow.add_node("debug", self.nodes.debug_node)

        # Set clarification as entry point directly
        workflow.set_entry_point("clarification")

        # Add conditional edges based on the architecture flow
        workflow.add_conditional_edges(
            "clarification",
            self.nodes.should_continue,
            {
                "clarification": "clarification",  # Continue clarification if needs more info
                "gap_analysis": "gap_analysis",
                "END": END,  # Wait for user input
            },
        )

        workflow.add_conditional_edges(
            "gap_analysis",
            self.nodes.should_continue,
            {
                "clarification": "clarification",  # Go back to clarification if has gaps
                "workflow_generation": "workflow_generation",  # Proceed if no gaps
                "END": END,  # End if waiting for user input
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
        logger.info("LangGraph workflow compiled successfully with 4-node architecture")
    
    async def astream(self, state: WorkflowState):
        """
        Async stream method for processing workflow state
        """
        try:
            logger.info("WorkflowAgent.astream called", extra={"stage": state.get('stage')})
            # 使用 LangGraph 的 astream 方法
            chunk_count = 0
            async for chunk in self.graph.astream(state):
                chunk_count += 1
                logger.info("WorkflowAgent yielding chunk", extra={"chunk_count": chunk_count, "chunk_keys": list(chunk.keys())})
                yield chunk
            logger.info("WorkflowAgent.astream completed", extra={"total_chunks": chunk_count})
        except Exception as e:
            logger.error("Error in workflow astream", extra={"error": str(e)})
            import traceback
            logger.error("Traceback details", extra={"traceback": traceback.format_exc()})
            raise
