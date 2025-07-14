"""
Workflow Service - 工作流CRUD操作服务.

This module implements workflow-related operations: Create, Read, Update, Delete, List.
"""

import logging
from typing import Optional
import uuid
from datetime import datetime

import grpc
from sqlalchemy.orm import Session

from workflow_engine.proto import workflow_service_pb2
from workflow_engine.proto import workflow_pb2
from workflow_engine.models.database import get_db
from workflow_engine.models.workflow import Workflow as WorkflowModel
from workflow_engine.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class WorkflowService:
    """Service for workflow CRUD operations."""

    def __init__(self):
        self.logger = logger

    def create_workflow(
        self, 
        request: workflow_service_pb2.CreateWorkflowRequest, 
        context: grpc.ServicerContext
    ) -> workflow_service_pb2.CreateWorkflowResponse:
        """Create a new workflow."""
        try:
            self.logger.info(f"Creating workflow: {request.name}")
            
            # Create workflow protobuf object
            workflow = workflow_pb2.Workflow()
            workflow.id = str(uuid.uuid4())
            workflow.name = request.name
            workflow.description = request.description
            workflow.active = True
            workflow.created_at = int(datetime.now().timestamp())
            workflow.updated_at = int(datetime.now().timestamp())
            workflow.version = "1.0.0"
            
            # Copy nodes and connections
            workflow.nodes.extend(request.nodes)
            workflow.connections.CopyFrom(request.connections)
            workflow.settings.CopyFrom(request.settings)
            
            # Copy static data and tags
            workflow.static_data.update(request.static_data)
            workflow.tags.extend(request.tags)
            
            # Save to database
            db = next(get_db())
            try:
                db_workflow = WorkflowModel(
                    id=workflow.id,
                    user_id=request.user_id,
                    name=workflow.name,
                    description=workflow.description,
                    active=workflow.active,
                    workflow_data=workflow,  # Store protobuf as JSONB
                    created_at=workflow.created_at,
                    updated_at=workflow.updated_at,
                    version=workflow.version,
                    tags=list(workflow.tags)
                )
                db.add(db_workflow)
                db.commit()
                
                self.logger.info(f"Workflow created successfully: {workflow.id}")
                
                return workflow_service_pb2.CreateWorkflowResponse(
                    workflow=workflow,
                    success=True,
                    message="Workflow created successfully"
                )
                
            except Exception as e:
                db.rollback()
                raise e
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error creating workflow: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to create workflow: {str(e)}")
            return workflow_service_pb2.CreateWorkflowResponse(
                success=False,
                message=f"Error: {str(e)}"
            )

    def get_workflow(
        self, 
        request: workflow_service_pb2.GetWorkflowRequest, 
        context: grpc.ServicerContext
    ) -> workflow_service_pb2.GetWorkflowResponse:
        """Get a workflow by ID."""
        try:
            self.logger.info(f"Getting workflow: {request.workflow_id}")
            
            db = next(get_db())
            try:
                db_workflow = db.query(WorkflowModel).filter(
                    WorkflowModel.id == request.workflow_id,
                    WorkflowModel.user_id == request.user_id
                ).first()
                
                if not db_workflow:
                    return workflow_service_pb2.GetWorkflowResponse(
                        found=False,
                        message="Workflow not found"
                    )
                
                # Convert database model to protobuf
                workflow = workflow_pb2.Workflow()
                workflow.CopyFrom(db_workflow.workflow_data)
                
                return workflow_service_pb2.GetWorkflowResponse(
                    workflow=workflow,
                    found=True,
                    message="Workflow retrieved successfully"
                )
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error getting workflow: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to get workflow: {str(e)}")
            return workflow_service_pb2.GetWorkflowResponse(
                found=False,
                message=f"Error: {str(e)}"
            )

    def update_workflow(
        self, 
        request: workflow_service_pb2.UpdateWorkflowRequest, 
        context: grpc.ServicerContext
    ) -> workflow_service_pb2.UpdateWorkflowResponse:
        """Update an existing workflow."""
        try:
            self.logger.info(f"Updating workflow: {request.workflow_id}")
            
            db = next(get_db())
            try:
                db_workflow = db.query(WorkflowModel).filter(
                    WorkflowModel.id == request.workflow_id,
                    WorkflowModel.user_id == request.user_id
                ).first()
                
                if not db_workflow:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details("Workflow not found")
                    return workflow_service_pb2.UpdateWorkflowResponse(
                        success=False,
                        message="Workflow not found"
                    )
                
                # Update workflow protobuf
                workflow = workflow_pb2.Workflow()
                workflow.CopyFrom(db_workflow.workflow_data)
                
                if request.name:
                    workflow.name = request.name
                if request.description:
                    workflow.description = request.description
                if request.nodes:
                    workflow.nodes.clear()
                    workflow.nodes.extend(request.nodes)
                if request.connections:
                    workflow.connections.CopyFrom(request.connections)
                if request.settings:
                    workflow.settings.CopyFrom(request.settings)
                if request.static_data:
                    workflow.static_data.clear()
                    workflow.static_data.update(request.static_data)
                if request.tags:
                    workflow.tags.clear()
                    workflow.tags.extend(request.tags)
                
                workflow.active = request.active
                workflow.updated_at = int(datetime.now().timestamp())
                
                # Update database
                db_workflow.name = workflow.name
                db_workflow.description = workflow.description
                db_workflow.active = workflow.active
                db_workflow.workflow_data = workflow
                db_workflow.updated_at = workflow.updated_at
                db_workflow.tags = list(workflow.tags)
                
                db.commit()
                
                self.logger.info(f"Workflow updated successfully: {request.workflow_id}")
                
                return workflow_service_pb2.UpdateWorkflowResponse(
                    workflow=workflow,
                    success=True,
                    message="Workflow updated successfully"
                )
                
            except Exception as e:
                db.rollback()
                raise e
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error updating workflow: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to update workflow: {str(e)}")
            return workflow_service_pb2.UpdateWorkflowResponse(
                success=False,
                message=f"Error: {str(e)}"
            )

    def delete_workflow(
        self, 
        request: workflow_service_pb2.DeleteWorkflowRequest, 
        context: grpc.ServicerContext
    ) -> workflow_service_pb2.DeleteWorkflowResponse:
        """Delete a workflow."""
        try:
            self.logger.info(f"Deleting workflow: {request.workflow_id}")
            
            db = next(get_db())
            try:
                result = db.query(WorkflowModel).filter(
                    WorkflowModel.id == request.workflow_id,
                    WorkflowModel.user_id == request.user_id
                ).delete()
                
                if result == 0:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details("Workflow not found")
                    return workflow_service_pb2.DeleteWorkflowResponse(
                        success=False,
                        message="Workflow not found"
                    )
                
                db.commit()
                
                self.logger.info(f"Workflow deleted successfully: {request.workflow_id}")
                
                return workflow_service_pb2.DeleteWorkflowResponse(
                    success=True,
                    message="Workflow deleted successfully"
                )
                
            except Exception as e:
                db.rollback()
                raise e
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error deleting workflow: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to delete workflow: {str(e)}")
            return workflow_service_pb2.DeleteWorkflowResponse(
                success=False,
                message=f"Error: {str(e)}"
            )

    def list_workflows(
        self, 
        request: workflow_service_pb2.ListWorkflowsRequest, 
        context: grpc.ServicerContext
    ) -> workflow_service_pb2.ListWorkflowsResponse:
        """List workflows for a user."""
        try:
            self.logger.info(f"Listing workflows for user: {request.user_id}")
            
            db = next(get_db())
            try:
                query = db.query(WorkflowModel).filter(
                    WorkflowModel.user_id == request.user_id
                )
                
                # Apply filters
                if request.active is not None:
                    query = query.filter(WorkflowModel.active == request.active)
                
                if request.tags:
                    for tag in request.tags:
                        query = query.filter(WorkflowModel.tags.contains([tag]))
                
                # Apply pagination
                if request.limit > 0:
                    query = query.limit(request.limit)
                if request.offset > 0:
                    query = query.offset(request.offset)
                
                # Order by updated_at desc
                query = query.order_by(WorkflowModel.updated_at.desc())
                
                db_workflows = query.all()
                
                # Convert to protobuf
                workflows = []
                for db_workflow in db_workflows:
                    workflow = workflow_pb2.Workflow()
                    workflow.CopyFrom(db_workflow.workflow_data)
                    workflows.append(workflow)
                
                return workflow_service_pb2.ListWorkflowsResponse(
                    workflows=workflows,
                    total=len(workflows),
                    success=True,
                    message="Workflows retrieved successfully"
                )
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error listing workflows: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to list workflows: {str(e)}")
            return workflow_service_pb2.ListWorkflowsResponse(
                success=False,
                message=f"Error: {str(e)}"
            ) 