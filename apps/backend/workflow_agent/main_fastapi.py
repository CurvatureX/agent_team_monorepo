#!/usr/bin/env python3
"""
Workflow Agent FastAPI 启动入口
从 workflow_agent 根目录启动 FastAPI 服务器
"""

import os
import sys
import uvicorn

# 设置正确的 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

# 根据运行环境设置不同的导入路径
if os.path.exists('/app/shared'):  # Docker 环境
    sys.path.insert(0, '/app')
    from services.fastapi_server import app
    from core.config import settings
else:  # 本地开发环境
    sys.path.insert(0, parent_dir)  # 添加 backend 目录到路径
    sys.path.insert(0, current_dir)  # 添加 workflow_agent 目录到路径
    from services.fastapi_server import app
    from core.config import settings

def main():
    """启动 FastAPI 服务器"""
    port = getattr(settings, 'FASTAPI_PORT', None) or int(os.getenv('FASTAPI_PORT', '8001'))
    host = os.getenv('HOST', '0.0.0.0')
    
    print(f"🚀 启动 Workflow Agent FastAPI 服务器")
    print(f"   地址: http://{host}:{port}")
    print(f"   文档: http://{host}:{port}/docs")
    print(f"   健康检查: http://{host}:{port}/health")
    
    # 在 Docker 环境中禁用 reload 模式
    reload_mode = os.getenv('DEBUG', 'false').lower() == 'true' and not os.path.exists('/app/shared')
    
    uvicorn.run(
        app, 
        host=host, 
        port=port,
        reload=reload_mode,
        access_log=True
    )

if __name__ == "__main__":
    main()