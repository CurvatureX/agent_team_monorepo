# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a monorepo for building 24/7 AI Teams, containing multiple interconnected services that work together to create, manage, and execute AI-powered workflows.

### Core Services Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   API Gateway   │────▶│ Workflow Agent   │────▶│ Workflow Engine  │────▶│Workflow Scheduler│
│   (FastAPI)     │     │ (LangGraph/AI)   │     │ (Execution)      │     │ (Triggers)       │
└─────────────────┘     └──────────────────┘     └──────────────────┘     └──────────────────┘
        │                                                    │                         │
        └────────────────── Supabase ─────────────────────────────────────────────────┘
                    (Auth, State, Vector Store)
```

## Essential Development Commands

### Python Environment Setup
```bash
# Backend uses uv for dependency management
cd apps/backend
uv sync                          # Install all workspace dependencies

# Install service-specific dependencies
cd api-gateway && uv sync
cd workflow_agent && uv sync
cd workflow_engine && pip install -e .  # Legacy pip install
cd workflow_scheduler && uv sync
```

### Running Services
```bash
# Start all services with Docker Compose (recommended)
cd apps/backend
docker-compose up --build

# Start individual services for development
cd api-gateway && uv run uvicorn app.main:app --reload --port 8000
cd workflow_agent && python main.py
cd workflow_engine && python -m workflow_engine.main
cd workflow_scheduler && python main.py

# Start with observability stack (development)
docker-compose --profile development up
```

### Frontend Development
```bash
# Next.js frontend
cd apps/frontend/agent_team_web
npm run dev                      # Start development server
npm run build                    # Build for production
npm run lint                     # Run linter
```

### Testing
```bash
# Backend testing
cd apps/backend
pytest                           # Run all tests
pytest api-gateway/tests/        # Service-specific tests
uv run pytest --cov=app         # With coverage

# Frontend testing
cd apps/frontend/agent_team_web
npm test                         # Run tests
```

### Database Operations
```bash
# Supabase migrations
supabase db reset                # Reset local database
supabase db push                 # Push migrations
supabase functions deploy        # Deploy edge functions

# Workflow Engine database
cd workflow_engine
make db-init                     # Initialize database
make db-migrate MSG="description" # Create migration
alembic upgrade head            # Run migrations
```

### Build & Deployment
```bash
# Docker builds (for ECS deployment)
docker build --platform linux/amd64 -f api-gateway/Dockerfile -t api-gateway .
docker build --platform linux/amd64 -f workflow_agent/Dockerfile -t workflow-agent .
docker build --platform linux/amd64 -f workflow_engine/Dockerfile -t workflow-engine .

