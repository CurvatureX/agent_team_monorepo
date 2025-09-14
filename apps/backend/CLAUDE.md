# CLAUDE.md - Backend Development Guide

This file provides guidance to Claude Code and other AI assistants when working with the backend services in this repository.

## Architecture Overview

This backend consists of three main services that work together to provide AI-powered workflow automation:

### Services Structure
```
apps/backend/
├── api-gateway/       # Client-facing API (FastAPI)
├── workflow_agent/    # AI workflow consultant (FastAPI, formerly gRPC)
├── workflow_engine/   # Workflow execution engine (FastAPI)
└── shared/           # Shared models and utilities
```

### Service Communication
- **API Gateway** → **Workflow Agent**: HTTP/REST for workflow generation
- **API Gateway** → **Workflow Engine**: HTTP/REST for workflow execution
- All services now use FastAPI (migrated from gRPC)

## Critical Import Patterns & Best Practices

### ⚠️ **CRITICAL: Package Structure Rules**

**NEVER** use relative imports at the module level. Always use absolute imports for cross-module dependencies.

#### ✅ **Correct Import Patterns**

**For workflow_agent:**
```python
# In workflow_agent/main.py
from workflow_agent.core.config import settings
from workflow_agent.services.grpc_server import WorkflowAgentServer

# In workflow_agent/agents/workflow_agent.py
from workflow_agent.core.config import settings
from .nodes import WorkflowAgentNodes  # relative OK within same package
```

**For workflow_engine:**
```python
# In workflow_engine/server.py
from workflow_engine.services.main_service import MainWorkflowService
from workflow_engine.core.config import settings

# In workflow_engine/nodes/trigger_node.py
from croniter import croniter  # external dependency
from ..core.config import settings  # relative OK for parent package
```

#### ❌ **Incorrect Import Patterns**
```python
# NEVER do this at module level:
from .core.config import settings  # Will cause "attempted relative import with no known parent package"
from ..services.grpc_server import WorkflowAgentServer  # Same error
```

### 🐳 **Docker Configuration Rules**

#### ✅ **Correct Dockerfile Structure**

**For workflow_agent:**
```dockerfile
# Preserve package structure
COPY workflow_agent/ ./workflow_agent/
COPY shared/ ./shared/

# Run as module to maintain package hierarchy
CMD ["python", "-m", "workflow_agent.main"]
```

**For workflow_engine:**
```dockerfile
# Install dependencies from requirements.txt
RUN pip install --prefix=/install -r requirements.txt

# Ensure correct platform for ECS deployment
# Build with: docker build --platform linux/amd64
```

#### ❌ **Common Docker Mistakes**
```dockerfile
# NEVER flatten package structure:
COPY workflow_agent/ .  # Breaks import hierarchy

# NEVER run without module flag:
CMD ["python", "main.py"]  # Causes import errors

# NEVER forget platform specification for ECS:
# docker build . (without --platform linux/amd64)
```

## Service-Specific Configurations

### API Gateway (FastAPI Service)
- **Port**: 8000
- **Protocol**: HTTP/REST with OpenAPI docs
- **Dependencies**: FastAPI, Supabase Auth, Redis
- **Health Check**: `curl -f http://localhost:8000/health || exit 1`
- **Key Features**: Authentication, rate limiting, request routing

### Workflow Agent (FastAPI Service)
- **Port**: 8001 (migrated from gRPC port 50051)
- **Protocol**: HTTP/REST with streaming support
- **Dependencies**: LangGraph, OpenAI, Anthropic APIs, Supabase (for RAG)
- **Health Check**: `curl -f http://localhost:8001/health || exit 1`
- **Start Period**: 120s

### Workflow Engine (FastAPI Service)
- **Port**: 8002
- **Protocol**: HTTP/REST API
- **Dependencies**: croniter, Redis, PostgreSQL, SQLAlchemy
- **Health Check**: `curl -f http://localhost:8002/health || exit 1`
- **Start Period**: 90s

## Development Commands

### Core Development
- **Install dependencies**:
  - API Gateway: `cd api-gateway && pip install -e .`
  - Workflow Agent: `cd workflow_agent && uv pip install --system -e .`
  - Workflow Engine: `cd workflow_engine && pip install -r requirements.txt`
- **Run services**:
  - API Gateway: `cd api-gateway && python main.py`
  - Workflow Agent: `cd workflow_agent && python main.py`
  - Workflow Engine: `cd workflow_engine && python main.py`
- **Run tests**: `pytest tests/`

### Docker Development
```bash
# Build for local development (ARM64 on Mac)
docker build -f workflow_agent/Dockerfile -t workflow-agent .

# Build for AWS ECS deployment (AMD64 required)
docker build -f workflow_agent/Dockerfile -t workflow-agent --platform linux/amd64 .
docker build -f workflow_engine/Dockerfile -t workflow-engine --platform linux/amd64 .
```

