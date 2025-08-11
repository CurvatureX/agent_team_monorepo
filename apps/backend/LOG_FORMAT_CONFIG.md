# Log Format Configuration

## Current Configuration

Both **local (Docker Compose)** and **AWS (Terraform/ECS)** environments are now configured to use:

- `LOG_FORMAT=simple` - CloudWatch-compatible text format
- `LOG_LEVEL=INFO` - Standard info level logging

## Local Configuration (Docker Compose)

Updated in `docker-compose.yml` for all services:

### API Gateway
```yaml
environment:
  - LOG_LEVEL=INFO
  - LOG_FORMAT=simple
```

### Workflow Agent
```yaml
environment:
  LOG_LEVEL: "INFO"
  LOG_FORMAT: "simple"
```

### Workflow Engine
```yaml
environment:
  LOG_LEVEL: "INFO"
  LOG_FORMAT: "simple"
```

### Workflow Scheduler
```yaml
environment:
  LOG_LEVEL: "INFO"
  LOG_FORMAT: "simple"
```

## AWS Configuration (Terraform)

Updated in `infra/ecs.tf` for all ECS task definitions:

### All Services (API Gateway, Workflow Agent, Workflow Engine, Workflow Scheduler)
```hcl
environment = [
  # ... other env vars ...
  {
    name  = "LOG_LEVEL"
    value = "INFO"
  },
  {
    name  = "LOG_FORMAT"
    value = "simple"
  }
]
```

## Log Output Format

With `LOG_FORMAT=simple`, logs will appear in CloudWatch as:

```
INFO:     2025-08-11 14:03:25 - api-gateway - Starting service
INFO:     2025-08-11 14:03:25 - workflow-agent - Processing request
ERROR:    2025-08-11 14:03:26 - workflow-engine - Database connection failed
```

This format:
- ✅ Is recognized by CloudWatch for log level filtering
- ✅ Shows timestamps in human-readable format
- ✅ Identifies the service name clearly
- ✅ Matches Uvicorn's default format style

## Benefits

1. **CloudWatch Recognition**: Log levels (INFO, WARNING, ERROR) are automatically parsed
2. **Consistency**: Same format in local development and production
3. **Readability**: Clean, simple format that's easy to read in CloudWatch console
4. **Filtering**: Can filter by log level in CloudWatch
5. **No Emojis**: Removed emojis that don't render well in CloudWatch

## Deployment Steps

### Local Testing
```bash
# Rebuild and start services
docker-compose down
docker-compose up --build
```

### AWS Deployment
```bash
# Apply Terraform changes
cd infra
terraform plan
terraform apply

# Force new deployment to pick up env changes
aws ecs update-service --cluster agent-team-cluster \
  --service api-gateway-service --force-new-deployment
aws ecs update-service --cluster agent-team-cluster \
  --service workflow-agent-service --force-new-deployment
aws ecs update-service --cluster agent-team-cluster \
  --service workflow-engine-service --force-new-deployment
```

## Verification

After deployment, check CloudWatch Logs:
1. Go to AWS Console → CloudWatch → Log Groups
2. Select `/ecs/agent-team`
3. View log streams for each service
4. Verify logs show in format: `INFO:     timestamp - service - message`

## Default Configuration

- **LOG_FORMAT**: `simple` (default in code)
- **LOG_LEVEL**: `INFO` (default for production)

This configuration is optimized for:
- Easy reading in ECS console
- CloudWatch log level recognition
- Quick troubleshooting in production