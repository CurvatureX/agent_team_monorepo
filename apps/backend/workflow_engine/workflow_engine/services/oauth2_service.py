"""
OAuth2授权服务
处理OAuth2授权流程、令牌管理和凭证存储
"""

import asyncio
import base64
import json
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from urllib.parse import urlencode, urlparse

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, text
from sqlalchemy.orm import Session

from .credential_encryption import CredentialEncryption, EncryptionError, DecryptionError
from .api_adapters.base import OAuth2Config, HTTPConfig, NetworkError
from ..models.database import get_db_session

logger = logging.getLogger(__name__)


# ============================================================================
# 数据模型定义
# ============================================================================

@dataclass
class AuthUrlResponse:
    """授权URL响应"""
    auth_url: str
    state: str
    expires_at: datetime
    provider: str
    scopes: List[str]


@dataclass
class TokenResponse:
    """令牌响应"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_at: Optional[datetime] = None
    scope: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "scope": self.scope or []
        }


@dataclass
class CredentialInfo:
    """凭证信息"""
    id: str
    user_id: str
    provider: str
    credential_type: str
    is_valid: bool
    scope: List[str]
    created_at: datetime
    updated_at: datetime
    last_validated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


# ============================================================================
# OAuth2异常类
# ============================================================================

class OAuth2Error(Exception):
    """OAuth2错误基类"""
    pass


class InvalidStateError(OAuth2Error):
    """无效state参数错误"""
    pass


class AuthorizationCodeError(OAuth2Error):
    """授权码错误"""
    pass


class TokenExchangeError(OAuth2Error):
    """令牌交换错误"""
    pass


class TokenRefreshError(OAuth2Error):
    """令牌刷新错误"""
    pass


# ============================================================================
# OAuth2服务主类
# ============================================================================

class OAuth2Service:
    """OAuth2授权服务
    
    提供完整的OAuth2授权流程管理，包括：
    - 生成授权URL
    - 处理授权回调
    - 令牌刷新和撤销
    - 凭证存储和管理
    """
    
    def __init__(
        self,
        database_session: AsyncSession,
        redis_client: Any,  # Redis client
        encryption_service: CredentialEncryption,
        provider_configs: Dict[str, OAuth2Config],
        http_config: Optional[HTTPConfig] = None
    ):
        """初始化OAuth2服务
        
        Args:
            database_session: 数据库会话
            redis_client: Redis客户端 
            encryption_service: 加密服务
            provider_configs: OAuth2提供商配置字典
            http_config: HTTP配置
        """
        self.db = database_session
        self.redis = redis_client
        self.encryption = encryption_service
        self.provider_configs = provider_configs
        self.http_config = http_config or HTTPConfig()
        self._http_client: Optional[httpx.AsyncClient] = None
    
    async def get_http_client(self) -> httpx.AsyncClient:
        """获取HTTP客户端"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.http_config.timeout),
                limits=self.http_config.to_httpx_limits(),
                follow_redirects=self.http_config.follow_redirects,
                verify=self.http_config.verify_ssl
            )
        return self._http_client
    
    async def close_http_client(self):
        """关闭HTTP客户端"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
    
    async def generate_auth_url(
        self,
        user_id: str,
        provider: str,
        scopes: Optional[List[str]] = None,
        redirect_uri: Optional[str] = None
    ) -> AuthUrlResponse:
        """生成OAuth2授权URL
        
        Args:
            user_id: 用户ID
            provider: 提供商名称
            scopes: 授权范围列表
            redirect_uri: 重定向URI
            
        Returns:
            授权URL响应对象
            
        Raises:
            OAuth2Error: 提供商不支持或配置错误时抛出
        """
        if provider not in self.provider_configs:
            raise OAuth2Error(f"Unsupported OAuth2 provider: {provider}")
        
        config = self.provider_configs[provider]
        
        # 使用提供的scopes或默认scopes
        request_scopes = scopes or config.scopes
        redirect_uri = redirect_uri or config.redirect_uri
        
        if not redirect_uri:
            raise OAuth2Error(f"No redirect URI configured for provider: {provider}")
        
        # 生成安全的state参数
        state = self._generate_secure_state()
        
        # 存储state到Redis (30分钟过期)
        state_data = {
            "user_id": user_id,
            "provider": provider,
            "scopes": request_scopes,
            "redirect_uri": redirect_uri,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        state_key = f"oauth2_state:{state}"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        
        try:
            await self.redis.setex(
                state_key,
                int(timedelta(minutes=30).total_seconds()),
                json.dumps(state_data)
            )
        except Exception as e:
            logger.error(f"Failed to store OAuth2 state in Redis: {str(e)}")
            raise OAuth2Error(f"Failed to store authorization state: {str(e)}")
        
        # 构建授权URL
        auth_params = {
            "client_id": config.client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": " ".join(request_scopes),
            "state": state,
            "access_type": "offline",  # 请求refresh token
            "prompt": "consent"  # 强制显示同意页面
        }
        
        auth_url = f"{config.auth_url}?{urlencode(auth_params)}"
        
        logger.info(f"Generated OAuth2 auth URL for user {user_id}, provider {provider}")
        
        return AuthUrlResponse(
            auth_url=auth_url,
            state=state,
            expires_at=expires_at,
            provider=provider,
            scopes=request_scopes
        )
    
    async def handle_callback(
        self,
        code: str,
        state: str,
        provider: str,
        error: Optional[str] = None
    ) -> TokenResponse:
        """处理OAuth2授权回调
        
        Args:
            code: 授权码
            state: state参数
            provider: 提供商名称
            error: 错误信息 (如果有)
            
        Returns:
            令牌响应对象
            
        Raises:
            OAuth2Error: 授权失败时抛出相应错误
        """
        # 检查是否有错误
        if error:
            raise AuthorizationCodeError(f"Authorization failed: {error}")
        
        if not code:
            raise AuthorizationCodeError("No authorization code received")
        
        # 验证state参数
        state_data = await self._validate_and_consume_state(state, provider)
        user_id = state_data["user_id"]
        redirect_uri = state_data["redirect_uri"]
        
        # 获取provider配置
        if provider not in self.provider_configs:
            raise OAuth2Error(f"Unsupported OAuth2 provider: {provider}")
        
        config = self.provider_configs[provider]
        
        # 交换授权码获取访问令牌
        token_response = await self._exchange_code_for_token(
            config, code, redirect_uri
        )
        
        # 解析令牌响应
        token_data = await self._parse_token_response(token_response, provider)
        
        # 存储凭证到数据库
        await self._store_credentials(
            user_id=user_id,
            provider=provider,
            token_data=token_data,
            scope=state_data.get("scopes", [])
        )
        
        logger.info(f"Successfully handled OAuth2 callback for user {user_id}, provider {provider}")
        
        return token_data
    
    async def refresh_token(
        self,
        user_id: str,
        provider: str
    ) -> TokenResponse:
        """刷新访问令牌
        
        Args:
            user_id: 用户ID
            provider: 提供商名称
            
        Returns:
            新的令牌响应
            
        Raises:
            TokenRefreshError: 刷新失败时抛出
        """
        # 获取现有凭证
        credentials = await self._get_user_credentials(user_id, provider)
        if not credentials:
            raise TokenRefreshError(f"No credentials found for user {user_id}, provider {provider}")
        
        # 解密refresh token
        try:
            encrypted_refresh_token = credentials.get("encrypted_refresh_token")
            if not encrypted_refresh_token:
                raise TokenRefreshError("No refresh token available")
            
            refresh_token = self.encryption.decrypt_credential(encrypted_refresh_token)
        except DecryptionError as e:
            logger.error(f"Failed to decrypt refresh token: {str(e)}")
            raise TokenRefreshError(f"Failed to decrypt refresh token: {str(e)}")
        
        # 获取provider配置
        if provider not in self.provider_configs:
            raise OAuth2Error(f"Unsupported OAuth2 provider: {provider}")
        
        config = self.provider_configs[provider]
        
        # 发送refresh token请求
        refresh_response = await self._refresh_access_token(config, refresh_token)
        
        # 解析响应
        token_data = await self._parse_token_response(refresh_response, provider)
        
        # 如果没有返回新的refresh token，使用原来的
        if not token_data.refresh_token:
            token_data.refresh_token = refresh_token
        
        # 更新数据库中的凭证
        await self._update_credentials(
            user_id=user_id,
            provider=provider,
            token_data=token_data,
            scope=credentials.get("scope", [])
        )
        
        logger.info(f"Successfully refreshed token for user {user_id}, provider {provider}")
        
        return token_data
    
    async def get_valid_token(
        self,
        user_id: str,
        provider: str
    ) -> str:
        """获取有效的访问令牌
        
        如果令牌已过期，自动刷新后返回新令牌。
        
        Args:
            user_id: 用户ID
            provider: 提供商名称
            
        Returns:
            有效的访问令牌
            
        Raises:
            OAuth2Error: 无法获取有效令牌时抛出
        """
        # 获取现有凭证
        credentials = await self._get_user_credentials(user_id, provider)
        if not credentials:
            raise OAuth2Error(f"No credentials found for user {user_id}, provider {provider}")
        
        # 检查凭证是否有效
        if not credentials.get("is_valid", False):
            raise OAuth2Error(f"Credentials are marked as invalid for user {user_id}, provider {provider}")
        
        # 检查令牌是否过期
        expires_at = credentials.get("token_expires_at")
        if expires_at and datetime.now(timezone.utc) >= expires_at:
            # 令牌已过期，尝试刷新
            logger.info(f"Token expired for user {user_id}, provider {provider}, attempting refresh")
            try:
                token_response = await self.refresh_token(user_id, provider)
                return token_response.access_token
            except TokenRefreshError:
                # 刷新失败，标记凭证为无效
                await self._mark_credentials_invalid(user_id, provider)
                raise OAuth2Error(f"Token refresh failed for user {user_id}, provider {provider}")
        
        # 解密并返回访问令牌
        try:
            encrypted_access_token = credentials["encrypted_access_token"]
            return self.encryption.decrypt_credential(encrypted_access_token)
        except (KeyError, DecryptionError) as e:
            logger.error(f"Failed to decrypt access token: {str(e)}")
            raise OAuth2Error(f"Failed to decrypt access token: {str(e)}")
    
    async def revoke_token(
        self,
        user_id: str,
        provider: str
    ) -> bool:
        """撤销访问令牌
        
        Args:
            user_id: 用户ID
            provider: 提供商名称
            
        Returns:
            是否成功撤销
        """
        try:
            # 获取现有凭证
            credentials = await self._get_user_credentials(user_id, provider)
            if not credentials:
                logger.warning(f"No credentials found for user {user_id}, provider {provider}")
                return True  # 没有凭证可撤销，认为成功
            
            # 获取访问令牌
            encrypted_access_token = credentials.get("encrypted_access_token")
            if encrypted_access_token:
                access_token = self.encryption.decrypt_credential(encrypted_access_token)
                
                # 获取provider配置
                if provider in self.provider_configs:
                    config = self.provider_configs[provider]
                    if config.revoke_url:
                        # 发送撤销请求
                        await self._revoke_token_request(config, access_token)
            
            # 从数据库删除凭证
            await self._delete_credentials(user_id, provider)
            
            logger.info(f"Successfully revoked token for user {user_id}, provider {provider}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke token for user {user_id}, provider {provider}: {str(e)}")
            return False
    
    async def list_user_credentials(
        self,
        user_id: str
    ) -> List[CredentialInfo]:
        """列出用户的所有外部API凭证
        
        Args:
            user_id: 用户ID
            
        Returns:
            凭证信息列表
        """
        # 这里需要实际的数据库查询实现
        # 由于我们还没有数据库模型，先返回空列表
        logger.info(f"Listing credentials for user {user_id}")
        return []
    
    async def test_credentials(
        self,
        user_id: str,
        provider: str
    ) -> Dict[str, Any]:
        """测试凭证有效性
        
        Args:
            user_id: 用户ID
            provider: 提供商名称
            
        Returns:
            测试结果字典
        """
        try:
            # 尝试获取有效令牌
            access_token = await self.get_valid_token(user_id, provider)
            
            return {
                "success": True,
                "provider": provider,
                "user_id": user_id,
                "message": "Credentials are valid",
                "has_token": bool(access_token)
            }
        except Exception as e:
            return {
                "success": False,
                "provider": provider,
                "user_id": user_id,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    # ========================================================================
    # 私有辅助方法
    # ========================================================================
    
    def _generate_secure_state(self) -> str:
        """生成安全的state参数"""
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip('=')
    
    async def _validate_and_consume_state(
        self,
        state: str,
        provider: str
    ) -> Dict[str, Any]:
        """验证并消费state参数"""
        state_key = f"oauth2_state:{state}"
        
        try:
            state_data_json = await self.redis.get(state_key)
            if not state_data_json:
                raise InvalidStateError("Invalid or expired state parameter")
            
            state_data = json.loads(state_data_json)
            
            # 验证provider匹配
            if state_data.get("provider") != provider:
                raise InvalidStateError("State provider mismatch")
            
            # 删除state (一次性使用)
            await self.redis.delete(state_key)
            
            return state_data
            
        except json.JSONDecodeError:
            raise InvalidStateError("Corrupted state data")
        except Exception as e:
            logger.error(f"Failed to validate state: {str(e)}")
            raise InvalidStateError(f"State validation failed: {str(e)}")
    
    async def _exchange_code_for_token(
        self,
        config: OAuth2Config,
        code: str,
        redirect_uri: str
    ) -> httpx.Response:
        """交换授权码获取访问令牌"""
        client = await self.get_http_client()
        
        token_data = {
            "grant_type": "authorization_code",
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "code": code,
            "redirect_uri": redirect_uri
        }
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        try:
            response = await client.post(
                config.token_url,
                data=token_data,
                headers=headers
            )
            
            if not response.is_success:
                error_text = response.text
                logger.error(f"Token exchange failed: {response.status_code} - {error_text}")
                raise TokenExchangeError(f"Token exchange failed: {response.status_code}")
            
            return response
            
        except httpx.RequestError as e:
            logger.error(f"Network error during token exchange: {str(e)}")
            raise TokenExchangeError(f"Network error: {str(e)}")
    
    async def _refresh_access_token(
        self,
        config: OAuth2Config,
        refresh_token: str
    ) -> httpx.Response:
        """刷新访问令牌"""
        client = await self.get_http_client()
        
        refresh_data = {
            "grant_type": "refresh_token",
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "refresh_token": refresh_token
        }
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        try:
            response = await client.post(
                config.token_url,
                data=refresh_data,
                headers=headers
            )
            
            if not response.is_success:
                error_text = response.text
                logger.error(f"Token refresh failed: {response.status_code} - {error_text}")
                raise TokenRefreshError(f"Token refresh failed: {response.status_code}")
            
            return response
            
        except httpx.RequestError as e:
            logger.error(f"Network error during token refresh: {str(e)}")
            raise TokenRefreshError(f"Network error: {str(e)}")
    
    async def _revoke_token_request(
        self,
        config: OAuth2Config,
        access_token: str
    ) -> None:
        """发送令牌撤销请求"""
        if not config.revoke_url:
            return
        
        client = await self.get_http_client()
        
        revoke_data = {
            "token": access_token,
            "client_id": config.client_id,
            "client_secret": config.client_secret
        }
        
        try:
            response = await client.post(
                config.revoke_url,
                data=revoke_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if not response.is_success:
                logger.warning(f"Token revocation failed: {response.status_code}")
                
        except httpx.RequestError as e:
            logger.warning(f"Network error during token revocation: {str(e)}")
    
    async def _parse_token_response(
        self,
        response: httpx.Response,
        provider: str
    ) -> TokenResponse:
        """解析令牌响应"""
        try:
            data = response.json()
        except ValueError as e:
            raise TokenExchangeError(f"Invalid JSON response: {str(e)}")
        
        # 检查错误
        if "error" in data:
            error_msg = data.get("error_description", data["error"])
            raise TokenExchangeError(f"Token error: {error_msg}")
        
        # 提取令牌信息
        access_token = data.get("access_token")
        if not access_token:
            raise TokenExchangeError("No access token in response")
        
        refresh_token = data.get("refresh_token")
        token_type = data.get("token_type", "Bearer")
        expires_in = data.get("expires_in")
        scope_str = data.get("scope", "")
        
        # 计算过期时间
        expires_at = None
        if expires_in:
            try:
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
            except (ValueError, TypeError):
                logger.warning(f"Invalid expires_in value: {expires_in}")
        
        # 解析scope
        scope = scope_str.split() if scope_str else []
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type=token_type,
            expires_at=expires_at,
            scope=scope
        )
    
    async def _store_credentials(
        self,
        user_id: str,
        provider: str,
        token_data: TokenResponse,
        scope: List[str]
    ) -> None:
        """存储凭证到数据库"""
        try:
            # 加密令牌
            encrypted_access_token = self.encryption.encrypt_credential(token_data.access_token)
            encrypted_refresh_token = None
            if token_data.refresh_token:
                encrypted_refresh_token = self.encryption.encrypt_credential(token_data.refresh_token)
            
            # 使用同步数据库会话
            with get_db_session() as db:
                # 检查是否已存在记录
                check_query = text("""
                    SELECT id FROM user_external_credentials 
                    WHERE user_id = :user_id AND provider = :provider
                """)
                existing = db.execute(check_query, {
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
                    db.execute(update_query, {
                        "user_id": user_id,
                        "provider": provider,
                        "access_token": encrypted_access_token,
                        "refresh_token": encrypted_refresh_token,
                        "expires_at": token_data.expires_at,
                        "scope": scope,
                        "token_type": token_data.token_type
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
                    db.execute(insert_query, {
                        "user_id": user_id,
                        "provider": provider,
                        "access_token": encrypted_access_token,
                        "refresh_token": encrypted_refresh_token,
                        "expires_at": token_data.expires_at,
                        "scope": scope,
                        "token_type": token_data.token_type
                    })
                
                db.commit()
                logger.info(f"Successfully stored credentials for user {user_id}, provider {provider}")
                
        except Exception as e:
            logger.error(f"Failed to store credentials for user {user_id}, provider {provider}: {e}")
            raise
    
    async def _update_credentials(
        self,
        user_id: str,
        provider: str,
        token_data: TokenResponse,
        scope: List[str]
    ) -> None:
        """更新数据库中的凭证"""
        try:
            # 加密令牌
            encrypted_access_token = self.encryption.encrypt_credential(token_data.access_token)
            encrypted_refresh_token = None
            if token_data.refresh_token:
                encrypted_refresh_token = self.encryption.encrypt_credential(token_data.refresh_token)
            
            # 使用同步数据库会话
            with get_db_session() as db:
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
                result = db.execute(update_query, {
                    "user_id": user_id,
                    "provider": provider,
                    "access_token": encrypted_access_token,
                    "refresh_token": encrypted_refresh_token,
                    "expires_at": token_data.expires_at,
                    "scope": scope,
                    "token_type": token_data.token_type
                })
                
                if result.rowcount == 0:
                    logger.warning(f"No credentials found to update for user {user_id}, provider {provider}")
                    # 如果没有找到记录，创建新的
                    await self._store_credentials(user_id, provider, token_data, scope)
                else:
                    db.commit()
                    logger.info(f"Successfully updated credentials for user {user_id}, provider {provider}")
                    
        except Exception as e:
            logger.error(f"Failed to update credentials for user {user_id}, provider {provider}: {e}")
            raise
    
    async def _get_user_credentials(
        self,
        user_id: str,
        provider: str
    ) -> Optional[Dict[str, Any]]:
        """从数据库获取用户凭证"""
        try:
            # 使用同步数据库会话
            with get_db_session() as db:
                query = text("""
                    SELECT encrypted_access_token, encrypted_refresh_token,
                           token_expires_at, scope, token_type, is_valid,
                           last_validated_at, validation_error
                    FROM user_external_credentials 
                    WHERE user_id = :user_id AND provider = :provider
                """)
                result = db.execute(query, {
                    "user_id": user_id,
                    "provider": provider
                }).fetchone()
                
                if not result:
                    logger.debug(f"No credentials found for user {user_id}, provider {provider}")
                    return None
                
                # 解密令牌
                access_token = None
                refresh_token = None
                
                if result[0]:  # encrypted_access_token
                    try:
                        access_token = self.encryption.decrypt_credential(result[0])
                    except DecryptionError as e:
                        logger.error(f"Failed to decrypt access token for user {user_id}, provider {provider}: {e}")
                        # 标记凭证为无效
                        await self._mark_credentials_invalid(user_id, provider)
                        return None
                
                if result[1]:  # encrypted_refresh_token
                    try:
                        refresh_token = self.encryption.decrypt_credential(result[1])
                    except DecryptionError as e:
                        logger.warning(f"Failed to decrypt refresh token for user {user_id}, provider {provider}: {e}")
                        # 刷新令牌解密失败，但访问令牌可能还有效
                
                credentials = {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_expires_at": result[2],  # token_expires_at
                    "scope": result[3] or [],  # scope
                    "token_type": result[4] or "Bearer",  # token_type
                    "is_valid": result[5],  # is_valid
                    "last_validated_at": result[6],  # last_validated_at
                    "validation_error": result[7]  # validation_error
                }
                
                logger.debug(f"Retrieved credentials for user {user_id}, provider {provider}")
                return credentials
                
        except Exception as e:
            logger.error(f"Failed to get credentials for user {user_id}, provider {provider}: {e}")
            return None
    
    async def _delete_credentials(
        self,
        user_id: str,
        provider: str
    ) -> None:
        """从数据库删除凭证"""
        try:
            # 使用同步数据库会话
            with get_db_session() as db:
                delete_query = text("""
                    DELETE FROM user_external_credentials 
                    WHERE user_id = :user_id AND provider = :provider
                """)
                result = db.execute(delete_query, {
                    "user_id": user_id,
                    "provider": provider
                })
                
                db.commit()
                
                if result.rowcount > 0:
                    logger.info(f"Successfully deleted credentials for user {user_id}, provider {provider}")
                else:
                    logger.warning(f"No credentials found to delete for user {user_id}, provider {provider}")
                    
        except Exception as e:
            logger.error(f"Failed to delete credentials for user {user_id}, provider {provider}: {e}")
            raise
    
    async def _mark_credentials_invalid(
        self,
        user_id: str,
        provider: str,
        error_message: str = "Credential validation failed"
    ) -> None:
        """标记凭证为无效"""
        try:
            # 使用同步数据库会话
            with get_db_session() as db:
                update_query = text("""
                    UPDATE user_external_credentials 
                    SET is_valid = false,
                        validation_error = :error_message,
                        last_validated_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = :user_id AND provider = :provider
                """)
                result = db.execute(update_query, {
                    "user_id": user_id,
                    "provider": provider,
                    "error_message": error_message
                })
                
                db.commit()
                
                if result.rowcount > 0:
                    logger.info(f"Marked credentials as invalid for user {user_id}, provider {provider}: {error_message}")
                else:
                    logger.warning(f"No credentials found to mark invalid for user {user_id}, provider {provider}")
                    
        except Exception as e:
            logger.error(f"Failed to mark credentials invalid for user {user_id}, provider {provider}: {e}")
            raise
    
    async def get_valid_token(self, user_id: str, provider: str) -> Optional[str]:
        """获取有效的访问令牌，如果需要会自动刷新
        
        Args:
            user_id: 用户ID
            provider: OAuth2提供商名称
            
        Returns:
            有效的访问令牌，如果无法获取或刷新则返回None
        """
        try:
            # 获取存储的凭证
            credentials = await self._get_user_credentials(user_id, provider)
            if not credentials:
                logger.debug(f"No credentials found for user {user_id}, provider {provider}")
                return None
            
            # 检查凭证是否标记为无效
            if not credentials.get("is_valid", True):
                logger.debug(f"Credentials marked as invalid for user {user_id}, provider {provider}")
                return None
            
            access_token = credentials.get("access_token")
            refresh_token = credentials.get("refresh_token")
            expires_at = credentials.get("token_expires_at")
            
            if not access_token:
                logger.debug(f"No access token found for user {user_id}, provider {provider}")
                return None
            
            # 检查令牌是否即将过期（提前5分钟刷新）
            now = datetime.now(timezone.utc)
            if expires_at:
                if isinstance(expires_at, str):
                    # 解析ISO格式的时间戳
                    expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                
                # 如果令牌在5分钟内过期，尝试刷新
                buffer_time = timedelta(minutes=5)
                if expires_at <= now + buffer_time:
                    logger.info(f"Token for user {user_id}, provider {provider} expires soon, attempting refresh")
                    
                    if refresh_token:
                        try:
                            # 尝试刷新令牌
                            new_tokens = await self.refresh_token(user_id, provider)
                            if new_tokens:
                                return new_tokens.access_token
                            else:
                                logger.warning(f"Token refresh failed for user {user_id}, provider {provider}")
                                # 标记凭证为无效
                                await self._mark_credentials_invalid(user_id, provider, "Token refresh failed")
                                return None
                        except Exception as e:
                            logger.error(f"Exception during token refresh for user {user_id}, provider {provider}: {e}")
                            await self._mark_credentials_invalid(user_id, provider, f"Token refresh error: {str(e)}")
                            return None
                    else:
                        logger.warning(f"Token expired but no refresh token available for user {user_id}, provider {provider}")
                        await self._mark_credentials_invalid(user_id, provider, "Token expired, no refresh token")
                        return None
            
            # 令牌仍然有效
            logger.debug(f"Retrieved valid token for user {user_id}, provider {provider}")
            return access_token
            
        except Exception as e:
            logger.error(f"Failed to get valid token for user {user_id}, provider {provider}: {e}")
            return None
    
    async def refresh_token_if_needed(self, user_id: str, provider: str) -> bool:
        """检查并在需要时刷新令牌
        
        Args:
            user_id: 用户ID
            provider: OAuth2提供商名称
            
        Returns:
            True如果令牌有效或刷新成功，False如果无法获取有效令牌
        """
        token = await self.get_valid_token(user_id, provider)
        return token is not None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close_http_client()


# ============================================================================
# OAuth2服务工厂函数
# ============================================================================

def create_oauth2_service(
    database_session: AsyncSession,
    redis_client: Any,
    encryption_key: str,
    provider_configs: Dict[str, OAuth2Config],
    http_config: Optional[HTTPConfig] = None
) -> OAuth2Service:
    """创建OAuth2服务实例
    
    Args:
        database_session: 数据库会话
        redis_client: Redis客户端
        encryption_key: 加密密钥
        provider_configs: OAuth2提供商配置字典
        http_config: HTTP配置
        
    Returns:
        OAuth2Service实例
    """
    encryption_service = CredentialEncryption(encryption_key)
    
    return OAuth2Service(
        database_session=database_session,
        redis_client=redis_client,
        encryption_service=encryption_service,
        provider_configs=provider_configs,
        http_config=http_config
    )