# Database Design Technical Specification

## 1. Executive Summary

### Overview
The 24/7 AI Teams platform uses **PostgreSQL** as its primary database, hosted and managed through **Supabase**. The database design supports a comprehensive workflow automation system with AI-powered agents, real-time execution tracking, multi-tenant isolation, and sophisticated memory management.

### Key Architectural Decisions
- **Database Technology**: PostgreSQL 15+ with Supabase managed services
- **Multi-Tenancy**: Row Level Security (RLS) policies for user data isolation
- **Vector Search**: pgvector extension for semantic search and RAG capabilities
- **Real-time Updates**: Supabase Realtime for live execution status updates
- **Authentication**: Supabase Auth with `auth.users` as the canonical user source

### Technology Stack
- **Database**: PostgreSQL 15+ (Supabase)
- **Extensions**:
  - `uuid-ossp` - UUID generation
  - `vector` - Vector similarity search (pgvector)
  - Built-in full-text search (tsvector)
- **ORM**: SQLAlchemy (backend services)
- **Migration Tool**: Supabase CLI migrations
- **Connection Pooling**: Built-in Supabase connection pooler

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Supabase PostgreSQL                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌───────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │  auth.users   │  │  Workflow    │  │  Memory & Vector   │  │
│  │  (Supabase)   │──▶│  Execution   │  │  Storage           │  │
│  └───────────────┘  └──────────────┘  └────────────────────┘  │
│                              │                                   │
│  ┌───────────────┐  ┌───────▼──────┐  ┌────────────────────┐  │
│  │  Integration  │  │  HIL System  │  │  Trigger System    │  │
│  │  & OAuth      │  │  (Pause/     │  │  (Scheduler)       │  │
│  │               │  │   Resume)    │  │                    │  │
│  └───────────────┘  └──────────────┘  └────────────────────┘  │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Row Level Security (RLS) - Multi-tenant Isolation      │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Database Schema Organization

The database is organized into logical domains:

1. **Core Workflow System** - Workflows, nodes, connections, executions
2. **Trigger & Scheduler** - Workflow deployment, trigger index, execution history
3. **Human-in-the-Loop (HIL)** - Human interactions, responses, workflow pauses
4. **Memory System** - 8 memory types (conversation, entity, episodic, knowledge, etc.)
5. **Integration System** - OAuth tokens, external API credentials, API call logs
6. **AI & RAG System** - AI models, embeddings, node specifications, MCP tools
7. **Logging & Audit** - Execution logs, validation logs, deployment history

## 3. Data Architecture

### 3.1 Core Entity Relationships

```
auth.users (Supabase Auth - Canonical User Source)
    │
    ├──▶ workflows (1:N)
    │       │
    │       ├──▶ nodes (1:N)
    │       │       └──▶ node_connections (N:M via workflow_id)
    │       │
    │       ├──▶ workflow_executions (1:N)
    │       │       ├──▶ node_executions (1:N)
    │       │       ├──▶ workflow_execution_logs (1:N)
    │       │       └──▶ workflow_execution_pauses (1:N) [HIL]
    │       │
    │       ├──▶ trigger_index (1:N)
    │       ├──▶ workflow_deployment_history (1:N)
    │       └──▶ workflow_triggers (1:N)
    │
    ├──▶ sessions (1:N)
    │
    ├──▶ user_external_credentials (1:N)
    │       └──▶ oauth_tokens (1:N)
    │
    ├──▶ human_interactions (1:N) [HIL]
    │       └──▶ hil_responses (1:N)
    │
    └──▶ Memory System (all 1:N)
            ├──▶ conversation_buffers
            ├──▶ conversation_summaries
            ├──▶ entities
            ├──▶ episodic_memory
            ├──▶ knowledge_facts
            ├──▶ graph_nodes
            ├──▶ document_store
            └──▶ vector_embeddings
```

### 3.2 Data Flow Patterns

#### Workflow Execution Flow
```
1. Trigger Detection → trigger_index lookup
2. Create workflow_executions record (status: NEW)
3. Start execution → Update status to RUNNING
4. For each node:
   - Create node_executions record
   - Execute node logic
   - Update node_executions with results
   - Create workflow_execution_logs entries
5. Handle HIL pauses if needed:
   - Create human_interactions record
   - Create workflow_execution_pauses
   - Set workflow status to PAUSED
   - Wait for hil_responses
   - Resume and continue execution
6. Complete execution → Update status to SUCCESS/ERROR
```

#### HIL (Human-in-the-Loop) Data Flow
```
1. HIL Node Execution → Create human_interactions (status: pending)
2. Create workflow_execution_pauses (status: active)
3. Send notification via channel (Slack/Email/Webhook)
4. External webhook receives response → Create hil_responses
5. AI classification (Gemini) → Update relevance_score
6. Match to interaction → Update human_interactions (status: responded)
7. Resume workflow → Update workflow_execution_pauses (status: resumed)
8. Continue execution from paused node
```

## 4. Implementation Details

### 4.1 Core Workflow Tables

#### workflows
**Purpose**: Primary workflow definition and metadata storage

```sql
CREATE TABLE workflows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    session_id UUID REFERENCES sessions(id),

    -- Basic Information
    name VARCHAR(255) NOT NULL,
    description TEXT,
    version VARCHAR(50) DEFAULT '1.0.0',
    active BOOLEAN DEFAULT true,

    -- Workflow Definition (JSONB)
    workflow_data JSONB NOT NULL,
    settings JSONB,
    static_data JSONB,
    pin_data JSONB,

    -- Classification
    tags TEXT[],
    is_template BOOLEAN DEFAULT false,
    template_category VARCHAR(100),

    -- Deployment Status
    deployment_status VARCHAR(50) DEFAULT 'IDLE',
    deployed_at TIMESTAMP WITH TIME ZONE,
    deployed_by UUID REFERENCES auth.users(id),
    undeployed_at TIMESTAMP WITH TIME ZONE,
    deployment_version INTEGER DEFAULT 1,
    deployment_config JSONB DEFAULT '{}',

    -- Latest Execution Tracking
    latest_execution_status VARCHAR(50) DEFAULT 'IDLE',
    latest_execution_id VARCHAR(255),
    latest_execution_time TIMESTAMP WITH TIME ZONE,

    -- Visual
    icon_url VARCHAR(500),

    -- Timestamps (bigint for epoch milliseconds)
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL,

    CONSTRAINT workflows_name_not_empty CHECK (length(name) > 0),
    CONSTRAINT workflows_valid_workflow_data CHECK (workflow_data IS NOT NULL)
);
```

