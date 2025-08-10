# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a monorepo for building 24/7 AI Teams, containing multiple interconnected services that work together to create, manage, and execute AI-powered workflows.

### Core Services Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   API Gateway   │────▶│ Workflow Agent   │────▶│ Workflow Engine  │
│   (FastAPI)     │     │ (LangGraph/AI)   │     │ (Execution)      │
└─────────────────┘     └──────────────────┘     └──────────────────┘
        │                                                    │
        └────────────────── Supabase ────────────────────────┘
                    (Auth, State, Vector Store)
```

## Global Development Rules

### 1. Service Communication
- **Internal Services**: Use HTTP/REST between services (migrated from gRPC)
- **External API**: FastAPI-based API Gateway handles all client requests
- **Shared Models**: Use `shared/models/` for cross-service data structures

### 2. State Management
- **Session State**: Managed in Supabase with service-specific tables
- **Workflow State**: Persisted across service boundaries using session IDs
- **Cache**: Redis for temporary state and performance optimization

### 3. Error Handling
- **Service Errors**: Return structured error responses with correlation IDs
- **Graceful Degradation**: Services should handle downstream failures
- **Logging**: Use structured JSON logging with service context

### 4. Authentication & Security
- **Auth Flow**: Supabase Auth via API Gateway
- **Service-to-Service**: Internal services trust API Gateway authentication
- **Secrets**: Use environment variables, never commit credentials

### 5. Development Workflow
- **Branch Strategy**: Feature branches → main → deployment
- **Testing**: Unit tests required for business logic, integration tests for APIs
- **Documentation**: Update service-specific CLAUDE.md for significant changes

## Service-Specific Guides

Each service has its own CLAUDE.md with detailed information:

- **[API Gateway](./apps/backend/api-gateway/CLAUDE.md)**: Client-facing API, authentication, routing
- **[Workflow Agent](./apps/backend/workflow_agent/CLAUDE.md)**: AI consultant for workflow generation
- **[Workflow Engine](./apps/backend/workflow_engine/README.md)**: Workflow execution and orchestration

## Common Development Commands

### Environment Setup
```bash
# Copy environment template
cp apps/backend/env.example apps/backend/.env

# Install dependencies (Python 3.11+ required)
cd apps/backend/<service>
uv pip install --system -e .
```

### Running Services Locally
```bash
# Start all services
cd apps/backend
docker-compose up

# Or run individually
cd apps/backend/api-gateway && python main.py
cd apps/backend/workflow_agent && python main.py
cd apps/backend/workflow_engine && python main.py
```

### Testing
```bash
# Run all tests
pytest apps/backend/

# Run service-specific tests
pytest apps/backend/workflow_agent/tests/
```

## Architectural Decisions

### 1. Monorepo Structure
- **Shared Code**: Common models and utilities in `shared/`
- **Service Isolation**: Each service can be deployed independently
- **Unified CI/CD**: Single deployment pipeline with service-level controls

### 2. AI Integration Pattern
- **LangGraph**: For complex stateful AI workflows (Workflow Agent)
- **Direct LLM**: For simpler transformations (Workflow Engine)
- **RAG**: Supabase pgvector for knowledge retrieval

### 3. Data Flow
- **Request Flow**: Client → API Gateway → Workflow Agent → Workflow Engine
- **State Flow**: Services communicate through shared database state
- **Event Flow**: Async operations use message passing (future: event bus)

## Migration Notes

### From gRPC to FastAPI (Completed)
- All services now use FastAPI for consistency
- Protobuf definitions kept for data validation
- See migration guides in service-specific docs

### Deployment (AWS ECS)
- Services deployed as ECS tasks
- Service discovery via AWS Cloud Map
- Infrastructure as Code in `infra/`

## Key Technologies

- **Backend**: Python 3.11+, FastAPI, LangGraph, LangChain
- **Database**: PostgreSQL (via Supabase), Redis
- **AI/ML**: OpenAI, Anthropic, pgvector for embeddings
- **Infrastructure**: Docker, AWS ECS, Terraform
- **Frontend**: Next.js, React (in `frontend/`)

## Important Files to Review

1. **Workflow DSL Specification**: `apps/backend/workflow_agent/dsl/README.md`
2. **API Documentation**: `apps/backend/api-gateway/docs/API_DOC.md`
3. **Node Types**: `docs/tech-design/node_spec.md`
4. **Database Schema**: `apps/backend/workflow_engine/database/schema.sql`

## Getting Help

- **Architecture Questions**: Review `docs/tech-design/`
- **Deployment Issues**: Check `infra/README.md`
- **Service-Specific**: Consult individual service CLAUDE.md files

Remember: When in doubt, check the service-specific CLAUDE.md for detailed guidance.

## Backend Development Guidelines

- **Python Project Management**: Use `uv` and `.venv` to manage Python projects

## IMPORTANT: Sound Notification

After finishing responding to my request or running a command, run this command to notify me by sound:

```bash
say "I'm done"
```