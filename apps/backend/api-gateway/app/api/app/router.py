"""
App API Router
应用API路由，需要Supabase OAuth认证
专为Web/Mobile应用设计，支持RLS
"""

from app.api.app import chat, sessions, workflows, executions
from fastapi import APIRouter

# 创建App API总路由器
router = APIRouter()

# 包含所有App API子路由
router.include_router(sessions.router, prefix="", tags=["App - Sessions"])
router.include_router(chat.router, prefix="/chat", tags=["App - Chat"])
router.include_router(workflows.router, prefix="/workflows", tags=["App - Workflows"])
router.include_router(executions.router, prefix="", tags=["App - Executions"])

# 可以在这里添加其他应用API路由
# router.include_router(users.router, prefix="/users", tags=["App - Users"])
# router.include_router(files.router, prefix="/files", tags=["App - Files"])
