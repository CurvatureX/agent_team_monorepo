# Distributed Tracing and Observability System Technical Design

## 1. Executive Summary

### Overview
The AI Teams monorepo implements a comprehensive observability system built on OpenTelemetry, providing unified distributed tracing, metrics collection, and structured logging across all backend services. The system follows a hybrid architecture with local debugging tools (Jaeger, Prometheus) and cloud-based long-term storage and visualization (Grafana Cloud, AWS CloudWatch).

### Key Architectural Decisions
- **OpenTelemetry as the Standard**: All services use OpenTelemetry SDK for traces, metrics, and logs
- **Unified Tracking ID**: OpenTelemetry trace IDs serve as the single source of truth for request tracking (32-character hex format)
- **Zero-Configuration Propagation**: Automatic context propagation across service boundaries using W3C Trace Context standard
- **CloudWatch-Optimized Logging**: Structured JSON logs designed for AWS CloudWatch Logs Insights with nested field support
- **Hybrid Monitoring Stack**: Local tools for development/debugging, cloud services for production monitoring and long-term storage

### Technology Stack
- **Tracing**: OpenTelemetry SDK, Jaeger (local), OTLP Collector
- **Metrics**: OpenTelemetry Metrics API, Prometheus (local, 7-day retention), Grafana Cloud Mimir (long-term)
- **Logging**: Python structured logging, AWS CloudWatch Logs (production), Grafana Cloud Loki (aggregation)
- **Visualization**: Jaeger UI (local traces), Prometheus (local metrics), Grafana Cloud (unified dashboards)
- **Instrumentation**: Auto-instrumentation for FastAPI, HTTPX, Requests, PostgreSQL

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Application Services Layer                          │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐│
│  │ API Gateway  │   │  Workflow    │   │  Workflow    │   │  Workflow    ││
│  │  (Port 8000) │   │    Agent     │   │   Engine     │   │  Scheduler   ││
│  │              │   │  (Port 8001) │   │  (Port 8002) │   │  (Port 8003) ││
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘   └──────┬───────┘│
│         │                  │                  │                  │         │
│         └──────────────────┴──────────────────┴──────────────────┘         │
│                         OpenTelemetry SDK Integration                       │
│         ┌──────────────────────────────────────────────────────┐           │
│         │  - Auto-instrumentation (FastAPI, HTTPX, psycopg2)  │           │
│         │  - TrackingMiddleware (trace ID extraction)         │           │
│         │  - MetricsMiddleware (HTTP metrics collection)      │           │
│         │  - CloudWatchTracingFormatter (structured logs)     │           │
│         └──────────────────┬───────────────────────────────────┘           │
└────────────────────────────┼───────────────────────────────────────────────┘
                             │
                             ▼
         ┌──────────────────────────────────────────────────────┐
         │        OpenTelemetry Collector (Port 4317/4318)      │
         │  - Resource attribute injection (environment, project)│
         │  - Memory limiting and batch processing              │
         │  - Multi-exporter routing                            │
         └───────────┬──────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┬──────────────┬────────────────┐
         ▼                       ▼              ▼                ▼
┌─────────────────┐   ┌──────────────────┐   ┌──────────┐   ┌──────────────┐
│ Local Debugging │   │ Cloud Monitoring │   │   AWS    │   │   Grafana    │
│                 │   │                  │   │CloudWatch│   │    Cloud     │
│ • Jaeger UI     │   │ • Mimir (metrics)│   │   Logs   │   │   • Mimir    │
│   (Port 16686)  │   │ • Loki (logs)    │   │          │   │   • Loki     │
│ • Prometheus    │   │ • Grafana UI     │   │          │   │   • Grafana  │
│   (Port 9090)   │   │ • OnCall (alerts)│   │          │   │              │
└─────────────────┘   └──────────────────┘   └──────────┘   └──────────────┘
   Local Tools           Long-term Storage    Production        Unified
   (Development)         (Multi-environment)   Logging        Dashboards
```

### 2.2 Component Architecture

#### Service-Level Integration
Each backend service (API Gateway, Workflow Agent, Workflow Engine, Workflow Scheduler) integrates observability through:

1. **Telemetry SDK Initialization** (`shared/telemetry/complete_stack.py`):
   - Resource attribute configuration (service name, version, environment, project)
   - TracerProvider setup with OTLP exporter
   - MeterProvider setup with dual exporters (Prometheus + OTLP)
   - Structured logging configuration with CloudWatch formatter

2. **Auto-Instrumentation**:
   - FastAPI: Automatic span creation for all HTTP endpoints
   - HTTPX: Automatic tracing for inter-service HTTP calls
   - Requests: Automatic tracing for external API calls
   - psycopg2: Database query tracing (if PostgreSQL is used)

3. **Middleware Stack**:
   - **TrackingMiddleware**: Extracts OpenTelemetry trace ID as tracking_id, adds to request state and response headers
   - **MetricsMiddleware**: Collects HTTP request metrics (count, duration, errors, active requests)
   - **Request Logging**: Structured JSON logs with tracking_id correlation

#### OpenTelemetry Collector Pipeline
The OTLP Collector serves as the central processing and routing hub:

**Receivers:**
- OTLP gRPC (port 4317): Primary protocol for traces, metrics, logs
- OTLP HTTP (port 4318): Alternative HTTP transport

**Processors:**
- **Resource Processor**: Injects environment labels (dev/staging/prod), project identifier
- **Memory Limiter**: Prevents memory exhaustion (512MB limit)
- **Batch Processor**: Batches telemetry data for efficient export (1s timeout)

**Exporters:**
- **Jaeger**: Local trace debugging (port 14250)
- **Prometheus**: Local metrics scraping (port 8888) with environment labels
- **Grafana Cloud Mimir**: Long-term metrics storage via remote write
- **Grafana Cloud Loki**: Centralized log aggregation

**Pipelines:**
- **Traces**: OTLP → Memory Limiter → Resource → Batch → Jaeger
- **Metrics**: OTLP → Memory Limiter → Resource → Batch → Prometheus + Mimir
- **Logs**: OTLP → Memory Limiter → Resource → Batch → Loki

## 3. Data Architecture

### 3.1 Tracking ID Data Model

The system uses OpenTelemetry trace IDs as the unified tracking identifier across all observability components.

**Trace ID Format:**
- **Type**: 128-bit OpenTelemetry trace ID
- **Representation**: 32-character hexadecimal string (e.g., `4bf92f3577b34da6a3ce929d0e0e4736`)
- **Generation**: Automatic by OpenTelemetry SDK on span creation
- **Propagation**: W3C Trace Context standard via `traceparent` HTTP header

**Data Flow:**
```
HTTP Request → FastAPI Instrumentation → Span Created → Trace ID Generated
     ↓
TrackingMiddleware extracts trace_id → format(trace_id, '032x')
     ↓
Store in request.state.tracking_id (for business logic)
     ↓
Add to span attributes: span.set_attribute("tracking.id", tracking_id)
     ↓
Include in structured logs: logger.info(..., extra={"tracking_id": tracking_id})
     ↓
Return in response header: X-Tracking-ID: {tracking_id}
     ↓
