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

**职责**：管理 Workflow 的完整部署生命周期

**部署状态管理**：
- `DRAFT` - 工作流已创建但未部署
- `DEPLOYING` - 正在部署中（触发器注册进行中）
- `DEPLOYED` - 已成功部署，触发器正在运行
- `DEPLOYMENT_FAILED` - 部署失败
- `UNDEPLOYING` - 正在取消部署
- `UNDEPLOYED` - 已取消部署，触发器已停止
- `DEPRECATED` - 已弃用但未删除

**核心功能**：
- 验证 Workflow 定义的有效性（节点结构、触发器配置等）
- 管理部署状态转换和版本控制
- 协调触发器的注册/注销操作
- 记录部署历史和审计日志
- 处理部署回滚和错误恢复

**数据库设计**（新增迁移：`supabase/migrations/20250806190000_add_workflow_deployment_fields.sql`）：
```sql
-- workflows 表新增字段
ALTER TABLE workflows
ADD COLUMN deployment_status TEXT DEFAULT 'DRAFT',
ADD COLUMN deployed_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN deployed_by UUID REFERENCES users(id),
ADD COLUMN deployment_version INTEGER DEFAULT 1,
ADD COLUMN deployment_config JSONB DEFAULT '{}';

-- 部署历史跟踪表
CREATE TABLE workflow_deployment_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    deployment_action TEXT NOT NULL, -- 'DEPLOY', 'UNDEPLOY', 'UPDATE', 'ROLLBACK'
    from_status TEXT NOT NULL,
    to_status TEXT NOT NULL,
    deployment_version INTEGER NOT NULL,
    triggered_by UUID REFERENCES users(id),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    deployment_logs JSONB DEFAULT '{}'
);
```

**API接口**：
```python
class DeploymentService:
    async def deploy_workflow(self, workflow_id: str, user_id: str, deployment_config: dict = None) -> DeploymentResult
    async def undeploy_workflow(self, workflow_id: str, user_id: str) -> DeploymentResult
    async def update_deployment(self, workflow_id: str, user_id: str, deployment_config: dict = None) -> DeploymentResult
    async def rollback_deployment(self, workflow_id: str, target_version: int, user_id: str) -> DeploymentResult
    async def get_deployment_status(self, workflow_id: str) -> DeploymentStatus
    async def get_deployment_history(self, workflow_id: str) -> List[DeploymentEvent]
    async def list_deployed_workflows(self, user_id: str = None) -> List[WorkflowDeployment]

    # 内部辅助方法
    async def _transition_status(self, workflow_id: str, from_status: str, to_status: str, action: str, user_id: str) -> bool
    async def _log_deployment_event(self, workflow_id: str, action: str, from_status: str, to_status: str, user_id: str, logs: dict = None) -> None
    async def _validate_workflow_definition(self, workflow_spec: dict) -> ValidationResult
```

