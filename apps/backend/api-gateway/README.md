# API Gateway

API Gateway for Workflow Agent Team - Frontend Auth Architecture

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager
- Supabase account and project

### 1. Install uv

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or via pip
pip install uv
```

### 2. Setup Environment

```bash
# Copy environment variables
cp .env.example .env

# Edit .env with your Supabase credentials
# SUPABASE_URL=https://your-project-id.supabase.co
# SUPABASE_SERVICE_KEY=your-service-role-key
# SUPABASE_ANON_KEY=your-anon-key  # Required for RLS operations
```

### 3. Start the Server

```bash
# Option 1: Use the startup script (recommended)
./start.sh

# Option 2: Manual startup with uv
uv sync                    # Install dependencies
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Option 3: Legacy manual startup (if uv not available)
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Test the API

```bash
# Health check (public endpoint)
curl http://localhost:8000/health

# Create new workflow session (requires JWT token)
curl -X POST http://localhost:8000/api/v1/session \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "action": "create"
  }'

# Edit existing workflow session (requires JWT token)
curl -X POST http://localhost:8000/api/v1/session \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "action": "edit",
    "workflow_id": "existing-workflow-id"
  }'

# For authenticated endpoints, you need a Supabase JWT token from your frontend
# Replace YOUR_JWT_TOKEN with actual token from Supabase Auth

# Send chat message with streaming response (requires JWT token)
curl -N "http://localhost:8000/api/v1/chat/stream?session_id=your-session-id&user_message=Hello!" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Listen to workflow generation progress (requires JWT token)
curl -N "http://localhost:8000/api/v1/workflow_generation?session_id=your-session-id" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json
- **Frontend Integration Guide**: [docs/FRONTEND_INTEGRATION.md](docs/FRONTEND_INTEGRATION.md)

## Features

✅ **Implemented:**
- Frontend authentication with JWT verification
- Session management with workflow actions (POST /session)
- Incremental chat streaming API (GET /chat/stream)
- Workflow generation status monitoring (GET /workflow_generation)
- Industry-standard SSE streaming (delta-based)
- Comprehensive request/response logging
- Supabase integration with RLS support

🚧 **TODO (waiting for gRPC IDL):**
- Real gRPC integration with workflow service
- Real AI service integration

🔮 **Future Extensions:**
- Rate limiting
- Advanced error handling
- Monitoring and metrics
- Database connection pooling

## Authentication Architecture

This API Gateway follows **frontend authentication** best practices:

1. **Frontend responsibility**: User registration, login, token refresh handled by frontend Supabase client
2. **Backend responsibility**: JWT token verification and API request processing
3. **Token validation**: All authenticated endpoints require `Authorization: Bearer <token>` header
4. **Session actions**: Support for create/edit/copy workflow sessions
5. **User context**: Authenticated user data available in `request.state.user`

## Development with uv

### Package Management

```bash
# Install dependencies
uv sync

# Add a new dependency
uv add fastapi

# Add a dev dependency
uv add --dev pytest

# Remove a dependency
uv remove fastapi

# Update dependencies
uv sync --upgrade

# Check for outdated packages
uv pip list --outdated
```

### Running Tests

```bash
# Run tests with uv
uv run pytest tests/

# Run tests with coverage
uv run pytest tests/ --cov=app

# Run linting
uv run black app/ tests/
uv run isort app/ tests/
uv run flake8 app/ tests/
uv run mypy app/
```

### Development Scripts

For convenience, you can use the development helper script:

```bash
# Install dependencies
./scripts/dev.sh install

# Start development server
./scripts/dev.sh dev

# Run tests
./scripts/dev.sh test

# Run linting
./scripts/dev.sh lint

# Format code
./scripts/dev.sh format

# Run all checks (lint + test)
./scripts/dev.sh check

# Clean cache and virtual env
./scripts/dev.sh clean

