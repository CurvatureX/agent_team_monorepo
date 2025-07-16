# 工具集成和API适配最终共识文档

## 需求定义

### 1. 明确的需求描述

**核心目标：** 完善现有工作流引擎中的 `TOOL_NODE` 实现，实现真实的外部API集成能力。

**功能范围：**
- ✅ 替换 `ToolNodeExecutor` 中的模拟方法为真实API调用
- ✅ 实现OAuth2凭证管理系统（基于已有oauth_tokens表）
- ✅ 集成4个核心外部服务：Google Calendar、GitHub、Slack、HTTP
- ✅ 在API Gateway中实现OAuth2授权流程
- ✅ 提供统一的工具调用适配器接口
- ✅ GitHub集成支持仓库操作、Issue管理、PR创建、文件操作

**明确不做的内容：**
- ❌ 不涉及前端UI工具配置界面开发
- ❌ 不处理工作流执行引擎的基础框架修改
- ❌ 不涉及AI Agent节点的智能决策逻辑
- ❌ 不处理数据库schema的结构性变更
- ❌ MVP阶段不实现团队级别的API密钥共享

### 2. 用户故事和验收标准

#### 用户故事1：AI Agent创建Google Calendar事件
**作为** 工作流用户  
**我希望** AI Agent能够自动创建Google Calendar事件  
**以便于** 自动化我的日程管理

**验收标准：**
- [ ] 用户可以通过OAuth2授权Google Calendar访问权限
- [ ] AI Agent可以在指定日历中创建事件（包含标题、时间、描述）
- [ ] 支持创建、查询、更新、删除事件的完整CRUD操作
- [ ] 支持多日历操作（通过calendar_id参数）
- [ ] API调用失败时有明确的错误信息和重试机制

#### 用户故事2：工作流自动发送Slack消息
**作为** 工作流用户  
**我希望** 工作流可以自动发送Slack消息通知  
**以便于** 实时通知团队重要信息

**验收标准：**
- [ ] 用户可以通过OAuth2授权Slack访问权限
- [ ] 工作流可以向指定频道发送纯文本消息
- [ ] 支持基础markdown格式：`*bold*`, `_italic_`, `~strikethrough~`, ``` `code` ```
- [ ] 支持Slack特有格式：`<@USER_ID>` mentions和 `<#CHANNEL_ID>` channel links
- [ ] 支持链接格式：`<https://example.com|链接文本>`

#### 用户故事3：GitHub仓库集成
**作为** 工作流用户  
**我希望** 可以自动化GitHub仓库操作  
**以便于** 实现代码管理和协作流程自动化

**验收标准：**
- [ ] 用户可以通过OAuth2授权GitHub访问权限
- [ ] 支持创建Issue和Pull Request
- [ ] 支持获取仓库信息和文件内容
- [ ] 支持创建和更新文件
- [ ] 支持基础的仓库搜索和操作
- [ ] API调用失败时有明确的错误信息和重试机制

#### 用户故事4：HTTP API调用集成
**作为** 工作流用户  
**我希望** 可以调用任意HTTP API  
**以便于** 集成现有系统和服务

**验收标准：**
- [ ] 支持GET、POST、PUT、DELETE等HTTP方法
- [ ] 支持3种认证方式：Bearer Token、API Key（Header/Query）、Basic Auth
- [ ] 支持自定义请求头和请求体
- [ ] 连接超时5秒，读取超时30秒
- [ ] 响应大小限制10MB，并发限制每用户10个请求
- [ ] 支持JSON响应的自动解析

#### 用户故事5：凭证安全管理
**作为** 系统管理员  
**我希望** 所有API凭证都被安全存储和管理  
**以便于** 确保系统安全性和合规性

**验收标准：**
- [ ] 所有敏感凭证使用Fernet对称加密存储
- [ ] 支持OAuth2 token的自动刷新机制
- [ ] 凭证按用户隔离，确保权限边界
- [ ] 基础审计日志记录凭证的创建、更新、删除操作
- [ ] 凭证过期时工作流暂停并提供明确提示

## 技术方案

### 3. 技术实现方案

