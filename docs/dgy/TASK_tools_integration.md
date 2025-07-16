# 工具集成和API适配 - 任务拆分定义文档

## 任务拆分策略

基于DESIGN_tools.md架构设计，按照分层依赖关系将工具集成功能拆分为14个原子任务：

- **基础设施层**：Task_01 ~ Task_04
- **服务层扩展**：Task_05 ~ Task_08  
- **工具集成层**：Task_10 ~ Task_12 (Task_09已移除重复)
- **验证交付层**：Task_13 ~ Task_15

## 任务概览图 (修正版)

```
基础框架层 (✅ 已完成)
Task_01 → Task_02 → Task_03 → Task_04
  ↓        ↓        ↓        ↓
服务层扩展 (✅ 已完成)
Task_05 → Task_06 → Task_07 → Task_08
  ↓        ↓        ↓        ↓
工具集成层 (🔄 进行中)
Task_10 → Task_11 → Task_12
  ↓        ↓        ↓
验证交付层 (⏳ 等待中)
Task_13 → Task_14 → Task_15
```

**关键修正**：
- ❌ **Task_09已移除**: 与Task_06重复 (Google Calendar客户端)
- ✅ **依赖关系修正**: Task_10和Task_11直接依赖Task_05 (OAuth2处理器)
- 📊 **实际任务数**: 14个任务 (而非原计划15个)

---

## 基础框架层 (✅ 已完成验证)

### ✅ 原子任务：Task_01_加密服务实现

#### 输入契约
- **前置依赖：** 无（首个任务）
- **输入数据：** 
  - workflow_engine现有配置模式参考
  - cryptography库版本要求：>=41.0.0
- **环境依赖：** 
  - Python 3.11+
  - workflow_engine开发环境
  - 统一依赖管理：`uv sync --frozen`

#### 输出契约
- **输出数据：** ✅ **已完成**
  - CredentialEncryption类，提供encrypt/decrypt方法
  - 基于Fernet的对称加密实现
- **交付物清单：**
  - ✅ `workflow_engine/core/encryption.py` - 加密服务实现
  - ✅ `tests/test_encryption.py` - 单元测试（覆盖率≥90%）
  - ✅ 加密密钥生成和管理逻辑
- **验收标准：**
  - [x] Fernet加密/解密功能正常
  - [x] 环境变量CREDENTIAL_ENCRYPTION_KEY支持
  - [x] 32字符以上密钥长度验证
  - [x] 异常处理覆盖（密钥错误、数据损坏）
  - [x] 单元测试通过，覆盖率≥90%

#### 依赖关系
- **后置任务：** Task_03（凭证管理需要加密服务）

---

### ✅ 原子任务：Task_02_配置系统扩展

#### 输入契约
- **前置依赖：** 无（与Task_01并行）
- **输入数据：** 
  - `workflow_engine/core/config.py` 现有配置结构
  - 基于现有Redis配置的OAuth2状态管理需求

#### 输出契约
- **输出数据：** ✅ **已完成**
  - 扩展后的Settings类，包含工具集成配置
  - 向后兼容的配置项新增
- **交付物清单：**
  - ✅ `workflow_engine/core/config.py` - 配置类扩展
  - ✅ OAuth2提供商配置完整
- **验收标准：**
  - [x] 新增credential_encryption_key配置项
  - [x] 新增oauth2_state_expiry配置项（默认30分钟）
  - [x] 复用现有Redis配置，无需额外配置
  - [x] 现有配置向后兼容
  - [x] OAuth2提供商配置（Google、GitHub、Slack）

#### 依赖关系
- **后置任务：** Task_03, Task_05（需要配置支持）

---

### ✅ 原子任务：Task_03_凭证管理服务

#### 输入契约
- **前置依赖：** Task_01（加密服务）, Task_02（配置扩展）
- **输入数据：** 
  - oauth_tokens表结构（来自supabase migration）
  - CredentialEncryption类接口
  - 现有SQLAlchemy模型结构

#### 输出契约
- **输出数据：** ✅ **已完成**
  - CredentialService类，支持凭证CRUD操作
  - 与现有数据库模型集成
- **交付物清单：**
  - ✅ `workflow_engine/services/credential_service.py` - 凭证管理服务
  - ✅ `workflow_engine/models/credential.py` - 凭证数据模型
  - ✅ `tests/test_credential_service.py` - 服务测试
