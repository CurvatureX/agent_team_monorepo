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

## Development Philosophy: "Fail Fast with Clear Feedback"

### Core Principle
**Never use mock responses or silent failures in production code.** Always provide real errors with actionable feedback when functionality is not implemented or misconfigured.

### Implementation Guidelines

#### ✅ **DO: Proper Error Handling**
```python
# Return structured errors with clear solutions
return NodeExecutionResult(
    status=ExecutionStatus.ERROR,
    error_message="OpenAI API key not found",
    error_details={
        "reason": "missing_api_key",
        "solution": "Set OPENAI_API_KEY environment variable",
        "documentation": "https://platform.openai.com/api-keys"
    },
    metadata={"node_type": "ai_agent", "provider": "openai"},
)
```

#### ❌ **DON'T: Mock Responses**
```python
# NEVER do this - creates false positives
if not api_key:
    return f"[Mock Response] API key missing: {user_message}"

# NEVER do this - silent failures confuse users
return {"status": "success", "message": "Mock execution completed"}
```

### Error Response Standards

**All errors must include:**
1. **Clear error message**: What specifically failed
2. **Reason code**: Machine-readable error type
3. **Actionable solution**: Exact steps to fix the issue
4. **Context metadata**: Node type, operation, relevant IDs

**Example patterns:**
```python
# OAuth authentication failure
{
    "reason": "missing_oauth_token",
    "solution": "Connect Slack account in integrations settings",
    "oauth_provider": "slack"
}

# Missing environment variable
{
    "reason": "missing_configuration",
    "solution": "Set ANTHROPIC_API_KEY environment variable",
    "required_env_vars": ["ANTHROPIC_API_KEY"]
}

# Unsupported feature
{
    "reason": "feature_not_implemented",
    "solution": "Implement proper MCP tool integration",
    "alternatives": ["use HTTP action", "use external action"]
}
```

### Benefits of This Approach

1. **Real Error Visibility**: Developers see actual configuration issues
2. **Faster Debugging**: Clear error codes and solutions reduce investigation time
3. **No False Positives**: Workflows fail when they should, preventing silent data corruption
4. **Better User Experience**: Users get actionable guidance instead of confusion
5. **Maintainable Code**: Less mock code to maintain and debug

### Applied Across Services

- **Workflow Engine**: All node executors return proper errors instead of mock responses
- **API Gateway**: Authentication failures provide clear OAuth guidance
- **Workflow Agent**: AI provider errors include specific configuration steps
- **External Integrations**: OAuth token failures guide users to integration settings

**Remember**: If functionality isn't implemented, return a clear error explaining what needs to be built - never pretend it works with mock data.

## Workflow Execution Architecture

### Workflow Data Models (Based on new_workflow_spec.md)

**Core Components**:
1. **Workflow**: Metadata + Nodes + Connections + Triggers
2. **Node**: id, name, type, subtype, configurations, input/output params, attached_nodes (AI_AGENT only)
3. **Connection**: Defines directed data flow between nodes with optional conversion functions
4. **WorkflowExecution**: Complete execution state with node-level tracking

**Key Execution Structures**:
- **WorkflowExecution**: Tracks overall workflow execution state, triggers, node executions, errors, resource usage
- **NodeExecution**: Individual node execution details with status, timing, I/O data, execution details
- **NodeExecutionDetails**: Type-specific execution info (AI model responses, API calls, tool results, HIL interactions)

### Execution States & Flow

**ExecutionStatus** (Workflow-level):
```python
NEW → RUNNING → SUCCESS/ERROR/CANCELED
              ↓
         PAUSED (HIL) → WAITING_FOR_HUMAN → RUNNING
              ↓
         TIMEOUT
```

**NodeExecutionStatus**:
```python
pending → running → completed/failed
              ↓
        waiting_input (HIL) → running → completed
              ↓
        retrying → running
```

### Real-time Execution Updates

**ExecutionUpdateEvent** (WebSocket):
- `execution_started`: Workflow begins
- `node_started`: Node execution starts
- `node_output_update`: Streaming output updates
- `node_completed`/`node_failed`: Node finishes
- `execution_paused`: HIL pause triggered
- `user_input_required`: Awaiting human response
- `execution_resumed`: HIL resume after response
- `execution_completed`/`execution_failed`: Workflow ends

### Human-in-the-Loop (HIL) Execution Pattern

**5-Phase HIL Flow**:

1. **HIL Node Startup**:
   - Validate configurations (interaction_type, channel_type, timeout)
   - Extract user context from trigger/execution
   - Create `hil_interactions` record
   - Create `workflow_execution_pauses` record
   - Return pause signal with `_hil_wait: true`

2. **Workflow Pause**:
   - Persist complete execution state to database
   - Start timeout monitoring (background service)
   - Send interaction request via configured channel
   - Set workflow status to `PAUSED`

3. **Human Response Processing**:
   - Receive webhook response from Slack/Email/etc.
   - AI classification (Gemini 8-factor analysis):
     - `relevant` (score ≥ 0.7): Process response
     - `filtered` (score ≤ 0.3): Ignore
     - `uncertain` (0.3 < score < 0.7): Log only
   - Update `hil_interactions` status to `completed`