**实现示例**：
```python
class DeploymentService:
    def __init__(self, db_session, trigger_manager, trigger_index_manager):
        self.db = db_session
        self.trigger_manager = trigger_manager
        self.trigger_index = trigger_index_manager

    async def deploy_workflow(self, workflow_id: str, user_id: str, deployment_config: dict = None) -> DeploymentResult:
        """部署工作流 - 完整的状态管理和事务处理"""

        async with self.db.begin():  # 开启数据库事务
            try:
                # 1. 检查当前状态
                current_status = await self._get_workflow_status(workflow_id)
                if current_status not in ['DRAFT', 'DEPLOYMENT_FAILED', 'UNDEPLOYED']:
                    raise DeploymentError(f"Cannot deploy workflow in status: {current_status}")

                # 2. 更新状态为部署中
                await self._transition_status(workflow_id, current_status, 'DEPLOYING', 'DEPLOY', user_id)

                # 3. 获取workflow定义并验证
                workflow_spec = await self._get_workflow_spec(workflow_id)
                validation_result = await self._validate_workflow_definition(workflow_spec)

                if not validation_result.is_valid:
                    await self._transition_status(workflow_id, 'DEPLOYING', 'DEPLOYMENT_FAILED', 'DEPLOY', user_id)
                    return DeploymentResult(
                        success=False,
                        status='DEPLOYMENT_FAILED',
                        errors=validation_result.errors
                    )

                # 4. 注册触发器到索引表
                await self.trigger_index.register_workflow_triggers(workflow_id, workflow_spec)

                # 5. 启动实际的触发器
                trigger_result = await self.trigger_manager.register_triggers(
                    workflow_id,
                    self._extract_trigger_specs(workflow_spec)
                )

                if not trigger_result.success:
                    # 回滚触发器索引
                    await self.trigger_index.clear_workflow_triggers(workflow_id)
                    await self._transition_status(workflow_id, 'DEPLOYING', 'DEPLOYMENT_FAILED', 'DEPLOY', user_id)
                    return DeploymentResult(
                        success=False,
                        status='DEPLOYMENT_FAILED',
                        errors=['Trigger registration failed: ' + trigger_result.error]
                    )

                # 6. 成功部署 - 更新最终状态
                deployment_version = await self._increment_deployment_version(workflow_id)
                await self._mark_deployment_complete(workflow_id, user_id, deployment_version, deployment_config or {})

                return DeploymentResult(
                    success=True,
                    status='DEPLOYED',
                    deployment_version=deployment_version,
                    deployed_at=datetime.utcnow()
                )

            except Exception as e:
                # 异常处理 - 自动回滚到失败状态
                await self._transition_status(workflow_id, 'DEPLOYING', 'DEPLOYMENT_FAILED', 'DEPLOY', user_id)
                await self._log_deployment_event(
                    workflow_id, 'DEPLOY', 'DEPLOYING', 'DEPLOYMENT_FAILED', user_id,
                    {'error_message': str(e)}
                )
                raise DeploymentError(f"Deployment failed: {e}")

    async def _transition_status(self, workflow_id: str, from_status: str, to_status: str, action: str, user_id: str) -> bool:
        """安全的状态转换 - 带历史记录"""

        # 更新workflows表状态
        result = await self.db.execute(
            """
            UPDATE workflows
            SET deployment_status = %s,
                updated_at = EXTRACT(epoch FROM NOW()) * 1000
            WHERE id = %s AND deployment_status = %s
            """,
            to_status, workflow_id, from_status
        )

        if result.rowcount == 0:
            raise DeploymentError(f"Status transition failed: workflow {workflow_id} not in expected status {from_status}")

        # 记录部署历史
        await self._log_deployment_event(workflow_id, action, from_status, to_status, user_id)
        return True

    async def _log_deployment_event(self, workflow_id: str, action: str, from_status: str, to_status: str, user_id: str, logs: dict = None):
        """记录部署历史事件"""
        deployment_version = await self._get_current_deployment_version(workflow_id)

        await self.db.execute(
            """
            INSERT INTO workflow_deployment_history (
                workflow_id, deployment_action, from_status, to_status,
                deployment_version, triggered_by, deployment_logs
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            workflow_id, action, from_status, to_status,
            deployment_version, user_id, json.dumps(logs or {})
        )

    async def list_deployed_workflows(self, user_id: str = None) -> List[WorkflowDeployment]:
        """列出所有已部署的工作流"""
        query = """
        SELECT
            w.id,
            w.name,
            w.deployment_status,
            w.deployed_at,
            w.deployment_version,
            u.name as deployed_by_name,
            COUNT(ti.id) as active_triggers
        FROM workflows w
        LEFT JOIN users u ON w.deployed_by = u.id
        LEFT JOIN trigger_index ti ON w.id = ti.workflow_id AND ti.deployment_status = 'active'
        WHERE w.deployment_status = 'DEPLOYED'
        """

        params = []
        if user_id:
            query += " AND w.user_id = %s"
            params.append(user_id)

        query += " GROUP BY w.id, w.name, w.deployment_status, w.deployed_at, w.deployment_version, u.name"
        query += " ORDER BY w.deployed_at DESC"

        results = await self.db.fetch_all(query, *params)

        return [
            WorkflowDeployment(
                workflow_id=row['id'],
                name=row['name'],
                status=row['deployment_status'],
                deployed_at=row['deployed_at'],
                deployment_version=row['deployment_version'],
                deployed_by=row['deployed_by_name'],
                active_triggers=row['active_triggers']
            )
            for row in results
        ]
```

### 3.2. TriggerManager

**职责**：统一管理所有类型的触发器

**支持的触发器类型**（与 `shared/node_specs/trigger_nodes.py` 保持一致）：
- **TRIGGER_MANUAL**：用户手动触发，支持确认机制
- **TRIGGER_CRON**：基于cron表达式的定时执行
- **TRIGGER_WEBHOOK**：HTTP端点触发，每个workflow独立路径
- **TRIGGER_SLACK**：Slack交互触发，支持消息、提及、斜杠命令等事件
- **TRIGGER_EMAIL**：邮件监控触发，支持过滤器和附件处理
- **TRIGGER_GITHUB**：GitHub仓库事件触发，支持App集成和代码访问

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

### 4.5. Slack触发器 (SlackTrigger)

**技术实现**：
- 基于 Slack Events API 和 Slack Bot Token 集成
- 支持多种 Slack 事件类型：消息、提及、反应、文件分享等
- 灵活的过滤机制：工作空间、频道、用户、事件类型
- 支持斜杠命令和交互式消息

**核心配置示例**：
```json
{
  "node_type": "TRIGGER_NODE",
  "subtype": "TRIGGER_SLACK",
  "parameters": {
    "workspace_id": "T1234567890",
    "channel_filter": "C1234567890",
    "event_types": ["message", "app_mention"],
    "mention_required": false,
    "command_prefix": "!",
    "user_filter": "U1234567890",
    "ignore_bots": true,
    "require_thread": false
  }
}
```

