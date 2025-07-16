# 工具集成和API适配需求澄清文档

## 边界确认

### 1. 功能边界确认

**做什么：**
- ✅ 实现 `TOOL_NODE` 类型的基础框架和执行器
- ✅ 集成 4 个核心外部服务（Google Calendar、GitHub、Slack、HTTP）
- ✅ 实现 OAuth2 授权框架和凭证管理系统
- ✅ 提供统一的工具调用适配器接口
- ✅ 支持现有技术架构中定义的连接类型（`AI_TOOL` 连接）
- ✅ GitHub集成包含基础仓库操作（创建Issue、PR、文件操作）

**不做什么：**
- ❌ 不涉及前端UI工具配置界面开发
- ❌ 不处理工作流执行引擎的修改（已有框架）
- ❌ 不涉及AI Agent节点的智能决策逻辑
- ❌ 不处理数据库schema的变更

### 2. 非功能性需求

**性能要求：**
- API调用响应时间 < 5秒
- 支持并发调用（最少10个并发请求）
- OAuth token自动刷新机制

**安全要求：**
- 凭证加密存储（使用现有PostgreSQL的JSONB加密）
- OAuth2标准实现，支持token过期检测
- API密钥安全管理，不在日志中泄露

**可维护性要求：**
- 工具插件架构，易于扩展新的API集成
- 统一的错误处理和重试机制
- 完整的执行日志和调试信息

## 需求理解

### 1. 我对需求的理解（基于澄清后）

经过详细澄清，现在明确这个任务是要完善现有工作流引擎中的 `TOOL_NODE` 实现。当前系统已有：

- ✅ **基础框架**：`workflow_engine/nodes/tool_node.py` 已定义了基本结构
- ✅ **数据模型**：protobuf中已定义了OAuth2Credential、CredentialConfig等结构  
- ✅ **执行系统**：NodeExecutor基类和工厂模式已完成
- ✅ **数据库支持**：已有`oauth_tokens`表存储凭证，nodes表支持parameters的JSONB存储
- ✅ **集成架构**：API Gateway + gRPC服务的分层设计已确定

**明确的核心任务**：
1. 完善 `ToolNodeExecutor` 的具体实现，替换现有的模拟方法为真实API调用
2. 基于已有`oauth_tokens`表实现OAuth2凭证管理（应用层加密）
3. 在API Gateway中实现OAuth2授权流程（URL生成和回调处理）
4. 实现4个API客户端：Google Calendar（完整CRUD）、Slack（消息+基础markdown）、HTTP（3种认证）

### 2. 我对现有项目的理解

**技术栈：**
- 后端：Python + FastAPI + PostgreSQL + Redis
- 架构：基于protobuf的微服务架构，支持gRPC通信
- 执行引擎：工厂模式的节点执行器，支持8种核心节点类型
- 数据存储：PostgreSQL存储工作流定义，Redis用于缓存

**架构约束：**
- 必须遵循现有的NodeExecutor接口规范
- 必须支持现有的连接系统（ConnectionsMap）
- 必须与现有的错误处理和重试机制兼容
- 输出格式必须符合NodeExecutionResult结构

**接口规范：**
```python
class BaseNodeExecutor:
    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult
    def validate(self, node: Any) -> List[str]
    def get_supported_subtypes(self) -> List[str]
```

### 3. 核心业务逻辑分析

**工具节点执行流程：**
1. 接收上游节点的输入数据（通过`AI_TOOL`连接）
2. 从节点配置中获取API调用参数
3. 从凭证管理系统获取认证信息
4. 执行API调用（Google Calendar/GitHub/Slack/HTTP）
5. 处理API响应，转换为标准输出格式
6. 返回执行结果给下游节点

**认证授权流程：**
1. 初次配置时通过OAuth2获取authorization code
2. 交换access token和refresh token
3. 加密存储token到数据库credentials字段
4. 执行时自动检测token有效性
5. 必要时自动刷新token

### 4. 用户场景和使用流程

**场景1：AI Agent调用Google Calendar**
```
AI Agent Node → (AI_TOOL连接) → Tool Node (Google Calendar) → 返回日程数据
```

**场景2：工作流自动发送Slack消息**
```
触发器 → 数据处理 → Tool Node (Slack) → 发送通知完成
```

**场景3：GitHub仓库操作**
```
用户输入 → AI分析 → Tool Node (GitHub) → 创建Issue/PR
```

