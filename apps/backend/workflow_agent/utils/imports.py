"""
Unified import path management for workflow_agent
统一的导入路径管理，支持Docker和本地开发环境
"""

import os
import sys
from pathlib import Path


def setup_shared_imports():
    """
    设置shared models的导入路径
    支持Docker和本地开发环境
    """
    # 根据运行环境设置不同的导入路径
    if os.path.exists("/app/shared"):  # Docker 环境
        if "/app" not in sys.path:
            sys.path.insert(0, "/app")
    else:  # 本地开发环境
        # 从workflow_agent目录往上找到backend目录
        backend_dir = Path(__file__).parent.parent.parent
        backend_path = str(backend_dir)
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)


# 自动设置路径
setup_shared_imports()
