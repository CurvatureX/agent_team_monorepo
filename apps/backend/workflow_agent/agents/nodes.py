"""
LangGraph nodes for optimized Workflow Agent architecture
Implements the 3 core nodes: Clarification, Workflow Generation, and Debug
Simplified architecture with automatic gap handling for better user experience
"""

import json
import logging
import time
import uuid
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from workflow_agent.core.config import settings
from workflow_agent.core.prompt_engine import get_prompt_engine

# Import shared enums for consistent node type handling
try:
    from shared.models.node_enums import NodeType, TriggerSubtype
except ImportError:
    # Fallback if shared models not available
    NodeType = None
    TriggerSubtype = None

from .mcp_tools import MCPToolCaller
from .state import (
    ClarificationContext,
    Conversation,
    WorkflowStage,
    WorkflowState,
    get_current_workflow,
    get_intent_summary,
    get_user_message,
    is_clarification_ready,
)

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
            model=settings.DEFAULT_MODEL_NAME, api_key=settings.OPENAI_API_KEY, temperature=0
        )

    def _setup_llm_with_tools(self):
        """Setup OpenAI LLM with MCP tools bound"""
        llm = ChatOpenAI(
            model=settings.DEFAULT_MODEL_NAME, api_key=settings.OPENAI_API_KEY, temperature=0
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

        state["conversations"].append(
            Conversation(role=role, text=text, timestamp=int(time.time() * 1000))
        )

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
        """Determine the current goal based on the scenario"""
        scenario = self._get_current_scenario(state)
        goals = {
            "Initial Clarification": "Understand the user's workflow requirements thoroughly",
            "Debug Recovery": "Fix the workflow issues found during debugging",
            "Template Customization": "Customize the template workflow to meet user needs",
        }
        return goals.get(scenario, "Create a workflow based on the requirements")

    def _get_conversation_context(self, state: WorkflowState) -> str:
        """Extract conversation context from state"""
        conversations = state.get("conversations", [])
        context_parts = []
        for conv in conversations[-5:]:  # Last 5 messages for context
            context_parts.append(f"{conv.get('role')}: {conv.get('text', '')}")
        return "\n".join(context_parts)

    def _create_fallback_workflow(self, intent_summary: str) -> dict:
        """Create a simple fallback workflow when generation fails"""
        # Use enum values if available, fallback to hardcoded strings
        node_type = NodeType.TRIGGER.value if NodeType else "trigger"
        subtype = TriggerSubtype.MANUAL.value if TriggerSubtype else "manual"

        return {
            "name": "Fallback Workflow",
            "description": f"Basic workflow for: {intent_summary[:100]}",
            "nodes": [
                {
                    "id": str(uuid.uuid4()),
                    "name": "Start",
                    "type": node_type,
                    "subtype": subtype,
                    "properties": {},
                    "inputs": {},
                    "outputs": {"trigger_data": {"type": "object"}},
                    "metadata": {"position": {"x": 100, "y": 100}},
                }
            ],
            "connections": {},
            "settings": {"error_handling": "stop_on_error", "timeout": 300},
            "static_data": {},
            "tags": ["fallback"],
        }

    def should_continue(self, state: WorkflowState) -> str:
        """
        Determine the next step based on current state
        Used by LangGraph for conditional routing in optimized 3-node architecture
        """
        stage = state.get("stage", WorkflowStage.CLARIFICATION)
        logger.info(f"should_continue called with stage: {stage}")

        # Check for FAILED state first
        if stage == WorkflowStage.FAILED:
            logger.info("Workflow generation failed, ending flow")
            return "END"

        # Map stage to next action
        if stage == WorkflowStage.CLARIFICATION:
            # Check if we have pending questions that need user response
            clarification_context = state.get("clarification_context", {})
            pending_questions = clarification_context.get("pending_questions", [])

            # Derive clarification readiness from state
            clarification_ready = is_clarification_ready(state)

            pq_count = len(pending_questions)
            logger.info(f"Clarification routing: pq={pq_count}, ready={clarification_ready}")

            # If we have pending questions, wait for user input
            if pending_questions:
                logger.info("Have pending questions, waiting for user input")
                return "END"
            # Otherwise, check if we're ready to proceed
            elif clarification_ready:
                # In optimized architecture, go directly to workflow generation
                return "workflow_generation"
            else:
                return "END"  # Wait for user input

        elif stage == WorkflowStage.WORKFLOW_GENERATION:
            # After workflow generation, always go to debug
            return "debug"

        elif stage == WorkflowStage.DEBUG:
            # Check debug result
            debug_result = state.get("debug_result", {})
            success = debug_result.get("success", False)
            debug_loop_count = state.get("debug_loop_count", 0)
            max_debug_iterations = settings.DEBUG_MAX_ITERATIONS

            logger.info(f"Debug routing: success={success}, loop_count={debug_loop_count}")

            if success:
                # Workflow validated successfully
                logger.info("Debug successful, workflow complete")
                return "END"
            elif debug_loop_count >= max_debug_iterations:
                # Max iterations reached
                logger.info(f"Max debug iterations ({max_debug_iterations}) reached")
                return "END"
            else:
                # Debug failed, regenerate workflow
                logger.info("Debug failed, regenerating workflow")
                return "workflow_generation"

        # Default case
        logger.warning(f"Unknown stage in should_continue: {stage}")
        return "END"

    async def clarification_node(self, state: WorkflowState) -> WorkflowState:
        """
        Clarification Node - Ask clarifying questions to the user
        Maps prompt output to main branch state structure
        """
        logger.info("Processing clarification node")

        # Get user message
        user_message = get_user_message(state)
        session_id = self._get_session_id(state)
        existing_intent = get_intent_summary(state)
        clarification_context = state.get("clarification_context", {})

        logger.info(
            "Clarification context",
            extra={
                "session_id": session_id,
                "user_message": user_message[:100] if user_message else None,
                "existing_intent": existing_intent[:100] if existing_intent else None,
                "clarification_purpose": clarification_context.get("purpose"),
            },
        )

        # Set stage to CLARIFICATION
        state["stage"] = WorkflowStage.CLARIFICATION

        try:
            # Determine scenario type
            scenario_type = self._get_current_scenario(state)
            conversation_context = self._get_conversation_context(state)

            # Create structured template context
            template_context = {
                "user_message": user_message,
                "existing_intent": existing_intent,
                "conversation_context": conversation_context,
                "current_scenario": scenario_type,
                "goal": self._get_current_goal(state),
                "template_workflow": state.get("template_workflow"),
                "current_workflow": state.get("current_workflow"),
                "debug_result": state.get("debug_result"),
                "purpose": clarification_context.get("purpose", ""),
                "scenario_type": scenario_type,
                "clarification_context": clarification_context,
                "execution_history": state.get("execution_history", []),
            }

            # Use the f2 template system - both system and user prompts
            system_prompt = await self.prompt_engine.render_prompt(
                "clarification_f2_system", **template_context
            )

            user_prompt = await self.prompt_engine.render_prompt(
                "clarification_f2_user", **template_context
            )

            # Debug: Log the actual prompt being sent
            logger.info(
                "Clarification prompt details",
                extra={"user_message": user_message, "prompt_length": len(user_prompt)},
            )

            messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

            # Log the model being used
            logger.info(f"Using model: {settings.DEFAULT_MODEL_NAME}")

            # Try to use response_format, fall back if not supported
            try:
                response = await self.llm.ainvoke(messages, response_format={"type": "json_object"})
                logger.info("Successfully used response_format for JSON output")
            except Exception as format_error:
                if "response_format" in str(format_error):
                    logger.warning(
                        f"Model doesn't support response_format, falling back to standard call: {format_error}"
                    )
                    # Add JSON instruction to the prompt
                    messages.append(HumanMessage(content="Please respond in valid JSON format."))
                    response = await self.llm.ainvoke(messages)
                else:
                    # Re-raise if it's not a response_format issue
                    raise

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
                # Check if clarification is ready (for future routing logic)
                is_ready = clarification_output.get("is_complete", False)  # noqa: F841

                # Map to main branch state structure
                state["intent_summary"] = clarification_output.get("intent_summary", "")

                # Check if user selected an alternative from gap negotiation
                gap_resolution = clarification_output.get("gap_resolution", {})
                if gap_resolution.get("user_selected_alternative", False):
                    # User made a choice
                    alt_idx = gap_resolution.get("selected_index")
                    confidence = gap_resolution.get("confidence")
                    logger.info(f"User selected alternative {alt_idx} with confidence {confidence}")

                # Update clarification context
                existing_purpose = clarification_context.get("purpose", "initial_intent")

                clarification_context = ClarificationContext(
                    purpose=existing_purpose,
                    collected_info={"intent": clarification_output.get("intent_summary", "")},
                    pending_questions=[clarification_output.get("clarification_question", "")]
                    if clarification_output.get("clarification_question")
                    else [],
                    origin=clarification_context.get("origin", "create"),
                )
                state["clarification_context"] = clarification_context

            except json.JSONDecodeError:
                # Fallback to simple format
                state["intent_summary"] = response_text[:200]
                state["clarification_context"] = ClarificationContext(
                    purpose="initial_intent",
                    collected_info={"intent": response_text[:200]},
                    pending_questions=[response_text],
                    origin="create",
                )
                is_ready = False  # noqa: F841

            # Add to conversations
            self._add_conversation(state, "assistant", response_text)

            # Keep stage as CLARIFICATION - routing logic will decide next step
            # Note: clarification readiness is now derived from state, not stored
            # Set previous_stage for next node to know where we came from
            state["previous_stage"] = WorkflowStage.CLARIFICATION
            return {**state, "stage": WorkflowStage.CLARIFICATION}

        except Exception as e:
            import traceback

            error_details = {
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc(),
                "tracking_id": state.get("tracking_id", "unknown"),
                "location": "agents/nodes.py:336",
            }
            logger.error(
                f"Clarification node failed: {str(e)}",
                extra=error_details,
                exc_info=True,  # This will include the full stack trace
            )
            # Also log as separate ERROR for visibility
            logger.error(f"Error details: {error_details}")
            # Store error in debug_result instead of adding undefined field
            state["debug_result"] = {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": int(time.time() * 1000),
            }
            return {**state, "stage": WorkflowStage.CLARIFICATION}

    async def workflow_generation_node(self, state: WorkflowState) -> WorkflowState:
        """
        Optimized Workflow Generation Node - Automatically handles capability gaps
        Uses MCP tools to generate accurate workflows with smart substitutions
        Now also creates the workflow in workflow_engine immediately after generation
        """
        from workflow_agent.services.workflow_engine_client import WorkflowEngineClient

        logger.info("Processing optimized workflow generation node")

        # Set stage to WORKFLOW_GENERATION
        state["stage"] = WorkflowStage.WORKFLOW_GENERATION

        try:
            intent_summary = get_intent_summary(state)
            conversation_context = self._get_conversation_context(state)

            # Check if we're coming from debug with errors or previous generation failures
            debug_error = state.get("debug_error_for_regeneration")
            debug_result = state.get("debug_result") or {}
            creation_error = state.get("workflow_creation_error")  # New field for creation failures
            generation_loop_count = state.get("generation_loop_count", 0)

            # Skip manual MCP fetch - LLM will call it through tools if needed
            # This avoids duplicate API calls since the LLM with tools will
            # call get_node_types anyway when it needs the information
            available_nodes = None

            # Prepare template context with creation error if available
            error_context = None
            if creation_error:
                error_context = f"Previous workflow creation failed with error: {creation_error}. Please fix the issues and regenerate."
            elif debug_error:
                error_context = debug_error
            elif debug_result.get("error") and not debug_result.get("success", True):
                error_context = debug_result.get("error")

            template_context = {
                "intent_summary": intent_summary,
                "conversation_context": conversation_context,
                "available_nodes": available_nodes,
                "current_workflow": state.get("current_workflow"),
                "debug_result": error_context,
            }

            # Use the original f1 template system - the working approach
            system_prompt = await self.prompt_engine.render_prompt(
                "workflow_gen_f1", **template_context
            )

            # Create user prompt for workflow generation - optimized for efficiency
            user_prompt_content = f"""Create a workflow for: {intent_summary}

Instructions:
1. Call get_node_types() to discover available nodes
2. Call get_node_details() with a SINGLE call containing ALL required nodes as an array
3. Generate the complete JSON workflow (no explanations, just JSON)"""

            # Add error context to prompt if we're regenerating due to creation failure
            if error_context:
                user_prompt_content += f"\n\nIMPORTANT: {error_context}"

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt_content),
            ]

            # Generate workflow using OpenAI with multi-turn tool calling (like the test file)
            workflow_json = await self._generate_with_multi_turn_tools(messages)

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
                    logger.info(
                        "Successfully generated workflow using MCP tools, workflow: %s", workflow
                    )

                except json.JSONDecodeError as e:
                    logger.error(
                        f"Failed to parse workflow JSON: {e}, response was: {workflow_json[:500]}"
                    )
                    # Use fallback workflow on parse error
                    workflow = self._create_fallback_workflow(intent_summary)

            # NEW: Create workflow in workflow_engine immediately after generation
            logger.info("Creating workflow in workflow_engine")
            engine_client = WorkflowEngineClient()
            user_id = state.get("user_id", "test_user")
            session_id = state.get("session_id")

            # Pass session_id to the workflow creation
            creation_result = await engine_client.create_workflow(workflow, user_id, session_id)

            if creation_result.get("success", True) and creation_result.get("workflow", {}).get(
                "id"
            ):
                # Creation successful - store workflow and workflow_id
                workflow_id = creation_result["workflow"]["id"]
                state["current_workflow"] = workflow
                state["workflow_id"] = workflow_id
                state["workflow_creation_result"] = creation_result

                # Clear any previous creation errors
                if "workflow_creation_error" in state:
                    del state["workflow_creation_error"]

                logger.info(f"Workflow created successfully with ID: {workflow_id}")
                # Keep stage as WORKFLOW_GENERATION so routing goes to debug node
                return {**state, "stage": WorkflowStage.WORKFLOW_GENERATION}

            else:
                # Creation failed - check if we should retry generation
                creation_error = creation_result.get("error", "Unknown creation error")
                max_generation_retries = getattr(settings, "WORKFLOW_GENERATION_MAX_RETRIES", 3)

                logger.error(f"Workflow creation failed: {creation_error}")

                # Check if it's a session_id error - if so, don't retry as it won't help
                if "session_id" in creation_error or "ForeignKeyViolation" in creation_error:
                    logger.error("Session ID error detected, skipping retries")
                    state["workflow_creation_error"] = creation_error
                    state["current_workflow"] = workflow
                    # Mark as FAILED to end the flow
                    state["stage"] = WorkflowStage.FAILED
                    # Add failure message to conversations
                    self._add_conversation(
                        state,
                        "assistant",
                        f"I've generated the workflow but couldn't save it due to a session error. Here's the workflow configuration:\n\n```json\n{json.dumps(workflow, indent=2)}\n```",
                    )
                    return state

                if generation_loop_count < max_generation_retries:
                    # Store error for regeneration and increment loop count
                    state["workflow_creation_error"] = creation_error
                    state["generation_loop_count"] = generation_loop_count + 1

                    logger.info(
                        f"Retrying workflow generation (attempt {generation_loop_count + 1}/{max_generation_retries})"
                    )
                    # Recursively call this node to retry
                    return await self.workflow_generation_node(state)
                else:
                    # Max retries reached, mark as FAILED
                    state["workflow_creation_error"] = creation_error
                    state["current_workflow"] = workflow
                    state["stage"] = WorkflowStage.FAILED
                    logger.error(
                        f"Max workflow generation retries ({max_generation_retries}) reached"
                    )
                    # Add failure message to conversations
                    self._add_conversation(
                        state,
                        "assistant",
                        f"I've generated the workflow but encountered an error saving it after {max_generation_retries} attempts. Here's the workflow configuration:\n\n```json\n{json.dumps(workflow, indent=2)}\n```\n\nError: {creation_error}",
                    )
                    return state

        except Exception as e:
            import traceback

            error_details = {
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc(),
                "tracking_id": state.get("tracking_id", "unknown"),
                "location": "agents/nodes.py:workflow_generation_node",
            }
            logger.error(
                f"Workflow generation node failed: {str(e)}", extra=error_details, exc_info=True
            )
            logger.error(f"Error details: {error_details}")
            return {
                **state,
                "stage": WorkflowStage.WORKFLOW_GENERATION,
            }

    async def _generate_with_multi_turn_tools(self, messages: List) -> str:
        """
        Multi-turn workflow generation following the working pattern from test file.

        This matches the successful approach:
        1. First call with tools - LLM uses get_node_types
        2. Process tool responses
        3. Continue conversation to get node_details
        4. Final generation with complete JSON output
        """
        try:
            # Convert LangChain messages to OpenAI format
            openai_messages = []
            for msg in messages:
                if hasattr(msg, "content"):
                    role = "system" if type(msg).__name__ == "SystemMessage" else "user"
                    openai_messages.append({"role": role, "content": msg.content})

            logger.info("Starting multi-turn workflow generation with OpenAI")

            # Step 1: First call - let LLM call get_node_types
            # Use the LLM with tools bound (not passing tools parameter directly)
            response = await self.llm_with_tools.ainvoke(messages)

            # Convert back to openai format for processing
            if hasattr(response, "content") and response.content:
                openai_messages.append({"role": "assistant", "content": response.content})

            # Process tool calls if any
            if hasattr(response, "tool_calls") and response.tool_calls:
                logger.info(f"Processing {len(response.tool_calls)} tool calls from first response")

                # Add tool call responses
                for tool_call in response.tool_calls:
                    tool_name = getattr(tool_call, "name", tool_call.get("name", ""))
                    tool_args = getattr(tool_call, "args", tool_call.get("args", {}))

                    logger.info(f"Calling tool: {tool_name}")
                    result = await self.mcp_client.call_tool(tool_name, tool_args)

                    # Format as string for conversation
                    result_str = (
                        json.dumps(result, indent=2) if isinstance(result, dict) else str(result)
                    )

                    openai_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": getattr(tool_call, "id", str(uuid.uuid4())),
                            "content": result_str,
                        }
                    )

                # Step 2: Continue conversation to get node_details and final JSON
                openai_messages.append(
                    {
                        "role": "user",
                        "content": "Now call get_node_details with a SINGLE call containing ALL the nodes you need (pass them as an array in the 'nodes' parameter). Focus only on the specific nodes required for this workflow - don't fetch details for unnecessary nodes. After getting the details, output ONLY the complete JSON workflow configuration.",
                    }
                )

                # Convert back to LangChain format
                langchain_messages = []
                for msg in openai_messages:
                    if msg["role"] == "system":
                        langchain_messages.append(SystemMessage(content=msg["content"]))
                    elif msg["role"] == "user":
                        langchain_messages.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        langchain_messages.append(
                            SystemMessage(content=f"Assistant: {msg['content']}")
                        )
                    elif msg["role"] == "tool":
                        langchain_messages.append(
                            HumanMessage(content=f"Tool result: {msg['content']}")
                        )

                # Step 3: Final generation call
                final_response = await self.llm_with_tools.ainvoke(langchain_messages)

                # Handle any additional tool calls for node_details (with limit to prevent infinite loops)
                MAX_ADDITIONAL_CALLS = 5  # Prevent runaway tool calling
                if hasattr(final_response, "tool_calls") and final_response.tool_calls:
                    num_calls = len(final_response.tool_calls)
                    if num_calls > MAX_ADDITIONAL_CALLS:
                        logger.warning(
                            f"Too many tool calls ({num_calls}), limiting to {MAX_ADDITIONAL_CALLS}"
                        )
                        final_response.tool_calls = final_response.tool_calls[:MAX_ADDITIONAL_CALLS]

                    logger.info(
                        f"Processing {len(final_response.tool_calls)} additional tool calls"
                    )

                    # Process additional tool calls
                    for tool_call in final_response.tool_calls:
                        tool_name = getattr(tool_call, "name", tool_call.get("name", ""))
                        tool_args = getattr(tool_call, "args", tool_call.get("args", {}))

                        logger.info(
                            f"Calling additional tool: {tool_name} with args: {json.dumps(tool_args, indent=2) if tool_args else '{}'}"
                        )
                        result = await self.mcp_client.call_tool(tool_name, tool_args)

                        result_str = (
                            json.dumps(result, indent=2)
                            if isinstance(result, dict)
                            else str(result)
                        )
                        langchain_messages.append(
                            HumanMessage(content=f"Tool result for {tool_name}: {result_str}")
                        )

                    # Final call to get the JSON workflow with clearer instructions
                    langchain_messages.append(
                        HumanMessage(
                            content="You now have all the node details. Output ONLY the complete JSON workflow configuration. Start with { and end with }. No explanations, no markdown, just pure JSON."
                        )
                    )

                    final_json_response = await self.llm_with_tools.ainvoke(langchain_messages)
                    return (
                        str(final_json_response.content)
                        if hasattr(final_json_response, "content")
                        else ""
                    )

                # Return the final response content
                return str(final_response.content) if hasattr(final_response, "content") else ""

            # No tool calls in first response - return content directly
            return str(response.content) if hasattr(response, "content") else ""

        except Exception as e:
            logger.error(f"Multi-turn tool generation failed: {e}", exc_info=True)
            return ""

    async def debug_node(self, state: WorkflowState) -> WorkflowState:
        """
        Debug Node - Validate workflow using workflow_engine with real execution test
        Now only handles test data generation and execution since workflow is already created
        Returns debug result with either success or error message
        """
        from workflow_agent.agents.workflow_data_generator import WorkflowDataGenerator
        from workflow_agent.services.workflow_engine_client import WorkflowEngineClient

        logger.info("Processing debug node with workflow_engine validation")

        # Set stage to DEBUG
        state["stage"] = WorkflowStage.DEBUG

        try:
            current_workflow = get_current_workflow(state)
            workflow_id = state.get("workflow_id")

            # Check if we have workflow creation error from previous workflow generation
            creation_error = state.get("workflow_creation_error")
            if creation_error:
                logger.warning(f"Workflow creation failed previously: {creation_error}")
                state["debug_result"] = {
                    "success": False,
                    "error": f"Workflow creation failed: {creation_error}",
                    "timestamp": int(time.time() * 1000),
                }
                # Keep stage as DEBUG - the routing logic will handle this
                return {**state, "stage": WorkflowStage.DEBUG}

            if not current_workflow:
                logger.warning("No workflow to debug")
                state["debug_result"] = {
                    "success": False,
                    "error": "No workflow to debug",
                    "timestamp": int(time.time() * 1000),
                }
                return {**state, "stage": WorkflowStage.DEBUG}

            if not workflow_id:
                logger.warning(
                    "No workflow_id available, workflow may not have been created successfully"
                )
                state["debug_result"] = {
                    "success": False,
                    "error": "No workflow_id available - workflow creation may have failed",
                    "timestamp": int(time.time() * 1000),
                }
                return {**state, "stage": WorkflowStage.DEBUG}

            debug_loop_count = state.get("debug_loop_count", 0)

            # Step 1: Generate test data for the workflow
            logger.info("Generating test data for workflow execution")
            test_generator = WorkflowDataGenerator()
            test_data = await test_generator.generate_test_data(current_workflow)

            # Step 2: Execute the already created workflow using workflow_id
            logger.info(f"Executing existing workflow in workflow_engine (ID: {workflow_id})")
            engine_client = WorkflowEngineClient()

            # Get user_id from state or use default
            user_id = state.get("user_id", "test_user")

            # Execute the workflow directly using workflow_id (no creation needed)
            execution_result = await engine_client.execute_workflow(
                workflow_id=workflow_id, trigger_data=test_data, user_id=user_id
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
                    execution_id = execution_result.get("execution_id")
                    logger.info(f"Workflow executed successfully (execution_id: {execution_id})")
            else:
                # No valid result returned
                logger.error("Invalid or no execution result returned from workflow engine")
                error_message = "ERROR"

            # Store the simplified debug result
            state["debug_result"] = {
                "success": success,
                "error": error_message if not success else None,
                "timestamp": int(time.time() * 1000),
            }

            # Update debug loop count
            state["debug_loop_count"] = debug_loop_count + 1

            # Keep stage as DEBUG - routing logic will decide based on success
            return {**state, "stage": WorkflowStage.DEBUG}

        except Exception as e:
            import traceback

            error_details = {
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc(),
                "tracking_id": state.get("tracking_id", "unknown"),
                "location": "agents/nodes.py:debug_node",
            }
            logger.error(f"Debug node failed: {str(e)}", extra=error_details, exc_info=True)
            logger.error(f"Error details: {error_details}")
            state["debug_result"] = {
                "success": False,
                "error": f"Debug validation failed: {str(e)}",
                "timestamp": int(time.time() * 1000),
            }
            return {**state, "stage": WorkflowStage.DEBUG}