**Key Indexes**:
- `idx_workflows_user_id` - User's workflows lookup
- `idx_workflows_active` - Active workflows filtering
- `idx_workflows_deployment_status` - Deployment state queries
- `idx_workflows_tags` (GIN) - Tag-based search

**Design Decisions**:
- **JSONB for workflow_data**: Flexible schema for node/connection storage
- **Denormalized execution status**: Fast dashboard queries without joins
- **Bigint timestamps**: Consistent with epoch milliseconds from frontend
- **Deployment fields**: Track deployment lifecycle for scheduler integration

#### nodes
**Purpose**: Individual node configurations within workflows

```sql
CREATE TABLE nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    node_id VARCHAR(255) NOT NULL,
    workflow_id UUID REFERENCES workflows(id) ON DELETE CASCADE,

    -- Node Classification
    node_type VARCHAR(50) NOT NULL,
    node_subtype VARCHAR(100) NOT NULL,
    type_version INTEGER DEFAULT 1,

    -- Node Identity
    name VARCHAR(255) NOT NULL,
    description TEXT,
    disabled BOOLEAN DEFAULT false,

    -- Canvas Position
    position_x FLOAT DEFAULT 0,
    position_y FLOAT DEFAULT 0,

    -- Configuration (JSONB)
    parameters JSONB DEFAULT '{}',
    credentials JSONB DEFAULT '{}',

    -- Attached Nodes (AI_AGENT only)
    attached_nodes JSONB DEFAULT '[]',

    -- Error Handling
    error_handling VARCHAR(50) DEFAULT 'STOP_WORKFLOW_ON_ERROR',
    max_retries INTEGER DEFAULT 3,
    retry_wait_time INTEGER DEFAULT 5,

    -- Metadata
    notes TEXT,
    webhooks TEXT[],

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_node_type CHECK (
        node_type IN ('TRIGGER', 'AI_AGENT', 'EXTERNAL_ACTION', 'ACTION',
                      'FLOW', 'HUMAN_IN_THE_LOOP', 'TOOL', 'MEMORY')
    ),
    CONSTRAINT valid_error_handling CHECK (
        error_handling IN ('STOP_WORKFLOW_ON_ERROR',
                           'CONTINUE_REGULAR_OUTPUT_ON_ERROR',
                           'CONTINUE_ERROR_OUTPUT_ON_ERROR')
    ),
    UNIQUE(workflow_id, node_id)
);
```

**Key Indexes**:
- `idx_nodes_workflow_id` - Fetch all nodes for a workflow
- `idx_nodes_type` - Filter by node type
- `idx_nodes_type_subtype_active` (composite) - Active nodes by type

**Design Decisions**:
- **attached_nodes JSONB**: AI_AGENT nodes can attach TOOL/MEMORY nodes
- **Flexible error handling**: Per-node error strategies
- **UNIQUE(workflow_id, node_id)**: Enforce node uniqueness within workflow

#### node_connections
**Purpose**: Define data flow between nodes

```sql
CREATE TABLE node_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id UUID REFERENCES workflows(id) ON DELETE CASCADE,
    source_node_id VARCHAR(255) NOT NULL,
    target_node_id VARCHAR(255) NOT NULL,

    -- Connection Configuration
    connection_type VARCHAR(50) DEFAULT 'MAIN',
    connection_index INTEGER DEFAULT 0,
    label VARCHAR(255),
    conditions JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_connection_type CHECK (
        connection_type IN ('MAIN', 'ERROR', 'SUCCESS', 'CONDITIONAL',
                           'AI_AGENT', 'AI_CHAIN', 'AI_DOCUMENT', 'AI_EMBEDDING',
                           'AI_LANGUAGE_MODEL', 'AI_MEMORY', 'AI_OUTPUT_PARSER',
                           'AI_RETRIEVER', 'AI_RERANKER', 'AI_TEXT_SPLITTER',
                           'AI_TOOL', 'AI_VECTOR_STORE',
                           'MEMORY_ATTACHMENT', 'CONTEXT_PROVIDER')
    ),
    CONSTRAINT source_target_different CHECK (source_node_id != target_node_id),
    FOREIGN KEY (workflow_id, source_node_id)
        REFERENCES nodes(workflow_id, node_id) ON DELETE CASCADE,
    FOREIGN KEY (workflow_id, target_node_id)
        REFERENCES nodes(workflow_id, node_id) ON DELETE CASCADE
);
```

**Design Decisions**:
- **Connection types**: Support AI agent connections and memory attachments
- **Conditional connections**: JSONB for complex routing logic
- **Cascading deletes**: Maintain referential integrity with nodes

### 4.2 Execution Tracking Tables

#### workflow_executions
**Purpose**: Track individual workflow execution instances

```sql
CREATE TABLE workflow_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_id VARCHAR(255) UNIQUE NOT NULL,
    workflow_id UUID REFERENCES workflows(id) ON DELETE CASCADE,

    -- Execution State
    status VARCHAR(50) NOT NULL DEFAULT 'NEW',
    mode VARCHAR(50) NOT NULL DEFAULT 'MANUAL',

    -- Trigger Information
    triggered_by VARCHAR(255),
    parent_execution_id VARCHAR(255),

    -- Timing (epoch milliseconds)
    start_time BIGINT,
    end_time BIGINT,

    -- Execution Data (JSONB)
    run_data JSONB,
    metadata JSONB DEFAULT '{}',

    -- Error Information
    error_message TEXT,
    error_details JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_execution_status CHECK (
        status IN ('NEW', 'RUNNING', 'SUCCESS', 'ERROR', 'CANCELED',
                   'PAUSED', 'WAITING_FOR_HUMAN', 'TIMEOUT')
    ),
    CONSTRAINT valid_execution_mode CHECK (
        mode IN ('MANUAL', 'TRIGGER', 'WEBHOOK', 'RETRY')
    )
);
```

**Key Indexes**:
- `idx_executions_workflow_id` - All executions for a workflow
- `idx_executions_status` - Filter by status
- `idx_executions_status_created` (composite) - Recent failed executions
- `idx_executions_execution_id` - Fast execution lookup

**Design Decisions**:
- **PAUSED & WAITING_FOR_HUMAN**: Support HIL workflow pauses
- **parent_execution_id**: Track workflow chains and sub-workflows
- **run_data JSONB**: Flexible storage for node execution results

