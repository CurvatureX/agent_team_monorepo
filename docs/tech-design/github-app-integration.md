# GitHub App Integration Architecture

## Overview

This document outlines the technical design for a centralized GitHub App that enables users to connect their repositories (including private ones) to our AI workflow system. The GitHub App will handle webhook events, provide secure access to repository data, and enable workflow triggers based on GitHub activities.

## Architecture Components

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   GitHub App    │────▶│   API Gateway    │────▶│ Workflow         │────▶│ Workflow Engine  │
│   (Webhooks)    │     │ (Event Reception)│     │ Scheduler        │     │   (Execution)    │
└─────────────────┘     └──────────────────┘     └──────────────────┘     └──────────────────┘
        │                        │                        │                        │
        │                        │                        │                        │
        ▼                        ▼                        ▼                        ▼
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   GitHub API    │     │    Supabase      │     │   Trigger Match  │     │   User Workflows │
│ (Code Access)   │     │ (Auth & State)   │     │   & Filtering    │     │   (Triggered)    │
└─────────────────┘     └──────────────────┘     └──────────────────┘     └──────────────────┘
```

**Flow Description:**
1. **GitHub App** receives webhook events from repositories
2. **API Gateway** handles webhook reception, authentication, and signature verification
3. **Workflow Scheduler** checks if any workflows have matching GitHub triggers
4. **Workflow Engine** executes triggered workflows with repository context

## 1. GitHub App Registration & Setup

### Step 1: Register GitHub App

**Navigate to GitHub Settings:**
1. Go to `https://github.com/settings/apps`
2. Click "New GitHub App"

**App Configuration:**
```yaml
App Name: "AI Workflow Teams"
Description: "Connect your repositories to AI-powered workflow automation"
Homepage URL: "https://aiworkflowteams.com"
Callback URL: "https://api.aiworkflowteams.com/api/v1/public/webhooks/github/auth"
Webhook URL: "https://api.aiworkflowteams.com/webhooks/github"
Webhook Secret: "generate_secure_random_string_here"
```

**Public/Private Settings:**
- ✅ **Public** - Allow anyone to install (required for public distribution)
- ✅ **Allow installation on any account** - Users and Organizations

### Step 2: Configure Permissions & Events

### App Permissions Required

**Repository Permissions:**
- `contents: read` - Access repository files and diffs
- `metadata: read` - Basic repository information
- `pull_requests: read` - PR data and comments
- `issues: read` - Issue data and comments
- `actions: read` - Workflow run information
- `deployments: read` - Deployment status

**Organization Permissions:**
- `members: read` - Organization member information (optional)

**Webhook Events:**
- `push`, `pull_request`, `pull_request_review`
- `issues`, `issue_comment`, `release`
- `deployment`, `deployment_status`
- `workflow_run`, `check_run`, `check_suite`

### Step 3: Generate Private Key & Credentials

**After App Creation:**
1. **Generate Private Key**: Click "Generate a private key" - download and store securely
2. **Note App ID**: Found at top of app settings page
3. **Save Webhook Secret**: Used for signature verification
4. **Client ID & Secret**: For OAuth flow (if needed)

**Security Best Practices:**
- Store private key in secure environment variables or secret manager
- Use different webhook secrets for staging/production
- Enable webhook signature verification
- Regularly rotate credentials

### Step 4: Development & Testing (Before Public Release)

**Private App Testing Setup:**
```yaml
# Development App Configuration (Private)
App Name: "AI Workflow Teams (Dev)"
Description: "Development version for testing GitHub integration"
Homepage URL: "https://dev-api.aiworkflowteams.com"
Callback URL: "https://dev-api.aiworkflowteams.com/api/v1/public/webhooks/github/auth"
Webhook URL: "https://dev-api.aiworkflowteams.com/webhooks/github"
Webhook Secret: "dev_webhook_secret_here"

# Privacy Settings for Development
- ❌ **Private** - Only you can install (for testing)
- ✅ **Allow installation on personal account only** (initially)
```

**Testing Workflow:**

1. **Create Development App:**
   ```bash
   # Create separate dev app at https://github.com/settings/apps
   # Use different webhook URLs and secrets for dev environment
   ```

2. **Install on Personal Repositories:**
   ```bash
   # Install your dev app on test repositories
   # Direct installation URL: https://github.com/apps/ai-workflow-teams-dev/installations/new
   ```

3. **Test Webhook Reception:**
   ```python
   # Test webhook endpoint with ngrok for local development
   pip install pyngrok
   ngrok http 8000

   # Update GitHub App webhook URL to ngrok URL
   # Example: https://abc123.ngrok.io/webhooks/github
   ```

4. **Verify Event Processing:**
   ```bash
   # Monitor logs for webhook events
   tail -f logs/github-webhooks.log

   # Test different GitHub events:
   # - Create a PR in test repo
   # - Push commits
   # - Add comments
   # - Close/reopen issues
   ```

5. **Test Repository Access:**
   ```python
   # Test GitHub API access with installation token
   async def test_github_access():
       client = GitHubSDK(app_id, private_key)

       # Test getting installation token
       token = await client.get_installation_token(installation_id)

       # Test repository operations
       repos = await client.list_repositories(installation_id)
       pr_data = await client.get_pull_request(installation_id, "owner/repo", 1)

       print(f"Successfully accessed {len(repos)} repositories")
   ```

6. **Test Workflow Triggers:**
   ```bash
   # Create test workflows with GitHub triggers
   # Verify they execute when GitHub events occur
   # Check workflow execution logs
   ```

**Testing Checklist:**
- [ ] Webhook signature verification works
- [ ] Installation tokens are correctly generated
- [ ] Repository data can be accessed (private repos)
- [ ] Workflow triggers activate on GitHub events
- [ ] Filtering (branches, paths, actions) works correctly
- [ ] Rate limiting doesn't cause issues
- [ ] Error handling works for invalid events

### Step 5: App Distribution & Discovery

**GitHub Marketplace (After Testing):**
1. **Prepare for Marketplace**: Complete app description, screenshots, pricing
2. **Submit for Review**: GitHub reviews public apps for quality/security
3. **App Store Listing**: Users can discover and install from GitHub Marketplace

**Direct Installation URL:**
- `https://github.com/apps/ai-workflow-teams/installations/new`
- Can be embedded in your application for direct installation

### Installation Flow

1. **User initiates connection** via our frontend
2. **OAuth redirect** to GitHub App installation page: `https://github.com/apps/{APP_NAME}/installations/new?state=<user_id>`
3. **User selects repositories** to grant access
4. **GitHub redirects back** with installation data: `/api/v1/public/webhooks/github/auth?installation_id=12345&setup_action=install&state=<user_id>`
5. **We store installation mapping** in existing Supabase OAuth infrastructure

#### Database Schema (Implementation)

We leverage the existing OAuth infrastructure instead of creating separate GitHub tables:

```sql
-- Existing integrations table (stores GitHub app configuration)
-- Already exists - we create a GitHub integration entry
INSERT INTO integrations (
    integration_id, integration_type, name, description, version,
    configuration, supported_operations, required_scopes
) VALUES (
    'github_app', 'github', 'GitHub App Integration',
    'GitHub App for repository access and automation', '1.0',
    '{"app_name": "agent-team-monorepo", "callback_url": "/api/v1/public/webhooks/github/auth"}',
    ARRAY['repositories:read', 'repositories:write', 'issues:read', 'actions:read'],
    ARRAY['repo', 'issues', 'actions']
);

-- Existing oauth_tokens table (stores user installation mappings)
-- We store GitHub installations as OAuth tokens with:
-- - integration_id: 'github_app'
-- - provider: 'github'
-- - access_token: placeholder (will be replaced with actual installation token)
-- - credential_data: JSON containing installation_id and setup_action
-- - user_id: links installation to specific user
```

#### Installation Data Storage

**Credential Data Structure:**
```json
{
  "installation_id": "12345",
  "setup_action": "install",
  "callback_timestamp": "2025-01-13T10:30:00Z"
}
```

**Benefits of Existing Schema:**
- ✅ **Unified OAuth Management**: All integrations (GitHub, Slack, etc.) in one system
- ✅ **User Association**: Direct link between users and their integrations
- ✅ **Generic API**: `/api/v1/app/integrations` works for all providers
- ✅ **Authentication**: Proper JWT-based access control
- ✅ **Audit Trail**: Track when integrations are created/revoked

#### API Endpoints (Implementation)

**Public API (No Authentication Required):**
```bash
# GitHub App installation callback (handles redirect from GitHub)
GET /api/v1/public/webhooks/github/auth?installation_id=12345&setup_action=install&state=<user_id>
# - Stores installation data in database
# - Forwards to workflow_scheduler for additional processing
# - Returns success response with installation details
```

**App API (Requires JWT Authentication):**
```bash
# Get all user integrations (GitHub, Slack, etc.)
GET /api/v1/app/integrations
Authorization: Bearer <jwt_token>
# Returns: { "integrations": [...], "total_count": 2 }

# Get GitHub integrations only
GET /api/v1/app/integrations/github
Authorization: Bearer <jwt_token>
# Returns: GitHub installations for authenticated user

# Revoke specific integration
DELETE /api/v1/app/integrations/{integration_token_id}
Authorization: Bearer <jwt_token>
# Marks integration as inactive (soft delete)
```

**Example Response:**
```json
{
  "success": true,
  "user_id": "user-123",
  "integrations": [
    {
      "id": "token-abc-123",
      "integration_id": "github_app",
      "provider": "github",
      "integration_type": "github",
      "name": "GitHub App Integration",
      "is_active": true,
      "created_at": "2025-01-13T10:30:00Z",
      "credential_data": {
        "installation_id": "12345",
        "setup_action": "install"
      }
    }
  ],
  "total_count": 1
}
```

## 2. Webhook Event Processing

### Step 1: API Gateway Event Reception

```python
# API Gateway webhook endpoint (Implementation)
@router.post("/webhooks/github")
async def github_webhook(
    request: Request,
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_github_delivery: str = Header(..., alias="X-GitHub-Delivery"),
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
):
    """
    GitHub webhook endpoint - handles GitHub App webhooks and routes them to workflow_scheduler
    """
    # 1. Verify webhook signature if secret is configured
    payload = await request.body()
    if hasattr(settings, "GITHUB_WEBHOOK_SECRET") and settings.GITHUB_WEBHOOK_SECRET:
        if not x_hub_signature_256 or not _verify_github_signature(
            payload, x_hub_signature_256, settings.GITHUB_WEBHOOK_SECRET
        ):
            raise HTTPException(status_code=401, detail="Invalid signature")

    # 2. Parse JSON payload
    event_data = json.loads(payload.decode())

    # 3. Extract repository and installation info
    installation_id = event_data.get("installation", {}).get("id")
    repository = event_data.get("repository", {})
    repo_name = repository.get("full_name", "unknown")

    # 4. Forward to workflow_scheduler GitHub webhook handler
    scheduler_url = f"{settings.workflow_scheduler_http_url}/api/v1/triggers/github/events"

    github_webhook_data = {
        "event_type": x_github_event,
        "delivery_id": x_github_delivery,
        "payload": event_data,
        "installation_id": installation_id,
        "repository_name": repo_name,
        "timestamp": event_data.get("timestamp")
    }

    async with httpx.AsyncClient() as client:
        scheduler_response = await client.post(scheduler_url, json=github_webhook_data, timeout=30.0)

        if scheduler_response.status_code == 200:
            result = scheduler_response.json()
            return {
                "status": "received",
                "message": "GitHub webhook processed successfully",
                "event_type": x_github_event,
                "delivery_id": x_github_delivery,
                "repository": repo_name,
                "installation_id": installation_id,
                "processed_workflows": result.get("processed_workflows", 0),
                "results": result.get("results", []),
            }

# GitHub App installation callback (Implementation)
@router.get("/webhooks/github/auth")
async def github_oauth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    installation_id: Optional[str] = None,
    setup_action: Optional[str] = None,
    error: Optional[str] = None,
):
    """
    GitHub OAuth callback endpoint - handles GitHub App installation OAuth flow
    """
    # Handle app installation flow
    if setup_action in ["install", "update"]:
        # Store installation data in database if user_id is provided in state
        if state and installation_id:
            db_store_success = await _store_github_installation(state, installation_id, setup_action)

        # Forward to workflow_scheduler to handle the installation
        scheduler_url = f"{settings.workflow_scheduler_http_url}/api/v1/auth/github/callback"

        installation_data = {
            "installation_id": int(installation_id),
            "setup_action": setup_action,
            "state": state,
            "code": code,
        }

        # Process with workflow_scheduler and return response
        # Returns installation details including account info and repositories
```

