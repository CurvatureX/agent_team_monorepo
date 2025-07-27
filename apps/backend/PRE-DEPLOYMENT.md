# PRE-DEPLOYMENT CHECKLIST

This checklist must be completed before any AWS ECS deployment to prevent service failures and deployment issues. Review every item carefully.

## 🏗️ Infrastructure Configuration

### Health Check Validation
- [ ] **Health check command matches service protocol**
  - [ ] HTTP services use: `curl -f http://localhost:PORT/health`
  - [ ] gRPC services use: `nc -z localhost PORT`
  - [ ] TCP services use: `nc -z localhost PORT`
- [ ] **Health check timing configured appropriately**
  - [ ] HTTP services: `startPeriod: 60s`
  - [ ] gRPC services: `startPeriod: 90-120s`
  - [ ] Database-dependent services: `startPeriod: ≥90s`
- [ ] **Test health check command locally**
  ```bash
  # Test the exact command in container
  docker run --rm your-image nc -z localhost 8000
  docker run --rm your-image curl -f http://localhost:8000/health
  ```

### Port Configuration
- [ ] **Service ports match Terraform configuration**
  - [ ] workflow-agent: 50051 (gRPC)
  - [ ] workflow-engine: 8000 (gRPC)
  - [ ] api-gateway: 8000 (HTTP)
- [ ] **Port mappings correct in task definitions**
- [ ] **Security groups allow required ports**

## 🐳 Docker & Container Configuration

### Platform Compatibility
- [ ] **Images built for correct architecture**
  ```bash
  # REQUIRED for ECS Fargate
  docker build --platform linux/amd64 -t service-name .
  ```
- [ ] **Image tags are unique and traceable**
  - [ ] Not using `:latest` for production deployments
  - [ ] Using commit SHA or semantic version tags

### Package Structure
- [ ] **Python package hierarchy preserved**
  ```dockerfile
  # Correct structure
  COPY service_name/ ./service_name/
  COPY shared/ ./shared/

  # Run as module
  CMD ["python", "-m", "service_name.main"]
  ```
- [ ] **No relative imports at module level**
- [ ] **All dependencies in requirements.txt**

## 🔧 Service-Specific Checks

### Workflow Agent (gRPC Service)
- [ ] **Dependencies available**
  - [ ] OPENAI_API_KEY configured in SSM
  - [ ] ANTHROPIC_API_KEY configured in SSM
  - [ ] SUPABASE_URL and SUPABASE_SECRET_KEY configured
  - [ ] Redis endpoint accessible
- [ ] **Health check**: `nc -z localhost 50051`
- [ ] **Start period**: 120s minimum
- [ ] **gRPC server binds to `[::]`**

### Workflow Engine (gRPC Service)
- [ ] **Dependencies available**
  - [ ] Database connection string valid
  - [ ] Redis endpoint accessible
  - [ ] OPENAI_API_KEY and ANTHROPIC_API_KEY configured
- [ ] **Health check**: `nc -z localhost 8000`
- [ ] **Start period**: 90s minimum
- [ ] **Database initialization handled gracefully**

### API Gateway (HTTP Service)
- [ ] **Health endpoint implemented**: `/health`
- [ ] **Load balancer target group configured**
- [ ] **Health check**: `curl -f http://localhost:8000/health`
- [ ] **Start period**: 60s sufficient

## 🌐 Environment & Secrets

### SSM Parameters
- [ ] **All secrets exist in AWS SSM**
  - [ ] `/agent-team-production/openai/api-key`
  - [ ] `/agent-team-production/anthropic/api-key`
  - [ ] `/agent-team-production/supabase/url`
  - [ ] `/agent-team-production/supabase/secret-key`
- [ ] **No placeholder values** (e.g., "placeholder", "your-key-here")
- [ ] **Values are valid and current**

### Environment Variables
- [ ] **Service configuration correct**
  - [ ] GRPC_HOST="[::]" for gRPC services
  - [ ] DEBUG="false" for production
  - [ ] Proper Redis and database URLs
- [ ] **No hardcoded credentials in code**

## 🧪 Testing & Validation

### Local Testing
- [ ] **Services start locally with production-like config**
- [ ] **Health checks pass locally**
  ```bash
  # Test exact health check commands
  nc -z localhost 50051  # workflow-agent
  nc -z localhost 8000   # workflow-engine
  curl -f http://localhost:8000/health  # api-gateway
  ```
- [ ] **Inter-service communication works**
- [ ] **External dependencies accessible**

### Container Testing
- [ ] **Images run on target platform (linux/amd64)**
- [ ] **No missing dependencies in container**
- [ ] **Proper logging output visible**
- [ ] **Service binds to correct ports**

## 📋 Deployment Process

### Pre-Deployment
- [ ] **ECR repositories exist**
- [ ] **Images pushed to ECR with unique tags**
- [ ] **Task definitions updated with new image URIs**
- [ ] **ECS cluster has sufficient capacity**

### Terraform Configuration
- [ ] **`terraform plan` reviewed and approved**
- [ ] **Health check configurations validated**
- [ ] **Resource limits appropriate**
  - [ ] CPU: 512 units minimum for gRPC services
  - [ ] Memory: 1024 MB minimum
- [ ] **Network configuration correct**
  - [ ] Private subnets for services
  - [ ] Security groups allow required traffic

### Deployment Monitoring
- [ ] **CloudWatch logs configured**
- [ ] **Monitoring dashboard ready**
- [ ] **Alert thresholds configured**
- [ ] **Rollback plan prepared**

## 🚨 Common Pitfalls to Avoid

### ❌ NEVER DO
- Use HTTP health checks on gRPC services
- Use `:latest` tags for production
- Hardcode secrets in environment variables
- Build images without platform specification
- Deploy without testing health checks locally
- Use placeholder values in configuration
- Flatten Python package structure in Docker

### ✅ ALWAYS DO
- Test health check commands in containers
- Use TCP connection tests for gRPC services
- Set appropriate grace periods for services
- Validate all environment variables and secrets
- Build with `--platform linux/amd64`
- Use semantic versioning for images
- Monitor deployment progress and logs

## 📝 Deployment Commands

```bash
# Build and tag images
docker build --platform linux/amd64 -t workflow-agent:$(git rev-parse HEAD) .
docker tag workflow-agent:$(git rev-parse HEAD) 982081090398.dkr.ecr.us-east-1.amazonaws.com/agent-team/workflow-agent:$(git rev-parse HEAD)

# Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 982081090398.dkr.ecr.us-east-1.amazonaws.com
docker push 982081090398.dkr.ecr.us-east-1.amazonaws.com/agent-team/workflow-agent:$(git rev-parse HEAD)

# Deploy with Terraform
terraform plan -var="image_tag=$(git rev-parse HEAD)"
terraform apply -var="image_tag=$(git rev-parse HEAD)"

# Monitor deployment
aws ecs wait services-stable --cluster agent-team-production-cluster --services api-gateway-service workflow-engine-service workflow-agent-service --region us-east-1
```

## 🔍 Post-Deployment Verification

- [ ] **All services show RUNNING status**
- [ ] **Health checks passing**
- [ ] **No error logs in CloudWatch**
- [ ] **Service endpoints responding**
- [ ] **Load balancer targets healthy**
- [ ] **Inter-service communication working**

---

**Remember**: Every deployment failure costs time and potentially affects users. Take the extra 10 minutes to validate everything rather than debugging failed deployments for hours.

**Last Updated**: January 2025 after health check protocol mismatch incident.