- **验收标准：**
  - [x] 凭证加密存储到oauth_tokens表
  - [x] 用户权限隔离（基于user_id）
  - [x] 支持创建、查询、更新、删除凭证
  - [x] 数据库行级锁防止并发竞态
  - [x] 异常处理和事务回滚

#### 依赖关系
- **后置任务：** Task_04, Task_05, Task_08（需要凭证管理）

---

### ✅ 原子任务：Task_04_HTTP工具真实实现

#### 输入契约
- **前置依赖：** Task_03（凭证管理服务）
- **输入数据：** 
  - `workflow_engine/nodes/tool_node.py` 现有模拟实现
  - httpx>=0.25.0 (已存在依赖)
  - BaseNodeExecutor接口规范

#### 输出契约
- **输出数据：** ✅ **已完成**
  - 替换_simulate_http_request为真实HTTP请求
  - HTTPClient类支持3种认证方式
- **交付物清单：**
  - ✅ `workflow_engine/clients/http_client.py` - HTTP客户端实现
  - ✅ `workflow_engine/nodes/tool_node.py` - 修改_execute_http_tool方法
  - ✅ `tests/test_http_client.py` - HTTP客户端测试
- **验收标准：**
  - [x] 支持GET、POST、PUT、DELETE等HTTP方法
  - [x] 支持Bearer Token、API Key、Basic Auth认证
  - [x] 连接超时5秒，读取超时30秒
  - [x] 响应大小限制10MB
  - [x] 3次重试机制（2s, 4s, 8s指数退避）
  - [x] JSON响应自动解析

#### 依赖关系
- **后置任务：** Task_12（工具节点完善）

---

## 服务层扩展 (✅ 已完成验证)

### ✅ 原子任务：Task_05_OAuth2处理器

#### 输入契约
- **前置依赖：** Task_02（配置扩展）, Task_03（凭证管理）
- **输入数据：** 
  - Google Calendar、GitHub、Slack OAuth2配置信息
  - 现有Redis基础设施（用于状态管理）
  - 扩展后的Settings配置

#### 输出契约
- **输出数据：** ✅ **已完成**
  - OAuth2Handler类，支持授权URL生成和token交换
  - Redis状态管理实现
- **交付物清单：**
  - ✅ `workflow_engine/services/oauth2_handler.py` - OAuth2处理器
  - ✅ `workflow_engine/core/redis_client.py` - Redis客户端封装
  - ✅ `tests/test_oauth2_handler.py` - OAuth2处理器测试
- **验收标准：**
  - [x] 生成正确的OAuth2授权URL（Google、GitHub、Slack）
  - [x] 支持state参数防CSRF攻击
  - [x] Redis状态存储和过期管理（30分钟）
  - [x] 授权码交换access_token功能
  - [x] refresh_token自动刷新机制
  - [x] 多provider支持和配置化管理

#### 依赖关系
- **后置任务：** Task_06, Task_07, Task_10, Task_11（需要OAuth2支持）

---

### ✅ 原子任务：Task_06_Google_Calendar_API客户端

#### 输入契约
- **前置依赖：** Task_05（OAuth2处理器）
- **输入数据：** 
  - Google Calendar API v3文档规范
  - OAuth2Credential数据结构
  - httpx客户端配置

#### 输出契约
- **输出数据：** ✅ **已完成**
  - GoogleCalendarClient类，支持完整CRUD操作
  - 标准化的API响应格式
- **交付物清单：**
  - ✅ `workflow_engine/clients/google_calendar_client.py` - Calendar客户端
  - ✅ `workflow_engine/clients/base_client.py` - 基础客户端类
  - ✅ `tests/test_google_calendar_client.py` - 客户端测试
- **验收标准：**
  - [x] 创建日历事件（create_event）
  - [x] 查询日历事件（list_events）支持时间范围
  - [x] 更新日历事件（update_event）
  - [x] 删除日历事件（delete_event）
  - [x] 支持primary和具体calendar_id
  - [x] 自动处理token过期和刷新

#### 依赖关系
- **后置任务：** Task_12（需要客户端集成）

---

### ✅ 原子任务：Task_07_API_Gateway_OAuth2端点

#### 输入契约
- **前置依赖：** Task_05（OAuth2处理器）
- **输入数据：** 
  - `api-gateway/main.py` 现有路由结构
  - FastAPI框架约定
  - OAuth2Handler服务接口

#### 输出契约
- **输出数据：** ✅ **已完成**
  - OAuth2授权和回调REST API端点
  - 与前端集成的标准化响应
