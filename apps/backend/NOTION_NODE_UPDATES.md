# Notion Node Implementation Updates

This document summarizes the updates made to align Notion node implementations with the updated specifications.

## Updated Date
2025-10-05

## Updated Files

### 1. Node Specifications

#### `/apps/backend/shared/node_specs/TOOL/NOTION_MCP_TOOL.py`
**Changes:**
- Added `operation_type` configuration parameter
  - Type: `string`
  - Options: `["database", "page", "both"]`
  - Default: `"database"`
  - Description: Specifies whether the tool operates on databases, pages, or both

- Added `default_page_id` configuration parameter
  - Type: `string`
  - Description: Default page ID for page operations (when operation_type is "page" or "both")

- Enhanced `default_database_id` description
  - Now explicitly mentions usage when operation_type is "database" or "both"

- Updated examples to include operation_type:
  - "Create Notion Database Entry" example uses `operation_type: "database"`
  - "Query Notion Database" example uses `operation_type: "database"`
  - Added new "Update Notion Page" example demonstrating `operation_type: "page"` with `default_page_id`

#### `/apps/backend/shared/node_specs/EXTERNAL_ACTION/NOTION.py`
**Changes:**
- Added `operation_type` configuration parameter (same as MCP tool)

- Added `database_id` configuration parameter
  - Type: `string`
  - Description: Target database ID (when operation_type is "database" or "both")
  - Replaces nested `database_config.database_id` for direct access

- Added `page_id` configuration parameter
  - Type: `string`
  - Description: Target page ID (when operation_type is "page" or "both")
  - New direct configuration for page operations

- Updated `database_config` structure
  - Removed `database_id` from nested object (now top-level)
  - Kept as optional metadata for database creation operations

- Enhanced `system_prompt_appendix` with configuration guidelines:
  ```
  - Set `operation_type` to "database" for database operations (query, create items, etc.)
  - Set `operation_type` to "page" for page operations (update content, get page info, etc.)
  - Set `operation_type` to "both" if you need to work with both pages and databases
  - For database operations, provide `database_id` in configuration
  - For page operations, provide `page_id` in configuration
  ```

### 2. Implementation Files

#### `/apps/backend/workflow_engine_v2/runners/external_actions/notion_external_action.py`

**Changes:**

1. **Configuration Extraction & Validation** (`handle_operation` method):
   - Extracts `operation_type`, `page_id`, `database_id` from node configurations
   - Validates configuration completeness:
     - Warns if `operation_type="page"` but `page_id` is missing
     - Warns if `operation_type="database"` but `database_id` is missing
     - Warns if `operation_type="both"` but neither `page_id` nor `database_id` configured
     - Info logs if `operation_type="both"` but only one ID is configured
   - Logs operation type in execution start message

2. **AI Context Enhancement** (`_build_ai_context` method):
   - Adds new `configuration` section to AI context containing:
     - `operation_type`
     - `page_id`
     - `database_id`
   - AI can now reference these configurations when making decisions

3. **AI Prompt Updates** (`_get_ai_decision` method):
   - Added **Node Configuration** section to user message:
     ```
     **Node Configuration:**
     - Operation Type: {operation_type}
     - Page ID: {page_id if page_id else "(not configured)"}
     - Database ID: {database_id if database_id else "(not configured)"}
     ```
   - Added **Configuration Guidance** section:
     ```
     - When operation_type is "page": Use the configured page_id for page operations
     - When operation_type is "database": Use the configured database_id for database operations
     - When operation_type is "both": You can use either page_id or database_id as needed
     ```

#### `/apps/backend/workflow_engine_v2/runners/tool.py`

**Changes:**

1. **Configuration Extraction** (`run` method):
   - Extracts from node configurations:
     - `operation_type`
     - `default_page_id`
     - `default_database_id`
     - `notion_integration_token`

2. **Auto-Population of Tool Arguments**:
   - For Notion MCP tools (tool names starting with `notion_`):
     - Auto-adds `integration_token` if configured and not already in args
     - Auto-adds `page_id` if `operation_type="page"` and `default_page_id` configured
     - Auto-adds `database_id` if `operation_type="database"` and `default_database_id` configured
     - Auto-adds BOTH `page_id` and `database_id` if `operation_type="both"` and both are configured
   - Logs enrichment details for debugging

3. **Benefits**:
   - Reduces verbosity in AI agent tool calls
   - AI doesn't need to repeatedly specify page_id/database_id
   - Configuration-driven behavior aligned with node specs

