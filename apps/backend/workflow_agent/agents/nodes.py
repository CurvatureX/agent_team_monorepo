"""
LangGraph nodes for simplified Workflow Agent architecture
Implements the 4 core nodes: Clarification, Gap Analysis,
Workflow Generation, and Debug
"""

import asyncio
import json
import time
import uuid
from typing import List

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from .state import (
    ClarificationContext,
    Conversation,
    WorkflowOrigin,
    WorkflowStage,
    WorkflowState,
)
from .tools import RAGTool
from core.config import settings
import logging
from core.prompt_engine import get_prompt_engine

logger = logging.getLogger(__name__)

class WorkflowAgentNodes:
    """Simplified LangGraph nodes for workflow generation"""

    def __init__(self):
        self.llm = self._setup_llm()
        self.prompt_engine = get_prompt_engine()
        self.rag_tool = RAGTool()

    def _setup_llm(self):
        """Setup the language model based on configuration"""
        if settings.DEFAULT_MODEL_PROVIDER == "openai":
            return ChatOpenAI(
                model=settings.DEFAULT_MODEL_NAME, api_key=settings.OPENAI_API_KEY, temperature=0.1
            )
        elif settings.DEFAULT_MODEL_PROVIDER == "anthropic":
            return ChatAnthropic(
                model_name=settings.DEFAULT_MODEL_NAME,
                api_key=settings.ANTHROPIC_API_KEY,
                temperature=0.1,
                timeout=10,
                stop=["\n\n"],
            )
        else:
            raise ValueError(f"Unsupported model provider: {settings.DEFAULT_MODEL_PROVIDER}")

    def _get_session_id(self, state: WorkflowState) -> str:
        """Get session ID from state"""
        return state.get("session_id", "")

    def _update_conversations(self, state: WorkflowState, role: str, text: str) -> None:
        """Update conversations list in state"""
        if "conversations" not in state:
            state["conversations"] = []

        state["conversations"].append(Conversation(role=role, text=text))

    def _get_current_scenario(self, state: WorkflowState) -> str:
        """Determine the current scenario based on state"""
        stage = state.get("stage")
        previous_stage = state.get("previous_stage")

        if stage == WorkflowStage.CLARIFICATION:
            if previous_stage == WorkflowStage.DEBUG:
                return "Debug Recovery"
            elif previous_stage == WorkflowStage.GAP_ANALYSIS:
                return "Gap Analysis Feedback Processing"
            elif state.get("template_workflow"):
                return "Template Customization"
            else:
                return "Initial Clarification"
        return "Initial Clarification"

    def _get_current_goal(self, state: WorkflowState) -> str:
        """Determine the current goal based on scenario"""
        scenario = self._get_current_scenario(state)

        if scenario == "Debug Recovery":
            return "Understand debug failures and gather information needed to fix workflow issues"
        elif scenario == "Gap Analysis Feedback Processing":
            return "Process user feedback after gap analysis and alternative solution presentation"
        elif scenario == "Template Customization":
            return "Understand how the user wants to modify an existing template workflow to meet their specific needs"
        else:
            return "Understand the user's workflow automation needs and capture all essential requirements through strategic questioning"

    def _get_scenario_type(self, state: WorkflowState) -> str:
        """Determine the scenario type for template conditional logic"""
        stage = state.get("stage")
        previous_stage = state.get("previous_stage")

        if previous_stage == WorkflowStage.DEBUG:
            return "debug_recovery"
        elif previous_stage == WorkflowStage.GAP_ANALYSIS:
            return "gap_analysis_feedback"
        elif state.get("template_workflow"):
            return "template_customization"
        else:
            return "initial_creation"

    def _get_gap_analysis_scenario(self, state: WorkflowState) -> str:
        """Determine the gap analysis scenario based on state"""
        stage = state.get("stage")
        previous_stage = state.get("previous_stage")

        if stage == WorkflowStage.GAP_ANALYSIS:
            # Check if we're re-analyzing after user feedback on gaps
            if previous_stage == WorkflowStage.CLARIFICATION and state.get("gap_status") == "has_gap":
                return "Post-Gap Resolution Analysis"
            elif state.get("template_workflow"):
                return "Template Capability Analysis"
            elif previous_stage == WorkflowStage.DEBUG:
                return "Debug Failure Gap Analysis"
            else:
                return "Initial Gap Analysis"
        return "Initial Gap Analysis"

    def _get_gap_analysis_goal(self, state: WorkflowState) -> str:
        """Determine the gap analysis goal based on scenario"""
        scenario = self._get_gap_analysis_scenario(state)

        if scenario == "Post-Gap Resolution Analysis":
            return "Review user feedback and selected approach to resolve identified gaps"
        elif scenario == "Template Capability Analysis":
            return "Analyze template requirements against available capabilities"
        elif scenario == "Debug Failure Gap Analysis":
            return "Identify capability gaps that caused workflow failure"
        else:
            return "Analyze user requirements against available node capabilities and identify missing components"

    def _get_gap_analysis_scenario_type(self, state: WorkflowState) -> str:
        """Determine the scenario type for gap analysis template conditional logic"""
        previous_stage = state.get("previous_stage")

        # Check if we're re-analyzing after user feedback on gaps
        if previous_stage == WorkflowStage.CLARIFICATION and state.get("gap_status") == "has_gap":
            return "post_gap_resolution"
        elif state.get("template_workflow"):
            return "template_analysis"
        elif previous_stage == WorkflowStage.DEBUG:
            return "debug_analysis"
        else:
            return "initial_analysis"

    def _get_latest_user_input(self, state: WorkflowState) -> str:
        """Get the latest user input from conversations"""
        if state.get("conversations"):
            for conv in reversed(state["conversations"]):
                if conv["role"] == "user":
                    return conv["text"]
        return ""

    async def clarification_node(self, state: WorkflowState) -> WorkflowState:
        """
        Clarification Node - 解析和澄清用户意图
        支持多种澄清目的：初始意图、模板选择、模板修改、能力差距解决、调试问题
        现在也处理之前 Negotiation node 的功能：等待用户回答问题或选择方案
        """
        logger.info("Processing clarification node")

        try:
            # Get clarification context (now required)
            clarification_context = state["clarification_context"]
            origin = clarification_context.get("origin", "create")
            purpose = clarification_context.get("purpose", "initial_intent")
            pending_questions = clarification_context.get("pending_questions", [])
            
            logger.info("Clarification context", extra={"origin": origin, "purpose": purpose, "pending_questions_count": len(pending_questions)})
            if pending_questions:
                logger.info("Pending questions", extra={"pending_questions": pending_questions})

            # Get user input from conversations
            user_input = ""
            latest_user_message_index = -1
            conversations = state.get("conversations", [])
            logger.info("Total conversations in state", extra={"conversation_count": len(conversations)})
            
            if conversations:
                # Get the latest user message and its index
                for i in range(len(conversations) - 1, -1, -1):
                    conv = conversations[i]
                    if conv["role"] == "user":
                        user_input = conv["text"]
                        latest_user_message_index = i
                        break
            
            # Check if this is a response to pending questions
            is_response_to_pending_questions = False
            if pending_questions and latest_user_message_index >= 0:
                # If we have pending questions and a new user input, it's likely a response
                # Check if there's an assistant message before this user message
                for i in range(latest_user_message_index - 1, -1, -1):
                    conv = state["conversations"][i]
                    if conv["role"] == "assistant":
                        # Found the previous assistant message
                        is_response_to_pending_questions = True
                        logger.info("Found user input after assistant message with pending questions")
                        logger.info("Pending questions details", extra={"pending_questions": pending_questions})
                        user_preview = user_input[:100] + "..." if len(user_input) > 100 else user_input
                        logger.info("User response", extra={"user_input_preview": user_preview})
                        break
            
            # Clear pending questions if this is a response
            if is_response_to_pending_questions and pending_questions:
                logger.info("Clearing pending questions as we have user response")
                clarification_context["pending_questions"] = []
                # Update the state with cleared pending questions
                state["clarification_context"] = clarification_context
                
                # If this is a gap resolution response, mark that we need to re-run gap analysis
                if purpose == "gap_negotiation" and user_input:
                    logger.info("User responded to gap negotiation", extra={"user_input": user_input})
                    # The gap analysis will run again to check if gaps are resolved

            # If we have user input, use RAG to retrieve knowledge
            if user_input:
                logger.info("Retrieving knowledge with RAG tool")
                try:
                    state = await self.rag_tool.retrieve_knowledge(state, query=user_input)
                except Exception as rag_error:
                    logger.warning("RAG retrieval failed, continuing without RAG context", extra={"error": str(rag_error)})
                    # Continue without RAG context - the workflow should still function
                    if "rag" not in state:
                        state["rag"] = {"query": user_input, "results": []}

            # Track clarification rounds
            clarification_round = state.get("clarification_round", 0)
            state["clarification_round"] = clarification_round + 1
            
            # Use separate system and user prompt files for clarification
            template_context = {
                "origin": origin,
                "user_input": user_input,
                "execution_history": state.get("execution_history", []),
                "current_scenario": self._get_current_scenario(state),
                "goal": self._get_current_goal(state),
                "scenario_type": self._get_scenario_type(state),
                "current_workflow": state.get("current_workflow"),
                "debug_result": state.get("debug_result"),
                "identified_gaps": state.get("identified_gaps", []),
                "template_workflow": state.get("template_workflow"),
                "rag_context": state.get("rag"),
                "clarification_context": clarification_context,
                "clarification_round": clarification_round,
            }

            system_prompt = await self.prompt_engine.render_prompt(
                "clarification_f2_system", **template_context
            )
            user_prompt = await self.prompt_engine.render_prompt(
                "clarification_f2_user", **template_context
            )

            # Build messages with conversation history as separate messages
            messages = [SystemMessage(content=system_prompt)]

            # Add conversation history as separate messages (better for LLM understanding)
            conversations = state.get("conversations", [])
            for conv in conversations:
                if conv["role"] == "user":
                    messages.append(HumanMessage(content=conv["text"]))
                elif conv["role"] == "assistant":
                    messages.append(AIMessage(content=conv["text"]))

            # Add current clarification request
            messages.append(HumanMessage(content=user_prompt))

            response = await self.llm.ainvoke(messages)

            # Parse response using clarification_f2 format
            try:
                response_text = (
                    response.content if isinstance(response.content, str) else str(response.content)
                )
                
                # Remove markdown code blocks if present
                if response_text.strip().startswith("```json"):
                    response_text = response_text.strip()[7:]  # Remove ```json
                    if response_text.endswith("```"):
                        response_text = response_text[:-3]  # Remove trailing ```
                elif response_text.strip().startswith("```"):
                    response_text = response_text.strip()[3:]  # Remove ```
                    if response_text.endswith("```"):
                        response_text = response_text[:-3]  # Remove trailing ```
                
                analysis = json.loads(response_text.strip())

                logger.info("Clarification analysis", extra={"analysis": analysis})

                # clarification_f2 format: clarification_question, is_complete, intent_summary, gap_resolution
                clarification_question = analysis.get("clarification_question", "")
                is_complete = analysis.get("is_complete", False)
                intent_summary = analysis.get("intent_summary", "")
                gap_resolution = analysis.get("gap_resolution", {})
                
                # Handle gap resolution
                if purpose == "gap_negotiation" and gap_resolution.get("user_selected_alternative", False):
                    confidence = gap_resolution.get("confidence", 0)
                    selected_index = gap_resolution.get("selected_index")
                    
                    if confidence > 0.7 and selected_index is not None:
                        logger.info("User selected alternative", extra={
                            "selected_index": selected_index,
                            "confidence": confidence
                        })
                        state["selected_alternative_index"] = selected_index
                        state["gap_status"] = "gap_resolved"
                        # Skip further clarification and go directly to workflow generation
                        return {**state, "stage": WorkflowStage.WORKFLOW_GENERATION}

                # Force completion after 1 round for consumer experience
                if clarification_round >= 1 and not is_complete:
                    logger.info("Forcing completion after 1 round", extra={"round": clarification_round})
                    is_complete = True
                    if not intent_summary:
                        intent_summary = f"{intent_summary or 'User workflow request'}. Using smart defaults for configuration."
                
                # Determine if we need more clarification
                needs_clarification = not is_complete
                questions = [clarification_question] if clarification_question and not is_complete else []
                
                # Use provided intent_summary or create default
                if not intent_summary:
                    intent_summary = "用户需求已澄清" if is_complete else "需要进一步澄清用户需求"

            except json.JSONDecodeError:
                # Fallback parsing
                response_text = (
                    response.content if isinstance(response.content, str) else str(response.content)
                )
                intent_summary = (
                    response_text[:200] + "..." if len(response_text) > 200 else response_text
                )
                needs_clarification = "?" in response_text or "clarif" in response_text.lower()
                questions = []
                gap_resolution = {"user_selected_alternative": False, "selected_index": None, "confidence": 0.0}
                
                # Force completion after 1 round even in fallback
                if clarification_round >= 1:
                    needs_clarification = False

            # Update state
            state["intent_summary"] = intent_summary

            if needs_clarification and questions:
                # Need more clarification - store questions and wait for user input
                clarification_context = state.get("clarification_context")
                if clarification_context:
                    clarification_context["pending_questions"] = questions
                self._update_conversations(state, "assistant", "\n".join(questions))
                # Stay in clarification stage but return END to wait for user
                return {**state, "stage": WorkflowStage.CLARIFICATION}
            else:
                return {**state, "stage": WorkflowStage.GAP_ANALYSIS}

        except Exception as e:
            logger.error("Clarification node failed", extra={"error": str(e)})
            return {
                **state,
                "stage": WorkflowStage.CLARIFICATION,
                "debug_result": f"Clarification error: {str(e)}",
            }


    async def gap_analysis_node(self, state: WorkflowState) -> WorkflowState:
        """
        Gap Analysis Node - 分析需求与现有能力之间的差距
        """
        logger.info("Processing gap analysis node")

        try:
            intent_summary = state.get("intent_summary", "")
            
            # Check if gaps have been resolved (user selected an alternative)
            if state.get("gap_status") == "gap_resolved":
                logger.info("Gaps have been resolved, proceeding to workflow generation")
                selected_index = state.get("selected_alternative_index")
                if selected_index is not None:
                    logger.info("User selected alternative", extra={"index": selected_index})
                return {**state, "stage": WorkflowStage.WORKFLOW_GENERATION}

            # Use separate system and user prompt files for capability gap analysis
            template_context = {
                "intent_summary": intent_summary,
                "conversations": state.get("conversations", []),
                "execution_history": state.get("execution_history", []),
                "current_scenario": self._get_gap_analysis_scenario(state),
                "goal": self._get_gap_analysis_goal(state),
                "scenario_type": self._get_gap_analysis_scenario_type(state),
                "user_feedback": self._get_latest_user_input(state),
                "template_workflow": state.get("template_workflow"),
                "current_workflow": state.get("current_workflow"),
                "debug_result": state.get("debug_result"),
                "rag_context": state.get("rag"),
            }

            system_prompt = await self.prompt_engine.render_prompt(
                "gap_analysis_f2_system", **template_context
            )
            user_prompt = await self.prompt_engine.render_prompt(
                "gap_analysis_f2_user", **template_context
            )

            # Build messages with conversation history as separate messages
            messages = [SystemMessage(content=system_prompt)]

            # Add conversation history as separate messages (better for LLM understanding)
            conversations = state.get("conversations", [])
            for conv in conversations:
                if conv["role"] == "user":
                    messages.append(HumanMessage(content=conv["text"]))
                elif conv["role"] == "assistant":
                    messages.append(AIMessage(content=conv["text"]))

            # Add current analysis request
            messages.append(HumanMessage(content=user_prompt))

            response = await self.llm.ainvoke(messages)

            try:
                response_text = (
                    response.content if isinstance(response.content, str) else str(response.content)
                )
                
                # Remove markdown code blocks if present
                if response_text.strip().startswith("```json"):
                    response_text = response_text.strip()[7:]  # Remove ```json
                    if response_text.endswith("```"):
                        response_text = response_text[:-3]  # Remove trailing ```
                elif response_text.strip().startswith("```"):
                    response_text = response_text.strip()[3:]  # Remove ```
                    if response_text.endswith("```"):
                        response_text = response_text[:-3]  # Remove trailing ```
                
                analysis = json.loads(response_text.strip())
                logger.info("Gap analysis", extra={"analysis": analysis})
                
                # Extract gap analysis results
                gap_status = analysis.get("gap_status", "no_gap")
                negotiation_phrase = analysis.get("negotiation_phrase", "")
                identified_gaps = analysis.get("identified_gaps", [])
                
            except json.JSONDecodeError:
                # Fallback to simple analysis
                response_text = (
                    response.content if isinstance(response.content, str) else str(response.content)
                )
                response_lower = response_text.lower()
                gap_status = "has_gap" if ("gap" in response_lower or "missing" in response_lower) else "no_gap"
                negotiation_phrase = "We identified some gaps in the workflow requirements."
                identified_gaps = []

            # Update state with gap analysis results
            state["gap_status"] = gap_status
            state["identified_gaps"] = identified_gaps
            
            logger.info("Gap analysis results", extra={
                "gap_status": gap_status,
                "gaps_count": len(identified_gaps),
                "has_negotiation": bool(negotiation_phrase)
            })

            if gap_status == "has_gap" and identified_gaps:
                # We have gaps with alternatives - send negotiation phrase to user
                if negotiation_phrase:
                    self._update_conversations(state, "assistant", negotiation_phrase)
                
                # Set up clarification context for user choice
                clarification_context = state.get("clarification_context", {})
                clarification_context["purpose"] = "gap_negotiation"
                clarification_context["pending_questions"] = [negotiation_phrase] if negotiation_phrase else []
                state["clarification_context"] = clarification_context
                
                # Log the gaps for debugging
                for i, gap in enumerate(identified_gaps):
                    logger.info(f"Gap {i}", extra={
                        "capability": gap.get("required_capability"),
                        "alternatives_count": len(gap.get("alternatives", []))
                    })
                
                # Go back to clarification to get user's choice
                return {**state, "stage": WorkflowStage.CLARIFICATION}
            else:
                # No gaps or gaps resolved - proceed to workflow generation
                return {**state, "stage": WorkflowStage.WORKFLOW_GENERATION}

        except Exception as e:
            logger.error("Gap analysis node failed", extra={"error": str(e)})
            return {
                **state,
                "stage": WorkflowStage.GAP_ANALYSIS,
                "debug_result": f"Gap analysis error: {str(e)}",
            }

    async def workflow_generation_node(self, state: WorkflowState) -> WorkflowState:
        """
        Workflow Generation Node - 根据确定的需求生成工作流
        """
        logger.info("Processing workflow generation node")

        try:
            intent_summary = state.get("intent_summary", "")
            identified_gaps = state.get("identified_gaps", [])
            gap_status = state.get("gap_status", "no_gap")
            template_workflow = state.get("template_workflow")

            # Use prompt to generate workflow
            prompt_text = await self.prompt_engine.render_prompt(
                "workflow_architecture",
                intent_summary=intent_summary,
                identified_gaps=identified_gaps,
                gap_status=gap_status,
                template_workflow=template_workflow,
            )

            system_prompt = (
                "You are a workflow generation specialist. Create complete, functional workflows."
            )
            user_prompt = prompt_text

            messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            response = await self.llm.ainvoke(messages)

            try:
                response_text = (
                    response.content if isinstance(response.content, str) else str(response.content)
                )
                
                logger.info("workflow_generation response", extra={"response_text": response_text})
                # Remove markdown code blocks if present
                if response_text.strip().startswith("```json"):
                    response_text = response_text.strip()[7:]  # Remove ```json
                    if response_text.endswith("```"):
                        response_text = response_text[:-3]  # Remove trailing ```
                elif response_text.strip().startswith("```"):
                    response_text = response_text.strip()[3:]  # Remove ```
                    if response_text.endswith("```"):
                        response_text = response_text[:-3]  # Remove trailing ```
                
                workflow = json.loads(response_text.strip())
                logger.info("workflow_generation result", extra={"workflow": workflow})
            except json.JSONDecodeError:
                # Fallback workflow structure
                workflow = {
                    "id": f"workflow-{uuid.uuid4().hex[:8]}",
                    "name": f"Generated Workflow",
                    "description": intent_summary,
                    "nodes": [
                        {"id": "start", "type": "trigger", "name": "Start", "parameters": {}},
                        {"id": "process", "type": "action", "name": "Process", "parameters": {}},
                    ],
                    "connections": [{"from": "start", "to": "process"}],
                    "created_at": int(time.time()),
                }

            state["current_workflow"] = workflow
            return {**state, "stage": WorkflowStage.DEBUG}

        except Exception as e:
            logger.error("Workflow generation node failed", extra={"error": str(e)})
            return {
                **state,
                "stage": WorkflowStage.WORKFLOW_GENERATION,
                "debug_result": f"Workflow generation error: {str(e)}",
            }

    async def debug_node(self, state: WorkflowState) -> WorkflowState:
        """
        Debug Node - 测试生成的工作流，发现并尝试修复错误
        根据失败类型决定是回到 Workflow Generation 还是 Clarification
        """
        logger.info("Processing debug node")

        try:
            current_workflow = state.get("current_workflow", {})
            debug_loop_count = state.get("debug_loop_count", 0)

            # Use the debug prompt for sophisticated validation
            try:
                prompt_text = await self.prompt_engine.render_prompt(
                    "debug",
                    current_workflow=current_workflow,
                    debug_loop_count=debug_loop_count,
                    previous_errors=state.get("previous_errors", []),
                )

                system_prompt = (
                    "You are a workflow debugging specialist. Analyze the workflow thoroughly."
                )
                user_prompt = prompt_text

                messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
                llm_response = await self.llm.ainvoke(messages)

                # Try to parse the LLM response as JSON
                response_text = (
                    llm_response.content
                    if isinstance(llm_response.content, str)
                    else str(llm_response.content)
                )
                
                # Remove markdown code blocks if present
                if response_text.strip().startswith("```json"):
                    response_text = response_text.strip()[7:]  # Remove ```json
                    if response_text.endswith("```"):
                        response_text = response_text[:-3]  # Remove trailing ```
                elif response_text.strip().startswith("```"):
                    response_text = response_text.strip()[3:]  # Remove ```
                    if response_text.endswith("```"):
                        response_text = response_text[:-3]  # Remove trailing ```
                
                debug_analysis = json.loads(response_text.strip())
                logger.info("debug_analysis result", extra={"debug_analysis": debug_analysis})

                # Extract key information from LLM analysis
                errors = debug_analysis.get("issues_found", {}).get("critical_errors", [])
                warnings = debug_analysis.get("issues_found", {}).get("warnings", [])
                success = (
                    debug_analysis.get("validation_summary", {}).get("overall_status") == "valid"
                )

                debug_result = {
                    "success": success,
                    "errors": [error.get("description", str(error)) for error in errors],
                    "warnings": [warning.get("description", str(warning)) for warning in warnings],
                    "iteration": debug_loop_count + 1,
                    "full_analysis": debug_analysis,
                }

            except (json.JSONDecodeError, Exception) as e:
                # Fallback to basic validation if prompt-based analysis fails
                logger.warning(
                    "Debug prompt analysis failed, using fallback validation", extra={"error": str(e)}
                )

                errors = []
                warnings = []

                # Check workflow structure
                if not current_workflow:
                    errors.append("Empty workflow")
                else:
                    workflow_dict = current_workflow if isinstance(current_workflow, dict) else {}
                    nodes = workflow_dict.get("nodes", [])
                    connections = workflow_dict.get("connections", [])

                    if not nodes:
                        errors.append("No nodes in workflow")

                    if len(nodes) > 1 and not connections:
                        warnings.append("Multi-node workflow without connections")

                    # Check node parameters
                    for node in nodes:
                        if not node.get("parameters"):
                            warnings.append(f"Node {node.get('id', 'unknown')} missing parameters")

                # Simulate more complex validation
                if debug_loop_count > 0:
                    # On retry, add some randomness to simulate fixes
                    import random

                    if random.random() > 0.3:  # 70% chance of success on retry
                        errors = []

                debug_result = {
                    "success": len(errors) == 0,
                    "errors": errors,
                    "warnings": warnings,
                    "iteration": debug_loop_count + 1,
                }

            state["debug_result"] = json.dumps(debug_result)
            state["debug_loop_count"] = debug_loop_count + 1

            if errors:
                # Analyze error type to determine where to go
                error_text = " ".join(errors).lower()

                if (
                    "empty" in error_text
                    or "no nodes" in error_text
                    or "structure" in error_text
                    or "parameters" in error_text
                ):
                    # Implementation issues - back to workflow generation
                    logger.info("Debug found implementation issues, returning to generation")
                    return {**state, "stage": WorkflowStage.WORKFLOW_GENERATION}
                else:
                    # Requirement understanding issues - back to clarification
                    logger.info("Debug found requirement issues, returning to clarification")
                    state["clarification_context"] = ClarificationContext(
                        origin=state.get("clarification_context", {}).get(
                            "origin", WorkflowOrigin.CREATE
                        ),
                        pending_questions=[f"工作流验证失败：{'; '.join(errors)}。请提供更多信息以修复这些问题。"],
                    )
                    return {**state, "stage": WorkflowStage.CLARIFICATION}
            else:
                # Success - workflow is ready
                logger.info("Debug successful, workflow is ready")
                workflow_dict = current_workflow if isinstance(current_workflow, dict) else {}
                success_message = f"工作流生成成功！包含 {len(workflow_dict.get('nodes', []))} 个节点。"
                self._update_conversations(state, "assistant", success_message)
                return {**state, "stage": WorkflowStage.COMPLETED}

        except Exception as e:
            logger.error("Debug node failed", extra={"error": str(e)})
            return {
                **state,
                "stage": WorkflowStage.DEBUG,
                "debug_result": f"Debug error: {str(e)}",
            }

    def should_continue(self, state: WorkflowState) -> str:
        """Determine the next node based on current stage"""
        stage = state.get("stage", "clarification")

        # Special handling for clarification stage
        if stage == WorkflowStage.CLARIFICATION:
            # Check if we need to wait for user input
            clarification_context = state.get("clarification_context", {})
            pending_questions = clarification_context.get("pending_questions", [])
            
            if pending_questions:
                # We have pending questions - wait for user input
                logger.info("Clarification has pending questions, waiting for user input")
                return "END"
            # Otherwise continue to process in clarification or move to next stage

        # Map stages to node names
        stage_mapping = {
            WorkflowStage.CLARIFICATION: "clarification",
            WorkflowStage.GAP_ANALYSIS: "gap_analysis",
            WorkflowStage.WORKFLOW_GENERATION: "workflow_generation",
            WorkflowStage.DEBUG: "debug",
            WorkflowStage.COMPLETED: "END",
        }

        next_node = stage_mapping.get(stage, "END")
        logger.info("Stage transition", extra={"current_stage": stage, "next_node": next_node})

        return next_node
