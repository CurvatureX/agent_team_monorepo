"""
MCP (Model Context Protocol) Models
MCP相关的数据模型
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import Field, PrivateAttr

from .common import BaseModel


class MCPTool(BaseModel):
    """
    MCP工具模型 - 符合MCP JSON-RPC 2.0标准
    """

    name: str = Field(description="工具名称")
    description: Optional[str] = Field(default=None, description="工具描述")
    inputSchema: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="输入参数JSON Schema", alias="parameters"
    )
    annotations: Optional[Dict[str, Any]] = Field(default_factory=dict, description="工具注解和提示")

    # Optional fields for internal use
    required_scopes: List[str] = Field(default_factory=list, description="所需权限范围", exclude=True)
    category: Optional[str] = Field(
        default=None, description="工具分类"
    )  # Include in API response for tool discovery
    version: Optional[str] = Field(default="1.0.0", description="工具版本", exclude=True)
    tags: List[str] = Field(default_factory=list, description="工具标签", exclude=True)

    model_config = {"validate_by_name": True}


class MCPInvokeRequest(BaseModel):
    """
    MCP工具调用请求模型 - 符合MCP tools/call标准
    """

    name: str = Field(description="要调用的工具名称")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="工具调用参数")

    # Backwards compatibility aliases
    tool_name: Optional[str] = Field(default=None, description="工具名称（向后兼容）", exclude=True)
    parameters: Optional[Dict[str, Any]] = Field(
        default=None, description="工具参数（向后兼容）", exclude=True
    )

    def __init__(self, **data):
        # Handle backwards compatibility
        if "tool_name" in data and "name" not in data:
            data["name"] = data["tool_name"]
        if "parameters" in data and "arguments" not in data:
            data["arguments"] = data["parameters"]
        super().__init__(**data)


class MCPContentItem(BaseModel):
    """
    MCP内容项模型
    """

    type: str = Field(description="内容类型")
    text: Optional[str] = Field(default=None, description="文本内容")
    data: Optional[Dict[str, Any]] = Field(default=None, description="数据内容")


class MCPInvokeResponse(BaseModel):
    """
    MCP工具调用响应模型 - 符合MCP tools/call标准
    """

    content: List[MCPContentItem] = Field(default_factory=list, description="响应内容数组")
    isError: bool = Field(default=False, description="是否为错误响应")

    # Optional structured content for complex responses
    structuredContent: Optional[Dict[str, Any]] = Field(default=None, description="结构化内容")

    # Internal fields for backwards compatibility (private attributes)
    _success: Optional[bool] = PrivateAttr(default=None)
    _tool_name: Optional[str] = PrivateAttr(default=None)
    _execution_time_ms: Optional[float] = PrivateAttr(default=None)
    _request_id: Optional[str] = PrivateAttr(default=None)


class MCPToolsResponse(BaseModel):
    """
    MCP工具列表响应模型
    """

    success: bool = Field(default=True, description="请求是否成功")
    tools: List[MCPTool] = Field(default_factory=list, description="可用工具列表")
    total_count: int = Field(default=0, description="工具总数")
    available_count: int = Field(default=0, description="可用工具数")
    categories: List[str] = Field(default_factory=list, description="工具分类列表")
    timestamp: Optional[Any] = Field(default=None, description="响应时间戳")
    processing_time_ms: Optional[float] = Field(default=None, description="处理时间（毫秒）")
    request_id: Optional[str] = Field(default=None, description="请求ID")


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