### Step 2: Forward to Workflow Scheduler

```python
async def forward_to_workflow_scheduler(event_type: str, delivery_id: str, payload: dict):
    """Forward GitHub webhook to Workflow Scheduler service"""

    scheduler_payload = {
        "trigger_type": "github",
        "event_type": event_type,
        "delivery_id": delivery_id,
        "github_payload": payload,
        "timestamp": datetime.utcnow().isoformat()
    }

    # Call Workflow Scheduler API
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{WORKFLOW_SCHEDULER_URL}/triggers/github",
            json=scheduler_payload,
            headers={"Authorization": f"Bearer {INTERNAL_SERVICE_TOKEN}"}
        )

        if response.status_code != 200:
            logger.error(f"Failed to forward to scheduler: {response.text}")
            raise HTTPException(500, "Failed to process webhook")
```

### Step 3: Workflow Scheduler Processing

```python
# In Workflow Scheduler service
@app.post("/triggers/github")
async def handle_github_trigger(trigger_request: GitHubTriggerRequest):
    """Process GitHub webhook and check for matching workflow triggers"""

    # 1. Extract installation and repository info
    payload = trigger_request.github_payload
    installation_id = payload.get("installation", {}).get("id")
    repository = payload.get("repository", {})

    # 2. Find workflows with matching GitHub triggers
    matching_workflows = await find_workflows_with_github_triggers(
        installation_id=installation_id,
        repository_name=repository["full_name"],
        event_type=trigger_request.event_type,
        payload=payload
    )

    # 3. For each matching workflow, invoke Workflow Engine
    for workflow in matching_workflows:
        await invoke_workflow_engine(workflow, trigger_request)

async def find_workflows_with_github_triggers(
    installation_id: int,
    repository_name: str,
    event_type: str,
    payload: dict
) -> List[WorkflowDefinition]:
    """Find workflows that have GitHub triggers matching this event"""

    # Query database for workflows with GitHub triggers
    workflows = await db.execute("""
        SELECT w.*, t.trigger_config
        FROM workflows w
        JOIN workflow_triggers t ON w.id = t.workflow_id
        WHERE t.trigger_type = 'TRIGGER_GITHUB'
        AND JSON_EXTRACT(t.trigger_config, '$.repository') = ?
        AND JSON_EXTRACT(t.trigger_config, '$.events') LIKE ?
    """, [repository_name, f'%{event_type}%'])

    matching_workflows = []

    for workflow_row in workflows:
        trigger_config = json.loads(workflow_row.trigger_config)

        # Apply filters (branches, paths, actions, authors, labels)
        if await matches_github_filters(trigger_config, payload):
            matching_workflows.append(WorkflowDefinition.from_row(workflow_row))

    return matching_workflows

async def matches_github_filters(trigger_config: dict, payload: dict) -> bool:
    """Check if GitHub event matches all configured filters"""

    # Branch filter
    if trigger_config.get("branches"):
        if not matches_branch_filter(trigger_config["branches"], payload):
            return False

    # Path filter
    if trigger_config.get("paths"):
        if not matches_path_filter(trigger_config["paths"], payload):
            return False

    # Action filter (for PR/issue events)
    if trigger_config.get("action_filter"):
        action = payload.get("action")
        if action not in trigger_config["action_filter"]:
            return False

    # Author filter
    if trigger_config.get("author_filter"):
        if not matches_author_filter(trigger_config["author_filter"], payload):
            return False

    # Label filter (for PR/issue events)
    if trigger_config.get("label_filter"):
        if not matches_label_filter(trigger_config["label_filter"], payload):
            return False

    # Bot filter
    if trigger_config.get("ignore_bots", True):
        sender = payload.get("sender", {})
        if sender.get("type") == "Bot":
            return False

    return True
```

### Step 4: Invoke Workflow Engine

