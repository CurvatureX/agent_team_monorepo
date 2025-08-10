# AI Teams 分布式监控系统实施指南

## 系统概览

**目标**: 构建基于 OpenTelemetry + 本地 Jaeger + Grafana Cloud 的混合监控栈

**架构原则**:

- 本地 Jaeger: 追踪调试
- Grafana Cloud: 仪表板 + 长期存储
- 环境标签: dev/prod 共享云端实例

## 核心组件

### 本地保留

- **Jaeger**: 本地追踪调试 (端口 16686)
- **Prometheus**: 短期指标存储 (7 天)
- **OTel Collector**: 数据预处理 + 环境标签注入

### Grafana Cloud 替换

- **Grafana UI**: 统一仪表板 (免费: 5 用户)
- **Mimir**: 长期指标存储 (免费: 10K series)
- **Loki**: 日志聚合 (免费: 50GB/月)
- **OnCall**: 告警管理 (免费: 5 集成)

## 实施任务清单

### 🎯 必需标签配置

所有指标必须包含以下标签：

```yaml
environment: "dev" | "prod" | "staging"
project: "starmates-ai-team"
service: "api-gateway" | "workflow-engine" | "workflow-agent"
```

### 📁 文件创建任务

#### 1. 监控配置文件

- `monitoring/otel-collector-config.yml` - OTel Collector 混合配置
- `docker-compose.monitoring.yml` - 简化监控栈
- `.env.monitoring` - Grafana Cloud 环境变量

#### 2. Python SDK 文件

- `apps/backend/shared/telemetry/complete_stack.py` - 统一监控 SDK
- `apps/backend/shared/telemetry/middleware.py` - FastAPI 中间件
- `apps/backend/shared/telemetry/metrics.py` - 核心指标定义

#### 3. 基础设施文件

- `infra/monitoring.tf` - Terraform Grafana Cloud 集成
- 更新 `infra/ecs.tf` - ECS 任务环境变量

## 追踪标识符 (Track ID) 管理

### 🆔 **Track ID 生成与传播**

所有 API 请求和服务调用都必须包含 `track_id` 用于分布式追踪：

#### A. 统一追踪标识符策略 (基于 OpenTelemetry)

**核心思路：直接使用 OpenTelemetry Trace ID 作为统一的 tracking_id**

**1. 统一 ID 格式**

- **唯一格式**: OpenTelemetry 128-bit trace ID (32位十六进制)
  - 例: `4bf92f3577b34da6a3ce929d0e0e4736`
- **全场景使用**: 客户端、服务间、数据库、日志全部使用相同ID
- **HTTP Header**: `X-Tracking-ID` 返回完整格式给客户端

**2. 零侵入实现方案**

```python
class TrackingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # OpenTelemetry 自动处理所有追踪逻辑，无需手动传播
        span = trace.get_current_span()

        if span.is_recording():
            # 直接使用 OpenTelemetry 的完整 trace_id 作为 tracking_id
            tracking_id = format(span.get_span_context().trace_id, '032x')

            # 添加到 span 属性，便于业务查询
            span.set_attribute("tracking.id", tracking_id)

            # 存储到请求状态，供业务代码使用
            request.state.tracking_id = tracking_id

        response = await call_next(request)

        # 返回完整的 tracking_id 给客户端
        if hasattr(request.state, 'tracking_id'):
            response.headers["X-Tracking-ID"] = request.state.tracking_id

        return response

# 主应用初始化 - 一次性配置
def setup_telemetry(app: FastAPI):
    # 1. 配置 OpenTelemetry 导出器
    trace.set_tracer_provider(TracerProvider())
    otlp_exporter = OTLPSpanExporter(endpoint="http://otel-collector:4317")
    span_processor = BatchSpanProcessor(otlp_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)

    # 2. 自动装配 - 核心优势！
    FastAPIInstrumentor().instrument_app(app)  # 自动追踪所有请求
    RequestsInstrumentor().instrument()        # 自动追踪所有HTTP调用

    # 3. 添加统一追踪中间件
    app.add_middleware(TrackingMiddleware)
```

**3. 自动化传播机制**

