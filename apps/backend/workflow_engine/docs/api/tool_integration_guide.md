# 工具集成 API 使用指南

## 概述

Workflow Engine 提供了强大的工具集成系统，支持多种外部服务的API调用。本文档详细介绍如何使用各种工具集成功能，包括 Google Calendar、GitHub、Slack 和 HTTP 工具。

## 支持的工具类型

### 1. Google Calendar 工具

#### 功能概述
- 创建、更新、删除日程事件
- 查询日程列表
- 支持多日历管理
- OAuth2 认证

#### 基本配置

```json
{
  "node_type": "TOOL",
  "node_subtype": "CALENDAR",
  "parameters": {
    "provider": "google_calendar",
    "action": "create_event",
    "calendar_id": "primary",
    "user_id": "user123"
  }
}
```

#### 支持的操作

**创建事件 (create_event)**

```json
{
  "summary": "团队会议",
  "description": "讨论Q1项目计划",
  "start": {
    "dateTime": "2025-01-25T14:00:00Z",
    "timeZone": "Asia/Shanghai"
  },
  "end": {
    "dateTime": "2025-01-25T15:00:00Z",
    "timeZone": "Asia/Shanghai"
  },
  "attendees": [
    {"email": "user1@example.com"},
    {"email": "user2@example.com"}
  ],
  "location": "会议室A",
  "reminders": {
    "useDefault": false,
    "overrides": [
      {"method": "email", "minutes": 1440},
      {"method": "popup", "minutes": 30}
    ]
  }
}
```

**查询事件 (list_events)**

```json
{
  "timeMin": "2025-01-20T00:00:00Z",
  "timeMax": "2025-01-27T23:59:59Z",
  "maxResults": 50,
  "singleEvents": true,
  "orderBy": "startTime"
}
```

**更新事件 (update_event)**

```json
{
  "event_id": "event_123456",
  "summary": "更新后的会议标题",
  "description": "更新后的会议描述"
}
```

**删除事件 (delete_event)**

```json
{
  "event_id": "event_123456"
}
```

#### 响应格式

```json
{
  "tool_type": "calendar",
  "action": "create_event",
  "result": {
    "id": "event_123456",
    "summary": "团队会议",
    "htmlLink": "https://calendar.google.com/event?eid=...",
    "created": "2025-01-20T10:00:00Z",
    "status": "confirmed"
  },
  "executed_at": "2025-01-20T10:00:00Z"
}
```

### 2. GitHub 工具

#### 功能概述
- 仓库信息查询
- Issue 管理
- Pull Request 操作
- 文件操作
- 仓库搜索

#### 基本配置

```json
{
  "node_type": "TOOL",
  "node_subtype": "GITHUB",
  "parameters": {
    "provider": "github",
    "action": "create_issue",
    "repository": "username/repository",
    "user_id": "user123"
  }
}
```

#### 支持的操作

**创建 Issue (create_issue)**

```json
{
  "title": "Bug: 登录页面加载失败",
  "body": "## 问题描述\n用户在尝试登录时页面无法加载\n\n## 重现步骤\n1. 打开登录页面\n2. 输入用户名和密码\n3. 点击登录按钮\n\n## 预期结果\n成功登录并跳转到主页\n\n## 实际结果\n页面显示加载错误",
  "labels": ["bug", "priority-high"],
  "assignees": ["developer1", "developer2"]
}
```

**创建 Pull Request (create_pull_request)**

```json
{
  "title": "修复登录Bug",
  "head": "feature/fix-login-bug",
  "base": "main",
  "body": "修复了登录页面的加载问题\n\n关联 Issue: #123",
  "draft": false
}
```

**获取仓库信息 (get_repository_info)**

```json
{
  "repository": "username/repository"
}
```

**文件操作 (create_file, update_file, get_file_content)**

```json
{
  "path": "src/components/Login.tsx",
  "content": "import React from 'react';\n\nconst Login = () => {\n  return <div>Login Component</div>;\n};\n\nexport default Login;",
  "message": "添加登录组件",
  "branch": "main"
}
```

