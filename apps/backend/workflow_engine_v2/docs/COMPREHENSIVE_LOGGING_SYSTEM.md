# Comprehensive Workflow Execution Logging System

## Overview

The Comprehensive Workflow Execution Logging System provides detailed tracking and monitoring of workflow execution progress, highlighting which nodes are running, their input parameters, output parameters, and performance metrics. The system offers multiple output formats and interfaces for different use cases.

## Architecture

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│   Enhanced Engine   │────▶│  Execution Logger   │────▶│   Log Formatters    │
│                     │     │                     │     │                     │
│ - Node Tracking     │     │ - Progress Tracking │     │ - Console Output    │
│ - Parameter Logging │     │ - Performance Metrics│     │ - JSON/HTML Export  │
│ - Phase Management  │     │ - Error Context     │     │ - Multiple Formats  │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
           │                           │                           │
           │                           │                           │
           ▼                           ▼                           ▼
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│   CLI Interface     │     │   API Endpoints     │     │   Real-time Stream  │
│                     │     │                     │     │                     │
│ - Interactive Mode  │     │ - RESTful API       │     │ - WebSocket Support │
│ - Export Functions  │     │ - Multiple Formats  │     │ - Live Monitoring   │
│ - Filtering Options │     │ - Download Exports  │     │ - Event Publishing  │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
```

## Key Features

### 1. **Detailed Node Execution Tracking**
- **Input Parameters**: Captures and logs all input parameters with type information
- **Output Parameters**: Records all output parameters and their values
- **Configuration**: Logs node configuration settings
- **Execution Phases**: Tracks node through different execution phases
- **Performance Metrics**: Measures execution time, memory usage, and other metrics
- **Error Context**: Provides detailed error information with stack traces

### 2. **Multiple Output Formats**
- **Console**: Colored terminal output with symbols and indentation
- **JSON**: Structured data for API consumption
- **HTML**: Rich web format with styling and interactive elements
- **Markdown**: Documentation-friendly format
- **CSV**: Data analysis and spreadsheet import
- **Table**: ASCII table format for structured display

### 3. **Real-time Progress Monitoring**
- **Phase Tracking**: Monitor nodes as they progress through execution phases
- **Live Updates**: Real-time streaming of execution progress
- **Performance Metrics**: Live performance monitoring
- **Error Notifications**: Immediate error alerts

### 4. **Comprehensive Filtering**
- **By Execution ID**: Filter logs for specific workflow executions
- **By Node ID**: Focus on specific node execution
- **By Log Level**: Filter by severity (TRACE, DEBUG, INFO, PROGRESS, WARNING, ERROR, CRITICAL)
- **By Time Range**: Filter logs within specific time periods
- **By Phase**: Filter by node execution phase

## Components

### Core Components

#### 1. ExecutionLogger
**Location**: `workflow_engine_v2/services/execution_logger.py`

Primary logging component that provides:
- Node execution context tracking
- Progress phase management
- Parameter logging with sanitization
- Performance metrics collection
- Error context capture

```python
from workflow_engine_v2.services.execution_logger import get_execution_logger

logger = get_execution_logger()

# Log node start
context = logger.log_node_start(
    node=node,
    execution_id=execution_id,
    workflow_id=workflow_id,
    input_parameters={"user_id": "123", "action": "process"},
    configuration={"timeout": 30, "retries": 3}
)

# Log phase changes
logger.log_node_phase_change(
    node_id=node.id,
    phase=NodeExecutionPhase.PROCESSING,
    details={"stage": "data_validation"}
)

# Log completion
logger.log_node_complete(
    node_id=node.id,
    phase=NodeExecutionPhase.COMPLETED,
    output_parameters={"result": "success", "records_processed": 150},
    performance_metrics={"execution_time_ms": 1250, "memory_mb": 45.2}
)
```

#### 2. Log Formatters
**Location**: `workflow_engine_v2/services/log_formatters.py`

Provides multiple output formats:

```python
from workflow_engine_v2.services.log_formatters import LogFormatterFactory, OutputFormat

# Create formatter
formatter = LogFormatterFactory.create(OutputFormat.CONSOLE_DETAILED)

# Format logs
formatted_logs = formatter.format_entries(log_entries)
print(formatted_logs)
```

#### 3. Enhanced Logging Service
**Location**: `workflow_engine_v2/services/enhanced_logging_service.py`

High-level service that integrates all components:

```python
from workflow_engine_v2.services.enhanced_logging_service import get_enhanced_logging_service