- **交付物清单：**
  - ✅ `api-gateway/routers/oauth.py` - OAuth2路由实现
  - ✅ `api-gateway/schemas/oauth.py` - 请求响应模型
  - ✅ `tests/test_oauth_endpoints.py` - API端点测试
- **验收标准：**
  - [x] GET `/oauth2/authorize/{provider}` 生成授权URL
  - [x] GET `/oauth2/callback/{provider}` 处理授权回调
  - [x] 支持user_id参数传递
  - [x] 错误处理和状态码规范
  - [x] API文档自动生成（FastAPI Swagger）

#### 依赖关系
- **后置任务：** Task_13（端到端测试）

---

### ✅ 原子任务：Task_08_gRPC服务扩展

#### 输入契约
- **前置依赖：** Task_03（凭证管理）, Task_05（OAuth2处理器）
- **输入数据：** 
  - `shared/proto/engine/workflow_service.proto` 现有定义
  - gRPC服务器现有实现结构

#### 输出契约
- **输出数据：** ✅ **已完成**
  - 扩展的gRPC服务接口，支持凭证管理
  - 生成的Python gRPC代码
- **交付物清单：**
  - ✅ `shared/proto/engine/workflow_service.proto` - protobuf扩展
  - ✅ `workflow_engine/services/credential_grpc_service.py` - gRPC服务实现
  - ✅ `shared/scripts/generate_grpc.py` - 代码生成脚本
  - ✅ `tests/test_credential_grpc.py` - gRPC服务测试
- **验收标准：**
  - [x] StoreOAuth2Credential RPC方法实现
  - [x] RefreshOAuth2Token RPC方法实现
  - [x] GetCredential RPC方法实现
  - [x] DeleteCredential RPC方法实现
  - [x] gRPC错误码正确映射
  - [x] protobuf消息格式验证

#### 依赖关系
- **后置任务：** Task_12（工具节点集成）

---

## 工具集成层 (🚧 部分完成)

### ❌ 原子任务：Task_10_GitHub_API客户端

#### 输入契约
- **前置依赖：** Task_05（OAuth2处理器） ✅ **已完成**
- **输入数据：** 
  - GitHub API v4 (GraphQL) 和 REST API文档规范
  - OAuth2Credential数据结构
  - BaseAPIClient基础类（来自Task_06）
- **环境依赖：** 
  - GitHub API访问权限
  - 测试用GitHub账号和仓库
  - 统一依赖管理：`uv sync --frozen`

#### 输出契约
- **输出数据：** 
  - GitHubClient类，支持仓库操作和Issue/PR管理
  - 标准化的API响应格式
- **交付物清单：**
  - [ ] `workflow_engine/clients/github_client.py` - GitHub客户端 ⚠️ **缺失**
  - [ ] `tests/test_github_client.py` - 客户端测试 ⚠️ **缺失**
  - [ ] `examples/github_examples.py` - 使用示例 ⚠️ **缺失**
- **验收标准：**
  - [ ] 创建Issue（支持标签、指派）
  - [ ] 创建Pull Request（支持分支、描述）
  - [ ] 获取仓库信息（基础信息、统计数据）
  - [ ] 创建和更新文件（支持分支、提交信息）
  - [ ] 获取文件内容（支持不同分支）
  - [ ] 基础仓库搜索功能
  - [ ] 自动处理token过期和刷新
  - [ ] API错误码正确处理和重试

#### 实现约束
- **技术栈：** httpx.AsyncClient, JSON处理
- **接口规范：** 
  ```python
  class GitHubClient:
      async def create_issue(self, repo: str, title: str, body: str, labels: List[str] = None) -> dict
      async def create_pull_request(self, repo: str, title: str, head: str, base: str, body: str) -> dict
      async def get_repository_info(self, repo: str) -> dict
      async def create_file(self, repo: str, path: str, content: str, message: str, branch: str = "main") -> dict
      async def update_file(self, repo: str, path: str, content: str, message: str, sha: str) -> dict
      async def get_file_content(self, repo: str, path: str, branch: str = "main") -> dict
  ```
- **质量要求：** 
  - 仓库路径格式验证（owner/repo）
  - 分支名称和文件路径验证
  - GitHub API错误码正确处理

#### 依赖关系
- **后置任务：** Task_12（工具节点集成）
- **并行任务：** Task_11（Slack客户端）

---

### ❌ 原子任务：Task_11_Slack_API客户端

