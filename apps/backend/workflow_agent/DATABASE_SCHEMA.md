# Database Schema Documentation

## workflow_agent_states Table

This is the primary table for storing workflow agent state, aligned with the `WorkflowState` TypedDict in `agents/state.py`.

### Current Schema (After MCP Integration)

```sql
CREATE TABLE workflow_agent_states (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identity
    session_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255),
    
    -- Timestamps (milliseconds)
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL,
    
    -- Workflow Stage
    stage VARCHAR(50) NOT NULL,  -- Values: clarification, gap_analysis, workflow_generation, debug, completed
    previous_stage VARCHAR(50),
    
    -- Core Data
    intent_summary TEXT DEFAULT '',
    conversations JSONB NOT NULL DEFAULT '[]',
    execution_history JSONB DEFAULT '[]',
    
    -- Clarification
    clarification_context JSONB,
    
    -- Gap Analysis
    gap_status VARCHAR(20) DEFAULT 'no_gap',  -- Values: no_gap, has_gap, gap_resolved, blocking
    identified_gaps JSONB DEFAULT '[]',
    
    -- Workflow
    current_workflow JSONB,
    template_workflow JSONB,
    workflow_context JSONB,
    
    -- Debug
    debug_result JSONB,
    debug_loop_count INTEGER DEFAULT 0,
    
    -- Template
    template_id VARCHAR(255)
);
```

### Field Mappings

| Python (state.py) | Database Column | Type | Description |
|-------------------|-----------------|------|-------------|
| `session_id: str` | `session_id` | VARCHAR(255) | Unique session identifier |
| `user_id: str` | `user_id` | VARCHAR(255) | User identifier |
| `created_at: int` | `created_at` | BIGINT | Creation timestamp (ms) |
| `updated_at: int` | `updated_at` | BIGINT | Update timestamp (ms) |
| `stage: WorkflowStage` | `stage` | VARCHAR(50) | Current stage (enum value) |
| `previous_stage: WorkflowStage` | `previous_stage` | VARCHAR(50) | Previous stage for backtracking |
| `intent_summary: str` | `intent_summary` | TEXT | User intent from clarification |
| `conversations: List[Conversation]` | `conversations` | JSONB | Conversation history |
| `execution_history: List[str]` | `execution_history` | JSONB | Stage execution history |
| `clarification_context: ClarificationContext` | `clarification_context` | JSONB | Clarification metadata |
| `gap_status: str` | `gap_status` | VARCHAR(20) | Gap analysis status |
| `identified_gaps: List[GapDetail]` | `identified_gaps` | JSONB | Identified capability gaps |
| `current_workflow: Any` | `current_workflow` | JSONB | Generated workflow JSON |
| `template_workflow: Any` | `template_workflow` | JSONB | Template workflow if editing |
| `workflow_context: Dict[str, Any]` | `workflow_context` | JSONB | Workflow metadata |
| `debug_result: Dict[str, Any]` | `debug_result` | JSONB | Debug validation results |
| `debug_loop_count: int` | `debug_loop_count` | INTEGER | Debug iteration count |
| `template_id: str` | `template_id` | VARCHAR(255) | Template ID if using |

### JSONB Field Structures

#### conversations
```json
[
  {
    "role": "user|assistant|system",
    "text": "message content",
    "timestamp": 1234567890000,
    "metadata": {}
  }
]
```

#### clarification_context (ClarificationContext)
```json
{
  "purpose": "initial_intent|template_modification|gap_negotiation|debug_issue",
  "collected_info": {"key": "value"},
  "pending_questions": ["question1", "question2"],
  "origin": "create|edit|copy"
}
```

#### identified_gaps (List[GapDetail])
```json
[
  {
    "required_capability": "capability name",
    "missing_component": "component name",
    "alternatives": ["alternative1", "alternative2"]
  }
]
```

#### debug_result
```json
{
  "success": true,
  "errors": ["error1", "error2"],
  "warnings": ["warning1"],
  "suggestions": ["suggestion1"],
  "iteration_count": 1,
  "timestamp": 1234567890000
}
```

#### workflow_context
```json
{
  "origin": "create|edit|copy",
  "requirements": {
    "key": "value"
  }
}
```

### Indexes

- `idx_workflow_agent_states_session_id` - Primary lookup
- `idx_workflow_agent_states_user_id` - User queries
- `idx_workflow_agent_states_stage` - Stage filtering
- `idx_workflow_agent_states_gap_status` - Gap analysis queries
- `idx_workflow_agent_states_updated_at` - Time-based queries
- `idx_workflow_agent_states_template_id` - Template queries
- GIN indexes on JSONB fields for complex queries

### Migration History

1. **001_create_workflow_agent_states.sql** - Initial schema
2. **002_update_to_mcp_integration.sql** - Updates for MCP integration
3. **003_final_mcp_schema.sql** - Complete schema (drop & recreate)

### Important Notes

1. **Stage Values**: Use `'completed'` not `'end'`
2. **JSONB Storage**: All complex objects stored as JSONB
3. **No Text Serialization**: No more `current_workflow_json` TEXT field
4. **Removed Fields**: 
   - `user_message` (derived from conversations)
   - `clarification_questions` (in clarification_context)
   - `alternative_solutions` (merged into identified_gaps)
   - `selected_alternative_index` (not needed)
   - `previous_errors` (in debug_result)

### Testing

Run `python test_state_db_consistency.py` to verify:
- State creation and retrieval
- JSONB field handling
- Enum value conversion
- Update operations
- Full state persistence

### State Manager

The `services/state_manager.py` handles:
- Automatic enum conversion (WorkflowStage → string)
- JSONB field persistence
- Mock state for testing without Supabase
- Session-based state management