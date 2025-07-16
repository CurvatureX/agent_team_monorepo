-- Migration: 002_audit_logs
-- Description: Add audit logging tables and indexes
-- Created: 2025-01-20
-- Author: Workflow Engine Team

-- This migration adds comprehensive audit logging support
-- Run this migration using: alembic upgrade head

-- ==============================================================================
-- Audit Logs Table
-- ==============================================================================

-- Main audit logs table
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    user_id VARCHAR(255),
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    action VARCHAR(100),
    source_ip VARCHAR(45), -- IPv6 max length
    user_agent TEXT,
    details JSONB,
    metadata JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    session_id VARCHAR(255),
    correlation_id VARCHAR(255),
    
    -- Constraints
    CONSTRAINT valid_severity CHECK (
        severity IN ('low', 'medium', 'high', 'critical')
    ),
    CONSTRAINT valid_event_type CHECK (
        event_type IN (
            'login_success', 'login_failure', 'logout', 'token_refresh', 'unauthorized_access',
            'credential_created', 'credential_updated', 'credential_deleted', 'credential_accessed', 'oauth2_token_refresh',
            'api_call_success', 'api_call_failure', 'api_rate_limit', 'api_timeout',
            'workflow_created', 'workflow_updated', 'workflow_deleted', 'workflow_executed',
            'tool_executed', 'tool_failed',
            'service_started', 'service_stopped', 'configuration_changed', 'error_occurred',
            'suspicious_activity', 'security_violation', 'access_denied'
        )
    )
);

-- ==============================================================================
-- Security Event Aggregation Table
-- ==============================================================================

-- Table for aggregated security metrics
CREATE TABLE security_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_type VARCHAR(100) NOT NULL,
    user_id VARCHAR(255),
    resource_type VARCHAR(100),
    time_window TIMESTAMP WITH TIME ZONE NOT NULL, -- Start of the time window (hourly/daily)
    window_duration INTEGER NOT NULL, -- Duration in minutes (60 for hourly, 1440 for daily)
    event_count INTEGER NOT NULL DEFAULT 0,
    failure_count INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    unique_ips INTEGER NOT NULL DEFAULT 0,
    severity_breakdown JSONB, -- Count by severity level
    details JSONB,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint for aggregation windows
    UNIQUE(metric_type, user_id, resource_type, time_window, window_duration)
);

-- ==============================================================================
-- Credential Access Tracking
-- ==============================================================================

-- Table for tracking credential access patterns
CREATE TABLE credential_access_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    provider VARCHAR(100) NOT NULL,
    operation VARCHAR(50) NOT NULL, -- access, refresh, update, delete
    success BOOLEAN NOT NULL,
    source_ip VARCHAR(45),
    user_agent TEXT,
    access_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    session_id VARCHAR(255),
    
    -- Security context
    risk_score INTEGER DEFAULT 0, -- 0-100 risk assessment
    anomaly_flags TEXT[], -- Array of anomaly indicators
    metadata JSONB,
    
    -- Constraints
    CONSTRAINT valid_operation CHECK (
        operation IN ('access', 'refresh', 'update', 'delete', 'create')
    ),
    CONSTRAINT valid_risk_score CHECK (
        risk_score >= 0 AND risk_score <= 100
    )
);

-- ==============================================================================
-- API Call Metrics
-- ==============================================================================

-- Table for API call monitoring and rate limiting
CREATE TABLE api_call_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    provider VARCHAR(100) NOT NULL,
    operation VARCHAR(100) NOT NULL,
    method VARCHAR(10) NOT NULL, -- HTTP method
    endpoint VARCHAR(500) NOT NULL,
    
    -- Timing and status
    call_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    response_time_ms INTEGER,
    status_code INTEGER,
    success BOOLEAN NOT NULL,
    
    -- Request context
    request_size_bytes INTEGER,
    response_size_bytes INTEGER,
    source_ip VARCHAR(45),
    
    -- Rate limiting context
    rate_limit_remaining INTEGER,
    rate_limit_reset TIMESTAMP WITH TIME ZONE,
    
    -- Error information
    error_type VARCHAR(100),
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    metadata JSONB
);

-- ==============================================================================
-- System Health Monitoring
-- ==============================================================================

