"""
Workflow Service using Pydantic models for FastAPI endpoints.
Replaces the gRPC-based workflow service with HTTP/JSON operations.
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from workflow_engine.workflow_engine.core.config import get_settings
from workflow_engine.workflow_engine.models.database import get_db
from workflow_engine.workflow_engine.models.requests import (
    CreateWorkflowRequest,
    DeleteWorkflowRequest,
    GetWorkflowRequest,
    ListWorkflowsRequest,
    UpdateWorkflowRequest,
)
from workflow_engine.workflow_engine.models.responses import (
    CreateWorkflowResponse,
    DeleteWorkflowResponse,
    GetWorkflowResponse,
    ListWorkflowsResponse,
    UpdateWorkflowResponse,
)
from workflow_engine.workflow_engine.models.workflow import Workflow as WorkflowDBModel
from workflow_engine.workflow_engine.models.workflow import WorkflowData
from workflow_engine.workflow_engine.utils.converters import ValidationHelper, WorkflowConverter

logger = logging.getLogger(__name__)
settings = get_settings()


class WorkflowService:
    """Service for workflow CRUD operations using Pydantic models."""

    def __init__(self):
        self.logger = logger
        self.converter = WorkflowConverter()

    async def create_workflow(self, request: CreateWorkflowRequest) -> CreateWorkflowResponse:
        """Create a new workflow."""
        try:
            self.logger.info(f"Creating workflow: {request.name} for user: {request.user_id}")

            # Validate the workflow data
            workflow_dict = request.dict()
            validation_errors = ValidationHelper.validate_workflow_data(workflow_dict)
            if validation_errors:
                error_msg = "; ".join(
                    [f"{field}: {error}" for field, error in validation_errors.items()]
                )
                raise ValueError(f"Validation failed: {error_msg}")

            # Create WorkflowData from request
            workflow_data = WorkflowData(
                id=str(uuid.uuid4()),
                name=request.name,
                description=request.description,
                nodes=request.nodes,
                connections=request.connections,
                settings=request.settings or WorkflowData.__fields__["settings"].default_factory(),
                static_data=request.static_data,
                tags=request.tags,
                active=True,
                version="1.0.0",
                created_at=int(datetime.now().timestamp()),
                updated_at=int(datetime.now().timestamp()),
                session_id=request.session_id,
            )

            # Convert to database format
            db_data = self.converter.pydantic_to_db_data(workflow_data, request.user_id)

            # Save to database
            db = next(get_db())
            try:
                db_workflow = WorkflowDBModel(**db_data)
                db.add(db_workflow)
                db.commit()
                db.refresh(db_workflow)

                # Convert back to Pydantic for response
                result_workflow = self.converter.db_to_pydantic(db_workflow)

                self.logger.info(f"Workflow created successfully: {result_workflow.id}")

                return CreateWorkflowResponse(
                    workflow=result_workflow, success=True, message="Workflow created successfully"
                )

            except Exception as e:
                db.rollback()
                raise e
            finally:
                db.close()

        except ValueError as e:
            self.logger.error(f"Validation error creating workflow: {str(e)}")
            raise e
        except Exception as e:
            self.logger.error(f"Error creating workflow: {str(e)}")
            raise Exception(f"Failed to create workflow: {str(e)}")

    async def get_workflow(self, request: GetWorkflowRequest) -> GetWorkflowResponse:
        """Get a workflow by ID."""
        try:
            self.logger.info(f"Getting workflow: {request.workflow_id} for user: {request.user_id}")

            db = next(get_db())
            try:
                db_workflow = (
                    db.query(WorkflowDBModel)
                    .filter(
                        WorkflowDBModel.id == request.workflow_id,
                        WorkflowDBModel.user_id == request.user_id,
                    )
                    .first()
                )

                if not db_workflow:
                    return GetWorkflowResponse(
                        workflow=None, found=False, message="Workflow not found"
                    )

                # Convert to Pydantic model
                workflow_data = self.converter.db_to_pydantic(db_workflow)

                return GetWorkflowResponse(
                    workflow=workflow_data, found=True, message="Workflow retrieved successfully"
                )

            finally:
                db.close()

        except Exception as e:
            self.logger.error(f"Error getting workflow: {str(e)}")
            raise Exception(f"Failed to get workflow: {str(e)}")

    async def update_workflow(self, request: UpdateWorkflowRequest) -> UpdateWorkflowResponse:
        """Update an existing workflow."""
        try:
            self.logger.info(
                f"Updating workflow: {request.workflow_id} for user: {request.user_id}"
            )

            db = next(get_db())
            try:
                db_workflow = (
                    db.query(WorkflowDBModel)
                    .filter(
                        WorkflowDBModel.id == request.workflow_id,
                        WorkflowDBModel.user_id == request.user_id,
                    )
                    .first()
                )

                if not db_workflow:
                    raise ValueError("Workflow not found")

                # Convert existing workflow to Pydantic
                current_workflow = self.converter.db_to_pydantic(db_workflow)

                # Apply updates
                update_data = {}
                if request.name is not None:
                    update_data["name"] = request.name
                if request.description is not None:
                    update_data["description"] = request.description
                if request.nodes is not None:
                    update_data["nodes"] = request.nodes
                if request.connections is not None:
                    update_data["connections"] = request.connections
                if request.settings is not None:
                    update_data["settings"] = request.settings
                if request.static_data is not None:
                    update_data["static_data"] = request.static_data
                if request.tags is not None:
                    update_data["tags"] = request.tags
                if request.active is not None:
                    update_data["active"] = request.active
                if request.session_id is not None:
                    update_data["session_id"] = request.session_id

                # Update timestamp
                update_data["updated_at"] = int(datetime.now().timestamp())

                # Create updated workflow
                updated_workflow = current_workflow.copy(update=update_data)

                # Validate updated workflow
                validation_errors = ValidationHelper.validate_workflow_data(updated_workflow.dict())
                if validation_errors:
                    error_msg = "; ".join(
                        [f"{field}: {error}" for field, error in validation_errors.items()]
                    )
                    raise ValueError(f"Validation failed: {error_msg}")

                # Convert to database format
                db_data = self.converter.pydantic_to_db_data(updated_workflow, request.user_id)

                # Update database record
                for key, value in db_data.items():
                    if key != "id":  # Don't update the ID
                        setattr(db_workflow, key, value)

                db.commit()
                db.refresh(db_workflow)

                # Convert back to Pydantic for response
                result_workflow = self.converter.db_to_pydantic(db_workflow)

                self.logger.info(f"Workflow updated successfully: {request.workflow_id}")

                return UpdateWorkflowResponse(
                    workflow=result_workflow, success=True, message="Workflow updated successfully"
                )

            except Exception as e:
                db.rollback()
                raise e
            finally:
                db.close()

        except ValueError as e:
            self.logger.error(f"Validation error updating workflow: {str(e)}")
            raise e
        except Exception as e:
            self.logger.error(f"Error updating workflow: {str(e)}")
            raise Exception(f"Failed to update workflow: {str(e)}")

    async def delete_workflow(self, request: DeleteWorkflowRequest) -> DeleteWorkflowResponse:
        """Delete a workflow."""
        try:
            self.logger.info(
                f"Deleting workflow: {request.workflow_id} for user: {request.user_id}"
            )

            db = next(get_db())
            try:
                result = (
                    db.query(WorkflowDBModel)
                    .filter(
                        WorkflowDBModel.id == request.workflow_id,
                        WorkflowDBModel.user_id == request.user_id,
                    )
                    .delete()
                )

                if result == 0:
                    raise ValueError("Workflow not found")

                db.commit()

                self.logger.info(f"Workflow deleted successfully: {request.workflow_id}")

                return DeleteWorkflowResponse(success=True, message="Workflow deleted successfully")

            except Exception as e:
                db.rollback()
                raise e
            finally:
                db.close()

        except ValueError as e:
            self.logger.error(f"Workflow not found for deletion: {str(e)}")
            raise e
        except Exception as e:
            self.logger.error(f"Error deleting workflow: {str(e)}")
            raise Exception(f"Failed to delete workflow: {str(e)}")

    async def list_workflows(self, request: ListWorkflowsRequest) -> ListWorkflowsResponse:
        """List workflows for a user."""
        try:
            self.logger.info(f"Listing workflows for user: {request.user_id}")

            db = next(get_db())
            try:
                query = db.query(WorkflowDBModel).filter(WorkflowDBModel.user_id == request.user_id)

                # Apply filters
                if request.active_only:
                    query = query.filter(WorkflowDBModel.active == True)

                if request.tags:
                    for tag in request.tags:
                        query = query.filter(WorkflowDBModel.tags.contains([tag]))

                # Order by updated_at desc
                query = query.order_by(WorkflowDBModel.updated_at.desc())

                # Get total count before pagination
                total_count = query.count()

                # Apply pagination
                if request.limit > 0:
                    query = query.limit(request.limit)
                if request.offset > 0:
                    query = query.offset(request.offset)

                db_workflows = query.all()

                # Convert to Pydantic models
                workflows = []
                for db_workflow in db_workflows:
                    try:
                        workflow_data = self.converter.db_to_pydantic(db_workflow)
                        workflows.append(workflow_data)
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to convert workflow {db_workflow.id}: {str(e)}"
                        )
                        continue

                has_more = (request.offset + len(workflows)) < total_count

                self.logger.info(f"Listed {len(workflows)} workflows for user: {request.user_id}")

                return ListWorkflowsResponse(
                    workflows=workflows, total_count=total_count, has_more=has_more
                )

            finally:
                db.close()

        except Exception as e:
            self.logger.error(f"Error listing workflows: {str(e)}")
            raise Exception(f"Failed to list workflows: {str(e)}")

    async def get_workflow_by_id_internal(
        self, workflow_id: str, user_id: str
    ) -> Optional[WorkflowData]:
        """Internal method to get workflow data for other services."""
        try:
            request = GetWorkflowRequest(workflow_id=workflow_id, user_id=user_id)
            response = await self.get_workflow(request)

            if response.found and response.workflow:
                return response.workflow

            return None

        except Exception as e:
            self.logger.error(f"Error getting workflow internally: {str(e)}")
            return None
