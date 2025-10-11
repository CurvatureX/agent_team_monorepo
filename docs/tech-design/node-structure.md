# Node Structure Technical Design

## 1. Executive Summary

This document describes the comprehensive node structure and data models used in the 24/7 AI Teams workflow execution system. The system implements a sophisticated node-based workflow architecture with 8 core node types, each with multiple specialized subtypes. The design emphasizes type safety, runtime flexibility, and advanced patterns like attached nodes for AI agents and human-in-the-loop interactions.

### Key Architectural Decisions

- **Node-Based Workflow Architecture**: All workflow logic is composed of discrete, reusable node types
- **Output Key Routing**: Connections use output keys (e.g., "result", "true", "false") instead of port numbers for flexible data routing
- **Attached Nodes Pattern**: AI_AGENT nodes support attached TOOL and MEMORY nodes that execute within the same context
- **Schema-Driven Configuration**: Node specifications use JSON Schema-compatible definitions for validation and UI generation
- **Centralized Validation**: Node type/subtype combinations are validated through a centralized enum system

### Technology Stack

- **Data Models**: Pydantic v2 with BaseModel for type safety and validation
- **Database**: PostgreSQL via Supabase for persistence
- **Node Specifications**: Python dataclasses with JSON Schema support
- **Runtime Execution**: Tracked through WorkflowExecution and NodeExecution models

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Workflow Definition                       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Metadata + Nodes[] + Connections[] + Triggers[]      │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                 Node Structure Components                    │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │     Node     │  │  Connection  │  │  Position    │      │
│  │              │  │              │  │              │      │
│  │ • id         │  │ • from_node  │  │ • x: float   │      │
│  │ • name       │  │ • to_node    │  │ • y: float   │      │
│  │ • type       │  │ • output_key │  │              │      │
│  │ • subtype    │  │ • conversion │  │              │      │
│  │ • configs    │  │              │  │              │      │
│  │ • input[]    │  └──────────────┘  └──────────────┘      │
│  │ • output[]   │                                           │
│  │ • attached[] │  (AI_AGENT only)                          │
│  └──────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Execution Tracking (Runtime)                    │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         WorkflowExecution                             │   │
│  │  • execution_id                                       │   │
│  │  • status: NEW → RUNNING → SUCCESS/ERROR             │   │
│  │  • node_executions: Dict[node_id, NodeExecution]     │   │
│  │  • execution_sequence: List[node_id]                 │   │
│  │  • current_node_id                                    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         NodeExecution                                 │   │
│  │  • node_id, node_name, node_type, node_subtype       │   │
│  │  • status: pending → running → completed/failed      │   │
│  │  • input_data, output_data                           │   │
│  │  • execution_details (type-specific)                 │   │
│  │  • attached_executions (AI_AGENT only)               │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Component Architecture

#### Core Components

1. **Node Model** (`shared/models/workflow.py`): Base workflow node definition
2. **Node Enums** (`shared/models/node_enums.py`): Type system and validation
3. **Node Specifications** (`shared/node_specs/`): Schema definitions for each node subtype
4. **Execution Models** (`shared/models/execution_new.py`): Runtime tracking structures
5. **Connection Model** (`shared/models/workflow.py`): Data flow between nodes

#### Component Relationships

- **Node ← Node Specification**: Specifications define the schema; nodes are instances
- **Node → Connection**: Connections reference nodes via IDs and output keys
- **WorkflowExecution → NodeExecution**: One-to-many relationship tracking all node executions
- **AI_AGENT Node → Attached Nodes**: AI agents can have child TOOL/MEMORY nodes

## 3. Data Architecture

### 3.1 Data Models

#### Base Node Model