#### 3.1 加密和凭证管理
```python
# 加密实现 - workflow_engine/core/encryption.py
from cryptography.fernet import Fernet
import base64, hashlib, os

class CredentialEncryption:
    def __init__(self):
        key_source = os.getenv("CREDENTIAL_ENCRYPTION_KEY", "default-dev-key")
        self.key = base64.urlsafe_b64encode(hashlib.sha256(key_source.encode()).digest())
        self.fernet = Fernet(self.key)
    
    def encrypt(self, data: str) -> str:
        return self.fernet.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        return self.fernet.decrypt(encrypted_data.encode()).decode()
```

#### 3.2 数据库模型扩展
```python
# 基于已有oauth_tokens表的使用方式
# 表结构：
# - user_id: UUID (外键关联users表)
# - integration_id: VARCHAR (关联integrations表)  
# - provider: VARCHAR ('google_calendar', 'slack', 'http_bearer', 'http_apikey', 'http_basic')
# - access_token: TEXT (Fernet加密)
# - refresh_token: TEXT (Fernet加密，使用不同盐值)
# - credential_data: JSONB (存储其他认证信息，敏感部分加密)
```

#### 3.3 API客户端实现
```python
# Google Calendar客户端 - workflow_engine/clients/google_calendar_client.py
class GoogleCalendarClient:
    def __init__(self, credentials: OAuth2Credential):
        self.credentials = credentials
        self.base_url = "https://www.googleapis.com/calendar/v3"
    
    async def create_event(self, calendar_id: str, event_data: dict) -> dict:
        # 实现事件创建逻辑，包含token刷新处理
        pass
    
    async def list_events(self, calendar_id: str, time_min: str, time_max: str) -> List[dict]:
        # 实现事件查询逻辑
        pass

# Slack客户端 - workflow_engine/clients/slack_client.py  
class SlackClient:
    def __init__(self, credentials: OAuth2Credential):
        self.credentials = credentials
        self.base_url = "https://slack.com/api"
    
    async def send_message(self, channel: str, text: str, **kwargs) -> dict:
        # 实现消息发送，支持markdown格式转换
        pass

# HTTP客户端 - workflow_engine/clients/http_client.py
class HTTPClient:
    def __init__(self, auth_config: dict):
        self.auth_config = auth_config
        self.timeout = httpx.Timeout(connect=5.0, read=30.0)
    
    async def request(self, method: str, url: str, **kwargs) -> dict:
        # 实现通用HTTP请求，支持3种认证方式
        pass

# GitHub客户端 - workflow_engine/clients/github_client.py
class GitHubClient:
    def __init__(self, credentials: OAuth2Credential):
        self.credentials = credentials
        self.base_url = "https://api.github.com"
    
    async def create_issue(self, repo: str, title: str, body: str) -> dict:
        # 实现Issue创建逻辑
        pass
    
    async def create_pull_request(self, repo: str, title: str, head: str, base: str, body: str) -> dict:
        # 实现PR创建逻辑
        pass
    
    async def get_repository_info(self, repo: str) -> dict:
        # 实现仓库信息获取
        pass
    
    async def create_file(self, repo: str, path: str, content: str, message: str) -> dict:
        # 实现文件创建
        pass
```

#### 3.4 工具节点执行器改进
```python
# 替换tool_node.py中的模拟实现
class ToolNodeExecutor(BaseNodeExecutor):
    async def _execute_calendar_tool(self, context, logs, start_time):
        # 获取加密凭证
        credentials = await self._get_credentials(context, "google_calendar")
        client = GoogleCalendarClient(credentials)
        
        # 执行真实API调用
        operation = context.get_parameter("operation")
        if operation == "create_event":
            return await client.create_event(
                context.get_parameter("calendar_id", "primary"),
                context.get_parameter("event_data")
            )
        # ... 其他操作
    
    async def _execute_http_tool(self, context, logs, start_time):
        # 替换_simulate_http_request为真实请求
        auth_config = context.get_parameter("auth_config", {})
        client = HTTPClient(auth_config)
        
        return await client.request(
            method=context.get_parameter("method", "GET"),
            url=context.get_parameter("url"),
            headers=context.get_parameter("headers", {}),
            json=context.get_parameter("body")
        )
    
    async def _execute_github_tool(self, context, logs, start_time):
        # GitHub工具执行逻辑
        credentials = await self._get_credentials(context, "github")
        client = GitHubClient(credentials)
        
        operation = context.get_parameter("operation")
        if operation == "create_issue":
            return await client.create_issue(
                context.get_parameter("repo"),
                context.get_parameter("title"),
                context.get_parameter("body", "")
            )
        elif operation == "create_pull_request":
            return await client.create_pull_request(
                context.get_parameter("repo"),
                context.get_parameter("title"),
                context.get_parameter("head"),
                context.get_parameter("base"),
                context.get_parameter("body", "")
            )
        # ... 其他操作
```