Store in database records (e.g., WorkflowExecution.tracking_id)
```

**Cross-Service Propagation:**
- **Automatic**: OpenTelemetry auto-instrumentation for HTTPX/Requests propagates `traceparent` header
- **Zero Configuration**: No manual header management required in business logic
- **W3C Standard**: Compatible with all W3C Trace Context compliant systems

### 3.2 Structured Log Schema

All services emit JSON-formatted logs optimized for AWS CloudWatch Logs Insights.

**Base Log Entry Structure:**
```json
{
  "@timestamp": "2025-01-31T10:30:45.123Z",
  "@level": "INFO|WARN|ERROR|DEBUG",
  "@message": "Human readable message",
  "level": "INFO",
  "timestamp": "2025-01-31T10:30:45.123Z",
  "file": "main.py:123",
  "service": "api-gateway|workflow-agent|workflow-engine|workflow-scheduler",
  "tracking_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "source": {
    "module": "app.api.app.sessions",
    "function": "create_session",
    "line": 123,
    "filename": "sessions.py",
    "pathname": "/app/app/api/app/sessions.py"
  },
  "tracing": {
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
    "span_id": "1a2b3c4d5e6f7890"
  }
}
```

**Nested Field Groups (CloudWatch Dot-Notation Support):**

**HTTP Request Fields:**
```json
{
  "request": {
    "method": "POST",
    "path": "/api/v1/sessions",
    "size": 1024,
    "duration": 0.245,
    "user_agent": "Mozilla/5.0...",
    "ip": "192.168.1.100"
  }
}
```

**HTTP Response Fields:**
```json
{
  "response": {
    "status": 201,
    "size": 2048,
    "content_type": "application/json"
  }
}
```

**Business Context Fields:**
```json
{
  "user": {
    "id": "user_12345",
    "segment": "premium|free|enterprise"
  },
  "session": {
    "id": "session_67890",
    "duration": 1200
  },
  "workflow": {
    "id": "workflow_abc123",
    "type": "simple|complex|ai-assisted",
    "status": "running|completed|failed"
  },
  "operation": {
    "name": "create_session|execute_workflow|generate_response",
    "result": "success|failure|partial",
    "duration": 0.325
  }
}
```

**Error Fields (ERROR level only):**
```json
{
  "error": {
    "type": "ValidationError|BusinessLogicError|SystemError",
    "code": "E001|E002|E003",
    "message": "Detailed error description",
    "category": "client|server|network|timeout"
  },
  "exception": {
    "class": "ValueError",
    "message": "Invalid input format",
    "stack_trace": "Full stack trace for debugging"
  }
}
```

**Field Indexing Strategy (CloudWatch):**
- Auto-indexed: `@timestamp`, `@level`, `@message`
- Business-indexed: `tracking_id`, `service`, `request.method`, `response.status`
- Nested access: Use dot notation (e.g., `user.id`, `workflow.status`)

### 3.3 Metrics Data Model

**HTTP Infrastructure Metrics:**

| Metric Name | Type | Labels | Description |
|------------|------|--------|-------------|
| `request_count` | Counter | service_name, endpoint, method, status_code, api_version | Total HTTP request count |
| `request_duration_seconds` | Histogram | service_name, endpoint, method | Request duration distribution |
| `request_errors_total` | Counter | service_name, endpoint, method, error_type, status_code | Error count by type |
| `active_requests` | UpDownCounter | service_name, endpoint | Current active requests |

**Business Metrics:**

| Metric Name | Type | Labels | Description |
|------------|------|--------|-------------|
| `api_key_usage_total` | Counter | api_key_id, client_name, service_name, endpoint, success | API key usage tracking |
| `endpoint_usage_total` | Counter | service_name, endpoint, api_version, user_segment | Endpoint popularity |
| `user_activity_total` | Counter | user_id, activity_type, service_name, session_id | User activity events |
| `workflow_success_rate` | Histogram | workflow_type, complexity_level | Workflow execution success rate |

**AI-Specific Metrics:**

| Metric Name | Type | Labels | Description |
|------------|------|--------|-------------|
| `ai_requests_total` | Counter | model, provider, environment, tracking_id | AI model request count |
| `ai_tokens_total` | Counter | model, token_type (input/output), environment, tracking_id | Token consumption |
| `ai_cost_total` | Counter | model, environment, tracking_id | AI cost in USD |

**Standard Label Dimensions:**
- **Core Labels (all metrics)**: `service_name`, `environment` (dev/staging/prod), `project` (starmates-ai-team)
- **HTTP Labels**: `endpoint`, `method`, `status_code`, `api_version`
- **Business Labels**: `user_segment`, `client_type`, `workflow_type`

## 4. Implementation Details

### 4.1 Core Components

#### Telemetry SDK (`apps/backend/shared/telemetry/`)

**`complete_stack.py` - Unified Telemetry Setup:**
```python
def setup_telemetry(
    app: FastAPI,
    service_name: str,
    service_version: str = "1.0.0",
    otlp_endpoint: str = "http://localhost:4317",
    prometheus_port: int = 8000,
) -> None:
    """
    One-time initialization of OpenTelemetry stack for a service.

    Configures:
    - Resource attributes (service.name, service.version, deployment.environment, project)
    - TracerProvider with OTLP span exporter and batch processor
    - MeterProvider with Prometheus and OTLP metric exporters
    - Structured logging with CloudWatch formatter
    - Auto-instrumentation for FastAPI, HTTPX, Requests, psycopg2
    """
```

**Key Functions:**
- `_setup_tracing()`: Configures TracerProvider with OTLP exporter (gRPC, insecure)
- `_setup_metrics()`: Configures MeterProvider with dual exporters (Prometheus local + OTLP remote)
- `_setup_logging()`: Configures Python logging with CloudWatchTracingFormatter
- `_setup_auto_instrumentation()`: Enables automatic instrumentation for FastAPI, HTTP clients, databases

**Environment-Specific Configuration:**
- **Development**: OTLP endpoint = `http://otel-collector:4317` (Docker Compose service)
- **Production**: OTLP endpoint = `http://localhost:4317` (AWS ECS sidecar container)

#### Middleware Components (`shared/telemetry/middleware.py`)

**`TrackingMiddleware` - Unified Tracking ID Management:**
```python
class TrackingMiddleware(BaseHTTPMiddleware):
    """
    Extracts OpenTelemetry trace_id and makes it available as tracking_id.

    Responsibilities:
    1. Extract trace_id from current span context
    2. Store in request.state.tracking_id for business logic access
    3. Add to span attributes: tracking.id, http.method, http.url, user.id
    4. Return X-Tracking-ID header in response (32-char hex format)
    5. Add http.status_code and http.response.size to span attributes
    """
```

**Implementation Details:**
- **Zero Manual Propagation**: OpenTelemetry auto-instrumentation handles `traceparent` header injection/extraction
- **32-Character Format**: `format(span_context.trace_id, '032x')` converts 128-bit ID to hex string
- **Span Attribute Addition**: Enriches traces with business context (user_id, endpoint, status)
- **Fallback Handling**: Uses `"no-trace"` if span is not recording (graceful degradation)

**`MetricsMiddleware` - HTTP Metrics Collection:**
```python
class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Collects HTTP request metrics using OpenTelemetry Metrics API.

    Collected Metrics:
    - request_count (Counter): Total requests with labels (service, endpoint, method, status, version)
    - request_duration (Histogram): Duration distribution with buckets
    - active_requests (UpDownCounter): Current active requests
    - request_errors (Counter): Error count with error_type label

    Business Metrics:
    - api_key_usage (Counter): API key usage tracking
    - endpoint_usage (Counter): Endpoint popularity
    - user_activity (Counter): User activity events
    """
```

