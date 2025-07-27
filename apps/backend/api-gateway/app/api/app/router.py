"""
App API路由聚合器 - Supabase OAuth + RLS
专为Web/Mobile应用设计，需要用户认证
"""

from fastapi import APIRouter
from . import sessions, chat, workflows

# 创建App API总路由器
router = APIRouter()

# 包含所有App API子路由
router.include_router(sessions.router, prefix="", tags=["sessions"])
router.include_router(chat.router, prefix="/chat", tags=["chat"])
router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
