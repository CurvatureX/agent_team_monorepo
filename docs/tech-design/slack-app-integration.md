# Slack App Integration Architecture

## Overview

This document outlines the technical design for a centralized Slack App that enables users to connect their Slack workspaces to our AI workflow system. The Slack App will handle OAuth authentication, event subscriptions, interactive components, and provide secure access to Slack workspace data for workflow automation.

## Architecture Components

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Slack App     │────▶│   API Gateway    │────▶│ Workflow         │────▶│ Workflow Engine  │
│   (Events API)  │     │   (Webhooks)     │     │ Scheduler        │     │   (Execution)    │
└─────────────────┘     └──────────────────┘     └──────────────────┘     └──────────────────┘
        │                        │                        │                        │
        │                        │                        │                        │
        ▼                        ▼                        ▼                        ▼
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Slack Web API │     │    Supabase      │     │ Trigger Manager  │     │   User Workflows │
│ (Bot Actions)   │     │ (Auth & State)   │     │ (Slack Triggers) │     │   (Triggered)    │
└─────────────────┘     └──────────────────┘     └──────────────────┘     └──────────────────┘
```

## 1. Slack App Registration & Setup

### Step 1: Create Slack App

**Navigate to Slack App Management:**

1. Go to `https://api.slack.com/apps`
2. Click "Create New App"
3. Choose "From scratch"

**App Configuration:**

```yaml
App Name: "AI Workflow Teams"
Description: "Connect your Slack workspace to AI-powered workflow automation"
Development Slack Workspace: "your-test-workspace"
```

**App Settings Overview:**

- **App-Level Tokens**: For Socket Mode connections (development/testing)
- **OAuth & Permissions**: For workspace installation and bot permissions
- **Event Subscriptions**: For receiving workspace events
- **Interactive Components**: For buttons, modals, and slash commands
- **Slash Commands**: For direct bot interactions

### Step 2: Configure OAuth & Permissions

**OAuth Settings:**

```yaml
Redirect URLs:
  - "https://api.aiworkflowteams.com/auth/slack/callback" # Production
  - "https://staging-api.aiworkflowteams.com/auth/slack/callback" # Staging
  - "http://localhost:8000/auth/slack/callback" # Development

Scopes - Bot Token Scopes:
  - "app_mentions:read" # Detect @mentions of the bot
  - "channels:history" # Read messages in public channels
  - "channels:read" # View basic channel information
  - "chat:write" # Send messages as bot
  - "commands" # Enable slash commands
  - "files:read" # Access files shared in workspace
  - "groups:history" # Read messages in private channels (if invited)
  - "groups:read" # View private channels bot is in
  - "im:history" # Read direct messages with bot
  - "im:read" # View direct message info
  - "im:write" # Send direct messages
  - "mpim:history" # Read group direct messages
  - "mpim:read" # View group DM info
  - "reactions:read" # View message reactions
  - "reactions:write" # Add/remove reactions
  - "team:read" # View workspace info
  - "users:read" # View user profiles
  - "users:read.email" # View user email addresses
  - "workflow.steps:execute" # Execute workflow steps

Scopes - User Token Scopes (Optional):
  - "users:read" # View user profile information
  - "users:read.email" # Access user email addresses
```

**OAuth Flow Configuration:**

- **OAuth Version**: v2 (recommended)
- **Token Rotation**: Enabled for enhanced security
- **Public Distribution**: Enabled when ready for public use

### Step 3: Event Subscriptions Configuration

**Request URL Setup:**

```yaml
Request URL: "https://api.aiworkflowteams.com/webhooks/slack/events"
```

**Subscribe to Bot Events:**

```yaml
Bot Events:
  - "app_mention" # Bot mentioned in channel
  - "message.channels" # Message posted in public channel
  - "message.groups" # Message posted in private channel
  - "message.im" # Direct message to bot
  - "message.mpim" # Group direct message
  - "reaction_added" # Reaction added to message
  - "reaction_removed" # Reaction removed from message
  - "team_join" # New user joins workspace
  - "user_change" # User profile changes
  - "channel_created" # New channel created
  - "channel_deleted" # Channel deleted
  - "channel_rename" # Channel renamed
  - "file_shared" # File shared in workspace
  - "pin_added" # Message pinned
  - "pin_removed" # Message unpinned
```

**Subscribe to Workspace Events (Optional):**

```yaml
Workspace Events:
  - "team_domain_change" # Workspace domain changed
  - "team_rename" # Workspace renamed
  - "emoji_changed" # Custom emoji added/removed
```

### Step 4: Interactive Components & Slash Commands

**Interactive Components:**

```yaml
Request URL: "https://api.aiworkflowteams.com/webhooks/slack/interactive"

Supported Components:
  - "Shortcuts (Global)" # App shortcuts from message menu
  - "Shortcuts (Messages)" # Message shortcuts
  - "Select Menus" # Dropdown selections
  - "Buttons" # Interactive buttons
  - "Modals" # Dialog boxes
```

**Slash Commands:**

```yaml
Commands:
  - Command: "/workflow"
    Request URL: "https://api.aiworkflowteams.com/webhooks/slack/commands"
    Short Description: "Manage AI workflows"
    Usage Hint: "[create|list|run|help] [workflow-name]"

  - Command: "/ai-help"
    Request URL: "https://api.aiworkflowteams.com/webhooks/slack/commands"
    Short Description: "Get AI assistance"
    Usage Hint: "[question or task description]"

  - Command: "/workflow-status"
    Request URL: "https://api.aiworkflowteams.com/webhooks/slack/commands"
    Short Description: "Check workflow execution status"
    Usage Hint: "[workflow-id]"
```

### Step 5: App Distribution Setup

**For Public Distribution:**

**Slack App Directory Listing:**

```yaml
App Name: "AI Workflow Teams"
Short Description: "Automate your work with AI-powered workflows"
Long Description: |
  AI Workflow Teams brings intelligent automation to your Slack workspace.
  Create custom workflows that respond to messages, mentions, reactions, and
  other Slack events with AI-powered actions like content generation,
  analysis, notifications, and integrations with external services.

Categories:
  - "Productivity"
  - "Developer Tools"
  - "Workflow & Project Management"

Pricing:
  - "Free" # For basic features
  - "Freemium" # With premium tiers

Support:
  - Support URL: "https://docs.aiworkflowteams.com"
  - Privacy Policy: "https://aiworkflowteams.com/privacy"
  - Terms of Service: "https://aiworkflowteams.com/terms"
```

**App Installation Flow:**

1. **User initiates installation** via Slack App Directory or direct link
2. **OAuth authorization** redirect to Slack
3. **User selects workspace** and reviews permissions
4. **Slack redirects back** with authorization code
5. **We exchange code for tokens** and store installation

**Direct Installation URL:**

```
https://slack.com/oauth/v2/authorize?client_id=YOUR_CLIENT_ID&scope=app_mentions:read,channels:history,channels:read,chat:write,commands,files:read,groups:history,groups:read,im:history,im:read,im:write,mpim:history,mpim:read,reactions:read,reactions:write,team:read,users:read,users:read.email,workflow.steps:execute&redirect_uri=https://api.aiworkflowteams.com/auth/slack/callback
```

### Database Schema