## 现有代码分析和需要实现的接口

### 1. 当前Python架构现状

**✅ 已有基础框架：**
- `BaseNodeExecutor` 抽象基类（`workflow_engine/nodes/base.py`）
- `ToolNodeExecutor` 具体实现（`workflow_engine/nodes/tool_node.py`）
- PostgreSQL数据库schema（`database/schema.sql`）
- protobuf定义（`shared/proto/engine/integration.proto`）
- 现有4个子类型支持：MCP、CALENDAR、EMAIL、HTTP

**❌ 需要实现的核心接口：**

#### 1.1 ToolNodeExecutor中需要从模拟改为真实实现的方法：

```python
# 需要替换的模拟方法（现在都返回假数据）：
class ToolNodeExecutor(BaseNodeExecutor):
    def _execute_calendar_tool(self, context, logs, start_time)  # 真实Google Calendar API调用
    def _create_calendar_event(self, context, provider)         # 替换模拟实现
    def _list_calendar_events(self, context, provider)          # 替换模拟实现
    def _update_calendar_event(self, context, provider)         # 替换模拟实现
    def _delete_calendar_event(self, context, provider)         # 替换模拟实现
    
    def _execute_email_tool(self, context, logs, start_time)    # Slack API真实调用
    def _send_email(self, context, provider)                    # 替换模拟实现（实际是Slack消息）
    
    def _execute_http_tool(self, context, logs, start_time)     # 真实HTTP请求
    def _simulate_http_request(self, url, method, headers, auth, data)  # 替换为真实请求
    
    # 新增需要实现的方法：
    def _get_credentials(self, context, service_type)           # 从数据库获取凭证
    def _refresh_oauth_token(self, credential_id)               # OAuth2 token刷新
    def _handle_api_error(self, error, retry_count)             # 统一错误处理
```

#### 1.2 需要新增的凭证管理类：

```python
# 需要创建的新类（参考integration.proto）
class CredentialManager:
    def get_credential(self, user_id: str, service: str) -> Optional[CredentialConfig]
    def store_credential(self, user_id: str, service: str, credential: OAuth2Credential)
    def refresh_oauth_token(self, credential_id: str) -> bool
    def validate_credential(self, credential: CredentialConfig) -> bool

class OAuth2Handler:
    def generate_auth_url(self, service: str, user_id: str, scopes: List[str]) -> str
    def exchange_code_for_tokens(self, service: str, code: str, state: str) -> OAuth2Credential
    def refresh_access_token(self, refresh_token: str, service: str) -> OAuth2Credential
```

#### 1.3 需要新增的API适配器：

```python
# 需要创建的API客户端类
class GoogleCalendarClient:
    def __init__(self, credentials: OAuth2Credential)
    def create_event(self, calendar_id: str, event: dict) -> dict
    def list_events(self, calendar_id: str, time_min: str, time_max: str) -> List[dict]
    def update_event(self, calendar_id: str, event_id: str, event: dict) -> dict
    def delete_event(self, calendar_id: str, event_id: str) -> bool

class SlackClient:
    def __init__(self, credentials: OAuth2Credential)
    def send_message(self, channel: str, text: str, **kwargs) -> dict
    def create_channel(self, name: str) -> dict
    def upload_file(self, channels: str, file_path: str) -> dict

class GitHubClient:
    def __init__(self, credentials: OAuth2Credential)
    def create_issue(self, repo: str, title: str, body: str) -> dict
    def create_pull_request(self, repo: str, title: str, head: str, base: str) -> dict
    def get_repository_info(self, repo: str) -> dict
    def create_file(self, repo: str, path: str, content: str, message: str) -> dict
    def update_file(self, repo: str, path: str, content: str, message: str, sha: str) -> dict
```

### 2. 具体实现疑问澄清

**🔧 现有数据库schema的使用方式：**  已有oauth_tokens表使用就行，其余库表自行评估使用方式，有可以复用的尽量复用
- 现有`integrations`表已支持`credential_config JSONB`字段，是否直接使用？尽量使用oauth_tokens表
- 现有`nodes`表的`credentials JSONB`字段如何与`integrations`表关联？
- 是否需要新增`oauth_tokens`表或使用现有字段？ 已有oauth_tokens

