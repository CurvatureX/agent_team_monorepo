# Workflow Scheduler Technical Design

## 1. Executive Summary

**workflow_scheduler** is the trigger management and scheduling core of the Workflow System, responsible for managing workflow trigger conditions and coordinating workflow execution with the workflow_engine.

### Core Responsibilities

1. **Trigger Management**: Manage Cron, Manual, Webhook, Email, GitHub, Slack, and Google Calendar triggers
2. **Schedule Monitoring**: Continuously monitor trigger conditions to ensure timely response
3. **Deployment Management**: Manage workflow deployment status and trigger configuration
4. **Schedule Coordination**: Call workflow_engine via HTTP when trigger conditions are met

### Technology Stack

- **Web Framework**: FastAPI (Python 3.11+)
- **Scheduler**: APScheduler for cron triggers
- **Database**: Supabase PostgreSQL with RLS
- **Cache/Lock**: Redis for distributed locking
- **HTTP Client**: httpx for async HTTP calls
- **Dependency Management**: uv for Python packages

## 2. System Architecture

### 2.1 High-Level Architecture

```mermaid
graph TD
    subgraph "Client Layer"
        UI["Frontend (Web/App)"]
        API_CLIENTS["External API Clients"]
        WEBHOOK_CLIENTS["Webhook Clients"]
        EXTERNAL_EVENTS["External Events (Slack, GitHub, Email)"]
    end

    subgraph "API Gateway Layer"
        API_GATEWAY["API Gateway (FastAPI)"]
    end

    subgraph "Workflow Scheduler Service (Port 8003)"
        MAIN["Main FastAPI App"]
        DEPLOY_SERVICE["DeploymentService"]
        TRIGGER_MANAGER["TriggerManager"]
        EVENT_ROUTER["EventRouter"]

        CRON_TRIGGER["CronTrigger (APScheduler)"]
        MANUAL_TRIGGER["ManualTrigger"]
        WEBHOOK_TRIGGER["WebhookTrigger"]
        EMAIL_TRIGGER["EmailTrigger"]
        GITHUB_TRIGGER["GitHubTrigger"]
        SLACK_TRIGGER["SlackTrigger"]

        TRIGGER_INDEX_MGR["TriggerIndexManager"]
        LOCK_MGR["DistributedLockManager"]
    end

    subgraph "Workflow Engine Service (Port 8002)"
        WF_ENGINE["workflow_engine (FastAPI)"]
    end

    subgraph "Data Layer"
        SUPABASE[("Supabase PostgreSQL")]
        REDIS[("Redis")]
    end

    UI --> API_GATEWAY
    API_CLIENTS --> API_GATEWAY
    WEBHOOK_CLIENTS --> API_GATEWAY
    EXTERNAL_EVENTS --> API_GATEWAY

    API_GATEWAY --> MAIN

    MAIN --> DEPLOY_SERVICE
    MAIN --> TRIGGER_MANAGER
    MAIN --> EVENT_ROUTER

    DEPLOY_SERVICE --> TRIGGER_MANAGER
    DEPLOY_SERVICE --> TRIGGER_INDEX_MGR
    DEPLOY_SERVICE --> SUPABASE

    TRIGGER_MANAGER --> CRON_TRIGGER
    TRIGGER_MANAGER --> MANUAL_TRIGGER
    TRIGGER_MANAGER --> WEBHOOK_TRIGGER
    TRIGGER_MANAGER --> EMAIL_TRIGGER
    TRIGGER_MANAGER --> GITHUB_TRIGGER
    TRIGGER_MANAGER --> SLACK_TRIGGER
    TRIGGER_MANAGER --> LOCK_MGR

    CRON_TRIGGER --> WF_ENGINE
    MANUAL_TRIGGER --> WF_ENGINE
    WEBHOOK_TRIGGER --> WF_ENGINE
    EMAIL_TRIGGER --> WF_ENGINE
    GITHUB_TRIGGER --> WF_ENGINE
    SLACK_TRIGGER --> WF_ENGINE

    EVENT_ROUTER --> SUPABASE
    TRIGGER_INDEX_MGR --> SUPABASE
    LOCK_MGR --> REDIS
```

### 2.2 Service Communication

- **Port**: 8003 (HTTP/REST)
- **Protocol**: FastAPI with OpenAPI documentation
- **Health Check**: `curl -f http://localhost:8003/health`
- **Start Period**: 60s

**Key Endpoints**:
- `/api/v1/deployment/workflows/{workflow_id}/deploy` - Deploy workflow
- `/api/v1/deployment/workflows/{workflow_id}/undeploy` - Undeploy workflow
- `/api/v1/triggers/workflows/{workflow_id}/manual` - Manual trigger
- `/api/v1/github/webhook` - GitHub webhook handler
- `/api/v1/slack/events` - Slack event handler

## 3. Core Components

### 3.1 DeploymentService

