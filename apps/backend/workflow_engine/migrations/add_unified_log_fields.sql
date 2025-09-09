-- 统一日志表扩展 - 添加新字段以支持业务和技术日志分类
-- 执行前请确保备份现有数据

-- 第一步：添加新字段
ALTER TABLE workflow_execution_logs
ADD COLUMN IF NOT EXISTS log_category VARCHAR(20) NOT NULL DEFAULT 'technical',
ADD COLUMN IF NOT EXISTS user_friendly_message TEXT,
ADD COLUMN IF NOT EXISTS display_priority INTEGER NOT NULL DEFAULT 5,
ADD COLUMN IF NOT EXISTS is_milestone BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS technical_details JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS stack_trace TEXT,
ADD COLUMN IF NOT EXISTS performance_metrics JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS progress_percentage DECIMAL(5,2);

-- 第二步：创建新的索引优化查询性能
CREATE INDEX IF NOT EXISTS idx_execution_logs_category ON workflow_execution_logs(log_category);
CREATE INDEX IF NOT EXISTS idx_execution_logs_priority ON workflow_execution_logs(display_priority);
CREATE INDEX IF NOT EXISTS idx_execution_logs_milestone ON workflow_execution_logs(is_milestone);

-- 创建复合索引优化业务日志查询
CREATE INDEX IF NOT EXISTS idx_execution_logs_business_query
ON workflow_execution_logs(execution_id, log_category, display_priority)
WHERE log_category = 'business';

-- 创建复合索引优化技术日志查询
CREATE INDEX IF NOT EXISTS idx_execution_logs_technical_query
ON workflow_execution_logs(execution_id, log_category, level)
WHERE log_category = 'technical';

-- 创建里程碑事件查询索引
CREATE INDEX IF NOT EXISTS idx_execution_logs_milestones
ON workflow_execution_logs(execution_id, is_milestone, display_priority)
WHERE is_milestone = TRUE;

-- 第三步：更新现有数据，设置默认分类和优先级
UPDATE workflow_execution_logs
SET
    log_category = 'technical',  -- 现有日志默认标记为技术日志
    display_priority = CASE
        WHEN level = 'ERROR' THEN 7      -- 错误日志高优先级
        WHEN level = 'INFO' THEN 3       -- 信息日志低优先级
        WHEN level = 'DEBUG' THEN 1      -- 调试日志最低优先级
        ELSE 5
    END,
    is_milestone = CASE
        WHEN event_type IN ('workflow_started', 'workflow_completed') THEN TRUE
        ELSE FALSE
    END
WHERE log_category = 'technical';  -- 只更新还是默认值的记录

-- 第四步：创建一些示例业务日志（可选，用于测试）
-- 注意：这只是示例，实际环境中应该通过应用程序添加业务日志

-- INSERT INTO workflow_execution_logs (
--     execution_id,
--     log_category,
--     event_type,
--     level,
--     message,
--     user_friendly_message,
--     display_priority,
--     is_milestone,
--     step_number,
--     total_steps,
--     progress_percentage
-- ) VALUES (
--     'demo-execution-123',
--     'business',
--     'workflow_started',
--     'INFO',
--     'Starting demo workflow with 3 steps',
--     '🚀 开始执行演示工作流 (共3个步骤)',
--     10,  -- 最高优先级
--     TRUE,
--     NULL,
--     3,
--     0.0
-- );

-- 第五步：验证数据完整性
-- 检查所有记录都有正确的分类
SELECT
    log_category,
    COUNT(*) as count,
    MIN(created_at) as earliest,
    MAX(created_at) as latest
FROM workflow_execution_logs
GROUP BY log_category;

-- 检查优先级分布
SELECT
    log_category,
    display_priority,
    COUNT(*) as count
FROM workflow_execution_logs
GROUP BY log_category, display_priority
ORDER BY log_category, display_priority;

-- 检查里程碑事件
SELECT
    execution_id,
    event_type,
    message,
    user_friendly_message,
    is_milestone
FROM workflow_execution_logs
WHERE is_milestone = TRUE
ORDER BY created_at DESC
LIMIT 10;

-- 性能测试查询
EXPLAIN ANALYZE
SELECT execution_id, message, user_friendly_message, display_priority
FROM workflow_execution_logs
WHERE execution_id = 'demo-execution-123'
    AND log_category = 'business'
    AND display_priority >= 5
ORDER BY created_at ASC;

-- 完成提示
SELECT 'Unified log table migration completed successfully!' as status;
