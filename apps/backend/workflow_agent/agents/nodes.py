"""
LangGraph nodes for Workflow Agent
"""
import json
import uuid
import time
from typing import Dict, Any, List
import structlog
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from .state import AgentState, WorkflowGenerationState
from ..core.config import settings
from ..core.models import Workflow, Node, NodeType, Position, ConnectionsMap

logger = structlog.get_logger()


class WorkflowAgentNodes:
    """LangGraph nodes for workflow generation"""
    
    def __init__(self):
        self.llm = self._setup_llm()
        self.node_templates = self._load_node_templates()
    
    def _setup_llm(self):
        """Setup the language model based on configuration"""
        if settings.DEFAULT_MODEL_PROVIDER == "openai":
            return ChatOpenAI(
                model=settings.DEFAULT_MODEL_NAME,
                api_key=settings.OPENAI_API_KEY,
                temperature=0.1
            )
        elif settings.DEFAULT_MODEL_PROVIDER == "anthropic":
            return ChatAnthropic(
                model=settings.DEFAULT_MODEL_NAME,
                api_key=settings.ANTHROPIC_API_KEY,
                temperature=0.1
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
                        "autoReply": True
                    }
                },
                "webhook_trigger": {
                    "parameters": {
                        "httpMethod": "POST",
                        "path": "/webhook",
                        "authentication": "none"
                    }
                },
                "cron_trigger": {
                    "parameters": {
                        "cron_expression": "0 9 * * MON",
                        "timezone": "UTC"
                    }
                }
            },
            "ai_agent": {
                "router_agent": {
                    "parameters": {
                        "agent_type": "router",
                        "model_provider": "openai",
                        "model_name": "gpt-4",
                        "temperature": 0.1
                    }
                },
                "task_analyzer": {
                    "parameters": {
                        "agent_type": "taskAnalyzer",
                        "model_provider": "openai",
                        "model_name": "gpt-4",
                        "temperature": 0.2
                    }
                }
            },
            "external_action": {
                "google_calendar": {
                    "parameters": {
                        "action_type": "create_event",
                        "calendar_id": "primary",
                        "timezone": "UTC"
                    }
                },
                "slack_notification": {
                    "parameters": {
                        "channel": "#notifications",
                        "asUser": False
                    }
                }
            }
        }
    
    async def analyze_requirement(self, state: AgentState) -> AgentState:
        """Analyze user requirements and extract key information"""
        logger.info("Analyzing user requirements", description=state["description"])
        
        system_prompt = """你是一个工作流程分析专家。分析用户的自然语言描述，提取关键信息：
        1. 识别触发条件（什么时候执行）
        2. 确定主要操作（需要做什么）
        3. 识别数据流（数据如何传递）
        4. 确定集成需求（需要连接哪些外部服务）
        5. 识别人工干预点（需要人工确认的地方）
        
        以JSON格式返回分析结果。"""
        
        user_prompt = f"用户描述：{state['description']}\n\n请分析这个描述并提取工作流程的关键信息。"
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
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
                    "human_intervention": []
                }
            
            state["requirements"] = analysis
            state["parsed_intent"] = {
                "confidence": 0.8,
                "category": "automation",
                "complexity": "medium"
            }
            state["current_step"] = "plan_generation"
            
            logger.info("Requirements analyzed successfully", requirements=analysis)
            
        except Exception as e:
            logger.error("Failed to analyze requirements", error=str(e))
            state["workflow_errors"].append(f"Failed to analyze requirements: {str(e)}")
            state["current_step"] = "error"
        
        return state
    
    async def generate_plan(self, state: AgentState) -> AgentState:
        """Generate a high-level plan for the workflow"""
        logger.info("Generating workflow plan")
        
        requirements = state.get("requirements", {})
        
        system_prompt = """基于需求分析结果，生成详细的工作流程计划。计划应该包括：
        1. 节点列表（按执行顺序）
        2. 节点之间的连接关系
        3. 每个节点的配置要求
        4. 数据传递方式
        5. 错误处理策略
        
        以JSON格式返回计划。"""
        
        user_prompt = f"需求分析结果：{json.dumps(requirements, ensure_ascii=False)}\n\n请生成详细的工作流程计划。"
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        try:
            response = await self.llm.ainvoke(messages)
            
            try:
                plan = json.loads(response.content)
            except json.JSONDecodeError:
                plan = {
                    "nodes": [
                        {"type": "trigger", "subtype": "manual", "name": "Start"},
                        {"type": "action", "subtype": "data_processing", "name": "Process Data"},
                        {"type": "external_action", "subtype": "notification", "name": "Send Result"}
                    ],
                    "connections": [
                        {"from": "Start", "to": "Process Data"},
                        {"from": "Process Data", "to": "Send Result"}
                    ],
                    "error_handling": "stop_on_error"
                }
            
            state["current_plan"] = plan
            state["current_step"] = "check_knowledge"
            
            logger.info("Plan generated successfully", plan=plan)
            
        except Exception as e:
            logger.error("Failed to generate plan", error=str(e))
            state["workflow_errors"].append(f"Failed to generate plan: {str(e)}")
            state["current_step"] = "error"
        
        return state
    
    async def check_knowledge(self, state: AgentState) -> AgentState:
        """Check if we have enough information to proceed"""
        logger.info("Checking knowledge completeness")
        
        plan = state.get("current_plan", {})
        context = state.get("context", {})
        
        # Simple knowledge check - in production this would be more sophisticated
        required_info = []
        missing_info = []
        
        # Check for integration requirements
        nodes = plan.get("nodes", [])
        for node in nodes:
            if node.get("type") == "external_action":
                subtype = node.get("subtype", "")
                if subtype in ["google_calendar", "slack", "email"] and not context.get(f"{subtype}_credentials"):
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
        requirements = state.get("requirements", {})
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
            
            for i, node_def in enumerate(plan.get("nodes", [])):
                node_id = f"node-{i+1}"
                node = Node(
                    id=node_id,
                    name=node_def.get("name", f"Node {i+1}"),
                    type=NodeType(node_def.get("type", "action")),
                    subtype=node_def.get("subtype"),
                    position=Position(x=x_pos, y=y_pos),
                    parameters=self._get_node_parameters(node_def, context)
                )
                nodes.append(node)
                node_positions[node.name] = node_id
                x_pos += 200
            
            # Generate connections
            connections_data = {"connections": {}}
            for conn in plan.get("connections", []):
                from_node = conn.get("from")
                to_node = conn.get("to")
                
                if from_node in node_positions and to_node in node_positions:
                    from_id = node_positions[from_node]
                    to_id = node_positions[to_node]
                    
                    if from_node not in connections_data["connections"]:
                        connections_data["connections"][from_node] = {
                            "main": {"connections": []}
                        }
                    
                    connections_data["connections"][from_node]["main"]["connections"].append({
                        "node": to_node,
                        "type": "MAIN",
                        "index": 0
                    })
            
            # Create the complete workflow
            workflow = Workflow(
                id=workflow_id,
                name=f"Generated Workflow - {state['description'][:50]}",
                nodes=nodes,
                connections=ConnectionsMap(**connections_data),
                created_at=current_time,
                updated_at=current_time,
                tags=["ai-generated", "langgraph"]
            )
            
            state["workflow"] = workflow.model_dump()
            state["workflow_suggestions"] = [
                "Consider adding error handling nodes",
                "Review the node connections for optimization",
                "Add logging for better monitoring"
            ]
            state["current_step"] = "validate_workflow"
            
            logger.info("Workflow generated successfully", workflow_id=workflow_id)
            
        except Exception as e:
            logger.error("Failed to generate workflow", error=str(e))
            state["workflow_errors"].append(f"Failed to generate workflow: {str(e)}")
            state["current_step"] = "error"
        
        return state
    
    def _get_node_parameters(self, node_def: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Get parameters for a node based on its type and context"""
        node_type = node_def.get("type")
        subtype = node_def.get("subtype")
        
        # Get base parameters from templates
        base_params = {}
        if node_type in self.node_templates and subtype in self.node_templates[node_type]:
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
            "warnings": warnings
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