**🔧 凭证存储的具体实现方式：**  mvp版本简洁明确地实现就行
- OAuth2Credential应该存储在哪个表？（integrations表 vs 新建表） oauth_tokens表
- 凭证加密方式：使用SQLAlchemy的加密字段还是应用层加密？ 应用层加密
- refresh_token的安全存储策略？   refresh_token分离存储

**🔧 NodeExecutionContext的凭证获取：**
```python
# 现有接口：context.get_credential(key, default)
# 问题：凭证应该从哪里来？
# 1. 从context.credentials直接获取（当前方式）
# 2. 从数据库根据service_type动态获取
# 3. 混合方式：context提供service标识，实时查询数据库
```

**🔧 OAuth2授权流程的集成点：**
- 授权URL生成是否需要在API Gateway中暴露HTTP端点？是，需要在API Gateway暴露
- 回调处理是否在workflow_engine内部还是api-gateway？回调处理在API Gateway，但调用workflow_engine存储
- 与现有gRPC架构的集成方式？  推荐按照项目现有架构设计

**🔧 错误处理和重试的具体策略：**
- 使用现有的`RetryPolicy`（max_tries, wait_between_tries）配置？  是，复用现有RetryPolicy，可以扩展
- API速率限制时是否需要动态调整重试间隔？  是，需要动态调整
- 认证失败时的自动token刷新流程？  是，需要自动刷新

### 3. API功能范围确认

**🎯 Google Calendar集成的最小可行功能：**
- ✅ 需要实现：create_event, list_events（基础秘书功能）  是，需要实现
- ❓ 是否需要：update_event, delete_event（完整CRUD） 需要
- ❓ 是否支持：多日历、recurring events、attendees管理  多日历：支持，通过calendar_id参数，其他不支持

**🎯 Slack集成的功能边界：**
- ✅ 需要实现：send_message（基础通知功能） 需要
- ❓ 是否需要：interactive buttons, file upload, channel management  暂不支持
- ❓ 消息格式：纯文本 vs rich formatting vs blocks  纯文本：必须支持，Rich formatting：支持基础markdown

**🎯 HTTP工具的安全限制：**
- ❓ 是否需要URL白名单机制？  支持配置，先默认都允许访问
- ❓ 支持的认证方式：Bearer Token + Basic Auth + API Key？ MVP支持3种：Bearer Token（主要）、Basic Auth（兼容性）、API Key（Header或Query参数）
- ❓ 超时和并发限制策略？  需要限制：连接超时：5秒
读取超时：30秒
并发限制：每用户10个并发请求
响应大小限制：10MB

### 4. 技术选型确认

**🔧 实现方案（基于现有Python架构）：**
- 使用requests/httpx作为HTTP客户端（不使用官方SDK）
- 基于现有PostgreSQL + SQLAlchemy存储凭证
- 使用现有的错误处理和重试机制
- 集成到现有的gRPC服务中

**🔧 依赖管理策略：**统一使用 `uv sync --frozen` 进行依赖安装和管理
```python
# pyproject.toml中需要新增：
"cryptography>=41.0.0",  # 凭证加密
"httpx>=0.25.0",         # HTTP客户端（已有）
"python-jose>=3.3.0",    # JWT处理（已有）

# 开发环境设置：
uv sync --frozen  # 安装所有依赖
```

### 5. 实现优先级和交付策略

#### 阶段1：核心基础设施（优先级：🔥 高）
```python
# 第1周目标：基础凭证管理和HTTP工具
- CredentialManager类实现（数据库存储）
- OAuth2Handler基础流程
- HTTP工具真实实现（替换simulate方法）
- 基础错误处理和重试机制
```

#### 阶段2：Google Calendar集成（优先级：🔥 高）
```python
# 第2周目标：Google Calendar完整集成
- GoogleCalendarClient实现
- create_event, list_events核心功能
- OAuth2完整授权流程
- 与AI Agent的集成测试
```

#### 阶段3：Slack集成（优先级：🟡 中）
```python
# 第3周目标：Slack消息发送
- SlackClient基础实现
- send_message功能
- 错误处理和重试
- 与工作流通知的集成
```

#### 阶段4：扩展和优化（优先级：🔵 低）
```python
# 后续扩展：
- GitHub API集成（如需要）
- 高级功能（文件上传、交互按钮等）
- 性能优化和监控
- 安全审计和测试
```

### 6. 基于现有架构明确的技术实现方案

**✅ 已明确的加密实现方案（基于n8n设计和项目架构）：**

