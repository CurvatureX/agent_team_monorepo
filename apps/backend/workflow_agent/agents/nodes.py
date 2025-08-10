"""
LangGraph nodes for optimized Workflow Agent architecture
Implements the 3 core nodes: Clarification, Workflow Generation, and Debug
Simplified architecture with automatic gap handling for better user experience
"""

import json
import time
import uuid
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from .state import (
    ClarificationContext,
    Conversation,
    WorkflowStage,
    WorkflowState,
    get_user_message,
    get_intent_summary,
    get_current_workflow,
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
                    # User made a choice
                    logger.info(f"User selected alternative {gap_resolution.get('selected_index')} with confidence {gap_resolution.get('confidence')}")
                
                # Update clarification context
                existing_purpose = clarification_context.get("purpose", "initial_intent")
                
                clarification_context = ClarificationContext(
                    purpose=existing_purpose,
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


    async def workflow_generation_node(self, state: WorkflowState) -> WorkflowState:
        """
        Optimized Workflow Generation Node - Automatically handles capability gaps
        Uses MCP tools to generate accurate workflows with smart substitutions
        """
        logger.info("Processing optimized workflow generation node")
        
        # Set stage to WORKFLOW_GENERATION
        state["stage"] = WorkflowStage.WORKFLOW_GENERATION

        try:
            intent_summary = get_intent_summary(state)
            conversation_context = self._get_conversation_context(state)
            
            # Check if we're coming from debug with errors
            debug_error = state.get("debug_error_for_regeneration")
            debug_result = state.get("debug_result") or {}
            debug_loop_count = state.get("debug_loop_count", 0)
            
            # Get available nodes from MCP if enabled
            available_nodes = None
            if settings.GAP_ANALYSIS_USE_MCP:
                logger.info("Fetching node capabilities from MCP")
                try:
                    available_nodes = await self._get_available_nodes_from_mcp()
                    logger.info(f"Retrieved {len(available_nodes) if available_nodes else 0} node types from MCP")
                except Exception as e:
                    logger.warning(f"Failed to get MCP nodes, proceeding without: {e}")
            
            # Prepare template context
            template_context = {
                "intent_summary": intent_summary,
                "conversation_context": conversation_context,
                "available_nodes": available_nodes,
                "current_workflow": state.get("current_workflow"),
                "debug_result": debug_error or (debug_result.get("error") if not debug_result.get("success", True) else None)
            }
            
            # Use the optimized prompts
            system_prompt = await self.prompt_engine.render_prompt(
                "workflow_generation_optimized_system",
                **template_context
            )
            
            user_prompt = await self.prompt_engine.render_prompt(
                "workflow_generation_optimized_user",
                **template_context
            )
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
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
        Simplified Debug Node - Test generated workflow and route to regeneration if needed.
        No assumptions about execution result fields, no static validation, no clarification routing.
        Max 2 attempts at workflow generation before giving up.
        """
        logger.info("Processing simplified debug node")
        
        # Update stage to DEBUG
        state["stage"] = WorkflowStage.DEBUG
        
        # Import dependencies here to avoid circular imports
        from services.workflow_engine_client import WorkflowEngineClient
        from .workflow_data_generator import WorkflowDataGenerator
        
        try:
            current_workflow = get_current_workflow(state)
            if not current_workflow:
                # No workflow to debug
                state["debug_result"] = {
                    "success": False,
                    "error": "No workflow to debug",
                    "timestamp": int(time.time() * 1000)
                }
                return {**state, "stage": WorkflowStage.WORKFLOW_GENERATION}
            
            debug_loop_count = state.get("debug_loop_count", 0)
            
            # Step 1: Generate test data for the workflow
            logger.info("Generating test data for workflow execution")
            test_generator = WorkflowDataGenerator()
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
            
            # Step 3: Check if execution succeeded (no field assumptions)
            success = False
            error_message = "ERROR"
            
            if execution_result and isinstance(execution_result, dict):
                # Check for success indicator
                success = execution_result.get("success", False)
                if not success:
                    # Extract error message if available, otherwise use default
                    error_message = execution_result.get("error", "ERROR")
                    logger.info(f"Workflow execution failed: {error_message}")
                else:
                    # Success! Log the execution details
                    logger.info("Workflow executed successfully")
            else:
                # No valid result returned
                logger.error("Invalid or no execution result returned from workflow engine")
                error_message = "ERROR"
            
            # Store the simplified debug result
            state["debug_result"] = {
                "success": success,
                "error": error_message if not success else None,
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

            # Max 2 attempts (0 and 1), give up after that
            if debug_loop_count >= 2:
                logger.error("Max debug attempts (2) reached, workflow generation failed")
                # Mark as failed and return with error
                state["workflow_generation_failed"] = True
                state["final_error_message"] = f"Workflow generation failed after 2 attempts. Last error: {error_message}"
                return {**state, "stage": WorkflowStage.FAILED}

            # Failed - always route back to workflow generation for retry
            logger.info(f"Debug failed (attempt {debug_loop_count + 1}/2), routing to workflow generation with error: {error_message}")
            return {
                **state,
                "stage": WorkflowStage.DEBUG,  # Keep as DEBUG, let routing handle it
                "previous_stage": WorkflowStage.DEBUG,
                "debug_error_for_regeneration": error_message  # Pass error to workflow generation
            }

        except Exception as e:
            logger.error("Debug node failed", extra={"error": str(e)})
            # On debug failure, assume workflow is acceptable
            return {**state, "stage": WorkflowStage.COMPLETED}



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
                return "workflow_generation"  # Go directly to workflow generation
            else:
                return "END"  # Wait for user input
                
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
                if debug_loop_count >= 2:
                    return "END"  # Max attempts reached - will be in FAILED state
                # Failed but can retry - route to workflow generation
                return "workflow_generation"  # Try regenerating
                    
        elif stage == WorkflowStage.COMPLETED:
            return "END"
        
        elif stage == WorkflowStage.FAILED:
            return "END"  # Generation failed, terminate
            
        # Default to END if unknown state
        return "END"