```python
# 服务间调用示例 - 完全自动化
@app.post("/api/v1/sessions")
async def create_session(request: Request, session_data: SessionCreate):
    tracking_id = request.state.tracking_id  # 完整的 OpenTelemetry trace ID

    # 调用其他服务 - OpenTelemetry 自动传播完整 trace context
    # 无需手动添加任何 header！
    response = await httpx.post(
        f"{WORKFLOW_AGENT_URL}/generate",
        json=session_data.dict()
        # OpenTelemetry 自动注入 traceparent header
    )

    # 保存到数据库 - 使用完整 tracking_id
    db_session = Session(
        id=str(uuid.uuid4()),
        tracking_id=tracking_id,  # 完整的32位格式
        user_id=session_data.user_id,
        created_at=datetime.utcnow()
    )

    logger.info(
        f"Created session for user {session_data.user_id}",
        extra={
            "tracking_id": tracking_id,
            "session_id": db_session.id,
            "user_id": session_data.user_id
        }
    )

    return {"session_id": db_session.id, "tracking_id": tracking_id}
```

**4. 统一追踪的优势**

- ✅ **零侵入**: OpenTelemetry 自动处理所有 header 传播
- ✅ **完全统一**: 所有场景使用同一个 trace ID，无任何混淆
- ✅ **自动关联**: 日志、metrics、traces 自动包含相同标识符
- ✅ **标准兼容**: 完全遵循 W3C Trace Context 标准

#### 统一追踪传播机制

- **技术层面**: OpenTelemetry 自动传播 `traceparent` header (W3C标准)
- **业务层面**: 完整的 32位 `tracking_id` 用于客户端和数据库
- **响应头**: 返回 `X-Tracking-ID` (完整格式) 便于客户端追踪
- **完美对应**: tracking_id 直接对应 OpenTelemetry trace_id，无转换

### 📊 **自动化服务调用实现**

#### 完全自动化的服务间调用

```python
# API Gateway → Workflow Agent (零手动配置)
async def call_workflow_agent(request: Request, payload: dict):
    # 无需手动传递任何 header - OpenTelemetry 自动处理！
    response = await httpx.post(
        f"{WORKFLOW_AGENT_URL}/generate-workflow",
        json=payload
        # traceparent header 自动注入
    )

    # 业务代码使用统一的 tracking_id
    tracking_id = request.state.tracking_id
    logger.info(f"Called workflow agent with tracking_id: {tracking_id}")

    return response

# API Gateway → Workflow Engine (同样零配置)
async def execute_workflow(request: Request, workflow_data: dict):
    response = await httpx.post(
        f"{WORKFLOW_ENGINE_URL}/execute",
        json=workflow_data
        # OpenTelemetry 自动传播完整的 trace context
    )

    return response
```

#### 统一中间件 - 极简实现

```python
# 只需要这一个中间件！
class TrackingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        span = trace.get_current_span()

        if span.is_recording():
            # 直接使用 OpenTelemetry 的完整 trace_id
            tracking_id = format(span.get_span_context().trace_id, '032x')

            # 存储供业务使用
            request.state.tracking_id = tracking_id

            # 添加到 span 便于查询
            span.set_attribute("tracking.id", tracking_id)

        response = await call_next(request)

        # 返回完整 tracking_id 给客户端
        if hasattr(request.state, 'tracking_id'):
            response.headers["X-Tracking-ID"] = request.state.tracking_id

        return response

# 应用启动时的一次性配置
def main():
    app = FastAPI()

    # 1. 配置 OpenTelemetry
    setup_telemetry(app)

    # 2. 添加统一追踪中间件
    app.add_middleware(TrackingMiddleware)

    # 就这样！所有追踪自动工作
```

## C. 日志关联规范

### 📝 **1. 结构化日志要求**

所有服务必须使用 **JSON 格式** 的结构化日志，**完全适配 AWS CloudWatch Logs**：

```python
# AWS CloudWatch 优化的日志格式
{
    "@timestamp": "2025-01-31T10:30:45.123Z",
    "@level": "INFO",
    "@message": "POST /api/v1/sessions - 201",
    "service": "api-gateway",
    "tracking_id": "4bf92f3577b34da6a3ce929d0e0e4736",  # 完整的 OpenTelemetry trace ID
    "request": {  # 嵌套对象支持点号查询
        "method": "POST",
        "path": "/api/v1/sessions",
        "duration": 0.245,
        "size": 1024
    },
    "response": {
        "status": 201,
        "size": 2048
    },
    "user": {
        "id": "user_12345",
        "segment": "premium"
    },
    "session": {
        "id": "session_67890"
    },
    "tracing": {
        "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",  # OpenTelemetry trace ID (与 tracking_id 相同)
        "span_id": "1a2b3c4d5e6f7890"
    }
}
```

### 🔍 **CloudWatch Logs Insights 查询优化**