-- Table for system health and performance metrics
CREATE TABLE system_health_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    component VARCHAR(100) NOT NULL,
    metric_type VARCHAR(100) NOT NULL, -- cpu, memory, disk, network, response_time, etc.
    metric_value DECIMAL(10,4) NOT NULL,
    metric_unit VARCHAR(20) NOT NULL, -- %, MB, ms, etc.
    
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    threshold_exceeded BOOLEAN DEFAULT false,
    alert_level VARCHAR(20), -- info, warning, error, critical
    
    -- Additional context
    instance_id VARCHAR(255),
    environment VARCHAR(50),
    metadata JSONB
);

-- ==============================================================================
-- Indexes for Performance
-- ==============================================================================

-- Primary audit logs indexes
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_logs_event_type ON audit_logs(event_type);
CREATE INDEX idx_audit_logs_severity ON audit_logs(severity);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_resource_type ON audit_logs(resource_type);
CREATE INDEX idx_audit_logs_resource_id ON audit_logs(resource_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_source_ip ON audit_logs(source_ip);
CREATE INDEX idx_audit_logs_correlation_id ON audit_logs(correlation_id);

-- Composite indexes for common queries
CREATE INDEX idx_audit_logs_user_timestamp ON audit_logs(user_id, timestamp DESC);
CREATE INDEX idx_audit_logs_event_severity ON audit_logs(event_type, severity);
CREATE INDEX idx_audit_logs_resource_action ON audit_logs(resource_type, action);

-- Security metrics indexes
CREATE INDEX idx_security_metrics_type_window ON security_metrics(metric_type, time_window DESC);
CREATE INDEX idx_security_metrics_user_id ON security_metrics(user_id);
CREATE INDEX idx_security_metrics_updated_at ON security_metrics(updated_at DESC);

-- Credential access indexes
CREATE INDEX idx_credential_access_user_provider ON credential_access_log(user_id, provider);
CREATE INDEX idx_credential_access_timestamp ON credential_access_log(access_timestamp DESC);
CREATE INDEX idx_credential_access_source_ip ON credential_access_log(source_ip);
CREATE INDEX idx_credential_access_risk_score ON credential_access_log(risk_score DESC);

-- API metrics indexes
CREATE INDEX idx_api_metrics_user_provider ON api_call_metrics(user_id, provider);
CREATE INDEX idx_api_metrics_timestamp ON api_call_metrics(call_timestamp DESC);
CREATE INDEX idx_api_metrics_success ON api_call_metrics(success);
CREATE INDEX idx_api_metrics_status_code ON api_call_metrics(status_code);
CREATE INDEX idx_api_metrics_response_time ON api_call_metrics(response_time_ms DESC);

-- System health indexes
CREATE INDEX idx_system_health_component ON system_health_log(component);
CREATE INDEX idx_system_health_timestamp ON system_health_log(timestamp DESC);
CREATE INDEX idx_system_health_alert_level ON system_health_log(alert_level);
CREATE INDEX idx_system_health_threshold ON system_health_log(threshold_exceeded);

-- ==============================================================================
-- Partitioning for Large Tables (Optional - for high volume systems)
-- ==============================================================================

-- Partition audit_logs by month for better performance
-- Uncomment these lines if you expect high volume of audit logs

-- CREATE TABLE audit_logs_template (LIKE audit_logs INCLUDING DEFAULTS INCLUDING CONSTRAINTS);

-- -- Function to create monthly partitions
-- CREATE OR REPLACE FUNCTION create_monthly_partition(table_name text, start_date date)
-- RETURNS void AS $$
-- DECLARE
--     partition_name text;
--     end_date date;
-- BEGIN
--     partition_name := table_name || '_' || to_char(start_date, 'YYYY_MM');
--     end_date := start_date + interval '1 month';
--     
--     EXECUTE format('CREATE TABLE %I PARTITION OF %I 
--                     FOR VALUES FROM (%L) TO (%L)',
--                    partition_name, table_name, start_date, end_date);
--                    
--     EXECUTE format('ALTER TABLE %I ADD CONSTRAINT %I_check 
--                     CHECK (timestamp >= %L AND timestamp < %L)',
--                    partition_name, partition_name, start_date, end_date);
-- END;
-- $$ LANGUAGE plpgsql;

-- ==============================================================================
-- Triggers for Automatic Timestamping
-- ==============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for security_metrics table
CREATE TRIGGER update_security_metrics_updated_at 
    BEFORE UPDATE ON security_metrics 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ==============================================================================
-- Views for Common Queries
-- ==============================================================================

-- View for security dashboard
CREATE VIEW security_events_summary AS
SELECT 
    event_type,
    severity,
    COUNT(*) as event_count,
    COUNT(DISTINCT user_id) as affected_users,
    COUNT(DISTINCT source_ip) as unique_ips,
    MIN(timestamp) as first_occurrence,
    MAX(timestamp) as last_occurrence
FROM audit_logs 
WHERE event_type IN (
    'login_failure', 'unauthorized_access', 'suspicious_activity', 
    'security_violation', 'access_denied'
)
AND timestamp >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
GROUP BY event_type, severity
ORDER BY event_count DESC;

-- View for credential access patterns
CREATE VIEW credential_access_summary AS
SELECT 
    user_id,
    provider,
    operation,
    COUNT(*) as access_count,
    COUNT(CASE WHEN success = false THEN 1 END) as failure_count,
    COUNT(DISTINCT source_ip) as unique_ips,
    AVG(risk_score) as avg_risk_score,
    MAX(access_timestamp) as last_access
FROM credential_access_log
WHERE access_timestamp >= CURRENT_TIMESTAMP - INTERVAL '7 days'
GROUP BY user_id, provider, operation
ORDER BY access_count DESC;

-- View for API performance monitoring
CREATE VIEW api_performance_summary AS
SELECT 
    provider,
    operation,
    COUNT(*) as total_calls,
    COUNT(CASE WHEN success = true THEN 1 END) as successful_calls,
    AVG(response_time_ms) as avg_response_time,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time_ms) as p95_response_time,
    COUNT(DISTINCT user_id) as unique_users