```python
class Node(BaseModel):
    """节点定义 - Core workflow building block"""

    # Identification
    id: str                                    # Unique identifier
    name: str                                  # No spaces allowed
    description: str                           # One-line summary

    # Type information
    type: str                                  # NodeType enum value
    subtype: str                               # Specific node subtype

    # Configuration and parameters
    configurations: Dict[str, Any]             # Static config set at design time
    input_params: Dict[str, Any]               # Runtime input parameters
    output_params: Dict[str, Any]              # Runtime output parameters

    # UI and positioning
    position: Optional[Dict[str, float]]       # {x: float, y: float}

    # AI_AGENT specific
    attached_nodes: Optional[List[str]]        # IDs of TOOL/MEMORY nodes
```

**Field Details:**

- **configurations**: Static parameters that define node behavior (API keys, timeouts, model versions)
- **input_params**: Dynamic runtime data received from upstream nodes
- **output_params**: Dynamic runtime data sent to downstream nodes
- **position**: Canvas coordinates for UI visualization (`{x: 100.0, y: 200.0}`)
- **attached_nodes**: Only for AI_AGENT nodes; references TOOL and MEMORY nodes by ID

#### Connection Model

```python
class Connection(BaseModel):
    """连接定义 - Directed data flow between nodes"""

    id: str                                    # Connection unique identifier
    from_node: str                             # Source node ID
    to_node: str                               # Target node ID
    output_key: str = "result"                 # Output port identifier
    conversion_function: Optional[str] = None  # Python code for data transformation
```

**Output Key Patterns:**

- **Standard nodes**: `"result"` (default)
- **Conditional nodes (IF)**: `"true"`, `"false"`
- **Multi-branch nodes (SWITCH)**: `"case_0"`, `"case_1"`, ..., `"default"`
- **HIL nodes**: `"confirmed"`, `"rejected"`, `"unrelated"`, `"timeout"`

**Conversion Function Example:**

```python
conversion_function = """def convert(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "message": input_data.get("output", ""),
        "timestamp": str(input_data.get("timestamp", ""))
    }"""
```

### 3.2 Node Type System

#### Core Node Types (8 Categories)

```python
class NodeType(str, Enum):
    TRIGGER = "TRIGGER"                        # Workflow entry points
    AI_AGENT = "AI_AGENT"                      # AI model integrations
    EXTERNAL_ACTION = "EXTERNAL_ACTION"        # Third-party service calls
    ACTION = "ACTION"                          # Core system actions
    FLOW = "FLOW"                              # Control flow logic
    HUMAN_IN_THE_LOOP = "HUMAN_IN_THE_LOOP"   # Human interaction points
    TOOL = "TOOL"                              # External tools (MCP)
    MEMORY = "MEMORY"                          # LLM context storage
```

#### Node Subtypes (Selected Examples)

**TRIGGER Subtypes:**
- `MANUAL`: User-initiated execution
- `WEBHOOK`: HTTP endpoint triggers
- `CRON`: Time-based scheduling
- `SLACK`: Slack message/event triggers
- `GITHUB`: GitHub webhook events

**AI_AGENT Subtypes:**
- `OPENAI_CHATGPT`: OpenAI GPT models (GPT-5, GPT-4.1)
- `ANTHROPIC_CLAUDE`: Anthropic Claude models (Sonnet 4, Haiku 3.5)
- `GOOGLE_GEMINI`: Google Gemini models (2.5 Pro, Flash, Flash-Lite)

**HUMAN_IN_THE_LOOP Subtypes:**
- `SLACK_INTERACTION`: Slack-based approvals/input
- `GMAIL_INTERACTION`: Email-based interactions
- `IN_APP_APPROVAL`: Web application approvals

**TOOL Subtypes:**
- `NOTION_MCP_TOOL`: Notion Model Context Protocol tools
- `GOOGLE_CALENDAR_MCP_TOOL`: Calendar MCP tools
- `SLACK_MCP_TOOL`: Slack MCP tools

**MEMORY Subtypes:**
- `CONVERSATION_BUFFER`: Recent conversation storage
- `VECTOR_DATABASE`: Semantic search memory
- `KEY_VALUE_STORE`: Simple key-value persistence

