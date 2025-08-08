-- Migration: Add trigger optimization with dedicated index table
-- Description: Create trigger_index table for fast reverse lookup of all trigger types
-- Created: 2025-08-06

-- Create dedicated trigger index table for fast event matching
CREATE TABLE trigger_index (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL,
    trigger_type TEXT NOT NULL, -- 'TRIGGER_MANUAL', 'TRIGGER_CRON', 'TRIGGER_WEBHOOK', 'TRIGGER_SLACK', 'TRIGGER_EMAIL', 'TRIGGER_GITHUB'
    trigger_config JSONB NOT NULL, -- 触发器完整配置

    -- 快速匹配字段 (每个触发器类型只用一个核心字段进行粗筛选)
    index_key TEXT, -- 统一的快速匹配字段
    -- TRIGGER_CRON: cron_expression
    -- TRIGGER_WEBHOOK: webhook_path
    -- TRIGGER_SLACK: workspace_id
    -- TRIGGER_EMAIL: email_address
    -- TRIGGER_GITHUB: repository_name

    -- 部署状态
    deployment_status TEXT DEFAULT 'active', -- 'active', 'testing', 'inactive'

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 外键约束
ALTER TABLE trigger_index
ADD CONSTRAINT fk_trigger_index_workflow
FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE;

-- 创建针对不同触发器类型的专门索引
CREATE INDEX idx_trigger_index_type ON trigger_index(trigger_type);
CREATE INDEX idx_trigger_index_deployment_status ON trigger_index(deployment_status);

-- 统一的快速匹配索引 (支持所有触发器类型)
CREATE INDEX idx_trigger_index_key ON trigger_index(trigger_type, index_key)
    WHERE index_key IS NOT NULL;

-- 复合索引用于最常见的查询模式
CREATE INDEX idx_trigger_index_lookup ON trigger_index(trigger_type, index_key, deployment_status)
    WHERE index_key IS NOT NULL;

-- 添加注释说明
COMMENT ON TABLE trigger_index IS 'Optimized index table for fast trigger reverse lookup across all trigger types';
COMMENT ON COLUMN trigger_index.index_key IS 'Unified fast matching field: cron_expression for CRON, webhook_path for WEBHOOK, workspace_id for SLACK, email_address for EMAIL, repository_name for GITHUB';
COMMENT ON COLUMN trigger_index.deployment_status IS 'Deployment status: active, testing, inactive';
