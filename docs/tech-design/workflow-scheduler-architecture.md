# Workflow Scheduler 技术架构设计

## 1. 概述与业务目标

**workflow_scheduler** 是 Workflow 系统的触发器管理和调度核心，专注于管理workflow的触发条件监控，当触发条件满足时调用workflow_engine执行任务。

### 核心职责

1. **触发器管理**：管理 Cron、Manual、Webhook、Email、GitHub 等多种触发器配置
2. **调度监控**：持续监控触发条件，确保及时响应
3. **部署管理**：管理workflow的部署状态和触发器配置
4. **调度协调**：当触发条件满足时，通过HTTP调用workflow_engine执行

### 职责边界

**workflow_scheduler 负责**：
- 触发器配置和监控
- 调度时机判断
- 部署状态管理
- 分布式锁防重

**workflow_engine 负责**：
- 实际workflow执行
- 执行状态跟踪
- 执行历史记录
- 节点执行管理

## 2. 系统架构

```mermaid
graph TD
    subgraph "Client Layer"
        UI["Frontend (Web/App)"]
        API_CLIENTS["External API Clients"]
        WEBHOOK_CLIENTS["Webhook Clients"]
    end

    subgraph "API Gateway Layer"
        API_GATEWAY["API Gateway (FastAPI)"]
    end

    subgraph "Internal HTTP Services"
        WF_SCHEDULER["workflow_scheduler (FastAPI)"]
        WF_AGENT["workflow_agent (FastAPI)"]
        WF_ENGINE["workflow_engine (FastAPI)"]
    end

    subgraph "workflow_scheduler Service"
        DEPLOY_SERVICE["DeploymentService"]
        TRIGGER_MANAGER["TriggerManager"]

        CRON_TRIGGER["CronTrigger (APScheduler)"]
        MANUAL_TRIGGER["ManualTrigger"]
        WEBHOOK_TRIGGER["WebhookTrigger"]
        EMAIL_TRIGGER["EmailTrigger (IMAP)"]
        GITHUB_TRIGGER["GitHubTrigger (App Integration)"]
        DISTRIBUTED_LOCK["DistributedLockManager"]
    end

    subgraph "External Systems"
        POSTGRES[("PostgreSQL Database")]
        REDIS[("Redis (Locking & Cache)")]
        EMAIL_SERVER[("Email Server (IMAP)")]
        GITHUB_API[("GitHub API & Webhooks")]
    end

    %% Client connections
    UI --> API_GATEWAY
    API_CLIENTS --> API_GATEWAY
    WEBHOOK_CLIENTS --> API_GATEWAY

    %% API Gateway to internal services
    API_GATEWAY --> WF_SCHEDULER
    API_GATEWAY --> WF_AGENT

    %% Internal service connections
    WF_SCHEDULER --> DEPLOY_SERVICE
    DEPLOY_SERVICE --> TRIGGER_MANAGER

    TRIGGER_MANAGER --> CRON_TRIGGER
    TRIGGER_MANAGER --> MANUAL_TRIGGER
    TRIGGER_MANAGER --> WEBHOOK_TRIGGER
    TRIGGER_MANAGER --> EMAIL_TRIGGER
    TRIGGER_MANAGER --> GITHUB_TRIGGER

    %% All triggers call workflow_engine
    CRON_TRIGGER --> WF_ENGINE
    MANUAL_TRIGGER --> WF_ENGINE
    WEBHOOK_TRIGGER --> WF_ENGINE
    EMAIL_TRIGGER --> WF_ENGINE
    GITHUB_TRIGGER --> WF_ENGINE

    %% Data and external connections
    WF_SCHEDULER --> DISTRIBUTED_LOCK
    WF_SCHEDULER --> POSTGRES
    DISTRIBUTED_LOCK --> REDIS
    EMAIL_TRIGGER --> EMAIL_SERVER
    GITHUB_TRIGGER --> GITHUB_API
```

## 3. 核心组件设计

### 3.1. DeploymentService

**职责**：管理 Workflow 的部署生命周期

**核心功能**：
- 验证 Workflow 定义的有效性（基本结构验证）
- 创建/更新/删除部署记录
- 配置触发器（Cron 表达式、Webhook 路径、Email 过滤器）
- 与 TriggerManager 协调，注册/注销触发器

