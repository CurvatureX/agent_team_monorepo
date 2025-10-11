---
id: tech-design-intro
title: Technical Design Documentation
sidebar_label: Tech Design Overview
sidebar_position: 1
---

# Technical Design Documentation

## Overview

This directory contains comprehensive technical design documentation for the **24/7 AI Teams** platform - a monorepo-based system for building, deploying, and managing automated AI-powered workflows.

### What is 24/7 AI Teams?

The platform enables users to create sophisticated automated workflows that combine AI capabilities, external service integrations, and human-in-the-loop decision points. Think of it as a visual programming environment where AI agents can collaborate with tools, memory systems, and human oversight to accomplish complex tasks.

## System Architecture

The platform follows a microservices architecture with four core backend services communicating via HTTP/REST:

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   API Gateway   │────▶│ Workflow Agent   │────▶│ Workflow Engine  │────▶│Workflow Scheduler│
│   (FastAPI)     │     │ (LangGraph/AI)   │     │ (Execution)      │     │ (Triggers)       │
│   Port: 8000    │     │   Port: 8001     │     │   Port: 8002     │     │   Port: 8003     │
└─────────────────┘     └──────────────────┘     └──────────────────┘     └──────────────────┘
        │                        │                        │                         │
        └────────────────────── Supabase ─────────────────────────────────────────────┘
                          (Auth, State, Vector Store, Row Level Security)