**嵌套字段查询 (点号表示法)**：

```sql
# 查询特定用户的错误请求
fields @timestamp, message, request.method, response.status
| filter user.id = "user_12345" and response.status >= 400
| sort @timestamp desc

# 按服务和端点分组统计
fields @timestamp, service, request.path, request.duration
| filter request.duration > 1.0
| stats count() by service, request.path
```

### 🏷️ **CloudWatch 字段索引优化**

**索引字段 (提升查询性能)**：

- `@timestamp` - 自动索引时间字段
- `@level` - 日志级别索引
- `@message` - 消息内容索引
- `tracking_id` - 统一追踪 ID 索引 (32位 OpenTelemetry trace ID)
- `service` - 服务名索引
- `request.method` - HTTP 方法索引
- `response.status` - 状态码索引

### 🔗 **2. Tracking ID 必须包含**

**所有日志记录必须包含 `tracking_id` 字段**：

```python
# CloudWatch 优化的 TracingFormatter
class CloudWatchTracingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # 获取当前请求的 tracking_id
        tracking_id = getattr(record, 'tracking_id', None)
        if not tracking_id:
            tracking_id = getattr(current_request.state, 'tracking_id', 'unknown')

        timestamp = datetime.utcnow().isoformat() + "Z"

        # CloudWatch 优化格式 (统一使用 OpenTelemetry trace ID)
        log_entry = {
            "@timestamp": timestamp,
            "@level": record.levelname,
            "@message": record.getMessage(),
            "service": self.service_name,
            "tracking_id": tracking_id,  # 完整的32位 OpenTelemetry trace ID
            "source": {
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno
            }
        }

        # 结构化额外字段
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in EXCLUDED_FIELDS:
                extra_fields[key] = value

        # 按类型分组字段，便于 CloudWatch 查询
        if 'request_method' in extra_fields:
            log_entry['request'] = {
                'method': extra_fields.get('request_method'),
                'path': extra_fields.get('request_path'),
                'duration': extra_fields.get('request_duration'),
                'size': extra_fields.get('request_size')
            }

        if 'response_status' in extra_fields:
            log_entry['response'] = {
                'status': extra_fields.get('response_status'),
                'size': extra_fields.get('response_size')
            }

        if 'user_id' in extra_fields:
            log_entry['user'] = {
                'id': extra_fields.get('user_id'),
                'segment': extra_fields.get('user_segment')
            }

        if 'session_id' in extra_fields:
            log_entry['session'] = {
                'id': extra_fields.get('session_id'),
                'duration': extra_fields.get('session_duration')
            }

        # 添加追踪信息 (tracking_id 已经是完整的 trace_id)
        span = trace.get_current_span()
        if span.is_recording():
            span_context = span.get_span_context()
            log_entry['tracing'] = {
                'trace_id': tracking_id,  # 与 tracking_id 相同，都是完整的 trace_id
                'span_id': format(span_context.span_id, '016x')
            }

        return json.dumps(log_entry, ensure_ascii=False, separators=(',', ':'))
```

### ⚠️ **3. ERROR 级别自动创建 Span Events**

**所有 ERROR 日志自动在 OpenTelemetry Span 中创建事件**：

```python
class TracingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # ... 基础格式化 ...

        # ERROR 级别自动创建 span event
        if record.levelno >= logging.ERROR:
            span = trace.get_current_span()
            if span and span.get_span_context().is_valid:

                # 记录异常信息
                if record.exc_info:
                    exception = record.exc_info[1]
                    span.record_exception(exception)
                    span.set_status(Status(StatusCode.ERROR, record.getMessage()))

                # 创建错误事件
                span.add_event(
                    name="error_log",
                    attributes={
                        "log.level": record.levelname,
                        "log.message": record.getMessage(),
                        "log.logger": record.name,
                        "log.module": record.module,
                        "log.function": record.funcName,
                        "log.line": record.lineno,
                        "tracking.id": log_entry["tracking_id"],
                        "error.type": type(exception).__name__ if record.exc_info else "UnknownError"
                    },
                    timestamp=time.time_ns()
                )

        return json.dumps(log_entry, ensure_ascii=False)
```

### 🔍 **4. 关联机制实现**

#### 日志-追踪关联

```python
# 请求日志自动包含 tracking_id
logger.info(
    f"{method} {path} - {status_code}",
    extra={
        "tracking_id": getattr(request.state, 'tracking_id', None),
        "request_method": method,
        "request_path": path,
        "response_status": status_code,
        "request_duration": duration,
        "user_id": getattr(request.state, 'user_id', None),
        "session_id": getattr(request.state, 'session_id', None)
    }
)
```

