# Workflow Agent Technical Design

## 1. Executive Summary

The Workflow Agent is an AI-powered workflow generation service that transforms natural language requirements into executable workflow specifications using LangGraph-based state machines and MCP (Model Context Protocol) integration.

### Key Capabilities
- **AI-Driven Workflow Generation**: Converts user requirements into complete workflow DSL through conversational interaction
- **MCP Tool Integration**: Uses Model Context Protocol to dynamically query available node types and specifications from the API Gateway
- **Multi-Provider LLM Support**: Flexible AI provider integration supporting OpenAI, Anthropic Claude, and OpenRouter
- **Stateful Conversation Management**: Maintains session state in Supabase with full conversation history
- **Real-time Streaming**: Server-Sent Events (SSE) based streaming for responsive user experience
- **Edit & Copy Workflows**: Support for modifying existing workflows or creating copies with changes

### Technology Stack
- **Framework**: FastAPI (Python 3.11+)
- **AI Orchestration**: LangGraph for state machine management
- **LLM Providers**: OpenAI GPT-5/GPT-4, Anthropic Claude via LangChain
- **State Persistence**: Supabase PostgreSQL with RLS
- **Deployment**: AWS ECS Fargate with Docker containerization

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────┐
│   API Gateway   │
│   Port: 8000    │
└────────┬────────┘
         │ HTTP/REST /api/v1/app/assistant/chat
         ├─── Provides MCP endpoints: /api/v1/mcp/tools, /api/v1/mcp/invoke
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│              Workflow Agent (Port 8001)                     │
│                                                             │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │  FastAPI Server  │─────▶│  LangGraph Agent  │           │
│  │  (SSE Streaming) │      │  (State Machine)  │           │
│  └────────┬─────────┘      └────────┬──────────┘           │
│           │                         │                       │
│           │                         ▼                       │
│           │              ┌────────────────────┐             │
│           │              │  2-Node Workflow:  │             │
│           │              │  • Clarification   │             │
│           │              │  • Workflow Gen    │             │
│           │              │  • Conversion Gen  │             │
│           │              └────────┬───────────┘             │
│           │                       │                         │
│           ▼                       ▼                         │
│  ┌──────────────────┐   ┌──────────────────┐              │
│  │  State Manager   │   │   MCP Client     │              │
│  │  (Supabase)      │   │   (API GW Tools) │              │
│  └──────────────────┘   └──────────────────┘              │
└─────────────────────────────────────────────────────────────┘
         │                         │
         │ Supabase                │ HTTP → API Gateway
         │ workflow_agent_states   │ /api/v1/mcp/tools
         │                         │ /api/v1/mcp/invoke
         ▼                         ▼
