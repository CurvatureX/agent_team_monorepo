#!/usr/bin/env python3
"""
快速测试脚本 - 验证基本功能
使用方法: uv run python quick_test.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

def check_dependencies():
    """检查必要的依赖是否安装"""
    try:
        import fastapi
        import supabase
        print("✅ 依赖检查通过")
        return True
    except ImportError as e:
        print(f"❌ 依赖缺失: {e}")
        print("请使用: uv run python quick_test.py")
        return False

def check_app_module():
    """检查app模块是否可用"""
    try:
        import app
        import app.database
        import app.main
        print("✅ 应用模块检查通过")
        return True
    except ImportError as e:
        print(f"❌ 应用模块缺失: {e}")
        print("请确保在项目根目录运行，或使用: uv run python quick_test.py")
        return False

from unittest.mock import patch
from fastapi.testclient import TestClient


def main():
    """主测试函数"""
    print("🚀 Running quick session tests...")
    
    # 检查依赖
    if not check_dependencies():
        return False
    
    # 检查应用模块
    if not check_app_module():
        return False
    
    # Mock外部依赖
    with patch("app.database.init_supabase"), \
         patch("app.services.grpc_client.workflow_client.connect"), \
         patch("app.services.grpc_client.workflow_client.close"):
        
        from app.main import app
        client = TestClient(app)
        
        print("\n1. 测试健康检查...")
        response = client.get("/health")
        if response.status_code == 200:
            print("✅ 健康检查通过")
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
            return False
        
        print("\n2. 测试根路径...")
        response = client.get("/")
        if response.status_code == 200:
            print("✅ 根路径通过")
        else:
            print(f"❌ 根路径失败: {response.status_code}")
            return False
        
        print("\n3. 测试API文档...")
        response = client.get("/docs")
        if response.status_code == 200:
            print("✅ API文档可访问")
        else:
            print(f"❌ API文档失败: {response.status_code}")
            return False
        
        print("\n4. 测试OpenAPI schema...")
        response = client.get("/openapi.json")
        if response.status_code == 200:
            print("✅ OpenAPI schema可访问")
        else:
            print(f"❌ OpenAPI schema失败: {response.status_code}")
            return False
        
        print("\n5. 测试Guest会话创建 (无需认证)...")
        response = client.post("/api/v1/session", json={})
        if response.status_code == 200:
            print("✅ Guest会话创建成功")
        else:
            print(f"⚠️  Guest会话创建失败: {response.status_code} (这是预期的，因为需要数据库)")
        
        print("\n6. 测试认证端点 (应该需要JWT token)...")
        response = client.post("/api/v1/chat", json={"message": "test"})
        if response.status_code == 401:
            print("✅ 认证中间件正常工作 (要求JWT token)")
        else:
            print(f"⚠️  认证中间件可能有问题: {response.status_code}")
        
        print("\n🎉 前端认证架构测试完成!")
        print("📝 注意: 实际使用时需要从前端获得Supabase JWT token")
        return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)