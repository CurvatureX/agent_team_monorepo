"""
Simplified Workflow Agent based on optimized architecture
Implements 2 core nodes: Clarification and Workflow Generation
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
    Optimized Workflow Agent with 2-node architecture for better user experience
    """

    def __init__(self):
        self.nodes = WorkflowAgentNodes()
        self.graph = None
        self._setup_graph()

    def _setup_graph(self):
        """Setup the optimized LangGraph workflow with 2 nodes"""

        # Create the StateGraph with simplified state
        workflow = StateGraph(WorkflowState)

        # Add the 2 core nodes
        workflow.add_node("clarification", self.nodes.clarification_node)
        workflow.add_node("workflow_generation", self.nodes.workflow_generation_node)

        # Set clarification as entry point directly
        workflow.set_entry_point("clarification")

        # Add conditional edges based on the optimized flow
        workflow.add_conditional_edges(
            "clarification",
            self.nodes.should_continue,
            {
                "clarification": "clarification",  # Continue clarification if needs more info
                "workflow_generation": "workflow_generation",  # Generate workflow when ready
                "END": END,  # Wait for user input
            },
        )

        workflow.add_conditional_edges(
            "workflow_generation",
            self.nodes.should_continue,
            {
                "END": END,  # Workflow generation completes the flow
            },
        )

        # Compile the graph
        self.graph = workflow.compile()
        logger.info("LangGraph workflow compiled successfully with optimized 2-node architecture")
    
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
