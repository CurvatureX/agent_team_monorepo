from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from enum import Enum


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionLog(BaseModel):
    timestamp: int
    level: str
    message: str
    node_id: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None


class Execution(BaseModel):
    id: str
    workflow_id: str
    status: ExecutionStatus
    started_at: int
    ended_at: Optional[int] = None
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Dict[str, Any] = Field(default_factory=dict)
    logs: List[ExecutionLog] = Field(default_factory=list)
    user_id: str
    session_id: Optional[str] = None 