# CLAUDE.md - Backend Development Guide

This file provides guidance to Claude Code and other AI assistants when working with the backend services in this repository.

## Architecture Overview

This backend consists of two main services that work together to provide AI-powered workflow automation:

### Services Structure
```
apps/backend/
├── workflow_agent/     # AI workflow consultant (gRPC service)
├── workflow_engine/    # Workflow execution engine (FastAPI + gRPC)
└── shared/            # Shared protobuf definitions and utilities
```

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

### Workflow Agent (gRPC Service)
- **Port**: 50051 (gRPC)
- **Protocol**: gRPC with TCP health checks
- **Dependencies**: OpenAI, Anthropic APIs, Supabase (for RAG), Redis
- **Health Check**: `nc -z localhost 50051 || exit 1` (TCP connection test)
- **Start Period**: 120s (service takes time to initialize)

### Workflow Engine (gRPC Service)
- **Port**: 8000 (gRPC)
- **Protocol**: gRPC server with TCP health checks
- **Dependencies**: croniter, Redis, PostgreSQL, gRPC tools
- **Health Check**: `nc -z localhost 8000 || exit 1` (TCP connection test)
- **Start Period**: 90s (database initialization required)

## Development Commands

### Core Development
- **Install dependencies**: `pip install -r requirements.txt`
- **Run workflow-agent**: `python -m workflow_agent.main`
- **Run workflow-engine**: `python -m workflow_engine.server`
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

## Environment Configuration

### Required Environment Variables

**Workflow Agent:**
```bash
# Core service
GRPC_HOST="[::]"
GRPC_PORT="50051"
DEBUG="false"

# AI APIs
OPENAI_API_KEY="sk-..."
ANTHROPIC_API_KEY="sk-ant-..."

# Supabase RAG system
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_SECRET_KEY="sb_secret_..."

# State management
REDIS_URL="redis://localhost:6379/0"
```

**Workflow Engine:**
```bash
# Core service
PORT="8000"
DEBUG="false"

# AI APIs (for workflow execution)
OPENAI_API_KEY="sk-..."
ANTHROPIC_API_KEY="sk-ant-..."

# Data persistence
DATABASE_URL="postgresql://user:pass@localhost/workflow_engine"
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
- [ ] ✅ Health checks configured for correct ports
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

### Health Check Protocol Matrix
| Service Type | Port | Protocol | Health Check Command |
|-------------|------|----------|---------------------|
| workflow-agent | 50051 | gRPC | `nc -z localhost 50051` |
| workflow-engine | 8000 | gRPC | `nc -z localhost 8000` |
| api-gateway | 8000 | HTTP | `curl -f http://localhost:8000/health` |

### Critical Health Check Rules
- ❌ **NEVER**: `curl` on gRPC ports → Always fails
- ✅ **ALWAYS**: Use `nc -z` for gRPC services
- ✅ **ALWAYS**: Set startPeriod ≥ 90s for gRPC services
- ✅ **ALWAYS**: Test health check command locally before deployment

## RAG System Integration

The workflow_agent includes a sophisticated RAG (Retrieval-Augmented Generation) system:

- **Vector Store**: Supabase with pgvector for node knowledge storage
- **Embeddings**: OpenAI text-embedding-ada-002 for semantic search
- **Knowledge Base**: Pre-populated with workflow node examples and best practices

### RAG Configuration
```python
# In workflow_agent/core/config.py
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
RAG_SIMILARITY_THRESHOLD: float = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.3"))
```

This documentation should be updated whenever architectural changes are made to prevent future deployment issues.
