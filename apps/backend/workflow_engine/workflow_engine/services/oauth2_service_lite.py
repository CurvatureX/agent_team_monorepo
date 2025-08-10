"""
简化的OAuth2服务实现
专门用于external action node的token交换和存储
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from dataclasses import dataclass

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from .credential_encryption import CredentialEncryption
from .user_service import UserService
from ..models.database import get_db_session

logger = logging.getLogger(__name__)


@dataclass
class TokenResponse:
    """令牌响应"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_at: Optional[datetime] = None
    scope: Optional[str] = None


class OAuth2ServiceLite:
    """简化的OAuth2服务
    
    主要用于external action node的授权码交换和凭据管理
    """
    
    def __init__(self, db_session: Session):
        """初始化OAuth2服务
        
        Args:
            db_session: 数据库会话
        """
        self.db = db_session
        self.logger = logging.getLogger(__name__)
        self.user_service = UserService(db_session)
        
        # 初始化加密服务
        encryption_key = os.getenv('CREDENTIAL_ENCRYPTION_KEY', 'MMfaVOL8LCWT8kWM9dSUVDSPVF0+A3wMGO1+kEHG85o=')
        self.encryption = CredentialEncryption(encryption_key)
        
        # OAuth2配置 - 从环境变量获取敏感信息
        self.provider_configs = {
            'google_calendar': {
                'client_id': os.getenv('GOOGLE_CLIENT_ID', ''),
                'client_secret': os.getenv('GOOGLE_CLIENT_SECRET', ''),
                'token_url': 'https://oauth2.googleapis.com/token',
                'scopes': ['https://www.googleapis.com/auth/calendar']
            },
            'github': {
                'client_id': os.getenv('GITHUB_CLIENT_ID', ''),
                'client_secret': os.getenv('GITHUB_CLIENT_SECRET', ''),
                'token_url': 'https://github.com/login/oauth/access_token',
                'scopes': ['repo', 'user']
            },
            'slack': {
                'client_id': os.getenv('SLACK_CLIENT_ID', ''),
                'client_secret': os.getenv('SLACK_CLIENT_SECRET', ''),
                'token_url': 'https://slack.com/api/oauth.v2.access',
                'scopes': ['chat:write', 'channels:read']
            },
            'api_call': {
                'client_id': os.getenv('API_CALL_CLIENT_ID', ''),
                'client_secret': os.getenv('API_CALL_CLIENT_SECRET', ''),
                'token_url': os.getenv('API_CALL_TOKEN_URL', ''),
                'scopes': os.getenv('API_CALL_SCOPES', '').split(',') if os.getenv('API_CALL_SCOPES') else []
            }
        }
        
    async def exchange_code_for_token(
        self,
        code: str,
        client_id: str,
        redirect_uri: str,
        provider: str
    ) -> TokenResponse:
        """交换授权码获取访问令牌
        
        Args:
            code: 授权码
            client_id: 客户端ID
            redirect_uri: 重定向URI
            provider: 提供商名称
            
        Returns:
            TokenResponse对象
        """
        self.logger.info(f"Exchanging authorization code for {provider}")
        
        if provider not in self.provider_configs:
            raise ValueError(f"Unsupported provider: {provider}")
        
        config = self.provider_configs[provider]
        
        # 准备token交换请求
        token_data = {
            "grant_type": "authorization_code",
            "client_id": client_id or config['client_id'],
            "client_secret": config['client_secret'],
            "code": code,
            "redirect_uri": redirect_uri
        }
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        # 发送token请求
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    config['token_url'],
                    data=token_data,
                    headers=headers,
                    timeout=30.0
                )
                
                if not response.is_success:
                    error_text = response.text
                    self.logger.error(f"Token exchange failed: {response.status_code} - {error_text}")
                    raise Exception(f"Token exchange failed: {response.status_code} - {error_text}")
                
                # 解析响应
                token_response = response.json()
                self.logger.info(f"Token exchange successful for {provider}")
                
                # 构建TokenResponse
                access_token = token_response.get('access_token')
                if not access_token:
                    raise Exception("No access token in response")
                
                refresh_token = token_response.get('refresh_token')
                token_type = token_response.get('token_type', 'Bearer')
                expires_in = token_response.get('expires_in')
                scope = token_response.get('scope', '')
                
                # Convert scope string to list for database storage
                scope_list = scope.split(' ') if scope else []
                
                # 计算过期时间
                expires_at = None
                if expires_in:
                    try:
                        expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
                    except (ValueError, TypeError):
                        self.logger.warning(f"Invalid expires_in value: {expires_in}")
                
                return TokenResponse(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    token_type=token_type,
                    expires_at=expires_at,
                    scope=scope  # Keep as string for TokenResponse object
                )
                
            except httpx.RequestError as e:
                self.logger.error(f"Network error during token exchange: {str(e)}")
                raise Exception(f"Network error: {str(e)}")
    
    async def store_user_credentials(
        self,
        user_id: str,
        provider: str,
        token_response: TokenResponse
    ) -> bool:
        """存储用户凭据
        
        Args:
            user_id: 用户ID
            provider: 提供商名称
            token_response: 令牌响应
            
        Returns:
            是否存储成功
        """
        try:
            # 首先确保用户存在
            user_email = f"oauth2_user_{user_id[:8]}@{provider}.local"
            user_name = f"OAuth2 User ({provider})"
            
            if not self.user_service.ensure_user_exists(user_id, user_email, user_name):
                self.logger.error(f"Failed to ensure user exists: {user_id}")
                return False
            
            # 加密令牌
            encrypted_access_token = self.encryption.encrypt_credential(token_response.access_token)
            encrypted_refresh_token = None
            if token_response.refresh_token:
                encrypted_refresh_token = self.encryption.encrypt_credential(token_response.refresh_token)
            
            # Convert scope string to array for database storage
            scope_array = token_response.scope.split(' ') if token_response.scope else []
            
            # 检查是否已存在记录
            check_query = text("""
                SELECT id FROM user_external_credentials 
                WHERE user_id = :user_id AND provider = :provider
            """)
            existing = self.db.execute(check_query, {
                "user_id": user_id,
                "provider": provider
            }).fetchone()
            
            if existing:
                # 更新现有记录
                update_query = text("""
                    UPDATE user_external_credentials 
                    SET encrypted_access_token = :access_token,
                        encrypted_refresh_token = :refresh_token,
                        token_expires_at = :expires_at,
                        scope = :scope,
                        token_type = :token_type,
                        is_valid = true,
                        last_validated_at = CURRENT_TIMESTAMP,
                        validation_error = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = :user_id AND provider = :provider
                """)
                self.db.execute(update_query, {
                    "user_id": user_id,
                    "provider": provider,
                    "access_token": encrypted_access_token,
                    "refresh_token": encrypted_refresh_token,
                    "expires_at": token_response.expires_at,
                    "scope": scope_array,
                    "token_type": token_response.token_type
                })
            else:
                # 插入新记录
                insert_query = text("""
                    INSERT INTO user_external_credentials (
                        user_id, provider, credential_type,
                        encrypted_access_token, encrypted_refresh_token,
                        token_expires_at, scope, token_type,
                        is_valid, last_validated_at
                    ) VALUES (
                        :user_id, :provider, 'oauth2',
                        :access_token, :refresh_token,
                        :expires_at, :scope, :token_type,
                        true, CURRENT_TIMESTAMP
                    )
                """)
                self.db.execute(insert_query, {
                    "user_id": user_id,
                    "provider": provider,
                    "access_token": encrypted_access_token,
                    "refresh_token": encrypted_refresh_token,
                    "expires_at": token_response.expires_at,
                    "scope": scope_array,
                    "token_type": token_response.token_type
                })
            
            self.db.commit()
            self.logger.info(f"Successfully stored credentials for user {user_id}, provider {provider}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store credentials for user {user_id}, provider {provider}: {e}")
            self.db.rollback()
            return False
    
    async def get_valid_token(self, user_id: str, provider: str) -> Optional[str]:
        """获取有效的访问令牌
        
        Args:
            user_id: 用户ID
            provider: 提供商名称
            
        Returns:
            有效的访问令牌，如果没有则返回None
        """
        try:
            query = text("""
                SELECT encrypted_access_token, token_expires_at, is_valid
                FROM user_external_credentials 
                WHERE user_id = :user_id AND provider = :provider
            """)
            result = self.db.execute(query, {
                "user_id": user_id,
                "provider": provider
            }).fetchone()
            
            if not result:
                self.logger.debug(f"No credentials found for user {user_id}, provider {provider}")
                return None
            
            encrypted_access_token, expires_at, is_valid = result
            
            if not is_valid:
                self.logger.debug(f"Credentials marked as invalid for user {user_id}, provider {provider}")
                return None
            
            # 检查是否过期
            if expires_at:
                now = datetime.now(timezone.utc)
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                
                if expires_at <= now:
                    self.logger.debug(f"Token expired for user {user_id}, provider {provider}")
                    return None
            
            # 解密并返回访问令牌
            access_token = self.encryption.decrypt_credential(encrypted_access_token)
            self.logger.debug(f"Retrieved valid token for user {user_id}, provider {provider}")
            return access_token
            
        except Exception as e:
            self.logger.error(f"Failed to get valid token for user {user_id}, provider {provider}: {e}")
            return None