#### 数据库操作关联

```python
# 业务数据必须包含 tracking_id
async def create_workflow_session(tracking_id: str, user_id: str):
    session_data = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "tracking_id": tracking_id,  # 必需字段
        "created_at": datetime.utcnow(),
        "status": "active"
    }

    # 日志记录包含相同 tracking_id
    logger.info(
        f"Created workflow session for user {user_id}",
        extra={
            "tracking_id": tracking_id,
            "session_id": session_data["id"],
            "user_id": user_id,
            "operation": "create_session"
        }
    )

    await db.sessions.insert(session_data)
```

#### Span 属性关联

```python
# OpenTelemetry Span 必须包含 tracking_id
span.set_attributes({
    "tracking.id": tracking_id,
    "service.name": service_name,
    "operation.name": operation_name,
    "user.id": user_id,
    "session.id": session_id,
    "request.method": method,
    "request.path": path,
    "request.size": request_size,
    "response.size": response_size
})
```

### 📋 **5. CloudWatch 日志字段标准**

#### 必需字段 (所有日志)

```json
{
  "@timestamp": "2025-01-31T10:30:45.123Z",
  "@level": "INFO|WARN|ERROR|DEBUG",
  "@message": "Human readable message",
  "service": "api-gateway|workflow-agent|workflow-engine",
  "tracking_id": "4bf92f3577b34da6a3ce929d0e0e4736"
}
```

#### HTTP 请求结构 (嵌套对象)

```json
{
  "request": {
    "method": "GET|POST|PUT|DELETE",
    "path": "/api/v1/sessions",
    "size": 1024,
    "duration": 0.245,
    "user_agent": "Mozilla/5.0...",
    "ip": "192.168.1.100"
  },
  "response": {
    "status": 200,
    "size": 2048,
    "content_type": "application/json"
  }
}
```

#### 业务操作结构

```json
{
  "user": {
    "id": "user_12345",
    "segment": "premium|free|enterprise"
  },
  "session": {
    "id": "session_67890",
    "duration": 1200
  },
  "workflow": {
    "id": "workflow_abc123",
    "type": "simple|complex|ai-assisted",
    "status": "running|completed|failed"
  },
  "operation": {
    "name": "create_session|execute_workflow|generate_response",
    "result": "success|failure|partial",
    "duration": 0.325
  }
}
```

#### 错误结构 (ERROR 级别)

```json
{
  "error": {
    "type": "ValidationError|BusinessLogicError|SystemError",
    "code": "E001|E002|E003",
    "message": "Detailed error description",
    "category": "client|server|network|timeout"
  },
  "exception": {
    "class": "ValueError",
    "stack_trace": "Full stack trace for debugging",
    "file": "app/handlers/session.py",
    "line": 42
  }
}
```

### 💰 **成本优化配置**

**字段数量限制 (CloudWatch 最多 1000 字段)**：

```python
class CloudWatchFormatter:
    MAX_FIELDS = 900  # 保留 100 字段余量

    def _limit_fields(self, log_entry: dict) -> dict:
        """限制字段数量，避免 CloudWatch 截断"""
        if self._count_fields(log_entry) > self.MAX_FIELDS:
            # 保留核心字段，移除详细字段
            return self._keep_essential_fields(log_entry)
        return log_entry
```

**日志级别过滤 (减少存储成本)**：

```yaml
# 生产环境配置
production:
  log_level: "WARN" # 只记录 WARN 和 ERROR

# 开发环境配置
development:
  log_level: "DEBUG" # 记录所有级别
```

## 核心配置模板

### OTel Collector 混合配置

`monitoring/otel-collector-config.yml`