**Responsibility**: Manage the complete workflow deployment lifecycle

**Deployment Status Flow**:
```
UNDEPLOYED → DEPLOYING → DEPLOYED
                ↓
        DEPLOYMENT_FAILED
```

**Core Operations**:

1. **deploy_workflow(workflow_id, workflow_spec)**:
   - Validate workflow definition (nodes, triggers, connections)
   - Extract trigger specifications from workflow nodes
   - Register triggers with TriggerManager (in-memory)
   - Register triggers with TriggerIndexManager (database)
   - Update workflow deployment status in database
   - Create deployment history record

2. **undeploy_workflow(workflow_id)**:
   - Unregister triggers from TriggerManager
   - Remove trigger index entries
   - Update workflow status to UNDEPLOYED
   - Create deployment history record

3. **deploy_workflow_from_database(workflow_id)**:
   - Fetch workflow spec from database
   - Call deploy_workflow with fetched spec

**Auto-Resolution Features**:
- **GitHub Integration**: Automatically resolves `installation_id` from user's OAuth token
- **Slack Integration**: Automatically resolves `workspace_id` and converts channel names to IDs

### 3.2 TriggerManager

**Responsibility**: Central manager for all trigger types and their lifecycle

**Supported Trigger Types** (from `shared.models.node_enums.TriggerSubtype`):
- `MANUAL`: User-initiated triggers
- `CRON`: Time-based scheduled triggers
- `WEBHOOK`: HTTP endpoint triggers
- `SLACK`: Slack event triggers
- `EMAIL`: Email monitoring triggers
- `GITHUB`: GitHub webhook triggers
- `GOOGLE_CALENDAR`: Google Calendar event triggers

**Core Operations**:

1. **register_triggers(workflow_id, trigger_specs)**:
   - Create trigger instances from specifications
   - Start each trigger (setup monitoring/scheduling)
   - Store active triggers in memory
   - Return success/failure status

2. **unregister_triggers(workflow_id)**:
   - Stop all triggers for workflow
   - Cleanup trigger resources
   - Remove from in-memory registry

3. **restore_active_triggers()**:
   - Called on service startup
   - Query trigger_index table for active triggers
   - Register triggers for all deployed workflows

**Trigger Factory Pattern**:
```python
# Register trigger classes
trigger_manager.register_trigger_class(TriggerSubtype.CRON, CronTrigger)
trigger_manager.register_trigger_class(TriggerSubtype.MANUAL, ManualTrigger)
trigger_manager.register_trigger_class(TriggerSubtype.WEBHOOK, WebhookTrigger)

# Create trigger from specification
trigger = trigger_class(workflow_id, trigger_config)
await trigger.start()
```

### 3.3 TriggerIndexManager

**Responsibility**: Manage trigger indexing for fast event routing and matching

**Database Table**: `trigger_index`

**Schema Design**:
```sql
CREATE TABLE trigger_index (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL,
    trigger_type TEXT NOT NULL,           -- "TRIGGER"
    trigger_subtype TEXT NOT NULL,        -- "CRON", "SLACK", "GITHUB", etc.
    trigger_config JSONB NOT NULL,        -- Full trigger configuration
    index_key TEXT,                        -- Fast lookup key
    deployment_status TEXT DEFAULT 'active', -- 'active', 'inactive', 'pending', 'failed'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_trigger_index_key ON trigger_index(trigger_subtype, index_key)
    WHERE index_key IS NOT NULL;
```

**Index Key Strategy** (Unified Fast Lookup):
- **CRON**: `cron_expression` (e.g., "0 9 * * MON-FRI")
- **WEBHOOK**: `webhook_path` (e.g., "/webhook/workflow-123")
- **SLACK**: `workspace_id` (e.g., "T1234567890")
- **EMAIL**: `email_filter` (e.g., "support@example.com")
- **GITHUB**: `repository` (e.g., "owner/repo-name")
- **MANUAL**: No index_key (direct workflow_id lookup)

**Two-Phase Matching**:
1. **Coarse Filtering**: Fast lookup using index_key
2. **Detailed Matching**: Apply filters from trigger_config JSONB (channels, event types, branches, paths)

### 3.4 EventRouter

**Responsibility**: Fast event routing using database indexes

**Core Routing Methods**:

1. **route_cron_event(cron_expression, timezone)**:
   - Query: `SELECT * FROM trigger_index WHERE trigger_subtype='CRON' AND index_key=?`
   - Returns: List of matching workflows

2. **route_webhook_event(path, method, headers, payload)**:
   - Query: `SELECT * FROM trigger_index WHERE trigger_subtype='WEBHOOK' AND index_key=?`
   - Additional validation: Check allowed_methods from config

3. **route_github_event(event_type, delivery_id, payload)**:
   - Extract repository from payload
   - Query: `SELECT * FROM trigger_index WHERE trigger_subtype='GITHUB' AND index_key=repository`
   - Detailed validation: Check event_config, branches, paths, actions

