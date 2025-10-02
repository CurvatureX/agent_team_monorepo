# Workflow Engine V2 - Comprehensive Logging System

A modern, user-focused workflow execution engine with comprehensive logging that integrates seamlessly with the API Gateway's user-friendly logs endpoint system.

## 🎯 Overview

This system provides **detailed workflow execution progress tracking** with user-friendly messages that highlight:
- **Which node is running** with clear step indicators (e.g., "Step 2/5: Message Analyzer")
- **Input parameters** with concise summaries (e.g., "Processing: message: 'Hello world!'")
- **Output parameters** with result summaries (e.g., "Result: sentiment: 'positive', confidence: 0.8")
- **Performance metrics** with execution times (e.g., "completed in 1.2s")
- **Progress milestones** for important workflow events
- **Real-time streaming** for live monitoring

## 🏗️ Architecture

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│   Modern Engine     │────▶│ User-Friendly       │────▶│   API Gateway       │
│                     │     │ Logger              │     │                     │
│ - Node Tracking     │     │                     │     │ /api/v1/app/        │
│ - Progress Steps    │     │ - Milestone Logs    │     │ executions/{id}/    │
│ - Input/Output      │     │ - Progress Updates  │     │ logs                │
│ - Performance       │     │ - Supabase Storage  │     │                     │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
           │                           │                           │
           │                           │                           │
           ▼                           ▼                           ▼
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│   V2 Logs API       │     │   Real-time Stream  │     │   Frontend Display  │
│                     │     │                     │     │                     │
│ /api/v2/workflows/  │     │ - SSE Streaming     │     │ - Progress Bars     │
│ executions/{id}/    │     │ - Live Updates      │     │ - Step Indicators   │
│ logs                │     │ - Event Publishing  │     │ - Error Messages    │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
```

## 🚀 Quick Start

### 1. Start the Engine
```bash
cd apps/backend/workflow_engine_v2
python main.py
```

### 2. Execute a Workflow
```python
from workflow_engine_v2.core.engine import ExecutionEngine

# Create engine with user-friendly logging enabled
engine = ExecutionEngine(enable_user_friendly_logging=True)

# Execute workflow (async)
execution = await engine.execute_workflow(workflow, trigger)

# Or execute synchronously
execution = engine.run(workflow, trigger)
```

### 3. View Logs via API
```bash
# Get logs (used by API Gateway)
GET /api/v2/workflows/executions/{execution_id}/logs

# Stream real-time logs
GET /api/v2/executions/{execution_id}/logs/stream
```

### 4. Frontend Integration
The logs are automatically available through the API Gateway at:
```
GET /api/v1/app/executions/{execution_id}/logs
```

## 📋 Log Format Examples

### Workflow Start
```json
{
  "user_friendly_message": "🚀 Started workflow: Slack Sentiment Analysis - 4 steps to execute",
  "event_type": "workflow_started",
  "is_milestone": true,
  "step_number": 0,
  "total_steps": 4
}
```

### Node Execution
```json
{
  "user_friendly_message": "⚡ Step 2/4: Message Analyzer (ChatGPT AI) - Processing: message: 'Hello world!'",
  "event_type": "step_started",
  "node_id": "ai_001",
  "node_name": "Message Analyzer",
  "step_number": 2,
  "total_steps": 4
}
```

### Node Completion
```json
{
  "user_friendly_message": "✅ Step 2/4: Message Analyzer completed (1333ms) - Result: sentiment: 'positive', confidence: 0.8",
  "event_type": "step_completed",
  "duration_ms": 1333.2,
  "output_summary": "sentiment: 'positive', confidence: 0.8"
}
```

### Human Interaction
```json
{
  "user_friendly_message": "👤 Human Review: Please approve the sentiment analysis (timeout: 30min)",
  "event_type": "human_interaction",
  "interaction_type": "approval",
  "timeout_minutes": 30
}
```

## 🧩 Key Components

### 1. Modern Execution Engine (`core/modern_engine.py`)
- Streamlined workflow execution without backward compatibility
- Comprehensive logging at every step
- Error handling with clear user messages
- Performance tracking

### 2. User-Friendly Logger (`services/user_friendly_logger.py`)
- Creates user-friendly log messages with emojis and clear descriptions
- Tracks workflow progress through steps
- Summarizes input/output parameters
- Direct Supabase integration

### 3. Logs API Endpoints (`api/logs_endpoints.py`)
FastAPI endpoints that serve logs to the API Gateway

### 4. FastAPI Application (`main.py`)
- Modern FastAPI server on port 8002
- Workflow execution endpoint
- Health checks and monitoring

## 💻 Usage Examples

### Basic Workflow Execution
```python
import asyncio
from workflow_engine_v2.core.engine import ExecutionEngine

async def run_workflow():
    # Create engine with user-friendly logging
    engine = ExecutionEngine(enable_user_friendly_logging=True)

    execution = await engine.execute_workflow(
        workflow=my_workflow,
        trigger=my_trigger,
        trace_id="demo_001"
    )
    print(f"Execution {execution.execution_id} completed: {execution.status}")

asyncio.run(run_workflow())
```

### Custom Milestone Logging
```python
engine.log_milestone(
    execution_id="abc123",
    message="Data validation completed",
    user_message="✅ Validated 1,250 customer records",
    data={"validated_count": 1250, "errors": 0}
)
```

### API Integration
```python
import httpx

# Get logs via API (this is what API Gateway calls)
async with httpx.AsyncClient() as client:
    response = await client.get(
        f"http://localhost:8002/api/v2/workflows/executions/{execution_id}/logs"
    )
    logs_data = response.json()
```

## 🧪 Testing & Development

### Run Demo
```bash
cd apps/backend/workflow_engine_v2
python examples/demo_comprehensive_logging.py
```

### Start Development Server
```bash
python main.py
# Server starts on http://localhost:8002
```

## 🔧 Configuration

### Environment Variables
```bash
# Supabase (required for log storage)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SECRET_KEY=your-secret-key

# Server configuration
HOST=0.0.0.0
PORT=8002
```

## 🎨 Frontend Integration

The logs are designed to be frontend-friendly with:
- User-friendly messages with emojis
- Step tracking (1/4, 2/4, etc.)
- Performance metrics
- Real-time streaming support
- Milestone tracking

Example React component:
```tsx
function ExecutionLogs({ executionId }) {
    const [logs, setLogs] = useState([]);

    useEffect(() => {
        fetch(`/api/v1/app/executions/${executionId}/logs`)
            .then(res => res.json())
            .then(data => setLogs(data.logs));
    }, [executionId]);

    return (
        <div className="execution-logs">
            {logs.map(log => (
                <div key={log.id} className={`log-entry ${log.level}`}>
                    <div className="message">{log.user_friendly_message}</div>
                    {log.step_number && (
                        <div className="progress">
                            Step {log.step_number} of {log.total_steps}
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
}
```

---

**Version**: 2.0.0
**Status**: Production Ready
**Integration**: API Gateway `/api/v1/app/executions/{execution_id}/logs`
**Real-time**: SSE streaming support
**Storage**: Supabase PostgreSQL