1. **应用层加密方式：**
   - 使用Python `cryptography.fernet.Fernet` 进行对称加密（n8n同样方案）
   - 加密密钥通过环境变量 `CREDENTIAL_ENCRYPTION_KEY` 管理（类似n8n的N8N_ENCRYPTION_KEY）
   - 加密字段：`access_token`、`refresh_token`，`credential_data`中的敏感信息
   - 基于项目现有配置模式实现：

```python
# workflow_engine/core/config.py 中新增配置
class Settings(BaseSettings):
    # 现有配置...
    credential_encryption_key: str = "your-credential-encryption-key"
    
# 加密工具实现
from cryptography.fernet import Fernet
import base64, hashlib

def get_encryption_key() -> bytes:
    """基于环境变量生成一致的加密密钥"""
    key_source = get_settings().credential_encryption_key
    return base64.urlsafe_b64encode(hashlib.sha256(key_source.encode()).digest())
```

2. **refresh_token分离存储方案：**
   - refresh_token存储在oauth_tokens表的独立字段中
   - 使用不同的加密盐值分别加密access_token和refresh_token
   - 确保即使access_token泄露，refresh_token仍然安全

3. **API Gateway与workflow_engine交互协议（基于现有gRPC架构）：**
   - 使用现有的gRPC通信机制，在workflow_service.proto中扩展新方法
   - OAuth2状态管理：API Gateway生成state并存储到Redis（项目已有Redis配置）
   - 回调处理：API Gateway调用workflow_engine的gRPC方法存储凭证

```protobuf
// 在 shared/proto/engine/workflow_service.proto 中扩展
service WorkflowService {
  // 现有方法...
  rpc StoreOAuth2Credential(StoreCredentialRequest) returns (StoreCredentialResponse);
  rpc RefreshOAuth2Token(RefreshTokenRequest) returns (RefreshTokenResponse);
  rpc GetCredential(GetCredentialRequest) returns (GetCredentialResponse);
}
```

4. **现有gRPC服务扩展方式：**
   - 在workflow_engine中新增CredentialService（遵循现有MainWorkflowService模式）
   - 使用现有的配置管理模式（pydantic Settings）添加加密相关配置
   - 利用现有的数据库连接池和SQLAlchemy模型（workflow_engine/models/database.py）

**✅ 已明确的API功能实现细节：**

5. **Google Calendar API实现：**
   - calendar_id在节点参数中配置（默认使用"primary"主日历）
   - 提供 `list_calendars` 方法供用户选择日历（后续扩展功能）
   - 基于现有节点参数设计模式：

```python
# 工具节点参数配置示例
{
  "operation": "create_event",
  "calendar_id": "primary",  # 或具体的日历ID
  "event_data": {
    "summary": "会议主题",
    "start": {"dateTime": "2025-01-20T10:00:00Z"},
    "end": {"dateTime": "2025-01-20T11:00:00Z"}
  }
}
```

6. **Slack消息格式支持（基于Slack API限制）：**
   - 纯文本：完全支持
   - 基础markdown：支持 `*bold*`, `_italic_`, `~strikethrough~`, `code`, ``` `block code` ```
   - Slack特有格式：支持 `<@USER_ID>` mentions和 `<#CHANNEL_ID>` channel links
   - 链接格式：支持 `<https://example.com|链接文本>` 格式

7. **HTTP工具认证配置统一存储：**
   - 统一使用oauth_tokens表存储，通过`provider`字段区分服务类型
   - `credential_data`字段存储不同认证方式的配置：

```json
// Bearer Token
{"type": "bearer", "token": "encrypted_token_value"}

// API Key  
{"type": "api_key", "key_name": "X-API-Key", "key_value": "encrypted_key", "location": "header"}

// Basic Auth
{"type": "basic_auth", "username": "user", "password": "encrypted_password"}
```

**⭕ 仍需澄清的具体细节：**

8. **并发token刷新的竞态处理：**
   - 使用Redis分布式锁还是数据库行级锁？
   - token刷新失败时的重试策略和用户通知方式？

9. **多用户凭证权限隔离：**
   - 是否需要实现凭证共享功能（团队级别的API密钥）？
   - 凭证的访问审计日志是否需要记录？

**🔒 基于现有架构的安全保障：**
- **加密安全性**：使用业界标准的Fernet加密，密钥通过环境变量隔离
- **OAuth2状态同步**：使用现有Redis实现分布式状态管理，确保数据一致性
- **权限隔离**：基于现有的user_id字段确保用户只能访问自己的凭证
- **审计日志**：利用现有的结构化日志系统记录凭证操作

