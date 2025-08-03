# External API Integration Documentation

## 概述

外部API集成功能为Agent Team Monorepo提供了统一的OAuth2授权管理、凭证存储和外部API调用能力。支持Google Calendar、GitHub、Slack等主流服务的集成。

## API端点

### 基础路径
所有外部API端点都在 `/api/app/external-apis/` 路径下，需要Supabase JWT认证。

### 1. OAuth2授权管理

#### 启动OAuth2授权
```http
POST /api/app/external-apis/auth/authorize
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "provider": "google_calendar",
  "scopes": ["https://www.googleapis.com/auth/calendar"],
  "redirect_url": "https://app.example.com/callback"
}
```

**响应:**
```json
{
  "auth_url": "https://accounts.google.com/oauth/authorize?client_id=...",
  "state": "state_google_calendar_user123_1234567890",
  "expires_at": "2025-08-02T10:10:00Z",
  "provider": "google_calendar"
}
```

#### 处理OAuth2回调
```http
GET /api/app/external-apis/auth/callback?code=auth_code&state=state_value&provider=google_calendar
Authorization: Bearer {jwt_token}
```

**响应:**
```json
{
  "access_token": "ya29.a0AfH6SMC...",
  "refresh_token": "1//04XXXXXXXXXXXXX",
  "expires_at": "2025-08-02T11:00:00Z",
  "scope": ["https://www.googleapis.com/auth/calendar"],
  "provider": "google_calendar",
  "token_type": "Bearer"
}
```

### 2. 凭证管理

#### 获取用户凭证列表
```http
GET /api/app/external-apis/credentials
Authorization: Bearer {jwt_token}
```

**响应:**
```json
{
  "credentials": [
    {
      "provider": "google_calendar",
      "is_valid": true,
      "scope": ["https://www.googleapis.com/auth/calendar"],
      "last_used_at": "2025-08-02T08:00:00Z",
      "expires_at": "2025-09-01T10:00:00Z",
      "created_at": "2025-07-28T10:00:00Z",
      "updated_at": "2025-08-02T08:00:00Z"
    }
  ],
  "total_count": 1
}
```

#### 撤销凭证
```http
DELETE /api/app/external-apis/credentials/{provider}
Authorization: Bearer {jwt_token}
```

**响应:**
```json
{
  "success": true,
  "message": "Credential for google_calendar has been revoked successfully",
  "details": {
    "provider": "google_calendar",
    "user_id": "user123",
    "revoked_at": "2025-08-02T10:00:00Z"
  }
}
```

### 3. API测试

#### 测试API调用
```http
POST /api/app/external-apis/test-call
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "provider": "google_calendar",
  "operation": "list_events",
  "parameters": {
    "calendar_id": "primary",
    "time_min": "2025-08-01T00:00:00Z",
    "time_max": "2025-08-31T23:59:59Z"
  },
  "timeout_seconds": 30
}
```

**响应:**
```json
{
  "success": true,
  "provider": "google_calendar",
  "operation": "list_events",
  "execution_time_ms": 245.6,
  "result": {
    "events": [
      {
        "id": "event123",
        "summary": "Meeting",
        "start": "2025-08-02T10:00:00Z"
      }
    ]
  }
}
```

### 4. 状态监控

#### 获取API状态
```http
GET /api/app/external-apis/status
Authorization: Bearer {jwt_token}
```

**响应:**
```json
{
  "providers": [
    {
      "provider": "google_calendar",
      "available": true,
      "operations": ["list_events", "create_event", "update_event", "delete_event"],
      "last_check": "2025-08-02T10:00:00Z",
      "response_time_ms": 150.5
    }
  ],
  "total_available": 2,
  "last_updated": "2025-08-02T10:00:00Z"
}
```

#### 获取使用指标
```http
GET /api/app/external-apis/metrics?time_range=24h
Authorization: Bearer {jwt_token}
```

**响应:**
```json
{
  "metrics": [
    {
      "provider": "google_calendar",
      "total_calls": 156,
      "successful_calls": 148,
      "failed_calls": 8,
      "average_response_time_ms": 245.6,
      "last_24h_calls": 23,
      "success_rate": 94.9
    }
  ],
  "time_range": "24h",
  "generated_at": "2025-08-02T10:00:00Z"
}
```

## 支持的API提供商

### Google Calendar (`google_calendar`)
**默认权限范围:**
- `https://www.googleapis.com/auth/calendar` - 完整日历访问
- `https://www.googleapis.com/auth/calendar.readonly` - 只读访问

**支持的操作:**
- `list_events` - 获取日历事件列表
- `create_event` - 创建新事件
- `update_event` - 更新现有事件
- `delete_event` - 删除事件
- `list_calendars` - 获取用户日历列表

### GitHub (`github`)
**默认权限范围:**
- `repo` - 仓库访问权限
- `user:email` - 用户邮箱访问
- `issues` - Issues管理权限

**支持的操作:**
- `list_repos` - 获取仓库列表
- `create_issue` - 创建Issue
- `update_issue` - 更新Issue
- `list_prs` - 获取Pull Requests列表
- `create_pr` - 创建Pull Request