```sql
-- Slack App installations table
CREATE TABLE slack_installations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    team_id TEXT NOT NULL,              -- Slack workspace ID
    team_name TEXT NOT NULL,            -- Slack workspace name
    bot_token TEXT NOT NULL,            -- Bot User OAuth Token
    bot_user_id TEXT NOT NULL,          -- Bot user ID in workspace
    bot_access_token TEXT,              -- Bot access token (if different)
    user_token TEXT,                    -- User OAuth Token (optional)
    user_id_slack TEXT,                 -- Installing user's Slack ID
    scope TEXT NOT NULL,                -- Granted OAuth scopes
    token_type TEXT DEFAULT 'bot',      -- Token type
    is_enterprise_install BOOLEAN DEFAULT FALSE,
    enterprise_id TEXT,                 -- Enterprise Grid ID (if applicable)
    enterprise_name TEXT,               -- Enterprise Grid name
    authed_user JSONB,                  -- Authorized user info
    incoming_webhook JSONB,             -- Incoming webhook config (if applicable)
    app_id TEXT NOT NULL,               -- Slack App ID
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(team_id, user_id)
);

-- Slack workspace configurations
CREATE TABLE slack_workspace_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    installation_id UUID REFERENCES slack_installations(id),
    team_id TEXT NOT NULL,
    channel_configs JSONB DEFAULT '[]',    -- Per-channel settings
    user_configs JSONB DEFAULT '{}',       -- Per-user settings
    global_settings JSONB DEFAULT '{}',    -- Workspace-wide settings
    active_workflows JSONB DEFAULT '[]',   -- Active workflow configurations
    webhook_verification_token TEXT,       -- For webhook signature verification
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(team_id)
);

-- Slack events log (for debugging/monitoring)
CREATE TABLE slack_webhook_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id TEXT NOT NULL,
    event_id TEXT,                      -- Slack event ID (for deduplication)
    event_type TEXT NOT NULL,           -- Type of Slack event
    event_ts TEXT,                      -- Event timestamp from Slack
    user_id TEXT,                       -- Slack user ID who triggered event
    channel_id TEXT,                    -- Slack channel ID where event occurred
    payload JSONB NOT NULL,             -- Full event payload
    processed_at TIMESTAMP WITH TIME ZONE,
    processing_status TEXT DEFAULT 'pending',  -- pending, processed, failed
    error_details TEXT,                 -- Error details if processing failed
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(event_id)  -- Prevent duplicate event processing
);

-- Indexes for performance
CREATE INDEX idx_slack_installations_team_id ON slack_installations(team_id);
CREATE INDEX idx_slack_installations_user_id ON slack_installations(user_id);
CREATE INDEX idx_slack_workspace_configs_team_id ON slack_workspace_configs(team_id);
CREATE INDEX idx_slack_webhook_events_team_id ON slack_webhook_events(team_id);
CREATE INDEX idx_slack_webhook_events_event_type ON slack_webhook_events(event_type);
CREATE INDEX idx_slack_webhook_events_created_at ON slack_webhook_events(created_at);
```

## 2. Slack SDK Development

### Core SDK Architecture

