"""
简化的OAuth2服务实现
专门用于external action node的token交换和存储
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session
from supabase import Client, create_client

from ..models.database import get_db_session
from .credential_encryption import CredentialEncryption

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

        # 初始化加密服务
        encryption_key = os.getenv(
            "CREDENTIAL_ENCRYPTION_KEY", "MMfaVOL8LCWT8kWM9dSUVDSPVF0+A3wMGO1+kEHG85o="
        )
        self.encryption = CredentialEncryption(encryption_key)

        # 初始化Supabase客户端
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_service_key = os.getenv("SUPABASE_SECRET_KEY")
        if supabase_url and supabase_service_key:
            self.supabase: Client = create_client(supabase_url, supabase_service_key)
        else:
            self.logger.warning("Supabase credentials not configured, user validation will fail")
            self.supabase = None

        # OAuth2配置 - 从环境变量获取敏感信息
        self.provider_configs = {
            "google": {
                "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
                "token_url": "https://oauth2.googleapis.com/token",
                "scopes": ["https://www.googleapis.com/auth/calendar", "https://www.googleapis.com/auth/calendar.events"],
            },
            "github": {
                "client_id": os.getenv("GITHUB_CLIENT_ID", ""),
                "client_secret": os.getenv("GITHUB_CLIENT_SECRET", ""),
                "token_url": "https://github.com/login/oauth/access_token",
                "scopes": ["repo", "user"],
            },
            "slack": {
                "client_id": os.getenv("SLACK_CLIENT_ID", ""),
                "client_secret": os.getenv("SLACK_CLIENT_SECRET", ""),
                "token_url": "https://slack.com/api/oauth.v2.access",
                "scopes": ["chat:write", "channels:read"],
            },
            "api_call": {
                "client_id": os.getenv("API_CALL_CLIENT_ID", ""),
                "client_secret": os.getenv("API_CALL_CLIENT_SECRET", ""),
                "token_url": os.getenv("API_CALL_TOKEN_URL", ""),
                "scopes": os.getenv("API_CALL_SCOPES", "").split(",")
                if os.getenv("API_CALL_SCOPES")
                else [],
            },
        }

    def check_user_exists(self, user_id: str) -> bool:
        """检查用户是否存在于auth.users表中

        Args:
            user_id: 用户ID

        Returns:
            用户是否存在
        """
        if not self.supabase:
            self.logger.error("Supabase client not initialized")
            return False

        try:
            result = self.supabase.rpc("check_user_exists", {"user_id": user_id}).execute()
            return result.data is True
        except Exception as e:
            self.logger.error(f"Error checking user existence {user_id}: {e}")
            return False

    async def exchange_code_for_token(
        self, code: str, client_id: str, redirect_uri: str, provider: str
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
            "client_id": client_id or config["client_id"],
            "client_secret": config["client_secret"],
            "code": code,
            "redirect_uri": redirect_uri,
        }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        # 发送token请求
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    config["token_url"], data=token_data, headers=headers, timeout=30.0
                )

                if not response.is_success:
                    error_text = response.text
                    self.logger.error(
                        f"Token exchange failed: {response.status_code} - {error_text}"
                    )
                    raise Exception(f"Token exchange failed: {response.status_code} - {error_text}")

                # 解析响应
                token_response = response.json()
                self.logger.info(f"Token exchange successful for {provider}")

                # 构建TokenResponse
                access_token = token_response.get("access_token")
                if not access_token:
                    raise Exception("No access token in response")

                refresh_token = token_response.get("refresh_token")
                token_type = token_response.get("token_type", "Bearer")
                expires_in = token_response.get("expires_in")
                scope = token_response.get("scope", "")

                # Convert scope string to list for database storage
                scope_list = scope.split(" ") if scope else []

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
                    scope=scope,  # Keep as string for TokenResponse object
                )

            except httpx.RequestError as e:
                self.logger.error(f"Network error during token exchange: {str(e)}")
                raise Exception(f"Network error: {str(e)}")

    async def store_user_credentials(
        self, user_id: str, provider: str, token_response: TokenResponse
    ) -> bool:
        """存储用户凭据到oauth_tokens表（兼容现有系统）

        Args:
            user_id: 用户ID
            provider: 提供商名称
            token_response: 令牌响应

        Returns:
            是否存储成功
        """
        try:
            # 首先检查用户是否存在（使用Supabase RPC函数）
            if not self.check_user_exists(user_id):
                self.logger.error(f"User does not exist in auth.users: {user_id}")
                return False

            # Map provider to integration_id for consistency
            integration_id = "google_calendar" if provider == "google" else provider

            # 检查是否已存在记录 (使用oauth_tokens表)
            check_query = text(
                """
                SELECT id FROM oauth_tokens
                WHERE user_id = :user_id 
                AND (provider = :provider OR integration_id = :integration_id)
            """
            )
            existing = self.db.execute(
                check_query, {
                    "user_id": user_id, 
                    "provider": provider,
                    "integration_id": integration_id
                }
            ).fetchone()

            if existing:
                # 更新现有记录 (oauth_tokens表存储明文)
                update_query = text(
                    """
                    UPDATE oauth_tokens
                    SET access_token = :access_token,
                        refresh_token = :refresh_token,
                        expires_at = :expires_at,
                        token_type = :token_type,
                        is_active = true,
                        credential_data = :credential_data,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = :user_id 
                    AND (provider = :provider OR integration_id = :integration_id)
                """
                )
                
                # Prepare credential_data as JSONB
                credential_data = {
                    "scope": token_response.scope,
                    "token_type": token_response.token_type,
                    "expires_in": int((token_response.expires_at - datetime.now(timezone.utc)).total_seconds()) if token_response.expires_at else None,
                    "callback_timestamp": datetime.now(timezone.utc).isoformat()
                }

                self.db.execute(
                    update_query,
                    {
                        "user_id": user_id,
                        "provider": provider,
                        "integration_id": integration_id,
                        "access_token": token_response.access_token,  # Store plaintext like Notion
                        "refresh_token": token_response.refresh_token,
                        "expires_at": token_response.expires_at,
                        "token_type": token_response.token_type,
                        "credential_data": json.dumps(credential_data),
                    },
                )
            else:
                # 插入新记录 (oauth_tokens表，与Notion等保持一致)
                insert_query = text(
                    """
                    INSERT INTO oauth_tokens (
                        user_id, integration_id, provider,
                        access_token, refresh_token,
                        expires_at, token_type,
                        is_active, credential_data
                    ) VALUES (
                        :user_id, :integration_id, :provider,
                        :access_token, :refresh_token,
                        :expires_at, :token_type,
                        true, :credential_data
                    )
                """
                )
                
                # Prepare credential_data as JSONB
                credential_data = {
                    "scope": token_response.scope,
                    "token_type": token_response.token_type,
                    "expires_in": int((token_response.expires_at - datetime.now(timezone.utc)).total_seconds()) if token_response.expires_at else None,
                    "callback_timestamp": datetime.now(timezone.utc).isoformat()
                }

                self.db.execute(
                    insert_query,
                    {
                        "user_id": user_id,
                        "integration_id": integration_id,
                        "provider": provider,
                        "access_token": token_response.access_token,  # Store plaintext like Notion
                        "refresh_token": token_response.refresh_token,
                        "expires_at": token_response.expires_at,
                        "token_type": token_response.token_type,
                        "credential_data": json.dumps(credential_data),
                    },
                )

            self.db.commit()
            self.logger.info(
                f"Successfully stored credentials for user {user_id}, provider {provider}"
            )
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to store credentials for user {user_id}, provider {provider}: {e}"
            )
            self.db.rollback()
            return False

    async def get_valid_token(self, user_id: str, provider: str) -> Optional[str]:
        """获取有效的访问令牌，如果过期则自动刷新

        Args:
            user_id: 用户ID
            provider: 提供商名称

        Returns:
            有效的访问令牌，如果没有或无法刷新则返回None
        """
        try:
            # Query oauth_tokens table (primary storage, like Notion)
            query = text(
                """
                SELECT access_token, refresh_token, expires_at, is_active
                FROM oauth_tokens
                WHERE user_id = :user_id 
                AND (provider = :provider OR integration_id = :integration_id)
                ORDER BY updated_at DESC
                LIMIT 1
            """
            )
            # Map provider to integration_id for oauth_tokens table
            integration_id = "google_calendar" if provider == "google" else provider
            result = self.db.execute(
                query, 
                {"user_id": user_id, "provider": provider, "integration_id": integration_id}
            ).fetchone()
            
            if not result:
                self.logger.debug(f"No credentials found for user {user_id}, provider {provider}")
                return None
            
            # oauth_tokens table has plaintext tokens (like Notion)
            access_token, refresh_token, expires_at, is_active = result

            if not is_active:
                self.logger.debug(
                    f"Credentials marked as invalid for user {user_id}, provider {provider}"
                )
                return None

            # 检查访问令牌是否过期
            now = datetime.now(timezone.utc)
            token_expired = False

            if expires_at:
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))

                # 提前5分钟判断过期，避免API调用时刚好过期
                buffer_time = timedelta(minutes=5)
                if expires_at <= (now + buffer_time):
                    token_expired = True
                    self.logger.info(
                        f"Access token expired or about to expire for user {user_id}, provider {provider}"
                    )

            # 如果访问令牌未过期，直接返回
            if not token_expired:
                self.logger.debug(f"Retrieved valid token for user {user_id}, provider {provider}")
                return access_token

            # 访问令牌已过期，尝试使用刷新令牌自动刷新
            if not refresh_token:
                self.logger.warning(
                    f"Access token expired but no refresh token for user {user_id}, provider {provider}"
                )
                return None

            # 尝试刷新访问令牌 (tokens in oauth_tokens are stored plaintext)
            # Note: oauth_tokens table doesn't track refresh token expiration
            new_token_response = await self._refresh_access_token(refresh_token, provider)

            if new_token_response:
                # 保存新的令牌信息
                await self.store_user_credentials(user_id, provider, new_token_response)
                self.logger.info(
                    f"Successfully refreshed token for user {user_id}, provider {provider}"
                )
                return new_token_response.access_token
            else:
                self.logger.warning(
                    f"Failed to refresh token for user {user_id}, provider {provider}"
                )
                # 标记凭据为无效，需要用户重新授权
                await self._mark_credentials_invalid(user_id, provider, "refresh_failed")
                return None

        except Exception as e:
            self.logger.error(
                f"Failed to get valid token for user {user_id}, provider {provider}: {e}"
            )
            return None

    async def _refresh_access_token(
        self, refresh_token: str, provider: str
    ) -> Optional[TokenResponse]:
        """使用刷新令牌获取新的访问令牌

        Args:
            refresh_token: 刷新令牌
            provider: 提供商名称

        Returns:
            新的TokenResponse对象，失败返回None
        """
        try:
            provider_config = self.provider_configs.get(provider)
            if not provider_config:
                self.logger.error(f"No configuration found for provider: {provider}")
                return None

            # 构建刷新令牌请求
            data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": provider_config["client_id"],
                "client_secret": provider_config["client_secret"],
            }

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            }

            # 不同提供商的特殊处理
            if provider == "slack":
                # Slack使用不同的刷新方式
                headers[
                    "Authorization"
                ] = f"Basic {self._encode_basic_auth(provider_config['client_id'], provider_config['client_secret'])}"

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    provider_config["token_url"], data=data, headers=headers, timeout=30.0
                )

                if response.status_code != 200:
                    self.logger.error(
                        f"Token refresh failed for provider {provider}: {response.status_code} - {response.text}"
                    )
                    return None

                token_response = response.json()
                access_token = token_response.get("access_token")

                if not access_token:
                    self.logger.error(
                        f"No access token in refresh response for provider {provider}"
                    )
                    return None

                # 构建新的TokenResponse
                new_refresh_token = token_response.get(
                    "refresh_token", refresh_token
                )  # 有些提供商不返回新的refresh token
                token_type = token_response.get("token_type", "Bearer")
                expires_in = token_response.get("expires_in")
                scope = token_response.get("scope", "")

                expires_at = None
                if expires_in:
                    expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))

                return TokenResponse(
                    access_token=access_token,
                    refresh_token=new_refresh_token,
                    token_type=token_type,
                    expires_at=expires_at,
                    scope=scope,
                )

        except Exception as e:
            self.logger.error(f"Exception during token refresh for provider {provider}: {e}")
            return None

    async def _mark_credentials_invalid(self, user_id: str, provider: str, reason: str):
        """标记凭据为无效

        Args:
            user_id: 用户ID
            provider: 提供商名称
            reason: 失效原因
        """
        try:
            # Map provider to integration_id
            integration_id = "google_calendar" if provider == "google" else provider
            
            update_query = text(
                """
                UPDATE oauth_tokens
                SET is_active = false,
                    credential_data = jsonb_set(
                        COALESCE(credential_data, '{}')::jsonb,
                        '{validation_error}',
                        :reason::jsonb
                    ),
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = :user_id 
                AND (provider = :provider OR integration_id = :integration_id)
            """
            )
            self.db.execute(
                update_query, {
                    "user_id": user_id, 
                    "provider": provider, 
                    "integration_id": integration_id,
                    "reason": json.dumps(reason)
                }
            )
            self.db.commit()
            self.logger.info(
                f"Marked credentials as invalid for user {user_id}, provider {provider}, reason: {reason}"
            )
        except Exception as e:
            self.logger.error(
                f"Failed to mark credentials invalid for user {user_id}, provider {provider}: {e}"
            )

    def _encode_basic_auth(self, username: str, password: str) -> str:
        """编码Basic Auth头"""
        import base64

        credentials = f"{username}:{password}"
        return base64.b64encode(credentials.encode()).decode()

    def _calculate_refresh_token_expiration(
        self, provider: str, token_response: TokenResponse
    ) -> Optional[datetime]:
        """计算refresh token的过期时间

        Args:
            provider: 提供商名称
            token_response: 令牌响应对象

        Returns:
            refresh token过期时间，如果无法确定则返回None
        """
        # 不同提供商的refresh token过期策略
        refresh_token_lifetimes = {
            "google": timedelta(days=180),  # Google refresh tokens expire in 6 months if unused
            "github": None,  # GitHub refresh tokens don't expire
            "slack": None,  # Slack refresh tokens don't expire
            "email": timedelta(days=90),  # Generic email provider - 3 months
            "api_call": timedelta(days=90),  # Generic API - 3 months
        }

        lifetime = refresh_token_lifetimes.get(provider)
        if lifetime:
            return datetime.now(timezone.utc) + lifetime

        return None  # No expiration for this provider
