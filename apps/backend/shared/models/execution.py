from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from enum import Enum


class ExecutionStatus(str, Enum):
    NEW = "NEW"
    PENDING = "pending"
    RUNNING = "RUNNING"  # Match database constraint (uppercase)
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    CANCELED = "CANCELED"
    WAITING = "WAITING"


class ExecutionLog(BaseModel):
    timestamp: int
    level: str
    message: str
    node_id: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None


class NodePerformanceMetrics(BaseModel):
    """节点性能指标"""
    execution_time: float
    memory_usage: Dict[str, Any] = Field(default_factory=dict)
    cpu_usage: Dict[str, Any] = Field(default_factory=dict)


class NodeExecutionResult(BaseModel):
    """单个节点的执行结果"""
    status: str
    logs: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    output_data: Dict[str, Any] = Field(default_factory=dict)
    error_details: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_time: float
    input_data_summary: Optional[Dict[str, Any]] = None
    output_data_summary: Optional[Dict[str, Any]] = None
    performance_metrics: NodePerformanceMetrics


class ExecutionPerformanceMetrics(BaseModel):
    """整体执行性能指标"""
    total_execution_time: float
    node_execution_times: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    memory_usage: Dict[str, Any] = Field(default_factory=dict)
    cpu_usage: Dict[str, Any] = Field(default_factory=dict)


class ExecutionRunData(BaseModel):
    """执行运行时详细数据"""
    node_results: Dict[str, NodeExecutionResult] = Field(default_factory=dict)
    execution_order: List[str] = Field(default_factory=list)
    performance_metrics: ExecutionPerformanceMetrics


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
    run_data: Optional[ExecutionRunData] = None  # 新增：详细执行数据 