```python
# apps/backend/shared/sdks/slack_sdk.py

import asyncio
import json
import time
import hmac
import hashlib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx
from fastapi import HTTPException


@dataclass
class SlackInstallation:
    """Represents a Slack workspace installation"""
    team_id: str
    team_name: str
    bot_token: str
    bot_user_id: str
    user_token: Optional[str] = None
    scope: str = ""
    enterprise_id: Optional[str] = None
    authed_user: Optional[Dict] = None


class SlackWebClient:
    """Async Slack Web API client"""

    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://slack.com/api"
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8"
            }
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def _api_call(self, method: str, **kwargs) -> Dict[str, Any]:
        """Make API call to Slack Web API"""
        url = f"{self.base_url}/{method}"

        # Handle file uploads differently
        if 'files' in kwargs:
            # For file uploads, use form data
            response = await self.client.post(url, files=kwargs.pop('files'), data=kwargs)
        else:
            # Regular JSON API calls
            response = await self.client.post(url, json=kwargs)

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Slack API error: {response.text}"
            )

        data = response.json()

        if not data.get("ok", False):
            error = data.get("error", "unknown_error")
            raise HTTPException(
                status_code=400,
                detail=f"Slack API error: {error}"
            )

        return data

    # Auth & Team Info
    async def auth_test(self) -> Dict[str, Any]:
        """Test authentication and get bot info"""
        return await self._api_call("auth.test")

    async def team_info(self, team_id: Optional[str] = None) -> Dict[str, Any]:
        """Get team/workspace information"""
        params = {}
        if team_id:
            params['team'] = team_id
        return await self._api_call("team.info", **params)

    # Users
    async def users_list(self, limit: int = 200, cursor: Optional[str] = None) -> Dict[str, Any]:
        """List users in workspace"""
        params = {"limit": limit}
        if cursor:
            params['cursor'] = cursor
        return await self._api_call("users.list", **params)

    async def users_info(self, user_id: str) -> Dict[str, Any]:
        """Get user information"""
        return await self._api_call("users.info", user=user_id)

    async def users_profile_get(self, user_id: str) -> Dict[str, Any]:
        """Get user profile"""
        return await self._api_call("users.profile.get", user=user_id)

    # Channels
    async def conversations_list(
        self,
        types: str = "public_channel,private_channel,mpim,im",
        limit: int = 200,
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """List conversations (channels, DMs, etc.)"""
        params = {
            "types": types,
            "limit": limit
        }
        if cursor:
            params['cursor'] = cursor
        return await self._api_call("conversations.list", **params)

    async def conversations_info(self, channel_id: str) -> Dict[str, Any]:
        """Get conversation information"""
        return await self._api_call("conversations.info", channel=channel_id)

    async def conversations_members(self, channel_id: str, limit: int = 200) -> Dict[str, Any]:
        """Get conversation members"""
        return await self._api_call("conversations.members", channel=channel_id, limit=limit)

    async def conversations_history(
        self,
        channel_id: str,
        limit: int = 100,
        oldest: Optional[str] = None,
        latest: Optional[str] = None,
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get conversation history"""
        params = {
            "channel": channel_id,
            "limit": limit
        }
        if oldest:
            params['oldest'] = oldest
        if latest:
            params['latest'] = latest
        if cursor:
            params['cursor'] = cursor
        return await self._api_call("conversations.history", **params)

    # Messages
    async def chat_post_message(
        self,
        channel: str,
        text: Optional[str] = None,
        blocks: Optional[List[Dict]] = None,
        attachments: Optional[List[Dict]] = None,
        thread_ts: Optional[str] = None,
        reply_broadcast: bool = False,
        unfurl_links: bool = True,
        unfurl_media: bool = True
    ) -> Dict[str, Any]:
        """Post message to channel"""
        params = {"channel": channel}

        if text:
            params['text'] = text
        if blocks:
            params['blocks'] = blocks
        if attachments:
            params['attachments'] = attachments
        if thread_ts:
            params['thread_ts'] = thread_ts
            params['reply_broadcast'] = reply_broadcast

        params.update({
            "unfurl_links": unfurl_links,
            "unfurl_media": unfurl_media
        })

        return await self._api_call("chat.postMessage", **params)

    async def chat_update(
        self,
        channel: str,
        ts: str,
        text: Optional[str] = None,
        blocks: Optional[List[Dict]] = None,
        attachments: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Update existing message"""
        params = {
            "channel": channel,
            "ts": ts
        }

        if text:
            params['text'] = text
        if blocks:
            params['blocks'] = blocks
        if attachments:
            params['attachments'] = attachments

        return await self._api_call("chat.update", **params)

    async def chat_delete(self, channel: str, ts: str) -> Dict[str, Any]:
        """Delete message"""
        return await self._api_call("chat.delete", channel=channel, ts=ts)

    async def chat_permalink(self, channel: str, message_ts: str) -> Dict[str, Any]:
        """Get permalink for message"""
        return await self._api_call("chat.getPermalink", channel=channel, message_ts=message_ts)

    # Reactions
    async def reactions_add(self, channel: str, timestamp: str, name: str) -> Dict[str, Any]:
        """Add reaction to message"""
        return await self._api_call("reactions.add", channel=channel, timestamp=timestamp, name=name)

    async def reactions_remove(self, channel: str, timestamp: str, name: str) -> Dict[str, Any]:
        """Remove reaction from message"""
        return await self._api_call("reactions.remove", channel=channel, timestamp=timestamp, name=name)

    async def reactions_get(self, channel: str, timestamp: str) -> Dict[str, Any]:
        """Get reactions for message"""
        return await self._api_call("reactions.get", channel=channel, timestamp=timestamp)

    # Files
    async def files_upload_v2(
        self,
        filename: str,
        file_content: bytes,
        channel: Optional[str] = None,
        thread_ts: Optional[str] = None,
        title: Optional[str] = None,
        initial_comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload file using Files Upload v2 API"""
        # Step 1: Get upload URL
        upload_params = {
            "filename": filename,
            "length": len(file_content)
        }

        upload_url_response = await self._api_call("files.getUploadURLExternal", **upload_params)
        upload_url = upload_url_response["upload_url"]
        file_id = upload_url_response["file_id"]

        # Step 2: Upload file to the URL
        async with httpx.AsyncClient() as upload_client:
            upload_response = await upload_client.post(
                upload_url,
                files={"file": (filename, file_content)}
            )

            if upload_response.status_code != 200:
                raise HTTPException(
                    status_code=upload_response.status_code,
                    detail=f"File upload failed: {upload_response.text}"
                )

        # Step 3: Complete the upload
        complete_params = {
            "files": [{"id": file_id, "title": title or filename}]
        }

        if channel:
            complete_params["channel_id"] = channel
        if thread_ts:
            complete_params["thread_ts"] = thread_ts
        if initial_comment:
            complete_params["initial_comment"] = initial_comment

        return await self._api_call("files.completeUploadExternal", **complete_params)

    async def files_info(self, file_id: str) -> Dict[str, Any]:
        """Get file information"""
        return await self._api_call("files.info", file=file_id)

    async def files_delete(self, file_id: str) -> Dict[str, Any]:
        """Delete file"""
        return await self._api_call("files.delete", file=file_id)

    # Views (Modals)
    async def views_open(self, trigger_id: str, view: Dict[str, Any]) -> Dict[str, Any]:
        """Open modal view"""
        return await self._api_call("views.open", trigger_id=trigger_id, view=view)

    async def views_update(self, view_id: str, view: Dict[str, Any]) -> Dict[str, Any]:
        """Update modal view"""
        return await self._api_call("views.update", view_id=view_id, view=view)

    async def views_push(self, trigger_id: str, view: Dict[str, Any]) -> Dict[str, Any]:
        """Push new view onto modal stack"""
        return await self._api_call("views.push", trigger_id=trigger_id, view=view)

    # Shortcuts & Interactive Components
    async def shortcuts_list(self) -> Dict[str, Any]:
        """List app shortcuts"""
        return await self._api_call("shortcuts.list")


class SlackEventProcessor:
    """Process Slack webhook events"""

    def __init__(self, signing_secret: str):
        self.signing_secret = signing_secret

    def verify_signature(self, timestamp: str, signature: str, body: bytes) -> bool:
        """Verify Slack request signature"""
        # Check timestamp to prevent replay attacks
        current_time = int(time.time())
        if abs(current_time - int(timestamp)) > 60 * 5:  # 5 minutes
            return False

        # Create signature
        sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
        computed_signature = 'v0=' + hmac.new(
            self.signing_secret.encode('utf-8'),
            sig_basestring.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(computed_signature, signature)

    async def process_event(self, event_data: Dict[str, Any], team_id: str) -> Dict[str, Any]:
        """Process incoming Slack event"""
        event_type = event_data.get("type")

        if event_type == "url_verification":
            # Slack app verification
            return {"challenge": event_data.get("challenge")}

        if event_type == "event_callback":
            # Regular event
            event = event_data.get("event", {})
            inner_event_type = event.get("type")

            # Route to specific event handlers
            if inner_event_type == "app_mention":
                return await self.handle_app_mention(event, team_id)
            elif inner_event_type.startswith("message"):
                return await self.handle_message(event, team_id)
            elif inner_event_type in ["reaction_added", "reaction_removed"]:
                return await self.handle_reaction(event, team_id)
            elif inner_event_type == "team_join":
                return await self.handle_team_join(event, team_id)
            elif inner_event_type in ["channel_created", "channel_deleted", "channel_rename"]:
                return await self.handle_channel_event(event, team_id)
            elif inner_event_type == "file_shared":
                return await self.handle_file_shared(event, team_id)

        return {"ok": True}

    async def handle_app_mention(self, event: Dict[str, Any], team_id: str) -> Dict[str, Any]:
        """Handle bot mention in channel"""
        # Extract event details
        channel = event.get("channel")
        user = event.get("user")
        text = event.get("text", "")
        ts = event.get("ts")

        # Find matching workflow triggers for app mentions
        # This would integrate with your workflow system
        # await self.trigger_workflows("app_mention", event, team_id)

        return {"ok": True}

    async def handle_message(self, event: Dict[str, Any], team_id: str) -> Dict[str, Any]:
        """Handle message events"""
        # Skip bot messages to prevent loops
        if event.get("bot_id") or event.get("subtype") == "bot_message":
            return {"ok": True}

        message_type = event.get("channel_type", "channel")

        # Handle direct messages, mentions, keyword triggers, etc.
        # await self.trigger_workflows("message", event, team_id)

        return {"ok": True}

    async def handle_reaction(self, event: Dict[str, Any], team_id: str) -> Dict[str, Any]:
        """Handle reaction added/removed"""
        reaction = event.get("reaction")
        item = event.get("item", {})
        user = event.get("user")

        # Trigger workflows based on specific reactions
        # await self.trigger_workflows("reaction", event, team_id)

        return {"ok": True}

    async def handle_team_join(self, event: Dict[str, Any], team_id: str) -> Dict[str, Any]:
        """Handle new user joining workspace"""
        user = event.get("user", {})

        # Trigger welcome workflows
        # await self.trigger_workflows("team_join", event, team_id)

        return {"ok": True}

    async def handle_channel_event(self, event: Dict[str, Any], team_id: str) -> Dict[str, Any]:
        """Handle channel created/deleted/renamed"""
        # await self.trigger_workflows("channel_event", event, team_id)
        return {"ok": True}

    async def handle_file_shared(self, event: Dict[str, Any], team_id: str) -> Dict[str, Any]:
        """Handle file shared in workspace"""
        file_id = event.get("file_id")

        # Trigger file processing workflows
        # await self.trigger_workflows("file_shared", event, team_id)

        return {"ok": True}


class SlackInstallationManager:
    """Manage Slack app installations"""

    def __init__(self, client_id: str, client_secret: str, signing_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.signing_secret = signing_secret

    async def handle_oauth_callback(self, code: str, state: Optional[str] = None) -> SlackInstallation:
        """Handle OAuth callback and exchange code for tokens"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://slack.com/api/oauth.v2.access",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code
                }
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"OAuth error: {response.text}"
                )

            data = response.json()

            if not data.get("ok", False):
                error = data.get("error", "oauth_error")
                raise HTTPException(
                    status_code=400,
                    detail=f"Slack OAuth error: {error}"
                )

            # Extract installation details
            team = data.get("team", {})
            authed_user = data.get("authed_user", {})
            access_token = data.get("access_token")  # User token
            bot_token = data.get("bot_user_id") and data.get("access_token")  # Bot token

            # For bot installations, the bot token is in the response root
            if data.get("token_type") == "bot":
                bot_token = data.get("access_token")

            installation = SlackInstallation(
                team_id=team.get("id"),
                team_name=team.get("name"),
                bot_token=bot_token,
                bot_user_id=data.get("bot_user_id"),
                user_token=access_token if data.get("token_type") != "bot" else None,
                scope=data.get("scope", ""),
                enterprise_id=data.get("enterprise", {}).get("id"),
                authed_user=authed_user
            )

            return installation

    async def get_installation(self, team_id: str) -> Optional[SlackInstallation]:
        """Retrieve installation from database"""
        # This would query your database
        # SELECT * FROM slack_installations WHERE team_id = team_id
        pass

    async def save_installation(self, installation: SlackInstallation, user_id: str) -> bool:
        """Save installation to database"""
        # This would save to your database
        # INSERT INTO slack_installations (user_id, team_id, ...) VALUES (...)
        pass

    async def delete_installation(self, team_id: str) -> bool:
        """Delete installation (when app is uninstalled)"""
        # This would delete from your database
        # DELETE FROM slack_installations WHERE team_id = team_id
        pass


# Utility functions for Slack Block Kit
class SlackBlockBuilder:
    """Helper class to build Slack Block Kit UI components"""

    @staticmethod
    def text_block(text: str, block_type: str = "mrkdwn") -> Dict[str, Any]:
        """Create text block"""
        return {
            "type": "section",
            "text": {
                "type": block_type,
                "text": text
            }
        }

    @staticmethod
    def button_block(text: str, action_id: str, value: str = "", style: str = "primary") -> Dict[str, Any]:
        """Create button block"""
        return {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": text
                    },
                    "action_id": action_id,
                    "value": value,
                    "style": style
                }
            ]
        }

    @staticmethod
    def select_block(placeholder: str, action_id: str, options: List[Dict[str, str]]) -> Dict[str, Any]:
        """Create select menu block"""
        return {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": placeholder
            },
            "accessory": {
                "type": "static_select",
                "action_id": action_id,
                "placeholder": {
                    "type": "plain_text",
                    "text": placeholder
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": option["text"]
                        },
                        "value": option["value"]
                    }
                    for option in options
                ]
            }
        }

    @staticmethod
    def divider_block() -> Dict[str, Any]:
        """Create divider block"""
        return {"type": "divider"}

    @staticmethod
    def modal_view(title: str, blocks: List[Dict[str, Any]], callback_id: str = "") -> Dict[str, Any]:
        """Create modal view"""
        return {
            "type": "modal",
            "callback_id": callback_id,
            "title": {
                "type": "plain_text",
                "text": title
            },
            "blocks": blocks,
            "submit": {
                "type": "plain_text",
                "text": "Submit"
            },
            "close": {
                "type": "plain_text",
                "text": "Cancel"
            }
        }
```