### AWS ECS Deployment
```bash
# Tag and push images
docker tag workflow-agent 982081090398.dkr.ecr.us-east-1.amazonaws.com/agent-team/workflow-agent:latest
docker tag workflow-engine 982081090398.dkr.ecr.us-east-1.amazonaws.com/agent-team/workflow-engine:latest

# Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 982081090398.dkr.ecr.us-east-1.amazonaws.com
docker push 982081090398.dkr.ecr.us-east-1.amazonaws.com/agent-team/workflow-agent:latest
docker push 982081090398.dkr.ecr.us-east-1.amazonaws.com/agent-team/workflow-engine:latest
```

## Testing and Authentication

### Test Authentication Setup

When running tests or development tasks that require authentication:

- **Authentication credentials** are stored in `.env` file
- **IMPORTANT**: Always use the real test account credentials from `.env`:
- **GetToken interface** is available for obtaining JWT tokens programmatically
- Test files should use the authentication flow from `.env` configuration
- Example test authentication pattern:
  ```python
  # Load from .env
  supabase_url = os.getenv("SUPABASE_URL")
  test_email = os.getenv("TEST_USER_EMAIL")
  test_password = os.getenv("TEST_USER_PASSWORD")
  supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")

  # Use GetToken API for authentication
  auth_url = f"{supabase_url}/auth/v1/token?grant_type=password"
  ```
- **Note**: The test account must already exist in Supabase. Never use fake credentials as authentication will fail.

### Test Suite Architecture

The testing system has been upgraded with a modular structure:
- `tests/auth/` - Authentication functionality tests
- `tests/session/` - Session management tests
- `tests/chat/` - Chat and streaming response tests
- `tests/integration/` - End-to-end integration tests
- `tests/utils/` - Shared test utilities and configuration

Run tests using: `python run_tests.py --all` or `python run_tests.py --quick`

## Environment Configuration

### Required Environment Variables

**API Gateway:**
```bash
# Core service
APP_NAME="Workflow API Gateway"
PORT="8000"
DEBUG="false"

# Supabase Auth
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_ANON_KEY="eyJ..."
SUPABASE_SERVICE_KEY="eyJ..."

# Backend services
WORKFLOW_AGENT_URL="http://localhost:8001"
WORKFLOW_ENGINE_URL="http://localhost:8002"

# Redis cache
REDIS_URL="redis://localhost:6379"
```

**Workflow Agent:**
```bash
# Core service
FASTAPI_PORT="8001"
HOST="0.0.0.0"
DEBUG="false"

# AI APIs
OPENAI_API_KEY="sk-..."
ANTHROPIC_API_KEY="sk-ant-..."

# Supabase RAG system
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_SECRET_KEY="sb_secret_..."

# RAG Configuration
EMBEDDING_MODEL="text-embedding-ada-002"
RAG_SIMILARITY_THRESHOLD="0.3"
```

**Workflow Engine:**
```bash
# Core service
PORT="8002"
DEBUG="false"

# Database
DATABASE_URL="postgresql://user:pass@localhost/workflow_engine"

# Redis
REDIS_URL="redis://localhost:6379/0"
```

## Common Issues & Solutions

### Import Errors
**Issue**: `ImportError: attempted relative import with no known parent package`
**Solution**:
1. Ensure Dockerfile preserves package structure: `COPY service_name/ ./service_name/`
2. Run as module: `CMD ["python", "-m", "service_name.main"]`
3. Use absolute imports for cross-module dependencies

### Missing Dependencies
**Issue**: `ModuleNotFoundError: No module named 'croniter'`
**Solution**:
1. Add dependency to `requirements.txt`
2. Update Dockerfile: `RUN pip install -r requirements.txt`
3. Rebuild and push image with unique tag

### Docker Platform Issues
**Issue**: `image Manifest does not contain descriptor matching platform 'linux/amd64'`
**Solution**:
1. Build with platform flag: `docker build --platform linux/amd64`
2. ECS Fargate requires AMD64 architecture

### Health Check Configuration Issues
**Issue**: Health checks failing due to protocol/command mismatch
**Critical Solutions**:
- **NEVER use HTTP health checks on gRPC services**: `curl` will always fail on gRPC ports
- **Use TCP connection tests**: `nc -z localhost PORT` works for all service types
- **Match health check to service type**:
  - HTTP/REST API → `curl -f http://localhost:PORT/health`
  - gRPC Server → `nc -z localhost PORT` or `grpc_health_probe -addr=localhost:PORT`
  - TCP Service → `nc -z localhost PORT`
- **Set appropriate grace periods**: gRPC services need 90-120s start periods

### Supabase Connection
**Issue**: "Invalid URL" errors from Supabase client
**Solution**:
1. Ensure SSM parameter contains valid URL format: `https://your-project.supabase.co`
2. Not placeholder values like "placeholder"

