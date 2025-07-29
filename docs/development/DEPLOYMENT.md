# Deployment Guide

This guide covers deploying the Agent Team services (API Gateway, Workflow Agent, and Workflow Engine) to AWS ECS using Terraform and GitHub Actions.

## Architecture Overview

- **API Gateway**: FastAPI service running on ECS Fargate (HTTP/REST API)
- **Workflow Agent**: LangGraph-based AI workflow consultant running on ECS Fargate (gRPC service)
- **Workflow Engine**: Workflow execution engine running on ECS Fargate (gRPC service)
- **Database**: RDS PostgreSQL
- **Cache**: ElastiCache Redis
- **Load Balancer**: Application Load Balancer
- **Service Discovery**: AWS Cloud Map
- **Container Registry**: Amazon ECR
- **Secrets Management**: AWS Systems Manager Parameter Store

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** configured with credentials
3. **Terraform** >= 1.0
4. **Docker** for local building
5. **GitHub repository** with Actions enabled

## Monorepo Build Strategy

All backend services use a unified build context (`apps/backend`) for consistent dependency management:

- **Build Context**: `apps/backend` (contains workspace-level `pyproject.toml` and `uv.lock`)
- **Dockerfiles**: Each service has its own Dockerfile but shares the backend build context
- **Shared Resources**: Proto definitions and prompts in `apps/backend/shared/`
- **CI/CD Pipeline**: Tests and builds all three services in parallel

### Service Build Contexts

```yaml
# GitHub Actions Matrix Strategy
services:
  - name: api-gateway
    context: apps/backend
    dockerfile: apps/backend/api-gateway/Dockerfile
  - name: workflow-agent  
    context: apps/backend
    dockerfile: apps/backend/workflow_agent/Dockerfile
  - name: workflow-engine
    context: apps/backend
    dockerfile: apps/backend/workflow_engine/Dockerfile
```

## Setup Instructions

### 1. Configure AWS Credentials

```bash
aws configure
# or use environment variables
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_DEFAULT_REGION=us-east-1
```

### 2. Create S3 Backend for Terraform State

```bash
# Create S3 bucket for Terraform state
aws s3 mb s3://agent-team-terraform-state --region us-east-1

# Create DynamoDB table for state locking
aws dynamodb create-table \
    --table-name agent-team-terraform-locks \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
    --region us-east-1
```

### 3. Configure Environment Variables

Create `infra/terraform.tfvars` from the example:

```bash
cp infra/terraform.tfvars.example infra/terraform.tfvars
```

Edit the file with your values:

```hcl
# AWS Configuration
aws_region = "us-east-1"
environment = "production"
project_name = "agent-team"

# Sensitive variables (set via environment or GitHub Secrets)
supabase_url = "https://your-project.supabase.co"
supabase_anon_key = "your-anon-key"
supabase_service_role_key = "your-service-role-key"
openai_api_key = "your-openai-api-key"
anthropic_api_key = "your-anthropic-api-key"
```

### 4. Set GitHub Secrets

In your GitHub repository, add these secrets:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SECRET_KEY`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`

## Deployment Methods

### Method 1: GitHub Actions (Recommended)

1. Push changes to the `main` branch
2. GitHub Actions will automatically:
   - Run tests for all three services (api-gateway, workflow-agent, workflow-engine)
   - Build Docker images using unified build context
   - Push to ECR repositories:
     - `agent-team/api-gateway`
     - `agent-team/workflow-agent`
     - `agent-team/workflow-engine`
   - Deploy infrastructure via Terraform
   - Update all ECS services

### Method 2: Manual Deployment

Use the deployment script:

```bash
# Full deployment
./scripts/deploy.sh

# Or step by step
./scripts/deploy.sh check     # Check requirements
./scripts/deploy.sh build     # Build and push images
./scripts/deploy.sh infra     # Deploy infrastructure
./scripts/deploy.sh services  # Update services
./scripts/deploy.sh status    # Check status
```

### Method 3: Terraform Only

```bash
cd infra

# Initialize
terraform init

# Plan
terraform plan

# Apply
terraform apply
```

## Environment Configuration

### API Gateway Environment Variables

Set in `apps/backend/api-gateway/.env`:

