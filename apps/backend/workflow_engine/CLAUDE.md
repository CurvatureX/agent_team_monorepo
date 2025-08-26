# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Workflow Engine Overview

The Workflow Engine is a **FastAPI-based microservice** that executes AI-powered workflows through a sophisticated node-based execution system. It serves as the execution layer in a three-service architecture alongside the API Gateway and Workflow Agent.

## Core Architecture

### Node-Based Execution System
The engine uses a **factory pattern** with 8 core node types:
- **TRIGGER_NODE**: Manual, webhook, cron triggers
- **AI_AGENT_NODE**: OpenAI, Anthropic, and custom AI nodes with memory integration
- **ACTION_NODE**: HTTP requests, code execution, data transformation
- **EXTERNAL_ACTION_NODE**: Third-party API integrations (GitHub, Slack, etc.)
- **FLOW_NODE**: Conditional logic (IF, SWITCH, MERGE, FILTER)
- **HUMAN_IN_THE_LOOP_NODE**: Human interaction points
- **TOOL_NODE**: MCP tools and utilities
- **MEMORY_NODE**: Vector stores and data persistence

### Memory Integration System
The engine includes a comprehensive **memory implementation system** in `memory_implementations/`:
- **ConversationBufferMemory**: Chat history with Redis + Supabase backend
- **EntityMemory**: Entity extraction and relationship tracking
- **KnowledgeBaseMemory**: Structured fact storage with rule inference
- **GraphMemory**: Entity relationship modeling with path finding
- **EpisodicMemory**: Time-series event storage
- **DocumentStoreMemory**: Full-text document storage
- **VectorDatabaseMemory**: Semantic vector search with embeddings
- **MemoryContextMerger**: Intelligent context merging for LLM enhancement

### Key Components
- **BaseNodeExecutor**: Abstract base class with spec-aware validation
- **NodeExecutorFactory**: Dynamic node creation with type registration
- **NodeExecutionContext**: Execution context with input data and credentials
- **Node Specification System**: Centralized parameter validation and type conversion

## Development Commands

### Environment Setup
```bash
# Install dependencies
uv sync

# Alternative: pip install
pip install -e .
pip install -e ".[dev]"  # For development dependencies

# Memory implementations also require:
pip install supabase openai redis
# Or ensure these are in requirements.txt
```

### Server Management
```bash
# Start FastAPI server
python -m workflow_engine.main
# Or: ./start_server.sh

# Start with auto-reload
uvicorn workflow_engine.main:app --reload --port 8002
```

### Database Operations
```bash
# Initialize database
make db-init
alembic upgrade head

# Create migration
make db-migrate MSG="description"
alembic revision --autogenerate -m "description"

# Reset database (development)
make db-reset
```

### Testing & Quality
```bash
# Run tests
make test
pytest tests/

# Single test file
pytest tests/test_node_executor.py

# With coverage
pytest --cov=workflow_engine tests/

# Memory integration tests
cd memory_implementations/tests
python demo_test.py                    # Quick integration demo
python simple_test_runner.py          # Comprehensive tests

# Code quality
make lint     # flake8 + mypy
make format   # black + isort
```

## Node Specification Integration

The engine integrates with a centralized node specification system in `shared/node_specs/`:

### Key Features
- **Automatic Validation**: Parameters validated against specs during execution
- **Type Conversion**: Automatic conversion (string → int/float/bool/JSON)
- **Default Values**: Spec-defined defaults applied when parameters missing
- **Dual Validation**: Spec-based validation with legacy fallback

### Usage in Node Executors
```python
# In node executor classes
def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
    # Get parameter with automatic type conversion
    temperature = self.get_parameter_with_spec(context, "temperature")  # Returns float
    model = self.get_parameter_with_spec(context, "model_version")      # Returns string

    # Validation happens automatically during workflow creation
```

## API Endpoints Structure

### Core Endpoints (Port 8002)
```
GET    /health                              # Health check with DB validation
GET    /docs                                # OpenAPI documentation

# Workflow Management
POST   /v1/workflows                        # Create workflow with validation
GET    /v1/workflows/{id}                   # Get workflow details
PUT    /v1/workflows/{id}                   # Update workflow
DELETE /v1/workflows/{id}                   # Delete workflow
GET    /v1/workflows                        # List workflows

# Execution Management
POST   /v1/workflows/{id}/execute           # Execute complete workflow
GET    /v1/executions/{id}                  # Get execution status
POST   /v1/executions/{id}/cancel           # Cancel running execution
GET    /v1/workflows/{id}/executions        # Get execution history

# Single Node Execution
POST   /v1/workflows/{id}/nodes/{node_id}/execute  # Execute single node

# Node Specifications
GET    /api/v1/node-specs                   # List all node specifications
GET    /api/v1/node-specs/{type}/{subtype}  # Get specific node spec
```

