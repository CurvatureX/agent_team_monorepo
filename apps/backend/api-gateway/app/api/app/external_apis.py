"""
External APIs Router
外部API集成路由，处理OAuth2授权、凭证管理、API调用等功能
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.dependencies import AuthenticatedDeps
from app.models.auth import AuthUser
from app.models.external_api import (
    OAuth2AuthorizeRequest,
    OAuth2AuthUrlResponse,
    OAuth2CallbackRequest,
    OAuth2TokenResponse,
    CredentialInfo,
    CredentialListResponse,
    TestAPICallRequest,
    TestAPICallResponse,
    ExternalAPIStatusResponse,
    ExternalAPIStatus,
    StatusResponse,
    ErrorResponse,
    ExternalAPIMetricsResponse,
    ExternalAPIMetrics,
    ExternalAPIProvider
)
from app.services.oauth2_service import OAuth2ServiceClient

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter()

# 创建OAuth2服务客户端实例
oauth2_service = OAuth2ServiceClient()


@router.post("/auth/authorize", response_model=OAuth2AuthUrlResponse)
async def start_oauth2_authorization(
    request: OAuth2AuthorizeRequest,
    deps: AuthenticatedDeps = Depends()
) -> OAuth2AuthUrlResponse:
    """
    启动OAuth2授权流程
    
    为指定的API提供商生成OAuth2授权URL，用户需要访问此URL完成授权
    """
    try:
        logger.info(f"🔐 Starting OAuth2 authorization for provider: {request.provider}")
        
        # 使用实际的OAuth2服务
        auth_response = await oauth2_service.generate_auth_url(
            user_id=deps.user.sub,
            provider=request.provider.value,
            scopes=request.scopes,
            redirect_uri=request.redirect_uri
        )
        
        response = OAuth2AuthUrlResponse(
            auth_url=auth_response.auth_url,
            state=auth_response.state,
            expires_at=auth_response.expires_at,
            provider=auth_response.provider
        )
        
        logger.info(f"✅ Generated authorization URL for {request.provider}")
        return response
        
    except Exception as e:
        logger.error(f"❌ Failed to start OAuth2 authorization: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start authorization: {str(e)}"
        )


@router.get("/auth/callback", response_model=OAuth2TokenResponse)
async def oauth2_callback(
    code: str = Query(description="授权码"),
    state: str = Query(description="状态参数"),
    provider: ExternalAPIProvider = Query(description="API提供商"),
    deps: AuthenticatedDeps = Depends()
) -> OAuth2TokenResponse:
    """
    处理OAuth2授权回调
    
    接收授权码并交换访问令牌，存储用户凭证
    """
    try:
        logger.info(f"🔄 Processing OAuth2 callback for provider: {provider}")
        
        # 使用实际的OAuth2服务处理回调
        token_response = await oauth2_service.handle_callback(
            code=code,
            state=state,
            provider=provider.value
        )
        
        response = OAuth2TokenResponse(
            access_token=token_response.access_token,
            refresh_token=token_response.refresh_token,
            expires_at=token_response.expires_at,
            scope=token_response.scope or [],
            provider=provider.value,
            token_type=token_response.token_type
        )
        
        logger.info(f"✅ Successfully processed OAuth2 callback for {provider}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to process OAuth2 callback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process callback: {str(e)}"
        )


@router.get("/credentials", response_model=CredentialListResponse)
async def list_user_credentials(
    deps: AuthenticatedDeps = Depends()
) -> CredentialListResponse:
    """
    获取用户的外部API凭证列表
    
    返回当前用户所有已授权的外部API凭证信息
    """
    try:
        logger.info(f"📋 Listing credentials for user: {deps.user.sub}")
        
        # 从数据库查询用户的实际凭证
        credential_data = await oauth2_service.get_user_credentials(deps.user.sub)
        
        credentials = []
        for cred in credential_data:
            credentials.append(CredentialInfo(
                provider=cred.provider,
                is_valid=cred.is_valid,
                scope=cred.scope,
                last_used_at=cred.last_used_at,
                expires_at=cred.expires_at,
                created_at=cred.created_at,
                updated_at=cred.updated_at
            ))
        
        response = CredentialListResponse(
            credentials=credentials,
            total_count=len(credentials)
        )
        
        logger.info(f"✅ Found {len(credentials)} credentials for user")
        return response
        
    except Exception as e:
        logger.error(f"❌ Failed to list credentials: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list credentials: {str(e)}"
        )


@router.delete("/credentials/{provider}", response_model=StatusResponse)
async def revoke_credential(
    provider: ExternalAPIProvider,
    deps: AuthenticatedDeps = Depends()
) -> StatusResponse:
    """
    撤销指定的外部API凭证
    
    删除用户在指定API提供商的授权凭证
    """
    try:
        logger.info(f"🗑️ Revoking credential for provider: {provider}, user: {deps.user.sub}")
        
        # 使用实际的OAuth2服务撤销凭证
        success = await oauth2_service.revoke_credential(
            user_id=deps.user.sub,
            provider=provider.value
        )
        
        if success:
            logger.info(f"✅ Successfully revoked credential for {provider}")
            return StatusResponse(
                success=True,
                message=f"Credential for {provider.value} has been revoked successfully",
                details={
                    "provider": provider.value,
                    "user_id": deps.user.sub,
                    "revoked_at": datetime.now(timezone.utc).isoformat()
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No credential found for provider {provider.value}"
            )
        
    except Exception as e:
        logger.error(f"❌ Failed to revoke credential: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke credential: {str(e)}"
        )


@router.post("/test-call", response_model=TestAPICallResponse)
async def test_api_call(
    request: TestAPICallRequest,
    deps: AuthenticatedDeps = Depends()
) -> TestAPICallResponse:
    """
    测试外部API调用
    
    使用用户的凭证测试指定的API操作，验证连接性和权限
    """
    try:
        logger.info(f"🧪 Testing API call: {request.provider}.{request.operation}")
        
        # TODO: 实际实现需要：
        # 1. 获取用户凭证
        # 2. 创建相应的API适配器
        # 3. 执行API调用
        # 4. 记录调用日志
        
        # Mock实现
        import time
        start_time = time.time()
        
        # 模拟API调用
        await asyncio.sleep(0.1)  # 模拟网络延迟
        
        execution_time = (time.time() - start_time) * 1000
        
        mock_result = {
            "test_call": True,
            "provider": request.provider.value,
            "operation": request.operation,
            "parameters": request.parameters,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mock_data": f"This is a mock response for {request.operation}"
        }
        
        response = TestAPICallResponse(
            success=True,
            provider=request.provider.value,
            operation=request.operation,
            execution_time_ms=execution_time,
            result=mock_result
        )
        
        logger.info(f"✅ API test call completed successfully in {execution_time:.2f}ms")
        return response
        
    except Exception as e:
        logger.error(f"❌ API test call failed: {str(e)}")
        
        return TestAPICallResponse(
            success=False,
            provider=request.provider.value,
            operation=request.operation,
            execution_time_ms=0.0,
            error_message=str(e),
            error_details={
                "exception_type": type(e).__name__,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )


@router.get("/status", response_model=ExternalAPIStatusResponse)
async def get_external_api_status(
    deps: AuthenticatedDeps = Depends()
) -> ExternalAPIStatusResponse:
    """
    获取外部API服务状态
    
    返回所有支持的外部API提供商的可用性状态
    """
    try:
        logger.info("📊 Checking external API status")
        
        # TODO: 实际实现需要检查各个API适配器的状态
        # 这里返回Mock状态数据
        
        current_time = datetime.now(timezone.utc).replace(microsecond=0)
        
        mock_statuses = [
            ExternalAPIStatus(
                provider="google_calendar",
                available=True,
                operations=["list_events", "create_event", "update_event", "delete_event"],
                last_check=current_time,
                response_time_ms=150.5
            ),
            ExternalAPIStatus(
                provider="github",
                available=True,
                operations=["list_repos", "create_issue", "update_issue", "list_prs"],
                last_check=current_time,
                response_time_ms=89.2
            ),
            ExternalAPIStatus(
                provider="slack",
                available=False,
                operations=["send_message", "list_channels", "upload_file"],
                last_check=current_time,
                response_time_ms=None,
                error_message="Rate limit exceeded"
            )
        ]
        
        available_count = sum(1 for status in mock_statuses if status.available)
        
        response = ExternalAPIStatusResponse(
            providers=mock_statuses,
            total_available=available_count,
            last_updated=current_time
        )
        
        logger.info(f"✅ External API status check completed: {available_count}/{len(mock_statuses)} available")
        return response
        
    except Exception as e:
        logger.error(f"❌ Failed to check external API status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check API status: {str(e)}"
        )


@router.get("/metrics", response_model=ExternalAPIMetricsResponse)
async def get_external_api_metrics(
    time_range: str = Query(default="24h", description="时间范围 (1h, 24h, 7d, 30d)"),
    deps: AuthenticatedDeps = Depends()
) -> ExternalAPIMetricsResponse:
    """
    获取外部API使用指标
    
    返回指定时间范围内的API调用统计信息
    """
    try:
        logger.info(f"📈 Getting external API metrics for range: {time_range}")
        
        # 验证时间范围参数
        valid_ranges = ["1h", "24h", "7d", "30d"]
        if time_range not in valid_ranges:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid time range. Must be one of: {valid_ranges}"
            )
        
        # TODO: 从数据库查询实际的API调用指标
        # 这里返回Mock指标数据
        
        mock_metrics = [
            ExternalAPIMetrics(
                provider="google_calendar",
                total_calls=156,
                successful_calls=148,
                failed_calls=8,
                average_response_time_ms=245.6,
                last_24h_calls=23,
                success_rate=94.9
            ),
            ExternalAPIMetrics(
                provider="github",
                total_calls=89,
                successful_calls=87,
                failed_calls=2,
                average_response_time_ms=156.3,
                last_24h_calls=12,
                success_rate=97.8
            ),
            ExternalAPIMetrics(
                provider="slack",
                total_calls=234,
                successful_calls=198,
                failed_calls=36,
                average_response_time_ms=189.4,
                last_24h_calls=8,
                success_rate=84.6
            )
        ]
        
        response = ExternalAPIMetricsResponse(
            metrics=mock_metrics,
            time_range=time_range,
            generated_at=datetime.now(timezone.utc).replace(microsecond=0)
        )
        
        logger.info(f"✅ External API metrics retrieved for {time_range}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get external API metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(e)}"
        )


# 错误处理器
@router.exception_handler(HTTPException)
async def external_api_exception_handler(request, exc: HTTPException):
    """外部API路由专用错误处理器"""
    
    logger.error(f"❌ External API error: {exc.status_code} - {exc.detail}")
    
    error_response = ErrorResponse(
        error="ExternalAPIError",
        message=exc.detail,
        details={
            "status_code": exc.status_code,
            "path": str(request.url),
            "method": request.method,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )