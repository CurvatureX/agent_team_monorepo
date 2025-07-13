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
- `workflow_versions` - Version history for workflows
- `workflow_executions` - Execution records (based on ExecutionData protobuf)
- `node_executions` - Detailed node-level execution data

#### Node System (8 Core Node Types)
- `nodes` - Individual node configurations with 8 core types
- `node_connections` - Connections between nodes in workflows
- `node_templates` - Reusable node configuration templates

#### AI System
- `ai_generation_history` - AI workflow generation history
- `ai_models` - Available AI models and configurations

#### Integration System
- `integrations` - Available third-party integrations
- `oauth_tokens` - User OAuth tokens and credentials
- `workflow_triggers` - Workflow trigger configurations

#### Debugging & Validation
- `validation_logs` - Workflow validation results
- `debug_sessions` - Debug session management
- `workflow_memory` - Runtime memory storage

#### System Configuration
- `system_settings` - System-wide configuration

## Schema Features

### Data Types
- **UUID**: Primary keys using PostgreSQL's UUID type
- **JSONB**: Flexible JSON storage for complex data structures
- **Arrays**: PostgreSQL array types for lists
- **Timestamps**: Both Unix timestamps and PostgreSQL timestamps

### Protobuf Integration
The database schema is designed to work seamlessly with the protobuf definitions:
- `workflow_data` columns store complete protobuf JSON representations
- JSONB columns allow flexible querying of nested protobuf data
- Consistent field naming between protobuf and database

### Performance Optimizations
- **Indexes**: Comprehensive indexing strategy for common queries
- **Constraints**: Data integrity constraints and checks
- **Triggers**: Automatic timestamp updates
- **Partitioning**: Ready for future partitioning of large tables

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

### 3. Environment Variables

```bash
# Database connection
DATABASE_URL=postgresql://user:password@localhost:5432/workflow_engine

# For development
DATABASE_URL=postgresql://localhost:5432/workflow_engine_dev

# For testing
DATABASE_URL=postgresql://localhost:5432/workflow_engine_test
```

## Data Model Relationships

### Workflow Execution Flow
```
users → workflows → workflow_executions → node_executions
                 ↓
            workflow_triggers
```

### AI Generation Flow
```
users → ai_generation_history → workflows
                              ↓
                         ai_models
```

### Integration Flow
```
users → oauth_tokens → integrations
                    ↓
               workflow_triggers
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
- Separate tables for workflow and node executions
- Detailed timing and status information
- Error tracking and retry logic

### 4. Memory Management
- Separate memory table for runtime data
- Configurable expiration policies
- Support for different memory types

## Maintenance

### Regular Tasks

1. **Cleanup Old Executions**
```sql
DELETE FROM workflow_executions 
WHERE created_at < NOW() - INTERVAL '30 days';
```

2. **Vacuum and Analyze**
```sql
VACUUM ANALYZE;
```

3. **Index Maintenance**
```sql
REINDEX DATABASE workflow_engine;
```

### Monitoring Queries

1. **Active Executions**
```sql
SELECT status, COUNT(*) 
FROM workflow_executions 
WHERE status IN ('NEW', 'RUNNING', 'WAITING')
GROUP BY status;
```

2. **Execution Performance**
```sql
SELECT 
    AVG(end_time - start_time) as avg_duration,
    COUNT(*) as total_executions
FROM workflow_executions 
WHERE status = 'SUCCESS' 
AND start_time IS NOT NULL 
AND end_time IS NOT NULL;
```

3. **Storage Usage**
```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## Migration Strategy

### Version Control
- All schema changes through Alembic migrations
- Backwards compatibility for data migrations
- Rollback procedures for each migration

### Deployment Process
1. Backup current database
2. Run migrations in staging
3. Validate data integrity
4. Deploy to production
5. Monitor for issues

## Security Considerations

### Data Protection
- Encrypted storage for sensitive credentials
- Row-level security for multi-tenant scenarios
- Audit logging for sensitive operations

### Access Control
- Principle of least privilege
- Role-based access control
- Connection encryption (SSL/TLS)

## Troubleshooting

### Common Issues

1. **Migration Failures**
   - Check for data conflicts
   - Verify constraint violations
   - Review migration logs

2. **Performance Issues**
   - Analyze query plans
   - Check index usage
   - Monitor connection pools

3. **Data Integrity**
   - Validate foreign key constraints
   - Check JSON schema validation
   - Verify protobuf compatibility

### Support Tools
- Database monitoring dashboard
- Query performance analyzer
- Automated backup verification
- Health check endpoints

## Future Enhancements

### Planned Features
- Table partitioning for large datasets
- Read replicas for scaling
- Advanced indexing strategies
- Automated performance tuning

### Scalability Considerations
- Horizontal partitioning strategies
- Caching layer integration
- Connection pooling optimization
- Query optimization guidelines 