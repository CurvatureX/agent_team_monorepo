"""
MCP (Model Context Protocol) Models
MCP相关的数据模型
"""

from typing import Optional, Dict, Any, List
from pydantic import Field, validator

from .base import BaseModel, EntityModel, ResponseModel


class MCPTool(BaseModel):
    """
    MCP工具模型
    表示可用的MCP工具
    """

    name: str = Field(description="工具名称")
    description: str = Field(description="工具描述")
    version: str = Field(default="1.0.0", description="工具版本")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="工具参数架构")
    available: bool = Field(default=True, description="工具是否可用")
    category: Optional[str] = Field(default=None, description="工具分类")
    tags: List[str] = Field(default_factory=list, description="工具标签")
    examples: List[Dict[str, Any]] = Field(default_factory=list, description="使用示例")


class MCPInvokeRequest(BaseModel):
    """
    MCP工具调用请求模型
    """

    tool_name: str = Field(description="要调用的工具名称")
    params: Dict[str, Any] = Field(default_factory=dict, description="工具参数")
    timeout: Optional[int] = Field(default=30, ge=1, le=300, description="超时时间（秒，1-300）")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="执行上下文")

    @validator("tool_name")
    def validate_tool_name(cls, v):
        """验证工具名称"""
        if not v or not v.strip():
            raise ValueError("Tool name cannot be empty")
        return v.strip()


class MCPInvokeResponse(ResponseModel):
    """
    MCP工具调用响应模型
    """

    tool_name: str = Field(description="调用的工具名称")
    result: Optional[Dict[str, Any]] = Field(default=None, description="执行结果")
    error: Optional[str] = Field(default=None, description="错误信息")
    error_type: Optional[str] = Field(default=None, description="错误类型")
    execution_time_ms: Optional[int] = Field(default=None, description="执行时间（毫秒）")
    request_id: Optional[str] = Field(default=None, description="请求ID")


class MCPToolsResponse(ResponseModel):
    """
    MCP工具列表响应模型
    """

    tools: List[MCPTool] = Field(default_factory=list, description="可用工具列表")
    total_count: int = Field(default=0, description="工具总数")
    available_count: int = Field(default=0, description="可用工具数")
    categories: List[str] = Field(default_factory=list, description="工具分类列表")


class MCPToolInfo(BaseModel):
    """
    MCP工具详细信息模型
    """

    tool: MCPTool = Field(description="工具基本信息")
    usage_stats: Optional[Dict[str, Any]] = Field(default=None, description="使用统计")
    documentation: Optional[str] = Field(default=None, description="详细文档")
    changelog: Optional[List[Dict[str, Any]]] = Field(default=None, description="版本变更记录")


class MCPHealthCheck(BaseModel):
    """
    MCP服务健康检查模型
    """

    healthy: bool = Field(description="服务是否健康")
    version: str = Field(description="服务版本")
    available_tools: List[str] = Field(default_factory=list, description="可用工具名称列表")
    timestamp: int = Field(description="检查时间戳")
    processing_time_ms: Optional[float] = Field(default=None, description="处理时间（毫秒）")
    error: Optional[str] = Field(default=None, description="错误信息")
    request_id: Optional[str] = Field(default=None, description="请求ID")


class MCPErrorResponse(ResponseModel):
    """
    MCP错误响应模型
    """

    success: bool = Field(default=False, description="请求失败")
    error: str = Field(description="错误信息")
    error_type: str = Field(description="错误类型")
    tool_name: Optional[str] = Field(default=None, description="相关工具名称")
    request_id: Optional[str] = Field(default=None, description="请求ID")
    details: Optional[Dict[str, Any]] = Field(default=None, description="错误详情")


class MCPExecutionLog(EntityModel):
    """
    MCP执行日志模型
    """

    client_id: str = Field(description="客户端ID")
    tool_name: str = Field(description="工具名称")
    request_params: Dict[str, Any] = Field(description="请求参数")
    response_data: Optional[Dict[str, Any]] = Field(default=None, description="响应数据")
    status: str = Field(description="执行状态 (success, error, timeout)")
    execution_time_ms: int = Field(description="执行时间（毫秒）")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    ip_address: Optional[str] = Field(default=None, description="客户端IP地址")
    user_agent: Optional[str] = Field(default=None, description="用户代理")


class MCPBatchRequest(BaseModel):
    """
    MCP批量请求模型
    """

    requests: List[MCPInvokeRequest] = Field(description="批量请求列表")
    parallel: bool = Field(default=False, description="是否并行执行")
    fail_fast: bool = Field(default=False, description="是否快速失败")
    timeout: Optional[int] = Field(default=60, ge=1, le=600, description="总超时时间（秒）")

    @validator("requests")
    def validate_requests(cls, v):
        """验证请求列表"""
        if not v:
            raise ValueError("Requests list cannot be empty")
        if len(v) > 10:
            raise ValueError("Maximum 10 requests allowed per batch")
        return v


class MCPBatchResponse(ResponseModel):
    """
    MCP批量响应模型
    """

    responses: List[MCPInvokeResponse] = Field(description="批量响应列表")
    total_requests: int = Field(description="总请求数")
    successful_requests: int = Field(description="成功请求数")
    failed_requests: int = Field(description="失败请求数")
    total_execution_time_ms: int = Field(description="总执行时间（毫秒）")
    parallel_execution: bool = Field(description="是否并行执行")
