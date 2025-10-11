# Workflow Execution Log API Technical Design

## 1. Executive Summary

### Purpose
The Workflow Execution Log API provides comprehensive logging capabilities for AI-powered workflow executions, serving both technical debugging needs and user-friendly progress tracking.

### Key Features
- **Dual-Purpose Logging**: Technical debugging logs and user-friendly business logs in unified storage
- **Real-time Streaming**: Server-Sent Events (SSE) for live execution monitoring
- **REST API**: Historical log queries with advanced filtering and pagination
- **High Performance**: Optimized database indexes and connection pooling for sub-second response times

### Technology Stack
- **Backend**: FastAPI (Python 3.11+) with asyncio
- **Database**: PostgreSQL (Supabase) with Row Level Security (RLS)
- **Transport**: HTTP/REST + SSE streaming
- **Client**: httpx with HTTP/2 and connection pooling

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────┐        ┌─────────────────────┐        ┌──────────────────────┐
│   Frontend Client   │───────▶│   API Gateway       │───────▶│  Workflow Engine V2  │
│   (React/Next.js)   │  HTTPS │   (Port 8000)       │  HTTP  │   (Port 8002)        │
└─────────────────────┘        └─────────────────────┘        └──────────────────────┘
         │                              │                                │
         │ SSE Stream                   │ JWT Auth                       │ Direct Query
         │                              │                                │
         ▼                              ▼                                ▼
┌─────────────────────┐        ┌─────────────────────┐        ┌──────────────────────┐
│  SSE Event Stream   │        │  Supabase Auth      │        │  Supabase PostgreSQL │
│  Real-time Logs     │        │  JWT Verification   │        │  workflow_execution  │
└─────────────────────┘        └─────────────────────┘        │  _logs (RLS)         │
                                                                └──────────────────────┘
```

### 2.2 Component Architecture

**API Gateway (Port 8000)**:
- Endpoint: `/api/v1/app/executions/{execution_id}/logs`
- Endpoint: `/api/v1/app/executions/{execution_id}/logs/stream`
- Authentication: Supabase JWT token validation
- Function: Request routing, SSE streaming, token forwarding

**Workflow Engine V2 (Port 8002)**:
- Endpoint: `/v2/workflows/executions/{execution_id}/logs`
- Endpoint: `/v2/executions/{execution_id}/logs/stream`
- Authentication: Bearer token (optional for RLS)
- Function: Database queries, log formatting, SSE generation

### 2.3 Data Flow

**Log Creation Flow**:
```
Workflow Execution → User Friendly Logger → Supabase workflow_execution_logs table
         ↓
   Business logs (user-friendly_message, display_priority, is_milestone)
   Technical logs (stack_trace, technical_details, performance_metrics)
```

**Log Query Flow**:
```
Frontend Request → API Gateway → Workflow Engine V2 → Supabase (RLS enforced)
         ↓
   JWT token forwarded for user access control
         ↓
   Filtered logs returned (user can only see their own workflow logs)
