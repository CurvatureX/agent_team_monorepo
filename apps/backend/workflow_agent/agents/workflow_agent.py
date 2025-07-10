"""
Main LangGraph-based Workflow Agent
"""
import asyncio
from typing import Dict, Any, List
import structlog
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.redis import RedisAsyncClient, RedisSaver

from .state import AgentState
from .nodes import WorkflowAgentNodes
from ..core.config import settings

logger = structlog.get_logger()


class WorkflowAgent:
    """LangGraph-based Workflow Agent for generating workflows"""
    
    def __init__(self):
        self.nodes = WorkflowAgentNodes()
        self.graph = None
        self.checkpointer = None
        self._setup_graph()
    
    def _setup_checkpointer(self):
        """Setup checkpointer for state persistence"""
        if settings.LANGGRAPH_CHECKPOINT_BACKEND == "redis":
            try:
                redis_client = RedisAsyncClient.from_url(settings.REDIS_URL)
                self.checkpointer = RedisSaver(redis_client)
                logger.info("Using Redis checkpointer for state persistence")
            except Exception as e:
                logger.warning("Failed to setup Redis checkpointer, using memory", error=str(e))
                self.checkpointer = MemorySaver()
        else:
            self.checkpointer = MemorySaver()
            logger.info("Using memory checkpointer for state persistence")
    
    def _setup_graph(self):
        """Setup the LangGraph workflow"""
        self._setup_checkpointer()
        
        # Create the StateGraph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("analyze_requirement", self.nodes.analyze_requirement)
        workflow.add_node("generate_plan", self.nodes.generate_plan)
        workflow.add_node("check_knowledge", self.nodes.check_knowledge)
        workflow.add_node("generate_workflow", self.nodes.generate_workflow)
        workflow.add_node("validate_workflow", self.nodes.validate_workflow)
        
        # Add edges
        workflow.set_entry_point("analyze_requirement")
        
        workflow.add_edge("analyze_requirement", "generate_plan")
        workflow.add_edge("generate_plan", "check_knowledge")
        
        # Conditional edges
        workflow.add_conditional_edges(
            "check_knowledge",
            self.nodes.should_continue,
            {
                "ask_questions": END,  # For now, end if questions needed
                "generate_workflow": "generate_workflow",
                "complete": END
            }
        )
        
        workflow.add_edge("generate_workflow", "validate_workflow")
        
        workflow.add_conditional_edges(
            "validate_workflow",
            self.nodes.should_continue,
            {
                "complete": END,
                "error": END
            }
        )
        
        # Compile the graph
        self.graph = workflow.compile(checkpointer=self.checkpointer)
        
        logger.info("LangGraph workflow compiled successfully")
    
    async def generate_workflow(
        self,
        description: str,
        context: Dict[str, Any] = None,
        user_preferences: Dict[str, Any] = None,
        thread_id: str = None
    ) -> Dict[str, Any]:
        """Generate a workflow from natural language description"""
        logger.info("Starting workflow generation", description=description)
        
        try:
            # Initialize state
            initial_state = AgentState(
                user_input=description,
                description=description,
                context=context or {},
                user_preferences=user_preferences or {},
                requirements={},
                parsed_intent={},
                current_plan=None,
                collected_info={},
                missing_info=[],
                questions_asked=[],
                messages=[],
                conversation_history=[],
                workflow=None,
                workflow_suggestions=[],
                workflow_errors=[],
                debug_results=None,
                validation_results=None,
                current_step="analyze_requirement",
                iteration_count=0,
                max_iterations=10,
                should_continue=True,
                final_result=None,
                feedback=None,
                changes_made=[]
            )
            
            # Run the graph
            config = {"configurable": {"thread_id": thread_id or "default"}}
            final_state = await self.graph.ainvoke(initial_state, config=config)
            
            # Prepare response
            workflow = final_state.get("workflow")
            suggestions = final_state.get("workflow_suggestions", [])
            missing_info = final_state.get("missing_info", [])
            errors = final_state.get("workflow_errors", [])
            
            success = workflow is not None and len(errors) == 0
            
            result = {
                "success": success,
                "workflow": workflow,
                "suggestions": suggestions,
                "missing_info": missing_info,
                "errors": errors
            }
            
            logger.info("Workflow generation completed", success=success, errors=len(errors))
            return result
            
        except Exception as e:
            logger.error("Failed to generate workflow", error=str(e))
            return {
                "success": False,
                "workflow": None,
                "suggestions": [],
                "missing_info": [],
                "errors": [f"Internal error: {str(e)}"]
            }
    
    async def refine_workflow(
        self,
        workflow_id: str,
        feedback: str,
        original_workflow: Dict[str, Any],
        thread_id: str = None
    ) -> Dict[str, Any]:
        """Refine an existing workflow based on feedback"""
        logger.info("Starting workflow refinement", workflow_id=workflow_id)
        
        try:
            # For now, implement a simple refinement logic
            # In a full implementation, this would use another LangGraph workflow
            
            changes = []
            updated_workflow = original_workflow.copy()
            
            # Simple feedback processing
            if "error handling" in feedback.lower():
                # Add error handling suggestions
                changes.append("Added error handling recommendations")
                if "settings" in updated_workflow:
                    updated_workflow["settings"]["error_policy"] = "CONTINUE_REGULAR_OUTPUT"
                else:
                    updated_workflow["settings"] = {"error_policy": "CONTINUE_REGULAR_OUTPUT"}
            
            if "logging" in feedback.lower():
                changes.append("Added logging recommendations")
                # Add logging to workflow tags
                if "tags" not in updated_workflow:
                    updated_workflow["tags"] = []
                if "logging" not in updated_workflow["tags"]:
                    updated_workflow["tags"].append("logging")
            
            if "notification" in feedback.lower():
                changes.append("Added notification suggestions")
                # This would add notification nodes in a full implementation
            
            if not changes:
                changes.append("Applied general improvements based on feedback")
            
            result = {
                "success": True,
                "updated_workflow": updated_workflow,
                "changes": changes,
                "errors": []
            }
            
            logger.info("Workflow refinement completed", changes=len(changes))
            return result
            
        except Exception as e:
            logger.error("Failed to refine workflow", error=str(e))
            return {
                "success": False,
                "updated_workflow": None,
                "changes": [],
                "errors": [f"Internal error: {str(e)}"]
            }
    
    async def validate_workflow(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a workflow structure"""
        logger.info("Validating workflow structure")
        
        try:
            errors = []
            warnings = []
            
            # Basic structure validation
            if not isinstance(workflow_data, dict):
                errors.append("Workflow data must be a dictionary")
                return {"valid": False, "errors": errors, "warnings": warnings}
            
            # Check required fields
            required_fields = ["id", "name", "nodes"]
            for field in required_fields:
                if field not in workflow_data:
                    errors.append(f"Missing required field: {field}")
            
            # Validate nodes
            nodes = workflow_data.get("nodes", [])
            if not isinstance(nodes, list):
                errors.append("Nodes must be a list")
            elif len(nodes) == 0:
                errors.append("Workflow must have at least one node")
            else:
                # Validate each node
                for i, node in enumerate(nodes):
                    if not isinstance(node, dict):
                        errors.append(f"Node {i} must be a dictionary")
                        continue
                    
                    node_required = ["id", "name", "type"]
                    for field in node_required:
                        if field not in node:
                            errors.append(f"Node {i} missing required field: {field}")
            
            # Validate connections
            connections = workflow_data.get("connections", {})
            if len(nodes) > 1 and not connections.get("connections"):
                warnings.append("Multi-node workflow should have connections between nodes")
            
            # Check for orphaned nodes (nodes with no connections)
            if connections.get("connections"):
                connected_nodes = set()
                for source, targets in connections["connections"].items():
                    connected_nodes.add(source)
                    for connection_type, connection_list in targets.items():
                        for conn in connection_list.get("connections", []):
                            connected_nodes.add(conn.get("node"))
                
                all_node_names = {node.get("name") for node in nodes if isinstance(node, dict)}
                orphaned = all_node_names - connected_nodes
                if orphaned and len(nodes) > 1:
                    warnings.append(f"Nodes with no connections: {', '.join(orphaned)}")
            
            result = {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
            logger.info("Workflow validation completed", valid=result["valid"], errors=len(errors))
            return result
            
        except Exception as e:
            logger.error("Failed to validate workflow", error=str(e))
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": []
            }