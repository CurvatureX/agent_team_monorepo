-- Add automatic TTL cleanup for workflow_execution_logs using PostgreSQL functions
-- This runs at the database level, independent of application services

-- Create cleanup function
CREATE OR REPLACE FUNCTION cleanup_old_execution_logs()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete logs older than 10 days
    DELETE FROM workflow_execution_logs
    WHERE created_at < NOW() - INTERVAL '10 days';

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    -- Log the cleanup activity (optional)
    RAISE NOTICE 'Cleaned up % old execution logs', deleted_count;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Enable pg_cron extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Schedule the cleanup function to run daily at 2 AM UTC
-- Note: This requires superuser privileges and may need to be run manually in production
SELECT cron.schedule(
    'cleanup-execution-logs',           -- Job name
    '0 2 * * *',                        -- Cron expression: daily at 2 AM
    'SELECT cleanup_old_execution_logs();'
);

-- Alternative: Create a trigger-based approach for automatic cleanup
-- This approach cleans up during INSERT operations (less ideal for performance)

-- CREATE OR REPLACE FUNCTION trigger_cleanup_old_logs()
-- RETURNS TRIGGER AS $$
-- BEGIN
--     -- Only run cleanup randomly (1% chance) to avoid performance impact
--     IF random() < 0.01 THEN
--         PERFORM cleanup_old_execution_logs();
--     END IF;
--     RETURN NEW;
-- END;
-- $$ LANGUAGE plpgsql;

-- CREATE TRIGGER cleanup_logs_trigger
--     AFTER INSERT ON workflow_execution_logs
--     FOR EACH ROW EXECUTE FUNCTION trigger_cleanup_old_logs();

-- Grant necessary permissions
GRANT EXECUTE ON FUNCTION cleanup_old_execution_logs() TO service_role;

-- Test the function (optional)
-- SELECT cleanup_old_execution_logs();
