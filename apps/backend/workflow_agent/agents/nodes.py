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
            {"role": role, "text": text, "timestamp": int(time.time() * 1000)}
        )


    def _get_conversation_context(self, state: WorkflowState) -> str:
        """Extract conversation context from state with proper capping and formatting"""
        conversations = state.get("conversations", [])
        
        # Define maximum context based on the 3-node architecture
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

    def _generate_mock_value(self, param_name: str, param_type: str = "string") -> object:
        """
        生成符合类型的 mock value

        Args:
            param_name: 参数名称
            param_type: 参数类型 (string, integer, float, boolean, json)
            
        Returns:
            符合类型的 mock value
        """
        param_lower = param_name.lower()
        
        # 根据参数类型生成合适的 mock value
        if param_type == "integer":
            # 整数类型
            if 'number' in param_lower or 'id' in param_lower:
                return 123
            elif 'count' in param_lower:
                return 5
            elif 'port' in param_lower:
                return 8080
            else:
                return 42
                
        elif param_type == "float" or param_type == "number":
            # 浮点数类型
            if 'temperature' in param_lower:
                return 0.7
            elif 'threshold' in param_lower:
                return 0.5
            else:
                return 1.0
                
        elif param_type == "boolean":
            # 布尔类型
            if 'enable' in param_lower or 'active' in param_lower:
                return True
            elif 'disable' in param_lower or 'ignore' in param_lower:
                return False
            else:
                return True
                
        elif param_type == "json" or param_type == "array":
            # JSON/数组类型
            if 'labels' in param_lower or 'tags' in param_lower:
                return ["example", "test"]
            elif 'config' in param_lower or 'settings' in param_lower:
                return {"key": "value"}
            else:
                return []
                
        else:  # string 或其他
            # 字符串类型
            if 'repository' in param_lower or 'repo' in param_lower:
                return "owner/repo"
            elif 'token' in param_lower or 'key' in param_lower:
                return "mock-token-123456"
            elif 'email' in param_lower:
                return "user@example.com"
            elif 'url' in param_lower or 'webhook' in param_lower:
                return "https://api.example.com/webhook"
            elif 'message' in param_lower or 'body' in param_lower:
                return "Example message content"
            elif 'title' in param_lower or 'subject' in param_lower:
                return "Example Title"
            elif 'channel' in param_lower:
                return "#general"
            elif 'cron' in param_lower:
                return "0 9 * * *"
            elif 'timestamp' in param_lower or 'date' in param_lower:
                return "2024-01-01T00:00:00Z"
            else:
                return f"mock-{param_name}"
    
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
        if not node.get('parameters'):
            return node
        
        optimized_params = {}
        current_params = node['parameters']
        
        # 如果有节点规格，使用它来确定必需参数
        if node_spec and 'parameters' in node_spec:
            for param_spec in node_spec['parameters']:
                param_name = param_spec['name']
                param_required = param_spec.get('required', False)
                param_desc = param_spec.get('description', '')
                
                # 检查当前参数中是否有这个参数
                if param_name in current_params:
                    param_value = current_params[param_name]
                    
                    # 必需参数或有明确值的参数
                    if param_required or (param_value and param_value != param_spec.get('default_value')):
                        # 保留参数值，如果已经是模板变量格式则保持不变
                        optimized_params[param_name] = param_value
        else:
            # 没有规格信息时，进行基本优化
            for param_name, param_value in current_params.items():
                # 跳过真正的空值
                if param_value is None or param_value == "" or (isinstance(param_value, list) and len(param_value) == 0) or (isinstance(param_value, dict) and len(param_value) == 0):
                    continue
                
                # 保留非空参数
                optimized_params[param_name] = param_value
        
        node['parameters'] = optimized_params
        return node

    def _fix_parameter_types(self, node: dict) -> dict:
        """
        最小化的参数修正，只处理会导致验证失败的关键问题。
        优先依赖 LLM 通过改进的 prompt 生成正确值。
        
        Args:
            node: 节点数据
            
        Returns:
            修正后的节点数据
        """
        if not node.get('parameters'):
            return node
            
        parameters = node['parameters']
        
        for param_name, param_value in parameters.items():
            # 只修正最明显的占位符模式
            if isinstance(param_value, str):
                # 检测明确的占位符模式
                is_obvious_placeholder = (
                    # 尖括号占位符，如 <OWNER>/<REPO>, <YOUR_TOKEN>
                    ('<' in param_value and '>' in param_value) or
                    # 模板变量
                    ('{{' in param_value and '}}' in param_value) or
                    # 环境变量占位符
                    ('${' in param_value and '}' in param_value)
                )
                
                if is_obvious_placeholder:
                    # 使用更通用的 mock value 生成逻辑
                    parameters[param_name] = self._generate_mock_value(param_name, "string")
                    logger.debug(f"Replaced placeholder '{param_value}' with mock value for parameter '{param_name}'")
            
            # 只修正明显无效的值（如 ID 字段为 0）
            elif isinstance(param_value, int) and param_value == 0:
                if any(keyword in param_name.lower() for keyword in ['number', 'id', 'count', 'port']):
                    parameters[param_name] = self._generate_mock_value(param_name, "integer")
                    logger.debug(f"Replaced invalid value 0 with mock value for parameter '{param_name}'")
                    
        return node
    
    def _normalize_workflow_structure(self, workflow: dict) -> dict:
        """
        Minimal normalization - only fix critical issues that break workflow creation
        Most fields should be correctly generated by LLM with improved prompt
        """
        # Handle workflow_meta if LLM uses old format
        if "workflow_meta" in workflow and not workflow.get("name"):
            workflow["name"] = workflow["workflow_meta"].get("name", "Generated Workflow")
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
                        node["name"] = f"{node_type}_{node_subtype}_{node_id}".replace("_", "-").lower()
                    else:
                        node["name"] = f"{node_type}_{node_id}".replace("_", "-").lower()
                
                # Fix parameter types (ensure mock values instead of template variables)
                node = self._fix_parameter_types(node)
                
                # Optimize node parameters (remove unnecessary params)
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
                    "webhooks": []
                }
                
                for field, default in essential_defaults.items():
                    if field not in node:
                        node[field]= default
        
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
                    
                    if from_node not in connections_dict:
                        connections_dict[from_node] = {}
                    if from_port not in connections_dict[from_node]:
                        connections_dict[from_node][from_port] = []
                    
                    connections_dict[from_node][from_port].append({
                        "node": to_node,
                        "type": to_port,
                        "index": 0
                    })
            
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
                "caller_policy": "workflow"
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
            workflow["id"] = re.sub(r'[^a-z0-9-]', '-', name.lower())[:50]
        
        return workflow

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
        Clarification Node - Optimized for 3-node architecture
        Focuses on understanding user intent quickly with minimal questions
        """
        logger.info("Processing clarification node")

        # Get core state data
        user_message = get_user_message(state)
        existing_intent = get_intent_summary(state)
        conversation_history = self._get_conversation_context(state)
        
        # Track conversation rounds for limiting questions
        conversation_rounds = len([c for c in state.get("conversations", []) if c.get("role") == "user"])
        MAX_CLARIFICATION_ROUNDS = 3
        force_completion = conversation_rounds >= MAX_CLARIFICATION_ROUNDS
        
        logger.info(
            "Clarification context",
            extra={
                "user_message": user_message[:100] if user_message else None,
                "conversation_rounds": conversation_rounds,
                "force_completion": force_completion,
            },
        )

        state["stage"] = WorkflowStage.CLARIFICATION

        try:
            # Simplified template context - only what's needed
            template_context = {
                "user_message": user_message,
                "existing_intent": existing_intent,
                "conversation_history": conversation_history,
                "force_completion": force_completion,
                "conversation_rounds": conversation_rounds,
                "max_rounds": MAX_CLARIFICATION_ROUNDS,
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
                
                # Force completion if we've hit the round limit
                if force_completion:
                    clarification_output["is_complete"] = True
                    clarification_output["clarification_question"] = ""
                    logger.info(f"Forced completion after {conversation_rounds} rounds")
                
                # Check if clarification is ready (for future routing logic)
                is_ready = clarification_output.get("is_complete", False)  # noqa: F841

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
                    assistant_message = f"I understand your requirements: {clarification_output.get('intent_summary', 'Processing your workflow request')}"
                else:
                    assistant_message = clarification_output.get("intent_summary", "Processing your request")
                
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
                    
                    # Post-process the workflow to add missing required fields
                    workflow = self._normalize_workflow_structure(workflow)
                    
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