┌──────────────────┐     ┌────────────────────┐
│    Supabase      │     │  Workflow Engine   │
│    PostgreSQL    │     │    (Port 8002)     │
└──────────────────┘     └────────────────────┘
```

### 2.2 Component Architecture

#### Core Components

1. **FastAPI Server** (`services/fastapi_server.py`)
   - Exposes `/process-conversation` endpoint for client interactions
   - Implements Server-Sent Events (SSE) streaming for real-time responses
   - Manages request lifecycle and client disconnection handling
   - Health check endpoint at `/health`

2. **LangGraph State Machine** (`agents/workflow_agent.py`, `graph.py`)
   - Orchestrates workflow generation through 3 core nodes:
     - **Clarification Node**: Analyzes user intent, asks clarifying questions
     - **Workflow Generation Node**: Creates workflow DSL using MCP tools
     - **Conversion Generation Node**: Generates data mapping functions between nodes
   - Conditional routing based on state transitions
   - Compiled graph exported for both runtime and LangGraph Studio debugging

3. **Node Executors** (`agents/nodes.py`)
   - **WorkflowAgentNodes**: Container for all node execution logic
   - Clarification logic with JSON-structured output
   - MCP-integrated workflow generation with tool calling
   - Concurrent LLM enhancement for AI agent prompts
   - Conversion function generation with parallel execution

4. **MCP Tool Integration** (`agents/mcp_tools.py`)
   - **MCPToolCaller**: HTTP client for API Gateway MCP endpoints
   - Connection pooling with aiohttp for performance
   - LangChain tool adapters for `get_node_types` and `get_node_details`
   - Provider-agnostic tool conversion (OpenAI, Claude, Gemini)

5. **State Management** (`services/state_manager.py`)
   - **WorkflowAgentStateManager**: CRUD operations for `workflow_agent_states` table
   - Supabase integration with RLS-based access control
   - Session-based state retrieval and updates
   - Conversion between database format and LangGraph WorkflowState

6. **LLM Provider Abstraction** (`core/llm_provider.py`)
   - **LLMFactory**: Creates LLM instances based on configuration
   - Supports OpenAI, Anthropic, and OpenRouter providers
   - Configurable temperature, max_tokens, and timeout
   - Special handling for GPT-5 models (max_completion_tokens vs max_tokens)

## 3. Data Architecture

### 3.1 Data Models

#### WorkflowState (LangGraph Runtime)
```python
class WorkflowState(TypedDict):
    # Session and user info
    session_id: str
    user_id: str
    created_at: int  # timestamp in milliseconds
    updated_at: int

    # Stage tracking
    stage: WorkflowStage  # clarification | workflow_generation | conversion_generation | completed | failed
    previous_stage: NotRequired[WorkflowStage]

    # Core workflow data
    intent_summary: str
    conversations: List[Conversation]  # [{role, text, timestamp, metadata}]

    # Clarification context
    clarification_context: ClarificationContext  # {purpose, collected_info, pending_questions, origin}

    # Workflow data (runtime only)
    current_workflow: NotRequired[Any]  # Transient workflow JSON
    source_workflow: NotRequired[Any]  # For edit/copy mode
    workflow_context: NotRequired[Dict[str, Any]]  # {origin: create|edit|copy, source_workflow_id}

    # Workflow creation tracking
    workflow_id: NotRequired[str]  # ID from workflow_engine
    workflow_creation_result: NotRequired[Dict[str, Any]]
    workflow_creation_error: NotRequired[str]

    # Failure tracking
    workflow_generation_failed: NotRequired[bool]
    final_error_message: NotRequired[str]
```

#### WorkflowAgentStateModel (Database Persistence)
```python
class WorkflowAgentStateModel(BaseModel):
    id: UUID
    session_id: str
    user_id: Optional[str]

    # Timestamps (milliseconds)
    created_at: int
    updated_at: int

    # Stage tracking
    stage: WorkflowStageEnum  # clarification | workflow_generation | completed | failed
    previous_stage: Optional[WorkflowStageEnum]

    # Persistent data
    intent_summary: str
    conversations: List[ConversationMessage]

    # Debug state (NOT stored: debug_result as text, debug_loop_count as int)
    debug_result: Optional[str]  # For legacy compatibility
    debug_loop_count: int = 0

    # Workflow tracking
    template_workflow: Optional[Dict[str, Any]]
    workflow_id: Optional[str]  # Critical: ID of created workflow

    # Failure state
    final_error_message: Optional[str]
```

**Key Design Decision**: `current_workflow` is NOT persisted to the database. It's transient runtime data that exists only during workflow generation. Only the final `workflow_id` is stored after successful creation in the workflow_engine.

### 3.2 Data Flow

#### Workflow Generation Flow
```
1. User sends message
   ↓
2. Create/retrieve workflow_agent_state from Supabase
   ↓
3. Convert to LangGraph WorkflowState
   ↓
4. LangGraph executes nodes:
   • Clarification: Update intent_summary, pending_questions
   • Workflow Generation: Create current_workflow (in-memory)
   • Conversion Generation: Enhance workflow, persist to workflow_engine
   ↓
