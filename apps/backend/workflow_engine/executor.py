"""
Comprehensive Workflow Executor

Enhanced workflow execution logic with node-based execution system.
Migrated from old complex structure with proper node handling.
"""

import asyncio
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add shared models to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
from shared.models.execution import ExecutionStatus as SharedExecutionStatus

from database import Database
from models import ExecuteWorkflowRequest
from nodes import ExecutionStatus, NodeExecutionContext, NodeExecutorFactory
from services.execution_log_service import (
    ExecutionLogEntry,
    LogEventType,
    get_execution_log_service,
)
from utils.unicode_utils import clean_unicode_data, safe_json_dumps

logger = logging.getLogger(__name__)
logger.info("🔥 EXECUTOR DEBUG VERSION LOADED")


class WorkflowExecutor:
    """Enhanced workflow executor with node-based execution"""

    def __init__(self, database: Database):
        """Initialize executor"""
        self.db = database
        self.node_factory = NodeExecutorFactory
        self.log_service = get_execution_log_service()

    async def get_workflow_definition(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow definition from database."""
        try:
            logger.info(f"🔍 Getting workflow definition for: {workflow_id}")

            # Use Supabase repository instead of the corrupted db.client
            from services.supabase_repository import SupabaseWorkflowRepository

            repo = SupabaseWorkflowRepository(access_token=None)  # Use service role

            logger.info(f"🔍 DEBUG: Using service role repository to get workflow {workflow_id}")

            # Get the workflow using the repository
            workflow_data = await repo.get_workflow(workflow_id)
            if not workflow_data:
                logger.warning(f"❌ Workflow {workflow_id} not found in database")

                # DEBUG: Try to understand why workflow is not found
                logger.debug(f"🔍 DEBUG: Attempting to debug workflow not found issue...")

                # Let's see if we can list all workflows to understand what's in the database
                try:
                    workflows, total = await repo.list_workflows(limit=10)
                    logger.debug(f"🔍 DEBUG: Found {total} total workflows in database")
                    for wf in workflows[:3]:  # Show first 3 workflows
                        logger.debug(f"🔍 DEBUG: Workflow in DB: {wf.get('id')} - {wf.get('name')}")

                    # Try a direct table query to see if the workflow exists
                    if hasattr(repo.client, "table"):
                        direct_result = (
                            repo.client.table("workflows")
                            .select("id, name")
                            .eq("id", workflow_id)
                            .execute()
                        )
                        logger.debug(f"🔍 DEBUG: Direct table query result: {direct_result.data}")

                except Exception as debug_e:
                    logger.debug(f"🔍 DEBUG: Failed to debug workflow access: {debug_e}")

                return None

            logger.info(f"✅ Found workflow: {workflow_data.get('name', 'Unnamed')}")

            # Extract the workflow structure from workflow_data field
            workflow_definition = workflow_data.get("workflow_data", {})

            # Ensure we have the workflow ID
            workflow_definition["id"] = workflow_id

            # Extract nodes and connections
            nodes = workflow_definition.get("nodes", [])
            connections = workflow_definition.get("connections", {})

            logger.info(
                f"📋 Workflow has {len(nodes)} nodes and {len(connections)} connection groups"
            )

            return {
                "id": workflow_id,
                "name": workflow_data.get("name", "Unnamed Workflow"),
                "description": workflow_data.get("description", ""),
                "nodes": nodes,
                "connections": connections,
                "settings": workflow_definition.get("settings", {}),
                "static_data": workflow_definition.get("static_data", {}),
                "version": workflow_definition.get("version", "1.0.0"),
            }

        except Exception as e:
            logger.error(f"❌ Failed to get workflow definition for {workflow_id}: {e}")
            import traceback

            logger.error(f"❌ DEBUG: Full traceback: {traceback.format_exc()}")
            return None

    def _map_node_type_to_executor(self, workflow_node_type: str) -> str:
        """Validate and normalize node type using NodeType enum."""
        from shared.models.node_enums import NodeType

        try:
            # Validate it's a legitimate NodeType and return it directly
            node_type_enum = NodeType(workflow_node_type)
            return node_type_enum.value
        except ValueError:
            logger.warning(f"Unknown node type: {workflow_node_type}, using as-is")
            return workflow_node_type

    async def execute_workflow_nodes(
        self,
        workflow_definition: Dict[str, Any],
        execution_id: str,
        trigger_data: Dict[str, Any],
        access_token: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Execute nodes based on workflow graph connections."""
        print(f"🔥🔥🔥 EXECUTE_WORKFLOW_NODES CALLED FOR {execution_id} 🔥🔥🔥")
        logger.error(f"🔥🔥🔥 EXECUTE_WORKFLOW_NODES CALLED FOR {execution_id} 🔥🔥🔥")
        nodes = workflow_definition.get("nodes", [])
        connections = workflow_definition.get("connections", {})
        workflow_id = workflow_definition.get("id")

        # Build execution plan based on graph
        logger.info(
            f"🔍 DEBUG: Building execution plan with {len(nodes)} nodes and {len(connections)} connections"
        )
        logger.info(f"🔍 DEBUG: Node IDs: {[node.get('id') for node in nodes]}")
        logger.info(f"🔍 DEBUG: Raw connections data: {connections}")
        execution_plan = self._build_execution_plan(nodes, connections)
        logger.info(f"🔍 DEBUG: Execution plan result: {execution_plan}")
        if not execution_plan:
            logger.info(f"🔍 DEBUG: Empty execution plan - falling back to sequential execution")
            # Fallback to sequential execution if no connections defined
            return await self._execute_nodes_sequentially(
                nodes, workflow_id, execution_id, trigger_data, access_token
            )
        else:
            logger.info(f"🔍 DEBUG: Using graph-based execution with {len(execution_plan)} levels")

        # Execute nodes according to graph
        return await self._execute_nodes_by_graph(
            execution_plan, workflow_id, execution_id, trigger_data, access_token
        )

    def _build_execution_plan(
        self, nodes: List[Dict], connections: Dict[str, Any]
    ) -> List[List[str]]:
        """Build execution plan from workflow graph using topological sort."""
        # Create node map and filter out memory nodes (they're managed by AI agents internally)
        node_map = {node["id"]: node for node in nodes}

        # Filter out memory nodes from execution graph - they're managed internally by AI agents
        execution_nodes = [node for node in nodes if node.get("type") != "MEMORY"]
        logger.info(
            f"🔍 DEBUG: Filtered {len(nodes)} total nodes to {len(execution_nodes)} execution nodes (excluded {len(nodes) - len(execution_nodes)} memory nodes)"
        )

        # Build adjacency list from connections
        graph = {}
        in_degree = {}

        for node in execution_nodes:
            node_id = node["id"]
            graph[node_id] = []
            in_degree[node_id] = 0

        # Process connections to build graph
        logger.info(f"🔍 DEBUG: Processing connections: {connections}")
        for source_node_id, node_connections in connections.items():
            logger.info(
                f"🔍 DEBUG: Processing source node {source_node_id} with connections: {node_connections}"
            )
            if source_node_id not in graph:
                logger.info(f"🔍 DEBUG: Skipping {source_node_id} - not in graph")
                continue

            # Handle nested connection structure: {"connection_types": {"main": {"connections": [...]}}}
            if isinstance(node_connections, dict) and "connection_types" in node_connections:
                logger.info(f"🔍 DEBUG: Using new nested format for {source_node_id}")
                # New nested format from workflow factory
                for connection_type, type_data in node_connections["connection_types"].items():
                    # Only use "main" connections for execution order - memory connections are for data flow only
                    if connection_type != "main":
                        logger.info(
                            f"🔍 DEBUG: Skipping {connection_type} connections from {source_node_id} for execution graph (data-only)"
                        )
                        continue

                    if "connections" in type_data:
                        for connection in type_data["connections"]:
                            target_node_id = connection.get(
                                "node"
                            )  # Use "node" field from new format
                            logger.info(
                                f"🔍 DEBUG: Found main execution connection {source_node_id} -> {target_node_id}"
                            )
                            if target_node_id and target_node_id in graph:
                                graph[source_node_id].append(target_node_id)
                                in_degree[target_node_id] += 1
                                logger.info(
                                    f"🔍 DEBUG: Added execution edge {source_node_id} -> {target_node_id}"
                                )
                            else:
                                logger.info(
                                    f"🔍 DEBUG: Skipping connection {source_node_id} -> {target_node_id} (target not in graph or None)"
                                )
            else:
                # Legacy flat format fallback
                logger.info(f"🔍 DEBUG: Using legacy flat format for {source_node_id}")
                for connection in node_connections:
                    target_node_id = connection.get("target_node_id")
                    logger.info(f"🔍 DEBUG: Legacy connection {source_node_id} -> {target_node_id}")
                    if target_node_id and target_node_id in graph:
                        graph[source_node_id].append(target_node_id)
                        in_degree[target_node_id] += 1
                        logger.info(
                            f"🔍 DEBUG: Added legacy edge {source_node_id} -> {target_node_id}"
                        )
                    else:
                        logger.info(
                            f"🔍 DEBUG: Skipping legacy connection {source_node_id} -> {target_node_id} (target not in graph or None)"
                        )

        # Topological sort to determine execution order
        logger.info(f"🔍 DEBUG: Final graph: {graph}")
        logger.info(f"🔍 DEBUG: Final in_degree: {in_degree}")
        execution_levels = []
        available_nodes = [node_id for node_id, degree in in_degree.items() if degree == 0]
        logger.info(f"🔍 DEBUG: Initial available nodes (degree 0): {available_nodes}")

        while available_nodes:
            current_level = available_nodes[:]
            execution_levels.append(current_level)
            available_nodes = []

            for node_id in current_level:
                for neighbor in graph[node_id]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        available_nodes.append(neighbor)

        return execution_levels

    async def _execute_nodes_sequentially(
        self,
        nodes: List[Dict],
        workflow_id: str,
        execution_id: str,
        trigger_data: Dict[str, Any],
        access_token: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Execute nodes sequentially (fallback)."""
        results = []
        current_data = trigger_data

        for node in nodes:
            node_result = await self.execute_single_node_internal(
                node, workflow_id, execution_id, current_data, access_token
            )
            results.append(node_result)

            # Pass output data to next node
            if node_result.get("status") == "success":
                current_data = node_result.get("output_data", {})
            else:
                # Stop execution on error unless configured to continue
                break

        return results

    async def _execute_nodes_by_graph(
        self,
        execution_levels: List[List[str]],
        workflow_id: str,
        execution_id: str,
        trigger_data: Dict[str, Any],
        access_token: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Execute nodes based on graph levels."""
        print(f"🔥🔥🔥 _EXECUTE_NODES_BY_GRAPH CALLED WITH LEVELS: {execution_levels} 🔥🔥🔥")
        logger.error(f"🔥🔥🔥 _EXECUTE_NODES_BY_GRAPH CALLED WITH LEVELS: {execution_levels} 🔥🔥🔥")
        all_results = []
        node_outputs = {"trigger": trigger_data}  # Store outputs by node ID

        # Get all nodes by ID for lookup
        workflow_def = await self.get_workflow_definition(workflow_id)
        nodes_by_id = {node["id"]: node for node in workflow_def.get("nodes", [])}

        # Execute each level of nodes
        for level_idx, node_ids in enumerate(execution_levels):
            print(
                f"🔥🔥🔥 CRITICAL DEBUG: Executing level {level_idx + 1} with {len(node_ids)} nodes: {node_ids} 🔥🔥🔥"
            )
            logger.error(
                f"🔥🔥🔥 CRITICAL DEBUG: Executing level {level_idx + 1} with {len(node_ids)} nodes: {node_ids} 🔥🔥🔥"
            )
            logger.info(f"🔄 Executing level {level_idx + 1} with {len(node_ids)} nodes: {node_ids}")

            # Execute nodes in current level concurrently
            level_tasks = []
            for node_id in node_ids:
                node = nodes_by_id.get(node_id)
                if not node:
                    continue

                # Collect input data from connected upstream nodes
                input_data = self._collect_node_input_data(
                    node_id, node_outputs, workflow_def.get("connections", {})
                )

                # Create execution task
                task = self.execute_single_node_internal(
                    node, workflow_id, execution_id, input_data, access_token
                )
                level_tasks.append((node_id, task))

            # Execute all nodes in current level concurrently
            level_results = []
            for node_id, task in level_tasks:
                try:
                    result = await task
                    result["node_id"] = node_id
                    level_results.append(result)

                    # Store output for downstream nodes
                    if result.get("status") == "success":
                        node_outputs[node_id] = result.get("output_data", {})

                    logger.info(f"✅ Node {node_id} completed with status: {result.get('status')}")

                except Exception as e:
                    logger.error(f"❌ Node {node_id} failed: {e}")
                    error_result = {
                        "node_id": node_id,
                        "status": "error",
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                    }
                    level_results.append(error_result)

            all_results.extend(level_results)

            # Check if any critical errors occurred that should stop execution
            critical_errors = [
                r
                for r in level_results
                if r.get("status") == "error" and not r.get("continue_on_error", False)
            ]
            if critical_errors:
                logger.error(f"❌ Critical errors in level {level_idx + 1}, stopping execution")
                break

        return all_results

    def _collect_node_input_data(
        self, node_id: str, node_outputs: Dict[str, Any], connections: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Collect input data for a node from its upstream connections."""
        input_data = node_outputs.get("trigger", {}).copy()  # Start with trigger data

        # Find all nodes that connect to this node
        for source_node_id, source_connections in connections.items():
            # Handle nested connection structure: {"connection_types": {"main": {"connections": [...]}}}
            if isinstance(source_connections, dict) and "connection_types" in source_connections:
                # New nested format from workflow factory
                for connection_type, type_data in source_connections["connection_types"].items():
                    if "connections" in type_data:
                        for connection in type_data["connections"]:
                            target_node_id = connection.get(
                                "node"
                            )  # Use "node" field from new format
                            if target_node_id == node_id:
                                # Merge data from source node
                                source_data = node_outputs.get(source_node_id, {})

                                # Apply any data mapping from connection
                                output_field = connection.get("output_field", "output_data")
                                input_field = connection.get("input_field", "input_data")

                                if output_field in source_data:
                                    input_data[input_field] = source_data[output_field]
                                else:
                                    # Merge all source data if no specific field mapping
                                    input_data.update(source_data)
            else:
                # Handle old flat connection format for backward compatibility
                if isinstance(source_connections, list):
                    for connection in source_connections:
                        if (
                            connection.get("target_node_id") == node_id
                            or connection.get("node") == node_id
                        ):
                            # Merge data from source node
                            source_data = node_outputs.get(source_node_id, {})

                            # Apply any data mapping from connection
                            output_field = connection.get("output_field", "output_data")
                            input_field = connection.get("input_field", "input_data")

                            if output_field in source_data:
                                input_data[input_field] = source_data[output_field]
                            else:
                                # Merge all source data if no specific field mapping
                                input_data.update(source_data)

        return input_data

    async def execute_workflow_background(
        self,
        execution_id: str,
        workflow_id: str,
        request: ExecuteWorkflowRequest,
        access_token: Optional[str],
    ):
        """
        Execute workflow in background for async execution.

        This method runs the actual workflow but doesn't block the HTTP response.
        The API has already returned to the client at this point.
        """
        try:
            logger.info(f"🔄 Background execution started: {execution_id}")

            # Log workflow start
            start_entry = ExecutionLogEntry(
                execution_id=execution_id,
                event_type=LogEventType.WORKFLOW_STARTED,
                timestamp=datetime.now().isoformat(),
                message=f"Started workflow execution for {workflow_id}",
                level="INFO",
                data={
                    "workflow_id": workflow_id,
                    "user_id": request.user_id,
                    "trigger_data": request.trigger_data,
                    "user_friendly_message": f"🚀 Started workflow execution",
                    "display_priority": 8,
                    "is_milestone": True,
                },
            )
            await self.log_service.add_log_entry(start_entry)

            # Update status to RUNNING
            await self.db.update_execution_status(execution_id, SharedExecutionStatus.RUNNING.value)

            # Get workflow definition
            workflow_definition = await self.get_workflow_definition(workflow_id)
            if not workflow_definition:
                await self.db.update_execution_status(
                    execution_id, SharedExecutionStatus.ERROR.value, "Workflow not found"
                )
                return

            logger.info(
                f"⚡ Executing workflow {workflow_id} with trigger data: {request.trigger_data}"
            )

            # Execute workflow nodes
            node_results = await self.execute_workflow_nodes(
                workflow_definition, execution_id, request.trigger_data, access_token
            )

            # Check overall success
            all_successful = all(result.get("status") == "success" for result in node_results)

            if all_successful:
                success_message = f"Workflow {workflow_id} completed successfully"
                logger.info(f"✅ {success_message}")

                # Log successful completion
                completion_entry = ExecutionLogEntry(
                    execution_id=execution_id,
                    event_type=LogEventType.WORKFLOW_COMPLETED,
                    timestamp=datetime.now().isoformat(),
                    message=success_message,
                    level="INFO",
                    data={
                        "workflow_id": workflow_id,
                        "status": SharedExecutionStatus.SUCCESS.value,
                        "user_friendly_message": f"✅ Workflow completed successfully",
                        "display_priority": 8,
                        "is_milestone": True,
                    },
                )
                await self.log_service.add_log_entry(completion_entry)

                await self.db.update_execution_status(
                    execution_id, SharedExecutionStatus.SUCCESS.value
                )
            else:
                error_message = "Some nodes failed during execution"
                logger.error(f"❌ {error_message}")

                # Log error completion
                error_entry = ExecutionLogEntry(
                    execution_id=execution_id,
                    event_type=LogEventType.WORKFLOW_COMPLETED,
                    timestamp=datetime.now().isoformat(),
                    message=error_message,
                    level="ERROR",
                    data={
                        "workflow_id": workflow_id,
                        "status": "ERROR",
                        "user_friendly_message": f"❌ {error_message}",
                        "display_priority": 9,
                        "is_milestone": True,
                    },
                )
                await self.log_service.add_log_entry(error_entry)

                await self.db.update_execution_status(execution_id, "ERROR", error_message)

        except Exception as e:
            logger.error(f"❌ Background execution failed: {e}")
            # Update status to ERROR
            await self.db.update_execution_status(
                execution_id, SharedExecutionStatus.ERROR.value, str(e)
            )

    async def execute_workflow_sync(
        self,
        execution_id: str,
        workflow_id: str,
        request: ExecuteWorkflowRequest,
        access_token: Optional[str],
    ) -> Dict[str, Any]:
        """
        Execute workflow synchronously and wait for completion.

        This method blocks until the workflow is complete.
        Used for testing or when immediate results are needed.
        """
        try:
            logger.info(f"🔄 Synchronous execution started: {execution_id}")

            # Create execution record
            await self.db.create_execution_record(
                execution_id, workflow_id, request.user_id, SharedExecutionStatus.RUNNING.value
            )

            # Log workflow start
            start_entry = ExecutionLogEntry(
                execution_id=execution_id,
                event_type=LogEventType.WORKFLOW_STARTED,
                timestamp=datetime.now().isoformat(),
                message=f"Started workflow execution for {workflow_id}",
                level="INFO",
                data={
                    "workflow_id": workflow_id,
                    "user_id": request.user_id,
                    "trigger_data": request.trigger_data,
                    "user_friendly_message": "🚀 Started workflow execution",
                    "display_priority": 8,
                    "is_milestone": True,
                },
            )
            try:
                logger.error(f"🔥 DEBUG: About to add workflow start log entry for {execution_id}")
                await self.log_service.add_log_entry(start_entry)
                logger.error(
                    f"🔥 DEBUG: Successfully added workflow start log entry for {execution_id}"
                )
            except Exception as e:
                logger.error(f"🔥 DEBUG: Failed to add workflow start log: {e}")

            # Get workflow definition
            workflow_definition = await self.get_workflow_definition(workflow_id)
            if not workflow_definition:
                raise Exception("Workflow not found")

            logger.info(f"⚡ Executing workflow {workflow_id} synchronously")

            # Execute workflow nodes
            node_results = await self.execute_workflow_nodes(
                workflow_definition, execution_id, request.trigger_data, access_token
            )

            # Check overall success
            all_successful = all(result.get("status") == "success" for result in node_results)

            if all_successful:
                result = {
                    "status": SharedExecutionStatus.SUCCESS.value,
                    "success": True,
                    "message": f"Workflow {workflow_id} completed successfully",
                    "node_results": node_results,
                }
                # Update status
                await self.db.update_execution_status(
                    execution_id, SharedExecutionStatus.SUCCESS.value
                )

                # Log workflow completion
                completion_entry = ExecutionLogEntry(
                    execution_id=execution_id,
                    event_type=LogEventType.WORKFLOW_COMPLETED,
                    timestamp=datetime.now().isoformat(),
                    message=f"Workflow {workflow_id} completed successfully",
                    level="INFO",
                    data={
                        "status": "SUCCESS",
                        "workflow_id": workflow_id,
                        "user_friendly_message": "✅ Workflow completed successfully",
                        "display_priority": 8,
                        "is_milestone": True,
                    },
                )
                await self.log_service.add_log_entry(completion_entry)

            else:
                result = {
                    "status": "ERROR",
                    "success": False,
                    "message": "Some nodes failed during execution",
                    "node_results": node_results,
                }
                # Update status
                await self.db.update_execution_status(
                    execution_id, SharedExecutionStatus.ERROR.value, "Node execution failed"
                )

                # Log workflow error
                error_entry = ExecutionLogEntry(
                    execution_id=execution_id,
                    event_type=LogEventType.WORKFLOW_COMPLETED,
                    timestamp=datetime.now().isoformat(),
                    message=f"Workflow {workflow_id} failed during execution",
                    level="ERROR",
                    data={
                        "status": "ERROR",
                        "workflow_id": workflow_id,
                        "user_friendly_message": "❌ Workflow execution failed",
                        "display_priority": 9,
                        "is_milestone": True,
                    },
                )
                await self.log_service.add_log_entry(error_entry)

            logger.info(f"✅ Synchronous execution completed: {execution_id}")
            return result

        except Exception as e:
            logger.error(f"❌ Synchronous execution failed: {e}")
            # Update status to ERROR
            await self.db.update_execution_status(
                execution_id, SharedExecutionStatus.ERROR.value, str(e)
            )
            raise

    # Compatibility methods for services layer
    async def execute_workflow(
        self,
        workflow_id: str,
        execution_id: str,
        workflow_definition: Dict[str, Any],
        initial_data: Dict[str, Any],
        user_id: str,
    ) -> Dict[str, Any]:
        """Execute workflow with service-compatible interface."""
        try:
            logger.info(f"🔄 Service-compatible workflow execution: {workflow_id}")

            # Execute workflow nodes with the provided definition
            node_results = []
            nodes = workflow_definition.get("nodes", [])

            for node in nodes:
                result = await self.execute_single_node_internal(
                    node=node,
                    workflow_id=workflow_id,
                    execution_id=execution_id,
                    input_data=initial_data,
                )
                node_results.append(result)

            # Determine overall status
            all_successful = all(result.get("success", False) for result in node_results)

            return {
                "status": "completed" if all_successful else "error",
                "success": all_successful,
                "node_results": {f"node_{i}": result for i, result in enumerate(node_results)},
                "metadata": {"execution_id": execution_id, "workflow_id": workflow_id},
            }

        except Exception as e:
            logger.error(f"❌ Service-compatible execution failed: {e}")
            return {
                "status": "error",
                "success": False,
                "errors": [str(e)],
                "metadata": {"execution_id": execution_id, "workflow_id": workflow_id},
            }

    async def resume_workflow(
        self,
        execution_id: str,
        workflow_definition: Dict[str, Any],
        resume_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Resume workflow execution from saved state."""
        try:
            logger.info(f"🔄 Resuming workflow execution: {execution_id}")

            # Get current execution state from database
            execution_state = await self.db.get_execution_status(execution_id)
            if not execution_state:
                return {
                    "status": "error",
                    "success": False,
                    "message": f"Execution {execution_id} not found",
                }

            # Update status to resuming
            await self.db.update_execution_status(execution_id, "RESUMING")

            # Get completed nodes from execution logs
            completed_nodes = await self._get_completed_nodes(execution_id)
            remaining_nodes = self._get_remaining_nodes(workflow_definition, completed_nodes)

            if not remaining_nodes:
                await self.db.update_execution_status(execution_id, "COMPLETED")
                return {
                    "status": "completed",
                    "success": True,
                    "message": f"Workflow execution {execution_id} already completed",
                }

            # Get the last successful node output as input for resume
            last_output = await self._get_last_successful_output(execution_id)
            input_data = last_output or resume_data or {}

            # Continue execution from remaining nodes
            workflow_id = workflow_definition.get("id")
            access_token = execution_state.get("access_token")

            # Create modified workflow with only remaining nodes
            resume_workflow = {**workflow_definition, "nodes": remaining_nodes}

            results = await self.execute_workflow_nodes(
                resume_workflow, execution_id, input_data, access_token
            )

            # Update final status based on results
            success = all(r.get("status") == "success" for r in results)
            final_status = "COMPLETED" if success else "FAILED"
            await self.db.update_execution_status(execution_id, final_status)

            return {
                "status": "resumed",
                "success": success,
                "message": f"Workflow execution {execution_id} resumed and {'completed' if success else 'failed'}",
                "results": results,
                "metadata": {
                    "execution_id": execution_id,
                    "completed_nodes": [n["id"] for n in completed_nodes],
                    "resumed_nodes": [n["id"] for n in remaining_nodes],
                },
            }

        except Exception as e:
            logger.error(f"❌ Resume workflow failed: {e}")
            await self.db.update_execution_status(execution_id, "FAILED")
            return {
                "status": "error",
                "success": False,
                "error": str(e),
                "metadata": {"execution_id": execution_id},
            }

    async def _get_completed_nodes(self, execution_id: str) -> List[Dict[str, Any]]:
        """Get nodes that have been successfully completed."""
        try:
            # Query execution logs to find completed nodes
            query = (
                self.db.client.table("workflow_execution_logs")
                .select("node_id, node_data")
                .eq("execution_id", execution_id)
                .eq("message", "Node execution completed")
                .order("created_at")
            )
            result = query.execute()

            completed_nodes = []
            for log_entry in result.data or []:
                if log_entry.get("node_data"):
                    completed_nodes.append(log_entry["node_data"])

            return completed_nodes

        except Exception as e:
            logger.error(f"Failed to get completed nodes: {e}")
            return []

    def _get_remaining_nodes(
        self, workflow_definition: Dict[str, Any], completed_nodes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Get nodes that still need to be executed."""
        all_nodes = workflow_definition.get("nodes", [])
        completed_node_ids = {node.get("id") for node in completed_nodes}

        remaining_nodes = [node for node in all_nodes if node.get("id") not in completed_node_ids]

        return remaining_nodes

    async def _get_last_successful_output(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get output data from the last successfully executed node."""
        try:
            # Query execution logs for last successful node output
            query = (
                self.db.client.table("workflow_execution_logs")
                .select("output_data")
                .eq("execution_id", execution_id)
                .eq("level", "INFO")
                .contains("message", "completed")
                .order("created_at", desc=True)
                .limit(1)
            )
            result = query.execute()

            if result.data:
                return result.data[0].get("output_data", {})

        except Exception as e:
            logger.error(f"Failed to get last successful output: {e}")

        return None

    # Service-compatible single node execution
    async def execute_single_node(
        self,
        workflow_id: str,
        node_id: str,
        workflow_definition: Dict[str, Any],
        input_data: Dict[str, Any],
        user_id: str,
        execution_id: str,
    ) -> Dict[str, Any]:
        """Execute single node with service-compatible interface."""
        try:
            logger.info(f"🔄 Service-compatible single node execution: {node_id}")

            # Find the node in the workflow definition
            nodes = workflow_definition.get("nodes", [])
            target_node = None
            for node in nodes:
                if node.get("id") == node_id:
                    target_node = node
                    break

            if not target_node:
                raise ValueError(f"Node {node_id} not found in workflow definition")

            # Execute the node using the original method
            result = await self.execute_single_node_internal(
                node=target_node,
                workflow_id=workflow_id,
                execution_id=execution_id,
                input_data=input_data,
            )

            return result

        except Exception as e:
            logger.error(f"❌ Service-compatible single node execution failed: {e}")
            return {"success": False, "error": str(e), "execution_time": 0, "output_data": {}}

    async def execute_single_node_internal(
        self,
        node: Dict[str, Any],
        workflow_id: str,
        execution_id: str,
        input_data: Dict[str, Any],
        access_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a single workflow node (internal implementation)."""
        node_id = node.get("id")
        node_type = node.get("type")
        subtype = node.get("subtype")
        parameters = node.get("parameters", {})

        logger.info(f"Executing node {node_id} of type {node_type}")

        try:
            # Map workflow node types to executor node types
            executor_node_type = self._map_node_type_to_executor(node_type)

            # Create node executor
            executor = self.node_factory.create_executor(executor_node_type, subtype)

            # Clean all data to prevent Unicode issues before node execution
            cleaned_parameters = clean_unicode_data(parameters)
            cleaned_input_data = clean_unicode_data(input_data)

            logger.info(
                f"🧹 Cleaned Unicode data for node {node_id}: params={len(str(cleaned_parameters))}, input={len(str(cleaned_input_data))}"
            )

            # Get workflow definition for memory integration
            workflow_definition = await self.get_workflow_definition(workflow_id)

            # Create execution context with workflow metadata for memory integration
            context = NodeExecutionContext(
                node_id=node_id,
                workflow_id=workflow_id,
                execution_id=execution_id,
                parameters=cleaned_parameters,
                input_data=cleaned_input_data,
                static_data={},
                credentials={},
                metadata={
                    "access_token": access_token if access_token else None,
                    "node_id": node_id,
                    "workflow_connections": workflow_definition.get("connections", {})
                    if workflow_definition
                    else {},
                    "workflow_nodes": workflow_definition.get("nodes", [])
                    if workflow_definition
                    else [],
                },
            )

            # Add node start log
            node_name = parameters.get("name", node_id)
            start_entry = ExecutionLogEntry(
                execution_id=execution_id,
                event_type=LogEventType.STEP_STARTED,
                timestamp=datetime.now().isoformat(),
                message=f"Starting execution of {node_type} node: {node_name}",
                level="INFO",
                data={
                    "node_id": node_id,
                    "node_type": node_type,
                    "node_name": node_name,
                    "user_friendly_message": f"🔧 Starting {node_name}",
                    "display_priority": 6,
                    "is_milestone": False,
                },
            )
            await self.log_service.add_log_entry(start_entry)

            # Execute the node with logging
            result = await executor.execute_with_logging(context)

            # Add completion or error log based on result
            if result.status == ExecutionStatus.SUCCESS:
                completion_entry = ExecutionLogEntry(
                    execution_id=execution_id,
                    event_type=LogEventType.STEP_COMPLETED,
                    timestamp=datetime.now().isoformat(),
                    message=f"Successfully completed {node_type} node: {node_name}",
                    level="INFO",
                    data={
                        "node_id": node_id,
                        "node_type": node_type,
                        "node_name": node_name,
                        "execution_time": result.execution_time,
                        "user_friendly_message": f"✅ Completed {node_name}",
                        "display_priority": 7,
                        "is_milestone": False,
                    },
                )
                await self.log_service.add_log_entry(completion_entry)
            else:
                error_entry = ExecutionLogEntry(
                    execution_id=execution_id,
                    event_type=LogEventType.STEP_ERROR,
                    timestamp=datetime.now().isoformat(),
                    message=f"Failed to execute {node_type} node: {node_name} - {result.error_message}",
                    level="ERROR",
                    data={
                        "node_id": node_id,
                        "node_type": node_type,
                        "node_name": node_name,
                        "error_message": clean_unicode_data(result.error_message)
                        if result.error_message
                        else None,
                        "error_details": clean_unicode_data(result.error_details)
                        if result.error_details
                        else None,
                        "execution_time": result.execution_time,
                        "user_friendly_message": f"❌ Failed at {node_name}: {result.error_message}",
                        "display_priority": 8,
                        "is_milestone": False,
                    },
                )
                await self.log_service.add_log_entry(error_entry)

            # Clean output data to prevent Unicode corruption
            cleaned_output_data = clean_unicode_data(result.output_data)
            cleaned_error_message = (
                clean_unicode_data(result.error_message) if result.error_message else None
            )
            cleaned_logs = clean_unicode_data(result.logs) if result.logs else []

            return {
                "status": "success" if result.status == ExecutionStatus.SUCCESS else "error",
                "success": result.status == ExecutionStatus.SUCCESS,
                "output_data": cleaned_output_data,
                "execution_time": result.execution_time,
                "error_message": cleaned_error_message,
                "logs": cleaned_logs,
            }

        except Exception as e:
            logger.error(f"Node execution failed: {e}")

            # Add critical error log
            node_name = parameters.get("name", node_id)
            critical_error_entry = ExecutionLogEntry(
                execution_id=execution_id,
                event_type=LogEventType.STEP_ERROR,
                timestamp=datetime.now().isoformat(),
                message=f"Critical error in {node_type} node: {node_name} - {str(e)}",
                level="ERROR",
                data={
                    "node_id": node_id,
                    "node_type": node_type,
                    "node_name": node_name,
                    "exception": str(e),
                    "exception_type": type(e).__name__,
                    "user_friendly_message": f"🚨 Critical error at {node_name}: {str(e)}",
                    "display_priority": 9,
                    "is_milestone": False,
                },
            )
            await self.log_service.add_log_entry(critical_error_entry)

            return {
                "status": "error",
                "success": False,
                "output_data": {},
                "execution_time": 0,
                "error_message": str(e),
                "logs": [f"Execution failed: {e}"],
            }