### SDK Integration Service

```python
# apps/backend/shared/services/slack_service.py

from typing import Dict, List, Optional, Any
from ..sdks.slack_sdk import SlackWebClient, SlackInstallation, SlackInstallationManager
from ..models.database import get_database_session


class SlackService:
    """High-level service for Slack operations"""

    def __init__(self, client_id: str, client_secret: str, signing_secret: str):
        self.installation_manager = SlackInstallationManager(
            client_id, client_secret, signing_secret
        )

    async def get_client_for_team(self, team_id: str) -> Optional[SlackWebClient]:
        """Get authenticated Slack client for team"""
        installation = await self.installation_manager.get_installation(team_id)
        if not installation or not installation.bot_token:
            return None

        return SlackWebClient(installation.bot_token)

    async def send_message(
        self,
        team_id: str,
        channel: str,
        text: Optional[str] = None,
        blocks: Optional[List[Dict]] = None
    ) -> Optional[Dict[str, Any]]:
        """Send message to Slack channel"""
        client = await self.get_client_for_team(team_id)
        if not client:
            return None

        async with client:
            return await client.chat_post_message(
                channel=channel,
                text=text,
                blocks=blocks
            )

    async def upload_file(
        self,
        team_id: str,
        filename: str,
        file_content: bytes,
        channel: Optional[str] = None,
        title: Optional[str] = None,
        comment: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Upload file to Slack"""
        client = await self.get_client_for_team(team_id)
        if not client:
            return None

        async with client:
            return await client.files_upload_v2(
                filename=filename,
                file_content=file_content,
                channel=channel,
                title=title,
                initial_comment=comment
            )

    async def get_channel_history(
        self,
        team_id: str,
        channel_id: str,
        limit: int = 100
    ) -> Optional[List[Dict[str, Any]]]:
        """Get channel message history"""
        client = await self.get_client_for_team(team_id)
        if not client:
            return None

        async with client:
            response = await client.conversations_history(
                channel_id=channel_id,
                limit=limit
            )
            return response.get("messages", [])

    async def get_user_info(self, team_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user information"""
        client = await self.get_client_for_team(team_id)
        if not client:
            return None

        async with client:
            response = await client.users_info(user_id)
            return response.get("user")

    async def add_reaction(self, team_id: str, channel: str, timestamp: str, emoji: str) -> bool:
        """Add reaction to message"""
        client = await self.get_client_for_team(team_id)
        if not client:
            return False

        try:
            async with client:
                await client.reactions_add(channel, timestamp, emoji)
                return True
        except Exception:
            return False

    async def create_workflow_summary_message(
        self,
        team_id: str,
        channel: str,
        workflow_name: str,
        status: str,
        execution_id: str,
        results: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """Create formatted workflow summary message"""
        from ..sdks.slack_sdk import SlackBlockBuilder

        status_emoji = "✅" if status == "completed" else "❌" if status == "failed" else "⏳"

        blocks = [
            SlackBlockBuilder.text_block(
                f"{status_emoji} *Workflow: {workflow_name}*\n"
                f"Status: {status.title()}\n"
                f"Execution ID: `{execution_id}`"
            )
        ]

        if results:
            # Add results summary
            if "summary" in results:
                blocks.append(SlackBlockBuilder.text_block(f"*Summary:*\n{results['summary']}"))

            if "outputs" in results and results["outputs"]:
                output_text = "\n".join([f"• {k}: {v}" for k, v in results["outputs"].items()])
                blocks.append(SlackBlockBuilder.text_block(f"*Outputs:*\n{output_text}"))

        blocks.append(SlackBlockBuilder.divider_block())

        return await self.send_message(team_id, channel, blocks=blocks)
```

## 3. Integration with Workflow System

### Enhanced Event Processing

