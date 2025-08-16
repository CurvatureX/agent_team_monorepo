# Workflow Integration Test Fix Summary

## Issue Fixed
The workflow creation and execution integration test was failing because:
1. Wrong workflow ID was being extracted (`"workflow"` instead of actual UUID)
2. Incorrect request format for workflow execution API

## Root Cause
The workflow creation response contained both:
- `id: "workflow"` - A string identifier
- `workflow_id: "ec177247-8118-4fb9-b1d4-f93e86d1ed5b"` - The actual UUID

The code was checking `event_data.get('id')` first, which returned the string `"workflow"` instead of the actual UUID.

## Solution Applied

### 1. Fixed Workflow ID Extraction
Changed the extraction order to prioritize `workflow_id` fields and exclude invalid `"workflow"` strings:

```python
created_workflow_id = (
    workflow_data.get('workflow_id') or  # Actual UUID field
    event_data.get('workflow_id') or     
    (workflow_data.get('id') if workflow_data.get('id') != 'workflow' else None) or
    (event_data.get('id') if event_data.get('id') != 'workflow' else None)
)
```

### 2. Fixed Workflow Execution Request Format
Different endpoints require different request formats:
- **API Gateway** (`/api/v1/app/workflows/{id}/execute`): Uses original test data format
- **Workflow Engine** (`/v1/workflows/{id}/execute`): Requires structured format with `workflow_id`, `user_id`, and `input_data`

```python
if "8002" in api_path:  # Direct workflow engine call
    request_data = {
        "workflow_id": workflow_id,
        "user_id": TEST_USER_EMAIL or "test_user",
        "input_data": test_data
    }
else:  # API Gateway call
    request_data = test_data
```

## Test Results
✅ All integration tests now pass successfully:
- TC001 (GitHub to Webhook): **PASS** - Creates workflow and executes successfully
- TC002 (Scheduled Task): **PASS** - Creates workflow (execution skipped as designed)
- TC003 (Slack Integration): **PASS** - Creates workflow and executes successfully

## Impact
- Workflow creation now correctly returns and uses actual UUID
- Workflow execution properly formats requests for different API endpoints
- Integration tests provide true end-to-end validation of workflow creation and execution