```

### Core Services

1. **API Gateway** (Port 8000)
   - Three-layer API architecture: Public, App (OAuth), MCP (API Key)
   - Client-facing HTTP/REST endpoints with proper authentication
   - Real-time SSE (Server-Sent Events) for workflow execution updates
   - Row-Level Security (RLS) integration with Supabase

2. **Workflow Agent** (Port 8001)
   - LangGraph-based AI workflow generation
   - Conversational interface for workflow creation
   - Gap analysis and capability negotiation
   - Template-based workflow modification
   - Automatic debugging and refinement

3. **Workflow Engine** (Port 8002)
   - Node-based workflow execution engine
   - 8 core node types with flexible subtypes
   - Human-in-the-Loop (HIL) support with pause/resume
   - Real-time execution tracking and logging
   - Comprehensive error handling and retry mechanisms

4. **Workflow Scheduler** (Port 8003)
   - Trigger management (Cron, Manual, Webhook, GitHub, Slack, Email)
   - Deployment lifecycle management
   - Distributed locking for concurrent execution prevention
   - Real-time trigger monitoring

### Frontend Applications

- **Agent Team Web** (Next.js): Main web interface for workflow creation and management
- **Internal Tools**: Docusaurus-based documentation site

## Key Architectural Patterns

### Node-Based Workflow System

The workflow engine uses a sophisticated node system with **8 core node types**:

1. **TRIGGER**: Workflow initiation (Manual, Cron, Webhook, GitHub, Slack, Email)
2. **AI_AGENT**: Provider-based AI nodes (Gemini, OpenAI, Claude) with custom prompts
3. **ACTION**: System operations (HTTP requests, code execution, data transformation)
4. **EXTERNAL_ACTION**: External service integrations (Slack, GitHub, Notion, etc.)
5. **FLOW**: Control flow (If, Loop, Filter, Merge, Wait)
6. **HUMAN_IN_THE_LOOP**: Human interaction points with AI-powered response classification
7. **TOOL**: MCP (Model Context Protocol) tool integrations
8. **MEMORY**: Conversation and knowledge storage

#### Node Structure

Each node contains:
- **Configurations**: Node-specific parameters defining behavior
- **Input/Output Params**: Runtime data flow parameters
- **Attached Nodes**: (AI_AGENT only) Tool and Memory nodes executed in the same context
- **Position**: Canvas coordinates for UI visualization

### AI Integration Revolution

The system moved from hardcoded AI roles to **provider-based architecture**:

**Old Approach** ❌:
```python
AI_ROUTER_AGENT
AI_TASK_ANALYZER
AI_DATA_INTEGRATOR
```

**New Approach** ✅:
```python
GEMINI_NODE      # Google Gemini with custom system prompt
OPENAI_NODE      # OpenAI GPT with custom system prompt
CLAUDE_NODE      # Anthropic Claude with custom system prompt
```

Functionality is now defined entirely through system prompts, enabling unlimited AI capabilities without code changes.

### Authentication & Security

**Three-Layer API Architecture**:

1. **Public API** (`/api/v1/public/*`): No auth, rate-limited, health checks
2. **App API** (`/api/v1/app/*`): Supabase OAuth + JWT + Row Level Security
3. **MCP API** (`/api/v1/mcp/*`): API Key authentication for LLM clients

**Security Features**:
- Row-Level Security (RLS) for multi-tenant data isolation
- JWT token validation with Supabase
- API key scopes for fine-grained permissions
- Redis-based rate limiting

### Data Management

- **Primary Database**: Supabase PostgreSQL with RLS
- **Vector Store**: pgvector for RAG and semantic search
- **Cache Layer**: Redis for sessions, rate limiting, temporary state
- **File Storage**: Supabase Storage for artifacts

## Technical Documents by Category

### Core Service Architecture

#### API Gateway
- **[API Gateway Architecture](./api-gateway-architecture.md)** - Three-layer API design (Public/App/MCP), authentication middleware, rate limiting, SSE streaming, RLS integration

#### Workflow Agent
- **[Workflow Agent Architecture](./workflow-agent-architecture.md)** - LangGraph state machine, conversational workflow generation, gap analysis, negotiation, debugging
- **[Workflow Agent API](./workflow-agent-api-doc.md)** - API specification and integration guide

#### Workflow Engine
- **[Workflow Engine Architecture](./workflow-engine-architecure.md)** - Node execution engine, pause/resume system, provider-based AI agents, HIL integration, execution tracking
- **[Integration Tests](./workflow-engine-integration-tests-focused.md)** - Comprehensive test strategy and scenarios

#### Workflow Scheduler
- **[Workflow Scheduler Architecture](./workflow-scheduler-architecture.md)** - Trigger management, deployment lifecycle, distributed locking, GitHub/Slack integration

### Data & Specifications

#### Workflow Specifications
- **[Workflow Data Structure](./new_workflow_spec.md)** - Complete workflow data models, execution states, node definitions, API interfaces
- **[Node Specification System](./node_spec.md)** - Centralized node specs, parameter validation, input/output ports, data formats
- **[Node Structure](./node-structure.md)** - Detailed node anatomy and configuration patterns
- **[Node Communication Protocol](./node-communication-protocol.md)** - Standardized inter-node data exchange format

#### Database Design
- **[Database Design](./db-design.md)** - Complete schema, tables, relationships, RLS policies
- **[Unified Log Table](./unified_log_table_design.md)** - Centralized logging architecture
- **[Execution Log API](./execution_log_api_design.md)** - API for querying execution logs

### Feature Systems

#### Human-in-the-Loop (HIL)
- **[HIL Node System](./human-in-loop-node-system.md)** - Complete HIL architecture, AI response classification, multi-channel support
- **[HIL Data Formats](./hil-node-data-formats.md)** - Request/response schemas for HIL interactions

#### Integrations
- **[Slack App Integration](./slack-app-integration.md)** - Slack OAuth flow, event handling, messaging
- **[GitHub App Integration](./github-app-integration.md)** - GitHub App setup, webhook processing, code access
- **[Manual Trigger System](./manual-trigger-invocation-system.md)** - User-initiated workflow execution

#### Supporting Systems
- **[Data Mapping System](./data_mapping_system.md)** - Node-to-node data transformation
- **[Distributed Tracing](./distributed-tracing-system.md)** - OpenTelemetry integration for observability
- **[Monitoring Guide](./monitoring-guide.md)** - System health monitoring and alerting

### Migration & Development

- **[gRPC to FastAPI Migration](./grpc-to-fastapi-migration.md)** - Service communication architecture evolution
- **[Frontend Integration Examples](./frontend_integration_examples.md)** - UI integration patterns
- **[MCP Node Knowledge Server](./mcp-node-knowledge-server.md)** - Model Context Protocol integration

### Legacy/Reference
- **[MVP Workflow Data Structure](./MVP-Workflow-Data-Structure-Definition.md)** - Original workflow specification (superseded by new_workflow_spec.md)

## Development Workflow

### Setting Up Development Environment

```bash
# Backend services (Python with uv)
cd apps/backend
uv sync

# Individual services
cd api-gateway && uv sync
cd workflow_agent && uv sync
cd workflow_engine && pip install -e .
cd workflow_scheduler && uv sync

# Frontend
cd apps/frontend/agent_team_web
npm install
npm run dev
```

### Running Services

```bash
# All services with Docker Compose (recommended)
cd apps/backend
docker-compose up --build

# Individual services for development
cd api-gateway && uv run uvicorn app.main:app --reload --port 8000
cd workflow_agent && python main.py
cd workflow_engine && python -m workflow_engine.main
cd workflow_scheduler && python main.py
```

### Testing

```bash
# Backend testing
cd apps/backend
pytest                           # All tests
pytest api-gateway/tests/        # Service-specific
uv run pytest --cov=app         # With coverage

# Frontend testing
cd apps/frontend/agent_team_web
npm test
```

## Key Concepts & Terminology

### Workflow Execution Model

**Execution States**:
- `NEW`: Initial state
- `RUNNING`: Active execution
- `PAUSED`: Halted (Human-in-the-Loop)
- `SUCCESS`: Completed successfully
- `ERROR`: Failed execution
- `WAITING_FOR_HUMAN`: Awaiting HIL response

**Node-Level States**:
- `pending`: Waiting to execute
- `running`: Currently executing
- `waiting_input`: Awaiting user input (HIL)
- `completed`: Successfully finished
- `failed`: Execution error

### Attached Nodes Pattern (AI_AGENT)

AI_AGENT nodes can attach TOOL and MEMORY nodes for enhanced capabilities:

1. **Memory Context Loading** (pre-execution): Load conversation history
2. **Tool Discovery** (pre-execution): Register MCP tools with AI provider
3. **AI Response Generation**: Execute with enhanced context and tools
4. **Conversation Storage** (post-execution): Persist interaction to memory

### Human-in-the-Loop (HIL)

HIL nodes enable workflows to pause and await human decisions:

1. **Pause \& Wait**: Workflow pauses, state persisted to database
2. **Multi-channel Interaction**: Slack, Email, Webhook, In-App notifications
3. **AI Response Classification**: Gemini-powered 8-factor analysis determines response relevance
4. **Timeout Management**: Configurable timeouts (60s-24h) with customizable actions
5. **Resume Execution**: Workflow resumes with human response as node output

## Development Philosophy

### "Fail Fast with Clear Feedback"

**CRITICAL**: Never use mock responses or silent failures in production code. Always provide real errors with actionable feedback when functionality is not implemented or misconfigured.

**DO ✅**: Structured error responses with clear solutions
```python
return NodeExecutionResult(
    status=ExecutionStatus.ERROR,
    error_message="Slack OAuth token not configured",
    error_details={
        "reason": "missing_oauth_token",
        "solution": "Connect Slack account in integrations settings",
        "oauth_flow_url": "/integrations/connect/slack"
    }
)
```

**DON'T ❌**: Mock responses that hide issues
```python
# NEVER do this - creates false positives
if not api_key:
    return f"[Mock Response] Success: {message}"
```

## Deployment Architecture

### AWS ECS Deployment

- **Platform**: AWS ECS Fargate with service discovery
- **Networking**: VPC with private subnets, NAT gateways
- **Load Balancing**: Application Load Balancer with health checks
- **Security**: Security Groups, IAM roles, encrypted secrets (AWS SSM)

### Health Check Configuration

```bash
# API Gateway
curl http://localhost:8000/api/v1/public/health  # 120s start period

# Workflow Agent
curl http://localhost:8001/health  # 120s start period

# Workflow Engine
curl http://localhost:8002/health  # 90s start period

# Workflow Scheduler
curl http://localhost:8003/health  # 60s start period
```

### Critical Deployment Requirements

- **Platform**: Build with `--platform linux/amd64` for ECS
- **Dependencies**: All dependencies in requirements.txt/pyproject.toml
- **Import Structure**: Preserve Python package hierarchy in Docker images
- **Environment**: All secrets via AWS SSM Parameters

## Common Development Tasks

### Adding OAuth Integrations

When adding new OAuth providers (Slack, GitHub, Notion, etc.):

1. **GitHub Secrets**: Add `{PROVIDER}_CLIENT_ID`, `{PROVIDER}_CLIENT_SECRET`, etc.
2. **Terraform**: Add variables to `infra/variables.tf` and SSM parameters to `infra/secrets.tf`
3. **GitHub Actions**: Add environment variables to `.github/workflows/deploy.yml`
4. **Service Config**: Update all relevant ECS task definitions in `infra/ecs.tf`
5. **Testing**: Test complete OAuth flow end-to-end after deployment

**Checklist available in**: [CLAUDE.md OAuth Integration section](../../apps/backend/CLAUDE.md#oauth-integration--external-service-checklist)

### Writing Documentation (Docusaurus/MDX)

When writing technical documentation in MDX format, **escape comparison operators**:

```markdown
✅ Correct:
- score \>= 0.7
- score \<= 0.3

❌ Incorrect (causes build failures):
- score >= 0.7
- score <= 0.3
```

Build locally before committing:
```bash
cd apps/internal-tools/docusaurus-doc
npm run build
```

## Troubleshooting

### Service Health Checks

```bash
# Check all services
curl http://localhost:8000/api/v1/public/health  # API Gateway
curl http://localhost:8001/health                 # Workflow Agent
curl http://localhost:8002/health                 # Workflow Engine
curl http://localhost:8003/health                 # Workflow Scheduler

# Check Redis
redis-cli ping

# Check database
psql $SUPABASE_DATABASE_URL -c "SELECT version();"
```

### Common Issues

1. **Import Errors**: Ensure Docker preserves package structure with proper COPY commands
2. **Port Conflicts**: Services must use designated ports (8000-8003)
3. **Database Connection**: Check Supabase connection strings and SSL requirements
4. **Authentication**: Verify JWT tokens and RLS policies in Supabase

## Migration History

### Major Architectural Changes

- **gRPC → FastAPI Migration**: All services now use HTTP/REST for consistency
- **Three-Layer API Architecture**: Public/App/MCP authentication layers
- **Node Specification System**: Centralized validation with automatic type conversion
- **Provider-Based AI Agents**: From hardcoded roles to flexible prompt-driven nodes
- **Workflow Scheduler Addition**: Dedicated trigger management service

## Documentation Navigation

### Start Here
- **New to the project?** Read this overview, then [Workflow Data Structure](./new_workflow_spec.md)
- **Setting up API integration?** See [API Gateway Architecture](./api-gateway-architecture.md)
- **Building workflows?** Check [Node Specification System](./node_spec.md)
- **Adding OAuth providers?** Follow [OAuth Integration Checklist](../../apps/backend/CLAUDE.md#oauth-integration--external-service-checklist)

### Service-Specific Deep Dives
- Each service has detailed `CLAUDE.md` files with service-specific patterns
- Check `apps/backend/{service}/CLAUDE.md` for implementation details

### Database & Data Models
- Start with [Database Design](./db-design.md) for schema overview
- See [Workflow Data Structure](./new_workflow_spec.md) for complete data models
- Reference [Node Specification System](./node_spec.md) for node validation rules

### Integration Guides
- [Slack Integration](./slack-app-integration.md) - Slack OAuth and event handling
- [GitHub Integration](./github-app-integration.md) - GitHub App setup and webhooks
- [HIL System](./human-in-loop-node-system.md) - Human-in-the-Loop architecture

## Contributing

When adding new features or making architectural changes:

1. **Update Technical Design Docs**: Document new systems, data structures, and APIs
2. **Follow Existing Patterns**: Maintain consistency with current architecture
3. **Add Tests**: Comprehensive unit and integration tests
4. **Update CLAUDE.md**: Service-specific development guidance
5. **Fail Fast**: Never use mock responses - always return clear, actionable errors

---

**Documentation Version**: 2.0
**Last Updated**: 2025-01-28
**Maintained By**: Engineering Team
**Related**: See individual service `CLAUDE.md` files for service-specific guidance
