# Observability Configuration Guide

## 当前状态

### 本地开发环境 ✅
已经配置完成，可以通过以下方式启动：

```bash
# 启动带有 observability stack 的服务
./start-with-observability.sh

# 或者手动启动
docker-compose --profile observability up -d
```

**访问地址：**
- Jaeger UI: http://localhost:16686 - 查看分布式追踪
- Prometheus: http://localhost:8889/metrics - 查看指标
- OTEL Collector: localhost:4317 (gRPC) / localhost:4318 (HTTP)

### 线上环境 ⚠️
部分配置完成，但还需要添加 OTEL Collector：

**已完成：**
- ✅ ECS 任务定义中已配置 OTEL 环境变量
- ✅ CloudWatch 日志配置支持结构化日志
- ✅ SSM 参数存储了 OTEL 配置
- ✅ 代码中已集成 OpenTelemetry SDK

**待完成：**
- ❌ 需要在 ECS 任务中添加 OTEL Collector sidecar 容器
- ❌ 需要配置 OTEL Collector 将数据发送到 CloudWatch 或 Grafana Cloud

## 线上环境配置建议

### 方案 1：使用 AWS Distro for OpenTelemetry (推荐)

在 ECS 任务定义中添加 ADOT Collector sidecar：

```hcl
# 在 ecs.tf 中的每个任务定义中添加 sidecar 容器
container_definitions = jsonencode([
  {
    # 主应用容器配置...
  },
  {
    name  = "aws-otel-collector"
    image = "public.ecr.aws/aws-observability/aws-otel-collector:latest"
    
    command = ["--config=/etc/ecs/otel-config.yaml"]
    
    environment = [
      {
        name  = "AWS_REGION"
        value = var.aws_region
      }
    ]
    
    portMappings = [
      {
        containerPort = 4317
        protocol      = "tcp"
      },
      {
        containerPort = 4318
        protocol      = "tcp"
      }
    ]
    
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.ecs.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "otel-collector"
      }
    }
    
    # OTEL Collector 配置文件
    mountPoints = [
      {
        sourceVolume  = "otel-config"
        containerPath = "/etc/ecs"
        readOnly      = true
      }
    ]
  }
])

# 添加配置文件卷
volumes = [
  {
    name = "otel-config"
    configurationOptions = {
      s3Configuration = {
        bucketArn = aws_s3_bucket.otel_config.arn
        rootDirectory = "/"
      }
    }
  }
]
```

### 方案 2：使用 CloudWatch Container Insights

更简单的方案，直接将追踪数据发送到 CloudWatch X-Ray：

```hcl
# 在环境变量中配置
environment = [
  {
    name  = "OTEL_EXPORTER_OTLP_ENDPOINT"
    value = "http://localhost:4317"
  },
  {
    name  = "OTEL_TRACES_EXPORTER"
    value = "xray"
  },
  {
    name  = "AWS_XRAY_DAEMON_ADDRESS"
    value = "localhost:2000"
  }
]
```

## OTEL Collector 配置示例

创建 `otel-config-production.yaml`：

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 1s
    send_batch_size: 1024
  
  resource:
    attributes:
      - key: environment
        value: production
        action: upsert
      - key: project
        value: starmates-ai-team
        action: upsert

exporters:
  # 发送到 CloudWatch
  awsxray:
    region: us-east-1
    
  # 发送到 CloudWatch Metrics
  awsemf:
    region: us-east-1
    namespace: "StarMates/AITeam"
    
  # 发送到 CloudWatch Logs
  awscloudwatchlogs:
    region: us-east-1
    log_group_name: /ecs/starmates-ai-team
    log_stream_name: otel-traces

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch, resource]
      exporters: [awsxray]
    
    metrics:
      receivers: [otlp]
      processors: [batch, resource]
      exporters: [awsemf]
    
    logs:
      receivers: [otlp]
      processors: [batch, resource]
      exporters: [awscloudwatchlogs]
```

## 验证步骤

### 本地环境
1. 启动服务：`./start-with-observability.sh`
2. 发送测试请求：`curl http://localhost:8000/api/v1/public/health`
3. 打开 Jaeger UI：http://localhost:16686
4. 选择服务（api-gateway）并查看追踪

### 线上环境（配置完成后）
1. 查看 CloudWatch X-Ray 控制台
2. 检查 CloudWatch Logs 中的结构化日志
3. 查看 CloudWatch Metrics 中的自定义指标

## 故障排除

### 常见问题

1. **"Transient error StatusCode.UNAVAILABLE" 错误**
   - 原因：OTEL Collector 未运行或无法访问
   - 解决：启动 OTEL Collector 或禁用 OTEL SDK

2. **追踪数据未显示**
   - 检查环境变量配置
   - 验证 OTEL Collector 是否正常运行
   - 查看应用和 Collector 的日志

3. **性能影响**
   - 调整批处理大小和超时
   - 使用采样策略减少数据量
   - 监控 OTEL Collector 的资源使用

## 相关资源

- [OpenTelemetry Python Documentation](https://opentelemetry.io/docs/instrumentation/python/)
- [AWS Distro for OpenTelemetry](https://aws-otel.github.io/docs/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)