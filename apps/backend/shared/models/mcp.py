"""
MCP (Model Context Protocol) Models
MCP相关的数据模型
"""

from typing import Any, Dict, List, Optional

from pydantic import Field

from .common import BaseModel


class MCPTool(BaseModel):
    """
    MCP工具模型
    """

    name: str = Field(description="工具名称")
    description: Optional[str] = Field(default=None, description="工具描述")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="工具参数定义")
    required_scopes: List[str] = Field(default_factory=list, description="所需权限范围")
    category: Optional[str] = Field(default=None, description="工具分类")
    version: Optional[str] = Field(default="1.0.0", description="工具版本")


class MCPInvokeRequest(BaseModel):
    """
    MCP工具调用请求模型
    """

    tool_name: str = Field(description="要调用的工具名称")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="工具调用参数")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="调用上下文")
    timeout: Optional[int] = Field(default=30, description="调用超时时间（秒）")


class MCPInvokeResponse(BaseModel):
    """
    MCP工具调用响应模型
    """

    success: bool = Field(description="调用是否成功")
    result: Optional[Dict[str, Any]] = Field(default=None, description="调用结果")
    error: Optional[str] = Field(default=None, description="错误信息")
    tool_name: str = Field(description="被调用的工具名称")
    execution_time: Optional[float] = Field(default=None, description="执行时间（秒）")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="调用元数据")


class MCPToolsResponse(BaseModel):
    """
    MCP工具列表响应模型
    """

    tools: List[MCPTool] = Field(default_factory=list, description="可用工具列表")
    total_count: int = Field(default=0, description="工具总数")
    available_count: int = Field(default=0, description="可用工具数")
    categories: List[str] = Field(default_factory=list, description="工具分类列表")


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


class MCPErrorResponse(BaseModel):
    """
    MCP错误响应模型
    """

    success: bool = Field(default=False, description="请求失败")
    error: str = Field(description="错误信息")
    error_type: str = Field(description="错误类型")
    tool_name: Optional[str] = Field(default=None, description="相关工具名称")
    request_id: Optional[str] = Field(default=None, description="请求ID")
    details: Optional[Dict[str, Any]] = Field(default=None, description="错误详情")
