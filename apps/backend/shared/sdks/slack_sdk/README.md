# Slack SDK

A powerful and easy-to-use Python SDK for Slack Web API integration, built specifically for workflow automation and bot interactions.

## What This SDK Can Do

### 📩 Messaging Capabilities
- **Send messages to channels** - Post messages to public/private channels
- **Send direct messages** - Send private messages directly to users
- **Reply to threads** - Reply to existing message threads
- **Rich message formatting** - Use Slack Block Kit for interactive messages
- **File attachments** - Send messages with file attachments
- **Message scheduling** - Schedule messages for later delivery

### 🔍 Information Retrieval
- **Get user information** - Retrieve user profiles and status
- **Get channel information** - Access channel details and member lists
- **List channels** - Browse available channels in workspace
- **Authentication testing** - Verify bot token and permissions

### 🛡️ Security & Reliability
- **Request signature verification** - Verify webhook authenticity
- **Automatic rate limiting** - Handle API rate limits gracefully
- **Comprehensive error handling** - Specific exceptions for different scenarios
- **Token management** - Secure OAuth flow for app installations

## Core Components

- **SlackWebClient**: Main client for all Slack Web API interactions
- **SlackBlockBuilder**: Utility for creating rich, interactive messages
- **SlackInstallationManager**: OAuth 2.0 flow for multi-workspace installations
- **Error Classes**: Specific exceptions for robust error handling

## Quick Start

### Installation

```bash
pip install httpx
```

### Environment Setup

Set your Slack bot token as an environment variable:

```bash
export SLACK_BOT_TOKEN="xoxb-your-bot-token-here"
```

### Basic Usage Examples

#### 1. Send a Simple Message to Channel

```python
from slack_sdk import SlackWebClient

with SlackWebClient("xoxb-your-bot-token") as client:
    response = client.send_message(
        channel="#general",
        text="Hello from Slack SDK! 👋"
    )
    print(f"Message sent at {response['ts']}")
```

#### 2. Send a Direct Message to User

```python
with SlackWebClient("xoxb-your-bot-token") as client:
    response = client.send_dm(
        user_id="U123456789",  # User ID from Slack
        text="This is a private message just for you!"
    )
```

#### 3. Reply to a Message Thread

```python
with SlackWebClient("xoxb-your-bot-token") as client:
    response = client.send_message(
        channel="#general",
        text="This is a thread reply! 🧵",
        thread_ts="1609459200.000300"  # Original message timestamp
    )
```

#### 4. Send Rich Formatted Messages

```python
from slack_sdk import SlackWebClient, SlackBlockBuilder

with SlackWebClient("xoxb-your-bot-token") as client:
    # Create rich notification
    blocks = SlackBlockBuilder.notification_message(
        title="Deployment Complete",
        message="Your application has been successfully deployed to production!",
        status="success",
        timestamp="2025-01-28 10:30:00"
    )

    client.send_message(
        channel="#deployments",
        text="Deployment notification",  # Fallback text
        blocks=blocks
    )
```

## Detailed Usage Guide

### SlackWebClient - Complete Reference

#### Messaging Methods

```python
from slack_sdk import SlackWebClient

with SlackWebClient("xoxb-your-token") as client:
    # 1. Basic channel message
    response = client.send_message(
        channel="#general",
        text="Hello everyone! 👋"
    )

    # 2. Message with thread reply
    response = client.send_message(
        channel="#general",
        text="This is a reply in a thread",
        thread_ts="1609459200.000300",  # Parent message timestamp
        reply_broadcast=True  # Also show in main channel
    )

    # 3. Direct message to user
    response = client.send_dm(
        user_id="U123456789",
        text="Hi there! This is a private message."
    )

    # 4. Message with rich blocks
    response = client.send_message(
        channel="#general",
        text="Fallback text for notifications",
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Important Update* 📢\nSystem maintenance completed successfully!"
                }
            }
        ]
    )

    # 5. Message with attachments (legacy format)
    response = client.send_message(
        channel="#general",
        text="Report attached",
        attachments=[
            {
                "color": "good",
                "title": "Monthly Report",
                "text": "All metrics are looking great!"
            }
        ]
    )
```