### 3.3 Node Specifications

#### BaseNodeSpec Structure

```python
class BaseNodeSpec(BaseModel):
    """Base class for all node specifications"""

    # Core identification
    type: NodeType                             # Main category
    subtype: str                               # Specific variant
    name: str                                  # Display name
    description: str                           # Human-readable description

    # Schema definitions
    configurations: Dict[str, Any]             # Config parameter schemas
    input_params: Dict[str, Any]               # Input parameter schemas
    output_params: Dict[str, Any]              # Output parameter schemas

    # Legacy compatibility
    default_input_params: Dict[str, Any]       # Default runtime inputs
    default_output_params: Dict[str, Any]      # Default runtime outputs

    # Metadata
    version: str = "1.0"                       # Spec version
    tags: List[str]                            # Categorization tags
    examples: Optional[List[Dict[str, Any]]]   # Usage examples

    # AI guidance
    system_prompt_appendix: Optional[str]      # AI integration hints
```

#### Configuration Schema Format

Each configuration parameter follows this schema:

```python
{
    "parameter_name": {
        "type": "string|integer|float|boolean|enum|json|array",
        "default": <default_value>,
        "description": "Human-readable description",
        "required": True|False,

        # Optional constraints
        "min": <min_value>,               # For numeric types
        "max": <max_value>,               # For numeric types
        "options": ["opt1", "opt2"],      # For enum/select types
        "multiline": True|False,          # For string types
    }
}
```

**Example: OpenAI ChatGPT Configuration**

```python
configurations = {
    "model": {
        "type": "string",
        "default": "gpt-5-nano",
        "description": "OpenAI model version",
        "required": True,
        "options": ["gpt-5", "gpt-5-mini", "gpt-5-nano", "gpt-4.1"]
    },
    "system_prompt": {
        "type": "string",
        "default": "You are a helpful AI assistant.",
        "description": "System prompt defining AI behavior",
        "required": True,
        "multiline": True
    },
    "temperature": {
        "type": "float",
        "default": 0.7,
        "min": 0.0,
        "max": 2.0,
        "description": "Controls randomness of outputs",
        "required": False
    }
}
```

## 4. Implementation Details

### 4.1 Core Components

#### Node Instance Creation

Node instances are created from specifications:

```python
# From BaseNodeSpec.create_node_instance()
def create_node_instance(
    self,
    node_id: str,
    position: Optional[Dict[str, float]] = None,
    attached_nodes: Optional[List[str]] = None,
) -> Node:
    """Create a Node instance from specification"""

    # Extract default values from schema definitions
    runtime_configurations = {
        key: spec.get("default")
        for key, spec in self.configurations.items()
    }

    return Node(
        id=node_id,
        name=self.name,
        description=self.description,
        type=self.type,
        subtype=self.subtype,
        configurations=runtime_configurations,
        input_params=self.default_input_params,
        output_params=self.default_output_params,
        position=position,
        attached_nodes=attached_nodes  # AI_AGENT only
    )
```

#### Node Type Validation

```python
# From shared/models/node_enums.py
VALID_SUBTYPES: Dict[NodeType, Set[str]] = {
    NodeType.TRIGGER: {"MANUAL", "WEBHOOK", "CRON", "SLACK", ...},
    NodeType.AI_AGENT: {"OPENAI_CHATGPT", "ANTHROPIC_CLAUDE", ...},
    # ... all other node types
}

def is_valid_node_subtype_combination(node_type: str, subtype: str) -> bool:
    """Validate if a node_type/subtype combination is valid"""
    try:
        node_type_enum = NodeType(node_type)
        return subtype in VALID_SUBTYPES[node_type_enum]
    except ValueError:
        return False
```

### 4.2 Attached Nodes Pattern (AI_AGENT)

AI_AGENT nodes can attach TOOL and MEMORY nodes that execute within the AI's context:

```python
# Node definition with attached nodes
ai_agent_node = {
    "id": "ai_1",
    "type": "AI_AGENT",
    "subtype": "OPENAI_CHATGPT",
    "configurations": {
        "model": "gpt-5-nano",
        "system_prompt": "You are a calendar management assistant."
    },
    "attached_nodes": [
        "tool_calendar_1",    # TOOL: Google Calendar MCP
        "memory_buffer_1"     # MEMORY: Conversation Buffer
    ]
}

# Attached TOOL node
tool_node = {
    "id": "tool_calendar_1",
    "type": "TOOL",
    "subtype": "GOOGLE_CALENDAR_MCP_TOOL",
    "configurations": {
        "calendar_id": "primary"
    }
}

# Attached MEMORY node
memory_node = {
    "id": "memory_buffer_1",
    "type": "MEMORY",
    "subtype": "CONVERSATION_BUFFER",
    "configurations": {
        "max_messages": 10
    }
}
```

**Execution Flow:**

1. **Pre-execution**: Load memory context from MEMORY nodes
2. **Tool Discovery**: Register tools from TOOL nodes with AI provider
3. **AI Execution**: Generate response with enhanced context and tools
4. **Post-execution**: Store conversation to MEMORY nodes
5. **Result**: Attached node executions stored in `attached_executions` field

**Important**: Attached nodes do NOT appear in workflow execution sequence or connections.

### 4.3 Connection Output Key Routing

Connections use output keys to route data from specific node outputs:

```python
# Standard node connection (default output)
{
    "id": "conn_1",
    "from_node": "ai_agent_1",
    "to_node": "slack_action_1",
    "output_key": "result"  # Default output
}

# Conditional node connection (IF node)
{
    "id": "conn_2",
    "from_node": "if_node_1",
    "to_node": "approval_action",
    "output_key": "true"  # True branch
}

{
    "id": "conn_3",
    "from_node": "if_node_1",
    "to_node": "rejection_action",
    "output_key": "false"  # False branch
}

# Human-in-the-loop node connection
{
    "id": "conn_4",
    "from_node": "hil_slack_1",
    "to_node": "process_approval",
    "output_key": "confirmed"  # User confirmed
}
```

### 4.4 Node Execution Tracking

#### WorkflowExecution Model

```python
class WorkflowExecution(BaseModel):
    """Complete workflow execution state"""

    # Identity
    execution_id: str                          # Unique execution instance
    workflow_id: str                           # Source workflow
    workflow_version: str = "1.0"              # Workflow version

    # Status and timing
    status: ExecutionStatus                    # Overall execution state
    start_time: Optional[int]                  # Epoch milliseconds
    end_time: Optional[int]                    # Epoch milliseconds
    duration_ms: Optional[int]                 # Total duration

    # Trigger information
    trigger_info: TriggerInfo                  # What started this execution

    # Execution tracking
    node_executions: Dict[str, NodeExecution]  # All node execution details
    execution_sequence: List[str]              # Ordered node IDs
    current_node_id: Optional[str]             # Currently executing node
    next_nodes: List[str]                      # Pending nodes

    # Error handling
    error: Optional[ExecutionError]            # Execution-level errors

    # Resource tracking
    credits_consumed: int = 0                  # Total credits used
    tokens_used: Optional[TokenUsage]          # AI token consumption

    # Metadata
    metadata: Optional[Dict[str, Any]]         # Additional context
    created_at: Optional[str]                  # ISO timestamp
    updated_at: Optional[str]                  # ISO timestamp
```

#### NodeExecution Model