```python
# apps/backend/api-gateway/app/webhooks/slack.py

from fastapi import APIRouter, Request, Header, HTTPException
from typing import Optional
import json
import logging

from ...services.slack_service import SlackService
from ...services.workflow_trigger_service import WorkflowTriggerService
from ..core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

slack_service = SlackService(
    client_id=settings.slack_client_id,
    client_secret=settings.slack_client_secret,
    signing_secret=settings.slack_signing_secret
)

workflow_trigger_service = WorkflowTriggerService()


@router.post("/webhooks/slack/events")
async def slack_events_webhook(
    request: Request,
    x_slack_signature: str = Header(...),
    x_slack_request_timestamp: str = Header(...),
):
    """Handle Slack Events API webhook"""
    body = await request.body()

    # Verify Slack request signature
    if not slack_service.installation_manager.event_processor.verify_signature(
        x_slack_request_timestamp, x_slack_signature, body
    ):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse event data
    try:
        event_data = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Handle URL verification challenge
    if event_data.get("type") == "url_verification":
        return {"challenge": event_data.get("challenge")}

    # Process event asynchronously
    team_id = event_data.get("team_id")
    if not team_id:
        raise HTTPException(status_code=400, detail="Missing team_id")

    # Store event for processing
    await store_slack_event(event_data, team_id)

    # Find and trigger matching workflows
    await process_slack_event_for_workflows(event_data, team_id)

    return {"ok": True}


@router.post("/webhooks/slack/interactive")
async def slack_interactive_webhook(
    request: Request,
    x_slack_signature: str = Header(...),
    x_slack_request_timestamp: str = Header(...),
):
    """Handle Slack Interactive Components webhook"""
    body = await request.body()

    # Verify signature
    if not slack_service.installation_manager.event_processor.verify_signature(
        x_slack_request_timestamp, x_slack_signature, body
    ):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse form data (interactive components send form-encoded data)
    form_data = await request.form()
    payload_str = form_data.get("payload")

    if not payload_str:
        raise HTTPException(status_code=400, detail="Missing payload")

    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in payload")

    # Process interactive component
    return await process_interactive_component(payload)


@router.post("/webhooks/slack/commands")
async def slack_slash_commands_webhook(
    request: Request,
    x_slack_signature: str = Header(...),
    x_slack_request_timestamp: str = Header(...),
):
    """Handle Slack Slash Commands webhook"""
    body = await request.body()

    # Verify signature
    if not slack_service.installation_manager.event_processor.verify_signature(
        x_slack_request_timestamp, x_slack_signature, body
    ):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse form data
    form_data = await request.form()

    command_data = {
        "token": form_data.get("token"),
        "team_id": form_data.get("team_id"),
        "team_domain": form_data.get("team_domain"),
        "channel_id": form_data.get("channel_id"),
        "channel_name": form_data.get("channel_name"),
        "user_id": form_data.get("user_id"),
        "user_name": form_data.get("user_name"),
        "command": form_data.get("command"),
        "text": form_data.get("text", ""),
        "response_url": form_data.get("response_url"),
        "trigger_id": form_data.get("trigger_id")
    }

    # Process slash command
    return await process_slash_command(command_data)


async def store_slack_event(event_data: dict, team_id: str):
    """Store Slack event in database for debugging/monitoring"""
    try:
        # This would save to your slack_webhook_events table
        pass
    except Exception as e:
        logger.error(f"Failed to store Slack event: {e}")


async def process_slack_event_for_workflows(event_data: dict, team_id: str):
    """Find and trigger workflows based on Slack event"""
    try:
        event = event_data.get("event", {})
        event_type = event.get("type")

        # Find active workflows with Slack triggers for this team
        active_triggers = await workflow_trigger_service.find_slack_triggers(
            team_id=team_id,
            event_type=event_type,
            event_data=event
        )

        # Execute matching workflows
        for trigger in active_triggers:
            await workflow_trigger_service.execute_workflow(
                trigger_id=trigger["id"],
                event_data={
                    "slack_event": event_data,
                    "team_id": team_id,
                    "event_type": event_type,
                    "timestamp": event_data.get("event_time"),
                }
            )

    except Exception as e:
        logger.error(f"Failed to process Slack event for workflows: {e}")


async def process_interactive_component(payload: dict):
    """Process Slack interactive component interaction"""
    interaction_type = payload.get("type")

    if interaction_type == "block_actions":
        # Handle button clicks, select menus, etc.
        actions = payload.get("actions", [])
        for action in actions:
            action_id = action.get("action_id")
            value = action.get("value")

            # Route to appropriate handler based on action_id
            if action_id.startswith("workflow_"):
                await handle_workflow_action(payload, action)

    elif interaction_type == "view_submission":
        # Handle modal form submissions
        view = payload.get("view", {})
        callback_id = view.get("callback_id")

        if callback_id.startswith("workflow_"):
            await handle_workflow_modal_submission(payload)

    elif interaction_type == "shortcut":
        # Handle app shortcuts
        shortcut = payload.get("shortcut", {})
        callback_id = shortcut.get("callback_id")

        if callback_id == "create_workflow":
            await handle_create_workflow_shortcut(payload)

    return {"ok": True}


async def process_slash_command(command_data: dict):
    """Process Slack slash command"""
    command = command_data.get("command")
    text = command_data.get("text", "").strip()
    team_id = command_data.get("team_id")
    user_id = command_data.get("user_id")
    channel_id = command_data.get("channel_id")

    if command == "/workflow":
        return await handle_workflow_command(command_data, text)

    elif command == "/ai-help":
        return await handle_ai_help_command(command_data, text)

    elif command == "/workflow-status":
        return await handle_workflow_status_command(command_data, text)

    return {
        "response_type": "ephemeral",
        "text": f"Unknown command: {command}"
    }


async def handle_workflow_command(command_data: dict, text: str):
    """Handle /workflow slash command"""
    from ...sdks.slack_sdk import SlackBlockBuilder

    parts = text.split() if text else []
    action = parts[0] if parts else "help"

    team_id = command_data.get("team_id")
    user_id = command_data.get("user_id")

    if action == "list":
        # List user's workflows
        workflows = await workflow_trigger_service.get_user_workflows(user_id, team_id)

        if not workflows:
            return {
                "response_type": "ephemeral",
                "text": "You don't have any workflows configured yet. Use `/workflow create` to get started!"
            }

        blocks = [SlackBlockBuilder.text_block("*Your Workflows:*")]

        for workflow in workflows[:10]:  # Limit to 10
            status_emoji = "✅" if workflow["active"] else "⏸️"
            blocks.append(
                SlackBlockBuilder.text_block(
                    f"{status_emoji} *{workflow['name']}*\n"
                    f"Trigger: {workflow['trigger_type']}\n"
                    f"Last run: {workflow.get('last_execution', 'Never')}"
                )
            )

        return {
            "response_type": "ephemeral",
            "blocks": blocks
        }

    elif action == "create":
        # Open workflow creation modal
        trigger_id = command_data.get("trigger_id")

        modal_blocks = [
            {
                "type": "input",
                "block_id": "workflow_name",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "name_input",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Enter workflow name"
                    }
                },
                "label": {
                    "type": "plain_text",
                    "text": "Workflow Name"
                }
            },
            {
                "type": "input",
                "block_id": "trigger_type",
                "element": {
                    "type": "static_select",
                    "action_id": "trigger_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select trigger type"
                    },
                    "options": [
                        {
                            "text": {"type": "plain_text", "text": "App Mention"},
                            "value": "app_mention"
                        },
                        {
                            "text": {"type": "plain_text", "text": "Message in Channel"},
                            "value": "message"
                        },
                        {
                            "text": {"type": "plain_text", "text": "Reaction Added"},
                            "value": "reaction_added"
                        },
                        {
                            "text": {"type": "plain_text", "text": "File Shared"},
                            "value": "file_shared"
                        }
                    ]
                },
                "label": {
                    "type": "plain_text",
                    "text": "Trigger Type"
                }
            }
        ]

        modal_view = SlackBlockBuilder.modal_view(
            title="Create Workflow",
            blocks=modal_blocks,
            callback_id="create_workflow_modal"
        )

        # Open modal using Slack client
        client = await slack_service.get_client_for_team(team_id)
        if client:
            async with client:
                await client.views_open(trigger_id, modal_view)

        return ""  # Empty response for modal triggers

    elif action == "help":
        help_text = """
*Workflow Commands:*
• `/workflow list` - List your workflows
• `/workflow create` - Create a new workflow
• `/workflow run <name>` - Run a workflow manually
• `/workflow status <name>` - Check workflow status
• `/workflow help` - Show this help message

*Examples:*
• `/workflow create` - Opens workflow creation dialog
• `/workflow list` - Shows all your workflows
• `/workflow run daily-report` - Runs the "daily-report" workflow
        """

        return {
            "response_type": "ephemeral",
            "text": help_text
        }

    else:
        return {
            "response_type": "ephemeral",
            "text": f"Unknown workflow action: {action}. Use `/workflow help` for available commands."
        }


async def handle_ai_help_command(command_data: dict, text: str):
    """Handle /ai-help slash command"""
    if not text:
        return {
            "response_type": "ephemeral",
            "text": "Please provide a question or task. Example: `/ai-help How do I create a workflow that sends daily reports?`"
        }

    # This would integrate with your AI service
    # ai_response = await ai_service.get_help_response(text)

    return {
        "response_type": "ephemeral",
        "text": f"*AI Assistant:*\n\n{text}\n\n_This would be processed by your AI service..._"
    }


async def handle_workflow_status_command(command_data: dict, text: str):
    """Handle /workflow-status slash command"""
    if not text:
        return {
            "response_type": "ephemeral",
            "text": "Please provide a workflow ID or name. Example: `/workflow-status my-workflow`"
        }

    team_id = command_data.get("team_id")
    user_id = command_data.get("user_id")

    # Look up workflow status
    status = await workflow_trigger_service.get_workflow_status(user_id, team_id, text)

    if not status:
        return {
            "response_type": "ephemeral",
            "text": f"Workflow '{text}' not found. Use `/workflow list` to see your workflows."
        }

    status_emoji = "✅" if status["status"] == "completed" else "❌" if status["status"] == "failed" else "⏳"

    return {
        "response_type": "ephemeral",
        "text": f"{status_emoji} *{status['name']}*\n"
                f"Status: {status['status'].title()}\n"
                f"Last execution: {status.get('last_execution', 'Never')}\n"
                f"Next scheduled: {status.get('next_scheduled', 'Not scheduled')}"
    }


async def handle_workflow_action(payload: dict, action: dict):
    """Handle workflow-related button actions"""
    action_id = action.get("action_id")
    value = action.get("value")

    if action_id == "workflow_run":
        # Run workflow button clicked
        workflow_id = value
        team_id = payload.get("team", {}).get("id")
        user_id = payload.get("user", {}).get("id")

        # Trigger workflow execution
        await workflow_trigger_service.execute_workflow_manually(
            workflow_id=workflow_id,
            user_id=user_id,
            team_id=team_id,
            trigger_source="slack_button"
        )

    elif action_id == "workflow_stop":
        # Stop workflow button clicked
        execution_id = value
        await workflow_trigger_service.stop_workflow_execution(execution_id)


async def handle_workflow_modal_submission(payload: dict):
    """Handle workflow creation modal submission"""
    view = payload.get("view", {})
    values = view.get("state", {}).get("values", {})

    # Extract form values
    workflow_name = values.get("workflow_name", {}).get("name_input", {}).get("value", "")
    trigger_type = values.get("trigger_type", {}).get("trigger_select", {}).get("selected_option", {}).get("value", "")

    team_id = payload.get("team", {}).get("id")
    user_id = payload.get("user", {}).get("id")

    if not workflow_name or not trigger_type:
        return {
            "response_action": "errors",
            "errors": {
                "workflow_name": "Workflow name is required" if not workflow_name else None,
                "trigger_type": "Trigger type is required" if not trigger_type else None
            }
        }

    # Create workflow
    workflow = await workflow_trigger_service.create_slack_workflow(
        name=workflow_name,
        trigger_type=trigger_type,
        team_id=team_id,
        user_id=user_id
    )

    if workflow:
        # Send confirmation message
        channel_id = payload.get("channel", {}).get("id")
        if channel_id:
            await slack_service.send_message(
                team_id=team_id,
                channel=channel_id,
                text=f"✅ Workflow '{workflow_name}' created successfully! You can now configure it using `/workflow list`."
            )

    return {"response_action": "clear"}


async def handle_create_workflow_shortcut(payload: dict):
    """Handle create workflow app shortcut"""
    trigger_id = payload.get("trigger_id")
    team_id = payload.get("team", {}).get("id")

    # This would open a comprehensive workflow creation modal
    # Similar to the slash command version but with more options
    pass
```

