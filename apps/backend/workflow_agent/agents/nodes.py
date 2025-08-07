"""
LangGraph nodes for simplified Workflow Agent architecture
Implements the 4 core nodes: Clarification, Gap Analysis, Workflow Generation, and Debug
Based on main branch structure, updated for MCP integration
"""

import asyncio
import json
import time
import uuid
from typing import List, Dict, Any
from openai import AsyncOpenAI

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from .state import (
    ClarificationContext,
    Conversation,
    WorkflowStage,
    WorkflowState,
    GapDetail,
    get_user_message,
    get_intent_summary,
    get_gap_status,
    get_identified_gaps,
    get_current_workflow,
    get_debug_errors,
)
from .mcp_tools import MCPToolCaller, create_openai_function_definitions
from core.config import settings
import logging
from core.prompt_engine import get_prompt_engine

logger = logging.getLogger(__name__)

class WorkflowAgentNodes:
    """Simplified LangGraph nodes for workflow generation with MCP integration"""

    def __init__(self):
        self.llm = self._setup_llm()
        self.prompt_engine = get_prompt_engine()
        self.mcp_client = MCPToolCaller()
        self.openai_functions = create_openai_function_definitions()
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None

    def _setup_llm(self):
        """Setup the language model based on configuration"""
        if settings.DEFAULT_MODEL_PROVIDER == "openai":
            return ChatOpenAI(
                model=settings.DEFAULT_MODEL_NAME, 
                api_key=settings.OPENAI_API_KEY, 
                temperature=0  # Zero temperature for maximum determinism
            )
        elif settings.DEFAULT_MODEL_PROVIDER == "anthropic":
            return ChatAnthropic(
                model_name=settings.DEFAULT_MODEL_NAME,
                api_key=settings.ANTHROPIC_API_KEY,
                temperature=0,  # Zero temperature for maximum determinism
                timeout=10,
                stop=["\\n\\n"],
            )
        else:
            raise ValueError(f"Unsupported model provider: {settings.DEFAULT_MODEL_PROVIDER}")

    def _get_session_id(self, state: WorkflowState) -> str:
        """Get session ID from state"""
        return state.get("session_id", "")
    
    def _add_conversation(self, state: WorkflowState, role: str, text: str) -> None:
        """Add a new message to conversations"""
        if "conversations" not in state:
            state["conversations"] = []
        
        state["conversations"].append(Conversation(
            role=role, 
            text=text,
            timestamp=int(time.time() * 1000)
        ))

    def _get_current_scenario(self, state: WorkflowState) -> str:
        """Determine the current scenario based on state"""
        stage = state.get("stage")
        previous_stage = state.get("previous_stage")
        workflow_context = state.get("workflow_context", {})

        if stage == WorkflowStage.CLARIFICATION:
            if previous_stage == WorkflowStage.DEBUG:
                return "Debug Recovery"
            elif previous_stage == WorkflowStage.GAP_ANALYSIS:
                return "Gap Analysis Feedback Processing"
            elif workflow_context.get("template_workflow") or state.get("template_workflow"):
                return "Template Customization"
            else:
                return "Initial Clarification"
        return "Initial Clarification"

    def _get_current_goal(self, state: WorkflowState) -> str:
        """Determine the current goal based on scenario"""
        scenario = self._get_current_scenario(state)

        if scenario == "Debug Recovery":
            return "Understand what went wrong and gather ONLY the missing critical information"
        elif scenario == "Gap Analysis Feedback Processing":
            return "Process user's choice from the alternatives presented"
        elif scenario == "Template Customization":
            return "Understand the specific modifications needed for the template"
        else:
            return "Quickly understand WHAT the user wants to automate - avoid asking for details"

    def _get_scenario_type(self, state: WorkflowState) -> str:
        """Determine the scenario type for template conditional logic"""
        previous_stage = state.get("previous_stage")
        workflow_context = state.get("workflow_context", {})

        # Debug recovery has priority
        if previous_stage == WorkflowStage.DEBUG:
            return "debug_recovery"
        elif previous_stage == WorkflowStage.GAP_ANALYSIS:
            return "gap_analysis_feedback"
        elif workflow_context.get("template_workflow") or state.get("template_workflow"):
            return "template_customization"
        else:
            return "initial_clarification"

    def _get_conversation_context(self, state: WorkflowState) -> str:
        """Get conversation history for prompts"""
        conversations = state.get("conversations", [])

        if not conversations:
            return "No previous conversation"

        # Format conversation history
        history = []
        for conv in conversations[-10:]:  # Last 10 messages for context
            role = conv.get("role", "unknown")
            text = conv.get("text", "")
            history.append(f"{role.upper()}: {text}")

        return "\\n".join(history)

    async def clarification_node(self, state: WorkflowState) -> WorkflowState:
        """
        Clarification Node - 理解用户需求，提出澄清问题
        Maps prompt output to main branch state structure
        """
        logger.info("Processing clarification node")
        
        # Store the current stage as previous before updating
        current_stage = state.get("stage", WorkflowStage.CLARIFICATION)
        
        # Set stage to CLARIFICATION
        state["stage"] = WorkflowStage.CLARIFICATION

        try:
            # Check if we're coming from gap_analysis with pending questions
            clarification_context = state.get("clarification_context", {})
            pending_questions = clarification_context.get("pending_questions", [])
            previous_stage = state.get("previous_stage")
            
            logger.info(f"Clarification node check: previous_stage={previous_stage}, pending_questions={len(pending_questions) if pending_questions else 0}, context_purpose={clarification_context.get('purpose')}")
            
            # If we're coming from gap_analysis with pending questions, just wait for user input
            if previous_stage == WorkflowStage.GAP_ANALYSIS and pending_questions:
                logger.info("Coming from gap_analysis with pending questions, waiting for user input")
                # Keep the pending questions and wait for user response
                # IMPORTANT: Don't set clarification_ready to avoid infinite loop
                state["clarification_ready"] = False
                # Keep previous_stage so routing knows we came from gap_analysis
                state["previous_stage"] = WorkflowStage.GAP_ANALYSIS
                return {**state, "stage": WorkflowStage.CLARIFICATION}
            
            # Get user message from conversations
            user_message = get_user_message(state)
            if not user_message:
                user_message = "Continue with the workflow creation process"
            
            conversation_context = self._get_conversation_context(state)
            workflow_context = state.get("workflow_context", {})
            template_workflow = workflow_context.get("template_workflow") or state.get("template_workflow")

            # Get scenario-specific prompt
            scenario_type = self._get_scenario_type(state)
            
            # Prepare context for template, including gap negotiation info
            template_context = {
                "user_message": user_message,
                "user_input": user_message,  # For the user template
                "conversation_context": conversation_context,
                "template_workflow": template_workflow,
                "current_scenario": self._get_current_scenario(state),
                "current_goal": self._get_current_goal(state),
                "goal": self._get_current_goal(state),  # For the user template
                "purpose": clarification_context.get("purpose", ""),
                "identified_gaps": state.get("identified_gaps", []),
                "gap_status": state.get("gap_status", "no_gap"),
                "scenario_type": scenario_type,
                "clarification_context": clarification_context,
                "execution_history": state.get("execution_history", [])
            }

            # Use the f2 template system - both system and user prompts
            system_prompt = await self.prompt_engine.render_prompt(
                "clarification_f2_system",
                **template_context
            )
            
            user_prompt = await self.prompt_engine.render_prompt(
                "clarification_f2_user",
                **template_context
            )
            
            # Debug: Log the actual prompt being sent
            logger.info("Clarification prompt details", extra={
                "user_message": user_message,
                "prompt_length": len(user_prompt)
            })

            messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            
            # For OpenAI, use response_format to enforce JSON
            if settings.DEFAULT_MODEL_PROVIDER == "openai":
                response = await self.llm.ainvoke(
                    messages,
                    response_format={"type": "json_object"}
                )
            else:
                response = await self.llm.ainvoke(messages)

            # Parse response
            response_text = (
                response.content if isinstance(response.content, str) else str(response.content)
            )

            # Try to parse as JSON for structured response
            try:
                # Remove markdown code blocks if present
                clean_text = response_text.strip()
                if clean_text.startswith("```json"):
                    clean_text = clean_text[7:]
                    if clean_text.endswith("```"):
                        clean_text = clean_text[:-3]
                elif clean_text.startswith("```"):
                    clean_text = clean_text[3:]
                    if clean_text.endswith("```"):
                        clean_text = clean_text[:-3]

                clarification_output = json.loads(clean_text.strip())
                is_ready = clarification_output.get("is_complete", False)

                # Map to main branch state structure
                state["intent_summary"] = clarification_output.get("intent_summary", "")
                
                # Check if user selected an alternative from gap negotiation
                gap_resolution = clarification_output.get("gap_resolution", {})
                if gap_resolution.get("user_selected_alternative", False):
                    # User made a choice, mark gap as resolved
                    state["gap_status"] = "gap_resolved"
                    logger.info(f"User selected alternative {gap_resolution.get('selected_index')} with confidence {gap_resolution.get('confidence')}")
                
                # Update clarification context - preserve purpose if in gap negotiation
                existing_purpose = clarification_context.get("purpose", "initial_intent")
                new_purpose = "gap_resolved" if gap_resolution.get("user_selected_alternative", False) else existing_purpose
                
                clarification_context = ClarificationContext(
                    purpose=new_purpose,
                    collected_info={"intent": clarification_output.get("intent_summary", "")},
                    pending_questions=[clarification_output.get("clarification_question", "")] if clarification_output.get("clarification_question") else [],
                    origin=clarification_context.get("origin", "create")
                )
                state["clarification_context"] = clarification_context

            except json.JSONDecodeError:
                # Fallback to simple format
                state["intent_summary"] = response_text[:200]
                state["clarification_context"] = ClarificationContext(
                    purpose="initial_intent",
                    collected_info={"intent": response_text[:200]},
                    pending_questions=[response_text],
                    origin="create"
                )
                is_ready = False

            # Add to conversations
            self._add_conversation(state, "assistant", response_text)

            # Keep stage as CLARIFICATION - routing logic will decide next step
            # Store whether we're ready to continue for routing decision
            state["clarification_ready"] = is_ready
            # Set previous_stage for next node to know where we came from
            state["previous_stage"] = WorkflowStage.CLARIFICATION
            return {**state, "stage": WorkflowStage.CLARIFICATION}

        except Exception as e:
            logger.error("Clarification node failed", extra={"error": str(e)})
            return {
                **state,
                "stage": WorkflowStage.CLARIFICATION,
            }

    async def gap_analysis_node(self, state: WorkflowState) -> WorkflowState:
        """
        Gap Analysis Node - 分析需求可行性，识别gap
        Maps prompt output to main branch state structure
        """
        logger.info("Processing gap analysis node")
        
        # Set stage to GAP_ANALYSIS
        state["stage"] = WorkflowStage.GAP_ANALYSIS

        try:
            intent_summary = get_intent_summary(state)
            conversation_context = self._get_conversation_context(state)
            
            # Check if we're coming back from clarification after user made a choice
            clarification_context = state.get("clarification_context", {})
            previous_stage = state.get("previous_stage")
            logger.info(f"Gap analysis check: previous_stage={previous_stage}, clarification_purpose={clarification_context.get('purpose')}")
            
            # If coming from clarification after gap negotiation, mark as resolved
            if previous_stage == WorkflowStage.CLARIFICATION and clarification_context.get("purpose") in ["gap_negotiation", "gap_resolved"]:
                # User has already chosen from alternatives, mark gap as resolved
                logger.info("User has made choice from gap alternatives, marking as resolved")
                state["gap_status"] = "gap_resolved"
                # Clear the pending questions since user responded
                clarification_context["pending_questions"] = []
                clarification_context["purpose"] = "gap_resolved"  # Update purpose
                state["clarification_context"] = clarification_context
                # Set previous_stage for routing
                state["previous_stage"] = WorkflowStage.GAP_ANALYSIS
                # Don't need to run LLM again, just return with gap_resolved
                return {**state, "stage": WorkflowStage.GAP_ANALYSIS}

            # Determine scenario type for gap analysis
            if clarification_context.get("purpose") == "gap_negotiation":
                scenario_type = "post_negotiation"
            else:
                scenario_type = "initial_analysis"

            # Prepare context for both templates
            template_context = {
                "intent_summary": intent_summary,
                "conversation_context": conversation_context,
                "scenario_type": scenario_type,
                "current_scenario": self._get_current_scenario(state),
                "goal": self._get_current_goal(state),
                "template_workflow": state.get("template_workflow"),
                "current_workflow": state.get("current_workflow"),
                "debug_result": state.get("debug_result"),
                "execution_history": state.get("execution_history", []),
                "user_feedback": get_user_message(state) if scenario_type == "post_negotiation" else None,
                "selected_alternative": None  # TODO: Extract from user message if needed
            }

            # Use both system and user templates
            system_prompt = await self.prompt_engine.render_prompt(
                "gap_analysis_f2_system",
                **template_context
            )
            
            user_prompt = await self.prompt_engine.render_prompt(
                "gap_analysis_f2_user",
                **template_context
            )

            messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            response = await self.llm.ainvoke(messages)

            response_text = (
                response.content if isinstance(response.content, str) else str(response.content)
            )

            # Try to parse structured response
            try:
                # Remove markdown code blocks if present
                clean_text = response_text.strip()
                if clean_text.startswith("```json"):
                    clean_text = clean_text[7:]
                    if clean_text.endswith("```"):
                        clean_text = clean_text[:-3]
                elif clean_text.startswith("```"):
                    clean_text = clean_text[3:]
                    if clean_text.endswith("```"):
                        clean_text = clean_text[:-3]

                gap_analysis_output = json.loads(clean_text.strip())
                gap_status = gap_analysis_output.get("gap_status", "no_gap")
                negotiation_phrase = gap_analysis_output.get("negotiation_phrase", "")
                
                logger.info(f"Gap analysis result: gap_status={gap_status}, has_negotiation_phrase={bool(negotiation_phrase)}")

                # Map to main branch state structure
                state["gap_status"] = gap_status
                
                # Convert identified_gaps format
                identified_gaps_data = gap_analysis_output.get("identified_gaps", [])
                identified_gaps = []
                for gap in identified_gaps_data:
                    identified_gaps.append(GapDetail(
                        required_capability=gap.get("required_capability", ""),
                        missing_component=gap.get("missing_component", ""),
                        alternatives=gap.get("alternatives", [])
                    ))
                state["identified_gaps"] = identified_gaps
                
                # If we have gaps, set up for user input
                if gap_status == "has_gap":
                    # If no negotiation phrase provided, create a default one
                    if not negotiation_phrase:
                        negotiation_phrase = "I've identified some gaps in the workflow. Please choose from the alternatives provided or specify your preference."
                    
                    # Add negotiation phrase to conversations
                    self._add_conversation(state, "assistant", negotiation_phrase)
                    
                    # Set up clarification context to wait for user's choice
                    clarification_context = state.get("clarification_context", {})
                    clarification_context["purpose"] = "gap_negotiation"
                    clarification_context["pending_questions"] = [negotiation_phrase]
                    state["clarification_context"] = clarification_context
                else:
                    # For other cases, just add the full response
                    self._add_conversation(state, "assistant", response_text)

            except json.JSONDecodeError:
                # Fallback
                state["gap_status"] = "no_gap"
                state["identified_gaps"] = []
                # Add fallback response
                self._add_conversation(state, "assistant", response_text)

            # Keep stage as GAP_ANALYSIS and let routing logic decide based on gap_status
            # The prompt returns: "no_gap", "has_gap", or "gap_resolved"
            # Set previous_stage so clarification knows we're coming from gap_analysis
            state["previous_stage"] = WorkflowStage.GAP_ANALYSIS
            return {**state, "stage": WorkflowStage.GAP_ANALYSIS}

        except Exception as e:
            logger.error("Gap analysis node failed", extra={"error": str(e)})
            return {
                **state,
                "stage": WorkflowStage.GAP_ANALYSIS,
            }

    async def workflow_generation_node(self, state: WorkflowState) -> WorkflowState:
        """
        Workflow Generation Node - Uses MCP tools to generate accurate workflows
        """
        logger.info("Processing workflow generation node with MCP tools")
        
        # Set stage to WORKFLOW_GENERATION
        state["stage"] = WorkflowStage.WORKFLOW_GENERATION

        try:
            intent_summary = get_intent_summary(state)
            gap_status = get_gap_status(state)
            identified_gaps = get_identified_gaps(state)
            conversation_context = self._get_conversation_context(state)
            workflow_context = state.get("workflow_context", {})

            # Load the workflow generation prompt
            workflow_gen_prompt = await self.prompt_engine.render_prompt(
                "workflow_gen_f1",
                intent_summary=intent_summary,
                conversation_context=conversation_context
            )

            # Use OpenAI with function calling for MCP tools
            if not self.openai_client:
                # Fallback to original implementation if OpenAI client not available
                logger.warning("OpenAI client not available, using fallback generation")
                return await self._fallback_workflow_generation(state)

            messages = [
                {"role": "system", "content": workflow_gen_prompt},
                {"role": "user", "content": f"Create a comprehensive workflow based on these requirements:\\n\\n{intent_summary}\\n\\nConversation context:\\n{conversation_context}\\n\\nIMPORTANT: First call get_node_types to discover available nodes, then use get_node_details for the specific nodes you need, and finally generate the complete workflow JSON."}
            ]

            # Phase 1: Discovery
            logger.info("Starting MCP-based workflow generation - Phase 1: Discovery")
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                tools=self.openai_functions,
                tool_choice="auto"
            )

            workflow_json = await self._process_mcp_workflow_generation(messages, response)
            
            # Parse the workflow JSON
            try:
                # Clean up the response
                workflow_json = workflow_json.strip()
                if workflow_json.startswith("```json"):
                    workflow_json = workflow_json[7:]
                    if workflow_json.endswith("```"):
                        workflow_json = workflow_json[:-3]
                elif workflow_json.startswith("```"):
                    workflow_json = workflow_json[3:]
                    if workflow_json.endswith("```"):
                        workflow_json = workflow_json[:-3]

                workflow = json.loads(workflow_json.strip())
                logger.info("Successfully generated workflow using MCP tools")

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse workflow JSON: {e}")
                logger.error(f"Raw response was: {workflow_json[:500]}...")
                # Use fallback workflow
                workflow = self._create_fallback_workflow(intent_summary)

            # Store in main branch state structure
            state["current_workflow"] = workflow
            # Keep stage as WORKFLOW_GENERATION so routing goes to debug node
            return {**state, "stage": WorkflowStage.WORKFLOW_GENERATION}

        except Exception as e:
            logger.error("Workflow generation node failed", extra={"error": str(e)})
            return {
                **state,
                "stage": WorkflowStage.WORKFLOW_GENERATION,
            }

    async def _process_mcp_workflow_generation(self, messages: List[Dict], response) -> str:
        """Process MCP tool calls for workflow generation"""
        message = response.choices[0].message
        
        if not message.tool_calls:
            return message.content or ""

        # Add assistant message with tool calls
        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": message.tool_calls
        })

        # Execute tool calls
        for tool_call in message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            logger.info(f"Executing MCP tool: {function_name}")

            # Call the appropriate MCP tool
            if function_name == "get_node_types":
                result = await self.mcp_client.get_node_types(
                    function_args.get("type_filter")
                )
            elif function_name == "get_node_details":
                result = await self.mcp_client.get_node_details(
                    function_args.get("nodes", []),
                    function_args.get("include_examples", True),
                    function_args.get("include_schemas", True)
                )
            else:
                result = {"error": f"Unknown tool: {function_name}"}

            # Add tool response
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result)
            })

        # Final generation call
        messages.append({
            "role": "user",
            "content": "Generate the complete workflow JSON using the node specifications you retrieved. Output ONLY JSON."
        })

        final_response = await self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=messages
        )

        return final_response.choices[0].message.content or ""

    async def _fallback_workflow_generation(self, state: WorkflowState) -> WorkflowState:
        """Fallback to original workflow generation without MCP tools"""
        logger.info("Using fallback workflow generation without MCP tools")

        intent_summary = get_intent_summary(state)
        workflow = self._create_fallback_workflow(intent_summary)

        # Store in main branch state structure
        state["current_workflow"] = workflow
        # Keep stage as WORKFLOW_GENERATION so routing goes to debug node
        return {**state, "stage": WorkflowStage.WORKFLOW_GENERATION}

    def _create_fallback_workflow(self, intent_summary: str) -> dict:
        """Create a basic fallback workflow structure"""
        return {
            "id": f"workflow-{uuid.uuid4().hex[:8]}",
            "name": "Generated Workflow",
            "description": intent_summary,
            "nodes": [
                {"id": "start", "type": "trigger", "name": "Start", "parameters": {}},
                {"id": "process", "type": "action", "name": "Process", "parameters": {}},
            ],
            "connections": [{"from": "start", "to": "process"}],
            "created_at": int(time.time()),
        }

    async def debug_node(self, state: WorkflowState) -> WorkflowState:
        """
        Debug Node - 测试生成的工作流，发现并尝试修复错误
        Maps structured prompt output to main branch debug_result
        """
        logger.info("Processing debug node")
        
        # Update stage to DEBUG
        state["stage"] = WorkflowStage.DEBUG

        try:
            current_workflow = get_current_workflow(state)
            if not current_workflow:
                # No workflow to debug
                state["debug_result"] = {
                    "success": False,
                    "errors": ["No workflow to debug"],
                    "timestamp": int(time.time() * 1000)
                }
                return {**state, "stage": WorkflowStage.WORKFLOW_GENERATION}
            
            debug_loop_count = state.get("debug_loop_count", 0)

            # Use the debug prompt for sophisticated validation
            try:
                prompt_text = await self.prompt_engine.render_prompt(
                    "debug",
                    current_workflow=current_workflow,
                    debug_loop_count=debug_loop_count,
                    previous_errors=get_debug_errors(state),
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

                debug_output = json.loads(response_text.strip())
                logger.info("debug_analysis result", extra={"debug_analysis": debug_output})

                # Normalize the debug output format for main branch
                success = (
                    debug_output.get("success", False) or
                    debug_output.get("validation_summary", {}).get("overall_status") == "valid"
                )
                
                errors = []
                if "errors" in debug_output:
                    errors = debug_output["errors"]
                elif "issues_found" in debug_output:
                    critical_errors = debug_output["issues_found"].get("critical_errors", [])
                    errors = [error.get("description", str(error)) for error in critical_errors]

                # Store structured debug result in main branch format
                state["debug_result"] = {
                    "success": success,
                    "errors": errors,
                    "warnings": debug_output.get("warnings", []),
                    "suggestions": debug_output.get("suggestions", []),
                    "iteration_count": debug_loop_count,
                    "timestamp": int(time.time() * 1000)
                }

            except Exception as e:
                logger.warning("LLM debug analysis failed, using basic validation", extra={"error": str(e)})
                # Fallback to basic validation
                debug_result = self._basic_workflow_validation(current_workflow)
                state["debug_result"] = debug_result
                success = debug_result["success"]
                errors = debug_result["errors"]

            # Update debug loop count
            state["debug_loop_count"] = debug_loop_count + 1

            # Determine next action based on debug result
            if success:
                logger.info("Workflow validation successful")
                return {**state, "stage": WorkflowStage.COMPLETED}

            # If we've tried too many times, give up
            if debug_loop_count >= 3:
                logger.warning("Max debug attempts reached, ending with current workflow")
                return {**state, "stage": WorkflowStage.COMPLETED}

            # Analyze error type to decide next stage
            error_types = self._analyze_error_types(errors)

            if error_types["missing_requirements"]:
                # Need more information from user
                logger.info("Missing requirements detected, returning to clarification")
                # Reset clarification_ready since we need more info
                state["clarification_ready"] = False
                return {
                    **state,
                    "stage": WorkflowStage.CLARIFICATION,
                    "previous_stage": WorkflowStage.DEBUG,
                }
            else:
                # Can fix with regeneration
                logger.info("Fixable errors detected, returning to workflow generation")
                return {
                    **state,
                    "stage": WorkflowStage.WORKFLOW_GENERATION,
                    "previous_stage": WorkflowStage.DEBUG,
                }

        except Exception as e:
            logger.error("Debug node failed", extra={"error": str(e)})
            # On debug failure, assume workflow is acceptable
            return {**state, "stage": WorkflowStage.COMPLETED}

    def _basic_workflow_validation(self, workflow: dict) -> dict:
        """Basic workflow validation when LLM analysis fails"""
        errors = []
        warnings = []

        # Check required fields - be lenient about ID/name
        if not workflow.get("id") and not workflow.get("name"):
            warnings.append("No workflow ID or name")
        if not workflow.get("nodes"):
            errors.append("No nodes defined in workflow")
        if not workflow.get("connections"):
            warnings.append("No connections defined between nodes")

        # Check node structure
        nodes = workflow.get("nodes", [])
        for node in nodes:
            if not node.get("id"):
                errors.append(f"Node missing ID: {node}")
            if not node.get("type"):
                errors.append(f"Node missing type: {node.get('id', 'unknown')}")

        return {
            "success": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "suggestions": [],
            "timestamp": int(time.time() * 1000)
        }

    def _analyze_error_types(self, errors: List[str]) -> dict:
        """Analyze error types to determine the appropriate recovery action"""
        error_types = {
            "missing_requirements": False,
            "structural_issues": False,
            "logic_errors": False,
        }

        for error in errors:
            error_lower = error.lower()
            if any(
                keyword in error_lower
                for keyword in ["missing", "undefined", "not specified", "unclear", "ambiguous"]
            ):
                error_types["missing_requirements"] = True
            elif any(
                keyword in error_lower
                for keyword in ["invalid", "structure", "format", "schema", "connection"]
            ):
                error_types["structural_issues"] = True
            elif any(keyword in error_lower for keyword in ["logic", "flow", "sequence", "loop"]):
                error_types["logic_errors"] = True

        return error_types

    def should_continue(self, state: WorkflowState) -> str:
        """
        Determine the next step based on current state
        Used by LangGraph for conditional routing
        """
        stage = state.get("stage", WorkflowStage.CLARIFICATION)
        logger.info(f"should_continue called with stage: {stage}")
        
        # Map stage to next action
        if stage == WorkflowStage.CLARIFICATION:
            # Check if we have pending questions that need user response
            clarification_context = state.get("clarification_context", {})
            pending_questions = clarification_context.get("pending_questions", [])
            
            # Also check the clarification_ready flag for backward compatibility
            clarification_ready = state.get("clarification_ready", False)
            
            logger.info(f"Clarification routing check: pending_questions={len(pending_questions)}, ready={clarification_ready}")
            
            # If we have pending questions, wait for user input
            if pending_questions:
                logger.info("Have pending questions, waiting for user input")
                return "END"
            # Otherwise, check if we're ready to proceed
            elif clarification_ready:
                return "gap_analysis"
            else:
                return "END"  # Wait for user input
                
        elif stage == WorkflowStage.GAP_ANALYSIS:
            # From gap analysis, check gap status
            # The prompt returns: "no_gap", "has_gap", or "gap_resolved"
            gap_status = state.get("gap_status", "no_gap")
            logger.info(f"Gap analysis routing check: gap_status={gap_status}")
            
            if gap_status == "has_gap":
                # We have gaps and need user to choose from alternatives
                return "clarification"  # Go back to clarification for user choice
            elif gap_status == "gap_resolved" or gap_status == "no_gap":
                # Either no gaps or gaps have been resolved
                return "workflow_generation"  # Proceed to generation
            else:
                # Fallback for any unexpected status
                return "workflow_generation"
                
        elif stage == WorkflowStage.WORKFLOW_GENERATION:
            # From workflow generation, always go to debug
            logger.info("Routing from WORKFLOW_GENERATION to debug")
            return "debug"
            
        elif stage == WorkflowStage.DEBUG:
            # From debug, check if successful
            debug_result = state.get("debug_result", {})
            if debug_result.get("success", False):
                return "END"  # Workflow is complete
            else:
                debug_loop_count = state.get("debug_loop_count", 0)
                if debug_loop_count >= 3:
                    return "END"  # Max attempts reached
                # Check error types to determine next step
                errors = debug_result.get("errors", [])
                error_types = self._analyze_error_types(errors)
                if error_types["missing_requirements"]:
                    return "clarification"  # Need more info
                else:
                    return "workflow_generation"  # Try regenerating
                    
        elif stage == WorkflowStage.COMPLETED:
            return "END"
            
        # Default to END if unknown state
        return "END"