4. **route_slack_event(event_data)**:
   - Extract workspace_id from event
   - Query: `SELECT * FROM trigger_index WHERE trigger_subtype='SLACK' AND (index_key=workspace_id OR index_key IS NULL)`
   - Detailed validation: Check event_types, channels, users, mention_required

**Performance Optimization**:
- Database index on (trigger_subtype, index_key)
- JSONB containment operators for config filtering
- Connection pooling with async database sessions

### 3.5 BaseTrigger (Abstract Base Class)

**Responsibility**: Common trigger functionality and workflow execution interface

**Key Features**:

1. **Smart Resume Detection**:
   - Checks for paused workflow executions
   - Automatically resumes HIL workflows instead of starting new execution
   - Query: `/v2/workflows/{workflow_id}/executions` with status filter

2. **Workflow Execution**:
   - Calls workflow_engine: `POST /v2/workflows/{workflow_id}/execute`
   - Auto-resolves workflow owner user_id from database
   - Supports JWT token forwarding for authenticated execution
   - Timeout: 2 hours (for human-in-the-loop support)

3. **Jitter Calculation**:
   - Hash-based jitter for distributed execution
   - Ensures consistent but spread-out timing
   - Range: 0-30 seconds

## 4. Trigger Type Implementations

### 4.1 CronTrigger

**Technology**: Python APScheduler with AsyncIOScheduler

**Configuration**:
```json
{
  "cron_expression": "0 9 * * MON-FRI",
  "timezone": "America/New_York",
  "enabled": true
}
```

**Implementation**:
```python
class CronTrigger(BaseTrigger):
    async def start(self):
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger as APSCronTrigger

        self.scheduler = AsyncIOScheduler()
        self.scheduler.add_job(
            func=self._execute_workflow,
            trigger=APSCronTrigger.from_crontab(self.config['cron_expression']),
            timezone=self.config.get('timezone', 'UTC'),
            id=f"cron_{self.workflow_id}"
        )
        self.scheduler.start()
```

**Features**:
- Standard cron expression syntax
- Timezone support
- Hash-based jitter for load distribution
- Distributed lock prevents duplicate execution

### 4.2 ManualTrigger

**Configuration**:
```json
{
  "enabled": true,
  "require_confirmation": false
}
```

**API Endpoint**:
```
POST /api/v1/triggers/workflows/{workflow_id}/manual
Authorization: Bearer {jwt_token}
```

**Implementation**:
```python
class ManualTrigger(BaseTrigger):
    async def trigger_manual(self, user_id: str, access_token: Optional[str] = None):
        trigger_data = {
            "trigger_type": "MANUAL",
            "user_id": user_id,
            "trigger_time": datetime.now().isoformat()
        }
        return await self._trigger_workflow(trigger_data, access_token)
```

**Features**:
- Immediate execution
- User identity tracking
- JWT token forwarding
- Optional confirmation requirement

### 4.3 WebhookTrigger

**Configuration**:
```json
{
  "webhook_path": "/webhook/my-workflow",
  "allowed_methods": ["POST", "PUT"],
  "enabled": true
}
```

**Webhook URL Format**:
```
https://api.example.com/api/v1/public/webhook/{workflow_id}
https://api.example.com/api/v1/public/webhook/custom-path
```

**Implementation**:
```python
class WebhookTrigger(BaseTrigger):
    async def process_webhook(self, request_data: dict):
        trigger_data = {
            "headers": request_data["headers"],
            "body": request_data["body"],
            "query_params": request_data["query_params"],
            "method": request_data["method"],
            "path": request_data["path"]
        }
        return await self._trigger_workflow(trigger_data)
```

**Features**:
- Unique webhook path per workflow
- HTTP method filtering
- Header and query parameter capture
- Request body forwarding

### 4.4 SlackTrigger

**Configuration**:
```json
{
  "workspace_id": "T1234567890",
  "channels": ["C09D2JW6814", "C09D2JW6815"],
  "event_types": ["message", "app_mention"],
  "mention_required": false,
  "ignore_bots": true
}
```

**Auto-Resolution**:
- `workspace_id`: Auto-resolved from user's Slack OAuth token during deployment
- `channels`: Channel names converted to IDs (e.g., "general" → "C09D2JW6814")

**Event Processing**:
1. Slack platform sends event to API Gateway
2. API Gateway routes to EventRouter
3. EventRouter queries trigger_index with workspace_id
4. Detailed filtering: channels, event_types, users, mentions
5. Matching workflows triggered

**Features**:
- Multi-channel support
- Event type filtering (message, app_mention, reaction_added, etc.)
- User and bot filtering
- Mention detection
- Thread requirement support

### 4.5 GitHubTrigger