5. Stream responses via SSE:
   • STATUS_CHANGE: Stage transitions
   • MESSAGE: Assistant responses
   • WORKFLOW: Generated workflow JSON (with workflow_id)
   ↓
6. Save updated state to Supabase (including workflow_id)
```

#### MCP Tool Calling Flow
```
1. LLM bound with MCP tools (get_node_types, get_node_details)
   ↓
2. LLM decides to call tool (e.g., get_node_types)
   ↓
3. MCPToolCaller sends HTTP POST to API Gateway /api/v1/mcp/invoke
   ↓
4. API Gateway queries workflow_engine MCP server
   ↓
5. Return structured node specifications
   ↓
6. LLM processes tool results
   ↓
7. LLM generates workflow JSON with correct node types/parameters
```

## 4. Implementation Details

### 4.1 Core Components

#### Clarification Node
**Purpose**: Understand user intent through minimal interaction

**Key Implementation**:
```python
async def clarification_node(self, state: WorkflowState) -> WorkflowState:
    # Extract context
    user_message = get_user_message(state)
    existing_intent = get_intent_summary(state)
    conversation_history = self._get_conversation_context(state)

    # Render prompts using prompt engine
    system_prompt = await self.prompt_engine.render_prompt("clarification_f2_system", ...)
    user_prompt = await self.prompt_engine.render_prompt("clarification_f2_user", ...)

    # Call LLM with JSON response format
    response = await self.llm.ainvoke(messages, response_format={"type": "json_object"})

    # Parse structured output
    clarification_output = json.loads(response.content)

    # Update state
    state["intent_summary"] = clarification_output.get("intent_summary", "")
    state["clarification_context"] = {
        "pending_questions": [clarification_output.get("clarification_question", "")]
        if clarification_output.get("clarification_question") else []
    }

    return state
```

**Decision Logic** (`should_continue`):
- If `pending_questions` exist → END (wait for user)
- If `is_clarification_ready(state)` → workflow_generation
- Otherwise → END

#### Workflow Generation Node
**Purpose**: Generate complete workflow DSL using MCP tools

**Key Implementation**:
```python
async def workflow_generation_node(self, state: WorkflowState) -> WorkflowState:
    # Prepare context
    intent_summary = get_intent_summary(state)
    creation_error = state.get("workflow_creation_error")  # From previous attempt

    # Render system prompt with MCP tool guidance
    system_prompt = await self.prompt_engine.render_prompt("workflow_gen_simplified", ...)

    # Natural tool calling - LLM decides when to use MCP tools
    workflow_json = await self._generate_with_natural_tools(messages, state)

    # Parse and normalize workflow structure
    workflow = json.loads(workflow_json)
    workflow = self._normalize_workflow_structure(workflow)

    # Pre-fetch node specifications from MCP
    await self._prefetch_node_specs_for_workflow(workflow)
    await self._hydrate_nodes_from_specs(workflow)

    # Validate TOOL/MEMORY nodes not in connections
    invalid_conn_errors = self._validate_no_tool_memory_connections(workflow)
    if invalid_conn_errors:
        return self._fail_workflow_generation(state, error_message=...)

    # Enhance AI Agent prompts (concurrent LLM calls)
    workflow = await self._enhance_ai_agent_prompts_with_llm(workflow)

    # Store workflow and advance to conversion generation
    state["current_workflow"] = workflow
    state["stage"] = WorkflowStage.CONVERSION_GENERATION
    return state
