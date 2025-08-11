# CloudWatch Logging Configuration

## Overview
Logging configuration optimized for AWS CloudWatch in ECS deployment.

## Current Configuration

### Simple Text Format (Default)
```
INFO:     2025-08-11 14:03:25 - api-gateway - Starting service
INFO:     2025-08-11 14:03:25 - api-gateway - GET /health - 200 OK
ERROR:    2025-08-11 14:03:26 - workflow-engine - Database connection failed
```

**Benefits:**
- CloudWatch recognizes log levels automatically
- Human-readable in ECS console
- Easy to search and filter
- Similar to Uvicorn's default format

## Implementation

### File Structure
```
apps/backend/
├── api-gateway/
│   └── app/core/logging.py          # API Gateway logging config
├── workflow_agent/
│   └── core/logging.py               # Workflow Agent logging config
└── workflow_engine/
    └── workflow_engine/core/logging.py  # Workflow Engine logging config
```

### Configuration
Each service now:
1. Imports its logging configuration module
2. Calls `setup_logging()` at startup
3. Uses `simple` format by default for CloudWatch

### Environment Variables
```bash
# Set in ECS task definition or .env file
LOG_LEVEL=INFO        # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT=simple     # "simple" for text, "json" for structured
```

## Usage in Services

### API Gateway (main.py)
```python
from app.core.logging import setup_logging

# Setup logging for CloudWatch
setup_logging(
    log_level=settings.LOG_LEVEL,
    log_format="simple",  # CloudWatch-friendly format
    service_name="api-gateway"
)

logger = logging.getLogger("api-gateway")
logger.info("Starting API Gateway")
```

### Workflow Agent (main.py)
```python
from workflow_agent.core.logging import setup_logging

setup_logging(
    log_level=log_level,
    log_format="simple",
    service_name="workflow-agent"
)

logger = logging.getLogger("workflow-agent")
```

### Workflow Engine (main.py)
```python
from workflow_engine.core.logging import setup_logging

setup_logging(
    log_level=log_level,
    log_format="simple",
    service_name="workflow-engine"
)

logger = logging.getLogger("workflow-engine")
```

## CloudWatch Benefits

With this configuration:
1. **Log Levels are Recognized**: CloudWatch can filter by INFO, WARNING, ERROR
2. **Timestamps are Parsed**: Automatic time-based queries work
3. **Service Names are Clear**: Easy to identify which service logged what
4. **Uvicorn Logs Match**: Access logs and application logs have consistent format


## Deployment Checklist

- [x] Add logging.py modules to each service
- [x] Update main.py files to use new logging
- [x] Set LOG_FORMAT=simple in environment
- [x] Ensure all loggers output to stdout (not files)
- [x] Remove emoji from log messages (CloudWatch doesn't render them well)
- [x] Test locally with test_simple_logging.py

## Monitoring in AWS

Once deployed:
1. Go to CloudWatch Logs in AWS Console
2. Select your log group (e.g., `/ecs/agent-team/api-gateway`)
3. You'll see logs in the format: `INFO:     2025-08-11 14:03:25 - api-gateway - Message`
4. Use CloudWatch filters to search by level: `INFO` or `ERROR`
5. Use CloudWatch Insights for JSON format queries (if using json format)

## Notes

- Simple format is the default for all services
- All services log to stdout for CloudWatch capture
- Uvicorn access logs appear in their standard format
- No emojis in logs for better CloudWatch rendering