**Configuration**:
```json
{
  "github_app_installation_id": "12345678",
  "repository": "owner/repo-name",
  "event_config": {
    "push": {
      "branches": ["main", "develop"],
      "paths": ["src/**", "*.md"]
    },
    "pull_request": {
      "actions": ["opened", "synchronize"],
      "branches": ["main"]
    }
  }
}
```

**Auto-Resolution**:
- `github_app_installation_id`: Auto-resolved from user's GitHub OAuth token during deployment

**Event Processing**:
1. GitHub sends webhook to API Gateway `/api/v1/github/webhook`
2. Webhook signature verification
3. EventRouter queries trigger_index with repository name
4. Detailed filtering: event types, branches, paths, actions
5. Matching workflows triggered

**Advanced Filtering**:
- **Branch patterns**: `["main", "release/*", "feature/*"]`
- **Path patterns**: `["src/**/*.py", "docs/*.md"]`
- **Action filters**: `["opened", "synchronize", "reopened"]`
- **Author filters**: Regex patterns for commit authors

**Features**:
- GitHub App integration with installation_id
- Multi-event support (push, pull_request, issues, release, etc.)
- Complex filtering (branches, paths, actions, authors)
- Webhook event storage for debugging

### 4.6 EmailTrigger

**Configuration**:
```json
{
  "email_filter": "support@example.com",
  "folder": "INBOX",
  "mark_as_read": true,
  "check_interval": 60
}
```

**Implementation**:
```python
class EmailTrigger(BaseTrigger):
    async def start(self):
        asyncio.create_task(self._monitor_emails())

    async def _monitor_emails(self):
        while True:
            # Check for new emails via IMAP
            # Apply email_filter
            # Trigger matching workflows
            await asyncio.sleep(self.check_interval)
```

**Features**:
- IMAP-based email monitoring
- Sender, subject, content filtering
- Attachment handling
- Auto-mark as read
- Configurable check interval

## 5. Deployment Workflows

### 5.1 Workflow Deployment Flow

```mermaid
sequenceDiagram
    participant Client
    participant Gateway as API Gateway
    participant Deploy as DeploymentService
    participant TriggerMgr as TriggerManager
    participant IndexMgr as TriggerIndexManager
    participant DB as Supabase

    Client->>Gateway: POST /deployment/workflows/{id}/deploy
    Gateway->>Deploy: deploy_workflow_from_database(workflow_id)

    Deploy->>DB: Fetch workflow spec
    DB-->>Deploy: workflow_spec

    Deploy->>Deploy: validate_workflow_definition()
    Deploy->>Deploy: extract_trigger_specs()

    par Parallel Registration
        Deploy->>TriggerMgr: register_triggers(workflow_id, specs)
        Deploy->>IndexMgr: register_workflow_triggers(workflow_id, specs)
    end

    TriggerMgr->>TriggerMgr: Create trigger instances
    TriggerMgr->>TriggerMgr: Start triggers

    IndexMgr->>DB: INSERT INTO trigger_index

    Deploy->>DB: UPDATE workflows SET deployment_status='deployed'
    Deploy->>DB: INSERT INTO workflow_deployment_history

    Deploy-->>Gateway: DeploymentResult
    Gateway-->>Client: 200 OK {status: 'deployed'}
```

### 5.2 Workflow Undeployment Flow

```mermaid
sequenceDiagram
    participant Client
    participant Gateway as API Gateway
    participant Deploy as DeploymentService
    participant TriggerMgr as TriggerManager
    participant IndexMgr as TriggerIndexManager
    participant DB as Supabase

    Client->>Gateway: DELETE /deployment/workflows/{id}/undeploy
    Gateway->>Deploy: undeploy_workflow(workflow_id)

    Deploy->>DB: UPDATE deployment_status='deploying'
    Deploy->>DB: INSERT deployment_history (action='UNDEPLOY_STARTED')

    par Parallel Cleanup
        Deploy->>TriggerMgr: unregister_triggers(workflow_id)
        Deploy->>IndexMgr: unregister_workflow_triggers(workflow_id)
    end

    TriggerMgr->>TriggerMgr: Stop all triggers
    TriggerMgr->>TriggerMgr: Cleanup resources

    IndexMgr->>DB: DELETE FROM trigger_index WHERE workflow_id=?

    Deploy->>DB: UPDATE workflows SET deployment_status='undeployed'
    Deploy->>DB: INSERT deployment_history (action='UNDEPLOY_COMPLETED')

    Deploy-->>Gateway: Success
    Gateway-->>Client: 200 OK
```

### 5.3 Service Startup Trigger Restoration

