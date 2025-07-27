"""
Database Connection and Management
统一的数据库连接管理，支持Supabase和Redis
"""

from typing import Optional, Dict, Any
from functools import lru_cache
from supabase import create_client, Client

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from app.core.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """数据库连接管理器"""

    def __init__(self):
        self._supabase_client: Optional[Client] = None
        self._supabase_admin_client: Optional[Client] = None
        self._redis_client: Optional[redis.Redis] = None
        self._settings = get_settings()

    @property
    def supabase(self) -> Optional[Client]:
        """获取Supabase客户端（用户级别，支持RLS）"""
        if not self._supabase_client:
            self._supabase_client = self._create_supabase_client()
        return self._supabase_client

    @property
    def supabase_admin(self) -> Optional[Client]:
        """获取Supabase管理客户端（服务级别，绕过RLS）"""
        if not self._supabase_admin_client:
            self._supabase_admin_client = self._create_supabase_admin_client()
        return self._supabase_admin_client

    @property
    def redis(self) -> Optional[Any]:
        """获取Redis客户端"""
        if not self._redis_client:
            self._redis_client = self._create_redis_client()
        return self._redis_client

    def _create_supabase_client(self) -> Optional[Client]:
        """创建Supabase用户客户端"""
        try:
            if not self._settings.SUPABASE_URL or not self._settings.SUPABASE_ANON_KEY:
                logger.warning("🔶 Supabase configuration incomplete for user client")
                return None

            client = create_client(self._settings.SUPABASE_URL, self._settings.SUPABASE_ANON_KEY)

            logger.info("✅ Supabase user client initialized")
            return client

        except Exception as e:
            logger.error(f"❌ Failed to create Supabase user client: {e}")
            return None

    def _create_supabase_admin_client(self) -> Optional[Client]:
        """创建Supabase管理客户端"""
        try:
            if not self._settings.SUPABASE_URL or not self._settings.SUPABASE_SECRET_KEY:
                logger.warning("🔶 Supabase configuration incomplete for admin client")
                return None

            client = create_client(self._settings.SUPABASE_URL, self._settings.SUPABASE_SECRET_KEY)

            logger.info("✅ Supabase admin client initialized")
            return client

        except Exception as e:
            logger.error(f"❌ Failed to create Supabase admin client: {e}")
            return None

    def _create_redis_client(self) -> Optional[Any]:
        """创建Redis客户端"""
        try:
            if not REDIS_AVAILABLE:
                logger.warning("🔶 Redis module not available")
                return None

            if not self._settings.REDIS_URL:
                logger.warning("🔶 Redis URL not configured")
                return None

            client = redis.from_url(
                self._settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
            )

            # 测试连接
            client.ping()
            logger.info("✅ Redis client initialized and connected")
            return client

        except Exception as e:
            logger.error(f"❌ Failed to create Redis client: {e}")
            return None

    def create_user_client(self, access_token: str) -> Optional[Client]:
        """为特定用户创建带认证的Supabase客户端"""
        try:
            if not self._settings.SUPABASE_URL or not self._settings.SUPABASE_ANON_KEY:
                return None

            client = create_client(self._settings.SUPABASE_URL, self._settings.SUPABASE_ANON_KEY)

            # 设置用户认证令牌
            client.auth.set_auth(access_token)

            return client

        except Exception as e:
            logger.error(f"❌ Failed to create user-specific Supabase client: {e}")
            return None

    async def health_check(self) -> Dict[str, Any]:
        """数据库健康检查"""
        health_status = {
            "supabase": False,
            "supabase_admin": False,
            "redis": False,
            "overall": False,
        }

        # 检查Supabase用户客户端
        try:
            if self.supabase:
                # 简单查询测试连接
                result = self.supabase.auth.get_user()
                health_status["supabase"] = True
        except Exception as e:
            logger.warning(f"🔶 Supabase user client health check failed: {e}")

        # 检查Supabase管理客户端
        try:
            if self.supabase_admin:
                # 查询一个系统表测试连接
                result = self.supabase_admin.table("pg_tables").select("*").limit(1).execute()
                health_status["supabase_admin"] = True
        except Exception as e:
            logger.warning(f"🔶 Supabase admin client health check failed: {e}")

        # 检查Redis
        try:
            if self.redis:
                self.redis.ping()
                health_status["redis"] = True
        except Exception as e:
            logger.warning(f"🔶 Redis health check failed: {e}")

        # 整体健康状态
        health_status["overall"] = any([health_status["supabase"], health_status["supabase_admin"]])

        return health_status

    def close_connections(self):
        """关闭所有数据库连接"""
        try:
            if self._redis_client:
                self._redis_client.close()
                logger.info("✅ Redis connection closed")
        except Exception as e:
            logger.error(f"❌ Error closing Redis connection: {e}")

        # Supabase客户端不需要显式关闭
        logger.info("✅ Database connections cleanup completed")


# 全局数据库管理器实例
@lru_cache()
def get_database_manager() -> DatabaseManager:
    """获取数据库管理器实例（单例模式）"""
    return DatabaseManager()


# 便捷的数据库客户端获取函数
def get_supabase() -> Optional[Client]:
    """获取Supabase用户客户端"""
    return get_database_manager().supabase


def get_supabase_admin() -> Optional[Client]:
    """获取Supabase管理客户端"""
    return get_database_manager().supabase_admin


def get_redis() -> Optional[Any]:
    """获取Redis客户端"""
    return get_database_manager().redis


def create_user_supabase_client(access_token: str) -> Optional[Client]:
    """为特定用户创建Supabase客户端"""
    return get_database_manager().create_user_client(access_token)


# FastAPI依赖注入函数
async def get_database_manager_dependency() -> DatabaseManager:
    """用于FastAPI依赖注入的数据库管理器获取函数"""
    return get_database_manager()


async def get_supabase_dependency() -> Optional[Client]:
    """用于FastAPI依赖注入的Supabase客户端获取函数"""
    return get_supabase()


async def get_redis_dependency() -> Optional[Any]:
    """用于FastAPI依赖注入的Redis客户端获取函数"""
    return get_redis()