### 4. 系统集成方案

#### 4.1 gRPC服务扩展
```protobuf
// shared/proto/engine/workflow_service.proto 扩展
service WorkflowService {
  // 现有方法...
  
  // 凭证管理方法
  rpc StoreOAuth2Credential(StoreCredentialRequest) returns (StoreCredentialResponse);
  rpc RefreshOAuth2Token(RefreshTokenRequest) returns (RefreshTokenResponse);
  rpc GetCredential(GetCredentialRequest) returns (GetCredentialResponse);
  rpc DeleteCredential(DeleteCredentialRequest) returns (DeleteCredentialResponse);
}

message StoreCredentialRequest {
  string user_id = 1;
  string provider = 2;
  string integration_id = 3;
  OAuth2Credential credential = 4;
}

message RefreshTokenRequest {
  string user_id = 1;
  string provider = 2;
  string integration_id = 3;
}
```

#### 4.2 API Gateway OAuth2端点
```python
# api-gateway/routers/oauth.py
@router.get("/oauth2/authorize/{provider}")
async def generate_auth_url(provider: str, user_id: str):
    # 生成OAuth2授权URL
    # 状态管理使用Redis存储state参数
    pass

@router.get("/oauth2/callback/{provider}")  
async def oauth_callback(provider: str, code: str, state: str):
    # 处理OAuth2回调
    # 调用workflow_engine的gRPC接口存储凭证
    pass
```

#### 4.3 错误处理和重试机制
```python
# workflow_engine/core/retry.py
class APIRetryPolicy:
    def __init__(self):
        self.max_retries = 3
        self.backoff_delays = [2, 4, 8]  # 指数退避
    
    async def execute_with_retry(self, func, *args, **kwargs):
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except TokenExpiredError:
                # 尝试刷新token
                await self._refresh_token()
                if attempt < self.max_retries:
                    continue
                else:
                    # 降级：暂停工作流，通知用户重新授权
                    raise WorkflowSuspendError("Token refresh failed, manual reauthorization required")
            except RateLimitError:
                if attempt < self.max_retries:
                    await asyncio.sleep(self.backoff_delays[attempt])
                    continue
                else:
                    raise
```

## 约束边界

### 5. 明确的边界和限制

#### 5.1 功能边界
**包含的功能：**
- Google Calendar：创建、查询、更新、删除事件，支持多日历（通过calendar_id）
- GitHub：创建Issue、创建PR、获取仓库信息、文件创建和更新、基础搜索
- Slack：发送消息（纯文本+基础markdown），支持mentions和channel links
- HTTP工具：GET/POST/PUT/DELETE，支持Bearer Token/API Key/Basic Auth三种认证
- OAuth2授权：完整的授权码流程，自动token刷新，安全凭证存储

**明确排除的功能：**
- Google Calendar：不支持recurring events、attendees管理、日历权限管理
- GitHub：不支持高级CI/CD操作、组织管理、权限管理、Webhooks
- Slack：不支持interactive buttons、file upload、channel management
- 团队协作：不支持凭证共享，但预留team_id扩展

#### 5.2 技术约束
**性能限制：**
- API调用响应时间：< 5秒（连接超时5秒，读取超时30秒）
- 并发限制：每用户10个并发请求
- 响应大小限制：10MB
- 重试策略：最多3次，指数退避（2s, 4s, 8s）

**安全约束：**
- 使用Fernet对称加密存储凭证
- 加密密钥通过环境变量管理
- 凭证按user_id严格隔离
- OAuth2 token自动刷新，失败时暂停工作流

**兼容性约束：**
- 必须与现有NodeExecutor接口兼容
- 必须支持现有的连接系统（AI_TOOL连接类型）
- 输出格式必须符合NodeExecutionResult结构
- 使用现有的错误处理和重试机制

#### 5.3 资源限制
**依赖管理：**
- 使用uv进行依赖管理：`uv sync --frozen`
- 新增依赖：`cryptography>=41.0.0`, `httpx>=0.25.0`
- 不使用官方SDK，基于HTTP客户端实现