**API接口**：
```python
class DeploymentService:
    async def deploy_workflow(self, workflow_id: str, workflow_spec: dict) -> DeploymentResult
    async def undeploy_workflow(self, workflow_id: str) -> bool
    async def update_deployment(self, workflow_id: str, workflow_spec: dict) -> DeploymentResult
    async def get_deployment_status(self, workflow_id: str) -> DeploymentStatus
```

### 3.2. TriggerManager

**职责**：统一管理所有类型的触发器

**支持的触发器类型**：
- **Cron触发器**：基于cron表达式的定时执行
- **Manual触发器**：用户手动触发，支持确认机制
- **Webhook触发器**：HTTP端点触发，每个workflow独立路径
- **Email触发器**：邮件监控触发，支持过滤器和附件处理
- **GitHub触发器**：GitHub仓库事件触发，支持App集成和代码访问

**核心功能**：
- 管理触发器生命周期（启动/停止/重启）
- 解析触发事件，提取相关数据
- 验证触发权限和参数
- 直接调用 workflow_engine HTTP 接口执行workflow

**API接口**：
```python
class TriggerManager:
    async def register_triggers(self, workflow_id: str, trigger_specs: List[TriggerSpec]) -> bool
    async def unregister_triggers(self, workflow_id: str) -> bool
    async def get_trigger_status(self, workflow_id: str) -> Dict[str, TriggerStatus]
    async def trigger_manual(self, workflow_id: str, user_id: str, confirmation: bool = False) -> ExecutionResult
    async def process_webhook(self, workflow_id: str, request_data: dict) -> ExecutionResult
```

## 4. 触发器详细设计

### 4.1. Cron触发器 (CronTrigger)

**技术实现**：
- 基于 Python APScheduler 实现
- 支持标准cron表达式和时区配置
- 哈希分散机制避免任务同时执行
- 分布式锁防止重复执行

**配置示例**：
```json
{
  "node_type": "TRIGGER_NODE",
  "subtype": "TRIGGER_CRON",
  "parameters": {
    "cron_expression": "0 9 * * MON-FRI",
    "timezone": "America/New_York",
    "enabled": true
  }
}
```

**实现核心**：
```python
class CronTrigger(BaseTrigger):
    async def start(self):
        if not self.enabled:
            return

        self.scheduler.add_job(
            func=self._execute_with_jitter,
            trigger=CronTrigger(self.cron_expression),
            timezone=self.timezone,
            id=f"cron_{self.workflow_id}",
            replace_existing=True
        )

    async def _execute_with_jitter(self):
        jitter = self._calculate_jitter(self.workflow_id)
        await asyncio.sleep(jitter)

        async with self.lock_manager.acquire(f"workflow_{self.workflow_id}"):
            await self._trigger_workflow()
```

### 4.2. Manual触发器 (ManualTrigger)

**技术实现**：
- 通过 API Gateway 提供 REST 端点
- 支持用户身份验证
- 可选的确认机制防误触发
- 实时响应用户操作

**API端点**：
```
POST /api/v1/workflows/{workflow_id}/trigger/manual
Authorization: Bearer <jwt_token>
{
  "confirmation": true
}
```

**实现核心**：
```python
class ManualTrigger(BaseTrigger):
    async def trigger_manual(self, user_id: str, confirmation: bool = False):
        if self.require_confirmation and not confirmation:
            return {"status": "confirmation_required", "message": "Please confirm execution"}

        trigger_data = {
            "trigger_time": datetime.now().isoformat(),
            "execution_id": f"exec_{uuid.uuid4()}",
            "user_id": user_id
        }

        return await self._trigger_workflow(trigger_data)
```

### 4.3. Webhook触发器 (WebhookTrigger)

**技术实现**：
- 每个workflow分配唯一的webhook路径
- API Gateway统一接收并路由webhook请求
- 支持多种HTTP方法 (GET/POST/PUT/PATCH/DELETE)
- 可配置身份验证要求

**路径格式**：
```
https://api.example.com/webhook/{workflow_id}
https://api.example.com/webhook/custom-path  # 自定义路径
```

