"""
User Service - 用户管理服务
自动处理用户创建和验证
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from shared.logging_config import get_logger
logger = get_logger(__name__)


class UserService:
    """用户管理服务"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.logger = logger
    
    def ensure_user_exists(self, user_id: str, email: Optional[str] = None, name: Optional[str] = None) -> bool:
        """
        确保用户存在，如果不存在则创建
        
        Args:
            user_id: 用户ID
            email: 用户邮箱（可选）
            name: 用户姓名（可选）
            
        Returns:
            是否成功（用户已存在或创建成功）
        """
        try:
            # 检查用户是否已存在
            existing_user = self.db.execute(text("""
                SELECT id, email, name FROM users WHERE id = :user_id
            """), {"user_id": user_id}).fetchone()
            
            if existing_user:
                self.logger.debug(f"User already exists: {user_id}")
                return True
            
            # 生成默认值
            if not email:
                email = f"user_{user_id[:8]}@system.local"
            if not name:
                name = f"System User {user_id[:8]}"
            
            # 创建新用户
            current_time = datetime.now(timezone.utc)
            
            insert_query = text("""
                INSERT INTO users (
                    id, email, name, is_active, created_at, updated_at
                ) VALUES (
                    :user_id, :email, :name, :is_active, :created_at, :updated_at
                )
            """)
            
            self.db.execute(insert_query, {
                "user_id": user_id,
                "email": email,
                "name": name,
                "is_active": True,
                "created_at": current_time,
                "updated_at": current_time
            })
            
            self.db.commit()
            self.logger.info(f"Created new user: {user_id} ({email})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to ensure user exists: {user_id} - {e}")
            self.db.rollback()
            return False
    
    def get_user_info(self, user_id: str) -> Optional[dict]:
        """获取用户信息"""
        try:
            result = self.db.execute(text("""
                SELECT id, email, name, is_active, created_at
                FROM users WHERE id = :user_id
            """), {"user_id": user_id}).fetchone()
            
            if result:
                return {
                    "id": result[0],
                    "email": result[1], 
                    "name": result[2],
                    "is_active": result[3],
                    "created_at": result[4]
                }
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get user info: {user_id} - {e}")
            return None