```

## 3. Data Architecture

### 3.1 Database Schema

**Table**: `workflow_execution_logs`

```sql
CREATE TABLE workflow_execution_logs (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Execution reference
    execution_id VARCHAR(255) NOT NULL,

    -- Log categorization
    log_category VARCHAR(20) NOT NULL DEFAULT 'technical',

    -- Core log content
    event_type log_event_type_enum NOT NULL,
    level log_level_enum NOT NULL DEFAULT 'INFO',
    message TEXT NOT NULL,

    -- Structured data
    data JSONB DEFAULT '{}',

    -- Node context
    node_id VARCHAR(255),
    node_name VARCHAR(255),
    node_type VARCHAR(100),

    -- Progress tracking
    step_number INTEGER,
    total_steps INTEGER,
    progress_percentage DECIMAL(5,2),
    duration_seconds INTEGER,

    -- User-friendly display
    user_friendly_message TEXT,
    display_priority INTEGER NOT NULL DEFAULT 5,
    is_milestone BOOLEAN NOT NULL DEFAULT FALSE,

    -- Technical debugging
    technical_details JSONB DEFAULT '{}',
    stack_trace TEXT,
    performance_metrics JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Enums**:
- `log_level_enum`: DEBUG, INFO, WARNING, ERROR, CRITICAL
- `log_event_type_enum`: workflow_started, workflow_completed, workflow_progress, step_started, step_input, step_output, step_completed, step_error, separator

### 3.2 Indexes for Performance

**Single Column Indexes**:
- `idx_execution_logs_execution_id` - Primary query filter
- `idx_execution_logs_category` - Log category filtering
- `idx_execution_logs_event_type` - Event type filtering
- `idx_execution_logs_level` - Log level filtering
- `idx_execution_logs_priority` - Display priority sorting
- `idx_execution_logs_milestone` - Milestone filtering
- `idx_execution_logs_created_at` - Time-based ordering

**Composite Indexes**:
```sql
-- Business logs query optimization
CREATE INDEX idx_execution_logs_business_query
ON workflow_execution_logs(execution_id, log_category, display_priority)
WHERE log_category = 'business';

-- Technical logs query optimization
CREATE INDEX idx_execution_logs_technical_query
ON workflow_execution_logs(execution_id, log_category, level)
WHERE log_category = 'technical';

-- Milestone tracking optimization
CREATE INDEX idx_execution_logs_milestones
ON workflow_execution_logs(execution_id, is_milestone, display_priority)
WHERE is_milestone = TRUE;

-- Recent logs query optimization (30-day window)
CREATE INDEX idx_execution_logs_recent
ON workflow_execution_logs(execution_id, created_at, log_category)
WHERE created_at >= NOW() - INTERVAL '30 days';
```

### 3.3 Row Level Security (RLS)

**Policy 1: User Access**
```sql
-- Users can only view logs from their own workflow executions
CREATE POLICY "Users can view their own execution logs" ON workflow_execution_logs
FOR SELECT USING (
    EXISTS (
        SELECT 1
        FROM workflow_executions we
        JOIN workflows w ON w.id = we.workflow_id
        WHERE we.execution_id = workflow_execution_logs.execution_id
        AND w.user_id = auth.uid()
    )
);
```

**Policy 2: Service Access**
```sql
-- Only service role can insert/update logs
CREATE POLICY "Service can insert execution logs" ON workflow_execution_logs
FOR INSERT WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "Service can update execution logs" ON workflow_execution_logs
FOR UPDATE USING (auth.role() = 'service_role');
```

## 4. API Implementation Details

### 4.1 REST API for Historical Logs

#### Endpoint: GET /api/v1/app/executions/{execution_id}/logs

**API Gateway Implementation** (`api-gateway/app/api/app/executions.py`):
```python
@router.get("/executions/{execution_id}/logs")
async def get_execution_logs(
    execution_id: str,
    limit: int = 100,
    offset: int = 0,
    level: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    deps: AuthenticatedDeps = Depends(),
):
    """
    Get execution logs (static API endpoint)

    Args:
        execution_id: The execution ID to get logs for
        limit: Maximum number of logs to return (default: 100)
        offset: Number of logs to skip (default: 0)
        level: Filter by log level (optional)
        start_time: Filter logs after this time (optional)
        end_time: Filter logs before this time (optional)
    """
```

**Workflow Engine V2 Implementation** (`workflow_engine_v2/api/v2/logs.py`):
```python
@router.get("/workflows/executions/{execution_id}/logs")
async def get_execution_logs(
    execution_id: str = PathParam(...),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    level: Optional[str] = Query(None),
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
):
    """Get execution logs with filtering and pagination"""

    # Extract access token for RLS
    access_token = None
    if authorization and authorization.startswith("Bearer "):
        access_token = authorization[7:]

    # Query Supabase with RLS enforcement
    query = (
        supabase.table("workflow_execution_logs")
        .select("*")
        .eq("execution_id", execution_id)
        .order("created_at", desc=False)
    )

    # Apply filters
    if level:
        query = query.eq("level", level.upper())
    if start_time:
        query = query.gte("created_at", start_time)
    if end_time:
        query = query.lte("created_at", end_time)

    # Apply pagination
    query = query.range(offset, offset + limit - 1)

    response = query.execute()
    logs = response.data or []

    # Format for frontend
    formatted_logs = [
        {
            "id": log.get("id"),
            "timestamp": log.get("created_at"),
            "node_name": log.get("node_name"),
            "event_type": log.get("event_type", "log"),
            "message": log.get("user_friendly_message") or log.get("message"),
            "level": log.get("level", "info").lower(),
            "data": log.get("data", {}),
        }
        for log in logs
    ]

    return {
        "execution_id": execution_id,
        "logs": formatted_logs,
        "total_count": total_count,
        "pagination": {
            "limit": limit,
            "offset": offset,
            "has_more": total_count > offset + len(formatted_logs),
        },
    }
```

#### Request Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| execution_id | string | Yes | - | Unique execution identifier |
| limit | integer | No | 100 | Maximum logs to return (1-1000) |
| offset | integer | No | 0 | Number of logs to skip for pagination |
| level | string | No | - | Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| start_time | string | No | - | ISO 8601 timestamp for start time filter |
| end_time | string | No | - | ISO 8601 timestamp for end time filter |

#### Response Format

```typescript
interface LogsResponse {
  execution_id: string;
  logs: LogEntry[];
  total_count: number;
  pagination: PaginationInfo;
}

interface LogEntry {
  id: string;                    // Unique log entry ID
  timestamp: string;             // ISO 8601 timestamp
  node_name?: string;            // Node name if applicable
  event_type: string;            // workflow_started, step_completed, etc.
  message: string;               // User-friendly message or technical message
  level: string;                 // debug, info, warning, error, critical
  data: Record<string, any>;     // Additional structured data

  // Optional fields
  node_id?: string;
  node_type?: string;
  step_number?: number;
  total_steps?: number;
  display_priority?: number;
  is_milestone?: boolean;
}

interface PaginationInfo {
  limit: number;        // Requested page size
  offset: number;       // Current offset
  has_more: boolean;    // Whether more logs exist
}
```

#### Example Request

```bash
# Get first 50 logs
curl -X GET "http://localhost:8000/api/v1/app/executions/exec-123/logs?limit=50&offset=0" \
  -H "Authorization: Bearer <jwt_token>"

# Get error logs only
curl -X GET "http://localhost:8000/api/v1/app/executions/exec-123/logs?level=ERROR" \
  -H "Authorization: Bearer <jwt_token>"

# Get logs within time range
curl -X GET "http://localhost:8000/api/v1/app/executions/exec-123/logs?start_time=2025-01-10T00:00:00Z&end_time=2025-01-10T23:59:59Z" \
  -H "Authorization: Bearer <jwt_token>"
```

### 4.2 SSE Streaming API for Real-time Logs

#### Endpoint: GET /api/v1/app/executions/{execution_id}/logs/stream

**API Gateway SSE Implementation** (`api-gateway/app/api/app/executions.py`):
```python
@router.get("/executions/{execution_id}/logs/stream")
async def stream_execution_logs(
    execution_id: str,
    follow: bool = True,
    sse_deps: SSEDeps = Depends()
) -> StreamingResponse:
    """
    Stream execution logs in real-time via Server-Sent Events (SSE)

    - If execution is RUNNING: streams logs in real-time via database polling every 1 second
    - If execution is FINISHED: returns all logs from database
    - Auto-detects execution status
    """

    async def log_stream():
        """Generate SSE events for execution logs"""
        try:
            # Use SSEDeps for authentication (supports both header and URL param)
            token = sse_deps.access_token
            user = sse_deps.current_user

            # Get HTTP client
            http_client = await get_workflow_engine_client()

            # Check execution status
            execution_status_data = await http_client.get_execution_status(execution_id)
            execution_status = execution_status_data.get("status", "UNKNOWN")
            is_running = execution_status in ["NEW", "RUNNING", "WAITING_FOR_HUMAN", "PAUSED"]

            # Track sent log IDs to avoid duplicates
            sent_log_ids = set()

            # Get initial logs from database
            initial_logs_response = await http_client.get_execution_logs(
                execution_id, token, {"limit": 1000, "offset": 0}
            )
            existing_logs = initial_logs_response.get("logs", [])

            # Send initial logs
            for log_entry in existing_logs:
                log_id = log_entry.get("id")
                if log_id:
                    sent_log_ids.add(log_id)

                log_event = create_sse_event(
                    event_type=SSEEventType.LOG,
                    data=format_log_entry(log_entry),
                    session_id=execution_id,
                    is_final=False,
                )
                yield format_sse_event(log_event.model_dump())
                await asyncio.sleep(0.01)

            # Real-time streaming mode: poll database while execution is running
            if is_running and follow:
                poll_interval = 1.0  # 1 second
                max_poll_duration = 3600  # 1 hour maximum
                start_time = time.time()

                while True:
                    # Check max duration
                    if time.time() - start_time > max_poll_duration:
                        break

                    # Poll database for new logs
                    new_logs_response = await http_client.get_execution_logs(
                        execution_id, token, {"limit": 100, "offset": 0}
                    )
                    new_logs = new_logs_response.get("logs", [])

                    # Send new logs that haven't been sent yet
                    for log_entry in new_logs:
                        log_id = log_entry.get("id")
                        if log_id and log_id not in sent_log_ids:
                            sent_log_ids.add(log_id)

                            log_event = create_sse_event(
                                event_type=SSEEventType.LOG,
                                data={**format_log_entry(log_entry), "is_realtime": True},
                                session_id=execution_id,
                                is_final=False,
                            )
                            yield format_sse_event(log_event.model_dump())

                    # Check if execution finished
                    status_check = await http_client.get_execution_status(execution_id)
                    current_status = status_check.get("status", "UNKNOWN")

                    if current_status not in ["NEW", "RUNNING", "WAITING_FOR_HUMAN", "PAUSED"]:
                        # Send completion event
                        completion_event = create_sse_event(
                            event_type=SSEEventType.COMPLETE,
                            data={
                                "execution_id": execution_id,
                                "status": current_status,
                                "message": "Execution completed",
                                "total_logs": len(sent_log_ids),
                            },
                            session_id=execution_id,
                            is_final=True,
                        )
                        yield format_sse_event(completion_event.model_dump())
                        break

                    await asyncio.sleep(0.1)
            else:
                # Historical mode: execution finished, send completion
                completion_event = create_sse_event(
                    event_type=SSEEventType.COMPLETE,
                    data={
                        "execution_id": execution_id,
                        "status": execution_status,
                        "message": "Historical logs retrieved",
                        "total_logs": len(sent_log_ids),
                    },
                    session_id=execution_id,
                    is_final=True,
                )
                yield format_sse_event(completion_event.model_dump())

        except Exception as e:
            # Send fatal error event
            fatal_error_event = create_sse_event(
                event_type=SSEEventType.ERROR,
                data={
                    "execution_id": execution_id,
                    "error": f"Fatal streaming error: {str(e)}",
                    "error_type": "fatal_error",
                },
                session_id=execution_id,
                is_final=True,
            )
            yield format_sse_event(fatal_error_event.model_dump())

    return create_sse_response(log_stream())
```

#### SSE Event Types

| Event Type | Description | When Emitted |
|------------|-------------|--------------|
| LOG | Individual log entry | For each log in database |
| COMPLETE | Execution finished | When workflow completes or historical mode |
| ERROR | Fatal streaming error | On exceptions during streaming |

#### SSE Event Format

```typescript
interface SSEEvent {
  event: string;           // "message" for standard SSE
  data: EventData;         // JSON payload
  id?: string;             // Optional event ID
  retry?: number;          // Optional reconnection time
}

interface EventData {
  event_type: "LOG" | "COMPLETE" | "ERROR";
  session_id: string;      // execution_id
  is_final: boolean;       // Whether this is the last event
  data: LogData | CompletionData | ErrorData;
  timestamp: string;       // ISO 8601 timestamp
}

interface LogData {
  id: string;
  timestamp: string;
  node_name?: string;
  event_type: string;
  message: string;
  level: string;
  data: Record<string, any>;
  is_realtime?: boolean;   // True if from real-time poll
}

interface CompletionData {
  execution_id: string;
  status: string;
  message: string;
  total_logs: number;
}

interface ErrorData {
  execution_id: string;
  error: string;
  error_type: string;
}
```

#### Example Client Implementation (JavaScript)

```javascript
const eventSource = new EventSource(
  `http://localhost:8000/api/v1/app/executions/${executionId}/logs/stream?access_token=${jwt_token}`
);