**搜索仓库 (search_repositories)**

```json
{
  "query": "react typescript components",
  "limit": 10,
  "sort": "stars"
}
```

#### 响应格式

```json
{
  "tool_type": "github",
  "action": "create_issue",
  "repository": "username/repository",
  "result": {
    "id": 123456789,
    "number": 42,
    "title": "Bug: 登录页面加载失败",
    "state": "open",
    "html_url": "https://github.com/username/repository/issues/42",
    "created_at": "2025-01-20T10:00:00Z"
  },
  "executed_at": "2025-01-20T10:00:00Z"
}
```

### 3. Slack 工具

#### 功能概述
- 发送消息到频道
- 发送私人消息
- Markdown 格式支持
- 频道验证

#### 基本配置

```json
{
  "node_type": "TOOL",
  "node_subtype": "EMAIL",
  "parameters": {
    "provider": "slack",
    "action": "send_message",
    "channel": "#general",
    "user_id": "user123"
  }
}
```

#### 支持的操作

**发送频道消息 (send_message)**

```json
{
  "channel": "#engineering",
  "text": "🚀 **部署完成**\n\n新版本已成功部署到生产环境：\n- 修复了登录问题\n- 优化了性能\n- 添加了新功能\n\n请查看 [部署日志](https://deploy.example.com/logs) 获取详细信息。",
  "format_markdown": true,
  "as_user": true
}
```

**发送私人消息 (send_direct_message)**

```json
{
  "user_id": "U1234567890",
  "text": "你好！你的任务已经准备好了，请查看详情。",
  "format_markdown": true
}
```

#### Markdown 支持

Slack 工具支持以下 Markdown 格式：

- **粗体文本**: `**文本**` → `*文本*`
- **斜体文本**: `_文本_` → `_文本_`
- **删除线**: `~~文本~~` → `~文本~`
- **代码**: `` `代码` `` → `` `代码` ``
- **链接**: `[文本](URL)` → `<URL|文本>`
- **用户提及**: `@用户名` → `<@用户名>`
- **频道提及**: `#频道名` → `<#频道名>`

#### 响应格式

```json
{
  "tool_type": "email",
  "provider": "slack",
  "result": {
    "ok": true,
    "channel": "C1234567890",
    "ts": "1234567890.123456",
    "message": {
      "text": "消息已发送",
      "user": "B1234567890"
    }
  },
  "executed_at": "2025-01-20T10:00:00Z"
}
```

### 4. HTTP 工具

#### 功能概述
- 支持所有 HTTP 方法 (GET, POST, PUT, DELETE, PATCH 等)
- 多种认证方式
- 自定义请求头和参数
- 自动重试机制

#### 基本配置

```json
{
  "node_type": "TOOL",
  "node_subtype": "HTTP",
  "parameters": {
    "provider": "http",
    "action": "request",
    "method": "POST",
    "url": "https://api.example.com/data",
    "user_id": "user123"
  }
}
```

#### 认证配置

**Bearer Token 认证**

```json
{
  "auth_config": {
    "type": "bearer",
    "token": "your_access_token"
  }
}
```

**API Key 认证 (Header)**

```json
{
  "auth_config": {
    "type": "api_key",
    "key_name": "X-API-Key",
    "key_value": "your_api_key",
    "location": "header"
  }
}
```

**API Key 认证 (Query Parameter)**

```json
{
  "auth_config": {
    "type": "api_key",
    "key_name": "api_key",
    "key_value": "your_api_key",
    "location": "query"
  }
}
```

**Basic 认证**

```json
{
  "auth_config": {
    "type": "basic_auth",
    "username": "your_username",
    "password": "your_password"
  }
}
```

#### 请求示例

**GET 请求**

```json
{
  "method": "GET",
  "url": "https://api.example.com/users",
  "headers": {
    "Accept": "application/json",
    "User-Agent": "Workflow-Engine/1.0"
  },
  "params": {
    "page": 1,
    "limit": 20
  }
}
```

