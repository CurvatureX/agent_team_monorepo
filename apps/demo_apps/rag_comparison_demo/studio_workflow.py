"""
Standalone workflow file for LangGraph Studio compatibility

This workflow compares RAG vs non-RAG responses to user queries.
Input: {"query": "your question here", "node_type": "", "response_with_rag": "", "response_without_rag": "", "context": ""}
Note: Only "query" is required. Leave other fields as empty strings.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from langgraph.graph import END, StateGraph

# Import from local modules
from src.nodes import GraphState, NodeProcessor

load_dotenv()


def create_graph():
    """Create the RAG comparison workflow graph"""

    # Initialize the node processor
    processor = NodeProcessor()

    # Create the graph
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("rag_node", processor.node_with_rag)
    workflow.add_node("no_rag_node", processor.node_without_rag)
    workflow.add_node("comparison_node", processor.comparison_node)

    # Set entry point
    workflow.set_entry_point("rag_node")

    # Add edges - run both nodes sequentially, then compare
    workflow.add_edge("rag_node", "no_rag_node")
    workflow.add_edge("no_rag_node", "comparison_node")
    workflow.add_edge("comparison_node", END)

    return workflow.compile()


# Create graph instance for LangGraph Studio
graph = create_graph()
