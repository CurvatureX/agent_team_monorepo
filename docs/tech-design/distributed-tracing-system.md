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

#### A. Tracking ID 传递策略

**1. HTTP Header 标准**

- **Header 名称**: `X-Tracking-ID` (统一使用 Tracking 而非 Trace)
- **格式规范**: UUID v4 格式 (例: `f47ac10b-58cc-4372-a567-0e02b2c3d479`)
- **字符编码**: UTF-8, 长度固定 36 字符

**2. 传递规则**

```python
# 在 TracingMiddleware 中实现三级策略
def _extract_or_generate_tracking_id(self, request: Request) -> str:
    # 1. 优先从请求头提取 (继续使用现有 ID)
    tracking_id = request.headers.get("X-Tracking-ID")
    if tracking_id and self._is_valid_uuid(tracking_id):
        return tracking_id

    # 2. 从 OpenTelemetry 上下文提取
    context = propagate.extract(dict(request.headers))
    span_context = trace.get_current_span(context).get_span_context()
    if span_context.is_valid:
        return f"{span_context.trace_id:032x}"

    # 3. Gateway 生成新的 UUID v4
    return str(uuid.uuid4())

def _is_valid_uuid(self, uuid_string: str) -> bool:
    """验证 UUID v4 格式"""
    try:
        uuid_obj = uuid.UUID(uuid_string, version=4)
        return str(uuid_obj) == uuid_string
    except ValueError:
        return False
```

**3. 服务间调用要求**

- ✅ **必须携带**: 所有内部服务调用必须包含 `X-Tracking-ID` 头
- ✅ **格式验证**: 接收端验证 UUID v4 格式，无效时生成新 ID
- ✅ **响应返回**: 所有 HTTP 响应必须返回 `X-Tracking-ID` 头
- ✅ **日志记录**: 每个服务记录接收和发送的 tracking_id

#### Track ID 传播机制

- **HTTP 头部**: `X-Tracking-ID` 在所有服务间传递
- **响应头**: 返回 `X-Tracking-ID` 便于客户端追踪
- **日志关联**: 所有日志自动包含 `tracking_id` 字段
- **数据库记录**: 业务数据关联 `tracking_id` 便于问题定位

### 📊 **每个 API 的 Track ID 实现**

#### API Gateway → Workflow Agent

```python
# API Gateway 发起请求时传递 tracking_id
async def call_workflow_agent(tracking_id: str, payload: dict):
    headers = {"X-Tracking-ID": tracking_id}
    response = await httpx.post(
        f"{WORKFLOW_AGENT_URL}/generate-workflow",
        headers=headers,
        json=payload
    )
```

#### API Gateway → Workflow Engine

```python
# 执行工作流时传递 tracking_id
async def execute_workflow(tracking_id: str, workflow_data: dict):
    headers = {"X-Tracking-ID": tracking_id}
    response = await httpx.post(
        f"{WORKFLOW_ENGINE_URL}/execute",
        headers=headers,
        json=workflow_data
    )
```

#### 中间件自动处理

```python
# TracingMiddleware 自动处理所有请求
class TracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 提取或生成 tracking_id
        tracking_id = self._extract_or_generate_tracking_id(request)

        # 存储在请求状态中
        request.state.tracking_id = tracking_id

        # 处理请求
        with self.tracer.start_as_current_span(span_name) as span:
            span.set_attribute("tracking.id", tracking_id)
            response = await call_next(request)

            # 添加到响应头
            response.headers["X-Tracking-ID"] = tracking_id
            return response
```

## C. 日志关联规范

### 📝 **1. 结构化日志要求**

所有服务必须使用 **JSON 格式** 的结构化日志，**完全适配 AWS CloudWatch Logs**：

```python
# AWS CloudWatch 优化的日志格式
{
    "timestamp": "2025-01-31T10:30:45.123Z",
    "@timestamp": "2025-01-31T10:30:45.123Z",  # CloudWatch 自动解析
    "level": "INFO",
    "@level": "INFO",  # CloudWatch 日志级别字段
    "service": "api-gateway",
    "tracking_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "message": "POST /api/v1/sessions - 201",
    "@message": "POST /api/v1/sessions - 201",  # CloudWatch 消息字段
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
        "span_id": "1a2b3c4d5e6f7890",
        "trace_id": "f47ac10b58cc4372a5670e02b2c3d479"
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
- `tracking_id` - 追踪 ID 索引
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

        # CloudWatch 优化格式
        log_entry = {
            "timestamp": timestamp,
            "@timestamp": timestamp,  # CloudWatch 自动解析
            "level": record.levelname,
            "@level": record.levelname,  # CloudWatch 日志级别
            "service": self.service_name,
            "tracking_id": tracking_id,
            "message": record.getMessage(),
            "@message": record.getMessage(),  # CloudWatch 消息字段
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
  "timestamp": "2025-01-31T10:30:45.123Z",
  "@timestamp": "2025-01-31T10:30:45.123Z",
  "level": "INFO|WARN|ERROR|DEBUG",
  "@level": "INFO|WARN|ERROR|DEBUG",
  "service": "api-gateway|workflow-agent|workflow-engine",
  "tracking_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "message": "Human readable message",
  "@message": "Human readable message"
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
7. [ ] **每个 API 请求都有 tracking_id (UUID v4 格式)**
8. [ ] **服务间调用正确传递 X-Tracking-ID 头**
9. [ ] **响应头包含 X-Tracking-ID 便于客户端追踪**
10. [ ] **数据库记录关联 tracking_id 字段**
11. [ ] **所有日志使用 JSON 结构化格式 (完全适配 AWS CloudWatch)**
12. [ ] **所有日志必须包含 tracking_id 字段**
13. [ ] **ERROR 级别日志自动创建 OpenTelemetry Span Events**
14. [ ] **基础指标包含必需标签维度 (service_name, endpoint, method, status_code, api_version)**
15. [ ] **业务指标收集 (api_key_usage, endpoint_usage, user_activity)**
16. [ ] **CloudWatch 字段优化 (@timestamp, @level, @message 字段)**
17. [ ] **嵌套对象结构支持点号查询 (request.method, user.id)**
18. [ ] **字段数量限制 (小于 1000 字段避免截断)**
19. [ ] **CloudWatch Logs Insights 查询验证**

### 🎯 关键成功指标

- 系统可用性 &gt;99.9%
- 指标收集延迟 &lt;30 秒
- 追踪覆盖率 &gt;95%
- 成本优化潜力可见

---

**实施负责人**: 分配给具体开发者
**预计完成时间**: 1 个工作日
**依赖项**: Grafana Cloud 账号, AWS 权限
