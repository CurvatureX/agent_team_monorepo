---
id: api-gateway-architecture
title: "API Gateway 技术架构设计"
sidebar_label: "API Gateway 架构"
sidebar_position: 4
slug: /tech-design/api-gateway-architecture
---

# API Gateway 技术架构设计

## 概述

API Gateway 是 Workflow Agent Team 系统的前端网关服务，负责接收外部 HTTP 请求并通过 gRPC 与内部的 Workflow Agent 服务通信。基于 FastAPI 构建，提供高性能的 REST API 接口。

## 架构图

```mermaid
graph TB
    subgraph "External Clients"
        WEB[Web Frontend]
        MOBILE[Mobile App]
        API_CLIENT[API Clients]
    end

    subgraph "API Gateway Service"
        ROUTER[FastAPI Router]
        MIDDLEWARE[中间件层]
        GRPC_CLIENT[gRPC Client]
        AUTH[认证授权]
        LOGGING[日志记录]
    end

    subgraph "Internal Services"
        WORKFLOW_AGENT[Workflow Agent]
        WORKFLOW_RUNTIME[Workflow Runtime]
        WORKFLOW_ENGINE[Workflow Engine]
    end

    subgraph "Infrastructure"
        DB[(Database)]
        CACHE[(Redis Cache)]
    end

    WEB --> ROUTER
    MOBILE --> ROUTER
    API_CLIENT --> ROUTER

    ROUTER --> MIDDLEWARE
    MIDDLEWARE --> AUTH
    MIDDLEWARE --> LOGGING
    MIDDLEWARE --> GRPC_CLIENT

    GRPC_CLIENT --> WORKFLOW_AGENT
    GRPC_CLIENT --> WORKFLOW_RUNTIME
    GRPC_CLIENT --> WORKFLOW_ENGINE

    AUTH --> DB
    LOGGING --> DB
    ROUTER --> CACHE
```

## 核心组件

### 1. FastAPI 应用框架

**文件位置**: `apps/backend/api-gateway/main.py`

**核心特性**:
- 异步请求处理
- 自动 API 文档生成 (Swagger/OpenAPI)
- 数据验证 (Pydantic)
- 中间件支持

**配置示例**:
```python
app = FastAPI(
    title="API Gateway",
    description="API Gateway for Workflow Agent Team",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 2. 路由系统

**文件位置**: `apps/backend/api-gateway/routers/`

**API 端点结构**:
```
/api/v1/
├── session               # 会话管理 (workflow_agent)
│   └── POST /            # 创建新会话 {action: "create"|"edit", workflow_id?: string}
├── chat/                 # 对话交互 (workflow_agent)
│   └── stream            # GET - 流式对话 (SSE) ?session_id=xxx&user_message=yyy
├── workflow_generation   # 工作流生成 (workflow_agent)
│   └── GET /             # 监听生成进度 (SSE) ?session_id=xxx
├── workflow/
│   ├── execute           # POST - 直接执行工作流 (workflow_engine)
│   └── deployments/      # 部署管理 (workflow_runtime)
│       ├── POST /        # 部署工作流
│       ├── GET /         # 列出部署
│       ├── GET /{id}     # 获取部署状态
│       ├── PUT /{id}     # 更新部署
│       └── DELETE /{id}  # 删除部署
├── executions/           # 执行历史 (workflow_runtime)
│   ├── GET /             # 获取执行历史
│   └── GET /{id}         # 获取执行详情
├── webhooks/             # Webhook 端点 (workflow_runtime)
│   └── POST /{path}      # 动态 Webhook 触发器
├── health                # GET - 健康检查
└── docs                  # GET - API 文档
```

**请求/响应模型**:
```python
# Workflow Agent相关模型
class SessionCreateRequest(BaseModel):
    action: str  # "create" or "edit"
    workflow_id: Optional[str] = None

class SessionCreateResponse(BaseModel):
    session_id: str
    created_at: str

# SSE Chat Stream Response (text/event-stream)
class ChatStreamEvent(BaseModel):
    type: str  # "message"
    content: str

# SSE Workflow Generation Stream Response (text/event-stream)
class WorkflowGenerationEvent(BaseModel):
    type: str  # "waiting", "start", "draft", "debugging", "complete", "error"
    workflow_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

# Workflow Runtime相关模型
class WorkflowDeploymentRequest(BaseModel):
    workflow_definition: Dict[str, Any]
    triggers: List[Dict[str, Any]]
    name: str
    description: Optional[str] = None