```python
class NodeExecution(BaseModel):
    """Individual node execution details"""

    # Node identity
    node_id: str                               # References Node.id
    node_name: str                             # For display
    node_type: str                             # NodeType value
    node_subtype: str                          # Specific subtype

    # Execution state
    status: NodeExecutionStatus                # pending → running → completed/failed
    start_time: Optional[int]                  # When started
    end_time: Optional[int]                    # When finished
    duration_ms: Optional[int]                 # Execution time

    # Data flow
    input_data: Dict[str, Any]                 # Received parameters
    output_data: Dict[str, Any]                # Produced results

    # Type-specific details
    execution_details: NodeExecutionDetails    # AI responses, API calls, etc.

    # Error handling
    error: Optional[NodeError]                 # Node-level errors
    retry_count: int = 0                       # Retry attempts
    max_retries: int = 3                       # Max retry limit

    # Resource tracking
    credits_consumed: int = 0                  # Credits used by this node

    # AI_AGENT specific
    attached_executions: Optional[Dict[str, NodeExecution]]  # Tool/Memory executions
```

#### NodeExecutionDetails (Type-Specific)

```python
class NodeExecutionDetails(BaseModel):
    """Node type-specific execution information"""

    # AI_AGENT fields
    ai_model: Optional[str]                    # "gpt-5-nano"
    prompt_tokens: Optional[int]               # Input tokens
    completion_tokens: Optional[int]           # Output tokens
    model_response: Optional[str]              # AI response text

    # EXTERNAL_ACTION fields
    api_endpoint: Optional[str]                # "https://slack.com/api/chat.postMessage"
    http_method: Optional[str]                 # "POST"
    request_headers: Optional[Dict[str, str]]  # Request headers
    response_status: Optional[int]             # 200
    response_headers: Optional[Dict[str, str]] # Response headers

    # TOOL fields
    tool_name: Optional[str]                   # "create_event"
    tool_parameters: Optional[Dict[str, Any]]  # Tool input params
    tool_result: Optional[Any]                 # Tool output

    # HUMAN_IN_THE_LOOP fields
    user_prompt: Optional[str]                 # Message to user
    user_response: Optional[Any]               # User's response
    waiting_since: Optional[int]               # Wait start time

    # FLOW fields
    condition_result: Optional[bool]           # IF node result
    branch_taken: Optional[str]                # "true" or "false"

    # Common fields
    logs: List[LogEntry]                       # Execution logs
    metrics: Optional[Dict[str, Any]]          # Custom metrics
```

### 4.5 Execution Status Enums

#### WorkflowExecution Status

```python
class ExecutionStatus(str, Enum):
    IDLE = "IDLE"                              # Never executed (default)
    NEW = "NEW"                                # Created but not started
    PENDING = "PENDING"                        # Waiting to start
    RUNNING = "RUNNING"                        # Currently executing
    PAUSED = "PAUSED"                          # Temporarily halted
    SUCCESS = "SUCCESS"                        # Completed successfully
    ERROR = "ERROR"                            # Failed with error
    CANCELED = "CANCELED"                      # User-canceled
    WAITING = "WAITING"                        # Generic wait state
    TIMEOUT = "TIMEOUT"                        # Execution timeout
    WAITING_FOR_HUMAN = "WAITING_FOR_HUMAN"   # HIL pause
```

#### NodeExecution Status

```python
class NodeExecutionStatus(str, Enum):
    PENDING = "pending"                        # Not started
    RUNNING = "running"                        # Currently executing
    WAITING_INPUT = "waiting_input"            # HIL waiting for user
    COMPLETED = "completed"                    # Successfully finished
    FAILED = "failed"                          # Execution error
    SKIPPED = "skipped"                        # Bypassed in flow
    RETRYING = "retrying"                      # Retry in progress
```

## 5. System Interactions

### 5.1 Internal Interactions

#### Node Creation Workflow

```
User Request
    ↓
API Gateway: POST /api/v1/app/workflows
    ↓
Create Workflow with Nodes
    ↓
Validate Node Type/Subtype Combinations
    ↓
Load Node Specifications
    ↓
Apply Default Configurations
    ↓
Store in Database (Supabase)
    ↓
Return Workflow Definition
```

#### Workflow Execution Flow

