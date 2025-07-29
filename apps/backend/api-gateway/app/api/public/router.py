"""
Public API Router
公共API路由，无需认证，仅限流
专为外部系统和公开访问设计
"""

from app.api.public import docs, health, validation  # status temporarily disabled due to proto issues
from fastapi import APIRouter

# 创建Public API总路由器
router = APIRouter()

# Include all Public API sub-routes
router.include_router(health.router, prefix="", tags=["Public - Health"])
# router.include_router(status.router, prefix="", tags=["Public - Status"])  # Temporarily disabled
router.include_router(docs.router, prefix="", tags=["Public - Documentation"])
router.include_router(validation.router, prefix="", tags=["Public - Validation"])
