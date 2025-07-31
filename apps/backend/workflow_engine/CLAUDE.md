# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Core Development
- **Install dependencies**: `pip install -r requirements.txt`
- **Run service**: `python -m workflow_engine.main` or `./start_server.sh`
- **Run tests**: `pytest tests/`
- **Run specific test**: `pytest tests/test_workflow_crud.py::test_create_workflow`

### Database Operations
- **Initialize database**: `python tests/init_database.py`
- **Run migrations**: `alembic upgrade head`
- **Clean database**: `python tests/clean_database.py`

### Docker Operations
- **Build image**: `docker build -f Dockerfile -t workflow-engine .`
- **Run container**: `docker run -p 8002:8002 --env-file .env workflow-engine`

## Architecture Overview

The Workflow Engine is responsible for executing AI-powered workflows created by the Workflow Agent. It manages workflow lifecycle, executes nodes, and handles state persistence.

### Core Components

1. **FastAPI Server** (`workflow_engine/main.py`)
   - HTTP API on port 8002
   - Handles workflow CRUD operations
   - Manages workflow execution lifecycle

2. **Execution Engine** (`workflow_engine/execution_engine.py`)
   - Orchestrates workflow execution
   - Manages node state transitions
   - Handles error recovery and retries

3. **Node System** (`workflow_engine/nodes/`)
   - **Base Node**: Abstract interface for all node types
   - **Trigger Nodes**: Workflow entry points (cron, webhook, manual)
   - **AI Agent Nodes**: LLM-powered processing nodes
   - **Action Nodes**: External API calls, data transformations
   - **Flow Nodes**: Conditional logic, loops, branching
   - **Human-in-Loop Nodes**: User interaction points
   - **Memory Nodes**: Data persistence and retrieval
   - **Tool Nodes**: Specialized integrations

4. **Data Models** (`workflow_engine/models/`)
   - **Workflow Model**: Workflow definition and metadata
   - **Execution Model**: Runtime state and history
   - **Node Template Model**: Node configuration schemas

5. **Services** (`workflow_engine/services/`)
   - **Workflow Service**: CRUD operations for workflows
   - **Execution Service**: Manages workflow runs
   - **Validation Service**: Validates workflow definitions

## Workflow Execution Flow

1. **Workflow Creation**: Define workflow structure with nodes and connections
2. **Validation**: Ensure workflow is valid (no cycles, proper connections)
3. **Execution Start**: Create execution instance with initial state
4. **Node Processing**:
   - Execute nodes based on topological order
   - Pass data between nodes via connections
   - Handle errors with retry logic
5. **State Persistence**: Save execution state after each node
6. **Completion**: Mark execution as complete/failed

## Node Implementation

### Creating New Node Types

1. Extend `BaseNode` class in `nodes/base.py`
2. Implement required methods:
   ```python
   async def execute(self, context: ExecutionContext) -> NodeOutput
   async def validate(self, config: Dict[str, Any]) -> bool
   ```
3. Register node in `nodes/factory.py`
4. Add node type to protobuf definitions if needed

### Node Configuration

Each node has:
- **Type**: Node category (TRIGGER, AI_AGENT, ACTION, etc.)
- **Subtype**: Specific implementation (CRON, OPENAI_CHAT, HTTP_REQUEST)
- **Config**: Node-specific parameters
- **Connections**: Input/output mappings

## Database Schema

PostgreSQL database with tables:
- **workflows**: Workflow definitions
- **workflow_versions**: Version history
- **executions**: Execution instances
- **execution_logs**: Node execution history
- **node_templates**: Reusable node configurations

## Environment Configuration

Required environment variables:
```bash
# Service Configuration
PORT=8002
DEBUG=false

# Database
DATABASE_URL=postgresql://user:pass@localhost/workflow_engine

# Redis Cache
REDIS_URL=redis://localhost:6379/0

# AI Services (for AI nodes)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# External Services
WEBHOOK_BASE_URL=https://your-domain.com/webhooks
```

## API Endpoints

### Workflow Management
- `GET /api/v1/workflows` - List workflows
- `POST /api/v1/workflows` - Create workflow
- `GET /api/v1/workflows/{id}` - Get workflow details
- `PUT /api/v1/workflows/{id}` - Update workflow
- `DELETE /api/v1/workflows/{id}` - Delete workflow

### Execution Management
- `POST /api/v1/executions` - Start workflow execution
- `GET /api/v1/executions/{id}` - Get execution status
- `POST /api/v1/executions/{id}/cancel` - Cancel execution
- `GET /api/v1/executions/{id}/logs` - Get execution logs

### Triggers
- `POST /api/v1/triggers/webhook/{workflow_id}` - Webhook trigger
- `GET /api/v1/triggers/cron` - List cron triggers

## Testing Strategy

### Unit Tests
- Node implementations: `tests/test_nodes/`
- Service logic: `tests/test_services/`
- Validation: `tests/test_validation_service.py`

### Integration Tests
- Workflow CRUD: `tests/test_workflow_crud.py`
- Execution flow: `tests/test_workflow_execution.py`
- End-to-end: `tests/test_enhanced_execution.py`

### Test Utilities
- Database setup: `tests/init_database.py`
- Test data: `tests/fixtures/`

## Common Development Tasks

### Adding New Node Type
1. Create node class in `nodes/` directory
2. Add to node factory
3. Update protobuf if needed
4. Add tests
5. Update documentation

### Debugging Executions
1. Check execution logs in database
2. Use `quick_debug.sh` for rapid testing
3. Enable DEBUG logging
4. Review execution state transitions

### Performance Optimization
- Use Redis for frequently accessed data
- Implement connection pooling
- Optimize database queries
- Add appropriate indexes

## Migration from gRPC

The service is migrating from gRPC to FastAPI:
- Main server now uses FastAPI (port 8002)
- gRPC definitions kept for data validation
- RESTful API for all operations
- Maintains compatibility with existing data models

## Key Design Decisions

1. **Stateful Execution**: Each node execution is persisted for reliability
2. **Retry Logic**: Built-in retry mechanisms for transient failures
3. **Async First**: All node executions are async for better performance
4. **Modular Nodes**: Easy to add new node types without core changes
5. **Version Control**: Workflow versioning for safe updates

## Troubleshooting

### Common Issues

1. **Database Connection**:
   - Check DATABASE_URL format
   - Ensure PostgreSQL is running
   - Verify database exists

2. **Node Execution Failures**:
   - Check node configuration
   - Verify external service credentials
   - Review execution logs

3. **Performance Issues**:
   - Monitor database query performance
   - Check Redis connection
   - Review async operation handling

## Integration with Other Services

- **API Gateway**: Receives execution requests via HTTP
- **Workflow Agent**: Provides workflow definitions
- **External Services**: Integrates via action nodes

Remember: The Workflow Engine is the execution heart of the system - reliability and performance are critical.