## 6. Node Specifications for Slack Integration

Based on the existing node specification patterns in your codebase, here are the detailed specifications for the two key Slack nodes:

### 6.1 Slack Trigger Node Specification

The Slack Trigger Node allows users to trigger workflows through bot interactions in Slack. This follows the existing `TRIGGER_NODE` pattern but adds Slack-specific functionality.

```python
# apps/backend/shared/node_specs/definitions/trigger_nodes.py (Addition)

# Slack trigger - bot interaction in Slack workspaces
SLACK_TRIGGER_SPEC = NodeSpec(
    node_type="TRIGGER_NODE",
    subtype="TRIGGER_SLACK",
    description="Slack bot trigger activated by user interactions in Slack",
    parameters=[
        ParameterDef(
            name="team_id",
            type=ParameterType.STRING,
            required=True,
            description="Slack workspace team ID where the bot is installed",
        ),
        ParameterDef(
            name="trigger_type",
            type=ParameterType.ENUM,
            required=True,
            enum_values=["app_mention", "direct_message", "slash_command", "button_click", "modal_submit"],
            description="Type of Slack interaction that triggers the workflow",
        ),
        ParameterDef(
            name="command_pattern",
            type=ParameterType.STRING,
            required=False,
            description="Command pattern to match (regex, e.g., 'run workflow .*' or '/workflow .*')",
            validation_pattern=r"^.+$",
        ),
        ParameterDef(
            name="channel_filter",
            type=ParameterType.STRING,
            required=False,
            description="Specific channel ID to monitor (empty means all channels)",
        ),
        ParameterDef(
            name="user_filter",
            type=ParameterType.STRING,
            required=False,
            description="Specific user ID filter (empty means all users)",
        ),
        ParameterDef(
            name="require_mention",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Whether bot mention is required to trigger (for channel messages)",
        ),
        ParameterDef(
            name="response_in_thread",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Whether to respond in thread to keep channels clean",
        ),
        ParameterDef(
            name="immediate_ack",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Send immediate acknowledgment before workflow execution",
        ),
        ParameterDef(
            name="ack_message",
            type=ParameterType.STRING,
            required=False,
            default_value="🤖 Got it! Processing your request...",
            description="Message to send as immediate acknowledgment",
        ),
    ],
    input_ports=[],  # Trigger nodes have no input ports
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Slack trigger event data",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"trigger_time": "string", "execution_id": "string", "slack_data": "object", "user": "object", "channel": "object"}',
                examples=[
                    '{"trigger_time": "2025-01-28T10:30:00Z", "execution_id": "exec_123", "slack_data": {"text": "@bot run my-workflow", "ts": "1706441400.123456"}, "user": {"id": "U123456", "name": "john.doe"}, "channel": {"id": "C123456", "name": "general"}}'
                ],
            ),
            validation_schema='{"type": "object", "properties": {"trigger_time": {"type": "string"}, "execution_id": {"type": "string"}, "slack_data": {"type": "object"}, "user": {"type": "object"}, "channel": {"type": "object"}}, "required": ["trigger_time", "execution_id", "slack_data", "user"]}',
        )
    ],
)
```

### 6.2 Slack External Action Node Specification

The Slack External Action Node enables workflows to send messages to Slack channels or direct messages. This enhances the existing `SLACK_SPEC` with more comprehensive messaging capabilities.

```python
# apps/backend/shared/node_specs/definitions/external_action_nodes.py (Enhanced)

# Enhanced Slack - comprehensive Slack messaging operations
SLACK_ENHANCED_SPEC = NodeSpec(
    node_type="EXTERNAL_ACTION_NODE",
    subtype="SLACK",
    description="Send messages and interact with Slack workspaces",
    parameters=[
        ParameterDef(
            name="team_id",
            type=ParameterType.STRING,
            required=True,
            description="Slack workspace team ID",
        ),
        ParameterDef(
            name="action_type",
            type=ParameterType.ENUM,
            required=True,
            default_value="send_message",
            enum_values=["send_message", "send_dm", "upload_file", "add_reaction", "update_message"],
            description="Type of Slack action to perform",
        ),
        ParameterDef(
            name="channel",
            type=ParameterType.STRING,
            required=False,
            description="Channel ID or name (required for channel messages, ignored for DMs)",
        ),
        ParameterDef(
            name="user_id",
            type=ParameterType.STRING,
            required=False,
            description="User ID for direct messages (required when action_type is 'send_dm')",
        ),
        ParameterDef(
            name="message_text",
            type=ParameterType.STRING,
            required=False,
            description="Plain text message content",
        ),
        ParameterDef(
            name="message_blocks",
            type=ParameterType.JSON,
            required=False,
            description="Slack Block Kit formatted message (overrides message_text if provided)",
        ),
        ParameterDef(
            name="broadcast_reply",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=False,
            description="Broadcast thread reply to channel",
        ),
        ParameterDef(
            name="message_ts",
            type=ParameterType.STRING,
            required=False,
            description="Message timestamp (required for update_message and add_reaction)",
        ),
        ParameterDef(
            name="unfurl_links",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Automatically unfurl links in messages",
        ),
        ParameterDef(
            name="unfurl_media",
            type=ParameterType.BOOLEAN,
            required=False,
            default_value=True,
            description="Automatically unfurl media in messages",
        )
    ],
    input_ports=[
        InputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            required=False,
            description="Dynamic message content and Slack-specific data",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"dynamic_content": "object", "template_vars": "object", "slack_context": "object"}',
                examples=[
                    '{"dynamic_content": {"blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "Workflow completed successfully!"}}]}, "template_vars": {"user_name": "John", "result": "success"}, "slack_context": {"original_channel": "C123456", "original_user": "U123456"}}'
                ],
            ),
        )
    ],
    output_ports=[
        OutputPortSpec(
            name="main",
            type=ConnectionType.MAIN,
            description="Slack action result",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"message_ts": "string", "channel": "string", "success": "boolean", "permalink": "string", "response_metadata": "object"}',
                examples=[
                    '{"message_ts": "1706441400.123456", "channel": "C123456", "success": true, "permalink": "https://workspace.slack.com/archives/C123456/p1706441400123456", "response_metadata": {"scopes": ["chat:write"], "acceptedScopes": ["chat:write"]}}'
                ],
            ),
        ),
        OutputPortSpec(
            name="error",
            type=ConnectionType.ERROR,
            description="Error output when Slack operation fails",
            data_format=DataFormat(
                mime_type="application/json",
                schema='{"error_code": "string", "error_message": "string", "details": "object"}',
                examples=[
                    '{"error_code": "channel_not_found", "error_message": "Channel not found", "details": {"channel": "invalid_channel"}}'
                ],
            ),
        ),
    ],
)
```

