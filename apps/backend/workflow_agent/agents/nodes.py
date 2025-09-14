"""
LangGraph nodes for optimized Workflow Agent architecture
Implements the 2 core nodes: Clarification and Workflow Generation
Simplified architecture with automatic gap handling for better user experience
"""

import asyncio
import json
import logging
import time
import uuid
from typing import List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from workflow_agent.core.config import settings
from workflow_agent.core.llm_provider import LLMFactory
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
        """Setup the language model using configured provider"""
        return LLMFactory.create_llm(temperature=0)

    def _setup_llm_with_tools(self):
        """Setup LLM with MCP tools bound"""
        llm = LLMFactory.create_llm(temperature=0)
        # Bind MCP tools to the LLM
        return llm.bind_tools(self.mcp_tools)

    async def load_prompt_template(self, template_name: str, **context) -> str:
        """Load and render a prompt template using the prompt engine"""
        return await self.prompt_engine.render_prompt(template_name, **context)

    def _filter_mcp_response_for_prompt(self, result: dict, tool_name: str) -> str:
        """
        Filter MCP tool responses to include only essential information for workflow generation.
        This prevents the system prompt from becoming too large while preserving critical data.
        """
        if not isinstance(result, dict):
            return str(result)

        if tool_name == "get_node_types":
            # For node types, include essential structure but limit verbosity
            if "node_types" in result:
                filtered_types = {}
                for node_type, subtypes in result["node_types"].items():
                    # Keep only subtype names, not full descriptions
                    filtered_types[node_type] = (
                        list(subtypes.keys()) if isinstance(subtypes, dict) else subtypes
                    )
                return json.dumps({"node_types": filtered_types}, indent=2)

        elif tool_name == "get_node_details":
            # For node details, include only critical workflow generation data
            if "nodes" in result:
                filtered_nodes = []
                for node in result["nodes"]:
                    if isinstance(node, dict):
                        # Keep only essential fields for workflow generation
                        filtered_node = {
                            "node_type": node.get("node_type"),
                            "subtype": node.get("subtype"),
                            "name": node.get("name"),
                            "parameters": [],
                        }

                        # For parameters, keep only type, name, required status - remove descriptions and examples
                        parameters = node.get("parameters", [])
                        for param in parameters:
                            if isinstance(param, dict):
                                filtered_param = {
                                    "name": param.get("name"),
                                    "type": param.get("type"),
                                    "required": param.get("required", False),
                                }
                                # Include enum values if present (essential for correct generation)
                                if "enum_values" in param:
                                    filtered_param["enum_values"] = param["enum_values"]
                                filtered_node["parameters"].append(filtered_param)

                        filtered_nodes.append(filtered_node)

                # Add essential reminder about type compliance
                response_data = {
                    "nodes": filtered_nodes,
                    "_instructions": {
                        "critical": "Use EXACT types from 'type' field",
                        "types": {
                            "integer": 'numbers (123, not "123")',
                            "string": 'quoted strings ("example")',
                            "boolean": 'true/false (not "true")',
                        },
                    },
                }
                return json.dumps(response_data, indent=2)

        # For other tools or if filtering fails, return compact JSON
        return json.dumps(result, separators=(",", ":"))

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
        
        注意：AI_AGENT 节点会被跳过，因为它们的 system_prompt 已经通过 
        _enhance_ai_agent_prompts_with_llm 方法进行了增强。

        Args:
            workflow: 完整的工作流数据

        Returns:
            修正后的工作流数据
        """
        if "nodes" not in workflow:
            return workflow

        for node in workflow["nodes"]:
            # Skip AI_AGENT nodes entirely - their prompts are already enhanced
            if node.get("type") == "AI_AGENT":
                logger.debug(f"Skipping parameter fix for AI_AGENT node {node.get('id')} - already enhanced")
                continue
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
                # Check for common placeholder patterns
                is_placeholder = (
                    ("{{" in param_value and "}}" in param_value)  # Template variables
                    or ("${" in param_value and "}" in param_value)  # Template variables
                    or ("<" in param_value and ">" in param_value)  # Placeholders like <VALUE>
                    or param_value.startswith("example-value")  # Generated example values
                    or param_value.startswith("mock-")  # Mock values
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

    async def _prefetch_node_specs_for_workflow(self, workflow: dict):
        """Pre-fetch MCP specifications for all nodes that AI Agents connect to."""
        try:
            connections = workflow.get("connections", {})
            nodes = workflow.get("nodes", [])
            node_map = {node["id"]: node for node in nodes}
            
            # Find all node types that AI Agents connect to
            nodes_to_fetch = set()
            for node in nodes:
                if node.get("type") == "AI_AGENT":
                    node_id = node["id"]
                    if node_id in connections:
                        node_connections = connections[node_id].get("connection_types", {})
                        main_connections = node_connections.get("main", {}).get("connections", [])
                        
                        for conn in main_connections:
                            next_node_id = conn.get("node")
                            if next_node_id and next_node_id in node_map:
                                next_node = node_map[next_node_id]
                                node_type = next_node.get("type")
                                node_subtype = next_node.get("subtype")
                                if node_type and node_subtype:
                                    nodes_to_fetch.add(f"{node_type}:{node_subtype}")
            
            # Fetch all needed specs in one call
            if nodes_to_fetch and hasattr(self, 'mcp_client'):
                logger.info(f"Pre-fetching MCP specs for nodes: {nodes_to_fetch}")
                try:
                    spec_result = await self.mcp_client.call_tool(
                        "get_node_details",
                        {"node_types": list(nodes_to_fetch)}
                    )
                    if spec_result and "nodes" in spec_result:
                        nodes_list = spec_result.get("nodes", [])
                        for node_spec in nodes_list:
                            if "error" not in node_spec:
                                node_type = node_spec.get("node_type")
                                subtype = node_spec.get("subtype")
                                if node_type and subtype:
                                    cache_key = f"{node_type}:{subtype}"
                                    self.node_specs_cache[cache_key] = node_spec
                                    logger.info(f"Cached MCP spec for {cache_key}")
                except Exception as e:
                    logger.warning(f"Failed to pre-fetch node specs from MCP: {e}")
        except Exception as e:
            logger.warning(f"Error in pre-fetch node specs: {e}")
    
    async def _enhance_ai_agent_prompts_with_llm(self, workflow: dict) -> dict:
        """
        Enhance AI Agent node prompts using LLM to ensure output format matches the next node's expected input.
        Uses concurrent LLM calls for better performance.
        """
        try:
            logger.info("Enhancing AI Agent prompts with LLM assistance (concurrent)")
            
            # Get all connections to understand the workflow flow
            connections = workflow.get("connections", {})
            nodes = workflow.get("nodes", [])
            
            # Create a map of node IDs to nodes for quick lookup
            node_map = {node["id"]: node for node in nodes}
            
            # Collect all AI Agent nodes that need enhancement
            enhancement_tasks = []
            ai_agent_nodes = []
            
            for node in nodes:
                if node.get("type") == "AI_AGENT":
                    node_id = node["id"]
                    
                    # Find what this AI Agent connects to
                    if node_id in connections:
                        node_connections = connections[node_id].get("connection_types", {})
                        main_connections = node_connections.get("main", {}).get("connections", [])
                        
                        if main_connections:
                            # Get the first connected node (primary output target)
                            next_node_id = main_connections[0].get("node")
                            if next_node_id and next_node_id in node_map:
                                next_node = node_map[next_node_id]
                                
                                # Create async task for enhancing this AI Agent's prompt
                                task = self._enhance_single_ai_agent_prompt(
                                    node, next_node, node_id, next_node_id
                                )
                                enhancement_tasks.append(task)
                                ai_agent_nodes.append((node, node_id))
            
            if enhancement_tasks:
                # Run enhancement tasks with controlled concurrency
                max_concurrent = getattr(settings, "MAX_CONCURRENT_LLM_ENHANCEMENTS", 5)
                logger.info(f"Running {len(enhancement_tasks)} LLM enhancements with max concurrency of {max_concurrent}")
                
                # Process in batches to control concurrency
                enhanced_prompts = []
                for i in range(0, len(enhancement_tasks), max_concurrent):
                    batch = enhancement_tasks[i:i + max_concurrent]
                    batch_results = await asyncio.gather(*batch, return_exceptions=True)
                    enhanced_prompts.extend(batch_results)
                    
                    # Small delay between batches to avoid rate limiting
                    if i + max_concurrent < len(enhancement_tasks):
                        await asyncio.sleep(0.5)
                
                # Apply the enhanced prompts back to the nodes
                for (node, node_id), enhanced_prompt in zip(ai_agent_nodes, enhanced_prompts):
                    if isinstance(enhanced_prompt, Exception):
                        logger.warning(f"Failed to enhance prompt for node {node_id}: {enhanced_prompt}")
                        # Keep original prompt if enhancement failed
                    elif enhanced_prompt:
                        # Update the node's system prompt with LLM-enhanced version
                        if "parameters" not in node:
                            node["parameters"] = {}
                        node["parameters"]["system_prompt"] = enhanced_prompt
                        logger.info(f"Successfully enhanced AI Agent node '{node_id}' prompt with LLM")
            
            return workflow
            
        except Exception as e:
            logger.warning(f"Error in concurrent AI Agent prompt enhancement: {e}")
            # Fall back to non-LLM enhancement
            return self._enhance_ai_agent_prompts(workflow)
    
    async def _enhance_single_ai_agent_prompt(self, ai_node: dict, next_node: dict, ai_node_id: str, next_node_id: str) -> str:
        """
        Enhance a single AI Agent's prompt using LLM to understand the next node's requirements.
        """
        try:
            current_prompt = ai_node.get("parameters", {}).get("system_prompt", "")
            next_node_type = next_node.get("type")
            next_node_subtype = next_node.get("subtype")
            
            # Get the node spec from cache if available
            node_key = f"{next_node_type}:{next_node_subtype}"
            node_spec = self.node_specs_cache.get(node_key)
            
            # Prepare context for LLM
            enhancement_prompt = f"""You are a workflow optimization expert. You need to enhance an AI Agent's system prompt to ensure its output format matches what the next node expects.

