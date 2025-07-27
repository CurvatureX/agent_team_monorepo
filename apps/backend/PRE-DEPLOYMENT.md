# PRE-DEPLOYMENT CHECKLIST

This checklist must be completed before any AWS ECS deployment to prevent service failures and deployment issues. Review every item carefully.

## 🏗️ Infrastructure Configuration

### Health Check Validation
- [ ] **Health check command matches service protocol**
  - [ ] HTTP services use: `curl -f http://localhost:PORT/health`
  - [ ] gRPC services use: `nc -z localhost PORT`
  - [ ] TCP services use: `nc -z localhost PORT`
- [ ] **Health check timing configured appropriately**
  - [ ] HTTP services: `startPeriod: 120s` (increased from 60s)
  - [ ] gRPC services: `startPeriod: 180-240s` (increased for reliability)
  - [ ] Database-dependent services: `startPeriod: ≥180s`
- [ ] **Test health check command locally**
  ```bash
  # Test the exact command in container
  docker run --rm your-image nc -z localhost 8000
  docker run --rm your-image curl -f http://localhost:8000/health
  ```

### Port Configuration
- [ ] **Service ports match Terraform configuration**
  - [ ] workflow-agent: 50051 (gRPC)
  - [ ] workflow-engine: 50050 (gRPC) - **UPDATED after Jan 2025 port mismatch incident**
  - [ ] api-gateway: 8000 (HTTP)
- [ ] **Port mappings correct in task definitions**
- [ ] **Docker EXPOSE ports match ECS container ports**
- [ ] **Environment variables use correct ports (GRPC_PORT)**
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
  # CORRECT: Preserve nested package structure
  COPY workflow_engine/workflow_engine ./workflow_engine
  COPY shared/ ./shared/

  # Run as proper Python module
  CMD ["python", "-m", "workflow_engine"]
  ```
- [ ] **Test module imports work in container**
  ```bash
  # CRITICAL: Test this before deployment
  docker run --rm your-image python -c "import workflow_engine.server"
  docker run --rm your-image python -c "import workflow_agent.main"
  ```
- [ ] **No relative imports at module level**
- [ ] **All dependencies in requirements.txt**
- [ ] **File path operations work in both dev and container environments**

## 🔧 Service-Specific Checks

### Workflow Agent (gRPC Service)
- [ ] **Dependencies available**
  - [ ] OPENAI_API_KEY configured in SSM
  - [ ] ANTHROPIC_API_KEY configured in SSM
  - [ ] SUPABASE_URL and SUPABASE_SECRET_KEY configured
  - [ ] Redis endpoint accessible
- [ ] **Health check**: `nc -z localhost 50051`
- [ ] **Start period**: 240s minimum (updated after timeout issues)
- [ ] **gRPC server binds to `[::]`**

### Workflow Engine (gRPC Service)
- [ ] **Dependencies available**
  - [ ] Database connection string valid
  - [ ] Redis endpoint accessible
  - [ ] OPENAI_API_KEY and ANTHROPIC_API_KEY configured
- [ ] **Health check**: `nc -z localhost 50050` - **UPDATED after Jan 2025 port mismatch incident**
- [ ] **Start period**: 180s minimum (updated after timeout issues)
- [ ] **Database initialization handled gracefully**

### API Gateway (HTTP Service)
- [ ] **Health endpoint implemented**: `/health`
- [ ] **Load balancer target group configured**
- [ ] **Health check**: `curl -f http://localhost:8000/health`
- [ ] **Start period**: 120s minimum (updated for consistency)

## 🌐 Environment & Secrets

### SSM Parameters
- [ ] **All secrets exist in AWS SSM**
  - [ ] `/agent-team-production/openai/api-key`
  - [ ] `/agent-team-production/anthropic/api-key`
  - [ ] `/agent-team-production/supabase/url`
  - [ ] `/agent-team-production/supabase/secret-key`
- [ ] **No placeholder values** (e.g., "placeholder", "your-key-here")
  ```bash
  # CRITICAL: Verify no placeholder values
  aws ssm get-parameter --name "/agent-team-production/supabase/url" --with-decryption --query 'Parameter.Value'
  # Should return actual URL, NOT "placeholder"
  ```
- [ ] **Values are valid and current**
- [ ] **Services have graceful fallback for missing/invalid configuration**

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
  nc -z localhost 50050  # workflow-engine - UPDATED after Jan 2025 port mismatch incident
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
  - [ ] Initial desired_count: 1 (scale up after stability)
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

