# Workflow Deletion Migration Guide

## Overview

This migration implements **cascading deletion** for workflows, ensuring that when a workflow is deleted, all related data across multiple tables is automatically cleaned up.

## Changes Made

### 1. Database Migration (20251007000001_add_cascade_delete_constraints.sql)

Added `ON DELETE CASCADE` foreign key constraints to tables that reference workflows:

- ✅ **trigger_index** - Trigger configurations
- ✅ **workflow_deployments** - Deployment history
- ✅ **trigger_executions** - Trigger execution logs
- ✅ **trigger_status** - Current trigger status
- ✅ **email_messages** - Email messages for triggers
- ✅ **human_interactions** - HIL interactions
- ✅ **hil_responses** - HIL response records
- ✅ **workflow_execution_logs** - Execution logs (if exists)
- ✅ **workflow_memory** - Memory records (if exists)

**Already Had CASCADE** (from initial schema):
- workflow_executions
- workflow_versions
- nodes
- node_connections

### 2. Code Changes

**File**: `apps/backend/workflow_engine_v2/services/workflow.py`

**Changed**: `delete_workflow()` function

- **Before**: Soft delete (set `active=false`)
- **After**: Hard delete (actual `DELETE` from database)
- **Effect**: Triggers CASCADE deletion automatically
- **Logging**: Now counts and logs all deleted related records

## Migration Instructions

### For Development Environment

```bash
# Navigate to the backend directory
cd apps/backend

# Apply the migration using Supabase CLI
supabase db push

# Or apply directly to your Supabase project
SUPABASE_DB_PASSWORD='your-password' ./scripts/supabase-migrate.sh check
```

### For Production Environment

```bash
# Using the migration script
SUPABASE_URL="https://your-project.supabase.co" \
SUPABASE_SECRET_KEY="your-secret-key" \
SUPABASE_DB_PASSWORD='your-password' \
./scripts/supabase-migrate.sh check

# Or using psql directly
PGPASSWORD='your-password' psql \
  "postgresql://postgres.your-project@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres" \
  -f supabase/migrations/20251007000001_add_cascade_delete_constraints.sql
```

## Breaking Changes

### ⚠️ Important: Soft Delete → Hard Delete

**BEFORE** (soft delete):
```python
# Workflow was marked as inactive but data remained
workflow.active = False  # Still in database
```

**AFTER** (hard delete):
```python
# Workflow and ALL related data is permanently deleted
# This includes:
# - All trigger configurations
# - All execution history
# - All HIL interactions
# - All deployment records
# - Everything else related to the workflow
```

### Impact on Your Code

If your application relied on:
1. **Soft-deleted workflows being recoverable** → They are now permanently deleted
2. **Accessing execution history of deleted workflows** → History is deleted with the workflow
3. **Audit trails of deleted workflows** → Consider implementing a separate audit log

### Recommended Actions

1. **Add Audit Logging** (Optional but recommended):
   ```python
   # Before deleting, optionally save to audit log
   audit_log = {
       "workflow_id": workflow_id,
       "deleted_at": datetime.now(),
       "deleted_by": user_id,
       "workflow_snapshot": workflow.model_dump()
   }
   # Save to separate audit table
   ```

2. **Implement Confirmation UI**:
   ```javascript
   // Frontend should show clear warning
   const confirmDelete = confirm(
     "⚠️ This will permanently delete the workflow and ALL related data including:\n" +
     "- Trigger configurations\n" +
     "- Execution history\n" +
     "- HIL interactions\n" +
     "- Deployment records\n\n" +
     "This action cannot be undone. Continue?"
   );
   ```

3. **Consider Archiving Instead**:
   ```python
   # If you need soft delete behavior, implement archiving
   def archive_workflow(workflow_id: str):
       # Move to archive table instead of deleting
       workflow = get_workflow(workflow_id)
       save_to_archive(workflow)
       delete_workflow(workflow_id)  # Now safe to hard delete
   ```

## Testing the Migration

### 1. Pre-Migration Test (Development)

```bash
# Create a test workflow with related data
python test_workflow_deletion.py create

# Verify all tables have data
python test_workflow_deletion.py verify-before

# Expected output:
# ✅ workflow exists
# ✅ trigger_index has 2 records
# ✅ workflow_executions has 3 records
# ✅ human_interactions has 1 record
```

### 2. Apply Migration

```bash
# Apply the CASCADE constraints
supabase db push
```

### 3. Post-Migration Test

```bash
# Delete the test workflow
python test_workflow_deletion.py delete

# Verify CASCADE deletion worked
python test_workflow_deletion.py verify-after

# Expected output:
# ❌ workflow deleted
# ❌ trigger_index has 0 records (CASCADE deleted)
# ❌ workflow_executions has 0 records (CASCADE deleted)
# ❌ human_interactions has 0 records (CASCADE deleted)
```

## Rollback Plan

If you need to rollback to soft delete behavior:

### 1. Revert Code Changes

```python
# In workflow_engine_v2/services/workflow.py
def delete_workflow(self, workflow_id: str) -> bool:
    """Soft delete - set active=false"""
    result = (
        self.supabase.table("workflows")
        .update({"active": False})
        .eq("id", workflow_id)
        .execute()
    )
    return bool(result.data)
```

### 2. Database Constraints

The CASCADE constraints can remain (they don't hurt) or remove with:

```sql
-- Only if you really need to remove them
ALTER TABLE workflow_deployments DROP CONSTRAINT IF EXISTS fk_workflow_deployments_workflow_id;
ALTER TABLE trigger_executions DROP CONSTRAINT IF EXISTS fk_trigger_executions_workflow_id;
-- etc...
```

## Verification Queries

After applying the migration, verify CASCADE constraints exist:

```sql
-- Check all foreign key constraints on workflows
SELECT
    tc.table_name,
    tc.constraint_name,
    rc.update_rule,
    rc.delete_rule
FROM information_schema.table_constraints tc
JOIN information_schema.referential_constraints rc
    ON tc.constraint_name = rc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND rc.delete_rule = 'CASCADE'
    AND tc.table_name IN (
        'trigger_index',
        'workflow_deployments',
        'trigger_executions',
        'trigger_status',
        'email_messages',
        'human_interactions',
        'hil_responses'
    )
ORDER BY tc.table_name;
```

Expected result: All tables should show `delete_rule = 'CASCADE'`

## Monitoring

After deployment, monitor:

1. **Deletion Performance**: Cascading deletes may take longer
2. **Database Locks**: Large workflows with lots of related data
3. **User Feedback**: Ensure users understand data is permanently deleted

## Support

If you encounter issues:

1. Check migration was applied: `supabase db push` or `./scripts/supabase-migrate.sh check`
2. Verify foreign key constraints exist (query above)
3. Check logs for CASCADE deletion counts
4. Review the workflow_engine_v2 service logs for deletion details

## Related Files

- Migration: `supabase/migrations/20251007000001_add_cascade_delete_constraints.sql`
- Service: `apps/backend/workflow_engine_v2/services/workflow.py` (delete_workflow function)
- API: `apps/backend/workflow_engine_v2/api/v2/workflows.py` (DELETE endpoint)
- Client: `apps/backend/api-gateway/app/services/workflow_engine_http_client.py`
