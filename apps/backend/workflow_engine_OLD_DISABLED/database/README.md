# Database Schema Documentation

This directory contains the PostgreSQL database schema and related files for the Workflow Engine.

## Files Overview

- `schema.sql` - Complete database schema definition
- `migrations/001_initial_schema.sql` - Initial migration file for Alembic
- `seed_data.sql` - Sample data for development and testing
- `README.md` - This documentation file

## Database Structure

### Core Tables

#### User Management
- `users` - User accounts and profiles
- `user_settings` - User-specific configuration settings

#### Workflow System
- `workflows` - Workflow definitions (based on Workflow protobuf)
- `workflow_executions` - Execution records (based on ExecutionData protobuf)

#### Integration System
- `integrations` - Available third-party integrations

#### System Configuration
- `system_settings` - System-wide configuration

## Setup Instructions

### 1. Database Creation

```bash
# Create database
createdb workflow_engine

# Run schema
psql workflow_engine < schema.sql

# Load seed data (optional)
psql workflow_engine < seed_data.sql
```

### 2. Using with Alembic

```bash
# Initialize Alembic (if not already done)
alembic init alembic

# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "Description"
```

## Key Design Decisions

### 1. Protobuf-First Design
- Database schema mirrors protobuf definitions
- JSONB storage for complex nested structures
- Type safety through protobuf validation

### 2. Flexible Node System
- Generic node storage in workflow_data JSONB
- Type-specific validation at application layer
- Extensible for new node types

### 3. Execution Tracking
- Detailed timing and status information
- Error tracking and retry logic