**Last Updated**: January 2025 after ECS health check protocol mismatch and port configuration incident.

## 🚨 Critical Incident: Module Import & SSM Configuration Failures (July 2025)

**Issue**: Services failing `aws ecs wait services-stable` with continuous task restarts and import errors

**Root Causes**:
1. **Docker Module Import Failures**:
   - workflow-engine: `python: can't open file '/app/workflow_engine/server.py': [Errno 2] No such file or directory`
   - Later: `/usr/local/bin/python: No module named workflow_engine.server`
   - **Cause**: Incorrect Dockerfile CMD path and Python package structure

2. **SSM Parameter Placeholder Values**:
   - workflow-agent: `supabase._sync.client.SupabaseException: Invalid URL`
   - **Cause**: SSM parameters contained "placeholder" instead of real values
   - Services crashed on startup when trying to initialize with placeholder URLs

3. **Missing Directory Structure**:
   - workflow-agent: `Template folder not found at: /shared/prompts`
   - **Cause**: Dockerfile didn't create correct `/shared/prompts` directory structure

**Critical Fix Applied**:
1. **Fixed Docker Module Structure**:
   ```dockerfile
   # WRONG: Flattened structure
   COPY workflow_engine/ .
   CMD ["python", "server.py"]

   # CORRECT: Preserved package hierarchy
   COPY workflow_engine/workflow_engine ./workflow_engine
   CMD ["python", "-m", "workflow_engine"]
   ```

2. **Updated SSM Parameters**:
   - Replaced all "placeholder" values with actual API keys and URLs
   - Added validation in code to detect placeholder values

3. **Enhanced Error Handling**:
   - Added graceful fallback when Supabase is misconfigured
   - Services now start with warnings instead of crashes

**Services Affected & Resolution**:
- ✅ **workflow-agent**: Fixed SSM + graceful RAG fallback → 2/2 tasks running
- 🔧 **workflow-engine**: Fixed module imports → Running (protobuf imports remaining)

**Prevention Checklist**:
- [ ] **Verify Docker package structure preserves Python imports**
  ```bash
  # Test module imports in container
  docker run --rm your-image python -c "import service_name.main"
  ```
- [ ] **Validate ALL SSM parameters contain real values**
  ```bash
  # Check for placeholder values
  aws ssm get-parameter --name "/path/to/param" --with-decryption --query 'Parameter.Value'
  ```
- [ ] **Test container startup locally with production-like environment**
- [ ] **Add graceful error handling for external service dependencies**
- [ ] **Use relative path detection for file system operations in containers**

## 🚨 Critical Incident: Health Check Protocol Mismatch & Port Configuration (Jan 2025)

**Issue**: Services failing `aws ecs wait services-stable` - Max attempts exceeded due to health check failures

**Root Causes**:
1. **Health Check Protocol Mismatches**:
   - **workflow-agent**: Used `grpc_health_probe -addr=localhost:50051` but `grpc_health_probe` NOT installed in Docker image
   - **workflow-engine**: Used `curl -f http://localhost:8000/health` on gRPC service (always fails)
   - Services continuously restarting due to failed health checks

2. **Port Configuration Inconsistencies**:
   - **workflow-engine**: ECS expected port 8000, Docker exposed port 50050
   - **Environment variables**: GRPC_PORT=8000 but container exposed 50050
   - Connection failures due to port mismatch

3. **Missing Health Check Dependencies**:
   - Docker images missing `netcat-traditional` package for `nc` command
   - Containers failing health checks with "command not found" errors

**Critical Fixes Applied**:
1. **Standardized Health Check Protocols**:
   ```yaml
   # WRONG: Protocol mismatches
   workflow-agent: grpc_health_probe (not installed)
   workflow-engine: curl on gRPC port (always fails)

   # CORRECT: TCP connection tests
   workflow-agent: nc -z localhost 50051
   workflow-engine: nc -z localhost 50050
   api-gateway: curl -f http://localhost:8000/health (HTTP service)
   ```

2. **Fixed Port Configurations**:
   - Updated workflow-engine to use port 50050 consistently
   - Fixed GRPC_PORT environment variable: 8000 → 50050
   - Ensured Docker EXPOSE matches ECS containerPort

3. **Added Missing Dependencies**:
   - Added `netcat-traditional` to all Dockerfiles requiring `nc` command
   - Increased resource allocation for workflow-agent (512→1024 CPU, 1024→2048 MB)