```mermaid
sequenceDiagram
    participant System as System Startup
    participant Main as main.py
    participant TriggerMgr as TriggerManager
    participant DirectDB as DirectDBService
    participant DB as Supabase

    System->>Main: Start workflow_scheduler
    Main->>TriggerMgr: Initialize with DirectDBService
    Main->>TriggerMgr: restore_active_triggers()

    TriggerMgr->>DirectDB: Query trigger_index for active triggers
    DirectDB->>DB: SELECT * WHERE deployment_status='active'
    DB-->>DirectDB: Active trigger records
    DirectDB-->>TriggerMgr: List of trigger specs

    loop For each workflow
        TriggerMgr->>TriggerMgr: register_triggers(workflow_id, specs)
        TriggerMgr->>TriggerMgr: Create and start triggers
    end

    TriggerMgr-->>Main: Restoration complete {restored_count, workflows}
    Main-->>System: Service ready
```

## 6. Trigger Execution Flows

### 6.1 Cron Trigger Execution

```mermaid
sequenceDiagram
    participant Scheduler as APScheduler
    participant Cron as CronTrigger
    participant Lock as DistributedLockManager
    participant Engine as workflow_engine

    Note over Scheduler: Cron time reached

    Scheduler->>Cron: Execute job
    Cron->>Cron: calculate_jitter(workflow_id)
    Cron->>Cron: sleep(jitter_seconds)

    Cron->>Lock: acquire_lock(workflow_id)
    alt Lock acquired
        Cron->>Engine: POST /v2/workflows/{id}/execute
        Engine-->>Cron: 202 Accepted (execution_id)
        Cron->>Lock: release_lock(workflow_id)
    else Lock failed
        Note over Cron: Skip (already running)
    end
```

### 6.2 Manual Trigger Execution

```mermaid
sequenceDiagram
    participant User
    participant Gateway as API Gateway
    participant TriggerMgr as TriggerManager
    participant Manual as ManualTrigger
    participant Engine as workflow_engine

    User->>Gateway: POST /triggers/workflows/{id}/manual
    Gateway->>Gateway: Authenticate user (JWT)
    Gateway->>TriggerMgr: trigger_manual(workflow_id, user_id, token)

    TriggerMgr->>Manual: trigger_manual(user_id, token)
    Manual->>Manual: _get_workflow_owner_id()
    Manual->>Engine: POST /v2/workflows/{id}/execute
    Note over Manual,Engine: Headers: {Authorization: Bearer {token}}
    Engine-->>Manual: 202 Accepted (execution_id)
    Manual-->>TriggerMgr: ExecutionResult
    TriggerMgr-->>Gateway: ExecutionResult
    Gateway-->>User: 200 OK {execution_id, status}
```

### 6.3 Webhook Trigger Execution

```mermaid
sequenceDiagram
    participant Client as External System
    participant Gateway as API Gateway
    participant EventRouter
    participant Webhook as WebhookTrigger
    participant Engine as workflow_engine

    Client->>Gateway: POST /webhook/{workflow_id}
    Gateway->>EventRouter: route_webhook_event(path, method, headers, payload)

    EventRouter->>EventRouter: Query trigger_index (index_key=path)
    EventRouter->>EventRouter: Validate allowed_methods

    loop For each matching workflow
        EventRouter->>Webhook: process_webhook(request_data)
        Webhook->>Engine: POST /v2/workflows/{id}/execute
        Engine-->>Webhook: 202 Accepted (execution_id)
    end

    EventRouter-->>Gateway: List of results
    Gateway-->>Client: 200 OK
```

### 6.4 GitHub Webhook Execution

```mermaid
sequenceDiagram
    participant GitHub
    participant Gateway as API Gateway
    participant EventRouter
    participant GitHubTrigger
    participant Engine as workflow_engine
    participant DB as Supabase

    GitHub->>Gateway: POST /github/webhook (event payload)
    Gateway->>Gateway: verify_github_signature()
    Gateway->>EventRouter: route_github_event(event_type, payload)

    EventRouter->>DB: Query trigger_index (index_key=repository)
    DB-->>EventRouter: Candidate triggers

    EventRouter->>EventRouter: _validate_github_trigger_detailed()
    Note over EventRouter: Check: event_config, branches, paths, actions

    loop For each matching workflow
        EventRouter->>GitHubTrigger: _trigger_workflow(trigger_data)
        GitHubTrigger->>Engine: POST /v2/workflows/{id}/execute
        Engine-->>GitHubTrigger: 202 Accepted (execution_id)
    end

    EventRouter->>DB: Store webhook event (github_webhook_events)
    EventRouter-->>Gateway: Processing results
    Gateway-->>GitHub: 200 OK
```

### 6.5 Slack Event Execution

