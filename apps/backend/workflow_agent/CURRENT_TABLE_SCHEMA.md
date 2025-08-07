# Current Table Schema for workflow_agent_states

## 基于 state.py 的正确表结构

根据当前的 `agents/state.py` (MCP集成后的main分支版本)，正确的表结构应该是：

```sql
CREATE TABLE workflow_agent_states (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Core identity fields (from WorkflowState)
    session_id VARCHAR(255) NOT NULL UNIQUE,  -- state.session_id: str
    user_id VARCHAR(255),                      -- state.user_id: str
    
    -- Timestamps
    created_at BIGINT NOT NULL,                -- state.created_at: int (ms)
    updated_at BIGINT NOT NULL,                -- state.updated_at: int (ms)
    
    -- Stage management
    stage VARCHAR(50) NOT NULL CHECK (stage IN (
        'clarification', 
        'gap_analysis', 
        'workflow_generation', 
        'debug', 
        'completed'  -- 注意: 是 'completed' 不是 'end'
    )),                                        -- state.stage: WorkflowStage
    previous_stage VARCHAR(50) CHECK (previous_stage IN (
        'clarification', 
        'gap_analysis', 
        'workflow_generation', 
        'debug', 
        'completed'
    )),                                        -- state.previous_stage: NotRequired[WorkflowStage]
    
    -- Core workflow data
    intent_summary TEXT DEFAULT '',            -- state.intent_summary: str
    conversations JSONB NOT NULL DEFAULT '[]', -- state.conversations: List[Conversation]
    execution_history JSONB DEFAULT '[]',      -- state.execution_history: NotRequired[List[str]]
    
    -- Clarification context
    clarification_context JSONB DEFAULT '{
        "purpose": "initial_intent",
        "collected_info": {},
        "pending_questions": [],
        "origin": "create"
    }',                                        -- state.clarification_context: ClarificationContext
    
    -- Gap analysis results
    gap_status VARCHAR(20) DEFAULT 'no_gap' CHECK (gap_status IN (
        'no_gap', 
        'has_gap',
        'gap_resolved',
        'blocking'
    )),                                        -- state.gap_status: NotRequired[str]
    identified_gaps JSONB DEFAULT '[]',        -- state.identified_gaps: NotRequired[List[GapDetail]]
    
    -- Workflow data
    current_workflow JSONB,                    -- state.current_workflow: NotRequired[Any]
    template_workflow JSONB,                   -- state.template_workflow: NotRequired[Any]
    workflow_context JSONB DEFAULT '{
        "origin": "create",
        "requirements": {}
    }',                                        -- state.workflow_context: NotRequired[Dict[str, Any]]
    
    -- Debug information
    debug_result JSONB,                        -- state.debug_result: NotRequired[Dict[str, Any]]
    debug_loop_count INTEGER DEFAULT 0,        -- state.debug_loop_count: NotRequired[int]
    
    -- Template information
    template_id VARCHAR(255)                   -- state.template_id: NotRequired[str]
);
```

## state.py 和 数据库表的映射关系

| state.py 字段 | 数据库列 | 类型 | 说明 |
|-------------|---------|------|------|
| session_id | session_id | VARCHAR(255) | 会话ID |
| user_id | user_id | VARCHAR(255) | 用户ID |
| created_at | created_at | BIGINT | 创建时间(毫秒) |
| updated_at | updated_at | BIGINT | 更新时间(毫秒) |
| stage | stage | VARCHAR(50) | 当前阶段 |
| previous_stage | previous_stage | VARCHAR(50) | 上一阶段 |
| intent_summary | intent_summary | TEXT | 意图摘要 |
| conversations | conversations | JSONB | 对话历史 |
| execution_history | execution_history | JSONB | 执行历史 |
| clarification_context | clarification_context | JSONB | 澄清上下文 |
| gap_status | gap_status | VARCHAR(20) | Gap状态 |
| identified_gaps | identified_gaps | JSONB | 识别的gaps |
| current_workflow | current_workflow | JSONB | 当前工作流 |
| template_workflow | template_workflow | JSONB | 模板工作流 |
| workflow_context | workflow_context | JSONB | 工作流上下文 |
| debug_result | debug_result | JSONB | 调试结果 |
| debug_loop_count | debug_loop_count | INTEGER | 调试循环次数 |
| template_id | template_id | VARCHAR(255) | 模板ID |

## 需要注意的更改

1. **stage值**: 使用 `'completed'` 而不是 `'end'`
2. **移除的字段** (这些在state.py中不存在):
   - user_message (从conversations获取)
   - clarification_questions (在clarification_context中)
   - alternative_solutions
   - selected_alternative_index
   - current_workflow_json (改为JSONB的current_workflow)
   - previous_errors

3. **debug_result结构** (Dict[str, Any]):
   ```json
   {
     "success": true/false,
     "errors": ["error1", "error2"],
     "warnings": ["warning1"],
     "suggestions": ["suggestion1"],
     "iteration_count": 1,
     "timestamp": 1234567890000
   }
   ```

4. **clarification_context结构** (ClarificationContext):
   ```json
   {
     "purpose": "initial_intent",
     "collected_info": {"key": "value"},
     "pending_questions": ["question1", "question2"],
     "origin": "create"
   }
   ```

5. **identified_gaps结构** (List[GapDetail]):
   ```json
   [
     {
       "required_capability": "capability",
       "missing_component": "component",
       "alternatives": ["alt1", "alt2"]
     }
   ]
   ```

## 迁移步骤

如果从旧表结构迁移：

1. 运行 `001_create_workflow_agent_states.sql` 创建基础表
2. 运行 `002_update_to_mcp_integration.sql` 更新到MCP集成版本

这确保了数据库表与当前的state.py完全一致。