# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Package Management with uv
This project uses `uv` for Python package management:

```bash
# Install dependencies
uv sync

# Start development server with auto-reload
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker Development
This project uses a **centralized docker-compose.yml** in the parent backend directory:

```bash
# Navigate to backend root for centralized orchestration
cd ../

# Start full stack (API Gateway + Workflow Agent + Workflow Engine + Infrastructure)
docker-compose up --build

# Start with development tools (includes Redis Commander UI)
docker-compose --profile development up --build

# Start only local cache (services use Supabase for data)
docker-compose up redis

# Build individual service images
docker build -f api-gateway/Dockerfile -t api-gateway .
docker build -f workflow_agent/Dockerfile -t workflow-agent .
docker build -f workflow_engine/Dockerfile -t workflow-engine .

# Build for AWS ECS (AMD64 platform)
docker build --platform linux/amd64 -f api-gateway/Dockerfile -t api-gateway .
```

**Key Benefits of Centralized Approach:**
- ✅ All services share the same Redis cache and connect to Supabase
- ✅ Proper service discovery and networking
- ✅ Matches production AWS ECS deployment architecture
- ✅ Simplified environment management with single .env file
- ✅ Built-in Redis Commander UI for development
- ✅ No local PostgreSQL - uses Supabase directly for data persistence

### Development Commands (Manual)
Since the helper script doesn't exist yet, use these commands directly:

```bash
# Install dependencies
uv sync

# Start development server with auto-reload
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run tests
uv run pytest tests/ -v

# Format code
uv run black app/ tests/
uv run isort app/ tests/

# Run linting
uv run flake8 app/ tests/
# Note: mypy is configured in pyproject.toml but not in dev dependencies