**POST 请求**

```json
{
  "method": "POST",
  "url": "https://api.example.com/users",
  "headers": {
    "Content-Type": "application/json"
  },
  "json": {
    "name": "张三",
    "email": "zhangsan@example.com",
    "role": "developer"
  }
}
```

**PUT 请求**

```json
{
  "method": "PUT",
  "url": "https://api.example.com/users/123",
  "json": {
    "name": "李四",
    "email": "lisi@example.com"
  }
}
```

#### 响应格式

```json
{
  "tool_type": "http",
  "method": "POST",
  "result": {
    "id": 123,
    "name": "张三",
    "email": "zhangsan@example.com",
    "created_at": "2025-01-20T10:00:00Z"
  },
  "executed_at": "2025-01-20T10:00:00Z"
}
```

## 认证和凭证管理

### OAuth2 认证流程

#### 1. 生成授权 URL

```python
from workflow_engine.services.oauth2_handler import OAuth2Handler

handler = OAuth2Handler()

# 生成 Google Calendar 授权 URL
auth_url = await handler.generate_auth_url(
    provider="google_calendar",
    user_id="user123",
    scopes=["https://www.googleapis.com/auth/calendar.events"]
)

print(f"请访问以下URL进行授权: {auth_url}")
```

#### 2. 处理授权回调

```python
# 用户授权后，使用返回的 code 和 state 交换访问令牌
credentials = await handler.exchange_code_for_tokens(
    provider="google_calendar",
    code="authorization_code_from_callback",
    state="state_parameter_from_callback"
)

print(f"授权成功，访问令牌已保存")
```

#### 3. 令牌刷新

```python
# 系统会自动检查令牌过期并刷新
# 如需手动刷新
refreshed_credentials = await handler.refresh_access_token(
    refresh_token="refresh_token",
    provider="google_calendar"
)
```

### 凭证安全

- 所有凭证都使用 AES 加密存储
- 支持令牌自动刷新
- 审计日志记录所有凭证操作
- 定期凭证健康检查

## 错误处理

### 常见错误类型

#### 1. 认证错误

```json
{
  "error": "authentication_failed",
  "message": "访问令牌已过期或无效",
  "details": {
    "provider": "google_calendar",
    "user_id": "user123",
    "error_code": "invalid_token"
  }
}
```

#### 2. 权限错误

```json
{
  "error": "insufficient_permissions",
  "message": "用户权限不足，无法执行此操作",
  "details": {
    "required_scopes": ["calendar.events.create"],
    "granted_scopes": ["calendar.events.read"]
  }
}
```

#### 3. 限流错误

```json
{
  "error": "rate_limit_exceeded",
  "message": "API 调用频率超出限制",
  "details": {
    "retry_after": 300,
    "limit": 1000,
    "reset_time": "2025-01-20T11:00:00Z"
  }
}
```

#### 4. 网络错误

```json
{
  "error": "network_error",
  "message": "网络连接超时",
  "details": {
    "timeout": 30,
    "retry_count": 3,
    "last_attempt": "2025-01-20T10:30:00Z"
  }
}
```

### 重试机制

所有工具都实现了智能重试机制：

- **指数退避**: 重试间隔逐渐增加 (2s, 4s, 8s)
- **最大重试次数**: 默认 3 次
- **可重试错误**: 网络超时、服务器错误 (5xx)
- **不可重试错误**: 认证错误、权限错误、客户端错误 (4xx)

## 性能优化

### 1. 连接池

- HTTP 客户端使用连接池减少连接开销
- 每个 provider 维护独立的连接池
- 自动连接保活和清理

### 2. 缓存策略

- 认证令牌缓存
- API 响应缓存 (可配置)
- 频率限制信息缓存

### 3. 并发控制

- 每用户最大并发请求限制
- API 调用排队机制
- 资源使用监控

## 监控和日志

### 审计日志

所有工具操作都会记录详细的审计日志：

