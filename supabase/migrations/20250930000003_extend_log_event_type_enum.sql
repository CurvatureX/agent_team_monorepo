-- Migration: Extend log_event_type_enum to align with engine EventType
-- Adds missing enum values used by the v2 engine's user-friendly logger
-- Created: 2025-09-30

DO $$
BEGIN
    -- Add values if they don't already exist (Postgres >= 12 supports IF NOT EXISTS)
    ALTER TYPE log_event_type_enum ADD VALUE IF NOT EXISTS 'workflow_failed';
    ALTER TYPE log_event_type_enum ADD VALUE IF NOT EXISTS 'step_failed';
    ALTER TYPE log_event_type_enum ADD VALUE IF NOT EXISTS 'human_interaction';
    ALTER TYPE log_event_type_enum ADD VALUE IF NOT EXISTS 'data_processing';
END
$$;