eventSource.addEventListener("message", (event) => {
  const data = JSON.parse(event.data);

  switch (data.event_type) {
    case "LOG":
      console.log("📝 Log:", data.data.message);
      updateLogDisplay(data.data);
      break;

    case "COMPLETE":
      console.log("✅ Execution completed:", data.data.status);
      eventSource.close();
      break;

    case "ERROR":
      console.error("❌ Streaming error:", data.data.error);
      eventSource.close();
      break;
  }
});

eventSource.addEventListener("error", (error) => {
  console.error("SSE connection error:", error);
  eventSource.close();
});
```

### 4.3 Additional API Endpoints

#### GET /api/v1/app/executions/recent_logs

**Purpose**: Get the latest execution with detailed logs for a workflow

**Parameters**:
- `workflow_id` (required): Workflow ID
- `limit` (optional, default=100): Max logs to return
- `include_all_executions` (optional, default=false): Return multiple recent executions

**Response**:
```typescript
interface RecentLogsResponse {
  workflow_id: string;
  latest_execution: {
    execution_id: string;
    status: string;
    start_time: string;
    end_time?: string;
    duration?: string;
    error_message?: string;
  };
  logs: LogEntry[];
  summary: {
    total_logs: number;
    error_count: number;
    warning_count: number;
    milestone_count: number;
  };
  other_executions?: ExecutionSummary[];  // If include_all_executions=true
  total_executions?: number;
}
```

#### GET /v2/executions/{execution_id}/logs/summary

**Purpose**: Get execution logs summary including counts and milestones

**Response**:
```typescript
interface LogsSummaryResponse {
  execution_id: string;
  total_logs: number;
  log_levels: Record<string, number>;      // { "info": 45, "error": 2 }
  event_types: Record<string, number>;     // { "step_completed": 10, "step_started": 10 }
  milestones: Milestone[];
  nodes: Record<string, NodeSummary>;
  timeline: {
    first_log: string;
    last_log: string;
    duration_estimate?: number;
  };
}

