# Node Configuration Migration

## Problem

Previously, node configurations were stored as schema definitions instead of actual values:

```json
{
  "timeout": {
    "type": "integer",
    "default": 30,
    "description": "Execution timeout",
    "required": false
  },
  "allowed_methods": {
    "type": "array",
    "default": ["POST"],
    "description": "Allowed HTTP methods",
    "options": ["GET", "POST", "PUT"]
  }
}
```

This caused:
- Verbose and bloated workflow definitions in the database
- Confusion when debugging (seeing schemas instead of values)
- Inefficient storage and transmission

## Solution

Extract the `default` value from each configuration schema:

```json
{
  "timeout": 30,
  "allowed_methods": ["POST"]
}
```

## What Was Fixed

1. **Code Fix** (`shared/node_specs/base.py`):
   - Modified `create_node_instance()` to extract default values from configuration schemas
   - New nodes created from specs now have clean configurations

2. **Database Migration** (`migrate_node_configurations.py`):
   - Script to migrate existing workflows in the database
   - Transforms all node configurations from schema format to value format

## Running the Migration

### Prerequisites

Set environment variables:
```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SECRET_KEY="your-service-role-key"
```

### Run Migration

```bash
cd apps/backend/workflow_scheduler/utils
python migrate_node_configurations.py
```

### Expected Output

```
🔌 Connecting to Supabase: https://your-project.supabase.co
📥 Fetching workflows...
📊 Found 42 workflows
🔄 Migrating workflow abc123...
✅ Migrated workflow abc123
✅ Workflow def456: Already migrated
...
============================================================
📊 Migration complete!
   - Migrated: 38
   - Skipped: 4
   - Total: 42
============================================================
```

## Verification

After migration, check a workflow in the database:

```sql
SELECT definition->'nodes'->0->'configurations'
FROM workflows
WHERE id = 'your-workflow-id';
```

Should see:
```json
{"timeout": 30, "allowed_methods": ["POST"]}
```

Instead of:
```json
{"timeout": {"type": "integer", "default": 30, ...}}
```

## Rollback

If needed, you can rollback by:
1. Restoring from a database backup
2. Or re-running with the old code that includes schema definitions

**Important**: Back up your database before running the migration!

## Impact

- ✅ Cleaner workflow definitions
- ✅ Reduced database storage
- ✅ Faster JSON serialization/deserialization
- ✅ Easier debugging and inspection
- ✅ No breaking changes (values work the same way)