#### Information Retrieval Methods

```python
with SlackWebClient("xoxb-your-token") as client:
    # Get user information
    user_info = client.get_user_info("U123456789")
    print(f"User: {user_info['real_name']} ({user_info['name']})")

    # Get channel information
    channel_info = client.get_channel_info("C123456789")
    print(f"Channel: {channel_info['name']} - {channel_info['purpose']['value']}")

    # List all channels
    channels = client.list_channels(types="public_channel,private_channel")
    for channel in channels:
        print(f"#{channel['name']} - {channel['id']}")

    # Test authentication and get bot info
    auth_info = client.auth_test()
    print(f"Bot: {auth_info['user']} in team {auth_info['team']}")
```

### SlackBlockBuilder - Rich Message Formatting

Create beautiful, interactive messages using Slack Block Kit:

#### Pre-built Templates

```python
from slack_sdk import SlackBlockBuilder

# 1. Simple message with optional pretext
blocks = SlackBlockBuilder.simple_message(
    text="Your daily report is ready for review.",
    pretext="📊 Daily Analytics Report"
)

# 2. Status notifications with color coding
blocks = SlackBlockBuilder.notification_message(
    title="Deployment Status",
    message="Production deployment completed successfully!",
    status="success",  # "info", "success", "warning", "error"
    timestamp="2025-01-28 15:30:00"
)

# 3. Error notifications
blocks = SlackBlockBuilder.notification_message(
    title="System Alert",
    message="Database connection failed. Please check logs.",
    status="error",
    timestamp="2025-01-28 15:45:00"
)
```

#### Custom Block Layouts

```python
# Build custom layouts with individual components
blocks = [
    # Header section
    SlackBlockBuilder.header("🚀 Weekly Performance Report"),

    # Main content
    SlackBlockBuilder.section(
        text="*This week's highlights:*\n• 🎯 Goals achieved: 95%\n• 📈 Revenue growth: +12%\n• 👥 New users: 1,247",
        fields=SlackBlockBuilder.fields(
            "*Total Revenue*\n$45,231",
            "*Active Users*\n12,847",
            "*Conversion Rate*\n3.2%",
            "*Support Tickets*\n23 resolved"
        )
    ),

    # Visual separator
    SlackBlockBuilder.divider(),

    # Footer with timestamp
    SlackBlockBuilder.context([
        SlackBlockBuilder.text_element("📅 Generated on January 28, 2025 at 3:30 PM")
    ])
]

# Send the custom layout
with SlackWebClient("xoxb-your-token") as client:
    client.send_message(
        channel="#reports",
        text="Weekly Performance Report",  # Fallback text
        blocks=blocks
    )
```

#### Interactive Elements

```python
# Create messages with buttons and actions
blocks = [
    SlackBlockBuilder.section("Would you like to approve this deployment?"),
    SlackBlockBuilder.actions([
        SlackBlockBuilder.button(
            text="✅ Approve",
            action_id="approve_deployment",
            style="primary",
            value="deploy_v2.1.0"
        ),
        SlackBlockBuilder.button(
            text="❌ Reject",
            action_id="reject_deployment",
            style="danger",
            value="deploy_v2.1.0"
        )
    ])
]
```

### SlackInstallationManager

Handle OAuth flow for app installation:

```python
from slack_sdk import SlackInstallationManager

manager = SlackInstallationManager(
    client_id="your-client-id",
    client_secret="your-client-secret",
    signing_secret="your-signing-secret",
    redirect_uri="https://yourdomain.com/slack/oauth_redirect",
    scopes=["chat:write", "channels:read"]
)

# Generate install URL
install_url, state = manager.generate_install_url()

# Handle OAuth callback
installation_data = manager.handle_oauth_callback(
    code=oauth_code,
    state=received_state,
    expected_state=state
)

# Verify webhook signatures
is_valid = manager.verify_request_signature(
    body=request_body,
    timestamp=request_headers["X-Slack-Request-Timestamp"],
    signature=request_headers["X-Slack-Signature"]
)
```

## Error Handling