```mermaid
sequenceDiagram
    participant Slack as Slack Platform
    participant Gateway as API Gateway
    participant EventRouter
    participant SlackTrigger
    participant Engine as workflow_engine

    Slack->>Gateway: POST /slack/events (workspace event)
    Gateway->>Gateway: verify_slack_signature()
    Gateway->>EventRouter: route_slack_event(event_data)

    EventRouter->>EventRouter: Query trigger_index (index_key=workspace_id)
    EventRouter->>EventRouter: _validate_slack_trigger_detailed()
    Note over EventRouter: Check: event_types, channels, users, mentions

    loop For each matching workflow
        EventRouter->>SlackTrigger: _trigger_workflow(trigger_data)
        SlackTrigger->>SlackTrigger: _check_for_resume_opportunity()

        alt Paused execution found (HIL)
            SlackTrigger->>Engine: POST /v2/executions/{id}/resume
            Note over SlackTrigger,Engine: Resume with trigger_data as response
        else No paused execution
            SlackTrigger->>Engine: POST /v2/workflows/{id}/execute
        end

        Engine-->>SlackTrigger: 202 Accepted (execution_id)
    end

    EventRouter-->>Gateway: Processing results
    Gateway-->>Slack: 200 OK
```

## 7. Human-in-the-Loop (HIL) Integration

### 7.1 HIL Workflow Resume Pattern

The workflow_scheduler implements intelligent resume detection for Human-in-the-Loop workflows:

**Smart Resume Logic**:
1. When trigger fires (e.g., Slack message received)
2. Check for paused executions of the workflow
3. If paused execution exists, resume it with trigger data as human response
4. Otherwise, start new execution

**Resume Detection Implementation**:
```python
async def _check_for_resume_opportunity(self, trigger_data: dict) -> dict:
    # Query workflow_engine for paused executions
    engine_url = f"{settings.workflow_engine_url}/v2/workflows/{self.workflow_id}/executions"
    response = await client.get(engine_url)

    executions = response.json().get("workflows", [])
    paused_executions = [e for e in executions if e["status"] == "PAUSED"]

    if paused_executions:
        most_recent = max(paused_executions, key=lambda x: x["started_at"])
        return {
            "should_resume": True,
            "execution_id": most_recent["execution_id"]
        }
    return {"should_resume": False}
```

**Resume Execution**:
```python
async def _resume_paused_workflow(self, execution_id: str, trigger_data: dict):
    engine_url = f"{settings.workflow_engine_url}/v2/executions/{execution_id}/resume"
    resume_payload = {
        "resume_data": trigger_data,
        "interaction_id": trigger_data.get("interaction_id")
    }
    response = await self._client.post(engine_url, json=resume_payload)
```

### 7.2 HIL Use Cases

**Slack HIL Workflow**:
1. Workflow pauses at HIL node
2. HIL node sends Slack message: "Please approve this deployment"
3. User responds in Slack: "approved"
4. Slack event triggers workflow
5. Scheduler detects paused execution and resumes with response
6. Workflow continues with approval

**Email HIL Workflow**:
1. Workflow pauses at HIL node
2. HIL node sends email: "Review this document"
3. User replies to email
4. Email trigger fires
5. Scheduler resumes paused workflow with email content

## 8. Configuration & Environment

### 8.1 Environment Variables

```bash
# Core Service
PORT="8003"
HOST="0.0.0.0"
DEBUG="false"

# External Services
WORKFLOW_ENGINE_URL="http://workflow-engine:8002"
API_GATEWAY_URL="http://api-gateway:8000"

# Database
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_SECRET_KEY="service-role-key"
SUPABASE_PUB_KEY="anon-key"

# Redis
REDIS_URL="redis://localhost:6379/1"

# APScheduler
SCHEDULER_TIMEZONE="UTC"
SCHEDULER_MAX_WORKERS="10"

# GitHub Integration
GITHUB_APP_ID="123456"
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
GITHUB_WEBHOOK_SECRET="webhook-secret"
GITHUB_CLIENT_ID="github-oauth-client-id"

# Slack Integration
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CLIENT_ID="slack-client-id"
SLACK_CLIENT_SECRET="slack-client-secret"
SLACK_SIGNING_SECRET="slack-signing-secret"

# Google OAuth
GOOGLE_CLIENT_ID="google-client-id"
GOOGLE_CLIENT_SECRET="google-client-secret"

# Distributed Locks
LOCK_TIMEOUT="300"
LOCK_RETRY_DELAY="0.1"

# Logging
LOG_LEVEL="INFO"
LOG_FORMAT="text"
```

### 8.2 Service Configuration (core/config.py)

```python
class Settings(BaseSettings):
    service_name: str = "workflow_scheduler"
    host: str = "0.0.0.0"
    port: int = 8003
    debug: bool = False

    workflow_engine_url: str = "http://localhost:8002"
    api_gateway_url: str = "http://localhost:8000"

    supabase_url: str = ""
    supabase_secret_key: str = ""

    redis_url: str = "redis://localhost:6379/1"

    scheduler_timezone: str = "UTC"
    scheduler_max_workers: int = 10
```

## 9. Database Schema

### 9.1 trigger_index Table