## 7. Implementation Architecture for Slack Nodes

### 7.1 Slack Trigger Node Implementation Details

#### Event Processing Flow

```
Slack Event → API Gateway Webhook → Workflow Scheduler → Trigger Manager → Workflow Engine
```

#### Key Components:

**1. Slack Event Handler (in Workflow Scheduler)**

````python
# apps/backend/workflow_scheduler/app/triggers/slack_trigger.py

class SlackTrigger(BaseTrigger):
    """Handles incoming Slack events and matches them to workflow triggers"""

    async def process_event(self, event_data: dict, team_id: str):
        """Process Slack event and trigger matching workflows"""

        # Extract event details
        event_type = event_data.get("event", {}).get("type")
        channel = event_data.get("event", {}).get("channel")
        user = event_data.get("event", {}).get("user")
        text = event_data.get("event", {}).get("text", "")
        ts = event_data.get("event", {}).get("ts")

        # This follows the same pattern as other triggers in workflow_scheduler
        # The TriggerManager will handle the actual workflow execution
        if await self.matches_trigger_conditions(event_type, event_data):
            workflow_context = await SlackWorkflowContext.build_context(
                self.trigger_config, event_data
            )
            await self._trigger_workflow(workflow_context)

    async def find_slack_triggers(self, team_id: str, event_type: str, event_data: dict):
        """Find workflow triggers that match this Slack event"""

        # Query database for active Slack triggers
        query = """
        SELECT wt.*, w.workflow_definition
        FROM workflow_triggers wt
        JOIN workflows w ON wt.workflow_id = w.id
        WHERE wt.trigger_type = 'TRIGGER_SLACK'
        AND wt.active = true
        AND JSON_EXTRACT(wt.trigger_config, '$.team_id') = ?
        """

        triggers = await self.db.fetch_all(query, team_id)

        # Filter triggers based on event matching logic
        matching = []
        for trigger in triggers:
            if await self.matches_trigger_conditions(trigger, event_type, event_data):
                matching.append(trigger)

        return matching

    async def matches_trigger_conditions(self, trigger: dict, event_type: str, event_data: dict) -> bool:
        """Check if event matches trigger conditions"""

        config = trigger.get("trigger_config", {})

        # Check trigger type
        trigger_type = config.get("trigger_type")
        if trigger_type == "app_mention" and event_type != "app_mention":
            return False
        elif trigger_type == "direct_message" and event_type != "message":
            return False
        elif trigger_type == "slash_command":
            # Handle via separate webhook endpoint
            return False

        # Check channel filter
        channel_filter = config.get("channel_filter")
        if channel_filter and event_data.get("channel") != channel_filter:
            return False

        # Check user filter
        user_filter = config.get("user_filter")
        if user_filter and event_data.get("user") != user_filter:
            return False

        # Check command pattern
        command_pattern = config.get("command_pattern")
        if command_pattern:
            import re
            text = event_data.get("text", "")
            if not re.search(command_pattern, text, re.IGNORECASE):
                return False

        # Check mention requirement
        if config.get("require_mention", True) and event_type == "message":
            bot_user_id = await self.get_bot_user_id(config.get("team_id"))
            if f"<@{bot_user_id}>" not in event_data.get("text", ""):
                return False

        return True


**2. API Gateway Webhook Handler**
```python
# apps/backend/api-gateway/app/webhooks/slack.py

@router.post("/webhooks/slack/events")
async def slack_events_webhook(
    request: Request,
    x_slack_signature: str = Header(...),
    x_slack_request_timestamp: str = Header(...),
):
    """Receive Slack events and forward to workflow_scheduler"""
    body = await request.body()

    # Verify Slack request signature
    if not verify_slack_signature(x_slack_request_timestamp, x_slack_signature, body):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse event data
    try:
        event_data = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Handle URL verification challenge
    if event_data.get("type") == "url_verification":
        return {"challenge": event_data.get("challenge")}

    # Forward to workflow_scheduler
    team_id = event_data.get("team_id")
    if not team_id:
        raise HTTPException(status_code=400, detail="Missing team_id")

    # Call workflow_scheduler to process the Slack event
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.workflow_scheduler_url}/api/v1/triggers/slack/events",
            json={
                "team_id": team_id,
                "event_data": event_data
            },
            timeout=30.0
        )

        if response.status_code != 200:
            logger.error(f"Failed to forward Slack event to workflow_scheduler: {response.text}")
            raise HTTPException(status_code=500, detail="Failed to process event")

    return {"ok": True}
````

**3. Workflow Scheduler Slack Event Handler**

```python
# apps/backend/workflow_scheduler/app/api/slack.py

@router.post("/api/v1/triggers/slack/events")
async def process_slack_event(
    event_request: SlackEventRequest,
    trigger_manager: TriggerManager = Depends(get_trigger_manager)
):
    """Process Slack event and trigger matching workflows"""

    team_id = event_request.team_id
    event_data = event_request.event_data

    # Find all Slack triggers for this team
    slack_triggers = await trigger_manager.get_triggers_by_type_and_team(
        trigger_type="TRIGGER_SLACK",
        team_id=team_id
    )

    # Process each trigger that matches the event
    results = []
    for trigger in slack_triggers:
        try:
            if await trigger.matches_event(event_data):
                result = await trigger.process_event(event_data)
                results.append({
                    "workflow_id": trigger.workflow_id,
                    "execution_id": result.get("execution_id"),
                    "status": "triggered"
                })
        except Exception as e:
            logger.error(f"Failed to process Slack trigger {trigger.workflow_id}: {e}")
            results.append({
                "workflow_id": trigger.workflow_id,
                "status": "error",
                "error": str(e)
            })

    return {
        "processed_triggers": len(results),
        "results": results
    }


class SlackEventRequest(BaseModel):
    """Request model for Slack event processing"""
    team_id: str
    event_data: dict
```

**4. Workflow Context Builder**

```python
class SlackWorkflowContext:
    """Builds workflow execution context from Slack events"""

    @staticmethod
    async def build_context(trigger: dict, event_data: dict) -> dict:
        """Build workflow execution context from Slack event"""

        event = event_data.get("event", {})

        # Base context
        context = {
            "trigger_time": event_data.get("event_time"),
            "execution_id": f"slack_{event.get('ts', 'unknown')}_{int(time.time())}",
            "slack_data": {
                "text": event.get("text", ""),
                "ts": event.get("ts"),
                "event_type": event.get("type"),
                "channel_type": event.get("channel_type"),
                "team": event_data.get("team_id"),
            },
            "user": {
                "id": event.get("user"),
                "name": await SlackWorkflowContext.get_user_name(
                    event_data.get("team_id"),
                    event.get("user")
                ),
            },
            "channel": {
                "id": event.get("channel"),
                "name": await SlackWorkflowContext.get_channel_name(
                    event_data.get("team_id"),
                    event.get("channel")
                ),
            }
        }

        # Add command parsing if applicable
        if trigger.get("trigger_config", {}).get("command_pattern"):
            context["parsed_command"] = SlackWorkflowContext.parse_command(
                event.get("text", ""),
                trigger.get("trigger_config", {}).get("command_pattern")
            )

        return context

    @staticmethod
    def parse_command(text: str, pattern: str) -> dict:
        """Parse command from Slack message text"""
        import re

        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return {
                "full_match": match.group(0),
                "groups": match.groups(),
                "named_groups": match.groupdict(),
            }
        return {}
