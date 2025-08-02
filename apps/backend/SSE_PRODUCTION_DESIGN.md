# SSE 生产环境设计方案

## 当前问题

1. **SSE 连接特性**：
   - SSE 是单向的服务器推送
   - 连接断开后需要客户端重新建立
   - 不适合长时间保持连接

2. **实际场景**：
   - 用户可能在消息之间有很长的间隔
   - 服务可能重启或扩缩容
   - 网络可能中断

## 推荐的生产方案

### 方案1：短连接 + 轮询（Simple but Effective）

```python
# API Gateway
async def chat_stream():
    # 每次请求都是独立的，不依赖之前的连接
    session_state = await get_session_state(session_id)
    
    # 处理消息
    async for response in workflow_agent.process_message(
        session_id=session_id,
        message=user_message,
        state=session_state  # 传递完整状态
    ):
        yield response
    
    # 保存状态
    await save_session_state(session_id, new_state)
```

### 方案2：WebSocket with Reconnection（更复杂但更强大）

```python
# 使用 WebSocket 替代 SSE
@app.websocket("/ws/chat/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    
    # 支持断线重连
    last_message_id = await websocket.receive_json().get("last_message_id")
    
    # 从上次断开的地方继续
    messages = await get_messages_since(session_id, last_message_id)
    for msg in messages:
        await websocket.send_json(msg)
    
    # 继续处理新消息
    while True:
        data = await websocket.receive_json()
        # 处理消息
```

### 方案3：混合方案（推荐）

```python
# 1. 使用 SSE 进行实时流式响应（单个请求内）
# 2. 使用会话状态持久化（跨请求）
# 3. 每次请求都是独立的

class ChatService:
    async def process_message(self, session_id: str, message: str):
        # 1. 加载会话状态
        session = await self.load_session(session_id)
        
        # 2. 处理消息（流式）
        async for chunk in self.workflow_agent.stream_process(
            session_id=session_id,
            message=message,
            context=session.context
        ):
            yield chunk
        
        # 3. 保存会话状态
        await self.save_session(session_id, session)

# 客户端实现自动重连
class ChatClient:
    async def send_message(self, message: str):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async for response in self.stream_chat(message):
                    yield response
                break
            except ConnectionError:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # 指数退避
                else:
                    raise
```

## 最佳实践建议

1. **状态持久化**：
   - 所有会话状态保存在数据库（Supabase）
   - 不依赖内存或连接状态

2. **请求独立性**：
   - 每个请求都是无状态的
   - 通过 session_id 关联历史

3. **优雅降级**：
   - 连接断开时保存当前状态
   - 支持从断点继续

4. **超时控制**：
   ```python
   # 设置合理的超时
   timeout = httpx.Timeout(
       connect=5.0,      # 连接超时
       read=30.0,        # 读取超时
       write=10.0,       # 写入超时
       pool=None         # 不限制连接池超时
   )
   ```

5. **错误处理**：
   - 区分可恢复错误（网络）和不可恢复错误（业务）
   - 提供清晰的错误信息

## 具体实现建议

对于当前系统，建议的改进：

1. **移除长连接依赖**：
   - 每个 `/chat/stream` 请求都是独立的
   - 不假设之前的连接还存在

2. **增强状态管理**：
   ```python
   # workflow_agent_states 表已经存储了完整状态
   # 确保每次请求都能恢复完整上下文
   ```

3. **客户端改进**：
   ```javascript
   // 前端实现自动重连
   class ChatAPI {
     async sendMessage(sessionId, message) {
       const eventSource = new EventSource(
         `/api/app/chat/stream?session_id=${sessionId}&message=${message}`
       );
       
       eventSource.onerror = (error) => {
         eventSource.close();
         // 可以选择重试或提示用户
       };
       
       return eventSource;
     }
   }
   ```

这样的设计更适合生产环境，能够处理各种异常情况。