interface Milestone {
  timestamp: string;
  message: string;
  event_type: string;
}

interface NodeSummary {
  node_name: string;
  logs_count: number;
  step_number: number;
  status: "running" | "completed" | "failed";
}
```

## 5. System Interactions

### 5.1 Internal Interactions

**API Gateway ↔ Workflow Engine V2**:
- **Protocol**: HTTP/REST
- **Connection**: httpx.AsyncClient with connection pooling (10 keepalive, 20 max connections)
- **Timeouts**:
  - Connect: 5 seconds
  - Query: 60 seconds
  - Logs: 90 seconds (extended for large log queries)
- **HTTP/2**: Enabled for multiplexing

**Workflow Engine V2 ↔ Supabase**:
- **Protocol**: PostgreSQL wire protocol
- **Library**: supabase-py client
- **Authentication**: Service role key OR user JWT token
- **RLS**: Enforced when using user JWT tokens

### 5.2 External Integrations

**Frontend Client Integration**:
- **REST API**: Standard fetch() or axios calls with JWT token
- **SSE Streaming**: EventSource API with token in query parameter
- **Authentication**: Supabase JWT token in Authorization header

**Authentication Flow**:
```
1. Frontend authenticates with Supabase → receives JWT token
2. Frontend includes JWT in Authorization: Bearer <token> header
3. API Gateway validates JWT with Supabase
4. API Gateway forwards token to Workflow Engine V2
5. Workflow Engine V2 includes token when querying Supabase
6. Supabase RLS enforces user access control
```

## 6. Non-Functional Requirements

### 6.1 Performance

**Performance Targets**:
- REST API Response Time: \< 1 second (95th percentile)
- SSE Initial Connection: \< 2 seconds
- SSE Log Delivery Latency: \< 1 second from database write
- Database Query Performance: \< 500ms for 1000 logs

**Optimization Strategies**:
- Connection pooling for database and HTTP clients
- Composite indexes for common query patterns
- Partial indexes for recent logs (30-day window)
- HTTP/2 multiplexing for concurrent requests
- Limit log entry sizes (max 10KB per log)

**Caching Strategies**:
- No caching implemented currently (real-time data priority)
- Future: Redis cache for completed execution logs (5-minute TTL)

### 6.2 Scalability

**Scaling Approach**: Horizontal scaling of API Gateway and Workflow Engine V2

**Load Balancing**: AWS Application Load Balancer distributes traffic

**Resource Considerations**:
- Database connections: 10 per service instance
- HTTP connections: 20 per client instance
- Memory: ~200MB per service instance
- CPU: Asyncio event loop for high concurrency

**Capacity Limits**:
- Max concurrent SSE streams per instance: ~100
- Max logs per execution: Unlimited (paginated queries)
- Max log retention: 30 days (automatic cleanup)

### 6.3 Security

**Authentication**:
- Supabase JWT token validation at API Gateway
- Token forwarding to Workflow Engine V2
- RLS enforcement at database level

**Authorization**:
- Users can only access logs from their own workflows
- RLS policies verify workflow ownership via JOIN query
- Service role bypasses RLS for system operations

**Data Protection**:
- No sensitive data logging policy (must be enforced at application level)
- TLS/HTTPS encryption in transit
- Database encryption at rest (Supabase default)

### 6.4 Reliability

**Error Handling**:
- Graceful degradation: Return empty logs on database errors
- Retry logic: None (client should retry on connection errors)
- Timeout handling: Dedicated timeouts per operation type

**Failure Recovery**:
- SSE auto-reconnect: Client implements EventSource reconnection
- Database connection pool recovery: Automatic reconnection
- Service health checks: `/health` endpoint every 10 seconds

**Monitoring and Logging**:
- Structured logging with emoji indicators (📋, ✅, ❌, 🐛)
- Request ID tracking via `X-Request-ID` header
- Performance metrics logged for all database queries

### 6.5 Testing & Observability

#### Testing Strategy

**Unit Testing**:
- API endpoint handlers (pytest with FastAPI TestClient)
- Database query functions (pytest with pytest-asyncio)
- SSE event formatting (test event stream generation)
- RLS policy enforcement (test with different user contexts)

**Integration Testing**:
- End-to-end log creation and retrieval flow
- SSE streaming with real execution
- Authentication and authorization flows
- Database performance with large log volumes

**Test Data Management**:
- Test fixtures for sample log entries
- Mock Supabase client for unit tests
- Dedicated test database for integration tests

**Testing Automation**:
- GitHub Actions CI/CD pipeline
- Automated tests on PR and merge to main
- Coverage target: 80% for critical paths

#### Observability

**Key Metrics**:
- **Latency**: REST API response time, SSE connection time, database query time
- **Throughput**: Requests per second, logs retrieved per request
- **Error Rates**: HTTP 5xx errors, database errors, authentication failures
- **Resource Utilization**: Memory usage, CPU usage, database connections

**Logging Strategy**:
- Log Level: INFO for normal operations, DEBUG for detailed debugging
- Structured Logging: JSON format with consistent fields
- Log Aggregation: CloudWatch Logs for AWS ECS deployments

**Distributed Tracing**:
- Trace ID propagation via `X-Trace-ID` header
- OpenTelemetry integration (future enhancement)
- Correlation of logs across API Gateway and Workflow Engine V2

**Application Performance Monitoring (APM)**:
- Custom metrics: Database query performance, SSE connection count
- Health checks: `/health` endpoint for service availability
- Alerting: CloudWatch Alarms for error rate and latency

**Business Metrics and KPIs**:
- Execution log completeness: % of executions with logs
- Average logs per execution
- Most common error event types

#### Monitoring & Alerting

**Dashboard Design**:
- API Gateway request rate and latency
- Workflow Engine V2 database query performance
- SSE active connections and throughput
- Error rate trends by endpoint

**Alert Thresholds**:
- Error Rate: \> 5% of requests return 5xx errors (5-minute window)
- Latency: p95 response time \> 2 seconds (10-minute window)
- Database: Connection pool exhaustion or query timeout rate \> 1%

**SLIs and SLOs**:
- **Availability SLI**: 99.5% of requests succeed (HTTP 2xx)
- **Latency SLI**: 95% of REST API requests complete in \< 1 second
- **Streaming SLI**: 99% of SSE connections deliver logs within 1 second

**Incident Response Procedures**:
1. Alert triggered → Slack notification
2. On-call engineer investigates logs and metrics
3. Check health endpoints: `/api/v1/public/health`, `/health`
4. Review CloudWatch Logs for error patterns
5. Escalate to database team if Supabase connectivity issues
6. Post-incident: Update runbooks and improve monitoring

## 7. Technical Debt and Future Considerations

### Known Limitations
- No cursor-based pagination (only offset-based, performance degrades for large offsets)
- No client-side log caching (every request hits database)
- SSE reconnection logic is client-side only (no server-side resume)
- No log aggregation across multiple executions
- No full-text search capabilities on log messages

### Areas for Improvement
- Implement cursor-based pagination for better performance with large datasets
- Add Redis caching layer for completed execution logs (5-minute TTL)
- Implement server-side SSE resume with last event ID
- Add Elasticsearch integration for advanced log search and analytics
- Implement log compression for storage optimization
- Add batch log ingestion endpoint for high-throughput scenarios

### Planned Enhancements
- **Log Aggregation API**: Query logs across multiple executions for a workflow
- **Real-time Pub/Sub**: Replace polling with PostgreSQL LISTEN/NOTIFY for real-time log streaming
- **Log Analytics Dashboard**: Pre-aggregated statistics and trend analysis
- **Export Functionality**: Download logs in CSV/JSON format for external analysis
- **Log Retention Policies**: Configurable retention periods per workflow or user tier

### Migration Paths
- **From Polling to Pub/Sub**: Gradual rollout with feature flag, maintain polling as fallback
- **From Offset to Cursor Pagination**: Add cursor parameters while keeping offset support for backward compatibility
- **From Direct DB to Cache Layer**: Transparent caching with cache-aside pattern, no API changes required

## 8. Appendices

### A. Glossary

| Term | Definition |
|------|------------|
| **SSE** | Server-Sent Events - HTTP-based unidirectional streaming protocol |
| **RLS** | Row Level Security - PostgreSQL feature for fine-grained access control |
| **JWT** | JSON Web Token - Authentication token format used by Supabase |
| **httpx** | Modern async HTTP client library for Python |
| **Supabase** | Open-source Firebase alternative with PostgreSQL database |
| **Workflow Engine V2** | New FastAPI-based workflow execution service (replaces V1) |
| **API Gateway** | Three-layer FastAPI service (Public/App/MCP APIs) |
| **Event Type** | Categorization of log events (workflow_started, step_completed, etc.) |
| **Log Category** | Business (user-friendly) vs Technical (debugging) classification |
| **Milestone** | Important log entry marked for progress tracking (is_milestone=true) |
| **Display Priority** | Log importance ranking (1=low, 10=high) for UI filtering |

### B. References

**Internal Documentation**:
- [Workflow Engine Architecture](workflow-engine-architecure.md)
- [API Gateway Architecture](api-gateway-architecture.md)
- [New Workflow Specification](new_workflow_spec.md)
- [Node Structure](node-structure.md)

**External Resources**:
- [Server-Sent Events Specification](https://html.spec.whatwg.org/multipage/server-sent-events.html)
- [PostgreSQL Row Level Security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [httpx Documentation](https://www.python-httpx.org/)
- [Supabase Documentation](https://supabase.com/docs)

**Code Locations**:
- API Gateway logs endpoints: `apps/backend/api-gateway/app/api/app/executions.py`
- Workflow Engine V2 logs API: `apps/backend/workflow_engine_v2/api/v2/logs.py`
- HTTP client implementation: `apps/backend/api-gateway/app/services/workflow_engine_http_client.py`
- Database migration: `supabase/migrations/20250913000001_create_workflow_execution_logs.sql`

---

**Document Version**: 2.0
**Last Updated**: 2025-01-11
**Author**: Technical Design Documentation Specialist
**Status**: Current Implementation
