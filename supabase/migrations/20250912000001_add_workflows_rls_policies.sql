-- Migration: Add Row Level Security policies for workflows table
-- Description: Enable RLS and create policies to ensure users can only see their own workflows
-- Created: 2025-09-12

-- Enable Row Level Security on workflows table
ALTER TABLE workflows ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own workflows
CREATE POLICY "Users can view their own workflows" ON workflows
    FOR SELECT
    USING (auth.uid() = user_id);

-- Policy: Users can only insert workflows for themselves
CREATE POLICY "Users can insert their own workflows" ON workflows
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Policy: Users can only update their own workflows
CREATE POLICY "Users can update their own workflows" ON workflows
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Policy: Users can only delete their own workflows
CREATE POLICY "Users can delete their own workflows" ON workflows
    FOR DELETE
    USING (auth.uid() = user_id);

-- Create index on user_id for better RLS performance
CREATE INDEX IF NOT EXISTS idx_workflows_user_id ON workflows(user_id);

-- Also enable RLS on related tables for consistency
ALTER TABLE workflow_executions ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see executions of their own workflows
CREATE POLICY "Users can view executions of their workflows" ON workflow_executions
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM workflows
            WHERE workflows.id = workflow_executions.workflow_id
            AND workflows.user_id = auth.uid()
        )
    );

-- Policy: Users can only insert executions for their own workflows
CREATE POLICY "Users can insert executions for their workflows" ON workflow_executions
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM workflows
            WHERE workflows.id = workflow_executions.workflow_id
            AND workflows.user_id = auth.uid()
        )
    );

-- Policy: Users can only update executions of their own workflows
CREATE POLICY "Users can update executions of their workflows" ON workflow_executions
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM workflows
            WHERE workflows.id = workflow_executions.workflow_id
            AND workflows.user_id = auth.uid()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM workflows
            WHERE workflows.id = workflow_executions.workflow_id
            AND workflows.user_id = auth.uid()
        )
    );

-- Create index on workflow_id for better join performance
CREATE INDEX IF NOT EXISTS idx_workflow_executions_workflow_id ON workflow_executions(workflow_id);
