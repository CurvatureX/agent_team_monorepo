# Workflow Data Migration Guide

## Overview

This guide explains how to migrate existing workflow records from the old format to align with the latest data model defined in `shared/models/workflow_new.py` and `shared/node_specs/`.

## Why Migrate?

The workflow data model has been updated to:

1. **Cleaner structure**: Removed legacy fields (`disabled`, `notes`, `webhooks`, `credentials`, `retry_policy`, `type_version`, `on_error`)
2. **Better semantics**: Renamed `parameters` → `configurations` to align with node specification terminology
3. **Enhanced runtime support**: Added explicit `input_params` and `output_params` for runtime data flow
4. **Standardized connections**: Flat connection list with proper `output_key` based routing instead of nested structure
5. **Complete metadata**: Full WorkflowMetadata conforming to the specification
6. **Type safety**: All fields validated against Pydantic models and node specifications

## Key Changes

### Node Structure

**Old Format:**
```json
{
  "id": "node_id",
  "name": "Node Name",
  "type": "TRIGGER",
  "subtype": "SLACK",
  "parameters": {...},
  "disabled": false,
  "on_error": "continue",
  "notes": {},
  "webhooks": [],
  "credentials": {},
  "retry_policy": null,
  "type_version": 1,
  "position": {"x": 100, "y": 100}
}
```

**New Format:**
```json
{
  "id": "node_id",
  "name": "Node_Name",  // Note: Spaces replaced with underscores
  "description": "Node description",
  "type": "TRIGGER",
  "subtype": "SLACK",
  "configurations": {...},  // Renamed from "parameters"
  "input_params": {...},     // NEW: Runtime input data
  "output_params": {...},    // NEW: Runtime output data
  "position": {"x": 100, "y": 100}
}
```

### Connection Structure

**Old Format:**
```json
{
  "source_node": {
    "connection_types": {
      "main": {
        "connections": [
          {"node": "target_node", "type": "main", "index": 0}
        ]
      },
      "true": {
        "connections": [
          {"node": "another_node", "type": "main", "index": 0}
        ]
      }
    }
  }
}
```

**New Format:**
```json
[
  {
    "id": "conn_1",
    "from_node": "source_node",
    "to_node": "target_node",
    "output_key": "result",  // "main" mapped to "result"
    "conversion_function": "def convert(input_data: Dict[str, Any]) -> Dict[str, Any]: return input_data"
  },
  {
    "id": "conn_2",
    "from_node": "source_node",
    "to_node": "another_node",
    "output_key": "true",    // Conditional output keys preserved
    "conversion_function": "def convert(input_data: Dict[str, Any]) -> Dict[str, Any]: return input_data"
  }
]
```

### Workflow Metadata

The migration creates a complete `WorkflowMetadata` object with all required fields:

- `id`, `name`, `description`
- `deployment_status` (from existing field)
- `created_time`, `created_by`, `updated_by`
- `tags`, `icon_url`
- `statistics` (WorkflowStatistics object)
- `version`, `parent_workflow`

### Triggers

The migration automatically identifies all nodes with `type: "TRIGGER"` and populates the `triggers` array with their IDs.

## Migration Script Usage

### Prerequisites

1. Set environment variables:
   ```bash
   export SUPABASE_URL="https://your-project.supabase.co"
   export SUPABASE_SECRET_KEY="your-service-role-key"
   ```

2. Install required dependencies:
   ```bash
   cd apps/backend
   pip install -r requirements.txt
   # or if using uv
   uv sync
   ```

### Dry Run (Recommended First Step)

Preview changes without applying them:

```bash
cd apps/backend
python scripts/migrate_workflows.py --dry-run --limit 5 --verbose
```

This will:
- Fetch up to 5 workflows
- Show detailed migration logs
- **Not** modify the database

### Migrate Specific Workflow

Test migration on a specific workflow:

```bash
python scripts/migrate_workflows.py --dry-run --workflow-id <uuid>
```

### Execute Migration

**⚠️ WARNING: This will modify your database. Make a backup first!**

Migrate all workflows:

```bash
python scripts/migrate_workflows.py --execute
```

Migrate with limits:

```bash
python scripts/migrate_workflows.py --execute --limit 10
```

The script will:
1. Ask for confirmation before proceeding
2. Fetch workflows from database
3. Migrate each workflow's data structure
4. Update `workflow_data` field in database
5. Update `updated_at` timestamp
6. Report migration statistics

### Command Line Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Preview changes without applying (default: True) |
| `--execute` | Execute the migration (overrides --dry-run) |
| `--workflow-id <uuid>` | Migrate a specific workflow by ID |
| `--limit <n>` | Limit the number of workflows to migrate |
| `--verbose` or `-v` | Enable verbose debug logging |

### Example Workflow

```bash
# 1. Test on one workflow first
python scripts/migrate_workflows.py --dry-run --limit 1 --verbose

# 2. If successful, test on 10 workflows
python scripts/migrate_workflows.py --dry-run --limit 10

# 3. Backup your database
pg_dump $DATABASE_URL > backup_workflows_$(date +%Y%m%d).sql

# 4. Execute migration on small batch
python scripts/migrate_workflows.py --execute --limit 10

# 5. Verify results in database
# Check workflow_data structure manually

# 6. Execute full migration
python scripts/migrate_workflows.py --execute
```

## Migration Logic Details

### Node Migration

For each node, the script:

1. **Looks up node specification** from `NODE_SPECS_REGISTRY` using `type.subtype`
2. **Extracts description** from node spec or generates default
3. **Migrates parameters** → `configurations`
4. **Derives default runtime params** from node spec:
   - Uses `default_input_params`/`default_output_params` if available
   - Otherwise derives from `input_params`/`output_params` schema