4. **Extended Health Check Grace Periods**:
   - workflow-agent: startPeriod 60s → 240s
   - workflow-engine: startPeriod 60s → 180s
   - api-gateway: startPeriod 60s → 120s

**Services Affected & Resolution**:
- ✅ **workflow-agent**: Fixed health check + added netcat + increased resources
- ✅ **workflow-engine**: Fixed port mismatch + health check protocol
- ✅ **api-gateway**: Health check already correct (HTTP service)

**Prevention Checklist**:
- [ ] **Verify health check protocol matches service type**
  ```bash
  # gRPC services MUST use TCP tests
  nc -z localhost PORT

  # HTTP services use curl
  curl -f http://localhost:PORT/health
  ```
- [ ] **Ensure Docker EXPOSE matches ECS containerPort**
- [ ] **Test health check commands in actual container**
  ```bash
  docker run --rm your-image nc -z localhost 50051
  ```
- [ ] **Verify all health check dependencies installed**
- [ ] **Use conservative startPeriod values for complex services**

## 🚨 Previous Incident: Health Check Timeouts (Jan 2025)

**Issue**: Services failing `aws ecs wait services-stable` due to premature health check failures

**Root Cause**:
- Health check `startPeriod` values too low for service initialization
- Services restarting before full startup, causing deployment instability
- Multiple task instances running (3 vs 2 desired) due to failed health checks

**Solution Applied**:
- Increased all health check `startPeriod` values significantly:
  - API Gateway: 60s → 120s
  - Workflow Engine: 90s → 180s
  - Workflow Agent: 120s → 240s
- Reduced initial `desired_count` from 2 to 1 for deployment stability
- Enhanced monitoring of task health status during deployments

**Prevention**:
- Always test health check timing locally before deployment
- Monitor ECS service events for health check failures
- Use conservative `startPeriod` values for complex services

## 🚨 Critical Incident: Missing Database Configuration - workflow-engine Service (July 2025)

**Issue**: `aws ecs wait services-stable` hanging indefinitely (8+ minutes) due to workflow-engine service failing to start

**Root Cause**: workflow-engine service requires PostgreSQL database connection but configuration was missing:
1. **Missing Database Environment Variables**:
   - No `SUPABASE_URL` or `DATABASE_URL` configured in ECS task definition
   - Service tried to connect to database on startup and failed immediately
   - Container exit code 1: "Essential container in task exited"

2. **Placeholder SSM Values**:
   - SSM parameter `/agent-team-production/supabase/url` contained "placeholder"
   - SSM parameter `/agent-team-production/supabase/secret-key` contained "placeholder"
   - Even with secrets configured, placeholder values cause connection failures

**Service Failure Symptoms**:
- `aws ecs wait services-stable` never completes (hangs indefinitely)
- ECS service shows: 0 running tasks, 2 pending tasks, 49+ failed tasks
- Container logs: `❌ Database connection failed`, `❌ Failed to start unified gRPC server: Database connection failed`
- Tasks continuously restart and fail within seconds of startup

**Critical Fix Applied**:
1. **Added Missing Database Secrets to Task Definition**:
   ```terraform
   # In infra/ecs.tf - workflow_engine task definition secrets block
   secrets = [
     {
       name      = "OPENAI_API_KEY"
       valueFrom = aws_ssm_parameter.openai_api_key.arn
     },
     {
       name      = "ANTHROPIC_API_KEY"
       valueFrom = aws_ssm_parameter.anthropic_api_key.arn
     },
     # ADDED: Missing database configuration
     {
       name      = "SUPABASE_URL"
       valueFrom = aws_ssm_parameter.supabase_url.arn
     },
     {
       name      = "SUPABASE_SECRET_KEY"
       valueFrom = aws_ssm_parameter.supabase_secret_key.arn
     }
   ]
   ```

2. **Update SSM Parameters with Real Values**:
   ```bash
   # Replace placeholder values with actual Supabase credentials
   aws ssm put-parameter --name "/agent-team-production/supabase/url" \
     --value "https://your-project.supabase.co" --type "SecureString" --overwrite

   aws ssm put-parameter --name "/agent-team-production/supabase/secret-key" \
     --value "your-actual-supabase-key" --type "SecureString" --overwrite
   ```