**实现核心**：
```python
class WebhookTrigger(BaseTrigger):
    def get_webhook_url(self) -> str:
        return f"{API_GATEWAY_BASE_URL}{self.webhook_path}"

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

### 4.4. Email触发器 (EmailTrigger)

**技术实现**：
- 基于 IMAP 协议监控邮箱
- 异步邮件检查任务 (可配置间隔)
- 支持邮件过滤器 (发件人、主题、内容)
- 可选的附件处理和自动标记已读

**配置示例**：
```json
{
  "node_type": "TRIGGER_NODE",
  "subtype": "TRIGGER_EMAIL",
  "parameters": {
    "email_filter": "from:github-noreply@github.com",
    "folder": "INBOX",
    "mark_as_read": true,
    "attachment_processing": "include"
  }
}
```

**实现核心**：
```python
class EmailTrigger(BaseTrigger):
    async def _monitor_emails(self):
        while True:
            try:
                async with IMAPClient() as client:
                    await client.connect()
                    await client.select_folder(self.folder)

                    new_emails = await client.search('UNSEEN')

                    for email_id in new_emails:
                        email_data = await self._process_email(client, email_id)

                        if self._matches_filter(email_data):
                            await self._trigger_workflow(email_data)

                            if self.mark_as_read:
                                await client.add_flags(email_id, ['\\Seen'])

            except Exception as e:
                logger.error(f"Email monitoring error: {e}")

            await asyncio.sleep(self.check_interval)
```

### 4.5. GitHub触发器 (GitHubTrigger)

**技术实现**：
- 基于 GitHub App 集成，通过webhook接收事件
- 支持私有仓库访问和完整的代码权限
- 高级过滤器：分支、路径、作者、标签等
- 自动获取仓库上下文（PR diff、文件内容等）

**配置示例**：
```json
{
  "node_type": "TRIGGER_NODE",
  "subtype": "TRIGGER_GITHUB",
  "parameters": {
    "github_app_installation_id": "12345678",
    "repository": "microsoft/vscode",
    "events": ["push", "pull_request"],
    "branches": ["main", "develop"],
    "paths": ["src/**", "*.md"],
    "action_filter": ["opened", "synchronize"],
    "author_filter": "^(?!dependabot)",
    "label_filter": ["bug", "enhancement"],
    "ignore_bots": true,
    "draft_pr_handling": "ignore"
  }
}
```

**GitHub App集成**：
```python
class GitHubTrigger(BaseTrigger):
    def __init__(self, workflow_id: str, config: GitHubTriggerSpec):
        self.installation_id = config.github_app_installation_id
        self.repository = config.repository
        self.events = config.events
        self.filters = {
            "branches": config.branches,
            "paths": config.paths,
            "actions": config.action_filter,
            "author": config.author_filter,
            "labels": config.label_filter
        }

    async def process_github_event(self, event_type: str, payload: dict):
        # 1. 验证事件类型和仓库匹配
        if not self._matches_event_filter(event_type, payload):
            return

        # 2. 应用高级过滤器
        if not self._matches_advanced_filters(event_type, payload):
            return

        # 3. 增强事件数据 - 获取仓库上下文
        enhanced_data = await self._enhance_event_data(event_type, payload)

        # 4. 触发workflow执行
        return await self._trigger_workflow(enhanced_data)

    async def _enhance_event_data(self, event_type: str, payload: dict) -> dict:
        """使用GitHub App权限获取额外的仓库数据"""
        github_client = GitHubAppClient(
            app_id=GITHUB_APP_ID,
            private_key=GITHUB_APP_PRIVATE_KEY
        )

        enhanced_data = {
            "event": event_type,
            "action": payload.get("action"),
            "repository": payload["repository"],
            "sender": payload["sender"],
            "payload": payload,
            "timestamp": datetime.now().isoformat()
        }

        # 根据事件类型增强数据
        if event_type == "pull_request":
            pr_context = await github_client.get_pr_context(
                self.installation_id,
                self.repository,
                payload["number"]
            )
            enhanced_data["pr_context"] = pr_context

        elif event_type == "push":
            commit_contexts = []
            for commit in payload["commits"]:
                commit_context = await github_client.get_commit_context(
                    self.installation_id,
                    self.repository,
                    commit["id"]
                )
                commit_contexts.append(commit_context)
            enhanced_data["commit_contexts"] = commit_contexts

        return enhanced_data
```

**高级过滤系统**：
```python
def _matches_advanced_filters(self, event_type: str, payload: dict) -> bool:
    # 分支过滤
    if self.filters["branches"] and event_type in ["push", "pull_request"]:
        if event_type == "push":
            branch = payload["ref"].replace("refs/heads/", "")
        else:
            branch = payload["pull_request"]["base"]["ref"]

        if branch not in self.filters["branches"]:
            return False

    # 路径过滤 (对push和PR事件)
    if self.filters["paths"]:
        changed_files = self._get_changed_files(event_type, payload)
        if not any(
            any(fnmatch.fnmatch(file, pattern) for pattern in self.filters["paths"])
            for file in changed_files
        ):
            return False

    # 作者过滤
    if self.filters["author"]:
        author = self._get_event_author(event_type, payload)
        if not re.match(self.filters["author"], author):
            return False

    # 标签过滤 (仅对issues和PR)
    if self.filters["labels"] and event_type in ["issues", "pull_request"]:
        event_labels = [label["name"] for label in payload.get("labels", [])]
        if not any(label in event_labels for label in self.filters["labels"]):
            return False

    return True