```python
async def invoke_workflow_engine(workflow: WorkflowDefinition, trigger_request: GitHubTriggerRequest):
    """Invoke Workflow Engine to execute the workflow"""

    # Prepare workflow execution context with GitHub data
    execution_context = {
        "workflow_id": workflow.id,
        "trigger_type": "github",
        "trigger_data": {
            "event": trigger_request.event_type,
            "action": trigger_request.github_payload.get("action"),
            "repository": trigger_request.github_payload.get("repository"),
            "sender": trigger_request.github_payload.get("sender"),
            "payload": trigger_request.github_payload,
            "timestamp": trigger_request.timestamp,
            "delivery_id": trigger_request.delivery_id
        }
    }

    # Call Workflow Engine
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{WORKFLOW_ENGINE_URL}/workflows/execute",
            json={
                "workflow_definition": workflow.to_dict(),
                "execution_context": execution_context,
                "priority": "normal"
            },
            headers={"Authorization": f"Bearer {INTERNAL_SERVICE_TOKEN}"}
        )

        if response.status_code == 200:
            execution_result = response.json()
            logger.info(f"Workflow {workflow.id} triggered successfully: {execution_result['execution_id']}")
        else:
            logger.error(f"Failed to execute workflow {workflow.id}: {response.text}")
```

## 3. Repository Data Access

### GitHub API Client

```python
class GitHubAppClient:
    def __init__(self, app_id: str, private_key: str):
        self.app_id = app_id
        self.private_key = private_key

    async def get_installation_token(self, installation_id: int) -> str:
        """Get short-lived access token for installation"""
        jwt_token = self.generate_jwt()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.github.com/app/installations/{installation_id}/access_tokens",
                headers={
                    "Authorization": f"Bearer {jwt_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            return response.json()["token"]

    async def get_pull_request_diff(self, installation_id: int, repo: str, pr_number: int) -> str:
        """Get PR diff content"""
        token = await self.get_installation_token(installation_id)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/repos/{repo}/pulls/{pr_number}",
                headers={
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github.v3.diff"
                }
            )
            return response.text

    async def get_file_content(self, installation_id: int, repo: str, path: str, ref: str = "main") -> str:
        """Get specific file content"""
        token = await self.get_installation_token(installation_id)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/repos/{repo}/contents/{path}",
                headers={
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                params={"ref": ref}
            )

            content_data = response.json()
            if content_data["encoding"] == "base64":
                return base64.b64decode(content_data["content"]).decode("utf-8")
            return content_data["content"]
```

### Repository Context Service

```python
class GitHubRepositoryService:
    """Service for accessing repository data through GitHub App"""

    async def get_pr_context(self, installation_id: int, repo: str, pr_number: int) -> dict:
        """Get comprehensive PR context for workflow"""
        client = GitHubAppClient(app_id, private_key)

        # Get PR details
        pr_data = await client.get_pull_request(installation_id, repo, pr_number)

        # Get diff
        diff_content = await client.get_pull_request_diff(installation_id, repo, pr_number)

        # Get changed files
        changed_files = await client.get_pull_request_files(installation_id, repo, pr_number)

        # Get comments if needed
        comments = await client.get_pull_request_comments(installation_id, repo, pr_number)

        return {
            "pr": pr_data,
            "diff": diff_content,
            "files": changed_files,
            "comments": comments,
            "repository": await client.get_repository(installation_id, repo)
        }

    async def get_commit_context(self, installation_id: int, repo: str, commit_sha: str) -> dict:
        """Get commit context for push events"""
        client = GitHubAppClient(app_id, private_key)

        commit_data = await client.get_commit(installation_id, repo, commit_sha)

        return {
            "commit": commit_data,
            "diff": commit_data["files"],  # GitHub API includes diff in commit
            "repository": await client.get_repository(installation_id, repo)
        }
```

### GitHub SDK Implementation

**Location:** `apps/backend/shared/sdks/github_sdk/`

The GitHub SDK provides a comprehensive interface for all GitHub App operations, including repository management, PR/issue operations, and code manipulation.

**SDK Structure:**
```
github_sdk/
├── __init__.py
├── client.py          # Main GitHub SDK client
├── auth.py           # JWT and token management
├── repositories.py   # Repository operations
├── pulls.py          # Pull request operations
├── issues.py         # Issue operations
├── branches.py       # Branch and code operations
├── webhooks.py       # Webhook utilities
├── exceptions.py     # Custom exceptions
├── models.py         # Data models
├── requirements.txt  # Dependencies
└── README.md        # Usage documentation
```

