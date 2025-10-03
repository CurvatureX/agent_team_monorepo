"""
测试配置和工具函数
"""

import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class TestConfig:
    """测试配置类"""

    # URL配置
    api_gateway_url = "http://localhost:8000"
    workflow_agent_url = "localhost:50051"

    # Supabase配置
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_public_key = os.getenv("SUPABASE_PUB_KEY")
    test_email = os.getenv("TEST_USER_EMAIL")
    test_password = os.getenv("TEST_USER_PASSWORD")

    # 超时配置
    auth_timeout = 10.0
    session_timeout = 10.0
    chat_timeout = 20.0

    # 测试限制
    max_responses = 10
    max_wait_time = 30

    @classmethod
    def has_auth_config(cls) -> bool:
        """检查是否有完整的认证配置"""
        return all([cls.supabase_url, cls.supabase_public_key, cls.test_email, cls.test_password])

    @classmethod
    def get_auth_headers(cls, token: Optional[str] = None) -> Dict[str, str]:
        """获取认证headers"""
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers


# 全局测试配置实例
test_config = TestConfig