```

**MCP Tool Calling**:
```python
async def _generate_with_natural_tools(self, messages: List, state: Optional[dict]) -> str:
    # Initial LLM invocation with bound tools
    response = await self.llm_with_tools.ainvoke(messages)

    # Process tool calls iteratively (max 5 iterations)
    while hasattr(response, "tool_calls") and response.tool_calls:
        for tool_call in response.tool_calls:
            tool_name = tool_call.name
            tool_args = tool_call.args

            # Call MCP tool via HTTP
            result = await self.mcp_client.call_tool(tool_name, tool_args)

            # Cache node specs for validation
            if tool_name == "get_node_details":
                for node_spec in result.get("nodes", []):
                    cache_key = f"{node_spec['node_type']}:{node_spec['subtype']}"
                    self.node_specs_cache[cache_key] = node_spec

            # Add filtered result to conversation
            result_str = self._filter_mcp_response_for_prompt(result, tool_name)
            current_messages.append(HumanMessage(content=f"Tool result: {result_str}"))

        # Continue conversation with tool results
        response = await self.llm_with_tools.ainvoke(current_messages)

    return response.content  # Final workflow JSON
```

#### Conversion Generation Node
**Purpose**: Generate data mapping functions between workflow nodes

**Key Implementation**:
```python
async def conversion_generation_node(self, state: WorkflowState) -> WorkflowState:
    workflow = state.get("current_workflow")

    # Generate conversion functions for all connections
    generator = ConversionFunctionGenerator(
        prompt_engine=self.prompt_engine,
        llm=self.llm,
        spec_fetcher=self._get_or_fetch_node_spec,
        logger=logger
    )

    # Concurrent generation with semaphore (max 4 concurrent)
    workflow = await generator.populate(workflow, intent_summary=state.get("intent_summary"))

    # Ensure all nodes have descriptions
    self._ensure_node_descriptions(workflow, intent_summary)

    # Create workflow in workflow_engine
    engine_client = WorkflowEngineClient()
    creation_result = await engine_client.create_workflow(
        workflow,
        state.get("user_id"),
        state.get("session_id")
    )

    if creation_result.get("success"):
        workflow_id = creation_result["workflow"]["id"]
        state["workflow_id"] = workflow_id
        state["stage"] = WorkflowStage.WORKFLOW_GENERATION
        # Add completion message to conversations
    else:
        state["workflow_creation_error"] = creation_result.get("error")
        state["stage"] = WorkflowStage.FAILED

    return state
```

### 4.2 Technical Decisions

#### Why LangGraph?
**Rationale**:
- Stateful multi-turn conversations with persistent state
- Conditional routing based on complex business logic
- Built-in checkpointing and recovery
- LangGraph Studio integration for visual debugging

**Trade-offs**:
- Learning curve for LangGraph-specific patterns
- More complex than simple request/response patterns
- Excellent for conversational workflows, overkill for single-turn tasks

#### Why MCP Integration?
**Rationale**:
- **Dynamic Node Discovery**: Node types and specifications evolve independently of the agent
- **Single Source of Truth**: API Gateway MCP server provides authoritative node specs from workflow_engine
- **Type Safety**: LLM receives exact parameter types/enums from specs, reducing generation errors
- **Extensibility**: New node types automatically available without code changes

**Implementation**:
- HTTP-based MCP client (`MCPToolCaller`) with connection pooling
- LangChain tool adapters for seamless LLM integration
- Aggressive caching of node specs to reduce API calls

#### Why Supabase for State?
**Rationale**:
- PostgreSQL with RLS provides multi-tenant isolation
- JSON column support for flexible conversation storage
- Real-time subscriptions (future use for collaboration)
- Integrated with existing system architecture

**Performance Optimization**:
- Use `workflow_id` instead of storing full `current_workflow` JSON
- Store only essential fields (intent_summary, conversations, workflow_id)
- Transient runtime data (`current_workflow`) lives only in memory during generation

#### Multi-Provider LLM Support
**Design**:
```python
class LLMFactory:
    @staticmethod
    def create_llm(config: Optional[LLMConfig] = None, ...) -> BaseChatModel:
        if config.provider == LLMProvider.OPENROUTER:
            return ChatOpenAI(base_url=config.openrouter_base_url, ...)
        elif config.provider == LLMProvider.ANTHROPIC:
            return ChatAnthropic(api_key=config.anthropic_api_key, ...)
        else:
            return ChatOpenAI(api_key=config.openai_api_key, ...)
