#!/usr/bin/env python3
"""
固定的后端启动脚本，确保环境变量正确加载
"""

import os
import sys
from pathlib import Path

# 添加backend目录到Python路径
backend_dir = Path(__file__).parent.parent  # workflow_engine的parent就是backend
sys.path.insert(0, str(backend_dir))
# 同时添加当前目录以便导入workflow_engine模块
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# 手动加载环境变量
from dotenv import load_dotenv

env_path = backend_dir / ".env"
print(f"🔍 加载环境变量从: {env_path}")
print(f"📁 文件存在: {env_path.exists()}")
load_dotenv(env_path)

# 验证关键环境变量
required_vars = ["DATABASE_URL"]
missing_vars = []

for var in required_vars:
    if not os.getenv(var):
        missing_vars.append(var)

if missing_vars:
    print(f"❌ 缺少环境变量: {', '.join(missing_vars)}")
    sys.exit(1)

print("✅ 环境变量验证通过")
print(f"📊 DATABASE_URL: {os.getenv('DATABASE_URL')[:50]}...")
print(f"🔧 PORT: {os.getenv('PORT', '8002')}")

# 启动服务
if __name__ == "__main__":
    import uvicorn

    from workflow_engine.main import app

    port = int(os.getenv("PORT", "8002"))
    host = os.getenv("HOST", "0.0.0.0")

    print(f"🚀 启动服务: http://{host}:{port}")

    uvicorn.run(app, host=host, port=port, reload=False)  # 禁用reload避免多进程问题
