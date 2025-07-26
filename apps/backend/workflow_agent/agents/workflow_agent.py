"""
Simplified Workflow Agent based on new architecture
Implements 6 core nodes: Clarification, Negotiation, Gap Analysis,
Alternative Solution Generation, Workflow Generation, and Debug
"""

import asyncio
import time
from typing import Any, Dict, Optional

import structlog
from langgraph.graph import END, StateGraph

from .nodes import WorkflowAgentNodes
from .state import ClarificationContext, Conversation, WorkflowOrigin, WorkflowStage, WorkflowState

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

    def _create_initial_state(
        self, user_input: str, session_id: Optional[str] = None
    ) -> WorkflowState:
        """Create initial workflow state"""
        current_time = time.time()
        session_id = session_id or f"session_{int(current_time)}"

        return {
            "metadata": {
                "session_id": session_id,
                "user_id": "anonymous",
                "created_at": current_time,
                "updated_at": current_time,
            },
            "stage": WorkflowStage.CLARIFICATION,
            "execution_history": [],
            "clarification_context": {
                "origin": WorkflowOrigin.NEW_WORKFLOW,
                "pending_questions": [],
            },
            "conversations": [{"role": "user", "text": user_input}],
            "intent_summary": "",
            "gaps": [],
            "alternatives": [],
            "current_workflow": {},
            "debug_result": "",
            "debug_loop_count": 0,
        }

    async def generate_workflow(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
        user_preferences: Optional[Dict[str, Any]] = None,
        thread_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a workflow using the simplified 6-node process
        """
        logger.info("Starting simplified workflow generation", description=user_input)

        try:
            # Initialize state
            initial_state = self._create_initial_state(user_input, session_id)

            # Update metadata if provided
            if user_id:
                initial_state["metadata"]["user_id"] = user_id

            # Run the graph
            config = {"configurable": {"thread_id": thread_id or "default"}}
            final_state = await self.graph.ainvoke(initial_state, config=config)

            # Extract results
            current_workflow = final_state.get("current_workflow", {})
            errors = []
            if final_state.get("debug_result"):
                try:
                    import json

                    debug_info = json.loads(final_state["debug_result"])
                    if not debug_info.get("success", False):
                        errors = debug_info.get("errors", [])
                except (json.JSONDecodeError, TypeError):
                    if "error" in final_state.get("debug_result", "").lower():
                        errors = [final_state["debug_result"]]

            success = final_state.get("stage") == "completed" and len(errors) == 0

            # Prepare response in expected format
            result = {
                "success": success,
                "workflow": current_workflow if success else None,
                "suggestions": [],
                "missing_info": [],
                "errors": errors,
                "session_id": final_state["metadata"]["session_id"],
                "stage": final_state.get("stage"),
                "conversations": final_state.get("conversations", []),
                "intent_summary": final_state.get("intent_summary", ""),
                "gaps": final_state.get("gaps", []),
                "alternatives": final_state.get("alternatives", []),
            }

            logger.info(
                "Simplified workflow generation completed",
                success=success,
                stage=final_state.get("stage"),
                errors=len(errors),
            )

            return result

        except Exception as e:
            logger.error("Failed to generate workflow", error=str(e))
            return {
                "success": False,
                "workflow": None,
                "suggestions": [],
                "missing_info": [],
                "errors": [f"Internal error: {str(e)}"],
                "session_id": session_id,
                "stage": "error",
                "conversations": [],
                "intent_summary": "",
                "gaps": [],
                "alternatives": [],
            }

    async def continue_conversation(
        self,
        session_id: str,
        user_response: str,
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Continue the conversation by adding user response and running the graph
        """
        logger.info("Continuing conversation", session_id=session_id)

        try:
            # For this simplified version, we'll create a new state with the conversation
            # In a full implementation, you'd retrieve the previous state

            # Create a state with the user response
            current_state = {
                "metadata": {
                    "session_id": session_id,
                    "user_id": "anonymous",
                    "created_at": time.time(),
                    "updated_at": time.time(),
                },
                "stage": WorkflowStage.CLARIFICATION,  # Start from clarification with new input
                "execution_history": [],
                "clarification_context": {
                    "origin": WorkflowOrigin.NEW_WORKFLOW,
                    "pending_questions": [],
                },
                "conversations": [{"role": "user", "text": user_response}],
                "intent_summary": "",
                "gaps": [],
                "alternatives": [],
                "current_workflow": {},
                "debug_result": "",
                "debug_loop_count": 0,
            }

            # Run the graph
            config = {"configurable": {"thread_id": thread_id or session_id}}
            final_state = await self.graph.ainvoke(current_state, config=config)

            # Extract results similar to generate_workflow
            current_workflow = final_state.get("current_workflow", {})
            errors = []
            if final_state.get("debug_result"):
                try:
                    import json

                    debug_info = json.loads(final_state["debug_result"])
                    if not debug_info.get("success", False):
                        errors = debug_info.get("errors", [])
                except (json.JSONDecodeError, TypeError):
                    if "error" in final_state.get("debug_result", "").lower():
                        errors = [final_state["debug_result"]]

            success = final_state.get("stage") == "completed" and len(errors) == 0

            response = {
                "success": success,
                "session_id": session_id,
                "stage": final_state.get("stage"),
                "errors": errors,
                "conversations": final_state.get("conversations", []),
                "intent_summary": final_state.get("intent_summary", ""),
                "gaps": final_state.get("gaps", []),
                "alternatives": final_state.get("alternatives", []),
            }

            # Add workflow if completed
            if success and current_workflow:
                response["workflow"] = current_workflow

            logger.info(
                "Conversation continued",
                session_id=session_id,
                stage=response["stage"],
                success=success,
            )

            return response

        except Exception as e:
            logger.error("Failed to continue conversation", session_id=session_id, error=str(e))
            return {
                "success": False,
                "session_id": session_id,
                "errors": [f"Internal error: {str(e)}"],
                "stage": "error",
                "conversations": [],
                "intent_summary": "",
                "gaps": [],
                "alternatives": [],
            }

    def get_session_state(self, session_id: str) -> Dict[str, Any]:
        """Get current session state (placeholder for simplified version)"""
        return {}

    async def validate_workflow_dsl(self, workflow_dsl: Dict[str, Any]) -> Dict[str, Any]:
        """Validate workflow DSL (placeholder for simplified version)"""
        try:
            # Basic validation
            if not workflow_dsl:
                return {
                    "success": False,
                    "validation_results": {
                        "syntax_valid": False,
                        "logic_valid": False,
                        "overall_valid": False,
                        "completeness_score": 0.0,
                        "errors": ["Empty workflow"],
                        "warnings": [],
                    },
                    "errors": [],
                }

            nodes = workflow_dsl.get("nodes", [])
            connections = workflow_dsl.get("connections", [])

            errors = []
            warnings = []

            if not nodes:
                errors.append("No nodes in workflow")

            if len(nodes) > 1 and not connections:
                warnings.append("Multi-node workflow without connections")

            is_valid = len(errors) == 0
            completeness_score = 0.8 if is_valid else 0.2

            return {
                "success": True,
                "validation_results": {
                    "syntax_valid": is_valid,
                    "logic_valid": is_valid,
                    "overall_valid": is_valid,
                    "completeness_score": completeness_score,
                    "errors": errors,
                    "warnings": warnings,
                },
                "errors": [],
            }

        except Exception as e:
            logger.error("Failed to validate workflow DSL", error=str(e))
            return {
                "success": False,
                "validation_results": {},
                "errors": [f"Validation error: {str(e)}"],
            }