The SDK provides specific exceptions for different error scenarios:

```python
from slack_sdk import SlackWebClient, SlackAPIError, SlackAuthError

try:
    with SlackWebClient("invalid-token") as client:
        client.send_message(channel="#general", text="Test")

except SlackAuthError as e:
    print(f"Authentication failed: {e}")
except SlackRateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")
except SlackChannelNotFoundError as e:
    print(f"Channel not found: {e}")
except SlackAPIError as e:
    print(f"API error: {e.error_code} - {e}")
```

## Workflow System Integration

This SDK is specifically designed for the workflow automation system:

### Slack Trigger Node Implementation

```python
# workflow_scheduler/handlers/slack_handler.py
from slack_sdk import SlackInstallationManager
from workflow_scheduler.core.trigger_manager import TriggerManager

class SlackTriggerHandler:
    def __init__(self):
        self.installation_manager = SlackInstallationManager(
            client_id=settings.SLACK_CLIENT_ID,
            client_secret=settings.SLACK_CLIENT_SECRET,
            signing_secret=settings.SLACK_SIGNING_SECRET,
            redirect_uri=settings.SLACK_REDIRECT_URI,
            scopes=["chat:write", "channels:read", "app_mentions:read"]
        )
        self.trigger_manager = TriggerManager()

    async def handle_slack_event(self, request_body: str, headers: dict):
        # Verify request signature
        if not self.installation_manager.verify_request_signature(
            body=request_body,
            timestamp=headers["X-Slack-Request-Timestamp"],
            signature=headers["X-Slack-Signature"]
        ):
            raise ValueError("Invalid request signature")

        event_data = json.loads(request_body)

        # Handle different event types
        if event_data["type"] == "event_callback":
            event = event_data["event"]

            if event["type"] == "app_mention":
                # User mentioned the bot - trigger workflow
                await self.trigger_manager.trigger_workflow(
                    trigger_type="slack_mention",
                    event_data={
                        "user_id": event["user"],
                        "channel_id": event["channel"],
                        "text": event["text"],
                        "timestamp": event["ts"]
                    }
                )
```

### Slack External Action Node Implementation

```python
# workflow_engine/nodes/external_actions/slack_node.py
from slack_sdk import SlackWebClient, SlackBlockBuilder
from workflow_engine.core.base_node import BaseExternalActionNode

class SlackActionNode(BaseExternalActionNode):
    def __init__(self, node_config: dict):
        super().__init__(node_config)
        self.bot_token = node_config["parameters"]["bot_token"]
        self.channel = node_config["parameters"]["channel"]
        self.message = node_config["parameters"]["message"]

    async def execute(self, input_data: dict) -> dict:
        try:
            with SlackWebClient(self.bot_token) as client:
                # Build message based on input data
                if "blocks" in input_data:
                    # Rich message with blocks from previous nodes
                    blocks = input_data["blocks"]
                    text = input_data.get("fallback_text", self.message)
                else:
                    # Simple text message
                    blocks = None
                    text = self.message.format(**input_data)  # Template substitution

                # Send the message
                response = client.send_message(
                    channel=self.channel,
                    text=text,
                    blocks=blocks,
                    thread_ts=input_data.get("thread_ts"),
                    reply_broadcast=input_data.get("reply_broadcast", False)
                )

                return {
                    "status": "success",
                    "timestamp": response["ts"],
                    "channel": response["channel"],
                    "message": response["message"]
                }

        except Exception as e:
            return {
                "status": "error",
                "error_message": str(e),
                "error_type": type(e).__name__
            }
```

### Notification Helper

