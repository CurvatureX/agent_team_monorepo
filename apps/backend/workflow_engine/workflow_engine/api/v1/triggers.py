"""
Trigger API endpoints.
FastAPI router for trigger management operations, replacing gRPC TriggerService.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from workflow_engine.workflow_engine.core.config import get_settings
from workflow_engine.workflow_engine.models.requests import (
    CreateTriggerRequest,
    DeleteTriggerRequest,
    FireTriggerRequest,
    GetTriggerEventsRequest,
    GetTriggerRequest,
    ListTriggersRequest,
    TriggerType,
    UpdateTriggerRequest,
)
from workflow_engine.workflow_engine.models.responses import (
    CreateTriggerResponse,
    DeleteTriggerResponse,
    FireTriggerResponse,
    GetTriggerEventsResponse,
    GetTriggerResponse,
    ListTriggersResponse,
    UpdateTriggerResponse,
)
from workflow_engine.workflow_engine.services.trigger_service import TriggerService

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/v1/triggers", tags=["triggers"])


# Dependency injection
def get_trigger_service() -> TriggerService:
    return TriggerService()


@router.post("", response_model=CreateTriggerResponse, status_code=status.HTTP_201_CREATED)
async def create_trigger(
    request: CreateTriggerRequest, trigger_service: TriggerService = Depends(get_trigger_service)
) -> CreateTriggerResponse:
    """
    Create a new trigger.

    - **type**: Trigger type (schedule, webhook, email, etc.)
    - **node_name**: Target node name in the workflow
    - **workflow_id**: Associated workflow ID
    - **configuration**: Trigger-specific configuration
    - **schedule**: Schedule configuration for cron triggers
    - **conditions**: Trigger activation conditions
    - **user_id**: User ID for authorization
    """
    try:
        logger.info(
            f"Creating trigger for workflow: {request.workflow_id} by user: {request.user_id}"
        )

        result = await trigger_service.create_trigger(request)

        logger.info(f"Trigger created successfully: {result.trigger.id}")
        return result

    except ValueError as e:
        logger.error(f"Validation error creating trigger: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error creating trigger: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create trigger: {str(e)}",
        )


@router.get("/{trigger_id}", response_model=GetTriggerResponse)
async def get_trigger(
    trigger_id: str, user_id: str, trigger_service: TriggerService = Depends(get_trigger_service)
) -> GetTriggerResponse:
    """
    Get a trigger by ID.

    - **trigger_id**: Unique trigger identifier
    - **user_id**: User ID for authorization
    """
    try:
        logger.info(f"Getting trigger: {trigger_id} for user: {user_id}")

        request = GetTriggerRequest(trigger_id=trigger_id, user_id=user_id)
        result = await trigger_service.get_trigger(request)

        if not result.found:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trigger not found")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trigger: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trigger: {str(e)}",
        )


@router.put("/{trigger_id}", response_model=UpdateTriggerResponse)
async def update_trigger(
    trigger_id: str,
    request: UpdateTriggerRequest,
    trigger_service: TriggerService = Depends(get_trigger_service),
) -> UpdateTriggerResponse:
    """
    Update an existing trigger.

    - **trigger_id**: Unique trigger identifier
    - **configuration**: Updated trigger configuration (optional)
    - **schedule**: Updated schedule configuration (optional)
    - **conditions**: Updated trigger conditions (optional)
    - **active**: Active status (optional)
    - **user_id**: User ID for authorization
    """
    try:
        logger.info(f"Updating trigger: {trigger_id} for user: {request.user_id}")

        # Set trigger_id from path parameter
        request.trigger_id = trigger_id
        result = await trigger_service.update_trigger(request)

        logger.info(f"Trigger updated successfully: {trigger_id}")
        return result

    except ValueError as e:
        logger.error(f"Validation error updating trigger: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error updating trigger: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update trigger: {str(e)}",
        )


@router.delete("/{trigger_id}", response_model=DeleteTriggerResponse)
async def delete_trigger(
    trigger_id: str, user_id: str, trigger_service: TriggerService = Depends(get_trigger_service)
) -> DeleteTriggerResponse:
    """
    Delete a trigger.

    - **trigger_id**: Unique trigger identifier
    - **user_id**: User ID for authorization
    """
    try:
        logger.info(f"Deleting trigger: {trigger_id} for user: {user_id}")

        request = DeleteTriggerRequest(trigger_id=trigger_id, user_id=user_id)
        result = await trigger_service.delete_trigger(request)

        logger.info(f"Trigger deleted successfully: {trigger_id}")
        return result

    except Exception as e:
        logger.error(f"Error deleting trigger: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete trigger: {str(e)}",
        )


@router.get("", response_model=ListTriggersResponse)
async def list_triggers(
    user_id: str,
    workflow_id: Optional[str] = None,
    type: Optional[TriggerType] = None,
    active_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    trigger_service: TriggerService = Depends(get_trigger_service),
) -> ListTriggersResponse:
    """
    List triggers for a user.

    - **user_id**: User ID to filter triggers
    - **workflow_id**: Filter by workflow ID (optional)
    - **type**: Filter by trigger type (optional)
    - **active_only**: Filter to active triggers only
    - **limit**: Maximum number of results (1-100)
    - **offset**: Pagination offset
    """
    try:
        logger.info(f"Listing triggers for user: {user_id}")

        request = ListTriggersRequest(
            workflow_id=workflow_id,
            type=type,
            active_only=active_only,
            user_id=user_id,
            limit=limit,
            offset=offset,
        )
        result = await trigger_service.list_triggers(request)

        logger.info(f"Listed {len(result.triggers)} triggers for user: {user_id}")
        return result

    except ValueError as e:
        logger.error(f"Validation error listing triggers: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error listing triggers: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list triggers: {str(e)}",
        )


@router.post("/{trigger_id}/fire", response_model=FireTriggerResponse)
async def fire_trigger(
    trigger_id: str,
    request: FireTriggerRequest,
    trigger_service: TriggerService = Depends(get_trigger_service),
) -> FireTriggerResponse:
    """
    Manually fire a trigger.

    - **trigger_id**: Unique trigger identifier
    - **event_data**: Event data to pass to the trigger
    - **source**: Event source identifier (optional)
    """
    try:
        logger.info(f"Firing trigger: {trigger_id}")

        # Set trigger_id from path parameter
        request.trigger_id = trigger_id
        result = await trigger_service.fire_trigger(request)

        logger.info(f"Trigger fired successfully: {trigger_id}, event_id: {result.event_id}")
        return result

    except ValueError as e:
        logger.error(f"Validation error firing trigger: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error firing trigger: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fire trigger: {str(e)}",
        )


@router.get("/{trigger_id}/events", response_model=GetTriggerEventsResponse)
async def get_trigger_events(
    trigger_id: str,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    trigger_service: TriggerService = Depends(get_trigger_service),
) -> GetTriggerEventsResponse:
    """
    Get trigger events history.

    - **trigger_id**: Unique trigger identifier
    - **status**: Filter by event status (optional)
    - **limit**: Maximum number of results (1-100)
    - **offset**: Pagination offset
    """
    try:
        logger.info(f"Getting events for trigger: {trigger_id}")

        request = GetTriggerEventsRequest(
            trigger_id=trigger_id, status=status, limit=limit, offset=offset
        )
        result = await trigger_service.get_trigger_events(request)

        logger.info(f"Retrieved {len(result.events)} trigger events")
        return result

    except ValueError as e:
        logger.error(f"Validation error getting trigger events: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error getting trigger events: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trigger events: {str(e)}",
        )
