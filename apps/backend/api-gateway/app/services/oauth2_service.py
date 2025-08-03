"""
OAuth2 Service Client for API Gateway
Integrates with the OAuth2Service in workflow_engine via database connection
"""

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from app.core.config import get_settings
from app.core.database import get_supabase_admin

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class AuthUrlResponse:
    """OAuth2授权URL响应"""
    auth_url: str
    state: str
    expires_at: datetime
    provider: str
    scopes: List[str]


@dataclass
class TokenResponse:
    """OAuth2令牌响应"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_at: Optional[datetime] = None
    scope: List[str] = None


@dataclass
class CredentialData:
    """用户凭证数据"""
    provider: str
    is_valid: bool
    scope: List[str]
    created_at: datetime
    updated_at: datetime
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class OAuth2ServiceClient:
    """OAuth2服务客户端，直接集成数据库操作"""
    
    def __init__(self):
        """初始化OAuth2服务客户端"""
        self.supabase = get_supabase_admin()
        
        # OAuth2提供商配置
        self.provider_configs = {
            "google_calendar": {
                "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_url": "https://oauth2.googleapis.com/token",
                "revoke_url": "https://oauth2.googleapis.com/revoke",
                "scopes": ["https://www.googleapis.com/auth/calendar"],
                "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
            },
            "github": {
                "auth_url": "https://github.com/login/oauth/authorize",
                "token_url": "https://github.com/login/oauth/access_token",
                "revoke_url": "https://github.com/settings/connections/applications",
                "scopes": ["repo", "user:email"],
                "client_id": os.getenv("GITHUB_CLIENT_ID", ""),
            },
            "slack": {
                "auth_url": "https://slack.com/oauth/v2/authorize",
                "token_url": "https://slack.com/api/oauth.v2.access",
                "revoke_url": "https://slack.com/api/auth.revoke",
                "scopes": ["chat:write", "channels:read"],
                "client_id": os.getenv("SLACK_CLIENT_ID", ""),
            },
        }
    
    async def generate_auth_url(
        self,
        user_id: str,
        provider: str,
        scopes: List[str],
        redirect_uri: Optional[str] = None
    ) -> AuthUrlResponse:
        """生成OAuth2授权URL"""
        try:
            if provider not in self.provider_configs:
                raise ValueError(f"Unsupported provider: {provider}")
            
            config = self.provider_configs[provider]
            state = f"{provider}_{user_id}_{secrets.token_urlsafe(16)}"
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
            
            # 存储授权状态到数据库
            await self._store_authorization_state(
                user_id=user_id,
                provider=provider,
                state_value=state,
                scopes=scopes,
                expires_at=expires_at,
                redirect_uri=redirect_uri
            )
            
            # 构建授权URL
            auth_params = {
                "client_id": config["client_id"],
                "response_type": "code",
                "state": state,
                "scope": " ".join(scopes or config["scopes"])
            }
            
            if redirect_uri:
                auth_params["redirect_uri"] = redirect_uri
            
            from urllib.parse import urlencode
            auth_url = f"{config['auth_url']}?{urlencode(auth_params)}"
            
            logger.info(f"Generated auth URL for user {user_id}, provider {provider}")
            
            return AuthUrlResponse(
                auth_url=auth_url,
                state=state,
                expires_at=expires_at,
                provider=provider,
                scopes=scopes or config["scopes"]
            )
            
        except Exception as e:
            logger.error(f"Failed to generate auth URL: {e}")
            raise
    
    async def handle_callback(
        self,
        code: str,
        state: str,
        provider: str
    ) -> TokenResponse:
        """处理OAuth2授权回调"""
        try:
            # 验证state参数
            state_data = await self._get_authorization_state(state)
            if not state_data:
                raise ValueError("Invalid or expired state parameter")
            
            user_id = state_data["user_id"]
            
            # TODO: 这里应该调用实际的OAuth2令牌交换
            # 目前返回Mock数据，实际需要HTTP请求到各Provider的token_url
            
            mock_token = TokenResponse(
                access_token=f"access_token_{provider}_{code[:8]}",
                refresh_token=f"refresh_token_{provider}_{code[:8]}",
                token_type="Bearer",
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                scope=state_data["scopes"]
            )
            
            # 存储凭证到数据库
            await self._store_credentials(
                user_id=user_id,
                provider=provider,
                token_data=mock_token,
                scope=state_data["scopes"]
            )
            
            # 清理授权状态
            await self._cleanup_authorization_state(state)
            
            logger.info(f"Successfully handled callback for user {user_id}, provider {provider}")
            return mock_token
            
        except Exception as e:
            logger.error(f"Failed to handle callback: {e}")
            raise
    
    async def get_user_credentials(self, user_id: str) -> List[CredentialData]:
        """获取用户的所有外部API凭证"""
        try:
            response = self.supabase.table('user_external_credentials').select(
                'provider', 'is_valid', 'scope', 'created_at', 'updated_at', 
                'token_expires_at', 'last_validated_at'
            ).eq('user_id', user_id).execute()
            
            credentials = []
            for row in response.data:
                credentials.append(CredentialData(
                    provider=row['provider'],
                    is_valid=row['is_valid'],
                    scope=row['scope'] or [],
                    created_at=datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')),
                    updated_at=datetime.fromisoformat(row['updated_at'].replace('Z', '+00:00')),
                    last_used_at=datetime.fromisoformat(row['last_validated_at'].replace('Z', '+00:00')) if row['last_validated_at'] else None,
                    expires_at=datetime.fromisoformat(row['token_expires_at'].replace('Z', '+00:00')) if row['token_expires_at'] else None
                ))
            
            logger.info(f"Retrieved {len(credentials)} credentials for user {user_id}")
            return credentials
            
        except Exception as e:
            logger.error(f"Failed to get user credentials: {e}")
            return []
    
    async def revoke_credential(self, user_id: str, provider: str) -> bool:
        """撤销用户的外部API凭证"""
        try:
            # TODO: 调用Provider的撤销端点
            
            # 从数据库删除凭证
            response = self.supabase.table('user_external_credentials').delete().eq(
                'user_id', user_id
            ).eq('provider', provider).execute()
            
            success = len(response.data) > 0
            if success:
                logger.info(f"Successfully revoked credential for user {user_id}, provider {provider}")
            else:
                logger.warning(f"No credential found to revoke for user {user_id}, provider {provider}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to revoke credential: {e}")
            return False
    
    async def _store_authorization_state(
        self,
        user_id: str,
        provider: str,
        state_value: str,
        scopes: List[str],
        expires_at: datetime,
        redirect_uri: Optional[str] = None
    ) -> None:
        """存储OAuth2授权状态"""
        try:
            self.supabase.table('oauth2_authorization_states').insert({
                'state_value': state_value,
                'user_id': user_id,
                'provider': provider,
                'scopes': scopes,
                'redirect_uri': redirect_uri,
                'expires_at': expires_at.isoformat(),
                'is_valid': True
            }).execute()
            
        except Exception as e:
            logger.error(f"Failed to store authorization state: {e}")
            raise
    
    async def _get_authorization_state(self, state_value: str) -> Optional[Dict[str, Any]]:
        """获取OAuth2授权状态"""
        try:
            response = self.supabase.table('oauth2_authorization_states').select(
                '*'
            ).eq('state_value', state_value).eq('is_valid', True).execute()
            
            if not response.data:
                return None
            
            state_data = response.data[0]
            
            # 检查是否过期
            expires_at = datetime.fromisoformat(state_data['expires_at'].replace('Z', '+00:00'))
            if expires_at < datetime.now(timezone.utc):
                logger.warning(f"Authorization state expired: {state_value}")
                return None
            
            return state_data
            
        except Exception as e:
            logger.error(f"Failed to get authorization state: {e}")
            return None
    
    async def _cleanup_authorization_state(self, state_value: str) -> None:
        """清理OAuth2授权状态"""
        try:
            self.supabase.table('oauth2_authorization_states').update({
                'is_valid': False,
                'used_at': datetime.now(timezone.utc).isoformat()
            }).eq('state_value', state_value).execute()
            
        except Exception as e:
            logger.error(f"Failed to cleanup authorization state: {e}")
    
    async def _store_credentials(
        self,
        user_id: str,
        provider: str,
        token_data: TokenResponse,
        scope: List[str]
    ) -> None:
        """存储用户凭证（简化版本，实际需要加密）"""
        try:
            # TODO: 实际实现需要加密存储令牌
            # 这里使用简化版本进行Mock集成
            
            # 检查是否已存在
            existing = self.supabase.table('user_external_credentials').select(
                'id'
            ).eq('user_id', user_id).eq('provider', provider).execute()
            
            credential_data = {
                'user_id': user_id,
                'provider': provider,
                'credential_type': 'oauth2',
                'encrypted_access_token': f"encrypted_{token_data.access_token}",  # Mock加密
                'encrypted_refresh_token': f"encrypted_{token_data.refresh_token}" if token_data.refresh_token else None,
                'token_expires_at': token_data.expires_at.isoformat() if token_data.expires_at else None,
                'scope': scope,
                'token_type': token_data.token_type,
                'is_valid': True,
                'last_validated_at': datetime.now(timezone.utc).isoformat()
            }
            
            if existing.data:
                # 更新现有记录
                self.supabase.table('user_external_credentials').update(
                    credential_data
                ).eq('user_id', user_id).eq('provider', provider).execute()
            else:
                # 插入新记录
                self.supabase.table('user_external_credentials').insert(
                    credential_data
                ).execute()
            
            logger.info(f"Stored credentials for user {user_id}, provider {provider}")
            
        except Exception as e:
            logger.error(f"Failed to store credentials: {e}")
            raise


# 全局实例
oauth2_client = OAuth2ServiceClient()