```yaml
receivers:
  otlp:
    protocols:
      grpc: { endpoint: 0.0.0.0:4317 }
      http: { endpoint: 0.0.0.0:4318 }

processors:
  resource:
    attributes:
      - key: deployment.environment
        value: "${ENVIRONMENT}"
        action: upsert
  memory_limiter: { limit_mib: 512 }
  batch: { timeout: 1s }

exporters:
  # 本地 Jaeger
  jaeger:
    endpoint: jaeger:14250
    tls: { insecure: true }

  # 本地 Prometheus
  prometheus:
    endpoint: "0.0.0.0:8888"
    const_labels:
      environment: "${ENVIRONMENT}"
      project: "ai-teams-monorepo"

  # Grafana Cloud Mimir
  prometheusremotewrite/grafana-cloud:
    endpoint: "${GRAFANA_CLOUD_PROMETHEUS_URL}"
    headers:
      authorization: "Bearer ${GRAFANA_CLOUD_TENANT_ID}:${GRAFANA_CLOUD_API_KEY}"
    external_labels:
      environment: "${ENVIRONMENT}"
      project: "ai-teams-monorepo"

  # Grafana Cloud Loki
  loki/grafana-cloud:
    endpoint: "${GRAFANA_CLOUD_LOKI_URL}"
    headers:
      authorization: "Bearer ${GRAFANA_CLOUD_TENANT_ID}:${GRAFANA_CLOUD_API_KEY}"

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, resource, batch]
      exporters: [jaeger]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, resource, batch]
      exporters: [prometheus, prometheusremotewrite/grafana-cloud]
    logs:
      receivers: [otlp]
      processors: [memory_limiter, resource, batch]
      exporters: [loki/grafana-cloud]
```

### 简化 Docker Compose

`docker-compose.monitoring.yml`

```yaml
version: "3.8"
services:
  otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    volumes:
      - ./monitoring/otel-collector-config.yml:/etc/otel-collector-config.yml:ro
    ports:
      - "4317:4317" # OTLP gRPC
      - "4318:4318" # OTLP HTTP
      - "8888:8888" # Prometheus
    environment:
      - ENVIRONMENT=${ENVIRONMENT:-dev}
      - GRAFANA_CLOUD_API_KEY=${GRAFANA_CLOUD_API_KEY}
      - GRAFANA_CLOUD_PROMETHEUS_URL=${GRAFANA_CLOUD_PROMETHEUS_URL}
      - GRAFANA_CLOUD_LOKI_URL=${GRAFANA_CLOUD_LOKI_URL}
      - GRAFANA_CLOUD_TENANT_ID=${GRAFANA_CLOUD_TENANT_ID}

  jaeger:
    image: jaegertracing/all-in-one:latest
    ports: ["16686:16686", "14250:14250"]
    environment: [COLLECTOR_OTLP_ENABLED=true]

  prometheus:
    image: prom/prometheus:latest
    ports: ["9090:9090"]
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.retention.time=7d"
```

### 环境变量配置

`.env.monitoring`

```bash
# 开发环境
ENVIRONMENT=dev
GRAFANA_CLOUD_API_KEY=glc_eyJrIjoixxxxxxxx
GRAFANA_CLOUD_PROMETHEUS_URL=https://prometheus-prod-01-eu-west-0.grafana.net/api/prom/push
GRAFANA_CLOUD_LOKI_URL=https://logs-prod-006.grafana.net/loki/api/v1/push
GRAFANA_CLOUD_TENANT_ID=123456

# 生产环境：使用相同 API Key，通过 environment 标签区分
```

## Terraform 基础设施更新

### 新增 Grafana Cloud 集成

`infra/monitoring.tf`

```hcl
variable "grafana_cloud_api_key" {
  description = "Grafana Cloud API Key"
  type        = string
  sensitive   = true
}

resource "aws_ssm_parameter" "grafana_cloud_api_key" {
  name  = "/ai-teams/${var.environment}/monitoring/grafana-cloud-api-key"
  type  = "SecureString"
  value = var.grafana_cloud_api_key
}

resource "aws_ssm_parameter" "grafana_cloud_config" {
  name = "/ai-teams/${var.environment}/monitoring/grafana-cloud-config"
  type = "String"
  value = jsonencode({
    tenant_id     = var.grafana_cloud_tenant_id
    prometheus_url = "https://prometheus-prod-01-eu-west-0.grafana.net/api/prom/push"
    loki_url      = "https://logs-prod-006.grafana.net/loki/api/v1/push"
  })
}
```

### 更新 ECS 任务定义

`infra/ecs.tf` - 添加 OTel Collector 环境变量

```hcl
resource "aws_ecs_task_definition" "otel_collector" {
  family = "ai-teams-otel-collector-${var.environment}"
  container_definitions = jsonencode([{
    name  = "otel-collector"
    image = "otel/opentelemetry-collector-contrib:latest"
    environment = [
      { name = "ENVIRONMENT", value = var.environment }
    ]
    secrets = [
      { name = "GRAFANA_CLOUD_API_KEY", valueFrom = aws_ssm_parameter.grafana_cloud_api_key.arn }
    ]
  }])
}
```