4. **Workflow Resume**:
   - Update `workflow_execution_pauses` to `resumed`
   - Restore execution state from database
   - HIL node outputs human response data
   - Workflow continues to next nodes

5. **Timeout Handling**:
   - Warning notification (15min before timeout)
   - Timeout actions: `fail`, `continue`, `default_response`
   - Update interaction status to `timeout`

**HIL Configuration Parameters**:
```python
{
    "interaction_type": "approval|input|selection|review",
    "channel_type": "slack|email|webhook|in_app",
    "timeout_seconds": 60-86400,  # 60s to 24h
    "timeout_action": "fail|continue|default_response",
    "approval_options": [...],     # for approval type
    "input_fields": [...],         # for input type
    "selection_options": [...]     # for selection type
}
```

### AI_AGENT Attached Nodes Pattern

Attached TOOL and MEMORY nodes enhance AI_AGENT execution:

**Execution Sequence**:
1. **Pre-execution**:
   - Load memory context from MEMORY nodes
   - Discover and register tools from TOOL nodes (MCP)
   - Enhance AI prompt with context and tools

2. **AI Execution**:
   - Generate response with augmented capabilities
   - AI can invoke registered tools internally

3. **Post-execution**:
   - Store conversation (user msg + AI response) to MEMORY nodes
   - Persist tool invocation results

**Key Points**:
- Attached nodes don't appear in workflow execution sequence
- No separate NodeExecution records for attached nodes
- Managed entirely within AI_AGENT node context
- Results stored in `attached_executions` field

### Error Handling & Retry

**Structured Error Response**:
```python
{
    "error_code": "specific_error_identifier",
    "error_message": "Human-readable description",
    "error_details": {...},
    "is_retryable": True/False,
    "timestamp": epoch_ms
}
```

**Retry Mechanism**:
- `retry_count` and `max_retries` tracked per node
- `retrying` status during retry attempts
- Only retryable errors trigger automatic retry
- Manual retry available via API for failed nodes

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
# Test HTTP service endpoints
python tests/integration/test_http_service.py

# Test end-to-end workflow execution
python tests/integration/test_workflow_execution.py

# Test HIL workflow patterns
python tests/integration/test_hil_workflow.py
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

## Documentation & Docusaurus

### Docusaurus MDX Escaping Rules

When writing technical documentation in Docusaurus (MDX format), comparison operators must be escaped to prevent MDX from interpreting them as JSX/HTML tags.

**Common Issue**: MDX treats `<`, `>`, `<=`, `>=` as HTML tag syntax, causing compilation errors like:
```
Error: MDX compilation failed for file "/path/to/file.md"
Cause: Unexpected character `=` (U+003D) before name, expected a character that can start a name
```

**Root Cause**: MDX parser sees `<=` or `>=` and attempts to parse it as an HTML/JSX tag opening, then fails when it encounters unexpected characters.

**Solution**: Escape comparison operators with backslashes in prose text:

```markdown
✅ Correct:
- `relevant` (相关, score \>= 0.7): Process response
- `filtered` (无关, score \<= 0.3): Ignore
- `uncertain` (不确定, 0.3 \< score \< 0.7): Log only

❌ Incorrect (causes build failures):
- score >= 0.7
- score <= 0.3
- 0.3 < score < 0.7
```

**When to Escape**:
- Comparison operators in prose text (lists, paragraphs, headings)
- Operators in markdown outside of code blocks
- Mathematical expressions in documentation

**When NOT to Escape**:
- Inside triple-backtick code fences (```python, ```javascript, etc.)
- Inside inline code: `` `if score >= 0.7:` ``
- In actual JSX/HTML elements (intentional tags)

**Testing Locally**:
```bash
cd apps/internal-tools/docusaurus-doc
npm run build  # Builds static site, catches MDX errors
npm run serve  # Preview production build
```

**Common Files Affected**:
- Technical specifications with comparison operators
- API documentation with threshold values
- Algorithm descriptions with conditional logic

## Workflow Metadata & Statistics

### WorkflowMetadata Structure
```python
{
    "id": "uuid",
    "name": "Workflow name",
    "icon_url": "https://...",
    "description": "Workflow purpose",
    "deployment_status": "PENDING|DEPLOYED|FAILED|UNDEPLOYED",
    "last_execution_status": "NEW|RUNNING|SUCCESS|ERROR|...",
    "last_execution_time": 1234567890,  # epoch ms
    "tags": ["automation", "ai"],
    "created_time": 1234567890,
    "parent_workflow": "uuid",  # template source
    "statistics": {
        "total_runs": 100,
        "average_duration_ms": 5000,
        "total_credits": 1000,
        "last_success_time": 1234567890
    },
    "version": "1.0",
    "created_by": "user_id",
    "updated_by": "user_id"
}
```

### Connection & Data Flow
```python
{
    "id": "conn_id",
    "from_node": "source_node_id",
    "to_node": "target_node_id",
    "output_key": "result|true|false",  # default: "result"
    "conversion_function": "optional_transform_code"
}
```

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
