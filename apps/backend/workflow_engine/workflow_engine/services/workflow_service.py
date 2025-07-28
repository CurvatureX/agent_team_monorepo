"""
Workflow Service - 工作流CRUD操作服务.

This module implements workflow-related operations: Create, Read, Update, Delete, List.
"""

import logging
from typing import Optional
import uuid
from datetime import datetime
import json

import grpc
from sqlalchemy.orm import Session

from proto import workflow_service_pb2
from proto import workflow_pb2
from workflow_engine.models.database import get_db
from workflow_engine.models.workflow import Workflow as WorkflowModel
from workflow_engine.models.node_template import NodeTemplate
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
            if request.session_id:  # 新增：设置session_id
                workflow.session_id = request.session_id
            
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
                # Convert protobuf to JSON for JSONB storage
                from google.protobuf.json_format import MessageToDict
                workflow_json = MessageToDict(workflow)
                
                db_workflow = WorkflowModel(
                    id=workflow.id,
                    user_id=request.user_id,
                    name=workflow.name,
                    description=workflow.description,
                    active=workflow.active,
                    workflow_data=workflow_json,  # Store protobuf as JSONB
                    created_at=workflow.created_at,
                    updated_at=workflow.updated_at,
                    version=workflow.version,
                    tags=list(workflow.tags),  # Direct array, not JSON
                    session_id=request.session_id if request.session_id else None  # 新增：session_id支持
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
                    WorkflowModel.id == str(request.workflow_id),  # 确保是字符串
                    WorkflowModel.user_id == str(request.user_id)  # 确保是字符串
                ).first()
                
                if not db_workflow:
                    return workflow_service_pb2.GetWorkflowResponse(
                        found=False,
                        message="Workflow not found"
                    )
                
                # Convert database model to protobuf
                from google.protobuf.json_format import ParseDict
                workflow = workflow_pb2.Workflow()
                ParseDict(db_workflow.workflow_data, workflow)
                
                # 设置基本字段（这些字段在数据库中单独存储）
                workflow.id = str(db_workflow.id)  # 确保是字符串
                workflow.name = str(db_workflow.name)
                workflow.description = str(db_workflow.description)
                workflow.active = bool(db_workflow.active)
                workflow.created_at = int(db_workflow.created_at)
                workflow.updated_at = int(db_workflow.updated_at)
                if db_workflow.tags is not None:
                    workflow.tags.extend([str(tag) for tag in db_workflow.tags])
                
                # 新增：确保session_id正确设置
                if db_workflow.session_id is not None:
                    workflow.session_id = str(db_workflow.session_id)  # 转换为字符串
                
                return workflow_service_pb2.GetWorkflowResponse(
                    workflow=workflow,
                    found=True,
                    message="Workflow retrieved successfully"
                )
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error getting workflow: {str(e)}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
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
                from google.protobuf.json_format import ParseDict, MessageToDict
                workflow = workflow_pb2.Workflow()
                ParseDict(db_workflow.workflow_data, workflow)
                
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
                
                # Convert protobuf to JSON for database storage
                workflow_json = MessageToDict(workflow)
                
                # Update database
                db_workflow.name = workflow.name
                db_workflow.description = workflow.description
                db_workflow.active = workflow.active
                db_workflow.workflow_data = workflow_json
                db_workflow.updated_at = workflow.updated_at
                if request.tags:
                    db_workflow.tags = list(workflow.tags)
                if request.session_id:  # 新增：更新session_id
                    db_workflow.session_id = request.session_id
                
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
                    WorkflowModel.user_id == str(request.user_id)  # 确保是字符串
                )
                
                # Apply filters
                if request.active_only:
                    query = query.filter(WorkflowModel.active == True)
                
                if request.tags:
                    for tag in request.tags:
                        query = query.filter(WorkflowModel.tags.contains([tag]))
                
                # Order by updated_at desc (must be before limit/offset)
                query = query.order_by(WorkflowModel.updated_at.desc())
                
                # Apply pagination
                if request.limit > 0:
                    query = query.limit(request.limit)
                if request.offset > 0:
                    query = query.offset(request.offset)
                
                db_workflows = query.all()
                
                # Convert to protobuf
                from google.protobuf.json_format import ParseDict
                workflows = []
                for db_workflow in db_workflows:
                    workflow = workflow_pb2.Workflow()
                    ParseDict(db_workflow.workflow_data, workflow)
                    
                    # 设置基本字段（这些字段在数据库中单独存储）
                    workflow.id = str(db_workflow.id)  # 确保是字符串
                    workflow.name = str(db_workflow.name)
                    workflow.description = str(db_workflow.description)
                    workflow.active = bool(db_workflow.active)
                    workflow.created_at = int(db_workflow.created_at)
                    workflow.updated_at = int(db_workflow.updated_at)
                    if db_workflow.tags is not None:
                        workflow.tags.extend([str(tag) for tag in db_workflow.tags])
                    
                    # 新增：确保session_id正确设置
                    if db_workflow.session_id is not None:
                        workflow.session_id = str(db_workflow.session_id)  # 转换为字符串
                    workflows.append(workflow)
                
                return workflow_service_pb2.ListWorkflowsResponse(
                    workflows=workflows,
                    total_count=len(workflows)
                )
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error listing workflows: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to list workflows: {str(e)}")
            return workflow_service_pb2.ListWorkflowsResponse(
                workflows=[],
                total_count=0
            )

    def ListAllNodeTemplates(
        self,
        request: workflow_service_pb2.ListAllNodeTemplatesRequest,
        context: grpc.ServicerContext
    ) -> workflow_service_pb2.ListAllNodeTemplatesResponse:
        """List all available node templates."""
        try:
            self.logger.info("Listing all node templates")
            db = next(get_db())
            try:
                query = db.query(NodeTemplate)

                # Apply filters from request
                if request.category_filter:
                    query = query.filter(NodeTemplate.category == request.category_filter)
                if request.type_filter != workflow_pb2.NodeType.TRIGGER_NODE: # Proto default is 0 (TRIGGER_NODE)
                    # Assuming NodeType enum in proto has the same names as strings in the DB
                    query = query.filter(NodeTemplate.node_type == workflow_pb2.NodeType.Name(request.type_filter))
                if request.include_system_templates:
                    query = query.filter(NodeTemplate.is_system_template == True)

                db_node_templates = query.all()

                node_templates_pb = []
                for db_template in db_node_templates:
                    template_pb = workflow_pb2.NodeTemplate(
                        id=str(db_template.template_id),
                        name=db_template.name,
                        description=db_template.description or "",
                        category=db_template.category or "",
                        node_type=workflow_pb2.NodeType.Value(db_template.node_type),
                        node_subtype=db_template.node_subtype,
                        version=db_template.version or "1.0.0",
                        is_system_template=db_template.is_system_template,
                        default_parameters=json.dumps(db_template.default_parameters or {}),
                        required_parameters=db_template.required_parameters or [],
                        parameter_schema=json.dumps(db_template.parameter_schema or "{}")
                    )
                    node_templates_pb.append(template_pb)

                return workflow_service_pb2.ListAllNodeTemplatesResponse(node_templates=node_templates_pb)

            finally:
                db.close()

        except Exception as e:
            self.logger.error(f"Error listing node templates: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to list node templates: {str(e)}")
            return workflow_service_pb2.ListAllNodeTemplatesResponse() 