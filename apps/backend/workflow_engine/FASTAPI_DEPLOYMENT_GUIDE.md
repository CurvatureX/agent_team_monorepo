# FastAPI Deployment Guide

This guide covers deploying the migrated Workflow Engine from gRPC to FastAPI + Pydantic.

## 🚀 Quick Start

### Local Development with Docker

1. **Build and start the FastAPI service:**
```bash
cd apps/backend/workflow_engine
docker-compose -f docker-compose.test.yml up --build
```

2. **Verify the service is running:**
```bash
# Check health
curl http://localhost:8000/health

# View API documentation
open http://localhost:8000/docs
```

3. **Run endpoint tests:**
```bash
python test_fastapi_endpoints.py
```

### Production Docker Setup

Use the new FastAPI-enabled Docker Compose configuration:

```bash
cd apps/backend
docker-compose -f docker-compose.fastapi.yml up --build
```

This will start:
- **Workflow Engine** (FastAPI) on port `8002` → `http://localhost:8002`
- **Workflow Agent** (gRPC) on port `50051` (unchanged)
- **API Gateway** (HTTP) on port `8000` → `http://localhost:8000`
- **Redis** on port `6379`

## 📋 Migration Summary

### What Changed

| Component | Before (gRPC) | After (FastAPI) |
|-----------|---------------|-----------------|
| **Protocol** | gRPC/Protobuf | HTTP/JSON |
| **Port** | 50050 | 8000 |
| **Health Check** | `nc -z localhost 50050` | `curl -f http://localhost:8000/health` |
| **API Documentation** | None | `/docs` and `/redoc` |
| **Data Models** | Protobuf | Pydantic |
| **Validation** | Protobuf validation | Pydantic validation with error details |
| **Startup Time** | ~180s | ~60s |

### Key Benefits

✅ **Eliminates protobuf import issues** in Docker deployments
✅ **Full IDE support** with Pydantic type checking
✅ **Automatic API documentation** at `/docs`
✅ **Better error messages** with detailed validation
✅ **Faster startup** with HTTP instead of gRPC
✅ **Standard HTTP monitoring** and debugging tools

## 🏗️ Architecture

### New API Structure

```
Workflow Engine FastAPI (Port 8000)
├── /health                           # Health check endpoint
├── /docs                            # Swagger UI documentation
├── /redoc                           # ReDoc documentation
├── /v1/workflows                    # Workflow CRUD operations
│   ├── POST /                       # Create workflow
│   ├── GET /{id}                    # Get workflow
│   ├── PUT /{id}                    # Update workflow
│   ├── DELETE /{id}                 # Delete workflow
│   ├── GET /                        # List workflows
│   ├── POST /{id}/execute           # Execute workflow
│   ├── GET /executions/{id}/status  # Get execution status
│   ├── POST /executions/{id}/cancel # Cancel execution
│   ├── GET /executions/history      # Get execution history
│   ├── POST /validate               # Validate workflow
│   └── POST /test-node              # Test single node
└── /v1/triggers                     # Trigger management
    ├── POST /                       # Create trigger
    ├── GET /{id}                    # Get trigger
    ├── PUT /{id}                    # Update trigger
    ├── DELETE /{id}                 # Delete trigger
    ├── GET /                        # List triggers
    ├── POST /{id}/fire              # Fire trigger
    └── GET /{id}/events             # Get trigger events
```

### Service Communication

```mermaid
graph LR
    Frontend --> API_Gateway[API Gateway :8000]
    API_Gateway --> |HTTP/JSON| Workflow_Engine[Workflow Engine :8000]
    API_Gateway --> |gRPC| Workflow_Agent[Workflow Agent :50051]
    Workflow_Engine --> Database[(PostgreSQL)]
    Workflow_Engine --> Redis[(Redis)]
```

## 🐳 Docker Configuration

### Dockerfile.fastapi

The new Dockerfile uses HTTP health checks instead of gRPC:

```dockerfile
# Health check using HTTP endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run FastAPI with uvicorn
CMD ["python", "-m", "uvicorn", "workflow_engine.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables

Required environment variables for FastAPI deployment:

```bash
# Service configuration
PORT=8000
DEBUG=false

# Database
DATABASE_URL=postgresql://user:password@host:port/database

# Cache
REDIS_URL=redis://host:port/0

# AI APIs (optional for core functionality)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

## 🔧 API Gateway Integration

### Updated Configuration

The API Gateway now connects to the workflow engine via HTTP:

```python
# api-gateway/app/config.py
WORKFLOW_ENGINE_HOST: str = "localhost"
WORKFLOW_ENGINE_HTTP_PORT: int = 8000  # New FastAPI port
```

### HTTP Client Usage