# Infrastructure deployment
cd infra
terraform init
terraform plan
terraform apply
```

## Service Architecture & Communication

### Service Ports
- **API Gateway**: 8000 (HTTP/REST) - Client-facing three-layer API
- **Workflow Agent**: 8001 (HTTP/REST) - AI workflow generation with LangGraph
- **Workflow Engine**: 8002 (HTTP/REST) - Node-based workflow execution
- **Workflow Scheduler**: 8003 (HTTP/REST) - Trigger management and scheduling

### Authentication Layers
- **Public API** (`/api/public/*`): No auth, rate-limited public endpoints
- **App API** (`/api/app/*`): Supabase OAuth + JWT for web/mobile apps
- **MCP API** (`/api/mcp/*`): API Key authentication for LLM clients

### Service Communication
- **Internal**: HTTP/REST between services (migrated from gRPC)
- **External**: API Gateway handles all client requests with proper auth
- **State**: Shared via Supabase with Row Level Security (RLS)
- **Cache**: Redis for performance optimization and session state

## Key Architectural Patterns

### Node-Based Workflow System
The core workflow execution uses a sophisticated node system:

- **Node Types**: 8 core types (TRIGGER, AI_AGENT, ACTION, EXTERNAL_ACTION, FLOW, HUMAN_LOOP, TOOL, MEMORY)
- **Node Specifications**: Centralized specs in `shared/node_specs/` with automatic validation
- **Factory Pattern**: Dynamic node creation with type registration
- **Execution Context**: Unified execution environment with parameter validation

### AI Integration Strategy
- **LangGraph**: Complex stateful AI workflows in Workflow Agent
- **RAG System**: Supabase pgvector for knowledge retrieval
- **Multi-Provider**: OpenAI, Anthropic API support
- **MCP Integration**: Model Context Protocol for tool discovery

### Data Management
- **Primary Database**: Supabase PostgreSQL with RLS for multi-tenant isolation
- **Vector Store**: pgvector for semantic search and RAG
- **Cache Layer**: Redis for sessions, rate limiting, and temporary state
- **File Storage**: Supabase Storage for file uploads and artifacts

## Development Environment Configuration

### Required Environment Variables
```bash
# Supabase (Primary Database & Auth)
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_SECRET_KEY="service-role-key"
SUPABASE_ANON_KEY="anon-key"

# AI Providers
OPENAI_API_KEY="sk-..."
ANTHROPIC_API_KEY="sk-ant-..."

# Cache & Infrastructure
REDIS_URL="redis://localhost:6379"

# Service URLs (for docker-compose networking)
WORKFLOW_AGENT_URL="http://workflow-agent:8001"
WORKFLOW_ENGINE_URL="http://workflow-engine:8002"
WORKFLOW_SCHEDULER_URL="http://workflow-scheduler:8003"
```

### Docker Compose Profiles
```bash
# Basic services only
docker-compose up

# Development tools (includes Redis Commander UI)
docker-compose --profile development up

# Full observability stack (Jaeger, OpenTelemetry)
docker-compose --profile observability up
```

## Testing Strategy

### Backend Testing Patterns
```bash
# API Gateway: Comprehensive three-layer testing
cd api-gateway && uv run pytest tests/ -v

# Workflow Agent: LangGraph state machine testing
cd workflow_agent && pytest tests/

# Workflow Engine: Node execution and validation testing
cd workflow_engine && pytest tests/

# Integration testing across services
pytest apps/backend/tests/
```

### Authentication Testing
- **Test Credentials**: Use real Supabase test accounts from `.env`
- **JWT Tokens**: Test authentication flows with valid tokens
- **RLS Testing**: Verify row-level security isolation

## Code Quality & Standards

### Python Standards
```bash
# Formatting and linting (configured in pyproject.toml)
uv run black . --line-length 100
uv run isort . --profile black
uv run flake8
uv run mypy

# Pre-commit hooks (API Gateway)
cd api-gateway && pre-commit run --all-files
```

### TypeScript Standards
```bash
# Frontend linting and formatting
cd apps/frontend/agent_team_web
npm run lint
npm run type-check
```

## Development Philosophy: "Fail Fast with Clear Feedback"

### Core Principle
**CRITICAL**: Never use mock responses or silent failures in production code. Always provide real errors with actionable feedback when functionality is not implemented or misconfigured.

### Why This Matters
- **Real Error Visibility**: Developers see actual configuration issues instead of false successes
- **Faster Debugging**: Clear error codes and solutions reduce investigation time
- **No False Positives**: Workflows fail when they should, preventing silent data corruption
- **Better User Experience**: Users get actionable guidance instead of confusion

### Implementation Standards

#### ✅ **DO: Structured Error Responses**
```python
return NodeExecutionResult(
    status=ExecutionStatus.ERROR,
    error_message="Clear description of what failed",
    error_details={
        "reason": "specific_error_code",
        "solution": "Exact steps to fix the issue",
        "documentation": "https://relevant-docs-link"
    },
    metadata={"node_type": "...", "context": "..."},
)
```

#### ❌ **DON'T: Mock Responses**
```python
# NEVER do this - creates false positives
if not api_key:
    return f"[Mock Response] Success: {message}"

# NEVER do this - silent failures confuse users
return {"status": "success", "message": "Mock execution completed"}
```

### Error Categories & Solutions

**OAuth Authentication Failures:**
```python
{
    "reason": "missing_oauth_token",
    "solution": "Connect [Service] account in integrations settings",
    "oauth_flow_url": "/integrations/connect/slack"
}
```

**Missing Configuration:**
```python
{
    "reason": "missing_environment_variable",
    "solution": "Set OPENAI_API_KEY environment variable",
    "required_env_vars": ["OPENAI_API_KEY"]
}
```

**Unimplemented Features:**
```python
{
    "reason": "feature_not_implemented",
    "solution": "Implement proper [feature] integration",
    "alternatives": ["use HTTP action", "use external action"]
}
```

### Applied Across All Services

- **Workflow Engine**: All node executors return proper errors instead of mock responses
- **API Gateway**: Authentication failures provide clear OAuth guidance
- **Workflow Agent**: AI provider errors include specific configuration steps
- **External Integrations**: OAuth token failures guide users to integration settings

**Remember**: If functionality isn't ready, return a clear error explaining what needs to be implemented - never pretend it works with mock data.

## Deployment & Infrastructure

### AWS ECS Deployment
- **Platform**: AWS ECS Fargate with service discovery
- **Networking**: VPC with private subnets, NAT gateways
- **Load Balancing**: Application Load Balancer with health checks
- **Security**: SecurityGroups, IAM roles, encrypted secrets

### Health Check Configuration
- **API Gateway**: `curl -f http://localhost:8000/api/v1/public/health` (120s start period)
- **Workflow Agent**: `curl -f http://localhost:8001/health` (120s start period)
- **Workflow Engine**: `curl -f http://localhost:8002/health` (90s start period)
- **Workflow Scheduler**: `curl -f http://localhost:8003/health` (60s start period)

### Critical Deployment Requirements
- **Platform**: Build with `--platform linux/amd64` for ECS
- **Dependencies**: All dependencies must be in requirements.txt/pyproject.toml
- **Import Structure**: Preserve Python package hierarchy in Docker images
- **Environment**: All secrets via AWS SSM Parameters

## Troubleshooting

### Common Development Issues
1. **Import Errors**: Ensure Docker preserves package structure with proper COPY commands
2. **Port Conflicts**: Services must use designated ports (8000-8003)
3. **Database Connection**: Check Supabase connection strings and SSL requirements
4. **Authentication**: Verify JWT tokens and RLS policies in Supabase

### Service Health Checks
```bash
# Check service status
curl http://localhost:8000/api/v1/public/health  # API Gateway
curl http://localhost:8001/health                 # Workflow Agent
curl http://localhost:8002/health                 # Workflow Engine
curl http://localhost:8003/health                 # Workflow Scheduler

# Check Redis
redis-cli ping

# Check database connectivity
psql $SUPABASE_DATABASE_URL -c "SELECT version();"
```

## Important Architectural Files

1. **Service Configurations**: Each service has detailed `CLAUDE.md` files
2. **Node Specifications**: `shared/node_specs/` - Centralized node type definitions
3. **API Documentation**: `apps/backend/api-gateway/docs/` - OpenAPI specifications
4. **Infrastructure**: `infra/` - Terraform configurations for AWS deployment
5. **Database Schema**: `supabase/migrations/` - Database structure and RLS policies

## OAuth Integration & External Service Checklist

### Adding New OAuth Providers (Slack, GitHub, Notion, etc.)

**1. GitHub Secrets Configuration**
- [ ] Add all OAuth secrets to GitHub repository secrets:
  - `{PROVIDER}_CLIENT_ID`
  - `{PROVIDER}_CLIENT_SECRET`
  - `{PROVIDER}_REDIRECT_URI`
  - `{PROVIDER}_SIGNING_SECRET` (if applicable)
- [ ] Verify secrets are accessible in GitHub Actions environment

**2. Terraform Infrastructure Updates**
- [ ] Add variables to `infra/variables.tf`:
  ```hcl
  variable "{provider}_client_id" {
    description = "{Provider} OAuth client ID"
    type        = string
    sensitive   = true
    default     = ""
  }
  ```
- [ ] Add SSM parameters to `infra/secrets.tf`:
  ```hcl
  resource "aws_ssm_parameter" "{provider}_client_id" {
    name  = "/${local.name_prefix}/{provider}/client-id"
    type  = "SecureString"
    value = var.{provider}_client_id
  }
  ```
- [ ] Add environment variables to **ALL** relevant ECS task definitions in `infra/ecs.tf`:
  - API Gateway (if generating install links)
  - Workflow Scheduler (if handling OAuth callbacks)
  - Any other service that needs OAuth credentials

**3. GitHub Actions Workflow Updates**
- [ ] Add environment variables to `.github/workflows/deploy.yml`:
  ```yaml
  TF_VAR_{provider}_client_id: ${{ secrets.{PROVIDER}_CLIENT_ID }}
  TF_VAR_{provider}_client_secret: ${{ secrets.{PROVIDER}_CLIENT_SECRET }}
  ```
- [ ] Add to both `Terraform Plan` and `Terraform Apply` steps

**4. Service Configuration Updates**
- [ ] Add OAuth settings to service configuration files (`core/config.py`)
- [ ] Update service-specific environment variable handling
- [ ] Ensure proper error handling for missing OAuth credentials

**5. Deployment & Testing Checklist**
- [ ] Deploy infrastructure changes through proper CI/CD (not manual AWS CLI)
- [ ] Verify SSM parameters are created with correct values
- [ ] Check ECS task definitions include all required environment variables
- [ ] Test OAuth install links generate with correct client IDs
- [ ] Test OAuth callback flow completes successfully
- [ ] Verify OAuth tokens are stored in database correctly

### Common OAuth Integration Pitfalls

❌ **Don't Do This:**
- Manually updating ECS task definitions via AWS CLI
- Adding secrets to only one service when multiple services need them
- Forgetting to add environment variables to GitHub Actions workflow
- Using placeholder values in terraform.tfvars for sensitive data

✅ **Do This:**
- Always use GitHub Secrets → GitHub Actions → Terraform → SSM → ECS flow
- Add OAuth environment variables to ALL services that need them
- Test the complete OAuth flow end-to-end after deployment
- Use descriptive variable names and consistent naming conventions

### Debugging OAuth Issues

**When OAuth fails with "invalid_client_id" or similar:**
1. Check GitHub Secrets are properly configured
2. Verify GitHub Actions workflow includes the new TF_VAR mappings
3. Confirm SSM parameters exist and have correct values:
   ```bash
   aws ssm get-parameter --name "/agent-prod/{provider}/client-id" --with-decryption
   ```
4. Check ECS task definition includes the environment variable:
   ```bash
   aws ecs describe-task-definition --task-definition {service}:latest
   ```
5. Verify service logs show environment variables are loaded (not empty)

### Service-Specific OAuth Requirements

- **API Gateway**: Needs OAuth credentials for generating install links (`/integrations/install-links`)
- **Workflow Scheduler**: Needs OAuth credentials for handling callbacks (`/auth/{provider}/callback`)
- **Workflow Agent**: May need credentials for AI-driven OAuth operations
- **Workflow Engine**: Usually doesn't need OAuth credentials directly

## Migration History

### Major Architectural Changes
- **gRPC → FastAPI Migration**: All services now use HTTP/REST for consistency
- **Three-Layer API Architecture**: Public/App/MCP authentication layers
- **Node Specification System**: Centralized validation with automatic type conversion
- **Workflow Scheduler Addition**: Dedicated trigger management service
- **OAuth Integration Standardization**: Comprehensive checklist for external service integrations

Remember: Each service has its own detailed `CLAUDE.md` file with service-specific guidance. Always check the service-specific documentation for detailed implementation patterns and best practices.