```

**Configuration**:
- Environment variable driven (`LLM_PROVIDER`, `OPENAI_MODEL`, `ANTHROPIC_MODEL`)
- Per-request model override support
- Fallback to default provider if none specified

## 5. System Interactions

### 5.1 Internal Interactions

#### LangGraph State Transitions
```
START (user message)
  ↓
Clarification Node
  ├─ If pending_questions → END (wait for user)
  ├─ If clarification_ready → Workflow Generation Node
  │                             ↓
  │                           Conversion Generation Node
  │                             ├─ If success → END (workflow_id stored)
  │                             └─ If failed → FAILED state
  └─ Otherwise → END
```

#### SSE Streaming Protocol
```python
# 1. Status Change Event
{
    "session_id": "session-123",
    "response_type": "STATUS_CHANGE",
    "is_final": false,
    "status_change": {
        "previous_stage": "clarification",
        "current_stage": "workflow_generation",
        "stage_state": {...},
        "node_name": "workflow_generation"
    }
}

# 2. Message Event
{
    "session_id": "session-123",
    "response_type": "MESSAGE",
    "message": "I need more information about...",
    "is_final": false
}

# 3. Workflow Event
{
    "session_id": "session-123",
    "response_type": "WORKFLOW",
    "workflow": "{...workflow JSON...}",
    "is_final": false
}

# 4. Error Event
{
    "session_id": "session-123",
    "response_type": "ERROR",
    "error": {
        "error_code": "PROCESSING_ERROR",
        "message": "...",
        "details": "...",
        "is_recoverable": true
    },
    "is_final": true
}
```

### 5.2 External Integrations

#### API Gateway Integration
**Endpoints Used**:
- `GET /api/v1/mcp/tools` - List available MCP tools
- `POST /api/v1/mcp/invoke` - Invoke MCP tool (get_node_types, get_node_details)

**Authentication**: API Key based (dev_default for internal services)

**Request/Response Format**:
```python
# Request
POST /api/v1/mcp/invoke
{
    "name": "get_node_details",
    "tool_name": "get_node_details",
    "arguments": {
        "nodes": [
            {"node_type": "TRIGGER", "subtype": "SLACK"},
            {"node_type": "AI_AGENT", "subtype": "OPENAI_CHATGPT"}
        ],
        "include_examples": true,
        "include_schemas": true
    }
}

# Response
{
    "result": {
        "structuredContent": {
            "nodes": [
                {
                    "node_type": "TRIGGER",
                    "subtype": "SLACK",
                    "name": "Slack Trigger",
                    "description": "...",
                    "parameters": [
                        {"name": "channel_id", "type": "string", "required": true},
                        {"name": "event_type", "type": "string", "enum_values": ["message", "reaction_added"]}
                    ],
                    "configurations": {...},
                    "input_params_schema": {...},
                    "output_params_schema": {...}
                },
                ...
            ]
        }
    }
}
```

#### Workflow Engine Integration
**Client**: `WorkflowEngineClient` (`services/workflow_engine_client.py`)

**Operations**:
```python
# Create workflow
POST {WORKFLOW_ENGINE_URL}/workflows
{
    "workflow": {...},  # Complete workflow DSL
    "user_id": "user-123",
    "session_id": "session-456"
}

# Response
{
    "success": true,
    "workflow": {
        "id": "workflow-uuid",
        "name": "...",
        "nodes": [...],
        "connections": [...],
        ...
    }
}

# Get workflow (for edit/copy mode)
GET {WORKFLOW_ENGINE_URL}/workflows/{workflow_id}
```

#### Supabase Integration
**Tables**:
- `workflow_agent_states` - Session state persistence

**Operations**:
```python
# Create state
INSERT INTO workflow_agent_states (session_id, user_id, stage, intent_summary, conversations, ...)

