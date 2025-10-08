"""
User Integrations API
用户集成API，获取用户授权的外部应用和服务
需要Supabase OAuth认证
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.core.database import get_supabase_admin
from app.core.database_direct import DirectPostgreSQLManager, get_direct_db_dependency
from app.dependencies import AuthenticatedDeps
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from shared.sdks.notion_sdk.client import NotionClient
from shared.sdks.notion_sdk.exceptions import (
    NotionAPIError,
    NotionAuthError,
    NotionObjectNotFoundError,
    NotionRateLimitError,
)
from shared.sdks.notion_sdk.models import NotionDatabase, NotionPage, NotionUser, PropertyType
from shared.sdks.slack_sdk.client import SlackWebClient
from shared.sdks.slack_sdk.exceptions import SlackAPIError, SlackAuthError, SlackRateLimitError

logger = logging.getLogger(__name__)

router = APIRouter()


class IntegrationInfo(BaseModel):
    """Integration information model"""

    id: str
    integration_id: str
    provider: str
    integration_type: str
    name: str
    description: Optional[str] = None
    is_active: bool
    created_at: str
    updated_at: str
    credential_data: Optional[Dict] = None
    configuration: Optional[Dict] = None


class UserIntegrationsResponse(BaseModel):
    """User integrations response model"""

    success: bool
    user_id: str
    integrations: List[IntegrationInfo]
    total_count: int


class InstallLinksResponse(BaseModel):
    """Integration install links response model"""

    github: str
    notion: str
    slack: str
    google_calendar: str


class IntegrationMetadata(BaseModel):
    """Metadata for an available integration"""

    provider: str
    name: str
    description: str


class IntegrationWithInstallLink(BaseModel):
    """Available integration with connection status and install link"""

    provider: str
    name: str
    description: str
    install_url: str
    is_connected: bool
    connection: Optional[IntegrationInfo] = None


class IntegrationsWithStatusResponse(BaseModel):
    """Response with all available integrations and their connection status"""

    success: bool
    user_id: str
    integrations: List[IntegrationWithInstallLink]


class SlackChannelInfo(BaseModel):
    """Slack channel information returned to the frontend."""

    id: str
    name: str
    name_normalized: Optional[str] = None
    is_channel: Optional[bool] = None
    is_private: Optional[bool] = None
    is_member: Optional[bool] = None
    is_shared: Optional[bool] = None
    is_im: Optional[bool] = None
    created: Optional[int] = None
    num_members: Optional[int] = None
    topic: Optional[Dict[str, Any]] = None
    purpose: Optional[Dict[str, Any]] = None


class SlackChannelsResponse(BaseModel):
    """Slack channels list response."""

    success: bool
    channels: List[SlackChannelInfo]
    next_cursor: Optional[str] = None


class SlackUserInfo(BaseModel):
    """Slack user information for selection lists."""

    id: str
    name: Optional[str] = None
    real_name: Optional[str] = None
    team_id: Optional[str] = None
    is_bot: Optional[bool] = None
    is_app_user: Optional[bool] = None
    profile: Dict[str, Any] = {}


class SlackUsersResponse(BaseModel):
    """Slack users list response."""

    success: bool
    users: List[SlackUserInfo]
    next_cursor: Optional[str] = None


class NotionPropertySchema(BaseModel):
    """Simplified Notion property metadata for frontend configuration."""

    name: str
    type: str
    definition: Dict[str, Any]


class NotionDatabaseSchema(BaseModel):
    """Notion database schema response."""

    id: str
    title: str
    description: Optional[str] = None
    url: str
    icon: Optional[Dict[str, Any]] = None
    cover: Optional[Dict[str, Any]] = None
    properties: List[NotionPropertySchema]


class NotionDatabaseResponse(BaseModel):
    """Envelope for Notion database metadata."""

    success: bool
    database: NotionDatabaseSchema


class NotionDatabaseSummary(BaseModel):
    """Lightweight Notion database summary for list endpoints."""

    id: str
    title: str
    description: Optional[str] = None
    url: str
    icon: Optional[Dict[str, Any]] = None
    cover: Optional[Dict[str, Any]] = None
    created_time: Optional[str] = None
    last_edited_time: Optional[str] = None
    parent: Optional[Dict[str, Any]] = None


class NotionDatabasesListResponse(BaseModel):
    """Envelope for Notion database list."""

    success: bool
    databases: List[NotionDatabaseSummary]
    next_cursor: Optional[str] = None
    has_more: bool = False
    total_count: int


class NotionSearchItem(BaseModel):
    """Search result item for Notion resources."""

    id: str
    object_type: str
    title: str
    url: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[Dict[str, Any]] = None
    last_edited_time: Optional[str] = None
    parent: Optional[Dict[str, Any]] = None


class NotionSearchResponse(BaseModel):
    """Envelope for Notion search results."""

    success: bool
    results: List[NotionSearchItem]
    next_cursor: Optional[str] = None
    has_more: bool = False


class NotionUserInfo(BaseModel):
    """Notion user information for assigning people properties."""

    id: str
    name: Optional[str] = None
    type: Optional[str] = None
    avatar_url: Optional[str] = None
    email: Optional[str] = None


class NotionUsersResponse(BaseModel):
    """Envelope for Notion users list."""

    success: bool
    users: List[NotionUserInfo]
    next_cursor: Optional[str] = None
    has_more: bool = False


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _parse_slack_channel(channel_data: Dict[str, Any]) -> SlackChannelInfo:
    """Transform raw Slack channel payload into SlackChannelInfo."""

    return SlackChannelInfo(
        id=channel_data.get("id", ""),
        name=channel_data.get("name", ""),
        name_normalized=channel_data.get("name_normalized"),
        is_channel=channel_data.get("is_channel"),
        is_private=channel_data.get("is_private"),
        is_member=channel_data.get("is_member"),
        is_shared=channel_data.get("is_shared"),
        is_im=channel_data.get("is_im"),
        created=channel_data.get("created"),
        num_members=channel_data.get("num_members"),
        topic=channel_data.get("topic"),
        purpose=channel_data.get("purpose"),
    )


def _parse_slack_user(user_data: Dict[str, Any]) -> SlackUserInfo:
    """Transform raw Slack user payload into SlackUserInfo."""

    return SlackUserInfo(
        id=user_data.get("id", ""),
        name=user_data.get("name"),
        real_name=user_data.get("real_name"),
        team_id=user_data.get("team_id"),
        is_bot=user_data.get("is_bot"),
        is_app_user=user_data.get("is_app_user"),
        profile=user_data.get("profile", {}),
    )


def _rich_text_to_plain(rich_text: Optional[List[Dict[str, Any]]]) -> str:
    """Convert Notion rich text array to plain string."""

    if not rich_text:
        return ""

    parts: List[str] = []
    for block in rich_text:
        if isinstance(block, dict):
            if block.get("plain_text"):
                parts.append(block["plain_text"])
            elif block.get("text", {}).get("content"):
                parts.append(block["text"]["content"])
    return "".join(parts).strip()


def _extract_page_title(page: NotionPage) -> str:
    """Extract the title property from a Notion page."""

    for prop in page.properties.values():
        if prop.type == PropertyType.TITLE and isinstance(prop.value, str):
            title = prop.value.strip()
            if title:
                return title
    return "Untitled"


def _build_notion_database_schema(database: NotionDatabase) -> NotionDatabaseSchema:
    """Build simplified schema payload for Notion database."""

    properties: List[NotionPropertySchema] = []
    for prop_name, definition in (database.properties or {}).items():
        properties.append(
            NotionPropertySchema(
                name=prop_name,
                type=definition.get("type", "unknown"),
                definition=definition,
            )
        )

    return NotionDatabaseSchema(
        id=database.id,
        title=_rich_text_to_plain(database.title) or "Unnamed database",
        description=_rich_text_to_plain(database.description),
        url=database.url,
        icon=database.icon,
        cover=database.cover,
        properties=properties,
    )


def _build_notion_database_summary(database: NotionDatabase) -> NotionDatabaseSummary:
    """Convert NotionDatabase into lightweight summary payload."""

    return NotionDatabaseSummary(
        id=database.id,
        title=_rich_text_to_plain(database.title) or "Unnamed database",
        description=_rich_text_to_plain(database.description),
        url=database.url,
        icon=database.icon,
        cover=database.cover,
        created_time=database.created_time.isoformat() if database.created_time else None,
        last_edited_time=database.last_edited_time.isoformat()
        if database.last_edited_time
        else None,
        parent=database.parent,
    )


def _parse_notion_user(user: NotionUser) -> NotionUserInfo:
    """Convert NotionUser dataclass into API-friendly payload."""

    email = None
    if getattr(user, "person_email", None):
        email = user.person_email

    return NotionUserInfo(
        id=user.id,
        name=user.name,
        type=user.type,
        avatar_url=user.avatar_url,
        email=email,
    )


async def _get_provider_token_or_412(
    user_id: str,
    provider: str,
    direct_db: DirectPostgreSQLManager,
) -> Dict[str, Any]:
    """Fetch provider token or raise 412 if integration not connected."""

    token_record = await direct_db.get_oauth_token_fast(user_id, provider)
    if not token_record or not token_record.get("access_token"):
        logger.warning(
            "🔐 Missing %s token for user %s when attempting to fetch configuration",
            provider,
            user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail=f"{provider.title()} integration not connected",
        )

    return token_record


def get_available_integrations() -> List[IntegrationMetadata]:
    """Return metadata for all available integrations."""
    return [
        IntegrationMetadata(
            provider="github",
            name="GitHub",
            description="Connect GitHub for repository management and workflow automation",
        ),
        IntegrationMetadata(
            provider="notion",
            name="Notion",
            description="Connect Notion for workspace and database integration",
        ),
        IntegrationMetadata(
            provider="slack",
            name="Slack",
            description="Connect Slack for team communication and workflow automation",
        ),
        IntegrationMetadata(
            provider="google_calendar",
            name="Google Calendar",
            description="Connect Google Calendar for event management and scheduling",
        ),
    ]


def generate_install_url(provider: str, user_id: str) -> str:
    """Generate OAuth install URL for a specific provider."""
    from app.core.config import get_settings

    settings = get_settings()

    if provider == "github":
        return f"https://github.com/apps/starmates/installations/new?state={user_id}"

    elif provider == "notion":
        return (
            f"https://api.notion.com/v1/oauth/authorize"
            f"?client_id={settings.NOTION_CLIENT_ID}"
            f"&redirect_uri={settings.NOTION_REDIRECT_URI}"
            f"&response_type=code"
            f"&state={user_id}"
        )

    elif provider == "slack":
        return (
            f"https://slack.com/oauth/v2/authorize"
            f"?client_id={settings.SLACK_CLIENT_ID}"
            f"&scope=app_mentions:read,assistant:write,calls:read,calls:write,chat:write,channels:read,groups:read,conversations:read,reminders:read,reminders:write,im:read,chat:write.public"
            f"&user_scope=email,identity.basic"
            f"&redirect_uri={settings.SLACK_REDIRECT_URI}"
            f"&response_type=code"
            f"&state={user_id}"
        )

    elif provider == "google_calendar":
        return (
            f"https://accounts.google.com/o/oauth2/auth"
            f"?client_id={settings.GOOGLE_CLIENT_ID}"
            f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
            f"&response_type=code"
            f"&scope=https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/calendar.events"
            f"&access_type=offline"
            f"&prompt=consent"
            f"&state={user_id}"
        )

    else:
        raise ValueError(f"Unsupported provider: {provider}")


@router.get(
    "/integrations",
    response_model=IntegrationsWithStatusResponse,
    summary="Get All Integrations with Status",
    description="""
    Retrieve all available integrations with connection status and install links.

    This endpoint returns:
    - All available integrations (GitHub, Notion, Slack, Google Calendar)
    - Connection status for each integration (connected/not connected)
    - OAuth install URLs for connecting integrations
    - Full integration details if already connected

    Requires authentication via Supabase JWT token.
    """,
)
async def get_user_integrations(deps: AuthenticatedDeps = Depends()):
    """
    Get all available integrations with connection status and install links.

    Returns:
        IntegrationsWithStatusResponse with all integrations and their status
    """
    try:
        user_id = deps.user_data["id"]
        logger.info(f"🔍 Retrieving integrations with status for user {user_id}")

        supabase_admin = get_supabase_admin()

        if not supabase_admin:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database connection unavailable",
            )

        # Get user's connected integrations
        try:
            result = (
                supabase_admin.table("oauth_tokens")
                .select(
                    """
                id,
                integration_id,
                provider,
                is_active,
                created_at,
                updated_at,
                credential_data,
                integrations!oauth_tokens_integration_id_fkey (
                    integration_type,
                    name,
                    description,
                    configuration
                )
                """
                )
                .eq("user_id", user_id)
                .execute()
            )
        except Exception as e:
            logger.warning(
                f"⚠️ Failed to join with integrations table, falling back to simple query: {e}"
            )
            # Fallback to simple oauth_tokens query without join
            result = (
                supabase_admin.table("oauth_tokens")
                .select(
                    "id, integration_id, provider, is_active, created_at, updated_at, credential_data"
                )
                .eq("user_id", user_id)
                .execute()
            )

        # Build mapping of connected providers to their integration details
        connected_providers: Dict[str, IntegrationInfo] = {}
        for token_data in result.data or []:
            # Handle the joined integration data
            integration_info_data = token_data.get("integrations", {}) or {}

            provider = token_data["provider"]
            connected_providers[provider] = IntegrationInfo(
                id=token_data["id"],
                integration_id=token_data["integration_id"],
                provider=provider,
                integration_type=integration_info_data.get("integration_type", provider),
                name=integration_info_data.get("name", f"{provider.title()} Integration"),
                description=integration_info_data.get(
                    "description", f"OAuth integration for {provider}"
                ),
                is_active=token_data["is_active"],
                created_at=token_data["created_at"],
                updated_at=token_data["updated_at"],
                credential_data=token_data.get("credential_data"),
                configuration=integration_info_data.get("configuration", {}),
            )

        # Build response with all available integrations
        available_integrations = get_available_integrations()
        integrations_with_status: List[IntegrationWithInstallLink] = []

        for integration_meta in available_integrations:
            provider = integration_meta.provider
            is_connected = provider in connected_providers

            integrations_with_status.append(
                IntegrationWithInstallLink(
                    provider=integration_meta.provider,
                    name=integration_meta.name,
                    description=integration_meta.description,
                    install_url=generate_install_url(provider, user_id),
                    is_connected=is_connected,
                    connection=connected_providers.get(provider) if is_connected else None,
                )
            )

        logger.info(
            f"📋 Found {len(integrations_with_status)} available integrations "
            f"({len(connected_providers)} connected) for user {user_id}"
        )

        return IntegrationsWithStatusResponse(
            success=True, user_id=user_id, integrations=integrations_with_status
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"❌ Error retrieving user integrations: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user integrations",
        )


@router.get(
    "/integrations/slack/channels",
    response_model=SlackChannelsResponse,
    summary="List Slack channels",
    description="""
    使用用户授权的 Slack 凭证拉取工作区频道列表，并返回分页游标。
    需要先在 Integrations 页面完成 Slack 授权。
    """,
)
async def list_slack_channels(
    deps: AuthenticatedDeps = Depends(),
    direct_db: DirectPostgreSQLManager = Depends(get_direct_db_dependency),
    types: str = Query("public_channel,private_channel", description="Slack channel types"),
    limit: int = Query(100, ge=1, le=1000, description="Number of channels to fetch"),
    cursor: Optional[str] = Query(None, description="Slack pagination cursor"),
):
    """Return Slack channels using stored OAuth token."""

    user_id = deps.user_data["id"]
    logger.info("📡 Listing Slack channels for user %s", user_id)

    token_record = await _get_provider_token_or_412(user_id, "slack", direct_db)
    access_token = token_record["access_token"]

    def _fetch_channels() -> Dict[str, Any]:
        with SlackWebClient(token=access_token) as client:
            return client.list_channels_with_cursor(types=types, limit=limit, cursor=cursor)

    try:
        slack_response = await asyncio.to_thread(_fetch_channels)
    except SlackAuthError as exc:
        logger.error("❌ Slack auth error while listing channels: %s", exc)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Slack token invalid")
    except SlackRateLimitError as exc:
        logger.warning("⚠️ Slack rate limit hit while listing channels")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Slack rate limit exceeded",
            headers={"Retry-After": str(getattr(exc, "retry_after", 60))},
        )
    except SlackAPIError as exc:
        logger.error("❌ Slack API error while listing channels: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch Slack channels: {exc}",
        )

    channels = [_parse_slack_channel(channel) for channel in slack_response.get("channels", [])]

    return SlackChannelsResponse(
        success=True,
        channels=channels,
        next_cursor=slack_response.get("next_cursor"),
    )


@router.get(
    "/integrations/slack/users",
    response_model=SlackUsersResponse,
    summary="List Slack users",
    description="""
    使用用户授权的 Slack 凭证拉取工作区成员列表，用于节点选择 @user。
    支持 Slack 原生分页游标。
    """,
)
async def list_slack_users(
    deps: AuthenticatedDeps = Depends(),
    direct_db: DirectPostgreSQLManager = Depends(get_direct_db_dependency),
    limit: int = Query(100, ge=1, le=200, description="Number of users to fetch"),
    cursor: Optional[str] = Query(None, description="Slack pagination cursor"),
):
    """Return Slack users using stored OAuth token."""

    user_id = deps.user_data["id"]
    logger.info("📡 Listing Slack users for user %s", user_id)

    token_record = await _get_provider_token_or_412(user_id, "slack", direct_db)
    access_token = token_record["access_token"]

    def _fetch_users() -> Dict[str, Any]:
        with SlackWebClient(token=access_token) as client:
            return client.list_users_with_cursor(limit=limit, cursor=cursor)

    try:
        slack_response = await asyncio.to_thread(_fetch_users)
    except SlackAuthError as exc:
        logger.error("❌ Slack auth error while listing users: %s", exc)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Slack token invalid")
    except SlackRateLimitError as exc:
        logger.warning("⚠️ Slack rate limit hit while listing users")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Slack rate limit exceeded",
            headers={"Retry-After": str(getattr(exc, "retry_after", 60))},
        )
    except SlackAPIError as exc:
        logger.error("❌ Slack API error while listing users: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch Slack users: {exc}",
        )

    users = [_parse_slack_user(member) for member in slack_response.get("members", [])]

    return SlackUsersResponse(
        success=True,
        users=users,
        next_cursor=slack_response.get("next_cursor"),
    )


@router.get(
    "/integrations/notion/search",
    response_model=NotionSearchResponse,
    summary="Search Notion resources",
    description="""
    使用用户授权的 Notion 凭证搜索页面或数据库，辅助节点选择目标资源。
    支持关键字、类型过滤与分页。
    """,
)
async def search_notion_resources(
    deps: AuthenticatedDeps = Depends(),
    direct_db: DirectPostgreSQLManager = Depends(get_direct_db_dependency),
    query: Optional[str] = Query(None, description="关键字，可选"),
    filter_type: Optional[str] = Query(None, regex="^(page|database)$", description="过滤对象类型"),
    page_size: int = Query(20, ge=1, le=100, description="返回数量"),
    cursor: Optional[str] = Query(None, description="Notion start_cursor"),
):
    """Search Notion pages/databases via stored OAuth token."""

    user_id = deps.user_data["id"]
    logger.info("📡 Searching Notion resources for user %s", user_id)

    token_record = await _get_provider_token_or_412(user_id, "notion", direct_db)
    access_token = token_record["access_token"]

    filter_conditions: Optional[Dict[str, Any]] = None
    if filter_type:
        filter_conditions = {"property": "object", "value": filter_type}

    try:
        async with NotionClient(auth_token=access_token) as client:
            search_response = await client.search(
                query=query,
                filter_conditions=filter_conditions,
                start_cursor=cursor,
                page_size=page_size,
            )
    except NotionAuthError as exc:
        logger.error("❌ Notion auth error while searching resources: %s", exc)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Notion token invalid")
    except NotionRateLimitError as exc:
        logger.warning("⚠️ Notion rate limit hit while searching resources")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Notion rate limit exceeded",
            headers={"Retry-After": str(getattr(exc, "retry_after", 60))},
        )
    except NotionAPIError as exc:
        logger.error("❌ Notion API error while searching resources: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to search Notion resources: {exc}",
        )

    results: List[NotionSearchItem] = []
    for item in search_response.get("results", []):
        if isinstance(item, NotionPage):
            results.append(
                NotionSearchItem(
                    id=item.id,
                    object_type="page",
                    title=_extract_page_title(item),
                    url=item.url,
                    icon=item.icon,
                    last_edited_time=item.last_edited_time.isoformat(),
                    parent=item.parent,
                )
            )
        elif isinstance(item, NotionDatabase):
            results.append(
                NotionSearchItem(
                    id=item.id,
                    object_type="database",
                    title=_rich_text_to_plain(item.title) or "Unnamed database",
                    description=_rich_text_to_plain(item.description),
                    url=item.url,
                    icon=item.icon,
                    last_edited_time=item.last_edited_time.isoformat(),
                    parent=item.parent,
                )
            )

    return NotionSearchResponse(
        success=True,
        results=results,
        next_cursor=search_response.get("next_cursor"),
        has_more=search_response.get("has_more", False),
    )


@router.get(
    "/integrations/notion/databases",
    response_model=NotionDatabasesListResponse,
    summary="List Notion databases",
    description="""
    列出当前授权用户可访问的 Notion 数据库，支持搜索与分页。
    """,
)
async def list_notion_databases(
    deps: AuthenticatedDeps = Depends(),
    direct_db: DirectPostgreSQLManager = Depends(get_direct_db_dependency),
    query: Optional[str] = Query(None, description="关键字，可选"),
    page_size: int = Query(20, ge=1, le=100, description="返回数量"),
    cursor: Optional[str] = Query(None, description="Notion start_cursor"),
    sort_property: Optional[str] = Query(None, description="排序字段，如 last_edited_time"),
    sort_direction: Optional[str] = Query(
        None, regex="^(ascending|descending)$", description="排序方向"
    ),
):
    """Return accessible Notion databases for current user."""

    user_id = deps.user_data["id"]
    logger.info("📡 Listing Notion databases for user %s", user_id)

    token_record = await _get_provider_token_or_412(user_id, "notion", direct_db)
    access_token = token_record["access_token"]

    sort_payload: Optional[Dict[str, Any]] = None
    if sort_property and sort_direction:
        sort_payload = {"property": sort_property, "direction": sort_direction}

    try:
        async with NotionClient(auth_token=access_token) as client:
            databases_response = await client.list_databases(
                query=query,
                start_cursor=cursor,
                page_size=page_size,
                sort=sort_payload,
            )
    except NotionAuthError as exc:
        logger.error("❌ Notion auth error while listing databases: %s", exc)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Notion token invalid")
    except NotionRateLimitError as exc:
        logger.warning("⚠️ Notion rate limit hit while listing databases")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Notion rate limit exceeded",
            headers={"Retry-After": str(getattr(exc, "retry_after", 60))},
        )
    except NotionAPIError as exc:
        logger.error("❌ Notion API error while listing databases: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to list Notion databases: {exc}",
        )

    summaries = [
        _build_notion_database_summary(database)
        for database in databases_response.get("databases", [])
    ]

    return NotionDatabasesListResponse(
        success=True,
        databases=summaries,
        next_cursor=databases_response.get("next_cursor"),
        has_more=databases_response.get("has_more", False),
        total_count=databases_response.get("total_count", len(summaries)),
    )


@router.get(
    "/integrations/notion/databases/{database_id}",
    response_model=NotionDatabaseResponse,
    summary="Get Notion database schema",
    description="""
    使用用户授权的 Notion 凭证获取数据库属性结构，辅助节点配置。
    """,
)
async def get_notion_database_schema(
    database_id: str,
    deps: AuthenticatedDeps = Depends(),
    direct_db: DirectPostgreSQLManager = Depends(get_direct_db_dependency),
):
    """Fetch Notion database metadata and schema."""

    user_id = deps.user_data["id"]
    logger.info("📡 Fetching Notion database %s for user %s", database_id, user_id)

    token_record = await _get_provider_token_or_412(user_id, "notion", direct_db)
    access_token = token_record["access_token"]

    try:
        async with NotionClient(auth_token=access_token) as client:
            database = await client.get_database(database_id)
    except NotionObjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notion database not found"
        )
    except NotionAuthError as exc:
        logger.error("❌ Notion auth error while fetching database: %s", exc)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Notion token invalid")
    except NotionRateLimitError as exc:
        logger.warning("⚠️ Notion rate limit hit while fetching database")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Notion rate limit exceeded",
            headers={"Retry-After": str(getattr(exc, "retry_after", 60))},
        )
    except NotionAPIError as exc:
        logger.error("❌ Notion API error while fetching database: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch Notion database: {exc}",
        )

    schema = _build_notion_database_schema(database)
    return NotionDatabaseResponse(success=True, database=schema)


@router.get(
    "/integrations/notion/users",
    response_model=NotionUsersResponse,
    summary="List Notion users",
    description="""
    使用用户授权的 Notion 凭证拉取工作区用户列表，用于 People 属性配置。
    支持分页游标。
    """,
)
async def list_notion_users(
    deps: AuthenticatedDeps = Depends(),
    direct_db: DirectPostgreSQLManager = Depends(get_direct_db_dependency),
    page_size: int = Query(50, ge=1, le=100, description="返回数量"),
    cursor: Optional[str] = Query(None, description="Notion start_cursor"),
):
    """Return Notion users using stored OAuth token."""

    user_id = deps.user_data["id"]
    logger.info("📡 Listing Notion users for user %s", user_id)

    token_record = await _get_provider_token_or_412(user_id, "notion", direct_db)
    access_token = token_record["access_token"]

    try:
        async with NotionClient(auth_token=access_token) as client:
            users_response = await client.list_users(start_cursor=cursor, page_size=page_size)
    except NotionAuthError as exc:
        logger.error("❌ Notion auth error while listing users: %s", exc)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Notion token invalid")
    except NotionRateLimitError as exc:
        logger.warning("⚠️ Notion rate limit hit while listing users")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Notion rate limit exceeded",
            headers={"Retry-After": str(getattr(exc, "retry_after", 60))},
        )
    except NotionAPIError as exc:
        logger.error("❌ Notion API error while listing users: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch Notion users: {exc}",
        )

    users = [_parse_notion_user(user) for user in users_response.get("users", [])]

    return NotionUsersResponse(
        success=True,
        users=users,
        next_cursor=users_response.get("next_cursor"),
        has_more=users_response.get("has_more", False),
    )


@router.get(
    "/integrations/{provider}",
    summary="Get User Integrations by Provider",
    description="""
    Retrieve integrations for a specific provider (e.g., 'github', 'slack').

    Requires authentication via Supabase JWT token.
    """,
)
async def get_user_integrations_by_provider(provider: str, deps: AuthenticatedDeps = Depends()):
    """
    Get integrations for the authenticated user filtered by provider.

    Args:
        provider: The provider name (e.g., 'github', 'slack')

    Returns:
        Filtered list of user's integrations for the specified provider
    """
    try:
        user_id = deps.user_data["id"]
        logger.info(f"🔍 Retrieving {provider} integrations for user {user_id}")

        supabase_admin = get_supabase_admin()

        if not supabase_admin:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database connection unavailable",
            )

        # Query oauth_tokens filtered by provider
        result = (
            supabase_admin.table("oauth_tokens")
            .select(
                """
            id,
            integration_id,
            provider,
            is_active,
            created_at,
            updated_at,
            credential_data,
            integrations!oauth_tokens_integration_id_fkey (
                integration_type,
                name,
                description,
                configuration
            )
            """
            )
            .eq("user_id", user_id)
            .eq("provider", provider)
            .execute()
        )

        integrations = []
        for token_data in result.data or []:
            # Handle the joined integration data
            integration_info = token_data.get("integrations", {}) or {}

            integrations.append(
                IntegrationInfo(
                    id=token_data["id"],
                    integration_id=token_data["integration_id"],
                    provider=token_data["provider"],
                    integration_type=integration_info.get(
                        "integration_type", token_data["provider"]
                    ),
                    name=integration_info.get(
                        "name", f"{token_data['provider'].title()} Integration"
                    ),
                    description=integration_info.get(
                        "description", f"OAuth integration for {token_data['provider']}"
                    ),
                    is_active=token_data["is_active"],
                    created_at=token_data["created_at"],
                    updated_at=token_data["updated_at"],
                    credential_data=token_data.get("credential_data"),
                    configuration=integration_info.get("configuration", {}),
                )
            )

        logger.info(f"📋 Found {len(integrations)} {provider} integrations for user {user_id}")

        return {
            "success": True,
            "user_id": user_id,
            "provider": provider,
            "integrations": integrations,
            "total_count": len(integrations),
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"❌ Error retrieving {provider} integrations: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve {provider} integrations",
        )


@router.delete(
    "/integrations/{integration_token_id}",
    summary="Revoke User Integration",
    description="""
    Revoke/delete a specific integration for the authenticated user.

    This will mark the integration as inactive and remove access.

    Requires authentication via Supabase JWT token.
    """,
)
async def revoke_user_integration(integration_token_id: str, deps: AuthenticatedDeps = Depends()):
    """
    Revoke a specific integration for the authenticated user.

    Args:
        integration_token_id: The ID of the oauth_tokens record to revoke

    Returns:
        Success confirmation
    """
    try:
        user_id = deps.user_data["id"]
        logger.info(f"🗑️ Revoking integration {integration_token_id} for user {user_id}")

        supabase_admin = get_supabase_admin()

        if not supabase_admin:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database connection unavailable",
            )

        # First check if the integration belongs to this user
        check_result = (
            supabase_admin.table("oauth_tokens")
            .select("id, integration_id, provider")
            .eq("id", integration_token_id)
            .eq("user_id", user_id)
            .execute()
        )

        if not check_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found or doesn't belong to this user",
            )

        integration_info = check_result.data[0]

        # Mark as inactive instead of deleting (for audit purposes)
        update_result = (
            supabase_admin.table("oauth_tokens")
            .update({"is_active": False, "updated_at": "now()"})
            .eq("id", integration_token_id)
            .eq("user_id", user_id)
            .execute()
        )

        if not update_result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to revoke integration",
            )

        logger.info(
            f"✅ Integration revoked successfully - "
            f"id: {integration_token_id}, provider: {integration_info['provider']}, user: {user_id}"
        )

        return {
            "success": True,
            "message": "Integration revoked successfully",
            "integration_id": integration_token_id,
            "provider": integration_info["provider"],
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"❌ Error revoking integration: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to revoke integration"
        )
