"""
测试配置和工具函数
"""

import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class TestConfig:
    """测试配置类"""
    
    def __init__(self):
        self.api_gateway_url = "http://localhost:8000"
        self.workflow_agent_url = "localhost:50051"
        
        # Supabase配置
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
        self.test_email = os.getenv("TEST_USER_EMAIL")
        self.test_password = os.getenv("TEST_USER_PASSWORD")
        
        # 超时配置
        self.auth_timeout = 10.0
        self.session_timeout = 10.0
        self.chat_timeout = 20.0
        
        # 测试限制
        self.max_responses = 10
        self.max_wait_time = 30
    
    def has_auth_config(self) -> bool:
        """检查是否有完整的认证配置"""
        return all([
            self.supabase_url,
            self.supabase_anon_key, 
            self.test_email,
            self.test_password
        ])
    
    def get_auth_headers(self, token: Optional[str] = None) -> Dict[str, str]:
        """获取认证headers"""
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

# 全局测试配置实例
test_config = TestConfig()