**Key Features:**
- **Endpoint Normalization**: Replaces UUIDs and numeric IDs with placeholders (`/sessions/123` → `/sessions/{id}`)
- **API Version Extraction**: Parses version from path (`/api/v1/` → `v1`)
- **Business Metrics Integration**: Conditional metrics based on request.state attributes (api_key_id, user_id)
- **Error Handling**: Graceful degradation if business metrics fail to record

#### Structured Logging (`shared/telemetry/formatter.py`)

**`CloudWatchTracingFormatter` - CloudWatch-Optimized Logging:**
```python
class CloudWatchTracingFormatter(logging.Formatter):
    """
    JSON formatter optimized for AWS CloudWatch Logs Insights.

    Features:
    1. CloudWatch-compatible field naming (@timestamp, @level, @message)
    2. Automatic tracking_id inclusion from span context
    3. Nested field grouping (request.*, response.*, user.*, error.*)
    4. ERROR-level span event creation for distributed error tracking
    5. Field count limiting (max 900 fields) to prevent CloudWatch truncation
    """
```

**Key Behaviors:**
- **Automatic Trace ID Extraction**: Falls back to current span if not in log record
- **Structured Field Grouping**: Groups related fields into nested objects for CloudWatch dot-notation queries
- **Span Event Creation**: ERROR logs automatically create OpenTelemetry span events with attributes
- **Exception Recording**: `span.record_exception()` for full stack trace capture
- **Field Limiting**: Recursively counts fields and removes non-essential fields if limit exceeded

#### Metrics Registry (`shared/telemetry/metrics.py`)

**`ServiceMetrics` - Type-Safe Metrics Collection:**
```python
@dataclass
class ServiceMetrics:
    """Strongly-typed metrics container for a service."""
    # HTTP Infrastructure Metrics
    request_count: metrics.Counter
    request_duration: metrics.Histogram
    request_errors: metrics.Counter
    active_requests: metrics.UpDownCounter

    # Business Metrics
    api_key_usage: metrics.Counter
    endpoint_usage: metrics.Counter
    user_activity: metrics.Counter

    # AI Metrics
    ai_requests: metrics.Counter
    ai_tokens: metrics.Counter
    ai_cost: metrics.Counter

    # Workflow Metrics
    workflow_success_rate: metrics.Histogram
```

**Helper Functions:**
- `get_metrics(service_name: str)`: Factory function to create all metrics for a service
- `record_ai_usage(...)`: Convenience function for AI usage tracking
- `record_workflow_execution(...)`: Convenience function for workflow metrics
- `get_standard_labels(...)`: Generates standardized label dictionaries

### 4.2 Technical Decisions

#### Decision 1: OpenTelemetry as Universal Standard
**Rationale:**
- **Vendor Neutrality**: Avoid lock-in to proprietary monitoring solutions
- **Auto-Instrumentation**: Minimal code changes for comprehensive observability
- **W3C Standard Compliance**: Trace context propagation compatible with all major tools
- **Future-Proof**: Industry-standard with broad adoption and active development

**Trade-offs:**
- **Learning Curve**: Requires understanding OpenTelemetry concepts (spans, traces, context propagation)
- **Overhead**: Additional library dependencies and runtime overhead (mitigated by batch processing)

#### Decision 2: Unified Tracking ID via Trace ID
**Rationale:**
- **Zero Duplication**: No need to generate and propagate separate tracking identifiers
- **Automatic Correlation**: Logs, metrics, and traces automatically share the same ID
- **Standards-Based**: OpenTelemetry trace IDs are globally unique and follow W3C standards
- **Reduced Complexity**: No custom ID generation or header injection logic

**Implementation:**
- Use `format(span_context.trace_id, '032x')` to convert 128-bit ID to 32-character hex string
- Store in request.state for business logic access
- Include in all log records via `extra={"tracking_id": tracking_id}`
- Return in response header as `X-Tracking-ID` for client-side correlation

#### Decision 3: CloudWatch-Optimized JSON Logging
**Rationale:**
- **Production Logging**: AWS CloudWatch Logs is the primary log aggregation service in production
- **Query Performance**: Nested field structure optimized for CloudWatch Logs Insights dot-notation queries
- **Field Indexing**: `@timestamp`, `@level`, `@message` automatically indexed by CloudWatch
- **Cost Optimization**: Field count limiting prevents expensive log truncation and over-storage

**Schema Design:**
- **Standard Fields**: `@timestamp`, `@level`, `@message` for CloudWatch compatibility
- **Nested Groups**: Group related fields (request.*, response.*, user.*, error.*) for logical organization
- **Tracing Integration**: Include `tracing.trace_id` and `tracing.span_id` for correlation
- **Field Limiting**: Recursively count fields and strip non-essential data if \> 900 fields

#### Decision 4: Hybrid Local + Cloud Architecture
**Rationale:**
- **Development Experience**: Local Jaeger and Prometheus for fast debugging without cloud dependencies
- **Cost Management**: Grafana Cloud free tier (10K metrics, 50GB logs/month) adequate for small teams
- **Production Reliability**: AWS CloudWatch for production logs with guaranteed SLA
- **Flexibility**: Easy to switch between local and cloud based on environment

**Environment Configuration:**
```yaml
Development:
  - OTLP Collector: Docker Compose service (otel-collector:4317)
  - Jaeger UI: localhost:16686
  - Prometheus: localhost:9090
  - Logs: Console output (JSON formatted)

Production (AWS ECS):
  - OTLP Collector: Sidecar container (localhost:4317)
  - Traces: Exported to Grafana Cloud via OTLP Collector
  - Metrics: Exported to Grafana Cloud Mimir + CloudWatch (for AWS alarms)
  - Logs: CloudWatch Logs (via awslogs driver)
```

#### Decision 5: Auto-Instrumentation First
**Rationale:**
- **Minimal Code Changes**: FastAPI, HTTPX, Requests, psycopg2 automatically instrumented
- **Comprehensive Coverage**: All HTTP requests, external calls, and database queries traced
- **Consistent Naming**: OpenTelemetry semantic conventions ensure consistent span naming
- **Performance**: Batch span processing minimizes overhead

**Instrumented Components:**
- **FastAPI**: All endpoints automatically create spans with HTTP semantic conventions
- **HTTPX**: Inter-service calls automatically propagate trace context
- **Requests**: External API calls traced with HTTP attributes
- **psycopg2**: Database queries traced with SQL attributes (if PostgreSQL is used)

**Manual Instrumentation Use Cases:**
- Complex business logic requiring custom span attributes
- AI model calls requiring detailed token and cost tracking
- Workflow execution state transitions

## 5. System Interactions

### 5.1 Internal Interactions

#### Service-to-Service Communication with Automatic Tracing

**Scenario**: API Gateway calls Workflow Agent for workflow generation

