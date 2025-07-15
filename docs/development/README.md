# Development Guide

This document provides essential development guidance for the agent team monorepo, including database management with Supabase CLI.

## Database Management with Supabase CLI

### Schema Source of Truth

**⚠️ Important**: The **single source of truth** for database schema is the **`supabase/migrations/`** directory.

**Schema Management Strategy:**
- **Primary Source**: `supabase/migrations/*.sql` - Sequential migration files
- **Seed Data**: `supabase/seed.sql` - Initial data for development/testing
- **Configuration**: `supabase/config.toml` - Supabase project configuration

**Why Migrations Are Source of Truth:**
- **Version Control**: Each change is tracked and reversible
- **Team Collaboration**: Prevents conflicts and ensures consistency
- **Deployment Safety**: Incremental changes reduce risk
- **Environment Parity**: Same migrations run in dev, staging, and production

### Schema File Structure

```
supabase/
├── migrations/          # 🔴 SOURCE OF TRUTH
│   ├── 20250715000001_initial_schema.sql
│   ├── 20250716000001_add_user_preferences.sql
│   └── 20250717000001_add_workflow_templates.sql
├── seed.sql            # Initial data for development/testing
├── config.toml         # Supabase configuration
└── .env               # Environment variables (not in version control)
```

## Database Management with Supabase CLI

### Prerequisites

1. **Install Supabase CLI**
   ```bash
   npm install -g @supabase/cli
   ```

