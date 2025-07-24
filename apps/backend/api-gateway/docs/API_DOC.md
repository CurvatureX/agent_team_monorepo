# Workflow Generation API Documentation

## 基础信息

- **Base URL**: `https://api.example.com/v1/api`
- **认证方式**: Cookie认证
- **Content-Type**: `application/json`（除SSE接口外）

## API 接口

### 1. POST /session
创建新会话

**请求**
action: 
- `create` 从头创建新的 workflow
- `edit` 编辑自己的某个 workflow
- `copy` copy from a public / template workflow

```json
{
  "action": "",
  "workflow_id": ""
}
```

**响应**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2024-01-20T10:30:00Z",
}
```

### 2. GET /chat/stream?session_id=xxxx&user_message=yyy
发送聊天消息，返回AI流式响应

**响应（SSE流）**
使用业界标准增量模式 (OpenAI/Claude风格):
```
Content-Type: text/event-stream

data: {"type": "message", "delta": "1. 我将为你监控"}
data: {"type": "message", "delta": " BestBuy, Amazon"}
data: {"type": "message", "delta": " 的实时货源"}
```

**事件类型**
- `type: "message"` - AI回复消息
- `delta`: 增量内容，前端需要累积拼接

### 3. GET /workflow_generation
监听工作流生成进度

**请求**
```
GET /workflow?session_id=xxx
```

**响应（SSE流）**
```
Content-Type: text/event-stream

data: {"type": "waiting"}

data: {"type": "start", "workflow_id": "wf_abc123"}

data: {"type": "draft", "workflow_id": "wf_abc123", "data": {...}}

data: {"type": "debugging", "workflow_id": "wf_abc123", "data": {...}}

data: {"type": "complete", "workflow_id": "wf_abc123", "data": {...}}
```

**事件类型**
- `type: "waiting"` - 等待开始
- `type: "start"` - 开始生成
- `type: "draft"` - 生成草稿
- `type: "debugging"` - 系统自动调试中
- `type: "complete"` - 生成完成，包含workflow数据
- `type: "error"` - 生成失败

## 错误响应

所有API错误响应格式：
```json
{
  "error": "error_type",
  "message": "错误描述"
}
```

**HTTP状态码**
- 400 - 请求参数错误
- 401 - 未认证（Cookie无效）
- 404 - 资源不存在
- 500 - 服务器错误

## 交互流程

```mermaid
sequenceDiagram
    participant Client
    participant Session as /session
    participant Chat as /chat
    participant Workflow as /workflow
    participant Agent as AI Agent

    Client->>Session: POST /session
    Session-->>Client: {session_id}

    Client->>Workflow: GET /workflow_generation?session_id=xxx
    Note over Client,Workflow: SSE连接建立，保持等待状态

    loop 多轮对话
        Client->>Chat: GET /chat?session_id=xxx&user_message={message}
        Chat->>Agent: 分析用户意图

        alt Agent需要更多信息
            Chat-->>Client: SSE: "请问使用什么数据库？"
            Note over Client,Chat: 继续对话循环
        else Agent判断信息充足

                Agent->>Workflow: 触发工作流生成
                Workflow-->>Client: SSE: {type: "start"}
                Workflow-->>Client: SSE: {type: "draft", data: {...}}
                Workflow-->>Client: SSE: {type: "debugging", data: {...}}
                Workflow-->>Client: SSE: {type: "complete", data: {...}}
        end
    end

```
