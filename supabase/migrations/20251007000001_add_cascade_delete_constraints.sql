-- Migration: Add CASCADE DELETE foreign key constraints for workflow cleanup
-- Description: Ensure all tables referencing workflows have proper CASCADE constraints
-- Created: 2025-10-07
-- Purpose: Enable automatic cleanup of related records when workflows are deleted

BEGIN;

-- ============================================================================
-- 1. Add foreign key constraints to workflow_deployments
-- ============================================================================

-- Add constraint if it doesn't exist
DO $$
BEGIN
    -- Check if constraint exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_workflow_deployments_workflow_id'
        AND table_name = 'workflow_deployments'
    ) THEN
        -- Add foreign key constraint with CASCADE
        ALTER TABLE workflow_deployments
        ADD CONSTRAINT fk_workflow_deployments_workflow_id
        FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE;

        RAISE NOTICE 'Added CASCADE constraint to workflow_deployments';
    ELSE
        RAISE NOTICE 'CASCADE constraint already exists on workflow_deployments';
    END IF;
END $$;

-- ============================================================================
-- 2. Add foreign key constraints to trigger_executions
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_trigger_executions_workflow_id'
        AND table_name = 'trigger_executions'
    ) THEN
        ALTER TABLE trigger_executions
        ADD CONSTRAINT fk_trigger_executions_workflow_id
        FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE;

        RAISE NOTICE 'Added CASCADE constraint to trigger_executions';
    ELSE
        RAISE NOTICE 'CASCADE constraint already exists on trigger_executions';
    END IF;
END $$;

-- ============================================================================
-- 3. Add foreign key constraints to trigger_status
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_trigger_status_workflow_id'
        AND table_name = 'trigger_status'
    ) THEN
        ALTER TABLE trigger_status
        ADD CONSTRAINT fk_trigger_status_workflow_id
        FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE;

        RAISE NOTICE 'Added CASCADE constraint to trigger_status';
    ELSE
        RAISE NOTICE 'CASCADE constraint already exists on trigger_status';
    END IF;
END $$;

-- ============================================================================
-- 4. Add foreign key constraints to email_messages
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_email_messages_workflow_id'
        AND table_name = 'email_messages'
    ) THEN
        ALTER TABLE email_messages
        ADD CONSTRAINT fk_email_messages_workflow_id
        FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE;

        RAISE NOTICE 'Added CASCADE constraint to email_messages';
    ELSE
        RAISE NOTICE 'CASCADE constraint already exists on email_messages';
    END IF;
END $$;

-- ============================================================================
-- 5. Add foreign key constraints to human_interactions (HIL system)
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_human_interactions_workflow_id'
        AND table_name = 'human_interactions'
    ) THEN
        ALTER TABLE human_interactions
        ADD CONSTRAINT fk_human_interactions_workflow_id
        FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE;

        RAISE NOTICE 'Added CASCADE constraint to human_interactions';
    ELSE
        RAISE NOTICE 'CASCADE constraint already exists on human_interactions';
    END IF;
END $$;

-- ============================================================================
-- 6. Add foreign key constraints to hil_responses (HIL system)
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_hil_responses_workflow_id'
        AND table_name = 'hil_responses'
    ) THEN
        ALTER TABLE hil_responses
        ADD CONSTRAINT fk_hil_responses_workflow_id
        FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE;

        RAISE NOTICE 'Added CASCADE constraint to hil_responses';
    ELSE
        RAISE NOTICE 'CASCADE constraint already exists on hil_responses';
    END IF;
END $$;

-- ============================================================================
-- 7. Add foreign key constraints to workflow_execution_logs
-- ============================================================================

-- Check if table exists first
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'workflow_execution_logs'
    ) THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints
            WHERE constraint_name = 'fk_workflow_execution_logs_workflow_id'
            AND table_name = 'workflow_execution_logs'
        ) THEN
            ALTER TABLE workflow_execution_logs
            ADD CONSTRAINT fk_workflow_execution_logs_workflow_id
            FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE;

            RAISE NOTICE 'Added CASCADE constraint to workflow_execution_logs';
        ELSE
            RAISE NOTICE 'CASCADE constraint already exists on workflow_execution_logs';
        END IF;
    ELSE
        RAISE NOTICE 'Table workflow_execution_logs does not exist, skipping';
    END IF;
END $$;

-- ============================================================================
-- 8. Add foreign key constraints to workflow_memory
-- ============================================================================

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'workflow_memory'
    ) THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints
            WHERE constraint_name = 'fk_workflow_memory_workflow_id'
            AND table_name = 'workflow_memory'
        ) THEN
            ALTER TABLE workflow_memory
            ADD CONSTRAINT fk_workflow_memory_workflow_id
            FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE;

            RAISE NOTICE 'Added CASCADE constraint to workflow_memory';
        ELSE
            RAISE NOTICE 'CASCADE constraint already exists on workflow_memory';
        END IF;
    ELSE
        RAISE NOTICE 'Table workflow_memory does not exist, skipping';
    END IF;
END $$;

-- ============================================================================
-- 9. Verify all constraints were added
-- ============================================================================

DO $$
DECLARE
    constraint_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO constraint_count
    FROM information_schema.table_constraints
    WHERE constraint_type = 'FOREIGN KEY'
    AND constraint_name LIKE 'fk_%_workflow_id';

    RAISE NOTICE 'Total workflow CASCADE foreign key constraints: %', constraint_count;
END $$;

COMMIT;

-- ============================================================================
-- Documentation
-- ============================================================================

COMMENT ON CONSTRAINT fk_workflow_deployments_workflow_id ON workflow_deployments
IS 'Cascade delete: Remove all deployment records when workflow is deleted';

COMMENT ON CONSTRAINT fk_trigger_executions_workflow_id ON trigger_executions
IS 'Cascade delete: Remove all trigger execution history when workflow is deleted';

COMMENT ON CONSTRAINT fk_trigger_status_workflow_id ON trigger_status
IS 'Cascade delete: Remove trigger status when workflow is deleted';

COMMENT ON CONSTRAINT fk_email_messages_workflow_id ON email_messages
IS 'Cascade delete: Remove email messages when workflow is deleted';

COMMENT ON CONSTRAINT fk_human_interactions_workflow_id ON human_interactions
IS 'Cascade delete: Remove HIL interactions when workflow is deleted';

COMMENT ON CONSTRAINT fk_hil_responses_workflow_id ON hil_responses
IS 'Cascade delete: Remove HIL responses when workflow is deleted';
