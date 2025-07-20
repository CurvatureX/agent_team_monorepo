#!/usr/bin/env python3
"""
Session API 简单测试脚本
用于每次代码修改后快速验证基本功能
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


def test_basic_functionality():
    """测试基本功能"""
    print("🧪 Testing basic functionality...")
    
    # Mock所有外部依赖
    with patch("app.database.init_supabase"), \
         patch("app.services.grpc_client.workflow_client.connect"), \
         patch("app.services.grpc_client.workflow_client.close"):
        
        from app.main import app
        client = TestClient(app)
        
        # 测试健康检查
        response = client.get("/health")
        assert response.status_code == 200
        print("✅ Health check passed")
        
        # 测试根路径
        response = client.get("/")
        assert response.status_code == 200
        print("✅ Root endpoint passed")
        
        # 测试API文档
        response = client.get("/docs")
        assert response.status_code == 200
        print("✅ API docs accessible")
        
        print("🎉 Basic functionality tests passed!")


def test_session_creation():
    """测试会话创建"""
    print("🧪 Testing session creation...")
    
    with patch("app.database.init_supabase"), \
         patch("app.services.grpc_client.workflow_client.connect"), \
         patch("app.services.grpc_client.workflow_client.close"), \
         patch("app.database.sessions_repo") as mock_repo:
        
        # 设置mock返回值 - 这次直接返回我们想要的结果
        mock_repo.create.return_value = {
            "id": "test-session-123",
            "created_at": "2023-01-01T00:00:00Z",
            "user_id": None,
            "meta_data": {"auth_type": "guest"}
        }
        
        from app.main import app
        client = TestClient(app)
        
        # 测试创建会话
        response = client.post("/api/v1/session", json={})
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Session created: {data.get('session_id')}")
            print("✅ Session creation passed")
        else:
            print(f"⚠️  Session creation returned {response.status_code}")
            print(f"Response: {response.json()}")
        
        # 验证数据库调用
        if mock_repo.create.called:
            print("✅ Database create method was called")
        else:
            print("⚠️  Database create method was not called")


def test_with_real_mock():
    """使用更真实的mock测试"""
    print("🧪 Testing with real mock...")
    
    # 创建一个真实的mock对象
    mock_session_repo = MagicMock()
    mock_session_repo.create.return_value = {
        "id": "mock-session-456",
        "created_at": "2023-01-01T00:00:00Z",
        "user_id": None,
        "meta_data": {"auth_type": "guest"}
    }
    
    with patch("app.database.init_supabase"), \
         patch("app.services.grpc_client.workflow_client.connect"), \
         patch("app.services.grpc_client.workflow_client.close"), \
         patch("app.database.sessions_repo", mock_session_repo):
        
        from app.main import app
        client = TestClient(app)
        
        # 测试创建会话
        response = client.post("/api/v1/session", json={})
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Session ID: {data.get('session_id')}")
            print("✅ Real mock test passed")
        else:
            print(f"⚠️  Response: {response.json()}")


def test_models():
    """测试数据模型"""
    print("🧪 Testing data models...")
    
    try:
        from app.models import SessionCreateRequest, SessionResponse
        
        # 测试创建请求
        request = SessionCreateRequest(meta_data={"test": "value"})
        print(f"✅ SessionCreateRequest: {request.meta_data}")
        
        # 测试响应
        response = SessionResponse(
            session_id="test-123",
            created_at="2023-01-01T00:00:00Z"
        )
        print(f"✅ SessionResponse: {response.session_id}")
        
        print("✅ Model tests passed")
        
    except Exception as e:
        print(f"❌ Model test failed: {e}")


def main():
    """主函数"""
    print("🚀 Running session simple tests...")
    print("=" * 50)
    
    try:
        test_models()
        print()
        
        test_basic_functionality()
        print()
        
        test_session_creation()
        print()
        
        test_with_real_mock()
        print()
        
        print("🎉 All simple tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()