# Get state by session
SELECT * FROM workflow_agent_states
WHERE session_id = ?
ORDER BY updated_at DESC
LIMIT 1

# Update state
UPDATE workflow_agent_states
SET stage = ?, intent_summary = ?, conversations = ?, workflow_id = ?, updated_at = ?
WHERE id = ?
```

**RLS Policies**: Row-level security enforces user_id based access control

## 6. Non-Functional Requirements

### 6.1 Performance

**Targets**:
- Clarification response: \< 3 seconds for initial intent analysis
- Workflow generation: \< 30 seconds for 5-10 node workflows
- MCP tool calls: \< 2 seconds per tool invocation
- State persistence: \< 500ms per save operation

**Optimization Strategies**:
- **Connection Pooling**: aiohttp TCPConnector with 100 total / 30 per-host limits
- **MCP Spec Caching**: In-memory cache for node specifications (keyed by `node_type:subtype`)
- **Concurrent LLM Calls**: Parallel AI Agent prompt enhancement (max 5 concurrent)
- **Concurrent Conversion Generation**: Parallel conversion function generation (max 4 concurrent)
- **Response Filtering**: Aggressive filtering of MCP responses to reduce prompt size
- **Conversation Capping**: Limit conversation history to 10 most recent user-assistant pairs

**Measured Performance** (from implementation):
- MCP tool call overhead: ~60-100ms per call
- Workflow generation with 2 MCP calls: ~15-25 seconds total
- LLM prompt enhancement (5 nodes): ~8-12 seconds with batching

### 6.2 Scalability

**Horizontal Scaling**:
- Stateless service design (all state in Supabase)
- No in-process caching dependencies (MCP cache is session-scoped)
- ECS service auto-scaling based on CPU/memory

**Resource Limits**:
- Max workflow nodes: 50 (configurable via `MAX_WORKFLOW_NODES`)
- Max tool calling iterations: 5 (prevents infinite loops)
- Max conversation history: 10 pairs (prevents context overflow)
- Connection pool: 100 total, 30 per host

**Load Balancing**:
- AWS Application Load Balancer distributes traffic
- Session affinity not required (stateless)

### 6.3 Security

**Authentication**:
- Internal service-to-service: API Key (`dev_default`)
- User requests: JWT tokens from Supabase (validated by API Gateway)

**Data Protection**:
- Supabase RLS policies enforce user isolation
- No sensitive data in logs (API keys, tokens filtered)
- Environment-based secrets management (AWS SSM Parameters)

**API Security**:
- MCP endpoints rate-limited at API Gateway level
- Timeout enforcement (60s total, 10s connect for MCP calls)
- Input validation via Pydantic models

### 6.4 Reliability

**Error Handling**:
```python
# Structured error responses
class WorkflowGenerationError(Exception):
    """Raised when workflow generation fails after max attempts"""

