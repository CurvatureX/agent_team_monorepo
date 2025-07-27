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

### Frontend Auth + RLS Architecture
This FastAPI application serves as an API Gateway with **frontend-managed authentication** and **Supabase Row Level Security (RLS)** following best practices:

1. **FastAPI Application** (`app/main.py`) - Main application with JWT middleware, CORS, and comprehensive logging
2. **Supabase RLS Integration** (`app/database.py`) - Database client with RLS support, user token forwarding
3. **JWT Verification** (`app/services/auth_service.py`) - Supabase JWT token verification (backend only)
4. **gRPC Client** (`app/services/grpc_client.py`) - Client for workflow service communication
5. **SSE Streaming** (`app/utils/sse.py`) - Server-sent events for real-time data streaming

### RLS Security Model
- **User Isolation**: Each user can only access their own data via Supabase RLS policies
- **Guest Sessions**: Anonymous users can create and access guest sessions
- **Token Forwarding**: Frontend JWT tokens are forwarded to Supabase for RLS enforcement
- **Admin Override**: Service role key bypasses RLS for administrative operations

### Key API Endpoints
- `/api/v1/session` - Session management with action and workflow_id parameters
- `/api/v1/chat/stream` - Chat with SSE streaming via GET request
- `/api/v1/workflow_generation` - Workflow generation progress monitoring with SSE

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
5. Chat messages trigger gRPC calls to workflow service
7. All data is persisted in Supabase PostgreSQL with RLS protection

## Configuration

### Environment Variables
Required environment variables in `.env`:
```
# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SECRET_KEY=your-service-role-key
SUPABASE_ANON_KEY=your-anon-key  # Required for RLS operations

# Workflow Service Configuration
WORKFLOW_SERVICE_HOST=localhost
WORKFLOW_SERVICE_PORT=50051

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

### JWT Authentication Middleware
- Verifies Supabase JWT tokens via `Authorization: Bearer <token>` header
- Public endpoints: `/health`, `/docs`, and documentation endpoints
- Guest session creation: `POST /api/v1/session` (allows unauthenticated session creation)
- User data is added to `request.state.user` for authenticated requests
- Comprehensive request/response logging for debugging

### Repository Pattern with RLS
- **`SupabaseRepository`** in `app/database.py` - RLS-enabled repository with user token support
- **`MVPSupabaseRepository`** - Backwards compatible admin-only repository
- **RLS Repositories**: `sessions_rls_repo`, `messages_rls_repo` - Use user tokens for RLS
- **Admin Repositories**: `sessions_repo`, `messages_repo` - Use service role key
- All operations support both authenticated users and guest sessions
- User token caching to improve performance

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
- `quick_test.py` - Basic functionality verification (health, docs, basic endpoints)
- `tests/test_basic.py` - Basic unit tests with mocking
- `tests/test_session_quick.py` - Session-specific tests
- `tests/conftest.py` - Test configuration and fixtures

## Monorepo Context

This API Gateway is part of a larger monorepo structure:
- **Location**: `apps/backend/api-gateway/`
- **Related Services**: `apps/backend/workflow_agent/` (gRPC service with LangGraph)
- **Shared Components**: `apps/backend/shared/proto/` (gRPC definitions), `apps/backend/shared/prompts/` (Jinja2 templates)
- **Frontend Demo**: `apps/demo_apps/workflow_generation/` (React/Vite demo)
- **Documentation**: `docs/tech-design/` (Architecture and API documentation)

The API Gateway serves as the HTTP interface that coordinates between the frontend and the workflow agent service, handling authentication via Supabase and streaming responses via SSE.