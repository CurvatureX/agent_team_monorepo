"""
Workflow Service - 工作流CRUD操作服务.

This module implements workflow-related operations: Create, Read, Update, Delete, List.
"""

import logging
from typing import Optional, List, Tuple
import uuid
from datetime import datetime
import json

from sqlalchemy.orm import Session

from shared.models import (
    WorkflowData,
    CreateWorkflowRequest,
    UpdateWorkflowRequest,
    ListWorkflowsRequest,
    NodeTemplate,
)
from workflow_engine.models.workflow import Workflow as WorkflowModel
from workflow_engine.models.node_template import NodeTemplate as NodeTemplateModel
from workflow_engine.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class WorkflowService:
    """Service for workflow CRUD operations."""

    def __init__(self, db_session: Session):
        self.logger = logger
        self.db = db_session

    def create_workflow_from_data(self, request: CreateWorkflowRequest) -> WorkflowData:
        """Create a new workflow from Pydantic model."""
        try:
            self.logger.info(f"Creating workflow: {request.name}")
            
            workflow_id = str(uuid.uuid4())
            now = int(datetime.now().timestamp())

            workflow_data = WorkflowData(
                id=workflow_id,
                name=request.name,
                description=request.description,
                nodes=request.nodes,
                connections=request.connections,
                settings=request.settings,
                static_data=request.static_data,
                tags=request.tags,
                active=True,
                created_at=now,
                updated_at=now,
                version="1.0.0"
            )

            db_workflow = WorkflowModel(
                id=workflow_id,
                user_id=request.user_id,
                name=request.name,
                description=request.description,
                active=True,
                workflow_data=workflow_data.dict(),
                created_at=now,
                updated_at=now,
                version="1.0.0",
                tags=request.tags,
                session_id=request.session_id,
            )
            self.db.add(db_workflow)
            self.db.commit()
            
            self.logger.info(f"Workflow created successfully: {workflow_id}")
            return workflow_data
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Error creating workflow: {str(e)}")
            raise

    def get_workflow(self, workflow_id: str, user_id: str) -> Optional[WorkflowData]:
        """Get a workflow by ID."""
        try:
            self.logger.info(f"Getting workflow: {workflow_id}")
            
            db_workflow = self.db.query(WorkflowModel).filter(
                WorkflowModel.id == workflow_id,
                WorkflowModel.user_id == user_id
            ).first()
            
            if not db_workflow:
                return None
            
            return WorkflowData(**db_workflow.workflow_data)
        except Exception as e:
            self.logger.error(f"Error getting workflow: {str(e)}")
            raise

    def update_workflow_from_data(self, workflow_id: str, user_id: str, update_data: UpdateWorkflowRequest) -> WorkflowData:
        """Update an existing workflow from Pydantic model."""
        try:
            self.logger.info(f"Updating workflow: {workflow_id}")
            
            db_workflow = self.db.query(WorkflowModel).filter(
                WorkflowModel.id == workflow_id,
                WorkflowModel.user_id == user_id
            ).first()
            
            if not db_workflow:
                raise Exception("Workflow not found")
            
            workflow_data = WorkflowData(**db_workflow.workflow_data)
            
            update_dict = update_data.dict(exclude_unset=True)
            for key, value in update_dict.items():
                if hasattr(workflow_data, key):
                    setattr(workflow_data, key, value)
            
            workflow_data.updated_at = int(datetime.now().timestamp())
            
            db_workflow.name = workflow_data.name
            db_workflow.description = workflow_data.description
            db_workflow.active = workflow_data.active
            db_workflow.workflow_data = workflow_data.dict()
            db_workflow.updated_at = workflow_data.updated_at
            db_workflow.tags = workflow_data.tags
            if update_data.session_id:
                db_workflow.session_id = update_data.session_id
            
            self.db.commit()
            
            self.logger.info(f"Workflow updated successfully: {workflow_id}")
            return workflow_data
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Error updating workflow: {str(e)}")
            raise

    def delete_workflow(self, workflow_id: str, user_id: str) -> bool:
        """Delete a workflow."""
        try:
            self.logger.info(f"Deleting workflow: {workflow_id}")
            
            result = self.db.query(WorkflowModel).filter(
                WorkflowModel.id == workflow_id,
                WorkflowModel.user_id == user_id
            ).delete()
            
            if result == 0:
                raise Exception("Workflow not found")
            
            self.db.commit()
            self.logger.info(f"Workflow deleted successfully: {workflow_id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Error deleting workflow: {str(e)}")
            raise

    def list_workflows(self, request: ListWorkflowsRequest) -> Tuple[List[WorkflowData], int]:
        """List workflows for a user."""
        try:
            self.logger.info(f"Listing workflows for user: {request.user_id}")
            
            query = self.db.query(WorkflowModel).filter(
                WorkflowModel.user_id == request.user_id
            )
            
            if request.active_only:
                query = query.filter(WorkflowModel.active == True)
            
            if request.tags:
                for tag in request.tags:
                    query = query.filter(WorkflowModel.tags.contains([tag]))
            
            total_count = query.count()
            
            query = query.order_by(WorkflowModel.updated_at.desc())
            
            if request.limit > 0:
                query = query.limit(request.limit)
            if request.offset > 0:
                query = query.offset(request.offset)
            
            db_workflows = query.all()
            
            workflows = [WorkflowData(**db_workflow.workflow_data) for db_workflow in db_workflows]
            
            return workflows, total_count
        except Exception as e:
            self.logger.error(f"Error listing workflows: {str(e)}")
            raise

    def list_all_node_templates(
        self,
        category_filter: Optional[str] = None,
        include_system_templates: bool = True
    ) -> List[NodeTemplate]:
        """List all available node templates."""
        try:
            self.logger.info("Listing all node templates")
            query = self.db.query(NodeTemplateModel)

            if category_filter:
                query = query.filter(NodeTemplateModel.category == category_filter)

            if not include_system_templates:
                query = query.filter(NodeTemplateModel.is_system_template == False)

            db_node_templates = query.all()

            return [NodeTemplate.from_orm(t) for t in db_node_templates]

        except Exception as e:
            self.logger.error(f"Error listing node templates: {str(e)}")
            raise