# Run all tests with coverage
uv run pytest tests/ --cov=app
```

### Production Startup
```bash
# Use the startup script (checks env vars, installs deps, starts server)
./start.sh
```

## Architecture Overview

### Three-Layer API Architecture
This FastAPI application implements a **three-layer API architecture** with distinct authentication and authorization patterns:

1. **Public API** (`/api/public/*`) - No authentication required, rate-limited public endpoints
2. **App API** (`/api/app/*`) - Supabase OAuth + JWT authentication for web/mobile applications
3. **MCP API** (`/api/mcp/*`) - API Key authentication with scopes for LLM clients

### Core Components
1. **FastAPI Application** (`app/main.py`) - Factory pattern with lifespan events, middleware stack
2. **Three-Layer API Structure**:
   - `app/api/public/` - Health checks, service information
   - `app/api/app/` - Sessions, chat, workflows (requires Supabase auth)
   - `app/api/mcp/` - Tool discovery and invocation (requires API key)
3. **Structured Models** (`app/models/`) - Organized Pydantic models with inheritance
4. **Dependency Injection** (`app/dependencies.py`) - FastAPI dependencies for auth, validation, context
5. **Middleware Stack** (`app/middleware/`) - Rate limiting, authentication, request logging
6. **Core Services** (`app/core/`) - Configuration, events, database, logging

### Authentication & Security Model
- **Public API**: Rate-limited, no authentication required
- **App API**: Supabase JWT tokens with Row Level Security (RLS) for user data isolation
- **MCP API**: API Key authentication with granular scopes (tools:read, tools:execute, health:check)
- **Token Forwarding**: Frontend JWT tokens forwarded to Supabase for RLS enforcement
- **Admin Override**: Service role key bypasses RLS for administrative operations

### Key API Endpoints
- `/api/public/health` - Service health check (no auth)
- `/api/app/sessions` - Session management with RLS (Supabase auth required)
- `/api/app/chat/stream` - Real-time chat with SSE streaming (Supabase auth required)
- `/api/mcp/tools` - Tool discovery for LLM clients (API key required)
- `/api/mcp/invoke` - Tool invocation with parameters (API key required)

### Authentication Flow
1. **Frontend handles authentication** - User registration/login via Supabase Auth client
2. **Frontend obtains JWT tokens** - Access token and refresh token from Supabase
3. **Backend verifies JWT tokens** - All API calls include `Authorization: Bearer <token>` header
4. **Token validation** - Backend validates tokens with Supabase and extracts user data
5. **Request processing** - User data is available in `request.state.user` for authenticated requests

### Data Flow
1. User authenticates via frontend (Supabase Auth client)
2. Frontend sends API requests with JWT Bearer tokens
3. Backend verifies tokens and processes requests
4. Sessions are created and stored in Supabase with user association
5. Chat messages trigger HTTP calls to workflow agent service
6. Workflow execution requests forwarded to workflow engine service
7. All data is persisted in Supabase PostgreSQL with RLS protection

## Configuration

### Environment Variables
Required environment variables in `.env`:
```
# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SECRET_KEY=your-service-role-key
SUPABASE_ANON_KEY=your-anon-key  # Required for RLS operations

# Backend Services Configuration
WORKFLOW_AGENT_URL=http://localhost:8001
WORKFLOW_ENGINE_URL=http://localhost:8002

# Logging Configuration
DEBUG=true
LOG_LEVEL=DEBUG
LOG_FORMAT=standard
```

### Database Setup
1. Create Supabase project
2. Run `sql/init_tables.sql` in Supabase SQL Editor to enable RLS
3. Configure environment variables
4. Verify RLS policies are active in Supabase dashboard

## Key Implementation Details

### Unified Authentication Middleware
- **Three-Layer Authentication**: Different auth patterns per API layer
- **Public API**: No auth required, only rate limiting applied
- **App API**: Supabase JWT verification via `Authorization: Bearer <token>` header
- **MCP API**: API Key verification via `X-API-Key` header or `Authorization: Bearer <api_key>`
- **Dependency Injection**: `AuthenticatedDeps`, `MCPDeps`, `CommonDeps` for type-safe auth context
- **Request Context**: User data and auth info available in `request.state`

### Enhanced Dependency System
- **`AuthenticatedDeps`**: Provides validated Supabase user context for App API
- **`MCPDeps`**: Provides API key client context with scopes for MCP API
- **`CommonDeps`**: Shared dependencies like request ID and processing context
- **Scope Validation**: Granular permission checking (tools:read, tools:execute, health:check)
- **Error Handling**: Proper HTTP status codes and error responses per layer

### Repository Pattern with RLS
- **`SupabaseRepository`** in `app/core/database.py` - RLS-enabled repository with user token support
- **RLS Repositories**: `sessions_rls_repo`, `chats_rls_repo` - Use user tokens for data isolation
- **Admin Repositories**: Use service role key for administrative operations
- **Guest Sessions**: Support for unauthenticated session creation
- **Token Caching**: Performance optimization for repeated database operations

### SSE Streaming
- Chat responses use SSE for real-time streaming
- Workflow progress monitoring uses SSE with different event types
- SSE utility functions in `app/utils/sse.py`

### Error Handling & Logging
- **Standard Python Logging**: Uses Python's built-in `logging` module with configurable levels
- **Log Levels**: Controlled by `LOG_LEVEL` environment variable (DEBUG, INFO, WARNING, ERROR)
- **Log Formats**: Supports multiple formats via `LOG_FORMAT` environment variable:
  - `standard`: Timestamp, level, file:line:function - message
  - `json`: Structured JSON logging for production
  - `simple`: Level - message (for development)
- **Global exception handler** in `app/main.py` with comprehensive error logging
- **Repository methods** return `None` on error for graceful degradation
- **Enhanced logging** throughout the application with emoji indicators:
  - 📨 Request processing
  - 🌐 Public endpoint access
  - 👤 Guest sessions
  - 🔐 Token verification
  - ✅ Successful authentication
  - 🚫 Authentication failures
  - ❌ Errors and exceptions
  - 📤 Response logging
- **Exception logging**: Automatic traceback logging with `log_exception()`

## Testing

### Quick Testing
For rapid verification after code changes:
```bash
# Run basic functionality tests
uv run python quick_test.py

# Run pytest tests
uv run pytest tests/test_basic.py -v
```

### Manual Testing
Use the provided curl commands in README.md for basic flow testing:
1. Health check (public)
2. Session creation (with/without auth)
3. Chat messaging (requires JWT token)
4. Workflow monitoring (requires JWT token)

Note: User registration/login is now handled by the frontend application using Supabase Auth client.

### Automated Testing
```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=app

# Run specific test file
uv run pytest tests/test_basic.py -v
```

### Test Files
- `tests/test_basic.py` - Comprehensive basic tests (12 tests covering all major endpoints)
  - Root, health, and version endpoints
  - Authentication requirement verification for App/MCP APIs
  - Middleware functionality (request ID, process time headers)
  - Application creation and configuration
- `quick_test.py` - Basic functionality verification (if available)

### Test Coverage
Current test suite includes:
- ✅ 12 comprehensive tests covering core functionality
- ✅ All three API layers (Public, App, MCP)
- ✅ Authentication and authorization checks
- ✅ Middleware verification (CORS, headers, logging)
- ✅ Error handling and edge cases

## Development Workflow

### Pre-commit Hooks
This project uses pre-commit hooks for code quality:

```bash
# Install pre-commit hooks (done automatically in repo)
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

**Configured Hooks:**
- **Black**: Code formatting (line-length=100)
- **isort**: Import sorting (profile=black, line-length=100)
- **Trailing whitespace**: Remove trailing spaces
- **End of file fixer**: Ensure files end with newline
- **YAML check**: Validate YAML syntax
- **Large files check**: Prevent large file commits
- **Merge conflicts check**: Detect merge conflict markers
- **Test runner**: Automated test execution on changes

### Code Quality Standards
- **Line Length**: 100 characters (Black + isort configured)
- **Import Style**: Black-compatible isort profile
- **Type Hints**: Comprehensive typing with Pydantic models
- **Testing**: Minimum viable test coverage with real functionality verification
- **Documentation**: Inline docstrings and comprehensive CLAUDE.md

### Debugging & Development
```bash
# Enable debug mode
export DEBUG=true
export LOG_LEVEL=DEBUG

# Start with auto-reload
uv run uvicorn app.main:app --reload --log-level debug

# View structured logs
export LOG_FORMAT=json  # For structured logging
export LOG_FORMAT=simple  # For minimal output
```

## Monorepo Context

This API Gateway is part of a larger monorepo structure:
- **Location**: `apps/backend/api-gateway/`
- **Related Services**: 
  - `apps/backend/workflow_agent/` (FastAPI service with LangGraph for AI workflow generation)
  - `apps/backend/workflow_engine/` (FastAPI service for workflow execution)
- **Shared Components**: 
  - `apps/backend/shared/models/` (Shared Pydantic models)
  - `apps/backend/shared/prompts/` (Jinja2 templates for AI prompts)
- **Frontend Demo**: `apps/demo_apps/workflow_generation/` (React/Vite demo)
- **Documentation**: `docs/tech-design/` (Architecture and API documentation)

The API Gateway serves as the HTTP interface that coordinates between the frontend and the workflow agent service, handling authentication via Supabase and streaming responses via SSE.

## Migration History

### Three-Layer Architecture Migration (January 2025)
The API Gateway was recently migrated from a single-layer architecture to a comprehensive three-layer system:

**Key Changes:**
- **Architecture**: Migrated to Public/App/MCP three-layer API structure
- **Authentication**: Implemented layer-specific auth patterns (none/JWT/API-key)
- **Dependencies**: Replaced manual auth checks with FastAPI dependency injection
- **Models**: Restructured into organized Pydantic models with inheritance
- **Middleware**: Enhanced middleware stack with proper ordering and functionality
- **Testing**: Added comprehensive test suite (12 tests covering all layers)
- **Code Quality**: Implemented pre-commit hooks with Black, isort, and automated testing

**Migration Benefits:**
- ✅ **Clear Separation**: Distinct auth patterns for different use cases
- ✅ **Type Safety**: Comprehensive typing with Pydantic models and dependencies
- ✅ **Maintainability**: Organized code structure following FastAPI best practices
- ✅ **Security**: Granular authentication and authorization per API layer
- ✅ **Testing**: Robust test coverage for continued development
- ✅ **Developer Experience**: Pre-commit hooks ensure code quality
- ✅ **Production Ready**: Factory pattern, lifespan events, proper error handling

**Commits:**
- `73876ba` - Complete API Gateway migration to three-layer FastAPI architecture
- `53fa4c3` - Fix isort configuration and add basic tests

## Important: Supabase Authentication for Testing

When running tests or interactive demos that require authentication:

1. **Always use real credentials from `.env`**:
   - `TEST_USER_EMAIL` - Must be a real email registered in Supabase
   - `TEST_USER_PASSWORD` - Must be the real password for that account
   - These are NOT placeholder values - they are actual test account credentials

2. **Authentication flow**:
   ```bash
   # The .env file contains:
   TEST_USER_EMAIL=daming.lu@starmates.ai  # Real account
   TEST_USER_PASSWORD=test.1234!           # Real password
   
   # Use these in tests:
   curl -X POST "${SUPABASE_URL}/auth/v1/token?grant_type=password" \
     -H "apikey: ${SUPABASE_ANON_KEY}" \
     -H "Content-Type: application/json" \
     -d '{"email":"'${TEST_USER_EMAIL}'","password":"'${TEST_USER_PASSWORD}'"}'
   ```

3. **Never use fake credentials** - The API Gateway requires valid Supabase JWT tokens
4. **The test account must exist** in the Supabase project before running tests