```
Trigger Event
    ↓
Workflow Scheduler: Create WorkflowExecution
    ↓
Workflow Engine: Initialize Execution Context
    ↓
For Each Node in Sequence:
    ├─ Create NodeExecution (status: pending)
    ├─ Load Node Configuration
    ├─ Get Input Data from Upstream Connections
    ├─ Execute Node Logic
    │   ├─ AI_AGENT: Load attached TOOL/MEMORY → Execute → Store results
    │   ├─ HUMAN_IN_THE_LOOP: Pause execution → Wait for response
    │   ├─ FLOW: Evaluate condition → Route via output_key
    │   └─ Other: Execute action → Return result
    ├─ Update NodeExecution (status: completed/failed)
    └─ Route Output via Connections (using output_key)
    ↓
Update WorkflowExecution (status: SUCCESS/ERROR)
    ↓
Send WebSocket Events
```

### 5.2 Connection Output Routing

Output keys determine data flow paths:

```python
# Example workflow with conditional routing
nodes = [
    {"id": "trigger_1", "type": "TRIGGER", "subtype": "MANUAL"},
    {"id": "ai_1", "type": "AI_AGENT", "subtype": "OPENAI_CHATGPT"},
    {"id": "if_1", "type": "FLOW", "subtype": "IF"},
    {"id": "action_true", "type": "EXTERNAL_ACTION", "subtype": "SLACK"},
    {"id": "action_false", "type": "EXTERNAL_ACTION", "subtype": "SLACK"}
]

connections = [
    # Trigger to AI
    {
        "from_node": "trigger_1",
        "to_node": "ai_1",
        "output_key": "result"
    },
    # AI to IF
    {
        "from_node": "ai_1",
        "to_node": "if_1",
        "output_key": "result"
    },
    # IF true branch
    {
        "from_node": "if_1",
        "to_node": "action_true",
        "output_key": "true"  # Only follows if condition is true
    },
    # IF false branch
    {
        "from_node": "if_1",
        "to_node": "action_false",
        "output_key": "false"  # Only follows if condition is false
    }
]
```

## 6. Non-Functional Requirements

### 6.1 Performance

**Node Validation Performance:**
- Specification lookup: O(1) via registry dictionary
- Type validation: O(1) enum membership check
- Configuration validation: O(n) where n = number of parameters

**Execution Tracking Performance:**
- Node execution updates: O(1) dictionary access
- Execution sequence tracking: O(1) list append
- Attached node lookup: O(1) dictionary access

### 6.2 Scalability

**Node Type Extensibility:**
- New node types: Add enum value + specification
- New subtypes: Add to VALID_SUBTYPES mapping
- Custom configurations: Extend BaseNodeSpec

**Workflow Complexity:**
- Nodes per workflow: No hard limit (tested up to 100+)
- Connections per workflow: No hard limit
- Attached nodes per AI_AGENT: Recommended \< 10

### 6.3 Reliability

**Error Handling:**
- Invalid node type/subtype: Validation error before workflow creation
- Missing required configuration: Caught at node creation time
- Execution errors: Captured in NodeError with retry logic
- Attached node failures: Isolated from main AI execution

**Data Integrity:**
- Node ID uniqueness: Enforced by Pydantic validation
- Connection validity: Validated against node existence
- Type safety: Pydantic models prevent invalid data

### 6.4 Testing & Observability

#### Testing Strategy

**Unit Tests:**
- Node model validation (Pydantic schema tests)
- Node specification instantiation
- Connection output key routing
- Attached nodes pattern validation

**Integration Tests:**
- Workflow creation with mixed node types
- Execution tracking across multiple nodes
- HIL pause/resume with execution state
- AI_AGENT with attached TOOL/MEMORY nodes

**Test Coverage Targets:**
- Node models: \>= 90%
- Execution tracking: \>= 85%
- Node specifications: \>= 80%

#### Observability

**Key Metrics:**
- Node execution duration by type/subtype
- Configuration validation errors
- Attached node execution count
- Output key routing success rate