# State-based failure tracking
state["stage"] = WorkflowStage.FAILED
state["final_error_message"] = error_message
```

**Retry Mechanisms**:
- LLM calls: 3 retries with exponential backoff (via LangChain)
- MCP tool calls: No automatic retry (fail fast)
- Workflow generation: 1 retry on creation error (via `workflow_creation_error` field)

**Failure Recovery**:
- Client disconnection: State saved to Supabase, resumable
- LangGraph node failure: Error captured in state, workflow marked FAILED
- Database failure: Fallback to in-memory state (degraded mode)

**Circuit Breaking**:
- MCP client timeout: 60s total, 10s connect
- LLM timeout: 1200s (20 minutes) for long-running generation
- Workflow Engine timeout: 300s (5 minutes)

### 6.5 Testing & Observability

#### Testing Strategy

**Unit Tests**:
- Node execution logic (`tests/test_simplified_nodes.py`)
- State transition validation
- MCP tool calling mocks
- Conversion function generation

**Integration Tests**:
- End-to-end workflow generation with real MCP server
- Multi-turn conversation scenarios
- Edit/copy workflow modes
- Error handling and recovery

**Test Data Management**:
- Mock node specifications for offline testing
- Sample workflow templates
- Predefined conversation scenarios

#### Observability

**Logging**:
- Structured JSON logging with trace_id propagation
- Log levels: DEBUG (verbose), INFO (standard), WARNING, ERROR
- Contextual fields: session_id, user_id, stage, node_name, trace_id

**Key Metrics**:
- Workflow generation latency (by node count)
- MCP tool call success rate and latency
- LLM API call latency and token usage
- State persistence latency
- SSE connection duration

**Distributed Tracing**:
- OpenTelemetry integration (optional, via `OTEL_SDK_DISABLED`)
- Trace spans for LangGraph nodes, MCP calls, LLM invocations
- OTLP export to AWS OTEL Collector (production) or local collector (dev)

**Health Monitoring**:
```bash
# Health check endpoint
GET /health
Response: {"status": "healthy", "service": "workflow_agent_fastapi"}