```env
DEBUG=false
WORKFLOW_SERVICE_HOST=workflow-agent.agent-team-production.local
WORKFLOW_SERVICE_PORT=50051
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SECRET_KEY=your-service-role-key
```

### Workflow Agent Environment Variables

Set in `apps/backend/workflow_agent/.env`:

```env
DEBUG=false
GRPC_HOST=0.0.0.0
GRPC_PORT=50051
DATABASE_URL=postgresql://workflow_user:workflow_password@postgres:5432/workflow_agent
REDIS_URL=redis://redis:6379/0
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
DEFAULT_MODEL_PROVIDER=openai
DEFAULT_MODEL_NAME=gpt-4
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SECRET_KEY=your-service-role-key
```

### Workflow Engine Environment Variables

Set in `apps/backend/workflow_engine/.env`:

```env
DEBUG=false
GRPC_HOST=0.0.0.0
GRPC_PORT=8000
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
```

## Monitoring and Troubleshooting

### Check Service Status

```bash
# Get deployment status
./scripts/deploy.sh status

# Check ECS services
aws ecs describe-services \
    --cluster agent-team-production-cluster \
    --services api-gateway-service workflow-agent-service workflow-engine-service

# Check service logs
aws logs tail /ecs/agent-team-production --follow
```

### Common Issues

1. **Service won't start**: Check CloudWatch logs for errors
2. **Health check failures**: Verify health endpoints are responding
3. **Database connection issues**: Check security groups and RDS status
4. **Image pull errors**: Verify ECR permissions and image tags

### Scaling

```bash
# Scale services
aws ecs update-service \
    --cluster agent-team-production-cluster \
    --service api-gateway-service \
    --desired-count 4
```

## Security Considerations

1. **Secrets**: All sensitive data is stored in AWS Systems Manager Parameter Store
2. **Network**: Services run in private subnets with NAT gateway for outbound access
3. **Database**: RDS is in private subnets with encryption at rest
4. **Load Balancer**: HTTPS termination with optional custom domain
5. **Container Security**: Non-root user, minimal base images

## Cost Optimization

1. **Right-sizing**: Adjust CPU/memory based on actual usage
2. **Auto Scaling**: Configure ECS auto scaling based on metrics
3. **Reserved Instances**: Use RDS reserved instances for production
4. **Spot Instances**: Consider Fargate Spot for non-critical workloads

## Service Architecture Details

### Service Communication Flow

```
Internet → ALB → API Gateway (HTTP/8000) 
                     ↓ gRPC
           Workflow Agent (gRPC/50051)
                     ↓ gRPC  
           Workflow Engine (gRPC/8000)
```

### Container Specifications

| Service | Port | Protocol | CPU | Memory | Health Check |
|---------|------|----------|-----|--------|--------------|
| API Gateway | 8000 | HTTP | 512 | 1024MB | `/health` |
| Workflow Agent | 50051 | gRPC | 1024 | 2048MB | gRPC health check |
| Workflow Engine | 8000 | gRPC | 512 | 1024MB | `/health` |

## Rollback Procedure

```bash
# Rollback individual services to previous task definition
aws ecs update-service \
    --cluster agent-team-production-cluster \
    --service api-gateway-service \
    --task-definition agent-team-production-api-gateway:PREVIOUS_REVISION

aws ecs update-service \
    --cluster agent-team-production-cluster \
    --service workflow-agent-service \
    --task-definition agent-team-production-workflow-agent:PREVIOUS_REVISION

aws ecs update-service \
    --cluster agent-team-production-cluster \
    --service workflow-engine-service \
    --task-definition agent-team-production-workflow-engine:PREVIOUS_REVISION

# Or use Terraform to rollback infrastructure
terraform plan -target=aws_ecs_service.api_gateway
terraform apply -target=aws_ecs_service.api_gateway
```

## Custom Domain Setup (Optional)

1. **Request ACM Certificate**:

   ```bash
   aws acm request-certificate \
       --domain-name api.yourdomain.com \
       --validation-method DNS
   ```

2. **Update Terraform variables**:

   ```hcl
   domain_name = "api.yourdomain.com"
   certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/..."
   ```

3. **Create DNS record** pointing to the API Gateway domain

## Support

For issues and questions:

1. Check CloudWatch logs
2. Review GitHub Actions logs
3. Verify AWS resource status
4. Check security group rules
5. Validate environment variables
