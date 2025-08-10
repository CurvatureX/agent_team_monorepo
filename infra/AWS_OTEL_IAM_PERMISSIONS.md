# AWS OpenTelemetry IAM Permissions

This document outlines the required IAM permissions for OpenTelemetry integration with AWS X-Ray, CloudWatch, and other AWS services.

## Required IAM Roles

### 1. ECS Task Role (AgentTeamTaskRole)

**Purpose**: Allows ECS tasks to access AWS services for telemetry data export.

**Trust Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Permissions Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutMetricData"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "cloudwatch:namespace": "AgentTeam"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogStreams"
      ],
      "Resource": [
        "arn:aws:logs:*:*:log-group:/agent-team/*",
        "arn:aws:logs:*:*:log-group:/ecs/agent-team-*"
      ]
    }
  ]
}
```

### 2. ECS Task Execution Role (ecsTaskExecutionRole)

**Purpose**: Allows ECS to pull images and access secrets.

**AWS Managed Policies**:
- `arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy`

**Additional Custom Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:*:*:secret:agent-team/*"
      ]
    }
  ]
}
```

## AWS Services and Required Permissions

### AWS X-Ray
**Service**: Distributed tracing
**Required Permissions**:
- `xray:PutTraceSegments` - Send trace data
- `xray:PutTelemetryRecords` - Send telemetry metadata

**Resource**: `*` (X-Ray requires wildcard resource)

### CloudWatch Metrics
**Service**: Custom metrics collection
**Required Permissions**:
- `cloudwatch:PutMetricData` - Send custom metrics

**Resource**: Limited to `AgentTeam` namespace for security

### CloudWatch Logs
**Service**: Log aggregation
**Required Permissions**:
- `logs:CreateLogGroup` - Create log groups
- `logs:CreateLogStream` - Create log streams
- `logs:PutLogEvents` - Send log events
- `logs:DescribeLogStreams` - Query log streams

**Resource**: Limited to `/agent-team/*` and `/ecs/agent-team-*` log groups

## Service-Specific Configurations

### OpenTelemetry Collector Configuration

The AWS OTEL Collector uses the following configuration:

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
  memory_limiter:
    limit_mib: 256

exporters:
  awsxray:
    region: us-east-1
  awscloudwatchmetrics:
    region: us-east-1
    namespace: AgentTeam
    dimension_rollup_option: NoDimensionRollup
  awscloudwatchlogs:
    region: us-east-1
    log_group_name: '/agent-team/otel-logs'

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [awsxray]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [awscloudwatchmetrics]
    logs:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [awscloudwatchlogs]
```

## Environment Variables

Set these environment variables in ECS task definitions:

### Development Environment
```bash
OTEL_SDK_DISABLED=true  # Disable for local development
```

### Production Environment
```bash
OTEL_SDK_DISABLED=false
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_EXPORTER_OTLP_INSECURE=true
OTEL_SERVICE_NAME=service-name
OTEL_RESOURCE_ATTRIBUTES=service.namespace=agent-team,deployment.environment=production
AWS_DEFAULT_REGION=us-east-1
ENVIRONMENT=production
```

## Monitoring and Alerts

### CloudWatch Dashboards

Create dashboards to monitor:
- **Service Performance**: Request latency, error rates, throughput
- **Resource Usage**: CPU, memory, network utilization
- **Trace Analysis**: Service dependencies, bottlenecks
- **Error Tracking**: Exception rates, error patterns

### Recommended CloudWatch Alarms

```bash
# High error rate
aws cloudwatch put-metric-alarm \
  --alarm-name "AgentTeam-HighErrorRate" \
  --alarm-description "High error rate in agent team services" \
  --metric-name "ErrorRate" \
  --namespace "AgentTeam" \
  --statistic "Average" \
  --period 300 \
  --threshold 5.0 \
  --comparison-operator "GreaterThanThreshold" \
  --evaluation-periods 2

# High latency
aws cloudwatch put-metric-alarm \
  --alarm-name "AgentTeam-HighLatency" \
  --alarm-description "High latency in agent team services" \
  --metric-name "ResponseTime" \
  --namespace "AgentTeam" \
  --statistic "Average" \
  --period 300 \
  --threshold 1000 \
  --comparison-operator "GreaterThanThreshold" \
  --evaluation-periods 2
```

## Security Best Practices

1. **Least Privilege**: Grant only necessary permissions
2. **Resource Constraints**: Limit CloudWatch namespace and log groups
3. **Condition-Based Access**: Use conditions where possible
4. **Regular Auditing**: Review IAM policies regularly
5. **Secrets Management**: Use AWS Secrets Manager for sensitive data

## Troubleshooting

### Common Issues

**Issue**: `AccessDenied` for X-Ray
**Solution**: Ensure ECS task role has `xray:PutTraceSegments` permission

**Issue**: `AccessDenied` for CloudWatch
**Solution**: Check CloudWatch namespace matches policy condition

**Issue**: OTEL Collector not starting
**Solution**: Verify container dependencies and health checks

### Debug Commands

```bash
# Check ECS task role
aws iam get-role --role-name AgentTeamTaskRole

# View X-Ray traces
aws xray get-trace-summaries --time-range-type TimeRangeByStartTime --start-time 2025-01-01T00:00:00 --end-time 2025-01-01T23:59:59

# Check CloudWatch metrics
aws cloudwatch list-metrics --namespace AgentTeam

# View logs
aws logs describe-log-groups --log-group-name-prefix /agent-team/
```

## Cost Optimization

### X-Ray Pricing
- First 100,000 traces/month: Free
- Additional traces: $5.00 per 1 million traces

### CloudWatch Pricing
- Custom metrics: $0.30 per metric per month
- API requests: $0.01 per 1,000 requests
- Logs ingestion: $0.50 per GB

### Optimization Strategies
1. **Sampling**: Configure trace sampling rates
2. **Batching**: Use batch processors to reduce API calls
3. **Filtering**: Filter out unnecessary metrics/traces
4. **Retention**: Set appropriate log retention periods

This configuration provides comprehensive observability while maintaining security and cost efficiency.