### Slack (`slack`)
**默认权限范围:**
- `chat:write` - 发送消息权限
- `channels:read` - 读取频道列表
- `files:write` - 文件上传权限

**支持的操作:**
- `send_message` - 发送消息
- `send_dm` - 发送私信
- `list_channels` - 获取频道列表
- `create_channel` - 创建频道
- `upload_file` - 上传文件
- `list_users` - 获取用户列表

## 错误处理

### 常见错误状态码

#### 400 Bad Request
```json
{
  "detail": "Invalid state parameter"
}
```

#### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```

#### 422 Unprocessable Entity
```json
{
  "detail": [
    {
      "loc": ["body", "provider"],
      "msg": "Invalid provider. Must be one of: google_calendar, github, slack",
      "type": "value_error"
    }
  ]
}
```

#### 500 Internal Server Error
```json
{
  "error": "ExternalAPIError",
  "message": "Failed to process OAuth2 callback",
  "details": {
    "status_code": 500,
    "path": "/api/app/external-apis/auth/callback",
    "timestamp": "2025-08-02T10:00:00Z"
  }
}
```

## 安全考虑

### 1. 认证和授权
- 所有端点都需要有效的Supabase JWT令牌
- 使用Row Level Security (RLS) 确保用户只能访问自己的凭证
- State参数用于防止CSRF攻击

### 2. 凭证存储
- 访问令牌和刷新令牌使用AES-256加密存储
- 敏感信息不会出现在日志中
- 定期清理过期的凭证

### 3. API调用限流
- 每个用户的API调用有频率限制
- 超出限制时返回429状态码
- 支持根据用户级别调整限流策略

## 集成指南

### 前端集成示例

```typescript
// 启动OAuth2授权
const startAuthorization = async (provider: string, scopes: string[]) => {
  const response = await fetch('/api/app/external-apis/auth/authorize', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${userToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      provider,
      scopes,
      redirect_url: window.location.origin + '/oauth/callback'
    })
  });
  
  const data = await response.json();
  
  // 重定向到授权页面
  window.location.href = data.auth_url;
};

// 获取用户凭证列表
const getUserCredentials = async () => {
  const response = await fetch('/api/app/external-apis/credentials', {
    headers: {
      'Authorization': `Bearer ${userToken}`
    }
  });
  
  return response.json();
};

// 测试API调用
const testAPICall = async (provider: string, operation: string, parameters: any) => {
  const response = await fetch('/api/app/external-apis/test-call', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${userToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      provider,
      operation,
      parameters
    })
  });
  
  return response.json();
};
```

### 工作流集成示例

```json
{
  "node_type": "EXTERNAL_ACTION",
  "name": "Create Calendar Event",
  "parameters": {
    "api_service": "google_calendar",
    "operation": "create_event",
    "parameters": {
      "calendar_id": "primary",
      "event": {
        "summary": "{{workflow.input.meeting_title}}",
        "start": {"dateTime": "{{workflow.input.start_time}}"},
        "end": {"dateTime": "{{workflow.input.end_time}}"}
      }
    }
  }
}
```

## 开发和测试

### 本地开发设置

1. **配置环境变量**
```bash
# .env文件
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SECRET_KEY=your-service-role-key
SUPABASE_ANON_KEY=your-anon-key

# OAuth2配置（生产环境中需要真实值）
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
SLACK_CLIENT_ID=your-slack-client-id
SLACK_CLIENT_SECRET=your-slack-client-secret
```

2. **启动开发服务器**
```bash
uv run uvicorn app.main:app --reload
```

3. **查看API文档**
访问 `http://localhost:8000/docs` 查看自动生成的OpenAPI文档

### 测试

```bash
# 运行外部API测试
pytest tests/test_external_apis.py -v

# 运行所有测试
pytest tests/ -v

# 带覆盖率的测试
pytest tests/ --cov=app --cov-report=html
```

## 部署注意事项

### 1. 环境变量配置
确保生产环境中配置了正确的OAuth2客户端凭证和回调URL。

### 2. 数据库迁移
部署前运行数据库迁移脚本，创建必要的表结构：
- `user_external_credentials`
- `external_api_call_logs`

### 3. 监控设置
建议配置以下监控指标：
- API调用成功率
- 平均响应时间
- 错误率和错误类型
- 用户授权状态

### 4. 缓存策略
为提高性能，建议对以下数据进行缓存：
- 用户凭证状态（缓存5分钟）
- API提供商状态（缓存1分钟）
- OAuth2配置信息（缓存1小时）

## 路线图

### 近期功能
- [ ] 实际OAuth2服务集成
- [ ] 数据库持久化实现
- [ ] 令牌自动刷新机制
- [ ] 详细的访问日志记录

### 中期功能
- [ ] 更多API提供商支持（Microsoft Graph、Notion等）
- [ ] Webhook接收和处理
- [ ] 批量API操作支持
- [ ] 高级权限管理

### 长期功能
- [ ] API调用编排和工作流
- [ ] 智能重试和故障恢复
- [ ] 使用模式分析和优化建议
- [ ] 第三方应用集成市场