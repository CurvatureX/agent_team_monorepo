# Enhanced User-Friendly Logging

## Summary of Changes

I've enhanced the user-friendly logging system to display input params, output params, and error messages directly in the log messages as JSON.

## What Changed

### 1. Enhanced `log_node_start()`
- Now displays input parameters as JSON when a node starts
- Format: `Started: {node_name}\nInput: {json_object}`
- Uses `json.dumps()` for compact single-line JSON output

### 2. Enhanced `log_node_complete()`
- **Success case**: Displays output parameters as JSON
  - Format: `Completed: {node_name}\nOutput: {json_object}`
- **Failure case**: Displays error message as plain text
  - Format: `Failed: {node_name}\nError: {error_message}`

## Example Output

### Before (Old Logging)
```
1:33:45 AM [info] Started workflow: Daily_Joke_Slack_Poster (3 steps)
1:33:52 AM [info] Started: ai_agent_1
1:34:05 AM [info] Completed: ai_agent_1
1:34:11 AM [info] Started: slack_action_1
1:34:16 AM [error] Failed: slack_action_1
1:34:16 AM [error] Workflow failed (1 completed, 1 failed)
```

### After (Enhanced Logging)
```
1:33:45 AM [info] Started workflow: Daily_Joke_Slack_Poster (3 steps)

1:33:52 AM [info] Started: ai_agent_1
Input: {"prompt": "Generate a funny joke about programming"}

1:34:05 AM [info] Completed: ai_agent_1
Output: {"joke": "Why do programmers prefer dark mode? Because light attracts bugs!", "success": true}

1:34:11 AM [info] Started: slack_action_1
Input: {"channel": "#jokes", "message": "Why do programmers prefer dark mode? Because light attracts bugs!"}

1:34:16 AM [error] Failed: slack_action_1
Error: Slack API authentication failed. Missing OAuth token. Solution: Connect Slack account in integrations settings (/integrations/connect/slack)

1:34:16 AM [error] Workflow failed (1 completed, 1 failed)
```

## Technical Details

### Input Parameter Formatting
- **Location**: `user_friendly_logger.py:473-508`
- **Method**: `log_node_start()`
- **Format**: JSON string (single line)
  - Uses `json.dumps()` with `ensure_ascii=False`
  - Frontend can parse directly as JSON
  - No truncation - full object included

### Output Parameter Formatting
- **Location**: `user_friendly_logger.py:510-577`
- **Method**: `log_node_complete()`
- **Success**: Extracts `output_params` from `output_summary`
  - Converts to JSON string (single line)
  - Full object structure preserved
- **Failure**: Shows error message as plain text
  - No truncation - full error message included

### Data Preservation
- Full data still stored in `data` field for programmatic access
- Only `user_friendly_message` is enhanced for human readability
- Backend developer logs (with 🔥 emoji) remain verbose and unchanged

## Benefits

1. **Frontend-Friendly Format**: JSON output can be parsed directly by frontend
2. **Immediate Debugging**: See input/output values without clicking through UI
3. **Clear Error Messages**: Error details visible in logs, not just "Failed"
4. **Workflow Transparency**: Understand data flow between nodes with actual JSON objects
5. **Production Debugging**: Logs contain actual runtime values in parseable format
6. **No UI Changes Required**: Frontend can render JSON directly in log viewer

## Backward Compatibility

- ✅ All existing log consumers continue to work
- ✅ `data` field still contains full structured information
- ✅ Only `user_friendly_message` is enhanced
- ✅ No breaking changes to log structure

## Testing

To verify the changes work correctly:

1. Run a workflow with the Daily Joke example
2. Check the execution logs via API: `GET /api/v1/app/executions/{execution_id}/logs`
3. Verify logs show input/output params in `user_friendly_message`
4. Check that error messages are displayed when nodes fail

## Files Modified

- `apps/backend/workflow_engine_v2/services/user_friendly_logger.py`
  - Enhanced: `log_node_start()` (lines 473-508) - Added JSON input param logging
  - Enhanced: `log_node_complete()` (lines 510-577) - Added JSON output param logging

## No Changes Needed In

- `apps/backend/workflow_engine_v2/core/engine.py` - Already passes input/output params
- Database schema - Log structure unchanged
- Frontend - Will automatically display enhanced messages
- API endpoints - Same response format