class DeploymentResponse(BaseModel):
    deployment_id: str
    status: str
    webhook_url: Optional[str] = None
    created_at: str

class ExecutionHistoryResponse(BaseModel):
    executions: List[Dict[str, Any]]
    total_count: int
    page: int
    page_size: int

# Webhook触发模型
class WebhookTriggerData(BaseModel):
    workflow_id: str
    trigger_data: Dict[str, Any]
    timestamp: str
```

### 3. gRPC 客户端

**文件位置**: `apps/backend/api-gateway/core/grpc_client.py`

**主要功能**:
- 管理与多个内部服务的 gRPC 连接
- 协议缓冲区消息转换
- 连接池管理
- 错误处理和重试

**多服务连接管理**:
```python
class GRPCClientManager:
    def __init__(self):
        self.workflow_agent_client: Optional[WorkflowAgentClient] = None
        self.workflow_runtime_client: Optional[WorkflowRuntimeClient] = None
        self.workflow_engine_client: Optional[WorkflowEngineClient] = None

class WorkflowAgentClient:
    def __init__(self):
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub = None

    async def connect(self):
        server_address = f"{settings.WORKFLOW_AGENT_HOST}:{settings.WORKFLOW_AGENT_PORT}"
        self.channel = grpc.aio.insecure_channel(server_address)
        self.stub = workflow_agent_pb2_grpc.WorkflowAgentStub(self.channel)

    async def create_session(self, action: str, workflow_id: Optional[str] = None) -> dict:
        """Create new workflow agent session"""
        # gRPC call to workflow_agent
        pass

    async def stream_chat(self, session_id: str, user_message: str):
        """Stream chat responses from workflow_agent"""
        # gRPC streaming call to workflow_agent
        pass

    async def stream_workflow_generation(self, session_id: str):
        """Stream workflow generation progress from workflow_agent"""
        # gRPC streaming call to workflow_agent
        pass

class WorkflowRuntimeClient:
    def __init__(self):
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub = None

    async def connect(self):
        server_address = f"{settings.WORKFLOW_RUNTIME_HOST}:{settings.WORKFLOW_RUNTIME_PORT}"
        self.channel = grpc.aio.insecure_channel(server_address)
        self.stub = workflow_runtime_pb2_grpc.WorkflowRuntimeStub(self.channel)

class WorkflowEngineClient:
    def __init__(self):
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub = None

    async def connect(self):
        server_address = f"{settings.WORKFLOW_ENGINE_HOST}:{settings.WORKFLOW_ENGINE_PORT}"
        self.channel = grpc.aio.insecure_channel(server_address)
        self.stub = workflow_engine_pb2_grpc.WorkflowEngineStub(self.channel)
```

### 4. 配置管理

**文件位置**: `apps/backend/api-gateway/core/config.py`

**配置类别**:
- 应用配置 (调试模式、端口等)
- gRPC 服务端点配置
- CORS 策略配置
- 数据库连接配置
- 安全配置 (JWT、API 密钥等)

```python
class Settings(BaseSettings):
    APP_NAME: str = "API Gateway"
    DEBUG: bool = False

    # gRPC 服务配置
    WORKFLOW_AGENT_HOST: str = "localhost"
    WORKFLOW_AGENT_PORT: int = 50051

    WORKFLOW_RUNTIME_HOST: str = "localhost"
    WORKFLOW_RUNTIME_PORT: int = 50052

    WORKFLOW_ENGINE_HOST: str = "localhost"
    WORKFLOW_ENGINE_PORT: int = 50053

    # CORS 配置
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080"
    ]