#### node_executions
**Purpose**: Detailed per-node execution tracking

```sql
CREATE TABLE node_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_id VARCHAR(255) REFERENCES workflow_executions(execution_id) ON DELETE CASCADE,
    node_id VARCHAR(255) NOT NULL,
    node_type VARCHAR(100) NOT NULL,

    -- Execution Status
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    start_time BIGINT,
    end_time BIGINT,

    -- I/O Data (JSONB)
    input_data JSONB,
    output_data JSONB,
    error_data JSONB,

    -- Retry Information
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_node_status CHECK (
        status IN ('PENDING', 'RUNNING', 'SUCCESS', 'ERROR',
                   'SKIPPED', 'CANCELED', 'WAITING_INPUT', 'RETRYING')
    )
);
```

**Key Indexes**:
- `idx_node_executions_execution_id` - All nodes for an execution
- `idx_node_executions_node_id` - Node execution history
- `idx_node_executions_status` - Filter by status

#### workflow_execution_logs
**Purpose**: Unified logging for technical debugging and business events

```sql
CREATE TABLE workflow_execution_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id VARCHAR(255) NOT NULL,

    -- Log Classification
    log_category VARCHAR(20) NOT NULL DEFAULT 'TECHNICAL',
    event_type VARCHAR(50) NOT NULL,
    level VARCHAR(10) NOT NULL DEFAULT 'INFO',

    -- Content
    message TEXT NOT NULL,
    data JSONB DEFAULT '{}',

    -- Node Context
    node_id VARCHAR(255),
    node_name VARCHAR(255),
    node_type VARCHAR(100),

    -- Progress Tracking
    step_number INTEGER,
    total_steps INTEGER,
    progress_percentage NUMERIC(5,2),
    duration_seconds INTEGER,

    -- User-Friendly Display
    user_friendly_message TEXT,
    display_priority INTEGER DEFAULT 5,
    is_milestone BOOLEAN DEFAULT false,

    -- Technical Details
    technical_details JSONB DEFAULT '{}',
    stack_trace TEXT,
    performance_metrics JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_log_category CHECK (log_category IN ('TECHNICAL', 'BUSINESS')),
    CONSTRAINT valid_event_type CHECK (
        event_type IN ('workflow_started', 'workflow_completed', 'workflow_progress',
                      'step_started', 'step_input', 'step_output',
                      'step_completed', 'step_error', 'separator')
    ),
    CONSTRAINT valid_log_level CHECK (level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR'))
);
```

**Key Indexes**:
- `idx_workflow_execution_logs_execution_id` - All logs for execution
- `idx_workflow_execution_logs_category` - Filter by category
- `idx_workflow_execution_logs_level` - Filter by severity
- `idx_workflow_execution_logs_priority` - High-priority logs

**Design Decisions**:
- **Dual-purpose logging**: Technical debugging + user-friendly business logs
- **display_priority**: Control log visibility in UI (1-10 scale)
- **TTL support**: Logs can be automatically cleaned up (separate function)

### 4.3 Trigger & Scheduler System

#### trigger_index
**Purpose**: Fast reverse lookup for all trigger types (scheduler optimization)

```sql
CREATE TABLE trigger_index (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,

    -- Trigger Classification
    trigger_type VARCHAR(50) NOT NULL,
    trigger_subtype VARCHAR(100) NOT NULL,
    trigger_config JSON NOT NULL DEFAULT '{}',

    -- Fast Matching
    index_key VARCHAR(255) NOT NULL,
    -- CRON: cron_expression
    -- WEBHOOK: webhook_path
    -- SLACK: workspace_id
    -- EMAIL: email_address
    -- GITHUB: repository_name

    -- Deployment Status
    deployment_status VARCHAR(50) DEFAULT 'active',
    is_active BOOLEAN DEFAULT true,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_trigger_type CHECK (trigger_type IN ('TRIGGER')),
    CONSTRAINT valid_trigger_subtype CHECK (
        trigger_subtype IN ('CRON', 'MANUAL', 'WEBHOOK', 'EMAIL', 'GITHUB', 'SLACK')
    ),
    CONSTRAINT valid_deployment_status CHECK (
        deployment_status IN ('active', 'inactive', 'pending', 'failed')
    ),
    UNIQUE(workflow_id, index_key)
);
```

**Key Indexes**:
- `idx_trigger_index_type` - Filter by trigger type
- `idx_trigger_index_key` (composite: type + key) - Fast event matching
- `idx_trigger_index_lookup` (composite: type + key + status) - Active trigger queries

**Design Decisions**:
- **index_key unification**: Single field for fast matching across all trigger types
- **Denormalized trigger_config**: Avoid joins for trigger validation
- **Deployment tracking**: Support staged rollouts and testing

#### workflow_deployment_history
**Purpose**: Audit trail for workflow deployment actions

```sql
CREATE TABLE workflow_deployment_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,

    -- Deployment Action
    deployment_action VARCHAR(50) NOT NULL,
    from_status VARCHAR(50) NOT NULL,
    to_status VARCHAR(50) NOT NULL,

    -- Version Tracking
    deployment_version INTEGER NOT NULL,
    deployment_config JSON NOT NULL DEFAULT '{}',

    -- Audit Information
    triggered_by UUID REFERENCES auth.users(id),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Error Tracking
    error_message TEXT,
    deployment_logs JSON DEFAULT '{}',

    CONSTRAINT valid_deployment_action CHECK (
        deployment_action IN ('DEPLOY', 'UNDEPLOY', 'UPDATE', 'ROLLBACK',
                             'DEPLOY_STARTED', 'DEPLOY_COMPLETED', 'DEPLOY_FAILED',
                             'UNDEPLOY_STARTED', 'UNDEPLOY_COMPLETED')
    )
);
```

**Key Indexes**:
- `idx_deployment_history_workflow_id` - Deployment timeline
- `idx_deployment_history_action` - Filter by action type
- `idx_deployment_history_started_at` - Recent deployments

### 4.4 Human-in-the-Loop (HIL) System

#### human_interactions
**Purpose**: Track HIL interaction requests and responses