## 实施步骤

### 阶段 1: 环境准备 (30 分钟)

1. **注册 Grafana Cloud 免费账号**

   - 获取 API Key 和 Tenant ID
   - 配置 Prometheus + Loki 端点

2. **创建监控目录结构**
   ```bash
   mkdir -p monitoring
   mkdir -p apps/backend/shared/telemetry
   ```

### 阶段 2: 配置文件部署 (1 小时)

1. **创建上述模板文件**

   - `monitoring/otel-collector-config.yml`
   - `docker-compose.monitoring.yml`
   - `.env.monitoring`

2. **启动监控栈**
   ```bash
   docker-compose -f docker-compose.monitoring.yml up -d
   ```

### 阶段 3: 应用集成 (2 小时)

1. **安装依赖**

   ```bash
   pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi
   ```

2. **创建集成代码**

   - `apps/backend/shared/telemetry/complete_stack.py` - 统一 SDK
   - 更新各服务 `main.py` 添加中间件

3. **验证数据流**
   - Jaeger UI: http://localhost:16686
   - Prometheus: http://localhost:9090
   - Grafana Cloud: 登录查看指标

### 阶段 4: 基础设施更新 (1 小时)

1. **更新 Terraform 配置**

   - 添加 `infra/monitoring.tf`
   - 更新 `infra/ecs.tf` 环境变量

2. **部署到 AWS**
   ```bash
   cd infra
   terraform plan -var="grafana_cloud_api_key=$API_KEY"
   terraform apply
   ```

## 成本分析

### 免费层限制

- **Grafana Cloud**: 5 用户, 10K metrics, 50GB 日志/月
- **AWS**: ~$60-110/月 (vs 全本地 $200-400/月)

### 扩展成本

- **用户 100+**: Grafana Pro $29/月
- **用户 1000+**: Grafana Advanced $299/月

## B. Metrics 收集策略

### 📊 **1. 基础指标 (Infrastructure Metrics)**

所有服务必须收集的核心性能指标：

```python
# HTTP 请求指标
request_count = Counter(
    'request_count',
    'Total number of HTTP requests',
    ['service_name', 'endpoint', 'method', 'status_code', 'api_version']
)

request_duration = Histogram(
    'request_duration_seconds',
    'HTTP request duration in seconds',
    ['service_name', 'endpoint', 'method'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
)

request_errors = Counter(
    'request_errors_total',
    'Total number of HTTP request errors',
    ['service_name', 'endpoint', 'method', 'error_type', 'status_code']
)

active_requests = Gauge(
    'active_requests',
    'Number of active HTTP requests',
    ['service_name', 'endpoint']
)
```

### 🏢 **2. 业务指标 (Business Metrics)**

业务层面的关键指标：

```python
# API 使用情况
api_key_usage = Counter(
    'api_key_usage_total',
    'API key usage by client',
    ['api_key_id', 'client_name', 'service_name', 'endpoint', 'success']
)

endpoint_usage = Counter(
    'endpoint_usage_total',
    'Endpoint usage frequency',
    ['service_name', 'endpoint', 'api_version', 'user_segment']
)

user_activity = Counter(
    'user_activity_total',
    'User activity events',
    ['user_id', 'activity_type', 'service_name', 'session_id']
)

# 业务成功率
workflow_success_rate = Histogram(
    'workflow_success_rate',
    'Workflow execution success rate',
    ['workflow_type', 'complexity_level'],
    buckets=[0.0, 0.5, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0]
)
```

### 🏷️ **3. 标签维度 (Label Dimensions)**

所有指标必须包含的标准化标签：

#### 核心标签 (所有指标必需)

```yaml
service_name: # "api-gateway" | "workflow-agent" | "workflow-engine"
environment: # "dev" | "staging" | "prod"
version: # API 版本号 "v1" | "v2"
tracking_id: # UUID v4 格式的追踪 ID
```

#### HTTP 请求标签

```yaml
endpoint: # 标准化端点 "/api/v1/sessions/{id}"
method: # HTTP 方法 "GET" | "POST" | "PUT" | "DELETE"
status_code: # HTTP 状态码 "200" | "400" | "500"
api_version: # API 版本 "v1" | "v2"
user_agent: # 客户端类型 "web" | "mobile" | "mcp-client"
```

#### 业务指标标签

