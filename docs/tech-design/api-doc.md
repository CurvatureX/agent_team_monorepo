# Workflow Generation API Documentation

## 基础信息

- **Base URL**: `https://api.example.com/v1`
- **认证方式**: Cookie认证
- **Content-Type**: `application/json`（除SSE接口外）

## API 接口

### 1. POST /session
创建新会话

**请求**
```json
{
  "metadata": {}  // 可选，会话元数据
}
```

**响应**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2024-01-20T10:30:00Z",
  "expires_at": "2024-01-20T11:30:00Z"
}
```

### 2. POST /chat
发送聊天消息，返回AI流式响应

**请求**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "我想创建一个数据处理工作流"
}
```

**响应（SSE流）**
```
Content-Type: text/event-stream

data: {"type": "message", "content": "我理解您想要创建一个数据处理工作流"}

data: {"type": "message", "content": "请问需要处理什么类型的数据？"}

data: {"type": "signal", "action": "start_workflow_listening"}
```

**事件类型**
- `type: "message"` - AI回复消息
- `type: "signal"` - 系统信号
  - `action: "start_workflow_listening"` - 可以开始生成workflow
  - `action: "need_more_info"` - 需要更多信息

### 3. GET /workflow
监听工作流生成进度

**请求**
```
GET /workflow?session_id=550e8400-e29b-41d4-a716-446655440000
```

**响应（SSE流）**
```
Content-Type: text/event-stream

data: {"type": "waiting"}

data: {"type": "start", "workflow_id": "wf_abc123"}

data: {"type": "progress", "workflow_id": "wf_abc123", "progress": 50}

data: {"type": "complete", "workflow_id": "wf_abc123", "data": {...}}
```

**事件类型**
- `type: "waiting"` - 等待开始
- `type: "start"` - 开始生成
- `type: "progress"` - 生成进度（0-100）
- `type: "complete"` - 生成完成，包含workflow数据
- `type: "error"` - 生成失败

**Workflow数据结构**
```json
{
  "nodes": [
    {
      "id": "node_1",
      "type": "trigger",  // trigger|action|condition|loop|end
      "label": "定时触发器",
      "config": {},
      "position": {"x": 100, "y": 200}
    }
  ],
  "edges": [
    {
      "id": "edge_1",
      "source": "node_1",
      "target": "node_2"
    }
  ],
  "metadata": {
    "name": "数据处理工作流",
    "created_at": "2024-01-20T10:32:15Z"
  }
}
```

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
    participant Server
    
    Client->>Server: POST /session
    Server-->>Client: {session_id}
    
    Client->>Server: GET /workflow?session_id=xxx
    Note over Client,Server: 建立SSE连接，等待推送
    
    loop 多轮对话
        Client->>Server: POST /chat
        Server-->>Client: SSE: AI回复
        
        alt 需要更多信息
            Server-->>Client: SSE: 询问细节
        else 信息充足
            Server-->>Client: SSE: signal "start_workflow_listening"
            Server-->>Client: Workflow SSE: 生成进度
            Server-->>Client: Workflow SSE: 完成 + JSON
        end
    end
```