5. **Sanitizes node name** by replacing spaces with underscores
6. **Validates** against the Node Pydantic model

### Connection Migration

For each connection:

1. **Flattens nested structure** to flat list
2. **Maps connection types**:
   - `"main"` → `output_key: "result"`
   - `"true"`, `"false"`, etc. → preserved as-is (for conditional nodes)
3. **Generates connection IDs** (`conn_1`, `conn_2`, ...)
4. **Adds default passthrough conversion function**
5. **Validates** source and target nodes exist

### Workflow-Level Migration

1. **Builds WorkflowMetadata** from existing workflow record fields
2. **Identifies triggers** automatically (nodes with type `TRIGGER`)
3. **Validates** complete Workflow object with Pydantic
4. **Converts to JSON** for storage in `workflow_data` field

## Validation & Error Handling

The migration script:

- ✅ Validates each node against its node specification
- ✅ Validates connections reference existing nodes
- ✅ Validates complete Workflow object structure
- ✅ Logs detailed error messages for debugging
- ✅ Continues processing on individual node failures
- ✅ Reports migration statistics (success/failed/skipped)
- ✅ Preserves original data on validation failures

## Post-Migration Verification

After migration, verify:

1. **Workflow count** matches pre-migration count
2. **Node count** in each workflow is preserved
3. **Connection count** is correct
4. **Trigger identification** is accurate
5. **Configurations** are properly migrated from parameters

### SQL Verification Queries

```sql
-- Check total workflows
SELECT COUNT(*) FROM workflows;

-- Check workflow structure (should see new format)
SELECT
    id,
    name,
    jsonb_pretty(workflow_data->'metadata') as metadata,
    jsonb_array_length(workflow_data->'nodes') as node_count,
    jsonb_array_length(workflow_data->'connections') as connection_count,
    jsonb_array_length(workflow_data->'triggers') as trigger_count
FROM workflows
LIMIT 5;

-- Check for nodes with old fields (should be empty after migration)
SELECT
    w.id,
    w.name,
    node->>'id' as node_id,
    node->>'name' as node_name
FROM workflows w,
     jsonb_array_elements(w.workflow_data->'nodes') as node
WHERE node ? 'parameters'  -- Old field
   OR node ? 'disabled'
   OR node ? 'on_error'
LIMIT 10;

-- Check for new required fields (should have data)
SELECT
    w.id,
    w.name,
    node->>'id' as node_id,
    node->>'name' as node_name,
    node ? 'configurations' as has_configurations,
    node ? 'description' as has_description,
    node ? 'input_params' as has_input_params,
    node ? 'output_params' as has_output_params
FROM workflows w,
     jsonb_array_elements(w.workflow_data->'nodes') as node
LIMIT 10;

-- Check connection format (should be array, not nested object)
SELECT
    id,
    name,
    jsonb_typeof(workflow_data->'connections') as connections_type,
    jsonb_array_length(workflow_data->'connections') as connection_count
FROM workflows
LIMIT 10;
```

## Rollback Procedure

If you need to rollback:

```bash
# Restore from backup
psql $DATABASE_URL < backup_workflows_YYYYMMDD.sql
```

## Troubleshooting

### Common Issues

**Issue**: `No node spec found for TYPE.SUBTYPE`

**Solution**: This is a warning. The migration will use a default description. The node will still be migrated successfully.

---

**Issue**: `Validation error: 节点名称不可包含空格`

**Solution**: This is handled automatically. The script replaces spaces with underscores in node names.

---

**Issue**: `Failed to migrate node ... in workflow ...`

**Solution**: Check the verbose logs (`--verbose`) for specific validation errors. The workflow will be skipped if critical nodes fail migration.

---

**Issue**: `No valid nodes after migration`

**Solution**: All nodes failed validation. Check logs for specific errors. May indicate a node spec mismatch or data corruption.

---

**Issue**: Database connection errors

**Solution**: Verify `SUPABASE_URL` and `SUPABASE_SECRET_KEY` environment variables are correctly set.

## Support

For issues or questions:

1. Check verbose logs with `--verbose` flag
2. Review the [Node Specifications](../shared/node_specs/)
3. Review the [Workflow Models](../shared/models/workflow_new.py)
4. Contact the development team

## Migration Status Tracking

Create a tracking spreadsheet or table:

| Batch | Date | Workflows | Success | Failed | Notes |
|-------|------|-----------|---------|--------|-------|
| 1     | 2025-10-02 | 10 | 10 | 0 | Test batch |
| 2     | 2025-10-02 | 100 | 98 | 2 | Node spec missing for 2 custom nodes |
| ...   | ... | ... | ... | ... | ... |

## Best Practices

1. **Always run dry-run first** on a small sample
2. **Backup database** before executing migration
3. **Migrate in batches** (start with limit 10, then 100, then all)
4. **Monitor logs** for errors and warnings
5. **Verify results** with SQL queries after each batch
6. **Test workflow execution** after migration to ensure functionality
7. **Keep migration logs** for audit trail

## Timeline Recommendation

For large deployments:

- **Week 1**: Test migration on dev/staging environment
- **Week 2**: Migrate 10% of production workflows, monitor
- **Week 3**: Migrate remaining 90% in batches of 100-500
- **Week 4**: Verification and cleanup

## Additional Notes

- The migration is **idempotent**: running it multiple times on the same workflow will produce the same result
- The script uses Supabase client library for database access
- Migration preserves all workflow IDs and relationships
- The script updates `updated_at` timestamp on successful migration
- Original workflow metadata (user_id, created_at, etc.) is preserved