```

**GitHub App权限和安全**：
- 使用短期访问令牌（1小时有效期）
- 支持细粒度仓库权限控制
- Webhook签名验证确保数据完整性
- 支持私有仓库访问

## 5. 执行流程

### 5.1. Workflow 部署流程

```mermaid
sequenceDiagram
    participant Client
    participant Gateway as API Gateway
    participant Deploy as DeploymentService
    participant TriggerMgr as TriggerManager
    participant DB as PostgreSQL

    Client->>Gateway: POST /workflows/{id}/deploy
    Gateway->>Deploy: deploy_workflow(workflow_spec)

    Deploy->>Deploy: validate_workflow_definition()
    Deploy->>DB: UPDATE workflows SET deployment_status='DEPLOYED'

    Deploy->>TriggerMgr: register_triggers(workflow_id, trigger_specs)

    loop For each trigger
        TriggerMgr->>TriggerMgr: create_trigger_instance()
        TriggerMgr->>TriggerMgr: start_trigger()
    end

    TriggerMgr-->>Deploy: All triggers registered
    Deploy-->>Gateway: Deployment successful
    Gateway-->>Client: 200 OK (deployment_id)
```

### 5.2. Cron 触发执行流程

```mermaid
sequenceDiagram
    participant Scheduler as APScheduler
    participant Cron as CronTrigger
    participant Lock as DistributedLockManager
    participant Engine as workflow_engine

    Note over Scheduler: Cron 时间到达

    Scheduler->>Cron: trigger_execution()
    Cron->>Cron: calculate_jitter(workflow_id)
    Cron->>Cron: sleep(jitter_seconds)

    Cron->>Lock: acquire_lock(workflow_id)
    alt Lock acquired
        Cron->>Engine: POST /v1/workflows/{id}/execute
        Engine-->>Cron: 202 Accepted (execution_id)
        Cron->>Lock: release_lock(workflow_id)
    else Lock failed
        Note over Cron: Skip execution (already running)
    end
```

### 5.3. Manual 触发执行流程

```mermaid
sequenceDiagram
    participant User
    participant Gateway as API Gateway
    participant Manual as ManualTrigger
    participant Engine as workflow_engine

    User->>Gateway: POST /workflows/{id}/trigger/manual
    Gateway->>Gateway: authenticate_user()
    Gateway->>Manual: trigger_manual(workflow_id, user_id)

    alt require_confirmation = true
        Manual-->>Gateway: confirmation_required
        Gateway-->>User: 403 Confirmation Required
        User->>Gateway: POST /workflows/{id}/trigger/manual (confirmation=true)
        Gateway->>Manual: trigger_manual(workflow_id, user_id, confirmation=true)
    end

    Manual->>Engine: POST /v1/workflows/{id}/execute
    Engine-->>Manual: 202 Accepted (execution_id)
    Manual-->>Gateway: execution_started
    Gateway-->>User: 200 OK (execution_id)
```

### 5.4. Webhook 触发执行流程

```mermaid
sequenceDiagram
    participant Client as External System
    participant Gateway as API Gateway
    participant Webhook as WebhookTrigger
    participant Engine as workflow_engine

    Client->>Gateway: POST /webhook/{workflow_id}
    Gateway->>Gateway: parse_request_data()
    Gateway->>Webhook: process_webhook(workflow_id, request_data)

    Webhook->>Webhook: validate_authentication()
    Webhook->>Webhook: extract_trigger_data()

    Webhook->>Engine: POST /v1/workflows/{id}/execute
    Engine-->>Webhook: 202 Accepted (execution_id)

    Webhook-->>Gateway: 200 OK
    Gateway-->>Client: Webhook received
