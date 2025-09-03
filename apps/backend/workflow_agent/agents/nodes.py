"""
LangGraph nodes for optimized Workflow Agent architecture
Implements the 2 core nodes: Clarification and Workflow Generation
Simplified architecture with automatic gap handling for better user experience
"""

import json
import logging
import time
import uuid
from typing import List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from workflow_agent.core.config import settings
from workflow_agent.core.prompt_engine import get_prompt_engine

from .mcp_tools import MCPToolCaller
from .state import (
    WorkflowStage,
    WorkflowState,
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
        # Store MCP node specs for type reference
        self.node_specs_cache = {}

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

    async def load_prompt_template(self, template_name: str, **context) -> str:
        """Load and render a prompt template using the prompt engine"""
        return await self.prompt_engine.render_prompt(template_name, **context)

    async def _repair_json(self, json_str: str) -> str:
        """Use GEMINI to repair malformed JSON from gpt-5-mini"""
        import json
        import os

        logger.info(f"Attempting to repair JSON using GEMINI, original length: {len(json_str)}")

        # First try to parse the JSON as-is
        try:
            parsed = json.loads(json_str)
            logger.info("JSON is already valid, no repair needed")
            return json.dumps(parsed, indent=2)
        except json.JSONDecodeError as e:
            logger.info(f"JSON needs repair: {e}")

        try:
            # Initialize GEMINI model for JSON repair using enum
            import google.generativeai as genai

            from shared.models.node_enums import GoogleGeminiModel

            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            model = genai.GenerativeModel(GoogleGeminiModel.GEMINI_2_5_FLASH_LITE.value)

            # Create repair prompt with explicit JSON formatting request
            repair_prompt = f"""You are a JSON repair expert. Fix the malformed JSON below and return ONLY the valid JSON object.

Common issues to fix:
- Trailing backslashes in string values (e.g., "value\\" should be "value")
- Invalid escape sequences
- Control characters
- Missing quotes around property names
- Trailing commas
- Unclosed brackets or braces

CRITICAL: Return ONLY the valid JSON object with no markdown, no explanations, no code blocks:

{json_str}"""

            # Get GEMINI to repair the JSON
            response = model.generate_content(
                repair_prompt,
                generation_config={
                    "temperature": 0,
                    "max_output_tokens": 8192,
                },
            )

            repaired_json = response.text.strip() if response.text else ""

            # Test the repaired JSON
            parsed = json.loads(repaired_json)
            logger.info("GEMINI JSON repair successful")
            return json.dumps(parsed, indent=2)

        except Exception as e:
            logger.error(f"GEMINI JSON repair failed: {e}")

            # Fallback to basic structure extraction
            logger.info("Attempting basic structure extraction as fallback")
            try:
                import re

                name_match = re.search(r'"name":\s*"([^"]*)"', json_str)
                desc_match = re.search(r'"description":\s*"([^"]*)"', json_str)

                if name_match and desc_match:
                    fallback_json = {
                        "name": name_match.group(1),
                        "description": desc_match.group(1),
                        "nodes": [],
                        "connections": [],
                    }
                    json_str = json.dumps(fallback_json, indent=2)
                    logger.info("Applied fallback JSON structure")
                    return json_str

            except Exception as fallback_error:
                logger.error(f"Even fallback repair failed: {fallback_error}")

            # Return a minimal valid workflow as last resort
            minimal_workflow = {
                "name": "Generated Workflow",
                "description": "Workflow could not be parsed",
                "nodes": [],
                "connections": {},
            }
            return json.dumps(minimal_workflow, indent=2)

    def _add_conversation(self, state: WorkflowState, role: str, text: str) -> None:
        """Add a new message to conversations"""
        state["conversations"].append(
            {"role": role, "text": text, "timestamp": int(time.time() * 1000)}
        )

    def _get_conversation_context(self, state: WorkflowState) -> str:
        """Extract conversation context from state with proper capping and formatting"""
        conversations = state.get("conversations", [])

        # Define maximum context based on the 2-node architecture
        # We want enough context for understanding but not overwhelming the LLM
        MAX_CONVERSATION_PAIRS = 10  # Maximum of 10 user-assistant pairs
        MAX_TEXT_LENGTH = 500  # Truncate long messages to avoid token overflow

        context_parts = []
        conversation_pairs = []

        # Group conversations into user-assistant pairs for better context
        current_pair = {}
        for conv in reversed(conversations):  # Start from most recent
            role = conv.get("role", "")
            text = conv.get("text", "")

            # Truncate long messages
            if len(text) > MAX_TEXT_LENGTH:
                text = text[:MAX_TEXT_LENGTH] + "..."

            if role == "user":
                if current_pair.get("assistant"):
                    # Complete pair found, add it
                    conversation_pairs.append(current_pair)
                    current_pair = {}
                current_pair["user"] = text
            elif role == "assistant":
                current_pair["assistant"] = text
                if current_pair.get("user"):
                    # Complete pair found, add it
                    conversation_pairs.append(current_pair)
                    current_pair = {}

        # Add any incomplete pair
        if current_pair:
            conversation_pairs.append(current_pair)

        # Take only the most recent conversation pairs (up to MAX_CONVERSATION_PAIRS)
        conversation_pairs = conversation_pairs[:MAX_CONVERSATION_PAIRS]

        # Reverse to get chronological order (oldest to newest)
        conversation_pairs.reverse()

        # Format the conversation history for the prompt
        for pair in conversation_pairs:
            if pair.get("user"):
                context_parts.append(f"User: {pair['user']}")
            if pair.get("assistant"):
                context_parts.append(f"Assistant: {pair['assistant']}")

        return "\n".join(context_parts)

    def _optimize_node_parameters(self, node: dict, node_spec: dict = None) -> dict:
        """
        优化节点参数：只保留必需参数和用户指定的参数
        注意：模板变量保持原样，不进行类型转换

        Args:
            node: 节点数据
            node_spec: 节点规格（从MCP获取的详细信息）

        Returns:
            优化后的节点数据
        """
        if not node.get("parameters"):
            return node

        optimized_params = {}
        current_params = node["parameters"]

        # 如果有节点规格，使用它来确定必需参数
        if node_spec and "parameters" in node_spec:
            for param_spec in node_spec["parameters"]:
                param_name = param_spec["name"]
                param_required = param_spec.get("required", False)
                param_desc = param_spec.get("description", "")

                # 检查当前参数中是否有这个参数
                if param_name in current_params:
                    param_value = current_params[param_name]

                    # 必需参数或有明确值的参数
                    if param_required or (
                        param_value and param_value != param_spec.get("default_value")
                    ):
                        # 保留参数值，如果已经是模板变量格式则保持不变
                        optimized_params[param_name] = param_value
        else:
            # 没有规格信息时，进行基本优化
            for param_name, param_value in current_params.items():
                # 跳过真正的空值
                if (
                    param_value is None
                    or param_value == ""
                    or (isinstance(param_value, list) and len(param_value) == 0)
                    or (isinstance(param_value, dict) and len(param_value) == 0)
                ):
                    continue

                # 保留非空参数
                optimized_params[param_name] = param_value

        node["parameters"] = optimized_params
        return node

    def _fix_workflow_parameters(self, workflow: dict) -> dict:
        """
        修正工作流中所有节点的参数，使用 MCP 提供的 ParameterType 信息。
        这只是兜底逻辑，LLM 应该直接根据 MCP ParameterType 生成正确的 mock values。

        Args:
            workflow: 完整的工作流数据

        Returns:
            修正后的工作流数据
        """
        if "nodes" not in workflow:
            return workflow

        for node in workflow["nodes"]:
            self._fix_node_parameters(node)

        return workflow

    def _fix_node_parameters(self, node: dict) -> dict:
        """
        修正单个节点的参数，使用 MCP 节点规格中的 ParameterType 信息。

        重要：LLM 应该直接根据 MCP 返回的 ParameterType 生成正确的 mock values:
        - type: "integer" -> 生成 123, 456 等整数
        - type: "boolean" -> 生成 true/false
        - type: "string" -> 生成 "example-value" 等字符串
        - type: "float" -> 生成 0.7, 1.5 等浮点数

        Args:
            node: 节点数据

        Returns:
            修正后的节点数据
        """
        if not node.get("parameters"):
            return node

        # Get node spec from cache
        node_key = f"{node.get('type')}:{node.get('subtype')}"
        node_spec = self.node_specs_cache.get(node_key)

        parameters = node["parameters"]

        for param_name, param_value in list(parameters.items()):
            # Get parameter type from MCP spec if available
            param_type = None
            param_required = False
            if node_spec and "parameters" in node_spec:
                for param_spec in node_spec["parameters"]:
                    if param_spec.get("name") == param_name:
                        param_type = param_spec.get("type", "string")
                        param_required = param_spec.get("required", False)
                        break

            # Handle reference objects using MCP-provided ParameterType
            if isinstance(param_value, dict) and ("$ref" in param_value or "$expr" in param_value):
                logger.warning(f"LLM generated reference object for '{param_name}': {param_value}")
                logger.warning(
                    f"LLM should have used MCP ParameterType '{param_type}' to generate a proper mock value!"
                )

                if param_type:
                    logger.info(
                        f"Using MCP-provided ParameterType '{param_type}' for parameter '{param_name}'"
                    )
                    parameters[param_name] = self._generate_proper_value_for_type(param_type)
                else:
                    # Fallback only if MCP type not available
                    logger.warning(f"No MCP type info for '{param_name}', using fallback")
                    parameters[param_name] = "example-value"

            # Handle template variables (another form of placeholder)
            elif isinstance(param_value, str):
                is_placeholder = (
                    ("{{" in param_value and "}}" in param_value)
                    or ("${" in param_value and "}" in param_value)
                    or ("<" in param_value and ">" in param_value)
                )

                if is_placeholder:
                    logger.warning(f"LLM generated placeholder for '{param_name}': {param_value}")
                    if param_type:
                        logger.info(f"Fixing with MCP ParameterType '{param_type}'")
                        parameters[param_name] = self._generate_proper_value_for_type(param_type)
                    else:
                        # Fallback
                        logger.warning(f"No MCP type for '{param_name}', using fallback")
                        parameters[param_name] = "example-value"

            # Handle invalid zeros for ID fields
            elif isinstance(param_value, int) and param_value == 0:
                if any(keyword in param_name.lower() for keyword in ["number", "id", "count"]):
                    logger.warning(f"LLM generated invalid zero for '{param_name}'")
                    import random

                    parameters[param_name] = random.randint(100, 99999999)

        return node

    def _generate_proper_value_for_type(self, param_type: str) -> object:
        """Generate a proper value based on MCP ParameterType without hardcoding"""
        import random

        if param_type == "integer":
            # Generate a reasonable integer without hardcoding specific values
            return random.randint(100, 99999999)
        elif param_type == "boolean":
            return random.choice([True, False])
        elif param_type == "float":
            return round(random.uniform(0.1, 10.0), 2)
        elif param_type == "string":
            # Generate a generic example string
            return f"example-value-{random.randint(1000, 9999)}"
        elif param_type == "json":
            return {}
        else:
            # Default to string for unknown types
            return "example-value"

    def _normalize_workflow_structure(self, workflow: dict) -> dict:
        """
        Minimal normalization - only fix critical issues that break workflow creation
        Most fields should be correctly generated by LLM with improved prompt
        """
        # Handle workflow_meta if LLM uses old format
        if "workflow_meta" in workflow and not workflow.get("name"):
            workflow["name"] = workflow["workflow_meta"].get("name", "Automated Workflow")
            workflow["description"] = workflow["workflow_meta"].get("description", "")

        # Only add absolutely critical missing fields for nodes
        if "nodes" in workflow:
            for i, node in enumerate(workflow["nodes"]):
                # Ensure node has a name (required field)
                if "name" not in node or not node["name"]:
                    # Generate name from node type and ID
                    node_id = node.get("id", f"node_{i}")
                    node_type = node.get("type", "unknown")
                    node_subtype = node.get("subtype", "")
                    if node_subtype:
                        node["name"] = f"{node_type}_{node_subtype}_{node_id}".replace(
                            "_", "-"
                        ).lower()
                    else:
                        node["name"] = f"{node_type}_{node_id}".replace("_", "-").lower()

                # Optimize node parameters (remove unnecessary params)
                # Note: Parameter fixing is now done at workflow level after all nodes are normalized
                node = self._optimize_node_parameters(node)

                # Only add position if completely missing (required field)
                if "position" not in node:
                    node["position"] = {"x": 100.0 + i * 200.0, "y": 100.0}

                # These fields have defaults in the backend, only add if completely missing
                essential_defaults = {
                    "disabled": False,
                    "on_error": "continue",
                    "credentials": {},
                    "notes": {},
                    "webhooks": [],
                }

                for field, default in essential_defaults.items():
                    if field not in node:
                        node[field] = default

        # Fix connections format if it's a list
        if "connections" in workflow and isinstance(workflow["connections"], list):
            # Convert list format to dict format
            connections_dict = {}
            for conn in workflow["connections"]:
                if isinstance(conn, dict):
                    # Handle format 1: {"from": {"node_id": "x", "port": "y"}, "to": {...}}
                    if isinstance(conn.get("from"), dict) and isinstance(conn.get("to"), dict):
                        from_node = conn["from"].get("node_id", "")
                        to_node = conn["to"].get("node_id", "")
                        from_port = conn["from"].get("port", "main")
                        to_port = conn["to"].get("port", "main")
                    # Handle format 2: {"from": "x", "from_port": "y", "to": "z", "to_port": "w"}
                    elif "from" in conn and "to" in conn and isinstance(conn["from"], str):
                        from_node = conn.get("from", "")
                        to_node = conn.get("to", "")
                        from_port = conn.get("from_port", "main")
                        to_port = conn.get("to_port", "main")
                    else:
                        continue

                    # Create the proper nested structure with connection_types
                    if from_node not in connections_dict:
                        connections_dict[from_node] = {"connection_types": {}}
                    if from_port not in connections_dict[from_node]["connection_types"]:
                        connections_dict[from_node]["connection_types"][from_port] = {
                            "connections": []
                        }

                    connections_dict[from_node]["connection_types"][from_port][
                        "connections"
                    ].append({"node": to_node, "type": to_port, "index": 0})

            workflow["connections"] = connections_dict
        elif "connections" not in workflow:
            workflow["connections"] = {}

        # Add missing top-level fields
        if "settings" not in workflow:
            workflow["settings"] = {
                "timezone": {"name": "UTC"},
                "save_execution_progress": True,
                "save_manual_executions": True,
                "timeout": 3600,
                "error_policy": "continue",
                "caller_policy": "workflow",
            }

        if "static_data" not in workflow:
            workflow["static_data"] = {}

        if "pin_data" not in workflow:
            workflow["pin_data"] = {}

        if "tags" not in workflow:
            workflow["tags"] = []

        if "active" not in workflow:
            workflow["active"] = True

        if "version" not in workflow:
            workflow["version"] = "1.0"

        # Generate unique ID if not present
        if "id" not in workflow:
            import re

            # Create ID from name
            name = workflow.get("name", "workflow")
            workflow["id"] = re.sub(r"[^a-z0-9-]", "-", name.lower())[:50]

        return workflow

    def _create_fallback_workflow(self, intent_summary: str) -> dict:
        """Create a simple fallback workflow when generation fails"""
        return {
            "name": "Fallback Workflow",
            "description": f"Basic workflow for: {intent_summary[:100]}",
            "nodes": [
                {
                    "id": str(uuid.uuid4()),
                    "name": "manual-trigger",
                    "type": "TRIGGER",
                    "subtype": "MANUAL",
                    "parameters": {},
                    "position": {"x": 100, "y": 100},
                    "disabled": False,
                    "on_error": "continue",
                    "credentials": {},
                    "notes": {},
                    "webhooks": [],
                }
            ],
            "connections": {},
            "settings": {
                "timezone": {"name": "UTC"},
                "save_execution_progress": True,
                "save_manual_executions": True,
                "timeout": 3600,
                "error_policy": "continue",
                "caller_policy": "workflow",
            },
            "static_data": {},
            "pin_data": {},
            "tags": ["fallback"],
            "active": True,
            "version": "1.0",
            "id": "fallback-workflow",
        }

    def should_continue(self, state: WorkflowState) -> str:
        """
        Determine the next step based on current state
        Used by LangGraph for conditional routing in optimized 2-node architecture
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
                # In 2-node architecture, go directly to workflow generation
                return "workflow_generation"
            else:
                return "END"  # Wait for user input

        elif stage == WorkflowStage.WORKFLOW_GENERATION:
            # After workflow generation, workflow is complete - end the flow
            logger.info("Workflow generation complete, ending flow")
            return "END"

        # Default case
        logger.warning(f"Unknown stage in should_continue: {stage}")
        return "END"

    async def clarification_node(self, state: WorkflowState) -> WorkflowState:
        """
        Clarification Node - Optimized for 2-node architecture
        Focuses on understanding user intent quickly with minimal questions
        """
        logger.info("Processing clarification node")

        # Get core state data
        user_message = get_user_message(state)
        existing_intent = get_intent_summary(state)
        conversation_history = self._get_conversation_context(state)

        logger.info(
            "Clarification context",
            extra={
                "user_message": user_message[:100] if user_message else None,
            },
        )

        state["stage"] = WorkflowStage.CLARIFICATION

        try:
            # Simplified template context - let LLM decide when to complete
            template_context = {
                "user_message": user_message,
                "existing_intent": existing_intent,
                "conversation_history": conversation_history,
            }

            # Add source workflow if in edit/copy mode
            if "source_workflow" in state and state["source_workflow"]:
                template_context["source_workflow"] = json.dumps(state["source_workflow"], indent=2)
                logger.info(
                    f"Including source workflow in clarification context for edit/copy mode"
                )

            # Add workflow context if present
            if "workflow_context" in state and state["workflow_context"]:
                template_context["workflow_mode"] = state["workflow_context"].get(
                    "origin", "create"
                )
                logger.info(f"Workflow mode: {template_context['workflow_mode']}")

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

                # Map to main branch state structure
                state["intent_summary"] = clarification_output.get("intent_summary", "")

                # Update clarification context with simplified structure
                state["clarification_context"] = {
                    "pending_questions": [clarification_output.get("clarification_question", "")]
                    if clarification_output.get("clarification_question")
                    else [],
                }

            except json.JSONDecodeError:
                # Fallback to simple format
                state["intent_summary"] = response_text[:200]
                state["clarification_context"] = {
                    "pending_questions": [response_text],
                }

            # Add to conversations - but store the structured output, not raw JSON
            if isinstance(clarification_output, dict):
                # Create a user-friendly message from the structured output
                assistant_message = ""
                if clarification_output.get("clarification_question"):
                    assistant_message = clarification_output["clarification_question"]
                elif clarification_output.get("is_complete"):
                    # When clarification is complete, inform user we're proceeding to generate workflow
                    intent = clarification_output.get("intent_summary", "your workflow request")
                    assistant_message = f"Perfect! I understand your requirements: {intent}\n\nI'll now generate the workflow for you."
                else:
                    assistant_message = clarification_output.get(
                        "intent_summary", "Processing your request"
                    )

                self._add_conversation(state, "assistant", assistant_message)
            else:
                # Fallback to raw response if not structured
                self._add_conversation(state, "assistant", response_text)

            # Return updated state
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
            logger.error(f"Error details: {error_details}")
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

            # Check if we're coming from previous generation failures
            creation_error = state.get("workflow_creation_error")  # Field for creation failures
            generation_loop_count = state.get("generation_loop_count", 0)

            # Prepare template context with creation error if available
            error_context = None
            if creation_error:
                error_context = f"Previous workflow creation failed with error: {creation_error}. Please fix the issues and regenerate."

            template_context = {
                "intent_summary": intent_summary,
                "conversation_context": conversation_context,
                "current_workflow": state.get("current_workflow"),
                "creation_error": error_context,
            }

            # Add source workflow and mode for edit/copy operations
            if "source_workflow" in state and state["source_workflow"]:
                template_context["source_workflow"] = json.dumps(state["source_workflow"], indent=2)
                logger.info(f"Including source workflow in generation context for edit/copy mode")

            if "workflow_context" in state and state["workflow_context"]:
                template_context["workflow_mode"] = state["workflow_context"].get(
                    "origin", "create"
                )
                logger.info(f"Workflow generation mode: {template_context['workflow_mode']}")

            # Use the original f1 template system - the working approach
            system_prompt = await self.prompt_engine.render_prompt(
                "workflow_gen_simplified", **template_context
            )

            # Use template for user prompt - proper approach
            user_prompt_content = await self.prompt_engine.render_prompt(
                "workflow_generation_user", **template_context
            )

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt_content),
            ]

            # Generate workflow using natural MCP tool calling (with state for progress tracking)
            workflow_json = await self._generate_with_natural_tools(messages, state)

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

                    # Attempt to repair common JSON issues
                    workflow_json = await self._repair_json(workflow_json.strip())
                    workflow = json.loads(workflow_json)

                    # Post-process the workflow to add missing required fields
                    workflow = self._normalize_workflow_structure(workflow)

                    # Fix parameters using MCP-provided types (only as fallback)
                    workflow = self._fix_workflow_parameters(workflow)

                    # Iteratively validate and improve workflow
                    workflow = await self._iterative_workflow_validation(
                        workflow, intent_summary, state, messages
                    )

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

            # Always create a new workflow, even in edit mode
            # This allows users to test edits without overwriting the original
            workflow_context = state.get("workflow_context", {})
            workflow_mode = workflow_context.get("origin", "create")

            logger.info(f"Creating new workflow in workflow_engine (mode: {workflow_mode})")
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

                # Add detailed completion message to conversations
                workflow_name = workflow.get("name", "Workflow")
                workflow_description = workflow.get("description", "")
                node_count = len(workflow.get("nodes", []))

                # Check if we're in edit mode
                workflow_context = state.get("workflow_context", {})
                workflow_mode = workflow_context.get("origin", "create")
                source_workflow_id = workflow_context.get("source_workflow_id")

                if workflow_mode == "edit":
                    completion_message = f"""✅ **New Workflow Created from Edit!**

I've successfully created a new workflow based on your modifications:
- **Name**: {workflow_name}
- **New ID**: {workflow_id}
- **Original ID**: {source_workflow_id}
- **Nodes**: {node_count} nodes configured
{f'- **Description**: {workflow_description}' if workflow_description else ''}

The new workflow has been saved with your requested changes. The original workflow remains unchanged.

You can now:
1. Test the new workflow with sample data
2. Schedule it to run automatically
3. Make further modifications if needed

Would you like to test this updated workflow or make additional changes?"""
                else:
                    completion_message = f"""✅ **Workflow Created Successfully!**

I've successfully created your workflow:
- **Name**: {workflow_name}
- **ID**: {workflow_id}
- **Nodes**: {node_count} nodes configured
{f'- **Description**: {workflow_description}' if workflow_description else ''}

The workflow has been saved and is ready for execution. You can now:
1. Test the workflow with sample data
2. Schedule it to run automatically
3. Modify it as needed

Would you like to make any adjustments or shall we proceed with testing?"""

                self._add_conversation(state, "assistant", completion_message)

                # In 2-node architecture, workflow generation completion means END
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

    async def _generate_with_natural_tools(
        self, messages: List, state: Optional[dict] = None
    ) -> str:
        """
        Natural workflow generation - let LLM decide when and how to use MCP tools.
        Still emphasizes following MCP type specifications but doesn't force specific calling patterns.
        Includes progress tracking for long-running operations.
        """
        try:
            logger.info("Starting natural workflow generation with MCP tools")

            # Track timing for diagnostics
            start_time = time.time()

            # Update state to indicate we're generating
            if state:
                state["generation_status"] = "Starting LLM workflow generation..."
                state["generation_progress"] = 0

            # Let LLM use tools naturally - no forced multi-turn pattern
            logger.info("Invoking LLM for initial workflow generation")
            response = await self.llm_with_tools.ainvoke(messages)

            elapsed = time.time() - start_time
            logger.info(f"Initial LLM response received after {elapsed:.2f} seconds")

            # Process any tool calls the LLM decided to make
            current_messages = list(messages)
            max_iterations = 5  # Prevent infinite loops
            iteration = 0
            tool_call_history = []  # Track what tools have been called to avoid duplicates

            while (
                hasattr(response, "tool_calls")
                and response.tool_calls
                and iteration < max_iterations
            ):
                iteration += 1
                logger.info(
                    f"LLM made {len(response.tool_calls)} tool calls (iteration {iteration})"
                )

                # Update progress
                if state:
                    progress = min(20 + (iteration * 15), 80)  # Progress from 20% to 80%
                    state[
                        "generation_status"
                    ] = f"Processing MCP tools (iteration {iteration}/{max_iterations})..."
                    state["generation_progress"] = progress

                # Add assistant response to conversation
                if hasattr(response, "content") and response.content:
                    current_messages.append(SystemMessage(content=f"Assistant: {response.content}"))

                # Process each tool call
                for tool_call in response.tool_calls:
                    tool_name = getattr(tool_call, "name", tool_call.get("name", ""))
                    tool_args = getattr(tool_call, "args", tool_call.get("args", {}))

                    # Create a signature for this tool call to detect duplicates
                    tool_signature = f"{tool_name}:{json.dumps(tool_args, sort_keys=True)}"

                    # Skip if this exact tool call was already made
                    if tool_signature in tool_call_history:
                        logger.warning(f"Skipping duplicate tool call: {tool_name} with same args")
                        continue

                    tool_call_history.append(tool_signature)
                    logger.info(f"Processing tool call: {tool_name}")
                    result = await self.mcp_client.call_tool(tool_name, tool_args)

                    # Cache node specs for type reference
                    if tool_name == "get_node_details" and isinstance(result, dict):
                        nodes_list = result.get("nodes", [])
                        for node_spec in nodes_list:
                            if "error" not in node_spec:
                                node_key = (
                                    f"{node_spec.get('node_type')}:{node_spec.get('subtype')}"
                                )
                                self.node_specs_cache[node_key] = node_spec
                                logger.debug(f"Cached node spec for {node_key}")

                    # Add tool result to conversation
                    result_str = (
                        json.dumps(result, indent=2) if isinstance(result, dict) else str(result)
                    )
                    current_messages.append(
                        HumanMessage(content=f"Tool result for {tool_name}:\n{result_str}")
                    )

                # Add stronger reminder about MCP types if we got node details
                has_node_details = any("get_node_details" in str(tc) for tc in response.tool_calls)
                if has_node_details:
                    current_messages.append(
                        HumanMessage(
                            content="""FINAL REMINDER - Complete Workflow Generation:
You now have the node specifications. You MUST generate a COMPLETE workflow that includes ALL steps to fulfill the user's request.

🚨 CRITICAL REQUIREMENTS:
1. **COMPLETE WORKFLOW**: Include ALL nodes needed for the ENTIRE user workflow, not just the first few steps
2. **MCP Type Compliance**: For EVERY parameter, use the exact type from MCP response:
   - type="integer" → numbers (123, not "123")
   - type="string" → strings ("example", not example)
   - type="boolean" → true/false (not "true"/"false")

3. **For approval/confirmation workflows**: You MUST include:
   - Initial processing nodes
   - Confirmation/notification step
   - HUMAN_IN_THE_LOOP node to wait for response
   - Final action node that executes after approval

Generate the COMPLETE JSON workflow now with ALL required nodes."""
                        )
                    )

                # Continue the conversation
                if state:
                    state["generation_status"] = "Generating final workflow JSON..."
                    state["generation_progress"] = 85

                tool_start = time.time()
                response = await self.llm_with_tools.ainvoke(current_messages)
                tool_elapsed = time.time() - tool_start
                logger.info(f"Tool iteration {iteration} completed in {tool_elapsed:.2f} seconds")

            if iteration >= max_iterations:
                logger.warning(f"Reached max iterations ({max_iterations}) in tool calling")

            # Final progress update
            if state:
                state["generation_status"] = "Workflow generation complete"
                state["generation_progress"] = 100

            total_elapsed = time.time() - start_time
            logger.info(f"Total workflow generation time: {total_elapsed:.2f} seconds")

            # Check if we have a final response with content
            final_content = ""
            if hasattr(response, "content") and response.content:
                final_content = str(response.content)
                logger.info(f"LLM final response length: {len(final_content)} characters")
            else:
                logger.warning("No final content from LLM, attempting one more generation request")
                # Force final generation if we don't have content
                current_messages.append(
                    HumanMessage(
                        content="Generate the complete workflow JSON now. Output only the JSON starting with { and ending with }."
                    )
                )
                try:
                    final_response = await self.llm_with_tools.ainvoke(current_messages)
                    if hasattr(final_response, "content") and final_response.content:
                        final_content = str(final_response.content)
                        logger.info(f"Forced generation produced {len(final_content)} characters")
                    else:
                        logger.error("Even forced generation produced no content")
                except Exception as e:
                    logger.error(f"Forced generation failed: {e}")

            return final_content

        except Exception as e:
            logger.error(f"Natural tool generation failed: {e}", exc_info=True)
            return ""

    async def _validate_and_complete_workflow(
        self, workflow: dict, intent_summary: str, state: dict
    ) -> dict:
        """
        Use LLM with MCP tools to validate workflow completeness and add missing nodes.

        This approach is fully LLM-driven and uses the same MCP tools that the original
        workflow generation uses, ensuring consistency and flexibility.
        """
        try:
            logger.info("Using LLM to validate workflow completeness")

            # Use LLM to determine if workflow is complete and needs enhancement
            validation_result = await self._llm_validate_workflow_completeness(
                workflow, intent_summary, state
            )

            if validation_result.get("needs_completion", False):
                logger.info("LLM determined workflow needs completion")
                # Use LLM with MCP tools to analyze and complete the workflow
                completed_workflow = await self._llm_complete_workflow(
                    workflow, intent_summary, state
                )

                if completed_workflow and len(completed_workflow.get("nodes", [])) > len(
                    workflow.get("nodes", [])
                ):
                    logger.info(
                        f"LLM completed workflow: {len(workflow.get('nodes', []))} → {len(completed_workflow.get('nodes', []))} nodes"
                    )
                    return completed_workflow
                else:
                    logger.info("LLM did not improve workflow, keeping original")
                    return workflow
            else:
                logger.info("LLM determined workflow is complete")
                return workflow

        except Exception as e:
            logger.error(f"Workflow validation failed: {e}", exc_info=True)
            return workflow

    async def _iterative_workflow_validation(
        self, workflow: dict, intent_summary: str, state: dict, current_messages: list
    ) -> dict:
        """
        Iteratively validate and improve workflow using LLM feedback loop.

        This method validates the workflow and if issues are found, dynamically creates
        feedback messages to guide the LLM to regenerate with missing nodes/connections.
        Runs up to 3 iterations to achieve completeness.
        """
        max_iterations = 2
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Workflow validation iteration {iteration}/{max_iterations}")

            # Validate current workflow
            validation_result = await self._llm_validate_workflow_completeness(
                workflow, intent_summary, state
            )

            if not validation_result.get("needs_completion", False):
                logger.info(f"Workflow validation passed on iteration {iteration}")
                return workflow

            # Workflow needs improvement - create dynamic feedback message
            logger.info(
                f"Workflow needs improvement: {validation_result.get('reasoning', 'Unknown')}"
            )

            if iteration >= max_iterations:
                logger.warning(
                    f"Reached max validation iterations ({max_iterations}), using current workflow"
                )
                break

            # Generate improvement feedback message
            improvement_message = f"""The workflow validation failed with this feedback:
{validation_result.get('reasoning', 'Workflow needs improvement')}

Please regenerate the workflow JSON to address these issues. The workflow must:
1. Include ALL required nodes to implement the complete user request
2. Have proper connections between nodes
3. Use valid JSON formatting without trailing backslashes
4. Follow the exact MCP parameter types

Generate the complete workflow JSON now:"""

            # Add feedback to conversation
            current_messages.append(HumanMessage(content=improvement_message))

            # Regenerate workflow with feedback
            try:
                response = await self.llm_with_tools.ainvoke(current_messages)
                logger.info(f"Improvement iteration {iteration} response received")

                # Extract improved workflow JSON
                if hasattr(response, "content") and response.content:
                    try:
                        # Use the same JSON repair logic as the main workflow generation
                        clean_content = response.content.strip()
                        if clean_content.startswith("```json"):
                            clean_content = clean_content[7:]
                            if clean_content.endswith("```"):
                                clean_content = clean_content[:-3]
                        elif clean_content.startswith("```"):
                            clean_content = clean_content[3:]
                            if clean_content.endswith("```"):
                                clean_content = clean_content[:-3]

                        # Apply JSON repair
                        repaired_json = await self._repair_json(clean_content.strip())
                        improved_workflow = json.loads(repaired_json)
                        improved_workflow = self._normalize_workflow_structure(improved_workflow)
                        improved_workflow = self._fix_workflow_parameters(improved_workflow)

                        # Update workflow for next iteration
                        workflow = improved_workflow
                        logger.info(
                            f"Workflow improved in iteration {iteration}: {len(workflow.get('nodes', []))} nodes"
                        )

                        # Add assistant response to conversation for next iteration
                        current_messages.append(
                            SystemMessage(content=f"Assistant: {response.content}")
                        )

                    except json.JSONDecodeError as e:
                        logger.warning(
                            f"Failed to parse improved workflow JSON in iteration {iteration}: {e}"
                        )
                        logger.warning(f"Raw response: {response.content[:500]}...")
                        break
                else:
                    logger.warning(f"No content in improvement response for iteration {iteration}")
                    break

            except Exception as e:
                logger.error(f"Workflow improvement iteration {iteration} failed: {e}")
                break

        return workflow

    async def _generate_improvement_feedback(
        self, workflow: dict, intent_summary: str, validation_result: dict
    ) -> str:
        """Generate dynamic feedback message to guide workflow improvement."""
        workflow_json = json.dumps(workflow, indent=2)
        node_count = len(workflow.get("nodes", []))
        reasoning = validation_result.get("reasoning", "Workflow may be incomplete")

        feedback_message = f"""🔄 WORKFLOW IMPROVEMENT NEEDED

**Current Status:** Your workflow has {node_count} nodes but may not fully implement the user's requirements.

**Issue Identified:** {reasoning}

**User Requirements:** {intent_summary}

**Current Workflow:**
```json
{workflow_json}
```

**Required Actions:**
1. **Analyze gaps**: Compare current workflow against user requirements
2. **Add missing nodes**: Include any missing steps, approvals, or final actions
3. **Fix connections**: Ensure proper flow between all nodes
4. **Use correct subtypes**: Use enum values from MCP specifications

**For approval workflows specifically:**
- Include HUMAN_IN_THE_LOOP node with correct subtype (e.g., SLACK_INTERACTION)
- Include final action nodes that execute after approval
- Ensure proper connection flow: trigger → process → confirm → approve → final_action

**Generate the COMPLETE improved workflow JSON now:**"""

        return feedback_message

    async def _llm_validate_workflow_completeness(
        self, workflow: dict, intent_summary: str, state: dict
    ) -> dict:
        """
        Use LLM to determine if the workflow is complete or needs additional nodes.

        Returns a dict with 'needs_completion' boolean and optional 'reasoning' string.
        """
        try:
            workflow_json = json.dumps(workflow, indent=2)

            # Load validation prompt template
            validation_prompt = await self.load_prompt_template(
                "workflow_validation", intent_summary=intent_summary, workflow_json=workflow_json
            )

            messages = [HumanMessage(content=validation_prompt)]

            # Use basic LLM without tools for this validation step
            response = await self.llm.ainvoke(messages)

            if hasattr(response, "content") and response.content:
                try:
                    # Parse the JSON response
                    validation_result = json.loads(response.content.strip())
                    logger.info(f"LLM validation result: {validation_result}")
                    return validation_result
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse LLM validation response: {e}")
                    logger.warning(f"Raw response: {response.content}")
                    # Default to not needing completion if we can't parse
                    return {
                        "needs_completion": False,
                        "reasoning": "Failed to parse validation response",
                    }

            # Default to not needing completion if no response
            return {"needs_completion": False, "reasoning": "No validation response received"}

        except Exception as e:
            logger.error(f"Workflow validation failed: {e}", exc_info=True)
            # Default to not needing completion if validation fails
            return {"needs_completion": False, "reasoning": f"Validation error: {str(e)}"}

    async def _llm_complete_workflow(
        self, incomplete_workflow: dict, intent_summary: str, state: dict
    ) -> dict:
        """
        Use LLM with MCP tools to analyze an incomplete workflow and add missing nodes.

        This reuses the existing workflow generation prompt in "edit mode" to modify
        the incomplete workflow in place, ensuring consistency with the main generation system.
        """
        try:
            workflow_json = json.dumps(incomplete_workflow, indent=2)

            # Use the existing workflow generation prompt in edit mode
            completion_prompt = await self.load_prompt_template(
                "workflow_gen_simplified",
                workflow_mode="edit",
                source_workflow=workflow_json,
                intent_summary=intent_summary,
            )

            # Use the same natural tool generation approach
            messages = [HumanMessage(content=completion_prompt)]

            # Generate with a shorter timeout since this is completion, not full generation
            start_time = time.time()
            response = await self.llm_with_tools.ainvoke(messages)
            elapsed = time.time() - start_time
            logger.info(f"Initial completion response received after {elapsed:.2f} seconds")

            # Process tool calls (similar to main generation but with max 3 iterations)
            current_messages = list(messages)
            max_iterations = 3
            iteration = 0

            while (
                hasattr(response, "tool_calls")
                and response.tool_calls
                and iteration < max_iterations
            ):
                iteration += 1
                logger.info(f"Completion tool calls (iteration {iteration})")

                # Add assistant response to conversation
                if hasattr(response, "content") and response.content:
                    current_messages.append(SystemMessage(content=f"Assistant: {response.content}"))

                # Process each tool call
                for tool_call in response.tool_calls:
                    tool_name = getattr(tool_call, "name", tool_call.get("name", ""))
                    tool_args = getattr(tool_call, "args", tool_call.get("args", {}))

                    logger.info(f"Completion processing tool call: {tool_name}")
                    result = await self.mcp_client.call_tool(tool_name, tool_args)

                    # Add tool result to conversation
                    result_str = (
                        json.dumps(result, indent=2) if isinstance(result, dict) else str(result)
                    )
                    current_messages.append(
                        HumanMessage(content=f"Tool result for {tool_name}:\n{result_str}")
                    )

                # Add completion reminder
                if iteration >= 2:  # After getting node details
                    current_messages.append(
                        HumanMessage(
                            content="Generate the complete workflow JSON now. Include all existing nodes plus any missing nodes for full functionality. Use exact MCP parameter types."
                        )
                    )

                # Continue the conversation
                response = await self.llm_with_tools.ainvoke(current_messages)

            # Extract and return the completed workflow
            final_content = str(response.content) if hasattr(response, "content") else ""

            if final_content:
                # Parse the JSON response
                try:
                    # Clean up the response (similar to main generation)
                    clean_content = final_content.strip()
                    if clean_content.startswith("```json"):
                        clean_content = clean_content[7:]
                        if clean_content.endswith("```"):
                            clean_content = clean_content[:-3]
                    elif clean_content.startswith("```"):
                        clean_content = clean_content[3:]
                        if clean_content.endswith("```"):
                            clean_content = clean_content[:-3]

                    completed_workflow = json.loads(clean_content.strip())
                    logger.info(
                        f"LLM workflow completion successful: {len(completed_workflow.get('nodes', []))} nodes"
                    )
                    return completed_workflow

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse completed workflow JSON: {e}")
                    return incomplete_workflow
            else:
                logger.warning("No completion content from LLM")
                return incomplete_workflow

        except Exception as e:
            logger.error(f"LLM workflow completion failed: {e}", exc_info=True)
            return incomplete_workflow