```

### 7.2 Slack External Action Node Implementation Details

#### Execution Flow

```
Workflow Engine → Node Executor → Slack Service → Slack Web API → Slack Workspace
```

#### Key Components:

**1. Enhanced Slack Service**

```python
# apps/backend/shared/services/slack_service.py

class EnhancedSlackService:
    """Enhanced Slack service with comprehensive messaging capabilities"""

    def __init__(self):
        self.installations = {}  # Cache for team installations

    async def execute_action(self, team_id: str, action_config: dict, input_data: dict = None) -> dict:
        """Execute Slack action based on configuration"""

        action_type = action_config.get("action_type", "send_message")

        if action_type == "send_message":
            return await self.send_message(team_id, action_config, input_data)
        elif action_type == "send_dm":
            return await self.send_direct_message(team_id, action_config, input_data)
        elif action_type == "upload_file":
            return await self.upload_file(team_id, action_config, input_data)
        elif action_type == "add_reaction":
            return await self.add_reaction(team_id, action_config, input_data)
        elif action_type == "update_message":
            return await self.update_message(team_id, action_config, input_data)
        else:
            raise ValueError(f"Unsupported action type: {action_type}")

    async def send_message(self, team_id: str, config: dict, input_data: dict = None) -> dict:
        """Send message to Slack channel"""

        client = await self.get_slack_client(team_id)

        # Build message content
        message_content = await self.build_message_content(config, input_data)

        # Send message
        response = await client.chat_post_message(
            channel=config.get("channel"),
            text=message_content.get("text"),
            blocks=message_content.get("blocks"),
            thread_ts=config.get("thread_ts"),
            reply_broadcast=config.get("broadcast_reply", False),
            unfurl_links=config.get("unfurl_links", True),
            unfurl_media=config.get("unfurl_media", True),
            as_user=config.get("as_user", False)
        )

        return {
            "message_ts": response.get("ts"),
            "channel": response.get("channel"),
            "success": True,
            "permalink": await self.get_permalink(client, response.get("channel"), response.get("ts")),
            "response_metadata": response.get("response_metadata", {})
        }

    async def send_direct_message(self, team_id: str, config: dict, input_data: dict = None) -> dict:
        """Send direct message to Slack user"""

        client = await self.get_slack_client(team_id)

        # Open DM channel
        dm_response = await client.conversations_open(users=[config.get("user_id")])
        dm_channel = dm_response.get("channel", {}).get("id")

        # Build and send message
        message_content = await self.build_message_content(config, input_data)

        response = await client.chat_post_message(
            channel=dm_channel,
            text=message_content.get("text"),
            blocks=message_content.get("blocks"),
            unfurl_links=config.get("unfurl_links", True),
            unfurl_media=config.get("unfurl_media", True)
        )

        return {
            "message_ts": response.get("ts"),
            "channel": dm_channel,
            "success": True,
            "permalink": await self.get_permalink(client, dm_channel, response.get("ts")),
            "response_metadata": response.get("response_metadata", {})
        }

    async def build_message_content(self, config: dict, input_data: dict = None) -> dict:
        """Build message content from config and input data"""

        content = {}

        # Handle dynamic content from input
        if input_data and "dynamic_content" in input_data:
            dynamic = input_data["dynamic_content"]

            if "blocks" in dynamic:
                content["blocks"] = dynamic["blocks"]
            elif "text" in dynamic:
                content["text"] = dynamic["text"]

        # Fall back to static config
        if not content:
            if config.get("message_blocks"):
                content["blocks"] = config.get("message_blocks")
            else:
                content["text"] = config.get("message_text", "")

        # Apply template variables if present
        if input_data and "template_vars" in input_data:
            content = await self.apply_template_variables(content, input_data["template_vars"])

        return content

    async def apply_template_variables(self, content: dict, variables: dict) -> dict:
        """Apply template variables to message content"""
        import json
        import re

        # Convert content to string for processing
        content_str = json.dumps(content)

        # Replace template variables ({{variable_name}})
        for key, value in variables.items():
            content_str = content_str.replace(f"{{{{{key}}}}}", str(value))

        # Convert back to dict
        return json.loads(content_str)
```

**2. Node Executor Integration**

```python
# apps/backend/workflow_engine/nodes/external_action_node.py

class SlackActionNodeExecutor:
    """Executor for Slack external action nodes"""

    def __init__(self):
        self.slack_service = EnhancedSlackService()

    async def execute(self, node_config: dict, input_data: dict = None) -> dict:
        """Execute Slack action node"""

        try:
            # Validate required parameters
            team_id = node_config.get("team_id")
            if not team_id:
                raise ValueError("team_id is required for Slack actions")

            # Execute the action
            result = await self.slack_service.execute_action(
                team_id=team_id,
                action_config=node_config,
                input_data=input_data
            )

            return {
                "success": True,
                "result": result,
                "node_output": result
            }

        except Exception as e:
            return {
                "success": False,
                "error": {
                    "error_code": type(e).__name__,
                    "error_message": str(e),
                    "details": {"node_config": node_config}
                }
            }
```

## 8. Integration Points and Data Flow

### 8.1 Slack Trigger → Workflow Execution

```
1. User interacts with bot in Slack (@bot run my-workflow)
2. Slack sends event to API Gateway webhook endpoint
3. API Gateway verifies signature and forwards to workflow_scheduler
4. Workflow_scheduler's SlackTrigger processes and matches to workflows
5. Workflow context built from Slack event data
6. Workflow_scheduler calls workflow_engine to execute workflow
7. Bot sends acknowledgment if configured (via Slack External Action Node)
8. Workflow executes with Slack context available
```

### 8.2 Workflow → Slack Action

```
1. Workflow reaches Slack action node
2. Node executor calls Slack service
3. Message content built from config + input data
4. Slack Web API called with bot token
5. Response processed and returned to workflow
6. Workflow continues with Slack response data
```

### 8.3 Error Handling and Retry Logic

**Trigger Node Errors:**

- Invalid team_id → Log error, skip trigger
- Bot not in channel → Log warning, attempt DM to user
- Rate limits → Queue for retry with exponential backoff
- Auth failures → Disable trigger, notify admin

**Action Node Errors:**

- Channel not found → Try user DM fallback
- Permission denied → Log error, return to error port
- Rate limits → Retry with backoff (up to 3 attempts)
- Message too long → Truncate with indicator

This comprehensive design provides robust Slack integration that follows your existing node specification patterns while adding the specific trigger and action capabilities you need.

## 9. Summary

The updated technical design now includes:

### Slack Trigger Node (`TRIGGER_SLACK`)

- **Purpose**: Allow users to trigger workflows by interacting with your Slack bot
- **Trigger Types**: App mentions, direct messages, slash commands, button clicks, modal submissions
- **Key Features**:
  - Flexible command pattern matching with regex support
  - Channel and user filtering capabilities
  - Immediate acknowledgment with customizable messages
  - Thread-based responses to keep channels clean
  - Rich context passing to workflows (user info, channel info, parsed commands)

### Slack External Action Node (Enhanced `SLACK`)

- **Purpose**: Send messages and interact with Slack from workflows
- **Action Types**: Send messages, direct messages, file uploads, reactions, message updates
- **Key Features**:
  - Support for both plain text and Slack Block Kit messages
  - Template variable substitution for dynamic content
  - Thread support for organized conversations
  - Error handling with fallback to DMs
  - Comprehensive response data for workflow chaining

### Implementation Architecture

- **Event Processing**: Slack → API Gateway → Workflow Scheduler → Trigger Manager → Workflow Engine
- **Action Execution**: Workflow Engine → Node Executor → Enhanced Slack Service → Slack API
- **Error Handling**: Comprehensive retry logic, fallback mechanisms, and error ports
- **Integration**: Follows your existing node specification patterns and workflow_scheduler architecture

This design enables seamless bidirectional communication between your AI workflows and Slack workspaces, allowing users to trigger workflows naturally through chat and receive results back in context.