## 4. Workflow Integration

### Enhanced GitHub Trigger Node

```python
class GitHubTriggerNode:
    """Enhanced trigger node with repository access capabilities"""

    async def execute(self, context: WorkflowContext) -> dict:
        # Standard trigger execution
        trigger_data = await super().execute(context)

        # Enhanced with repository access
        installation_id = self.parameters["github_app_installation_id"]

        if trigger_data["event"] == "pull_request":
            pr_context = await self.github_service.get_pr_context(
                installation_id,
                trigger_data["repository"]["full_name"],
                trigger_data["payload"]["number"]
            )
            trigger_data["pr_context"] = pr_context

        elif trigger_data["event"] == "push":
            # Get commit contexts for all commits in push
            commit_contexts = []
            for commit in trigger_data["payload"]["commits"]:
                commit_context = await self.github_service.get_commit_context(
                    installation_id,
                    trigger_data["repository"]["full_name"],
                    commit["id"]
                )
                commit_contexts.append(commit_context)
            trigger_data["commit_contexts"] = commit_contexts

        return trigger_data
```

### GitHub Action Nodes

Create specialized nodes for GitHub operations:

```python
# Get PR Code Node
class GitHubGetPRCodeNode:
    async def execute(self, input_data: dict) -> dict:
        installation_id = self.parameters["installation_id"]
        repo = self.parameters["repository"]
        pr_number = input_data.get("pr_number") or self.parameters["pr_number"]

        pr_context = await self.github_service.get_pr_context(
            installation_id, repo, pr_number
        )

        return {
            "pr_data": pr_context["pr"],
            "diff": pr_context["diff"],
            "files": pr_context["files"],
            "comments": pr_context["comments"]
        }

# Create PR Comment Node
class GitHubCreateCommentNode:
    async def execute(self, input_data: dict) -> dict:
        installation_id = self.parameters["installation_id"]
        repo = self.parameters["repository"]
        pr_number = input_data["pr_number"]
        comment_body = input_data["comment"]

        await self.github_service.create_pr_comment(
            installation_id, repo, pr_number, comment_body
        )

        return {"success": True, "comment_created": True}
```

## 5. Security Considerations

### Webhook Security

1. **Signature Verification**: Always verify GitHub webhook signatures
2. **Rate Limiting**: Implement rate limiting on webhook endpoints
3. **IP Allowlisting**: Restrict to GitHub's webhook IP ranges

### Access Token Management

1. **Short-lived Tokens**: Use installation tokens (1 hour expiry)
2. **Minimal Permissions**: Request only necessary permissions
3. **Token Rotation**: Automatic rotation of installation tokens

### Data Privacy

1. **Selective Access**: Users control which repositories to connect
2. **Data Retention**: Clear policies on webhook payload storage
3. **Encryption**: Encrypt sensitive data at rest

## 6. Implementation Status & Plan

### ✅ **Phase 1: Core Infrastructure (COMPLETED)**
1. ✅ **GitHub App Registration**: App configuration and credentials management
2. ✅ **Webhook Reception**: `/api/v1/public/webhooks/github` endpoint with signature verification
3. ✅ **Installation Flow**: `/api/v1/public/webhooks/github/auth` callback with database storage
4. ✅ **Database Schema**: Using existing `oauth_tokens` and `integrations` tables
5. ✅ **User Management API**: Generic `/api/v1/app/integrations` endpoints

**Key Implementation Details:**
- **Database**: Leverages existing OAuth infrastructure instead of separate GitHub tables
- **API Design**: Generic integrations API supports GitHub, Slack, and future providers
- **Authentication**: Proper JWT-based access control for user data
- **Dual Processing**: Stores in database AND forwards to workflow_scheduler
- **Error Handling**: Graceful failure handling with detailed logging

### 🔄 **Phase 2: Event Processing (IN PROGRESS)**
1. ✅ **Event Routing**: Forward GitHub webhooks to workflow_scheduler service
2. ✅ **Basic Filtering**: Installation and repository-level filtering
3. 🚧 **GitHub Trigger Enhancements**: Enhanced trigger nodes with repository context
4. 🚧 **Repository Context**: GitHub API client for accessing repository data