3. **Deploy Updated Task Definition**:
   ```bash
   # Apply Terraform changes
   terraform apply -target=aws_ecs_task_definition.workflow_engine

   # Update service to use new task definition
   aws ecs update-service --cluster agent-team-production-cluster \
     --service workflow-engine-service \
     --task-definition agent-team-production-workflow-engine:37
   ```

**workflow-engine Database Dependency Understanding**:
- The workflow-engine service uses PostgreSQL for persistence via Supabase
- Database connection is established during service startup (`workflow_engine/server.py`)
- Service fails immediately if database connection cannot be established
- Unlike other services, workflow-engine has a hard dependency on database availability

**Verification Commands**:
```bash
# 1. Check if database secrets are configured in task definition
aws ecs describe-task-definition \
  --task-definition agent-team-production-workflow-engine:latest \
  --query 'taskDefinition.containerDefinitions[0].secrets[?contains(name, `SUPABASE`)]' \
  --region us-east-1

# 2. Verify SSM parameters contain real values (not "placeholder")
aws ssm get-parameter --name "/agent-team-production/supabase/url" \
  --region us-east-1 --with-decryption --query 'Parameter.Value' --output text

# 3. Monitor service health after configuration fix
aws ecs describe-services --cluster agent-team-production-cluster \
  --services workflow-engine-service --region us-east-1 \
  --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount,Pending:pendingCount,TaskDef:taskDefinition}'

# 4. Check recent task failures for database connection errors
aws logs filter-log-events --log-group-name "/ecs/agent-team-production" \
  --log-stream-name-prefix "workflow-engine" --start-time $(date -d '30 minutes ago' +%s)000 \
  --region us-east-1 --query 'events[?contains(message, `Database`)]' --output text
```

**Prevention Checklist**:
- [ ] **Verify workflow-engine has database configuration BEFORE deployment**
  ```bash
  # Must show SUPABASE_URL and SUPABASE_SECRET_KEY in secrets
  aws ecs describe-task-definition --task-definition agent-team-production-workflow-engine:latest \
    --query 'taskDefinition.containerDefinitions[0].secrets' --region us-east-1
  ```
- [ ] **Ensure SSM parameters contain actual values, not placeholders**
  ```bash
  # Should return actual Supabase URL, NOT "placeholder"
  aws ssm get-parameter --name "/agent-team-production/supabase/url" \
    --with-decryption --query 'Parameter.Value' --region us-east-1
  ```
- [ ] **Test database connectivity before deployment**
  ```bash
  # Test connection with actual credentials
  psql "postgresql://postgres:password@db.project.supabase.co:5432/postgres?sslmode=require"
  ```
- [ ] **Monitor task startup logs for database connection errors**
- [ ] **Set workflow-engine startPeriod ≥180s to account for database initialization**

**Critical Learning**: workflow-engine is the ONLY service with a hard database dependency. All other services (api-gateway, workflow-agent) can start without database but workflow-engine cannot. Always verify database configuration exists and is valid before deploying workflow-engine.

## 🚨 Critical Incident: Protobuf Import Failures - workflow-engine Service (RESOLVED - July 2025)

**Issue**: `aws ecs wait services-stable` timing out due to workflow-engine service continuous task restart cycle

**Root Cause**: Missing protobuf files causing critical import failures:
```
ImportError: cannot import name 'workflow_service_pb2' from 'proto' (/app/proto/__init__.py)
```

**Service Failure Symptoms**:
- Tasks fail immediately on startup with Python import errors
- Service shows: 0 running tasks, 2 desired, 28+ failed tasks
- `aws logs tail` shows continuous import error pattern every 10-20 seconds
- Container exit code 1: Essential container unable to start due to missing dependencies

**Investigation Results**:
1. **Docker Build Issue**: Protobuf files not generated or copied correctly during image build
2. **Import Path Problem**: Proto files not available at expected import location `/app/proto/`
3. **Build Process Failure**: Proto generation script couldn't find source files or failed silently
4. **Working Directory Context**: Proto generation was running in wrong directory context

**✅ FINAL RESOLUTION APPLIED (July 2025)**:
1. **Fixed Dockerfile Proto Generation**:
   ```dockerfile
   # BEFORE: Proto generation failed due to working directory and import issues
   RUN python -c "import sys, os; sys.path.insert(0, '.'); from generate_proto import generate_proto_files; generate_proto_files()" && echo "Proto generation completed successfully"
   RUN cp -r /app/workflow_engine/proto /app/proto

   # AFTER: Fixed working directory context and script location
   COPY --from=builder /app/workflow_engine/generate_proto.py ./workflow_engine/
   WORKDIR /app/workflow_engine
   RUN python generate_proto.py && echo "Proto generation completed successfully"
   WORKDIR /app
   RUN cp -r /app/workflow_engine/proto /app/proto
   RUN ls -la /app/proto/ && python -c "from proto import workflow_service_pb2; print('Proto import test successful')"
   ```