```

### 5.5. Email 触发执行流程

```mermaid
sequenceDiagram
    participant Email as Email Server
    participant Monitor as EmailTrigger
    participant Engine as workflow_engine

    loop Email Monitoring
        Monitor->>Email: IMAP check for new emails
        Email-->>Monitor: new_emails[]

        loop For each new email
            Monitor->>Monitor: extract_email_data()
            Monitor->>Monitor: apply_email_filter()

            alt Email matches filter
                Monitor->>Engine: POST /v1/workflows/{id}/execute
                Engine-->>Monitor: 202 Accepted (execution_id)

                opt mark_as_read = true
                    Monitor->>Email: IMAP mark as read
                end
            end
        end

        Monitor->>Monitor: sleep(check_interval)
    end
```

### 5.6. GitHub 触发执行流程

```mermaid
sequenceDiagram
    participant GitHub as GitHub (Webhook)
    participant Gateway as API Gateway
    participant GitHubTrigger as GitHubTrigger
    participant GitHubClient as GitHubAppClient
    participant Engine as workflow_engine

    GitHub->>Gateway: POST /webhooks/github (event payload)
    Gateway->>Gateway: verify_github_signature()
    Gateway->>GitHubTrigger: process_github_event(event_type, payload)

    GitHubTrigger->>GitHubTrigger: matches_event_filter()
    GitHubTrigger->>GitHubTrigger: matches_advanced_filters()

    alt Event matches filters
        GitHubTrigger->>GitHubClient: get_installation_token(installation_id)
        GitHubClient-->>GitHubTrigger: access_token (1h validity)

        alt Event type: pull_request
            GitHubTrigger->>GitHubClient: get_pr_context(repo, pr_number)
            GitHubClient->>GitHub: GET /repos/{repo}/pulls/{number}
            GitHubClient->>GitHub: GET /repos/{repo}/pulls/{number}/files
            GitHubClient-->>GitHubTrigger: pr_context (diff, files, comments)
        else Event type: push
            GitHubTrigger->>GitHubClient: get_commit_context(repo, commit_sha)
            GitHubClient->>GitHub: GET /repos/{repo}/commits/{sha}
            GitHubClient-->>GitHubTrigger: commit_context (diff, files)
        end

        GitHubTrigger->>Engine: POST /v1/workflows/{id}/execute (enhanced_data)
        Engine-->>GitHubTrigger: 202 Accepted (execution_id)
    end

    GitHubTrigger-->>Gateway: 200 OK
    Gateway-->>GitHub: Webhook processed
```

## 6. GitHub App 集成架构

### 6.1. GitHub App 配置

**App权限要求**：
- `contents: read` - 访问仓库文件和diff
- `metadata: read` - 基本仓库信息
- `pull_requests: read` - PR数据和评论
- `issues: read` - Issue数据和评论
- `actions: read` - Workflow运行信息
- `deployments: read` - 部署状态

**Webhook事件**：
```yaml
支持的事件类型:
  - push, pull_request, pull_request_review
  - issues, issue_comment, release
  - deployment, deployment_status
  - workflow_run, check_run, check_suite
  - create, delete, fork, star, watch
```

### 6.2. 数据库集成

**GitHub安装记录**：
```sql
CREATE TABLE github_installations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    installation_id BIGINT UNIQUE NOT NULL,
    account_id BIGINT NOT NULL,
    account_login TEXT NOT NULL,
    account_type TEXT NOT NULL, -- 'User' or 'Organization'
    repositories JSONB, -- Array of accessible repo info
    permissions JSONB,
    access_token_expires_at TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

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

### 6.3. API Gateway集成

**Webhook端点**：
```python
@app.post("/webhooks/github")
async def github_webhook_handler(
    request: Request,
    x_github_event: str = Header(...),
    x_github_delivery: str = Header(...),
    x_hub_signature_256: str = Header(...)
):
    # 1. 验证webhook签名
    payload = await request.body()
    if not verify_github_signature(payload, x_hub_signature_256):
        raise HTTPException(401, "Invalid signature")

    # 2. 解析事件数据
    event_data = json.loads(payload)

    # 3. 路由到workflow_scheduler
    await workflow_scheduler.process_github_event(
        event_type=x_github_event,
        delivery_id=x_github_delivery,
        payload=event_data
    )

    return {"status": "processed"}
```

## 7. 部署架构

### 7.1. 服务配置

**workflow_scheduler** 作为独立的 FastAPI 服务：

- **端口**: 8003
- **协议**: HTTP/REST API
- **依赖**: APScheduler, Redis, PostgreSQL, IMAP客户端
- **健康检查**: `curl -f http://localhost:8003/health`

### 7.2. 环境变量配置

