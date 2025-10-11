# Workflow Engine V2: Technical Design Document

## 1. Executive Summary

The **Workflow Engine V2** (workflow_engine_v2) is a modern, spec-driven execution engine designed to run complex AI-powered workflows with precision, reliability, and comprehensive observability. Built with FastAPI, it provides a robust foundation for executing node-based workflows with advanced features including Human-in-the-Loop (HIL) interactions, attached node patterns, and real-time execution tracking.

### Key Architectural Decisions

- **Spec-Driven Validation**: All nodes validated against centralized specifications in `shared/node_specs/`
- **Graph-Based Execution**: Workflows executed using topological sort with cycle detection
- **Runner Factory Pattern**: Dynamic node executor dispatch based on node type/subtype
- **Attached Nodes Pattern**: AI_AGENT nodes support TOOL and MEMORY attachments for enhanced capabilities
- **State Persistence**: Complete execution state preserved in Supabase for pause/resume operations

### Technology Stack

- **Framework**: FastAPI 0.104+ (HTTP/REST API)
- **Database**: PostgreSQL via Supabase (execution state, workflow definitions)
- **ORM**: Pydantic models with direct Supabase client integration
- **Validation**: Centralized node specifications with automatic type coercion
- **AI Providers**: OpenAI, Anthropic, Google Gemini with unified interface
- **Deployment**: Docker + AWS ECS Fargate (linux/amd64)

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         API Layer (FastAPI)                          │
├──────────────────────┬──────────────────────┬──────────────────────┤
│  Health Endpoint     │  V2 Execution API    │  V2 Workflow API     │
│  /health             │  /v2/executions/*    │  /v2/workflows/*     │
└──────────────────────┴──────────────────────┴──────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Core Execution Engine                         │
├──────────────────────┬──────────────────────┬──────────────────────┤
│  ExecutionEngine     │  WorkflowGraph       │  ExecutionContext    │
│  - run()             │  - topo_order()      │  - node_outputs      │
│  - run_async()       │  - cycle detection   │  - pending_inputs    │
│  - resume_*()        │  - attached nodes    │  - execution state   │
└──────────────────────┴──────────────────────┴──────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  Node Runners    │  │  Services        │  │  Persistence     │
├──────────────────┤  ├──────────────────┤  ├──────────────────┤
│ AIAgentRunner    │  │ HILService       │  │ Supabase Repo    │
│ ActionRunner     │  │ MemoryService    │  │ - executions     │
│ FlowRunner       │  │ EventPublisher   │  │ - workflows      │
│ ExternalAction   │  │ LoggingService   │  │ - hil_interact.  │
│ HILRunner        │  │ AI Providers     │  │ - pauses         │
│ MemoryRunner     │  │ Timer Service    │  │                  │
│ ToolRunner       │  │ Credential Encr. │  │                  │
└──────────────────┘  └──────────────────┘  └──────────────────┘
                                │
                                ▼
                      ┌──────────────────┐
                      │  External APIs   │
                      ├──────────────────┤
                      │ OpenAI           │
                      │ Anthropic        │
                      │ Google Gemini    │
                      │ Slack            │
                      │ GitHub           │
                      │ Notion           │
                      │ Firecrawl        │
                      └──────────────────┘
```

### 2.2 Component Architecture

#### Execution Engine (`core/engine.py`)
- **ExecutionEngine**: Main orchestrator for workflow execution
  - Validates workflows against node specifications
  - Builds execution graph with attached node filtering
  - Manages execution lifecycle (NEW → RUNNING → SUCCESS/ERROR/PAUSED)
  - Handles retry logic with exponential backoff
  - Implements timeout enforcement per node
  - Provides pause/resume for HIL interactions
  - Tracks token usage and credits consumption

#### Runner Factory (`runners/factory.py`)
- **default_runner_for(node)**: Dispatcher function
  - Routes nodes to appropriate runner based on type/subtype
  - Supports 7 core node types: TRIGGER, AI_AGENT, ACTION, EXTERNAL_ACTION, FLOW, HUMAN_IN_THE_LOOP, MEMORY, TOOL
  - Enforces explicit AI provider selection (no fallback to generic AI)
  - Returns PassthroughRunner for unknown types (graceful degradation)

#### Node Runners (`runners/*.py`)
- **Base Runners**:
  - `NodeRunner` (ABC): Defines `run(node, inputs, trigger) -> outputs` interface
  - `TriggerRunner`: Passes through trigger data to downstream nodes
  - `PassthroughRunner`: Default fallback, passes inputs through unchanged

- **AI Agent Runners**:
  - `AIAgentRunner`: Enhanced AI execution with memory/tool integration
  - `AnthropicClaudeRunner`: Anthropic Claude-specific implementation
  - `OpenAIChatGPTRunner`: OpenAI GPT-specific implementation
  - `GoogleGeminiRunner`: Google Gemini-specific implementation

- **Flow Control Runners**:
  - `IfRunner`: Conditional branching based on expression evaluation
  - `MergeRunner`: Combines multiple inputs into single output
  - `SplitRunner`: Splits data into multiple outputs
  - `FilterRunner`: Filters data based on conditions
  - `SortRunner`: Sorts data collections
  - `WaitRunner`: Waits for external events or timeouts
  - `DelayRunner`: Introduces delays in execution
  - `TimeoutRunner`: Enforces execution time limits
  - `LoopRunner`: Repeats execution for collections
  - `ForEachRunner`: Fan-out execution for each item

- **Action Runners**:
  - `HttpRequestRunner`: HTTP API calls
  - `DataTransformationRunner`: Data manipulation and transformation

- **Integration Runners**:
  - `ExternalActionRunner`: Routes to service-specific external actions
  - `MemoryRunner`: Manages conversation history and context storage
  - `ToolRunner`: MCP tool discovery and invocation
  - `HILRunner`: Human-in-the-loop interaction management

## 3. Data Architecture

### 3.1 Data Models

#### Core Execution Models (from `shared/models/`)

**Workflow**:
```python
class Workflow(BaseModel):
    metadata: WorkflowMetadata
    nodes: List[Node]
    connections: List[Connection]
    triggers: List[str]  # Node IDs that can initiate execution
    variables: Dict[str, Any]
```

**Node**:
```python
class Node(BaseModel):
    id: str
    name: str
    type: NodeType  # TRIGGER, AI_AGENT, ACTION, EXTERNAL_ACTION, FLOW, HUMAN_IN_THE_LOOP, MEMORY, TOOL
    subtype: str    # Provider/action-specific subtype
    configurations: Dict[str, Any]
    input_params: Dict[str, Any]
    output_params: Dict[str, Any]
    input_ports: List[Port]
    output_ports: List[Port]
    attached_nodes: List[str]  # For AI_AGENT: attached TOOL/MEMORY node IDs
    position: Optional[Position]
```

**Execution**:
```python
class Execution(BaseModel):
    id: str
    execution_id: str
    workflow_id: str
    workflow_version: str
    status: ExecutionStatus  # NEW, RUNNING, SUCCESS, ERROR, PAUSED, WAITING_FOR_HUMAN, CANCELED, TIMEOUT
    start_time: int  # epoch milliseconds
    end_time: Optional[int]
    duration_ms: Optional[int]
    trigger_info: TriggerInfo
    node_executions: Dict[str, NodeExecution]  # keyed by node_id
    node_runs: Dict[str, List[NodeExecution]]  # for fan-out tracking
    execution_sequence: List[str]  # ordered node execution history
    current_node_id: Optional[str]  # for paused workflows
    error: Optional[ExecutionError]
    tokens_used: Optional[TokenUsage]
    credits_consumed: int
    run_data: Optional[Dict[str, Any]]  # snapshot for API responses
```

**NodeExecution**:
```python
class NodeExecution(BaseModel):
    node_id: str
    node_name: str
    node_type: str
    node_subtype: str
    status: NodeExecutionStatus  # PENDING, RUNNING, COMPLETED, FAILED, WAITING_INPUT, RETRYING
    start_time: Optional[int]
    end_time: Optional[int]
    duration_ms: Optional[int]
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    error: Optional[NodeError]
    execution_details: NodeExecutionDetails
    activation_id: Optional[str]  # for tracking fan-out executions
    parent_activation_id: Optional[str]
    credits_consumed: int
```

### 3.2 Data Flow

#### Standard Node Execution Flow

1. **Input Aggregation**: Engine merges outputs from predecessor nodes
   - Inputs keyed by port name (default: "result")
   - Multiple inputs to same port are collected in a list
   - Conversion functions applied during propagation

2. **Node Execution**: Runner processes inputs and produces outputs
   - Context object (`_ctx`) provides access to execution state
   - Outputs structured as `{port_name: payload}` dictionary
   - Special control keys (prefixed with `_`) control engine behavior

3. **Output Shaping**: Outputs validated against node spec output_params
   - Only declared output parameters included in final output
   - Undeclared fields filtered out for data consistency
   - Fallback to defaults for missing declared parameters

4. **Output Propagation**: Shaped outputs flow to successor nodes
   - Connection `output_key` determines which port to use
   - Conversion functions transform data during propagation
   - Fan-out supported via "iteration" output key

#### Attached Node Flow (AI_AGENT only)

AI_AGENT nodes can attach TOOL and MEMORY nodes for enhanced capabilities:

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI_AGENT Node Execution                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. PRE-EXECUTION: Load Context                                 │
│     ┌──────────────────────────────────────────────────────┐   │
│     │ Attached MEMORY Nodes                                 │   │
│     │ - Query conversation history                          │   │
│     │ - Retrieve relevant context                           │   │
│     │ - Enhance system prompt with memory                   │   │
│     └──────────────────────────────────────────────────────┘   │
│                                                                  │
│  2. PRE-EXECUTION: Discover Tools                               │
│     ┌──────────────────────────────────────────────────────┐   │
│     │ Attached TOOL Nodes                                   │   │
│     │ - List available MCP functions                        │   │
│     │ - Register tools with AI provider                     │   │
│     │ - Enable tool calling during generation               │   │
│     └──────────────────────────────────────────────────────┘   │
│                                                                  │
│  3. EXECUTION: AI Generation                                    │
│     ┌──────────────────────────────────────────────────────┐   │
│     │ AI Provider (OpenAI/Anthropic/Gemini)                 │   │
│     │ - Generate response with enhanced prompt              │   │
│     │ - Invoke tools if needed                              │   │
│     │ - Return structured response                          │   │
│     └──────────────────────────────────────────────────────┘   │
│                                                                  │
│  4. POST-EXECUTION: Store Conversation                          │
│     ┌──────────────────────────────────────────────────────┐   │
│     │ Attached MEMORY Nodes                                 │   │
│     │ - Store user message                                  │   │
│     │ - Store AI response                                   │   │
│     │ - Update conversation context                         │   │
│     └──────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Key Points**:
- Attached nodes do NOT appear in workflow execution sequence
- No separate NodeExecution records for attached nodes
- All attachment logic handled within AIAgentRunner
- Results tracked in AI node's execution_details

## 4. Implementation Details

### 4.1 Core Components

#### ExecutionEngine.run()

The main execution loop implements a sophisticated task-queue based system:

```python
def run(self, workflow: Workflow, trigger: TriggerInfo, workflow_id: str) -> Execution:
    # 1. Validation
    self.validate_against_specs(workflow)  # Validates nodes against spec registry

    # 2. Graph Construction
    graph = WorkflowGraph(workflow)  # Filters out attached nodes
    _ = graph.topo_order()  # Raises CycleError if cycle detected

    # 3. Initialize Execution State
    workflow_execution = Execution(status=ExecutionStatus.RUNNING, ...)
    pending_inputs = {node_id: {} for node_id in graph.nodes.keys()}
    execution_context = ExecutionContext(workflow, graph, workflow_execution, pending_inputs)

    # 4. Task Queue Execution
    queue = [{"node_id": tid, "override": None} for tid in self._get_initial_ready_nodes(graph)]
    executed_main = set()

    while queue:
        task = queue.pop(0)
        node_id = task["node_id"]

        # Skip if already executed (unless fan-out)
        if task["override"] is None and node_id in executed_main:
            continue

        # 5. Node Execution with Retry
        max_retries = node.configurations.get("retry_attempts", 0)
        for attempt in range(max_retries + 1):
            try:
                runner = default_runner_for(node)
                outputs = runner.run(node, inputs, trigger)
                break
            except Exception as e:
                if attempt == max_retries:
                    # Fail workflow
                    workflow_execution.status = ExecutionStatus.ERROR
                    break
                # Exponential backoff
                time.sleep(backoff * (backoff_factor ** attempt))

        # 6. Handle Special Outputs
        if outputs.get("_hil_wait"):
            # Pause workflow for Human-in-the-Loop
            workflow_execution.status = ExecutionStatus.WAITING_FOR_HUMAN
            return workflow_execution

        if outputs.get("_wait") or outputs.get("_delay_ms"):
            # Schedule timer for delayed continuation
            self._timers.schedule(...)
            return workflow_execution

        # 7. Fail-Fast on Node Failure
        if any(port.get("success") is False for port in outputs.values()):
            workflow_execution.status = ExecutionStatus.ERROR
            break

        # 8. Output Shaping and Propagation
        shaped_outputs = {port: _shape_payload(payload) for port, payload in outputs.items()}

        for successor, output_key, conversion_fn in graph.successors(node_id):
            value = shaped_outputs.get(output_key)

            # Apply conversion function if specified
            if conversion_fn:
                value = execute_conversion_function_flexible(conversion_fn, value)

            # Handle fan-out for "iteration" port
            if output_key == "iteration" and isinstance(value, list):
                for item in value:
                    queue.append({"node_id": successor, "override": {"result": item}})
            else:
                pending_inputs[successor]["result"] = value
                if self._is_node_ready(graph, successor, pending_inputs):
                    queue.append({"node_id": successor, "override": None})

        executed_main.add(node_id)

    # 9. Finalization
    workflow_execution.status = ExecutionStatus.SUCCESS
    workflow_execution.end_time = _now_ms()
    return workflow_execution
```

### 4.2 Technical Decisions

#### Node Specification System

**Centralized Validation**: All node types defined in `shared/node_specs/`
- Type-safe configuration schemas with default values
- Automatic type coercion for inputs/outputs
- Runtime validation before execution
- Supports optional parameters with fallback defaults

**Example Spec**:
```python
class SlackExternalActionSpec(NodeSpecificationBase):
    node_type: str = "EXTERNAL_ACTION"
    subtype: str = "SLACK"

    configurations: Dict[str, Any] = {
        "action": {"type": "string", "options": ["send_message", "create_channel"]},
        "channel": {"type": "string", "required": True},
        "message": {"type": "string", "default": ""},
    }

    input_params: Dict[str, Any] = {
        "channel": None,
        "message": None,
    }

    output_params: Dict[str, Any] = {
        "success": False,
        "message_ts": None,
        "channel_id": None,
    }
```

#### Runner Factory Pattern

**Dynamic Dispatch**: Removes need for large if/elif chains
- Cleaner codebase with separation of concerns
- Easy to add new node types without modifying core engine
- Type-safe dispatch with Enum-based routing

**Trade-off**: Requires explicit registration in factory.py, but provides compile-time safety and clear documentation of supported node types.

#### Graph-Based Execution

**Topological Sort**: Ensures correct execution order
- Detects cycles at graph construction time (fail-fast)
- Supports conditional execution via output port selection
- Handles fan-out with activation tracking

**Attached Node Filtering**: WorkflowGraph excludes attached nodes
- Prevents double execution of TOOL/MEMORY nodes
- Maintains clean separation between workflow graph and attachment logic
- Attached nodes managed by parent AI_AGENT runner

#### Fail-Fast Error Handling

**Philosophy**: "Fail Fast with Clear Feedback" (from CLAUDE.md)
- Never return mock responses or silent failures
- Structured errors with error_code, error_message, error_details
- Actionable solutions provided in error responses

**Example Error Response**:
```python
{
    "success": False,
    "error_code": "missing_oauth_token",
    "error_message": "Slack OAuth token not found",
    "error_details": {
        "reason": "missing_oauth_token",
        "solution": "Connect Slack account in integrations settings",
        "oauth_flow_url": "/integrations/connect/slack"
    }
}
```

## 5. System Interactions

### 5.1 Internal Interactions

#### API Gateway → Workflow Engine

**Execute Workflow**:
```http
POST /v2/workflows/{workflow_id}/execute
Content-Type: application/json

{
  "trigger_data": {"user_input": "Hello!"},
  "async_execution": true,
  "start_from_node": null
}
```

**Response**:
```json
{
  "success": true,
  "execution_id": "exec_123",
  "execution": {
    "id": "exec_123",
    "workflow_id": "wf_456",
    "status": "RUNNING",
    "start_time": 1705000000000
  }
}
```

#### Resume HIL Workflow

**Flow**:
1. User responds to HIL interaction (Slack/Email/Web)
2. Response processed by API Gateway
3. API Gateway calls Workflow Engine resume endpoint
4. Engine restores execution context from database
5. Engine updates paused node with user response
6. Engine continues workflow from next nodes

**Resume Endpoint**:
```http
POST /v2/executions/{execution_id}/resume
Content-Type: application/json

{
  "node_id": "hil_node_1",
  "user_response": {
    "approved": true,
    "comment": "Looks good!"
  }
}
```

### 5.2 External Integrations

#### AI Providers

**Unified Interface** (`services/ai_providers.py`):
```python
class AIProvider(ABC):
    def generate(self, prompt: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI response with provider-specific implementation"""
        pass

# Implementations:
# - OpenAIProvider: Uses openai SDK
# - AnthropicProvider: Uses anthropic SDK
# - GeminiProvider: Uses google.generativeai SDK
```

**Provider Configuration**:
- Model selection via node configuration
- Temperature, max_tokens, top_p customizable per node
- Tool calling support for MCP integration
- Streaming support (chunked responses)

#### External Action Services

**OAuth-Based Integrations**:
- Slack: send_message, create_channel, update_message
- GitHub: create_issue, create_pr, add_comment
- Notion: create_page, update_page, query_database
- Google Calendar: create_event, update_event, list_events

**Authentication Flow**:
1. User connects account via API Gateway OAuth flow
2. OAuth tokens stored in Supabase with encryption
3. Workflow Engine retrieves tokens via credential service
4. Tokens automatically refreshed when expired

## 6. Non-Functional Requirements

### 6.1 Performance

**Targets**:
- Workflow execution initiation: \< 100ms
- Simple node execution (no external calls): \< 50ms
- AI node execution: \< 5s (depends on AI provider)
- Database query latency: \< 100ms
- Full workflow execution: \< 30s for typical workflows

**Optimization Strategies**:
- Supabase connection pooling for database operations
- Async execution with FastAPI background tasks
- Caching of node specifications
- Efficient graph traversal algorithms
- Minimal serialization overhead with Pydantic

**Caching**:
- Node specs cached in memory after first load
- Workflow definitions cached per execution
- AI provider clients reused across executions

### 6.2 Scalability

**Horizontal Scaling**:
- Stateless API layer (FastAPI)
- Execution state stored in Supabase (shared across instances)
- Background task processing via FastAPI BackgroundTasks
- Ready for message queue integration (future: Celery/RQ)

**Resource Considerations**:
- Memory: ~200MB per instance (base)
- CPU: 0.25 vCPU per instance (ECS Fargate)
- Database connections: 10 per instance (Supabase pool)
- Concurrent executions: Limited by ECS task count

### 6.3 Security

**Authentication**:
- JWT tokens from Supabase Auth
- Row-level security (RLS) for multi-tenant isolation
- API key authentication for MCP endpoints

**Data Encryption**:
- OAuth tokens encrypted at rest (credential_encryption service)
- TLS for all external API calls
- Environment variables for secrets (AWS SSM Parameters)

**Input Validation**:
- Pydantic models for all API requests
- Node spec validation before execution
- SQL injection prevention via parameterized queries

### 6.4 Reliability

**Error Handling**:
- Per-node retry with exponential backoff
- Structured error responses with error codes
- Execution state persisted after each node
- Graceful degradation for external service failures

**Failure Recovery**:
- Automatic retry for transient failures (network, timeout)
- Manual retry capability for failed nodes
- Workflow pause/resume for long-running executions
- Complete execution history for debugging

**Monitoring & Logging**:
- Structured logging with log levels (INFO, WARNING, ERROR)
- Execution events published to event system
- User-friendly logs for frontend display
- Backend developer logs with detailed diagnostics

### 6.5 Testing & Observability

#### Testing Strategy

**Unit Testing**:
- Runner tests: Verify node execution logic
- Graph tests: Cycle detection, topological sort
- Spec tests: Validation and type coercion
- Service tests: HIL service, memory service, AI providers

**Integration Testing**:
- End-to-end workflow execution
- HIL pause/resume flows
- External action integration tests
- Database persistence verification

**Test Coverage**:
- Target: \>= 80% code coverage
- Critical paths: \>= 95% coverage (execution engine, runners)
- Edge cases: Cycle detection, error handling, retry logic

**Testing Automation**:
- pytest with async support
- GitHub Actions CI/CD pipeline
- Pre-deployment integration tests

#### Observability

**Key Metrics**:
- **Latency**: Node execution time, workflow duration
- **Throughput**: Workflows executed per minute, nodes per second
- **Error Rates**: Failed executions, failed nodes, retry counts
- **Resource Utilization**: Memory usage, CPU usage, database connections

**Logging Strategy**:
- **INFO**: Workflow start/end, node execution milestones
- **WARNING**: Retry attempts, timeout warnings
- **ERROR**: Execution failures, external API errors
- **DEBUG**: Detailed input/output data, graph construction

**Application Performance Monitoring**:
- Execution traces with unique trace_id
- Per-node performance tracking
- Database query performance
- External API latency tracking

#### Monitoring & Alerting

**Dashboards**:
- Real-time execution status
- Node execution timeline
- Error rate trends
- Resource utilization graphs

**Alert Thresholds**:
- Error rate \> 5% over 5 minutes
- Average execution time \> 60s
- Database connection pool exhaustion
- External API failure rate \> 10%

**SLIs and SLOs**:
- **Availability**: \>= 99.9% uptime
- **Latency**: p95 \< 10s for workflow execution
- **Success Rate**: \>= 95% successful executions

**Incident Response**:
1. Automatic alerts via PagerDuty/Slack
2. Execution logs retrieved from Supabase
3. Retry failed workflows manually
4. Escalate to on-call engineer if needed

## 7. Human-in-the-Loop (HIL) Architecture

### 7.1 HIL Workflow Pattern

**5-Phase Execution Flow**:

1. **HIL Node Startup**:
   - Extract configuration (interaction_type, channel_type, timeout_seconds)
   - Validate parameters against HIL spec
   - Extract user_id from trigger/execution context
   - Return `_hil_wait: true` to signal pause

2. **Workflow Pause**:
   - ExecutionEngine detects `_hil_wait` flag
   - Creates record in `hil_interactions` table
   - Creates record in `workflow_execution_pauses` table
   - Updates workflow status to WAITING_FOR_HUMAN
   - Stores complete execution context for resume

3. **Interaction Request**:
   - HILService sends notification via configured channel
   - Slack: Interactive message with action buttons
   - Email: Email with approval links
   - App: In-app notification with form

4. **Human Response**:
   - User responds via Slack/Email/Web interface
   - Response webhook received by API Gateway
   - AI classification (8-factor analysis):
     - `relevant` (score \>= 0.7): Process response
     - `filtered` (score \<= 0.3): Ignore spam
     - `uncertain` (0.3 \< score \< 0.7): Log for review
   - Update `hil_interactions.status` to "completed"

5. **Workflow Resume**:
   - API Gateway calls `/v2/executions/{id}/resume`
   - ExecutionEngine restores context from database
   - HIL node output includes user response data
   - Workflow continues from successor nodes
   - Update `workflow_execution_pauses.status` to "resumed"

### 7.2 HIL Configuration

**Node Configuration**:
```python
{
  "interaction_type": "approval",  # approval|input|selection|review
  "channel_type": "slack",         # slack|email|webhook|app
  "timeout_seconds": 3600,         # 60 to 86400 (1 hour to 24 hours)
  "message": "Please approve this request",
  "approval_options": ["approve", "reject"],
  "channel_config": {
    "channel": "#approvals",       # Slack channel
  },
  "timeout_action": "fail"         # fail|continue|default_response
}
```

### 7.3 Database Schema

**hil_interactions**:
```sql
CREATE TABLE hil_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL,
    execution_id VARCHAR(255) NOT NULL,
    node_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    interaction_type VARCHAR(50) NOT NULL,
    channel_type VARCHAR(50) NOT NULL,
    request_data JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    timeout_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    responded_at TIMESTAMP,
    response_data JSONB
);
```

**workflow_execution_pauses**:
```sql
CREATE TABLE workflow_execution_pauses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id VARCHAR(255) NOT NULL,
    paused_node_id VARCHAR(255) NOT NULL,
    pause_reason VARCHAR(255) NOT NULL,
    resume_conditions JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    paused_at TIMESTAMP DEFAULT NOW(),
    resumed_at TIMESTAMP,
    hil_interaction_id UUID
);
```

## 8. Technical Debt and Future Considerations

### Known Limitations

**Current State**:
- In-memory execution store has no persistence between restarts (mitigated by Supabase repository)
- Limited support for distributed execution (single-instance design)
- No built-in workflow versioning or rollback
- Manual OAuth token refresh (not fully automated)

### Areas for Improvement

**Short-Term (Next Quarter)**:
- [ ] Implement workflow version control with rollback
- [ ] Add distributed tracing with OpenTelemetry
- [ ] Enhance error recovery with automatic retry policies
- [ ] Implement workflow debugging tools (breakpoints, step-through)

**Medium-Term (6-12 Months)**:
- [ ] Support for parallel execution of independent nodes
- [ ] Workflow optimization recommendations based on execution history
- [ ] Advanced monitoring dashboards with custom metrics
- [ ] Workflow testing framework for pre-deployment validation

**Long-Term (12+ Months)**:
- [ ] Distributed execution with message queue (Celery/RabbitMQ)
- [ ] Workflow analytics and intelligence layer
- [ ] Auto-scaling based on execution volume
- [ ] Multi-region deployment support

### Migration Paths

**From V1 to V2**:
- Gradual migration with parallel execution support
- Workflow conversion tool for V1 → V2 format
- Backward compatibility layer for V1 API endpoints
- Deprecation timeline: 6 months after V2 GA

## 9. Appendices

### A. Glossary

- **Attached Node**: TOOL or MEMORY node attached to AI_AGENT node, executed as part of AI context enhancement (not as separate workflow step)
- **Conversion Function**: Python code snippet that transforms data during connection propagation
- **Execution Context**: Complete runtime state including node outputs, pending inputs, and workflow definition
- **Fan-out**: Executing a node multiple times with different inputs (via LOOP/FOR_EACH nodes)
- **HIL (Human-in-the-Loop)**: Workflow pause pattern requiring human interaction before continuation
- **Node Spec**: Centralized specification defining node configuration schema, inputs, outputs, and validation rules
- **Output Port**: Named output channel from a node (e.g., "result", "true", "false", "iteration")
- **Runner**: Executor class responsible for running a specific node type
- **Topological Sort**: Graph ordering algorithm ensuring nodes execute after all dependencies
- **Workflow Graph**: Directed acyclic graph (DAG) representing node dependencies

### B. References

**Internal Documentation**:
- `/docs/tech-design/new_workflow_spec.md`: Complete workflow data model specification
- `/apps/backend/workflow_engine_v2/README.md`: Service-specific setup and development guide
- `/apps/backend/CLAUDE.md`: Backend architecture and development patterns
- `/shared/node_specs/README.md`: Node specification system documentation

**External Resources**:
- FastAPI Documentation: https://fastapi.tiangolo.com/
- Pydantic Models: https://docs.pydantic.dev/
- Supabase Python Client: https://supabase.com/docs/reference/python
- OpenAI API: https://platform.openai.com/docs
- Anthropic Claude API: https://docs.anthropic.com/
- Google Gemini API: https://ai.google.dev/docs

**Code Examples**:
- `/apps/backend/workflow_engine_v2/examples/`: Example workflows and usage patterns
- `/apps/backend/workflow_engine_v2/tests/`: Comprehensive test suite with examples
