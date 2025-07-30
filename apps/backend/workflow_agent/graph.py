"""
LangGraph graph definition for LangGraph Studio
Simplified 6-node architecture implementation
"""

import os
import sys
from pathlib import Path

# 统一的路径设置
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from agents.workflow_agent import WorkflowAgent

# Create the simplified workflow agent instance
agent = WorkflowAgent()

# Export the compiled graph for LangGraph Studio
# The graph now implements the 6-node architecture:
# Clarification -> Negotiation -> Gap Analysis -> Alternative Generation -> Workflow Generation -> Debug
graph = agent.graph