# Show help
./scripts/dev.sh help
```

### Manual Testing Checklist

- [ ] Health check endpoint works (public)
- [ ] Session creation with actions works (requires auth)
- [ ] JWT token verification works
- [ ] Incremental chat streaming works (GET /chat/stream)
- [ ] Workflow generation monitoring works (GET /workflow_generation)
- [ ] SSE delta streaming works correctly
- [ ] Supabase connection and JWT verification works
- [ ] Request/response logging appears in console

## Docker

```bash
# Build image with uv
docker build -t api-gateway .

# Run container
docker run -p 8000:8000 --env-file .env api-gateway

# Or with docker-compose (if available)
docker-compose up --build
```

## Project Structure

```
apps/backend/api-gateway/
├── app/                    # Main application code
│   ├── api/               # API route handlers
│   │   ├── session.py     # Session management (create/edit/copy)
│   │   ├── chat.py        # Chat streaming (GET /chat/stream)
│   │   └── workflow.py    # Workflow generation (GET /workflow_generation)
│   ├── services/          # Business logic services
│   │   ├── auth_service.py # JWT verification
│   │   └── grpc_client.py # gRPC client (future)
│   ├── utils/             # Utility functions
│   │   ├── sse.py         # SSE streaming utilities
│   │   └── logger.py      # Logging utilities
│   ├── config.py          # Configuration
│   ├── database.py        # Supabase connection with RLS
│   ├── models.py          # Pydantic data models
│   └── main.py            # FastAPI app with JWT middleware
├── docs/                  # Documentation
│   ├── API_DOC.md        # API specification
│   └── FRONTEND_INTEGRATION.md # Frontend integration guide
├── sql/                   # Database scripts
├── tests/                 # Test files
├── Dockerfile             # Container configuration
├── pyproject.toml         # Python dependencies with uv
└── README.md             # This file
```

## Troubleshooting

### Common Issues

1. **uv not found**
   ```bash
   # Install uv
   curl -LsSf https://astral.sh/uv/install.sh | sh
   # Add to PATH
   export PATH="$HOME/.cargo/bin:$PATH"
   ```

2. **Supabase connection failed**
   ```bash
   # Check environment variables
   echo $SUPABASE_URL
   echo $SUPABASE_SERVICE_KEY
   ```

3. **Database tables not found**
   - Run `sql/init_tables.sql` in Supabase SQL Editor

4. **Port already in use**
   ```bash
   # Kill process using port 8000
   lsof -ti:8000 | xargs kill -9
   ```

5. **Import errors**
   ```bash
   # Make sure dependencies are installed
   uv sync
   # Or export PYTHONPATH
   export PYTHONPATH=/path/to/api-gateway:$PYTHONPATH
   ```

6. **Lock file conflicts**
   ```bash
   # Remove lock file and reinstall
   rm uv.lock
   uv sync
   ```

## Key Features

### 🔄 Incremental SSE Streaming
- **Industry Standard**: Follows OpenAI/Claude/Gemini delta-based streaming
- **Efficient**: Only sends new content in each SSE event
- **Real-time**: Immediate UI updates as content streams

### 📋 Session Management
- **Action-based**: Support for `create`, `edit`, and `copy` workflows
- **RLS Security**: Row-level security ensures user data isolation
- **JWT Authentication**: Secure token-based authentication

### 🔧 Workflow Generation
- **Status Tracking**: Real-time workflow generation status via SSE
- **Stage Monitoring**: `waiting → start → draft → debugging → complete`
- **Error Handling**: Graceful error reporting and recovery

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check (public) |
| `POST` | `/api/v1/session` | Create/edit workflow session |
| `GET` | `/api/v1/chat/stream` | Incremental chat streaming |
| `GET` | `/api/v1/workflow_generation` | Workflow status monitoring |

## Contributing

This API Gateway follows frontend authentication patterns recommended by Supabase. 

Frontend applications should handle user authentication and pass JWT tokens to the backend via Authorization headers.

See [docs/FRONTEND_INTEGRATION.md](docs/FRONTEND_INTEGRATION.md) for complete integration examples.