```python
# API Gateway (caller service)
@app.post("/api/v1/app/sessions/{session_id}/chat")
async def chat_with_session(request: Request, session_id: str, message: ChatMessage):
    # TrackingMiddleware has already extracted tracking_id from span
    tracking_id = request.state.tracking_id

    # OpenTelemetry auto-instrumentation handles trace context propagation
    response = await httpx.post(
        f"{WORKFLOW_AGENT_URL}/generate-workflow",
        json={"user_message": message.content, "session_id": session_id}
        # No manual header management - OpenTelemetry injects traceparent automatically
    )

    # Log with tracking_id for correlation
    logger.info(
        "Generated workflow from user message",
        extra={
            "tracking_id": tracking_id,
            "session_id": session_id,
            "workflow_agent_response_status": response.status_code
        }
    )

    return response.json()

# Workflow Agent (receiver service)
@app.post("/generate-workflow")
async def generate_workflow(request: Request, payload: WorkflowRequest):
    # OpenTelemetry auto-instrumentation creates child span from propagated context
    # TrackingMiddleware extracts same trace_id from child span
    tracking_id = request.state.tracking_id  # Same as caller's tracking_id!

    # Business logic with shared tracking_id
    workflow = await create_workflow_from_prompt(payload.user_message)

    # Log with same tracking_id for end-to-end correlation
    logger.info(
        "Generated workflow",
        extra={
            "tracking_id": tracking_id,
            "workflow_id": workflow.id,
            "node_count": len(workflow.nodes)
        }
    )

    return workflow
```

**Trace Context Propagation:**
```
API Gateway HTTP Request → FastAPI Instrumentation → Span Created (trace_id: 4bf92...)
    ↓
HTTPX Call to Workflow Agent → HTTPX Instrumentation → traceparent Header Injected
    ↓
Workflow Agent HTTP Request → FastAPI Instrumentation → Child Span Created (same trace_id)
    ↓
Both services log with same tracking_id (4bf92...)
```

**Jaeger UI Visualization:**
```
Trace 4bf92f3577b34da6a3ce929d0e0e4736
├─ Span: POST /api/v1/app/sessions/123/chat (api-gateway) [200ms]
│  └─ Span: POST /generate-workflow (workflow-agent) [180ms]
│     ├─ Span: create_workflow_from_prompt (workflow-agent) [150ms]
│     └─ Span: postgres.query (workflow-agent) [20ms]
```

#### Event Flow and State Management

**Workflow Execution with Distributed Tracing:**

```python
# API Gateway triggers workflow execution
@app.post("/api/v1/app/workflows/{workflow_id}/execute")
async def execute_workflow(request: Request, workflow_id: str):
    tracking_id = request.state.tracking_id

    # Call Workflow Engine with automatic trace propagation
    response = await httpx.post(
        f"{WORKFLOW_ENGINE_URL}/execute",
        json={"workflow_id": workflow_id, "tracking_id": tracking_id}
    )

    execution_id = response.json()["execution_id"]

    # Store execution record with tracking_id for correlation
    await db.workflow_executions.insert({
        "id": execution_id,
        "workflow_id": workflow_id,
        "tracking_id": tracking_id,
        "status": "RUNNING",
        "created_at": datetime.utcnow()
    })

    return {"execution_id": execution_id, "tracking_id": tracking_id}

# Workflow Engine executes nodes with span annotations
@app.post("/execute")
async def execute_workflow(request: Request, payload: ExecutionRequest):
    tracking_id = request.state.tracking_id

    # Manual span creation for business-critical operation
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("workflow_execution") as span:
        span.set_attributes({
            "tracking.id": tracking_id,
            "workflow.id": payload.workflow_id,
            "node.count": len(workflow.nodes)
        })

        for node in workflow.nodes:
            # Each node execution creates child span
            await execute_node(node, tracking_id, span)

        span.set_attribute("workflow.status", "SUCCESS")
```

**Span Hierarchy:**
```
Trace 4bf92f3577b34da6a3ce929d0e0e4736
├─ POST /api/v1/app/workflows/123/execute (api-gateway) [5000ms]
│  └─ POST /execute (workflow-engine) [4800ms]
│     └─ workflow_execution (workflow-engine) [4700ms]
│        ├─ execute_node[TRIGGER] (workflow-engine) [100ms]
│        ├─ execute_node[AI_AGENT] (workflow-engine) [3000ms]
│        │  ├─ openai.chat.completions (workflow-engine) [2800ms]
│        │  └─ store_conversation (workflow-engine) [150ms]
│        └─ execute_node[EXTERNAL_ACTION] (workflow-engine) [1500ms]
│           └─ slack.api_call (workflow-engine) [1400ms]
```

### 5.2 External Integrations

#### OpenTelemetry Collector Integration

**Configuration** (`monitoring/otel-collector-config.yml`):
```yaml
receivers:
  otlp:
    protocols:
      grpc: { endpoint: 0.0.0.0:4317 }
      http: { endpoint: 0.0.0.0:4318 }

processors:
  resource:
    attributes:
      - key: deployment.environment
        value: "${ENVIRONMENT}"  # dev, staging, prod
        action: upsert
      - key: project
        value: "starmates-ai-team"
        action: upsert
  memory_limiter: { limit_mib: 512 }
  batch: { timeout: 1s }

exporters:
  jaeger:
    endpoint: jaeger:14250
    tls: { insecure: true }

  prometheus:
    endpoint: "0.0.0.0:8888"
    const_labels:
      environment: "${ENVIRONMENT}"
      project: "starmates-ai-team"

  prometheusremotewrite/grafana-cloud:
    endpoint: "${GRAFANA_CLOUD_PROMETHEUS_URL}"
    headers:
      authorization: "Bearer ${GRAFANA_CLOUD_TENANT_ID}:${GRAFANA_CLOUD_API_KEY}"
    external_labels:
      environment: "${ENVIRONMENT}"
      project: "starmates-ai-team"

  loki/grafana-cloud:
    endpoint: "${GRAFANA_CLOUD_LOKI_URL}"
    headers:
      authorization: "Bearer ${GRAFANA_CLOUD_TENANT_ID}:${GRAFANA_CLOUD_API_KEY}"

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, resource, batch]
      exporters: [jaeger]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, resource, batch]
      exporters: [prometheus, prometheusremotewrite/grafana-cloud]
    logs:
      receivers: [otlp]
      processors: [memory_limiter, resource, batch]
      exporters: [loki/grafana-cloud]
```

**Deployment Models:**

**Development (Docker Compose):**
```yaml
# monitoring/docker-compose.monitoring.yml
services:
  otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    ports:
      - "4317:4317"  # OTLP gRPC
      - "4318:4318"  # OTLP HTTP
      - "8888:8888"  # Prometheus scraping
    volumes:
      - ./otel-collector-config.yml:/etc/otel-collector-config.yml:ro
    environment:
      - ENVIRONMENT=dev
      - GRAFANA_CLOUD_API_KEY=${GRAFANA_CLOUD_API_KEY}
      - GRAFANA_CLOUD_PROMETHEUS_URL=${GRAFANA_CLOUD_PROMETHEUS_URL}
      - GRAFANA_CLOUD_LOKI_URL=${GRAFANA_CLOUD_LOKI_URL}
      - GRAFANA_CLOUD_TENANT_ID=${GRAFANA_CLOUD_TENANT_ID}
    command: ["--config=/etc/otel-collector-config.yml"]

  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"  # Jaeger UI
      - "14250:14250"  # Jaeger gRPC receiver
    environment:
      - COLLECTOR_OTLP_ENABLED=true

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.retention.time=7d"
```

