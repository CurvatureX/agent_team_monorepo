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
    is_clarification_ready,
)
from .mcp_tools import MCPToolCaller
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
        # Get LangChain tools for MCP
        self.mcp_tools = self.mcp_client.get_langchain_tools()
        # Bind tools to LLM if supported
        self.llm_with_tools = self._setup_llm_with_tools()

    def _setup_llm(self):
        """Setup the OpenAI language model"""
        return ChatOpenAI(
            model=settings.DEFAULT_MODEL_NAME, 
            api_key=settings.OPENAI_API_KEY, 
            temperature=0
        )
    
    def _setup_llm_with_tools(self):
        """Setup OpenAI LLM with MCP tools bound"""
        llm = ChatOpenAI(
            model=settings.DEFAULT_MODEL_NAME,
            api_key=settings.OPENAI_API_KEY,
            temperature=0
        )
        # Bind MCP tools to the LLM
        return llm.bind_tools(self.mcp_tools)

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
            
            # Use OpenAI with JSON response format
            response = await self.llm.ainvoke(
                messages,
                response_format={"type": "json_object"}
            )

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
            # Note: clarification readiness is now derived from state, not stored
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
        Gap Analysis Node - 使用 MCP 分析需求可行性，智能识别和解决 gaps
        Enhanced with real capability checking and intelligent alternatives
        """
        logger.info("Processing enhanced gap analysis node with MCP")
        
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
                # Create a new clarification context with updated values
                updated_context = ClarificationContext(
                    purpose="gap_resolved",
                    collected_info=clarification_context.get("collected_info", {}),
                    pending_questions=[],  # Clear the pending questions since user responded
                    origin=clarification_context.get("origin", "create")
                )
                state["clarification_context"] = updated_context
                # Set previous_stage for routing
                state["previous_stage"] = WorkflowStage.GAP_ANALYSIS
                # Don't need to run LLM again, just return with gap_resolved
                return {**state, "stage": WorkflowStage.GAP_ANALYSIS}

            # Check negotiation count to limit rounds
            gap_negotiation_count = state.get("gap_negotiation_count", 0)
            max_rounds = settings.GAP_ANALYSIS_MAX_ROUNDS
            
            # Determine scenario type for gap analysis
            if clarification_context.get("purpose") == "gap_negotiation":
                scenario_type = "post_negotiation"
            else:
                scenario_type = "initial_analysis"
            
            # NEW: Use MCP to get real available capabilities if enabled
            available_nodes = None
            if settings.GAP_ANALYSIS_USE_MCP:
                logger.info("Fetching real node capabilities from MCP")
                available_nodes = await self._get_available_nodes_from_mcp()
                logger.info(f"Retrieved {len(available_nodes) if available_nodes else 0} node types from MCP")
            else:
                logger.info("MCP disabled, using prompt-based capability analysis")

            # Prepare context for both templates - now with MCP data
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
                "selected_alternative": None,  # TODO: Extract from user message if needed
                "available_nodes": available_nodes,  # NEW: Real MCP capabilities
                "negotiation_count": gap_negotiation_count  # NEW: Track negotiation rounds
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
                
                # If we have gaps, set up for user input with smart handling
                if gap_status == "has_gap":
                    # Track negotiation count
                    state["gap_negotiation_count"] = gap_negotiation_count + 1
                    
                    # Check if we've reached max negotiation rounds (configurable)
                    if state["gap_negotiation_count"] > max_rounds:
                        # Auto-select recommended alternative
                        logger.info("Max negotiation rounds reached, using recommended alternative")
                        state["gap_status"] = "gap_resolved"
                        # Select first alternative as default
                        if identified_gaps and identified_gaps[0].alternatives:
                            state["selected_alternative"] = identified_gaps[0].alternatives[0]
                            self._add_conversation(state, "assistant", 
                                f"I'll proceed with the recommended approach: {identified_gaps[0].alternatives[0]}")
                    else:
                        # First negotiation - present alternatives with smart recommendation
                        negotiation_phrase = await self._create_smart_negotiation_message(
                            identified_gaps, intent_summary, negotiation_phrase
                        )
                        
                        # Add negotiation phrase to conversations
                        self._add_conversation(state, "assistant", negotiation_phrase)
                        
                        # Set up clarification context to wait for user's choice
                        existing_context = state.get("clarification_context", {})
                        updated_context = ClarificationContext(
                            purpose="gap_negotiation",
                            collected_info=existing_context.get("collected_info", {}),
                            pending_questions=[negotiation_phrase],
                            origin=existing_context.get("origin", "create")
                        )
                        state["clarification_context"] = updated_context
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
        Now enhanced to handle error-based regeneration from debug node
        """
        logger.info("Processing workflow generation node with MCP tools")
        
        # Set stage to WORKFLOW_GENERATION
        state["stage"] = WorkflowStage.WORKFLOW_GENERATION

        try:
            intent_summary = get_intent_summary(state)
            conversation_context = self._get_conversation_context(state)
            
            # Check if we're coming from debug with errors
            debug_result = state.get("debug_result") or {}
            previous_errors = debug_result.get("errors", []) if debug_result else []
            previous_suggestions = debug_result.get("suggestions", []) if debug_result else []
            debug_loop_count = state.get("debug_loop_count", 0)
            
            # Build enhanced context if we have debug feedback
            error_context = ""
            if previous_errors:
                error_context = f"""
                
IMPORTANT: Previous attempt failed with these errors:
Errors: {json.dumps(previous_errors, indent=2)}
Suggestions: {json.dumps(previous_suggestions, indent=2) if previous_suggestions else 'None'}

Please fix these issues in the regenerated workflow:
1. Address each error specifically
2. Apply the suggestions if provided
3. Ensure all node parameters are correctly configured
4. Verify connection logic is sound
"""

            # Load the workflow generation prompt
            workflow_gen_prompt = await self.prompt_engine.render_prompt(
                "workflow_gen_f1",
            )

            # Build the user message with error context if available
            user_message = f"Create a comprehensive workflow based on these requirements:\\n\\n{intent_summary}\\n\\nConversation context:\\n{conversation_context}"
            
            if error_context:
                user_message += error_context
                logger.info(f"Regenerating workflow after debug failure (attempt {debug_loop_count + 1})")
            
            user_message += """

IMPORTANT WORKFLOW GENERATION PROCESS:
1. First, use get_node_types to discover all available node types
2. Then, use get_node_details to get specifications for the nodes you need
3. Finally, generate a COMPLETE workflow JSON with this structure:
{
  "name": "...",
  "description": "...",
  "nodes": [...],
  "connections": {...},
  "settings": {...},
  "static_data": {},
  "tags": []
}

You MUST use the exact node types, subtypes, and parameters from the MCP responses."""
            
            messages = [
                SystemMessage(content=workflow_gen_prompt),
                HumanMessage(content=user_message)
            ]

            # Generate workflow using OpenAI with tools
            workflow_json = await self._generate_with_tools(messages)
            
            # Check if we got an empty response
            if not workflow_json or workflow_json.strip() == "":
                logger.error("Empty response from LLM, using fallback workflow")
                workflow = self._create_fallback_workflow(intent_summary)
            else:
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
                    logger.info("Successfully generated workflow using MCP tools, workflow: %s", workflow)

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse workflow JSON: {e}, response was: {workflow_json[:500]}")
                    # Use fallback workflow on parse error
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

    async def _generate_with_tools(self, messages: List) -> str:
        """
        Generate workflow using LangChain tool calling pattern.
        
        This implementation uses the recommended pattern for tool calling with structured output:
        1. Bind tools to LLM
        2. Manually handle tool execution loop
        3. Control output format
        
        Alternative approaches considered:
        - AgentExecutor: Too much overhead, adds reasoning text that breaks JSON
        - create_structured_output_agent: Good for structured output but less flexible
        - Direct OpenAI function calling: Would bypass LangChain abstractions
        """
        logger.info("Using LangChain tool binding for workflow generation")
        
        try:
            # Convert input messages to proper format
            conversation_messages = list(messages)
            
            # Tool execution loop - this is the recommended pattern for controlled tool use
            max_iterations = 5
            for iteration in range(max_iterations):
                logger.info(f"Tool execution iteration {iteration + 1}")
                
                # Call LLM with current conversation state
                response = await self.llm_with_tools.ainvoke(conversation_messages)
                
                # Add assistant response to conversation
                conversation_messages.append(response)
                
                # Check for tool calls
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    # New LangChain format uses response.tool_calls directly
                    tool_calls = response.tool_calls
                    logger.info(f"LLM made {len(tool_calls)} tool calls")
                    
                    for tool_call in tool_calls:
                        await self._execute_tool_call(tool_call, conversation_messages)
                        
                elif hasattr(response, 'additional_kwargs') and 'tool_calls' in response.additional_kwargs:
                    # Fallback to older format
                    tool_calls = response.additional_kwargs['tool_calls']
                    logger.info(f"LLM made {len(tool_calls)} tool calls (legacy format)")
                    
                    for tool_call in tool_calls:
                        await self._execute_tool_call_legacy(tool_call, conversation_messages)
                        
                elif response.content:
                    # No more tool calls, we have final output
                    logger.info("Got final response from LLM")
                    return str(response.content)
                else:
                    # Empty response without tool calls
                    logger.warning("Got empty response without tool calls")
                    break
            
            # Max iterations reached or empty response
            logger.warning("Tool execution completed without final JSON")
            # Try to get the last non-empty content
            for msg in reversed(conversation_messages):
                if hasattr(msg, 'content') and msg.content:
                    return str(msg.content)
            return ""
                
        except Exception as e:
            logger.error(f"Tool-based generation failed: {e}", exc_info=True)
            raise e
    
    async def _execute_tool_call(self, tool_call: dict, conversation_messages: list):
        """Execute a tool call in the new LangChain format"""
        from langchain_core.messages import ToolMessage
        
        tool_name = tool_call.get('name', '')
        tool_args = tool_call.get('args', {})
        tool_id = tool_call.get('id', '')
        
        logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
        
        # Find and execute the tool
        tool_result = await self._run_tool(tool_name, tool_args)
        
        # Add tool result as ToolMessage
        tool_message = ToolMessage(
            content=str(tool_result),
            tool_call_id=tool_id,
            name=tool_name
        )
        conversation_messages.append(tool_message)
        logger.info(f"Tool {tool_name} result added to conversation")
    
    async def _execute_tool_call_legacy(self, tool_call: dict, conversation_messages: list):
        """Execute a tool call in the legacy format"""
        from langchain_core.messages import ToolMessage
        
        tool_name = tool_call.get('function', {}).get('name', '')
        tool_args_str = tool_call.get('function', {}).get('arguments', '{}')
        tool_args = json.loads(tool_args_str) if tool_args_str else {}
        tool_id = tool_call.get('id', '')
        
        logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
        
        # Find and execute the tool
        tool_result = await self._run_tool(tool_name, tool_args)
        
        # Add tool result as ToolMessage
        tool_message = ToolMessage(
            content=str(tool_result),
            tool_call_id=tool_id,
            name=tool_name
        )
        conversation_messages.append(tool_message)
        logger.info(f"Tool {tool_name} result added to conversation")
    
    async def _run_tool(self, tool_name: str, tool_args: dict) -> str:
        """Execute a tool by name with given arguments"""
        for tool in self.mcp_tools:
            if tool.name == tool_name:
                try:
                    # LangChain tools have either coroutine (async) or func (sync)
                    if tool.coroutine:
                        # Async function - await it
                        result = await tool.coroutine(**tool_args)
                    elif tool.func:
                        # Sync function - call it directly (no await)
                        result = tool.func(**tool_args)
                    else:
                        result = f"Error: Tool {tool_name} has no implementation"
                    return str(result)
                except Exception as e:
                    logger.error(f"Error executing tool {tool_name}: {e}")
                    return f"Error executing tool: {str(e)}"
        
        return f"Error: Tool {tool_name} not found"
    

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
        Now integrates with workflow_engine to actually execute and test workflows
        """
        logger.info("Processing debug node with workflow engine integration")
        
        # Update stage to DEBUG
        state["stage"] = WorkflowStage.DEBUG
        
        # Import dependencies here to avoid circular imports
        from services.workflow_engine_client import WorkflowEngineClient
        from .test_data_generator import TestDataGenerator
        
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
            
            # Step 1: Generate test data for the workflow
            logger.info("Generating test data for workflow execution")
            test_generator = TestDataGenerator()
            test_data = await test_generator.generate_test_data(current_workflow)
            
            # Step 2: Create and execute the workflow using workflow_engine
            logger.info("Creating and executing workflow in workflow_engine")
            engine_client = WorkflowEngineClient()
            
            # Get user_id from state or use default
            user_id = state.get("user_id", "test_user")
            
            # Execute the workflow with test data
            execution_result = await engine_client.validate_and_execute_workflow(
                workflow_data=current_workflow,
                test_data=test_data,
                user_id=user_id
            )
            
            # Step 3: Analyze execution results
            if not execution_result:
                # Handle None or empty result
                logger.error("No execution result returned from workflow engine")
                execution_result = {"success": False, "error": "No response from workflow engine"}
            
            success = execution_result.get("success", False)
            errors = []
            warnings = []
            
            if not success:
                # Execution failed - analyze the error
                stage = execution_result.get("stage", "unknown")
                error_msg = execution_result.get("error", "Unknown error")
                
                if stage == "creation":
                    # Workflow creation failed - likely structural issues
                    errors.append(f"Workflow creation failed: {error_msg}")
                    # Parse detailed error if available
                    details = execution_result.get("details", {})
                    if details.get("status_code") == 400:
                        errors.append("Invalid workflow structure or parameters")
                    elif details.get("status_code") == 500:
                        errors.append("Internal error in workflow engine")
                        
                elif stage == "execution":
                    # Workflow created but execution failed
                    errors.append(f"Workflow execution failed: {error_msg}")
                    workflow_id = execution_result.get("workflow_id")
                    if workflow_id:
                        warnings.append(f"Workflow was created with ID: {workflow_id}")
                    # This might indicate missing parameters or logic errors
                    errors.append("Check node parameters and connection logic")
            else:
                # Success! Log the execution details
                logger.info(
                    "Workflow executed successfully",
                    extra={
                        "workflow_id": execution_result.get("workflow_id"),
                        "execution_id": execution_result.get("execution_id")
                    }
                )
            
            # Step 4: If there are errors, also run static validation for more insights
            if errors or debug_loop_count == 0:
                # Use the existing LLM-based validation for additional insights
                try:
                    prompt_text = await self.prompt_engine.render_prompt(
                        "debug",
                        current_workflow=current_workflow,
                        debug_loop_count=debug_loop_count,
                        previous_errors=errors,
                    )

                    system_prompt = (
                        "You are a workflow debugging specialist. Analyze the workflow and any execution errors."
                    )
                    user_prompt = prompt_text

                    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
                    llm_response = await self.llm.ainvoke(messages)

                    # Parse LLM response
                    response_text = (
                        llm_response.content
                        if isinstance(llm_response.content, str)
                        else str(llm_response.content)
                    )

                    # Clean JSON
                    if response_text.strip().startswith("```json"):
                        response_text = response_text.strip()[7:]
                        if response_text.endswith("```"):
                            response_text = response_text[:-3]
                    elif response_text.strip().startswith("```"):
                        response_text = response_text.strip()[3:]
                        if response_text.endswith("```"):
                            response_text = response_text[:-3]

                    debug_output = json.loads(response_text.strip())
                    
                    # Merge LLM insights with execution results
                    if "issues_found" in debug_output:
                        additional_errors = debug_output["issues_found"].get("critical_errors", [])
                        for error in additional_errors:
                            error_desc = error.get("description", str(error))
                            if error_desc not in errors:
                                errors.append(error_desc)
                    
                    if "warnings" in debug_output:
                        warnings.extend(debug_output.get("warnings", []))
                    
                    suggestions = debug_output.get("suggestions", [])

                except Exception as e:
                    logger.warning(f"LLM analysis failed: {str(e)}")
                    suggestions = []
            else:
                suggestions = []
            
            # Store the complete debug result
            state["debug_result"] = {
                "success": success,
                "errors": errors,
                "warnings": warnings,
                "suggestions": suggestions,
                "execution_result": execution_result if not success else None,
                "test_data_used": test_data,
                "iteration_count": debug_loop_count,
                "timestamp": int(time.time() * 1000)
            }

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
                # Note: clarification readiness will be derived from pending questions
                return {
                    **state,
                    "stage": WorkflowStage.CLARIFICATION,
                    "previous_stage": WorkflowStage.DEBUG,
                }
            else:
                # Can fix with regeneration - keep stage as DEBUG
                # The routing logic will handle sending it to workflow_generation
                logger.info("Fixable errors detected, will route to workflow generation")
                return {
                    **state,
                    "stage": WorkflowStage.DEBUG,  # Keep as DEBUG, let routing handle it
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
            # Check for parameter-related errors first (these are structural, not missing requirements)
            if "missing required parameter" in error_lower or "field required" in error_lower:
                # Missing required parameter/field is a structural issue (wrong parameter name)
                # This can be fixed by regeneration with correct MCP specs
                error_types["structural_issues"] = True
            elif any(
                keyword in error_lower
                for keyword in ["parameter", "must be", "integer", "string", "type", "float", "boolean", "dict_type", "position", "subtype"]
            ):
                # Parameter type mismatches and missing fields are structural issues
                error_types["structural_issues"] = True
            elif any(
                keyword in error_lower
                for keyword in ["missing", "undefined", "not specified", "unclear", "ambiguous"]
            ):
                # Only treat as missing requirements if it's about user intent, not structure
                error_types["missing_requirements"] = True
            elif any(
                keyword in error_lower
                for keyword in ["invalid", "structure", "format", "schema", "connection"]
            ):
                error_types["structural_issues"] = True
            elif any(keyword in error_lower for keyword in ["logic", "flow", "sequence", "loop"]):
                error_types["logic_errors"] = True

        return error_types

    async def _get_available_nodes_from_mcp(self) -> dict:
        """
        Get real available node types and capabilities from MCP
        Returns a structured dict of available nodes
        """
        try:
            # Use MCP to get all available node types
            node_types = await self.mcp_client.get_node_types()
            logger.info(f"MCP returned node types: {node_types}")
            return node_types
        except Exception as e:
            logger.warning(f"Failed to get MCP node types, using fallback: {e}")
            # Fallback to basic node types if MCP fails
            return self._get_fallback_node_types()
    
    def _get_fallback_node_types(self) -> dict:
        """Fallback node types when MCP is unavailable"""
        return {
            "TRIGGER_NODE": ["schedule", "webhook", "manual", "email"],
            "AI_AGENT_NODE": ["ai_agent"],
            "ACTION_NODE": ["http_request", "database", "file_operation"],
            "FLOW_NODE": ["if", "loop", "wait"],
            "EXTERNAL_ACTION_NODE": ["github", "slack", "email", "api_call"]
        }
    
    async def _create_smart_negotiation_message(self, identified_gaps, intent_summary, default_phrase):
        """
        Create an intelligent negotiation message with recommendations
        """
        if not identified_gaps:
            return default_phrase or "I'll help you create this workflow."
        
        # Analyze alternatives to find the best recommendation
        recommendation = self._analyze_best_alternative(identified_gaps, intent_summary)
        
        # Build the message
        message_parts = []
        message_parts.append(f"I found {len(identified_gaps)} capability {'gap' if len(identified_gaps) == 1 else 'gaps'} for your workflow.\n")
        
        for i, gap in enumerate(identified_gaps):
            if gap.alternatives:
                message_parts.append(f"\nFor {gap.required_capability}:")
                for j, alt in enumerate(gap.alternatives[:3]):  # Limit to 3 alternatives
                    star = "⭐ " if j == recommendation.get(gap.required_capability, 0) else ""
                    message_parts.append(f"{star}{chr(65+j)}) {alt}")
        
        message_parts.append(f"\n{chr(65 + recommendation.get('overall', 0))} is recommended based on your requirements.")
        message_parts.append("\nChoose an option (A/B/C) or describe your preference:")
        
        return "\n".join(message_parts)
    
    def _analyze_best_alternative(self, identified_gaps, intent_summary):
        """
        Analyze and recommend the best alternative based on user intent
        """
        recommendation = {}
        
        # Simple heuristic: prefer first alternative as it's usually the most straightforward
        # In production, this could use more sophisticated analysis
        for gap in identified_gaps:
            if gap.alternatives:
                # Score alternatives based on simplicity and reliability
                scores = []
                for alt in gap.alternatives:
                    score = self._score_alternative(alt, intent_summary)
                    scores.append(score)
                
                best_idx = scores.index(max(scores)) if scores else 0
                recommendation[gap.required_capability] = best_idx
        
        # Overall recommendation (simplified: use most common recommendation)
        if recommendation:
            recommendation['overall'] = max(set(recommendation.values()), key=list(recommendation.values()).count)
        else:
            recommendation['overall'] = 0
            
        return recommendation
    
    def _score_alternative(self, alternative, intent_summary):
        """
        Score an alternative based on various factors
        """
        score = 0
        alt_lower = alternative.lower()
        
        # Prefer simpler solutions
        if any(word in alt_lower for word in ['simple', 'basic', 'standard']):
            score += 2
        
        # Prefer scheduled/automated solutions for automation requests
        if 'automat' in intent_summary.lower() and 'schedule' in alt_lower:
            score += 3
        
        # Prefer webhook for real-time needs
        if any(word in intent_summary.lower() for word in ['real-time', 'instant', 'immediate']) and 'webhook' in alt_lower:
            score += 3
        
        # Penalize complex solutions
        if any(word in alt_lower for word in ['complex', 'advanced', 'custom']):
            score -= 1
            
        return score

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
            
            # Derive clarification readiness from state
            clarification_ready = is_clarification_ready(state)
            
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
            # From gap analysis, check gap status and negotiation count
            gap_status = state.get("gap_status", "no_gap")
            gap_negotiation_count = state.get("gap_negotiation_count", 0)
            logger.info(f"Gap analysis routing: gap_status={gap_status}, negotiation_count={gap_negotiation_count}")
            
            if gap_status == "has_gap":
                # Check if we've reached max negotiation rounds (configurable)
                max_rounds = settings.GAP_ANALYSIS_MAX_ROUNDS
                if gap_negotiation_count >= max_rounds:
                    # Already negotiated once, proceed with recommendation
                    logger.info("Max negotiation rounds reached, proceeding with recommended alternative")
                    return "workflow_generation"
                else:
                    # First time finding gaps, go to clarification for user choice
                    return "clarification"
            elif gap_status == "gap_resolved" or gap_status == "no_gap":
                # Either no gaps or gaps have been resolved
                return "workflow_generation"
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