# CancelledError 详细解释

## 取消发生的确切时机

### 场景1：正常的第一次请求
```
时间线：
0ms   - 用户: "创建工作流"
10ms  - API Gateway 创建 SSE 连接到 Workflow Agent
20ms  - Workflow Agent: 发送 status_change (stage: clarification)
30ms  - Workflow Agent: 发送 message ("需要什么信息？")
40ms  - Workflow Agent: 设置 is_final=false
50ms  - API Gateway: 继续等待更多响应
5000ms - Workflow Agent: 完成处理
5010ms - 连接正常关闭
```

### 场景2：有问题的第二次请求（修复前）
```
时间线：
0ms   - 用户: "使用特定标签"
10ms  - API Gateway 创建新的 SSE 连接
20ms  - Workflow Agent: 检测到 pending_questions
30ms  - Workflow Agent: 返回相同的澄清问题
40ms  - API Gateway: 收到 workflow 响应，is_final=True（默认值）
50ms  - API Gateway: break 循环，开始关闭连接
60ms  - Workflow Agent: 还在尝试发送更多数据
70ms  - 连接已关闭 → CancelledError!
```

## 关键代码位置

1. **API Gateway 提前结束循环**：
```python
# chat.py 第288-289行
if response.get("is_final", True):  # 默认 True！
    break  # 这里提前结束了 async for 循环
```

2. **SSE 连接关闭**：
```python
async for response in workflow_client.process_conversation_stream(...):
    # 处理响应
    if is_final:
        break  # 退出循环
# 这里 async with 结束，连接关闭
```

3. **Workflow Agent 检测到取消**：
```python
# workflow_agent/services/fastapi_server.py
try:
    yield f"data: {response.model_dump_json()}\n\n"
except asyncio.CancelledError:
    # 客户端已断开！
```

## 为什么是 1 秒？

第二次请求在约 1 秒后取消，是因为：
1. Workflow Agent 快速检测到有 pending_questions
2. 立即返回相同的问题（不需要调用 LLM）
3. API Gateway 收到后立即 break
4. 整个过程很快，约 1 秒

## 总结

CancelledError 的根本原因：
1. `is_final` 的默认值设置错误（应该是 False 而不是 True）
2. 导致 SSE 流提前结束
3. Workflow Agent 还在处理时连接已断开

修复方法：
1. 正确设置 `is_final` 的逻辑
2. 只在真正完成时才设置为 true
3. 确保 SSE 流的生命周期与处理逻辑匹配