service = get_enhanced_logging_service()

# Track node execution with context manager
async with service.track_node_execution(
    node=node,
    execution=execution,
    input_parameters=inputs,
    configuration=config
) as context:
    # Execute node logic here
    result = await execute_node_logic()
    return result

# Get formatted logs
logs = service.get_execution_logs(
    execution_id="abc123",
    format_type=OutputFormat.HTML
)
```

#### 4. Enhanced Execution Engine
**Location**: `workflow_engine_v2/core/enhanced_engine.py`

Extended engine with comprehensive logging:

```python
from workflow_engine_v2.core.enhanced_engine import EnhancedExecutionEngine

engine = EnhancedExecutionEngine()

# Run workflow with enhanced logging
execution = engine.run(workflow, trigger, trace_id="trace123")

# Get execution summary
summary = engine.get_execution_summary(
    execution.execution_id,
    format_type=OutputFormat.CONSOLE
)
print(summary)
```

### Interface Components

#### 1. CLI Tool
**Location**: `workflow_engine_v2/cli/log_manager.py`

Command-line interface for log management:

```bash
# View execution logs
python -m workflow_engine_v2.cli.log_manager logs --execution-id abc123 --format console_detailed

# Get execution summary
python -m workflow_engine_v2.cli.log_manager summary --execution-id abc123 --format json_pretty

# Export logs to HTML
python -m workflow_engine_v2.cli.log_manager export --execution-id abc123 --output report.html --format html

# Interactive mode
python -m workflow_engine_v2.cli.log_manager interactive --execution-id abc123
```

#### 2. API Endpoints
**Location**: `workflow_engine_v2/api/logging_endpoints.py`

RESTful API for log access:

```bash
# Get execution logs
GET /api/v2/executions/{execution_id}/logs?format=console&node_id=node_001

# Get execution summary
GET /api/v2/executions/{execution_id}/summary?format=json_pretty

# Get node details
GET /api/v2/executions/{execution_id}/nodes/{node_id}/details

# Export logs
POST /api/v2/executions/{execution_id}/export
{
  "format": "html",
  "include_summary": true
}

# List available formats
GET /api/v2/logging/formats
```

## Node Execution Phases

The system tracks nodes through the following execution phases:

1. **QUEUED** - Node is queued for execution
2. **STARTING** - Node execution is starting
3. **VALIDATING_INPUTS** - Validating input parameters
4. **PROCESSING** - Main processing logic
5. **WAITING_HUMAN** - Waiting for human input (HIL nodes)
6. **COMPLETING** - Finalizing execution
7. **COMPLETED** - Successfully completed
8. **FAILED** - Failed with error
9. **TIMEOUT** - Execution timed out

## Log Levels

The system supports enhanced log levels:

- **TRACE** - Detailed internal operations
- **DEBUG** - Debugging information
- **INFO** - General information
- **PROGRESS** - Execution progress updates
- **WARNING** - Non-critical issues
- **ERROR** - Error conditions
- **CRITICAL** - Critical failures

## Usage Examples

### 1. Basic Logging with Enhanced Engine

```python
from workflow_engine_v2.core.enhanced_engine import EnhancedExecutionEngine
from workflow_engine_v2.services.log_formatters import OutputFormat

# Create enhanced engine
engine = EnhancedExecutionEngine()

# Execute workflow
execution = engine.run(workflow, trigger)

# Print execution summary
engine.print_execution_summary(execution.execution_id, detailed=True)

# Print detailed logs
engine.print_execution_logs(execution.execution_id, detailed=True)

# Export to HTML report
engine.export_execution_logs(
    execution_id=execution.execution_id,
    file_path="execution_report.html",
    format_type=OutputFormat.HTML
)
```

### 2. Manual Node Tracking

```python
from workflow_engine_v2.services.enhanced_logging_service import get_enhanced_logging_service
from workflow_engine_v2.services.execution_logger import NodeExecutionPhase

service = get_enhanced_logging_service()

