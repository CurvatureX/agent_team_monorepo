# AI Provider重构指南

## 概述

新的AI Provider架构通过统一的接口处理所有AI提供商的调用和错误处理，解决了原有代码中依赖"⚠️"前缀检测错误的问题。

## 核心改进

### 1. 统一的错误类型
```python
class ErrorType(Enum):
    AUTH_ERROR = "auth_error"           # 认证错误
    RATE_LIMIT = "rate_limit"           # 限流错误
    INVALID_REQUEST = "invalid_request" # 请求参数错误
    MODEL_ERROR = "model_error"         # 模型相关错误
    NETWORK_ERROR = "network_error"     # 网络连接错误
    TIMEOUT = "timeout"                 # 超时错误
    RESPONSE_ERROR = "response_error"   # 响应内容错误
    UNKNOWN = "unknown"                 # 未知错误
```

### 2. 标准化的响应结构
```python
@dataclass
class AIResponse:
    success: bool           # 是否成功
    content: str           # AI生成的内容
    error_type: ErrorType  # 错误类型
    error_message: str     # 错误信息
    metadata: Dict         # 元数据（模型、用量等）
```

### 3. 多层错误检测
- **异常捕获层**：捕获特定的API异常
- **响应验证层**：验证API响应结构
- **内容检测层**：检测响应内容中的错误标记

## 使用示例

### 原代码（ai_agent_node.py中的方法）
```python
def _execute_openai_agent(self, input_text: str, params: dict) -> NodeExecutionResult:
    # ... 省略前面的代码 ...
    
    # 调用OpenAI API
    ai_response = self._call_openai_api(
        api_key=api_key,
        model=model_version,
        system_prompt=system_prompt,
        user_prompt=input_text,
        # ... 其他参数
    )
    
    # 检查是否是错误响应（不够健壮）
    if ai_response.startswith("⚠️"):
        # 处理错误
        return self._create_error_result(...)
    
    # 处理成功响应
    content = self._parse_ai_response(ai_response)
```

### 重构后的代码
```python
from workflow_engine.nodes.ai_providers import AIProviderFactory, ErrorType

def _execute_openai_agent(self, input_text: str, params: dict) -> NodeExecutionResult:
    # ... 省略前面的代码 ...
    
    # 创建provider实例
    provider = AIProviderFactory.create_from_subtype("OPENAI_CHATGPT", api_key=api_key)
    
    # 调用API（自动处理所有错误情况）
    response = provider.call_api(
        system_prompt=system_prompt,
        user_prompt=input_text,
        model=model_version,
        temperature=temperature,
        max_tokens=max_tokens,
        presence_penalty=presence_penalty,
        frequency_penalty=frequency_penalty,
        messages=conversation_messages  # 历史对话
    )
    
    # 根据响应状态处理
    if not response.success:
        # 错误已经被结构化处理
        logs.append(f"AI agent failed: {response.error_message}")
        return self._create_error_result(
            error_message=response.error_message,
            error_details={
                "error_type": response.error_type.value,
                "provider": "openai",
                "model": model_version,
            },
            execution_time=time.time() - start_time,
            logs=logs,
        )
    
    # 成功响应
    content = response.content  # 内容已经过验证
    
    # 可以访问元数据
    usage = response.metadata.get("usage", {})
    finish_reason = response.metadata.get("finish_reason")
```

## 完整的重构示例

### 简化后的execute方法
```python
def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
    """使用新的Provider架构执行AI节点"""
    start_time = time.time()
    logs = []
    
    try:
        # 获取节点子类型
        subtype = context.node.subtype
        
        # 获取参数
        system_prompt = self.get_parameter_with_spec(context, "system_prompt")
        model_version = self.get_parameter_with_spec(context, "model_version")
        temperature = self.get_parameter_with_spec(context, "temperature")
        max_tokens = self.get_parameter_with_spec(context, "max_tokens")
        
        # 准备输入
        user_input = self._prepare_input_for_ai(context.input_data)
        
        # 创建provider
        try:
            provider = AIProviderFactory.create_from_subtype(subtype)
        except ValueError as e:
            return self._create_error_result(
                error_message=str(e),
                execution_time=time.time() - start_time,
                logs=logs,
            )
        
        # 调用API
        logs.append(f"Calling {provider.__class__.__name__}")
        response = provider.call_api(
            system_prompt=system_prompt,
            user_prompt=user_input,
            model=model_version,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        # 处理响应
        if not response.success:
            logs.append(f"AI call failed: {response.error_message}")
            return self._create_error_result(
                error_message=response.error_message,
                error_details={
                    "error_type": response.error_type.value,
                    **response.metadata
                },
                execution_time=time.time() - start_time,
                logs=logs,
            )
        
        # 成功
        logs.append(f"AI call successful: {len(response.content)} chars")
        
        return self._create_success_result(
            output_data={
                "content": response.content,
                "metadata": response.metadata,
                "format_type": "text",
                "source_node": context.node.id,
                "timestamp": datetime.now().isoformat(),
            },
            execution_time=time.time() - start_time,
            logs=logs,
        )
        
    except Exception as e:
        return self._create_error_result(
            f"Unexpected error: {str(e)}",
            error_details={"exception": str(e)},
            execution_time=time.time() - start_time,
            logs=logs,
        )
```

## 重构步骤

1. **保留原有代码**：不要立即删除原有的`_call_openai_api`等方法
2. **逐步迁移**：先在一个provider上测试新架构
3. **并行运行**：可以同时运行新旧代码进行对比
4. **完全迁移**：确认无误后删除旧代码

## 优势总结

1. **更可靠的错误检测**：不依赖单一的"⚠️"标记
2. **统一的接口**：所有provider使用相同的调用方式
3. **更好的错误分类**：明确的错误类型便于处理和监控
4. **易于扩展**：添加新provider只需实现接口
5. **结构化响应**：便于日志记录和问题排查

## 测试建议

```python
# 测试错误处理
def test_error_handling():
    provider = OpenAIProvider(api_key="invalid_key")
    response = provider.call_api(
        system_prompt="Test",
        user_prompt="Hello",
        model="gpt-5"
    )
    
    assert not response.success
    assert response.error_type == ErrorType.AUTH_ERROR
    
# 测试成功调用
def test_successful_call():
    provider = OpenAIProvider()  # 使用环境变量中的key
    response = provider.call_api(
        system_prompt="You are helpful",
        user_prompt="Say hello",
        model="gpt-5-nano"
    )
    
    assert response.success
    assert len(response.content) > 0
    assert "usage" in response.metadata
```