2. **Key Fix Details**:
   - **Proper Working Directory**: Change to `/app/workflow_engine` before running proto generation
   - **Script Location**: Copy `generate_proto.py` to correct location within workflow_engine directory
   - **Verification Step**: Added proto import test in Dockerfile to catch failures early
   - **Direct Copy Method**: Confirmed symlinks don't work reliably in Docker context

3. **Deployment Success**:
   - Built and deployed new image: `fixed-proto-20250728-010009`
   - Updated task definition: `agent-team-production-workflow-engine:39`
   - **Result**: Service now shows 1/2 tasks running (significant improvement from 0/2)
   - **Logs**: No more protobuf import errors in startup logs

**Services Affected & Resolution Status**:
- ✅ **workflow-engine**: **FULLY RESOLVED** → Proto files now generate and import correctly
- ✅ **workflow-agent**: No impact (has own proto generation working)
- ✅ **api-gateway**: No impact (no proto dependencies)

**Protobuf Dependency Understanding**:
- workflow-engine has complex gRPC dependencies requiring multiple .proto files
- Proto files must be generated from `/shared/proto/engine/` source files during build
- Import statement `from proto import workflow_service_pb2` requires files at `/app/proto/`
- Generation requires grpcio-tools and proper Python path resolution

**Verification Commands**:
```bash
# 1. Test proto generation locally before build
cd apps/backend/workflow_engine && python generate_proto.py
ls -la proto/  # Should show: workflow_service_pb2.py, execution_pb2.py, etc.

# 2. Build and test Docker image with proto verification
docker build --platform linux/amd64 -f workflow_engine/Dockerfile -t workflow-engine-test .
docker run --rm workflow-engine-test ls -la /app/proto/
docker run --rm workflow-engine-test python -c "from proto import workflow_service_pb2; print('Proto import successful')"

# 3. Check service status after deployment
aws ecs describe-services --cluster agent-team-production-cluster \
  --services workflow-engine-service --region us-east-1 \
  --query 'services[0].{Running:runningCount,Desired:desiredCount,TaskDef:taskDefinition}'

# 4. Monitor container startup logs for proto errors
aws logs filter-log-events --log-group-name "/ecs/agent-team-production" \
  --log-stream-name-prefix "workflow-engine" --start-time $(date -d '5 minutes ago' +%s)000 \
  --region us-east-1 --query 'events[?contains(message, `ImportError`) || contains(message, `proto`)].message'
```

**Updated Prevention Checklist**:
- [ ] **Test protobuf generation locally in correct directory context**
  ```bash
  cd apps/backend/workflow_engine && python generate_proto.py
  ls -la proto/  # Must show all generated .py files
  python -c "from proto import workflow_service_pb2; print('Local test passed')"
  ```
- [ ] **Use proper working directory in Dockerfile for proto generation**
  ```dockerfile
  COPY --from=builder /app/workflow_engine/generate_proto.py ./workflow_engine/
  WORKDIR /app/workflow_engine
  RUN python generate_proto.py
  WORKDIR /app
  RUN cp -r /app/workflow_engine/proto /app/proto
  ```
- [ ] **Add proto import verification in Docker build**
  ```dockerfile
  RUN python -c "from proto import workflow_service_pb2; print('Proto import test successful')"
  ```
- [ ] **Test complete Docker build with proto verification before ECR push**
  ```bash
  docker build --platform linux/amd64 -f workflow_engine/Dockerfile -t test-image .
  docker run --rm test-image python -c "from proto import workflow_service_pb2"
  ```
- [ ] **Monitor ECS service for successful task startup after deployment**
  ```bash
  aws ecs describe-services --cluster agent-team-production-cluster \
    --services workflow-engine-service --region us-east-1
  ```
- [ ] **Ensure grpcio-tools installed and shared proto source files available during build**

**Critical Learning**: Protobuf generation requires correct working directory context during Docker build. The script must run from the directory containing the generate_proto.py file with proper Python path resolution. Always include verification steps in the Dockerfile to catch proto generation failures before deployment. Working directory changes are crucial for successful proto file generation.