```yaml
user_segment: # 用户分组 "free" | "premium" | "enterprise"
client_type: # 客户端类型 "web-app" | "mobile-app" | "api-client"
workflow_type: # 工作流类型 "simple" | "complex" | "ai-assisted"
error_category: # 错误分类 "validation" | "business" | "system"
```

### 📈 **指标收集实现**

```python
# 在 MetricsMiddleware 中实现
class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        tracking_id = getattr(request.state, 'tracking_id', 'unknown')

        # 增加活跃请求
        active_requests.labels(
            service_name=self.service_name,
            endpoint=self._normalize_endpoint(request.url.path)
        ).inc()

        try:
            response = await call_next(request)

            # 记录成功请求
            duration = time.time() - start_time
            labels = {
                'service_name': self.service_name,
                'endpoint': self._normalize_endpoint(request.url.path),
                'method': request.method,
                'status_code': str(response.status_code),
                'api_version': self._extract_api_version(request.url.path),
                'tracking_id': tracking_id
            }

            request_count.labels(**labels).inc()
            request_duration.labels(
                service_name=labels['service_name'],
                endpoint=labels['endpoint'],
                method=labels['method']
            ).observe(duration)

            return response

        except Exception as e:
            # 记录错误
            request_errors.labels(
                service_name=self.service_name,
                endpoint=self._normalize_endpoint(request.url.path),
                method=request.method,
                error_type=type(e).__name__,
                status_code="500"
            ).inc()
            raise

        finally:
            # 减少活跃请求
            active_requests.labels(
                service_name=self.service_name,
                endpoint=self._normalize_endpoint(request.url.path)
            ).dec()
```

## 核心指标定义

### HTTP 基础指标

- `request_count{service_name, endpoint, method, status_code, api_version, tracking_id}`
- `request_duration_seconds{service_name, endpoint, method}`
- `request_errors_total{service_name, endpoint, method, error_type, status_code}`
- `active_requests{service_name, endpoint}`

### AI 专项指标

- `ai_requests_total{model, provider, environment, tracking_id}`
- `ai_tokens_total{model, token_type, environment, tracking_id}`
- `ai_cost_total{model, environment, tracking_id}`

### 业务指标

- `api_key_usage_total{api_key_id, client_name, service_name, endpoint, success}`
- `endpoint_usage_total{service_name, endpoint, api_version, user_segment}`
- `user_activity_total{user_id, activity_type, service_name, session_id}`
- `workflow_success_rate{workflow_type, complexity_level}`

## 验收标准

### ✅ 完成检查项

1. [ ] Jaeger UI 显示服务间调用链
2. [ ] Prometheus 收集到应用指标
3. [ ] Grafana Cloud 显示 dev/prod 分离数据
4. [ ] 日志包含 trace_id 关联
5. [ ] 告警规则正常触发
6. [ ] 成本控制在预算内
7. [ ] **每个 API 请求都有 tracking_id (直接使用完整的 OpenTelemetry trace ID)**
8. [ ] **OpenTelemetry 自动传播 traceparent header (零手动配置)**
9. [ ] **响应头包含完整的 X-Tracking-ID 便于客户端追踪**
10. [ ] **数据库记录关联完整的 tracking_id 字段 (32位格式)**
11. [ ] **所有日志使用 JSON 结构化格式 (完全适配 AWS CloudWatch)**
12. [ ] **所有日志包含统一的 tracking_id (与 OpenTelemetry trace_id 完全一致)**
13. [ ] **ERROR 级别日志自动创建 OpenTelemetry Span Events**
14. [ ] **基础指标自动包含 OpenTelemetry 标签维度**
15. [ ] **业务指标收集 (通过 span 属性自动关联)**
16. [ ] **CloudWatch 字段优化 (@timestamp, @level, @message 字段)**
17. [ ] **tracing 对象包含 trace_id 和 span_id (无重复字段)**
18. [ ] **字段数量限制 (小于 1000 字段避免截断)**
19. [ ] **OpenTelemetry 自动装配验证 (FastAPI + requests)**

### 🎯 关键成功指标

- 系统可用性 &gt;99.9%
- 指标收集延迟 &lt;30 秒
- 追踪覆盖率 &gt;95%
- 成本优化潜力可见

---

## 🚀 详细实施清单

### 📋 Claude 负责完成的本地代码/配置更改

#### ✅ 监控配置文件创建
- [x] `monitoring/otel-collector-config.yml` - OpenTelemetry Collector 混合配置
- [x] `monitoring/docker-compose.monitoring.yml` - 简化监控栈
- [x] `monitoring/.env.monitoring` - Grafana Cloud 环境变量模板
- [x] `monitoring/prometheus.yml` - 本地 Prometheus 配置