2. **Docker Desktop** (for local development)
   - Download and install from [Docker Desktop](https://docs.docker.com/desktop/)
   - Ensure Docker is running before using local Supabase

3. **Environment Setup**
   - Ensure `.env` file exists in `/supabase/` directory with connection details
   - Project should be linked to remote Supabase instance

### Initial Setup

1. **Link to Remote Project**
   ```bash
   cd supabase/
   supabase link --project-ref mkrczzgjeduruwxpanbj
   ```

2. **Start Local Development Environment**
   ```bash
   supabase start
   ```

3. **Check Status**
   ```bash
   supabase status
   ```

### Migration Management

#### Understanding Migrations

Migrations are SQL files that define incremental changes to your database schema. They should be:
- **Incremental**: Each migration builds upon the previous one
- **Reversible**: Include both UP and DOWN operations when possible
- **Timestamped**: Named with timestamp prefix for proper ordering

#### Creating New Migrations

1. **Generate Migration File**
   ```bash
   supabase migration new migration_name
   ```
   This creates a new file in `supabase/migrations/` with timestamp prefix.

2. **Edit Migration File**
   - Add your SQL changes (CREATE TABLE, ALTER TABLE, etc.)
   - Include appropriate constraints and indexes
   - Add comments explaining the changes

3. **Example Migration Structure**
   ```sql
   -- Description: Add user preferences table
   -- Created: 2025-01-15

   -- Create user_preferences table
   CREATE TABLE user_preferences (
       id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
       user_id UUID REFERENCES users(id) ON DELETE CASCADE,
       preferences JSONB NOT NULL DEFAULT '{}',
       created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
       updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
   );

   -- Add indexes
   CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);

   -- Add trigger for updated_at
   CREATE TRIGGER update_user_preferences_updated_at
       BEFORE UPDATE ON user_preferences
       FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
   ```

#### Applying Migrations

1. **Local Development**
   ```bash
   # Reset local database (applies all migrations)
   supabase db reset

   # Or apply specific migration
   supabase migration up
   ```

2. **Remote Database**
   ```bash
   # Push all pending migrations to remote
   supabase db push

   # Or push using connection string
   supabase db push --db-url "postgresql://postgres:password@host:port/db"
   ```

#### Migration Best Practices

1. **Always Test Locally First**
   ```bash
   # Test migration locally
   supabase db reset
   # Verify everything works
   # Then push to remote
   supabase db push
   ```

2. **Backup Before Major Changes**
   ```bash
   # Create backup before applying
   pg_dump "connection_string" > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

3. **Review Migration History**
   ```bash
   # List applied migrations
   supabase migration list --linked
   ```

### Schema Change Workflow

#### Standard Workflow for Schema Changes

1. **Create New Migration**
   ```bash
   supabase migration new add_feature_x
   ```

2. **Edit Migration File**
   - Edit the generated file in `supabase/migrations/`
   - Add your SQL changes (CREATE TABLE, ALTER TABLE, etc.)
   - Include appropriate constraints and indexes
   - Add comments explaining the changes

3. **Test Locally**
   ```bash
   supabase db reset
   ```

4. **Verify Changes**
   ```bash
   # Check tables
   supabase db diff

   # Or connect to local database
   psql "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
   ```

5. **Push to Remote**
   ```bash
   supabase db push
   ```

#### Emergency Schema Export

If you need to export the current schema for backup or documentation:

```bash
# Export complete schema
supabase db dump --schema-only > schema_backup_$(date +%Y%m%d_%H%M%S).sql

# Export with data
supabase db dump > full_backup_$(date +%Y%m%d_%H%M%S).sql
```

#### Generating Migrations from Schema Diff

1. **Generate Diff**
   ```bash
   # Compare local with remote
   supabase db diff --use-migra
   ```

2. **Save as Migration**
   ```bash
   # Save diff as new migration
   supabase db diff --use-migra > supabase/migrations/$(date +%Y%m%d%H%M%S)_schema_diff.sql
   ```

### Environment-Specific Operations

#### Local Development

```bash
# Start local environment
supabase start

# Reset database with fresh migrations
supabase db reset

# Stop local environment
supabase stop
```

#### Remote Database

```bash
# Using .env connection details
PGPASSWORD="password" psql -h host -p port -U user -d database -f migration.sql

# Using Supabase CLI
supabase db push --db-url "postgresql://user:password@host:port/database"
```

### Common Operations

#### Seed Data Management

1. **Update Seed Data**
   ```bash
   # Edit supabase/seed.sql
   # Then reset local database
   supabase db reset
   ```

2. **Apply Seed Data to Remote**
   ```bash
   PGPASSWORD="password" psql -h host -p port -U user -d database -f supabase/seed.sql
   ```

#### Database Inspection

```bash
# List all tables
psql "connection_string" -c "\dt"

# Describe table structure
psql "connection_string" -c "\d table_name"

# Check data counts
psql "connection_string" -c "SELECT COUNT(*) FROM table_name;"
```

### Troubleshooting

#### Common Issues

1. **Migration Conflicts**
   - Check migration order and dependencies
   - Verify foreign key constraints
   - Ensure data types compatibility

2. **Connection Issues**
   - Verify connection string format
   - Check firewall and network settings
   - Confirm database credentials

3. **Docker Issues**
   - Ensure Docker Desktop is running
   - Check available disk space
   - Restart Docker if containers fail

#### Debugging Commands

```bash
# Debug mode
supabase start --debug

# Check logs
supabase logs

# Inspect container health
docker ps | grep supabase
```

### Integration with Development Workflow

1. **Before Making Schema Changes**
   - Create feature branch
   - Plan migration strategy
   - Test locally first

2. **Schema Change Process**
   - Write migration file
   - Test with `supabase db reset`
   - Update seed data if needed
   - Commit migration files

3. **Deployment Process**
   - Review migrations in PR
   - Test in staging environment
   - Apply to production with `supabase db push`

### Security Considerations

1. **Connection Strings**
   - Never commit passwords to version control
   - Use environment variables or .env files
   - Rotate passwords regularly

2. **Migration Safety**
   - Always backup before major changes
   - Test migrations on staging first
   - Use transactions for complex operations

3. **Access Control**
   - Limit database access to necessary personnel
   - Use service accounts for automated deployments
   - Monitor database access logs

## Summary: Schema Management Rules

### ✅ DO:
- **Always create migrations** in `supabase/migrations/` for schema changes
- **Test migrations locally** before pushing to remote
- **Use descriptive names** for migration files
- **Include comments** in migration files explaining changes
- **Backup before major changes** to production

### ❌ DON'T:
- **Don't make schema changes** directly in the database without migrations
- **Don't skip testing** migrations locally first
- **Don't create migrations** with conflicting timestamps
- **Don't edit existing migrations** that have been applied to production

### Quick Reference Commands

```bash
# Create new migration
supabase migration new feature_name

# Test locally
supabase db reset

# Check differences
supabase db diff

# Push to remote
supabase db push

# Export schema backup
supabase db dump --schema-only > backup.sql
```

## Additional Resources

- [Supabase CLI Documentation](https://supabase.com/docs/guides/cli)
- [Migration Best Practices](https://supabase.com/docs/guides/database/migrations)
- [Local Development Guide](https://supabase.com/docs/guides/local-development)