```sql
CREATE TABLE trigger_index (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    trigger_type TEXT NOT NULL,
    trigger_subtype TEXT NOT NULL,
    trigger_config JSONB NOT NULL,
    index_key TEXT,
    deployment_status TEXT DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT trigger_index_deployment_status_check
        CHECK (deployment_status IN ('active', 'inactive', 'pending', 'failed'))
);

CREATE INDEX idx_trigger_index_key
    ON trigger_index(trigger_subtype, index_key)
    WHERE index_key IS NOT NULL;

CREATE INDEX idx_trigger_index_lookup
    ON trigger_index(trigger_subtype, index_key, deployment_status)
    WHERE index_key IS NOT NULL;
```

### 9.2 github_webhook_events Table

```sql
CREATE TABLE github_webhook_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    delivery_id TEXT UNIQUE NOT NULL,
    event_type TEXT NOT NULL,
    installation_id BIGINT,
    repository_id BIGINT,
    payload JSONB,
    processed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_github_webhook_events_delivery
    ON github_webhook_events(delivery_id);

CREATE INDEX idx_github_webhook_events_repo
    ON github_webhook_events(repository_id, event_type);
```

### 9.3 github_installations Table

```sql
CREATE TABLE github_installations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    installation_id BIGINT UNIQUE NOT NULL,
    account_id BIGINT NOT NULL,
    account_login TEXT NOT NULL,
    account_type TEXT NOT NULL,
    repositories JSONB,
    permissions JSONB,
    access_token_expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_github_installations_user
    ON github_installations(user_id);
```

## 10. Monitoring & Observability

### 10.1 Health Check Endpoints

```python
@app.get("/health")
async def health_check():
    # Check TriggerManager initialization
    # Quick Redis connectivity test (2s timeout)
    return {"service": "workflow_scheduler", "status": "healthy"}

@app.get("/health/detailed")
async def detailed_health_check():
    # Check lock_manager (Redis)
    # Check trigger_manager (active triggers)
    return {
        "service": "workflow_scheduler",
        "status": "healthy",
        "components": {
            "lock_manager": "healthy",
            "trigger_manager": {...}
        }
    }
```

### 10.2 Metrics Endpoint

```python
@app.get("/metrics")
async def get_metrics():
    return {
        "service": "workflow_scheduler",
        "total_workflows": 10,
        "total_triggers": 25,
        "trigger_types": {
            "CRON": 5,
            "SLACK": 8,
            "GITHUB": 7,
            "MANUAL": 5
        }
    }
```

### 10.3 Key Metrics

- **Deployment Metrics**:
  - Total deployed workflows
  - Deployment success/failure rate
  - Average deployment time

- **Trigger Metrics**:
  - Active triggers by type
  - Trigger execution count
  - Trigger execution latency
  - Failed trigger executions

- **Event Router Metrics**:
  - Event routing latency
  - Matching workflow count per event
  - Database query performance

- **System Metrics**:
  - Redis connection status
  - Database connection pool status
  - Memory usage
  - CPU usage

### 10.4 OpenTelemetry Integration

```python
# Automatic tracing for all HTTP requests
app.add_middleware(TrackingMiddleware)
app.add_middleware(MetricsMiddleware, service_name="workflow-scheduler")

# OTLP endpoint configuration
environment = os.getenv("ENVIRONMENT", "development")
if environment in ["production", "staging"]:
    otlp_endpoint = "http://localhost:4317"  # AWS OTEL Collector sidecar
else:
    otlp_endpoint = "http://otel-collector:4317"  # Docker Compose
```

## 11. Security Considerations

### 11.1 Authentication & Authorization

- **Internal API**: Service-to-service authentication via API Gateway
- **OAuth Integrations**: User-specific OAuth tokens stored in oauth_tokens table
- **GitHub Webhooks**: Signature verification using GITHUB_WEBHOOK_SECRET
- **Slack Events**: Signature verification using SLACK_SIGNING_SECRET
- **Manual Triggers**: JWT token authentication and forwarding

### 11.2 Data Security

- **Sensitive Configuration**: Encrypted storage in Supabase
- **OAuth Tokens**: Stored with encryption in oauth_tokens table
- **Environment Secrets**: AWS SSM Parameters for production
- **Network Security**: VPC isolation, security groups, TLS encryption

### 11.3 Rate Limiting & Abuse Prevention

- **Distributed Locks**: Prevent duplicate cron executions
- **Jitter**: Spread out concurrent executions
- **Timeout Configuration**: 2-hour timeout for HIL workflows
- **Event Deduplication**: Track processed webhook delivery IDs

## 12. Development & Deployment

### 12.1 Development Commands

```bash
# Install dependencies
cd apps/backend/workflow_scheduler
uv sync

# Run service locally
python -m workflow_scheduler.main

# Run tests
pytest tests/

# Test trigger system
python test_trigger_system.py
```

### 12.2 Docker Deployment

```bash
# Build for AWS ECS (AMD64)
docker build --platform linux/amd64 \
  -f apps/backend/workflow_scheduler/Dockerfile \
  -t workflow-scheduler .

# Run with Docker Compose
cd apps/backend
docker-compose up workflow-scheduler
```