### 📋 **Phase 3: Advanced Features (PLANNED)**
1. **Specialized GitHub Nodes**: PR analysis, code review, issue management
2. **Advanced Filtering**: Branch patterns, file paths, user/label filters
3. **Monitoring Dashboard**: Installation analytics and webhook metrics
4. **User Interface**: Frontend components for GitHub integration management

### 📋 **Phase 4: Production Readiness (PLANNED)**
1. **Security Audit**: Comprehensive security review and penetration testing
2. **Performance Optimization**: Rate limiting, caching, and scaling
3. **Documentation**: User guides and developer documentation
4. **Onboarding Flows**: Guided setup and integration tutorials

### **Current Implementation Architecture:**

```
Frontend App → GitHub App Install → GitHub Callback → API Gateway
                                                           ↓
User clicks     User authorizes      GitHub redirects    Stores in DB
"Connect GitHub"    repositories     with installation   +
                                           data           Forwards to
                                                         Scheduler
```

**Ready for Integration:**
- ✅ Frontend can initiate GitHub connections via GitHub App install URL
- ✅ Backend properly handles installation callbacks and stores user mappings
- ✅ Generic API allows frontend to display user's connected integrations
- ✅ Webhook processing forwards events to workflow scheduling system

## 7. Monitoring and Observability

### Metrics to Track
- Webhook delivery success rates
- API rate limit usage
- Installation/uninstallation events
- Workflow trigger success rates
- Token refresh frequency

### Logging Strategy
- Structured logging for all GitHub API calls
- Webhook payload logging (sanitized)
- Error tracking and alerting
- Performance monitoring

## 8. Production Deployment Strategy

### Step 1: Infrastructure Setup

**Domain & SSL Requirements:**
```yaml
Primary Domain: api.aiworkflowteams.com
Webhook Endpoint: api.aiworkflowteams.com/webhooks/github
Auth Callback: api.aiworkflowteams.com/api/v1/public/webhooks/github/auth
SSL Certificate: Required (Let's Encrypt or commercial)
```

**AWS ECS Deployment Architecture:**
```yaml
# docker-compose.production.yml
services:
  api-gateway:
    image: aiworkflowteams/api-gateway:latest
    environment:
      - GITHUB_APP_ID=${GITHUB_APP_ID}
      - GITHUB_APP_PRIVATE_KEY=${GITHUB_APP_PRIVATE_KEY}
      - GITHUB_WEBHOOK_SECRET=${GITHUB_WEBHOOK_SECRET}
    ports:
      - "443:8000"
    volumes:
      - ./ssl:/etc/ssl/certs

  github-processor:
    image: aiworkflowteams/github-processor:latest
    environment:
      - GITHUB_APP_ID=${GITHUB_APP_ID}
      - GITHUB_APP_PRIVATE_KEY=${GITHUB_APP_PRIVATE_KEY}
    depends_on:
      - redis
      - postgres
```

### Step 2: Environment Configuration

**Production Environment Variables:**
```bash
# GitHub App Configuration
GITHUB_APP_ID=123456
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n..."
GITHUB_WEBHOOK_SECRET=prod_webhook_secret_here
GITHUB_API_BASE_URL=https://api.github.com

# Database
DATABASE_URL=postgresql://user:pass@prod-db:5432/aiworkflow
REDIS_URL=redis://prod-redis:6379

# Security
JWT_SECRET=prod_jwt_secret
ENCRYPTION_KEY=prod_encryption_key

# Monitoring
SENTRY_DSN=https://...
DATADOG_API_KEY=...
```

**Secret Management:**
```bash
# AWS Secrets Manager
aws secretsmanager create-secret \
  --name "github-app-private-key" \
  --secret-string file://github-private-key.pem

# ECS Task Definition
{
  "secrets": [
    {
      "name": "GITHUB_APP_PRIVATE_KEY",
      "valueFrom": "arn:aws:secretsmanager:region:account:secret:github-app-private-key"
    }
  ]
}
```

### Step 3: Load Balancer & Scaling

**Application Load Balancer Configuration:**
```yaml
# ALB Rules
- Path: /webhooks/github
  Target: github-webhook-service
  Health Check: /health

- Path: /auth/github/*
  Target: auth-service
  Health Check: /health

# Auto Scaling
Min Capacity: 2
Max Capacity: 20
Target CPU: 70%
Scale Out: 2 instances
Scale In: 1 instance
```