```sql
CREATE TABLE human_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Workflow Context
    workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    execution_id UUID,
    node_id VARCHAR(255) NOT NULL,

    -- Interaction Details
    interaction_type VARCHAR(50) NOT NULL,
    channel_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    priority VARCHAR(20) DEFAULT 'normal',

    -- Request & Response (JSONB)
    request_data JSONB NOT NULL,
    response_data JSONB,

    -- Timing
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    responded_at TIMESTAMP WITH TIME ZONE,
    timeout_at TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Metadata
    correlation_id VARCHAR(255),
    tags TEXT[],

    CONSTRAINT valid_interaction_type CHECK (
        interaction_type IN ('approval', 'input', 'selection', 'review')
    ),
    CONSTRAINT valid_channel_type CHECK (
        channel_type IN ('slack', 'email', 'webhook', 'in_app')
    ),
    CONSTRAINT valid_status CHECK (
        status IN ('pending', 'responded', 'timeout', 'error', 'cancelled')
    ),
    CONSTRAINT valid_priority CHECK (
        priority IN ('low', 'normal', 'high', 'critical')
    )
);
```

**Key Indexes**:
- `idx_human_interactions_workflow` - All interactions for workflow
- `idx_human_interactions_status` - Filter by status
- `idx_human_interactions_pending_timeout` (partial) - Timeout monitoring
- `idx_human_interactions_correlation` (partial) - Response matching

#### hil_responses
**Purpose**: Capture incoming responses from communication channels

```sql
CREATE TABLE hil_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Incoming Response
    workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    source_channel VARCHAR(50) NOT NULL,
    raw_payload JSONB NOT NULL,
    headers JSONB,

    -- Processing Status
    status VARCHAR(20) DEFAULT 'unprocessed',
    processed_at TIMESTAMP WITH TIME ZONE,

    -- AI Classification Results
    matched_interaction_id UUID REFERENCES human_interactions(id),
    ai_relevance_score DECIMAL(3,2),
    ai_reasoning TEXT,

    -- Timing
    received_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT valid_source_channel CHECK (
        source_channel IN ('slack', 'email', 'webhook')
    ),
    CONSTRAINT valid_processing_status CHECK (
        status IN ('unprocessed', 'matched', 'filtered_out', 'error')
    )
);
```

**Key Indexes**:
- `idx_hil_responses_workflow` - All responses for workflow
- `idx_hil_responses_status` - Processing queue
- `idx_hil_responses_unprocessed` (partial) - Pending processing
- `idx_hil_responses_matched` (partial) - Successful matches

**Design Decisions**:
- **AI classification**: Gemini-powered 8-factor relevance analysis
- **Raw payload storage**: Full debugging capability for webhook responses
- **Partial indexes**: Optimize queries for unprocessed/matched states

#### workflow_execution_pauses
**Purpose**: Track workflow pauses for HIL interactions

```sql
CREATE TABLE workflow_execution_pauses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID NOT NULL REFERENCES workflow_executions(id) ON DELETE CASCADE,

    -- Pause Details
    paused_at TIMESTAMP WITH TIME ZONE NOT NULL,
    paused_node_id VARCHAR(255) NOT NULL,
    pause_reason VARCHAR(100) NOT NULL,

    -- Resume Conditions (JSONB)
    resume_conditions JSONB NOT NULL,
    resumed_at TIMESTAMP WITH TIME ZONE,
    resume_trigger VARCHAR(100),

    -- Status
    status VARCHAR(20) DEFAULT 'active',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT valid_pause_reason CHECK (
        pause_reason IN ('human_interaction', 'timeout', 'error')
    ),
    CONSTRAINT valid_pause_status CHECK (
        status IN ('active', 'resumed', 'timeout')
    )
);
```

**Key Indexes**:
- `idx_workflow_execution_pauses_execution` - All pauses for execution
- `idx_workflow_execution_pauses_active` (partial) - Active pauses
- `idx_workflow_execution_pauses_node` - Pauses by node

### 4.5 Memory System Tables

The system implements 8 specialized memory types for AI agent context management:

#### conversation_buffers
**Purpose**: Short-term conversation history storage

```sql
CREATE TABLE conversation_buffers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255),

    -- Message Details
    message_index INTEGER NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,

    -- Metadata
    metadata JSONB DEFAULT '{}',
    tokens_count INTEGER,

    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (session_id, message_index)
);
```

**Key Indexes**:
- `idx_conversation_buffers_session_id` - Session history
- `idx_conversation_buffers_timestamp` - Chronological ordering
- `idx_conversation_buffers_user_id` - User's conversations

#### conversation_summaries
**Purpose**: Progressive summarization of long conversations

```sql
CREATE TABLE conversation_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255),

    -- Summary Content
    summary TEXT NOT NULL,
    key_points JSONB DEFAULT '[]',
    entities JSONB DEFAULT '[]',
    topics JSONB DEFAULT '[]',

    -- Summary Configuration
    summary_type VARCHAR(50) DEFAULT 'progressive',
    message_count INTEGER NOT NULL DEFAULT 0,
    token_count INTEGER DEFAULT 0,
    model_used VARCHAR(100),
    confidence_score FLOAT DEFAULT 0.0,

    -- Hierarchical Linking
    previous_summary_id UUID REFERENCES conversation_summaries(id),

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_summary_type CHECK (
        summary_type IN ('progressive', 'hierarchical', 'key_points')
    ),
    UNIQUE (session_id, created_at)
);
```

#### entities & entity_relationships
**Purpose**: Named entity recognition and relationship tracking

```sql
CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(500) NOT NULL,
    type VARCHAR(100) NOT NULL,
    aliases TEXT[] DEFAULT '{}',
    attributes JSONB DEFAULT '{}',
    description TEXT,

    -- Importance Tracking
    importance_score FLOAT DEFAULT 0.5 CHECK (importance_score BETWEEN 0.0 AND 1.0),
    first_seen TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    mention_count INTEGER DEFAULT 1,

    user_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (name, type, user_id)
);

CREATE TABLE entity_relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    target_entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    relationship_type VARCHAR(100) NOT NULL,
    relationship_attributes JSONB DEFAULT '{}',
    confidence FLOAT DEFAULT 1.0 CHECK (confidence BETWEEN 0.0 AND 1.0),
    source VARCHAR(255),

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (source_entity_id, target_entity_id, relationship_type)
);
```

**Key Indexes**:
- `idx_entities_name` - Entity lookup
- `idx_entities_type` - Filter by entity type
- `idx_entities_importance` - Most important entities
- `idx_entity_relationships_source/target` - Relationship navigation

#### episodic_memory
**Purpose**: Event-based memory storage (Actor-Action-Object-Context-Outcome)