**Logging Strategy:**
- Node creation: INFO level with type/subtype
- Execution start/end: INFO level with node_id
- Configuration errors: ERROR level with validation details
- Attached node executions: DEBUG level

**Monitoring & Alerting:**
- Alert on node validation failures \> 5% of workflows
- Track execution duration percentiles (p50, p95, p99)
- Monitor attached node execution failures
- Dashboard: Node type distribution, execution success rate

## 7. Technical Debt and Future Considerations

### 7.1 Known Limitations

1. **Configuration Schema Complexity**: Some node types have \>20 configuration parameters, making UI generation complex
2. **Attached Nodes Isolation**: Attached node errors can fail the entire AI_AGENT execution
3. **Output Key Naming**: No formal validation for custom output key names (beyond "result", "true", "false")
4. **Node Name Constraints**: No spaces allowed, but no length limits enforced

### 7.2 Areas for Improvement

1. **Schema Simplification**: Group related configurations into sub-objects
2. **Attached Node Resilience**: Allow AI execution to continue even if attached nodes fail
3. **Output Key Registry**: Formal registry of valid output keys per node type
4. **Node Name Validation**: Add length limits and additional character restrictions

### 7.3 Planned Enhancements

1. **Visual Node Builder**: UI component for graphical node configuration
2. **Node Templates Library**: Pre-configured node instances for common use cases
3. **Advanced Validation**: Cross-field validation (e.g., if model=X, then temperature \< Y)
4. **Dynamic Schema Updates**: Hot-reload node specifications without redeployment

### 7.4 Migration Paths

**From Legacy Port-Based Routing:**
- Update all connections to use output_key field
- Remove InputPort/OutputPort models
- Update UI to show output key selection

**From Hardcoded AI Roles:**
- Migrate to provider-based AI agents (OPENAI_CHATGPT, etc.)
- Convert role-specific configs to system_prompt
- Update workflow templates with new AI node structure

## 8. Appendices

### A. Glossary

- **Node**: Basic building block of a workflow; represents a single operation
- **Node Type**: One of 8 core categories (TRIGGER, AI_AGENT, etc.)
- **Node Subtype**: Specific variant within a type (e.g., OPENAI_CHATGPT)
- **Configuration**: Static parameters set at workflow design time
- **Input Parameters**: Runtime data received from upstream nodes
- **Output Parameters**: Runtime data sent to downstream nodes
- **Output Key**: Identifier for a specific output port (e.g., "result", "true")
- **Attached Nodes**: TOOL/MEMORY nodes linked to an AI_AGENT node
- **Node Specification**: Schema definition for a node type/subtype
- **Connection**: Directed edge between two nodes with optional data transformation
- **WorkflowExecution**: Runtime instance tracking complete workflow execution
- **NodeExecution**: Runtime instance tracking single node execution

### B. References

#### Internal Documentation
- `/apps/backend/shared/models/workflow.py` - Node and Connection models
- `/apps/backend/shared/models/execution_new.py` - Execution tracking models
- `/apps/backend/shared/models/node_enums.py` - Node type system
- `/apps/backend/shared/node_specs/base.py` - Node specification base classes
- `/docs/tech-design/new_workflow_spec.md` - Complete workflow specification

#### Node Specification Examples
- `/apps/backend/shared/node_specs/AI_AGENT/OPENAI_CHATGPT.py` - OpenAI agent spec
- `/apps/backend/shared/node_specs/TRIGGER/WEBHOOK.py` - Webhook trigger spec
- `/apps/backend/shared/node_specs/FLOW/IF.py` - Conditional flow spec
- `/apps/backend/shared/node_specs/HUMAN_IN_THE_LOOP/SLACK_INTERACTION.py` - HIL spec

#### External Resources
- Pydantic Documentation: https://docs.pydantic.dev/
- JSON Schema Specification: https://json-schema.org/
- Supabase PostgreSQL: https://supabase.com/docs/guides/database
