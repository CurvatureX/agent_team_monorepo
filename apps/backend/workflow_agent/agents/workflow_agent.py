"""
Main LangGraph-based Workflow Agent
Refactored to use WorkflowOrchestrator from MVP plan
"""

import asyncio
from typing import Any, Dict, List, Optional

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

    def _get_session_id(self, state: MVPWorkflowState) -> Optional[str]:
        """Safely extract session_id from state"""
        metadata = state.get("metadata", {})
        return metadata.get("session_id")

    async def _assess_clarification_need(self, user_input: str) -> bool:
        """Assess if clarification questions are needed based on user input clarity"""
        try:
            # Use the prompt engine to assess if clarification is needed
            from core.prompt_engine import get_prompt_engine

            prompt_engine = get_prompt_engine()

            # Render the assessment prompt
            assessment_prompt = await prompt_engine.render_prompt(
                "clarification_assessment", user_input=user_input
            )

            # Call the LLM to assess clarity
            response = await self.orchestrator.analyzer.scanner._call_llm(
                assessment_prompt, model="gpt-4o-mini"
            )

            # Parse the response
            if response and isinstance(response, dict):
                response_text = response.get("response", "").strip()
                response_upper = response_text.upper()
                # Check for explicit assessment response (exact matches)
                if response_upper == "CLEAR" or response_upper.startswith("CLEAR "):
                    return False  # No clarification needed
                elif "NEEDS_CLARIFICATION" in response_upper:
                    return True  # Clarification needed
                else:
                    # Fallback: Look for indicators that clarification is needed
                    response_lower = response_text.lower()
                    needs_clarification = any(
                        word in response_lower
                        for word in [
                            "clarification",
                            "unclear",
                            "ambiguous",
                            "more details",
                            "specific",
                            "vague",
                            "insufficient",
                            "需要澄清",
                            "不清楚",
                            "模糊",
                        ]
                    )
                    return needs_clarification

            return True  # Default to needing clarification if unsure

        except Exception as e:
            logger.error(f"Failed to assess clarification need: {e}")
            # Default to needing clarification on error
            return True

    async def _generate_requirement_clarification_questions(self, user_input: str) -> List[str]:
        """Generate clarification questions based on user requirements when capability_gaps is empty"""
        try:
            # Use the prompt engine to generate clarification questions
            from core.prompt_engine import get_prompt_engine

            prompt_engine = get_prompt_engine()

            # Render the clarification prompt
            clarification_prompt = await prompt_engine.render_prompt(
                "requirement_clarification", user_input=user_input
            )

            # Call the LLM to generate questions
            response = await self.orchestrator.analyzer.scanner._call_llm(
                clarification_prompt, model="gpt-4o-mini"
            )

            # Parse the response into a list of questions
            if response and isinstance(response, dict):
                # Extract the response content
                response_text = response.get("response", "") if "response" in response else ""
                if response_text:
                    # Split by newlines and filter out empty lines
                    questions = [q.strip() for q in response_text.split("\n") if q.strip()]
                    # Remove any numbering or bullet points
                    cleaned_questions = []
                    for q in questions:
                        # Remove common prefixes like "1.", "- ", "• "
                        q = q.lstrip("0123456789. -•").strip()
                        if q and q.endswith("?"):
                            cleaned_questions.append(q)

                    return cleaned_questions[:5]  # Limit to 5 questions

            return []

        except Exception as e:
            logger.error(f"Failed to generate requirement clarification questions: {e}")
            # Return fallback questions based on common patterns
            return [
                "能否详细描述一下您希望自动化的具体流程？",
                "这个工作流需要处理哪些类型的数据？",
                "您希望多久运行一次这个工作流？",
                "是否需要与特定的系统或服务集成？",
            ]

    def _setup_graph(self):
        """Setup the LangGraph workflow with 5-phase architecture"""

        # Create the StateGraph with updated state
        workflow = StateGraph(MVPWorkflowState)

        # Add a node to collect user input at the beginning for debugging
        workflow.add_node("collect_user_input", self._collect_user_input_node)

        # Add nodes for each phase according to architecture
        workflow.add_node("initialize_session", self._initialize_session_node)

        # Phase 1: Consultant Phase
        workflow.add_node("consultant_phase", self._consultant_phase_node)
        workflow.add_node("capability_scan", self._capability_scan_node)
        workflow.add_node("constraint_identification", self._constraint_identification_node)
        workflow.add_node("solution_research", self._solution_research_node)

        # Phase 2: Requirement Negotiation
        workflow.add_node("requirement_negotiation", self._requirement_negotiation_node)
        workflow.add_node("tradeoff_presentation", self._tradeoff_presentation_node)
        workflow.add_node("requirement_adjustment", self._requirement_adjustment_node)
        workflow.add_node("implementation_confirmation", self._implementation_confirmation_node)

        # Phase 3: Design Phase
        workflow.add_node("design", self._design_node)
        workflow.add_node("task_decomposition", self._task_decomposition_node)
        workflow.add_node("architecture_design", self._architecture_design_node)
        workflow.add_node("dsl_generation", self._dsl_generation_node)

        # Phase 4: Configuration Phase
        workflow.add_node("configuration", self._configuration_node)
        workflow.add_node("node_configuration", self._node_configuration_node)
        workflow.add_node("parameter_validation", self._parameter_validation_node)
        workflow.add_node("missing_info_collection", self._missing_info_collection_node)

        # Phase 5: Testing & Deployment
        workflow.add_node("testing", self._testing_node)
        workflow.add_node("automated_testing", self._automated_testing_node)
        workflow.add_node("error_fixing", self._error_fixing_node)
        workflow.add_node("deployment", self._deployment_node)
        workflow.add_node("completion", self._completion_node)

        # Human-in-the-loop nodes for debugging
        workflow.add_node(
            "wait_for_requirements_confirmation", self._wait_for_requirements_confirmation_node
        )
        workflow.add_node("wait_for_design_confirmation", self._wait_for_design_confirmation_node)
        workflow.add_node("wait_for_missing_info", self._wait_for_missing_info_node)

        # Set entry point
        workflow.set_entry_point("collect_user_input")

        # Add edges according to architecture flow
        workflow.add_edge("collect_user_input", "initialize_session")
        workflow.add_edge("initialize_session", "consultant_phase")

        # Consultant phase flow - conditional based on whether waiting for user input
        workflow.add_conditional_edges(
            "consultant_phase",
            self._determine_next_stage,
            {
                "capability_scan": "capability_scan",
                "wait_for_user": "wait_for_requirements_confirmation",
                "requirement_negotiation": "requirement_negotiation",
                "end": END,
            },
        )
        workflow.add_conditional_edges(
            "capability_scan",
            self._determine_next_stage,
            {
                "capability_scan": "capability_scan",  # Handle self-loop edge case
                "constraint_identification": "constraint_identification",
                "solution_research": "solution_research",
                "requirement_negotiation": "requirement_negotiation",
                "end": END,
            },
        )
        workflow.add_edge("constraint_identification", "solution_research")
        workflow.add_edge("solution_research", "requirement_negotiation")

        # Negotiation phase flow
        workflow.add_conditional_edges(
            "requirement_negotiation",
            self._determine_next_stage,
            {
                "requirement_negotiation": "requirement_negotiation",  # Continue negotiation
                "tradeoff_presentation": "tradeoff_presentation",
                "requirement_adjustment": "requirement_adjustment",
                "implementation_confirmation": "implementation_confirmation",
                "design": "design",  # Move to design
                "end": END,
            },
        )
        workflow.add_edge("tradeoff_presentation", "requirement_adjustment")
        workflow.add_edge("requirement_adjustment", "implementation_confirmation")
        workflow.add_edge("implementation_confirmation", "wait_for_requirements_confirmation")
        workflow.add_edge("wait_for_requirements_confirmation", "design")

        # Design phase flow
        workflow.add_conditional_edges(
            "design",
            self._determine_next_stage,
            {
                "task_decomposition": "task_decomposition",
                "architecture_design": "architecture_design",
                "dsl_generation": "dsl_generation",
                "configuration": "configuration",
                "requirement_negotiation": "requirement_negotiation",  # Back to negotiation
                "end": END,
            },
        )
        workflow.add_edge("task_decomposition", "architecture_design")
        workflow.add_edge("architecture_design", "dsl_generation")
        workflow.add_edge("dsl_generation", "wait_for_design_confirmation")
        workflow.add_edge("wait_for_design_confirmation", "configuration")

        # Configuration phase flow
        workflow.add_conditional_edges(
            "configuration",
            self._determine_next_stage,
            {
                "node_configuration": "node_configuration",
                "parameter_validation": "parameter_validation",
                "missing_info_collection": "missing_info_collection",
                "testing": "testing",
                "design": "design",  # Back to design
                "end": END,
            },
        )
        workflow.add_edge("node_configuration", "parameter_validation")
        workflow.add_edge("parameter_validation", "missing_info_collection")
        workflow.add_edge("missing_info_collection", "wait_for_missing_info")
        workflow.add_edge("wait_for_missing_info", "testing")

        # Testing & Deployment phase flow
        workflow.add_conditional_edges(
            "testing",
            self._determine_next_stage,
            {
                "automated_testing": "automated_testing",
                "error_fixing": "error_fixing",
                "deployment": "deployment",
                "configuration": "configuration",  # Back to configuration
                "end": END,
            },
        )
        workflow.add_edge("automated_testing", "error_fixing")
        workflow.add_edge("error_fixing", "deployment")
        workflow.add_edge("deployment", "completion")
        workflow.add_edge("completion", END)

        # Compile the graph, interrupting before the session is initialized to allow for user input.
        self.graph = workflow.compile(interrupt_before=["initialize_session"])

        logger.info("LangGraph workflow compiled successfully with 5-phase architecture")

    async def _collect_user_input_node(self, state: MVPWorkflowState) -> MVPWorkflowState:
        """Node to wait for user input for debugging in LangGraph Studio."""
        logger.info(
            "Collect User Input: Waiting for user to provide 'user_input' in the state for debugging."
        )
        # This node is a placeholder. The user is expected to fill in the 'user_input'
        # field in the LangGraph Studio debugger.
        return state

    async def _wait_for_requirements_confirmation_node(
        self, state: MVPWorkflowState
    ) -> MVPWorkflowState:
        """Node to wait for user to confirm final requirements."""
        logger.info(
            "Waiting for Confirmation: Final requirements are ready. "
            "Please review and provide 'user_input' (e.g., 'confirm') to proceed to design."
        )
        return state

    async def _wait_for_design_confirmation_node(self, state: MVPWorkflowState) -> MVPWorkflowState:
        """Node to wait for user to confirm the generated design."""
        logger.info(
            "Waiting for Confirmation: Workflow design is complete. "
            "Please review the DSL and provide 'user_input' (e.g., 'confirm') to proceed to configuration."
        )
        return state

    async def _wait_for_missing_info_node(self, state: MVPWorkflowState) -> MVPWorkflowState:
        """Node to wait for user to provide missing information."""
        logger.info(
            "Waiting for Input: The workflow requires additional information. "
            "Please provide the missing info in the state and then proceed."
        )
        return state

    async def _initialize_session_node(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """Initialize workflow generation session"""
        logger.info("Initializing workflow session")

        user_input = state.get("user_input", "")
        user_id = state.get("user_id")
        session_id = state.get("session_id")

        # Always generate a fresh session_id to avoid stale sessions
        if not session_id or "session_" in str(session_id):
            session_id = None

        try:
            # Initialize session using orchestrator
            actual_session_id = session_id or f"session_{asyncio.get_event_loop().time()}"
            logger.info(f"Initializing session with session_id: {actual_session_id}")

            initial_state = await self.orchestrator.initialize_session(
                user_input=user_input,
                user_id=user_id or "anonymous",
                session_id=actual_session_id,
            )

            # Update state with initialized data
            return {
                **initial_state,
                **state,
                **initial_state,  # Ensure metadata and important fields from initial_state take precedence
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

    # Phase 1: Consultant Phase Nodes
    async def _consultant_phase_node(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """Initial requirement capture and intent parsing"""
        logger.info("Processing consultant phase")

        try:
            user_input = state.get("user_input", "")
            session_id = self._get_session_id(state)

            logger.info(f"Consultant phase looking for session_id: {session_id}")
            logger.info(
                f"Available sessions in state_store: {list(self.orchestrator.state_store.keys())}"
            )

            if not session_id:
                logger.error("No session_id found in state metadata")
                return {
                    **state,
                    "current_step": "error",
                    "should_continue": False,
                    "errors": ["Missing session_id in state metadata"],
                }

            # Get the current state from initialization
            current_state = self.orchestrator.get_session_state(session_id)
            if not current_state:
                # Session not found, try to reinitialize it
                logger.warning(f"Session {session_id} not found, reinitializing...")
                current_state = await self.orchestrator.initialize_session(
                    user_input=user_input,
                    user_id="anonymous",
                    session_id=session_id,
                )

            # Extract the parsed requirements and capability analysis
            requirement_data = current_state.get("requirement_negotiation", {})
            parsed_intent = requirement_data.get("parsed_intent", {})
            capability_analysis = requirement_data.get("capability_analysis", {})

            # Get existing negotiation history
            negotiation_history = requirement_data.get("negotiation_history", [])

            # Check if clarification assessment has already been done
            existing_assessment = requirement_data.get("need_clarification")
            if existing_assessment is not None:
                logger.info(f"Using existing clarification assessment: {existing_assessment}")
                needs_clarification = existing_assessment
            else:
                # Assess if clarification is needed based on input clarity
                logger.info(f"Assessing if clarification is needed for input: {user_input}")
                needs_clarification = await self._assess_clarification_need(user_input)
                logger.info(f"Clarification assessment result: {needs_clarification}")

                # Store the assessment result in the state
                current_state["requirement_negotiation"]["need_clarification"] = needs_clarification

            if needs_clarification:
                # Input is unclear or incomplete, generate clarification questions
                logger.info("Input needs clarification, generating questions...")

                # Extract capability gaps for question generation
                capability_gaps = (
                    getattr(capability_analysis, "capability_gaps", [])
                    if capability_analysis
                    else []
                )

                # Generate AI questions for clarification
                if not capability_gaps and user_input:
                    # Generate clarification questions based on the user's requirements
                    ai_questions = await self._generate_requirement_clarification_questions(
                        user_input
                    )
                    logger.info(f"Generated requirement-based questions: {ai_questions}")
                else:
                    ai_questions = await self.orchestrator.negotiator.generate_contextual_questions(
                        gaps=capability_gaps,
                        capability_analysis=capability_analysis,
                        history=negotiation_history,
                    )
                    logger.info(f"Generated capability-based questions: {ai_questions}")

                # Add user's original input as user message
                negotiation_history.append(
                    {
                        "role": "user",
                        "content": user_input,
                        "timestamp": current_state["metadata"]["updated_at"],
                    }
                )

                # Add AI questions as assistant message
                ai_message = ""
                if ai_questions:
                    ai_message = (
                        "\n".join(ai_questions)
                        if isinstance(ai_questions, list)
                        else str(ai_questions)
                    )
                    negotiation_history.append(
                        {
                            "role": "assistant",
                            "content": ai_message,
                            "timestamp": current_state["metadata"]["updated_at"],
                            "type": "clarification_questions",
                        }
                    )
                    logger.info(f"Added AI questions to negotiation history: {ai_message}")
                else:
                    # If no AI questions, generate a default clarification request
                    ai_message = "我理解了您的需求。为了更好地帮助您，请提供更多详细信息："
                    negotiation_history.append(
                        {
                            "role": "assistant",
                            "content": ai_message,
                            "timestamp": current_state["metadata"]["updated_at"],
                            "type": "clarification_questions",
                        }
                    )
                    logger.info("No AI questions generated, using default message")

                # Update the session state with negotiation history
                current_state["requirement_negotiation"][
                    "negotiation_history"
                ] = negotiation_history
                await self.orchestrator.save_session_state(current_state)

                logger.info(f"Final negotiation_history length: {len(negotiation_history)}")
                logger.info(f"Negotiation history contents: {negotiation_history}")

                return {
                    **current_state,  # Use the current state from orchestrator as base
                    **state,  # Override with any input state fields
                    "current_step": "consultant_phase",
                    "stage": "consultant",
                    "should_continue": False,  # Wait for user response
                    "ai_message": ai_message,
                    "negotiation_history": negotiation_history,
                    "waiting_for_user": True,
                    "errors": [],
                }
            else:
                # Input is clear enough, proceed directly to capability scan
                logger.info("Input is clear, proceeding directly to capability scan...")

                # Add user's input to negotiation history for record keeping
                negotiation_history.append(
                    {
                        "role": "user",
                        "content": user_input,
                        "timestamp": current_state["metadata"]["updated_at"],
                    }
                )

                # Add AI acknowledgment message
                ai_message = "明白了您的需求，正在分析工作流程的可行性..."
                negotiation_history.append(
                    {
                        "role": "assistant",
                        "content": ai_message,
                        "timestamp": current_state["metadata"]["updated_at"],
                        "type": "acknowledgment",
                    }
                )

                # Update the session state
                current_state["requirement_negotiation"][
                    "negotiation_history"
                ] = negotiation_history
                await self.orchestrator.save_session_state(current_state)

                logger.info("Proceeding directly to capability scan without further clarification")

                return {
                    **current_state,
                    **state,
                    "current_step": "capability_scan",  # Skip to capability scan
                    "stage": "consultant",
                    "should_continue": True,  # Continue processing
                    "ai_message": ai_message,
                    "negotiation_history": negotiation_history,
                    "waiting_for_user": False,
                    "errors": [],
                }
        except Exception as e:
            logger.error("Consultant phase failed", error=str(e))
            return {
                **state,
                "current_step": "error",
                "should_continue": False,
                "errors": [f"Consultant phase error: {str(e)}"],
            }

    async def _capability_scan_node(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """Quick capability scanning and gap identification"""
        logger.info("Processing capability scan")

        try:
            session_id = self._get_session_id(state)
            if not session_id:
                return {
                    **state,
                    "current_step": "error",
                    "should_continue": False,
                    "errors": ["Missing session_id"],
                }

            # Perform capability scan
            result = await self.orchestrator.process_stage_transition(
                session_id=session_id, user_input="capability_scan"
            )

            # Extract capability analysis
            capability_analysis = result.get("capability_analysis", {})
            gaps = capability_analysis.get("capability_gaps", [])

            return {
                **state,
                "current_step": "capability_scan",
                "capability_gaps": gaps,
                "capability_analysis": capability_analysis,
                "should_continue": True,
                "errors": [],
            }
        except Exception as e:
            logger.error("Capability scan failed", error=str(e))
            return {
                **state,
                "current_step": "error",
                "should_continue": False,
                "errors": [f"Capability scan error: {str(e)}"],
            }

    async def _constraint_identification_node(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """Identify potential blockers and constraints"""
        logger.info("Processing constraint identification")

        try:
            session_id = self._get_session_id(state)
            if not session_id:
                return {
                    **state,
                    "current_step": "error",
                    "should_continue": False,
                    "errors": ["Missing session_id"],
                }

            result = await self.orchestrator.process_stage_transition(
                session_id=session_id, user_input="constraint_identification"
            )

            return {
                **state,
                "current_step": "constraint_identification",
                "should_continue": True,
                "errors": [],
            }
        except Exception as e:
            logger.error("Constraint identification failed", error=str(e))
            return {
                **state,
                "current_step": "error",
                "should_continue": False,
                "errors": [f"Constraint identification error: {str(e)}"],
            }

    async def _solution_research_node(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """Research solutions for capability gaps"""
        logger.info("Processing solution research")

        try:
            session_id = self._get_session_id(state)
            if not session_id:
                return {
                    **state,
                    "current_step": "error",
                    "should_continue": False,
                    "errors": ["Missing session_id"],
                }

            result = await self.orchestrator.process_stage_transition(
                session_id=session_id, user_input="solution_research"
            )

            return {
                **state,
                "current_step": "solution_research",
                "should_continue": True,
                "errors": [],
            }
        except Exception as e:
            logger.error("Solution research failed", error=str(e))
            return {
                **state,
                "current_step": "error",
                "should_continue": False,
                "errors": [f"Solution research error: {str(e)}"],
            }

    # Phase 2: Negotiation Phase Nodes
    async def _tradeoff_presentation_node(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """Present tradeoff analysis to user"""
        logger.info("Processing tradeoff presentation")

        try:
            session_id = self._get_session_id(state)
            if not session_id:
                return {
                    **state,
                    "current_step": "error",
                    "should_continue": False,
                    "errors": ["Missing session_id"],
                }

            result = await self.orchestrator.process_stage_transition(
                session_id=session_id, user_input="tradeoff_presentation"
            )

            return {
                **state,
                "current_step": "tradeoff_presentation",
                "tradeoff_analysis": result.get("tradeoff_analysis"),
                "should_continue": True,
                "errors": [],
            }
        except Exception as e:
            logger.error("Tradeoff presentation failed", error=str(e))
            return {
                **state,
                "current_step": "error",
                "should_continue": False,
                "errors": [f"Tradeoff presentation error: {str(e)}"],
            }

    async def _requirement_adjustment_node(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """Adjust requirements based on constraints"""
        logger.info("Processing requirement adjustment")

        try:
            session_id = self._get_session_id(state)
            if not session_id:
                return {
                    **state,
                    "current_step": "error",
                    "should_continue": False,
                    "errors": ["Missing session_id"],
                }
            user_input = state.get("current_user_input", "")

            result = await self.orchestrator.process_stage_transition(
                session_id=session_id, user_input=user_input
            )

            return {
                **state,
                "current_step": "requirement_adjustment",
                "should_continue": True,
                "errors": [],
            }
        except Exception as e:
            logger.error("Requirement adjustment failed", error=str(e))
            return {
                **state,
                "current_step": "error",
                "should_continue": False,
                "errors": [f"Requirement adjustment error: {str(e)}"],
            }

    async def _implementation_confirmation_node(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """Confirm implementation plan with user"""
        logger.info("Processing implementation confirmation")

        try:
            session_id = self._get_session_id(state)
            if not session_id:
                return {
                    **state,
                    "current_step": "error",
                    "should_continue": False,
                    "errors": ["Missing session_id"],
                }

            result = await self.orchestrator.process_stage_transition(
                session_id=session_id, user_input="implementation_confirmation"
            )

            return {
                **state,
                "current_step": "implementation_confirmation",
                "should_continue": True,
                "errors": [],
            }
        except Exception as e:
            logger.error("Implementation confirmation failed", error=str(e))
            return {
                **state,
                "current_step": "error",
                "should_continue": False,
                "errors": [f"Implementation confirmation error: {str(e)}"],
            }

    # Phase 3: Design Phase Nodes
    async def _task_decomposition_node(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """Decompose requirements into task tree"""
        logger.info("Processing task decomposition")

        try:
            session_id = self._get_session_id(state)
            if not session_id:
                return {
                    **state,
                    "current_step": "error",
                    "should_continue": False,
                    "errors": ["Missing session_id"],
                }

            result = await self.orchestrator.process_stage_transition(
                session_id=session_id, user_input="task_decomposition"
            )

            return {
                **state,
                "current_step": "task_decomposition",
                "task_tree": result.get("task_tree"),
                "should_continue": True,
                "errors": [],
            }
        except Exception as e:
            logger.error("Task decomposition failed", error=str(e))
            return {
                **state,
                "current_step": "error",
                "should_continue": False,
                "errors": [f"Task decomposition error: {str(e)}"],
            }

    async def _architecture_design_node(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """Design workflow architecture"""
        logger.info("Processing architecture design")

        try:
            session_id = self._get_session_id(state)
            if not session_id:
                return {
                    **state,
                    "current_step": "error",
                    "should_continue": False,
                    "errors": ["Missing session_id"],
                }

            result = await self.orchestrator.process_stage_transition(
                session_id=session_id, user_input="architecture_design"
            )

            return {
                **state,
                "current_step": "architecture_design",
                "architecture": result.get("architecture"),
                "should_continue": True,
                "errors": [],
            }
        except Exception as e:
            logger.error("Architecture design failed", error=str(e))
            return {
                **state,
                "current_step": "error",
                "should_continue": False,
                "errors": [f"Architecture design error: {str(e)}"],
            }

    async def _dsl_generation_node(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """Generate workflow DSL"""
        logger.info("Processing DSL generation")

        try:
            session_id = self._get_session_id(state)
            if not session_id:
                return {
                    **state,
                    "current_step": "error",
                    "should_continue": False,
                    "errors": ["Missing session_id"],
                }

            result = await self.orchestrator.process_stage_transition(
                session_id=session_id, user_input="dsl_generation"
            )

            return {
                **state,
                "current_step": "dsl_generation",
                "workflow_dsl": result.get("workflow_dsl"),
                "should_continue": True,
                "errors": [],
            }
        except Exception as e:
            logger.error("DSL generation failed", error=str(e))
            return {
                **state,
                "current_step": "error",
                "should_continue": False,
                "errors": [f"DSL generation error: {str(e)}"],
            }

    # Phase 4: Configuration Phase Nodes
    async def _node_configuration_node(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """Configure individual nodes"""
        logger.info("Processing node configuration")

        try:
            session_id = self._get_session_id(state)
            if not session_id:
                return {
                    **state,
                    "current_step": "error",
                    "should_continue": False,
                    "errors": ["Missing session_id"],
                }

            result = await self.orchestrator.process_stage_transition(
                session_id=session_id, user_input="node_configuration"
            )

            return {
                **state,
                "current_step": "node_configuration",
                "node_configurations": result.get("node_configurations", []),
                "should_continue": True,
                "errors": [],
            }
        except Exception as e:
            logger.error("Node configuration failed", error=str(e))
            return {
                **state,
                "current_step": "error",
                "should_continue": False,
                "errors": [f"Node configuration error: {str(e)}"],
            }

    async def _parameter_validation_node(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """Validate node parameters"""
        logger.info("Processing parameter validation")

        try:
            session_id = self._get_session_id(state)
            if not session_id:
                return {
                    **state,
                    "current_step": "error",
                    "should_continue": False,
                    "errors": ["Missing session_id"],
                }

            result = await self.orchestrator.process_stage_transition(
                session_id=session_id, user_input="parameter_validation"
            )

            return {
                **state,
                "current_step": "parameter_validation",
                "validation_results": result.get("validation_results", []),
                "should_continue": True,
                "errors": [],
            }
        except Exception as e:
            logger.error("Parameter validation failed", error=str(e))
            return {
                **state,
                "current_step": "error",
                "should_continue": False,
                "errors": [f"Parameter validation error: {str(e)}"],
            }

    async def _missing_info_collection_node(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """Collect missing information"""
        logger.info("Processing missing info collection")

        try:
            session_id = self._get_session_id(state)
            if not session_id:
                return {
                    **state,
                    "current_step": "error",
                    "should_continue": False,
                    "errors": ["Missing session_id"],
                }

            result = await self.orchestrator.process_stage_transition(
                session_id=session_id, user_input="missing_info_collection"
            )

            return {
                **state,
                "current_step": "missing_info_collection",
                "missing_parameters": result.get("missing_parameters", []),
                "should_continue": True,
                "errors": [],
            }
        except Exception as e:
            logger.error("Missing info collection failed", error=str(e))
            return {
                **state,
                "current_step": "error",
                "should_continue": False,
                "errors": [f"Missing info collection error: {str(e)}"],
            }

    # Phase 5: Testing & Deployment Phase Nodes
    async def _testing_node(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """Main testing coordination node"""
        logger.info("Processing testing phase")

        try:
            session_id = self._get_session_id(state)
            if not session_id:
                return {
                    **state,
                    "current_step": "error",
                    "should_continue": False,
                    "errors": ["Missing session_id"],
                }

            result = await self.orchestrator.process_stage_transition(
                session_id=session_id, user_input="testing"
            )

            return {
                **state,
                "current_step": "testing",
                "stage": "testing",
                "should_continue": True,
                "errors": [],
            }
        except Exception as e:
            logger.error("Testing failed", error=str(e))
            return {
                **state,
                "current_step": "error",
                "should_continue": False,
                "errors": [f"Testing error: {str(e)}"],
            }

    async def _automated_testing_node(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """Execute automated tests"""
        logger.info("Processing automated testing")

        try:
            session_id = self._get_session_id(state)
            if not session_id:
                return {
                    **state,
                    "current_step": "error",
                    "should_continue": False,
                    "errors": ["Missing session_id"],
                }

            result = await self.orchestrator.process_stage_transition(
                session_id=session_id, user_input="automated_testing"
            )

            return {
                **state,
                "current_step": "automated_testing",
                "test_results": result.get("test_results", []),
                "should_continue": True,
                "errors": [],
            }
        except Exception as e:
            logger.error("Automated testing failed", error=str(e))
            return {
                **state,
                "current_step": "error",
                "should_continue": False,
                "errors": [f"Automated testing error: {str(e)}"],
            }

    async def _error_fixing_node(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """Fix errors found during testing"""
        logger.info("Processing error fixing")

        try:
            session_id = self._get_session_id(state)
            if not session_id:
                return {
                    **state,
                    "current_step": "error",
                    "should_continue": False,
                    "errors": ["Missing session_id"],
                }

            result = await self.orchestrator.process_stage_transition(
                session_id=session_id, user_input="error_fixing"
            )

            return {
                **state,
                "current_step": "error_fixing",
                "should_continue": True,
                "errors": [],
            }
        except Exception as e:
            logger.error("Error fixing failed", error=str(e))
            return {
                **state,
                "current_step": "error",
                "should_continue": False,
                "errors": [f"Error fixing error: {str(e)}"],
            }

    async def _deployment_node(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """Deploy workflow to production"""
        logger.info("Processing deployment")

        try:
            session_id = self._get_session_id(state)
            if not session_id:
                return {
                    **state,
                    "current_step": "error",
                    "should_continue": False,
                    "errors": ["Missing session_id"],
                }

            result = await self.orchestrator.process_stage_transition(
                session_id=session_id, user_input="deployment"
            )

            return {
                **state,
                "current_step": "deployment",
                "stage": "deployment",
                "deployment_status": result.get("deployment_status", "deployed"),
                "should_continue": True,
                "errors": [],
            }
        except Exception as e:
            logger.error("Deployment failed", error=str(e))
            return {
                **state,
                "current_step": "error",
                "should_continue": False,
                "errors": [f"Deployment error: {str(e)}"],
            }

    async def _requirement_negotiation_node(self, state: MVPWorkflowState) -> Dict[str, Any]:
        """Handle requirement negotiation stage"""
        logger.info("Processing requirement negotiation")

        session_id = self._get_session_id(state)
        if not session_id:
            return {
                **state,
                "current_step": "error",
                "should_continue": False,
                "errors": ["Missing session_id"],
            }
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
                "current_step": "requirement_negotiation",  # Always set to current node
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

        session_id = self._get_session_id(state)
        if not session_id:
            return {
                **state,
                "current_step": "error",
                "should_continue": False,
                "errors": ["Missing session_id"],
            }
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
                "current_step": "design",  # Always set to current node
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

        session_id = self._get_session_id(state)
        if not session_id:
            return {
                **state,
                "current_step": "error",
                "should_continue": False,
                "errors": ["Missing session_id"],
            }
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
                "current_step": "configuration",  # Always set to current node
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

        session_id = self._get_session_id(state)
        if not session_id:
            return {
                **state,
                "current_step": "error",
                "should_continue": False,
                "errors": ["Missing session_id"],
            }
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
                "current_step": "validation",  # Always set to current node
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
        """Determine next stage based on current state and architecture flow"""
        current_step = state.get("current_step", "")
        stage = state.get("stage", "")
        should_continue = state.get("should_continue", True)
        errors = state.get("errors", [])

        logger.info(
            "Determining next stage",
            current_step=current_step,
            stage=stage,
            should_continue=should_continue,
            errors=len(errors),
        )

        # Check for errors
        if not should_continue or errors:
            logger.info("Routing to end due to errors or should_continue=False")
            return "end"

        # Phase-specific routing logic according to architecture

        # Phase 1: Consultant Phase
        if current_step == "consultant_phase":
            # Check if waiting for user input
            waiting_for_user = state.get("waiting_for_user", False)
            logger.info(f"Consultant phase routing: waiting_for_user={waiting_for_user}")
            if waiting_for_user:
                route = "wait_for_user"
            else:
                route = "capability_scan"
            logger.info(f"Consultant phase routing decision: {route}")
            return route

        elif current_step == "capability_scan":
            # Check if we have capability gaps
            capability_gaps = state.get("capability_gaps", [])
            if capability_gaps:
                route = "constraint_identification"
            else:
                route = "requirement_negotiation"
            logger.info(f"Capability scan routing decision: {route} (gaps: {len(capability_gaps)})")
            return route

        elif current_step == "constraint_identification":
            return "solution_research"

        elif current_step == "solution_research":
            return "requirement_negotiation"

        # Phase 2: Requirement Negotiation
        elif current_step == "requirement_negotiation":
            # Check if negotiation is complete
            negotiation_state = state.get("requirement_negotiation", {})
            final_requirements = negotiation_state.get("final_requirements", "")
            if final_requirements:
                logger.info("Negotiation complete, routing to design")
                return "design"
            else:
                # Continue negotiation process
                next_questions = state.get("next_questions", [])
                if next_questions:
                    return "requirement_negotiation"
                else:
                    return "tradeoff_presentation"

        elif current_step == "tradeoff_presentation":
            return "requirement_adjustment"

        elif current_step == "requirement_adjustment":
            return "implementation_confirmation"

        elif current_step == "implementation_confirmation":
            return "design"

        # Phase 3: Design Phase
        elif current_step == "design":
            return "task_decomposition"

        elif current_step == "task_decomposition":
            return "architecture_design"

        elif current_step == "architecture_design":
            return "dsl_generation"

        elif current_step == "dsl_generation":
            return "configuration"

        # Phase 4: Configuration Phase
        elif current_step == "configuration":
            return "node_configuration"

        elif current_step == "node_configuration":
            return "parameter_validation"

        elif current_step == "parameter_validation":
            return "missing_info_collection"

        elif current_step == "missing_info_collection":
            return "testing"

        # Phase 5: Testing & Deployment
        elif current_step == "testing":
            return "automated_testing"

        elif current_step == "automated_testing":
            # Check if tests passed
            test_results = state.get("test_results", [])
            if test_results and any(not result.get("success", False) for result in test_results):
                return "error_fixing"
            else:
                return "deployment"

        elif current_step == "error_fixing":
            # After fixing errors, retry testing
            return "automated_testing"

        elif current_step == "deployment":
            return "end"

        elif current_step in ["completed"]:
            logger.info("Workflow completed, routing to end")
            return "end"

        # Fallback routing for backward compatibility
        logger.info("Using fallback routing logic", stage=stage)
        if stage == "consultant":
            return "capability_scan"
        elif stage == "requirement_negotiation":
            negotiation_state = state.get("requirement_negotiation", {})
            final_requirements = negotiation_state.get("final_requirements", "")
            if final_requirements:
                return "design"
            else:
                return "requirement_negotiation"
        elif stage == "design":
            return "task_decomposition"
        elif stage == "configuration":
            return "node_configuration"
        elif stage == "testing":
            return "automated_testing"
        elif stage == "deployment":
            return "end"
        elif stage in ["completed"]:
            return "end"

        # Default routing
        logger.info("Default routing", current_step=current_step)
        return current_step if current_step else "end"

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
        Generate a workflow using the MVP intelligent consultation process
        """
        logger.info("Starting intelligent workflow generation", description=user_input)

        try:
            # Initialize state for MVP workflow
            initial_state = {
                "user_input": user_input,
                "metadata": {
                    "session_id": session_id or f"session_{asyncio.get_event_loop().time()}",
                    "user_id": user_id or "anonymous",
                    "created_at": asyncio.get_event_loop().time(),
                    "updated_at": asyncio.get_event_loop().time(),
                    "version": "1.0.0",
                    "interaction_count": 0,
                },
                "stage": WorkflowStage.CONSULTANT,
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
                "session_id": self._get_session_id(final_state),
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
        thread_id: Optional[str] = None,
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
        thread_id: Optional[str] = None,
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