```sql
CREATE TABLE episodic_memory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    actor VARCHAR(255) NOT NULL,
    action VARCHAR(255) NOT NULL,
    object TEXT,
    context JSONB DEFAULT '{}',
    outcome JSONB DEFAULT '{}',

    -- Event Metadata
    importance DECIMAL(3,2) NOT NULL DEFAULT 0.5 CHECK (importance BETWEEN 0.0 AND 1.0),
    timestamp TIMESTAMPTZ NOT NULL,
    session_id VARCHAR(255),
    user_id VARCHAR(255),
    event_description TEXT,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

**Key Indexes**:
- `idx_episodic_memory_timestamp` - Chronological events
- `idx_episodic_memory_actor` - Events by actor
- `idx_episodic_memory_importance` - Important events

#### knowledge_facts & knowledge_rules
**Purpose**: Subject-Predicate-Object knowledge base

```sql
CREATE TABLE knowledge_facts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subject VARCHAR(500) NOT NULL,
    predicate VARCHAR(255) NOT NULL,
    object JSONB NOT NULL,
    confidence FLOAT DEFAULT 1.0 CHECK (confidence BETWEEN 0.0 AND 1.0),
    source VARCHAR(255),
    domain VARCHAR(100),
    fact_type VARCHAR(100),
    metadata JSONB DEFAULT '{}',
    user_id VARCHAR(255),

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    validated_at TIMESTAMPTZ,

    UNIQUE (subject, predicate, object, user_id)
);

CREATE TABLE knowledge_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    conditions JSONB NOT NULL,
    actions JSONB NOT NULL,
    priority INTEGER DEFAULT 0,
    active BOOLEAN DEFAULT true,
    user_id VARCHAR(255),

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

#### graph_nodes & graph_relationships
**Purpose**: Graph-based memory with weighted relationships

```sql
CREATE TABLE graph_nodes (
    id VARCHAR(255) PRIMARY KEY,
    label VARCHAR(500) NOT NULL,
    type VARCHAR(100) NOT NULL,
    properties JSONB DEFAULT '{}',
    user_id VARCHAR(255),

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (label, type, user_id)
);

CREATE TABLE graph_relationships (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255),
    source_node_id VARCHAR(255) REFERENCES graph_nodes(id) ON DELETE CASCADE,
    target_node_id VARCHAR(255) REFERENCES graph_nodes(id) ON DELETE CASCADE,
    relationship_type VARCHAR(100) NOT NULL,
    properties JSONB DEFAULT '{}',
    weight FLOAT DEFAULT 1.0 CHECK (weight BETWEEN 0.0 AND 1.0),

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (source_node_id, target_node_id, relationship_type)
);
```

#### document_store
**Purpose**: Full-text searchable document storage

```sql
CREATE TABLE document_store (
    id VARCHAR(255) PRIMARY KEY,
    collection_name VARCHAR(255) NOT NULL,
    title VARCHAR(500),
    description TEXT,
    content TEXT NOT NULL,
    search_content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    category VARCHAR(100) DEFAULT 'general',
    tags TEXT[] DEFAULT '{}',
    user_id VARCHAR(255),

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

**Key Indexes**:
- `idx_document_store_collection` - Collection queries
- `idx_document_store_tags` (GIN) - Tag-based search
- `idx_document_store_search` (GIN tsvector) - Full-text search

#### vector_embeddings
**Purpose**: Vector similarity search (RAG system)

```sql
CREATE TABLE vector_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    collection_name VARCHAR(255) NOT NULL,
    text_content TEXT NOT NULL,
    embedding vector(1536) NOT NULL, -- OpenAI ada-002 size
    metadata JSONB DEFAULT '{}',
    user_id VARCHAR(255),

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

**Key Indexes**:
- `idx_vector_embeddings_cosine` (ivfflat) - Cosine similarity search
- `idx_vector_embeddings_euclidean` (ivfflat) - Euclidean distance search
- `idx_vector_embeddings_collection` - Collection filtering

**Vector Search Function**:
```sql
CREATE OR REPLACE FUNCTION search_similar_vectors(
    query_embedding vector(1536),
    collection_name_param TEXT,
    similarity_threshold FLOAT DEFAULT 0.7,
    max_results INTEGER DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    text_content TEXT,
    metadata JSONB,
    similarity FLOAT
)
```

### 4.6 Integration & OAuth System

#### oauth_tokens
**Purpose**: OAuth token storage with refresh capability

```sql
CREATE TABLE oauth_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    integration_id VARCHAR(255) REFERENCES integrations(integration_id) ON DELETE CASCADE,
    provider VARCHAR(100) NOT NULL,

    -- Token Data
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_type VARCHAR(50) DEFAULT 'Bearer',
    expires_at TIMESTAMP WITH TIME ZONE,

    -- Metadata
    credential_data JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, integration_id)
);
```

**Key Indexes**:
- `idx_oauth_tokens_user_id` - User's OAuth tokens
- `idx_oauth_tokens_integration_id` - Tokens by integration

#### user_external_credentials
**Purpose**: Encrypted external API credentials

```sql
CREATE TABLE user_external_credentials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    credential_type VARCHAR(20) DEFAULT 'oauth2',

    -- Encrypted Credentials
    encrypted_access_token TEXT,
    encrypted_refresh_token TEXT,
    encrypted_additional_data JSONB DEFAULT '{}',

    -- Token Metadata
    token_expires_at TIMESTAMP WITH TIME ZONE,
    scope TEXT[] DEFAULT '{}',
    token_type VARCHAR(20) DEFAULT 'Bearer',

    -- Validation
    is_valid BOOLEAN DEFAULT true,
    last_validated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    validation_error TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_provider CHECK (
        provider IN ('google_calendar', 'github', 'slack', 'custom_http')
    ),
    CONSTRAINT valid_credential_type CHECK (
        credential_type IN ('oauth2', 'api_key', 'basic_auth', 'bearer_token')
    ),
    UNIQUE(user_id, provider)
);
```

**Key Indexes**:
- `idx_user_credentials_user_provider` - Credential lookup
- `idx_user_credentials_expires_at` - Token refresh monitoring
- `idx_user_credentials_valid` - Valid credentials filtering

**Design Decisions**:
- **Fernet encryption**: Credentials encrypted at application layer
- **Refresh token support**: Automatic token refresh capability
- **Validation tracking**: Monitor credential health

#### external_api_call_logs
**Purpose**: API call monitoring and debugging

