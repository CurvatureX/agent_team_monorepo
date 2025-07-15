"""
LangGraph graph definition for LangGraph Studio
"""

import os
import sys

# Add the current directory to sys.path to enable imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.workflow_agent import WorkflowAgent

# Create the workflow agent instance
agent = WorkflowAgent()

# Export the compiled graph for LangGraph Studio
graph = agent.graph