**Rate Limiting Strategy:**
```python
# API Gateway Rate Limits
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # GitHub webhook endpoints: 1000 req/min per IP
    # Auth endpoints: 100 req/min per IP
    # API endpoints: 500 req/min per user
    pass
```

### Step 4: Database Migration & Setup

**Production Database Schema:**
```sql
-- Run database migrations
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- GitHub installations table
CREATE TABLE github_installations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
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

-- Indexes for performance
CREATE INDEX idx_github_installations_user_id ON github_installations(user_id);
CREATE INDEX idx_github_installations_installation_id ON github_installations(installation_id);
CREATE INDEX idx_github_installations_account_id ON github_installations(account_id);

-- GitHub events log (for debugging/monitoring)
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
```

### Step 5: Monitoring & Alerting

**Health Checks:**
```python
@app.get("/health")
async def health_check():
    checks = {
        "database": await check_database_connection(),
        "github_api": await check_github_api_access(),
        "redis": await check_redis_connection()
    }

    if all(checks.values()):
        return {"status": "healthy", "checks": checks}
    else:
        raise HTTPException(500, {"status": "unhealthy", "checks": checks})
```

**Monitoring Metrics:**
```yaml
# CloudWatch/DataDog Metrics
- github.webhook.received (counter)
- github.webhook.processed (counter)
- github.webhook.failed (counter)
- github.api.rate_limit_remaining (gauge)
- github.installations.active (gauge)
- github.token.refresh_rate (counter)
- workflow.triggers.executed (counter)
```

**Alerting Rules:**
```yaml
# Critical Alerts
- Webhook failure rate > 5%
- GitHub API rate limit < 100 remaining
- Database connection failures
- SSL certificate expiring in 30 days

# Warning Alerts
- High webhook processing latency (>2s)
- Installation uninstall rate spike
- Unusual API usage patterns
```

### Step 6: CI/CD Pipeline

**GitHub Actions Deployment:**
```yaml
# .github/workflows/deploy-production.yml
name: Deploy Production
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build Docker Images
        run: |
          docker build -t aiworkflowteams/api-gateway:${{ github.sha }} .
          docker build -t aiworkflowteams/github-processor:${{ github.sha }} ./processors/github

      - name: Push to ECR
        run: |
          aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_REGISTRY
          docker push aiworkflowteams/api-gateway:${{ github.sha }}
          docker push aiworkflowteams/github-processor:${{ github.sha }}

      - name: Deploy to ECS
        run: |
          aws ecs update-service --cluster prod --service github-integration --force-new-deployment
```

### Step 7: Go-Live Checklist

**Pre-Launch Verification:**
- [ ] GitHub App created and configured in production
- [ ] SSL certificates installed and verified
- [ ] Webhook endpoints responding correctly
- [ ] Database migrations completed
- [ ] Environment variables configured
- [ ] Rate limiting and security measures active
- [ ] Monitoring and alerting configured
- [ ] Load testing completed
- [ ] Security audit completed

**Launch Steps:**
1. **Soft Launch**: Enable for internal team first
2. **Beta Testing**: Invite select users to test
3. **GitHub Marketplace**: Submit app for review and listing
4. **Public Launch**: Announce availability
5. **Monitor & Scale**: Watch metrics and scale as needed

**Post-Launch Actions:**
- Monitor webhook delivery rates
- Track user installation patterns
- Gather user feedback for improvements
- Scale infrastructure based on usage
- Plan feature enhancements

### Step 8: Operational Procedures

**Incident Response:**
```bash
# Webhook endpoint down
1. Check ALB health checks
2. Verify ECS service status
3. Check application logs
4. Scale up if needed
5. Alert GitHub if widespread issues

# Rate limit exceeded
1. Check current usage patterns
2. Implement request queuing
3. Contact GitHub for limit increase if needed
4. Optimize API usage patterns
```

**Maintenance Windows:**
- Schedule during low-usage hours (typically 2-6 AM UTC)
- Notify users via status page 24 hours in advance
- Implement rolling updates to minimize downtime
- Test rollback procedures before deployments

This comprehensive deployment strategy ensures the GitHub App can be reliably used by all users while maintaining high availability, security, and performance standards.
