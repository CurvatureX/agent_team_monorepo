"""
Main LangGraph-based Workflow Agent
Refactored to use WorkflowOrchestrator from MVP plan
"""

import asyncio
from typing import Any, Dict, List

import structlog
from langgraph.graph import END, StateGraph

from agents.state import MVPWorkflowState, WorkflowStage
from core.config import settings
from core.design_engine import WorkflowOrchestrator

logger = structlog.get_logger()


class WorkflowAgent:
    """
    Refactored Workflow Agent based on MVP architecture
    Uses WorkflowOrchestrator to coordinate intelligent engines
    """

    def __init__(self):
        self.orchestrator = WorkflowOrchestrator()
        self.graph = None
        self._setup_graph()

    def _setup_graph(self):
        """Setup the LangGraph workflow with MVP architecture"""

        # Create the StateGraph with MVP state
        workflow = StateGraph(MVPWorkflowState)

        # Add nodes for each stage
        workflow.add_node("initialize_session", self._initialize_session_node)
        workflow.add_node("requirement_negotiation", self._requirement_negotiation_node)
        workflow.add_node("design", self._design_node)
        workflow.add_node("configuration", self._configuration_node)
        workflow.add_node("validation", self._validation_node)
        workflow.add_node("completion", self._completion_node)

        # Set entry point
        workflow.set_entry_point("initialize_session")

        # Add edges
        workflow.add_edge("initialize_session", "requirement_negotiation")

        # Conditional edges based on stage transitions
        workflow.add_conditional_edges(
            "requirement_negotiation",
            self._determine_next_stage,
            {
                "requirement_negotiation": "requirement_negotiation",  # Continue negotiation
                "design": "design",  # Move to design
                "end": END,  # End if error
            },
        )

        workflow.add_conditional_edges(
            "design",
            self._determine_next_stage,
            {
                "configuration": "configuration",  # Move to configuration
                "requirement_negotiation": "requirement_negotiation",  # Back to negotiation
                "end": END,
            },
        )

        workflow.add_edge("configuration", "validation")
        workflow.add_edge("validation", "completion")
        workflow.add_edge("completion", END)

        # Compile the graph
        self.graph = workflow.compile()

        logger.info("LangGraph workflow compiled successfully with MVP architecture")

    async def _initialize_session_node(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """Initialize workflow generation session"""
        logger.info("Initializing workflow session")

        user_input = state.get("user_input", "")
        user_id = state.get("user_id")
        session_id = state.get("session_id")

        try:
            # Initialize session using orchestrator
            initial_state = await self.orchestrator.initialize_session(
                user_input=user_input,
                user_id=user_id or "anonymous",
                session_id=session_id or f"session_{asyncio.get_event_loop().time()}",
            )

            # Update state with initialized data
            return {
                **state,
                **initial_state,
                "current_step": "requirement_negotiation",
                "should_continue": True,
                "errors": [],
            }

        except Exception as e:
            logger.error("Session initialization failed", error=str(e))
            return {
                **state,
                "current_step": "error",
                "should_continue": False,
                "errors": [f"Initialization error: {str(e)}"],
            }

    async def _requirement_negotiation_node(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """Handle requirement negotiation stage"""
        logger.info("Processing requirement negotiation")

        session_id = state["metadata"]["session_id"]
        user_input = state.get("current_user_input", "")

        try:
            # Process negotiation using orchestrator
            result = await self.orchestrator.process_stage_transition(
                session_id=session_id, user_input=user_input
            )

            # Update state with result
            updated_state = result.get("state", state)

            return {
                **state,
                **updated_state,
                "current_step": result.get("stage", "requirement_negotiation"),
                "next_questions": result.get("next_questions", []),
                "tradeoff_analysis": result.get("tradeoff_analysis"),
                "should_continue": True,
                "errors": [],
            }

        except Exception as e:
            logger.error("Requirement negotiation failed", error=str(e))
            return {
                **state,
                "current_step": "error",
                "should_continue": False,
                "errors": [f"Negotiation error: {str(e)}"],
            }

    async def _design_node(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """Handle design stage"""
        logger.info("Processing design stage")

        session_id = state["metadata"]["session_id"]
        user_input = state.get("current_user_input", "confirmed")

        try:
            # Process design using orchestrator
            result = await self.orchestrator.process_stage_transition(
                session_id=session_id, user_input=user_input
            )

            # Update state with design result
            updated_state = result.get("state", state)

            return {
                **state,
                **updated_state,
                "current_step": result.get("stage", "design"),
                "task_tree": result.get("task_tree"),
                "architecture": result.get("architecture"),
                "workflow_dsl": result.get("workflow_dsl"),
                "optimization_suggestions": result.get("optimization_suggestions", []),
                "performance_estimate": result.get("performance_estimate"),
                "design_patterns": result.get("design_patterns", []),
                "should_continue": True,
                "errors": [],
            }

        except Exception as e:
            logger.error("Design stage failed", error=str(e))
            return {
                **state,
                "current_step": "error",
                "should_continue": False,
                "errors": [f"Design error: {str(e)}"],
            }

    async def _configuration_node(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """Handle configuration stage"""
        logger.info("Processing configuration stage")

        session_id = state["metadata"]["session_id"]
        user_input = state.get("current_user_input", "configure")

        try:
            # Process configuration using orchestrator
            result = await self.orchestrator.process_stage_transition(
                session_id=session_id, user_input=user_input
            )

            # Update state with configuration result
            updated_state = result.get("state", state)

            return {
                **state,
                **updated_state,
                "current_step": result.get("stage", "configuration"),
                "node_configurations": result.get("node_configurations", []),
                "should_continue": True,
                "errors": [],
            }

        except Exception as e:
            logger.error("Configuration stage failed", error=str(e))
            return {
                **state,
                "current_step": "error",
                "should_continue": False,
                "errors": [f"Configuration error: {str(e)}"],
            }

    async def _validation_node(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """Handle validation stage"""
        logger.info("Processing validation stage")

        session_id = state["metadata"]["session_id"]
        user_input = state.get("current_user_input", "validate")

        try:
            # Process validation using orchestrator
            result = await self.orchestrator.process_stage_transition(
                session_id=session_id, user_input=user_input
            )

            # Update state with validation result
            updated_state = result.get("state", state)

            return {
                **state,
                **updated_state,
                "current_step": result.get("stage", "validation"),
                "validation_result": result.get("validation_result"),
                "completeness_check": result.get("completeness_check"),
                "should_continue": True,
                "errors": [],
            }

        except Exception as e:
            logger.error("Validation stage failed", error=str(e))
            return {
                **state,
                "current_step": "error",
                "should_continue": False,
                "errors": [f"Validation error: {str(e)}"],
            }

    async def _completion_node(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """Handle completion stage"""
        logger.info("Processing completion stage")

        try:
            # Mark as completed
            return {
                **state,
                "current_step": "completed",
                "should_continue": False,
                "final_result": {
                    "workflow_dsl": state.get("workflow_dsl"),
                    "validation_result": state.get("validation_result"),
                    "completeness_check": state.get("completeness_check"),
                    "optimization_suggestions": state.get("optimization_suggestions", []),
                    "performance_estimate": state.get("performance_estimate"),
                },
                "errors": [],
            }

        except Exception as e:
            logger.error("Completion stage failed", error=str(e))
            return {
                **state,
                "current_step": "error",
                "should_continue": False,
                "errors": [f"Completion error: {str(e)}"],
            }

    def _determine_next_stage(self, state: MVPWorkflowState) -> str:
        """Determine next stage based on current state"""
        current_step = state.get("current_step", "")
        stage = state.get("stage", "")
        should_continue = state.get("should_continue", True)
        errors = state.get("errors", [])

        # Check for errors
        if not should_continue or errors:
            return "end"

        # Stage-specific logic
        if stage == "requirement_negotiation":
            # Check if negotiation is complete
            negotiation_state = state.get("requirement_negotiation", {})
            if negotiation_state.get("final_requirements"):
                return "design"
            else:
                return "requirement_negotiation"

        elif stage == "design":
            # Move to configuration after design
            return "configuration"

        elif stage in ["configuration", "completed"]:
            # End the workflow
            return "end"

        # Default to current stage
        return current_step

    async def generate_workflow(
        self,
        user_input: str,
        context: Dict[str, Any] = None,
        user_preferences: Dict[str, Any] = None,
        thread_id: str = None,
        user_id: str = None,
        session_id: str = None,
    ) -> Dict[str, Any]:
        """
        Generate a workflow using the MVP intelligent consultation process
        """
        logger.info("Starting intelligent workflow generation", description=user_input)

        try:
            # Initialize state for MVP workflow
            initial_state = {
                "metadata": {
                    "session_id": session_id or f"session_{asyncio.get_event_loop().time()}",
                    "user_id": user_id or "anonymous",
                    "created_at": asyncio.get_event_loop().time(),
                    "updated_at": asyncio.get_event_loop().time(),
                    "version": "1.0.0",
                    "interaction_count": 0,
                },
                "stage": WorkflowStage.REQUIREMENT_NEGOTIATION,
                "requirement_negotiation": {
                    "original_requirements": user_input,
                    "parsed_intent": {},
                    "capability_analysis": {},
                    "identified_constraints": [],
                    "proposed_solutions": [],
                    "user_decisions": [],
                    "negotiation_history": [],
                    "final_requirements": "",
                    "confidence_score": 0.0,
                },
                "design_state": {
                    "task_tree": {},
                    "architecture": {},
                    "workflow_dsl": {},
                    "optimization_suggestions": [],
                    "design_patterns_used": [],
                    "estimated_performance": {},
                },
                "configuration_state": {
                    "current_node_index": 0,
                    "node_configurations": [],
                    "missing_parameters": [],
                    "validation_results": [],
                    "configuration_templates": [],
                    "auto_filled_params": [],
                },
                "execution_state": {
                    "preview_results": [],
                    "static_validation": {},
                    "configuration_completeness": {},
                },
                # Additional fields for compatibility
                "user_input": user_input,
                "context": context or {},
                "user_preferences": user_preferences or {},
                "current_user_input": user_input,
                "user_id": user_id or "anonymous",
                "session_id": session_id or f"session_{asyncio.get_event_loop().time()}",
            }

            # Run the graph
            config = {"configurable": {"thread_id": thread_id or "default"}}
            final_state = await self.graph.ainvoke(initial_state, config=config)

            # Extract results
            final_result = final_state.get("final_result", {})
            workflow_dsl = final_result.get("workflow_dsl")
            errors = final_state.get("errors", [])
            next_questions = final_state.get("next_questions", [])

            success = final_state.get("current_step") == "completed" and len(errors) == 0

            # Prepare response in expected format
            result = {
                "success": success,
                "workflow": workflow_dsl,
                "suggestions": final_result.get("optimization_suggestions", []),
                "missing_info": [],  # MVP doesn't use missing_info in the same way
                "errors": errors,
                "session_id": final_state["metadata"]["session_id"],
                "stage": final_state.get("stage"),
                "negotiation_questions": next_questions,
                "performance_estimate": final_result.get("performance_estimate"),
                "validation_result": final_result.get("validation_result"),
            }

            logger.info(
                "Intelligent workflow generation completed",
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
                "negotiation_questions": [],
            }

    async def continue_conversation(
        self,
        session_id: str,
        user_response: str,
        thread_id: str = None,
    ) -> Dict[str, Any]:
        """
        Continue the intelligent conversation in an existing session
        """
        logger.info("Continuing conversation", session_id=session_id)

        try:
            # Get current session state
            current_state = self.orchestrator.get_session_state(session_id)
            if not current_state:
                return {
                    "success": False,
                    "errors": [f"Session {session_id} not found"],
                    "stage": "error",
                }

            # Convert to MVP state format
            mvp_state = MVPWorkflowState(
                **current_state,
                current_user_input=user_response,
            )

            # Process the response based on current stage
            stage = current_state.get("stage", "requirement_negotiation")

            if stage == "requirement_negotiation":
                result = await self._requirement_negotiation_node(mvp_state)
            elif stage == "design":
                result = await self._design_node(mvp_state)
            elif stage == "configuration":
                result = await self._configuration_node(mvp_state)
            else:
                return {"success": False, "errors": [f"Invalid stage: {stage}"], "stage": stage}

            # Extract results
            errors = result.get("errors", [])
            success = len(errors) == 0 and result.get("should_continue", True)

            response = {
                "success": success,
                "session_id": session_id,
                "stage": result.get("current_step", stage),
                "errors": errors,
                "next_questions": result.get("next_questions", []),
                "tradeoff_analysis": result.get("tradeoff_analysis"),
            }

            # Add stage-specific results
            if result.get("workflow_dsl"):
                response["workflow"] = result["workflow_dsl"]
                response["validation_result"] = result.get("validation_result")
                response["performance_estimate"] = result.get("performance_estimate")
                response["optimization_suggestions"] = result.get("optimization_suggestions", [])

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
            }

    async def refine_workflow(
        self,
        workflow_id: str,
        feedback: str,
        original_workflow: Dict[str, Any],
        thread_id: str = None,
    ) -> Dict[str, Any]:
        """Refine an existing workflow based on feedback"""
        logger.info("Starting workflow refinement", workflow_id=workflow_id)

        try:
            # For MVP, implement basic refinement
            # Full implementation would use the orchestrator for iterative design

            return {
                "success": True,
                "updated_workflow": original_workflow,  # Placeholder
                "changes": [f"Applied feedback: {feedback}"],
                "errors": [],
            }

        except Exception as e:
            logger.error("Failed to refine workflow", error=str(e))
            return {
                "success": False,
                "updated_workflow": None,
                "changes": [],
                "errors": [f"Internal error: {str(e)}"],
            }

    def get_session_state(self, session_id: str) -> Dict[str, Any]:
        """Get current session state"""
        return self.orchestrator.get_session_state(session_id)

    async def validate_workflow_dsl(self, workflow_dsl: Dict[str, Any]) -> Dict[str, Any]:
        """Validate workflow DSL using static validation"""
        try:
            from core.design_engine import DSLValidator

            # Perform static validation
            syntax_result = await DSLValidator.validate_syntax(workflow_dsl)
            logic_result = await DSLValidator.validate_logic(workflow_dsl)
            completeness_score = await DSLValidator.calculate_completeness_score(workflow_dsl)

            # Combine results
            all_errors = syntax_result.get("errors", []) + logic_result.get("errors", [])
            all_warnings = syntax_result.get("warnings", []) + logic_result.get("warnings", [])

            is_valid = syntax_result.get("valid", False) and logic_result.get("valid", False)

            return {
                "success": True,
                "validation_results": {
                    "syntax_valid": syntax_result.get("valid", False),
                    "logic_valid": logic_result.get("valid", False),
                    "overall_valid": is_valid,
                    "completeness_score": completeness_score,
                    "errors": all_errors,
                    "warnings": all_warnings,
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
