from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from enum import Enum


class TriggerType(str, Enum):
    MANUAL = "manual"
    SCHEDULE = "schedule"
    WEBHOOK = "webhook"


class Trigger(BaseModel):
    id: str
    workflow_id: str
    type: TriggerType
    config: Dict[str, Any]
    is_active: bool = True
    last_fired_at: Optional[int] = None
    created_at: int
    updated_at: int 