**环境要求：**
- Python 3.11+
- PostgreSQL（已有oauth_tokens表）
- Redis（OAuth2状态管理）
- 环境变量：`CREDENTIAL_ENCRYPTION_KEY`

### 6. 整体验收标准

#### 6.1 功能验收标准
**基础功能验收：**
- [ ] HTTP工具支持3种认证方式，成功调用外部API
- [ ] Google Calendar完整CRUD操作，支持多日历
- [ ] Slack消息发送支持基础markdown格式
- [ ] OAuth2授权流程完整，包含授权、回调、token存储

**安全验收标准：**
- [ ] 所有敏感凭证使用Fernet加密存储
- [ ] 凭证按用户隔离，无跨用户访问
- [ ] OAuth2 token自动刷新，失败时合理降级
- [ ] 基础审计日志记录凭证操作

**性能验收标准：**
- [ ] API调用响应时间 < 5秒
- [ ] 支持并发调用（最少10个并发请求）
- [ ] 错误重试机制正常工作
- [ ] 系统稳定性不受API调用影响

#### 6.2 集成验收标准
**系统集成验收：**
- [ ] 与现有gRPC架构无缝集成
- [ ] API Gateway OAuth2端点正常工作
- [ ] workflow_engine凭证管理服务稳定运行
- [ ] 现有工作流执行不受影响

**开发验收标准：**
- [ ] 代码遵循现有项目规范和架构模式
- [ ] 单元测试覆盖核心功能
- [ ] 文档更新完整，包含使用示例
- [ ] 部署流程与现有系统一致

## 风险管控

### 7. 不确定性已全部解决

#### 7.1 已明确的技术决策
| 决策点 | 最终决策 | 决策依据 |
|-------|---------|----------|
| 加密算法 | Fernet对称加密 | 参考n8n设计，简单安全，适合应用层加密 |
| 密钥管理 | 环境变量 | 符合现有项目配置模式，便于部署管理 |
| 数据库设计 | 使用已有oauth_tokens表 | 避免schema变更，复用现有基础设施 |
| 并发控制 | 数据库行级锁 | MVP阶段简单可靠，SELECT FOR UPDATE |
| 系统集成 | 扩展gRPC服务 | 遵循现有架构模式，最小化变更影响 |
| 错误处理 | 分层处理机制 | 自动重试+用户通知+降级策略 |
| 团队功能 | MVP不实现 | 预留team_id字段，降低初期复杂度 |
| 审计需求 | 基础审计 | 记录关键安全事件，满足基本合规要求 |

#### 7.2 技术风险已缓解
| 风险点 | 缓解措施 | 监控指标 |
|-------|---------|----------|
| 凭证泄露 | Fernet加密+权限隔离+审计日志 | 异常访问次数、失败登录率 |
| API调用失败 | 重试机制+降级策略+用户通知 | API成功率、响应时间、错误率 |
| 并发竞态 | 数据库锁+分布式状态管理 | 锁等待时间、死锁次数 |
| token过期 | 自动刷新+失败处理+工作流暂停 | token刷新成功率、工作流暂停次数 |
| 性能影响 | 超时控制+并发限制+资源监控 | 响应时间、CPU使用率、内存占用 |

#### 7.3 交付里程碑
| 里程碑 | 交付内容 | 验收标准 |
|-------|---------|----------|
| M1 | 基础凭证管理+HTTP工具 | 加密存储+HTTP三种认证 |
| M2 | Google Calendar集成 | 完整CRUD+OAuth2流程 |  
| M3 | GitHub集成 | Issue/PR创建+仓库操作 |
| M4 | Slack集成+功能完善 | 消息发送+审计日志 |
| M5 | 系统集成测试+文档 | 端到端测试+部署验证 |

#### 7.4 质量保证
**代码质量：**
- 遵循现有项目的代码规范和架构模式
- 单元测试覆盖率 > 80%
- 集成测试验证端到端功能
- 代码审查确保安全性和可维护性

**部署质量：**
- 使用现有的uv依赖管理
- 环境变量配置标准化
- Docker容器化部署
- 渐进式发布，降低影响

---

## 总结

本共识文档明确了工具集成和API适配的完整实现方案，所有技术决策已确定，功能边界清晰，风险已识别并制定缓解措施。项目具备立即开始实施的条件，预计4周内完成MVP版本交付。 