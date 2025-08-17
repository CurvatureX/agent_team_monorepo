"""
Test Data Generator for Workflow Execution
Analyzes workflow structure and generates appropriate test data using LLM
"""

import json
import logging
from typing import Any, Dict, List, Optional

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from workflow_agent.core.config import settings

# Import shared enums for consistent node type handling
try:
    from shared.models.node_enums import (
        ActionSubtype,
        AIAgentSubtype,
        ExternalActionSubtype,
        NodeType,
        TriggerSubtype,
    )
except ImportError:
    # Fallback if shared models not available
    NodeType = None
    TriggerSubtype = None
    AIAgentSubtype = None
    ActionSubtype = None
    ExternalActionSubtype = None

logger = logging.getLogger(__name__)


class WorkflowDataGenerator:
    """Generates test data for workflow execution"""

    def __init__(self):
        self.llm = self._setup_llm()

    def _setup_llm(self):
        """Setup the language model"""
        if settings.DEFAULT_MODEL_PROVIDER == "openai":
            return ChatOpenAI(
                model=settings.DEFAULT_MODEL_NAME,
                api_key=settings.OPENAI_API_KEY,
                temperature=0.3,  # Some creativity for test data
            )
        else:
            # Fallback to OpenAI for JSON generation
            return ChatOpenAI(model="gpt-4.1", api_key=settings.OPENAI_API_KEY, temperature=0.3)

    async def generate_test_data(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate test data based on workflow structure

        Args:
            workflow_data: The workflow JSON structure

        Returns:
            Generated test data for workflow execution
        """
        try:
            # Analyze workflow to understand required inputs
            analysis = self._analyze_workflow_inputs(workflow_data)

            # Generate test data using LLM
            system_prompt = self._create_test_data_prompt()
            user_prompt = self._create_user_prompt(workflow_data, analysis)

            messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

            # Log the model being used
            logger.info(f"Workflow data generator using model: {settings.DEFAULT_MODEL_NAME}")

            # Try to use response_format for JSON if OpenAI
            if settings.DEFAULT_MODEL_PROVIDER == "openai":
                try:
                    response = await self.llm.ainvoke(
                        messages, response_format={"type": "json_object"}
                    )
                    logger.info("Successfully used response_format for JSON output")
                except Exception as format_error:
                    if "response_format" in str(format_error):
                        logger.warning(
                            f"Model doesn't support response_format, falling back: {format_error}"
                        )
                        messages.append(
                            HumanMessage(content="Please respond in valid JSON format.")
                        )
                        response = await self.llm.ainvoke(messages)
                    else:
                        raise
            else:
                response = await self.llm.ainvoke(messages)

            # Parse the response
            response_text = (
                response.content if isinstance(response.content, str) else str(response.content)
            )

            # Clean and parse JSON
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]
            elif response_text.startswith("```"):
                response_text = response_text[3:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]

            test_data = json.loads(response_text.strip())

            logger.info("Generated test data for workflow execution")
            return test_data.get("trigger_data", {})

        except Exception as e:
            logger.error(f"Error generating test data: {str(e)}")
            # Return minimal default test data
            return self._generate_default_test_data(workflow_data)

    def _extract_template_variables(self, workflow_data: Dict[str, Any]) -> List[str]:
        """
        Extract all template variables from the workflow
        
        Args:
            workflow_data: The workflow JSON structure
            
        Returns:
            List of unique template variable names
        """
        import re
        template_vars = set()
        
        # Pattern to match template variables like {{trigger.xxx}} or {{payload.xxx}}
        pattern = r'\{\{([^}]+)\}\}'
        
        def extract_from_value(value):
            """Recursively extract template variables from any value"""
            if isinstance(value, str):
                matches = re.findall(pattern, value)
                for match in matches:
                    # Extract the variable name (e.g., "trigger.issue_number" -> "issue_number")
                    var_path = match.strip()
                    if '.' in var_path:
                        # Get the last part after the dot
                        var_name = var_path.split('.')[-1]
                        template_vars.add(var_name)
                    else:
                        template_vars.add(var_path)
            elif isinstance(value, dict):
                for v in value.values():
                    extract_from_value(v)
            elif isinstance(value, list):
                for item in value:
                    extract_from_value(item)
        
        # Extract from all nodes
        nodes = workflow_data.get("nodes", [])
        for node in nodes:
            extract_from_value(node.get("parameters", {}))
        
        return list(template_vars)
    
    def _generate_smart_test_value(self, var_name: str) -> Any:
        """
        Generate smart test data based on variable name
        
        Args:
            var_name: The variable name
            
        Returns:
            A reasonable test value for the variable
        """
        var_lower = var_name.lower()
        
        # Number/ID patterns
        if any(keyword in var_lower for keyword in ['number', 'id', 'count', 'size', 'port']):
            if 'port' in var_lower:
                return 8080
            elif 'count' in var_lower or 'size' in var_lower:
                return 5
            else:
                return 123
        
        # Title/Name patterns
        elif any(keyword in var_lower for keyword in ['title', 'name', 'subject']):
            if 'issue' in var_lower:
                return "Bug: Application crashes on startup"
            elif 'pr' in var_lower or 'pull' in var_lower:
                return "Feature: Add user authentication"
            else:
                return "Example Title"
        
        # Body/Content patterns
        elif any(keyword in var_lower for keyword in ['body', 'content', 'message', 'description']):
            return "This is an example content. It contains detailed information about the topic."
        
        # Time/Date patterns
        elif any(keyword in var_lower for keyword in ['time', 'date', 'timestamp', 'created_at', 'updated_at']):
            return "2025-01-15T10:00:00Z"
        
        # User/Author patterns
        elif any(keyword in var_lower for keyword in ['user', 'author', 'owner', 'assignee']):
            return "testuser"
        
        # Email patterns
        elif 'email' in var_lower or 'mail' in var_lower:
            return "user@example.com"
        
        # URL patterns
        elif 'url' in var_lower or 'link' in var_lower or 'webhook' in var_lower:
            return "https://api.example.com/webhook"
        
        # Repository patterns
        elif 'repository' in var_lower or 'repo' in var_lower:
            return "myorg/myrepo"
        
        # Boolean patterns
        elif any(keyword in var_lower for keyword in ['is_', 'has_', 'should_', 'enable', 'disable', 'active']):
            return True
        
        # List patterns
        elif any(keyword in var_lower for keyword in ['labels', 'tags', 'items', 'list']):
            return ["item1", "item2", "item3"]
        
        # Default fallback
        else:
            return f"example_{var_name}"

    def _analyze_workflow_inputs(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze workflow to identify required inputs

        Args:
            workflow_data: The workflow JSON structure

        Returns:
            Analysis of required inputs
        """
        analysis = {
            "trigger_inputs": [], 
            "node_parameters": [], 
            "data_dependencies": [],
            "template_variables": []  # New: track template variables
        }

        nodes = workflow_data.get("nodes", [])
        
        # Extract all template variables
        template_vars = self._extract_template_variables(workflow_data)
        analysis["template_variables"] = template_vars

        for node in nodes:
            node_type = node.get("type", "")
            subtype = node.get("subtype", "")
            node_id = node.get("id", "")
            parameters = node.get("parameters", {})

            # Identify trigger nodes using enum values only - no legacy support
            is_trigger = False
            if NodeType:
                # Use enum-based checking only
                is_trigger = node_type == NodeType.TRIGGER.value
            else:
                raise ImportError("NodeType enums are required - no legacy support")

            if is_trigger:
                analysis["trigger_inputs"].append(
                    {"node_id": node_id, "type": node_type, "parameters": parameters}
                )

            # Identify nodes that need external data using enum values only - no legacy support
            needs_external_data = False
            if NodeType:
                # Use enum-based checking only
                needs_external_data = (
                    node_type == NodeType.AI_AGENT.value
                    or node_type == NodeType.EXTERNAL_ACTION.value
                )
            else:
                raise ImportError("NodeType enums are required - no legacy support")

            if needs_external_data:
                for param_key, param_value in parameters.items():
                    if isinstance(param_value, str) and "{{" in param_value:
                        # This parameter expects input data
                        analysis["data_dependencies"].append(
                            {"node_id": node_id, "parameter": param_key, "reference": param_value}
                        )

            # Collect all parameter requirements
            if parameters:
                analysis["node_parameters"].append(
                    {"node_id": node_id, "type": node_type, "parameters": list(parameters.keys())}
                )

        return analysis

    def _create_test_data_prompt(self) -> str:
        """Create system prompt for test data generation"""
        return """You are a test data generator for workflow execution.

Your task is to generate realistic test data that will help validate the workflow execution.

## Guidelines:
1. Generate data that matches the expected input types
2. Use realistic values that would occur in actual usage
3. Include edge cases where appropriate
4. Ensure all required fields are populated
5. Keep data reasonable in size (avoid huge arrays or strings)

## Output Format:
Return a JSON object with this structure:
{
  "trigger_data": {
    // ALL VALUES MUST BE STRINGS - this is critical for API compatibility
    "field_name": "value",
    "another_field": "123",  // Numbers as strings
    "boolean_field": "true",  // Booleans as strings ("true" or "false")
    "array_field": "[\"item1\", \"item2\"]",  // Arrays as JSON strings
    "object_field": "{\"key\": \"value\"}"  // Objects as JSON strings
  },
  "test_scenario": "Description of what this test data represents",
  "expected_behavior": "What should happen with this data"
}

CRITICAL RULES:
- ALL values in trigger_data MUST be strings
- Numbers: Convert to string (123 → "123")
- Booleans: Convert to string (true → "true", false → "false")
- Arrays/Objects: Convert to JSON string using JSON.stringify format
- null/undefined: Convert to empty string ""

Focus on creating data that will exercise the main path through the workflow."""

    def _create_user_prompt(self, workflow_data: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """Create user prompt with workflow context"""

        # Extract workflow description
        workflow_name = workflow_data.get("name", "Unnamed Workflow")
        workflow_description = workflow_data.get("description", "No description")

        # Build prompt
        prompt = f"""Generate test data for this workflow:

## Workflow Information:
- Name: {workflow_name}
- Description: {workflow_description}

## Workflow Structure:
{json.dumps(workflow_data, indent=2)[:2000]}  # Truncate if too long

## Input Analysis:
- Trigger Inputs: {json.dumps(analysis['trigger_inputs'], indent=2) if analysis['trigger_inputs'] else 'None identified'}
- Data Dependencies: {json.dumps(analysis['data_dependencies'], indent=2) if analysis['data_dependencies'] else 'None identified'}
- Template Variables Found: {json.dumps(analysis['template_variables'], indent=2) if analysis['template_variables'] else 'None identified'}

## Requirements:
1. Generate test data for ALL template variables found (e.g., {{{{trigger.issue_number}}}})
2. Use realistic values based on variable names:
   - *_number/*_id → integers (e.g., 123)
   - *_title/*_name → descriptive strings
   - timestamps → ISO 8601 format
   - booleans → true/false
3. Ensure the test data allows the workflow to execute successfully

Return ONLY valid JSON with the trigger_data field containing the test inputs.
The trigger_data should have keys matching the template variable names (without the 'trigger.' prefix)."""

        return prompt

    def _generate_default_test_data(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate minimal default test data as fallback
        Now enhanced with smart data generation based on template variables

        Args:
            workflow_data: The workflow JSON structure

        Returns:
            Smart test data based on template variables
        """
        # Extract template variables from workflow
        template_vars = self._extract_template_variables(workflow_data)
        
        # Generate smart test data for each template variable
        default_data = {}
        for var_name in template_vars:
            default_data[var_name] = self._generate_smart_test_value(var_name)
        
        # Add some basic defaults if no template variables found
        if not default_data:
            default_data = {
                "test_input": "Sample test data",
                "timestamp": "2024-01-01T00:00:00Z",
                "user_id": "test_user",
                "test_mode": "true",  # Boolean as string
            }
            
            # Try to add some context-specific defaults
            workflow_name = workflow_data.get("name", "").lower()
            
            if "email" in workflow_name:
                default_data["email"] = "test@example.com"
                default_data["subject"] = "Test Email"
                default_data["body"] = "This is a test email body"
            elif "slack" in workflow_name:
                default_data["channel"] = "#general"
                default_data["message"] = "Test message"
            elif "github" in workflow_name:
                default_data["issue_number"] = 123
                default_data["issue_title"] = "Test Issue"
                default_data["repository"] = "myorg/myrepo"
            elif "data" in workflow_name or "process" in workflow_name:
                # Arrays and objects must be JSON strings
                default_data["data"] = json.dumps(
                    [{"id": 1, "value": "test1"}, {"id": 2, "value": "test2"}]
                )

        # Ensure all values are strings where needed (for workflow engine compatibility)
        stringified_data = {}
        for key, value in default_data.items():
            if isinstance(value, bool):
                stringified_data[key] = "true" if value else "false"
            elif isinstance(value, (int, float)):
                stringified_data[key] = str(value)
            elif isinstance(value, (dict, list)):
                stringified_data[key] = json.dumps(value)
            elif value is None:
                stringified_data[key] = ""
            else:
                stringified_data[key] = str(value)
        
        logger.info(f"Generated smart test data for {len(template_vars)} template variables")
        return stringified_data