**实现细节**：
```python
class SlackTrigger(BaseTrigger):
    trigger_type = "TRIGGER_SLACK"

    def __init__(self, workflow_id: str, trigger_config: dict):
        super().__init__(workflow_id, trigger_config)
        self.workspace_id = trigger_config.get("workspace_id")
        self.channel_filter = trigger_config.get("channel_filter")
        self.event_types = trigger_config.get("event_types", ["message", "app_mention"])
        self.mention_required = trigger_config.get("mention_required", False)
        self.user_filter = trigger_config.get("user_filter")
        self.ignore_bots = trigger_config.get("ignore_bots", True)
        self.slack_client = SlackWebClient()

    async def start(self) -> bool:
        """启动Slack事件监听"""
        try:
            # 注册webhook处理器到全局Slack事件路由器
            await self.slack_event_router.register_trigger(
                workspace_id=self.workspace_id,
                trigger=self
            )
            self.status = TriggerStatus.ACTIVE
            return True
        except Exception as e:
            logger.error(f"Failed to start Slack trigger: {e}")
            self.status = TriggerStatus.FAILED
            return False

    async def process_slack_event(self, event_data: dict) -> bool:
        """处理Slack事件"""
        event_type = event_data.get("type")

        # 过滤事件类型
        if event_type not in self.event_types:
            return False

        # 频道过滤
        channel_id = event_data.get("channel")
        if self.channel_filter and not self._matches_channel_filter(channel_id):
            return False

        # 用户过滤
        user_id = event_data.get("user")
        if self.user_filter and not self._matches_user_filter(user_id):
            return False

        # Bot过滤
        if self.ignore_bots and event_data.get("bot_id"):
            return False

        # 提及过滤
        if self.mention_required and not self._has_bot_mention(event_data):
            return False

        # 构建触发数据
        trigger_data = {
            "event_type": event_type,
            "message": event_data.get("text", ""),
            "user_id": user_id,
            "channel_id": channel_id,
            "team_id": event_data.get("team"),
            "timestamp": event_data.get("ts"),
            "thread_ts": event_data.get("thread_ts"),
            "event_data": event_data
        }

        # 触发workflow
        await self._trigger_workflow(trigger_data)
        return True

    def _matches_channel_filter(self, channel_id: str) -> bool:
        """检查频道是否匹配过滤器"""
        if not self.channel_filter:
            return True

        # 支持精确匹配、正则表达式或频道名
        import re
        try:
            if self.channel_filter.startswith("C"):  # 频道ID
                return channel_id == self.channel_filter
            else:  # 作为正则表达式处理
                return bool(re.match(self.channel_filter, channel_id))
        except re.error:
            return False
```

### 4.6. GitHub触发器 (GitHubTrigger)

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
    participant TriggerIndex as TriggerIndexManager
    participant DB as PostgreSQL

    Client->>Gateway: POST /workflows/{id}/deploy
    Gateway->>Deploy: deploy_workflow(workflow_id, user_id, config)

    Deploy->>DB: BEGIN TRANSACTION
    Deploy->>DB: UPDATE workflows SET deployment_status='DEPLOYING'
    Deploy->>DB: INSERT deployment_history (action='DEPLOY', from_status='DRAFT', to_status='DEPLOYING')

    Deploy->>Deploy: validate_workflow_definition()

    alt Validation successful
        Deploy->>TriggerIndex: register_workflow_triggers(workflow_id, workflow_spec)
        TriggerIndex->>DB: DELETE FROM trigger_index WHERE workflow_id=?
        TriggerIndex->>DB: INSERT INTO trigger_index (extracted triggers)

        Deploy->>TriggerMgr: register_triggers(workflow_id, trigger_specs)

        loop For each trigger
            TriggerMgr->>TriggerMgr: create_trigger_instance()
            TriggerMgr->>TriggerMgr: start_trigger()
        end

        TriggerMgr-->>Deploy: All triggers registered successfully

        Deploy->>DB: UPDATE workflows SET deployment_status='DEPLOYED', deployed_at=NOW(), deployed_by=user_id
        Deploy->>DB: UPDATE deployment_history SET completed_at=NOW(), to_status='DEPLOYED'
        Deploy->>DB: COMMIT TRANSACTION

        Deploy-->>Gateway: Deployment successful
        Gateway-->>Client: 200 OK {status: 'DEPLOYED', deployment_version: N}

    else Validation failed
        Deploy->>DB: UPDATE workflows SET deployment_status='DEPLOYMENT_FAILED'
        Deploy->>DB: UPDATE deployment_history SET completed_at=NOW(), to_status='DEPLOYMENT_FAILED', error_message=error
        Deploy->>DB: ROLLBACK TRANSACTION

        Deploy-->>Gateway: Deployment failed
        Gateway-->>Client: 400 Bad Request {error: validation_errors}
    end
```

### 5.1.1. Workflow 取消部署流程

```mermaid
sequenceDiagram
    participant Client
    participant Gateway as API Gateway
    participant Deploy as DeploymentService
    participant TriggerMgr as TriggerManager
    participant TriggerIndex as TriggerIndexManager
    participant DB as PostgreSQL

    Client->>Gateway: POST /workflows/{id}/undeploy
    Gateway->>Deploy: undeploy_workflow(workflow_id, user_id)

    Deploy->>DB: BEGIN TRANSACTION
    Deploy->>DB: UPDATE workflows SET deployment_status='UNDEPLOYING'
    Deploy->>DB: INSERT deployment_history (action='UNDEPLOY', from_status='DEPLOYED', to_status='UNDEPLOYING')

    Deploy->>TriggerMgr: unregister_triggers(workflow_id)

    loop For each active trigger
        TriggerMgr->>TriggerMgr: stop_trigger()
        TriggerMgr->>TriggerMgr: cleanup_trigger_resources()
    end

    TriggerMgr-->>Deploy: All triggers stopped

    Deploy->>TriggerIndex: clear_workflow_triggers(workflow_id)
    TriggerIndex->>DB: DELETE FROM trigger_index WHERE workflow_id=?

    Deploy->>DB: UPDATE workflows SET deployment_status='UNDEPLOYED', undeployed_at=NOW()
    Deploy->>DB: UPDATE deployment_history SET completed_at=NOW(), to_status='UNDEPLOYED'
    Deploy->>DB: COMMIT TRANSACTION

    Deploy-->>Gateway: Undeployment successful
    Gateway-->>Client: 200 OK {status: 'UNDEPLOYED'}
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

## 7. Slack 集成架构

### 7.1. Slack App 配置