**Production (AWS ECS Sidecar):**
```terraform
# infra/ecs.tf
resource "aws_ecs_task_definition" "api_gateway" {
  family = "api-gateway"
  container_definitions = jsonencode([
    {
      name  = "api-gateway"
      image = "..."
      environment = [
        { name = "OTEL_EXPORTER_OTLP_ENDPOINT", value = "http://localhost:4317" }
      ]
    },
    {
      name  = "otel-collector"
      image = "public.ecr.aws/aws-observability/aws-otel-collector:latest"
      portMappings = [
        { containerPort = 4317, protocol = "tcp" }
      ]
      environment = [
        { name = "ENVIRONMENT", value = "production" }
      ]
      secrets = [
        { name = "GRAFANA_CLOUD_API_KEY", valueFrom = "${aws_ssm_parameter.grafana_cloud_api_key.arn}" }
      ]
    }
  ])
}
```

#### AWS CloudWatch Logs Integration

**Log Driver Configuration (ECS Task Definition):**
```json
{
  "logConfiguration": {
    "logDriver": "awslogs",
    "options": {
      "awslogs-group": "/ecs/ai-teams-prod",
      "awslogs-region": "us-east-1",
      "awslogs-stream-prefix": "api-gateway"
    }
  }
}
```

**CloudWatch Logs Insights Queries** (defined in `infra/monitoring.tf`):

**Query 1: Tracking ID Correlation**
```sql
fields @timestamp, @message, tracking_id, service, @level
| filter ispresent(tracking_id)
| sort @timestamp desc
| limit 100
```

**Query 2: Error Tracking with Trace Context**
```sql
fields @timestamp, @message, tracking_id, service, error.type, error.message
| filter @level = "ERROR"
| filter ispresent(tracking_id)
| sort @timestamp desc
| limit 50
```

**Query 3: Request Performance Analysis**
```sql
fields @timestamp, tracking_id, request.method, request.path, request.duration, response.status
| filter ispresent(request.duration)
| filter request.duration > 1.0
| sort request.duration desc
| limit 50
```

**Query 4: User Activity Tracking**
```sql
fields @timestamp, tracking_id, user.id, user.segment, operation.name, operation.result
| filter ispresent(user.id)
| stats count() by user.id, operation.name
| sort count() desc
```

#### Grafana Cloud Integration

**Authentication Configuration:**
```bash
# Stored in AWS SSM Parameter Store
/ai-teams/{environment}/monitoring/grafana-cloud-api-key  # SecureString
/ai-teams/{environment}/monitoring/grafana-cloud-config   # JSON String

# Grafana Cloud Configuration JSON
{
  "tenant_id": "123456",
  "prometheus_url": "https://prometheus-prod-01-eu-west-0.grafana.net/api/prom/push",
  "loki_url": "https://logs-prod-006.grafana.net/loki/api/v1/push"
}
```

**Grafana Cloud Free Tier Limits:**
- **Metrics**: 10,000 active series
- **Logs**: 50 GB/month ingestion
- **Traces**: 50 GB/month ingestion
- **Users**: 5 active users
- **Retention**: 14 days for metrics, 30 days for logs/traces

**Cost Optimization Strategy:**
- **Environment Labeling**: Use `environment` label to filter dev/staging/prod data in single Grafana instance
- **Metric Cardinality Control**: Limit label values to prevent explosion of time series
- **Log Sampling**: Use sampling for high-volume debug logs in development
- **Alert Consolidation**: Grafana OnCall free tier supports 5 integrations

## 6. Non-Functional Requirements

### 6.1 Performance

**Performance Targets:**
- **Instrumentation Overhead**: \< 5% latency increase compared to uninstrumented baseline
- **Trace Collection Latency**: \< 30 seconds from span creation to Jaeger UI visibility
- **Metrics Export Interval**: 10 seconds (configurable in OTLP Collector)
- **Log Ingestion Latency**: \< 60 seconds to CloudWatch Logs Insights query availability

**Optimization Strategies:**

**Batch Processing:**
- **Span Export**: BatchSpanProcessor with 1s timeout, 512 span batch size
- **Metric Export**: PeriodicExportingMetricReader with 10s export interval
- **Log Export**: Batch processor with 1s timeout for Loki export

**Memory Management:**
- **OTLP Collector Memory Limit**: 512 MB (memory_limiter processor)
- **Span Queue Size**: 2048 spans (BatchSpanProcessor default)
- **Metric Aggregation**: Temporary memory for aggregation (Prometheus exporter)

**Cardinality Control:**
- **Endpoint Normalization**: UUID and numeric ID replacement to limit unique values
- **Label Value Constraints**: Predefined enums for status codes, methods, environments
- **Field Limiting**: CloudWatch formatter caps at 900 fields to prevent truncation

**Caching Strategies:**
- **Tracer/Meter Caching**: Single tracer and meter instance per service (singleton pattern)
- **Formatter Caching**: CloudWatch formatter created once during logging setup
- **Resource Attribute Caching**: Resource created once during telemetry initialization

### 6.2 Scalability

**Scaling Approach:**
- **Horizontal Scaling**: Each service instance runs independent telemetry stack
- **OTLP Collector Scaling**: Stateless collector allows multiple instances with load balancing
- **Grafana Cloud Auto-Scaling**: Managed service handles ingestion scaling automatically

**Resource Considerations:**

**Per-Service Resource Usage:**
- **CPU Overhead**: ~2-5% for instrumentation and context propagation
- **Memory Overhead**: ~50-100 MB for OpenTelemetry SDK and buffers
- **Network Overhead**: ~1-5 KB/request for span and metric export (batched)

**OTLP Collector Resource Usage:**
- **CPU**: ~0.5 core for 1000 requests/sec trace processing
- **Memory**: 512 MB limit enforced by memory_limiter processor
- **Network**: Depends on telemetry volume (batched export reduces overhead)

**Load Handling:**
- **High Request Volume**: Batch processing prevents overload of downstream exporters
- **Burst Traffic**: Memory limiter prevents OOM, drops data if necessary
- **Back Pressure**: OTLP Collector queue full → drops new spans/metrics (logged as warnings)

### 6.3 Security

**Security Measures:**

**Data Transmission:**
- **Development**: Insecure gRPC (no TLS) for local debugging
- **Production**: TLS-encrypted connections to Grafana Cloud and AWS CloudWatch
- **API Keys**: Grafana Cloud API keys stored in AWS SSM Parameter Store (SecureString)
- **Service Authentication**: AWS ECS task role for CloudWatch Logs write permissions

**Sensitive Data Handling:**
- **PII Filtering**: No automatic PII scrubbing (manual exclusion required in logs)
- **Credential Redaction**: Avoid logging API keys, tokens, passwords in span attributes or logs
- **Field Exclusion**: CloudWatchTracingFormatter excludes internal Python log fields

**Access Control:**
- **Jaeger UI**: No authentication (development only, not exposed publicly)
- **Prometheus**: No authentication (development only, not exposed publicly)
- **Grafana Cloud**: User authentication with role-based access control (RBAC)
- **AWS CloudWatch Logs**: IAM-based access control with fine-grained permissions

**Data Retention:**
- **Local Development**: No retention limits (Jaeger/Prometheus purge on restart)
- **Grafana Cloud Free Tier**: 14 days metrics, 30 days logs/traces
- **AWS CloudWatch Logs**: Configurable retention (default 7 days for cost optimization)

**Audit Logging:**
- **CloudWatch Logs**: Immutable audit trail of all application logs
- **Grafana Cloud Access Logs**: User access and query audit logs available

### 6.4 Reliability

**Error Handling Strategies:**