```

## 数据流处理

### 1. 请求处理流程

```mermaid
sequenceDiagram
    participant Client
    participant Router
    participant Middleware
    participant gRPCClient
    participant WorkflowAgent
    participant WorkflowRuntime
    participant WorkflowEngine

    Client->>Router: HTTP Request
    Router->>Middleware: Process Request
    Middleware->>Middleware: 认证检查
    Middleware->>Middleware: 请求验证
    Middleware->>gRPCClient: 路由到对应服务

    alt Session Management
        gRPCClient->>WorkflowAgent: CreateSession gRPC
        WorkflowAgent->>gRPCClient: Session Response
    else Chat Stream
        gRPCClient->>WorkflowAgent: StreamChat gRPC
        WorkflowAgent->>gRPCClient: SSE Chat Stream
    else Workflow Generation Stream
        gRPCClient->>WorkflowAgent: StreamWorkflowGeneration gRPC
        WorkflowAgent->>gRPCClient: SSE Generation Stream
    else Workflow Deployment/Monitoring
        gRPCClient->>WorkflowRuntime: gRPC Request
        WorkflowRuntime->>gRPCClient: gRPC Response
    else Workflow Execution
        gRPCClient->>WorkflowEngine: gRPC Request
        WorkflowEngine->>gRPCClient: gRPC Response
    else Webhook Trigger
        gRPCClient->>WorkflowRuntime: TriggerWorkflow RPC
        WorkflowRuntime->>gRPCClient: Execution Status
    end

    gRPCClient->>Middleware: 转换响应
    Middleware->>Router: HTTP Response
    Router->>Client: JSON Response
```

### 2. 错误处理机制

**错误类型**:
- 请求验证错误 (400 Bad Request)
- 认证失败 (401 Unauthorized)
- 权限不足 (403 Forbidden)
- 资源未找到 (404 Not Found)
- 内部服务错误 (500 Internal Server Error)
- gRPC 通信错误 (502 Bad Gateway)

**错误响应格式**:
```python
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid request parameters",
        "details": {
            "field": "description",
            "reason": "This field is required"
        }
    }
}
```

## 性能优化

### 1. 异步处理

- 使用 FastAPI 的原生异步支持
- gRPC 异步客户端
- 数据库连接池
- 缓存策略

### 2. 连接管理

```python
# 应用生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化所有 gRPC 连接
    app.state.grpc_manager = GRPCClientManager()

    # 连接到所有内部服务
    await app.state.grpc_manager.workflow_agent_client.connect()
    await app.state.grpc_manager.workflow_runtime_client.connect()
    await app.state.grpc_manager.workflow_engine_client.connect()

    yield

    # 关闭时清理所有连接
    await app.state.grpc_manager.workflow_agent_client.close()
    await app.state.grpc_manager.workflow_runtime_client.close()
    await app.state.grpc_manager.workflow_engine_client.close()
```

### 3. 缓存策略

- API 响应缓存
- gRPC 连接复用
- 静态资源缓存

## 安全设计

### 1. 认证授权

```python
# JWT Token 验证
def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### 2. 输入验证

- Pydantic 模型验证
- SQL 注入防护
- XSS 攻击防护
- CSRF 保护

### 3. 限流保护

```python
# 基于 IP 的限流
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    # 实现限流逻辑
    return await call_next(request)
```

## 监控和日志

### 1. 结构化日志

```python
import structlog

logger = structlog.get_logger()

# 请求日志
logger.info("API request received",
           method=request.method,
           path=request.url.path,
           client_ip=request.client.host)
```

### 2. 健康检查

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "api-gateway",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }
```

### 3. 指标收集

- 请求量统计
- 响应时间监控
- 错误率跟踪
- gRPC 连接状态

## 部署配置

### 1. Docker 配置

```dockerfile
FROM python:3.11-slim

# 安装 uv 包管理器
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# 安装依赖
COPY pyproject.toml .
RUN uv pip install --system -e .

# 启动应用
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. 环境变量

```bash
# 应用配置
DEBUG=false
SECRET_KEY=your-secret-key

# gRPC 服务配置
WORKFLOW_AGENT_HOST=workflow-agent
WORKFLOW_AGENT_PORT=50051

WORKFLOW_RUNTIME_HOST=workflow-runtime
WORKFLOW_RUNTIME_PORT=50052

WORKFLOW_ENGINE_HOST=workflow-engine
WORKFLOW_ENGINE_PORT=50053

# 数据库配置
DATABASE_URL=postgresql://user:pass@localhost/db
```

## 服务路由策略

### 1. API 端点到服务的映射