Current AI Agent System Prompt:
{current_prompt}

This AI Agent connects to: {next_node_type} - {next_node_subtype}
Next node's purpose: {next_node.get('name', 'Unknown')}

"""
            
            if node_spec:
                # Add spec details if available
                parameters = node_spec.get("parameters", [])
                if parameters:
                    enhancement_prompt += "Next node expects these parameters:\n"
                    for param in parameters[:10]:  # Limit to first 10 params
                        enhancement_prompt += f"- {param.get('name')} ({param.get('type')}): {param.get('description', 'N/A')}\n"
            
            enhancement_prompt += """
Please enhance the system prompt to:
1. Clearly specify the output format required by the next node
2. Include JSON structure if the next node expects JSON
3. Add examples if helpful
4. Keep the original intent and functionality
5. Be concise but explicit about format requirements

Return ONLY the enhanced system prompt, no explanations."""

            # Use LLM to enhance the prompt
            messages = [
                SystemMessage(content="You are an expert at optimizing AI system prompts for workflow integration."),
                HumanMessage(content=enhancement_prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            enhanced_prompt = response.content.strip()
            
            # Validate the enhanced prompt isn't empty or too different
            if enhanced_prompt and len(enhanced_prompt) > 20:
                logger.info(f"LLM enhanced prompt for node {ai_node_id} connecting to {next_node_id}")
                return enhanced_prompt
            else:
                # Fall back to simple enhancement
                format_prompt = self._generate_format_prompt_for_node(next_node)
                return self._add_format_requirements_to_prompt(current_prompt, format_prompt, next_node)
                
        except Exception as e:
            logger.warning(f"Error enhancing single prompt with LLM: {e}")
            # Fall back to simple enhancement
            format_prompt = self._generate_format_prompt_for_node(next_node)
            return self._add_format_requirements_to_prompt(current_prompt, format_prompt, next_node)
    
    def _enhance_ai_agent_prompts(self, workflow: dict) -> dict:
        """
        Enhance AI Agent node prompts to ensure output format matches the next node's expected input.
        This is crucial for workflow reliability - preventing format mismatches between nodes.
        """
        try:
            logger.info("Enhancing AI Agent prompts based on connected nodes")
            
            # Get all connections to understand the workflow flow
            connections = workflow.get("connections", {})
            nodes = workflow.get("nodes", [])
            
            # Create a map of node IDs to nodes for quick lookup
            node_map = {node["id"]: node for node in nodes}
            
            # Process each AI Agent node
            for node in nodes:
                if node.get("type") == "AI_AGENT":
                    node_id = node["id"]
                    
                    # Find what this AI Agent connects to
                    if node_id in connections:
                        node_connections = connections[node_id].get("connection_types", {})
                        main_connections = node_connections.get("main", {}).get("connections", [])
                        
                        if main_connections:
                            # Get the first connected node (primary output target)
                            next_node_id = main_connections[0].get("node")
                            if next_node_id and next_node_id in node_map:
                                next_node = node_map[next_node_id]
                                
                                # Generate format requirements based on next node type
                                format_prompt = self._generate_format_prompt_for_node(next_node)
                                
                                if format_prompt:
                                    # Enhance the system prompt with format requirements
                                    current_prompt = node.get("parameters", {}).get("system_prompt", "")
                                    enhanced_prompt = self._add_format_requirements_to_prompt(
                                        current_prompt, format_prompt, next_node
                                    )
                                    
                                    # Update the node's system prompt
                                    if "parameters" not in node:
                                        node["parameters"] = {}
                                    node["parameters"]["system_prompt"] = enhanced_prompt
                                    
                                    logger.info(
                                        f"Enhanced AI Agent node '{node_id}' prompt for "
                                        f"connection to '{next_node['type']}' node '{next_node_id}'"
                                    )
            
            return workflow
            
        except Exception as e:
            logger.warning(f"Error enhancing AI Agent prompts: {e}")
            # Return workflow unchanged if enhancement fails
            return workflow
    
    def _generate_format_prompt_for_node(self, node: dict) -> str:
        """Generate format requirements based on the node's MCP specification."""
        node_type = node.get("type")
        node_subtype = node.get("subtype")
        
        # Try to get node spec from cache first
        node_key = f"{node_type}:{node_subtype}"
        node_spec = self.node_specs_cache.get(node_key)
        
        # If not in cache, try to fetch from MCP
        if not node_spec and hasattr(self, 'mcp_client'):
            try:
                # Query MCP for this specific node's details
                # Note: We'll use the cached specs if available, otherwise skip dynamic fetch
                # since this is called from sync context but MCP client is async
                logger.info(f"Node spec for {node_key} not in cache, will use generic format prompt")
            except Exception as e:
                logger.warning(f"Failed to fetch node spec from MCP: {e}")
        
        # Generate format prompt from MCP spec
        if node_spec:
            return self._generate_format_from_mcp_spec(node_spec, node_type, node_subtype)
        
        # Fallback: Generic prompt for unknown nodes
        return """
Your output should be structured data that the next node can process.
Check the node's expected input format and structure your response accordingly.
"""
    
    def _add_format_requirements_to_prompt(self, current_prompt: str, format_prompt: str, next_node: dict) -> str:
        """Add format requirements to the existing prompt."""
        if not format_prompt:
            return current_prompt
        
        # Add a clear section about output format requirements
        enhanced_prompt = current_prompt
        
        # Check if prompt already has format requirements
        if "output format" not in current_prompt.lower() and "json" not in current_prompt.lower():
            node_name = next_node.get("name", next_node.get("subtype", "next node"))
            node_subtype = next_node.get("subtype", "")
            
            enhanced_prompt += f"""

=== CRITICAL OUTPUT FORMAT REQUIREMENT ===
Your response will be passed to a {node_subtype or node_name} node.
{format_prompt}

IMPORTANT: 
- Your entire response should be ONLY the JSON object
- Do NOT include any explanation, markdown formatting, or code blocks
- The JSON must be valid and parseable
- All required fields must be present
"""
        
        return enhanced_prompt
    
    def _generate_format_from_mcp_spec(self, node_spec: dict, node_type: str, node_subtype: str) -> str:
        """Generate format prompt from MCP node specification."""
        format_prompt = """
Your output MUST match the expected input format for the next node.
"""
        
        # Extract parameters from the spec
        parameters = node_spec.get("parameters", [])
        required_params = [p for p in parameters if p.get("required", False)]
        optional_params = [p for p in parameters if not p.get("required", False)]
        
        if parameters:
            format_prompt += f"\nThe {node_subtype} node expects the following input:\n\n"
            
            # Build a JSON structure example based on parameters
            format_prompt += "Required JSON structure:\n```json\n{\n"
            
            # Add required parameters
            if required_params:
                for i, param in enumerate(required_params):
                    param_name = param.get("name", "param")
                    param_type = param.get("type", "string")
                    param_desc = param.get("description", "")
                    
                    # Generate example value based on type
                    example_value = self._get_example_for_param_type(param_type, param_name)
                    
                    format_prompt += f'    "{param_name}": {example_value}'
                    if param_desc:
                        format_prompt += f'  // {param_desc}'
                    
                    if i < len(required_params) - 1 or optional_params:
                        format_prompt += ","
                    format_prompt += "\n"
            
            # Add optional parameters as comments
            if optional_params:
                format_prompt += "    // Optional fields:\n"
                for param in optional_params[:3]:  # Show max 3 optional fields
                    param_name = param.get("name", "param")
                    param_type = param.get("type", "string")
                    example_value = self._get_example_for_param_type(param_type, param_name)
                    format_prompt += f'    // "{param_name}": {example_value}\n'
            
            format_prompt += "}\n```\n"
            
            # Add parameter descriptions if available
            if required_params:
                format_prompt += "\nRequired fields:\n"
                for param in required_params:
                    param_name = param.get("name")
                    param_desc = param.get("description", "No description")
                    param_type = param.get("type", "string")
                    format_prompt += f"- **{param_name}** ({param_type}): {param_desc}\n"
        
        # Add any specific notes based on node type
        if node_type == "EXTERNAL_ACTION":
            format_prompt += "\nIMPORTANT: This is an external API integration. Ensure your output exactly matches the API's expected format."
        elif node_type == "ACTION":
            format_prompt += "\nIMPORTANT: Structure your output as valid JSON that can be processed by the action node."
        
        return format_prompt
    
    def _get_example_for_param_type(self, param_type: str, param_name: str) -> str:
        """Generate an example value for a parameter based on its type."""
        # Map MCP parameter types to example values
        type_examples = {
            "string": '"example text"',
            "integer": "123",
            "float": "1.5",
            "boolean": "true",
            "json": "{}",
            "array": "[]",
            "object": "{}"
        }
        
        # Use parameter name hints for better examples
        if "email" in param_name.lower():
            return '"user@example.com"'
        elif "date" in param_name.lower() or "time" in param_name.lower():
            return '"2024-01-15T10:00:00Z"'
        elif "url" in param_name.lower() or "link" in param_name.lower():
            return '"https://example.com"'
        elif "title" in param_name.lower() or "name" in param_name.lower():
            return '"Example Title"'
        elif "description" in param_name.lower() or "body" in param_name.lower():
            return '"Detailed description here"'
        elif "id" in param_name.lower():
            return '"item-123"'
        elif "channel" in param_name.lower():
            return '"#general"'
        
        # Return type-based default
        return type_examples.get(param_type, '"value"')
    
    def _validate_ai_agent_prompts(self, workflow: dict) -> List[str]:
        """
        Validate that AI Agent prompts are properly configured for their connections.
        Returns a list of warnings if issues are found.
        """
        warnings = []
        
        try:
            connections = workflow.get("connections", {})
            nodes = workflow.get("nodes", [])
            node_map = {node["id"]: node for node in nodes}
            
            for node in nodes:
                if node.get("type") == "AI_AGENT":
                    node_id = node["id"]
                    system_prompt = node.get("parameters", {}).get("system_prompt", "")
                    
                    # Check if this AI Agent connects to an action node
                    if node_id in connections:
                        node_connections = connections[node_id].get("connection_types", {})
                        main_connections = node_connections.get("main", {}).get("connections", [])
                        
                        if main_connections:
                            next_node_id = main_connections[0].get("node")
                            if next_node_id and next_node_id in node_map:
                                next_node = node_map[next_node_id]
                                next_type = next_node.get("type")
                                next_subtype = next_node.get("subtype")
                                
                                # Check if connecting to an action node that needs structured output
                                needs_json = False
                                if next_type == "EXTERNAL_ACTION":
                                    needs_json = True
                                elif next_type == "ACTION" and next_subtype in ["HTTP_REQUEST", "SAVE_TO_DATABASE"]:
                                    needs_json = True
                                
                                if needs_json:
                                    # Check if prompt mentions JSON or output format
                                    prompt_lower = system_prompt.lower()
                                    has_format = any(keyword in prompt_lower for keyword in [
                                        "json", "format", "output", "structure", "object", "api"
                                    ])
                                    
                                    if not has_format:
                                        warnings.append(
                                            f"AI Agent '{node_id}' connects to '{next_subtype}' but "
                                            f"system prompt doesn't specify output format. This may cause failures."
                                        )
                                    
                                    # Check for specific node types
                                    if next_subtype == "GOOGLE_CALENDAR" and "calendar" not in prompt_lower:
                                        warnings.append(
                                            f"AI Agent '{node_id}' connects to Google Calendar but "
                                            f"prompt doesn't mention calendar event format"
                                        )
                                    elif next_subtype == "SLACK" and "slack" not in prompt_lower and "message" not in prompt_lower:
                                        warnings.append(
                                            f"AI Agent '{node_id}' connects to Slack but "
                                            f"prompt doesn't mention message format"
                                        )
            
            return warnings
            
        except Exception as e:
            logger.error(f"Error validating AI Agent prompts: {e}")
            return warnings
    
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

                    # Parse the JSON directly - trust LLM to generate valid JSON
                    workflow = json.loads(workflow_json.strip())

                    # Post-process the workflow to add missing required fields
                    workflow = self._normalize_workflow_structure(workflow)
                    
                    # Pre-fetch node specs for connected nodes
                    await self._prefetch_node_specs_for_workflow(workflow)
                    
                    # Enhance AI Agent prompts based on connected nodes
                    # Try to use LLM-enhanced version for better quality
                    try:
                        # Check if we should use LLM enhancement (can be controlled by settings)
                        use_llm_enhancement = getattr(settings, "USE_LLM_PROMPT_ENHANCEMENT", True)
                        
                        if use_llm_enhancement:
                            logger.info("Using concurrent LLM enhancement for AI Agent prompts")
                            workflow = await self._enhance_ai_agent_prompts_with_llm(workflow)
                        else:
                            logger.info("Using rule-based enhancement for AI Agent prompts")
                            workflow = self._enhance_ai_agent_prompts(workflow)
                    except Exception as e:
                        logger.warning(f"LLM enhancement failed, falling back to rule-based: {e}")
                        workflow = self._enhance_ai_agent_prompts(workflow)
                    
                    # Validate that AI Agent prompts are properly configured
                    validation_warnings = self._validate_ai_agent_prompts(workflow)
                    if validation_warnings:
                        for warning in validation_warnings:
                            logger.warning(f"AI Agent prompt validation: {warning}")

                    # Fix parameters using MCP-provided types (only as fallback)
                    workflow = self._fix_workflow_parameters(workflow)

                    # Skip iterative validation - single pass generation for better performance
                    logger.info(
                        "Single-pass workflow generation completed - skipping validation rounds"
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

                    # Add tool result to conversation with optimized filtering
                    original_size = (
                        len(json.dumps(result, indent=2))
                        if isinstance(result, dict)
                        else len(str(result))
                    )
                    result_str = self._filter_mcp_response_for_prompt(result, tool_name)
                    logger.debug(
                        f"💡 MCP response filtered: reduced from {original_size} to {len(result_str)} characters"
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

                        # Parse the JSON directly - trust LLM to generate valid JSON
                        improved_workflow = json.loads(clean_content.strip())
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

                    # Add tool result to conversation with optimized filtering
                    original_size = (
                        len(json.dumps(result, indent=2))
                        if isinstance(result, dict)
                        else len(str(result))
                    )
                    result_str = self._filter_mcp_response_for_prompt(result, tool_name)
                    logger.debug(
                        f"💡 MCP response filtered: reduced from {original_size} to {len(result_str)} characters"
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
