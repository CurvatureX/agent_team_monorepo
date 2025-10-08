# Backend API Implementation Requirements for Codex

## Endpoint: GET /api/v1/app/executions/recent_logs

### Purpose
Return simplified execution logs/summaries for a workflow's recent executions to display in the frontend UI.

### Implementation Details

**File**: `apps/backend/api-gateway/app/api/app/executions.py`

**Location**: Add this endpoint BEFORE the existing `/workflows/{workflow_id}/executions` endpoint (around line 112)

### Request

**Method**: GET

**Path**: `/api/v1/app/executions/recent_logs`

**Query Parameters**:
- `workflow_id` (required, string): The workflow ID to get execution logs for
- `limit` (optional, integer, default=10, max=50): Number of recent logs to return

**Authentication**: Required via `AuthenticatedDeps`

### Response Format

```json
{
  "workflow_id": "uuid-string",
  "logs": [
    {
      "execution_id": "uuid-string",
      "status": "success" | "error" | "running" | "cancelled",
      "timestamp": "2025-02-04T10:30:00Z",
      "duration": "2.5s",
      "error_message": "error details if failed" | null
    }
  ],
  "total": 10
}
```

### Implementation Steps

1. **Add the endpoint function**:
   ```python
   @router.get("/executions/recent_logs")
   async def get_recent_execution_logs(
       workflow_id: str,
       limit: int = 10,
       deps: AuthenticatedDeps = Depends()
   ):
   ```

2. **Validate and clamp limit**:
   ```python
   limit = max(1, min(limit, 50))  # Clamp between 1-50
   ```

3. **Fetch execution history**:
   - Use existing `get_workflow_engine_client()` to get HTTP client
   - Call `http_client.get_execution_history(workflow_id, limit)`

4. **Transform execution data to log format**:
   ```python
   logs = []
   for execution in executions:
       log_entry = {
           "execution_id": execution.get("execution_id") or execution.get("id"),
           "status": execution.get("status"),
           "timestamp": execution.get("start_time") or execution.get("created_at"),
           "duration": format_duration(execution),  # See below
           "error_message": execution.get("error_message") or execution.get("error")
       }
       logs.append(log_entry)
   ```

5. **Duration formatting helper**:
   - If `duration_ms` exists, format as "X.Xs"
   - Otherwise calculate from `start_time` and `end_time`:
     ```python
     duration_ms = (end_time - start_time) * 1000
     duration = f"{duration_ms / 1000:.1f}s"
     ```
   - If execution is still running (no end_time), set duration to None

6. **Return response**:
   ```python
   return {
       "workflow_id": workflow_id,
       "logs": logs,
       "total": len(logs)
   }
   ```

### Error Handling

- Log all operations with appropriate emoji prefixes (📋 for info, ✅ for success, ❌ for errors)
- Return 500 status code with "Internal server error" message for exceptions
- Allow HTTPException to propagate

### Example Log Messages

```python
logger.info(f"📋 Getting recent execution logs for workflow {workflow_id} (user: {deps.current_user.sub})")
logger.info(f"✅ Retrieved {len(logs)} recent execution logs")
logger.error(f"❌ Error getting recent execution logs: {e}")
```

### Testing

After implementation, the endpoint should be accessible at:
```
GET http://localhost:8000/api/v1/app/executions/recent_logs?workflow_id=<uuid>&limit=10
```

With valid JWT token in `Authorization: Bearer <token>` header.

### Notes

- This endpoint is specifically designed for UI display, not for detailed execution analysis
- The response is intentionally simplified compared to the full execution history endpoint
- Duration formatting should be human-readable (e.g., "2.5s", "120.3s")
- Status values should match the ExecutionStatusEnum from shared models