```bash
# 核心服务配置
PORT="8003"
HOST="0.0.0.0"
DEBUG="false"

# 外部服务地址
WORKFLOW_ENGINE_URL="http://workflow-engine:8002"
API_GATEWAY_URL="http://api-gateway:8000"

# 数据库配置
DATABASE_URL="postgresql://user:pass@postgres/workflow_scheduler"
REDIS_URL="redis://redis:6379/1"

# 邮件监控配置
IMAP_SERVER="imap.gmail.com"
EMAIL_USER="workflow@example.com"
EMAIL_PASSWORD="app_password"
EMAIL_CHECK_INTERVAL="60"

# GitHub App集成配置
GITHUB_APP_ID="123456"
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
GITHUB_WEBHOOK_SECRET="secure_webhook_secret_here"
GITHUB_API_BASE_URL="https://api.github.com"

# APScheduler配置
SCHEDULER_TIMEZONE="UTC"
SCHEDULER_MAX_WORKERS="10"
```

### 7.3. 分布式部署

- 多个 workflow_scheduler 实例负载均衡
- 通过 Redis 实现分布式锁和状态共享
- PostgreSQL 作为共享数据存储
- workflow_engine 通过 AWS ECS 独立部署和伸缩
- **简化架构**：无需复杂的执行状态同步，只需管理触发器状态

## 7. 安全考虑

### 7.1. 身份验证

- **Manual触发器**: JWT token验证
- **Webhook触发器**: 可选的API密钥或签名验证
- **Email触发器**: 安全的IMAP连接和凭据管理
- **内部服务**: HTTP API之间的服务间认证

### 7.2. 权限控制

- 基于用户角色的workflow触发权限
- Webhook端点的访问控制
- 邮箱监控的权限隔离
- 审计日志记录所有触发事件

### 7.3. 数据安全

- 敏感配置加密存储
- 邮件内容的安全处理
- 网络传输TLS加密
- 分布式锁的安全实现

## 8. 监控与可观测性

### 8.1. 关键指标

- 部署的 Workflow 数量和状态分布
- 各类触发器的调度成功率和失败率
- 调度延迟和哈希分散效果
- 系统资源使用情况（CPU、内存、数据库连接）
- 邮件监控延迟和处理量

### 8.2. 日志结构

```json
{
  "timestamp": "2025-01-28T10:30:00Z",
  "service": "workflow_scheduler",
  "trigger_type": "cron",
  "workflow_id": "wf_123",
  "execution_id": "exec_456",
  "event": "trigger_fired",
  "duration_ms": 1250,
  "status": "success"
}
```

### 8.3. 告警策略

- 触发器调度失败率超过阈值
- 调度延迟异常延长
- 邮件监控连接失败
- 系统资源不足
- 依赖服务不可用（workflow_engine、数据库）

## 9. 实现技术栈

### 9.1. 核心技术

- **Web框架**: FastAPI (Python 3.11+)
- **调度器**: APScheduler
- **数据库**: PostgreSQL + SQLAlchemy
- **缓存/锁**: Redis
- **邮件**: aioimaplib (异步IMAP客户端)
- **HTTP客户端**: httpx (异步HTTP)

### 9.2. 项目结构

```
workflow_scheduler/
├── app/
│   ├── main.py                    # FastAPI应用入口
│   ├── api/                       # REST API端点
│   │   ├── deployment.py         # 部署管理API
│   │   └── triggers.py           # 触发器管理API
│   ├── services/
│   │   ├── deployment_service.py # 部署服务
│   │   ├── trigger_manager.py    # 触发器管理器
│   │   └── github_client.py     # GitHub App客户端
│   ├── triggers/
│   │   ├── base.py               # 基础触发器类
│   │   ├── cron_trigger.py       # Cron触发器
│   │   ├── manual_trigger.py     # 手动触发器
│   │   ├── webhook_trigger.py    # Webhook触发器
│   │   ├── email_trigger.py      # 邮件触发器
│   │   └── github_trigger.py     # GitHub触发器
│   ├── models/                   # 数据模型
│   └── core/                     # 核心配置
├── tests/                        # 单元测试
├── requirements.txt              # Python依赖
└── Dockerfile                    # 容器化配置
```

### 9.3. 开发命令

```bash
# 安装依赖
uv sync

# 运行服务
python -m workflow_scheduler.app.main

# 运行测试
pytest tests/

# 构建Docker镜像
docker build -t workflow-scheduler --platform linux/amd64 .
```

这个设计专注于workflow_scheduler的实现，完全移除了workflow_runtime的历史包袱，提供了清晰、可实现的架构方案。
