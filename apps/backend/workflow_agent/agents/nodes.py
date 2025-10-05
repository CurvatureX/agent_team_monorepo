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
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from workflow_agent.core.config import settings
from workflow_agent.core.llm_provider import LLMFactory
from workflow_agent.core.prompt_engine import get_prompt_engine

from .exceptions import WorkflowGenerationError
from .mcp_tools import MCPToolCaller
from .state import (
    WorkflowStage,
    WorkflowState,
    get_intent_summary,
    get_user_message,
    is_clarification_ready,
)

logger = logging.getLogger(__name__)

DEFAULT_CONVERSION_FUNCTION = (
    "def convert(input_data: Dict[str, Any]) -> Dict[str, Any]:\n"
    "    return input_data.get('data', input_data)"
)


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
        logger.info("=== Creating LLM for workflow execution ===")
        llm = LLMFactory.create_llm(temperature=0)
        logger.info(f"LLM created successfully: {type(llm).__name__}")
        return llm

    def _setup_llm_with_tools(self):
        """Setup LLM with MCP tools bound"""
        logger.info("=== Creating LLM with MCP tools for workflow execution ===")
        llm = LLMFactory.create_llm(temperature=0)
        logger.info(f"LLM with tools created successfully: {type(llm).__name__}")
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

    async def _prefetch_node_specs_for_workflow(self, workflow: dict):
        """Pre-fetch MCP specifications for all nodes involved in the workflow."""
        try:
            nodes = workflow.get("nodes", [])

            nodes_to_fetch: List[Dict[str, Any]] = []
            for node in nodes:
                node_type = node.get("type")
                node_subtype = node.get("subtype")
                if not node_type or not node_subtype:
                    continue

                cache_key = f"{node_type}:{node_subtype}"
                if cache_key in self.node_specs_cache:
                    continue

                nodes_to_fetch.append({"node_type": node_type, "subtype": node_subtype})

            if nodes_to_fetch and hasattr(self, "mcp_client"):
                pretty_list = [f"{n['node_type']}:{n['subtype']}" for n in nodes_to_fetch]
                logger.info(f"Pre-fetching MCP specs for nodes: {pretty_list}")
                try:
                    spec_result = await self.mcp_client.call_tool(
                        "get_node_details",
                        {
                            "nodes": nodes_to_fetch,
                            "include_examples": True,
                            "include_schemas": True,
                        },
                    )

                    nodes_list: List[Dict[str, Any]] = []
                    if isinstance(spec_result, dict):
                        if "nodes" in spec_result:
                            nodes_list = spec_result.get("nodes", [])
                        elif "result" in spec_result and isinstance(spec_result["result"], dict):
                            nodes_list = spec_result["result"].get("nodes", [])
                    elif isinstance(spec_result, list):
                        nodes_list = spec_result

                    for node_spec in nodes_list:
                        if not isinstance(node_spec, dict) or "error" in node_spec:
                            continue
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

    async def _hydrate_nodes_from_specs(self, workflow: dict):
        """Ensure every node includes configuration and param defaults derived from MCP specs."""
        try:
            nodes = workflow.get("nodes", [])
            for node in nodes:
                spec = await self._get_or_fetch_node_spec(node)
                if not spec:
                    continue
                self._apply_spec_defaults(node, spec)
        except Exception as e:
            logger.warning(f"Error hydrating nodes from specs: {e}")

    def _apply_spec_defaults(self, node: Dict[str, Any], spec: Dict[str, Any]) -> None:
        """Merge configuration/input/output schemas into the node with sensible defaults."""

        config_schema = spec.get("configurations") or {}
        input_schema = spec.get("input_params_schema") or {}
        output_schema = spec.get("output_params_schema") or {}

        node.setdefault("configurations", {})
        node.setdefault("input_params", {})
        node.setdefault("output_params", {})

        self._merge_schema_defaults(node["configurations"], config_schema)
        self._merge_schema_defaults(node["input_params"], input_schema)
        self._merge_schema_defaults(node["output_params"], output_schema)

        if spec.get("attached_nodes") and "attached_nodes" not in node:
            node["attached_nodes"] = spec["attached_nodes"]

    def _merge_schema_defaults(self, target: Dict[str, Any], schema: Dict[str, Any]) -> None:
        for name, definition in schema.items():
            if not isinstance(definition, dict):
                target.setdefault(name, definition)
                continue

            desired_type = definition.get("type")
            default_value = definition.get("default")
            if default_value is None and definition.get("enum_values"):
                default_value = definition["enum_values"][0]
            if default_value is None:
                default_value = self._example_for_type(desired_type)

            if name not in target or target[name] in (None, "", []):
                target[name] = default_value
            else:
                coerced = self._coerce_value(desired_type, target[name])
                target[name] = coerced

    @staticmethod
    def _coerce_value(expected_type: Optional[str], value: Any) -> Any:
        """Best-effort coercion of simple scalar types."""

        if value is None or not expected_type:
            return value

        normalized = str(expected_type).lower()
        try:
            if normalized in {"integer", "int"}:
                if isinstance(value, bool):
                    return int(value)
                return int(value)
            if normalized in {"float", "number"}:
                if isinstance(value, bool):
                    return float(int(value))
                return float(value)
            if normalized in {"boolean", "bool"}:
                if isinstance(value, str):
                    return value.lower() in {"true", "1", "yes"}
                return bool(value)
            if normalized in {"json", "object", "dict"}:
                if isinstance(value, str):
                    try:
                        return json.loads(value)
                    except Exception:
                        return {}
                return value if isinstance(value, dict) else {}
            if normalized in {"array", "list"}:
                if isinstance(value, str):
                    try:
                        parsed = json.loads(value)
                        return parsed if isinstance(parsed, list) else []
                    except Exception:
                        return []
                return value if isinstance(value, list) else []
        except Exception:
            return value

        if isinstance(value, str):
            return value

        return str(value)

    @staticmethod
    def _example_for_type(type_name: Optional[str]) -> Any:
        if not type_name:
            return ""

        normalized = str(type_name).lower()
        if normalized in {"integer", "int"}:
            return 0
        if normalized in {"float", "number"}:
            return 0.0
        if normalized in {"boolean", "bool"}:
            return False
        if normalized in {"json", "object", "dict"}:
            return {}
        if normalized in {"array", "list"}:
            return []

        return ""

    def _ensure_workflow_metadata(self, workflow: dict, state: WorkflowState) -> None:
        """Populate metadata and triggers required by workflow_engine v2."""

        metadata = workflow.get("metadata") or {}
        workflow_name = workflow.get("name", metadata.get("name", "Generated Workflow"))

        metadata.setdefault("id", workflow.get("id", str(uuid.uuid4())))
        metadata.setdefault("name", workflow_name)
        metadata.setdefault(
            "description", workflow.get("description", metadata.get("description", ""))
        )
        metadata.setdefault("tags", workflow.get("tags", metadata.get("tags", [])))
        metadata.setdefault("version", metadata.get("version", "1.0"))
        metadata["deployment_status"] = "pending"
        metadata.setdefault("created_by", state.get("user_id", "workflow_agent"))
        metadata.setdefault("created_time", int(time.time() * 1000))

        workflow["metadata"] = metadata
        workflow["id"] = metadata["id"]

        triggers = workflow.get("triggers")
        if not triggers:
            triggers = [
                node.get("id")
                for node in workflow.get("nodes", [])
                if node.get("type") == "TRIGGER" and node.get("id")
            ]
            if not triggers:
                logger.warning(
                    "Workflow metadata hydration: no TRIGGER nodes found; triggers list will be empty"
                )
            workflow["triggers"] = triggers

    async def _enhance_ai_agent_prompts_with_llm(self, workflow: dict) -> dict:
        """
        Enhance AI Agent node prompts using LLM to ensure output format matches the next node's expected input.
        Uses concurrent LLM calls for better performance.
        """
        try:
            logger.info("Enhancing AI Agent prompts with LLM assistance (concurrent)")

            connections = workflow.get("connections") or []
            nodes = workflow.get("nodes", [])

            node_map = {node.get("id"): node for node in nodes if node.get("id")}

            # Collect all AI Agent nodes that need enhancement
            enhancement_tasks = []
            ai_agent_nodes = []

            for node in nodes:
                if node.get("type") != "AI_AGENT":
                    continue

                node_id = node.get("id")
                if not node_id:
                    continue

                outgoing = [conn for conn in connections if conn.get("from_node") == node_id]

                if not outgoing:
                    continue

                next_node_id = outgoing[0].get("to_node")
                if not next_node_id or next_node_id not in node_map:
                    continue

                next_node = node_map[next_node_id]

                task = self._enhance_single_ai_agent_prompt(node, next_node, node_id, next_node_id)
                enhancement_tasks.append(task)
                ai_agent_nodes.append((node, node_id))

            if enhancement_tasks:
                # Run enhancement tasks with controlled concurrency
                max_concurrent = getattr(settings, "MAX_CONCURRENT_LLM_ENHANCEMENTS", 5)
                logger.info(
                    f"Running {len(enhancement_tasks)} LLM enhancements with max concurrency of {max_concurrent}"
                )

                # Process in batches to control concurrency
                enhanced_prompts = []
                for i in range(0, len(enhancement_tasks), max_concurrent):
                    batch = enhancement_tasks[i : i + max_concurrent]
                    batch_results = await asyncio.gather(*batch, return_exceptions=True)
                    enhanced_prompts.extend(batch_results)

                    # Small delay between batches to avoid rate limiting
                    if i + max_concurrent < len(enhancement_tasks):
                        await asyncio.sleep(0.5)

                # Apply the enhanced prompts back to the nodes
                for (node, node_id), enhanced_prompt in zip(ai_agent_nodes, enhanced_prompts):
                    if isinstance(enhanced_prompt, Exception):
                        logger.warning(
                            f"Failed to enhance prompt for node {node_id}: {enhanced_prompt}"
                        )
                        # Keep original prompt if enhancement failed
                    elif enhanced_prompt:
                        # Update the node's system prompt with LLM-enhanced version
                        if "configurations" not in node or not isinstance(
                            node["configurations"], dict
                        ):
                            node["configurations"] = {}
                        node["configurations"]["system_prompt"] = enhanced_prompt
                        logger.info(
                            f"Successfully enhanced AI Agent node '{node_id}' prompt with LLM"
                        )

            return workflow

        except Exception as e:
            logger.warning(f"Error in concurrent AI Agent prompt enhancement: {e}")
            # Fall back to non-LLM enhancement
            return self._enhance_ai_agent_prompts(workflow)

    async def _enhance_single_ai_agent_prompt(
        self, ai_node: dict, next_node: dict, ai_node_id: str, next_node_id: str
    ) -> str:
        """
        Enhance a single AI Agent's prompt using LLM to understand the next node's requirements.
        """
        try:
            # Read system prompt from configurations (parameters is deprecated)
            current_prompt = ai_node.get("configurations", {}).get("system_prompt", "")
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
                SystemMessage(
                    content="You are an expert at optimizing AI system prompts for workflow integration."
                ),
                HumanMessage(content=enhancement_prompt),
            ]

            response = await self.llm.ainvoke(messages)
            enhanced_prompt = response.content.strip()

            # Validate the enhanced prompt isn't empty or too different
            if enhanced_prompt and len(enhanced_prompt) > 20:
                logger.info(
                    f"LLM enhanced prompt for node {ai_node_id} connecting to {next_node_id}"
                )
                return enhanced_prompt
            else:
                # Fall back to simple enhancement
                format_prompt = self._generate_format_prompt_for_node(next_node)
                return self._add_format_requirements_to_prompt(
                    current_prompt, format_prompt, next_node
                )

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

            connections = workflow.get("connections") or []
            nodes = workflow.get("nodes", [])

            node_map = {node.get("id"): node for node in nodes if node.get("id")}

            # Process each AI Agent node
            for node in nodes:
                if node.get("type") != "AI_AGENT":
                    continue

                node_id = node.get("id")
                if not node_id:
                    continue

                outgoing = [conn for conn in connections if conn.get("from_node") == node_id]

                if not outgoing:
                    continue

                next_node_id = outgoing[0].get("to_node")
                if not next_node_id or next_node_id not in node_map:
                    continue

                next_node = node_map[next_node_id]

                format_prompt = self._generate_format_prompt_for_node(next_node)

                if format_prompt:
                    current_prompt = node.get("configurations", {}).get("system_prompt", "")
                    enhanced_prompt = self._add_format_requirements_to_prompt(
                        current_prompt, format_prompt, next_node
                    )

                    if "configurations" not in node or not isinstance(node["configurations"], dict):
                        node["configurations"] = {}
                    node["configurations"]["system_prompt"] = enhanced_prompt

                    logger.info(
                        f"Enhanced AI Agent node '{node_id}' prompt for connection to "
                        f"'{next_node['type']}' node '{next_node_id}'"
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
        if not node_spec and hasattr(self, "mcp_client"):
            try:
                # Query MCP for this specific node's details
                # Note: We'll use the cached specs if available, otherwise skip dynamic fetch
                # since this is called from sync context but MCP client is async
                logger.info(
                    f"Node spec for {node_key} not in cache, will use generic format prompt"
                )
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

    def _add_format_requirements_to_prompt(
        self, current_prompt: str, format_prompt: str, next_node: dict
    ) -> str:
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

    def _generate_format_from_mcp_spec(
        self, node_spec: dict, node_type: str, node_subtype: str
    ) -> str:
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
                        format_prompt += f"  // {param_desc}"

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
            "object": "{}",
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
            connections = workflow.get("connections") or []
            nodes = workflow.get("nodes", [])
            node_map = {node.get("id"): node for node in nodes if node.get("id")}

            for node in nodes:
                if node.get("type") != "AI_AGENT":
                    continue

                node_id = node.get("id")
                if not node_id:
                    continue

                system_prompt = node.get("configurations", {}).get("system_prompt", "")

                outgoing = [conn for conn in connections if conn.get("from_node") == node_id]

                if not outgoing:
                    continue

                next_node_id = outgoing[0].get("to_node")
                if not next_node_id or next_node_id not in node_map:
                    continue

                next_node = node_map[next_node_id]
                next_type = next_node.get("type")
                next_subtype = next_node.get("subtype")

                needs_json = False
                if next_type == "EXTERNAL_ACTION":
                    needs_json = True
                elif next_type == "ACTION" and next_subtype in ["HTTP_REQUEST", "SAVE_TO_DATABASE"]:
                    needs_json = True

                if not needs_json:
                    continue

                prompt_lower = system_prompt.lower()
                has_format = any(
                    keyword in prompt_lower
                    for keyword in ["json", "format", "output", "structure", "object", "api"]
                )

                if not has_format:
                    warnings.append(
                        f"AI Agent '{node_id}' connects to '{next_subtype}' but system prompt doesn't specify output format."
                    )

                if next_subtype == "GOOGLE_CALENDAR" and "calendar" not in prompt_lower:
                    warnings.append(
                        f"AI Agent '{node_id}' connects to Google Calendar but prompt doesn't mention calendar event format"
                    )
                elif (
                    next_subtype == "SLACK"
                    and "slack" not in prompt_lower
                    and "message" not in prompt_lower
                ):
                    warnings.append(
                        f"AI Agent '{node_id}' connects to Slack but prompt doesn't mention message format"
                    )

            return warnings

        except Exception as e:
            logger.error(f"Error validating AI Agent prompts: {e}")
            return warnings

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

        connections_value = workflow.get("connections")
        if connections_value is None:
            workflow["connections"] = []
        elif isinstance(connections_value, list):
            normalized_connections = []
            for index, conn in enumerate(connections_value):
                if not isinstance(conn, dict):
                    continue
                normalised = dict(conn)
                if "from_node" not in normalised and "from" in normalised:
                    normalised["from_node"] = normalised["from"]
                if "to_node" not in normalised and "to" in normalised:
                    normalised["to_node"] = normalised["to"]
                if not normalised.get("id"):
                    normalised["id"] = normalised.get("connection_id") or f"conn_{index}"
                if not normalised.get("output_key"):
                    normalised["output_key"] = normalised.get("output") or "result"
                normalized_connections.append(normalised)
            workflow["connections"] = normalized_connections
        else:
            logger.warning(
                "Workflow connections output is not a list. Expected latest workflow engine format."
            )
            workflow["connections"] = []

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

    def _validate_no_tool_memory_connections(self, workflow: Dict[str, Any]) -> List[str]:
        """Validate that TOOL/MEMORY nodes do not appear in connections.

        Returns a list of human-readable error strings for each offending connection.
        """
        errors: List[str] = []
        try:
            nodes: List[Dict[str, Any]] = workflow.get("nodes") or []
            connections: List[Dict[str, Any]] = workflow.get("connections") or []

            if not isinstance(nodes, list) or not isinstance(connections, list):
                return errors

            node_map: Dict[str, Dict[str, Any]] = {
                n.get("id"): n for n in nodes if isinstance(n, dict) and n.get("id")
            }

            def node_type(node_id: Optional[str]) -> Optional[str]:
                if not node_id:
                    return None
                node = node_map.get(node_id)
                return node.get("type") if isinstance(node, dict) else None

            for conn in connections:
                if not isinstance(conn, dict):
                    continue
                from_id = conn.get("from_node") or conn.get("from")
                to_id = conn.get("to_node") or conn.get("to")
                cid = conn.get("id") or f"{from_id or '?'}->{to_id or '?'}"

                ft = node_type(from_id)
                tt = node_type(to_id)

                if ft in {"TOOL", "MEMORY"}:
                    errors.append(
                        f"Connection '{cid}' uses {ft} node '{from_id}' as source; TOOL/MEMORY must be attached to AI_AGENT, not connected."
                    )
                if tt in {"TOOL", "MEMORY"}:
                    errors.append(
                        f"Connection '{cid}' uses {tt} node '{to_id}' as target; TOOL/MEMORY must be attached to AI_AGENT, not connected."
                    )

            return errors
        except Exception as e:
            logger.warning(f"Failed to validate TOOL/MEMORY connections: {e}")
            return errors

    def _ensure_node_descriptions(self, workflow: Dict[str, Any], intent_summary: str = "") -> None:
        """Ensure every node has a non-empty description before submission."""
        nodes = workflow.get("nodes", [])
        context = (intent_summary or workflow.get("description", "")).strip()

        for index, node in enumerate(nodes):
            if not isinstance(node, dict):
                raise ValueError(
                    f"Invalid node payload at index {index}: expected dict, got {type(node).__name__}"
                )
            description = node.get("description")
            if isinstance(description, str) and description.strip():
                continue

            node_name = (
                node.get("name")
                or node.get("subtype")
                or node.get("type")
                or node.get("id")
                or f"node-{index + 1}"
            )
            description_context = context[:200]
            if description_context:
                node[
                    "description"
                ] = f"Auto-generated node '{node_name}' supporting intent: {description_context}"
            else:
                node["description"] = f"Auto-generated node '{node_name}'"

        workflow["nodes"] = nodes

        missing_nodes = []
        for index, node in enumerate(nodes):
            node_description = node.get("description")
            if not (isinstance(node_description, str) and node_description.strip()):
                missing_nodes.append(node.get("id") or f"node-{index + 1}")

        if missing_nodes:
            raise ValueError(f"Nodes missing descriptions: {', '.join(missing_nodes)}")

    def _fail_workflow_generation(
        self,
        state: WorkflowState,
        *,
        error_message: str,
        user_message: Optional[str] = None,
    ) -> WorkflowState:
        """Mark the current workflow state as failed and record messaging."""

        state["stage"] = WorkflowStage.FAILED
        state["workflow_generation_failed"] = True
        state["final_error_message"] = error_message

        if user_message:
            self._add_conversation(state, "assistant", user_message)

        # Ensure there is no stale workflow payload that downstream nodes could use
        state.pop("current_workflow", None)

        return state

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

        elif stage == WorkflowStage.CONVERSION_GENERATION:
            logger.info("Routing to conversion generation stage")
            return "conversion_generation"

        elif stage == WorkflowStage.WORKFLOW_GENERATION:
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
        """
        logger.info("Processing optimized workflow generation node")

        # Set stage to WORKFLOW_GENERATION
        state["stage"] = WorkflowStage.WORKFLOW_GENERATION

        try:
            intent_summary = get_intent_summary(state)
            conversation_context = self._get_conversation_context(state)

            # Check if we're coming from previous generation failures
            creation_error = state.get("workflow_creation_error")  # Field for creation failures

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
                error_message = (
                    "Empty workflow response from LLM after reaching the maximum tool iterations"
                )
                logger.error(error_message)
                failure_message = (
                    "I wasn't able to generate a workflow because the model returned an empty "
                    "response after several attempts. Please adjust the requirements or try again."
                )
                self._fail_workflow_generation(
                    state,
                    error_message=error_message,
                    user_message=failure_message,
                )
                return state
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

                    # DEBUG: Log raw LLM output to check if connections are generated
                    raw_connections = workflow.get("connections", [])
                    logger.info(f"🔍 RAW LLM OUTPUT - Connections count: {len(raw_connections)}")
                    if raw_connections:
                        logger.info(f"🔍 RAW LLM OUTPUT - Connections: {raw_connections}")
                    else:
                        logger.warning("🚨 RAW LLM OUTPUT - NO CONNECTIONS GENERATED BY LLM!")

                    # Post-process the workflow to add missing required fields
                    workflow = self._normalize_workflow_structure(workflow)

                    # DEBUG: Log connections after normalization
                    normalized_connections = workflow.get("connections", [])
                    logger.info(
                        f"🔧 AFTER NORMALIZATION - Connections count: {len(normalized_connections)}"
                    )
                    if len(raw_connections) != len(normalized_connections):
                        logger.error(
                            f"🚨 CONNECTIONS LOST DURING NORMALIZATION! Before: {len(raw_connections)}, After: {len(normalized_connections)}"
                        )

                    # Pre-fetch node specs for connected nodes
                    await self._prefetch_node_specs_for_workflow(workflow)
                    await self._hydrate_nodes_from_specs(workflow)

                    # Validate that TOOL/MEMORY nodes are not used in connections
                    invalid_conn_errors = self._validate_no_tool_memory_connections(workflow)
                    if invalid_conn_errors:
                        error_message = (
                            "Invalid workflow: TOOL and MEMORY nodes must be attached to AI_AGENT via 'attached_nodes', not connected.\n"
                            + "\n".join(invalid_conn_errors)
                        )
                        logger.error(error_message)
                        failure_message = (
                            "The generated workflow connected TOOL/MEMORY nodes in the dataflow. "
                            "Please regenerate the workflow and attach TOOL/MEMORY node IDs to the AI agent's 'attached_nodes' field instead of connecting them."
                        )
                        self._fail_workflow_generation(
                            state,
                            error_message=error_message,
                            user_message=failure_message,
                        )
                        return state

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

                    # Skip iterative validation - single pass generation for better performance
                    logger.info(
                        "Single-pass workflow generation completed - skipping validation rounds"
                    )

                    logger.info(
                        "Successfully generated workflow using MCP tools, workflow: %s", workflow
                    )

                except json.JSONDecodeError as e:
                    error_message = "Failed to parse workflow JSON returned by the model"
                    logger.error(f"{error_message}: {e}, response was: {workflow_json[:500]}")
                    failure_message = (
                        "I attempted to generate the workflow but the response format was invalid. "
                        "Please retry or provide additional guidance."
                    )
                    self._fail_workflow_generation(
                        state,
                        error_message=error_message,
                        user_message=failure_message,
                    )
                    return state

            # Store latest workflow and advance to conversion generation stage
            state["current_workflow"] = workflow
            state["stage"] = WorkflowStage.CONVERSION_GENERATION

            self._ensure_workflow_metadata(workflow, state)

            # Clear previous errors so conversion stage starts clean
            if "workflow_creation_error" in state:
                del state["workflow_creation_error"]

            logger.info("Workflow JSON prepared; proceeding to conversion generation stage")
            return state

        except WorkflowGenerationError:
            raise
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

    async def conversion_generation_node(self, state: WorkflowState) -> WorkflowState:
        """Generate conversion functions and persist workflow in the engine."""
        from workflow_agent.services.workflow_engine_client import WorkflowEngineClient

        logger.info("Processing conversion generation node")
        state["stage"] = WorkflowStage.CONVERSION_GENERATION

        workflow = state.get("current_workflow")
        if not workflow:
            error_msg = "No workflow available to generate conversion functions."
            logger.error(error_msg)
            state["workflow_creation_error"] = error_msg
            state["stage"] = WorkflowStage.FAILED
            self._add_conversation(
                state,
                "assistant",
                "I attempted to finalise the workflow but the configuration was missing. Please regenerate the workflow before trying again.",
            )
            return state

        intent_summary = state.get("intent_summary", "")
        generator = ConversionFunctionGenerator(
            prompt_engine=self.prompt_engine,
            llm=self.llm,
            spec_fetcher=self._get_or_fetch_node_spec,
            logger=logger,
        )

        try:
            await self._prefetch_node_specs_for_workflow(workflow)
            workflow = await generator.populate(workflow, intent_summary=intent_summary)
            self._ensure_node_descriptions(workflow, intent_summary=intent_summary)
            state["current_workflow"] = workflow
        except Exception as exc:
            logger.error("Failed to generate conversion functions", exc_info=True)
            state["workflow_creation_error"] = str(exc)
            state["stage"] = WorkflowStage.FAILED
            self._add_conversation(
                state,
                "assistant",
                "I ran into an error while preparing data mappings between nodes. Please try regenerating the workflow.",
            )
            return state

        engine_client = WorkflowEngineClient()
        user_id = state.get("user_id", "test_user")
        session_id = state.get("session_id")
        workflow_context = state.get("workflow_context", {})
        workflow_mode = workflow_context.get("origin", "create")

        logger.info("Creating workflow in workflow_engine after conversion generation")
        creation_result = await engine_client.create_workflow(workflow, user_id, session_id)

        if creation_result.get("success", True) and creation_result.get("workflow", {}).get("id"):
            workflow_id = creation_result["workflow"]["id"]
            state["workflow_id"] = workflow_id
            state["workflow_creation_result"] = creation_result
            state.pop("workflow_creation_error", None)

            workflow_name = workflow.get("name", "Workflow")
            workflow_description = workflow.get("description", "")
            node_count = len(workflow.get("nodes", []))
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
            state["stage"] = WorkflowStage.WORKFLOW_GENERATION
            return state

        creation_error = creation_result.get("error", "Unknown creation error")
        logger.error("Workflow creation failed after conversion generation: %s", creation_error)
        state["workflow_creation_error"] = creation_error
        state["stage"] = WorkflowStage.FAILED

        self._add_conversation(
            state,
            "assistant",
            f"I generated the workflow but encountered an error while saving it. Error: {creation_error}.\n\nHere is the workflow JSON so you can review it:\n\n```json\n{json.dumps(workflow, indent=2)}\n```",
        )
        return state

    async def _get_or_fetch_node_spec(self, node: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        node_type = node.get("type")
        node_subtype = node.get("subtype")
        if not node_type or not node_subtype:
            return None

        cache_key = f"{node_type}:{node_subtype}"
        if cache_key in self.node_specs_cache:
            return self.node_specs_cache[cache_key]

        if not getattr(self, "mcp_client", None):
            return None

        try:
            result = await self.mcp_client.call_tool(
                "get_node_details",
                {
                    "nodes": [{"node_type": node_type, "subtype": node_subtype}],
                    "include_examples": True,
                    "include_schemas": True,
                },
            )

            nodes_list = []
            if isinstance(result, dict):
                if "nodes" in result:
                    nodes_list = result["nodes"]
                elif "result" in result and isinstance(result["result"], dict):
                    nodes_list = result["result"].get("nodes", [])
            elif isinstance(result, list):
                nodes_list = result

            if nodes_list:
                spec = nodes_list[0]
                if spec and "error" not in spec:
                    self.node_specs_cache[cache_key] = spec
                    return spec
        except Exception as e:
            logger.warning(f"Failed to fetch MCP node spec for {node_type}:{node_subtype}: {e}")

        return self.node_specs_cache.get(cache_key)

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
                has_new_tool_calls = False
                for tool_call in response.tool_calls:
                    tool_name = getattr(tool_call, "name", tool_call.get("name", ""))
                    tool_args = getattr(tool_call, "args", tool_call.get("args", {}))

                    # Create a signature for this tool call to detect duplicates
                    tool_signature = f"{tool_name}:{json.dumps(tool_args, sort_keys=True)}"

                    # Skip if this exact tool call was already made
                    if tool_signature in tool_call_history:
                        logger.warning(f"Skipping duplicate tool call: {tool_name} with same args")
                        current_messages.append(
                            HumanMessage(
                                content=(
                                    f"Tool `{tool_name}` was already called with the same arguments. "
                                    "Reuse the earlier response and proceed to build the workflow JSON."
                                )
                            )
                        )
                        continue

                    has_new_tool_calls = True
                    tool_call_history.append(tool_signature)
                    logger.info(f"Processing tool call: {tool_name}")
                    result = await self.mcp_client.call_tool(tool_name, tool_args)
                    logger.info(f"🔍 Raw MCP result for {tool_name}: {result}")

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
                    logger.info(
                        f"💡 MCP response for {tool_name}: original={original_size} chars, filtered={len(result_str)} chars"
                    )
                    logger.info(f"📤 Sending to LLM: {result_str[:500]}...")

                    # Add explicit next step guidance for get_node_types
                    if tool_name == "get_node_types":
                        current_messages.append(
                            HumanMessage(
                                content=f"Tool result for {tool_name}:\n{result_str}\n\n**Next step**: Now call get_node_details with the specific nodes you need (e.g., TRIGGER:SLACK, AI_AGENT:OPENAI_CHATGPT, EXTERNAL_ACTION:NOTION) to get their full specifications before generating the workflow JSON."
                            )
                        )
                    else:
                        current_messages.append(
                            HumanMessage(content=f"Tool result for {tool_name}:\n{result_str}")
                        )

                # Break the loop if all tool calls were duplicates
                if not has_new_tool_calls:
                    logger.warning("All tool calls were duplicates, breaking out of loop")
                    break

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


class ConversionFunctionGenerator:
    """Generate conversion functions for workflow connections in a minimal, testable way."""

    def __init__(
        self,
        *,
        prompt_engine,
        llm,
        spec_fetcher,
        logger: logging.Logger,
    ) -> None:
        self.prompt_engine = prompt_engine
        self.llm = llm
        self.spec_fetcher = spec_fetcher
        self.logger = logger

    async def populate(
        self, workflow: Dict[str, Any], *, intent_summary: str = ""
    ) -> Dict[str, Any]:
        nodes = {node.get("id"): node for node in workflow.get("nodes", []) if node.get("id")}
        connections = workflow.get("connections") or []

        semaphore = asyncio.Semaphore(getattr(settings, "CONVERSION_GENERATION_MAX_CONCURRENCY", 4))

        tasks = []
        processed_connections: List[Dict[str, Any]] = []

        for index, connection in enumerate(connections):
            if not self._normalize_connection(connection, index):
                continue
            tasks.append(
                self._generate_for_connection(
                    connection,
                    nodes,
                    intent_summary,
                    semaphore,
                )
            )
            processed_connections.append(connection)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for connection, result in zip(processed_connections, results):
            if isinstance(result, Exception):
                self.logger.warning(
                    "Conversion generation failed for %s → %s: %s",
                    connection.get("from_node"),
                    connection.get("to_node"),
                    result,
                )
                code = connection.get("conversion_function") or DEFAULT_CONVERSION_FUNCTION
            else:
                code = (
                    result or connection.get("conversion_function") or DEFAULT_CONVERSION_FUNCTION
                )

            connection["conversion_function"] = code

        workflow["connections"] = connections
        return workflow

    def _normalize_connection(self, connection: Dict[str, Any], index: int) -> bool:
        if not connection.get("id"):
            connection["id"] = f"conn_{index}"

        if not connection.get("from_node") and connection.get("from"):
            connection["from_node"] = connection["from"]
        if not connection.get("to_node") and connection.get("to"):
            connection["to_node"] = connection["to"]

        if not connection.get("from_node") or not connection.get("to_node"):
            self.logger.warning(
                "Skipping conversion generation for connection %s due to missing endpoints",
                connection.get("id"),
            )
            return False
        return True

    async def _generate_for_connection(
        self,
        connection: Dict[str, Any],
        nodes: Dict[str, Dict[str, Any]],
        intent_summary: str,
        semaphore: asyncio.Semaphore,
    ) -> Optional[str]:
        return await self._generate_code(
            connection,
            nodes,
            intent_summary,
            semaphore,
        )

    async def _generate_code(
        self,
        connection: Dict[str, Any],
        nodes: Dict[str, Dict[str, Any]],
        intent_summary: str,
        semaphore: Optional[asyncio.Semaphore] = None,
    ) -> Optional[str]:
        source = nodes.get(connection["from_node"])
        target = nodes.get(connection["to_node"])

        if not source or not target:
            self.logger.warning(
                "Skipping conversion generation for connection %s — unknown node references",
                connection.get("id"),
            )
            return connection.get("conversion_function")

        source_spec = await self.spec_fetcher(source)
        target_spec = await self.spec_fetcher(target)

        source_context = self._build_node_summary(source, source_spec)
        target_context = self._build_node_summary(target, target_spec, include_inputs=True)

        prompt = await self.prompt_engine.render_prompt(
            "conversion_generation",
            source_context=source_context,
            target_context=target_context,
            connection_info={
                "connection_id": connection.get("id"),
                "from_node": connection.get("from_node"),
                "to_node": connection.get("to_node"),
                "output_key": connection.get("output_key", "result"),
                "existing_conversion_function": connection.get("conversion_function"),
            },
            intent_summary=intent_summary,
        )

        system_prompt = (
            "You create Python conversion functions for workflow automation. "
            "Return only the function code, keep the logic minimal (simple field access and dictionary construction), "
            "and follow the provided guidelines exactly."
        )

        async def _invoke_llm():
            return await self.llm.ainvoke(
                [SystemMessage(content=system_prompt), HumanMessage(content=prompt)]
            )

        if semaphore:
            await semaphore.acquire()
            try:
                response = await _invoke_llm()
            finally:
                semaphore.release()
        else:
            response = await _invoke_llm()

        code = self._extract_code(getattr(response, "content", ""))
        if not self._is_valid(code):
            self.logger.warning(
                "Generated conversion function invalid for connection %s; using fallback",
                connection.get("id"),
            )
            return None

        return code.strip()

    def _build_node_summary(
        self,
        node: Dict[str, Any],
        spec: Optional[Dict[str, Any]],
        *,
        include_inputs: bool = False,
    ) -> Dict[str, Any]:
        summary: Dict[str, Any] = {
            "id": node.get("id"),
            "name": node.get("name"),
            "type": node.get("type"),
            "subtype": node.get("subtype"),
            "description": node.get("description") or (spec.get("description") if spec else ""),
            "configurations": self._compact_dict(node.get("configurations", {})),
        }

        if include_inputs:
            summary["expected_inputs"] = self._summarize_parameters(spec)
        else:
            summary["sample_outputs"] = list((node.get("output_params") or {}).keys())[:6]

        if spec and spec.get("examples"):
            summary["examples"] = spec["examples"][:1]

        return summary

    def _summarize_parameters(self, spec: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not spec:
            return []
        params = []
        for param in (spec.get("parameters") or [])[:6]:
            if isinstance(param, dict):
                params.append(
                    {
                        "name": param.get("name"),
                        "type": param.get("type"),
                        "required": param.get("required", False),
                    }
                )
        return params

    def _compact_dict(self, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        compact = {}
        for key, val in value.items():
            if isinstance(val, (str, int, float, bool)):
                compact[key] = val
            elif isinstance(val, list) and len(val) <= 5:
                compact[key] = val
            elif isinstance(val, dict) and len(val) <= 5:
                compact[key] = val
        return compact

    def _extract_code(self, content: Any) -> str:
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    parts.append(item["text"])
                elif isinstance(item, str):
                    parts.append(item)
            content = "".join(parts)
        if not isinstance(content, str):
            content = str(content or "")

        code = content.strip()
        if code.startswith("```"):
            sections = code.split("```")
            if len(sections) >= 2:
                code = sections[1]
        code = code.strip()
        if code.lower().startswith("python"):
            code = code[6:].strip()
        if code.startswith("lambda"):
            code = self._lambda_to_def(code)
        return code.strip()

    def _is_valid(self, code: str) -> bool:
        cleaned = code.strip()
        return cleaned.startswith("def convert") and "return" in cleaned

    def _lambda_to_def(self, lambda_code: str) -> str:
        body = lambda_code.strip()
        if not body.startswith("lambda"):
            return body
        try:
            args, expression = body[len("lambda") :].split(":", 1)
        except ValueError:
            return body
        args = args.strip() or "input_data"
        expression = expression.strip() or "input_data"
        if "," in args:
            args = "input_data"
        return "\n".join(
            [
                f"def convert({args}) -> Dict[str, Any]:",
                f"    return {expression}",
            ]
        )
