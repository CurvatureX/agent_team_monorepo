"""
Workflow Repository - Database operations for workflow and deployment management
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.db_models import WorkflowDB, WorkflowDeploymentHistory
from shared.models.workflow import WorkflowDeploymentStatus as DeploymentStatus
from workflow_scheduler.core.database import get_db_session

logger = logging.getLogger(__name__)


class WorkflowRepository:
    """Repository for workflow database operations"""

    async def get_workflow_by_id(self, workflow_id: str) -> Optional[WorkflowDB]:
        """Get workflow by ID"""
        try:
            async with get_db_session() as session:
                # Handle both string and UUID workflow_id
                if isinstance(workflow_id, str):
                    try:
                        workflow_uuid = UUID(workflow_id)
                    except ValueError:
                        # If it's not a valid UUID string, return None
                        logger.warning(f"Invalid workflow_id format: {workflow_id}")
                        return None
                else:
                    workflow_uuid = workflow_id

                stmt = select(WorkflowDB).where(WorkflowDB.id == workflow_uuid)
                result = await session.execute(stmt)
                workflow = result.scalar_one_or_none()

                if workflow:
                    logger.info(f"Found workflow: {workflow_id}")
                else:
                    logger.warning(f"Workflow not found: {workflow_id}")

                return workflow
        except Exception as e:
            logger.error(f"Error getting workflow {workflow_id}: {e}", exc_info=True)
            return None

    async def update_workflow_deployment_status(
        self,
        workflow_id: str,
        deployment_status: str,
        deployed_at: Optional[datetime] = None,
        deployed_by: Optional[str] = None,
        undeployed_at: Optional[datetime] = None,
        deployment_config: Optional[Dict] = None,
        increment_version: bool = False,
    ) -> bool:
        """Update workflow deployment fields"""
        try:
            async with get_db_session() as session:
                # Handle both string and UUID workflow_id
                if isinstance(workflow_id, str):
                    try:
                        workflow_uuid = UUID(workflow_id)
                    except ValueError:
                        logger.warning(f"Invalid workflow_id format: {workflow_id}")
                        return False
                else:
                    workflow_uuid = workflow_id

                # Normalize deployment status using enum to avoid case mismatches
                try:
                    normalized_status = (
                        DeploymentStatus(deployment_status).value
                        if isinstance(deployment_status, str)
                        else str(deployment_status)
                    )
                except Exception:
                    # Fallback: Default to UNDEPLOYED if invalid status
                    normalized_status = DeploymentStatus.UNDEPLOYED.value

                # Prepare update data
                current_time = datetime.now(timezone.utc)
                update_data = {
                    "deployment_status": normalized_status,
                    "updated_at": int(
                        current_time.timestamp()
                    ),  # Convert to Unix timestamp for bigint field
                }

                if deployed_at:
                    update_data["deployed_at"] = (
                        deployed_at if isinstance(deployed_at, datetime) else deployed_at
                    )

                if undeployed_at:
                    update_data["undeployed_at"] = (
                        undeployed_at if isinstance(undeployed_at, datetime) else undeployed_at
                    )

                if deployed_by:
                    try:
                        update_data["deployed_by"] = UUID(deployed_by)
                    except ValueError:
                        logger.warning(f"Invalid deployed_by UUID format: {deployed_by}")

                if deployment_config:
                    update_data["deployment_config"] = deployment_config

                # Handle version increment
                if increment_version:
                    # First get current version
                    stmt = select(WorkflowDB.deployment_version).where(
                        WorkflowDB.id == workflow_uuid
                    )
                    result = await session.execute(stmt)
                    current_version = result.scalar_one_or_none()
                    if current_version is not None:
                        update_data["deployment_version"] = current_version + 1
                    else:
                        update_data["deployment_version"] = 1

                # Execute update
                stmt = (
                    update(WorkflowDB).where(WorkflowDB.id == workflow_uuid).values(**update_data)
                )

                result = await session.execute(stmt)
                await session.commit()

                if result.rowcount > 0:
                    logger.info(
                        f"Updated workflow deployment status: {workflow_id} -> {normalized_status}"
                    )
                    return True
                else:
                    logger.warning(f"No workflow found to update: {workflow_id}")
                    return False

        except Exception as e:
            logger.error(
                f"Error updating workflow deployment status {workflow_id}: {e}",
                exc_info=True,
            )
            return False

    async def create_deployment_history_record(
        self,
        workflow_id: str,
        deployment_action: str,
        from_status: str,
        to_status: str,
        deployment_version: int,
        triggered_by: Optional[str] = None,
        deployment_config: Optional[Dict] = None,
        error_message: Optional[str] = None,
        deployment_logs: Optional[Dict] = None,
    ) -> bool:
        """Create a deployment history record"""
        try:
            async with get_db_session() as session:
                # Handle both string and UUID workflow_id
                if isinstance(workflow_id, str):
                    try:
                        workflow_uuid = UUID(workflow_id)
                    except ValueError:
                        logger.warning(f"Invalid workflow_id format: {workflow_id}")
                        return False
                else:
                    workflow_uuid = workflow_id

                # Handle triggered_by UUID
                triggered_by_uuid = None
                if triggered_by:
                    try:
                        triggered_by_uuid = UUID(triggered_by)
                    except ValueError:
                        logger.warning(f"Invalid triggered_by UUID format: {triggered_by}")

                history_record = WorkflowDeploymentHistory(
                    workflow_id=workflow_uuid,
                    deployment_action=deployment_action,
                    from_status=from_status,
                    to_status=to_status,
                    deployment_version=deployment_version,
                    triggered_by=triggered_by_uuid,
                    deployment_config=deployment_config or {},
                    error_message=error_message,
                    deployment_logs=deployment_logs or {},
                    started_at=datetime.now(timezone.utc),
                    completed_at=(datetime.now(timezone.utc) if error_message is None else None),
                )

                session.add(history_record)
                await session.commit()

                logger.info(
                    f"Created deployment history record: {workflow_id} - {deployment_action}"
                )
                return True

        except Exception as e:
            logger.error(
                f"Error creating deployment history record {workflow_id}: {e}",
                exc_info=True,
            )
            return False

    async def get_deployment_history(
        self, workflow_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get deployment history for a workflow"""
        try:
            async with get_db_session() as session:
                # Handle both string and UUID workflow_id
                if isinstance(workflow_id, str):
                    try:
                        workflow_uuid = UUID(workflow_id)
                    except ValueError:
                        logger.warning(f"Invalid workflow_id format: {workflow_id}")
                        return []
                else:
                    workflow_uuid = workflow_id

                stmt = (
                    select(WorkflowDeploymentHistory)
                    .where(WorkflowDeploymentHistory.workflow_id == workflow_uuid)
                    .order_by(WorkflowDeploymentHistory.started_at.desc())
                    .limit(limit)
                )

                result = await session.execute(stmt)
                history_records = result.scalars().all()

                return [record.to_dict() for record in history_records]

        except Exception as e:
            logger.error(
                f"Error getting deployment history for {workflow_id}: {e}",
                exc_info=True,
            )
            return []

    async def update_deployment_history_completion(
        self,
        workflow_id: str,
        deployment_action: str,
        error_message: Optional[str] = None,
        deployment_logs: Optional[Dict] = None,
    ) -> bool:
        """Update the most recent deployment history record with completion info"""
        try:
            async with get_db_session() as session:
                # Handle both string and UUID workflow_id
                if isinstance(workflow_id, str):
                    try:
                        workflow_uuid = UUID(workflow_id)
                    except ValueError:
                        logger.warning(f"Invalid workflow_id format: {workflow_id}")
                        return False
                else:
                    workflow_uuid = workflow_id

                # Find the most recent incomplete record for this workflow and action
                stmt = (
                    select(WorkflowDeploymentHistory)
                    .where(
                        WorkflowDeploymentHistory.workflow_id == workflow_uuid,
                        WorkflowDeploymentHistory.deployment_action == deployment_action,
                        WorkflowDeploymentHistory.completed_at.is_(None),
                    )
                    .order_by(WorkflowDeploymentHistory.started_at.desc())
                    .limit(1)
                )

                result = await session.execute(stmt)
                history_record = result.scalar_one_or_none()

                if history_record:
                    # Update completion info
                    update_data = {
                        "completed_at": datetime.now(timezone.utc),
                    }

                    if error_message:
                        update_data["error_message"] = error_message

                    if deployment_logs:
                        update_data["deployment_logs"] = deployment_logs

                    stmt = (
                        update(WorkflowDeploymentHistory)
                        .where(WorkflowDeploymentHistory.id == history_record.id)
                        .values(**update_data)
                    )

                    await session.execute(stmt)
                    await session.commit()

                    logger.info(
                        f"Updated deployment history completion: {workflow_id} - {deployment_action}"
                    )
                    return True
                else:
                    logger.warning(
                        f"No incomplete deployment history found for {workflow_id} - {deployment_action}"
                    )
                    return False

        except Exception as e:
            logger.error(
                f"Error updating deployment history completion {workflow_id}: {e}",
                exc_info=True,
            )
            return False

    async def batched_deployment_transaction(
        self,
        workflow_id: str,
        deployment_status: str,
        deployment_action: str = "DEPLOY",
        deployment_config: Optional[Dict] = None,
        deployment_logs: Optional[Dict] = None,
        increment_version: bool = False,
        error_message: Optional[str] = None,
    ) -> bool:
        """
        Perform all deployment-related database operations in a single transaction
        for improved performance
        """
        try:
            async with get_db_session() as session:
                # Handle both string and UUID workflow_id
                if isinstance(workflow_id, str):
                    try:
                        workflow_uuid = UUID(workflow_id)
                    except ValueError:
                        logger.warning(f"Invalid workflow_id format: {workflow_id}")
                        return False
                else:
                    workflow_uuid = workflow_id

                # 1. Get current workflow state
                workflow_stmt = select(WorkflowDB).where(WorkflowDB.id == workflow_uuid)
                workflow_result = await session.execute(workflow_stmt)
                workflow = workflow_result.scalar_one_or_none()

                if not workflow:
                    logger.warning(f"Workflow not found: {workflow_id}")
                    return False

                current_status = (
                    getattr(workflow, "deployment_status", None)
                    or DeploymentStatus.UNDEPLOYED.value
                )
                current_version = getattr(workflow, "deployment_version", None) or 0

                # 2. Create deployment history record
                new_version = current_version + (1 if increment_version else 0)
                # Use uppercase enum names for history table consistency
                try:
                    from_status_name = (
                        DeploymentStatus(current_status).name
                        if current_status in {d.value for d in DeploymentStatus}
                        else DeploymentStatus.UNDEPLOYED.name
                    )
                except Exception:
                    from_status_name = DeploymentStatus.UNDEPLOYED.name

                try:
                    to_status_name = (
                        DeploymentStatus(deployment_status).name
                        if isinstance(deployment_status, str)
                        else DeploymentStatus(str(deployment_status)).name
                    )
                except Exception:
                    to_status_name = DeploymentStatus.UNDEPLOYED.name

                history_record = WorkflowDeploymentHistory(
                    workflow_id=workflow_uuid,
                    deployment_action=deployment_action,
                    from_status=from_status_name,
                    to_status=to_status_name,
                    deployment_version=new_version,
                    deployment_config=deployment_config or {},
                    error_message=error_message,
                    deployment_logs=deployment_logs or {},
                    started_at=datetime.now(timezone.utc),
                    completed_at=(datetime.now(timezone.utc) if error_message is None else None),
                )

                session.add(history_record)

                # 3. Update workflow deployment fields
                current_time = datetime.now(timezone.utc)

                update_data = {
                    "deployment_status": deployment_status,
                    "updated_at": int(
                        current_time.timestamp()
                    ),  # Convert to Unix timestamp for bigint field
                }

                if normalized_status == DeploymentStatus.DEPLOYED.value:
                    update_data["deployed_at"] = current_time
                elif normalized_status == DeploymentStatus.UNDEPLOYED.value:
                    update_data["undeployed_at"] = current_time

                if deployment_config:
                    update_data["deployment_config"] = deployment_config

                if increment_version:
                    update_data["deployment_version"] = new_version

                workflow_stmt = (
                    update(WorkflowDB).where(WorkflowDB.id == workflow_uuid).values(**update_data)
                )

                await session.execute(workflow_stmt)

                # 4. Commit all changes in single transaction
                await session.commit()

                logger.info(
                    f"Batched deployment transaction completed: {workflow_id} -> {deployment_status}"
                )
                return True

        except Exception as e:
            logger.error(
                f"Error in batched deployment transaction {workflow_id}: {e}",
                exc_info=True,
            )
            return False
