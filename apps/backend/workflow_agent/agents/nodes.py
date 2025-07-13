"""
LangGraph nodes for Workflow Agent
"""

import asyncio
import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

import structlog
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

# Add the backend path to sys.path to import shared modules
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

from agents.state import AgentState, WorkflowGenerationState
from shared.prompts.loader import PromptLoader

from core.config import settings
from core.models import ConnectionsMap, Node, NodeType, Position, Workflow

logger = structlog.get_logger()


class WorkflowAgentNodes:
    """LangGraph nodes for workflow generation"""

    def __init__(self):
        self.llm = self._setup_llm()
        self.node_templates = self._load_node_templates()
        self.prompt_loader = PromptLoader()

    def _initialize_state_defaults(self, state: AgentState) -> AgentState:
        """Initialize state with default values for missing optional fields"""
        defaults = {
            "workflow_errors": [],
            "current_step": "analyze_requirement",
            "iteration_count": 0,
            "max_iterations": 10,
            "should_continue": True,
            "context": {},
            "user_preferences": {},
            "missing_info": [],
            "workflow_suggestions": [],
            "messages": [],
            "conversation_history": [],
            "questions_asked": [],
            "collected_info": {},
            "changes_made": [],
        }

        for key, default_value in defaults.items():
            if key not in state:
                state[key] = default_value

        return state

    def _setup_llm(self):
        """Setup the language model based on configuration"""
        if settings.DEFAULT_MODEL_PROVIDER == "openai":
            return ChatOpenAI(
                model=settings.DEFAULT_MODEL_NAME, api_key=settings.OPENAI_API_KEY, temperature=0.1
            )
        elif settings.DEFAULT_MODEL_PROVIDER == "anthropic":
            return ChatAnthropic(
                model=settings.DEFAULT_MODEL_NAME,
                api_key=settings.ANTHROPIC_API_KEY,
                temperature=0.1,
            )
        else:
            raise ValueError(f"Unsupported model provider: {settings.DEFAULT_MODEL_PROVIDER}")

    def _load_node_templates(self) -> Dict[str, Any]:
        """Load node templates for workflow generation"""
        return {
            "trigger": {
                "slack_trigger": {
                    "parameters": {
                        "channel": "#general",
                        "allowedUsers": [],
                        "triggerPhrase": "",
                        "autoReply": True,
                    }
                },
                "webhook_trigger": {
                    "parameters": {
                        "httpMethod": "POST",
                        "path": "/webhook",
                        "authentication": "none",
                    }
                },
                "cron_trigger": {
                    "parameters": {"cron_expression": "0 9 * * MON", "timezone": "UTC"}
                },
            },
            "ai_agent": {
                "router_agent": {
                    "parameters": {
                        "agent_type": "router",
                        "model_provider": "openai",
                        "model_name": "gpt-4",
                        "temperature": 0.1,
                    }
                },
                "task_analyzer": {
                    "parameters": {
                        "agent_type": "taskAnalyzer",
                        "model_provider": "openai",
                        "model_name": "gpt-4",
                        "temperature": 0.2,
                    }
                },
            },
            "external_action": {
                "google_calendar": {
                    "parameters": {
                        "action_type": "create_event",
                        "calendar_id": "primary",
                        "timezone": "UTC",
                    }
                },
                "slack_notification": {
                    "parameters": {"channel": "#notifications", "asUser": False}
                },
            },
        }

    async def analyze_requirement(self, state: AgentState) -> AgentState:
        """Analyze user requirements and extract key information"""

        # Initialize missing fields with defaults
        # Use user_input instead of description as that's what's in the state
        if "user_input" not in state:
            raise ValueError("User input is required to analyze requirements")

        state = self._initialize_state_defaults(state)
        logger.info("Analyzing user requirements", description=state["user_input"])

        # Use the prompt loader to get system and user prompts
        system_prompt, user_prompt = await asyncio.to_thread(
            self.prompt_loader.get_system_and_user_prompts,
            "analyze_requirement",
            description=state["user_input"],
        )

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

        try:
            response = await self.llm.ainvoke(messages)

            # Parse the response
            try:
                analysis = json.loads(response.content)
            except json.JSONDecodeError:
                # Fallback if response is not valid JSON
                analysis = {
                    "triggers": ["manual"],
                    "main_operations": ["data_processing"],
                    "data_flow": ["user_input"],
                    "integrations": [],
                    "human_intervention": [],
                }

            state["requirements"] = analysis
            state["parsed_intent"] = {
                "confidence": 0.8,
                "category": "automation",
                "complexity": "medium",
            }
            state["current_step"] = "plan_generation"

            logger.info("Requirements analyzed successfully", requirements=analysis)

        except Exception as e:
            logger.error("Failed to analyze requirements", error=str(e))
            if "workflow_errors" not in state:
                state["workflow_errors"] = []
            state["workflow_errors"].append(f"Failed to analyze requirements: {str(e)}")
            state["current_step"] = "error"

        return state

    async def generate_plan(self, state: AgentState) -> AgentState:
        """Generate a high-level plan for the workflow"""
        logger.info("Generating workflow plan")

        requirements = state.get("requirements", {})

        # Use the prompt loader to get system and user prompts
        system_prompt, user_prompt = await asyncio.to_thread(
            self.prompt_loader.get_system_and_user_prompts,
            "generate_plan",
            requirements=requirements,
        )

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

        try:
            response = await self.llm.ainvoke(messages)

            try:
                plan = json.loads(response.content)
            except json.JSONDecodeError:
                plan = {
                    "nodes": [
                        {"type": "trigger", "subtype": "manual", "name": "Start"},
                        {"type": "action", "subtype": "data_processing", "name": "Process Data"},
                        {
                            "type": "external_action",
                            "subtype": "notification",
                            "name": "Send Result",
                        },
                    ],
                    "connections": [
                        {"from": "Start", "to": "Process Data"},
                        {"from": "Process Data", "to": "Send Result"},
                    ],
                    "error_handling": "stop_on_error",
                }

            state["current_plan"] = plan
            state["current_step"] = "check_knowledge"

            logger.info("Plan generated successfully", plan=plan)

        except Exception as e:
            logger.error("Failed to generate plan", error=str(e))
            if "workflow_errors" not in state:
                state["workflow_errors"] = []
            state["workflow_errors"].append(f"Failed to generate plan: {str(e)}")
            state["current_step"] = "error"

        return state

    async def check_knowledge(self, state: AgentState) -> AgentState:
        """Check if we have enough information to proceed"""
        logger.info("Checking knowledge completeness")

        plan = state.get("current_plan", {})
        context = state.get("context", {})

        # Simple knowledge check - in production this would be more sophisticated
        missing_info = []

        # Check for integration requirements
        nodes = plan.get("nodes", []) if plan else []
        for node in nodes:
            if node.get("type") == "external_action":
                subtype = node.get("subtype", "")
                if subtype in ["google_calendar", "slack", "email"] and not context.get(
                    f"{subtype}_credentials"
                ):
                    missing_info.append(f"需要{subtype}的认证信息")
                if subtype == "google_calendar" and not context.get("calendar_id"):
                    missing_info.append("需要指定Google Calendar的日历ID")

        state["missing_info"] = missing_info

        if missing_info:
            state["current_step"] = "ask_questions"
        else:
            state["current_step"] = "generate_workflow"

        logger.info("Knowledge check completed", missing_info=missing_info)
        return state

    async def generate_workflow(self, state: AgentState) -> AgentState:
        """Generate the complete workflow JSON"""
        logger.info("Generating complete workflow")

        plan = state.get("current_plan", {})
        context = state.get("context", {})

        try:
            # Generate workflow ID and metadata
            workflow_id = f"workflow-{uuid.uuid4().hex[:8]}"
            current_time = int(time.time())

            # Generate nodes
            nodes = []
            node_positions = {}
            x_pos = 100
            y_pos = 100

            for i, node_def in enumerate(plan.get("nodes", []) if plan else []):
                node_id = f"node-{i+1}"
                node = Node(
                    id=node_id,
                    name=node_def.get("name", f"Node {i+1}"),
                    type=NodeType(node_def.get("type", "action")),
                    subtype=node_def.get("subtype"),
                    position=Position(x=x_pos, y=y_pos),
                    parameters=self._get_node_parameters(node_def, context),
                )
                nodes.append(node)
                node_positions[node.name] = node_id
                x_pos += 200

            # Generate connections
            connections_data = {"connections": {}}
            for conn in plan.get("connections", []) if plan else []:
                from_node = conn.get("from")
                to_node = conn.get("to")

                if from_node in node_positions and to_node in node_positions:
                    if from_node not in connections_data["connections"]:
                        connections_data["connections"][from_node] = {"main": {"connections": []}}

                    connections_data["connections"][from_node]["main"]["connections"].append(
                        {"node": to_node, "type": "MAIN", "index": 0}
                    )

            # Create the complete workflow
            workflow = Workflow(
                id=workflow_id,
                name=f"Generated Workflow - {state['user_input'][:50]}",
                nodes=nodes,
                connections=ConnectionsMap(**connections_data),
                created_at=current_time,
                updated_at=current_time,
                tags=["ai-generated", "langgraph"],
            )

            state["workflow"] = workflow.model_dump()
            state["workflow_suggestions"] = [
                "Consider adding error handling nodes",
                "Review the node connections for optimization",
                "Add logging for better monitoring",
            ]
            state["current_step"] = "validate_workflow"

            logger.info("Workflow generated successfully", workflow_id=workflow_id)

        except Exception as e:
            logger.error("Failed to generate workflow", error=str(e))
            if "workflow_errors" not in state:
                state["workflow_errors"] = []
            state["workflow_errors"].append(f"Failed to generate workflow: {str(e)}")
            state["current_step"] = "error"

        return state

    def _get_node_parameters(
        self, node_def: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get parameters for a node based on its type and context"""
        node_type = node_def.get("type")
        subtype = node_def.get("subtype")

        # Get base parameters from templates
        base_params = {}
        if (
            node_type
            and subtype
            and node_type in self.node_templates
            and subtype in self.node_templates[node_type]
        ):
            base_params = self.node_templates[node_type][subtype]["parameters"].copy()

        # Override with context-specific values
        if subtype == "slack_trigger" and context.get("slack_channel"):
            base_params["channel"] = context["slack_channel"]
        elif subtype == "google_calendar" and context.get("calendar_id"):
            base_params["calendar_id"] = context["calendar_id"]

        return base_params

    async def validate_workflow(self, state: AgentState) -> AgentState:
        """Validate the generated workflow"""
        logger.info("Validating workflow")

        workflow = state.get("workflow")
        errors = []
        warnings = []

        if not workflow:
            errors.append("No workflow generated")
        else:
            # Basic validation
            nodes = workflow.get("nodes", [])
            if not nodes:
                errors.append("Workflow must have at least one node")

            connections = workflow.get("connections", {}).get("connections", {})
            if len(nodes) > 1 and not connections:
                warnings.append("Multi-node workflow should have connections")

        state["validation_results"] = {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

        if errors:
            state["current_step"] = "error"
        else:
            state["current_step"] = "complete"
            state["should_continue"] = False

        logger.info("Workflow validation completed", errors=errors, warnings=warnings)
        return state

    def should_continue(self, state: AgentState) -> str:
        """Determine the next step in the workflow generation process"""
        current_step = state.get("current_step", "analyze_requirement")
        iteration_count = state.get("iteration_count", 0)
        max_iterations = state.get("max_iterations", 10)

        if iteration_count >= max_iterations:
            return "complete"

        if current_step == "error" or current_step == "complete":
            return "complete"

        return current_step