### 12.3 Project Structure

```
workflow_scheduler/
├── main.py                          # FastAPI app entry point
├── core/
│   ├── config.py                   # Configuration management
│   ├── database.py                 # Database connections
│   └── supabase_client.py          # Supabase client
├── api/
│   ├── deployment.py               # Deployment endpoints
│   ├── triggers.py                 # Trigger management endpoints
│   ├── github.py                   # GitHub webhook handler
│   ├── slack.py                    # Slack event handler
│   ├── google_calendar.py          # Google Calendar integration
│   └── auth.py                     # OAuth callbacks
├── services/
│   ├── deployment_service.py       # Deployment orchestration
│   ├── trigger_manager.py          # Trigger lifecycle management
│   ├── trigger_index_manager.py    # Database indexing
│   ├── event_router.py             # Fast event routing
│   ├── lock_manager.py             # Distributed locking
│   ├── notification_service.py     # Notifications
│   └── direct_db_service.py        # Direct database access
├── triggers/
│   ├── base.py                     # BaseTrigger abstract class
│   ├── cron_trigger.py             # Cron implementation
│   ├── manual_trigger.py           # Manual implementation
│   ├── webhook_trigger.py          # Webhook implementation
│   ├── slack_trigger.py            # Slack implementation
│   ├── github_trigger.py           # GitHub implementation
│   └── email_trigger.py            # Email implementation
├── dependencies.py                  # FastAPI dependency injection
├── tests/                          # Unit tests
└── pyproject.toml                  # Python project config
```

## 13. Key Design Decisions

### 13.1 Unified Index Key Design

**Decision**: Use single `index_key` column for all trigger types instead of type-specific columns

**Rationale**:
- Simplifies database schema
- Reduces index maintenance
- Supports future trigger types without schema changes
- Enables consistent query patterns

**Trade-offs**:
- Requires type-specific index_key calculation logic
- JSONB config required for detailed filtering

### 13.2 Two-Phase Matching

**Decision**: Coarse filtering with index_key, detailed filtering with trigger_config

**Rationale**:
- Fast initial filtering using database indexes
- Flexible detailed filtering without schema changes
- Supports complex trigger configurations

**Trade-offs**:
- Additional CPU overhead for detailed matching
- Cannot index all filter criteria

### 13.3 In-Memory + Database Hybrid

**Decision**: Active triggers in memory (TriggerManager) + persistent index (TriggerIndexManager)

**Rationale**:
- Fast trigger execution without database queries
- Persistent state for service restarts
- Enables fast event routing via database indexes

**Trade-offs**:
- Memory usage scales with number of workflows
- Requires restoration on service startup

### 13.4 Auto-Resolution of Integration Credentials

**Decision**: Automatically resolve OAuth credentials during deployment

**Rationale**:
- Simplified user experience (no manual credential entry)
- Ensures credentials are up-to-date
- Reduces configuration errors

**Implementation**:
- GitHub: Resolve installation_id from oauth_tokens
- Slack: Resolve workspace_id and channel IDs from oauth_tokens

### 13.5 Smart HIL Resume Detection

**Decision**: Automatically detect and resume paused workflows on trigger

**Rationale**:
- Enables seamless HIL user experience
- Avoids duplicate workflow executions
- Supports conversational workflows

**Trade-offs**:
- Additional latency for paused execution check
- Complexity in matching trigger to paused execution

## 14. Future Enhancements

### 14.1 Performance Optimizations

- Redis caching for frequently matched triggers
- Pre-computed filter indexes for complex queries
- Batch event processing for high-volume triggers
- Connection pooling optimization

### 14.2 Feature Additions

- Trigger condition expressions (e.g., "time == 9am AND day == Monday")
- Trigger dependencies (e.g., "trigger A must complete before trigger B")
- Trigger rate limiting per workflow
- Advanced HIL matching (context-aware resume)
- Trigger execution history and analytics

### 14.3 Scalability

- Multi-region deployment support
- Horizontal scaling with leader election
- Trigger sharding by workflow_id
- Event queue for high-volume processing

## Appendices

### A. Glossary

- **Trigger**: Condition that initiates workflow execution
- **Deployment**: Process of activating workflow and its triggers
- **Index Key**: Fast lookup field for trigger matching
- **Event Router**: Service for matching events to workflows
- **HIL**: Human-in-the-Loop, workflows requiring human interaction
- **Jitter**: Random delay to distribute execution load
- **Distributed Lock**: Redis-based lock to prevent duplicate execution

### B. References

- Workflow Specification: `docs/tech-design/new_workflow_spec.md`
- Node Specifications: `shared/node_specs/`
- API Gateway Documentation: `apps/backend/api-gateway/docs/`
- Supabase Migrations: `supabase/migrations/`
- CLAUDE.md: `apps/backend/CLAUDE.md`
