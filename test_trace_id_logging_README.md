# Trace ID Logging Test Script

This test script verifies that all three services (api-gateway, workflow_agent, workflow_engine) are properly logging with `tracking_id` fields.

## What it tests

1. **Service Logging Structure**: Verifies that each service produces logs with the expected JSON structure including:
   - `@timestamp`
   - `@level` 
   - `@message`
   - `service`
   - `tracking_id`
   - `source`

2. **Tracking ID Consistency**: Ensures that all services use the same tracking_id for a given request trace.

3. **Telemetry Integration**: Tests the telemetry system integration when dependencies are available.

4. **Cross-Service Scenarios**: Simulates a request flowing through all three services and validates consistent tracking.

## Usage

### Basic Usage
```bash
cd /Users/bytedance/personal/feature-logs
python test_trace_id_logging.py
```

### With Dependencies (Full Test)
If you have the Python dependencies installed:
```bash
# Install dependencies first (in a virtual environment)
cd apps/backend
pip install fastapi opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi

# Run the test
cd /Users/bytedance/personal/feature-logs
python test_trace_id_logging.py
```

## Test Modes

### Mock Mode (Default)
- Runs when telemetry dependencies are not available
- Uses mock tracking IDs and formatters
- Tests the structure and consistency of logging
- All tests should pass in this mode

### Real Mode
- Runs when OpenTelemetry and FastAPI dependencies are available
- Uses actual OpenTelemetry trace IDs
- Tests real telemetry integration
- Provides more comprehensive validation

## Output

The script generates:

1. **Console Output**: Real-time test results with ✅/❌ status indicators
2. **JSON Results File**: `test_trace_id_results.json` with detailed test results

### Example Success Output
```
🚀 Starting comprehensive trace_id logging test
============================================================

🧪 Testing api-gateway logging...
   📊 Expected tracking_id: 0000009bd30a3c645943dd1690a03a14
   ✅ Mock tracking ID present (telemetry not available)
   ✅ All expected fields present
   ✅ Service name correct: api-gateway
   ✅ api-gateway logging test PASSED

... (similar for other services)

============================================================
📊 TEST SUMMARY
============================================================
api-gateway          ✅ PASS
workflow-agent       ✅ PASS  
workflow-engine      ✅ PASS
Middleware           ✅ PASS
Cross-service        ✅ PASS

OVERALL              ✅ PASS
```

## Expected Behavior

### In Each Service
The test simulates what happens when a request comes in:

1. **API Gateway**: Receives external request, generates/extracts tracking_id
2. **Workflow Agent**: Processes conversation, maintains tracking_id
3. **Workflow Engine**: Executes workflow, maintains tracking_id

### Logging Structure
Each log entry should contain:

```json
{
  "@timestamp": "2025-08-02T10:30:45Z",
  "@level": "INFO", 
  "@message": "Processing request",
  "service": "api-gateway",
  "tracking_id": "abc123def456...",
  "source": {
    "module": "test_module",
    "function": "test_function", 
    "line": 42
  },
  "request": {
    "method": "POST",
    "path": "/api/v1/test"
  },
  "user": {
    "id": "test-user-123"
  },
  "session": {
    "id": "test-session-456"
  }
}
```

## Troubleshooting

### Import Errors
If you see import errors, the script will fall back to mock mode. This is expected and the tests should still pass.

### Failed Tests
If tests fail, check:

1. **File Structure**: Ensure the script is in the correct location relative to the backend code
2. **Dependencies**: Install missing dependencies for full testing
3. **Code Changes**: Verify that the telemetry system hasn't been modified

### Common Issues

1. **Module Not Found**: Normal in environments without dependencies installed
2. **Tracking ID Mismatch**: May occur in mock mode, which is expected
3. **Missing Fields**: Indicates potential issues with log formatting

## Integration with CI/CD

This script can be integrated into automated testing:

```bash
# In CI pipeline
python test_trace_id_logging.py
if [ $? -eq 0 ]; then
    echo "Trace ID logging tests passed"
else
    echo "Trace ID logging tests failed"
    exit 1
fi
```

## Files Created

- `test_trace_id_logging.py`: Main test script
- `test_trace_id_results.json`: Detailed test results
- `test_trace_id_logging_README.md`: This documentation