```python
# 路由配置
SERVICE_ROUTES = {
    "/api/v1/session": "workflow_agent",
    "/api/v1/chat/stream": "workflow_agent",
    "/api/v1/workflow_generation": "workflow_agent",
    "/api/v1/workflow/execute": "workflow_engine",
    "/api/v1/workflow/deployments": "workflow_runtime",
    "/api/v1/executions": "workflow_runtime",
    "/api/v1/webhooks": "workflow_runtime"
}

class ServiceRouter:
    def __init__(self, grpc_manager: GRPCClientManager):
        self.grpc_manager = grpc_manager

    def route_request(self, path: str) -> str:
        """根据请求路径确定目标服务"""
        for route_prefix, service_name in SERVICE_ROUTES.items():
            if path.startswith(route_prefix):
                return service_name
        return "workflow_agent"  # 默认服务

    async def call_service(self, service_name: str, method: str, request_data: dict):
        """调用指定服务的方法"""
        if service_name == "workflow_agent":
            return await self.grpc_manager.workflow_agent_client.call_method(method, request_data)
        elif service_name == "workflow_runtime":
            return await self.grpc_manager.workflow_runtime_client.call_method(method, request_data)
        elif service_name == "workflow_engine":
            return await self.grpc_manager.workflow_engine_client.call_method(method, request_data)
        else:
            raise ValueError(f"Unknown service: {service_name}")
```

### 2. 动态 Webhook 路由

```python
class WebhookRouter:
    def __init__(self, workflow_runtime_client):
        self.runtime_client = workflow_runtime_client
        self._webhook_cache = {}  # 缓存 webhook 路径映射

    async def handle_webhook(self, webhook_path: str, request_data: dict):
        """处理动态 webhook 请求"""
        # 1. 从缓存或服务查找 workflow_id
        workflow_id = await self._resolve_webhook_path(webhook_path)
        if not workflow_id:
            raise HTTPException(404, "Webhook path not found")

        # 2. 调用 workflow_runtime 触发执行
        trigger_request = {
            "workflow_id": workflow_id,
            "trigger_data": request_data,
            "trigger_type": "webhook"
        }

        return await self.runtime_client.trigger_workflow(trigger_request)

    async def _resolve_webhook_path(self, webhook_path: str) -> Optional[str]:
        # 实现 webhook 路径到 workflow_id 的映射逻辑
        pass
```

### 3. 错误处理和重试

```python
class ServiceCallHandler:
    async def call_with_retry(self, service_name: str, method: str, request_data: dict, max_retries: int = 3):
        """带重试的服务调用"""
        for attempt in range(max_retries):
            try:
                return await self.call_service(service_name, method, request_data)
            except grpc.RpcError as e:
                if attempt == max_retries - 1:
                    # 最后一次重试失败，抛出 HTTP 异常
                    self._handle_grpc_error(e)
                await asyncio.sleep(2 ** attempt)  # 指数退避

    def _handle_grpc_error(self, error: grpc.RpcError):
        """将 gRPC 错误转换为 HTTP 错误"""
        if error.code() == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(404, "Resource not found")
        elif error.code() == grpc.StatusCode.INVALID_ARGUMENT:
            raise HTTPException(400, "Invalid request")
        elif error.code() == grpc.StatusCode.UNAVAILABLE:
            raise HTTPException(502, "Service unavailable")
        else:
            raise HTTPException(500, "Internal server error")
```

## 扩展性设计

### 1. 水平扩展

- 无状态服务设计
- 负载均衡支持
- 服务发现集成

### 2. 版本管理

```python
# API 版本路由
app.include_router(v1_router, prefix="/api/v1")
app.include_router(v2_router, prefix="/api/v2")
```

### 3. 插件系统

- 中间件插件化
- 认证策略可插拔
- 缓存后端可配置

## 最佳实践

### 1. 代码组织

```
api-gateway/
├── core/              # 核心配置和客户端
├── routers/           # API 路由定义
├── models/            # 数据模型
├── middleware/        # 中间件
├── utils/             # 工具函数
└── tests/             # 测试代码
```

### 2. 错误处理

- 统一异常处理器
- 详细的错误日志
- 用户友好的错误消息

### 3. 测试策略

```python
# 集成测试示例
@pytest.mark.asyncio
async def test_generate_workflow():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/v1/workflow/generate", json={
            "description": "Test workflow"
        })
    assert response.status_code == 200
```

## 故障排除

### 常见问题

1. **gRPC 连接失败**
   - 检查 Workflow Agent 服务状态
   - 验证网络连接和端口配置

2. **认证失败**
   - 检查 JWT Token 配置
   - 验证密钥设置

3. **性能问题**
   - 监控连接池使用情况
   - 检查缓存命中率
   - 分析慢查询日志

### 调试工具

- FastAPI 自动生成的交互式 API 文档
- 结构化日志分析
- Prometheus 指标监控
- gRPC 健康检查探针