**必要权限和范围**：
- `app_mentions:read` - 监听 @bot 提及
- `channels:read` - 读取频道信息
- `chat:write` - 发送消息响应
- `im:read` - 读取私信
- `users:read` - 读取用户信息
- `files:read` - 读取共享文件
- `reactions:read` - 读取消息反应

**事件订阅设置**：
```json
{
  "event_subscriptions": {
    "url": "https://api.your-domain.com/slack/events",
    "bot_events": [
      "message.channels",
      "message.groups",
      "message.im",
      "app_mention",
      "reaction_added",
      "pin_added",
      "file_shared"
    ]
  },
  "slash_commands": [
    {
      "command": "/workflow",
      "url": "https://api.your-domain.com/slack/commands",
      "description": "Trigger workflows"
    }
  ]
}
```

### 7.2. Slack 事件路由系统

**全局事件处理器**：
```python
class SlackEventRouter:
    def __init__(self):
        self.workspace_triggers = {}  # {workspace_id: [triggers]}
        self.global_triggers = []     # 监听所有工作空间的触发器

    async def register_trigger(self, workspace_id: str = None, trigger: SlackTrigger):
        """注册 Slack 触发器到路由系统"""
        if workspace_id:
            if workspace_id not in self.workspace_triggers:
                self.workspace_triggers[workspace_id] = []
            self.workspace_triggers[workspace_id].append(trigger)
        else:
            self.global_triggers.append(trigger)

    async def route_event(self, event_data: dict) -> List[ExecutionResult]:
        """将Slack事件路由到匹配的触发器"""
        workspace_id = event_data.get("team_id")
        results = []

        # 处理工作空间特定的触发器
        if workspace_id in self.workspace_triggers:
            for trigger in self.workspace_triggers[workspace_id]:
                try:
                    if await trigger.process_slack_event(event_data):
                        result = await trigger._trigger_workflow({
                            "slack_event": event_data,
                            "workspace_id": workspace_id
                        })
                        results.append(result)
                except Exception as e:
                    logger.error(f"Slack trigger error: {e}")

        # 处理全局触发器
        for trigger in self.global_triggers:
            try:
                if await trigger.process_slack_event(event_data):
                    result = await trigger._trigger_workflow({
                        "slack_event": event_data,
                        "workspace_id": workspace_id
                    })
                    results.append(result)
            except Exception as e:
                logger.error(f"Global Slack trigger error: {e}")

        return results
```

### 7.3. Slack 事件处理流程

```mermaid
sequenceDiagram
    participant Slack as Slack Platform
    participant Gateway as API Gateway
    participant Router as SlackEventRouter
    participant SlackTrigger
    participant Engine as workflow_engine

    Slack->>Gateway: POST /slack/events (workspace event)
    Gateway->>Gateway: verify_slack_signature()
    Gateway->>Router: route_event(event_data)

    Router->>Router: find_matching_triggers(workspace_id, event_type)

    loop For each matching trigger
        Router->>SlackTrigger: process_slack_event(event_data)
        SlackTrigger->>SlackTrigger: apply_filters()

        alt Event matches all filters
            SlackTrigger->>SlackTrigger: extract_trigger_data()
            SlackTrigger->>Engine: POST /v1/workflows/{id}/execute
            Engine-->>SlackTrigger: 202 Accepted (execution_id)
        end

        SlackTrigger-->>Router: execution_result
    end

    Router-->>Gateway: List[ExecutionResult]
    Gateway-->>Slack: 200 OK
```

### 7.4. 快速事件匹配优化

使用简化的触发器索引表进行快速匹配：

```sql
-- 查找监听特定工作空间的触发器 (粗筛选)
SELECT workflow_id, trigger_config
FROM trigger_index
WHERE trigger_type = 'TRIGGER_SLACK'
  AND deployment_status = 'active'
  AND (index_key = %s OR index_key IS NULL OR index_key = '')
```

**优化策略**：
- **粗筛选**: `index_key` 只存储 `workspace_id` 用于快速过滤工作空间
- **精确匹配**: 从 `trigger_config` JSONB 字段中进行详细的事件类型、频道、用户等过滤
- **统一索引**: `idx_trigger_index_key` 支持所有触发器类型的快速查询
- **可扩展性**: 新增触发器类型不会增加额外字段

## 8. 安全考虑

### 8.1. 身份验证

- **Manual触发器**: JWT token验证
- **Webhook触发器**: 可选的API密钥或签名验证
- **Slack触发器**: Slack签名验证和Bot Token管理
- **Email触发器**: 安全的IMAP连接和凭据管理
- **内部服务**: HTTP API之间的服务间认证

### 8.2. 权限控制

- 基于用户角色的workflow触发权限
- Webhook端点的访问控制
- Slack工作空间和频道的访问控制
- 邮箱监控的权限隔离
- 审计日志记录所有触发事件

### 8.3. 数据安全

- 敏感配置加密存储
- 邮件内容的安全处理
- 网络传输TLS加密
- 分布式锁的安全实现

## 9. 监控与可观测性

### 9.1. 关键指标

- 部署的 Workflow 数量和状态分布
- 各类触发器的调度成功率和失败率
- 调度延迟和哈希分散效果
- 系统资源使用情况（CPU、内存、数据库连接）
- 邮件监控延迟和处理量