```json
{
  "event_type": "tool_executed",
  "timestamp": "2025-01-20T10:00:00Z",
  "user_id": "user123",
  "tool_type": "calendar",
  "provider": "google_calendar",
  "action": "create_event",
  "execution_time_ms": 1500,
  "success": true,
  "details": {
    "input_data_keys": ["summary", "start", "end"],
    "result_keys": ["id", "htmlLink"]
  }
}
```

### 性能监控

```json
{
  "metric_type": "api_call_performance",
  "provider": "google_calendar",
  "operation": "create_event",
  "avg_response_time": 1200,
  "success_rate": 0.995,
  "total_calls": 1000,
  "p95_response_time": 2500
}
```

### 错误监控

```json
{
  "event_type": "tool_failed",
  "timestamp": "2025-01-20T10:05:00Z",
  "user_id": "user123",
  "tool_type": "github",
  "error_type": "rate_limit_exceeded",
  "error_message": "API rate limit exceeded",
  "retry_count": 3
}
```

## 最佳实践

### 1. 错误处理

- 始终检查工具执行结果的 success 状态
- 为不同错误类型实现对应的处理逻辑
- 使用重试机制处理临时性错误
- 记录错误日志便于问题排查

### 2. 性能优化

- 批量操作优于单个操作
- 合理设置超时时间
- 避免在短时间内大量API调用
- 使用缓存减少重复请求

### 3. 安全最佳实践

- 定期轮换 API 密钥
- 使用最小权限原则
- 监控异常访问模式
- 及时撤销不需要的凭证

### 4. 可靠性

- 实现幂等性检查
- 使用事务保证数据一致性
- 设置合适的超时和重试参数
- 监控工具执行成功率

## 开发指南

### 添加新的工具提供商

1. **创建客户端类**

```python
from workflow_engine.clients.base import BaseAPIClient

class NewProviderClient(BaseAPIClient):
    def __init__(self, credentials):
        super().__init__(credentials)
        self.base_url = "https://api.newprovider.com"
    
    async def create_resource(self, data):
        return await self._make_request("POST", "/resources", json=data)
```

2. **注册工具执行器**

```python
# 在 tool_node.py 中添加新的执行方法
def _execute_newprovider_tool(self, context, logs, start_time):
    # 实现工具执行逻辑
    pass
```

3. **更新配置**

```python
# 在 get_supported_subtypes 中添加新类型
def get_supported_subtypes(self):
    return ["MCP", "CALENDAR", "EMAIL", "HTTP", "GITHUB", "NEWPROVIDER"]
```

4. **编写测试**

```python
class TestNewProviderClient:
    def test_create_resource(self):
        # 测试资源创建
        pass
```

### 调试技巧

- 启用详细日志: `LOG_LEVEL=DEBUG`
- 查看审计日志了解工具执行情况
- 使用性能监控识别瓶颈
- 检查凭证状态和权限

## 常见问题

### Q: 如何处理令牌过期？

A: 系统会自动检测令牌过期并尝试刷新。如果刷新失败，会返回认证错误，需要用户重新授权。

### Q: API 调用失败如何重试？

A: 系统会自动重试可重试的错误（如网络错误、服务器错误）。不可重试的错误（如认证失败）会立即返回错误。

### Q: 如何监控工具性能？

A: 可以通过审计日志和性能监控指标查看工具执行情况，包括响应时间、成功率等。

### Q: 如何限制API调用频率？

A: 系统会自动遵守各个API提供商的频率限制，并在超出限制时自动等待或重试。

### Q: 凭证信息如何保护？

A: 所有凭证都使用AES加密存储，并记录所有访问操作的审计日志。

## 版本兼容性

- API 版本: v1.0
- 支持的 Provider 版本:
  - Google Calendar API: v3
  - GitHub API: v4 (REST)
  - Slack API: v2
  - HTTP: 1.1/2.0

## 更新日志

### v1.0.0 (2025-01-20)
- 初始发布
- 支持 Google Calendar, GitHub, Slack, HTTP 工具
- OAuth2 认证支持
- 审计日志系统
- 性能监控 