```sql
CREATE TABLE external_api_call_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    workflow_execution_id UUID REFERENCES workflow_executions(id) ON DELETE SET NULL,
    node_id UUID REFERENCES nodes(id) ON DELETE SET NULL,

    -- API Call Information
    provider VARCHAR(50) NOT NULL,
    operation VARCHAR(100) NOT NULL,
    api_endpoint TEXT,
    http_method VARCHAR(10) DEFAULT 'POST',

    -- Request & Response (sanitized)
    request_data JSONB,
    response_data JSONB,
    request_headers JSONB DEFAULT '{}',
    response_headers JSONB DEFAULT '{}',

    -- Execution Results
    success BOOLEAN NOT NULL,
    status_code INTEGER,
    error_type VARCHAR(50),
    error_message TEXT,

    -- Performance Metrics
    response_time_ms INTEGER,
    retry_count INTEGER DEFAULT 0,

    -- Rate Limiting
    rate_limit_remaining INTEGER,
    rate_limit_reset_at TIMESTAMP WITH TIME ZONE,

    called_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

**Key Indexes**:
- `idx_api_logs_user_provider` - User's API usage
- `idx_api_logs_execution` - Execution debugging
- `idx_api_logs_provider_operation` - Operation analytics
- `idx_api_logs_time` - Chronological logs

### 4.7 AI & RAG System Tables

#### ai_models
**Purpose**: Available AI model registry with pricing

```sql
CREATE TABLE ai_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    model_id VARCHAR(100) NOT NULL,
    version VARCHAR(50),

    -- Pricing (per token)
    cost_per_input_token DECIMAL(10, 8),
    cost_per_output_token DECIMAL(10, 8),
    cost_per_cached_token DECIMAL(10, 8),

    -- Capabilities
    max_context_tokens INTEGER,
    supports_vision BOOLEAN DEFAULT false,
    supports_function_calling BOOLEAN DEFAULT false,
    supports_streaming BOOLEAN DEFAULT true,
    model_capabilities JSONB DEFAULT '{}',

    -- Configuration
    config JSONB NOT NULL DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    is_default BOOLEAN DEFAULT false,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(name, version)
);
```

**Pre-populated Models**:
- GPT-5, GPT-5 Mini, GPT-5 Nano (OpenAI)
- Claude Sonnet 4, Claude Haiku 3.5 (Anthropic)
- Gemini 2.5 Pro, Flash, Flash Lite (Google)

#### node_specifications
**Purpose**: Dynamic node type specifications

```sql
CREATE TABLE node_specifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    node_type VARCHAR(50) NOT NULL,
    node_subtype VARCHAR(100) NOT NULL,
    specification_version VARCHAR(20) DEFAULT '1.0.0',

    -- Specification (JSONB)
    specification_data JSONB NOT NULL,

    -- Status
    is_active BOOLEAN DEFAULT true,
    is_system_spec BOOLEAN DEFAULT true,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(node_type, node_subtype, specification_version),
    CONSTRAINT valid_spec_node_type CHECK (
        node_type IN ('TRIGGER', 'AI_AGENT', 'EXTERNAL_ACTION', 'ACTION',
                      'FLOW', 'HUMAN_IN_THE_LOOP', 'TOOL', 'MEMORY')
    )
);
```

**Key Indexes**:
- `idx_node_specifications_type_subtype` - Spec lookup
- `idx_node_specifications_active` (partial) - Active specs

#### mcp_tools
**Purpose**: Model Context Protocol (MCP) tools registry

```sql
CREATE TABLE mcp_tools (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tool_name VARCHAR(255) NOT NULL,
    tool_type VARCHAR(100) NOT NULL,
    provider VARCHAR(100) NOT NULL,
    version VARCHAR(50) DEFAULT '1.0.0',
    description TEXT,

    -- Tool Schema (JSONB)
    tool_schema JSONB NOT NULL,
    configuration_schema JSONB DEFAULT '{}',

    -- Status
    is_active BOOLEAN DEFAULT true,
    is_system_tool BOOLEAN DEFAULT true,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(tool_name, provider, version)
);
```

**Key Indexes**:
- `idx_mcp_tools_name` - Tool lookup
- `idx_mcp_tools_type` - Filter by type
- `idx_mcp_tools_active` (partial) - Active tools

## 5. System Interactions

### 5.1 Internal Interactions

#### Service Database Access Patterns

**API Gateway**:
- Read: workflows, workflow_executions, sessions, oauth_tokens
- Write: workflow_executions, sessions
- Heavy RLS queries: User's workflows and executions

**Workflow Agent**:
- Read: workflows, node_specifications, ai_models, vector_embeddings (RAG)
- Write: ai_generation_history
- RAG queries: Vector similarity search for node examples

**Workflow Engine**:
- Read: workflows, nodes, node_connections, trigger_index
- Write: workflow_executions, node_executions, workflow_execution_logs
- Heavy writes: Execution tracking and logging

**Workflow Scheduler**:
- Read: trigger_index, workflows
- Write: workflow_deployment_history, trigger_index
- Time-series: Deployment actions and trigger updates

### 5.2 External Integrations

#### Supabase Auth Integration
- **Canonical User Source**: `auth.users` (managed by Supabase)
- **RLS Policies**: `auth.uid()` for user identification
- **No public.users table**: All user references point to `auth.users(id)`

#### Vector Search Integration
- **pgvector Extension**: Cosine similarity search
- **Embedding Model**: OpenAI text-embedding-ada-002 (1536 dimensions)
- **Use Cases**: RAG for workflow agent, semantic node search

#### External OAuth Providers
- Google Calendar, GitHub, Slack
- Token storage in `oauth_tokens` and `user_external_credentials`
- API call tracking in `external_api_call_logs`

## 6. Non-Functional Requirements

### 6.1 Performance

#### Query Optimization Strategies

**Index Strategy**:
- **Primary indexes**: All foreign keys and frequently queried columns
- **Composite indexes**: Common query patterns (e.g., `idx_executions_status_created`)
- **Partial indexes**: Filter conditions in WHERE clauses (e.g., `WHERE is_active = true`)
- **GIN indexes**: JSONB, array, and full-text search columns

**Denormalization**:
- `workflows.latest_execution_status` - Avoid joins for dashboard
- `trigger_index.trigger_config` - Fast trigger validation
- `human_interactions.request_data` - Complete HIL context

**Connection Pooling**:
- Supabase connection pooler (pgBouncer)
- Service-level connection pools (SQLAlchemy)

**Caching Strategy**:
- Redis for session state and rate limiting
- Application-level caching for node specifications and AI models

#### Performance Targets
- **Workflow list query**: \< 200ms (with RLS)
- **Execution status update**: \< 50ms
- **Vector similarity search**: \< 500ms (10 results)
- **Trigger index lookup**: \< 100ms

### 6.2 Scalability

#### Horizontal Scaling
- **Read Replicas**: Supabase supports read replicas for read-heavy workloads
- **Partitioning Strategy**:
  - `workflow_execution_logs` - Partition by created_at (monthly)
  - `external_api_call_logs` - Partition by called_at (monthly)

#### Data Growth Management
- **Log Retention**: 30-day default retention for execution logs
- **Cleanup Functions**:
  ```sql
  CREATE OR REPLACE FUNCTION cleanup_old_conversation_buffers(retention_days INTEGER)
  CREATE OR REPLACE FUNCTION cleanup_old_execution_logs(retention_days INTEGER)
  ```

#### Connection Management
- **Max Connections**: Configured per service in Supabase dashboard
- **Connection Limits**: pgBouncer for connection pooling

### 6.3 Security

#### Row Level Security (RLS)

**All user-facing tables have RLS enabled**:
```sql
ALTER TABLE workflows ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own workflows" ON workflows
    FOR ALL USING (auth.uid() = user_id);
