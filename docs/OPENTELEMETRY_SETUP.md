# OpenTelemetry Setup for AWS ECS

This document describes how to set up and use OpenTelemetry for distributed tracing, metrics, and logging in the AWS ECS environment.

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   API Gateway   │────▶│ Workflow Agent   │────▶│ Workflow Engine  │
│   (Port 8000)   │     │   (Port 8001)    │     │   (Port 8002)    │
└─────────────────┘     └──────────────────┘     └──────────────────┘
        │                        │                         │
        └────────────────────────┼─────────────────────────┘
                                 ▼
                    ┌──────────────────────┐
                    │  OTEL Collector      │
                    │  (Port 4317/4318)    │
                    └──────────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
              CloudWatch    CloudWatch    CloudWatch
                X-Ray        Metrics        Logs
```

## Components

### 1. OpenTelemetry Collector
- **Service**: Runs as a separate ECS service in the cluster
- **Image**: AWS Distro for OpenTelemetry (`public.ecr.aws/aws-observability/aws-otel-collector:latest`)
- **Ports**: 
  - 4317: gRPC for OTLP
  - 4318: HTTP for OTLP
  - 8889: Prometheus metrics endpoint
- **Configuration**: Defined in Terraform (`infra/otel_collector.tf`)
- **Note**: Uses `debug` exporter instead of deprecated `logging` exporter

### 2. Service Configuration
Each service (API Gateway, Workflow Agent, Workflow Engine) is configured with:
- OpenTelemetry SDK for automatic instrumentation
- OTLP exporter pointing to the collector
- Tracking ID generation for request correlation

### 3. Data Exporters
The collector exports data to:
- **AWS X-Ray**: Distributed traces
- **CloudWatch Metrics**: Performance metrics
- **CloudWatch Logs**: Structured logs

## Deployment

### Initial Setup

1. **Deploy the OTEL Collector**:
```bash
cd scripts
./deploy_otel_collector.sh
```

2. **Verify Collector is Running**:
```bash
aws ecs describe-services \
  --cluster agent-team-dev-cluster \
  --services agent-team-dev-otel-collector \
  --region us-east-1 \
  --query 'services[0].runningCount'
```

3. **Check Collector Logs**:
```bash
aws logs tail /ecs/agent-team-dev/otel-collector --follow
```

### Environment Variables

The following environment variables are automatically configured in ECS:

```bash
# Enable OpenTelemetry
OTEL_SDK_DISABLED=false

# Collector endpoint (service discovery)
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector.agent-team.local:4317

# Exporters configuration
OTEL_TRACES_EXPORTER=otlp
OTEL_METRICS_EXPORTER=otlp
OTEL_LOGS_EXPORTER=otlp
```

## Monitoring

### View Traces in X-Ray

1. **AWS Console**:
   - Navigate to CloudWatch → X-Ray traces
   - Filter by service name: `api-gateway`, `workflow-agent`, `workflow-engine`

2. **AWS CLI**:
```bash
# Get recent traces
aws xray get-trace-summaries \
  --time-range-type LastHour \
  --region us-east-1

# Get specific trace details
aws xray get-trace-graph \
  --trace-id <trace-id> \
  --region us-east-1
```

### View Metrics in CloudWatch

1. **AWS Console**:
   - Navigate to CloudWatch → Metrics
   - Look for namespace: `agent-team-dev`

2. **AWS CLI**:
```bash
# List available metrics
aws cloudwatch list-metrics \
  --namespace agent-team-dev \
  --region us-east-1

# Get metric statistics
aws cloudwatch get-metric-statistics \
  --namespace agent-team-dev \
  --metric-name http_request_duration \
  --start-time 2025-01-01T00:00:00Z \
  --end-time 2025-01-01T01:00:00Z \
  --period 300 \
  --statistics Average \
  --dimensions Name=service,Value=api-gateway
```

### View Logs

Structured logs with tracking IDs are available in CloudWatch Logs:

```bash
# API Gateway logs
aws logs tail /ecs/agent-team-dev --filter-pattern "api-gateway" --follow