**Graceful Degradation:**
- **OTLP Collector Unavailable**: Services continue operating, spans queued locally (2048 span limit)
- **Exporter Failures**: OTLP Collector logs errors but continues processing other pipelines
- **Span Drop Policy**: Drop oldest spans if queue full (prevents memory exhaustion)

**Failure Recovery Mechanisms:**
- **Automatic Retry**: OTLP exporter retries failed exports with exponential backoff
- **Circuit Breaker**: Not implemented (OpenTelemetry SDK does not include circuit breaker)
- **Fallback Logging**: If telemetry initialization fails, services log to console (JSON format)

**Health Monitoring:**
- **Service Health Checks**: Each service exposes `/health` endpoint (not directly tied to telemetry)
- **OTLP Collector Health**: Prometheus metrics exposed at `:8888/metrics` for collector health
- **Jaeger Health**: Jaeger UI availability indicates trace ingestion health

**Data Integrity:**
- **Span Sampling**: No sampling enabled (all spans collected in development/production)
- **Metric Accuracy**: Counter/gauge metrics are exact, histograms use default buckets
- **Log Completeness**: All logs sent to CloudWatch (no intentional filtering or sampling)

### 6.5 Testing & Observability

#### Testing Strategy

**Unit Testing:**
- **Middleware Testing**: Verify TrackingMiddleware extracts trace_id and sets request.state
- **Formatter Testing**: Verify CloudWatchTracingFormatter produces valid JSON with required fields
- **Metrics Testing**: Verify MetricsMiddleware collects metrics with correct labels

**Integration Testing:**
- **Service-to-Service Tracing**: Verify trace context propagates across API Gateway → Workflow Agent → Workflow Engine
- **OTLP Collector Integration**: Verify spans/metrics exported to Jaeger/Prometheus in Docker Compose environment
- **CloudWatch Logs Integration**: Verify JSON logs visible in CloudWatch Logs Insights (production)

**End-to-End Testing:**
- **Workflow Execution Tracing**: Create workflow, execute, verify complete trace in Jaeger UI
- **Error Tracing**: Trigger error, verify ERROR log creates span event in Jaeger
- **Metrics Verification**: Generate traffic, verify metrics in Prometheus/Grafana

**Test Coverage Targets:**
- **Telemetry Components**: 80% code coverage (middleware, formatter, metrics)
- **Service Integration**: Manual verification of telemetry in Docker Compose
- **Production Validation**: Smoke tests after deployment to verify CloudWatch logs

#### Observability

**Key Metrics to Collect:**

**Latency Metrics:**
- `request_duration_seconds{service_name, endpoint, method}` - P50, P95, P99 latency by endpoint
- `ai_model_duration{model, provider}` - AI model response time
- `workflow_execution_duration{workflow_type}` - End-to-end workflow execution time

**Throughput Metrics:**
- `request_count{service_name, endpoint, method, status_code}` - Request rate and success rate
- `ai_requests_total{model, provider}` - AI API call rate
- `workflow_success_rate{workflow_type}` - Workflow completion rate

**Error Metrics:**
- `request_errors_total{service_name, endpoint, error_type}` - Error rate by type
- `ai_errors_total{model, provider, error_type}` - AI API error rate
- `workflow_failures_total{workflow_type, error_category}` - Workflow failure rate

**Resource Utilization Metrics:**
- `active_requests{service_name, endpoint}` - Concurrent request count
- `process_cpu_seconds_total` - CPU usage (standard OpenTelemetry metric)
- `process_memory_bytes` - Memory usage (standard OpenTelemetry metric)

**Business Metrics:**
- `api_key_usage_total{api_key_id, client_name}` - API usage by client
- `user_activity_total{user_id, activity_type}` - User engagement
- `ai_tokens_total{model, token_type}` - Token consumption and cost
- `ai_cost_total{model}` - AI spend tracking

**Logging Strategy:**

**Log Levels:**
- **DEBUG**: Detailed execution flow (disabled in production)
- **INFO**: Normal operations (request/response, state changes)
- **WARN**: Recoverable issues (rate limit warnings, retry attempts)
- **ERROR**: Failures requiring investigation (exceptions, external service failures)

**Structured Logging Conventions:**
- **All logs**: Include `tracking_id`, `service`, `@timestamp`, `@level`, `@message`
- **Request logs**: Include `request.method`, `request.path`, `request.duration`, `response.status`
- **Error logs**: Include `error.type`, `error.message`, `exception.stack_trace`
- **Business logs**: Include relevant entity IDs (`user.id`, `session.id`, `workflow.id`)

**Log Sampling Strategy:**
- **Production**: INFO level minimum (WARN/ERROR always logged)
- **Development**: DEBUG level for detailed troubleshooting
- **High-Volume Endpoints**: Consider sampling at INFO level if log volume exceeds CloudWatch limits

**Distributed Tracing Implementation:**

**Automatic Tracing (via Auto-Instrumentation):**
- **HTTP Servers**: FastAPI automatically creates spans for all incoming requests
- **HTTP Clients**: HTTPX/Requests automatically create spans for outgoing requests and propagate context
- **Database Calls**: psycopg2 automatically creates spans for SQL queries (if enabled)

**Manual Tracing (for Business Logic):**
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def execute_workflow(workflow_id: str, tracking_id: str):
    with tracer.start_as_current_span("workflow_execution") as span:
        span.set_attributes({
            "tracking.id": tracking_id,
            "workflow.id": workflow_id,
            "workflow.node_count": len(workflow.nodes)
        })

        for node in workflow.nodes:
            with tracer.start_as_current_span(f"execute_node[{node.type}]") as node_span:
                node_span.set_attributes({
                    "node.id": node.id,
                    "node.type": node.type,
                    "node.name": node.name
                })

                result = await node_executor.execute(node)

                node_span.set_attribute("node.status", result.status)
                if result.error:
                    node_span.set_status(trace.Status(trace.StatusCode.ERROR, result.error))

        span.set_attribute("workflow.status", "SUCCESS")
