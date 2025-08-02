# is_final 最佳实践

## 默认值设置原则

### ✅ 推荐：默认 False
```python
is_final = response.get("is_final", False)
```

### ❌ 避免：默认 True
```python
is_final = response.get("is_final", True)  # 危险！
```

## 原因分析

### 1. 防御性编程
- 宁可多等待，不可早断开
- 避免数据丢失

### 2. 明确的完成信号
```python
# Workflow Agent 应该明确告知完成
return ConversationResponse(
    session_id=session_id,
    response_type=ResponseType.WORKFLOW,
    workflow=workflow_json,
    is_final=True  # 明确设置
)
```

### 3. 统一的行为
所有响应类型应该保持一致：
- STATUS_CHANGE: 默认 False ✅
- MESSAGE: 默认 False ✅
- WORKFLOW: 默认 False ✅
- ERROR: 默认 True ✅ (错误时应该结束)

### 4. 超时保护
即使默认 False，也有超时机制：
```python
timeout = httpx.Timeout(
    timeout=300.0,  # 5分钟总超时
    connect=10.0,   # 10秒连接超时
    read=30.0       # 30秒读取超时
)
```

## 实施检查清单

- [x] API Gateway 所有响应类型默认 False
- [x] Workflow Agent 在适当时机显式设置 is_final=True
- [x] 错误响应显式设置 is_final=True
- [x] 超时配置合理

这样的设计更加健壮和安全！