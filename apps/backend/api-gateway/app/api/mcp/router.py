"""
MCP API Router
MCP API路由，需要API Key认证
专为LLM客户端设计
"""

from fastapi import APIRouter
from . import tools

# 创建MCP API总路由器
router = APIRouter()

# 包含所有MCP API子路由
router.include_router(tools.router, prefix="", tags=["MCP - Tools"])

# 可以在这里添加其他MCP API路由
# router.include_router(models.router, prefix="/models", tags=["MCP - Models"])
# router.include_router(knowledge.router, prefix="/knowledge", tags=["MCP - Knowledge"])
