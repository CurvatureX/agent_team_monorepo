from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ExecutionStatus(str, Enum):
    NEW = "NEW"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    CANCELED = "CANCELED"
    WAITING = "WAITING"
    PAUSED = "PAUSED"


class ExecutionLog(BaseModel):
    timestamp: int
    level: str
    message: str
    node_id: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None


class Execution(BaseModel):
    id: str  # 对应数据库的 id (UUID)
    execution_id: str  # 对应数据库的 execution_id
    workflow_id: str  # 对应数据库的 workflow_id (UUID)
    status: ExecutionStatus
    mode: Optional[str] = None  # 对应数据库的 mode
    triggered_by: Optional[str] = None  # 对应数据库的 triggered_by (可以作为 user_id)
    start_time: Optional[int] = None  # 对应数据库的 start_time
    end_time: Optional[int] = None  # 对应数据库的 end_time
    run_data: Optional[Dict[str, Any]] = None  # 对应数据库的 run_data
    metadata: Optional[Dict[str, Any]] = None  # 对应数据库的 metadata
    execution_metadata: Optional[Dict[str, Any]] = None  # 对应数据库的 execution_metadata
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