## Database Architecture

### Key Models (in shared/models/db_models.py)
- **Workflow**: Complete workflow definitions stored as JSONB
- **WorkflowExecution**: Execution tracking with status and results
- **NodeTemplate**: Reusable node configurations
- **Integration**: Third-party service configurations

### Database Configuration
- **PostgreSQL**: Primary database with SSL for Supabase
- **SQLAlchemy**: ORM with proper session management
- **Alembic**: Migration management
- **Connection Pooling**: Configured for production use

## Service Layer Architecture

### Core Services (workflow_engine/services/)
- **WorkflowService**: CRUD operations with spec validation
- **ExecutionService**: Workflow and single-node execution
- **ValidationService**: Workflow structure and parameter validation

### Validation Integration
```python
# WorkflowService automatically validates using specs
def create_workflow_from_data(self, workflow_data: dict) -> Workflow:
    # Validates against node specifications
    validation_result = self.validator.validate_workflow_structure(
        workflow_data, validate_node_parameters=True
    )
    if not validation_result['valid']:
        raise ValueError(f"Validation failed: {validation_result['errors']}")
```

## Configuration Management

### Environment Variables (workflow_engine/core/config.py)
```bash
# Database
DATABASE_URL="postgresql://user:pass@host/db"

# Server
PORT="8002"
HOST="0.0.0.0"
DEBUG="false"

# AI Providers (required for memory implementations)
OPENAI_API_KEY="sk-..."
ANTHROPIC_API_KEY="sk-ant-..."

# Memory System Dependencies
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_SECRET_KEY="your-service-role-key"
REDIS_URL="redis://localhost:6379/0"
```

## Testing Patterns

### Test Structure
- **Unit Tests**: Node executors, services, validation
- **Integration Tests**: End-to-end workflow execution
- **Database Tests**: Schema validation and migrations

### Common Test Patterns
```python
# Test node execution with specs
def test_node_with_spec():
    node = OpenAINode(subtype="OPENAI_NODE")
    context = NodeExecutionContext(
        parameters={"system_prompt": "test", "model_version": "gpt-4"}
    )
    result = node.execute(context)
    assert result.status == "success"

# Test workflow validation
def test_workflow_validation():
    workflow_data = {...}  # Complete workflow definition
    validator = WorkflowValidator()
    result = validator.validate_workflow_structure(
        workflow_data, validate_node_parameters=True
    )
    assert result['valid']
```

## Important Development Notes

### Recent Architectural Changes
1. **gRPC → FastAPI Migration**: Service migrated from gRPC to FastAPI for consistency
2. **Node Specification Integration**: All node executors now use centralized specs
3. **Dual Validation System**: Spec-based validation with legacy fallback
4. **Type-Safe Parameters**: Automatic type conversion based on specifications

### Factory Pattern Registration
```python
# New node types automatically registered
@NodeExecutorFactory.register("NEW_NODE_TYPE")
class NewNodeExecutor(BaseNodeExecutor):
    def execute(self, context):
        # Implementation with spec support
        param_value = self.get_parameter_with_spec(context, "param_name")
```

### Error Handling Patterns
- **Structured Errors**: Consistent error responses with correlation IDs
- **Graceful Degradation**: Fallback to legacy validation when specs unavailable
- **Comprehensive Logging**: Detailed execution tracking and debugging

### Docker & Deployment
- **Multi-stage Dockerfile**: Optimized for production deployment
- **Health Checks**: Built-in container health monitoring
- **Non-root User**: Security best practices implemented
- **Resource Optimization**: Proper signal handling and cleanup

## Performance Considerations

- **Connection Pooling**: Database connections optimized for concurrent workflows
- **Redis Caching**: Used for execution state and temporary data
- **Async Operations**: FastAPI async support for I/O-bound operations
- **Monitoring**: OpenTelemetry integration for performance tracking

The Workflow Engine provides a robust, scalable foundation for executing complex AI workflows with comprehensive validation, monitoring, and extensibility for new node types.
