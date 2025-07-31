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

## 核心指标定义

### HTTP 基础指标

- `http_requests_total{method, endpoint, status_code, environment}`
- `http_request_duration_seconds{method, endpoint, environment}`
- `http_errors_total{error_type, environment}`

### AI 专项指标

- `ai_requests_total{model, provider, environment}`
- `ai_tokens_total{model, token_type, environment}`
- `ai_cost_total{model, environment}`

### 业务指标

- `user_retention_rate{retention_period, user_segment, environment}`
- `feature_adoption_rate{feature_name, environment}`
- `pmf_score{calculation_method, environment}`

## 验收标准

### ✅ 完成检查项

1. [ ] Jaeger UI 显示服务间调用链
2. [ ] Prometheus 收集到应用指标
3. [ ] Grafana Cloud 显示 dev/prod 分离数据
4. [ ] 日志包含 trace_id 关联
5. [ ] 告警规则正常触发
6. [ ] 成本控制在预算内

### 🎯 关键成功指标

- 系统可用性 >99.9%
- 指标收集延迟 <30 秒
- 追踪覆盖率 >95%
- 成本优化潜力可见

---

**实施负责人**: 分配给具体开发者
**预计完成时间**: 1 个工作日
**依赖项**: Grafana Cloud 账号, AWS 权限