FROM api_call_metrics
WHERE call_timestamp >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
GROUP BY provider, operation
ORDER BY total_calls DESC;

-- ==============================================================================
-- Functions for Data Retention
-- ==============================================================================

-- Function to clean old audit logs (run as scheduled job)
CREATE OR REPLACE FUNCTION cleanup_old_audit_logs(retention_days INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM audit_logs 
    WHERE timestamp < CURRENT_TIMESTAMP - (retention_days || ' days')::INTERVAL;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    INSERT INTO audit_logs (event_type, severity, action, details)
    VALUES ('system_maintenance', 'low', 'audit_log_cleanup', 
            jsonb_build_object('deleted_records', deleted_count, 'retention_days', retention_days));
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to archive old data to separate table
CREATE OR REPLACE FUNCTION archive_old_audit_logs(archive_days INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    archived_count INTEGER;
BEGIN
    -- Create archive table if it doesn't exist
    CREATE TABLE IF NOT EXISTS audit_logs_archive (LIKE audit_logs INCLUDING ALL);
    
    -- Move old records to archive
    WITH moved_rows AS (
        DELETE FROM audit_logs 
        WHERE timestamp < CURRENT_TIMESTAMP - (archive_days || ' days')::INTERVAL
        RETURNING *
    )
    INSERT INTO audit_logs_archive SELECT * FROM moved_rows;
    
    GET DIAGNOSTICS archived_count = ROW_COUNT;
    
    INSERT INTO audit_logs (event_type, severity, action, details)
    VALUES ('system_maintenance', 'low', 'audit_log_archive', 
            jsonb_build_object('archived_records', archived_count, 'archive_days', archive_days));
    
    RETURN archived_count;
END;
$$ LANGUAGE plpgsql;

-- ==============================================================================
-- Grant Permissions
-- ==============================================================================

-- Grant necessary permissions (adjust based on your user setup)
-- GRANT SELECT, INSERT ON audit_logs TO workflow_engine_app;
-- GRANT SELECT, INSERT, UPDATE ON security_metrics TO workflow_engine_app;
-- GRANT SELECT, INSERT ON credential_access_log TO workflow_engine_app;
-- GRANT SELECT, INSERT ON api_call_metrics TO workflow_engine_app;
-- GRANT SELECT, INSERT ON system_health_log TO workflow_engine_app;

-- GRANT SELECT ON security_events_summary TO workflow_engine_readonly;
-- GRANT SELECT ON credential_access_summary TO workflow_engine_readonly;
-- GRANT SELECT ON api_performance_summary TO workflow_engine_readonly; 