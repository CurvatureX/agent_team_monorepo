# 工作流系统数据库设计文档

## 数据库选型

**PostgreSQL** - 支持JSONB、事务、外键约束，适合工作流系统的复杂数据结构和一致性要求。

## 核心表设计

### 1. Sessions 表
```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'active'
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_user_status ON sessions(user_id, status);
```

### 2. Messages 表
```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    message_type VARCHAR(20) NOT NULL, -- user, assistant, system
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    sequence_number INTEGER NOT NULL
);

CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_messages_user_id ON messages(user_id);
CREATE INDEX idx_messages_session_sequence ON messages(session_id, sequence_number);
```

### 3. Workflows 表
```sql
CREATE TABLE workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id VARCHAR(50) UNIQUE NOT NULL,
    session_id UUID NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    
    -- 版本管理
    sequence_number INTEGER NOT NULL,
    parent_workflow_id VARCHAR(50) REFERENCES workflows(workflow_id),
    is_current BOOLEAN DEFAULT false,
    
    -- 源追踪
    source_type VARCHAR(20), -- 'template', 'user_workflow', 'scratch'
    source_template_id VARCHAR(50) REFERENCES workflow_templates(template_id),
    source_workflow_id VARCHAR(50) REFERENCES workflows(workflow_id),
    source_user_id UUID,
    
    -- 工作流数据
    status VARCHAR(20) NOT NULL DEFAULT 'waiting',
    workflow_data JSONB,
    error_message TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_workflows_user_session ON workflows(user_id, session_id);
CREATE INDEX idx_workflows_session_sequence ON workflows(session_id, sequence_number);
CREATE INDEX idx_workflows_source_template ON workflows(source_template_id);
CREATE UNIQUE INDEX idx_workflows_session_current ON workflows(session_id) WHERE is_current = true;
```

### 4. Workflow Templates 表
```sql
CREATE TABLE workflow_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id VARCHAR(50) UNIQUE NOT NULL,
    template_name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    tags TEXT[],
    
    created_by_user_id UUID,
    is_public BOOLEAN DEFAULT false,
    is_official BOOLEAN DEFAULT false,
    
    template_data JSONB NOT NULL,
    usage_count INTEGER DEFAULT 0,
    version VARCHAR(20) DEFAULT '1.0.0',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_workflow_templates_public ON workflow_templates(is_public, is_official);
CREATE INDEX idx_workflow_templates_category ON workflow_templates(category);
CREATE INDEX idx_workflow_templates_usage ON workflow_templates(usage_count DESC);
```

## 数据关系

```
Users (1) ────> (N) Sessions ────> (N) Messages
         │                    │
         │                    └──> (N) Workflows
         │                           │
         │                           └──> (N) Workflow_Templates
         │
         └────> (N) Workflow_Templates
```

## 常用查询

### 会话管理
```sql
-- 获取用户的活跃会话
SELECT * FROM sessions WHERE user_id = ? AND status = 'active';

-- 获取会话的所有消息
SELECT * FROM messages WHERE session_id = ? ORDER BY sequence_number;
```

### 工作流版本管理
```sql
-- 获取当前工作流
SELECT * FROM workflows WHERE session_id = ? AND is_current = true;

-- 获取上一个工作流
WITH current_workflow AS (
    SELECT sequence_number FROM workflows 
    WHERE session_id = ? AND is_current = true
)
SELECT w.* FROM workflows w, current_workflow c
WHERE w.session_id = ? AND w.sequence_number = c.sequence_number - 1;

-- 获取工作流历史
SELECT workflow_id, sequence_number, status, created_at, is_current
FROM workflows WHERE session_id = ? ORDER BY sequence_number;
```

### 工作流创建
```sql
-- 创建新版本工作流
BEGIN;
UPDATE workflows SET is_current = false WHERE session_id = ? AND is_current = true;
INSERT INTO workflows (workflow_id, session_id, user_id, sequence_number, parent_workflow_id, is_current)
SELECT ?, ?, ?, COALESCE(MAX(sequence_number), 0) + 1, ?, true
FROM workflows WHERE session_id = ?;
COMMIT;

-- 从模板创建工作流
INSERT INTO workflows (workflow_id, session_id, user_id, sequence_number, 
                      source_type, source_template_id, workflow_data, is_current)
SELECT ?, ?, ?, 1, 'template', wt.template_id, wt.template_data, true
FROM workflow_templates wt WHERE wt.template_id = ?;
```

### 模板系统
```sql
-- 获取可用模板
SELECT t.*, 
       CASE 
           WHEN t.created_by_user_id = ? THEN 'own'
           WHEN t.is_official = true THEN 'official'
           ELSE 'community'
       END as template_source
FROM workflow_templates t
WHERE t.is_public = true OR t.created_by_user_id = ? OR t.is_official = true
ORDER BY t.is_official DESC, t.usage_count DESC;

-- 保存工作流为模板
INSERT INTO workflow_templates (template_id, template_name, description, 
                               created_by_user_id, is_public, template_data)
SELECT ?, ?, ?, w.user_id, ?, w.workflow_data
FROM workflows w WHERE w.workflow_id = ?;
```

### 源追踪
```sql
-- 查询工作流来源
SELECT w.workflow_id, w.source_type,
       CASE 
           WHEN w.source_type = 'template' THEN wt.template_name
           WHEN w.source_type = 'user_workflow' THEN 'Copied from user workflow'
           ELSE 'Created from scratch'
       END as source_info
FROM workflows w
LEFT JOIN workflow_templates wt ON w.source_template_id = wt.template_id
WHERE w.workflow_id = ?;
```

## 缓存策略

**Redis 缓存结构**：
```json
{
  "session:{session_id}": {"status": "active", "user_id": "user_123"},
  "workflow:{workflow_id}": {"status": "complete", "session_id": "session_123"},
  "session_workflows:{session_id}": ["wf_001", "wf_002"],
  "sse_connections": {"session_id": ["connection_1", "connection_2"]}
}
```

## 核心特性

1. **多版本管理**：支持工作流的修改历史和版本回退
2. **模板系统**：官方模板、社区模板、用户私有模板
3. **源追踪**：记录工作流的创建来源
4. **实时推送**：配合SSE实现工作流状态实时更新
5. **用户隔离**：所有数据都有user_id标识归属