```

**Key RLS Patterns**:
1. **Direct ownership**: `auth.uid() = user_id`
2. **Transitive ownership**: Through JOIN to owned resource
3. **Service role bypass**: Service accounts bypass RLS

#### Credential Encryption
- **Fernet encryption**: Applied at application layer
- **Environment variable management**: AWS SSM Parameters
- **Token refresh**: Automatic refresh before expiration

#### Audit Logging
- **Deployment history**: All workflow deployments tracked
- **API call logs**: All external API calls logged
- **Error tracking**: Detailed error information for debugging

### 6.4 Reliability

#### Data Integrity

**Foreign Key Constraints**:
- All relationships enforced with FK constraints
- Cascade deletes where appropriate
- `ON DELETE SET NULL` for soft references

**Check Constraints**:
- Enum validation for status fields
- Range validation for scores and weights
- Non-empty string validation

**Unique Constraints**:
- Prevent duplicate workflows, nodes, connections
- Enforce unique OAuth tokens per user/provider

#### Backup & Recovery
- **Supabase Point-in-Time Recovery (PITR)**: Up to 30 days
- **Daily Backups**: Automatic Supabase backups
- **Migration History**: All schema changes tracked in migrations

#### Error Handling
- **Structured errors**: JSONB error_details with error codes
- **Retry tracking**: `retry_count` in node_executions
- **Timeout handling**: HIL timeout actions and monitoring

### 6.5 Testing & Observability

#### Testing Strategy

**Unit Testing**:
- SQLAlchemy model validation
- Database constraint enforcement
- JSONB schema validation

**Integration Testing**:
- Cross-service database operations
- RLS policy verification
- Transaction rollback testing

**Performance Testing**:
- Query performance benchmarking
- Index effectiveness validation
- Connection pool stress testing

#### Observability

**Key Metrics**:
- Database connection pool utilization
- Query execution time (p50, p95, p99)
- Table sizes and growth rates
- Index hit ratios
- Replication lag (if using replicas)

**Monitoring**:
- **Supabase Dashboard**: Connection stats, slow query log
- **CloudWatch**: ECS task metrics, database metrics
- **Application Logs**: Query timing, connection errors

**Alerting**:
- High connection pool utilization (\> 80%)
- Slow queries (\> 1s)
- Failed migrations
- Replication lag (\> 10s)

#### Logging Strategy
- **Execution logs**: Dual-purpose (technical + business)
- **API call logs**: Complete request/response for debugging
- **Deployment logs**: Full deployment action history
- **Error logs**: Stack traces and context

## 7. Technical Debt and Future Considerations

### 7.1 Known Limitations

**Current Limitations**:
1. **JSONB queries**: Complex JSONB queries can be slow without proper indexing
2. **Log table growth**: `workflow_execution_logs` can grow rapidly
3. **Vector search latency**: Large collections may require index optimization
4. **RLS overhead**: Complex RLS policies add 20-50ms per query

**Workarounds**:
1. Use partial indexes on JSONB fields for common queries
2. Implement log retention and archival strategy
3. Tune ivfflat index lists parameter (currently 100)
4. Use service role for internal service-to-service queries

### 7.2 Areas for Improvement

**Performance Enhancements**:
- **Materialized views**: Pre-compute expensive dashboard queries
- **Partitioning**: Implement table partitioning for high-volume tables
- **Index optimization**: Regular ANALYZE and index maintenance
- **Query caching**: Application-level query result caching

**Feature Enhancements**:
- **Time-series data**: Consider TimescaleDB extension for execution metrics
- **Graph queries**: Evaluate Apache AGE for graph memory queries
- **Full-text search**: Enhanced full-text search with custom dictionaries

**Operational Improvements**:
- **Automated cleanup**: Scheduled cleanup of old logs and expired data
- **Index monitoring**: Automated index usage analysis
- **Query optimization**: Slow query alerts and auto-optimization

### 7.3 Planned Enhancements

**Short-term (Q1 2025)**:
1. Implement log retention policies
2. Add execution metrics aggregation tables
3. Optimize vector search indexes
4. Add database monitoring dashboards

**Medium-term (Q2-Q3 2025)**:
1. Implement table partitioning for logs
2. Add read replicas for scalability
3. Implement materialized views for dashboards
4. Enhance vector search with hybrid search

**Long-term (Q4 2025+)**:
1. Evaluate graph database for memory system
2. Implement time-series database for metrics
3. Add advanced search capabilities
4. Implement automated database tuning

### 7.4 Migration Paths

#### Current Migration Strategy
- **Supabase CLI**: All migrations in `supabase/migrations/`
- **Sequential migrations**: Timestamped migration files
- **Version control**: All migrations tracked in git
- **Rollback support**: Manual rollback procedures

#### Future Migration Considerations
- **Blue-green deployments**: Zero-downtime schema changes
- **Backward compatibility**: Support multiple schema versions
- **Data migrations**: Separate data migrations from schema migrations
- **Testing**: Automated migration testing in staging environment

## 8. Appendices

### A. Glossary

**Core Terms**:
- **RLS (Row Level Security)**: PostgreSQL feature for multi-tenant data isolation
- **pgvector**: PostgreSQL extension for vector similarity search
- **JSONB**: PostgreSQL binary JSON data type with indexing support
- **HIL (Human-in-the-Loop)**: Workflow pause for human interaction
- **MCP (Model Context Protocol)**: Standard for AI tool integration
- **RAG (Retrieval-Augmented Generation)**: AI technique using vector search

**Database Terms**:
- **ivfflat**: Index type for approximate nearest neighbor search
- **GIN (Generalized Inverted Index)**: Index type for JSONB and arrays
- **PITR (Point-in-Time Recovery)**: Database backup/recovery capability
- **pgBouncer**: Connection pooler for PostgreSQL

**System Terms**:
- **Epoch milliseconds**: Unix timestamp in milliseconds (JavaScript standard)
- **Attached nodes**: AI_AGENT nodes with attached TOOL/MEMORY nodes
- **Trigger index**: Fast reverse lookup table for trigger matching
- **Deployment status**: Workflow deployment lifecycle state

### B. References

**Internal Documentation**:
- [Workflow Specification](/docs/tech-design/new_workflow_spec.md)
- [Node Structure](/docs/tech-design/node-structure.md)
- [HIL System Architecture](/docs/tech-design/human-in-loop-node-system.md)
- [Workflow Engine Architecture](/docs/tech-design/workflow-engine-architecure.md)
- [API Gateway Architecture](/docs/tech-design/api-gateway-architecture.md)

**External Resources**:
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Supabase Documentation](https://supabase.com/docs)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)

**Migration Files**:
- `20250715000001_initial_schema.sql` - Initial database schema
- `20250125000001_align_with_latest_design.sql` - Latest node specs alignment
- `20250901000001_hil_system_schema.sql` - HIL system tables
- `20250826000001_memory_implementations.sql` - Memory system tables
- `20250929000002_add_workflow_scheduler_tables.sql` - Scheduler tables

### C. Database Schema Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                         auth.users (Supabase)                        │
└────────────┬───────────────────────────────────────────────────┬────┘
             │                                                   │
     ┌───────▼────────┐                                  ┌──────▼──────┐
     │   workflows    │◀──────────────┐                 │  sessions   │
     │   ┌─────────┐  │               │                 └─────────────┘
     │   │ nodes   │  │               │
     │   ├─────────┤  │               │
     │   │ conns   │  │               │
     │   └─────────┘  │               │
     └────────┬────────┘               │
              │                        │
     ┌────────▼────────┐      ┌────────▼─────────┐
     │ trigger_index   │      │ oauth_tokens     │
     └─────────────────┘      │ credentials      │
              │                └──────────────────┘
     ┌────────▼────────────────────────────────────────┐
     │         workflow_executions                     │
     │  ┌─────────────────────────────────────────┐   │
     │  │ node_executions                         │   │
     │  │ workflow_execution_logs                 │   │
     │  │ workflow_execution_pauses [HIL]         │   │
     │  └─────────────────────────────────────────┘   │
     └─────────────────────────────────────────────────┘
              │
     ┌────────▼────────────────────────────────────────┐
     │         human_interactions [HIL]                │
     │  ┌─────────────────────────────────────────┐   │
     │  │ hil_responses                           │   │
     │  └─────────────────────────────────────────┘   │
     └─────────────────────────────────────────────────┘
              │
     ┌────────▼────────────────────────────────────────┐
     │         Memory System (8 types)                 │
     │  ┌─────────────────────────────────────────┐   │
     │  │ conversation_buffers / summaries        │   │
     │  │ entities / entity_relationships         │   │
     │  │ episodic_memory                         │   │
     │  │ knowledge_facts / rules                 │   │
     │  │ graph_nodes / relationships             │   │
     │  │ document_store                          │   │
     │  │ vector_embeddings                       │   │
     │  └─────────────────────────────────────────┘   │
     └─────────────────────────────────────────────────┘
```

