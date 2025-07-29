#!/usr/bin/env python3
"""
简化的测试检查 - 诊断问题
"""

import asyncio
import httpx
import os
from pathlib import Path

async def check_api_gateway():
    """检查API Gateway是否运行"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health", timeout=5.0)
            print(f"✅ API Gateway 响应: {response.status_code}")
            return True
    except Exception as e:
        print(f"❌ API Gateway 连接失败: {e}")
        return False

async def check_environment():
    """检查环境变量"""
    required_vars = ["SUPABASE_URL", "OPENAI_API_KEY"]
    missing = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"⚠️ 缺少环境变量: {', '.join(missing)}")
        return False
    else:
        print("✅ 关键环境变量存在")
        return True

async def check_proto_files():
    """检查proto文件"""
    files_to_check = [
        "shared/proto/workflow_agent_pb2.py",
        "api-gateway/proto/workflow_agent_pb2.py",
        "workflow_agent/workflow_agent_pb2.py"
    ]
    
    missing = []
    for file_path in files_to_check:
        if not Path(file_path).exists():
            missing.append(file_path)
    
    if missing:
        print(f"❌ 缺少proto文件: {missing}")
        return False
    else:
        print("✅ Proto文件存在")
        return True

async def test_imports():
    """测试关键导入"""
    try:
        # 测试api-gateway导入
        import sys
        sys.path.append("api-gateway")
        
        from app.services.grpc_client import WorkflowGRPCClient
        print("✅ gRPC客户端导入成功")
        
        # 测试proto导入
        sys.path.append("api-gateway/proto")
        import workflow_agent_pb2
        print("✅ Proto文件导入成功")
        
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False

async def main():
    print("🔍 开始诊断检查...")
    
    # 检查proto文件
    proto_ok = await check_proto_files()
    
    # 检查导入
    import_ok = await test_imports()
    
    # 检查环境变量
    env_ok = await check_environment()
    
    # 检查API Gateway
    api_ok = await check_api_gateway()
    
    print(f"\n📊 诊断结果:")
    print(f"Proto文件: {'✅' if proto_ok else '❌'}")
    print(f"导入检查: {'✅' if import_ok else '❌'}")
    print(f"环境变量: {'✅' if env_ok else '❌'}")
    print(f"API Gateway: {'✅' if api_ok else '❌'}")
    
    if all([proto_ok, import_ok]):
        print("\n✅ 基础检查通过，可以运行简化测试")
    else:
        print("\n❌ 发现问题，需要修复")

if __name__ == "__main__":
    asyncio.run(main())