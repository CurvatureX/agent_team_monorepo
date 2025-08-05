# GitHub App Integration Architecture

## Overview

This document outlines the technical design for a centralized GitHub App that enables users to connect their repositories (including private ones) to our AI workflow system. The GitHub App will handle webhook events, provide secure access to repository data, and enable workflow triggers based on GitHub activities.

## Architecture Components

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   GitHub App    │────▶│  Event Processor │────▶│ Workflow Engine  │
│   (Webhooks)    │     │   (API Gateway)  │     │   (Execution)    │
└─────────────────┘     └──────────────────┘     └──────────────────┘
        │                        │                        │
        │                        │                        │
        ▼                        ▼                        ▼
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   GitHub API    │     │    Supabase      │     │   User Workflows │
│ (Code Access)   │     │ (Auth & State)   │     │   (Triggered)    │
└─────────────────┘     └──────────────────┘     └──────────────────┘
```

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
Callback URL: "https://api.aiworkflowteams.com/auth/github/callback"
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

### Step 4: App Distribution & Discovery

**GitHub Marketplace (Recommended):**
1. **Prepare for Marketplace**: Complete app description, screenshots, pricing
2. **Submit for Review**: GitHub reviews public apps for quality/security
3. **App Store Listing**: Users can discover and install from GitHub Marketplace

**Direct Installation URL:**
- `https://github.com/apps/ai-workflow-teams/installations/new`
- Can be embedded in your application for direct installation

### Installation Flow

1. **User initiates connection** via our frontend
2. **OAuth redirect** to GitHub App installation page
3. **User selects repositories** to grant access
4. **GitHub redirects back** with installation ID
5. **We store installation mapping** in Supabase

```sql
-- GitHub App installations table
CREATE TABLE github_installations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    installation_id BIGINT UNIQUE NOT NULL,
    account_id BIGINT NOT NULL,
    account_login TEXT NOT NULL,
    account_type TEXT NOT NULL, -- 'User' or 'Organization'
    repositories JSONB, -- Array of accessible repo info
    permissions JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- GitHub repository configurations
CREATE TABLE github_repository_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    installation_id UUID REFERENCES github_installations(id),
    repository_id BIGINT NOT NULL,
    repository_name TEXT NOT NULL, -- 'owner/repo'
    webhook_secret TEXT, -- For signature verification
    active_triggers JSONB, -- Array of active workflow trigger configs
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## 2. Webhook Event Processing

### Event Reception Pipeline

```python
# API Gateway webhook endpoint
@app.post("/webhooks/github")
async def github_webhook_handler(
    request: Request,
    x_github_event: str = Header(...),
    x_github_delivery: str = Header(...),
    x_hub_signature_256: str = Header(...)
):
    # 1. Verify webhook signature
    payload = await request.body()
    if not verify_github_signature(payload, x_hub_signature_256):
        raise HTTPException(401, "Invalid signature")

    # 2. Parse event data
    event_data = json.loads(payload)

    # 3. Route to event processor
    await process_github_event(
        event_type=x_github_event,
        delivery_id=x_github_delivery,
        payload=event_data
    )
```

### Event Processing Service

```python
class GitHubEventProcessor:
    async def process_event(self, event_type: str, payload: dict):
        # 1. Extract installation and repository info
        installation_id = payload.get("installation", {}).get("id")
        repository = payload.get("repository", {})

        # 2. Find matching workflow triggers
        triggers = await self.find_matching_triggers(
            installation_id, repository["full_name"], event_type, payload
        )

        # 3. For each matching trigger, initiate workflow
        for trigger in triggers:
            await self.execute_workflow_trigger(trigger, payload)

    async def find_matching_triggers(self, installation_id, repo_name, event_type, payload):
        # Query active triggers for this repository and event type
        # Apply filters (branches, paths, actions, authors, labels)
        return matching_triggers
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

## 6. Implementation Plan

### Phase 1: Core Infrastructure
1. Create GitHub App with basic permissions
2. Implement webhook reception and signature verification
3. Set up installation flow and database schema
4. Build GitHub API client with token management

### Phase 2: Event Processing
1. Implement event routing and filtering
2. Create GitHub trigger node enhancements
3. Build repository context services
4. Add workflow integration

### Phase 3: Advanced Features
1. Create specialized GitHub action nodes
2. Implement advanced filtering (paths, labels, etc.)
3. Add monitoring and analytics
4. Build user management interface

### Phase 4: Production Readiness
1. Security audit and penetration testing
2. Performance optimization
3. Comprehensive documentation
4. User onboarding flows

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
Auth Callback: api.aiworkflowteams.com/auth/github/callback
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