### D. Index Strategy Summary

**Critical Performance Indexes**:
1. `idx_workflows_user_id` - Dashboard workflow list
2. `idx_executions_status_created` - Recent failed executions
3. `idx_trigger_index_lookup` - Trigger event matching
4. `idx_vector_embeddings_cosine` - RAG vector search
5. `idx_human_interactions_pending_timeout` - HIL timeout monitoring

**Index Maintenance**:
- Regular ANALYZE after bulk operations
- Monitor index bloat with pg_stat_user_indexes
- Rebuild indexes on low hit ratios
- Review slow query log for missing indexes

### E. Common Query Patterns

**User Dashboard**:
```sql
-- Get user's workflows with latest execution status
SELECT w.*,
       w.latest_execution_status,
       w.latest_execution_time
FROM workflows w
WHERE w.user_id = auth.uid()
  AND w.active = true
ORDER BY w.updated_at DESC
LIMIT 20;
```

**Execution Monitoring**:
```sql
-- Get execution details with node executions
SELECT we.*,
       json_agg(ne.*) as node_executions
FROM workflow_executions we
LEFT JOIN node_executions ne ON ne.execution_id = we.execution_id
WHERE we.execution_id = $1
GROUP BY we.id;
```

**Trigger Lookup**:
```sql
-- Find workflows triggered by webhook path
SELECT ti.workflow_id, ti.trigger_config
FROM trigger_index ti
WHERE ti.trigger_type = 'TRIGGER'
  AND ti.trigger_subtype = 'WEBHOOK'
  AND ti.index_key = '/webhook/my-path'
  AND ti.is_active = true
  AND ti.deployment_status = 'active';
```

**Vector Search (RAG)**:
```sql
-- Search similar node examples
SELECT * FROM search_similar_vectors(
    query_embedding := $1::vector(1536),
    collection_name_param := 'node_examples',
    similarity_threshold := 0.7,
    max_results := 10
);
```

**HIL Timeout Monitoring**:
```sql
-- Find pending HIL interactions approaching timeout
SELECT hi.*
FROM human_interactions hi
WHERE hi.status = 'pending'
  AND hi.timeout_at < NOW() + INTERVAL '15 minutes'
  AND hi.timeout_at > NOW()
ORDER BY hi.timeout_at ASC;
```

---

**Document Version**: 2.0
**Last Updated**: 2025-01-25
**Authors**: Technical Documentation Team
**Status**: Current Implementation