#### ✅ Python 遥测 SDK 开发
- [x] `apps/backend/shared/telemetry/__init__.py` - 包初始化
- [x] `apps/backend/shared/telemetry/complete_stack.py` - 统一监控 SDK
- [x] `apps/backend/shared/telemetry/middleware.py` - FastAPI 追踪中间件
- [x] `apps/backend/shared/telemetry/metrics.py` - 核心指标定义
- [x] `apps/backend/shared/telemetry/formatter.py` - CloudWatch 日志格式化器

#### ✅ 服务集成更新
- [x] `apps/backend/api-gateway/main.py` - 添加遥测初始化
- [x] `apps/backend/workflow_agent/main.py` - 添加遥测初始化
- [x] `apps/backend/workflow_engine/main.py` - 添加遥测初始化

#### ✅ 依赖包更新
- [x] `apps/backend/api-gateway/pyproject.toml` - 添加 OpenTelemetry 包
- [x] `apps/backend/workflow_agent/pyproject.toml` - 添加 OpenTelemetry 包
- [x] `apps/backend/workflow_engine/requirements.txt` - 添加 OpenTelemetry 包

#### ✅ 基础设施代码
- [x] `infra/monitoring.tf` - Terraform Grafana Cloud 集成
- [x] 更新 `infra/ecs.tf` - ECS 任务环境变量配置
- [x] 更新 `infra/variables.tf` - 添加 Grafana Cloud 变量

#### ✅ 现有日志系统更新
- [x] 检查并更新现有日志配置以符合 CloudWatch 结构化要求
- [x] 确保所有服务使用统一的日志格式 (通过 telemetry 系统)

### 🌐 您需要完成的云端配置

#### ☁️ Grafana Cloud 设置
- [ ] 注册 Grafana Cloud 免费账号 (grafana.com)
- [ ] 获取 API Key 和 Tenant ID
- [ ] 获取 Prometheus Push URL (格式: https://prometheus-prod-xx-xx-x.grafana.net/api/prom/push)
- [ ] 获取 Loki Push URL (格式: https://logs-prod-xxx.grafana.net/loki/api/v1/push)
- [ ] 在 Grafana Cloud 中配置告警规则

#### 🔐 AWS Parameter Store 配置
- [ ] 在 AWS Systems Manager Parameter Store 中存储:
  - `/ai-teams/dev/monitoring/grafana-cloud-api-key` (SecureString)
  - `/ai-teams/prod/monitoring/grafana-cloud-api-key` (SecureString)
  - `/ai-teams/dev/monitoring/grafana-cloud-config` (String - JSON 格式)
  - `/ai-teams/prod/monitoring/grafana-cloud-config` (String - JSON 格式)

#### 🚀 基础设施部署
- [ ] 运行 `terraform plan` 检查监控基础设施更改
- [ ] 运行 `terraform apply` 部署监控配置到 AWS
- [ ] 重启 ECS 服务以应用新的环境变量

### 🔍 验证和测试

#### 🏠 本地验证
- [ ] 启动本地监控栈: `docker-compose -f monitoring/docker-compose.monitoring.yml up -d`
- [ ] 验证 Jaeger UI 可访问: http://localhost:16686
- [ ] 验证 Prometheus UI 可访问: http://localhost:9090
- [ ] 测试 API 请求是否生成追踪数据
- [ ] 检查日志是否包含 tracking_id

#### ☁️ 云端验证
- [ ] 验证 Grafana Cloud 仪表板显示指标数据
- [ ] 确认 Loki 收到结构化日志
- [ ] 测试告警规则是否正常触发
- [ ] 验证 dev/prod 环境标签正确分离

#### 🆔 Trace ID 流转验证
- [ ] 确认每个 API 请求都有 X-Tracking-ID 响应头
- [ ] 验证服务间调用自动传播 traceparent header
- [ ] 检查数据库记录包含完整的 tracking_id
- [ ] 确认日志和 traces 通过 tracking_id 正确关联

### 📊 性能和成本监控
- [ ] 监控 Grafana Cloud 使用量 (指标数量、日志容量)
- [ ] 确认成本在免费层限制内
- [ ] 设置使用量告警避免超出免费额度

---

**实施负责人**: Claude (本地代码) + 您 (云端配置)
**预计完成时间**: 1 个工作日
**依赖项**: Grafana Cloud 账号, AWS 权限
