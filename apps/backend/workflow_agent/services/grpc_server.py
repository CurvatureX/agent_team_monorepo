"""
gRPC server for Workflow Agent service
"""

import asyncio
from concurrent import futures
from typing import Optional

import grpc
import structlog

from ..agents.workflow_agent import WorkflowAgent
from ..core.config import settings
from ..proto import workflow_agent_pb2, workflow_agent_pb2_grpc

logger = structlog.get_logger()


class WorkflowAgentServicer(workflow_agent_pb2_grpc.WorkflowAgentServicer):
    """Implementation of the WorkflowAgent gRPC service"""

    def __init__(self):
        # Initialize the LangGraph agent
        self.workflow_agent = WorkflowAgent()
        logger.info("WorkflowAgent initialized")

    def _dict_to_workflow_data(self, data: dict) -> workflow_agent_pb2.WorkflowData:
        """Convert dictionary to WorkflowData protobuf message"""
        if not data:
            return workflow_agent_pb2.WorkflowData()

        # Convert nodes
        nodes = []
        for node_data in data.get("nodes", []):
            position = workflow_agent_pb2.PositionData(
                x=node_data.get("position", {}).get("x", 0),
                y=node_data.get("position", {}).get("y", 0),
            )

            retry_policy = workflow_agent_pb2.RetryPolicyData(
                max_tries=node_data.get("retry_policy", {}).get("max_tries", 1),
                wait_between_tries=node_data.get("retry_policy", {}).get("wait_between_tries", 0),
            )

            node = workflow_agent_pb2.NodeData(
                id=node_data.get("id", ""),
                name=node_data.get("name", ""),
                type=node_data.get("type", ""),
                subtype=node_data.get("subtype", ""),
                type_version=node_data.get("type_version", 1),
                position=position,
                disabled=node_data.get("disabled", False),
                parameters=node_data.get("parameters", {}),
                credentials=node_data.get("credentials", {}),
                on_error=node_data.get("on_error", ""),
                retry_policy=retry_policy,
                notes=node_data.get("notes", {}),
                webhooks=node_data.get("webhooks", []),
            )
            nodes.append(node)

        # Convert connections
        connections_map = workflow_agent_pb2.ConnectionsMapData()
        connections_data = data.get("connections", {}).get("connections", {})

        for node_name, node_connections in connections_data.items():
            node_conn_data = workflow_agent_pb2.NodeConnectionsData()

            for conn_type, conn_array in node_connections.items():
                connections = []
                for conn in conn_array.get("connections", []):
                    connection = workflow_agent_pb2.ConnectionData(
                        node=conn.get("node", ""),
                        type=conn.get("type", ""),
                        index=conn.get("index", 0),
                    )
                    connections.append(connection)

                conn_array_data = workflow_agent_pb2.ConnectionArrayData(connections=connections)
                node_conn_data.connection_types[conn_type].CopyFrom(conn_array_data)

            connections_map.connections[node_name].CopyFrom(node_conn_data)

        # Convert settings
        settings_data = data.get("settings", {})
        workflow_settings = workflow_agent_pb2.WorkflowSettingsData(
            timezone=settings_data.get("timezone", {}),
            save_execution_progress=settings_data.get("save_execution_progress", True),
            save_manual_executions=settings_data.get("save_manual_executions", True),
            timeout=settings_data.get("timeout", 300),
            error_policy=settings_data.get("error_policy", ""),
            caller_policy=settings_data.get("caller_policy", ""),
        )

        # Create the main WorkflowData message
        workflow_data = workflow_agent_pb2.WorkflowData(
            id=data.get("id", ""),
            name=data.get("name", ""),
            active=data.get("active", True),
            nodes=nodes,
            connections=connections_map,
            settings=workflow_settings,
            static_data=data.get("static_data", {}),
            pin_data=data.get("pin_data", {}),
            created_at=data.get("created_at", 0),
            updated_at=data.get("updated_at", 0),
            version=data.get("version", ""),
            tags=data.get("tags", []),
        )

        return workflow_data

    async def GenerateWorkflow(self, request, context):
        """Generate workflow from natural language description"""
        try:
            logger.info("Generating workflow", description=request.description)

            # Convert request to dictionary
            context_dict = dict(request.context)
            user_preferences_dict = dict(request.user_preferences)

            # Call the LangGraph agent
            result = await self.workflow_agent.generate_workflow(
                user_input=request.description,
                context=context_dict,
                user_preferences=user_preferences_dict,
            )

            # Convert response to protobuf
            workflow_data = None
            if result.get("workflow"):
                workflow_data = self._dict_to_workflow_data(result["workflow"])

            response = workflow_agent_pb2.WorkflowGenerationResponse(
                success=result["success"],
                workflow=workflow_data,
                suggestions=result["suggestions"],
                missing_info=result["missing_info"],
                errors=result["errors"],
            )

            return response

        except Exception as e:
            logger.error("Failed to generate workflow", error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to generate workflow: {str(e)}")
            return workflow_agent_pb2.WorkflowGenerationResponse(
                success=False, errors=[f"Internal error: {str(e)}"]
            )

    async def RefineWorkflow(self, request, context):
        """Refine existing workflow based on feedback"""
        try:
            logger.info("Refining workflow", workflow_id=request.workflow_id)

            # Convert original workflow protobuf to dict
            original_workflow_dict = {
                "id": request.original_workflow.id,
                "name": request.original_workflow.name,
                "active": request.original_workflow.active,
                # Add more fields as needed
            }

            # Call the LangGraph agent
            result = await self.workflow_agent.refine_workflow(
                workflow_id=request.workflow_id,
                feedback=request.feedback,
                original_workflow=original_workflow_dict,
            )

            # Convert response to protobuf
            updated_workflow = None
            if result.get("updated_workflow"):
                updated_workflow = self._dict_to_workflow_data(result["updated_workflow"])

            response = workflow_agent_pb2.WorkflowRefinementResponse(
                success=result["success"],
                updated_workflow=updated_workflow,
                changes=result["changes"],
                errors=result["errors"],
            )

            return response

        except Exception as e:
            logger.error("Failed to refine workflow", error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to refine workflow: {str(e)}")
            return workflow_agent_pb2.WorkflowRefinementResponse(
                success=False, errors=[f"Internal error: {str(e)}"]
            )

    async def ValidateWorkflow(self, request, context):
        """Validate workflow structure and configuration"""
        try:
            logger.info("Validating workflow")

            # Convert request workflow_data to dict
            workflow_data_dict = dict(request.workflow_data)

            # Call the LangGraph agent
            result = await self.workflow_agent.validate_workflow(workflow_data_dict)

            response = workflow_agent_pb2.WorkflowValidationResponse(
                valid=result["valid"], errors=result["errors"], warnings=result["warnings"]
            )

            return response

        except Exception as e:
            logger.error("Failed to validate workflow", error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to validate workflow: {str(e)}")
            return workflow_agent_pb2.WorkflowValidationResponse(
                valid=False, errors=[f"Internal error: {str(e)}"]
            )


class WorkflowAgentServer:
    """gRPC server for Workflow Agent"""

    def __init__(self):
        self.server: Optional[grpc.aio.Server] = None
        self.servicer = WorkflowAgentServicer()

    async def start(self):
        """Start the gRPC server"""
        try:
            self.server = grpc.aio.server(
                futures.ThreadPoolExecutor(max_workers=settings.MAX_WORKERS)
            )

            # Add the servicer to the server
            workflow_agent_pb2_grpc.add_WorkflowAgentServicer_to_server(self.servicer, self.server)

            # Configure server address
            listen_addr = f"{settings.GRPC_HOST}:{settings.GRPC_PORT}"
            self.server.add_insecure_port(listen_addr)

            # Start the server
            await self.server.start()
            logger.info("gRPC server started", address=listen_addr)

        except Exception as e:
            logger.error("Failed to start gRPC server", error=str(e))
            raise

    async def stop(self):
        """Stop the gRPC server"""
        if self.server:
            logger.info("Stopping gRPC server")
            await self.server.stop(grace=5)
            logger.info("gRPC server stopped")

    async def wait_for_termination(self):
        """Wait for the server to terminate"""
        if self.server:
            await self.server.wait_for_termination()
