from langgraph.graph import END, StateGraph
from src.nodes import GraphState, NodeProcessor


class RAGComparisonWorkflow:
    def __init__(self):
        self.processor = NodeProcessor()
        self.graph = self._build_graph()

    def _build_graph(self):
        """Build the LangGraph workflow"""
        workflow = StateGraph(GraphState)

        # Add nodes
        workflow.add_node("rag_node", self.processor.node_with_rag)
        workflow.add_node("no_rag_node", self.processor.node_without_rag)
        workflow.add_node("comparison_node", self.processor.comparison_node)

        # Set entry point
        workflow.set_entry_point("rag_node")

        # Add edges - run both nodes in parallel, then compare
        workflow.add_edge("rag_node", "no_rag_node")
        workflow.add_edge("no_rag_node", "comparison_node")
        workflow.add_edge("comparison_node", END)

        return workflow.compile()

    def run(self, query: str, node_type: str = None) -> dict:
        """Run the comparison workflow"""
        initial_state = {
            "query": query,
            "node_type": node_type,
            "response_with_rag": "",
            "response_without_rag": "",
            "context": "",
        }

        result = self.graph.invoke(initial_state)
        return result


# Create a graph instance for LangGraph Studio
graph = RAGComparisonWorkflow().graph
