# OpenTelemetry 部署指南

## 🚀 部署确认清单

### ✅ 已完成的配置修改

#### 1. **GitHub Actions 部署配置** (`.github/workflows/deploy.yml`)
- ✅ 添加了 OTEL Collector 服务更新步骤
- ✅ 在等待部署完成时包含 OTEL Collector 服务

#### 2. **OTEL Collector 配置** (`infra/otel_collector.tf`)
- ✅ 增加内存和 CPU (512 CPU units, 1024 MB 内存)
- ✅ 配置 AWS X-Ray 追踪导出
- ✅ 配置 AWS CloudWatch 指标导出 (EMF)
- ✅ 添加 Grafana Cloud 集成（可选）
- ✅ 添加资源处理器自动添加环境标签
- ✅ 优化批处理和内存限制设置
- ✅ 添加健康检查和 pprof 扩展

#### 3. **ECS 服务配置** (`infra/ecs.tf`)
- ✅ 所有服务配置 OTEL 环境变量
  - `OTEL_SDK_DISABLED=false`
  - `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector.{namespace}:4317`
  - `OTEL_TRACES_EXPORTER=otlp`
  - `OTEL_METRICS_EXPORTER=otlp`
  - `OTEL_LOGS_EXPORTER=otlp`
- ✅ 修改日志格式为 JSON (`LOG_FORMAT=json`)
- ✅ 设置日志级别为 DEBUG (`LOG_LEVEL=DEBUG`)
- ✅ 添加 `PYTHONUNBUFFERED=1` 确保日志即时输出

## 📊 数据流向

```
应用服务 (ECS Tasks)
    ↓ OTLP (gRPC:4317)
OTEL Collector
    ↓
┌──────────────┬────────────────┬─────────────────┐
│   AWS X-Ray  │ CloudWatch EMF │  Grafana Cloud  │
│   (Traces)   │   (Metrics)    │ (Traces/Metrics)│
└──────────────┴────────────────┴─────────────────┘
```

## 🔍 在 AWS 上查看数据

### 1. **AWS X-Ray** - 查看追踪数据
```bash
# 打开 AWS Console → X-Ray → Traces
# 或使用 CLI
aws xray get-trace-summaries \
  --time-range-type LastHour \
  --region us-east-1
```

### 2. **CloudWatch Metrics** - 查看指标
```bash
# 打开 AWS Console → CloudWatch → Metrics → AgentTeam/production
# 或使用 CLI
aws cloudwatch list-metrics \
  --namespace "AgentTeam/production" \
  --region us-east-1
```

### 3. **CloudWatch Logs** - 查看日志
```bash
# 查看 OTEL Collector 日志
aws logs tail /ecs/agent-prod/otel-collector --follow

# 查看应用日志（现在是 JSON 格式）
aws logs tail /ecs/agent-prod --follow | jq '.'
```

## 🚦 部署步骤

### 1. **推送代码触发自动部署**
```bash
git add .
git commit -m "Configure OTEL with AWS X-Ray and CloudWatch"
git push origin main
```

### 2. **手动部署（如需要）**
```bash
cd infra/
terraform plan
terraform apply -auto-approve
```

### 3. **验证部署**
```bash
# 检查 OTEL Collector 服务状态
aws ecs describe-services \
  --cluster agent-prod-cluster \
  --services agent-prod-otel-collector \
  --query 'services[0].runningCount'

# 确认服务发现注册
aws servicediscovery list-instances \
  --service-id $(aws servicediscovery list-services \
    --query "Services[?Name=='otel-collector'].Id" \
    --output text)
```

## 🐛 故障排查

### 问题 1: 日志中看不到 extra 字段
**解决方案**: 已配置 `LOG_FORMAT=json`，日志将以 JSON 格式输出，包含所有字段。

### 问题 2: 没有看到追踪数据
**检查步骤**:
1. 确认 OTEL Collector 正在运行
2. 检查应用是否正确连接到 Collector
3. 查看 Collector 日志是否有错误

### 问题 3: CloudWatch 中没有指标
**检查步骤**:
1. 确认 namespace 正确: `AgentTeam/production`
2. 检查 IAM 权限是否包含 `cloudwatch:PutMetricData`
3. 查看 OTEL Collector 日志

## 🔐 需要的 GitHub Secrets

确保在 GitHub 仓库设置中配置了以下 Secrets：

- `AWS_ACCESS_KEY` - AWS 访问密钥
- `AWS_SECRET_KEY` - AWS 密钥
- `GRAFANA_CLOUD_API_KEY` - Grafana Cloud API 密钥（可选）
- `GRAFANA_CLOUD_TENANT_ID` - Grafana Cloud 租户 ID（可选）

## 📈 监控建议

1. **设置 CloudWatch 告警**：
   - OTEL Collector 内存使用率 > 80%
   - 追踪错误率 > 1%
   - 服务不健康

2. **创建 CloudWatch Dashboard**：
   - 服务请求率
   - 错误率
   - 延迟 P50/P95/P99
   - 追踪采样率

3. **定期检查**：
   - OTEL Collector 资源使用情况
   - 数据导出成功率
   - 成本监控

## ✅ 部署确认

**所有配置已完成，推送代码后将自动：**
1. 构建并推送 Docker 镜像到 ECR
2. 通过 Terraform 更新基础设施
3. 部署 OTEL Collector 服务
4. 更新所有 ECS 服务
5. 开始收集和导出遥测数据到 AWS X-Ray 和 CloudWatch

**数据将出现在：**
- AWS X-Ray: 分布式追踪
- CloudWatch Metrics: 应用指标
- CloudWatch Logs: 结构化日志（JSON 格式）
- Grafana Cloud: 如果配置了 API 密钥