```python
# shared/services/slack_notifications.py
from slack_sdk import SlackWebClient, SlackBlockBuilder
import os

class SlackNotificationService:
    def __init__(self):
        self.client = SlackWebClient(os.getenv("SLACK_BOT_TOKEN"))

    def notify_workflow_completion(self, workflow_id: str, status: str, channel: str = "#workflows"):
        """Send workflow completion notification"""
        blocks = SlackBlockBuilder.notification_message(
            title="Workflow Complete",
            message=f"Workflow {workflow_id} finished with status: {status}",
            status="success" if status == "completed" else "error"
        )

        return self.client.send_message(
            channel=channel,
            text=f"Workflow {workflow_id} {status}",
            blocks=blocks
        )

    def notify_error(self, error_message: str, context: dict, channel: str = "#alerts"):
        """Send error notification to alerts channel"""
        blocks = [
            SlackBlockBuilder.header("🚨 System Error Alert"),
            SlackBlockBuilder.section(f"*Error:* {error_message}"),
            SlackBlockBuilder.section(
                "*Context:*",
                fields=SlackBlockBuilder.fields(
                    *[f"*{k}:* {v}" for k, v in context.items()]
                )
            )
        ]

        return self.client.send_message(
            channel=channel,
            text=f"System Error: {error_message}",
            blocks=blocks
        )
```

## Integration Guide

### Adding to Your Project

1. **Copy the SDK to your project:**
   ```bash
   cp -r shared/sdks/slack_sdk /path/to/your/project/
   ```

2. **Install dependencies:**
   ```bash
   pip install httpx
   ```

3. **Import and use:**
   ```python
   from slack_sdk import SlackWebClient, SlackBlockBuilder
   ```

### Integration Examples

#### FastAPI Integration

```python
from fastapi import FastAPI, HTTPException
from slack_sdk import SlackWebClient, SlackAPIError
import os

app = FastAPI()
slack_client = SlackWebClient(os.getenv("SLACK_BOT_TOKEN"))

@app.post("/send-notification")
async def send_notification(channel: str, message: str):
    try:
        response = slack_client.send_message(channel=channel, text=message)
        return {"success": True, "timestamp": response["ts"]}
    except SlackAPIError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

#### Celery Task Integration

```python
from celery import Celery
from slack_sdk import SlackWebClient, SlackBlockBuilder
import os

app = Celery('slack_notifications')

@app.task
def send_deployment_notification(status: str, environment: str):
    with SlackWebClient(os.getenv("SLACK_BOT_TOKEN")) as client:
        blocks = SlackBlockBuilder.notification_message(
            title=f"Deployment to {environment}",
            message=f"Status: {status}",
            status="success" if status == "completed" else "error"
        )

        return client.send_message(
            channel="#deployments",
            text=f"Deployment {status}",
            blocks=blocks
        )
```

#### Django Integration

```python
# settings.py
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")

# utils/slack_utils.py
from django.conf import settings
from slack_sdk import SlackWebClient

def notify_admins(message: str):
    with SlackWebClient(settings.SLACK_BOT_TOKEN) as client:
        return client.send_message(
            channel="#admin-alerts",
            text=message
        )

# In your views or models
from utils.slack_utils import notify_admins

def process_order(order):
    # ... order processing logic ...
    notify_admins(f"New order #{order.id} processed successfully")
```

## Testing

Run the included test script to verify your setup:

```bash
# Set your bot token in environment or .env file
export SLACK_BOT_TOKEN=xoxb-your-bot-token

# Run the test script
cd shared/sdks/slack_sdk
python test_slack.py
```

The test will:
- ✅ Verify authentication
- ✅ Send a basic text message
- ✅ Send a rich Block Kit message
- ✅ Test all SDK components

## Requirements

- Python 3.8+
- httpx >= 0.24.0

## Slack App Setup

To use this SDK, you need a Slack app with appropriate permissions:

1. **Create Slack App**: Go to https://api.slack.com/apps
2. **OAuth & Permissions**: Add bot token scopes:
   - `chat:write` - Send messages
   - `channels:read` - Access channel information
   - `users:read` - Access user information
   - `app_mentions:read` - Receive mentions (for triggers)
3. **Install App**: Install to your workspace to get bot token
4. **Event Subscriptions** (for triggers): Enable and set request URL

## Architecture Integration

This SDK integrates with the workflow system architecture:

```
Slack Events → API Gateway → Workflow Scheduler → Trigger Manager → Workflow Engine
                                     ↓
Workflow Engine → Slack SDK → Slack Web API
```

- **Triggers**: Slack events processed by workflow_scheduler
- **Actions**: Messages sent via workflow_engine using this SDK