# Workflow Agent logs
aws logs tail /ecs/agent-team-dev --filter-pattern "workflow-agent" --follow

# Workflow Engine logs
aws logs tail /ecs/agent-team-dev --filter-pattern "workflow-engine" --follow
```

## Tracking IDs

Every request gets a unique tracking ID that flows through all services:

1. **Generation**: Created at the API Gateway entry point
2. **Propagation**: Passed via HTTP headers to downstream services
3. **Format**: 32-character hex string (OpenTelemetry trace ID format)
4. **Usage**: Available in logs as `tracking_id` field

Example log entry:
```json
{
  "timestamp": "2025-01-12T10:30:00Z",
  "level": "INFO",
  "service": "api-gateway",
  "tracking_id": "a1b2c3d4e5f6789012345678901234567",
  "message": "Request processed successfully",
  "duration_ms": 150
}
```

## Troubleshooting

### Common Issues

1. **"UNAVAILABLE" errors in logs**:
   - **Cause**: Services trying to connect to collector before it's ready
   - **Solution**: These are transient and will resolve once collector is running

2. **"No such file or directory: /bin/sh" error**:
   - **Cause**: Using generic OTEL image that lacks shell
   - **Solution**: Use AWS distro image: `public.ecr.aws/aws-observability/aws-otel-collector:latest`

3. **"logging exporter has been deprecated" error**:
   - **Cause**: Using deprecated `logging` exporter in configuration
   - **Solution**: Replace `logging` with `debug` exporter in all pipelines

4. **No traces appearing in X-Ray**:
   - **Check**: Collector is running: `aws ecs describe-services --cluster agent-team-dev-cluster --services agent-team-dev-otel-collector`
   - **Check**: Environment variables are set correctly
   - **Check**: IAM permissions for X-Ray write access

5. **High memory usage in collector**:
   - **Solution**: Adjust memory limits in `otel_collector.tf`
   - **Default**: 512MB, can increase if needed

### Debug Commands

```bash
# Check if collector service is healthy
aws ecs describe-tasks \
  --cluster agent-team-dev-cluster \
  --tasks $(aws ecs list-tasks --cluster agent-team-dev-cluster --service-name agent-team-dev-otel-collector --query 'taskArns[0]' --output text) \
  --query 'tasks[0].healthStatus'

# View collector configuration
aws ecs describe-task-definition \
  --task-definition agent-team-dev-otel-collector \
  --query 'taskDefinition.containerDefinitions[0].environment'

# Force restart collector
aws ecs update-service \
  --cluster agent-team-dev-cluster \
  --service agent-team-dev-otel-collector \
  --force-new-deployment
```

## Performance Impact

OpenTelemetry adds minimal overhead:
- **Latency**: < 1ms per request for tracing
- **Memory**: ~50MB per service for SDK
- **Network**: Batched exports every 10 seconds

## Disabling Telemetry

To temporarily disable telemetry (for debugging):

1. **Per Service**:
```bash
# Set environment variable in ECS task definition
OTEL_SDK_DISABLED=true
```

2. **Globally**:
```bash
# Stop the collector service
aws ecs update-service \
  --cluster agent-team-dev-cluster \
  --service agent-team-dev-otel-collector \
  --desired-count 0
```

## Best Practices

1. **Use Tracking IDs**: Always include tracking ID in log messages for correlation
2. **Add Custom Spans**: Use OpenTelemetry SDK to add custom spans for important operations
3. **Set Attributes**: Add relevant attributes to spans (user_id, workflow_id, etc.)
4. **Handle Errors**: Ensure errors are properly recorded in spans
5. **Monitor Collector**: Set up alarms for collector health and resource usage

## Further Reading

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [AWS X-Ray Developer Guide](https://docs.aws.amazon.com/xray/latest/devguide/)
- [CloudWatch Metrics User Guide](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/)
- [OTLP Specification](https://opentelemetry.io/docs/reference/specification/protocol/otlp/)