### 9.2. 日志结构

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
├── main.py                       # FastAPI应用入口
├── api/                          # REST API端点
│   ├── __init__.py
│   ├── deployment.py            # 部署管理API
│   ├── github.py                # GitHub webhook处理API
│   └── triggers.py              # 触发器管理API
├── services/                     # 业务服务层
│   ├── __init__.py
│   ├── deployment_service.py    # 部署服务
│   ├── trigger_manager.py       # 触发器管理器
│   ├── trigger_index_manager.py # 触发器索引管理
│   ├── event_router.py          # 事件路由服务
│   ├── lock_manager.py          # 分布式锁管理
│   └── notification_service.py  # Slack通知服务
├── triggers/                     # 触发器实现
│   ├── __init__.py
│   ├── base.py                  # 基础触发器类
│   ├── cron_trigger.py          # Cron触发器
│   ├── manual_trigger.py        # 手动触发器
│   ├── webhook_trigger.py       # Webhook触发器
│   ├── email_trigger.py         # 邮件触发器
│   └── github_trigger.py        # GitHub触发器
├── models/                       # 数据模型
│   ├── __init__.py
│   ├── database.py              # 数据库模型
│   ├── triggers.py              # 触发器模型
│   └── trigger_index.py         # 触发器索引模型
├── core/                         # 核心配置
│   ├── __init__.py
│   ├── config.py                # 配置管理
│   └── database.py              # 数据库连接
├── tests/                        # 单元测试
│   ├── __init__.py
│   ├── test_basic.py
│   └── test_notification.py
├── dependencies.py               # FastAPI依赖注入
├── pyproject.toml               # Python项目配置
├── start.sh                     # 启动脚本
├── test_trigger_system.py       # 触发器系统测试
├── README.md                    # 项目说明
├── TESTING_MODE.md              # 内测模式说明
└── Dockerfile                   # 容器化配置
```

### 9.3. 开发命令

```bash
# 安装依赖
uv sync

# 运行服务
python -m workflow_scheduler.main
# 或者使用启动脚本
./start.sh

# 运行测试
pytest tests/

# 测试触发器系统
python test_trigger_system.py