```

**Trace Context Propagation:**
- **Automatic**: OpenTelemetry auto-instrumentation handles `traceparent` header injection/extraction
- **Manual**: Use `tracer.start_as_current_span()` to create child spans in business logic
- **Cross-Process**: Works across API Gateway → Workflow Agent → Workflow Engine without manual header management

#### Monitoring & Alerting

**Dashboard Design:**

**Service Health Dashboard (Grafana Cloud):**
- **Request Rate**: Requests/sec by service and endpoint
- **Error Rate**: Errors/sec by service and error type
- **Latency Distribution**: P50, P95, P99 latency by service
- **Active Requests**: Concurrent requests by service
- **Service Availability**: Uptime percentage (derived from health check logs)

**Workflow Execution Dashboard (Grafana Cloud):**
- **Execution Rate**: Workflows started/completed per minute
- **Success Rate**: Percentage of successful executions by workflow type
- **Execution Duration**: P50, P95, P99 execution time by workflow type
- **Node Execution Distribution**: Time spent in each node type

**AI Model Usage Dashboard (Grafana Cloud):**
- **Request Rate**: AI API calls/sec by model and provider
- **Token Consumption**: Tokens/sec by model (input vs output)
- **Cost Tracking**: USD spent per hour/day by model
- **Error Rate**: AI API failures by model and error type

**Infrastructure Dashboard (Grafana Cloud + AWS CloudWatch):**
- **ECS Service Metrics**: CPU, memory, task count by service
- **Load Balancer Metrics**: Request count, response time, healthy target count
- **CloudWatch Logs Metrics**: Log ingestion rate, log group size

**Alert Thresholds and Escalation Policies:**

**Critical Alerts (Immediate Notification):**
- **Service Down**: Health check failure for \> 2 minutes → Page on-call engineer
- **Error Rate Spike**: Error rate \> 10% for \> 5 minutes → Page on-call engineer
- **P95 Latency Spike**: P95 latency \> 5s for \> 5 minutes → Page on-call engineer
- **ECS Task Failure**: Task restart rate \> 3 restarts/10 minutes → Page on-call engineer

**Warning Alerts (Slack Notification):**
- **Elevated Error Rate**: Error rate \> 5% for \> 10 minutes → Notify dev channel
- **Elevated Latency**: P95 latency \> 2s for \> 10 minutes → Notify dev channel
- **High AI Cost**: AI spend \> $10/hour → Notify dev channel
- **CloudWatch Logs Size**: Log group size \> 80% of quota → Notify ops channel

**Informational Alerts (Email Notification):**
- **Daily AI Cost Report**: Total AI spend for the day → Email to team
- **Weekly Performance Report**: Service SLI/SLO summary → Email to team
- **Grafana Cloud Usage**: Metrics/logs usage vs free tier limit → Email to ops

**SLIs (Service Level Indicators) and SLOs (Service Level Objectives):**

**Availability SLI/SLO:**
- **SLI**: Percentage of successful health checks over 5-minute windows
- **SLO**: 99.9% availability (43 minutes downtime/month)
- **Measurement**: CloudWatch Logs query for health check responses

**Latency SLI/SLO:**
- **SLI**: Percentage of requests with P95 latency \< 2 seconds
- **SLO**: 95% of requests meet latency target
- **Measurement**: Prometheus histogram query on `request_duration_seconds`

**Error Rate SLI/SLO:**
- **SLI**: Percentage of requests returning 5xx status codes
- **SLO**: \< 1% error rate
- **Measurement**: Prometheus counter ratio query on `request_count{status_code=~"5.."}`

**Workflow Success Rate SLI/SLO:**
- **SLI**: Percentage of workflows completing successfully
- **SLO**: 95% success rate for simple workflows, 85% for complex workflows
- **Measurement**: Prometheus histogram query on `workflow_success_rate`

**Incident Response Procedures:**

**Incident Detection:**
1. **Automated Alert**: Grafana OnCall or AWS CloudWatch Alarm triggers notification
2. **Manual Discovery**: Engineer notices issue in Grafana dashboard or Jaeger traces
3. **User Report**: Support ticket or user complaint indicates service degradation

**Incident Triage:**
1. **Acknowledge Alert**: On-call engineer acknowledges incident in Grafana OnCall
2. **Severity Assessment**: Determine impact (critical, high, medium, low)
3. **Initial Investigation**: Check Grafana dashboards, Jaeger traces, CloudWatch logs

**Incident Investigation:**
1. **Identify Tracking ID**: Obtain tracking_id from error alert or user report
2. **Trace Analysis**: Search Jaeger UI for tracking_id to see full distributed trace
3. **Log Correlation**: Query CloudWatch Logs Insights for tracking_id to see all related logs
4. **Metrics Verification**: Check Prometheus/Grafana metrics for anomalies

**Incident Resolution:**
1. **Immediate Mitigation**: Rollback deployment, scale services, or disable feature flag
2. **Root Cause Fix**: Deploy code fix or configuration change
3. **Verification**: Monitor metrics and logs to confirm issue resolved
4. **Incident Closure**: Document root cause and resolution in incident report

**Post-Incident Review:**
1. **Timeline Documentation**: Record incident timeline with tracking IDs
2. **Root Cause Analysis**: Analyze traces and logs to determine root cause
3. **Action Items**: Create tasks to prevent recurrence (alerts, code fixes, documentation)
4. **Knowledge Sharing**: Share learnings with team in post-mortem meeting

## 7. Technical Debt and Future Considerations

### Known Limitations

**Current System Constraints:**

1. **No Sampling Strategy**: All spans are collected without sampling, potentially causing high cardinality in production
   - **Impact**: High telemetry data volume and cost at scale
   - **Mitigation**: Implement head-based or tail-based sampling in OTLP Collector

2. **Limited PII Scrubbing**: No automatic removal of personally identifiable information from logs/spans
   - **Impact**: Compliance risk for GDPR, CCPA if PII is logged
   - **Mitigation**: Implement custom processor in OTLP Collector to scrub PII patterns

3. **No Circuit Breaker**: Services continue exporting telemetry even if OTLP Collector is down
   - **Impact**: Potential memory exhaustion if collector is unavailable for extended period
   - **Mitigation**: OpenTelemetry SDK has internal queue limits, but explicit circuit breaker would be better

4. **No Real-User Monitoring (RUM)**: Frontend observability not integrated with backend tracing
   - **Impact**: Cannot trace requests end-to-end from browser to backend
   - **Mitigation**: Implement OpenTelemetry JS SDK in frontend with trace context injection

5. **No Profiling**: No continuous profiling data for CPU/memory performance analysis
   - **Impact**: Difficult to diagnose performance issues without detailed profiling data
   - **Mitigation**: Integrate Pyroscope or Grafana Cloud Profiles for continuous profiling

6. **Limited Alerting Logic**: Alerts are basic threshold-based, no anomaly detection
   - **Impact**: False positives/negatives due to lack of adaptive thresholds
   - **Mitigation**: Implement machine learning-based anomaly detection in Grafana

### Areas for Improvement

**Short-Term Improvements (1-3 months):**

1. **Implement Trace Sampling**:
   - Configure tail-based sampling in OTLP Collector (sample errors and slow traces at 100%, normal traces at 10%)
   - Reduce telemetry data volume while maintaining error visibility
   - **Priority**: High (cost optimization)

2. **Add PII Scrubbing Processor**:
   - Create custom OTLP Collector processor to scrub email, phone, SSN patterns
   - Apply to both logs and span attributes
   - **Priority**: High (compliance)

3. **Frontend RUM Integration**:
   - Add OpenTelemetry JS SDK to React frontend
   - Inject trace context in API calls to correlate frontend → backend traces
   - **Priority**: Medium (user experience insights)

4. **Enhanced Business Metrics**:
   - Add workflow complexity score metric
   - Add user retention cohort metrics
   - Add AI model accuracy metrics (if applicable)
   - **Priority**: Medium (product insights)

5. **Prometheus Alerting Rules**:
   - Define Prometheus alerting rules for common issues (high error rate, slow queries)
   - Forward alerts to Grafana OnCall for central incident management
   - **Priority**: High (incident response)

**Medium-Term Improvements (3-6 months):**

1. **Continuous Profiling**:
   - Integrate Pyroscope or Grafana Cloud Profiles for CPU/memory profiling
   - Enable automatic profiling trigger on high latency spans
   - **Priority**: Medium (performance optimization)

2. **Anomaly Detection Dashboards**:
   - Implement Grafana ML plugins for anomaly detection on key metrics
   - Auto-generate alerts for detected anomalies
   - **Priority**: Medium (proactive incident detection)

3. **Service Mesh Integration**:
   - Evaluate Istio or Linkerd for service mesh observability
   - Automatic mTLS, traffic splitting, and advanced tracing
   - **Priority**: Low (only if microservices complexity increases)

4. **Distributed Tracing Cost Analysis**:
   - Add span attribute to track estimated cost per trace (AI tokens, external API calls)
   - Dashboard showing cost breakdown by workflow type
   - **Priority**: Medium (cost optimization)

5. **Security Audit Logging**:
   - Dedicated audit log pipeline for security-relevant events (login, permission changes)
   - Separate retention policy (1 year vs 30 days)
   - **Priority**: Medium (compliance)

**Long-Term Improvements (6-12 months):**

1. **Multi-Cloud Telemetry**:
   - Add support for exporting to multiple cloud providers (Azure Monitor, Google Cloud Operations)
   - Vendor-agnostic telemetry architecture
   - **Priority**: Low (only if multi-cloud deployment is planned)

2. **Custom Business KPI Tracking**:
   - Build custom KPI calculation pipeline (e.g., workflow ROI, user LTV)
   - Real-time dashboard for executive visibility
   - **Priority**: Low (business analytics focus)

3. **OpenTelemetry Ecosystem Integration**:
   - Integrate with eBPF-based tracing (Pixie, Parca)
   - Zero-instrumentation tracing for legacy components
   - **Priority**: Low (advanced use cases)

### Planned Enhancements

**Committed Roadmap Items:**

**Q1 2025:**
- [ ] Implement trace sampling in OTLP Collector
- [ ] Add PII scrubbing processor
- [ ] Deploy Grafana Cloud dashboards for all services
- [ ] Configure CloudWatch Logs Insights saved queries for common investigations

**Q2 2025:**
- [ ] Integrate OpenTelemetry JS SDK in frontend
- [ ] Implement Prometheus alerting rules
- [ ] Add continuous profiling via Pyroscope
- [ ] Create runbooks for common incidents

**Q3 2025:**
- [ ] Implement anomaly detection dashboards
- [ ] Add distributed tracing cost analysis
- [ ] Deploy security audit logging pipeline
- [ ] Performance optimization based on profiling insights

**Experimental Features:**
- **Trace Context in Database**: Store trace_id in database for direct SQL-based trace lookups
- **Custom Span Processors**: Business-specific span enrichment (e.g., cost calculation, user segmentation)
- **Telemetry Replay**: Ability to replay production traces in staging for debugging

### Migration Paths

**Migration from Manual Logging to Structured Logging:**
1. **Phase 1**: Add CloudWatchTracingFormatter to existing services without changing log statements
2. **Phase 2**: Refactor log statements to use structured logging with extra fields
3. **Phase 3**: Remove legacy logging format support

**Migration from Placeholder Trace IDs to OpenTelemetry Trace IDs:**
1. **Phase 1**: Run both systems in parallel (manual trace_id + OpenTelemetry trace_id)
2. **Phase 2**: Update database schemas to use OpenTelemetry trace_id format (32-char hex)
3. **Phase 3**: Remove manual trace_id generation code

**Migration from Local Monitoring to Full Cloud Monitoring:**
1. **Phase 1**: Deploy OTLP Collector with dual export (local + cloud)
2. **Phase 2**: Verify data quality in Grafana Cloud dashboards
3. **Phase 3**: Disable local Jaeger/Prometheus in production (keep for development)

## 8. Appendices

### A. Glossary

**Technical Terms:**

- **OpenTelemetry (OTel)**: Open-source observability framework for traces, metrics, and logs
- **Trace**: Complete path of a request through a distributed system
- **Span**: Single unit of work within a trace (e.g., HTTP request, database query)
- **Trace Context**: Metadata propagated across services to correlate spans into traces
- **Trace ID**: Globally unique 128-bit identifier for a trace
- **Span ID**: Unique 64-bit identifier for a span within a trace
- **W3C Trace Context**: Standard HTTP header format for trace context propagation (`traceparent`)
- **OTLP (OpenTelemetry Protocol)**: gRPC/HTTP protocol for exporting telemetry data
- **OTLP Collector**: Standalone service for receiving, processing, and exporting telemetry data
- **Structured Logging**: JSON-formatted logs with consistent schema for machine parsing
- **CloudWatch Logs Insights**: AWS query language for searching and analyzing CloudWatch logs
- **Grafana Cloud**: SaaS platform for metrics (Mimir), logs (Loki), and dashboards (Grafana)
- **Jaeger**: Open-source distributed tracing system
- **Prometheus**: Open-source time-series database and monitoring system
- **Cardinality**: Number of unique label combinations in metrics (high cardinality = high cost)
- **Instrumentation**: Code that emits telemetry data (traces, metrics, logs)
- **Auto-Instrumentation**: Automatic instrumentation via library hooks (no manual code changes)
- **Span Processor**: Component that processes spans before export (e.g., batching, filtering)
- **Resource Attributes**: Key-value pairs describing the service emitting telemetry (service.name, environment)
- **Span Attributes**: Key-value pairs describing a specific span (http.method, user.id)
- **SLI (Service Level Indicator)**: Metric measuring service performance (e.g., error rate)
- **SLO (Service Level Objective)**: Target value for an SLI (e.g., error rate \< 1%)

**Acronyms:**

- **OTLP**: OpenTelemetry Protocol
- **RLS**: Row Level Security (Supabase database feature)
- **RUM**: Real User Monitoring (frontend observability)
- **APM**: Application Performance Monitoring
- **PII**: Personally Identifiable Information
- **GDPR**: General Data Protection Regulation
- **CCPA**: California Consumer Privacy Act
- **ECS**: Elastic Container Service (AWS)
- **SSM**: AWS Systems Manager (for secrets management)
- **KPI**: Key Performance Indicator
- **LTV**: Lifetime Value (business metric)

### B. References

**Related Documentation:**
- [OpenTelemetry Official Documentation](https://opentelemetry.io/docs/)
- [W3C Trace Context Specification](https://www.w3.org/TR/trace-context/)
- [Grafana Cloud Documentation](https://grafana.com/docs/grafana-cloud/)
- [AWS CloudWatch Logs Insights Documentation](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [Prometheus Documentation](https://prometheus.io/docs/)

**Internal Documentation:**
- `/apps/backend/CLAUDE.md` - Backend development guide
- `/apps/backend/api-gateway/CLAUDE.md` - API Gateway architecture
- `/docs/tech-design/api-gateway-architecture.md` - API Gateway technical design
- `/docs/tech-design/workflow-engine-architecture.md` - Workflow Engine technical design
- `/docs/tech-design/new_workflow_spec.md` - Workflow data model specification
- `/CLAUDE.md` - Monorepo overview and deployment guide

**External Resources:**
- OpenTelemetry Python SDK: https://github.com/open-telemetry/opentelemetry-python
- OpenTelemetry Collector: https://github.com/open-telemetry/opentelemetry-collector-contrib
- CloudWatch Logs Insights Query Syntax: https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax.html
- Grafana Dashboard Examples: https://grafana.com/grafana/dashboards/

**Configuration Files:**
- `/monitoring/otel-collector-config.yml` - OTLP Collector configuration
- `/monitoring/docker-compose.monitoring.yml` - Local monitoring stack
- `/apps/backend/shared/telemetry/complete_stack.py` - Telemetry SDK implementation
- `/apps/backend/shared/telemetry/middleware.py` - Middleware implementation
- `/infra/monitoring.tf` - Production monitoring infrastructure

---

**Document Version**: 1.0
**Last Updated**: January 2025
**Status**: Current Implementation
**Authors**: Technical Design Documentation Specialist
**Review Cycle**: Quarterly or after major architecture changes