#### 输入契约
- **前置依赖：** Task_05（OAuth2处理器） ✅ **已完成**
- **输入数据：** 
  - Slack Web API文档规范
  - Slack markdown格式支持列表
  - BaseAPIClient基础类（来自Task_06）
- **环境依赖：** 
  - Slack Workspace和App配置
  - Slack OAuth2应用权限
  - 统一依赖管理：`uv sync --frozen`

#### 输出契约
- **输出数据：** 
  - SlackClient类，支持消息发送和格式化
  - Slack markdown格式转换器
- **交付物清单：**
  - [ ] `workflow_engine/clients/slack_client.py` - Slack客户端 ⚠️ **缺失**
  - [ ] `workflow_engine/utils/slack_formatter.py` - 消息格式化工具 ⚠️ **缺失**
  - [ ] `tests/test_slack_client.py` - 客户端测试 ⚠️ **缺失**
  - [ ] `examples/slack_examples.py` - 使用示例 ⚠️ **缺失**
- **验收标准：**
  - [ ] 发送纯文本消息到指定频道
  - [ ] 支持基础markdown：`*bold*`, `_italic_`, `~strikethrough~`, ``` `code` ```
  - [ ] 支持Slack特有格式：`<@USER_ID>`, `<#CHANNEL_ID>`
  - [ ] 支持链接格式：`<https://example.com|链接文本>`
  - [ ] 频道名称验证和错误处理
  - [ ] 消息长度限制和截断处理

#### 实现约束
- **技术栈：** httpx, 正则表达式, JSON
- **接口规范：** 
  ```python
  class SlackClient:
      async def send_message(self, channel: str, text: str, **kwargs) -> dict
      async def format_markdown(self, text: str) -> str
      async def validate_channel(self, channel: str) -> bool
  ```
- **质量要求：** 
  - Slack API错误码处理
  - 消息格式安全转义
  - 支持频道ID和频道名称

#### 依赖关系
- **后置任务：** Task_12（工具节点集成）
- **并行任务：** Task_10（GitHub客户端）

---

### ❌ 原子任务：Task_12_工具节点执行器完善

#### 输入契约
- **前置依赖：** 
  - Task_04（HTTP工具） ✅ **已完成**
  - Task_06（Google Calendar客户端） ✅ **已完成**
  - Task_10（GitHub客户端） ❌ **未完成**
  - Task_11（Slack客户端） ❌ **未完成**
- **输入数据：** 
  - 现有tool_node.py实现
  - 各API客户端接口
  - BaseNodeExecutor接口规范

#### 输出契约
- **输出数据：** 
  - 完整的ToolNodeExecutor实现，替换所有模拟方法
  - 统一的错误处理和重试机制
- **交付物清单：**
  - [ ] `workflow_engine/nodes/tool_node.py` - 完善的工具节点执行器 ⚠️ **需要更新**
  - [ ] `workflow_engine/core/retry.py` - 重试机制实现
  - [ ] `workflow_engine/core/audit.py` - 基础审计日志
  - [ ] `tests/test_tool_node_complete.py` - 完整功能测试
- **验收标准：**
  - [x] _execute_calendar_tool真实实现（Google Calendar，基于Task_06）
  - [x] _execute_http_tool真实实现（基于Task_04）
  - [ ] _execute_github_tool真实实现（GitHub API，需要Task_10）
  - [ ] _execute_email_tool真实实现（Slack消息，需要Task_11）
  - [ ] 统一的凭证获取和刷新机制
  - [ ] 3次重试机制集成（2s, 4s, 8s指数退避）
  - [ ] 基础审计日志集成

#### 实现约束
- **技术栈：** 异步编程, 异常处理, 审计集成
- **接口规范：** 
  - 保持现有BaseNodeExecutor接口兼容
  - NodeExecutionResult格式不变
  - 支持现有连接系统（AI_TOOL连接）
- **质量要求：** 
  - 各工具类型执行成功率≥95%
  - 错误信息清晰可操作
  - 性能符合要求（5秒内响应）

#### 依赖关系
- **后置任务：** Task_13（端到端测试）

---

## 验证交付层 (⏳ 等待工具集成完成)

### ❌ 原子任务：Task_13_端到端集成测试

#### 输入契约
- **前置依赖：** Task_07（API Gateway） ✅, Task_12（工具节点完善） ❌
- **输入数据：** 
  - 完整的工具集成系统
  - 测试用API账号和配置
  - 测试数据集

