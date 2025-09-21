# Workflow Engine - Clean & Simple ✅ COMPLETED

This is the **completely revamped** Workflow Engine with a clean, simple structure that's easy to understand and maintain.

## 🎉 **MIGRATION COMPLETED SUCCESSFULLY**

The old complex nested structure has been fully migrated to a clean, maintainable architecture with **ALL functionality preserved**.

## Why the Revamp?

The old structure was a nightmare:
- ❌ `workflow_engine/workflow_engine/` (redundant nesting)
- ❌ `workflow_engine/workflow_engine/api/v1/` (too deep)
- ❌ `workflow_engine/workflow_engine/services/` (confusing)
- ❌ Multiple scattered configuration files
- ❌ Complex inheritance hierarchies
- ❌ Hard to debug and maintain
- ❌ **The async execution bug that took hours to debug**

## ✅ New Clean Structure - FULLY MIGRATED

```
workflow_engine/
├── main.py              # 🎯 FastAPI app - THE entry point with ALL endpoints
├── config.py            # ⚙️ Comprehensive configuration (OAuth, AI providers, etc.)
├── models.py            # 📋 Pydantic models with full request/response types
├── executor.py          # 🚀 Enhanced execution logic with node-based system
├── database.py          # 💾 Comprehensive database operations (SQLAlchemy + Supabase)
├── nodes/               # 🔧 Complete node execution system
│   ├── __init__.py      # Node system exports
│   ├── base.py          # BaseNodeExecutor with validation & logging
│   ├── factory.py       # NodeExecutorFactory with registration system
│   ├── trigger_node.py  # Manual, webhook, scheduled triggers
│   ├── ai_agent_node.py # OpenAI (gpt-4o*, gpt-3.5*), Anthropic (claude-3-5*) providers
│   ├── action_node.py   # HTTP requests, data transformation
│   ├── external_action_node.py  # Third-party integrations (Slack, Notion, etc.)
│   ├── flow_node.py     # Conditional logic (IF, SWITCH, MERGE)
│   ├── human_loop_node.py  # Human interaction points
│   ├── memory_node.py   # Vector stores, data persistence
│   └── tool_node.py     # MCP tools and utilities

**IMPORTANT NODE TYPE VALIDATION:**
The workflow engine validates node types strictly. Use these exact values:
- `TRIGGER` (not `TRIGGER_NODE`)
- `AI_AGENT` (not `AI_AGENT_NODE`) with subtype `ANTHROPIC_CLAUDE` (not `CLAUDE`)
- `EXTERNAL_ACTION` (not `EXTERNAL_ACTION_NODE`) requires `action_type` parameter
- `ACTION`, `FLOW`, `HUMAN_LOOP`, `TOOL`, `MEMORY`
├── requirements.txt     # 📦 All dependencies (FastAPI, AI providers, DB, etc.)
├── Dockerfile          # 🐳 Container build
└── CLAUDE.md           # 📚 This documentation
```

## Key Features

### 1. **Single Entry Point** (`main.py`)
- All HTTP requests go through ONE clear FastAPI app
- **The core endpoint**: `/v1/workflows/{workflow_id}/execute`
- Clear debug logging so you can see exactly what's happening
- Simple async vs sync execution logic

**AI AGENT SUBTYPES:**
- `OPENAI` - OpenAI GPT models (gpt-4o-mini, gpt-3.5-turbo, etc.)
- `ANTHROPIC_CLAUDE` - Anthropic Claude models (claude-3-5-haiku-20241022, etc.)
- Not `CLAUDE` or `CLAUDE_NODE` - these will cause validation errors

**EXTERNAL ACTION REQUIREMENTS:**
All EXTERNAL_ACTION nodes require an `action_type` parameter:
- For Notion: `search`, `page_update`, `update_page`
- For Slack: `send_message`
- Without `action_type`, you'll get: "Missing required parameter: action_type"

### 2. **Crystal Clear Async Execution**
```python
if request.async_execution:
    # 🎯 ASYNC: Return immediately (within 1 second)
    asyncio.create_task(executor.execute_workflow_background(...))
    return ExecuteWorkflowResponse(execution_id=execution_id, ...)
else:
    # 🔄 SYNC: Wait for completion
    result = await executor.execute_workflow_sync(...)
    return result
```

### 3. **Simple Configuration** (`config.py`)
- One class, clean environment variables
- No complex inheritance or multiple config files