---

## 澄清状态总结

### ✅ 已澄清的关键问题（基于n8n设计和现有架构）

1. **数据库架构**：使用已有`oauth_tokens`表，通过`provider`字段区分服务类型
2. **加密实现方案**：使用Fernet对称加密，环境变量管理密钥，参考n8n设计模式
3. **系统集成架构**：基于现有gRPC架构扩展，API Gateway处理OAuth2流程，workflow_engine管理凭证
4. **API功能实现**：Google Calendar完整CRUD（primary日历），Slack基础markdown，HTTP三种认证方式
5. **技术栈和配置**：使用uv管理依赖，遵循现有pydantic Settings配置模式，复用现有组件
6. **安全保障机制**：基于现有架构的权限隔离、Redis状态管理、结构化日志审计

### ✅ 已完成的最后4个问题澄清

1. **并发控制策略**：MVP阶段使用数据库行级锁（SELECT FOR UPDATE），简单可靠
2. **团队协作功能**：MVP阶段不实现，但在数据库设计中预留team_id字段扩展接口  
3. **运维监控需求**：MVP实现基础审计（凭证创建/更新/删除），重点关注安全事件和异常访问
4. **错误处理策略**：分层处理机制
   - **自动重试**：3次指数退避重试（2s, 4s, 8s）
   - **用户通知**：通过工作流日志记录失败原因
   - **降级策略**：token失效时暂停相关工作流，等待重新授权

## 🎉 需求澄清完成 - 可立即开始技术实现

### 📋 实施准备清单

**✅ 所有技术决策已明确，具备开始开发的条件：**

1. **架构设计**：gRPC扩展方案、数据库使用策略、加密实现方案
2. **安全策略**：Fernet加密、环境变量密钥管理、用户权限隔离
3. **功能范围**：4个核心API集成的具体实现细节
4. **错误处理**：重试机制、并发控制、降级策略
5. **实施计划**：3周分阶段交付时间表

### 🚀 立即可开始的开发任务

**第1优先级（并行开发）：**
```python
# 1. 加密模块实现
workflow_engine/core/encryption.py

# 2. 凭证管理服务
workflow_engine/services/credential_service.py

# 3. gRPC接口扩展  
shared/proto/engine/workflow_service.proto

# 4. HTTP工具真实实现
workflow_engine/nodes/tool_node.py (_execute_http_tool方法)
```

**第2优先级（第1周后）：**
```python
# 5. Google Calendar客户端
workflow_engine/clients/google_calendar_client.py

# 6. API Gateway OAuth2端点
api-gateway/routers/oauth.py
```

**第3优先级（第2周后）：**
```python
# 7. Slack客户端实现
workflow_engine/clients/slack_client.py

# 8. 审计日志和监控
workflow_engine/services/audit_service.py
```

### 📊 开发准备度评估

| 技术组件 | 准备度 | 开始条件 |
|---------|-------|----------|
| 基础加密和凭证管理 | 100% ✅ | 立即可开始 |
| HTTP工具实现 | 100% ✅ | 立即可开始 |
| Google Calendar集成 | 100% ✅ | 立即可开始 |
| gRPC接口扩展 | 100% ✅ | 立即可开始 |
| Slack集成 | 100% ✅ | 立即可开始 |
| OAuth2授权流程 | 100% ✅ | 立即可开始 |

**🎯 结论：所有技术细节已澄清完毕，可立即进入实施阶段，无技术阻塞因素。**

---

## 附录：MVP实现方案参考

用户提供的TypeScript实现方案展示了完整的OAuth2授权流程和API集成思路，虽然技术栈不同（TypeScript vs Python），但设计理念可以借鉴：

**核心设计思路：**
- 统一的服务抽象层（ServiceManager）
- OAuth2配置和状态管理
- 凭证安全存储策略
- 统一的错误处理和重试机制

**Python实现时的适配要点：**
- 使用现有的BaseNodeExecutor框架替代ServiceManager
- 使用PostgreSQL JSONB字段替代独立凭证表
- 集成到现有gRPC服务而非独立HTTP服务
- 利用现有的错误处理和重试策略（RetryPolicy）

这个参考方案为实际的Python实现提供了详细的架构思路和最佳实践指导。