## Configuration Mapping

### NOTION_MCP_TOOL vs NOTION External Action

| Configuration Field | NOTION_MCP_TOOL | NOTION External Action |
|-------------------|-----------------|----------------------|
| Operation Type | `operation_type` | `operation_type` |
| Page ID | `default_page_id` | `page_id` |
| Database ID | `default_database_id` | `database_id` |
| Token | `notion_integration_token` | `notion_token` |

## Updated Workflow Example

See `/apps/backend/enriched_workflow.json` for a complete example workflow using:
- Real Slack credentials (`bot_token`)
- Real Notion credentials (`notion_integration_token` / `notion_token`)
- Proper `operation_type: "page"` configuration
- Configured `page_id: "27f0b1df-411b-80ac-aa54-c4cba158a1f9"` (Test page)

## Key Improvements

1. **Clear Page vs Database Distinction**: Users explicitly declare whether they're working with pages or databases via `operation_type`

2. **Reduced Configuration Complexity**: Direct `page_id` and `database_id` fields instead of nested objects

3. **AI Guidance**: System prompts and context now include configuration awareness, helping AI make better decisions

4. **Auto-Population**: Tool runner automatically enriches MCP tool calls with configured IDs, reducing redundancy

5. **Validation & Warnings**: Runtime validation warns when configuration is incomplete for the specified operation type

6. **Backwards Compatible**: Still supports AI discovering resources when IDs are not configured (with warnings)

## Testing Recommendations

1. **Page Operations**:
   - Set `operation_type: "page"`
   - Configure `page_id` or `default_page_id`
   - Test: Get page, update page, append blocks, retrieve block children

2. **Database Operations**:
   - Set `operation_type: "database"`
   - Configure `database_id` or `default_database_id`
   - Test: Query database, create database item, retrieve database schema

3. **Mixed Operations (Both)**:
   - Set `operation_type: "both"`
   - Configure both `page_id` and `database_id`
   - **Behavior**: Both IDs are auto-populated in tool calls, AI chooses which to use
   - **Use Cases**:
     - Read from page, write to database
     - Query database, update page with summary
     - Cross-reference content between page and database
   - Test workflows that interact with both resources seamlessly
   - See: `/apps/backend/notion_both_example.json` for detailed examples

4. **Partial Configuration (Both)**:
   - Set `operation_type: "both"`
   - Configure only `page_id` OR only `database_id`
   - **Behavior**: Configured ID is auto-populated, other operations require discovery
   - **Validation**: Info log indicates which operations will need discovery
   - Test: Workflows that primarily use one resource but occasionally need the other

5. **Auto-Discovery Mode**:
   - Set `operation_type` but leave IDs empty
   - Verify warnings appear in logs
   - Test AI's ability to discover resources via search

## Migration Guide for Existing Workflows

### From Old Configuration:
```json
{
  "database_config": {
    "database_id": "db_123"
  }
}
```

### To New Configuration:
```json
{
  "operation_type": "database",
  "database_id": "db_123",
  "database_config": {
    "title": "",
    "description": "",
    "properties": {}
  }
}
```

### For Page Operations:
```json
{
  "operation_type": "page",
  "page_id": "27f0b1df-411b-80ac-aa54-c4cba158a1f9",
  "page_config": {
    "properties": {},
    "children": []
  }
}
```

### For Both Page and Database Operations:
```json
{
  "operation_type": "both",
  "page_id": "27f0b1df-411b-80ac-aa54-c4cba158a1f9",
  "database_id": "27c0b1df-411b-81fa-ac40-ca8f7b697a0b",
  "page_config": {
    "properties": {},
    "children": []
  },
  "database_config": {
    "title": "",
    "description": "",
    "properties": {}
  }
}
```

**Note**: With `operation_type: "both"`, the AI can seamlessly switch between page and database operations. Both IDs are auto-populated in tool calls, and the AI determines which to use based on the operation being performed.

## Related Documentation

- Node Specification: `apps/backend/shared/node_specs/TOOL/NOTION_MCP_TOOL.py`
- Node Specification: `apps/backend/shared/node_specs/EXTERNAL_ACTION/NOTION.py`
- Example Workflow (Page Mode): `apps/backend/enriched_workflow.json`
- Example Workflow (Both Mode): `apps/backend/notion_both_example.json`
- Implementation: `apps/backend/workflow_engine_v2/runners/external_actions/notion_external_action.py`
- Implementation: `apps/backend/workflow_engine_v2/runners/tool.py`
