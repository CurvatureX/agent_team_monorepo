"""
LangGraph graph definition for LangGraph Studio
Simplified 6-node architecture implementation
"""

import os
import sys

# Add the current directory to sys.path to enable imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.workflow_agent import WorkflowAgent

# Create the simplified workflow agent instance
agent = WorkflowAgent()

# Export the compiled graph for LangGraph Studio
# The graph now implements the 6-node architecture:
# Clarification -> Negotiation -> Gap Analysis -> Alternative Generation -> Workflow Generation -> Debug
graph = agent.graph