#### 输出契约
- **输出数据：** 
  - 完整的端到端测试套件
  - 测试覆盖报告和性能基准
- **交付物清单：**
  - [ ] `tests/integration/test_e2e_google_calendar.py` - Google Calendar端到端测试
  - [ ] `tests/integration/test_e2e_github.py` - GitHub端到端测试
  - [ ] `tests/integration/test_e2e_slack.py` - Slack端到端测试
  - [ ] `tests/integration/test_e2e_http.py` - HTTP工具端到端测试
  - [ ] `tests/integration/test_oauth_flow.py` - OAuth2流程测试
  - [ ] `tests/performance/test_performance_benchmarks.py` - 性能基准测试

#### 依赖关系
- **后置任务：** Task_14（审计日志完善）

---

### ❌ 原子任务：Task_14_审计日志完善

#### 输入契约
- **前置依赖：** Task_13（端到端测试通过）

#### 输出契约
- **输出数据：** 
  - 完善的审计日志系统，记录关键安全事件
  - 结构化日志格式和监控支持
- **交付物清单：**
  - [ ] `workflow_engine/core/audit.py` - 审计日志完善（基于Task_12）
  - [ ] `workflow_engine/core/logger.py` - 日志配置扩展
  - [ ] `tests/test_audit_complete.py` - 完整审计系统测试

#### 依赖关系
- **后置任务：** Task_15（文档和部署）

---

### ❌ 原子任务：Task_15_文档和部署

#### 输入契约
- **前置依赖：** Task_14（审计日志完善）

#### 输出契约
- **输出数据：** 
  - 完整的使用文档和部署指南
  - 部署脚本和配置文件
- **交付物清单：**
  - [ ] `docs/api/tools_integration.md` - API使用文档
  - [ ] `docs/deployment/tools_setup.md` - 部署配置指南
  - [ ] `examples/workflow_examples/` - 完整工作流示例
  - [ ] `scripts/deploy_tools.sh` - 部署脚本

---

## 🎯 **关键实施建议**

### 1. **立即可开始的任务** (依赖已满足)
#### **优先级1: Task_10 GitHub客户端** (3-5天)
```python
# 核心实现内容
class GitHubClient(BaseAPIClient):
    async def create_issue(self, repo: str, title: str, body: str) -> dict
    async def create_pull_request(self, repo: str, title: str, head: str, base: str) -> dict
    async def get_repository_info(self, repo: str) -> dict
    async def create_file(self, repo: str, path: str, content: str, message: str) -> dict
```

#### **优先级1: Task_11 Slack客户端** (2-3天)
```python
# 核心实现内容  
class SlackClient(BaseAPIClient):
    async def send_message(self, channel: str, text: str) -> dict
    async def format_markdown(self, text: str) -> str
```

**建议**: Task_10和Task_11可并行开发，技术栈相同，可复用Task_06的BaseAPIClient模式

### 2. **关键路径管理**
```
Task_10 + Task_11 → Task_12 → Task_13 → Task_14 → Task_15
  (3-5天)   (2-3天)    (2-3天)   (3-5天)   (2天)    (2天)
```

**总预估时间**: 14-20天 (约3周)

### 3. **质量保证策略**
- **代码复用**: 基于已完成的Task_06 GoogleCalendarClient模式
- **测试驱动**: 每个客户端都要有完整的单元测试
- **渐进集成**: Task_12分阶段集成各客户端，避免一次性集成风险

### 4. **风险缓解**
- **低风险**: OAuth2基础已完善，客户端模式已验证
- **中风险**: Task_12集成复杂度，建议分步实施
- **无阻塞**: 所有前置依赖已完成，可立即推进

---

## 总结

### 任务拆分优化后的特点

1. **原子性**: 移除重复任务后，14个任务都可独立开发和测试
2. **依赖清晰**: 修正后的依赖关系无循环，支持并行开发
3. **验收明确**: 每个任务有具体的功能和质量验收标准  
4. **复杂度可控**: 单个任务1-5天完成，风险可控

### 项目健康度评估

- **✅ 基础设施层**: 100%完成，质量优秀
- **✅ 服务层扩展**: 100%完成，架构完善
- **🚧 工具集成层**: 33%完成，GitHub和Slack客户端待实现
- **⏳ 验证交付层**: 0%完成，等待工具集成完成

**下一步**: 立即并行开始Task_10和Task_11，预计2-3周内完成全部剩余任务。 