```python
from app.services.workflow_service_http_client import WorkflowServiceHTTPClient

client = WorkflowServiceHTTPClient()
await client.connect()

# Create workflow
result = await client.create_workflow(
    user_id="user123",
    name="Test Workflow",
    description="A test workflow",
    nodes=[...],
    connections={...}
)
```

## 🧪 Testing

### Automated Tests

Run the comprehensive test suite:

```bash
# Quick health check
python test_fastapi_endpoints.py health

# Full test suite
python test_fastapi_endpoints.py

# Using the test script
./test_migration.sh
```

### Manual Testing

1. **Health Check:**
```bash
curl http://localhost:8000/health
```

2. **Create Workflow:**
```bash
curl -X POST http://localhost:8000/v1/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Workflow",
    "description": "A simple test workflow",
    "nodes": [...],
    "connections": {...},
    "user_id": "test_user"
  }'
```

3. **API Documentation:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🚢 AWS ECS Deployment

### Updated Task Definition

The ECS task definition changes from gRPC to HTTP:

```hcl
# Port mapping updated
port_mappings = [
  {
    container_port = 8000  # Changed from 50050
    protocol      = "tcp"
  }
]

# Health check updated
health_check = {
  command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
  interval    = 30
  timeout     = 5
  retries     = 3
  start_period = 60  # Reduced from 180s
}
```

### Load Balancer Configuration

All services now use the same Application Load Balancer:

```hcl
# Target group for workflow engine (HTTP)
resource "aws_lb_target_group" "workflow_engine_http" {
  name        = "workflow-engine-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }
}
```

## 🔍 Monitoring & Debugging

### Health Checks

- **Endpoint:** `GET /health`
- **Response:** JSON with service status and dependencies
- **Use:** Load balancer health checks, monitoring systems

### Logging

Enhanced structured logging with emoji indicators:
- 📝 Workflow operations (create, update, delete)
- 🚀 Execution operations (start, status, cancel)
- ✅ Successful operations
- ❌ Errors and failures
- ⚠️ Warnings and validation issues

### API Documentation

- **Swagger UI:** Interactive API testing at `/docs`
- **ReDoc:** Clean API documentation at `/redoc`
- **OpenAPI JSON:** Machine-readable spec at `/openapi.json`

## 🔒 Security Considerations

### Input Validation

Pydantic models provide comprehensive validation:
- **Type checking:** Automatic type coercion and validation
- **Field validation:** Custom validators for business logic
- **Error messages:** Detailed validation error responses
- **Sanitization:** Input sanitization utilities

### Authentication

The FastAPI service relies on the API Gateway for authentication:
- **User ID:** Passed in request parameters/body
- **Session tracking:** Optional session_id for request correlation
- **No direct auth:** Service focuses on workflow logic

## 📊 Performance

### Startup Time

| Metric | gRPC | FastAPI | Improvement |
|--------|------|---------|-------------|
| **Container startup** | ~180s | ~60s | 3x faster |
| **First request** | ~5s | ~1s | 5x faster |
| **Health check** | TCP probe | HTTP endpoint | More reliable |

### Request Processing

- **JSON serialization:** Optimized with Pydantic
- **HTTP overhead:** Minimal impact vs gRPC for current load
- **Async processing:** Full async/await support with FastAPI

## 🔄 Rollback Strategy

### Emergency Rollback

If issues arise, you can quickly rollback to gRPC:

1. **Switch Docker Compose:**
```bash
# Stop FastAPI version
docker-compose -f docker-compose.fastapi.yml down

# Start original gRPC version
docker-compose up --build
```

2. **Update API Gateway:**
```bash
# Revert to gRPC client in API Gateway code
# Deploy previous API Gateway version
```

3. **Infrastructure Rollback:**
```bash
# Revert ECS task definitions
# Switch load balancer target groups
```

### Gradual Migration

For production, consider a gradual migration:

1. **Deploy both versions** (gRPC + FastAPI)
2. **Route percentage of traffic** to FastAPI
3. **Monitor metrics** and error rates
4. **Gradually increase** FastAPI traffic
5. **Decommission gRPC** when confident

## 📚 Additional Resources

### Documentation
- **API Reference:** Available at `/docs` when service is running
- **Migration Plan:** `/docs/tech-design/grpc-to-fastapi-migration.md`
- **Architecture:** `/workflow_engine/doc/WORKFLOW_ENGINE_ARCHITECTURE.md`

### Development Tools
- **Test Script:** `test_fastapi_endpoints.py`
- **Migration Tester:** `test_migration.sh`
- **Docker Compose:** `docker-compose.test.yml`

### Support
- **Health Check:** `GET /health` for service diagnostics
- **Logs:** Enhanced logging with structured output
- **Metrics:** Standard HTTP metrics via FastAPI middleware