# Track node execution manually
async def execute_custom_node(node, execution, inputs, config):
    async with service.track_node_execution(
        node=node,
        execution=execution,
        input_parameters=inputs,
        configuration=config
    ) as context:

        # Phase: Input validation
        service.update_node_phase(
            node_id=node.id,
            phase=NodeExecutionPhase.VALIDATING_INPUTS,
            details={"validation_rules": len(config.get("rules", []))}
        )

        # Validate inputs
        validated_inputs = validate_inputs(inputs, config)

        # Phase: Processing
        service.update_node_phase(
            node_id=node.id,
            phase=NodeExecutionPhase.PROCESSING,
            details={"processing_mode": config.get("mode", "default")}
        )

        # Execute core logic
        results = await process_data(validated_inputs)

        # Log intermediate results
        service.log_custom(
            level=ExecutionLogLevel.DEBUG,
            message=f"Processed {len(results)} items",
            execution_id=execution.execution_id,
            node_id=node.id,
            structured_data={"item_count": len(results)}
        )

        return results
```

### 3. API Integration

```python
import requests

# Get execution logs via API
response = requests.get(
    f"/api/v2/executions/{execution_id}/logs",
    params={
        "format": "json_pretty",
        "node_id": "my_node_001",
        "level": "ERROR"
    }
)

logs = response.json()
print(logs["data"]["content"])

# Export logs
export_response = requests.post(
    f"/api/v2/executions/{execution_id}/export",
    json={
        "format": "html",
        "include_summary": true
    }
)

# Save exported file
with open("execution_report.html", "wb") as f:
    f.write(export_response.content)
```

### 4. CLI Usage

```bash
# Interactive exploration
python -m workflow_engine_v2.cli.log_manager interactive

# Command sequence in interactive mode:
> load abc123-def456-789
> summary console
> logs console_detailed
> node my_node_001 json_pretty
> formats

# Batch operations
python -m workflow_engine_v2.cli.log_manager logs \
    --execution-id abc123-def456-789 \
    --format console_detailed \
    --node-id critical_node \
    --level ERROR

# Export comprehensive report
python -m workflow_engine_v2.cli.log_manager export \
    --execution-id abc123-def456-789 \
    --output comprehensive_report.html \
    --format html
```

## Output Format Examples

### Console Format
```
🚀 WORKFLOW EXECUTION: abc123...

  📦 NODE: User_Validation (AI_AGENT.OPENAI_CHATGPT)
      [12:34:56.123] PROGRESS  ⏳ Node execution started: User_Validation (AI_AGENT.OPENAI_CHATGPT)
      [12:34:56.124] DEBUG     ✅ Node phase changed: User_Validation -> VALIDATING_INPUTS
      [12:34:56.125] DEBUG     ⚡ Node phase changed: User_Validation -> PROCESSING
      [12:34:56.890] PROGRESS  ✅ Node execution completed: User_Validation (took 767.2ms)

  📦 NODE: Data_Processing (ACTION.HTTP_REQUEST)
      [12:34:57.001] PROGRESS  ⏳ Node execution started: Data_Processing (ACTION.HTTP_REQUEST)
      [12:34:57.002] DEBUG     ✅ Node phase changed: Data_Processing -> VALIDATING_INPUTS
      [12:34:57.003] DEBUG     ⚡ Node phase changed: Data_Processing -> PROCESSING
      [12:34:57.445] PROGRESS  ✅ Node execution completed: Data_Processing (took 444.1ms)

=== EXECUTION SUMMARY ===
Execution ID: abc123...
Total Logs: 24

Node Statistics:
  Total Nodes: 5
  ✓ Completed: 5
  ✗ Failed: 0
  ⏳ In Progress: 0

Performance:
  Total Duration: 1211.3ms
  Average Node: 242.3ms
  Fastest Node: 123.4ms
  Slowest Node: 767.2ms
```

### JSON Pretty Format
```json
{
  "execution_id": "abc123-def456-789",
  "total_logs": 24,
  "node_statistics": {
    "total_nodes": 5,
    "completed_nodes": 5,
    "failed_nodes": 0,
    "in_progress_nodes": 0
  },
  "performance": {
    "total_duration_ms": 1211.3,
    "average_node_duration_ms": 242.3,
    "fastest_node_ms": 123.4,
    "slowest_node_ms": 767.2
  },
  "timestamp": 1706441232.123
}
```

### HTML Format (excerpt)
```html
<div class="workflow-logs">
    <div class="execution-header">🚀 EXECUTION: abc123...</div>

    <div class="node-header">📦 User_Validation (AI_AGENT.OPENAI_CHATGPT)</div>
    <div class="log-entry PROGRESS">
        <span class="timestamp">[12:34:56.123]</span>
        PROGRESS  Node execution started: User_Validation ⏳
    </div>
    <div class="node-context">
        <div>📥 Inputs: <pre>{"user_id": "123", "validation_rules": ["email", "age"]}</pre></div>
        <div>📤 Outputs: <pre>{"valid": true, "score": 0.95}</pre></div>
    </div>