### 4. **Clean Database Interface** (`database.py`)
- Simple Supabase client
- Clear method names
- Proper error handling

### 5. **Focused Executor** (`executor.py`)
- Background execution for async requests
- Synchronous execution for testing
- Clear separation of concerns

## Development Commands

### Start the Engine
```bash
# Development mode
python main.py

# Or with uvicorn
uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```

### Build & Run with Docker
```bash
# Build
docker compose up --build workflow-engine

# Full rebuild
docker compose down && docker compose up --build
```

### Testing the API
```bash
# Health check
curl http://localhost:8002/health

# Execute workflow (async - returns immediately)
curl -X POST "http://localhost:8002/v1/workflows/test-id/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "test-id",
    "user_id": "user123",
    "async_execution": true,
    "trigger_data": {"message": "test"}
  }'

# Execute workflow (sync - waits for completion)
curl -X POST "http://localhost:8002/v1/workflows/test-id/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "test-id",
    "user_id": "user123",
    "async_execution": false,
    "trigger_data": {"message": "test"}
  }'
```

## API Endpoints

### Core Execution
- `POST /v1/workflows/{workflow_id}/execute` - **THE main endpoint**
- `GET /v1/executions/{execution_id}` - Get execution status
- `GET /health` - Health check

### Simple Request/Response
```python
# Request
{
  "workflow_id": "abc123",
  "user_id": "user456",
  "async_execution": true,  # KEY: true = return immediately
  "trigger_data": {"message": "hello"}
}

# Response (immediate for async)
{
  "execution_id": "exec789",
  "status": "NEW",
  "success": true,
  "message": "Workflow execution started asynchronously"
}
```

## Key Insights

### 1. **The Async Fix**
The original problem was that `async_execution=true` wasn't working. The fix:
- **Old**: Complex nested structure made it hard to find the issue
- **New**: Simple, clear logic in `main.py` - you can see exactly what happens

### 2. **Debug Visibility**
Every request logs clearly:
```
🔥 WORKFLOW EXECUTE ENDPOINT HIT!
🔥 Workflow ID: abc123
🔥 Async execution: True
⚡ ASYNC: Starting background execution
```

### 3. **No More Nested Confusion**
- **Old**: `workflow_engine/workflow_engine/api/v1/executions.py`
- **New**: `main.py` - ONE file with the endpoint

## Environment Variables

```bash
# Required
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SECRET_KEY=your-service-role-key

# AI Provider Keys (required for AI_AGENT nodes)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# OAuth Tokens (required for EXTERNAL_ACTION nodes)
SLACK_BOT_TOKEN=xoxb-...
NOTION_API_KEY=secret_...

# Optional
HOST=0.0.0.0
PORT=8002
DEBUG=true
LOG_LEVEL=INFO

# Model Validation Note
# The OpenAI API validates model names strictly
# Use standard models: gpt-4o-mini, gpt-3.5-turbo, claude-3-5-haiku-20241022
# Custom endpoints may have different model names (e.g., gpt-5)
```

## Docker Integration

The `Dockerfile` is clean and simple:
1. Install dependencies from `requirements.txt`
2. Copy application code
3. Run `python main.py`

No complex build steps, no confusing COPY commands.

## Migration Notes

### What Was Kept
- Core execution logic (simplified)
- Supabase database integration
- FastAPI framework
- Docker containerization

### What Was Removed
- ❌ Complex nested directory structure
- ❌ Multiple scattered API files
- ❌ Confusing service layer abstractions
- ❌ Complex inheritance hierarchies
- ❌ Redundant configuration files

### What Was Fixed
- ✅ **The async execution bug** - now works correctly
- ✅ **Clear endpoint visibility** - easy to debug
- ✅ **Simple structure** - easy to understand and maintain
- ✅ **Fast response times** - async returns within 1 second

## Future Extensions

When you need to add features:

1. **New endpoints** → Add to `main.py`
2. **New models** → Add to `models.py`
3. **New database operations** → Add to `database.py`
4. **New execution logic** → Add to `executor.py`
5. **New node types** → Add to `nodes/`

Keep it simple, keep it clean, keep it working.

## Remember

> **Every time you make code changes, rebuild with:**
> ```bash
> docker compose down && docker compose up --build
> ```

This new structure makes debugging and maintenance much easier. The async execution issue that was taking hours to debug is now obvious and fixed in the clean `main.py` file.
