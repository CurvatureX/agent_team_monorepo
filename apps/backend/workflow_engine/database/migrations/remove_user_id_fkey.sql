-- Remove user_id foreign key constraint from workflows table
ALTER TABLE public.workflows 
DROP CONSTRAINT IF EXISTS workflows_user_id_fkey;

-- Optional: Add comment to document the change
COMMENT ON COLUMN public.workflows.user_id IS 'User ID - no longer enforces foreign key constraint';