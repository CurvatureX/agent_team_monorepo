# Workflow Engine

A high-performance workflow execution engine for the AI Agent Team monorepo.

## Overview

The Workflow Engine is responsible for executing AI-powered workflows, managing state transitions, and coordinating between different workflow nodes. It provides a robust foundation for building complex, multi-step AI automation processes.

## Features

- **Workflow Execution**: Execute complex multi-node workflows
- **State Management**: Persistent workflow state tracking
- **Node Types**: Support for various node types (AI Agent, Action, Condition, etc.)
- **Database Integration**: PostgreSQL backend with SQLAlchemy ORM
- **Caching**: Redis integration for performance optimization
- **API Interface**: RESTful API for workflow management
- **Monitoring**: Comprehensive logging and metrics

## Quick Start

1. **Install Dependencies**:
   ```bash
   uv sync
   ```

2. **Set Environment Variables**:
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

3. **Start the Server**:
   ```bash
   ./start_server.sh
   ```

## Architecture

The Workflow Engine follows a modular architecture:

- `workflow_engine/core/` - Core workflow execution logic
- `workflow_engine/models/` - Database models and schemas
- `workflow_engine/nodes/` - Workflow node implementations
- `workflow_engine/services/` - Business logic services
- `workflow_engine/api/` - HTTP API endpoints

## Development

- **Testing**: `pytest tests/`
- **Linting**: Configured with ruff and mypy
- **Database Migrations**: Alembic for schema management

For detailed documentation, see the `/doc` directory.
