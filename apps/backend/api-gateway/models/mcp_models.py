"""
Pydantic models for MCP service
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MCPToolSchema(BaseModel):
    """Schema for MCP tool definition"""

    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    parameters: Dict[str, Any] = Field(..., description="Tool parameter schema")


class MCPToolsResponse(BaseModel):
    """Response model for tool discovery endpoint"""

    tools: List[MCPToolSchema] = Field(..., description="List of available tools")


class MCPInvokeRequest(BaseModel):
    """Request model for tool invocation"""

    tool_name: str = Field(..., description="Name of the tool to invoke")
    params: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")


class MCPInvokeResponse(BaseModel):
    """Response model for tool invocation"""

    success: bool = Field(..., description="Whether the tool execution was successful")
    result: Optional[Dict[str, Any]] = Field(None, description="Tool execution result")
    error: Optional[str] = Field(None, description="Error message if execution failed")


class MCPErrorResponse(BaseModel):
    """Enhanced error response model with comprehensive error information"""

    success: bool = Field(False, description="Always false for error responses")
    error: str = Field(..., description="User-friendly error message")
    error_type: str = Field(..., description="Error type classification")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    error_id: Optional[str] = Field(None, description="Unique error identifier for tracking")
    request_id: Optional[str] = Field(None, description="Request identifier for tracing")
    retryable: Optional[bool] = Field(None, description="Whether the error is retryable")
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retrying")
    timestamp: Optional[float] = Field(None, description="Error timestamp")
    recovery_suggestions: Optional[List[str]] = Field(
        None, description="Suggested recovery actions"
    )
    support_info: Optional[Dict[str, str]] = Field(None, description="Support contact information")


class NodeKnowledgeResult(BaseModel):
    """Result model for node knowledge retrieval"""

    node_name: str = Field(..., description="Name of the node")
    knowledge: str = Field(..., description="Knowledge content for the node")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Node metadata")
    similarity_score: Optional[float] = Field(None, description="Similarity score if applicable")


class NodeKnowledgeResponse(BaseModel):
    """Response model for node knowledge retrieval"""

    success: bool = Field(..., description="Whether the retrieval was successful")
    results: List[NodeKnowledgeResult] = Field(..., description="List of node knowledge results")
    total_nodes: int = Field(..., description="Total number of nodes processed")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")


# Tool registry definition
TOOL_REGISTRY = {
    "node_knowledge_retriever": {
        "name": "node_knowledge_retriever",
        "description": "根据节点名称列表检索节点知识信息",
        "parameters": {
            "type": "object",
            "properties": {
                "node_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "需要检索知识的节点名称列表",
                },
                "include_metadata": {
                    "type": "boolean",
                    "description": "是否包含节点元数据信息",
                    "default": False,
                },
            },
            "required": ["node_names"],
        },
    },
    "elasticsearch": {
        "name": "elasticsearch",
        "description": "Elasticsearch搜索工具",
        "parameters": {
            "type": "object",
            "properties": {
                "index": {"type": "string", "description": "索引名"},
                "query": {"type": "object", "description": "查询条件"},
            },
            "required": ["index", "query"],
        },
    },
}