# 构建Docker镜像
docker build -t workflow-scheduler --platform linux/amd64 .
```

## 10. 触发器反查和匹配机制

### 10.1. 问题分析

**核心挑战**：当外部事件发生时（如GitHub webhook、邮件到达、定时任务触发），系统需要快速找到所有匹配的workflow触发器。

**现有问题**：
- Workflow定义中触发器配置分散，难以建立反向索引
- 事件过滤逻辑复杂（分支、路径、作者等），无法预计算
- 需要遍历所有部署的workflow才能找到匹配项，性能低下

### 10.2. 触发器索引设计

创建专门的 `trigger_index` 表来支持**所有类型触发器**的快速反查：

**优化后的简化设计**（已创建：`supabase/migrations/20250806200000_add_trigger_index_table.sql`）：
```sql
-- 创建触发器索引表 - 支持所有触发器类型的统一快速筛选
CREATE TABLE trigger_index (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL,
    trigger_type TEXT NOT NULL, -- 'TRIGGER_MANUAL', 'TRIGGER_CRON', 'TRIGGER_WEBHOOK', 'TRIGGER_SLACK', 'TRIGGER_EMAIL', 'TRIGGER_GITHUB'
    trigger_config JSONB NOT NULL, -- 触发器完整配置

    -- 统一的快速匹配字段 (每个触发器类型只用一个核心字段进行粗筛选)
    index_key TEXT, -- 统一的快速匹配字段
    -- TRIGGER_CRON: cron_expression
    -- TRIGGER_WEBHOOK: webhook_path
    -- TRIGGER_SLACK: workspace_id
    -- TRIGGER_EMAIL: email_address
    -- TRIGGER_GITHUB: repository_name

    -- 部署状态
    deployment_status TEXT DEFAULT 'active', -- 'active', 'testing', 'inactive'

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 统一的快速匹配索引 (支持所有触发器类型)
CREATE INDEX idx_trigger_index_key ON trigger_index(trigger_type, index_key)
    WHERE index_key IS NOT NULL;

-- 复合索引用于最常见的查询模式
CREATE INDEX idx_trigger_index_lookup ON trigger_index(trigger_type, index_key, deployment_status)
    WHERE index_key IS NOT NULL;
```

**简化设计的优势**：
- **可扩展性**：新增触发器类型不会导致字段爆炸，只需要确定一个核心筛选字段
- **统一索引**：所有触发器类型使用同一套索引结构，简化维护
- **粗筛选策略**：索引表只负责快速粗筛选，详细匹配由trigger_config中的完整配置处理
- **性能优化**：避免了多字段查询，使用单一index_key进行快速匹配
- **未来扩展**：每个新的触发器类型只需要定义一个主要的筛选维度

### 10.3. 快速匹配算法

**事件路由器 (EventRouter)**：
```python
class EventRouter:
    def __init__(self, db_session):
        self.db = db_session

    async def find_matching_workflows(self, event_type: str, event_data: dict) -> List[TriggerMatch]:
        """根据事件类型和数据快速找到匹配的触发器"""

        if event_type == "github":
            return await self._find_github_matches(event_data)
        elif event_type == "webhook":
            return await self._find_webhook_matches(event_data)
        elif event_type == "email":
            return await self._find_email_matches(event_data)
        elif event_type == "cron":
            return await self._find_cron_matches(event_data)
        elif event_type == "chat":
            return await self._find_chat_matches(event_data)
        elif event_type == "form":
            return await self._find_form_matches(event_data)
        elif event_type == "calendar":
            return await self._find_calendar_matches(event_data)

        return []

    async def _find_github_matches(self, event_data: dict) -> List[TriggerMatch]:
        """GitHub事件快速匹配 - 使用统一index_key进行粗筛选"""
        repository = event_data["repository"]["full_name"]

        # 1. 基础索引查询 - 快速粗筛选 (只匹配repository)
        base_query = """
        SELECT workflow_id, trigger_config
        FROM trigger_index
        WHERE trigger_type = 'TRIGGER_GITHUB'
          AND deployment_status = 'active'
          AND index_key = %s
        """

        candidates = await self.db.fetch_all(base_query, repository)

        # 2. 详细匹配 - 在trigger_config中进行精确过滤
        matches = []
        for candidate in candidates:
            trigger_config = candidate["trigger_config"]

            # 从完整配置中进行详细匹配
            if self._matches_github_filters(event_data, trigger_config):
                matches.append(TriggerMatch(
                    workflow_id=candidate["workflow_id"],
                    trigger_config=trigger_config,
                    match_score=self._calculate_match_score(event_data, trigger_config)
                ))

        return matches

    def _matches_github_filters(self, event_data: dict, config: dict) -> bool:
        """从trigger_config中应用GitHub详细过滤器"""
        # 事件类型过滤
        if event_data["event"] not in config.get("events", []):
            return False

        # 分支过滤 (如果适用)
        if "ref" in event_data and config.get("branches"):
            branch_name = event_data["ref"].replace("refs/heads/", "")
            if not any(fnmatch(branch_name, pattern) for pattern in config["branches"]):
                return False

        # 路径过滤 (如果适用)
        if config.get("paths") and "commits" in event_data:
            # 检查提交中的文件路径是否匹配
            if not self._matches_path_filters(event_data["commits"], config["paths"]):
                return False

        # 作者过滤
        if config.get("author_filter"):
            author = event_data.get("sender", {}).get("login", "")
            if not re.match(config["author_filter"], author):
                return False

        return True

    async def _find_webhook_matches(self, event_data: dict) -> List[TriggerMatch]:
        """Webhook路径直接匹配 - 使用统一index_key"""
        webhook_path = event_data["path"]

        query = """
        SELECT workflow_id, trigger_config
        FROM trigger_index
        WHERE trigger_type = 'TRIGGER_WEBHOOK'
          AND deployment_status = 'active'
          AND index_key = %s
        """

        results = await self.db.fetch_all(query, webhook_path)

        return [
            TriggerMatch(
                workflow_id=result["workflow_id"],
                trigger_config=result["trigger_config"],
                match_score=1.0  # 精确匹配
            )
            for result in results
        ]

    async def _find_slack_matches(self, event_data: dict) -> List[TriggerMatch]:
        """Slack事件快速匹配 - 使用workspace_id进行粗筛选"""
        workspace_id = event_data.get("team_id", "")

        # 1. 基础索引查询 - 快速粗筛选 (只匹配workspace)
        query = """
        SELECT workflow_id, trigger_config
        FROM trigger_index
        WHERE trigger_type = 'TRIGGER_SLACK'
          AND deployment_status = 'active'
          AND (index_key = %s OR index_key IS NULL OR index_key = '')
        """

        candidates = await self.db.fetch_all(query, workspace_id)

        # 2. 详细匹配 - 在trigger_config中进行精确过滤
        matches = []
        for candidate in candidates:
            trigger_config = candidate["trigger_config"]

            # 从完整配置中进行详细匹配
            if self._matches_slack_filters(event_data, trigger_config):
                matches.append(TriggerMatch(
                    workflow_id=candidate["workflow_id"],
                    trigger_config=trigger_config,
                    match_score=self._calculate_slack_match_score(event_data, trigger_config)
                ))

        return matches

    def _matches_slack_filters(self, event_data: dict, config: dict) -> bool:
        """从trigger_config中应用Slack详细过滤器"""
        # 事件类型过滤
        event_type = event_data.get("type", "")
        if config.get("event_types") and event_type not in config["event_types"]:
            return False

        # 频道过滤
        channel_id = event_data.get("channel", "")
        if config.get("channel_filter"):
            if not self._matches_channel_pattern(channel_id, config["channel_filter"]):
                return False

        # 用户过滤
        user_id = event_data.get("user", "")
        if config.get("user_filter"):
            if not re.match(config["user_filter"], user_id):
                return False

        # Bot过滤
        if config.get("ignore_bots", True) and event_data.get("bot_id"):
            return False

        # 提及过滤
        if config.get("mention_required", False):
            message_text = event_data.get("text", "")
            if not self._has_bot_mention(message_text):
                return False

        return True

### 10.4. 触发器注册管理

**TriggerIndexManager**：
```python
class TriggerIndexManager:
    def __init__(self, db_session):
        self.db = db_session

    async def register_workflow_triggers(self, workflow_id: str, workflow_spec: dict):
        """注册workflow的所有触发器到索引表"""

        # 清除旧的索引记录
        await self.db.execute(
            "DELETE FROM trigger_index WHERE workflow_id = %s",
            workflow_id
        )

        # 解析workflow中的触发器节点
        trigger_nodes = self._extract_trigger_nodes(workflow_spec)

        for trigger_node in trigger_nodes:
            await self._index_trigger(workflow_id, trigger_node)

    async def _index_trigger(self, workflow_id: str, trigger_node: dict):
        """将单个触发器添加到索引"""
        trigger_type = trigger_node["subtype"]  # 直接使用subtype，如 'TRIGGER_GITHUB'
        trigger_config = trigger_node["parameters"]

        index_data = {
            "workflow_id": workflow_id,
            "trigger_type": trigger_type,
            "trigger_config": trigger_config,
            "deployment_status": "active"
        }

        # 根据触发器类型填充统一的index_key字段 (粗筛选)
        if trigger_type == "TRIGGER_GITHUB":
            index_data["index_key"] = trigger_config["repository"]  # 只用repository进行粗筛选
        elif trigger_type == "TRIGGER_WEBHOOK":
            index_data["index_key"] = trigger_config.get("webhook_path", f"/webhook/{workflow_id}")
        elif trigger_type == "TRIGGER_SLACK":
            index_data["index_key"] = trigger_config.get("workspace_id", "")  # 只用workspace_id进行粗筛选
        elif trigger_type == "TRIGGER_EMAIL":
            index_data["index_key"] = trigger_config.get("email_filter", "")  # 使用邮箱地址或过滤器进行粗筛选
        elif trigger_type == "TRIGGER_CRON":
            index_data["index_key"] = trigger_config["cron_expression"]
        # TRIGGER_MANUAL 不需要index_key，因为不需要快速匹配

        await self.db.execute(
            """
            INSERT INTO trigger_index (
                workflow_id, trigger_type, trigger_config, index_key, deployment_status
            ) VALUES (
                %(workflow_id)s, %(trigger_type)s, %(trigger_config)s, %(index_key)s, %(deployment_status)s
            )
            """,
            index_data
        )

    def _extract_trigger_nodes(self, workflow_spec: dict) -> List[dict]:
        """从workflow定义中提取所有触发器节点"""
        trigger_nodes = []

        for node in workflow_spec.get("nodes", []):
            if node.get("node_type") == "TRIGGER_NODE":
                trigger_nodes.append(node)

        return trigger_nodes
```

## 11. 内测模式 - Slack 通知系统

### 11.1. 内测配置

当前 workflow_scheduler 处于**内测模式**，所有触发器在满足条件时会发送 Slack 通知而不是实际执行 workflow。

**环境变量配置**：
```bash
# Slack 通知配置
SLACK_BOT_TOKEN="xoxb-your-bot-token-here"  # Slack Bot Token
SLACK_TARGET_CHANNEL="#webhook-test"        # 默认通知频道
```

**Slack Bot 配置要求**：
- Bot Token 权限：`chat:write`, `channels:read`
- Bot 必须加入到目标频道
- 支持 Block Kit 格式的富文本消息

### 11.2. 内测触发器实现

**基础触发器类**（来自 `triggers/base.py`）：
```python
class BaseTrigger(ABC):
    def __init__(self, workflow_id: str, trigger_config: Dict[str, Any]):
        self.workflow_id = workflow_id
        self.config = trigger_config
        self._notification_service = NotificationService()

    async def _trigger_workflow(self, trigger_data: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """内测模式：发送 Slack 通知而不是执行 workflow"""

        if not self.enabled:
            return ExecutionResult(status="skipped", message="Trigger is disabled")

        try:
            # 发送 Slack 通知代替执行 workflow
            result = await self._notification_service.send_trigger_notification(
                workflow_id=self.workflow_id,
                trigger_type=self.trigger_type,
                trigger_data=trigger_data or {},
            )

            logger.info(f"✅ Trigger notification sent for workflow {self.workflow_id}")
            return result

        except Exception as e:
            logger.error(f"Error sending trigger notification: {str(e)}")
            return ExecutionResult(status="notification_error", message=str(e))

    async def _trigger_workflow_original(self, trigger_data: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """生产模式：实际调用 workflow_engine（当前被禁用）"""
        # 这是原始的 workflow 执行逻辑，内测期间暂时禁用
        # 生产部署时需要将此方法重命名为 _trigger_workflow
        pass
```

### 11.3. Slack 通知服务实现

**NotificationService**（来自 `services/notification_service.py`）：
```python
class NotificationService:
    def __init__(self):
        self.target_channel = "#webhook-test"
        self.slack_client = SlackWebClient(os.getenv("SLACK_BOT_TOKEN"))

    async def send_trigger_notification(self, workflow_id: str, trigger_type: str, trigger_data: Dict[str, Any]) -> ExecutionResult:
        """发送 Slack 通知"""
        try:
            logger.info(f"🔔 Trigger notification: {workflow_id} triggered by {trigger_type}")

            if self.slack_client:
                success = await self._send_slack_notification(workflow_id, trigger_type, trigger_data)

                if success:
                    logger.info(f"💬 Slack notification sent to {self.target_channel}")
                    return ExecutionResult(status="notified_slack", message=f"Slack notification sent for {trigger_type} trigger")
                else:
                    logger.warning(f"💬 Slack notification failed for workflow {workflow_id}")
                    return ExecutionResult(status="notified_log_only", message="Slack failed, logged trigger")
            else:
                logger.info(f"📝 Logged trigger notification (Slack not configured)")
                return ExecutionResult(status="notified_log_only", message="Logged trigger (Slack not configured)")

        except Exception as e:
            logger.error(f"Failed to send trigger notification: {e}")
            return ExecutionResult(status="notification_failed", message=str(e))

    async def _send_slack_notification(self, workflow_id: str, trigger_type: str, trigger_data: Dict[str, Any]) -> bool:
        """使用 Slack Block Kit 发送富格式通知"""
        try:
            display_trigger_type = trigger_type.replace("TRIGGER_", "").title()
            blocks = self._generate_slack_blocks(workflow_id, display_trigger_type, trigger_data)
            fallback_text = f"🚀 Workflow {workflow_id} triggered by {display_trigger_type}"

            response = self.slack_client.send_message(
                channel=self.target_channel,
                text=fallback_text,
                blocks=blocks
            )

            return response.get("ok", False)

        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")
            return False

    def _generate_slack_blocks(self, workflow_id: str, display_trigger_type: str, trigger_data: Dict[str, Any]) -> list:
        """生成 Slack Block Kit 消息块"""
        blocks = [
            SlackBlockBuilder.header("🚀 Workflow Triggered"),
            SlackBlockBuilder.section(
                f"*Workflow ID:* `{workflow_id}`\n*Trigger Type:* {display_trigger_type}\n*Time:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
            ),
        ]

        # 根据触发器类型添加详细信息
        if "GITHUB" in workflow_id.upper():
            event_type = trigger_data.get("event_type", "Unknown")
            payload = trigger_data.get("payload", {})
            repository = payload.get("repository", {}).get("full_name", "Unknown")
            sender = payload.get("sender", {}).get("login", "Unknown")

            blocks.append(SlackBlockBuilder.section(
                f"*GitHub Event:* {event_type}\n*Repository:* {repository}\n*User:* @{sender}"
            ))

        elif "WEBHOOK" in workflow_id.upper():
            method = trigger_data.get("method", "Unknown")
            path = trigger_data.get("path", "Unknown")
            blocks.append(SlackBlockBuilder.section(
                f"*HTTP Method:* {method}\n*Path:* `{path}`"
            ))

        # 添加测试模式说明
        blocks.extend([
            SlackBlockBuilder.divider(),
            SlackBlockBuilder.section("💡 *Note:* This is a test notification. The actual workflow was not executed."),
            SlackBlockBuilder.context([
                SlackBlockBuilder.text_element("🔧 Workflow Scheduler | 📍 workflow_scheduler service")
            ])
        ])

        return blocks
```

### 11.4. 切换到生产模式

要启用实际的 workflow 执行，需要修改 `triggers/base.py`：

```python
# 1. 将当前的 _trigger_workflow 方法重命名为 _trigger_workflow_testing
async def _trigger_workflow_testing(self, trigger_data: Optional[Dict[str, Any]] = None) -> ExecutionResult:
    # 当前的 Slack 通知逻辑...

# 2. 将 _trigger_workflow_original 方法重命名为 _trigger_workflow
async def _trigger_workflow(self, trigger_data: Optional[Dict[str, Any]] = None) -> ExecutionResult:
    # 原始的 workflow_engine 调用逻辑...

# 3. 移除 NotificationService 依赖
# 从 BaseTrigger.__init__ 中删除:
# self._notification_service = NotificationService()
```

### 11.5. 监控和测试

**健康检查**：
```bash
# 服务健康检查
curl http://localhost:8003/health

# Slack 连接状态
curl http://localhost:8003/api/v1/triggers/health
```

**测试触发器**：
```bash
# 手动触发
curl -X POST http://localhost:8003/api/v1/triggers/workflows/test-workflow/manual \
  -H "Content-Type: application/json" \
  -d '{"confirmation": true}'

# Webhook 触发
curl -X POST http://localhost:8000/api/v1/public/webhook/test-workflow \
  -H "Content-Type: application/json" \
  -d '{"event": "test", "data": "sample"}'
```

**日志监控**：
```bash
# 查看触发器日志
tail -f logs/workflow_scheduler.log

# 查看 Slack 通知状态
grep "Slack notification" logs/workflow_scheduler.log
```

### 11.6. 当前实现状态

根据 `TESTING_MODE.md` 和现有代码，当前实现包含：

1. **✅ 已实现**：
   - Slack 通知服务 (`NotificationService`)
   - 基础触发器的内测模式 (`BaseTrigger._trigger_workflow`)
   - 富格式 Slack 消息 (Block Kit)
   - 健康检查和状态监控
   - 所有触发器类型支持 (Cron, Manual, Webhook, GitHub, Email)

2. **📝 配置要求**：
   ```bash
   # .env 文件配置
   SLACK_BOT_TOKEN=xoxb-your-bot-token-here
   WORKFLOW_ENGINE_URL=http://workflow-engine:8002
   ```

3. **🔧 生产模式切换**：
   - 当前 `_trigger_workflow` = 内测模式 (Slack 通知)
   - 当前 `_trigger_workflow_original` = 生产模式 (调用 workflow_engine)
   - 切换：重命名方法并移除 NotificationService 依赖

### 11.7. 性能优化建议

**索引查询优化**：
- 使用数据库连接池减少连接开销
- 预计算常用过滤器组合
- 使用Redis缓存热点查询结果
- 批量处理多个事件

**匹配算法优化**：
```python
class OptimizedEventRouter(EventRouter):
    def __init__(self, db_session, redis_client):
        super().__init__(db_session)
        self.redis = redis_client
        self.cache_ttl = 300  # 5分钟缓存

    async def find_matching_workflows(self, event_type: str, event_data: dict) -> List[TriggerMatch]:
        # 构造缓存键
        cache_key = self._build_cache_key(event_type, event_data)

        # 尝试从缓存获取
        cached_result = await self.redis.get(cache_key)
        if cached_result:
            return json.loads(cached_result)

        # 缓存未命中，执行查询
        matches = await super().find_matching_workflows(event_type, event_data)

        # 缓存结果
        await self.redis.setex(
            cache_key,
            self.cache_ttl,
            json.dumps([m.to_dict() for m in matches])
        )

        return matches
```

这个设计完整地集成了现有的 Slack 通知系统，确保与当前实现保持一致。