</div>
```

## Performance Considerations

### Memory Management
- Log entries are stored in bounded deques to prevent memory leaks
- Automatic cleanup of old entries
- Parameter sanitization to remove sensitive data
- JSON serialization validation

### Storage Options
- **In-Memory**: Fast access, limited by available RAM
- **Redis**: Persistent caching with TTL support
- **Supabase**: Long-term storage with query capabilities
- **File Export**: Local file storage for archival

### Scalability
- Thread-safe operations with proper locking
- Async-compatible interfaces
- Background processing for exports
- Streaming support for large result sets

## Integration Guide

### 1. Replace Existing Engine
```python
# Old approach
from workflow_engine_v2.core.engine import ExecutionEngine

# New approach
from workflow_engine_v2.core.enhanced_engine import EnhancedExecutionEngine

# Drop-in replacement with enhanced logging
engine = EnhancedExecutionEngine()
execution = engine.run(workflow, trigger)
```

### 2. Add to Existing FastAPI App
```python
from fastapi import FastAPI
from workflow_engine_v2.api.logging_endpoints import router

app = FastAPI()
app.include_router(router, prefix="/workflow")

# Endpoints will be available at:
# /workflow/api/v2/executions/{execution_id}/logs
# /workflow/api/v2/executions/{execution_id}/summary
# etc.
```

### 3. Custom Integration
```python
from workflow_engine_v2.services.enhanced_logging_service import get_enhanced_logging_service

# Use in your own workflow system
service = get_enhanced_logging_service()

async def my_workflow_executor(workflow, trigger):
    execution = create_execution(workflow, trigger)

    service.log_workflow_start(execution, trigger)

    for node in workflow.nodes:
        async with service.track_node_execution(
            node=node,
            execution=execution,
            input_parameters=get_inputs(node)
        ) as context:
            result = await execute_node(node, context)

    service.log_workflow_complete(execution, ExecutionStatus.COMPLETED)
    return execution
```

## Configuration

### Environment Variables
```bash
# Redis configuration (optional)
REDIS_URL=redis://localhost:6379/1

# Supabase configuration (optional)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SECRET_KEY=your-secret-key

# Logging configuration
MAX_LOG_ENTRIES=10000
LOG_RETENTION_HOURS=24
ENABLE_PARAMETER_LOGGING=true
ENABLE_PERFORMANCE_METRICS=true
```

### Service Configuration
```python
from workflow_engine_v2.services.execution_logger import ExecutionLogger

# Custom logger configuration
logger = ExecutionLogger(
    max_entries=5000,  # Maximum log entries to keep in memory
    enable_performance_metrics=True,
    enable_parameter_sanitization=True
)
```

## Troubleshooting

### Common Issues

1. **High Memory Usage**
   - Reduce `max_entries` in ExecutionLogger
   - Enable log rotation
   - Use Redis for caching instead of in-memory storage

2. **Slow Performance**
   - Disable detailed parameter logging for large parameters
   - Use background tasks for exports
   - Implement log level filtering

3. **Missing Logs**
   - Check that enhanced engine is being used
   - Verify trace IDs are being passed correctly
   - Ensure proper error handling in tracking contexts

### Debug Mode
```python
import logging

# Enable debug logging
logging.getLogger("workflow_execution").setLevel(logging.DEBUG)

# Enable trace-level logging
from workflow_engine_v2.services.execution_logger import ExecutionLogLevel

logger.log_custom(
    level=ExecutionLogLevel.TRACE,
    message="Debug information",
    execution_id=execution_id,
    structured_data={"debug_info": "value"}
)
```

## Future Enhancements

- **WebSocket Streaming**: Real-time log streaming for web interfaces
- **Metrics Integration**: Prometheus metrics export
- **Advanced Filtering**: Complex query language for log filtering
- **Log Aggregation**: Multi-execution log analysis
- **Performance Profiling**: Detailed performance profiling and bottleneck detection
- **Custom Formatters**: Plugin system for custom output formats
- **Log Retention Policies**: Automatic cleanup and archival
- **Distributed Tracing**: Integration with OpenTelemetry for distributed tracing

---

**Version**: 2.0.0
**Last Updated**: January 28, 2025
**Status**: Production Ready
