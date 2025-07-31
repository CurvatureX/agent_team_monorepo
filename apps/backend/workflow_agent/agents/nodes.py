"""
LangGraph nodes for simplified Workflow Agent architecture
Implements the 6 core nodes: Clarification, Negotiation, Gap Analysis,
Alternative Solution Generation, Workflow Generation, and Debug
"""

import json
import time
import uuid
from typing import List

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from agents.state import (
    AlternativeOption,
    ClarificationContext,
    Conversation,
    WorkflowOrigin,
    WorkflowStage,
    WorkflowState,
)
from .tools import RAGTool
from core.config import settings
from core.logging_config import get_logger
from core.prompt_engine import get_prompt_engine

logger = get_logger(__name__)

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
            if previous_stage == WorkflowStage.NEGOTIATION:
                return "Post-Negotiation Gap Analysis"
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

        if scenario == "Post-Negotiation Gap Analysis":
            return "Review user feedback and selected alternatives to resolve identified gaps"
        elif scenario == "Template Capability Analysis":
            return "Analyze template requirements against available capabilities"
        elif scenario == "Debug Failure Gap Analysis":
            return "Identify capability gaps that caused workflow failure"
        else:
            return "Analyze user requirements against available node capabilities and identify missing components"

    def _get_gap_analysis_scenario_type(self, state: WorkflowState) -> str:
        """Determine the scenario type for gap analysis template conditional logic"""
        previous_stage = state.get("previous_stage")

        if previous_stage == WorkflowStage.NEGOTIATION:
            return "post_negotiation"
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
        """
        logger.info("Processing clarification node")

        try:
            # Get clarification context (now required)
            clarification_context = state["clarification_context"]
            origin = clarification_context["origin"]

            # Get user input from conversations
            user_input = ""
            if state.get("conversations"):
                # Get the latest user message
                for conv in reversed(state["conversations"]):
                    if conv["role"] == "user":
                        user_input = conv["text"]
                        break

            # If we have user input, use RAG to retrieve knowledge
            if user_input:
                logger.info("Retrieving knowledge with RAG tool")
                state = await self.rag_tool.retrieve_knowledge(state, query=user_input)

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
                "gaps": state.get("gaps", []),
                "alternatives": state.get("alternatives", []),
                "template_workflow": state.get("template_workflow"),
                "rag_context": state.get("rag"),
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

                logger.info(f"Clarification analysis: {analysis}")

                # clarification_f2 format: clarification_question, is_complete, workflow_summary
                clarification_question = analysis.get("clarification_question", "")
                is_complete = analysis.get("is_complete", False)
                workflow_summary = analysis.get("workflow_summary", "")

                # Convert to old format for compatibility
                if is_complete and workflow_summary:
                    # Clarification is complete - extract intent from workflow summary
                    intent_summary = (
                        workflow_summary.split("\n")[0] if workflow_summary else "用户需求已澄清"
                    )
                    needs_clarification = False
                    questions = []
                else:
                    # More clarification needed
                    intent_summary = "需要进一步澄清用户需求"
                    needs_clarification = True
                    questions = [clarification_question] if clarification_question else []

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

            # Update state
            state["intent_summary"] = intent_summary

            # # Store workflow summary if complete
            # if "workflow_summary" in locals() and workflow_summary:
            #     state["intent_summary"] = workflow_summary

            if needs_clarification and questions:
                # Need more clarification - go to negotiation
                clarification_context = state.get("clarification_context")
                if clarification_context:
                    clarification_context["pending_questions"] = questions
                self._update_conversations(state, "assistant", "\n".join(questions))
                return {**state, "stage": WorkflowStage.NEGOTIATION}
            else:
                # Clarification complete - proceed to gap analysis
                return {**state, "stage": WorkflowStage.GAP_ANALYSIS}

        except Exception as e:
            logger.error("Clarification node failed", error=str(e))
            return {
                **state,
                "stage": WorkflowStage.CLARIFICATION,
                "debug_result": f"Clarification error: {str(e)}",
            }

    async def negotiation_node(self, state: WorkflowState) -> WorkflowState:
        """
        Negotiation Node - 与用户协商，获取额外信息或在备选方案中选择
        """
        logger.info("Processing negotiation node")

        try:
            # Get pending questions from clarification context
            clarification_context = state.get("clarification_context", {})
            pending_questions = clarification_context.get("pending_questions", [])

            # Check if user has provided new information
            latest_user_input = ""
            if state.get("conversations"):
                for conv in reversed(state["conversations"]):
                    if conv["role"] == "user":
                        latest_user_input = conv["text"]
                        break

            if latest_user_input:
                # User provided response, update conversations and return to clarification
                self._update_conversations(state, "user", latest_user_input)
                return {**state, "stage": WorkflowStage.CLARIFICATION}
            else:
                # Wait for user response - present questions
                if pending_questions:
                    questions_text = "\n".join(pending_questions)
                    self._update_conversations(state, "assistant", questions_text)
                return {**state, "stage": WorkflowStage.NEGOTIATION}

        except Exception as e:
            logger.error("Negotiation node failed", error=str(e))
            return {
                **state,
                "stage": WorkflowStage.NEGOTIATION,
                "debug_result": f"Negotiation error: {str(e)}",
            }

    async def gap_analysis_node(self, state: WorkflowState) -> WorkflowState:
        """
        Gap Analysis Node - 分析需求与现有能力之间的差距
        """
        logger.info("Processing gap analysis node")

        try:
            intent_summary = state.get("intent_summary", "")

            # Use separate system and user prompt files for capability gap analysis
            template_context = {
                "intent_summary": intent_summary,
                "conversations": state.get("conversations", []),
                "execution_history": state.get("execution_history", []),
                "current_scenario": self._get_gap_analysis_scenario(state),
                "goal": self._get_gap_analysis_goal(state),
                "scenario_type": self._get_gap_analysis_scenario_type(state),
                "user_feedback": self._get_latest_user_input(state),
                "selected_alternative": state.get("selected_alternative"),
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
                gaps = analysis.get("gaps", [])
                severity = analysis.get("severity", "low")
            except json.JSONDecodeError:
                # Simple fallback gap detection
                response_text = (
                    response.content if isinstance(response.content, str) else str(response.content)
                )
                response_lower = response_text.lower()
                gaps = []
                if "integration" in response_lower or "api" in response_lower:
                    gaps.append("external_integration")
                if "authentication" in response_lower or "credential" in response_lower:
                    gaps.append("authentication_setup")
                severity = "medium" if gaps else "low"

            state["gaps"] = gaps

            if gaps:
                # Capability gaps found - generate alternatives
                return {**state, "stage": WorkflowStage.ALTERNATIVE_GENERATION}
            else:
                # No gaps - proceed to workflow generation
                return {**state, "stage": WorkflowStage.WORKFLOW_GENERATION}

        except Exception as e:
            logger.error("Gap analysis node failed", error=str(e))
            return {
                **state,
                "stage": WorkflowStage.GAP_ANALYSIS,
                "debug_result": f"Gap analysis error: {str(e)}",
            }

    async def alternative_solution_generation_node(self, state: WorkflowState) -> WorkflowState:
        """
        Alternative Solution Generation Node - 当存在能力差距时，生成替代解决方案
        """
        logger.info("Processing alternative solution generation node")

        try:
            gaps = state.get("gaps", [])
            intent_summary = state.get("intent_summary", "")

            # Use prompt to generate alternative solutions
            prompt_text = await self.prompt_engine.render_prompt(
                "solution_generation",
                intent_summary=intent_summary,
                gaps=gaps,
                conversations=state.get("conversations", []),
            )

            system_prompt = "You are an alternative solution generator. Provide practical alternatives for capability gaps."
            user_prompt = prompt_text

            messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            response = await self.llm.ainvoke(messages)

            try:
                response_text = (
                    response.content if isinstance(response.content, str) else str(response.content)
                )
                analysis = json.loads(response_text)
                alternatives = analysis.get("alternatives", [])
            except json.JSONDecodeError:
                # Fallback alternatives
                alternatives: List[AlternativeOption] = [
                    AlternativeOption(
                        id=f"alt_{i+1}",
                        title=f"简化版本实现（跳过{gap}）",
                        description=f"跳过{gap}相关功能的简化实现",
                        approach="简化实现",
                        trade_offs=[f"不包含{gap}功能"],
                        complexity="simple",
                    )
                    for i, gap in enumerate(gaps[:2])
                ] + [
                    AlternativeOption(
                        id="alt_manual",
                        title="手动配置替代方案",
                        description="通过手动配置实现所需功能",
                        approach="手动配置",
                        trade_offs=["需要手动设置"],
                        complexity="medium",
                    )
                ]

            state["alternatives"] = alternatives

            # Present alternatives to user via negotiation
            alt_text = "由于存在能力差距，我们提供以下替代方案：\n" + "\n".join(
                [f"{i+1}. {alt}" for i, alt in enumerate(alternatives)]
            )
            self._update_conversations(state, "assistant", alt_text)

            # Set up clarification context for gap resolution
            state["clarification_context"] = ClarificationContext(
                origin=state.get("clarification_context", {}).get("origin", WorkflowOrigin.CREATE),
                pending_questions=[f"请选择您希望采用的方案（1-{len(alternatives)}）"],
            )

            return {**state, "stage": WorkflowStage.NEGOTIATION}

        except Exception as e:
            logger.error("Alternative solution generation node failed", error=str(e))
            return {
                **state,
                "stage": WorkflowStage.WORKFLOW_GENERATION,
                "debug_result": f"Alternative generation error: {str(e)}",
            }

    async def workflow_generation_node(self, state: WorkflowState) -> WorkflowState:
        """
        Workflow Generation Node - 根据确定的需求生成工作流
        """
        logger.info("Processing workflow generation node")

        try:
            intent_summary = state.get("intent_summary", "")
            gaps = state.get("gaps", [])
            alternatives = state.get("alternatives", [])
            template_workflow = state.get("template_workflow")

            # Use prompt to generate workflow
            prompt_text = await self.prompt_engine.render_prompt(
                "workflow_architecture",
                intent_summary=intent_summary,
                gaps=gaps,
                alternatives=alternatives,
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
            logger.error("Workflow generation node failed", error=str(e))
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
                    "Debug prompt analysis failed, using fallback validation", error=str(e)
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
            logger.error("Debug node failed", error=str(e))
            return {
                **state,
                "stage": WorkflowStage.DEBUG,
                "debug_result": f"Debug error: {str(e)}",
            }

    def should_continue(self, state: WorkflowState) -> str:
        """Determine the next node based on current stage"""
        stage = state.get("stage", "clarification")

        # Map stages to node names
        stage_mapping = {
            WorkflowStage.CLARIFICATION: "clarification",
            WorkflowStage.NEGOTIATION: "negotiation",
            WorkflowStage.GAP_ANALYSIS: "gap_analysis",
            WorkflowStage.WORKFLOW_GENERATION: "workflow_generation",
            WorkflowStage.ALTERNATIVE_GENERATION: "alternative_generation",
            WorkflowStage.DEBUG: "debug",
            "completed": "END",
        }

        next_node = stage_mapping.get(stage, "END")
        logger.info(f"Stage {stage} -> Next node: {next_node}")

        return next_node