### Supabase RLS Performance Issues
**Issue**: API responses taking 3+ seconds when using Row Level Security (RLS)
**Root Cause**: `client.auth.set_session(access_token, access_token)` makes expensive HTTP calls on every repository initialization
**Solution**: Use header-based authentication instead of session-based authentication
```python
# ❌ SLOW - Avoid this pattern:
self.client.auth.set_session(access_token, access_token)

# ✅ FAST - Use header-based auth:
self.client.auth.session = None  # Clear any existing session
self.client.headers["Authorization"] = f"Bearer {access_token}"
```
**Performance Impact**: Reduces API response times from 3+ seconds to ~2.4 seconds (20% improvement)
**Applied**: Workflow Engine optimized, API Gateway already uses correct pattern

## Testing Strategy

### Unit Tests
```bash
# Run all tests
pytest tests/

# Run specific service tests
pytest tests/workflow_agent/
pytest tests/workflow_engine/

# Run with coverage
pytest --cov=workflow_agent tests/workflow_agent/
```

### Integration Tests
```bash
# Test gRPC service
python tests/integration/test_grpc_service.py

# Test end-to-end workflow
python tests/integration/test_workflow_execution.py
```

## Deployment Checklist

Before deploying to AWS ECS:

- [ ] ✅ All imports use correct absolute/relative patterns
- [ ] ✅ Docker images built with `--platform linux/amd64`
- [ ] ✅ All required dependencies in requirements.txt
- [ ] ✅ Health checks configured for correct ports with adequate startPeriod values
- [ ] ✅ Environment variables configured in ECS task definition
- [ ] ✅ ECR images pushed with unique tags
- [ ] ✅ Task definitions registered and services updated

## Key Learnings from Production Issues

1. **Package Structure is Critical**: Python import system requires proper package hierarchy preservation in Docker
2. **Platform Consistency**: Local development (ARM64) vs production (AMD64) platform differences cause deployment failures
3. **Dependency Management**: All dependencies must be explicitly declared and installed correctly
4. **Health Check Protocol Matching**: CRITICAL - Health checks must match service protocol (HTTP vs gRPC)
5. **Grace Period Configuration**: gRPC services need longer startup times than HTTP services
6. **Environment Variables**: Placeholder values in configuration cause runtime failures
7. **Health Check Timing**: Conservative startPeriod values prevent deployment timeouts and service instability

### Health Check Protocol Matrix
| Service Type | Port | Protocol | Health Check Command |
|-------------|------|----------|---------------------|
| api-gateway | 8000 | HTTP | `curl -f http://localhost:8000/health` (startPeriod: 60s) |
| workflow-agent | 8001 | HTTP | `curl -f http://localhost:8001/health` (startPeriod: 120s) |
| workflow-engine | 8002 | HTTP | `curl -f http://localhost:8002/health` (startPeriod: 90s) |

### Critical Health Check Rules
- ✅ **ALWAYS**: Use `curl` for HTTP/FastAPI services
- ✅ **ALWAYS**: Set appropriate startPeriod based on service complexity
- ✅ **ALWAYS**: Test health check command locally before deployment
- ✅ **ALWAYS**: Use conservative timing - services need adequate startup time
- ✅ **ALWAYS**: Include health endpoint in all FastAPI services

## RAG System Integration

The workflow_agent includes a sophisticated RAG (Retrieval-Augmented Generation) system:

- **Vector Store**: Supabase with pgvector for node knowledge storage
- **Embeddings**: OpenAI text-embedding-ada-002 for semantic search
- **Knowledge Base**: Pre-populated with workflow node examples and best practices

### RAG Configuration
```python
# In workflow_agent/core/config.py
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_SECRET_KEY: str = os.getenv("SUPABASE_SECRET_KEY", "")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
RAG_SIMILARITY_THRESHOLD: float = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.3"))
```

## Recent Production Fixes (Jan 2025)

### ECS Deployment Timeout Resolution

**Issue**: `aws ecs wait services-stable` timing out due to health check failures

**Investigation Results**:
- Services were restarting before completing initialization
- Multiple task instances running (3 vs 2 desired) due to failed health checks
- Health check `startPeriod` values were insufficient for service startup

**Applied Fixes**:
1. **Increased Health Check Grace Periods**:
   - Workflow Agent: 120s → 240s
   - Workflow Engine: 90s → 180s
   - API Gateway: 60s → 120s

2. **Infrastructure Configuration**:
   - Reduced initial `desired_count` from 2 to 1
   - Updated Terraform variables for stable deployments

3. **Monitoring Improvements**:
   - Enhanced ECS service event monitoring
   - Better health status tracking during deployments

**Key Learning**: Always use conservative health check timing to prevent deployment instability.

This documentation should be updated whenever architectural changes are made to prevent future deployment issues.