# ECS health check
CMD curl -f http://localhost:8001/health || exit 1
Start period: 120s (allows model loading)
```

**Alerting Thresholds**:
- Workflow generation failure rate \> 10%
- MCP tool call error rate \> 5%
- State persistence failure rate \> 1%
- Average latency \> 60s for simple workflows

## 7. Technical Debt and Future Considerations

### Known Limitations

1. **Single Workflow Generation Pass**
   - Current implementation generates workflow in one pass without iterative validation
   - Trade-off: Faster generation vs. potential incompleteness
   - Future: Add optional validation loop with LLM-based completeness check

2. **In-Memory MCP Spec Caching**
   - Node specs cached in memory, not shared across instances
   - Impact: Duplicate MCP calls across service instances
   - Future: Implement Redis-based shared cache

3. **Limited Conversation History**
   - Only 10 most recent conversation pairs retained in prompt context
   - Risk: Loss of important early context in long sessions
   - Future: Implement conversation summarization for older messages

4. **No Workflow Validation**
   - Workflows sent to engine without deep validation
   - Reliance on engine-side validation
   - Future: Add pre-flight validation using MCP specs

5. **Debug Result Field**
   - `debug_result` and `debug_loop_count` fields exist but unused in current 2-node architecture
   - Legacy from 6-node architecture with debug node
   - Future: Remove deprecated fields in next schema migration

### Areas for Improvement

**Performance Optimization**:
- Implement GraphQL-style field selection for MCP tool responses (reduce payload size)
- Add request deduplication for identical MCP tool calls within same session
- Optimize prompt rendering with template caching
- Use smaller LLM models for clarification (GPT-4o-mini vs GPT-5)

**User Experience**:
- Add workflow preview before creation
- Implement undo/redo for conversation steps
- Add workflow complexity estimation upfront
- Support batch workflow generation (multiple workflows from one conversation)

**Robustness**:
- Add schema validation for LLM-generated workflow JSON
- Implement automatic workflow repair for common errors
- Add fallback to simpler generation strategy on repeated failures
- Circuit breaker for MCP tool calls

**Observability**:
- Add user-facing progress indicators (% complete for workflow generation)
- Track and log token usage per session for cost analysis
- Implement A/B testing framework for prompt variations
- Add conversation replay for debugging

### Planned Enhancements

**Q1 2025**:
- [ ] Workflow templates library (common patterns pre-generated)
- [ ] Multi-language support (prompt localization)
- [ ] Enhanced error messages with suggested fixes

**Q2 2025**:
- [ ] Collaborative workflow editing (multi-user sessions)
- [ ] Workflow version control and rollback
- [ ] Integration with workflow marketplace

**Q3 2025**:
- [ ] Natural language workflow testing ("test this workflow with X data")
- [ ] Automated workflow optimization suggestions
- [ ] Voice-based workflow creation

### Migration Paths

**From 6-Node to 2-Node Architecture** (Completed):
- Simplified state machine: Removed gap_analysis, negotiation, debug nodes
- Faster generation: Reduced average time from 45s to 25s
- Better UX: Fewer clarification rounds, more direct workflow generation

**Future Migration to Prompt Caching**:
- Anthropic Claude supports prompt caching for repeated content
- Opportunity: Cache MCP tool responses, node specs
- Estimated savings: 50-70% reduction in input tokens for multi-turn sessions

**Future Migration to Streaming Workflow Generation**:
- Stream workflow nodes as they're generated (not all-at-once)
- Allows early feedback and validation
- Requires workflow_engine support for incremental workflow building

## 8. Appendices

### A. Glossary

- **LangGraph**: LangChain's framework for building stateful, multi-agent workflows using directed graphs
- **MCP**: Model Context Protocol - standardized protocol for LLM tool discovery and invocation
- **SSE**: Server-Sent Events - HTTP protocol for server-to-client streaming
- **RLS**: Row Level Security - PostgreSQL feature for fine-grained access control
- **DSL**: Domain-Specific Language - specialized workflow description format
- **WorkflowState**: LangGraph's runtime state object passed between nodes
- **Node Executor**: LangGraph node implementation (clarification, workflow_generation, etc.)
- **Conversion Function**: Python function that transforms data between workflow nodes
- **Session**: User interaction session tracked by session_id in workflow_agent_states
- **Clarification Context**: Metadata about clarification state (pending questions, collected info)
- **MCP Tool**: Discoverable function exposed via Model Context Protocol (get_node_types, get_node_details)

### B. References

**Internal Documentation**:
- `/apps/backend/workflow_agent/CLAUDE.md` - Workflow Agent development guide
- `/apps/backend/CLAUDE.md` - Backend services architecture
- `/CLAUDE.md` - Monorepo architecture overview
- `/docs/tech-design/new_workflow_spec.md` - Workflow DSL specification
- `/shared/node_specs/` - Node type specifications

**External Resources**:
- [LangGraph Documentation](https://python.langchain.com/docs/langgraph)
- [LangChain Documentation](https://python.langchain.com/)
- [Model Context Protocol Spec](https://spec.modelcontextprotocol.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Supabase Documentation](https://supabase.com/docs)

**Architecture Decisions**:
- ADR-001: Migration from gRPC to FastAPI (Jan 2025)
- ADR-002: 6-Node to 2-Node Simplification (Feb 2025)
- ADR-003: MCP Integration for Node Discovery (Feb 2025)
- ADR-004: Workflow Creation in Conversion Node (Mar 2025)

**Key Files**:
```
apps/backend/workflow_agent/
├── main.py                          # FastAPI server entry point
├── graph.py                         # LangGraph graph definition
├── agents/
│   ├── workflow_agent.py            # LangGraph agent orchestration
│   ├── nodes.py                     # Node execution logic (2400+ lines)
│   ├── state.py                     # WorkflowState TypedDict definitions
│   ├── mcp_tools.py                 # MCP client integration
│   └── exceptions.py                # Custom exceptions
├── core/
│   ├── config.py                    # Settings and configuration
│   ├── llm_provider.py              # Multi-provider LLM factory
│   └── prompt_engine.py             # Prompt template rendering
├── models/
│   └── workflow_agent_state.py      # Pydantic state model
├── services/
│   ├── fastapi_server.py            # FastAPI app and endpoints
│   ├── state_manager.py             # Supabase state CRUD
│   └── workflow_engine_client.py    # Workflow Engine HTTP client
└── tests/
    ├── test_simplified_nodes.py     # Node execution tests
    └── test_attached_nodes_validation.py  # Validation tests
```
