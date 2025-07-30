#!/usr/bin/env python3
"""
Workflow Agent FastAPI 启动入口
从 workflow_agent 根目录启动 FastAPI 服务器
"""

import os
import sys

# 统一导入路径管理
from pathlib import Path

import uvicorn

current_dir = Path(__file__).parent
backend_dir = current_dir.parent

# 根据运行环境设置不同的导入路径
if os.path.exists("/app/shared"):  # Docker 环境
    if "/app" not in sys.path:
        sys.path.insert(0, "/app")
else:  # 本地开发环境
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))  # 添加 backend 目录到路径
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))  # 添加 workflow_agent 目录到路径

from core.config import settings
from services.fastapi_server import app


def main():
    """启动 FastAPI 服务器"""
    port = getattr(settings, "FASTAPI_PORT", None) or int(os.getenv("FASTAPI_PORT", "8001"))
    host = os.getenv("HOST", "0.0.0.0")

    print(f"🚀 启动 Workflow Agent FastAPI 服务器")
    print(f"   地址: http://{host}:{port}")
    print(f"   文档: http://{host}:{port}/docs")
    print(f"   健康检查: http://{host}:{port}/health")

    # 在 Docker 环境中禁用 reload 模式
    reload_mode = os.getenv("DEBUG", "false").lower() == "true" and not os.path.exists(
        "/app/shared"
    )

    uvicorn.run(app, host=host, port=port, reload=reload_mode, access_log=True)


if __name__ == "__main__":
    main()
