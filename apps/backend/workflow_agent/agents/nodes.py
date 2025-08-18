"""
LangGraph nodes for optimized Workflow Agent architecture
Implements the 2 core nodes: Clarification and Workflow Generation
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

    def _fix_workflow_parameters(self, workflow: dict) -> dict:
        """
        修正工作流中所有节点的参数，使用 MCP 提供的 ParameterType 信息。
        这只是兜底逻辑，LLM 应该直接根据 MCP ParameterType 生成正确的 mock values。
        
        Args:
            workflow: 完整的工作流数据
            
        Returns:
            修正后的工作流数据
        """
        if 'nodes' not in workflow:
            return workflow
            
        for node in workflow['nodes']:
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
        if not node.get('parameters'):
            return node
            
        # Get node spec from cache
        node_key = f"{node.get('type')}:{node.get('subtype')}"
        node_spec = self.node_specs_cache.get(node_key)
        
        parameters = node['parameters']
        
        for param_name, param_value in list(parameters.items()):
            # Get parameter type from MCP spec if available
            param_type = None
            param_required = False
            if node_spec and 'parameters' in node_spec:
                for param_spec in node_spec['parameters']:
                    if param_spec.get('name') == param_name:
                        param_type = param_spec.get('type', 'string')
                        param_required = param_spec.get('required', False)
                        break
            
            # Handle reference objects using MCP-provided ParameterType
            if isinstance(param_value, dict) and ('$ref' in param_value or '$expr' in param_value):
                logger.warning(f"LLM generated reference object for '{param_name}': {param_value}")
                logger.warning(f"LLM should have used MCP ParameterType '{param_type}' to generate a proper mock value!")
                
                if param_type:
                    logger.info(f"Using MCP-provided ParameterType '{param_type}' for parameter '{param_name}'")
                    parameters[param_name] = self._generate_proper_value_for_type(param_type)
                else:
                    # Fallback only if MCP type not available
                    logger.warning(f"No MCP type info for '{param_name}', using fallback")
                    parameters[param_name] = "example-value"
            
            # Handle template variables (another form of placeholder)
            elif isinstance(param_value, str):
                is_placeholder = (
                    ('{{' in param_value and '}}' in param_value) or
                    ('${' in param_value and '}' in param_value) or
                    ('<' in param_value and '>' in param_value)
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
                if any(keyword in param_name.lower() for keyword in ['number', 'id', 'count']):
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
                        node["name"] = f"{node_type}_{node_subtype}_{node_id}".replace("_", "-").lower()
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
                    "webhooks": []
                }
            ],
            "connections": {},
            "settings": {
                "timezone": {"name": "UTC"},
                "save_execution_progress": True,
                "save_manual_executions": True,
                "timeout": 3600,
                "error_policy": "continue",
                "caller_policy": "workflow"
            },
            "static_data": {},
            "pin_data": {},
            "tags": ["fallback"],
            "active": True,
            "version": "1.0",
            "id": "fallback-workflow"
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
                    intent = clarification_output.get('intent_summary', 'your workflow request')
                    assistant_message = f"Perfect! I understand your requirements: {intent}\n\nI'll now generate the workflow for you."
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

            # Generate workflow using natural MCP tool calling
            workflow_json = await self._generate_with_natural_tools(messages)

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
                    
                    # Fix parameters using MCP-provided types (only as fallback)
                    workflow = self._fix_workflow_parameters(workflow)
                    
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
                
                # Add detailed completion message to conversations
                workflow_name = workflow.get("name", "Workflow")
                workflow_description = workflow.get("description", "")
                node_count = len(workflow.get("nodes", []))
                
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
                
                self._add_conversation(
                    state,
                    "assistant",
                    completion_message
                )
                
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

    async def _generate_with_natural_tools(self, messages: List) -> str:
        """
        Natural workflow generation - let LLM decide when and how to use MCP tools.
        Still emphasizes following MCP type specifications but doesn't force specific calling patterns.
        """
        try:
            logger.info("Starting natural workflow generation with MCP tools")
            
            # Let LLM use tools naturally - no forced multi-turn pattern
            response = await self.llm_with_tools.ainvoke(messages)
            
            # Process any tool calls the LLM decided to make
            current_messages = list(messages)
            max_iterations = 5  # Prevent infinite loops
            iteration = 0
            tool_call_history = []  # Track what tools have been called to avoid duplicates
            
            while hasattr(response, "tool_calls") and response.tool_calls and iteration < max_iterations:
                iteration += 1
                logger.info(f"LLM made {len(response.tool_calls)} tool calls (iteration {iteration})")
                
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
                                node_key = f"{node_spec.get('node_type')}:{node_spec.get('subtype')}"
                                self.node_specs_cache[node_key] = node_spec
                                logger.debug(f"Cached node spec for {node_key}")
                    
                    # Add tool result to conversation
                    result_str = json.dumps(result, indent=2) if isinstance(result, dict) else str(result)
                    current_messages.append(HumanMessage(content=f"Tool result for {tool_name}:\n{result_str}"))
                
                # Add stronger reminder about MCP types if we got node details
                has_node_details = any("get_node_details" in str(tc) for tc in response.tool_calls)
                if has_node_details:
                    current_messages.append(HumanMessage(
                        content="""FINAL REMINDER - MCP Type Compliance:
You now have the node specifications with exact type requirements. 
For EVERY parameter, you MUST use the type specified in the MCP response:
- If MCP says type="integer" → Use numbers WITHOUT quotes (123, not "123")
- If MCP says type="string" → Use strings WITH quotes ("example", not example)
- If MCP says type="boolean" → Use true/false WITHOUT quotes

Generate the complete JSON workflow now, strictly following these MCP types."""
                    ))
                
                # Continue the conversation
                response = await self.llm_with_tools.ainvoke(current_messages)
            
            if iteration >= max_iterations:
                logger.warning(f"Reached max iterations ({max_iterations}) in tool calling")
            
            # Return the final response content
            return str(response.content) if hasattr(response, "content") else ""
            
        except Exception as e:
            logger.error(f"Natural tool generation failed: {e}", exc_info=True)
            return ""

